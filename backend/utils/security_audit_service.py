#!/usr/bin/env python3
"""
🔒 خدمة التسجيل الأمني الموحدة
Security Audit Service - تسجيل جميع العمليات الحساسة

الميزات:
- تسجيل كل عملية حساسة (تسجيل، دخول، تغيير كلمة مرور، إلخ)
- ربط كل عملية بمستخدم
- تسجيل IP و User Agent
- Trace واضح لكل عملية
- لا كشف بيانات حساسة
"""

import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.database_manager import DatabaseManager
from config.logging_config import get_logger

logger = get_logger(__name__)


class SecurityAuditService:
    """خدمة التسجيل الأمني الموحدة"""
    
    # أنواع العمليات المدعومة
    ACTIONS = {
        # المصادقة
        'LOGIN_SUCCESS': 'تسجيل دخول ناجح',
        'LOGIN_FAILED': 'فشل تسجيل الدخول',
        'LOGOUT': 'تسجيل خروج',
        'REGISTER': 'تسجيل حساب جديد',
        
        # كلمة المرور
        'PASSWORD_RESET_REQUEST': 'طلب استعادة كلمة المرور',
        'PASSWORD_RESET_SUCCESS': 'تغيير كلمة المرور بنجاح',
        'PASSWORD_RESET_FAILED': 'فشل تغيير كلمة المرور',
        'PASSWORD_CHANGE': 'تغيير كلمة المرور',
        
        # التحقق
        'EMAIL_VERIFICATION_SENT': 'إرسال رمز التحقق',
        'EMAIL_VERIFIED': 'تم التحقق من البريد',
        'PHONE_VERIFIED': 'تم التحقق من الهاتف',
        'OTP_SENT': 'إرسال OTP',
        'OTP_VERIFIED': 'التحقق من OTP',
        'OTP_FAILED': 'فشل التحقق من OTP',
        
        # الملف الشخصي
        'PROFILE_UPDATE': 'تحديث الملف الشخصي',
        'EMAIL_CHANGE': 'تغيير البريد الإلكتروني',
        'PHONE_CHANGE': 'تغيير رقم الهاتف',
        
        # الأمان
        'BINANCE_KEYS_ADDED': 'إضافة مفاتيح Binance',
        'BINANCE_KEYS_REMOVED': 'حذف مفاتيح Binance',
        'BIOMETRIC_ENABLED': 'تفعيل البصمة',
        'BIOMETRIC_DISABLED': 'تعطيل البصمة',
        
        # الإشعارات
        'FCM_TOKEN_REGISTERED': 'تسجيل FCM Token',
        'FCM_TOKEN_REMOVED': 'حذف FCM Token',
        'NOTIFICATION_SENT': 'إرسال إشعار',
        
        # التداول
        'TRADING_ENABLED': 'تفعيل التداول',
        'TRADING_DISABLED': 'تعطيل التداول',
        'SETTINGS_UPDATED': 'تحديث الإعدادات',
    }
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or DatabaseManager()
    
    def log_action(
        self,
        action: str,
        user_id: Optional[int] = None,
        resource: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = 'success',
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        تسجيل عملية أمنية
        
        Args:
            action: نوع العملية (من ACTIONS)
            user_id: معرف المستخدم (اختياري)
            resource: المورد المتأثر (مثل: email, phone)
            ip_address: عنوان IP
            user_agent: معلومات المتصفح
            status: حالة العملية (success, failed, blocked)
            details: تفاصيل إضافية (بدون بيانات حساسة!)
        
        Returns:
            True إذا تم التسجيل بنجاح
        """
        try:
            # ✅ تنظيف التفاصيل من البيانات الحساسة
            safe_details = self._sanitize_details(details) if details else None
            
            with self.db_manager.get_write_connection() as conn:
                conn.execute("""
                    INSERT INTO security_audit_log 
                    (user_id, action, resource, ip_address, user_agent, status, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    action,
                    resource,
                    ip_address,
                    user_agent[:200] if user_agent else None,  # تقليم User Agent
                    status,
                    str(safe_details) if safe_details else None
                ))
            
            # تسجيل في الـ logger أيضاً
            action_desc = self.ACTIONS.get(action, action)
            log_msg = f"🔒 [{action}] User:{user_id} - {action_desc}"
            if status == 'failed':
                logger.warning(log_msg)
            else:
                logger.info(log_msg)
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في تسجيل العملية الأمنية: {e}")
            return False
    
    def _sanitize_details(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✅ تنظيف التفاصيل من البيانات الحساسة
        لا يتم تسجيل: كلمات المرور، المفاتيح، التوكنات
        """
        sensitive_keys = [
            'password', 'password_hash', 'new_password', 'old_password',
            'api_key', 'api_secret', 'secret', 'token', 'access_token',
            'refresh_token', 'otp', 'otp_code', 'verification_code',
            'fcm_token', 'id_token'
        ]
        
        safe_details = {}
        for key, value in details.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                # إخفاء القيمة الحساسة
                safe_details[key] = '***HIDDEN***'
            else:
                safe_details[key] = value
        
        return safe_details
    
    def get_user_activity(self, user_id: int, limit: int = 50) -> list:
        """جلب سجل نشاط المستخدم"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT action, resource, status, ip_address, created_at
                    FROM security_audit_log
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (user_id, limit))
                
                return [
                    {
                        'action': row[0],
                        'action_desc': self.ACTIONS.get(row[0], row[0]),
                        'resource': row[1],
                        'status': row[2],
                        'ip_address': row[3],
                        'created_at': row[4]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"خطأ في جلب سجل النشاط: {e}")
            return []
    
    def get_failed_login_attempts(self, email: str, minutes: int = 30) -> int:
        """عدد محاولات الدخول الفاشلة في آخر X دقيقة"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM security_audit_log
                    WHERE action = 'LOGIN_FAILED'
                    AND resource = ?
                    AND created_at > datetime('now', '-' || ? || ' minutes')
                """, (email, minutes))
                
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"خطأ في جلب محاولات الدخول الفاشلة: {e}")
            return 0
    
    def is_rate_limited(self, email: str, action: str, max_attempts: int = 5, minutes: int = 15) -> bool:
        """
        ✅ التحقق من Rate Limiting
        يمنع الإرسال المتكرر للـ OTP أو محاولات الدخول
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM security_audit_log
                    WHERE action = ?
                    AND resource = ?
                    AND created_at > datetime('now', '-' || ? || ' minutes')
                """, (action, email, minutes))
                
                count = cursor.fetchone()[0]
                return count >= max_attempts
        except Exception as e:
            logger.error(f"خطأ في فحص Rate Limiting: {e}")
            return False


# Singleton instance
_security_audit_service = None

def get_security_audit_service() -> SecurityAuditService:
    """الحصول على instance وحيد من الخدمة"""
    global _security_audit_service
    if _security_audit_service is None:
        _security_audit_service = SecurityAuditService()
    return _security_audit_service
