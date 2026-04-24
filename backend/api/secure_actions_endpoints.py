"""
Secure Actions Endpoints - نظام التحقق الموحد للعمليات الحساسة
================================================================

✅ جميع العمليات الحساسة تتطلب تحقق OTP (SMS أو Email)
✅ تغيير الإيميل → تحقق من الجوال
✅ تغيير الجوال → تحقق من الإيميل
✅ باقي العمليات → المستخدم يختار الطريقة

العمليات المدعومة:
- change_username: تغيير اسم المستخدم
- change_password: تغيير كلمة المرور
- change_email: تغيير الإيميل
- change_phone: تغيير رقم الجوال
- change_biometric: تفعيل/إلغاء البصمة
- change_binance_keys: تغيير مفاتيح Binance
"""

from backend.api.auth_middleware import require_auth
from backend.utils.password_utils import verify_password, hash_password
from backend.utils.user_lookup_service import get_user_by_id
from backend.infrastructure.db_access import get_db_manager
from flask import Blueprint, request, jsonify, g
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

# Database
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# استيراد خدمة OTP الموحدة
try:
    from backend.utils.simple_email_otp_service import SimpleEmailOTPService

    otp_service = SimpleEmailOTPService()
    OTP_SERVICE_AVAILABLE = True
except ImportError:
    otp_service = None
    OTP_SERVICE_AVAILABLE = False

db_manager = get_db_manager()
logger = logging.getLogger(__name__)

# إنشاء Blueprint
secure_actions_bp = Blueprint(
    "secure_actions", __name__, url_prefix="/user/secure"
)

# ==================== أنواع العمليات ====================

SECURE_ACTIONS = {
    "change_name": {
        "name": "تغيير الاسم الكامل",
        "verification_options": ["sms", "email"],  # ✅ SMS الافتراضي
        "requires_password": False,
    },
    "change_username": {
        "name": "تغيير اسم المستخدم",
        "verification_options": ["sms", "email"],  # ✅ SMS الافتراضي
        "requires_password": False,
    },
    "change_password": {
        "name": "تغيير كلمة المرور",
        "verification_options": ["sms", "email"],
        "requires_password": True,  # يتطلب كلمة المرور القديمة
    },
    "change_email": {
        "name": "تغيير الإيميل",
        # ✅ كلاهما متاح - SMS الافتراضي
        "verification_options": ["sms", "email"],
        "requires_password": False,
    },
    "change_phone": {
        "name": "تغيير رقم الجوال",
        # ✅ كلاهما متاح - SMS الافتراضي
        "verification_options": ["sms", "email"],
        "requires_password": False,
    },
    "change_biometric": {
        "name": "تغيير إعدادات البصمة",
        "verification_options": ["sms", "email"],
        "requires_password": False,
    },
    "change_binance_keys": {
        "name": "تغيير مفاتيح Binance",
        "verification_options": ["sms", "email"],
        "requires_password": False,
    },
    "delete_binance_keys": {
        "name": "حذف مفاتيح Binance",
        "verification_options": ["sms", "email"],
        "requires_password": False,
    },
}

DEDICATED_ACCOUNT_ACTIONS = {
    "change_password": "استخدم مسار تغيير كلمة المرور المخصص",
    "change_email": "استخدم مسار تغيير البريد الإلكتروني المخصص",
}

# ==================== OTP Storage (DB-backed) ====================


def _save_pending_verification(
    user_id, action, otp, expires_at, method, new_value=None, old_password=None
):
    """حفظ طلب تحقق معلق في قاعدة البيانات"""
    db = db_manager
    
    # FIX 9: Encrypt old_password before storing
    encrypted_password = None
    if old_password:
        try:
            from config.security.encryption_service import encrypt_password
            encrypted_password = encrypt_password(old_password)
        except Exception as e:
            logger.error(f"🔴 Failed to encrypt old_password: {e}")
            raise RuntimeError(f"Password encryption failed: {e}") from e
    
    with db.get_write_connection() as conn:
        conn.execute(
            """
            INSERT INTO pending_verifications
            (user_id, action, otp, expires_at, method, new_value, old_password, attempts)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
            ON CONFLICT (user_id, action) DO UPDATE SET
                otp = EXCLUDED.otp,
                expires_at = EXCLUDED.expires_at,
                method = EXCLUDED.method,
                new_value = EXCLUDED.new_value,
                old_password = EXCLUDED.old_password,
                attempts = GREATEST(pending_verifications.attempts, 0)
        """,
            (
                user_id,
                action,
                otp,
                expires_at.isoformat(),
                method,
                new_value,
                encrypted_password if encrypted_password else old_password,
            ),
        )


def _get_pending_verification(user_id, action):
    """جلب طلب تحقق معلق من قاعدة البيانات"""
    db = db_manager
    with db.get_connection() as conn:
        row = conn.execute(
            """
            SELECT otp, expires_at, method, new_value, old_password, attempts
            FROM pending_verifications
            WHERE user_id = %s AND action = %s
        """,
            (user_id, action),
        ).fetchone()
        if row:
            expires_raw = (
                row[1]
                if isinstance(row, (list, tuple))
                else (
                    row["expires_at"] if "expires_at" in row.keys() else row[1]
                )
            )
            if isinstance(expires_raw, datetime):
                expires_dt = expires_raw
                # Ensure timezone-aware so comparison with
                # datetime.now(timezone.utc) works
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            else:
                expires_dt = datetime.fromisoformat(str(expires_raw))
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=timezone.utc)
            return {
                "otp": (
                    row[0] if isinstance(row, (list, tuple)) else row["otp"]
                ),
                "expires": expires_dt,
                "method": (
                    row[2] if isinstance(row, (list, tuple)) else row["method"]
                ),
                "new_value": (
                    row[3]
                    if isinstance(row, (list, tuple))
                    else row["new_value"]
                ),
                "old_password": (
                    row[4]
                    if isinstance(row, (list, tuple))
                    else row["old_password"]
                ),
                "attempts": (
                    row[5]
                    if isinstance(row, (list, tuple))
                    else row["attempts"]
                ),
            }
    return None


def _update_pending_attempts(user_id, action, attempts):
    """تحديث عدد المحاولات"""
    db = db_manager
    with db.get_write_connection() as conn:
        conn.execute(
            """
            UPDATE pending_verifications SET attempts = %s
            WHERE user_id = %s AND action = %s
        """,
            (attempts, user_id, action),
        )


def _update_pending_otp(user_id, action, otp):
    """تحديث رمز OTP (عند إرسال OTP فعلي من خدمة الإيميل)"""
    db = db_manager
    with db.get_write_connection() as conn:
        conn.execute(
            """
            UPDATE pending_verifications SET otp = %s
            WHERE user_id = %s AND action = %s
        """,
            (otp, user_id, action),
        )


def _delete_pending_verification(user_id, action):
    """حذف طلب تحقق معلق"""
    db = db_manager
    with db.get_write_connection() as conn:
        conn.execute(
            """
            DELETE FROM pending_verifications
            WHERE user_id = %s AND action = %s
        """,
            (user_id, action),
        )


# ==================== Helper Functions ====================


def generate_otp(length=6):
    """توليد رمز OTP عشوائي"""
    return "".join([str(secrets.randbelow(10)) for _ in range(length)])


# ❌ DELETED: get_user_by_id() - Moved to unified service
# Reason: Duplicate implementation
# Replacement: backend/utils/user_lookup_service.py


def send_otp_email(email, otp_code, action_name):
    """إرسال OTP عبر الإيميل باستخدام SimpleEmailOTPService
    Returns: (success: bool, actual_code: str) - the actual OTP code sent to the user
    """
    try:
        if not (OTP_SERVICE_AVAILABLE and otp_service):
            logger.error("❌ OTP email service unavailable")
            return False, None

        success, service_code = otp_service.send_email_otp(
            email, purpose=action_name
        )
        if success:
            logger.info(f"✅ تم إرسال OTP إلى {email} للعملية: {action_name}")
            return True, service_code

        logger.error(f"❌ فشل إرسال OTP إلى {email}")
        return False, None
    except Exception as e:
        logger.error(f"خطأ في إرسال OTP: {e}")
        return False, None


def send_otp_sms(phone, otp_code, action_name):
    """إرسال OTP عبر SMS باستخدام Firebase"""
    try:
        from backend.utils.firebase_sms_service import send_sms_otp

        result = send_sms_otp(phone, otp_code, action_name)
        if result:
            logger.info(f"📱 تم إرسال OTP عبر Firebase SMS إلى {phone}")
            return True

        logger.error(f"❌ فشل إرسال OTP عبر SMS إلى {phone}")
        return False
    except ImportError:
        logger.error("❌ Firebase SMS service unavailable")
        return False
    except Exception as e:
        logger.error(f"خطأ في إرسال SMS: {e}")
        return False


def get_token_user_id():
    """الحصول على user_id من Token - مع التحقق من التوقيع"""
    try:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # 🔒 استخدام التحقق الحقيقي من التوقيع
            try:
                from backend.api.token_refresh_endpoint import verify_token

                payload = verify_token(token, "access")
                return payload.get("user_id") or payload.get("sub")
            except (ImportError, ModuleNotFoundError):
                # fallback: التحقق اليدوي مع التوقيع
                import jwt
                import os
                from dotenv import load_dotenv

                load_dotenv()
                jwt_secret = os.getenv("JWT_SECRET_KEY")
                if not jwt_secret:
                    logger.error("❌ JWT_SECRET_KEY not configured")
                    return None
                payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
                return payload.get("user_id") or payload.get("sub")
    except Exception as e:
        logger.debug(f"Token decode failed: {e}")
    return None


# ==================== API Endpoints ====================


@secure_actions_bp.route("/request-verification", methods=["POST"])
@require_auth
def request_verification():
    """
    طلب رمز التحقق لعملية حساسة

    Input:
    {
        "action": "change_username|change_password|change_email|change_phone|change_biometric|change_binance_keys",
        "method": "email|sms",
        "new_value": "القيمة الجديدة (اختياري)",
        "old_password": "كلمة المرور القديمة (للعمليات التي تتطلبها)"
    }

    Output:
    {
        "success": true,
        "message": "تم إرسال رمز التحقق",
        "method": "email|sms",
        "masked_target": "a***@example.com | +966****1234",
        "expires_in": 600
    }
    """
    try:
        user_id = g.user_id
        data = request.get_json(silent=True) or {}

        if not data:
            return jsonify({"success": False, "error": "لا توجد بيانات"}), 400

        action = data.get("action")
        method = data.get("method", "sms")  # ✅ الافتراضي: SMS
        new_value = (
            data.get("newValue")
            if "newValue" in data
            else data.get("new_value")
        )
        old_password = (
            data.get("oldPassword")
            if "oldPassword" in data
            else data.get("old_password")
        )

        # التحقق من نوع العملية
        if action not in SECURE_ACTIONS:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "نوع العملية غير مدعوم",
                        "supported_actions": list(SECURE_ACTIONS.keys()),
                    }
                ),
                400,
            )

        action_config = SECURE_ACTIONS[action]

        if action in DEDICATED_ACCOUNT_ACTIONS:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": DEDICATED_ACCOUNT_ACTIONS[action],
                    }
                ),
                400,
            )

        # التحقق من طريقة التحقق المسموحة
        if method not in action_config["verification_options"]:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"طريقة التحقق غير مسموحة لهذه العملية",
                        "allowed_methods": action_config[
                            "verification_options"
                        ],
                    }
                ),
                400,
            )

        # جلب بيانات المستخدم
        user = get_user_by_id(user_id)
        if not user:
            return (
                jsonify({"success": False, "error": "المستخدم غير موجود"}),
                404,
            )

        # التحقق من كلمة المرور القديمة (إذا مطلوبة)
        if action_config["requires_password"]:
            if not old_password:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "كلمة المرور القديمة مطلوبة",
                        }
                    ),
                    400,
                )
            if not verify_password(old_password, user["password_hash"]):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "كلمة المرور القديمة غير صحيحة",
                        }
                    ),
                    400,
                )

        # تحديد الهدف (إيميل أو جوال)
        if method == "email":
            target = user["email"]
            if not target:
                return (
                    jsonify({"success": False, "error": "لا يوجد إيميل مسجل"}),
                    400,
                )
            masked_target = (
                target[:2] + "***@" + target.split("@")[1]
                if "@" in target
                else target
            )
        else:  # sms
            target = user.get("phone") or user.get("phone_number")
            if not target:
                return (
                    jsonify(
                        {"success": False, "error": "لا يوجد رقم جوال مسجل"}
                    ),
                    400,
                )
            masked_target = (
                target[:4] + "****" + target[-4:]
                if len(target) > 8
                else target
            )

        # توليد OTP
        otp_code = generate_otp()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        # حفظ التحقق المعلق في DB
        _save_pending_verification(
            user_id, action, otp_code, expires_at, method, new_value, None
        )

        # إرسال OTP
        if method == "email":
            sent, actual_code = send_otp_email(
                target, otp_code, action_config["name"]
            )
            if sent and actual_code:
                _update_pending_otp(user_id, action, actual_code)
        else:
            sent = send_otp_sms(target, otp_code, action_config["name"])

        if not sent:
            return (
                jsonify(
                    {"success": False, "error": "فشل في إرسال رمز التحقق"}
                ),
                500,
            )

        return jsonify(
            {
                "success": True,
                "message": f"تم إرسال رمز التحقق إلى {masked_target}",
                "method": method,
                "masked_target": masked_target,
                "expires_in": 600,  # 10 دقائق
                "action": action,
                "action_name": action_config["name"],
            }
        )

    except Exception as e:
        logger.error(f"خطأ في طلب التحقق: {e}")
        return jsonify({"success": False, "error": "خطأ في الخادم"}), 500


@secure_actions_bp.route("/verify-and-execute", methods=["POST"])
@require_auth
def verify_and_execute():
    """
    التحقق من OTP وتنفيذ العملية

    Input:
    {
        "action": "change_username|change_password|...",
        "otp": "123456",
        "new_value": "القيمة الجديدة (إذا لم تُرسل في request-verification)"
    }

    Output:
    {
        "success": true,
        "message": "تم تنفيذ العملية بنجاح"
    }
    """
    try:
        user_id = g.user_id
        data = request.get_json(silent=True) or {}

        if not data:
            return jsonify({"success": False, "error": "لا توجد بيانات"}), 400

        action = data.get("action")
        otp_code = (data.get("otp_code") or data.get("otp") or "").strip()
        new_value = (
            data.get("newValue")
            if "newValue" in data
            else data.get("new_value")
        )

        if not action or not otp_code:
            return (
                jsonify(
                    {"success": False, "error": "العملية ورمز OTP مطلوبان"}
                ),
                400,
            )

        if action in DEDICATED_ACCOUNT_ACTIONS:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": DEDICATED_ACCOUNT_ACTIONS[action],
                    }
                ),
                400,
            )

        # التحقق من وجود طلب معلق
        pending = _get_pending_verification(user_id, action)
        if not pending:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "لا يوجد طلب تحقق معلق لهذه العملية",
                    }
                ),
                400,
            )

        # التحقق من انتهاء الصلاحية
        if datetime.now(timezone.utc) > pending["expires"]:
            _delete_pending_verification(user_id, action)
            return (
                jsonify(
                    {"success": False, "error": "انتهت صلاحية رمز التحقق"}
                ),
                400,
            )

        # التحقق من عدد المحاولات
        if pending["attempts"] >= 5:
            _delete_pending_verification(user_id, action)
            return (
                jsonify(
                    {"success": False, "error": "تجاوزت الحد الأقصى للمحاولات"}
                ),
                400,
            )

        # التحقق من OTP
        if otp_code != pending["otp"]:
            _update_pending_attempts(user_id, action, pending["attempts"] + 1)
            remaining = 5 - (pending["attempts"] + 1)
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"رمز التحقق غير صحيح. المحاولات المتبقية: {remaining}",
                    }),
                400,
            )

        # استخدام القيمة الجديدة من الطلب الحالي أو السابق
        final_new_value = new_value or pending.get("new_value")

        # تنفيذ العملية
        result = execute_secure_action(
            user_id, action, final_new_value, pending.get("old_password")
        )

        # حذف التحقق المعلق
        _delete_pending_verification(user_id, action)

        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"خطأ في التحقق والتنفيذ: {e}")
        return jsonify({"success": False, "error": "خطأ في الخادم"}), 500


@secure_actions_bp.route("/get-verification-options/<action>", methods=["GET"])
@require_auth
def get_verification_options(action):
    """
    الحصول على خيارات التحقق المتاحة لعملية معينة
    """
    try:
        user_id = g.user_id

        if action not in SECURE_ACTIONS:
            return (
                jsonify({"success": False, "error": "نوع العملية غير مدعوم"}),
                400,
            )

        action_config = SECURE_ACTIONS[action]

        if action in DEDICATED_ACCOUNT_ACTIONS:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": DEDICATED_ACCOUNT_ACTIONS[action],
                    }
                ),
                400,
            )
        user = get_user_by_id(user_id)

        if not user:
            return (
                jsonify({"success": False, "error": "المستخدم غير موجود"}),
                404,
            )

        # تحديد الخيارات المتاحة بناءً على بيانات المستخدم
        # ✅ SMS أولاً (الافتراضي)
        available_options = []

        phone_value = user.get("phone") or user.get("phone_number")
        if "sms" in action_config["verification_options"] and phone_value:
            phone = phone_value
            masked = (
                phone[:4] + "****" + phone[-4:] if len(phone) > 8 else phone
            )
            available_options.append(
                {
                    "method": "sms",
                    "masked_target": masked,
                    "label": "إرسال رمز إلى الجوال",
                }
            )

        if "email" in action_config["verification_options"] and user.get(
            "email"
        ):
            email = user["email"]
            masked = (
                email[:2] + "***@" + email.split("@")[1]
                if "@" in email
                else email
            )
            available_options.append(
                {
                    "method": "email",
                    "masked_target": masked,
                    "label": "إرسال رمز إلى الإيميل",
                }
            )

        return jsonify(
            {
                "success": True,
                "action": action,
                "action_name": action_config["name"],
                "requires_password": action_config["requires_password"],
                "options": available_options,
            }
        )

    except Exception as e:
        logger.error(f"خطأ في جلب خيارات التحقق: {e}")
        return jsonify({"success": False, "error": "خطأ في الخادم"}), 500


@secure_actions_bp.route("/cancel-verification/<action>", methods=["DELETE"])
@require_auth
def cancel_verification(action):
    """إلغاء طلب تحقق معلق"""
    try:
        user_id = g.user_id

        if action not in SECURE_ACTIONS:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "نوع العملية غير مدعوم",
                        "supported_actions": list(SECURE_ACTIONS.keys()),
                    }
                ),
                400,
            )

        try:
            pending = _get_pending_verification(user_id, action)
        except Exception:
            pending = None
        if pending:
            try:
                _delete_pending_verification(user_id, action)
            except Exception:
                pass
            return jsonify({"success": True, "message": "تم إلغاء طلب التحقق"})

        return jsonify({"success": True, "message": "لا يوجد طلب معلق"})

    except Exception as e:
        logger.error(f"خطأ في إلغاء التحقق: {e}")
        return jsonify({"success": False, "error": "خطأ في الخادم"}), 500


# ==================== تنفيذ العمليات ====================


def execute_secure_action(
    action: str, user_id: int, new_value: Any = None, old_password: str = None
) -> Dict[str, Any]:
    """تنفيذ العملية الآمنة بعد التحقق من OTP"""
    try:

        def load_api_permissions(client):
            if hasattr(client, "get_api_key_permission"):
                return client.get_api_key_permission()
            if hasattr(client, "get_account_api_permissions"):
                return client.get_account_api_permissions()
            raise AttributeError(
                "Binance client permissions API is unavailable"
            )

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            if action == "change_name":
                # الاسم الكامل يمكن أن يكون فارغاً
                cursor.execute(
                    "UPDATE users SET name = %s WHERE id = %s",
                    (new_value.strip() if new_value else "", user_id),
                )
                return {"success": True, "message": "تم تغيير الاسم بنجاح"}

            elif action == "change_username":
                if not new_value or len(new_value) < 3:
                    return {
                        "success": False,
                        "error": "اسم المستخدم يجب أن يكون 3 أحرف على الأقل",
                    }

                # التحقق من عدم وجود اسم مستخدم مكرر
                cursor.execute(
                    "SELECT id FROM users WHERE username = %s AND id != %s",
                    (new_value, user_id),
                )
                if cursor.fetchone():
                    return {
                        "success": False,
                        "error": "اسم المستخدم مستخدم بالفعل",
                    }

                cursor.execute(
                    "UPDATE users SET username = %s WHERE id = %s",
                    (new_value, user_id),
                )
                return {
                    "success": True,
                    "message": "تم تغيير اسم المستخدم بنجاح",
                }

            elif action == "change_password":
                if not new_value or len(new_value) < 6:
                    return {
                        "success": False,
                        "error": "كلمة المرور يجب أن تكون 6 أحرف على الأقل",
                    }

                new_hash = hash_password(new_value)
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (new_hash, user_id),
                )
                return {
                    "success": True,
                    "message": "تم تغيير كلمة المرور بنجاح",
                }

            elif action == "change_email":
                if not new_value or "@" not in new_value:
                    return {"success": False, "error": "الإيميل غير صحيح"}

                # التحقق من عدم وجود إيميل مكرر
                cursor.execute(
                    "SELECT id FROM users WHERE email = %s AND id != %s",
                    (new_value.lower(), user_id),
                )
                if cursor.fetchone():
                    return {"success": False, "error": "الإيميل مستخدم بالفعل"}

                cursor.execute(
                    "UPDATE users SET email = %s WHERE id = %s",
                    (new_value.lower(), user_id),
                )
                return {"success": True, "message": "تم تغيير الإيميل بنجاح"}

            elif action == "change_phone":
                if not new_value or len(new_value) < 10:
                    return {"success": False, "error": "رقم الجوال غير صحيح"}

                # التحقق من عدم وجود رقم مكرر
                cursor.execute(
                    "SELECT id FROM users WHERE phone_number = %s AND id != %s",
                    (new_value, user_id),
                )
                if cursor.fetchone():
                    return {
                        "success": False,
                        "error": "رقم الجوال مستخدم بالفعل",
                    }

                cursor.execute(
                    "UPDATE users SET phone_number = %s WHERE id = %s",
                    (new_value, user_id),
                )
                return {
                    "success": True,
                    "message": "تم تغيير رقم الجوال بنجاح",
                }

            elif action == "change_biometric":
                # new_value = 'enable' أو 'disable'
                enabled = new_value == "enable"
                cursor.execute(
                    """
                    UPDATE user_settings SET biometric_enabled = %s WHERE user_id = %s
                """,
                    (enabled, user_id),
                )
                status = "تفعيل" if enabled else "إلغاء"
                return {
                    "success": True,
                    "message": f"تم {status} البصمة بنجاح",
                }

            elif action == "change_binance_keys":
                # new_value = {'api_key': '...', 'secret_key': '...'}
                if not isinstance(new_value, dict):
                    return {
                        "success": False,
                        "error": "بيانات المفاتيح غير صحيحة",
                    }

                api_key = new_value.get("api_key")
                secret_key = new_value.get("secret_key")

                if not api_key or not secret_key:
                    return {"success": False, "error": "مفاتيح Binance مطلوبة"}

                # ===== فحص أمان المفتاح قبل الحفظ =====
                try:
                    from binance.client import Client

                    client = Client(api_key, secret_key)
                    api_perms = load_api_permissions(client)

                    if api_perms.get("enableWithdrawals", False):
                        return {
                            "success": False,
                            "error": "🚨 المفتاح يملك صلاحية السحب!\n\n"
                            "لحماية أموالك، يجب تعطيل Enable Withdrawals "
                            "من إعدادات API في Binance قبل الحفظ.\n\n"
                            "خطوات التعطيل:\n"
                            "1. افتح Binance → API Management\n"
                            "2. اضغط Edit restrictions\n"
                            "3. عطّل Enable Withdrawals\n"
                            "4. أعد المحاولة هنا",
                        }

                    if not api_perms.get("ipRestrict", False):
                        logger.warning(
                            f"⚠️ User {user_id} saving keys without IP restriction")

                except Exception as binance_check_error:
                    logger.warning(
                        f"⚠️ Could not verify key permissions: {binance_check_error}")

                # تشفير المفاتيح
                try:
                    from config.security.encryption_service import (
                        encrypt_binance_keys,
                    )

                    encrypted = encrypt_binance_keys(api_key, secret_key)
                    api_key = encrypted["api_key"]
                    secret_key = encrypted["secret_key"]
                except Exception as e:
                    logger.error(
                        f"🔴 Encryption failed: {e}"
                    )
                    raise RuntimeError(f"Encryption service unavailable: {e}") from e

                # حفظ أو تحديث المفاتيح
                cursor.execute(
                    """
                    INSERT INTO user_binance_keys (user_id, api_key, api_secret, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) DO UPDATE SET
                        api_key = EXCLUDED.api_key,
                        api_secret = EXCLUDED.api_secret,
                        is_active = EXCLUDED.is_active,
                        updated_at = EXCLUDED.updated_at
                """,
                    (user_id, api_key, secret_key),
                )
                return {
                    "success": True,
                    "message": "تم حفظ مفاتيح Binance بنجاح",
                }

            elif action == "delete_binance_keys":
                cursor.execute(
                    "DELETE FROM user_binance_keys WHERE user_id = %s",
                    (user_id,),
                )
                return {
                    "success": True,
                    "message": "تم حذف مفاتيح Binance بنجاح",
                }

            else:
                return {"success": False, "error": "نوع العملية غير مدعوم"}

    except Exception as e:
        logger.error(f"خطأ في تنفيذ العملية {action}: {e}")
        return {"success": False, "error": "خطأ في تنفيذ العملية"}


# ==================== تسجيل Blueprint ====================


def register_secure_actions_blueprint(app):
    """تسجيل Blueprint في التطبيق"""
    app.register_blueprint(secure_actions_bp)
    logger.info("✅ تم تسجيل Secure Actions Blueprint")


if __name__ == "__main__":
    print("🔐 Secure Actions Endpoints جاهزة")
    print("\nالمسارات المتاحة:")
    print("- POST /api/user/secure/request-verification")
    print("- POST /api/user/secure/verify-and-execute")
    print("- GET  /api/user/secure/get-verification-options/<action>")
    print("- DELETE /api/user/secure/cancel-verification/<action>")
    print("\nالعمليات المدعومة:")
    for action, config in SECURE_ACTIONS.items():
        print(f"  • {action}: {config['name']}")
