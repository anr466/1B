"""
CryptoWave Database Integration
Connects CryptoWave trading system with the main database and mobile app.
"""

import sys
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import json

# Add project paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import database manager
try:
    from database.database_manager import DatabaseManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("[WARN] DatabaseManager not available")

@dataclass
class CryptoWaveTrade:
    """Trade record for database storage"""
    user_id: int
    symbol: str
    strategy: str
    entry_price: float
    exit_price: Optional[float] = None
    stop_loss: float = 0.0
    take_profit: float = 0.0
    quantity: float = 0.0
    pnl_pct: float = 0.0
    pnl_usd: float = 0.0
    entry_time: Optional[str] = None
    exit_time: Optional[str] = None
    exit_reason: str = ""
    is_demo: int = 0  # 0 = real, 1 = demo
    confidence: float = 0.0
    market_condition: str = ""

class CryptoWaveDBIntegration:
    """
    Database Integration Layer for CryptoWave Hopper
    
    Connects trading system with:
    - Database for trade storage
    - Mobile app API for real-time updates
    - Performance tracking
    """
    
    def __init__(self, user_id: int = 1, is_demo: bool = True):
        self.user_id = user_id
        self.is_demo = 1 if is_demo else 0
        
        if DB_AVAILABLE:
            self.db = DatabaseManager()
        else:
            self.db = None
        
        self.trade_cache: Dict[str, CryptoWaveTrade] = {}
    
    def register_trade_entry(self, 
                             symbol: str,
                             strategy: str,
                             entry_price: float,
                             stop_loss: float,
                             take_profit: float,
                             quantity: float = 0.0,
                             confidence: float = 0.0,
                             market_condition: str = "") -> bool:
        """
        Register a new trade entry in the database
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            strategy: Strategy name (e.g., Scalping, DCA)
            entry_price: Entry price
            stop_loss: Stop-loss price
            take_profit: Take-profit price
            quantity: Position size
            confidence: AI confidence score
            market_condition: Market condition at entry
        
        Returns:
            Success status
        """
        try:
            # Create trade record
            trade = CryptoWaveTrade(
                user_id=self.user_id,
                symbol=symbol,
                strategy=strategy,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                quantity=quantity,
                entry_time=datetime.now().isoformat(),
                is_demo=self.is_demo,
                confidence=confidence,
                market_condition=market_condition
            )
            
            # Cache for quick lookup
            self.trade_cache[symbol] = trade
            
            # Save to database
            if self.db:
                self.db.register_active_position(
                    user_id=self.user_id,
                    symbol=symbol,
                    strategy=f"CryptoWave_{strategy}",
                    timeframe="15m",
                    position_type="long",
                    entry_price=entry_price,
                    quantity=quantity,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    trailing_sl_price=stop_loss,
                    is_demo=self.is_demo
                )
                print(f"[DB] ✅ Registered: {symbol} @ {entry_price:.4f} | {strategy}")
                return True
            
            return False
            
        except Exception as e:
            print(f"[DB] ❌ Error registering trade: {e}")
            return False
    
    def update_trailing_stop(self, symbol: str, new_sl: float) -> bool:
        """Update trailing stop-loss for active position"""
        try:
            if self.db:
                self.db.update_position_trailing_sl(
                    user_id=self.user_id,
                    symbol=symbol,
                    trailing_sl_price=new_sl
                )
                
                if symbol in self.trade_cache:
                    self.trade_cache[symbol].stop_loss = new_sl
                
                return True
            return False
            
        except Exception as e:
            print(f"[DB] ❌ Error updating SL: {e}")
            return False
    
    def record_trade_exit(self,
                          symbol: str,
                          exit_price: float,
                          exit_reason: str,
                          pnl_pct: float,
                          pnl_usd: float = 0.0) -> bool:
        """
        Record trade exit and close position
        
        Args:
            symbol: Trading pair
            exit_price: Exit price
            exit_reason: Reason for exit
            pnl_pct: Profit/loss percentage
            pnl_usd: Profit/loss in USD
        
        Returns:
            Success status
        """
        try:
            # Update cache
            if symbol in self.trade_cache:
                trade = self.trade_cache[symbol]
                trade.exit_price = exit_price
                trade.exit_time = datetime.now().isoformat()
                trade.exit_reason = exit_reason
                trade.pnl_pct = pnl_pct
                trade.pnl_usd = pnl_usd
            
            # Close in database
            if self.db:
                self.db.close_active_position(
                    user_id=self.user_id,
                    symbol=symbol,
                    strategy=f"CryptoWave_{self.trade_cache.get(symbol, {}).strategy if symbol in self.trade_cache else 'Unknown'}"
                )
                
                # Save trade history
                self._save_trade_history(symbol, exit_price, exit_reason, pnl_pct, pnl_usd)
                
                print(f"[DB] ✅ Closed: {symbol} | {exit_reason} | PnL: {pnl_pct:+.2f}%")
            
            # Remove from cache
            if symbol in self.trade_cache:
                del self.trade_cache[symbol]
            
            return True
            
        except Exception as e:
            print(f"[DB] ❌ Error recording exit: {e}")
            return False
    
    def _save_trade_history(self, symbol: str, exit_price: float, 
                            exit_reason: str, pnl_pct: float, pnl_usd: float):
        """Save trade to history table"""
        if not self.db or symbol not in self.trade_cache:
            return
        
        trade = self.trade_cache[symbol]
        
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO user_trades (
                        user_id, symbol, trade_type, strategy,
                        entry_price, exit_price, quantity,
                        profit_loss, profit_percentage,
                        entry_time, exit_time, status, is_demo,
                        notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.user_id,
                    symbol,
                    'long',
                    f"CryptoWave_{trade.strategy}",
                    trade.entry_price,
                    exit_price,
                    trade.quantity,
                    pnl_usd,
                    pnl_pct,
                    trade.entry_time,
                    datetime.now().isoformat(),
                    'closed',
                    self.is_demo,
                    f"Exit: {exit_reason} | Confidence: {trade.confidence:.0%}"
                ))
                conn.commit()
        except Exception as e:
            print(f"[DB] Error saving history: {e}")
    
    def get_active_positions(self) -> List[Dict]:
        """Get all active positions for user"""
        if self.db:
            return self.db.get_active_positions_for_user(self.user_id)
        return []
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary from database"""
        if not self.db:
            return {}
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get trade stats
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(profit_loss) as total_pnl,
                        AVG(profit_percentage) as avg_pnl_pct
                    FROM user_trades
                    WHERE user_id = ? AND strategy LIKE 'CryptoWave_%'
                    AND created_at >= datetime('now', '-30 days')
                """, (self.user_id,))
                
                row = cursor.fetchone()
                if row:
                    total = row[0] or 0
                    wins = row[1] or 0
                    return {
                        'total_trades': total,
                        'winning_trades': wins,
                        'win_rate': (wins / total * 100) if total > 0 else 0,
                        'total_pnl': row[2] or 0,
                        'avg_pnl_pct': row[3] or 0
                    }
        except Exception as e:
            print(f"[DB] Error getting performance: {e}")
        
        return {}
    
    def sync_with_mobile_app(self) -> Dict:
        """
        Prepare data for mobile app synchronization
        Returns data in format expected by mobile API
        """
        positions = self.get_active_positions()
        performance = self.get_performance_summary()
        
        return {
            'active_positions': [{
                'symbol': p.get('symbol'),
                'strategy': p.get('strategy', '').replace('CryptoWave_', ''),
                'entry_price': p.get('entry_price'),
                'current_sl': p.get('trailing_sl_price') or p.get('stop_loss'),
                'take_profit': p.get('take_profit'),
                'is_demo': p.get('is_demo', 1)
            } for p in positions],
            'performance': performance,
            'system': 'CryptoWave Hopper',
            'last_sync': datetime.now().isoformat()
        }


# === Quick Test ===
if __name__ == '__main__':
    print("Testing CryptoWave DB Integration...")
    
    integration = CryptoWaveDBIntegration(user_id=1, is_demo=True)
    
    # Test registration
    success = integration.register_trade_entry(
        symbol='BTCUSDT',
        strategy='Scalping',
        entry_price=87500.0,
        stop_loss=87000.0,
        take_profit=88500.0,
        quantity=0.01,
        confidence=0.75,
        market_condition='sideways'
    )
    
    print(f"Registration: {'✅' if success else '❌'}")
    
    # Test update
    success = integration.update_trailing_stop('BTCUSDT', 87200.0)
    print(f"Update SL: {'✅' if success else '❌'}")
    
    # Test exit
    success = integration.record_trade_exit(
        symbol='BTCUSDT',
        exit_price=88000.0,
        exit_reason='take_profit',
        pnl_pct=0.57,
        pnl_usd=5.70
    )
    print(f"Exit: {'✅' if success else '❌'}")
    
    # Test sync
    sync_data = integration.sync_with_mobile_app()
    print(f"Sync data: {json.dumps(sync_data, indent=2, default=str)}")
    
    print("\n✅ DB Integration test complete!")
