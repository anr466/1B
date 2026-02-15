#!/usr/bin/env python3
"""
نظام فحص صحة الخدمات
Health Check Service - للتأكد من عمل جميع المكونات
"""

import logging
import sqlite3
import psutil
import time
from typing import Dict, Any, Optional
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

class HealthCheckService:
    """
    خدمة فحص صحة النظام
    تفحص جميع المكونات وتُنبّه عند وجود مشاكل
    """
    
    def __init__(self, db_path: str = "database/trading_database.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
    def check_all(self) -> Dict[str, Any]:
        """
        فحص شامل لجميع المكونات
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',  # healthy, degraded, unhealthy
            'components': {
                'backend': self.check_backend(),
                'database': self.check_database(),
                'binance_api': self.check_binance_api(),
                'system_resources': self.check_system_resources()
            }
        }
    
    def check_backend(self) -> Dict[str, Any]:
        """فحص حالة Backend"""
        try:
            # Backend يعمل إذا استطعنا تشغيل هذا الكود
            return {
                'status': 'healthy',
                'message': 'Backend is running',
                'uptime_seconds': self._get_uptime()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Backend error: {str(e)}'
            }
    
    def check_database(self) -> Dict[str, Any]:
        """فحص حالة قاعدة البيانات"""
        try:
            start_time = time.time()
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
            
            # فحص حجم قاعدة البيانات
            import os
            db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            status = 'healthy' if response_time < 100 else 'degraded'
            
            return {
                'status': status,
                'message': 'Database connected',
                'tables': table_count,
                'size_mb': round(db_size_mb, 2),
                'response_time_ms': round(response_time, 2)
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Database error: {str(e)}'
            }
    
    def check_binance_api(self) -> Dict[str, Any]:
        """فحص حالة Binance API"""
        try:
            start_time = time.time()
            response = requests.get('https://api.binance.com/api/v3/ping', timeout=5)
            response_time = (time.time() - start_time) * 1000  # ms
            
            if response.status_code == 200:
                status = 'healthy' if response_time < 500 else 'degraded'
                return {
                    'status': status,
                    'message': 'Binance API reachable',
                    'response_time_ms': round(response_time, 2)
                }
            else:
                return {
                    'status': 'unhealthy',
                    'message': f'Binance API returned {response.status_code}'
                }
                
        except requests.exceptions.Timeout:
            return {
                'status': 'unhealthy',
                'message': 'Binance API timeout'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Binance API error: {str(e)}'
            }
    
    def check_system_resources(self) -> Dict[str, Any]:
        """فحص موارد النظام"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # تحديد الحالة
            status = 'healthy'
            if cpu_percent > 80 or memory.percent > 85 or disk.percent > 90:
                status = 'degraded'
            if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
                status = 'unhealthy'
            
            return {
                'status': status,
                'cpu_percent': round(cpu_percent, 1),
                'memory_percent': round(memory.percent, 1),
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'disk_percent': round(disk.percent, 1),
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'disk_total_gb': round(disk.total / (1024**3), 2)
            }
            
        except Exception as e:
            return {
                'status': 'unknown',
                'message': f'System resources check failed: {str(e)}'
            }
    
    def _get_uptime(self) -> float:
        """حساب uptime للنظام (بالثواني)"""
        try:
            import os
            return time.time() - os.path.getctime('/proc/self')
        except Exception:
            return 0.0


# ==================== Singleton Instance ====================
_health_check_service = None

def get_health_check_service():
    """الحصول على instance من HealthCheckService"""
    global _health_check_service
    if _health_check_service is None:
        _health_check_service = HealthCheckService()
    return _health_check_service
