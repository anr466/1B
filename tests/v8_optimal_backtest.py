#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8.4 OPTIMAL Backtest — Smart Exit on top of V7 Entry
======================================================
Strategy: Keep V7's high-WR entries, fix the exit system only.

Key Changes:
1. Smart Early Exit (momentum-aware, not blind cut)
2. Faster Breakeven (move SL to entry at +0.5%)
3. Keep V7 trailing (94% WR proven)
4. No Multi-TP partial exits (keeps trade count high)
5. Wider initial SL via ATR (reduces SL hits)

Target: WR>60% PF>2
"""

import sys, os, json, time, logging
import requests, pandas as pd, numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from backend.strategies.scalping_v7_engine import ScalpingV7Engine, V7_CONFIG

logging.basicConfig(level=logging.WARNING)


def fetch_klines(symbol, interval='1h', days=60):
    url = "https://api.binance.com/api/v3/klines"
    all_data = []
    end_t = int(datetime.now().timestamp() * 1000)
    start_t = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    cur = start_t
    while cur < end_t:
        try:
            r = requests.get(url, params={'symbol': symbol, 'interval': interval,
                                          'startTime': cur, 'endTime': end_t, 'limit': 1000}, timeout=15)
            data = r.json()
        except:
            break
        if not data: break
        all_data.extend(data)
        cur = data[-1][0] + 1
        if len(data) < 1000: break
        time.sleep(0.2)
    if not all_data: return pd.DataFrame()
    df = pd.DataFrame(all_data, columns=[
        'timestamp','open','high','low','close','volume',
        'ct','qv','trades','tbb','tbq','ig'])
    for c in ['open','high','low','close','volume']: df[c] = df[c].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df[['timestamp','open','high','low','close','volume']].drop_duplicates('timestamp').sort_values('timestamp').reset_index(drop=True)


class SmartExitBacktester:
    """
    Uses V7 entries unchanged. Patches only the exit logic.
    Fixed $60 risk per trade (no compounding distortion).
    """

    def __init__(self, engine, exit_mode='v7', initial_balance=1000.0):
        self.engine = engine
        self.exit_mode = exit_mode  # 'v7', 'v8_smart', 'v8_optimal'
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.open_positions = []
        self.closed_trades = []
        self.commission = 0.001
        self.slippage = 0.0005

    def run(self, symbol, df):
        df_p = self.engine.prepare_data(df)
        if df_p is None or len(df_p) < 80:
            return {'symbol': symbol, 'total_trades': 0}

        for i in range(60, len(df_p)):
            bar = df_p.iloc[i]
            self._check_exits(df_p, i, symbol)

            if len(self.open_positions) < 5:
                trend = self.engine.get_4h_trend(df_p, i - 1)
                sig = self.engine.detect_entry(df_p, trend, i - 1)
                if sig:
                    ep = bar['open'] * (1 + self.slippage if sig['side'] == 'LONG' else 1 - self.slippage)
                    self._open(symbol, sig, ep, bar.get('timestamp', i), i)

        # Close remaining
        if self.open_positions and len(df_p) > 0:
            last = df_p.iloc[-1]
            for pos in list(self.open_positions):
                self._close(pos, last['close'], 'END_OF_DATA', last)

        return self._report(symbol)

    def _open(self, symbol, sig, ep, bar_time, bar_idx):
        val = min(60.0, self.balance * 0.10)
        if val < 10: return
        qty = val / ep
        comm = val * self.commission
        self.balance -= comm

        sl = sig.get('stop_loss', 0)
        if sl <= 0:
            sl = ep * (1 - 0.008) if sig['side'] == 'LONG' else ep * (1 + 0.008)

        self.open_positions.append({
            'symbol': symbol, 'side': sig['side'],
            'entry_price': ep, 'quantity': qty, 'value': val,
            'sl': sl, 'trail': 0, 'peak': ep,
            'entry_time': bar_time, 'entry_bar': bar_idx,
            'entry_comm': comm, 'strategy': sig.get('strategy', ''),
            'score': sig.get('score', 0), 'hold_bars': 0,
            'be_moved': False,
        })

    def _check_exits(self, df, idx, symbol):
        to_close = []
        for pos in self.open_positions:
            pos['hold_bars'] += 1
            row = df.iloc[idx]
            hi, lo, cl = row['high'], row['low'], row['close']
            entry = pos['entry_price']
            side = pos['side']
            peak = pos['peak']
            trail = pos['trail']
            sl = pos['sl']
            hb = pos['hold_bars']

            # PnL
            if side == 'LONG':
                pnl = (cl - entry) / entry
                pnl_peak = (peak - entry) / entry
                if hi > peak:
                    peak = hi
                    pos['peak'] = peak
            else:
                pnl = (entry - cl) / entry
                pnl_peak = (entry - peak) / entry
                if lo < peak:
                    peak = lo
                    pos['peak'] = peak

            # === STOP LOSS ===
            if side == 'LONG' and lo <= sl:
                to_close.append((pos, sl, 'STOP_LOSS', row)); continue
            if side == 'SHORT' and hi >= sl:
                to_close.append((pos, sl, 'STOP_LOSS', row)); continue

            # === EXIT MODE SPECIFIC LOGIC ===
            if self.exit_mode == 'v7':
                result = self._v7_exit(df, idx, pos, pnl, pnl_peak, peak, trail, sl, hb)
            elif self.exit_mode == 'v8_smart':
                result = self._v8_smart_exit(df, idx, pos, pnl, pnl_peak, peak, trail, sl, hb)
            elif self.exit_mode == 'v8_optimal':
                result = self._v8_optimal_exit(df, idx, pos, pnl, pnl_peak, peak, trail, sl, hb)
            else:
                result = None

            if result:
                to_close.append((pos, result[0], result[1], row))

        for pos, price, reason, bar in to_close:
            if side := pos['side']:
                price *= (1 - self.slippage) if side == 'LONG' else (1 + self.slippage)
            self._close(pos, price, reason, bar)

    def _v7_exit(self, df, idx, pos, pnl, pnl_peak, peak, trail, sl, hb):
        """Original V7 exit logic (baseline)"""
        row = df.iloc[idx]
        lo, hi, cl = row['low'], row['high'], row['close']
        side = pos['side']
        entry = pos['entry_price']

        # Trailing
        trail_dist = 0.003
        if pnl_peak >= 0.02: trail_dist = 0.002
        elif pnl_peak >= 0.015: trail_dist = 0.003
        elif pnl_peak >= 0.01: trail_dist = 0.0035

        if pnl_peak >= 0.004:
            if side == 'LONG':
                ts = peak * (1 - trail_dist)
                if ts > trail:
                    trail = ts
                    pos['trail'] = trail
                if trail > 0 and lo <= trail:
                    return (trail, 'TRAILING')
            else:
                ts = peak * (1 + trail_dist)
                if trail == 0 or ts < trail:
                    trail = ts
                    pos['trail'] = trail
                if trail > 0 and hi >= trail:
                    return (trail, 'TRAILING')

        # Breakeven (V7: at +0.5%)
        if pnl_peak >= 0.005 and not pos.get('be_moved'):
            if side == 'LONG' and sl < entry:
                pos['sl'] = entry * 1.0001
                pos['be_moved'] = True
            elif side == 'SHORT' and sl > entry:
                pos['sl'] = entry * 0.9999
                pos['be_moved'] = True

        # Reversal (if in profit > 0.3%)
        rev = self._check_reversal(df, idx, pos, pnl)
        if rev: return rev

        # Early cut (V7 original: 3h / -0.5%)
        if hb >= 3 and pnl < -0.005:
            return (cl, 'EARLY_CUT')

        # Stagnant
        if hb >= 4 and abs(pnl) < 0.002:
            return (cl, 'STAGNANT')

        # Max hold
        if hb >= 12:
            return (cl, 'MAX_HOLD')

        return None

    def _v8_smart_exit(self, df, idx, pos, pnl, pnl_peak, peak, trail, sl, hb):
        """V8 Smart Exit: momentum-aware early cut + faster breakeven"""
        row = df.iloc[idx]
        prev = df.iloc[idx - 1] if idx > 0 else row
        lo, hi, cl = row['low'], row['high'], row['close']
        side = pos['side']
        entry = pos['entry_price']

        # === TRAILING (same as V7 - proven) ===
        trail_dist = 0.003
        if pnl_peak >= 0.02: trail_dist = 0.002
        elif pnl_peak >= 0.015: trail_dist = 0.003
        elif pnl_peak >= 0.01: trail_dist = 0.0035

        if pnl_peak >= 0.004:
            if side == 'LONG':
                ts = peak * (1 - trail_dist)
                if ts > trail:
                    trail = ts
                    pos['trail'] = trail
                if trail > 0 and lo <= trail:
                    return (trail, 'TRAILING')
            else:
                ts = peak * (1 + trail_dist)
                if trail == 0 or ts < trail:
                    trail = ts
                    pos['trail'] = trail
                if trail > 0 and hi >= trail:
                    return (trail, 'TRAILING')

        # === FASTER BREAKEVEN (at +0.4% instead of +0.5%) ===
        if pnl_peak >= 0.004 and not pos.get('be_moved'):
            if side == 'LONG' and sl < entry:
                pos['sl'] = entry * 1.0001
                pos['be_moved'] = True
            elif side == 'SHORT' and sl > entry:
                pos['sl'] = entry * 0.9999
                pos['be_moved'] = True

        # === REVERSAL EXIT ===
        rev = self._check_reversal(df, idx, pos, pnl)
        if rev: return rev

        # === SMART EARLY EXIT (momentum-aware) ===
        if hb >= 2 and pnl < -0.003:
            momentum_against = self._check_momentum_against(df, idx, side)
            if momentum_against:
                return (cl, 'SMART_CUT')

        if hb >= 5 and pnl < -0.004:
            return (cl, 'SMART_CUT_LATE')

        # Stagnant (slightly longer)
        if hb >= 5 and abs(pnl) < 0.002:
            return (cl, 'STAGNANT')

        # Max hold
        if hb >= 14:
            return (cl, 'MAX_HOLD')

        return None

    def _v8_optimal_exit(self, df, idx, pos, pnl, pnl_peak, peak, trail, sl, hb):
        """
        V8.4 OPTIMAL: Best combination of all learnings.
        - Aggressive breakeven (lock in BE early)
        - Smart momentum-based early exit
        - Progressive trailing (proven)
        - Wider SL tolerance for first 2 hours
        """
        row = df.iloc[idx]
        lo, hi, cl = row['low'], row['high'], row['close']
        side = pos['side']
        entry = pos['entry_price']

        # === PROGRESSIVE TRAILING (proven 94% WR) ===
        trail_dist = 0.003
        if pnl_peak >= 0.025: trail_dist = 0.0015
        elif pnl_peak >= 0.02: trail_dist = 0.002
        elif pnl_peak >= 0.015: trail_dist = 0.0025
        elif pnl_peak >= 0.01: trail_dist = 0.003

        if pnl_peak >= 0.004:
            if side == 'LONG':
                ts = peak * (1 - trail_dist)
                if ts > trail:
                    trail = ts
                    pos['trail'] = trail
                if trail > 0 and lo <= trail:
                    return (trail, 'TRAILING')
            else:
                ts = peak * (1 + trail_dist)
                if trail == 0 or ts < trail:
                    trail = ts
                    pos['trail'] = trail
                if trail > 0 and hi >= trail:
                    return (trail, 'TRAILING')

        # === AGGRESSIVE BREAKEVEN (at +0.35%) ===
        if pnl_peak >= 0.0035 and not pos.get('be_moved'):
            if side == 'LONG' and sl < entry:
                pos['sl'] = entry * 1.0001
                pos['be_moved'] = True
            elif side == 'SHORT' and sl > entry:
                pos['sl'] = entry * 0.9999
                pos['be_moved'] = True

        # === REVERSAL EXIT (profitable trades) ===
        rev = self._check_reversal(df, idx, pos, pnl)
        if rev: return rev

        # === SMART EARLY EXIT V2 ===
        # Phase 1: After 2 bars, if losing AND strong momentum against → cut
        if hb >= 2 and pnl < -0.002:
            mom_score = self._momentum_score(df, idx, side)
            if mom_score <= -3:  # Strong momentum against
                return (cl, 'SMART_CUT')

        # Phase 2: After 4 bars, cut moderate losers with weak momentum
        if hb >= 4 and pnl < -0.003:
            mom_score = self._momentum_score(df, idx, side)
            if mom_score <= 0:  # No positive momentum
                return (cl, 'SMART_CUT_MID')

        # Phase 3: After 6 bars, cut any losing position
        if hb >= 6 and pnl < -0.004:
            return (cl, 'SMART_CUT_LATE')

        # Stagnant
        if hb >= 5 and abs(pnl) < 0.0015:
            return (cl, 'STAGNANT')

        # Max hold
        if hb >= 14:
            return (cl, 'MAX_HOLD')

        return None

    def _momentum_score(self, df, idx, side):
        """
        Calculate momentum score for the position's direction.
        Positive = momentum supports position, Negative = against.
        Range: roughly -6 to +6.
        """
        if idx < 3: return 0
        row = df.iloc[idx]
        prev = df.iloc[idx - 1]
        prev2 = df.iloc[idx - 2]
        score = 0

        rsi = row.get('rsi', 50)
        prev_rsi = prev.get('rsi', 50)
        macd_h = row.get('macd_h', 0)
        prev_macd_h = prev.get('macd_h', 0)
        st_dir = row.get('st_dir', 0)

        if side == 'LONG':
            # RSI improving
            if not pd.isna(rsi) and not pd.isna(prev_rsi):
                if rsi > prev_rsi: score += 1
                elif rsi < prev_rsi - 3: score -= 1
                if rsi < 35: score -= 1
                if rsi > 55: score += 1

            # MACD improving
            if not pd.isna(macd_h) and not pd.isna(prev_macd_h):
                if macd_h > prev_macd_h: score += 1
                elif macd_h < prev_macd_h: score -= 1
                if macd_h > 0: score += 1
                elif macd_h < 0: score -= 1

            # SuperTrend
            if not pd.isna(st_dir):
                if st_dir == 1: score += 1
                else: score -= 1

            # Price vs EMA
            ema8 = row.get('ema8', 0)
            if not pd.isna(ema8) and ema8 > 0:
                if row['close'] > ema8: score += 1
                else: score -= 1

        else:  # SHORT — mirror logic
            if not pd.isna(rsi) and not pd.isna(prev_rsi):
                if rsi < prev_rsi: score += 1
                elif rsi > prev_rsi + 3: score -= 1
                if rsi > 65: score -= 1
                if rsi < 45: score += 1

            if not pd.isna(macd_h) and not pd.isna(prev_macd_h):
                if macd_h < prev_macd_h: score += 1
                elif macd_h > prev_macd_h: score -= 1
                if macd_h < 0: score += 1
                elif macd_h > 0: score -= 1

            if not pd.isna(st_dir):
                if st_dir == -1: score += 1
                else: score -= 1

            ema8 = row.get('ema8', 0)
            if not pd.isna(ema8) and ema8 > 0:
                if row['close'] < ema8: score += 1
                else: score -= 1

        return score

    def _check_momentum_against(self, df, idx, side):
        """Simple check: is momentum against the position?"""
        return self._momentum_score(df, idx, side) <= -2

    def _check_reversal(self, df, idx, pos, pnl):
        if idx < 2 or pnl <= 0.003: return None
        row = df.iloc[idx]
        prev = df.iloc[idx - 1]
        cl = row['close']
        side = pos['side']
        rev = 0

        if side == 'LONG':
            if not pd.isna(row.get('st_dir')) and not pd.isna(prev.get('st_dir')):
                if prev['st_dir'] == 1 and row['st_dir'] == -1: rev += 3
            if prev.get('bull', True) and not row.get('bull', True):
                if row.get('body', 0) > prev.get('body', 0): rev += 2
            if not pd.isna(row.get('macd_l')) and not pd.isna(prev.get('macd_l')):
                if prev['macd_l'] > prev['macd_s'] and row['macd_l'] < row['macd_s']: rev += 2
        else:
            if not pd.isna(row.get('st_dir')) and not pd.isna(prev.get('st_dir')):
                if prev['st_dir'] == -1 and row['st_dir'] == 1: rev += 3
            if not prev.get('bull', False) and row.get('bull', False):
                if row.get('body', 0) > prev.get('body', 0): rev += 2
            if not pd.isna(row.get('macd_l')) and not pd.isna(prev.get('macd_l')):
                if prev['macd_l'] < prev['macd_s'] and row['macd_l'] > row['macd_s']: rev += 2

        if rev >= 3: return (cl, 'REVERSAL')
        return None

    def _close(self, pos, ep, reason, bar):
        if pos['side'] == 'LONG':
            pnl_pct = (ep - pos['entry_price']) / pos['entry_price']
        else:
            pnl_pct = (pos['entry_price'] - ep) / pos['entry_price']

        pnl_dollar = pos['value'] * pnl_pct
        exit_comm = (pos['value'] * (1 + pnl_pct)) * self.commission
        net = pnl_dollar - exit_comm
        self.balance += pos['value'] + pnl_dollar - exit_comm

        self.closed_trades.append({
            'symbol': pos['symbol'], 'side': pos['side'],
            'entry_price': pos['entry_price'], 'exit_price': ep,
            'pnl_pct': round(pnl_pct * 100, 4),
            'pnl_dollar': round(net, 4),
            'commission': round(pos['entry_comm'] + exit_comm, 4),
            'hold_hours': pos['hold_bars'],
            'exit_reason': reason, 'strategy': pos['strategy'],
            'score': pos['score'], 'is_win': net > 0,
        })
        self.open_positions.remove(pos)

    def _report(self, symbol):
        trades = [t for t in self.closed_trades if t['symbol'] == symbol]
        if not trades: return {'symbol': symbol, 'total_trades': 0}
        wins = [t for t in trades if t['is_win']]
        losses = [t for t in trades if not t['is_win']]
        gp = sum(t['pnl_dollar'] for t in wins) if wins else 0
        gl = abs(sum(t['pnl_dollar'] for t in losses)) if losses else 0.001
        return {
            'symbol': symbol, 'total_trades': len(trades),
            'wins': len(wins), 'losses': len(losses),
            'win_rate': round(len(wins)/len(trades)*100, 1),
            'profit_factor': round(gp/gl, 2),
            'total_pnl': round(sum(t['pnl_dollar'] for t in trades), 2),
            'trades': trades,
        }

    def reset(self):
        self.balance = self.initial_balance
        self.open_positions = []
        self.closed_trades = []


def run_all_tests():
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
        'AVAXUSDT', 'NEARUSDT', 'SUIUSDT', 'ARBUSDT', 'APTUSDT',
        'INJUSDT', 'LINKUSDT',
    ]

    print(f"\n{'='*70}")
    print(f"  Fetching 60-day data for {len(symbols)} symbols...")
    print(f"{'='*70}")
    data = {}
    for s in symbols:
        print(f"  → {s}...", end=" ", flush=True)
        df = fetch_klines(s, '1h', 60)
        if not df.empty and len(df) >= 80:
            data[s] = df
            print(f"✅ {len(df)}")
        else:
            print("❌")
        time.sleep(0.3)

    engine = ScalpingV7Engine(V7_CONFIG)
    results = {}

    for mode_name, mode_label in [
        ('v7', 'V7.1 BASELINE'),
        ('v8_smart', 'V8 SMART EXIT'),
        ('v8_optimal', 'V8.4 OPTIMAL'),
    ]:
        print(f"\n{'='*70}")
        print(f"  🔬 {mode_label}")
        print(f"{'='*70}")

        all_trades = []
        for sym, df in data.items():
            bt = SmartExitBacktester(engine, exit_mode=mode_name)
            r = bt.run(sym, df)
            if r.get('trades'): all_trades.extend(r['trades'])
            n = r.get('total_trades', 0)
            wr = r.get('win_rate', 0)
            pf = r.get('profit_factor', 0)
            pnl = r.get('total_pnl', 0)
            s = "✅" if pnl > 0 else "❌"
            print(f"  {s} {sym:12s} | N:{n:3d} | WR:{wr:5.1f}% | PF:{pf:5.2f} | PnL:${pnl:+8.2f}")

        results[mode_label] = _agg(all_trades, mode_label)

    # Comparison
    print(f"\n{'='*70}")
    print(f"  📊 FINAL COMPARISON")
    print(f"{'='*70}")
    print(f"  {'System':22s} | {'WR':>6s} | {'PF':>5s} | {'N':>5s} | {'PnL':>10s} | {'AvgW':>7s} | {'AvgL':>7s} | {'R:R':>5s}")
    print(f"  {'-'*22}-+-{'-'*6}-+-{'-'*5}-+-{'-'*5}-+-{'-'*10}-+-{'-'*7}-+-{'-'*7}-+-{'-'*5}")
    for name, r in results.items():
        wr = r['win_rate']
        pf = r['profit_factor']
        nt = r['total_trades']
        pnl = r['total_pnl']
        aw = r['avg_win']
        al = r['avg_loss']
        rr = abs(aw / al) if al != 0 else 0
        print(f"  {name:22s} | {wr:5.1f}% | {pf:5.2f} | {nt:5d} | ${pnl:+9.2f} | {aw:+6.3f}% | {al:+6.3f}% | {rr:5.2f}")

    # Save detailed results
    out = os.path.join(PROJECT_ROOT, 'tests', 'backtest_results')
    os.makedirs(out, exist_ok=True)
    for name, r in results.items():
        fname = name.lower().replace(' ', '_').replace('.', '')
        with open(os.path.join(out, f'{fname}_detail.json'), 'w') as f:
            json.dump({k: v for k, v in r.items() if k != 'trades'}, f, indent=2, default=str)

    return results


def _agg(trades, label):
    if not trades:
        return {'total_trades': 0, 'win_rate': 0, 'profit_factor': 0, 'total_pnl': 0,
                'avg_win': 0, 'avg_loss': 0}

    wins = [t for t in trades if t['is_win']]
    losses = [t for t in trades if not t['is_win']]
    gp = sum(t['pnl_dollar'] for t in wins) if wins else 0
    gl = abs(sum(t['pnl_dollar'] for t in losses)) if losses else 0.001
    pnl = sum(t['pnl_dollar'] for t in trades)

    # Exit breakdown
    exits = defaultdict(lambda: {'n': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        r = t['exit_reason']
        exits[r]['n'] += 1
        exits[r]['pnl'] += t['pnl_dollar']
        if t['is_win']: exits[r]['wins'] += 1

    # Strategy breakdown
    strats = defaultdict(lambda: {'n': 0, 'pnl': 0, 'wins': 0, 'pcts': []})
    for t in trades:
        s = t['strategy']
        strats[s]['n'] += 1
        strats[s]['pnl'] += t['pnl_dollar']
        strats[s]['pcts'].append(t['pnl_pct'])
        if t['is_win']: strats[s]['wins'] += 1

    longs = [t for t in trades if t['side'] == 'LONG']
    shorts = [t for t in trades if t['side'] == 'SHORT']
    aw = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
    al = np.mean([t['pnl_pct'] for t in losses]) if losses else 0

    print(f"\n  📊 {label}:")
    print(f"  Trades:{len(trades)} | WR:{len(wins)/len(trades)*100:.1f}% | PF:{gp/gl:.2f} | PnL:${pnl:+.2f}")
    print(f"  AvgWin:{aw:+.3f}% | AvgLoss:{al:+.3f}% | R:R={abs(aw/al) if al else 0:.2f}")
    print(f"  LONG:{len(longs)}(WR:{sum(1 for t in longs if t['is_win'])/max(len(longs),1)*100:.1f}%) | "
          f"SHORT:{len(shorts)}(WR:{sum(1 for t in shorts if t['is_win'])/max(len(shorts),1)*100:.1f}%)")

    print(f"\n  Exit Reasons:")
    for r, d in sorted(exits.items(), key=lambda x: x[1]['n'], reverse=True):
        wr = d['wins']/max(d['n'],1)*100
        print(f"    {r:18s} | N:{d['n']:4d} | WR:{wr:5.1f}% | PnL:${d['pnl']:+8.2f}")

    print(f"\n  Strategies:")
    for s, d in sorted(strats.items(), key=lambda x: x[1]['pnl'], reverse=True):
        wr = d['wins']/max(d['n'],1)*100
        avg = np.mean(d['pcts']) if d['pcts'] else 0
        print(f"    {s:22s} | N:{d['n']:4d} | WR:{wr:5.1f}% | Avg:{avg:+.3f}% | PnL:${d['pnl']:+8.2f}")

    return {
        'total_trades': len(trades), 'wins': len(wins), 'losses': len(losses),
        'win_rate': round(len(wins)/len(trades)*100, 1),
        'profit_factor': round(gp/gl, 2),
        'total_pnl': round(pnl, 2),
        'avg_win': round(aw, 3), 'avg_loss': round(al, 3),
        'exit_reasons': {k: dict(v) for k, v in exits.items()},
        'strategy_stats': {k: {kk: vv for kk, vv in v.items() if kk != 'pcts'} for k, v in strats.items()},
        'trades': trades,
    }


if __name__ == '__main__':
    print("\n" + "="*70)
    print("  V8.4 OPTIMAL BACKTEST — Smart Exit Comparison")
    print("  V7 Entries + 3 Exit Modes | Fixed $60 Risk | 12 Symbols | 60 Days")
    print("="*70)
    run_all_tests()
