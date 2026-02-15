#!/usr/bin/env python3
"""
خدمة إشعارات الأدمن المتقدمة
Admin Notification Service - إشعارات فورية للأدمن عند حدوث مشاكل

الطرق المدعومة:
1. Push Notifications (Firebase/Expo)
2. Telegram Bot
3. Email
4. Webhook
5. In-App Alerts (قاعدة البيانات)
"""

import os
import sys
import json
import logging
import sqlite3
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
from threading import Thread

# إضافة مسار المشروع
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# استيراد خدمة Firebase للإشعارات
try:
    from utils.firebase_notification_service import FirebaseNotificationService
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

logger = logging.getLogger(__name__)


class AdminNotificationService:
    """
    خدمة إرسال إشعارات فورية للأدمن
    """
    
    def __init__(self, db_path: str = "database/trading_database.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # إعدادات الإشعارات (تُحمّل من قاعدة البيانات أو متغيرات البيئة)
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_ADMIN_CHAT_ID')
        self.webhook_url = os.getenv('ADMIN_WEBHOOK_URL')
        self.admin_email = os.getenv('ADMIN_EMAIL')
        
        # ✅ تهيئة خدمة Firebase للإشعارات Push
        self.firebase_service = None
        if FIREBASE_AVAILABLE:
            try:
                self.firebase_service = FirebaseNotificationService()
                self.logger.info("✅ Firebase Push Notifications مُفعّل للأدمن")
            except Exception as e:
                self.logger.warning(f"⚠️ Firebase غير متاح: {e}")
        
        # تحميل إعدادات الإشعارات من قاعدة البيانات
        self._load_notification_settings()
        
    def _load_notification_settings(self):
        """تحميل إعدادات الإشعارات من قاعدة البيانات"""
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_write_connection() as conn:
                cursor = conn.cursor()
                
                # التحقق من وجود إعدادات
                cursor.execute("SELECT * FROM admin_notification_settings WHERE id = 1")
                settings = cursor.fetchone()
                
                if settings:
                    # تحميل الإعدادات
                    self.telegram_enabled = bool(settings[1])
                    self.telegram_bot_token = settings[2] or self.telegram_bot_token
                    self.telegram_chat_id = settings[3] or self.telegram_chat_id
                    self.email_enabled = bool(settings[4])
                    self.admin_email = settings[5] or self.admin_email
                    self.webhook_enabled = bool(settings[6])
                    self.webhook_url = settings[7] or self.webhook_url
                    self.push_enabled = bool(settings[8])
                    self.notify_on_error = bool(settings[9])
                    self.notify_on_trade = bool(settings[10])
                    self.notify_on_warning = bool(settings[11])
                else:
                    # إنشاء إعدادات افتراضية
                    cursor.execute("""
                        INSERT INTO admin_notification_settings (id) VALUES (1)
                    """)
                    self.telegram_enabled = False
                    self.email_enabled = False
                    self.webhook_enabled = False
                    self.push_enabled = True
                    self.notify_on_error = True
                    self.notify_on_trade = True
                    self.notify_on_warning = True
            
        except Exception as e:
            self.logger.error(f"فشل تحميل إعدادات الإشعارات: {e}")
            # إعدادات افتراضية
            self.telegram_enabled = False
            self.email_enabled = False
            self.webhook_enabled = False
            self.push_enabled = True
            self.notify_on_error = True
            self.notify_on_trade = True
            self.notify_on_warning = True
    
    # ═══════════════════════════════════════════════════════════════
    # إرسال الإشعارات
    # ═══════════════════════════════════════════════════════════════
    
    def notify_admin(self, title: str, message: str, severity: str = 'info', 
                     alert_type: str = 'general', data: Dict = None):
        """
        إرسال إشعار للأدمن عبر جميع القنوات المفعّلة
        
        Args:
            title: عنوان الإشعار
            message: نص الإشعار
            severity: خطورة (info, warning, error, critical)
            alert_type: نوع الإشعار
            data: بيانات إضافية
        """
        # التحقق من نوع الإشعار
        if severity in ['error', 'critical'] and not self.notify_on_error:
            return
        if severity == 'warning' and not self.notify_on_warning:
            return
        if alert_type == 'trade' and not self.notify_on_trade:
            return
        
        # حفظ في قاعدة البيانات (دائماً)
        self._save_to_database(title, message, severity, alert_type, data)
        
        # إرسال عبر القنوات المفعّلة (في thread منفصل لعدم تأخير العملية الرئيسية)
        Thread(target=self._send_notifications, args=(title, message, severity, data)).start()
    
    def _send_notifications(self, title: str, message: str, severity: str, data: Dict = None):
        """إرسال الإشعارات عبر جميع القنوات"""
        
        # 1. Telegram
        if self.telegram_enabled and self.telegram_bot_token and self.telegram_chat_id:
            self._send_telegram(title, message, severity)
        
        # 2. Webhook
        if self.webhook_enabled and self.webhook_url:
            self._send_webhook(title, message, severity, data)
        
        # 3. Email (يحتاج إعداد SMTP)
        if self.email_enabled and self.admin_email:
            self._send_email(title, message, severity)
        
        # 4. ✅ Firebase Push Notifications للأدمن (خارج التطبيق)
        if self.push_enabled and self.firebase_service:
            self._send_fcm_push(title, message, severity, data)
    
    def _save_to_database(self, title: str, message: str, severity: str, 
                          alert_type: str, data: Dict = None):
        """حفظ الإشعار في قاعدة البيانات"""
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_write_connection() as conn:
                cursor = conn.cursor()
                
                data_json = json.dumps(data) if data else None
                
                cursor.execute("""
                    INSERT INTO system_alerts 
                    (alert_type, title, message, severity, data)
                    VALUES (?, ?, ?, ?, ?)
                """, (alert_type, title, message, severity, data_json))
            
        except Exception as e:
            self.logger.error(f"فشل حفظ الإشعار: {e}")
    
    def _send_with_retry(self, send_func, max_retries: int = 3, description: str = "notification"):
        """
        ✅ إرسال مع إعادة المحاولة (Exponential Backoff)
        
        Args:
            send_func: دالة الإرسال
            max_retries: عدد المحاولات القصوى
            description: وصف العملية للتسجيل
        
        Returns:
            True إذا نجح الإرسال
        """
        import time
        
        for attempt in range(max_retries):
            try:
                result = send_func()
                if result:
                    return True
            except Exception as e:
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                self.logger.warning(f"⚠️ محاولة {attempt + 1}/{max_retries} فشلت لـ {description}: {e}")
                
                if attempt < max_retries - 1:
                    self.logger.info(f"🔄 إعادة المحاولة بعد {wait_time} ثانية...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"❌ فشل نهائي في إرسال {description} بعد {max_retries} محاولات")
        
        return False
    
    def _send_telegram(self, title: str, message: str, severity: str):
        """إرسال إشعار عبر Telegram مع إعادة المحاولة"""
        
        def _do_send():
            # تحديد الإيموجي حسب الخطورة
            emoji = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'error': '❌',
                'critical': '🚨'
            }.get(severity, '📢')
            
            text = f"{emoji} *{title}*\n\n{message}\n\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                self.logger.info(f"✅ Telegram notification sent: {title}")
                return True
            else:
                self.logger.error(f"❌ Telegram error: {response.text}")
                return False
        
        # ✅ استخدام retry mechanism
        return self._send_with_retry(_do_send, max_retries=3, description="Telegram")
    
    def _send_webhook(self, title: str, message: str, severity: str, data: Dict = None):
        """إرسال إشعار عبر Webhook مع إعادة المحاولة"""
        
        def _do_send():
            payload = {
                'title': title,
                'message': message,
                'severity': severity,
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            response = requests.post(
                self.webhook_url, 
                json=payload, 
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                self.logger.info(f"✅ Webhook notification sent: {title}")
                return True
            else:
                self.logger.error(f"❌ Webhook error: {response.status_code}")
                return False
        
        # ✅ استخدام retry mechanism
        return self._send_with_retry(_do_send, max_retries=3, description="Webhook")
    
    def _send_email(self, title: str, message: str, severity: str):
        """إرسال إشعار عبر Email"""
        # يحتاج إعداد SMTP - placeholder
        self.logger.info(f"📧 Email notification (not configured): {title}")
    
    def _send_fcm_push(self, title: str, message: str, severity: str, data: Dict = None):
        """
        ✅ إرسال إشعار Push للأدمن عبر Firebase FCM
        يصل للأدمن حتى لو كان خارج التطبيق
        """
        try:
            # جلب معرف الأدمن من قاعدة البيانات
            admin_user_id = self._get_admin_user_id()
            
            if not admin_user_id:
                self.logger.warning("⚠️ لم يتم العثور على حساب الأدمن")
                return False
            
            # تحديد نوع الإشعار حسب الخطورة
            notification_type = {
                'info': 'admin_info',
                'warning': 'admin_warning',
                'error': 'admin_error',
                'critical': 'admin_critical'
            }.get(severity, 'admin_alert')
            
            # إعداد البيانات الإضافية
            fcm_data = {
                'type': notification_type,
                'severity': severity,
                'screen': 'AdminDashboard',
                'action': 'refresh'
            }
            if data:
                fcm_data.update({k: str(v) for k, v in data.items() if v is not None})
            
            # إرسال الإشعار
            success = self.firebase_service.send_notification_to_user(
                user_id=admin_user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                data=fcm_data
            )
            
            if success:
                self.logger.info(f"✅ FCM Push sent to admin: {title}")
            else:
                self.logger.warning(f"⚠️ FCM Push failed for admin: {title}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ خطأ في إرسال FCM Push: {e}")
            return False
    
    def _get_admin_user_id(self) -> Optional[int]:
        """جلب معرف حساب الأدمن"""
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id FROM users 
                    WHERE user_type = 'admin' AND is_active = 1
                    LIMIT 1
                """)
                result = cursor.fetchone()
                return result[0] if result else None
            
        except Exception as e:
            self.logger.error(f"خطأ في جلب معرف الأدمن: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════
    # إشعارات محددة
    # ═══════════════════════════════════════════════════════════════
    
    def notify_system_error(self, error_type: str, error_message: str, traceback: str = None):
        """إشعار بخطأ في النظام"""
        self.notify_admin(
            title=f"🚨 خطأ في النظام: {error_type}",
            message=error_message,
            severity='critical',
            alert_type='system_error',
            data={'error_type': error_type, 'traceback': traceback}
        )
    
    def notify_trading_stopped(self, reason: str):
        """إشعار بتوقف التداول"""
        self.notify_admin(
            title="⛔ توقف التداول",
            message=f"توقف نظام التداول: {reason}",
            severity='critical',
            alert_type='trading_stopped',
            data={'reason': reason}
        )
    
    def notify_trade_executed(self, symbol: str, action: str, price: float, quantity: float, pnl: float = None):
        """إشعار بتنفيذ صفقة"""
        emoji = '🟢' if action == 'BUY' else '🔴'
        pnl_text = f"\nالربح/الخسارة: ${pnl:.2f}" if pnl is not None else ""
        
        self.notify_admin(
            title=f"{emoji} صفقة {action}: {symbol}",
            message=f"السعر: ${price:.4f}\nالكمية: {quantity}{pnl_text}",
            severity='info',
            alert_type='trade',
            data={'symbol': symbol, 'action': action, 'price': price, 'quantity': quantity, 'pnl': pnl}
        )
    
    def notify_binance_error(self, error_message: str):
        """إشعار بخطأ في Binance API"""
        self.notify_admin(
            title="⚠️ خطأ في Binance API",
            message=error_message,
            severity='error',
            alert_type='binance_error',
            data={'error': error_message}
        )
    
    def notify_low_balance(self, balance: float, threshold: float):
        """إشعار بانخفاض الرصيد"""
        self.notify_admin(
            title="💰 تحذير: رصيد منخفض",
            message=f"الرصيد الحالي: ${balance:.2f}\nالحد الأدنى: ${threshold:.2f}",
            severity='warning',
            alert_type='low_balance',
            data={'balance': balance, 'threshold': threshold}
        )
    
    def notify_ml_status_change(self, is_ready: bool, samples: int, required: int):
        """إشعار بتغيير حالة ML"""
        if is_ready:
            self.notify_admin(
                title="🧠 ML جاهز للعمل!",
                message=f"تم جمع {samples} عينة. ML مفعّل الآن.",
                severity='info',
                alert_type='ml_ready'
            )
        else:
            self.notify_admin(
                title="🧠 تقدم ML",
                message=f"العينات: {samples}/{required}",
                severity='info',
                alert_type='ml_progress'
            )
    
    # ═══════════════════════════════════════════════════════════════
    # إدارة الإعدادات
    # ═══════════════════════════════════════════════════════════════
    
    def update_settings(self, settings: Dict) -> bool:
        """تحديث إعدادات الإشعارات"""
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE admin_notification_settings SET
                        telegram_enabled = ?,
                        telegram_bot_token = ?,
                        telegram_chat_id = ?,
                        email_enabled = ?,
                        admin_email = ?,
                        webhook_enabled = ?,
                        webhook_url = ?,
                        push_enabled = ?,
                        notify_on_error = ?,
                        notify_on_trade = ?,
                        notify_on_warning = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (
                    settings.get('telegram_enabled', self.telegram_enabled),
                    settings.get('telegram_bot_token', self.telegram_bot_token),
                    settings.get('telegram_chat_id', self.telegram_chat_id),
                    settings.get('email_enabled', self.email_enabled),
                    settings.get('admin_email', self.admin_email),
                    settings.get('webhook_enabled', self.webhook_enabled),
                    settings.get('webhook_url', self.webhook_url),
                    settings.get('push_enabled', self.push_enabled),
                    settings.get('notify_on_error', self.notify_on_error),
                    settings.get('notify_on_trade', self.notify_on_trade),
                    settings.get('notify_on_warning', self.notify_on_warning)
                ))
            
            # إعادة تحميل الإعدادات
            self._load_notification_settings()
            
            return True
            
        except Exception as e:
            self.logger.error(f"فشل تحديث الإعدادات: {e}")
            return False
    
    def get_settings(self) -> Dict:
        """الحصول على إعدادات الإشعارات"""
        return {
            'telegram_enabled': self.telegram_enabled,
            'telegram_configured': bool(self.telegram_bot_token and self.telegram_chat_id),
            'email_enabled': self.email_enabled,
            'email_configured': bool(self.admin_email),
            'webhook_enabled': self.webhook_enabled,
            'webhook_configured': bool(self.webhook_url),
            'push_enabled': self.push_enabled,
            'notify_on_error': self.notify_on_error,
            'notify_on_trade': self.notify_on_trade,
            'notify_on_warning': self.notify_on_warning
        }
    
    def get_unread_alerts(self, limit: int = 50) -> List[Dict]:
        """الحصول على الإشعارات غير المقروءة"""
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_connection() as conn:
                conn.row_factory = lambda row: dict(row)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM system_alerts 
                    WHERE read = 0 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,))
                
                alerts = []
                import json
                for row in cursor.fetchall():
                    alerts.append({
                        'id': row['id'],
                        'type': row['alert_type'],
                        'title': row['title'],
                        'message': row['message'],
                        'severity': row['severity'],
                        'data': json.loads(row['data']) if row['data'] else None,
                        'created_at': row['created_at'],
                        'read': bool(row['read'])
                    })
                
                return alerts
            
        except Exception as e:
            self.logger.error(f"فشل جلب الإشعارات: {e}")
            return []
    
    def get_unread_count(self) -> int:
        """عدد الإشعارات غير المقروءة"""
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM system_alerts WHERE read = 0")
                count = cursor.fetchone()[0]
                return count
        except Exception as e:
            self.logger.error(f"خطأ في جلب عدد الإشعارات غير المقروءة: {e}")
            return 0
    
    def mark_as_read(self, alert_id: int) -> bool:
        """تحديد إشعار كمقروء"""
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE system_alerts SET read = 1 WHERE id = ?", (alert_id,))
            
            return True
        except Exception as e:
            self.logger.error(f"خطأ في تحديد الإشعار كمقروء: {e}")
            return False
    
    def mark_all_as_read(self) -> bool:
        """تحديد جميع الإشعارات كمقروءة"""
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE system_alerts SET read = 1 WHERE read = 0")
            
            return True
        except Exception as e:
            self.logger.error(f"خطأ في تحديد جميع الإشعارات كمقروءة: {e}")
            return False


# Singleton instance
_admin_notification_service = None

def get_admin_notification_service() -> AdminNotificationService:
    """الحصول على instance وحيد من الخدمة"""
    global _admin_notification_service
    if _admin_notification_service is None:
        _admin_notification_service = AdminNotificationService()
    return _admin_notification_service
