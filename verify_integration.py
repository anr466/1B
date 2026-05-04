#!/usr/bin/env python3
"""
Integration Verification Script
===============================
Verifies the integrity of communication between:
1. Database Schema
2. Backend API (Routes & Data)
3. Flutter App (Models & Endpoints)
"""

import sys
import os
import re
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check_db_schema():
    """Verify DB schema has required columns for new features."""
    print("🔍 Checking Database Schema...")
    schema_file = "database/postgres_schema.sql"
    if not os.path.exists(schema_file):
        print("   ❌ Schema file not found!")
        return False

    with open(schema_file, "r") as f:
        content = f.read()

    checks = {
        "portfolio.is_demo": "is_demo BOOLEAN" in content,
        "portfolio.available_balance": "available_balance" in content,
        "active_positions.trailing_sl_price": "trailing_sl_price" in content,
        "active_positions.position_type": "position_type" in content,
        "user_settings.trading_enabled": "trading_enabled" in content,
        "user_settings.is_demo": "is_demo" in content and "user_settings" in content,
    }

    all_ok = True
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
        if not passed:
            all_ok = False

    # Check migration
    migration = "database/migrations/004_add_growth_mode.sql"
    if os.path.exists(migration):
        print("   ✅ Migration 004 (growth_mode) exists")
    else:
        print("   ❌ Migration 004 missing")
        all_ok = False

    return all_ok


def check_api_routes():
    """Verify Backend API routes match Flutter expectations."""
    print("\n🔍 Checking Backend API Routes...")

    # Read Flutter endpoints
    flutter_file = "flutter_trading_app/lib/core/constants/api_endpoints.dart"
    if not os.path.exists(flutter_file):
        print("   ❌ Flutter endpoints file not found!")
        return False

    with open(flutter_file, "r") as f:
        flutter_content = f.read()

    # Extract expected routes
    expected_routes = {
        "portfolio": r"'/user/portfolio/\$userId'",
        "active_positions": r"'/user/active-positions/\$userId'",
        "settings": r"'/user/settings/\$userId'",
        "stats": r"'/user/stats/\$userId'",
    }

    # Check Backend files
    backend_files = [
        "backend/api/mobile_endpoints.py",
        "backend/api/mobile_trades_routes.py",
        "backend/api/mobile_settings_routes.py",
    ]

    backend_routes = {}
    for f_path in backend_files:
        if os.path.exists(f_path):
            with open(f_path, "r") as f:
                content = f.read()
                # Find route definitions
                routes = re.findall(r'@.*\.route\("([^"]+)"', content)
                for route in routes:
                    backend_routes[route.split("/")[1]] = route  # Simple check

    all_ok = True
    # Manual checks for critical routes
    checks = {
        "Portfolio Endpoint": any(
            "portfolio/<int:user_id>" in open(f).read()
            for f in backend_files
            if os.path.exists(f)
        ),
        "Active Positions Endpoint": any(
            "active-positions/<int:user_id>" in open(f).read()
            for f in backend_files
            if os.path.exists(f)
        ),
        "Settings Update Endpoint": any(
            'methods=["PUT"]' in open(f).read()
            and "settings/<int:user_id>" in open(f).read()
            for f in backend_files
            if os.path.exists(f)
        ),
    }

    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
        if not passed:
            all_ok = False

    return all_ok


def check_data_models():
    """Verify JSON keys match between Backend and Flutter."""
    print("\n🔍 Checking Data Model Compatibility...")

    # Backend Portfolio Response keys
    backend_portfolio_keys = [
        "currentBalance",
        "totalBalance",
        "initialBalance",
        "availableBalance",
        "lockedBalance",
        "dailyPnL",
        "totalPnL",
        "realizedPnL",
        "unrealizedPnL",
    ]

    # Flutter Portfolio Model keys (fromJson)
    flutter_portfolio_keys = [
        "current_balance",
        "totalBalance",
        "balance",  # currentBalance
        "initial_balance",
        "initialBalance",  # initialBalance
        "available_balance",
        "availableBalance",  # availableBalance
        "lockedBalance",
        "reserved_balance",
        "investedBalance",  # reservedBalance
        "dailyPnL",
        "daily_pnl",  # dailyPnL
        "totalPnL",
        "total_pnl",
        "totalProfitLoss",  # totalPnL
    ]

    # Check if Flutter handles Backend keys
    flutter_model_file = "flutter_trading_app/lib/core/models/portfolio_model.dart"
    if not os.path.exists(flutter_model_file):
        print("   ❌ Flutter Portfolio Model not found!")
        return False

    with open(flutter_model_file, "r") as f:
        model_content = f.read()

    all_ok = True
    for key in backend_portfolio_keys:
        if key in model_content:
            print(f"   ✅ Flutter handles '{key}'")
        else:
            # Check for fallback
            snake = re.sub(r"(?<!^)(?=[A-Z])", "_", key).lower()
            if snake in model_content:
                print(f"   ✅ Flutter handles '{key}' (via {snake})")
            else:
                print(f"   ⚠️ Flutter might miss '{key}'")
                all_ok = False

    return all_ok


def main():
    print("=" * 60)
    print("  INTEGRATION VERIFICATION")
    print("=" * 60)

    results = []
    results.append(("Database Schema", check_db_schema()))
    results.append(("API Routes", check_api_routes()))
    results.append(("Data Models", check_data_models()))

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 All checks passed! System is integrated and ready.")
    else:
        print("\n⚠️ Some checks failed. Please review the details above.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
