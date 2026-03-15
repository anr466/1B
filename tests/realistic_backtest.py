#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Realistic Backtest Engine — يحاكي التداول الفعلي بدقة
=====================================================
- بيانات حقيقية من Binance Public API
- نفس ScalpingV7Engine المُستخدم في النظام الحي
- محاكاة: Commission + Slippage + Position Sizing
- تقرير مفصّل لكل صفقة مع أسباب الخروج
"""

import sys
import os
import json
import time
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from backend.strategies.scalping_v7_engine import ScalpingV7Engine, V7_CONFIG

logging.basicConfig(level=logging.WARNING, format='%(message)s')
logger = logging.getLogger(__name__)

# ============================================================
# 1. DATA FETCHER — Binance Public API (no key needed)
# ============================================================

def fetch_binance_klines(symbol: str, interval: str = '1h',
                         days: int = 60, limit_per_req: int = 1000) -> pd.DataFrame:
    """Fetch historical klines from Binance public API"""
    url = "https://api.binance.com/api/v3/klines"
    all_data = []
    
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    
    current_start = start_time
    while current_start < end_time:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': current_start,
            'endTime': end_time,
            'limit': limit_per_req
        }
        
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  ⚠️ Error fetching {symbol}: {e}")
            break
        
        if not data:
            break
        
        all_data.extend(data)
        current_start = data[-1][0] + 1
        
        if len(data) < limit_per_req:
            break
        
        time.sleep(0.2)  # Rate limit respect
    
    if not all_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]


# ============================================================
# 2. REALISTIC BACKTESTER
# ============================================================

class RealisticBacktester:
    """
    Backtest engine that mirrors live trading behavior exactly.
    
    Key realism features:
    - Entry at NEXT bar open (not at signal bar close)
    - Commission & slippage deducted
    - Position sizing from balance
    - Max concurrent positions enforced
    - Exit checks use HIGH/LOW for SL/trailing (not just close)
    - Bar-by-bar simulation with proper state tracking
    """
    
    def __init__(self, config: Dict = None, initial_balance: float = 1000.0):
        self.config = {**V7_CONFIG, **(config or {})}
        self.engine = ScalpingV7Engine(self.config)
        self.initial_balance = initial_balance
        self.balance = initial_balance
        
        # Trading state
        self.open_positions: List[Dict] = []
        self.closed_trades: List[Dict] = []
        self.equity_curve: List[Dict] = []
        
        # Costs
        self.commission_pct = self.config.get('commission_pct', 0.001)
        self.slippage_pct = self.config.get('slippage_pct', 0.0005)
        
        # Position sizing
        self.position_size_pct = self.config.get('position_size_pct', 0.06)
        self.max_positions = self.config.get('max_positions', 5)
    
    def run(self, symbol: str, df: pd.DataFrame) -> Dict:
        """Run backtest on prepared data for one symbol"""
        if df is None or len(df) < 80:
            return {'error': f'Insufficient data for {symbol}'}
        
        # Prepare indicators
        df_prepared = self.engine.prepare_data(df)
        if df_prepared is None:
            return {'error': f'Failed to prepare data for {symbol}'}
        
        # Bar-by-bar simulation (start from bar 60 for indicator warmup)
        for i in range(60, len(df_prepared)):
            current_bar = df_prepared.iloc[i]
            bar_time = current_bar.get('timestamp', i)
            
            # Record equity
            unrealized = self._calc_unrealized_pnl(current_bar['close'])
            self.equity_curve.append({
                'time': bar_time,
                'balance': self.balance,
                'equity': self.balance + unrealized,
                'open_positions': len(self.open_positions)
            })
            
            # 1. Check exits for open positions (using current bar H/L/C)
            self._check_exits(df_prepared, i, symbol)
            
            # 2. Check for new entry signals (on previous completed bar)
            if len(self.open_positions) < self.max_positions:
                trend = self.engine.get_4h_trend(df_prepared, i - 1)
                signal = self.engine.detect_entry(df_prepared, trend, i - 1)
                
                if signal:
                    # Enter at current bar OPEN (simulating next-bar entry)
                    entry_price = current_bar['open']
                    # Apply slippage
                    if signal['side'] == 'LONG':
                        entry_price *= (1 + self.slippage_pct)
                    else:
                        entry_price *= (1 - self.slippage_pct)
                    
                    self._open_position(symbol, signal, entry_price, bar_time, i)
        
        return self._generate_report(symbol)
    
    def _open_position(self, symbol: str, signal: Dict, entry_price: float,
                       bar_time, bar_idx: int):
        """Open a new position"""
        # Position sizing — FIXED SIZE based on initial balance (realistic)
        position_value = self.initial_balance * self.position_size_pct
        if position_value < 10:  # Min $10
            return
        
        quantity = position_value / entry_price
        
        # Commission on entry
        entry_commission = position_value * self.commission_pct
        self.balance -= entry_commission
        
        # Calculate SL from signal
        sl = signal.get('stop_loss', 0)
        if sl <= 0:
            if signal['side'] == 'LONG':
                sl = entry_price * (1 - self.config['sl_pct'])
            else:
                sl = entry_price * (1 + self.config['sl_pct'])
        
        position = {
            'symbol': symbol,
            'side': signal['side'],
            'entry_price': entry_price,
            'quantity': quantity,
            'position_value': position_value,
            'stop_loss': sl,
            'trailing_stop': 0,
            'peak': entry_price,
            'entry_time': bar_time,
            'entry_bar': bar_idx,
            'entry_commission': entry_commission,
            'signal_strategy': signal.get('strategy', 'unknown'),
            'signal_score': signal.get('score', 0),
            'signal_confidence': signal.get('confidence', 0),
            'signal_type': signal.get('signal_type', ''),
            'hold_bars': 0,
        }
        
        self.open_positions.append(position)
    
    def _check_exits(self, df: pd.DataFrame, bar_idx: int, symbol: str):
        """Check exit conditions for all open positions"""
        positions_to_close = []
        
        for pos in self.open_positions:
            pos['hold_bars'] += 1
            hold_hours = pos['hold_bars']  # 1h bars = hours
            
            # Build position data for engine
            pos_data = {
                'entry_price': pos['entry_price'],
                'side': pos['side'],
                'peak': pos['peak'],
                'trail': pos['trailing_stop'],
                'sl': pos['stop_loss'],
                'entry_time': pos['entry_time'],
                'hold_hours': hold_hours,
            }
            
            # Use engine's exit logic with data up to current bar
            df_slice = df.iloc[:bar_idx + 1]
            exit_result = self.engine.check_exit_signal(df_slice, pos_data)
            
            if exit_result.get('should_exit', False):
                exit_price = exit_result.get('exit_price', df.iloc[bar_idx]['close'])
                reason = exit_result.get('reason', 'UNKNOWN')
                
                # Apply slippage on exit
                if pos['side'] == 'LONG':
                    exit_price *= (1 - self.slippage_pct)
                else:
                    exit_price *= (1 + self.slippage_pct)
                
                positions_to_close.append((pos, exit_price, reason, bar_idx))
            else:
                # Update trailing/peak from engine result
                updated = exit_result.get('updated', {})
                if 'peak' in updated:
                    pos['peak'] = updated['peak']
                if 'trail' in updated:
                    pos['trailing_stop'] = updated['trail']
                if 'sl' in updated:
                    pos['stop_loss'] = updated['sl']
        
        # Close positions
        for pos, exit_price, reason, idx in positions_to_close:
            self._close_position(pos, exit_price, reason, df.iloc[idx])
    
    def _close_position(self, pos: Dict, exit_price: float, reason: str, bar):
        """Close a position and record the trade"""
        # PnL calculation
        if pos['side'] == 'LONG':
            pnl_pct = (exit_price - pos['entry_price']) / pos['entry_price']
        else:
            pnl_pct = (pos['entry_price'] - exit_price) / pos['entry_price']
        
        pnl_dollar = pos['position_value'] * pnl_pct
        
        # Exit commission
        exit_value = pos['position_value'] * (1 + pnl_pct)
        exit_commission = exit_value * self.commission_pct
        
        # Net PnL after commissions
        total_commission = pos['entry_commission'] + exit_commission
        net_pnl = pnl_dollar - exit_commission
        
        self.balance += pos['position_value'] + net_pnl
        
        trade = {
            'symbol': pos['symbol'],
            'side': pos['side'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'pnl_pct': round(pnl_pct * 100, 4),
            'pnl_dollar': round(net_pnl, 4),
            'gross_pnl': round(pnl_dollar, 4),
            'commission': round(total_commission, 4),
            'hold_hours': pos['hold_bars'],
            'exit_reason': reason,
            'strategy': pos['signal_strategy'],
            'signal_score': pos['signal_score'],
            'signal_confidence': pos['signal_confidence'],
            'signal_type': pos['signal_type'],
            'entry_time': pos['entry_time'],
            'exit_time': bar.get('timestamp', ''),
            'is_win': net_pnl > 0,
        }
        
        self.closed_trades.append(trade)
        self.open_positions.remove(pos)
    
    def _calc_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized PnL for all open positions"""
        total = 0
        for pos in self.open_positions:
            if pos['side'] == 'LONG':
                pnl = (current_price - pos['entry_price']) / pos['entry_price']
            else:
                pnl = (pos['entry_price'] - current_price) / pos['entry_price']
            total += pos['position_value'] * pnl
        return total
    
    def _generate_report(self, symbol: str) -> Dict:
        """Generate detailed performance report"""
        trades = [t for t in self.closed_trades if t['symbol'] == symbol]
        
        if not trades:
            return {
                'symbol': symbol,
                'total_trades': 0,
                'message': 'No trades generated'
            }
        
        wins = [t for t in trades if t['is_win']]
        losses = [t for t in trades if not t['is_win']]
        
        total_pnl = sum(t['pnl_dollar'] for t in trades)
        gross_profit = sum(t['pnl_dollar'] for t in wins) if wins else 0
        gross_loss = abs(sum(t['pnl_dollar'] for t in losses)) if losses else 0.001
        
        # Max drawdown from equity curve
        max_dd = self._calc_max_drawdown()
        
        # Win/Loss streaks
        max_win_streak, max_loss_streak = self._calc_streaks(trades)
        
        # Exit reason breakdown
        exit_reasons = defaultdict(lambda: {'count': 0, 'pnl': 0})
        for t in trades:
            r = t['exit_reason']
            exit_reasons[r]['count'] += 1
            exit_reasons[r]['pnl'] += t['pnl_dollar']
        
        # Strategy breakdown
        strategy_stats = defaultdict(lambda: {'count': 0, 'wins': 0, 'pnl': 0})
        for t in trades:
            s = t['strategy']
            strategy_stats[s]['count'] += 1
            strategy_stats[s]['pnl'] += t['pnl_dollar']
            if t['is_win']:
                strategy_stats[s]['wins'] += 1
        
        # Average hold times
        avg_hold_win = np.mean([t['hold_hours'] for t in wins]) if wins else 0
        avg_hold_loss = np.mean([t['hold_hours'] for t in losses]) if losses else 0
        
        return {
            'symbol': symbol,
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': round(len(wins) / len(trades) * 100, 1),
            'total_pnl': round(total_pnl, 2),
            'total_pnl_pct': round(total_pnl / self.initial_balance * 100, 2),
            'profit_factor': round(gross_profit / gross_loss, 2) if gross_loss > 0 else 999,
            'avg_win': round(np.mean([t['pnl_pct'] for t in wins]), 3) if wins else 0,
            'avg_loss': round(np.mean([t['pnl_pct'] for t in losses]), 3) if losses else 0,
            'avg_win_dollar': round(np.mean([t['pnl_dollar'] for t in wins]), 3) if wins else 0,
            'avg_loss_dollar': round(np.mean([t['pnl_dollar'] for t in losses]), 3) if losses else 0,
            'best_trade': round(max(t['pnl_pct'] for t in trades), 3),
            'worst_trade': round(min(t['pnl_pct'] for t in trades), 3),
            'max_drawdown_pct': round(max_dd * 100, 2),
            'max_win_streak': max_win_streak,
            'max_loss_streak': max_loss_streak,
            'avg_hold_hours_win': round(avg_hold_win, 1),
            'avg_hold_hours_loss': round(avg_hold_loss, 1),
            'total_commission': round(sum(t['commission'] for t in trades), 2),
            'exit_reasons': dict(exit_reasons),
            'strategy_stats': dict(strategy_stats),
            'trades': trades,
        }
    
    def _calc_max_drawdown(self) -> float:
        """Calculate maximum drawdown from equity curve"""
        if not self.equity_curve:
            return 0
        
        peak = self.equity_curve[0]['equity']
        max_dd = 0
        
        for point in self.equity_curve:
            eq = point['equity']
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def _calc_streaks(self, trades: List[Dict]) -> Tuple[int, int]:
        """Calculate max win and loss streaks"""
        max_win = max_loss = current_win = current_loss = 0
        
        for t in trades:
            if t['is_win']:
                current_win += 1
                current_loss = 0
                max_win = max(max_win, current_win)
            else:
                current_loss += 1
                current_win = 0
                max_loss = max(max_loss, current_loss)
        
        return max_win, max_loss
    
    def reset(self):
        """Reset backtester state for new symbol"""
        self.balance = self.initial_balance
        self.open_positions = []
        self.closed_trades = []
        self.equity_curve = []


# ============================================================
# 3. MULTI-SYMBOL BACKTEST RUNNER
# ============================================================

def run_full_backtest(config: Dict = None, symbols: List[str] = None,
                      days: int = 60, initial_balance: float = 1000.0,
                      label: str = "CURRENT") -> Dict:
    """Run backtest across multiple symbols and aggregate results"""
    
    if symbols is None:
        symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
            'ADAUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT', 'LINKUSDT',
            'ARBUSDT', 'OPUSDT', 'DOGEUSDT', 'PEPEUSDT', 'SHIBUSDT',
            'NEARUSDT', 'APTUSDT', 'SUIUSDT', 'INJUSDT',
        ]
    
    print(f"\n{'='*70}")
    print(f"  🔬 REALISTIC BACKTEST — {label}")
    print(f"  Balance: ${initial_balance} | Period: {days} days | Symbols: {len(symbols)}")
    print(f"{'='*70}\n")
    
    # Fetch data for all symbols
    all_data = {}
    print("📥 Fetching real market data from Binance...")
    for sym in symbols:
        print(f"  → {sym}...", end=" ", flush=True)
        df = fetch_binance_klines(sym, '1h', days)
        if not df.empty and len(df) >= 80:
            all_data[sym] = df
            print(f"✅ {len(df)} bars")
        else:
            print(f"❌ insufficient data ({len(df)} bars)")
        time.sleep(0.3)
    
    print(f"\n📊 Running backtest on {len(all_data)} symbols...\n")
    
    # Run backtest per symbol
    all_results = {}
    all_trades = []
    total_pnl = 0
    
    for sym, df in all_data.items():
        bt = RealisticBacktester(config=config, initial_balance=initial_balance)
        result = bt.run(sym, df)
        all_results[sym] = result
        
        n = result.get('total_trades', 0)
        wr = result.get('win_rate', 0)
        pnl = result.get('total_pnl', 0)
        pf = result.get('profit_factor', 0)
        total_pnl += pnl
        
        if result.get('trades'):
            all_trades.extend(result['trades'])
        
        status = "✅" if pnl > 0 else "❌"
        print(f"  {status} {sym:12s} | Trades: {n:3d} | WR: {wr:5.1f}% | "
              f"PF: {pf:5.2f} | PnL: ${pnl:+8.2f}")
    
    # Aggregate analysis
    agg = _aggregate_results(all_trades, all_results, initial_balance, label)
    agg['per_symbol'] = all_results
    
    return agg


def _aggregate_results(trades: List[Dict], results: Dict,
                       initial_balance: float, label: str) -> Dict:
    """Aggregate results across all symbols"""
    if not trades:
        print("\n❌ No trades generated across all symbols!")
        return {'total_trades': 0}
    
    wins = [t for t in trades if t['is_win']]
    losses = [t for t in trades if not t['is_win']]
    
    gross_profit = sum(t['pnl_dollar'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl_dollar'] for t in losses)) if losses else 0.001
    total_pnl = sum(t['pnl_dollar'] for t in trades)
    
    # Exit reason analysis
    exit_reasons = defaultdict(lambda: {'count': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        r = t['exit_reason']
        exit_reasons[r]['count'] += 1
        exit_reasons[r]['pnl'] += t['pnl_dollar']
        if t['is_win']:
            exit_reasons[r]['wins'] += 1
    
    # Strategy analysis
    strat_stats = defaultdict(lambda: {'count': 0, 'wins': 0, 'pnl': 0,
                                        'avg_pnl_pct': []})
    for t in trades:
        s = t['strategy']
        strat_stats[s]['count'] += 1
        strat_stats[s]['pnl'] += t['pnl_dollar']
        strat_stats[s]['avg_pnl_pct'].append(t['pnl_pct'])
        if t['is_win']:
            strat_stats[s]['wins'] += 1
    
    for s in strat_stats:
        arr = strat_stats[s]['avg_pnl_pct']
        strat_stats[s]['avg_pnl_pct'] = round(np.mean(arr), 3) if arr else 0
        strat_stats[s]['wr'] = round(strat_stats[s]['wins'] / max(strat_stats[s]['count'], 1) * 100, 1)
    
    # Side analysis
    longs = [t for t in trades if t['side'] == 'LONG']
    shorts = [t for t in trades if t['side'] == 'SHORT']
    
    # Loss analysis — why are we losing?
    loss_analysis = _analyze_losses(losses)
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"  📊 AGGREGATE RESULTS — {label}")
    print(f"{'='*70}")
    print(f"  Total Trades:    {len(trades)}")
    print(f"  Win Rate:        {len(wins)/len(trades)*100:.1f}%")
    print(f"  Profit Factor:   {gross_profit/gross_loss:.2f}")
    print(f"  Total PnL:       ${total_pnl:+.2f} ({total_pnl/initial_balance*100:+.1f}%)")
    print(f"  Avg Win:         {np.mean([t['pnl_pct'] for t in wins]):.3f}%" if wins else "  Avg Win: N/A")
    print(f"  Avg Loss:        {np.mean([t['pnl_pct'] for t in losses]):.3f}%" if losses else "  Avg Loss: N/A")
    print(f"  Commissions:     ${sum(t['commission'] for t in trades):.2f}")
    print(f"  LONG trades:     {len(longs)} (WR: {sum(1 for t in longs if t['is_win'])/max(len(longs),1)*100:.1f}%)")
    print(f"  SHORT trades:    {len(shorts)} (WR: {sum(1 for t in shorts if t['is_win'])/max(len(shorts),1)*100:.1f}%)")
    
    print(f"\n  📤 Exit Reasons:")
    for reason, data in sorted(exit_reasons.items(), key=lambda x: x[1]['count'], reverse=True):
        wr = data['wins'] / max(data['count'], 1) * 100
        print(f"    {reason:15s} | Count: {data['count']:3d} | "
              f"WR: {wr:5.1f}% | PnL: ${data['pnl']:+8.2f}")
    
    print(f"\n  🎯 Strategy Performance:")
    for strat, data in sorted(strat_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
        print(f"    {strat:20s} | Trades: {data['count']:3d} | "
              f"WR: {data['wr']:5.1f}% | Avg: {data['avg_pnl_pct']:+.3f}% | "
              f"PnL: ${data['pnl']:+.2f}")
    
    print(f"\n  🔍 Loss Analysis:")
    for key, val in loss_analysis.items():
        print(f"    {key}: {val}")
    
    print(f"{'='*70}\n")
    
    return {
        'label': label,
        'total_trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': round(len(wins) / len(trades) * 100, 1),
        'profit_factor': round(gross_profit / gross_loss, 2),
        'total_pnl': round(total_pnl, 2),
        'total_pnl_pct': round(total_pnl / initial_balance * 100, 2),
        'avg_win_pct': round(np.mean([t['pnl_pct'] for t in wins]), 3) if wins else 0,
        'avg_loss_pct': round(np.mean([t['pnl_pct'] for t in losses]), 3) if losses else 0,
        'exit_reasons': {k: dict(v) for k, v in exit_reasons.items()},
        'strategy_stats': {k: dict(v) for k, v in strat_stats.items()},
        'loss_analysis': loss_analysis,
        'all_trades': trades,
        'long_count': len(longs),
        'short_count': len(shorts),
        'long_wr': round(sum(1 for t in longs if t['is_win']) / max(len(longs), 1) * 100, 1),
        'short_wr': round(sum(1 for t in shorts if t['is_win']) / max(len(shorts), 1) * 100, 1),
    }


def _analyze_losses(losses: List[Dict]) -> Dict:
    """Deep analysis of losing trades to find patterns"""
    if not losses:
        return {'message': 'No losses to analyze'}
    
    analysis = {}
    
    # 1. SL hits vs other exits
    sl_losses = [t for t in losses if t['exit_reason'] == 'STOP_LOSS']
    trail_losses = [t for t in losses if t['exit_reason'] == 'TRAILING']
    stagnant_losses = [t for t in losses if t['exit_reason'] == 'STAGNANT']
    early_cut_losses = [t for t in losses if t['exit_reason'] == 'EARLY_CUT']
    max_hold_losses = [t for t in losses if t['exit_reason'] == 'MAX_HOLD']
    reversal_losses = [t for t in losses if t['exit_reason'] == 'REVERSAL']
    
    analysis['total_losses'] = len(losses)
    analysis['avg_loss_pct'] = f"{np.mean([t['pnl_pct'] for t in losses]):.3f}%"
    analysis['sl_hit_losses'] = f"{len(sl_losses)} (${sum(t['pnl_dollar'] for t in sl_losses):.2f})"
    analysis['trailing_losses'] = f"{len(trail_losses)} (${sum(t['pnl_dollar'] for t in trail_losses):.2f})"
    analysis['stagnant_losses'] = f"{len(stagnant_losses)} (${sum(t['pnl_dollar'] for t in stagnant_losses):.2f})"
    analysis['early_cut_losses'] = f"{len(early_cut_losses)} (${sum(t['pnl_dollar'] for t in early_cut_losses):.2f})"
    analysis['max_hold_losses'] = f"{len(max_hold_losses)} (${sum(t['pnl_dollar'] for t in max_hold_losses):.2f})"
    
    # 2. Average hold time for losses
    analysis['avg_hold_hours_losses'] = f"{np.mean([t['hold_hours'] for t in losses]):.1f}h"
    
    # 3. Quick losses (<2h)
    quick_losses = [t for t in losses if t['hold_hours'] <= 2]
    analysis['quick_losses_under_2h'] = f"{len(quick_losses)} / {len(losses)}"
    
    # 4. Loss by side
    long_losses = [t for t in losses if t['side'] == 'LONG']
    short_losses = [t for t in losses if t['side'] == 'SHORT']
    analysis['long_losses'] = f"{len(long_losses)} (${sum(t['pnl_dollar'] for t in long_losses):.2f})"
    analysis['short_losses'] = f"{len(short_losses)} (${sum(t['pnl_dollar'] for t in short_losses):.2f})"
    
    # 5. Worst strategies
    strat_losses = defaultdict(list)
    for t in losses:
        strat_losses[t['strategy']].append(t['pnl_dollar'])
    
    worst = sorted(strat_losses.items(), key=lambda x: sum(x[1]))
    analysis['worst_strategies'] = {s: f"${sum(pnls):.2f} ({len(pnls)} trades)" 
                                    for s, pnls in worst[:5]}
    
    return analysis


# ============================================================
# 4. MAIN — Run current config, then optimized, and compare
# ============================================================

if __name__ == '__main__':
    print("\n" + "🔬" * 35)
    print("  REALISTIC TRADING SYSTEM BACKTEST")
    print("  Real Binance Data | Full V7.1 Engine")
    print("🔬" * 35)
    
    # ========== PHASE 1: TEST CURRENT SYSTEM ==========
    print("\n\n" + "=" * 70)
    print("  PHASE 1: TESTING CURRENT SYSTEM (as-is)")
    print("=" * 70)
    
    current_results = run_full_backtest(
        config=None,  # Use default V7_CONFIG
        days=60,
        initial_balance=1000.0,
        label="CURRENT V7.1"
    )
    
    # Save results
    output_dir = os.path.join(PROJECT_ROOT, 'tests', 'backtest_results')
    os.makedirs(output_dir, exist_ok=True)
    
    # Save summary (without full trade list for readability)
    summary = {k: v for k, v in current_results.items() 
               if k not in ('all_trades', 'per_symbol')}
    
    with open(os.path.join(output_dir, 'current_system_results.json'), 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    # Save all trades for analysis
    if current_results.get('all_trades'):
        trades_df = pd.DataFrame(current_results['all_trades'])
        trades_df.to_csv(os.path.join(output_dir, 'current_trades.csv'), index=False)
        print(f"\n💾 Results saved to {output_dir}/")
    
    print("\n✅ Phase 1 Complete — Current system tested.")
    print("   Run this script to see results. Phase 2 (optimization) follows automatically.\n")
