"""
Smart Stop-Loss Engine for CryptoWave Hopper
Advanced risk management with trailing stops, ATR-based adjustment, and partial exits.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from datetime import datetime
import numpy as np

@dataclass
class StopLossConfig:
    """Configuration for Smart Stop-Loss"""
    # Initial SL
    initial_sl_atr_mult: float = 1.5      # SL = Entry - (ATR * mult)
    
    # Break-Even
    be_trigger_rr: float = 1.0            # Move to BE at 1.0R profit
    be_buffer_pct: float = 0.2            # Add 0.2% buffer above entry
    
    # Trailing Stop
    trail_start_rr: float = 1.5           # Start trailing at 1.5R
    trail_atr_mult: float = 1.5           # Trail distance = ATR * mult
    
    # Partial Exit
    partial_exit_rr: float = 2.0          # Exit 50% at 2.0R
    partial_exit_pct: float = 0.50        # Exit 50% of position
    
    # Time-based
    stagnation_bars: int = 16             # Exit if no profit after X bars
    stagnation_threshold: float = 0.002   # 0.2% minimum profit needed
    max_hold_bars: int = 96               # Max hold time (24 hours @ 15m)
    
    # Max Loss
    max_loss_pct: float = 0.02            # 2% max loss per trade

@dataclass
class PositionState:
    """Track position state for SL management"""
    entry_price: float
    current_sl: float
    original_sl: float
    take_profit: float
    peak_price: float
    bars_held: int = 0
    be_triggered: bool = False
    trailing_active: bool = False
    partial_exit_done: bool = False
    partial_exit_price: float = 0.0

class SmartStopLoss:
    """
    Smart Stop-Loss Engine
    
    Features:
    - ATR-based initial stop
    - Dynamic break-even trigger
    - Trailing stop with ATR distance
    - Partial exits at profit targets
    - Stagnation detection
    - Time-based exits
    """
    
    def __init__(self, config: StopLossConfig = None):
        self.config = config or StopLossConfig()
    
    def calculate_initial_sl(self, entry_price: float, atr: float, side: str = 'long') -> float:
        """Calculate initial stop-loss based on ATR"""
        sl_distance = atr * self.config.initial_sl_atr_mult
        
        if side == 'long':
            return entry_price - sl_distance
        else:
            return entry_price + sl_distance
    
    def calculate_take_profit(self, entry_price: float, stop_loss: float, rr_ratio: float = 2.0) -> float:
        """Calculate take-profit based on risk-reward ratio"""
        risk = abs(entry_price - stop_loss)
        
        if entry_price > stop_loss:  # Long
            return entry_price + (risk * rr_ratio)
        else:  # Short
            return entry_price - (risk * rr_ratio)
    
    def update(self, state: PositionState, current_price: float, atr: float) -> Tuple[PositionState, Optional[str]]:
        """
        Update stop-loss and check for exit signals
        
        Args:
            state: Current position state
            current_price: Current market price
            atr: Current ATR value
        
        Returns:
            Tuple of (updated_state, exit_reason or None)
        """
        entry = state.entry_price
        sl = state.current_sl
        original_risk = abs(entry - state.original_sl)
        
        if original_risk <= 0:
            return state, None
        
        # Calculate current R (risk multiple)
        current_pnl = current_price - entry
        current_rr = current_pnl / original_risk
        current_pnl_pct = current_pnl / entry
        
        # Increment bars held
        state.bars_held += 1
        
        # Update peak price
        if current_price > state.peak_price:
            state.peak_price = current_price
        
        # === CHECK EXITS ===
        
        # 1. Stop-Loss Hit
        if current_price <= state.current_sl:
            return state, 'stop_loss'
        
        # 2. Take-Profit Hit
        if current_price >= state.take_profit:
            return state, 'take_profit'
        
        # 3. Max Hold Time
        if state.bars_held >= self.config.max_hold_bars:
            return state, 'time_exit'
        
        # 4. Stagnation Exit
        if state.bars_held >= self.config.stagnation_bars:
            if current_pnl_pct < self.config.stagnation_threshold:
                return state, 'stagnation_exit'
        
        # === UPDATE STOP-LOSS ===
        
        # 1. Partial Exit Trigger
        if current_rr >= self.config.partial_exit_rr and not state.partial_exit_done:
            state.partial_exit_done = True
            state.partial_exit_price = current_price
            # Move SL to entry + small profit
            new_sl = entry * (1 + self.config.be_buffer_pct / 100)
            state.current_sl = max(state.current_sl, new_sl)
            # Return partial signal
            return state, 'partial_exit'
        
        # 2. Break-Even Trigger
        if current_rr >= self.config.be_trigger_rr and not state.be_triggered:
            state.be_triggered = True
            new_sl = entry * (1 + self.config.be_buffer_pct / 100)
            state.current_sl = max(state.current_sl, new_sl)
        
        # 3. Trailing Stop
        if current_rr >= self.config.trail_start_rr:
            if not state.trailing_active:
                state.trailing_active = True
            
            # Calculate trailing stop
            trail_distance = atr * self.config.trail_atr_mult
            trail_sl = state.peak_price - trail_distance
            
            # Only move SL up, never down
            state.current_sl = max(state.current_sl, trail_sl)
        
        return state, None
    
    def get_position_stats(self, state: PositionState, current_price: float) -> Dict:
        """Get current position statistics"""
        entry = state.entry_price
        original_risk = abs(entry - state.original_sl)
        
        if original_risk <= 0:
            return {}
        
        current_pnl = current_price - entry
        current_rr = current_pnl / original_risk
        current_pnl_pct = current_pnl / entry * 100
        
        return {
            'entry_price': entry,
            'current_price': current_price,
            'current_sl': state.current_sl,
            'take_profit': state.take_profit,
            'pnl_pct': current_pnl_pct,
            'current_rr': current_rr,
            'bars_held': state.bars_held,
            'be_triggered': state.be_triggered,
            'trailing_active': state.trailing_active,
            'partial_done': state.partial_exit_done,
            'peak_price': state.peak_price
        }
    
    def calculate_partial_pnl(self, entry: float, partial_exit: float, final_exit: float, partial_pct: float = 0.5) -> float:
        """Calculate weighted PnL for partial exit trades"""
        pnl1 = (partial_exit - entry) / entry * 100
        pnl2 = (final_exit - entry) / entry * 100
        
        return (partial_pct * pnl1) + ((1 - partial_pct) * pnl2)


class PositionSizer:
    """
    Position Sizing Engine
    
    Calculates optimal position size based on:
    - Risk per trade
    - Account balance
    - Stop-loss distance
    - Correlation with other positions
    """
    
    def __init__(self, 
                 capital: float = 10000,
                 max_risk_per_trade: float = 0.02,
                 max_position_pct: float = 0.15,
                 max_total_exposure: float = 0.50):
        self.capital = capital
        self.max_risk_per_trade = max_risk_per_trade
        self.max_position_pct = max_position_pct
        self.max_total_exposure = max_total_exposure
    
    def calculate_size(self, 
                       price: float, 
                       stop_loss: float,
                       current_exposure: float = 0.0) -> float:
        """
        Calculate position size based on risk
        
        Args:
            price: Entry price
            stop_loss: Stop-loss price
            current_exposure: Current total exposure as decimal
        
        Returns:
            Position size in base currency units
        """
        # Risk amount in USD
        risk_amount = self.capital * self.max_risk_per_trade
        
        # Risk per unit
        risk_per_unit = abs(price - stop_loss)
        if risk_per_unit <= 0:
            return 0
        
        # Size based on risk
        risk_based_size = risk_amount / risk_per_unit
        
        # Max size based on position limit
        max_position_value = self.capital * self.max_position_pct
        max_size = max_position_value / price
        
        # Adjust for current exposure
        remaining_exposure = self.max_total_exposure - current_exposure
        exposure_limit_size = (self.capital * remaining_exposure) / price
        
        # Take minimum of all limits
        final_size = min(risk_based_size, max_size, exposure_limit_size)
        
        return max(0, final_size)
    
    def kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate Kelly Criterion for optimal bet sizing
        
        Args:
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade %
            avg_loss: Average losing trade %
        
        Returns:
            Optimal fraction of capital to risk (0-1)
        """
        if avg_loss <= 0:
            return 0
        
        win_loss_ratio = abs(avg_win / avg_loss)
        kelly = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
        
        # Half-Kelly for safety
        return max(0, min(kelly * 0.5, 0.25))


# === Quick Test ===
if __name__ == '__main__':
    print("Testing Smart Stop-Loss Engine...")
    
    # Create engine
    sl_engine = SmartStopLoss()
    
    # Simulate position
    entry = 100.0
    atr = 2.0
    initial_sl = sl_engine.calculate_initial_sl(entry, atr)
    tp = sl_engine.calculate_take_profit(entry, initial_sl, 3.0)
    
    print(f"Entry: ${entry}")
    print(f"Initial SL: ${initial_sl:.2f}")
    print(f"Take Profit: ${tp:.2f}")
    
    state = PositionState(
        entry_price=entry,
        current_sl=initial_sl,
        original_sl=initial_sl,
        take_profit=tp,
        peak_price=entry
    )
    
    # Simulate price movement
    prices = [100, 101, 102, 103, 104, 105, 104.5, 106, 105, 107, 106]
    
    for i, price in enumerate(prices):
        state, exit_signal = sl_engine.update(state, price, atr)
        stats = sl_engine.get_position_stats(state, price)
        
        status = f"Bar {i+1}: Price=${price} | SL=${state.current_sl:.2f} | RR={stats.get('current_rr', 0):.2f}"
        if state.be_triggered:
            status += " [BE]"
        if state.trailing_active:
            status += " [TRAIL]"
        if exit_signal:
            status += f" -> EXIT: {exit_signal}"
        print(status)
        
        if exit_signal and exit_signal != 'partial_exit':
            break
    
    print("\n✅ Smart Stop-Loss test complete!")
