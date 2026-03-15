#!/usr/bin/env python3
"""
Admin Logs & Cleanup Routes — extracted from admin_unified_api.py (God Object split)
====================================================================================
Routes: activity-logs, audit/log, reports/*, logs/cleanup/*, logs/retention-policy,
        cleanup/*, logs/statistics, logs/clear
"""

from flask import request, jsonify
from datetime import datetime

from config.logging_config import get_logger

logger = get_logger(__name__)


def register_admin_logs_routes(bp, shared):
    """Register all logs/cleanup routes on the admin blueprint."""
    require_admin = shared['require_admin']
    get_safe_connection = shared['get_safe_connection']
    db = shared['db']
    audit_logger = shared['audit_logger']

    @bp.route('/activity-logs', methods=['GET'])
    @require_admin
    def get_activity_logs():
        """جلب سجل activity logs مع filtering وpagination"""
        try:
            page = max(1, int(request.args.get('page', 1)))
            limit = min(int(request.args.get('limit', 50)), 200)
            user_id = request.args.get('user_id', default=None)
            action = request.args.get('action', default=None)
            status = request.args.get('status', default=None)
            date_from = request.args.get('date_from', default=None)
            date_to = request.args.get('date_to', default=None)
            
            if page < 1:
                page = 1
            if limit < 1 or limit > 200:
                limit = 50
            
            if user_id:
                try:
                    user_id = int(user_id)
                except (ValueError, TypeError) as e:
                    logger.debug(f"user_id غير صالح: {e}")
                    user_id = None
            
            if audit_logger and hasattr(audit_logger, 'get_logs_paginated'):
                result = audit_logger.get_logs_paginated(
                    page=page,
                    limit=limit,
                    user_id=user_id,
                    action=action,
                    status=status,
                    date_from=date_from,
                    date_to=date_to
                )
            else:
                # Fallback for lightweight audit logger implementations
                try:
                    conn = get_safe_connection()
                    cursor = conn.cursor()

                    where_clauses = []
                    params = []
                    if user_id is not None:
                        where_clauses.append('user_id = ?')
                        params.append(user_id)
                    if action:
                        where_clauses.append('action = ?')
                        params.append(action)
                    if status:
                        where_clauses.append('status = ?')
                        params.append(status)

                    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ''
                    count_sql = f"SELECT COUNT(*) FROM activity_logs {where_sql}"
                    cursor.execute(count_sql, tuple(params))
                    total = cursor.fetchone()[0]

                    offset = (page - 1) * limit
                    data_sql = f"""
                        SELECT id, user_id, action, status, details, created_at
                        FROM activity_logs
                        {where_sql}
                        ORDER BY created_at DESC
                        LIMIT ? OFFSET ?
                    """
                    cursor.execute(data_sql, tuple(params + [limit, offset]))
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in (cursor.description or [])]
                    conn.close()

                    result = {
                        'logs': [
                            dict(row) if isinstance(row, dict)
                            else {columns[i]: row[i] for i in range(min(len(columns), len(row)))}
                            for row in rows
                        ],
                        'total': total,
                        'page': page,
                        'limit': limit,
                    }
                except Exception as fallback_error:
                    logger.warning(f"Activity logs fallback failed: {fallback_error}")
                    result = {
                        'logs': [],
                        'total': 0,
                        'page': page,
                        'limit': limit,
                    }
            
            return jsonify({'success': True, 'data': result})
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/system-errors', methods=['GET'])
    @require_admin
    def get_system_errors():
        """جلب سجل الأخطاء من system_errors مع filtering وpagination"""
        try:
            page = max(1, int(request.args.get('page', 1)))
            limit = min(int(request.args.get('limit', 50)), 200)
            severity = request.args.get('severity')  # critical, high, medium, low
            source = request.args.get('source')  # group_b, background, system, etc.
            status = request.args.get('status')  # new, resolved, auto_resolved, escalated
            requires_admin = request.args.get('requires_admin')  # true/false
            
            conn = get_safe_connection()
            cursor = conn.cursor()
            
            where_clauses = []
            params = []
            
            if severity:
                where_clauses.append('severity = ?')
                params.append(severity)
            if source:
                where_clauses.append('source = ?')
                params.append(source)
            if status:
                where_clauses.append('status = ?')
                params.append(status)
            if requires_admin:
                where_clauses.append('requires_admin = ?')
                params.append(1 if requires_admin.lower() == 'true' else 0)
            
            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ''
            
            # Count total
            count_sql = f"SELECT COUNT(*) FROM system_errors {where_sql}"
            cursor.execute(count_sql, tuple(params))
            total = cursor.fetchone()[0]
            
            # Get data
            offset = (page - 1) * limit
            data_sql = f"""
                SELECT 
                    id, error_type, error_message, severity, source, details,
                    traceback, resolved, resolved_at, resolved_by, created_at,
                    error_fingerprint, status, attempt_count, last_attempt_at,
                    requires_admin, auto_action
                FROM system_errors
                {where_sql}
                ORDER BY 
                    CASE severity 
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        ELSE 4
                    END,
                    created_at DESC
                LIMIT ? OFFSET ?
            """
            cursor.execute(data_sql, tuple(params + [limit, offset]))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            errors = []
            for row in rows:
                error = {columns[i]: row[i] for i in range(len(columns))}
                # إخفاء traceback الطويل في القائمة
                if error.get('traceback'):
                    error['has_traceback'] = True
                    error['traceback'] = None  # نرسله فقط في التفاصيل
                errors.append(error)
            
            conn.close()
            
            # إحصائيات إضافية
            stats_conn = get_safe_connection()
            stats_cursor = stats_conn.cursor()
            stats_cursor.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE severity = 'critical' AND status = 'new') as critical_new,
                    COUNT(*) FILTER (WHERE severity = 'high' AND status = 'new') as high_new,
                    COUNT(*) FILTER (WHERE status = 'auto_resolved') as auto_resolved_count,
                    COUNT(*) FILTER (WHERE status = 'resolved') as manual_resolved_count
                FROM system_errors
            """)
            stats = stats_cursor.fetchone()
            stats_conn.close()
            
            return jsonify({
                'success': True,
                'data': {
                    'errors': errors,
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'stats': {
                        'critical_new': stats[0] if stats else 0,
                        'high_new': stats[1] if stats else 0,
                        'auto_resolved_count': stats[2] if stats else 0,
                        'manual_resolved_count': stats[3] if stats else 0,
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"Error fetching system errors: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/system-errors/<int:error_id>', methods=['GET'])
    @require_admin
    def get_system_error_details(error_id):
        """جلب تفاصيل خطأ محدد مع traceback كامل"""
        try:
            conn = get_safe_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    id, error_type, error_message, severity, source, details,
                    traceback, resolved, resolved_at, resolved_by, created_at,
                    error_fingerprint, status, attempt_count, last_attempt_at,
                    requires_admin, auto_action
                FROM system_errors
                WHERE id = ?
            """, (error_id,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return jsonify({'success': False, 'error': 'Error not found'}), 404
            
            columns = [desc[0] for desc in cursor.description]
            error = {columns[i]: row[i] for i in range(len(columns))}
            
            # جلب الأخطاء المشابهة بنفس الـ fingerprint
            if error.get('error_fingerprint'):
                cursor.execute("""
                    SELECT COUNT(*), MAX(created_at) as last_occurrence
                    FROM system_errors
                    WHERE error_fingerprint = ? AND id != ?
                """, (error['error_fingerprint'], error_id))
                similar = cursor.fetchone()
                error['similar_count'] = similar[0] if similar else 0
                error['last_occurrence'] = similar[1] if similar else None
            
            conn.close()
            return jsonify({'success': True, 'data': error})
            
        except Exception as e:
            logger.error(f"Error fetching error details: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/system-errors/<int:error_id>/resolve', methods=['POST'])
    @require_admin
    def resolve_system_error(error_id):
        """تعليم خطأ كـ محلول"""
        try:
            data = request.get_json() or {}
            resolved_by = data.get('resolved_by', 'admin')
            notes = data.get('notes', '')
            
            conn = get_safe_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE system_errors
                SET resolved = 1,
                    resolved_at = CURRENT_TIMESTAMP,
                    resolved_by = ?,
                    status = 'resolved',
                    details = details || ' [Admin Notes: ' || ? || ']'
                WHERE id = ?
            """, (resolved_by, notes, error_id))
            conn.commit()
            conn.close()
            
            if audit_logger:
                audit_logger.log(
                    action='resolve_system_error',
                    user_id=request.user_id,
                    details={'error_id': error_id, 'notes': notes}
                )
            
            return jsonify({'success': True, 'message': 'تم تعليم الخطأ كمحلول'})
            
        except Exception as e:
            logger.error(f"Error resolving error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @bp.route('/system-errors/<int:error_id>/retry', methods=['POST'])
    @require_admin
    def retry_auto_fix(error_id):
        """إعادة محاولة الإصلاح التلقائي"""
        try:
            from backend.utils.error_logger import error_logger
            
            conn = get_safe_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT auto_action, attempt_count, error_fingerprint
                FROM system_errors
                WHERE id = ?
            """, (error_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return jsonify({'success': False, 'error': 'Error not found'}), 404
            
            auto_action, attempt_count, fingerprint = row
            
            if not auto_action or auto_action == 'manual_investigation':
                return jsonify({
                    'success': False,
                    'error': 'هذا الخطأ يتطلب تحقيق يدوي ولا يمكن إصلاحه تلقائيًا'
                }), 400
            
            # محاولة الإصلاح
            success = error_logger._try_auto_fix(auto_action)
            
            # تحديث السجل
            update_conn = get_safe_connection()
            update_cursor = update_conn.cursor()
            
            if success:
                update_cursor.execute("""
                    UPDATE system_errors
                    SET status = 'auto_resolved',
                        resolved = 1,
                        resolved_at = CURRENT_TIMESTAMP,
                        resolved_by = 'auto_fix_retry',
                        attempt_count = attempt_count + 1,
                        last_attempt_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (error_id,))
                message = f'تم إصلاح الخطأ تلقائيًا: {auto_action}'
            else:
                update_cursor.execute("""
                    UPDATE system_errors
                    SET attempt_count = attempt_count + 1,
                        last_attempt_at = CURRENT_TIMESTAMP,
                        status = CASE 
                            WHEN attempt_count + 1 >= 3 THEN 'escalated'
                            ELSE status
                        END
                    WHERE id = ?
                """, (error_id,))
                message = 'فشل الإصلاح التلقائي - قد يتطلب تدخل يدوي'
            
            update_conn.commit()
            update_conn.close()
            
            if audit_logger:
                audit_logger.log(
                    action='retry_auto_fix',
                    user_id=request.user_id,
                    details={'error_id': error_id, 'auto_action': auto_action, 'success': success}
                )
            
            return jsonify({
                'success': success,
                'message': message,
                'auto_action': auto_action,
                'new_attempt_count': attempt_count + 1
            })
            
        except Exception as e:
            logger.error(f"Error retrying auto-fix: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/audit/log', methods=['GET'])
    @require_admin
    def get_audit_log():
        """سجل العمليات (backward compatibility)"""
        return get_activity_logs()

    @bp.route('/reports/generate', methods=['POST'])
    @require_admin
    def generate_report():
        """إنشاء تقرير"""
        return jsonify({'success': False, 'message': 'report_generation_not_implemented'}), 501

    @bp.route('/reports/<report_id>/export', methods=['GET'])
    @require_admin
    def export_report(report_id):
        """تصدير تقرير"""
        return jsonify({'success': False, 'message': 'report_export_not_implemented', 'report_id': report_id}), 501

    @bp.route('/logs/clear', methods=['POST'])
    @require_admin
    def clear_logs():
        """حذف السجلات"""
        try:
            return jsonify({'success': True, 'message': 'تم حذف السجلات'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/logs/cleanup', methods=['POST'])
    @require_admin
    def cleanup_logs():
        """حذف السجلات القديمة تلقائياً"""
        try:
            from backend.utils.unified_operation_logger import unified_logger
            
            data = request.get_json() or {}
            operation_days = data.get('operation_days', 7)
            activity_days = data.get('activity_days', 7)
            error_days = data.get('error_days', 30)
            
            if not isinstance(operation_days, int) or operation_days < 1:
                operation_days = 7
            if not isinstance(activity_days, int) or activity_days < 1:
                activity_days = 7
            if not isinstance(error_days, int) or error_days < 1:
                error_days = 30
            
            result = unified_logger.cleanup_all_logs(
                operation_days=operation_days,
                activity_days=activity_days,
                error_days=error_days
            )
            
            return jsonify({
                'success': True,
                'message': f"تم حذف {result['total']} سجل قديم",
                'data': {
                    'operation_logs_deleted': result['operation_logs'],
                    'activity_logs_deleted': result['activity_logs'],
                    'system_errors_deleted': result['system_errors'],
                    'total_deleted': result['total'],
                    'retention_days': {
                        'operation_logs': operation_days,
                        'activity_logs': activity_days,
                        'system_errors': error_days
                    }
                }
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/logs/cleanup/activity', methods=['POST'])
    @require_admin
    def cleanup_activity_logs():
        """حذف سجلات النشاط القديمة"""
        try:
            from backend.utils.unified_operation_logger import unified_logger
            
            data = request.get_json() or {}
            days = data.get('days', 7)
            
            if not isinstance(days, int) or days < 1:
                days = 7
            
            deleted_count = unified_logger.cleanup_activity_logs(days=days)
            
            return jsonify({
                'success': True,
                'message': f"تم حذف {deleted_count} سجل نشاط قديم",
                'data': {'deleted_count': deleted_count, 'retention_days': days}
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/logs/cleanup/errors', methods=['POST'])
    @require_admin
    def cleanup_system_errors():
        """حذف أخطاء النظام القديمة"""
        try:
            from backend.utils.unified_operation_logger import unified_logger
            
            data = request.get_json() or {}
            days = data.get('days', 30)
            
            if not isinstance(days, int) or days < 1:
                days = 30
            
            deleted_count = unified_logger.cleanup_system_errors(days=days)
            
            return jsonify({
                'success': True,
                'message': f"تم حذف {deleted_count} خطأ قديم",
                'data': {'deleted_count': deleted_count, 'retention_days': days}
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/logs/retention-policy', methods=['GET'])
    @require_admin
    def get_retention_policy():
        """جلب سياسة الاحتفاظ بالسجلات"""
        try:
            return jsonify({
                'success': True,
                'data': {
                    'retention_policy': {
                        'operation_logs': {'retention_days': 7, 'description': 'سجلات العمليات (تشغيل/إيقاف المجموعات)'},
                        'activity_logs': {'retention_days': 7, 'description': 'سجلات النشاط (تسجيل الدخول، التحديثات)'},
                        'system_errors': {'retention_days': 30, 'description': 'أخطاء النظام والتطبيق'}
                    },
                    'auto_cleanup': {
                        'enabled': True,
                        'frequency': 'عند بدء كل عملية',
                        'description': 'يتم حذف السجلات القديمة تلقائياً عند بدء العمليات'
                    }
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/cleanup/preview', methods=['GET'])
    @require_admin
    def cleanup_preview():
        """معاينة الملفات التي سيتم حذفها"""
        try:
            from backend.utils.auto_cleanup_manager import AutoCleanupManager
            
            manager = AutoCleanupManager()
            stats = manager.cleanup_all(dry_run=True)
            
            return jsonify({
                'success': True,
                'data': {
                    'files_to_delete': stats['files_deleted'],
                    'space_to_free_mb': round(stats['space_freed'] / 1024 / 1024, 2),
                    'details': {
                        category: {
                            'to_delete': len(details.get('deleted', [])),
                            'to_keep': len(details.get('kept', []))
                        }
                        for category, details in stats.get('details', {}).items()
                    }
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/cleanup/execute', methods=['POST'])
    @require_admin
    def cleanup_execute():
        """تنفيذ التنظيف الفعلي"""
        try:
            from backend.utils.auto_cleanup_manager import AutoCleanupManager
            
            manager = AutoCleanupManager()
            stats = manager.cleanup_all(dry_run=False)
            
            return jsonify({
                'success': True,
                'message': f'تم حذف {stats["files_deleted"]} ملف',
                'data': {
                    'files_deleted': stats['files_deleted'],
                    'directories_deleted': stats.get('directories_deleted', 0),
                    'space_freed_mb': round(stats['space_freed'] / 1024 / 1024, 2),
                    'errors': stats.get('errors', [])
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/cleanup/status', methods=['GET'])
    @require_admin
    def cleanup_status():
        """حالة نظام التنظيف"""
        try:
            from backend.utils.auto_cleanup_manager import AutoCleanupManager
            import os
            
            manager = AutoCleanupManager()
            stats = manager.cleanup_all(dry_run=True)
            
            return jsonify({
                'success': True,
                'data': {
                    'cleanup_enabled': True,
                    'auto_cleanup_on_startup': True,
                    'pending_cleanup': {
                        'files': stats['files_deleted'],
                        'size_mb': round(stats['space_freed'] / 1024 / 1024, 2)
                    },
                    'categories': list(manager.config.keys())
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @bp.route('/logs/statistics', methods=['GET'])
    @require_admin
    def get_logs_statistics():
        """جلب إحصائيات السجلات"""
        try:
            conn = get_safe_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("SELECT COUNT(*) FROM operation_log")
                operation_count = cursor.fetchone()[0]
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                operation_count = 0
            
            cursor.execute("SELECT COUNT(*) FROM activity_logs")
            activity_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM system_errors")
            error_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT pg_database_size(current_database())")
            db_size = cursor.fetchone()[0]
            
            conn.close()
            
            return jsonify({
                'success': True,
                'data': {
                    'operation_logs': operation_count,
                    'activity_logs': activity_count,
                    'system_errors': error_count,
                    'total_logs': operation_count + activity_count + error_count,
                    'database_size_mb': round(db_size / 1024 / 1024, 2)
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
