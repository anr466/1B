#!/usr/bin/env python3
"""
نقاط النهاية لـ OTP في تسجيل الدخول
يدعم إرسال والتحقق من OTP عند تسجيل الدخول
"""

import sys
import os
import hashlib
import random
import time
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta

# إضافة مسار المشروع
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.database_manager import DatabaseManager
from config.logging_config import get_logger

# استيراد خدمات OTP
try:
    from utils.firebase_sms_service import FirebaseSMSHandler
    sms_service = FirebaseSMSHandler()
except ImportError:
    sms_service = None

try:
    from backend.api.token_refresh_endpoint import generate_tokens
    TOKEN_SYSTEM_AVAILABLE = True
except ImportError:
    TOKEN_SYSTEM_AVAILABLE = False

logger = get_logger(__name__)
db_manager = DatabaseManager()

# إنشاء Blueprint
# Flask mounted على /api، لذا نستخدم /auth/login فقط
login_otp_bp = Blueprint('login_otp', __name__, url_prefix='/auth/login')

# ✅ استخدام SimpleEmailOTPService الموحد بدلاً من RAM dict
try:
    from backend.utils.simple_email_otp_service import SimpleEmailOTPService
    otp_service = SimpleEmailOTPService()
    OTP_SERVICE_AVAILABLE = True
except ImportError:
    otp_service = None
    OTP_SERVICE_AVAILABLE = False

def generate_otp():
    """توليد OTP من 6 أرقام"""
    return str(random.randint(100000, 999999))

# ❌ DELETED: get_user_by_identifier() - Moved to unified service
# Reason: Duplicate implementation
# Replacement: backend/utils/user_lookup_service.py
from backend.utils.user_lookup_service import get_user_by_identifier

@login_otp_bp.route('/send-otp', methods=['POST'])
def send_login_otp():
    """إرسال OTP لتسجيل الدخول"""
    try:
        # Timeout: 10 ثوانِ للطلب
        request.environ.get('werkzeug.server.shutdown')
        
        data = request.get_json(force=True) or {}
        
        identifier = data.get('identifier', '').strip()  # إيميل أو يوزر
        password = data.get('password', '')
        
        if not identifier or not password:
            return jsonify({
                'success': False,
                'error': 'اسم المستخدم أو الإيميل وكلمة المرور مطلوبان'
            }), 400
        
        # البحث عن المستخدم
        user = get_user_by_identifier(identifier)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'اسم المستخدم أو الإيميل غير مسجل'
            }), 400
        
        # التحقق من كلمة المرور
        from backend.utils.password_utils import verify_password as _verify_pw
        if not _verify_pw(password, user['password_hash']):
            return jsonify({
                'success': False,
                'error': 'كلمة المرور غير صحيحة'
            }), 401
        
        # التحقق من تفعيل الحساب
        if not user.get('email_verified', False):
            return jsonify({
                'success': False,
                'error': 'يجب تفعيل البريد الإلكتروني أولاً',
                'requires_verification': True
            }), 403
        
        # ✅ استخدام خدمة OTP الموحدة
        if not OTP_SERVICE_AVAILABLE or not otp_service:
            return jsonify({
                'success': False,
                'error': 'خدمة OTP غير متاحة'
            }), 500
        
        # ✅ تحديد طريقة الإرسال (الافتراضي: sms)
        method = data.get('method', 'sms')
        phone_number = user.get('phone_number')
        email = user.get('email')
        
        # إذا طلب SMS لكن لا يوجد رقم جوال → fallback للإيميل
        if method == 'sms' and not phone_number:
            method = 'email'
        
        # إذا طلب email لكن لا يوجد إيميل → fallback للـ SMS
        if method == 'email' and not email:
            method = 'sms'
        
        # إرسال OTP عبر الخدمة الموحدة (Database-backed) — يُخزن دائماً
        success, otp_code = otp_service.send_email_otp(
            email or phone_number,
            purpose='login'
        )
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'فشل في إرسال رمز التحقق'
            }), 500
        
        # ✅ إرسال OTP حسب الطريقة المختارة
        if method == 'sms' and phone_number:
            sms_sent = False
            if sms_service:
                try:
                    message = f"رمز التحقق لتسجيل الدخول: {otp_code}\nصالح لمدة 5 دقائق"
                    sms_service.send_sms(phone_number, message)
                    sms_sent = True
                    logger.info(f"📱 تم إرسال OTP عبر SMS إلى {phone_number}")
                except Exception as sms_error:
                    logger.error(f"❌ فشل إرسال SMS: {sms_error}")
            
            if not sms_sent:
                logger.info(f"📱 [DEV] OTP للمستخدم {user['username']}: {otp_code}")
            
            masked_target = phone_number[:4] + '****' + phone_number[-2:] if len(phone_number) > 6 else phone_number
        else:
            # Email — OTP أُرسل بالفعل عبر send_email_otp
            logger.info(f"� تم إرسال OTP عبر Email إلى {email}")
            masked_target = email[:2] + '***@' + email.split('@')[1] if '@' in email else email
        
        # ✅ إرجاع خيارات التحقق المتاحة ليستخدمها العميل
        verification_options = []
        if phone_number:
            masked_phone = phone_number[:4] + '****' + phone_number[-2:] if len(phone_number) > 6 else phone_number
            verification_options.append({'method': 'sms', 'masked_target': masked_phone, 'label': 'رسالة نصية SMS'})
        if email:
            masked_email = email[:2] + '***@' + email.split('@')[1] if '@' in email else email
            verification_options.append({'method': 'email', 'masked_target': masked_email, 'label': 'البريد الإلكتروني'})
        
        return jsonify({
            'success': True,
            'message': f'تم إرسال رمز التحقق إلى {"هاتفك" if method == "sms" else "إيميلك"}',
            'method': method,
            'masked_target': masked_target,
            'user_id': user['id'],
            'verification_options': verification_options,
            'expires_in': 300
        })
        
    except Exception as e:
        logger.error(f"خطأ في إرسال OTP: {e}")
        
        # رسائل خطأ محددة
        error_message = 'خطأ في الخادم'
        if 'timeout' in str(e).lower():
            error_message = 'انتهى وقت الانتظار. يرجى المحاولة مرة أخرى'
        elif 'connection' in str(e).lower():
            error_message = 'فشل الاتصال. تحقق من اتصالك بالإنترنت'
        
        return jsonify({
            'success': False,
            'error': error_message,
            'retry_allowed': True
        }), 500

@login_otp_bp.route('/verify-otp', methods=['POST'])
def verify_login_otp():
    """التحقق من OTP وإتمام تسجيل الدخول"""
    try:
        data = request.get_json(force=True) or {}
        
        user_id = data.get('user_id')
        otp_code = data.get('otp_code', '').strip()
        
        if not user_id or not otp_code:
            return jsonify({
                'success': False,
                'error': 'معرف المستخدم ورمز التحقق مطلوبان'
            }), 400
        
        # ✅ الحصول على بيانات المستخدم من Database
        user = get_user_by_identifier(str(user_id))
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'المستخدم غير موجود'
            }), 400
        
        # ✅ استخدام الخدمة الموحدة للتحقق
        if not OTP_SERVICE_AVAILABLE or not otp_service:
            return jsonify({
                'success': False,
                'error': 'خدمة OTP غير متاحة'
            }), 500
        
        verified, result = otp_service.verify_email_otp(user['email'], otp_code)
        
        if not verified:
            # إرجاع رسالة الخطأ من الخدمة الموحدة
            error_msg = result.get('error', 'رمز التحقق غير صحيح')
            remaining = result.get('remaining_attempts')
            
            response = {
                'success': False,
                'error': error_msg
            }
            
            if remaining is not None:
                response['remaining_attempts'] = remaining
            
            return jsonify(response), 400
        
        # ✅ OTP صحيح - إنشاء JWT tokens
        if TOKEN_SYSTEM_AVAILABLE:
            tokens = generate_tokens(
                user['id'],
                user['username'],
                user.get('user_type', 'user')
            )
            
            return jsonify({
                'success': True,
                'token': tokens['access_token'],
                'refresh_token': tokens['refresh_token'],
                'expires_in': tokens['expires_in'],
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'user_type': user.get('user_type', 'user')
                },
                'message': 'تم تسجيل الدخول بنجاح'
            })
        else:
            return jsonify({
                'success': True,
                'user_id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'message': 'تم تسجيل الدخول بنجاح'
            })
        
    except Exception as e:
        logger.error(f"خطأ في التحقق من OTP: {e}")
        return jsonify({
            'success': False,
            'error': 'خطأ في الخادم'
        }), 500

@login_otp_bp.route('/resend-otp', methods=['POST'])
def resend_login_otp():
    """إعادة إرسال OTP"""
    try:
        data = request.get_json(force=True) or {}
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'معرف المستخدم مطلوب'
            }), 400
        
        # ✅ الحصول على بيانات المستخدم
        user = get_user_by_identifier(str(user_id))
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'المستخدم غير موجود'
            }), 400
        
        # ✅ استخدام الخدمة الموحدة لإعادة الإرسال
        if not OTP_SERVICE_AVAILABLE or not otp_service:
            return jsonify({
                'success': False,
                'error': 'خدمة OTP غير متاحة'
            }), 500
        
        # التحقق من cooldown
        can_send, wait_seconds = otp_service.can_send_otp(user['email'], purpose='login', cooldown_minutes=1)
        
        if not can_send:
            return jsonify({
                'success': False,
                'error': f'يرجى الانتظار {wait_seconds} ثانية قبل إعادة الإرسال'
            }), 429
        
        # إرسال OTP جديد
        success, otp_code = otp_service.send_email_otp(user['email'], purpose='login')
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'فشل في إعادة إرسال رمز التحقق'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'تم إعادة إرسال رمز التحقق',
            'expires_in': 600  # 10 minutes (موحد)
        })
        
    except Exception as e:
        logger.error(f"خطأ في إعادة إرسال OTP: {e}")
        return jsonify({
            'success': False,
            'error': 'خطأ في الخادم'
        }), 500
