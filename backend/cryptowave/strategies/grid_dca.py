"""
Grid Trading Strategy for CryptoWave Hopper
Places buy/sell orders in a grid pattern to profit from range-bound markets.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class GridLevel:
    """Single grid level"""
    price: float
    type: str  # 'buy' or 'sell'
    filled: bool = False
    fill_time: Optional[str] = None

@dataclass
class GridConfig:
    """Grid trading configuration"""
    grid_levels: int = 10
    grid_spacing_pct: float = 0.5  # 0.5% between levels
    position_per_level_pct: float = 0.05  # 5% of capital per level
    upper_bound_pct: float = 3.0  # Upper range from current
    lower_bound_pct: float = 3.0  # Lower range from current

class GridTradingStrategy:
    """
    Grid Trading Strategy
    
    Creates a grid of buy/sell orders around the current price.
    Profits from price oscillations in range-bound markets.
    """
    
    def __init__(self, config: GridConfig = None):
        self.config = config or GridConfig()
        self.active_grids: Dict[str, List[GridLevel]] = {}
    
    def calculate_grid_levels(self, current_price: float) -> Tuple[List[GridLevel], List[GridLevel]]:
        """
        Calculate buy and sell grid levels
        
        Returns:
            Tuple of (buy_levels, sell_levels)
        """
        cfg = self.config
        
        # Calculate range
        upper_price = current_price * (1 + cfg.upper_bound_pct / 100)
        lower_price = current_price * (1 - cfg.lower_bound_pct / 100)
        
        # Calculate number of levels each side
        levels_each_side = cfg.grid_levels // 2
        
        # Calculate spacing
        total_range = upper_price - lower_price
        spacing = total_range / cfg.grid_levels
        
        buy_levels = []
        sell_levels = []
        
        # Buy levels below current price
        for i in range(1, levels_each_side + 1):
            price = current_price - (i * spacing)
            if price >= lower_price:
                buy_levels.append(GridLevel(price=price, type='buy'))
        
        # Sell levels above current price
        for i in range(1, levels_each_side + 1):
            price = current_price + (i * spacing)
            if price <= upper_price:
                sell_levels.append(GridLevel(price=price, type='sell'))
        
        return buy_levels, sell_levels
    
    def check_for_fills(self, symbol: str, current_price: float, high: float, low: float) -> List[GridLevel]:
        """Check which grid levels have been filled"""
        if symbol not in self.active_grids:
            return []
        
        filled = []
        for level in self.active_grids[symbol]:
            if level.filled:
                continue
            
            # Buy triggered if price dropped to level
            if level.type == 'buy' and low <= level.price:
                level.filled = True
                filled.append(level)
            
            # Sell triggered if price rose to level
            if level.type == 'sell' and high >= level.price:
                level.filled = True
                filled.append(level)
        
        return filled
    
    def should_create_grid(self, df: pd.DataFrame) -> bool:
        """Determine if market is suitable for grid trading"""
        if len(df) < 50:
            return False
        
        # Calculate ADX
        h = df['h']
        l = df['l']
        c = df['c']
        
        plus_dm = h.diff()
        minus_dm = l.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr = pd.concat([h - l, abs(h - c.shift(1)), abs(l - c.shift(1))], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        
        plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / atr)
        minus_di = 100 * (abs(minus_dm).ewm(alpha=1/14).mean() / atr)
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.rolling(14).mean().iloc[-1]
        
        # Grid works best in low-trend markets
        if adx < 25:
            return True
        
        return False
    
    def calculate_grid_profit(self, buy_price: float, sell_price: float, position_size: float) -> float:
        """Calculate profit from a completed grid cycle"""
        profit = (sell_price - buy_price) * position_size
        fees = (buy_price + sell_price) * position_size * 0.001  # 0.1% fee each way
        return profit - fees
    
    def get_market_suitability(self, df: pd.DataFrame) -> float:
        """Calculate how suitable market is for grid trading (0-1)"""
        if len(df) < 50:
            return 0.5
        
        c = df['c']
        
        # Check for range-bound behavior
        price_range = (c.max() - c.min()) / c.mean() * 100
        
        score = 0.5
        
        # Ideal range for grid: 2-8%
        if 2 <= price_range <= 8:
            score += 0.3
        elif 1 <= price_range <= 10:
            score += 0.15
        
        # Low trend strength
        if self.should_create_grid(df):
            score += 0.2
        
        return min(score, 1.0)


class DCAStrategy:
    """
    Dollar Cost Averaging Strategy
    
    Accumulates positions during dips by buying at regular intervals
    or when price drops below certain thresholds.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'dip_threshold_pct': 3.0,  # Buy when price drops 3% from recent high
            'max_dca_levels': 5,
            'level_spacing_pct': 2.0,  # 2% between DCA levels
            'position_per_level_pct': 0.05,  # 5% of capital per level
        }
        self.dca_positions: Dict[str, List[Dict]] = {}
    
    def find_dca_entry(self, df: pd.DataFrame) -> Optional[Dict]:
        """Find DCA entry opportunities"""
        if len(df) < 50:
            return None
        
        c = df['c']
        latest = df.iloc[-1]
        cfg = self.config
        
        # Find recent high (20-bar)
        recent_high = c.rolling(20).max().iloc[-1]
        current_price = latest['c']
        
        # Calculate dip percentage
        dip_pct = (recent_high - current_price) / recent_high * 100
        
        # Check if significant dip
        if dip_pct >= cfg['dip_threshold_pct']:
            # Additional confirmation: RSI low
            delta = c.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss.replace(0, 1)
            rsi = 100 - (100 / (1 + rs))
            
            if rsi.iloc[-1] < 40:
                return {
                    'action': 'buy',
                    'price': current_price,
                    'dip_pct': dip_pct,
                    'rsi': rsi.iloc[-1],
                    'reason': f'DCA: {dip_pct:.1f}% dip from high, RSI {rsi.iloc[-1]:.1f}'
                }
        
        return None
    
    def calculate_average_price(self, positions: List[Dict]) -> float:
        """Calculate average entry price for DCA positions"""
        if not positions:
            return 0
        
        total_value = sum(p['price'] * p['quantity'] for p in positions)
        total_quantity = sum(p['quantity'] for p in positions)
        
        return total_value / total_quantity if total_quantity > 0 else 0
    
    def get_market_suitability(self, df: pd.DataFrame) -> float:
        """Calculate how suitable market is for DCA (0-1)"""
        if len(df) < 50:
            return 0.5
        
        c = df['c']
        
        # DCA works best in downtrends or corrections
        ema50 = c.ewm(span=50).mean().iloc[-1]
        current = c.iloc[-1]
        
        score = 0.5
        
        # Below EMA50 (correction)
        if current < ema50:
            score += 0.2
        
        # Significant drop from high
        recent_high = c.rolling(20).max().iloc[-1]
        dip = (recent_high - current) / recent_high * 100
        
        if dip >= 3:
            score += 0.15
        if dip >= 5:
            score += 0.15
        
        return min(score, 1.0)


# === Quick Test ===
if __name__ == '__main__':
    import requests
    
    print("Testing Grid Trading & DCA Strategies...")
    
    # Fetch data
    url = "https://api.binance.com/api/v3/klines"
    params = {'symbol': 'BTCUSDT', 'interval': '15m', 'limit': 100}
    response = requests.get(url, params=params)
    data = response.json()
    
    df = pd.DataFrame(data, columns=[
        'ts', 'o', 'h', 'l', 'c', 'v', 'close_time',
        'quote_vol', 'trades', 'taker_base', 'taker_quote', 'ignore'
    ])
    for col in ['o', 'h', 'l', 'c', 'v']:
        df[col] = df[col].astype(float)
    
    current_price = df.iloc[-1]['c']
    
    # Test Grid
    grid_strategy = GridTradingStrategy()
    buy_levels, sell_levels = grid_strategy.calculate_grid_levels(current_price)
    grid_suit = grid_strategy.get_market_suitability(df)
    
    print(f"\n📊 Grid Trading @ ${current_price:.2f}")
    print(f"   Suitability: {grid_suit:.0%}")
    print(f"   Buy Levels: {len(buy_levels)} | Sell Levels: {len(sell_levels)}")
    if buy_levels:
        print(f"   First Buy: ${buy_levels[0].price:.2f}")
    if sell_levels:
        print(f"   First Sell: ${sell_levels[0].price:.2f}")
    
    # Test DCA
    dca_strategy = DCAStrategy()
    dca_signal = dca_strategy.find_dca_entry(df)
    dca_suit = dca_strategy.get_market_suitability(df)
    
    print(f"\n📉 DCA Strategy")
    print(f"   Suitability: {dca_suit:.0%}")
    if dca_signal:
        print(f"   Signal: {dca_signal['reason']}")
    else:
        print("   No DCA entry detected")
    
    print("\n✅ Grid & DCA test complete!")
