"""
نظام تتبع حالة العملات والتعلم من الأخطاء
يتتبع أداء كل عملة ويتعلم من الصفقات الخاسرة
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

from database.database_manager import DatabaseManager


class CoinStateTracker:
    """
    تتبع حالة كل عملة والتعلم من الأداء التاريخي
    
    States:
    - EXCELLENT: 3+ أرباح متتالية → زيادة Position Size 30%
    - GOOD: أداء جيد عام → Position Size عادي
    - CAUTIOUS: 2 خسائر متتالية → تقليل Position Size 50%
    - BLACKLISTED: 3 خسائر متتالية → منع التداول 7 أيام
    """
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager or DatabaseManager()
    
    def update_after_trade(self, symbol: str, pnl: float, profit_pct: float, 
                          exit_reason: str, strategy: str = None, 
                          timeframe: str = None, market_regime: str = None):
        """
        تحديث حالة العملة بعد إغلاق صفقة
        
        Args:
            symbol: رمز العملة
            pnl: الربح/الخسارة بالـ USDT
            profit_pct: نسبة الربح/الخسارة
            exit_reason: سبب الخروج
            strategy: الاستراتيجية المستخدمة
            timeframe: الإطار الزمني
            market_regime: حالة السوق
        """
        with self.db_manager.get_write_connection() as conn:
            cursor = conn.cursor()
            
            # 1. حفظ الصفقة في التاريخ
            cursor.execute("""
                INSERT INTO coin_trade_history 
                (symbol, entry_time, exit_time, pnl, profit_pct, exit_reason, strategy, timeframe, market_regime)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                symbol,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                pnl,
                profit_pct,
                exit_reason,
                strategy,
                timeframe,
                market_regime
            ))
            
            # 2. جلب الحالة الحالية أو إنشاء جديدة
            cursor.execute("SELECT * FROM coin_states WHERE symbol = %s", (symbol,))
            row = cursor.fetchone()
            
            if row:
                state = row[1]
                pos_multiplier = row[2]
                sl_multiplier = row[3]
                consec_wins = row[4]
                consec_losses = row[5]
                total_trades = row[6]
                winning_trades = row[7]
                total_pnl = row[8]
            else:
                state = "GOOD"
                pos_multiplier = 1.0
                sl_multiplier = 1.0
                consec_wins = 0
                consec_losses = 0
                total_trades = 0
                winning_trades = 0
                total_pnl = 0.0
            
            # 3. تحديث الإحصائيات
            total_trades += 1
            total_pnl += pnl
            
            if pnl > 0:
                winning_trades += 1
                consec_wins += 1
                consec_losses = 0
            else:
                consec_wins = 0
                consec_losses += 1
            
            # 4. تحديد الحالة الجديدة
            new_state = state
            blacklist_until = None
            
            # حالة EXCELLENT: 3+ أرباح متتالية
            if consec_wins >= 3:
                new_state = "EXCELLENT"
                pos_multiplier = 1.3  # زيادة 30%
                sl_multiplier = 1.0
            
            # حالة CAUTIOUS: 2 خسائر متتالية
            elif consec_losses >= 2:
                new_state = "CAUTIOUS"
                pos_multiplier = 0.5  # تقليل 50%
                sl_multiplier = 1.2  # زيادة SL 20%
            
            # حالة BLACKLISTED: 3 خسائر متتالية
            if consec_losses >= 3:
                new_state = "BLACKLISTED"
                pos_multiplier = 0.0
                blacklist_until = (datetime.now() + timedelta(days=7)).isoformat()
            
            # حالة GOOD: افتراضية
            if consec_wins < 3 and consec_losses < 2:
                new_state = "GOOD"
                pos_multiplier = 1.0
                sl_multiplier = 1.0
            
            # 5. حفظ الحالة الجديدة
            cursor.execute("""
                INSERT INTO coin_states
                (symbol, state, position_size_multiplier, stop_loss_multiplier,
                 consecutive_wins, consecutive_losses, total_trades, winning_trades,
                 total_pnl, blacklist_until, last_updated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    state = EXCLUDED.state,
                    position_size_multiplier = EXCLUDED.position_size_multiplier,
                    stop_loss_multiplier = EXCLUDED.stop_loss_multiplier,
                    consecutive_wins = EXCLUDED.consecutive_wins,
                    consecutive_losses = EXCLUDED.consecutive_losses,
                    total_trades = EXCLUDED.total_trades,
                    winning_trades = EXCLUDED.winning_trades,
                    total_pnl = EXCLUDED.total_pnl,
                    blacklist_until = EXCLUDED.blacklist_until,
                    last_updated = EXCLUDED.last_updated
            """, (
                symbol, new_state, pos_multiplier, sl_multiplier,
                consec_wins, consec_losses, total_trades, winning_trades,
                total_pnl, blacklist_until, datetime.now().isoformat()
            ))
        
        return new_state, pos_multiplier, sl_multiplier
    
    def get_coin_state(self, symbol: str) -> Dict:
        """
        الحصول على حالة العملة الحالية
        
        Returns:
            Dict: {
                'state': str,
                'position_size_multiplier': float,
                'stop_loss_multiplier': float,
                'can_trade': bool,
                'consecutive_wins': int,
                'consecutive_losses': int,
                'win_rate': float,
                'total_pnl': float
            }
        """
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM coin_states WHERE symbol = %s", (symbol,))
            row = cursor.fetchone()
        
        if not row:
            return {
                'state': 'GOOD',
                'position_size_multiplier': 1.0,
                'stop_loss_multiplier': 1.0,
                'can_trade': True,
                'consecutive_wins': 0,
                'consecutive_losses': 0,
                'win_rate': None,
                'total_pnl': 0.0
            }
        
        # التحقق من Blacklist
        blacklist_until = row[9]
        can_trade = True
        
        if blacklist_until:
            blacklist_date = datetime.fromisoformat(blacklist_until)
            if datetime.now() < blacklist_date:
                can_trade = False
            else:
                # انتهى Blacklist → إعادة تعيين
                self._reset_coin_state(symbol)
                return self.get_coin_state(symbol)
        
        total_trades = row[6]
        winning_trades = row[7]
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else None
        
        return {
            'state': row[1],
            'position_size_multiplier': row[2],
            'stop_loss_multiplier': row[3],
            'can_trade': can_trade,
            'consecutive_wins': row[4],
            'consecutive_losses': row[5],
            'win_rate': win_rate,
            'total_pnl': row[8],
            'total_trades': total_trades,
            'winning_trades': winning_trades
        }
    
    def _reset_coin_state(self, symbol: str):
        """إعادة تعيين حالة العملة بعد انتهاء Blacklist"""
        with self.db_manager.get_write_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE coin_states
                SET state = 'CAUTIOUS',
                    position_size_multiplier = 0.5,
                    stop_loss_multiplier = 1.2,
                    consecutive_wins = 0,
                    consecutive_losses = 0,
                    blacklist_until = NULL,
                    last_updated = %s
                WHERE symbol = %s
            """, (datetime.now().isoformat(), symbol))
    
    def get_recent_trades(self, symbol: str, n: int = 5) -> List[Dict]:
        """الحصول على آخر N صفقة للعملة"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT pnl, profit_pct, exit_reason, strategy, timeframe, market_regime, exit_time
                FROM coin_trade_history
                WHERE symbol = %s
                ORDER BY exit_time DESC
                LIMIT %s
            """, (symbol, n))
            
            rows = cursor.fetchall()
        
        return [
            {
                'pnl': row[0],
                'profit_pct': row[1],
                'exit_reason': row[2],
                'strategy': row[3],
                'timeframe': row[4],
                'market_regime': row[5],
                'exit_time': row[6]
            }
            for row in rows
        ]
    
    def get_all_states(self) -> List[Dict]:
        """الحصول على حالة جميع العملات"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT symbol FROM coin_states")
            symbols = [row[0] for row in cursor.fetchall()]
        
        return [
            {
                'symbol': symbol,
                **self.get_coin_state(symbol)
            }
            for symbol in symbols
        ]
    
    def get_statistics(self) -> Dict:
        """إحصائيات عامة"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_coins,
                    SUM(CASE WHEN state = 'EXCELLENT' THEN 1 ELSE 0 END) as excellent,
                    SUM(CASE WHEN state = 'GOOD' THEN 1 ELSE 0 END) as good,
                    SUM(CASE WHEN state = 'CAUTIOUS' THEN 1 ELSE 0 END) as cautious,
                    SUM(CASE WHEN state = 'BLACKLISTED' THEN 1 ELSE 0 END) as blacklisted,
                    SUM(total_pnl) as total_system_pnl
                FROM coin_states
            """)
            
            row = cursor.fetchone()
        
        return {
            'total_coins': row[0],
            'excellent': row[1],
            'good': row[2],
            'cautious': row[3],
            'blacklisted': row[4],
            'total_system_pnl': row[5]
        }
