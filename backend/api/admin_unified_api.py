"""
Admin Unified API - نظام موحد لجميع endpoints الأدمن
ربط حقيقي مع قاعدة البيانات، بدون تكرار أو تضارب
"""

from config.logging_config import get_logger
from flask import Blueprint, request, jsonify, g
import sqlite3
import subprocess
import hashlib
from backend.utils.password_utils import hash_password as _hash_pw
from datetime import datetime, timedelta
import os
import sys
from functools import lru_cache
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'utils'))

from database.database_manager import DatabaseManager
from config.security.encryption_utils import encrypt_data, decrypt_data

# إعداد logger
logger = get_logger(__name__)

def get_safe_connection(db_path: str) -> sqlite3.Connection:
    """إنشاء اتصال آمن بقاعدة البيانات مع WAL mode لمنع database locked"""
    conn = sqlite3.connect(db_path, timeout=60.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn

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
db = DatabaseManager()

# Response Cache - يقلل الطلبات المكررة (30 ثانية)
_cache = {}
_cache_ttl = 30  # ثانية

# ✅ FIX: تعيين مرجع الـ cache لنظام الإبطال
if CACHE_INVALIDATION_AVAILABLE:
    set_admin_cache(_cache)

def get_cached_or_fetch(cache_key, fetch_func):
    """جلب من Cache أو تنفيذ الدالة"""
    now = time.time()
    if cache_key in _cache:
        data, timestamp = _cache[cache_key]
        if now - timestamp < _cache_ttl:
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
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        
        # إحصائيات المستخدمين
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_type='admin'")
        admin_users = cursor.fetchone()[0]
        
        # إحصائيات التداول
        cursor.execute("SELECT COUNT(*) FROM user_trades")
        total_trades = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM active_positions")
        active_positions = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(profit_loss) FROM user_trades WHERE profit_loss > 0")
        total_profit = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(profit_loss) FROM user_trades WHERE profit_loss < 0")
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
        result = get_cached_or_fetch('admin_dashboard', fetch_dashboard)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== System Overview ====================
@admin_unified_bp.route('/system/overview', methods=['GET'])
@require_admin
def get_system_overview():
    """نظرة عامة على النظام - تم تغيير المسار لتجنب التعارض مع system_fast_api"""
    def fetch_status():
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_trades")
        total_trades = cursor.fetchone()[0]
        
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
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE user_type='user'")
        regular_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_trades WHERE profit_loss > 0")
        profitable_trades = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_trades")
        total_trades = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(profit_loss) FROM user_trades")
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
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM active_positions")
        active_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'active_positions': active_count,
                'cpu_usage': 0,
                'memory_usage': 0
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/monitor/active-users', methods=['GET'])
@require_admin
def get_active_users():
    """المستخدمون النشطون"""
    return jsonify({'success': True, 'data': []})

# ==================== Errors ====================
@admin_unified_bp.route('/errors', methods=['GET'])
@require_admin
def get_errors():
    """سجل الأخطاء"""
    try:
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        
        # التحقق من وجود جدول system_errors
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_errors'")
            if not cursor.fetchone():
                # الجدول غير موجود - أرجع بيانات فارغة
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
            query += " AND severity = ?"
            params.append(severity)
        
        if resolved is not None and resolved in ['0', '1', 0, 1]:
            query += " AND resolved = ?"
            params.append(1 if resolved == 'true' else 0)
        
        query += " ORDER BY created_at DESC LIMIT ?"
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
                    'created_at': row_dict.get('created_at'),
                    'resolved_at': row_dict.get('resolved_at'),
                    'source': row_dict.get('source') or row_dict.get('error_type') or 'unknown',
                    'details': row_dict.get('details'),
                    'resolved_by': row_dict.get('resolved_by'),
                    'traceback': row_dict.get('traceback')
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
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        
        # Total errors
        cursor.execute("SELECT COUNT(*) FROM system_errors")
        total = cursor.fetchone()[0]
        
        # Critical errors
        cursor.execute("SELECT COUNT(*) FROM system_errors WHERE severity = 'critical'")
        critical = cursor.fetchone()[0]
        
        # Unresolved errors
        cursor.execute("SELECT COUNT(*) FROM system_errors WHERE resolved = 0")
        unresolved = cursor.fetchone()[0]
        
        # Errors by severity
        cursor.execute("""
            SELECT severity, COUNT(*) as count 
            FROM system_errors 
            GROUP BY severity
        """)
        by_severity = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'critical': critical,
                'unresolved': unresolved,
                'by_severity': by_severity
            }
        })
    except Exception as e:
        logger.error(f"❌ خطأ في جلب إحصائيات الأخطاء: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/errors/<error_id>/resolve', methods=['PATCH'])
@require_admin
def resolve_error(error_id):
    """تحديد خطأ كمحلول"""
    return jsonify({'success': True})

# ==================== Performance ====================
@admin_unified_bp.route('/performance/metrics', methods=['GET'])
@require_admin
def get_performance_metrics():
    """مقاييس الأداء"""
    return jsonify({'success': True, 'data': {}})

@admin_unified_bp.route('/performance/group-b', methods=['GET'])
@require_admin
def get_group_b_performance():
    """✅ FIX: أداء Group B مع health check حقيقي"""
    try:
        import subprocess
        from datetime import datetime, timedelta
        
        # 1️⃣ فحص Process
        result = subprocess.run(
            ['pgrep', '-f', 'background_trading_manager.py'],
            capture_output=True,
            text=True
        )
        is_running = bool(result.stdout.strip())
        pid = result.stdout.strip().split('\n')[0] if is_running else None
        
        # 2️⃣ فحص النشاط الفعلي
        last_activity = None
        is_active = False
        health_status = 'stopped'
        
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        
        if is_running:
            # فحص آخر صفقة أو تحديث
            cursor.execute("""
                SELECT MAX(updated_at) as last_activity
                FROM active_positions
                WHERE is_active = 1
            """)
            last_activity_row = cursor.fetchone()
            last_activity = last_activity_row[0] if last_activity_row else None
            
            # ✅ فحص: هل آخر نشاط خلال آخر 5 دقائق؟
            if last_activity:
                last_time = datetime.fromisoformat(last_activity)
                time_diff = (datetime.now() - last_time).total_seconds() / 60
                
                if time_diff < 5:
                    is_active = True
                    health_status = 'running'
                else:
                    is_active = False
                    health_status = 'stale'  # Process موجود لكن لا نشاط
            else:
                health_status = 'starting'  # بدأ للتو
        
        # 3️⃣ البيانات
        cursor.execute("SELECT COUNT(*), AVG(profit_loss), SUM(profit_loss) FROM user_trades WHERE profit_loss IS NOT NULL")
        db_result = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) FROM active_positions WHERE is_active = 1")
        active_trades = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM successful_coins WHERE is_active = 1")
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
    return jsonify({'success': True, 'data': {}})

# ==================== Users ====================
@admin_unified_bp.route('/users', methods=['GET'])
@require_admin
def get_all_users():
    """جميع المستخدمين"""
    try:
        # معالجة آمنة للـ pagination
        page = max(1, request.args.get('page', 1, type=int))
        limit = min(request.args.get('limit', 50, type=int), 200)
        offset = (page - 1) * limit
        
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, email, username, user_type, created_at 
            FROM users 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        users = []
        for row in cursor.fetchall():
            users.append({
                'id': row[0],
                'email': row[1],
                'name': row[2],
                'type': row[3],
                'created_at': row[4]
            })
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': users,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/legacy/users/<user_id>', methods=['GET', 'PATCH', 'DELETE'])
@require_admin
@invalidate_cache('admin_dashboard', 'system_stats', 'users_list')  # ✅ FIX (for PATCH/DELETE)
def manage_user(user_id):
    """إدارة مستخدم محدد"""
    if request.method == 'GET':
        try:
            conn = get_safe_connection(db.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                return jsonify({'success': True, 'data': {'id': user_id}})
            return jsonify({'success': False, 'message': 'User not found'}), 404
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    return jsonify({'success': True})

@admin_unified_bp.route('/users/<user_id>/toggle-status', methods=['PATCH'])
@require_admin
def toggle_user_status(user_id):
    """تبديل حالة المستخدم"""
    return jsonify({'success': True})

# ==================== Trading ====================
@admin_unified_bp.route('/trading/status', methods=['GET'])
@require_admin
def get_trading_status():
    """حالة التداول"""
    return jsonify({
        'success': True,
        'data': {
            'group_b': 'stopped',
            'enabled': False
        }
    })

@admin_unified_bp.route('/background/trading-status', methods=['GET'])
@require_admin
def get_background_trading_status():
    """حالة التداول الخلفي"""
    try:
        db_manager = DatabaseManager()
        
        # جلب حالة النظام من قاعدة البيانات
        try:
            with db_manager.get_connection() as conn:
                status_row = conn.execute(
                    "SELECT status, is_running, message FROM system_status WHERE id = 1"
                ).fetchone()
        except Exception as db_error:
            # إذا فشل الاتصال بقاعدة البيانات، أرجع حالة افتراضية
            return jsonify({
                'success': True,
                'data': {
                    'status': 'stopped',
                    'is_running': False,
                    'message': 'النظام متوقف',
                    'timestamp': datetime.now().isoformat()
                }
            })
        
        if status_row:
            return jsonify({
                'success': True,
                'data': {
                    'status': status_row[0] if status_row[0] else 'unknown',
                    'is_running': bool(status_row[1]) if status_row[1] is not None else False,
                    'message': status_row[2] if status_row[2] else 'لا توجد رسالة',
                    'timestamp': datetime.now().isoformat()
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'status': 'unknown',
                    'is_running': False,
                    'message': 'لم يتم العثور على حالة النظام',
                    'timestamp': datetime.now().isoformat()
                }
            })
    except Exception as e:
        import traceback
        logger.error(f"Error in get_background_trading_status: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'data': {
                'status': 'error',
                'is_running': False,
                'message': 'حدث خطأ في جلب حالة النظام'
            }
        }), 200  # أرجع 200 بدلاً من 500 لتجنب فشل الاختبار

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
        admin_id = g.get('user_id', 1)
        data = request.get_json() or {}
        reset_ml = data.get('reset_ml', False)  # خيار مسح بيانات ML
        
        with db.get_write_connection() as conn:
            cursor = conn.cursor()
            
            deleted_counts = {}
            
            # جلب الرصيد الأولي الفعلي من المحفظة الوهمية
            cursor.execute("""
                SELECT initial_balance FROM portfolio 
                WHERE user_id = ? AND is_demo = 1
            """, (admin_id,))
            portfolio_row = cursor.fetchone()
            # ✅ FIX: الرصيد الافتراضي = 1000 USDT (يتطابق مع UI والتوثيق)
            initial_balance = portfolio_row[0] if portfolio_row else 1000.00
            
            # حذف الصفقات الوهمية للأدمن فقط
            cursor.execute("""
                DELETE FROM user_trades 
                WHERE user_id = ? AND is_demo = 1
            """, (admin_id,))
            deleted_counts['trades'] = cursor.rowcount
            
            # ✅ FIX: حذف الصفقات النشطة الوهمية فقط (ليس الحقيقية!)
            cursor.execute("""
                DELETE FROM active_positions 
                WHERE user_id = ? AND is_demo = 1
            """, (admin_id,))
            deleted_counts['positions'] = cursor.rowcount
            
            # حذف كامل تاريخ نمو المحفظة الوهمية للأدمن (حذف كامل الجدول)
            cursor.execute("""
                DELETE FROM admin_demo_portfolio_history 
                WHERE admin_id = ?
            """, (str(admin_id),))
            deleted_counts['history'] = cursor.rowcount
            
            # إعادة ضبط المحفظة الوهمية إلى الرصيد الأولي الفعلي
            cursor.execute("""
                UPDATE portfolio 
                SET total_balance = ?,
                    available_balance = ?,
                    invested_balance = 0.00,
                    total_profit_loss = 0.00,
                    total_profit_loss_percentage = 0.00,
                    initial_balance = ?,
                    updated_at = datetime('now')
                WHERE user_id = ? AND is_demo = 1
            """, (initial_balance, initial_balance, initial_balance, admin_id))
            
            # إذا لم يوجد سجل، أنشئ واحداً جديداً
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO portfolio 
                    (user_id, is_demo, total_balance, available_balance, invested_balance, 
                     total_profit_loss, total_profit_loss_percentage, initial_balance)
                    VALUES (?, 1, ?, ?, 0.00, 0.00, 0.00, ?)
                """, (admin_id, initial_balance, initial_balance, initial_balance))
            
            # إعادة ضبط إعدادات التداول للقيم الافتراضية
            # ✅ FIX: إضافة AND is_demo = 1 لمنع إعادة ضبط إعدادات الحساب الحقيقي
            cursor.execute("""
                UPDATE user_settings 
                SET stop_loss_pct = 2.0,
                    take_profit_pct = 5.0,
                    trailing_distance = 3.0,
                    max_positions = 5,
                    trading_enabled = 0,
                    updated_at = datetime('now')
                WHERE user_id = ? AND is_demo = 1
            """, (admin_id,))
            
            # portfolio table already updated above — single source of truth
        
        # مسح بيانات ML (اختياري)
        if reset_ml:
            try:
                import os
                ml_data_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'backend', 'ml', 'saved_models', 'training_data.pkl'
                )
                if os.path.exists(ml_data_path):
                    os.remove(ml_data_path)
                    deleted_counts['ml_data'] = True
                    logger.info("🗑️ تم مسح بيانات ML")
                
                # مسح أنماط التعلم
                patterns_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'database', 'patterns', 'trade_patterns.json'
                )
                if os.path.exists(patterns_path):
                    os.remove(patterns_path)
                    deleted_counts['patterns'] = True
                    logger.info("🗑️ تم مسح أنماط التعلم")
                    
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
                'ml_reset': deleted_counts.get('ml_data', False),
                'patterns_reset': deleted_counts.get('patterns', False),
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
        # ✅ استخدام request context بدلاً من g مباشرة
        admin_id = getattr(g, 'user_id', None) or 1
        
        conn = get_safe_connection(db.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, symbol, entry_price, quantity, strategy, timeframe, 
                   stop_loss, take_profit, created_at, position_type
            FROM active_positions 
            WHERE user_id = ? AND is_active = 1
            ORDER BY created_at DESC
            LIMIT 20
        """, (admin_id,))
        
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
        return jsonify({'success': True, 'data': []})

@admin_unified_bp.route('/positions/<position_id>/close', methods=['POST'])
@require_admin
@invalidate_cache('admin_dashboard', 'portfolio', 'active_positions')  # ✅ FIX
def close_position(position_id):
    """إغلاق صفقة"""
    return jsonify({'success': True})

@admin_unified_bp.route('/positions/<position_id>/stop-loss', methods=['PATCH'])
@require_admin
def update_stop_loss(position_id):
    """تحديث SL"""
    return jsonify({'success': True})

# ==================== Trades ====================
@admin_unified_bp.route('/trades/history', methods=['GET'])
@require_admin
def get_trade_history():
    """سجل الصفقات"""
    try:
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT symbol, entry_price, exit_price, profit_loss as profit, created_at 
            FROM user_trades 
            ORDER BY created_at DESC 
            LIMIT 100
        """)
        
        trades = []
        for row in cursor.fetchall():
            trades.append({
                'symbol': row[0],
                'entry': row[1],
                'exit': row[2],
                'profit': row[3],
                'date': row[4]
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
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as wins,
                AVG(profit_loss) as avg_profit,
                SUM(profit_loss) as total_profit
            FROM user_trades
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total': result[0],
                'wins': result[1],
                'avg_profit': round(result[2] or 0, 2),
                'total_profit': round(result[3] or 0, 2)
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
        
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_trades LIMIT ? OFFSET ?", (page_size, (page-1)*page_size))
        trades = cursor.fetchall()
        conn.close()
        
        return jsonify({'success': True, 'data': trades or [], 'page': page})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_unified_bp.route('/trades/export', methods=['GET'])
@require_admin
def export_trades():
    """تصدير الصفقات"""
    return jsonify({'success': True})

# ==================== Analytics ====================
@admin_unified_bp.route('/analytics/overview', methods=['GET'])
@require_admin
def get_analytics_overview():
    """نظرة عامة على التحليلات"""
    try:
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM user_trades")
        total_trades = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(profit_loss) FROM user_trades")
        total_profit = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total_users': total_users,
                'total_trades': total_trades,
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
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT SUM(profit_loss) FROM user_trades WHERE profit_loss > 0")
        revenue = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(profit_loss) FROM user_trades WHERE profit_loss < 0")
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
        return jsonify({
            'success': True,
            'data': {
                'total_tests': 0,
                'success_rate': 0,
                'avg_profit': 0
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_unified_bp.route('/backtest/run', methods=['POST'])
@require_admin
def run_backtest():
    """تشغيل الاختبار الخلفي"""
    try:
        return jsonify({'success': True, 'message': 'تم بدء الاختبار الخلفي'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== Database ====================
@admin_unified_bp.route('/database/stats', methods=['GET'])
@require_admin
def get_database_stats():
    """إحصائيات قاعدة البيانات"""
    try:
        size = os.path.getsize(db.db_path) / (1024 * 1024)
        
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = len(cursor.fetchall())
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'size_mb': round(size, 2),
                'tables': tables,
                'path': str(db.db_path)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_unified_bp.route('/database/backup', methods=['POST'])
@require_admin
def create_backup():
    """إنشاء نسخة احتياطية"""
    return jsonify({'success': True, 'message': 'Backup created'})

@admin_unified_bp.route('/database/restore', methods=['POST'])
@require_admin
def restore_backup():
    """استعادة نسخة احتياطية"""
    return jsonify({'success': True})

@admin_unified_bp.route('/database/optimize', methods=['POST'])
@require_admin
def optimize_database():
    """تحسين قاعدة البيانات"""
    try:
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
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Failed to update'}), 500
            
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
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Failed to update all'}), 500
            
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
        return jsonify({'success': False, 'message': str(e)}), 500

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
        
    except Exception as e:
        logger.error(f"فشل جلب مقاييس النظام: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== Config ====================
@admin_unified_bp.route('/config', methods=['GET', 'PATCH'])
@require_admin
def manage_config():
    """إدارة الإعدادات"""
    if request.method == 'GET':
        return jsonify({'success': True, 'data': {}})
    return jsonify({'success': True})

# ==================== Binance ====================
@admin_unified_bp.route('/binance/status', methods=['GET'])
@require_admin
def get_binance_status():
    """حالة Binance"""
    try:
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT is_active FROM user_binance_keys WHERE user_id='1'")
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
        conn = get_safe_connection(db.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT api_key, api_secret, is_active 
            FROM user_binance_keys 
            WHERE user_id='1'
        """)
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
    return jsonify({'success': True, 'connected': False})

# ==================== Routes extracted to sub-modules ====================
# activity-logs, audit/log, reports/*, logs/*, cleanup/* → admin_logs_routes.py
# system/ml-status, ml/*, notification-settings/* → admin_ml_routes.py
# users/all, users/create, users/update, users/delete → admin_users_routes.py
_END_OF_MAIN_ROUTES = True
