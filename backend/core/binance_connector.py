"""
🔌 Binance Connector - اتصال دائم ومستقل بـ Binance للنظام الخلفي
================================================================

يوفر:
1. اتصال دائم ومستقل عن مفاتيح المستخدمين
2. دعم endpoints متعددة (api1, api2, api3, api4)
3. Failover تلقائي بين الـ endpoints
4. دعم Proxy كخيار بديل
5. إعادة الاتصال التلقائي عند الانقطاع
6. تخزين مؤقت ذكي للبيانات
7. Health Check دوري

هذا الملف مخصص للنظام الخلفي فقط (Group B)
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# استيراد Binance Client
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException, BinanceRequestException

    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    logger.error("❌ مكتبة python-binance غير متوفرة")


# ============================================================
# إعدادات الاتصال
# ============================================================

# مفاتيح API للنظام الخلفي (من متغيرات البيئة - لا تُكتب في الكود)
BACKEND_API_KEY = os.getenv("BINANCE_BACKEND_API_KEY", "")
BACKEND_API_SECRET = os.getenv("BINANCE_BACKEND_API_SECRET", "")

# قائمة الـ endpoints البديلة
BINANCE_ENDPOINTS = [
    "https://api.binance.com",  # الرئيسي
    "https://api1.binance.com",  # بديل 1
    "https://api2.binance.com",  # بديل 2
    "https://api3.binance.com",  # بديل 3
    "https://api4.binance.com",  # بديل 4
]

# إعدادات الاتصال
CONNECTION_CONFIG = {
    "timeout": 30,  # مهلة الاتصال بالثواني
    "max_retries": 5,  # عدد المحاولات القصوى
    "retry_delay": 2,  # التأخير بين المحاولات
    "health_check_interval": 30,  # فترة فحص الصحة بالثواني
    "cache_ttl": 60,  # مدة صلاحية التخزين المؤقت
}

# إعدادات Proxy (اختياري)
PROXY_CONFIG = {
    "enabled": False,
    "http": None,  # مثال: 'http://proxy.example.com:8080'
    "https": None,  # مثال: 'https://proxy.example.com:8080'
}


class BinanceConnector:
    """
    موصل Binance الدائم للنظام الخلفي
    يضمن اتصال مستمر ومستقر مع Binance API
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern - نسخة واحدة فقط"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # حالة الاتصال
        self._client: Optional[Client] = None
        self._is_connected = False
        self._current_endpoint_index = 0
        self._last_successful_endpoint = None

        # إحصائيات
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "endpoint_switches": 0,
            "reconnections": 0,
            "last_success": None,
            "last_failure": None,
        }

        # التخزين المؤقت
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

        # Health Check
        self._health_check_thread = None
        self._stop_health_check = threading.Event()

        # قفل الاتصال
        self._connection_lock = threading.Lock()

        # تهيئة الاتصال
        self._initialize_connection()

        logger.info("✅ تم تهيئة Binance Connector للنظام الخلفي")

    def _initialize_connection(self) -> bool:
        """تهيئة الاتصال بـ Binance"""
        if not BINANCE_AVAILABLE:
            logger.error("❌ مكتبة python-binance غير متوفرة")
            return False

        # محاولة الاتصال بكل endpoint
        for i, endpoint in enumerate(BINANCE_ENDPOINTS):
            if self._try_connect_to_endpoint(endpoint, i):
                return True

        logger.error("❌ فشل الاتصال بجميع الـ endpoints")
        return False

    def _try_connect_to_endpoint(self, endpoint: str, index: int) -> bool:
        """محاولة الاتصال بـ endpoint معين"""
        with self._connection_lock:
            try:
                logger.info(f"🔄 محاولة الاتصال بـ {endpoint}...")

                # إعداد requests_params
                requests_params = {"timeout": CONNECTION_CONFIG["timeout"]}

                # إضافة Proxy إذا كان مفعلاً
                if PROXY_CONFIG["enabled"] and PROXY_CONFIG["https"]:
                    requests_params["proxies"] = {
                        "http": PROXY_CONFIG["http"],
                        "https": PROXY_CONFIG["https"],
                    }

                # إنشاء العميل
                # تغيير الـ base URL
                self._client = Client(
                    api_key=BACKEND_API_KEY,
                    api_secret=BACKEND_API_SECRET,
                    requests_params=requests_params,
                )

                # تغيير الـ endpoint
                self._client.API_URL = endpoint + "/api"

                # اختبار الاتصال
                self._client.ping()

                self._is_connected = True
                self._current_endpoint_index = index
                self._last_successful_endpoint = endpoint
                self._stats["last_success"] = datetime.now()

                logger.info(f"✅ تم الاتصال بنجاح بـ {endpoint}")
                return True

            except Exception as e:
                logger.debug(f"تأخير في الاتصال بـ {endpoint}: {e}")
                self._is_connected = False
                return False

    def _switch_to_next_endpoint(self) -> bool:
        """التبديل إلى الـ endpoint التالي"""
        self._stats["endpoint_switches"] += 1

        # جرب كل الـ endpoints بدءاً من التالي
        for i in range(len(BINANCE_ENDPOINTS)):
            next_index = (self._current_endpoint_index + 1 + i) % len(
                BINANCE_ENDPOINTS
            )
            endpoint = BINANCE_ENDPOINTS[next_index]

            if self._try_connect_to_endpoint(endpoint, next_index):
                return True

        return False

    def reconnect(self) -> bool:
        """إعادة الاتصال"""
        self._stats["reconnections"] += 1
        logger.info("🔄 محاولة إعادة الاتصال...")

        # أولاً: جرب الـ endpoint الأخير الناجح
        if self._last_successful_endpoint:
            if self._try_connect_to_endpoint(
                self._last_successful_endpoint,
                BINANCE_ENDPOINTS.index(self._last_successful_endpoint),
            ):
                return True

        # ثانياً: جرب كل الـ endpoints
        return self._initialize_connection()

    def _ensure_connected(self) -> bool:
        """التأكد من الاتصال قبل أي عملية"""
        if self._is_connected and self._client:
            return True

        return self.reconnect()

    def _execute_with_failover(
        self, func: Callable, cache_key: str = None, cache_ttl: int = None
    ) -> Any:
        """
        تنفيذ عملية مع Failover تلقائي

        Args:
            func: الدالة المراد تنفيذها
            cache_key: مفتاح التخزين المؤقت
            cache_ttl: مدة صلاحية التخزين
        """
        self._stats["total_requests"] += 1

        # محاولة الحصول من التخزين المؤقت
        if cache_key:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                return cached

        last_error = None

        # محاولة التنفيذ مع Failover
        for attempt in range(CONNECTION_CONFIG["max_retries"]):
            try:
                # التأكد من الاتصال
                if not self._ensure_connected():
                    raise ConnectionError("غير متصل بـ Binance")

                # تنفيذ العملية
                result = func()

                # تحديث الإحصائيات
                self._stats["successful_requests"] += 1
                self._stats["last_success"] = datetime.now()

                # تخزين النتيجة
                if cache_key:
                    self._set_cache(cache_key, result, cache_ttl)

                return result

            except (BinanceAPIException, BinanceRequestException) as e:
                last_error = e
                self._stats["failed_requests"] += 1
                self._stats["last_failure"] = datetime.now()

                if attempt < CONNECTION_CONFIG["max_retries"] - 1:
                    logger.info(
                        f"⚠️ خطأ Binance عابر (محاولة {attempt + 1}/{CONNECTION_CONFIG['max_retries']}): {e}"
                    )
                else:
                    logger.warning(f"⚠️ فشل Binance بعد {
                        attempt + 1} محاولات: {e}")

                # أخطاء لا تستحق Failover
                if hasattr(e, "code") and e.code in [
                    -1000,
                    -1001,
                    -1002,
                    -2015,
                ]:
                    break

                # محاولة التبديل للـ endpoint التالي
                if attempt < CONNECTION_CONFIG["max_retries"] - 1:
                    self._is_connected = False
                    if not self._switch_to_next_endpoint():
                        time.sleep(CONNECTION_CONFIG["retry_delay"])

            except Exception as e:
                last_error = e
                self._stats["failed_requests"] += 1
                self._stats["last_failure"] = datetime.now()
                self._is_connected = False

                if attempt < CONNECTION_CONFIG["max_retries"] - 1:
                    logger.info(
                        f"⚠️ خطأ اتصال عابر (محاولة {attempt + 1}/{CONNECTION_CONFIG['max_retries']}): {e}"
                    )
                else:
                    logger.warning(f"⚠️ فشل الاتصال بعد {
                        attempt + 1} محاولات: {e}")

                # محاولة التبديل للـ endpoint التالي
                if attempt < CONNECTION_CONFIG["max_retries"] - 1:
                    if not self._switch_to_next_endpoint():
                        time.sleep(CONNECTION_CONFIG["retry_delay"])

        # محاولة استخدام البيانات المخزنة كـ Fallback
        if cache_key:
            with self._cache_lock:
                if cache_key in self._cache:
                    logger.info(f"🔀 استخدام البيانات المخزنة كـ Fallback")
                    return self._cache[cache_key]["data"]

        raise last_error if last_error else Exception("فشل غير معروف")

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """الحصول من التخزين المؤقت"""
        with self._cache_lock:
            if key in self._cache:
                entry = self._cache[key]
                if datetime.now() < entry["expires"]:
                    return entry["data"]
                else:
                    del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any, ttl: int = None):
        """تخزين في التخزين المؤقت"""
        ttl = ttl or CONNECTION_CONFIG["cache_ttl"]
        with self._cache_lock:
            self._cache[key] = {
                "data": data,
                "expires": datetime.now() + timedelta(seconds=ttl),
            }

    # ============================================================
    # API Methods
    # ============================================================

    def ping(self) -> bool:
        """اختبار الاتصال"""
        try:
            self._execute_with_failover(
                lambda: self._client.ping(), cache_key=None
            )
            return True
        except Exception:
            return False

    def get_server_time(self) -> Dict:
        """الحصول على وقت الخادم"""
        return self._execute_with_failover(
            lambda: self._client.get_server_time(),
            cache_key="server_time",
            cache_ttl=5,
        )

    def get_ticker(self, symbol: str = None) -> Any:
        """الحصول على بيانات Ticker"""
        cache_key = f"ticker_{symbol}" if symbol else "ticker_all"

        if symbol:
            return self._execute_with_failover(
                lambda: self._client.get_ticker(symbol=symbol),
                cache_key=cache_key,
                cache_ttl=10,
            )
        else:
            return self._execute_with_failover(
                lambda: self._client.get_ticker(),
                cache_key=cache_key,
                cache_ttl=10,
            )

    def get_symbol_ticker(self, symbol: str = None) -> Any:
        """الحصول على سعر الرمز"""
        cache_key = (
            f"symbol_ticker_{symbol}" if symbol else "symbol_ticker_all"
        )

        if symbol:
            return self._execute_with_failover(
                lambda: self._client.get_symbol_ticker(symbol=symbol),
                cache_key=cache_key,
                cache_ttl=5,
            )
        else:
            return self._execute_with_failover(
                lambda: self._client.get_symbol_ticker(),
                cache_key=cache_key,
                cache_ttl=5,
            )

    def get_current_price(self, symbol: str) -> float:
        """الحصول على السعر الحالي لعملة"""
        ticker = self.get_symbol_ticker(symbol)
        return float(ticker["price"])

    def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
        start_str: str = None,
        end_str: str = None,
    ) -> List:
        """الحصول على بيانات الشموع"""
        cache_key = f"klines_{symbol}_{interval}_{limit}"

        def fetch():
            kwargs = {"symbol": symbol, "interval": interval, "limit": limit}
            if start_str:
                kwargs["start_str"] = start_str
            if end_str:
                kwargs["end_str"] = end_str
            return self._client.get_klines(**kwargs)

        return self._execute_with_failover(
            fetch, cache_key=cache_key, cache_ttl=30
        )

    def get_exchange_info(self) -> Dict:
        """الحصول على معلومات البورصة"""
        return self._execute_with_failover(
            lambda: self._client.get_exchange_info(),
            cache_key="exchange_info",
            cache_ttl=3600,
        )

    def get_all_tickers(self) -> List:
        """الحصول على جميع الأسعار"""
        return self._execute_with_failover(
            lambda: self._client.get_all_tickers(),
            cache_key="all_tickers",
            cache_ttl=10,
        )

    def get_orderbook_tickers(self) -> List:
        """الحصول على أفضل أسعار العرض والطلب"""
        return self._execute_with_failover(
            lambda: self._client.get_orderbook_tickers(),
            cache_key="orderbook_tickers",
            cache_ttl=5,
        )

    def get_24h_ticker(self, symbol: str = None) -> Any:
        """الحصول على إحصائيات 24 ساعة"""
        cache_key = f"24h_ticker_{symbol}" if symbol else "24h_ticker_all"

        if symbol:
            return self._execute_with_failover(
                lambda: self._client.get_ticker(symbol=symbol),
                cache_key=cache_key,
                cache_ttl=60,
            )
        else:
            return self._execute_with_failover(
                lambda: self._client.get_ticker(),
                cache_key=cache_key,
                cache_ttl=60,
            )

    def get_top_volume_coins(
        self, limit: int = 100, min_volume: float = 1000000
    ) -> List[str]:
        """الحصول على العملات الأعلى حجماً"""
        try:
            tickers = self.get_24h_ticker()

            # فلترة أزواج USDT
            usdt_pairs = [t for t in tickers if t["symbol"].endswith("USDT")]

            # فلترة حسب الحجم
            filtered = []
            for ticker in usdt_pairs:
                try:
                    volume = float(ticker.get("quoteVolume", 0))
                    if volume >= min_volume:
                        filtered.append(ticker)
                except Exception:
                    continue

            # ترتيب حسب الحجم
            sorted_pairs = sorted(
                filtered, key=lambda x: float(x["quoteVolume"]), reverse=True
            )

            # استخراج الرموز
            return [t["symbol"] for t in sorted_pairs[:limit]]

        except Exception as e:
            logger.error(f"❌ خطأ في جلب العملات الأعلى حجماً: {e}")
            return []

    # ============================================================
    # Health Check
    # ============================================================

    def start_health_check(self, interval: int = None):
        """بدء فحص الصحة الدوري"""
        if self._health_check_thread and self._health_check_thread.is_alive():
            return

        interval = interval or CONNECTION_CONFIG["health_check_interval"]
        self._stop_health_check.clear()
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            args=(interval,),
            daemon=True,
            name="BinanceHealthCheck",
        )
        self._health_check_thread.start()
        logger.info(f"🏥 بدء فحص صحة Binance (كل {interval} ثانية)")

    def stop_health_check(self):
        """إيقاف فحص الصحة"""
        self._stop_health_check.set()
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)
        logger.info("⏹️ تم إيقاف فحص صحة Binance")

    def _health_check_loop(self, interval: int):
        """حلقة فحص الصحة"""
        while not self._stop_health_check.is_set():
            try:
                if not self.ping():
                    logger.warning(
                        "⚠️ فشل فحص صحة Binance - محاولة إعادة الاتصال..."
                    )
                    self.reconnect()

                self._stop_health_check.wait(timeout=interval)

            except Exception as e:
                logger.error(f"❌ خطأ في فحص الصحة: {e}")
                time.sleep(10)

    # ============================================================
    # إحصائيات ومعلومات
    # ============================================================

    @property
    def is_connected(self) -> bool:
        """حالة الاتصال"""
        return self._is_connected

    @property
    def current_endpoint(self) -> str:
        """الـ endpoint الحالي"""
        return BINANCE_ENDPOINTS[self._current_endpoint_index]

    def get_stats(self) -> Dict[str, Any]:
        """الحصول على الإحصائيات"""
        return {
            **self._stats,
            "is_connected": self._is_connected,
            "current_endpoint": self.current_endpoint,
            "cache_size": len(self._cache),
        }

    def get_connection_status(self) -> Dict[str, Any]:
        """الحصول على حالة الاتصال"""
        return {
            "is_connected": self._is_connected,
            "current_endpoint": self.current_endpoint,
            "last_successful_endpoint": self._last_successful_endpoint,
            "available_endpoints": BINANCE_ENDPOINTS,
            "stats": self.get_stats(),
        }

    def clear_cache(self):
        """مسح التخزين المؤقت"""
        with self._cache_lock:
            self._cache.clear()
        logger.info("🗑️ تم مسح التخزين المؤقت")


# ============================================================
# Singleton accessor
# ============================================================

_binance_connector: Optional[BinanceConnector] = None
_connector_lock = threading.Lock()


def get_binance_connector() -> BinanceConnector:
    """
    الحصول على موصل Binance (Singleton)

    هذه الدالة تُستخدم من Group B للحصول على اتصال دائم
    """
    global _binance_connector

    with _connector_lock:
        if _binance_connector is None:
            _binance_connector = BinanceConnector()

    return _binance_connector


# ============================================================
# دوال مساعدة للاستخدام المباشر
# ============================================================


def get_current_price(symbol: str) -> float:
    """الحصول على السعر الحالي لعملة"""
    return get_binance_connector().get_current_price(symbol)


def get_klines(symbol: str, interval: str, limit: int = 500) -> List:
    """الحصول على بيانات الشموع"""
    return get_binance_connector().get_klines(symbol, interval, limit)


def get_top_volume_coins(limit: int = 100) -> List[str]:
    """الحصول على العملات الأعلى حجماً"""
    return get_binance_connector().get_top_volume_coins(limit)


def is_binance_connected() -> bool:
    """فحص حالة الاتصال"""
    return get_binance_connector().is_connected
