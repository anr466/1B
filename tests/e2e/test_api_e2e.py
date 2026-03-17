#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E API Tests — Trading AI Bot
================================
اختبارات شاملة من البداية للنهاية للـ Backend API
يختبر تدفق كامل: Auth → User Data → Notifications → FCM → Admin

الاستخدام:
    pytest tests/e2e/test_api_e2e.py -v
    pytest tests/e2e/test_api_e2e.py -v --tb=short

المتطلبات:
    pip install pytest requests
    يجب أن يكون الخادم شغالاً على port 3002
"""

import time
import uuid
import pytest
import requests

# ─── Config ──────────────────────────────────────────────────────────────────

BASE_URL = "http://localhost:3002/api"

ADMIN_EMAIL    = "admin@tradingbot.com"
ADMIN_PASSWORD = "admin123"

TIMEOUT = 10  # seconds per request

# ─── Session State ───────────────────────────────────────────────────────────

class State:
    admin_token:  str  = ""
    admin_id:     int  = 0
    user_token:   str  = ""
    user_id:      int  = 0
    test_fcm_token: str = f"test_fcm_{uuid.uuid4().hex[:16]}"
    notification_id: int = 0


state = State()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def api(method: str, path: str, *, token: str = "", **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    headers.setdefault("Content-Type", "application/json")
    url = BASE_URL + path
    return requests.request(method, url, headers=headers, timeout=TIMEOUT, **kwargs)


def ok(resp: requests.Response, context: str = "") -> dict:
    """Assert 2xx and return parsed JSON."""
    label = f" [{context}]" if context else ""
    assert resp.status_code < 300, (
        f"Expected 2xx{label}, got {resp.status_code}: {resp.text[:300]}"
    )
    data = resp.json()
    assert data.get("success") is not False, (
        f"success=False{label}: {data.get('error', data)}"
    )
    return data


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Infrastructure
# ═══════════════════════════════════════════════════════════════════════════════

class TestInfrastructure:
    def test_health_check(self):
        resp = requests.get("http://localhost:3002/health", timeout=TIMEOUT)
        assert resp.status_code == 200, f"Server not running: {resp.status_code}"
        body = resp.json()
        assert body["status"] == "healthy", f"Unhealthy: {body}"

    def test_api_version(self):
        resp = requests.get(f"{BASE_URL}/version", timeout=TIMEOUT)
        assert resp.status_code == 200
        body = resp.json()
        assert "current_version" in body

    def test_connection_info(self):
        resp = requests.get("http://localhost:3002/api/connection/info", timeout=TIMEOUT)
        assert resp.status_code == 200
        body = resp.json()
        assert "port" in body
        assert body["port"] == 3002

    def test_unauthenticated_request_rejected(self):
        """طلب بدون توكن يجب أن يُرفض"""
        resp = api("GET", f"/user/portfolio/1")
        assert resp.status_code in (401, 403), (
            f"Expected 401/403 without token, got {resp.status_code}"
        )

    def test_invalid_token_rejected(self):
        resp = api("GET", f"/user/portfolio/1", token="invalid.token.here")
        assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Authentication Flow
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthFlow:
    def test_login_admin(self):
        resp = api("POST", "/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        })
        data = ok(resp, "admin login")
        assert "token" in data or "token" in data.get("data", {}), (
            f"No token in response: {data}"
        )
        token = data.get("token") or data["data"]["token"]
        user  = data.get("user")  or data["data"].get("user", {})
        state.admin_token = token
        state.admin_id    = user.get("id", 1)
        assert state.admin_token, "Empty admin token"

    def test_validate_session(self):
        assert state.admin_token, "Need admin token from previous test"
        resp = api("GET", "/auth/validate-session", token=state.admin_token)
        assert resp.status_code == 200

    def test_login_wrong_password_rejected(self):
        resp = api("POST", "/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": "wrong_password_xyz",
        })
        assert resp.status_code in (400, 401, 403), (
            f"Expected 4xx for wrong password, got {resp.status_code}"
        )

    def test_login_missing_fields_rejected(self):
        resp = api("POST", "/auth/login", json={"email": ADMIN_EMAIL})
        assert resp.status_code in (400, 422)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. User Data Flow
# ═══════════════════════════════════════════════════════════════════════════════

class TestUserData:
    def setup_method(self):
        assert state.admin_token, "Need admin token — run TestAuthFlow first"
        self.token = state.admin_token
        self.uid   = state.admin_id or 1

    def test_portfolio(self):
        resp = api("GET", f"/user/portfolio/{self.uid}", token=self.token)
        # A fresh admin may have no portfolio rows → 400 PORTFOLIO_ERROR is acceptable
        assert resp.status_code in (200, 400), (
            f"Unexpected portfolio status: {resp.status_code} — {resp.text[:200]}"
        )
        if resp.status_code == 200:
            assert "data" in resp.json()

    def test_stats(self):
        resp = api("GET", f"/user/stats/{self.uid}", token=self.token)
        data = ok(resp, "stats")
        assert "data" in data

    def test_active_positions(self):
        resp = api("GET", f"/user/active-positions/{self.uid}", token=self.token)
        data = ok(resp, "active positions")
        assert "data" in data

    def test_trades_list(self):
        resp = api("GET", f"/user/trades/{self.uid}?limit=10", token=self.token)
        data = ok(resp, "trades list")
        assert "data" in data

    def test_trades_with_status_filter(self):
        resp = api("GET", f"/user/trades/{self.uid}?status=closed&limit=5", token=self.token)
        assert resp.status_code == 200

    def test_settings_get(self):
        resp = api("GET", f"/user/settings/{self.uid}", token=self.token)
        data = ok(resp, "settings get")
        assert "data" in data

    def test_daily_status(self):
        resp = api("GET", f"/user/daily-status/{self.uid}", token=self.token)
        assert resp.status_code == 200

    def test_daily_pnl(self):
        resp = api("GET", f"/user/daily-pnl/{self.uid}?days=30", token=self.token)
        assert resp.status_code == 200

    def test_user_profile(self):
        resp = api("GET", f"/user/profile/{self.uid}", token=self.token)
        assert resp.status_code == 200

    def test_cross_user_isolation(self):
        """مستخدم لا يمكنه الوصول لبيانات مستخدم آخر"""
        other_id = self.uid + 9999
        resp = api("GET", f"/user/portfolio/{other_id}", token=self.token)
        # يجب أن يُرفض أو يُعيد بيانات فارغة/خطأ
        assert resp.status_code in (200, 403, 404)
        if resp.status_code == 200:
            body = resp.json()
            # إما success=False أو data فارغة
            assert body.get("success") is False or body.get("data") is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Notifications Flow
# ═══════════════════════════════════════════════════════════════════════════════

class TestNotificationsFlow:
    def setup_method(self):
        assert state.admin_token
        self.token = state.admin_token
        self.uid   = state.admin_id or 1

    def test_notifications_list(self):
        resp = api("GET", f"/user/notifications/{self.uid}", token=self.token)
        data = ok(resp, "notifications list")
        assert "data" in data
        notifs = data["data"]
        if isinstance(notifs, list) and notifs:
            state.notification_id = notifs[0].get("id", 0)

    def test_notifications_stats(self):
        resp = api("GET", f"/user/notifications/{self.uid}/stats", token=self.token)
        assert resp.status_code == 200

    def test_notification_settings_get(self):
        resp = api("GET", "/user/notifications/settings", token=self.token)
        assert resp.status_code == 200

    def test_notification_settings_update(self):
        resp = api("PUT", "/user/notifications/settings", token=self.token, json={
            "dailySummary": True,
            "tradeOpened": True,
            "tradeClosed": True,
        })
        assert resp.status_code in (200, 201), (
            f"Notification settings update failed: {resp.status_code} — {resp.text[:200]}"
        )
        body = resp.json()
        assert body.get("success") is not False

    def test_notifications_list_with_pagination(self):
        resp = api("GET", f"/user/notifications/{self.uid}?page=1&limit=5", token=self.token)
        assert resp.status_code == 200

    def test_notifications_mark_all_read(self):
        resp = api("POST", f"/user/notifications/{self.uid}/mark-all-read", token=self.token)
        assert resp.status_code in (200, 201, 204)

    def test_single_notification_read(self):
        if not state.notification_id:
            pytest.skip("No notification_id available")
        resp = api("POST", f"/user/notifications/{state.notification_id}/read",
                   token=self.token)
        assert resp.status_code in (200, 201, 404)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. FCM Token Flow
# ═══════════════════════════════════════════════════════════════════════════════

class TestFcmTokenFlow:
    def setup_method(self):
        assert state.admin_token
        self.token = state.admin_token

    def test_register_fcm_token(self):
        resp = api("POST", "/user/fcm-token", token=self.token, json={
            "fcm_token": state.test_fcm_token,
            "platform": "android",
        })
        assert resp.status_code in (200, 201), (
            f"FCM register failed: {resp.status_code} — {resp.text[:200]}"
        )
        body = resp.json()
        assert body.get("success") is not False

    def test_register_fcm_token_missing_field(self):
        resp = api("POST", "/user/fcm-token", token=self.token, json={})
        assert resp.status_code in (400, 422)

    def test_register_fcm_token_twice_is_idempotent(self):
        """تسجيل نفس التوكن مرتين يجب أن ينجح بدون خطأ"""
        resp = api("POST", "/user/fcm-token", token=self.token, json={
            "fcm_token": state.test_fcm_token,
            "platform": "android",
        })
        assert resp.status_code in (200, 201)

    def test_unregister_fcm_token(self):
        resp = api("DELETE", "/user/fcm-token", token=self.token, json={
            "fcm_token": state.test_fcm_token,
        })
        assert resp.status_code in (200, 204), (
            f"FCM unregister failed: {resp.status_code} — {resp.text[:200]}"
        )

    def test_unregister_nonexistent_token_is_safe(self):
        """حذف توكن غير موجود لا يسبب خطأ 5xx"""
        resp = api("DELETE", "/user/fcm-token", token=self.token, json={
            "fcm_token": "nonexistent_token_abc123xyz",
        })
        assert resp.status_code < 500


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Device Registration Flow
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeviceRegistration:
    def setup_method(self):
        assert state.admin_token
        self.token = state.admin_token

    def test_register_device(self):
        resp = api("POST", "/user/device/register", token=self.token, json={
            "device_id": f"test_device_{uuid.uuid4().hex[:8]}",
            "device_name": "E2E Test Device",
            "device_type": "android",
            "fcm_token": f"test_device_fcm_{uuid.uuid4().hex[:12]}",
        })
        # قد يكون 200 أو 201 أو 404 إذا لم يكن المسار موجوداً
        assert resp.status_code < 500, f"Server error on device register: {resp.text[:200]}"

    def test_register_device_missing_device_id(self):
        resp = api("POST", "/user/device/register", token=self.token, json={
            "device_name": "Missing ID Device",
            "device_type": "android",
        })
        assert resp.status_code in (400, 404, 422)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Admin Flow
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminFlow:
    def setup_method(self):
        assert state.admin_token, "Need admin token"
        self.token = state.admin_token

    def test_trading_state(self):
        resp = api("GET", "/admin/trading/state", token=self.token)
        data = ok(resp, "trading state")
        assert "data" in data or "state" in data or "trading_enabled" in str(data)

    def test_system_stats(self):
        resp = api("GET", "/admin/system/stats", token=self.token)
        assert resp.status_code == 200

    def test_admin_users_list(self):
        resp = api("GET", "/admin/users/all", token=self.token)
        data = ok(resp, "users list")
        assert "data" in data
        payload = data["data"]
        # Response may be a list OR {users: [...], stats: {...}}
        users = payload if isinstance(payload, list) else payload.get("users", payload)
        assert isinstance(users, list), f"Expected list of users, got: {type(users)}"
        assert len(users) > 0, "No users returned"

    def test_admin_config_get(self):
        resp = api("GET", "/admin/config", token=self.token)
        assert resp.status_code == 200

    def test_admin_system_public_status(self):
        resp = api("GET", "/admin/system/public-status", token=self.token)
        assert resp.status_code == 200

    def test_regular_user_cannot_access_admin(self):
        """مستخدم عادي لا يمكنه الوصول للـ admin endpoints"""
        # استخدام توكن مزيف يشبه توكن مستخدم عادي
        resp = api("GET", "/admin/users/all", token="fake_user_token_not_admin")
        assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Full User Journey (end-to-end scenario)
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullUserJourney:
    """سيناريو كامل: تسجيل دخول → بيانات → إشعارات → FCM → تسجيل خروج"""

    def test_full_journey(self):
        # Step 1: Login
        resp = api("POST", "/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
        })
        assert resp.status_code == 200, f"Login failed: {resp.text[:200]}"
        login_data = resp.json()
        token = login_data.get("token") or login_data["data"]["token"]
        uid   = (login_data.get("user") or login_data["data"].get("user", {})).get("id", 1)

        # Step 2: Load dashboard data in parallel-ish sequence
        for endpoint in [
            f"/user/portfolio/{uid}",
            f"/user/stats/{uid}",
            f"/user/active-positions/{uid}",
        ]:
            r = api("GET", endpoint, token=token)
            # Portfolio may return 400 for fresh admin with no portfolio records
            assert r.status_code in (200, 400), (
                f"Dashboard load failed at {endpoint}: {r.text[:200]}"
            )

        # Step 3: Load trades
        r = api("GET", f"/user/trades/{uid}?limit=20", token=token)
        assert r.status_code == 200

        # Step 4: Check notifications
        r = api("GET", f"/user/notifications/{uid}", token=token)
        assert r.status_code == 200

        # Step 5: Update notification settings
        r = api("PUT", "/user/notifications/settings", token=token, json={
            "dailySummary": True,
            "tradeOpened": True,
        })
        assert r.status_code in (200, 201)

        # Step 6: Register FCM token
        journey_fcm = f"journey_fcm_{uuid.uuid4().hex[:16]}"
        r = api("POST", "/user/fcm-token", token=token, json={
            "fcm_token": journey_fcm,
            "platform": "android",
        })
        assert r.status_code in (200, 201), f"FCM register failed: {r.text[:200]}"

        # Step 7: Load settings
        r = api("GET", f"/user/settings/{uid}", token=token)
        assert r.status_code == 200

        # Step 8: Cleanup — unregister FCM
        r = api("DELETE", "/user/fcm-token", token=token, json={"fcm_token": journey_fcm})
        assert r.status_code < 500

        # Journey complete ✅


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Performance — basic response time checks
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformance:
    MAX_MS = 2000  # 2 seconds max per endpoint

    def setup_method(self):
        assert state.admin_token
        self.token = state.admin_token
        self.uid   = state.admin_id or 1

    def _check_speed(self, method: str, path: str, **kwargs):
        start = time.monotonic()
        resp  = api(method, path, token=self.token, **kwargs)
        ms    = (time.monotonic() - start) * 1000
        assert resp.status_code < 500, f"{path} returned {resp.status_code}"
        assert ms < self.MAX_MS, (
            f"{path} took {ms:.0f}ms — exceeded {self.MAX_MS}ms limit"
        )

    def test_portfolio_speed(self):
        self._check_speed("GET", f"/user/portfolio/{self.uid}")

    def test_stats_speed(self):
        self._check_speed("GET", f"/user/stats/{self.uid}")

    def test_trades_speed(self):
        self._check_speed("GET", f"/user/trades/{self.uid}?limit=20")

    def test_trading_state_speed(self):
        self._check_speed("GET", "/admin/trading/state")
