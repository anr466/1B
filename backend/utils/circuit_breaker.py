"""
🔌 Circuit Breaker - نمط الحماية من الأخطاء المتكررة
يوقف الطلبات مؤقتاً عند حدوث أخطاء متكررة لحماية النظام
"""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional, Dict
from datetime import datetime, timedelta
from functools import wraps
import threading

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """حالات Circuit Breaker"""
    CLOSED = "closed"          # يعمل بشكل طبيعي
    OPEN = "open"              # مفتوح - يرفض الطلبات
    HALF_OPEN = "half_open"    # نصف مفتوح - يختبر الاتصال


class CircuitBreakerConfig:
    """إعدادات Circuit Breaker"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: str = "circuit_breaker"
    ):
        """
        Args:
            failure_threshold: عدد الأخطاء قبل فتح الـ circuit
            recovery_timeout: مدة الانتظار قبل محاولة الاتصال مجدداً (ثانية)
            expected_exception: نوع الخطأ المتوقع
            name: اسم الـ circuit breaker
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name


class CircuitBreaker:
    """نمط Circuit Breaker لحماية النظام من الأخطاء المتكررة"""
    
    def __init__(self, config: CircuitBreakerConfig = None):
        """تهيئة Circuit Breaker"""
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.opened_at = None
        self.lock = threading.RLock()
        
        logger.info(f"✅ Circuit Breaker '{self.config.name}' تم تهيئته")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        استدعاء دالة مع حماية Circuit Breaker
        
        Args:
            func: الدالة المراد استدعاؤها
            *args: معاملات الدالة
            **kwargs: معاملات مسماة
            
        Returns:
            نتيجة الدالة
            
        Raises:
            CircuitBreakerOpenError: إذا كان الـ circuit مفتوحاً
        """
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info(f"🔄 {self.config.name}: تغيير الحالة إلى HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.config.name}' مفتوح. "
                        f"سيتم إعادة المحاولة بعد {self._get_remaining_timeout():.0f} ثانية"
                    )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.config.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """التحقق من إمكانية إعادة محاولة الاتصال"""
        if self.last_failure_time is None:
            return False
        
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.recovery_timeout
    
    def _get_remaining_timeout(self) -> float:
        """الحصول على الوقت المتبقي قبل إعادة المحاولة"""
        if self.last_failure_time is None:
            return 0
        
        elapsed = time.time() - self.last_failure_time
        remaining = self.config.recovery_timeout - elapsed
        return max(0, remaining)
    
    def _on_success(self):
        """معالجة النجاح"""
        with self.lock:
            self.failure_count = 0
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.success_count += 1
                logger.info(f"✅ {self.config.name}: تم إغلاق الـ circuit (نجح الاتصال)")
    
    def _on_failure(self):
        """معالجة الفشل"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            logger.warning(
                f"⚠️ {self.config.name}: خطأ {self.failure_count}/{self.config.failure_threshold}"
            )
            
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = datetime.now()
                logger.error(
                    f"🔴 {self.config.name}: فتح الـ circuit بعد {self.failure_count} أخطاء"
                )
    
    def get_state(self) -> Dict[str, Any]:
        """الحصول على حالة الـ circuit breaker"""
        with self.lock:
            return {
                'name': self.config.name,
                'state': self.state.value,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'failure_threshold': self.config.failure_threshold,
                'recovery_timeout': self.config.recovery_timeout,
                'last_failure_time': self.last_failure_time,
                'opened_at': self.opened_at.isoformat() if self.opened_at else None,
                'remaining_timeout': self._get_remaining_timeout()
            }
    
    def reset(self):
        """إعادة تعيين الـ circuit breaker"""
        with self.lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.opened_at = None
            logger.info(f"🔄 {self.config.name}: تم إعادة تعيين الـ circuit")


class CircuitBreakerOpenError(Exception):
    """خطأ عند محاولة الوصول إلى circuit breaker مفتوح"""
    pass


class CircuitBreakerManager:
    """مدير Circuit Breakers - يدير عدة circuit breakers"""
    
    def __init__(self):
        """تهيئة مدير الـ circuit breakers"""
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.lock = threading.RLock()
    
    def get_or_create(
        self,
        name: str,
        config: CircuitBreakerConfig = None
    ) -> CircuitBreaker:
        """الحصول على أو إنشاء circuit breaker"""
        with self.lock:
            if name not in self.breakers:
                if config is None:
                    config = CircuitBreakerConfig(name=name)
                self.breakers[name] = CircuitBreaker(config)
            return self.breakers[name]
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """الحصول على حالة جميع الـ circuit breakers"""
        with self.lock:
            return {
                name: breaker.get_state()
                for name, breaker in self.breakers.items()
            }
    
    def reset_all(self):
        """إعادة تعيين جميع الـ circuit breakers"""
        with self.lock:
            for breaker in self.breakers.values():
                breaker.reset()
            logger.info("🔄 تم إعادة تعيين جميع الـ circuit breakers")


# مثيل عام لمدير الـ circuit breakers
circuit_breaker_manager = CircuitBreakerManager()


def circuit_breaker(
    name: str = "default",
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    exceptions: tuple = (Exception,)
):
    """
    Decorator لتطبيق Circuit Breaker على دالة
    
    Args:
        name: اسم الـ circuit breaker
        failure_threshold: عدد الأخطاء قبل الفتح
        recovery_timeout: مدة الانتظار قبل إعادة المحاولة
        exceptions: أنواع الأخطاء المتوقعة
    
    مثال:
        @circuit_breaker(name="binance_api", failure_threshold=5, recovery_timeout=60)
        def fetch_binance_data():
            return binance_client.get_ticker()
    """
    def decorator(func: Callable) -> Callable:
        config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=exceptions[0] if exceptions else Exception,
            name=name
        )
        breaker = circuit_breaker_manager.get_or_create(name, config)
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return breaker.call(func, *args, **kwargs)
            except CircuitBreakerOpenError as e:
                logger.error(f"❌ {name}: {e}")
                raise
        
        return wrapper
    return decorator


# إعدادات محددة مسبقاً للحالات الشائعة

BINANCE_API_BREAKER_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception,
    name="binance_api"
)

DATA_PROVIDER_BREAKER_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=Exception,
    name="data_provider"
)

TRADING_BREAKER_CONFIG = CircuitBreakerConfig(
    failure_threshold=2,
    recovery_timeout=120,
    expected_exception=Exception,
    name="trading_operations"
)
