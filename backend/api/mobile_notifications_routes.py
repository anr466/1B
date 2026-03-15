"""
Mobile Notifications Routes — extracted from mobile_endpoints.py (God Object split)
====================================================================================
Routes: /notifications, /notification-settings, /onboarding, /cache, /integration, /user/notifications
"""

from flask import request, jsonify, g
from datetime import datetime, timedelta
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

            # ✅ جلب الإشعارات من جدول notifications (الجدول الصحيح)
            notif_query = "SELECT id, user_id, title, message, COALESCE(type, 'general') as type, is_read, created_at, data FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?"
            result = db.execute_query(notif_query, (user_id, limit, offset))

            # ✅ جلب العدد الإجمالي
            count_query = "SELECT COUNT(*) as total FROM notifications WHERE user_id = ?"
            count_result = db.execute_query(count_query, (user_id,))
            total = count_result[0]['total'] if count_result else 0

            notifications = []
            if result:
                for notif in result:
                    notifications.append({
                        'id': notif['id'],
                        'user_id': notif['user_id'],
                        'title': notif['title'],
                        'message': notif['message'],
                        'type': notif['type'],
                        'is_read': bool(notif.get('is_read', False)),
                        'created_at': notif['created_at'],
                        'data': notif.get('data')
                    })

            return jsonify({'success': True, 'data': {
                'notifications': notifications, 'total': total,
                'unread': sum(1 for n in notifications if not n['is_read']),
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

            # تحديث جميع الإشعارات غير المقروءة إلى مقروءة في جدول notifications
            update_query = """
                UPDATE notifications 
                SET is_read = TRUE 
                WHERE user_id = ? AND is_read = FALSE
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

    # ==================== NOTIFICATION STATS (moved to unified endpoint below) ====================


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
                    "UPDATE notifications SET is_read = TRUE WHERE id = ? AND user_id = ?",
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
    def mark_all_notifications_read_put(user_id):
        """تحديد جميع الإشعارات كمقروءة"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()

            with db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE notifications SET is_read = TRUE WHERE user_id = ? AND is_read = FALSE",
                    (user_id,)
                )
                affected = cursor.rowcount
                conn.commit()

            logger.info(f"✅ تم تحديد {affected} إشعار كمقروء للمستخدم {user_id}")
            return jsonify({'success': True, 'message': f'تم تحديد {affected} إشعار كمقروء'})
        except Exception as e:
            logger.error(f"❌ خطأ mark all notifications read {user_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


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
                # تحكم المستخدم بالخسائر التراكمية اليومية + تقرير نهاية اليوم
                'cumulativeLossAlertEnabled': True,
                'cumulativeLossThresholdUsd': 100,
                'endOfDayReportEnabled': True,
                'endOfDayReportTime': '23:00',
            }

            # محاولة جلب الإعدادات من قاعدة البيانات
            try:
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT settings_data FROM user_notification_settings 
                        WHERE user_id = ?
                    """, (user_id,))
                    row = cursor.fetchone()
                    
                    if row and row[0]:
                        import json as _json
                        saved_settings = _json.loads(row[0])
                        default_settings.update(saved_settings)
            except Exception as db_error:
                logger.warning(f"فشل في جلب إعدادات الإشعارات من DB: {db_error}")

            return success_response(default_settings)

        except Exception as e:
            logger.error(f"❌ خطأ في جلب إعدادات الإشعارات: {e}")
            return error_response('خطأ في جلب إعدادات الإشعارات', 500)

    @bp.route('/notifications/settings', methods=['PUT'])
    @require_auth
    @rate_limit_general
    def update_user_notification_settings():
        """
        تحديث إعدادات الإشعارات للمستخدم الحالي
        """
        try:
            user_id = g.user_id
            body = request.get_json()

            if not body:
                return error_response('بيانات الإعدادات مطلوبة', 400)

            # Flutter wraps payload as {'settings': {...}} — unwrap if present
            settings = body.get('settings', body) if isinstance(body.get('settings'), dict) else body

            # يجب أن يحتوي الطلب على حقل معروف واحد على الأقل من إعدادات الإشعارات
            supported_fields = {
                'pushEnabled', 'tradeNotifications', 'priceAlerts', 'errorNotifications',
                'dailySummary', 'notifyNewDeal', 'notifyDealProfit', 'notifyDealLoss',
                'notifyDailyProfit', 'notifyDailyLoss', 'notifyLowBalance',
                'notifySecurityAlerts', 'notifySystemStatus', 'notifyMaintenance',
                'quietHoursEnabled', 'quietHoursStart', 'quietHoursEnd',
                'notifyLargeProfit', 'notifyLargeLoss', 'profitThreshold',
                'lossThreshold', 'weeklySummary', 'monthlyReport',
                'cumulativeLossAlertEnabled', 'cumulativeLossThresholdUsd',
                'endOfDayReportEnabled', 'endOfDayReportTime'
            }
            if not any(k in supported_fields for k in settings.keys()):
                return error_response('يجب تقديم حقل واحد على الأقل من إعدادات الإشعارات', 400)

            # التحقق من صحة الحدود المالية
            if 'profitThreshold' in settings and (settings['profitThreshold'] < 0 or settings['profitThreshold'] > 10000):
                return error_response('حد الربح يجب أن يكون بين 0 و 10000 دولار', 400)

            if 'lossThreshold' in settings and (settings['lossThreshold'] < 0 or settings['lossThreshold'] > 10000):
                return error_response('حد الخسارة يجب أن يكون بين 0 و 10000 دولار', 400)

            if (
                'cumulativeLossThresholdUsd' in settings
                and (
                    settings['cumulativeLossThresholdUsd'] < 0
                    or settings['cumulativeLossThresholdUsd'] > 100000
                )
            ):
                return error_response('حد الخسائر التراكمية يجب أن يكون بين 0 و 100000 دولار', 400)

            # التحقق من صحة أوقات الهدوء
            if settings.get('quietHoursEnabled'):
                if 'quietHoursStart' not in settings or 'quietHoursEnd' not in settings:
                    return error_response('أوقات الهدوء مطلوبة عند تفعيل الميزة', 400)

            if settings.get('endOfDayReportEnabled') and 'endOfDayReportTime' in settings:
                report_time = str(settings['endOfDayReportTime'])
                if len(report_time) != 5 or report_time[2] != ':':
                    return error_response('صيغة وقت تقرير نهاية اليوم يجب أن تكون HH:MM', 400)

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
                        ) VALUES (?, ?, CURRENT_TIMESTAMP)
                    """, (user_id, settings_json))

                    conn.commit()

                logger.info(f"✅ تم تحديث إعدادات الإشعارات للمستخدم {user_id}")
                return success_response(settings, 'تم تحديث الإعدادات بنجاح')

            except Exception as db_error:
                logger.error(f"❌ خطأ في حفظ الإعدادات: {db_error}")
                return error_response('خطأ في حفظ الإعدادات', 500)

        except Exception as e:
            logger.error(f"❌ خطأ في تحديث إعدادات الإشعارات: {e}")
            return error_response('خطأ في تحديث الإعدادات', 500)

    # ==================== NOTIFICATION STATS ====================

    @bp.route('/notifications/<int:user_id>/stats', methods=['GET'])
    @require_auth
    @rate_limit_data
    def get_notification_stats_endpoint(user_id):
        """جلب إحصائيات الإشعارات للمستخدم"""
        if not verify_user_access(user_id):
            response_data, status_code = error_response('Unauthorized access', 'UNAUTHORIZED', 403)
            return jsonify(response_data), status_code

        try:
            now = datetime.utcnow()
            notifications = db_manager.execute_query(
                """
                    SELECT COALESCE(type, 'general') as type, is_read, created_at, title
                    FROM notifications
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                """,
                (user_id,),
            ) or []

            total = len(notifications)
            unread = sum(1 for row in notifications if not bool(row.get('is_read')))
            read = total - unread

            last_7_days = 0
            last_24_hours = 0
            for row in notifications:
                created_at_raw = row.get('created_at')
                created_at = None
                if isinstance(created_at_raw, datetime):
                    created_at = created_at_raw
                elif created_at_raw:
                    created_at_str = str(created_at_raw).replace(' GMT', '')
                    for fmt in ('%a, %d %b %Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
                        try:
                            created_at = datetime.strptime(created_at_str, fmt)
                            break
                        except ValueError:
                            continue
                if created_at is None:
                    continue
                if created_at.tzinfo is not None:
                    created_at = created_at.astimezone().replace(tzinfo=None)
                if created_at >= now - timedelta(days=7):
                    last_7_days += 1
                if created_at >= now - timedelta(days=1):
                    last_24_hours += 1

            by_type = db_manager.execute_query(
                """
                    SELECT 
                        COALESCE(type, 'general') as type,
                        COUNT(*) as count
                    FROM notifications 
                    WHERE user_id = ?
                    GROUP BY type
                    ORDER BY count DESC
                """,
                (user_id,),
            ) or []

            last_result = db_manager.execute_query(
                """
                    SELECT title, created_at 
                    FROM notifications 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """,
                (user_id,),
            )
            last_notification = last_result[0] if last_result else None

            response_data, status_code = success_response({
                'total': total,
                'unread': unread,
                'read': read,
                'last_7_days': last_7_days,
                'last_24_hours': last_24_hours,
                'by_type': by_type,
                'last_notification': last_notification
            })
            return jsonify(response_data), status_code

        except Exception as e:
            logger.error(f"❌ خطأ في جلب إحصائيات الإشعارات {user_id}: {e}")
            response_data, status_code = error_response('خطأ في جلب الإحصائيات', 'NOTIFICATION_STATS_ERROR', 500)
            return jsonify(response_data), status_code

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
                        SELECT COUNT(*) FROM active_positions
                        WHERE user_id = ?
                        AND created_at >= (CURRENT_TIMESTAMP - INTERVAL '7 days')
                    """, (user_id,))
                    recent_trades = cursor.fetchone()[0]
                    integration_status['offline_ready'] = recent_trades > 0
            except Exception:
                pass

            return success_response(integration_status)

        except Exception as e:
            logger.error(f"❌ خطأ في جلب حالة التكامل: {e}")
            return error_response('خطأ في جلب حالة التكامل', 500)

    # ==================== NOTIFICATION CLEANUP ====================

    @bp.route('/notifications/cleanup', methods=['POST'])
    @require_auth
    @rate_limit_general
    def cleanup_notifications():
        """تنظيف الإشعارات القديمة بناءً على السياسة"""
        try:
            user_id = g.user_id
            
            # استدعاء خدمة التنظيف
            from backend.services.notification_cleanup_service import get_notification_cleanup_service
            cleanup_service = get_notification_cleanup_service()
            
            results = cleanup_service.cleanup_notifications(user_id)
            
            if 'error' in results:
                return error_response(results['error'], 500)
            
            logger.info(f"✅ تم تنظيف إشعارات المستخدم {user_id}: {results}")
            return success_response({
                'message': 'تم تنظيف الإشعارات بنجاح',
                'results': results
            })
            
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف الإشعارات: {e}")
            return error_response('خطأ في تنظيف الإشعارات', 500)

    @bp.route('/notifications/cleanup/stats', methods=['GET'])
    @require_auth
    @rate_limit_data
    def get_cleanup_stats():
        """الحصول على إحصائيات التنظيف"""
        try:
            user_id = g.user_id
            
            from backend.services.notification_cleanup_service import get_notification_cleanup_service
            cleanup_service = get_notification_cleanup_service()
            
            stats = cleanup_service.get_cleanup_stats()
            
            # فلترة الإحصائيات للمستخدم الحالي
            user_stats = {
                'total_notifications': stats.get('total_notifications', 0),
                'read_notifications': stats.get('read_notifications', 0),
                'unread_notifications': stats.get('unread_notifications', 0),
                'old_read_notifications': stats.get('old_read_notifications', 0),
                'old_unread_notifications': stats.get('old_unread_notifications', 0),
                'cleanup_policy': {
                    'read_retention_days': 7,
                    'unread_retention_days': 30,
                    'system_retention_days': 3,
                    'max_notifications': 1000
                }
            }
            
            return success_response(user_stats)
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إحصائيات التنظيف: {e}")
            return error_response('خطأ في جلب إحصائيات التنظيف', 500)

    @bp.route('/notifications/cleanup/admin', methods=['POST'])
    @require_auth
    @rate_limit_general
    def admin_cleanup_all_notifications():
        """تنظيف جميع الإشعارات (للأدمن فقط)"""
        try:
            # التحقق من صلاحيات الأدمن
            user_id = g.user_id
            user_data = db_manager.get_user_by_id(user_id)
            
            if not user_data or user_data.get('user_type') != 'admin':
                return error_response('غير مصرح بالوصول', 403)
            
            from backend.services.notification_cleanup_service import get_notification_cleanup_service
            cleanup_service = get_notification_cleanup_service()
            
            results = cleanup_service.cleanup_notifications()  # جميع المستخدمين
            
            if 'error' in results:
                return error_response(results['error'], 500)
            
            logger.info(f"✅ الأدمن {user_id} قام بتنظيف جميع الإشعارات: {results}")
            return success_response({
                'message': 'تم تنظيف جميع الإشعارات بنجاح',
                'results': results
            })
            
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف جميع الإشعارات: {e}")
            return error_response('خطأ في تنظيف جميع الإشعارات', 500)


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

            success = onboarding.dismiss_step(user_id, step)
            if not success:
                return jsonify({'success': False, 'error': 'dismiss_step_failed'}), 500

            return jsonify({'success': True, 'data': {'step': step, 'dismissed': True}})
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

                try:
                    cursor.execute("""
                        SELECT id, COALESCE(type, 'general') as type, title, message, data, priority,
                               CASE WHEN is_read THEN 'read' ELSE 'unread' END as status,
                               created_at, NULL as delivered_at
                        FROM notifications
                        WHERE user_id = ?
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?
                    """, (user_id, per_page, offset))
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    cursor.execute("""
                        SELECT id, COALESCE(type, 'general') as type, title, message, data, NULL as priority,
                               CASE WHEN is_read THEN 'read' ELSE 'unread' END as status,
                               created_at, NULL as delivered_at
                        FROM notifications
                        WHERE user_id = ?
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?
                    """, (user_id, per_page, offset))

                notifications = cursor.fetchall()

                cursor.execute("""
                    SELECT COUNT(*) FROM notifications WHERE user_id = ?
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
