"""
Simple Email OTP Service - خدمة OTP بسيطة للإيميل
تستخدم verification_codes جدول قاعدة البيانات
"""

import random
import string
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database.database_manager import DatabaseManager

class SimpleEmailOTPService:
    """خدمة OTP بسيطة - تحفظ في قاعدة البيانات فقط"""
    
    def __init__(self):
        self.db = DatabaseManager()
        # ✅ تنظيف تلقائي عند التهيئة
        self._cleanup_expired_otps()
    
    def generate_otp_code(self, length=6):
        """توليد رمز OTP عشوائي"""
        return ''.join(random.choices(string.digits, k=length))
    
    def can_send_otp(self, email: str, purpose: str = 'password_reset', cooldown_minutes: int = 2) -> tuple:
        """
        ✅ FIX: التحقق مما إذا كان يمكن إرسال OTP جديد
        يمنع الإرسال المتكرر خلال فترة قصيرة
        
        Returns:
            (can_send: bool, wait_seconds: int or None)
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT created_at FROM verification_codes
                    WHERE email = ? AND purpose = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (email.lower(), purpose))
                
                result = cursor.fetchone()
                
                if not result:
                    return True, None
                
                # حساب الوقت المتبقي
                created_at_str = result[0]
                try:
                    created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                except Exception:
                    return True, None
                
                time_since = (datetime.now() - created_at).total_seconds()
                cooldown_seconds = cooldown_minutes * 60
                
                if time_since < cooldown_seconds:
                    wait_seconds = int(cooldown_seconds - time_since)
                    return False, wait_seconds
                
                return True, None
                
        except Exception as e:
            print(f"❌ خطأ في فحص can_send_otp: {e}")
            return True, None  # السماح في حالة الخطأ
    
    def send_email_otp(self, email, purpose='password_reset'):
        """
        إرسال OTP للإيميل
        في الواقع: فقط حفظ في قاعدة البيانات
        المستخدم يمكنه رؤية الرمز في logs أو database
        """
        try:
            # ✅ تنظيف OTPs منتهية قبل الإرسال
            self._cleanup_expired_otps()
            
            # توليد رمز OTP
            otp_code = self.generate_otp_code()
            
            # حفظ في قاعدة البيانات
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                
                # حذف أي رموز قديمة لنفس الإيميل
                cursor.execute("""
                    DELETE FROM verification_codes 
                    WHERE email = ? AND purpose = ?
                """, (email.lower(), purpose))
                
                # إضافة الرمز الجديد
                expires_at = datetime.now() + timedelta(minutes=10)
                expires_timestamp = expires_at.timestamp()
                cursor.execute("""
                    INSERT INTO verification_codes (
                        email, otp_code, purpose, expires_at, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    email.lower(),
                    otp_code,
                    purpose,
                    expires_timestamp,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
            
            # إرسال البريد الإلكتروني
            email_sent = self._send_email(email, otp_code, purpose)
            
            # طباعة الرمز في Logs (للتطوير)
            print(f"""
╔════════════════════════════════════════╗
║        OTP Code for {email[:20]}       
║                                        
║        Code: {otp_code}                
║        Purpose: {purpose}              
║        Valid for: 10 minutes           
║        Email Sent: {'✅' if email_sent else '❌'}
╚════════════════════════════════════════╝
            """)
            
            return True, otp_code
            
        except Exception as e:
            print(f"❌ خطأ في إرسال OTP: {e}")
            return False, None
    
    def _cleanup_expired_otps(self):
        """
        ✅ تنظيف OTPs المنتهية والمستخدمة
        يُستدعى تلقائياً عند التهيئة وقبل الإرسال
        """
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                
                # حذف OTPs المنتهية
                cursor.execute("""
                    DELETE FROM verification_codes 
                    WHERE expires_at < ?
                """, (datetime.now().timestamp(),))
                
                deleted_expired = cursor.rowcount
                
                # حذف OTPs المستخدمة والقديمة (أكثر من 24 ساعة)
                yesterday = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("""
                    DELETE FROM verification_codes 
                    WHERE verified = TRUE AND verified_at < ?
                """, (yesterday,))
                
                deleted_verified = cursor.rowcount
                
                # حذف OTPs الفاشلة (attempts >= 5)
                cursor.execute("""
                    DELETE FROM verification_codes 
                    WHERE attempts >= 5
                """)
                
                deleted_failed = cursor.rowcount
                
                if deleted_expired + deleted_verified + deleted_failed > 0:
                    print(f"🧹 OTP Cleanup: منتهية={deleted_expired}, مستخدمة={deleted_verified}, فاشلة={deleted_failed}")
                
                return True
        except Exception as e:
            print(f"❌ خطأ في cleanup OTPs: {e}")
            return False
    
    def cancel_otp(self, email: str, purpose: str = 'password_reset') -> bool:
        """
        ✅ إلغاء OTP نشط (للمستخدم الذي يريد الإلغاء)
        """
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM verification_codes 
                    WHERE email = ? AND purpose = ?
                """, (email.lower(), purpose))
                
                deleted = cursor.rowcount > 0
                if deleted:
                    print(f"🗑️ تم إلغاء OTP للإيميل {email} ({purpose})")
                
                return deleted
        except Exception as e:
            print(f"❌ خطأ في إلغاء OTP: {e}")
            return False
    
    def verify_email_otp(self, email, code):
        """التحقق من صحة رمز OTP"""
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                
                # البحث عن الرمز
                cursor.execute("""
                    SELECT otp_code, expires_at, attempts, verified
                    FROM verification_codes
                    WHERE email = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (email.lower(),))
                
                result = cursor.fetchone()
                
                if not result:
                    return False, {'error': 'رمز التحقق غير صحيح'}
                
                stored_code, expires_at, attempts, verified = result
                
                # ✅ FIX: التحقق من أن الرمز لم يُستخدم مسبقاً
                if verified:
                    return False, {'error': 'رمز التحقق مستخدم مسبقاً'}
                
                # التحقق من انتهاء الصلاحية (expires_at هو timestamp)
                if datetime.now().timestamp() > expires_at:
                    return False, {'error': 'انتهت صلاحية رمز التحقق'}
                
                # ✅ CRITICAL FIX: التحقق من صحة الرمز أولاً
                if stored_code != code:
                    # عدد المحاولات الحالي
                    current_attempts = attempts if attempts else 0
                    
                    # تحديث عدد المحاولات
                    cursor.execute("""
                        UPDATE verification_codes
                        SET attempts = attempts + 1
                        WHERE email = ? AND otp_code = ?
                    """, (email.lower(), stored_code))
                    
                    # التحقق من تجاوز الحد بعد الزيادة
                    if current_attempts + 1 >= 5:
                        return False, {'error': 'تجاوزت الحد الأقصى للمحاولات', 'remaining_attempts': 0}
                    
                    remaining = 5 - (current_attempts + 1)
                    return False, {'error': 'رمز التحقق غير صحيح', 'remaining_attempts': remaining}
                
                # ✅ التحقق ناجح - تعيين verified = TRUE بدلاً من الحذف
                cursor.execute("""
                    UPDATE verification_codes
                    SET verified = TRUE, verified_at = ?
                    WHERE email = ? AND otp_code = ?
                """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), email.lower(), code))
                
                return True, {'message': 'تم التحقق بنجاح'}
                
        except Exception as e:
            print(f"❌ خطأ في التحقق من OTP: {e}")
            return False, {'error': 'خطأ في التحقق'}
    
    def _send_email(self, email: str, otp_code: str, purpose: str) -> bool:
        """إرسال البريد الإلكتروني عبر SMTP"""
        try:
            smtp_enabled = os.getenv('SMTP_ENABLED', 'True').lower() == 'true'
            if not smtp_enabled:
                print("⚠️ SMTP disabled")
                return False
            
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_username = os.getenv('SMTP_USERNAME', '')
            smtp_password = os.getenv('SMTP_PASSWORD', '')
            smtp_from = os.getenv('SMTP_FROM_EMAIL', smtp_username)
            
            if not smtp_username or not smtp_password:
                print("⚠️ SMTP credentials not configured")
                return False
            
            msg = MIMEMultipart('alternative')
            msg['From'] = smtp_from
            msg['To'] = email
            
            if purpose == 'password_reset':
                msg['Subject'] = 'رمز إعادة تعيين كلمة المرور - Trading Bot'
                body = f"""
                <html>
                <body dir="rtl" style="font-family: Arial, sans-serif; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background: #f5f5f5; padding: 30px; border-radius: 10px;">
                        <h2 style="color: #2196F3; text-align: center;">إعادة تعيين كلمة المرور</h2>
                        <p style="font-size: 16px;">رمز التحقق الخاص بك هو:</p>
                        <div style="background: white; padding: 20px; text-align: center; border-radius: 5px; margin: 20px 0;">
                            <h1 style="color: #2196F3; font-size: 36px; letter-spacing: 8px; margin: 0;">{otp_code}</h1>
                        </div>
                        <p style="color: #666;">هذا الرمز صالح لمدة <strong>10 دقائق</strong> فقط.</p>
                        <p style="color: #999; font-size: 14px;">إذا لم تطلب إعادة تعيين كلمة المرور، يرجى تجاهل هذه الرسالة.</p>
                    </div>
                </body>
                </html>
                """
            else:
                msg['Subject'] = 'رمز التحقق - Trading Bot'
                body = f"""
                <html>
                <body dir="rtl" style="font-family: Arial, sans-serif; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background: #f5f5f5; padding: 30px; border-radius: 10px;">
                        <h2 style="color: #4CAF50; text-align: center;">تحقق من بريدك الإلكتروني</h2>
                        <p style="font-size: 16px;">رمز التحقق الخاص بك هو:</p>
                        <div style="background: white; padding: 20px; text-align: center; border-radius: 5px; margin: 20px 0;">
                            <h1 style="color: #4CAF50; font-size: 36px; letter-spacing: 8px; margin: 0;">{otp_code}</h1>
                        </div>
                        <p style="color: #666;">هذا الرمز صالح لمدة <strong>10 دقائق</strong> فقط.</p>
                    </div>
                </body>
                </html>
                """
            
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            print(f"✅ تم إرسال OTP إلى {email}")
            return True
            
        except Exception as e:
            print(f"❌ فشل إرسال البريد: {e}")
            return False
