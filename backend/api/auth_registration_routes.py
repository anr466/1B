#!/usr/bin/env python3
"""
Registration Routes — extracted from auth_endpoints.py (God Object split)
=========================================================================
Routes: check-availability, send-registration-otp, register,
        verify-registration-otp, register-with-phone
"""

import time
import re
import bcrypt
from flask import request, jsonify

from config.logging_config import get_logger

logger = get_logger(__name__)


def register_registration_routes(bp, shared):
    """Register all registration-related routes on the auth blueprint.
    
    Args:
        bp: Flask Blueprint (auth_bp)
        shared: dict with shared services
    """
    db_manager = shared['db_manager']
    otp_service = shared['otp_service']
    sms_service = shared['sms_service']
    security_audit = shared['security_audit']
    validate_email = shared['validate_email']
    validate_password = shared['validate_password']
    validate_username = shared['validate_username']
    validate_phone = shared['validate_phone']
    normalize_username = shared['normalize_username']
    sanitize_input = shared['sanitize_input']
    get_request_info = shared['get_request_info']
    TOKEN_SYSTEM_AVAILABLE = shared['TOKEN_SYSTEM_AVAILABLE']
    generate_tokens = shared.get('generate_tokens')
    prevent_concurrent_duplicates = shared['prevent_concurrent_duplicates']
    require_idempotency = shared['require_idempotency']

    try:
        from utils.error_handler import log_error
    except ImportError:
        def log_error(message):
            pass

    @bp.route('/check-availability', methods=['POST'])
    def check_availability():
        """فحص توفر البريد الإلكتروني واسم المستخدم ورقم الجوال - مع Rate Limiting"""
        try:
            data = request.get_json(force=True) or {}
            email = (data.get('email') or '').strip().lower()
            username = (data.get('username') or '').strip().lower()
            phone = (data.get('phone') or '').strip()
            
            if not email and not username and not phone:
                return jsonify({'success': False, 'error': 'يجب توفير البريد أو اسم المستخدم أو رقم الجوال'}), 400
            
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            
            try:
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT COUNT(*) FROM activity_log 
                        WHERE action = 'availability_check' 
                        AND ip_address = ? 
                        AND created_at > datetime('now', '-1 minute')
                    """, (client_ip,))
                    request_count = cursor.fetchone()[0]
                    
                    if request_count >= 30:
                        logger.warning(f"⚠️ Rate limit exceeded for IP: {client_ip}")
                        return jsonify({
                            'success': False, 
                            'error': 'تم تجاوز الحد المسموح. الرجاء الانتظار.',
                            'code': 'RATE_LIMIT'
                        }), 429
                    
            except Exception as rate_err:
                logger.warning(f"⚠️ Rate limiting check failed: {rate_err}")
            
            try:
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    email_available = True
                    username_available = True
                    phone_available = True
                    
                    if email:
                        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                        if cursor.fetchone():
                            email_available = False
                    
                    if username:
                        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                        if cursor.fetchone():
                            username_available = False
                    
                    if phone:
                        cursor.execute("SELECT id FROM users WHERE phone_number = ?", (phone,))
                        if cursor.fetchone():
                            phone_available = False
                    
                    return jsonify({
                        'success': True,
                        'emailAvailable': email_available,
                        'usernameAvailable': username_available,
                        'phoneAvailable': phone_available,
                        'email_available': email_available,
                        'username_available': username_available,
                        'phone_available': phone_available,
                        'message': 'تم التحقق من التوفر بنجاح'
                    }), 200
            except Exception as e:
                logger.error(f"❌ خطأ في فحص التوفر: {e}")
                return jsonify({'success': False, 'error': 'خطأ في فحص التوفر'}), 500
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الطلب: {e}")
            return jsonify({'success': False, 'error': 'خطأ في معالجة الطلب'}), 500

    @bp.route('/send-registration-otp', methods=['POST'])
    def send_registration_otp():
        """إرسال OTP للتسجيل (بدون إنشاء حساب) - مع Rate Limiting ودعم SMS/Email"""
        try:
            data = request.get_json(force=True)
            email = data.get('email', '').strip().lower()
            phone = data.get('phone', '').strip()
            method = data.get('method', 'sms')
            
            if not email:
                return jsonify({'success': False, 'error': 'البريد الإلكتروني مطلوب'}), 400
            
            if not validate_email(email):
                return jsonify({'success': False, 'error': 'البريد الإلكتروني غير صحيح'}), 400
            
            if method == 'sms' and not phone:
                method = 'email'
            
            try:
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                    if cursor.fetchone():
                        return jsonify({'success': False, 'error': 'البريد الإلكتروني مسجل مسبقاً'}), 409
            except Exception as e:
                logger.error(f"❌ خطأ في فحص البريد: {e}")
                return jsonify({'success': False, 'error': 'خطأ في التحقق'}), 500
            
            if otp_service:
                try:
                    target = email if method == 'email' else phone
                    
                    can_send, cooldown_msg = otp_service.can_send_otp(target)
                    if not can_send:
                        return jsonify({
                            'success': False,
                            'error': cooldown_msg,
                            'code': 'COOLDOWN'
                        }), 429
                    
                    success, otp_code = otp_service.send_email_otp(email)
                    if not success:
                        return jsonify({'success': False, 'error': 'فشل في إرسال رمز التحقق'}), 500
                    
                    if method == 'sms' and phone:
                        sms_sent = False
                        if sms_service:
                            try:
                                message = f"رمز تفعيل الحساب: {otp_code}\nصالح لمدة 5 دقائق"
                                sms_service.send_sms(phone, message)
                                sms_sent = True
                                logger.info(f"📱 تم إرسال OTP تسجيل عبر SMS إلى {phone}")
                            except Exception as sms_err:
                                logger.warning(f"⚠️ فشل إرسال SMS: {sms_err}")
                        if not sms_sent:
                            logger.info(f"📱 [DEV] OTP تسجيل: sent")
                        
                        masked_target = phone[:4] + '****' + phone[-2:] if len(phone) > 6 else phone
                    else:
                        logger.info(f"📧 تم إرسال OTP تسجيل عبر Email إلى {email}")
                        masked_target = email[:2] + '***@' + email.split('@')[1] if '@' in email else email
                    
                    return jsonify({
                        'success': True,
                        'message': f'تم إرسال رمز التحقق إلى {"هاتفك" if method == "sms" else "بريدك الإلكتروني"}',
                        'method': method,
                        'masked_target': masked_target,
                        'expires_in': 300
                    }), 200
                except Exception as e:
                    logger.error(f"❌ خطأ في إرسال OTP: {e}")
                    return jsonify({'success': False, 'error': 'فشل في إرسال رمز التحقق'}), 500
            else:
                logger.error("❌ خدمة OTP غير متاحة")
                return jsonify({'success': False, 'error': 'خدمة التحقق غير متاحة'}), 503
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الطلب: {e}")
            return jsonify({'success': False, 'error': 'خطأ في معالجة الطلب'}), 500

    @bp.route('/register', methods=['POST'])
    @prevent_concurrent_duplicates
    @require_idempotency('user_register', require_user_id=False)
    def register_user():
        """تسجيل مستخدم جديد (دعم الهاتف والإيميل)"""
        try:
            try:
                data = request.get_json(force=True)
            except Exception as json_error:
                return jsonify({'success': False, 'error': 'JSON غير صحيح', 'code': 'INVALID_JSON'}), 400
            
            if not data:
                return jsonify({'success': False, 'error': 'لا توجد بيانات'}), 400
            
            logger.info(f"📥 طلب تسجيل مستخدم جديد - البيانات المستلمة: {list(data.keys())}")
            
            email_check = data.get('email', '').strip().lower()
            if email_check:
                try:
                    with db_manager.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM users WHERE email = ?", (email_check,))
                        existing = cursor.fetchone()
                        if existing:
                            logger.info(f"⚠️ المستخدم موجود مسبقاً: {email_check} - توجيه لتسجيل الدخول")
                            return jsonify({
                                'success': False, 
                                'error': 'البريد الإلكتروني مسجل مسبقاً. يرجى تسجيل الدخول.',
                                'code': 'USER_EXISTS',
                                'action': 'login'
                            }), 409
                except Exception as check_err:
                    logger.error(f"خطأ في فحص المستخدم: {check_err}")
            
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
            username = data.get('username', '').strip()
            full_name = data.get('fullName') or data.get('full_name', '').strip()
            phone_number = data.get('phoneNumber') or data.get('phone_number') or data.get('phone')
            id_token = data.get('idToken')
            verification_method = data.get('verificationMethod', 'email')
            
            logger.info(f"📧 Email: {email}, Username: {username}, Name: {full_name}, Phone: {phone_number}, Method: {verification_method}")
            
            if not email or not password or not username:
                logger.error(f"❌ بيانات ناقصة - Email: {'✓' if email else '✗'}, Password: {'✓' if password else '✗'}, Username: {'✓' if username else '✗'}")
                return jsonify({'success': False, 'error': 'الإيميل وكلمة المرور واسم المستخدم مطلوبين'}), 400
            
            if not full_name:
                logger.error(f"❌ الاسم الكامل مطلوب")
                return jsonify({'success': False, 'error': 'الاسم الكامل مطلوب'}), 400
            
            if not validate_email(email):
                logger.error(f"❌ بريد إلكتروني غير صحيح: {email}")
                return jsonify({'success': False, 'error': 'البريد الإلكتروني غير صحيح', 'code': 'INVALID_EMAIL'}), 400
            
            if not validate_password(password):
                logger.error(f"❌ كلمة مرور ضعيفة - الطول: {len(password)}")
                return jsonify({'success': False, 'error': 'كلمة المرور يجب أن تكون 8 أحرف على الأقل وتحتوي على حروف كبيرة وصغيرة وأرقام', 'code': 'WEAK_PASSWORD'}), 400
            
            if not validate_username(username):
                logger.error(f"❌ اسم مستخدم غير صحيح: {username} - الطول: {len(username)}")
                return jsonify({'success': False, 'error': 'اسم المستخدم يجب أن يكون بين 3 و 50 حرف (أحرف إنجليزية وأرقام فقط)'}), 400
            
            is_phone_verified = False
            if id_token and sms_service:
                success, result = sms_service.verify_phone_token(id_token, phone_number)
                if success:
                    is_phone_verified = True
                    phone_number = result['phone_number']
                    logger.info(f"✅ تم التحقق من هاتف المستخدم الجديد: {phone_number}")
                else:
                    logger.warning(f"⚠️ فشل التحقق من هاتف المستخدم الجديد: {result.get('error')}")
                    return jsonify({'success': False, 'error': f"فشل التحقق من الهاتف: {result.get('error')}"}), 400

            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            user_id = None
            is_verified = 1 if is_phone_verified else 0
            
            try:
                with db_manager.get_write_connection() as conn:
                    cursor = conn.cursor()
                    
                    try:
                        cursor.execute("SELECT id FROM users WHERE email = ? OR username = ?", (email, username))
                        if cursor.fetchone():
                            conn.rollback()
                            return jsonify({'success': False, 'error': 'المستخدم موجود مسبقاً'}), 409
                        
                        cursor.execute("""
                            INSERT INTO users (username, email, password_hash, phone_number, name, email_verified, 
                                is_phone_verified, preferred_verification_method, created_at, user_type)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'user')
                        """, (username, email, password_hash, phone_number, full_name, is_verified, 1 if is_phone_verified else 0, verification_method))
                        
                        user_id = cursor.lastrowid
                        logger.info(f"🔹 User ID created: {user_id}")
                        
                        cursor.execute("""
                            INSERT INTO user_settings (user_id, is_demo, trading_enabled, trade_amount, 
                                stop_loss_pct, take_profit_pct, max_positions, risk_level, 
                                max_daily_loss_pct, trading_mode)
                            VALUES (?, 0, 0, 100.0, 2.0, 5.0, 5, 'medium', 10.0, 'auto')
                        """, (user_id,))
                        
                        cursor.execute("""
                            INSERT INTO portfolio (user_id, total_balance, available_balance, 
                                invested_balance, total_profit_loss, total_profit_loss_percentage, is_demo)
                            VALUES (?, 0.0, 0.0, 0.0, 0.0, 0.0, 0)
                        """, (user_id,))
                        
                        cursor.execute("""
                            INSERT INTO user_onboarding (user_id, step, shown_at)
                            VALUES (?, 'welcome', datetime('now'))
                        """, (user_id,))
                        
                        cursor.execute("""
                            INSERT INTO user_notification_settings (
                                user_id, trade_notifications, price_alerts, system_notifications,
                                marketing_notifications, push_enabled, email_enabled, sms_enabled,
                                notify_new_deal, notify_deal_profit, notify_deal_loss,
                                notify_daily_profit, notify_daily_loss, notify_low_balance
                            ) VALUES (?, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1)
                        """, (user_id,))
                        
                        conn.commit()
                        logger.info(f"✅ Database commit successful for user {user_id}")
                        
                    except Exception as transaction_error:
                        conn.rollback()
                        logger.error(f"❌ Transaction error, rollback executed: {transaction_error}")
                        return jsonify({'success': False, 'error': 'فشل في إنشاء الحساب'}), 500
                
                otp_sent = False
                if not is_phone_verified and otp_service:
                    try:
                        otp_sent, otp_code = otp_service.send_email_otp(email)
                        if otp_sent:
                            logger.info(f"✅ تم إرسال OTP إلى {email}")
                    except Exception as otp_error:
                        logger.warning(f"⚠️ فشل إرسال OTP (المستخدم موجود في DB): {otp_error}")
                
                if security_audit and user_id:
                    try:
                        ip, user_agent = get_request_info()
                        security_audit.log_action(
                            action='REGISTER',
                            user_id=user_id,
                            resource=email,
                            ip_address=ip,
                            user_agent=user_agent,
                            status='success',
                            details={'username': username, 'verification_method': verification_method}
                        )
                    except Exception as audit_error:
                        logger.warning(f"⚠️ فشل تسجيل العملية الأمنية (المستخدم موجود في DB): {audit_error}")
                
                if TOKEN_SYSTEM_AVAILABLE and user_id and generate_tokens:
                    tokens = generate_tokens(user_id, username, 'user')
                    
                    return jsonify({
                        'success': True,
                        'token': tokens['access_token'],
                        'refresh_token': tokens['refresh_token'],
                        'user': {
                            'id': user_id,
                            'username': username,
                            'email': email,
                            'phone_number': phone_number,
                            'user_type': 'user',
                            'email_verified': bool(is_verified),
                            'phone_verified': bool(is_phone_verified)
                        },
                        'message': 'تم إنشاء الحساب بنجاح'
                    })
                else:
                    return jsonify({
                        'success': True,
                        'user_id': user_id,
                        'message': 'تم إنشاء الحساب بنجاح'
                    })
            
            except Exception as db_error:
                logger.error(f"❌ خطأ قاعدة البيانات: {db_error}")
                return jsonify({'success': False, 'error': 'خطأ في قاعدة البيانات'}), 500
                
        except Exception as e:
            log_error(f"خطأ عام: {str(e)}")
            return jsonify({'success': False, 'error': 'خطأ في الخادم'}), 500

    @bp.route('/verify-registration-otp', methods=['POST'])
    def verify_registration_otp():
        """التحقق من OTP وإنشاء الحساب - مع تحقق شامل"""
        try:
            data = request.get_json(force=True)
            email = data.get('email', '').strip().lower()
            otp_code = data.get('otp_code', '').strip()
            username = normalize_username(data.get('username', ''))
            password = data.get('password', '')
            phone_number = data.get('phone') or data.get('phoneNumber')
            full_name = sanitize_input(data.get('fullName') or data.get('full_name', ''))
            
            if not email or not otp_code or not username or not password:
                return jsonify({'success': False, 'error': 'بيانات ناقصة'}), 400
            
            if not validate_email(email):
                return jsonify({'success': False, 'error': 'البريد الإلكتروني غير صحيح'}), 400
            
            if not validate_username(username):
                return jsonify({'success': False, 'error': 'اسم المستخدم يجب أن يكون 3-50 حرف (أحرف إنجليزية وأرقام فقط)'}), 400
            
            if not validate_password(password):
                return jsonify({'success': False, 'error': 'كلمة المرور يجب أن تكون 8 أحرف على الأقل وتحتوي على حروف كبيرة وصغيرة وأرقام'}), 400
            
            if phone_number and not validate_phone(phone_number):
                return jsonify({'success': False, 'error': 'رقم الهاتف غير صحيح'}), 400
            
            if otp_service:
                try:
                    verified, result = otp_service.verify_email_otp(email, otp_code)
                    if not verified:
                        error_msg = result.get('error', 'رمز التحقق غير صحيح')
                        remaining = result.get('remaining_attempts')
                        response = {'success': False, 'error': error_msg}
                        if remaining is not None:
                            response['remaining_attempts'] = remaining
                        return jsonify(response), 400
                except Exception as e:
                    logger.error(f"❌ خطأ في التحقق من OTP: {e}")
                    return jsonify({'success': False, 'error': 'رمز التحقق غير صحيح'}), 400
            else:
                logger.error("❌ خدمة OTP غير متاحة")
                return jsonify({'success': False, 'error': 'خدمة التحقق غير متاحة'}), 503
            
            user_id = None
            try:
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                with db_manager.get_write_connection() as conn:
                    cursor = conn.cursor()
                    
                    try:
                        cursor.execute("SELECT id FROM users WHERE email = ? OR LOWER(username) = ?", (email, username))
                        if cursor.fetchone():
                            conn.rollback()
                            return jsonify({'success': False, 'error': 'المستخدم موجود مسبقاً'}), 409
                        
                        cursor.execute("""
                            INSERT INTO users (username, email, password_hash, phone_number, name, email_verified, 
                                is_phone_verified, preferred_verification_method, created_at, user_type)
                            VALUES (?, ?, ?, ?, ?, 1, 0, 'email', datetime('now'), 'user')
                        """, (username, email, password_hash, phone_number, full_name))
                        
                        user_id = cursor.lastrowid
                        logger.info(f"🔹 User ID created via OTP: {user_id}")
                        
                        cursor.execute("""
                            INSERT INTO user_settings (user_id, is_demo, trading_enabled, trade_amount, 
                                stop_loss_pct, take_profit_pct, max_positions, risk_level, 
                                max_daily_loss_pct, trading_mode)
                            VALUES (?, 0, 0, 100.0, 2.0, 5.0, 5, 'medium', 10.0, 'auto')
                        """, (user_id,))
                        
                        cursor.execute("""
                            INSERT INTO portfolio (user_id, total_balance, available_balance, 
                                invested_balance, total_profit_loss, total_profit_loss_percentage, is_demo)
                            VALUES (?, 0.0, 0.0, 0.0, 0.0, 0.0, 0)
                        """, (user_id,))
                        
                        cursor.execute("""
                            INSERT INTO user_onboarding (user_id, step, shown_at)
                            VALUES (?, 'welcome', datetime('now'))
                        """, (user_id,))
                        
                        cursor.execute("""
                            INSERT INTO user_notification_settings (
                                user_id, trade_notifications, price_alerts, system_notifications,
                                marketing_notifications, push_enabled, email_enabled, sms_enabled,
                                notify_new_deal, notify_deal_profit, notify_deal_loss,
                                notify_daily_profit, notify_daily_loss, notify_low_balance
                            ) VALUES (?, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1)
                        """, (user_id,))
                        
                        cursor.execute("""
                            DELETE FROM verification_codes 
                            WHERE email = ? AND purpose = 'registration'
                        """, (email,))
                        
                        conn.commit()
                        logger.info(f"✅ Database commit successful for user {user_id} via OTP")
                        
                    except Exception as e:
                        conn.rollback()
                        logger.error(f"❌ Transaction error in OTP registration: {e}")
                        return jsonify({'success': False, 'error': 'خطأ في إنشاء الحساب'}), 500
                
                logger.info(f"✅ تم إنشاء مستخدم جديد: {email}")
                
                if TOKEN_SYSTEM_AVAILABLE and user_id and generate_tokens:
                    tokens = generate_tokens(user_id, username, 'user')
                    return jsonify({
                        'success': True,
                        'message': 'تم إنشاء حسابك بنجاح',
                        'user_id': user_id,
                        'access_token': tokens['access_token'],
                        'refresh_token': tokens['refresh_token']
                    }), 201
                else:
                    return jsonify({
                        'success': True,
                        'message': 'تم إنشاء حسابك بنجاح',
                        'user_id': user_id
                    }), 201
                            
            except Exception as e:
                logger.error(f"❌ خطأ داخلي في OTP registration: {e}")
                return jsonify({'success': False, 'error': 'خطأ داخلي في الخادم'}), 500
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الطلب: {e}")
            return jsonify({'success': False, 'error': 'خطأ في معالجة الطلب'}), 500

    @bp.route('/register-with-phone', methods=['POST'])
    def register_with_phone():
        """التسجيل عبر رقم الهاتف (بعد التحقق من Firebase)"""
        try:
            data = request.get_json(force=True)
            phone = data.get('phone', '').strip()
            username = data.get('username', '').strip()
            password = data.get('password', '')
            full_name = data.get('fullName') or data.get('full_name', '')
            email = data.get('email', '').strip().lower() if data.get('email') else None
            firebase_token = data.get('firebaseToken') or data.get('firebase_token')
            
            if not phone or not username or not password:
                return jsonify({'success': False, 'error': 'بيانات ناقصة'}), 400
            
            try:
                password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                with db_manager.get_write_connection() as conn:
                    cursor = conn.cursor()
                    
                    try:
                        cursor.execute("SELECT id FROM users WHERE phone = ? OR username = ?", (phone, username))
                        if cursor.fetchone():
                            conn.rollback()
                            return jsonify({'success': False, 'error': 'رقم الهاتف أو اسم المستخدم مسجل مسبقاً'}), 409
                        
                        cursor.execute("""
                            INSERT INTO users (
                                username, email, phone, password_hash, full_name,
                                is_verified, user_type, is_active, created_at
                            ) VALUES (?, ?, ?, ?, ?, 1, 'user', 1, ?)
                        """, (username, email, phone, password_hash, full_name, 
                              time.strftime('%Y-%m-%d %H:%M:%S')))
                        
                        user_id = cursor.lastrowid
                        
                        cursor.execute("""
                            INSERT OR IGNORE INTO user_settings (user_id, is_demo, trading_enabled)
                            VALUES (?, 1, 0)
                        """, (user_id,))
                        
                        cursor.execute("""
                            INSERT OR IGNORE INTO portfolio 
                            (user_id, total_balance, available_balance, initial_balance, is_demo, updated_at)
                            VALUES (?, 1000.0, 1000.0, 1000.0, 1, CURRENT_TIMESTAMP)
                        """, (user_id,))
                        
                        conn.commit()
                        logger.info(f"✅ تم إنشاء مستخدم جديد عبر الهاتف: {phone}")
                        
                        if generate_tokens:
                            tokens = generate_tokens(user_id, username, 'user')
                        else:
                            tokens = None
                        
                        if tokens:
                            return jsonify({
                                'success': True,
                                'message': 'تم إنشاء حسابك بنجاح',
                                'user_id': user_id,
                                'access_token': tokens['access_token'],
                                'refresh_token': tokens['refresh_token']
                            }), 201
                        else:
                            return jsonify({
                                'success': True,
                                'message': 'تم إنشاء حسابك بنجاح',
                                'user_id': user_id
                            }), 201
                            
                    except Exception as e:
                        conn.rollback()
                        logger.error(f"❌ خطأ في إنشاء المستخدم عبر الهاتف: {e}")
                        return jsonify({'success': False, 'error': 'خطأ في إنشاء الحساب'}), 500
            except Exception as e:
                logger.error(f"❌ خطأ داخلي: {e}")
                return jsonify({'success': False, 'error': 'خطأ داخلي في الخادم'}), 500
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة طلب التسجيل عبر الهاتف: {e}")
            return jsonify({'success': False, 'error': 'خطأ في معالجة الطلب'}), 500
