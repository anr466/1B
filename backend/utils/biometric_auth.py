#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام المصادقة البيومترية المحسّن
- تسجيل البصمة
- التحقق من البصمة
- الدخول التلقائي بالبصمة
- الشروط:
  1. المستخدم مسجل بالفعل
  2. المستخدم مفعل حفظ بيانات الدخول
  3. المستخدم مفعل البصمة
"""

import hashlib
import hmac
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
import secrets

logger = logging.getLogger(__name__)

class BiometricAuthManager:
    """مدير المصادقة البيومترية"""
    
    def __init__(self, hash_algorithm: str = 'sha256', timeout_seconds: int = 300):
        """
        تهيئة مدير البصمة
        
        Args:
            hash_algorithm: خوارزمية التجزئة
            timeout_seconds: مدة صلاحية البصمة بالثواني
        """
        self.hash_algorithm = hash_algorithm
        self.timeout_seconds = timeout_seconds
    
    def hash_biometric(self, biometric_data: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        تجزئة بيانات البصمة بشكل آمن
        
        Args:
            biometric_data: بيانات البصمة (بصمة الإصبع، الوجه، إلخ)
            salt: ملح عشوائي (يتم إنشاؤه إذا لم يكن موجوداً)
        
        Returns:
            (hash, salt) - التجزئة والملح
        """
        try:
            # إنشاء ملح عشوائي إذا لم يكن موجوداً
            if salt is None:
                salt = secrets.token_hex(16)
            
            # تجزئة البيانات مع الملح
            hash_object = hashlib.pbkdf2_hmac(
                self.hash_algorithm,
                biometric_data.encode('utf-8'),
                salt.encode('utf-8'),
                iterations=100000
            )
            
            biometric_hash = hash_object.hex()
            
            logger.info("✅ تم تجزئة بيانات البصمة بنجاح")
            
            return biometric_hash, salt
        
        except Exception as e:
            logger.error(f"❌ خطأ في تجزئة البصمة: {e}")
            raise
    
    def verify_biometric(
        self,
        biometric_data: str,
        stored_hash: str,
        salt: str
    ) -> bool:
        """
        التحقق من صحة البصمة
        
        Args:
            biometric_data: بيانات البصمة المدخلة
            stored_hash: التجزئة المخزنة
            salt: الملح المخزن
        
        Returns:
            True إذا كانت البصمة صحيحة
        """
        try:
            # تجزئة البيانات المدخلة بنفس الملح
            computed_hash, _ = self.hash_biometric(biometric_data, salt)
            
            # مقارنة آمنة (تجنب timing attacks)
            is_valid = hmac.compare_digest(computed_hash, stored_hash)
            
            if is_valid:
                logger.info("✅ تم التحقق من البصمة بنجاح")
            else:
                logger.warning("⚠️ البصمة غير متطابقة")
            
            return is_valid
        
        except Exception as e:
            logger.error(f"❌ خطأ في التحقق من البصمة: {e}")
            return False
    
    def can_use_biometric_login(
        self,
        user_data: Dict
    ) -> Tuple[bool, str]:
        """
        التحقق من شروط استخدام الدخول بالبصمة
        
        الشروط:
        1. المستخدم مسجل بالفعل (user_id موجود)
        2. المستخدم مفعل حفظ بيانات الدخول (save_credentials = True)
        3. المستخدم مفعل البصمة (biometric_enabled = True)
        
        Args:
            user_data: بيانات المستخدم من قاعدة البيانات
        
        Returns:
            (is_allowed, reason) - هل مسموح والسبب
        """
        try:
            # الشرط 1: المستخدم مسجل
            if not user_data.get('user_id'):
                return False, "المستخدم غير مسجل"
            
            # الشرط 2: حفظ بيانات الدخول مفعل
            if not user_data.get('save_credentials'):
                return False, "حفظ بيانات الدخول غير مفعل"
            
            # الشرط 3: البصمة مفعلة
            if not user_data.get('biometric_enabled'):
                return False, "البصمة غير مفعلة"
            
            # جميع الشروط متحققة
            logger.info(f"✅ المستخدم {user_data.get('user_id')} يمكنه استخدام الدخول بالبصمة")
            return True, "جميع الشروط متحققة"
        
        except Exception as e:
            logger.error(f"❌ خطأ في فحص شروط البصمة: {e}")
            return False, f"خطأ: {str(e)}"
    
    def is_biometric_valid(
        self,
        biometric_data: str,
        stored_hash: str,
        salt: str,
        last_used: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        التحقق الشامل من صحة البصمة مع الوقت
        
        Args:
            biometric_data: بيانات البصمة
            stored_hash: التجزئة المخزنة
            salt: الملح
            last_used: آخر وقت استخدام
        
        Returns:
            (is_valid, reason) - هل صحيحة والسبب
        """
        try:
            # التحقق من صلاحية البصمة الزمنية
            if last_used:
                elapsed = datetime.utcnow() - last_used
                if elapsed.total_seconds() > self.timeout_seconds:
                    logger.warning("⚠️ انتهت صلاحية البصمة")
                    return False, "انتهت صلاحية البصمة"
            
            # التحقق من صحة البصمة
            if not self.verify_biometric(biometric_data, stored_hash, salt):
                logger.warning("⚠️ البصمة غير صحيحة")
                return False, "البصمة غير صحيحة"
            
            logger.info("✅ البصمة صحيحة وسارية")
            return True, "البصمة صحيحة"
        
        except Exception as e:
            logger.error(f"❌ خطأ في التحقق من البصمة: {e}")
            return False, f"خطأ: {str(e)}"
    
    def get_biometric_status(self, user_data: Dict) -> Dict:
        """
        الحصول على حالة البصمة للمستخدم
        
        Args:
            user_data: بيانات المستخدم
        
        Returns:
            قاموس بحالة البصمة
        """
        can_use, reason = self.can_use_biometric_login(user_data)
        
        return {
            'can_use_biometric': can_use,
            'reason': reason,
            'user_registered': bool(user_data.get('user_id')),
            'save_credentials_enabled': bool(user_data.get('save_credentials')),
            'biometric_enabled': bool(user_data.get('biometric_enabled')),
            'last_used': user_data.get('last_biometric_used'),
            'device_id': user_data.get('device_id')
        }

# إنشاء instance عام
biometric_manager = BiometricAuthManager(
    hash_algorithm='sha256',
    timeout_seconds=300
)

def create_biometric_manager(
    hash_algorithm: str = 'sha256',
    timeout_seconds: int = 300
) -> BiometricAuthManager:
    """إنشاء مدير البصمة"""
    return BiometricAuthManager(hash_algorithm, timeout_seconds)
