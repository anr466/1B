"""
🔔 خدمة الإشعارات الموحدة - مرجع واحد فقط
يستخدمها جميع الـ endpoints والنظام الخلفي
"""

import json
from typing import Dict, List, Optional
from datetime import datetime

from database.database_manager import DatabaseManager


class NotificationService:
    """خدمة الإشعارات الموحدة"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
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
            print(f"❌ خطأ في إرسال الإشعار: {e}")
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
                
                if last_check:
                    cursor.execute("""
                        SELECT id, user_id, type, title, message, data, priority, status, created_at
                        FROM notification_history
                        WHERE user_id = ? AND status IN ('pending', 'sent')
                        AND created_at > ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (user_id, last_check, limit))
                else:
                    cursor.execute("""
                        SELECT id, user_id, type, title, message, data, priority, status, created_at
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
                        'data': json.loads(row[5]) if row[5] else {},
                        'priority': row[6],
                        'status': row[7],
                        'createdAt': row[8]
                    })
                
                return notifications
        
        except Exception as e:
            print(f"❌ خطأ في جلب الإشعارات: {e}")
            return []
    
    # ==================== تحديث حالة الإشعار ====================
    
    def mark_notification_delivered(self, notification_id: int) -> bool:
        """وضع علامة على الإشعار كمُسلم"""
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE notification_history
                    SET status = 'delivered', delivered_at = CURRENT_TIMESTAMP
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
                cursor.execute("""
                    SELECT id, type, title, message, data, priority, status, created_at, delivered_at
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
                        'data': json.loads(row[4]) if row[4] else {},
                        'priority': row[5],
                        'status': row[6],
                        'createdAt': row[7],
                        'deliveredAt': row[8]
                    })
                
                return history
        
        except Exception:
            return []
    
    # ==================== الإحصائيات ====================
    
    def get_notification_stats(self, user_id: int) -> Dict:
        """جلب إحصائيات الإشعارات"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                        COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered,
                        COUNT(CASE WHEN type LIKE 'trade%' THEN 1 END) as trade_notifications,
                        COUNT(CASE WHEN priority = 'high' THEN 1 END) as high_priority
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
        
        except Exception:
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
