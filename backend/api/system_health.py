"""
System Health Check API - مراقبة صحة النظام
التحقق من حالة جميع الأنظمة الأساسية
"""

from backend.core.trading_state_machine import get_trading_state_machine
from backend.infrastructure.db_access import get_db_manager
from backend.api.auth_middleware import require_admin
from flask import Blueprint, jsonify
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

health_bp = Blueprint("health", __name__)
# ✅ Alias للتوافق مع الاستيرادات المختلفة
system_health_bp = health_bp
db = get_db_manager()


def check_trading_system():
    """التحقق من حالة نظام التداول عبر TradingStateMachine"""
    try:
        tsm = get_trading_state_machine()
        state = tsm.get_state() or {}
        trading_state = state.get("trading_state", "STOPPED")
        message = state.get("message", "")

        if trading_state == "RUNNING":
            status = "running"
            message = message or "نظام التداول يعمل"
        elif trading_state in ("STARTING", "STOPPING"):
            status = "warning"
            message = message or f"نظام التداول في حالة {trading_state}"
        elif trading_state == "ERROR":
            status = "error"
            message = message or "نظام التداول في حالة خطأ"
        else:
            status = "stopped"
            message = message or "نظام التداول متوقف"

        return {
            "status": status,
            "message": message,
            "trading_state": trading_state,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"خطأ في التحقق: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


def check_database():
    """التحقق من حالة قاعدة البيانات"""
    try:
        # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]

        return {
            "status": "connected",
            "message": f"قاعدة البيانات متصلة ({count} مستخدم)",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"خطأ في الاتصال: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


def check_binance_api():
    """التحقق من حالة Binance API"""
    try:
        # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM user_binance_keys WHERE is_active=TRUE"
            )
            active_keys = cursor.fetchone()[0]

        if active_keys > 0:
            return {
                "status": "connected",
                "message": f"{active_keys} مفتاح نشط",
                "timestamp": datetime.now().isoformat(),
            }
        return {
            "status": "warning",
            "message": "لا توجد مفاتيح نشطة",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"خطأ: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }


@health_bp.route("/admin/system/health", methods=["GET"])
def get_system_health():
    """
    الحصول على حالة جميع الأنظمة

    Returns:
        {
            "trading_system": {...},
            "database": {...},
            "binance_api": {...},
            "overall_status": "healthy/warning/error"
        }
    """
    try:
        trading = check_trading_system()
        database = check_database()
        binance = check_binance_api()

        # تحديد الحالة العامة
        statuses = [trading["status"], database["status"], binance["status"]]

        if "error" in statuses:
            overall = "error"
        elif "warning" in statuses or "stopped" in statuses:
            overall = "warning"
        else:
            overall = "healthy"

        return jsonify(
            {
                "success": True,
                "data": {
                    "trading_system": trading,
                    "database": database,
                    "binance_api": binance,
                    "overall_status": overall,
                    "timestamp": datetime.now().isoformat(),
                },
            }
        )
    except Exception as e:
        return (
            jsonify({"success": False, "message": f"خطأ في فحص النظام: {str(e)}"}),
            500,
        )


@health_bp.route("/admin/system/critical-errors", methods=["GET"])
def get_critical_errors():
    """
    الحصول على الأخطاء الحرجة فقط

    Returns:
        [
            {
                "id": 1,
                "system": "Trading/Database/API",
                "message": "...",
                "timestamp": "...",
                "resolved": false
            }
        ]
    """
    try:
        # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # نجلب الأخطاء من جدول system_errors (إذا موجود)
            try:
                cursor.execute("""
                    SELECT id, error_type, error_message, timestamp, resolved
                    FROM system_errors
                    WHERE severity = 'critical' AND resolved = FALSE
                    ORDER BY timestamp DESC
                    LIMIT 10
                """)

                errors = []
                for row in cursor.fetchall():
                    errors.append(
                        {
                            "id": row[0],
                            "system": row[1],
                            "message": row[2],
                            "timestamp": row[3],
                            "resolved": bool(row[4]),
                        }
                    )

                return jsonify({"success": True, "data": errors, "count": len(errors)})
            except Exception as inner_error:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"خطأ في قراءة الأخطاء: {str(inner_error)}",
                        }
                    ),
                    500,
                )
    except Exception as e:
        return (
            jsonify({"success": False, "message": f"خطأ في جلب الأخطاء: {str(e)}"}),
            500,
        )


@health_bp.route("/admin/system/errors/<error_id>/resolve", methods=["POST"])
@require_admin
def resolve_error(error_id):
    """وضع علامة على خطأ كمحلول"""
    try:
        # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
        with db.get_write_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE system_errors
                SET resolved = TRUE, resolved_at = %s
                WHERE id = %s
            """,
                (datetime.now().isoformat(), error_id),
            )

        return jsonify({"success": True, "message": "تم وضع علامة محلول على الخطأ"})
    except Exception as e:
        return jsonify({"success": False, "message": f"خطأ: {str(e)}"}), 500


@health_bp.route("/admin/system/restart", methods=["POST"])
def restart_system():
    """
    ⛔ DEPRECATED: استخدم POST /api/admin/trading/start (State Machine)
    هذا المسار معطل لأنه يتجاوز State Machine ولا يحتوي مصادقة.
    """
    return (
        jsonify(
            {
                "success": False,
                "message": "هذا المسار مُلغى. استخدم POST /api/admin/trading/start أو /api/admin/trading/stop",
                "redirect": "/api/admin/trading/start",
            }
        ),
        410,
    )


# ❌ تم حذف هذا الـ endpoint - استخدم /api/admin/background/emergency-stop بدلاً منه
# @health_bp.route('/api/admin/emergency-stop', methods=['POST'])
# def emergency_stop():
#     """
#     ❌ DEPRECATED - استخدم background_control.py بدلاً منه
#     """
#     pass
