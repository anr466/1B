from datetime import datetime
from typing import Optional


class NotificationService:
    def __init__(self, db=None):
        # Lazy-injected DB wrapper; can be replaced with a real DB wrapper later
        self.db = db

    def log_delivery(
        self,
        user_id: int,
        notification_id: int,
        status: str,
        delivered_at: Optional[str] = None,
    ) -> None:
        """Log a delivery attempt for a notification to ensure idempotency and tracing."""
        delivered_at = delivered_at or datetime.utcnow().isoformat()
        # Placeholder: insert into notification_delivery_log table
        # In future, replace with actual DB insert using DB wrapper
        return None

    def is_duplicate(self, user_id: int, notification_id: int) -> bool:
        # Placeholder: check notification_delivery_log for existing delivery
        return False
