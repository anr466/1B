"""
🔄 Retry Logic - نظام المحاولات المتكررة
يوفر decorators لإعادة محاولة العمليات الفاشلة مع Exponential Backoff
"""

import time
import logging
from functools import wraps
from typing import Callable, Any, Type, Tuple

logger = logging.getLogger(__name__)


class RetryConfig:
    """إعدادات نظام المحاولات المتكررة"""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 32.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Args:
            max_attempts: عدد المحاولات الأقصى
            initial_delay: التأخير الأولي بالثواني
            max_delay: التأخير الأقصى بالثواني
            exponential_base: أساس الزيادة الأسية
            jitter: إضافة عشوائية للتأخير
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """حساب التأخير للمحاولة الحالية"""
        delay = min(
            self.initial_delay * (self.exponential_base**attempt),
            self.max_delay,
        )

        if self.jitter:
            import random

            delay = delay * (0.5 + random.random())

        return delay


# إعدادات محددة مسبقاً
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    initial_delay=1.0,
    max_delay=32.0,
    exponential_base=2.0,
    jitter=True,
)

AGGRESSIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=0.5,
    max_delay=16.0,
    exponential_base=2.0,
    jitter=True,
)

CONSERVATIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    initial_delay=2.0,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=False,
)


def retry(
    config: RetryConfig = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Callable = None,
    on_failure: Callable = None,
):
    """
    Decorator لإعادة محاولة دالة عند الفشل

    Args:
        config: إعدادات المحاولات (استخدم DEFAULT_RETRY_CONFIG إذا لم يُحدد)
        exceptions: أنواع الاستثناءات التي تستدعي إعادة المحاولة
        on_retry: دالة callback عند إعادة المحاولة
        on_failure: دالة callback عند الفشل النهائي

    مثال:
        @retry(config=DEFAULT_RETRY_CONFIG, exceptions=(ConnectionError, TimeoutError))
        def fetch_data():
            return requests.get('http://api.example.com/data')
    """
    if config is None:
        config = DEFAULT_RETRY_CONFIG

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    logger.debug(
                        f"🔄 محاولة {attempt + 1}/{config.max_attempts} لـ {func.__name__}"
                    )
                    result = func(*args, **kwargs)

                    if attempt > 0:
                        logger.info(f"✅ نجحت المحاولة {
                            attempt +
                            1} لـ {
                            func.__name__}")

                    return result

                except exceptions as e:
                    last_exception = e

                    if attempt < config.max_attempts - 1:
                        delay = config.get_delay(attempt)
                        logger.warning(f"⚠️ فشلت المحاولة {
                            attempt +
                            1} لـ {
                            func.__name__}: {e}. " f"إعادة المحاولة بعد {
                            delay:.2f} ثانية...")

                        if on_retry:
                            on_retry(attempt + 1, delay, e)

                        time.sleep(delay)
                    else:
                        logger.error(f"❌ فشلت جميع المحاولات ({
                            config.max_attempts}) لـ {
                            func.__name__}: {e}")

                        if on_failure:
                            on_failure(config.max_attempts, e)

            raise (
                last_exception
                if last_exception
                else Exception(f"فشلت جميع المحاولات ({
                    config.max_attempts}) لـ {
                    func.__name__}")
            )

        return wrapper

    return decorator


# Decorators محددة مسبقاً للاستخدام الشائع


def retry_default(func: Callable) -> Callable:
    """Retry مع الإعدادات الافتراضية (3 محاولات)"""
    return retry(config=DEFAULT_RETRY_CONFIG)(func)


def retry_aggressive(func: Callable) -> Callable:
    """Retry عدواني (5 محاولات مع تأخير قصير)"""
    return retry(config=AGGRESSIVE_RETRY_CONFIG)(func)


def retry_conservative(func: Callable) -> Callable:
    """Retry محافظ (محاولتان فقط مع تأخير طويل)"""
    return retry(config=CONSERVATIVE_RETRY_CONFIG)(func)


def retry_on_network_error(func: Callable) -> Callable:
    """Retry للأخطاء الشبكية"""
    return retry(
        config=AGGRESSIVE_RETRY_CONFIG,
        exceptions=(ConnectionError, TimeoutError, OSError, Exception),
    )(func)


def retry_on_api_error(func: Callable) -> Callable:
    """Retry لأخطاء API"""
    return retry(config=DEFAULT_RETRY_CONFIG, exceptions=(Exception,))(func)


class RetryableOperation:
    """فئة لتنفيذ عملية قابلة للمحاولة المتكررة"""

    def __init__(self, config: RetryConfig = None):
        self.config = config or DEFAULT_RETRY_CONFIG
        self.attempts = 0
        self.last_exception = None

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """تنفيذ عملية مع المحاولات المتكررة"""
        for attempt in range(self.config.max_attempts):
            self.attempts = attempt + 1

            try:
                logger.debug(
                    f"🔄 محاولة {self.attempts}/{self.config.max_attempts}"
                )
                result = func(*args, **kwargs)

                if attempt > 0:
                    logger.info(f"✅ نجحت المحاولة {self.attempts}")

                return result

            except Exception as e:
                self.last_exception = e

                if attempt < self.config.max_attempts - 1:
                    delay = self.config.get_delay(attempt)
                    logger.warning(
                        f"⚠️ فشلت المحاولة {self.attempts}: {e}. "
                        f"إعادة المحاولة بعد {delay:.2f} ثانية..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"❌ فشلت جميع المحاولات ({
                        self.config.max_attempts}): {e}")

        raise (
            self.last_exception
            if self.last_exception
            else Exception(f"فشلت جميع المحاولات ({self.config.max_attempts})")
        )

    def get_stats(self) -> dict:
        """الحصول على إحصائيات المحاولات"""
        return {
            "total_attempts": self.attempts,
            "max_attempts": self.config.max_attempts,
            "last_exception": (
                str(self.last_exception) if self.last_exception else None
            ),
            "success": self.last_exception is None,
        }
