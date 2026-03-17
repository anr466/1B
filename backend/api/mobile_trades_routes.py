"""
Mobile Trades Routes — extracted from mobile_endpoints.py (God Object split)
=============================================================================
Routes: /trades, /active-positions, /daily-pnl, /portfolio-growth, /trades/favorite, /trades/distribution
"""

from flask import request, jsonify, g
from datetime import datetime, timedelta
import json
import logging

from backend.utils.trading_context import get_effective_is_demo, get_trading_context

logger = logging.getLogger(__name__)


def register_mobile_trades_routes(bp, shared):
    """Register trade-related routes on the mobile blueprint"""
    db_manager = shared['db_manager']
    verify_user_access = shared['verify_user_access']
    require_auth = shared['require_auth']
    rate_limit_data = shared['rate_limit_data']
    rate_limit_general = shared.get('rate_limit_general', lambda f: f)
    success_response = shared['success_response']
    error_response = shared['error_response']
    CACHE_AVAILABLE = shared.get('CACHE_AVAILABLE', False)
    response_cache = shared.get('response_cache', None)

    def _resolve_trade_context(db, user_id, requested_mode=None):
        """Resolve demo mode and canonical owner via centralized trading context rules."""
        trading_context = get_trading_context(db, user_id, requested_mode=requested_mode)
        return trading_context['is_demo'], trading_context['portfolio_owner_id']

    # ==================== سجل الصفقات (Trade History) ====================

    @bp.route('/trade/<int:trade_id>', methods=['GET'])
    @require_auth
    @rate_limit_data
    def get_trade_by_id(trade_id):
        """
        جلب صفقة واحدة بواسطة الـ ID
        يستخدم للتنقل من الإشعارات إلى تفاصيل الصفقة
        """
        try:
            user_id = g.user_id
            db = db_manager

            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT
                        id, user_id, symbol,
                        CASE WHEN position_type IN ('long', 'LONG') THEN 'buy' ELSE 'sell' END AS side,
                        quantity,
                        entry_price,
                        exit_price,
                        CASE WHEN is_active = TRUE THEN 'open' ELSE 'closed' END AS status,
                        profit_loss,
                        profit_pct,
                        strategy,
                        COALESCE(entry_date, created_at::text) AS opened_at,
                        closed_at
                    FROM active_positions
                    WHERE id = %s AND user_id = %s
                """, (trade_id, user_id))
                
                row = cursor.fetchone()
                
                if not row:
                    response_data, status_code = error_response('الصفقة غير موجودة', 'NOT_FOUND', 404)
                    return jsonify(response_data), status_code
                
                trade = {
                    'id': row[0],
                    'userId': row[1],
                    'symbol': row[2],
                    'side': row[3],
                    'quantity': float(row[4]) if row[4] else None,
                    'entryPrice': float(row[5]) if row[5] else None,
                    'exitPrice': float(row[6]) if row[6] else None,
                    'pnl': float(row[8]) if row[8] else None,
                    'pnlPercentage': float(row[9]) if row[9] else None,
                    'status': row[7],
                    'orderType': None,
                    'strategy': row[10],
                    'openedAt': row[11],
                    'closedAt': row[12],
                    'createdAt': row[11],
                    'updatedAt': row[12]
                }
                
                response_data, status_code = success_response(trade)
                return jsonify(response_data), status_code
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الصفقة {trade_id}: {e}")
            response_data, status_code = error_response('خطأ في جلب البيانات', 'ERROR', 500)
            return jsonify(response_data), status_code

    @bp.route('/trades/<int:user_id>', methods=['GET'])
    @require_auth
    @rate_limit_data
    def get_user_trades(user_id):
        """
        ✅ Phase 1: الحصول على سجل صفقات المستخدم مع Pagination
        
        Query Parameters:
        - page: رقم الصفحة (default: 1)
        - limit: عدد النتائج (default: 50, max: 200)
        - status: فلتر حسب الحالة (all, open, closed)
        - date_from: من تاريخ (ISO format)
        - date_to: إلى تاريخ (ISO format)
        
        ✅ عزل كامل: WHERE user_id = %s
        ✅ Pagination لتحسين الأداء
        ✅ Cache support
        """
        if not verify_user_access(user_id):
            return error_response('لا توجد صلاحيات', 'UNAUTHORIZED', 403)
        
        try:
            import math
            db = db_manager
            
            from datetime import datetime as dt
            
            page = request.args.get('page', 1, type=int)
            if page < 1:
                page = 1
            
            limit = min(request.args.get('limit', 50, type=int), 200)
            if limit < 1:
                limit = 50
            
            status = request.args.get('status', 'all')
            if status not in ['all', 'open', 'closed']:
                status = 'all'
            
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            
            if date_from:
                try:
                    dt.fromisoformat(date_from)
                except (ValueError, TypeError):
                    response_data, status_code = error_response('صيغة date_from غير صحيحة. استخدم ISO format (YYYY-MM-DD)', 'INVALID_DATE', 400)
                    return jsonify(response_data), status_code
            
            if date_to:
                try:
                    dt.fromisoformat(date_to)
                except (ValueError, TypeError):
                    response_data, status_code = error_response('صيغة date_to غير صحيحة. استخدم ISO format (YYYY-MM-DD)', 'INVALID_DATE', 400)
                    return jsonify(response_data), status_code
            
            if date_from and date_to:
                try:
                    if dt.fromisoformat(date_to) < dt.fromisoformat(date_from):
                        response_data, status_code = error_response('date_to يجب أن يكون بعد date_from', 'INVALID_DATE_RANGE', 400)
                        return jsonify(response_data), status_code
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ خطأ في مقارنة التواريخ: {e}")
            
            offset = (page - 1) * limit
            
            requested_mode = request.args.get('mode', None)
            is_demo, portfolio_owner_id = _resolve_trade_context(db, user_id, requested_mode)
            
            cache_key = f"trades_{user_id}_{page}_{limit}_{status}_{date_from}_{date_to}_{requested_mode}"
            if CACHE_AVAILABLE:
                cached_data = response_cache.get(cache_key)
                if cached_data:
                    logger.debug(f"✅ Trades من Cache للمستخدم {user_id}")
                    response_data, status_code = success_response(cached_data, 'تم جلب الصفقات من الذاكرة المؤقتة')
                    return jsonify(response_data), status_code
            
            trades_data = db.get_user_trades_paginated(
                user_id=portfolio_owner_id,
                limit=limit,
                offset=offset,
                status=status,
                date_from=date_from,
                date_to=date_to,
                is_demo=is_demo
            )
            
            if not trades_data:
                response_data, status_code = error_response('فشل في جلب الصفقات', 'TRADES_ERROR', 500)
                return jsonify(response_data), status_code
            
            formatted_trades = []
            trades_list = trades_data.get('trades', [])
            if trades_list:
                for trade in trades_list:
                    formatted_trades.append({
                        'id': trade.get('id'),
                        'symbol': trade.get('symbol'),
                        'side': trade.get('side', 'buy'),
                        'entryPrice': float(trade.get('entry_price', 0)) if trade.get('entry_price') else 0,
                        'exitPrice': float(trade.get('exit_price', 0)) if trade.get('exit_price') else 0,
                        'quantity': float(trade.get('quantity', 0)) if trade.get('quantity') else 0,
                        'profitLoss': float(trade.get('profit_loss', 0)) if trade.get('profit_loss') else 0,
                        'profitLossPercentage': float(trade.get('profit_loss_percentage', 0)) if trade.get('profit_loss_percentage') else 0,
                        'status': trade.get('status', 'unknown'),
                        'entryTime': trade.get('entry_time'),
                        'exitTime': trade.get('exit_time'),
                        'strategyName': trade.get('strategy', 'unknown'),
                        'timeframe': trade.get('timeframe'),
                        'stopLoss': float(trade['stop_loss']) if trade.get('stop_loss') else None,
                        'takeProfit': float(trade['take_profit']) if trade.get('take_profit') else None,
                        'exitReason': trade.get('exit_reason'),
                        'mlConfidence': float(trade['ml_confidence']) if trade.get('ml_confidence') else None,
                    })
            
            total_count = trades_data.get('total', 0) or 0
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
            
            result = {
                'trades': formatted_trades,
                'pagination': {
                    'total': total_count,
                    'page': page,
                    'limit': limit,
                    'pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }
            
            if CACHE_AVAILABLE:
                response_cache.set(cache_key, result, ttl=600, user_id=user_id)
            
            logger.info(f"Pagination: صفحة {page}/{total_pages} - {len(formatted_trades)} صفقة")
            
            response_data, status_code = success_response(result, 'تم جلب الصفقات بنجاح')
            return jsonify(response_data), status_code
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب صفقات المستخدم {user_id}: {e}")
            response_data, status_code = error_response('خطأ في جلب الصفقات', 'TRADES_ERROR', 500)
            return jsonify(response_data), status_code

    # ==================== الصفقات النشطة (Active Positions) ====================

    @bp.route('/active-positions/<int:user_id>', methods=['GET'])
    @require_auth
    def get_active_positions(user_id):
        """
        ✅ جلب الصفقات النشطة للمستخدم مع الأسعار الحالية
        """
        if not verify_user_access(user_id):
            response_data, status_code = error_response('غير مصرح بالوصول', 'UNAUTHORIZED_ACCESS', 403)
            return jsonify(response_data), status_code
        
        try:
            db = db_manager
            
            requested_mode = request.args.get('mode', None)
            is_demo, portfolio_owner_id = _resolve_trade_context(db, user_id, requested_mode)
            
            is_demo_bool = bool(is_demo) if is_demo is not None else None
            positions = db.get_user_active_positions(portfolio_owner_id, is_demo=is_demo_bool)
            
            formatted_positions = []
            total_unrealized_pnl = 0
            
            for pos in positions:
                entry_price = float(pos.get('entry_price', 0))
                quantity = float(pos.get('quantity', 0))
                symbol = pos.get('symbol', 'UNKNOWN')
                position_type = pos.get('position_type', 'long')
                
                current_price = entry_price
                try:
                    from backend.utils.data_provider import DataProvider
                    dp = DataProvider()
                    price = dp.get_current_price(symbol)
                    if price and price > 0:
                        current_price = price
                except Exception as price_err:
                    logger.warning(f"⚠️ فشل جلب السعر الحالي لـ {symbol}: {price_err}")
                
                if position_type in ['long', 'LONG', 'BUY', 'buy']:
                    unrealized_pnl = (current_price - entry_price) * quantity
                else:
                    unrealized_pnl = (entry_price - current_price) * quantity
                
                initial_investment = entry_price * quantity
                unrealized_pnl_pct = (unrealized_pnl / initial_investment * 100) if initial_investment > 0 else 0
                
                total_unrealized_pnl += unrealized_pnl
                
                formatted_positions.append({
                    'id': pos.get('id'),
                    'symbol': symbol,
                    'positionType': position_type,
                    'entryPrice': entry_price,
                    'currentPrice': current_price,
                    'quantity': quantity,
                    'positionSize': float(pos.get('position_size', 0)),
                    'stopLoss': float(pos.get('stop_loss', 0)) if pos.get('stop_loss') else None,
                    'takeProfit': float(pos.get('take_profit', 0)) if pos.get('take_profit') else None,
                    'trailingSlPrice': float(pos.get('trailing_sl_price', 0)) if pos.get('trailing_sl_price') else None,
                    'unrealizedPnl': round(unrealized_pnl, 2),
                    'unrealizedPnlPct': round(unrealized_pnl_pct, 2),
                    'strategy': pos.get('strategy', 'unknown'),
                    'timeframe': pos.get('timeframe', '1h'),
                    'entryDate': pos.get('entry_date') or pos.get('created_at'),
                    'isDemo': bool(pos.get('is_demo', 0)),
                })
            
            result = {
                'positions': formatted_positions,
                'total': len(formatted_positions),
                'totalUnrealizedPnl': round(total_unrealized_pnl, 2),
                'mode': 'demo' if is_demo else 'real'
            }
            
            response_data, status_code = success_response(result, 'تم جلب الصفقات النشطة بنجاح')
            return jsonify(response_data), status_code
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الصفقات النشطة للمستخدم {user_id}: {e}")
            response_data, status_code = error_response('خطأ في جلب الصفقات النشطة', 'POSITIONS_ERROR', 500)
            return jsonify(response_data), status_code

    # ==================== Daily PnL ====================

    @bp.route('/daily-pnl/<int:user_id>', methods=['GET'])
    @require_auth
    def get_daily_pnl(user_id):
        """جلب الأرباح/الخسائر اليومية للمستخدم (للـ Heatmap)"""
        try:
            if g.current_user_id != user_id:
                logger.warning(f"⚠️ محاولة وصول غير مصرح: المستخدم {g.current_user_id} يحاول الوصول لبيانات المستخدم {user_id}")
                response_data, status_code = error_response('غير مصرح بالوصول', 'UNAUTHORIZED_ACCESS', 403)
                return jsonify(response_data), status_code
            
            days = request.args.get('days', 90, type=int)
            requested_mode = request.args.get('trading_mode', None) or request.args.get('mode', None)
            
            db = db_manager
            is_demo, portfolio_owner_id = _resolve_trade_context(db, user_id, requested_mode)
            is_admin = (db.get_user_by_id(user_id) or {}).get('user_type') == 'admin'
            
            logger.info(f"📊 جلب البيانات اليومية للمستخدم {user_id} (is_demo={is_demo}, days={days})")
            
            query = """
                SELECT DATE(closed_at) as date,
                       SUM(profit_loss) as total_pnl,
                       COUNT(*) as trades_count,
                       SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                       SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades
                FROM active_positions
                WHERE user_id = %s
                  AND is_demo = %s
                  AND closed_at IS NOT NULL
                  AND is_active = FALSE
                  AND closed_at >= (CURRENT_TIMESTAMP - (%s::text || ' days')::interval)
                GROUP BY DATE(closed_at)
                ORDER BY date DESC
            """
            
            results = db_manager.execute_query(query, (portfolio_owner_id, is_demo, days))
            
            daily_data = []
            for row in results:
                daily_data.append({
                    'date': row['date'],
                    'total_pnl': round(float(row['total_pnl'] or 0), 2),
                    'trades_count': int(row['trades_count'] or 0),
                    'winning_trades': int(row['winning_trades'] or 0),
                    'losing_trades': int(row['losing_trades'] or 0),
                })
            
            response_data = {
                'data': daily_data,
                'period': {
                    'days': days,
                    'start_date': (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
                    'end_date': datetime.now().strftime('%Y-%m-%d'),
                },
                'mode': 'demo' if is_demo == 1 else 'real',
                'is_admin': is_admin,
                'total_days': len(daily_data)
            }
            
            logger.info(f"✅ تم جلب {len(daily_data)} يوم من البيانات للمستخدم {user_id}")
            
            resp, code = success_response(response_data, 'تم جلب البيانات اليومية بنجاح')
            return jsonify(resp), code
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب البيانات اليومية: {e}")
            response_data, status_code = error_response('خطأ في جلب البيانات اليومية', 'DAILY_PNL_ERROR', 500)
            return jsonify(response_data), status_code

    # ============ نقاط نهاية نمو المحفظة (Portfolio Growth) ============

    @bp.route('/portfolio-growth/<user_id>', methods=['GET'])
    @require_auth
    @rate_limit_data
    def get_portfolio_growth(user_id):
        """جلب بيانات نمو المحفظة"""
        try:
            user_id = int(user_id)
            if not verify_user_access(user_id):
                response_data, status_code = error_response('غير مصرح بالوصول', 'UNAUTHORIZED_ACCESS', 403)
                return jsonify(response_data), status_code
            
            days = request.args.get('days', 30, type=int)
            requested_mode = request.args.get('mode', None)
            
            db = db_manager
            is_demo, portfolio_owner_id = _resolve_trade_context(db, user_id, requested_mode)
            
            with db_manager.get_connection() as conn:
                try:
                    rows = conn.execute("""
                        SELECT date, total_balance, daily_pnl, daily_pnl_percentage
                        FROM portfolio_growth_history
                        WHERE user_id = %s AND is_demo = %s
                        AND date >= CURRENT_DATE - (%s::integer)
                        ORDER BY date ASC
                    """, (portfolio_owner_id, is_demo, days)).fetchall()
                except Exception:
                    rows = []
                
                growth_data = []
                for row in rows:
                    growth_data.append({
                        'date': row[0],
                        'totalBalance': float(row[1] or 0),
                        'dailyPnl': float(row[2] or 0),
                        'dailyPnlPercentage': float(row[3] or 0),
                    })
            
            result = {
                'growth': growth_data,
                'period': days,
                'mode': 'demo' if is_demo == 1 else 'real'
            }
            
            response_data, status_code = success_response(result, 'تم جلب بيانات نمو المحفظة')
            return jsonify(response_data), status_code
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب نمو المحفظة: {e}")
            response_data, status_code = error_response('خطأ في جلب البيانات', 'GROWTH_ERROR', 500)
            return jsonify(response_data), status_code

    @bp.route('/admin/demo-portfolio-growth/<admin_id>', methods=['GET'])
    @require_auth
    @rate_limit_data
    def get_admin_demo_portfolio_growth(admin_id):
        """جلب بيانات نمو محفظة الأدمن التجريبية"""
        try:
            if getattr(g, 'current_user_type', None) != 'admin':
                response_data, status_code = error_response('غير مصرح بالوصول', 'UNAUTHORIZED', 403)
                return jsonify(response_data), status_code

            admin_id = g.current_user_id
            days = request.args.get('days', 30, type=int)
            
            with db_manager.get_connection() as conn:
                try:
                    rows = conn.execute("""
                        SELECT date, total_balance, daily_pnl, daily_pnl_percentage
                        FROM portfolio_growth_history
                        WHERE user_id = %s AND is_demo = TRUE
                        AND date >= CURRENT_DATE - (%s::integer)
                        ORDER BY date ASC
                    """, (admin_id, days)).fetchall()
                except Exception:
                    rows = []
                
                growth_data = [{
                    'date': row[0],
                    'totalBalance': float(row[1] or 0),
                    'dailyPnl': float(row[2] or 0),
                    'dailyPnlPercentage': float(row[3] or 0),
                } for row in rows]
            
            result = {
                'growth': growth_data,
                'period': days,
                'mode': 'demo'
            }
            
            response_data, status_code = success_response(result, 'تم جلب بيانات نمو المحفظة التجريبية')
            return jsonify(response_data), status_code
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب نمو محفظة الأدمن: {e}")
            response_data, status_code = error_response('خطأ في جلب البيانات', 'GROWTH_ERROR', 500)
            return jsonify(response_data), status_code

    # ============ Favorite Trades & Distribution ============

    @bp.route('/trades/favorite', methods=['POST'])
    @require_auth
    def toggle_trade_favorite():
        """تبديل حالة المفضلة لصفقة"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'لا توجد بيانات'}), 400
            
            trade_id = data.get('trade_id')
            is_favorite = data.get('is_favorite')
            
            if not trade_id:
                return jsonify({'success': False, 'error': 'معرف الصفقة مطلوب'}), 400
            
            with db_manager.get_write_connection() as conn:
                trade = conn.execute(
                    "SELECT id, user_id FROM active_positions WHERE id = %s",
                    (trade_id,)
                ).fetchone()
                
                if not trade:
                    return jsonify({'success': False, 'error': 'الصفقة غير موجودة'}), 404

                if trade[1] != g.current_user_id:
                    logger.warning(f"⚠️ Unauthorized favorite toggle: user {g.current_user_id} tried trade {trade_id} owned by {trade[1]}")
                    return jsonify({'success': False, 'error': 'غير مصرح بتعديل صفقة مستخدم آخر'}), 403
                
                conn.execute(
                    "UPDATE active_positions SET is_favorite = %s WHERE id = %s",
                    (True if is_favorite else False, trade_id)
                )
                
                logger.info(f"✅ Trade {trade_id} favorite: {is_favorite}")
                return jsonify({
                    'success': True,
                    'message': 'تم تحديث المفضلة بنجاح',
                    'is_favorite': bool(is_favorite)
                })
                
        except Exception as e:
            logger.error(f"❌ خطأ في تبديل المفضلة: {e}")
            return jsonify({'success': False, 'error': 'خطأ في الخادم'}), 500

    @bp.route('/trades/favorites/<int:user_id>', methods=['GET'])
    @require_auth
    def get_favorite_trades(user_id):
        """جلب الصفقات المفضلة"""
        try:
            if not verify_user_access(user_id):
                return jsonify({'success': False, 'error': 'Unauthorized access to another user\'s data'}), 403

            db = db_manager
            is_demo, portfolio_owner_id = _resolve_trade_context(db, user_id, request.args.get('mode', None))
            
            with db_manager.get_connection() as conn:
                try:
                    cursor = conn.execute("""
                        SELECT id, symbol, entry_price, exit_price, quantity,
                               profit_loss, profit_pct AS profit_loss_percentage,
                               CASE WHEN is_active = TRUE THEN 'open' ELSE 'closed' END AS status,
                               COALESCE(entry_date, created_at::text) AS entry_time,
                               closed_at AS exit_time, strategy, is_favorite
                        FROM active_positions
                        WHERE user_id = %s AND is_demo = %s AND is_favorite = TRUE
                        ORDER BY COALESCE(closed_at, updated_at) DESC
                    """, (portfolio_owner_id, is_demo))
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    cursor = conn.execute("""
                        SELECT id, symbol, entry_price, exit_price, quantity,
                               profit_loss, profit_pct AS profit_loss_percentage,
                               CASE WHEN is_active = TRUE THEN 'open' ELSE 'closed' END AS status,
                               COALESCE(entry_date, created_at::text) AS entry_time,
                               closed_at AS exit_time, strategy, FALSE as is_favorite
                        FROM active_positions
                        WHERE user_id = %s AND is_demo = %s
                        ORDER BY COALESCE(closed_at, updated_at) DESC
                    """, (portfolio_owner_id, is_demo))
                trades = cursor.fetchall()
                cols = [c[0] for c in cursor.description] if cursor.description else []
                
                return jsonify({
                    'success': True,
                    'data': {
                        'trades': [dict(zip(cols, row)) for row in trades],
                        'total': len(trades)
                    }
                })
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب المفضلة: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/trades/distribution/<int:user_id>', methods=['GET'])
    @require_auth
    def get_trades_distribution(user_id):
        """جلب توزيع الصفقات"""
        try:
            db = db_manager
            is_demo, portfolio_owner_id = _resolve_trade_context(db, user_id, request.args.get('mode', None))
            
            with db_manager.get_connection() as conn:
                stats = conn.execute("""
                    SELECT
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
                        SUM(CASE WHEN profit_loss = 0 THEN 1 ELSE 0 END) as breakeven_trades,
                        SUM(profit_loss) as total_profit,
                        AVG(profit_loss) as avg_profit,
                        MAX(profit_loss) as best_trade,
                        MIN(profit_loss) as worst_trade
                    FROM active_positions
                    WHERE user_id = %s AND is_demo = %s AND is_active = 0
                """, (portfolio_owner_id, is_demo)).fetchone()
                
                by_symbol = conn.execute("""
                    SELECT symbol, COUNT(*) as count, SUM(profit_loss) as total
                    FROM active_positions
                    WHERE user_id = %s AND is_demo = %s AND is_active = 0
                    GROUP BY symbol
                    ORDER BY total DESC
                    LIMIT 10
                """, (portfolio_owner_id, is_demo)).fetchall()
                
                by_strategy = conn.execute("""
                    SELECT strategy, COUNT(*) as count, AVG(profit_loss) as avg
                    FROM active_positions
                    WHERE user_id = %s AND is_demo = %s AND is_active = 0
                    GROUP BY strategy
                    ORDER BY count DESC
                    LIMIT 5
                """, (portfolio_owner_id, is_demo)).fetchall()
                
                distribution = {
                    'total_trades': stats[0] or 0,
                    'winning_trades': stats[1] or 0,
                    'losing_trades': stats[2] or 0,
                    'breakeven_trades': stats[3] or 0,
                    'winning_percent': round((stats[1] or 0) / max(stats[0] or 1, 1) * 100),
                    'losing_percent': round((stats[2] or 0) / max(stats[0] or 1, 1) * 100),
                    'breakeven_percent': round((stats[3] or 0) / max(stats[0] or 1, 1) * 100),
                    'total_profit': stats[4] or 0,
                    'avg_profit': stats[5] or 0,
                    'best_trade': stats[6] or 0,
                    'worst_trade': stats[7] or 0,
                    'by_symbol': [dict(zip(['symbol', 'count', 'total'], row)) for row in by_symbol],
                    'by_strategy': [dict(zip(['strategy', 'count', 'avg'], row)) for row in by_strategy],
                }
                
                return jsonify({
                    'success': True,
                    'data': {
                        'distribution': distribution,
                        'total_trades': stats[0] or 0
                    }
                })
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب التوزيع: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # ============ Dashboard ============

    @bp.route('/dashboard/<int:user_id>', methods=['GET'])
    @require_auth
    def get_dashboard(user_id):
        """📊 جلب بيانات Dashboard الشاملة"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403
        
        try:
            db = db_manager
            dashboard_data = {
                'portfolio': {},
                'active_positions': [],
                'stats': {},
                'settings': {},
                'system_status': {}
            }
            
            is_demo, portfolio_owner_id = _resolve_trade_context(db, user_id, request.args.get('mode', None))
            
            with db.get_connection() as conn:
                portfolio_balance_row = conn.execute(
                    "SELECT available_balance FROM portfolio WHERE user_id = %s AND is_demo = %s ORDER BY updated_at DESC LIMIT 1",
                    (portfolio_owner_id, is_demo)
                ).fetchone()

                # fallback: في real mode فقط، يمكن استخدام آخر رصيد Binance إن لم تتوفر محفظة
                if portfolio_balance_row is not None:
                    dashboard_data['portfolio']['balance'] = portfolio_balance_row[0] or 0
                elif is_demo == 0:
                    balance_row = conn.execute(
                        "SELECT total_balance FROM user_binance_balance WHERE user_id = %s ORDER BY updated_at DESC LIMIT 1",
                        (user_id,)
                    ).fetchone()
                    dashboard_data['portfolio']['balance'] = balance_row[0] if balance_row else 0
                else:
                    dashboard_data['portfolio']['balance'] = 0
                
                trades_stats = conn.execute("""
                    SELECT
                        SUM(CASE WHEN is_active = FALSE THEN 1 ELSE 0 END) as total_trades,
                        SUM(CASE WHEN is_active = FALSE AND profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(CASE WHEN is_active = FALSE AND profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
                        SUM(CASE WHEN is_active = FALSE THEN profit_loss ELSE 0 END) as total_pnl
                    FROM active_positions
                    WHERE user_id = %s AND is_demo = %s
                """, (portfolio_owner_id, is_demo)).fetchone()
                
                dashboard_data['stats'] = {
                    'total_trades': trades_stats[0] or 0,
                    'winning_trades': trades_stats[1] or 0,
                    'losing_trades': trades_stats[2] or 0,
                    'total_pnl': round(trades_stats[3] or 0, 2),
                    'win_rate': round((((trades_stats[1] or 0) / (trades_stats[0] or 0)) * 100), 2) if (trades_stats[0] or 0) > 0 else 0
                }
                
                positions = conn.execute("""
                    SELECT 
                        id, symbol, position_type, entry_price, quantity,
                        stop_loss, take_profit, COALESCE(entry_date, created_at::text) as created_at
                    FROM active_positions 
                    WHERE user_id = %s AND is_demo = %s AND is_active = TRUE
                    ORDER BY COALESCE(entry_date, created_at::text) DESC
                    LIMIT 5
                """, (portfolio_owner_id, is_demo)).fetchall()
                
                dashboard_data['active_positions'] = [
                    {
                        'id': row[0],
                        'symbol': row[1],
                        'position_type': row[2],
                        'entry_price': row[3],
                        'quantity': row[4],
                        'stop_loss': row[5],
                        'take_profit': row[6],
                        'created_at': row[7]
                    }
                    for row in positions
                ]
                
                settings_row = conn.execute(
                    "SELECT trading_mode, risk_level FROM user_settings WHERE user_id = %s AND is_demo = %s LIMIT 1",
                    (user_id, is_demo)
                ).fetchone()
                
                if settings_row:
                    dashboard_data['settings'] = {
                        'trading_mode': settings_row[0] if settings_row[0] in ('demo', 'real') else 'demo',
                        'risk_level': settings_row[1] or 'medium'
                    }
            
            # Read system status from DB directly
            try:
                with db.get_connection() as conn:
                    status_row = conn.execute("""
                        SELECT trading_state, is_running, status, message
                        FROM system_status WHERE id=1
                    """).fetchone()
                    
                    if status_row:
                        dashboard_data['system_status'] = {
                            'trading_state': status_row[0],
                            'is_running': bool(status_row[1]),
                            'status': status_row[2] or 'unknown',
                            'message': status_row[3]
                        }
                    else:
                        dashboard_data['system_status'] = {
                            'is_running': False,
                            'status': 'unknown'
                        }
            except Exception as sys_error:
                logger.warning(f"⚠️ Could not get system status from DB: {sys_error}")
                dashboard_data['system_status'] = {
                    'is_running': False,
                    'status': 'error'
                }
            
            logger.info(f"✅ Dashboard data fetched for user {user_id}")
            return jsonify({
                'success': True,
                'data': dashboard_data
            })
            
        except Exception as e:
            import traceback
            logger.error(f"❌ خطأ في جلب بيانات Dashboard: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({'success': False, 'error': f'خطأ في جلب البيانات: {str(e)}'}), 500
