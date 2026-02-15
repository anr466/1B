"""
Mobile Notifications Routes — extracted from mobile_endpoints.py (God Object split)
====================================================================================
Routes: /notifications, /notification-settings, /onboarding, /cache, /integration, /user/notifications
"""

from flask import request, jsonify, g
from datetime import datetime
from pydantic import ValidationError
import json
import logging

logger = logging.getLogger(__name__)


def register_mobile_notifications_routes(bp, shared):
    """Register notification-related routes on the mobile blueprint"""
    db_manager = shared['db_manager']
    verify_user_access = shared['verify_user_access']
    require_auth = shared['require_auth']
    rate_limit_general = shared.get('rate_limit_general', lambda f: f)
    rate_limit_data = shared.get('rate_limit_data', lambda f: f)
    success_response = shared['success_response']
    error_response = shared['error_response']
    require_idempotency = shared.get('require_idempotency', lambda *a: (lambda f: f))
    audit_logger = shared.get('audit_logger', None)

    # ==================== الإشعارات ====================

    @bp.route('/notifications/<int:user_id>', methods=['GET'])
    @require_auth
    def get_notifications(user_id):
        """الحصول على الإشعارات مع دعم Pagination"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()

            # ✅ دعم Pagination من التطبيق
            page = request.args.get('page', 1, type=int)
            limit = min(request.args.get('limit', 20, type=int), 100)
            offset = (page - 1) * limit

            # ✅ جلب الإشعارات مع Pagination
            notif_query = "SELECT id, title, message, COALESCE(notification_type, type, 'general') as type, status, created_at FROM notification_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?"
            result = db.execute_query(notif_query, (user_id, limit, offset))

            # ✅ جلب العدد الإجمالي
            count_query = "SELECT COUNT(*) as total FROM notification_history WHERE user_id = ?"
            count_result = db.execute_query(count_query, (user_id,))
            total = count_result[0]['total'] if count_result else 0

            notifications = []
            if result:
                for notif in result:
                    notifications.append({
                        'id': notif['id'], 'title': notif['title'], 'message': notif['message'],
                        'type': notif['type'], 'isRead': notif.get('status') == 'read', 'createdAt': notif['created_at']
                    })

            return jsonify({'success': True, 'data': {
                'notifications': notifications, 'total': total,
                'unread': sum(1 for n in notifications if not n['isRead']),
                'page': page, 'limit': limit
            }})
        except Exception as e:
            logger.error(f"❌ خطأ Notifications {user_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @bp.route('/notifications/<int:user_id>/mark-all-read', methods=['POST'])
    @require_auth
    @rate_limit_general
    def mark_all_notifications_read(user_id):
        """تحديد جميع الإشعارات كمقروءة للمستخدم"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()

            # تحديث جميع الإشعارات غير المقروءة إلى مقروءة
            update_query = """
                UPDATE notification_history 
                SET status = 'read' 
                WHERE user_id = ? AND status != 'read'
            """
            db.execute_query(update_query, (user_id,))
            
            logger.info(f"✅ تم تحديد جميع الإشعارات كمقروءة للمستخدم {user_id}")
            
            return jsonify({
                'success': True,
                'message': 'تم تحديد جميع الإشعارات كمقروءة'
            })
            
        except Exception as e:
            logger.error(f"❌ خطأ mark all read {user_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @bp.route('/notifications/stats/<int:user_id>', methods=['GET'])
    @require_auth
    @rate_limit_general
    def get_notification_stats(user_id):
        """إحصائيات الإشعارات لليوم الحالي"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()

            with db.get_connection() as conn:
                cursor = conn.cursor()

                # إجمالي الإشعارات اليوم
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM notification_history
                    WHERE user_id = ? AND DATE(created_at) = DATE('now')
                """, (user_id,))
                total = cursor.fetchone()[0] or 0

                # إشعارات الصفقات
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM notification_history
                    WHERE user_id = ? 
                    AND DATE(created_at) = DATE('now')
                    AND notification_type IN ('trade_opened', 'trade_closed', 'stop_loss_triggered', 'take_profit_reached')
                """, (user_id,))
                trades = cursor.fetchone()[0] or 0

                # التنبيهات
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM notification_history
                    WHERE user_id = ? 
                    AND DATE(created_at) = DATE('now')
                    AND notification_type IN ('price_alert', 'margin_call', 'low_balance', 'strategy_signal')
                """, (user_id,))
                alerts = cursor.fetchone()[0] or 0

                # الملخص اليومي
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM notification_history
                    WHERE user_id = ? 
                    AND DATE(created_at) = DATE('now')
                    AND notification_type = 'daily_summary'
                """, (user_id,))
                summary = cursor.fetchone()[0] or 0

            logger.info(f"✅ Notification Stats {user_id}: total={total}, trades={trades}, alerts={alerts}")
            return jsonify({
                'success': True,
                'stats': {
                    'total': total,
                    'trades': trades,
                    'alerts': alerts,
                    'summary': summary
                }
            })

        except Exception as e:
            logger.error(f"❌ خطأ Notification Stats {user_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @bp.route('/notifications/<int:notification_id>/read', methods=['PUT'])
    @require_auth
    def mark_notification_read(notification_id):
        """تحديد إشعار كمقروء — مع تحقق من ملكية المستخدم"""
        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()

            user_id = g.user_id

            with db.get_write_connection() as conn:
                cursor = conn.cursor()
                # ✅ SECURITY FIX: التحقق من أن الإشعار يخص المستخدم الحالي
                cursor.execute(
                    "UPDATE notification_history SET status = 'read' WHERE id = ? AND user_id = ?",
                    (notification_id, user_id)
                )
                if cursor.rowcount == 0:
                    return jsonify({'success': False, 'error': 'الإشعار غير موجود أو لا يخصك'}), 404
                conn.commit()

            return jsonify({'success': True, 'message': 'تم تحديد الإشعار كمقروء'})
        except Exception as e:
            logger.error(f"❌ خطأ mark notification read {notification_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @bp.route('/notifications/<int:user_id>/read-all', methods=['PUT'])
    @require_auth
    def mark_all_notifications_read(user_id):
        """تحديد جميع الإشعارات كمقروءة"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()

            with db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE notification_history SET status = 'read' WHERE user_id = ? AND status != 'read'",
                    (user_id,)
                )
                affected = cursor.rowcount
                conn.commit()

            logger.info(f"✅ تم تحديد {affected} إشعار كمقروء للمستخدم {user_id}")
            return jsonify({'success': True, 'message': f'تم تحديد {affected} إشعار كمقروء'})
        except Exception as e:
            logger.error(f"❌ خطأ mark all notifications read {user_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    def _get_notification_settings_impl(user_id):
        """جلب إعدادات الإشعارات (Implementation)"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()

            with db.get_connection() as conn:
                cursor = conn.cursor()

                # ✅ جلب من settings_data JSON (يتوافق مع schema الفعلي)
                import json as _json
                cursor.execute("SELECT settings_data FROM user_notification_settings WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()

                # القيم الافتراضية
                defaults = {
                    'tradeNotifications': True,
                    'priceAlerts': True,
                    'systemNotifications': True,
                    'marketingNotifications': False,
                    'pushEnabled': True,
                    'emailEnabled': True,
                    'smsEnabled': True,
                    'notifyNewDeal': True,
                    'notifyDealProfit': True,
                    'notifyDealLoss': True,
                    'notifyDailyProfit': True,
                    'notifyDailyLoss': True,
                    'notifyLowBalance': True
                }

                if row:
                    row_dict = dict(row)
                    sd = row_dict.get('settings_data')
                    if sd:
                        try:
                            saved = _json.loads(sd)
                            defaults.update(saved)
                        except (ValueError, TypeError):
                            pass

                return jsonify({'success': True, 'data': defaults})

        except Exception as e:
            logger.error(f"❌ خطأ في جلب إعدادات الإشعارات {user_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    def _update_notification_settings_impl(user_id):
        """تحديث إعدادات الإشعارات (Implementation) - يستخدم settings_data JSON"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        try:
            from database.database_manager import DatabaseManager
            import json as _json
            db = DatabaseManager()

            data = request.get_json()

            if not data:
                return jsonify({'success': False, 'error': 'لا توجد بيانات'}), 400

            # ✅ تخزين كـ JSON في settings_data (يتوافق مع schema الفعلي)
            settings_json = _json.dumps(data)

            with db.get_write_connection() as conn:
                existing = conn.execute(
                    "SELECT id FROM user_notification_settings WHERE user_id = ?", (user_id,)
                ).fetchone()

                if existing:
                    conn.execute(
                        "UPDATE user_notification_settings SET settings_data = ?, updated_at = datetime('now') WHERE user_id = ?",
                        (settings_json, user_id)
                    )
                else:
                    conn.execute(
                        "INSERT INTO user_notification_settings (user_id, settings_data, created_at, updated_at) VALUES (?, ?, datetime('now'), datetime('now'))",
                        (user_id, settings_json)
                    )

                conn.commit()

            logger.info(f"✅ تحديث إعدادات الإشعارات للمستخدم {user_id}")
            return jsonify({'success': True, 'message': 'تم تحديث الإعدادات بنجاح'})

        except Exception as e:
            logger.error(f"❌ خطأ في تحديث إعدادات الإشعارات {user_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @bp.route('/notification-settings/<int:user_id>', methods=['GET', 'PUT'])
    @require_auth
    def handle_notification_settings(user_id):
        """إدارة إعدادات الإشعارات (GET/PUT)"""
        if request.method == 'GET':
            return _get_notification_settings_impl(user_id)
        elif request.method == 'PUT':
            return _update_notification_settings_impl(user_id)


    # ═══════════════════════════════════════════════════════════════

    # ============================================
    # 📈 Portfolio API - تم حذف الـ route المكرر
    # ✅ Route الصحيح موجود في سطر 236 (get_user_portfolio)
    # ❌ كان هذا الـ route يتجاوز الأصلي لأن Flask يسجل آخر route مكرر
    # ============================================
    # 🔔 USER NOTIFICATION SETTINGS APIs
    # ============================================================================

    @bp.route('/notifications/settings', methods=['GET'])
    @require_auth
    @rate_limit_data
    def get_user_notification_settings():
        """
        جلب إعدادات الإشعارات للمستخدم الحالي
        """
        try:
            user_id = g.user_id

            # إعدادات افتراضية شاملة
            default_settings = {
                'pushEnabled': True,
                'tradeNotifications': True,
                'priceAlerts': True,
                'errorNotifications': True,
                'dailySummary': True,

                # إعدادات تفصيلية
                'notifyNewDeal': True,
                'notifyDealProfit': True,
                'notifyDealLoss': True,
                'notifyDailyProfit': True,
                'notifyDailyLoss': True,
                'notifyLowBalance': True,

                # إعدادات متقدمة
                'notifySecurityAlerts': True,
                'notifySystemStatus': False,
                'notifyMaintenance': False,
                'quietHoursEnabled': False,
                'quietHoursStart': '22:00',
                'quietHoursEnd': '08:00',
                'notifyLargeProfit': True,
                'notifyLargeLoss': True,
                'profitThreshold': 50,
                'lossThreshold': 25,
                'weeklySummary': True,
                'monthlyReport': True,
            }

            # محاولة جلب الإعدادات من قاعدة البيانات
            try:
                with db_manager.get_connection() as conn:
                    cursor = conn.execute("""
                        SELECT settings_data, updated_at
                        FROM user_notification_settings
                        WHERE user_id = ?
                        ORDER BY updated_at DESC
                        LIMIT 1
                    """, (user_id,))

                    row = cursor.fetchone()
                    if row:
                        settings_data, updated_at = row
                        try:
                            import json as _json
                            saved_settings = _json.loads(settings_data) if isinstance(settings_data, str) else settings_data
                            # دمج الإعدادات المحفوظة مع الافتراضية
                            default_settings.update(saved_settings)
                        except Exception as parse_error:
                            logger.warning(f"فشل في تحليل إعدادات المستخدم {user_id}: {parse_error}")
                            # نستمر مع الإعدادات الافتراضية
            except Exception as db_error:
                logger.warning(f"فشل في جلب إعدادات الإشعارات من قاعدة البيانات للمستخدم {user_id}: {db_error}")
                # نستمر مع الإعدادات الافتراضية

            return success_response({
                'settings': default_settings,
                'lastUpdated': datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"❌ خطأ في جلب إعدادات الإشعارات: {e}")
            return error_response('خطأ في جلب إعدادات الإشعارات', 500)

    @bp.route('/notifications/settings', methods=['PUT'])
    @require_auth
    @rate_limit_data
    @require_idempotency('update_notification_settings')
    def update_user_notification_settings():
        """تحديث إعدادات الإشعارات للمستخدم الحالي"""
        try:
            user_id = g.user_id
            data = request.get_json()

            if not data or 'settings' not in data:
                return error_response('بيانات الإعدادات مطلوبة', 400)

            settings = data['settings']

            # التحقق من صحة البيانات الأساسية
            required_fields = ['pushEnabled', 'tradeNotifications', 'priceAlerts']
            for field in required_fields:
                if field not in settings:
                    return error_response(f'الحقل {field} مطلوب', 400)

            # التحقق من صحة الحدود المالية
            if 'profitThreshold' in settings and (settings['profitThreshold'] < 0 or settings['profitThreshold'] > 10000):
                return error_response('حد الربح يجب أن يكون بين 0 و 10000 دولار', 400)

            if 'lossThreshold' in settings and (settings['lossThreshold'] < 0 or settings['lossThreshold'] > 10000):
                return error_response('حد الخسارة يجب أن يكون بين 0 و 10000 دولار', 400)

            # التحقق من صحة أوقات الهدوء
            if settings.get('quietHoursEnabled'):
                if 'quietHoursStart' not in settings or 'quietHoursEnd' not in settings:
                    return error_response('أوقات الهدوء مطلوبة عند تفعيل الميزة', 400)

            # حفظ الإعدادات في قاعدة البيانات
            try:
                import json as _json
                with db_manager.get_write_connection() as conn:
                    # تحويل الإعدادات إلى JSON
                    settings_json = _json.dumps(settings, ensure_ascii=False)

                    # حذف الإعدادات السابقة
                    conn.execute("""
                        DELETE FROM user_notification_settings
                        WHERE user_id = ?
                    """, (user_id,))

                    # إدراج الإعدادات الجديدة
                    conn.execute("""
                        INSERT INTO user_notification_settings (
                            user_id, settings_data, updated_at
                        ) VALUES (?, ?, datetime('now'))
                    """, (user_id, settings_json))

                    # تسجيل في audit log
                    if audit_logger:
                        audit_logger.log(
                            action='update_notification_settings',
                            user_id=user_id,
                            details={
                                'settings_count': len(settings),
                                'has_quiet_hours': settings.get('quietHoursEnabled', False),
                                'has_thresholds': 'profitThreshold' in settings
                            }
                        )

            except Exception as db_error:
                logger.error(f"فشل في حفظ إعدادات الإشعارات للمستخدم {user_id}: {db_error}")
                return error_response('فشل في حفظ الإعدادات', 500)

            # إبطال الـ cache
            try:
                if hasattr(g, 'cache_invalidator'):
                    g.cache_invalidator.invalidate_cache(f'user_notifications_{user_id}')
            except Exception as cache_error:
                logger.warning(f"فشل في إبطال الـ cache: {cache_error}")

            return success_response({
                'message': 'تم حفظ إعدادات الإشعارات بنجاح',
                'settings': settings,
                'updatedAt': datetime.now().isoformat()
            })

        except ValidationError as e:
            return error_response(str(e), 400)
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث إعدادات الإشعارات: {e}")
            return error_response('خطأ في تحديث الإعدادات', 500)

    # ============================================================================
    # 📊 CACHE & OFFLINE SUPPORT APIs
    # ============================================================================

    @bp.route('/cache/status', methods=['GET'])
    @require_auth
    def get_cache_status():
        """جلب حالة الـ cache للمستخدم"""
        try:
            user_id = g.user_id

            cache_info = {
                'user_id': user_id,
                'cache_keys': [],
                'total_size': 0,
                'last_updated': None
            }

            # محاولة جلب معلومات الـ cache
            try:
                if hasattr(g, 'cache_invalidator'):
                    cache_info.update(g.cache_invalidator.get_user_cache_info(user_id))
            except Exception as cache_error:
                logger.warning(f"فشل في جلب معلومات الـ cache: {cache_error}")

            return success_response(cache_info)

        except Exception as e:
            logger.error(f"❌ خطأ في جلب حالة الـ cache: {e}")
            return error_response('خطأ في جلب حالة الـ cache', 500)

    @bp.route('/cache/clear', methods=['POST'])
    @require_auth
    @rate_limit_data
    def clear_user_cache():
        """مسح cache المستخدم"""
        try:
            user_id = g.user_id

            cleared_keys = []
            try:
                if hasattr(g, 'cache_invalidator'):
                    cleared_keys = g.cache_invalidator.clear_user_cache(user_id)
            except Exception as cache_error:
                logger.warning(f"فشل في مسح الـ cache: {cache_error}")

            # تسجيل في audit log
            if audit_logger:
                audit_logger.log(
                    action='clear_cache',
                    user_id=user_id,
                    details={'cleared_keys': len(cleared_keys)}
                )

            return success_response({
                'message': 'تم مسح الـ cache بنجاح',
                'cleared_keys': len(cleared_keys)
            })

        except Exception as e:
            logger.error(f"❌ خطأ في مسح الـ cache: {e}")
            return error_response('خطأ في مسح الـ cache', 500)

    # ============================================================================
    # 🔄 SYSTEM INTEGRATION APIs
    # ============================================================================

    @bp.route('/integration/status', methods=['GET'])
    @require_auth
    def get_integration_status():
        """جلب حالة التكامل مع النظام"""
        try:
            user_id = g.user_id

            integration_status = {
                'user_authenticated': True,
                'database_connected': True,
                'cache_working': False,
                'notifications_configured': False,
                'offline_ready': False,
                'last_check': datetime.now().isoformat()
            }

            # فحص حالة الـ cache
            try:
                if hasattr(g, 'cache_invalidator'):
                    integration_status['cache_working'] = True
            except Exception:
                pass

            # فحص إعدادات الإشعارات
            try:
                with db_manager.get_connection() as conn:
                    cursor = conn.execute("""
                        SELECT COUNT(*) FROM user_notification_settings
                        WHERE user_id = ?
                    """, (user_id,))
                    count = cursor.fetchone()[0]
                    integration_status['notifications_configured'] = count > 0
            except Exception:
                pass

            # فحص الجاهزية للعمل دون اتصال
            try:
                with db_manager.get_connection() as conn:
                    cursor = conn.execute("""
                        SELECT COUNT(*) FROM user_trades
                        WHERE user_id = ? AND created_at >= datetime('now', '-7 days')
                    """, (user_id,))
                    recent_trades = cursor.fetchone()[0]
                    integration_status['offline_ready'] = recent_trades > 0
            except Exception:
                pass

            return success_response(integration_status)

        except Exception as e:
            logger.error(f"❌ خطأ في جلب حالة التكامل: {e}")
            return error_response('خطأ في جلب حالة التكامل', 500)


    # ═══════════════════════════════════════════════════════════════
    #                    نظام توجيه المستخدم
    # ═══════════════════════════════════════════════════════════════

    @bp.route('/onboarding/status/<int:user_id>', methods=['GET'])
    @require_auth
    def get_onboarding_status(user_id):
        """جلب حالة توجيه المستخدم وتقدمه"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        try:
            from backend.services.user_onboarding_service import get_onboarding_service
            onboarding = get_onboarding_service()

            progress = onboarding.get_user_progress(user_id)

            return jsonify({
                'success': True,
                'data': progress
            })
        except Exception as e:
            logger.error(f"خطأ في جلب حالة التوجيه: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @bp.route('/onboarding/next-step/<int:user_id>', methods=['GET'])
    @require_auth
    def get_next_onboarding_step(user_id):
        """جلب الخطوة التالية للمستخدم (تظهر مرة واحدة فقط)"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        try:
            from backend.services.user_onboarding_service import get_onboarding_service
            onboarding = get_onboarding_service()

            next_step = onboarding.get_next_step(user_id)

            # إذا وجدت خطوة، سجّل أنها عُرضت
            if next_step:
                onboarding.mark_step_shown(user_id, next_step['step'])

            return jsonify({
                'success': True,
                'data': next_step  # None إذا لا توجد خطوات
            })
        except Exception as e:
            logger.error(f"خطأ في جلب الخطوة التالية: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @bp.route('/onboarding/dismiss/<int:user_id>', methods=['POST'])
    @require_auth
    def dismiss_onboarding_step(user_id):
        """تجاهل خطوة التوجيه (المستخدم أغلقها)"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        try:
            data = request.get_json() or {}
            step = data.get('step')

            if not step:
                return jsonify({'success': False, 'error': 'step مطلوب'}), 400

            from backend.services.user_onboarding_service import get_onboarding_service
            onboarding = get_onboarding_service()

            onboarding.dismiss_step(user_id, step)

            return jsonify({'success': True})
        except Exception as e:
            logger.error(f"خطأ في تجاهل الخطوة: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    # =========================================================================
    # 📬 NOTIFICATIONS APIs
    # =========================================================================

    @bp.route('/notifications-list', methods=['GET'])
    @require_auth
    def get_user_notifications():
        """جلب إشعارات المستخدم مع pagination"""
        try:
            user_id = g.user_id

            # معالجة pagination parameters
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 20))
            offset = (page - 1) * per_page

            with db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # جلب الإشعارات
                cursor.execute("""
                    SELECT id, COALESCE(notification_type, type, 'general') as type, title, message, data, priority, status, created_at, delivered_at
                    FROM notification_history
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (user_id, per_page, offset))

                notifications = cursor.fetchall()

                # جلب العدد الإجمالي
                cursor.execute("""
                    SELECT COUNT(*) FROM notification_history WHERE user_id = ?
                """, (user_id,))

                total_count = cursor.fetchone()[0]

                # تحويل النتائج إلى تنسيق JSON
                notifications_list = []
                for notification in notifications:
                    notifications_list.append({
                        'id': notification[0],
                        'type': notification[1],
                        'title': notification[2],
                        'message': notification[3],
                        'data': json.loads(notification[4]) if notification[4] else None,
                        'priority': notification[5],
                        'status': notification[6],
                        'created_at': notification[7],
                        'delivered_at': notification[8]
                    })

                return jsonify({
                    'success': True,
                    'notifications': notifications_list,
                    'total': total_count,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total_count + per_page - 1) // per_page
                })

        except Exception as e:
            logger.error(f"❌ خطأ في جلب الإشعارات للمستخدم {g.user_id}: {e}")
            return jsonify({'success': False, 'error': 'خطأ في جلب الإشعارات'}), 500
