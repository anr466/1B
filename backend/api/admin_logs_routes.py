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
            
            result = audit_logger.get_logs_paginated(
                page=page,
                limit=limit,
                user_id=user_id,
                action=action,
                status=status,
                date_from=date_from,
                date_to=date_to
            )
            
            return jsonify({'success': True, 'data': result})
            
        except Exception as e:
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
        return jsonify({'success': True, 'report_id': 'RPT' + datetime.now().strftime('%Y%m%d%H%M%S')})

    @bp.route('/reports/<report_id>/export', methods=['GET'])
    @require_admin
    def export_report(report_id):
        """تصدير تقرير"""
        return jsonify({'success': True})

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
            conn = get_safe_connection(db.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM operation_log")
            operation_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM activity_logs")
            activity_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM system_errors")
            error_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
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
