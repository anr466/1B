#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Unified State Manager - مدير الحالة الموحد
================================================

Single Source of Truth لحالة النظام — DATABASE ONLY
- NO JSON files (follows system philosophy)
- Uses system_status table in DB
- Atomic writes via DB transactions
- Audit trail in activity_logs
- Thread-safe

Author: System Unification Team
Date: 2026-02-21 (Refactored to DB-only)
"""

import json
import threading
from datetime import datetime
from typing import Dict, Any, Optional

from backend.infrastructure.db_access import get_db_manager


class StateManager:
    """
    مدير الحالة الموحد - DATABASE ONLY (تطبيق الفلسفة)

    Features:
    - Database storage (system_status table)
    - Atomic writes (DB transactions)
    - Thread-safe operations
    - Audit trail in activity_logs
    - State validation
    """

    def __init__(self, db_manager=None):
        """
        Args:
            db_manager: DatabaseManager instance (optional, will create if needed)
        """
        self.lock = threading.RLock()

        if db_manager is None:
            self.db = get_db_manager()
        else:
            self.db = db_manager

    def read_state(self) -> Dict[str, Any]:
        """
        قراءة الحالة من DB (system_status table)

        Returns:
            dict: الحالة الحالية
        """
        with self.lock:
            try:
                with self.db.get_connection() as conn:
                    row = conn.execute("""
                        SELECT trading_state, mode, session_id, started_at,
                               is_running, status, message, pid, subsystem_status
                        FROM system_status WHERE id=1
                    """).fetchone()

                    if row:
                        subsystem_data = {}
                        raw_subsystem_status = row[8]
                        if raw_subsystem_status:
                            try:
                                subsystem_data = json.loads(
                                    raw_subsystem_status
                                )
                                if not isinstance(subsystem_data, dict):
                                    subsystem_data = {}
                            except Exception:
                                subsystem_data = {}

                        state = {
                            "trading_state": row[0],
                            "mode": row[1],
                            "session_id": row[2],
                            "started_at": row[3],
                            "is_running": bool(row[4]),
                            "status": row[5],
                            "message": row[6],
                            "activity": subsystem_data.get("activity", {}),
                            "heartbeat": subsystem_data.get("heartbeat", {}),
                            "updated_at": datetime.now().isoformat(),
                            "pid": row[7],
                        }
                        return self._validate_state(state)
                    else:
                        return self._get_default_state()
            except Exception as e:
                print(f"⚠️ خطأ في قراءة الحالة من DB: {e}")
                return self._get_default_state()

    def write_state(
        self, state_data: Dict[str, Any], user: Optional[str] = None
    ) -> bool:
        """
        كتابة الحالة في DB (atomic via transaction)

        Args:
            state_data: البيانات الجديدة
            user: المستخدم الذي قام بالتغيير (optional)

        Returns:
            bool: True if successful
        """
        with self.lock:
            # Get old state for audit
            old_state = self.read_state()
            merged_state = dict(old_state)

            for key, value in (state_data or {}).items():
                if key in {"activity", "heartbeat"} and isinstance(
                    value, dict
                ):
                    current_value = merged_state.get(key, {})
                    merged_value = (
                        dict(current_value)
                        if isinstance(current_value, dict)
                        else {}
                    )
                    for nested_key, nested_value in value.items():
                        if isinstance(nested_value, dict) and isinstance(
                            merged_value.get(nested_key), dict
                        ):
                            nested_merged = dict(merged_value[nested_key])
                            nested_merged.update(nested_value)
                            merged_value[nested_key] = nested_merged
                        else:
                            merged_value[nested_key] = nested_value
                    merged_state[key] = merged_value
                else:
                    merged_state[key] = value

            # Validate merged state so partial updates never wipe monitoring
            # data
            state_data = self._validate_state(merged_state)

            try:
                with self.db.get_write_connection() as conn:
                    # Update system_status table
                    subsystem_status = json.dumps(
                        {
                            "activity": state_data.get("activity", {}),
                            "heartbeat": state_data.get("heartbeat", {}),
                        },
                        ensure_ascii=False,
                        default=str,
                    )

                    conn.execute(
                        """
                        UPDATE system_status SET
                            trading_state = %s,
                            mode = %s,
                            session_id = %s,
                            started_at = %s,
                            is_running = %s,
                            status = %s,
                            message = %s,
                            pid = %s,
                            subsystem_status = %s,
                            last_update = CURRENT_TIMESTAMP
                        WHERE id = 1
                    """,
                        (
                            state_data.get("trading_state"),
                            state_data.get("mode"),
                            state_data.get("session_id"),
                            state_data.get("started_at"),
                            bool(state_data.get("is_running")),
                            state_data.get("status"),
                            state_data.get("message"),
                            state_data.get("pid"),
                            subsystem_status,
                        ),
                    )

                    conn.commit()

                # Log to audit trail in DB
                self._log_audit(old_state, state_data, user)

                return True

            except Exception as e:
                print(f"❌ فشل كتابة الحالة في DB: {e}")
                return False

    def update_state(self, **kwargs) -> bool:
        """
        تحديث حقول محددة في الحالة

        Args:
            **kwargs: الحقول المراد تحديثها

        Returns:
            bool: True if successful
        """
        state = self.read_state()
        state.update(kwargs)
        return self.write_state(state)

    def send_heartbeat(self) -> bool:
        """
        إرسال نبضة (heartbeat) لإثبات أن النظام حي

        Returns:
            bool: True if successful
        """
        state = self.read_state()
        if "heartbeat" not in state:
            state["heartbeat"] = {
                "last_beat": None,
                "beats_count": 0,
                "missed_beats": 0,
            }

        state["heartbeat"]["last_beat"] = datetime.now().isoformat()
        state["heartbeat"]["beats_count"] = (
            state["heartbeat"].get("beats_count", 0) + 1
        )
        state["heartbeat"]["missed_beats"] = 0  # Reset missed beats

        return self.write_state(state, user="heartbeat")

    def update_activity(self, component: str, **kwargs) -> bool:
        """
        تحديث آخر نشاط لمكون معين

        Args:
            component: اسم المكون (group_b, ml)
            **kwargs: البيانات المراد تحديثها

        Returns:
            bool: True if successful
        """
        state = self.read_state()
        if "activity" not in state:
            state["activity"] = {}
        if component not in state["activity"]:
            state["activity"][component] = {}

        # Update last_activity timestamp
        state["activity"][component][
            "last_activity"
        ] = datetime.now().isoformat()

        # Update other fields
        state["activity"][component].update(kwargs)

        return self.write_state(state, user=f"{component}_activity")

    def get_seconds_since_heartbeat(self) -> Optional[int]:
        """
        حساب عدد الثواني منذ آخر نبضة

        Returns:
            int: عدد الثواني، أو None إذا لم توجد نبضة
        """
        state = self.read_state()
        last_beat = state.get("heartbeat", {}).get("last_beat")

        if not last_beat:
            return None

        try:
            last_beat_time = datetime.fromisoformat(last_beat)
            delta = datetime.now() - last_beat_time
            return int(delta.total_seconds())
        except Exception:
            return None

    def get_seconds_since_activity(self, component: str) -> Optional[int]:
        """
        حساب عدد الثواني منذ آخر نشاط لمكون

        Args:
            component: اسم المكون (group_b, ml)

        Returns:
            int: عدد الثواني، أو None إذا لم يوجد نشاط
        """
        state = self.read_state()
        last_activity = (
            state.get("activity", {}).get(component, {}).get("last_activity")
        )

        if not last_activity:
            return None

        try:
            last_activity_time = datetime.fromisoformat(last_activity)
            delta = datetime.now() - last_activity_time
            return int(delta.total_seconds())
        except Exception:
            return None

    def reset_monitoring_data(self):
        """
        تصفير بيانات المراقبة عند بدء تشغيل جديد

        يتم استدعاؤها عند start_system() لضمان بدء نظيف
        """
        state = self.read_state()

        # تصفير heartbeat
        state["heartbeat"] = {
            "last_beat": None,
            "beats_count": 0,
            "missed_beats": 0,
        }

        # تصفير activity لجميع المكونات
        state["activity"] = {
            "group_b": {
                "last_activity": None,
                "last_cycle": None,
                "total_cycles": 0,
                "active_trades": 0,
            },
            "ml": {"last_activity": None, "total_samples": 0},
        }

        # تحديث الحالة
        return self.write_state(state, user="system_start")

    def _get_default_state(self) -> Dict[str, Any]:
        """الحالة الافتراضية"""
        return {
            "status": "stopped",
            "is_running": False,
            "pid": None,
            "started_at": None,
            "uptime": 0,
            "message": "النظام متوقف",
            "updated_at": datetime.now().isoformat(),
            "version": "2.0.0",  # Unified version
            # ===== Live Monitoring =====
            "heartbeat": {
                "last_beat": None,
                "beats_count": 0,
                "missed_beats": 0,
            },
            "activity": {
                "group_b": {
                    "last_activity": None,
                    "last_cycle": None,
                    "total_cycles": 0,
                    "active_trades": 0,
                },
                "ml": {"last_activity": None, "total_samples": 0},
            },
        }

    def _validate_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        التحقق من وتصحيح الحالة

        Args:
            state: الحالة المراد التحقق منها

        Returns:
            dict: الحالة المُحققة
        """
        default = self._get_default_state()

        # Ensure required fields exist
        for key, value in default.items():
            if key not in state:
                state[key] = value

        # Validate status values
        valid_statuses = [
            "stopped",
            "starting",
            "running",
            "stopping",
            "error",
        ]
        if state.get("status") not in valid_statuses:
            state["status"] = "stopped"

        # Ensure is_running matches status
        state["is_running"] = state["status"] in ["starting", "running"]

        return state

    def _log_audit(
        self, old_state: Dict, new_state: Dict, user: Optional[str] = None
    ):
        """
        تسجيل التغيير في audit trail (DB: activity_logs table)

        Args:
            old_state: الحالة القديمة
            new_state: الحالة الجديدة
            user: المستخدم (optional)
        """
        try:
            changes = self._get_changes(old_state, new_state)
            if not changes:
                return  # No changes to log

            details = json.dumps(
                {
                    "old_status": old_state.get("status", "unknown"),
                    "new_status": new_state.get("status"),
                    "changes": changes,
                },
                ensure_ascii=False,
                default=str,
            )

            # Log to activity_logs table in DB
            with self.db.get_write_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO activity_logs (action, details, created_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                """,
                    ("state_change", details),
                )
                conn.commit()

        except Exception as e:
            print(f"⚠️ فشل تسجيل audit في DB: {e}")

    def _get_changes(self, old: Dict, new: Dict) -> Dict:
        """استخراج التغييرات بين الحالتين"""
        changes = {}
        for key in set(old.keys()) | set(new.keys()):
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val != new_val:
                changes[key] = {"old": old_val, "new": new_val}
        return changes

    def get_audit_trail(self, limit: int = 100) -> list:
        """
        جلب آخر التغييرات من audit trail (DB: activity_logs)

        Args:
            limit: عدد السجلات المراد جلبها

        Returns:
            list: قائمة السجلات
        """
        try:
            with self.db.get_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT created_at, action, details
                    FROM activity_logs
                    WHERE action = 'state_change'
                    ORDER BY created_at DESC
                    LIMIT %s
                """,
                    (limit,),
                ).fetchall()

                entries = []
                for row in rows:
                    try:
                        details = json.loads(row[2]) if row[2] else {}
                        entries.append(
                            {"timestamp": row[0], "action": row[1], **details}
                        )
                    except Exception:
                        continue

                return entries

        except Exception as e:
            print(f"⚠️ فشل قراءة audit trail من DB: {e}")
            return []


# Global instance للاستخدام السريع
_state_manager_instance = None


def get_state_manager() -> StateManager:
    """Get or create global StateManager instance"""
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = StateManager()
    return _state_manager_instance


if __name__ == "__main__":
    # اختبار سريع
    print("🧪 اختبار StateManager...")

    sm = StateManager("tmp/test_state.json")

    # Test write
    print("\n1️⃣ كتابة حالة جديدة...")
    sm.write_state({"status": "running", "pid": 12345}, user="test_user")

    # Test read
    print("2️⃣ قراءة الحالة...")
    state = sm.read_state()
    print(f"   الحالة: {state}")

    # Test update
    print("3️⃣ تحديث الحالة...")
    sm.update_state(message="اختبار ناجح")

    # Test audit trail
    print("4️⃣ Audit trail:")
    for entry in sm.get_audit_trail(limit=5):
        print(f"   {
            entry['timestamp']}: {
            entry['old_status']} → {
            entry['new_status']}")

    print("\n✅ الاختبار ناجح!")
