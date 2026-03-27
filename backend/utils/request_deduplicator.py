#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Request Deduplicator - منع الطلبات المكررة المتزامنة
يستخدم locks لمنع تنفيذ نفس العملية بشكل متزامن
"""

import threading
import time
import hashlib
import json
from functools import wraps
from flask import request, jsonify, g
from typing import Dict


class RequestDeduplicator:
    """منع الطلبات المكررة المتزامنة (خلال 3 ثواني)"""

    def __init__(self, window: int = 3):
        """
        Args:
            window: نافذة الكشف بالثواني (افتراضي 3 ثواني)
        """
        self.window = window
        self.active_requests: Dict[str, float] = {}
        self.lock = threading.Lock()

    def _generate_key(
        self, user_id: int, endpoint: str, method: str, payload: dict
    ) -> str:
        """توليد مفتاح فريد للطلب"""
        payload_str = json.dumps(payload, sort_keys=True) if payload else ""
        content = f"{user_id}:{method}:{endpoint}:{payload_str}"
        return hashlib.md5(content.encode()).hexdigest()

    def _cleanup_old_requests(self):
        """تنظيف الطلبات القديمة"""
        current_time = time.time()
        with self.lock:
            expired = [
                key
                for key, timestamp in self.active_requests.items()
                if current_time - timestamp > self.window
            ]
            for key in expired:
                del self.active_requests[key]

    def is_duplicate(
        self, user_id: int, endpoint: str, method: str, payload: dict
    ) -> bool:
        """
        فحص ما إذا كان الطلب مكرراً

        Returns:
            True: طلب مكرر (خلال نافذة 3 ثواني)
            False: طلب جديد
        """
        self._cleanup_old_requests()

        key = self._generate_key(user_id, endpoint, method, payload)
        current_time = time.time()

        with self.lock:
            if key in self.active_requests:
                last_time = self.active_requests[key]
                if current_time - last_time <= self.window:
                    return True

            # تسجيل الطلب الجديد
            self.active_requests[key] = current_time
            return False

    def mark_completed(
        self, user_id: int, endpoint: str, method: str, payload: dict
    ):
        """وضع علامة على اكتمال الطلب"""
        key = self._generate_key(user_id, endpoint, method, payload)
        with self.lock:
            if key in self.active_requests:
                del self.active_requests[key]


# مثيل عام
request_deduplicator = RequestDeduplicator(window=3)


def prevent_concurrent_duplicates(f):
    """
    Decorator لمنع الطلبات المكررة المتزامنة

    Usage:
        @prevent_concurrent_duplicates
        def update_settings():
            ...
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # استخراج user_id
        user_id = getattr(g, "current_user_id", None)
        if not user_id and "user_id" in kwargs:
            user_id = kwargs["user_id"]

        if not user_id:
            # السماح بالطلبات بدون user_id (مثل login)
            return f(*args, **kwargs)

        # معلومات الطلب
        endpoint = request.endpoint or request.path
        method = request.method

        try:
            payload = request.get_json(silent=True) or {}
        except Exception:
            payload = {}

        # فحص التكرار
        if request_deduplicator.is_duplicate(
            user_id, endpoint, method, payload
        ):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "طلب مكرر - يرجى الانتظار",
                        "code": "DUPLICATE_REQUEST",
                        "retry_after": 3,
                    }
                ),
                429,
            )

        try:
            # تنفيذ الطلب
            result = f(*args, **kwargs)
            return result
        finally:
            # وضع علامة على اكتمال الطلب
            request_deduplicator.mark_completed(
                user_id, endpoint, method, payload
            )

    return decorated_function
