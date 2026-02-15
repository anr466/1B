#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
وحدة تكوين السجلات للنظام
توفر دالات لإعداد وتهيئة نظام السجلات بطريقة موحدة للمشروع
from config.logging_config import get_logger

"""

import os
import sys
import glob
import logging
from typing import Optional
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logger(name: str, log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    إعداد وتهيئة مسجل مع تنسيق موحد

    المدخلات:
        name (str): اسم المسجل
        log_file (Optional[str]): مسار ملف السجل (اختياري)
        level (int): مستوى التسجيل (INFO افتراضيًا)

    المخرجات:
        logging.Logger: مسجل مهيأ
    """
    # إنشاء مسجل جديد
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # تحقق مما إذا كان المسجل يحتوي بالفعل على معالجات
    if logger.handlers:
        logger.handlers = []  # إزالة المعالجات الموجودة لتجنب التكرار
    
    # تنسيق موحد للسجلات
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # معالج لعرض السجلات في وحدة التحكم
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # إضافة معالج ملفات إذا تم تحديد ملف سجل
    if log_file:
        # التأكد من وجود مجلد السجلات
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # معالج ملفات مع تناوب (10 ميجابايت لكل ملف، 5 ملفات كحد أقصى)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 ميجابايت
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

def get_default_logger(component_name: str) -> logging.Logger:
    """
    الحصول على مسجل افتراضي باستخدام مجلد السجلات الافتراضي

    المدخلات:
        component_name (str): اسم المكون أو الوحدة

    المخرجات:
        logging.Logger: مسجل مهيأ
    """
    # تحديد مجلد المشروع
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # إنشاء مجلد السجلات إذا لم يكن موجودًا
    logs_dir = os.path.join(project_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # تحديد ملف السجل باستخدام اسم المكون وتاريخ اليوم
    log_file = os.path.join(
        logs_dir,
        f"{component_name}_{datetime.now().strftime('%Y%m%d')}.log"
    )
    
    # إنشاء المسجل
    return setup_logger(component_name, log_file)

def cleanup_old_logs(component_name: str) -> None:
    """
    حذف ملفات السجل السابقة لمكون معين
    
    المدخلات:
        component_name (str): اسم المكون
    """
    try:
        # تحديد مجلد المشروع
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logs_dir = os.path.join(project_dir, "logs")
        
        if not os.path.exists(logs_dir):
            return
        
        # البحث عن ملفات السجل السابقة لهذا المكون
        pattern = os.path.join(logs_dir, f"{component_name}_*.log*")
        old_log_files = glob.glob(pattern)
        
        # حذف الملفات السابقة
        for log_file in old_log_files:
            try:
                os.remove(log_file)
                print(f"تم حذف ملف السجل السابق: {os.path.basename(log_file)}")
            except Exception as e:
                print(f"تعذر حذف ملف السجل {log_file}: {e}")
                
    except Exception as e:
        print(f"خطأ في تنظيف ملفات السجل: {e}")

def get_backend_logger() -> logging.Logger:
    """
    الحصول على مسجل خاص بالنظام الخلفي مع حذف الملفات السابقة
    
    المخرجات:
        logging.Logger: مسجل مهيأ للنظام الخلفي
    """
    component_name = "backend_system"
    
    # حذف ملفات السجل السابقة
    cleanup_old_logs(component_name)
    
    # تحديد مجلد المشروع
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # إنشاء مجلد السجلات إذا لم يكن موجودًا
    logs_dir = os.path.join(project_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # تحديد ملف السجل الجديد بالتاريخ والوقت
    log_file = os.path.join(
        logs_dir,
        f"{component_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    
    # إنشاء المسجل
    return setup_logger(component_name, log_file)
