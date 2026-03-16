"""
🔔 خدمة الإشعارات الموحدة - مرجع واحد فقط
يستخدمها جميع الـ endpoints والنظام الخلفي
"""

import json
from typing import Dict, List, Optional
from datetime import datetime
import logging

from database.database_manager import DatabaseManager


logger = logging.getLogger(__name__)


class NotificationService:
    """خدمة الإشعارات الموحدة"""
    
    def __init__(self):
        self.db = DatabaseManager()

    def _safe_json_loads(self, raw_value):
        if not raw_value:
            return {}
        if isinstance(raw_value, dict):
            return raw_value
        try:
            return json.loads(raw_value)
        except Exception:
            return {}
    
    # ==================== إرسال إشعار ====================
    
    def send_notification(self, user_id: int, notification_type: str, title: str, 
                         message: str, data: Optional[Dict] = None, 
                         priority: str = 'medium') -> bool:
        """
        إرسال إشعار للمستخدم
        
        Args:
            user_id: معرف المستخدم
            notification_type: نوع الإشعار (trade_opened, trade_closed, price_alert, etc)
            title: عنوان الإشعار
            message: نص الإشعار
            data: بيانات إضافية (JSON)
            priority: الأولوية (low, medium, high)
        
        Returns:
            success
        """
        try:
            # تحضير بيانات الإشعار
            notification_data = data or {}
            notification_data['notification_type'] = 'trade' if 'trade' in notification_type else 'system'
            notification_data['created_at'] = datetime.now().isoformat()
            
            # تحويل البيانات إلى JSON
            data_json = json.dumps(notification_data, ensure_ascii=False)
            
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                
                # حفظ الإشعار في جدول notifications الجديد
                cursor.execute("""
                    INSERT INTO notifications 
                    (user_id, title, message, type, is_read, created_at, data)
                    VALUES (?, ?, ?, ?, FALSE, CURRENT_TIMESTAMP, ?)
                """, (
                    user_id,
                    title,
                    message,
                    notification_type,
                    data_json
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال الإشعار: {e}")
            return False
    
    # ==================== جلب الإشعارات المعلقة ====================
    
    def get_pending_notifications(self, user_id: int, last_check: Optional[str] = None, 
                                 limit: int = 50) -> List[Dict]:
        """
        جلب الإشعارات المعلقة للمستخدم
        
        Returns:
            قائمة الإشعارات
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    if last_check:
                        cursor.execute("""
                            SELECT id, user_id, COALESCE(type, 'general') as type,
                                   title, message, data, NULL as priority,
                                   CASE WHEN COALESCE(is_read, FALSE) THEN 'read' ELSE 'sent' END as status,
                                   created_at
                            FROM notifications
                            WHERE user_id = ? AND created_at > ?
                            ORDER BY created_at DESC
                            LIMIT ?
                        """, (user_id, last_check, limit))
                    else:
                        cursor.execute("""
                            SELECT id, user_id, COALESCE(type, 'general') as type,
                                   title, message, data, NULL as priority,
                                   CASE WHEN COALESCE(is_read, FALSE) THEN 'read' ELSE 'sent' END as status,
                                   created_at
                            FROM notifications
                            WHERE user_id = ?
                            ORDER BY created_at DESC
                            LIMIT ?
                        """, (user_id, limit))
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    if last_check:
                        try:
                            cursor.execute("""
                                SELECT id, user_id, COALESCE(type, notification_type, 'general') as type,
                                       title, message, data, NULL as priority,
                                       status, created_at
                                FROM notification_history
                                WHERE user_id = ? AND status IN ('pending', 'sent')
                                AND created_at > ?
                                ORDER BY created_at DESC
                                LIMIT ?
                            """, (user_id, last_check, limit))
                        except Exception:
                            try:
                                conn.rollback()
                            except Exception:
                                pass
                            cursor.execute("""
                                SELECT id, user_id, COALESCE(type, notification_type, 'general') as type,
                                       title, message, NULL as data, NULL as priority,
                                       status, created_at
                                FROM notification_history
                                WHERE user_id = ? AND status IN ('pending', 'sent')
                                AND created_at > ?
                                ORDER BY created_at DESC
                                LIMIT ?
                            """, (user_id, last_check, limit))
                    else:
                        try:
                            cursor.execute("""
                                SELECT id, user_id, COALESCE(type, notification_type, 'general') as type,
                                       title, message, data, NULL as priority,
                                       status, created_at
                                FROM notification_history
                                WHERE user_id = ? AND status IN ('pending', 'sent')
                                ORDER BY created_at DESC
                                LIMIT ?
                            """, (user_id, limit))
                        except Exception:
                            try:
                                conn.rollback()
                            except Exception:
                                pass
                            cursor.execute("""
                                SELECT id, user_id, COALESCE(type, notification_type, 'general') as type,
                                       title, message, NULL as data, NULL as priority,
                                       status, created_at
                                FROM notification_history
                                WHERE user_id = ? AND status IN ('pending', 'sent')
                                ORDER BY created_at DESC
                                LIMIT ?
                            """, (user_id, limit))

                notifications = []
                for row in cursor.fetchall():
                    notifications.append({
                        'id': row[0],
                        'userId': row[1],
                        'type': row[2],
                        'title': row[3],
                        'message': row[4],
                        'data': self._safe_json_loads(row[5]),
                        'priority': row[6],
                        'status': row[7],
                        'createdAt': row[8]
                    })

                return notifications
        
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الإشعارات: {e}")
            return []
    
    # ==================== تحديث حالة الإشعار ====================
    
    def mark_notification_delivered(self, notification_id: int) -> bool:
        """وضع علامة على الإشعار كمُسلم"""
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        UPDATE notification_history
                        SET status = 'delivered'
                        WHERE id = ?
                    """, (notification_id,))
                    return True
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    cursor.execute("""
                        UPDATE notifications
                        SET is_read = COALESCE(is_read, FALSE)
                        WHERE id = ?
                    """, (notification_id,))
                    return True
        
        except Exception:
            return False
    
    def mark_notification_read(self, notification_id: int) -> bool:
        """وضع علامة على الإشعار كمقروء"""
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        UPDATE notifications
                        SET is_read = TRUE
                        WHERE id = ?
                    """, (notification_id,))
                    return True
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    cursor.execute("""
                        UPDATE notification_history
                        SET status = 'read', read_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (notification_id,))
                    return True
        
        except Exception:
            return False
    
    # ==================== جلب التاريخ ====================
    
    def get_notification_history(self, user_id: int, limit: int = 100) -> List[Dict]:
        """جلب تاريخ الإشعارات"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        SELECT id, COALESCE(type, 'general') as type, title, message, data,
                               NULL as priority,
                               CASE WHEN COALESCE(is_read, FALSE) THEN 'read' ELSE 'unread' END as status,
                               created_at,
                               NULL as delivered_at
                        FROM notifications
                        WHERE user_id = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (user_id, limit))
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    try:
                        cursor.execute("""
                            SELECT id, COALESCE(type, notification_type, 'general') as type,
                                   title, message, data, NULL as priority,
                                   status, created_at, NULL as delivered_at
                            FROM notification_history
                            WHERE user_id = ?
                            ORDER BY created_at DESC
                            LIMIT ?
                        """, (user_id, limit))
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        cursor.execute("""
                            SELECT id, COALESCE(type, notification_type, 'general') as type,
                                   title, message, NULL as data, NULL as priority,
                                   status, created_at, NULL as delivered_at
                            FROM notification_history
                            WHERE user_id = ?
                            ORDER BY created_at DESC
                            LIMIT ?
                        """, (user_id, limit))

                history = []
                for row in cursor.fetchall():
                    history.append({
                        'id': row[0],
                        'type': row[1],
                        'title': row[2],
                        'message': row[3],
                        'data': self._safe_json_loads(row[4]),
                        'priority': row[5],
                        'status': row[6],
                        'createdAt': row[7],
                        'deliveredAt': row[8]
                    })

                return history
        
        except Exception as e:
            logger.error(f"❌ خطأ في get_notification_history: {e}")
            return []
    
    # ==================== الإحصائيات ====================
    
    def get_notification_stats(self, user_id: int) -> Dict:
        """جلب إحصائيات الإشعارات"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(CASE WHEN COALESCE(is_read, FALSE) = FALSE THEN 1 END) as pending,
                            COUNT(CASE WHEN COALESCE(is_read, FALSE) = TRUE THEN 1 END) as delivered,
                            COUNT(CASE WHEN COALESCE(type, '') LIKE 'trade%' THEN 1 END) as trade_notifications,
                            0 as high_priority
                        FROM notifications
                        WHERE user_id = ?
                        AND created_at > (CURRENT_TIMESTAMP - INTERVAL '30 days')
                    """, (user_id,))
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                            COUNT(CASE WHEN status IN ('delivered', 'read', 'sent') THEN 1 END) as delivered,
                            COUNT(CASE WHEN COALESCE(type, notification_type, '') LIKE 'trade%' THEN 1 END) as trade_notifications,
                            0 as high_priority
                        FROM notification_history
                        WHERE user_id = ?
                        AND created_at > (CURRENT_TIMESTAMP - INTERVAL '30 days')
                    """, (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'totalNotifications': row[0],
                        'pendingNotifications': row[1],
                        'deliveredNotifications': row[2],
                        'tradeNotifications': row[3],
                        'highPriorityNotifications': row[4],
                        'deliveryRate': round((row[2] / row[0] * 100) if row[0] > 0 else 0, 2)
                    }
                
                return {
                    'totalNotifications': 0,
                    'pendingNotifications': 0,
                    'deliveredNotifications': 0,
                    'tradeNotifications': 0,
                    'highPriorityNotifications': 0,
                    'deliveryRate': 0.0
                }
        
        except Exception as e:
            logger.error(f"❌ خطأ في get_notification_stats: {e}")
            return {}


# Singleton instance
_notification_service = None

def get_notification_service() -> NotificationService:
    """الحصول على نسخة واحدة من الخدمة"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


# إنشاء instance عام
notification_service = NotificationService()
