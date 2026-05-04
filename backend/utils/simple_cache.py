#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🗂️ نظام Cache متقدم وفعال
========================

نظام caching في الذاكرة مع:
- دعم TTL (Time To Live)
- Invalidation ذكي بناءً على الاعتماديات
- تتبع المفاتيح المرتبطة
- تنظيف تلقائي للبيانات المنتهية الصلاحية
"""

import time
import threading
from typing import Any, Optional, Dict, List, Set


class SmartCache:
    """نظام cache متقدم مع invalidation ذكي"""

    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.RLock()
        # تتبع الاعتماديات: مفتاح -> قائمة المفاتيح المرتبطة
        self.dependencies: Dict[str, Set[str]] = {}
        # تتبع المفاتيح حسب المستخدم: user_id -> قائمة المفاتيح
        self.user_keys: Dict[int, Set[str]] = {}
        self._start_cleanup_thread()

    def _start_cleanup_thread(self):
        """بدء thread لتنظيف الكاش الدوري"""
        import threading

        def cleanup_worker():
            import time

            while True:
                time.sleep(300)  # كل 5 دقائق
                self.cleanup_expired()

        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()

    def cleanup_expired(self):
        """تنظيف البيانات المنتهية الصلاحية"""
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, entry in self.cache.items()
                if current_time > entry["expires_at"]
            ]
            for key in expired_keys:
                del self.cache[key]
                if key in self.dependencies:
                    del self.dependencies[key]

    def set(
        self,
        key: str,
        value: Any,
        ttl: int = 900,
        user_id: Optional[int] = None,
        dependencies: Optional[List[str]] = None,
    ) -> None:
        """
        حفظ قيمة في الـ cache مع دعم الاعتماديات

        Args:
            key: مفتاح التخزين
            value: القيمة المراد تخزينها
            ttl: مدة الصلاحية بالثواني (افتراضي: 900 ثانية)
            ttl: مدة الصلاحية بالثواني (افتراضي: 300 ثانية)
            user_id: معرف المستخدم (لتتبع المفاتيح حسب المستخدم)
            dependencies: قائمة المفاتيح المرتبطة (للـ invalidation الذكي)
        """
        with self.lock:
            self.cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl,
                "user_id": user_id,
            }

            # تتبع المفاتيح حسب المستخدم
            if user_id:
                if user_id not in self.user_keys:
                    self.user_keys[user_id] = set()
                self.user_keys[user_id].add(key)

            # تتبع الاعتماديات
            if dependencies:
                if key not in self.dependencies:
                    self.dependencies[key] = set()
                self.dependencies[key].update(dependencies)

    def get(self, key: str) -> Optional[Any]:
        """جلب قيمة من الـ cache"""
        with self.lock:
            if key not in self.cache:
                return None

            entry = self.cache[key]

            # التحقق من انتهاء صلاحية البيانات
            if time.time() > entry["expires_at"]:
                del self.cache[key]
                return None

            return entry["value"]

    def delete(self, key: str) -> None:
        """حذف قيمة من الـ cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
            if key in self.dependencies:
                del self.dependencies[key]

    def invalidate_user_cache(self, user_id: int) -> None:
        """
        حذف جميع مفاتيح المستخدم من الـ cache
        ✅ يُستخدم عند تحديث بيانات المستخدم
        """
        with self.lock:
            if user_id in self.user_keys:
                keys_to_delete = list(self.user_keys[user_id])
                for key in keys_to_delete:
                    if key in self.cache:
                        del self.cache[key]
                    if key in self.dependencies:
                        del self.dependencies[key]
                del self.user_keys[user_id]

    def invalidate_dependencies(self, key: str) -> None:
        """
        حذف جميع المفاتيح المرتبطة بمفتاح معين
        ✅ يُستخدم عند تحديث بيانات حرجة
        """
        with self.lock:
            if key in self.dependencies:
                dependent_keys = list(self.dependencies[key])
                for dep_key in dependent_keys:
                    if dep_key in self.cache:
                        del self.cache[dep_key]
                    if dep_key in self.dependencies:
                        del self.dependencies[dep_key]

    def clear(self) -> None:
        """مسح جميع البيانات من الـ cache"""
        with self.lock:
            self.cache.clear()
            self.dependencies.clear()
            self.user_keys.clear()

    def cleanup_expired(self) -> None:
        """تنظيف البيانات المنتهية الصلاحية"""
        with self.lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, entry in self.cache.items()
                if current_time > entry["expires_at"]
            ]
            for key in expired_keys:
                del self.cache[key]
                if key in self.dependencies:
                    del self.dependencies[key]

    def get_stats(self) -> Dict[str, int]:
        """الحصول على إحصائيات الـ cache"""
        with self.lock:
            return {
                "total_keys": len(self.cache),
                "total_users": len(self.user_keys),
                "total_dependencies": len(self.dependencies),
            }


# ✅ للتوافق مع الاستيرادات القديمة
class SimpleCache(SmartCache):
    """للتوافق مع الاستيرادات القديمة"""


# إنشاء instance عام للـ cache
response_cache = SmartCache()
cache = response_cache  # للتوافق مع الاستيرادات القديمة
