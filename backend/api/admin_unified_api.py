"""
Admin Unified API - نظام موحد لجميع endpoints الأدمن
ربط حقيقي مع قاعدة البيانات، بدون تكرار أو تضارب
"""

from config.logging_config import get_logger
from flask import Blueprint, request, jsonify, g
import subprocess
import hashlib
import json
from backend.utils.password_utils import hash_password as _hash_pw
from datetime import datetime, timedelta
import os
import sys
from functools import lru_cache
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
repo_root = os.path.dirname(project_root)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'utils'))

from backend.infrastructure.db_access import get_db_manager, open_db_connection
from config.security.encryption_utils import encrypt_data, decrypt_data
from backend.utils.error_logger import error_logger

# إعداد logger
logger = get_logger(__name__)

def get_safe_connection():
    """إنشاء اتصال آمن موحد بقاعدة البيانات."""
    return open_db_connection()

# ✅ FIX: استيراد نظام إبطال الـ cache
try:
    from backend.api.cache_invalidator import invalidate_cache, set_admin_cache, clear_all_cache
    CACHE_INVALIDATION_AVAILABLE = True
    logger.info("✅ Cache invalidation system available")
except ImportError as e:
    CACHE_INVALIDATION_AVAILABLE = False
    logger.warning(f"⚠️ Cache invalidation not available: {e}")
    # Fallback decorator
    def invalidate_cache(*keys):
        def decorator(f):
            return f
        return decorator
    def clear_all_cache():
        return 0

try:
    from utils.audit_logger import audit_logger
except (ImportError, ModuleNotFoundError):
    audit_logger = None

try:
    from backend.utils.admin_auth import require_admin
except (ImportError, ModuleNotFoundError):
    # ❌ لا fallback - نظام المصادقة مطلوب
    # 🔒 إذا فشل الاستيراد، نرفض جميع الطلبات
    from functools import wraps
    from flask import jsonify
    import logging
    _fallback_logger = logging.getLogger(__name__)
    _fallback_logger.error("❌ CRITICAL: admin_auth module not available - all admin endpoints will be blocked")
    
    def require_admin(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            return jsonify({'success': False, 'error': 'Admin authentication system unavailable'}), 503
        return decorated

# استيراد أنظمة منع التكرار
from backend.utils.idempotency_manager import require_idempotency
from backend.utils.request_deduplicator import prevent_concurrent_duplicates

# ✅ استيراد Limiter للـ Rate Limiting
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    # إنشاء limiter instance محلي (سيعمل مع flask_app المسجل عليه هذا Blueprint)
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["100 per minute"],
        storage_uri="memory://"
    )
    LIMITER_AVAILABLE = True
except ImportError:
    LIMITER_AVAILABLE = False
    # Fallback decorator - لا يفعل شيء
    class MockLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    limiter = MockLimiter()

try:
    from utils.uptime_calculator import uptime_calc
except (ImportError, ModuleNotFoundError):
    uptime_calc = None

admin_unified_bp = Blueprint('admin_unified', __name__, url_prefix='/admin')
db = get_db_manager()

# Response Cache - يقلل الطلبات المكررة (30 ثانية)
_cache = {}
_cache_ttl = 30  # ثانية

# ✅ FIX: تعيين مرجع الـ cache لنظام الإبطال
if CACHE_INVALIDATION_AVAILABLE:
    set_admin_cache(_cache)

def get_cached_or_fetch(cache_key, fetch_func, cache_ttl=None):
    """جلب من Cache أو تنفيذ الدالة"""
    now = time.time()
    ttl_to_use = cache_ttl if cache_ttl is not None else _cache_ttl
    if cache_key in _cache:
        data, timestamp = _cache[cache_key]
        if now - timestamp < ttl_to_use:
            return data
    
    data = fetch_func()
    _cache[cache_key] = (data, now)
    return data

# ==================== Register Sub-Module Routes ====================
_admin_shared = {
    'require_admin': require_admin,
    'get_safe_connection': get_safe_connection,
    'db': db,
    'audit_logger': audit_logger,
}

from backend.api.admin_logs_routes import register_admin_logs_routes
from backend.api.admin_ml_routes import register_admin_ml_routes
from backend.api.admin_users_routes import register_admin_users_routes

register_admin_logs_routes(admin_unified_bp, _admin_shared)
register_admin_ml_routes(admin_unified_bp, _admin_shared)
register_admin_users_routes(admin_unified_bp, _admin_shared)

# ==================== Dashboard ====================
@admin_unified_bp.route('/dashboard', methods=['GET'])
@require_admin
def get_admin_dashboard():
    """لوحة تحكم الأدمن الرئيسية"""
    def fetch_dashboard():
        conn = get_safe_connection()
        cursor = conn.cursor()
        
        # إحصائيات المستخدمين
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_type='admin'")
        admin_users = cursor.fetchone()[0]
        
        # إحصائيات التداول — استبعاد الحسابات التجريبية
        cursor.execute("SELECT COUNT(*) FROM active_positions WHERE is_active = FALSE AND is_demo = FALSE")
        total_trades = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM active_positions WHERE is_active = TRUE AND is_demo = FALSE")
        active_trades = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM active_positions WHERE is_demo = FALSE")
        active_positions = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(profit_loss) FROM active_positions WHERE is_active = FALSE AND is_demo = FALSE AND profit_loss > 0")
        total_profit = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(profit_loss) FROM active_positions WHERE is_active = FALSE AND is_demo = FALSE AND profit_loss < 0")
        total_loss = cursor.fetchone()[0] or 0
        
        # حالة النظام
        cursor.execute("SELECT trading_status, database_status FROM system_status ORDER BY id DESC LIMIT 1")
        system_row = cursor.fetchone()
        trading_status = system_row[0] if system_row else 'unknown'
        db_status = system_row[1] if system_row else 'unknown'
        
        conn.close()
        
        # حساب uptime
        uptime_data = {}
        if uptime_calc:
            try:
                uptime_data = uptime_calc.get_uptime()
            except Exception as e:
                logger.debug(f"فشل حساب uptime: {e}")
                uptime_data = {'formatted': '0s'}
        
        return {
            'success': True,
            'data': {
                'users': {
                    'total': total_users,
                    'admins': admin_users,
                    'regular': total_users - admin_users
                },
                'trading': {
                    'total_trades': total_trades,
                    'active_positions': active_positions,
                    'total_profit': round(total_profit, 2),
                    'total_loss': round(abs(total_loss), 2),
                    'net_profit': round(total_profit + total_loss, 2)
                },
                'system': {
                    'status': 'healthy',
                    'trading_status': trading_status,
                    'database_status': db_status,
                    'uptime': uptime_data.get('formatted', '0s')
                },
                'timestamp': datetime.now().isoformat()
            }
        }
    
    try:
        # Dashboard needs real-time updates - temporarily reduce cache TTL
        global _cache_ttl
        original_ttl = _cache_ttl
        _cache_ttl = 5  # 5 seconds cache for real-time updates
        try:
            result = get_cached_or_fetch('admin_dashboard', fetch_dashboard)
            return jsonify(result)
        finally:
            _cache_ttl = original_ttl  # Restore original TTL
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== System Overview ====================
@admin_unified_bp.route('/system/overview', methods=['GET'])
@require_admin
def get_system_overview():
    """نظرة عامة على النظام - تم تغيير المسار لتجنب التعارض مع system_fast_api"""
    def fetch_status():
        conn = get_safe_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM active_positions WHERE is_active = FALSE")
        total_trades = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM active_positions WHERE is_active = TRUE")
        active_trades = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM active_positions")
        active_positions = cursor.fetchone()[0]
        
        conn.close()
        
        # حساب uptime ديناميكياً
        uptime_data = {}
        if uptime_calc:
            try:
                uptime_data = uptime_calc.get_uptime()
            except Exception as e:
                logger.debug(f"فشل حساب uptime: {e}")
                uptime_data = {'uptime_seconds': 0, 'formatted': '0s', 'started_at': datetime.now().isoformat()}
        else:
            uptime_data = {'uptime_seconds': 0, 'formatted': '0s', 'started_at': datetime.now().isoformat()}
        
        return {
            'success': True,
            'data': {
                'status': 'healthy',
                'uptime': uptime_data.get('uptime_seconds', 0),
                'uptime_formatted': uptime_data.get('formatted', '0s'),
                'started_at': uptime_data.get('started_at', datetime.now().isoformat()),
                'users': total_users,
                'trades': total_trades,
                'active_positions': active_positions,
                'timestamp': datetime.now().isoformat()
            }
        }
    
    try:
        result = get_cached_or_fetch('system_status', fetch_status)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/system/stats', methods=['GET'])
@require_admin
def get_system_stats():
    """إحصائيات النظام - مع Caching"""
    def fetch_stats():
        conn = get_safe_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_type='user'")
        regular_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM active_positions WHERE is_active = FALSE AND profit_loss > 0")
        profitable_trades = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM active_positions WHERE is_active = FALSE")
        total_trades = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM active_positions WHERE is_active = TRUE")
        active_trades = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(profit_loss) FROM active_positions WHERE is_active = FALSE")
        total_profit = cursor.fetchone()[0] or 0
        
        conn.close()
        
        win_rate = (profitable_trades / max(total_trades, 1)) * 100
        
        return {
            'success': True,
            'data': {
                'users': regular_users,
                'trades': total_trades,
                'profitable_trades': profitable_trades,
                'win_rate': round(win_rate, 2),
                'total_profit': round(total_profit, 2)
            }
        }
    
    try:
        result = get_cached_or_fetch('system_stats', fetch_stats)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Monitor ====================
@admin_unified_bp.route('/monitor/realtime', methods=['GET'])
@require_admin
def get_realtime_monitor():
    """مراقبة حية للنظام"""
    try:
        conn = get_safe_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM active_positions WHERE is_active = TRUE")
        active_count = cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
        active_users_count = cursor.fetchone()[0] or 0
        conn.close()

        system_metrics = None
        try:
            import psutil
            system_metrics = {
                'cpu_usage': round(psutil.cpu_percent(interval=0.2), 1),
                'memory_usage': round(psutil.virtual_memory().percent, 1),
            }
        except Exception:
            system_metrics = None
        
        return jsonify({
            'success': True,
            'data': {
                'active_positions': active_count,
                'active_users': active_users_count,
                'system': system_metrics
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/monitor/active-users', methods=['GET'])
@require_admin
def get_active_users():
    """المستخدمون النشطون"""
    try:
        conn = get_safe_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, email, name, user_type, last_login_at
            FROM users
            WHERE is_active = TRUE
              AND last_login_at IS NOT NULL
              AND last_login_at >= (CURRENT_TIMESTAMP - INTERVAL '15 minutes')
            ORDER BY last_login_at DESC
            LIMIT 100
        """)
        rows = cursor.fetchall()
        conn.close()

        users = [
            {
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'name': row[3],
                'user_type': row[4],
                'last_login_at': row[5],
            }
            for row in rows
        ]
        return jsonify({'success': True, 'data': users})
    except Exception as e:
        logger.error(f"❌ get_active_users failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Errors ====================
@admin_unified_bp.route('/errors', methods=['GET'])
@require_admin
def get_errors():
    """سجل الأخطاء"""
    try:
        conn = get_safe_connection()
        cursor = conn.cursor()
        
        # التحقق من وجود جدول system_errors
        try:
            cursor.execute("""
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'system_errors'
                LIMIT 1
            """)
            if not cursor.fetchone():
                conn.close()
                return jsonify({
                    'success': True,
                    'data': {
                        'errors': [],
                        'total': 0
                    }
                })
        except Exception as e:
            logger.debug(f"Cache check skipped: {e}")
        
        # Get query parameters for filtering - معالجة آمنة
        severity = request.args.get('severity', default=None)
        resolved = request.args.get('resolved', default=None)
        limit = min(int(request.args.get('limit', 50)), 200)  # حد أقصى 200
        
        # Build query - معالجة آمنة
        query = "SELECT * FROM system_errors WHERE 1=1"
        params = []
        
        # التحقق من صحة severity
        if severity and severity in ['low', 'medium', 'high', 'critical']:
            query += " AND severity = %s"
            params.append(severity)
        
        if resolved is not None and str(resolved).lower() in ['0', '1', 'true', 'false']:
            query += " AND resolved = %s"
            resolved_bool = str(resolved).lower() in ['1', 'true']
            params.append(1 if resolved_bool else 0)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        # Convert to list of dicts - معالجة آمنة للأعمدة المفقودة
        errors = []
        for row in rows:
            try:
                row_dict = dict(zip(column_names, row))
                error_dict = {
                    'id': row_dict.get('id'),
                    'error_type': row_dict.get('error_type') or row_dict.get('source') or 'unknown',
                    'error_message': row_dict.get('error_message'),
                    'user_id': row_dict.get('user_id'),
                    'severity': row_dict.get('severity'),
                    'resolved': bool(row_dict.get('resolved', 0)),
                    'status': row_dict.get('status') or ('resolved' if bool(row_dict.get('resolved', 0)) else 'new'),
                    'created_at': row_dict.get('created_at'),
                    'resolved_at': row_dict.get('resolved_at'),
                    'source': row_dict.get('source') or row_dict.get('error_type') or 'unknown',
                    'details': row_dict.get('details'),
                    'resolved_by': row_dict.get('resolved_by'),
                    'traceback': row_dict.get('traceback'),
                    'attempt_count': int(row_dict.get('attempt_count') or 0),
                    'last_attempt_at': row_dict.get('last_attempt_at'),
                    'requires_admin': bool(row_dict.get('requires_admin', 0)),
                    'auto_action': row_dict.get('auto_action'),
                    'error_fingerprint': row_dict.get('error_fingerprint'),
                }
                errors.append(error_dict)
            except Exception as ke:
                # تخطي الصفوف التي تحتوي على مشاكل
                logger.warning(f"⚠️ تحذير: خطأ في معالجة صف الخطأ: {ke}")
                continue
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM system_errors")
        total_row = cursor.fetchone()
        total = total_row[0] if total_row else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'errors': errors,
                'total': total
            }
        })
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الأخطاء: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/errors/stats', methods=['GET'])
@require_admin
def get_error_stats():
    """إحصائيات الأخطاء"""
    try:
        conn = get_safe_connection()
        cursor = conn.cursor()
        
        # Total errors
        cursor.execute("SELECT COUNT(*) FROM system_errors")
        total = cursor.fetchone()[0]
        
        # Critical errors
        cursor.execute("SELECT COUNT(*) FROM system_errors WHERE severity = 'critical'")
        critical = cursor.fetchone()[0]
        
        # Unresolved errors
        cursor.execute("SELECT COUNT(*) FROM system_errors WHERE resolved = FALSE")
        unresolved = cursor.fetchone()[0]
        
        # Errors by severity
        cursor.execute("""
            SELECT severity, COUNT(*) as count 
            FROM system_errors 
            GROUP BY severity
        """)
        by_severity = {row[0]: row[1] for row in cursor.fetchall()}

        # Errors by lifecycle status
        cursor.execute("""
            SELECT COALESCE(status, CASE WHEN resolved = TRUE THEN 'resolved' ELSE 'new' END) as status, COUNT(*) as count
            FROM system_errors
            GROUP BY COALESCE(status, CASE WHEN resolved = TRUE THEN 'resolved' ELSE 'new' END)
        """)
        by_status = {row[0]: row[1] for row in cursor.fetchall()}

        # Admin intervention queue
        cursor.execute("SELECT COUNT(*) FROM system_errors WHERE resolved = FALSE AND COALESCE(requires_admin, FALSE) = TRUE")
        requires_admin = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'critical': critical,
                'unresolved': unresolved,
                'by_severity': by_severity,
                'by_status': by_status,
                'requires_admin': requires_admin,
            }
        })
    except Exception as e:
        logger.error(f"❌ خطأ في جلب إحصائيات الأخطاء: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/errors/<error_id>/resolve', methods=['PATCH'])
@require_admin
def resolve_error(error_id):
    """تحديد خطأ كمحلول"""
    try:
        resolved_by = 'admin'
        try:
            if hasattr(g, 'user') and isinstance(g.user, dict):
                resolved_by = f"admin:{g.user.get('id', 'unknown')}"
        except Exception:
            pass

        conn = get_safe_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE system_errors
            SET resolved = TRUE,
                resolved_at = CURRENT_TIMESTAMP,
                resolved_by = %s,
                status = 'resolved',
                requires_admin = FALSE
            WHERE id = %s
            """,
            (resolved_by, error_id)
        )
        affected = cursor.rowcount
        conn.commit()
        conn.close()

        if affected == 0:
            return jsonify({'success': False, 'message': 'error_not_found'}), 404

        return jsonify({'success': True, 'message': 'resolved'})
    except Exception as e:
        logger.error(f"❌ خطأ resolve_error #{error_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_unified_bp.route('/errors/resolved', methods=['DELETE'])
@require_admin
def delete_resolved_errors():
    """حذف الأخطاء المحلولة القديمة من قاعدة البيانات"""
    try:
        conn = get_safe_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM system_errors WHERE status IN ('resolved', 'auto_resolved') OR resolved = TRUE"
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        logger.error(f"❌ خطأ delete_resolved_errors: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_unified_bp.route('/errors/auto-heal/run', methods=['POST'])
@require_admin
def run_error_auto_healer():
    """تشغيل محرك أتمتة الأخطاء بشكل يدوي من لوحة الأدمن."""
    try:
        payload = request.get_json(silent=True) or {}
        limit = int(payload.get('limit', 100))
        limit = max(1, min(limit, 500))

        result = error_logger.process_pending_errors(limit=limit)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"❌ خطأ run_error_auto_healer: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Performance ====================
@admin_unified_bp.route('/performance/metrics', methods=['GET'])
@require_admin
def get_performance_metrics():
    """مقاييس الأداء"""
    try:
        conn = get_safe_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM active_positions")
        total_trades = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM active_positions WHERE is_active = TRUE")
        active_positions = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COALESCE(SUM(profit_loss), 0) FROM active_positions WHERE is_active = FALSE")
        total_profit = float(cursor.fetchone()[0] or 0)

        conn.close()

        payload = {
            'timestamp': datetime.now().isoformat(),
            'users': total_users,
            'trades': total_trades,
            'active_positions': active_positions,
            'total_profit': round(total_profit, 2),
        }

        try:
            import psutil
            payload['system'] = {
                'cpu_percent': round(psutil.cpu_percent(interval=0.2), 1),
                'memory_percent': round(psutil.virtual_memory().percent, 1),
                'disk_percent': round(psutil.disk_usage('/').percent, 1),
            }
        except Exception as system_err:
            payload['system'] = None
            payload['system_metrics_error'] = str(system_err)

        return jsonify({'success': True, 'data': payload})
    except Exception as e:
        logger.error(f"❌ get_performance_metrics failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/performance/group-b', methods=['GET'])
@require_admin
def get_group_b_performance():
    """✅ FIX: أداء Group B مع health check حقيقي"""
    try:
        import subprocess
        from datetime import datetime, timedelta
        
        # 1️⃣ فحص Process — background_trading_manager أو trading state machine
        try:
            import shutil as _shutil
            if _shutil.which('pgrep'):
                result = subprocess.run(
                    ['pgrep', '-f', 'background_trading_manager.py'],
                    capture_output=True,
                    text=True
                )
                is_running = bool(result.stdout.strip())
                pid = result.stdout.strip().split('\n')[0] if is_running else None
            else:
                is_running = False
                pid = None
        except Exception:
            is_running = False
            pid = None

        # Fallback: check trading state machine if background process not found
        if not is_running:
            try:
                from backend.core.trading_state_machine import get_trading_state_machine
                tsm = get_trading_state_machine()
                state_info = tsm.get_state()
                if state_info.get('state') == 'RUNNING':
                    is_running = True
                    pid = pid or str(state_info.get('pid', ''))
            except Exception:
                pass

        # 2️⃣ فحص النشاط الفعلي
        last_activity = None
        is_active = False
        health_status = 'stopped'

        conn = get_safe_connection()
        cursor = conn.cursor()

        if is_running:
            # فحص آخر صفقة مفتوحة
            cursor.execute("""
                SELECT MAX(updated_at) FROM active_positions WHERE is_active = TRUE
            """)
            row = cursor.fetchone()
            last_activity = row[0] if row and row[0] else None

            # إذا لا يوجد صفقات مفتوحة، فحص آخر صفقة مغلقة خلال آخر 10 دقائق
            if not last_activity:
                cursor.execute("""
                    SELECT MAX(COALESCE(closed_at, updated_at))
                    FROM active_positions
                    WHERE closed_at >= (CURRENT_TIMESTAMP - INTERVAL '10 minutes')
                       OR updated_at >= (CURRENT_TIMESTAMP - INTERVAL '10 minutes')
                """)
                row2 = cursor.fetchone()
                last_activity = row2[0] if row2 and row2[0] else None

            # ✅ فحص: هل آخر نشاط خلال آخر 5 دقائق؟
            if last_activity:
                last_time = last_activity if isinstance(last_activity, datetime) else datetime.fromisoformat(str(last_activity))
                time_diff = (datetime.now() - last_time).total_seconds() / 60
                if time_diff < 5:
                    is_active = True
                    health_status = 'running'
                else:
                    is_active = False
                    health_status = 'stale'
            else:
                # لا صفقات على الإطلاق — النظام يعمل لكن في مرحلة المسح فقط
                is_active = True
                health_status = 'running'
        
        # 3️⃣ البيانات
        cursor.execute("SELECT COUNT(*), AVG(profit_loss), SUM(profit_loss) FROM active_positions WHERE is_active = FALSE AND profit_loss IS NOT NULL")
        db_result = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) FROM active_positions WHERE is_active = TRUE")
        active_trades = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM successful_coins WHERE is_active = TRUE")
        monitored_coins = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # 4️⃣ الحالة الفعلية
        is_really_running = is_running and is_active
        
        return jsonify({
            'success': True,
            'data': {
                'is_running': is_really_running,     # ✅ الحالة الحقيقية
                'process_running': is_running,        # ✅ Process موجود؟
                'is_active': is_active,               # ✅ نشط فعلاً؟
                'health_status': health_status,       # ✅ 'running', 'stale', 'starting', 'stopped'
                'last_activity': last_activity,       # ✅ آخر نشاط فعلي
                'pid': int(pid) if pid else None,
                'active_trades': active_trades,
                'monitored_coins': monitored_coins,
                'total_trades': db_result[0] or 0,
                'avg_profit': round(db_result[1] or 0, 2),
                'total_profit': round(db_result[2] or 0, 2),
                'status': health_status
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/performance/api', methods=['GET'])
@require_admin
def get_api_performance():
    """أداء API"""
    try:
        conn = get_safe_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM activity_logs")
        total_requests = cursor.fetchone()[0] or 0

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM activity_logs
            WHERE created_at >= (CURRENT_TIMESTAMP - INTERVAL '24 hours')
            """
        )
        requests_24h = cursor.fetchone()[0] or 0

        cursor.execute(
            """
            SELECT status, COUNT(*)
            FROM activity_logs
            GROUP BY status
            """
        )
        by_status = {row[0] or 'unknown': row[1] for row in cursor.fetchall()}

        conn.close()

        return jsonify({
            'success': True,
            'data': {
                'timestamp': datetime.now().isoformat(),
                'total_requests': total_requests,
                'requests_last_24h': requests_24h,
                'by_status': by_status,
                'error_rate_pct': round((by_status.get('failed', 0) / max(total_requests, 1)) * 100, 2),
            }
        })
    except Exception as e:
        logger.error(f"❌ get_api_performance failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Users ====================
@admin_unified_bp.route('/users', methods=['GET'])
@require_admin
def get_all_users():
    """جميع المستخدمين (متوافق مع schema المسار الموحد الجديد /users/all)."""
    try:
        # معالجة آمنة للـ pagination
        page = max(1, request.args.get('page', 1, type=int))
        limit = min(request.args.get('limit', 50, type=int), 200)
        offset = (page - 1) * limit
        
        conn = get_safe_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT
                id, username, email, name, phone_number,
                user_type, is_active, created_at, last_login_at,
                (SELECT COUNT(*) FROM active_positions WHERE user_id = users.id) as total_trades,
                (SELECT COUNT(*) FROM active_positions WHERE user_id = users.id AND is_active = FALSE AND profit_loss > 0) as winning_trades,
                COALESCE((SELECT trading_enabled FROM user_settings WHERE user_id = users.id LIMIT 1), FALSE) as trading_enabled,
                COALESCE((SELECT trading_mode FROM user_settings WHERE user_id = users.id LIMIT 1), 'demo') as trading_mode
            FROM users 
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        users = []
        for row in cursor.fetchall():
            total_trades = row[9] or 0
            winning_trades = row[10] or 0
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            effective_trading_mode = (row[12] or 'demo') if row[5] == 'admin' else 'real'

            users.append({
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'full_name': row[3],
                'phone': row[4],
                'user_type': row[5],
                'is_active': bool(row[6]),
                'created_at': row[7],
                'last_login': row[8],
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': round(win_rate, 1),
                'trading_enabled': bool(row[11]),
                'trading_mode': effective_trading_mode,
            })
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
        active_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_type = 'admin'")
        admin_users = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'users': users,
                'stats': {
                    'total_users': total,
                    'active_users': active_users,
                    'inactive_users': total - active_users,
                    'admin_users': admin_users,
                    'regular_users': total - admin_users,
                },
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total,
                },
            }
        })
    except Exception as e:
        logger.error(f"❌ get_all_users failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_unified_bp.route('/legacy/users/<user_id>', methods=['GET', 'PATCH', 'DELETE'])
@require_admin
@invalidate_cache('admin_dashboard', 'system_stats', 'users_list')  # ✅ FIX (for PATCH/DELETE)
def manage_user(user_id):
    """إدارة مستخدم محدد"""
    if request.method == 'GET':
        try:
            conn = get_safe_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                return jsonify({'success': True, 'data': {'id': user_id}})
            return jsonify({'success': False, 'message': 'User not found'}), 404
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    return jsonify({
        'success': False,
        'message': 'legacy_endpoint_not_supported_use_new_users_routes'
    }), 410

@admin_unified_bp.route('/users/<user_id>/toggle-status', methods=['PATCH'])
@require_admin
def toggle_user_status(user_id):
    """تبديل حالة المستخدم"""
    try:
        target_user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'invalid_user_id'}), 400

    try:
        conn = get_safe_connection()
        cursor = conn.cursor()

        cursor.execute("""
SELECT id, is_active FROM users WHERE id = %s""", (target_user_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'message': 'user_not_found'}), 404

        current_active = bool(row[1])
        next_active = 0 if current_active else 1

        cursor.execute(
            """
            UPDATE users
            SET is_active = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (next_active, target_user_id),
        )
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'data': {
                'id': target_user_id,
                'is_active': bool(next_active),
            }
        })
    except Exception as e:
        logger.error(f"❌ toggle_user_status failed for user #{user_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Trading ====================
@admin_unified_bp.route('/trading/status', methods=['GET'])
@require_admin
def get_trading_status():
    """حالة التداول"""
    try:
        from backend.core.trading_state_machine import get_trading_state_machine

        tsm = get_trading_state_machine()
        state = tsm.get_state() or {}
        trading_state = str(state.get('trading_state') or 'STOPPED').upper()

        return jsonify({
            'success': True,
            'data': {
                'group_b': 'running' if trading_state == 'RUNNING' else 'stopped',
                'enabled': trading_state in ('RUNNING', 'STARTING'),
                'trading_state': trading_state,
                'session_id': state.get('session_id'),
                'mode': state.get('mode', 'PAPER'),
                'open_positions': state.get('open_positions', 0),
                'pid': state.get('pid'),
            }
        })
    except Exception as e:
        logger.error(f"❌ get_trading_status failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/background/trading-status', methods=['GET'])
@require_admin
def get_background_trading_status():
    """حالة التداول الخلفي"""
    try:
        from backend.core.trading_state_machine import get_trading_state_machine

        tsm = get_trading_state_machine()
        state = tsm.get_state() or {}
        trading_state = str(
            state.get('state') or state.get('trading_state') or 'STOPPED'
        ).upper()
        is_running = bool(
            state.get('is_running', state.get('trading_active', False))
        )

        return jsonify({
            'success': bool(state.get('success', True)),
            'data': {
                'status': 'running' if is_running else 'stopped',
                'state': trading_state,
                'trading_state': trading_state,
                'is_running': is_running,
                'message': state.get('message') or ('النظام يعمل' if is_running else 'النظام متوقف'),
                'session_id': state.get('session_id'),
                'mode': state.get('mode', 'PAPER'),
                'open_positions': state.get('open_positions', 0),
                'pid': state.get('pid'),
                'last_update': state.get('last_update'),
                'last_updated': state.get('last_updated'),
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error in get_background_trading_status: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {
                'status': 'error',
                'is_running': False,
                'message': 'حدث خطأ في جلب حالة النظام'
            }
        }), 500

# ❌ REMOVED: Group A System is legacy - no longer exists
# Group A functionality has been replaced by CryptoWave unified trading system
# Historical: Group A was for backtesting/coin selection

@admin_unified_bp.route('/performance/group-a', methods=['GET'])
@require_admin
def get_group_a_performance():
    """
    ⚠️ DEPRECATED: Group A System has been removed
    Functionality moved to CryptoWave unified system
    Use /api/admin/background/status for current trading status
    """
    return jsonify({
        'success': False,
        'deprecated': True,
        'message': 'Group A System has been removed - use CryptoWave system instead',
        'alternative_endpoint': '/api/admin/background/status',
        'info': 'Group A functionality (backtesting/coin selection) is now integrated into CryptoWave'
    }), 410  # 410 Gone - resource permanently removed

@admin_unified_bp.route('/trading/group-b/start', methods=['POST'])
@require_admin
def start_group_b():
    """⛔ DEPRECATED: استخدم /admin/trading/start (State Machine)"""
    return jsonify({
        'success': False,
        'message': 'هذا المسار مُلغى. استخدم POST /api/admin/trading/start',
        'redirect': '/api/admin/trading/start'
    }), 410

@admin_unified_bp.route('/trading/group-b/stop', methods=['POST'])
@require_admin
def stop_group_b():
    """⛔ DEPRECATED: استخدم /admin/trading/stop (State Machine)"""
    return jsonify({
        'success': False,
        'message': 'هذا المسار مُلغى. استخدم POST /api/admin/trading/stop',
        'redirect': '/api/admin/trading/stop'
    }), 410

# ==================== إعادة ضبط الحساب التجريبي ====================
@admin_unified_bp.route('/demo/reset', methods=['POST'])
@require_admin
@limiter.limit("3 per minute")
@prevent_concurrent_duplicates
@require_idempotency('admin_demo_reset')
def reset_demo_account():
    """
    إعادة ضبط الحساب التجريبي للأدمن
    - تصفير سجل الصفقات الوهمية
    - إعادة الرصيد الوهمي إلى الرصيد الأولي الفعلي (المعروض حالياً)
    - حذف كامل تاريخ نمو المحفظة الوهمية
    - مسح بيانات ML (اختياري)
    
    ⚠️ للأدمن فقط
    ⚠️ معزول تماماً عن الحساب الحقيقي
    ⚠️ الرصيد المعاد ضبطه = الرصيد الأولي الفعلي (ليس قيمة ثابتة)
    """
    try:
        admin_id = getattr(g, 'current_user_id', None) or getattr(g, 'user_id', None)
        data = request.get_json() or {}
        reset_ml = data.get('reset_ml', False)  # خيار مسح بيانات ML
        
        deleted_counts = {
            'trades': 0,
            'positions': 0,
            'history': 0,
        }
        initial_balance = getattr(db, 'DEMO_ACCOUNT_INITIAL_BALANCE', 1000.0)

        reset_ok = db.reset_user_portfolio(admin_id, initial_balance=initial_balance)
        if not reset_ok:
            return jsonify({
                'success': False,
                'message': 'فشل إعادة ضبط الحساب التجريبي'
            }), 500
        
        # مسح بيانات ML (اختياري)
        if reset_ml:
            try:
                from pathlib import Path
                
                # استخدام Path بدلاً من os.path.join
                ml_dir = Path(__file__).parent.parent.parent / 'backend' / 'ml' / 'saved_models'
                
                # حذف ملفات ML
                ml_files = ['training_data.pkl', 'scaler.pkl', 'signal_model.json']
                for f in ml_files:
                    fpath = ml_dir / f
                    if fpath.exists():
                        fpath.unlink()
                        deleted_counts[f'file_{f}'] = True
                        logger.info(f"🗑️ تم مسح {f}")
                
                # مسح بيانات ML من DB باتصال كتابة مستقل
                with db.get_write_connection() as ml_conn:
                    ml_cursor = ml_conn.cursor()
                    try:
                        ml_cursor.execute("DELETE FROM ml_patterns")
                        deleted_counts['patterns'] = ml_cursor.rowcount
                    except Exception:
                        deleted_counts['patterns'] = 0

                    try:
                        ml_cursor.execute("DELETE FROM trade_learning_log")
                        deleted_counts['trade_learning_log'] = ml_cursor.rowcount
                    except Exception:
                        deleted_counts['trade_learning_log'] = 0

                    try:
                        ml_cursor.execute("DELETE FROM signal_learning")
                        deleted_counts['signal_learning'] = ml_cursor.rowcount
                    except Exception:
                        deleted_counts['signal_learning'] = 0

                    try:
                        ml_cursor.execute("DELETE FROM learning_validation_log")
                        deleted_counts['learning_validation_log'] = ml_cursor.rowcount
                    except Exception:
                        deleted_counts['learning_validation_log'] = 0
                    
            except Exception as ml_err:
                logger.warning(f"⚠️ فشل مسح بيانات ML: {ml_err}")
        
        # تسجيل العملية
        if audit_logger:
            try:
                audit_logger.log(
                    action='reset_demo_account',
                    user_id=admin_id,
                    details={'message': f'إعادة ضبط الحساب التجريبي: {deleted_counts}'}
                )
            except Exception as audit_err:
                logger.warning(f"⚠️ فشل تسجيل العملية في audit_logger: {audit_err}")
        
        logger.info(f"✅ تم إعادة ضبط الحساب التجريبي للأدمن {admin_id}")
        
        return jsonify({
            'success': True,
            'message': 'تم إعادة ضبط الحساب التجريبي بنجاح',
            'data': {
                'deleted_trades': deleted_counts.get('trades', 0),
                'deleted_positions': deleted_counts.get('positions', 0),
                'deleted_history': deleted_counts.get('history', 0),
                'ml_reset': bool(
                    reset_ml and (
                        deleted_counts.get('file_training_data.pkl')
                        or deleted_counts.get('file_scaler.pkl')
                        or deleted_counts.get('file_signal_model.json')
                        or deleted_counts.get('patterns', 0) > 0
                        or deleted_counts.get('trade_learning_log', 0) > 0
                        or deleted_counts.get('signal_learning', 0) > 0
                        or deleted_counts.get('learning_validation_log', 0) > 0
                    )
                ),
                'ml_reset_requested': bool(reset_ml),
                'patterns_reset': deleted_counts.get('patterns', 0),
                'trade_learning_log': deleted_counts.get('trade_learning_log', 0),
                'signal_learning': deleted_counts.get('signal_learning', 0),
                'learning_validation_log': deleted_counts.get('learning_validation_log', 0),
                'new_balance': initial_balance
            }
        })
        
    except Exception as e:
        logger.error(f"❌ فشل إعادة ضبط الحساب التجريبي: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'فشل إعادة ضبط الحساب: {str(e)}'
        }), 500

# ==================== Positions ====================
@admin_unified_bp.route('/positions/active', methods=['GET'])
@require_admin
def get_active_positions():
    """الصفقات النشطة"""
    try:
        from flask import request, g
        from backend.utils.trading_context import get_trading_context
        # ✅ استخدام request context بدلاً من g مباشرة
        admin_id = getattr(g, 'user_id', None) or 1
        requested_mode = request.args.get('mode')
        trading_context = get_trading_context(db, admin_id, requested_mode=requested_mode)
        is_demo = trading_context['is_demo']
        
        conn = get_safe_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, symbol, entry_price, quantity, strategy, timeframe, 
                   stop_loss, take_profit, created_at, position_type
            FROM active_positions 
            WHERE user_id = %s AND is_demo = %s AND is_active = TRUE
            ORDER BY created_at DESC
            LIMIT 20
        """, (admin_id, is_demo))
        
        rows = cursor.fetchall()
        
        # ✅ جلب الأسعار الحالية من Binance
        symbols = list(set(row['symbol'] for row in rows))
        current_prices = {}
        try:
            from backend.utils.data_provider import DataProvider
            data_provider = DataProvider()
            for symbol in symbols:
                try:
                    # ✅ FIX: get_ticker doesn't exist — use get_current_price
                    price = data_provider.get_current_price(symbol)
                    if price and isinstance(price, (int, float)) and price > 0:
                        current_prices[symbol] = float(price)
                except Exception as e:
                    logger.debug(f"⚠️ فشل جلب سعر {symbol}: {e}")
        except Exception as e:
            logger.warning(f"⚠️ فشل جلب الأسعار: {e}")
        
        positions = []
        for row in rows:
            symbol = row['symbol']
            entry_price = float(row['entry_price'])
            quantity = float(row['quantity'])
            position_type = row['position_type'] if row['position_type'] else 'long'
            current_price = current_prices.get(symbol, entry_price)
            
            # ✅ FIX: DB stores 'long'/'short', NOT 'BUY'/'SELL'
            is_long = position_type.lower() in ('long', 'buy')
            if is_long:
                pnl = (current_price - entry_price) * quantity
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl = (entry_price - current_price) * quantity
                pnl_pct = ((entry_price - current_price) / entry_price) * 100
            
            positions.append({
                'id': row['id'],
                'symbol': symbol,
                'entry_price': entry_price,
                'current_price': current_price,
                'quantity': quantity,
                'strategy': row['strategy'],
                'timeframe': row['timeframe'],
                'stop_loss': row['stop_loss'],
                'take_profit': row['take_profit'],
                'created_at': row['created_at'],
                'position_type': position_type,
                'profit_loss': round(pnl, 2),
                'profit_loss_percentage': round(pnl_pct, 2),
                'is_profitable': pnl > 0
            })
        
        # ✅ ترتيب حسب نسبة الربح (الأعلى أولاً)
        positions.sort(key=lambda x: x['profit_loss_percentage'], reverse=True)
        
        conn.close()
        
        return jsonify({'success': True, 'data': positions})
    except Exception as e:
        logger.error(f"Error getting active positions: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/positions/<position_id>/close', methods=['POST'])
@require_admin
@invalidate_cache('admin_dashboard', 'portfolio', 'active_positions')  # ✅ FIX
def close_position(position_id):
    """إغلاق صفقة"""
    try:
        pid = int(position_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'invalid_position_id'}), 400

    payload = request.get_json(silent=True) or {}
    reason = str(payload.get('reason') or 'ADMIN_MANUAL_CLOSE')
    requested_exit = payload.get('exit_price')

    try:
        conn = get_safe_connection()
        cursor = conn.cursor()

        position = cursor.execute(
            """
            SELECT id, user_id, symbol, entry_price, quantity, position_type, is_demo, is_active
            FROM active_positions
            WHERE id = %s
            LIMIT 1
            """,
            (pid,),
        ).fetchone()
        conn.close()

        if not position:
            return jsonify({'success': False, 'message': 'position_not_found'}), 404

        if not bool(position['is_active']):
            return jsonify({'success': False, 'message': 'position_already_closed'}), 409

        entry_price = float(position['entry_price'] or 0)
        quantity = float(position['quantity'] or 0)
        if entry_price <= 0 or quantity <= 0:
            return jsonify({'success': False, 'message': 'invalid_position_data'}), 400

        exit_price = 0.0
        try:
            if requested_exit is not None:
                exit_price = float(requested_exit)
        except (TypeError, ValueError):
            exit_price = 0.0

        if exit_price <= 0:
            try:
                from backend.utils.data_provider import DataProvider
                market_price = DataProvider().get_current_price(position['symbol'])
                if market_price and float(market_price) > 0:
                    exit_price = float(market_price)
            except Exception as price_err:
                logger.debug(f"Close position fallback price failed: {price_err}")

        if exit_price <= 0:
            exit_price = entry_price

        position_type = str(position['position_type'] or 'long').lower()
        is_long = position_type in ('long', 'buy')
        pnl_raw = ((exit_price - entry_price) * quantity) if is_long else ((entry_price - exit_price) * quantity)

        is_demo = int(position['is_demo'] or 0)
        DEMO_COMMISSION_RATE = 0.001  # 0.1% per side — matches _simulate_demo_fill
        exit_commission = round(exit_price * quantity * DEMO_COMMISSION_RATE, 8) if bool(is_demo) else 0.0
        pnl = pnl_raw - exit_commission

        close_ok = db.close_position(
            position_id=pid,
            exit_price=exit_price,
            exit_reason=reason,
            pnl=pnl,
            exit_commission=exit_commission,
            exit_order_id='ADMIN_MANUAL_CLOSE',
        )
        if not close_ok:
            return jsonify({'success': False, 'message': 'close_position_failed'}), 500

        try:
            user_id = int(position['user_id'])
            is_demo = int(position['is_demo'] or 0)
            with get_safe_connection() as balance_conn:
                balance_query = "SELECT available_balance FROM demo_accounts WHERE user_id = %s LIMIT 1" if bool(is_demo) else "SELECT available_balance FROM portfolio WHERE user_id = %s AND is_demo = %s LIMIT 1"
                balance_params = (user_id,) if bool(is_demo) else (user_id, is_demo)
                bal_row = balance_conn.execute(balance_query, balance_params).fetchone()
            if bal_row is not None:
                available_before = float(bal_row[0] or 0)
                returned_amount = (entry_price * quantity) + pnl
                new_available = available_before + returned_amount
                db.update_user_balance(user_id, new_available, bool(is_demo))
        except Exception as bal_err:
            logger.warning(f"⚠️ position #{pid} closed but balance sync failed: {bal_err}")

        return jsonify({
            'success': True,
            'data': {
                'position_id': pid,
                'symbol': position['symbol'],
                'exit_price': round(exit_price, 8),
                'pnl': round(pnl, 8),
                'reason': reason,
            }
        })
    except Exception as e:
        logger.error(f"❌ close_position failed for position #{position_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/positions/<position_id>/stop-loss', methods=['PATCH'])
@require_admin
def update_stop_loss(position_id):
    """تحديث SL"""
    try:
        pid = int(position_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'invalid_position_id'}), 400

    payload = request.get_json(silent=True) or {}
    if 'stop_loss' not in payload:
        return jsonify({'success': False, 'message': 'stop_loss_required'}), 400

    try:
        new_sl = float(payload.get('stop_loss'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'invalid_stop_loss'}), 400

    if new_sl <= 0:
        return jsonify({'success': False, 'message': 'stop_loss_must_be_positive'}), 400

    try:
        conn = get_safe_connection()
        cursor = conn.cursor()

        row = cursor.execute(
            """
            SELECT id, is_active, stop_loss, symbol
            FROM active_positions
            WHERE id = %s
            LIMIT 1
            """,
            (pid,),
        ).fetchone()
        if not row:
            conn.close()
            return jsonify({'success': False, 'message': 'position_not_found'}), 404

        if not bool(row['is_active']):
            conn.close()
            return jsonify({'success': False, 'message': 'position_not_active'}), 409

        cursor.execute(
            """
            UPDATE active_positions
            SET stop_loss = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (new_sl, pid),
        )
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'data': {
                'position_id': pid,
                'symbol': row['symbol'],
                'old_stop_loss': row['stop_loss'],
                'new_stop_loss': new_sl,
            }
        })
    except Exception as e:
        logger.error(f"❌ update_stop_loss failed for position #{position_id}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Trades ====================
@admin_unified_bp.route('/trades/history', methods=['GET'])
@require_admin
def get_trade_history():
    """سجل الصفقات"""
    try:
        conn = get_safe_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol, entry_price, exit_price, profit_loss as profit,
                   COALESCE(entry_date, created_at::text) as entry_time, is_demo
            FROM active_positions
            WHERE is_active = FALSE
            ORDER BY COALESCE(entry_date, created_at::text) DESC
            LIMIT 100
        """)
        
        trades = []
        for row in cursor.fetchall():
            trades.append({
                'symbol': row[0],
                'entry': row[1],
                'exit': row[2],
                'profit': row[3],
                'date': row[4],
                'mode': 'demo' if bool(row[5]) else 'real'
            })
        
        conn.close()
        
        return jsonify({'success': True, 'data': trades})
    except Exception as e:
        logger.error(f"خطأ في جلب سجل الصفقات: {e}")
        return jsonify({'success': False, 'message': 'خطأ في جلب سجل الصفقات'}), 500

@admin_unified_bp.route('/trades/stats', methods=['GET'])
@require_admin
def get_trade_stats():
    """إحصائيات الصفقات"""
    try:
        conn = get_safe_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as closed_total,
                SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as wins,
                AVG(profit_loss) as avg_profit,
                SUM(profit_loss) as total_profit
            FROM active_positions
            WHERE is_active = FALSE
        """)
        closed_result = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(*) as active_total
            FROM active_positions
            WHERE is_active = TRUE
        """)
        active_result = cursor.fetchone()

        closed_total = closed_result[0] or 0
        active_total = active_result[0] or 0
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total': closed_total + active_total,
                'active_trades': active_total,
                'closed_trades': closed_total,
                'wins': closed_result[1] or 0,
                'avg_profit': round(closed_result[2] or 0, 2),
                'total_profit': round(closed_result[3] or 0, 2)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/trades', methods=['GET'])
@require_admin
def get_trades():
    """الحصول على الصفقات"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('pageSize', 10, type=int)
        
        conn = get_safe_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM active_positions ORDER BY id DESC LIMIT %s OFFSET %s", (page_size, (page-1)*page_size))
        trades = cursor.fetchall()
        conn.close()
        
        return jsonify({'success': True, 'data': trades or [], 'page': page})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_unified_bp.route('/trades/export', methods=['GET'])
@require_admin
def export_trades():
    """تصدير الصفقات"""
    try:
        export_format = (request.args.get('format', 'json') or 'json').strip().lower()
        limit = min(max(int(request.args.get('limit', 500)), 1), 5000)

        conn = get_safe_connection()
        cursor = conn.cursor()
        rows = cursor.execute(
            """
            SELECT id, user_id, symbol, strategy, timeframe,
                   CASE WHEN position_type IN ('long', 'LONG') THEN 'buy' ELSE 'sell' END AS side,
                   entry_price, exit_price, quantity, profit_loss,
                   profit_pct AS profit_loss_percentage,
                   CASE WHEN is_active = TRUE THEN 'open' ELSE 'closed' END AS status,
                   is_demo,
                   COALESCE(entry_date, created_at::text) AS entry_time,
                   closed_at AS exit_time, created_at
            FROM active_positions
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
        cols = [c[0] for c in cursor.description] if cursor.description else []
        conn.close()

        trades = [dict(zip(cols, row)) for row in rows]

        if export_format == 'csv':
            import csv
            import io
            from flask import Response

            output = io.StringIO()
            writer = csv.writer(output)
            header = [
                'id', 'user_id', 'symbol', 'strategy', 'timeframe', 'side',
                'entry_price', 'exit_price', 'quantity', 'profit_loss',
                'profit_loss_percentage', 'status', 'is_demo', 'entry_time',
                'exit_time', 'created_at'
            ]
            writer.writerow(header)
            for t in trades:
                writer.writerow([t.get(col) for col in header])

            csv_body = output.getvalue()
            output.close()
            return Response(
                csv_body,
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=trades_export.csv'}
            )

        return jsonify({
            'success': True,
            'data': {
                'count': len(trades),
                'trades': trades,
            }
        })
    except Exception as e:
        logger.error(f"❌ export_trades failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Analytics ====================
@admin_unified_bp.route('/analytics/overview', methods=['GET'])
@require_admin
def get_analytics_overview():
    """نظرة عامة على التحليلات"""
    try:
        conn = get_safe_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM active_positions WHERE is_active = FALSE")
        total_trades = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM active_positions WHERE is_active = TRUE")
        active_trades = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(profit_loss) FROM active_positions WHERE is_active = FALSE")
        total_profit = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total_users': total_users,
                'total_trades': total_trades + active_trades,
                'active_trades': active_trades,
                'closed_trades': total_trades,
                'total_profit': round(total_profit, 2)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_unified_bp.route('/analytics/revenue', methods=['GET'])
@require_admin
def get_analytics_revenue():
    """تحليل الإيرادات"""
    try:
        conn = get_safe_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT SUM(profit_loss) FROM active_positions WHERE is_active = FALSE AND profit_loss > 0")
        revenue = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(profit_loss) FROM active_positions WHERE is_active = FALSE AND profit_loss < 0")
        losses = abs(cursor.fetchone()[0] or 0)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'revenue': round(revenue, 2),
                'losses': round(losses, 2),
                'net': round(revenue - losses, 2)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== Backtesting ====================
@admin_unified_bp.route('/backtest/results', methods=['GET'])
@require_admin
def get_backtest_results():
    """نتائج الاختبار الخلفي"""
    try:
        results_dir = os.path.join(repo_root, 'tests', 'backtest_results')
        if not os.path.isdir(results_dir):
            return jsonify({'success': True, 'data': {'available': False, 'results': []}})

        files = [
            os.path.join(results_dir, f)
            for f in os.listdir(results_dir)
            if f.endswith('.json')
        ]
        if not files:
            return jsonify({'success': True, 'data': {'available': False, 'results': []}})

        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        latest_file = files[0]

        latest_data = {}
        try:
            with open(latest_file, 'r', encoding='utf-8') as fh:
                latest_data = json.load(fh)
        except Exception as parse_err:
            latest_data = {'error': f'parse_error: {parse_err}'}

        return jsonify({
            'success': True,
            'data': {
                'available': True,
                'latest_file': os.path.basename(latest_file),
                'latest_updated_at': datetime.fromtimestamp(os.path.getmtime(latest_file)).isoformat(),
                'files_count': len(files),
                'latest_result': latest_data,
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_unified_bp.route('/backtest/run', methods=['POST'])
@require_admin
def run_backtest():
    """تشغيل الاختبار الخلفي"""
    try:
        payload = request.get_json(silent=True) or {}
        script_name = str(payload.get('script', 'v8_backtest.py')).strip()

        allowed = {
            'v8_backtest.py',
            'v8_optimal_backtest.py',
            'v8_comprehensive_backtest.py',
            'realistic_backtest.py',
            'optimized_backtest.py',
        }
        if script_name not in allowed:
            return jsonify({'success': False, 'message': 'script_not_allowed'}), 400

        script_path = os.path.join(repo_root, 'tests', script_name)
        if not os.path.exists(script_path):
            return jsonify({'success': False, 'message': 'script_not_found'}), 404

        proc = subprocess.Popen(
            [sys.executable, script_path],
            cwd=repo_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return jsonify({
            'success': True,
            'message': 'backtest_started',
            'data': {
                'script': script_name,
                'pid': proc.pid,
            }
        })
    except Exception as e:
        logger.error(f"❌ run_backtest failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_unified_bp.route('/database/stats', methods=['GET'])
@require_admin
def get_database_stats():
    """إحصائيات قاعدة البيانات"""
    try:
        counts = db.get_database_stats()
        return jsonify({
            'success': True,
            'data': {
                'engine': 'postgresql',
                'tables': len(counts),
                'path': db.database_url,
                'table_row_counts': counts,
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/database/backup', methods=['POST'])
@require_admin
def create_backup():
    """إنشاء نسخة احتياطية"""
    try:
        return jsonify({
            'success': False,
            'message': 'postgres_backup_requires_pg_dump_workflow'
        }), 501
    except Exception as e:
        logger.error(f"❌ create_backup failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/database/restore', methods=['POST'])
@require_admin
def restore_backup():
    """استعادة نسخة احتياطية"""
    return jsonify({'success': False, 'message': 'postgres_restore_requires_psql_workflow'}), 501

@admin_unified_bp.route('/database/optimize', methods=['POST'])
@require_admin
def optimize_database():
    """تحسين قاعدة البيانات"""
    try:
        if getattr(db, 'is_postgres', lambda: False)():
            return jsonify({'success': True, 'message': 'PostgreSQL optimization is managed automatically'})
        with db.get_write_connection() as conn:
            conn.execute('VACUUM')
        return jsonify({'success': True, 'message': 'Database optimized'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Notifications ====================
@admin_unified_bp.route('/notifications', methods=['GET'])
@require_admin
def get_notifications():
    """جلب إشعارات النظام (System Alerts فقط)"""
    try:
        from backend.monitoring.system_alerts import get_system_alert_service
        alert_service = get_system_alert_service()
        
        # جلب جميع الإشعارات غير المقروءة
        alerts = alert_service.get_unread_alerts(limit=100)
        
        return jsonify({'success': True, 'data': alerts})
        
    except Exception as e:
        logger.error(f"فشل جلب إشعارات النظام: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/notifications/<int:notification_id>/read', methods=['PATCH'])
@require_admin
def mark_notification_read(notification_id):
    """تحديد إشعار نظام كمقروء"""
    try:
        from backend.monitoring.system_alerts import get_system_alert_service
        alert_service = get_system_alert_service()
        
        success = alert_service.mark_as_read(notification_id)
        
        if success:
            return jsonify({'success': True, 'data': {'notification_id': notification_id, 'updated': True}})
        return jsonify({'success': False, 'message': 'notification_update_failed'}), 500
            
    except Exception as e:
        logger.error(f"فشل تحديث الإشعار: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/notifications/mark-all-read', methods=['PATCH'])
@require_admin
def mark_all_read():
    """تحديد جميع إشعارات النظام كمقروءة"""
    try:
        from backend.monitoring.system_alerts import get_system_alert_service
        alert_service = get_system_alert_service()
        
        success = alert_service.mark_all_as_read()
        
        if success:
            return jsonify({'success': True, 'data': {'updated': True}})
        return jsonify({'success': False, 'message': 'notifications_update_failed'}), 500
            
    except Exception as e:
        logger.error(f"فشل تحديث الإشعارات: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Health Check ====================
@admin_unified_bp.route('/health', methods=['GET'])
@require_admin
def health_check():
    """فحص صحة النظام الكامل"""
    try:
        from backend.monitoring.health_check import get_health_check_service
        health_service = get_health_check_service()
        
        health_status = health_service.check_all()
        
        return jsonify({'success': True, 'data': health_status})
        
    except Exception as e:
        logger.error(f"فشل Health Check: {e}")
        return jsonify({
            'success': False,
            'message': 'health_check_failed',
            'error': str(e),
        }), 500

@admin_unified_bp.route('/system/metrics', methods=['GET'])
@require_admin
def get_system_metrics():
    """جلب مقاييس النظام (CPU, RAM, Disk)"""
    try:
        import psutil
        
        metrics = {
            'cpu': {
                'percent': round(psutil.cpu_percent(interval=1), 1),
                'count': psutil.cpu_count()
            },
            'memory': {
                'percent': round(psutil.virtual_memory().percent, 1),
                'used_gb': round(psutil.virtual_memory().used / (1024**3), 2),
                'total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                'available_gb': round(psutil.virtual_memory().available / (1024**3), 2)
            },
            'disk': {
                'percent': round(psutil.disk_usage('/').percent, 1),
                'used_gb': round(psutil.disk_usage('/').used / (1024**3), 2),
                'total_gb': round(psutil.disk_usage('/').total / (1024**3), 2),
                'free_gb': round(psutil.disk_usage('/').free / (1024**3), 2)
            }
        }
        
        return jsonify({'success': True, 'data': metrics})
    except ModuleNotFoundError as e:
        logger.warning(f"⚠️ psutil غير مثبت: {e}")
        return jsonify({'success': False, 'message': 'system_metrics_unavailable', 'error': str(e)}), 503
        
    except Exception as e:
        logger.error(f"فشل جلب مقاييس النظام: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Circuit Breaker Management ====================
@admin_unified_bp.route('/system/circuit-breakers', methods=['GET'])
@require_admin
def get_circuit_breakers():
    """جلب حالة جميع الـ Circuit Breakers"""
    try:
        from backend.utils.circuit_breaker import circuit_breaker_manager
        states = circuit_breaker_manager.get_all_states()
        return jsonify({'success': True, 'data': states})
    except Exception as e:
        logger.error(f"فشل جلب حالة الـ circuit breakers: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/system/circuit-breakers/reset', methods=['POST'])
@require_admin
def reset_circuit_breakers():
    """إعادة تعيين جميع الـ Circuit Breakers لإعادة الاتصال بـ Binance"""
    try:
        from backend.utils.circuit_breaker import circuit_breaker_manager
        circuit_breaker_manager.reset_all()
        logger.warning("⚠️ تم إعادة تعيين جميع الـ Circuit Breakers بواسطة الأدمن")
        return jsonify({
            'success': True, 
            'message': 'تم إعادة تعيين جميع الـ Circuit Breakers - جرب الاتصال مجدداً'
        })
    except Exception as e:
        logger.error(f"فشل إعادة تعيين الـ circuit breakers: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Binance Connection Status ====================
@admin_unified_bp.route('/system/binance-status', methods=['GET'])
@require_admin
def get_binance_connection_status():
    """فحص حالة الاتصال الحقيقية بـ Binance مع تشخيص كامل"""
    try:
        from backend.utils.data_provider import DataProvider
        
        dp = DataProvider()
        status = dp.get_connection_status()
        
        # تحديد حالة التداول بناءً على الاتصال
        trading_status = 'healthy'
        if not status.get('connected'):
            trading_status = 'disconnected'
            if status.get('error') == 'CIRCUIT_OPEN':
                trading_status = 'degraded'
        
        return jsonify({
            'success': True,
            'data': {
                'connection': status,
                'trading_status': trading_status,
                'can_trade': status.get('connected', False),
                'last_check': status.get('timestamp')
            }
        })
    except Exception as e:
        logger.error(f"فشل فحص حالة Binance: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/system/binance-retry', methods=['POST'])
@require_admin
def retry_binance_connection():
    """محاولة إعادة الاتصال بـ Binance"""
    try:
        from backend.utils.data_provider import DataProvider
        
        dp = DataProvider()
        result = dp.retry_connection()
        
        return jsonify({
            'success': result.get('success', False),
            'message': result.get('message', ''),
            'latency_ms': result.get('latency_ms')
        })
    except Exception as e:
        logger.error(f"فشل إعادة الاتصال: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Public System Status (for app) ====================
@admin_unified_bp.route('/system/public-status', methods=['GET'])
def get_public_system_status():
    """الحالة العامة للنظام بدون مصادقة - للتطبيق"""
    try:
        from backend.core.trading_state_machine import get_trading_state_machine

        tsm = get_trading_state_machine()
        state = tsm.get_state()

        return jsonify({
            'success': True,
            'data': {
                **state,
                'is_running': state.get('trading_active', False),
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"فشل جلب الحالة العامة: {e}")
        return jsonify({
            'success': True,
            'data': {
                'state': 'ERROR',
                'trading_state': 'ERROR',
                'trading_active': False,
                'is_running': False,
                'status': 'unknown',
                'message': 'خطأ',
                'error': str(e)
            }
        })

# ==================== Notification Services Status ====================
@admin_unified_bp.route('/system/notifications-status', methods=['GET'])
def get_notifications_status():
    """فحص حالة خدمات الإشعارات"""
    try:
        status = {
            'fcm_available': False,
            'sms_available': False,
            'push_enabled': False,
            'sms_enabled': False,
            'provider_errors': {}
        }
        
        try:
            from backend.services.admin_notification_service import get_admin_notification_service
            service = get_admin_notification_service()
            settings = service.get_settings() or {}
            status['push_enabled'] = bool(settings.get('push_enabled', False))
            status['sms_enabled'] = bool(settings.get('sms_enabled', False))
        except Exception as e:
            status['provider_errors']['settings'] = str(e)
        
        try:
            import sys
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            sys.path.insert(0, project_root)
            sys.path.insert(0, os.path.join(project_root, 'utils'))
            from firebase_notification_service import FirebaseNotificationService
            fcm = FirebaseNotificationService()
            status['fcm_available'] = bool(getattr(fcm, 'is_available', False))
        except Exception as e:
            status['provider_errors']['fcm'] = str(e)
        
        try:
            from backend.utils.firebase_sms_service import FirebaseSMSHandler
            sms = FirebaseSMSHandler()
            status['sms_available'] = bool(getattr(sms, 'is_available', False))
        except Exception as e:
            status['provider_errors']['sms'] = str(e)
        
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"فشل فحص حالة الإشعارات: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Config ====================
@admin_unified_bp.route('/config', methods=['GET', 'PATCH'])
@require_admin
def manage_config():
    """إدارة الإعدادات"""
    global _cache_ttl

    if request.method == 'GET':
        return jsonify({
            'success': True,
            'data': {
                'cache_ttl_seconds': _cache_ttl,
                'cache_entries': len(_cache),
                'cache_invalidation_available': CACHE_INVALIDATION_AVAILABLE,
            }
        })

    payload = request.get_json(silent=True) or {}
    updated = {}

    try:
        if 'cache_ttl_seconds' in payload:
            new_ttl = int(payload.get('cache_ttl_seconds'))
            if new_ttl < 5 or new_ttl > 3600:
                return jsonify({'success': False, 'message': 'cache_ttl_seconds_out_of_range'}), 400

            _cache_ttl = new_ttl
            updated['cache_ttl_seconds'] = _cache_ttl

        if payload.get('clear_cache') is True:
            _cache.clear()
            updated['cache_cleared'] = True

        if not updated:
            return jsonify({'success': False, 'message': 'no_supported_fields'}), 400

        return jsonify({'success': True, 'data': updated})
    except Exception as e:
        logger.error(f"❌ manage_config PATCH failed: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Binance ====================
@admin_unified_bp.route('/binance/status', methods=['GET'])
@require_admin
def get_binance_status():
    """حالة Binance"""
    try:
        user_id = getattr(g, 'user_id', None) or 1
        conn = get_safe_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM user_binance_keys WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        is_connected = bool(result[0]) if result else False
        
        return jsonify({
            'success': True,
            'data': {
                'connected': is_connected,
                'api_configured': is_connected
            }
        })
    except Exception as e:
        logger.warning(f"⚠️ فشل التحقق من اتصال Binance: {e}")
        return jsonify({'success': True, 'data': {'connected': False}})

@admin_unified_bp.route('/binance/keys', methods=['GET'])
@require_admin
def get_binance_keys():
    """مفاتيح Binance"""
    try:
        user_id = getattr(g, 'user_id', None) or 1
        conn = get_safe_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT api_key, api_secret, is_active 
            FROM user_binance_keys 
            WHERE user_id = %s
        """, (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            try:
                api_key = decrypt_data(result[0]) if result[0] else ''
                return jsonify({
                    'success': True,
                    'data': {
                        'apiKey': api_key[:10] + '...' if len(api_key) > 10 else '',
                        'configured': bool(result[2])
                    }
                })
            except Exception as e:
                logger.debug(f"Binance keys check skipped: {e}")
        
        return jsonify({'success': True, 'data': {'configured': False}})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/binance/test', methods=['POST'])
@require_admin
def test_binance_connection():
    """اختبار اتصال Binance"""
    try:
        user_id = getattr(g, 'user_id', None) or 1

        from backend.utils.binance_manager import BinanceManager
        manager = BinanceManager()
        result = manager.verify_user_api_keys(user_id)

        connected = bool(result.get('success'))
        return jsonify({
            'success': True,
            'data': {
                'connected': connected,
                'details': result,
            }
        })
    except Exception as e:
        logger.warning(f"⚠️ test_binance_connection failed: {e}")
        return jsonify({
            'success': True,
            'data': {
                'connected': False,
                'details': {'success': False, 'message': str(e)},
            }
        }), 200

# ==================== Routes extracted to sub-modules ====================
# activity-logs, audit/log, reports/*, logs/*, cleanup/* → admin_logs_routes.py
# system/ml-status, ml/*, notification-settings/* → admin_ml_routes.py
# users/all, users/create, users/update, users/delete → admin_users_routes.py

@admin_unified_bp.route('/security-audit-log', methods=['GET'])
@require_admin
def get_security_audit_log_direct():
    """سجل التدقيق الأمني — security_audit_log (direct registration)"""
    try:
        page = max(1, int(request.args.get('page', 1)))
        limit = min(int(request.args.get('limit', 50)), 200)
        offset = (page - 1) * limit
        with db.get_connection() as conn:
            total_row = conn.execute("SELECT COUNT(*) AS count FROM security_audit_log").fetchone()
            rows = conn.execute("""
                SELECT id, user_id, action, resource, ip_address, status, details, created_at
                FROM security_audit_log
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (limit, offset)).fetchall()
        total = int((total_row['count'] if total_row and 'count' in total_row else total_row[0]) if total_row else 0)
        logs = [dict(r) for r in rows]
        return jsonify({
            'success': True,
            'data': {'logs': logs, 'total': total, 'page': page, 'limit': limit}
        })
    except Exception as e:
        logger.error(f"Error fetching security audit log: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

_END_OF_MAIN_ROUTES = True
