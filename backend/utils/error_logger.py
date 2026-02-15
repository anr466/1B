#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام تسجيل الأخطاء - Error Logging System
=========================================

يسجل جميع الأخطاء من:
- Group B (التداول الآلي)
- النظام العام

ويرسلها إلى:
- Database (للعرض في تطبيق الجوال)
- Logs (للمراجعة المفصلة)
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from enum import Enum

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.database_manager import DatabaseManager


class ErrorLevel(Enum):
    """مستويات الأخطاء - متوافقة مع Database"""
    INFO = "low"            # معلومة عادية
    WARNING = "medium"      # تحذير
    ERROR = "high"          # خطأ
    CRITICAL = "critical"   # خطأ حرج (يوقف النظام)


class ErrorSource(Enum):
    """مصادر الأخطاء"""
    GROUP_B = "group_b"             # التداول الآلي
    SYSTEM = "system"               # النظام العام
    DATABASE = "database"           # قاعدة البيانات
    BINANCE = "binance"             # Binance API
    BACKGROUND = "background"       # النظام الخلفي


class ErrorLogger:
    """
    مسجل الأخطاء المركزي
    
    يسجل الأخطاء في Database و Logs
    """
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(__name__)
        self._ensure_errors_table()
    
    def _ensure_errors_table(self):
        """التأكد من وجود جدول الأخطاء - استخدام الجدول الموجود"""
        try:
            with self.db_manager.get_write_connection() as conn:
                # التحقق من وجود الأعمدة المطلوبة
                cursor = conn.execute("PRAGMA table_info(system_errors)")
                columns = {row[1] for row in cursor.fetchall()}
                
                # إضافة الأعمدة المفقودة إذا لزم الأمر
                if 'source' not in columns:
                    conn.execute("ALTER TABLE system_errors ADD COLUMN source TEXT DEFAULT 'system'")
                
                if 'details' not in columns:
                    conn.execute("ALTER TABLE system_errors ADD COLUMN details TEXT")
                
                if 'traceback' not in columns:
                    conn.execute("ALTER TABLE system_errors ADD COLUMN traceback TEXT")
                
                if 'resolved_by' not in columns:
                    conn.execute("ALTER TABLE system_errors ADD COLUMN resolved_by TEXT")
                
                # إنشاء index للبحث السريع
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_errors_created_at 
                    ON system_errors(created_at DESC)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_errors_resolved 
                    ON system_errors(resolved, severity)
                """)
                
        except Exception as e:
            self.logger.error(f"خطأ في تهيئة جدول الأخطاء: {e}")
    
    def log_error(
        self,
        level: ErrorLevel,
        source: ErrorSource,
        message: str,
        details: str = None,
        include_traceback: bool = False
    ) -> int:
        """
        تسجيل خطأ
        
        Args:
            level: مستوى الخطأ
            source: مصدر الخطأ
            message: رسالة الخطأ
            details: تفاصيل إضافية
            include_traceback: تضمين traceback
        
        Returns:
            معرف الخطأ المسجل
        """
        try:
            # الحصول على traceback إذا طُلب
            tb = None
            if include_traceback:
                tb = traceback.format_exc()
            
            # حفظ في Database (استخدام الأعمدة الموجودة)
            with self.db_manager.get_write_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO system_errors 
                    (error_type, error_message, severity, source, details, traceback)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    source.value,  # error_type
                    message,       # error_message
                    level.value,   # severity
                    source.value,  # source (عمود جديد)
                    details,
                    tb
                ))
                
                error_id = cursor.lastrowid
            
            # تسجيل في Logs
            log_message = f"[{source.value.upper()}] {message}"
            if details:
                log_message += f" | {details}"
            
            if level == ErrorLevel.CRITICAL:
                self.logger.critical(log_message)
            elif level == ErrorLevel.ERROR:
                self.logger.error(log_message)
            elif level == ErrorLevel.WARNING:
                self.logger.warning(log_message)
            else:
                self.logger.info(log_message)
            
            return error_id
            
        except Exception as e:
            self.logger.error(f"فشل في تسجيل الخطأ: {e}")
            return -1
    
    def log_group_b_error(self, message: str, details: str = None, critical: bool = False):
        """تسجيل خطأ Group B"""
        level = ErrorLevel.CRITICAL if critical else ErrorLevel.ERROR
        return self.log_error(level, ErrorSource.GROUP_B, message, details, True)
    
    def log_system_error(self, message: str, details: str = None, critical: bool = False):
        """تسجيل خطأ النظام"""
        level = ErrorLevel.CRITICAL if critical else ErrorLevel.ERROR
        return self.log_error(level, ErrorSource.SYSTEM, message, details, True)
    
    def log_binance_error(self, message: str, details: str = None):
        """تسجيل خطأ Binance API"""
        return self.log_error(ErrorLevel.ERROR, ErrorSource.BINANCE, message, details, False)
    
    def log_warning(self, source: ErrorSource, message: str, details: str = None):
        """تسجيل تحذير"""
        return self.log_error(ErrorLevel.WARNING, source, message, details, False)
    
    def get_errors(
        self,
        limit: int = 50,
        level: str = None,
        source: str = None,
        resolved: bool = None
    ) -> list:
        """
        جلب الأخطاء
        
        Args:
            limit: عدد الأخطاء
            level: فلترة حسب المستوى
            source: فلترة حسب المصدر
            resolved: فلترة حسب الحل
        
        Returns:
            قائمة الأخطاء
        """
        try:
            query = """
                SELECT 
                    id, created_at as timestamp, severity as level, 
                    COALESCE(source, error_type) as source, 
                    error_message as message, details, 
                    traceback, resolved, resolved_at, resolved_by
                FROM system_errors
                WHERE 1=1
            """
            params = []
            
            if level:
                query += " AND severity = ?"
                params.append(level)
            
            if source:
                query += " AND (source = ? OR error_type = ?)"
                params.append(source)
                params.append(source)
            
            if resolved is not None:
                query += " AND resolved = ?"
                params.append(resolved)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            with self.db_manager.get_connection() as conn:
                rows = conn.execute(query, params).fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"خطأ في جلب الأخطاء: {e}")
            return []
    
    def get_critical_errors(self, limit: int = 20) -> list:
        """جلب الأخطاء الحرجة فقط"""
        return self.get_errors(limit=limit, level="critical", resolved=False)
    
    def get_unresolved_errors(self, limit: int = 50) -> list:
        """جلب الأخطاء غير المحلولة"""
        return self.get_errors(limit=limit, resolved=False)
    
    def resolve_error(self, error_id: int, resolved_by: str = "admin") -> bool:
        """
        وضع علامة على خطأ كمحلول
        
        Args:
            error_id: معرف الخطأ
            resolved_by: من حل الخطأ
        
        Returns:
            نجح أم لا
        """
        try:
            with self.db_manager.get_write_connection() as conn:
                conn.execute("""
                    UPDATE system_errors
                    SET resolved = TRUE, 
                        resolved_at = CURRENT_TIMESTAMP,
                        resolved_by = ?
                    WHERE id = ?
                """, (resolved_by, error_id))
            
            self.logger.info(f"تم حل الخطأ #{error_id} بواسطة {resolved_by}")
            return True
            
        except Exception as e:
            self.logger.error(f"خطأ في حل الخطأ: {e}")
            return False
    
    def resolve_all_errors(self, resolved_by: str = "admin") -> int:
        """
        حل جميع الأخطاء
        
        Returns:
            عدد الأخطاء المحلولة
        """
        try:
            with self.db_manager.get_write_connection() as conn:
                cursor = conn.execute("""
                    UPDATE system_errors
                    SET resolved = TRUE,
                        resolved_at = CURRENT_TIMESTAMP,
                        resolved_by = ?
                    WHERE resolved = FALSE
                """, (resolved_by,))
                
                count = cursor.rowcount
            
            self.logger.info(f"تم حل {count} خطأ بواسطة {resolved_by}")
            return count
            
        except Exception as e:
            self.logger.error(f"خطأ في حل جميع الأخطاء: {e}")
            return 0
    
    def get_error_stats(self) -> dict:
        """
        الحصول على إحصائيات الأخطاء
        
        Returns:
            إحصائيات مفصلة
        """
        try:
            with self.db_manager.get_connection() as conn:
                # إجمالي الأخطاء
                total = conn.execute(
                    "SELECT COUNT(*) as count FROM system_errors"
                ).fetchone()['count']
                
                # الأخطاء غير المحلولة
                unresolved = conn.execute(
                    "SELECT COUNT(*) as count FROM system_errors WHERE resolved = 0"
                ).fetchone()['count']
                
                # الأخطاء الحرجة
                critical = conn.execute(
                    "SELECT COUNT(*) as count FROM system_errors WHERE severity = 'critical' AND resolved = 0"
                ).fetchone()['count']
                
                # حسب المصدر
                by_source = conn.execute("""
                    SELECT COALESCE(source, error_type) as source, COUNT(*) as count
                    FROM system_errors
                    WHERE resolved = 0
                    GROUP BY COALESCE(source, error_type)
                """).fetchall()
                
                # حسب المستوى
                by_level = conn.execute("""
                    SELECT COALESCE(severity, 'error') as level, COUNT(*) as count
                    FROM system_errors
                    WHERE resolved = 0
                    GROUP BY COALESCE(severity, 'error')
                """).fetchall()
                
                return {
                    'total': total,
                    'unresolved': unresolved,
                    'critical': critical,
                    'by_source': {row['source']: row['count'] for row in by_source},
                    'by_level': {row['level']: row['count'] for row in by_level}
                }
                
        except Exception as e:
            self.logger.error(f"خطأ في جلب إحصائيات الأخطاء: {e}")
            return {}
    
    def cleanup_old_errors(self, days: int = 30) -> int:
        """
        حذف الأخطاء القديمة المحلولة
        
        Args:
            days: عدد الأيام
        
        Returns:
            عدد الأخطاء المحذوفة
        """
        try:
            with self.db_manager.get_write_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM system_errors
                    WHERE resolved = 1
                    AND datetime(created_at) < datetime('now', '-' || ? || ' days')
                """, (days,))
                
                count = cursor.rowcount
            
            self.logger.info(f"تم حذف {count} خطأ قديم")
            return count
            
        except Exception as e:
            self.logger.error(f"خطأ في تنظيف الأخطاء: {e}")
            return 0


# مثيل عام للاستخدام
error_logger = ErrorLogger()
