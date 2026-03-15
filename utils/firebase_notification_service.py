#!/usr/bin/env python3
"""
🔔 خدمة إشعارات Firebase Push Notifications
ترسل إشعارات Push للمستخدمين عبر Firebase Cloud Messaging (FCM)
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

# تحميل متغيرات البيئة
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# محاولة استيراد Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_SDK_AVAILABLE = True
except ImportError:
    FIREBASE_SDK_AVAILABLE = False
    logger.warning("⚠️ firebase-admin غير مثبت. قم بتثبيته: pip install firebase-admin")


class FirebaseNotificationService:
    """
    خدمة إرسال Push Notifications عبر Firebase Cloud Messaging
    
    الاستخدام:
        service = FirebaseNotificationService()
        service.send_to_user(user_id, "عنوان", "رسالة", {"key": "value"})
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern - نسخة واحدة فقط"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """تهيئة Firebase Admin SDK"""
        if FirebaseNotificationService._initialized:
            return
            
        self.app = None
        self.is_available = False
        
        if not FIREBASE_SDK_AVAILABLE:
            logger.warning("⚠️ Firebase SDK غير متاح")
            return
        
        # البحث عن ملف credentials
        credentials_path = self._find_credentials_file()
        
        if not credentials_path:
            logger.warning("⚠️ ملف Firebase credentials غير موجود")
            return
        
        try:
            # تهيئة Firebase إذا لم يكن مهيأ
            if not firebase_admin._apps:
                cred = credentials.Certificate(credentials_path)
                self.app = firebase_admin.initialize_app(cred)
                logger.info(f"✅ Firebase initialized from: {credentials_path}")
            else:
                self.app = firebase_admin.get_app()
                logger.info("✅ Firebase already initialized")
            
            self.is_available = True
            FirebaseNotificationService._initialized = True
            
        except Exception as e:
            logger.error(f"❌ فشل تهيئة Firebase: {e}")
            self.is_available = False
    
    def _find_credentials_file(self) -> Optional[str]:
        """البحث عن ملف Firebase credentials"""
        # المسارات المحتملة
        project_root = Path(__file__).parent.parent
        possible_paths = [
            # من متغير البيئة
            os.environ.get('FIREBASE_CREDENTIALS_PATH'),
            os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'),
            # المسارات الافتراضية
            project_root / 'config' / 'security' / 'firebase-service-account.json',
            project_root / 'config' / 'firebase-service-account.json',
            project_root / 'firebase-service-account.json',
        ]
        
        for path in possible_paths:
            if path and Path(path).exists():
                return str(path)
        
        return None
    
    def send_to_token(self, token: str, title: str, body: str, 
                      data: Optional[Dict[str, str]] = None,
                      priority: str = 'high') -> bool:
        """
        إرسال إشعار لـ FCM Token محدد
        
        Args:
            token: FCM Token للجهاز
            title: عنوان الإشعار
            body: نص الإشعار
            data: بيانات إضافية (يجب أن تكون Dict[str, str])
            priority: الأولوية (high, normal)
        
        Returns:
            True إذا نجح الإرسال
        """
        if not self.is_available:
            logger.warning("⚠️ Firebase غير متاح - لم يتم إرسال الإشعار")
            return False
        
        if not token:
            logger.warning("⚠️ FCM Token فارغ")
            return False
        
        try:
            # تحويل البيانات لـ strings
            str_data = {}
            if data:
                for k, v in data.items():
                    str_data[str(k)] = str(v) if v is not None else ""
            
            # إنشاء الرسالة
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=str_data,
                token=token,
                android=messaging.AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        icon='ic_notification',
                        color='#4CAF50',
                        sound='default',
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            badge=1,
                        )
                    )
                )
            )
            
            # إرسال الرسالة
            response = messaging.send(message)
            logger.info(f"✅ تم إرسال الإشعار: {response}")
            return True
            
        except messaging.UnregisteredError:
            logger.warning(f"⚠️ Token غير مسجل أو منتهي الصلاحية")
            return False
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال الإشعار: {e}")
            return False
    
    def send_to_tokens(self, tokens: List[str], title: str, body: str,
                       data: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        إرسال إشعار لعدة أجهزة
        
        Returns:
            {'success': int, 'failure': int, 'failed_tokens': List[str]}
        """
        if not self.is_available:
            return {'success': 0, 'failure': len(tokens), 'failed_tokens': tokens}
        
        if not tokens:
            return {'success': 0, 'failure': 0, 'failed_tokens': []}
        
        # تحويل البيانات
        str_data = {}
        if data:
            for k, v in data.items():
                str_data[str(k)] = str(v) if v is not None else ""
        
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=str_data,
                tokens=tokens,
            )
            
            response = messaging.send_each_for_multicast(message)
            
            failed_tokens = []
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    failed_tokens.append(tokens[idx])
            
            return {
                'success': response.success_count,
                'failure': response.failure_count,
                'failed_tokens': failed_tokens
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال الإشعارات المتعددة: {e}")
            return {'success': 0, 'failure': len(tokens), 'failed_tokens': tokens}
    
    def send_to_user(self, user_id: int, title: str, body: str,
                     data: Optional[Dict] = None) -> bool:
        """
        إرسال إشعار لمستخدم محدد (يجلب FCM Token من قاعدة البيانات)
        
        Args:
            user_id: معرف المستخدم
            title: عنوان الإشعار
            body: نص الإشعار
            data: بيانات إضافية
        
        Returns:
            True إذا نجح الإرسال
        """
        if not self.is_available:
            return False
        
        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_connection() as conn:
                # جلب FCM Token للمستخدم من جدول fcm_tokens
                result = conn.execute("""
                    SELECT fcm_token FROM fcm_tokens 
                    WHERE user_id = ? AND fcm_token IS NOT NULL AND fcm_token != ''
                    ORDER BY created_at DESC LIMIT 1
                """, (user_id,)).fetchone()
                
                if not result or not result[0]:
                    logger.debug(f"⚠️ المستخدم {user_id} ليس لديه FCM Token")
                    return False
                
                token = result[0]
                return self.send_to_token(token, title, body, data)
                
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال إشعار للمستخدم {user_id}: {e}")
            return False
    
    def send_to_all_users(self, title: str, body: str,
                          data: Optional[Dict] = None,
                          user_type: Optional[str] = None) -> Dict[str, Any]:
        """
        إرسال إشعار لجميع المستخدمين (أو نوع محدد)
        
        Args:
            title: عنوان الإشعار
            body: نص الإشعار
            data: بيانات إضافية
            user_type: نوع المستخدم (admin, user, أو None للجميع)
        
        Returns:
            {'success': int, 'failure': int}
        """
        if not self.is_available:
            return {'success': 0, 'failure': 0}
        
        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_connection() as conn:
                # جلب FCM Tokens من جدول fcm_tokens
                if user_type:
                    results = conn.execute("""
                        SELECT f.fcm_token FROM fcm_tokens f
                        JOIN users u ON f.user_id = u.id
                        WHERE f.fcm_token IS NOT NULL AND f.fcm_token != ''
                        AND u.user_type = ?
                    """, (user_type,)).fetchall()
                else:
                    results = conn.execute("""
                        SELECT fcm_token FROM fcm_tokens 
                        WHERE fcm_token IS NOT NULL AND fcm_token != ''
                    """).fetchall()
                
                tokens = [r[0] for r in results if r[0]]
                
                if not tokens:
                    return {'success': 0, 'failure': 0}
                
                return self.send_to_tokens(tokens, title, body, data)
                
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال إشعار للجميع: {e}")
            return {'success': 0, 'failure': 0}


# Singleton instance
_firebase_service = None

def get_firebase_service() -> FirebaseNotificationService:
    """جلب نسخة واحدة من خدمة Firebase"""
    global _firebase_service
    if _firebase_service is None:
        _firebase_service = FirebaseNotificationService()
    return _firebase_service


# اختبار سريع
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    service = get_firebase_service()
    print(f"Firebase Available: {service.is_available}")
    
    if service.is_available:
        print("✅ Firebase جاهز للاستخدام!")
    else:
        print("⚠️ Firebase غير متاح - تحقق من الإعدادات")
