#!/usr/bin/env python3
"""
نظام إشعارات النظام للأدمن
System Alerts Service - للمراقبة والإنذار المبكر
"""

import logging
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any
import psutil
import os

logger = logging.getLogger(__name__)

class SystemAlertService:
    """
    خدمة إنشاء إشعارات النظام للأدمن
    تُراقب صحة الخدمات وتُنبّه عند المشاكل
    """
    
    def __init__(self, db_path: str = "database/trading_database.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # عتبات التحذير
        self.CPU_WARNING_THRESHOLD = 80  # %
        self.RAM_WARNING_THRESHOLD = 85  # %
        self.DISK_WARNING_THRESHOLD = 90  # %
        
    def _save_alert(self, alert_type: str, title: str, message: str, 
                    severity: str = 'warning', data: Dict[str, Any] = None):
        """
        حفظ إشعار نظام في قاعدة البيانات
        
        Args:
            alert_type: نوع الإشعار (backend_error, database_error, etc.)
            title: عنوان الإشعار
            message: نص الإشعار
            severity: خطورة (info, warning, error, critical)
            data: بيانات إضافية JSON
        """
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_write_connection() as conn:
                cursor = conn.cursor()
                
                import json
                data_json = json.dumps(data) if data else None
                
                cursor.execute("""
                    INSERT INTO system_alerts 
                    (alert_type, title, message, severity, data)
                    VALUES (?, ?, ?, ?, ?)
                """, (alert_type, title, message, severity, data_json))
            
            self.logger.info(f"📢 System Alert: [{severity.upper()}] {title}")
            return True
            
        except Exception as e:
            self.logger.error(f"فشل حفظ إشعار النظام: {e}")
            return False
    
    # ==================== Backend Alerts ====================
    
    def alert_backend_crash(self, error_message: str):
        """Backend توقف عن العمل"""
        return self._save_alert(
            alert_type='backend_crash',
            title='⛔ Backend Crash',
            message=f'Backend توقف عن العمل: {error_message}',
            severity='critical',
            data={'error': error_message}
        )
    
    def alert_backend_slow_response(self, endpoint: str, response_time: float):
        """استجابة Backend بطيئة"""
        return self._save_alert(
            alert_type='backend_slow',
            title='⚠️ Backend Slow Response',
            message=f'بطء في استجابة {endpoint}: {response_time:.2f}s',
            severity='warning',
            data={'endpoint': endpoint, 'response_time': response_time}
        )
    
    # ==================== Database Alerts ====================
    
    def alert_database_error(self, error_type: str, error_message: str):
        """خطأ في قاعدة البيانات"""
        return self._save_alert(
            alert_type='database_error',
            title='⛔ Database Error',
            message=f'خطأ في قاعدة البيانات ({error_type}): {error_message}',
            severity='critical',
            data={'error_type': error_type, 'error': error_message}
        )
    
    def alert_database_connection_lost(self):
        """فقدان اتصال قاعدة البيانات"""
        return self._save_alert(
            alert_type='database_disconnected',
            title='⚠️ Database Connection Lost',
            message='فقدان الاتصال بقاعدة البيانات',
            severity='critical'
        )
    
    def alert_database_slow_query(self, query: str, duration: float):
        """استعلام بطيء"""
        return self._save_alert(
            alert_type='database_slow_query',
            title='⚠️ Slow Database Query',
            message=f'استعلام بطيء: {duration:.2f}s',
            severity='warning',
            data={'query': query[:200], 'duration': duration}
        )
    
    # ==================== Binance API Alerts ====================
    
    def alert_binance_disconnected(self):
        """فقدان اتصال Binance"""
        return self._save_alert(
            alert_type='binance_disconnected',
            title='⛔ Binance API Disconnected',
            message='فقدان الاتصال بـ Binance API',
            severity='critical'
        )
    
    def alert_binance_rate_limit_warning(self, remaining: int, limit: int):
        """تحذير Rate Limit"""
        percentage = (remaining / limit) * 100
        return self._save_alert(
            alert_type='binance_rate_limit',
            title='⚠️ Binance Rate Limit Warning',
            message=f'اقتراب من حد Rate Limit: {remaining}/{limit} ({percentage:.1f}%)',
            severity='warning',
            data={'remaining': remaining, 'limit': limit}
        )
    
    def alert_binance_error(self, error_code: int, error_message: str):
        """خطأ Binance API"""
        severity = 'critical' if error_code in [403, 418] else 'error'
        return self._save_alert(
            alert_type='binance_error',
            title=f'⛔ Binance API Error {error_code}',
            message=f'خطأ Binance: {error_message}',
            severity=severity,
            data={'error_code': error_code, 'error': error_message}
        )
    
    # ==================== Group B Alerts ====================================
    
    def alert_group_b_error(self, user_id: int, symbol: str, error: str):
        """خطأ في Group B"""
        return self._save_alert(
            alert_type='group_b_error',
            title=f'⛔ Group B Error: {symbol}',
            message=f'خطأ في Group B للمستخدم {user_id}: {error}',
            severity='error',
            data={'user_id': user_id, 'symbol': symbol, 'error': error}
        )
    
    # ==================== Server Resources Alerts ====================
    
    def check_system_resources(self):
        """
        فحص موارد النظام وإنشاء إشعارات عند الحاجة
        """
        alerts = []
        
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self.CPU_WARNING_THRESHOLD:
                self.alert_high_cpu_usage(cpu_percent)
                alerts.append(f'High CPU: {cpu_percent}%')
            
            # RAM
            ram = psutil.virtual_memory()
            if ram.percent > self.RAM_WARNING_THRESHOLD:
                self.alert_high_memory_usage(ram.percent, ram.used, ram.total)
                alerts.append(f'High RAM: {ram.percent}%')
            
            # Disk
            disk = psutil.disk_usage('/')
            if disk.percent > self.DISK_WARNING_THRESHOLD:
                self.alert_low_disk_space(disk.percent, disk.free, disk.total)
                alerts.append(f'Low Disk: {disk.percent}%')
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"فشل فحص موارد النظام: {e}")
            return []
    
    def alert_high_cpu_usage(self, usage: float):
        """استهلاك CPU مرتفع"""
        return self._save_alert(
            alert_type='high_cpu',
            title='⚠️ High CPU Usage',
            message=f'استهلاك CPU مرتفع: {usage:.1f}%',
            severity='warning',
            data={'cpu_percent': usage}
        )
    
    def alert_high_memory_usage(self, percent: float, used: int, total: int):
        """استهلاك RAM مرتفع"""
        used_gb = used / (1024**3)
        total_gb = total / (1024**3)
        return self._save_alert(
            alert_type='high_memory',
            title='⚠️ High Memory Usage',
            message=f'استهلاك RAM مرتفع: {percent:.1f}% ({used_gb:.1f}GB / {total_gb:.1f}GB)',
            severity='warning',
            data={'percent': percent, 'used_gb': used_gb, 'total_gb': total_gb}
        )
    
    def alert_low_disk_space(self, percent: float, free: int, total: int):
        """مساحة القرص منخفضة"""
        free_gb = free / (1024**3)
        total_gb = total / (1024**3)
        return self._save_alert(
            alert_type='low_disk_space',
            title='⚠️ Low Disk Space',
            message=f'مساحة القرص منخفضة: {percent:.1f}% مستخدمة ({free_gb:.1f}GB متبقية)',
            severity='warning',
            data={'percent': percent, 'free_gb': free_gb, 'total_gb': total_gb}
        )
    
    # ==================== Info Alerts ====================
    
    def alert_backup_completed(self, backup_size: int):
        """تم backup قاعدة البيانات"""
        size_mb = backup_size / (1024**2)
        return self._save_alert(
            alert_type='backup_completed',
            title='✅ Database Backup Completed',
            message=f'تم backup قاعدة البيانات بنجاح: {size_mb:.1f}MB',
            severity='info',
            data={'size_mb': size_mb}
        )
    
    def alert_new_user_registered(self, user_id: int, username: str):
        """مستخدم جديد سجل"""
        return self._save_alert(
            alert_type='new_user',
            title='ℹ️ New User Registered',
            message=f'مستخدم جديد: {username}',
            severity='info',
            data={'user_id': user_id, 'username': username}
        )
    
    # ==================== Emergency Alerts ====================
    
    def alert_emergency_stop_triggered(self, triggered_by: str, reason: str):
        """تم تفعيل إيقاف الطوارئ"""
        return self._save_alert(
            alert_type='emergency_stop',
            title='🚨 Emergency Stop Triggered',
            message=f'تم تفعيل إيقاف الطوارئ بواسطة {triggered_by}: {reason}',
            severity='critical',
            data={'triggered_by': triggered_by, 'reason': reason}
        )
    
    def alert_security_breach_attempt(self, ip_address: str, attempt_type: str):
        """محاولة اختراق مشتبهة"""
        return self._save_alert(
            alert_type='security_breach',
            title='🚨 Security Breach Attempt',
            message=f'محاولة اختراق مشتبهة من {ip_address}: {attempt_type}',
            severity='critical',
            data={'ip_address': ip_address, 'attempt_type': attempt_type}
        )
    
    # ==================== Query Methods ====================
    
    def get_unread_alerts(self, limit: int = 50):
        """جلب الإشعارات غير المقروءة"""
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, alert_type, title, message, severity, data, created_at
                    FROM system_alerts
                    WHERE read = 0
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
                
                alerts = []
                import json
                for row in cursor.fetchall():
                    alerts.append({
                        'id': row[0],
                        'type': row[1],
                        'title': row[2],
                        'message': row[3],
                        'severity': row[4],
                        'data': json.loads(row[5]) if row[5] else {},
                        'created_at': row[6],
                        'read': False
                    })
                
                return alerts
            
        except Exception as e:
            self.logger.error(f"فشل جلب الإشعارات: {e}")
            return []
    
    def mark_as_read(self, alert_id: int):
        """تحديد إشعار كمقروء"""
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE system_alerts
                    SET read = 1
                    WHERE id = ?
                """, (alert_id,))
            
            return True
            
        except Exception as e:
            self.logger.error(f"فشل تحديث الإشعار: {e}")
            return False
    
    def mark_all_as_read(self):
        """تحديد جميع الإشعارات كمقروءة"""
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            
            with db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE system_alerts SET read = 1 WHERE read = 0")
                affected = cursor.rowcount
            
            self.logger.info(f"تم تحديد {affected} إشعار كمقروء")
            return True
            
        except Exception as e:
            self.logger.error(f"فشل تحديث الإشعارات: {e}")
            return False


# ==================== Singleton Instance ====================
_system_alert_service = None

def get_system_alert_service():
    """الحصول على instance من SystemAlertService"""
    global _system_alert_service
    if _system_alert_service is None:
        _system_alert_service = SystemAlertService()
    return _system_alert_service
