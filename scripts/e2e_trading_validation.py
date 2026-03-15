#!/usr/bin/env python3
"""End-to-end sequential validation for trading system.

Flow:
1) Pre-check API health/status + DB critical errors
2) Execute one real trading cycle through current manager/system path
3) Post-check for new errors and final status

Exit code:
- 0: PASS
- 1: FAIL
"""

from __future__ import annotations

import json
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
API_BASE = "http://127.0.0.1:3002"

# Ensure project imports resolve exactly as runtime does.
sys.path.insert(0, str(ROOT))

from bin.background_trading_manager import BackgroundTradingManager  # noqa: E402
from database.database_manager import DatabaseManager  # noqa: E402


db = DatabaseManager()


class CycleTimeout(Exception):
    pass


def _timeout_handler(signum: int, frame: Any) -> None:
    raise CycleTimeout("run_trading_cycle timeout")


@dataclass
class CheckResult:
    passed: bool
    data: dict[str, Any]


def http_json(url: str, timeout: int = 5) -> dict[str, Any]:
    with urlopen(url, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body)


def db_scalar(sql: str, params: tuple[Any, ...] = ()) -> Any:
    with db.get_connection() as conn:
        cur = conn.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None


def precheck() -> CheckResult:
    out: dict[str, Any] = {"stage": "precheck"}
    try:
        health = http_json(f"{API_BASE}/api/system/health")
        status = http_json(f"{API_BASE}/api/system/status")
    except Exception as exc:
        return CheckResult(False, {**out, "error": f"api_unreachable: {exc}"})

    critical_unresolved = db_scalar(
        "SELECT COUNT(*) FROM system_errors WHERE COALESCE(severity,'')='critical' AND COALESCE(resolved,0)=0"
    )

    out["health"] = health
    out["status"] = status
    out["critical_unresolved_before"] = int(critical_unresolved or 0)

    is_healthy = bool(health.get("success") and health.get("status") == "healthy")
    status_data = status.get("data", {}) if isinstance(status, dict) else {}
    is_running = bool(
        status.get("success")
        and status_data.get("status") == "running"
        and status_data.get("tradingActive") is True
    )

    passed = is_healthy and is_running and out["critical_unresolved_before"] == 0
    return CheckResult(passed, out)


def run_one_cycle() -> CheckResult:
    out: dict[str, Any] = {"stage": "cycle"}
    manager = BackgroundTradingManager()
    users = manager._get_active_trading_users()
    out["active_users"] = users

    if not users:
        return CheckResult(False, {**out, "error": "no_active_trading_users"})

    signal.signal(signal.SIGALRM, _timeout_handler)

    cycles: list[dict[str, Any]] = []
    any_cycle_failed = False

    for user in users:
        rec: dict[str, Any] = {
            "user_id": user.get("id"),
            "username": user.get("username"),
            "trading_enabled": user.get("trading_enabled"),
            "has_open_positions": user.get("has_open_positions"),
        }

        try:
            system = manager._get_or_create_system(user["id"])
            rec["mode"] = "demo" if getattr(system, "is_demo_trading", False) else "real"
            rec["can_trade"] = bool(getattr(system, "can_trade", False))

            signal.alarm(90)
            t0 = time.time()
            result = system.run_trading_cycle()
            rec["duration_sec"] = round(time.time() - t0, 2)
            rec["result"] = {
                "positions_checked": result.get("positions_checked"),
                "positions_closed": result.get("positions_closed"),
                "new_positions": result.get("new_positions"),
                "errors": result.get("errors", []),
                "actions_count": len(result.get("actions", [])),
            }

            if rec["result"]["errors"]:
                any_cycle_failed = True

        except CycleTimeout as exc:
            rec["error"] = str(exc)
            any_cycle_failed = True
        except Exception as exc:
            rec["error"] = str(exc)
            any_cycle_failed = True
        finally:
            signal.alarm(0)

        cycles.append(rec)

    out["cycles"] = cycles
    return CheckResult(not any_cycle_failed, out)


def postcheck(started_at: str) -> CheckResult:
    out: dict[str, Any] = {"stage": "postcheck", "started_at": started_at}

    critical_unresolved_after = db_scalar(
        "SELECT COUNT(*) FROM system_errors WHERE COALESCE(severity,'')='critical' AND COALESCE(resolved,0)=0"
    )
    new_critical_since_start = db_scalar(
        "SELECT COUNT(*) FROM system_errors WHERE COALESCE(severity,'')='critical' AND datetime(created_at) >= datetime(?)",
        (started_at,),
    )

    out["critical_unresolved_after"] = int(critical_unresolved_after or 0)
    out["new_critical_since_start"] = int(new_critical_since_start or 0)

    passed = out["critical_unresolved_after"] == 0 and out["new_critical_since_start"] == 0
    return CheckResult(passed, out)


def main() -> int:
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report: dict[str, Any] = {
        "started_at": started_at,
        "overall": "FAIL",
        "checks": [],
    }

    p = precheck()
    report["checks"].append(p.data)
    if not p.passed:
        report["reason"] = "precheck_failed"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    c = run_one_cycle()
    report["checks"].append(c.data)
    if not c.passed:
        report["reason"] = "cycle_failed"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    post = postcheck(started_at)
    report["checks"].append(post.data)
    if not post.passed:
        report["reason"] = "postcheck_failed"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    report["overall"] = "PASS"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
