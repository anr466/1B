#!/usr/bin/env python3
"""
Admin Users Management Routes — extracted from admin_unified_api.py (God Object split)
======================================================================================
Routes: users/all, users/<id> (GET detail), users/create, users/<id>/update, users/<id>/delete
"""

from flask import request, jsonify

from config.logging_config import get_logger
from database.database_manager import DatabaseManager
from backend.utils.password_utils import hash_password as _hash_pw

logger = get_logger(__name__)


def register_admin_users_routes(bp, shared):
    """Register all user management routes on the admin blueprint."""
    require_admin = shared['require_admin']
    audit_logger = shared['audit_logger']

    @bp.route('/users/all', methods=['GET'])
    @require_admin
    def get_all_users_with_stats():
        """جلب جميع المستخدمين مع إحصائياتهم"""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT
                        id, username, email, name, phone_number,
                        user_type, is_active, created_at, last_login_at,
                        (SELECT COUNT(*) FROM user_trades WHERE user_id = users.id) as total_trades,
                        (SELECT COUNT(*) FROM user_trades WHERE user_id = users.id AND status = 'closed' AND profit_loss > 0) as winning_trades
                    FROM users
                    ORDER BY created_at DESC
                    LIMIT 50
                """)

                users = []
                for row in cursor.fetchall():
                    user_id, username, email, full_name, phone, user_type, is_active, created_at, last_login, total_trades, winning_trades = row
                    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

                    users.append({
                        'id': user_id,
                        'username': username,
                        'email': email,
                        'full_name': full_name,
                        'phone': phone,
                        'user_type': user_type,
                        'is_active': bool(is_active),
                        'created_at': created_at,
                        'last_login': last_login,
                        'total_trades': total_trades,
                        'winning_trades': winning_trades,
                        'win_rate': round(win_rate, 1)
                    })

                total_users = len(users)
                active_users = len([u for u in users if u['is_active']])
                admin_users = len([u for u in users if u['user_type'] == 'admin'])

                stats = {
                    'total_users': total_users,
                    'active_users': active_users,
                    'inactive_users': total_users - active_users,
                    'admin_users': admin_users,
                    'regular_users': total_users - admin_users
                }

                return jsonify({
                    'success': True,
                    'data': {'users': users, 'stats': stats}
                })

        except Exception as e:
            logger.error(f"خطأ في جلب المستخدمين: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/users/<int:user_id>', methods=['GET'])
    @require_admin
    def get_user_details(user_id):
        """جلب تفاصيل مستخدم معين"""
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT
                        id, username, email, full_name, phone,
                        user_type, is_active, created_at, last_login
                    FROM users
                    WHERE id = ?
                """, (user_id,))

                row = cursor.fetchone()
                if not row:
                    return jsonify({'success': False, 'error': 'المستخدم غير موجود'}), 404

                user_id, username, email, full_name, phone, user_type, is_active, created_at, last_login = row

                return jsonify({
                    'success': True,
                    'data': {
                        'id': user_id, 'username': username, 'email': email,
                        'full_name': full_name, 'phone': phone,
                        'user_type': user_type, 'is_active': bool(is_active),
                        'created_at': created_at, 'last_login': last_login
                    }
                })

        except Exception as e:
            logger.error(f"خطأ في جلب تفاصيل المستخدم: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/users/create', methods=['POST'])
    @require_admin
    def create_user():
        """إنشاء مستخدم جديد"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'بيانات مطلوبة'}), 400

            required_fields = ['username', 'email', 'password', 'user_type']
            for field in required_fields:
                if field not in data:
                    return jsonify({'success': False, 'error': f'الحقل {field} مطلوب'}), 400

            if data['user_type'] not in ['admin', 'regular']:
                return jsonify({'success': False, 'error': 'نوع المستخدم غير صحيح'}), 400

            db = DatabaseManager()
            with db.get_write_connection() as conn:
                cursor = conn.execute("""
                    SELECT id FROM users
                    WHERE username = ? OR email = ?
                """, (data['username'], data['email']))

                if cursor.fetchone():
                    return jsonify({'success': False, 'error': 'الاسم أو الإيميل موجود بالفعل'}), 409

                cursor = conn.execute("""
                    INSERT INTO users (
                        username, email, password_hash, name, phone_number,
                        user_type, is_active, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'))
                """, (
                    data['username'],
                    data['email'],
                    _hash_pw(data['password']),
                    data.get('full_name', data.get('name', '')),
                    data.get('phone', data.get('phone_number', '')),
                    data['user_type']
                ))

                user_id = cursor.lastrowid

                if audit_logger:
                    audit_logger.log(
                        action='create_user',
                        user_id=user_id,
                        details={
                            'username': data['username'],
                            'email': data['email'],
                            'user_type': data['user_type']
                        }
                    )

                return jsonify({
                    'success': True,
                    'data': {
                        'user_id': user_id,
                        'username': data['username'],
                        'email': data['email'],
                        'user_type': data['user_type']
                    }
                })

        except Exception as e:
            logger.error(f"خطأ في إنشاء المستخدم: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/users/<int:user_id>/update', methods=['PUT'])
    @require_admin
    def update_user(user_id):
        """تحديث بيانات المستخدم"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'بيانات مطلوبة'}), 400

            db = DatabaseManager()
            with db.get_write_connection() as conn:
                cursor = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,))
                if not cursor.fetchone():
                    return jsonify({'success': False, 'error': 'المستخدم غير موجود'}), 404

                if 'user_type' in data and data['user_type'] not in ['admin', 'regular']:
                    return jsonify({'success': False, 'error': 'نوع المستخدم غير صحيح'}), 400

                update_fields = []
                update_values = []

                allowed_fields = ['username', 'email', 'full_name', 'phone', 'user_type', 'is_active']
                for field in allowed_fields:
                    if field in data:
                        update_fields.append(f"{field} = ?")
                        update_values.append(data[field])

                if not update_fields:
                    return jsonify({'success': False, 'error': 'لا توجد حقول للتحديث'}), 400

                update_values.append(user_id)
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"

                conn.execute(query, update_values)

                if audit_logger:
                    audit_logger.log(
                        action='update_user',
                        user_id=user_id,
                        details=data
                    )

                return jsonify({'success': True, 'message': 'تم تحديث المستخدم بنجاح'})

        except Exception as e:
            logger.error(f"خطأ في تحديث المستخدم: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/users/<int:user_id>/delete', methods=['DELETE'])
    @require_admin
    def delete_user(user_id):
        """حذف مستخدم (تعطيل بدلاً من الحذف الكامل)"""
        try:
            db = DatabaseManager()
            with db.get_write_connection() as conn:
                conn.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))

                if audit_logger:
                    audit_logger.log(
                        action='deactivate_user',
                        user_id=user_id,
                        details={'action': 'deactivated'}
                    )

                return jsonify({'success': True, 'message': 'تم تعطيل المستخدم بنجاح'})

        except Exception as e:
            logger.error(f"خطأ في حذف المستخدم: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
