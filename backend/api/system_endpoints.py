"""
System Endpoints - نقاط نهاية النظام العامة
"""

from flask import Blueprint, jsonify, request
from config.logging_config import get_logger
from backend.api.auth_middleware import require_auth

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
        from database.database_manager import DatabaseManager
        db = DatabaseManager()
        
        # الحصول على حالة النظام من قاعدة البيانات
        with db.get_connection() as conn:
            # جلب الأعمدة الفعلية الموجودة في جدول system_status
            system_status = conn.execute("""
                SELECT status, last_update, is_running, total_users, active_trades, total_trades
                FROM system_status
                WHERE id = 1
            """).fetchone()
            
            if system_status:
                return jsonify({
                    'success': True,
                    'data': {
                        'status': system_status[0] or 'online',
                        'lastUpdate': system_status[1],
                        'tradingActive': bool(system_status[2]),
                        'totalUsers': system_status[3] or 0,
                        'activeTrades': system_status[4] or 0,
                        'totalTrades': system_status[5] or 0,
                        'serverStatus': 'online'
                    }
                })
            else:
                # إذا لم يكن هناك سجل، نعيد قيم افتراضية
                return jsonify({
                    'success': True,
                    'data': {
                        'status': 'online',
                        'lastUpdate': None,
                        'tradingActive': False,
                        'totalUsers': 0,
                        'activeTrades': 0,
                        'totalTrades': 0,
                        'serverStatus': 'online'
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
        from ..database.database_manager import DatabaseManager
        import os
        jwt_secret = os.getenv('JWT_SECRET_KEY')
        if not jwt_secret:
            return jsonify({'success': False, 'error': 'Server configuration error'}), 500
        from ..utils.jwt_manager import JWTManager
        
        db = DatabaseManager()
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
            # حذف الصفقات (demo فقط)
            conn.execute("DELETE FROM user_trades WHERE user_id = ? AND is_demo = 1", (user_id,))
            
            # حذف المراكز النشطة (demo فقط)
            conn.execute("DELETE FROM active_positions WHERE user_id = ? AND is_demo = 1", (user_id,))
            
            # إعادة تعيين المحفظة (demo فقط)
            conn.execute("""
                UPDATE portfolio
                SET total_balance = 1000.0,
                    available_balance = 1000.0,
                    invested_balance = 0,
                    total_profit_loss = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND is_demo = 1
            """, (user_id,))
            
            # حذف الإشعارات
            conn.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
        
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
        from database.database_manager import DatabaseManager
        db = DatabaseManager()
        
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
