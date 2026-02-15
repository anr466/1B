#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔐 Unified OTP Manager - مدير موحد لجميع عمليات OTP
====================================================

مدير شامل لجميع تدفقات OTP في النظام:
- Login OTP
- Registration OTP
- Password Reset OTP
- Email Verification OTP

Features:
- إرسال OTP موحد (email/sms)
- التحقق من OTP موحد
- إعادة إرسال OTP موحد
- إلغاء OTP موحد
- Error handling موحد
- Rate limiting موحد
- Logging موحد
- Cleanup تلقائي

Author: System Unification Team
Date: 2026-02-14
"""

import random
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.logging_config import get_logger
from database.database_manager import DatabaseManager

logger = get_logger(__name__)


class OTPError(Exception):
    """Base exception for OTP errors"""
    pass


class OTPExpiredError(OTPError):
    """OTP has expired"""
    pass


class OTPInvalidError(OTPError):
    """OTP is invalid"""
    pass


class OTPRateLimitError(OTPError):
    """Too many OTP requests"""
    pass


class UnifiedOTPManager:
    """
    مدير موحد لجميع عمليات OTP
    
    Supports:
    - login: OTP لتسجيل الدخول
    - registration: OTP للتسجيل
    - password_reset: OTP لاستعادة كلمة المرور
    - email_verification: OTP للتحقق من الإيميل
    - change_password: OTP لتغيير كلمة المرور
    """
    
    # OTP expiration times (in minutes)
    EXPIRATION_TIMES = {
        'login': 5,
        'registration': 10,
        'password_reset': 15,
        'email_verification': 30,
        'change_password': 10
    }
    
    # Rate limiting (max attempts per time window)
    RATE_LIMITS = {
        'send': (5, 15),  # 5 attempts per 15 minutes
        'verify': (10, 15),  # 10 attempts per 15 minutes
        'resend': (3, 5)  # 3 attempts per 5 minutes
    }
    
    # Error messages
    ERROR_MESSAGES = {
        'INVALID_CODE': 'رمز التحقق غير صحيح',
        'EXPIRED': 'انتهت صلاحية رمز التحقق',
        'TOO_MANY_ATTEMPTS': 'تم تجاوز عدد المحاولات المسموح بها',
        'RATE_LIMITED': 'يرجى الانتظار قبل طلب رمز جديد',
        'SERVICE_UNAVAILABLE': 'خدمة OTP غير متاحة حالياً',
        'NOT_FOUND': 'لم يتم العثور على رمز تحقق نشط',
        'INVALID_PURPOSE': 'نوع العملية غير صحيح'
    }
    
    def __init__(self):
        self.db = DatabaseManager()
        
        # Try to import email service
        try:
            from backend.utils.simple_email_otp_service import SimpleEmailOTPService
            self.email_service = SimpleEmailOTPService()
            self.email_available = True
        except ImportError:
            self.email_service = None
            self.email_available = False
            logger.warning("⚠️ Email OTP service not available")
        
        # Try to import SMS service
        try:
            from utils.firebase_sms_service import FirebaseSMSHandler
            self.sms_service = FirebaseSMSHandler()
            self.sms_available = True
        except ImportError:
            self.sms_service = None
            self.sms_available = False
            logger.warning("⚠️ SMS OTP service not available")
    
    def _generate_otp(self) -> str:
        """توليد OTP من 6 أرقام"""
        return str(random.randint(100000, 999999))
    
    def _mask_identifier(self, identifier: str) -> str:
        """إخفاء جزء من المعرف للخصوصية"""
        if '@' in identifier:
            # Email
            parts = identifier.split('@')
            return f"{parts[0][:2]}***@{parts[1]}"
        elif len(identifier) > 6:
            # Phone
            return f"{identifier[:4]}****{identifier[-2:]}"
        else:
            return f"{identifier[:2]}***"
    
    def _check_rate_limit(self, identifier: str, action: str) -> Tuple[bool, Optional[int]]:
        """
        التحقق من rate limiting
        
        Returns:
            (is_allowed, wait_seconds)
        """
        max_attempts, window_minutes = self.RATE_LIMITS.get(action, (5, 15))
        
        try:
            with self.db.get_connection() as conn:
                # Count attempts in the time window
                cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
                
                result = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM pending_verifications
                    WHERE email = ? 
                    AND created_at > ?
                """, (identifier.lower(), cutoff_time.isoformat())).fetchone()
                
                count = result[0] if result else 0
                
                if count >= max_attempts:
                    # Calculate wait time
                    oldest = conn.execute("""
                        SELECT created_at
                        FROM pending_verifications
                        WHERE email = ?
                        ORDER BY created_at ASC
                        LIMIT 1
                    """, (identifier.lower(),)).fetchone()
                    
                    if oldest:
                        oldest_time = datetime.fromisoformat(oldest[0])
                        wait_until = oldest_time + timedelta(minutes=window_minutes)
                        wait_seconds = int((wait_until - datetime.now()).total_seconds())
                        return False, max(0, wait_seconds)
                
                return True, None
                
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True, None  # Allow on error
    
    def send_otp(
        self, 
        identifier: str, 
        purpose: str, 
        method: str = 'sms',
        additional_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        إرسال OTP موحد
        
        Args:
            identifier: email أو phone number
            purpose: login, registration, password_reset, etc.
            method: sms أو email (الافتراضي: sms)
            additional_data: بيانات إضافية (مثل user_id)
        
        Returns:
            {
                'success': bool,
                'message': str,
                'data': {
                    'masked_target': str,
                    'expires_in': int (seconds),
                    'can_resend_after': int (seconds),
                    'methods_available': list
                },
                'error_code': str (if failed)
            }
        """
        try:
            # Validate purpose
            if purpose not in self.EXPIRATION_TIMES:
                return {
                    'success': False,
                    'error': self.ERROR_MESSAGES['INVALID_PURPOSE'],
                    'error_code': 'INVALID_PURPOSE'
                }
            
            # Check rate limiting
            is_allowed, wait_seconds = self._check_rate_limit(identifier, 'send')
            if not is_allowed:
                return {
                    'success': False,
                    'error': f"{self.ERROR_MESSAGES['RATE_LIMITED']} ({wait_seconds} ثانية)",
                    'error_code': 'RATE_LIMITED',
                    'wait_seconds': wait_seconds
                }
            
            # Generate OTP
            otp_code = self._generate_otp()
            
            # Calculate expiration
            expires_in_minutes = self.EXPIRATION_TIMES[purpose]
            
            # Store in database using email service
            if self.email_available and self.email_service:
                success, result = self.email_service.send_email_otp(
                    identifier.lower(),
                    purpose=purpose
                )
                
                if not success:
                    return {
                        'success': False,
                        'error': self.ERROR_MESSAGES['SERVICE_UNAVAILABLE'],
                        'error_code': 'SERVICE_UNAVAILABLE'
                    }
                
                # Get the OTP code from result
                otp_code = result
            else:
                return {
                    'success': False,
                    'error': self.ERROR_MESSAGES['SERVICE_UNAVAILABLE'],
                    'error_code': 'SERVICE_UNAVAILABLE'
                }
            
            # Send via selected method
            if method == 'sms' and self.sms_available and self.sms_service:
                try:
                    message = f"رمز التحقق: {otp_code}\nصالح لمدة {expires_in_minutes} دقيقة"
                    self.sms_service.send_sms(identifier, message)
                    logger.info(f"📱 OTP sent via SMS to {self._mask_identifier(identifier)}")
                except Exception as sms_error:
                    logger.error(f"SMS send failed: {sms_error}")
                    # Fall back to email
                    method = 'email'
            
            if method == 'email':
                logger.info(f"📧 OTP sent via Email to {self._mask_identifier(identifier)}")
            
            # Log for development
            logger.info(f"🔐 [DEV] OTP for {identifier}: {otp_code}")
            
            return {
                'success': True,
                'message': 'تم إرسال رمز التحقق بنجاح',
                'data': {
                    'masked_target': self._mask_identifier(identifier),
                    'expires_in': expires_in_minutes * 60,
                    'can_resend_after': 60,
                    'methods_available': self._get_available_methods(),
                    'method_used': method
                }
            }
            
        except Exception as e:
            logger.error(f"Send OTP error: {e}")
            return {
                'success': False,
                'error': 'خطأ في إرسال رمز التحقق',
                'error_code': 'INTERNAL_ERROR'
            }
    
    def verify_otp(
        self, 
        identifier: str, 
        otp_code: str, 
        purpose: str
    ) -> Dict[str, Any]:
        """
        التحقق من OTP موحد
        
        Returns:
            {
                'success': bool,
                'verified': bool,
                'message': str,
                'error_code': str (if failed),
                'attempts_remaining': int (if failed)
            }
        """
        try:
            # Check rate limiting
            is_allowed, wait_seconds = self._check_rate_limit(identifier, 'verify')
            if not is_allowed:
                return {
                    'success': False,
                    'verified': False,
                    'error': self.ERROR_MESSAGES['TOO_MANY_ATTEMPTS'],
                    'error_code': 'TOO_MANY_ATTEMPTS',
                    'wait_seconds': wait_seconds
                }
            
            # Verify using email service
            if self.email_available and self.email_service:
                verified, result = self.email_service.verify_email_otp(
                    identifier.lower(),
                    otp_code
                )
                
                if verified:
                    return {
                        'success': True,
                        'verified': True,
                        'message': 'تم التحقق بنجاح'
                    }
                else:
                    # Parse error from result
                    error_msg = result if isinstance(result, str) else self.ERROR_MESSAGES['INVALID_CODE']
                    
                    # Determine error code
                    if 'انتهت' in error_msg or 'expired' in error_msg.lower():
                        error_code = 'EXPIRED'
                    elif 'غير صحيح' in error_msg or 'invalid' in error_msg.lower():
                        error_code = 'INVALID_CODE'
                    else:
                        error_code = 'NOT_FOUND'
                    
                    return {
                        'success': False,
                        'verified': False,
                        'error': error_msg,
                        'error_code': error_code
                    }
            else:
                return {
                    'success': False,
                    'verified': False,
                    'error': self.ERROR_MESSAGES['SERVICE_UNAVAILABLE'],
                    'error_code': 'SERVICE_UNAVAILABLE'
                }
                
        except Exception as e:
            logger.error(f"Verify OTP error: {e}")
            return {
                'success': False,
                'verified': False,
                'error': 'خطأ في التحقق من الرمز',
                'error_code': 'INTERNAL_ERROR'
            }
    
    def resend_otp(
        self, 
        identifier: str, 
        purpose: str,
        method: str = 'sms'
    ) -> Dict[str, Any]:
        """
        إعادة إرسال OTP موحد
        
        Returns same format as send_otp()
        """
        # Check rate limiting for resend
        is_allowed, wait_seconds = self._check_rate_limit(identifier, 'resend')
        if not is_allowed:
            return {
                'success': False,
                'error': f"{self.ERROR_MESSAGES['RATE_LIMITED']} ({wait_seconds} ثانية)",
                'error_code': 'RATE_LIMITED',
                'wait_seconds': wait_seconds
            }
        
        # Cancel existing OTP
        self.cancel_otp(identifier, purpose)
        
        # Send new OTP
        return self.send_otp(identifier, purpose, method)
    
    def cancel_otp(self, identifier: str, purpose: str) -> Dict[str, Any]:
        """
        إلغاء OTP نشط
        
        Returns:
            {'success': bool, 'message': str}
        """
        try:
            with self.db.get_write_connection() as conn:
                conn.execute("""
                    DELETE FROM pending_verifications
                    WHERE email = ? AND purpose = ?
                """, (identifier.lower(), purpose))
                
                logger.info(f"🗑️ Cancelled OTP for {self._mask_identifier(identifier)} ({purpose})")
                
                return {
                    'success': True,
                    'message': 'تم إلغاء رمز التحقق'
                }
                
        except Exception as e:
            logger.error(f"Cancel OTP error: {e}")
            return {
                'success': False,
                'error': 'خطأ في إلغاء رمز التحقق'
            }
    
    def cleanup_expired(self) -> int:
        """
        تنظيف OTP منتهية الصلاحية
        
        Returns:
            عدد السجلات المحذوفة
        """
        try:
            with self.db.get_write_connection() as conn:
                result = conn.execute("""
                    DELETE FROM pending_verifications
                    WHERE expires_at < datetime('now')
                """)
                
                deleted_count = result.rowcount
                
                if deleted_count > 0:
                    logger.info(f"🧹 Cleaned up {deleted_count} expired OTP records")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return 0
    
    def _get_available_methods(self) -> list:
        """الحصول على طرق الإرسال المتاحة"""
        methods = []
        if self.email_available:
            methods.append('email')
        if self.sms_available:
            methods.append('sms')
        return methods


# Singleton instance
_otp_manager = None

def get_otp_manager() -> UnifiedOTPManager:
    """الحصول على instance موحد من OTP Manager"""
    global _otp_manager
    if _otp_manager is None:
        _otp_manager = UnifiedOTPManager()
    return _otp_manager
