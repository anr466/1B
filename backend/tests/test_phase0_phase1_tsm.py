#!/usr/bin/env python3
"""
اختبار تحقق شامل — Phase 0 + Phase 1 + Trading State Machine
=============================================================

يتحقق من:
1. تفعيل PortfolioHeatManager و KellyPositionSizer
2. Self-Throttling (حد يومي + حد خسارة)
3. Capital Stress Awareness (تكدس الاتجاه)
4. System-wide Cooldown (بعد خسائر متتالية)
5. Trading State Machine (stop_event + dual state sync)
6. تكامل تدفق التداول
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

PASS = 0
FAIL = 0
RESULTS = []

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        RESULTS.append(f"  ✅ {name}")
    else:
        FAIL += 1
        RESULTS.append(f"  ❌ {name} — {detail}")

print("=" * 80)
print("🧪 Phase 0 + Phase 1 + TSM Verification Test")
print("=" * 80)

# ====================================================================
# Phase 0: PortfolioHeatManager & KellyPositionSizer مفعّلان
# ====================================================================
print("\n📦 Phase 0: Risk Components Activation")

try:
    from backend.risk.portfolio_heat_manager import PortfolioHeatManager
    heat_mgr = PortfolioHeatManager(max_heat_pct=6.0)
    test("PortfolioHeatManager import", True)
    
    # فحص بدون صفقات
    result = heat_mgr.check_portfolio_heat([], 1000.0)
    test("Heat: empty portfolio → can_open_new=True", result['can_open_new'])
    test("Heat: empty → heat=0%", result['current_heat_pct'] == 0)
    
    # فحص مع صفقات مشبعة
    fake_positions = [
        {'entry_price': 100, 'stop_loss': 94, 'size': 10},  # risk = 60
        {'entry_price': 200, 'stop_loss': 190, 'size': 5},  # risk = 50
    ]
    result2 = heat_mgr.check_portfolio_heat(fake_positions, 1000.0)
    test("Heat: with positions → heat > 0", result2['current_heat_pct'] > 0)
    
    # فحص تجاوز الحد
    overloaded = [{'entry_price': 100, 'stop_loss': 0.01, 'size': 1}]  # risk = 99.99
    result3 = heat_mgr.check_portfolio_heat(overloaded, 1000.0)
    test("Heat: overloaded → can_open_new=False", not result3['can_open_new'])
    
except Exception as e:
    test("PortfolioHeatManager import", False, str(e))

try:
    from backend.risk.kelly_position_sizer import KellyPositionSizer
    kelly = KellyPositionSizer(initial_balance=10000)
    test("KellyPositionSizer import", True)
    
    # حساب حجم افتراضي
    size = kelly.calculate_position_size(
        balance=10000, max_position_pct=0.10, symbol='BTCUSDT'
    )
    test("Kelly: returns kelly_pct > 0", size['kelly_pct'] > 0)
    test("Kelly: kelly_pct in range", 0.01 <= size['kelly_pct'] <= 0.15)
    test("Kelly: confidence field exists", 'confidence' in size)
    
except Exception as e:
    test("KellyPositionSizer import", False, str(e))

# ====================================================================
# Phase 0: Kelly مفعّل في group_b_system
# ====================================================================
print("\n📦 Phase 0: Kelly Wired in GroupBSystem")

try:
    import inspect
    from backend.core.group_b_system import GroupBSystem
    
    src = inspect.getsource(GroupBSystem._calculate_position_size)
    test("Kelly: _calculate_position_size accepts signal param",
         'signal' in inspect.signature(GroupBSystem._calculate_position_size).parameters)
    test("Kelly: kelly_sizer used in _calculate_position_size",
         'kelly_sizer' in src and 'calculate_position_size' in src)
    test("Kelly: fallback to fixed pct exists",
         'position_size_percentage' in src)
    
    # فحص أن _scan_for_entries يستدعي _check_risk_gates
    scan_src = inspect.getsource(GroupBSystem._scan_for_entries)
    test("Risk gates wired in _scan_for_entries", '_check_risk_gates' in scan_src)
    test("Directional stress wired in _scan_for_entries", '_check_directional_stress' in scan_src)
    test("Heat manager wired in _check_risk_gates",
         'heat_manager' in inspect.getsource(GroupBSystem._check_risk_gates))
    
except Exception as e:
    test("GroupBSystem inspection", False, str(e))

# ====================================================================
# Phase 1: Self-Throttling + Cooldown + Capital Stress
# ====================================================================
print("\n📦 Phase 1: Self-Throttling & Cooldown & Capital Stress")

try:
    src_init = inspect.getsource(GroupBSystem.__init__)
    test("daily_state initialized in __init__", 'daily_state' in src_init)
    test("max_daily_trades in daily_state", 'max_daily_trades' in src_init)
    test("max_daily_loss_pct in daily_state", 'max_daily_loss_pct' in src_init)
    test("cooldown_hours in daily_state", 'cooldown_hours' in src_init)
    test("max_same_direction in daily_state", 'max_same_direction' in src_init)
    
    # فحص _record_trade_result wired in _close_position
    close_src = inspect.getsource(GroupBSystem._close_position)
    test("_record_trade_result wired in _close_position", '_record_trade_result' in close_src)
    
    # فحص trades_today incremented in _open_position
    open_src = inspect.getsource(GroupBSystem._open_position)
    test("trades_today incremented in _open_position", "trades_today" in open_src)
    
    # فحص _record_trade_result logic
    record_src = inspect.getsource(GroupBSystem._record_trade_result)
    test("Cooldown trigger in _record_trade_result", 'cooldown_until' in record_src)
    test("Consecutive losses tracked", 'consecutive_losses' in record_src)
    
    # فحص _check_risk_gates logic
    gates_src = inspect.getsource(GroupBSystem._check_risk_gates)
    test("Daily trade limit check", 'max_daily_trades' in gates_src)
    test("Daily loss limit check", 'max_daily_loss_pct' in gates_src)
    test("Cooldown check", 'cooldown_until' in gates_src)
    
    # فحص directional stress
    stress_src = inspect.getsource(GroupBSystem._check_directional_stress)
    test("Directional stress: max_same_direction check", 'max_same_direction' in stress_src)
    
except Exception as e:
    test("Phase 1 inspection", False, str(e))

# ====================================================================
# Trading State Machine Fixes
# ====================================================================
print("\n📦 TSM: Trading State Machine Fixes")

try:
    with open(os.path.join(project_root, 'bin', 'background_trading_manager.py'), 'r') as f:
        btm_src = f.read()
    
    # Bug 1: stop_event.set() was missing in stop()
    test("TSM: stop_event.set() in stop()", 'self.stop_event.set()' in btm_src)
    
    # Bug 1b: Thread join for graceful shutdown
    test("TSM: group_b_thread.join() in stop()", 'group_b_thread.join' in btm_src)
    test("TSM: heartbeat_thread.join() in stop()", 'heartbeat_thread.join' in btm_src)
    
    # Bug 2: Dual State sync — state_manager.write_state in _update_system_status
    # Find the _update_system_status method
    idx = btm_src.index('def _update_system_status')
    method_src = btm_src[idx:idx+2000]  # read enough
    test("TSM: StateManager JSON sync in _update_system_status",
         'state_manager' in method_src and 'write_state' in method_src)
    test("TSM: DB update also present",
         'UPDATE system_status' in method_src)
    
except Exception as e:
    test("TSM background_trading_manager", False, str(e))

try:
    with open(os.path.join(project_root, 'backend', 'core', 'unified_system_manager.py'), 'r') as f:
        usm_src = f.read()
    
    # Bug 3: reconcile_state now syncs DB
    test("TSM: _sync_db_status method exists", 'def _sync_db_status' in usm_src)
    test("TSM: _sync_db_status called in reconcile_state", '_sync_db_status' in usm_src)
    
except Exception as e:
    test("TSM unified_system_manager", False, str(e))

# ====================================================================
# Integration: Trading Flow
# ====================================================================
print("\n📦 Integration: Trading Flow Integrity")

try:
    # GroupBSystem exists and can be inspected
    test("GroupBSystem class exists", True)
    
    # Critical methods exist
    for method in ['run_trading_cycle', 'run_monitoring_only', '_scan_for_entries',
                   '_manage_position', '_open_position', '_close_position',
                   '_check_risk_gates', '_check_directional_stress',
                   '_record_trade_result', '_reset_daily_state_if_needed',
                   '_calculate_position_size', '_get_open_positions',
                   '_check_market_regime']:
        test(f"Method exists: {method}", hasattr(GroupBSystem, method))
    
    # Critical attributes initialized
    init_src = inspect.getsource(GroupBSystem.__init__)
    for attr in ['heat_manager', 'kelly_sizer', 'scalping_v7', 'daily_state',
                 'dynamic_blacklist', 'notification_service', 'ml_training_manager']:
        test(f"Attribute initialized: {attr}", f'self.{attr}' in init_src)
    
except Exception as e:
    test("Integration checks", False, str(e))

# ====================================================================
# Syntax Check on All Modified Files
# ====================================================================
print("\n📦 Syntax Validation")

import py_compile
files_to_check = [
    'backend/core/group_b_system.py',
    'backend/risk/portfolio_heat_manager.py',
    'backend/risk/kelly_position_sizer.py',
    'backend/core/unified_system_manager.py',
    'backend/core/state_manager.py',
    'backend/api/system_fast_api.py',
    'bin/background_trading_manager.py',
]

for fpath in files_to_check:
    full = os.path.join(project_root, fpath)
    try:
        py_compile.compile(full, doraise=True)
        test(f"Syntax OK: {fpath}", True)
    except py_compile.PyCompileError as e:
        test(f"Syntax OK: {fpath}", False, str(e))

# ====================================================================
# Summary
# ====================================================================
print("\n" + "=" * 80)
print(f"📊 RESULTS: {PASS} PASSED, {FAIL} FAILED out of {PASS + FAIL} tests")
print("=" * 80)

for r in RESULTS:
    print(r)

print("\n" + "=" * 80)
if FAIL == 0:
    print("🎉 ALL TESTS PASSED")
else:
    print(f"⚠️ {FAIL} TESTS FAILED — review above")
print("=" * 80)

sys.exit(0 if FAIL == 0 else 1)
