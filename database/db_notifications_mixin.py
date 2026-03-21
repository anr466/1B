"""
Database Notifications Mixin — extracted from database_manager.py (God Object split)
====================================================================================
Methods: notifications, FCM tokens, activity logs, sessions, biometrics, devices
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any


class DbNotificationsMixin:
    """Notification & security database methods (notifications, FCM, sessions, biometrics, devices)"""

    # ==================== إدارة الإشعارات ====================

    def get_user_notifications(self, user_id: int, limit: int = 50):
        """جلب إشعارات المستخدم"""
        try:
            with self.get_connection() as conn:
                try:
                    rows = conn.execute("""
                        SELECT id, title, message, notification_type as type, data, created_at, status as read_status
                        FROM notification_history 
                        WHERE user_id = %s 
                        ORDER BY created_at DESC 
                        LIMIT %s
                    """, (user_id, limit)).fetchall()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    rows = conn.execute("""
                        SELECT id,
                               title,
                               message,
                               COALESCE(notification_type, type, 'general') as type,
                               NULL as data,
                               created_at,
                               status as read_status
                        FROM notification_history
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (user_id, limit)).fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"خطأ في جلب الإشعارات للمستخدم {user_id}: {e}")
            return []

    def save_notification(self, user_id: int, title: str, message: str, notification_type: str = 'general', data: dict = None):
        """حفظ إشعار جديد"""
        try:
            with self.get_write_connection() as conn:
                try:
                    conn.execute("""
                        INSERT INTO notification_history 
                        (user_id, title, message, notification_type, data, created_at, status)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 'pending')
                    """, (user_id, title, message, notification_type, json.dumps(data) if data else None))
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    conn.execute("""
                        INSERT INTO notification_history 
                        (user_id, title, message, notification_type, type, created_at, status)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 'pending')
                    """, (user_id, title, message, notification_type, notification_type))
                return True
        except Exception as e:
            self.logger.error(f"خطأ في حفظ الإشعار للمستخدم {user_id}: {e}")
            return False

    def update_notification_settings(self, user_id: int, settings: dict):
        """تحديث إعدادات الإشعارات للمستخدم"""
        try:
            with self.get_write_connection() as conn:
                existing = conn.execute("""
                    SELECT id FROM user_notification_settings WHERE user_id = %s
                """, (user_id,)).fetchone()
                
                if existing:
                    conn.execute("""
                        UPDATE user_notification_settings 
                        SET push_enabled = %s, email_enabled = %s, sms_enabled = %s,
                            trade_notifications = %s, price_alerts = %s, system_notifications = %s,
                            updated_at = datetime('now')
                        WHERE user_id = %s
                    """, (
                        settings.get('push_enabled', True),
                        settings.get('email_enabled', True), 
                        settings.get('sms_enabled', False),
                        settings.get('trade_signals', True),
                        settings.get('portfolio_updates', True),
                        settings.get('system_alerts', True),
                        user_id
                    ))
                else:
                    conn.execute("""
                        INSERT INTO user_notification_settings 
                        (user_id, push_enabled, email_enabled, sms_enabled, 
                         trade_notifications, price_alerts, system_notifications, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, datetime('now'))
                    """, (
                        user_id,
                        settings.get('push_enabled', True),
                        settings.get('email_enabled', True),
                        settings.get('sms_enabled', False),
                        settings.get('trade_signals', True),
                        settings.get('portfolio_updates', True),
                        settings.get('system_alerts', True)
                    ))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"خطأ في تحديث إعدادات الإشعارات للمستخدم {user_id}: {e}")
            return False

    def register_fcm_token(self, user_id: int, fcm_token: str, platform: str = 'android'):
        """تسجيل FCM Token للمستخدم"""
        try:
            with self.get_write_connection() as conn:
                existing = conn.execute("""
                    SELECT id FROM user_devices WHERE user_id = %s AND push_token = %s
                """, (user_id, fcm_token)).fetchone()

                if not existing:
                    device_id = f"device_{user_id}_{int(time.time())}"
                    conn.execute("""
                        INSERT INTO user_devices 
                        (user_id, device_id, device_type, device_name, push_token, is_trusted, created_at)
                        VALUES (%s, %s, %s, %s, %s, 1, datetime('now'))
                    """, (user_id, device_id, platform, 'Mobile App', fcm_token))
                else:
                    conn.execute("""
                        UPDATE user_devices 
                        SET is_trusted = 1, last_login = datetime('now')
                        WHERE user_id = %s AND push_token = %s
                    """, (user_id, fcm_token))

                conn.execute("""
                    INSERT INTO fcm_tokens (user_id, fcm_token, platform, created_at)
                    VALUES (%s, %s, %s, datetime('now'))
                    ON CONFLICT (fcm_token) DO UPDATE SET platform = EXCLUDED.platform
                """, (user_id, fcm_token, platform))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"خطأ في تسجيل FCM Token للمستخدم {user_id}: {e}")
            return False

    def unregister_fcm_token(self, user_id: int, fcm_token: str):
        """إلغاء تسجيل FCM Token للمستخدم"""
        try:
            with self.get_write_connection() as conn:
                conn.execute("""
                    DELETE FROM fcm_tokens 
                    WHERE user_id = %s AND fcm_token = %s
                """, (user_id, fcm_token))
                conn.execute("""
                    DELETE FROM user_devices
                    WHERE user_id = %s AND push_token = %s
                """, (user_id, fcm_token))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"خطأ في إلغاء تسجيل FCM Token للمستخدم {user_id}: {e}")
            return False

    def get_user_fcm_tokens(self, user_id: int):
        """جلب جميع FCM Tokens النشطة للمستخدم من جدول fcm_tokens"""
        try:
            with self.get_connection() as conn:
                rows = conn.execute("""
                    SELECT fcm_token, platform FROM fcm_tokens 
                    WHERE user_id = %s
                """, (user_id,)).fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"خطأ في جلب FCM Tokens للمستخدم {user_id}: {e}")
            return []

    # ==================== سجل أنشطة المستخدم ====================

    def get_user_activity_logs(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """الحصول على سجل أنشطة المستخدم"""
        try:
            with self.get_connection() as conn:
                rows = conn.execute("""
                    SELECT * FROM activity_logs 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (user_id, limit)).fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"خطأ في جلب سجل الأنشطة: {e}")
            return []

    # ==================== إدارة الجلسات والأمان ====================

    def create_user_session(self, user_id: int, token: str, device_info: dict = None) -> bool:
        """إنشاء جلسة جديدة للمستخدم"""
        try:
            with self.get_write_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO user_sessions 
                    (user_id, session_token, expires_at, created_at)
                    VALUES (%s, %s, datetime('now', '+7 days'), datetime('now'))
                """, (user_id, token))
                
                self.logger.info(f"تم إنشاء جلسة جديدة للمستخدم {user_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"خطأ في إنشاء الجلسة: {e}")
            return False

    def validate_user_session(self, token: str) -> dict:
        """التحقق من صحة جلسة المستخدم"""
        try:
            with self.get_connection() as conn:
                
                session = conn.execute("""
                    SELECT us.*, u.username, u.user_type 
                    FROM user_sessions us
                    JOIN users u ON us.user_id = u.id
                    WHERE us.session_token = %s AND us.expires_at > datetime('now')
                """, (token,)).fetchone()
                
                if session:
                    return dict(session)
                return None
                
        except Exception as e:
            self.logger.error(f"خطأ في التحقق من الجلسة: {e}")
            return None

    def invalidate_user_session(self, token: str) -> bool:
        """إلغاء جلسة المستخدم"""
        try:
            with self.get_write_connection() as conn:
                conn.execute("""
                    DELETE FROM user_sessions 
                    WHERE session_token = %s
                """, (token,))
                
                self.logger.info(f"تم إلغاء الجلسة: {token[:20]}...")
                return True
                
        except Exception as e:
            self.logger.error(f"خطأ في إلغاء الجلسة: {e}")
            return False

    def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """الحصول على جلسات المستخدم النشطة"""
        try:
            with self.get_connection() as conn:
                
                sessions = conn.execute("""
                    SELECT session_token, created_at, expires_at
                    FROM user_sessions 
                    WHERE user_id = %s AND expires_at > datetime('now')
                    ORDER BY created_at DESC
                """, (user_id,)).fetchall()
                
                return [dict(session) for session in sessions]
                
        except Exception as e:
            self.logger.error(f"خطأ في جلب الجلسات: {e}")
            return []

    # ==================== إدارة البصمة والأمان البيومتري ====================

    def register_user_biometric(self, user_id: int, biometric_data: dict) -> bool:
        """تسجيل البيانات البيومترية للمستخدم مع حذف البيانات القديمة من نفس النوع"""
        try:
            with self.get_write_connection() as conn:
                biometric_type = biometric_data.get('biometric_type')
                
                conn.execute("""
                    DELETE FROM user_biometric_auth 
                    WHERE user_id = %s AND biometric_type = %s
                """, (user_id, biometric_type))
                
                conn.execute("""
                    INSERT INTO user_biometric_auth 
                    (user_id, biometric_type, biometric_hash, device_id, created_at, is_active)
                    VALUES (%s, %s, %s, %s, datetime('now'), 1)
                """, (
                    user_id,
                    biometric_type,
                    biometric_data.get('biometric_hash'),
                    biometric_data.get('device_id')
                ))
                
                conn.commit()
                self.logger.info(f"تم تحديث البيانات البيومترية ({biometric_type}) للمستخدم {user_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"خطأ في تسجيل البيانات البيومترية: {e}")
            return False

    def verify_user_biometric(self, user_id: int, biometric_data: dict) -> bool:
        """التحقق من البيانات البيومترية للمستخدم"""
        try:
            with self.get_connection() as conn:
                
                stored_biometric = conn.execute("""
                    SELECT biometric_hash, biometric_type 
                    FROM user_biometric_auth 
                    WHERE user_id = %s AND biometric_type = %s AND is_active = TRUE
                """, (user_id, biometric_data.get('biometric_type'))).fetchone()
                
                if stored_biometric:
                    return stored_biometric['biometric_hash'] == biometric_data.get('biometric_hash')
                
                return False
                
        except Exception as e:
            self.logger.error(f"خطأ في التحقق من البيانات البيومترية: {e}")
            return False

    def get_user_biometrics(self, user_id: int) -> List[Dict[str, Any]]:
        """الحصول على البيانات البيومترية المسجلة للمستخدم"""
        try:
            with self.get_connection() as conn:
                
                biometrics = conn.execute("""
                    SELECT biometric_type, device_id, created_at, is_active
                    FROM user_biometric_auth 
                    WHERE user_id = %s AND is_active = TRUE
                """, (user_id,)).fetchall()
                
                return [dict(biometric) for biometric in biometrics]
                
        except Exception as e:
            self.logger.error(f"خطأ في جلب البيانات البيومترية: {e}")
            return []

    # ==================== إدارة الأجهزة ====================

    def register_user_device(self, user_id: int, device_data: dict) -> bool:
        """تسجيل جهاز جديد للمستخدم"""
        try:
            with self.get_write_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO user_devices 
                    (user_id, device_id, device_name, device_type, device_model, created_at)
                    VALUES (%s, %s, %s, %s, %s, datetime('now'))
                """, (
                    user_id,
                    device_data.get('device_id'),
                    device_data.get('device_name'),
                    device_data.get('device_type'),
                    device_data.get('device_info', {}).get('model', 'Unknown')
                ))
                
                self.logger.info(f"تم تسجيل جهاز جديد للمستخدم {user_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"خطأ في تسجيل الجهاز: {e}")
            return False

    def get_user_devices(self, user_id: int) -> List[Dict[str, Any]]:
        """الحصول على أجهزة المستخدم المسجلة"""
        try:
            with self.get_connection() as conn:
                
                devices = conn.execute("""
                    SELECT device_id, device_name, device_type, device_model, created_at
                    FROM user_devices 
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """, (user_id,)).fetchall()
                
                return [dict(device) for device in devices]
                
        except Exception as e:
            self.logger.error(f"خطأ في جلب الأجهزة: {e}")
            return []
