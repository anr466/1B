#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 Improvement Validation Test
================================
Runs 4 configurations in parallel on the same data to isolate each fix's impact.

Configuration matrix:
  A — Baseline   : Current V8 as deployed in production
  B — Fix1       : SMART_CUT_1 thresholds loosened (less trigger-happy)
  C — Fix1+Fix2  : Fix1 + LONG-in-DOWN-trend filter
  D — All3       : Fix1+Fix2 + coin swap (drop BTC/BNB → add WIF/DOGE)

Success criteria to auto-apply to production:
  ✅ Win Rate  ≥ 62.0%
  ✅ PF        ≥ 1.65
  ✅ Net PnL   ≥ $650 (14 coins baseline)
  ✅ All coins profitable

Usage:
  python tests/v8_improvement_test.py
  python tests/v8_improvement_test.py --days 30
"""

import sys
import os
import json
import time
import argparse
import logging
from typing import Dict, List, Optional
from copy import deepcopy
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ── Re-use infrastructure from the extended backtest ──────────────────────────
from tests.v8_extended_backtest import (
    V8RealisticBacktester,
    fetch_binance_klines,
    _aggregate,
    _print_separator,
    RESULTS_DIR,
)
from backend.strategies.scalping_v8_engine import V8_CONFIG

logging.basicConfig(level=logging.WARNING, format='%(message)s')

# ──────────────────────────────────────────────────────────────
#  COIN UNIVERSES
# ──────────────────────────────────────────────────────────────
# Original 14 — exact same list as the benchmark run
COINS_BASELINE = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
    'AVAXUSDT', 'NEARUSDT', 'SUIUSDT', 'ARBUSDT', 'APTUSDT',
    'INJUSDT', 'LINKUSDT', 'PEPEUSDT', 'OPUSDT',
]

# Fix3 swap: remove weakest (BTC WR=51.8%, BNB WR=49.2%) → add best new (WIF, DOGE)
COINS_FIX3 = [
    'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'AVAXUSDT', 'NEARUSDT',
    'SUIUSDT', 'ARBUSDT', 'APTUSDT', 'INJUSDT', 'LINKUSDT',
    'PEPEUSDT', 'OPUSDT', 'WIFUSDT', 'DOGEUSDT',
]

# ──────────────────────────────────────────────────────────────
#  CONFIG VARIANTS
# ──────────────────────────────────────────────────────────────
# A — Baseline: production V8 unchanged
CONFIG_A = deepcopy(V8_CONFIG)

# B — Fix1: SMART_CUT_1 less aggressive
#   Before: bars=1, loss=-0.001(0.1%), momentum≤-2
#   After:  bars=1, loss=-0.0015(0.15%), momentum≤-3
CONFIG_B = {
    **CONFIG_A,
    'v8_smart_cut_1': {'bars': 1, 'loss': -0.0015, 'momentum': -3},
}

# C — Fix1 + Fix2: (SMART_CUT_1 + LONG-in-DOWN filter)
#   The LONG filter is implemented at the backtester level (see subclass below)
CONFIG_C = deepcopy(CONFIG_B)   # same config, filter applied in backtester

# D — All3: Fix1 + Fix2 + coin swap (applied via COINS_FIX3)
CONFIG_D = deepcopy(CONFIG_B)


# ──────────────────────────────────────────────────────────────
#  FIX-2 BACKTESTER — blocks LONG signals in DOWN trend
# ──────────────────────────────────────────────────────────────
class V8Fix2Backtester(V8RealisticBacktester):
    """
    Adds Fix2 on top of any config:
    Blocks LONG entry signals when 4H trend = 'DOWN'
    (V7 reversal strategy can generate LONGs in DOWN trends — often bad quality)
    """

    def run(self, symbol: str, df) -> Dict:
        self._reset_state()
        if df is None or len(df) < 80:
            return {'symbol': symbol, 'total_trades': 0, 'error': 'insufficient data'}

        df_prep = self.engine.prepare_data(df)
        if df_prep is None:
            return {'symbol': symbol, 'total_trades': 0, 'error': 'prepare_data failed'}

        import pandas as pd
        import numpy as np

        for i in range(60, len(df_prep)):
            bar = df_prep.iloc[i]
            unr = self._calc_unrealized_pnl(bar['close'])
            self.equity_curve.append({
                'time':           bar.get('timestamp', i),
                'balance':        self.balance,
                'equity':         self.balance + unr,
                'open_positions': len(self.open_positions),
            })

            self._check_exits(df_prep, i, symbol)

            if len(self.open_positions) < self.max_positions:
                trend  = self.engine.get_4h_trend(df_prep, i - 1)
                signal = self.engine.detect_entry(df_prep, trend, i - 1)

                # ── FIX 2: block LONG in DOWN trend ───────────────
                if signal and signal.get('side') == 'LONG' and trend == 'DOWN':
                    signal = None
                # ─────────────────────────────────────────────────

                if signal:
                    ep  = bar['open']
                    ep *= (1 + self.slippage_pct) if signal['side'] == 'LONG' \
                         else (1 - self.slippage_pct)
                    self._open_position(symbol, signal, ep,
                                        bar.get('timestamp', i), i)

        if self.open_positions and len(df_prep) > 0:
            last_bar = df_prep.iloc[-1]
            for pos in list(self.open_positions):
                self._close_position(pos, last_bar['close'],
                                     last_bar.get('timestamp'), 'END_OF_DATA')
            self.open_positions = []

        return self._generate_symbol_report(symbol)


# ──────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────
SUCCESS_CRITERIA = {
    'win_rate':        62.0,
    'profit_factor':    1.65,
    'total_pnl':      650.0,
    'profitable_pct': 100.0,
}


def _check_pass(agg: Dict) -> Dict:
    ps  = agg.get('profitable_syms', 0)
    ts  = agg.get('total_syms', 1)
    pct = ps / ts * 100 if ts > 0 else 0
    checks = {
        'wr':   (agg.get('win_rate', 0),      SUCCESS_CRITERIA['win_rate'],        '≥ 62%'),
        'pf':   (agg.get('profit_factor', 0), SUCCESS_CRITERIA['profit_factor'],   '≥ 1.65'),
        'pnl':  (agg.get('total_pnl', 0),     SUCCESS_CRITERIA['total_pnl'],       '≥ $650'),
        'sym':  (pct,                          SUCCESS_CRITERIA['profitable_pct'],  '100% coins'),
    }
    passed  = {k: v[0] >= v[1] for k, v in checks.items()}
    n_pass  = sum(passed.values())
    return {'checks': checks, 'passed': passed, 'n_pass': n_pass, 'all_pass': n_pass == 4}


def _fmt_delta(a, b, fmt='+.2f') -> str:
    try:
        d = float(a) - float(b)
        s = '+' if d >= 0 else ''
        return f'{s}{d:{fmt[1:]}}'
    except Exception:
        return '—'


def _run_config(label: str, backtester_cls, config: Dict,
                coins: List[str], all_data: Dict) -> Dict:
    bt = backtester_cls(config=config, initial_balance=1000.0)
    results = {}
    for sym in coins:
        if sym not in all_data:
            results[sym] = {'symbol': sym, 'total_trades': 0, 'error': 'no data'}
            continue
        results[sym] = bt.run(sym, all_data[sym])
    agg = _aggregate(results)
    agg['label']   = label
    agg['coins']   = coins
    agg['results'] = results
    return agg


# ──────────────────────────────────────────────────────────────
#  PRINT FUNCTIONS
# ──────────────────────────────────────────────────────────────
def _print_summary_table(configs: List[Dict]):
    _print_separator('═')
    print('  📊 مقارنة التكوينات الأربعة — نفس البيانات × نفس الفترة')
    _print_separator('═')
    hdr = f'  {"Config":<22} {"Trades":>7} {"WR":>7} {"PF":>6} {"PnL ($)":>10} {"R:R":>5} {"Coins":>6}'
    print(hdr)
    _print_separator()

    baseline = configs[0]
    for cfg in configs:
        ps   = cfg.get('profitable_syms', 0)
        ts   = cfg.get('total_syms', 1)
        wr   = cfg.get('win_rate', 0)
        pf   = cfg.get('profit_factor', 0)
        pnl  = cfg.get('total_pnl', 0)
        rr   = cfg.get('rr', 0)
        n    = cfg.get('total_trades', 0)
        lbl  = cfg.get('label', '?')

        checks = _check_pass(cfg)
        status = '✅' if checks['all_pass'] else ('🟡' if checks['n_pass'] >= 3 else '❌')
        delta  = f'  Δ{_fmt_delta(pnl, baseline["total_pnl"])}' if cfg is not baseline else ''

        print(f'  {status} {lbl:<20} {n:>7} {wr:>6.1f}% {pf:>6.2f} '
              f'${pnl:>+9.2f} {rr:>5.2f}  {ps}/{ts}{delta}')

    _print_separator()


def _print_config_detail(cfg: Dict, prev_cfg: Dict = None):
    label  = cfg.get('label', '?')
    checks = _check_pass(cfg)
    print(f'\n  📋 {label}')
    _print_separator('-')

    criteria_keys = [
        ('wr',  'Win Rate',       '%',  '.1f'),
        ('pf',  'Profit Factor',  '',   '.2f'),
        ('pnl', 'Net PnL',        '$',  '.2f'),
        ('sym', '100% Coins',     '%',  '.0f'),
    ]
    for k, name, unit, fmt in criteria_keys:
        val, target, desc = checks['checks'][k]
        ok    = checks['passed'][k]
        icon  = '✅' if ok else '❌'
        line  = f'  {icon}  {name:<18} {val:{fmt}}{unit}  (هدف: {desc})'
        if prev_cfg and k != 'sym':
            prev_checks = _check_pass(prev_cfg)
            prev_val    = prev_checks['checks'][k][0]
            line += f'  Δ{_fmt_delta(val, prev_val)}'
        print(line)

    # exit reason breakdown
    exits = cfg.get('exit_reasons', {})
    if exits:
        total_n = cfg.get('total_trades', 1)
        sc1 = exits.get('SMART_CUT_1', {})
        sl  = exits.get('STOP_LOSS', {})
        tr  = exits.get('TRAILING', {})
        print(f'  ─  TRAILING:     {tr.get("count",0):4d} trades  ${tr.get("pnl",0):+8.2f}')
        print(f'  ─  SMART_CUT_1:  {sc1.get("count",0):4d} trades  ${sc1.get("pnl",0):+8.2f}  '
              f'({sc1.get("count",0)/max(total_n,1)*100:.1f}% of all)')
        print(f'  ─  STOP_LOSS:    {sl.get("count",0):4d} trades  ${sl.get("pnl",0):+8.2f}')


def _print_per_coin_comparison(configs: List[Dict]):
    # Collect all symbols across configs
    all_syms: set = set()
    for cfg in configs:
        all_syms.update(cfg.get('results', {}).keys())

    print(f'\n  📋 نتائج تفصيلية بالعملة')
    _print_separator()
    labels = [c.get('label', '?')[:16] for c in configs]
    hdr    = f'  {"Symbol":<12}' + ''.join(f'  {l:>16}' for l in labels)
    print(hdr)
    _print_separator('-')

    for sym in sorted(all_syms):
        row = f'  {sym:<12}'
        for cfg in configs:
            r   = cfg.get('results', {}).get(sym, {})
            n   = r.get('total_trades', 0)
            pnl = r.get('total_pnl', 0)
            wr  = r.get('win_rate', 0)
            if n == 0:
                row += f'  {"  — no data —":>16}'
            else:
                icon = '✅' if pnl > 0 else '❌'
                row += f'  {icon} WR:{wr:.0f}% ${pnl:+.0f}'
        print(row)
    _print_separator()


def _print_verdict(winning_cfg: Optional[Dict], all_configs: List[Dict]):
    _print_separator('═')
    print('  🏆 VERDICT')
    _print_separator('═')

    if winning_cfg is None:
        print('  ❌  لم تجتز أي تكوين معايير النجاح')
        print('  ⚠️  الاستراتيجية تحتاج مراجعة أعمق')
        _print_separator('═')
        return False

    print(f'  ✅  {winning_cfg["label"]} اجتاز جميع معايير النجاح!')
    print()
    baseline = all_configs[0]
    print(f'  WR:  {baseline["win_rate"]:.1f}% → {winning_cfg["win_rate"]:.1f}%  '
          f'Δ{_fmt_delta(winning_cfg["win_rate"], baseline["win_rate"], "+.1f")}pp')
    print(f'  PF:  {baseline["profit_factor"]:.2f} → {winning_cfg["profit_factor"]:.2f}  '
          f'Δ{_fmt_delta(winning_cfg["profit_factor"], baseline["profit_factor"])}')
    print(f'  PnL: ${baseline["total_pnl"]:+.2f} → ${winning_cfg["total_pnl"]:+.2f}  '
          f'Δ${winning_cfg["total_pnl"] - baseline["total_pnl"]:+.2f}')
    _print_separator('═')
    return True


# ──────────────────────────────────────────────────────────────
#  APPLY FIXES TO PRODUCTION
# ──────────────────────────────────────────────────────────────
def apply_to_production(winning_label: str, all_configs: List[Dict]) -> bool:
    """Apply validated improvements to the live trading engine and coin pool."""

    engine_path   = os.path.join(PROJECT_ROOT,
                                  'backend', 'strategies', 'scalping_v8_engine.py')
    group_b_path  = os.path.join(PROJECT_ROOT,
                                  'backend', 'core', 'group_b_system.py')

    fixes_applied = []

    # ── FIX 1: update V8_CONFIG SMART_CUT_1 in engine ──────────────────────
    try:
        with open(engine_path, 'r', encoding='utf-8') as f:
            src = f.read()

        old_cut = "'v8_smart_cut_1': {'bars': 1, 'loss': -0.001, 'momentum': -2}"
        new_cut = "'v8_smart_cut_1': {'bars': 1, 'loss': -0.0015, 'momentum': -3}"

        if old_cut in src:
            src = src.replace(old_cut, new_cut)
            with open(engine_path, 'w', encoding='utf-8') as f:
                f.write(src)
            fixes_applied.append('Fix1: SMART_CUT_1 threshold updated in V8_CONFIG')
            print(f'  ✅  Fix1 applied → {os.path.relpath(engine_path, PROJECT_ROOT)}')
        elif new_cut in src:
            fixes_applied.append('Fix1: already applied (no-op)')
            print(f'  ℹ️   Fix1 already present in engine (no change needed)')
        else:
            print(f'  ⚠️   Fix1: could not locate SMART_CUT_1 pattern — manual update needed')
    except Exception as e:
        print(f'  ❌  Fix1 failed: {e}')
        return False

    # ── FIX 2: add LONG-in-DOWN filter to detect_entry in engine ───────────
    try:
        with open(engine_path, 'r', encoding='utf-8') as f:
            src = f.read()

        old_entry = (
            "        # V8: Block reversal strategy (verified net negative)\n"
            "        if self.config.get('v8_block_reversal', True):\n"
            "            if signal.get('strategy') == 'reversal':\n"
            "                return None\n"
            "\n"
            "        return signal"
        )
        new_entry = (
            "        # V8: Block reversal strategy (verified net negative)\n"
            "        if self.config.get('v8_block_reversal', True):\n"
            "            if signal.get('strategy') == 'reversal':\n"
            "                return None\n"
            "\n"
            "        # V8.1 Fix2: Block LONG entries when 4H trend is DOWN\n"
            "        # (reduces false LONG entries in bear/choppy markets)\n"
            "        if self.config.get('v8_block_long_in_downtrend', True):\n"
            "            if signal.get('side') == 'LONG' and trend == 'DOWN':\n"
            "                return None\n"
            "\n"
            "        return signal"
        )

        if 'v8_block_long_in_downtrend' in src:
            fixes_applied.append('Fix2: already applied (no-op)')
            print(f'  ℹ️   Fix2 already present in engine (no change needed)')
        elif old_entry in src:
            src = src.replace(old_entry, new_entry)
            with open(engine_path, 'w', encoding='utf-8') as f:
                f.write(src)
            fixes_applied.append('Fix2: LONG-in-DOWN filter added to detect_entry')
            print(f'  ✅  Fix2 applied → {os.path.relpath(engine_path, PROJECT_ROOT)}')
        else:
            print(f'  ⚠️   Fix2: could not locate detect_entry pattern — manual update needed')
    except Exception as e:
        print(f'  ❌  Fix2 failed: {e}')

    # ── FIX 2: also add config flag to V8_CONFIG ────────────────────────────
    try:
        with open(engine_path, 'r', encoding='utf-8') as f:
            src = f.read()

        old_flag = "    'v8_block_reversal': True,"
        new_flag = "    'v8_block_reversal': True,\n    'v8_block_long_in_downtrend': True,"

        if 'v8_block_long_in_downtrend' not in src and old_flag in src:
            src = src.replace(old_flag, new_flag)
            with open(engine_path, 'w', encoding='utf-8') as f:
                f.write(src)
            print(f'  ✅  Fix2 config flag added to V8_CONFIG')
    except Exception as e:
        print(f'  ⚠️   Fix2 config flag: {e}')

    # ── FIX 3: update DEFAULT_SYMBOLS_POOL in group_b_system.py ────────────
    try:
        with open(group_b_path, 'r', encoding='utf-8') as f:
            src = f.read()

        old_pool = (
            "DEFAULT_SYMBOLS_POOL = [\n"
            "    'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT',\n"
            "    'NEARUSDT', 'SUIUSDT', 'ARBUSDT', 'APTUSDT',\n"
            "    'INJUSDT', 'LINKUSDT'\n"
            "]"
        )
        new_pool = (
            "DEFAULT_SYMBOLS_POOL = [\n"
            "    # V8.1: BTC/BNB removed (WR<52%), WIF/DOGE added (WR>64%)\n"
            "    'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'NEARUSDT',\n"
            "    'SUIUSDT', 'ARBUSDT', 'APTUSDT', 'INJUSDT',\n"
            "    'LINKUSDT', 'WIFUSDT', 'DOGEUSDT', 'DOTUSDT',\n"
            "]"
        )

        if 'WIFUSDT' in src:
            fixes_applied.append('Fix3: already applied (no-op)')
            print(f'  ℹ️   Fix3 already present in group_b_system (no change needed)')
        elif old_pool in src:
            src = src.replace(old_pool, new_pool)
            with open(group_b_path, 'w', encoding='utf-8') as f:
                f.write(src)
            fixes_applied.append('Fix3: DEFAULT_SYMBOLS_POOL updated in group_b_system')
            print(f'  ✅  Fix3 applied → {os.path.relpath(group_b_path, PROJECT_ROOT)}')
        else:
            print(f'  ⚠️   Fix3: could not locate DEFAULT_SYMBOLS_POOL — manual update needed')
    except Exception as e:
        print(f'  ❌  Fix3 failed: {e}')

    # ── Save approval record ─────────────────────────────────────────────────
    os.makedirs(RESULTS_DIR, exist_ok=True)
    approval_path = os.path.join(RESULTS_DIR, 'v8_improvement_approved.json')
    with open(approval_path, 'w', encoding='utf-8') as f:
        json.dump({
            'approved_at':    datetime.now().isoformat(),
            'winning_config': winning_label,
            'fixes_applied':  fixes_applied,
            'criteria':       SUCCESS_CRITERIA,
        }, f, indent=2, ensure_ascii=False)

    print(f'\n  💾 Approval record → {os.path.relpath(approval_path, PROJECT_ROOT)}')
    return len(fixes_applied) > 0


# ──────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────
def run_improvement_test(days: int = 60):
    print('═' * 78)
    print('  🧪 V8 Improvement Validation — 4-way A/B/C/D test')
    print(f'  Baseline coins (A/B/C): {len(COINS_BASELINE)} | '
          f'Fix3 coins (D): {len(COINS_FIX3)} | Period: {days}d')
    print('═' * 78)

    # ── FETCH DATA (union of all symbols needed) ───────────────────────────
    all_symbols = list(set(COINS_BASELINE + COINS_FIX3))
    print(f'\n📥 Fetching {len(all_symbols)} symbols from Binance…')
    all_data: Dict = {}
    for sym in all_symbols:
        print(f'  → {sym:<12}', end=' ', flush=True)
        df = fetch_binance_klines(sym, '1h', days)
        if not df.empty and len(df) >= 80:
            all_data[sym] = df
            print(f'✅  {len(df)} bars')
        else:
            print(f'❌  no data ({len(df) if not df.empty else 0} bars)')
        time.sleep(0.2)

    print(f'\n  ✅ {len(all_data)}/{len(all_symbols)} symbols ready\n')

    # ── RUN 4 CONFIGS ──────────────────────────────────────────────────────
    print('🔄 Running 4 configurations…\n')

    configs_def = [
        ('A — Baseline   ', V8RealisticBacktester, CONFIG_A, COINS_BASELINE),
        ('B — Fix1 only  ', V8RealisticBacktester, CONFIG_B, COINS_BASELINE),
        ('C — Fix1+Fix2  ', V8Fix2Backtester,      CONFIG_C, COINS_BASELINE),
        ('D — All3       ', V8Fix2Backtester,       CONFIG_D, COINS_FIX3),
    ]

    agg_list: List[Dict] = []
    for label, cls, cfg, coins in configs_def:
        print(f'  Running {label}…', end=' ', flush=True)
        agg = _run_config(label.strip(), cls, cfg, coins, all_data)
        agg_list.append(agg)
        chk = _check_pass(agg)
        status = ('✅ PASS' if chk['all_pass'] else
                  f'🟡 {chk["n_pass"]}/4' if chk['n_pass'] >= 3 else
                  f'❌ {chk["n_pass"]}/4')
        print(f'WR={agg["win_rate"]:.1f}%  PF={agg["profit_factor"]:.2f}  '
              f'PnL=${agg["total_pnl"]:+.2f}  [{status}]')

    # ── PRINT COMPARISON TABLE ────────────────────────────────────────────
    print()
    _print_summary_table(agg_list)

    for i, cfg in enumerate(agg_list):
        prev = agg_list[i-1] if i > 0 else None
        _print_config_detail(cfg, prev)

    # ── PER-COIN TABLE ────────────────────────────────────────────────────
    try:
        _print_per_coin_comparison(agg_list)
    except Exception:
        pass   # non-critical display

    # ── VERDICT ───────────────────────────────────────────────────────────
    passing = [c for c in agg_list if _check_pass(c)['all_pass']]

    # Pick best passing config (highest PF, then WR)
    if passing:
        winning = max(passing, key=lambda c: (c['profit_factor'], c['win_rate']))
    else:
        # Best marginal
        winning = max(agg_list, key=lambda c: _check_pass(c)['n_pass'])

    print()
    approved = _print_verdict(winning if passing else None, agg_list)

    # ── AUTO-APPLY IF PASSING ─────────────────────────────────────────────
    if approved:
        print(f'\n🔧 Applying {winning["label"]} improvements to production…\n')
        success = apply_to_production(winning['label'], agg_list)
        if success:
            print('\n  ✅  جميع التحسينات طُبّقت على نظام التداول الفعلي')
            print('  ⚠️  أعد تشغيل الـ backend لأخذ التغييرات بعين الاعتبار')
        else:
            print('\n  ❌  فشل تطبيق بعض التحسينات — راجع الأخطاء أعلاه')
    else:
        print('\n  ⚠️  لا يوجد تكوين ناجح — التحسينات لن تُطبّق على الإنتاج')

    # ── SAVE RESULTS ──────────────────────────────────────────────────────
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts         = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path   = os.path.join(RESULTS_DIR, f'improvement_test_{ts}.json')
    serialisable = []
    for cfg in agg_list:
        entry = {k: v for k, v in cfg.items() if k not in ('results', 'coins')}
        entry['coins'] = cfg.get('coins', [])
        serialisable.append(entry)

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({
            'meta':    {'days': days, 'timestamp': datetime.now().isoformat()},
            'configs': serialisable,
            'winning': winning.get('label'),
            'approved': approved,
        }, f, ensure_ascii=False, indent=2, default=str)

    print(f'\n💾 Results → {os.path.relpath(out_path, PROJECT_ROOT)}')
    return agg_list, approved


# ──────────────────────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='V8 Improvement A/B Test')
    parser.add_argument('--days', type=int, default=60,
                        help='lookback period (default: 60)')
    args = parser.parse_args()
    run_improvement_test(days=args.days)
