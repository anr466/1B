#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام إدارة التداول الخلفي - Background Trading Manager
=======================================================

المسؤوليات:
1. ✅ إزالة Group A - تم دمج وظائفه في Group B
2. إدارة Group B: التداول الآلي (كل 60 ثانية)
3. التحكم من تطبيق الجوال (الأدمن فقط)
4. مراقبة الحالة والأخطاء
5. إيقاف طوارئ سريع

الاستخدام:
---------
python3 background_trading_manager.py --start
python3 background_trading_manager.py --stop
python3 background_trading_manager.py --status
"""

import os
import sys
import time
import signal
import logging
import argparse
import json
from datetime import datetime, timedelta
from threading import Thread, Event
from pathlib import Path

# إضافة المسار الأساسي
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.infrastructure.db_access import get_db_manager
from backend.core.group_b_system import GroupBSystem
from backend.utils.error_logger import error_logger, ErrorSource
from backend.utils.trading_context import get_effective_is_demo

# استيراد نظام مراقبة الصحة والتعافي التلقائي
try:
    from backend.utils.system_health_monitor import (
        get_health_monitor,
        setup_database_health_check,
        HealthStatus,
    )

    HEALTH_MONITOR_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    HEALTH_MONITOR_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("⚠️ نظام مراقبة الصحة غير متاح")

# استيراد مدير الاتصالات (اختياري)
try:
    from backend.utils.connection_manager import (
        get_connection_manager,
        ConnectionConfig,
    )

    CONNECTION_MANAGER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    CONNECTION_MANAGER_AVAILABLE = False

    def get_connection_manager():
        return None


# ✅ إزالة Group A - Group B يحتوي على جميع الوظائف
GROUP_A_AVAILABLE = False

# ✅ SK-1 FIX: Process Lock لمنع التشغيل المزدوج
try:
    from backend.utils.process_lock import (
        get_process_lock,
        acquire_system_lock,
        release_system_lock,
    )

    PROCESS_LOCK_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    PROCESS_LOCK_AVAILABLE = False

    def get_process_lock(name="trading_bot"):
        return None

    def acquire_system_lock(force=False):
        return True, "Lock not available"

    def release_system_lock():
        return True, "Lock not available"


# ✅ Audit Logger للتتبع الكامل
try:
    from backend.utils.audit_logger import audit_logger

    AUDIT_LOGGER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    AUDIT_LOGGER_AVAILABLE = False
    audit_logger = None

# إعداد المسجل الموحد
from config.logging_config import get_logger

logger = get_logger(__name__)


class BackgroundTradingManager:
    """
    مدير النظام الخلفي للتداول

    يدير:
    - ✅ Group B فقط: التداول الآلي مع اختيار العملات (كل 60 ثانية)
    - التحكم من الجوال
    """

    def __init__(self):
        self.db_manager = get_db_manager()
        self.is_running = False
        self.stop_event = Event()

        # ✅ إزالة Group A - Group B يحتوي على جميع الوظائف
        self.group_b_thread = None
        self.heartbeat_thread = None

        # إعدادات التشغيل
        self.group_b_interval = 60  # 60 ثانية
        self.heartbeat_interval = 15  # 15 ثانية

        # آخر تشغيل
        self.last_group_b_run = None

        # ✅ عدادات الدورات (تبدأ من صفر عند كل تشغيل)
        self._group_b_cycles = 0

        # ✅ FIX: Cache لأنظمة التداول لكل مستخدم
        # بدلاً من إنشاء GroupBSystem جديد كل 60 ثانية (يصفّر daily_state)
        # نحتفظ بنسخة واحدة لكل مستخدم طوال عمر العملية
        self._user_systems = {}  # {user_id: GroupBSystem}
        self._user_context_fingerprints = {}  # {user_id: str}

        # StateManager للمراقبة الحية
        try:
            from backend.core.state_manager import get_state_manager

            self.state_manager = get_state_manager()
        except Exception as e:
            self.state_manager = None
            logger.warning(f"⚠️ StateManager غير متاح - المراقبة الحية معطلة: {e}")

        # ✅ تنظيف السجلات القديمة عند البدء
        self._cleanup_old_logs()

        # ✅ تهيئة نظام مراقبة الصحة
        self._setup_health_monitoring()

        logger.info("✅ تم تهيئة مدير التداول الخلفي")

    def _setup_health_monitoring(self):
        """تهيئة نظام مراقبة الصحة والتعافي التلقائي"""
        if not HEALTH_MONITOR_AVAILABLE:
            logger.warning("⚠️ نظام مراقبة الصحة غير متاح")
            return

        try:
            # إعداد مراقب الصحة
            health_monitor = get_health_monitor()

            # إعداد فحص صحة قاعدة البيانات
            setup_database_health_check(self.db_manager)

            # إعداد مدير الاتصالات
            conn_manager = get_connection_manager()

            # ✅ إزالة Group A - Group B يحتوي على جميع الوظائف
            # لا يوجد recovery handlers للـ Group A
            health_monitor.recovery_handlers["group_b"] = self._recover_group_b
            health_monitor.recovery_handlers["background_manager"] = self._recover_self

            # تسجيل فاحصات الصحة
            # ✅ إزالة Group A - Group B يحتوي على جميع الوظائف
            health_monitor.health_checkers["group_b"] = self._check_group_b_health
            health_monitor.health_checkers["background_manager"] = (
                self._check_self_health
            )

            # ✅ FIX GAP 1+2: تشغيل Binance health-check loop + تسجيله في SystemHealthMonitor
            # بدونه: لا يوجد ping دوري → لا reconnect تلقائي → binance_api = UNKNOWN دائماً
            try:
                from backend.core.binance_connector import get_binance_connector
                from backend.utils.system_health_monitor import (
                    setup_binance_health_check,
                )

                bc = get_binance_connector()
                bc.start_health_check()  # 30s ping loop مع auto-reconnect + endpoint failover
                setup_binance_health_check(
                    bc
                )  # يسجّل binance_api في SystemHealthMonitor
                logger.info("✅ تم تهيئة Binance health-check loop (كل 30 ثانية)")
            except Exception as _binance_hc_err:
                logger.warning(f"⚠️ فشل تهيئة Binance health-check: {_binance_hc_err}")

            logger.info("✅ تم تهيئة نظام مراقبة الصحة والتعافي التلقائي")

        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة نظام مراقبة الصحة: {e}")

    # ✅ إزالة Group A - Group B يحتوي على جميع الوظائف

    def _check_group_b_health(self) -> bool:
        """فحص صحة Group B"""
        if not self.group_b_thread:
            return False
        return self.group_b_thread.is_alive()

    def _check_self_health(self) -> bool:
        """فحص صحة المدير نفسه"""
        return self.is_running

    def _recover_group_b(self) -> bool:
        """محاولة تعافي Group B"""
        try:
            logger.info("🔄 محاولة تعافي Group B...")

            if self.group_b_thread and self.group_b_thread.is_alive():
                return True  # يعمل بالفعل

            # إعادة تشغيل الخيط
            self.group_b_thread = Thread(target=self._run_group_b_loop, daemon=False)
            self.group_b_thread.start()

            logger.info("✅ تم تعافي Group B بنجاح")
            return True

        except Exception as e:
            logger.error(f"❌ فشل تعافي Group B: {e}")
            return False

    def _recover_self(self) -> bool:
        """محاولة تعافي المدير نفسه"""
        try:
            logger.info("🔄 محاولة تعافي Background Manager...")

            # إعادة تشغيل الخيوط المتوقفة
            recovered = True

            # ✅ إزالة Group A - Group B يحتوي على جميع الوظائف
            # لا يوجد Group A للتعافي

            if not self._check_group_b_health():
                recovered = self._recover_group_b() and recovered

            if recovered:
                self.is_running = True
                self._update_system_status("running", "تم التعافي التلقائي")
                logger.info("✅ تم تعافي Background Manager بنجاح")

            return recovered

        except Exception as e:
            logger.error(f"❌ فشل تعافي Background Manager: {e}")
            return False

    def start(self):
        """بدء النظام الخلفي"""
        if self.is_running:
            logger.warning("⚠️ النظام يعمل بالفعل")
            return False

        try:
            # ✅ SK-1 FIX: الحصول على Process Lock أولاً
            if PROCESS_LOCK_AVAILABLE:
                success, message = acquire_system_lock()
                if not success:
                    logger.error(f"❌ فشل الحصول على Process Lock: {message}")
                    return False
                logger.info(f"🔒 {message}")

            logger.info("=" * 80)
            logger.info("🚀 بدء نظام التداول الخلفي")
            logger.info("=" * 80)

            self.is_running = True
            self.stop_event.clear()

            # ✅ FIX: كتابة PID file لتمكين UnifiedSystemManager من كشف العملية
            try:
                pid_file = Path(project_root) / "tmp" / "system.pid"
                pid_file.parent.mkdir(parents=True, exist_ok=True)
                with open(pid_file, "w") as f:
                    f.write(str(os.getpid()))
                logger.info(f"✅ تم كتابة PID file: {os.getpid()}")
            except Exception as pid_err:
                logger.warning(f"⚠️ فشل كتابة PID file: {pid_err}")

            # ✅ إزالة Group A - Group B يحتوي على جميع الوظائف
            # بدء خيط Group B (التداول الآلي مع اختيار العملات) — أولاً قبل أي شيء
            self.group_b_thread = Thread(target=self._run_group_b_loop, daemon=False)
            self.group_b_thread.start()
            logger.info("✅ تم بدء Group B (التداول الآلي + اختيار العملات)")

            # ✅ بدء Heartbeat Thread
            self.heartbeat_thread = Thread(
                target=self._run_heartbeat_loop, daemon=False
            )
            self.heartbeat_thread.start()
            logger.info("✅ تم بدء Heartbeat (نبضات النظام - كل 15 ثانية)")

            # ✅ تحديث حالة النظام في Database (بعد بدء الخيوط — لا يحجب التداول)
            try:
                self._update_system_status("running")
            except Exception as status_error:
                logger.warning(f"⚠️ فشل تحديث حالة النظام (الخيوط تعمل): {status_error}")

            # ✅ تسجيل في Audit Trail (غير حرج)
            if AUDIT_LOGGER_AVAILABLE and audit_logger:
                try:
                    admin_user_id = self._resolve_operator_admin_id()
                    audit_logger.log_admin_action(
                        user_id=admin_user_id,
                        action="start_background_system",
                        details="تم بدء النظام الخلفي (Group B فقط)",
                        request=None,
                    )
                except Exception as audit_error:
                    logger.warning(f"⚠️ فشل تسجيل audit trail: {audit_error}")

            # ✅ بدء مراقبة الصحة الدورية
            if HEALTH_MONITOR_AVAILABLE:
                try:
                    health_monitor = get_health_monitor()
                    health_monitor.start_monitoring(interval=60)
                    logger.info("✅ تم بدء مراقبة الصحة الدورية")
                except Exception as e:
                    logger.warning(f"⚠️ فشل بدء مراقبة الصحة: {e}")

            logger.info("=" * 80)
            logger.info("✅ النظام الخلفي يعمل الآن")
            logger.info("   • ✅ Group B: التداول الآلي + اختيار العملات (كل 60 ثانية)")
            logger.info("   • Heartbeat: كل 15 ثانية (💓 نبض النظام)")
            logger.info("   • Health Monitor: كل 60 ثانية")
            logger.info("=" * 80)

            return True

        except Exception as e:
            logger.error(f"❌ فشل بدء النظام الخلفي: {e}")
            self.is_running = False
            self._update_system_status("error", str(e))
            return False

    def stop(self, emergency=False):
        """إيقاف النظام الخلفي"""
        if not self.is_running:
            logger.warning("⚠️ النظام متوقف بالفعل")
            return False

        try:
            if emergency:
                logger.warning("🚨 إيقاف طوارئ - إيقاف فوري!")
            else:
                logger.info("⏸️ إيقاف النظام الخلفي...")

            # ✅ FIX: إشارة الإيقاف للخيوط (كانت مفقودة — الخيوط لم تكن تتوقف)
            self.is_running = False
            self.stop_event.set()

            # ✅ انتظار توقف الخيوط بشكل نظيف
            if self.group_b_thread and self.group_b_thread.is_alive():
                logger.info("⏳ انتظار توقف Group B thread...")
                self.group_b_thread.join(timeout=30)
                if self.group_b_thread.is_alive():
                    logger.warning("⚠️ Group B thread لم يتوقف في الوقت المحدد")

            if self.heartbeat_thread and self.heartbeat_thread.is_alive():
                logger.info("⏳ انتظار توقف Heartbeat thread...")
                self.heartbeat_thread.join(timeout=5)

            # إيقاف مراقبة الصحة
            if HEALTH_MONITOR_AVAILABLE:
                try:
                    health_monitor = get_health_monitor()
                    health_monitor.stop_monitoring()
                    logger.info("✅ تم إيقاف مراقبة الصحة")
                except Exception as e:
                    logger.warning(f"⚠️ خطأ في إيقاف مراقبة الصحة: {e}")

            # تحديث حالة النظام
            status = "emergency_stopped" if emergency else "stopped"
            self._update_system_status(status)

            # ✅ FIX: حذف PID file عند الإيقاف
            try:
                pid_file = Path(project_root) / "tmp" / "system.pid"
                if pid_file.exists():
                    pid_file.unlink()
                    logger.info("✅ تم حذف PID file")
            except Exception as pid_err:
                logger.warning(f"⚠️ فشل حذف PID file: {pid_err}")

            # ✅ SK-1 FIX: تحرير Process Lock
            if PROCESS_LOCK_AVAILABLE:
                success, message = release_system_lock()
                if success:
                    logger.info(f"🔓 {message}")
                else:
                    logger.warning(f"⚠️ فشل تحرير Lock: {message}")

            # ✅ تسجيل في Audit Trail
            if AUDIT_LOGGER_AVAILABLE and audit_logger:
                try:
                    admin_user_id = self._resolve_operator_admin_id()
                    audit_logger.log_admin_action(
                        user_id=admin_user_id,
                        action="stop_background_system",
                        details=f"تم إيقاف النظام الخلفي (طوارئ: {emergency})",
                        request=None,
                    )
                except Exception as audit_error:
                    logger.warning(f"⚠️ فشل تسجيل audit trail: {audit_error}")

            logger.info("=" * 80)
            logger.info("✅ تم إيقاف النظام الخلفي")
            logger.info("=" * 80)

            return True

        except Exception as e:
            logger.error(f"❌ خطأ في إيقاف النظام: {e}")
            # ✅ تحرير Lock حتى في حالة الخطأ
            if PROCESS_LOCK_AVAILABLE:
                release_system_lock()
            return False

    def _run_group_b_loop(self):
        """حلقة تشغيل Group B (التداول الآلي)"""
        logger.info("🔄 بدء حلقة Group B")
        _consecutive_errors = 0
        _max_consecutive_for_error_status = 3

        while not self.stop_event.is_set():
            try:
                # تنفيذ Group B
                self._execute_group_b()
                if self.state_manager:
                    try:
                        from backend.core.heartbeat_monitor import get_heartbeat_monitor

                        monitor = get_heartbeat_monitor(self.state_manager)
                        monitor.check_heartbeat()
                    except Exception as monitor_error:
                        logger.warning(
                            f"⚠️ فشل فحص heartbeat في worker: {monitor_error}"
                        )

                # نجاح — إعادة عداد الأخطاء
                if _consecutive_errors > 0:
                    logger.info(
                        f"✅ Group B recovered after {_consecutive_errors} consecutive errors"
                    )
                    _consecutive_errors = 0

                # انتظار 60 ثانية
                self.stop_event.wait(self.group_b_interval)

            except Exception as e:
                _consecutive_errors += 1
                logger.error(
                    f"❌ خطأ في حلقة Group B (consecutive: {_consecutive_errors}): {e}"
                )
                error_logger.log_group_b_error(
                    message="خطأ في حلقة التداول",
                    details=str(e),
                    critical=(_consecutive_errors >= _max_consecutive_for_error_status),
                )
                # تسجيل حالة error فقط بعد 3 أخطاء متتالية (ليس على أول خطأ عابر)
                if _consecutive_errors >= _max_consecutive_for_error_status:
                    self._update_system_status(
                        "error",
                        f"Group B: {_consecutive_errors} consecutive errors: {e}",
                    )
                # انتظار تصاعدي: 30s → 60s → 120s (max) — ليس 5 دقائق ثابتة
                wait_seconds = min(30 * _consecutive_errors, 120)
                logger.info(f"   ⏳ Retry in {wait_seconds}s...")
                self.stop_event.wait(wait_seconds)

    def _get_or_create_system(
        self, user_id: int, requested_mode: str = None
    ) -> GroupBSystem:
        """
        الحصول على نظام تداول مُخزّن أو إنشاء جديد.
        ✅ FIX: يحافظ على daily_state عبر الدورات (حماية رأس المال)
        ✅ يُحدّث إعدادات المستخدم والمحفظة كل دورة من DB
        """
        context_key = f"{user_id}:{requested_mode or 'real'}"
        context_fingerprint = self._build_user_context_fingerprint(
            user_id, requested_mode=requested_mode
        )
        cached_fingerprint = self._user_context_fingerprints.get(context_key)

        if (
            context_key not in self._user_systems
            or cached_fingerprint != context_fingerprint
        ):
            logger.info(
                f"🆕 إنشاء GroupBSystem جديد للمستخدم {user_id} mode={requested_mode or 'real'}"
            )
            self._user_systems[context_key] = GroupBSystem(
                user_id=user_id, requested_mode=requested_mode
            )
            self._user_context_fingerprints[context_key] = context_fingerprint
        else:
            system = self._user_systems[context_key]
            system.requested_mode = requested_mode
            system.user_settings = system._load_user_settings()
            system.is_demo_trading = system._determine_trading_mode()
            system.user_portfolio = system._load_user_portfolio()
            system.can_trade = system.user_settings.get("trading_enabled", False)
            system.daily_state["max_daily_loss_pct"] = (
                system._resolve_max_daily_loss_pct()
            )

        return self._user_systems[context_key]

    def _execute_group_b(self):
        """تنفيذ Group B (التداول الآلي لجميع المستخدمين النشطين)"""
        try:
            # ✅ دائماً زيادة عداد الدورات (يعكس عدد مرات المسح الفعلية)
            self._group_b_cycles += 1

            # ========== جلب جميع المستخدمين النشطين ==========
            active_users = self._get_active_trading_users()

            if not active_users:
                logger.debug("⚠️ Group B: لا يوجد مستخدمين نشطين للتداول")
                self._update_group_b_activity(self._group_b_cycles, 0)
                return

            logger.info(f"🔄 Group B: بدء التداول لـ {len(active_users)} مستخدم")

            # تنظيف cache المستخدمين الذين لم يعودوا نشطين
            active_ids = {u["context_key"] for u in active_users}
            stale_ids = [uid for uid in self._user_systems if uid not in active_ids]
            for uid in stale_ids:
                del self._user_systems[uid]
                self._user_context_fingerprints.pop(uid, None)

            # ========== تشغيل التداول لكل مستخدم ==========
            for user in active_users:
                try:
                    user_id = user["id"]
                    username = user.get("username", f"User_{user_id}")
                    trading_enabled = user.get("trading_enabled", False)
                    has_open_positions = user.get("has_open_positions", False)
                    requested_mode = user.get("requested_mode")

                    group_b = self._get_or_create_system(
                        user_id, requested_mode=requested_mode
                    )
                    group_b.start_runtime_services()

                    # تحميل العملات من قاعدة البيانات
                    if not group_b.load_successful_coins_from_database():
                        if not group_b.load_successful_coins_from_file():
                            logger.debug(f"⚠️ User {user_id}: لا توجد عملات للتداول")

                    # ========== منطق التداول ==========
                    if trading_enabled:
                        group_b.run_trading_cycle()
                        logger.debug(
                            f"✅ User {user_id} ({username}) mode={requested_mode}: دورة تداول كاملة"
                        )
                    elif has_open_positions:
                        group_b.run_monitoring_only()
                        logger.debug(
                            f"👁️ User {user_id} ({username}) mode={requested_mode}: مراقبة صفقات مفتوحة فقط"
                        )

                except Exception as user_error:
                    logger.error(
                        f"❌ خطأ في التداول للمستخدم {user.get('id', '?')}: {user_error}"
                    )
                    continue

            self.last_group_b_run = datetime.now()

            # ✅ تحديث نشاط Group B
            total_active_trades = sum(
                1 for u in active_users if u.get("has_open_positions", False)
            )
            self._update_group_b_activity(self._group_b_cycles, total_active_trades)

            logger.info(f"✅ Group B: اكتملت الدورة لـ {len(active_users)} مستخدم")

        except Exception as e:
            logger.error(f"❌ خطأ في تنفيذ Group B: {e}")
            error_logger.log_group_b_error(
                message="خطأ في تنفيذ Group B", details=str(e), critical=False
            )
            self._update_system_status("error", f"Group B: {e}")

    def _get_active_trading_users(self) -> list:
        """
        جلب المستخدمين النشطين للتداول/المراقبة بشكل متوافق مع PostgreSQL.

        القواعد:
        - المصدر الوحيد للحالة هو DB (users/user_settings/user_binance_keys/active_positions)
        - تضمين المستخدم إذا كان:
          1) trading_enabled=True ومؤهل للتنفيذ
             - regular: يتطلب مفاتيح Binance نشطة
             - admin (demo): يسمح بدون مفاتيح Binance
          2) أو لديه صفقات مفتوحة للمراقبة فقط
        - لا ازدواجية: كل مستخدم يظهر مرة واحدة فقط
        """
        try:
            with self.db_manager.get_connection() as conn:
                active_true = True if self.db_manager.is_postgres() else 1

                user_rows = conn.execute(
                    """
                    SELECT id, username, user_type
                    FROM users
                    WHERE is_active = %s
                    ORDER BY id
                """,
                    (active_true,),
                ).fetchall()

                key_rows = conn.execute(
                    """
                    SELECT user_id
                    FROM user_binance_keys
                    WHERE is_active = %s
                """,
                    (active_true,),
                ).fetchall()
                users_with_keys = {row[0] for row in key_rows}

                open_positions_rows = conn.execute(
                    """
                    SELECT user_id, is_demo, COUNT(*) AS open_count
                    FROM active_positions
                    WHERE is_active = %s
                    GROUP BY user_id, is_demo
                """,
                    (active_true,),
                ).fetchall()
                open_positions_map = {
                    (row[0], bool(row[1])): int(row[2] or 0)
                    for row in open_positions_rows
                }

                users = []
                for row in user_rows:
                    user_id = row[0]
                    username = row[1]
                    user_type = row[2]
                    has_binance_keys = user_id in users_with_keys

                    mode_specs = [("real", False)]
                    if user_type == "admin":
                        mode_specs = [("demo", True), ("real", False)]

                    for requested_mode, is_demo_mode in mode_specs:
                        settings = (
                            self.db_manager.get_trading_settings(
                                user_id, is_demo=is_demo_mode
                            )
                            or {}
                        )
                        trading_enabled = bool(settings.get("trading_enabled", False))
                        has_open_positions = (
                            open_positions_map.get((user_id, is_demo_mode), 0) > 0
                        )

                        eligible_for_execution = has_binance_keys or (
                            user_type == "admin" and requested_mode == "demo"
                        )
                        include_user = (
                            trading_enabled and eligible_for_execution
                        ) or has_open_positions

                        logger.warning(
                            f"🔍 DECISION: user={username} mode={requested_mode} "
                            f"trading_enabled={trading_enabled} eligible={eligible_for_execution} "
                            f"has_open={has_open_positions} -> include={include_user}"
                        )

                        if trading_enabled and eligible_for_execution:
                            logger.warning(
                                f"🚨 ADDING USER TO ACTIVE LIST: {username} mode={requested_mode} trading_enabled={trading_enabled} eligible={eligible_for_execution}"
                            )

                        if not include_user:
                            continue

                        users.append(
                            {
                                "id": user_id,
                                "username": username,
                                "user_type": user_type,
                                "requested_mode": requested_mode,
                                "context_key": f"{user_id}:{requested_mode}",
                                "trading_enabled": trading_enabled,
                                "has_open_positions": has_open_positions,
                                "has_binance_keys": has_binance_keys,
                            }
                        )

                logger.debug(f"📋 وجدنا {len(users)} مستخدم نشط للتداول/المراقبة")
                return users

        except Exception as e:
            logger.error(f"❌ خطأ في جلب المستخدمين النشطين: {e}")
            return []

    def _resolve_operator_admin_id(self):
        """تحديد الأدمن المشغّل ديناميكياً بدلاً من افتراض user_id=1."""
        try:
            with self.db_manager.get_connection() as conn:
                row = conn.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE user_type = 'admin' AND is_active = %s
                    ORDER BY id
                    LIMIT 1
                    """,
                    (True if self.db_manager.is_postgres() else 1,),
                ).fetchone()
                return int(row[0]) if row else None
        except Exception as e:
            logger.warning(f"⚠️ تعذر تحديد admin operator id: {e}")
            return None

    def _build_user_context_fingerprint(
        self, user_id: int, requested_mode: str = None
    ) -> str:
        """بصمة لسياق التنفيذ لضمان عدم استمرار استخدام نظام stale بعد تغيّر الإعدادات/الوضع."""
        try:
            effective_is_demo = bool(
                get_effective_is_demo(
                    self.db_manager, user_id, requested_mode=requested_mode
                )
            )
            settings = (
                self.db_manager.get_trading_settings(user_id, is_demo=effective_is_demo)
                or {}
            )
            keys = self.db_manager.get_binance_keys(user_id) or {}
            fingerprint_payload = {
                "is_demo": effective_is_demo,
                "trading_enabled": bool(settings.get("trading_enabled", False)),
                "trade_amount": settings.get("trade_amount"),
                "position_size_percentage": settings.get("position_size_percentage"),
                "max_positions": settings.get("max_positions"),
                "risk_level": settings.get("risk_level"),
                "has_keys": bool(keys.get("api_key")),
                "requested_mode": requested_mode,
            }
            return json.dumps(fingerprint_payload, sort_keys=True, default=str)
        except Exception as e:
            logger.warning(f"⚠️ تعذر بناء fingerprint للمستخدم {user_id}: {e}")
            return f"fallback:{user_id}"

    def _cleanup_old_logs(self):
        """✅ تنظيف السجلات القديمة عند البدء"""
        try:
            log_file = Path("logs/background_trading.log")
            if log_file.exists():
                file_size = log_file.stat().st_size
                # إذا كان الملف أكبر من 50 MB
                if file_size > 50 * 1024 * 1024:
                    # أرشفة السجل القديم
                    backup_name = f"logs/background_trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log.bak"
                    log_file.rename(backup_name)
                    logger.info(f"✅ تم أرشفة السجل القديم: {backup_name}")
                    # إنشاء ملف سجل جديد
                    log_file.touch()
                    logger.info("✅ تم إنشاء ملف سجل جديد")
        except Exception as e:
            logger.warning(f"⚠️ خطأ في تنظيف السجلات: {e}")

    def _run_heartbeat_loop(self):
        """
        حلقة إرسال نبضات النظام (Heartbeat)

        يتم تشغيلها كـ thread منفصل
        ترسل نبضة كل 15 ثانية لإثبات أن النظام حي
        """
        logger.info("💓 بدء حلقة Heartbeat")

        while not self.stop_event.is_set():
            try:
                # إرسال نبضة عبر StateManager
                if self.state_manager:
                    self.state_manager.send_heartbeat()
                    logger.debug("💓 تم إرسال heartbeat")

                # انتظار قبل النبضة التالية
                self.stop_event.wait(self.heartbeat_interval)

            except Exception as e:
                logger.error(f"❌ خطأ في حلقة Heartbeat: {e}")
                self.stop_event.wait(self.heartbeat_interval)

        logger.info("💓 توقفت حلقة Heartbeat")

    def _update_group_b_activity(self, total_cycles: int, active_trades: int):
        """
        تحديث نشاط Group B في StateManager

        Args:
            total_cycles: إجمالي عدد الدورات
            active_trades: عدد الصفقات النشطة
        """
        if self.state_manager:
            try:
                self.state_manager.update_activity(
                    "group_b",
                    total_cycles=total_cycles,
                    active_trades=active_trades,
                    last_cycle=datetime.now().isoformat(),
                )
            except Exception as e:
                logger.warning(f"⚠️ فشل تحديث نشاط Group B: {e}")

    def _update_system_status(self, status: str, message: str = ""):
        """تحديث حالة النظام في Database + StateManager JSON (مصدران متزامنان)

        ✅ FIX: يحدّث كلا المصدرين لضمان التزامن
        ✅ FIX: يستخدم DatabaseManager بدلاً من اتصال مباشر
        ✅ FIX: WAL mode و busy_timeout مفعّالان
        """
        import time

        # تحديد is_running بناءً على الحالة
        is_running = status in ["running", "starting"]

        # ✅ FIX: تحديث StateManager JSON أيضاً (حل مشكلة Dual State)
        if self.state_manager:
            try:
                trading_state_map_sm = {
                    "running": "RUNNING",
                    "starting": "STARTING",
                    "stopped": "STOPPED",
                    "emergency_stopped": "STOPPED",
                    "error": "ERROR",
                }
                state_data = {
                    "status": status,
                    "is_running": bool(is_running),
                    "trading_state": trading_state_map_sm.get(status, "STOPPED"),
                    "message": message
                    or ("النظام يعمل" if status == "running" else "النظام متوقف"),
                    "pid": os.getpid() if is_running else None,
                }
                if status == "running":
                    state_data["started_at"] = datetime.now().isoformat()
                elif status in ["stopped", "emergency_stopped"]:
                    state_data["started_at"] = None
                    state_data["uptime"] = 0

                self.state_manager.write_state(state_data, user="background_manager")
                logger.debug(f"✅ تم تحديث StateManager JSON: {status}")
            except Exception as e:
                logger.warning(f"⚠️ فشل تحديث StateManager JSON: {e}")

        if status in {"error", "stopped", "emergency_stopped"}:
            try:
                from backend.services.admin_notification_service import (
                    get_admin_notification_service,
                )

                admin_notifier = get_admin_notification_service()
                admin_notifier.notify_trading_stopped(
                    message or f"تحول النظام إلى الحالة: {status}"
                )
            except Exception as notify_error:
                logger.warning(f"⚠️ فشل إرسال إشعار توقف التداول للأدمن: {notify_error}")

        # محاولة التحديث في DB مع retry (timeout قصير لتجنب الحجب)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self.db_manager.get_write_connection() as conn:
                    # ✅ FIX: removed PRAGMA busy_timeout (SQLite-only, breaks psycopg2)
                    trading_state_map = {
                        "running": "RUNNING",
                        "starting": "STARTING",
                        "stopped": "STOPPED",
                        "emergency_stopped": "STOPPED",
                        "error": "ERROR",
                    }
                    trading_state = trading_state_map.get(status, "STOPPED")
                    conn.execute(
                        """
                        UPDATE system_status 
                        SET status = %s, is_running = %s, trading_state = %s,
                            pid = %s,
                            last_update = CURRENT_TIMESTAMP, message = %s
                        WHERE id = 1
                    """,
                        (
                            status,
                            is_running,
                            trading_state,
                            os.getpid() if is_running else None,
                            message,
                        ),
                    )

                    logger.debug(
                        f"✅ تم تحديث DB: status={status}, is_running={is_running}"
                    )
                    self._last_status = status
                    return  # نجاح

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"⚠️ فشل تحديث الحالة (محاولة {attempt + 1}/{max_retries}): {e}"
                    )
                    time.sleep(0.3 * (attempt + 1))
                    continue
                logger.error(f"❌ فشل تحديث حالة النظام بعد {max_retries} محاولات: {e}")

        logger.error(f"❌ فشل تحديث حالة النظام: status={status}, message={message}")

    def get_status(self):
        """الحصول على حالة النظام"""
        return {
            "is_running": self.is_running,
            "last_group_b_run": self.last_group_b_run.isoformat()
            if self.last_group_b_run
            else None,
            "group_b_interval_seconds": self.group_b_interval,
        }


def signal_handler(signum, frame):
    """معالج إشارات النظام"""
    logger.info(f"\n⚠️ تم استلام إشارة {signum}")
    if manager:
        manager.stop(emergency=True)
    sys.exit(0)


# متغير عام للمدير
manager = None


def main():
    """النقطة الرئيسية للتشغيل"""
    parser = argparse.ArgumentParser(description="نظام إدارة التداول الخلفي")
    parser.add_argument("--start", action="store_true", help="بدء النظام")
    parser.add_argument("--stop", action="store_true", help="إيقاف النظام")
    parser.add_argument("--status", action="store_true", help="عرض حالة النظام")
    parser.add_argument("--emergency-stop", action="store_true", help="إيقاف طوارئ")

    args = parser.parse_args()

    global manager
    manager = BackgroundTradingManager()

    # تسجيل معالجات الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if args.start:
        success = manager.start()
        if success:
            logger.info("✅ النظام يعمل - الحلقة الرئيسية نشطة")
            try:
                # ✅ الاستمرار في العمل حتى إشارة الإيقاف
                # هذه الحلقة ضرورية لإبقاء البرنامج حياً
                _recovery_attempts = 0
                _max_recovery_attempts = 3
                while manager.is_running:
                    time.sleep(1)
                    # فحص دوري لحالة الـ threads مع إعادة تشغيل تلقائي
                    if not manager.group_b_thread.is_alive():
                        _recovery_attempts += 1
                        if _recovery_attempts <= _max_recovery_attempts:
                            logger.warning(
                                f"⚠️ Group B thread died — auto-recovering (attempt {_recovery_attempts}/{_max_recovery_attempts})"
                            )
                            recovered = manager._recover_group_b()
                            if recovered:
                                logger.info("✅ Group B thread recovered successfully")
                                continue
                        logger.error(
                            f"❌ Group B failed after {_recovery_attempts} recovery attempts — stopping system"
                        )
                        manager.is_running = False
                        break
                    else:
                        # Thread alive — reset recovery counter
                        if _recovery_attempts > 0:
                            _recovery_attempts = 0
            except KeyboardInterrupt:
                logger.info("\n⚠️ تم إيقاف النظام بواسطة المستخدم")
                manager.stop()
            except Exception as e:
                logger.error(f"❌ خطأ في الحلقة الرئيسية: {e}")
                manager.stop()
        sys.exit(0 if success else 1)

    elif args.stop:
        success = manager.stop()
        sys.exit(0 if success else 1)

    elif args.emergency_stop:
        success = manager.stop(emergency=True)
        sys.exit(0 if success else 1)

    elif args.status:
        status = manager.get_status()
        print("\n" + "=" * 80)
        print("📊 حالة نظام التداول الخلفي")
        print("=" * 80)
        print(f"الحالة: {'🟢 يعمل' if status['is_running'] else '🔴 متوقف'}")
        print(f"✅ Group B: التداول الآلي + اختيار العملات")
        print(f"آخر تشغيل Group B: {status['last_group_b_run'] or 'لم يتم بعد'}")
        print(f"فترة Group B: كل {status['group_b_interval_seconds']} ثانية")
        print("=" * 80)
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
