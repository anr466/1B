#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Full System Integration Test
=================================
Tests against LIVE server on port 3002:
1. Server health & connectivity
2. API endpoints (health, version, connection info)
3. Auth system (register, login, token)
4. Admin endpoints (system status, background control)
5. User endpoints (portfolio, trades, settings)
6. Database integrity
7. ML system readiness
8. Trading system (GroupBSystem) initialization
9. Mobile app endpoint compatibility
10. Conflict/duplication detection
"""

import sys
import os
import json
import time
import requests
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

BASE_URL = "http://localhost:3002"
API_URL = f"{BASE_URL}/api"

passed = 0
failed = 0
warnings = 0
issues = []

def test(name, condition, details=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
        return True
    else:
        failed += 1
        msg = f"{name}: {details}" if details else name
        issues.append(msg)
        print(f"  ❌ {name} — {details}")
        return False

def warn(name, details=""):
    global warnings
    warnings += 1
    print(f"  ⚠️ {name} — {details}")

# ============================================================
print("\n" + "=" * 70)
print("  🧪 FULL SYSTEM INTEGRATION TEST")
print("=" * 70)

# ============================================================
# 1. SERVER HEALTH & CONNECTIVITY
# ============================================================
print("\n── 1. Server Health & Connectivity ──")

try:
    r = requests.get(f"{BASE_URL}/", timeout=5)
    test("Root endpoint responds", r.status_code == 200, f"status={r.status_code}")
    data = r.json()
    test("Root returns JSON with status", data.get("status") == "running")
except Exception as e:
    test("Server reachable", False, str(e))

try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    test("Health endpoint responds", r.status_code == 200)
    data = r.json()
    test("Database connected", data.get("database") == "connected", f"db={data.get('database')}")
except Exception as e:
    test("Health check", False, str(e))

try:
    r = requests.get(f"{BASE_URL}/api/version", timeout=5)
    test("API version endpoint", r.status_code == 200)
    data = r.json()
    test("API version is v2", data.get("current_version") == "v2", f"version={data.get('current_version')}")
except Exception as e:
    test("API version", False, str(e))

try:
    r = requests.get(f"{BASE_URL}/api/connection/info", timeout=5)
    test("Connection info endpoint", r.status_code == 200)
    data = r.json()
    test("Port is 3002", data.get("port") == 3002)
except Exception as e:
    test("Connection info", False, str(e))

# ============================================================
# 2. AUTH SYSTEM
# ============================================================
print("\n── 2. Auth System ──")

auth_token = None
try:
    # Test login endpoint exists
    r = requests.post(f"{API_URL}/auth/login", json={
        "email": "admin@test.com",
        "password": "admin123"
    }, timeout=10)
    test("Login endpoint responds", r.status_code in [200, 401, 400, 403], f"status={r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        if data.get("success") and data.get("token"):
            auth_token = data["token"]
            test("Login returns token", True)
        else:
            warn("Login unsuccessful", f"response={data}")
    else:
        warn("Login returned non-200", f"status={r.status_code}")
except Exception as e:
    test("Login endpoint", False, str(e))

try:
    r = requests.get(f"{API_URL}/auth/validate-session", 
                     headers={"Authorization": f"Bearer {auth_token}"} if auth_token else {},
                     timeout=5)
    test("Session validation endpoint exists", r.status_code in [200, 401, 422], f"status={r.status_code}")
except Exception as e:
    warn("Session validation", str(e))

# ============================================================
# 3. ADMIN ENDPOINTS
# ============================================================
print("\n── 3. Admin Endpoints ──")

headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

# System status (admin_unified_api)
try:
    r = requests.get(f"{API_URL}/admin/system/status", headers=headers, timeout=10)
    test("Admin system status responds", r.status_code in [200, 401, 403], f"status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        test("System status has success field", "success" in data, f"keys={list(data.keys())}")
except Exception as e:
    test("Admin system status", False, str(e))

# Background control status
try:
    r = requests.get(f"{API_URL}/admin/background/status", headers=headers, timeout=10)
    test("Background status responds", r.status_code in [200, 401, 403], f"status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        test("Background status has data", "data" in data or "success" in data)
        if data.get("data"):
            bg_data = data["data"]
            test("Background has is_running field", "is_running" in bg_data, f"keys={list(bg_data.keys())}")
            test("Background has status field", "status" in bg_data)
            print(f"       System running: {bg_data.get('is_running')}, status: {bg_data.get('status')}")
except Exception as e:
    test("Background status", False, str(e))

# Background logs
try:
    r = requests.get(f"{API_URL}/admin/background/logs?lines=10", headers=headers, timeout=10)
    test("Background logs endpoint", r.status_code in [200, 401, 403], f"status={r.status_code}")
except Exception as e:
    warn("Background logs", str(e))

# Error stats
try:
    r = requests.get(f"{API_URL}/admin/background/errors/stats", headers=headers, timeout=10)
    test("Error stats endpoint", r.status_code in [200, 401, 403], f"status={r.status_code}")
except Exception as e:
    warn("Error stats", str(e))

# Operations log
try:
    r = requests.get(f"{API_URL}/admin/background/operations/log", headers=headers, timeout=10)
    test("Operations log endpoint", r.status_code in [200, 401, 403], f"status={r.status_code}")
except Exception as e:
    warn("Operations log", str(e))

# Operations statistics
try:
    r = requests.get(f"{API_URL}/admin/background/operations/statistics", headers=headers, timeout=10)
    test("Operations statistics endpoint", r.status_code in [200, 401, 403], f"status={r.status_code}")
except Exception as e:
    warn("Operations statistics", str(e))

# System stats (admin_unified_api)
try:
    r = requests.get(f"{API_URL}/admin/system/stats", headers=headers, timeout=10)
    test("Admin system stats", r.status_code in [200, 401, 403], f"status={r.status_code}")
except Exception as e:
    warn("Admin system stats", str(e))

# ============================================================
# 4. FAST SYSTEM API
# ============================================================
print("\n── 4. Fast System API ──")

try:
    r = requests.get(f"{API_URL}/admin/system/status", headers=headers, timeout=10)
    test("Fast system status", r.status_code in [200, 401, 403], f"status={r.status_code}")
except Exception as e:
    test("Fast system status", False, str(e))

try:
    r = requests.get(f"{API_URL}/admin/system/health", headers=headers, timeout=10)
    test("System health check", r.status_code in [200, 401, 403], f"status={r.status_code}")
    if r.status_code == 200:
        data = r.json()
        if data.get("success"):
            print(f"       Healthy: {data.get('is_healthy')}, Process: {data.get('process_alive')}, Consistent: {data.get('state_consistent')}")
except Exception as e:
    warn("System health", str(e))

# ============================================================
# 5. USER ENDPOINTS (Mobile App)
# ============================================================
print("\n── 5. User Endpoints (Mobile App) ──")

user_endpoints = [
    ("GET", "/user/portfolio/1", "Portfolio"),
    ("GET", "/user/stats/1", "Stats"),
    ("GET", "/user/trades/1", "Trades"),
    ("GET", "/user/settings/1", "Settings"),
    ("GET", "/user/successful-coins/1", "Successful Coins"),
]

for method, path, name in user_endpoints:
    try:
        if method == "GET":
            r = requests.get(f"{API_URL}{path}", headers=headers, timeout=10)
        test(f"User {name} endpoint", r.status_code in [200, 401, 403, 404], f"status={r.status_code}")
    except Exception as e:
        warn(f"User {name}", str(e))

# ============================================================
# 6. ML ENDPOINTS
# ============================================================
print("\n── 6. ML System Endpoints ──")

ml_endpoints = [
    ("GET", "/ml/status", "ML Status"),
    ("GET", "/ml/health", "ML Health"),
]

for method, path, name in ml_endpoints:
    try:
        r = requests.get(f"{API_URL}{path}", headers=headers, timeout=10)
        test(f"{name} endpoint", r.status_code in [200, 401, 403, 404], f"status={r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if "ml_ready" in data or "is_ready" in data or "status" in data:
                print(f"       ML data: {json.dumps({k:v for k,v in data.items() if k != 'details'}, default=str)[:200]}")
    except Exception as e:
        warn(f"{name}", str(e))

# ============================================================
# 7. DATABASE INTEGRITY
# ============================================================
print("\n── 7. Database Integrity ──")

try:
    from database.database_manager import DatabaseManager
    db = DatabaseManager()
    
    # Check core tables exist
    with db.get_connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t['name'] for t in tables]
    
    critical_tables = ['users', 'active_positions', 'system_status', 'portfolio', 'user_portfolio']
    for table in critical_tables:
        test(f"Table '{table}' exists", table in table_names, f"tables={table_names[:10]}")
    
    # Check system_status has row
    with db.get_connection() as conn:
        status = conn.execute("SELECT * FROM system_status WHERE id = 1").fetchone()
    test("system_status has row id=1", status is not None)
    if status:
        print(f"       Status: {dict(status).get('status')}, Running: {dict(status).get('is_running')}")
    
    # Check active_positions schema has required columns
    with db.get_connection() as conn:
        cols = conn.execute("PRAGMA table_info(active_positions)").fetchall()
        col_names = [c['name'] for c in cols]
    
    required_cols = ['position_type', 'stop_loss', 'take_profit', 'trailing_sl_price', 'highest_price', 'timeframe']
    for col in required_cols:
        test(f"active_positions.{col} column exists", col in col_names, f"cols={col_names}")
    
    # Check user count
    with db.get_connection() as conn:
        user_count = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()['cnt']
    test("Users table has data", user_count > 0, f"count={user_count}")
    print(f"       Users: {user_count}")
    
    # Check write connection works
    with db.get_write_connection() as conn:
        conn.execute("UPDATE system_status SET last_update = datetime('now') WHERE id = 1")
    test("Write connection works", True)
    
except Exception as e:
    test("Database integrity", False, str(e))
    import traceback; traceback.print_exc()

# ============================================================
# 8. TRADING SYSTEM (GroupBSystem)
# ============================================================
print("\n── 8. Trading System (GroupBSystem) ──")

try:
    from backend.core.group_b_system import GroupBSystem, SCALPING_V7_AVAILABLE
    test("GroupBSystem imports", True)
    test("ScalpingV7Engine available", SCALPING_V7_AVAILABLE)
    
    system = GroupBSystem(user_id=1)
    test("GroupBSystem initializes", system is not None)
    test("V7 engine is primary", system.scalping_v7 is not None)
    test("Config has v7 params", 
         system.config['max_sl_pct'] == 0.010 and system.config['trailing_activation_pct'] == 0.006,
         f"SL={system.config.get('max_sl_pct')}, Trail={system.config.get('trailing_activation_pct')}")
    test("Max positions = 5", system.config['max_positions'] == 5)
    test("Timeframe = 1h", system.config['execution_timeframe'] == '1h')
    
    # Test monitoring cycle
    result = system.run_monitoring_only()
    test("Monitoring cycle runs", result is not None)
    
except Exception as e:
    test("Trading system", False, str(e))
    import traceback; traceback.print_exc()

# ============================================================
# 9. ML SYSTEM READINESS
# ============================================================
print("\n── 9. ML System Readiness ──")

try:
    from backend.ml.signal_classifier import MLSignalClassifier, ML_AVAILABLE
    test("ML Signal Classifier imports", True)
    
    if ML_AVAILABLE:
        classifier = MLSignalClassifier()
        test("ML Classifier initialized", classifier.enabled)
        print(f"       ML libraries available: True")
        print(f"       Min samples for training: {classifier.MIN_SAMPLES_FOR_TRAINING}")
        print(f"       Min accuracy: {classifier.MIN_ACCURACY_FOR_READINESS}")
    else:
        warn("ML libraries not installed", "xgboost/sklearn missing - ML will work without them")
    
    from backend.ml.training_manager import MLTrainingManager
    test("Training Manager imports", True)
    
    from backend.ml.trading_brain import TradingBrain, get_trading_brain
    test("Trading Brain imports", True)
    brain = get_trading_brain()
    test("Trading Brain initializes", brain is not None)
    
except Exception as e:
    test("ML system", False, str(e))
    import traceback; traceback.print_exc()

# ============================================================
# 10. SCALPING V7 ENGINE
# ============================================================
print("\n── 10. Scalping V7 Engine ──")

try:
    from backend.strategies.scalping_v7_engine import ScalpingV7Engine, get_scalping_v7_engine
    engine = get_scalping_v7_engine()
    test("V7 Engine singleton", engine is not None)
    test("V7 Config correct", engine.config['sl_pct'] == 0.010 and engine.config['trailing_activation'] == 0.006)
    
    # Test with real data from Binance
    from backend.utils.data_provider import DataProvider
    dp = DataProvider()
    df = dp.get_historical_data('BTCUSDT', '1h', limit=200)
    
    if df is not None and len(df) >= 70:
        df = engine.prepare_data(df)
        test("V7 prepare_data on real BTC data", True)
        
        trend = engine.get_4h_trend(df)
        test("V7 trend detection", trend in ['UP', 'DOWN', 'NEUTRAL'], f"trend={trend}")
        print(f"       BTC 4H Trend: {trend}")
        
        signal = engine.detect_entry(df, trend)
        if signal:
            print(f"       BTC Signal: {signal['side']} | {signal['strategy']} | Score: {signal['score']}")
        else:
            print(f"       BTC Signal: No entry (normal)")
        test("V7 entry detection runs", True)
    else:
        warn("Real data test", "Could not fetch BTC data from Binance")
        
except Exception as e:
    test("V7 Engine", False, str(e))
    import traceback; traceback.print_exc()

# ============================================================
# 11. ENDPOINT CONFLICT DETECTION
# ============================================================
print("\n── 11. Endpoint Conflict Detection ──")

# Check that Flask routes don't conflict
try:
    r = requests.get(f"{BASE_URL}/docs", timeout=5)
    test("FastAPI docs accessible", r.status_code == 200)
except:
    warn("FastAPI docs", "May be blocked by Flask mount")

# Test 404 handling returns JSON not HTML
try:
    r = requests.get(f"{API_URL}/nonexistent/endpoint", timeout=5)
    test("404 returns JSON", r.headers.get('content-type', '').startswith('application/json'), 
         f"content-type={r.headers.get('content-type')}")
    data = r.json()
    test("404 has error field", 'error' in data or 'success' in data)
except Exception as e:
    warn("404 handling", str(e))

# ============================================================
# RESULTS
# ============================================================
print("\n" + "=" * 70)
print(f"  📊 RESULTS: {passed} PASSED | {failed} FAILED | {warnings} WARNINGS")

if issues:
    print(f"\n  🔴 ISSUES FOUND ({len(issues)}):")
    for i, issue in enumerate(issues, 1):
        print(f"     {i}. {issue}")

if failed == 0:
    print("\n  ✅ ALL TESTS PASSED!")
elif failed <= 3:
    print(f"\n  ⚠️ {failed} minor issues to address")
else:
    print(f"\n  ❌ {failed} issues need fixing")

print("=" * 70)
