"""
Firebase Notification Service — إرسال إشعارات Push عبر FCM
يعتمد على firebase_admin SDK لإرسال رسائل FCM للأجهزة المسجّلة
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    _FIREBASE_ADMIN_OK = True
except Exception:
    _FIREBASE_ADMIN_OK = False

try:
    from database.database_manager import DatabaseManager
    _DB_OK = True
except Exception:
    _DB_OK = False


def _find_credentials_file() -> Optional[Path]:
    """البحث عن ملف service account في المسارات المعروفة"""
    root = Path(__file__).resolve().parents[2]
    candidates = [
        os.getenv("FIREBASE_CREDENTIALS_PATH"),
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        root / "config" / "security" / "firebase-service-account.json",
        root / "tradingai-bot-firebase-adminsdk-fbsvc-82584e6886.json",
        root / "firebase-service-account.json",
        root / "backend" / "config" / "firebase-service-account.json",
    ]
    for cand in candidates:
        if not cand:
            continue
        p = Path(cand)
        if p.exists() and p.is_file():
            return p
    return None


class FirebaseNotificationService:
    """
    خدمة إرسال Push Notifications عبر Firebase Cloud Messaging

    المهام:
    - تهيئة Firebase Admin SDK
    - تسجيل / حذف FCM tokens للمستخدمين
    - إرسال إشعارات لمستخدم واحد أو مجموعة
    """

    _initialized: bool = False

    def __init__(self) -> None:
        self._available = False
        self._db: Optional[DatabaseManager] = None

        if not _FIREBASE_ADMIN_OK:
            logger.warning("⚠️ firebase_admin غير مثبّت — الإشعارات معطّلة")
            return

        if _DB_OK:
            try:
                self._db = DatabaseManager()
            except Exception as e:
                logger.warning(f"⚠️ فشل تهيئة قاعدة البيانات: {e}")

        self._init_firebase()

    def _init_firebase(self) -> None:
        if FirebaseNotificationService._initialized and firebase_admin._apps:
            self._available = True
            return

        cred_path = _find_credentials_file()
        if not cred_path:
            logger.warning(
                "⚠️ لم يُعثر على ملف firebase service-account — الإشعارات معطّلة. "
                "ضع الملف في: config/security/firebase-service-account.json"
            )
            return

        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(str(cred_path))
                firebase_admin.initialize_app(cred)
            FirebaseNotificationService._initialized = True
            self._available = True
            logger.info("✅ FirebaseNotificationService جاهز")
        except Exception as exc:
            logger.error("❌ فشل تهيئة Firebase Admin: %s", exc)
            self._available = False

    def is_available(self) -> bool:
        return self._available

    # ─── Token Management ──────────────────────────────────────

    def register_token(self, user_id: int, fcm_token: str, platform: str = "android") -> bool:
        """تسجيل FCM token للمستخدم في جدول fcm_tokens"""
        if not fcm_token or not self._db:
            return False
        try:
            with self._db.get_write_connection() as conn:
                cursor = conn.cursor()
                # حذف أي token قديم لنفس المستخدم أو نفس الجهاز
                cursor.execute(
                    "DELETE FROM fcm_tokens WHERE user_id = %s OR fcm_token = %s",
                    (user_id, fcm_token)
                )
                cursor.execute(
                    "INSERT INTO fcm_tokens (user_id, fcm_token, platform, created_at) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
                    (user_id, fcm_token, platform)
                )
            logger.debug(f"✅ FCM token مسجّل للمستخدم {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل FCM token: {e}")
            return False

    def unregister_token(self, fcm_token: str) -> bool:
        """حذف FCM token من fcm_tokens"""
        if not fcm_token or not self._db:
            return False
        try:
            with self._db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM fcm_tokens WHERE fcm_token = %s",
                    (fcm_token,)
                )
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في حذف FCM token: {e}")
            return False

    def get_user_tokens(self, user_id: int) -> List[str]:
        """جلب كل FCM tokens للمستخدم من fcm_tokens"""
        if not self._db:
            return []
        try:
            with self._db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT fcm_token FROM fcm_tokens WHERE user_id = %s",
                    (user_id,)
                )
                rows = cursor.fetchall()
                return [row[0] for row in rows if row[0]]
        except Exception as e:
            logger.error(f"❌ خطأ في جلب FCM tokens: {e}")
            return []

    # ─── Sending ───────────────────────────────────────────────

    def send_to_user(
        self,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """إرسال إشعار لمستخدم واحد (كل أجهزته)"""
        if not self._available:
            return False

        tokens = self.get_user_tokens(user_id)
        if not tokens:
            logger.debug(f"لا توجد FCM tokens للمستخدم {user_id}")
            return False

        return self._send_to_tokens(tokens, title, body, data)

    def send_to_tokens(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """إرسال إشعار لقائمة tokens مباشرة"""
        if not self._available or not tokens:
            return False
        return self._send_to_tokens(tokens, title, body, data)

    def _send_to_tokens(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """الإرسال الفعلي عبر FCM"""
        if not tokens:
            return False

        # تحويل data إلى str:str كما يتطلب FCM
        str_data: Dict[str, str] = {}
        if data:
            for k, v in data.items():
                str_data[str(k)] = str(v) if v is not None else ""

        success_count = 0
        invalid_tokens: List[str] = []

        for token in tokens:
            try:
                msg = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data=str_data,
                    android=messaging.AndroidConfig(
                        priority="high",
                        notification=messaging.AndroidNotification(
                            icon="ic_notification",
                            color="#1565C0",
                            channel_id="trading_alerts",
                            sound="default",
                        ),
                    ),
                    token=token,
                )
                messaging.send(msg)
                success_count += 1
            except messaging.UnregisteredError:
                invalid_tokens.append(token)
                logger.debug(f"FCM token غير صالح: {token[:20]}...")
            except Exception as e:
                logger.warning(f"⚠️ فشل إرسال FCM: {e}")

        # حذف الـ tokens غير الصالحة من fcm_tokens
        if invalid_tokens and self._db:
            try:
                with self._db.get_write_connection() as conn:
                    cursor = conn.cursor()
                    for t in invalid_tokens:
                        cursor.execute(
                            "DELETE FROM fcm_tokens WHERE fcm_token = %s", (t,)
                        )
            except Exception:
                pass

        return success_count > 0

    def send_multicast(
        self,
        user_ids: List[int],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> int:
        """إرسال إشعار لعدة مستخدمين — يرجع عدد المرسَل إليهم"""
        if not self._available:
            return 0

        all_tokens: List[str] = []
        for uid in user_ids:
            all_tokens.extend(self.get_user_tokens(uid))

        if not all_tokens:
            return 0

        sent = self._send_to_tokens(all_tokens, title, body, data)
        return 1 if sent else 0


# ─── Singleton ─────────────────────────────────────────────────

_instance: Optional[FirebaseNotificationService] = None


def get_firebase_notification_service() -> FirebaseNotificationService:
    global _instance
    if _instance is None:
        _instance = FirebaseNotificationService()
    return _instance
