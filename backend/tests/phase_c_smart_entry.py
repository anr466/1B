#!/usr/bin/env python3
"""
Phase C: Smart Entry Per Coin State
=====================================
يختبر فلاتر دخول ذكية حسب حالة كل عملة:

C1: ADX filter — فقط تداول في أسواق متجهة (ADX > 20)
C2: SuperTrend alignment — تأكيد أن SuperTrend يوافق اتجاه الدخول
C3: Volume spike — رفض الدخول إذا الحجم أقل من المتوسط
C4: Momentum confirmation — RSI يتحرك في اتجاه الصفقة
C5: BB width filter — رفض الأسواق الراكدة (BB ضيق جداً)

يطبق A1+A3+B3 (التحسينات المُثبتة سابقاً)
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
from typing import Dict
import logging
import urllib.request
import json

logging.basicConfig(level=logging.WARNING)

from backend.strategies.scalping_v7_engine import ScalpingV7Engine, V7_CONFIG

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
# Progressive trailing exit (B3 — confirmed improvement)
# ============================================================
def b3_exit_check(engine, df_slice, pos_data):
    """V7 exit + progressive trailing tightening (B3)"""
    if df_slice is None or len(df_slice) < 3:
        return {'should_exit': False, 'reason': 'HOLD'}
    
    idx = len(df_slice) - 1
    row = df_slice.iloc[idx]
    hi, lo, cl = row['high'], row['low'], row['close']
    
    entry = pos_data['entry_price']
    side = pos_data.get('side', 'LONG')
    peak = pos_data.get('peak', entry)
    trail = pos_data.get('trail', 0)
    sl = pos_data.get('sl', entry * (1 - V7_CONFIG['sl_pct']) if side == 'LONG'
                       else entry * (1 + V7_CONFIG['sl_pct']))
    hold_hours = pos_data.get('hold_hours', 0)
    updated = {}
    
    if side == 'LONG':
        if hi > peak:
            peak = hi
            updated['peak'] = peak
        if lo <= sl:
            return {'should_exit': True, 'reason': 'STOP_LOSS', 'exit_price': sl, 'updated': updated}
        
        profit_pct = (peak - entry) / entry
        trail_dist = V7_CONFIG['trailing_distance']
        
        # B3: Progressive tightening
        if profit_pct >= 0.02:
            trail_dist = min(trail_dist, 0.002)
        elif profit_pct >= 0.015:
            trail_dist = min(trail_dist, 0.003)
        elif profit_pct >= 0.01:
            trail_dist = min(trail_dist, 0.0035)
        
        if profit_pct >= V7_CONFIG['trailing_activation']:
            ts = peak * (1 - trail_dist)
            if ts > trail:
                trail = ts
                updated['trail'] = trail
            if trail > 0 and lo <= trail:
                return {'should_exit': True, 'reason': 'TRAILING', 'exit_price': trail, 'updated': updated}
    else:
        if lo < peak:
            peak = lo
            updated['peak'] = peak
        if hi >= sl:
            return {'should_exit': True, 'reason': 'STOP_LOSS', 'exit_price': sl, 'updated': updated}
        
        profit_pct = (entry - peak) / entry
        trail_dist = V7_CONFIG['trailing_distance']
        
        if profit_pct >= 0.02:
            trail_dist = min(trail_dist, 0.002)
        elif profit_pct >= 0.015:
            trail_dist = min(trail_dist, 0.003)
        elif profit_pct >= 0.01:
            trail_dist = min(trail_dist, 0.0035)
        
        if profit_pct >= V7_CONFIG['trailing_activation']:
            ts = peak * (1 + trail_dist)
            if trail == 0 or ts < trail:
                trail = ts
                updated['trail'] = trail
            if trail > 0 and hi >= trail:
                return {'should_exit': True, 'reason': 'TRAILING', 'exit_price': trail, 'updated': updated}
    
    # Reversal exit
    if idx >= 2:
        prev = df_slice.iloc[idx - 1]
        rev = 0
        if side == 'LONG':
            pnl = (cl - entry) / entry
            if pnl > 0.003:
                if not pd.isna(row.get('st_dir')) and not pd.isna(prev.get('st_dir')):
                    if prev['st_dir'] == 1 and row['st_dir'] == -1: rev += 3
                if prev.get('bull', True) and not row.get('bull', True) and row['open'] > prev['close'] and cl < prev['open']: rev += 2
                if not pd.isna(row.get('macd_l')) and not pd.isna(prev.get('macd_l')):
                    if prev['macd_l'] > prev['macd_s'] and row['macd_l'] < row['macd_s']: rev += 2
        else:
            pnl = (entry - cl) / entry
            if pnl > 0.003:
                if not pd.isna(row.get('st_dir')) and not pd.isna(prev.get('st_dir')):
                    if prev['st_dir'] == -1 and row['st_dir'] == 1: rev += 3
                if not prev.get('bull', False) and row.get('bull', False) and row['close'] > prev['open'] and row['open'] < prev['close']: rev += 2
                if not pd.isna(row.get('macd_l')) and not pd.isna(prev.get('macd_l')):
                    if prev['macd_l'] < prev['macd_s'] and row['macd_l'] > row['macd_s']: rev += 2
        if rev >= 3:
            return {'should_exit': True, 'reason': 'REVERSAL', 'exit_price': cl, 'updated': updated}
    
    if hold_hours >= V7_CONFIG['max_hold_hours']:
        return {'should_exit': True, 'reason': 'MAX_HOLD', 'exit_price': cl, 'updated': updated}
    
    pnl_now = (cl - entry) / entry if side == 'LONG' else (entry - cl) / entry
    if hold_hours >= 6 and abs(pnl_now) < 0.002:
        return {'should_exit': True, 'reason': 'STAGNANT', 'exit_price': cl, 'updated': updated}
    
    return {'should_exit': False, 'reason': 'HOLD', 'exit_price': cl, 'updated': updated}


# ============================================================
# COIN STATE CLASSIFIER
# ============================================================
def classify_coin_state(df, idx):
    """
    Classify coin state at bar idx.
    Returns: dict with state info
    """
    if idx < 30:
        return {'state': 'UNKNOWN', 'adx': 0, 'bb_width': 0, 'vol_ratio': 1}
    
    row = df.iloc[idx]
    adx = float(row.get('adx', 0)) if not pd.isna(row.get('adx')) else 0
    
    # BB width as % of price
    bbu = row.get('bbu', row['close'])
    bbl = row.get('bbl', row['close'])
    bb_width = (bbu - bbl) / row['close'] if row['close'] > 0 and not pd.isna(bbu) and not pd.isna(bbl) else 0
    
    vol_ratio = float(row.get('vol_r', 1)) if not pd.isna(row.get('vol_r')) else 1
    
    st_dir = row.get('st_dir', 0)
    pdi = row.get('pdi', 0)
    mdi = row.get('mdi', 0)
    
    # State classification
    if adx > 25:
        state = 'TRENDING'
    elif adx < 15 or bb_width < 0.02:
        state = 'RANGING'
    elif bb_width > 0.06:
        state = 'VOLATILE'
    else:
        state = 'NORMAL'
    
    return {
        'state': state,
        'adx': adx,
        'bb_width': bb_width,
        'vol_ratio': vol_ratio,
        'st_dir': float(st_dir) if not pd.isna(st_dir) else 0,
        'pdi': float(pdi) if not pd.isna(pdi) else 0,
        'mdi': float(mdi) if not pd.isna(mdi) else 0,
    }


# ============================================================
# BACKTESTER
# ============================================================
class SmartEntryBT:
    def __init__(self, engine, label="", entry_filters=None):
        self.engine = engine
        self.label = label
        self.entry_filters = entry_filters or {}
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
            self._track(all_data, i)
        self._close_all(all_data, min_len - 1)
    
    def _manage(self, all_data, idx):
        closed = []
        for pos in self.positions:
            df = all_data[pos['symbol']]
            if idx >= len(df): continue
            
            pos_data = {
                'entry_price': pos['entry'], 'side': pos['side'],
                'peak': pos['peak'], 'trail': pos['trail'],
                'sl': pos['sl'], 'hold_hours': idx - pos['bar'],
            }
            result = b3_exit_check(self.engine, df.iloc[:idx + 1], pos_data)
            
            upd = result.get('updated', {})
            if 'peak' in upd: pos['peak'] = upd['peak']
            if 'trail' in upd: pos['trail'] = upd['trail']
            
            if result['should_exit']:
                ep = result['exit_price']
                if pos['side'] == 'LONG': ep *= (1 - self.slip)
                else: ep *= (1 + self.slip)
                
                pnl_raw = (ep - pos['entry']) * pos['qty'] if pos['side'] == 'LONG' else (pos['entry'] - ep) * pos['qty']
                pnl = pnl_raw - abs(ep * pos['qty']) * self.comm
                self.balance += pos['size'] + pnl
                
                self.trades.append({
                    'symbol': pos['symbol'], 'side': pos['side'],
                    'pnl': pnl, 'pnl_pct': pnl / pos['size'] * 100,
                    'reason': result['reason'], 'trend': pos['trend'],
                    'strategy': pos.get('strategy', ''), 'hold': idx - pos['bar'],
                    'coin_state': pos.get('coin_state', ''),
                })
                closed.append(pos)
        for p in closed: self.positions.remove(p)
    
    def _scan(self, all_data, idx):
        for sym, df in all_data.items():
            if len(self.positions) >= self.max_pos: break
            if any(p['symbol'] == sym for p in self.positions): continue
            if idx >= len(df) - 1: continue
            
            trend = self.engine.get_4h_trend(df, idx - 1)
            
            # A1: Block NEUTRAL
            if trend == 'NEUTRAL':
                continue
            
            signal = self.engine.detect_entry(df, trend, idx - 1)
            if not signal: continue
            
            # A3: Block losing LONG patterns
            strat = signal.get('strategy', '')
            if signal['side'] == 'LONG' and strat in {'macd_x', 'st_flip', 'engulf'}:
                continue
            
            # ===== PHASE C FILTERS =====
            coin_state = classify_coin_state(df, idx - 1)
            filters = self.entry_filters
            
            # C1: ADX filter — block ranging markets
            if filters.get('adx_filter', False):
                if coin_state['adx'] < 20:
                    continue
            
            # C2: SuperTrend alignment
            if filters.get('st_alignment', False):
                st_dir = coin_state['st_dir']
                if signal['side'] == 'LONG' and st_dir != 1:
                    continue
                if signal['side'] == 'SHORT' and st_dir != -1:
                    continue
            
            # C3: Volume spike required
            if filters.get('vol_filter', False):
                if coin_state['vol_ratio'] < 1.0:
                    continue
            
            # C4: ADX direction alignment
            if filters.get('adx_direction', False):
                if signal['side'] == 'LONG' and coin_state['pdi'] <= coin_state['mdi']:
                    continue
                if signal['side'] == 'SHORT' and coin_state['mdi'] <= coin_state['pdi']:
                    continue
            
            # C5: BB width — block ranging (BB too narrow)
            if filters.get('bb_width_filter', False):
                if coin_state['bb_width'] < 0.02:
                    continue
            
            # Execute
            entry_price = df.iloc[idx]['open']
            if signal['side'] == 'LONG':
                entry_price *= (1 + self.slip)
                sl = entry_price * (1 - V7_CONFIG['sl_pct'])
            else:
                entry_price *= (1 - self.slip)
                sl = entry_price * (1 + V7_CONFIG['sl_pct'])
            
            if self.pos_size > self.balance: continue
            
            qty = self.pos_size / entry_price
            self.balance -= (self.pos_size + self.pos_size * self.comm)
            
            self.positions.append({
                'symbol': sym, 'side': signal['side'],
                'entry': entry_price, 'qty': qty, 'size': self.pos_size,
                'sl': sl, 'peak': entry_price, 'trail': 0, 'bar': idx,
                'trend': trend, 'strategy': strat,
                'coin_state': coin_state['state'],
            })
    
    def _track(self, all_data, idx):
        unrealized = sum(
            ((all_data[p['symbol']].iloc[idx]['close'] - p['entry']) * p['qty'] if p['side'] == 'LONG'
             else (p['entry'] - all_data[p['symbol']].iloc[idx]['close']) * p['qty'])
            for p in self.positions if idx < len(all_data[p['symbol']])
        )
        eq = self.balance + sum(p['size'] for p in self.positions) + unrealized
        if eq > self.peak_bal: self.peak_bal = eq
        dd = (self.peak_bal - eq) / self.peak_bal if self.peak_bal > 0 else 0
        if dd > self.max_dd: self.max_dd = dd
    
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
                    'pnl': pnl, 'pnl_pct': pnl / pos['size'] * 100,
                    'reason': 'FORCE_CLOSE', 'trend': pos['trend'],
                    'strategy': pos.get('strategy', ''), 'hold': idx - pos['bar'],
                    'coin_state': pos.get('coin_state', ''),
                })
        self.positions.clear()
    
    def summary(self):
        if not self.trades:
            return {'trades': 0, 'wr': 0, 'pf': 0, 'pnl': 0, 'pnl_pct': 0,
                    'dd': 0, 'avg_pnl': 0, 'avg_win': 0, 'avg_loss': 0,
                    'long_wr': 0, 'short_wr': 0, 'sl_rate': 0, 'trail_rate': 0}
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
            'pnl_pct': tdf['pnl'].sum() / self.initial * 100,
            'dd': self.max_dd * 100,
            'avg_pnl': tdf['pnl_pct'].mean(),
            'avg_win': w['pnl_pct'].mean() if len(w) > 0 else 0,
            'avg_loss': l['pnl_pct'].mean() if len(l) > 0 else 0,
            'long_wr': len(tdf[(tdf['side']=='LONG') & (tdf['pnl']>0)]) / max(len(tdf[tdf['side']=='LONG']), 1) * 100,
            'short_wr': len(tdf[(tdf['side']=='SHORT') & (tdf['pnl']>0)]) / max(len(tdf[tdf['side']=='SHORT']), 1) * 100,
            'sl_rate': reasons.get('STOP_LOSS', 0) / len(tdf) * 100,
            'trail_rate': reasons.get('TRAILING', 0) / len(tdf) * 100,
        }


def print_cmp(label, base, mod):
    b, m = base, mod
    def d(vb, vm, fmt="+.2f", bh=True):
        delta = vm - vb
        a = "↑" if (delta > 0) == bh else "↓"
        c = "🟢" if (delta > 0) == bh else "🔴"
        if abs(delta) < 0.01: c = "⚪"
        return f"{c} {delta:{fmt}} {a}"
    
    print(f"\n{'='*65}")
    print(f"  {label}")
    print(f"{'='*65}")
    print(f"  {'Metric':<20} {'BASE':>10} {'MOD':>10} {'DELTA':>18}")
    print(f"  {'-'*58}")
    print(f"  {'Trades':<20} {b['trades']:>10} {m['trades']:>10} {d(b['trades'], m['trades'], '+d', False):>18}")
    print(f"  {'Win Rate %':<20} {b['wr']:>9.1f}% {m['wr']:>9.1f}% {d(b['wr'], m['wr']):>18}")
    print(f"  {'Profit Factor':<20} {b['pf']:>10.2f} {m['pf']:>10.2f} {d(b['pf'], m['pf']):>18}")
    print(f"  {'PnL $':<20} {b['pnl']:>+9.2f} {m['pnl']:>+9.2f} {d(b['pnl'], m['pnl']):>18}")
    print(f"  {'Max DD %':<20} {b['dd']:>9.2f}% {m['dd']:>9.2f}% {d(b['dd'], m['dd'], '+.2f', False):>18}")
    print(f"  {'Avg Trade %':<20} {b['avg_pnl']:>+9.3f}% {m['avg_pnl']:>+9.3f}% {d(b['avg_pnl'], m['avg_pnl'], '+.3f'):>18}")
    print(f"  {'SL Rate %':<20} {b['sl_rate']:>9.1f}% {m['sl_rate']:>9.1f}% {d(b['sl_rate'], m['sl_rate'], '+.1f', False):>18}")
    print(f"  {'Trail Rate %':<20} {b['trail_rate']:>9.1f}% {m['trail_rate']:>9.1f}% {d(b['trail_rate'], m['trail_rate'], '+.1f'):>18}")


def main():
    symbols = [
        'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT', 'NEARUSDT',
        'SUIUSDT', 'ARBUSDT', 'APTUSDT', 'INJUSDT', 'LINKUSDT',
    ]
    
    print("=" * 65)
    print("🔬 Phase C: Smart Entry Per Coin State")
    print("  (with A1+A3+B3 confirmed improvements)")
    print("=" * 65)
    
    print("\n📥 Fetching data...")
    engine = ScalpingV7Engine()
    all_data = {}
    for sym in symbols:
        df = fetch_binance_klines(sym)
        if df is not None and len(df) >= 100:
            all_data[sym] = engine.prepare_data(df)
            print(f"  ✅ {sym}: {len(df)} bars")
    
    # BASELINE: A1+A3+B3
    print("\n🏁 BASELINE (A1+A3+B3)...")
    bt_base = SmartEntryBT(engine, "BASELINE")
    bt_base.run(all_data)
    base = bt_base.summary()
    print(f"  → {base['trades']} trades | WR={base['wr']:.1f}% | PF={base['pf']:.2f} | PnL=${base['pnl']:+.2f}")
    
    # C1: ADX filter
    print("\n🧪 C1: ADX > 20 filter...")
    bt_c1 = SmartEntryBT(engine, "C1", {'adx_filter': True})
    bt_c1.run(all_data)
    c1 = bt_c1.summary()
    print_cmp("C1: فقط أسواق متجهة (ADX > 20)", base, c1)
    
    # C2: SuperTrend alignment
    print("\n🧪 C2: SuperTrend alignment...")
    bt_c2 = SmartEntryBT(engine, "C2", {'st_alignment': True})
    bt_c2.run(all_data)
    c2 = bt_c2.summary()
    print_cmp("C2: SuperTrend يوافق اتجاه الدخول", base, c2)
    
    # C3: Volume filter
    print("\n🧪 C3: Volume > 1.0x average...")
    bt_c3 = SmartEntryBT(engine, "C3", {'vol_filter': True})
    bt_c3.run(all_data)
    c3 = bt_c3.summary()
    print_cmp("C3: حجم أعلى من المتوسط", base, c3)
    
    # C4: ADX direction alignment
    print("\n🧪 C4: ADX direction (+DI > -DI for LONG)...")
    bt_c4 = SmartEntryBT(engine, "C4", {'adx_direction': True})
    bt_c4.run(all_data)
    c4 = bt_c4.summary()
    print_cmp("C4: اتجاه ADX يوافق الصفقة", base, c4)
    
    # C5: BB width filter
    print("\n🧪 C5: BB width > 2% (not ranging)...")
    bt_c5 = SmartEntryBT(engine, "C5", {'bb_width_filter': True})
    bt_c5.run(all_data)
    c5 = bt_c5.summary()
    print_cmp("C5: رفض الأسواق الراكدة (BB ضيق)", base, c5)
    
    # Best individual combos
    print("\n🧪 C2+C4: SuperTrend + ADX direction...")
    bt_c24 = SmartEntryBT(engine, "C2+C4", {'st_alignment': True, 'adx_direction': True})
    bt_c24.run(all_data)
    c24 = bt_c24.summary()
    print_cmp("C2+C4: SuperTrend + ADX direction", base, c24)
    
    print("\n🧪 C1+C2: ADX + SuperTrend...")
    bt_c12 = SmartEntryBT(engine, "C1+C2", {'adx_filter': True, 'st_alignment': True})
    bt_c12.run(all_data)
    c12 = bt_c12.summary()
    print_cmp("C1+C2: ADX + SuperTrend", base, c12)
    
    print("\n🧪 ALL C: C1+C2+C3+C4+C5...")
    bt_all = SmartEntryBT(engine, "ALL C", {
        'adx_filter': True, 'st_alignment': True,
        'vol_filter': True, 'adx_direction': True,
        'bb_width_filter': True,
    })
    bt_all.run(all_data)
    call = bt_all.summary()
    print_cmp("ALL C: كل الفلاتر مجتمعة", base, call)
    
    # Verdict
    print("\n" + "=" * 65)
    print("📋 ملخص Phase C:")
    print("=" * 65)
    
    tests = [
        ("C1: ADX>20", c1),
        ("C2: ST align", c2),
        ("C3: Vol>1x", c3),
        ("C4: ADX dir", c4),
        ("C5: BB width", c5),
        ("C2+C4", c24),
        ("C1+C2", c12),
        ("ALL C", call),
    ]
    
    for name, mod in tests:
        pd_ = mod['pnl'] - base['pnl']
        pfd = mod['pf'] - base['pf']
        wrd = mod['wr'] - base['wr']
        v = "✅" if pd_ > 0 and pfd > 0 else "⚠️" if pfd > 0 else "❌"
        print(f"  {v} {name:<15}: PnL {pd_:+.0f}$ | WR {wrd:+.1f}% | PF {pfd:+.2f} | Trades {mod['trades']}")
    
    best_name, best = max(tests, key=lambda x: x[1]['pnl'])
    print(f"\n  🏆 Best: {best_name} → PnL=${best['pnl']:+.2f} | WR={best['wr']:.1f}% | PF={best['pf']:.2f}")
    
    return base, tests


if __name__ == '__main__':
    main()
