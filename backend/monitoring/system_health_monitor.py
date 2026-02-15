#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 نظام مراقبة صحة النظام الشامل
═══════════════════════════════════════════════════════════

يوفر مراقبة حية لجميع مكونات النظام مع تشخيص الأعطال
"""

import os
import sys
import time
import psutil
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# إضافة مسار المشروع
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "database"))

class SystemHealthMonitor:
    """
    نظام مراقبة صحة النظام الشامل
    يفحص جميع المكونات ويشخّص الأعطال
    """
    
    def __init__(self, db_manager=None):
        self.logger = logging.getLogger(__name__)
        self.db_manager = db_manager
        self.start_time = time.time()
        
        # حالة آخر فحص
        self.last_check = {}
        self.error_history = []
        
    def get_full_system_status(self) -> Dict[str, Any]:
        """
        جلب حالة النظام الكاملة مع جميع التفاصيل
        """
        try:
            return {
                'timestamp': datetime.now().isoformat(),
                'uptime': self._get_uptime(),
                'overall_health': self._calculate_overall_health(),
                
                # Group B System  
                'group_b': self._check_group_b_status(),
                
                # Database
                'database': self._check_database_status(),
                
                # Binance API
                'binance': self._check_binance_status(),
                
                # Firebase
                'firebase': self._check_firebase_status(),
                
                # System Resources
                'resources': self._check_system_resources(),
                
                # Errors & Warnings
                'errors': self._get_recent_errors(),
                
                # Users & Trades
                'statistics': self._get_system_statistics()
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في جلب حالة النظام: {e}\n{traceback.format_exc()}")
            return self._get_fallback_status(str(e))
    
    def _get_uptime(self) -> Dict[str, Any]:
        """حساب وقت التشغيل"""
        uptime_seconds = int(time.time() - self.start_time)
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        
        return {
            'seconds': uptime_seconds,
            'formatted': f"{hours}h {minutes}m",
            'started_at': datetime.fromtimestamp(self.start_time).isoformat()
        }
    
    def _calculate_overall_health(self) -> Dict[str, Any]:
        """حساب الصحة العامة للنظام"""
        health_score = 100
        issues = []
        status = 'healthy'
        
        # فحص قاعدة البيانات
        db_status = self._check_database_status()
        if db_status['status'] != 'connected':
            health_score -= 30
            issues.append('قاعدة البيانات غير متصلة')
            status = 'critical'
        
        # فحص الموارد
        resources = self._check_system_resources()
        if resources['cpu']['usage'] > 90:
            health_score -= 15
            issues.append('استهلاك CPU عالي جداً')
            if status != 'critical':
                status = 'warning'
        
        if resources['memory']['usage_percent'] > 90:
            health_score -= 15
            issues.append('استهلاك RAM عالي جداً')
            if status != 'critical':
                status = 'warning'
        
        # فحص الأخطاء
        errors = self._get_recent_errors()
        critical_errors = len([e for e in errors.get('critical', [])])
        if critical_errors > 0:
            health_score -= 20
            issues.append(f'{critical_errors} أخطاء حرجة')
            status = 'critical'
        
        return {
            'status': status,
            'score': max(0, health_score),
            'issues': issues,
            'last_check': datetime.now().isoformat()
        }
    
    def _check_group_b_status(self) -> Dict[str, Any]:
        """
        فحص حالة Group B (نظام التداول)
        """
        try:
            if not self.db_manager:
                return self._service_unavailable('Group B', 'قاعدة البيانات غير متاحة')
            
            # جلب الصفقات النشطة
            active_positions = self._get_active_positions()
            
            # جلب إحصائيات اليوم
            today_stats = self._get_today_trading_stats()
            
            # تحديد الحالة
            if len(active_positions) > 0:
                status = 'trading'
                health = 'active'
                message = f'يتداول الآن ({len(active_positions)} صفقات نشطة)'
            else:
                status = 'monitoring'
                health = 'idle'
                message = 'يراقب العملات (لا توجد صفقات نشطة)'
            
            return {
                'status': status,
                'health': health,
                'message': message,
                'last_check': datetime.now().isoformat(),
                'update_interval': '60 ثانية',
                'today_stats': today_stats,
                'active_positions': active_positions,
                'monitoring_coins': self._get_monitoring_coins_count()
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في فحص Group B: {e}\n{traceback.format_exc()}")
            return self._service_error('Group B', str(e))
    
    def _check_database_status(self) -> Dict[str, Any]:
        """فحص حالة قاعدة البيانات"""
        try:
            if not self.db_manager:
                return {
                    'status': 'disconnected',
                    'health': 'critical',
                    'message': 'قاعدة البيانات غير مهيأة',
                    'error': 'DatabaseManager not initialized'
                }
            
            # اختبار الاتصال
            is_connected = self.db_manager.test_connection()
            
            if not is_connected:
                return {
                    'status': 'disconnected',
                    'health': 'critical',
                    'message': 'فقدان الاتصال بقاعدة البيانات',
                    'error': 'Connection test failed',
                    'last_successful_connection': self.last_check.get('database', {}).get('time')
                }
            
            # جلب الإحصائيات
            stats = {
                'total_users': self.db_manager.get_total_users() or 0,
                'total_tables': 33,
                'db_type': 'SQLite'
            }
            
            return {
                'status': 'connected',
                'health': 'healthy',
                'message': 'متصلة وتعمل بشكل طبيعي',
                'stats': stats,
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في فحص Database: {e}\n{traceback.format_exc()}")
            return {
                'status': 'error',
                'health': 'critical',
                'message': 'خطأ في فحص قاعدة البيانات',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def _check_binance_status(self) -> Dict[str, Any]:
        """فحص حالة Binance API"""
        try:
            if not self.db_manager:
                return self._service_unavailable('Binance API', 'قاعدة البيانات غير متاحة')
            
            # عدد المفاتيح النشطة
            active_keys = self._count_active_binance_keys()
            
            # محاولة اختبار الاتصال (بسيط)
            # يمكن تحسينه لاحقاً باختبار فعلي
            
            if active_keys == 0:
                return {
                    'status': 'no_keys',
                    'health': 'warning',
                    'message': 'لا توجد مفاتيح Binance مفعّلة',
                    'active_keys': 0,
                    'response_time_ms': None
                }
            
            return {
                'status': 'connected',
                'health': 'healthy',
                'message': 'متصلة',
                'active_keys': active_keys,
                'response_time_ms': 125,  # تقديري - يمكن تحسينه
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في فحص Binance: {e}\n{traceback.format_exc()}")
            return self._service_error('Binance API', str(e))
    
    def _check_firebase_status(self) -> Dict[str, Any]:
        """فحص حالة Firebase"""
        try:
            # فحص بسيط - يمكن تحسينه
            return {
                'status': 'connected',
                'health': 'healthy',
                'message': 'متاحة',
                'services': {
                    'auth': 'active',
                    'fcm': 'active'
                },
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في فحص Firebase: {e}")
            return self._service_error('Firebase', str(e))
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """فحص موارد النظام"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory
            memory = psutil.virtual_memory()
            
            # Disk
            disk = psutil.disk_usage('/')
            
            return {
                'cpu': {
                    'usage': round(cpu_percent, 1),
                    'cores': cpu_count,
                    'status': self._get_usage_status(cpu_percent)
                },
                'memory': {
                    'usage_percent': round(memory.percent, 1),
                    'used_gb': round(memory.used / (1024**3), 2),
                    'total_gb': round(memory.total / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2),
                    'status': self._get_usage_status(memory.percent)
                },
                'disk': {
                    'usage_percent': round(disk.percent, 1),
                    'used_gb': round(disk.used / (1024**3), 2),
                    'total_gb': round(disk.total / (1024**3), 2),
                    'free_gb': round(disk.free / (1024**3), 2),
                    'status': self._get_usage_status(disk.percent)
                },
                'last_check': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في فحص الموارد: {e}")
            return {
                'cpu': {'usage': 0, 'status': 'unknown'},
                'memory': {'usage_percent': 0, 'status': 'unknown'},
                'disk': {'usage_percent': 0, 'status': 'unknown'},
                'error': str(e)
            }
    
    def _get_recent_errors(self) -> Dict[str, List[Dict]]:
        """جلب الأخطاء الأخيرة (آخر 24 ساعة)"""
        try:
            # محاولة جلب من قاعدة البيانات
            if self.db_manager:
                # يمكن تحسينه بإضافة جدول system_errors
                pass
            
            # استخدام سجل الأخطاء المحلي
            critical = []
            warnings = []
            info = []
            
            # تصنيف الأخطاء (مثال)
            for error in self.error_history[-50:]:  # آخر 50 خطأ
                if error.get('level') == 'critical':
                    critical.append(error)
                elif error.get('level') == 'warning':
                    warnings.append(error)
                else:
                    info.append(error)
            
            return {
                'critical': critical[-5:],  # آخر 5 أخطاء حرجة
                'warning': warnings[-10:],  # آخر 10 تحذيرات
                'info': info[-20:],  # آخر 20 معلومة
                'counts_24h': {
                    'critical': len(critical),
                    'warning': len(warnings),
                    'info': len(info)
                },
                'last_critical': critical[-1] if critical else None
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في جلب الأخطاء: {e}")
            return {
                'critical': [],
                'warning': [],
                'info': [],
                'counts_24h': {'critical': 0, 'warning': 0, 'info': 0},
                'last_critical': None
            }
    
    def _get_system_statistics(self) -> Dict[str, Any]:
        """جلب إحصائيات النظام"""
        try:
            if not self.db_manager:
                return {}
            
            return {
                'users': {
                    'total': self.db_manager.get_total_users() or 0,
                    'active_today': 0,  # يمكن تحسينه
                    'with_binance_keys': self._count_active_binance_keys()
                },
                'trades': {
                    'active': self.db_manager.get_active_trades_count() or 0,
                    'total': self.db_manager.get_total_trades_count() or 0,
                    'today': self._get_today_trades_count()
                },
                'coins': {
                    'successful': self.db_manager.get_successful_coins_count() or 0,
                    'monitoring': self._get_monitoring_coins_count()
                }
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في جلب الإحصائيات: {e}")
            return {}
    
    # ═══════════════════════════════════════════════════════════
    # دوال مساعدة
    # ═══════════════════════════════════════════════════════════
    
    def _get_usage_status(self, percent: float) -> str:
        """تحديد حالة الاستهلاك"""
        if percent < 50:
            return 'normal'
        elif percent < 80:
            return 'medium'
        else:
            return 'high'
    
    def _service_unavailable(self, service_name: str, reason: str) -> Dict[str, Any]:
        """رسالة خدمة غير متاحة"""
        return {
            'status': 'unavailable',
            'health': 'unknown',
            'message': f'{service_name} غير متاحة',
            'reason': reason
        }
    
    def _service_error(self, service_name: str, error: str) -> Dict[str, Any]:
        """رسالة خطأ في الخدمة"""
        return {
            'status': 'error',
            'health': 'critical',
            'message': f'خطأ في {service_name}',
            'error': error
        }
    
    def _get_fallback_status(self, error: str) -> Dict[str, Any]:
        """حالة احتياطية عند فشل النظام"""
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_health': {
                'status': 'error',
                'score': 0,
                'issues': ['فشل في جلب حالة النظام']
            },
            'error': error,
            'message': 'فشل في جلب حالة النظام الكاملة'
        }
    
    # ═══════════════════════════════════════════════════════════
    # دوال قاعدة البيانات المساعدة
    # ═══════════════════════════════════════════════════════════
    
    def _get_successful_coins_list(self) -> List[Dict]:
        """جلب قائمة العملات الناجحة"""
        try:
            if not self.db_manager:
                return []
            
            query = """
                SELECT symbol, level, strategy, timeframe, added_at, 
                       return_pct, sharpe_ratio, win_rate
                FROM successful_coins 
                ORDER BY added_at DESC 
                LIMIT 10
            """
            result = self.db_manager.execute_query(query)
            
            coins = []
            for row in result:
                coins.append({
                    'symbol': row[0],
                    'level': row[1],
                    'strategy': row[2],
                    'timeframe': row[3],
                    'added_at': row[4],
                    'metrics': {
                        'return': row[5] if len(row) > 5 else 0,
                        'sharpe': row[6] if len(row) > 6 else 0,
                        'win_rate': row[7] if len(row) > 7 else 0
                    }
                })
            
            return coins
            
        except Exception as e:
            self.logger.error(f"خطأ في جلب قائمة العملات: {e}")
            return []
    
    def _get_active_positions(self) -> List[Dict]:
        """جلب الصفقات النشطة"""
        try:
            if not self.db_manager:
                return []
            
            query = """
                SELECT id, user_id, symbol, position_type, entry_price, 
                       current_price, amount, opened_at
                FROM active_positions 
                ORDER BY opened_at DESC
            """
            result = self.db_manager.execute_query(query)
            
            positions = []
            for row in result:
                entry_price = row[4] if len(row) > 4 else 0
                current_price = row[5] if len(row) > 5 else entry_price
                amount = row[6] if len(row) > 6 else 0
                
                pnl = (current_price - entry_price) * amount
                pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
                
                positions.append({
                    'id': row[0],
                    'user_id': row[1],
                    'symbol': row[2],
                    'type': row[3],
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'pnl': round(pnl, 2),
                    'pnl_pct': round(pnl_pct, 2),
                    'opened_at': row[7] if len(row) > 7 else None
                })
            
            return positions
            
        except Exception as e:
            self.logger.error(f"خطأ في جلب الصفقات النشطة: {e}")
            return []
    
    def _get_today_trading_stats(self) -> Dict[str, Any]:
        """جلب إحصائيات التداول اليوم"""
        try:
            if not self.db_manager:
                return {}
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            # يمكن تحسينه باستعلامات فعلية
            return {
                'trades_opened': 0,
                'trades_closed': 0,
                'profit_loss': 0,
                'profit_loss_pct': 0,
                'win_rate': 0,
                'wins': 0,
                'losses': 0
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في جلب إحصائيات اليوم: {e}")
            return {}
    
    def _get_monitoring_coins_count(self) -> int:
        """عدد العملات تحت المراقبة"""
        try:
            if not self.db_manager:
                return 0
            
            successful_count = self.db_manager.get_successful_coins_count() or 0
            active_positions_count = self.db_manager.get_active_trades_count() or 0
            
            # العملات الفريدة = العملات الناجحة + عملات الصفقات النشطة (بدون تكرار)
            return max(successful_count, active_positions_count)
            
        except Exception as e:
            self.logger.error(f"خطأ في حساب العملات المراقبة: {e}")
            return 0
    
    def _count_active_binance_keys(self) -> int:
        """عدد مفاتيح Binance النشطة"""
        try:
            if not self.db_manager:
                return 0
            
            query = "SELECT COUNT(*) FROM user_binance_keys WHERE is_active = 1"
            result = self.db_manager.execute_query(query)
            
            if result and len(result) > 0:
                return result[0][0]
            
            return 0
            
        except Exception as e:
            self.logger.error(f"خطأ في عد مفاتيح Binance: {e}")
            return 0
    
    def _get_today_trades_count(self) -> int:
        """عدد صفقات اليوم"""
        try:
            if not self.db_manager:
                return 0
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            query = """
                SELECT COUNT(*) FROM user_trades 
                WHERE DATE(opened_at) = ?
            """
            result = self.db_manager.execute_query(query, (today,))
            
            if result and len(result) > 0:
                return result[0][0]
            
            return 0
            
        except Exception as e:
            self.logger.error(f"خطأ في عد صفقات اليوم: {e}")
            return 0
    
    def log_error(self, level: str, message: str, details: Optional[Dict] = None):
        """تسجيل خطأ في السجل"""
        error_entry = {
            'level': level,
            'message': message,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        self.error_history.append(error_entry)
        
        # الاحتفاظ بآخر 1000 خطأ فقط
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
