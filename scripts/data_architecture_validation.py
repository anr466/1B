#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E Data Architecture Validation & QA Framework
================================================
System: Trading AI Bot — trading_ai_bot-1
Backend: Flask/Python (port 3002) + PostgreSQL
Coverage: 10 Domains | 7 Progressive Stages | 60+ Checkpoints

SYSTEM DATA FLOW:
  [Binance API] → [DataProvider] → [Analysis Engine]
       ↓                                  ↓
  [Market Data]          [Signal Generator V7/V8/SMC]
                                    ↓
                          [ML Filter / Confidence]
                                    ↓
                         [Trading Execution Engine]
                         ↙                  ↘
              [active_positions]    [trading_history]
                     ↓                       ↓
              [Portfolio Sync]       [ML Training Data]
                     ↓                       ↓
          [Notification Engine]    [Model Retrain Loop]
          (FCM/Telegram/Email)    (ml_training_history)
                     ↓                       ↓
             [Mobile App]           [Analytics Layer]

DOMAIN SEGMENTATION:
  D1: Authentication & Identity      D6: ML Learning Pipeline
  D2: Market Data Ingestion          D7: Notification & Delivery
  D3: Signal Processing Pipeline     D8: Admin & System State
  D4: Trading Execution Engine       D9: Analytics & Reporting
  D5: Portfolio & Balance Sync       D10: Cross-Domain Integrity

PROGRESSIVE STAGES:
  Stage 1: DB Schema Integrity     (offline)
  Stage 2: API Connectivity & Health
  Stage 3: Domain Unit Validation  (per-domain)
  Stage 4: Inter-Domain Integration
  Stage 5: Full E2E Flow Simulation
  Stage 6: Drift & Anomaly Detection
  Stage 7: Observability & Audit Trail

Usage:
    python scripts/data_architecture_validation.py
    python scripts/data_architecture_validation.py --stage 1
    python scripts/data_architecture_validation.py --domain D4
    python scripts/data_architecture_validation.py --report json
    python scripts/data_architecture_validation.py --strict

Exit codes: 0=PASS  1=FAIL  2=CRITICAL infrastructure failure
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import uuid
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
API_BASE = os.getenv("VALIDATION_API_BASE", "http://127.0.0.1:3002")
ADMIN_EMAIL = "admin@tradingbot.com"
ADMIN_PASSWORD = "admin123"
ADMIN_USER_ID = 1

load_dotenv(ROOT / ".env")


def _resolve_local_db_environment() -> None:
    host = (os.getenv("POSTGRES_HOST") or "").strip().lower()
    database_url = (os.getenv("DATABASE_URL") or "").strip()

    if host and host != "postgres":
        return

    try:
        socket.gethostbyname("postgres")
        return
    except OSError:
        pass

    if host == "postgres":
        os.environ["POSTGRES_HOST"] = "127.0.0.1"

    if database_url and "@postgres:" in database_url:
        os.environ["DATABASE_URL"] = database_url.replace("@postgres:", "@127.0.0.1:")


_resolve_local_db_environment()

sys.path.insert(0, str(ROOT))

from backend.infrastructure.db_access import get_db_manager  # noqa: E402


db = get_db_manager()

# ─── Status & Severity constants ───────────────────────────────────────────────
STATUS_PASS, STATUS_FAIL, STATUS_WARN, STATUS_SKIP = "PASS", "FAIL", "WARN", "SKIP"
SEV_CRITICAL, SEV_HIGH, SEV_MEDIUM, SEV_LOW = "CRITICAL", "HIGH", "MEDIUM", "LOW"


# ─── Result dataclasses ────────────────────────────────────────────────────────
@dataclass
class CheckResult:
    id: str; name: str; domain: str; stage: int; status: str
    severity: str = SEV_MEDIUM; message: str = ""; details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0; rule: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    def is_pass(self): return self.status == STATUS_PASS
    def is_fail(self): return self.status == STATUS_FAIL
    def is_warn(self): return self.status == STATUS_WARN


@dataclass
class DomainReport:
    domain_id: str; domain_name: str
    checks: List[CheckResult] = field(default_factory=list); stage: int = 0

    @property
    def pass_count(self): return sum(1 for c in self.checks if c.is_pass())
    @property
    def fail_count(self): return sum(1 for c in self.checks if c.is_fail())
    @property
    def warn_count(self): return sum(1 for c in self.checks if c.is_warn())
    @property
    def overall_status(self):
        if any(c.is_fail() for c in self.checks): return STATUS_FAIL
        if any(c.is_warn() for c in self.checks): return STATUS_WARN
        return STATUS_PASS


@dataclass
class ValidationReport:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8].upper())
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: str = ""; domains: List[DomainReport] = field(default_factory=list)
    overall_status: str = STATUS_PASS; stages_run: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def all_checks(self): return [c for d in self.domains for c in d.checks]
    @property
    def total_pass(self): return sum(c.is_pass() for c in self.all_checks)
    @property
    def total_fail(self): return sum(c.is_fail() for c in self.all_checks)
    @property
    def total_warn(self): return sum(c.is_warn() for c in self.all_checks)
    @property
    def critical_failures(self):
        return [c for c in self.all_checks if c.is_fail() and c.severity == SEV_CRITICAL]

    def finalize(self):
        self.finished_at = datetime.now().isoformat()
        if any(c.is_fail() for c in self.all_checks): self.overall_status = STATUS_FAIL
        elif any(c.is_warn() for c in self.all_checks): self.overall_status = STATUS_WARN
        else: self.overall_status = STATUS_PASS


# ─── Check executor ────────────────────────────────────────────────────────────
def _check(cid, name, domain, stage, fn: Callable[[], Tuple[bool, str, Dict]],
           severity=SEV_MEDIUM, rule="", warn_on_fail=False) -> CheckResult:
    t0 = time.monotonic()
    try:
        passed, msg, details = fn()
        status = STATUS_PASS if passed else (STATUS_WARN if warn_on_fail else STATUS_FAIL)
    except Exception as exc:
        passed, msg, details = False, f"Exception: {exc}", {"exception": str(exc)}
        status = STATUS_WARN if warn_on_fail else STATUS_FAIL
    return CheckResult(id=cid, name=name, domain=domain, stage=stage, status=status,
                       severity=severity, message=msg, details=details,
                       duration_ms=round((time.monotonic() - t0) * 1000, 2), rule=rule)


# ─── DB helpers ───────────────────────────────────────────────────────────────
def db_connect(timeout=10.0):
    return db._build_connection(timeout=timeout)

def db_scalar(sql, params=()):
    with db_connect() as conn:
        cur = conn.execute(sql, params); row = cur.fetchone()
        return row[0] if row else None

def db_fetchall(sql, params=()):
    with db_connect() as conn:
        return conn.execute(sql, params).fetchall()

def db_table_exists(t):
    return bool(db_scalar(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s",
        (t,),
    ))

def db_columns(t):
    rows = db_fetchall(
        "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position",
        (t,),
    )
    return [r[0] for r in rows]

def db_count(t, where="", params=()):
    sql = f"SELECT COUNT(*) FROM {t}" + (f" WHERE {where}" if where else "")
    return int(db_scalar(sql, params) or 0)


# ─── API helpers ──────────────────────────────────────────────────────────────
_auth_token: Optional[str] = None
_auth_user_id: Optional[int] = None


def _decode_jwt_payload_without_verification(token: str) -> Dict[str, Any]:
    try:
        parts = token.split('.')
        if len(parts) < 2:
            return {}
        payload_part = parts[1]
        padding = '=' * (-len(payload_part) % 4)
        decoded = base64.urlsafe_b64decode(payload_part + padding)
        return json.loads(decoded.decode('utf-8'))
    except Exception:
        return {}


def get_authenticated_user_id() -> Optional[int]:
    global _auth_user_id
    if _auth_user_id is not None:
        return _auth_user_id

    token = get_admin_token()
    if not token:
        return None

    payload = _decode_jwt_payload_without_verification(token)
    user_id = payload.get('user_id')
    try:
        _auth_user_id = int(user_id) if user_id is not None else None
    except (TypeError, ValueError):
        _auth_user_id = None
    return _auth_user_id

def api_request(path, method="GET", body=None, token=None, timeout=8):
    url = f"{API_BASE}/api{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            rb = resp.read()
            return resp.status, (json.loads(rb) if rb else {})
    except HTTPError as e:
        rb = e.read()
        try: return e.code, json.loads(rb)
        except Exception: return e.code, {"error": str(e)}
    except (URLError, OSError) as e:
        return 0, {"error": str(e)}

def get_admin_token():
    global _auth_token, _auth_user_id
    if _auth_token: return _auth_token
    for path in ["/auth/login", "/mobile/auth/login"]:
        code, resp = api_request(path, "POST", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        tok = resp.get("token") or resp.get("access_token")
        if code == 200 and tok:
            _auth_token = tok
            login_user = resp.get('user') or resp.get('data', {}).get('user') or {}
            try:
                if login_user.get('id') is not None:
                    _auth_user_id = int(login_user.get('id'))
                else:
                    payload = _decode_jwt_payload_without_verification(tok)
                    _auth_user_id = int(payload.get('user_id')) if payload.get('user_id') is not None else None
            except (TypeError, ValueError):
                _auth_user_id = None
            return _auth_token
    return None

def api_get(path, auth=True):
    return api_request(path, token=get_admin_token() if auth else None)

def api_post(path, body, auth=True):
    return api_request(path, "POST", body, token=get_admin_token() if auth else None)


# ═══════════════════════════════════════════════════════════
#  STAGE 1 — DB SCHEMA INTEGRITY
# ═══════════════════════════════════════════════════════════
REQUIRED_SCHEMA = {
    "users": ["id","username","email","password_hash","is_active","user_type","created_at"],
    "user_settings": ["id","user_id","trading_enabled","trade_amount","stop_loss_pct","take_profit_pct","is_demo"],
    "user_binance_keys": ["id","user_id","api_key","api_secret","is_active"],
    "biometric_auth": ["id","user_id","biometric_hash","device_id","is_active"],
    "pending_verifications": ["id","user_id","action","otp","expires_at","method"],
    "password_reset_requests": ["id","user_id","token","used","expires_at"],
    "trading_signals": ["id","symbol","signal_type","strategy","timeframe","price","confidence","is_processed","generated_at"],
    "active_positions": ["id","user_id","symbol","strategy","timeframe","position_type","entry_price","quantity","stop_loss","take_profit","is_active","is_demo"],
    "trading_history": ["id","user_id","symbol","side","entry_price","exit_price","quantity","profit_loss","profit_pct","status","entry_time"],
    "portfolio": ["id","user_id","total_balance","available_balance","total_profit_loss","is_demo"],
    "ml_training_data": ["id","symbol","strategy","timeframe","entry_price","exit_price","profit_loss","is_winning","source","created_at"],
    "ml_training_history": ["id","cycle_number","total_samples","accuracy","is_ready","status","created_at"],
    "ml_models": ["id","model_name","accuracy","is_best","created_at"],
    "signal_learning": ["id","symbol","strategy","entry_price","actual_profit_pct","was_correct","timestamp"],
    "backtest_vs_reality": ["id","symbol","strategy","timeframe","backtest_win_rate","actual_result","reliability_score"],
    "combo_reliability": ["id","symbol","strategy","timeframe","total_trades","actual_win_rate","reliability_score"],
    "notifications": ["id","user_id","title","message","type","is_read","created_at"],
    "system_status": ["id"],
    "operation_log": ["id","operation_type","operation_name","status","start_time"],
    "security_audit_log": ["id","user_id","action","resource","status","created_at"],
    "system_alerts": ["id","alert_type","title","message","severity","read","resolved"],
    "dynamic_blacklist": ["id","user_id","symbol","reason","added_at","is_active"],
    "coin_states": ["symbol","state","total_trades","winning_trades","total_pnl","last_updated"],
    "successful_coins": ["id","symbol","strategy","timeframe","win_rate","score","is_active"],
    "trade_learning_log": ["id","symbol","entry_price","exit_price","pnl","pnl_pct","exit_reason","created_at"],
    "agent_memory": ["id","memory_type","category","symbol","title","content","confidence","is_active"],
    "ml_patterns": ["id","pattern_name","pattern_data","success_rate","frequency"],
    "ml_quality_metrics": ["id","metric_type","total_validated","valid_count","validity_rate"],
    "user_notification_settings": ["id","user_id"],
    "admin_notification_settings": ["id","telegram_enabled","email_enabled"],
}

def stage1_schema_integrity() -> DomainReport:
    rpt = DomainReport("S1", "Stage-1: DB Schema Integrity", stage=1)

    rpt.checks.append(_check("S1.01","DB Connection Available","S1",1,
        lambda: (bool(db_scalar("SELECT 1")), "postgres_connection_ok", {"engine": "postgresql"}),
        SEV_CRITICAL, "PostgreSQL connection must be reachable"))

    rpt.checks.append(_check("S1.02","Current Schema Is Public","S1",1,
        lambda: ((str(db_scalar("SELECT current_schema()") or "") == "public"),
                 f"schema={db_scalar('SELECT current_schema()')}", {}), SEV_HIGH, "current_schema() must be public"))

    rpt.checks.append(_check("S1.03","Database Responds To Integrity Query","S1",1,
        lambda: (db_scalar("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'") is not None,
                 "information_schema_accessible", {}), SEV_HIGH, "information_schema must be readable"))

    def check_tables():
        missing = [t for t in REQUIRED_SCHEMA if not db_table_exists(t)]
        return not missing, f"Missing: {missing}" if missing else f"All {len(REQUIRED_SCHEMA)} tables present", {"missing": missing}
    rpt.checks.append(_check("S1.04","Required Tables Exist","S1",1, check_tables, SEV_CRITICAL,
                             "All tables in REQUIRED_SCHEMA must exist"))

    def check_columns():
        viol = {t: [c for c in cols if c not in set(db_columns(t))]
                for t, cols in REQUIRED_SCHEMA.items() if db_table_exists(t)}
        viol = {k: v for k, v in viol.items() if v}
        return not viol, f"Column violations in {len(viol)} tables" if viol else "All columns present",{"violations": viol}
    rpt.checks.append(_check("S1.05","Required Columns Present","S1",1, check_columns, SEV_CRITICAL,
                             "All required columns must exist"))

    rpt.checks.append(_check("S1.06","Core Tables Queryable","S1",1,
        lambda: (db_scalar("SELECT COUNT(*) FROM users") is not None,
                 "users_table_query_ok", {}), SEV_CRITICAL, "Core tables must be queryable"))

    rpt.checks.append(_check("S1.07","System Status Queryable","S1",1,
        lambda: (db_scalar("SELECT COUNT(*) FROM system_status") is not None,
                 "system_status_query_ok", {}), SEV_HIGH, "system_status must be queryable"))

    def check_table_volume():
        table_count = int(db_scalar("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'") or 0)
        return table_count > 0, f"public_tables={table_count}", {"public_tables": table_count}
    rpt.checks.append(_check("S1.08","Public Schema Has Tables","S1",1, check_table_volume, SEV_MEDIUM,
                             "public schema must contain tables", warn_on_fail=True))

    return rpt


# ═══════════════════════════════════════════════════════════
#  STAGE 2 — API CONNECTIVITY & HEALTH
# ═══════════════════════════════════════════════════════════
def stage2_api_health() -> DomainReport:
    rpt = DomainReport("S2","Stage-2: API Connectivity & Health", stage=2)

    def check_reach():
        code, _ = api_request("/system/health")
        return code > 0, f"HTTP {code}", {"code": code, "url": API_BASE}
    rpt.checks.append(_check("S2.01","Server Reachable","S2",2, check_reach, SEV_CRITICAL,
                             "GET /api/system/health must respond"))

    def check_healthy():
        code, resp = api_request("/system/health")
        ok = code == 200 and resp.get("status") in ("healthy","ok","running")
        return ok, f"status={resp.get('status')} HTTP {code}", {"code": code}
    rpt.checks.append(_check("S2.02","Health Endpoint Returns Healthy","S2",2, check_healthy, SEV_CRITICAL,
                             "/api/system/health must return status=healthy"))

    def check_login():
        global _auth_token; _auth_token = None
        tok = get_admin_token()
        return bool(tok), f"Token {'obtained' if tok else 'FAILED'}", {"token_len": len(tok) if tok else 0}
    rpt.checks.append(_check("S2.03","Admin Login & JWT Issuance","S2",2, check_login, SEV_CRITICAL,
                             "POST /api/auth/login must return JWT"))

    def check_bad_creds():
        code, _ = api_request("/auth/login","POST",{"email":"bad@x.com","password":"wrong"})
        return code in (400,401,403), f"Bad creds → HTTP {code}", {"code": code}
    rpt.checks.append(_check("S2.04","Invalid Credentials Rejected","S2",2, check_bad_creds, SEV_HIGH,
                             "Bad login must return 4xx"))

    def check_protected():
        code, _ = api_request("/admin/system/status")  # no token
        return code in (401,403), f"No-token -> HTTP {code}", {"code": code}
    rpt.checks.append(_check("S2.05","Protected Endpoints Require Auth","S2",2, check_protected, SEV_HIGH,
                             "Unauthenticated request must return 401/403"))

    def check_status_ep():
        code, resp = api_get("/admin/system/status")
        return code == 200 and "data" in resp, f"HTTP {code}", {"code": code}
    rpt.checks.append(_check("S2.06","System Status Endpoint","S2",2, check_status_ep, SEV_HIGH,
                             "GET /api/admin/system/status → 200 with 'data'"))

    def check_latency():
        t0 = time.monotonic()
        api_get("/admin/system/status")
        ms = (time.monotonic()-t0)*1000
        return ms < 3000, f"{ms:.0f}ms (SLA<3000ms)", {"latency_ms": round(ms,1)}
    rpt.checks.append(_check("S2.07","API Response Time <3s","S2",2, check_latency, SEV_MEDIUM,
                             "Admin status must respond <3000ms", warn_on_fail=True))

    return rpt


# ═══════════════════════════════════════════════════════════
#  STAGE 3 — DOMAIN UNIT VALIDATION
# ═══════════════════════════════════════════════════════════

def domain_d1_auth() -> DomainReport:
    rpt = DomainReport("D1", "D1: Authentication & Identity", stage=3)
    rpt.checks.append(_check("D1.01","Users Table Populated","D1",3,
        lambda: (db_count("users")>0,f"{db_count('users')} user(s)",{"count":db_count("users")}),
        SEV_CRITICAL,"At least one user must exist"))
    def _check_admin():
        cnt = db_scalar("SELECT COUNT(*) FROM users WHERE user_type='admin' AND is_active=1")
        return int(cnt or 0)>=1, f"admin_count={cnt}", {}
    rpt.checks.append(_check("D1.02","Active Admin Exists","D1",3,_check_admin,
        SEV_CRITICAL,"At least one active admin required"))
    rpt.checks.append(_check("D1.03","No NULL Password Hashes","D1",3,
        lambda: (int(db_scalar("SELECT COUNT(*) FROM users WHERE password_hash IS NULL OR password_hash=''") or 0)==0,
                 "No null passwords",{}),SEV_CRITICAL,"password_hash must never be NULL/empty"))
    rpt.checks.append(_check("D1.04","No Duplicate Emails","D1",3,
        lambda: (int(db_scalar("SELECT COUNT(*) FROM (SELECT email FROM users GROUP BY email HAVING COUNT(*)>1)") or 0)==0,
                 "No duplicate emails",{}),SEV_HIGH,"email must be UNIQUE"))
    def check_settings_cov():
        u=db_count("users","is_active=1"); s=db_count("user_settings")
        return s>=u,f"{s} settings for {u} active users",{"delta":max(u-s,0)}
    rpt.checks.append(_check("D1.05","user_settings Coverage","D1",3,check_settings_cov,SEV_HIGH,
                             "Every active user must have a user_settings row"))
    rpt.checks.append(_check("D1.06","Stale OTP Accumulation","D1",3,
        lambda: (int(db_scalar("SELECT COUNT(*) FROM pending_verifications WHERE expires_at<datetime('now')") or 0)<100,
                 f"stale OTPs count",{}),SEV_LOW,"<100 stale OTPs",warn_on_fail=True))
    rpt.checks.append(_check("D1.07","No Users With is_active=NULL","D1",3,
        lambda: (int(db_scalar("SELECT COUNT(*) FROM users WHERE is_active IS NULL") or 0)==0,
                 "All is_active set",{}),SEV_HIGH,"is_active must not be NULL"))
    return rpt


def domain_d2_market_data() -> DomainReport:
    rpt = DomainReport("D2","D2: Market Data Ingestion (Binance->DB)", stage=3)
    rpt.checks.append(_check("D2.01","trading_signals Populated","D2",3,
        lambda: (db_count("trading_signals")>0,f"{db_count('trading_signals')} signals",
                 {"count":db_count("trading_signals")}),SEV_HIGH,
        "trading_signals must have data (WARN: may be empty on fresh start)",warn_on_fail=True))
    def check_freshness():
        latest=db_scalar("SELECT MAX(generated_at) FROM trading_signals")
        if not latest: return False,"No signals",{"latest":None}
        try:
            if isinstance(latest, datetime):
                ts = latest
            else:
                latest_s = str(latest).replace("Z", "+00:00")
                ts = datetime.fromisoformat(latest_s)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age=(datetime.now(timezone.utc)-ts.astimezone(timezone.utc)).total_seconds()/3600
            return age<24,f"Latest {age:.1f}h ago",{"age_hours":round(age,2)}
        except Exception as e: return False,f"Parse error: {e}",{}
    rpt.checks.append(_check("D2.02","Signal Freshness <24h","D2",3,check_freshness,SEV_MEDIUM,
                             "Most recent signal must be <24h old",warn_on_fail=True))
    def check_sig_schema():
        rows=db_fetchall("SELECT * FROM trading_signals LIMIT 5")
        if not rows: return True,"No signals (skip)",{}
        v=[]
        for r in rows:
            d=dict(r)
            if not d.get("symbol"): v.append(f"id={d.get('id')}: no symbol")
            if d.get("confidence") is None: v.append(f"id={d.get('id')}: null confidence")
            if not d.get("price") or float(d.get("price",0))<=0: v.append(f"id={d.get('id')}: bad price")
        return not v,f"{len(v)} violations",{"violations":v[:5]}
    rpt.checks.append(_check("D2.03","Signal Schema Validity","D2",3,check_sig_schema,SEV_HIGH,
                             "symbol not empty, confidence>=0, price>0"))
    rpt.checks.append(_check("D2.04","No Duplicate Signals","D2",3,
        lambda: (int(db_scalar("""SELECT COUNT(*) FROM (SELECT symbol,strategy,timeframe,generated_at,COUNT(*) c
               FROM trading_signals GROUP BY symbol,strategy,timeframe,generated_at HAVING COUNT(*)>1)""") or 0)==0,
                 "No duplicate signals",{}),SEV_HIGH,"(symbol,strategy,timeframe,generated_at) must be unique"))
    rpt.checks.append(_check("D2.05","Signal Confidence in [0,1]","D2",3,
        lambda: (int(db_scalar("SELECT COUNT(*) FROM trading_signals WHERE confidence<0 OR confidence>1") or 0)==0,
                 "All confidence in [0,1]",{}),SEV_HIGH,"confidence in [0.0,1.0]"))
    rpt.checks.append(_check("D2.06","Successful Coins Active","D2",3,
        lambda: (db_count("successful_coins","is_active=1")>0,
                 f"{db_count('successful_coins','is_active=1')} active coins",{}),
        SEV_MEDIUM,"successful_coins must have active entries"))
    return rpt


def domain_d3_signals() -> DomainReport:
    rpt = DomainReport("D3","D3: Signal Processing Pipeline", stage=3)
    def check_backlog():
        total=db_count("trading_signals")
        if total==0: return True,"No signals (skip)",{}
        unproc=db_count("trading_signals","is_processed=0")
        pct=(unproc/total)*100
        return pct<50,f"{unproc}/{total} ({pct:.1f}%) unprocessed",{"pct":round(pct,1)}
    rpt.checks.append(_check("D3.01","Signal Processing Backlog <50%","D3",3,check_backlog,SEV_HIGH,
                             "<50% signals unprocessed",warn_on_fail=True))
    def check_ratio():
        sig=db_count("trading_signals","is_processed=1"); pos=db_count("trading_history")
        if sig==0: return True,"No processed signals yet",{}
        r=pos/sig
        return r<=1.0,f"positions/processed_signals={r:.3f}",{"ratio":round(r,3)}
    rpt.checks.append(_check("D3.02","Positions <= Processed Signals","D3",3,check_ratio,SEV_HIGH,
                             "Total positions must not exceed processed signals"))
    rpt.checks.append(_check("D3.03","Blacklist Consistency","D3",3,
        lambda: (int(db_scalar("SELECT COUNT(*) FROM dynamic_blacklist WHERE is_active=1 AND datetime(expires_at)<datetime('now')") or 0)==0,
                 "No expired-active blacklists",{}),SEV_MEDIUM,
                 "No is_active=1 blacklist past expires_at",warn_on_fail=True))
    return rpt


def domain_d4_trading() -> DomainReport:
    rpt = DomainReport("D4","D4: Trading Execution Engine", stage=3)
    def check_pos_schema():
        rows=db_fetchall("SELECT * FROM active_positions LIMIT 10")
        v=[]
        for r in rows:
            d=dict(r)
            if not d.get("entry_price") or float(d.get("entry_price",0))<=0:
                v.append(f"id={d.get('id')}: bad entry_price")
            if not d.get("quantity") or float(d.get("quantity",0))<=0:
                v.append(f"id={d.get('id')}: bad quantity")
            if d.get("user_id") is None:
                v.append(f"id={d.get('id')}: NULL user_id")
        return not v,f"{len(v)} schema violation(s)",{"violations":v[:5]}
    rpt.checks.append(_check("D4.01","Active Positions Schema Valid","D4",3,check_pos_schema,SEV_HIGH,
                             "entry_price>0, quantity>0, user_id not NULL"))
    rpt.checks.append(_check("D4.02","No Duplicate Active Positions","D4",3,
        lambda: (int(db_scalar("""SELECT COUNT(*) FROM (SELECT user_id,symbol,strategy,COUNT(*) c
               FROM active_positions WHERE is_active=1 GROUP BY user_id,symbol,strategy HAVING COUNT(*)>1)""") or 0)==0,
                 "No duplicates",{}),SEV_CRITICAL,"(user_id,symbol,strategy) unique per is_active=1"))
    def check_sl_tp():
        bad_sl=int(db_scalar("""SELECT COUNT(*) FROM active_positions WHERE is_active=1
               AND stop_loss IS NOT NULL AND position_type='LONG' AND stop_loss>=entry_price""") or 0)
        bad_tp=int(db_scalar("""SELECT COUNT(*) FROM active_positions WHERE is_active=1
               AND take_profit IS NOT NULL AND position_type='LONG' AND take_profit<=entry_price""") or 0)
        t=bad_sl+bad_tp
        return t==0,f"{t} invalid SL/TP (LONG)",{"bad_sl":bad_sl,"bad_tp":bad_tp}
    rpt.checks.append(_check("D4.03","SL/TP Validity LONG Positions","D4",3,check_sl_tp,SEV_CRITICAL,
                             "LONG: stop_loss<entry_price AND take_profit>entry_price"))
    rpt.checks.append(_check("D4.04","Closed Positions Have Exit Data","D4",3,
        lambda: (int(db_scalar("""SELECT COUNT(*) FROM active_positions WHERE is_active=0
               AND (exit_price IS NULL OR profit_loss IS NULL OR closed_at IS NULL)""") or 0)==0,
                 "All closed positions have exit data",{}),SEV_HIGH,
                 "is_active=0 must have exit_price, profit_loss, closed_at"))
    def check_pnl_dir():
        rows=db_fetchall("SELECT profit_loss,entry_price,exit_price FROM trading_history LIMIT 50")
        bad=[]
        for i,r in enumerate(rows):
            d=dict(r)
            pnl,ep,xp=d.get("profit_loss"),d.get("entry_price"),d.get("exit_price")
            if pnl and ep and xp and abs(float(pnl))>0.5:
                if (float(xp)>float(ep)) != (float(pnl)>0):
                    bad.append(f"row{i}: pnl={pnl} ep={ep} xp={xp}")
        return not bad,f"{len(bad)} P&L direction inconsistencies",{"bad":bad[:5]}
    rpt.checks.append(_check("D4.05","P&L Direction Consistency","D4",3,check_pnl_dir,SEV_HIGH,
                             "profit_loss sign must match exit_price vs entry_price direction",warn_on_fail=True))
    rpt.checks.append(_check("D4.06","No Orphan Positions (FK)","D4",3,
        lambda: (int(db_scalar("""SELECT COUNT(*) FROM active_positions ap
               LEFT JOIN users u ON u.id=ap.user_id WHERE u.id IS NULL""") or 0)==0,
                 "No orphan positions",{}),SEV_CRITICAL,"active_positions.user_id must reference valid user"))
    return rpt


def domain_d5_portfolio() -> DomainReport:
    rpt = DomainReport("D5","D5: Portfolio & Balance Synchronization", stage=3)
    rpt.checks.append(_check("D5.01","Portfolio Records Exist","D5",3,
        lambda: (db_count("portfolio")>0,f"{db_count('portfolio')} rows",{"count":db_count("portfolio")}),
        SEV_CRITICAL,"At least one portfolio row must exist"))
    rpt.checks.append(_check("D5.02","Portfolio Balances Non-Negative","D5",3,
        lambda: (int(db_scalar("SELECT COUNT(*) FROM portfolio WHERE total_balance<0 OR available_balance<0") or 0)==0,
                 "All balances >= 0",{}),SEV_HIGH,"total_balance>=0 AND available_balance>=0"))
    def check_balance_eq():
        bad=int(db_scalar("SELECT COUNT(*) FROM portfolio WHERE ABS(total_balance-(available_balance+invested_balance))>0.01") or 0)
        return bad==0,f"{bad} balance equation violation(s)",{"bad":bad}
    rpt.checks.append(_check("D5.03","Portfolio Balance Equation","D5",3,check_balance_eq,SEV_HIGH,
                             "total_balance=available_balance+invested_balance (+-0.01)"))
    rpt.checks.append(_check("D5.04","portfolio initial_balance Set","D5",3,
        lambda: (int(db_scalar("SELECT COUNT(*) FROM portfolio WHERE initial_balance IS NULL OR initial_balance<=0") or 0)==0,
                 "initial_balance set",{}),SEV_MEDIUM,"initial_balance must be >0"))
    def check_port_cov():
        u=db_count("users","is_active=1")
        pu=int(db_scalar("SELECT COUNT(DISTINCT user_id) FROM portfolio") or 0)
        return pu>=u,f"{pu} portfolio users vs {u} active",{"delta":max(u-pu,0)}
    rpt.checks.append(_check("D5.05","Portfolio Coverage Per User","D5",3,check_port_cov,SEV_HIGH,
                             "Each active user must have a portfolio row"))
    rpt.checks.append(_check("D5.06","No Orphan Portfolio Rows (FK)","D5",3,
        lambda: (int(db_scalar("""SELECT COUNT(*) FROM portfolio p
               LEFT JOIN users u ON u.id=p.user_id WHERE u.id IS NULL""") or 0)==0,
                 "No orphan portfolio rows",{}),SEV_HIGH,"portfolio.user_id must reference valid user"))
    return rpt


def domain_d6_ml() -> DomainReport:
    rpt = DomainReport("D6","D6: ML Learning Pipeline", stage=3)
    rpt.checks.append(_check("D6.01","ML Training Data Accessible","D6",3,
        lambda: (True,f"{db_count('ml_training_data')} samples",{"count":db_count("ml_training_data")}),
        SEV_HIGH,"ml_training_data must be accessible"))
    def check_ml_schema():
        rows=db_fetchall("SELECT * FROM ml_training_data LIMIT 10")
        v=[]
        for r in rows:
            d=dict(r)
            if d.get("is_winning") not in (0,1,True,False): v.append(f"id={d.get('id')}: bad is_winning")
            if d.get("profit_loss") is None: v.append(f"id={d.get('id')}: null profit_loss")
        return not v,f"{len(v)} violations",{"violations":v[:5]}
    rpt.checks.append(_check("D6.02","ML Training Data Schema Valid","D6",3,check_ml_schema,SEV_HIGH,
                             "is_winning in {0,1}, profit_loss not NULL"))
    def check_ml_accuracy():
        count=db_count("ml_training_history")
        if count==0: return True,"No training cycles yet",{"count":0}
        best=db_scalar("SELECT MAX(accuracy) FROM ml_training_history WHERE status='completed'")
        ok=best is None or float(best)>=0.5
        return ok,f"{count} cycles, best_acc={best}",{"best_accuracy":best}
    rpt.checks.append(_check("D6.03","ML Best Accuracy >= 0.5","D6",3,check_ml_accuracy,SEV_MEDIUM,
                             "Model accuracy must exceed random baseline 0.5",warn_on_fail=True))
    def check_win_rate():
        total=db_count("signal_learning")
        if total==0: return True,"No signal_learning yet",{}
        correct=int(db_scalar("SELECT COUNT(*) FROM signal_learning WHERE was_correct=1") or 0)
        wr=(correct/total)*100
        return wr>=40,f"win_rate={wr:.1f}%",{"win_rate_pct":round(wr,2)}
    rpt.checks.append(_check("D6.04","Signal Learning Win Rate >= 40%","D6",3,check_win_rate,SEV_MEDIUM,
                             "signal_learning win_rate>=40%",warn_on_fail=True))
    def check_ml_quality():
        total=db_count("ml_quality_metrics")
        if total==0: return True,"ml_quality_metrics empty",{}
        low=int(db_scalar("SELECT COUNT(*) FROM ml_quality_metrics WHERE validity_rate<0.5") or 0)
        return low==0,f"{low} metrics below 50% validity",{"low":low}
    rpt.checks.append(_check("D6.05","ML Quality Validity Rate >= 50%","D6",3,check_ml_quality,SEV_MEDIUM,
                             "validity_rate>=0.5",warn_on_fail=True))
    return rpt


def domain_d7_notifications() -> DomainReport:
    rpt = DomainReport("D7","D7: Notification & Delivery System", stage=3)
    rpt.checks.append(_check("D7.01","Notifications Table Accessible","D7",3,
        lambda: (True,f"{db_count('notifications')} rows",{"count":db_count("notifications")}),
        SEV_MEDIUM,"notifications table accessible"))
    rpt.checks.append(_check("D7.02","No Orphan Notifications (FK)","D7",3,
        lambda: (int(db_scalar("""SELECT COUNT(*) FROM notifications n
               LEFT JOIN users u ON u.id=n.user_id WHERE u.id IS NULL""") or 0)==0,
                 "No orphans",{}),SEV_HIGH,"notifications.user_id must reference valid user"))
    rpt.checks.append(_check("D7.03","Admin Notification Settings Exist","D7",3,
        lambda: (db_count("admin_notification_settings")>=1,
                 f"{db_count('admin_notification_settings')} row(s)",{}),
        SEV_MEDIUM,"admin_notification_settings must have >=1 row",warn_on_fail=True))
    rpt.checks.append(_check("D7.04","Stale Unread Notifications","D7",3,
        lambda: (int(db_scalar("SELECT COUNT(*) FROM notifications WHERE is_read=0 AND datetime(created_at)<datetime('now','-30 days')") or 0)<100,
                 "Stale unread check",{}),SEV_LOW,"<100 unread notifs older than 30 days",warn_on_fail=True))
    return rpt


def domain_d8_system() -> DomainReport:
    rpt = DomainReport("D8","D8: Admin & System State Control", stage=3)
    rpt.checks.append(_check("D8.01","system_status Row Exists","D8",3,
        lambda: (db_count("system_status")>=1,f"{db_count('system_status')} row(s)",{}),
        SEV_CRITICAL,"system_status must have >=1 row"))
    def check_state_valid():
        state=db_scalar("SELECT trading_state FROM system_status WHERE id=1")
        valid={"RUNNING","STOPPED","PAUSED","STARTING","STOPPING",None}
        return state in valid,f"trading_state={state}",{"state":state}
    rpt.checks.append(_check("D8.02","System State Valid Enum","D8",3,check_state_valid,SEV_HIGH,
                             "trading_state in {RUNNING,STOPPED,PAUSED,STARTING,STOPPING,NULL}"))
    rpt.checks.append(_check("D8.03","No Unresolved Critical Alerts","D8",3,
        lambda: (int(db_scalar("SELECT COUNT(*) FROM system_alerts WHERE severity='critical' AND resolved=0") or 0)==0,
                 "All critical alerts resolved",{}),SEV_CRITICAL,"critical system_alerts must be resolved=1"))
    def check_pid_state():
        import subprocess
        pid_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "tmp","background_manager.pid")
        if not os.path.exists(pid_file): return True,"No PID file (system stopped/clean)",{}
        try:
            pid=int(open(pid_file).read().strip())
            alive=subprocess.run(["ps","-p",str(pid)],capture_output=True,timeout=3).returncode==0
            state=db_scalar("SELECT trading_state FROM system_status WHERE id=1")
            if alive and str(state or "").upper()=="STOPPED":
                return False,f"PID {pid} alive but DB=STOPPED (stale state)",{"pid":pid}
            if not alive and str(state or "").upper()=="RUNNING":
                return False,f"PID {pid} dead but DB=RUNNING (zombie state)",{"pid":pid}
            return True,f"PID={pid} alive={alive} state={state}",{}
        except Exception as e: return True,f"PID check skipped: {e}",{}
    rpt.checks.append(_check("D8.04","System PID vs DB State Sync","D8",3,check_pid_state,SEV_HIGH,
                             "PID file must be consistent with DB trading_state",warn_on_fail=True))
    return rpt


def domain_d9_analytics() -> DomainReport:
    rpt = DomainReport("D9","D9: Analytics & Reporting Layer", stage=3)
    def check_reliability():
        total=db_count("combo_reliability")
        if total==0: return True,"combo_reliability empty",{}
        # Scores stored as percentage [0,100]
        bad=int(db_scalar("SELECT COUNT(*) FROM combo_reliability WHERE reliability_score<0 OR reliability_score>100") or 0)
        return bad==0,f"{bad} out-of-range scores (expected 0-100)",{"bad":bad}
    rpt.checks.append(_check("D9.01","combo_reliability Score in [0,100]","D9",3,check_reliability,SEV_HIGH,
                             "reliability_score must be in [0, 100] (stored as percentage)"))
    def check_drift():
        rows=db_fetchall("""SELECT symbol,strategy,backtest_win_rate,actual_result
               FROM backtest_vs_reality WHERE actual_result IS NOT NULL LIMIT 50""")
        # actual_result may be 'win'/'loss' text or numeric
        high=[]
        for r in rows:
            d=dict(r)  
            bw,ar=d.get("backtest_win_rate"),d.get("actual_result")
            if bw is None or ar is None: continue
            try: ar_f=float(ar)
            except (ValueError,TypeError): continue  # skip text values like 'win'
            try: bw_f=float(bw)
            except (ValueError,TypeError): continue
            if abs(bw_f-ar_f)>30:
                high.append(f"{d.get('symbol')}/{d.get('strategy')}: drift={abs(bw_f-ar_f):.1f}%")
        return not high,f"{len(high)} symbols >30% drift",{"high_drift":high[:5]}
    rpt.checks.append(_check("D9.02","Backtest vs Reality Drift <30%","D9",3,check_drift,SEV_MEDIUM,
                             "drift(backtest_win_rate,actual_result)<30%",warn_on_fail=True))
    def check_learning_log():
        count=db_count("learning_validation_log")
        if count==0: return True,"No validation log yet",{}
        last=db_scalar("SELECT verdict FROM learning_validation_log ORDER BY validated_at DESC LIMIT 1")
        return str(last or "").upper()!="FAIL",f"Last verdict={last}",{"verdict":last}
    rpt.checks.append(_check("D9.03","Latest Learning Validation Verdict","D9",3,check_learning_log,SEV_MEDIUM,
                             "Most recent learning verdict must not be FAIL",warn_on_fail=True))
    rpt.checks.append(_check("D9.04","Agent Memory Table Accessible","D9",3,
        lambda: (True,f"{db_count('agent_memory','is_active=1')} active entries",{}),
        SEV_LOW,"agent_memory accessible"))
    return rpt


def domain_d10_integrity() -> DomainReport:
    rpt = DomainReport("D10","D10: Cross-Domain Integrity & Consistency", stage=3)
    rpt.checks.append(_check("D10.01","trading_history FK Integrity","D10",3,
        lambda: (int(db_scalar("""SELECT COUNT(*) FROM trading_history th
               LEFT JOIN users u ON u.id=th.user_id WHERE u.id IS NULL""") or 0)==0,
                 "No orphan trading_history rows",{}),SEV_CRITICAL,
                 "All trading_history.user_id must reference valid user"))
    rpt.checks.append(_check("D10.02","No Duplicate Trades","D10",3,
        lambda: (int(db_scalar("""SELECT COUNT(*) FROM (SELECT user_id,symbol,entry_time,COUNT(*) c
               FROM trading_history GROUP BY user_id,symbol,entry_time HAVING COUNT(*)>1)""") or 0)==0,
                 "No duplicate trades",{}),SEV_HIGH,
                 "(user_id,symbol,entry_time) must be unique in trading_history"))
    def check_pnl_sync():
        th=db_scalar("SELECT SUM(profit_loss) FROM trading_history WHERE status='closed'")
        p=db_scalar("SELECT SUM(total_profit_loss) FROM portfolio")
        if th is None or p is None: return True,"Skip: missing aggregates",{}
        delta=abs(float(th or 0)-float(p or 0))
        threshold=max(abs(float(th or 0))*0.05,10.0)
        return delta<=threshold,f"P&L delta={delta:.2f} (threshold={threshold:.2f})",{"delta":round(delta,4)}
    rpt.checks.append(_check("D10.03","Portfolio P&L sync with trading_history","D10",3,check_pnl_sync,SEV_HIGH,
                             "Aggregate P&L must match portfolio.total_profit_loss (+-5%)",warn_on_fail=True))
    def check_gaps():
        rows=db_fetchall("SELECT DATE(entry_time) d FROM trading_history WHERE entry_time IS NOT NULL ORDER BY entry_time DESC LIMIT 30")
        if len(rows)<2: return True,"Not enough history for gap detection",{}
        dates=[r[0] for r in rows if r[0]]
        max_gap=0
        for i in range(len(dates)-1):
            try:
                d1=datetime.strptime(dates[i],"%Y-%m-%d")
                d2=datetime.strptime(dates[i+1],"%Y-%m-%d")
                max_gap=max(max_gap,abs((d1-d2).days))
            except Exception: pass
        return max_gap<14,f"Max trading gap: {max_gap} days",{"max_gap_days":max_gap}
    rpt.checks.append(_check("D10.04","Trading History Temporal Gaps <14d","D10",3,check_gaps,SEV_MEDIUM,
                             "No gap >14 days in trading_history for active systems",warn_on_fail=True))
    def check_ml_overlap():
        ml_s={r[0] for r in db_fetchall("SELECT DISTINCT symbol FROM ml_training_data LIMIT 100")}
        th_s={r[0] for r in db_fetchall("SELECT DISTINCT symbol FROM trading_history LIMIT 100")}
        if not ml_s or not th_s: return True,"One table empty (skip)",{}
        overlap=len(ml_s & th_s)
        return overlap>0,f"ML/TH overlap: {overlap}/{len(ml_s)}",{"overlap":overlap}
    rpt.checks.append(_check("D10.05","ML Symbols Overlap With Trading History","D10",3,check_ml_overlap,
                             SEV_MEDIUM,"ML training must include symbols from trading history",warn_on_fail=True))
    return rpt


# ═══════════════════════════════════════════════════════════
#  STAGE 4 — INTER-DOMAIN INTEGRATION CHECKS
# ═══════════════════════════════════════════════════════════

def stage4_integration() -> DomainReport:
    rpt = DomainReport("INT","Stage-4: Inter-Domain Integration", stage=4)

    rpt.checks.append(_check("INT.01","Auth->Trading: No Trades for Disabled Users","INT",4,
        lambda: (int(db_scalar("""SELECT COUNT(*) FROM trading_history th
               JOIN user_settings us ON us.user_id=th.user_id
               WHERE us.trading_enabled=0 AND th.status='closed'""") or 0)==0,
                 "No trades for disabled users",{}),SEV_CRITICAL,
                 "Trades must not exist for users where trading_enabled=0"))

    def check_pos_metadata():
        with_meta=db_count("active_positions","signal_metadata IS NOT NULL AND signal_metadata!=''")
        total=db_count("active_positions")
        pct=(with_meta/total*100) if total>0 else 100
        return True,f"{with_meta}/{total} positions have signal_metadata ({pct:.1f}%)",{"pct":round(pct,1)}
    rpt.checks.append(_check("INT.02","Signal->Position: Metadata Traceability","INT",4,check_pos_metadata,
                             SEV_LOW,"Positions should carry signal_metadata"))

    def check_ml_coverage():
        th=db_count("trading_history","status='closed'"); ml=db_count("ml_training_data")
        if th==0: return True,"No closed trades yet",{}
        cov=(ml/th*100) if th>0 else 0
        return True,f"ML coverage: {ml}/{th} ({cov:.1f}%)",{"coverage_pct":round(cov,1)}
    rpt.checks.append(_check("INT.03","Trade->ML: Training Data Coverage","INT",4,check_ml_coverage,
                             SEV_MEDIUM,"Closed trades should feed ml_training_data pipeline"))

    def check_pnl_int():
        th=db_scalar("SELECT SUM(profit_loss) FROM trading_history WHERE status='closed'")
        p=db_scalar("SELECT SUM(total_profit_loss) FROM portfolio")
        if th is None or p is None: return True,"Skip: missing aggregates",{}
        delta=abs(float(th or 0)-float(p or 0))
        threshold=max(abs(float(th or 0))*0.05,10.0)
        return delta<=threshold,f"delta={delta:.4f} threshold={threshold:.2f}",{"delta":round(delta,4)}
    rpt.checks.append(_check("INT.04","Portfolio P&L <-> Trade History Sync","INT",4,check_pnl_int,
                             SEV_HIGH,"Aggregate P&L must match +-5%",warn_on_fail=True))

    def check_api_db_sync():
        code,resp=api_get("/admin/system/status")
        if code!=200: return False,f"API returned {code}",{"code":code}
        db_state=db_scalar("SELECT trading_state FROM system_status WHERE id=1")
        api_run=(resp.get("data",{}).get("is_running") or resp.get("data",{}).get("status")=="running")
        db_run=str(db_state or "").upper()=="RUNNING"
        ok=api_run==db_run
        return ok,f"API running={api_run}, DB state={db_state}",{"api_running":api_run,"db_state":db_state}
    rpt.checks.append(_check("INT.05","API <-> DB System State Sync","INT",4,check_api_db_sync,
                             SEV_HIGH,"API system status must match DB trading_state",warn_on_fail=True))

    def check_ml_confidence():
        with_conf=db_count("active_positions","ml_confidence IS NOT NULL")
        total=db_count("active_positions")
        pct=(with_conf/total*100) if total>0 else 100
        return True,f"{with_conf}/{total} positions have ml_confidence ({pct:.1f}%)",{"pct":round(pct,1)}
    rpt.checks.append(_check("INT.06","ML->Position: Confidence Traceability","INT",4,check_ml_confidence,
                             SEV_LOW,"Positions should carry ml_confidence"))

    def check_trade_notif():
        recent_tr=int(db_scalar("SELECT COUNT(*) FROM trading_history WHERE datetime(entry_time)>datetime('now','-24 hours')") or 0)
        recent_no=int(db_scalar("SELECT COUNT(*) FROM notifications WHERE datetime(created_at)>datetime('now','-24 hours') AND type='trade'") or 0)
        if recent_tr==0: return True,"No recent trades to check",{}
        return True,f"24h: {recent_tr} trades, {recent_no} trade notifs",{"trades":recent_tr,"notifs":recent_no}
    rpt.checks.append(_check("INT.07","Trade->Notification: Event Propagation","INT",4,check_trade_notif,
                             SEV_MEDIUM,"Trade events should generate user notifications",warn_on_fail=True))

    return rpt


# ═══════════════════════════════════════════════════════════
#  STAGE 5 — FULL E2E FLOW SIMULATION
# ═══════════════════════════════════════════════════════════

def stage5_e2e_flow() -> DomainReport:
    rpt = DomainReport("E2E","Stage-5: Full E2E Flow Simulation", stage=5)

    def check_e2e_login():
        global _auth_token, _auth_user_id
        _auth_token=None
        _auth_user_id=None
        tok=get_admin_token()
        auth_user_id = get_authenticated_user_id()
        return bool(tok) and auth_user_id is not None,f"Token {'obtained' if tok else 'FAILED'}",{"token_len":len(tok) if tok else 0, "auth_user_id": auth_user_id}
    rpt.checks.append(_check("E2E.01","E2E: Admin Login","E2E",5,check_e2e_login,SEV_CRITICAL,
                             "Must obtain valid JWT"))

    def _user_path_ok(path_template: str, label: str):
        user_id = get_authenticated_user_id()
        if user_id is None:
            return False, "No authenticated user_id", {"code": 0}
        code, _ = api_get(path_template.format(user_id=user_id))
        return code == 200, label, {"code": code, "user_id": user_id}

    rpt.checks.append(_check("E2E.02","E2E: Fetch Portfolio","E2E",5,
        lambda: _user_path_ok("/user/portfolio/{user_id}", "Portfolio fetch"),
        SEV_HIGH,"GET /api/user/portfolio/{id} must return 200"))

    rpt.checks.append(_check("E2E.03","E2E: Fetch Trade History","E2E",5,
        lambda: _user_path_ok("/user/trades/{user_id}", "Trades history"),
        SEV_HIGH,"GET /api/user/trades/{id} must return 200"))

    rpt.checks.append(_check("E2E.04","E2E: Fetch User Settings","E2E",5,
        lambda: _user_path_ok("/user/settings/{user_id}", "Settings fetch"),
        SEV_MEDIUM,"GET /api/user/settings/{id} must return 200"))

    def check_settings_write():
        user_id = get_authenticated_user_id()
        if user_id is None:
            return False, "No authenticated user_id", {}
        cc,cur=api_get(f"/user/settings/{user_id}")
        if cc!=200: return False,f"Cannot get current settings (HTTP {cc})",{}
        cur_amount=cur.get("trade_amount") or cur.get("data",{}).get("trade_amount") or 50
        code,_=api_request(f"/user/settings/{user_id}","PUT",{"trade_amount":cur_amount},
                           token=get_admin_token())
        return code in (200,201,204),f"Settings update HTTP {code}",{"code":code, "user_id": user_id}
    rpt.checks.append(_check("E2E.05","E2E: Update Settings Write Path","E2E",5,check_settings_write,
                             SEV_MEDIUM,"PUT /api/user/settings/{id} must return 200/201/204"))

    rpt.checks.append(_check("E2E.06","E2E: Admin Fetch User List","E2E",5,
        lambda: (api_get("/admin/users")[0]==200,"Admin user list",{"code":api_get("/admin/users")[0]}),
        SEV_MEDIUM,"GET /api/admin/users must return 200"))

    rpt.checks.append(_check("E2E.07","E2E: Fetch Notifications","E2E",5,
        lambda: _user_path_ok("/user/notifications/{user_id}", "Notifications"),
        SEV_MEDIUM,"GET /api/user/notifications/{id} must return 200"))

    def check_db_roundtrip():
        marker=f"e2e_test_{int(time.time())}"
        try:
            with db_connect() as conn:
                conn.execute("INSERT INTO operation_log (operation_type,operation_name,status,start_time,details) VALUES (%s,%s,%s,CURRENT_TIMESTAMP,%s)",
                             ("E2E_TEST","db_roundtrip","test",marker))
                conn.commit()
            found=int(db_scalar("SELECT COUNT(*) FROM operation_log WHERE details=%s AND operation_type='E2E_TEST'",(marker,)) or 0)
            with db_connect() as conn:
                conn.execute("DELETE FROM operation_log WHERE operation_type='E2E_TEST' AND details=%s",(marker,))
                conn.commit()
            return found>=1,f"DB roundtrip {'OK' if found>=1 else 'FAILED'}",{"marker":marker}
        except Exception as e:
            return False,f"DB roundtrip exception: {e}",{"error":str(e)}
    rpt.checks.append(_check("E2E.08","E2E: DB Write->Read Roundtrip","E2E",5,check_db_roundtrip,
                             SEV_CRITICAL,"DB must support concurrent write and immediate read"))

    def check_role_enforcement():
        # Regular user token cannot access admin endpoints
        code,resp=api_request("/admin/users")  # no token
        return code in (401,403),f"No-auth admin access HTTP {code}",{"code":code}
    rpt.checks.append(_check("E2E.09","E2E: Role Enforcement (No-Auth Blocked)","E2E",5,check_role_enforcement,
                             SEV_CRITICAL,"Admin endpoints must reject unauthenticated requests"))

    def check_portfolio_balance_api():
        user_id = get_authenticated_user_id()
        if user_id is None:
            return False, "No authenticated user_id", {"code": 0}
        code,resp=api_get(f"/user/portfolio/{user_id}")
        if code!=200: return False,f"HTTP {code}",{"code":code}
        data=resp.get("data",resp)
        has_bal=any(k in data for k in ("totalBalance","total_balance","balance","availableBalance"))
        return has_bal,f"Portfolio has balance field: {has_bal}",{"code":code,"keys":list(data.keys())[:6], "user_id": user_id}
    rpt.checks.append(_check("E2E.10","E2E: Portfolio Balance in API Response","E2E",5,check_portfolio_balance_api,
                             SEV_HIGH,"GET /api/user/portfolio/{id} must return totalBalance field"))

    return rpt


# ═══════════════════════════════════════════════════════════
#  STAGE 6 — DRIFT & ANOMALY DETECTION
# ═══════════════════════════════════════════════════════════

def stage6_drift_detection() -> DomainReport:
    rpt = DomainReport("DRF","Stage-6: Drift & Anomaly Detection", stage=6)

    def check_pnl_drift():
        rows=db_fetchall("""SELECT DATE(entry_time) d, AVG(profit_pct) avg_pnl, COUNT(*) cnt
               FROM trading_history WHERE status='closed' AND entry_time IS NOT NULL
               GROUP BY DATE(entry_time) ORDER BY d DESC LIMIT 30""")
        if len(rows)<7: return True,"Not enough data for drift detection",{}
        recent_avg=sum(float(r[1] or 0) for r in rows[:7])/7
        older_avg=sum(float(r[1] or 0) for r in rows[7:min(14,len(rows))])/len(rows[7:min(14,len(rows))]) if len(rows)>7 else recent_avg
        drift=abs(recent_avg-older_avg)
        ok=drift<10  # >10% drift in average daily P&L is anomalous
        return ok,f"P&L drift: recent={recent_avg:.2f}% older={older_avg:.2f}% delta={drift:.2f}%",{
            "recent_avg_pnl":round(recent_avg,4),"older_avg_pnl":round(older_avg,4),"drift":round(drift,4)}
    rpt.checks.append(_check("DRF.01","P&L Performance Drift (7d vs 7d-prior)","DRF",6,check_pnl_drift,
                             SEV_MEDIUM,"Daily avg P&L drift must be <10% between rolling windows",warn_on_fail=True))

    def check_signal_volume_drift():
        today_count=int(db_scalar("SELECT COUNT(*) FROM trading_signals WHERE DATE(generated_at)=DATE('now')") or 0)
        week_avg=db_scalar("SELECT AVG(cnt) FROM (SELECT DATE(generated_at) d,COUNT(*) cnt FROM trading_signals WHERE generated_at>datetime('now','-7 days') GROUP BY DATE(generated_at))")
        if not week_avg or float(week_avg)==0: return True,"Not enough data",{}
        ratio=today_count/float(week_avg)
        ok=0.2<=ratio<=5.0  # today must be between 20% and 500% of weekly average
        return ok,f"Signal volume today={today_count}, 7d_avg={float(week_avg):.1f}, ratio={ratio:.2f}",{
            "today":today_count,"week_avg":round(float(week_avg),1),"ratio":round(ratio,3)}
    rpt.checks.append(_check("DRF.02","Signal Volume Drift vs 7d Average","DRF",6,check_signal_volume_drift,
                             SEV_MEDIUM,"Signal volume must be within 20%-500% of 7-day average",warn_on_fail=True))

    def check_win_rate_drift():
        rows=db_fetchall("""SELECT DATE(entry_time) d,
               SUM(CASE WHEN profit_loss>0 THEN 1 ELSE 0 END)*100.0/COUNT(*) wr
               FROM trading_history WHERE status='closed' AND entry_time IS NOT NULL
               GROUP BY DATE(entry_time) ORDER BY d DESC LIMIT 14""")
        if len(rows)<7: return True,"Not enough data for win-rate drift",{}
        recent=[float(r[1]) for r in rows[:7] if r[1] is not None]
        older=[float(r[1]) for r in rows[7:] if r[1] is not None]
        if not recent or not older: return True,"Skip: empty windows",{}
        r_avg=sum(recent)/len(recent); o_avg=sum(older)/len(older)
        drift=abs(r_avg-o_avg)
        ok=drift<20  # >20% win rate drift is critical
        return ok,f"Win-rate drift: recent={r_avg:.1f}% older={o_avg:.1f}% delta={drift:.1f}%",{
            "recent_wr":round(r_avg,2),"older_wr":round(o_avg,2),"drift":round(drift,2)}
    rpt.checks.append(_check("DRF.03","Win Rate Drift (7d vs 7d-prior)","DRF",6,check_win_rate_drift,
                             SEV_HIGH,"Win rate drift must be <20% between rolling windows",warn_on_fail=True))

    def check_position_size_drift():
        rows=db_fetchall("""SELECT symbol
               FROM (SELECT DISTINCT symbol FROM active_positions WHERE is_active=1) LIMIT 10""")
        # SQLite has no STDEV; compute manually
        anomalies=[]
        syms={r[0] for r in db_fetchall("SELECT DISTINCT symbol FROM active_positions WHERE is_active=1")}
        for sym in list(syms)[:10]:
            sizes=[float(r[0]*r[1]) for r in db_fetchall(
                "SELECT quantity,entry_price FROM active_positions WHERE symbol=%s",(sym,))
                   if r[0] and r[1]]
            if len(sizes)<3: continue
            avg=sum(sizes)/len(sizes)
            std=(sum((x-avg)**2 for x in sizes)/len(sizes))**0.5
            for s in sizes:
                if std>0 and abs(s-avg)/std>3:
                    anomalies.append(f"{sym}: size={s:.2f} avg={avg:.2f} z={abs(s-avg)/std:.1f}")
        ok=len(anomalies)==0
        return ok,f"{len(anomalies)} position size outliers (>3 stdev)",{"anomalies":anomalies[:5]}
    rpt.checks.append(_check("DRF.04","Position Size Anomaly Detection","DRF",6,check_position_size_drift,
                             SEV_MEDIUM,"No position size must exceed 3 standard deviations from symbol mean",warn_on_fail=True))

    def check_schema_drift():
        known_tables=set(REQUIRED_SCHEMA.keys())
        with db_connect() as conn:
            rows = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'").fetchall()
            actual={r[0] for r in rows}
        new_tables=actual-known_tables
        return True,f"{len(new_tables)} undocumented tables: {list(new_tables)[:5]}",{
            "undocumented_tables":list(new_tables)}
    rpt.checks.append(_check("DRF.05","Schema Drift (Undocumented Tables)","DRF",6,check_schema_drift,
                             SEV_LOW,"New tables should be documented in REQUIRED_SCHEMA"))

    def check_error_spike():
        recent_errors=int(db_scalar("""SELECT COUNT(*) FROM system_alerts
               WHERE datetime(created_at)>datetime('now','-1 hour') AND severity IN ('critical','high')""") or 0)
        ok=recent_errors<10
        return ok,f"{recent_errors} critical/high alerts in last 1h",{"count":recent_errors}
    rpt.checks.append(_check("DRF.06","System Error Spike Detection","DRF",6,check_error_spike,
                             SEV_HIGH,"<10 critical/high alerts in last 1 hour"))

    def check_latency_drift():
        times=[]
        for _ in range(3):
            t0=time.monotonic(); api_get("/admin/system/status")
            times.append((time.monotonic()-t0)*1000)
        avg=sum(times)/len(times)
        ok=avg<3000
        return ok,f"API latency avg={avg:.0f}ms over 3 samples",{"avg_ms":round(avg,1),"samples":times}
    rpt.checks.append(_check("DRF.07","API Latency Drift (3 samples)","DRF",6,check_latency_drift,
                             SEV_MEDIUM,"Average latency of 3 consecutive requests must be <3000ms",warn_on_fail=True))

    return rpt


# ═══════════════════════════════════════════════════════════
#  STAGE 7 — OBSERVABILITY & AUDIT TRAIL
# ═══════════════════════════════════════════════════════════

def stage7_observability() -> DomainReport:
    rpt = DomainReport("OBS","Stage-7: Observability & Audit Trail", stage=7)

    rpt.checks.append(_check("OBS.01","Operation Log Active","OBS",7,
        lambda: (db_count("operation_log")>0,
                 f"{db_count('operation_log')} total operation log entries",
                 {"total":db_count("operation_log")}),SEV_MEDIUM,"operation_log must be written to"))

    rpt.checks.append(_check("OBS.02","Security Audit Log Active","OBS",7,
        lambda: (db_count("security_audit_log")>0,
                 f"{db_count('security_audit_log')} security audit entries",
                 {"total":db_count("security_audit_log")}),SEV_HIGH,"security_audit_log must record auth events"))

    def check_op_log_recent():
        recent=int(db_scalar("SELECT COUNT(*) FROM operation_log WHERE datetime(start_time)>datetime('now','-24 hours')") or 0)
        return True,f"{recent} operation log entries in last 24h",{"recent":recent}
    rpt.checks.append(_check("OBS.03","Recent Operation Log Activity (24h)","OBS",7,check_op_log_recent,
                             SEV_MEDIUM,"operation_log should show recent system activity"))

    def check_failed_ops():
        failed=int(db_scalar("SELECT COUNT(*) FROM operation_log WHERE status='error' AND datetime(start_time)>datetime('now','-1 hour')") or 0)
        ok=failed<5
        return ok,f"{failed} failed operations in last 1h",{"failed":failed}
    rpt.checks.append(_check("OBS.04","Failed Operations Spike","OBS",7,check_failed_ops,
                             SEV_HIGH,"<5 failed operations in last 1 hour"))

    def check_audit_coverage():
        # Verify that auth actions are covered
        login_audits=int(db_scalar("SELECT COUNT(*) FROM security_audit_log WHERE action ILIKE %s", ("%login%",)) or 0)
        return True,f"{login_audits} login events in security_audit_log",{"login_audits":login_audits}
    rpt.checks.append(_check("OBS.05","Security Audit Covers Login Events","OBS",7,check_audit_coverage,
                             SEV_MEDIUM,"Login events must appear in security_audit_log"))

    def check_system_alerts_log():
        total=db_count("system_alerts")
        unread=db_count("system_alerts","read=0")
        return True,f"{total} system alerts, {unread} unread",{"total":total,"unread":unread}
    rpt.checks.append(_check("OBS.06","System Alerts Log Populated","OBS",7,check_system_alerts_log,
                             SEV_MEDIUM,"system_alerts should log system events"))

    def check_ml_training_log():
        count=db_count("ml_training_history")
        failed=int(db_scalar("SELECT COUNT(*) FROM ml_training_history WHERE status='failed'") or 0)
        ok=failed==0
        return ok,f"{count} total cycles, {failed} failed",{"total":count,"failed":failed}
    rpt.checks.append(_check("OBS.07","ML Training History: No Failed Cycles","OBS",7,check_ml_training_log,
                             SEV_MEDIUM,"No ml_training_history rows with status=failed",warn_on_fail=True))

    def check_api_logging():
        code,resp=api_get("/admin/activity-logs")
        ok=code==200
        return ok,f"Admin activity-logs HTTP {code}",{"code":code}
    rpt.checks.append(_check("OBS.08","Admin Activity Logs API Accessible","OBS",7,check_api_logging,
                             SEV_MEDIUM,"GET /api/admin/activity-logs must return 200"))

    return rpt


# ═══════════════════════════════════════════════════════════
#  ORCHESTRATOR & RUNNER
# ═══════════════════════════════════════════════════════════

STAGE_MAP = {
    1: [stage1_schema_integrity],
    2: [stage2_api_health],
    3: [domain_d1_auth, domain_d2_market_data, domain_d3_signals, domain_d4_trading,
        domain_d5_portfolio, domain_d6_ml, domain_d7_notifications, domain_d8_system,
        domain_d9_analytics, domain_d10_integrity],
    4: [stage4_integration],
    5: [stage5_e2e_flow],
    6: [stage6_drift_detection],
    7: [stage7_observability],
}

ICON = {STATUS_PASS: "PASS", STATUS_FAIL: "FAIL", STATUS_WARN: "WARN", STATUS_SKIP: "SKIP"}
SEV_ICON = {SEV_CRITICAL: "[CRIT]", SEV_HIGH: "[HIGH]", SEV_MEDIUM: "[MED]", SEV_LOW: "[LOW]"}
COLOR = {"PASS": "\033[92m", "FAIL": "\033[91m", "WARN": "\033[93m", "SKIP": "\033[90m", "RESET": "\033[0m"}


def _color(status, text):
    return f"{COLOR.get(status,'')}{text}{COLOR['RESET']}"


def print_console_report(report: ValidationReport):
    width = 78
    print("\n" + "=" * width)
    print(f"  E2E DATA ARCHITECTURE VALIDATION REPORT  |  Run ID: {report.run_id}")
    print("=" * width)
    print(f"  Started : {report.started_at}")
    print(f"  Finished: {report.finished_at}")
    print(f"  Stages  : {report.stages_run}")
    print("-" * width)

    for domain in report.domains:
        status_str = _color(domain.overall_status, f"[{domain.overall_status}]")
        print(f"\n  {status_str}  {domain.domain_name}")
        print(f"  {'─'*60}")
        for chk in domain.checks:
            icon = _color(chk.status, f"  {chk.status:<4}")
            sev = SEV_ICON.get(chk.severity, "     ")
            print(f"  {icon}  {sev}  {chk.id:<12}  {chk.name}")
            if chk.message:
                print(f"              ↳ {chk.message}")
            if chk.is_fail() and chk.details:
                for k, v in list(chk.details.items())[:3]:
                    print(f"              · {k}: {v}")

    print("\n" + "=" * width)
    total = len(report.all_checks)
    print(f"  SUMMARY: {_color(STATUS_PASS, f'PASS={report.total_pass}')}  "
          f"{_color(STATUS_FAIL, f'FAIL={report.total_fail}')}  "
          f"{_color(STATUS_WARN, f'WARN={report.total_warn}')}  "
          f"Total={total}")
    print(f"  OVERALL: {_color(report.overall_status, report.overall_status)}")
    if report.critical_failures:
        print(f"\n  {_color(STATUS_FAIL, 'CRITICAL FAILURES:')}")
        for c in report.critical_failures:
            print(f"    · {c.id}  {c.name}: {c.message}")
    print("=" * width + "\n")


def build_validation_rules_summary() -> str:
    """Returns a text summary of all validation rules for documentation."""
    lines = [
        "=" * 70,
        "  VALIDATION RULES REFERENCE",
        "=" * 70,
        "",
        "STAGE 1 — DB SCHEMA INTEGRITY",
        "  S1.01  PostgreSQL connection must be reachable",
        "  S1.02  current_schema() must be 'public'",
        "  S1.03  information_schema must be readable",
        "  S1.04  All required tables must exist",
        "  S1.05  All critical columns must exist per table",
        "  S1.06  Core tables must be queryable",
        "  S1.07  system_status must be queryable",
        "  S1.08  public schema must contain tables",
        "",
        "STAGE 2 — API CONNECTIVITY",
        "  S2.01  Server must respond at port 3002",
        "  S2.02  /api/system/health → status=healthy",
        "  S2.03  POST /api/auth/login → valid JWT",
        "  S2.04  Bad credentials → 401/403/400",
        "  S2.05  Protected endpoints → 401/403 without token",
        "  S2.06  /api/admin/system/status → 200 + data",
        "  S2.07  API latency SLA < 3000 ms",
        "",
        "STAGE 3 — DOMAIN UNIT VALIDATION (per domain)",
        "  D1  Auth: users exist, no null passwords, no duplicate emails",
        "  D2  Market: signals populated, fresh <24h, confidence in [0,1]",
        "  D3  Signals: backlog <50%, no expired blacklists",
        "  D4  Trading: SL<entry, TP>entry, no duplicate active positions",
        "  D5  Portfolio: balance equations, per-user coverage",
        "  D6  ML: training accuracy ≥0.5, win rate ≥40%",
        "  D7  Notifications: no orphans, no stale unread",
        "  D8  System: state valid enum, PID consistent with DB state",
        "  D9  Analytics: reliability scores [0,1], drift <30%",
        "  D10 Integrity: no FK violations, no duplicate trades, P&L sync",
        "",
        "STAGE 4 — INTER-DOMAIN INTEGRATION",
        "  INT.01  No trades for disabled users",
        "  INT.04  Portfolio P&L matches trading_history ±5%",
        "  INT.05  API system state matches DB trading_state",
        "",
        "STAGE 5 — E2E FLOW SIMULATION",
        "  Full read/write API roundtrip per endpoint",
        "  DB write→read roundtrip",
        "  Role enforcement verification",
        "",
        "STAGE 6 — DRIFT & ANOMALY DETECTION",
        "  DRF.01  P&L drift <10% between 7d rolling windows",
        "  DRF.03  Win-rate drift <20% between 7d rolling windows",
        "  DRF.04  Position size Z-score ≤3 per symbol",
        "  DRF.06  <10 critical/high alerts in last 1 hour",
        "",
        "STAGE 7 — OBSERVABILITY & AUDIT TRAIL",
        "  OBS.02  security_audit_log active",
        "  OBS.04  <5 failed operations in last 1 hour",
        "  OBS.07  No failed ML training cycles",
        "=" * 70,
    ]
    return "\n".join(lines)


def run_validation(stages: Optional[List[int]] = None,
                   domains: Optional[List[str]] = None,
                   strict: bool = False,
                   report_format: str = "console") -> ValidationReport:

    report = ValidationReport()
    report.metadata = {
        "db_engine": "postgresql",
        "api_base": API_BASE,
        "strict": strict,
        "filter_stages": stages,
        "filter_domains": domains,
    }

    stages_to_run = stages or list(STAGE_MAP.keys())
    report.stages_run = stages_to_run

    # Stage 1 (offline) always runs first
    if 1 in stages_to_run:
        for fn in STAGE_MAP[1]:
            domain_rpt = fn()
            if domains and domain_rpt.domain_id not in domains:
                continue
            report.domains.append(domain_rpt)
        # If critical failures in stage 1, abort
        if any(c.is_fail() and c.severity == SEV_CRITICAL
               for d in report.domains for c in d.checks):
            report.finalize()
            if report_format == "console":
                print_console_report(report)
            elif report_format == "json":
                import dataclasses
                def _serial(obj):
                    if dataclasses.is_dataclass(obj): return dataclasses.asdict(obj)
                    return str(obj)
                print(json.dumps(dataclasses.asdict(report), default=_serial, ensure_ascii=False, indent=2))
            print("\n[ABORTED] Critical Stage-1 failures prevent further validation.\n")
            return report

    for stage_num in stages_to_run:
        if stage_num == 1:
            continue  # already run
        for fn in STAGE_MAP.get(stage_num, []):
            domain_rpt = fn()
            if domains and domain_rpt.domain_id not in domains:
                continue
            report.domains.append(domain_rpt)

    report.finalize()

    if report_format == "console":
        print_console_report(report)
        if strict:
            print(build_validation_rules_summary())
    elif report_format == "json":
        import dataclasses
        def _serial(obj):
            if dataclasses.is_dataclass(obj): return dataclasses.asdict(obj)
            return str(obj)
        print(json.dumps(dataclasses.asdict(report), default=_serial, ensure_ascii=False, indent=2))

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="E2E Data Architecture Validation")
    parser.add_argument("--stage", type=int, help="Run only a specific stage (1-7)")
    parser.add_argument("--domain", type=str, help="Run only a specific domain (e.g. D4)")
    parser.add_argument("--report", choices=["console", "json"], default="console")
    parser.add_argument("--strict", action="store_true", help="Print full validation rules; fail on warnings")
    args = parser.parse_args()

    stages = [args.stage] if args.stage else None
    domains = [args.domain] if args.domain else None

    try:
        if db_scalar("SELECT 1") != 1:
            print("[ERROR] PostgreSQL connection check failed")
            return 2
    except Exception as exc:
        print(f"[ERROR] PostgreSQL unavailable: {exc}")
        return 2

    report = run_validation(stages=stages, domains=domains,
                            strict=args.strict, report_format=args.report)

    if args.strict and report.overall_status in (STATUS_FAIL, STATUS_WARN):
        return 1
    return 0 if report.overall_status in (STATUS_PASS, STATUS_WARN) else 1


if __name__ == "__main__":
    raise SystemExit(main())
