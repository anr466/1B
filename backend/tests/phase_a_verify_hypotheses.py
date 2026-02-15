#!/usr/bin/env python3
"""
Phase A: Verify Root Cause Hypotheses
======================================
يختبر 3 فرضيات بشكل مستقل لقياس تأثير كل واحدة قبل تعديل الكود.

A1: حظر التداول في NEUTRAL trend
A2: رفع min_confluence من 4 إلى 5
A3: تعطيل الأنماط الخاسرة (macd_x, st_flip, breakout LONG)

كل اختبار يقارن: BASELINE vs MODIFIED
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import logging
import copy
import urllib.request
import json

logging.basicConfig(level=logging.WARNING)

from backend.strategies.scalping_v7_engine import ScalpingV7Engine, V7_CONFIG

# ============================================================
# DATA
# ============================================================
def fetch_binance_klines(symbol, interval='1h', limit=1000):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        print(f"  ❌ {symbol}: {e}")
        return None

# ============================================================
# MINI BACKTESTER (streamlined for hypothesis testing)
# ============================================================
class MiniBT:
    def __init__(self, engine, label=""):
        self.engine = engine
        self.label = label
        self.balance = 10000.0
        self.initial = 10000.0
        self.positions = []
        self.trades = []
        self.peak_bal = 10000.0
        self.max_dd = 0
        self.pos_size = 600  # fixed $600 per trade (6% of 10k)
        self.max_pos = 5
        self.comm = 0.001
        self.slip = 0.0005
        # Filters (configurable per hypothesis)
        self.block_neutral_long = False
        self.min_confluence_override = None
        self.blocked_patterns_long = set()
        self.blocked_patterns_short = set()
    
    def run(self, all_data):
        min_len = min(len(df) for df in all_data.values())
        for i in range(60, min_len):
            self._manage(all_data, i)
            if len(self.positions) < self.max_pos:
                self._scan(all_data, i)
            self._track(all_data, i)
        self._close_all(all_data, min_len - 1)
    
    def _manage(self, all_data, idx):
        closed = []
        for pos in self.positions:
            df = all_data[pos['symbol']]
            if idx >= len(df):
                continue
            
            hold_h = idx - pos['bar']
            pos_data = {
                'entry_price': pos['entry'], 'side': pos['side'],
                'peak': pos['peak'], 'trail': pos['trail'],
                'sl': pos['sl'], 'hold_hours': hold_h,
            }
            df_slice = df.iloc[:idx + 1]
            result = self.engine.check_exit_signal(df_slice, pos_data)
            
            upd = result.get('updated', {})
            if 'peak' in upd: pos['peak'] = upd['peak']
            if 'trail' in upd: pos['trail'] = upd['trail']
            
            if result['should_exit']:
                ep = result['exit_price']
                if pos['side'] == 'LONG': ep *= (1 - self.slip)
                else: ep *= (1 + self.slip)
                
                if pos['side'] == 'LONG':
                    pnl_raw = (ep - pos['entry']) * pos['qty']
                else:
                    pnl_raw = (pos['entry'] - ep) * pos['qty']
                
                exit_comm = abs(ep * pos['qty']) * self.comm
                pnl = pnl_raw - exit_comm
                self.balance += pos['size'] + pnl
                
                self.trades.append({
                    'symbol': pos['symbol'], 'side': pos['side'],
                    'pnl': pnl, 'pnl_pct': pnl / pos['size'] * 100,
                    'reason': result['reason'], 'trend': pos['trend'],
                    'strategy': pos.get('strategy', ''), 'hold': hold_h,
                })
                closed.append(pos)
        
        for p in closed:
            self.positions.remove(p)
    
    def _scan(self, all_data, idx):
        for sym, df in all_data.items():
            if len(self.positions) >= self.max_pos:
                break
            if any(p['symbol'] == sym for p in self.positions):
                continue
            if idx >= len(df) - 1:
                continue
            
            trend = self.engine.get_4h_trend(df, idx - 1)
            
            # === HYPOTHESIS FILTERS ===
            # A1: Block NEUTRAL LONG
            if self.block_neutral_long and trend == 'NEUTRAL':
                continue
            
            signal = self.engine.detect_entry(df, trend, idx - 1)
            if not signal:
                continue
            
            # A2: Min confluence override
            if self.min_confluence_override and signal.get('score', 0) < self.min_confluence_override:
                continue
            
            # A3: Block specific patterns
            strat = signal.get('strategy', '')
            if signal['side'] == 'LONG' and strat in self.blocked_patterns_long:
                continue
            if signal['side'] == 'SHORT' and strat in self.blocked_patterns_short:
                continue
            
            # Execute at next bar open
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
            comm = self.pos_size * self.comm
            self.balance -= (self.pos_size + comm)
            
            self.positions.append({
                'symbol': sym, 'side': signal['side'],
                'entry': entry_price, 'qty': qty, 'size': self.pos_size,
                'sl': sl, 'peak': entry_price, 'trail': 0, 'bar': idx,
                'trend': trend, 'strategy': signal.get('strategy', ''),
            })
    
    def _track(self, all_data, idx):
        unrealized = 0
        for p in self.positions:
            df = all_data[p['symbol']]
            if idx < len(df):
                c = df.iloc[idx]['close']
                if p['side'] == 'LONG':
                    unrealized += (c - p['entry']) * p['qty']
                else:
                    unrealized += (p['entry'] - c) * p['qty']
        
        eq = self.balance + sum(p['size'] for p in self.positions) + unrealized
        if eq > self.peak_bal: self.peak_bal = eq
        dd = (self.peak_bal - eq) / self.peak_bal if self.peak_bal > 0 else 0
        if dd > self.max_dd: self.max_dd = dd
    
    def _close_all(self, all_data, idx):
        for pos in list(self.positions):
            df = all_data[pos['symbol']]
            if idx < len(df):
                ep = df.iloc[idx]['close']
                if pos['side'] == 'LONG':
                    pnl = (ep - pos['entry']) * pos['qty'] - abs(ep * pos['qty']) * self.comm
                else:
                    pnl = (pos['entry'] - ep) * pos['qty'] - abs(ep * pos['qty']) * self.comm
                self.balance += pos['size'] + pnl
                self.trades.append({
                    'symbol': pos['symbol'], 'side': pos['side'],
                    'pnl': pnl, 'pnl_pct': pnl / pos['size'] * 100,
                    'reason': 'FORCE_CLOSE', 'trend': pos['trend'],
                    'strategy': pos.get('strategy', ''), 'hold': idx - pos['bar'],
                })
        self.positions.clear()
    
    def summary(self):
        if not self.trades:
            return {'trades': 0}
        df = pd.DataFrame(self.trades)
        winners = df[df['pnl'] > 0]
        losers = df[df['pnl'] <= 0]
        gp = winners['pnl'].sum() if len(winners) > 0 else 0
        gl = abs(losers['pnl'].sum()) if len(losers) > 0 else 0
        return {
            'trades': len(df),
            'wr': len(winners) / len(df) * 100,
            'pf': gp / gl if gl > 0 else float('inf'),
            'pnl': df['pnl'].sum(),
            'pnl_pct': df['pnl'].sum() / self.initial * 100,
            'dd': self.max_dd * 100,
            'avg_pnl': df['pnl_pct'].mean(),
            'avg_win': winners['pnl_pct'].mean() if len(winners) > 0 else 0,
            'avg_loss': losers['pnl_pct'].mean() if len(losers) > 0 else 0,
            'long_wr': len(df[(df['side']=='LONG') & (df['pnl']>0)]) / max(len(df[df['side']=='LONG']), 1) * 100,
            'short_wr': len(df[(df['side']=='SHORT') & (df['pnl']>0)]) / max(len(df[df['side']=='SHORT']), 1) * 100,
            'sl_rate': len(df[df['reason']=='STOP_LOSS']) / len(df) * 100,
            'trail_rate': len(df[df['reason']=='TRAILING']) / len(df) * 100,
        }


def print_comparison(label, baseline, modified):
    """Print side-by-side comparison"""
    b = baseline
    m = modified
    
    def delta(val_b, val_m, fmt="+.2f", better_higher=True):
        d = val_m - val_b
        arrow = "↑" if (d > 0) == better_higher else "↓"
        color = "🟢" if (d > 0) == better_higher else "🔴"
        if abs(d) < 0.01: color = "⚪"
        return f"{color} {d:{fmt}} {arrow}"
    
    print(f"\n{'='*65}")
    print(f"  {label}")
    print(f"{'='*65}")
    print(f"  {'Metric':<20} {'BASELINE':>12} {'MODIFIED':>12} {'DELTA':>18}")
    print(f"  {'-'*62}")
    print(f"  {'Trades':<20} {b['trades']:>12} {m['trades']:>12} {delta(b['trades'], m['trades'], '+d', False):>18}")
    print(f"  {'Win Rate %':<20} {b['wr']:>11.1f}% {m['wr']:>11.1f}% {delta(b['wr'], m['wr']):>18}")
    print(f"  {'Profit Factor':<20} {b['pf']:>12.2f} {m['pf']:>12.2f} {delta(b['pf'], m['pf']):>18}")
    print(f"  {'Total PnL $':<20} {b['pnl']:>+11.2f} {m['pnl']:>+11.2f} {delta(b['pnl'], m['pnl']):>18}")
    print(f"  {'PnL %':<20} {b['pnl_pct']:>+11.2f}% {m['pnl_pct']:>+11.2f}% {delta(b['pnl_pct'], m['pnl_pct']):>18}")
    print(f"  {'Max DD %':<20} {b['dd']:>11.2f}% {m['dd']:>11.2f}% {delta(b['dd'], m['dd'], '+.2f', False):>18}")
    print(f"  {'Avg Trade %':<20} {b['avg_pnl']:>+11.3f}% {m['avg_pnl']:>+11.3f}% {delta(b['avg_pnl'], m['avg_pnl'], '+.3f'):>18}")
    print(f"  {'LONG WR %':<20} {b['long_wr']:>11.1f}% {m['long_wr']:>11.1f}% {delta(b['long_wr'], m['long_wr']):>18}")
    print(f"  {'SHORT WR %':<20} {b['short_wr']:>11.1f}% {m['short_wr']:>11.1f}% {delta(b['short_wr'], m['short_wr']):>18}")
    print(f"  {'SL Rate %':<20} {b['sl_rate']:>11.1f}% {m['sl_rate']:>11.1f}% {delta(b['sl_rate'], m['sl_rate'], '+.1f', False):>18}")
    print(f"  {'Trail Rate %':<20} {b['trail_rate']:>11.1f}% {m['trail_rate']:>11.1f}% {delta(b['trail_rate'], m['trail_rate'], '+.1f'):>18}")


def main():
    symbols = [
        'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT', 'NEARUSDT',
        'SUIUSDT', 'ARBUSDT', 'APTUSDT', 'INJUSDT', 'LINKUSDT',
    ]
    
    print("=" * 65)
    print("🔬 Phase A: Verify Root Cause Hypotheses")
    print("=" * 65)
    
    # Fetch data
    print("\n📥 Fetching data...")
    engine = ScalpingV7Engine()
    all_data = {}
    for sym in symbols:
        df = fetch_binance_klines(sym)
        if df is not None and len(df) >= 100:
            all_data[sym] = engine.prepare_data(df)
            print(f"  ✅ {sym}: {len(df)} bars")
    
    print(f"\n  📊 {len(all_data)} symbols loaded")
    
    # ============================================================
    # BASELINE (no changes)
    # ============================================================
    print("\n🏁 Running BASELINE...")
    bt_base = MiniBT(engine, "BASELINE")
    bt_base.run(all_data)
    base = bt_base.summary()
    print(f"  → {base['trades']} trades | WR={base['wr']:.1f}% | PF={base['pf']:.2f} | PnL=${base['pnl']:+.2f}")
    
    # ============================================================
    # A1: Block NEUTRAL LONG entries
    # ============================================================
    print("\n🧪 A1: Block NEUTRAL trend entries...")
    bt_a1 = MiniBT(engine, "A1: Block NEUTRAL")
    bt_a1.block_neutral_long = True
    bt_a1.run(all_data)
    a1 = bt_a1.summary()
    print_comparison("A1: حظر التداول في NEUTRAL (LONG)", base, a1)
    
    # ============================================================
    # A2: Min confluence = 5 (instead of 4)
    # ============================================================
    print("\n🧪 A2: Min confluence = 5...")
    bt_a2 = MiniBT(engine, "A2: Confluence=5")
    bt_a2.min_confluence_override = 5
    bt_a2.run(all_data)
    a2 = bt_a2.summary()
    print_comparison("A2: رفع min_confluence إلى 5", base, a2)
    
    # ============================================================
    # A3: Block losing patterns for LONG
    # ============================================================
    print("\n🧪 A3: Block losing LONG patterns (macd_x, st_flip, engulf)...")
    bt_a3 = MiniBT(engine, "A3: Block losing")
    bt_a3.blocked_patterns_long = {'macd_x', 'st_flip', 'engulf'}
    bt_a3.run(all_data)
    a3 = bt_a3.summary()
    print_comparison("A3: حظر أنماط LONG الخاسرة (macd_x, st_flip, engulf)", base, a3)
    
    # ============================================================
    # COMBINED: A1 + A2 + A3 together
    # ============================================================
    print("\n🧪 COMBINED: A1 + A2 + A3...")
    bt_all = MiniBT(engine, "ALL COMBINED")
    bt_all.block_neutral_long = True
    bt_all.min_confluence_override = 5
    bt_all.blocked_patterns_long = {'macd_x', 'st_flip', 'engulf'}
    bt_all.run(all_data)
    combined = bt_all.summary()
    print_comparison("مجتمعة: A1 + A2 + A3", base, combined)
    
    # ============================================================
    # VERDICT
    # ============================================================
    print("\n" + "=" * 65)
    print("📋 ملخص نتائج التحقق:")
    print("=" * 65)
    
    tests = [
        ("A1: حظر NEUTRAL", a1, base),
        ("A2: confluence=5", a2, base),
        ("A3: أنماط خاسرة", a3, base),
        ("ALL: مجتمعة", combined, base),
    ]
    
    for name, mod, ref in tests:
        pnl_delta = mod['pnl'] - ref['pnl']
        wr_delta = mod['wr'] - ref['wr']
        pf_delta = mod['pf'] - ref['pf']
        verdict = "✅ تحسين" if pnl_delta > 0 and pf_delta > 0 else "⚠️ مختلط" if pf_delta > 0 else "❌ لا تحسين"
        print(f"  {verdict} {name}: PnL {pnl_delta:+.2f}$ | WR {wr_delta:+.1f}% | PF {pf_delta:+.2f}")
    
    print()
    return base, a1, a2, a3, combined


if __name__ == '__main__':
    main()
