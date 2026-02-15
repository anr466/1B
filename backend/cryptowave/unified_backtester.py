"""
CryptoWave Hopper - Unified Backtester
Comprehensive backtesting engine for all strategies with detailed performance analysis.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import requests
import time

# Import strategies
import sys
sys.path.insert(0, '/Users/anr/Desktop/trading_ai_bot/backend')

@dataclass
class BacktestTrade:
    """Single backtest trade result"""
    symbol: str
    strategy: str
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    exit_reason: str
    pnl_pct: float
    hold_bars: int
    entry_confidence: float = 0.0

@dataclass
class BacktestResult:
    """Complete backtest result"""
    trades: List[BacktestTrade]
    total_pnl: float
    win_rate: float
    avg_trade_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float
    trades_per_day: float
    avg_hold_time_mins: float

class CryptoWaveBacktester:
    """
    Unified Backtester for CryptoWave Hopper
    
    Tests all strategies on historical data with:
    - Multi-strategy support
    - AI prediction simulation
    - Smart stop-loss integration
    - Detailed performance metrics
    """
    
    def __init__(self):
        self.config = {
            # === Entry ===
            'adx_trend_min': 30,
            'adx_range_max': 35,
            'pullback_min': 0.5,
            'pullback_max': 3.0,
            'rsi_oversold': 35,
            'rsi_overbought': 65,
            
            # === Exit ===
            'sl_atr_mult': 1.5,
            'tp1_rr': 2.0,
            'tp2_rr': 5.0,
            'be_trigger_rr': 1.0,
            'trail_start_rr': 2.0,
            'stagnation_bars': 16,
            'max_hold_bars': 96,
            
            # === Risk ===
            'max_risk_pct': 0.02,
            'partial_exit_pct': 0.5,
        }
    
    def fetch_data(self, symbol: str, interval: str = '15m', days: int = 14) -> Optional[pd.DataFrame]:
        """Fetch historical OHLCV data"""
        try:
            limit = min(days * 96, 1000)  # 96 bars per day for 15m
            url = "https://api.binance.com/api/v3/klines"
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
            
            return self._calculate_indicators(df)
        except Exception as e:
            print(f"[ERROR] Failed to fetch {symbol}: {e}")
            return None
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        c = df['c']
        h = df['h']
        l = df['l']
        o = df['o']
        v = df['v']
        
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
        bb_std = c.rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + (bb_std * 2)
        df['bb_lower'] = df['bb_mid'] - (bb_std * 2)
        
        # ADX
        plus_dm = h.diff()
        minus_dm = l.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        atr_smooth = df['atr'].replace(0, 1)
        plus_di = 100 * (plus_dm.ewm(alpha=1/14).mean() / atr_smooth)
        minus_di = 100 * (abs(minus_dm).ewm(alpha=1/14).mean() / atr_smooth)
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1)) * 100
        df['adx'] = dx.rolling(14).mean()
        
        # Volume
        df['vol_ma'] = v.rolling(20).mean()
        
        # Candle patterns
        df['is_green'] = c > o
        df['is_red'] = c < o
        
        # Pullback
        high_20 = h.rolling(20).max()
        df['pullback_pct'] = (high_20 - c) / high_20 * 100
        
        return df.fillna(0)
    
    def _find_entry(self, df: pd.DataFrame, i: int) -> Tuple[bool, str, float]:
        """
        Find entry signal using multi-strategy approach
        Returns: (should_enter, strategy_name, confidence)
        """
        if i < 50:
            return False, "", 0
        
        r = df.iloc[i]
        prev = df.iloc[i-1]
        c = self.config
        
        # === Common Filters ===
        is_green = r['is_green']
        prev_red = prev['c'] < prev['o']
        volume_ok = r['v'] > r['vol_ma']
        
        # Reversal patterns
        is_engulfing = r['c'] > prev['o']
        prev_mid = (prev['o'] + prev['c']) / 2
        is_piercing = r['c'] > prev_mid
        body = abs(r['c'] - r['o'])
        lower_wick = min(r['c'], r['o']) - r['l']
        is_hammer = lower_wick > (body * 2) if body > 0 else False
        
        confirmed_reversal = is_green and prev_red and (is_engulfing or is_piercing or is_hammer)
        
        # Anti-chase filter
        candle_range = r['h'] - r['l']
        atr_val = r['atr'] if r['atr'] > 0 else r['c'] * 0.01
        is_chasing = candle_range > (atr_val * 2.0)
        
        # Crash filter
        is_crash = (r['adx'] > 40) and (r['c'] < r['ema50'])
        
        if not confirmed_reversal or not volume_ok or is_crash or is_chasing:
            return False, "", 0
        
        # === STRATEGY 1: TREND FOLLOWING ===
        is_uptrend = r['c'] > r['ema21'] > r['ema50']
        strong_trend = r['adx'] > c['adx_trend_min']
        pullback_ok = c['pullback_min'] <= r['pullback_pct'] <= c['pullback_max']
        macd_pos = r['macd_hist'] > 0
        
        if is_uptrend and strong_trend and pullback_ok and macd_pos and r['rsi'] < 70:
            return True, "Trend Following", 0.80
        
        # === STRATEGY 2: SCALPING (Range Reversal) ===
        is_range = r['adx'] < c['adx_range_max']
        if is_range:
            above_200 = r['c'] > r['ema200']
            rsi_threshold = 40 if above_200 else 30
            oversold = r['rsi'] < rsi_threshold
            near_bb = r['c'] <= r['bb_lower'] * 1.01
            
            if oversold and near_bb:
                return True, "Scalping", 0.75
        
        # === STRATEGY 3: DCA (Deep Value) ===
        deep_dip = r['pullback_pct'] > 5.0
        very_oversold = r['rsi'] < 25
        below_200 = r['c'] < r['ema200']
        
        if deep_dip and very_oversold and below_200 and confirmed_reversal:
            return True, "DCA", 0.70
        
        return False, "", 0
    
    def _manage_position(self, pos: Dict, r: pd.Series) -> Tuple[Optional[float], Optional[str]]:
        """
        Manage open position with smart exits
        Returns: (exit_price, exit_reason) or (None, None)
        """
        entry = pos['entry']
        sl = pos['sl']
        tp = pos['tp']
        sl_orig = pos['sl_orig']
        c = self.config
        
        current_price = r['c']
        high = r['h']
        low = r['l']
        atr = r['atr'] if r['atr'] > 0 else current_price * 0.01
        
        risk = entry - sl_orig
        if risk <= 0:
            return None, None
        
        current_rr = (current_price - entry) / risk
        current_pnl_pct = (current_price - entry) / entry
        bars_held = pos['bars'] + 1
        pos['bars'] = bars_held
        
        # Update peak
        if current_price > pos.get('peak', entry):
            pos['peak'] = current_price
        
        # === PARTIAL EXIT at TP1 ===
        if current_rr >= c['tp1_rr'] and not pos.get('tp1_hit'):
            pos['tp1_hit'] = True
            pos['tp1_price'] = current_price
            pos['sl'] = entry * 1.002  # Move to BE
        
        # === BREAK-EVEN ===
        if current_rr >= c['be_trigger_rr'] and not pos.get('be_moved') and not pos.get('tp1_hit'):
            pos['sl'] = max(pos['sl'], entry * 1.002)
            pos['be_moved'] = True
        
        # === TRAILING STOP ===
        if current_rr >= c['trail_start_rr']:
            trail_sl = pos['peak'] - (atr * 1.5)
            pos['sl'] = max(pos['sl'], trail_sl)
        
        # === CHECK EXITS ===
        
        # Stagnation
        if bars_held >= c['stagnation_bars'] and current_pnl_pct < 0.002:
            return current_price, 'stagnation'
        
        # Stop-Loss
        if low <= pos['sl']:
            return pos['sl'], 'stop_loss'
        
        # Take-Profit
        if high >= tp:
            return tp, 'take_profit'
        
        # Max Hold
        if bars_held >= c['max_hold_bars']:
            return current_price, 'time_exit'
        
        return None, None
    
    def backtest(self, symbol: str, days: int = 14) -> List[BacktestTrade]:
        """Run backtest on single symbol"""
        df = self.fetch_data(symbol, '15m', days)
        if df is None or len(df) < 100:
            return []
        
        trades = []
        pos = None
        c = self.config
        
        for i in range(50, len(df)):
            r = df.iloc[i]
            
            # Manage existing position
            if pos:
                exit_price, reason = self._manage_position(pos, r)
                
                if exit_price:
                    # Calculate PnL (with partial exit if applicable)
                    if pos.get('tp1_hit'):
                        pnl1 = (pos['tp1_price'] - pos['entry']) / pos['entry']
                        pnl2 = (exit_price - pos['entry']) / pos['entry']
                        total_pnl = (0.5 * pnl1) + (0.5 * pnl2)
                        reason = f"Partial_{reason}"
                    else:
                        total_pnl = (exit_price - pos['entry']) / pos['entry']
                    
                    trades.append(BacktestTrade(
                        symbol=symbol,
                        strategy=pos['strategy'],
                        entry_price=pos['entry'],
                        exit_price=exit_price,
                        entry_time=pos['time'],
                        exit_time=r['ts'],
                        exit_reason=reason,
                        pnl_pct=total_pnl * 100,
                        hold_bars=pos['bars'],
                        entry_confidence=pos['confidence']
                    ))
                    pos = None
                continue
            
            # Find new entry
            should_enter, strategy, confidence = self._find_entry(df, i)
            
            if should_enter:
                entry = r['c']
                atr = r['atr'] if r['atr'] > 0 else entry * 0.01
                sl = entry - (atr * c['sl_atr_mult'])
                risk = entry - sl
                tp = entry + (risk * c['tp2_rr'])
                
                pos = {
                    'entry': entry,
                    'sl': sl,
                    'sl_orig': sl,
                    'tp': tp,
                    'peak': entry,
                    'time': r['ts'],
                    'strategy': strategy,
                    'confidence': confidence,
                    'bars': 0,
                    'tp1_hit': False,
                    'be_moved': False
                }
        
        return trades
    
    def calculate_metrics(self, trades: List[BacktestTrade], days: int = 14) -> BacktestResult:
        """Calculate comprehensive performance metrics"""
        if not trades:
            return BacktestResult(
                trades=[], total_pnl=0, win_rate=0, avg_trade_pnl=0,
                max_drawdown=0, sharpe_ratio=0, profit_factor=0,
                trades_per_day=0, avg_hold_time_mins=0
            )
        
        pnls = [t.pnl_pct for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        total_pnl = sum(pnls)
        win_rate = len(wins) / len(trades) * 100 if trades else 0
        avg_pnl = np.mean(pnls) if pnls else 0
        
        # Profit Factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Max Drawdown
        cumulative = np.cumsum(pnls)
        peak = np.maximum.accumulate(cumulative)
        drawdown = peak - cumulative
        max_dd = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # Sharpe Ratio (simplified)
        if len(pnls) > 1:
            sharpe = np.mean(pnls) / np.std(pnls) * np.sqrt(252) if np.std(pnls) > 0 else 0
        else:
            sharpe = 0
        
        # Timing
        trades_per_day = len(trades) / days
        avg_hold = np.mean([t.hold_bars for t in trades]) * 15  # 15 min per bar
        
        return BacktestResult(
            trades=trades,
            total_pnl=total_pnl,
            win_rate=win_rate,
            avg_trade_pnl=avg_pnl,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            profit_factor=profit_factor,
            trades_per_day=trades_per_day,
            avg_hold_time_mins=avg_hold
        )
    
    def run_full_backtest(self, symbols: List[str], days: int = 14) -> Tuple[BacktestResult, str]:
        """
        Run full backtest on multiple symbols
        Returns: (result, markdown_report)
        """
        print("=" * 60)
        print("🚀 CryptoWave Hopper - Full Backtest")
        print("=" * 60)
        
        all_trades = []
        symbol_results = {}
        
        print(f"{'SYMBOL':<12} {'TRADES':<8} {'WIN%':<8} {'PNL%':<10} {'STRATEGY':<15}")
        print("-" * 55)
        
        for symbol in symbols:
            trades = self.backtest(symbol, days)
            all_trades.extend(trades)
            
            if trades:
                wins = len([t for t in trades if t.pnl_pct > 0])
                wr = wins / len(trades) * 100
                pnl = sum(t.pnl_pct for t in trades)
                strategies = set(t.strategy for t in trades)
                strat_str = '/'.join(strategies)[:15]
                print(f"{symbol:<12} {len(trades):<8} {wr:<8.1f} {pnl:+8.2f}%  {strat_str:<15}")
                symbol_results[symbol] = {'trades': len(trades), 'wr': wr, 'pnl': pnl}
            else:
                print(f"{symbol:<12} 0        0.0      0.00%    -")
                symbol_results[symbol] = {'trades': 0, 'wr': 0, 'pnl': 0}
            
            time.sleep(0.3)
        
        # Calculate overall metrics
        result = self.calculate_metrics(all_trades, days)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE SUMMARY")
        print("=" * 60)
        print(f"   Total Trades:    {len(all_trades)}")
        print(f"   Win Rate:        {result.win_rate:.1f}%")
        print(f"   Total PnL:       {result.total_pnl:+.2f}%")
        print(f"   Avg Trade:       {result.avg_trade_pnl:+.3f}%")
        print(f"   Profit Factor:   {result.profit_factor:.2f}")
        print(f"   Sharpe Ratio:    {result.sharpe_ratio:.2f}")
        print(f"   Max Drawdown:    {result.max_drawdown:.2f}%")
        print(f"   Trades/Day:      {result.trades_per_day:.1f}")
        print(f"   Avg Hold Time:   {result.avg_hold_time_mins:.0f} mins")
        print("=" * 60)
        
        # Generate report
        report = self._generate_report(result, symbol_results, days)
        
        return result, report
    
    def _generate_report(self, result: BacktestResult, symbol_results: Dict, days: int) -> str:
        """Generate markdown report"""
        report = f"""# 📊 CryptoWave Hopper - Backtest Report

## Performance Summary
- **Total Trades**: {len(result.trades)}
- **Win Rate**: {result.win_rate:.1f}%
- **Total PnL**: {result.total_pnl:+.2f}%
- **Profit Factor**: {result.profit_factor:.2f}
- **Sharpe Ratio**: {result.sharpe_ratio:.2f}
- **Max Drawdown**: {result.max_drawdown:.2f}%

## Strategy Breakdown
"""
        # Strategy stats
        strat_trades = {}
        for t in result.trades:
            if t.strategy not in strat_trades:
                strat_trades[t.strategy] = []
            strat_trades[t.strategy].append(t)
        
        for strat, trades in strat_trades.items():
            wins = len([t for t in trades if t.pnl_pct > 0])
            wr = wins / len(trades) * 100 if trades else 0
            pnl = sum(t.pnl_pct for t in trades)
            report += f"- **{strat}**: {len(trades)} trades ({wr:.1f}% WR) | PnL: {pnl:+.2f}%\n"
        
        report += "\n## Symbol Performance\n"
        report += "| Symbol | Trades | Win Rate | PnL |\n"
        report += "|--------|--------|----------|-----|\n"
        
        for sym, data in symbol_results.items():
            icon = "✅" if data['pnl'] > 0 else "❌" if data['pnl'] < 0 else "➖"
            report += f"| {sym} | {data['trades']} | {data['wr']:.1f}% | {icon} {data['pnl']:+.2f}% |\n"
        
        report += "\n## Trade Log (Top 10)\n"
        report += "| Symbol | Strategy | Entry | Exit | Reason | PnL |\n"
        report += "|--------|----------|-------|------|--------|-----|\n"
        
        sorted_trades = sorted(result.trades, key=lambda x: x.pnl_pct, reverse=True)[:10]
        for t in sorted_trades:
            icon = "✅" if t.pnl_pct > 0 else "❌"
            report += f"| {t.symbol} | {t.strategy} | {t.entry_price:.4f} | {t.exit_price:.4f} | {t.exit_reason} | {icon} {t.pnl_pct:+.2f}% |\n"
        
        return report


# === Main Execution ===
if __name__ == '__main__':
    # Test symbols - diverse set
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
        'ADAUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT', 'MATICUSDT',
        'LTCUSDT', 'UNIUSDT', 'ATOMUSDT', 'NEARUSDT', 'APTUSDT',
        'ARBUSDT', 'OPUSDT', 'INJUSDT', 'LDOUSDT', 'STXUSDT'
    ]
    
    backtester = CryptoWaveBacktester()
    result, report = backtester.run_full_backtest(symbols, days=14)
    
    # Save report
    with open('/Users/anr/Desktop/trading_ai_bot/cryptowave_backtest_report.md', 'w') as f:
        f.write(report)
    
    print("\n📄 Report saved to: cryptowave_backtest_report.md")
