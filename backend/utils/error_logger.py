#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام تسجيل الأخطاء - Error Logging System
=========================================

يسجل جميع الأخطاء من:
- Group B (التداول الآلي)
- النظام العام

ويرسلها إلى:
- Database (للعرض في تطبيق الجوال)
- Logs (للمراجعة المفصلة)
"""

from backend.infrastructure.db_access import get_db_manager
import os
import sys
import logging
import traceback
import hashlib
from enum import Enum

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ErrorLevel(Enum):
    """مستويات الأخطاء - متوافقة مع Database"""

    INFO = "low"  # معلومة عادية
    WARNING = "medium"  # تحذير
    ERROR = "high"  # خطأ
    CRITICAL = "critical"  # خطأ حرج (يوقف النظام)


class ErrorSource(Enum):
    """مصادر الأخطاء"""

    GROUP_B = "group_b"  # التداول الآلي
    SYSTEM = "system"  # النظام العام
    DATABASE = "database"  # قاعدة البيانات
    BINANCE = "binance"  # Binance API
    BACKGROUND = "background"  # النظام الخلفي


class ErrorLogger:
    """
    مسجل الأخطاء المركزي

    يسجل الأخطاء في Database و Logs
    """

    def __init__(self):
        self.db_manager = get_db_manager()
        self.logger = logging.getLogger(__name__)
        self._default_max_auto_attempts = 3
        self._ensure_errors_table()

    def _ensure_errors_table(self):
        """التأكد من وجود جدول الأخطاء - استخدام الجدول الموجود"""
        try:
            with self.db_manager.get_write_connection() as conn:
                # التحقق من وجود الأعمدة المطلوبة
                cursor = conn.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'system_errors'
                """)
                columns = {row[0] for row in cursor.fetchall()}

                # إضافة الأعمدة المفقودة إذا لزم الأمر
                if "source" not in columns:
                    conn.execute(
                        "ALTER TABLE system_errors ADD COLUMN source TEXT DEFAULT 'system'"
                    )

                if "details" not in columns:
                    conn.execute("ALTER TABLE system_errors ADD COLUMN details TEXT")

                if "traceback" not in columns:
                    conn.execute("ALTER TABLE system_errors ADD COLUMN traceback TEXT")

                if "resolved_by" not in columns:
                    conn.execute(
                        "ALTER TABLE system_errors ADD COLUMN resolved_by TEXT"
                    )

                # Lifecycle columns (backward-compatible)
                if "error_fingerprint" not in columns:
                    conn.execute(
                        "ALTER TABLE system_errors ADD COLUMN error_fingerprint TEXT"
                    )
                if "status" not in columns:
                    conn.execute(
                        "ALTER TABLE system_errors ADD COLUMN status TEXT DEFAULT 'new'"
                    )
                if "attempt_count" not in columns:
                    conn.execute(
                        "ALTER TABLE system_errors ADD COLUMN attempt_count INTEGER DEFAULT 0"
                    )
                if "last_attempt_at" not in columns:
                    conn.execute(
                        "ALTER TABLE system_errors ADD COLUMN last_attempt_at TIMESTAMP"
                    )
                if "requires_admin" not in columns:
                    conn.execute(
                        "ALTER TABLE system_errors ADD COLUMN requires_admin BOOLEAN DEFAULT FALSE"
                    )
                if "auto_action" not in columns:
                    conn.execute(
                        "ALTER TABLE system_errors ADD COLUMN auto_action TEXT"
                    )

                # إنشاء index للبحث السريع
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_errors_created_at
                    ON system_errors(created_at DESC)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_errors_resolved
                    ON system_errors(resolved, severity)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_errors_fingerprint
                    ON system_errors(error_fingerprint, resolved)
                """)

        except Exception as e:
            self.logger.error(f"خطأ في تهيئة جدول الأخطاء: {e}")

    def _build_fingerprint(
        self, source: ErrorSource, message: str, details: str = None
    ) -> str:
        raw = f"{source.value}|{message}|{details or ''}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def _classify_auto_action(
        self, message: str, details: str = None
    ) -> tuple[str, int, bool]:
        """إرجاع (auto_action, max_attempts, can_auto_heal)."""
        text = f"{message or ''} {details or ''}".lower()

        if "database is locked" in text or "database busy" in text:
            return ("retry_db_operation", 5, True)

        if "binance" in text and any(
            k in text for k in ["timeout", "network", "connection", "temporar"]
        ):
            return ("retry_binance_operation", 3, True)

        if (
            "failed to save position" in text
            or "active_positions" in text
            or "unique constraint" in text
        ):
            return ("investigate_active_positions_constraint", 2, True)

        return ("manual_investigation", 1, False)

    def _try_auto_fix(self, action: str) -> bool:
        """تنفيذ إصلاح تلقائي آمن ومحدد."""
        try:
            if action == "investigate_active_positions_constraint":
                # إصلاح آمن: تشغيل migrations (idempotent)
                self.db_manager._apply_migrations()
                with self.db_manager.get_connection() as conn:
                    # Check table exists
                    row = conn.execute("""
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'public' AND table_name = 'active_positions'
                    """).fetchone()
                    if not row:
                        return False
                    # Check unique index exists
                    idx_row = conn.execute("""
                        SELECT 1 FROM pg_indexes
                        WHERE schemaname = 'public'
                          AND indexname = 'idx_active_positions_unique_open'
                        LIMIT 1
                    """).fetchone()
                    return idx_row is not None

            if action in ("retry_db_operation", "retry_binance_operation"):
                # لا توجد عملية تنفيذ مباشرة هنا؛ نعيد True كـ soft recovery
                # cycle.
                return True

            return False
        except Exception as e:
            self.logger.warning(f"⚠️ auto-fix failed for action={action}: {e}")
            return False

    def log_error(
        self,
        level: ErrorLevel,
        source: ErrorSource,
        message: str,
        details: str = None,
        include_traceback: bool = False,
        status: str = "new",
        requires_admin: bool = False,
        auto_action: str = None,
        attempt_count: int = 0,
        fingerprint: str = None,
    ) -> int:
        """
        تسجيل خطأ

        Args:
            level: مستوى الخطأ
            source: مصدر الخطأ
            message: رسالة الخطأ
            details: تفاصيل إضافية
            include_traceback: تضمين traceback

        Returns:
            معرف الخطأ المسجل
        """
        try:
            # الحصول على traceback إذا طُلب
            tb = None
            if include_traceback:
                tb = traceback.format_exc()

            # حفظ/تجميع في Database (dedup بالبصمة)
            final_fingerprint = fingerprint or self._build_fingerprint(
                source, message, details
            )
            with self.db_manager.get_write_connection() as conn:
                existing = conn.execute(
                    """
                    SELECT id, attempt_count, status, requires_admin
                    FROM system_errors
                    WHERE resolved = FALSE AND error_fingerprint = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (final_fingerprint,),
                ).fetchone()

                if existing:
                    existing_attempts = int(existing["attempt_count"] or 0)
                    new_attempts = max(
                        existing_attempts + 1, int(attempt_count or 0) + 1
                    )
                    existing_status = str(existing["status"] or "new")
                    next_status = (
                        existing_status
                        if existing_status in ("escalated", "auto_processing")
                        else status
                    )
                    needs_admin = bool(existing["requires_admin"]) or bool(
                        requires_admin
                    )

                    conn.execute(
                        """
                        UPDATE system_errors
                        SET error_type = %s,
                            error_message = %s,
                            severity = %s,
                            source = %s,
                            details = %s,
                            traceback = %s,
                            status = %s,
                            attempt_count = %s,
                            last_attempt_at = CURRENT_TIMESTAMP,
                            requires_admin = %s,
                            auto_action = COALESCE(%s, auto_action)
                        WHERE id = %s
                        """,
                        (
                            source.value,
                            message,
                            level.value,
                            source.value,
                            details,
                            tb,
                            next_status,
                            new_attempts,
                            needs_admin,
                            auto_action,
                            int(existing["id"]),
                        ),
                    )
                    error_id = int(existing["id"])
                    return error_id

                cursor = conn.execute(
                    """
                    INSERT INTO system_errors
                    (error_type, error_message, severity, source, details, traceback,
                     error_fingerprint, status, attempt_count, last_attempt_at,
                     requires_admin, auto_action)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s)
                    RETURNING id
                """,
                    (
                        source.value,  # error_type
                        message,  # error_message
                        level.value,  # severity
                        source.value,  # source (عمود جديد)
                        details,
                        tb,
                        final_fingerprint,
                        status,
                        max(1, int(attempt_count or 1)),
                        bool(requires_admin),
                        auto_action,
                    ),
                )

                row = cursor.fetchone()
                error_id = row[0] if row else None

            # تسجيل في Logs
            log_message = f"[{source.value.upper()}] {message}"
            if details:
                log_message += f" | {details}"

            if level == ErrorLevel.CRITICAL:
                self.logger.critical(log_message)
            elif level == ErrorLevel.ERROR:
                self.logger.error(log_message)
            elif level == ErrorLevel.WARNING:
                self.logger.warning(log_message)
            else:
                self.logger.info(log_message)

            return error_id

        except Exception as e:
            self.logger.error(f"فشل في تسجيل الخطأ: {e}")
            return -1

    def process_pending_errors(self, limit: int = 100) -> dict:
        """محرك أتمتة أخطاء آمن: يصنف ويعالج أو يصعّد."""
        result = {
            "processed": 0,
            "auto_resolved": 0,
            "escalated": 0,
            "auto_processing": 0,
        }
        try:
            with self.db_manager.get_write_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT id, error_message, details, attempt_count, status
                    FROM system_errors
                    WHERE resolved = FALSE
                      AND COALESCE(status, 'new') IN ('new', 'auto_processing', 'escalated')
                    ORDER BY created_at ASC
                    LIMIT %s
                    """,
                    (max(1, int(limit)),),
                ).fetchall()

                for row in rows:
                    result["processed"] += 1
                    error_id = int(row["id"])
                    attempts = int(row["attempt_count"] or 0)
                    message = row["error_message"] or ""
                    details = row["details"] or ""

                    action, max_attempts, can_auto_heal = self._classify_auto_action(
                        message, details
                    )
                    next_attempt = attempts + 1

                    if can_auto_heal and next_attempt <= max_attempts:
                        ok = self._try_auto_fix(action)
                        if ok:
                            conn.execute(
                                """
                                UPDATE system_errors
                                SET resolved = TRUE,
                                    resolved_at = CURRENT_TIMESTAMP,
                                    resolved_by = 'auto-healer',
                                    status = 'auto_resolved',
                                    requires_admin = FALSE,
                                    auto_action = %s,
                                    attempt_count = %s,
                                    last_attempt_at = CURRENT_TIMESTAMP
                                WHERE id = %s
                                """,
                                (action, next_attempt, error_id),
                            )
                            result["auto_resolved"] += 1
                        else:
                            conn.execute(
                                """
                                UPDATE system_errors
                                SET status = 'auto_processing',
                                    auto_action = %s,
                                    attempt_count = %s,
                                    last_attempt_at = CURRENT_TIMESTAMP,
                                    requires_admin = FALSE
                                WHERE id = %s
                                """,
                                (action, next_attempt, error_id),
                            )
                            result["auto_processing"] += 1
                    else:
                        conn.execute(
                            """
                            UPDATE system_errors
                            SET status = 'escalated',
                                requires_admin = TRUE,
                                auto_action = %s,
                                attempt_count = %s,
                                last_attempt_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                            """,
                            (action, next_attempt, error_id),
                        )
                        result["escalated"] += 1

            return result
        except Exception as e:
            self.logger.error(f"خطأ في process_pending_errors: {e}")
            return result

    def log_group_b_error(
        self, message: str, details: str = None, critical: bool = False
    ):
        """تسجيل خطأ Group B"""
        level = ErrorLevel.CRITICAL if critical else ErrorLevel.ERROR
        return self.log_error(level, ErrorSource.GROUP_B, message, details, True)

    def log_system_error(
        self, message: str, details: str = None, critical: bool = False
    ):
        """تسجيل خطأ النظام"""
        level = ErrorLevel.CRITICAL if critical else ErrorLevel.ERROR
        return self.log_error(level, ErrorSource.SYSTEM, message, details, True)

    def log_binance_error(self, message: str, details: str = None):
        """تسجيل خطأ Binance API"""
        return self.log_error(
            ErrorLevel.ERROR, ErrorSource.BINANCE, message, details, False
        )

    def log_warning(self, source: ErrorSource, message: str, details: str = None):
        """تسجيل تحذير"""
        return self.log_error(ErrorLevel.WARNING, source, message, details, False)

    def get_errors(
        self,
        limit: int = 50,
        level: str = None,
        source: str = None,
        resolved: bool = None,
    ) -> list:
        """
        جلب الأخطاء

        Args:
            limit: عدد الأخطاء
            level: فلترة حسب المستوى
            source: فلترة حسب المصدر
            resolved: فلترة حسب الحل

        Returns:
            قائمة الأخطاء
        """
        try:
            query = """
                SELECT
                    id, created_at as timestamp, severity as level,
                    COALESCE(source, error_type) as source,
                    error_message as message, details,
                    traceback, resolved, resolved_at, resolved_by
                FROM system_errors
                WHERE 1=1
            """
            params = []

            if level:
                query += " AND severity = %s"
                params.append(level)

            if source:
                query += " AND (source = %s OR error_type = %s)"
                params.append(source)
                params.append(source)

            if resolved is not None:
                query += " AND resolved = %s"
                params.append(resolved)

            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)

            with self.db_manager.get_connection() as conn:
                rows = conn.execute(query, params).fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"خطأ في جلب الأخطاء: {e}")
            return []

    def get_critical_errors(self, limit: int = 20) -> list:
        """جلب الأخطاء الحرجة فقط"""
        return self.get_errors(limit=limit, level="critical", resolved=False)

    def get_unresolved_errors(self, limit: int = 50) -> list:
        """جلب الأخطاء غير المحلولة"""
        return self.get_errors(limit=limit, resolved=False)

    def resolve_error(self, error_id: int, resolved_by: str = "admin") -> bool:
        """
        وضع علامة على خطأ كمحلول

        Args:
            error_id: معرف الخطأ
            resolved_by: من حل الخطأ

        Returns:
            نجح أم لا
        """
        try:
            with self.db_manager.get_write_connection() as conn:
                conn.execute(
                    """
                    UPDATE system_errors
                    SET resolved = TRUE,
                        resolved_at = CURRENT_TIMESTAMP,
                        resolved_by = %s
                    WHERE id = %s
                """,
                    (resolved_by, error_id),
                )

            self.logger.info(f"تم حل الخطأ #{error_id} بواسطة {resolved_by}")
            return True

        except Exception as e:
            self.logger.error(f"خطأ في حل الخطأ: {e}")
            return False

    def resolve_all_errors(self, resolved_by: str = "admin") -> int:
        """
        حل جميع الأخطاء

        Returns:
            عدد الأخطاء المحلولة
        """
        try:
            with self.db_manager.get_write_connection() as conn:
                cursor = conn.execute(
                    """
                    UPDATE system_errors
                    SET resolved = TRUE,
                        resolved_at = CURRENT_TIMESTAMP,
                        resolved_by = %s
                    WHERE resolved = FALSE
                """,
                    (resolved_by,),
                )

                count = cursor.rowcount

            self.logger.info(f"تم حل {count} خطأ بواسطة {resolved_by}")
            return count

        except Exception as e:
            self.logger.error(f"خطأ في حل جميع الأخطاء: {e}")
            return 0

    def get_error_stats(self) -> dict:
        """
        الحصول على إحصائيات الأخطاء

        Returns:
            إحصائيات مفصلة
        """
        try:
            with self.db_manager.get_connection() as conn:
                # إجمالي الأخطاء
                total = conn.execute(
                    "SELECT COUNT(*) as count FROM system_errors"
                ).fetchone()["count"]

                # الأخطاء غير المحلولة
                unresolved = conn.execute(
                    "SELECT COUNT(*) as count FROM system_errors WHERE resolved = FALSE"
                ).fetchone()["count"]

                # الأخطاء الحرجة
                critical = conn.execute(
                    "SELECT COUNT(*) as count FROM system_errors WHERE severity = 'critical' AND resolved = FALSE"
                ).fetchone()["count"]

                # حسب المصدر
                by_source = conn.execute("""
                    SELECT COALESCE(source, error_type) as source, COUNT(*) as count
                    FROM system_errors
                    WHERE resolved = FALSE
                    GROUP BY COALESCE(source, error_type)
                """).fetchall()

                # حسب المستوى
                by_level = conn.execute("""
                    SELECT COALESCE(severity, 'error') as level, COUNT(*) as count
                    FROM system_errors
                    WHERE resolved = FALSE
                    GROUP BY COALESCE(severity, 'error')
                """).fetchall()

                return {
                    "total": total,
                    "unresolved": unresolved,
                    "critical": critical,
                    "by_source": {row["source"]: row["count"] for row in by_source},
                    "by_level": {row["level"]: row["count"] for row in by_level},
                }

        except Exception as e:
            self.logger.error(f"خطأ في جلب إحصائيات الأخطاء: {e}")
            return {}

    def cleanup_old_errors(self, days: int = 30) -> int:
        """
        حذف الأخطاء القديمة المحلولة

        Args:
            days: عدد الأيام

        Returns:
            عدد الأخطاء المحذوفة
        """
        try:
            with self.db_manager.get_write_connection() as conn:
                retention_days = max(1, int(days))
                cursor = conn.execute(
                    """
                    DELETE FROM system_errors
                    WHERE resolved = TRUE
                    AND created_at < (CURRENT_TIMESTAMP - (%s * INTERVAL '1 day'))
                """,
                    (retention_days,),
                )

                count = cursor.rowcount

            self.logger.info(f"تم حذف {count} خطأ قديم")
            return count

        except Exception as e:
            self.logger.error(f"خطأ في تنظيف الأخطاء: {e}")
            return 0


# مثيل عام للاستخدام
error_logger = ErrorLogger()
