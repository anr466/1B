#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Optimized Backtest - نظام محسّن بناءً على تحليل النتائج
==============================================================
التحسينات المطبقة:
1. ❌ حذف reversal strategy (خاسرة: -$132)
2. 🔧 SL: 0.8% → 2.0% (ATR-based)
3. 🔧 Early Cut: تعديل (3h/-0.5% → 6h/-0.8%)
4. ✅ Selective Entry: min_confluence 4→6
5. 🎯 Focus on: breakout, breakdown, trend_cont_short
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from realistic_backtest import run_full_backtest

# ============================================================
# OPTIMIZED CONFIG - Phase 1: Entry Filtering
# ============================================================

OPTIMIZED_CONFIG_V1 = {
    # Position sizing
    'position_size_pct': 0.06,
    'max_positions': 5,
    'max_hold_hours': 12,

    # Entry thresholds (MORE SELECTIVE)
    'min_confluence': 6,  # ↑ from 4 (fewer but better trades)
    'min_timing': 2,      # ↑ from 1 (stronger signals)
    'require_quality': True,

    # Cognitive entry (REMOVE reversal)
    'use_cognitive_entry': True,
    'blocked_cognitive': ['pullback', 'vol_expand', 'reversal'],  # ← ADDED reversal

    # ATR-based SL (WIDER)
    'use_atr_sl': True,
    'atr_sl_multiplier': 2.5,
    'sl_pct': 0.020,      # ↑ from 0.008 (2% fallback SL)

    # Exit - trailing only
    'trailing_activation': 0.004,
    'trailing_distance': 0.003,
    'breakeven_trigger': 0.005,

    # Early exit (MORE PATIENT)
    'early_cut_hours': 6,     # ↑ from 3 (let trades develop)
    'early_cut_loss': 0.008,  # ↑ from 0.005 (wider tolerance)
    'stagnant_hours': 4,
    'stagnant_threshold': 0.002,

    # Blocked SHORT patterns
    'blocked_short': ['st_flip_bear', 'rsi_reject', 'macd_x_bear'],

    # Costs
    'commission_pct': 0.001,
    'slippage_pct': 0.0005,

    # Data
    'min_bars': 60,
    'data_timeframe': '1h',
}


# ============================================================
# OPTIMIZED CONFIG - Phase 2: More Aggressive Filtering
# ============================================================

OPTIMIZED_CONFIG_V2 = {
    **OPTIMIZED_CONFIG_V1,
    
    # Even MORE selective
    'min_confluence': 7,  # ↑ from 6 (ultra-selective)
    'min_timing': 2,
    
    # Wider SL
    'sl_pct': 0.025,  # 2.5% (more breathing room)
    
    # No early cut (trust the system)
    'early_cut_hours': 12,  # Same as max_hold (effectively disabled)
    'early_cut_loss': 0.02,  # 2% (very patient)
}


# ============================================================
# RUN TESTS
# ============================================================

if __name__ == '__main__':
    import json
    
    print("\n" + "="*70)
    print("  🚀 OPTIMIZATION TESTING")
    print("  Comparing: CURRENT vs OPTIMIZED_V1 vs OPTIMIZED_V2")
    print("="*70 + "\n")
    
    # Test symbols (subset for faster testing)
    test_symbols = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'PEPEUSDT', 'INJUSDT',
        'ARBUSDT', 'OPUSDT', 'DOGEUSDT', 'ADAUSDT', 'NEARUSDT'
    ]
    
    # ===== Phase 1: Optimized V1 =====
    print("\n" + "🔬"*35)
    print("  PHASE 1: OPTIMIZED V1 (Selective Entry + Wider SL)")
    print("🔬"*35 + "\n")
    
    results_v1 = run_full_backtest(
        config=OPTIMIZED_CONFIG_V1,
        symbols=test_symbols,
        days=60,
        initial_balance=1000.0,
        label="OPTIMIZED V1"
    )
    
    # Save results
    output_dir = os.path.join(PROJECT_ROOT, 'tests', 'backtest_results')
    
    summary_v1 = {k: v for k, v in results_v1.items() 
                  if k not in ('all_trades', 'per_symbol')}
    
    with open(os.path.join(output_dir, 'optimized_v1_results.json'), 'w') as f:
        json.dump(summary_v1, f, indent=2, default=str)
    
    # ===== Phase 2: Optimized V2 =====
    print("\n" + "🔬"*35)
    print("  PHASE 2: OPTIMIZED V2 (Ultra-Selective + No Early Cut)")
    print("🔬"*35 + "\n")
    
    results_v2 = run_full_backtest(
        config=OPTIMIZED_CONFIG_V2,
        symbols=test_symbols,
        days=60,
        initial_balance=1000.0,
        label="OPTIMIZED V2"
    )
    
    summary_v2 = {k: v for k, v in results_v2.items() 
                  if k not in ('all_trades', 'per_symbol')}
    
    with open(os.path.join(output_dir, 'optimized_v2_results.json'), 'w') as f:
        json.dump(summary_v2, f, indent=2, default=str)
    
    # ===== COMPARISON =====
    print("\n" + "="*70)
    print("  📊 COMPARISON SUMMARY")
    print("="*70)
    
    # Load current results for comparison
    with open(os.path.join(output_dir, 'current_system_results.json'), 'r') as f:
        current = json.load(f)
    
    def print_comparison(label, curr, opt1, opt2):
        print(f"\n{label}:")
        print(f"  CURRENT:      {curr}")
        print(f"  OPTIMIZED V1: {opt1} ({'+' if opt1 > curr else ''}{((opt1-curr)/curr*100):.1f}%)")
        print(f"  OPTIMIZED V2: {opt2} ({'+' if opt2 > curr else ''}{((opt2-curr)/curr*100):.1f}%)")
    
    print_comparison(
        "Win Rate",
        current.get('win_rate', 0),
        summary_v1.get('win_rate', 0),
        summary_v2.get('win_rate', 0)
    )
    
    print_comparison(
        "Profit Factor",
        current.get('profit_factor', 0),
        summary_v1.get('profit_factor', 0),
        summary_v2.get('profit_factor', 0)
    )
    
    print_comparison(
        "Total PnL ($)",
        current.get('total_pnl', 0),
        summary_v1.get('total_pnl', 0),
        summary_v2.get('total_pnl', 0)
    )
    
    print_comparison(
        "Total Trades",
        current.get('total_trades', 0),
        summary_v1.get('total_trades', 0),
        summary_v2.get('total_trades', 0)
    )
    
    print("\n" + "="*70)
    print("  🎯 RECOMMENDATION")
    print("="*70)
    
    # Determine best config
    pf_v1 = summary_v1.get('profit_factor', 0)
    pf_v2 = summary_v2.get('profit_factor', 0)
    
    if pf_v1 >= 2.0 or pf_v2 >= 2.0:
        winner = "V1" if pf_v1 > pf_v2 else "V2"
        pf = pf_v1 if pf_v1 > pf_v2 else pf_v2
        print(f"\n✅ SUCCESS! OPTIMIZED {winner} achieved PF = {pf:.2f} (target: 2.0)")
        print(f"   Use config: OPTIMIZED_CONFIG_{winner}")
    else:
        print(f"\n⚠️  Neither version reached PF=2.0 yet")
        print(f"   Best: {'V1' if pf_v1 > pf_v2 else 'V2'} with PF={max(pf_v1, pf_v2):.2f}")
        print(f"   → Need Phase 3 optimizations (portfolio management)")
    
    print("\n💾 All results saved to tests/backtest_results/")
    print("="*70 + "\n")
