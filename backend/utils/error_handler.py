#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Error Handler - معالجة الأخطاء الموحدة
"""

class HTTPStatus:
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_ERROR = 500


class ErrorMessages:
    INVALID_INPUT = "البيانات المدخلة غير صالحة"
    UNAUTHORIZED = "غير مصرح"
    NOT_FOUND = "غير موجود"
    INTERNAL_ERROR = "خطأ داخلي في الخادم"
    VALIDATION_ERROR = "خطأ في التحقق من البيانات"


def log_error(message, error=None):
    """تسجيل الأخطاء - للتوافق مع الكود القديم"""
    import logging
    logger = logging.getLogger(__name__)
    if error:
        logger.error(f"{message}: {error}")
    else:
        logger.error(message)
