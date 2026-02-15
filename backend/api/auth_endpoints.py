#!/usr/bin/env python3
"""
نقاط النهاية للمصادقة والتحقق من الإيميل
يدعم تسجيل المستخدمين الجدد واستعادة كلمة المرور

God Object Split:
- Registration routes → auth_registration_routes.py
- Password/change routes → auth_password_routes.py
- Login, OTP, session routes → here (this file)
"""

import sys
import os
import hashlib
import time
import re
import bcrypt
from flask import Blueprint, request, jsonify
from typing import Dict, Optional

# إضافة مسار المشروع
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.database_manager import DatabaseManager
from config.logging_config import get_logger

# استيراد نظام JWT Tokens
try:
    from backend.api.token_refresh_endpoint import generate_tokens, TOKEN_SYSTEM_AVAILABLE
except ImportError:
    TOKEN_SYSTEM_AVAILABLE = False
    generate_tokens = None

try:
    from backend.utils.security_audit_service import SecurityAuditService
    security_audit = SecurityAuditService()
    SECURITY_AUDIT_AVAILABLE = True
    def get_security_audit():
        return security_audit
except (ImportError, ModuleNotFoundError):
    SECURITY_AUDIT_AVAILABLE = False
    def get_security_audit():
        return None
from backend.utils.idempotency_manager import require_idempotency
from backend.utils.request_deduplicator import prevent_concurrent_duplicates

# استيراد آمن للخدمات الاختيارية
try:
    from backend.utils.simple_email_otp_service import SimpleEmailOTPService
    otp_service = SimpleEmailOTPService()
    print('✅ SimpleEmailOTPService initialized successfully')
except ImportError as e:
    print(f'❌ Failed to import SimpleEmailOTPService: {e}')
    otp_service = None

try:
    from utils.firebase_sms_service import FirebaseSMSHandler
    sms_service = FirebaseSMSHandler()
except ImportError:
    sms_service = None

try:
    from utils.error_handler import log_error
except ImportError:
    def log_error(message):
        pass

# ✅ استيراد خدمة التسجيل الأمني
try:
    from backend.utils.security_audit_service import get_security_audit_service
    security_audit = get_security_audit_service()
except ImportError:
    security_audit = None

# إعداد Logger
logger = get_logger(__name__)

# إنشاء Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
# تهيئة الخدمات
db_manager = DatabaseManager()

# ✅ دالة مساعدة لجلب معلومات الطلب
def get_request_info():
    """جلب IP و User Agent من الطلب"""
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    return ip, user_agent

# ==================== دوال Validation ====================
def validate_email(email: str) -> bool:
    """التحقق من صيغة البريد الإلكتروني"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> bool:
    """التحقق من قوة كلمة المرور - متوافق مع Frontend"""
    if len(password) < 8:
        return False
    # يجب أن تحتوي على حرف صغير
    if not re.search(r'[a-z]', password):
        return False
    # يجب أن تحتوي على حرف كبير
    if not re.search(r'[A-Z]', password):
        return False
    # يجب أن تحتوي على رقم
    if not re.search(r'\d', password):
        return False
    return True

def validate_phone(phone: str) -> bool:
    """التحقق من صيغة رقم الهاتف"""
    if not phone:
        return True  # الهاتف اختياري
    # إزالة أي أحرف غير رقمية
    digits_only = re.sub(r'[^0-9]', '', phone)
    # يجب أن يكون بين 10 و 15 رقم
    return 10 <= len(digits_only) <= 15

def validate_username(username: str) -> bool:
    """التحقق من صيغة اسم المستخدم - متوافق مع Frontend"""
    if len(username) < 3 or len(username) > 50:
        return False
    # فقط أحرف إنجليزية وأرقام وشرطة سفلية (متوافق مع Frontend)
    pattern = r'^[a-zA-Z0-9_]+$'
    return re.match(pattern, username) is not None

def normalize_username(username: str) -> str:
    """توحيد اسم المستخدم - تحويل لـ lowercase"""
    return username.strip().lower()

def sanitize_input(text: str) -> str:
    """تنظيف المدخلات من XSS"""
    if not text:
        return text
    # إزالة علامات HTML
    dangerous_chars = ['<', '>', '"', "'", '&', '\\', '/', ';']
    result = text
    for char in dangerous_chars:
        result = result.replace(char, '')
    return result.strip()

# ❌ DELETED: get_user_by_email() and get_user_by_username()
# Reason: Duplicated across 3 files (auth_endpoints, login_otp_endpoints, secure_actions_endpoints)
# Unified in: backend/utils/user_lookup_service.py
# Import: from backend.utils.user_lookup_service import get_user_by_email, get_user_by_username

from backend.utils.user_lookup_service import get_user_by_email, get_user_by_username, get_user_by_identifier

def update_user_verification(user_id: int, verified: bool) -> bool:
    """تحديث حالة التحقق من البريد الإلكتروني"""
    try:
        with db_manager.get_write_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET email_verified = ? WHERE id = ?",
                (1 if verified else 0, user_id)
            )
            return True
    except Exception as e:
        logger.error(f"خطأ في تحديث حالة التحقق: {e}")
        return False

def update_user_password(user_id: int, password_hash: str):
    """تحديث كلمة مرور المستخدم"""
    try:
        with db_manager.get_write_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE users 
                SET password_hash = ?, updated_at = datetime('now')
                WHERE id = ?
            """, (password_hash, user_id))
        
    except Exception as e:
        log_error(f"خطأ في تحديث كلمة المرور: {e}")

def save_password_reset_request(user_id: int, otp_code: str):
    """حفظ طلب استعادة كلمة المرور"""
    try:
        # يمكن حفظ طلبات الاستعادة في جدول منفصل للمراقبة
        # هنا نكتفي بتسجيل العملية
        log_error(f"طلب استعادة كلمة المرور للمستخدم {user_id}")
        
    except Exception as e:
        log_error(f"خطأ في حفظ طلب الاستعادة: {e}")

def cleanup_verification_data(email: str):
    """تنظيف بيانات التحقق من قاعدة البيانات بعد العملية الناجحة"""
    try:
        with db_manager.get_write_connection() as conn:
            cursor = conn.cursor()
            
            # حذف رموز التحقق المنتهية
            cursor.execute("""
                DELETE FROM verification_codes 
                WHERE email = ? AND (verified = 1 OR expires_at < ?)
            """, (email, time.time()))
            logger.debug(f"✅ Verification data cleaned up for {email}")
        
    except Exception as e:
        log_error(f"خطأ في تنظيف بيانات التحقق: {e}")

# ==================== Shared state for sub-modules ====================
_shared = {
    'db_manager': db_manager,
    'otp_service': otp_service,
    'sms_service': sms_service,
    'security_audit': security_audit,
    'validate_email': validate_email,
    'validate_password': validate_password,
    'validate_username': validate_username,
    'validate_phone': validate_phone,
    'normalize_username': normalize_username,
    'sanitize_input': sanitize_input,
    'get_request_info': get_request_info,
    'get_user_by_email': get_user_by_email,
    'cleanup_verification_data': cleanup_verification_data,
    'save_password_reset_request': save_password_reset_request,
    'update_user_password': update_user_password,
    'TOKEN_SYSTEM_AVAILABLE': TOKEN_SYSTEM_AVAILABLE,
    'generate_tokens': generate_tokens,
    'prevent_concurrent_duplicates': prevent_concurrent_duplicates,
    'require_idempotency': require_idempotency,
}

# ==================== Register sub-module routes ====================
from backend.api.auth_registration_routes import register_registration_routes
from backend.api.auth_password_routes import register_password_routes

register_registration_routes(auth_bp, _shared)
register_password_routes(auth_bp, _shared)


# ==================== OTP / Verification Routes ====================

@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    """إرسال OTP للتحقق من الإيميل"""
    try:
        # ✅ معالجة JSON errors
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            return jsonify({'success': False, 'error': 'JSON غير صحيح', 'code': 'INVALID_JSON'}), 400
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'لا توجد بيانات'
            }), 400
        
        email = data.get('email', '').strip().lower()
        phone = data.get('phone', '').strip()
        method = data.get('method', 'sms')  # ✅ الافتراضي: SMS
        operation_type = data.get('operation_type', 'register')  # register, reset_password, change_email
        
        if not email:
            return jsonify({
                'success': False,
                'error': 'الإيميل مطلوب'
            }), 400
        
        # إذا طلب SMS لكن لا يوجد رقم → جلب من DB أو fallback للإيميل
        if method == 'sms' and not phone:
            try:
                user = get_user_by_email(email)
                if user and user.get('phone_number'):
                    phone = user['phone_number']
                else:
                    method = 'email'
            except Exception:
                method = 'email'
        
        # ✅ Rate Limiting - منع الإرسال المتكرر
        if security_audit and security_audit.is_rate_limited(email, 'OTP_SENT', max_attempts=5, minutes=15):
            return jsonify({
                'success': False,
                'error': 'تم إرسال عدة رموز تحقق. يرجى الانتظار 15 دقيقة قبل المحاولة مرة أخرى.'
            }), 429
        
        # إرسال OTP
        if otp_service:
            success, otp_code = otp_service.send_email_otp(email)
            
            if success:
                # ✅ إرسال حسب الطريقة المختارة
                if method == 'sms' and phone and sms_service:
                    try:
                        purpose_msg = 'إعادة تعيين كلمة المرور' if operation_type == 'reset_password' else 'التحقق'
                        message = f"رمز {purpose_msg}: {otp_code}\nصالح لمدة 5 دقائق"
                        sms_service.send_sms(phone, message)
                        logger.info(f"📱 تم إرسال OTP عبر SMS إلى {phone}")
                    except Exception as sms_err:
                        logger.warning(f"⚠️ فشل إرسال SMS: {sms_err}")
                        logger.info(f"📱 [DEV] OTP sent via email fallback")
                
                # ✅ تسجيل إرسال OTP
                if security_audit:
                    ip, user_agent = get_request_info()
                    security_audit.log_action(
                        action='OTP_SENT',
                        resource=email,
                        ip_address=ip,
                        user_agent=user_agent,
                        status='success',
                        details={'operation_type': operation_type, 'method': method}
                    )
                
                masked_target = email
                if method == 'sms' and phone:
                    masked_target = phone[:4] + '****' + phone[-2:] if len(phone) > 6 else phone
                elif email and '@' in email:
                    masked_target = email[:2] + '***@' + email.split('@')[1]
                
                return jsonify({
                    'success': True,
                    'message': f'تم إرسال رمز التحقق إلى {"هاتفك" if method == "sms" else "إيميلك"}',
                    'method': method,
                    'masked_target': masked_target,
                    'email': email
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'فشل في إرسال رمز التحقق'
                }), 500
        else:
            return jsonify({
                'success': False,
                'error': 'خدمة OTP غير متاحة'
            }), 503
            
    except Exception as e:
        log_error(f"خطأ في إرسال OTP: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'خطأ في الخادم'
        }), 500

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """التحقق من OTP - alias لـ verify-email"""
    return verify_email_internal()

@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """التحقق من الإيميل باستخدام OTP"""
    return verify_email_internal()

def verify_email_internal():
    """التحقق من الإيميل باستخدام OTP - الدالة الداخلية"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'لا توجد بيانات'
            }), 400
        
        email = data.get('email', '').strip().lower()
        otp_code = data.get('otp', '').strip()
        
        if not email or not otp_code:
            return jsonify({
                'success': False,
                'error': 'الإيميل ورمز OTP مطلوبان'
            }), 400
        
        # التحقق من OTP
        if otp_service:
            verified, result = otp_service.verify_email_otp(email, otp_code)
            
            if verified:
                # تحديث حالة التحقق في قاعدة البيانات
                user = get_user_by_email(email)
                if user:
                    update_user_verification(user['id'], True)
                    
                    # تنظيف بيانات التحقق من قاعدة البيانات
                    cleanup_verification_data(email)
                    
                    return jsonify({
                        'success': True,
                        'user_id': user['id'],
                        'message': 'تم التحقق من الإيميل بنجاح'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'المستخدم غير موجود'
                    }), 404
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'رمز OTP غير صحيح') if isinstance(result, dict) else 'رمز OTP غير صحيح'
                }), 400
        else:
            return jsonify({
                'success': False,
                'error': 'خدمة OTP غير متاحة'
            }), 503
            
    except Exception as e:
        log_error(f"خطأ في التحقق من الإيميل: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'خطأ في الخادم'
        }), 500

@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """إعادة إرسال رمز OTP"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'لا توجد بيانات'
            }), 400
        
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({
                'success': False,
                'error': 'الإيميل مطلوب'
            }), 400
        
        # التحقق من وجود المستخدم
        user = get_user_by_email(email)
        if not user:
            return jsonify({
                'success': False,
                'error': 'الإيميل غير مسجل'
            }), 400
        
        # إرسال OTP جديد
        success, otp_code = otp_service.send_email_otp(email)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'تم إرسال رمز جديد للإيميل'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'فشل في إرسال رمز التحقق'
            }), 500
            
    except Exception as e:
        log_error(f"خطأ في إعادة إرسال OTP: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'خطأ في الخادم'
        }), 500

@auth_bp.route('/send-verification-email', methods=['POST'])
def send_verification_email():
    """إرسال بريد التحقق من الإيميل"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'لا توجد بيانات'
            }), 400
        
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({
                'success': False,
                'error': 'الإيميل مطلوب'
            }), 400
        
        # إرسال OTP (يعمل كـ verification email)
        if otp_service:
            success, otp_code = otp_service.send_email_otp(email)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'تم إرسال بريد التحقق إلى إيميلك',
                    'email': email
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'فشل في إرسال بريد التحقق'
                }), 500
        else:
            return jsonify({
                'success': False,
                'error': 'خدمة البريد غير متاحة'
            }), 503
            
    except Exception as e:
        log_error(f"خطأ في إرسال بريد التحقق: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'خطأ في الخادم'
        }), 500


# ==================== Login Route ====================

@auth_bp.route('/login', methods=['POST'])
@prevent_concurrent_duplicates
def login_user():
    """تسجيل دخول المستخدم"""
    try:
        # ✅ معالجة JSON errors
        try:
            data = request.get_json(force=True)
        except Exception as json_error:
            return jsonify({'success': False, 'error': 'JSON غير صحيح', 'code': 'INVALID_JSON'}), 400
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'لا توجد بيانات'
            }), 400
        
        # ✅ Type validation - تحقق من أنواع البيانات
        email_raw = data.get('email', '')
        username_raw = data.get('username', '')
        password_raw = data.get('password', '')
        
        # التحقق من أن القيم strings وليست أنواع أخرى
        if not isinstance(email_raw, str):
            return jsonify({
                'success': False,
                'error': 'نوع البيانات غير صحيح: email يجب أن يكون نص'
            }), 400
        
        if not isinstance(username_raw, str):
            return jsonify({
                'success': False,
                'error': 'نوع البيانات غير صحيح: username يجب أن يكون نص'
            }), 400
        
        if not isinstance(password_raw, str):
            return jsonify({
                'success': False,
                'error': 'نوع البيانات غير صحيح: password يجب أن يكون نص'
            }), 400
        
        # دعم تسجيل الدخول بالإيميل أو اسم المستخدم
        email = email_raw.strip().lower()
        username = username_raw.strip()
        password = password_raw
        
        # سجل تفصيلي للتشخيص
        logger.info(f"🔐 Login attempt - email: '{email}', username: '{username}', password_len: {len(password)}")
        
        if (not email and not username) or not password:
            return jsonify({
                'success': False,
                'error': 'اسم المستخدم أو الإيميل وكلمة المرور مطلوبان'
            }), 400
        
        # البحث عن المستخدم بالإيميل أو اسم المستخدم
        user = None
        if email:
            # محاولة البحث بالإيميل أولاً
            user = get_user_by_email(email)
            # إذا لم يُعثر عليه، جرب البحث باليوزر نيم (في حال أدخل المستخدم اليوزر في حقل الإيميل)
            if not user:
                user = get_user_by_username(email)
        if username and not user:
            user = get_user_by_username(username)
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'اسم المستخدم أو الإيميل غير مسجل'
            }), 400
        
        # التحقق من كلمة المرور (يدعم bcrypt + SHA-256 القديم)
        from backend.utils.password_utils import verify_password as _verify_pw, needs_upgrade, upgrade_hash
        password_match = _verify_pw(password, user['password_hash'])
        
        # ✅ ترقية تلقائية من SHA-256 → bcrypt عند نجاح الدخول
        if password_match and needs_upgrade(user['password_hash']):
            try:
                new_hash = upgrade_hash(password)
                db_manager.execute_query("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user['id']))
                logger.info(f"✅ Password hash upgraded to bcrypt for user {user['id']}")
            except Exception as upgrade_err:
                logger.warning(f"⚠️ Password hash upgrade failed: {upgrade_err}")
        
        logger.debug(f"🔐 Login attempt - User: {user.get('username')}, Password match: {password_match}")
        if not password_match:
            logger.warning(f"❌ Password mismatch for user: {user.get('username')}")
            
            # ✅ تسجيل محاولة الدخول الفاشلة
            if security_audit:
                ip, user_agent = get_request_info()
                security_audit.log_action(
                    action='LOGIN_FAILED',
                    user_id=user['id'],
                    resource=email or username,
                    ip_address=ip,
                    user_agent=user_agent,
                    status='failed',
                    details={'reason': 'wrong_password'}
                )
            
            return jsonify({
                'success': False,
                'error': 'كلمة المرور غير صحيحة'
            }), 401
        
        # ✅ التحقق من تفعيل الحساب (إجباري)
        # البريد الإلكتروني يجب أن يكون مفعلاً
        if not user.get('email_verified', False):
            return jsonify({
                'success': False,
                'error': 'يجب تفعيل البريد الإلكتروني أولاً. يرجى التحقق من بريدك الإلكتروني.',
                'requires_verification': True,
                'email': user.get('email')
            }), 403
        
        # ✅ تسجيل الدخول الناجح
        if security_audit:
            ip, user_agent = get_request_info()
            security_audit.log_action(
                action='LOGIN_SUCCESS',
                user_id=user['id'],
                resource=email or username,
                ip_address=ip,
                user_agent=user_agent,
                status='success'
            )
        
        # إنشاء JWT tokens
        if TOKEN_SYSTEM_AVAILABLE:
            user_type = user.get('user_type', 'user')
            tokens = generate_tokens(user['id'], user['username'], user_type)
            
            return jsonify({
                'success': True,
                'token': tokens['access_token'],
                'refresh_token': tokens['refresh_token'],
                'expires_in': tokens['expires_in'],
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'user_type': user_type
                },
                'message': 'تم تسجيل الدخول بنجاح'
            })
        else:
            # Fallback بدون token (للتوافق)
            return jsonify({
                'success': True,
                'username': user['username'],
                'email': user['email'],
                'message': 'تم تسجيل الدخول بنجاح (بدون token)'
            })
        
    except Exception as e:
        log_error(f"خطأ في تسجيل الدخول: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى'
        }), 500


# ==================== Verification Methods ====================

@auth_bp.route('/get-verification-methods', methods=['POST'])
def get_verification_methods():
    """✅ جلب طرق التحقق المتاحة لإيميل معين (قبل المصادقة)"""
    try:
        data = request.get_json(force=True) or {}
        email = (data.get('email') or '').strip().lower()
        
        if not email:
            return jsonify({'success': False, 'error': 'الإيميل مطلوب'}), 400
        
        user = get_user_by_email(email)
        
        # لأسباب أمنية: نعيد نفس البنية حتى لو المستخدم غير موجود
        options = []
        masked_phone = None
        masked_email = None
        
        if user:
            phone = user.get('phone_number')
            if phone:
                masked_phone = phone[:4] + '****' + phone[-2:] if len(phone) > 6 else '****'
                options.append({'method': 'sms', 'masked_target': masked_phone, 'label': 'رسالة نصية SMS'})
            
            if user.get('email'):
                e = user['email']
                masked_email = e[:2] + '***@' + e.split('@')[1] if '@' in e else '***'
                options.append({'method': 'email', 'masked_target': masked_email, 'label': 'البريد الإلكتروني'})
        else:
            # إرجاع email فقط كخيار حتى لا نكشف عدم وجود الحساب
            if '@' in email:
                masked_email = email[:2] + '***@' + email.split('@')[1]
            options.append({'method': 'email', 'masked_target': masked_email or '***', 'label': 'البريد الإلكتروني'})
        
        return jsonify({
            'success': True,
            'options': options,
            'masked_phone': masked_phone,
            'masked_email': masked_email,
        })
    except Exception as e:
        logger.error(f"❌ خطأ في جلب طرق التحقق: {e}")
        return jsonify({'success': False, 'error': 'خطأ في الخادم'}), 500


# ==================== Phone Verification ====================

@auth_bp.route('/verify-phone-token', methods=['POST'])
def verify_phone_token():
    """التحقق من رمز الهاتف وتحديث حالة المستخدم"""
    try:
        data = request.get_json()
        
        id_token = data.get('idToken')
        user_id = data.get('userId')  # اختياري، لتحديث مستخدم موجود
        
        if not id_token:
            return jsonify({'success': False, 'error': 'Token مطلوب'}), 400
            
        if not sms_service:
            return jsonify({'success': False, 'error': 'خدمة SMS غير متاحة'}), 503
            
        # التحقق من التوكن
        success, result = sms_service.verify_phone_token(id_token)
        
        if success:
            phone_number = result['phone_number']
            firebase_uid = result['uid']
            
            # إذا تم تمرير user_id، قم بتحديث حالته
            if user_id:
                sms_service.update_user_verification_status(user_id, phone_number)
                return jsonify({
                    'success': True,
                    'message': 'تم التحقق من الهاتف بنجاح',
                    'phone_number': phone_number,
                    'verified': True
                })
            else:
                # حالة تسجيل جديد أو تحقق عام
                return jsonify({
                    'success': True,
                    'message': 'رمز التحقق صحيح',
                    'phone_number': phone_number,
                    'firebase_uid': firebase_uid
                })
        else:
            return jsonify({'success': False, 'error': result.get('error', 'فشل التحقق')}), 400
            
    except Exception as e:
        log_error(f"خطأ في verify-phone-token: {e}")
        return jsonify({'success': False, 'error': 'خطأ في الخادم'}), 500


# ==================== Session Routes ====================

@auth_bp.route('/validate-session', methods=['GET'])
def validate_session():
    """التحقق من صحة الجلسة الحالية"""
    try:
        # الحصول على Token من Header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'message': 'لا يوجد token'
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # فك تشفير Token والتحقق منه
        import os
        jwt_secret = os.getenv('JWT_SECRET_KEY')
        if not jwt_secret:
            return jsonify({'success': False, 'message': 'Server configuration error'}), 500
        from ..utils.jwt_manager import JWTManager
        jwt_manager = JWTManager(secret_key=jwt_secret)
        payload = jwt_manager.verify_token(token)
        
        if not payload:
            return jsonify({
                'success': False,
                'message': 'Token غير صالح'
            }), 401
        
        # التحقق من وجود المستخدم في قاعدة البيانات
        user_id = payload.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'Token غير صالح'
            }), 401
        
        with db_manager.get_connection() as conn:
            user = conn.execute("""
                SELECT id, username, email, user_type
                FROM users
                WHERE id = ?
            """, (user_id,)).fetchone()
            
            if not user:
                return jsonify({
                    'success': False,
                    'message': 'المستخدم غير موجود'
                }), 401
        
        return jsonify({
            'success': True,
            'message': 'الجلسة صالحة',
            'user': {
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'user_type': user[3]
            }
        })
    
    except Exception as e:
        log_error(f"خطأ في التحقق من الجلسة: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'خطأ في التحقق من الجلسة'
        }), 500

@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """تحديث التوكن باستخدام refresh_token"""
    try:
        data = request.get_json(force=True) or {}
        refresh_token_str = data.get('refresh_token')
        
        # محاولة الحصول على refresh_token من Authorization header
        if not refresh_token_str:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                refresh_token_str = auth_header.split(' ')[1]
        
        if not refresh_token_str:
            return jsonify({
                'success': False,
                'error': 'refresh_token مطلوب'
            }), 400
        
        # فك تشفير refresh_token والتحقق منه
        import os
        jwt_secret = os.getenv('JWT_SECRET_KEY')
        if not jwt_secret:
            return jsonify({'success': False, 'error': 'Server configuration error'}), 500
        from ..utils.jwt_manager import JWTManager
        jwt_manager = JWTManager(secret_key=jwt_secret)
        payload = jwt_manager.verify_token(refresh_token_str)
        
        if not payload:
            return jsonify({
                'success': False,
                'error': 'refresh_token غير صالح'
            }), 401
        
        # التحقق من وجود المستخدم
        user_id = payload.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'refresh_token غير صالح'
            }), 401
        
        with db_manager.get_connection() as conn:
            user = conn.execute("""
                SELECT id, username, email, user_type
                FROM users
                WHERE id = ?
            """, (user_id,)).fetchone()
            
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'المستخدم غير موجود'
                }), 401
        
        # توليد توكن جديد
        if TOKEN_SYSTEM_AVAILABLE:
            from ..api.token_refresh_endpoint import generate_tokens
            tokens = generate_tokens(user_id, user[1], user[3])
            
            return jsonify({
                'success': True,
                'message': 'تم تحديث التوكن بنجاح',
                'token': tokens.get('access_token'),
                'refresh_token': tokens.get('refresh_token'),
                'expires_in': tokens.get('expires_in', 3600)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'نظام التوكن غير متاح'
            }), 500
    
    except Exception as e:
        logger.error(f"خطأ في تحديث التوكن: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'خطأ في تحديث التوكن'
        }), 500

@auth_bp.route('/logout', methods=['POST'])
def logout_user():
    """تسجيل خروج المستخدم وإبطال Token"""
    try:
        # الحصول على Token من Header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            # محاولة إبطال Token في قاعدة البيانات
            try:
                with db_manager.get_write_connection() as conn:
                    # حذف الجلسة من قاعدة البيانات
                    conn.execute("""
                        DELETE FROM user_sessions 
                        WHERE session_token = ?
                    """, (token,))
            except Exception as db_error:
                log_error(f"خطأ في حذف الجلسة: {db_error}")
        
        return jsonify({
            'success': True,
            'message': 'تم تسجيل الخروج بنجاح'
        })
    
    except Exception as e:
        log_error(f"خطأ في تسجيل الخروج: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'خطأ في تسجيل الخروج'
        }), 500

@auth_bp.route('/delete-account', methods=['DELETE'])
def delete_account():
    """
    حذف حساب المستخدم نهائياً
    
    يتطلب:
    - Authorization header مع Bearer token
    - كلمة المرور للتأكيد
    
    يحذف:
    - جميع بيانات المستخدم من جميع الجداول (CASCADE)
    - الجلسات والتوكنات
    - مفاتيح Binance
    - الصفقات والمحفظة
    """
    try:
        # 1. التحقق من التوكن
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': 'التوكن مطلوب'
            }), 401
        
        token = auth_header.split(' ')[1]
        
        # 2. فك تشفير التوكن للحصول على user_id
        try:
            from backend.api.token_refresh_endpoint import verify_token
            payload = verify_token(token)
            if not payload:
                return jsonify({
                    'success': False,
                    'error': 'التوكن غير صالح أو منتهي'
                }), 401
            user_id = payload.get('user_id')
        except Exception as token_error:
            logger.error(f"خطأ في التحقق من التوكن: {token_error}")
            return jsonify({
                'success': False,
                'error': 'التوكن غير صالح'
            }), 401
        
        # 3. الحصول على البيانات من الطلب
        data = request.get_json(silent=True) or {}
        password = data.get('password')
        confirmation = data.get('confirmation')  # "DELETE" للتأكيد
        
        # 4. التحقق من التأكيد
        if confirmation != "DELETE":
            return jsonify({
                'success': False,
                'error': 'يجب كتابة DELETE للتأكيد'
            }), 400
        
        # 5. التحقق من كلمة المرور
        if not password:
            return jsonify({
                'success': False,
                'error': 'كلمة المرور مطلوبة للتأكيد'
            }), 400
        
        with db_manager.get_write_connection() as conn:
            cursor = conn.cursor()
            
            # 6. التحقق من صحة كلمة المرور
            cursor.execute("SELECT password_hash, username, email FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'المستخدم غير موجود'
                }), 404
            
            from backend.utils.password_utils import verify_password as _verify_pw
            if not _verify_pw(password, user['password_hash']):
                return jsonify({
                    'success': False,
                    'error': 'كلمة المرور غير صحيحة'
                }), 401
            
            # 7. منع حذف حساب الأدمن الرئيسي
            if user['username'] == 'admin_user' or user['email'] == 'admin@test.com':
                return jsonify({
                    'success': False,
                    'error': 'لا يمكن حذف حساب الأدمن الرئيسي'
                }), 403
            
            # 8. تفعيل المفاتيح الأجنبية
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # 9. حذف المستخدم (CASCADE سيحذف جميع البيانات المرتبطة)
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            
            logger.info(f"✅ تم حذف حساب المستخدم {user_id} ({user['username']}) نهائياً")
            
            return jsonify({
                'success': True,
                'message': 'تم حذف حسابك نهائياً. نأسف لرؤيتك تغادر.'
            })
    
    except Exception as e:
        logger.error(f"❌ خطأ في حذف الحساب: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'حدث خطأ أثناء حذف الحساب'
        }), 500


if __name__ == "__main__":
    print("🔐 نقاط النهاية للمصادقة جاهزة")
    print("المسارات المتاحة:")
    print("- POST /api/auth/register")
    print("- POST /api/auth/verify-email") 
    print("- POST /api/auth/resend-otp")
    print("- POST /api/auth/login")
    print("- POST /api/auth/logout")
    print("- POST /api/auth/forgot-password")
    print("- POST /api/auth/reset-password")
    print("- DELETE /api/auth/delete-account")
