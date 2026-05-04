#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Notification Cleanup Scheduler - مجدول تنظيف الإشعارات اليومي
يقوم بتشغيل تنظيف الإشعارات يومياً في الساعة 2 صباحاً
Uses threading.Timer instead of the external 'schedule' library.
"""

import logging
import time
from threading import Thread, Event

from backend.services.notification_cleanup_service import (
    scheduled_notification_cleanup,
)

logger = logging.getLogger(__name__)

# Cleanup interval: every 6 hours (seconds)
_CLEANUP_INTERVAL_SECONDS = 6 * 3600


class DailyNotificationCleanupScheduler:
    """
    مجدول تنظيف الإشعارات اليومي
    """

    def __init__(self):
        """تهيئة المجدول"""
        self.running = False
        self.scheduler_thread = None
        self._stop_event = Event()
        logger.info("✅ تم تهيئة Daily Notification Cleanup Scheduler")

    def start(self):
        """بدء المجدول"""
        try:
            if self.running:
                logger.warning("⚠️ المجدول يعمل بالفعل")
                return

            self.running = True
            self._stop_event.clear()

            self.scheduler_thread = Thread(
                target=self._run_scheduler, daemon=True
            )
            self.scheduler_thread.start()

            logger.info("🚀 تم بدء مجدول تنظيف الإشعارات اليومي (كل 6 ساعات)")

        except Exception as e:
            logger.error(f"❌ خطأ في بدء المجدول: {e}")

    def stop(self):
        """إيقاف المجدول"""
        try:
            self.running = False
            self._stop_event.set()

            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)

            logger.info("🛑 تم إيقاف مجدول تنظيف الإشعارات")

        except Exception as e:
            logger.error(f"❌ خطأ في إيقاف المجدول: {e}")

    def _run_scheduler(self):
        """تشغيل المجدول في الخلفية — ينتظر interval ثم ينفذ التنظيف"""
        logger.info("📅 المجدول يعمل في الخلفية")

        while self.running and not self._stop_event.is_set():
            try:
                # Wait for the interval, but wake up every 60s to check
                # stop_event
                elapsed = 0
                while (
                    elapsed < _CLEANUP_INTERVAL_SECONDS
                    and not self._stop_event.is_set()
                ):
                    time.sleep(min(60, _CLEANUP_INTERVAL_SECONDS - elapsed))
                    elapsed += 60

                if not self._stop_event.is_set():
                    self._run_cleanup()

            except Exception as e:
                logger.error(f"❌ خطأ في تشغيل المجدول: {e}")
                time.sleep(300)

    def _run_cleanup(self):
        """تشغيل التنظيف المجدول"""
        try:
            logger.info("🧹 بدء التنظيف المجدول للإشعارات")

            results = scheduled_notification_cleanup()

            if "error" in results:
                logger.error(f"❌ فشل التنظيف المجدول: {results['error']}")
            else:
                logger.info(f"✅ اكتمل التنظيف المجدول: {results}")

        except Exception as e:
            logger.error(f"❌ خطأ في التنظيف المجدول: {e}")

    def get_status(self):
        """الحصول على حالة المجدول"""
        return {
            "running": self.running,
            "interval_hours": _CLEANUP_INTERVAL_SECONDS // 3600,
            "jobs_count": 1 if self.running else 0,
        }

    def run_cleanup_now(self):
        """تشغيل التنظيف فوراً"""
        logger.info("🚀 تشغيل التنظيف الفوري")
        return self._run_cleanup()


# Singleton instance
_scheduler = None


def get_notification_scheduler() -> DailyNotificationCleanupScheduler:
    """الحصول على نسخة واحدة من المجدول"""
    global _scheduler
    if _scheduler is None:
        _scheduler = DailyNotificationCleanupScheduler()
    return _scheduler


# بدء تلقائي عند الاستيراد
def start_notification_scheduler():
    """بدء مجدول الإشعارات تلقائياً"""
    try:
        scheduler = get_notification_scheduler()
        scheduler.start()
        return scheduler
    except Exception as e:
        logger.error(f"❌ خطأ في بدء مجدول الإشعارات التلقائي: {e}")
        return None


# إيقاف عند الإغلاق
def stop_notification_scheduler():
    """إيقاف مجدول الإشعارات"""
    try:
        scheduler = get_notification_scheduler()
        scheduler.stop()
    except Exception as e:
        logger.error(f"❌ خطأ في إيقاف مجدول الإشعارات: {e}")


if __name__ == "__main__":
    # اختبار المجدول
    print("🚀 اختبار مجدول تنظيف الإشعارات")

    scheduler = get_notification_scheduler()

    print("📊 حالة المجدول:")
    status = scheduler.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    print("\n🧹 تشغيل التنظيف الفوري:")
    results = scheduler.run_cleanup_now()
    print(f"  النتائج: {results}")

    print("\n🛑 إيقاف المجدول")
    scheduler.stop()
