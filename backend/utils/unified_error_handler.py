#!/usr/bin/env python3
"""
معالج أخطاء موحد - يضمن معالجة متسقة للأخطاء في جميع الـ APIs
"""

import logging
from typing import Optional, Dict
from functools import wraps
from flask import jsonify

logger = logging.getLogger(__name__)


class AppError(Exception):
    """خطأ تطبيق مخصص"""

    def __init__(
        self,
        message: str,
        error_code: str = "APP_ERROR",
        status_code: int = 400,
        details: Optional[Dict] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class ValidationError(AppError):
    """خطأ Validation"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message, "VALIDATION_ERROR", 400, details)


class AuthenticationError(AppError):
    """خطأ مصادقة"""

    def __init__(self, message: str = "فشل المصادقة"):
        super().__init__(message, "AUTHENTICATION_ERROR", 401)


class AuthorizationError(AppError):
    """خطأ تفويض"""

    def __init__(self, message: str = "لا توجد صلاحيات"):
        super().__init__(message, "AUTHORIZATION_ERROR", 403)


class NotFoundError(AppError):
    """خطأ عدم العثور"""

    def __init__(self, resource: str = "المورد"):
        super().__init__(f"{resource} غير موجود", "NOT_FOUND", 404)


class ConflictError(AppError):
    """خطأ تضارب"""

    def __init__(self, message: str):
        super().__init__(message, "CONFLICT", 409)


class InternalServerError(AppError):
    """خطأ خادم داخلي"""

    def __init__(self, message: str = "خطأ في الخادم"):
        super().__init__(message, "INTERNAL_SERVER_ERROR", 500)


def handle_errors(f):
    """ديكوريتر لمعالجة الأخطاء تلقائياً"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)

        except AppError as e:
            logger.warning(f"AppError: {e.error_code} - {e.message}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": e.message,
                        "error_code": e.error_code,
                        "details": e.details,
                    }
                ),
                e.status_code,
            )

        except ValueError as e:
            logger.warning(f"ValueError: {str(e)}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "بيانات غير صحيحة",
                        "error_code": "VALUE_ERROR",
                        "details": {"message": str(e)},
                    }
                ),
                400,
            )

        except KeyError as e:
            logger.warning(f"KeyError: {str(e)}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "حقل مفقود",
                        "error_code": "MISSING_FIELD",
                        "details": {"field": str(e)},
                    }
                ),
                400,
            )

        except TypeError as e:
            logger.warning(f"TypeError: {str(e)}")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "نوع بيانات غير صحيح",
                        "error_code": "TYPE_ERROR",
                        "details": {"message": str(e)},
                    }
                ),
                400,
            )

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "خطأ غير متوقع في الخادم",
                        "error_code": "UNEXPECTED_ERROR",
                    }
                ),
                500,
            )

    return decorated_function


def log_error(error_code: str, message: str, details: Optional[Dict] = None):
    """تسجيل الخطأ"""
    log_message = f"[{error_code}] {message}"
    if details:
        log_message += f" - Details: {details}"
    logger.error(log_message)
