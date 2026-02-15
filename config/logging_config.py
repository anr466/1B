#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📝 نظام السجلات الموحد
====================
ملف إعدادات التسجيل المركزي للنظام بأكمله
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import os

# مسارات السجلات
PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / 'logs'
LOG_FILE = LOGS_DIR / 'server.log'
ERROR_LOG_FILE = LOGS_DIR / 'errors.log'
PRINT_LOG_FILE = LOGS_DIR / 'print_output.log'

# إنشاء مجلد logs إذا لم يكن موجوداً
LOGS_DIR.mkdir(exist_ok=True)

# البيئة
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

def is_production():
    """التحقق من بيئة الإنتاج"""
    return ENVIRONMENT == 'production'

def setup_logging(name: str, level=None) -> logging.Logger:
    """
    إعداد نظام التسجيل الموحد
    
    Args:
        name: اسم Logger (عادة __name__)
        level: مستوى التسجيل (اختياري)
        
    Returns:
        Logger instance
    """
    if level is None:
        level = logging.WARNING if is_production() else logging.DEBUG
    
    logger = logging.getLogger(name)
    
    # تجنب التكرار
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Console Handler - WARNING+ فقط
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING if is_production() else logging.INFO)
    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File Handler - جميع الرسائل
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Error File Handler - أخطاء فقط
    error_handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """الحصول على logger (alias لـ setup_logging)"""
    return setup_logging(name)

def disable_print_in_production():
    """تعطيل print() في الإنتاج وتحويله لملف"""
    if is_production():
        class PrintLogger:
            def __init__(self, log_file):
                self.log_file = open(log_file, 'a', encoding='utf-8')
                self.stdout = sys.stdout
            
            def write(self, message):
                if message.strip():
                    self.log_file.write(f"{message}")
                    self.log_file.flush()
            
            def flush(self):
                self.log_file.flush()
            
            def isatty(self):
                return False
        
        sys.stdout = PrintLogger(PRINT_LOG_FILE)
        return True
    return False

def log_api_error(error_message, context=None):
    """تسجيل أخطاء API"""
    logger = setup_logging('api_error')
    logger.error(f"{error_message} | Context: {context}")

# إعداد أساسي للمشروع
_root_logger = setup_logging('trading_ai_bot')
