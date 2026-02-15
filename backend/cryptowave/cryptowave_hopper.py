"""
CryptoWave Hopper - AI-Powered Trading Bot
Main orchestrator for 24/7 automated trading with multi-strategy support.

Integrated with Cognitive Layer for intelligent decision making.
"""

import asyncio
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import Cognitive Layer (العقل)
try:
    from backend.cognitive import get_cognitive_trading_engine
    from backend.cognitive.cognitive_trading_engine import CognitiveTradingEngine
    COGNITIVE_AVAILABLE = True
except ImportError as e:
    COGNITIVE_AVAILABLE = False
    print(f"[WARN] Cognitive layer not available: {e}")

# Import Database Integration
try:
    from backend.cryptowave.db_integration import CryptoWaveDBIntegration
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

@dataclass
class Position:
    """Active trading position"""
    symbol: str
    entry_price: float
    quantity: float
    side: str  # 'long' or 'short'
    strategy: str
    entry_time: datetime
    stop_loss: float
    take_profit: float
    trailing_active: bool = False
    peak_price: float = 0.0

@dataclass
class TradeResult:
    """Completed trade result"""
    symbol: str
    strategy: str
    entry_price: float
    exit_price: float
    pnl_pct: float
    pnl_usd: float
    hold_time_minutes: int
    exit_reason: str

class CryptoWaveHopper:
    """
    Main Trading Bot Orchestrator
    
    Features:
    - 24/7 continuous operation
    - Multi-strategy support (Arbitrage, Scalping, Grid, DCA, Trend)
    - AI-powered trade selection
    - Smart risk management
    """
    
    def __init__(self, config: Dict[str, Any] = None, user_id: int = 1, is_demo: bool = True):
        self.config = config or self._default_config()
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[TradeResult] = []
        self.is_running = False
        self.strategies = {}
        self.user_id = user_id
        self.is_demo = is_demo
        
        # Initialize Cognitive Engine (العقل)
        if COGNITIVE_AVAILABLE:
            self.cognitive_engine = get_cognitive_trading_engine()
            print("[INIT] ✅ Cognitive Engine connected (AI brain active)")
        else:
            self.cognitive_engine = None
            print("[INIT] ⚠️ Cognitive Engine not available, using basic analysis")
        
        # Initialize Database Integration
        if DB_AVAILABLE:
            self.db_integration = CryptoWaveDBIntegration(user_id=user_id, is_demo=is_demo)
            print(f"[INIT] ✅ Database connected (user_id={user_id}, demo={is_demo})")
        else:
            self.db_integration = None
            print("[INIT] ⚠️ Database not available")
        
        # Performance tracking
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        
    def _default_config(self) -> Dict:
        return {
            # === Trading Settings ===
            'symbols': [
                'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
                'ADAUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT', 'MATICUSDT'
            ],
            'base_currency': 'USDT',
            'exchange': 'binance',
            
            # === Risk Management ===
            'max_risk_per_trade': 0.02,  # 2% max loss per trade
            'max_daily_loss': 0.05,      # 5% max daily loss
            'max_positions': 5,           # Max concurrent positions
            'position_size_pct': 0.10,   # 10% of capital per position
            
            # === AI Settings ===
            'ai_confidence_threshold': 0.70,  # 70% confidence minimum
            'use_ai_prediction': True,
            
            # === Strategy Selection ===
            'enabled_strategies': ['scalping', 'trend_following', 'dca'],
            'auto_select_strategy': True,
            
            # === Timing ===
            'data_interval': '1m',
            'loop_interval_seconds': 60,
        }
    
    def fetch_market_data(self, symbol: str, interval: str = '1m', limit: int = 500) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from Binance"""
        try:
            url = f"https://api.binance.com/api/v3/klines"
            params = {'symbol': symbol, 'interval': interval, 'limit': limit}
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            df = pd.DataFrame(data, columns=[
                'ts', 'o', 'h', 'l', 'c', 'v', 'close_time',
                'quote_vol', 'trades', 'taker_base', 'taker_quote', 'ignore'
            ])
            
            for col in ['o', 'h', 'l', 'c', 'v']:
                df[col] = df[col].astype(float)
            df['ts'] = pd.to_datetime(df['ts'], unit='ms')
            
            return df[['ts', 'o', 'h', 'l', 'c', 'v']]
        except Exception as e:
            print(f"[ERROR] Failed to fetch data for {symbol}: {e}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        c = df['c']
        h = df['h']
        l = df['l']
        
        # EMAs
        df['ema21'] = c.ewm(span=21).mean()
        df['ema50'] = c.ewm(span=50).mean()
        df['ema200'] = c.ewm(span=200).mean()
        
        # ATR
        tr1 = h - l
        tr2 = abs(h - c.shift(1))
        tr3 = abs(l - c.shift(1))
        df['atr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()
        
        # RSI
        delta = c.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = c.ewm(span=12).mean()
        ema26 = c.ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_mid'] = c.rolling(20).mean()
        df['bb_std'] = c.rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * 2)
        
        # ADX
        df['adx'] = self._calculate_adx(h, l, c, 14)
        
        # Volume
        df['vol_ma'] = df['v'].rolling(20).mean()
        
        return df
    
    def _calculate_adx(self, high, low, close, period):
        """Calculate ADX indicator"""
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        
        plus_di = 100 * (plus_dm.ewm(alpha=1/period).mean() / atr)
        minus_di = 100 * (abs(minus_dm).ewm(alpha=1/period).mean() / atr)
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        return dx.rolling(period).mean()
    
    def get_market_condition(self, df: pd.DataFrame) -> str:
        """Determine current market condition"""
        if len(df) < 50:
            return 'unknown'
        
        latest = df.iloc[-1]
        adx = latest['adx']
        rsi = latest['rsi']
        price = latest['c']
        ema200 = latest['ema200']
        
        # Strong Trend
        if adx > 30:
            if price > ema200:
                return 'strong_uptrend'
            else:
                return 'strong_downtrend'
        
        # Weak Trend / Range
        if adx < 25:
            if rsi < 30:
                return 'oversold_range'
            elif rsi > 70:
                return 'overbought_range'
            else:
                return 'sideways'
        
        return 'moderate_trend'
    
    def select_strategy(self, market_condition: str, ai_prediction: Optional[Dict] = None) -> str:
        """Select optimal strategy based on market conditions"""
        strategy_map = {
            'strong_uptrend': 'trend_following',
            'strong_downtrend': 'trend_following',  # For shorts if enabled
            'oversold_range': 'dca',
            'overbought_range': 'scalping',
            'sideways': 'grid_trading',
            'moderate_trend': 'scalping',
            'unknown': 'scalping'
        }
        
        selected = strategy_map.get(market_condition, 'scalping')
        
        # Override with AI if high confidence
        if ai_prediction and ai_prediction.get('confidence', 0) > 0.80:
            if ai_prediction['direction'] == 'up':
                selected = 'trend_following'
            elif ai_prediction['direction'] == 'down':
                selected = 'scalping'  # Quick exit on shorts
        
        return selected
    
    def check_entry_signal(self, symbol: str, df: pd.DataFrame, strategy: str) -> Optional[Dict]:
        """Check if entry conditions are met"""
        if len(df) < 50:
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Common filters
        volume_ok = latest['v'] > latest['vol_ma']
        
        if strategy == 'trend_following':
            # Uptrend + Pullback + Bounce
            uptrend = latest['c'] > latest['ema21'] > latest['ema50']
            pullback = 0.5 <= ((df['c'].rolling(20).max().iloc[-1] - latest['c']) / df['c'].rolling(20).max().iloc[-1] * 100) <= 3.0
            macd_pos = latest['macd_hist'] > 0
            bounce = latest['c'] > latest['o'] and prev['c'] < prev['o']
            
            if uptrend and pullback and macd_pos and bounce and volume_ok:
                return {
                    'action': 'buy',
                    'strategy': strategy,
                    'confidence': 0.75,
                    'reason': 'Trend pullback bounce'
                }
        
        elif strategy == 'scalping':
            # RSI reversal + Volume
            oversold = latest['rsi'] < 35
            near_bb = latest['c'] <= latest['bb_lower'] * 1.01
            bounce = latest['c'] > latest['o'] and prev['c'] < prev['o']
            
            if oversold and near_bb and bounce and volume_ok:
                return {
                    'action': 'buy',
                    'strategy': strategy,
                    'confidence': 0.70,
                    'reason': 'Oversold bounce at BB'
                }
        
        elif strategy == 'dca':
            # Price significantly below MA
            below_ma = latest['c'] < latest['ema50'] * 0.95
            rsi_low = latest['rsi'] < 40
            
            if below_ma and rsi_low:
                return {
                    'action': 'buy',
                    'strategy': strategy,
                    'confidence': 0.65,
                    'reason': 'DCA accumulation zone'
                }
        
        return None
    
    def calculate_position_size(self, price: float, stop_loss: float) -> float:
        """Calculate position size based on risk"""
        capital = 10000  # Placeholder - should be from account
        risk_amount = capital * self.config['max_risk_per_trade']
        risk_per_unit = abs(price - stop_loss)
        
        if risk_per_unit <= 0:
            return 0
        
        position_size = risk_amount / risk_per_unit
        max_size = capital * self.config['position_size_pct'] / price
        
        return min(position_size, max_size)
    
    def manage_position(self, position: Position, current_price: float, atr: float) -> Optional[str]:
        """Manage open position - returns exit reason if should exit"""
        entry = position.entry_price
        sl = position.stop_loss
        tp = position.take_profit
        
        # Update peak for trailing
        if current_price > position.peak_price:
            position.peak_price = current_price
        
        # Calculate current R
        risk = entry - position.stop_loss
        if risk <= 0:
            return None
        current_r = (current_price - entry) / risk
        
        # Trailing Stop Activation (after 1.5R)
        if current_r >= 1.5 and not position.trailing_active:
            position.trailing_active = True
            new_sl = entry * 1.005  # Move to BE + buffer
            position.stop_loss = max(position.stop_loss, new_sl)
        
        # Dynamic Trailing
        if position.trailing_active and current_price > position.peak_price * 0.99:
            trail_sl = position.peak_price - (atr * 1.5)
            position.stop_loss = max(position.stop_loss, trail_sl)
        
        # Check exits
        if current_price <= position.stop_loss:
            return 'stop_loss'
        if current_price >= position.take_profit:
            return 'take_profit'
        
        return None
    
    async def run_cycle(self):
        """Single trading cycle - uses Cognitive Layer for decisions"""
        for symbol in self.config['symbols']:
            # Skip if max positions reached
            if len(self.positions) >= self.config['max_positions']:
                break
            
            # Skip if already in position for this symbol
            if symbol in self.positions:
                # Manage existing position
                pos = self.positions[symbol]
                df = self.fetch_market_data(symbol)
                if df is not None:
                    df = self.calculate_indicators(df)
                    current_price = df.iloc[-1]['c']
                    atr = df.iloc[-1]['atr']
                    exit_reason = self.manage_position(pos, current_price, atr)
                    if exit_reason:
                        # Close position
                        pnl = (current_price - pos.entry_price) / pos.entry_price * 100
                        print(f"[CLOSE] {symbol} | {exit_reason} | PnL: {pnl:+.2f}%")
                        
                        # Record exit in database
                        if self.db_integration:
                            self.db_integration.record_trade_exit(
                                symbol=symbol,
                                exit_price=current_price,
                                exit_reason=exit_reason,
                                pnl_pct=pnl,
                                pnl_usd=pnl * 10  # Placeholder
                            )
                        
                        del self.positions[symbol]
                        self.total_trades += 1
                        if pnl > 0:
                            self.winning_trades += 1
                continue
            
            # Fetch data for multiple timeframes
            df_1h = self.fetch_market_data(symbol, '1h', 200)
            df_15m = self.fetch_market_data(symbol, '15m', 200)
            
            if df_1h is None or df_15m is None:
                continue
            
            # Calculate indicators
            df_1h = self.calculate_indicators(df_1h)
            df_15m = self.calculate_indicators(df_15m)
            
            # === Use Cognitive Engine for Analysis ===
            if self.cognitive_engine and COGNITIVE_AVAILABLE:
                try:
                    # Prepare context with multi-timeframe data
                    additional_context = {
                        'df_1h': df_1h,
                        'df_15m': df_15m
                    }
                    
                    # Get AI decision from Cognitive Layer
                    analysis = self.cognitive_engine.analyze(
                        symbol=symbol,
                        df=df_1h,  # Primary timeframe
                        additional_context=additional_context
                    )
                    
                    if analysis.should_trade:
                        # Execute trade based on Cognitive decision
                        entry_price = analysis.entry_price or df_1h.iloc[-1]['c']
                        sl = analysis.stop_loss_price or (entry_price * 0.98)
                        tp = analysis.take_profit_price or (entry_price * 1.04)
                        
                        # Create position
                        pos = Position(
                            symbol=symbol,
                            entry_price=entry_price,
                            quantity=self.calculate_position_size(entry_price, sl),
                            side='long',
                            strategy=analysis.strategy.strategy.value if analysis.strategy else 'cognitive',
                            entry_time=datetime.now(),
                            stop_loss=sl,
                            take_profit=tp,
                            peak_price=entry_price
                        )
                        self.positions[symbol] = pos
                        
                        # Register in database
                        if self.db_integration:
                            self.db_integration.register_trade_entry(
                                symbol=symbol,
                                strategy=pos.strategy,
                                entry_price=entry_price,
                                stop_loss=sl,
                                take_profit=tp,
                                quantity=pos.quantity,
                                confidence=analysis.confidence,
                                market_condition=analysis.market_state.state.value if analysis.market_state else ''
                            )
                        
                        print(f"[🧠 COGNITIVE] {symbol} @ {entry_price:.4f} | "
                              f"Strategy: {pos.strategy} | Confidence: {analysis.confidence:.0f}%")
                    else:
                        # Cognitive decided not to trade
                        print(f"[🧠 ABSTAIN] {symbol} | {analysis.summary[:50]}...")
                        
                except Exception as e:
                    print(f"[ERROR] Cognitive analysis failed for {symbol}: {e}")
                    # Fallback to basic analysis
                    self._fallback_basic_analysis(symbol, df_1h)
            else:
                # Fallback to basic analysis without Cognitive
                self._fallback_basic_analysis(symbol, df_1h)
    
    def _fallback_basic_analysis(self, symbol: str, df: pd.DataFrame):
        """Fallback basic analysis when Cognitive not available"""
        condition = self.get_market_condition(df)
        strategy = self.select_strategy(condition)
        signal = self.check_entry_signal(symbol, df, strategy)
        
        if signal:
            latest = df.iloc[-1]
            entry_price = latest['c']
            atr = latest['atr']
            sl = entry_price - (atr * 1.5)
            tp = entry_price + (atr * 3.0)
            
            pos = Position(
                symbol=symbol,
                entry_price=entry_price,
                quantity=self.calculate_position_size(entry_price, sl),
                side='long',
                strategy=strategy,
                entry_time=datetime.now(),
                stop_loss=sl,
                take_profit=tp,
                peak_price=entry_price
            )
            self.positions[symbol] = pos
            
            if self.db_integration:
                self.db_integration.register_trade_entry(
                    symbol=symbol,
                    strategy=strategy,
                    entry_price=entry_price,
                    stop_loss=sl,
                    take_profit=tp,
                    quantity=pos.quantity,
                    confidence=signal.get('confidence', 0.6),
                    market_condition=condition
                )
            
            print(f"[BASIC] {symbol} @ {entry_price:.4f} | Strategy: {strategy}")
    
    async def run(self):
        """Main 24/7 loop"""
        print("=" * 60)
        print("🚀 CryptoWave Hopper - Starting...")
        print("=" * 60)
        self.is_running = True
        
        while self.is_running:
            try:
                cycle_start = time.time()
                await self.run_cycle()
                
                # Status update
                win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
                print(f"[STATUS] Positions: {len(self.positions)} | Trades: {self.total_trades} | WR: {win_rate:.1f}%")
                
                # Wait for next cycle
                elapsed = time.time() - cycle_start
                sleep_time = max(0, self.config['loop_interval_seconds'] - elapsed)
                await asyncio.sleep(sleep_time)
                
            except KeyboardInterrupt:
                print("\n[STOP] Shutting down...")
                self.is_running = False
            except Exception as e:
                print(f"[ERROR] Cycle error: {e}")
                await asyncio.sleep(10)
    
    def stop(self):
        """Stop the bot"""
        self.is_running = False


# === Quick Test ===
if __name__ == '__main__':
    print("Testing CryptoWave Hopper Core...")
    
    bot = CryptoWaveHopper()
    
    # Test data fetch
    df = bot.fetch_market_data('BTCUSDT', '15m', 100)
    if df is not None:
        df = bot.calculate_indicators(df)
        condition = bot.get_market_condition(df)
        print(f"Market Condition: {condition}")
        
        strategy = bot.select_strategy(condition)
        print(f"Selected Strategy: {strategy}")
        
        signal = bot.check_entry_signal('BTCUSDT', df, strategy)
        print(f"Entry Signal: {signal}")
    
    print("✅ Core test complete!")
