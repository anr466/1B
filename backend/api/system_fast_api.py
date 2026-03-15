#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Unified System API - نظام موحد للتحكم
==========================================

نظام موحد ومحسّن مع:
- UnifiedSystemManager (Transaction safety)
- Single Source of Truth (JSON only)
- Health checking
- Audit trail

Endpoints:
- POST /api/admin/system/start
- POST /api/admin/system/stop
- GET /api/admin/system/status
- GET /api/admin/system/health
"""

import os
import sys
from flask import Blueprint, jsonify

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from config.logging_config import get_logger
from backend.core.unified_system_manager import UnifiedSystemManager, SystemAlreadyRunningError, SystemNotRunningError, get_unified_manager
from backend.utils.admin_auth import require_admin
from backend.core.heartbeat_monitor import get_heartbeat_monitor
from backend.core.trading_state_machine import get_trading_state_machine
from backend.core.state_manager import get_state_manager

# إنشاء Blueprint
system_fast_bp = Blueprint('system_fast', __name__, url_prefix='/admin/system')
logger = get_logger(__name__)

# Global unified manager instance
unified_manager = get_unified_manager()

# ==================== Unified Endpoints ====================

@system_fast_bp.route('/start', methods=['POST'])
@require_admin
def start_system():
    """
    🚀 بدء النظام - Unified API with transaction safety
    
    Features:
    - Transaction safety (rollback on failure)
    - File locking (prevent race conditions)
    - Audit trail
    - Health checking
    - ✅ Syncs with TradingStateMachine
    """
    try:
        logger.info("🚀 طلب بدء النظام...")
        
        # Use unified manager
        result = unified_manager.start_system(user='api_user')
        
        # ✅ FIX: Sync with TradingStateMachine
        try:
            from backend.core.trading_state_machine import get_trading_state_machine
            tsm = get_trading_state_machine()
            # Update trading_state in DB to match
            with tsm.db.get_write_connection() as conn:
                conn.execute("""
                    UPDATE system_status 
                    SET trading_state = 'RUNNING',
                        session_id = ?,
                        mode = 'PAPER',
                        initiated_by = 'api_user',
                        last_update = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (result.get('pid', 'unknown'),))
                conn.commit()
            logger.info("✅ Synced state with TradingStateMachine")
        except Exception as sync_error:
            logger.warning(f"⚠️ Failed to sync with TradingStateMachine: {sync_error}")
        
        logger.info(f"✅ تم بدء النظام بنجاح (PID: {result['pid']})")
        return jsonify(result)
        
    except SystemAlreadyRunningError as e:
        logger.warning(f"⚠️ {e}")
        pid = unified_manager.get_pid()
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'ALREADY_RUNNING',
            'pid': pid
        }), 409
        
    except Exception as e:
        logger.error(f"❌ خطأ في بدء النظام: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_fast_bp.route('/stop', methods=['POST'])
@require_admin
def stop_system():
    """
    ⏹️ إيقاف النظام - Unified API with cleanup
    
    Features:
    - Safe shutdown with zombie cleanup
    - File locking
    - Audit trail
    - ✅ Syncs with TradingStateMachine
    """
    try:
        logger.info("⏹️ طلب إيقاف النظام...")
        
        # Use unified manager
        result = unified_manager.stop_system(user='api_user')
        
        # ✅ FIX: Sync with TradingStateMachine
        try:
            from backend.core.trading_state_machine import get_trading_state_machine
            tsm = get_trading_state_machine()
            # Update trading_state in DB to match
            with tsm.db.get_write_connection() as conn:
                conn.execute("""
                    UPDATE system_status 
                    SET trading_state = 'STOPPED',
                        pid = NULL,
                        last_update = CURRENT_TIMESTAMP
                    WHERE id = 1
                """)
                conn.commit()
            logger.info("✅ Synced state with TradingStateMachine")
        except Exception as sync_error:
            logger.warning(f"⚠️ Failed to sync with TradingStateMachine: {sync_error}")
        
        logger.info("✅ تم إيقاف النظام")
        return jsonify(result)
        
    except SystemNotRunningError as e:
        logger.warning(f"⚠️ {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'NOT_RUNNING'
        }), 400
        
    except Exception as e:
        logger.error(f"❌ خطأ في إيقاف النظام: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_fast_bp.route('/status', methods=['GET'])
@require_admin
def get_status():
    """
    📊 جلب حالة النظام - Unified API with health check + Live Monitoring
    
    Features:
    - Health checking
    - State reconciliation
    - Uptime calculation
    - Heartbeat monitoring (يثبت أن النظام حي)
    - Last activity tracking (لكل نظام فرعي)
    """
    try:
        tsm = get_trading_state_machine()
        state_manager = get_state_manager()

        canonical_state = tsm.get_state()
        raw_state = state_manager.read_state()
        subsystems = canonical_state.get('subsystems', {}) or {}
        heartbeat_data = subsystems.get('heartbeat', {}) or raw_state.get('heartbeat', {}) or {}

        result_data = dict(canonical_state)
        trading_state = str(result_data.get('trading_state') or result_data.get('state') or 'STOPPED').upper()
        result_data['trading_state'] = trading_state
        result_data['state'] = trading_state
        result_data['status'] = 'running' if trading_state == 'RUNNING' else 'stopped'
        result_data['is_running'] = trading_state == 'RUNNING'

        heartbeat_seconds_ago = heartbeat_data.get('seconds_ago')
        if heartbeat_seconds_ago is None:
            heartbeat_seconds_ago = state_manager.get_seconds_since_heartbeat()

        if heartbeat_seconds_ago is not None:
            result_data['heartbeat_seconds_ago'] = heartbeat_seconds_ago
            result_data['heartbeat_status'] = (
                'healthy' if heartbeat_seconds_ago < 30
                else 'warning' if heartbeat_seconds_ago < 60
                else 'critical'
            )

            if result_data.get('trading_active'):
                try:
                    monitor = get_heartbeat_monitor(state_manager)
                    monitor.check_heartbeat()
                except Exception as monitor_error:
                    logger.warning(f"⚠️ فشل فحص heartbeat: {monitor_error}")

        activity_status = {}
        for component in ['group_b', 'ml']:
            comp_data = subsystems.get(component) or raw_state.get('activity', {}).get(component, {})
            if not comp_data:
                continue

            seconds_since = comp_data.get('seconds_ago')
            if seconds_since is None:
                seconds_since = state_manager.get_seconds_since_activity(component)

            component_status = {
                'last_activity': comp_data.get('last_activity'),
                'seconds_ago': seconds_since,
                'total_cycles': comp_data.get('total_cycles', 0),
                'status': 'active' if (seconds_since is not None and (
                    (component == 'group_b' and seconds_since < 120) or
                    (component == 'ml' and seconds_since < 300)
                )) else 'idle'
            }

            if component == 'group_b':
                component_status['active_trades'] = comp_data.get('active_trades', 0)
                component_status['last_cycle'] = comp_data.get('last_cycle')
            elif component == 'ml':
                component_status['total_samples'] = comp_data.get('total_samples', 0)

            activity_status[component] = component_status

        result_data['activity_status'] = activity_status
        result_data['heartbeat'] = heartbeat_data
        result_data['activity'] = raw_state.get('activity', {})

        return jsonify({
            'success': True,
            'data': result_data,
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الحالة: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_fast_bp.route('/health', methods=['GET'])
@require_admin
def health_check():
    """
    🏥 فحص صحة النظام
    
    Returns:
        - is_healthy: bool
        - process_alive: bool
        - state_consistent: bool
    """
    try:
        state = unified_manager.state_manager.read_state()
        pid = state.get('pid')
        
        process_alive = unified_manager._is_process_alive(pid) if pid else False
        state_says_running = state.get('is_running', False)
        
        is_healthy = (process_alive == state_says_running)
        
        return jsonify({
            'success': True,
            'is_healthy': is_healthy,
            'process_alive': process_alive,
            'state_says_running': state_says_running,
            'state_consistent': is_healthy,
            'pid': pid
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في فحص الصحة: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@system_fast_bp.route('/reconcile', methods=['POST'])
@require_admin
def reconcile_state():
    """
    🔄 مطابقة الحالة مع الواقع
    
    يستخدم عند:
    - بدء الخادم
    - بعد crash
    - للتحقق من التناسق
    """
    try:
        logger.info("🔄 مطابقة الحالة...")
        unified_manager.reconcile_state()
        
        result = unified_manager.get_status()
        return jsonify({
            'success': True,
            'message': 'تم مطابقة الحالة بنجاح',
            'data': result['data']
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في المطابقة: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
