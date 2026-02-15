"""
🚦 Rate Limiter Helper - مساعد تطبيق حدود الطلبات
يوفر decorators موحدة لتطبيق Rate Limiting على endpoints مختلفة
"""

from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta
import threading

class RateLimiterHelper:
    """مساعد Rate Limiting مع تخزين في الذاكرة"""
    
    def __init__(self):
        self.requests = {}  # {ip: [(timestamp, endpoint), ...]}
        self.lock = threading.Lock()
    
    def is_rate_limited(self, ip: str, endpoint: str, limit: int, window_seconds: int) -> bool:
        """
        التحقق من تجاوز حد الطلبات
        
        Args:
            ip: عنوان IP
            endpoint: نقطة النهاية
            limit: عدد الطلبات المسموح به
            window_seconds: نافذة الوقت بالثواني
            
        Returns:
            True إذا تم تجاوز الحد، False خلاف ذلك
        """
        with self.lock:
            now = datetime.now()
            key = f"{ip}:{endpoint}"
            
            # تنظيف الطلبات القديمة
            if key in self.requests:
                cutoff_time = now - timedelta(seconds=window_seconds)
                self.requests[key] = [
                    (ts, ep) for ts, ep in self.requests[key]
                    if ts > cutoff_time
                ]
            else:
                self.requests[key] = []
            
            # التحقق من الحد
            if len(self.requests[key]) >= limit:
                return True
            
            # إضافة الطلب الحالي
            self.requests[key].append((now, endpoint))
            return False
    
    def get_remaining(self, ip: str, endpoint: str, limit: int, window_seconds: int) -> int:
        """الحصول على عدد الطلبات المتبقية"""
        with self.lock:
            now = datetime.now()
            key = f"{ip}:{endpoint}"
            
            if key not in self.requests:
                return limit
            
            cutoff_time = now - timedelta(seconds=window_seconds)
            valid_requests = [
                (ts, ep) for ts, ep in self.requests[key]
                if ts > cutoff_time
            ]
            
            return max(0, limit - len(valid_requests))


# إنشاء instance واحد
rate_limiter = RateLimiterHelper()


def rate_limit(limit: int = 100, window_seconds: int = 60, endpoint_name: str = None):
    """
    Decorator لتطبيق Rate Limiting
    
    Args:
        limit: عدد الطلبات المسموح به
        window_seconds: نافذة الوقت بالثواني
        endpoint_name: اسم النقطة (اختياري)
    
    مثال:
        @rate_limit(limit=50, window_seconds=60)
        def my_endpoint():
            return {"message": "success"}
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr or "unknown"
            endpoint = endpoint_name or request.endpoint or "unknown"
            
            # التحقق من Rate Limit
            if rate_limiter.is_rate_limited(ip, endpoint, limit, window_seconds):
                remaining = rate_limiter.get_remaining(ip, endpoint, limit, window_seconds)
                return jsonify({
                    'success': False,
                    'error': 'تم تجاوز حد الطلبات',
                    'error_code': 'RATE_LIMIT_EXCEEDED',
                    'message': f'لقد تجاوزت حد الطلبات المسموح به ({limit} طلب/{window_seconds} ثانية). حاول مرة أخرى لاحقاً.',
                    'retry_after': window_seconds,
                    'remaining': remaining
                }), 429
            
            # تنفيذ الدالة الأصلية
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


# Decorators محددة مسبقاً للاستخدام الشائع

def rate_limit_general(f):
    """Rate Limit عام: 100 طلب/دقيقة"""
    return rate_limit(limit=100, window_seconds=60, endpoint_name="general")(f)


def rate_limit_trading(f):
    """Rate Limit للتداول: 50 طلب/دقيقة"""
    return rate_limit(limit=50, window_seconds=60, endpoint_name="trading")(f)


def rate_limit_auth(f):
    """Rate Limit للمصادقة: 5 محاولات/دقيقة"""
    return rate_limit(limit=5, window_seconds=60, endpoint_name="auth")(f)


def rate_limit_data(f):
    """Rate Limit لجلب البيانات: 300 طلب/دقيقة - لكل endpoint منفصل"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # استخدام اسم الـ endpoint الفعلي بدلاً من "data" المشترك
        endpoint = f.__name__ or "data"
        return rate_limit(limit=300, window_seconds=60, endpoint_name=endpoint)(f)(*args, **kwargs)
    return decorated_function


def rate_limit_strict(f):
    """Rate Limit صارم: 10 طلبات/دقيقة"""
    return rate_limit(limit=10, window_seconds=60, endpoint_name="strict")(f)
