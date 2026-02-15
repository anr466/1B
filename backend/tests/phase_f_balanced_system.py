#!/usr/bin/env python3
"""
Phase F: Balanced Trading System — Smart Entry + Multi-Exit
============================================================
Tests improvements based on loss analysis findings:

ENTRY:
  F3: Volume filter (winners vol_ratio=3.29 vs losers 1.96)

EXIT:
  F1: Lower trailing activation (0.6% -> 0.4%)
  F2: Partial exit 50% at +1%, tighten trailing for rest
  F4: Break-even move at +0.5% (combo with partial)
  F5: Reversal-confirmed exit (multi-signal, don't exit on noise)

Each tested individually vs baseline (A1+A3+B3+C2+C4), then best combined.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
import json
import urllib.request
import logging

logging.basicConfig(level=logging.WARNING)

from backend.strategies.scalping_v7_engine import ScalpingV7Engine, V7_CONFIG


def fetch_klines(symbol, interval='1h', limit=1000):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    df = pd.DataFrame(data, columns=[
        'timestamp','open','high','low','close','volume',
        'close_time','quote_volume','trades','taker_buy_base','taker_buy_quote','ignore'
    ])
    for c in ['open','high','low','close','volume']:
        df[c] = df[c].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df[['timestamp','open','high','low','close','volume']]


# ============================================================
# SMART EXIT FUNCTION — configurable features
# ============================================================
def smart_exit_check(engine, df_slice, pos_data, features):
    """
    Enhanced exit with configurable features.
    
    features dict:
      trail_activation: float (default 0.006)
      partial_exit: bool — take 50% at +1%
      be_move: bool — move SL to entry at +0.5%
      reversal_confirm: bool — require multi-signal reversal
    """
    if df_slice is None or len(df_slice) < 3:
        return {'should_exit': False, 'reason': 'HOLD', 'partial': False}

    idx = len(df_slice) - 1
    row = df_slice.iloc[idx]
    hi, lo, cl = row['high'], row['low'], row['close']
    entry = pos_data['entry_price']
    side = pos_data.get('side', 'LONG')
    peak = pos_data.get('peak', entry)
    trail = pos_data.get('trail', 0)
    sl = pos_data.get('sl')
    hold_hours = pos_data.get('hold_hours', 0)
    partial_done = pos_data.get('partial_done', False)
    updated = {}

    trail_activation = features.get('trail_activation', 0.006)
    do_partial = features.get('partial_exit', False)
    do_be = features.get('be_move', False)
    do_reversal_confirm = features.get('reversal_confirm', False)

    if side == 'LONG':
        # Update peak
        if hi > peak:
            peak = hi
            updated['peak'] = peak

        # BE move at +0.5%
        if do_be:
            be_pct = (hi - entry) / entry
            if be_pct >= 0.005 and sl < entry:
                sl = entry * 1.0001
                updated['sl'] = sl

        # SL check
        if lo <= sl:
            return {'should_exit': True, 'reason': 'STOP_LOSS', 'exit_price': sl,
                    'updated': updated, 'partial': False}

        # Partial exit at +1%
        if do_partial and not partial_done:
            partial_pct = (hi - entry) / entry
            if partial_pct >= 0.01:
                updated['partial_done'] = True
                # Tighten SL to entry for remaining
                updated['sl'] = max(sl, entry * 1.0001)
                return {'should_exit': True, 'reason': 'PARTIAL_TP', 'exit_price': hi,
                        'updated': updated, 'partial': True, 'partial_pct': 0.5}

        # Progressive trailing (B3)
        profit_pct = (peak - entry) / entry
        td = V7_CONFIG['trailing_distance']
        if profit_pct >= 0.02:
            td = min(td, 0.002)
        elif profit_pct >= 0.015:
            td = min(td, 0.003)
        elif profit_pct >= 0.01:
            td = min(td, 0.0035)

        if profit_pct >= trail_activation:
            ts = peak * (1 - td)
            if ts > trail:
                trail = ts
                updated['trail'] = trail
            if trail > 0 and lo <= trail:
                # Reversal confirmation for profitable trades
                if do_reversal_confirm and profit_pct > 0.005:
                    rev_signals = _count_reversal_signals(df_slice, idx, 'LONG')
                    if rev_signals < 2:
                        # Not confirmed — widen trailing slightly, stay
                        trail = peak * (1 - td * 1.3)
                        updated['trail'] = trail
                        if lo > trail:
                            return {'should_exit': False, 'reason': 'HOLD',
                                    'updated': updated, 'partial': False}
                return {'should_exit': True, 'reason': 'TRAILING', 'exit_price': trail,
                        'updated': updated, 'partial': False}

    else:  # SHORT
        if lo < peak:
            peak = lo
            updated['peak'] = peak

        if do_be:
            be_pct = (entry - lo) / entry
            if be_pct >= 0.005 and sl > entry:
                sl = entry * 0.9999
                updated['sl'] = sl

        if hi >= sl:
            return {'should_exit': True, 'reason': 'STOP_LOSS', 'exit_price': sl,
                    'updated': updated, 'partial': False}

        if do_partial and not partial_done:
            partial_pct = (entry - lo) / entry
            if partial_pct >= 0.01:
                updated['partial_done'] = True
                updated['sl'] = min(sl, entry * 0.9999)
                return {'should_exit': True, 'reason': 'PARTIAL_TP', 'exit_price': lo,
                        'updated': updated, 'partial': True, 'partial_pct': 0.5}

        profit_pct = (entry - peak) / entry
        td = V7_CONFIG['trailing_distance']
        if profit_pct >= 0.02:
            td = min(td, 0.002)
        elif profit_pct >= 0.015:
            td = min(td, 0.003)
        elif profit_pct >= 0.01:
            td = min(td, 0.0035)

        if profit_pct >= trail_activation:
            ts = peak * (1 + td)
            if trail == 0 or ts < trail:
                trail = ts
                updated['trail'] = trail
            if trail > 0 and hi >= trail:
                if do_reversal_confirm and profit_pct > 0.005:
                    rev_signals = _count_reversal_signals(df_slice, idx, 'SHORT')
                    if rev_signals < 2:
                        trail = peak * (1 + td * 1.3)
                        updated['trail'] = trail
                        if hi < trail:
                            return {'should_exit': False, 'reason': 'HOLD',
                                    'updated': updated, 'partial': False}
                return {'should_exit': True, 'reason': 'TRAILING', 'exit_price': trail,
                        'updated': updated, 'partial': False}

    # V7 Reversal detection
    if idx >= 2:
        prev = df_slice.iloc[idx - 1]
        rev = 0
        if side == 'LONG':
            pnl = (cl - entry) / entry
            if pnl > 0.003:
                if not pd.isna(row.get('st_dir')) and not pd.isna(prev.get('st_dir')):
                    if prev['st_dir'] == 1 and row['st_dir'] == -1:
                        rev += 3
                if prev.get('bull', True) and not row.get('bull', True):
                    if row['open'] > prev['close'] and cl < prev['open']:
                        rev += 2
                if not pd.isna(row.get('macd_l')) and not pd.isna(prev.get('macd_l')):
                    if prev['macd_l'] > prev['macd_s'] and row['macd_l'] < row['macd_s']:
                        rev += 2
        else:
            pnl = (entry - cl) / entry
            if pnl > 0.003:
                if not pd.isna(row.get('st_dir')) and not pd.isna(prev.get('st_dir')):
                    if prev['st_dir'] == -1 and row['st_dir'] == 1:
                        rev += 3
                if not prev.get('bull', False) and row.get('bull', False):
                    if row['close'] > prev['open'] and row['open'] < prev['close']:
                        rev += 2
                if not pd.isna(row.get('macd_l')) and not pd.isna(prev.get('macd_l')):
                    if prev['macd_l'] < prev['macd_s'] and row['macd_l'] > row['macd_s']:
                        rev += 2
        if rev >= 3:
            return {'should_exit': True, 'reason': 'REVERSAL', 'exit_price': cl,
                    'updated': updated, 'partial': False}

    # Max hold / stagnant
    if hold_hours >= V7_CONFIG['max_hold_hours']:
        return {'should_exit': True, 'reason': 'MAX_HOLD', 'exit_price': cl,
                'updated': updated, 'partial': False}
    pnl_now = (cl - entry) / entry if side == 'LONG' else (entry - cl) / entry
    if hold_hours >= 6 and abs(pnl_now) < 0.002:
        return {'should_exit': True, 'reason': 'STAGNANT', 'exit_price': cl,
                'updated': updated, 'partial': False}

    return {'should_exit': False, 'reason': 'HOLD', 'exit_price': cl,
            'updated': updated, 'partial': False}


def _count_reversal_signals(df, idx, side):
    """Count reversal confirmation signals (from MultiExitEngine logic)."""
    if idx < 3:
        return 0
    signals = 0
    row = df.iloc[idx]
    prev = df.iloc[idx - 1]
    prev2 = df.iloc[idx - 2]

    if side == 'LONG':
        # MACD bearish cross
        if not pd.isna(row.get('macd_l')) and not pd.isna(prev.get('macd_l')):
            if row['macd_l'] < row['macd_s'] and prev['macd_l'] >= prev['macd_s']:
                signals += 1
        # RSI dropping below 45
        if not pd.isna(row.get('rsi')) and not pd.isna(prev2.get('rsi')):
            if row['rsi'] < 45 and prev2['rsi'] > 55:
                signals += 1
        # SuperTrend flip
        if not pd.isna(row.get('st_dir')) and not pd.isna(prev.get('st_dir')):
            if prev['st_dir'] == 1 and row['st_dir'] == -1:
                signals += 1
        # Bearish engulfing
        if row['close'] < row['open'] and prev['close'] > prev['open']:
            if abs(row['close'] - row['open']) > abs(prev['close'] - prev['open']):
                signals += 1
    else:
        # MACD bullish cross
        if not pd.isna(row.get('macd_l')) and not pd.isna(prev.get('macd_l')):
            if row['macd_l'] > row['macd_s'] and prev['macd_l'] <= prev['macd_s']:
                signals += 1
        # RSI rising above 55
        if not pd.isna(row.get('rsi')) and not pd.isna(prev2.get('rsi')):
            if row['rsi'] > 55 and prev2['rsi'] < 45:
                signals += 1
        # SuperTrend flip
        if not pd.isna(row.get('st_dir')) and not pd.isna(prev.get('st_dir')):
            if prev['st_dir'] == -1 and row['st_dir'] == 1:
                signals += 1
        # Bullish engulfing
        if row['close'] > row['open'] and prev['close'] < prev['open']:
            if abs(row['close'] - row['open']) > abs(prev['close'] - prev['open']):
                signals += 1

    return signals


# ============================================================
# BACKTESTER with partial exit support
# ============================================================
class SmartBT:
    def __init__(self, engine, exit_features=None, entry_features=None):
        self.engine = engine
        self.exit_features = exit_features or {}
        self.entry_features = entry_features or {}
        self.balance = 10000.0
        self.initial = 10000.0
        self.positions = []
        self.trades = []
        self.peak_bal = 10000.0
        self.max_dd = 0
        self.pos_size = 600
        self.max_pos = 5
        self.comm = 0.001
        self.slip = 0.0005

    def run(self, all_data):
        min_len = min(len(df) for df in all_data.values())
        for i in range(60, min_len):
            self._manage(all_data, i)
            if len(self.positions) < self.max_pos:
                self._scan(all_data, i)
        self._close_all(all_data, min_len - 1)

    def _manage(self, all_data, idx):
        closed = []
        for pos in self.positions:
            df = all_data[pos['symbol']]
            if idx >= len(df):
                continue
            pos_data = {
                'entry_price': pos['entry'], 'side': pos['side'],
                'peak': pos['peak'], 'trail': pos['trail'],
                'sl': pos['sl'], 'hold_hours': idx - pos['bar'],
                'partial_done': pos.get('partial_done', False),
            }
            df_slice = df.iloc[:idx + 1]

            result = smart_exit_check(self.engine, df_slice, pos_data, self.exit_features)

            upd = result.get('updated', {})
            if 'peak' in upd:
                pos['peak'] = upd['peak']
            if 'trail' in upd:
                pos['trail'] = upd['trail']
            if 'sl' in upd:
                pos['sl'] = upd['sl']
            if 'partial_done' in upd:
                pos['partial_done'] = upd['partial_done']

            if result.get('should_exit'):
                is_partial = result.get('partial', False)
                partial_pct = result.get('partial_pct', 1.0)
                ep = result['exit_price']

                if pos['side'] == 'LONG':
                    ep *= (1 - self.slip)
                else:
                    ep *= (1 + self.slip)

                if is_partial:
                    # Partial exit: close partial_pct of position
                    close_qty = pos['qty'] * partial_pct
                    close_size = pos['size'] * partial_pct
                    pnl_raw = ((ep - pos['entry']) * close_qty if pos['side'] == 'LONG'
                               else (pos['entry'] - ep) * close_qty)
                    pnl = pnl_raw - abs(ep * close_qty) * self.comm
                    self.balance += close_size + pnl

                    # Record partial trade
                    self.trades.append({
                        'symbol': pos['symbol'], 'side': pos['side'],
                        'entry': pos['entry'], 'exit': ep,
                        'pnl': pnl, 'pnl_pct': pnl / close_size * 100,
                        'reason': result['reason'], 'hold': idx - pos['bar'],
                        'partial': True,
                    })

                    # Reduce position
                    pos['qty'] -= close_qty
                    pos['size'] -= close_size

                else:
                    # Full exit
                    pnl_raw = ((ep - pos['entry']) * pos['qty'] if pos['side'] == 'LONG'
                               else (pos['entry'] - ep) * pos['qty'])
                    pnl = pnl_raw - abs(ep * pos['qty']) * self.comm
                    self.balance += pos['size'] + pnl

                    self.trades.append({
                        'symbol': pos['symbol'], 'side': pos['side'],
                        'entry': pos['entry'], 'exit': ep,
                        'pnl': pnl, 'pnl_pct': pnl / pos['size'] * 100,
                        'reason': result['reason'], 'hold': idx - pos['bar'],
                        'partial': False,
                    })
                    closed.append(pos)

        for p in closed:
            self.positions.remove(p)

    def _scan(self, all_data, idx):
        vol_filter = self.entry_features.get('vol_filter', False)
        vol_threshold = self.entry_features.get('vol_threshold', 1.5)

        for sym, df in all_data.items():
            if len(self.positions) >= self.max_pos:
                break
            if any(p['symbol'] == sym for p in self.positions):
                continue
            if idx >= len(df) - 1:
                continue

            trend = self.engine.get_4h_trend(df, idx - 1)
            signal = self.engine.detect_entry(df, trend, idx - 1)
            if not signal:
                continue

            # F3: Volume filter
            if vol_filter:
                row = df.iloc[idx - 1]
                vol_sma = df['volume'].iloc[max(0, idx - 21):idx - 1].mean()
                if vol_sma > 0:
                    vol_ratio = row['volume'] / vol_sma
                    if vol_ratio < vol_threshold:
                        continue

            entry_price = df.iloc[idx]['open']
            if signal['side'] == 'LONG':
                entry_price *= (1 + self.slip)
                sl = entry_price * (1 - V7_CONFIG['sl_pct'])
            else:
                entry_price *= (1 - self.slip)
                sl = entry_price * (1 + V7_CONFIG['sl_pct'])

            if self.pos_size > self.balance:
                continue
            qty = self.pos_size / entry_price
            self.balance -= (self.pos_size + self.pos_size * self.comm)

            self.positions.append({
                'symbol': sym, 'side': signal['side'],
                'entry': entry_price, 'qty': qty, 'size': self.pos_size,
                'sl': sl, 'peak': entry_price, 'trail': 0, 'bar': idx,
                'partial_done': False,
            })

    def _close_all(self, all_data, idx):
        for pos in list(self.positions):
            df = all_data[pos['symbol']]
            if idx < len(df):
                ep = df.iloc[idx]['close']
                pnl = ((ep - pos['entry']) * pos['qty'] if pos['side'] == 'LONG'
                       else (pos['entry'] - ep) * pos['qty']) - abs(ep * pos['qty']) * self.comm
                self.balance += pos['size'] + pnl
                self.trades.append({
                    'symbol': pos['symbol'], 'side': pos['side'],
                    'entry': pos['entry'], 'exit': ep,
                    'pnl': pnl, 'pnl_pct': pnl / pos['size'] * 100,
                    'reason': 'FORCE_CLOSE', 'hold': idx - pos['bar'],
                    'partial': False,
                })
        self.positions.clear()

    def metrics(self):
        if not self.trades:
            return None
        tdf = pd.DataFrame(self.trades)
        w = tdf[tdf['pnl'] > 0]
        l = tdf[tdf['pnl'] <= 0]
        gp = w['pnl'].sum() if len(w) > 0 else 0
        gl = abs(l['pnl'].sum()) if len(l) > 0 else 0
        reasons = tdf['reason'].value_counts()
        return {
            'trades': len(tdf),
            'wr': len(w) / len(tdf) * 100,
            'pf': gp / gl if gl > 0 else float('inf'),
            'pnl': tdf['pnl'].sum(),
            'dd': self.max_dd * 100,
            'avg': tdf['pnl_pct'].mean(),
            'sl_rate': reasons.get('STOP_LOSS', 0) / len(tdf) * 100,
            'trail_rate': reasons.get('TRAILING', 0) / len(tdf) * 100,
            'partial_n': reasons.get('PARTIAL_TP', 0),
            'reasons': {k: int(v) for k, v in reasons.items()},
        }


def print_comparison(name, desc, base_m, mod_m):
    """Print comparison table."""
    print()
    print("=" * 65)
    print(f"  {name}: {desc}")
    print("=" * 65)
    print(f"  {'Metric':<20} {'BASE':>10} {'MOD':>10} {'DELTA':>15}")
    print(f"  {'-' * 58}")

    def row(label, bv, mv, fmt='.2f', better_high=True):
        delta = mv - bv
        arrow = '+' if delta > 0 else ''
        good = (delta > 0) == better_high
        color = '🟢' if good and abs(delta) > 0.01 else '🔴' if not good and abs(delta) > 0.01 else '⚪'
        print(f"  {label:<20} {bv:>10{fmt}} {mv:>10{fmt}} {color}{arrow}{delta:>10{fmt}}")

    row('Trades', base_m['trades'], mod_m['trades'], '.0f', False)
    row('Win Rate %', base_m['wr'], mod_m['wr'])
    row('Profit Factor', base_m['pf'], mod_m['pf'])
    row('PnL $', base_m['pnl'], mod_m['pnl'])
    row('Avg Trade %', base_m['avg'], mod_m['avg'])
    row('SL Rate %', base_m['sl_rate'], mod_m['sl_rate'], '.1f', False)
    row('Trail Rate %', base_m['trail_rate'], mod_m['trail_rate'], '.1f')
    if mod_m['partial_n'] > 0:
        print(f"  {'Partial Exits':<20} {base_m['partial_n']:>10.0f} {mod_m['partial_n']:>10.0f}")

    # Exit reasons
    print(f"\n  Exit reasons:")
    all_r = set(list(base_m['reasons'].keys()) + list(mod_m['reasons'].keys()))
    for r in sorted(all_r):
        bv = base_m['reasons'].get(r, 0)
        mv = mod_m['reasons'].get(r, 0)
        print(f"    {r:<15} {bv:>5} -> {mv:>5}")


def main():
    symbols = [
        'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT', 'NEARUSDT',
        'SUIUSDT', 'ARBUSDT', 'APTUSDT', 'INJUSDT', 'LINKUSDT',
    ]

    print("=" * 65)
    print("  Phase F: Balanced Trading System")
    print("  Testing smart entry + multi-exit improvements")
    print("=" * 65)

    print("\nFetching data...")
    engine = ScalpingV7Engine()
    all_data = {}
    for sym in symbols:
        df = fetch_klines(sym)
        if df is not None and len(df) >= 100:
            all_data[sym] = engine.prepare_data(df)
            print(f"  {sym}: {len(df)} bars")

    # ============================================================
    # BASELINE: Current V7 with A1+A3+B3+C2+C4
    # ============================================================
    print("\n🏁 BASELINE (current V7 with all improvements)...")
    bt_base = SmartBT(engine,
                      exit_features={'trail_activation': 0.006},
                      entry_features={})
    bt_base.run(all_data)
    base_m = bt_base.metrics()
    print(f"  -> {base_m['trades']} trades | WR={base_m['wr']:.1f}% | PF={base_m['pf']:.2f} | PnL=${base_m['pnl']:+.2f}")

    # ============================================================
    # F1: Lower trailing activation (0.6% -> 0.4%)
    # ============================================================
    print("\n🧪 F1: Trailing activation 0.4%...")
    bt_f1 = SmartBT(engine,
                    exit_features={'trail_activation': 0.004},
                    entry_features={})
    bt_f1.run(all_data)
    f1_m = bt_f1.metrics()
    print_comparison("F1", "Trailing activation 0.6% -> 0.4%", base_m, f1_m)

    # ============================================================
    # F1b: Even lower trailing (0.3%)
    # ============================================================
    print("\n🧪 F1b: Trailing activation 0.3%...")
    bt_f1b = SmartBT(engine,
                     exit_features={'trail_activation': 0.003},
                     entry_features={})
    bt_f1b.run(all_data)
    f1b_m = bt_f1b.metrics()
    print_comparison("F1b", "Trailing activation 0.3%", base_m, f1b_m)

    # ============================================================
    # F2: Partial exit 50% at +1%
    # ============================================================
    print("\n🧪 F2: Partial exit 50% at +1%...")
    bt_f2 = SmartBT(engine,
                    exit_features={'trail_activation': 0.006, 'partial_exit': True},
                    entry_features={})
    bt_f2.run(all_data)
    f2_m = bt_f2.metrics()
    print_comparison("F2", "Partial exit 50% at +1%", base_m, f2_m)

    # ============================================================
    # F3: Volume entry filter (vol_ratio > 1.5)
    # ============================================================
    print("\n🧪 F3: Volume filter vol>1.5x...")
    bt_f3 = SmartBT(engine,
                    exit_features={'trail_activation': 0.006},
                    entry_features={'vol_filter': True, 'vol_threshold': 1.5})
    bt_f3.run(all_data)
    f3_m = bt_f3.metrics()
    print_comparison("F3", "Volume entry filter > 1.5x", base_m, f3_m)

    # ============================================================
    # F3b: Volume filter > 2.0
    # ============================================================
    print("\n🧪 F3b: Volume filter vol>2.0x...")
    bt_f3b = SmartBT(engine,
                     exit_features={'trail_activation': 0.006},
                     entry_features={'vol_filter': True, 'vol_threshold': 2.0})
    bt_f3b.run(all_data)
    f3b_m = bt_f3b.metrics()
    print_comparison("F3b", "Volume entry filter > 2.0x", base_m, f3b_m)

    # ============================================================
    # F4: BE move at +0.5%
    # ============================================================
    print("\n🧪 F4: Break-even at +0.5%...")
    bt_f4 = SmartBT(engine,
                    exit_features={'trail_activation': 0.006, 'be_move': True},
                    entry_features={})
    bt_f4.run(all_data)
    f4_m = bt_f4.metrics()
    print_comparison("F4", "Break-even move at +0.5%", base_m, f4_m)

    # ============================================================
    # F4+F2: BE + Partial combo
    # ============================================================
    print("\n🧪 F4+F2: BE + Partial exit combo...")
    bt_f42 = SmartBT(engine,
                     exit_features={'trail_activation': 0.006, 'be_move': True, 'partial_exit': True},
                     entry_features={})
    bt_f42.run(all_data)
    f42_m = bt_f42.metrics()
    print_comparison("F4+F2", "BE move + Partial exit combo", base_m, f42_m)

    # ============================================================
    # F5: Reversal confirmation
    # ============================================================
    print("\n🧪 F5: Reversal-confirmed exit...")
    bt_f5 = SmartBT(engine,
                    exit_features={'trail_activation': 0.006, 'reversal_confirm': True},
                    entry_features={})
    bt_f5.run(all_data)
    f5_m = bt_f5.metrics()
    print_comparison("F5", "Reversal confirmation for trailing exit", base_m, f5_m)

    # ============================================================
    # F1+F2: Lower trail + Partial
    # ============================================================
    print("\n🧪 F1+F2: Trail 0.4% + Partial exit...")
    bt_12 = SmartBT(engine,
                    exit_features={'trail_activation': 0.004, 'partial_exit': True},
                    entry_features={})
    bt_12.run(all_data)
    f12_m = bt_12.metrics()
    print_comparison("F1+F2", "Trail 0.4% + Partial exit", base_m, f12_m)

    # ============================================================
    # F1+F4+F2: Trail 0.4% + BE + Partial
    # ============================================================
    print("\n🧪 F1+F4+F2: Trail 0.4% + BE + Partial...")
    bt_142 = SmartBT(engine,
                     exit_features={'trail_activation': 0.004, 'be_move': True, 'partial_exit': True},
                     entry_features={})
    bt_142.run(all_data)
    f142_m = bt_142.metrics()
    print_comparison("F1+F4+F2", "Trail 0.4% + BE + Partial", base_m, f142_m)

    # ============================================================
    # BEST COMBO: Top performers combined
    # ============================================================
    print("\n🧪 BEST: Trail 0.4% + Partial + BE + RevConfirm...")
    bt_best = SmartBT(engine,
                      exit_features={
                          'trail_activation': 0.004,
                          'partial_exit': True,
                          'be_move': True,
                          'reversal_confirm': True,
                      },
                      entry_features={})
    bt_best.run(all_data)
    best_m = bt_best.metrics()
    print_comparison("BEST", "All exit improvements combined", base_m, best_m)

    # ============================================================
    # SUMMARY
    # ============================================================
    results = [
        ("F1: Trail 0.4%", f1_m),
        ("F1b: Trail 0.3%", f1b_m),
        ("F2: Partial", f2_m),
        ("F3: Vol>1.5", f3_m),
        ("F3b: Vol>2.0", f3b_m),
        ("F4: BE", f4_m),
        ("F4+F2: BE+Part", f42_m),
        ("F5: RevConfirm", f5_m),
        ("F1+F2", f12_m),
        ("F1+F4+F2", f142_m),
        ("BEST: All", best_m),
    ]

    print("\n" + "=" * 65)
    print("  SUMMARY — Phase F Results")
    print("=" * 65)
    print(f"  {'Test':<20} {'PnL':>10} {'dPnL':>8} {'WR':>7} {'PF':>6} {'Trades':>7}")
    print(f"  {'-' * 60}")
    print(f"  {'BASELINE':<20} ${base_m['pnl']:>+8.2f} {'---':>8} {base_m['wr']:>6.1f}% {base_m['pf']:>5.2f} {base_m['trades']:>7}")
    for name, m in results:
        dpnl = m['pnl'] - base_m['pnl']
        marker = '✅' if dpnl > 10 else '❌' if dpnl < -10 else '⚠️'
        print(f"  {marker} {name:<18} ${m['pnl']:>+8.2f} {dpnl:>+7.0f} {m['wr']:>6.1f}% {m['pf']:>5.2f} {m['trades']:>7}")

    # Find best
    best_name, best_result = max(results, key=lambda x: x[1]['pnl'])
    print(f"\n  🏆 Best: {best_name} -> PnL=${best_result['pnl']:+.2f} | WR={best_result['wr']:.1f}% | PF={best_result['pf']:.2f}")
    print("=" * 65)


if __name__ == '__main__':
    main()
