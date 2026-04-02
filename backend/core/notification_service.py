from datetime import datetime
from typing import Optional


class NotificationService:
    def __init__(self, db=None):
        self.db = db

    def log_delivery(
        self,
        user_id: int,
        notification_id: int,
        status: str,
        delivered_at: Optional[str] = None,
    ) -> None:
        delivered_at = delivered_at or datetime.utcnow().isoformat()
        if not self.db:
            return
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO notification_delivery_log (user_id, notification_id, status, delivered_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (user_id, notification_id, status, delivered_at),
                )
                conn.commit()
        except Exception:
            pass

    def is_duplicate(self, user_id: int, notification_id: int) -> bool:
        if not self.db:
            return False
        try:
            with self.db.get_read_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM notification_delivery_log
                    WHERE user_id = %s AND notification_id = %s AND status = 'delivered'
                    """,
                    (user_id, notification_id),
                )
                row = cursor.fetchone()
                return row[0] > 0 if row else False
        except Exception:
            return False
