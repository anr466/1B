#!/usr/bin/env python3
"""
Phase B: Smart Exit System Testing
====================================
يختبر 3 تحسينات للخروج بشكل مستقل ثم مجتمعة:

B1: Break-even move — نقل SL إلى نقطة الدخول بعد +0.4%
B2: ATR-adaptive trailing — مسافة trailing ديناميكية حسب التقلب
B3: Progressive trailing — تضييق trailing كلما زاد الربح

+ يطبق A1+A3 (الفلاتر المُثبتة)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
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
# SMART EXIT ENGINE — Enhanced check_exit with B1/B2/B3
# ============================================================
def smart_exit_check(engine, df_slice, pos_data, features=None):
    """
    Enhanced exit logic with configurable smart features.
    
    features dict:
        'breakeven': True/False — move SL to entry after +0.4% profit
        'atr_trailing': True/False — use ATR for dynamic trailing distance
        'progressive': True/False — tighten trailing as profit grows
    """
    if features is None:
        features = {}
    
    if df_slice is None or len(df_slice) < 3:
        return {'should_exit': False, 'reason': 'HOLD'}
    
    idx = len(df_slice) - 1
    row = df_slice.iloc[idx]
    hi = row['high']
    lo = row['low']
    cl = row['close']
    
    entry = pos_data['entry_price']
    side = pos_data.get('side', 'LONG')
    peak = pos_data.get('peak', entry)
    trail = pos_data.get('trail', 0)
    sl = pos_data.get('sl', entry * (1 - V7_CONFIG['sl_pct']) if side == 'LONG'
                       else entry * (1 + V7_CONFIG['sl_pct']))
    hold_hours = pos_data.get('hold_hours', 0)
    
    updated = {}
    
    # ---- B1: BREAK-EVEN MOVE ----
    if features.get('breakeven', False):
        if side == 'LONG':
            current_profit_pct = (hi - entry) / entry
            # If price reached +0.4% at any point, move SL to entry
            if current_profit_pct >= 0.004 and sl < entry:
                sl = entry * 1.0001  # tiny buffer above entry
                updated['sl'] = sl
        else:  # SHORT
            current_profit_pct = (entry - lo) / entry
            if current_profit_pct >= 0.004 and sl > entry:
                sl = entry * 0.9999
                updated['sl'] = sl
    
    # ---- STOP LOSS CHECK ----
    if side == 'LONG':
        if hi > peak:
            peak = hi
            updated['peak'] = peak
        
        if lo <= sl:
            return {
                'should_exit': True,
                'reason': 'STOP_LOSS' if sl < entry * 0.999 else 'BREAK_EVEN',
                'exit_price': sl,
                'updated': updated,
            }
        
        # ---- TRAILING STOP ----
        profit_pct = (peak - entry) / entry
        
        # Determine trailing parameters
        trail_activation = V7_CONFIG['trailing_activation']  # 0.6%
        trail_distance = V7_CONFIG['trailing_distance']      # 0.4%
        
        # B2: ATR-adaptive trailing distance
        if features.get('atr_trailing', False):
            atr_val = row.get('atr', None)
            if atr_val and not pd.isna(atr_val) and cl > 0:
                atr_pct = atr_val / cl
                # Scale trailing distance: min 0.2%, max 0.6%, based on ATR
                trail_distance = max(0.002, min(0.006, atr_pct * 0.5))
        
        # B3: Progressive trailing tightening
        if features.get('progressive', False):
            if profit_pct >= 0.02:        # +2% → very tight
                trail_distance = min(trail_distance, 0.002)
            elif profit_pct >= 0.015:     # +1.5% → tight
                trail_distance = min(trail_distance, 0.003)
            elif profit_pct >= 0.01:      # +1% → tighter
                trail_distance = min(trail_distance, 0.0035)
        
        if profit_pct >= trail_activation:
            ts = peak * (1 - trail_distance)
            if ts > trail:
                trail = ts
                updated['trail'] = trail
            if trail > 0 and lo <= trail:
                return {
                    'should_exit': True,
                    'reason': 'TRAILING',
                    'exit_price': trail,
                    'updated': updated,
                }
    
    else:  # SHORT
        if lo < peak:
            peak = lo
            updated['peak'] = peak
        
        if hi >= sl:
            return {
                'should_exit': True,
                'reason': 'STOP_LOSS' if sl > entry * 1.001 else 'BREAK_EVEN',
                'exit_price': sl,
                'updated': updated,
            }
        
        profit_pct = (entry - peak) / entry
        
        trail_activation = V7_CONFIG['trailing_activation']
        trail_distance = V7_CONFIG['trailing_distance']
        
        # B2: ATR-adaptive
        if features.get('atr_trailing', False):
            atr_val = row.get('atr', None)
            if atr_val and not pd.isna(atr_val) and cl > 0:
                atr_pct = atr_val / cl
                trail_distance = max(0.002, min(0.006, atr_pct * 0.5))
        
        # B3: Progressive
        if features.get('progressive', False):
            if profit_pct >= 0.02:
                trail_distance = min(trail_distance, 0.002)
            elif profit_pct >= 0.015:
                trail_distance = min(trail_distance, 0.003)
            elif profit_pct >= 0.01:
                trail_distance = min(trail_distance, 0.0035)
        
        if profit_pct >= trail_activation:
            ts = peak * (1 + trail_distance)
            if trail == 0 or ts < trail:
                trail = ts
                updated['trail'] = trail
            if trail > 0 and hi >= trail:
                return {
                    'should_exit': True,
                    'reason': 'TRAILING',
                    'exit_price': trail,
                    'updated': updated,
                }
    
    # ---- REVERSAL EXIT (same as V7) ----
    if idx >= 2:
        prev = df_slice.iloc[idx - 1]
        rev_score = 0
        if side == 'LONG':
            pnl = (cl - entry) / entry
            if pnl > 0.003:
                if not pd.isna(row.get('st_dir')) and not pd.isna(prev.get('st_dir')):
                    if prev['st_dir'] == 1 and row['st_dir'] == -1:
                        rev_score += 3
                if (prev.get('bull', True) and not row.get('bull', True) and
                        row['open'] > prev['close'] and cl < prev['open']):
                    rev_score += 2
                if not pd.isna(row.get('macd_l')) and not pd.isna(prev.get('macd_l')):
                    if prev['macd_l'] > prev['macd_s'] and row['macd_l'] < row['macd_s']:
                        rev_score += 2
        else:
            pnl = (entry - cl) / entry
            if pnl > 0.003:
                if not pd.isna(row.get('st_dir')) and not pd.isna(prev.get('st_dir')):
                    if prev['st_dir'] == -1 and row['st_dir'] == 1:
                        rev_score += 3
                if (not prev.get('bull', False) and row.get('bull', False) and
                        row['close'] > prev['open'] and row['open'] < prev['close']):
                    rev_score += 2
                if not pd.isna(row.get('macd_l')) and not pd.isna(prev.get('macd_l')):
                    if prev['macd_l'] < prev['macd_s'] and row['macd_l'] > row['macd_s']:
                        rev_score += 2
        
        if rev_score >= 3:
            return {
                'should_exit': True,
                'reason': 'REVERSAL',
                'exit_price': cl,
                'updated': updated,
            }
    
    # ---- TIME EXITS ----
    if hold_hours >= V7_CONFIG['max_hold_hours']:
        return {
            'should_exit': True,
            'reason': 'MAX_HOLD',
            'exit_price': cl,
            'updated': updated,
        }
    
    pnl_now = ((cl - entry) / entry if side == 'LONG' else (entry - cl) / entry)
    if hold_hours >= 6 and abs(pnl_now) < 0.002:
        return {
            'should_exit': True,
            'reason': 'STAGNANT',
            'exit_price': cl,
            'updated': updated,
        }
    
    return {
        'should_exit': False,
        'reason': 'HOLD',
        'exit_price': cl,
        'updated': updated,
    }


# ============================================================
# BACKTESTER WITH SMART EXITS
# ============================================================
class SmartBT:
    def __init__(self, engine, label="", exit_features=None):
        self.engine = engine
        self.label = label
        self.exit_features = exit_features or {}
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
        # A1+A3 filters (confirmed improvements)
        self.block_neutral = True
        self.blocked_long_patterns = {'macd_x', 'st_flip', 'engulf'}
    
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
            
            # Use smart exit if features enabled, else original V7
            if self.exit_features:
                result = smart_exit_check(self.engine, df_slice, pos_data, self.exit_features)
            else:
                result = self.engine.check_exit_signal(df_slice, pos_data)
            
            upd = result.get('updated', {})
            if 'peak' in upd: pos['peak'] = upd['peak']
            if 'trail' in upd: pos['trail'] = upd['trail']
            if 'sl' in upd: pos['sl'] = upd['sl']
            
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
            
            # A1: Block NEUTRAL
            if self.block_neutral and trend == 'NEUTRAL':
                continue
            
            signal = self.engine.detect_entry(df, trend, idx - 1)
            if not signal:
                continue
            
            # A3: Block losing LONG patterns
            strat = signal.get('strategy', '')
            if signal['side'] == 'LONG' and strat in self.blocked_long_patterns:
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
            return {'trades': 0, 'wr': 0, 'pf': 0, 'pnl': 0, 'pnl_pct': 0,
                    'dd': 0, 'avg_pnl': 0, 'avg_win': 0, 'avg_loss': 0,
                    'long_wr': 0, 'short_wr': 0, 'sl_rate': 0, 'trail_rate': 0,
                    'be_rate': 0}
        df = pd.DataFrame(self.trades)
        w = df[df['pnl'] > 0]
        l = df[df['pnl'] <= 0]
        gp = w['pnl'].sum() if len(w) > 0 else 0
        gl = abs(l['pnl'].sum()) if len(l) > 0 else 0
        
        # Exit reason breakdown
        reasons = df['reason'].value_counts()
        
        return {
            'trades': len(df),
            'wr': len(w) / len(df) * 100,
            'pf': gp / gl if gl > 0 else float('inf'),
            'pnl': df['pnl'].sum(),
            'pnl_pct': df['pnl'].sum() / self.initial * 100,
            'dd': self.max_dd * 100,
            'avg_pnl': df['pnl_pct'].mean(),
            'avg_win': w['pnl_pct'].mean() if len(w) > 0 else 0,
            'avg_loss': l['pnl_pct'].mean() if len(l) > 0 else 0,
            'long_wr': len(df[(df['side']=='LONG') & (df['pnl']>0)]) / max(len(df[df['side']=='LONG']), 1) * 100,
            'short_wr': len(df[(df['side']=='SHORT') & (df['pnl']>0)]) / max(len(df[df['side']=='SHORT']), 1) * 100,
            'sl_rate': reasons.get('STOP_LOSS', 0) / len(df) * 100,
            'trail_rate': reasons.get('TRAILING', 0) / len(df) * 100,
            'be_rate': reasons.get('BREAK_EVEN', 0) / len(df) * 100,
            'reasons': {k: v for k, v in reasons.items()},
        }


def print_comparison(label, baseline, modified):
    b, m = baseline, modified
    
    def delta(vb, vm, fmt="+.2f", better_higher=True):
        d = vm - vb
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
    print(f"  {'Avg Win %':<20} {b['avg_win']:>+11.3f}% {m['avg_win']:>+11.3f}% {delta(b['avg_win'], m['avg_win'], '+.3f'):>18}")
    print(f"  {'Avg Loss %':<20} {b['avg_loss']:>+11.3f}% {m['avg_loss']:>+11.3f}% {delta(b['avg_loss'], m['avg_loss'], '+.3f'):>18}")
    print(f"  {'SL Rate %':<20} {b['sl_rate']:>11.1f}% {m['sl_rate']:>11.1f}% {delta(b['sl_rate'], m['sl_rate'], '+.1f', False):>18}")
    print(f"  {'Trail Rate %':<20} {b['trail_rate']:>11.1f}% {m['trail_rate']:>11.1f}% {delta(b['trail_rate'], m['trail_rate'], '+.1f'):>18}")
    if m.get('be_rate', 0) > 0 or b.get('be_rate', 0) > 0:
        print(f"  {'Break-Even Rate %':<20} {b.get('be_rate',0):>11.1f}% {m.get('be_rate',0):>11.1f}% {delta(b.get('be_rate',0), m.get('be_rate',0), '+.1f'):>18}")
    
    # Show exit reason breakdown
    if 'reasons' in m:
        print(f"\n  Exit Reasons: ", end="")
        for r, c in sorted(m['reasons'].items(), key=lambda x: -x[1]):
            print(f"{r}={c}", end="  ")
        print()


def main():
    symbols = [
        'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT', 'NEARUSDT',
        'SUIUSDT', 'ARBUSDT', 'APTUSDT', 'INJUSDT', 'LINKUSDT',
    ]
    
    print("=" * 65)
    print("🔬 Phase B: Smart Exit System Testing")
    print("  (with A1+A3 entry filters applied)")
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
    
    # ============================================================
    # BASELINE: A1+A3 with original V7 exits
    # ============================================================
    print("\n🏁 Running BASELINE (A1+A3, original V7 exits)...")
    bt_base = SmartBT(engine, "BASELINE")
    bt_base.run(all_data)
    base = bt_base.summary()
    print(f"  → {base['trades']} trades | WR={base['wr']:.1f}% | PF={base['pf']:.2f} | PnL=${base['pnl']:+.2f}")
    
    # ============================================================
    # B1: Break-even only
    # ============================================================
    print("\n🧪 B1: Break-even move after +0.4%...")
    bt_b1 = SmartBT(engine, "B1: Break-even", {'breakeven': True})
    bt_b1.run(all_data)
    b1 = bt_b1.summary()
    print_comparison("B1: نقل SL إلى نقطة الدخول بعد +0.4%", base, b1)
    
    # ============================================================
    # B2: ATR-adaptive trailing only
    # ============================================================
    print("\n🧪 B2: ATR-adaptive trailing distance...")
    bt_b2 = SmartBT(engine, "B2: ATR Trail", {'atr_trailing': True})
    bt_b2.run(all_data)
    b2 = bt_b2.summary()
    print_comparison("B2: مسافة Trailing ديناميكية حسب ATR", base, b2)
    
    # ============================================================
    # B3: Progressive trailing only
    # ============================================================
    print("\n🧪 B3: Progressive trailing tightening...")
    bt_b3 = SmartBT(engine, "B3: Progressive", {'progressive': True})
    bt_b3.run(all_data)
    b3 = bt_b3.summary()
    print_comparison("B3: تضييق Trailing التدريجي", base, b3)
    
    # ============================================================
    # B1+B2: Break-even + ATR trailing
    # ============================================================
    print("\n🧪 B1+B2: Break-even + ATR trailing...")
    bt_b12 = SmartBT(engine, "B1+B2", {'breakeven': True, 'atr_trailing': True})
    bt_b12.run(all_data)
    b12 = bt_b12.summary()
    print_comparison("B1+B2: Break-even + ATR trailing", base, b12)
    
    # ============================================================
    # B1+B3: Break-even + Progressive
    # ============================================================
    print("\n🧪 B1+B3: Break-even + Progressive...")
    bt_b13 = SmartBT(engine, "B1+B3", {'breakeven': True, 'progressive': True})
    bt_b13.run(all_data)
    b13 = bt_b13.summary()
    print_comparison("B1+B3: Break-even + Progressive", base, b13)
    
    # ============================================================
    # ALL: B1+B2+B3
    # ============================================================
    print("\n🧪 ALL B: B1+B2+B3...")
    bt_all = SmartBT(engine, "ALL B", {'breakeven': True, 'atr_trailing': True, 'progressive': True})
    bt_all.run(all_data)
    ball = bt_all.summary()
    print_comparison("ALL B: Break-even + ATR + Progressive", base, ball)
    
    # ============================================================
    # VERDICT
    # ============================================================
    print("\n" + "=" * 65)
    print("📋 ملخص نتائج Phase B:")
    print("=" * 65)
    
    tests = [
        ("B1: Break-even", b1),
        ("B2: ATR trailing", b2),
        ("B3: Progressive", b3),
        ("B1+B2", b12),
        ("B1+B3", b13),
        ("ALL B1+B2+B3", ball),
    ]
    
    for name, mod in tests:
        pnl_d = mod['pnl'] - base['pnl']
        pf_d = mod['pf'] - base['pf']
        wr_d = mod['wr'] - base['wr']
        verdict = "✅" if pnl_d > 0 and pf_d > 0 else "⚠️" if pf_d > 0 else "❌"
        print(f"  {verdict} {name:<20}: PnL {pnl_d:+.2f}$ | WR {wr_d:+.1f}% | PF {pf_d:+.2f}")
    
    # Best combination
    best_name, best_mod = max(tests, key=lambda x: x[1]['pnl'])
    print(f"\n  🏆 Best: {best_name} → PnL=${best_mod['pnl']:+.2f} | WR={best_mod['wr']:.1f}% | PF={best_mod['pf']:.2f}")
    
    return base, b1, b2, b3, b12, b13, ball


if __name__ == '__main__':
    main()
