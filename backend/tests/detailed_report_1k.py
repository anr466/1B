#!/usr/bin/env python3
"""
Detailed backtest report with $1,000 balance and $100 position size.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
import json
import urllib.request
from collections import Counter

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
            print(f"  {sym}: {len(df)} bars")

    INITIAL = 1000.0
    POS_SIZE = 100.0
    MAX_POS = 5
    COMM = 0.001
    SLIP = 0.0005

    balance = INITIAL
    positions = []
    trades = []
    peak_bal = INITIAL
    max_dd = 0
    daily_pnl = {}

    min_len = min(len(df) for df in all_data.values())
    days = min_len / 24.0

    for i in range(60, min_len):
        # ---- manage positions ----
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
            df_slice = df.iloc[:i+1]
            result = engine.check_exit_signal(df_slice, pos_data)
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
                pnl_raw = ((ep - pos['entry']) * pos['qty'] if pos['side'] == 'LONG'
                           else (pos['entry'] - ep) * pos['qty'])
                pnl = pnl_raw - abs(ep * pos['qty']) * COMM
                balance += pos['size'] + pnl

                day_key = str(df.iloc[i]['timestamp'].date())
                daily_pnl[day_key] = daily_pnl.get(day_key, 0) + pnl

                trades.append({
                    'symbol': pos['symbol'], 'side': pos['side'],
                    'entry': pos['entry'], 'exit': ep,
                    'pnl': pnl, 'pnl_pct': pnl / pos['size'] * 100,
                    'reason': result['reason'],
                    'hold': i - pos['bar'],
                    'entry_time': pos.get('entry_time', ''),
                    'exit_time': str(df.iloc[i]['timestamp']),
                })
                closed.append(pos)
        for p in closed:
            positions.remove(p)

        # ---- scan for entries ----
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
                    'entry_time': str(df.iloc[i]['timestamp']),
                })

        # ---- track DD ----
        unrealized = sum(
            ((all_data[p['symbol']].iloc[i]['close'] - p['entry']) * p['qty']
             if p['side'] == 'LONG'
             else (p['entry'] - all_data[p['symbol']].iloc[i]['close']) * p['qty'])
            for p in positions if i < len(all_data[p['symbol']])
        )
        eq = balance + sum(p['size'] for p in positions) + unrealized
        if eq > peak_bal:
            peak_bal = eq
        dd = (peak_bal - eq) / peak_bal if peak_bal > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # close remaining
    for pos in list(positions):
        df = all_data[pos['symbol']]
        ep = df.iloc[min_len - 1]['close']
        pnl = ((ep - pos['entry']) * pos['qty'] if pos['side'] == 'LONG'
               else (pos['entry'] - ep) * pos['qty']) - abs(ep * pos['qty']) * COMM
        balance += pos['size'] + pnl
        trades.append({
            'symbol': pos['symbol'], 'side': pos['side'],
            'entry': pos['entry'], 'exit': ep,
            'pnl': pnl, 'pnl_pct': pnl / pos['size'] * 100,
            'reason': 'FORCE_CLOSE', 'hold': min_len - 1 - pos['bar'],
            'entry_time': pos.get('entry_time', ''), 'exit_time': '',
        })
    positions.clear()

    # ============================================================
    # ANALYSIS
    # ============================================================
    tdf = pd.DataFrame(trades)
    w = tdf[tdf['pnl'] > 0]
    l = tdf[tdf['pnl'] <= 0]
    gp = w['pnl'].sum() if len(w) > 0 else 0
    gl = abs(l['pnl'].sum()) if len(l) > 0 else 0
    pf = gp / gl if gl > 0 else float('inf')
    total_pnl = tdf['pnl'].sum()
    holds = tdf['hold']
    reasons = tdf['reason'].value_counts()

    # Daily
    daily_vals = list(daily_pnl.values())
    pos_days = sum(1 for d in daily_vals if d > 0)
    neg_days = sum(1 for d in daily_vals if d < 0)

    # Trades per day
    trade_dates = []
    for _, t in tdf.iterrows():
        if t['entry_time']:
            trade_dates.append(str(pd.Timestamp(t['entry_time']).date()))
    tpd = Counter(trade_dates)
    tpd_vals = list(tpd.values()) if tpd else [0]

    # Date range
    first_date = tdf.iloc[0]['entry_time'][:10] if tdf.iloc[0]['entry_time'] else 'N/A'
    last_date = tdf.iloc[-1]['entry_time'][:10] if tdf.iloc[-1]['entry_time'] else 'N/A'

    avg_win_pnl = w['pnl'].mean() if len(w) > 0 else 0
    avg_win_pct = w['pnl_pct'].mean() if len(w) > 0 else 0
    avg_loss_pnl = l['pnl'].mean() if len(l) > 0 else 0
    avg_loss_pct = l['pnl_pct'].mean() if len(l) > 0 else 0

    daily_avg = total_pnl / days
    weekly_avg = daily_avg * 7
    monthly_avg = daily_avg * 30
    yearly_avg = daily_avg * 365

    # ============================================================
    # PRINT REPORT
    # ============================================================
    print()
    print("=" * 65)
    print("  DETAILED BACKTEST REPORT")
    print(f"  Balance: $1,000 | Position: $100 | Max {MAX_POS} concurrent")
    print("=" * 65)

    print(f"""
  Period:            {first_date} to {last_date} ({days:.0f} days)

  FINANCIAL RESULTS
  ─────────────────────────────────────────
  Starting Balance:  $1,000.00
  Ending Balance:    ${balance:,.2f}
  Total PnL:         ${total_pnl:+,.2f}
  Return:            {total_pnl/INITIAL*100:+.2f}%
  Max Drawdown:      {max_dd*100:.2f}%

  TRADE STATISTICS
  ─────────────────────────────────────────
  Total Trades:      {len(tdf)}
  Winners:           {len(w)} ({len(w)/len(tdf)*100:.1f}%)
  Losers:            {len(l)} ({len(l)/len(tdf)*100:.1f}%)
  Profit Factor:     {pf:.2f}
  Avg Win:           ${avg_win_pnl:+.2f} ({avg_win_pct:+.2f}%)
  Avg Loss:          ${avg_loss_pnl:+.2f} ({avg_loss_pct:+.2f}%)

  TRADE DURATION
  ─────────────────────────────────────────
  Average:           {holds.mean():.1f} hours
  Minimum:           {holds.min()} hour(s)
  Maximum:           {holds.max()} hours
  Median:            {holds.median():.0f} hour(s)

  DAILY ACTIVITY
  ─────────────────────────────────────────
  Avg trades/day:    {len(tdf)/days:.1f}
  Min trades/day:    {min(tpd_vals)}
  Max trades/day:    {max(tpd_vals)}
  Profitable days:   {pos_days}
  Losing days:       {neg_days}
  Avg daily PnL:     ${daily_avg:+.2f}""")

    print(f"""
  HOLD TIME DISTRIBUTION
  ─────────────────────────────────────────
  1 hour:            {len(holds[holds<=1]):>4} trades ({len(holds[holds<=1])/len(holds)*100:>5.1f}%)
  2-3 hours:         {len(holds[(holds>1)&(holds<=3)]):>4} trades ({len(holds[(holds>1)&(holds<=3)])/len(holds)*100:>5.1f}%)
  4-6 hours:         {len(holds[(holds>3)&(holds<=6)]):>4} trades ({len(holds[(holds>3)&(holds<=6)])/len(holds)*100:>5.1f}%)
  7-12 hours:        {len(holds[(holds>6)&(holds<=12)]):>4} trades ({len(holds[(holds>6)&(holds<=12)])/len(holds)*100:>5.1f}%)
  13+ hours:         {len(holds[holds>12]):>4} trades ({len(holds[holds>12])/len(holds)*100:>5.1f}%)""")

    print(f"""
  EXIT REASONS
  ─────────────────────────────────────────
  Trailing (target): {reasons.get('TRAILING',0):>4} ({reasons.get('TRAILING',0)/len(tdf)*100:.1f}%)
  Stop Loss:         {reasons.get('STOP_LOSS',0):>4} ({reasons.get('STOP_LOSS',0)/len(tdf)*100:.1f}%)
  Stagnant:          {reasons.get('STAGNANT',0):>4} ({reasons.get('STAGNANT',0)/len(tdf)*100:.1f}%)
  Max Hold:          {reasons.get('MAX_HOLD',0):>4}
  Force Close:       {reasons.get('FORCE_CLOSE',0):>4}""")

    # Per-symbol
    print(f"""
  PER-SYMBOL PERFORMANCE
  ─────────────────────────────────────────""")
    print(f"  {'Symbol':<12} {'Trades':>6} {'WR':>7} {'PnL':>10} {'Avg%':>8}")
    print(f"  {'-'*44}")
    for sym in sorted(tdf['symbol'].unique()):
        st = tdf[tdf['symbol'] == sym]
        sw = st[st['pnl'] > 0]
        wr = len(sw) / len(st) * 100
        pnl_sym = st['pnl'].sum()
        avg_sym = st['pnl_pct'].mean()
        marker = "+" if pnl_sym > 0 else "-"
        print(f"  {sym:<12} {len(st):>6} {wr:>6.1f}% ${pnl_sym:>+8.2f} {avg_sym:>+7.2f}%")

    # Projections
    print(f"""
  RETURN PROJECTIONS (based on {days:.0f}-day backtest)
  ─────────────────────────────────────────
  Daily:     ${daily_avg:+.2f}  ({daily_avg/INITIAL*100:+.3f}%)
  Weekly:    ${weekly_avg:+.2f}  ({weekly_avg/INITIAL*100:+.2f}%)
  Monthly:   ${monthly_avg:+.2f} ({monthly_avg/INITIAL*100:+.2f}%)
  Yearly:    ${yearly_avg:+.2f} ({yearly_avg/INITIAL*100:+.2f}%)

  NOTE: Projections assume consistent market conditions.
  Actual results may vary significantly.
""")
    print("=" * 65)


if __name__ == '__main__':
    main()
