#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Official Binance API connectivity tester.
Tests ALL official endpoints, versions, and methods to find a working connection.
"""

import os
import time
import json
import logging
import requests
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)

# ============================================================
# ALL Official Binance API Endpoints
# ============================================================
OFFICIAL_ENDPOINTS = {
    # Primary
    "api.binance.com": "https://api.binance.com",
    # Official alternates (documented by Binance)
    "api1.binance.com": "https://api1.binance.com",
    "api2.binance.com": "https://api2.binance.com",
    "api3.binance.com": "https://api3.binance.com",
    "api4.binance.com": "https://api4.binance.com",
    # Binance.US (if applicable)
    "api.binance.us": "https://api.binance.us",
    # Global alternate domains
    "www.binance.com": "https://www.binance.com",
}

# ============================================================
# Official Public Endpoints (no API key needed)
# ============================================================
PUBLIC_ENDPOINTS = [
    "/api/v3/ping",
    "/api/v3/time",
    "/api/v3/exchangeInfo",
    "/api/v3/ticker/price?symbol=BTCUSDT",
    "/api/v3/ticker/24hr?symbol=BTCUSDT",
    "/api/v1/exchangeInfo",  # v1 alternate
    "/sapi/v1/system/status",  # System status
]

# ============================================================
# Official Authenticated Endpoints (need API key)
# ============================================================
AUTH_ENDPOINTS = [
    "/api/v3/account",
    "/api/v3/accountSnapshot?type=SPOT",
    "/sapi/v1/capital/config/getall",
]


def test_public_endpoint(
    base_url: str, path: str, timeout: int = 10
) -> Tuple[bool, str, float]:
    """
    Test a public Binance endpoint.
    Returns (success, message, response_time_ms)
    """
    url = f"{base_url}{path}"
    start = time.time()
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": "TradingAI/1.0",
                "Accept": "application/json",
            },
        )
        elapsed = (time.time() - start) * 1000

        if resp.status_code == 200:
            return True, f"OK ({resp.status_code})", elapsed
        elif resp.status_code == 451:
            return (
                False,
                f"GEO_BLOCKED ({resp.status_code}) — {resp.text[:200]}",
                elapsed,
            )
        elif resp.status_code == 403:
            return False, f"FORBIDDEN ({resp.status_code}) — {resp.text[:200]}", elapsed
        else:
            return False, f"HTTP {resp.status_code} — {resp.text[:200]}", elapsed
    except requests.exceptions.ConnectionError as e:
        elapsed = (time.time() - start) * 1000
        return False, f"CONNECTION_ERROR — {str(e)[:100]}", elapsed
    except requests.exceptions.Timeout:
        elapsed = (time.time() - start) * 1000
        return False, f"TIMEOUT ({timeout}s)", elapsed
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return False, f"ERROR — {str(e)[:100]}", elapsed


def test_auth_endpoint(
    base_url: str, path: str, api_key: str, api_secret: str, timeout: int = 10
) -> Tuple[bool, str, float]:
    """
    Test an authenticated Binance endpoint.
    Uses HMAC-SHA256 signature (official method).
    """
    import hmac
    import hashlib
    from urllib.parse import urlencode

    timestamp = int(time.time() * 1000)
    params = {"timestamp": timestamp, "recvWindow": 10000}
    query_string = urlencode(params)

    signature = hmac.new(
        api_secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    url = f"{base_url}{path}?{query_string}&signature={signature}"
    start = time.time()
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={
                "X-MBX-APIKEY": api_key,
                "User-Agent": "TradingAI/1.0",
                "Accept": "application/json",
            },
        )
        elapsed = (time.time() - start) * 1000

        if resp.status_code == 200:
            return True, f"OK ({resp.status_code})", elapsed
        elif resp.status_code == 451:
            return False, f"GEO_BLOCKED ({resp.status_code})", elapsed
        elif resp.status_code == 401:
            return False, f"UNAUTHORIZED — invalid key", elapsed
        else:
            return False, f"HTTP {resp.status_code} — {resp.text[:200]}", elapsed
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return False, f"ERROR — {str(e)[:100]}", elapsed


def run_full_test():
    """
    Run comprehensive test of ALL Binance endpoints and methods.
    Returns a detailed report.
    """
    api_key = os.getenv("BINANCE_BACKEND_API_KEY", "")
    api_secret = os.getenv("BINANCE_BACKEND_API_SECRET", "")

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "public_tests": [],
        "auth_tests": [],
        "working_endpoints": [],
        "geo_blocked": [],
        "failed": [],
        "summary": {},
    }

    logger.info("=" * 80)
    logger.info("🔍 BINANCE API CONNECTIVITY TEST — ALL OFFICIAL METHODS")
    logger.info("=" * 80)

    # Phase 1: Public endpoints
    logger.info("\n📡 Phase 1: Testing PUBLIC endpoints (no key needed)")
    for domain, base_url in OFFICIAL_ENDPOINTS.items():
        for path in PUBLIC_ENDPOINTS:
            success, msg, elapsed = test_public_endpoint(base_url, path)
            result = {
                "domain": domain,
                "path": path,
                "url": f"{base_url}{path}",
                "success": success,
                "message": msg,
                "response_ms": round(elapsed, 1),
            }
            report["public_tests"].append(result)

            status = "✅" if success else "❌"
            logger.info(f"  {status} {domain}{path} — {msg} ({elapsed:.0f}ms)")

            if success:
                report["working_endpoints"].append(f"{domain}{path}")
            elif "GEO_BLOCKED" in msg:
                if domain not in report["geo_blocked"]:
                    report["geo_blocked"].append(domain)

    # Phase 2: Authenticated endpoints
    if api_key and api_secret:
        logger.info("\n🔑 Phase 2: Testing AUTHENTICATED endpoints (with API key)")
        for domain, base_url in OFFICIAL_ENDPOINTS.items():
            for path in AUTH_ENDPOINTS:
                success, msg, elapsed = test_auth_endpoint(
                    base_url, path, api_key, api_secret
                )
                result = {
                    "domain": domain,
                    "path": path,
                    "url": f"{base_url}{path}",
                    "success": success,
                    "message": msg,
                    "response_ms": round(elapsed, 1),
                }
                report["auth_tests"].append(result)

                status = "✅" if success else "❌"
                logger.info(f"  {status} {domain}{path} — {msg} ({elapsed:.0f}ms)")

                if success:
                    report["working_endpoints"].append(f"{domain}{path} [auth]")
    else:
        logger.info("\n⚠️ Phase 2: SKIPPED — no API keys in .env")

    # Summary
    total_tests = len(report["public_tests"]) + len(report["auth_tests"])
    working = len(report["working_endpoints"])
    geo_blocked = len(report["geo_blocked"])

    report["summary"] = {
        "total_tests": total_tests,
        "working": working,
        "geo_blocked_domains": geo_blocked,
        "all_blocked": working == 0,
    }

    logger.info("\n" + "=" * 80)
    logger.info(
        f"📊 SUMMARY: {working}/{total_tests} working, {geo_blocked} domains geo-blocked"
    )
    if working > 0:
        logger.info(f"✅ Working endpoints: {report['working_endpoints']}")
    else:
        logger.info("❌ ALL endpoints blocked — geographic restriction confirmed")
        logger.info("   Solutions:")
        logger.info("   1. Use a proxy server in an allowed country")
        logger.info("   2. Move server to an allowed region")
        logger.info("   3. Use Binance Testnet for development")
        logger.info("   4. Use an alternative exchange API")
    logger.info("=" * 80)

    return report


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    report = run_full_test()

    # Save report
    import json

    report_path = "/tmp/binance_connectivity_test.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Full report saved to: {report_path}")
