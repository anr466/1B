#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام Group B - التداول الفعلي
==============================

المسؤولية:
- مراقبة الصفقات المفتوحة
- فحص شروط الخروج والدخول
- تنفيذ أوامر الشراء والبيع
- إدارة المحفظة
- إرسال الإشعارات

الاستخدام:
python3 run_group_b.py [--user-id 1] [--duration 24]

الخيارات:
  --user-id:    معرف المستخدم (افتراضي: 1 للأدمن)
  --duration:   مدة المراقبة بالساعات (افتراضي: 24)
"""

import os
import sys
import logging
import argparse
import signal
from pathlib import Path
from datetime import datetime

# إضافة المسار الأساسي
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.database_manager import DatabaseManager
from backend.core.group_b_system import GroupBSystem

# إعداد المسجل الموحد
from config.logging_config import get_logger
logger = get_logger(__name__)

# متغير عام للتحكم في الإيقاف
group_b_instance = None
is_running = True


def signal_handler(signum, frame):
    """معالج إشارة الإيقاف"""
    global is_running, group_b_instance
    
    logger.info("⏹️ تم استقبال إشارة إيقاف...")
    is_running = False
    
    if group_b_instance:
        logger.info("🛑 إيقاف Group B...")
        group_b_instance.stop_monitoring()
    
    logger.info("✅ تم إيقاف البرنامج بنجاح")
    sys.exit(0)


def validate_user(user_id):
    """التحقق من وجود المستخدم"""
    try:
        db_manager = DatabaseManager()
        user = db_manager.get_user_by_id(user_id)
        
        if not user:
            logger.error(f"❌ المستخدم {user_id} غير موجود")
            return False
        
        logger.info(f"✅ تم العثور على المستخدم: {user.get('username', 'N/A')}")
        return True
    
    except Exception as e:
        logger.error(f"❌ خطأ في التحقق من المستخدم: {e}")
        return False


def run_group_b(user_id=1, duration_hours=24):
    """
    تشغيل نظام Group B
    
    Args:
        user_id: معرف المستخدم (افتراضي: 1 للأدمن)
        duration_hours: مدة المراقبة بالساعات (افتراضي: 24)
    """
    global group_b_instance, is_running
    
    try:
        logger.info("=" * 80)
        logger.info("🟢 بدء نظام Group B - التداول الفعلي")
        logger.info("=" * 80)
        
        # التحقق من المستخدم
        if not validate_user(user_id):
            logger.error("❌ فشل التحقق من المستخدم")
            return False
        
        # إنشاء مثيل من Group B
        logger.info(f"📊 تهيئة نظام التداول للمستخدم {user_id}...")
        group_b_instance = GroupBSystem(user_id=user_id)
        
        # التحقق من تحميل الإعدادات
        if not group_b_instance.can_trade:
            logger.warning(f"⚠️ المستخدم {user_id} غير مفعل للتداول")
            logger.info("ℹ️ سيتم مراقبة الصفقات المفتوحة فقط")
        
        # عرض معلومات النظام
        logger.info(f"📋 معلومات النظام:")
        logger.info(f"   • معرف المستخدم: {user_id}")
        logger.info(f"   • نوع التداول: {'وهمي' if group_b_instance.is_demo_trading else 'حقيقي'}")
        logger.info(f"   • التداول مفعل: {group_b_instance.user_settings.get('trading_enabled', False)}")
        logger.info(f"   • الرصيد المتاح: {group_b_instance.user_portfolio.get('balance', 0):.2f} USDT")
        logger.info(f"   • مدة المراقبة: {duration_hours} ساعة")
        
        # بدء المراقبة
        logger.info(f"\n🚀 بدء مراقبة التداول...")
        logger.info(f"⏱️ سيتم تحديث الصفقات كل 60 ثانية")
        
        # بدء المراقبة
        logger.info("📊 بدء دورة المراقبة والتداول...")
        group_b_instance.start_monitoring(duration_hours=duration_hours)
        
        logger.info("=" * 80)
        logger.info("✅ انتهت فترة المراقبة")
        logger.info("=" * 80)
        
        return True
    
    except KeyboardInterrupt:
        logger.info("⏹️ تم إيقاف البرنامج بواسطة المستخدم")
        return True
    
    except Exception as e:
        logger.error(f"❌ خطأ في Group B: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """الدالة الرئيسية"""
    parser = argparse.ArgumentParser(
        description='نظام Group B - التداول الفعلي',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
أمثلة الاستخدام:
  python3 run_group_b.py                    # تشغيل للأدمن (user_id=1) لمدة 24 ساعة
  python3 run_group_b.py --user-id 5       # تشغيل للمستخدم 5 لمدة 24 ساعة
  python3 run_group_b.py --duration 12     # تشغيل للأدمن لمدة 12 ساعة
  python3 run_group_b.py --user-id 5 --duration 6  # تشغيل للمستخدم 5 لمدة 6 ساعات
        """
    )
    
    parser.add_argument(
        '--user-id',
        type=int,
        default=1,
        help='معرف المستخدم (افتراضي: 1 للأدمن)'
    )
    
    parser.add_argument(
        '--duration',
        type=int,
        default=24,
        help='مدة المراقبة بالساعات (افتراضي: 24)'
    )
    
    args = parser.parse_args()
    
    # تسجيل معالج الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # تشغيل Group B
    success = run_group_b(user_id=args.user_id, duration_hours=args.duration)
    
    # الخروج
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
