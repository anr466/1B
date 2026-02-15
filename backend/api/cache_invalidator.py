"""
Cache Invalidation System - للتزامن بين Admin API و User API
==================================================================
يحل مشكلة: Admin يعدل البيانات لكن User يرى cache قديم
"""

from functools import wraps
from flask import g, make_response
import logging

logger = logging.getLogger(__name__)

# Global cache reference (will be set by admin_unified_api.py)
_admin_cache = None

def set_admin_cache(cache_dict):
    """تعيين مرجع الـ cache الخاص بالأدمن"""
    global _admin_cache
    _admin_cache = cache_dict
    logger.info("✅ Admin cache reference set")

def invalidate_cache(*cache_keys):
    """
    Decorator لإبطال cache بعد عمليات الكتابة
    
    Usage:
        @invalidate_cache('admin_dashboard', 'portfolio', 'stats')
        def update_user_balance():
            # ... update DB ...
            return jsonify({'success': True})
    
    يقوم بـ:
    1. مسح الـ cache المحلي في Admin API
    2. إرسال header X-Cache-Invalidate للـ frontend
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # تنفيذ الدالة الأساسية
            result = f(*args, **kwargs)
            
            # مسح cache keys المحددة
            if _admin_cache is not None:
                for key in cache_keys:
                    if key in _admin_cache:
                        del _admin_cache[key]
                        logger.info(f"🗑️ Invalidated cache key: {key}")
            
            # إضافة header للـ frontend
            if isinstance(result, tuple):
                response_data, status_code = result
                response = make_response(response_data, status_code)
            else:
                response = make_response(result)
            
            # إرسال قائمة الـ cache keys للتطبيق
            response.headers['X-Cache-Invalidate'] = ','.join(cache_keys)
            logger.debug(f"📤 Sent cache invalidation header: {cache_keys}")
            
            return response
        return wrapped
    return decorator

def clear_all_cache():
    """مسح جميع الـ cache (للاستخدام في حالات الطوارئ)"""
    if _admin_cache is not None:
        cleared_count = len(_admin_cache)
        _admin_cache.clear()
        logger.info(f"🗑️ Cleared all cache ({cleared_count} keys)")
        return cleared_count
    return 0
