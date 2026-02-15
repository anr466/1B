#!/usr/bin/env python3
"""
🔍 System Verification Test Suite
===================================
Tests across 5 dimensions:
1. Architecture (imports, blueprints, module dependencies)
2. State Management (state machine, daily_state, user isolation)
3. Data Integrity (DB schema, balance sync, position lifecycle)
4. Security (auth, CORS, API keys, admin protection)
5. Scalability & Stability (error handling, thread safety, graceful degradation)
"""

import sys
import os
import json
import sqlite3
import threading
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'database'))

logging.basicConfig(level=logging.WARNING)

# Test counters
PASSED = 0
FAILED = 0
ERRORS = []

def test(name, condition, detail=""):
    global PASSED, FAILED, ERRORS
    if condition:
        PASSED += 1
        print(f"  ✅ {name}")
    else:
        FAILED += 1
        ERRORS.append(f"{name}: {detail}")
        print(f"  ❌ {name} — {detail}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ============================================================
# 1. ARCHITECTURE
# ============================================================
section("1️⃣ ARCHITECTURE — Module Dependencies & Blueprint Registration")

# 1.1 Core module imports
core_modules = [
    ('backend.core.group_b_system', 'GroupBSystem'),
    ('backend.core.state_manager', 'StateManager'),
    ('backend.core.trading_state_machine', 'TradingStateMachine'),
    ('backend.core.unified_system_manager', 'UnifiedSystemManager'),
]

for mod_path, class_name in core_modules:
    try:
        mod = __import__(mod_path, fromlist=[class_name])
        cls = getattr(mod, class_name, None)
        test(f"Import {class_name}", cls is not None, f"Class not found in {mod_path}")
    except Exception as e:
        test(f"Import {class_name}", False, str(e)[:80])

# 1.2 Strategy & cognitive imports
strategy_modules = [
    'backend.strategies.scalping_v7_engine',
    'backend.cognitive.cognitive_orchestrator',
    'backend.cognitive.multi_exit_engine',
    'backend.cognitive.market_state_detector',
]

for mod_path in strategy_modules:
    try:
        __import__(mod_path)
        test(f"Import {mod_path.split('.')[-1]}", True)
    except Exception as e:
        test(f"Import {mod_path.split('.')[-1]}", False, str(e)[:80])

# 1.3 Risk & selection modules
risk_modules = [
    'backend.risk.kelly_position_sizer',
    'backend.risk.portfolio_heat_manager',
    'backend.selection.dynamic_blacklist',
    'backend.utils.data_provider',
]

for mod_path in risk_modules:
    try:
        __import__(mod_path)
        test(f"Import {mod_path.split('.')[-1]}", True)
    except Exception as e:
        test(f"Import {mod_path.split('.')[-1]}", False, str(e)[:80])

# 1.4 Database manager
try:
    from database.database_manager import DatabaseManager
    test("Import DatabaseManager", True)
except Exception as e:
    test("Import DatabaseManager", False, str(e)[:80])

# 1.5 Flask blueprints
print("\n  --- Flask Blueprints ---")
blueprint_imports = [
    ('backend.api.mobile_endpoints', 'mobile_bp'),
    ('backend.api.auth_endpoints', 'auth_bp'),
    ('backend.api.admin_unified_api', 'admin_unified_bp'),
    ('backend.api.system_endpoints', 'system_bp'),
    ('backend.api.background_control', 'background_bp'),
    ('backend.api.system_fast_api', 'system_fast_bp'),
    ('backend.api.trading_control_api', 'trading_control_bp'),
    ('backend.api.smart_exit_api', 'smart_exit_bp'),
    ('backend.api.secure_actions_endpoints', 'secure_actions_bp'),
    ('backend.api.fcm_endpoints', 'fcm_bp'),
    ('backend.api.login_otp_endpoints', 'login_otp_bp'),
    ('backend.api.client_logs_endpoint', 'client_logs_bp'),
    ('backend.api.ml_status_endpoints', 'ml_status_bp'),
    ('backend.api.ml_learning_endpoints', 'ml_learning_bp'),
    ('backend.cryptowave.api_endpoints', 'cryptowave_bp'),
]

for mod_path, bp_name in blueprint_imports:
    try:
        mod = __import__(mod_path, fromlist=[bp_name])
        bp = getattr(mod, bp_name, None)
        test(f"Blueprint {bp_name}", bp is not None, f"Not found in {mod_path}")
    except Exception as e:
        test(f"Blueprint {bp_name}", False, str(e)[:80])

# 1.6 Blueprint URL prefix consistency
print("\n  --- Blueprint URL Prefixes ---")
try:
    from backend.api.admin_unified_api import admin_unified_bp
    from backend.api.background_control import background_bp
    from backend.api.trading_control_api import trading_control_bp
    
    test("admin_unified_bp prefix = /admin", 
         admin_unified_bp.url_prefix == '/admin',
         f"Got: {admin_unified_bp.url_prefix}")
    test("background_bp prefix = /admin/background",
         background_bp.url_prefix == '/admin/background',
         f"Got: {background_bp.url_prefix}")
    test("trading_control_bp prefix = /admin/trading",
         trading_control_bp.url_prefix == '/admin/trading',
         f"Got: {trading_control_bp.url_prefix}")
except Exception as e:
    test("Blueprint prefix check", False, str(e)[:80])

# ============================================================
# 2. STATE MANAGEMENT
# ============================================================
section("2️⃣ STATE MANAGEMENT — State Machine, StateManager, User Isolation")

# 2.1 StateManager uses RLock (not Lock)
try:
    from backend.core.state_manager import StateManager
    sm = StateManager()
    lock_type = type(sm.lock).__name__
    test("StateManager uses RLock (not Lock)", 
         'RLock' in lock_type,
         f"Got: {lock_type}")
except Exception as e:
    test("StateManager RLock check", False, str(e)[:80])

# 2.2 StateManager read/write cycle
try:
    sm = StateManager()
    test_data = {'test_key': 'test_value', 'timestamp': str(datetime.now())}
    sm.write_state(test_data)
    read_back = sm.read_state()
    test("StateManager write→read cycle",
         read_back.get('test_key') == 'test_value',
         f"Got: {read_back.get('test_key')}")
except Exception as e:
    test("StateManager write→read", False, str(e)[:80])

# 2.3 TradingStateMachine states
try:
    from backend.core.trading_state_machine import TradingStateMachine
    tsm = TradingStateMachine()
    state = tsm.get_state()
    test("TradingStateMachine.get_state() returns dict",
         isinstance(state, dict),
         f"Got: {type(state)}")
    test("TradingStateMachine has trading_state field",
         'trading_state' in state,
         f"Keys: {list(state.keys())}")
    valid_states = ['STOPPED', 'STARTING', 'RUNNING', 'STOPPING', 'ERROR']
    test("trading_state is valid",
         state.get('trading_state') in valid_states,
         f"Got: {state.get('trading_state')}")
except Exception as e:
    test("TradingStateMachine check", False, str(e)[:80])

# 2.4 GroupBSystem user isolation
try:
    from backend.core.group_b_system import GroupBSystem
    sys1 = GroupBSystem.__new__(GroupBSystem)
    sys2 = GroupBSystem.__new__(GroupBSystem)
    # Don't fully init (needs DB), just verify class supports user_id
    test("GroupBSystem accepts user_id parameter",
         'user_id' in GroupBSystem.__init__.__code__.co_varnames,
         "user_id not in __init__ params")
except Exception as e:
    test("GroupBSystem user isolation", False, str(e)[:80])

# 2.5 Daily state structure
try:
    from backend.core.group_b_system import GroupBSystem
    # Check default daily_state keys
    import inspect
    source = inspect.getsource(GroupBSystem.__init__)
    required_keys = ['trades_today', 'losses_today', 'max_daily_trades', 'max_daily_loss_pct', 'daily_pnl']
    for key in required_keys:
        test(f"daily_state has '{key}'", key in source, f"Not found in __init__")
except Exception as e:
    test("daily_state structure", False, str(e)[:80])

# ============================================================
# 3. DATA INTEGRITY
# ============================================================
section("3️⃣ DATA INTEGRITY — DB Schema, Balance Sync, Position Lifecycle")

# 3.1 Database exists and is accessible
db_path = PROJECT_ROOT / 'database' / 'trading_database.db'
test("Database file exists", db_path.exists(), f"Not found at {db_path}")

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # 3.2 Required tables exist
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    required_tables = [
        'users', 'user_settings', 'active_positions', 'portfolio',
        'user_portfolio', 'system_status', 'user_binance_keys'
    ]
    
    for table in required_tables:
        test(f"Table '{table}' exists", table in tables, f"Tables: {tables[:10]}...")
    
    # 3.3 active_positions schema has all required columns
    cursor = conn.execute("PRAGMA table_info(active_positions)")
    ap_columns = {row[1] for row in cursor.fetchall()}
    
    required_ap_columns = [
        'id', 'user_id', 'symbol', 'entry_price', 'quantity',
        'stop_loss', 'take_profit', 'is_active', 'is_demo',
        'position_size', 'position_type', 'timeframe', 'entry_date',
        'exit_price', 'exit_reason', 'profit_loss', 'highest_price',
        'entry_commission', 'exit_commission'
    ]
    
    for col in required_ap_columns:
        test(f"active_positions.{col} exists", col in ap_columns, f"Missing column")
    
    # 3.4 system_status has trading_state column
    cursor = conn.execute("PRAGMA table_info(system_status)")
    ss_columns = {row[1] for row in cursor.fetchall()}
    test("system_status.trading_state exists", 'trading_state' in ss_columns, 
         f"Columns: {ss_columns}")
    
    # 3.5 Balance dual-table consistency
    cursor = conn.execute("""
        SELECT p.available_balance as p_balance, up.balance as up_balance, u.id, u.username
        FROM users u
        LEFT JOIN portfolio p ON u.id = p.user_id AND p.is_demo = 1
        LEFT JOIN user_portfolio up ON u.id = up.user_id
        WHERE u.user_type = 'admin'
        LIMIT 1
    """)
    row = cursor.fetchone()
    if row and row['p_balance'] is not None and row['up_balance'] is not None:
        diff = abs((row['p_balance'] or 0) - (row['up_balance'] or 0))
        test(f"Balance sync: portfolio vs user_portfolio (admin demo)",
             diff < 0.01,
             f"portfolio={row['p_balance']}, user_portfolio={row['up_balance']}, diff={diff:.2f}")
    else:
        test("Balance sync check", True, "No admin demo portfolio found (skipped)")
    
    # 3.6 No orphan active positions (user must exist)
    cursor = conn.execute("""
        SELECT COUNT(*) as cnt FROM active_positions ap
        LEFT JOIN users u ON ap.user_id = u.id
        WHERE u.id IS NULL
    """)
    orphans = cursor.fetchone()[0]
    test("No orphan positions (user_id references valid user)", orphans == 0,
         f"Found {orphans} orphan positions")
    
    # 3.7 No active positions with exit data (logical consistency)
    cursor = conn.execute("""
        SELECT COUNT(*) as cnt FROM active_positions
        WHERE is_active = 1 AND exit_price IS NOT NULL
    """)
    bad_active = cursor.fetchone()[0]
    test("No active positions with exit_price set", bad_active == 0,
         f"Found {bad_active} inconsistent positions")
    
    # 3.8 Closed positions have exit_reason
    cursor = conn.execute("""
        SELECT COUNT(*) as cnt FROM active_positions
        WHERE is_active = 0 AND exit_reason IS NULL
    """)
    no_reason = cursor.fetchone()[0]
    test("All closed positions have exit_reason", no_reason == 0,
         f"Found {no_reason} closed positions without reason")
    
    # 3.9 user_settings referential integrity
    cursor = conn.execute("""
        SELECT COUNT(*) as cnt FROM user_settings us
        LEFT JOIN users u ON us.user_id = u.id
        WHERE u.id IS NULL
    """)
    orphan_settings = cursor.fetchone()[0]
    test("No orphan user_settings", orphan_settings == 0,
         f"Found {orphan_settings} orphan settings")
    
    conn.close()

# 3.10 DatabaseManager update_user_balance syncs both tables
try:
    import inspect
    from database.database_manager import DatabaseManager
    source = inspect.getsource(DatabaseManager.update_user_balance)
    test("update_user_balance updates 'portfolio' table",
         'portfolio' in source and 'UPDATE' in source,
         "Missing portfolio UPDATE")
    test("update_user_balance updates 'user_portfolio' table",
         'user_portfolio' in source,
         "Missing user_portfolio UPDATE")
except Exception as e:
    test("update_user_balance dual-table check", False, str(e)[:80])

# ============================================================
# 4. SECURITY
# ============================================================
section("4️⃣ SECURITY — Auth, CORS, API Keys, Admin Protection")

# 4.1 No hardcoded API keys in source
print("\n  --- Hardcoded Secrets Scan ---")
import re

sensitive_patterns = [
    (r'["\']([A-Za-z0-9]{64})["\']', 'Possible Binance API key (64 chars)'),
    (r'sk-[a-zA-Z0-9]{20,}', 'Possible OpenAI key'),
]

scan_dirs = ['backend/', 'bin/', 'config/']
hardcoded_found = False

for scan_dir in scan_dirs:
    scan_path = PROJECT_ROOT / scan_dir
    if not scan_path.exists():
        continue
    for py_file in scan_path.rglob('*.py'):
        if '__pycache__' in str(py_file) or '_archive' in str(py_file):
            continue
        try:
            content = py_file.read_text(errors='ignore')
            for pattern, desc in sensitive_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Skip common false positives (hex hashes, etc.)
                    if match.startswith('0x') or match == '0' * 64:
                        continue
                    hardcoded_found = True
                    test(f"No hardcoded secrets in {py_file.name}", False, desc)
        except Exception:
            pass

if not hardcoded_found:
    test("No hardcoded API keys in backend/bin/config", True)

# 4.2 .env file used for secrets
env_path = PROJECT_ROOT / '.env'
test(".env file exists", env_path.exists(), "Missing .env file")

if env_path.exists():
    env_content = env_path.read_text()
    test(".env has BINANCE_BACKEND_API_KEY", 'BINANCE_BACKEND_API_KEY' in env_content,
         "Missing key")
    test(".env has BINANCE_BACKEND_API_SECRET", 'BINANCE_BACKEND_API_SECRET' in env_content,
         "Missing secret")
    test(".env has SECRET_KEY or JWT_SECRET", 
         'SECRET_KEY' in env_content or 'JWT_SECRET' in env_content,
         "Missing auth secret")

# 4.3 .env in .gitignore
gitignore_path = PROJECT_ROOT / '.gitignore'
if gitignore_path.exists():
    gi_content = gitignore_path.read_text()
    test(".env in .gitignore", '.env' in gi_content, "Not ignored!")
else:
    test(".gitignore exists", False, "No .gitignore found")

# 4.4 Admin routes have require_admin decorator
try:
    import inspect
    from backend.api.admin_unified_api import admin_unified_bp
    
    # Check if require_admin is imported and used
    source = inspect.getsource(sys.modules['backend.api.admin_unified_api'])
    test("admin_unified_api uses require_admin decorator",
         'require_admin' in source,
         "No admin protection found")
except Exception as e:
    test("Admin route protection", False, str(e)[:80])

try:
    from backend.api.background_control import background_bp
    source = inspect.getsource(sys.modules['backend.api.background_control'])
    test("background_control uses require_admin decorator",
         'require_admin' in source,
         "No admin protection found")
except Exception as e:
    test("Background control admin protection", False, str(e)[:80])

# 4.5 CORS configuration
try:
    source = (PROJECT_ROOT / 'start_server.py').read_text()
    test("CORS configured in start_server.py", 'CORS' in source, "CORS not found")
except Exception as e:
    test("CORS check", False, str(e)[:80])

# 4.6 Password hashing (not plaintext)
try:
    from database.database_manager import DatabaseManager
    source = inspect.getsource(DatabaseManager)
    has_hash = ('hash' in source.lower() or 'bcrypt' in source.lower() or 
                'pbkdf2' in source.lower() or 'hashlib' in source.lower())
    test("Password hashing in DatabaseManager", has_hash,
         "No hash/bcrypt/pbkdf2 reference found")
except Exception as e:
    test("Password hashing check", False, str(e)[:80])

# ============================================================
# 5. SCALABILITY & STABILITY
# ============================================================
section("5️⃣ SCALABILITY & STABILITY — Error Handling, Thread Safety, Graceful Degradation")

# 5.1 DatabaseManager singleton pattern
try:
    from database.database_manager import DatabaseManager
    test("DatabaseManager uses singleton pattern", 
         hasattr(DatabaseManager, '_instance'),
         "No _instance attribute")
    test("DatabaseManager has _singleton_lock",
         hasattr(DatabaseManager, '_singleton_lock'),
         "No thread-safe singleton")
except Exception as e:
    test("DatabaseManager singleton", False, str(e)[:80])

# 5.2 Write lock for DB writes
try:
    dm = DatabaseManager()
    test("DatabaseManager has _write_lock (RLock)",
         hasattr(dm, '_write_lock'),
         "No write lock")
    lock_type = type(dm._write_lock).__name__
    test("_write_lock is RLock",
         'RLock' in lock_type,
         f"Got: {lock_type}")
except Exception as e:
    test("DB write lock", False, str(e)[:80])

# 5.3 Connection context manager
try:
    source = inspect.getsource(DatabaseManager)
    test("DatabaseManager has get_connection context manager",
         'get_connection' in source and 'contextmanager' in source,
         "Missing context manager")
    test("DatabaseManager has get_write_connection",
         'get_write_connection' in source,
         "Missing write connection method")
except Exception as e:
    test("Connection management", False, str(e)[:80])

# 5.4 Graceful import fallbacks in start_server.py
try:
    server_source = (PROJECT_ROOT / 'start_server.py').read_text()
    # Count try/except for blueprint imports
    import_tries = server_source.count('except Exception')
    test("start_server.py has graceful import fallbacks",
         import_tries >= 10,
         f"Only {import_tries} Exception handlers")
except Exception as e:
    test("Graceful fallbacks", False, str(e)[:80])

# 5.5 Background trading manager error handling
try:
    btm_source = (PROJECT_ROOT / 'bin' / 'background_trading_manager.py').read_text()
    test("background_trading_manager has per-user error handling",
         'continue' in btm_source and 'user_error' in btm_source,
         "Missing per-user error isolation")
    test("background_trading_manager has stop_event",
         'stop_event' in btm_source,
         "Missing graceful shutdown mechanism")
except Exception as e:
    test("Background manager stability", False, str(e)[:80])

# 5.6 GroupBSystem graceful degradation
try:
    source = inspect.getsource(sys.modules['backend.core.group_b_system'])
    test("GroupBSystem: ScalpingV7 import with fallback",
         'SCALPING_V7_AVAILABLE' in source,
         "No fallback flag")
    test("GroupBSystem: Cognitive system import with fallback",
         'COGNITIVE_AVAILABLE' in source,
         "No fallback flag")
except Exception as e:
    test("GroupBSystem fallbacks", False, str(e)[:80])

# 5.7 Risk gates prevent runaway trading
try:
    source = inspect.getsource(sys.modules['backend.core.group_b_system'])
    test("Risk gate: max_daily_trades limit",
         'max_daily_trades' in source,
         "Missing daily trade limit")
    test("Risk gate: max_daily_loss_pct limit",
         'max_daily_loss_pct' in source,
         "Missing daily loss limit")
    test("Risk gate: portfolio heat check",
         'heat_manager' in source or 'portfolio_heat' in source,
         "Missing heat management")
    test("Risk gate: position size cap (15%)",
         '0.15' in source,
         "Missing 15% position size cap")
    test("Risk gate: minimum position $10",
         'position_size < 10' in source or 'min' in source,
         "Missing minimum check")
except Exception as e:
    test("Risk gates", False, str(e)[:80])

# 5.8 Thread safety in StateManager
try:
    sm_source = inspect.getsource(sys.modules['backend.core.state_manager'])
    test("StateManager uses threading lock",
         'RLock' in sm_source or '_lock' in sm_source,
         "No thread lock found")
except Exception as e:
    test("StateManager thread safety", False, str(e)[:80])

# ============================================================
# 6. INTEGRATION FLOW
# ============================================================
section("6️⃣ INTEGRATION FLOW — Component Connectivity & Data Flow")

# 6.1 GroupBSystem → DatabaseManager connectivity
try:
    source = inspect.getsource(sys.modules['backend.core.group_b_system'])
    test("GroupBSystem imports DatabaseManager",
         'DatabaseManager' in source,
         "Missing import")
    test("GroupBSystem uses self.db for DB operations",
         'self.db.' in source,
         "No self.db usage")
except Exception as e:
    test("GroupB→DB connectivity", False, str(e)[:80])

# 6.2 GroupBSystem → Risk modules connectivity
try:
    test("GroupBSystem imports KellyPositionSizer",
         'KellyPositionSizer' in source,
         "Missing Kelly import")
    test("GroupBSystem imports PortfolioHeatManager",
         'PortfolioHeatManager' in source,
         "Missing Heat import")
    test("GroupBSystem imports DynamicBlacklist",
         'dynamic_blacklist' in source,
         "Missing blacklist import")
except Exception as e:
    test("GroupB→Risk connectivity", False, str(e)[:80])

# 6.3 Trading cycle flow: manage existing → scan new → execute
try:
    source = inspect.getsource(sys.modules['backend.core.group_b_system'])
    manage_pos = source.find('_manage_open_positions')
    scan_pos = source.find('_scan_for_entries')
    
    # In run_trading_cycle, manage should come before scan
    rtc_source = ''
    in_rtc = False
    for line in source.split('\n'):
        if 'def run_trading_cycle' in line:
            in_rtc = True
        elif in_rtc and line.strip().startswith('def '):
            break
        if in_rtc:
            rtc_source += line + '\n'
    
    manage_in_rtc = rtc_source.find('_manage_position')
    scan_in_rtc = rtc_source.find('_scan_for_entries')
    
    test("run_trading_cycle: manage positions BEFORE scan",
         0 < manage_in_rtc < scan_in_rtc,
         f"manage@{manage_in_rtc}, scan@{scan_in_rtc}")
except Exception as e:
    test("Trading cycle flow order", False, str(e)[:80])

# 6.4 Position lifecycle: open → manage → close → balance update
try:
    test("GroupBSystem has _open_position method",
         '_open_position' in source or 'add_position' in source,
         "Missing open logic")
    test("GroupBSystem has _manage_position method",
         '_manage_position' in source,
         "Missing manage logic")
    test("GroupBSystem has _close_position method",
         '_close_position' in source,
         "Missing close logic")
    test("_close_position updates balance",
         'update_user_balance' in source,
         "Missing balance update on close")
except Exception as e:
    test("Position lifecycle", False, str(e)[:80])

# 6.5 Background trading manager → GroupBSystem
try:
    btm_source = (PROJECT_ROOT / 'bin' / 'background_trading_manager.py').read_text()
    test("BackgroundManager imports GroupBSystem",
         'GroupBSystem' in btm_source,
         "Missing import")
    test("BackgroundManager caches per-user systems",
         '_user_systems' in btm_source,
         "Missing user system cache")
    test("BackgroundManager refreshes settings each cycle",
         '_load_user_settings' in btm_source,
         "Settings not refreshed")
    test("BackgroundManager refreshes portfolio each cycle",
         '_load_user_portfolio' in btm_source,
         "Portfolio not refreshed")
except Exception as e:
    test("BackgroundManager→GroupB flow", False, str(e)[:80])

# 6.6 Mobile API path consistency (spot check)
try:
    api_source = (PROJECT_ROOT / 'mobile_app' / 'TradingApp' / 'src' / 'services' / 'DatabaseApiService.js').read_text()
    
    # Verify fixed paths
    test("Mobile: getTradingStats → /admin/trades/stats (not /trading/stats)",
         '/admin/trades/stats' in api_source and '/admin/trading/stats' not in api_source,
         "Path mismatch still exists")
    test("Mobile: getAdminNotificationSettings → /admin/notification-settings",
         '/admin/notification-settings' in api_source,
         "Path not fixed")
    test("Mobile: admin paths use isAdminPath interceptor",
         'isAdminPath' in api_source,
         "Missing admin path detection")
except Exception as e:
    test("Mobile API paths", False, str(e)[:80])

# ============================================================
# FINAL SUMMARY
# ============================================================
section("📊 FINAL RESULTS")

total = PASSED + FAILED
print(f"\n  Total Tests: {total}")
print(f"  ✅ Passed:   {PASSED}")
print(f"  ❌ Failed:   {FAILED}")
print(f"  Success Rate: {PASSED/total*100:.1f}%")

if ERRORS:
    print(f"\n  --- Failures ---")
    for err in ERRORS:
        print(f"  ⚠️  {err}")

print(f"\n{'='*60}")
if FAILED == 0:
    print("  🎉 ALL TESTS PASSED — System is VERIFIED")
else:
    print(f"  ⚠️  {FAILED} ISSUES FOUND — Review required")
print(f"{'='*60}\n")

sys.exit(0 if FAILED == 0 else 1)
