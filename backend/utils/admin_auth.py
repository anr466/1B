"""
Admin Authentication Decorator
يوفر decorator للتحقق من صلاحيات الأدمن

✅ موحد مع auth_middleware كمصدر حقيقة واحد
⚠️ يستخدم _verify_jwt_and_set_g (بدون فحص URL user_id)
   لأن الأدمن يحتاج الوصول لمسارات تحتوي user_id لمستخدمين آخرين
"""

from functools import wraps
from flask import jsonify, g

from backend.api.auth_middleware import _verify_jwt_and_set_g


def require_admin(f):
    """
    Decorator للتحقق من أن المستخدم لديه صلاحيات admin.
    يستخدم نفس منطق التحقق من التوكن في auth_middleware
    لكن بدون فرض تطابق URL user_id (الأدمن يدير مستخدمين آخرين).
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        error_response = _verify_jwt_and_set_g()
        if error_response is not None:
            return error_response

        if getattr(g, "current_user_type", None) != "admin":
            return (
                jsonify({"success": False, "error": "Admin access required"}),
                403,
            )

        return f(*args, **kwargs)

    return decorated
