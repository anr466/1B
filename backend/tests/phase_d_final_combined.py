#!/usr/bin/env python3
"""
Phase D: Final Combined Backtest — المقارنة النهائية
=====================================================
يقارن الاستراتيجية الأصلية V7 مع كل التحسينات المُثبتة:

Entry:  A1 (block NEUTRAL) + A3 (block losing LONG patterns) + C2 (ST align) + C4 (ADX dir)
Exit:   B3 (progressive trailing)

المخرجات: جدول مقارنة شامل BEFORE vs AFTER
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

def fetch_klines(symbol, interval='1h', limit=1000):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
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
    except Exception as e:
        return None


def progressive_exit(engine, df_slice, pos_data):
    """V7 exit + B3 progressive trailing"""
    if df_slice is None or len(df_slice) < 3:
        return {'should_exit': False, 'reason': 'HOLD'}
    
    idx = len(df_slice) - 1
    row = df_slice.iloc[idx]
    hi, lo, cl = row['high'], row['low'], row['close']
    entry = pos_data['entry_price']
    side = pos_data.get('side', 'LONG')
    peak = pos_data.get('peak', entry)
    trail = pos_data.get('trail', 0)
    sl = pos_data.get('sl')
    hold_hours = pos_data.get('hold_hours', 0)
    updated = {}

    if side == 'LONG':
        if hi > peak: peak = hi; updated['peak'] = peak
        if lo <= sl:
            return {'should_exit': True, 'reason': 'STOP_LOSS', 'exit_price': sl, 'updated': updated}
        profit_pct = (peak - entry) / entry
        td = V7_CONFIG['trailing_distance']
        if profit_pct >= 0.02: td = min(td, 0.002)
        elif profit_pct >= 0.015: td = min(td, 0.003)
        elif profit_pct >= 0.01: td = min(td, 0.0035)
        if profit_pct >= V7_CONFIG['trailing_activation']:
            ts = peak * (1 - td)
            if ts > trail: trail = ts; updated['trail'] = trail
            if trail > 0 and lo <= trail:
                return {'should_exit': True, 'reason': 'TRAILING', 'exit_price': trail, 'updated': updated}
    else:
        if lo < peak: peak = lo; updated['peak'] = peak
        if hi >= sl:
            return {'should_exit': True, 'reason': 'STOP_LOSS', 'exit_price': sl, 'updated': updated}
        profit_pct = (entry - peak) / entry
        td = V7_CONFIG['trailing_distance']
        if profit_pct >= 0.02: td = min(td, 0.002)
        elif profit_pct >= 0.015: td = min(td, 0.003)
        elif profit_pct >= 0.01: td = min(td, 0.0035)
        if profit_pct >= V7_CONFIG['trailing_activation']:
            ts = peak * (1 + td)
            if trail == 0 or ts < trail: trail = ts; updated['trail'] = trail
            if trail > 0 and hi >= trail:
                return {'should_exit': True, 'reason': 'TRAILING', 'exit_price': trail, 'updated': updated}

    # Reversal
    if idx >= 2:
        prev = df_slice.iloc[idx - 1]
        rev = 0
        if side == 'LONG':
            pnl = (cl - entry) / entry
            if pnl > 0.003:
                if not pd.isna(row.get('st_dir')) and not pd.isna(prev.get('st_dir')):
                    if prev['st_dir'] == 1 and row['st_dir'] == -1: rev += 3
                if prev.get('bull',True) and not row.get('bull',True) and row['open']>prev['close'] and cl<prev['open']: rev += 2
                if not pd.isna(row.get('macd_l')) and not pd.isna(prev.get('macd_l')):
                    if prev['macd_l']>prev['macd_s'] and row['macd_l']<row['macd_s']: rev += 2
        else:
            pnl = (entry - cl) / entry
            if pnl > 0.003:
                if not pd.isna(row.get('st_dir')) and not pd.isna(prev.get('st_dir')):
                    if prev['st_dir'] == -1 and row['st_dir'] == 1: rev += 3
                if not prev.get('bull',False) and row.get('bull',False) and row['close']>prev['open'] and row['open']<prev['close']: rev += 2
                if not pd.isna(row.get('macd_l')) and not pd.isna(prev.get('macd_l')):
                    if prev['macd_l']<prev['macd_s'] and row['macd_l']>row['macd_s']: rev += 2
        if rev >= 3:
            return {'should_exit': True, 'reason': 'REVERSAL', 'exit_price': cl, 'updated': updated}

    if hold_hours >= V7_CONFIG['max_hold_hours']:
        return {'should_exit': True, 'reason': 'MAX_HOLD', 'exit_price': cl, 'updated': updated}
    pnl_now = (cl-entry)/entry if side=='LONG' else (entry-cl)/entry
    if hold_hours >= 6 and abs(pnl_now) < 0.002:
        return {'should_exit': True, 'reason': 'STAGNANT', 'exit_price': cl, 'updated': updated}
    return {'should_exit': False, 'reason': 'HOLD', 'exit_price': cl, 'updated': updated}


class Backtester:
    def __init__(self, engine, mode='original'):
        self.engine = engine
        self.mode = mode  # 'original' or 'enhanced'
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
        self.max_loss_streak = 0
        self._curr_loss_streak = 0

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
            df_slice = df.iloc[:idx+1]

            if self.mode == 'enhanced':
                result = progressive_exit(self.engine, df_slice, pos_data)
            else:
                result = self.engine.check_exit_signal(df_slice, pos_data)

            upd = result.get('updated', {})
            if 'peak' in upd: pos['peak'] = upd['peak']
            if 'trail' in upd: pos['trail'] = upd['trail']

            if result['should_exit']:
                ep = result['exit_price']
                if pos['side']=='LONG': ep *= (1 - self.slip)
                else: ep *= (1 + self.slip)
                pnl_raw = (ep-pos['entry'])*pos['qty'] if pos['side']=='LONG' else (pos['entry']-ep)*pos['qty']
                pnl = pnl_raw - abs(ep*pos['qty'])*self.comm
                self.balance += pos['size'] + pnl

                if pnl > 0:
                    self._curr_loss_streak = 0
                else:
                    self._curr_loss_streak += 1
                    self.max_loss_streak = max(self.max_loss_streak, self._curr_loss_streak)

                self.trades.append({
                    'symbol': pos['symbol'], 'side': pos['side'],
                    'entry': pos['entry'], 'exit': ep,
                    'pnl': pnl, 'pnl_pct': pnl/pos['size']*100,
                    'reason': result['reason'], 'trend': pos['trend'],
                    'strategy': pos.get('strategy',''), 'hold': idx-pos['bar'],
                    'entry_time': pos.get('entry_time',''),
                })
                closed.append(pos)
        for p in closed: self.positions.remove(p)

    def _scan(self, all_data, idx):
        for sym, df in all_data.items():
            if len(self.positions) >= self.max_pos: break
            if any(p['symbol']==sym for p in self.positions): continue
            if idx >= len(df)-1: continue

            trend = self.engine.get_4h_trend(df, idx-1)

            if self.mode == 'enhanced':
                # A1: Block NEUTRAL
                if trend == 'NEUTRAL': continue

            signal = self.engine.detect_entry(df, trend, idx-1)
            if not signal: continue

            if self.mode == 'enhanced':
                # A3: Block losing LONG patterns
                strat = signal.get('strategy','')
                if signal['side']=='LONG' and strat in {'macd_x','st_flip','engulf'}:
                    continue

                # C2: SuperTrend alignment
                row = df.iloc[idx-1]
                st_dir = row.get('st_dir', 0)
                if not pd.isna(st_dir):
                    if signal['side']=='LONG' and st_dir != 1: continue
                    if signal['side']=='SHORT' and st_dir != -1: continue

                # C4: ADX direction
                pdi = row.get('pdi', 0)
                mdi = row.get('mdi', 0)
                if not pd.isna(pdi) and not pd.isna(mdi):
                    if signal['side']=='LONG' and pdi <= mdi: continue
                    if signal['side']=='SHORT' and mdi <= pdi: continue

            entry_price = df.iloc[idx]['open']
            if signal['side']=='LONG':
                entry_price *= (1+self.slip)
                sl = entry_price*(1-V7_CONFIG['sl_pct'])
            else:
                entry_price *= (1-self.slip)
                sl = entry_price*(1+V7_CONFIG['sl_pct'])

            if self.pos_size > self.balance: continue
            qty = self.pos_size / entry_price
            self.balance -= (self.pos_size + self.pos_size*self.comm)

            self.positions.append({
                'symbol': sym, 'side': signal['side'],
                'entry': entry_price, 'qty': qty, 'size': self.pos_size,
                'sl': sl, 'peak': entry_price, 'trail': 0, 'bar': idx,
                'trend': trend, 'strategy': signal.get('strategy',''),
                'entry_time': df.iloc[idx]['timestamp'] if 'timestamp' in df.columns else '',
            })

    def _track(self, all_data, idx):
        unrealized = sum(
            ((all_data[p['symbol']].iloc[idx]['close']-p['entry'])*p['qty'] if p['side']=='LONG'
             else (p['entry']-all_data[p['symbol']].iloc[idx]['close'])*p['qty'])
            for p in self.positions if idx < len(all_data[p['symbol']])
        )
        eq = self.balance + sum(p['size'] for p in self.positions) + unrealized
        if eq > self.peak_bal: self.peak_bal = eq
        dd = (self.peak_bal - eq)/self.peak_bal if self.peak_bal>0 else 0
        if dd > self.max_dd: self.max_dd = dd

    def _close_all(self, all_data, idx):
        for pos in list(self.positions):
            df = all_data[pos['symbol']]
            if idx < len(df):
                ep = df.iloc[idx]['close']
                pnl = ((ep-pos['entry'])*pos['qty'] if pos['side']=='LONG'
                       else (pos['entry']-ep)*pos['qty']) - abs(ep*pos['qty'])*self.comm
                self.balance += pos['size'] + pnl
                self.trades.append({
                    'symbol': pos['symbol'], 'side': pos['side'],
                    'entry': pos['entry'], 'exit': ep,
                    'pnl': pnl, 'pnl_pct': pnl/pos['size']*100,
                    'reason': 'FORCE_CLOSE', 'trend': pos['trend'],
                    'strategy': pos.get('strategy',''), 'hold': idx-pos['bar'],
                    'entry_time': pos.get('entry_time',''),
                })
        self.positions.clear()

    def full_report(self):
        if not self.trades:
            return None
        tdf = pd.DataFrame(self.trades)
        w = tdf[tdf['pnl']>0]
        l = tdf[tdf['pnl']<=0]
        gp = w['pnl'].sum() if len(w)>0 else 0
        gl = abs(l['pnl'].sum()) if len(l)>0 else 0
        reasons = tdf['reason'].value_counts()

        # Per-symbol
        sym_stats = {}
        for sym in tdf['symbol'].unique():
            st = tdf[tdf['symbol']==sym]
            sw = st[st['pnl']>0]
            sym_stats[sym] = {
                'trades': len(st), 'wr': len(sw)/len(st)*100,
                'pnl': st['pnl'].sum(), 'avg': st['pnl_pct'].mean(),
            }

        # Per-trend
        trend_stats = {}
        for tr in tdf['trend'].unique():
            tt = tdf[tdf['trend']==tr]
            tw = tt[tt['pnl']>0]
            trend_stats[tr] = {
                'trades': len(tt), 'wr': len(tw)/len(tt)*100,
                'pnl': tt['pnl'].sum(),
            }

        # Per-strategy
        strat_stats = {}
        for st in tdf['strategy'].unique():
            ss = tdf[tdf['strategy']==st]
            ssw = ss[ss['pnl']>0]
            strat_stats[st] = {
                'trades': len(ss), 'wr': len(ssw)/len(ss)*100,
                'pnl': ss['pnl'].sum(),
            }

        return {
            'trades': len(tdf),
            'wr': len(w)/len(tdf)*100,
            'pf': gp/gl if gl>0 else float('inf'),
            'pnl': tdf['pnl'].sum(),
            'pnl_pct': tdf['pnl'].sum()/self.initial*100,
            'dd': self.max_dd*100,
            'avg_pnl': tdf['pnl_pct'].mean(),
            'avg_win': w['pnl_pct'].mean() if len(w)>0 else 0,
            'avg_loss': l['pnl_pct'].mean() if len(l)>0 else 0,
            'avg_hold': tdf['hold'].mean(),
            'long_n': len(tdf[tdf['side']=='LONG']),
            'short_n': len(tdf[tdf['side']=='SHORT']),
            'long_wr': len(tdf[(tdf['side']=='LONG')&(tdf['pnl']>0)])/max(len(tdf[tdf['side']=='LONG']),1)*100,
            'short_wr': len(tdf[(tdf['side']=='SHORT')&(tdf['pnl']>0)])/max(len(tdf[tdf['side']=='SHORT']),1)*100,
            'sl_rate': reasons.get('STOP_LOSS',0)/len(tdf)*100,
            'trail_rate': reasons.get('TRAILING',0)/len(tdf)*100,
            'max_loss_streak': self.max_loss_streak,
            'reasons': {k:int(v) for k,v in reasons.items()},
            'per_symbol': sym_stats,
            'per_trend': trend_stats,
            'per_strategy': strat_stats,
        }


def main():
    symbols = [
        'ETHUSDT','BNBUSDT','SOLUSDT','AVAXUSDT','NEARUSDT',
        'SUIUSDT','ARBUSDT','APTUSDT','INJUSDT','LINKUSDT',
    ]

    print("="*70)
    print("🏁 Phase D: FINAL COMBINED BACKTEST")
    print("    ORIGINAL V7  vs  ENHANCED (A1+A3+B3+C2+C4)")
    print("="*70)

    print("\n📥 Fetching data...")
    engine = ScalpingV7Engine()
    all_data = {}
    for sym in symbols:
        df = fetch_klines(sym)
        if df is not None and len(df) >= 100:
            all_data[sym] = engine.prepare_data(df)
            print(f"  ✅ {sym}: {len(df)} bars")
    
    days = min(len(df) for df in all_data.values()) / 24
    print(f"\n  📊 {len(all_data)} symbols | {days:.0f} days of data")

    # ORIGINAL
    print("\n🔵 Running ORIGINAL V7...")
    bt_orig = Backtester(engine, 'original')
    bt_orig.run(all_data)
    orig = bt_orig.full_report()

    # ENHANCED
    print("🟢 Running ENHANCED (A1+A3+B3+C2+C4)...")
    bt_enh = Backtester(engine, 'enhanced')
    bt_enh.run(all_data)
    enh = bt_enh.full_report()

    # ============================================================
    # COMPARISON TABLE
    # ============================================================
    o, e = orig, enh

    def d(vo, ve, fmt=".2f", bh=True):
        delta = ve - vo
        arrow = "▲" if delta > 0 else "▼" if delta < 0 else "="
        color = "🟢" if (delta > 0) == bh else "🔴" if delta != 0 else "⚪"
        return f"{color}{delta:{fmt}}{arrow}"

    print("\n" + "="*70)
    print("📊 المقارنة النهائية: ORIGINAL vs ENHANCED")
    print("="*70)
    print(f"""
┌──────────────────────┬──────────────┬──────────────┬──────────────┐
│ المقياس               │  ORIGINAL V7 │   ENHANCED   │    DELTA     │
├──────────────────────┼──────────────┼──────────────┼──────────────┤
│ عدد الصفقات           │ {o['trades']:>12} │ {e['trades']:>12} │ {e['trades']-o['trades']:>+12} │
│ نسبة الفوز %          │ {o['wr']:>11.1f}% │ {e['wr']:>11.1f}% │ {e['wr']-o['wr']:>+11.1f}% │
│ عامل الربحية PF       │ {o['pf']:>12.2f} │ {e['pf']:>12.2f} │ {e['pf']-o['pf']:>+12.2f} │
│ إجمالي الربح $        │ {o['pnl']:>+11.2f} │ {e['pnl']:>+11.2f} │ {e['pnl']-o['pnl']:>+11.2f} │
│ العائد %              │ {o['pnl_pct']:>+11.2f}% │ {e['pnl_pct']:>+11.2f}% │ {e['pnl_pct']-o['pnl_pct']:>+11.2f}% │
│ أقصى تراجع DD%        │ {o['dd']:>11.2f}% │ {e['dd']:>11.2f}% │ {e['dd']-o['dd']:>+11.2f}% │
│ متوسط صفقة %          │ {o['avg_pnl']:>+11.3f}% │ {e['avg_pnl']:>+11.3f}% │ {e['avg_pnl']-o['avg_pnl']:>+11.3f}% │
│ متوسط ربح %           │ {o['avg_win']:>+11.3f}% │ {e['avg_win']:>+11.3f}% │ {e['avg_win']-o['avg_win']:>+11.3f}% │
│ متوسط خسارة %         │ {o['avg_loss']:>+11.3f}% │ {e['avg_loss']:>+11.3f}% │ {e['avg_loss']-o['avg_loss']:>+11.3f}% │
│ متوسط احتفاظ (ساعة)    │ {o['avg_hold']:>11.1f}h │ {e['avg_hold']:>11.1f}h │ {e['avg_hold']-o['avg_hold']:>+11.1f}h │
│ أطول سلسلة خسارة      │ {o['max_loss_streak']:>12} │ {e['max_loss_streak']:>12} │ {e['max_loss_streak']-o['max_loss_streak']:>+12} │
├──────────────────────┼──────────────┼──────────────┼──────────────┤
│ LONG عدد              │ {o['long_n']:>12} │ {e['long_n']:>12} │ {e['long_n']-o['long_n']:>+12} │
│ LONG WR%              │ {o['long_wr']:>11.1f}% │ {e['long_wr']:>11.1f}% │ {e['long_wr']-o['long_wr']:>+11.1f}% │
│ SHORT عدد             │ {o['short_n']:>12} │ {e['short_n']:>12} │ {e['short_n']-o['short_n']:>+12} │
│ SHORT WR%             │ {o['short_wr']:>11.1f}% │ {e['short_wr']:>11.1f}% │ {e['short_wr']-o['short_wr']:>+11.1f}% │
├──────────────────────┼──────────────┼──────────────┼──────────────┤
│ SL Rate%              │ {o['sl_rate']:>11.1f}% │ {e['sl_rate']:>11.1f}% │ {e['sl_rate']-o['sl_rate']:>+11.1f}% │
│ Trail Rate%           │ {o['trail_rate']:>11.1f}% │ {e['trail_rate']:>11.1f}% │ {e['trail_rate']-o['trail_rate']:>+11.1f}% │
└──────────────────────┴──────────────┴──────────────┴──────────────┘""")

    # Exit reasons
    print("\n📊 أسباب الخروج:")
    all_reasons = set(list(o['reasons'].keys()) + list(e['reasons'].keys()))
    print(f"  {'Reason':<15} {'ORIG':>8} {'ENH':>8}")
    print(f"  {'-'*33}")
    for r in sorted(all_reasons):
        ov = o['reasons'].get(r, 0)
        ev = e['reasons'].get(r, 0)
        print(f"  {r:<15} {ov:>8} {ev:>8}")

    # Per-symbol comparison
    print("\n📊 أداء كل عملة:")
    print(f"  {'Symbol':<12} {'ORIG WR':>8} {'ENH WR':>8} {'ORIG PnL':>10} {'ENH PnL':>10} {'Δ PnL':>10}")
    print(f"  {'-'*58}")
    all_syms = sorted(set(list(o['per_symbol'].keys()) + list(e['per_symbol'].keys())))
    for sym in all_syms:
        os_ = o['per_symbol'].get(sym, {'trades':0,'wr':0,'pnl':0})
        es_ = e['per_symbol'].get(sym, {'trades':0,'wr':0,'pnl':0})
        delta_pnl = es_['pnl'] - os_['pnl']
        marker = "🟢" if delta_pnl > 0 else "🔴" if delta_pnl < -1 else "⚪"
        print(f"  {sym:<12} {os_['wr']:>7.1f}% {es_['wr']:>7.1f}% ${os_['pnl']:>+8.2f} ${es_['pnl']:>+8.2f} {marker}{delta_pnl:>+8.2f}")

    # Per-trend
    print("\n📊 أداء حسب الاتجاه:")
    print(f"  {'Trend':<10} {'ORIG':>6} {'WR':>6} {'PnL':>9} {'ENH':>6} {'WR':>6} {'PnL':>9}")
    print(f"  {'-'*55}")
    for tr in ['UP','DOWN','NEUTRAL']:
        ot = o['per_trend'].get(tr, {'trades':0,'wr':0,'pnl':0})
        et = e['per_trend'].get(tr, {'trades':0,'wr':0,'pnl':0})
        print(f"  {tr:<10} {ot['trades']:>6} {ot['wr']:>5.1f}% ${ot['pnl']:>+7.0f} {et['trades']:>6} {et['wr']:>5.1f}% ${et['pnl']:>+7.0f}")

    # VERDICT
    pnl_improved = e['pnl'] > o['pnl']
    pf_improved = e['pf'] > o['pf']
    wr_improved = e['wr'] > o['wr']
    dd_improved = e['dd'] < o['dd']

    improvements = sum([pnl_improved, pf_improved, wr_improved, dd_improved])

    print("\n" + "="*70)
    print("🏆 الحكم النهائي:")
    print("="*70)
    print(f"  PnL:  {'🟢 تحسن' if pnl_improved else '🔴 تراجع'} (${o['pnl']:+.2f} → ${e['pnl']:+.2f})")
    print(f"  PF:   {'🟢 تحسن' if pf_improved else '🔴 تراجع'} ({o['pf']:.2f} → {e['pf']:.2f})")
    print(f"  WR:   {'🟢 تحسن' if wr_improved else '🔴 تراجع'} ({o['wr']:.1f}% → {e['wr']:.1f}%)")
    print(f"  DD:   {'🟢 تحسن' if dd_improved else '🔴 تراجع'} ({o['dd']:.2f}% → {e['dd']:.2f}%)")

    if improvements >= 3:
        print(f"\n  ✅ التحسينات ناجحة ({improvements}/4 مقاييس تحسنت) — جاهز للتطبيق")
    elif improvements >= 2:
        print(f"\n  ⚠️ التحسينات جزئية ({improvements}/4) — يحتاج مراجعة")
    else:
        print(f"\n  ❌ التحسينات غير كافية ({improvements}/4) — لا تُطبّق")

    print("\n  التحسينات المطبقة:")
    print("    A1: حظر التداول في NEUTRAL trend")
    print("    A3: حظر أنماط LONG الخاسرة (macd_x, st_flip, engulf)")
    print("    B3: تضييق Trailing التدريجي (+1%→0.35%, +1.5%→0.3%, +2%→0.2%)")
    print("    C2: SuperTrend يوافق اتجاه الدخول")
    print("    C4: ADX direction يوافق الصفقة")
    print("="*70)

    return orig, enh


if __name__ == '__main__':
    main()
