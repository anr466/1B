#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📝 نظام السجلات الموحد
====================
ملف إعدادات التسجيل المركزي للنظام بأكمله
✅ Single Source of Truth للسجلات
✅ تصنيف السجلات حسب النوع
✅ تنظيف تلقائي للسجلات القديمة
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
import time
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).parent.parent
LOGS_DIR = PROJECT_ROOT / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# ═══════════════════════════════════════════════════════
# Log Files - موحدة ومنظمة
# ═══════════════════════════════════════════════════════

LOG_FILES = {
    'main': LOGS_DIR / 'server.log',           # السيرفر الرئيسي
    'errors': LOGS_DIR / 'errors.log',         # الأخطاء فقط
    'trading': LOGS_DIR / 'trading.log',       # عمليات التداول
    'api': LOGS_DIR / 'api.log',               # API calls
    'database': LOGS_DIR / 'database.log',     # Database operations
    'mobile': LOGS_DIR / 'mobile.log',         # Mobile app logs
    'security': LOGS_DIR / 'security.log',     # Security events
    'print': LOGS_DIR / 'print_output.log',    # Print redirection
}

# Legacy files for backward compatibility
LOG_FILE = LOG_FILES['main']
ERROR_LOG_FILE = LOG_FILES['errors']
PRINT_LOG_FILE = LOG_FILES['print']

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
        level = logging.INFO if is_production() else logging.DEBUG
    
    logger = logging.getLogger(name)
    
    # تجنب التكرار
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    # Console Handler - INFO+ في production لرؤية scanning
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # كان WARNING في production
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

# ═══════════════════════════════════════════════════════
# Specialized Loggers
# ═══════════════════════════════════════════════════════

def get_trading_logger(name: str) -> logging.Logger:
    """Logger for trading operations"""
    logger = setup_logging(name)
    # Add trading-specific file handler
    if not any(isinstance(h, RotatingFileHandler) and str(h.baseFilename).endswith('trading.log') for h in logger.handlers):
        trading_handler = RotatingFileHandler(
            LOG_FILES['trading'],
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        trading_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        trading_handler.setFormatter(formatter)
        logger.addHandler(trading_handler)
    return logger

def get_api_logger(name: str) -> logging.Logger:
    """Logger for API calls"""
    logger = setup_logging(name)
    if not any(isinstance(h, RotatingFileHandler) and str(h.baseFilename).endswith('api.log') for h in logger.handlers):
        api_handler = RotatingFileHandler(
            LOG_FILES['api'],
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        api_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        api_handler.setFormatter(formatter)
        logger.addHandler(api_handler)
    return logger

def get_database_logger(name: str) -> logging.Logger:
    """Logger for database operations"""
    logger = setup_logging(name)
    if not any(isinstance(h, RotatingFileHandler) and str(h.baseFilename).endswith('database.log') for h in logger.handlers):
        db_handler = RotatingFileHandler(
            LOG_FILES['database'],
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        db_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        db_handler.setFormatter(formatter)
        logger.addHandler(db_handler)
    return logger

def get_security_logger(name: str) -> logging.Logger:
    """Logger for security events"""
    logger = setup_logging(name)
    if not any(isinstance(h, RotatingFileHandler) and str(h.baseFilename).endswith('security.log') for h in logger.handlers):
        security_handler = RotatingFileHandler(
            LOG_FILES['security'],
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        security_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        security_handler.setFormatter(formatter)
        logger.addHandler(security_handler)
    return logger

# ═══════════════════════════════════════════════════════
# Log Cleanup
# ═══════════════════════════════════════════════════════

def cleanup_old_logs(days: int = 7):
    """
    حذف السجلات القديمة
    
    Args:
        days: عدد الأيام للاحتفاظ بالسجلات
    """
    cutoff_time = time.time() - (days * 86400)
    deleted_count = 0
    
    for log_file in LOGS_DIR.glob('*.log*'):
        try:
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                deleted_count += 1
                print(f"Deleted old log: {log_file.name}")
        except Exception as e:
            print(f"Failed to delete {log_file.name}: {e}")
    
    return deleted_count

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
