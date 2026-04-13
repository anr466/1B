#!/usr/bin/env python3
"""
نقاط النهاية لتسجيل FCM Tokens
"""

from backend.api.auth_middleware import require_auth
from backend.utils.unified_error_handler import log_error
from backend.infrastructure.db_access import get_db_manager
import sys
import os
from flask import Blueprint, request, jsonify, g

# إضافة مسار المشروع
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


# إنشاء Blueprint
fcm_bp = Blueprint("fcm", __name__, url_prefix="/notifications")

# تهيئة قاعدة البيانات
db_manager = get_db_manager()


@fcm_bp.route("/fcm-token", methods=["POST"])
@require_auth
def register_fcm_token():
    """تسجيل FCM Token للمستخدم"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "لا توجد بيانات"}), 400

        auth_user_id = getattr(g, "user_id", None) or getattr(
            g, "current_user_id", None
        )
        requested_user_id = data.get("user_id")
        # 🔒 Security: never allow client to write token for another user
        if requested_user_id and str(requested_user_id) != str(auth_user_id):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "غير مصرح بتسجيل التوكن لمستخدم آخر",
                    }
                ),
                403,
            )

        user_id = auth_user_id
        fcm_token = data.get("fcm_token", "").strip()
        platform = data.get("platform", "android").strip()

        if not user_id or not fcm_token:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "معرف المستخدم و FCM Token مطلوبان",
                    }
                ),
                400,
            )

        # تسجيل FCM Token
        success = register_user_fcm_token(user_id, fcm_token, platform)

        if success:
            return jsonify({"success": True, "message": "تم تسجيل FCM Token بنجاح"})
        else:
            return (
                jsonify({"success": False, "error": "فشل في تسجيل FCM Token"}),
                500,
            )

    except Exception as e:
        log_error(f"خطأ في تسجيل FCM Token: {str(e)}")
        return jsonify({"success": False, "error": "خطأ في الخادم"}), 500


def register_user_fcm_token(
    user_id: str, fcm_token: str, platform: str = "android"
) -> bool:
    """تسجيل FCM Token في قاعدة البيانات"""
    try:
        with db_manager.get_write_connection() as conn:
            # حذف التوكن القديم للمستخدم أو نفس التوكن المرتبط بحساب آخر
            # (نقل الجهاز بين حسابات يجب ألا يفشل بسبب UNIQUE constraint)
            conn.execute(
                """
                DELETE FROM fcm_tokens
                WHERE user_id = %s OR fcm_token = %s
            """,
                (user_id, fcm_token),
            )

            # إضافة التوكن الجديد
            conn.execute(
                """
                INSERT INTO fcm_tokens (user_id, fcm_token, platform, created_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            """,
                (user_id, fcm_token, platform),
            )

            conn.commit()

        log_error(f"تم تسجيل FCM Token للمستخدم {user_id}: {fcm_token[:20]}...")

        return True

    except Exception as e:
        log_error(f"خطأ في تسجيل FCM Token: {e}")
        return False


@fcm_bp.route("/fcm-token", methods=["DELETE"])
@require_auth
def unregister_fcm_token():
    """إلغاء تسجيل FCM Token للمستخدم"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "لا توجد بيانات"}), 400

        user_id = g.user_id
        fcm_token = data.get("fcm_token", "").strip()

        if not user_id:
            return (
                jsonify({"success": False, "error": "معرف المستخدم مطلوب"}),
                400,
            )

        # حذف FCM Token
        success = unregister_user_fcm_token(user_id, fcm_token)

        if success:
            return jsonify(
                {"success": True, "message": "تم إلغاء تسجيل FCM Token بنجاح"}
            )
        else:
            return (
                jsonify({"success": False, "error": "فشل في إلغاء تسجيل FCM Token"}),
                500,
            )

    except Exception as e:
        log_error(f"خطأ في إلغاء تسجيل FCM Token: {str(e)}")
        return jsonify({"success": False, "error": "خطأ في الخادم"}), 500


def unregister_user_fcm_token(user_id: str, fcm_token: str = None) -> bool:
    """إلغاء تسجيل FCM Token من قاعدة البيانات"""
    try:
        with db_manager.get_write_connection() as conn:
            if fcm_token:
                conn.execute(
                    """
                    DELETE FROM fcm_tokens
                    WHERE user_id = %s AND fcm_token = %s
                """,
                    (user_id, fcm_token),
                )
            else:
                conn.execute(
                    """
                    DELETE FROM fcm_tokens
                    WHERE user_id = %s
                """,
                    (user_id,),
                )

            conn.commit()

        log_error(f"تم إلغاء تسجيل FCM Token للمستخدم {user_id}")

        return True

    except Exception as e:
        log_error(f"خطأ في إلغاء تسجيل FCM Token: {e}")
        return False


if __name__ == "__main__":
    print("🔔 نقاط النهاية لـ FCM جاهزة")
    print("المسارات المتاحة:")
    print("- POST /api/user/fcm-token")
    print("- DELETE /api/user/fcm-token")
