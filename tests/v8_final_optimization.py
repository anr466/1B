#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8.5+ FINAL OPTIMIZATION — Iterating to PF>2 WR>60%
=====================================================
Based on V8.4 OPTIMAL results, applying targeted improvements:
1. Block 'reversal' strategy (only losing strategy, -$93)
2. 2-Phase SL: wider first 2 bars, then tighten
3. Aggressive breakeven at +0.3%
4. Lock-in trailing: tighter distance at higher profit
5. Smarter early cut: lower threshold, momentum-based
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
    all_data, end_t = [], int(datetime.now().timestamp() * 1000)
    cur = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    while cur < end_t:
        try:
            r = requests.get(url, params={'symbol': symbol, 'interval': interval,
                'startTime': cur, 'endTime': end_t, 'limit': 1000}, timeout=15)
            data = r.json()
        except: break
        if not data: break
        all_data.extend(data)
        cur = data[-1][0] + 1
        if len(data) < 1000: break
        time.sleep(0.2)
    if not all_data: return pd.DataFrame()
    df = pd.DataFrame(all_data, columns=[
        'timestamp','open','high','low','close','volume','ct','qv','trades','tbb','tbq','ig'])
    for c in ['open','high','low','close','volume']: df[c] = df[c].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df[['timestamp','open','high','low','close','volume']].drop_duplicates('timestamp').sort_values('timestamp').reset_index(drop=True)


# ============================================================
# CONFIGURABLE EXIT VARIANTS
# ============================================================

EXIT_CONFIGS = {
    # Previous best: V8.8 PF=1.59 R:R=1.02, V8.7 WR=71.3%
    # Now: Hybrid combinations targeting PF>2.0

    # HYBRID A: V8.7 wide SL + V8.8 ultra-tight trail + V8.6 aggressive BE
    'V9.0_HYBRID_A': {
        'block_reversal': True,
        'be_trigger': 0.0025,        # Aggressive BE from V8.6
        'trail_activation': 0.002,   # Ultra-early trail from V8.8
        'trail_base_dist': 0.002,    # Tight trail from V8.8
        'smart_cut_1_bars': 1, 'smart_cut_1_loss': -0.002, 'smart_cut_1_mom': -4,
        'smart_cut_2_bars': 3, 'smart_cut_2_loss': -0.002, 'smart_cut_2_mom': -1,
        'smart_cut_3_bars': 5, 'smart_cut_3_loss': -0.003,
        'stagnant_bars': 3, 'stagnant_thresh': 0.001,
        'max_hold': 10,
        'sl_multiplier': 1.5,        # Wide SL from V8.7
        'progressive_trail': {0.02: 0.001, 0.015: 0.0012, 0.01: 0.0015, 0.005: 0.002},
    },

    # HYBRID B: Like A but even tighter trailing at high profit
    'V9.1_HYBRID_B': {
        'block_reversal': True,
        'be_trigger': 0.002,         # Very aggressive BE at +0.2%
        'trail_activation': 0.0015,  # Ultra-early trail
        'trail_base_dist': 0.0018,   # Very tight base
        'smart_cut_1_bars': 1, 'smart_cut_1_loss': -0.0015, 'smart_cut_1_mom': -3,
        'smart_cut_2_bars': 2, 'smart_cut_2_loss': -0.002, 'smart_cut_2_mom': -1,
        'smart_cut_3_bars': 4, 'smart_cut_3_loss': -0.0025,
        'stagnant_bars': 3, 'stagnant_thresh': 0.0008,
        'max_hold': 8,
        'sl_multiplier': 1.5,
        'progressive_trail': {0.02: 0.0008, 0.015: 0.001, 0.01: 0.0012, 0.005: 0.0015, 0.003: 0.0018},
    },

    # HYBRID C: Higher min_confluence (5) for better entry quality + tight trail
    'V9.2_QUALITY_ENTRY': {
        'block_reversal': True,
        'block_breakdown': True,     # Also block breakdown (lower WR)
        'min_confluence': 5,         # Higher entry threshold
        'be_trigger': 0.002,
        'trail_activation': 0.002,
        'trail_base_dist': 0.002,
        'smart_cut_1_bars': 1, 'smart_cut_1_loss': -0.002, 'smart_cut_1_mom': -3,
        'smart_cut_2_bars': 3, 'smart_cut_2_loss': -0.002, 'smart_cut_2_mom': -1,
        'smart_cut_3_bars': 5, 'smart_cut_3_loss': -0.003,
        'stagnant_bars': 3, 'stagnant_thresh': 0.001,
        'max_hold': 10,
        'sl_multiplier': 1.3,
        'progressive_trail': {0.02: 0.001, 0.015: 0.0012, 0.01: 0.0015, 0.005: 0.002},
    },

    # HYBRID D: Wide SL 2.0x + very tight progressive trail + fast smart cuts
    'V9.3_WIDE_SL_2X': {
        'block_reversal': True,
        'be_trigger': 0.003,
        'trail_activation': 0.002,
        'trail_base_dist': 0.002,
        'smart_cut_1_bars': 1, 'smart_cut_1_loss': -0.002, 'smart_cut_1_mom': -4,
        'smart_cut_2_bars': 2, 'smart_cut_2_loss': -0.003, 'smart_cut_2_mom': -2,
        'smart_cut_3_bars': 4, 'smart_cut_3_loss': -0.004,
        'stagnant_bars': 4, 'stagnant_thresh': 0.001,
        'max_hold': 12,
        'sl_multiplier': 2.0,        # 2x wider SL
        'progressive_trail': {0.025: 0.0008, 0.02: 0.001, 0.015: 0.0012, 0.01: 0.0015, 0.005: 0.002},
    },

    # HYBRID E: Scalping mode — fastest possible entries/exits
    'V9.4_SCALPING': {
        'block_reversal': True,
        'be_trigger': 0.0015,        # BE at +0.15%
        'trail_activation': 0.001,   # Trail at +0.1%
        'trail_base_dist': 0.0015,   # 0.15% trail distance
        'smart_cut_1_bars': 1, 'smart_cut_1_loss': -0.001, 'smart_cut_1_mom': -2,
        'smart_cut_2_bars': 2, 'smart_cut_2_loss': -0.0015, 'smart_cut_2_mom': 0,
        'smart_cut_3_bars': 3, 'smart_cut_3_loss': -0.002,
        'stagnant_bars': 2, 'stagnant_thresh': 0.0005,
        'max_hold': 6,
        'sl_multiplier': 1.0,
        'progressive_trail': {0.015: 0.0006, 0.01: 0.0008, 0.005: 0.001, 0.003: 0.0012, 0.002: 0.0015},
    },

    # HYBRID F: Best of V8.8 + wider SL 1.3x + faster smart cuts
    'V9.5_REFINED_BEST': {
        'block_reversal': True,
        'be_trigger': 0.0025,
        'trail_activation': 0.002,
        'trail_base_dist': 0.002,
        'smart_cut_1_bars': 1, 'smart_cut_1_loss': -0.0015, 'smart_cut_1_mom': -3,
        'smart_cut_2_bars': 2, 'smart_cut_2_loss': -0.002, 'smart_cut_2_mom': -1,
        'smart_cut_3_bars': 4, 'smart_cut_3_loss': -0.0025,
        'stagnant_bars': 3, 'stagnant_thresh': 0.001,
        'max_hold': 10,
        'sl_multiplier': 1.3,
        'progressive_trail': {0.02: 0.0008, 0.015: 0.001, 0.01: 0.0012, 0.005: 0.0018},
    },
}


class OptimizedBacktester:
    def __init__(self, engine, exit_cfg, initial_balance=1000.0):
        self.engine = engine
        self.cfg = exit_cfg
        self.balance = initial_balance
        self.initial_balance = initial_balance
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
            self._check_exits(df_p, i)

            if len(self.open_positions) < 5:
                trend = self.engine.get_4h_trend(df_p, i - 1)
                sig = self.engine.detect_entry(df_p, trend, i - 1)
                if sig:
                    # Block strategies if configured
                    if self.cfg.get('block_reversal') and sig.get('strategy') == 'reversal':
                        continue
                    if self.cfg.get('block_breakdown') and sig.get('strategy') == 'breakdown':
                        continue
                    # Higher confluence filter
                    min_conf = self.cfg.get('min_confluence', 0)
                    if min_conf > 0 and sig.get('score', 0) < min_conf:
                        continue

                    ep = bar['open']
                    if sig['side'] == 'LONG':
                        ep *= (1 + self.slippage)
                    else:
                        ep *= (1 - self.slippage)
                    self._open(symbol, sig, ep, bar.get('timestamp', i), i, df_p)

        for pos in list(self.open_positions):
            self._close(pos, df_p.iloc[-1]['close'], 'END_OF_DATA')
        return self._report(symbol)

    def _open(self, symbol, sig, ep, time, idx, df):
        val = min(60.0, self.balance * 0.10)
        if val < 10: return
        comm = val * self.commission
        self.balance -= comm

        # SL with multiplier
        sl = sig.get('stop_loss', 0)
        mult = self.cfg.get('sl_multiplier', 1.0)
        if sl > 0 and mult != 1.0:
            if sig['side'] == 'LONG':
                dist = ep - sl
                sl = ep - dist * mult
            else:
                dist = sl - ep
                sl = ep + dist * mult
        if sl <= 0:
            sl = ep * (1 - 0.008 * mult) if sig['side'] == 'LONG' else ep * (1 + 0.008 * mult)

        self.open_positions.append({
            'symbol': symbol, 'side': sig['side'],
            'entry_price': ep, 'value': val,
            'sl': sl, 'trail': 0, 'peak': ep,
            'entry_time': time, 'entry_bar': idx,
            'entry_comm': comm, 'strategy': sig.get('strategy', ''),
            'score': sig.get('score', 0), 'hold_bars': 0,
            'be_moved': False,
        })

    def _check_exits(self, df, idx):
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

            if side == 'LONG':
                pnl = (cl - entry) / entry
                if hi > peak: peak = hi; pos['peak'] = peak
                pnl_peak = (peak - entry) / entry
                if lo <= sl:
                    to_close.append((pos, sl, 'STOP_LOSS')); continue
            else:
                pnl = (entry - cl) / entry
                if lo < peak: peak = lo; pos['peak'] = peak
                pnl_peak = (entry - peak) / entry
                if hi >= sl:
                    to_close.append((pos, sl, 'STOP_LOSS')); continue

            result = self._exit_logic(df, idx, pos, pnl, pnl_peak, peak, trail, sl, hb)
            if result:
                to_close.append((pos, result[0], result[1]))

        for pos, price, reason in to_close:
            if pos['side'] == 'LONG':
                price *= (1 - self.slippage)
            else:
                price *= (1 + self.slippage)
            self._close(pos, price, reason)

    def _exit_logic(self, df, idx, pos, pnl, pnl_peak, peak, trail, sl, hb):
        row = df.iloc[idx]
        lo, hi, cl = row['low'], row['high'], row['close']
        side = pos['side']
        entry = pos['entry_price']
        cfg = self.cfg

        # === PROGRESSIVE TRAILING ===
        trail_dist = cfg['trail_base_dist']
        for threshold, dist in sorted(cfg['progressive_trail'].items(), reverse=True):
            if pnl_peak >= threshold:
                trail_dist = dist
                break

        if pnl_peak >= cfg['trail_activation']:
            if side == 'LONG':
                ts = peak * (1 - trail_dist)
                if ts > trail: trail = ts; pos['trail'] = trail
                if trail > 0 and lo <= trail:
                    return (trail, 'TRAILING')
            else:
                ts = peak * (1 + trail_dist)
                if trail == 0 or ts < trail: trail = ts; pos['trail'] = trail
                if trail > 0 and hi >= trail:
                    return (trail, 'TRAILING')

        # === BREAKEVEN ===
        if pnl_peak >= cfg['be_trigger'] and not pos.get('be_moved'):
            if side == 'LONG' and sl < entry:
                pos['sl'] = entry * 1.0001; pos['be_moved'] = True
            elif side == 'SHORT' and sl > entry:
                pos['sl'] = entry * 0.9999; pos['be_moved'] = True

        # === REVERSAL EXIT (only if profitable) ===
        if idx >= 2 and pnl > 0.003:
            prev = df.iloc[idx - 1]
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

        # === SMART EARLY EXIT (momentum-based) ===
        # Phase 1: Very early + strong momentum against
        if hb >= cfg['smart_cut_1_bars'] and pnl < cfg['smart_cut_1_loss']:
            mom = self._momentum_score(df, idx, side)
            if mom <= cfg['smart_cut_1_mom']:
                return (cl, 'SMART_CUT')

        # Phase 2: Medium timing + moderate momentum against
        if hb >= cfg['smart_cut_2_bars'] and pnl < cfg['smart_cut_2_loss']:
            mom = self._momentum_score(df, idx, side)
            if mom <= cfg['smart_cut_2_mom']:
                return (cl, 'SMART_CUT_MID')

        # Phase 3: Late timing, cut regardless
        if hb >= cfg['smart_cut_3_bars'] and pnl < cfg['smart_cut_3_loss']:
            return (cl, 'SMART_CUT_LATE')

        # === STAGNANT ===
        if hb >= cfg['stagnant_bars'] and abs(pnl) < cfg['stagnant_thresh']:
            return (cl, 'STAGNANT')

        # === MAX HOLD ===
        if hb >= cfg['max_hold']:
            return (cl, 'MAX_HOLD')

        return None

    def _momentum_score(self, df, idx, side):
        if idx < 3: return 0
        row = df.iloc[idx]
        prev = df.iloc[idx - 1]
        score = 0
        rsi = row.get('rsi', 50); prev_rsi = prev.get('rsi', 50)
        macd_h = row.get('macd_h', 0); prev_mh = prev.get('macd_h', 0)
        st_dir = row.get('st_dir', 0)

        if side == 'LONG':
            if not pd.isna(rsi) and not pd.isna(prev_rsi):
                if rsi > prev_rsi: score += 1
                elif rsi < prev_rsi - 3: score -= 1
                if rsi < 35: score -= 1
                if rsi > 55: score += 1
            if not pd.isna(macd_h) and not pd.isna(prev_mh):
                if macd_h > prev_mh: score += 1
                elif macd_h < prev_mh: score -= 1
                if macd_h > 0: score += 1
                elif macd_h < 0: score -= 1
            if not pd.isna(st_dir):
                score += 1 if st_dir == 1 else -1
            ema8 = row.get('ema8', 0)
            if not pd.isna(ema8) and ema8 > 0:
                score += 1 if row['close'] > ema8 else -1
        else:
            if not pd.isna(rsi) and not pd.isna(prev_rsi):
                if rsi < prev_rsi: score += 1
                elif rsi > prev_rsi + 3: score -= 1
                if rsi > 65: score -= 1
                if rsi < 45: score += 1
            if not pd.isna(macd_h) and not pd.isna(prev_mh):
                if macd_h < prev_mh: score += 1
                elif macd_h > prev_mh: score -= 1
                if macd_h < 0: score += 1
                elif macd_h > 0: score -= 1
            if not pd.isna(st_dir):
                score += 1 if st_dir == -1 else -1
            ema8 = row.get('ema8', 0)
            if not pd.isna(ema8) and ema8 > 0:
                score += 1 if row['close'] < ema8 else -1
        return score

    def _close(self, pos, ep, reason):
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
            'pnl_pct': round(pnl_pct * 100, 4), 'pnl_dollar': round(net, 4),
            'hold_hours': pos['hold_bars'], 'exit_reason': reason,
            'strategy': pos['strategy'], 'score': pos['score'],
            'is_win': net > 0,
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
            'win_rate': round(len(wins)/len(trades)*100, 1),
            'profit_factor': round(gp/gl, 2),
            'total_pnl': round(sum(t['pnl_dollar'] for t in trades), 2),
            'trades': trades,
        }

    def reset(self):
        self.balance = self.initial_balance
        self.open_positions = []
        self.closed_trades = []


def run_optimization():
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
        'AVAXUSDT', 'NEARUSDT', 'SUIUSDT', 'ARBUSDT', 'APTUSDT',
        'INJUSDT', 'LINKUSDT',
    ]

    print(f"\n{'='*70}")
    print(f"  Fetching 60-day data...")
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
    all_results = {}

    for config_name, exit_cfg in EXIT_CONFIGS.items():
        print(f"\n{'='*70}")
        print(f"  🔬 {config_name}")
        print(f"{'='*70}")

        all_trades = []
        per_symbol = {}
        for sym, df in data.items():
            bt = OptimizedBacktester(engine, exit_cfg)
            r = bt.run(sym, df)
            if r.get('trades'):
                all_trades.extend(r['trades'])
            per_symbol[sym] = {
                'trades': r.get('total_trades', 0),
                'wr': r.get('win_rate', 0),
                'pf': r.get('profit_factor', 0),
                'pnl': r.get('total_pnl', 0),
            }
            s = "✅" if r.get('total_pnl', 0) > 0 else "❌"
            print(f"  {s} {sym:12s} | N:{r.get('total_trades',0):3d} | "
                  f"WR:{r.get('win_rate',0):5.1f}% | PF:{r.get('profit_factor',0):5.2f} | "
                  f"PnL:${r.get('total_pnl',0):+8.2f}")

        agg = _agg(all_trades)
        agg['per_symbol'] = per_symbol
        agg['profitable_symbols'] = sum(1 for v in per_symbol.values() if v['pnl'] > 0)
        all_results[config_name] = agg

        # Short summary
        print(f"\n  → WR:{agg['wr']:.1f}% | PF:{agg['pf']:.2f} | N:{agg['n']} | "
              f"PnL:${agg['pnl']:+.2f} | R:R={agg['rr']:.2f} | "
              f"Profitable:{agg['profitable_symbols']}/12")

    # Final comparison
    print(f"\n{'='*70}")
    print(f"  📊 FINAL OPTIMIZATION COMPARISON")
    print(f"{'='*70}")
    print(f"  {'Config':28s} | {'WR':>6s} | {'PF':>5s} | {'N':>5s} | {'PnL':>9s} | {'AvgW':>7s} | {'AvgL':>7s} | {'R:R':>5s} | {'Win$':>4s}")
    print(f"  {'-'*28}-+-{'-'*6}-+-{'-'*5}-+-{'-'*5}-+-{'-'*9}-+-{'-'*7}-+-{'-'*7}-+-{'-'*5}-+-{'-'*4}")
    for name, r in all_results.items():
        pf_marker = "🎯" if r['pf'] >= 2.0 else ("📈" if r['pf'] >= 1.5 else "  ")
        print(f"{pf_marker}{name:28s} | {r['wr']:5.1f}% | {r['pf']:5.2f} | {r['n']:5d} | "
              f"${r['pnl']:+8.2f} | {r['aw']:+6.3f}% | {r['al']:+6.3f}% | {r['rr']:5.2f} | {r['profitable_symbols']:2d}/12")

    # Save best result details
    best = max(all_results.items(), key=lambda x: x[1]['pf'])
    print(f"\n  🏆 BEST: {best[0]} (PF={best[1]['pf']:.2f})")

    out = os.path.join(PROJECT_ROOT, 'tests', 'backtest_results')
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'optimization_results.json'), 'w') as f:
        json.dump({k: {kk: vv for kk, vv in v.items() if kk not in ('trades', 'exits', 'strats')}
                   for k, v in all_results.items()}, f, indent=2, default=str)

    return all_results


def _agg(trades):
    if not trades:
        return {'n': 0, 'wr': 0, 'pf': 0, 'pnl': 0, 'aw': 0, 'al': 0, 'rr': 0}
    wins = [t for t in trades if t['is_win']]
    losses = [t for t in trades if not t['is_win']]
    gp = sum(t['pnl_dollar'] for t in wins) if wins else 0
    gl = abs(sum(t['pnl_dollar'] for t in losses)) if losses else 0.001
    pnl = sum(t['pnl_dollar'] for t in trades)
    aw = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
    al = np.mean([t['pnl_pct'] for t in losses]) if losses else 0
    rr = abs(aw / al) if al != 0 else 0

    exits = defaultdict(lambda: {'n': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        r = t['exit_reason']
        exits[r]['n'] += 1; exits[r]['pnl'] += t['pnl_dollar']
        if t['is_win']: exits[r]['wins'] += 1

    strats = defaultdict(lambda: {'n': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        s = t['strategy']
        strats[s]['n'] += 1; strats[s]['pnl'] += t['pnl_dollar']
        if t['is_win']: strats[s]['wins'] += 1

    return {
        'n': len(trades), 'wr': round(len(wins)/len(trades)*100, 1),
        'pf': round(gp/gl, 2), 'pnl': round(pnl, 2),
        'aw': round(aw, 3), 'al': round(al, 3), 'rr': round(rr, 2),
        'gp': round(gp, 2), 'gl': round(gl, 2),
        'exits': {k: dict(v) for k, v in exits.items()},
        'strats': {k: dict(v) for k, v in strats.items()},
    }


if __name__ == '__main__':
    print("="*70)
    print("  V8.5+ FINAL OPTIMIZATION — 6 Exit Variants | 12 Symbols | 60 Days")
    print("="*70)
    run_optimization()
