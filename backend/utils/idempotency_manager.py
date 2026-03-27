#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Idempotency Manager - نظام منع تكرار العمليات
يستخدم Redis أو ذاكرة محلية لتتبع العمليات المكررة
"""

import time
import hashlib
import json
from functools import wraps
from flask import request, jsonify, g
from typing import Dict, Any, Optional
import threading


class IdempotencyManager:
    """إدارة مفاتيح Idempotency لمنع تكرار العمليات"""

    def __init__(self, ttl: int = 300):
        """
        Args:
            ttl: مدة صلاحية المفتاح بالثواني (افتراضي 5 دقائق)
        """
        self.ttl = ttl
        self.store: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def _generate_key(
        self, user_id: int, operation: str, payload: dict
    ) -> str:
        """توليد مفتاح idempotency من user_id + operation + payload"""
        payload_str = json.dumps(payload, sort_keys=True)
        content = f"{user_id}:{operation}:{payload_str}"
        return hashlib.sha256(content.encode()).hexdigest()

    def _cleanup_expired(self):
        """تنظيف المفاتيح المنتهية الصلاحية"""
        current_time = time.time()
        with self.lock:
            expired_keys = [
                key
                for key, value in self.store.items()
                if current_time - value["timestamp"] > self.ttl
            ]
            for key in expired_keys:
                del self.store[key]

    def check_and_store(
        self, user_id: int, operation: str, payload: dict
    ) -> Optional[Dict[str, Any]]:
        """
        فحص وجود العملية وحفظها إذا لم تكن موجودة

        Returns:
            None: إذا كانت العملية جديدة
            Dict: استجابة العملية السابقة إذا كانت مكررة
        """
        self._cleanup_expired()

        key = self._generate_key(user_id, operation, payload)

        with self.lock:
            if key in self.store:
                stored = self.store[key]
                # التحقق من أن العملية لم تنتهي بعد أو منتهية خلال TTL
                if time.time() - stored["timestamp"] <= self.ttl:
                    return stored.get("response")

            # حفظ العملية الجديدة
            self.store[key] = {
                "timestamp": time.time(),
                "user_id": user_id,
                "operation": operation,
                "status": "processing",
            }

            return None

    def store_response(
        self, user_id: int, operation: str, payload: dict, response: dict
    ):
        """حفظ استجابة العملية بعد اكتمالها"""
        key = self._generate_key(user_id, operation, payload)

        with self.lock:
            if key in self.store:
                self.store[key]["response"] = response
                self.store[key]["status"] = "completed"
                self.store[key]["completed_at"] = time.time()

    def remove(self, user_id: int, operation: str, payload: dict):
        """حذف مفتاح idempotency (في حالة الفشل)"""
        key = self._generate_key(user_id, operation, payload)
        with self.lock:
            if key in self.store:
                del self.store[key]


# مثيل عام
idempotency_manager = IdempotencyManager(ttl=300)


def require_idempotency(operation_name: str, require_user_id: bool = True):
    """
    Decorator لمنع تكرار العمليات

    Usage:
        @require_idempotency('update_settings')
        def update_settings():
            ...

        # لعمليات لا تتطلب user_id (مثل التسجيل)
        @require_idempotency('register', require_user_id=False)
        def register():
            ...
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # استخراج user_id من g.current_user_id أو kwargs
            user_id = getattr(g, "current_user_id", None)
            if not user_id and "user_id" in kwargs:
                user_id = kwargs["user_id"]

            # إذا كانت العملية لا تتطلب user_id، استخدم email أو معرف بديل
            if not user_id and not require_user_id:
                try:
                    payload = request.get_json(silent=True) or {}
                    # استخدام email أو username أو phone كمعرف بديل
                    alt_id = (
                        payload.get("email")
                        or payload.get("username")
                        or payload.get("phone")
                        or "anonymous"
                    )
                    user_id = f"pre_auth_{alt_id}"
                except Exception:
                    user_id = "anonymous"

            if not user_id and require_user_id:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "User ID required for idempotency check",
                        }
                    ),
                    400,
                )

            # استخراج payload من request
            try:
                payload = request.get_json(silent=True) or {}
            except Exception:
                payload = {}

            # فحص التكرار
            existing_response = idempotency_manager.check_and_store(
                user_id=user_id, operation=operation_name, payload=payload
            )

            if existing_response:
                # عملية مكررة - إرجاع الاستجابة السابقة
                return (jsonify({"success": True,
                                 "duplicate": True,
                                 "message": "عملية مكررة - تم إرجاع النتيجة السابقة",
                                 **existing_response,
                                 }),
                        200,
                        )

            try:
                # تنفيذ العملية
                result = f(*args, **kwargs)

                # حفظ الاستجابة
                if isinstance(result, tuple) and len(result) == 2:
                    response, status_code = result
                    if status_code in [200, 201]:
                        try:
                            response_data = response.get_json()
                            idempotency_manager.store_response(
                                user_id=user_id,
                                operation=operation_name,
                                payload=payload,
                                response=response_data,
                            )
                        except Exception:
                            pass

                return result

            except Exception:
                # حذف المفتاح في حالة الفشل
                idempotency_manager.remove(user_id, operation_name, payload)
                raise

        return decorated_function

    return decorator
