"""
Database Portfolio Mixin — extracted from database_manager.py (God Object split)
================================================================================
Methods: portfolio CRUD, trades, PnL calculation, Binance keys, demo reset
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any


class DbPortfolioMixin:
    """Portfolio-related database methods (portfolio, trades, Binance keys)"""

    # ==================== المحفظة والصفقات المحسنة ====================

    def sync_portfolio_data(self, user_id: int) -> Dict[str, Any]:
        """مزامنة بيانات المحفظة وحساب القيم المحدثة"""
        try:
            with self.get_write_connection() as conn:
                cursor = conn.execute("""
                    SELECT 
                        p.totalBalance,
                        COALESCE(SUM(CASE WHEN t.status = 'active' THEN t.quantity * t.entry_price ELSE 0 END), 0) as invested_amount
                    FROM portfolio p
                    LEFT JOIN user_trades t ON p.user_id = t.user_id
                    WHERE p.user_id = ?
                    GROUP BY p.user_id, p.totalBalance
                """, (user_id,))
                
                result = cursor.fetchone()
                if result:
                    total_balance = float(result[0])
                    invested_amount = float(result[1])
                    available_balance = total_balance - invested_amount
                    
                    try:
                        conn.execute("""
                            INSERT OR REPLACE INTO portfolio (user_id, totalBalance, availableBalance)
                            VALUES (?, 1000.0, 1000.0)
                        """, (user_id,))
                        
                        self.logger.info(f"تم إعادة ضبط رصيد المحفظة إلى $1000 للمستخدم {user_id}")
                    except Exception as e:
                        self.logger.warning(f"خطأ في إعادة ضبط المحفظة: {e}")
                return {}
        except Exception as e:
            self.logger.error(f"خطأ في مزامنة بيانات المحفظة للمستخدم {user_id}: {e}")
            return {}

    def update_user_portfolio(self, user_id: int, is_demo: int = None, **updates):
        """تحديث محفظة المستخدم حسب الوضع"""
        if is_demo is None:
            user_data = self.get_user_by_id(user_id)
            is_admin = user_data.get('user_type') == 'admin' if user_data else False
            
            if is_admin:
                settings = self.get_trading_settings(user_id)
                trading_mode = settings.get('trading_mode', 'auto')
                if trading_mode == 'demo':
                    is_demo = 1
                elif trading_mode == 'real':
                    is_demo = 0
                else:  # auto
                    keys = self.get_binance_keys(user_id)
                    is_demo = 0 if keys else 1
            else:
                is_demo = 0
        
        with self.get_write_connection() as conn:
            update_fields = ["updated_at = CURRENT_TIMESTAMP"]
            values = []
            
            allowed_fields = [
                'balance', 'total_profit_loss', 'total_trades', 
                'winning_trades', 'losing_trades',
                'totalBalance', 'availableBalance', 'totalProfitLoss'
            ]
            
            for key, value in updates.items():
                if key in allowed_fields:
                    update_fields.append(f"{key} = ?")
                    values.append(value)
                    
                    if key == 'balance':
                        update_fields.append("totalBalance = ?")
                        values.append(value)
                    elif key == 'totalBalance':
                        update_fields.append("balance = ?")
                        values.append(value)
                    elif key == 'total_profit_loss':
                        update_fields.append("totalProfitLoss = ?")
                        values.append(value)
                    elif key == 'totalProfitLoss':
                        update_fields.append("total_profit_loss = ?")
                        values.append(value)
            
            if values:
                values.extend([user_id, is_demo])
                query = f"UPDATE portfolio SET {', '.join(update_fields)} WHERE user_id = ? AND is_demo = ?"
                conn.execute(query, values)

    def add_user_trade(self, user_id: int, trade_data: Dict[str, Any], is_demo: int = None) -> int:
        """إضافة صفقة جديدة للمستخدم حسب الوضع"""
        if is_demo is None:
            user_data = self.get_user_by_id(user_id)
            is_admin = user_data.get('user_type') == 'admin' if user_data else False
            
            if is_admin:
                settings = self.get_trading_settings(user_id)
                trading_mode = settings.get('trading_mode', 'auto')
                if trading_mode == 'demo':
                    is_demo = 1
                elif trading_mode == 'real':
                    is_demo = 0
                else:  # auto
                    keys = self.get_binance_keys(user_id)
                    is_demo = 0 if keys else 1
            else:
                is_demo = 0
        
        with self.get_write_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO user_trades 
                (user_id, symbol, strategy, timeframe, side, entry_price, quantity, 
                 stop_loss, take_profit, status, is_demo, entry_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, CURRENT_TIMESTAMP)
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
        """جلب الصفقات المفتوحة للمستخدم"""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM user_trades 
                WHERE user_id = ? AND status = 'active'
                ORDER BY entry_time DESC
            """, (user_id,)).fetchall()
            
            return [dict(row) for row in rows]

    def close_user_trade(self, trade_id: int, exit_price: float, profit_loss: float):
        """إغلاق صفقة المستخدم"""
        with self.get_write_connection() as conn:
            trade = conn.execute("""
                SELECT entry_price, quantity FROM user_trades WHERE id = ?
            """, (trade_id,)).fetchone()
            
            if trade:
                entry_price, quantity = trade
                initial_investment = entry_price * quantity
                profit_loss_percentage = (profit_loss / initial_investment * 100) if initial_investment > 0 else 0
            else:
                profit_loss_percentage = 0
            
            conn.execute("""
                UPDATE user_trades 
                SET exit_price = ?, profit_loss = ?, profit_loss_percentage = ?, 
                    status = 'closed', exit_time = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                exit_price,
                profit_loss,
                profit_loss_percentage,
                trade_id
            ))
            
            self.logger.info(f"تم إغلاق الصفقة {trade_id} بنسبة {profit_loss_percentage:.2f}%")

    def reset_user_portfolio(self, user_id: int, initial_balance: float = 1000.0) -> bool:
        """إعادة ضبط الحساب التجريبي - مسح جميع البيانات وإعادة تعيين الرصيد"""
        try:
            with self.get_write_connection() as conn:
                conn.execute("DELETE FROM user_trades WHERE user_id = ? AND is_demo = 1", (user_id,))
                self.logger.info(f"تم مسح صفقات الحساب التجريبي للمستخدم {user_id})")
                
                conn.execute("DELETE FROM user_binance_orders WHERE user_id = ? AND is_demo = 1", (user_id,))
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
                
                conn.execute("""
                    INSERT OR REPLACE INTO portfolio 
                    (user_id, balance, total_profit_loss, total_trades, winning_trades, 
                     losing_trades, totalBalance, availableBalance, totalProfitLoss, updated_at)
                    VALUES (?, ?, 0.0, 0, 0, 0, ?, ?, 0.0, CURRENT_TIMESTAMP)
                """, (user_id, initial_balance, initial_balance, initial_balance))
                
                conn.execute("""
                    INSERT OR REPLACE INTO user_settings 
                    (user_id, trade_amount, max_positions, risk_level, stop_loss_pct, 
                     take_profit_pct, trading_enabled, max_trades, 
                     capital_percentage, updated_at)
                    VALUES (?, 100.00, 5, 'medium', 3.00, 6.00, 0, 5, 10.00, CURRENT_TIMESTAMP)
                """, (user_id,))
                
                self.logger.info(f"تم إعادة ضبط الحساب التجريبي للمستخدم {user_id} بنجاح - الرصيد: {initial_balance}$")
                return True
                
        except Exception as e:
            self.logger.error(f"خطأ في إعادة ضبط الحساب التجريبي للمستخدم {user_id}: {e}")
            return False

    def get_user_trades_simple(self, user_id: int, status: Optional[str] = None, is_demo: Optional[int] = None) -> List[Dict[str, Any]]:
        """الحصول على صفقات المستخدم (نسخة بسيطة)"""
        with self.get_connection() as conn:
            conditions = ["user_id = ?"]
            params = [user_id]
            
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            if is_demo is not None:
                conditions.append("is_demo = ?")
                params.append(is_demo)
            
            query = f"""
                SELECT * FROM user_trades 
                WHERE {' AND '.join(conditions)}
                ORDER BY entry_time DESC
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
            
            is_admin = user_data.get('user_type') == 'admin'
            
            if is_admin:
                if is_demo is None:
                    settings = self.get_trading_settings(user_id)
                    trading_mode = settings.get('trading_mode', 'auto')
                    if trading_mode == 'demo':
                        is_demo = 1
                    elif trading_mode == 'real':
                        is_demo = 0
                    else:  # auto
                        keys = self.get_binance_keys(user_id)
                        is_demo = 0 if keys else 1
                
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
                    initial_balance = self._get_or_set_initial_balance(user_id, total_usdt)
                    
                    total_growth = total_usdt - initial_balance if initial_balance > 0 else 0
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
                        COALESCE(SUM(profit_loss), 0) as total_pnl,
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(CASE WHEN status = 'open' THEN quantity * entry_price ELSE 0 END) as invested
                    FROM user_trades
                    WHERE user_id = ? AND is_demo = 0
                """, (user_id,)).fetchone()
                
                daily_result = conn.execute("""
                    SELECT COALESCE(SUM(profit_loss), 0) as daily_pnl
                    FROM user_trades
                    WHERE user_id = ? AND is_demo = 0
                    AND DATE(exit_time) = DATE('now')
                """, (user_id,)).fetchone()
                
                total_pnl = total_result[0] if total_result else 0
                total_trades = total_result[1] if total_result else 0
                winning_trades = total_result[2] if total_result else 0
                invested = total_result[3] if total_result else 0
                daily_pnl = daily_result[0] if daily_result else 0
                
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
                    'invested': invested
                }
        except Exception as e:
            self.logger.error(f"خطأ في حساب الأرباح: {e}")
            return {
                'total_pnl': 0, 'total_pnl_pct': 0,
                'daily_pnl': 0, 'daily_pnl_pct': 0,
                'trades_count': 0, 'winning_trades': 0,
                'win_rate': 0, 'invested': 0
            }

    def _get_or_set_initial_balance(self, user_id: int, current_balance: float) -> float:
        """جلب أو تعيين الرصيد الابتدائي للمستخدم"""
        try:
            with self.get_write_connection() as conn:
                result = conn.execute("""
                    SELECT initial_balance FROM portfolio
                    WHERE user_id = ? AND is_demo = 0
                """, (user_id,)).fetchone()
                
                if result and result[0] and result[0] > 0:
                    return result[0]
                
                if current_balance > 0:
                    conn.execute("""
                        INSERT INTO portfolio (user_id, total_balance, initial_balance, is_demo, updated_at)
                        VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)
                        ON CONFLICT(user_id, is_demo) DO UPDATE SET
                        initial_balance = CASE 
                            WHEN initial_balance IS NULL OR initial_balance = 0 
                            THEN excluded.initial_balance 
                            ELSE initial_balance 
                        END,
                        total_balance = excluded.total_balance,
                        updated_at = CURRENT_TIMESTAMP
                    """, (user_id, current_balance, current_balance))
                    return current_balance
                
                return 0
        except Exception as e:
            self.logger.error(f"خطأ في جلب الرصيد الابتدائي: {e}")
            return 0

    def _get_admin_portfolio(self, user_id: int, is_demo: int) -> Dict[str, Any]:
        """جلب بيانات المحفظة للأدمن من جدول portfolio الموحد"""
        try:
            with self.get_connection() as conn:
                # جلب بيانات المحفظة من الجدول الموحد فقط
                portfolio_result = conn.execute("""
                    SELECT 
                        total_balance, available_balance, invested_balance,
                        total_profit_loss, total_profit_loss_percentage,
                        updated_at
                    FROM portfolio
                    WHERE user_id = ? AND is_demo = ?
                """, (user_id, is_demo)).fetchone()
                
                pnl_result = conn.execute("""
                    SELECT 
                        COALESCE(SUM(profit_loss), 0) as total_pnl,
                        COUNT(*) as trades_count,
                        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning
                    FROM user_trades
                    WHERE user_id = ? AND is_demo = ? AND status = 'closed'
                """, (user_id, is_demo)).fetchone()
                
                daily_result = conn.execute("""
                    SELECT COALESCE(SUM(profit_loss), 0) as daily_pnl
                    FROM user_trades
                    WHERE user_id = ? AND is_demo = ? AND DATE(exit_time) = DATE('now')
                """, (user_id, is_demo)).fetchone()
                
                total_pnl = pnl_result[0] if pnl_result else 0
                trades_count = pnl_result[1] if pnl_result else 0
                winning_trades = pnl_result[2] if pnl_result else 0
                daily_pnl = daily_result[0] if daily_result else 0
                win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0
            
            if portfolio_result:
                portfolio = dict(portfolio_result)
                total_balance = float(portfolio.get('total_balance', 1000.0))
                available_balance = float(portfolio.get('available_balance', total_balance))
                invested_balance = float(portfolio.get('invested_balance', 0.0))
                total_profit_loss = float(portfolio.get('total_profit_loss', 0.0))
                total_profit_loss_percentage = float(portfolio.get('total_profit_loss_percentage', 0.0))
                
                return {
                    'balance': available_balance,
                    'totalBalance': self._format_currency(total_balance),
                    'availableBalance': self._format_currency(available_balance),
                    'investedBalance': self._format_currency(invested_balance),
                    'totalProfitLoss': f"{total_profit_loss:+,.2f}",
                    'totalProfitLossPercentage': f"{total_profit_loss_percentage:+.2f}%",
                    'dailyPnL': f"{daily_pnl:+,.2f}",
                    'dailyPnLPercentage': f"{(daily_pnl / invested_balance * 100) if invested_balance > 0 else 0.0:+.2f}%",
                    'investedAmount': self._format_currency(invested_balance),
                    'tradesCount': trades_count,
                    'winRate': f"{win_rate:.1f}%",
                    'currency': 'USD',
                    'mode': 'demo' if is_demo else 'real',
                    'source': 'portfolio_unified',
                    'lastUpdate': portfolio.get('updated_at', datetime.now().isoformat())
                }
            else:
                # ✅ فقط هنا نستخدم write connection — عند الحاجة لإدراج صف جديد
                if not portfolio_result:
                    # إنشاء محفظة جديدة في الجدول الموحد إذا لم تكن موجودة
                    initial_balance = 10000.0 if is_demo else 1000.0
                    conn.execute("""
                        INSERT INTO portfolio 
                        (user_id, total_balance, available_balance, invested_balance,
                         total_profit_loss, total_profit_loss_percentage, is_demo)
                        VALUES (?, ?, ?, 0.0, 0.0, 0.0, ?)
                    """, (user_id, initial_balance, initial_balance, is_demo))
                    
                    return {
                        'totalBalance': self._format_currency(initial_balance),
                        'balance': initial_balance,
                        'availableBalance': self._format_currency(initial_balance),
                        'investedBalance': self._format_currency(0.0),
                        'totalProfitLoss': '+0.00',
                        'totalProfitLossPercentage': '+0.00%',
                        'currency': 'USD',
                        'mode': 'demo' if is_demo else 'real',
                        'source': 'portfolio_unified',
                        'lastUpdate': datetime.now().isoformat()
                    }
        except Exception as e:
            self.logger.error(f"خطأ في جلب محفظة الأدمن: {e}")
            return {'error': True, 'message': str(e)}

    def get_user_trading_stats(self, user_id: int) -> Dict[str, Any]:
        """الحصول على إحصائيات التداول للمستخدم"""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                
                stats_row = conn.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_trades,
                        COUNT(CASE WHEN profit_loss > 0 THEN 1 END) as winning_trades,
                        AVG(CASE WHEN profit_loss > 0 THEN profit_loss END) as avg_profit,
                        AVG(CASE WHEN profit_loss < 0 THEN profit_loss END) as avg_loss,
                        MAX(created_at) as last_trade_date
                    FROM user_trades WHERE user_id = ?
                """, (user_id,)).fetchone()
                
                if stats_row:
                    stats = dict(stats_row)
                    total_trades = stats.get('total_trades', 0)
                    winning_trades = stats.get('winning_trades', 0)
                    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
                    
                    return {
                        'activeTrades': stats.get('active_trades', 0),
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
        """الحصول على سجل الصفقات للمستخدم حسب الوضع"""
        try:
            user_data = self.get_user_by_id(user_id)
            is_admin = user_data.get('user_type') == 'admin' if user_data else False
            
            if is_admin and is_demo is None:
                settings = self.get_trading_settings(user_id)
                trading_mode = settings.get('trading_mode', 'auto')
                if trading_mode == 'demo':
                    is_demo = 1
                elif trading_mode == 'real':
                    is_demo = 0
                else:  # auto
                    keys = self.get_binance_keys(user_id)
                    is_demo = 0 if keys else 1
            
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                
                if is_demo is not None:
                    rows = conn.execute("""
                        SELECT * FROM user_trades 
                        WHERE user_id = ? AND is_demo = ?
                        ORDER BY created_at DESC 
                        LIMIT ?
                    """, (user_id, is_demo, limit)).fetchall()
                else:
                    rows = conn.execute("""
                        SELECT * FROM user_trades 
                        WHERE user_id = ? 
                        ORDER BY created_at DESC 
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
                        'pnlPercentage': trade.get('profit_loss_pct', 0.0),
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
                conn.row_factory = sqlite3.Row
                
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
                    VALUES (?, ?, ?, 1)
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
                    conn.execute("DELETE FROM user_trades WHERE user_id = ?", (user_id,))
                    self.logger.info(f"تم مسح سجل التداول للمستخدم {user_id}")
                except Exception as e:
                    self.logger.warning(f"جدول user_trades غير موجود: {e}")
                
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
                
                conn.execute("""
                    INSERT OR REPLACE INTO portfolio 
                    (user_id, balance, total_profit_loss, total_trades, winning_trades, 
                     losing_trades, updated_at)
                    VALUES (?, 1000.0, 0.0, 0, 0, 0, datetime('now'))
                """, (user_id,))
                
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO user_settings 
                        (user_id, risk_level, max_position_size, stop_loss_pct, take_profit_pct)
                        VALUES (?, 'medium', 0.1, 0.02, 0.06)
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
