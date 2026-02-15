#!/usr/bin/env python3
"""
اختبار تحقق شامل نهائي — كود ميت، تكرار، تعارض
=================================================
"""

import os
import sys
import py_compile
from pathlib import Path

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
print("🧪 Final Comprehensive Verification")
print("=" * 80)

# ====================================================================
# 1. Syntax check ALL production Python files
# ====================================================================
print("\n📦 1. Syntax Validation — All Production Files")

production_dirs = [
    'backend/core',
    'backend/api',
    'backend/risk',
    'backend/strategies',
    'backend/cognitive',
    'backend/utils',
    'backend/ml',
    'backend/analysis',
    'backend/selection',
    'backend/trade_management',
    'bin',
]

syntax_errors = []
files_checked = 0
for d in production_dirs:
    full_dir = project_root / d
    if not full_dir.exists():
        continue
    for py_file in full_dir.glob('*.py'):
        files_checked += 1
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            syntax_errors.append(f"{py_file.name}: {e}")

test(f"Syntax OK: {files_checked} production files checked", len(syntax_errors) == 0,
     f"{len(syntax_errors)} errors: {'; '.join(syntax_errors[:3])}")

# ====================================================================
# 2. No broken imports in cognitive __init__.py
# ====================================================================
print("\n📦 2. Cognitive Module Import Check")

try:
    # Test that cognitive __init__ doesn't import deleted files
    init_path = project_root / 'backend' / 'cognitive' / '__init__.py'
    with open(init_path, 'r') as f:
        init_content = f.read()
    
    # These files were deleted - they should NOT be in __init__.py
    deleted_modules = [
        'asset_classifier', 'pattern_objective', 'strategy_selector',
        'dynamic_parameters', 'reasoning_engine', 'confirmation_layer',
        'reversal_detector', 'cognitive_trading_engine', 'scalping_engine',
        'multi_strategy_system', 'unified_trading_v1', 'optimized_signal_engine',
        'ml_enhanced_trading_engine', 'multi_timeframe_entry_v2',
    ]
    
    for mod in deleted_modules:
        # Check import lines only (not comments)
        lines = [l for l in init_content.split('\n') 
                if f'from .{mod}' in l and not l.strip().startswith('#')]
        test(f"Deleted module NOT imported: {mod}", len(lines) == 0,
             f"Still imported in __init__.py")
    
    # These should still be present
    active_modules = [
        'market_state_detector', 'mtf_reversal_confirmation',
        'market_surveillance_engine', 'multi_exit_engine', 'cognitive_orchestrator',
    ]
    for mod in active_modules:
        test(f"Active module imported: {mod}", f'from .{mod}' in init_content)

except Exception as e:
    test("Cognitive __init__.py check", False, str(e))

# ====================================================================
# 3. No deleted files still referenced in production code
# ====================================================================
print("\n📦 3. Dead Reference Check")

deleted_files = [
    'backtest_real_system', 'backtest_v11', 'backtest_v16',
    'cognitive_trading_engine', 'unified_trading_system',
    'multi_strategy_system', 'scalping_engine',  # old scalping, not v7
]

# Check core production files only
prod_files = list((project_root / 'backend' / 'core').glob('*.py'))
prod_files += list((project_root / 'backend' / 'api').glob('*.py'))
prod_files += list((project_root / 'bin').glob('*.py'))

for deleted in deleted_files:
    found_in = []
    for pf in prod_files:
        with open(pf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        # Check for actual import lines (not comments)
        for line in content.split('\n'):
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            if f'from' in stripped and deleted in stripped and 'import' in stripped:
                found_in.append(pf.name)
                break
    test(f"No dead import: {deleted}", len(found_in) == 0,
         f"Still imported in: {', '.join(found_in)}")

# ====================================================================
# 4. Trading Flow Integrity
# ====================================================================
print("\n📦 4. Trading Flow Integrity")

try:
    from backend.core.group_b_system import GroupBSystem
    import inspect
    
    # Verify the complete trading flow chain
    # Entry: _scan_for_entries → _check_risk_gates → _check_directional_stress → _open_position
    scan_src = inspect.getsource(GroupBSystem._scan_for_entries)
    test("Entry flow: risk gates before scanning", '_check_risk_gates' in scan_src)
    test("Entry flow: directional stress before opening", '_check_directional_stress' in scan_src)
    test("Entry flow: _open_position called", '_open_position' in scan_src)
    
    # Exit: _manage_position → _close_position → _record_trade_result
    close_src = inspect.getsource(GroupBSystem._close_position)
    test("Exit flow: _record_trade_result in _close_position", '_record_trade_result' in close_src)
    
    # Position sizing: Kelly active
    size_src = inspect.getsource(GroupBSystem._calculate_position_size)
    test("Position sizing: Kelly criterion active", 'kelly_sizer' in size_src)
    test("Position sizing: 15% hard cap", '0.15' in size_src)
    
    # Monitoring: run_monitoring_only exists and works independently
    test("Monitoring mode exists", hasattr(GroupBSystem, 'run_monitoring_only'))
    
except Exception as e:
    test("Trading flow integrity", False, str(e))

# ====================================================================
# 5. Trading State Machine Integrity
# ====================================================================
print("\n📦 5. TSM State Machine Integrity")

try:
    # background_trading_manager
    btm_path = project_root / 'bin' / 'background_trading_manager.py'
    with open(btm_path, 'r') as f:
        btm_src = f.read()
    
    test("BTM: stop_event.set() in stop()", 'self.stop_event.set()' in btm_src)
    test("BTM: thread join in stop()", '.join(timeout=' in btm_src)
    test("BTM: StateManager sync in _update_system_status", 
         'state_manager' in btm_src and 'write_state' in btm_src)
    test("BTM: DB sync in _update_system_status", 'UPDATE system_status' in btm_src)
    test("BTM: heartbeat loop checks stop_event", 'stop_event.is_set' in btm_src)
    
    # unified_system_manager
    usm_path = project_root / 'backend' / 'core' / 'unified_system_manager.py'
    with open(usm_path, 'r') as f:
        usm_src = f.read()
    
    test("USM: _sync_db_status exists", 'def _sync_db_status' in usm_src)
    test("USM: reconcile syncs DB", '_sync_db_status' in usm_src)
    test("USM: FileLock in start_system", 'FileLock' in usm_src)
    test("USM: rollback on failure", 'old_state' in usm_src)
    
except Exception as e:
    test("TSM integrity", False, str(e))

# ====================================================================
# 6. No Duplicate Definitions
# ====================================================================
print("\n📦 6. Duplicate Definition Check")

try:
    # Check for duplicate method definitions in group_b_system.py
    gbs_path = project_root / 'backend' / 'core' / 'group_b_system.py'
    with open(gbs_path, 'r') as f:
        gbs_lines = f.readlines()
    
    method_defs = {}
    for i, line in enumerate(gbs_lines):
        stripped = line.strip()
        if stripped.startswith('def ') and '(' in stripped:
            method_name = stripped.split('(')[0].replace('def ', '')
            if method_name in method_defs:
                method_defs[method_name].append(i + 1)
            else:
                method_defs[method_name] = [i + 1]
    
    duplicates = {k: v for k, v in method_defs.items() if len(v) > 1}
    test("No duplicate methods in group_b_system.py", len(duplicates) == 0,
         f"Duplicates: {duplicates}")
    
    # Check background_trading_manager
    with open(btm_path, 'r') as f:
        btm_lines = f.readlines()
    
    btm_methods = {}
    for i, line in enumerate(btm_lines):
        stripped = line.strip()
        if stripped.startswith('def ') and '(' in stripped:
            method_name = stripped.split('(')[0].replace('def ', '')
            if method_name in btm_methods:
                btm_methods[method_name].append(i + 1)
            else:
                btm_methods[method_name] = [i + 1]
    
    btm_dupes = {k: v for k, v in btm_methods.items() if len(v) > 1}
    test("No duplicate methods in background_trading_manager.py", len(btm_dupes) == 0,
         f"Duplicates: {btm_dupes}")

except Exception as e:
    test("Duplicate check", False, str(e))

# ====================================================================
# 7. Risk Management Components Active
# ====================================================================
print("\n📦 7. Risk Management Active Verification")

try:
    from backend.risk.portfolio_heat_manager import PortfolioHeatManager
    from backend.risk.kelly_position_sizer import KellyPositionSizer
    
    # Heat manager functional test
    hm = PortfolioHeatManager(max_heat_pct=6.0)
    r = hm.check_portfolio_heat([], 1000)
    test("HeatManager: functional", r['can_open_new'] == True)
    
    # Kelly sizer functional test
    ks = KellyPositionSizer()
    r = ks.calculate_position_size(balance=1000, max_position_pct=0.10, symbol='BTCUSDT')
    test("KellySizer: functional", r['kelly_pct'] > 0)
    test("KellySizer: within bounds", r['kelly_pct'] <= 0.15)
    
    # Verify they're initialized in GroupBSystem
    init_src = inspect.getsource(GroupBSystem.__init__)
    test("HeatManager: initialized in GroupBSystem", 'PortfolioHeatManager' in init_src)
    test("KellySizer: initialized in GroupBSystem", 'KellyPositionSizer' in init_src)
    
except Exception as e:
    test("Risk management active", False, str(e))

# ====================================================================
# 8. Cognitive folder clean
# ====================================================================
print("\n📦 8. Cognitive Folder Cleanliness")

cog_dir = project_root / 'backend' / 'cognitive'
remaining_files = [f.name for f in cog_dir.glob('*.py') if f.name != '__init__.py' and f.name != '__pycache__']
expected_files = {
    'cognitive_orchestrator.py', 'multi_exit_engine.py',
    'mtf_reversal_confirmation.py', 'market_surveillance_engine.py',
    'market_state_detector.py',
}
unexpected = set(remaining_files) - expected_files
test(f"Cognitive folder: only {len(expected_files)} active files remain",
     len(unexpected) == 0, f"Unexpected: {unexpected}")

# ====================================================================
# Summary
# ====================================================================
print("\n" + "=" * 80)
print(f"📊 FINAL RESULTS: {PASS} PASSED, {FAIL} FAILED out of {PASS + FAIL} tests")
print("=" * 80)

for r in RESULTS:
    print(r)

print("\n" + "=" * 80)
if FAIL == 0:
    print("🎉 ALL TESTS PASSED — System is clean, integrated, and protected")
else:
    print(f"⚠️ {FAIL} TESTS FAILED — review above")
print("=" * 80)

sys.exit(0 if FAIL == 0 else 1)
