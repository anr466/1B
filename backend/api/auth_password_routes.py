#!/usr/bin/env python3
"""
Password & Account Change Routes — extracted from auth_endpoints.py (God Object split)
======================================================================================
Routes: forgot-password, cancel-otp, send-change-email-otp, verify-change-email-otp,
        send-change-password-otp, verify-change-password-otp, verify-reset-otp, reset-password
"""

import os
from flask import request, jsonify, g

from config.logging_config import get_logger
from backend.api.auth_middleware import require_auth

logger = get_logger(__name__)


def register_password_routes(bp, shared):
    """Register all password/account-change routes on the auth blueprint.

    Args:
        bp: Flask Blueprint (auth_bp)
        shared: dict with shared services
    """
    db_manager = shared["db_manager"]
    otp_service = shared["otp_service"]
    sms_service = shared["sms_service"]
    security_audit = shared["security_audit"]
    validate_email = shared["validate_email"]
    validate_password = shared["validate_password"]
    get_request_info = shared["get_request_info"]
    get_user_by_email = shared["get_user_by_email"]
    cleanup_verification_data = shared["cleanup_verification_data"]
    save_password_reset_request = shared["save_password_reset_request"]
    update_user_password = shared["update_user_password"]
    TOKEN_SYSTEM_AVAILABLE = shared["TOKEN_SYSTEM_AVAILABLE"]
    generate_tokens = shared.get("generate_tokens")
    prevent_concurrent_duplicates = shared["prevent_concurrent_duplicates"]
    require_idempotency = shared["require_idempotency"]

    try:
        from backend.utils.error_handler import log_error
    except ImportError:

        def log_error(message):
            pass

    @bp.route("/forgot-password", methods=["POST"])
    @prevent_concurrent_duplicates
    @require_idempotency("password_reset", require_user_id=False)
    def forgot_password():
        """طلب استعادة كلمة المرور"""
        try:
            data = request.get_json()

            if not data:
                return (
                    jsonify({"success": False, "error": "لا توجد بيانات"}),
                    400,
                )

            email = (data.get("email") or "").strip().lower()
            method = data.get("method", "sms")
            phone = (data.get("phone") or "").strip()
            logger.info(
                f"📧 Forgot password request for: {email}, method: {method}"
            )

            if not email:
                return (
                    jsonify({"success": False, "error": "الإيميل مطلوب"}),
                    400,
                )

            user = get_user_by_email(email)
            logger.info(
                f'🔍 User found: {user is not None} - User ID: {user.get("id") if user else "N/A"}'
            )

            if not user:
                logger.info(f"❌ User not found for email: {email}")
                return jsonify(
                    {
                        "success": True,
                        "message": "إذا كان الإيميل مسجل، ستصلك رسالة لاستعادة كلمة المرور",
                    }
                )

            if not phone and user.get("phone_number"):
                phone = user["phone_number"]

            if method == "sms" and not phone:
                method = "email"

            if security_audit and security_audit.is_rate_limited(
                email, "PASSWORD_RESET_REQUEST", max_attempts=3, minutes=15
            ):
                logger.warning(f"⚠️ Rate limited for email: {email}")
                return jsonify(
                    {
                        "success": True,
                        "message": "إذا كان الإيميل مسجل، ستصلك رسالة لاستعادة كلمة المرور",
                    }
                )

            logger.info(
                f"📤 Attempting to send OTP via {method} - otp_service: {otp_service is not None}"
            )
            if otp_service:
                logger.info(f"🔄 Calling send_email_otp for: {email}")
                success, otp_code = otp_service.send_email_otp(email)
                logger.info(f"📬 OTP send result - Success: {success}")

                if success:
                    if method == "sms" and phone and sms_service:
                        try:
                            message = f"رمز استعادة كلمة المرور: {otp_code}\nصالح لمدة 5 دقائق"
                            sms_service.send_sms(phone, message)
                            logger.info(
                                f"📱 تم إرسال OTP استعادة عبر SMS إلى {phone}"
                            )
                        except Exception as sms_err:
                            logger.warning(f"⚠️ فشل إرسال SMS: {sms_err}")
                            logger.info(
                                f"📱 [DEV] OTP sent via email fallback"
                            )

                    save_password_reset_request(user["id"], otp_code)

                    if security_audit:
                        ip, user_agent = get_request_info()
                        security_audit.log_action(
                            action="PASSWORD_RESET_REQUEST",
                            user_id=user["id"],
                            resource=email,
                            ip_address=ip,
                            user_agent=user_agent,
                            status="success",
                            details={"method": method},
                        )

                    masked_target = email
                    if method == "sms" and phone:
                        masked_target = (
                            phone[:4] + "****" + phone[-2:]
                            if len(phone) > 6
                            else phone
                        )
                    elif "@" in email:
                        masked_target = (
                            email[:2] + "***@" + email.split("@")[1]
                        )

                    return jsonify(
                        {
                            "success": True,
                            "message": f'تم إرسال رمز استعادة كلمة المرور إلى {
                                "هاتفك" if method == "sms" else "إيميلك"}',
                            "method": method,
                            "masked_target": masked_target,
                        }
                    )
                else:
                    return jsonify(
                        {
                            "success": True,
                            "message": "إذا كان الإيميل مسجل، ستصلك رسالة لاستعادة كلمة المرور",
                        }
                    )
            else:
                return jsonify(
                    {
                        "success": True,
                        "message": "إذا كان الإيميل مسجل، ستصلك رسالة لاستعادة كلمة المرور",
                    }
                )

        except Exception as e:
            log_error(f"خطأ في طلب استعادة كلمة المرور: {str(e)}")
            return jsonify({"success": False, "error": "خطأ في الخادم"}), 500

    @bp.route("/cancel-otp", methods=["POST"])
    def cancel_otp():
        """✅ إلغاء OTP نشط - يسمح للمستخدم بإلغاء العملية"""
        try:
            data = request.get_json(silent=True) or {}
            email = (data.get("email") or "").strip().lower()
            purpose = data.get("purpose", "password_reset")

            if not email:
                return (
                    jsonify({"success": False, "error": "الإيميل مطلوب"}),
                    400,
                )

            if otp_service:
                cancelled = otp_service.cancel_otp(email, purpose)

                if cancelled:
                    return jsonify(
                        {
                            "success": True,
                            "message": "تم إلغاء رمز التحقق بنجاح",
                        }
                    )
                else:
                    return jsonify(
                        {
                            "success": True,
                            "message": "لا يوجد رمز تحقق نشط لإلغائه",
                        }
                    )
            else:
                return (
                    jsonify({"success": False, "error": "خدمة OTP غير متاحة"}),
                    500,
                )

        except Exception as e:
            logger.error(f"خطأ في إلغاء OTP: {e}")
            return jsonify({"success": False, "error": "خطأ في الخادم"}), 500

    @bp.route("/send-change-email-otp", methods=["POST"])
    @require_auth
    def send_change_email_otp():
        """إرسال OTP لتغيير الإيميل"""
        try:
            data = request.get_json(silent=True) or {}
            new_email = (
                (data.get("new_email") or data.get("newEmail") or "")
                .strip()
                .lower()
            )
            requested_user_id = data.get("user_id") or data.get("userId")
            user_id = g.user_id

            if not new_email:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "الإيميل الجديد ومعرف المستخدم مطلوبان",
                        }
                    ),
                    400,
                )

            if requested_user_id is not None and str(requested_user_id) != str(
                user_id
            ):
                return (
                    jsonify({"success": False, "error": "لا توجد صلاحية"}),
                    403,
                )

            if not validate_email(new_email):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "صيغة الإيميل الجديد غير صحيحة",
                        }
                    ),
                    400,
                )

            try:
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id FROM users WHERE email = %s AND id != %s",
                        (new_email, user_id),
                    )
                    if cursor.fetchone():
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": "الإيميل الجديد مستخدم بالفعل",
                                }
                            ),
                            409,
                        )
            except Exception as e:
                logger.error(f"خطأ في فحص الإيميل: {e}")
                return (
                    jsonify({"success": False, "error": "خطأ في التحقق"}),
                    500,
                )

            if otp_service:
                success, otp_code = otp_service.send_email_otp(
                    new_email, purpose="change_email"
                )
                if success:
                    logger.info(
                        f"✅ تم إرسال OTP لتغيير الإيميل إلى: {new_email}"
                    )
                    return jsonify({"success": True,
                                    "message": "تم إرسال رمز التحقق إلى الإيميل الجديد",
                                    "expires_in": 600,
                                    })
                else:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "فشل في إرسال رمز التحقق",
                            }
                        ),
                        500,
                    )
            else:
                return (
                    jsonify({"success": False, "error": "خدمة OTP غير متاحة"}),
                    500,
                )

        except Exception as e:
            logger.error(f"خطأ في إرسال OTP لتغيير الإيميل: {e}")
            return jsonify({"success": False, "error": "خطأ في الخادم"}), 500

    @bp.route("/verify-change-email-otp", methods=["POST"])
    @require_auth
    def verify_change_email_otp():
        """التحقق من OTP وتغيير الإيميل"""
        try:
            data = request.get_json(silent=True) or {}
            new_email = (
                (data.get("new_email") or data.get("newEmail") or "")
                .strip()
                .lower()
            )
            otp_code = (data.get("otp") or data.get("otp_code") or "").strip()
            requested_user_id = data.get("user_id") or data.get("userId")
            user_id = g.user_id

            if not new_email or not otp_code:
                return (
                    jsonify(
                        {"success": False, "error": "جميع البيانات مطلوبة"}
                    ),
                    400,
                )

            if requested_user_id is not None and str(requested_user_id) != str(
                user_id
            ):
                return (
                    jsonify({"success": False, "error": "لا توجد صلاحية"}),
                    403,
                )

            if otp_service:
                verified, result = otp_service.verify_email_otp(
                    new_email,
                    otp_code,
                    purpose="change_email",
                )

                if verified:
                    try:
                        with db_manager.get_write_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE users SET email = %s, email_verified = TRUE WHERE id = %s",
                                (new_email, user_id),
                            )
                            logger.info(
                                f"✅ تم تغيير الإيميل للمستخدم {user_id}"
                            )
                            return jsonify(
                                {
                                    "success": True,
                                    "message": "تم تغيير الإيميل بنجاح",
                                    "email": new_email,
                                }
                            )
                    except Exception as e:
                        logger.error(f"خطأ في تحديث الإيميل: {e}")
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": "فشل في تحديث الإيميل",
                                }
                            ),
                            500,
                        )
                else:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": result.get(
                                    "error", "رمز التحقق غير صحيح"
                                ),
                                "remaining_attempts": result.get(
                                    "remaining_attempts"
                                ),
                            }
                        ),
                        400,
                    )
            else:
                return (
                    jsonify({"success": False, "error": "خدمة OTP غير متاحة"}),
                    500,
                )

        except Exception as e:
            logger.error(f"خطأ في التحقق من OTP لتغيير الإيميل: {e}")
            return jsonify({"success": False, "error": "خطأ في الخادم"}), 500

    @bp.route("/send-change-password-otp", methods=["POST"])
    @require_auth
    def send_change_password_otp():
        """إرسال OTP لتغيير كلمة المرور"""
        try:
            data = request.get_json(silent=True) or {}
            old_password = data.get("old_password") or data.get("oldPassword")
            user_id = g.user_id

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

            try:
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, email, password_hash FROM users WHERE id = %s", (user_id,), )
                    user = cursor.fetchone()

                    if not user:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": "المستخدم غير موجود",
                                }
                            ),
                            404,
                        )

                    email = (user["email"] or "").strip().lower()
                    if not email:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": "لا يوجد بريد إلكتروني موثق",
                                }
                            ),
                            400,
                        )

                    from backend.utils.password_utils import (
                        verify_password as _verify_pw,
                    )

                    if not _verify_pw(old_password, user["password_hash"]):
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": "كلمة المرور القديمة غير صحيحة",
                                }
                            ),
                            401,
                        )
            except Exception as e:
                logger.error(f"خطأ في التحقق من كلمة المرور: {e}")
                return (
                    jsonify({"success": False, "error": "خطأ في التحقق"}),
                    500,
                )

            if otp_service:
                success, otp_code = otp_service.send_email_otp(
                    email, purpose="change_password"
                )
                if success:
                    logger.info(
                        f"✅ تم إرسال OTP لتغيير كلمة المرور إلى: {email}"
                    )
                    return jsonify(
                        {
                            "success": True,
                            "message": "تم إرسال رمز التحقق إلى إيميلك",
                            "expires_in": 600,
                        }
                    )
                else:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "فشل في إرسال رمز التحقق",
                            }
                        ),
                        500,
                    )
            else:
                return (
                    jsonify({"success": False, "error": "خدمة OTP غير متاحة"}),
                    500,
                )

        except Exception as e:
            logger.error(f"خطأ في إرسال OTP لتغيير كلمة المرور: {e}")
            return jsonify({"success": False, "error": "خطأ في الخادم"}), 500

    @bp.route("/verify-change-password-otp", methods=["POST"])
    @require_auth
    def verify_change_password_otp():
        """التحقق من OTP وتغيير كلمة المرور"""
        try:
            data = request.get_json(silent=True) or {}
            otp_code = (data.get("otp") or data.get("otp_code") or "").strip()
            new_password = data.get("new_password") or data.get("newPassword")
            user_id = g.user_id

            if not otp_code or not new_password:
                return (
                    jsonify(
                        {"success": False, "error": "جميع البيانات مطلوبة"}
                    ),
                    400,
                )

            if not validate_password(new_password):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "كلمة المرور الجديدة يجب أن تحتوي على 8 أحرف على الأقل، وحرف كبير وصغير ورقم",
                        }),
                    400,
                )

            try:
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT email FROM users WHERE id = %s", (user_id,)
                    )
                    user = cursor.fetchone()
                    if not user:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": "المستخدم غير موجود",
                                }
                            ),
                            404,
                        )
                    email = (user["email"] or "").strip().lower()
                    if not email:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": "لا يوجد بريد إلكتروني موثق",
                                }
                            ),
                            400,
                        )
            except Exception as e:
                logger.error(f"خطأ في جلب المستخدم لتغيير كلمة المرور: {e}")
                return (
                    jsonify({"success": False, "error": "خطأ في التحقق"}),
                    500,
                )

            if otp_service:
                verified, result = otp_service.verify_email_otp(
                    email,
                    otp_code,
                    purpose="change_password",
                )

                if verified:
                    try:
                        from backend.utils.password_utils import (
                            hash_password as _hash_pw,
                        )

                        password_hash = _hash_pw(new_password)

                        with db_manager.get_write_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE users SET password_hash = %s WHERE id = %s",
                                (password_hash, user_id),
                            )
                            logger.info(
                                f"✅ تم تغيير كلمة المرور للمستخدم {user_id}"
                            )
                            return jsonify(
                                {
                                    "success": True,
                                    "message": "تم تغيير كلمة المرور بنجاح",
                                }
                            )
                    except Exception as e:
                        logger.error(f"خطأ في تحديث كلمة المرور: {e}")
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": "فشل في تحديث كلمة المرور",
                                }
                            ),
                            500,
                        )
                else:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": result.get(
                                    "error", "رمز التحقق غير صحيح"
                                ),
                                "remaining_attempts": result.get(
                                    "remaining_attempts"
                                ),
                            }
                        ),
                        400,
                    )
            else:
                return (
                    jsonify({"success": False, "error": "خدمة OTP غير متاحة"}),
                    500,
                )

        except Exception as e:
            logger.error(f"خطأ في التحقق من OTP لتغيير كلمة المرور: {e}")
            return jsonify({"success": False, "error": "خطأ في الخادم"}), 500

    @bp.route("/verify-reset-otp", methods=["POST"])
    def verify_reset_otp():
        """التحقق من OTP فقط وإصدار Reset Token - خطوة 2 من تدفق Forget Password"""
        try:
            data = request.get_json()

            if not data:
                return (
                    jsonify({"success": False, "error": "لا توجد بيانات"}),
                    400,
                )

            email = data.get("email", "").strip().lower()
            otp_code = data.get("otp", "").strip()

            if not email or not otp_code:
                return (
                    jsonify(
                        {"success": False, "error": "الإيميل ورمز OTP مطلوبان"}
                    ),
                    400,
                )

            if otp_service:
                verified, result = otp_service.verify_email_otp(
                    email, otp_code
                )

                if verified:
                    user = get_user_by_email(email)
                    if not user:
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": "المستخدم غير موجود",
                                }
                            ),
                            404,
                        )

                    import jwt
                    from datetime import datetime, timedelta

                    reset_token_payload = {
                        "user_id": user["id"],
                        "email": email,
                        "purpose": "password_reset",
                        "exp": datetime.utcnow() + timedelta(minutes=10),
                        "iat": datetime.utcnow(),
                    }

                    secret_key = os.getenv(
                        "JWT_SECRET_KEY", "trading_ai_bot_secret_key_2026"
                    )
                    reset_token = jwt.encode(
                        reset_token_payload, secret_key, algorithm="HS256"
                    )

                    cleanup_verification_data(email)

                    if security_audit:
                        ip, user_agent = get_request_info()
                        security_audit.log_action(
                            action="RESET_OTP_VERIFIED",
                            user_id=user["id"],
                            resource=email,
                            ip_address=ip,
                            user_agent=user_agent,
                            status="success",
                        )

                    return jsonify(
                        {
                            "success": True,
                            "message": "تم التحقق بنجاح",
                            "reset_token": reset_token,
                            "expires_in": 900,
                        }
                    )
                else:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": result.get(
                                    "error", "رمز OTP غير صحيح"
                                ),
                                "remaining_attempts": result.get(
                                    "remaining_attempts", 0
                                ),
                            }
                        ),
                        400,
                    )
            else:
                return (
                    jsonify(
                        {"success": False, "error": "خدمة التحقق غير متاحة"}
                    ),
                    503,
                )

        except Exception as e:
            log_error(f"خطأ في التحقق من OTP: {str(e)}")
            return jsonify({"success": False, "error": "خطأ في الخادم"}), 500

    @bp.route("/reset-password", methods=["POST"])
    def reset_password():
        """إعادة تعيين كلمة المرور باستخدام Reset Token - خطوة 3 من تدفق Forget Password"""
        try:
            data = request.get_json()

            if not data:
                return (
                    jsonify({"success": False, "error": "لا توجد بيانات"}),
                    400,
                )

            reset_token = (
                data.get("reset_token") or data.get("resetToken") or ""
            ).strip()
            new_password = (
                data.get("new_password") or data.get("newPassword") or ""
            )

            if not reset_token or not new_password:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Reset Token وكلمة المرور الجديدة مطلوبان",
                        }
                    ),
                    400,
                )

            if not validate_password(new_password):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "كلمة المرور يجب أن تكون 8 أحرف على الأقل وتحتوي على حروف كبيرة وصغيرة وأرقام",
                        }),
                    400,
                )

            try:
                import jwt

                secret_key = os.getenv(
                    "JWT_SECRET_KEY", "trading_ai_bot_secret_key_2026"
                )

                payload = jwt.decode(
                    reset_token, secret_key, algorithms=["HS256"]
                )

                if payload.get("purpose") != "password_reset":
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "Token غير صالح لهذه العملية",
                            }
                        ),
                        400,
                    )

                user_id = payload.get("user_id")
                email = payload.get("email")

                if not user_id or not email:
                    return (
                        jsonify({"success": False, "error": "Token غير صحيح"}),
                        400,
                    )

                user = get_user_by_email(email)
                if not user or user["id"] != user_id:
                    return (
                        jsonify(
                            {"success": False, "error": "المستخدم غير موجود"}
                        ),
                        404,
                    )

                from backend.utils.password_utils import (
                    hash_password as _hash_pw,
                )

                new_password_hash = _hash_pw(new_password)
                update_user_password(user_id, new_password_hash)

                try:
                    db_manager.execute_query(
                        "DELETE FROM user_sessions WHERE user_id = %s",
                        (user_id,),
                    )
                except Exception as e:
                    logger.debug(f"فشل حذف الجلسات القديمة: {e}")

                if TOKEN_SYSTEM_AVAILABLE and generate_tokens:
                    try:
                        auth_tokens = generate_tokens(user_id)
                        access_token = auth_tokens.get("access_token")
                        refresh_token = auth_tokens.get("refresh_token")
                    except Exception as e:
                        logger.warning(f"⚠️ فشل إنشاء JWT tokens: {e}")
                        access_token = None
                        refresh_token = None
                else:
                    access_token = None
                    refresh_token = None

                if security_audit:
                    ip, user_agent = get_request_info()
                    security_audit.log_action(
                        action="PASSWORD_RESET_SUCCESS",
                        user_id=user_id,
                        resource=email,
                        ip_address=ip,
                        user_agent=user_agent,
                        status="success",
                    )

                response_data = {
                    "success": True,
                    "message": "تم تغيير كلمة المرور بنجاح",
                    "email": email,
                }

                if access_token:
                    response_data["access_token"] = access_token
                    response_data["accessToken"] = access_token
                if refresh_token:
                    response_data["refresh_token"] = refresh_token
                    response_data["refreshToken"] = refresh_token

                return jsonify(response_data)

            except Exception as jwt_import_err:
                import jwt as jwt_mod

                if isinstance(jwt_import_err, jwt_mod.ExpiredSignatureError):
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "انتهت صلاحية الرمز. يرجى طلب رمز جديد",
                            }
                        ),
                        400,
                    )
                elif isinstance(jwt_import_err, jwt_mod.InvalidTokenError):
                    return (
                        jsonify({"success": False, "error": "رمز غير صحيح"}),
                        400,
                    )
                else:
                    log_error(f"خطأ في التحقق من Reset Token: {
                        str(jwt_import_err)}")
                    return (
                        jsonify({"success": False, "error": "رمز غير صالح"}),
                        400,
                    )

        except Exception as e:
            log_error(f"خطأ في إعادة تعيين كلمة المرور: {str(e)}")
            return jsonify({"success": False, "error": "خطأ في الخادم"}), 500
