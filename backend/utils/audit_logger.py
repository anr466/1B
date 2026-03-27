#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit Logger - تسجيل العمليات الأمنية
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AuditLogger:
    """تسجيل العمليات الأمنية"""

    def log(self, action: str, user_id: int = None, details: dict = None):
        """تسجيل عملية"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user_id": user_id,
            "details": details or {},
        }
        logger.info(f"🔒 AUDIT: {action} | User: {user_id} | {details}")
        return log_entry

    def log_admin_action(
        self, user_id: int = None, action: str = "", details=None, request=None
    ):
        """توافق خلفي مع الاستدعاءات التي تتوقع واجهة admin audit أوسع."""
        payload = {
            "details": details,
            "request": request,
        }
        return self.log(action=action, user_id=user_id, details=payload)


audit_logger = AuditLogger()
