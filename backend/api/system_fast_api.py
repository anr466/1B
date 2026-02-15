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
import json
import time
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from config.logging_config import get_logger
from backend.core.unified_system_manager import UnifiedSystemManager, SystemAlreadyRunningError, SystemNotRunningError, get_unified_manager
from backend.utils.admin_auth import require_admin
from backend.core.heartbeat_monitor import get_heartbeat_monitor

# إنشاء Blueprint
system_fast_bp = Blueprint('system_fast', __name__, url_prefix='/admin/system')
logger = get_logger(__name__)

# Global unified manager instance
unified_manager = get_unified_manager()

# مسارات الملفات
STATUS_FILE = Path(project_root) / 'tmp' / 'system_status.json'
PID_FILE = Path(project_root) / 'tmp' / 'background_manager.pid'


def ensure_tmp_dir():
    """إنشاء مجلد tmp"""
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)


def read_status():
    """قراءة حالة النظام"""
    ensure_tmp_dir()
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return get_default_status()


def write_status(status_data):
    """كتابة حالة النظام"""
    ensure_tmp_dir()
    status_data['updated_at'] = datetime.now().isoformat()
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(status_data, f, ensure_ascii=False, indent=2)


def get_default_status():
    return {
        'status': 'stopped',
        'is_running': False,
        'pid': None,
        'started_at': None,
        'uptime': 0,
        'message': 'النظام متوقف',
        'updated_at': datetime.now().isoformat()
    }


def get_pid():
    if PID_FILE.exists():
        try:
            with open(PID_FILE, 'r') as f:
                return int(f.read().strip())
        except Exception:
            pass
    return None


def write_pid(pid):
    ensure_tmp_dir()
    with open(PID_FILE, 'w') as f:
        f.write(str(pid))


def clear_pid():
    if PID_FILE.exists():
        PID_FILE.unlink()


def is_process_running(pid):
    try:
        import subprocess
        result = subprocess.run(
            ['ps', '-p', str(pid)],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0
    except Exception:
        return False


def kill_process(pid):
    try:
        import subprocess
        subprocess.run(['kill', '-15', str(pid)], timeout=5, capture_output=True)
        time.sleep(1)
        subprocess.run(['kill', '-9', str(pid)], timeout=5, capture_output=True)
        return True
    except Exception:
        return False


def format_uptime(seconds):
    if seconds <= 0:
        return "0 ثانية"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    
    if days > 0:
        return f"{days} يوم {hours} ساعة"
    elif hours > 0:
        return f"{hours} ساعة {minutes} دقيقة"
    elif minutes > 0:
        return f"{minutes} دقيقة"
    else:
        return f"{seconds} ثانية"


# ==================== Unified Endpoints ====================

@system_fast_bp.route('/start', methods=['POST'])
@require_admin
@system_fast_bp.route('/fast-start', methods=['POST'])  # Backward compatibility
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
                        last_update = datetime('now')
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
@system_fast_bp.route('/fast-stop', methods=['POST'])  # Backward compatibility
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
                        last_update = datetime('now')
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
@system_fast_bp.route('/fast-status', methods=['GET'])  # Backward compatibility
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
        # Use unified manager (includes health check)
        result = unified_manager.get_status()
        
        # ✅ إضافة بيانات المراقبة الحية
        if result.get('success') and result.get('data'):
            state = result['data']
            
            # Heartbeat data مع مراقبة وتسجيل أخطاء
            heartbeat_data = state.get('heartbeat', {})
            if heartbeat_data and heartbeat_data.get('last_beat'):
                seconds_since = unified_manager.state_manager.get_seconds_since_heartbeat()
                result['data']['heartbeat_seconds_ago'] = seconds_since
                result['data']['heartbeat_status'] = 'healthy' if (seconds_since and seconds_since < 30) else 'warning' if (seconds_since and seconds_since < 60) else 'critical'
                
                # ✅ مراقبة heartbeat وتسجيل أخطاء تلقائياً
                if state.get('is_running') and seconds_since:
                    try:
                        from backend.core.heartbeat_monitor import get_heartbeat_monitor
                        monitor = get_heartbeat_monitor(unified_manager.state_manager)
                        monitor.check_heartbeat()
                    except Exception as monitor_error:
                        logger.warning(f"⚠️ فشل فحص heartbeat: {monitor_error}")
            
            # Activity data for each component
            activity_data = state.get('activity', {})
            if activity_data:
                result['data']['activity_status'] = {}
                
                # ✅ إزالة Group A - فقط Group B يعمل
                for component in ['group_b', 'ml']:
                    if component in activity_data:
                        comp_data = activity_data[component]
                        seconds_since = unified_manager.state_manager.get_seconds_since_activity(component)
                        
                        result['data']['activity_status'][component] = {
                            'last_activity': comp_data.get('last_activity'),
                            'seconds_ago': seconds_since,
                            'total_cycles': comp_data.get('total_cycles', 0),
                            'status': 'active' if (seconds_since is not None and (
                                (component == 'group_b' and seconds_since < 120) or
                                (component == 'ml' and seconds_since < 300)
                            )) else 'idle'
                        }
                        
                        # ✅ إزالة Group A - فقط Group B يعمل
                        if component == 'group_b':
                            result['data']['activity_status'][component]['active_trades'] = comp_data.get('active_trades', 0)
                            result['data']['activity_status'][component]['last_cycle'] = comp_data.get('last_cycle')
                        elif component == 'ml':
                            result['data']['activity_status'][component]['total_samples'] = comp_data.get('total_samples', 0)
        
        return jsonify(result)
        
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


# ==================== Test ====================
if __name__ == '__main__':
    # للاختبار المباشر
    print("\n=== اختبار النظام السريع ===")
    print("1. جلب الحالة...")
    import requests
    
    base_url = 'http://localhost:3002/api/admin/system'
    
    # جلب الحالة
    resp = requests.get(f'{base_url}/fast-status')
    print(f"الحالة: {resp.json()}")
    
    print("\n2. بدء النظام...")
    resp = requests.post(f'{base_url}/fast-start')
    print(f"النتيجة: {resp.json()}")
    
    print("\n3. جلب الحالة...")
    resp = requests.get(f'{base_url}/fast-status')
    print(f"الحالة: {resp.json()}")
    
    print("\n4. إيقاف النظام...")
    resp = requests.post(f'{base_url}/fast-stop')
    print(f"النتيجة: {resp.json()}")
