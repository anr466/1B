"""
Scalping Strategy for CryptoWave Hopper
Quick trades on M1-M5 timeframes for small consistent profits.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from dataclasses import dataclass

@dataclass
class ScalpSignal:
    """Scalping trade signal"""
    action: str  # 'buy', 'sell', 'hold'
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    reason: str

class ScalpingStrategy:
    """
    Quick Scalping Strategy
    
    Targets small, frequent profits from short-term price movements.
    Uses RSI, Bollinger Bands, and Volume for entry signals.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'bb_squeeze_threshold': 0.02,
            'volume_multiplier': 1.2,
            'min_atr_pct': 0.3,
            'sl_atr_mult': 1.0,  # Tight stop
            'tp_rr': 1.5,  # Quick TP
        }
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate scalping-specific indicators"""
        c = df['c']
        h = df['h']
        l = df['l']
        v = df['v']
        
        # RSI (Fast)
        delta = c.diff()
        gain = delta.where(delta > 0, 0).rolling(7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(7).mean()
        rs = gain / loss.replace(0, 1)
        df['rsi_fast'] = 100 - (100 / (1 + rs))
        
        # RSI Standard
        gain14 = delta.where(delta > 0, 0).rolling(14).mean()
        loss14 = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs14 = gain14 / loss14.replace(0, 1)
        df['rsi'] = 100 - (100 / (1 + rs14))
        
        # Bollinger Bands
        df['bb_mid'] = c.rolling(20).mean()
        df['bb_std'] = c.rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
        df['bb_position'] = (c - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ATR
        tr1 = h - l
        tr2 = abs(h - c.shift(1))
        tr3 = abs(l - c.shift(1))
        df['atr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()
        df['atr_pct'] = df['atr'] / c * 100
        
        # Volume
        df['vol_ma'] = v.rolling(20).mean()
        df['vol_ratio'] = v / df['vol_ma']
        
        # Candle patterns
        df['is_green'] = c > df['o']
        df['is_red'] = c < df['o']
        df['body_pct'] = abs(c - df['o']) / c * 100
        
        # Momentum
        df['momentum'] = c - c.shift(3)
        
        return df
    
    def find_entry(self, df: pd.DataFrame) -> Optional[ScalpSignal]:
        """Find scalping entry signal"""
        if len(df) < 25:
            return None
        
        df = self.calculate_indicators(df)
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        cfg = self.config
        
        # Check volatility - need minimum movement
        if latest['atr_pct'] < cfg['min_atr_pct']:
            return None
        
        # === BUY SIGNALS ===
        
        # 1. RSI Oversold Bounce
        rsi_oversold = latest['rsi'] < cfg['rsi_oversold']
        rsi_turning = latest['rsi'] > prev['rsi']
        
        # 2. Near Bollinger Lower
        near_bb_low = latest['bb_position'] < 0.1
        
        # 3. Volume confirmation
        volume_spike = latest['vol_ratio'] > cfg['volume_multiplier']
        
        # 4. Bullish candle
        bullish = latest['is_green'] and prev['is_red']
        
        # Combined Buy Signal
        if rsi_oversold and rsi_turning and (near_bb_low or volume_spike) and bullish:
            entry = latest['c']
            atr = latest['atr']
            sl = entry - (atr * cfg['sl_atr_mult'])
            risk = entry - sl
            tp = entry + (risk * cfg['tp_rr'])
            
            return ScalpSignal(
                action='buy',
                confidence=0.70 + (0.1 if volume_spike else 0),
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                reason='RSI Oversold Bounce'
            )
        
        # === SELL SIGNALS (for shorts or exit longs) ===
        
        rsi_overbought = latest['rsi'] > cfg['rsi_overbought']
        rsi_falling = latest['rsi'] < prev['rsi']
        near_bb_high = latest['bb_position'] > 0.9
        bearish = latest['is_red'] and prev['is_green']
        
        if rsi_overbought and rsi_falling and (near_bb_high or volume_spike) and bearish:
            entry = latest['c']
            atr = latest['atr']
            sl = entry + (atr * cfg['sl_atr_mult'])
            risk = sl - entry
            tp = entry - (risk * cfg['tp_rr'])
            
            return ScalpSignal(
                action='sell',
                confidence=0.70 + (0.1 if volume_spike else 0),
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                reason='RSI Overbought Rejection'
            )
        
        return None
    
    def get_market_suitability(self, df: pd.DataFrame) -> float:
        """
        Calculate how suitable current market is for scalping (0-1)
        High volatility + range-bound = good for scalping
        """
        if len(df) < 30:
            return 0.5
        
        df = self.calculate_indicators(df)
        latest = df.iloc[-1]
        
        score = 0.5
        
        # Good volatility
        if 0.3 <= latest['atr_pct'] <= 2.0:
            score += 0.2
        
        # Not in extreme trend (ADX < 30)
        if 'adx' in df.columns and latest.get('adx', 25) < 30:
            score += 0.15
        
        # Bollinger squeeze (consolidation)
        if latest['bb_width'] < self.config['bb_squeeze_threshold']:
            score += 0.15
        
        return min(score, 1.0)


# === Quick Test ===
if __name__ == '__main__':
    import requests
    
    print("Testing Scalping Strategy...")
    
    # Fetch data
    url = "https://api.binance.com/api/v3/klines"
    params = {'symbol': 'BTCUSDT', 'interval': '5m', 'limit': 100}
    response = requests.get(url, params=params)
    data = response.json()
    
    df = pd.DataFrame(data, columns=[
        'ts', 'o', 'h', 'l', 'c', 'v', 'close_time',
        'quote_vol', 'trades', 'taker_base', 'taker_quote', 'ignore'
    ])
    for col in ['o', 'h', 'l', 'c', 'v']:
        df[col] = df[col].astype(float)
    
    strategy = ScalpingStrategy()
    signal = strategy.find_entry(df)
    suitability = strategy.get_market_suitability(df)
    
    print(f"Market Suitability: {suitability:.0%}")
    if signal:
        print(f"Signal: {signal.action.upper()} @ {signal.entry_price:.2f}")
        print(f"Reason: {signal.reason}")
        print(f"SL: {signal.stop_loss:.2f} | TP: {signal.take_profit:.2f}")
    else:
        print("No entry signal")
    
    print("✅ Scalping Strategy test complete!")
