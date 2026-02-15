#!/usr/bin/env python3
"""
Comprehensive V7 Strategy Backtest — اختبار خلفي شامل
=====================================================
يختبر استراتيجية ScalpingV7Engine على بيانات حقيقية من Binance
مع محاكاة كاملة لدورة التداول: دخول → إدارة → خروج → رصيد

المخرجات:
- إحصائيات شاملة (WR, PF, DD, Sharpe, etc.)
- تحليل أنماط السوق (UP, DOWN, NEUTRAL)
- تحليل كل عملة على حدة
- تحليل أسباب الخروج
- تحليل الضعف والقوة
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import json

logging.basicConfig(level=logging.WARNING)

from backend.strategies.scalping_v7_engine import ScalpingV7Engine, V7_CONFIG

# ============================================================
# DATA FETCHER — جلب بيانات حقيقية من Binance
# ============================================================
def fetch_binance_klines(symbol: str, interval: str = '1h', limit: int = 1000) -> pd.DataFrame:
    """Fetch historical klines from Binance REST API"""
    import urllib.request
    import json as _json
    
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read().decode())
        
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        return df
    except Exception as e:
        print(f"  ❌ Error fetching {symbol}: {e}")
        return None


# ============================================================
# BACKTEST ENGINE
# ============================================================
class V7Backtester:
    def __init__(self, initial_balance: float = 10000.0):
        self.engine = ScalpingV7Engine()
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.peak_balance = initial_balance
        self.positions = []  # active positions
        self.trades = []     # completed trades
        self.balance_history = []
        self.max_drawdown = 0
        self.max_concurrent = 0
        
        # Config
        self.position_size_pct = V7_CONFIG['position_size_pct']
        self.max_positions = V7_CONFIG['max_positions']
        self.commission_pct = V7_CONFIG['commission_pct']
        self.slippage_pct = V7_CONFIG['slippage_pct']
    
    def run_backtest(self, all_data: Dict[str, pd.DataFrame]):
        """
        Run bar-by-bar backtest across all symbols simultaneously.
        all_data: {symbol: DataFrame with indicators}
        
        CRITICAL: Every function sees ONLY data up to current bar (no look-ahead).
        """
        # Get common time range
        min_len = min(len(df) for df in all_data.values())
        print(f"\n  📊 Bars to simulate: {min_len}")
        
        start_idx = 60  # skip warmup period for indicators
        
        for i in range(start_idx, min_len):
            # 1. Manage open positions (check exits)
            self._manage_positions(all_data, i)
            
            # 2. Scan for new entries
            if len(self.positions) < self.max_positions:
                self._scan_entries(all_data, i)
            
            # 3. Track balance
            self._track_balance(all_data, i)
            
            # Track max concurrent
            if len(self.positions) > self.max_concurrent:
                self.max_concurrent = len(self.positions)
        
        # Force close remaining positions at last bar
        self._force_close_all(all_data, min_len - 1)
    
    def _manage_positions(self, all_data, bar_idx):
        """Check exit conditions for all open positions"""
        closed = []
        for pos in self.positions:
            symbol = pos['symbol']
            df = all_data[symbol]
            
            if bar_idx >= len(df):
                continue
            
            entry = pos['entry_price']
            side = pos['side']
            peak = pos['peak']
            trail = pos['trail']
            sl = pos['sl']
            hold_hours = bar_idx - pos['entry_bar']  # 1 bar = 1 hour
            
            # Build position data for V7 exit check
            pos_data = {
                'entry_price': entry,
                'side': side,
                'peak': peak,
                'trail': trail,
                'sl': sl,
                'hold_hours': hold_hours,
            }
            
            # ✅ CRITICAL: slice df to current bar ONLY (prevent look-ahead bias)
            df_slice = df.iloc[:bar_idx + 1]
            exit_result = self.engine.check_exit_signal(df_slice, pos_data)
            
            # Update position tracking
            updated = exit_result.get('updated', {})
            if 'peak' in updated:
                pos['peak'] = updated['peak']
            if 'trail' in updated:
                pos['trail'] = updated['trail']
            
            if exit_result['should_exit']:
                exit_price = exit_result['exit_price']
                reason = exit_result['reason']
                
                # Apply slippage
                if side == 'LONG':
                    exit_price *= (1 - self.slippage_pct)
                else:
                    exit_price *= (1 + self.slippage_pct)
                
                self._close_position(pos, exit_price, reason, bar_idx, df)
                closed.append(pos)
        
        for pos in closed:
            self.positions.remove(pos)
    
    def _scan_entries(self, all_data, bar_idx):
        """Scan all symbols for entry signals"""
        for symbol, df in all_data.items():
            if len(self.positions) >= self.max_positions:
                break
            
            # Skip if already have position in this symbol
            if any(p['symbol'] == symbol for p in self.positions):
                continue
            
            if bar_idx >= len(df) - 1:
                continue
            
            # Get trend and check entry (use bar_idx-1 as the "completed" bar)
            trend = self.engine.get_4h_trend(df, bar_idx - 1)
            signal = self.engine.detect_entry(df, trend, bar_idx - 1)
            
            if signal:
                # Execute at NEXT bar open (realistic — signal on bar_idx-1, execute at bar_idx open)
                next_bar = df.iloc[bar_idx]
                entry_price = next_bar['open']
                
                # Apply slippage
                if signal['side'] == 'LONG':
                    entry_price *= (1 + self.slippage_pct)
                else:
                    entry_price *= (1 - self.slippage_pct)
                
                # Position sizing — FIXED based on initial balance to avoid compounding distortion
                position_size = self.initial_balance * self.position_size_pct
                if position_size < 10 or position_size > self.balance:
                    continue
                
                quantity = position_size / entry_price
                commission = position_size * self.commission_pct
                
                # SL
                if signal['side'] == 'LONG':
                    sl_price = entry_price * (1 - V7_CONFIG['sl_pct'])
                else:
                    sl_price = entry_price * (1 + V7_CONFIG['sl_pct'])
                
                # Deduct from balance
                self.balance -= (position_size + commission)
                
                self.positions.append({
                    'symbol': symbol,
                    'side': signal['side'],
                    'entry_price': entry_price,
                    'quantity': quantity,
                    'position_size': position_size,
                    'entry_commission': commission,
                    'sl': sl_price,
                    'peak': entry_price,
                    'trail': 0,
                    'entry_bar': bar_idx,
                    'entry_time': df.iloc[bar_idx]['timestamp'] if 'timestamp' in df.columns else bar_idx,
                    'signal': signal,
                    'trend': trend,
                })
    
    def _close_position(self, pos, exit_price, reason, bar_idx, df):
        """Close a position and record the trade"""
        entry = pos['entry_price']
        side = pos['side']
        qty = pos['quantity']
        position_size = pos['position_size']
        
        # Calculate PnL
        if side == 'LONG':
            pnl_raw = (exit_price - entry) * qty
        else:
            pnl_raw = (entry - exit_price) * qty
        
        # Exit commission
        exit_commission = abs(exit_price * qty) * self.commission_pct
        pnl = pnl_raw - exit_commission
        pnl_pct = pnl / position_size if position_size > 0 else 0
        
        # Return to balance
        self.balance += position_size + pnl
        
        hold_hours = bar_idx - pos['entry_bar']
        
        self.trades.append({
            'symbol': pos['symbol'],
            'side': side,
            'entry_price': entry,
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct * 100,
            'position_size': position_size,
            'hold_hours': hold_hours,
            'reason': reason,
            'trend': pos['trend'],
            'strategy': pos['signal'].get('strategy', 'unknown'),
            'score': pos['signal'].get('score', 0),
            'entry_time': pos['entry_time'],
            'exit_time': df.iloc[bar_idx]['timestamp'] if 'timestamp' in df.columns else bar_idx,
        })
    
    def _force_close_all(self, all_data, bar_idx):
        """Force close all remaining positions"""
        for pos in list(self.positions):
            symbol = pos['symbol']
            df = all_data[symbol]
            if bar_idx < len(df):
                exit_price = df.iloc[bar_idx]['close']
                self._close_position(pos, exit_price, 'FORCE_CLOSE', bar_idx, df)
        self.positions.clear()
    
    def _track_balance(self, all_data, bar_idx):
        """Track balance and drawdown"""
        # Calculate unrealized PnL
        unrealized = 0
        for pos in self.positions:
            symbol = pos['symbol']
            df = all_data[symbol]
            if bar_idx < len(df):
                current_price = df.iloc[bar_idx]['close']
                if pos['side'] == 'LONG':
                    unrealized += (current_price - pos['entry_price']) * pos['quantity']
                else:
                    unrealized += (pos['entry_price'] - current_price) * pos['quantity']
        
        equity = self.balance + sum(p['position_size'] for p in self.positions) + unrealized
        
        if equity > self.peak_balance:
            self.peak_balance = equity
        
        dd = (self.peak_balance - equity) / self.peak_balance if self.peak_balance > 0 else 0
        if dd > self.max_drawdown:
            self.max_drawdown = dd
        
        self.balance_history.append({
            'bar': bar_idx,
            'balance': self.balance,
            'equity': equity,
            'drawdown': dd,
            'positions': len(self.positions),
        })
    
    def get_report(self) -> Dict:
        """Generate comprehensive backtest report"""
        if not self.trades:
            return {'error': 'No trades executed'}
        
        trades_df = pd.DataFrame(self.trades)
        
        total_trades = len(trades_df)
        winners = trades_df[trades_df['pnl'] > 0]
        losers = trades_df[trades_df['pnl'] <= 0]
        
        win_count = len(winners)
        loss_count = len(losers)
        win_rate = win_count / total_trades * 100 if total_trades > 0 else 0
        
        total_pnl = trades_df['pnl'].sum()
        total_pnl_pct = total_pnl / self.initial_balance * 100
        
        gross_profit = winners['pnl'].sum() if len(winners) > 0 else 0
        gross_loss = abs(losers['pnl'].sum()) if len(losers) > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        avg_win = winners['pnl_pct'].mean() if len(winners) > 0 else 0
        avg_loss = losers['pnl_pct'].mean() if len(losers) > 0 else 0
        avg_trade = trades_df['pnl_pct'].mean()
        
        avg_hold = trades_df['hold_hours'].mean()
        
        # Consecutive analysis
        streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        current_streak_type = None
        
        for _, trade in trades_df.iterrows():
            is_win = trade['pnl'] > 0
            if current_streak_type == is_win:
                streak += 1
            else:
                streak = 1
                current_streak_type = is_win
            if is_win:
                max_win_streak = max(max_win_streak, streak)
            else:
                max_loss_streak = max(max_loss_streak, streak)
        
        # Sharpe ratio (annualized, assuming 1h bars)
        daily_returns = []
        running_pnl = 0
        for _, trade in trades_df.iterrows():
            running_pnl += trade['pnl']
            daily_returns.append(trade['pnl_pct'])
        
        returns_std = np.std(daily_returns) if len(daily_returns) > 1 else 1
        sharpe = (np.mean(daily_returns) / returns_std * np.sqrt(252 * 24 / avg_hold)) if returns_std > 0 and avg_hold > 0 else 0
        
        # Expectancy
        expectancy = (win_rate / 100 * avg_win) + ((100 - win_rate) / 100 * avg_loss)
        
        # Per-symbol analysis
        symbol_stats = {}
        for symbol in trades_df['symbol'].unique():
            sym_trades = trades_df[trades_df['symbol'] == symbol]
            sym_winners = sym_trades[sym_trades['pnl'] > 0]
            sym_losers = sym_trades[sym_trades['pnl'] <= 0]
            sym_gp = sym_winners['pnl'].sum() if len(sym_winners) > 0 else 0
            sym_gl = abs(sym_losers['pnl'].sum()) if len(sym_losers) > 0 else 0
            symbol_stats[symbol] = {
                'trades': len(sym_trades),
                'win_rate': len(sym_winners) / len(sym_trades) * 100 if len(sym_trades) > 0 else 0,
                'total_pnl': sym_trades['pnl'].sum(),
                'pf': sym_gp / sym_gl if sym_gl > 0 else float('inf'),
                'avg_pnl_pct': sym_trades['pnl_pct'].mean(),
            }
        
        # Per-trend analysis
        trend_stats = {}
        for trend in ['UP', 'DOWN', 'NEUTRAL']:
            t_trades = trades_df[trades_df['trend'] == trend]
            if len(t_trades) > 0:
                t_winners = t_trades[t_trades['pnl'] > 0]
                trend_stats[trend] = {
                    'trades': len(t_trades),
                    'win_rate': len(t_winners) / len(t_trades) * 100,
                    'total_pnl': t_trades['pnl'].sum(),
                    'avg_pnl_pct': t_trades['pnl_pct'].mean(),
                }
        
        # Per-exit-reason analysis
        reason_stats = {}
        for reason in trades_df['reason'].unique():
            r_trades = trades_df[trades_df['reason'] == reason]
            r_winners = r_trades[r_trades['pnl'] > 0]
            reason_stats[reason] = {
                'count': len(r_trades),
                'pct': len(r_trades) / total_trades * 100,
                'win_rate': len(r_winners) / len(r_trades) * 100 if len(r_trades) > 0 else 0,
                'avg_pnl_pct': r_trades['pnl_pct'].mean(),
                'total_pnl': r_trades['pnl'].sum(),
            }
        
        # Per-strategy analysis
        strategy_stats = {}
        for strat in trades_df['strategy'].unique():
            s_trades = trades_df[trades_df['strategy'] == strat]
            s_winners = s_trades[s_trades['pnl'] > 0]
            strategy_stats[strat] = {
                'count': len(s_trades),
                'win_rate': len(s_winners) / len(s_trades) * 100 if len(s_trades) > 0 else 0,
                'avg_pnl_pct': s_trades['pnl_pct'].mean(),
                'total_pnl': s_trades['pnl'].sum(),
            }
        
        # Per-side analysis
        long_trades = trades_df[trades_df['side'] == 'LONG']
        short_trades = trades_df[trades_df['side'] == 'SHORT']
        
        long_wr = len(long_trades[long_trades['pnl'] > 0]) / len(long_trades) * 100 if len(long_trades) > 0 else 0
        short_wr = len(short_trades[short_trades['pnl'] > 0]) / len(short_trades) * 100 if len(short_trades) > 0 else 0
        
        # Score analysis
        score_bins = [(4, 6), (6, 8), (8, 10), (10, 20)]
        score_stats = {}
        for low, high in score_bins:
            s_trades = trades_df[(trades_df['score'] >= low) & (trades_df['score'] < high)]
            if len(s_trades) > 0:
                s_winners = s_trades[s_trades['pnl'] > 0]
                score_stats[f"{low}-{high}"] = {
                    'count': len(s_trades),
                    'win_rate': len(s_winners) / len(s_trades) * 100,
                    'avg_pnl_pct': s_trades['pnl_pct'].mean(),
                }
        
        # Hourly analysis
        if 'entry_time' in trades_df.columns:
            try:
                trades_df['hour'] = pd.to_datetime(trades_df['entry_time']).dt.hour
                hour_stats = {}
                for hour in sorted(trades_df['hour'].unique()):
                    h_trades = trades_df[trades_df['hour'] == hour]
                    h_winners = h_trades[h_trades['pnl'] > 0]
                    hour_stats[int(hour)] = {
                        'trades': len(h_trades),
                        'win_rate': len(h_winners) / len(h_trades) * 100 if len(h_trades) > 0 else 0,
                        'avg_pnl_pct': h_trades['pnl_pct'].mean(),
                    }
            except Exception:
                hour_stats = {}
        else:
            hour_stats = {}
        
        # Monthly PnL
        monthly_pnl = {}
        if 'entry_time' in trades_df.columns:
            try:
                trades_df['month'] = pd.to_datetime(trades_df['entry_time']).dt.strftime('%Y-%m')
                for month in sorted(trades_df['month'].unique()):
                    m_trades = trades_df[trades_df['month'] == month]
                    m_winners = m_trades[m_trades['pnl'] > 0]
                    monthly_pnl[month] = {
                        'trades': len(m_trades),
                        'win_rate': len(m_winners) / len(m_trades) * 100 if len(m_trades) > 0 else 0,
                        'pnl': m_trades['pnl'].sum(),
                        'pnl_pct': m_trades['pnl'].sum() / self.initial_balance * 100,
                    }
            except Exception:
                pass
        
        return {
            'summary': {
                'initial_balance': self.initial_balance,
                'final_balance': self.balance,
                'total_pnl': total_pnl,
                'total_pnl_pct': total_pnl_pct,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'max_drawdown': self.max_drawdown * 100,
                'sharpe_ratio': sharpe,
                'expectancy': expectancy,
                'avg_trade_pnl_pct': avg_trade,
                'avg_win_pct': avg_win,
                'avg_loss_pct': avg_loss,
                'avg_hold_hours': avg_hold,
                'max_win_streak': max_win_streak,
                'max_loss_streak': max_loss_streak,
                'max_concurrent_positions': self.max_concurrent,
                'win_count': win_count,
                'loss_count': loss_count,
                'long_trades': len(long_trades),
                'short_trades': len(short_trades),
                'long_wr': long_wr,
                'short_wr': short_wr,
            },
            'per_symbol': symbol_stats,
            'per_trend': trend_stats,
            'per_exit_reason': reason_stats,
            'per_strategy': strategy_stats,
            'per_score': score_stats,
            'per_hour': hour_stats,
            'monthly_pnl': monthly_pnl,
        }


# ============================================================
# MAIN
# ============================================================
def main():
    symbols = [
        'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT', 'NEARUSDT',
        'SUIUSDT', 'ARBUSDT', 'APTUSDT', 'INJUSDT', 'LINKUSDT',
    ]
    
    print("=" * 70)
    print("🔬 COMPREHENSIVE V7 BACKTEST — اختبار خلفي شامل")
    print("=" * 70)
    print(f"  Strategy: ScalpingV7 (SL={V7_CONFIG['sl_pct']*100}%, Trail={V7_CONFIG['trailing_activation']*100}%/{V7_CONFIG['trailing_distance']*100}%)")
    print(f"  Symbols: {len(symbols)}")
    print(f"  Timeframe: 1h")
    print(f"  Commission: {V7_CONFIG['commission_pct']*100}% | Slippage: {V7_CONFIG['slippage_pct']*100}%")
    
    # Fetch data
    print("\n📥 Fetching historical data from Binance...")
    all_data = {}
    engine = ScalpingV7Engine()
    
    for sym in symbols:
        print(f"  📊 {sym}...", end=" ", flush=True)
        df = fetch_binance_klines(sym, '1h', 1000)
        if df is not None and len(df) >= 100:
            df = engine.prepare_data(df)
            all_data[sym] = df
            days = len(df) / 24
            print(f"✅ {len(df)} bars ({days:.0f} days)")
        else:
            print("❌ SKIPPED")
    
    if not all_data:
        print("❌ No data fetched!")
        return
    
    min_bars = min(len(df) for df in all_data.values())
    print(f"\n  📊 Total symbols: {len(all_data)} | Common bars: {min_bars} ({min_bars/24:.0f} days)")
    
    # Run backtest
    print("\n🚀 Running backtest...")
    bt = V7Backtester(initial_balance=10000.0)
    bt.run_backtest(all_data)
    
    # Generate report
    report = bt.get_report()
    
    if 'error' in report:
        print(f"\n❌ {report['error']}")
        return
    
    s = report['summary']
    
    # ============================================================
    # PRINT REPORT
    # ============================================================
    print("\n" + "=" * 70)
    print("📊 نتائج الاختبار الخلفي الشامل")
    print("=" * 70)
    
    print(f"""
┌─────────────────────────────────────────┐
│         الملخص العام                      │
├─────────────────────────────────────────┤
│  الرصيد الأولي:     ${s['initial_balance']:>12,.2f}        │
│  الرصيد النهائي:    ${s['final_balance']:>12,.2f}        │
│  إجمالي الربح:      ${s['total_pnl']:>+12,.2f} ({s['total_pnl_pct']:+.2f}%) │
│  عدد الصفقات:       {s['total_trades']:>6}               │
│  نسبة الفوز:        {s['win_rate']:>6.1f}%              │
│  عامل الربحية (PF): {s['profit_factor']:>6.2f}               │
│  أقصى تراجع (DD):   {s['max_drawdown']:>6.2f}%              │
│  Sharpe Ratio:       {s['sharpe_ratio']:>6.2f}               │
│  Expectancy:         {s['expectancy']:>+6.3f}%             │
├─────────────────────────────────────────┤
│  متوسط صفقة:        {s['avg_trade_pnl_pct']:>+6.3f}%             │
│  متوسط ربح:         {s['avg_win_pct']:>+6.3f}%             │
│  متوسط خسارة:       {s['avg_loss_pct']:>+6.3f}%             │
│  متوسط احتفاظ:      {s['avg_hold_hours']:>6.1f}h               │
│  أطول سلسلة فوز:    {s['max_win_streak']:>6}               │
│  أطول سلسلة خسارة:  {s['max_loss_streak']:>6}               │
│  أقصى صفقات متزامنة:{s['max_concurrent_positions']:>6}               │
├─────────────────────────────────────────┤
│  LONG:  {s['long_trades']:>4} صفقة | WR={s['long_wr']:.1f}%            │
│  SHORT: {s['short_trades']:>4} صفقة | WR={s['short_wr']:.1f}%            │
└─────────────────────────────────────────┘""")

    # Per symbol
    print("\n📊 تحليل كل عملة:")
    print(f"  {'Symbol':<12} {'Trades':>7} {'WR%':>7} {'PF':>7} {'PnL$':>10} {'Avg%':>8}")
    print("  " + "-" * 55)
    sorted_symbols = sorted(report['per_symbol'].items(), key=lambda x: x[1]['total_pnl'], reverse=True)
    for sym, st in sorted_symbols:
        pf_str = f"{st['pf']:.2f}" if st['pf'] < 100 else "∞"
        print(f"  {sym:<12} {st['trades']:>7} {st['win_rate']:>6.1f}% {pf_str:>7} ${st['total_pnl']:>+9.2f} {st['avg_pnl_pct']:>+7.3f}%")

    # Per trend
    print("\n📊 تحليل أنماط السوق:")
    print(f"  {'Trend':<10} {'Trades':>7} {'WR%':>7} {'PnL$':>10} {'Avg%':>8}")
    print("  " + "-" * 45)
    for trend, st in report['per_trend'].items():
        print(f"  {trend:<10} {st['trades']:>7} {st['win_rate']:>6.1f}% ${st['total_pnl']:>+9.2f} {st['avg_pnl_pct']:>+7.3f}%")

    # Per exit reason
    print("\n📊 تحليل أسباب الخروج:")
    print(f"  {'Reason':<15} {'Count':>6} {'%':>6} {'WR%':>7} {'Avg%':>8} {'PnL$':>10}")
    print("  " + "-" * 58)
    sorted_reasons = sorted(report['per_exit_reason'].items(), key=lambda x: x[1]['count'], reverse=True)
    for reason, st in sorted_reasons:
        print(f"  {reason:<15} {st['count']:>6} {st['pct']:>5.1f}% {st['win_rate']:>6.1f}% {st['avg_pnl_pct']:>+7.3f}% ${st['total_pnl']:>+9.2f}")

    # Per strategy
    print("\n📊 تحليل أنماط الدخول:")
    print(f"  {'Strategy':<15} {'Count':>6} {'WR%':>7} {'Avg%':>8} {'PnL$':>10}")
    print("  " + "-" * 50)
    sorted_strats = sorted(report['per_strategy'].items(), key=lambda x: x[1]['total_pnl'], reverse=True)
    for strat, st in sorted_strats:
        print(f"  {strat:<15} {st['count']:>6} {st['win_rate']:>6.1f}% {st['avg_pnl_pct']:>+7.3f}% ${st['total_pnl']:>+9.2f}")

    # Per score
    if report['per_score']:
        print("\n📊 تحليل جودة الإشارة (Score):")
        print(f"  {'Score':<10} {'Count':>6} {'WR%':>7} {'Avg%':>8}")
        print("  " + "-" * 35)
        for score, st in report['per_score'].items():
            print(f"  {score:<10} {st['count']:>6} {st['win_rate']:>6.1f}% {st['avg_pnl_pct']:>+7.3f}%")

    # Monthly PnL
    if report['monthly_pnl']:
        print("\n📊 الأداء الشهري:")
        print(f"  {'Month':<10} {'Trades':>7} {'WR%':>7} {'PnL$':>10} {'PnL%':>8}")
        print("  " + "-" * 45)
        for month, st in report['monthly_pnl'].items():
            print(f"  {month:<10} {st['trades']:>7} {st['win_rate']:>6.1f}% ${st['pnl']:>+9.2f} {st['pnl_pct']:>+7.2f}%")

    # ============================================================
    # ANALYSIS & RECOMMENDATIONS
    # ============================================================
    print("\n" + "=" * 70)
    print("🔍 التحليل والتوصيات")
    print("=" * 70)
    
    issues = []
    strengths = []
    
    # WR analysis
    if s['win_rate'] < 45:
        issues.append(f"❌ نسبة الفوز منخفضة ({s['win_rate']:.1f}%) — الحد الأدنى المقبول 45%")
    elif s['win_rate'] < 50:
        issues.append(f"⚠️ نسبة الفوز حدية ({s['win_rate']:.1f}%) — مقبولة مع PF>1.2")
    else:
        strengths.append(f"✅ نسبة فوز جيدة ({s['win_rate']:.1f}%)")
    
    # PF analysis
    if s['profit_factor'] < 1.0:
        issues.append(f"❌ عامل الربحية < 1.0 ({s['profit_factor']:.2f}) — النظام يخسر!")
    elif s['profit_factor'] < 1.2:
        issues.append(f"⚠️ عامل الربحية هامشي ({s['profit_factor']:.2f}) — أي تكلفة إضافية تمحو الأرباح")
    elif s['profit_factor'] < 1.5:
        strengths.append(f"✅ عامل ربحية مقبول ({s['profit_factor']:.2f})")
    else:
        strengths.append(f"✅ عامل ربحية ممتاز ({s['profit_factor']:.2f})")
    
    # DD analysis
    if s['max_drawdown'] > 15:
        issues.append(f"❌ التراجع الأقصى خطير ({s['max_drawdown']:.1f}%) — الحد 10%")
    elif s['max_drawdown'] > 10:
        issues.append(f"⚠️ التراجع مرتفع ({s['max_drawdown']:.1f}%)")
    else:
        strengths.append(f"✅ التراجع محكوم ({s['max_drawdown']:.1f}%)")
    
    # Avg trade
    if s['avg_trade_pnl_pct'] <= 0:
        issues.append(f"❌ متوسط الصفقة سالب ({s['avg_trade_pnl_pct']:+.3f}%) — لا توجد ميزة")
    else:
        strengths.append(f"✅ متوسط الصفقة إيجابي ({s['avg_trade_pnl_pct']:+.3f}%)")
    
    # Loss streak
    if s['max_loss_streak'] > 8:
        issues.append(f"⚠️ أطول سلسلة خسائر مقلقة ({s['max_loss_streak']} صفقات)")
    
    # SHORT analysis
    if s['short_trades'] > 0 and s['short_wr'] < 40:
        issues.append(f"⚠️ صفقات SHORT ضعيفة (WR={s['short_wr']:.1f}%) — قد يكون أفضل تعطيلها")
    
    # Symbol weakness
    for sym, st in report['per_symbol'].items():
        if st['trades'] >= 5 and st['win_rate'] < 35:
            issues.append(f"⚠️ {sym}: أداء سيء (WR={st['win_rate']:.1f}%, PnL=${st['total_pnl']:.2f}) — مرشح للقائمة السوداء")
    
    # Exit reason analysis
    for reason, st in report['per_exit_reason'].items():
        if st['count'] > 5 and st['win_rate'] < 30:
            issues.append(f"⚠️ خروج {reason} سيء (WR={st['win_rate']:.1f}%, Avg={st['avg_pnl_pct']:+.3f}%)")
    
    # Stagnant positions
    stagnant = report['per_exit_reason'].get('STAGNANT', {})
    if stagnant and stagnant.get('pct', 0) > 20:
        issues.append(f"⚠️ {stagnant['pct']:.1f}% من الصفقات راكدة — يحتاج تحسين فلتر الدخول")
    
    # Max hold
    max_hold = report['per_exit_reason'].get('MAX_HOLD', {})
    if max_hold and max_hold.get('pct', 0) > 15:
        issues.append(f"⚠️ {max_hold['pct']:.1f}% من الصفقات تصل الحد الأقصى — يحتاج إدارة أفضل")
    
    print("\n💪 نقاط القوة:")
    for s in strengths:
        print(f"  {s}")
    
    print(f"\n⚠️ نقاط الضعف ({len(issues)}):")
    for i in issues:
        print(f"  {i}")
    
    # Final verdict
    print("\n" + "=" * 70)
    total_score = len(strengths) - len(issues)
    if report['summary']['profit_factor'] >= 1.3 and report['summary']['win_rate'] >= 48 and report['summary']['max_drawdown'] < 12:
        print("🟢 الحكم: النظام مربح ومستقر — يحتاج مراقبة مستمرة")
    elif report['summary']['profit_factor'] >= 1.1 and report['summary']['win_rate'] >= 45:
        print("🟡 الحكم: النظام يعمل لكن يحتاج تحسينات")
    else:
        print("🔴 الحكم: النظام يحتاج إعادة تقييم جدية")
    print("=" * 70)
    
    return report


if __name__ == '__main__':
    main()
