"""
Mobile Settings Routes — extracted from mobile_endpoints.py (God Object split)
===============================================================================
Routes: /settings, /settings/validate, /settings/trading-mode, /binance-keys, /profile, /reset-data
"""

from flask import request, jsonify, g
from datetime import datetime, timedelta
import json
import logging
import os
import re

logger = logging.getLogger(__name__)


def register_mobile_settings_routes(bp, shared):
    """Register settings-related routes on the mobile blueprint"""
    db_manager = shared['db_manager']
    verify_user_access = shared['verify_user_access']
    require_auth = shared['require_auth']
    rate_limit_general = shared.get('rate_limit_general', lambda f: f)
    rate_limit_trading = shared.get('rate_limit_trading', lambda f: f)
    rate_limit_auth = shared.get('rate_limit_auth', lambda f: f)
    success_response = shared['success_response']
    error_response = shared['error_response']
    require_idempotency = shared.get('require_idempotency', lambda *a: (lambda f: f))
    prevent_concurrent_duplicates = shared.get('prevent_concurrent_duplicates', lambda f: f)
    CACHE_AVAILABLE = shared.get('CACHE_AVAILABLE', False)
    response_cache = shared.get('response_cache', None)
    ENCRYPTION_AVAILABLE = shared.get('ENCRYPTION_AVAILABLE', False)
    audit_logger = shared.get('audit_logger', None)

    # ==================== إعدادات التداول (Settings) ====================

    @bp.route('/settings/<int:user_id>', methods=['GET'])
    @require_auth
    @rate_limit_general
    def get_user_settings(user_id):
        """الحصول على إعدادات التداول - عزل كامل"""
        if not verify_user_access(user_id):
            response_data, status_code = error_response('لا توجد صلاحيات', 'UNAUTHORIZED', 403)
            return jsonify(response_data), status_code

        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()

            # ✅ فحص نوع المستخدم أولاً لتحديد كيفية قراءة الإعدادات
            user_query = "SELECT user_type FROM users WHERE id = ?"
            user_result = db.execute_query(user_query, (user_id,))
            is_admin = user_result[0]['user_type'] == 'admin' if user_result else False

            # ✅ للأدمن: قراءة الإعدادات حسب المحفظة النشطة (trading_mode)
            if is_admin:
                # جلب trading_mode الحالي من أي صف للأدمن
                mode_query = "SELECT trading_mode FROM user_settings WHERE user_id = ? LIMIT 1"
                mode_result = db.execute_query(mode_query, (user_id,))
                current_mode = mode_result[0]['trading_mode'] if mode_result else 'demo'

                # تحديد is_demo حسب trading_mode
                if current_mode == 'demo':
                    is_demo = 1
                elif current_mode == 'real':
                    is_demo = 0
                else:  # auto
                    # فحص وجود مفاتيح
                    keys_query = "SELECT COUNT(*) as count FROM user_binance_keys WHERE user_id = ? AND is_active = 1"
                    keys_result = db.execute_query(keys_query, (user_id,))
                    has_keys = keys_result[0]['count'] > 0 if keys_result else False
                    is_demo = 0 if has_keys else 1

                # قراءة الإعدادات الخاصة بالمحفظة النشطة
                settings_query = """
                    SELECT trading_enabled, trade_amount, position_size_percentage,
                           risk_level, stop_loss_pct, trailing_distance,
                           take_profit_pct, max_positions, trading_mode, is_demo
                    FROM user_settings 
                    WHERE user_id = ? AND is_demo = ?
                    LIMIT 1
                """
                result = db.execute_query(settings_query, (user_id, is_demo))
            else:
                # ✅ للمستخدمين العاديين: قراءة إعدادات Real فقط
                settings_query = """
                    SELECT trading_enabled, trade_amount, position_size_percentage,
                           risk_level, stop_loss_pct, trailing_distance,
                           take_profit_pct, max_positions, trading_mode, is_demo
                    FROM user_settings 
                    WHERE user_id = ? AND is_demo = 0
                    LIMIT 1
                """
                result = db.execute_query(settings_query, (user_id, ))

            if result and len(result) > 0:
                s = result[0]

                # ✅ فحص وجود مفاتيح Binance
                keys_query = "SELECT COUNT(*) as count FROM user_binance_keys WHERE user_id = ? AND is_active = 1"
                keys_result = db.execute_query(keys_query, (user_id,))
                has_keys = keys_result[0]['count'] > 0 if keys_result else False

                data = {
                    'tradingEnabled': bool(s['trading_enabled']),
                    'tradeAmount': float(s['trade_amount'] or 100.0),
                    'positionSizePercentage': float(s['position_size_percentage'] or 10.0),
                    'riskLevel': s['risk_level'] or 'medium',
                    'stopLossPercentage': float(s['stop_loss_pct'] or 3.0),
                    'takeProfitPercentage': float(s['take_profit_pct'] or 6.0),
                    'trailingDistance': float(s['trailing_distance'] or 3.0),
                    'maxConcurrentTrades': int(s['max_positions'] or 5),
                    'tradingMode': s['trading_mode'] or 'auto',
                    'activePortfolio': 'demo' if s['is_demo'] else 'real',
                    'canToggle': is_admin,
                    'hasBinanceKeys': has_keys
                }
                response_data, status_code = success_response(data, 'تم جلب الإعدادات بنجاح')
                return jsonify(response_data), status_code
            else:
                data = {
                    'tradingEnabled': False, 
                    'tradeAmount': 100.0,
                    'positionSizePercentage': 10.0,
                    'riskLevel': 'medium',
                    'stopLossPercentage': 3.0, 
                    'takeProfitPercentage': 6.0,
                    'maxConcurrentTrades': 5, 
                    'tradingMode': 'auto',
                    'canToggle': False,
                    'hasBinanceKeys': False
                }
                response_data, status_code = success_response(data, 'تم جلب الإعدادات الافتراضية')
                return jsonify(response_data), status_code
        except Exception as e:
            logger.error(f"❌ خطأ Settings {user_id}: {e}")
            response_data, status_code = error_response('خطأ في جلب الإعدادات', 'SETTINGS_ERROR', 500)
            return jsonify(response_data), status_code


    @bp.route('/settings/<int:user_id>/validate', methods=['POST'])
    @require_auth
    @rate_limit_general
    def validate_trading_settings(user_id):
        """
        التحقق من صحة إعدادات التداول وفحص المتطلبات

        Returns:
            Dict: {
                'can_trade': bool,
                'reason': str,
                'has_keys': bool,
                'sufficient_balance': bool,
                'current_positions': int,
                'max_allowed_positions': int,
                'available_balance': float,
                'required_amount': float,
                'validation_errors': List[str]
            }
        """
        if not verify_user_access(user_id):
            response_data, status_code = error_response('لا توجد صلاحيات', 'UNAUTHORIZED', 403)
            return jsonify(response_data), status_code

        try:
            from backend.core.group_b_system import GroupBSystem

            group_b = GroupBSystem(user_id)

            # 1. فحص المتطلبات الأساسية
            settings = group_b.user_settings
            portfolio = group_b.user_portfolio
            balance = portfolio.get('balance', 0)
            has_keys = group_b._check_binance_keys()
            open_positions = group_b._get_open_positions()

            position_size_pct = settings.get('position_size_percentage', 0)
            max_positions = settings.get('max_positions', 0)

            # 2. فحص بوابات الحماية
            can_trade_gate, gate_reason = group_b._check_risk_gates(open_positions, balance)

            # 3. حساب حجم الصفقة
            position_size = group_b._calculate_position_size(balance) if balance > 0 else 0

            # 4. تحديد الأخطاء والتحذيرات
            errors = []
            warnings = []

            if not group_b.is_demo_trading and not has_keys:
                errors.append('مفاتيح Binance غير مضافة')
            if balance < 10:
                errors.append(f'الرصيد غير كافٍ: ${balance:.2f} (الحد الأدنى $10)')
            if position_size_pct <= 0:
                errors.append('نسبة حجم الصفقة غير محددة')
            if max_positions <= 0:
                errors.append('الحد الأقصى للصفقات غير محدد')
            if not can_trade_gate and gate_reason != "OK":
                warnings.append(f'بوابة الحماية: {gate_reason}')

            can_trade = len(errors) == 0 and settings.get('trading_enabled', False)
            reason = 'جاهز للتداول' if can_trade else (errors[0] if errors else 'التداول معطّل')

            data = {
                'can_trade': can_trade,
                'reason': reason,
                'has_keys': has_keys,
                'sufficient_balance': balance >= 10,
                'current_positions': len(open_positions),
                'max_allowed_positions': max_positions,
                'available_balance': balance,
                'required_amount': position_size,
                'validation_errors': errors,
                'validation_warnings': warnings,
            }

            response_data, status_code = success_response(data, 'تم التحقق من متطلبات التداول')
            return jsonify(response_data), status_code

        except Exception as e:
            logger.error(f"❌ خطأ في التحقق من إعدادات التداول {user_id}: {e}")
            response_data, status_code = error_response('خطأ في التحقق من الإعدادات', 'VALIDATION_ERROR', 500)
            return jsonify(response_data), status_code


    @bp.route('/settings/<int:user_id>', methods=['PUT'])
    @require_auth
    @rate_limit_trading
    @prevent_concurrent_duplicates
    @require_idempotency('update_settings')
    def update_user_settings(user_id):
        """تحديث إعدادات التداول - عزل كامل + Validation للحد اليومي + إبطال Cache"""
        if not verify_user_access(user_id):
            response_data, status_code = error_response('لا توجد صلاحيات', 'UNAUTHORIZED', 403)
            return jsonify(response_data), status_code

        try:
            from database.database_manager import DatabaseManager
            import re
            db = DatabaseManager()
            data = request.get_json()

            # ═══════════════════════════════════════════════════════════════
            # ✅ FIX: تطبيع أسماء الحقول — القبول بـ snake_case و camelCase
            # Frontend interceptor يحوّل كل المفاتيح إلى snake_case تلقائياً
            # لكن الكود أدناه يقرأ camelCase — لذلك نطبّع هنا
            # ═══════════════════════════════════════════════════════════════
            if data:
                normalized = {}
                for key, value in data.items():
                    camel_key = re.sub(r'_([a-z])', lambda m: m.group(1).upper(), key)
                    normalized[camel_key] = value
                    if key != camel_key:
                        normalized[key] = value  # نحتفظ بالمفتاح الأصلي أيضاً
                data = normalized

            # ═══════════════════════════════════════════════════════════════
            # ✅ التحقق من صحة البيانات المدخلة (Input Validation)
            # ═══════════════════════════════════════════════════════════════

            # التحقق من tradeAmount
            if 'tradeAmount' in data:
                try:
                    trade_amount_val = float(data['tradeAmount'])
                    if trade_amount_val < 5 or trade_amount_val > 10000:
                        return jsonify({
                            'success': False,
                            'error': 'مبلغ التداول يجب أن يكون بين 5 و 10000 USDT',
                            'error_code': 'INVALID_TRADE_AMOUNT'
                        }), 400
                    data['tradeAmount'] = trade_amount_val
                except (ValueError, TypeError):
                    return jsonify({
                        'success': False,
                        'error': 'مبلغ التداول يجب أن يكون رقماً صحيحاً',
                        'error_code': 'INVALID_TRADE_AMOUNT'
                    }), 400

            # التحقق من maxConcurrentTrades
            if 'maxConcurrentTrades' in data:
                try:
                    max_trades_val = int(data['maxConcurrentTrades'])
                    if max_trades_val < 1 or max_trades_val > 20:
                        return jsonify({
                            'success': False,
                            'error': 'عدد الصفقات المتزامنة يجب أن يكون بين 1 و 20',
                            'error_code': 'INVALID_MAX_TRADES'
                        }), 400
                    data['maxConcurrentTrades'] = max_trades_val
                except (ValueError, TypeError):
                    return jsonify({
                        'success': False,
                        'error': 'عدد الصفقات يجب أن يكون رقماً صحيحاً',
                        'error_code': 'INVALID_MAX_TRADES'
                    }), 400

            # التحقق من stopLossPercentage
            if 'stopLossPercentage' in data:
                try:
                    sl_val = float(data['stopLossPercentage'])
                    if sl_val < 0.5 or sl_val > 10:
                        return jsonify({
                            'success': False,
                            'error': 'نسبة وقف الخسارة يجب أن تكون بين 0.5% و 10%',
                            'error_code': 'INVALID_STOP_LOSS'
                        }), 400
                    data['stopLossPercentage'] = sl_val
                except (ValueError, TypeError):
                    return jsonify({
                        'success': False,
                        'error': 'نسبة وقف الخسارة يجب أن تكون رقماً',
                        'error_code': 'INVALID_STOP_LOSS'
                    }), 400

            # التحقق من takeProfitPercentage
            if 'takeProfitPercentage' in data:
                try:
                    tp_val = float(data['takeProfitPercentage'])
                    if tp_val < 1 or tp_val > 50:
                        return jsonify({
                            'success': False,
                            'error': 'نسبة جني الأرباح يجب أن تكون بين 1% و 50%',
                            'error_code': 'INVALID_TAKE_PROFIT'
                        }), 400
                    data['takeProfitPercentage'] = tp_val
                except (ValueError, TypeError):
                    return jsonify({
                        'success': False,
                        'error': 'نسبة جني الأرباح يجب أن تكون رقماً',
                        'error_code': 'INVALID_TAKE_PROFIT'
                    }), 400

            # ═══════════════════════════════════════════════════════════════
            # ✅ فحص شروط تفعيل التداول
            # ═══════════════════════════════════════════════════════════════
            trading_enabled = data.get('tradingEnabled', False)

            if trading_enabled:
                # ✅ فحص نوع المستخدم ووضع التداول لتحديد الاستثناءات
                user_type_query = "SELECT user_type FROM users WHERE id = ?"
                user_type_result = db.execute_query(user_type_query, (user_id,))
                is_admin_user = user_type_result[0]['user_type'] == 'admin' if user_type_result else False

                # ✅ جلب وضع التداول الحالي
                mode_query = "SELECT trading_mode, is_demo FROM user_settings WHERE user_id = ? ORDER BY is_demo ASC LIMIT 1"
                mode_result = db.execute_query(mode_query, (user_id,))
                current_mode = mode_result[0]['trading_mode'] if mode_result else 'auto'
                current_is_demo = mode_result[0]['is_demo'] if mode_result else 1

                # ✅ استثناء الأدمن في الوضع التجريبي: لا يحتاج مفاتيح Binance
                skip_binance_check = is_admin_user and (current_mode == 'demo' or current_is_demo == 1)

                if not skip_binance_check:
                    # 1️⃣ فحص وجود مفاتيح Binance (مطلوب للتداول الحقيقي)
                    keys_query = "SELECT api_key, api_secret FROM user_binance_keys WHERE user_id = ? AND is_active = 1"
                    keys_result = db.execute_query(keys_query, (user_id,))
                    has_keys = keys_result and len(keys_result) > 0 and keys_result[0].get('api_key')

                    if not has_keys:
                        return jsonify({
                            'success': False,
                            'error': 'لا يمكن تفعيل التداول بدون ربط حساب Binance',
                            'error_code': 'NO_BINANCE_KEYS',
                            'message': '🔑 يرجى إضافة مفاتيح Binance API أولاً من إعدادات التداول',
                            'action_required': 'add_binance_keys'
                        }), 400

                # 2️⃣ ✅ جلب الرصيد - من DB للتجريبي، من Binance للحقيقي
                trade_amount = data.get('tradeAmount', 100.0)
                available_balance = 0.0
                binance_error = None

                if skip_binance_check:
                    # ✅ الأدمن في الوضع التجريبي: جلب الرصيد من قاعدة البيانات
                    demo_query = "SELECT available_balance FROM portfolio WHERE user_id = ? AND is_demo = 1"
                    demo_result = db.execute_query(demo_query, (user_id,))
                    available_balance = float(demo_result[0]['available_balance'] or 0) if demo_result else 1000.0
                    logger.info(f"✅ Admin demo balance for user {user_id}: {available_balance:.2f} USDT")
                else:
                    try:
                        from backend.utils.binance_balance_checker import BinanceBalanceChecker
                        balance_checker = BinanceBalanceChecker(user_id)
                        balance_result = balance_checker.get_available_balance()

                        if balance_result.get('success'):
                            available_balance = float(balance_result.get('free_usdt', 0))
                            logger.info(f"✅ جلب رصيد Binance للمستخدم {user_id}: {available_balance:.2f} USDT")
                        else:
                            binance_error = balance_result.get('error', 'خطأ في الاتصال بـ Binance')
                    except ImportError:
                        # إذا لم تتوفر خدمة فحص الرصيد، نستخدم قاعدة البيانات كاحتياطي
                        logger.warning(f"⚠️ BinanceBalanceChecker غير متاح، استخدام قاعدة البيانات")
                        portfolio_query = "SELECT available_balance FROM portfolio WHERE user_id = ? AND is_demo = 0"
                        portfolio_result = db.execute_query(portfolio_query, (user_id,))
                        available_balance = float(portfolio_result[0]['available_balance'] or 0) if portfolio_result else 0
                    except Exception as e:
                        binance_error = str(e)
                        logger.error(f"❌ خطأ في جلب رصيد Binance: {e}")

                # إذا فشل الاتصال بـ Binance
                if binance_error:
                    return jsonify({
                        'success': False,
                        'error': 'فشل التحقق من رصيد Binance',
                        'error_code': 'BINANCE_CONNECTION_ERROR',
                        'message': f'⚠️ لم نتمكن من التحقق من رصيدك في Binance.\n\n{binance_error}\n\nتأكد من صحة مفاتيح API وأنها تملك صلاحية القراءة.',
                        'action_required': 'check_binance_keys'
                    }), 400

                # 3️⃣ فحص الرصيد الحر الكافي
                if available_balance < trade_amount:
                    return jsonify({
                        'success': False,
                        'error': 'الرصيد المتاح غير كافٍ',
                        'error_code': 'INSUFFICIENT_BALANCE',
                        'message': f'💰 رصيدك الحر في Binance ({available_balance:.2f} USDT) أقل من مبلغ التداول ({trade_amount:.2f} USDT).\n\nيرجى إيداع المزيد في حساب Binance الخاص بك أو تقليل مبلغ التداول.',
                        'available_balance': available_balance,
                        'required_amount': trade_amount,
                        'action_required': 'deposit_funds'
                    }), 400

                # 4️⃣ فحص المراكز المفتوحة (للتحذير فقط)
                # ✅ FIX: user_trades لا يحتوي status='open' — استخدام active_positions WHERE is_active=1
                positions_query = """
                    SELECT COUNT(*) as count, SUM(COALESCE(quantity * entry_price, 0)) as locked_amount
                    FROM active_positions 
                    WHERE user_id = ? AND is_active = 1 AND is_demo = 0
                """
                positions_result = db.execute_query(positions_query, (user_id,))
                open_positions = positions_result[0]['count'] if positions_result else 0
                locked_amount = positions_result[0]['locked_amount'] or 0 if positions_result else 0

                # إذا كان هناك مراكز مفتوحة، نضيف تحذير (لكن نسمح بالتفعيل)
                if open_positions > 0:
                    logger.info(f"⚠️ المستخدم {user_id} يفعّل التداول مع {open_positions} مراكز مفتوحة (مبلغ مقفل: {locked_amount:.2f} USDT)")

                logger.info(f"✅ المستخدم {user_id}: تفعيل التداول - رصيد حر: {available_balance:.2f} USDT")

            # ✅ Validation لحد الخسارة اليومي (نظام هجين)
            max_daily_loss = data.get('maxDailyLoss', 10.0)
            if max_daily_loss is not None:
                # فرض الحدود من النظام (5%-15%)
                if max_daily_loss < 5.0:
                    logger.warning(f"⚠️ المستخدم {user_id}: حد الخسارة اليومي أقل من 5%، تم التعديل")
                    max_daily_loss = 5.0
                elif max_daily_loss > 15.0:
                    logger.warning(f"⚠️ المستخدم {user_id}: حد الخسارة اليومي أكبر من 15%، تم التعديل")
                    max_daily_loss = 15.0

            # ✅ تحديد المحفظة المستهدفة (للأدمن حسب trading_mode، للمستخدمين دائماً وهمية)
            user_query = "SELECT user_type FROM users WHERE id = ?"
            user_result = db.execute_query(user_query, (user_id,))
            is_admin = user_result[0]['user_type'] == 'admin' if user_result else False

            if is_admin:
                # جلب trading_mode الحالي لتحديد المحفظة المستهدفة
                mode_query = "SELECT trading_mode FROM user_settings WHERE user_id = ? LIMIT 1"
                mode_result = db.execute_query(mode_query, (user_id,))
                current_mode = mode_result[0]['trading_mode'] if mode_result else 'demo'

                if current_mode == 'demo':
                    target_is_demo = 1
                elif current_mode == 'real':
                    target_is_demo = 0
                else:  # auto
                    keys_query = "SELECT COUNT(*) as count FROM user_binance_keys WHERE user_id = ? AND is_active = 1"
                    keys_result = db.execute_query(keys_query, (user_id,))
                    has_keys = keys_result[0]['count'] > 0 if keys_result else False
                    target_is_demo = 0 if has_keys else 1
            else:
                target_is_demo = 0  # ✅ المستخدمون العاديون دائماً Real

            # فحص وجود إعدادات للمحفظة المستهدفة
            check_query = "SELECT id FROM user_settings WHERE user_id = ? AND is_demo = ?"
            existing = db.execute_query(check_query, (user_id, target_is_demo))

            if existing and len(existing) > 0:
                # تحديث الإعدادات الموجودة للمحفظة المستهدفة
                update_query = """
                    UPDATE user_settings
                    SET trading_enabled = ?, trade_amount = ?, position_size_percentage = ?,
                        risk_level = ?, stop_loss_pct = ?, take_profit_pct = ?,
                        trailing_distance = ?, max_positions = ?, max_daily_loss_pct = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND is_demo = ?
                """
                db.execute_query(update_query, (
                    data.get('tradingEnabled', False), data.get('tradeAmount', 100.0),
                    data.get('positionSizePercentage', 10.0),
                    data.get('riskLevel', 'medium'),
                    data.get('stopLossPercentage', 3.0), data.get('takeProfitPercentage', 6.0),
                    data.get('trailingDistance', 3.0),
                    data.get('maxConcurrentTrades', 5),
                    max_daily_loss, user_id, target_is_demo
                ))
            else:
                # إنشاء إعدادات جديدة للمحفظة المستهدفة
                insert_query = """
                    INSERT INTO user_settings (user_id, is_demo, trading_enabled, trade_amount,
                        position_size_percentage, stop_loss_pct, take_profit_pct, trailing_distance,
                        max_positions, risk_level, max_daily_loss_pct, trading_mode, 
                        created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
                db.execute_query(insert_query, (
                    user_id, target_is_demo, data.get('tradingEnabled', False), 
                    data.get('tradeAmount', 100.0), data.get('positionSizePercentage', 10.0),
                    data.get('stopLossPercentage', 3.0), data.get('takeProfitPercentage', 6.0),
                    data.get('trailingDistance', 3.0), data.get('maxConcurrentTrades', 5), 
                    data.get('riskLevel', 'medium'), max_daily_loss, data.get('tradingMode', 'auto')
                ))

            # ✅ إبطال Cache بعد التحديث - جميع بيانات المستخدم
            if CACHE_AVAILABLE:
                response_cache.invalidate_user_cache(user_id)
                logger.debug(f"🗑️ تم إبطال Cache الكامل - المستخدم {user_id}")

            return jsonify({
                'success': True, 
                'message': 'تم تحديث الإعدادات',
                'max_daily_loss_pct': max_daily_loss  # إرجاع القيمة المُعدلة
            })
        except Exception as e:
            error_str = str(e)
            logger.error(f"❌ خطأ Update Settings {user_id}: {error_str}")

            # ✅ معالجة خاصة لـ database is locked
            if 'database is locked' in error_str.lower():
                return jsonify({
                    'success': False, 
                    'error': 'النظام مشغول حالياً، يرجى المحاولة بعد قليل',
                    'error_code': 'DATABASE_BUSY',
                    'retry_after': 3
                }), 503

            return jsonify({'success': False, 'error': error_str}), 500


    @bp.route('/settings/trading-mode/<int:user_id>', methods=['GET'])
    @require_auth
    @rate_limit_general
    def get_trading_mode(user_id):
        """جلب وضع التداول الحالي - للأدمن فقط"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()

            # فحص نوع المستخدم
            user_query = "SELECT user_type FROM users WHERE id = ?"
            user_result = db.execute_query(user_query, (user_id,))

            if not user_result:
                return jsonify({'success': False, 'error': 'User not found'}), 404

            user_type = user_result[0]['user_type']
            is_admin = user_type == 'admin'

            # ✅ فقط الأدمن يستطيع جلب الوضع
            if not is_admin:
                return jsonify({
                    'success': False,
                    'error': 'Only admin can view trading mode'
                }), 403

            # جلب الوضع الحالي
            mode_query = "SELECT trading_mode FROM user_settings WHERE user_id = ? LIMIT 1"
            mode_result = db.execute_query(mode_query, (user_id,))
            current_mode = mode_result[0]['trading_mode'] if mode_result else 'auto'

            # فحص وجود مفاتيح Binance
            keys_query = "SELECT COUNT(*) as count FROM user_binance_keys WHERE user_id = ? AND is_active = 1"
            keys_result = db.execute_query(keys_query, (user_id,))
            has_keys = keys_result[0]['count'] > 0 if keys_result else False

            return jsonify({
                'success': True,
                'data': {
                    'tradingMode': current_mode,
                    'hasBinanceKeys': has_keys,
                    'canToggle': is_admin,
                    'availableModes': ['auto', 'demo', 'real']
                }
            })

        except Exception as e:
            logger.error(f"❌ خطأ في جلب trading_mode: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @bp.route('/settings/trading-mode/<int:user_id>', methods=['PUT'])
    @require_auth
    @rate_limit_trading
    def update_trading_mode(user_id):
        """تحديث وضع التداول (Toggle Mode) - للأدمن فقط"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        try:
            data = request.json
            new_mode = data.get('mode')

            # التحقق من صحة القيمة
            if new_mode not in ['auto', 'demo', 'real']:
                return jsonify({'success': False, 'error': 'Invalid mode. Must be: auto, demo, or real'}), 400

            from database.database_manager import DatabaseManager
            db = DatabaseManager()

            # فحص نوع المستخدم
            user_query = "SELECT user_type FROM users WHERE id = ?"
            user_result = db.execute_query(user_query, (user_id,))

            if not user_result:
                return jsonify({'success': False, 'error': 'User not found'}), 404

            user_type = user_result[0]['user_type']

            # ✅ فقط الأدمن يستطيع التبديل
            if user_type != 'admin':
                return jsonify({
                    'success': False,
                    'error': 'Only admin can toggle trading mode'
                }), 403

            # إذا كان real، تحقق من المفاتيح
            if new_mode == 'real':
                keys_query = "SELECT COUNT(*) as count FROM user_binance_keys WHERE user_id = ? AND is_active = 1"
                keys_result = db.execute_query(keys_query, (user_id,))
                has_keys = keys_result[0]['count'] > 0 if keys_result else False

                if not has_keys:
                    return jsonify({
                        'success': False,
                        'error': 'Real trading requires Binance API keys'
                    }), 400

            # جلب الوضع القديم (للـ audit log)
            old_settings_query = "SELECT trading_mode FROM user_settings WHERE user_id = ? LIMIT 1"
            old_result = db.execute_query(old_settings_query, (user_id,))
            old_mode = old_result[0]['trading_mode'] if old_result else 'auto'

            # ✅ تحديث الوضع في جميع إعدادات المستخدم
            # trading_mode يجب أن يكون متزامن في كلا الصفين
            update_query = """
                UPDATE user_settings
                SET trading_mode = ?, updated_at = datetime('now')
                WHERE user_id = ?
            """
            db.execute_query(update_query, (new_mode, user_id))

            # ✅ تسجيل في activity_logs (باستخدام audit_logger الموحد)
            if audit_logger:
                audit_logger.log(
                    action='trading_mode_change',
                    user_id=user_id,
                    details={'old_mode': old_mode, 'new_mode': new_mode}
                )

            # ✅ إبطال Cache لجميع البيانات المتأثرة
            if CACHE_AVAILABLE:
                # حذف cache keys الأساسية
                response_cache.delete(f"settings_{user_id}")
                response_cache.delete(f"portfolio_{user_id}")
                response_cache.delete(f"stats_{user_id}")
                response_cache.delete(f"trading_mode_{user_id}")

                # حذف جميع صفحات trades (متعدد الصفحات)
                # نحذف بـ pattern بدل حذف كل صفحة على حدة
                for page in range(1, 50):  # حد أقصى 50 صفحة
                    for limit in [10, 20, 50, 100, 200]:
                        for status in ['all', 'open', 'closed']:
                            cache_key = f"trades_{user_id}_{page}_{limit}_{status}_None_None"
                            try:
                                response_cache.delete(cache_key)
                            except Exception as e:
                                logger.debug(f"Cache delete skipped: {cache_key}")

                logger.debug(f"✅ تم إبطال cache لجميع البيانات للمستخدم {user_id}")

            logger.info(f"✅ الأدمن {user_id}: تبديل trading_mode من {old_mode} إلى {new_mode}")

            return jsonify({
                'success': True,
                'message': 'تم تحديث وضع التداول',
                'old_mode': old_mode,
                'new_mode': new_mode
            })

        except Exception as e:
            logger.error(f"❌ خطأ في تحديث trading_mode: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    # ==================== مفاتيح Binance ====================

    @bp.route('/binance-keys/<int:user_id>', methods=['GET'])
    @require_auth
    @rate_limit_general
    def get_binance_keys(user_id):
        """الحصول على مفاتيح Binance - بدون Secret (مع فك التشفير)"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()

            # جلب المفاتيح المشفرة
            keys_query = "SELECT id, api_key, is_active, created_at FROM user_binance_keys WHERE user_id = ? AND is_active = 1"
            result = db.execute_query(keys_query, (user_id,))

            if result and len(result) > 0:
                key = result[0]
                api_key_encrypted = key['api_key']

                # فك تشفير API Key للعرض (masked)
                if ENCRYPTION_AVAILABLE and api_key_encrypted:
                    try:
                        from config.security.encryption_service import decrypt_text
                        api_key_decrypted = decrypt_text(api_key_encrypted)
                        masked_key = api_key_decrypted[:8] + '...' + api_key_decrypted[-8:] if len(api_key_decrypted) > 16 else '***'
                    except Exception as decrypt_error:
                        logger.warning(f"⚠️ فشل فك التشفير، ربما مفتاح قديم غير مشفر: {decrypt_error}")
                        # إذا فشل فك التشفير، نفترض أنه غير مشفر (للتوافق مع البيانات القديمة)
                        masked_key = api_key_encrypted[:8] + '...' + api_key_encrypted[-8:] if len(api_key_encrypted) > 16 else '***'
                else:
                    masked_key = api_key_encrypted[:8] + '...' + api_key_encrypted[-8:] if api_key_encrypted and len(api_key_encrypted) > 16 else '***'

                return jsonify({'success': True, 'data': {
                    'hasKeys': True, 'keyId': key['id'], 'apiKey': masked_key,
                    'createdAt': key['created_at'], 'isActive': bool(key['is_active']),
                    'isConfigured': True
                }})
            else:
                return jsonify({'success': True, 'data': {
                    'hasKeys': False, 'keyId': None, 'apiKey': None, 'createdAt': None, 'isActive': False,
                    'isConfigured': False
                }})
        except Exception as e:
            logger.error(f"❌ خطأ Binance Keys {user_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @bp.route('/binance-keys', methods=['POST'])
    @require_auth
    @rate_limit_auth
    @prevent_concurrent_duplicates
    @require_idempotency('save_binance_keys')
    def save_binance_keys():
        """حفظ مفاتيح Binance - مع تشفير AES"""
        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            data = request.get_json()
            user_id = g.current_user_id

            # دعم جميع التنسيقات المحتملة من التطبيق
            api_key = data.get('apiKey') or data.get('api_key')
            api_secret = data.get('apiSecret') or data.get('api_secret') or data.get('secretKey') or data.get('secret_key')

            if not api_key or not api_secret:
                return error_response('بيانات المفاتيح مطلوبة', 'MISSING_CREDENTIALS', 400)

            # 🔒 فحص أمان المفتاح قبل الحفظ — منع المفاتيح ذات صلاحية السحب
            try:
                from binance.client import Client
                client = Client(api_key, api_secret)
                api_perms = client.get_api_key_permission()

                if api_perms.get('enableWithdrawals', False):
                    return jsonify({
                        'success': False,
                        'error': '🚨 المفتاح يملك صلاحية السحب!\n\n'
                                 'لحماية أموالك، يجب تعطيل Enable Withdrawals '
                                 'من إعدادات API في Binance قبل الحفظ.',
                        'error_code': 'WITHDRAWAL_ENABLED'
                    }), 400

                if not api_perms.get('ipRestrict', False):
                    logger.warning(f"⚠️ User {user_id} saving keys without IP restriction")
            except Exception as perm_error:
                logger.warning(f"⚠️ Could not verify key permissions before save: {perm_error}")

            # 🔒 FIX #5: ENFORCE encryption - no fallback allowed
            if not ENCRYPTION_AVAILABLE:
                logger.critical("❌ CRITICAL: Encryption service not available - cannot save keys")
                return jsonify({
                    'success': False,
                    'error': 'نظام التشفير غير متاح حالياً. يرجى المحاولة لاحقاً.',
                    'error_code': 'ENCRYPTION_UNAVAILABLE'
                }), 503

            # تشفير المفاتيح - إلزامي
            try:
                encrypted_key, encrypted_secret = encrypt_binance_keys(api_key, api_secret)
                logger.info(f"✅ تم تشفير مفاتيح Binance للمستخدم {user_id}")
            except Exception as encrypt_error:
                logger.error(f"❌ خطأ في التشفير: {encrypt_error}")
                return jsonify({
                    'success': False,
                    'error': 'فشل في تشفير المفاتيح',
                    'error_code': 'ENCRYPTION_FAILED'
                }), 500

            # حذف القديم وإضافة الجديد
            db.execute_query("UPDATE user_binance_keys SET is_active = 0 WHERE user_id = ?", (user_id,))
            db.execute_query(
                "INSERT INTO user_binance_keys (user_id, api_key, api_secret, is_active, created_at) VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)",
                (user_id, encrypted_key, encrypted_secret)
            )

            return success_response(
                {'encrypted': ENCRYPTION_AVAILABLE},
                'تم حفظ المفاتيح بشكل آمن',
                201
            )
        except Exception as e:
            logger.error(f"❌ خطأ Save Keys: {e}")
            return error_response('فشل في حفظ المفاتيح', 'SAVE_ERROR', 500)


    @bp.route('/binance-keys/<int:key_id>', methods=['DELETE'])
    @require_auth
    def delete_binance_key(key_id):
        """حذف مفتاح Binance - مع التحقق"""
        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            user_id = g.current_user_id

            check_query = "SELECT user_id FROM user_binance_keys WHERE id = ?"
            result = db.execute_query(check_query, (key_id,))

            if not result or result[0]['user_id'] != user_id:
                return error_response('لا توجد صلاحيات', 'UNAUTHORIZED', 403)

            db.execute_query("UPDATE user_binance_keys SET is_active = 0 WHERE id = ?", (key_id,))
            return success_response(None, 'تم حذف المفتاح')
        except Exception as e:
            logger.error(f"❌ خطأ Delete Key: {e}")
            return error_response('فشل في حذف المفتاح', 'DELETE_ERROR', 500)


    @bp.route('/binance-keys/validate', methods=['POST'])
    @require_auth
    def validate_binance_keys():
        """
        ✅ اختبار صحة مفاتيح Binance مع Binance API

        Request Body:
            {
                "apiKey": "...",
                "apiSecret": "..."
            }

        Response:
            {
                "success": true,
                "valid": true,
                "message": "المفاتيح صحيحة",
                "account_type": "spot",
                "can_trade": true
            }
        """
        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            user_id = g.current_user_id
            data = request.get_json()

            api_key = data.get('apiKey') or data.get('api_key')
            api_secret = data.get('apiSecret') or data.get('api_secret')

            if not api_key or not api_secret:
                return jsonify({
                    'success': False,
                    'valid': False,
                    'error': 'Missing API key or secret'
                }), 400

            # فك تشفير المفاتيح إذا كانت مشفرة
            if ENCRYPTION_AVAILABLE:
                try:
                    from config.security.encryption_service import decrypt_text
                    api_key_decrypted = decrypt_text(api_key) if len(api_key) > 50 else api_key
                    api_secret_decrypted = decrypt_text(api_secret) if len(api_secret) > 50 else api_secret
                except Exception as e:
                    logger.warning(f"⚠️ فشل فك تشفير المفاتيح، استخدام القيم الأصلية: {e}")
                    api_key_decrypted = api_key
                    api_secret_decrypted = api_secret
            else:
                api_key_decrypted = api_key
                api_secret_decrypted = api_secret

            # اختبار الاتصال مع Binance API
            try:
                from binance.client import Client
                from binance.exceptions import BinanceAPIException, BinanceRequestException

                client = Client(api_key_decrypted, api_secret_decrypted)

                # محاولة الحصول على معلومات الحساب
                account = client.get_account()

                # التحقق من الصلاحيات الأساسية
                can_trade = account.get('canTrade', False)
                can_withdraw = account.get('canWithdraw', False)
                account_type = 'spot'

                # ===== فحص صلاحيات المفتاح التفصيلية =====
                ip_restricted = False
                ip_list = []
                enable_withdrawals = can_withdraw
                enable_spot = can_trade
                security_warnings = []
                security_score = 100  # يبدأ من 100 وينقص مع كل مشكلة

                try:
                    api_restrictions = client.get_api_key_permission()
                    ip_restricted = api_restrictions.get('ipRestrict', False)
                    enable_withdrawals = api_restrictions.get('enableWithdrawals', False)
                    enable_spot = api_restrictions.get('enableSpotAndMarginTrading', False)
                    # enableInternalTransfer, enableFutures, etc.

                    if enable_withdrawals:
                        security_warnings.append({
                            'level': 'critical',
                            'message': 'صلاحية السحب مفعّلة! يجب تعطيلها لحماية أموالك',
                            'action': 'قم بتعطيل Enable Withdrawals من إعدادات API في Binance'
                        })
                        security_score -= 50

                    if not ip_restricted:
                        security_warnings.append({
                            'level': 'warning',
                            'message': 'المفتاح غير مقيّد بعنوان IP — أي جهاز يمكنه استخدامه',
                            'action': 'قم بإضافة IP السيرفر في Restrict access to trusted IPs only'
                        })
                        security_score -= 30

                    if not enable_spot:
                        security_warnings.append({
                            'level': 'info',
                            'message': 'صلاحية التداول غير مفعّلة',
                            'action': 'قم بتفعيل Enable Spot & Margin Trading'
                        })
                        security_score -= 20

                except Exception as perm_error:
                    logger.warning(f"⚠️ تعذر جلب صلاحيات المفتاح: {perm_error}")
                    security_warnings.append({
                        'level': 'info',
                        'message': 'تعذر التحقق من صلاحيات المفتاح التفصيلية',
                        'action': 'تحقق يدوياً من إعدادات API في Binance'
                    })

                security_score = max(0, security_score)

                logger.info(f"✅ مفاتيح Binance صحيحة للمستخدم {user_id} | "
                            f"withdraw={enable_withdrawals}, ip_restricted={ip_restricted}, "
                            f"security_score={security_score}")

                return jsonify({
                    'success': True,
                    'valid': True,
                    'message': 'المفاتيح صحيحة وتعمل بشكل صحيح',
                    'account_type': account_type,
                    'can_trade': can_trade,
                    'balances_count': len(account.get('balances', [])),
                    'security': {
                        'score': security_score,
                        'ip_restricted': ip_restricted,
                        'withdrawals_enabled': enable_withdrawals,
                        'spot_enabled': enable_spot,
                        'warnings': security_warnings,
                        'is_safe': security_score >= 70 and not enable_withdrawals
                    }
                })

            except BinanceAPIException as e:
                logger.warning(f"⚠️ خطأ Binance API للمستخدم {user_id}: {e}")
                return jsonify({
                    'success': False,
                    'valid': False,
                    'error': f'خطأ في Binance API: {str(e)}',
                    'error_code': e.status_code
                }), 400

            except BinanceRequestException as e:
                logger.warning(f"⚠️ خطأ في الاتصال بـ Binance للمستخدم {user_id}: {e}")
                return jsonify({
                    'success': False,
                    'valid': False,
                    'error': 'فشل الاتصال بـ Binance. تحقق من الاتصال بالإنترنت'
                }), 503

            except Exception as e:
                logger.error(f"❌ خطأ في اختبار المفاتيح للمستخدم {user_id}: {e}")
                return jsonify({
                    'success': False,
                    'valid': False,
                    'error': f'خطأ في الاختبار: {str(e)}'
                }), 500

        except Exception as e:
            logger.error(f"❌ خطأ Validate Keys: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    # ==================== الملف الشخصي ====================

    @bp.route('/profile/<int:user_id>', methods=['GET'])
    @require_auth
    @rate_limit_general
    def get_user_profile(user_id):
        """الحصول على الملف الشخصي"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()

            profile_query = "SELECT id, username, name, email, phone_number, user_type, is_active, created_at, last_login_at FROM users WHERE id = ?"
            result = db.execute_query(profile_query, (user_id,))

            if result and len(result) > 0:
                user = result[0]
                return jsonify({'success': True, 'data': {
                    'id': user['id'], 'username': user['username'], 'name': user['name'] or '',
                    'email': user['email'], 'phone_number': user['phone_number'] or '',
                    'user_type': user['user_type'], 'isActive': bool(user['is_active']),
                    'createdAt': user['created_at'], 'lastLogin': user['last_login_at']
                }})
            else:
                return jsonify({'success': False, 'error': 'User not found'}), 404
        except Exception as e:
            logger.error(f"❌ خطأ Profile {user_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @bp.route('/profile/<int:user_id>', methods=['PUT'])
    @require_auth
    @rate_limit_general
    @prevent_concurrent_duplicates
    @require_idempotency('update_profile')
    def update_user_profile(user_id):
        """تحديث الملف الشخصي"""
        if not verify_user_access(user_id):
            return error_response('لا توجد صلاحيات', 'UNAUTHORIZED', 403)

        try:
            data = request.get_json()

            if not data:
                return error_response('لا توجد بيانات', 'MISSING_DATA', 400)

            # ✅ استخدام get_write_connection لتجنب database lock
            with db_manager.get_write_connection() as conn:
                cursor = conn.cursor()

                # تحديث البيانات المتاحة فقط (بدون username)
                updates = []
                params = []

                if 'name' in data and data['name']:
                    updates.append("name = ?")
                    params.append(data['name'])
                if 'bio' in data and data['bio']:
                    updates.append("bio = ?")
                    params.append(data['bio'])
                if 'avatar' in data and data['avatar']:
                    updates.append("avatar = ?")
                    params.append(data['avatar'])
                if 'phone_number' in data and data['phone_number']:
                    updates.append("phone_number = ?")
                    params.append(data['phone_number'])

                if updates:
                    params.append(user_id)
                    query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
                    cursor.execute(query, params)

            return success_response(None, 'تم تحديث الملف الشخصي بنجاح')
        except Exception as e:
            logger.error(f"❌ خطأ Update Profile {user_id}: {e}")
            return error_response('خطأ في الخادم', 'INTERNAL_ERROR', 500)



    # ==================== إعادة ضبط البيانات ====================

    @bp.route('/reset-data/<int:user_id>', methods=['POST'])
    @require_auth
    @prevent_concurrent_duplicates
    @require_idempotency('reset_account')
    def reset_account_data(user_id):
        """
        إعادة ضبط بيانات الحساب (حذف الصفقات والإعدادات)
        ⚠️ عملية خطيرة - تتطلب تأكيد
        """
        if not verify_user_access(user_id):
            response_data, status_code = error_response('غير مصرح', 'UNAUTHORIZED', 403)
            return jsonify(response_data), status_code

        try:
            with db_manager.get_write_connection() as conn:
                # حذف الصفقات
                conn.execute("DELETE FROM user_trades WHERE user_id = ?", (user_id,))

                # حذف المراكز النشطة
                conn.execute("DELETE FROM active_positions WHERE user_id = ?", (user_id,))

                # إعادة ضبط المحفظة (استخدام الأعمدة الصحيحة)
                # ✅ FIX: الرصيد الافتراضي = 1000 USDT (يتطابق مع UI والتوثيق)
                conn.execute("""
                    UPDATE portfolio 
                    SET total_balance = 1000.0, available_balance = 1000.0, 
                        invested_balance = 0.0, total_profit_loss = 0.0, 
                        total_profit_loss_percentage = 0.0, initial_balance = 1000.0
                    WHERE user_id = ?
                """, (user_id,))

                # إعادة ضبط الإعدادات للقيم الافتراضية
                conn.execute("""
                    UPDATE user_settings 
                    SET trading_mode = 'demo', stop_loss_pct = 2.0, take_profit_pct = 5.0,
                        max_positions = 5, trading_enabled = 1
                    WHERE user_id = ?
                """, (user_id,))

                conn.commit()

            logger.info(f"✅ تم إعادة ضبط بيانات المستخدم {user_id}")
            response_data, status_code = success_response({'reset': True}, 'تم إعادة ضبط البيانات بنجاح')
            return jsonify(response_data), status_code

        except Exception as e:
            logger.error(f"❌ خطأ في إعادة ضبط البيانات: {e}")
            response_data, status_code = error_response('خطأ في إعادة ضبط البيانات', 'RESET_ERROR', 500)
            return jsonify(response_data), status_code


