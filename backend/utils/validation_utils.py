"""
Validation Utilities - نظام توحيد التحقق من البيانات
========================================================
يوحد جميع دوال التحقق المكررة في ملف واحد

Usage:
    from backend.utils.validation_utils import validate_email, validate_password, validate_username
"""

import re
from typing import Tuple


def validate_email(email: str) -> bool:
    """
    التحقق من صيغة البريد الإلكتروني
    
    Args:
        email: البريد الإلكتروني للتحقق منه
        
    Returns:
        True إذا كان البريد صحيح، False إذا كان خاطئ
    """
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email.strip()) is not None


def validate_password(password: str) -> Tuple[bool, str]:
    """
    التحقق من قوة كلمة المرور
    
    Requirements:
        - 8 أحرف على الأقل
        - حرف صغير واحد على الأقل
        - حرف كبير واحد على الأقل
        - رقم واحد على الأقل
    
    Args:
        password: كلمة المرور للتحقق منها
        
    Returns:
        (is_valid, error_message)
    """
    if not password or not isinstance(password, str):
        return False, 'كلمة المرور مطلوبة'
    
    if len(password) < 8:
        return False, 'كلمة المرور يجب أن تكون 8 أحرف على الأقل'
    
    if not re.search(r'[a-z]', password):
        return False, 'كلمة المرور يجب أن تحتوي على حرف صغير واحد على الأقل'
    
    if not re.search(r'[A-Z]', password):
        return False, 'كلمة المرور يجب أن تحتوي على حرف كبير واحد على الأقل'
    
    if not re.search(r'\d', password):
        return False, 'كلمة المرور يجب أن تحتوي على رقم واحد على الأقل'
    
    return True, ''


def validate_username(username: str) -> Tuple[bool, str]:
    """
    التحقق من اسم المستخدم
    
    Requirements:
        - بين 3 و 50 حرف
        - أحرف إنجليزية وأرقام فقط
        - يبدأ بحرف
    
    Args:
        username: اسم المستخدم للتحقق منه
        
    Returns:
        (is_valid, error_message)
    """
    if not username or not isinstance(username, str):
        return False, 'اسم المستخدم مطلوب'
    
    username = username.strip()
    
    if len(username) < 3:
        return False, 'اسم المستخدم يجب أن يكون 3 أحرف على الأقل'
    
    if len(username) > 50:
        return False, 'اسم المستخدم يجب أن لا يتجاوز 50 حرف'
    
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', username):
        return False, 'اسم المستخدم يجب أن يبدأ بحرف ويحتوي على أحرف إنجليزية وأرقام فقط'
    
    return True, ''


def validate_phone(phone: str) -> Tuple[bool, str]:
    """
    التحقق من رقم الهاتف
    
    Args:
        phone: رقم الهاتف للتحقق منه
        
    Returns:
        (is_valid, error_message)
    """
    if not phone or not isinstance(phone, str):
        return False, 'رقم الهاتف مطلوب'
    
    phone = phone.strip()
    
    # إزالة المسافات والرموز
    phone_digits = re.sub(r'[^\d+]', '', phone)
    
    # يجب أن يبدأ بـ + ويحتوي على 10-15 رقم
    if not re.match(r'^\+\d{10,15}$', phone_digits):
        return False, 'رقم الهاتف غير صحيح (يجب أن يبدأ بـ + ويحتوي على 10-15 رقم)'
    
    return True, ''


def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    تنظيف النص من المحارف الخطرة
    
    Args:
        text: النص للتنظيف
        max_length: الحد الأقصى للطول
        
    Returns:
        النص المنظف
    """
    if not text or not isinstance(text, str):
        return ''
    
    # إزالة المسافات الزائدة
    text = text.strip()
    
    # قص النص إذا كان طويل جداً
    if len(text) > max_length:
        text = text[:max_length]
    
    # إزالة المحارف الخطرة (XSS prevention)
    dangerous_chars = ['<', '>', '"', "'", '&', ';']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    return text


def normalize_username(username: str) -> str:
    """
    تطبيع اسم المستخدم
    
    Args:
        username: اسم المستخدم
        
    Returns:
        اسم المستخدم المطبع (lowercase, trimmed)
    """
    if not username or not isinstance(username, str):
        return ''
    
    return username.strip().lower()
