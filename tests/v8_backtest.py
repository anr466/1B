#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 Realistic Backtest — Tests the ACTUAL production engine (V8)
================================================================
Uses the same RealisticBacktester framework but with ScalpingV8Engine.
Fetches real Binance data, simulates commission + slippage.
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

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from backend.strategies.scalping_v8_engine import ScalpingV8Engine, V8_CONFIG

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
        
        time.sleep(0.2)
    
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
# 2. V8 BACKTESTER
# ============================================================

class V8RealisticBacktester:
    """
    Backtest engine using ScalpingV8Engine (production engine).
    Mirrors live trading behavior exactly.
    """
    
    def __init__(self, config: Dict = None, initial_balance: float = 1000.0):
        self.config = {**V8_CONFIG, **(config or {})}
        self.engine = ScalpingV8Engine(self.config)
        self.initial_balance = initial_balance
        self.balance = initial_balance
        
        self.open_positions: List[Dict] = []
        self.closed_trades: List[Dict] = []
        self.equity_curve: List[Dict] = []
        
        self.commission_pct = self.config.get('commission_pct', 0.001)
        self.slippage_pct = self.config.get('slippage_pct', 0.0005)
        self.position_size_pct = self.config.get('position_size_pct', 0.06)
        self.max_positions = self.config.get('max_positions', 5)
    
    def run(self, symbol: str, df: pd.DataFrame) -> Dict:
        """Run backtest on prepared data for one symbol"""
        if df is None or len(df) < 80:
            return {'error': f'Insufficient data for {symbol}'}
        
        df_prepared = self.engine.prepare_data(df)
        if df_prepared is None:
            return {'error': f'Failed to prepare data for {symbol}'}
        
        for i in range(60, len(df_prepared)):
            current_bar = df_prepared.iloc[i]
            bar_time = current_bar.get('timestamp', i)
            
            unrealized = self._calc_unrealized_pnl(current_bar['close'])
            self.equity_curve.append({
                'time': bar_time,
                'balance': self.balance,
                'equity': self.balance + unrealized,
                'open_positions': len(self.open_positions)
            })
            
            # 1. Check exits
            self._check_exits(df_prepared, i, symbol)
            
            # 2. Check for new entries
            if len(self.open_positions) < self.max_positions:
                trend = self.engine.get_4h_trend(df_prepared, i - 1)
                signal = self.engine.detect_entry(df_prepared, trend, i - 1)
                
                if signal:
                    entry_price = current_bar['open']
                    if signal['side'] == 'LONG':
                        entry_price *= (1 + self.slippage_pct)
                    else:
                        entry_price *= (1 - self.slippage_pct)
                    
                    self._open_position(symbol, signal, entry_price, bar_time, i)
        
        return self._generate_report(symbol)
    
    def _open_position(self, symbol, signal, entry_price, bar_time, bar_idx):
        position_value = self.initial_balance * self.position_size_pct
        if position_value < 10:
            return
        
        quantity = position_value / entry_price
        entry_commission = position_value * self.commission_pct
        self.balance -= entry_commission
        
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
    
    def _check_exits(self, df, bar_idx, symbol):
        positions_to_close = []
        
        for pos in self.open_positions:
            pos['hold_bars'] += 1
            hold_hours = pos['hold_bars']
            
            pos_data = {
                'entry_price': pos['entry_price'],
                'side': pos['side'],
                'peak': pos['peak'],
                'trail': pos['trailing_stop'],
                'sl': pos['stop_loss'],
                'entry_time': pos['entry_time'],
                'hold_hours': hold_hours,
            }
            
            df_slice = df.iloc[:bar_idx + 1]
            exit_result = self.engine.check_exit_signal(df_slice, pos_data)
            
            if exit_result.get('should_exit', False):
                exit_price = exit_result.get('exit_price', df.iloc[bar_idx]['close'])
                reason = exit_result.get('reason', 'UNKNOWN')
                
                if pos['side'] == 'LONG':
                    exit_price *= (1 - self.slippage_pct)
                else:
                    exit_price *= (1 + self.slippage_pct)
                
                positions_to_close.append((pos, exit_price, reason, bar_idx))
            else:
                updated = exit_result.get('updated', {})
                if 'peak' in updated:
                    pos['peak'] = updated['peak']
                if 'trail' in updated:
                    pos['trailing_stop'] = updated['trail']
                if 'sl' in updated:
                    pos['stop_loss'] = updated['sl']
        
        for pos, exit_price, reason, idx in positions_to_close:
            self._close_position(pos, exit_price, reason, df.iloc[idx])
    
    def _close_position(self, pos, exit_price, reason, bar):
        if pos['side'] == 'LONG':
            pnl_pct = (exit_price - pos['entry_price']) / pos['entry_price']
        else:
            pnl_pct = (pos['entry_price'] - exit_price) / pos['entry_price']
        
        pnl_dollar = pos['position_value'] * pnl_pct
        exit_value = pos['position_value'] * (1 + pnl_pct)
        exit_commission = exit_value * self.commission_pct
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
    
    def _calc_unrealized_pnl(self, current_price):
        total = 0
        for pos in self.open_positions:
            if pos['side'] == 'LONG':
                pnl = (current_price - pos['entry_price']) / pos['entry_price']
            else:
                pnl = (pos['entry_price'] - current_price) / pos['entry_price']
            total += pos['position_value'] * pnl
        return total
    
    def _generate_report(self, symbol):
        trades = [t for t in self.closed_trades if t['symbol'] == symbol]
        
        if not trades:
            return {'symbol': symbol, 'total_trades': 0, 'message': 'No trades'}
        
        wins = [t for t in trades if t['is_win']]
        losses = [t for t in trades if not t['is_win']]
        
        total_pnl = sum(t['pnl_dollar'] for t in trades)
        gross_profit = sum(t['pnl_dollar'] for t in wins) if wins else 0
        gross_loss = abs(sum(t['pnl_dollar'] for t in losses)) if losses else 0.001
        
        max_dd = self._calc_max_drawdown()
        
        exit_reasons = defaultdict(lambda: {'count': 0, 'pnl': 0})
        for t in trades:
            r = t['exit_reason']
            exit_reasons[r]['count'] += 1
            exit_reasons[r]['pnl'] += t['pnl_dollar']
        
        strategy_stats = defaultdict(lambda: {'count': 0, 'wins': 0, 'pnl': 0})
        for t in trades:
            s = t['strategy']
            strategy_stats[s]['count'] += 1
            strategy_stats[s]['pnl'] += t['pnl_dollar']
            if t['is_win']:
                strategy_stats[s]['wins'] += 1
        
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
            'max_drawdown_pct': round(max_dd * 100, 2),
            'total_commission': round(sum(t['commission'] for t in trades), 2),
            'exit_reasons': dict(exit_reasons),
            'strategy_stats': dict(strategy_stats),
            'trades': trades,
        }
    
    def _calc_max_drawdown(self):
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
    
    def reset(self):
        self.balance = self.initial_balance
        self.open_positions = []
        self.closed_trades = []
        self.equity_curve = []


# ============================================================
# 3. MULTI-SYMBOL RUNNER
# ============================================================

def run_v8_backtest(symbols=None, days=60, initial_balance=1000.0):
    """Run V8 backtest across multiple symbols"""
    
    if symbols is None:
        # Use the EXACT same coins as the live system (group_b_system.py)
        symbols = [
            'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT', 'NEARUSDT',
            'SUIUSDT', 'ARBUSDT', 'APTUSDT', 'INJUSDT', 'LINKUSDT',
        ]
    
    print(f"\n{'='*70}")
    print(f"  🔬 V8 REALISTIC BACKTEST — Production Engine")
    print(f"  Balance: ${initial_balance} | Period: {days} days | Symbols: {len(symbols)}")
    print(f"  Engine: ScalpingV8 | Trail: {V8_CONFIG['trailing_activation']*100}%/{V8_CONFIG['trailing_distance']*100}%")
    print(f"  BE: {V8_CONFIG['breakeven_trigger']*100}% | MaxHold: {V8_CONFIG['max_hold_hours']}h")
    print(f"  Reversal blocked: {V8_CONFIG.get('v8_block_reversal', True)}")
    print(f"{'='*70}\n")
    
    # Fetch data
    all_data = {}
    print("📥 Fetching real market data from Binance...")
    for sym in symbols:
        print(f"  → {sym}...", end=" ", flush=True)
        df = fetch_binance_klines(sym, '1h', days)
        if not df.empty and len(df) >= 80:
            all_data[sym] = df
            print(f"✅ {len(df)} bars")
        else:
            print(f"❌ insufficient data ({len(df) if not df.empty else 0} bars)")
        time.sleep(0.3)
    
    print(f"\n📊 Running V8 backtest on {len(all_data)} symbols...\n")
    
    all_trades = []
    total_pnl = 0
    symbol_results = {}
    
    for sym, df in all_data.items():
        bt = V8RealisticBacktester(initial_balance=initial_balance)
        result = bt.run(sym, df)
        symbol_results[sym] = result
        
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
    
    # === AGGREGATE ===
    if not all_trades:
        print("\n❌ No trades generated!")
        return {'total_trades': 0}
    
    wins = [t for t in all_trades if t['is_win']]
    losses = [t for t in all_trades if not t['is_win']]
    
    gross_profit = sum(t['pnl_dollar'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl_dollar'] for t in losses)) if losses else 0.001
    total_commission = sum(t['commission'] for t in all_trades)
    
    # Exit reasons
    exit_reasons = defaultdict(lambda: {'count': 0, 'pnl': 0, 'wins': 0})
    for t in all_trades:
        r = t['exit_reason']
        exit_reasons[r]['count'] += 1
        exit_reasons[r]['pnl'] += t['pnl_dollar']
        if t['is_win']:
            exit_reasons[r]['wins'] += 1
    
    # Strategy breakdown
    strat_stats = defaultdict(lambda: {'count': 0, 'wins': 0, 'pnl': 0})
    for t in all_trades:
        s = t['strategy']
        strat_stats[s]['count'] += 1
        strat_stats[s]['pnl'] += t['pnl_dollar']
        if t['is_win']:
            strat_stats[s]['wins'] += 1
    
    # Side analysis
    longs = [t for t in all_trades if t['side'] == 'LONG']
    shorts = [t for t in all_trades if t['side'] == 'SHORT']
    
    pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 999
    wr = round(len(wins) / len(all_trades) * 100, 1)
    
    print(f"\n{'='*70}")
    print(f"  📊 V8 AGGREGATE RESULTS")
    print(f"{'='*70}")
    print(f"  Total Trades:    {len(all_trades)}")
    print(f"  Win Rate:        {wr}%")
    print(f"  Profit Factor:   {pf}")
    print(f"  Total PnL:       ${total_pnl:+.2f} ({total_pnl/initial_balance*100:+.1f}%)")
    print(f"  Gross Profit:    ${gross_profit:+.2f}")
    print(f"  Gross Loss:      ${gross_loss:.2f}")
    print(f"  Commissions:     ${total_commission:.2f}")
    print(f"  Net after fees:  ${total_pnl:+.2f}")
    if wins:
        print(f"  Avg Win:         {np.mean([t['pnl_pct'] for t in wins]):.3f}%")
    if losses:
        print(f"  Avg Loss:        {np.mean([t['pnl_pct'] for t in losses]):.3f}%")
    print(f"  LONG trades:     {len(longs)} (WR: {sum(1 for t in longs if t['is_win'])/max(len(longs),1)*100:.1f}%)")
    print(f"  SHORT trades:    {len(shorts)} (WR: {sum(1 for t in shorts if t['is_win'])/max(len(shorts),1)*100:.1f}%)")
    
    print(f"\n  📤 Exit Reasons:")
    for reason, data in sorted(exit_reasons.items(), key=lambda x: x[1]['count'], reverse=True):
        r_wr = data['wins'] / max(data['count'], 1) * 100
        print(f"    {reason:15s} | Count: {data['count']:3d} | "
              f"WR: {r_wr:5.1f}% | PnL: ${data['pnl']:+8.2f}")
    
    print(f"\n  🎯 Strategy Performance:")
    for strat, data in sorted(strat_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
        s_wr = data['wins'] / max(data['count'], 1) * 100
        print(f"    {strat:20s} | Trades: {data['count']:3d} | "
              f"WR: {s_wr:5.1f}% | PnL: ${data['pnl']:+.2f}")
    
    # Profitable symbols count
    profitable = sum(1 for r in symbol_results.values() if r.get('total_pnl', 0) > 0)
    losing = len(symbol_results) - profitable
    print(f"\n  📈 Profitable symbols: {profitable}/{len(symbol_results)}")
    print(f"  📉 Losing symbols:    {losing}/{len(symbol_results)}")
    
    # VERDICT
    print(f"\n{'='*70}")
    if pf >= 1.5 and wr >= 60:
        print(f"  ✅ VERDICT: V8 Engine PASSES (PF={pf} ≥ 1.5, WR={wr}% ≥ 60%)")
    elif pf >= 1.0:
        print(f"  ⚠️  VERDICT: V8 Engine MARGINAL (PF={pf}, WR={wr}%) — needs optimization")
    else:
        print(f"  ❌ VERDICT: V8 Engine FAILS (PF={pf} < 1.0) — losing money")
    print(f"{'='*70}\n")
    
    # Save results
    output_dir = os.path.join(PROJECT_ROOT, 'tests', 'backtest_results')
    os.makedirs(output_dir, exist_ok=True)
    
    summary = {
        'engine': 'ScalpingV8',
        'timestamp': datetime.now().isoformat(),
        'days': days,
        'initial_balance': initial_balance,
        'symbols_count': len(all_data),
        'total_trades': len(all_trades),
        'win_rate': wr,
        'profit_factor': pf,
        'total_pnl': round(total_pnl, 2),
        'total_pnl_pct': round(total_pnl / initial_balance * 100, 2),
        'total_commission': round(total_commission, 2),
        'profitable_symbols': profitable,
        'losing_symbols': losing,
        'exit_reasons': {k: dict(v) for k, v in exit_reasons.items()},
        'strategy_stats': {k: dict(v) for k, v in strat_stats.items()},
    }
    
    # ❌ REMOVED: No JSON/CSV files — follows system philosophy
    # Results are printed to console only
    # For permanent storage, use database with is_backtest=1 flag
    
    print(f"\n💾 Backtest complete — results printed above")
    print(f"⚠️  No files saved (system uses DB only)")
    print(f"� To persist results, save trades to user_trades table with is_backtest=1")
    
    return summary


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("\n" + "🔬" * 35)
    print("  V8 PRODUCTION ENGINE BACKTEST")
    print("  Real Binance Data | ScalpingV8Engine")
    print("🔬" * 35)
    
    results = run_v8_backtest(days=60, initial_balance=1000.0)
    
    print("\n✅ V8 Backtest Complete.")
