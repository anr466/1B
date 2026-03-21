#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notification Cleanup Service - خدمة تنظيف الإشعارات
تنظيف تلقائي للإشعارات القديمة بناءً على سياسة واضحة
"""

import logging
from typing import Dict, Any

from backend.infrastructure.db_access import get_db_manager

logger = logging.getLogger(__name__)


class NotificationCleanupService:
    """
    خدمة تنظيف الإشعارات التلقائي
    
    السياسة:
    - الإشعارات المقروءة: تحذف بعد 7 أيام
    - الإشعارات غير المقروءة: تحذف بعد 30 يوم
    - الإشعارات النظامية: تحذف بعد 3 أيام
    - الحد الأقصى: 1000 إشعار لكل مستخدم
    """
    READ_RETENTION_DAYS = 7
    UNREAD_RETENTION_DAYS = 30
    SYSTEM_RETENTION_DAYS = 3
    MAX_NOTIFICATIONS_PER_USER = 1000
    
    def __init__(self):
        """تهيئة الخدمة"""
        self.db = get_db_manager()
        logger.info("✅ تم تهيئة Notification Cleanup Service")
    
    def cleanup_notifications(self, user_id: int = None) -> Dict[str, Any]:
        """
        تنظيف الإشعارات بناءً على السياسة
        
        Args:
            user_id: المستخدم المحدد (None للجميع)
            
        Returns:
            Dict: نتائج التنظيف
        """
        try:
            results = {
                'read_deleted': 0,
                'unread_deleted': 0,
                'system_deleted': 0,
                'total_deleted': 0,
                'limit_deleted': 0,
            }
            
            # 1. حذف الإشعارات المقروءة (أقدم من 7 أيام)
            read_deleted = self._cleanup_read_notifications(user_id)
            results['read_deleted'] = read_deleted
            
            # 2. حذف الإشعارات غير المقروءة (أقدم من 30 يوم)
            unread_deleted = self._cleanup_unread_notifications(user_id)
            results['unread_deleted'] = unread_deleted
            
            # 3. حذف الإشعارات النظامية (أقدم من 3 أيام)
            system_deleted = self._cleanup_system_notifications(user_id)
            results['system_deleted'] = system_deleted
            
            # 4. فرض الحد الأقصى للإشعارات
            limit_deleted = self._enforce_notification_limit(user_id)
            results['limit_deleted'] = limit_deleted
            
            # 5. حساب الإجمالي
            results['total_deleted'] = sum([
                results['read_deleted'],
                results['unread_deleted'], 
                results['system_deleted'],
                results['limit_deleted']
            ])
            
            logger.info(f"🧹 تم تنظيف {results['total_deleted']} إشعار")
            return results
            
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف الإشعارات: {e}")
            return {'error': str(e), 'total_deleted': 0}
    
    def _cleanup_read_notifications(self, user_id: int = None) -> int:
        """حذف الإشعارات المقروءة الأقدم من 7 أيام"""
        try:
            where_clause = (
                "WHERE is_read = TRUE "
                f"AND created_at < (CURRENT_TIMESTAMP - INTERVAL '{self.READ_RETENTION_DAYS} days')"
            )
            params = []
            
            if user_id:
                where_clause += " AND user_id = %s"
                params.append(user_id)
            
            query = f"DELETE FROM notifications {where_clause}"
            
            with self.db.get_write_connection() as conn:
                cursor = conn.execute(query, params)
                deleted_count = cursor.rowcount
                conn.commit()
                
            logger.info(f"📖 تم حذف {deleted_count} إشعار مقروء")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ خطأ في حذف الإشعارات المقروءة: {e}")
            return 0
    
    def _cleanup_unread_notifications(self, user_id: int = None) -> int:
        """حذف الإشعارات غير المقروءة الأقدم من 30 يوم"""
        try:
            where_clause = (
                "WHERE is_read = FALSE "
                f"AND created_at < (CURRENT_TIMESTAMP - INTERVAL '{self.UNREAD_RETENTION_DAYS} days')"
            )
            params = []
            
            if user_id:
                where_clause += " AND user_id = %s"
                params.append(user_id)
            
            query = f"DELETE FROM notifications {where_clause}"
            
            with self.db.get_write_connection() as conn:
                cursor = conn.execute(query, params)
                deleted_count = cursor.rowcount
                conn.commit()
                
            logger.info(f"📕 تم حذف {deleted_count} إشعار غير مقروء")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ خطأ في حذف الإشعارات غير المقروءة: {e}")
            return 0
    
    def _cleanup_system_notifications(self, user_id: int = None) -> int:
        """حذف الإشعارات النظامية الأقدم من 3 أيام"""
        try:
            where_clause = (
                "WHERE type IN ('system', 'error', 'info') "
                f"AND created_at < (CURRENT_TIMESTAMP - INTERVAL '{self.SYSTEM_RETENTION_DAYS} days')"
            )
            params = []
            
            if user_id:
                where_clause += " AND user_id = %s"
                params.append(user_id)
            
            query = f"DELETE FROM notifications {where_clause}"
            
            with self.db.get_write_connection() as conn:
                cursor = conn.execute(query, params)
                deleted_count = cursor.rowcount
                conn.commit()
                
            logger.info(f"⚙️ تم حذف {deleted_count} إشعار نظام")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ خطأ في حذف إشعارات النظام: {e}")
            return 0
    
    def _enforce_notification_limit(self, user_id: int = None) -> int:
        """فرض الحد الأقصى للإشعارات (1000 لكل مستخدم)"""
        try:
            deleted_count = 0
            
            if user_id:
                # حذف الإشعارات الزائدة لمستخدم واحد
                deleted_count = self._delete_excess_notifications(user_id, self.MAX_NOTIFICATIONS_PER_USER)
            else:
                # جلب كل المستخدمين الذين لديهم إشعارات زائدة
                query = """
                    SELECT user_id, COUNT(*) as count
                    FROM notifications
                    GROUP BY user_id
                    HAVING COUNT(*) > %s
                """
                
                users = self.db.execute_query(query, (self.MAX_NOTIFICATIONS_PER_USER,))
                
                for user in users:
                    user_id = user['user_id']
                    excess_deleted = self._delete_excess_notifications(user_id, self.MAX_NOTIFICATIONS_PER_USER)
                    deleted_count += excess_deleted
            
            if deleted_count > 0:
                logger.info(f"📊 تم حذف {deleted_count} إشعار زائد عن الحد")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ خطأ في فرض حدود الإشعارات: {e}")
            return 0
    
    def _delete_excess_notifications(self, user_id: int, limit: int) -> int:
        """حذف الإشعارات الزائدة لمستخدم معين"""
        try:
            total_result = self.db.execute_query(
                "SELECT COUNT(*) AS total FROM notifications WHERE user_id = %s",
                (user_id,),
            )
            total_notifications = total_result[0]['total'] if total_result else 0
            if total_notifications <= limit:
                return 0

            # حذف أقدم الإشعارات الزائدة مع الاحتفاظ بآخر `limit`
            query = """
                DELETE FROM notifications
                WHERE user_id = %s
                AND id IN (
                    SELECT id FROM notifications
                    WHERE user_id = %s
                    ORDER BY created_at DESC, id DESC
                    OFFSET %s
                )
            """
            
            with self.db.get_write_connection() as conn:
                cursor = conn.execute(query, (user_id, user_id, limit))
                deleted_count = cursor.rowcount
                conn.commit()
                
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ خطأ في حذف الإشعارات الزائدة للمستخدم {user_id}: {e}")
            return 0
    
    def get_cleanup_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات التنظيف"""
        try:
            stats = {}
            
            # إجمالي الإشعارات
            total_query = "SELECT COUNT(*) as total FROM notifications"
            total_result = self.db.execute_query(total_query)
            stats['total_notifications'] = total_result[0]['total'] if total_result else 0
            
            # الإشعارات المقروءة
            read_query = "SELECT COUNT(*) as count FROM notifications WHERE is_read = TRUE"
            read_result = self.db.execute_query(read_query)
            stats['read_notifications'] = read_result[0]['count'] if read_result else 0
            
            # الإشعارات غير المقروءة
            unread_query = "SELECT COUNT(*) as count FROM notifications WHERE is_read = FALSE"
            unread_result = self.db.execute_query(unread_query)
            stats['unread_notifications'] = unread_result[0]['count'] if unread_result else 0
            
            # الإشعارات القديمة
            old_read_query = (
                "SELECT COUNT(*) as count FROM notifications "
                f"WHERE is_read = TRUE AND created_at < (CURRENT_TIMESTAMP - INTERVAL '{self.READ_RETENTION_DAYS} days')"
            )
            old_read_result = self.db.execute_query(old_read_query)
            stats['old_read_notifications'] = old_read_result[0]['count'] if old_read_result else 0
            
            old_unread_query = (
                "SELECT COUNT(*) as count FROM notifications "
                f"WHERE is_read = FALSE AND created_at < (CURRENT_TIMESTAMP - INTERVAL '{self.UNREAD_RETENTION_DAYS} days')"
            )
            old_unread_result = self.db.execute_query(old_unread_query)
            stats['old_unread_notifications'] = old_unread_result[0]['count'] if old_unread_result else 0
            
            # المستخدمين مع إشعارات زائدة
            excess_query = """
                SELECT COUNT(*) as count
                FROM (
                    SELECT user_id, COUNT(*) as notification_count
                    FROM notifications
                    GROUP BY user_id
                    HAVING COUNT(*) > %s
                )
            """
            excess_result = self.db.execute_query(excess_query, (self.MAX_NOTIFICATIONS_PER_USER,))
            stats['users_with_excess'] = excess_result[0]['count'] if excess_result else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إحصائيات التنظيف: {e}")
            return {'error': str(e)}


# Singleton instance
_cleanup_service = None

def get_notification_cleanup_service() -> NotificationCleanupService:
    """الحصول على نسخة واحدة من الخدمة"""
    global _cleanup_service
    if _cleanup_service is None:
        _cleanup_service = NotificationCleanupService()
    return _cleanup_service


# Scheduled cleanup function
def scheduled_notification_cleanup():
    """تنظيف مجدول للإشعارات (يتم استدعاؤه يومياً)"""
    try:
        service = get_notification_cleanup_service()
        results = service.cleanup_notifications()
        
        logger.info(f"🧹 التنظيف المجدول للإشعارات: {results}")
        return results
        
    except Exception as e:
        logger.error(f"❌ خطأ في التنظيف المجدول: {e}")
        return {'error': str(e)}


if __name__ == "__main__":
    # اختبار الخدمة
    service = get_notification_cleanup_service()
    
    print("📊 إحصائيات قبل التنظيف:")
    stats = service.get_cleanup_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\n🧹 بدء التنظيف:")
    results = service.cleanup_notifications()
    print(f"  النتائج: {results}")
    
    print("\n📊 إحصائيات بعد التنظيف:")
    stats_after = service.get_cleanup_stats()
    for key, value in stats_after.items():
        print(f"  {key}: {value}")
