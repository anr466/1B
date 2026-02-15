#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام Rate Limiting الآمن
- حماية من Brute Force attacks
- حماية من DDoS
- تحديد عدد الطلبات لكل مستخدم/IP
"""

import time
from collections import defaultdict
from threading import Lock
from functools import wraps
from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

class HTTPRateLimiter:
    """نظام Rate Limiting للـ HTTP Requests"""
    
    def __init__(self, requests: int = 100, period: int = 3600):
        """
        تهيئة Rate Limiter
        
        Args:
            requests: عدد الطلبات المسموح به
            period: الفترة الزمنية بالثواني
        """
        self.requests = requests
        self.period = period
        self.requests_by_ip = defaultdict(list)
        self.requests_by_user = defaultdict(list)
        self.lock = Lock()
    
    def _get_client_ip(self) -> str:
        """الحصول على IP العميل"""
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        return request.remote_addr or '127.0.0.1'
    
    def _cleanup_old_requests(self, requests_list: list) -> list:
        """حذف الطلبات القديمة"""
        current_time = time.time()
        return [req_time for req_time in requests_list if current_time - req_time < self.period]
    
    def is_allowed(self, identifier: str = None) -> bool:
        """
        التحقق من السماح بالطلب
        
        Args:
            identifier: معرف فريد (IP أو User ID)
        
        Returns:
            True إذا كان الطلب مسموح به
        """
        if identifier is None:
            identifier = self._get_client_ip()
        
        with self.lock:
            # تنظيف الطلبات القديمة
            self.requests_by_ip[identifier] = self._cleanup_old_requests(
                self.requests_by_ip[identifier]
            )
            
            # التحقق من عدد الطلبات
            if len(self.requests_by_ip[identifier]) >= self.requests:
                logger.warning(f"⚠️ Rate limit exceeded for {identifier}")
                return False
            
            # إضافة الطلب الحالي
            self.requests_by_ip[identifier].append(time.time())
            return True
    
    def get_remaining(self, identifier: str = None) -> int:
        """الحصول على عدد الطلبات المتبقية"""
        if identifier is None:
            identifier = self._get_client_ip()
        
        with self.lock:
            self.requests_by_ip[identifier] = self._cleanup_old_requests(
                self.requests_by_ip[identifier]
            )
            return max(0, self.requests - len(self.requests_by_ip[identifier]))
    
    def get_reset_time(self, identifier: str = None) -> float:
        """الحصول على وقت إعادة تعيين الحد"""
        if identifier is None:
            identifier = self._get_client_ip()
        
        with self.lock:
            if identifier not in self.requests_by_ip or not self.requests_by_ip[identifier]:
                return 0
            
            oldest_request = min(self.requests_by_ip[identifier])
            reset_time = oldest_request + self.period
            return max(0, reset_time - time.time())

# إنشاء instance عام
http_rate_limiter = HTTPRateLimiter(requests=100, period=3600)

def rate_limit(identifier_func=None):
    """
    Decorator للـ Rate Limiting
    
    Args:
        identifier_func: دالة للحصول على معرف فريد
    
    Example:
        @app.route('/api/login', methods=['POST'])
        @rate_limit(lambda: request.json.get('email'))
        def login():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # الحصول على المعرف
            if identifier_func:
                identifier = identifier_func()
            else:
                identifier = http_rate_limiter._get_client_ip()
            
            # التحقق من الحد
            if not http_rate_limiter.is_allowed(identifier):
                remaining = http_rate_limiter.get_remaining(identifier)
                reset_time = http_rate_limiter.get_reset_time(identifier)
                
                logger.warning(f"🚫 Rate limit exceeded for {identifier}")
                
                return jsonify({
                    'success': False,
                    'message': 'تم تجاوز حد الطلبات. حاول لاحقاً.',
                    'retry_after': int(reset_time)
                }), 429
            
            # تنفيذ الدالة
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator

# Rate limiters محددة لعمليات معينة
class LoginRateLimiter:
    """Rate Limiter خاص بتسجيل الدخول"""
    
    def __init__(self):
        self.limiter = HTTPRateLimiter(requests=5, period=900)  # 5 محاولات كل 15 دقيقة
    
    def is_allowed(self, email: str) -> bool:
        """التحقق من السماح بمحاولة تسجيل دخول"""
        return self.limiter.is_allowed(f"login:{email}")
    
    def get_remaining(self, email: str) -> int:
        """الحصول على عدد المحاولات المتبقية"""
        return self.limiter.get_remaining(f"login:{email}")
    
    def get_reset_time(self, email: str) -> float:
        """الحصول على وقت إعادة التعيين"""
        return self.limiter.get_reset_time(f"login:{email}")

class APIRateLimiter:
    """Rate Limiter خاص بـ API"""
    
    def __init__(self):
        self.limiter = HTTPRateLimiter(requests=100, period=3600)  # 100 طلب كل ساعة
    
    def is_allowed(self, user_id: str) -> bool:
        """التحقق من السماح بطلب API"""
        return self.limiter.is_allowed(f"api:{user_id}")
    
    def get_remaining(self, user_id: str) -> int:
        """الحصول على عدد الطلبات المتبقية"""
        return self.limiter.get_remaining(f"api:{user_id}")

# إنشاء instances
login_rate_limiter = LoginRateLimiter()
api_rate_limiter = APIRateLimiter()
