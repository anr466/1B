"""
Database Portfolio Mixin — extracted from database_manager.py (God Object split)
================================================================================
Methods: portfolio CRUD, trades, PnL calculation, Binance keys, demo reset
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.utils.trading_context import get_effective_is_demo, is_admin_user


class DbPortfolioMixin:
    """Portfolio-related database methods (portfolio, trades, Binance keys)"""

    # ==================== المحفظة والصفقات المحسنة ====================

    def sync_portfolio_data(self, user_id: int) -> Dict[str, Any]:
        """مزامنة بيانات المحفظة وحساب القيم المحدثة"""
        try:
            with self.get_write_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        p.total_balance,
                        COALESCE(SUM(CASE WHEN t.status = 'open' THEN t.quantity * t.entry_price ELSE 0 END), 0) as invested_amount
                    FROM portfolio p
                    LEFT JOIN active_positions t ON p.user_id = t.user_id AND t.is_active = 1
                    WHERE p.user_id = ?
                    GROUP BY p.user_id, p.total_balance
                """, (user_id,))
                
                result = cursor.fetchone()
                if result:
                    total_balance = float(result[0])
                    invested_amount = float(result[1])
                    available_balance = total_balance - invested_amount
                    
                    try:
                        updated = conn.execute(
                            """
                            UPDATE portfolio
                            SET invested_balance = ?, available_balance = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = ?
                            """,
                            (invested_amount, available_balance, user_id),
                        )

                        if updated.rowcount == 0:
                            conn.execute(
                                """
                                INSERT INTO portfolio (
                                    user_id, is_demo, total_balance, available_balance,
                                    invested_balance, initial_balance, updated_at
                                )
                                VALUES (?, FALSE, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                                """,
                                (user_id, total_balance, available_balance, invested_amount, total_balance),
                            )
                        
                        self.logger.info(f"تم إعادة ضبط رصيد المحفظة إلى $1000 للمستخدم {user_id}")
                        try:
                            from backend.utils.simple_cache import response_cache
                            response_cache.invalidate_user_cache(user_id)
                        except Exception:
                            pass
                    except Exception as e:
                        self.logger.warning(f"خطأ في إعادة ضبط المحفظة: {e}")
                return {}
        except Exception as e:
            self.logger.error(f"خطأ في مزامنة بيانات المحفظة للمستخدم {user_id}: {e}")
            return {}

    def update_user_portfolio(self, user_id: int, is_demo: int = None, **updates):
        """تحديث محفظة المستخدم حسب الوضع"""
        if is_demo is None:
            is_demo = get_effective_is_demo(self, user_id)
        
        with self.get_write_connection() as conn:
            update_fields = ["updated_at = CURRENT_TIMESTAMP"]
            values = []
            mapped_updates = {}
            
            field_mapping = {
                'balance': 'total_balance',
                'totalBalance': 'total_balance',
                'total_balance': 'total_balance',
                'availableBalance': 'available_balance',
                'available_balance': 'available_balance',
                'totalProfitLoss': 'total_profit_loss',
                'total_profit_loss': 'total_profit_loss',
                'total_profit_loss_percentage': 'total_profit_loss_percentage',
                'invested_balance': 'invested_balance',
                'total_trades': 'total_trades',
                'winning_trades': 'winning_trades',
                'losing_trades': 'losing_trades',
            }
            
            for key, value in updates.items():
                target = field_mapping.get(key)
                if target:
                    mapped_updates[target] = value

            for field_name, field_value in mapped_updates.items():
                update_fields.append(f"{field_name} = ?")
                values.append(field_value)
            
            if values:
                values.extend([user_id, bool(is_demo)])
                query = f"UPDATE portfolio SET {', '.join(update_fields)} WHERE user_id = ? AND is_demo = ?"
                conn.execute(query, values)
                try:
                    from backend.utils.simple_cache import response_cache
                    response_cache.invalidate_user_cache(user_id)
                except Exception:
                    pass

    def add_user_trade(self, user_id: int, trade_data: Dict[str, Any], is_demo: int = None) -> int:
        """إضافة صفقة جديدة للمستخدم حسب الوضع"""
        if is_demo is None:
            is_demo = get_effective_is_demo(self, user_id)
        is_demo = bool(is_demo)
        
        with self.get_write_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO active_positions 
                (user_id, symbol, strategy, timeframe, side, entry_price, quantity, 
                 stop_loss, take_profit, is_active, is_demo, entry_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE, ?, CURRENT_TIMESTAMP)
            """, (
                user_id,
                trade_data['symbol'],
                trade_data['strategy'],
                trade_data['timeframe'],
                trade_data['side'],
                trade_data['entry_price'],
                trade_data['quantity'],
                trade_data.get('stop_loss'),
                trade_data.get('take_profit'),
                is_demo
            ))
            
            trade_id = cursor.lastrowid
            mode_text = 'وهمية' if is_demo else 'حقيقية'
            self.logger.info(f"تم إضافة صفقة {mode_text} {trade_id} للمستخدم {user_id}")
            return trade_id

    def save_trade(self, user_id: int, symbol: str, side: str, quantity: float, price: float, **kwargs) -> int:
        """حفظ صفقة جديدة - alias لـ add_user_trade"""
        trade_data = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'entry_price': price,
            'strategy': kwargs.get('strategy', 'manual'),
            'timeframe': kwargs.get('timeframe', '1h'),
            'stop_loss': kwargs.get('stop_loss'),
            'take_profit': kwargs.get('take_profit')
        }
        return self.add_user_trade(user_id, trade_data)

    def get_open_trades(self, user_id: int) -> List[Dict[str, Any]]:
        """جلب الصفقات المفتوحة للمستخدم — يقرأ من active_positions"""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT
                    id, user_id, symbol, strategy, is_demo,
                    entry_price, exit_price, quantity,
                    profit_loss,
                    profit_pct AS profit_loss_percentage,
                    'open' AS status,
                    COALESCE(entry_date, created_at) AS entry_time,
                    closed_at AS exit_time,
                    CASE WHEN position_type IN ('long', 'LONG') THEN 'buy' ELSE 'sell' END AS side,
                    stop_loss, take_profit, created_at
                FROM active_positions
                WHERE user_id = ? AND is_active = 1
                ORDER BY COALESCE(entry_date, created_at) DESC
            """, (user_id,)).fetchall()
            
            return [dict(row) for row in rows]

    def close_user_trade(self, trade_id: int, exit_price: float, profit_loss: float):
        """إغلاق صفقة المستخدم"""
        with self.get_write_connection() as conn:
            trade = conn.execute("""
                SELECT entry_price, quantity FROM active_positions WHERE id = ?
            """, (trade_id,)).fetchone()
            
            if trade:
                entry_price, quantity = trade
                initial_investment = entry_price * quantity
                profit_loss_percentage = (profit_loss / initial_investment * 100) if initial_investment > 0 else 0
            else:
                profit_loss_percentage = 0
            
            conn.execute("""
                UPDATE active_positions 
                SET exit_price = ?, profit_loss = ?, profit_pct = ?, 
                    is_active = FALSE, closed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                exit_price,
                profit_loss,
                profit_loss_percentage,
                trade_id
            ))
            
            self.logger.info(f"تم إغلاق الصفقة {trade_id} بنسبة {profit_loss_percentage:.2f}%")

    def reset_user_portfolio(self, user_id: int, initial_balance: float = 0.0) -> bool:
        """إعادة ضبط الحساب التجريبي - مسح جميع البيانات وإعادة تعيين الرصيد"""
        try:
            with self.get_write_connection() as conn:
                conn.execute("DELETE FROM active_positions WHERE user_id = ? AND is_demo = TRUE", (user_id,))
                self.logger.info(f"تم مسح صفقات الحساب التجريبي للمستخدم {user_id})")
                
                conn.execute("DELETE FROM user_binance_orders WHERE user_id = ? AND is_demo = TRUE", (user_id,))
                self.logger.info(f"تم مسح أوامر Binance التجريبية للمستخدم {user_id}")
                
                try:
                    conn.execute("DELETE FROM user_binance_balance WHERE user_id = ?", (user_id,))
                    self.logger.info(f"تم مسح user_binance_balance للمستخدم {user_id}")
                except Exception as e:
                    self.logger.warning(f"جدول user_binance_balance غير موجود: {e}")
                
                try:
                    conn.execute("DELETE FROM user_binance_balances WHERE user_id = ?", (user_id,))
                    self.logger.info(f"تم مسح user_binance_balances للمستخدم {user_id}")
                except Exception as e:
                    self.logger.warning(f"جدول user_binance_balances غير موجود: {e}")
                
                try:
                    conn.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
                    self.logger.info(f"تم مسح إشعارات المستخدم {user_id}")
                except Exception as e:
                    self.logger.warning(f"جدول notifications غير موجود: {e}")
                
                try:
                    conn.execute("DELETE FROM notification_history WHERE user_id = ?", (user_id,))
                    self.logger.info(f"تم مسح سجل الإشعارات للمستخدم {user_id}")
                except Exception as e:
                    self.logger.warning(f"جدول notification_history غير موجود: {e}")
                
                try:
                    conn.execute("DELETE FROM activity_logs WHERE user_id = ?", (user_id,))
                    self.logger.info(f"تم مسح سجل الأنشطة للمستخدم {user_id}")
                except Exception as e:
                    self.logger.warning(f"جدول activity_logs غير موجود: {e}")
                
                portfolio_row = conn.execute("""
                    SELECT initial_balance FROM portfolio WHERE user_id = ? AND is_demo = TRUE LIMIT 1
                """, (user_id,)).fetchone()
                resolved_initial_balance = float(portfolio_row[0] or initial_balance or 0.0) if portfolio_row else float(initial_balance or 0.0)
                conn.execute("""
                    INSERT OR REPLACE INTO portfolio 
                    (user_id, is_demo, total_balance, available_balance, invested_balance,
                     total_profit_loss, total_profit_loss_percentage, initial_balance, updated_at)
                    VALUES (?, TRUE, ?, ?, 0.0, 0.0, 0.0, ?, CURRENT_TIMESTAMP)
                """, (user_id, resolved_initial_balance, resolved_initial_balance, resolved_initial_balance))
                
                conn.execute("""
                    INSERT OR REPLACE INTO user_settings 
                    (user_id, is_demo, trade_amount, max_positions, risk_level, stop_loss_pct,
                     take_profit_pct, trailing_distance, position_size_percentage, trading_enabled,
                     max_daily_loss_pct, daily_loss_limit, trading_mode, updated_at)
                    VALUES (?, TRUE, 100.00, 5, 'medium', 3.00, 6.00, 3.00, 10.00, FALSE, 10.00, 100.00, 'demo', CURRENT_TIMESTAMP)
                """, (user_id,))
                
                self.logger.info(f"تم إعادة ضبط الحساب التجريبي للمستخدم {user_id} بنجاح - الرصيد: {resolved_initial_balance}$")
                return True
                
        except Exception as e:
            self.logger.error(f"خطأ في إعادة ضبط الحساب التجريبي للمستخدم {user_id}: {e}")
            return False

    def get_user_trades_simple(self, user_id: int, status: Optional[str] = None, is_demo: Optional[int] = None) -> List[Dict[str, Any]]:
        """الحصول على صفقات المستخدم — يقرأ من active_positions (المصدر الوحيد للبيانات)"""
        with self.get_connection() as conn:
            conditions = ["user_id = ?"]
            params = [user_id]
            
            if status == 'open':
                conditions.append("is_active = 1")
            elif status == 'closed':
                conditions.append("is_active = 0")
            
            if is_demo is not None:
                conditions.append("is_demo = ?")
                params.append(is_demo)
            
            query = f"""
                SELECT
                    id, user_id, symbol, strategy, is_demo,
                    entry_price, exit_price, quantity,
                    profit_loss,
                    profit_pct AS profit_loss_percentage,
                    CASE WHEN is_active = 1 THEN 'open' ELSE 'closed' END AS status,
                    COALESCE(entry_date, created_at) AS entry_time,
                    closed_at AS exit_time,
                    CASE WHEN position_type IN ('long', 'LONG') THEN 'buy' ELSE 'sell' END AS side,
                    stop_loss, take_profit, created_at
                FROM active_positions
                WHERE {' AND '.join(conditions)}
                ORDER BY COALESCE(entry_date, created_at) DESC
            """
            
            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(row) for row in rows]

    # ==================== المحفظة والإحصائيات ====================

    def _format_currency(self, value: float) -> str:
        """تنسيق القيمة المالية بفواصل الآلاف"""
        return f"{value:,.2f}"

    def get_user_portfolio(self, user_id: int, is_demo: Optional[int] = None) -> Dict[str, Any]:
        """الحصول على بيانات المحفظة حسب الوضع"""
        try:
            user_data = self.get_user_by_id(user_id)
            if not user_data:
                return {'error': True, 'message': 'المستخدم غير موجود'}
            
            is_admin = is_admin_user(self, user_id)
            
            if is_admin:
                if is_demo is None:
                    is_demo = get_effective_is_demo(self, user_id)

                # ✅ الأدمن الحقيقي = نفس مسار المستخدم الحقيقي (Binance live)
                if is_demo == 0:
                    return self._get_binance_portfolio(user_id)

                return self._get_admin_portfolio(user_id, is_demo)
            
            return self._get_binance_portfolio(user_id)
                    
        except Exception as e:
            self.logger.error(f"خطأ في جلب بيانات المحفظة: {e}")
            return {'error': True, 'message': str(e)}

    def _get_binance_portfolio(self, user_id: int) -> Dict[str, Any]:
        """جلب محفظة حقيقية من Binance API مع حساب الأرباح"""
        keys = self.get_binance_keys(user_id)
        if not keys:
            return {
                'hasKeys': False,
                'error': False,
                'message': '🔑 يرجى إضافة مفاتيح Binance لعرض محفظتك والبدء في التداول',
                'action': 'ADD_BINANCE_KEYS',
                'totalBalance': '0.00',
                'availableBalance': '0.00',
                'investedBalance': '0.00',
                'totalProfitLoss': '+0.00',
                'totalProfitLossPercentage': '+0.00',
                'currency': 'USD'
            }
        
        try:
            from backend.utils.binance_manager import BinanceManager
            binance_mgr = BinanceManager()
            
            sync_result = binance_mgr.sync_user_balance(user_id)
            
            if sync_result:
                balance_data = binance_mgr.get_user_real_balance(user_id)
                
                if balance_data.get('success'):
                    total_usdt = balance_data.get('total_usdt', 0)
                    
                    pnl_data = self._calculate_user_pnl(user_id)
                    system_total_pnl = float(pnl_data.get('total_pnl', 0) or 0)
                    has_system_activity = (pnl_data.get('trades_count', 0) or 0) > 0 or (pnl_data.get('active_trades', 0) or 0) > 0
                    baseline_balance = total_usdt if not has_system_activity else max(total_usdt - system_total_pnl, 0)
                    initial_balance = self._get_or_set_initial_balance(user_id, baseline_balance, has_system_activity)

                    # ✅ النمو للحقيقي يعتمد فقط على صفقات النظام (وليس تغيرات خارجية في محفظة Binance)
                    total_growth = system_total_pnl
                    total_growth_pct = (total_growth / initial_balance * 100) if initial_balance > 0 else 0
                    
                    return {
                        'hasKeys': True,
                        'totalBalance': self._format_currency(total_usdt),
                        'balance': total_usdt,
                        'availableBalance': self._format_currency(total_usdt),
                        'investedBalance': self._format_currency(pnl_data['invested']),
                        'initialBalance': self._format_currency(initial_balance),
                        'dailyPnL': f"{pnl_data['daily_pnl']:+,.2f}",
                        'dailyPnLPercentage': f"{pnl_data['daily_pnl_pct']:+.2f}",
                        'totalPnL': f"{pnl_data['total_pnl']:+,.2f}",
                        'totalPnLPercentage': f"{pnl_data['total_pnl_pct']:+.2f}",
                        'totalProfitLoss': f"{pnl_data['total_pnl']:+,.2f}",
                        'totalProfitLossPercentage': f"{pnl_data['total_pnl_pct']:+.2f}",
                        'portfolioGrowth': f"{total_growth:+,.2f}",
                        'portfolioGrowthPercentage': f"{total_growth_pct:+.2f}",
                        'investedAmount': self._format_currency(pnl_data['invested']),
                        'tradesCount': pnl_data['trades_count'],
                        'winRate': f"{pnl_data['win_rate']:.1f}%",
                        'currency': 'USD',
                        'source': 'binance_live',
                        'lastUpdate': datetime.now().isoformat()
                    }
            
            return {
                'hasKeys': True,
                'error': True,
                'message': 'فشل في جلب البيانات من Binance - تحقق من المفاتيح'
            }
        
        except Exception as e:
            self.logger.error(f"خطأ في الاتصال بـ Binance: {e}")
            return {
                'hasKeys': True,
                'error': True,
                'message': f'خطأ في الاتصال بـ Binance: {str(e)}'
            }

    def _calculate_user_pnl(self, user_id: int) -> Dict[str, Any]:
        """حساب الأرباح والخسائر من صفقات المستخدم"""
        try:
            with self.get_connection() as conn:
                total_result = conn.execute("""
                    SELECT
                        COALESCE(SUM(CASE WHEN is_active = 0 THEN profit_loss ELSE 0 END), 0) as total_pnl,
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN is_active = 0 AND profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                        (
                            SELECT COALESCE(SUM(position_size), 0)
                            FROM active_positions ap
                            WHERE ap.user_id = ? AND ap.is_active = 1 AND ap.is_demo = 0
                        ) as invested
                    FROM active_positions
                    WHERE user_id = ? AND is_demo = 0
                """, (user_id, user_id)).fetchone()
                
                daily_result = conn.execute("""
                    SELECT COALESCE(SUM(profit_loss), 0) as daily_pnl
                    FROM active_positions
                    WHERE user_id = ? AND is_demo = 0
                    AND is_active = 0
                    AND DATE(closed_at) = DATE('now')
                """, (user_id,)).fetchone()

                active_result = conn.execute("""
                    SELECT COUNT(*) as active_trades
                    FROM active_positions
                    WHERE user_id = ? AND is_demo = 0 AND is_active = 1
                """, (user_id,)).fetchone()
                
                total_pnl = total_result[0] if total_result else 0
                total_trades = total_result[1] if total_result else 0
                winning_trades = total_result[2] if total_result else 0
                invested = total_result[3] if total_result else 0
                daily_pnl = daily_result[0] if daily_result else 0
                active_trades = active_result[0] if active_result else 0
                
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                total_pnl_pct = (total_pnl / invested * 100) if invested > 0 else 0
                daily_pnl_pct = (daily_pnl / invested * 100) if invested > 0 else 0
                
                return {
                    'total_pnl': total_pnl,
                    'total_pnl_pct': total_pnl_pct,
                    'daily_pnl': daily_pnl,
                    'daily_pnl_pct': daily_pnl_pct,
                    'trades_count': total_trades,
                    'winning_trades': winning_trades,
                    'win_rate': win_rate,
                    'invested': invested,
                    'active_trades': active_trades
                }
        except Exception as e:
            self.logger.error(f"خطأ في حساب الأرباح: {e}")
            return {
                'total_pnl': 0, 'total_pnl_pct': 0,
                'daily_pnl': 0, 'daily_pnl_pct': 0,
                'trades_count': 0, 'winning_trades': 0,
                'win_rate': 0, 'invested': 0, 'active_trades': 0
            }

    def _get_or_set_initial_balance(self, user_id: int, current_balance: float, has_system_activity: bool) -> float:
        """جلب أو تعيين baseline النمو للحساب الحقيقي من أول تداول داخل النظام فقط"""
        try:
            with self.get_write_connection() as conn:
                result = conn.execute("""
                    SELECT initial_balance FROM portfolio
                    WHERE user_id = ? AND is_demo = FALSE
                """, (user_id,)).fetchone()
                
                if result and result[0] and result[0] > 0:
                    return result[0]

                # قبل أول تداول داخل النظام: baseline = الرصيد الحالي (بدون احتساب نمو)
                if not has_system_activity:
                    return current_balance if current_balance > 0 else 0

                if current_balance > 0:
                    updated = conn.execute(
                        """
                        UPDATE portfolio
                        SET initial_balance = CASE
                                WHEN initial_balance IS NULL OR initial_balance = 0 THEN ?
                                ELSE initial_balance
                            END,
                            total_balance = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND is_demo = FALSE
                        """,
                        (current_balance, current_balance, user_id),
                    )

                    if updated.rowcount == 0:
                        conn.execute(
                            """
                            INSERT INTO portfolio (user_id, total_balance, available_balance, initial_balance, is_demo, updated_at)
                            VALUES (?, ?, ?, ?, FALSE, CURRENT_TIMESTAMP)
                            """,
                            (user_id, current_balance, current_balance, current_balance),
                        )
                    return current_balance
                
                return 0
        except Exception as e:
            self.logger.error(f"خطأ في جلب الرصيد الابتدائي: {e}")
            return 0

    def _get_admin_portfolio(self, user_id: int, is_demo: int) -> Dict[str, Any]:
        """جلب بيانات محفظة الأدمن من جدول portfolio كمصدر الحقيقة الوحيد"""
        try:
            with self.get_connection() as conn:
                portfolio_result = conn.execute("""
                    SELECT total_balance, available_balance, invested_balance,
                           initial_balance, total_profit_loss, total_profit_loss_percentage,
                           updated_at
                    FROM portfolio
                    WHERE user_id = ? AND is_demo = ?
                    LIMIT 1
                """, (user_id, is_demo)).fetchone()

                if not portfolio_result:
                    return {'error': True, 'message': 'محفظة الأدمن المرجعية غير موجودة'}

                daily_result = conn.execute("""
                    SELECT COALESCE(SUM(profit_loss), 0) as daily_pnl
                    FROM active_positions
                    WHERE user_id = ? AND is_demo = ? AND is_active = FALSE
                    AND DATE(closed_at) = DATE('now')
                """, (user_id, is_demo)).fetchone()

                trades_result = conn.execute("""
                    SELECT
                        COUNT(*) as trades_count,
                        COALESCE(SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END), 0) as winning_trades
                    FROM active_positions
                    WHERE user_id = ? AND is_demo = ? AND is_active = FALSE
                """, (user_id, is_demo)).fetchone()

                total_balance = float(portfolio_result[0] or 0)
                available_balance = float(portfolio_result[1] or 0)
                invested_balance = float(portfolio_result[2] or 0)
                initial_balance = float(portfolio_result[3] or 0)
                total_pnl = float(portfolio_result[4] or 0)
                total_pnl_pct = float(portfolio_result[5] or 0)
                last_update = portfolio_result[6] if portfolio_result[6] else datetime.now().isoformat()

                daily_pnl = float(daily_result[0] or 0) if daily_result else 0.0
                daily_pnl_pct = (daily_pnl / initial_balance * 100) if initial_balance > 0 else 0.0
                trades_count = int(trades_result[0] or 0) if trades_result else 0
                winning_trades = int(trades_result[1] or 0) if trades_result else 0
                win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0.0

                return {
                    'balance': available_balance,
                    'totalBalance': self._format_currency(total_balance),
                    'availableBalance': self._format_currency(available_balance),
                    'investedBalance': self._format_currency(invested_balance),
                    'initialBalance': self._format_currency(initial_balance),
                    'totalPnL': f"{total_pnl:+,.2f}",
                    'totalPnLPercentage': f"{total_pnl_pct:+.2f}",
                    'totalProfitLoss': f"{total_pnl:+,.2f}",
                    'totalProfitLossPercentage': f"{total_pnl_pct:+.2f}%",
                    'dailyPnL': f"{daily_pnl:+,.2f}",
                    'dailyPnLPercentage': f"{daily_pnl_pct:+.2f}",
                    'investedAmount': self._format_currency(invested_balance),
                    'tradesCount': trades_count,
                    'winRate': f"{win_rate:.1f}%",
                    'hasKeys': False,
                    'currency': 'USD',
                    'mode': 'demo' if is_demo else 'real',
                    'source': 'portfolio_table',
                    'lastUpdate': last_update
                }
        except Exception as e:
            self.logger.error(f"خطأ في جلب محفظة الأدمن: {e}")
            return {'error': True, 'message': str(e)}

    def get_user_trading_stats(self, user_id: int) -> Dict[str, Any]:
        """الحصول على إحصائيات التداول للمستخدم"""
        try:
            with self.get_connection() as conn:
                
                stats_row = conn.execute("""
                    SELECT
                        SUM(CASE WHEN is_active = FALSE THEN 1 ELSE 0 END) as closed_trades,
                        SUM(CASE WHEN is_active = FALSE AND profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                        AVG(CASE WHEN is_active = FALSE AND profit_loss > 0 THEN profit_loss END) as avg_profit,
                        AVG(CASE WHEN is_active = FALSE AND profit_loss < 0 THEN profit_loss END) as avg_loss,
                        MAX(CASE WHEN is_active = FALSE THEN closed_at ELSE NULL END) as last_trade_date
                    FROM active_positions
                    WHERE user_id = ?
                """, (user_id,)).fetchone()

                active_row = conn.execute("""
                    SELECT COUNT(*) as active_trades
                    FROM active_positions
                    WHERE user_id = ? AND is_active = TRUE
                """, (user_id,)).fetchone()
                
                if stats_row:
                    stats = dict(stats_row)
                    closed_trades = int(stats.get('closed_trades', 0) or 0)
                    active_trades = int((dict(active_row).get('active_trades', 0) if active_row else 0) or 0)
                    total_trades = closed_trades + active_trades
                    winning_trades = stats.get('winning_trades', 0)
                    win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0
                    
                    return {
                        'activeTrades': active_trades,
                        'totalTrades': total_trades,
                        'winRate': round(win_rate, 1),
                        'avgProfit': round(stats.get('avg_profit', 0) or 0, 2),
                        'avgLoss': round(stats.get('avg_loss', 0) or 0, 2),
                        'profitFactor': 1.25,
                        'maxDrawdown': 8.2,
                        'sharpeRatio': 1.45,
                        'totalDays': 30,
                        'tradingDays': 22,
                        'lastTradeDate': stats.get('last_trade_date') or datetime.now().isoformat()
                    }
                else:
                    return self._get_default_trading_stats()
                    
        except Exception as e:
            self.logger.error(f"خطأ في جلب إحصائيات التداول: {e}")
            return self._get_default_trading_stats()

    def _get_default_trading_stats(self) -> Dict[str, Any]:
        """إحصائيات تداول افتراضية"""
        return {
            'activeTrades': 0,
            'totalTrades': 0,
            'winRate': 0.0,
            'avgProfit': 0.0,
            'avgLoss': 0.0,
            'profitFactor': 0.0,
            'maxDrawdown': 0.0,
            'sharpeRatio': 0.0,
            'totalDays': 0,
            'tradingDays': 0,
            'lastTradeDate': datetime.now().isoformat()
        }

    def get_user_trades(self, user_id: int, limit: int = 50, is_demo: Optional[int] = None) -> List[Dict[str, Any]]:
        """الحصول على سجل الصفقات للمستخدم — يقرأ من active_positions (المصدر الوحيد للبيانات)"""
        try:
            is_admin = is_admin_user(self, user_id)
            
            if is_admin and is_demo is None:
                is_demo = get_effective_is_demo(self, user_id)
            
            with self.get_connection() as conn:
                
                if is_demo is not None:
                    rows = conn.execute("""
                        SELECT
                            id, user_id, symbol, strategy, is_demo,
                            entry_price, exit_price, quantity,
                            profit_loss,
                            profit_pct AS profit_loss_percentage,
                            CASE WHEN is_active = 1 THEN 'open' ELSE 'closed' END AS status,
                            COALESCE(entry_date, created_at) AS entry_time,
                            closed_at AS exit_time,
                            CASE WHEN position_type IN ('long', 'LONG') THEN 'buy' ELSE 'sell' END AS side,
                            timeframe, created_at
                        FROM active_positions
                        WHERE user_id = ? AND is_demo = ?
                        ORDER BY COALESCE(entry_date, created_at) DESC
                        LIMIT ?
                    """, (user_id, is_demo, limit)).fetchall()
                else:
                    rows = conn.execute("""
                        SELECT
                            id, user_id, symbol, strategy, is_demo,
                            entry_price, exit_price, quantity,
                            profit_loss,
                            profit_pct AS profit_loss_percentage,
                            CASE WHEN is_active = 1 THEN 'open' ELSE 'closed' END AS status,
                            COALESCE(entry_date, created_at) AS entry_time,
                            closed_at AS exit_time,
                            CASE WHEN position_type IN ('long', 'LONG') THEN 'buy' ELSE 'sell' END AS side,
                            timeframe, created_at
                        FROM active_positions
                        WHERE user_id = ?
                        ORDER BY COALESCE(entry_date, created_at) DESC
                        LIMIT ?
                    """, (user_id, limit)).fetchall()
                
                trades = []
                for row in rows:
                    trade = dict(row)
                    trades.append({
                        'id': f"trade_{trade['id']}",
                        'symbol': trade.get('symbol', 'UNKNOWN'),
                        'side': trade.get('side', 'BUY'),
                        'amount': trade.get('quantity', 0.0),
                        'price': trade.get('entry_price', 0.0),
                        'pnl': trade.get('profit_loss', 0.0),
                        'pnlPercentage': trade.get('profit_loss_percentage', 0.0),
                        'status': trade.get('status', 'UNKNOWN'),
                        'openTime': trade.get('entry_time') or trade.get('created_at'),
                        'closeTime': trade.get('exit_time'),
                        'strategy': trade.get('strategy', 'Manual'),
                        'timeframe': trade.get('timeframe', '1h')
                    })
                
                return trades
                
        except Exception as e:
            self.logger.error(f"خطأ في جلب سجل الصفقات: {e}")
            return []

    # ==================== مفاتيح Binance ====================

    def get_binance_keys(self, user_id: int) -> Dict[str, Any]:
        """الحصول على مفاتيح Binance للمستخدم (الدالة الرئيسية)"""
        try:
            from backend.utils.encryption_utils import encrypt_key, decrypt_key
            ENCRYPTION_AVAILABLE = True
        except ImportError:
            ENCRYPTION_AVAILABLE = False
            
        try:
            with self.get_connection() as conn:
                
                row = conn.execute("""
                    SELECT api_key, api_secret, is_active, created_at 
                    FROM user_binance_keys WHERE user_id = ? AND is_active = 1
                    ORDER BY created_at DESC LIMIT 1
                """, (user_id,)).fetchone()
                
                if row and row['api_key']:
                    api_key = row['api_key']
                    api_secret = row['api_secret']
                    
                    if ENCRYPTION_AVAILABLE:
                        try:
                            api_key = decrypt_key(api_key)
                            api_secret = decrypt_key(api_secret)
                            self.logger.debug(f"✅ تم فك تشفير مفاتيح Binance للمستخدم {user_id}")
                        except Exception as e:
                            self.logger.warning(f"⚠️ فشل فك تشفير المفاتيح: {e} - سيتم استخدام المفاتيح كما هي")
                    
                    return {
                        'api_key': api_key,
                        'secret_key': api_secret,
                        'is_active': row['is_active'],
                        'created_at': row['created_at']
                    }
                else:
                    return None
                    
        except Exception as e:
            self.logger.error(f"❌ خطأ في جلب مفاتيح Binance: {e}")
            return None

    def get_user_binance_keys(self, user_id: int) -> Dict[str, Any]:
        """الحصول على مفاتيح Binance (توافق خلفي)"""
        keys = self.get_binance_keys(user_id)
        if keys:
            return keys
        else:
            return {
                'api_key': '',
                'is_active': False,
                'created_at': None
            }

    def save_user_binance_keys(self, user_id: int, api_key: str, secret_key: str) -> bool:
        """حفظ مفاتيح Binance للمستخدم مع حذف المفاتيح القديمة وتشفيرها"""
        try:
            encrypted_api_key = api_key
            encrypted_secret_key = secret_key
            
            try:
                from backend.utils.encryption_utils import encrypt_key
                encrypted_api_key = encrypt_key(api_key)
                encrypted_secret_key = encrypt_key(secret_key)
                self.logger.info(f"✅ تم تشفير مفاتيح Binance للمستخدم {user_id}")
            except ImportError:
                self.logger.warning("⚠️ مدير التشفير غير متاح - سيتم الحفظ بدون تشفير")
            except Exception as e:
                self.logger.warning(f"⚠️ فشل تشفير المفاتيح: {e} - سيتم الحفظ بدون تشفير")
            
            with self.get_write_connection() as conn:
                conn.execute("""
                    DELETE FROM user_binance_keys WHERE user_id = ?
                """, (user_id,))
                
                conn.execute("""
                    INSERT INTO user_binance_keys 
                    (user_id, api_key, api_secret, is_active)
                    VALUES (?, ?, ?, TRUE)
                """, (user_id, encrypted_api_key, encrypted_secret_key))
                self.logger.info(f"✅ تم تحديث مفاتيح Binance للمستخدم {user_id} (مشفرة)")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ خطأ في حفظ مفاتيح Binance: {e}")
            return False

    def delete_user_binance_keys(self, user_id: int) -> bool:
        """حذف مفاتيح Binance للمستخدم"""
        try:
            with self.get_write_connection() as conn:
                conn.execute("DELETE FROM user_binance_keys WHERE user_id = ?", (user_id,))
                self.logger.info(f"تم حذف مفاتيح Binance للمستخدم {user_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"خطأ في حذف مفاتيح Binance: {e}")
            return False

    def reset_demo_account(self, user_id: int = 1):
        """إعادة ضبط بيانات الحساب للأدمن - مسح جميع البيانات وإعادة الرصيد إلى 1000$"""
        try:
            with self.get_write_connection() as conn:
                admin_user = conn.execute("""
                    SELECT id, username, user_type FROM users 
                    WHERE id = ? AND (user_type = 'admin' OR username = 'admin')
                """, (user_id,)).fetchone()
                
                if not admin_user:
                    self.logger.warning(f"محاولة إعادة ضبط بيانات حساب لمستخدم غير مخول: {user_id}")
                    return False
                
                self.logger.info(f"بدء إعادة ضبط بيانات الحساب للأدمن {user_id}")
                
                try:
                    conn.execute("DELETE FROM trades WHERE user_id = ?", (user_id,))
                    self.logger.info(f"تم مسح جميع الصفقات للمستخدم {user_id}")
                except Exception as e:
                    self.logger.warning(f"جدول trades غير موجود: {e}")
                
                try:
                    conn.execute("DELETE FROM active_positions WHERE user_id = ?", (user_id,))
                    self.logger.info(f"تم مسح سجل التداول للمستخدم {user_id}")
                except Exception as e:
                    self.logger.warning(f"جدول active_positions غير موجود: {e}")
                
                try:
                    conn.execute("DELETE FROM user_orders WHERE user_id = ?", (user_id,))
                    self.logger.info(f"تم مسح الأوامر المعلقة للمستخدم {user_id}")
                except Exception as e:
                    self.logger.warning(f"جدول user_orders غير موجود: {e}")
                
                try:
                    conn.execute("DELETE FROM notification_history WHERE user_id = ?", (user_id,))
                    self.logger.info(f"تم مسح سجل الإشعارات للمستخدم {user_id}")
                except Exception as e:
                    self.logger.warning(f"جدول notification_history غير موجود: {e}")
                
                portfolio_row = conn.execute("""
                    SELECT initial_balance FROM portfolio WHERE user_id = ? AND is_demo = TRUE LIMIT 1
                """, (user_id,)).fetchone()
                resolved_initial_balance = float(portfolio_row[0] or 0.0) if portfolio_row else 0.0
                conn.execute("""
                    INSERT OR REPLACE INTO portfolio 
                    (user_id, is_demo, total_balance, available_balance, invested_balance,
                     total_profit_loss, total_profit_loss_percentage, initial_balance, updated_at)
                    VALUES (?, TRUE, ?, ?, 0.0, 0.0, 0.0, ?, datetime('now'))
                """, (user_id, resolved_initial_balance, resolved_initial_balance, resolved_initial_balance))
                
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO user_settings 
                        (user_id, is_demo, risk_level, max_positions, stop_loss_pct,
                         take_profit_pct, trade_amount, position_size_percentage,
                         trailing_distance, trading_enabled, max_daily_loss_pct,
                         daily_loss_limit, trading_mode, updated_at)
                        VALUES (?, TRUE, 'medium', 5, 2.0, 6.0, 100.0, 10.0, 3.0, FALSE, 10.0, 100.0, 'demo', CURRENT_TIMESTAMP)
                    """, (user_id,))
                    
                    self.logger.info(f"تم إعادة ضبط إعدادات التداول للمستخدم {user_id}")
                except Exception as e:
                    self.logger.warning(f"خطأ في إعادة ضبط الإعدادات: {e}")
                
                conn.commit()
                self.logger.info(f"تم إكمال إعادة ضبط الحساب التجريبي للأدمن {user_id} بنجاح")
                return True
                
        except Exception as e:
            self.logger.error(f"خطأ في إعادة ضبط الحساب التجريبي للمستخدم {user_id}: {e}")
            return False

    def record_portfolio_snapshot(self, user_id: int, is_demo: int = 0) -> bool:
        """تسجيل لقطة يومية من بيانات المحفظة في portfolio_growth_history"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            is_demo = bool(is_demo)
            with self.get_connection() as conn:
                # جلب بيانات المحفظة الحالية
                portfolio_row = conn.execute(
                    "SELECT total_balance, initial_balance FROM portfolio WHERE user_id = ? AND is_demo = ?",
                    (user_id, is_demo)
                ).fetchone()

                if not portfolio_row:
                    return False

                total_balance = float(portfolio_row[0] or 0)
                initial_balance = float(portfolio_row[1] or total_balance or 1)

                # حساب PnL اليوم من الصفقات المغلقة اليوم
                daily_pnl = conn.execute(
                    """SELECT COALESCE(SUM(profit_loss), 0)
                       FROM active_positions
                       WHERE user_id = ? AND is_demo = ? AND is_active = 0
                       AND date(COALESCE(closed_at, updated_at)) = ?""",
                    (user_id, is_demo, today)
                ).fetchone()[0] or 0
                daily_pnl = float(daily_pnl)

                daily_pnl_pct = (daily_pnl / initial_balance * 100) if initial_balance > 0 else 0

                # عدد الصفقات المفتوحة
                active_count = conn.execute(
                    "SELECT COUNT(*) FROM active_positions WHERE user_id = ? AND is_demo = ? AND is_active = 1",
                    (user_id, is_demo)
                ).fetchone()[0] or 0

            with self.get_write_connection() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO portfolio_growth_history
                       (user_id, date, total_balance, daily_pnl, daily_pnl_percentage,
                        active_trades_count, created_at, is_demo)
                       VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)""",
                    (user_id, today, total_balance, daily_pnl, daily_pnl_pct, active_count, is_demo)
                )
                conn.commit()

            self.logger.info(f"✅ تم تسجيل snapshot المحفظة للمستخدم {user_id} (is_demo={is_demo}) بتاريخ {today}")
            return True

        except Exception as e:
            self.logger.error(f"❌ خطأ في تسجيل snapshot المحفظة للمستخدم {user_id}: {e}")
            return False

    def record_all_portfolios_snapshot(self) -> int:
        """تسجيل لقطة يومية لجميع المستخدمين النشطين"""
        try:
            users = self.execute_query(
                "SELECT id FROM users WHERE is_active = 1"
            )
            count = 0
            for user in (users or []):
                uid = user['id']
                # demo و real كلاهما
                for is_demo in [False, True]:
                    if self.record_portfolio_snapshot(uid, is_demo):
                        count += 1
            return count
        except Exception as e:
            self.logger.error(f"❌ خطأ في record_all_portfolios_snapshot: {e}")
            return 0
