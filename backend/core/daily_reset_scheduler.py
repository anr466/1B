#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Loss Reset Scheduler
يقوم بإعادة تعيين حدود الخسارة اليومية تلقائياً عند بداية كل يوم جديد
"""

import time
import logging
from datetime import datetime, time as dt_time, timedelta
from threading import Thread, Event

from backend.infrastructure.db_access import get_db_manager

class DailyResetScheduler:
    """
    جدولة إعادة تعيين الحدود اليومية
    """
    
    def __init__(self, db_manager=None, logger=None):
        """
        تهيئة المجدول
        
        Args:
            db_manager: مدير قاعدة البيانات (اختياري)
            logger: مسجل الأحداث (اختياري)
        """
        self.db = db_manager or get_db_manager()
        self.logger = logger or logging.getLogger(__name__)
        self.is_running = False
        self.scheduler_thread = None
        self._stop_event = Event()
        
        self.logger.info("✅ تم تهيئة Daily Reset Scheduler")
    
    def reset_all_daily_limits(self):
        """
        إعادة تعيين حدود الخسارة اليومية لجميع المستخدمين
        """
        try:
            now = datetime.now()
            self.logger.info(f"🔄 بدء إعادة تعيين الحدود اليومية - {now.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # جلب جميع المستخدمين النشطين
            users = self.db.execute_query("""
                SELECT id, username, user_type 
                FROM users 
                WHERE is_active = TRUE
            """)
            
            if not users:
                self.logger.warning("⚠️ لا يوجد مستخدمين نشطين")
                return
            
            # ✅ تسجيل snapshot يومي للمحافظ قبل إعادة التعيين
            try:
                snap_count = self.db.record_all_portfolios_snapshot()
                self.logger.info(f"📸 تم تسجيل {snap_count} snapshot يومي للمحافظ")
            except Exception as snap_err:
                self.logger.warning(f"⚠️ تعذّر تسجيل snapshots المحافظ: {snap_err}")

            reset_count = 0
            for user in users:
                user_id = user['id']
                username = user.get('username', f'User_{user_id}')
                
                try:
                    # لا يوجد شيء للحذف - الحدود تُحسب تلقائياً بناءً على التاريخ
                    # لكن يمكن إعادة تفعيل التداول إذا كان معطل بسبب Daily Loss
                    self._reactivate_trading_if_needed(user_id)
                    reset_count += 1
                    
                except Exception as user_error:
                    self.logger.error(f"❌ خطأ في إعادة التعيين للمستخدم {username}: {user_error}")
            
            self.logger.info(
                f"✅ تم إعادة تعيين الحدود لـ {reset_count} مستخدم من أصل {len(users)}"
            )
            
            # إرسال إشعار للأدمن
            self._notify_admin_reset(reset_count, len(users))
            
        except Exception as e:
            self.logger.error(f"❌ خطأ حرج في إعادة تعيين الحدود اليومية: {e}")
    
    def _reactivate_trading_if_needed(self, user_id: int):
        """
        إعادة تفعيل التداول إذا كان معطل بسبب Daily Loss
        
        Args:
            user_id: معرف المستخدم
        """
        try:
            # فحص إعدادات المستخدم
            settings = self.db.get_trading_settings(user_id)
            
            if not settings:
                return
            
            # إذا كان التداول معطل، نفحص السبب من activity_logs
            if not settings.get('trading_enabled'):
                recent_logs = self.db.execute_query("""
                    SELECT action, details 
                    FROM activity_logs 
                    WHERE user_id = %s 
                    AND action LIKE %s
                    ORDER BY created_at DESC 
                    LIMIT 1
                """, (user_id, '%daily_loss%'))
                
                if recent_logs:
                    # إعادة تفعيل التداول لكلا المحفظتين (demo و real)
                    for portfolio_is_demo in (False, True):
                        self.db.update_trading_settings(
                            user_id, {'trading_enabled': True}, is_demo=portfolio_is_demo
                        )
                    self.logger.info(f"✅ تم إعادة تفعيل التداول للمستخدم {user_id} (يوم جديد)")

                    # تسجيل في activity_logs
                    self.db.add_activity_log(
                        user_id=user_id,
                        action='daily_reset_reactivate_trading',
                        details='تم إعادة تفعيل التداول تلقائياً بعد بداية يوم جديد',
                        component='DailyResetScheduler'
                    )
        
        except Exception as e:
            self.logger.error(f"خطأ في إعادة تفعيل التداول للمستخدم {user_id}: {e}")
    
    def _notify_admin_reset(self, reset_count: int, total_users: int):
        """
        إرسال إشعار للأدمن بنجاح إعادة التعيين
        
        Args:
            reset_count: عدد المستخدمين الذين تم إعادة تعيينهم
            total_users: إجمالي المستخدمين
        """
        try:
            # جلب الأدمن
            admin = self.db.execute_query("""
                SELECT id FROM users WHERE user_type = 'admin' LIMIT 1
            """)
            
            if admin:
                admin_id = admin[0]['id']
                
                # إضافة إشعار
                self.db.execute_query("""
                    INSERT INTO notifications (user_id, title, message, type, created_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    admin_id,
                    '🔄 إعادة تعيين الحدود اليومية',
                    f'تم إعادة تعيين حدود الخسارة اليومية لـ {reset_count} من أصل {total_users} مستخدم بنجاح',
                    'system'
                ))
                
        except Exception as e:
            self.logger.debug(f"خطأ في إرسال الإشعار للأدمن: {e}")
    
    def _seconds_until(self, target_time_str: str) -> float:
        """حساب عدد الثواني حتى الوقت المحدد"""
        h, m = map(int, target_time_str.split(':'))
        now = datetime.now()
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return (target - now).total_seconds()
    
    def start(self, reset_time: str = "00:00"):
        """
        بدء المجدول في خيط منفصل
        
        Args:
            reset_time: وقت إعادة التعيين اليومي (HH:MM)
        """
        if self.is_running:
            self.logger.warning("⚠️ المجدول يعمل بالفعل")
            return
        
        self.is_running = True
        self._stop_event.clear()
        self._reset_time = reset_time
        self.scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info(f"✅ تم بدء Daily Reset Scheduler (إعادة تعيين يومية عند {reset_time})")
    
    def _run_scheduler(self):
        """
        تشغيل المجدول (يعمل في خيط منفصل)
        يستخدم threading.Event.wait بدلاً من schedule library
        """
        while self.is_running and not self._stop_event.is_set():
            try:
                wait_seconds = self._seconds_until(self._reset_time)
                self.logger.info(f"⏰ الانتظار {wait_seconds/3600:.1f} ساعة حتى إعادة التعيين التالية")
                
                # انتظار حتى الوقت المحدد أو حتى الإيقاف
                if self._stop_event.wait(timeout=wait_seconds):
                    break  # تم الإيقاف
                
                # تنفيذ إعادة التعيين
                self.reset_all_daily_limits()
                
                # انتظار دقيقة لتجنب التنفيذ المتكرر
                self._stop_event.wait(timeout=60)
                
            except Exception as e:
                self.logger.error(f"❌ خطأ في حلقة المجدول: {e}")
                self._stop_event.wait(timeout=60)
    
    def stop(self):
        """
        إيقاف المجدول
        """
        self.is_running = False
        self._stop_event.set()
        self.logger.info("🛑 تم إيقاف Daily Reset Scheduler")
    
    def force_reset_now(self):
        """
        فرض إعادة التعيين فوراً (للاختبار أو الطوارئ)
        """
        self.logger.warning("⚠️ فرض إعادة تعيين فورية للحدود اليومية")
        self.reset_all_daily_limits()


# ===== الاستخدام الرئيسي =====

_scheduler_instance = None

def get_daily_reset_scheduler(db_manager=None, logger=None):
    """
    الحصول على مثيل وحيد من المجدول (Singleton Pattern)
    
    Args:
        db_manager: مدير قاعدة البيانات
        logger: مسجل الأحداث
        
    Returns:
        DailyResetScheduler instance
    """
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = DailyResetScheduler(db_manager, logger)
    
    return _scheduler_instance


def start_daily_reset_scheduler(reset_time: str = "00:00"):
    """
    بدء المجدول (وظيفة سريعة)
    
    Args:
        reset_time: وقت إعادة التعيين (HH:MM)
    """
    scheduler = get_daily_reset_scheduler()
    scheduler.start(reset_time)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    scheduler = DailyResetScheduler()
    
    print("🧪 اختبار إعادة التعيين الفوري...")
    scheduler.force_reset_now()
    
    print("✅ تم. اضغط Ctrl+C للإيقاف.")
    try:
        scheduler.start("00:00")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 إيقاف المجدول...")
        scheduler.stop()
