#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heartbeat Monitor - مراقب نبضات النظام
========================================

يفحص heartbeat بشكل دوري ويسجل أخطاء إذا توقف النظام
"""

import time
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class HeartbeatMonitor:
    """
    مراقب نبضات النظام
    
    يفحص آخر نبضة ويسجل خطأ إذا:
    - لم تصل نبضة منذ > 60 ثانية (critical)
    - لم تصل نبضة منذ > 30 ثانية (warning)
    """
    
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.last_warning_time = None
        self.last_critical_time = None
    
    def check_heartbeat(self) -> dict:
        """
        فحص آخر نبضة
        
        Returns:
            dict: {
                'status': 'healthy' | 'warning' | 'critical',
                'seconds_ago': int,
                'error_logged': bool
            }
        """
        seconds_ago = self.state_manager.get_seconds_since_heartbeat()
        
        if seconds_ago is None:
            return {
                'status': 'unknown',
                'seconds_ago': None,
                'error_logged': False
            }
        
        error_logged = False
        status = 'healthy'
        
        # Critical: > 60 ثانية
        if seconds_ago > 60:
            status = 'critical'
            # تسجيل خطأ مرة واحدة كل 5 دقائق لتجنب الازدحام
            if self._should_log_critical():
                error_logged = self._log_heartbeat_failure(seconds_ago, critical=True)
                self.last_critical_time = datetime.now()
        
        # Warning: > 30 ثانية
        elif seconds_ago > 30:
            status = 'warning'
            # تسجيل تحذير مرة واحدة كل دقيقة
            if self._should_log_warning():
                error_logged = self._log_heartbeat_failure(seconds_ago, critical=False)
                self.last_warning_time = datetime.now()
        else:
            # Reset counters when healthy
            self.last_warning_time = None
            self.last_critical_time = None
        
        return {
            'status': status,
            'seconds_ago': seconds_ago,
            'error_logged': error_logged
        }
    
    def _should_log_warning(self) -> bool:
        """هل يجب تسجيل تحذير؟"""
        if self.last_warning_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_warning_time).total_seconds()
        return elapsed > 60  # مرة كل دقيقة
    
    def _should_log_critical(self) -> bool:
        """هل يجب تسجيل خطأ حرج؟"""
        if self.last_critical_time is None:
            return True
        
        elapsed = (datetime.now() - self.last_critical_time).total_seconds()
        return elapsed > 300  # مرة كل 5 دقائق
    
    def _log_heartbeat_failure(self, seconds_ago: int, critical: bool = False) -> bool:
        """
        تسجيل فشل heartbeat
        
        Args:
            seconds_ago: عدد الثواني منذ آخر نبضة
            critical: هل هو خطأ حرج؟
        
        Returns:
            bool: True إذا تم التسجيل بنجاح
        """
        try:
            from backend.utils.error_logger import ErrorLogger, ErrorLevel, ErrorSource
            
            error_logger = ErrorLogger()
            
            if critical:
                error_logger.log_error(
                    level=ErrorLevel.CRITICAL,
                    source=ErrorSource.BACKGROUND,
                    message=f'⚠️ النظام متوقف أو معلق - لم تصل نبضة منذ {seconds_ago} ثانية',
                    details=f'آخر نبضة كانت منذ {seconds_ago} ثانية. النظام على الأرجح معلق أو توقف. يجب التحقق فوراً.',
                    include_traceback=False
                )
                logger.critical(f"🚨 HEARTBEAT FAILURE: {seconds_ago}s ago")
            else:
                error_logger.log_error(
                    level=ErrorLevel.WARNING,
                    source=ErrorSource.BACKGROUND,
                    message=f'تحذير: تأخر في نبضات النظام',
                    details=f'آخر نبضة كانت منذ {seconds_ago} ثانية (المتوقع: < 30 ثانية)',
                    include_traceback=False
                )
                logger.warning(f"⚠️ HEARTBEAT WARNING: {seconds_ago}s ago")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ فشل تسجيل خطأ heartbeat: {e}")
            return False


# Global instance
_heartbeat_monitor = None

def get_heartbeat_monitor(state_manager):
    """الحصول على مثيل HeartbeatMonitor"""
    global _heartbeat_monitor
    if _heartbeat_monitor is None:
        _heartbeat_monitor = HeartbeatMonitor(state_manager)
    return _heartbeat_monitor
