"""
ML Learning API Endpoints
نقاط API لعرض تقدم نظام التعلم الذكي في لوحة الأدمن
"""

from flask import Blueprint, jsonify, request
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# إنشاء Blueprint
ml_learning_bp = Blueprint('ml_learning', __name__, url_prefix='/ml/learning')


# 🔒 حماية endpoints الأدمن
try:
    from backend.utils.admin_auth import require_admin as admin_required
except (ImportError, ModuleNotFoundError):
    logger.error("❌ CRITICAL: admin_auth not available - ML learning endpoints will be blocked")
    def admin_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return jsonify({'success': False, 'error': 'Auth system unavailable'}), 503
        return decorated_function


@ml_learning_bp.route('/progress/<int:user_id>', methods=['GET'])
@admin_required
def get_learning_progress(user_id):
    """
    الحصول على تقدم التعلم لمستخدم معين
    
    Returns:
        {
            "success": true,
            "data": {
                "total_signals_processed": 150,
                "total_combinations": 8,
                "learned_combinations": 3,
                "overall_win_rate": 0.65,
                "learning_stage": "developing",
                "system_readiness": 50.5,
                ...
            }
        }
    """
    try:
        from backend.ml.smart_incremental_learning import get_learning_system
        
        # الحصول على نظام التعلم للمستخدم
        learning_system = get_learning_system(user_id)
        
        # الحصول على التقدم
        progress = learning_system.get_learning_progress()
        
        return jsonify({
            'success': True,
            'data': progress
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب تقدم التعلم: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_learning_bp.route('/health', methods=['GET'])
@admin_required
def get_system_health():
    """
    الحصول على صحة نظام التعلم
    
    Returns:
        {
            "success": true,
            "data": {
                "latest_check": "2024-01-10T10:30:00",
                "current_health_score": 0.85,
                "trend": "improving",
                "recent_issues": 0,
                "recent_corrections": 2,
                ...
            }
        }
    """
    try:
        # يمكن جلب هذا من جميع المستخدمين أو مستخدم محدد
        user_id = request.args.get('user_id', type=int, default=1)
        
        from backend.ml.smart_incremental_learning import get_learning_system
        
        learning_system = get_learning_system(user_id)
        
        # فحص صحة يومي
        health_report = learning_system.health_monitor.get_health_report()
        
        return jsonify({
            'success': True,
            'data': health_report
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب صحة النظام: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_learning_bp.route('/combination/<path:combination>', methods=['GET'])
@admin_required
def get_combination_details(combination):
    """
    الحصول على تفاصيل تركيبة معينة
    
    Args:
        combination: symbol_strategy_timeframe (e.g., BTCUSDT_trend_following_1h)
    
    Returns:
        {
            "success": true,
            "data": {
                "combination": "BTCUSDT_trend_following_1h",
                "total_signals": 45,
                "wins": 30,
                "losses": 15,
                "win_rate": 0.67,
                "patterns": {...},
                ...
            }
        }
    """
    try:
        user_id = request.args.get('user_id', type=int, default=1)
        
        from backend.ml.smart_incremental_learning import get_learning_system
        
        learning_system = get_learning_system(user_id)
        
        # الحصول على تقرير التركيبة
        report = learning_system.get_detailed_combination_report(combination)
        
        if not report:
            return jsonify({
                'success': False,
                'error': 'لا توجد بيانات كافية لهذه التركيبة'
            }), 404
        
        return jsonify({
            'success': True,
            'data': report
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب تفاصيل التركيبة: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_learning_bp.route('/stats/summary', methods=['GET'])
@admin_required
def get_learning_summary():
    """
    ملخص شامل لنظام التعلم (جميع المستخدمين أو مستخدم محدد)
    
    Returns:
        {
            "success": true,
            "data": {
                "total_users": 10,
                "total_signals": 1500,
                "average_win_rate": 0.63,
                "top_combinations": [...],
                "system_performance": {...}
            }
        }
    """
    try:
        user_id = request.args.get('user_id', type=int)
        
        from backend.ml.smart_incremental_learning import _learning_instances
        
        if user_id:
            # ملخص لمستخدم واحد
            from backend.ml.smart_incremental_learning import get_learning_system
            learning_system = get_learning_system(user_id)
            progress = learning_system.get_learning_progress()
            
            summary = {
                'user_id': user_id,
                'progress': progress,
                'dual_path_performance': progress['dual_path_performance'],
                'health_status': progress['health_status']
            }
        else:
            # ملخص لجميع المستخدمين
            total_signals = 0
            total_users = len(_learning_instances)
            all_win_rates = []
            
            for uid, system in _learning_instances.items():
                progress = system.get_learning_progress()
                total_signals += progress['total_signals_processed']
                if progress['overall_win_rate'] > 0:
                    all_win_rates.append(progress['overall_win_rate'])
            
            summary = {
                'total_users': total_users,
                'total_signals': total_signals,
                'average_win_rate': sum(all_win_rates) / len(all_win_rates) if all_win_rates else 0,
                'active_users': total_users
            }
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الملخص: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_learning_bp.route('/run-health-check', methods=['POST'])
@admin_required
def trigger_health_check():
    """
    تشغيل فحص صحة يدوي
    
    Body:
        {
            "user_id": 1
        }
    
    Returns:
        {
            "success": true,
            "data": {
                "checks_performed": 4,
                "issues_found": 1,
                "corrections_applied": 1,
                ...
            }
        }
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 1)
        
        from backend.ml.smart_incremental_learning import get_learning_system
        from database.database_manager import DatabaseManager
        
        learning_system = get_learning_system(user_id)
        db = DatabaseManager()
        
        # جلب آخر الصفقات
        recent_trades = []
        try:
            with db.get_connection() as conn:
                trades = conn.execute("""
                    SELECT * FROM active_positions
                    WHERE user_id = %s AND is_active = 0
                    ORDER BY COALESCE(closed_at, updated_at) DESC
                    LIMIT 50
                """, (user_id,)).fetchall()
                
                recent_trades = [dict(t) for t in trades]
        except Exception as e:
            logger.warning(f"⚠️ لم يتم جلب الصفقات: {e}")
        
        # تشغيل الفحص
        health_check = learning_system.run_daily_health_check(recent_trades)
        
        return jsonify({
            'success': True,
            'data': health_check
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل فحص الصحة: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# معلومات عن الـ Blueprint
@ml_learning_bp.route('/info', methods=['GET'])
def get_info():
    """معلومات عن API التعلم"""
    return jsonify({
        'name': 'ML Learning API',
        'version': '1.0',
        'description': 'Smart Incremental Learning System API',
        'endpoints': {
            'GET /progress/<user_id>': 'تقدم التعلم لمستخدم',
            'GET /health': 'صحة النظام',
            'GET /combination/<combination>': 'تفاصيل تركيبة',
            'GET /stats/summary': 'ملخص شامل',
            'POST /run-health-check': 'فحص صحة يدوي'
        }
    })
