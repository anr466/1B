#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 Trading Control API - واجهة التحكم بنظام التداول
====================================================

State-machine-driven API. Backend is Single Source of Truth.
Start/Stop never throw errors for normal states.

Endpoints:
- GET  /api/admin/trading/state          → الحالة الحالية
- POST /api/admin/trading/start          → تشغيل النظام
- POST /api/admin/trading/stop           → إيقاف النظام
- POST /api/admin/trading/emergency-stop → إيقاف طوارئ
- POST /api/admin/trading/reset-error    → إعادة تعيين من حالة خطأ

Author: System Orchestrator
Date: 2026-02-09
"""

import os
import sys
from flask import Blueprint, request, jsonify, g

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from config.logging_config import get_logger
from backend.core.trading_state_machine import get_trading_state_machine
from backend.utils.admin_auth import require_admin

trading_control_bp = Blueprint('trading_control', __name__, url_prefix='/admin/trading')
logger = get_logger(__name__)

# Singleton state machine
tsm = get_trading_state_machine()


@trading_control_bp.route('/state', methods=['GET'])
@require_admin
def get_trading_state():
    """
    📊 الحصول على حالة نظام التداول الحالية
    
    Always returns:
    - trading_state: STOPPED|STARTING|RUNNING|STOPPING|ERROR
    - session_id
    - mode (PAPER/LIVE)
    - open_positions count
    - pid, uptime, subsystems
    """
    try:
        state = tsm.get_state()
        state['is_running'] = state.get('trading_active', False)
        return jsonify(state)
    except Exception as e:
        logger.error(f"❌ get_trading_state error: {e}")
        return jsonify({
            'success': False,
            'trading_state': 'ERROR',
            'is_running': False,
            'message': str(e),
        }), 500


@trading_control_bp.route('/start', methods=['POST'])
@require_admin
def start_trading():
    """
    🚀 تشغيل نظام التداول
    
    Body (optional):
    - mode: "PAPER" or "LIVE" (default: PAPER)
    
    Rules:
    - If STOPPED/ERROR → starts system, returns new state
    - If STARTING/RUNNING → returns current state (NO error)
    - Never returns 409 or throws for normal conditions
    """
    try:
        data = request.get_json(silent=True) or {}
        mode = data.get('mode', 'PAPER')
        initiated_by = f"admin:{getattr(g, 'user_id', 'unknown')}"

        # تنظيف السجلات القديمة عند بدء التداول
        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            with db.get_write_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM activity_logs WHERE created_at < (CURRENT_TIMESTAMP - INTERVAL '1 day')"
                )
                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    logger.info(f"🗑️ تم تنظيف {deleted_count} سجل نشاط قديم عند بدء التداول")
        except Exception as cleanup_err:
            logger.warning(f"⚠️ فشل تنظيف السجلات: {cleanup_err}")

        logger.info(f"🚀 Start trading requested by {initiated_by}, mode={mode}")
        state = tsm.start(initiated_by=initiated_by, mode=mode)
        return jsonify(state)

    except Exception as e:
        logger.error(f"❌ start_trading error: {e}")
        return jsonify({
            'success': False,
            'trading_state': 'ERROR',
            'message': str(e),
        }), 500


@trading_control_bp.route('/stop', methods=['POST'])
@require_admin
def stop_trading():
    """
    ⏹️ إيقاف نظام التداول
    
    Rules:
    - If RUNNING → stops system gracefully, returns new state
    - If STOPPED/STOPPING → returns current state (NO error)
    - Open positions are noted but system still stops
    """
    try:
        initiated_by = f"admin:{getattr(g, 'user_id', 'unknown')}"

        logger.info(f"⏹️ Stop trading requested by {initiated_by}")
        state = tsm.stop(initiated_by=initiated_by)
        return jsonify(state)

    except Exception as e:
        logger.error(f"❌ stop_trading error: {e}")
        return jsonify({
            'success': False,
            'trading_state': 'ERROR',
            'message': str(e),
        }), 500


@trading_control_bp.route('/emergency-stop', methods=['POST'])
@require_admin
def emergency_stop_trading():
    """
    🚨 إيقاف طوارئ فوري
    
    Kills all processes immediately. No grace period.
    """
    try:
        initiated_by = f"admin:{getattr(g, 'user_id', 'unknown')}"

        logger.warning(f"🚨 Emergency stop requested by {initiated_by}")
        state = tsm.emergency_stop(initiated_by=initiated_by)
        return jsonify(state)

    except Exception as e:
        logger.error(f"❌ emergency_stop error: {e}")
        return jsonify({
            'success': False,
            'trading_state': 'ERROR',
            'message': str(e),
        }), 500


@trading_control_bp.route('/reset-error', methods=['POST'])
@require_admin
def reset_error():
    """
    🔄 إعادة تعيين من حالة ERROR إلى STOPPED
    """
    try:
        initiated_by = f"admin:{getattr(g, 'user_id', 'unknown')}"
        state = tsm.reset_error(initiated_by=initiated_by)
        return jsonify(state)

    except Exception as e:
        logger.error(f"❌ reset_error error: {e}")
        return jsonify({
            'success': False,
            'trading_state': 'ERROR',
            'message': str(e),
        }), 500
