#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 Extended Multi-Coin Backtest + Benchmark Comparison
=======================================================
Tests the CURRENT V8 production engine on an expanded coin universe:
  • Group A — Original 14 coins (same as previous benchmark, direct comparison)
  • Group B — 12 new coins (first run, broadening coverage)

Previous benchmark (stored in tests/backtest_results/production_validation.json):
  V8 PRODUCTION  WR=62.8%  PF=1.64  Trades=3098  PnL=+$623.65  14/14 profitable

Usage:
  python tests/v8_extended_backtest.py
  python tests/v8_extended_backtest.py --days 30
  python tests/v8_extended_backtest.py --days 90 --balance 5000
"""

import sys
import os
import json
import time
import math
import argparse
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from backend.strategies.scalping_v8_engine import ScalpingV8Engine, V8_CONFIG

logging.basicConfig(level=logging.WARNING, format='%(message)s')
logger = logging.getLogger(__name__)

RESULTS_DIR = os.path.join(PROJECT_ROOT, 'tests', 'backtest_results')

# ──────────────────────────────────────────────────────────────
#  COIN UNIVERSE
# ──────────────────────────────────────────────────────────────
ORIGINAL_14 = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'AVAXUSDT', 'NEARUSDT', 'SUIUSDT', 'ARBUSDT', 'APTUSDT',
    'INJUSDT', 'LINKUSDT', 'PEPEUSDT', 'OPUSDT',
]

NEW_COINS = [
    'DOGEUSDT', 'ADAUSDT', 'DOTUSDT', 'MATICUSDT', 'ATOMUSDT',
    'LTCUSDT',  'UNIUSDT', 'AAVEUSDT', 'TIAUSDT',  'SEIUSDT',
    'WIFUSDT',  'RNDRUSDT',
]

ALL_SYMBOLS = ORIGINAL_14 + NEW_COINS   # 26 coins total

# ──────────────────────────────────────────────────────────────
#  PREVIOUS BENCHMARK  (from production_validation.json)
# ──────────────────────────────────────────────────────────────
PREV_BENCHMARK_PATH = os.path.join(RESULTS_DIR, 'production_validation.json')

_HARDCODED_PREV = {
    'label':   'V8 PRODUCTION (مارس 2026)',
    'coins':   14,
    'days':    60,
    'n':       3098,
    'wr':      62.8,
    'pf':      1.64,
    'pnl':     623.65,
    'aw':      1.472,
    'al':     -1.309,
    'rr':      1.12,
    'sym_ok':  14,
    'exits': {
        'TRAILING':       {'count': 2280, 'pnl':  1577, 'wins': 1945},
        'STOP_LOSS':      {'count':  215, 'pnl':  -385, 'wins':    0},
        'SMART_CUT_1':    {'count':  243, 'pnl':  -254, 'wins':    0},
        'SMART_CUT_LATE': {'count':  174, 'pnl':  -138, 'wins':    0},
        'SMART_CUT_2':    {'count':  161, 'pnl':  -170, 'wins':    0},
        'STAGNANT':       {'count':   12, 'pnl':    -1, 'wins':    0},
    },
    'strats': {
        'trend_cont_short': {'count': 1210, 'pnl':  259, 'wins': 787},
        'breakdown':        {'count':  522, 'pnl':  165, 'wins': 355},
        'breakout':         {'count':  833, 'pnl':  121, 'wins': 474},
        'trend_cont':       {'count':  526, 'pnl':   70, 'wins': 321},
    },
}


def _load_previous_benchmark() -> Dict:
    """Load previous V8 benchmark from JSON, fallback to hardcoded."""
    try:
        with open(PREV_BENCHMARK_PATH) as f:
            raw = json.load(f)
        v8 = raw.get('V8_PRODUCTION', {})
        if v8:
            return {
                'label':   'V8 PRODUCTION (production_validation.json)',
                'coins':   14,
                'days':    60,
                'n':       v8.get('n',   _HARDCODED_PREV['n']),
                'wr':      v8.get('wr',  _HARDCODED_PREV['wr']),
                'pf':      v8.get('pf',  _HARDCODED_PREV['pf']),
                'pnl':     v8.get('pnl', _HARDCODED_PREV['pnl']),
                'aw':      v8.get('aw',  _HARDCODED_PREV['aw']),
                'al':      v8.get('al',  _HARDCODED_PREV['al']),
                'rr':      v8.get('rr',  _HARDCODED_PREV['rr']),
                'sym_ok':  v8.get('sym_ok', 14),
                'exits':   v8.get('exits',  _HARDCODED_PREV['exits']),
                'strats':  v8.get('strats', _HARDCODED_PREV['strats']),
            }
    except Exception:
        pass
    return _HARDCODED_PREV


# ──────────────────────────────────────────────────────────────
#  DATA FETCHER — Binance public API
# ──────────────────────────────────────────────────────────────
def fetch_binance_klines(symbol: str, interval: str = '1h',
                         days: int = 60, limit_per_req: int = 1000) -> pd.DataFrame:
    url = 'https://api.binance.com/api/v3/klines'
    end_time   = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

    all_data = []
    current_start = start_time
    while current_start < end_time:
        params = {
            'symbol':    symbol,
            'interval':  interval,
            'startTime': current_start,
            'endTime':   end_time,
            'limit':     limit_per_req,
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f'  ⚠️  {symbol}: network error — {e}')
            break
        if not data:
            break
        all_data.extend(data)
        current_start = data[-1][0] + 1
        if len(data) < limit_per_req:
            break
        time.sleep(0.15)

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore',
    ])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = (df.drop_duplicates(subset=['timestamp'])
            .sort_values('timestamp')
            .reset_index(drop=True))
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]


# ──────────────────────────────────────────────────────────────
#  V8 REALISTIC BACKTESTER
# ──────────────────────────────────────────────────────────────
class V8RealisticBacktester:
    """Mirrors live V8 trading behavior exactly."""

    def __init__(self, config: Dict = None, initial_balance: float = 1000.0):
        self.config          = {**V8_CONFIG, **(config or {})}
        self.engine          = ScalpingV8Engine(self.config)
        self.initial_balance = initial_balance

        self.commission_pct    = self.config.get('commission_pct',    0.001)
        self.slippage_pct      = self.config.get('slippage_pct',      0.0005)
        self.position_size_pct = self.config.get('position_size_pct', 0.06)
        self.max_positions     = self.config.get('max_positions',      5)

        self._reset_state()

    def _reset_state(self):
        self.balance        = self.initial_balance
        self.open_positions: List[Dict] = []
        self.closed_trades:  List[Dict] = []
        self.equity_curve:   List[Dict] = []

    # ── ENTRY ──────────────────────────────────────────────────
    def _open_position(self, symbol, signal, entry_price, bar_time, bar_idx):
        position_value = self.initial_balance * self.position_size_pct
        if position_value < 5:
            return
        quantity         = position_value / entry_price
        entry_commission = position_value * self.commission_pct
        self.balance    -= entry_commission

        sl = signal.get('stop_loss', 0)
        if sl <= 0:
            if signal['side'] == 'LONG':
                sl = entry_price * (1 - self.config['sl_pct'])
            else:
                sl = entry_price * (1 + self.config['sl_pct'])

        self.open_positions.append({
            'symbol':           symbol,
            'side':             signal['side'],
            'entry_price':      entry_price,
            'quantity':         quantity,
            'position_value':   position_value,
            'stop_loss':        sl,
            'trailing_stop':    0.0,
            'peak':             entry_price,
            'entry_time':       bar_time,
            'entry_bar':        bar_idx,
            'entry_commission': entry_commission,
            'signal_strategy':  signal.get('strategy', 'unknown'),
            'signal_score':     signal.get('score', 0),
            'hold_bars':        0,
        })

    # ── EXIT ───────────────────────────────────────────────────
    def _check_exits(self, df: pd.DataFrame, bar_idx: int, symbol: str):
        bar       = df.iloc[bar_idx]
        low_price = bar['low']
        high_price= bar['high']
        close     = bar['close']
        bar_time  = bar.get('timestamp', bar_idx)

        remaining = []
        for pos in self.open_positions:
            if pos['symbol'] != symbol:
                remaining.append(pos)
                continue

            side           = pos['side']
            entry_price    = pos['entry_price']
            peak           = pos['peak']
            trail_stop     = pos['trailing_stop']
            sl             = pos['stop_loss']
            hold_bars      = pos['hold_bars']
            pos['hold_bars'] = hold_bars + 1

            # update peak
            if side == 'LONG':
                pos['peak'] = max(peak, high_price)
            else:
                pos['peak'] = min(peak, low_price)
            peak = pos['peak']

            # price movement
            if side == 'LONG':
                pnl_pct = (close - entry_price) / entry_price
                peak_pct= (peak  - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - close) / entry_price
                peak_pct= (entry_price - peak)  / entry_price

            cfg = self.config
            exit_reason = None
            exit_price  = close

            # 1. Hard SL
            if side == 'LONG'  and low_price  <= sl:
                exit_reason = 'STOP_LOSS'
                exit_price  = sl
            elif side == 'SHORT' and high_price >= sl:
                exit_reason = 'STOP_LOSS'
                exit_price  = sl

            # 2. Breakeven
            if exit_reason is None:
                be = cfg.get('breakeven_trigger', 0.003)
                if peak_pct >= be and trail_stop == 0:
                    if side == 'LONG':
                        pos['trailing_stop'] = entry_price * (1 + 0.0001)
                    else:
                        pos['trailing_stop'] = entry_price * (1 - 0.0001)
                    trail_stop = pos['trailing_stop']

            # 3. Progressive trailing
            if exit_reason is None and peak_pct >= cfg.get('trailing_activation', 0.001):
                progressive = cfg.get('v8_progressive_trail', {})
                trail_dist  = cfg.get('trailing_distance', 0.002)
                for threshold in sorted(progressive.keys(), reverse=True):
                    if peak_pct >= threshold:
                        trail_dist = progressive[threshold]
                        break
                if side == 'LONG':
                    new_trail = peak * (1 - trail_dist)
                    pos['trailing_stop'] = max(trail_stop, new_trail)
                else:
                    new_trail = peak * (1 + trail_dist)
                    pos['trailing_stop'] = (min(trail_stop, new_trail)
                                            if trail_stop > 0 else new_trail)
                trail_stop = pos['trailing_stop']

            # 4. Trail hit
            if exit_reason is None and trail_stop > 0:
                if side == 'LONG'  and low_price  <= trail_stop:
                    exit_reason = 'TRAILING'
                    exit_price  = trail_stop
                elif side == 'SHORT' and high_price >= trail_stop:
                    exit_reason = 'TRAILING'
                    exit_price  = trail_stop

            # 5. Smart Cut 1 — immediate reversal
            if exit_reason is None:
                sc1 = cfg.get('v8_smart_cut_1', {})
                sc1_bars = sc1.get('bars', 1)
                sc1_loss = sc1.get('loss', -0.001)
                if hold_bars <= sc1_bars and pnl_pct <= sc1_loss:
                    momentum_col = 'macd_hist' if 'macd_hist' in bar.index else None
                    momentum_bad = True
                    if momentum_col and sc1.get('momentum') is not None:
                        momentum_bad = bar[momentum_col] <= sc1.get('momentum', -2)
                    if momentum_bad:
                        exit_reason = 'SMART_CUT_1'

            # 6. Smart Cut 2
            if exit_reason is None:
                sc2 = cfg.get('v8_smart_cut_2', {})
                if hold_bars <= sc2.get('bars', 2) and pnl_pct <= sc2.get('loss', -0.0015):
                    exit_reason = 'SMART_CUT_2'

            # 7. Smart Cut 3 (late)
            if exit_reason is None:
                sc3 = cfg.get('v8_smart_cut_3', {})
                if hold_bars <= sc3.get('bars', 3) and pnl_pct <= sc3.get('loss', -0.002):
                    exit_reason = 'SMART_CUT_LATE'

            # 8. Stagnant
            if exit_reason is None:
                stagnant_h   = cfg.get('stagnant_hours', 2)
                stagnant_thr = cfg.get('stagnant_threshold', 0.0005)
                if hold_bars >= stagnant_h and abs(pnl_pct) <= stagnant_thr:
                    exit_reason = 'STAGNANT'

            # 9. Max hold
            if exit_reason is None:
                max_hold = cfg.get('max_hold_hours', 6)
                if hold_bars >= max_hold:
                    exit_reason = 'MAX_HOLD'

            if exit_reason:
                self._close_position(pos, exit_price, bar_time, exit_reason)
            else:
                remaining.append(pos)

        self.open_positions = remaining

    def _close_position(self, pos, exit_price, bar_time, exit_reason):
        side          = pos['side']
        entry_price   = pos['entry_price']
        quantity      = pos['quantity']
        position_value= pos['position_value']

        if side == 'LONG':
            exit_price *= (1 - self.slippage_pct)
            raw_pnl     = (exit_price - entry_price) * quantity
        else:
            exit_price *= (1 + self.slippage_pct)
            raw_pnl     = (entry_price - exit_price) * quantity

        exit_commission = abs(exit_price * quantity) * self.commission_pct
        net_pnl         = raw_pnl - exit_commission
        self.balance   += net_pnl
        total_commission= pos['entry_commission'] + exit_commission

        pnl_pct = net_pnl / position_value * 100

        self.closed_trades.append({
            'symbol':       pos['symbol'],
            'side':         side,
            'entry_price':  entry_price,
            'exit_price':   exit_price,
            'pnl_dollar':   round(net_pnl, 4),
            'pnl_pct':      round(pnl_pct, 4),
            'is_win':       net_pnl > 0,
            'exit_reason':  exit_reason,
            'strategy':     pos['signal_strategy'],
            'hold_bars':    pos['hold_bars'],
            'commission':   round(total_commission, 4),
        })

    def _calc_unrealized_pnl(self, price: float) -> float:
        total = 0.0
        for pos in self.open_positions:
            qty = pos['quantity']
            if pos['side'] == 'LONG':
                total += (price - pos['entry_price']) * qty
            else:
                total += (pos['entry_price'] - price) * qty
        return total

    def _calc_max_drawdown(self) -> float:
        if not self.equity_curve:
            return 0.0
        peak   = self.equity_curve[0]['equity']
        max_dd = 0.0
        for pt in self.equity_curve:
            eq = pt['equity']
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return max_dd

    # ── MAIN RUN ───────────────────────────────────────────────
    def run(self, symbol: str, df: pd.DataFrame) -> Dict:
        self._reset_state()
        if df is None or len(df) < 80:
            return {'symbol': symbol, 'total_trades': 0,
                    'error': 'insufficient data'}

        df_prep = self.engine.prepare_data(df)
        if df_prep is None:
            return {'symbol': symbol, 'total_trades': 0,
                    'error': 'prepare_data failed'}

        for i in range(60, len(df_prep)):
            bar = df_prep.iloc[i]
            unr = self._calc_unrealized_pnl(bar['close'])
            self.equity_curve.append({
                'time':          bar.get('timestamp', i),
                'balance':       self.balance,
                'equity':        self.balance + unr,
                'open_positions': len(self.open_positions),
            })

            self._check_exits(df_prep, i, symbol)

            if len(self.open_positions) < self.max_positions:
                trend  = self.engine.get_4h_trend(df_prep, i - 1)
                signal = self.engine.detect_entry(df_prep, trend, i - 1)
                if signal:
                    ep = bar['open']
                    ep *= (1 + self.slippage_pct) if signal['side'] == 'LONG' \
                         else (1 - self.slippage_pct)
                    self._open_position(symbol, signal, ep,
                                        bar.get('timestamp', i), i)

        # Force-close any remaining open positions at last close
        if self.open_positions and len(df_prep) > 0:
            last_bar = df_prep.iloc[-1]
            for pos in list(self.open_positions):
                self._close_position(pos, last_bar['close'],
                                     last_bar.get('timestamp'), 'END_OF_DATA')
            self.open_positions = []

        return self._generate_symbol_report(symbol)

    def _generate_symbol_report(self, symbol: str) -> Dict:
        trades = [t for t in self.closed_trades if t['symbol'] == symbol]
        if not trades:
            return {'symbol': symbol, 'total_trades': 0, 'trades': []}

        wins   = [t for t in trades if t['is_win']]
        losses = [t for t in trades if not t['is_win']]

        total_pnl    = sum(t['pnl_dollar'] for t in trades)
        gross_profit = sum(t['pnl_dollar'] for t in wins)   if wins   else 0
        gross_loss   = abs(sum(t['pnl_dollar'] for t in losses)) if losses else 0.001

        exit_reasons = defaultdict(lambda: {'count': 0, 'pnl': 0.0, 'wins': 0})
        strat_stats  = defaultdict(lambda: {'count': 0, 'pnl': 0.0, 'wins': 0})
        for t in trades:
            r = t['exit_reason']
            exit_reasons[r]['count'] += 1
            exit_reasons[r]['pnl']   += t['pnl_dollar']
            if t['is_win']:
                exit_reasons[r]['wins'] += 1
            s = t['strategy']
            strat_stats[s]['count'] += 1
            strat_stats[s]['pnl']   += t['pnl_dollar']
            if t['is_win']:
                strat_stats[s]['wins'] += 1

        return {
            'symbol':        symbol,
            'total_trades':  len(trades),
            'wins':          len(wins),
            'losses':        len(losses),
            'win_rate':      round(len(wins) / len(trades) * 100, 1),
            'total_pnl':     round(total_pnl, 2),
            'total_pnl_pct': round(total_pnl / self.initial_balance * 100, 2),
            'profit_factor': round(gross_profit / gross_loss, 2),
            'avg_win_pct':   round(float(np.mean([t['pnl_pct'] for t in wins])), 3)
                             if wins   else 0.0,
            'avg_loss_pct':  round(float(np.mean([t['pnl_pct'] for t in losses])), 3)
                             if losses else 0.0,
            'max_drawdown_pct': round(self._calc_max_drawdown() * 100, 2),
            'total_commission': round(sum(t['commission'] for t in trades), 2),
            'exit_reasons':  {k: dict(v) for k, v in exit_reasons.items()},
            'strategy_stats': {k: dict(v) for k, v in strat_stats.items()},
            'trades':         trades,
        }


# ──────────────────────────────────────────────────────────────
#  AGGREGATE HELPERS
# ──────────────────────────────────────────────────────────────
def _aggregate(symbol_results: Dict[str, Dict]) -> Dict:
    all_trades = []
    for r in symbol_results.values():
        all_trades.extend(r.get('trades', []))

    if not all_trades:
        return {}

    wins   = [t for t in all_trades if t['is_win']]
    losses = [t for t in all_trades if not t['is_win']]

    gross_profit = sum(t['pnl_dollar'] for t in wins)   if wins   else 0
    gross_loss   = abs(sum(t['pnl_dollar'] for t in losses)) if losses else 0.001
    total_pnl    = sum(t['pnl_dollar'] for t in all_trades)

    exit_reasons = defaultdict(lambda: {'count': 0, 'pnl': 0.0, 'wins': 0})
    strat_stats  = defaultdict(lambda: {'count': 0, 'pnl': 0.0, 'wins': 0})
    for t in all_trades:
        r = t['exit_reason']
        exit_reasons[r]['count'] += 1
        exit_reasons[r]['pnl']   += t['pnl_dollar']
        if t['is_win']:
            exit_reasons[r]['wins'] += 1
        s = t['strategy']
        strat_stats[s]['count'] += 1
        strat_stats[s]['pnl']   += t['pnl_dollar']
        if t['is_win']:
            strat_stats[s]['wins'] += 1

    longs  = [t for t in all_trades if t['side'] == 'LONG']
    shorts = [t for t in all_trades if t['side'] == 'SHORT']

    profitable_syms = sum(1 for r in symbol_results.values()
                          if r.get('total_pnl', 0) > 0 and r.get('total_trades', 0) > 0)
    total_syms = sum(1 for r in symbol_results.values()
                     if r.get('total_trades', 0) > 0)

    wr = round(len(wins) / len(all_trades) * 100, 1) if all_trades else 0

    return {
        'total_trades':     len(all_trades),
        'wins':             len(wins),
        'losses':           len(losses),
        'win_rate':         wr,
        'profit_factor':    round(gross_profit / gross_loss, 2),
        'total_pnl':        round(total_pnl, 2),
        'gross_profit':     round(gross_profit, 2),
        'gross_loss':       round(gross_loss, 2),
        'avg_win_pct':      round(float(np.mean([t['pnl_pct'] for t in wins])),   3) if wins   else 0,
        'avg_loss_pct':     round(float(np.mean([t['pnl_pct'] for t in losses])), 3) if losses else 0,
        'rr':               round(abs(float(np.mean([t['pnl_pct'] for t in wins]))   /
                                  max(abs(float(np.mean([t['pnl_pct'] for t in losses]))), 0.001)), 2)
                            if wins and losses else 0,
        'long_trades':      len(longs),
        'long_wr':          round(sum(1 for t in longs if t['is_win']) / max(len(longs), 1) * 100, 1),
        'short_trades':     len(shorts),
        'short_wr':         round(sum(1 for t in shorts if t['is_win']) / max(len(shorts), 1) * 100, 1),
        'profitable_syms':  profitable_syms,
        'total_syms':       total_syms,
        'total_commission': round(sum(t['commission'] for t in all_trades), 2),
        'exit_reasons':     {k: dict(v) for k, v in exit_reasons.items()},
        'strategy_stats':   {k: dict(v) for k, v in strat_stats.items()},
    }


def _delta(current, previous, fmt='+.2f') -> str:
    try:
        d = float(current) - float(previous)
        sign = '+' if d >= 0 else ''
        return f'{sign}{d:{fmt[1:]}}'
    except Exception:
        return '—'


# ──────────────────────────────────────────────────────────────
#  PRINT FUNCTIONS
# ──────────────────────────────────────────────────────────────
def _print_separator(char='─', width=78):
    print(char * width)


def _print_header(title: str):
    _print_separator('═')
    print(f'  {title}')
    _print_separator('═')


def _print_per_coin_table(results: Dict[str, Dict], group_label: str,
                           benchmark_per_coin: Optional[Dict] = None):
    """Print per-coin table. benchmark_per_coin keyed by symbol."""
    print(f'\n  📋 {group_label}')
    _print_separator()
    hdr = f'  {"Symbol":<12} {"Trades":>6} {"WR":>7} {"PF":>6} {"PnL ($)":>10} {"MaxDD":>7}'
    if benchmark_per_coin:
        hdr += f'  {"PnL Δ":>8}'
    print(hdr)
    _print_separator()

    for sym, r in sorted(results.items(), key=lambda x: x[1].get('total_pnl', 0), reverse=True):
        n    = r.get('total_trades', 0)
        if n == 0:
            print(f'  {sym:<12} {"—":>6} {"—":>7} {"—":>6} {"no data":>10}')
            continue
        wr   = r.get('win_rate', 0)
        pf   = r.get('profit_factor', 0)
        pnl  = r.get('total_pnl', 0)
        mdd  = r.get('max_drawdown_pct', 0)
        icon = '✅' if pnl > 0 else '❌'
        line = (f'  {icon} {sym:<10} {n:>6} {wr:>6.1f}% {pf:>6.2f} '
                f'${pnl:>+9.2f} {mdd:>6.1f}%')
        if benchmark_per_coin and sym in benchmark_per_coin:
            prev_pnl = benchmark_per_coin[sym].get('pnl', 0)
            line += f'  {_delta(pnl, prev_pnl):>8}'
        print(line)

    _print_separator()


def _print_aggregate_comparison(current: Dict, prev: Dict, current_label: str,
                                  days: int, balance: float, n_coins: int):
    _print_header(f'📊 نتائج مقارنة  ─  {current_label}  vs  {prev["label"]}')

    def row(label, curr_val, prev_val, fmt='.2f', unit=''):
        delta = _delta(curr_val, prev_val, f'+{fmt}')
        print(f'  {label:<25} {str(curr_val) + unit:>12}  {str(prev_val) + unit:>12}  {delta:>10}')

    print(f'  {"Metric":<25} {"Current":>12}  {"Previous":>12}  {"Delta":>10}')
    _print_separator()
    row('Coins tested',     n_coins,                          prev['coins'],  'd',   '')
    row('Days',             days,                             prev['days'],   'd',   '')
    row('Initial balance',  f'${balance:.0f}',                f'${balance:.0f}','s', '')
    _print_separator('-')
    row('Total trades',     current['total_trades'],          prev['n'],      'd',   '')
    row('Win Rate',         f'{current["win_rate"]:.1f}%',   f'{prev["wr"]:.1f}%', 's', '')
    row('Profit Factor',    f'{current["profit_factor"]:.2f}', f'{prev["pf"]:.2f}', 's', '')
    row('Total PnL',        f'${current["total_pnl"]:+.2f}', f'${prev["pnl"]:+.2f}', 's', '')
    row('Avg Win %',        f'{current["avg_win_pct"]:+.3f}%', f'{prev["aw"]:+.3f}%', 's', '')
    row('Avg Loss %',       f'{current["avg_loss_pct"]:+.3f}%', f'{prev["al"]:+.3f}%', 's', '')
    row('R:R',              f'{current["rr"]:.2f}',           f'{prev["rr"]:.2f}', 's', '')
    row('Profitable syms',  f'{current["profitable_syms"]}/{current["total_syms"]}',
                            f'{prev["sym_ok"]}/{prev["coins"]}', 's', '')
    _print_separator()


def _print_exit_analysis(exit_reasons: Dict, prev_exits: Dict):
    print('\n  📤 تحليل أسباب الخروج:')
    _print_separator('-')
    print(f'  {"Exit Reason":<18} {"Count":>6} {"WR":>7} {"PnL ($)":>10}  '
          f'{"Prev PnL":>10}  {"Δ PnL":>8}')
    _print_separator('-')
    for reason, data in sorted(exit_reasons.items(),
                                key=lambda x: x[1]['count'], reverse=True):
        cnt   = data['count']
        wr    = data['wins'] / max(cnt, 1) * 100
        pnl   = data['pnl']
        prev_pnl = prev_exits.get(reason, {}).get('pnl', 0)
        print(f'  {reason:<18} {cnt:>6} {wr:>6.1f}% ${pnl:>+9.2f}  '
              f'${prev_pnl:>+9.2f}  {_delta(pnl, prev_pnl):>8}')
    _print_separator('-')


def _print_strategy_analysis(strat_stats: Dict, prev_strats: Dict):
    print('\n  🎯 أداء الاستراتيجيات:')
    _print_separator('-')
    print(f'  {"Strategy":<22} {"Trades":>6} {"WR":>7} {"PnL ($)":>10}  '
          f'{"Prev PnL":>10}  {"Δ PnL":>8}')
    _print_separator('-')
    for strat, data in sorted(strat_stats.items(),
                               key=lambda x: x[1]['pnl'], reverse=True):
        cnt   = data['count']
        wr    = data['wins'] / max(cnt, 1) * 100
        pnl   = data['pnl']
        prev_pnl = prev_strats.get(strat, {}).get('pnl', 0)
        print(f'  {strat:<22} {cnt:>6} {wr:>6.1f}% ${pnl:>+9.2f}  '
              f'${prev_pnl:>+9.2f}  {_delta(pnl, prev_pnl):>8}')
    _print_separator('-')


def _print_verdict(current: Dict, days: int, balance: float):
    pf = current['profit_factor']
    wr = current['win_rate']
    ps = current['profitable_syms']
    ts = current['total_syms']
    pnl= current['total_pnl']

    print()
    _print_separator('═')
    print(f'  VERDICT — {days}d backtest | ${balance:.0f} starting capital')
    _print_separator('═')
    checks = [
        (pf  >= 1.5,   f'Profit Factor  {pf:.2f} {"✅ ≥ 1.5" if pf>=1.5 else "❌ < 1.5"}'),
        (wr  >= 60,    f'Win Rate       {wr:.1f}% {"✅ ≥ 60%" if wr>=60 else "❌ < 60%"}'),
        (pnl >  0,     f'Net PnL        ${pnl:+.2f} {"✅ positive" if pnl>0 else "❌ negative"}'),
        (ps  == ts,    f'Profitable     {ps}/{ts} {"✅ 100%" if ps==ts else f"⚠️ {ps/max(ts,1)*100:.0f}%"}'),
    ]
    for ok, msg in checks:
        print(f'  {"✅" if ok else "❌"}  {msg}')

    passed = sum(1 for ok, _ in checks if ok)
    print()
    if passed == 4:
        print(f'  🟢 PASS  — نظام V8 يعمل بشكل ممتاز على {ts} عملة')
    elif passed >= 3:
        print(f'  🟡 MARGINAL  — V8 مقبول ({passed}/4 معايير)')
    else:
        print(f'  🔴 FAIL  — V8 يحتاج مراجعة ({passed}/4 معايير)')
    _print_separator('═')


# ──────────────────────────────────────────────────────────────
#  SAVE RESULTS
# ──────────────────────────────────────────────────────────────
def _save_results(symbol_results_all: Dict, agg_all: Dict, agg_orig: Dict,
                  agg_new: Dict, benchmark: Dict, days: int, balance: float):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')

    # ── JSON ──────────────────────────────────────────────────
    json_path = os.path.join(RESULTS_DIR, f'v8_extended_{ts}.json')
    payload = {
        'meta': {
            'engine':          'ScalpingV8',
            'timestamp':        datetime.now().isoformat(),
            'days':             days,
            'initial_balance':  balance,
            'total_coins':      len(symbol_results_all),
            'original_coins':   len(ORIGINAL_14),
            'new_coins':        len(NEW_COINS),
        },
        'aggregate_all':      agg_all,
        'aggregate_original': agg_orig,
        'aggregate_new':      agg_new,
        'benchmark':          benchmark,
        'per_symbol': {
            sym: {k: v for k, v in r.items() if k != 'trades'}
            for sym, r in symbol_results_all.items()
        },
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    # ── Markdown ───────────────────────────────────────────────
    md_path = os.path.join(RESULTS_DIR, f'EXTENDED_RESULTS_{ts}.md')
    prev = benchmark

    def pct_delta(a, b):
        try:
            d = (float(a) - float(b)) / abs(float(b)) * 100
            return f'{d:+.1f}%'
        except Exception:
            return '—'

    md_lines = [
        f'# نتائج الاختبار الموسّع — V8 Extended Backtest',
        f'**تاريخ الاختبار:** {datetime.now().strftime("%Y-%m-%d %H:%M")}  ',
        f'**البيانات:** {days} يوم × 1h bars من Binance API  ',
        f'**العملات:** {len(symbol_results_all)} عملة '
        f'({len(ORIGINAL_14)} أصلية + {len(NEW_COINS)} جديدة)  ',
        f'**رأس المال:** ${balance:.0f} | عمولة 0.1% | Slippage 0.05%  ',
        '',
        '---',
        '',
        '## مقارنة الأداء الإجمالي',
        '',
        '| المقياس | Current (All) | Orig-14 فقط | Previous V8 | Δ (All vs Prev) |',
        '|---------|--------------|-------------|-------------|----------------|',
        f'| عدد العملات | {agg_all["total_syms"]} | 14 | {prev["coins"]} | — |',
        f'| عدد الصفقات | {agg_all["total_trades"]} | {agg_orig.get("total_trades","—")} | {prev["n"]} | {_delta(agg_all["total_trades"], prev["n"], "+d")} |',
        f'| Win Rate | **{agg_all["win_rate"]}%** | {agg_orig.get("win_rate","—")}% | {prev["wr"]}% | {_delta(agg_all["win_rate"], prev["wr"], "+.1f")}pp |',
        f'| Profit Factor | **{agg_all["profit_factor"]}** | {agg_orig.get("profit_factor","—")} | {prev["pf"]} | {_delta(agg_all["profit_factor"], prev["pf"])} |',
        f'| Total PnL | **${agg_all["total_pnl"]:+.2f}** | ${agg_orig.get("total_pnl",0):+.2f} | ${prev["pnl"]:+.2f} | {_delta(agg_all["total_pnl"], prev["pnl"])} |',
        f'| Avg Win | {agg_all["avg_win_pct"]:+.3f}% | {agg_orig.get("avg_win_pct",0):+.3f}% | {prev["aw"]:+.3f}% | {_delta(agg_all["avg_win_pct"], prev["aw"], "+.3f")}pp |',
        f'| Avg Loss | {agg_all["avg_loss_pct"]:+.3f}% | {agg_orig.get("avg_loss_pct",0):+.3f}% | {prev["al"]:+.3f}% | {_delta(agg_all["avg_loss_pct"], prev["al"], "+.3f")}pp |',
        f'| R:R | {agg_all["rr"]:.2f} | {agg_orig.get("rr",0):.2f} | {prev["rr"]:.2f} | {_delta(agg_all["rr"], prev["rr"])} |',
        f'| عملات رابحة | {agg_all["profitable_syms"]}/{agg_all["total_syms"]} | {agg_orig.get("profitable_syms","—")}/14 | {prev["sym_ok"]}/{prev["coins"]} | — |',
        '',
        '---',
        '',
        '## نتائج العملات الأصلية (14 عملة)',
        '',
        '| العملة | صفقات | WR | PF | PnL |',
        '|--------|--------|-----|-----|-----|',
    ]
    for sym in ORIGINAL_14:
        r = symbol_results_all.get(sym, {})
        n = r.get('total_trades', 0)
        if n == 0:
            md_lines.append(f'| {sym} | — | — | — | no data |')
        else:
            icon = '✅' if r['total_pnl'] > 0 else '❌'
            md_lines.append(
                f'| {icon} {sym} | {n} | {r["win_rate"]:.1f}% | '
                f'{r["profit_factor"]:.2f} | ${r["total_pnl"]:+.2f} |'
            )

    md_lines += [
        '',
        '## نتائج العملات الجديدة (12 عملة)',
        '',
        '| العملة | صفقات | WR | PF | PnL |',
        '|--------|--------|-----|-----|-----|',
    ]
    for sym in NEW_COINS:
        r = symbol_results_all.get(sym, {})
        n = r.get('total_trades', 0)
        if n == 0:
            md_lines.append(f'| {sym} | — | — | — | no data |')
        else:
            icon = '✅' if r['total_pnl'] > 0 else '❌'
            md_lines.append(
                f'| {icon} {sym} | {n} | {r["win_rate"]:.1f}% | '
                f'{r["profit_factor"]:.2f} | ${r["total_pnl"]:+.2f} |'
            )

    passed = sum([
        agg_all['profit_factor'] >= 1.5,
        agg_all['win_rate']      >= 60,
        agg_all['total_pnl']     > 0,
        agg_all['profitable_syms'] == agg_all['total_syms'],
    ])
    verdict = ('🟢 PASS' if passed == 4 else
               '🟡 MARGINAL' if passed >= 3 else '🔴 FAIL')

    md_lines += [
        '',
        '---',
        '',
        '## الحكم النهائي',
        '',
        f'**{verdict}** — {passed}/4 معايير محققة  ',
        f'- Profit Factor: {agg_all["profit_factor"]} '
          f'{"✅" if agg_all["profit_factor"]>=1.5 else "❌"} (الهدف ≥ 1.5)',
        f'- Win Rate: {agg_all["win_rate"]}% '
          f'{"✅" if agg_all["win_rate"]>=60 else "❌"} (الهدف ≥ 60%)',
        f'- Net PnL: ${agg_all["total_pnl"]:+.2f} '
          f'{"✅" if agg_all["total_pnl"]>0 else "❌"}',
        f'- Profitable: {agg_all["profitable_syms"]}/{agg_all["total_syms"]} '
          f'{"✅" if agg_all["profitable_syms"]==agg_all["total_syms"] else "⚠️"}',
        '',
        f'---',
        f'*بيانات: tests/backtest_results/v8_extended_{ts}.json*',
    ]

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines) + '\n')

    return json_path, md_path


# ──────────────────────────────────────────────────────────────
#  MAIN RUNNER
# ──────────────────────────────────────────────────────────────
def run_extended_backtest(days: int = 60, balance: float = 1000.0,
                          symbols: Optional[List[str]] = None):

    if symbols is None:
        symbols = ALL_SYMBOLS

    benchmark = _load_previous_benchmark()

    _print_header(
        f'🔬 V8 EXTENDED BACKTEST — {len(symbols)} عملة × {days} يوم  |  '
        f'${balance:.0f} capital'
    )
    print(f'  Original-14: {", ".join(ORIGINAL_14[:7])}…')
    print(f'  New coins:   {", ".join(NEW_COINS[:6])}…')
    print(f'  Previous benchmark: {benchmark["label"]}')
    print(f'  WR={benchmark["wr"]}%  PF={benchmark["pf"]}  '
          f'PnL=${benchmark["pnl"]:+.2f}  {benchmark["sym_ok"]}/{benchmark["coins"]} coins\n')

    # ── FETCH DATA ─────────────────────────────────────────────
    print('📥 Fetching market data from Binance…')
    all_data: Dict[str, pd.DataFrame] = {}
    for sym in symbols:
        print(f'  → {sym:<12}', end=' ', flush=True)
        df = fetch_binance_klines(sym, '1h', days)
        if not df.empty and len(df) >= 80:
            all_data[sym] = df
            print(f'✅  {len(df)} bars')
        else:
            print(f'❌  insufficient ({len(df) if not df.empty else 0} bars)')
        time.sleep(0.25)

    avail = list(all_data.keys())
    print(f'\n  ✅ {len(avail)}/{len(symbols)} symbols ready\n')

    # ── RUN BACKTEST ───────────────────────────────────────────
    print('📊 Running V8 backtest…\n')
    backtester = V8RealisticBacktester(initial_balance=balance)
    symbol_results: Dict[str, Dict] = {}

    for sym, df in all_data.items():
        result = backtester.run(sym, df)
        symbol_results[sym] = result

        n   = result.get('total_trades', 0)
        wr  = result.get('win_rate', 0)
        pnl = result.get('total_pnl', 0)
        pf  = result.get('profit_factor', 0)
        grp = '★' if sym in ORIGINAL_14 else '+'
        icon= '✅' if pnl > 0 else '❌'
        print(f'  {icon} [{grp}] {sym:<12} | Trades:{n:3d} | '
              f'WR:{wr:5.1f}% | PF:{pf:5.2f} | PnL:${pnl:+8.2f}')

    # ── AGGREGATES ─────────────────────────────────────────────
    orig_results = {s: r for s, r in symbol_results.items() if s in ORIGINAL_14}
    new_results  = {s: r for s, r in symbol_results.items() if s in NEW_COINS}

    agg_all  = _aggregate(symbol_results)
    agg_orig = _aggregate(orig_results)
    agg_new  = _aggregate(new_results)

    if not agg_all:
        print('\n❌ No trades generated — check internet connectivity.')
        return {}

    # ── PRINT RESULTS ──────────────────────────────────────────
    _print_aggregate_comparison(agg_all, benchmark,
                                 f'V8 Current ({len(avail)} coins)',
                                 days, balance, len(avail))

    print(f'\n  LONG  {agg_all["long_trades"]:4d} trades | WR {agg_all["long_wr"]:.1f}%')
    print(f'  SHORT {agg_all["short_trades"]:4d} trades | WR {agg_all["short_wr"]:.1f}%')
    print(f'  Commissions paid: ${agg_all["total_commission"]:.2f}')

    _print_exit_analysis(agg_all['exit_reasons'], benchmark.get('exits', {}))
    _print_strategy_analysis(agg_all['strategy_stats'], benchmark.get('strats', {}))

    # Per-coin tables
    if orig_results:
        _print_per_coin_table(orig_results, f'العملات الأصلية (★) — {len(orig_results)} عملة')
    if new_results:
        _print_per_coin_table(new_results, f'العملات الجديدة (+) — {len(new_results)} عملة')

    # Orig-14 aggregate vs previous
    if agg_orig:
        print(f'\n  📌 الـ14 عملة الأصلية (مقارنة مباشرة بالـ benchmark):')
        _print_separator('-')
        print(f'  WR:  {agg_orig["win_rate"]:.1f}%  '
              f'(prev {benchmark["wr"]:.1f}%  Δ{_delta(agg_orig["win_rate"], benchmark["wr"], "+.1f")}pp)')
        print(f'  PF:  {agg_orig["profit_factor"]:.2f}  '
              f'(prev {benchmark["pf"]:.2f}  Δ{_delta(agg_orig["profit_factor"], benchmark["pf"])})')
        print(f'  PnL: ${agg_orig["total_pnl"]:+.2f}  '
              f'(prev ${benchmark["pnl"]:+.2f}  Δ{_delta(agg_orig["total_pnl"], benchmark["pnl"])})')
        _print_separator('-')

    _print_verdict(agg_all, days, balance)

    # ── SAVE ───────────────────────────────────────────────────
    json_path, md_path = _save_results(
        symbol_results, agg_all, agg_orig, agg_new, benchmark, days, balance
    )
    print(f'\n💾 Results saved:')
    print(f'   JSON: {os.path.relpath(json_path, PROJECT_ROOT)}')
    print(f'   MD:   {os.path.relpath(md_path,   PROJECT_ROOT)}')

    return {
        'symbol_results': symbol_results,
        'aggregate_all':  agg_all,
        'aggregate_orig': agg_orig,
        'aggregate_new':  agg_new,
        'benchmark':      benchmark,
    }


# ──────────────────────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='V8 Extended Multi-Coin Backtest')
    parser.add_argument('--days',    type=int,   default=60,
                        help='lookback period in days (default: 60)')
    parser.add_argument('--balance', type=float, default=1000.0,
                        help='starting capital in USDT (default: 1000)')
    parser.add_argument('--coins',   type=str,   default='all',
                        help='comma-separated symbols, "original", "new", or "all"')
    args = parser.parse_args()

    if args.coins == 'all':
        syms = None
    elif args.coins == 'original':
        syms = ORIGINAL_14
    elif args.coins == 'new':
        syms = NEW_COINS
    else:
        syms = [s.strip().upper() for s in args.coins.split(',')]

    run_extended_backtest(days=args.days, balance=args.balance, symbols=syms)
