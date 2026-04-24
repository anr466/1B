"""
Admin Authentication Decorator
يوفر decorator للتحقق من صلاحيات الأدمن

✅ موحد مع auth_middleware كمصدر حقيقة واحد
⚠️ يستخدم _verify_jwt_and_set_g (بدون فحص URL user_id)
   لأن الأدمن يحتاج الوصول لمسارات تحتوي user_id لمستخدمين آخرين
"""

from functools import wraps
from flask import jsonify, g
import logging

from backend.api.auth_middleware import _verify_jwt_and_set_g
from backend.infrastructure.db_access import get_db_manager

logger = logging.getLogger(__name__)


def require_admin(f):
    """
    Decorator للتحقق من أن المستخدم لديه صلاحيات admin.
    يتحقق من JWT ثم يعتمد على قاعدة البيانات كمصدر حقيقة وحيد
    لمنع التوكنات القديمة من تجاوز إلغاء صلاحيات الأدمن.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        error_response = _verify_jwt_and_set_g()
        if error_response is not None:
            return error_response

        user_id = getattr(g, "current_user_id", None)
        if not user_id:
            return (
                jsonify({"success": False, "error": "Admin access required"}),
                403,
            )

        try:
            db = get_db_manager()
            with db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT user_type FROM users WHERE id = %s",
                        (user_id,),
                    )
                    row = cur.fetchone()
                    if not row or row[0] != "admin":
                        logger.warning(
                            "Admin access denied for user_id=%s (db_type=%s)",
                            user_id,
                            row[0] if row else "none",
                        )
                        return (
                            jsonify(
                                {"success": False, "error": "Admin access required"}
                            ),
                            403,
                        )
        except Exception as e:
            logger.error("DB verification failed for admin check: %s", e)
            return (
                jsonify({"success": False, "error": "Authentication error"}),
                500,
            )

        return f(*args, **kwargs)

    return decorated
