"""
System Endpoints - نقاط نهاية النظام العامة
"""

from flask import Blueprint, jsonify, request
from config.logging_config import get_logger
from backend.api.auth_middleware import require_auth
from backend.infrastructure.db_access import get_db_manager

# إنشاء Blueprint (بدون /api لأن Flask مثبت على /api في unified_server.py)
system_bp = Blueprint('system', __name__, url_prefix='/system')

# إعداد السجلات
logger = get_logger(__name__)


@system_bp.route('/status', methods=['GET'])
def get_system_status():
    """
    الحصول على حالة النظام العامة
    لا يحتاج مصادقة - معلومات عامة
    """
    try:
        db = get_db_manager()
        
        # الحصول على حالة النظام من قاعدة البيانات
        with db.get_connection() as conn:
            # جلب الأعمدة الفعلية الموجودة في جدول system_status
            system_status = conn.execute("""
                SELECT status, last_update, is_running, total_users, active_trades, total_trades, trading_state
                FROM system_status
                WHERE id = 1
            """).fetchone()
            
            if not system_status:
                return jsonify({
                    'success': False,
                    'error': 'system_status_record_not_found'
                }), 404

            trading_state = str(system_status[6] or '').upper() if system_status[6] is not None else ''
            effective_running = trading_state == 'RUNNING'
            if not trading_state:
                effective_running = bool(system_status[2])
                trading_state = 'RUNNING' if effective_running else 'STOPPED'

            return jsonify({
                'success': True,
                'data': {
                    'status': 'running' if effective_running else 'stopped',
                    'lastUpdate': system_status[1],
                    'tradingActive': effective_running,
                    'totalUsers': system_status[3],
                    'activeTrades': system_status[4],
                    'totalTrades': system_status[5],
                    'serverStatus': system_status[0],
                    'trading_state': trading_state,
                    'tradingState': trading_state,
                }
            })
    
    except Exception as e:
        logger.error(f"❌ خطأ في الحصول على حالة النظام: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/reset-account-data', methods=['POST'])
@require_auth
def reset_account_data():
    """
    إعادة تعيين بيانات الحساب
    يحذف جميع الصفقات والمحفظة والإعدادات
    """
    try:
        import os
        jwt_secret = os.getenv('JWT_SECRET_KEY')
        if not jwt_secret:
            return jsonify({'success': False, 'error': 'Server configuration error'}), 500
        from ..utils.jwt_manager import JWTManager
        
        db = get_db_manager()
        data = request.get_json()
        
        # الحصول على user_id من Token
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.split(' ')[1]
        jwt_manager = JWTManager(secret_key=jwt_secret)
        payload = jwt_manager.verify_token(token)
        user_id = payload.get('user_id')
        
        # يمكن للمستخدم فقط إعادة تعيين حسابه الخاص
        request_user_id = data.get('userId')
        if request_user_id and request_user_id != user_id:
            return jsonify({'success': False, 'error': 'لا يمكنك إعادة تعيين حساب آخر'}), 403
        
        with db.get_write_connection() as conn:
            # حذف المراكز النشطة (demo فقط)
            conn.execute("DELETE FROM active_positions WHERE user_id = %s AND is_demo = 1", (user_id,))
            
            # إعادة تعيين المحفظة (demo فقط)
            portfolio_row = conn.execute("""
                SELECT initial_balance FROM portfolio WHERE user_id = %s AND is_demo = 1 LIMIT 1
            """, (user_id,)).fetchone()
            initial_balance = float(portfolio_row[0] or 0.0) if portfolio_row else 0.0
            conn.execute("""
                UPDATE portfolio
                SET total_balance = %s,
                    available_balance = %s,
                    invested_balance = 0,
                    total_profit_loss = 0,
                    total_profit_loss_percentage = 0,
                    initial_balance = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND is_demo = 1
            """, (initial_balance, initial_balance, initial_balance, user_id))
            
            # حذف الإشعارات
            conn.execute("DELETE FROM notifications WHERE user_id = %s", (user_id,))
        
        logger.info(f"✅ إعادة تعيين بيانات الحساب للمستخدم {user_id}")
        return jsonify({
            'success': True,
            'message': 'تم إعادة تعيين بيانات الحساب بنجاح'
        })
    
    except Exception as e:
        logger.error(f"❌ خطأ في إعادة تعيين بيانات الحساب: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_bp.route('/health', methods=['GET'])
def health_check():
    """
    فحص صحة النظام - لا يحتاج مصادقة
    """
    try:
        db = get_db_manager()
        
        # فحص الاتصال بقاعدة البيانات
        with db.get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'database': 'connected',
            'timestamp': __import__('datetime').datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"❌ خطأ في فحص الصحة: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500


if __name__ == "__main__":
    print("🔧 System Endpoints جاهزة")
    print("المسارات المتاحة:")
    print("- GET /api/system/status")
    print("- POST /api/system/reset-account-data")
    print("- GET /api/system/health")
