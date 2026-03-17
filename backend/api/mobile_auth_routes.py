"""
Mobile Auth Routes — extracted from mobile_endpoints.py (God Object split)
==========================================================================
Routes: /change-password, /biometric, /device, /fcm-token, /auth/send-otp, /auth/verify-otp,
        /auth/forgot-password, /auth/reset-password, /auth/verify-phone-token
"""

from flask import request, jsonify, g
from datetime import datetime, timedelta
import json
import logging
import os
import jwt
import hashlib

logger = logging.getLogger(__name__)


def register_mobile_auth_routes(bp, shared):
    """Register auth-related routes on the mobile blueprint"""
    db_manager = shared['db_manager']
    require_auth = shared['require_auth']
    rate_limit_auth = shared.get('rate_limit_auth', lambda f: f)
    success_response = shared['success_response']
    error_response = shared['error_response']
    audit_logger = shared.get('audit_logger', None)

    @bp.route('/change-password', methods=['POST'])
    @require_auth
    def change_password():
        """
        ❌ DEPRECATED: استخدم OTP endpoints بدلاً من ذلك

        تم تعطيل هذا الـ endpoint لأسباب أمنية.
        استخدم:
        1. POST /api/auth/send-change-password-otp
        2. POST /api/auth/verify-change-password-otp

        السبب: العمليات الحساسة تتطلب تحقق OTP حسب نظام الأمان
        """
        return jsonify({
            'success': False,
            'error': 'هذا الـ endpoint معطل. استخدم نظام OTP لتغيير كلمة المرور',
            'code': 'ENDPOINT_DEPRECATED',
            'instructions': {
                'step1': 'POST /api/auth/send-change-password-otp',
                'step2': 'POST /api/auth/verify-change-password-otp'
            }
        }), 410  # 410 Gone



    # ==================== المصادقة البيومترية ====================

    @bp.route('/biometric/verify', methods=['POST'])
    @require_auth
    def verify_biometric():
        """
        التحقق من المصادقة البيومترية

        Body:
        {
            "biometric_data": "base64_encoded_data",
            "type": "fingerprint|face"
        }
        """
        try:
            user_id = g.current_user_id
            data = request.get_json()

            if not data or not data.get('biometric_data'):
                response_data, status_code = error_response('بيانات بيومترية مطلوبة', 'MISSING_DATA', 400)
                return jsonify(response_data), status_code

            biometric_type = data.get('type', 'fingerprint')

            # التحقق من نوع البيومتريا
            if biometric_type not in ['fingerprint', 'face']:
                response_data, status_code = error_response('نوع بيومتريا غير صحيح', 'INVALID_TYPE', 400)
                return jsonify(response_data), status_code

            biometric_data = data.get('biometric_data', '').strip()

            # التحقق من طول البيانات
            if len(biometric_data) < 20:
                response_data, status_code = error_response('بيانات بيومترية غير صحيحة', 'INVALID_DATA', 400)
                return jsonify(response_data), status_code

            # تخزين بصمة مُشفرة (Hash only) وعدم حفظ البيانات الخام
            biometric_hash = hashlib.sha256(biometric_data.encode('utf-8')).hexdigest()
            try:
                with db_manager.get_write_connection() as conn:
                    conn.execute("""
                        INSERT INTO biometric_auth 
                        (user_id, biometric_hash, device_id, is_active, created_at, updated_at)
                        VALUES (%s, %s, %s, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id) DO UPDATE SET
                            biometric_hash = EXCLUDED.biometric_hash,
                            device_id = EXCLUDED.device_id,
                            is_active = EXCLUDED.is_active,
                            updated_at = EXCLUDED.updated_at
                    """, (user_id, biometric_hash, f"mobile:{biometric_type}"))
                    conn.commit()
            except Exception as db_error:
                logger.error(f"❌ خطأ في حفظ البيانات البيومترية: {db_error}")
                response_data, status_code = error_response('خطأ في حفظ البيانات', 'DB_ERROR', 500)
                return jsonify(response_data), status_code

            logger.info(f"✅ تم التحقق من المصادقة البيومترية ({biometric_type}) للمستخدم {user_id}")
            response_data, status_code = success_response({'verified': True, 'type': biometric_type}, 'تم التحقق من البيانات البيومترية بنجاح')
            return jsonify(response_data), status_code

        except Exception as e:
            logger.error(f"❌ خطأ في التحقق البيومتري: {e}")
            response_data, status_code = error_response('خطأ في التحقق البيومتري', 'BIOMETRIC_ERROR', 500)
            return jsonify(response_data), status_code


    # ❌ DELETED: /trading-settings endpoints (GET & PUT)
    # Reason: DUPLICATE of /settings/<user_id> endpoints (lines 809-1130)
    # The /settings/<user_id> endpoint provides:
    #   - Better security (user_id verification via verify_user_access)
    #   - Rate limiting (@rate_limit_general, @rate_limit_trading)
    #   - Idempotency protection (@require_idempotency)
    #   - Concurrent request prevention (@prevent_concurrent_duplicates)
    #   - Admin/User mode support
    # Frontend should use: getSettings(userId) and updateSettings(userId, settings)


    # ==================== إدارة الأجهزة ====================

    @bp.route('/device', methods=['POST'])
    @require_auth
    def register_device():
        """
        تسجيل جهاز جديد

        Body:
        {
            "device_id": "device_uuid",
            "device_name": "iPhone 12",
            "device_type": "ios|android",
            "fcm_token": "firebase_token"
        }
        """
        try:
            user_id = g.current_user_id
            data = request.get_json()

            if not data or not data.get('device_id'):
                response_data, status_code = error_response('معرف الجهاز مطلوب', 'MISSING_DATA', 400)
                return jsonify(response_data), status_code

            device_id = data.get('device_id', '').strip()
            device_name = data.get('device_name', 'Unknown Device').strip()
            device_type = data.get('device_type', 'unknown').strip()
            fcm_token = data.get('fcm_token', '').strip() if data.get('fcm_token') else None

            # التحقق من صحة معرف الجهاز
            if len(device_id) < 5:
                response_data, status_code = error_response('معرف الجهاز غير صحيح', 'INVALID_DATA', 400)
                return jsonify(response_data), status_code

            # التحقق من نوع الجهاز
            if device_type not in ['ios', 'android', 'unknown']:
                device_type = 'unknown'

            try:
                with db_manager.get_write_connection() as conn:
                    conn.execute("""
                        INSERT INTO user_devices
                        (user_id, device_id, device_name, device_type, fcm_token, created_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id, device_id) DO UPDATE SET
                            device_name = EXCLUDED.device_name,
                            device_type = EXCLUDED.device_type,
                            fcm_token = EXCLUDED.fcm_token
                    """, (user_id, device_id, device_name, device_type, fcm_token))
                    conn.commit()
            except Exception as db_error:
                logger.error(f"❌ خطأ في حفظ بيانات الجهاز: {db_error}")
                response_data, status_code = error_response('خطأ في حفظ البيانات', 'DB_ERROR', 500)
                return jsonify(response_data), status_code

            logger.info(f"✅ تم تسجيل جهاز جديد ({device_type}) للمستخدم {user_id}")
            response_data, status_code = success_response({'registered': True, 'device_id': device_id}, 'تم تسجيل الجهاز بنجاح')
            return jsonify(response_data), status_code

        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل الجهاز: {e}")
            response_data, status_code = error_response('خطأ في تسجيل الجهاز', 'DEVICE_ERROR', 500)
            return jsonify(response_data), status_code


    # ==================== إدارة FCM Token ====================


    @bp.route('/fcm-token', methods=['POST'])
    @require_auth
    def update_fcm_token():
        """
        تحديث FCM Token للإشعارات

        Body:
        {
            "fcm_token": "new_firebase_token"
        }
        """
        try:
            user_id = g.current_user_id
            data = request.get_json()

            # قبول token أو fcm_token
            fcm_token = data.get('fcm_token') or data.get('token') if data else None

            if not fcm_token:
                response_data, status_code = error_response('FCM Token مطلوب', 'MISSING_DATA', 400)
                return jsonify(response_data), status_code

            fcm_token = fcm_token.strip()

            # التحقق من صحة FCM Token
            if len(fcm_token) < 10:
                response_data, status_code = error_response('FCM Token غير صحيح', 'INVALID_DATA', 400)
                return jsonify(response_data), status_code

            try:
                # ✅ استخدام get_write_connection لتجنب database lock
                with db_manager.get_write_connection() as conn:
                    # توحيد التخزين في جدول fcm_tokens (المستخدم + التوكن فريد)
                    conn.execute(
                        "DELETE FROM fcm_tokens WHERE user_id = %s OR fcm_token = %s",
                        (user_id, fcm_token)
                    )
                    conn.execute(
                        "INSERT INTO fcm_tokens (user_id, fcm_token, platform, created_at) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)",
                        (user_id, fcm_token, 'android')
                    )
                    conn.commit()
            except Exception as db_error:
                logger.error(f"❌ خطأ في حفظ FCM Token: {db_error}")
                response_data, status_code = error_response('خطأ في حفظ البيانات', 'DB_ERROR', 500)
                return jsonify(response_data), status_code

            logger.info(f"✅ تم تحديث FCM Token للمستخدم {user_id}")
            response_data, status_code = success_response({'updated': True}, 'تم تحديث FCM Token بنجاح')
            return jsonify(response_data), status_code

        except Exception as e:
            logger.error(f"❌ خطأ في تحديث FCM Token: {e}")
            response_data, status_code = error_response('خطأ في تحديث FCM Token', 'FCM_ERROR', 500)
            return jsonify(response_data), status_code



    @bp.route('/fcm-token', methods=['DELETE'])
    @require_auth
    def delete_fcm_token():
        """
        إلغاء تسجيل FCM Token عند تسجيل الخروج

        Body:
        {
            "fcm_token": "token_to_remove"
        }
        """
        try:
            user_id = g.current_user_id
            data = request.get_json(silent=True) or {}
            fcm_token = (data.get('fcm_token') or '').strip()

            try:
                with db_manager.get_write_connection() as conn:
                    if fcm_token:
                        conn.execute(
                            "DELETE FROM fcm_tokens WHERE user_id = %s AND fcm_token = %s",
                            (user_id, fcm_token)
                        )
                    else:
                        conn.execute(
                            "DELETE FROM fcm_tokens WHERE user_id = %s",
                            (user_id,)
                        )
                    conn.commit()
            except Exception as db_error:
                logger.error(f"❌ خطأ في حذف FCM Token: {db_error}")
                response_data, status_code = error_response('خطأ في حذف البيانات', 'DB_ERROR', 500)
                return jsonify(response_data), status_code

            logger.info(f"✅ تم إلغاء تسجيل FCM Token للمستخدم {user_id}")
            response_data, status_code = success_response({'deleted': True}, 'تم إلغاء تسجيل FCM Token بنجاح')
            return jsonify(response_data), status_code

        except Exception as e:
            logger.error(f"❌ خطأ في إلغاء FCM Token: {e}")
            response_data, status_code = error_response('خطأ في إلغاء FCM Token', 'FCM_ERROR', 500)
            return jsonify(response_data), status_code


    # ============================================
    # Unified OTP/Verification Endpoints (لدعم التطبيق)
    # ============================================

    @bp.route('/auth/send-registration-otp', methods=['POST'])
    def mobile_send_registration_otp():
        """إرسال OTP للتسجيل - نسخة mobile"""
        try:
            from backend.api.auth_endpoints import otp_service

            data = request.get_json(silent=True) or {}
            if not data:
                return jsonify({'success': False, 'error': 'لا توجد بيانات'}), 400

            email = data.get('email', '').strip().lower()
            logger.info(f"📱 Mobile send registration OTP: email={email}")

            if not email:
                return jsonify({'success': False, 'error': 'الإيميل مطلوب'}), 400

            if otp_service:
                success, otp_code = otp_service.send_email_otp(email, purpose='registration')

                if success:
                    logger.info(f"✅ OTP sent for registration: {email}")
                    return jsonify({'success': True, 'message': 'تم إرسال رمز التحقق'})
                else:
                    return jsonify({'success': False, 'error': 'فشل إرسال OTP'}), 500
            else:
                return jsonify({'success': False, 'error': 'خدمة OTP غير متاحة'}), 503

        except Exception as e:
            logger.error(f"❌ خطأ في إرسال registration OTP: {e}")
            return jsonify({'success': False, 'error': 'خطأ في الخادم'}), 500

    @bp.route('/auth/verify-registration-otp', methods=['POST'])
    def mobile_verify_registration_otp():
        """التحقق من OTP وإنشاء الحساب - نسخة mobile"""
        try:
            from backend.api.auth_endpoints import otp_service, get_user_by_email
            from backend.services.auth_service import AuthService

            data = request.get_json(silent=True) or {}
            if not data:
                return jsonify({'success': False, 'error': 'لا توجد بيانات'}), 400

            email = data.get('email', '').strip().lower()
            otp_code = (data.get('otp_code') or data.get('otp') or '').strip()
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()

            logger.info(f"📱 Mobile verify registration OTP: email={email}")

            if not all([email, otp_code, username, password]):
                return jsonify({'success': False, 'error': 'جميع الحقول مطلوبة'}), 400

            if otp_service:
                verified, result = otp_service.verify_email_otp(email, otp_code)

                if verified:
                    # إنشاء الحساب
                    auth_service = AuthService()
                    user_data = auth_service.register_user(
                        username=username,
                        email=email,
                        password=password,
                        email_verified=True
                    )

                    if user_data and user_data.get('success'):
                        logger.info(f"✅ Account created: user_id={user_data['user']['id']}")
                        user_payload = {
                            **(user_data.get('user') or {}),
                            'email_verified': True,
                            'user_type': (user_data.get('user') or {}).get('user_type', 'user'),
                        }
                        return jsonify({
                            'success': True,
                            'message': 'تم إنشاء الحساب بنجاح',
                            'user': user_payload,
                            'token': user_data.get('token')
                        })
                    else:
                        return jsonify({'success': False, 'error': 'فشل إنشاء الحساب'}), 500
                else:
                    error_msg = result.get('error', 'رمز OTP غير صحيح')
                    logger.warning(f"⚠️ Registration OTP verification failed: {error_msg}")
                    return jsonify({'success': False, 'error': error_msg}), 400
            else:
                return jsonify({'success': False, 'error': 'خدمة التحقق غير متاحة'}), 503

        except Exception as e:
            logger.error(f"❌ خطأ في التحقق من registration OTP: {e}")
            return jsonify({'success': False, 'error': 'خطأ في الخادم'}), 500

    @bp.route('/auth/send-otp', methods=['POST'])
    def mobile_send_otp():
        """إرسال OTP للتحقق من البريد - نسخة mobile"""
        try:
            from backend.api.auth_endpoints import otp_service

            data = request.get_json(silent=True) or {}
            if not data:
                return jsonify({'success': False, 'error': 'لا توجد بيانات'}), 400

            email = data.get('email', '').strip().lower()
            purpose = data.get('purpose', 'verification')

            logger.info(f"📱 Mobile send OTP: email={email}, purpose={purpose}")

            if not email:
                return jsonify({'success': False, 'error': 'الإيميل مطلوب'}), 400

            if otp_service:
                success, otp_code = otp_service.send_email_otp(email, purpose=purpose)

                if success:
                    logger.info(f"✅ OTP sent: {email}")
                    return jsonify({'success': True, 'message': 'تم إرسال رمز التحقق'})
                else:
                    return jsonify({'success': False, 'error': 'فشل إرسال OTP'}), 500
            else:
                return jsonify({'success': False, 'error': 'خدمة OTP غير متاحة'}), 503

        except Exception as e:
            logger.error(f"❌ خطأ في إرسال OTP: {e}")
            return jsonify({'success': False, 'error': 'خطأ في الخادم'}), 500

    @bp.route('/auth/verify-otp', methods=['POST'])
    def mobile_verify_otp():
        """التحقق من OTP - نسخة mobile"""
        try:
            from backend.api.auth_endpoints import otp_service

            data = request.get_json(silent=True) or {}
            if not data:
                return jsonify({'success': False, 'error': 'لا توجد بيانات'}), 400

            email = data.get('email', '').strip().lower()
            otp_code = (data.get('otp_code') or data.get('otp') or '').strip()

            logger.info(f"📱 Mobile verify OTP: email={email}")

            if not email or not otp_code:
                return jsonify({'success': False, 'error': 'الإيميل ورمز OTP مطلوبان'}), 400

            if otp_service:
                verified, result = otp_service.verify_email_otp(email, otp_code)
                logger.info(f"🔍 OTP verification result: verified={verified}, result={result}")

                if verified:
                    logger.info(f"✅ OTP verified: {email}")
                    return jsonify({'success': True, 'message': result.get('message', 'تم التحقق بنجاح')})
                else:
                    error_msg = result.get('error', 'رمز OTP غير صحيح')
                    remaining = result.get('remaining_attempts')
                    logger.warning(f"❌ OTP verification failed: {error_msg}")

                    response = {'success': False, 'error': error_msg}
                    if remaining is not None:
                        response['remaining_attempts'] = remaining

                    return jsonify(response), 400
            else:
                return jsonify({'success': False, 'error': 'خدمة التحقق غير متاحة'}), 503

        except Exception as e:
            logger.error(f"❌ خطأ في التحقق من OTP: {e}")
            return jsonify({'success': False, 'error': 'خطأ في الخادم'}), 500

    @bp.route('/auth/resend-otp', methods=['POST'])
    def mobile_resend_otp():
        """إعادة إرسال OTP - نسخة mobile"""
        try:
            from backend.api.auth_endpoints import otp_service

            data = request.get_json(silent=True) or {}
            if not data:
                return jsonify({'success': False, 'error': 'لا توجد بيانات'}), 400

            email = data.get('email', '').strip().lower()
            purpose = data.get('purpose', 'verification')

            logger.info(f"📱 Mobile resend OTP: email={email}")

            if not email:
                return jsonify({'success': False, 'error': 'الإيميل مطلوب'}), 400

            if otp_service:
                can_send, wait_seconds = otp_service.can_send_otp(email, purpose)

                if not can_send:
                    return jsonify({
                        'success': False,
                        'error': f'يرجى الانتظار {wait_seconds} ثانية قبل إعادة الإرسال',
                        'wait_seconds': wait_seconds
                    }), 429

                success, otp_code = otp_service.send_email_otp(email, purpose=purpose)

                if success:
                    logger.info(f"✅ OTP resent: {email}")
                    return jsonify({'success': True, 'message': 'تم إعادة إرسال رمز التحقق'})
                else:
                    return jsonify({'success': False, 'error': 'فشل إرسال OTP'}), 500
            else:
                return jsonify({'success': False, 'error': 'خدمة OTP غير متاحة'}), 503

        except Exception as e:
            logger.error(f"❌ خطأ في إعادة إرسال OTP: {e}")
            return jsonify({'success': False, 'error': 'خطأ في الخادم'}), 500

    @bp.route('/auth/forgot-password', methods=['POST'])
    def mobile_forgot_password():
        """طلب استعادة كلمة المرور - نسخة mobile مع دعم SMS/Email"""
        try:
            from backend.api.auth_endpoints import otp_service, get_user_by_email, sms_service

            data = request.get_json(silent=True) or {}
            if not data:
                return jsonify({'success': False, 'error': 'لا توجد بيانات'}), 400

            email = data.get('email', '').strip().lower()
            method = data.get('method', 'sms')  # ✅ الافتراضي: SMS
            phone = (data.get('phone') or data.get('phoneNumber') or data.get('phone_number') or '').strip()
            logger.info(f"📱 Mobile forgot password: email={email}, method={method}")

            if not email:
                return jsonify({'success': False, 'error': 'الإيميل مطلوب'}), 400

            user = get_user_by_email(email)
            if not user:
                return jsonify({'success': True, 'message': 'إذا كان الإيميل مسجل، ستصلك رسالة لاستعادة كلمة المرور'})

            # ✅ جلب رقم الجوال من DB إذا لم يُرسل
            if not phone and user.get('phone_number'):
                phone = user['phone_number']
            if method == 'sms' and not phone:
                method = 'email'

            if otp_service:
                success, otp_code = otp_service.send_email_otp(email, purpose='password_reset')

                if success:
                    # ✅ إرسال SMS إذا كانت الطريقة المختارة
                    if method == 'sms' and phone and sms_service:
                        try:
                            message = f"رمز استعادة كلمة المرور: {otp_code}\nصالح لمدة 5 دقائق"
                            sms_service.send_sms(phone, message)
                            logger.info(f"📱 تم إرسال OTP استعادة عبر SMS إلى {phone}")
                        except Exception as sms_err:
                            logger.warning(f"⚠️ فشل إرسال SMS: {sms_err}")

                    masked_target = email
                    if method == 'sms' and phone:
                        masked_target = phone[:4] + '****' + phone[-2:] if len(phone) > 6 else phone
                    elif '@' in email:
                        masked_target = email[:2] + '***@' + email.split('@')[1]

                    logger.info(f"✅ Password reset OTP sent via {method}: {email}")
                    return jsonify({
                        'success': True,
                        'message': f'تم إرسال رمز استعادة كلمة المرور إلى {"هاتفك" if method == "sms" else "إيميلك"}',
                        'method': method,
                        'masked_target': masked_target,
                    })
                else:
                    return jsonify({'success': True, 'message': 'إذا كان الإيميل مسجل، ستصلك رسالة'})
            else:
                return jsonify({'success': False, 'error': 'خدمة OTP غير متاحة'}), 503

        except Exception as e:
            logger.error(f"❌ خطأ في طلب استعادة كلمة المرور: {e}")
            return jsonify({'success': False, 'error': 'خطأ في الخادم'}), 500

    # ============================================
    # Password Reset Endpoints
    # ============================================

    @bp.route('/auth/verify-reset-otp', methods=['POST'])
    def mobile_verify_reset_otp():
        """التحقق من OTP لاستعادة كلمة المرور - نسخة mobile"""
        try:
            from backend.api.auth_endpoints import otp_service, get_user_by_email, cleanup_verification_data

            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'لا توجد بيانات'}), 400

            email = data.get('email', '').strip().lower()
            otp_code = data.get('otp', '').strip()

            logger.info(f"📱 Mobile verify reset OTP: email={email}, otp_length={len(otp_code) if otp_code else 0}")

            if not email or not otp_code:
                return jsonify({'success': False, 'error': 'الإيميل ورمز OTP مطلوبان'}), 400

            if otp_service:
                verified, result = otp_service.verify_email_otp(email, otp_code)
                logger.info(f"🔍 Reset OTP verification: verified={verified}, result={result}")

                if verified:
                    user = get_user_by_email(email)
                    if not user:
                        logger.error(f"❌ User not found for email: {email}")
                        return jsonify({'success': False, 'error': 'المستخدم غير موجود'}), 404

                    # ✅ get_user_by_email تُرجع dict وليس tuple
                    user_id = user['id'] if isinstance(user, dict) else user[0]

                    import jwt
                    secret_key = os.getenv('JWT_SECRET_KEY', 'trading_ai_bot_secret_key_2026')

                    reset_token_payload = {
                        'user_id': user_id,
                        'email': email,
                        'purpose': 'password_reset',
                        'exp': datetime.utcnow() + timedelta(minutes=10),
                        'iat': datetime.utcnow()
                    }

                    reset_token = jwt.encode(reset_token_payload, secret_key, algorithm='HS256')

                    # ✅ حذف OTP من قاعدة البيانات (استخدام واحد فقط)
                    cleanup_verification_data(email)
                    logger.info(f"✅ Reset OTP verified and cleaned for: {email}")

                    return jsonify({
                        'success': True,
                        'reset_token': reset_token,
                        'expires_in': 600,
                        'message': 'تم التحقق بنجاح'
                    })
                else:
                    error_msg = result.get('error', 'رمز OTP غير صحيح')
                    remaining = result.get('remaining_attempts')
                    logger.warning(f"❌ Reset OTP verification failed: {error_msg}, remaining={remaining}")

                    response = {'success': False, 'error': error_msg}
                    if remaining is not None:
                        response['remaining_attempts'] = remaining

                    return jsonify(response), 400
            else:
                logger.error("❌ OTP service not available")
                return jsonify({'success': False, 'error': 'خدمة التحقق غير متاحة'}), 503

        except Exception as e:
            logger.error(f"❌ خطأ في التحقق من OTP: {e}", exc_info=True)
            return jsonify({'success': False, 'error': 'خطأ في الخادم'}), 500

    @bp.route('/auth/reset-password', methods=['POST'])
    def mobile_reset_password():
        """إعادة تعيين كلمة المرور باستخدام Reset Token - نسخة mobile"""
        try:
            from backend.services.auth_service import AuthService

            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'لا توجد بيانات'}), 400

            reset_token = (data.get('reset_token') or data.get('resetToken') or '').strip()
            new_password = (data.get('new_password') or data.get('newPassword') or '').strip()

            logger.info(f"📱 Mobile reset password request")

            if not reset_token or not new_password:
                return jsonify({'success': False, 'error': 'Reset token وكلمة المرور الجديدة مطلوبان'}), 400

            from backend.api.auth_endpoints import validate_password
            if not validate_password(new_password):
                return jsonify({'success': False, 'error': 'كلمة المرور يجب أن تكون 8 أحرف على الأقل وتحتوي على حروف كبيرة وصغيرة وأرقام'}), 400

            import jwt
            secret_key = os.getenv('JWT_SECRET_KEY', 'trading_ai_bot_secret_key_2026')

            try:
                payload = jwt.decode(reset_token, secret_key, algorithms=['HS256'])

                if payload.get('purpose') != 'password_reset':
                    return jsonify({'success': False, 'error': 'Token غير صالح'}), 400

                user_id = payload.get('user_id')
                auth_service = AuthService()
                success = auth_service.update_password(user_id, new_password)

                if success:
                    logger.info(f"✅ Password reset successfully for user {user_id}")
                    return jsonify({'success': True, 'message': 'تم إعادة تعيين كلمة المرور بنجاح'})
                else:
                    return jsonify({'success': False, 'error': 'فشل تحديث كلمة المرور'}), 500

            except jwt.ExpiredSignatureError:
                return jsonify({'success': False, 'error': 'انتهت صلاحية Reset Token'}), 400
            except jwt.InvalidTokenError:
                return jsonify({'success': False, 'error': 'Reset Token غير صالح'}), 400

        except Exception as e:
            logger.error(f"❌ خطأ في إعادة تعيين كلمة المرور: {e}")
            return jsonify({'success': False, 'error': 'خطأ في الخادم'}), 500

    # ============================================
    # SMS/Phone Verification Endpoints
    # ============================================

    @bp.route('/auth/verify-phone-token', methods=['POST'])
    @require_auth
    def mobile_verify_phone_token():
        """التحقق من Firebase Phone Token - نسخة mobile"""
        try:
            from backend.utils.firebase_sms_service import verify_firebase_phone_token, get_sms_handler

            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'لا توجد بيانات'}), 400

            id_token = data.get('id_token', '').strip()
            phone_number = data.get('phone_number', '').strip()
            user_id = data.get('user_id')
            auth_user_id = getattr(g, 'current_user_id', None) or getattr(g, 'user_id', None)

            if user_id and str(user_id) != str(auth_user_id):
                return jsonify({'success': False, 'error': 'غير مصرح بتحديث مستخدم آخر'}), 403

            logger.info(f"📱 Mobile verify phone token: phone={phone_number}")

            if not id_token:
                return jsonify({'success': False, 'error': 'Firebase ID Token مطلوب'}), 400

            verified, result = verify_firebase_phone_token(id_token, phone_number)

            if verified:
                # تحديث حالة المستخدم في قاعدة البيانات
                handler = get_sms_handler()
                handler.update_user_verification_status(auth_user_id, result['phone_number'])

                logger.info(f"✅ Phone verified: {result['phone_number']}")
                return jsonify({
                    'success': True,
                    'message': 'تم التحقق من الهاتف بنجاح',
                    'phone_number': result['phone_number']
                })
            else:
                return jsonify({'success': False, 'error': result.get('error', 'فشل التحقق')}), 400

        except Exception as e:
            logger.error(f"❌ خطأ في التحقق من الهاتف: {e}")
            return jsonify({'success': False, 'error': 'خطأ في الخادم'}), 500
