"""
Database Trading Mixin — extracted from database_manager.py (God Object split)
===============================================================================
Methods: successful coins, active positions, signals, GroupB position management
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


class DbTradingMixin:
    """Trading-related database methods (coins, positions, signals)"""

    # ==================== العملات الناجحة ====================

    def save_successful_coins(self, coins_data):
        """حفظ العملات الناجحة مع الحفاظ على حد أقصى ثابت (25 عملة) - توازن بين التنويع والأداء"""
        normalized_new = self._normalize_coins_data(coins_data)
        
        if not normalized_new:
            self.logger.warning("لا توجد بيانات عملات للحفظ بعد التطبيع")
            return
        
        MAX_COINS = 25
        
        with self.get_write_connection() as conn:
            existing_rows = conn.execute("""
                SELECT symbol, score FROM successful_coins 
                WHERE is_active = 1
                ORDER BY score DESC
            """).fetchall()
            
            existing_symbols = {row[0]: row[1] for row in existing_rows}
            
            all_coins = {}
            for row in existing_rows:
                all_coins[row[0]] = {'score': row[1], 'source': 'existing'}
            
            for coin in normalized_new:
                symbol = coin['symbol']
                score = coin.get('score', 0)
                all_coins[symbol] = {'score': score, 'source': 'new', 'data': coin}
            
            sorted_coins = sorted(all_coins.items(), key=lambda x: x[1]['score'], reverse=True)
            top_coins = sorted_coins[:MAX_COINS]
            removed_coins = sorted_coins[MAX_COINS:]
            
            if removed_coins:
                removed_symbols = [c[0] for c in removed_coins]
                placeholders = ','.join(['?' for _ in removed_symbols])
                conn.execute(f"""
                    UPDATE successful_coins SET is_active = 0 
                    WHERE symbol IN ({placeholders})
                """, removed_symbols)
                self.logger.info(f"🔄 تم إلغاء تفعيل {len(removed_symbols)} عملة ضعيفة")
            
            for symbol, info in top_coins:
                if info['source'] == 'new':
                    coin_data = info['data']
                    self._insert_coin_data_direct(conn, coin_data)
            
            self.logger.info(f"✅ تم حفظ {len(top_coins)} عملة (الحد الأقصى: {MAX_COINS})")
            
            self._cleanup_old_records(conn)

    def _insert_coin_data(self, conn, symbol, data):
        """إدراج بيانات عملة واحدة في قاعدة البيانات"""
        try:
            score = float(data.get('score', 0))
            profit_pct = float(data.get('profit_pct', 0))
            win_rate = float(data.get('win_rate', 0))
            total_trades = int(data.get('total_trades', 0))
            
            conn.execute("""
                INSERT OR REPLACE INTO successful_coins 
                (symbol, strategy, timeframe, score, profit_pct, win_rate, 
                 total_trades, market_trend, analysis_date, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                str(symbol),
                str(data.get('strategy', 'unknown')),
                str(data.get('timeframe', '1h')),
                score,
                profit_pct,
                win_rate,
                total_trades,
                str(data.get('market_trend', 'neutral')),
                str(data.get('analysis_date', datetime.now().isoformat()))
            ))
        except (ValueError, TypeError) as e:
            self.logger.warning(f"تخطي العملة {symbol} بسبب خطأ في البيانات: {e}")

    def _normalize_coins_data(self, coins_data):
        """تطبيع بيانات العملات إلى تنسيق موحد"""
        normalized = []
        
        try:
            if isinstance(coins_data, dict):
                for symbol, data in coins_data.items():
                    if isinstance(data, dict):
                        normalized.append(self._normalize_single_coin(symbol, data))
            elif isinstance(coins_data, list):
                for item in coins_data:
                    if isinstance(item, dict):
                        symbol = item.get('symbol', 'UNKNOWN')
                        normalized.append(self._normalize_single_coin(symbol, item))
            
            return normalized
        except Exception as e:
            self.logger.error(f"خطأ في تطبيع بيانات العملات: {e}")
            return []

    def _normalize_single_coin(self, symbol, data):
        """تطبيع بيانات عملة واحدة"""
        return {
            'symbol': str(symbol),
            'strategy': str(data.get('strategy', 'unknown')),
            'timeframe': str(data.get('timeframe', '1h')),
            'score': float(data.get('score', 0)),
            'profit_pct': float(data.get('profit_pct', 0)),
            'win_rate': float(data.get('win_rate', 0)),
            'total_trades': int(data.get('total_trades', 0)),
            'market_trend': str(data.get('market_trend', 'neutral')),
            'analysis_date': str(data.get('analysis_date', datetime.now().isoformat())),
            'avg_trade_duration_hours': float(data.get('avg_trade_duration_hours', 0.0)),
            'trading_style': str(data.get('trading_style', 'swing'))
        }

    def _insert_coin_data_direct(self, conn, coin_data):
        """إدراج بيانات عملة مطبعة مباشرة في قاعدة البيانات"""
        try:
            conn.execute("""
                INSERT OR REPLACE INTO successful_coins 
                (symbol, strategy, timeframe, score, profit_pct, win_rate, 
                 total_trades, market_trend, analysis_date, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                coin_data['symbol'],
                coin_data['strategy'],
                coin_data['timeframe'],
                coin_data['score'],
                coin_data['profit_pct'],
                coin_data['win_rate'],
                coin_data['total_trades'],
                coin_data['market_trend'],
                coin_data['analysis_date']
            ))
        except Exception as e:
            self.logger.warning(f"تخطي العملة {coin_data.get('symbol', 'UNKNOWN')} بسبب خطأ في الإدراج: {e}")

    def get_successful_coins(self) -> List[Dict[str, Any]]:
        """الحصول على العملات الناجحة الحالية"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT symbol, strategy, timeframe, score, profit_pct, win_rate,
                       total_trades, market_trend, analysis_date, is_active
                FROM successful_coins 
                WHERE is_active = 1 
                ORDER BY score DESC
            """).fetchall()
            
            result = []
            for row in rows:
                result.append({
                    'symbol': row['symbol'],
                    'strategy': row['strategy'],
                    'timeframe': row['timeframe'],
                    'score': row['score'],
                    'profit_pct': row['profit_pct'],
                    'win_rate': row['win_rate'],
                    'total_trades': row['total_trades'],
                    'market_trend': row['market_trend'],
                    'analysis_date': row['analysis_date'],
                    'is_active': row['is_active']
                })
            
            return result

    def _cleanup_old_records(self, conn):
        """تنظيف السجلات القديمة من الجداول الأخرى للاحتفاظ بسجل واحد فقط"""
        try:
            try:
                conn.execute("""
                    DELETE FROM successful_coins 
                    WHERE is_active = 0 
                    AND datetime(analysis_date) < datetime('now', '-7 days')
                """)
            except Exception as e:
                self.logger.debug(f"ملاحظة في تنظيف successful_coins: {e}")
            
            try:
                conn.execute("""
                    DELETE FROM trading_signals 
                    WHERE is_processed = TRUE 
                    AND datetime(generated_at) < datetime('now', '-3 days')
                """)
            except Exception as e:
                self.logger.debug(f"ملاحظة في تنظيف trading_signals: {e}")
            
            try:
                conn.execute("""
                    DELETE FROM active_positions 
                    WHERE is_active = 0 
                    AND datetime(updated_at) < datetime('now', '-30 days')
                """)
            except Exception as e:
                self.logger.debug(f"ملاحظة في تنظيف active_positions: {e}")
                
            try:
                conn.execute("""
                    DELETE FROM activity_logs 
                    WHERE datetime(created_at) < datetime('now', '-30 days')
                """)
            except Exception as e:
                self.logger.debug(f"ملاحظة في تنظيف activity_logs: {e}")

        except Exception as e:
            self.logger.debug(f"ملاحظة في تنظيف السجلات القديمة: {e}")

    # ==================== إدارة الصفقات المفتوحة ====================

    def register_active_position(self, user_id: int, symbol: str, strategy: str, 
                               timeframe: str, position_type: str, entry_price: float = None,
                               quantity: float = None, stop_loss: float = None, 
                               take_profit: float = None, trailing_sl_price: float = None,
                               signal_metadata: str = None):
        """تسجيل صفقة مفتوحة جديدة"""
        try:
            with self.get_write_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO active_positions 
                    (user_id, symbol, strategy, timeframe, position_type, entry_date,
                     entry_price, quantity, stop_loss, take_profit, trailing_sl_price,
                     is_active, created_at, updated_at, signal_metadata)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, TRUE, 
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?)
                """, (user_id, symbol, strategy, timeframe, position_type,
                      entry_price, quantity, stop_loss, take_profit, trailing_sl_price,
                      signal_metadata))
                
                self.logger.info(f"تم تسجيل صفقة مفتوحة: {symbol} ({strategy}/{timeframe})")
                
        except Exception as e:
            self.logger.error(f"خطأ في تسجيل الصفقة المفتوحة: {e}")

    def close_active_position(self, user_id: int, symbol: str, strategy: str = None):
        """إغلاق صفقة مفتوحة"""
        try:
            with self.get_write_connection() as conn:
                if strategy:
                    conn.execute("""
                        UPDATE active_positions 
                        SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND symbol = ? AND strategy = ? AND is_active = TRUE
                    """, (user_id, symbol, strategy))
                else:
                    conn.execute("""
                        UPDATE active_positions 
                        SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND symbol = ? AND is_active = TRUE
                    """, (user_id, symbol))
                
                self.logger.info(f"تم إغلاق الصفقة: {symbol}")
                
        except Exception as e:
            self.logger.error(f"خطأ في إغلاق الصفقة: {e}")

    def update_position_trailing_sl(self, user_id: int, symbol: str, trailing_sl_price: float, strategy: str = None):
        """تحديث Trailing Stop Loss لصفقة مفتوحة"""
        try:
            with self.get_write_connection() as conn:
                if strategy:
                    conn.execute("""
                        UPDATE active_positions 
                        SET trailing_sl_price = ?, updated_at = ?
                        WHERE user_id = ? AND symbol = ? AND strategy = ? AND is_active = TRUE
                    """, (trailing_sl_price, datetime.now().isoformat(), user_id, symbol, strategy))
                else:
                    conn.execute("""
                        UPDATE active_positions 
                        SET trailing_sl_price = ?, updated_at = ?
                        WHERE user_id = ? AND symbol = ? AND is_active = TRUE
                    """, (trailing_sl_price, datetime.now().isoformat(), user_id, symbol))
                
        except Exception as e:
            self.logger.error(f"خطأ في تحديث Trailing SL: {e}")

    def get_active_positions_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        """الحصول على جميع الصفقات المفتوحة للمستخدم مع trailing_sl_price"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("""
                    SELECT * FROM active_positions 
                    WHERE user_id = ? AND is_active = TRUE
                    ORDER BY created_at DESC
                """, (user_id,)).fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"خطأ في جلب الصفقات المفتوحة: {e}")
            return []

    def get_active_positions(self, user_id: int) -> List[Dict[str, Any]]:
        """الحصول على جميع الصفقات المفتوحة للمستخدم"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("""
                    SELECT * FROM active_positions 
                    WHERE user_id = ? AND is_active = TRUE
                    ORDER BY created_at DESC
                """, (user_id,)).fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"خطأ في جلب الصفقات المفتوحة: {e}")
            return []

    def get_user_trades_paginated(self, user_id: int, limit: int = 50, offset: int = 0,
                                   status: str = 'all', date_from: str = None, 
                                   date_to: str = None, is_demo: Optional[int] = None) -> Dict[str, Any]:
        """جلب صفقات المستخدم مع Pagination"""
        try:
            limit = min(limit, 200)
            
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                
                where_clauses = ['user_id = ?']
                params = [user_id]
                
                if is_demo is not None:
                    where_clauses.append('is_demo = ?')
                    params.append(is_demo)
                
                if status != 'all':
                    where_clauses.append('status = ?')
                    params.append(status)
                
                if date_from:
                    where_clauses.append('entry_time >= ?')
                    params.append(date_from)
                
                if date_to:
                    where_clauses.append('entry_time <= ?')
                    params.append(date_to)
                
                where_sql = ' AND '.join(where_clauses)
                
                count_query = f"SELECT COUNT(*) FROM user_trades WHERE {where_sql}"
                total = conn.execute(count_query, params).fetchone()[0]
                
                query = f"""
                    SELECT * FROM user_trades 
                    WHERE {where_sql}
                    ORDER BY entry_time DESC
                    LIMIT ? OFFSET ?
                """
                params.extend([limit, offset])
                
                trades = conn.execute(query, params).fetchall()
                
                self.logger.debug(f"✅ Pagination: {len(trades)} trades (total: {total}, offset: {offset})")
                
                return {
                    'trades': [dict(trade) for trade in trades],
                    'total': total
                }
                
        except Exception as e:
            self.logger.error(f"خطأ في get_user_trades_paginated: {e}")
            return {'trades': [], 'total': 0}

    def get_coins_for_monitoring(self, user_id: int) -> List[Dict[str, Any]]:
        """الحصول على قائمة العملات للمراقبة (ناجحة + صفقات مفتوحة)"""
        try:
            successful_coins = self.get_successful_coins()
            active_positions = self.get_active_positions(user_id)
            
            all_symbols = {coin['symbol']: coin for coin in successful_coins}
            
            for pos in active_positions:
                symbol = pos['symbol']
                if symbol not in all_symbols:
                    all_symbols[symbol] = {
                        'symbol': symbol,
                        'strategy': pos['strategy'],
                        'timeframe': pos['timeframe'],
                        'profit_pct': 0.0,
                        'win_rate': 0.0,
                        'total_trades': 0,
                        'score': 0.0,
                        'market_trend': 'neutral',
                        'analysis_date': pos['created_at'],
                        'is_active': True,
                        'source': 'active_position'
                    }
                else:
                    all_symbols[symbol]['has_active_position'] = True
                    all_symbols[symbol]['original_strategy'] = pos['strategy']
                    all_symbols[symbol]['original_timeframe'] = pos['timeframe']
                    all_symbols[symbol]['position_entry_date'] = pos['created_at']
                    all_symbols[symbol]['active_strategy'] = pos['strategy']
                    all_symbols[symbol]['active_timeframe'] = pos['timeframe']
            
            result = list(all_symbols.values())
            
            self.logger.info(f"📊 قائمة المراقبة للمستخدم {user_id}: {len(result)} عملة "
                           f"({len(successful_coins)} ناجحة + {len(active_positions)} صفقة مفتوحة)")
            
            return result
            
        except Exception as e:
            self.logger.error(f"خطأ في إنشاء قائمة المراقبة: {e}")
            return self.get_successful_coins()

    def cleanup_old_positions(self, days: int = 30):
        """تنظيف الصفقات المغلقة القديمة"""
        try:
            with self.get_write_connection() as conn:
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                result = conn.execute("""
                    DELETE FROM active_positions 
                    WHERE is_active = FALSE AND updated_at < ?
                """, (cutoff_date,))
                
                deleted_count = result.rowcount
                if deleted_count > 0:
                    self.logger.info(f"🧹 تم حذف {deleted_count} صفقة مغلقة قديمة")
                    
        except Exception as e:
            self.logger.error(f"خطأ في تنظيف الصفقات القديمة: {e}")

    # ==================== الإشارات الحالية ====================

    def save_current_signals(self, signals: List[Dict[str, Any]]):
        """حفظ الإشارات الحالية من المجموعة B"""
        with self.get_write_connection() as conn:
            for signal in signals:
                conn.execute("""
                    INSERT OR REPLACE INTO trading_signals 
                    (symbol, strategy, timeframe, signal_type, price, confidence, generated_at, is_processed)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, FALSE)
                """, (
                    signal['symbol'],
                    signal['strategy'],
                    signal['timeframe'],
                    signal['signal_type'],
                    signal['price'],
                    signal.get('confidence', 0.0)
                ))
        
        self.logger.info(f"تم حفظ {len(signals)} إشارة")

    def get_unprocessed_signals(self, user_id: int) -> List[Dict[str, Any]]:
        """الحصول على الإشارات غير المعالجة لمستخدم معين"""
        with self.get_connection() as conn:
            settings = conn.execute("""
                SELECT trading_enabled, max_positions FROM user_settings WHERE user_id = ?
            """, (user_id,)).fetchone()
            
            if not settings or not settings['trading_enabled']:
                return []
            
            active_trades = conn.execute("""
                SELECT COUNT(*) as count FROM user_trades 
                WHERE user_id = ? AND status = 'active'
            """, (user_id,)).fetchone()['count']
            
            if active_trades >= settings['max_positions']:
                return []
            
            rows = conn.execute("""
                SELECT * FROM trading_signals 
                WHERE is_processed = FALSE 
                ORDER BY generated_at DESC
            """).fetchall()
            
            return [dict(row) for row in rows]

    def mark_signal_processed(self, signal_id: int):
        """تحديد إشارة كمعالجة"""
        with self.get_write_connection() as conn:
            conn.execute("""
                UPDATE trading_signals SET is_processed = TRUE WHERE id = ?
            """, (signal_id,))

    # ==================== دوال GroupBSystem ====================

    def get_user_active_positions(self, user_id: int, is_demo: bool = None) -> List[Dict[str, Any]]:
        """جلب الصفقات المفتوحة للمستخدم حسب الوضع"""
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT * FROM active_positions 
                    WHERE user_id = ? AND is_active = 1
                """
                params = [user_id]
                
                if is_demo is not None:
                    query += " AND is_demo = ?"
                    params.append(1 if is_demo else 0)
                
                query += " ORDER BY created_at DESC"
                
                rows = conn.execute(query, params).fetchall()
                
                return [dict(row) for row in rows] if rows else []
        except Exception as e:
            self.logger.error(f"خطأ في جلب الصفقات المفتوحة: {e}")
            return []

    def add_position(self, user_id: int, symbol: str, entry_price: float,
                    quantity: float, position_size: float, signal_type: str,
                    is_demo: int = 1, order_id: str = None,
                    position_type: str = 'long', stop_loss_price: float = None,
                    take_profit_price: float = None, timeframe: str = '1h',
                    signal_metadata: str = None) -> Optional[int]:
        """إضافة صفقة جديدة"""
        try:
            if stop_loss_price is None:
                if position_type == 'short':
                    stop_loss_price = entry_price * 1.01
                else:
                    stop_loss_price = entry_price * 0.99
            
            # ✅ FIX: لا نضع TP افتراضي — V7 يستخدم trailing-only بدون TP ثابت
            # إذا لم يُحدد TP، يبقى 0 (الخروج يعتمد على trailing/SL فقط)
            if take_profit_price is None:
                take_profit_price = 0
            
            entry_commission = 0
            if is_demo == 1:
                entry_commission = position_size * 0.001
            
            with self.get_write_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO active_positions 
                    (user_id, symbol, entry_price, quantity, strategy,
                     stop_loss, take_profit, is_demo, order_id, entry_commission,
                     position_size, position_type, timeframe, entry_date, 
                     is_active, created_at, highest_price, signal_metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 1, CURRENT_TIMESTAMP, ?, ?)
                """, (user_id, symbol, entry_price, quantity, signal_type, 
                      stop_loss_price, take_profit_price, is_demo, order_id, 
                      entry_commission, position_size, position_type, timeframe,
                      entry_price, signal_metadata))
                
                # get_write_connection يعمل commit تلقائياً
                self.logger.info(f"تم فتح صفقة {position_type.upper()}: {symbol} للمستخدم {user_id}")
                return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"خطأ في فتح صفقة: {e}")
            return None

    def close_position(self, position_id: int, exit_price: float,
                      exit_reason: str, pnl: float, exit_commission: float = 0,
                      exit_order_id: str = None) -> bool:
        """إغلاق صفقة"""
        try:
            with self.get_write_connection() as conn:
                position = conn.execute(
                    "SELECT * FROM active_positions WHERE id = ?", (position_id,)
                ).fetchone()
                
                conn.execute("""
                    UPDATE active_positions 
                    SET is_active = 0, exit_price = ?, exit_reason = ?,
                        profit_loss = ?, exit_commission = ?, exit_order_id = ?,
                        closed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (exit_price, exit_reason, pnl, exit_commission, exit_order_id, position_id))
                
                if position:
                    pos = dict(position)
                    entry_price = pos.get('entry_price', 0)
                    quantity = pos.get('quantity', 0)
                    initial_investment = entry_price * quantity
                    pnl_pct = (pnl / initial_investment * 100) if initial_investment > 0 else 0
                    
                    conn.execute("""
                        INSERT INTO user_trades 
                        (user_id, symbol, strategy, timeframe, side, entry_price, quantity,
                         stop_loss, take_profit, status, is_demo, entry_time,
                         exit_price, profit_loss, profit_loss_percentage, exit_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'closed', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        pos.get('user_id'),
                        pos.get('symbol'),
                        pos.get('strategy', 'SCALP_V7'),
                        pos.get('timeframe', '1h'),
                        pos.get('position_type', 'long').upper(),
                        entry_price,
                        quantity,
                        pos.get('stop_loss'),
                        pos.get('take_profit'),
                        pos.get('is_demo', 1),
                        pos.get('created_at'),
                        exit_price,
                        pnl,
                        pnl_pct,
                    ))
                
                conn.commit()
                self.logger.info(f"تم إغلاق الصفقة {position_id}: {exit_reason} (synced to user_trades)")
                return True
        except Exception as e:
            self.logger.error(f"خطأ في إغلاق صفقة: {e}")
            return False

    def update_user_balance(self, user_id: int, new_balance: float, is_demo: bool = True) -> bool:
        """تحديث رصيد المحفظة للمستخدم"""
        try:
            is_demo_int = 1 if is_demo else 0
            with self.get_write_connection() as conn:
                invested_row = conn.execute("""
                    SELECT COALESCE(SUM(position_size), 0) as invested
                    FROM active_positions
                    WHERE user_id = ? AND is_active = 1 AND is_demo = ?
                """, (user_id, is_demo_int)).fetchone()
                invested_balance = invested_row[0] if invested_row else 0
                
                total_balance = new_balance + invested_balance
                
                conn.execute("""
                    UPDATE portfolio 
                    SET total_balance = ?, available_balance = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND is_demo = ?
                """, (total_balance, new_balance, user_id, is_demo_int))
                
                return True
        except Exception as e:
            self.logger.error(f"خطأ في تحديث رصيد المستخدم {user_id}: {e}")
            return False

    def update_position_trailing_stop(self, position_id: int, new_price: float) -> bool:
        """تحديث Trailing Stop"""
        try:
            with self.get_write_connection() as conn:
                conn.execute("""
                    UPDATE active_positions 
                    SET trailing_sl_price = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_price, position_id))
                
                # get_write_connection يعمل commit تلقائياً
                return True
        except Exception as e:
            self.logger.error(f"خطأ في تحديث Trailing Stop: {e}")
            return False
