"""Firebase phone token verification helpers.

This module provides a lightweight compatibility layer for routes that expect
Firebase SMS/Phone verification functionality.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from backend.infrastructure.db_access import get_db_manager

logger = logging.getLogger(__name__)

try:
    import firebase_admin
    from firebase_admin import auth, credentials

    FIREBASE_ADMIN_AVAILABLE = True
except Exception:  # pragma: no cover - import-time optional dependency
    FIREBASE_ADMIN_AVAILABLE = False


class FirebaseSMSHandler:
    """Handles Firebase phone token verification and user updates."""

    _initialized = False

    def __init__(self) -> None:
        self._db = get_db_manager()
        self._is_available = False
        self._init_firebase()

    def _init_firebase(self) -> None:
        if not FIREBASE_ADMIN_AVAILABLE:
            logger.warning("firebase_admin is not installed")
            return

        if FirebaseSMSHandler._initialized and firebase_admin._apps:
            self._is_available = True
            return

        cred_path = _find_firebase_credentials_file()
        if not cred_path:
            logger.warning("No Firebase service-account credentials file found")
            return

        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(str(cred_path))
                firebase_admin.initialize_app(cred)
            FirebaseSMSHandler._initialized = True
            self._is_available = True
            logger.info("Firebase SMS handler initialized")
        except Exception as exc:
            logger.error("Failed to initialize Firebase Admin: %s", exc)
            self._is_available = False

    @property
    def is_available(self) -> bool:
        return self._is_available

    def verify_phone_token(
        self,
        id_token: str,
        expected_phone_number: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Verify Firebase ID token and ensure it contains a phone number."""
        if not self._is_available:
            return False, {"error": "خدمة SMS غير متاحة"}

        if not id_token:
            return False, {"error": "Firebase ID token مطلوب"}

        try:
            decoded = auth.verify_id_token(id_token)
            phone_number = decoded.get("phone_number")
            uid = decoded.get("uid")

            if not phone_number:
                return False, {"error": "الرمز لا يحتوي رقم هاتف"}

            if expected_phone_number and expected_phone_number.strip():
                if _normalize_phone(phone_number) != _normalize_phone(expected_phone_number):
                    return False, {"error": "رقم الهاتف لا يطابق الرمز"}

            return True, {"phone_number": phone_number, "uid": uid}
        except Exception as exc:
            logger.warning("Firebase token verification failed: %s", exc)
            return False, {"error": "فشل التحقق من رمز Firebase"}

    def update_user_verification_status(self, user_id: int, phone_number: str) -> bool:
        """Persist phone verification status for a user."""
        try:
            with self._db.get_write_connection() as conn:
                conn.execute(
                    """
                    UPDATE users
                    SET is_phone_verified = 1,
                        phone_number = COALESCE(NULLIF(%s, ''), phone_number),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (phone_number or "", user_id),
                )
                conn.commit()
            return True
        except Exception as exc:
            logger.error("Failed updating phone verification status: %s", exc)
            return False

    def send_sms(self, phone_number: str, message: str) -> bool:
        """Compatibility method. Firebase Admin cannot send SMS directly."""
        logger.info("SMS send requested for %s (not supported server-side by Firebase Admin)", phone_number)
        return False


def verify_firebase_phone_token(
    id_token: str,
    phone_number: Optional[str] = None,
) -> Tuple[bool, Dict[str, Any]]:
    return get_sms_handler().verify_phone_token(id_token, phone_number)


def send_sms_otp(phone: str, otp_code: str, action_name: str) -> bool:
    """Compatibility helper for older call-sites.

    Returns False so caller can use its existing fallback flow.
    """
    logger.info("send_sms_otp fallback path used for %s action=%s", phone, action_name)
    return False


_sms_handler_singleton: Optional[FirebaseSMSHandler] = None


def get_sms_handler() -> FirebaseSMSHandler:
    global _sms_handler_singleton
    if _sms_handler_singleton is None:
        _sms_handler_singleton = FirebaseSMSHandler()
    return _sms_handler_singleton


def _normalize_phone(phone: str) -> str:
    return "".join(ch for ch in (phone or "") if ch.isdigit())


def _find_firebase_credentials_file() -> Optional[Path]:
    root = Path(__file__).resolve().parents[2]
    candidates = [
        os.getenv("FIREBASE_CREDENTIALS_PATH"),
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        root / "config" / "security" / "firebase-service-account.json",
        root / "tradingai-bot-firebase-adminsdk-fbsvc-82584e6886.json",
        root / "firebase-service-account.json",
    ]

    for cand in candidates:
        if not cand:
            continue
        p = Path(cand)
        if p.exists() and p.is_file():
            return p
    return None
