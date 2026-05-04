"""
🏥 System Health Monitor - نظام مراقبة صحة النظام الشامل
========================================================

يوفر:
1. مراقبة شاملة لجميع مكونات النظام
2. التعافي التلقائي عند اكتشاف مشاكل
3. تنبيهات عند تدهور الأداء
4. تقارير صحة دورية
5. إعادة تشغيل تلقائي للخدمات المتوقفة
"""

import time
import threading
import logging
import psutil
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """حالات الصحة"""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """صحة مكون"""

    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    last_check: Optional[datetime] = None
    response_time_ms: float = 0.0
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class SystemHealthMonitor:
    """
    مراقب صحة النظام الشامل
    """

    def __init__(self):
        self.components: Dict[str, ComponentHealth] = {}
        self.health_checkers: Dict[str, Callable] = {}
        self.recovery_handlers: Dict[str, Callable] = {}
        self.alert_handlers: List[Callable] = []

        self._monitor_thread = None
        self._stop_monitor = threading.Event()
        self._check_interval = 30  # ثانية

        # عتبات التحذير
        self.thresholds = {
            "cpu_warning": 80,
            "cpu_critical": 95,
            "memory_warning": 80,
            "memory_critical": 95,
            "disk_warning": 85,
            "disk_critical": 95,
            "response_time_warning": 5000,  # 5 ثواني
            "response_time_critical": 30000,  # 30 ثانية
        }

        # تسجيل المكونات الأساسية
        self._register_system_components()

        logger.info("✅ تم تهيئة مراقب صحة النظام")

    def _register_system_components(self):
        """تسجيل المكونات الأساسية"""
        # مكونات النظام
        self.register_component("system_cpu", self._check_cpu)
        self.register_component("system_memory", self._check_memory)
        self.register_component("system_disk", self._check_disk)

        # مكونات التطبيق
        self.register_component("database", None)  # سيتم تعيينه لاحقاً
        self.register_component("binance_api", None)
        self.register_component("group_b", None)
        self.register_component("background_manager", None)

    def register_component(
        self,
        name: str,
        health_checker: Callable = None,
        recovery_handler: Callable = None,
    ):
        """
        تسجيل مكون للمراقبة

        Args:
            name: اسم المكون
            health_checker: دالة فحص الصحة
            recovery_handler: دالة التعافي
        """
        self.components[name] = ComponentHealth(name=name)

        if health_checker:
            self.health_checkers[name] = health_checker

        if recovery_handler:
            self.recovery_handlers[name] = recovery_handler

        logger.debug(f"📝 تم تسجيل المكون: {name}")

    def add_alert_handler(self, handler: Callable):
        """إضافة معالج تنبيهات"""
        self.alert_handlers.append(handler)

    def _check_cpu(self) -> ComponentHealth:
        """فحص استخدام المعالج"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)

            if cpu_percent >= self.thresholds["cpu_critical"]:
                status = HealthStatus.CRITICAL
                message = f"استخدام المعالج مرتفع جداً: {cpu_percent}%"
            elif cpu_percent >= self.thresholds["cpu_warning"]:
                status = HealthStatus.WARNING
                message = f"استخدام المعالج مرتفع: {cpu_percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"استخدام المعالج طبيعي: {cpu_percent}%"

            return ComponentHealth(
                name="system_cpu",
                status=status,
                message=message,
                last_check=datetime.now(),
                details={"cpu_percent": cpu_percent},
            )
        except Exception as e:
            return ComponentHealth(
                name="system_cpu",
                status=HealthStatus.UNKNOWN,
                message=f"خطأ في فحص المعالج: {e}",
                last_check=datetime.now(),
            )

    def _check_memory(self) -> ComponentHealth:
        """فحص استخدام الذاكرة"""
        try:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent

            if memory_percent >= self.thresholds["memory_critical"]:
                status = HealthStatus.CRITICAL
                message = f"استخدام الذاكرة مرتفع جداً: {memory_percent}%"
            elif memory_percent >= self.thresholds["memory_warning"]:
                status = HealthStatus.WARNING
                message = f"استخدام الذاكرة مرتفع: {memory_percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"استخدام الذاكرة طبيعي: {memory_percent}%"

            return ComponentHealth(
                name="system_memory",
                status=status,
                message=message,
                last_check=datetime.now(),
                details={
                    "memory_percent": memory_percent,
                    "available_gb": memory.available / (1024**3),
                    "total_gb": memory.total / (1024**3),
                },
            )
        except Exception as e:
            return ComponentHealth(
                name="system_memory",
                status=HealthStatus.UNKNOWN,
                message=f"خطأ في فحص الذاكرة: {e}",
                last_check=datetime.now(),
            )

    def _check_disk(self) -> ComponentHealth:
        """فحص استخدام القرص"""
        try:
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent

            if disk_percent >= self.thresholds["disk_critical"]:
                status = HealthStatus.CRITICAL
                message = f"استخدام القرص مرتفع جداً: {disk_percent}%"
            elif disk_percent >= self.thresholds["disk_warning"]:
                status = HealthStatus.WARNING
                message = f"استخدام القرص مرتفع: {disk_percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"استخدام القرص طبيعي: {disk_percent}%"

            return ComponentHealth(
                name="system_disk",
                status=status,
                message=message,
                last_check=datetime.now(),
                details={
                    "disk_percent": disk_percent,
                    "free_gb": disk.free / (1024**3),
                    "total_gb": disk.total / (1024**3),
                },
            )
        except Exception as e:
            return ComponentHealth(
                name="system_disk",
                status=HealthStatus.UNKNOWN,
                message=f"خطأ في فحص القرص: {e}",
                last_check=datetime.now(),
            )

    def check_component(self, name: str) -> ComponentHealth:
        """فحص مكون معين"""
        checker = self.health_checkers.get(name)

        if not checker:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNKNOWN,
                message="لا يوجد فاحص صحة مسجل",
                last_check=datetime.now(),
            )

        try:
            start_time = time.time()
            result = checker()
            response_time = (time.time() - start_time) * 1000

            if isinstance(result, ComponentHealth):
                result.response_time_ms = response_time
                self.components[name] = result
                return result
            elif isinstance(result, bool):
                status = (
                    HealthStatus.HEALTHY if result else HealthStatus.CRITICAL
                )
                health = ComponentHealth(
                    name=name,
                    status=status,
                    message="صحي" if result else "غير صحي",
                    last_check=datetime.now(),
                    response_time_ms=response_time,
                )
                self.components[name] = health
                return health
            else:
                health = ComponentHealth(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    message=str(result),
                    last_check=datetime.now(),
                    response_time_ms=response_time,
                )
                self.components[name] = health
                return health

        except Exception as e:
            health = ComponentHealth(
                name=name,
                status=HealthStatus.CRITICAL,
                message=f"خطأ في الفحص: {e}",
                last_check=datetime.now(),
            )
            self.components[name] = health
            return health

    def check_all(self) -> Dict[str, ComponentHealth]:
        """فحص جميع المكونات"""
        results = {}

        for name in self.health_checkers:
            results[name] = self.check_component(name)

        return results

    def get_overall_status(self) -> HealthStatus:
        """الحصول على الحالة العامة"""
        statuses = [c.status for c in self.components.values()]

        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            return HealthStatus.WARNING
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def get_health_report(self) -> Dict[str, Any]:
        """الحصول على تقرير الصحة الشامل"""
        self.check_all()

        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": self.get_overall_status().value,
            "components": {},
        }

        for name, health in self.components.items():
            report["components"][name] = {
                "status": health.status.value,
                "message": health.message,
                "last_check": (
                    health.last_check.isoformat()
                    if health.last_check
                    else None
                ),
                "response_time_ms": health.response_time_ms,
                "details": health.details,
            }

        return report

    def try_recovery(self, name: str) -> bool:
        """محاولة التعافي لمكون معين"""
        handler = self.recovery_handlers.get(name)

        if not handler:
            logger.warning(f"⚠️ لا يوجد معالج تعافي لـ: {name}")
            return False

        try:
            logger.info(f"🔄 محاولة التعافي لـ: {name}")
            result = handler()

            if result:
                logger.info(f"✅ تم التعافي بنجاح: {name}")
                # إعادة فحص الصحة
                self.check_component(name)
                return True
            else:
                logger.error(f"❌ فشل التعافي: {name}")
                return False

        except Exception as e:
            logger.error(f"❌ خطأ في التعافي: {name} - {e}")
            return False

    def _send_alert(self, component: str, status: HealthStatus, message: str):
        """إرسال تنبيه"""
        for handler in self.alert_handlers:
            try:
                handler(component, status, message)
            except Exception as e:
                logger.error(f"❌ خطأ في إرسال التنبيه: {e}")

    def start_monitoring(self, interval: int = 30):
        """بدء المراقبة الدورية"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        self._check_interval = interval
        self._stop_monitor.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="SystemHealthMonitor"
        )
        self._monitor_thread.start()
        logger.info(f"🏥 بدء مراقبة صحة النظام (كل {interval} ثانية)")

    def stop_monitoring(self):
        """إيقاف المراقبة"""
        self._stop_monitor.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("⏹️ تم إيقاف مراقبة صحة النظام")

    def _monitor_loop(self):
        """حلقة المراقبة"""
        while not self._stop_monitor.is_set():
            try:
                # فحص جميع المكونات
                results = self.check_all()

                # معالجة المكونات غير الصحية
                for name, health in results.items():
                    if health.status == HealthStatus.CRITICAL:
                        self._send_alert(name, health.status, health.message)

                        # محاولة التعافي التلقائي
                        if name in self.recovery_handlers:
                            self.try_recovery(name)

                    elif health.status == HealthStatus.WARNING:
                        self._send_alert(name, health.status, health.message)

                # انتظار قبل الدورة التالية
                self._stop_monitor.wait(timeout=self._check_interval)

            except Exception as e:
                logger.error(f"❌ خطأ في حلقة المراقبة: {e}")
                time.sleep(10)


# ============================================================
# Singleton accessor
# ============================================================

_health_monitor: Optional[SystemHealthMonitor] = None


def get_health_monitor() -> SystemHealthMonitor:
    """الحصول على مراقب الصحة (Singleton)"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = SystemHealthMonitor()
    return _health_monitor


def setup_database_health_check(db_manager) -> None:
    """إعداد فحص صحة قاعدة البيانات"""
    monitor = get_health_monitor()

    def check_database():
        try:
            with db_manager.get_connection() as conn:
                conn.execute("SELECT 1")
            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                message="قاعدة البيانات تعمل بشكل طبيعي",
                last_check=datetime.now(),
            )
        except Exception as e:
            return ComponentHealth(
                name="database",
                status=HealthStatus.CRITICAL,
                message=f"خطأ في قاعدة البيانات: {e}",
                last_check=datetime.now(),
            )

    def recover_database():
        try:
            db_manager._init_connection_pool()
            return True
        except Exception:
            return False

    monitor.health_checkers["database"] = check_database
    monitor.recovery_handlers["database"] = recover_database

    logger.info("✅ تم إعداد فحص صحة قاعدة البيانات")


def setup_binance_health_check(client) -> None:
    """إعداد فحص صحة Binance"""
    monitor = get_health_monitor()

    def check_binance():
        try:
            start = time.time()
            client.ping()
            latency = (time.time() - start) * 1000

            return ComponentHealth(
                name="binance_api",
                status=HealthStatus.HEALTHY,
                message=f"Binance API يعمل (latency: {latency:.0f}ms)",
                last_check=datetime.now(),
                response_time_ms=latency,
            )
        except Exception as e:
            return ComponentHealth(
                name="binance_api",
                status=HealthStatus.CRITICAL,
                message=f"خطأ في Binance API: {e}",
                last_check=datetime.now(),
            )

    monitor.health_checkers["binance_api"] = check_binance

    logger.info("✅ تم إعداد فحص صحة Binance API")
