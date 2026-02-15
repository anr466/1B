#!/usr/bin/env python3
"""
🚀 Scalping Backtest v7 - LONG + SHORT with Quality Filtering
==============================================================
Key changes from v3 (PF 0.94):
1. ENTRY QUALITY: Require breakout_volume OR 2+ timing signals
2. SHORT SUPPORT: Trade shorts when 4H trend is DOWN
3. v3 exit params: Trailing 0.6%/0.4%, SL 1.0%
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests, time, logging

logging.basicConfig(level=logging.WARNING)

# ============================================================
# CONFIGURATION
# ============================================================
COINS = [
    'ETHUSDT', 'BNBUSDT', 'SOLUSDT',
    'AVAXUSDT', 'NEARUSDT', 'LINKUSDT', 'APTUSDT',
    'SUIUSDT', 'ARBUSDT', 'INJUSDT',
]
CATEGORIES = {
    'Large Cap': ['ETHUSDT', 'BNBUSDT', 'SOLUSDT'],
    'Mid Cap': ['AVAXUSDT', 'NEARUSDT', 'LINKUSDT', 'APTUSDT'],
    'Small Cap': ['SUIUSDT', 'ARBUSDT', 'INJUSDT'],
}

INITIAL_BALANCE = 10_000
COMMISSION_PCT = 0.001
SLIPPAGE_PCT = 0.0005
MAX_POSITIONS = 5
POSITION_SIZE_PCT = 0.06
MAX_HOLD_HOURS = 12

# Entry
MIN_CONFLUENCE = 4
MIN_TIMING = 1
REQUIRE_QUALITY = True  # Require breakout OR 2+ timing signals

# Exit - trailing only (proven best)
SL_PCT = 0.010          # 1.0% stop loss
TRAILING_ACT = 0.006    # Activate trailing at +0.6%
TRAILING_DIST = 0.004   # 0.4% trailing distance

# ============================================================
# INDICATORS (manual, no pandas_ta)
# ============================================================
def ema(s, p): return s.ewm(span=p, adjust=False).mean()

def rsi(s, p=14):
    d = s.diff()
    g = d.where(d > 0, 0).rolling(p).mean()
    l = (-d.where(d < 0, 0)).rolling(p).mean()
    return 100 - 100 / (1 + g / l)

def macd(s, f=12, sl=26, sg=9):
    m = ema(s, f) - ema(s, sl)
    sig = ema(m, sg)
    return m, sig, m - sig

def atr(h, l, c, p=14):
    tr = pd.concat([h-l, abs(h-c.shift(1)), abs(l-c.shift(1))], axis=1).max(axis=1)
    return tr.rolling(p).mean()

def supertrend(h, l, c, p=10, mult=3.0):
    a = atr(h, l, c, p)
    hl2 = (h + l) / 2
    ub = hl2 + mult * a
    lb = hl2 - mult * a
    st = pd.Series(index=c.index, dtype=float)
    dr = pd.Series(index=c.index, dtype=float)
    st.iloc[0] = ub.iloc[0]; dr.iloc[0] = -1
    for i in range(1, len(c)):
        if pd.isna(ub.iloc[i]) or pd.isna(lb.iloc[i]):
            st.iloc[i] = st.iloc[i-1]; dr.iloc[i] = dr.iloc[i-1]; continue
        if c.iloc[i-1] <= st.iloc[i-1]:
            if c.iloc[i] > ub.iloc[i]:
                st.iloc[i] = lb.iloc[i]; dr.iloc[i] = 1
            else:
                st.iloc[i] = min(ub.iloc[i], st.iloc[i-1] if st.iloc[i-1] > 0 else ub.iloc[i]); dr.iloc[i] = -1
        else:
            if c.iloc[i] < lb.iloc[i]:
                st.iloc[i] = ub.iloc[i]; dr.iloc[i] = -1
            else:
                st.iloc[i] = max(lb.iloc[i], st.iloc[i-1] if st.iloc[i-1] > 0 else lb.iloc[i]); dr.iloc[i] = 1
    return st, dr

def bbands(s, p=20, std=2.0):
    m = s.rolling(p).mean(); sd = s.rolling(p).std()
    return m + std*sd, m, m - std*sd

def adx_calc(h, l, c, p=14):
    n = len(c); hv = h.values; lv = l.values; cv = c.values
    tr = np.zeros(n); pdm = np.zeros(n); mdm = np.zeros(n)
    for i in range(1, n):
        hd = hv[i]-hv[i-1]; ld = lv[i-1]-lv[i]
        tr[i] = max(hv[i]-lv[i], abs(hv[i]-cv[i-1]), abs(lv[i]-cv[i-1]))
        pdm[i] = hd if (hd > ld and hd > 0) else 0
        mdm[i] = ld if (ld > hd and ld > 0) else 0
    sa = np.zeros(n); sp = np.zeros(n); sm = np.zeros(n)
    if n > p:
        sa[p] = np.mean(tr[1:p+1]); sp[p] = np.mean(pdm[1:p+1]); sm[p] = np.mean(mdm[1:p+1])
        for i in range(p+1, n):
            sa[i] = (sa[i-1]*(p-1)+tr[i])/p; sp[i] = (sp[i-1]*(p-1)+pdm[i])/p; sm[i] = (sm[i-1]*(p-1)+mdm[i])/p
    pdi = np.where(sa > 0, sp/sa*100, 0); mdi = np.where(sa > 0, sm/sa*100, 0)
    dx = np.where((pdi+mdi) > 0, np.abs(pdi-mdi)/(pdi+mdi)*100, 0)
    av = np.zeros(n); s2 = p*2
    if s2 < n:
        av[s2] = np.mean(dx[p:s2+1])
        for i in range(s2+1, n): av[i] = (av[i-1]*(p-1)+dx[i])/p
    return pd.Series(av, index=c.index), pd.Series(pdi, index=c.index), pd.Series(mdi, index=c.index)

# ============================================================
# DATA
# ============================================================
def fetch_klines(symbol, interval='1h', months=6):
    end = int(datetime.now().timestamp()*1000)
    start = int((datetime.now()-timedelta(days=months*30)).timestamp()*1000)
    klines = []; cur = start
    while cur < end:
        try:
            r = requests.get('https://api.binance.com/api/v3/klines',
                params={'symbol':symbol,'interval':interval,'startTime':cur,'endTime':end,'limit':1000}, timeout=15)
            d = r.json()
            if not d or not isinstance(d, list): break
            klines.extend(d); cur = d[-1][0]+1
            if len(d) < 1000: break
            time.sleep(0.2)
        except: break
    if not klines: return pd.DataFrame()
    df = pd.DataFrame(klines, columns=['timestamp','open','high','low','close','volume',
        'close_time','quote_volume','trades','taker_buy_base','taker_buy_quote','ignore'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for c in ['open','high','low','close','volume']: df[c] = df[c].astype(float)
    return df.drop_duplicates(subset='timestamp').sort_values('timestamp').reset_index(drop=True)

def prep(df):
    if len(df) < 60: return df
    df['ema8'] = ema(df['close'], 8)
    df['ema21'] = ema(df['close'], 21)
    df['ema55'] = ema(df['close'], 55)
    df['rsi'] = rsi(df['close'])
    df['macd_l'], df['macd_s'], df['macd_h'] = macd(df['close'])
    df['atr'] = atr(df['high'], df['low'], df['close'])
    df['st'], df['st_dir'] = supertrend(df['high'], df['low'], df['close'])
    df['bbu'], df['bbm'], df['bbl'] = bbands(df['close'])
    df['adx'], df['pdi'], df['mdi'] = adx_calc(df['high'], df['low'], df['close'])
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_r'] = df['volume'] / df['vol_ma']
    df['body'] = abs(df['close'] - df['open'])
    df['range'] = df['high'] - df['low']
    df['uwk'] = df['high'] - df[['close','open']].max(axis=1)
    df['lwk'] = df[['close','open']].min(axis=1) - df['low']
    df['bull'] = df['close'] > df['open']
    df['res20'] = df['high'].rolling(20).max()
    df['sup20'] = df['low'].rolling(20).min()
    return df

# ============================================================
# 4H TREND
# ============================================================
def trend_4h(df, idx):
    if idx < 20: return 'NEUTRAL'
    r = df.iloc[idx]
    e21 = r.get('ema21'); e55 = r.get('ema55')
    if pd.isna(e21) or pd.isna(e55): return 'NEUTRAL'
    c = r['close']
    if e21 > e55 and c > e21: return 'UP'
    elif e21 < e55 and c < e21: return 'DOWN'
    return 'NEUTRAL'

# ============================================================
# LONG ENTRY SIGNALS
# ============================================================
def detect_long(df, idx):
    if idx < 55: return 0, [], 0
    r = df.iloc[idx]; p = df.iloc[idx-1]
    timing = []; cond = []; sc = 0; cur = r['close']
    if pd.isna(r.get('vol_r')) or r['vol_r'] < 0.9: return 0, ['low_vol'], 0

    # TIMING (2pts each)
    if not pd.isna(r['st_dir']) and not pd.isna(p['st_dir']):
        if p['st_dir'] == -1 and r['st_dir'] == 1: timing.append('st_flip'); sc += 2
    if not pd.isna(r['macd_l']) and not pd.isna(p['macd_l']):
        if p['macd_l'] < p['macd_s'] and r['macd_l'] > r['macd_s']: timing.append('macd_x'); sc += 2
    if not pd.isna(r['rsi']) and not pd.isna(p['rsi']):
        if p['rsi'] < 35 and r['rsi'] > p['rsi'] and r['rsi'] < 55: timing.append('rsi_bounce'); sc += 2
    if r['range'] > 0 and r['body'] > 0:
        if not p['bull'] and r['bull'] and r['close'] > p['open'] and r['open'] < p['close']:
            timing.append('engulf'); sc += 2
    if not pd.isna(r.get('res20')):
        prev_res = df['high'].iloc[max(0,idx-21):idx-1].max()
        if not pd.isna(prev_res) and cur > prev_res and r['vol_r'] > 1.5:
            timing.append('breakout'); sc += 2
    if not pd.isna(r['bbl']) and not pd.isna(p['bbl']):
        if p['low'] <= p['bbl'] and cur > r['bbl'] and r['bull']: timing.append('bb_bounce'); sc += 2
    if r['range'] > 0 and r['body'] > 0:
        if r['lwk'] > r['body']*2 and r['uwk'] < r['body']*0.3 and r['bull']:
            timing.append('hammer'); sc += 2

    # CONDITIONS (1pt each)
    if not pd.isna(r['ema8']) and not pd.isna(r['ema21']) and not pd.isna(r['ema55']):
        if r['ema8'] > r['ema21'] > r['ema55']: cond.append('ema_up'); sc += 1
    if not pd.isna(r['st_dir']) and r['st_dir'] == 1 and 'st_flip' not in timing:
        cond.append('st_bull'); sc += 1
    if not pd.isna(r['rsi']) and not pd.isna(p['rsi']):
        if 40 < r['rsi'] < 65 and r['rsi'] > p['rsi']: cond.append('rsi_mom'); sc += 1
    if not pd.isna(r['macd_h']) and not pd.isna(p['macd_h']):
        if r['macd_h'] > 0 and r['macd_h'] > p['macd_h']: cond.append('macd_up'); sc += 1
    if not pd.isna(r['ema8']):
        if abs(cur - r['ema8'])/cur < 0.004: cond.append('near_ema'); sc += 1
    if not pd.isna(r['adx']) and r['adx'] > 20 and not pd.isna(r['pdi']) and not pd.isna(r['mdi']):
        if r['pdi'] > r['mdi']: cond.append('adx_bull'); sc += 1
    if not pd.isna(r['vol_r']) and r['vol_r'] > 1.3: cond.append('hi_vol'); sc += 1

    # PENALTIES
    if not pd.isna(r['rsi']) and r['rsi'] > 72: sc -= 3
    if not pd.isna(r['st_dir']) and r['st_dir'] == -1: sc -= 2

    return sc, timing + cond, len(timing)

# ============================================================
# SHORT ENTRY SIGNALS
# ============================================================
def detect_short(df, idx):
    if idx < 55: return 0, [], 0
    r = df.iloc[idx]; p = df.iloc[idx-1]
    timing = []; cond = []; sc = 0; cur = r['close']
    if pd.isna(r.get('vol_r')) or r['vol_r'] < 0.9: return 0, ['low_vol'], 0

    # TIMING (2pts each)
    if not pd.isna(r['st_dir']) and not pd.isna(p['st_dir']):
        if p['st_dir'] == 1 and r['st_dir'] == -1: timing.append('st_flip_bear'); sc += 2
    if not pd.isna(r['macd_l']) and not pd.isna(p['macd_l']):
        if p['macd_l'] > p['macd_s'] and r['macd_l'] < r['macd_s']: timing.append('macd_x_bear'); sc += 2
    if not pd.isna(r['rsi']) and not pd.isna(p['rsi']):
        if p['rsi'] > 65 and r['rsi'] < p['rsi'] and r['rsi'] > 45: timing.append('rsi_reject'); sc += 2
    if r['range'] > 0 and r['body'] > 0:
        if p['bull'] and not r['bull'] and r['open'] > p['close'] and r['close'] < p['open']:
            timing.append('engulf_bear'); sc += 2
    if not pd.isna(r.get('sup20')):
        prev_sup = df['low'].iloc[max(0,idx-21):idx-1].min()
        if not pd.isna(prev_sup) and cur < prev_sup and r['vol_r'] > 1.5:
            timing.append('breakdown'); sc += 2
    if not pd.isna(r['bbu']) and not pd.isna(p['bbu']):
        if p['high'] >= p['bbu'] and cur < r['bbu'] and not r['bull']:
            timing.append('bb_reject'); sc += 2
    if r['range'] > 0 and r['body'] > 0:
        if r['uwk'] > r['body']*2 and r['lwk'] < r['body']*0.3 and not r['bull']:
            timing.append('shooting_star'); sc += 2

    # CONDITIONS (1pt each)
    if not pd.isna(r['ema8']) and not pd.isna(r['ema21']) and not pd.isna(r['ema55']):
        if r['ema8'] < r['ema21'] < r['ema55']: cond.append('ema_dn'); sc += 1
    if not pd.isna(r['st_dir']) and r['st_dir'] == -1 and 'st_flip_bear' not in timing:
        cond.append('st_bear'); sc += 1
    if not pd.isna(r['rsi']) and not pd.isna(p['rsi']):
        if 35 < r['rsi'] < 60 and r['rsi'] < p['rsi']: cond.append('rsi_dn'); sc += 1
    if not pd.isna(r['macd_h']) and not pd.isna(p['macd_h']):
        if r['macd_h'] < 0 and r['macd_h'] < p['macd_h']: cond.append('macd_dn'); sc += 1
    if not pd.isna(r['adx']) and r['adx'] > 20 and not pd.isna(r['pdi']) and not pd.isna(r['mdi']):
        if r['mdi'] > r['pdi']: cond.append('adx_bear'); sc += 1
    if not pd.isna(r['vol_r']) and r['vol_r'] > 1.3: cond.append('hi_vol'); sc += 1

    # PENALTIES
    if not pd.isna(r['rsi']) and r['rsi'] < 28: sc -= 3
    if not pd.isna(r['st_dir']) and r['st_dir'] == 1: sc -= 2

    return sc, timing + cond, len(timing)

# ============================================================
# EXIT CHECK
# ============================================================
def check_exit(df, idx, t):
    r = df.iloc[idx]
    hi = r['high']; lo = r['low']; cl = r['close']
    entry = t['entry_price']; side = t['side']
    peak = t['peak']

    if side == 'LONG':
        if hi > peak: t['peak'] = hi; peak = hi
        if lo <= t['sl']: return True, 'STOP_LOSS', t['sl']
        prof = (peak - entry) / entry
        if prof >= TRAILING_ACT:
            ts = peak * (1 - TRAILING_DIST)
            if ts > t.get('trail', 0): t['trail'] = ts
            if t.get('trail', 0) > 0 and lo <= t['trail']:
                return True, 'TRAILING', t['trail']
    else:  # SHORT
        if lo < peak: t['peak'] = lo; peak = lo
        if hi >= t['sl']: return True, 'STOP_LOSS', t['sl']
        prof = (entry - peak) / entry
        if prof >= TRAILING_ACT:
            ts = peak * (1 + TRAILING_DIST)
            if t.get('trail', 0) == 0 or ts < t['trail']: t['trail'] = ts
            if t.get('trail', 0) > 0 and hi >= t['trail']:
                return True, 'TRAILING', t['trail']

    # Reversal exit (only if in profit)
    if idx >= 2:
        p = df.iloc[idx-1]; rev = 0
        if side == 'LONG':
            pnl = (cl - entry) / entry
            if pnl > 0.003:
                if not pd.isna(r['st_dir']) and not pd.isna(p['st_dir']):
                    if p['st_dir'] == 1 and r['st_dir'] == -1: rev += 3
                if p['bull'] and not r['bull'] and r['open'] > p['close'] and cl < p['open']: rev += 2
                if not pd.isna(r['macd_l']) and not pd.isna(p['macd_l']):
                    if p['macd_l'] > p['macd_s'] and r['macd_l'] < r['macd_s']: rev += 2
        else:
            pnl = (entry - cl) / entry
            if pnl > 0.003:
                if not pd.isna(r['st_dir']) and not pd.isna(p['st_dir']):
                    if p['st_dir'] == -1 and r['st_dir'] == 1: rev += 3
                if not p['bull'] and r['bull'] and r['close'] > p['open'] and r['open'] < p['close']: rev += 2
                if not pd.isna(r['macd_l']) and not pd.isna(p['macd_l']):
                    if p['macd_l'] < p['macd_s'] and r['macd_l'] > r['macd_s']: rev += 2
        if rev >= 3: return True, 'REVERSAL', cl

    # Time exit
    et = t['entry_time']; ct = r['timestamp']
    if isinstance(ct, pd.Timestamp): ct = ct.to_pydatetime()
    if isinstance(et, pd.Timestamp): et = et.to_pydatetime()
    hrs = (ct - et).total_seconds() / 3600
    if hrs >= MAX_HOLD_HOURS: return True, 'MAX_HOLD', cl

    # Stagnant
    pnl_now = ((cl - entry)/entry if side == 'LONG' else (entry - cl)/entry)
    if hrs >= 6 and abs(pnl_now) < 0.002: return True, 'STAGNANT', cl

    return False, 'HOLD', 0

# ============================================================
# MAIN
# ============================================================
def run():
    print("\n" + "="*70)
    print("  🚀 SCALPING v7 - LONG+SHORT, QUALITY FILTER, 6 MONTHS")
    print("="*70)

    data = {}
    print("\n📊 Fetching 1H data (6 months)...")
    for sym in COINS:
        print(f"  {sym}...", end=" ", flush=True)
        df = fetch_klines(sym, '1h', 6)
        if len(df) > 100:
            df = prep(df); data[sym] = df; print(f"✓ {len(df)} bars")
        else:
            print(f"✗ {len(df)}")
    if not data: print("❌ No data!"); return

    bal = INITIAL_BALANCE; pos = {}; trades = []
    comm_total = 0; slip_total = 0; peak_bal = bal; max_dd = 0
    nb = min(len(d) for d in data.values())
    rej = {'low_vol':0, 'low_conf':0, 'no_timing':0, 'no_quality':0,
           'max_pos':0, 'has_pos':0, 'neutral':0}

    print(f"\n🏃 Running on {nb} bars × {len(data)} coins...")
    print(f"  SL={SL_PCT*100}% | Trail act={TRAILING_ACT*100}%/dist={TRAILING_DIST*100}%")
    print(f"  Confluence≥{MIN_CONFLUENCE} | Timing≥{MIN_TIMING} | Quality filter={REQUIRE_QUALITY}")
    print(f"  Max hold={MAX_HOLD_HOURS}h | Max pos={MAX_POSITIONS}")

    sig_count = 0
    for bi in range(60, nb):
        # EXITS
        for sym in list(pos.keys()):
            t = pos[sym]; df = data[sym]
            if bi >= len(df): continue
            ex, reason, price = check_exit(df, bi, t)
            if ex:
                side = t['side']
                if side == 'LONG':
                    ep = price * (1 - SLIPPAGE_PCT)
                    pnl_pct = (ep - t['entry_price']) / t['entry_price'] * 100
                else:
                    ep = price * (1 + SLIPPAGE_PCT)
                    pnl_pct = (t['entry_price'] - ep) / t['entry_price'] * 100

                cm = t['pos_val'] * COMMISSION_PCT; sl_c = t['pos_val'] * SLIPPAGE_PCT
                comm_total += cm; slip_total += sl_c
                pnl_dollar = t['pos_val'] * pnl_pct / 100 - cm - sl_c
                bal += pnl_dollar
                if bal > peak_bal: peak_bal = bal
                dd = (peak_bal - bal) / peak_bal * 100
                if dd > max_dd: max_dd = dd

                et2 = t['entry_time']; xt = df['timestamp'].iloc[bi]
                if isinstance(xt, pd.Timestamp): xt = xt.to_pydatetime()
                if isinstance(et2, pd.Timestamp): et2 = et2.to_pydatetime()
                hrs = (xt - et2).total_seconds() / 3600

                trades.append({
                    'symbol': sym, 'side': side, 'entry': t['entry_price'], 'exit': ep,
                    'pnl': pnl_dollar, 'pnl_pct': pnl_pct, 'entry_time': et2,
                    'exit_time': xt, 'hours': hrs, 'exit_type': reason,
                    'signals': t['signals'], 'strategy': t['strat'],
                })
                del pos[sym]

        # ENTRIES
        for sym, df in data.items():
            if bi >= len(df): continue
            sig_count += 1
            if sym in pos: rej['has_pos'] += 1; continue
            if len(pos) >= MAX_POSITIONS: rej['max_pos'] += 1; continue

            t4h = trend_4h(df, bi - 1)

            # Try LONG if UP or NEUTRAL
            if t4h in ('UP', 'NEUTRAL'):
                sc, sigs, tc = detect_long(df, bi - 1)
                if 'low_vol' in sigs: rej['low_vol'] += 1; continue
                if sc < MIN_CONFLUENCE: rej['low_conf'] += 1; continue
                if tc < MIN_TIMING: rej['no_timing'] += 1; continue
                if REQUIRE_QUALITY and tc < 2 and 'breakout' not in sigs:
                    rej['no_quality'] += 1; continue

                entry_p = df['open'].iloc[bi] * (1 + SLIPPAGE_PCT)
                pv = bal * POSITION_SIZE_PCT
                cm = pv * COMMISSION_PCT; sl_c = pv * SLIPPAGE_PCT
                comm_total += cm; slip_total += sl_c

                strat = 'mixed'
                for s in ['breakout','st_flip','macd_x','rsi_bounce','engulf','bb_bounce','hammer']:
                    if s in sigs: strat = s; break

                pos[sym] = {
                    'entry_price': entry_p, 'sl': entry_p * (1 - SL_PCT),
                    'pos_val': pv, 'entry_time': df['timestamp'].iloc[bi],
                    'peak': entry_p, 'signals': sigs, 'strat': strat,
                    'side': 'LONG', 'trail': 0,
                }
                continue

            # Try SHORT if DOWN
            if t4h == 'DOWN':
                sc, sigs, tc = detect_short(df, bi - 1)
                if 'low_vol' in sigs: rej['low_vol'] += 1; continue
                if sc < MIN_CONFLUENCE: rej['low_conf'] += 1; continue
                if tc < MIN_TIMING: rej['no_timing'] += 1; continue
                if REQUIRE_QUALITY and tc < 2 and 'breakdown' not in sigs:
                    rej['no_quality'] += 1; continue

                entry_p = df['open'].iloc[bi] * (1 - SLIPPAGE_PCT)
                pv = bal * POSITION_SIZE_PCT
                cm = pv * COMMISSION_PCT; sl_c = pv * SLIPPAGE_PCT
                comm_total += cm; slip_total += sl_c

                strat = 'mixed'
                for s in ['breakdown','st_flip_bear','macd_x_bear','rsi_reject','engulf_bear','bb_reject','shooting_star']:
                    if s in sigs: strat = s; break

                pos[sym] = {
                    'entry_price': entry_p, 'sl': entry_p * (1 + SL_PCT),
                    'pos_val': pv, 'entry_time': df['timestamp'].iloc[bi],
                    'peak': entry_p, 'signals': sigs, 'strat': strat,
                    'side': 'SHORT', 'trail': 0,
                }
                continue

            rej['neutral'] += 1

    # Force close
    for sym, t in pos.items():
        df = data[sym]; cl = df['close'].iloc[-1]
        side = t['side']
        if side == 'LONG': pnl_pct = (cl - t['entry_price'])/t['entry_price']*100
        else: pnl_pct = (t['entry_price'] - cl)/t['entry_price']*100
        pnl_d = t['pos_val'] * pnl_pct / 100
        bal += pnl_d
        et2 = t['entry_time']; xt = df['timestamp'].iloc[-1]
        if isinstance(xt, pd.Timestamp): xt = xt.to_pydatetime()
        if isinstance(et2, pd.Timestamp): et2 = et2.to_pydatetime()
        trades.append({'symbol':sym,'side':side,'entry':t['entry_price'],'exit':cl,
            'pnl':pnl_d,'pnl_pct':pnl_pct,'entry_time':et2,'exit_time':xt,
            'hours':(xt-et2).total_seconds()/3600,'exit_type':'FORCED',
            'signals':t['signals'],'strategy':t['strat']})

    # ============================================================
    # RESULTS
    # ============================================================
    print("\n" + "="*70)
    print("  📊 SCALPING v7 RESULTS")
    print("="*70)
    if not trades: print("  ❌ No trades!"); return

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    total_pnl = sum(t['pnl'] for t in trades)
    wr = len(wins)/len(trades)*100
    gp = sum(t['pnl'] for t in wins); gl = abs(sum(t['pnl'] for t in losses))
    pf = gp/gl if gl > 0 else float('inf')
    avg_w = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
    avg_l = np.mean([t['pnl_pct'] for t in losses]) if losses else 0
    avg_h = np.mean([t['hours'] for t in trades])

    ft = min(t['entry_time'] for t in trades)
    lt = max(t['exit_time'] for t in trades)
    days = (lt-ft).total_seconds()/86400
    tpd = len(trades)/days if days > 0 else 0

    longs = [t for t in trades if t['side']=='LONG']
    shorts = [t for t in trades if t['side']=='SHORT']

    print(f"\n  {'Initial:':<22} ${INITIAL_BALANCE:>10,.2f}")
    print(f"  {'Final:':<22} ${bal:>10,.2f}")
    print(f"  {'Total PnL:':<22} ${total_pnl:>10,.2f} ({total_pnl/INITIAL_BALANCE*100:+.2f}%)")
    print(f"  {'Commission:':<22} ${comm_total:>10,.2f}")
    print(f"  {'Slippage:':<22} ${slip_total:>10,.2f}")

    print(f"\n  {'Trades:':<22} {len(trades)}")
    print(f"  {'Win Rate:':<22} {wr:.1f}%")
    print(f"  {'Profit Factor:':<22} {pf:.2f}")
    print(f"  {'Avg Win:':<22} {avg_w:+.2f}%")
    print(f"  {'Avg Loss:':<22} {avg_l:+.2f}%")
    print(f"  {'Best:':<22} {max(t['pnl_pct'] for t in trades):+.2f}%")
    print(f"  {'Worst:':<22} {min(t['pnl_pct'] for t in trades):+.2f}%")
    print(f"  {'Avg Hold:':<22} {avg_h:.1f}h")
    print(f"  {'Max Drawdown:':<22} {max_dd:.2f}%")
    print(f"  {'Trades/Day:':<22} {tpd:.1f}")

    print(f"\n  --- LONG vs SHORT ---")
    if longs:
        lw = len([t for t in longs if t['pnl']>0])/len(longs)*100
        lp = sum(t['pnl'] for t in longs)
        print(f"  LONG:  {len(longs):>4} trades | WR: {lw:>5.1f}% | PnL: ${lp:>8.2f}")
    if shorts:
        sw = len([t for t in shorts if t['pnl']>0])/len(shorts)*100
        sp = sum(t['pnl'] for t in shorts)
        print(f"  SHORT: {len(shorts):>4} trades | WR: {sw:>5.1f}% | PnL: ${sp:>8.2f}")

    print(f"\n  --- BY STRATEGY ---")
    strats = {}
    for t in trades:
        s = t['strategy']
        if s not in strats: strats[s] = {'n':0,'w':0,'pnl':0}
        strats[s]['n'] += 1
        if t['pnl'] > 0: strats[s]['w'] += 1
        strats[s]['pnl'] += t['pnl']
    for k,v in sorted(strats.items(), key=lambda x:-x[1]['pnl']):
        w = v['w']/v['n']*100 if v['n'] else 0
        print(f"  {k:<22} | N={v['n']:>3} | WR: {w:>5.1f}% | PnL: ${v['pnl']:>8.2f}")

    print(f"\n  --- BY COIN ---")
    coins = {}
    for t in trades:
        s = t['symbol']
        if s not in coins: coins[s] = {'n':0,'w':0,'pnl':0}
        coins[s]['n'] += 1
        if t['pnl'] > 0: coins[s]['w'] += 1
        coins[s]['pnl'] += t['pnl']
    for k in sorted(coins.keys()):
        v = coins[k]; w = v['w']/v['n']*100 if v['n'] else 0
        print(f"  {k:<12} | N={v['n']:>3} | WR: {w:>5.1f}% | PnL: ${v['pnl']:>8.2f}")

    print(f"\n  --- BY CATEGORY ---")
    for cn, cc in CATEGORIES.items():
        ct = [t for t in trades if t['symbol'] in cc]
        if ct:
            cw = len([t for t in ct if t['pnl']>0])/len(ct)*100
            cp = sum(t['pnl'] for t in ct)
            ch = np.mean([t['hours'] for t in ct])
            print(f"  {cn:<12} | N={len(ct):>3} | WR: {cw:>5.1f}% | PnL: ${cp:>8.2f} | Hold: {ch:.0f}h")

    print(f"\n  --- EXIT REASONS ---")
    exits = {}
    for t in trades:
        e = t['exit_type']
        if e not in exits: exits[e] = {'n':0,'w':0,'pnl':0}
        exits[e]['n'] += 1
        if t['pnl'] > 0: exits[e]['w'] += 1
        exits[e]['pnl'] += t['pnl']
    for k,v in sorted(exits.items(), key=lambda x:-x[1]['n']):
        w = v['w']/v['n']*100 if v['n'] else 0
        print(f"  {k:<20} | N={v['n']:>4} | WR: {w:>5.1f}% | PnL: ${v['pnl']:>8.2f}")

    print(f"\n  --- REJECTIONS ---")
    print(f"  Signals analyzed: {sig_count}")
    for k,v in sorted(rej.items(), key=lambda x:-x[1]):
        if v > 0: print(f"  {k:<20}: {v:>5}")

    print(f"\n  --- MONTHLY ---")
    monthly = {}
    for t in trades:
        m = t['exit_time'].strftime('%Y-%m') if isinstance(t['exit_time'], datetime) else str(t['exit_time'])[:7]
        if m not in monthly: monthly[m] = {'n':0,'w':0,'pnl':0,'l':0,'s':0}
        monthly[m]['n'] += 1
        if t['pnl'] > 0: monthly[m]['w'] += 1
        monthly[m]['pnl'] += t['pnl']
        if t['side'] == 'LONG': monthly[m]['l'] += 1
        else: monthly[m]['s'] += 1
    for m in sorted(monthly.keys()):
        v = monthly[m]; w = v['w']/v['n']*100 if v['n'] else 0
        print(f"  {m} | N={v['n']:>3} (L:{v['l']}/S:{v['s']}) | WR: {w:>5.1f}% | PnL: ${v['pnl']:>8.2f}")

    print(f"\n  --- DAILY FREQ ---")
    daily = {}
    for t in trades:
        d = t['entry_time'].strftime('%Y-%m-%d') if isinstance(t['entry_time'], datetime) else str(t['entry_time'])[:10]
        daily[d] = daily.get(d, 0) + 1
    if daily:
        print(f"  Days with trades: {len(daily)}")
        print(f"  Avg/active day:   {np.mean(list(daily.values())):.1f}")
        print(f"  Max in one day:   {max(daily.values())}")

    # VERDICT
    print(f"\n  --- VERDICT ---")
    if wr >= 60: print(f"  ✅ WR {wr:.1f}% ≥ 60%")
    else: print(f"  ⚠️  WR {wr:.1f}% < 60%")
    if tpd >= 1: print(f"  ✅ {tpd:.1f} trades/day")
    else: print(f"  ⚠️  {tpd:.1f} trades/day < 1")
    if pf >= 1.3: print(f"  ✅ PROFITABLE PF={pf:.2f}")
    elif pf >= 1.0: print(f"  🟡 MARGINAL PF={pf:.2f}")
    else: print(f"  ❌ LOSING PF={pf:.2f}")
    print("="*70)

if __name__ == '__main__':
    run()
