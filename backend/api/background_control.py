#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API للتحكم في النظام الخلفي من تطبيق الجوال
============================================

Endpoints:
- POST /api/admin/background/start
- POST /api/admin/background/stop
- POST /api/admin/background/emergency-stop
- GET /api/admin/background/status
- PUT /api/admin/background/settings
- GET /api/admin/background/logs
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from config.logging_config import get_logger
from flask import Blueprint, request, jsonify
from functools import wraps

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'backend'))
sys.path.insert(0, os.path.join(project_root, 'utils'))

from database.database_manager import DatabaseManager
try:
    from utils.error_logger import error_logger
except (ImportError, ModuleNotFoundError):
    error_logger = None

try:
    from utils.unified_operation_logger import unified_logger
except (ImportError, ModuleNotFoundError):
    unified_logger = None

# استيراد الملفات من utils
try:
    from utils.audit_logger import audit_logger
except (ImportError, ModuleNotFoundError):
    audit_logger = None

try:
    from utils.admin_auth import require_admin as admin_require
except (ImportError, ModuleNotFoundError):
    try:
        from backend.utils.admin_auth import require_admin as admin_require
    except (ImportError, ModuleNotFoundError):
        # 🔒 SECURITY: Block ALL requests if auth unavailable (never bypass)
        from flask import jsonify as _jsonify
        logger.error("❌ CRITICAL: admin_auth not available - background endpoints will be BLOCKED")
        def admin_require(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                return _jsonify({'success': False, 'error': 'Admin auth system unavailable'}), 503
            return decorated_function

try:
    from utils.uptime_calculator import uptime_calc
except (ImportError, ModuleNotFoundError):
    uptime_calc = None

# ✅ خدمة إشعارات الأدمن
try:
    from backend.services.admin_notification_service import get_admin_notification_service
    admin_notifier = get_admin_notification_service()
except (ImportError, ModuleNotFoundError):
    admin_notifier = None

# ✅ SK-1 FIX: Process Lock لمنع التشغيل المزدوج
try:
    from utils.process_lock import get_process_lock, is_system_running
    PROCESS_LOCK_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PROCESS_LOCK_AVAILABLE = False
    def get_process_lock(name='trading_bot'):
        return None
    def is_system_running():
        return False, None

background_bp = Blueprint('background_control', __name__, url_prefix='/admin/background')
# ملاحظة: جميع الـ routes تبدأ من /api/admin/background/* (Flask mounted on /api)
logger = get_logger(__name__)
db_manager = DatabaseManager()

# استخدام require_admin الموحد
require_admin = admin_require


def _format_uptime(seconds):
    """تحويل الثواني إلى صيغة مقروءة"""
    if not seconds or seconds <= 0:
        return "0 ثانية"
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    if days > 0:
        return f"{days} يوم {hours} ساعة"
    elif hours > 0:
        return f"{hours} ساعة {minutes} دقيقة"
    elif minutes > 0:
        return f"{minutes} دقيقة"
    else:
        return f"{seconds} ثانية"


@background_bp.route('/start', methods=['POST'])
@require_admin
def start_background_system():
    """
    ⛔ DEPRECATED: استخدم /admin/trading/start (State Machine) بدلاً من هذا
    يُعيد توجيه الطلب للحفاظ على التوافق
    """
    return jsonify({
        "success": False,
        "error": "هذا المسار مُلغى. استخدم POST /api/admin/trading/start",
        "redirect": "/api/admin/trading/start"
    }), 410  # 410 Gone


@background_bp.route('/stop', methods=['POST'])
@require_admin
def stop_background_system():
    """
    ⛔ DEPRECATED: استخدم /admin/trading/stop (State Machine) بدلاً من هذا
    """
    return jsonify({
        "success": False,
        "error": "هذا المسار مُلغى. استخدم POST /api/admin/trading/stop",
        "redirect": "/api/admin/trading/stop"
    }), 410


@background_bp.route('/emergency-stop', methods=['POST'])
@require_admin
def emergency_stop_background_system():
    """
    ⛔ DEPRECATED: استخدم /admin/trading/emergency-stop (State Machine) بدلاً من هذا
    """
    return jsonify({
        "success": False,
        "error": "هذا المسار مُلغى. استخدم POST /api/admin/trading/emergency-stop",
        "redirect": "/api/admin/trading/emergency-stop"
    }), 410


@background_bp.route('/status', methods=['GET'])
@require_admin
def get_background_status():
    """
    الحصول على حالة النظام الخلفي - يتحقق من العملية الفعلية أولاً
    
    الأدمن فقط
    """
    try:
        from pathlib import Path
        
        # ✅ الخطوة 1: التحقق من العملية الفعلية أولاً (المصدر الحقيقي)
        process_running = False
        uptime = 0
        started_at = None
        pid = None
        
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'background_trading_manager.py'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                pid = result.stdout.strip().split('\n')[0]
                process_running = True
                
                # جلب وقت البدء
                ps_result = subprocess.run(
                    ['ps', '-p', pid, '-o', 'lstart='],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if ps_result.returncode == 0 and ps_result.stdout.strip():
                    start_time_str = ps_result.stdout.strip()
                    start_time = datetime.strptime(start_time_str, '%a %b %d %H:%M:%S %Y')
                    started_at = start_time.isoformat()
                    uptime = int((datetime.now() - start_time).total_seconds())
        except Exception as proc_error:
            logger.warning(f"⚠️ فشل فحص العملية: {proc_error}")
        
        # ✅ الخطوة 2: جلب حالة قاعدة البيانات (باستخدام DatabaseManager)
        db_status = {}
        db = DatabaseManager()
        
        try:
            with db.get_connection() as conn:
                status_row = conn.execute("""
                    SELECT status, is_running, last_update, message
                    FROM system_status
                    WHERE id = 1
                """).fetchone()
                db_status = dict(status_row) if status_row else {}
        except Exception as db_err:
            logger.warning(f"⚠️ فشل قراءة DB: {db_err}")
        
        # ✅ الخطوة 3: مزامنة قاعدة البيانات مع الحالة الفعلية
        try:
            with db.get_write_connection() as conn:
                if process_running and not db_status.get('is_running'):
                    conn.execute("""
                        UPDATE system_status 
                        SET status = 'running', is_running = 1, last_update = CURRENT_TIMESTAMP,
                            message = 'النظام يعمل (تم المزامنة)'
                        WHERE id = 1
                    """)
                    logger.info("✅ تم مزامنة حالة DB مع العملية الفعلية (running)")
                elif not process_running and db_status.get('is_running'):
                    conn.execute("""
                        UPDATE system_status 
                        SET status = 'stopped', is_running = 0, last_update = CURRENT_TIMESTAMP,
                            message = 'النظام متوقف (تم المزامنة)'
                        WHERE id = 1
                    """)
                    logger.info("✅ تم مزامنة حالة DB مع العملية الفعلية (stopped)")
        except Exception as sync_err:
            logger.warning(f"⚠️ فشل مزامنة DB: {sync_err}")
        
        # ✅ الخطوة 4: إرجاع الحالة الفعلية (بناءً على العملية، وليس DB)
        actual_status = 'running' if process_running else 'stopped'
        
        return jsonify({
            "success": True,
            "data": {
                "is_running": process_running,
                "status": actual_status,
                "last_update": datetime.now().isoformat(),
                "message": f"النظام {'يعمل' if process_running else 'متوقف'}",
                "uptime": uptime,
                "started_at": started_at,
                "pid": pid,
                "uptime_formatted": _format_uptime(uptime) if process_running else None
            }
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب حالة النظام: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@background_bp.route('/logs', methods=['GET'])
@require_admin
def get_background_logs():
    """
    جلب آخر سجلات النظام الخلفي
    
    الأدمن فقط
    """
    lines = request.args.get('lines', 100, type=int)
    try:
        log_file = "logs/background_trading.log"
        
        if not os.path.exists(log_file):
            return jsonify({
                "success": True,
                "logs": [],
                "message": "لا توجد سجلات بعد"
            })
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return jsonify({
            "success": True,
            "total_lines": len(all_lines),
            "returned_lines": len(last_lines),
            "logs": [line.strip() for line in last_lines]
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب السجلات: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@background_bp.route('/errors', methods=['GET'])
@require_admin
def get_errors():
    """
    جلب الأخطاء من Group B
    
    Parameters:
    - limit: عدد الأخطاء (افتراضي 50)
    - level: فلترة حسب المستوى (info, warning, error, critical)
    - source: فلترة حسب المصدر (group_b, system, binance)
    - resolved: فلترة حسب الحل (true/false)
    
    الأدمن فقط
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        level = request.args.get('level')
        source = request.args.get('source')
        resolved = request.args.get('resolved')
        
        # تحويل resolved من string إلى boolean
        if resolved is not None:
            resolved = resolved.lower() == 'true'
        
        if not error_logger:
            return jsonify({
                "success": True,
                "count": 0,
                "errors": []
            })
        
        errors = error_logger.get_errors(
            limit=limit,
            level=level,
            source=source,
            resolved=resolved
        )
        
        return jsonify({
            "success": True,
            "count": len(errors),
            "errors": errors
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الأخطاء: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@background_bp.route('/errors/critical', methods=['GET'])
@require_admin
def get_critical_errors():
    """
    جلب الأخطاء الحرجة فقط
    
    الأدمن فقط
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        
        if not error_logger:
            return jsonify({
                "success": True,
                "count": 0,
                "critical_errors": []
            })
        
        errors = error_logger.get_critical_errors(limit=limit)
        
        return jsonify({
            "success": True,
            "count": len(errors),
            "critical_errors": errors
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الأخطاء الحرجة: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@background_bp.route('/errors/stats', methods=['GET'])
@require_admin
def get_error_stats():
    """
    جلب إحصائيات الأخطاء
    
    الأدمن فقط
    """
    try:
        if not error_logger:
            return jsonify({
                "success": True,
                "stats": {
                    "total": 0,
                    "critical": 0,
                    "unresolved": 0
                }
            })
        
        stats = error_logger.get_error_stats()
        
        return jsonify({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب إحصائيات الأخطاء: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@background_bp.route('/errors/<int:error_id>/resolve', methods=['POST'])
@require_admin
def resolve_error(error_id):
    """
    وضع علامة على خطأ كمحلول
    
    الأدمن فقط
    """
    try:
        data = request.get_json() or {}
        resolved_by = data.get('resolved_by', 'admin')
        
        if not error_logger:
            return jsonify({
                "success": True,
                "message": f"تم حل الخطأ #{error_id}"
            })
        
        success = error_logger.resolve_error(error_id, resolved_by)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"تم حل الخطأ #{error_id}"
            })
        else:
            return jsonify({
                "success": False,
                "error": "فشل في حل الخطأ"
            }), 500
        
    except Exception as e:
        logger.error(f"❌ خطأ في حل الخطأ: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@background_bp.route('/errors/resolve-all', methods=['POST'])
@require_admin
def resolve_all_errors():
    """
    حل جميع الأخطاء
    
    الأدمن فقط
    """
    try:
        data = request.get_json() or {}
        resolved_by = data.get('resolved_by', 'admin')
        
        if not error_logger:
            return jsonify({
                "success": True,
                "message": "تم حل 0 خطأ",
                "resolved_count": 0
            })
        
        count = error_logger.resolve_all_errors(resolved_by)
        
        return jsonify({
            "success": True,
            "message": f"تم حل {count} خطأ",
            "resolved_count": count
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في حل جميع الأخطاء: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@background_bp.route('/operations/log', methods=['GET'])
@require_admin
def get_operations_log():
    """
    الحصول على السجل الموحد للعمليات
    
    الأدمن فقط
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        operation_type = request.args.get('type', None)
        
        operations = []
        if unified_logger:
            operations = unified_logger.get_recent_operations(limit=limit, operation_type=operation_type)
        
        return jsonify({
            "success": True,
            "data": operations,
            "count": len(operations)
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب السجل: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@background_bp.route('/operations/statistics', methods=['GET'])
@require_admin
def get_operations_statistics():
    """
    الحصول على إحصائيات العمليات
    
    الأدمن فقط
    """
    try:
        stats = {}
        if unified_logger:
            stats = unified_logger.get_statistics()
        
        return jsonify({
            "success": True,
            "data": stats
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الإحصائيات: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
