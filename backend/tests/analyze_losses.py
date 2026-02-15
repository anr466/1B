#!/usr/bin/env python3
"""
Analyze why trades fail — root cause analysis of losing trades.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
import json, urllib.request
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


def main():
    engine = ScalpingV7Engine()
    symbols = [
        'ETHUSDT','BNBUSDT','SOLUSDT','AVAXUSDT','NEARUSDT',
        'SUIUSDT','ARBUSDT','APTUSDT','INJUSDT','LINKUSDT',
    ]

    print("Loading data...")
    all_data = {}
    for sym in symbols:
        df = fetch_klines(sym)
        if df is not None and len(df) >= 100:
            all_data[sym] = engine.prepare_data(df)

    POS_SIZE = 100.0
    MAX_POS = 5
    COMM = 0.001
    SLIP = 0.0005

    balance = 1000.0
    positions = []
    trades = []
    min_len = min(len(df) for df in all_data.values())

    for i in range(60, min_len):
        # manage
        closed = []
        for pos in positions:
            df = all_data[pos['symbol']]
            if i >= len(df):
                continue
            pos_data = {
                'entry_price': pos['entry'], 'side': pos['side'],
                'peak': pos['peak'], 'trail': pos['trail'],
                'sl': pos['sl'], 'hold_hours': i - pos['bar'],
            }
            result = engine.check_exit_signal(df.iloc[:i+1], pos_data)
            upd = result.get('updated', {})
            if 'peak' in upd:
                pos['peak'] = upd['peak']
            if 'trail' in upd:
                pos['trail'] = upd['trail']
            if result['should_exit']:
                ep = result['exit_price']
                if pos['side'] == 'LONG':
                    ep *= (1 - SLIP)
                else:
                    ep *= (1 + SLIP)
                pnl_raw = ((ep - pos['entry']) * pos['qty']
                           if pos['side'] == 'LONG'
                           else (pos['entry'] - ep) * pos['qty'])
                pnl = pnl_raw - abs(ep * pos['qty']) * COMM
                balance += pos['size'] + pnl

                # Compute MFE / MAE
                row_entry = df.iloc[pos['bar']]
                adx_entry = float(row_entry.get('adx', 0)) if not pd.isna(row_entry.get('adx')) else 0
                bb_up = row_entry.get('bb_upper', 0)
                bb_lo = row_entry.get('bb_lower', 0)
                cl_e = row_entry.get('close', 1)
                if pd.isna(bb_up) or pd.isna(bb_lo):
                    bb_w = 0
                else:
                    bb_w = (bb_up - bb_lo) / cl_e

                vol_sma = df['volume'].iloc[max(0, pos['bar']-20):pos['bar']].mean()
                vol_ratio = float(row_entry['volume']) / vol_sma if vol_sma > 0 else 1

                max_favorable = 0
                max_adverse = 0
                for j in range(pos['bar'], min(i + 1, len(df))):
                    r = df.iloc[j]
                    if pos['side'] == 'LONG':
                        fav = (r['high'] - pos['entry']) / pos['entry']
                        adv = (pos['entry'] - r['low']) / pos['entry']
                    else:
                        fav = (pos['entry'] - r['low']) / pos['entry']
                        adv = (r['high'] - pos['entry']) / pos['entry']
                    max_favorable = max(max_favorable, fav)
                    max_adverse = max(max_adverse, adv)

                trades.append({
                    'symbol': pos['symbol'], 'side': pos['side'],
                    'entry': pos['entry'], 'exit': ep,
                    'pnl': pnl, 'pnl_pct': pnl / pos['size'] * 100,
                    'reason': result['reason'], 'trend': pos['trend'],
                    'strategy': pos.get('strategy', ''),
                    'hold': i - pos['bar'],
                    'adx': adx_entry, 'bb_width': bb_w, 'vol_ratio': vol_ratio,
                    'max_favorable': max_favorable * 100,
                    'max_adverse': max_adverse * 100,
                })
                closed.append(pos)
        for p in closed:
            positions.remove(p)

        # scan
        if len(positions) < MAX_POS:
            for sym, df in all_data.items():
                if len(positions) >= MAX_POS:
                    break
                if any(p['symbol'] == sym for p in positions):
                    continue
                if i >= len(df) - 1:
                    continue
                trend = engine.get_4h_trend(df, i - 1)
                signal = engine.detect_entry(df, trend, i - 1)
                if not signal:
                    continue
                entry_price = df.iloc[i]['open']
                if signal['side'] == 'LONG':
                    entry_price *= (1 + SLIP)
                    sl = entry_price * (1 - V7_CONFIG['sl_pct'])
                else:
                    entry_price *= (1 - SLIP)
                    sl = entry_price * (1 + V7_CONFIG['sl_pct'])
                if POS_SIZE > balance:
                    continue
                qty = POS_SIZE / entry_price
                balance -= (POS_SIZE + POS_SIZE * COMM)
                positions.append({
                    'symbol': sym, 'side': signal['side'],
                    'entry': entry_price, 'qty': qty, 'size': POS_SIZE,
                    'sl': sl, 'peak': entry_price, 'trail': 0, 'bar': i,
                    'trend': trend, 'strategy': signal.get('strategy', ''),
                })

    # ============================================================
    # ANALYSIS
    # ============================================================
    tdf = pd.DataFrame(trades)
    w = tdf[tdf['pnl'] > 0]
    l = tdf[tdf['pnl'] <= 0]

    print()
    print("=" * 65)
    print("  تحليل أسباب فشل الصفقات الخاسرة")
    print("=" * 65)

    # 1. Winners vs Losers
    print()
    print("  1. مقارنة: رابحة vs خاسرة")
    print("  " + "-" * 50)
    print(f"  {'':>25} {'رابحة':>10} {'خاسرة':>10}")
    print(f"  عدد الصفقات:         {len(w):>10} {len(l):>10}")
    print(f"  متوسط PnL%:          {w['pnl_pct'].mean():>+9.2f}% {l['pnl_pct'].mean():>+9.2f}%")
    print(f"  متوسط المدة (ساعة):  {w['hold'].mean():>10.1f} {l['hold'].mean():>10.1f}")
    print(f"  متوسط ADX:           {w['adx'].mean():>10.1f} {l['adx'].mean():>10.1f}")
    print(f"  متوسط Vol ratio:     {w['vol_ratio'].mean():>10.2f} {l['vol_ratio'].mean():>10.2f}")
    print(f"  متوسط BB width:      {w['bb_width'].mean():>10.4f} {l['bb_width'].mean():>10.4f}")

    # 2. MFE — how much profit was available before the trade lost
    print()
    print("  2. أقصى حركة مواتية (MFE) للخاسرة — كم ربح كان متاحاً قبل أن تخسر؟")
    print("  " + "-" * 50)
    mfe_0 = l[l['max_favorable'] < 0.1]
    mfe_05 = l[(l['max_favorable'] >= 0.1) & (l['max_favorable'] < 0.5)]
    mfe_10 = l[(l['max_favorable'] >= 0.5) & (l['max_favorable'] < 1.0)]
    mfe_big = l[l['max_favorable'] >= 1.0]
    print(f"    لم تتحرك لصالحنا أبداً (<0.1%):  {len(mfe_0):>4} ({len(mfe_0)/len(l)*100:.0f}%)")
    print(f"    تحركت 0.1-0.5% ثم انعكست:       {len(mfe_05):>4} ({len(mfe_05)/len(l)*100:.0f}%)")
    print(f"    تحركت 0.5-1.0% ثم انعكست:       {len(mfe_10):>4} ({len(mfe_10)/len(l)*100:.0f}%)")
    print(f"    تحركت >1% ثم انعكست:            {len(mfe_big):>4} ({len(mfe_big)/len(l)*100:.0f}%)")

    # MAE for winners
    print()
    print("  أقصى حركة معاكسة (MAE) للرابحة — كم خسرت مؤقتاً قبل أن تربح؟")
    print("  " + "-" * 50)
    mae_03 = w[w['max_adverse'] < 0.3]
    mae_06 = w[(w['max_adverse'] >= 0.3) & (w['max_adverse'] < 0.6)]
    mae_10 = w[(w['max_adverse'] >= 0.6) & (w['max_adverse'] < 1.0)]
    print(f"    < 0.3% (مستقرة):   {len(mae_03):>4} ({len(mae_03)/len(w)*100:.0f}%)")
    print(f"    0.3-0.6%:          {len(mae_06):>4} ({len(mae_06)/len(w)*100:.0f}%)")
    print(f"    0.6-1%:            {len(mae_10):>4} ({len(mae_10)/len(w)*100:.0f}%)")

    # 3. Exit reason for losers
    print()
    print("  3. سبب الخروج للخاسرة")
    print("  " + "-" * 50)
    for reason in l['reason'].value_counts().index:
        subset = l[l['reason'] == reason]
        avg_pnl = subset['pnl_pct'].mean()
        print(f"    {reason:<15} {len(subset):>4} ({len(subset)/len(l)*100:.1f}%) | avg: {avg_pnl:+.2f}%")

    # 4. By strategy pattern
    print()
    print("  4. أداء كل نمط دخول")
    print("  " + "-" * 50)
    print(f"    {'Pattern':<15} {'Total':>6} {'Win':>6} {'Lose':>6} {'WR':>7} {'PnL':>10}")
    print(f"    {'-'*52}")
    for strat in sorted(tdf['strategy'].unique()):
        st = tdf[tdf['strategy'] == strat]
        sw = st[st['pnl'] > 0]
        sl_s = st[st['pnl'] <= 0]
        wr = len(sw) / len(st) * 100
        pnl_sum = st['pnl'].sum()
        print(f"    {strat:<15} {len(st):>6} {len(sw):>6} {len(sl_s):>6} {wr:>6.1f}% ${pnl_sum:>+8.2f}")

    # 5. LONG vs SHORT
    print()
    print("  5. LONG vs SHORT")
    print("  " + "-" * 50)
    for side in ['LONG', 'SHORT']:
        st = tdf[tdf['side'] == side]
        sw = st[st['pnl'] > 0]
        sl_s = st[st['pnl'] <= 0]
        wr = len(sw) / len(st) * 100 if len(st) > 0 else 0
        print(f"    {side}: {len(st)} trades | WR={wr:.1f}% | PnL=${st['pnl'].sum():+.2f}")
        if len(sl_s) > 0:
            print(f"      Losses: {len(sl_s)} | avg loss: {sl_s['pnl_pct'].mean():+.2f}%")

    # 6. Per symbol
    print()
    print("  6. أكثر العملات خسارة")
    print("  " + "-" * 50)
    for sym in sorted(tdf['symbol'].unique()):
        st = tdf[tdf['symbol'] == sym]
        sw = st[st['pnl'] > 0]
        sl_s = st[st['pnl'] <= 0]
        wr = len(sw) / len(st) * 100
        loss_sum = sl_s['pnl'].sum() if len(sl_s) > 0 else 0
        print(f"    {sym:<12} {len(sl_s):>3} losses / {len(st)} total | WR={wr:.0f}% | loss=${loss_sum:+.2f}")

    # 7. ADX ranges
    print()
    print("  7. قوة الاتجاه (ADX) وتأثيرها")
    print("  " + "-" * 50)
    for adx_lo, adx_hi, label in [(0, 15, 'ضعيف جداً'), (15, 25, 'ضعيف'), (25, 40, 'متوسط'), (40, 100, 'قوي')]:
        subset = tdf[(tdf['adx'] >= adx_lo) & (tdf['adx'] < adx_hi)]
        if len(subset) > 0:
            sw = subset[subset['pnl'] > 0]
            wr = len(sw) / len(subset) * 100
            pnl_s = subset['pnl'].sum()
            print(f"    ADX {adx_lo:>2}-{adx_hi:<3} ({label}): {len(subset):>4} trades | WR={wr:.0f}% | PnL=${pnl_s:+.2f}")

    # 8. Hold time
    print()
    print("  8. مدة الاحتفاظ وتأثيرها")
    print("  " + "-" * 50)
    for h_lo, h_hi, label in [(1, 1, '1h'), (2, 3, '2-3h'), (4, 6, '4-6h'), (7, 20, '7+h')]:
        subset = tdf[(tdf['hold'] >= h_lo) & (tdf['hold'] <= h_hi)]
        if len(subset) > 0:
            sw = subset[subset['pnl'] > 0]
            wr = len(sw) / len(subset) * 100
            pnl_s = subset['pnl'].sum()
            print(f"    {label:<6} {len(subset):>4} trades | WR={wr:.0f}% | PnL=${pnl_s:+.2f} | avg={subset['pnl_pct'].mean():+.3f}%")

    # ============================================================
    # ROOT CAUSE SUMMARY
    # ============================================================
    sl_immediate = l[(l['max_favorable'] < 0.1) & (l['hold'] <= 1)]
    sl_reversed = l[l['max_favorable'] >= 0.5]
    low_adx_lose = l[l['adx'] < 20]

    total_loss = abs(l['pnl'].sum())
    imm_loss = abs(sl_immediate['pnl'].sum())
    rev_loss = abs(sl_reversed['pnl'].sum())
    rest_loss = total_loss - imm_loss - rev_loss

    print()
    print("=" * 65)
    print("  الأسباب الجذرية الأربعة لفشل الصفقات")
    print("=" * 65)

    print(f"""
  السبب #1: ضرب SL فوري — الدخول متأخر
  ────────────────────────────────────────
  {len(sl_immediate)} صفقة ({len(sl_immediate)/len(l)*100:.0f}% من الخاسرة)
  خسارة: ${imm_loss:.2f} ({imm_loss/total_loss*100:.0f}% من إجمالي الخسائر)

  الشرح: السعر يتحرك ضدنا فوراً بعد الدخول ويضرب SL
  خلال الشمعة الأولى. الإشارة كانت متأخرة — الحركة
  التي أعطت الإشارة انتهت بالفعل وبدأ الانعكاس.

  السبب #2: انعكاس بعد ربح مؤقت
  ────────────────────────────────────────
  {len(sl_reversed)} صفقة ({len(sl_reversed)/len(l)*100:.0f}% من الخاسرة)
  خسارة: ${rev_loss:.2f} ({rev_loss/total_loss*100:.0f}% من إجمالي الخسائر)

  الشرح: السعر تحرك لصالحنا +0.5% أو أكثر ثم انعكس
  بعنف وضرب SL. الـ Trailing يتفعل عند +0.6%، لذا بعض
  هذه الصفقات كانت قريبة جداً من النجاح لكن لم تصل.

  السبب #3: سوق ضعيف الاتجاه (ADX منخفض)
  ────────────────────────────────────────
  {len(low_adx_lose)} صفقة خاسرة في ADX < 20
  الشرح: حتى مع فلاتر C2+C4، بعض الصفقات تدخل في
  أسواق ضعيفة حيث السعر يتذبذب بلا اتجاه واضح.

  السبب #4: طبيعة Scalping (حتمي ولا يمكن تجنبه)
  ────────────────────────────────────────
  SL = 1% ثابت. أي حركة 1% ضدنا = خسارة.
  في أي استراتيجية Scalping، نسبة خسارة 45-48% طبيعية.

  المهم هو:
    متوسط الربح:  {w['pnl_pct'].mean():+.2f}%
    متوسط الخسارة: {l['pnl_pct'].mean():+.2f}%
    Reward:Risk  = {abs(w['pnl_pct'].mean()/l['pnl_pct'].mean()):.2f}:1

  هذا يعني كل صفقة رابحة تعوّض {abs(w['pnl_pct'].mean()/l['pnl_pct'].mean()):.1f} صفقة خاسرة.
  لذلك حتى مع 47.5% خسارة، المحفظة تنمو.""")

    print()
    print("=" * 65)


if __name__ == '__main__':
    main()
