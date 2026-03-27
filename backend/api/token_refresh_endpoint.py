"""
Token Refresh Endpoint
يوفر endpoint لتحديث JWT tokens بدون إعادة تسجيل دخول
"""

from backend.infrastructure.db_access import get_db_manager
from dotenv import load_dotenv
import os
import jwt
import time
import hashlib
from datetime import datetime
from flask import Blueprint, request, jsonify
from functools import wraps

# إنشاء Blueprint
token_refresh_bp = Blueprint("token_refresh", __name__)

# إعدادات JWT (يجب أن تتطابق مع auth_endpoints.py)
# ✅ FIX: تحميل dotenv أولاً لضمان وجود المتغيرات

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRY = 86400  # 24 ساعة (تم تمديده من ساعة واحدة)
REFRESH_TOKEN_EXPIRY = 2592000  # 30 يوم

# ✅ FIX: متغير للتحقق من توفر النظام
TOKEN_SYSTEM_AVAILABLE = bool(JWT_SECRET_KEY)

# ─── DB-backed token blocklist ──────────────────────────────────────────
try:
    _db = get_db_manager()
    with _db.get_write_connection() as _conn:
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS revoked_tokens (
                token_hash  TEXT        PRIMARY KEY,
                user_id     BIGINT,
                revoked_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                expires_at  TIMESTAMPTZ
            )
        """)
    BLOCKLIST_AVAILABLE = True
except Exception:
    _db = None
    BLOCKLIST_AVAILABLE = False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def revoke_token(
    token: str, user_id: int = None, expires_at: datetime = None
) -> bool:
    """Add token to DB blocklist atomically. Returns True on success."""
    if not BLOCKLIST_AVAILABLE or not _db:
        return False
    try:
        token_hash = _token_hash(token)
        with _db.get_write_connection() as conn:
            conn.execute(
                """
                INSERT INTO revoked_tokens (token_hash, user_id, expires_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (token_hash) DO NOTHING
                """,
                (token_hash, user_id, expires_at),
            )
        return True
    except Exception:
        return False


def is_token_revoked(token: str) -> bool:
    """Return True if token is in the DB blocklist."""
    if not BLOCKLIST_AVAILABLE or not _db:
        return False
    try:
        token_hash = _token_hash(token)
        result = _db.execute_query(
            "SELECT 1 FROM revoked_tokens WHERE token_hash = %s",
            (token_hash,),
        )
        return bool(result)
    except Exception:
        return False


def verify_token_with_lock(token: str, token_type: str = "access") -> dict:
    """
    التحقق من صحة Token مع Atomic Blocklist Check

    Uses advisory lock to prevent race condition between check and use.
    This is the RECOMMENDED function for critical operations.
    """
    if not BLOCKLIST_AVAILABLE or not _db:
        return verify_token(token, token_type)

    token_hash = _token_hash(token)

    try:
        with _db.get_write_connection() as conn:
            conn.execute(
                "SELECT pg_advisory_xact_lock(%s)",
                (abs(hash(token_hash)) % (2**31),),
            )

            result = conn.execute(
                "SELECT 1 FROM revoked_tokens WHERE token_hash = %s",
                (token_hash,),
            ).fetchone()

            if result:
                raise jwt.InvalidTokenError("Token has been revoked")

        return verify_token(token, token_type)

    except jwt.InvalidTokenError:
        raise
    except Exception:
        return verify_token(token, token_type)


def generate_tokens(
    user_id: int, username: str = None, user_type: str = "user"
) -> dict:
    """
    إنشاء access token و refresh token

    Returns:
        {
            'access_token': str,
            'refresh_token': str,
            'expires_in': int
        }
    """
    if not JWT_SECRET_KEY:
        return None

    now = time.time()

    # Access Token (قصير المدى)
    access_payload = {
        "user_id": user_id,
        "username": username,
        "user_type": user_type,
        "type": "access",
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRY,
    }
    access_token = jwt.encode(
        access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
    )

    # Refresh Token (طويل المدى)
    refresh_payload = {
        "user_id": user_id,
        "username": username,
        "type": "refresh",
        "iat": now,
        "exp": now + REFRESH_TOKEN_EXPIRY,
    }
    refresh_token = jwt.encode(
        refresh_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TOKEN_EXPIRY,
    }


def verify_token(token: str, token_type: str = "access") -> dict:
    """
    التحقق من صحة Token

    Args:
        token: JWT token
        token_type: 'access' أو 'refresh'

    Returns:
        decoded payload أو يرفع jwt.InvalidTokenError
    """
    # فحص Blocklist قبل فك التشفير
    if is_token_revoked(token):
        raise jwt.InvalidTokenError("Token has been revoked")

    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # فحص نوع Token
        if payload.get("type") != token_type:
            raise jwt.InvalidTokenError(f"Expected {token_type} token")

        return payload

    except jwt.ExpiredSignatureError as e:
        raise jwt.InvalidTokenError(f"Token expired")
    except jwt.InvalidTokenError as e:
        raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")


def require_refresh_token(func):
    """
    Decorator للتحقق من Refresh Token
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # الحصول على Token من Header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Missing or invalid authorization header",
                    }
                ),
                401,
            )

        token = auth_header.split(" ")[1]

        try:
            # التحقق من Refresh Token
            payload = verify_token(token, token_type="refresh")

            # إضافة البيانات للـ request
            request.token_payload = payload

            return func(*args, **kwargs)

        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 401

    return wrapper


@token_refresh_bp.route("/refresh-token", methods=["POST"])
@require_refresh_token
def refresh_token():
    """
    تحديث Access Token باستخدام Refresh Token

    Request Headers:
        Authorization: Bearer <refresh_token>

    Response:
        {
            'success': True,
            'access_token': str,
            'expires_in': int,
            'message': str
        }
    """
    try:
        # الحصول على بيانات المستخدم من Refresh Token
        payload = request.token_payload
        user_id = payload["user_id"]
        username = payload["username"]

        # إنشاء Access Token جديد
        now = time.time()
        access_payload = {
            "user_id": user_id,
            "username": username,
            "user_type": payload.get("user_type", "user"),  # من DB إذا متوفر
            "type": "access",
            "iat": now,
            "exp": now + ACCESS_TOKEN_EXPIRY,
        }

        new_access_token = jwt.encode(
            access_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM
        )

        return (
            jsonify(
                {
                    "success": True,
                    "access_token": new_access_token,
                    "expires_in": ACCESS_TOKEN_EXPIRY,
                    "message": "تم تحديث الـ token بنجاح",
                }
            ),
            200,
        )

    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"❌ خطأ في تحديث Token: {str(e)}")
        return (
            jsonify({"success": False, "message": "فشل في تحديث الـ token"}),
            500,
        )


@token_refresh_bp.route("/validate-token", methods=["GET"])
def validate_token_endpoint():
    """
    التحقق من صحة Token

    Request Headers:
        Authorization: Bearer <access_token>

    Response:
        {
            'success': True,
            'valid': bool,
            'user_id': int,
            'expires_at': int
        }
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return (
                jsonify(
                    {
                        "success": False,
                        "valid": False,
                        "message": "Missing authorization header",
                    }
                ),
                401,
            )

        token = auth_header.split(" ")[1]

        try:
            payload = verify_token(token, token_type="access")

            return (
                jsonify(
                    {
                        "success": True,
                        "valid": True,
                        "user_id": payload["user_id"],
                        "username": payload["username"],
                        "expires_at": int(payload["exp"]),
                    }
                ),
                200,
            )

        except Exception as e:
            return (
                jsonify({"success": False, "valid": False, "message": str(e)}),
                401,
            )

    except Exception:
        return (
            jsonify(
                {"success": False, "message": "خطأ في التحقق من الـ token"}
            ),
            500,
        )


@token_refresh_bp.route("/logout", methods=["POST"])
def logout():
    """
    تسجيل خروج (في نظام stateless، هذا informational فقط)

    في المستقبل يمكن إضافة token blacklist

    Response:
        {
            'success': True,
            'message': str
        }
    """
    # في نظام JWT stateless، العميل يحذف الـ token
    # يمكن إضافة token blacklist هنا إذا لزم الأمر

    return jsonify({"success": True, "message": "تم تسجيل الخروج بنجاح"}), 200


# دالة مساعدة لتحديث login endpoint الحالي
def update_login_response_with_refresh_token(
    user_id: int, username: str, user_type: str
) -> dict:
    """
    دالة مساعدة لتحديث login response ليشمل refresh token

    يمكن استخدامها في auth_endpoints.py:

    from backend.api.token_refresh_endpoint import update_login_response_with_refresh_token

    # في login endpoint
    tokens = update_login_response_with_refresh_token(user['id'], user['username'], user['user_type'])
    return jsonify({
        'success': True,
        'user': user,
        'token': tokens['access_token'],
        'refresh_token': tokens['refresh_token'],  # جديد
        'expires_in': tokens['expires_in']  # جديد
    })
    """
    return generate_tokens(user_id, username, user_type)
