#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend Unit Tests — No DB Required
====================================
Tests Flask/FastAPI route registration, blueprint structure, and API endpoint
consistency without requiring PostgreSQL or Docker.

Tests that require unavailable local deps (cryptography, etc.) are skipped
gracefully — they run fine in Docker where all deps are installed.
"""

import sys
import os

import pytest
from unittest.mock import patch, MagicMock

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "config"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "database"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))


def _can_import_blueprints():
    """Check if all required deps for blueprint imports are available."""
    try:
        import cryptography  # noqa: F401
        import binance  # noqa: F401
        return True
    except ImportError:
        return False


requires_blueprints = pytest.mark.skipif(
    not _can_import_blueprints(),
    reason="Required dependencies (cryptography, binance) not installed locally; run in Docker"
)


# ────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def flask_app():
    """Create Flask app with all blueprints registered (mocked DB & deps)."""
    from flask import Flask

    # Mock unavailable modules BEFORE any imports that need them
    # These are available in Docker but not in local dev environment
    _mock_modules = [
        "cryptography", "cryptography.hazmat", "cryptography.hazmat.primitives",
        "cryptography.hazmat.primitives.ciphers",
        "cryptography.hazmat.primitives.ciphers.aead",
        "cryptography.hazmat.primitives.kdf",
        "cryptography.hazmat.primitives.kdf.pbkdf2",
        "cryptography.hazmat.backends",
        "binance", "binance.client",
        "firebase_admin",
        "slowapi", "slowapi.util", "slowapi.errors",
        "flask_limiter", "flask_limiter.util",
        "pandas_ta",
    ]
    for mod in _mock_modules:
        sys.modules.setdefault(mod, MagicMock())

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["JSON_AS_ASCII"] = False

    # Mock DB manager before any blueprint imports
    mock_db = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (1,)
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.execute.return_value = mock_cursor
    mock_db.get_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_db.get_connection.return_value.__exit__ = MagicMock(return_value=False)
    mock_db.get_write_connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_db.get_write_connection.return_value.__exit__ = MagicMock(return_value=False)

    with patch("backend.infrastructure.db_access.get_db_manager", return_value=mock_db):
        # Import blueprints
        # NOTE: auth_bp already includes password routes from auth_password_routes
        # (register_password_routes is called in auth_endpoints.py during import)
        from backend.api.auth_endpoints import auth_bp
        from backend.api.system_endpoints import system_bp
        from backend.api.token_refresh_endpoint import token_refresh_bp
        from backend.api.mobile_endpoints import mobile_bp
        from backend.api.secure_actions_endpoints import secure_actions_bp
        from backend.api.fcm_endpoints import fcm_bp
        from backend.api.login_otp_endpoints import login_otp_bp
        from backend.api.client_logs_endpoint import client_logs_bp
        from backend.api.ml_status_endpoints import ml_status_bp
        from backend.api.system_health import health_bp

        # Register all blueprints (password routes already in auth_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(system_bp)
        app.register_blueprint(token_refresh_bp)
        app.register_blueprint(mobile_bp)
        app.register_blueprint(secure_actions_bp)
        app.register_blueprint(fcm_bp)
        app.register_blueprint(login_otp_bp)
        app.register_blueprint(client_logs_bp)
        app.register_blueprint(ml_status_bp)
        app.register_blueprint(health_bp)

    yield app


@pytest.fixture(scope="session")
def client(flask_app):
    """Flask test client."""
    return flask_app.test_client()


# ────────────────────────────────────────────────────────────
# Test: Blueprint Route Registration
# ────────────────────────────────────────────────────────────

class TestBlueprintRegistration:
    """Verify that all expected blueprints are registered with correct prefixes."""

    EXPECTED_BLUEPRINTS = {
        "auth": "/auth",
        "system": "/system",
        "token_refresh": "",  # no prefix; routes use full paths like /refresh
        "mobile": "/user",
        "secure_actions": "/user/secure",
        "fcm": "/notifications",
        "login_otp": "/auth/login",
        "client_logs": "",  # no prefix; routes use full paths
        "ml_status": "/admin/ml",
        "health": "",  # no prefix; routes use /system/health path directly
    }

    def test_all_blueprints_registered(self, flask_app):
        """All core blueprints must be registered."""
        registered = {bp.name for bp in flask_app.blueprints.values()}
        for name in self.EXPECTED_BLUEPRINTS:
            assert name in registered, f"Blueprint '{name}' not registered"

    def test_blueprint_url_prefixes(self, flask_app):
        """Each blueprint must have the correct URL prefix."""
        for name, expected_prefix in self.EXPECTED_BLUEPRINTS.items():
            bp = flask_app.blueprints.get(name)
            assert bp is not None, f"Blueprint '{name}' not found"
            actual_prefix = bp.url_prefix or ""
            assert actual_prefix == expected_prefix, (
                f"Blueprint '{name}' prefix: expected '{expected_prefix}', got '{actual_prefix}'"
            )


# ────────────────────────────────────────────────────────────
# Test: Route Existence (key routes must resolve)
# ────────────────────────────────────────────────────────────

class TestRouteExistence:
    """Verify that critical API routes exist and return proper status codes."""

    # Routes that should return non-404 status (may require auth)
    KEY_GET_ROUTES = [
        "/system/status",
        "/system/health",
    ]

    # Routes that should return 405 (GET not allowed, POST expected)
    POST_ONLY_ROUTES = [
        "/auth/login",
        "/auth/send-otp",
        "/auth/forgot-password",
    ]

    @pytest.mark.parametrize("route", KEY_GET_ROUTES)
    def test_get_routes_exist(self, client, route):
        """GET routes should not return 404."""
        response = client.get(route)
        assert response.status_code != 404, f"Route {route} returned 404"

    @pytest.mark.parametrize("route", POST_ONLY_ROUTES)
    def test_post_only_routes_reject_get(self, client, route):
        """POST-only routes should return 405 on GET request."""
        response = client.get(route)
        assert response.status_code == 405, (
            f"Route {route} should return 405 for GET, got {response.status_code}"
        )


# ────────────────────────────────────────────────────────────
# Test: Secure Actions Routes
# ────────────────────────────────────────────────────────────

class TestSecureActionsRoutes:
    """Verify the secure actions blueprint routes."""

    SECURE_ROUTES = [
        "/user/secure/request-verification",
        "/user/secure/verify-and-execute",
    ]

    @pytest.mark.parametrize("route", SECURE_ROUTES)
    def test_secure_routes_reject_get(self, client, route):
        """Secure action routes should return 405 on GET (POST only)."""
        response = client.get(route)
        assert response.status_code == 405, (
            f"Secure route {route} should return 405 for GET, got {response.status_code}"
        )

    def test_secure_get_verification_options(self, client):
        """GET verification options requires auth."""
        response = client.get("/user/secure/get-verification-options/change_username")
        # Should be 401 (auth required) or 405 — not 404
        assert response.status_code in (401, 405), (
            f"Expected 401/405, got {response.status_code}"
        )


# ────────────────────────────────────────────────────────────
# Test: Flutter ↔ Backend API Endpoint Consistency
# ────────────────────────────────────────────────────────────

class TestApiEndpointConsistency:
    """Cross-check Flutter ApiEndpoints with Flask route patterns."""

    # These Flutter endpoints should map to Flask routes
    FLUTTER_ENDPOINTS = {
        "login": "/auth/login",
        "register": "/auth/register",
        "sendOtp": "/auth/send-otp",
        "verifyOtp": "/auth/verify-otp",
        "forgotPassword": "/auth/forgot-password",
        "resetPassword": "/auth/reset-password",
        "refreshToken": "/auth/refresh",
        "fcmToken": "/notifications/fcm-token",
        "systemStatus": "/system/status",
        "secureInitiate": "/user/secure/request-verification",
        "secureVerify": "/user/secure/verify-and-execute",
        # Password change routes are registered on auth_bp
        "sendChangeEmailOtp": "/auth/send-change-email-otp",
        "verifyChangeEmailOtp": "/auth/verify-change-email-otp",
        "sendChangePasswordOtp": "/auth/send-change-password-otp",
        "verifyChangePasswordOtp": "/auth/verify-change-password-otp",
    }

    def test_flutter_endpoints_match_backend(self, flask_app):
        """Every Flutter endpoint should have a corresponding Flask route."""
        all_routes = set()
        for rule in flask_app.url_map.iter_rules():
            all_routes.add(rule.rule)

        missing = []
        for name, path in self.FLUTTER_ENDPOINTS.items():
            if path not in all_routes:
                missing.append((name, path))

        assert not missing, (
            f"Missing Flask routes for Flutter endpoints:\n"
            + "\n".join(f"  {n}: {p}" for n, p in missing)
        )


# ────────────────────────────────────────────────────────────
# Test: Lazy import of backend.core
# ────────────────────────────────────────────────────────────

class TestLazyImport:
    """Verify that backend.core can be imported without triggering DB connection."""

    def test_import_backend_core_no_db(self):
        """Importing backend.core should not trigger a DB connection."""
        import importlib
        import backend.core

        importlib.reload(backend.core)

        # GroupBSystem should be accessible via __getattr__
        assert hasattr(backend.core, "__all__"), "backend.core missing __all__"
        assert "GroupBSystem" in backend.core.__all__, "GroupBSystem not in __all__"


# ────────────────────────────────────────────────────────────
# Test: Config Validation
# ────────────────────────────────────────────────────────────

class TestConfigValidation:
    """Verify configuration files are syntactically valid."""

    def test_unified_settings_importable(self):
        """unified_settings.py should be importable."""
        from config.unified_settings import UnifiedSettings

        settings = UnifiedSettings()
        assert hasattr(settings, "LOG_FILE"), "UnifiedSettings missing LOG_FILE"
        # LOG_FILE should default to containing app.log (matching .env.example)
        assert "app.log" in settings.LOG_FILE, (
            f"LOG_FILE should contain 'app.log', got '{settings.LOG_FILE}'"
        )

    def test_dockerfile_python_version(self):
        """Dockerfile should use python:3.13-slim."""
        dockerfile_path = os.path.join(PROJECT_ROOT, "Dockerfile")
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "python:3.13-slim" in content, (
            "Dockerfile should use python:3.13-slim"
        )


# ────────────────────────────────────────────────────────────
# Test: No SELECT * in backend code
# ────────────────────────────────────────────────────────────

class TestNoSelectStar:
    """Verify that no SELECT * remains in backend/database code."""

    def test_no_select_star_in_backend(self):
        """No SQL query should use SELECT *."""
        import re

        pattern = re.compile(r"SELECT\s+\*\s+FROM", re.IGNORECASE)
        violations = []

        for root, dirs, files in os.walk(os.path.join(PROJECT_ROOT, "backend")):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules")]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if pattern.search(line):
                            violations.append(f"{fpath}:{i}: {line.strip()}")

        for root, dirs, files in os.walk(os.path.join(PROJECT_ROOT, "database")):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "node_modules")]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if pattern.search(line):
                            violations.append(f"{fpath}:{i}: {line.strip()}")

        assert not violations, (
            f"Found {len(violations)} SELECT * violations:\n"
            + "\n".join(violations)
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])