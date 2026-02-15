#!/usr/bin/env python3
"""
موحد Response format - يضمن توحيد جميع الـ Response في النظام
"""

from typing import Any, Dict, Optional
from datetime import datetime


class ResponseFormatter:
    """موحد Response format لجميع الـ APIs"""
    
    @staticmethod
    def success(data: Any = None, message: str = "نجح", status_code: int = 200) -> tuple:
        """إنشاء Response نجح"""
        response = {
            'success': True,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        return response, status_code
    
    @staticmethod
    def error(error: str, error_code: str = "UNKNOWN_ERROR", 
              status_code: int = 400, details: Optional[Dict] = None) -> tuple:
        """إنشاء Response خطأ"""
        response = {
            'success': False,
            'error': error,
            'error_code': error_code,
            'timestamp': datetime.now().isoformat()
        }
        if details:
            response['details'] = details
        return response, status_code
    
    @staticmethod
    def paginated(items: list, total: int, page: int, limit: int, 
                  message: str = "نجح") -> tuple:
        """إنشاء Response مع Pagination"""
        total_pages = (total + limit - 1) // limit
        
        response = {
            'success': True,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'data': {
                'items': items,
                'pagination': {
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'pages': total_pages,
                    'hasNext': page < total_pages,
                    'hasPrev': page > 1
                }
            }
        }
        return response, 200
    
    @staticmethod
    def validation_error(errors: Dict[str, str]) -> tuple:
        """إنشاء Response لأخطاء Validation"""
        response = {
            'success': False,
            'error': 'بيانات غير صحيحة',
            'error_code': 'VALIDATION_ERROR',
            'timestamp': datetime.now().isoformat(),
            'details': {
                'validation_errors': errors
            }
        }
        return response, 400


# اختصارات للاستخدام السريع
def success_response(data=None, message="نجح", status_code=200):
    """اختصار للـ success response"""
    return ResponseFormatter.success(data, message, status_code)


def error_response(error, error_code="UNKNOWN_ERROR", status_code=400, details=None):
    """اختصار للـ error response"""
    return ResponseFormatter.error(error, error_code, status_code, details)


def paginated_response(items, total, page, limit, message="نجح"):
    """اختصار للـ paginated response"""
    return ResponseFormatter.paginated(items, total, page, limit, message)


def validation_error_response(errors):
    """اختصار للـ validation error response"""
    return ResponseFormatter.validation_error(errors)
