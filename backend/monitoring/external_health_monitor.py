#!/usr/bin/env python3
"""
🔍 مراقب صحة النظام الخارجي
External Health Monitor

يعمل كـ process منفصل ويراقب:
1. هل Backend يستجيب؟
2. هل Database متاحة؟
3. هل نظام التداول يعمل؟

إذا اكتشف مشكلة → يرسل Telegram مباشرة (بدون الاعتماد على Backend)
"""

import os
import sys
import time
import sqlite3
import requests
import logging
from datetime import datetime
from pathlib import Path

# إعداد المسارات
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ExternalHealthMonitor:
    """
    مراقب خارجي مستقل عن Backend
    """
    
    def __init__(self):
        self.db_path = PROJECT_ROOT / 'database' / 'trading_database.db'
        self.api_url = os.getenv('API_URL', 'http://127.0.0.1:5000/api')
        
        # إعدادات Telegram (تُحمّل من DB أو متغيرات البيئة)
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        # حالة المراقبة
        self.last_backend_status = True
        self.last_db_status = True
        self.last_trading_status = True
        self.consecutive_failures = 0
        
        # تحميل إعدادات Telegram من DB
        self._load_telegram_settings()
    
    def _load_telegram_settings(self):
        """تحميل إعدادات Telegram من قاعدة البيانات"""
        try:
            if self.db_path.exists():
                # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
                from database.database_manager import DatabaseManager
                db = DatabaseManager()
                
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT telegram_bot_token, telegram_chat_id 
                        FROM admin_notification_settings 
                        WHERE id = 1
                    """)
                    row = cursor.fetchone()
                    if row:
                        self.telegram_bot_token = row[0] or self.telegram_bot_token
                        self.telegram_chat_id = row[1] or self.telegram_chat_id
                
                logger.info("✅ تم تحميل إعدادات Telegram")
        except Exception as e:
            logger.warning(f"⚠️ فشل تحميل إعدادات Telegram: {e}")
    
    def send_telegram_alert(self, alert_type: str, details: dict = None):
        """
        إرسال تنبيه واضح ومفصّل عبر Telegram
        
        alert_type: نوع التنبيه
        details: تفاصيل إضافية
        """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logger.warning("⚠️ Telegram غير مُعد")
            return False
        
        # قوالب الرسائل الواضحة
        templates = {
            'backend_down': {
                'emoji': '🚨',
                'title': 'تنبيه عاجل: الخادم متوقف',
                'message': '''
🔴 *حالة الخادم: متوقف*

━━━━━━━━━━━━━━━━━━━━
📍 *المشكلة:*
لا يمكن الوصول إلى Backend API

⚠️ *التأثير:*
• التداول الآلي متوقف
• التطبيق لا يستجيب
• لا يمكن تنفيذ أوامر

🔧 *الإجراء المطلوب:*
1. تحقق من السيرفر
2. أعد تشغيل الخدمة:
   `python3 start_server.py`
━━━━━━━━━━━━━━━━━━━━
'''
            },
            'backend_recovered': {
                'emoji': '✅',
                'title': 'تم استعادة الخادم',
                'message': '''
🟢 *حالة الخادم: يعمل*

━━━━━━━━━━━━━━━━━━━━
✅ تم استعادة الاتصال بـ Backend
✅ API يستجيب بشكل طبيعي
✅ يمكن استئناف التداول
━━━━━━━━━━━━━━━━━━━━
'''
            },
            'database_down': {
                'emoji': '🚨',
                'title': 'تنبيه عاجل: قاعدة البيانات متوقفة',
                'message': '''
🔴 *حالة Database: متوقفة*

━━━━━━━━━━━━━━━━━━━━
📍 *المشكلة:*
لا يمكن الوصول إلى قاعدة البيانات

⚠️ *التأثير:*
• لا يمكن حفظ/قراءة البيانات
• الصفقات لن تُسجّل
• النظام في حالة خطر

🔧 *الإجراء المطلوب:*
1. تحقق من ملف قاعدة البيانات
2. تحقق من مساحة القرص
3. أعد تشغيل الخدمة
━━━━━━━━━━━━━━━━━━━━
'''
            },
            'database_recovered': {
                'emoji': '✅',
                'title': 'تم استعادة قاعدة البيانات',
                'message': '''
🟢 *حالة Database: تعمل*

━━━━━━━━━━━━━━━━━━━━
✅ تم استعادة الاتصال بقاعدة البيانات
✅ يمكن حفظ وقراءة البيانات
━━━━━━━━━━━━━━━━━━━━
'''
            },
            'trading_stopped': {
                'emoji': '⚠️',
                'title': 'نظام التداول متوقف',
                'message': '''
🟡 *حالة التداول: متوقف*

━━━━━━━━━━━━━━━━━━━━
📍 *الحالة:* {status}
📅 *آخر تحديث:* {last_update}

💡 *ملاحظة:*
قد يكون التوقف مقصوداً.
تحقق من لوحة التحكم.
━━━━━━━━━━━━━━━━━━━━
'''
            },
            'trading_resumed': {
                'emoji': '✅',
                'title': 'نظام التداول يعمل',
                'message': '''
🟢 *حالة التداول: يعمل*

━━━━━━━━━━━━━━━━━━━━
✅ تم استئناف التداول الآلي
✅ النظام يراقب السوق
━━━━━━━━━━━━━━━━━━━━
'''
            },
            'monitor_started': {
                'emoji': '🔍',
                'title': 'المراقب الخارجي بدأ',
                'message': '''
🔵 *المراقب الخارجي نشط*

━━━━━━━━━━━━━━━━━━━━
📊 *يراقب:*
• حالة Backend API
• حالة قاعدة البيانات
• حالة نظام التداول

⏱️ *فترة الفحص:* كل {interval} ثانية

💡 ستصلك إشعارات فورية عند:
• توقف أي خدمة
• استعادة الخدمة
━━━━━━━━━━━━━━━━━━━━
'''
            },
            'health_report': {
                'emoji': '📊',
                'title': 'تقرير صحة النظام',
                'message': '''
📊 *تقرير صحة النظام*

━━━━━━━━━━━━━━━━━━━━
{backend_status} *Backend:* {backend}
{db_status} *Database:* {database}
{trading_status} *Trading:* {trading}
━━━━━━━━━━━━━━━━━━━━
'''
            }
        }
        
        template = templates.get(alert_type, {
            'emoji': '📢',
            'title': alert_type,
            'message': str(details)
        })
        
        # تعبئة القالب بالتفاصيل
        message = template['message']
        if details:
            message = message.format(**details)
        
        # بناء الرسالة النهائية
        text = f"{template['emoji']} *{template['title']}*\n{message}\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"❌ فشل إرسال Telegram: {e}")
            return False
    
    def check_backend_health(self) -> bool:
        """فحص صحة Backend"""
        try:
            response = requests.get(
                f"{self.api_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def check_database_health(self) -> bool:
        """فحص صحة قاعدة البيانات"""
        try:
            if not self.db_path.exists():
                return False
            
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
            
            return True
        except Exception:
            return False
    
    def check_trading_system(self) -> dict:
        """فحص حالة نظام التداول"""
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT status, is_running, last_update 
                    FROM system_status 
                    WHERE id = 1
                """)
                row = cursor.fetchone()
            
            if row:
                return {
                    'status': row[0],
                    'is_running': bool(row[1]),
                    'last_update': row[2]
                }
            return {'status': 'unknown', 'is_running': False}
        except Exception:
            return {'status': 'error', 'is_running': False}
    
    def run_health_check(self):
        """تشغيل فحص صحة شامل"""
        logger.info("🔍 بدء فحص الصحة...")
        
        # 1. فحص Backend
        backend_ok = self.check_backend_health()
        if not backend_ok and self.last_backend_status:
            # Backend توقف للتو
            self.send_telegram_alert('backend_down')
            logger.error("❌ Backend لا يستجيب")
        elif backend_ok and not self.last_backend_status:
            # Backend عاد للعمل
            self.send_telegram_alert('backend_recovered')
            logger.info("✅ Backend يعمل مجدداً")
        self.last_backend_status = backend_ok
        
        # 2. فحص Database
        db_ok = self.check_database_health()
        if not db_ok and self.last_db_status:
            self.send_telegram_alert('database_down')
            logger.error("❌ Database لا تستجيب")
        elif db_ok and not self.last_db_status:
            self.send_telegram_alert('database_recovered')
        self.last_db_status = db_ok
        
        # 3. فحص نظام التداول
        if db_ok:
            trading = self.check_trading_system()
            trading_ok = trading.get('is_running', False)
            
            if not trading_ok and self.last_trading_status:
                self.send_telegram_alert('trading_stopped', {
                    'status': trading.get('status', 'unknown'),
                    'last_update': trading.get('last_update', 'N/A')
                })
            elif trading_ok and not self.last_trading_status:
                self.send_telegram_alert('trading_resumed')
            self.last_trading_status = trading_ok
        
        # تحديث عداد الفشل
        if not backend_ok or not db_ok:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0
        
        return {
            'backend': backend_ok,
            'database': db_ok,
            'trading': self.last_trading_status,
            'consecutive_failures': self.consecutive_failures
        }
    
    def run_forever(self, interval: int = 60):
        """تشغيل المراقبة بشكل مستمر"""
        logger.info(f"🚀 بدء المراقبة الخارجية (كل {interval} ثانية)")
        
        # إرسال رسالة بدء
        self.send_telegram_alert('monitor_started', {'interval': interval})
        
        while True:
            try:
                result = self.run_health_check()
                
                status = "✅" if all([result['backend'], result['database']]) else "❌"
                logger.info(f"{status} Backend: {result['backend']}, DB: {result['database']}, Trading: {result['trading']}")
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("⏹️ إيقاف المراقبة")
                break
            except Exception as e:
                logger.error(f"❌ خطأ في المراقبة: {e}")
                time.sleep(interval)


def main():
    """نقطة الدخول الرئيسية"""
    import argparse
    
    parser = argparse.ArgumentParser(description='مراقب صحة النظام الخارجي')
    parser.add_argument('--interval', type=int, default=60, help='فترة الفحص بالثواني')
    parser.add_argument('--once', action='store_true', help='فحص مرة واحدة فقط')
    args = parser.parse_args()
    
    monitor = ExternalHealthMonitor()
    
    if args.once:
        result = monitor.run_health_check()
        print(f"Backend: {'✅' if result['backend'] else '❌'}")
        print(f"Database: {'✅' if result['database'] else '❌'}")
        print(f"Trading: {'✅' if result['trading'] else '❌'}")
    else:
        monitor.run_forever(interval=args.interval)


if __name__ == '__main__':
    main()
