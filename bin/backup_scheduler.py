#!/usr/bin/env python3
"""
🗄️ مُجدوِل النسخ الاحتياطي الخارجي
External Backup Scheduler

مسؤول عن:
1. نسخة يومية تلقائية (كل 24 ساعة)
2. نسخة أسبوعية (كل 7 أيام)
3. تنظيف النسخ القديمة

يعمل كـ process منفصل عن النظام الرئيسي
"""

import os
import sys
import time
import logging
import schedule
from datetime import datetime
from pathlib import Path

# إعداد المسارات
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.backup_manager import BackupManager

# إعداد التسجيل الموحد
from config.logging_config import get_logger
logger = get_logger(__name__)


class BackupScheduler:
    """مُجدوِل النسخ الاحتياطي"""
    
    def __init__(self):
        self.backup_manager = BackupManager()
        self.is_running = False
        
    def create_daily_backup(self):
        """إنشاء نسخة يومية"""
        logger.info("⏰ بدء النسخ الاحتياطي اليومي...")
        try:
            path = self.backup_manager.create_backup("daily")
            if path:
                logger.info(f"✅ تم إنشاء النسخة اليومية: {path}")
            else:
                logger.error("❌ فشل إنشاء النسخة اليومية")
        except Exception as e:
            logger.error(f"❌ خطأ في النسخ اليومي: {e}")
    
    def create_weekly_backup(self):
        """إنشاء نسخة أسبوعية"""
        logger.info("⏰ بدء النسخ الاحتياطي الأسبوعي...")
        try:
            path = self.backup_manager.create_backup("weekly")
            if path:
                logger.info(f"✅ تم إنشاء النسخة الأسبوعية: {path}")
            else:
                logger.error("❌ فشل إنشاء النسخة الأسبوعية")
        except Exception as e:
            logger.error(f"❌ خطأ في النسخ الأسبوعي: {e}")
    
    def cleanup_old_backups(self):
        """تنظيف النسخ القديمة"""
        logger.info("🧹 تنظيف النسخ القديمة...")
        try:
            deleted = self.backup_manager.cleanup_old_backups()
            if deleted > 0:
                logger.info(f"✅ تم حذف {deleted} نسخة قديمة")
        except Exception as e:
            logger.error(f"❌ خطأ في التنظيف: {e}")
    
    def setup_schedule(self):
        """إعداد الجدولة"""
        # نسخة يومية الساعة 3 صباحاً
        schedule.every().day.at("03:00").do(self.create_daily_backup)
        
        # نسخة أسبوعية كل جمعة الساعة 4 صباحاً
        schedule.every().friday.at("04:00").do(self.create_weekly_backup)
        
        # تنظيف كل يوم الساعة 5 صباحاً
        schedule.every().day.at("05:00").do(self.cleanup_old_backups)
        
        logger.info("📅 تم إعداد الجدولة:")
        logger.info("   • نسخة يومية: 03:00 صباحاً")
        logger.info("   • نسخة أسبوعية: الجمعة 04:00 صباحاً")
        logger.info("   • تنظيف: 05:00 صباحاً")
    
    def run_forever(self):
        """تشغيل المُجدوِل بشكل مستمر"""
        self.is_running = True
        self.setup_schedule()
        
        logger.info("🚀 مُجدوِل النسخ الاحتياطي بدأ")
        
        # إنشاء نسخة فورية عند البدء
        self.create_daily_backup()
        
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # فحص كل دقيقة
            except KeyboardInterrupt:
                logger.info("⏹️ إيقاف المُجدوِل")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"❌ خطأ: {e}")
                time.sleep(60)
    
    def run_once(self, backup_type: str = "manual"):
        """تشغيل نسخة واحدة فقط"""
        logger.info(f"📦 إنشاء نسخة {backup_type}...")
        path = self.backup_manager.create_backup(backup_type)
        if path:
            logger.info(f"✅ تم: {path}")
        else:
            logger.error("❌ فشل")
        return path
    
    def status(self):
        """عرض حالة النسخ الاحتياطية"""
        backups = self.backup_manager.list_backups()
        
        print("\n" + "=" * 50)
        print("📦 حالة النسخ الاحتياطية")
        print("=" * 50)
        
        if not backups:
            print("❌ لا توجد نسخ احتياطية")
        else:
            for b in backups:
                size_mb = b['size'] / (1024 * 1024)
                created = b['created'].strftime("%Y-%m-%d %H:%M")
                print(f"  • {b['type']:10} | {size_mb:.2f} MB | {created}")
        
        print("=" * 50 + "\n")


def main():
    """نقطة الدخول الرئيسية"""
    import argparse
    
    parser = argparse.ArgumentParser(description='مُجدوِل النسخ الاحتياطي')
    parser.add_argument('--once', type=str, help='إنشاء نسخة واحدة (daily, weekly, manual)')
    parser.add_argument('--status', action='store_true', help='عرض حالة النسخ')
    parser.add_argument('--daemon', action='store_true', help='تشغيل كـ daemon')
    args = parser.parse_args()
    
    scheduler = BackupScheduler()
    
    if args.status:
        scheduler.status()
    elif args.once:
        scheduler.run_once(args.once)
    elif args.daemon:
        scheduler.run_forever()
    else:
        # الافتراضي: عرض الحالة
        scheduler.status()
        print("الاستخدام:")
        print("  --daemon    تشغيل الجدولة التلقائية")
        print("  --once TYPE إنشاء نسخة واحدة (daily, weekly, manual)")
        print("  --status    عرض حالة النسخ")


if __name__ == '__main__':
    main()
