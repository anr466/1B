#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 Trading State Machine - آلة حالة التداول
=============================================

DB-backed state machine for trading system control.
Single Source of Truth — all state lives in system_status table.

States: STOPPED, STARTING, RUNNING, STOPPING, ERROR

Rules:
- Start/Stop NEVER throw HTTP errors for normal states
- They always return the current canonical state
- DB-level locking prevents race conditions
- Process health is reconciled on every state read

Author: System Orchestrator
Date: 2026-02-09
"""

import os
import sys
import signal
import subprocess
import time
import uuid
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.logging_config import get_logger
from backend.infrastructure.db_access import get_db_manager
from backend.core.state_manager import StateManager

logger = get_logger(__name__)

# Valid states
STOPPED = 'STOPPED'
STARTING = 'STARTING'
RUNNING = 'RUNNING'
STOPPING = 'STOPPING'
ERROR = 'ERROR'

VALID_STATES = [STOPPED, STARTING, RUNNING, STOPPING, ERROR]

VALID_TRANSITIONS = {
    STOPPED:  [STARTING],
    STARTING: [RUNNING, ERROR, STOPPED],
    RUNNING:  [STOPPING, ERROR],
    STOPPING: [STOPPED, ERROR],
    ERROR:    [STOPPED, STARTING],
}

# State labels for UI
STATE_LABELS = {
    STOPPED:  'متوقف',
    STARTING: 'جاري التشغيل...',
    RUNNING:  'يعمل',
    STOPPING: 'جاري الإيقاف...',
    ERROR:    'خطأ',
}


class TradingStateMachine:
    """
    DB-backed trading state machine.
    
    Golden Rule: Start/Stop always return current state, never throw for normal conditions.
    Golden Rule: DB is the single source of truth.
    Golden Rule: Process health is verified on every read.
    """

    def __init__(self):
        self.db = get_db_manager()
        self.state_manager = StateManager(self.db)
        self.project_root = PROJECT_ROOT
        self.pid_file = self.project_root / 'tmp' / 'system.pid'
        self.reconcile_stats = {
            'total': 0,
            'running_to_error': 0,
            'starting_timeout': 0,
            'stopping_to_stopped': 0,
            'stopped_orphan_killed': 0,
            'stopped_to_running': 0,
            'last_event_at': None,
            'last_event_type': None,
        }
        self.reconcile_warn_threshold = int(os.getenv('RECONCILE_WARN_THRESHOLD', '5'))

    def _normalize_state(self, raw_state: Any) -> str:
        """Normalize DB state into canonical enum values."""
        if raw_state is None:
            return STOPPED
        state = str(raw_state).strip().upper()
        return state if state in VALID_STATES else STOPPED

    # ==================== Core State Operations ====================

    def get_state(self) -> Dict[str, Any]:
        """
        Get canonical trading state.
        
        1. Read state from DB
        2. Verify process health
        3. Reconcile if mismatch
        4. Count open positions
        5. Return canonical state
        """
        try:
            with self.db.get_connection() as conn:
                row = conn.execute("""
                    SELECT trading_state, session_id, mode, initiated_by,
                           is_running, started_at, message, last_update,
                           error_count, last_error
                    FROM system_status WHERE id = 1
                """).fetchone()

                if not row:
                    return self._default_state()

                trading_state = self._normalize_state(row[0])
                session_id = row[1]
                mode = row[2] or 'PAPER'
                initiated_by = row[3]
                is_running_db = bool(row[4])
                started_at = row[5]
                message = row[6] or ''
                last_update = row[7]
                error_count = int(row[8] or 0)
                last_error = row[9]

            # Verify process health
            pid = self._find_trading_process()
            process_alive = pid is not None

            # Reconcile state vs reality
            trading_state, message = self._reconcile(
                trading_state, process_alive, pid, message
            )

            # Keep UI-facing message aligned with canonical state
            if trading_state == STOPPED:
                if (not message) or ('يعمل' in str(message) and not process_alive):
                    message = 'النظام متوقف'
            elif trading_state == RUNNING and not message:
                message = 'النظام يعمل'

            # Count open positions
            open_positions = self._count_open_positions()

            # Calculate uptime
            uptime = 0
            uptime_formatted = None
            if trading_state == RUNNING and started_at:
                try:
                    started_dt = datetime.fromisoformat(started_at)
                    uptime = int((datetime.now() - started_dt).total_seconds())
                    uptime_formatted = self._format_uptime(uptime)
                except Exception:
                    pass

            # Get subsystem activity from JSON state file (if exists)
            subsystems = self._get_subsystem_status()
            if trading_state != RUNNING and subsystems:
                if 'group_b' in subsystems:
                    subsystems['group_b']['status'] = 'idle'
                if 'ml' in subsystems:
                    subsystems['ml']['status'] = 'idle'
                if 'heartbeat' in subsystems:
                    subsystems['heartbeat']['status'] = 'stopped'

            # Binance connection status — safe import to avoid circular deps
            binance_connected = False
            binance_latency_ms = None
            try:
                from backend.core.binance_connector import get_binance_connector
                bc = get_binance_connector()
                binance_connected = bc.is_connected
                binance_latency_ms = getattr(bc, 'latency_ms', None)
            except Exception:
                binance_connected = False  # unknown / unavailable — do not assume OK

            return {
                'success': True,
                'trading_state': trading_state,
                'state': trading_state,
                'trading_state_label': STATE_LABELS.get(trading_state, trading_state),
                'trading_active': trading_state == RUNNING,
                'session_id': session_id,
                'mode': mode,
                'trading_mode': mode.lower() if mode else 'demo',
                'initiated_by': initiated_by,
                'open_positions': open_positions,
                'pid': pid,
                'uptime': uptime,
                'uptime_formatted': uptime_formatted,
                'started_at': started_at,
                'message': message,
                'last_update': last_update or datetime.now().isoformat(),
                'last_updated': last_update or datetime.now().isoformat(),
                'error_count': error_count,
                'last_error': last_error,
                'subsystems': subsystems,
                'reconcile_stats': self.reconcile_stats,
                'binance_connected': binance_connected,
                'binance_latency_ms': binance_latency_ms,
            }

        except Exception as e:
            logger.error(f"❌ get_state error: {e}")
            return {
                'success': False,
                'trading_state': ERROR,
                'state': ERROR,
                'trading_state_label': STATE_LABELS[ERROR],
                'trading_active': False,
                'message': str(e),
                'open_positions': 0,
                'pid': None,
                'uptime': 0,
                'session_id': None,
                'mode': 'PAPER',
                'trading_mode': 'demo',
                'error_count': 0,
                'last_error': str(e),
                'last_update': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'subsystems': {},
                'reconcile_stats': self.reconcile_stats,
            }

    def start(self, initiated_by: str = 'admin', mode: str = 'PAPER') -> Dict[str, Any]:
        """
        Attempt to start trading system.
        
        NEVER throws for normal states.
        If already STARTING/RUNNING → returns current state silently.
        If STOPPED/ERROR → transitions to STARTING → starts process → RUNNING.
        """
        try:
            # Use write connection for exclusive lock
            with self.db.get_write_connection() as conn:
                row = conn.execute(
                    "SELECT trading_state FROM system_status WHERE id = 1"
                ).fetchone()
                current_state = self._normalize_state(row[0] if row else STOPPED)

                # Already running or starting — return current state (no error!)
                if current_state in (STARTING, RUNNING):
                    logger.info(f"ℹ️ Start requested but state is {current_state} — returning current state")
                    return self.get_state()

                # Can only start from STOPPED or ERROR
                if current_state not in (STOPPED, ERROR):
                    logger.warning(f"⚠️ Cannot start from state {current_state}")
                    return self.get_state()

                # Containerized deployment safety:
                # if a trading process is already alive (e.g. worker service),
                # adopt it instead of trying to spawn a duplicate process.
                existing_pid = self._find_trading_process()
                if existing_pid:
                    self._transition(
                        conn,
                        RUNNING,
                        pid=existing_pid,
                        started_at=datetime.now().isoformat(),
                        message=f'النظام يعمل (PID: {existing_pid}) - تمت المزامنة'
                    )
                    conn.commit()
                    self._log_transition(
                        current_state, RUNNING, initiated_by, None,
                        f'Adopted existing process PID={existing_pid}'
                    )
                    logger.info(f"✅ Adopted existing trading process PID={existing_pid}")
                    return self.get_state()

                # Transition to STARTING
                session_id = str(uuid.uuid4())[:8]
                self._transition(conn, STARTING, session_id=session_id,
                                mode=mode, initiated_by=initiated_by,
                                message='جاري تشغيل النظام...')
                conn.commit()

            # Log state transition
            self._log_transition(STOPPED, STARTING, initiated_by, session_id,
                                'طلب تشغيل النظام')

            # Start the actual process (outside DB lock)
            try:
                pid = self._start_process()

                # Verify process started
                time.sleep(1.0)
                if not self._is_process_alive(pid):
                    raise Exception(f"Process {pid} died immediately after start")

                # Transition to RUNNING
                with self.db.get_write_connection() as conn:
                    self._transition(conn, RUNNING, pid=pid,
                                    started_at=datetime.now().isoformat(),
                                    message=f'النظام يعمل (PID: {pid})')
                    conn.commit()

                self._log_transition(STARTING, RUNNING, 'system', session_id,
                                    f'تم التشغيل بنجاح PID={pid}')

                # ✅ FIX: Sync with StateManager (UnifiedSystemManager)
                try:
                    self.state_manager.reset_monitoring_data()
                    self.state_manager.write_state({
                        'status': 'running',
                        'trading_state': RUNNING,
                        'is_running': True,
                        'pid': pid,
                        'started_at': datetime.now().isoformat(),
                        'heartbeat': {
                            'last_beat': None,
                            'beats_count': 0,
                            'missed_beats': 0,
                        },
                        'message': 'النظام يعمل'
                    }, user=initiated_by)
                    logger.info("✅ Synced state with StateManager")
                except Exception as sync_error:
                    logger.warning(f"⚠️ Failed to sync with StateManager: {sync_error}")

                logger.info(f"✅ Trading system started (PID: {pid}, session: {session_id})")

            except Exception as start_error:
                logger.error(f"❌ Failed to start process: {start_error}")
                # Fallback safety:
                # if another process became alive during start race, recover to RUNNING.
                recovered_pid = self._find_trading_process()
                if recovered_pid:
                    with self.db.get_write_connection() as conn:
                        self._transition(
                            conn,
                            RUNNING,
                            pid=recovered_pid,
                            started_at=datetime.now().isoformat(),
                            message=f'النظام يعمل (PID: {recovered_pid}) - تمت المزامنة بعد تعثر البدء'
                        )
                        conn.commit()
                    self._log_transition(
                        STARTING, RUNNING, 'system', session_id,
                        f'recovered via existing PID={recovered_pid} after start error'
                    )
                    logger.info(f"✅ Recovered start flow using existing process PID={recovered_pid}")
                else:
                    # Transition to ERROR
                    with self.db.get_write_connection() as conn:
                        self._transition(conn, ERROR,
                                        message=f'فشل التشغيل: {str(start_error)[:100]}')
                        conn.commit()

                    self._log_transition(STARTING, ERROR, 'system', session_id,
                                        f'فشل التشغيل: {start_error}')

            return self.get_state()

        except Exception as e:
            logger.error(f"❌ start() error: {e}")
            return self.get_state()

    def stop(self, initiated_by: str = 'admin') -> Dict[str, Any]:
        """
        Attempt to stop trading system.
        
        NEVER throws for normal states.
        If already STOPPED/STOPPING → returns current state silently.
        If RUNNING → transitions to STOPPING → stops process → STOPPED.
        """
        try:
            session_id = None
            with self.db.get_write_connection() as conn:
                row = conn.execute(
                    "SELECT trading_state, session_id FROM system_status WHERE id = 1"
                ).fetchone()
                current_state = self._normalize_state(row[0] if row else STOPPED)
                session_id = row[1] if row else None

                # Already stopped or stopping — return current state
                if current_state in (STOPPED, STOPPING):
                    logger.info(f"ℹ️ Stop requested but state is {current_state}")
                    return self.get_state()

                # Can stop from RUNNING, ERROR, or STARTING
                if current_state not in (RUNNING, ERROR, STARTING):
                    return self.get_state()

                # Transition to STOPPING
                self._transition(conn, STOPPING,
                                message='جاري إيقاف النظام...')
                conn.commit()

            self._log_transition(current_state, STOPPING, initiated_by, session_id,
                                'طلب إيقاف النظام')

            # Count open positions before stopping
            open_positions = self._count_open_positions()

            # Stop the process
            try:
                self._stop_all_processes()

                # Transition to STOPPED
                with self.db.get_write_connection() as conn:
                    self._transition(conn, STOPPED, pid=None,
                                    started_at=None,
                                    message='النظام متوقف')
                    conn.commit()

                self._log_transition(STOPPING, STOPPED, 'system', session_id,
                                    f'تم الإيقاف. صفقات مفتوحة: {open_positions}')

                # ✅ FIX: Sync with StateManager (UnifiedSystemManager)
                try:
                    self.state_manager.reset_monitoring_data()
                    self.state_manager.write_state({
                        'status': 'stopped',
                        'trading_state': STOPPED,
                        'is_running': False,
                        'pid': None,
                        'started_at': None,
                        'message': 'النظام متوقف'
                    }, user=initiated_by)
                    logger.info("✅ Synced state with StateManager")
                except Exception as sync_error:
                    logger.warning(f"⚠️ Failed to sync with StateManager: {sync_error}")

                logger.info(f"✅ Trading system stopped (session: {session_id})")

            except Exception as stop_error:
                logger.error(f"❌ Failed to stop process: {stop_error}")

                with self.db.get_write_connection() as conn:
                    self._transition(conn, ERROR,
                                    message=f'فشل الإيقاف: {str(stop_error)[:100]}')
                    conn.commit()

                self._log_transition(STOPPING, ERROR, 'system', session_id,
                                    f'فشل الإيقاف: {stop_error}')

            return self.get_state()

        except Exception as e:
            logger.error(f"❌ stop() error: {e}")
            return self.get_state()

    def emergency_stop(self, initiated_by: str = 'admin') -> Dict[str, Any]:
        """Force stop everything immediately. No grace period."""
        try:
            session_id = None
            with self.db.get_write_connection() as conn:
                row = conn.execute(
                    "SELECT session_id FROM system_status WHERE id = 1"
                ).fetchone()
                session_id = row[0] if row else None

            # Kill everything immediately
            self._force_kill_all()

            # Transition directly to STOPPED
            with self.db.get_write_connection() as conn:
                self._transition(conn, STOPPED, pid=None,
                                started_at=None,
                                message='إيقاف طوارئ')
                conn.commit()

            try:
                self.state_manager.reset_monitoring_data()
                self.state_manager.write_state({
                    'status': 'stopped',
                    'trading_state': STOPPED,
                    'is_running': False,
                    'pid': None,
                    'started_at': None,
                    'message': 'إيقاف طوارئ'
                }, user=initiated_by)
            except Exception as sync_error:
                logger.warning(f"⚠️ Failed to sync emergency stop with StateManager: {sync_error}")

            self._log_transition('ANY', STOPPED, initiated_by, session_id,
                                'إيقاف طوارئ فوري')

            logger.warning(f"🚨 Emergency stop executed by {initiated_by}")
            return self.get_state()

        except Exception as e:
            logger.error(f"❌ emergency_stop error: {e}")
            return self.get_state()

    def reset_error(self, initiated_by: str = 'admin') -> Dict[str, Any]:
        """Reset from ERROR state to STOPPED."""
        try:
            with self.db.get_write_connection() as conn:
                row = conn.execute(
                    "SELECT trading_state FROM system_status WHERE id = 1"
                ).fetchone()
                current_state = self._normalize_state(row[0] if row else STOPPED)
                if current_state == ERROR:
                    self._transition(conn, STOPPED, pid=None,
                                    started_at=None,
                                    message='تم إعادة التعيين')
                    conn.commit()
                    try:
                        self.state_manager.reset_monitoring_data()
                        self.state_manager.write_state({
                            'status': 'stopped',
                            'trading_state': STOPPED,
                            'is_running': False,
                            'pid': None,
                            'started_at': None,
                            'message': 'تم إعادة التعيين'
                        }, user=initiated_by)
                    except Exception as sync_error:
                        logger.warning(f"⚠️ Failed to sync reset-error with StateManager: {sync_error}")
                    self._log_transition(ERROR, STOPPED, initiated_by, None,
                                        'إعادة تعيين من حالة خطأ')
            return self.get_state()
        except Exception as e:
            logger.error(f"❌ reset_error: {e}")
            return self.get_state()

    # ==================== State Transitions ====================

    def _transition(self, conn, new_state: str, **kwargs):
        """Execute a state transition in the DB."""
        updates = ['trading_state = %s', 'last_update = CURRENT_TIMESTAMP']
        params = [new_state]

        # Also sync the legacy is_running column
        is_running = new_state in (STARTING, RUNNING)
        updates.append('is_running = %s')
        params.append(is_running)

        # Also sync legacy status column (lowercase)
        updates.append('status = %s')
        params.append(new_state.lower())

        field_map = {
            'session_id': 'session_id',
            'mode': 'mode',
            'initiated_by': 'initiated_by',
            'message': 'message',
            'pid': 'pid',  # We store pid in message since no pid column in system_status
            'started_at': 'started_at',
        }

        for key, col in field_map.items():
            if key in kwargs:
                # pid doesn't have its own column — encode it in message
                if key == 'pid':
                    continue
                updates.append(f'{col} = %s')
                params.append(kwargs[key])

        sql = f"UPDATE system_status SET {', '.join(updates)} WHERE id = 1"
        conn.execute(sql, params)

    def _reconcile(self, db_state: str, process_alive: bool, pid: Optional[int],
                   message: str) -> tuple:
        """
        Reconcile DB state with process reality.
        Returns (corrected_state, corrected_message).
        """
        corrected = db_state
        corrected_msg = message
        heartbeat_seconds = self._get_seconds_since_heartbeat()
        heartbeat_fresh = heartbeat_seconds is not None and heartbeat_seconds < 60

        if db_state == RUNNING and not process_alive:
            # In containerized/distributed runtime, PID discovery may fail while
            # the system is still healthy. Fresh heartbeat is authoritative enough
            # to keep the state as RUNNING.
            if heartbeat_fresh:
                corrected = RUNNING
                corrected_msg = message or 'النظام يعمل (مؤكد عبر heartbeat)'
            else:
                corrected = ERROR
                corrected_msg = 'العملية توقفت بشكل غير متوقع'
                self._do_reconcile_update(corrected, corrected_msg)
                self._record_reconcile_event('running_to_error')
                self._log_transition(RUNNING, ERROR, 'reconcile', None,
                                    'Process died unexpectedly')

        elif db_state == STARTING and not process_alive:
            # Check if stuck in STARTING for too long (>60s)
            try:
                with self.db.get_connection() as conn:
                    row = conn.execute(
                        "SELECT last_update FROM system_status WHERE id = 1"
                    ).fetchone()
                    if row and row[0]:
                        last_update = datetime.fromisoformat(row[0])
                        if (datetime.now() - last_update).total_seconds() > 60:
                            corrected = ERROR
                            corrected_msg = 'انتهت مهلة التشغيل'
                            self._do_reconcile_update(corrected, corrected_msg)
                            self._record_reconcile_event('starting_timeout')
            except Exception:
                pass

        elif db_state == STOPPING:
            # Check if stuck in STOPPING for too long (>30s)
            if not process_alive:
                corrected = STOPPED
                corrected_msg = 'تم الإيقاف'
                self._do_reconcile_update(corrected, corrected_msg)
                self._record_reconcile_event('stopping_to_stopped')

        elif db_state == STOPPED and process_alive:
            # Process running but DB says stopped
            # Grace period: don't auto-promote if state was recently set to STOPPED
            # (e.g. after emergency stop, orphan processes may linger briefly)
            try:
                with self.db.get_connection() as conn:
                    row = conn.execute(
                        "SELECT last_update FROM system_status WHERE id = 1"
                    ).fetchone()
                    if row and row[0]:
                        last_update = datetime.fromisoformat(row[0])
                        seconds_since = (datetime.now() - last_update).total_seconds()
                        if seconds_since < 15:
                            # Recently stopped — kill the orphan instead of promoting
                            logger.warning(f"⚠️ Orphan process PID={pid} found {seconds_since:.0f}s after STOPPED — killing it")
                            try:
                                os.kill(pid, 9)
                                self._record_reconcile_event('stopped_orphan_killed')
                            except OSError:
                                pass
                            return corrected, corrected_msg
            except Exception:
                pass

            # If STOPPED for >15s and process still alive, promote to RUNNING
            corrected = RUNNING
            corrected_msg = f'النظام يعمل (PID: {pid}) - تمت المزامنة'
            self._do_reconcile_update(corrected, corrected_msg)
            self._record_reconcile_event('stopped_to_running')
            self._log_transition(STOPPED, RUNNING, 'reconcile', None,
                                f'Found running process PID={pid}')

        return corrected, corrected_msg

    def _do_reconcile_update(self, state: str, message: str):
        """Update DB during reconciliation."""
        try:
            with self.db.get_write_connection() as conn:
                is_running = state in (STARTING, RUNNING)
                conn.execute("""
                    UPDATE system_status
                    SET trading_state = %s, status = %s, is_running = %s,
                        message = %s, last_update = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (state, state.lower(), is_running, message))
                conn.commit()
        except Exception as e:
            logger.warning(f"⚠️ Reconcile update failed: {e}")

    def _record_reconcile_event(self, event_type: str):
        """تسجيل حدث مصالحة مع تنبيهات عند التكرار العالي."""
        self.reconcile_stats['total'] += 1
        if event_type in self.reconcile_stats:
            self.reconcile_stats[event_type] += 1
        self.reconcile_stats['last_event_at'] = datetime.now().isoformat()
        self.reconcile_stats['last_event_type'] = event_type

        event_count = self.reconcile_stats.get(event_type, 0)
        if event_count >= self.reconcile_warn_threshold:
            logger.warning(
                f"⚠️ Reconcile anomaly threshold reached: {event_type} count={event_count} "
                f"(threshold={self.reconcile_warn_threshold})"
            )

    def _get_seconds_since_heartbeat(self) -> Optional[int]:
        """Read heartbeat freshness from StateManager-backed DB state."""
        try:
            from backend.core.state_manager import StateManager
            state_manager = StateManager(self.db)
            return state_manager.get_seconds_since_heartbeat()
        except Exception:
            return None

    # ==================== Settings Check ====================

    def _check_settings_configured(self) -> bool:
        """Check if trading settings exist and are properly configured."""
        try:
            admin_user_id = self._resolve_active_admin_user_id()
            if admin_user_id is None:
                return False
            with self.db.get_connection() as conn:
                row = conn.execute("""
                    SELECT position_size_percentage, max_positions
                    FROM user_settings
                    WHERE user_id = %s AND is_demo = %s
                    LIMIT 1
                """, (admin_user_id, True)).fetchone()
                if not row:
                    return False
                # Settings exist — consider configured if position_size > 0 and max_positions > 0
                return bool(row[0] and row[0] > 0 and row[1] and row[1] > 0)
        except Exception:
            return False

    def _resolve_active_admin_user_id(self) -> Optional[int]:
        """Resolve the active admin account dynamically instead of assuming a fixed user id."""
        try:
            with self.db.get_connection() as conn:
                row = conn.execute("""
                    SELECT id
                    FROM users
                    WHERE user_type = 'admin' AND is_active = %s
                    ORDER BY id
                    LIMIT 1
                """, (True,)).fetchone()
                return int(row[0]) if row else None
        except Exception:
            return None

    # ==================== Process Management ====================

    def _find_trading_process(self) -> Optional[int]:
        """Find PID of a live background_trading_manager process."""
        try:
            if self.pid_file.exists():
                pid_text = self.pid_file.read_text(encoding='utf-8').strip()
                if pid_text.isdigit():
                    pid = int(pid_text)
                    if self._is_process_alive(pid):
                        return pid
                    try:
                        self.pid_file.unlink(missing_ok=True)
                    except Exception:
                        pass

            if shutil.which('pgrep'):
                result = subprocess.run(
                    ['pgrep', '-f', 'background_trading_manager.py'],
                    capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid_text in pids:
                        if pid_text.strip().isdigit():
                            pid = int(pid_text.strip())
                            if self._is_process_alive(pid):
                                try:
                                    self.pid_file.parent.mkdir(parents=True, exist_ok=True)
                                    self.pid_file.write_text(str(pid), encoding='utf-8')
                                except Exception:
                                    pass
                                return pid
        except Exception:
            pass
        return None

    def _is_process_alive(self, pid: int) -> bool:
        """Check if a specific PID is alive."""
        try:
            os.kill(pid, 0)
            proc_cmdline = Path(f'/proc/{pid}/cmdline')
            if proc_cmdline.exists():
                try:
                    raw = proc_cmdline.read_bytes()
                    cmdline = raw.decode('utf-8', errors='ignore').replace('\x00', ' ')
                    return 'background_trading_manager.py' in cmdline
                except Exception:
                    return True
            return True
        except OSError:
            return False

    def _start_process(self) -> int:
        """Start the background_trading_manager process."""
        # Kill any lingering processes first
        self._force_kill_all()
        time.sleep(0.3)

        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.project_root)

        # Log process output for debugging
        log_dir = self.project_root / 'logs'
        log_dir.mkdir(exist_ok=True)
        self._stdout_log = open(log_dir / 'trading_process_stdout.log', 'w')
        self._stderr_log = open(log_dir / 'trading_process_stderr.log', 'w')

        process = subprocess.Popen(
            [sys.executable, str(self.project_root / 'bin' / 'background_trading_manager.py'), '--start'],
            cwd=str(self.project_root),
            stdout=self._stdout_log,
            stderr=self._stderr_log,
            start_new_session=True,
            env=env
        )
        try:
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)
            self.pid_file.write_text(str(process.pid), encoding='utf-8')
        except Exception:
            pass
        logger.info(f"📋 Process launched PID={process.pid}, logs → logs/trading_process_*.log")
        return process.pid

    def _close_log_handles(self):
        """Close any open log file handles from _start_process."""
        for attr in ('_stdout_log', '_stderr_log'):
            handle = getattr(self, attr, None)
            if handle and not handle.closed:
                try:
                    handle.close()
                except Exception:
                    pass

    def _stop_all_processes(self):
        """Graceful stop with escalation."""
        self._close_log_handles()
        try:
            subprocess.run(
                ['pkill', '-15', '-f', 'background_trading_manager.py'],
                capture_output=True, timeout=5
            )
            time.sleep(2)

            result = subprocess.run(
                ['pgrep', '-f', 'background_trading_manager.py'],
                capture_output=True, timeout=2
            )
            if result.returncode == 0:
                subprocess.run(
                    ['pkill', '-9', '-f', 'background_trading_manager.py'],
                    capture_output=True, timeout=5
                )
                time.sleep(1)
        except Exception as e:
            logger.warning(f"⚠️ Stop process error: {e}")
        finally:
            try:
                self.pid_file.unlink(missing_ok=True)
            except Exception:
                pass

    def _force_kill_all(self):
        """Force kill all trading processes immediately."""
        try:
            subprocess.run(
                ['pkill', '-9', '-f', 'background_trading_manager.py'],
                capture_output=True, timeout=5
            )
            subprocess.run(
                ['pkill', '-9', '-f', 'group_b_system.py'],
                capture_output=True, timeout=5
            )
        except Exception:
            pass

        # Clean PID files
        try:
            for pid_file in (self.project_root / 'tmp').glob('*.pid'):
                pid_file.unlink(missing_ok=True)
        except Exception:
            pass

    # ==================== Helpers ====================

    def _count_open_positions(self) -> int:
        """Count open/active positions in DB."""
        try:
            with self.db.get_connection() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM active_positions WHERE is_active = TRUE"
                ).fetchone()
                return row[0] if row else 0
        except Exception:
            return 0

    def _get_subsystem_status(self) -> Dict:
        """Read subsystem status from DB (system_status + activity_logs)."""
        try:
            # استخدام StateManager للقراءة من DB
            from backend.core.state_manager import get_state_manager
            state_mgr = get_state_manager()
            data = state_mgr.read_state()
            
            activity = data.get('activity', {})
            heartbeat = data.get('heartbeat', {})

            result = {}
            # Group B
            gb = activity.get('group_b', {})
            if gb:
                last_act = gb.get('last_activity')
                seconds_ago = None
                if last_act:
                    try:
                        seconds_ago = int((datetime.now() - datetime.fromisoformat(last_act)).total_seconds())
                    except Exception:
                        pass
                result['group_b'] = {
                    'status': 'active' if (seconds_ago is not None and seconds_ago < 120) else 'idle',
                    'last_activity': last_act,
                    'seconds_ago': seconds_ago,
                    'total_cycles': gb.get('total_cycles', 0),
                    'active_trades': gb.get('active_trades', 0),
                }

            # ML
            ml = activity.get('ml', {})
            if ml:
                last_act = ml.get('last_activity')
                seconds_ago = None
                if last_act:
                    try:
                        seconds_ago = int((datetime.now() - datetime.fromisoformat(last_act)).total_seconds())
                    except Exception:
                        pass
                result['ml'] = {
                    'status': 'active' if (seconds_ago is not None and seconds_ago < 300) else 'idle',
                    'last_activity': last_act,
                    'seconds_ago': seconds_ago,
                    'total_samples': ml.get('total_samples', 0),
                }

            # Heartbeat
            if heartbeat.get('last_beat'):
                try:
                    hb_seconds = int((datetime.now() - datetime.fromisoformat(heartbeat['last_beat'])).total_seconds())
                    result['heartbeat'] = {
                        'seconds_ago': hb_seconds,
                        'status': 'healthy' if hb_seconds < 30 else 'warning' if hb_seconds < 60 else 'critical',
                    }
                except Exception:
                    pass

            return result
        except Exception:
            pass
        return {}

    def _format_uptime(self, seconds: int) -> str:
        """Format uptime for display."""
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
        return f"{seconds} ثانية"

    def _log_transition(self, from_state: str, to_state: str,
                        initiated_by: str, session_id: Optional[str],
                        reason: str):
        """Log state transition to audit trail."""
        try:
            log_dir = self.project_root / 'logs' / 'audit'
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / 'trading_state_transitions.jsonl'

            entry = {
                'timestamp': datetime.now().isoformat(),
                'from_state': from_state,
                'to_state': to_state,
                'initiated_by': initiated_by,
                'session_id': session_id,
                'reason': reason,
            }

            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')

            logger.info(f"📋 State: {from_state} → {to_state} | by={initiated_by} | {reason}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to log transition: {e}")

    def _default_state(self) -> Dict[str, Any]:
        return {
            'success': True,
            'trading_state': STOPPED,
            'trading_state_label': STATE_LABELS[STOPPED],
            'session_id': None,
            'mode': 'PAPER',
            'initiated_by': None,
            'open_positions': 0,
            'pid': None,
            'uptime': 0,
            'uptime_formatted': None,
            'started_at': None,
            'message': 'النظام متوقف',
            'last_update': datetime.now().isoformat(),
            'error_count': 0,
            'last_error': None,
            'subsystems': {},
            'reconcile_stats': self.reconcile_stats,
        }


# ==================== Singleton ====================

_instance = None

def get_trading_state_machine() -> TradingStateMachine:
    global _instance
    if _instance is None:
        _instance = TradingStateMachine()
    return _instance
