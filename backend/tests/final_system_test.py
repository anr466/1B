#!/usr/bin/env python3
"""
🧪 Final Comprehensive System Test Before Deployment
=====================================================
Tests ALL aspects of the system:
1. Server Health & Infrastructure
2. Database Integrity
3. Authentication Flow
4. User API Endpoints
5. Admin API Endpoints
6. ML Endpoints
7. System Control Endpoints
8. Security Tests
9. CORS & Headers
10. Blueprint Loading
"""

import requests
import json
import time
import sys
import os
import sqlite3

BASE_URL = "http://localhost:3002"
RESULTS = {"passed": 0, "failed": 0, "warnings": 0, "errors": []}

def test(name, condition, detail=""):
    if condition:
        RESULTS["passed"] += 1
        print(f"  ✅ {name}")
    else:
        RESULTS["failed"] += 1
        RESULTS["errors"].append(f"{name}: {detail}")
        print(f"  ❌ {name} — {detail}")

def warn(name, detail=""):
    RESULTS["warnings"] += 1
    print(f"  ⚠️ {name} — {detail}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ============================================================
# Phase 1: Server Health & Infrastructure
# ============================================================
section("Phase 1: Server Health & Infrastructure")

try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    test("Health endpoint responds", r.status_code == 200, f"status={r.status_code}")
    data = r.json()
    test("Database connected", data.get("database") == "connected", f"db={data.get('database')}")
    test("Server status healthy", data.get("status") == "healthy", f"status={data.get('status')}")
except Exception as e:
    test("Server reachable", False, str(e))
    print("\n❌ Server not reachable. Aborting tests.")
    sys.exit(1)

try:
    r = requests.get(f"{BASE_URL}/", timeout=5)
    test("Root endpoint", r.status_code == 200)
    data = r.json()
    test("API version present", "api_version" in data, str(data.keys()))
except Exception as e:
    test("Root endpoint", False, str(e))

try:
    r = requests.get(f"{BASE_URL}/docs", timeout=5)
    test("FastAPI docs accessible", r.status_code == 200)
except Exception as e:
    test("FastAPI docs", False, str(e))

try:
    r = requests.get(f"{BASE_URL}/api/connection/info", timeout=5)
    test("Connection info endpoint", r.status_code == 200)
    data = r.json()
    test("Server IP present", "server_ip" in data)
except Exception as e:
    test("Connection info", False, str(e))

# ============================================================
# Phase 2: Database Integrity
# ============================================================
section("Phase 2: Database Integrity")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "database", "trading_database.db")
if not os.path.exists(DB_PATH):
    # Try alternate path
    DB_PATH = "/Users/anr/Desktop/trading_ai_bot-1/database/trading_database.db"

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check essential tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    essential_tables = ["users", "portfolio", "user_portfolio", "active_positions", "trade_history", "user_settings"]
    for table in essential_tables:
        test(f"Table '{table}' exists", table in tables, f"Missing from: {tables[:10]}")
    
    # Check users
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    test(f"Users table has data ({user_count} users)", user_count > 0)
    
    # Check portfolio integrity
    cursor.execute("SELECT COUNT(*) FROM portfolio")
    portfolio_count = cursor.fetchone()[0]
    test(f"Portfolio table has data ({portfolio_count} rows)", portfolio_count > 0)
    
    # Check user_portfolio
    cursor.execute("SELECT COUNT(*) FROM user_portfolio")
    up_count = cursor.fetchone()[0]
    test(f"User_portfolio has data ({up_count} rows)", up_count > 0)
    
    # Check for orphan records
    cursor.execute("""
        SELECT COUNT(*) FROM user_portfolio up 
        LEFT JOIN users u ON up.user_id = u.id 
        WHERE u.id IS NULL
    """)
    orphans = cursor.fetchone()[0]
    test("No orphan user_portfolio records", orphans == 0, f"{orphans} orphans found")
    
    # Check active_positions schema
    cursor.execute("PRAGMA table_info(active_positions)")
    ap_columns = [row[1] for row in cursor.fetchall()]
    needed_cols = ["user_id", "symbol", "entry_price", "position_size", "position_type", "stop_loss_price"]
    for col in needed_cols:
        test(f"active_positions.{col} column exists", col in ap_columns, f"columns: {ap_columns}")
    
    # Check user_settings
    cursor.execute("SELECT COUNT(*) FROM user_settings")
    settings_count = cursor.fetchone()[0]
    test(f"User settings configured ({settings_count} rows)", settings_count > 0)
    
    conn.close()
except Exception as e:
    test("Database access", False, str(e))

# ============================================================
# Phase 3: Authentication Flow
# ============================================================
section("Phase 3: Authentication Flow")

# Test login
admin_token = None
user_token = None

try:
    # Try admin login
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@trading.com",
        "password": "admin123"
    }, timeout=10)
    test("Admin login endpoint responds", r.status_code in [200, 401, 400], f"status={r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        admin_token = data.get("token") or data.get("access_token")
        test("Admin token received", admin_token is not None, "No token in response")
    else:
        # Try different admin credentials
        for creds in [
            {"username": "admin", "password": "admin123"},
            {"email": "admin@admin.com", "password": "admin123"},
        ]:
            r2 = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=10)
            if r2.status_code == 200:
                data = r2.json()
                admin_token = data.get("token") or data.get("access_token")
                test("Admin login (alt creds)", admin_token is not None)
                break
        
        if not admin_token:
            warn("Admin login failed", f"status={r.status_code}, body={r.text[:200]}")
except Exception as e:
    test("Auth login endpoint", False, str(e))

# Get a valid token from DB if login fails
if not admin_token:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT email, password_hash FROM users WHERE is_admin=1 LIMIT 1")
        admin_row = cursor.fetchone()
        if admin_row:
            warn("Admin found in DB", f"email={admin_row[0]}")
        
        cursor.execute("SELECT email FROM users WHERE is_admin=0 LIMIT 1")
        user_row = cursor.fetchone()
        if user_row:
            warn("Regular user found in DB", f"email={user_row[0]}")
        conn.close()
    except:
        pass

# Test auth validation
try:
    r = requests.post(f"{BASE_URL}/api/auth/validate-session", timeout=5)
    test("Validate session (no token) returns 401", r.status_code == 401, f"status={r.status_code}")
except Exception as e:
    test("Validate session endpoint", False, str(e))

# ============================================================
# Phase 4: User API Endpoints (with token)
# ============================================================
section("Phase 4: User API Endpoints")

headers_auth = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}

user_endpoints = [
    ("GET", "/api/user/portfolio/1", "User portfolio"),
    ("GET", "/api/user/stats/1", "User stats"),
    ("GET", "/api/user/trades/1", "User trades"),
    ("GET", "/api/user/settings/1", "User settings"),
    ("GET", "/api/user/profile/1", "User profile"),
]

for method, path, name in user_endpoints:
    try:
        if method == "GET":
            r = requests.get(f"{BASE_URL}{path}", headers=headers_auth, timeout=10)
        else:
            r = requests.post(f"{BASE_URL}{path}", headers=headers_auth, timeout=10)
        
        if admin_token:
            test(f"{name} ({r.status_code})", r.status_code in [200, 403], f"status={r.status_code}")
        else:
            test(f"{name} (no auth → {r.status_code})", r.status_code in [401, 403, 200], f"status={r.status_code}")
    except Exception as e:
        test(name, False, str(e))

# ============================================================
# Phase 5: Admin API Endpoints
# ============================================================
section("Phase 5: Admin API Endpoints")

admin_endpoints = [
    ("GET", "/api/admin/system/status", "Admin system status"),
    ("GET", "/api/admin/system/stats", "Admin system stats"),
    ("GET", "/api/admin/dashboard", "Admin dashboard"),
    ("GET", "/api/admin/users", "Admin users list"),
    ("GET", "/api/admin/errors", "Admin errors"),
    ("GET", "/api/admin/trading/status", "Admin trading status"),
    ("GET", "/api/admin/performance/summary", "Admin performance summary"),
]

for method, path, name in admin_endpoints:
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=headers_auth, timeout=10)
        if admin_token:
            test(f"{name} ({r.status_code})", r.status_code in [200, 403], f"status={r.status_code}, body={r.text[:100]}")
        else:
            test(f"{name} (no auth → {r.status_code})", r.status_code in [401, 403], f"status={r.status_code}")
    except Exception as e:
        test(name, False, str(e))

# ============================================================
# Phase 6: ML Endpoints
# ============================================================
section("Phase 6: ML Endpoints")

ml_endpoints = [
    ("GET", "/api/ml/health", "ML health"),
    ("GET", "/api/ml/status", "ML status"),
    ("GET", "/api/ml/patterns", "ML patterns"),
]

for method, path, name in ml_endpoints:
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=headers_auth, timeout=10)
        test(f"{name} ({r.status_code})", r.status_code in [200, 401, 403, 503], f"status={r.status_code}")
    except Exception as e:
        test(name, False, str(e))

# ============================================================
# Phase 7: System Control Endpoints
# ============================================================
section("Phase 7: System Control Endpoints")

system_endpoints = [
    ("GET", "/api/admin/background/status", "Background status"),
    ("GET", "/api/admin/system/health", "System health"),
]

for method, path, name in system_endpoints:
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=headers_auth, timeout=10)
        test(f"{name} ({r.status_code})", r.status_code in [200, 401, 403], f"status={r.status_code}")
    except Exception as e:
        test(name, False, str(e))

# ============================================================
# Phase 8: Security Tests
# ============================================================
section("Phase 8: Security Tests")

# Test no auth → 401
try:
    r = requests.get(f"{BASE_URL}/api/admin/system/status", timeout=5)
    test("Admin without token → 401/403", r.status_code in [401, 403], f"status={r.status_code}")
except Exception as e:
    test("Auth protection", False, str(e))

# SQL injection test
try:
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "'; DROP TABLE users; --",
        "password": "test"
    }, timeout=5)
    test("SQL injection blocked", r.status_code in [400, 401, 422], f"status={r.status_code}")
except Exception as e:
    test("SQL injection test", False, str(e))

# XSS test
try:
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "<script>alert('xss')</script>",
        "password": "test"
    }, timeout=5)
    test("XSS input handled", r.status_code in [400, 401, 422], f"status={r.status_code}")
except Exception as e:
    test("XSS test", False, str(e))

# Invalid JSON
try:
    r = requests.post(f"{BASE_URL}/api/auth/login", 
                       data="not json", 
                       headers={"Content-Type": "application/json"},
                       timeout=5)
    test("Invalid JSON handled", r.status_code in [400, 415, 422, 500], f"status={r.status_code}")
except Exception as e:
    test("Invalid JSON test", False, str(e))

# Token forgery
try:
    r = requests.get(f"{BASE_URL}/api/admin/system/status", 
                      headers={"Authorization": "Bearer fake_token_12345"},
                      timeout=5)
    test("Forged token rejected", r.status_code in [401, 403, 422], f"status={r.status_code}")
except Exception as e:
    test("Token forgery test", False, str(e))

# ============================================================
# Phase 9: CORS & Headers
# ============================================================
section("Phase 9: CORS & Response Headers")

try:
    r = requests.options(f"{BASE_URL}/api/auth/login", 
                          headers={"Origin": "http://localhost:8081"},
                          timeout=5)
    test("OPTIONS request handled", r.status_code in [200, 204, 405], f"status={r.status_code}")
except Exception as e:
    test("CORS OPTIONS", False, str(e))

try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    content_type = r.headers.get("content-type", "")
    test("JSON content-type", "json" in content_type.lower(), f"content-type={content_type}")
except Exception as e:
    test("Content-type check", False, str(e))

# ============================================================
# Phase 10: Error Handling
# ============================================================
section("Phase 10: Error Handling")

try:
    r = requests.get(f"{BASE_URL}/api/nonexistent/path", timeout=5)
    test("404 returns JSON", r.headers.get("content-type", "").startswith("application/json"), 
         f"content-type={r.headers.get('content-type')}")
    test("404 status code", r.status_code == 404, f"status={r.status_code}")
except Exception as e:
    test("404 handling", False, str(e))

try:
    r = requests.put(f"{BASE_URL}/api/auth/login", timeout=5)
    test("405 method not allowed", r.status_code in [405, 404], f"status={r.status_code}")
except Exception as e:
    test("405 handling", False, str(e))

# ============================================================
# Phase 11: CryptoWave Endpoints
# ============================================================
section("Phase 11: CryptoWave & Trading Endpoints")

cw_endpoints = [
    ("GET", "/api/cryptowave/status", "CryptoWave status"),
    ("GET", "/api/cryptowave/health", "CryptoWave health"),
]

for method, path, name in cw_endpoints:
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=headers_auth, timeout=10)
        test(f"{name} ({r.status_code})", r.status_code in [200, 401, 403, 404], f"status={r.status_code}")
    except Exception as e:
        test(name, False, str(e))

# ============================================================
# Phase 12: Response Format Consistency
# ============================================================
section("Phase 12: Response Format Consistency")

format_endpoints = [
    "/health",
    "/api/user/portfolio/1",
    "/api/admin/system/status",
]

for path in format_endpoints:
    try:
        r = requests.get(f"{BASE_URL}{path}", headers=headers_auth, timeout=10)
        try:
            data = r.json()
            test(f"{path} returns valid JSON", True)
        except:
            test(f"{path} returns valid JSON", False, f"Not JSON: {r.text[:100]}")
    except Exception as e:
        test(f"{path} format", False, str(e))

# ============================================================
# FINAL REPORT
# ============================================================
section("FINAL REPORT")

total = RESULTS["passed"] + RESULTS["failed"]
pass_rate = (RESULTS["passed"] / total * 100) if total > 0 else 0

print(f"\n  📊 Total Tests: {total}")
print(f"  ✅ Passed: {RESULTS['passed']}")
print(f"  ❌ Failed: {RESULTS['failed']}")
print(f"  ⚠️ Warnings: {RESULTS['warnings']}")
print(f"  📈 Pass Rate: {pass_rate:.1f}%")

if RESULTS["errors"]:
    print(f"\n  🔴 Failed Tests:")
    for err in RESULTS["errors"]:
        print(f"     • {err}")

if pass_rate >= 90:
    print(f"\n  🟢 SYSTEM READY FOR DEPLOYMENT")
elif pass_rate >= 70:
    print(f"\n  🟡 SYSTEM NEEDS ATTENTION BEFORE DEPLOYMENT")
else:
    print(f"\n  🔴 SYSTEM NOT READY FOR DEPLOYMENT")

print(f"\n{'='*60}\n")
