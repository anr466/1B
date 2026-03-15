#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 PRODUCTION VALIDATION — Final backtest using the actual production engine.
Confirms PF, WR, R:R match development results before going live.
"""

import sys, os, json, time, logging
import requests, pandas as pd, numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from backend.strategies.scalping_v8_engine import ScalpingV8Engine, V8_CONFIG
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


class ProductionBacktester:
    """Uses the actual production engine classes for validation."""

    def __init__(self, engine, initial_balance=1000.0):
        self.engine = engine
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
                    ep = bar['open']
                    if sig['side'] == 'LONG': ep *= (1 + self.slippage)
                    else: ep *= (1 - self.slippage)
                    self._open(symbol, sig, ep, bar.get('timestamp', i), i)

        for pos in list(self.open_positions):
            self._close(pos, df_p.iloc[-1]['close'], 'END_OF_DATA')
        return self._report(symbol)

    def _open(self, symbol, sig, ep, time_val, idx):
        val = min(60.0, self.balance * 0.10)
        if val < 10: return
        comm = val * self.commission
        self.balance -= comm
        sl = sig.get('stop_loss', 0)
        if sl <= 0:
            sl = ep * (1 - 0.008) if sig['side'] == 'LONG' else ep * (1 + 0.008)
        self.open_positions.append({
            'symbol': symbol, 'side': sig['side'],
            'entry_price': ep, 'value': val, 'sl': sl,
            'trail': 0, 'peak': ep,
            'entry_time': time_val, 'entry_bar': idx,
            'entry_comm': comm, 'strategy': sig.get('strategy', ''),
            'score': sig.get('score', 0), 'hold_bars': 0,
        })

    def _check_exits(self, df, idx):
        to_close = []
        for pos in self.open_positions:
            pos['hold_bars'] += 1
            pos_data = {
                'entry_price': pos['entry_price'], 'side': pos['side'],
                'peak': pos['peak'], 'trail': pos['trail'],
                'sl': pos['sl'], 'hold_hours': pos['hold_bars'],
            }
            df_slice = df.iloc[:idx + 1]
            result = self.engine.check_exit_signal(df_slice, pos_data)

            if result.get('should_exit', False):
                ep = result.get('exit_price', df.iloc[idx]['close'])
                if pos['side'] == 'LONG': ep *= (1 - self.slippage)
                else: ep *= (1 + self.slippage)
                to_close.append((pos, ep, result.get('reason', 'UNKNOWN')))
            else:
                upd = result.get('updated', {})
                if 'peak' in upd: pos['peak'] = upd['peak']
                if 'trail' in upd: pos['trail'] = upd['trail']
                if 'sl' in upd: pos['sl'] = upd['sl']

        for pos, ep, reason in to_close:
            self._close(pos, ep, reason)

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
            'strategy': pos['strategy'], 'is_win': net > 0,
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


def run_validation():
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
        'AVAXUSDT', 'NEARUSDT', 'SUIUSDT', 'ARBUSDT', 'APTUSDT',
        'INJUSDT', 'LINKUSDT', 'PEPEUSDT', 'OPUSDT',
    ]

    print(f"\n{'='*70}")
    print(f"  📥 Fetching 60-day data for {len(symbols)} symbols...")
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

    results = {}

    # ===== V7.1 BASELINE =====
    print(f"\n{'='*70}")
    print(f"  🔬 V7.1 BASELINE (ScalpingV7Engine)")
    print(f"{'='*70}")
    v7 = ScalpingV7Engine(V7_CONFIG)
    v7_trades = []
    for sym, df in data.items():
        bt = ProductionBacktester(v7)
        r = bt.run(sym, df)
        if r.get('trades'): v7_trades.extend(r['trades'])
        s = "✅" if r.get('total_pnl', 0) > 0 else "❌"
        print(f"  {s} {sym:12s} | N:{r.get('total_trades',0):3d} | "
              f"WR:{r.get('win_rate',0):5.1f}% | PF:{r.get('profit_factor',0):5.2f} | "
              f"PnL:${r.get('total_pnl',0):+8.2f}")
    results['V7.1_BASELINE'] = _agg(v7_trades, 'V7.1 BASELINE')

    # ===== V8 PRODUCTION =====
    print(f"\n{'='*70}")
    print(f"  🚀 V8 PRODUCTION (ScalpingV8Engine)")
    print(f"{'='*70}")
    v8 = ScalpingV8Engine()
    v8_trades = []
    for sym, df in data.items():
        bt = ProductionBacktester(v8)
        r = bt.run(sym, df)
        if r.get('trades'): v8_trades.extend(r['trades'])
        s = "✅" if r.get('total_pnl', 0) > 0 else "❌"
        print(f"  {s} {sym:12s} | N:{r.get('total_trades',0):3d} | "
              f"WR:{r.get('win_rate',0):5.1f}% | PF:{r.get('profit_factor',0):5.2f} | "
              f"PnL:${r.get('total_pnl',0):+8.2f}")
    results['V8_PRODUCTION'] = _agg(v8_trades, 'V8 PRODUCTION')

    # ===== V8 AGGRESSIVE MODE =====
    print(f"\n{'='*70}")
    print(f"  🔥 V8 AGGRESSIVE MODE")
    print(f"{'='*70}")
    v8a = ScalpingV8Engine(mode='aggressive')
    v8a_trades = []
    for sym, df in data.items():
        bt = ProductionBacktester(v8a)
        r = bt.run(sym, df)
        if r.get('trades'): v8a_trades.extend(r['trades'])
        s = "✅" if r.get('total_pnl', 0) > 0 else "❌"
        print(f"  {s} {sym:12s} | N:{r.get('total_trades',0):3d} | "
              f"WR:{r.get('win_rate',0):5.1f}% | PF:{r.get('profit_factor',0):5.2f} | "
              f"PnL:${r.get('total_pnl',0):+8.2f}")
    results['V8_AGGRESSIVE'] = _agg(v8a_trades, 'V8 AGGRESSIVE')

    # ===== V8 CONSERVATIVE MODE =====
    print(f"\n{'='*70}")
    print(f"  🛡️ V8 CONSERVATIVE MODE")
    print(f"{'='*70}")
    v8c = ScalpingV8Engine(mode='conservative')
    v8c_trades = []
    for sym, df in data.items():
        bt = ProductionBacktester(v8c)
        r = bt.run(sym, df)
        if r.get('trades'): v8c_trades.extend(r['trades'])
        s = "✅" if r.get('total_pnl', 0) > 0 else "❌"
        print(f"  {s} {sym:12s} | N:{r.get('total_trades',0):3d} | "
              f"WR:{r.get('win_rate',0):5.1f}% | PF:{r.get('profit_factor',0):5.2f} | "
              f"PnL:${r.get('total_pnl',0):+8.2f}")
    results['V8_CONSERVATIVE'] = _agg(v8c_trades, 'V8 CONSERVATIVE')

    # ===== FINAL COMPARISON =====
    print(f"\n{'='*70}")
    print(f"  📊 PRODUCTION VALIDATION — FINAL RESULTS")
    print(f"{'='*70}")
    print(f"  {'System':22s} | {'WR':>6s} | {'PF':>5s} | {'N':>5s} | {'PnL':>10s} | {'AvgW':>7s} | {'AvgL':>7s} | {'R:R':>5s} | {'Sym+':>4s}")
    print(f"  {'-'*22}-+-{'-'*6}-+-{'-'*5}-+-{'-'*5}-+-{'-'*10}-+-{'-'*7}-+-{'-'*7}-+-{'-'*5}-+-{'-'*4}")
    for name, r in results.items():
        wr, pf = r['wr'], r['pf']
        nt, pnl = r['n'], r['pnl']
        aw, al = r['aw'], r['al']
        rr = abs(aw / al) if al != 0 else 0
        sym_ok = r.get('sym_ok', 0)
        marker = "🎯" if pf >= 2.0 else ("📈" if pf >= 1.5 else "  ")
        print(f"{marker}{name:22s} | {wr:5.1f}% | {pf:5.2f} | {nt:5d} | ${pnl:+9.2f} | "
              f"{aw:+6.3f}% | {al:+6.3f}% | {rr:5.2f} | {sym_ok:2d}/14")

    # Save
    out = os.path.join(PROJECT_ROOT, 'tests', 'backtest_results')
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'production_validation.json'), 'w') as f:
        json.dump({k: {kk: vv for kk, vv in v.items() if kk != 'trades'}
                   for k, v in results.items()}, f, indent=2, default=str)

    print(f"\n  📁 Results saved to {out}/production_validation.json")
    return results


def _agg(trades, label):
    if not trades:
        return {'n': 0, 'wr': 0, 'pf': 0, 'pnl': 0, 'aw': 0, 'al': 0, 'sym_ok': 0}
    wins = [t for t in trades if t['is_win']]
    losses = [t for t in trades if not t['is_win']]
    gp = sum(t['pnl_dollar'] for t in wins) if wins else 0
    gl = abs(sum(t['pnl_dollar'] for t in losses)) if losses else 0.001
    pnl = sum(t['pnl_dollar'] for t in trades)
    aw = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
    al = np.mean([t['pnl_pct'] for t in losses]) if losses else 0
    rr = abs(aw / al) if al != 0 else 0

    # Per-symbol profitability
    sym_pnl = defaultdict(float)
    for t in trades: sym_pnl[t['symbol']] += t['pnl_dollar']
    sym_ok = sum(1 for v in sym_pnl.values() if v > 0)

    # Exit breakdown
    exits = defaultdict(lambda: {'n': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        r = t['exit_reason']
        exits[r]['n'] += 1; exits[r]['pnl'] += t['pnl_dollar']
        if t['is_win']: exits[r]['wins'] += 1

    # Strategy breakdown
    strats = defaultdict(lambda: {'n': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        s = t['strategy']
        strats[s]['n'] += 1; strats[s]['pnl'] += t['pnl_dollar']
        if t['is_win']: strats[s]['wins'] += 1

    print(f"\n  📊 {label}:")
    print(f"  Trades:{len(trades)} | WR:{len(wins)/len(trades)*100:.1f}% | PF:{gp/gl:.2f} | "
          f"PnL:${pnl:+.2f} | R:R={rr:.2f} | Profitable:{sym_ok}/14")

    print(f"  Exit Reasons:")
    for r, d in sorted(exits.items(), key=lambda x: x[1]['n'], reverse=True):
        wr = d['wins']/max(d['n'],1)*100
        print(f"    {r:18s} | N:{d['n']:4d} | WR:{wr:5.1f}% | PnL:${d['pnl']:+8.2f}")

    print(f"  Strategies:")
    for s, d in sorted(strats.items(), key=lambda x: x[1]['pnl'], reverse=True):
        wr = d['wins']/max(d['n'],1)*100
        print(f"    {s:22s} | N:{d['n']:4d} | WR:{wr:5.1f}% | PnL:${d['pnl']:+8.2f}")

    return {
        'n': len(trades), 'wr': round(len(wins)/len(trades)*100, 1),
        'pf': round(gp/gl, 2), 'pnl': round(pnl, 2),
        'aw': round(aw, 3), 'al': round(al, 3), 'rr': round(rr, 2),
        'sym_ok': sym_ok,
        'exits': {k: dict(v) for k, v in exits.items()},
        'strats': {k: dict(v) for k, v in strats.items()},
        'trades': trades,
    }


if __name__ == '__main__':
    print("="*70)
    print("  🚀 V8 PRODUCTION VALIDATION")
    print("  ScalpingV8Engine vs V7 Baseline | 4 modes | 14 Symbols | 60 Days")
    print("="*70)
    run_validation()
