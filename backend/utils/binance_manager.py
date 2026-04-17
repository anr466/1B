"""
مدير Binance API - للتعامل مع حسابات المستخدمين الحقيقية
يوفر واجهة آمنة للتفاعل مع Binance API
"""

from backend.utils.trading_context import get_effective_is_demo
from backend.infrastructure.db_access import get_db_manager
import os
import logging
import json
import time
import threading
from datetime import datetime
from typing import Dict, Optional, Any, Tuple
from decimal import Decimal
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "database"))

# استيراد خدمة التشفير الموحدة
try:
    from config.security.encryption_service import decrypt_text

    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False


class BinanceManager:
    """مدير Binance API للمستخدمين"""

    _shared_clients: Dict[int, Client] = {}
    _shared_balance_cache: Dict[int, Dict[str, Any]] = {}
    _shared_balance_locks: Dict[int, threading.Lock] = {}
    _shared_guard_lock = threading.Lock()

    # FIX 4: Circuit breaker + retry state
    _client_failures: Dict[int, int] = {}
    _client_circuit_open: Dict[int, float] = {}
    _client_failure_lock = threading.Lock()
    _circuit_threshold = 5
    _circuit_recovery_seconds = 120

    def __init__(self):
        self.db_manager = get_db_manager()
        self.logger = logging.getLogger(__name__)
        self._clients = self.__class__._shared_clients
        self._balance_cache = self.__class__._shared_balance_cache
        self._balance_cache_ttl_seconds = 2

    # FIX 3: Encryption method — fails explicitly if encryption unavailable
    def _encrypt_api_secret(self, api_secret: str, user_id: int) -> str:
        """تشفير المفتاح السري — يفشل صراحةً إذا لم يكن التشفير متاحاً"""
        if ENCRYPTION_AVAILABLE:
            try:
                from config.security.encryption_service import encrypt_text

                return encrypt_text(api_secret)
            except Exception as e:
                self.logger.error(f"خطأ في تشفير المفتاح السري للمستخدم {user_id}: {e}")
                raise RuntimeError(
                    f"فشل تشفير مفتاح API للمستخدم {user_id}: {e}. "
                    "لا يمكن حفظ المفاتيح بدون تشفير."
                )
        else:
            self.logger.error(
                f"⚠️ خدمة التشفير غير متاحة — لا يمكن حفظ مفاتيح API للمستخدم {user_id}. "
                "يجب تفعيل ENCRYPTION_AVAILABLE."
            )
            raise RuntimeError(
                f"Encryption service unavailable for user {user_id}. "
                "Cannot save API keys without encryption."
            )

    def _get_balance_lock(self, user_id: int) -> threading.Lock:
        with self.__class__._shared_guard_lock:
            lock = self.__class__._shared_balance_locks.get(user_id)
            if lock is None:
                lock = threading.Lock()
                self.__class__._shared_balance_locks[user_id] = lock
            return lock

    # FIX 4: Circuit breaker methods
    def _record_client_failure(self, user_id: int):
        with self.__class__._client_failure_lock:
            self.__class__._client_failures[user_id] = (
                self.__class__._client_failures.get(user_id, 0) + 1
            )
            if (
                self.__class__._client_failures[user_id]
                >= self.__class__._circuit_threshold
            ):
                self.__class__._client_circuit_open[user_id] = time.time()
                self.logger.warning(
                    f"⚡ Circuit OPEN for User {user_id}: "
                    f"{self.__class__._client_failures[user_id]} consecutive failures"
                )

    def _record_client_success(self, user_id: int):
        with self.__class__._client_failure_lock:
            self.__class__._client_failures.pop(user_id, None)
            self.__class__._client_circuit_open.pop(user_id, None)

    def _is_circuit_open(self, user_id: int) -> bool:
        with self.__class__._client_failure_lock:
            open_at = self.__class__._client_circuit_open.get(user_id)
            if open_at is None:
                return False
            if time.time() - open_at > self.__class__._circuit_recovery_seconds:
                self.__class__._client_circuit_open.pop(user_id, None)
                self.logger.info(
                    f"🔓 Circuit HALF-OPEN for User {user_id}: testing recovery"
                )
                return False
            return True

    def invalidate_client(self, user_id: int):
        """إبطال عميل Binance المخزن — يُستدعى عند تحديث المفاتيح"""
        with self.__class__._shared_guard_lock:
            self.__class__._shared_clients.pop(user_id, None)
        with self.__class__._client_failure_lock:
            self.__class__._client_failures.pop(user_id, None)
            self.__class__._client_circuit_open.pop(user_id, None)
        self.logger.info(f"🔄 Client invalidated for User {user_id}")

    def _decrypt_api_keys(self, encrypted_key: str, encrypted_secret: str) -> tuple:
        """فك تشفير مفاتيح API باستخدام خدمة التشفير الموحدة"""
        try:
            if ENCRYPTION_AVAILABLE:
                api_key = decrypt_text(encrypted_key)
                api_secret = decrypt_text(encrypted_secret)
                return api_key, api_secret
            else:
                # Fallback: المفاتيح غير مشفرة
                return encrypted_key, encrypted_secret
        except Exception as e:
            self.logger.error(f"خطأ في فك تشفير المفاتيح: {e}")
            # محاولة إرجاع المفاتيح كما هي (ربما غير مشفرة)
            return encrypted_key, encrypted_secret

    def save_user_api_keys(
        self,
        user_id: int,
        api_key: str,
        api_secret: str,
        is_testnet: bool = True,
    ) -> bool:
        """حفظ مفاتيح API للمستخدم"""
        try:
            # تشفير المفتاح السري
            encrypted_secret = self._encrypt_api_secret(api_secret, user_id)

            with self.db_manager.get_write_connection() as conn:
                # حذف المفاتيح القديمة إن وجدت
                conn.execute(
                    "DELETE FROM user_binance_keys WHERE user_id = %s",
                    (user_id,),
                )

                # إدراج المفاتيح الجديدة
                conn.execute(
                    """
                    INSERT INTO user_binance_keys
                    (user_id, api_key, api_secret, is_testnet, is_active)
                    VALUES (%s, %s, %s, %s, FALSE)
                """,
                    (user_id, api_key, encrypted_secret, is_testnet),
                )

            # FIX 4: Invalidate cached client so new keys are picked up
            self.invalidate_client(user_id)

            self.logger.info(f"تم حفظ مفاتيح API للمستخدم {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"خطأ في حفظ مفاتيح API: {e}")
            return False

    def verify_user_api_keys(self, user_id: int) -> Dict[str, Any]:
        """التحقق من صحة مفاتيح API للمستخدم"""
        try:
            # جلب مفاتيح المستخدم
            api_data = self.get_user_api_keys(user_id)
            if not api_data:
                return {"success": False, "message": "لا توجد مفاتيح API"}

            # إنشاء عميل Binance
            client = self._get_binance_client(user_id)
            if not client:
                return {
                    "success": False,
                    "message": "فشل في إنشاء عميل Binance",
                }

            # اختبار الاتصال
            account_info = client.get_account()

            # استخراج الصلاحيات
            permissions = []
            if account_info.get("canTrade"):
                permissions.append("spot")
            if account_info.get("canWithdraw"):
                permissions.append("withdraw")
            if account_info.get("canDeposit"):
                permissions.append("deposit")

            # تحديث بيانات التحقق
            with self.db_manager.get_write_connection() as conn:
                conn.execute(
                    """
                    UPDATE user_binance_keys SET is_active = TRUE,
                        permissions = %s,
                        last_verified = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """,
                    (json.dumps(permissions), user_id),
                )

            # FIX 4: Invalidate cached client to pick up verified keys
            self.invalidate_client(user_id)

            # مزامنة الرصيد
            self.sync_user_balance(user_id)

            return {
                "success": True,
                "message": "تم التحقق بنجاح",
                "permissions": permissions,
                "account_type": account_info.get("accountType", "SPOT"),
            }

        except BinanceAPIException as e:
            self.logger.error(f"خطأ Binance API: {e}")
            return {"success": False, "message": f"خطأ في API: {e.message}"}
        except Exception as e:
            self.logger.error(f"خطأ في التحقق من API: {e}")
            return {"success": False, "message": f"خطأ غير متوقع: {str(e)}"}

    def get_user_api_keys(self, user_id: int) -> Optional[Dict[str, Any]]:
        """جلب مفاتيح API للمستخدم"""
        try:
            with self.db_manager.get_connection() as conn:
                row = conn.execute(
                    """
                    SELECT api_key, api_secret, is_testnet, is_active, permissions, last_verified
                    FROM user_binance_keys
                    WHERE user_id = %s
                """,
                    (user_id,),
                ).fetchone()

                if row:
                    return {
                        "api_key": row[0],
                        "api_secret": row[1],
                        "is_testnet": bool(row[2]),
                        "is_active": bool(row[3]),
                        "permissions": json.loads(row[4]) if row[4] else [],
                        "last_verified": row[5],
                    }

                allow_env_keys = (
                    os.getenv("ALLOW_ENV_BINANCE_KEYS_FOR_TESTING") or ""
                ).strip().lower() in ("1", "true", "yes", "on")
                env_api_key = (os.getenv("BINANCE_BACKEND_API_KEY") or "").strip()
                env_api_secret = (os.getenv("BINANCE_BACKEND_API_SECRET") or "").strip()
                if allow_env_keys and env_api_key and env_api_secret:
                    self.logger.info(
                        f"✅ استخدام مفاتيح Binance من البيئة للمستخدم {user_id} داخل BinanceManager في وضع الاختبار"
                    )
                    return {
                        "api_key": env_api_key,
                        "api_secret": env_api_secret,
                        "is_testnet": False,
                        "is_active": True,
                        "permissions": [],
                        "last_verified": None,
                    }

                return None

        except Exception as e:
            self.logger.error(f"خطأ في جلب مفاتيح API: {e}")
            return None

    # FIX: Working endpoints for BinanceManager (bypasses geo-block)
    _BINANCE_ENDPOINTS = [
        "https://www.binance.com",
        "https://api1.binance.com",
        "https://api3.binance.com",
        "https://api.binance.com",
    ]

    def _get_binance_client(self, user_id: int) -> Optional[Client]:
        """إنشاء عميل Binance للمستخدم مع endpoint failover + circuit breaker"""
        try:
            # FIX 4: Check circuit breaker
            if self._is_circuit_open(user_id):
                self.logger.warning(
                    f"⚡ Circuit OPEN — refusing client for User {user_id}"
                )
                return None

            # التحقق من التخزين المؤقت
            if user_id in self._clients:
                return self._clients[user_id]

            # جلب مفاتيح المستخدم
            api_data = self.get_user_api_keys(user_id)
            if not api_data or not api_data["is_active"]:
                return None

            # فك تشفير المفاتيح باستخدام خدمة التشفير الموحدة
            api_key, api_secret = self._decrypt_api_keys(
                api_data["api_key"], api_data["api_secret"]
            )

            # FIX: Try each endpoint until one works
            client = None
            for endpoint in self._BINANCE_ENDPOINTS:
                try:
                    client = Client(
                        api_key=api_key,
                        api_secret=api_secret,
                        testnet=api_data["is_testnet"],
                        requests_params={"timeout": 10},
                    )
                    client.API_URL = f"{endpoint}/api"
                    client.PRIVATE_API_URL = f"{endpoint}/api"
                    client.ping()
                    self.logger.info(
                        f"✅ Binance client for User {user_id} using {endpoint}"
                    )
                    break
                except Exception as endpoint_err:
                    self.logger.debug(
                        f"⚠️ Endpoint {endpoint} failed for User {user_id}: {endpoint_err}"
                    )
                    client = None
                    continue

            if client is None:
                self.logger.error(f"❌ All Binance endpoints failed for User {user_id}")
                self._record_client_failure(user_id)
                return None

            # FIX 4: Test connection before caching
            self._record_client_success(user_id)

            # حفظ في التخزين المؤقت
            self._clients[user_id] = client

            return client

        except Exception as e:
            self.logger.error(f"خطأ في إنشاء عميل Binance: {e}")
            self._record_client_failure(user_id)
            return None

    def _get_asset_usdt_price(self, client: Client, asset: str) -> Decimal:
        asset = (asset or "").upper()
        if not asset:
            return Decimal("0")
        if asset in {"USDT", "USD"}:
            return Decimal("1")
        if asset in {"USDC", "BUSD", "FDUSD", "TUSD", "USDP"}:
            return Decimal("1")

        pairs_to_try = [
            f"{asset}USDT",
            f"{asset}USDC",
            f"{asset}BUSD",
            f"{asset}FDUSD",
        ]
        for symbol in pairs_to_try:
            try:
                ticker = client.get_symbol_ticker(symbol=symbol)
                if ticker and ticker.get("price"):
                    return Decimal(str(ticker["price"]))
            except Exception:
                continue
        return Decimal("0")

    def _summarize_account_balances(
        self, client: Client, account_info: Dict[str, Any]
    ) -> Tuple[Decimal, Decimal, Decimal]:
        total_usdt = Decimal("0")
        free_usdt = Decimal("0")
        locked_usdt = Decimal("0")

        for balance in account_info.get("balances", []):
            asset = balance.get("asset")
            free = Decimal(str(balance.get("free", "0") or "0"))
            locked = Decimal(str(balance.get("locked", "0") or "0"))
            total = free + locked
            if total <= 0:
                continue

            price = self._get_asset_usdt_price(client, asset)
            if price <= 0:
                continue

            free_usdt += free * price
            locked_usdt += locked * price
            total_usdt += total * price

        return total_usdt, free_usdt, locked_usdt

    def _get_cached_balance_summary(self, user_id: int) -> Optional[Dict[str, float]]:
        cached = self._balance_cache.get(user_id)
        if not cached:
            return None
        cached_at = cached.get("cached_at")
        if (
            not cached_at
            or (datetime.now() - cached_at).total_seconds()
            > self._balance_cache_ttl_seconds
        ):
            self._balance_cache.pop(user_id, None)
            return None
        return {
            "total_usdt": float(cached.get("total_usdt", 0.0) or 0.0),
            "free_usdt": float(cached.get("free_usdt", 0.0) or 0.0),
            "locked_usdt": float(cached.get("locked_usdt", 0.0) or 0.0),
        }

    def _set_cached_balance_summary(
        self,
        user_id: int,
        total_usdt: Decimal,
        free_usdt: Decimal,
        locked_usdt: Decimal,
    ) -> None:
        self._balance_cache[user_id] = {
            "cached_at": datetime.now(),
            "total_usdt": float(total_usdt),
            "free_usdt": float(free_usdt),
            "locked_usdt": float(locked_usdt),
        }

    def sync_user_balance(self, user_id: int) -> bool:
        """مزامنة رصيد المستخدم من Binance"""
        try:
            cached_summary = self._get_cached_balance_summary(user_id)
            if cached_summary is not None:
                return True

            balance_lock = self._get_balance_lock(user_id)
            with balance_lock:
                cached_summary = self._get_cached_balance_summary(user_id)
                if cached_summary is not None:
                    return True

                client = self._get_binance_client(user_id)
                if not client:
                    return False

                account_info = client.get_account()

                with self.db_manager.get_write_connection() as conn:
                    conn.execute(
                        "DELETE FROM user_binance_balance WHERE user_id = %s",
                        (user_id,),
                    )

                    for balance in account_info["balances"]:
                        asset = balance["asset"]
                        free = Decimal(balance["free"])
                        locked = Decimal(balance["locked"])
                        total = free + locked

                        if total > 0:
                            conn.execute(
                                """
                                INSERT INTO user_binance_balance
                                (user_id, asset, free_balance, locked_balance, total_balance)
                                VALUES (%s, %s, %s, %s, %s)
                            """,
                                (
                                    user_id,
                                    asset,
                                    float(free),
                                    float(locked),
                                    float(total),
                                ),
                            )

                    total_usdt, free_usdt, locked_usdt = (
                        self._summarize_account_balances(client, account_info)
                    )
                    self._set_cached_balance_summary(
                        user_id, total_usdt, free_usdt, locked_usdt
                    )

                    conn.execute(
                        """
                        INSERT INTO portfolio (user_id, total_balance, available_balance, is_demo, updated_at)
                        VALUES (%s, %s, %s, FALSE, CURRENT_TIMESTAMP)
                        ON CONFLICT(user_id, is_demo) DO UPDATE SET
                        total_balance = excluded.total_balance,
                        available_balance = excluded.available_balance,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                        (user_id, float(total_usdt), float(free_usdt)),
                    )

            self.logger.info(f"تم مزامنة رصيد المستخدم {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"خطأ في مزامنة الرصيد: {e}")
            return False

    def execute_buy_order(
        self,
        user_id: int,
        symbol: str,
        quantity: float,
        order_type: str = "MARKET",
        price: float = None,
    ) -> Dict[str, Any]:
        """تنفيذ أمر شراء (حقيقي أو وهمي) مع سحب البيانات الفعلية"""
        try:
            is_demo_mode = bool(get_effective_is_demo(self.db_manager, user_id))
            if is_demo_mode:
                current_price = price if price else self._get_current_price(symbol)
                return self._execute_demo_buy_order(
                    user_id, symbol, quantity, current_price
                )

            if not self.is_user_api_active(user_id):
                return {
                    "success": False,
                    "message": "التداول الحقيقي يتطلب مفاتيح Binance مفعلة",
                }

            client = self._get_binance_client(user_id)
            if not client:
                return {"success": False, "message": "عميل Binance غير متاح"}

            # 🔍 الخطوة 0: فحص الرصيد قبل التنفيذ
            current_price = self._get_current_price(symbol)
            required_amount = quantity * current_price
            user_balance = self._get_user_balance(user_id)

            if user_balance < required_amount:
                self.logger.warning(
                    f"⚠️ رصيد غير كافٍ للمستخدم {user_id}: "
                    f"المطلوب={required_amount:.2f}, المتاح={user_balance:.2f}"
                )
                return {
                    "success": False,
                    "message": f"الرصيد غير كافٍ. المطلوب: {
                        required_amount:.2f}, المتاح: {user_balance:.2f}",
                    "error_code": "INSUFFICIENT_BALANCE",
                }

            # 🔄 الخطوة 0.5: فحص Idempotency - منع الصفقات المكررة
            existing_order = self.check_order_idempotency(
                user_id, symbol, "BUY", quantity
            )
            if existing_order:
                self.logger.warning(
                    f"⚠️ أمر موجود مسبقاً للمستخدم {user_id}: {
                        existing_order['order_id']
                    }"
                )
                return {
                    "success": True,
                    "order_id": existing_order["order_id"],
                    "status": existing_order["status"],
                    "message": "الأمر موجود مسبقاً",
                    "idempotent": True,
                }

            # 🚀 الخطوة 1: تنفيذ الأمر
            self.logger.info(f"🔄 إرسال أمر شراء {symbol}: {quantity}")

            if order_type == "MARKET":
                order = client.order_market_buy(symbol=symbol, quantity=quantity)
            else:
                return {
                    "success": False,
                    "message": "نوع الأمر غير مدعوم حالياً",
                }

            order_id = order.get("orderId")
            if not order_id:
                return {
                    "success": False,
                    "message": "لم يتم إرجاع order_id من Binance",
                }
            self.logger.info(f"✅ تم إرسال الأمر برقم: {order_id}")

            # 🔍 الخطوة 2: سحب بيانات الأمر الفعلية من Binance
            actual_order_data = self._fetch_real_order_data(client, symbol, order_id)

            if not actual_order_data:
                return {
                    "success": False,
                    "message": "فشل تأكيد تنفيذ الأمر من Binance بعد الانتظار",
                }

            # استخدام البيانات الحقيقية حصراً (لا fallback)
            final_order_data = actual_order_data
            self.logger.info(f"📊 تم سحب البيانات الحقيقية للأمر {order_id}")

            if not final_order_data.get("orderId"):
                return {
                    "success": False,
                    "message": "لا يوجد order_id في بيانات الأمر المؤكدة",
                }

            # 🗄️ الخطوة 3: حفظ البيانات الحقيقية في قاعدة البيانات
            self._save_real_binance_order(user_id, final_order_data)

            # 💰 الخطوة 4: مزامنة الرصيد الحقيقي
            self.sync_user_balance(user_id)

            return {
                "success": True,
                "order_id": final_order_data["orderId"],
                "symbol": final_order_data["symbol"],
                "side": final_order_data["side"],
                "quantity": final_order_data["executedQty"],
                "price": self._calculate_average_price(final_order_data),
                "status": final_order_data["status"],
                "commission": self._calculate_total_commission(final_order_data),
                "data_source": "binance_api",  # مصدر البيانات
            }

        except BinanceOrderException as e:
            self.logger.error(f"❌ خطأ في تنفيذ الأمر: {e}")
            return {"success": False, "message": f"خطأ في الأمر: {e.message}"}
        except Exception as e:
            self.logger.error(f"❌ خطأ غير متوقع في التنفيذ: {e}")
            return {"success": False, "message": f"خطأ غير متوقع: {str(e)}"}

    def execute_sell_order(
        self,
        user_id: int,
        symbol: str,
        quantity: float,
        order_type: str = "MARKET",
    ) -> Dict[str, Any]:
        """تنفيذ أمر بيع (حقيقي أو وهمي) مع سحب البيانات الفعلية"""
        try:
            is_demo_mode = bool(get_effective_is_demo(self.db_manager, user_id))
            if is_demo_mode:
                return self._execute_demo_sell_order(user_id, symbol, quantity)

            if not self.is_user_api_active(user_id):
                return {
                    "success": False,
                    "message": "التداول الحقيقي يتطلب مفاتيح Binance مفعلة",
                }

            client = self._get_binance_client(user_id)
            if not client:
                return {"success": False, "message": "عميل Binance غير متاح"}

            # 🚀 الخطوة 1: تنفيذ أمر البيع
            self.logger.info(f"🔄 إرسال أمر بيع {symbol}: {quantity}")

            if order_type == "MARKET":
                order = client.order_market_sell(symbol=symbol, quantity=quantity)
            else:
                return {
                    "success": False,
                    "message": "نوع الأمر غير مدعوم حالياً",
                }

            order_id = order.get("orderId")
            if not order_id:
                return {
                    "success": False,
                    "message": "لم يتم إرجاع order_id من Binance",
                }
            self.logger.info(f"✅ تم إرسال أمر البيع برقم: {order_id}")

            # 🔍 الخطوة 2: سحب بيانات الأمر الفعلية
            actual_order_data = self._fetch_real_order_data(client, symbol, order_id)

            if not actual_order_data:
                return {
                    "success": False,
                    "message": "فشل تأكيد تنفيذ أمر البيع من Binance بعد الانتظار",
                }

            final_order_data = actual_order_data
            self.logger.info(f"📊 تم سحب بيانات البيع الحقيقية للأمر {order_id}")

            if not final_order_data.get("orderId"):
                return {
                    "success": False,
                    "message": "لا يوجد order_id في بيانات أمر البيع المؤكدة",
                }

            # 🗄️ الخطوة 3: حفظ بيانات البيع الحقيقية
            self._save_real_binance_order(user_id, final_order_data)

            # 💰 الخطوة 4: مزامنة الرصيد
            self.sync_user_balance(user_id)

            return {
                "success": True,
                "order_id": final_order_data["orderId"],
                "symbol": final_order_data["symbol"],
                "side": final_order_data["side"],
                "quantity": final_order_data["executedQty"],
                "price": self._calculate_average_price(final_order_data),
                "status": final_order_data["status"],
                "commission": self._calculate_total_commission(final_order_data),
                "data_source": "binance_api",
            }

        except BinanceOrderException as e:
            self.logger.error(f"❌ خطأ في تنفيذ أمر البيع: {e}")
            return {"success": False, "message": f"خطأ في الأمر: {e.message}"}
        except Exception as e:
            self.logger.error(f"❌ خطأ غير متوقع في بيع: {e}")
            return {"success": False, "message": f"خطأ غير متوقع: {str(e)}"}

    def _fetch_real_order_data(
        self, client, symbol: str, order_id: str
    ) -> Dict[str, Any]:
        """سحب بيانات الأمر الحقيقية من Binance مع انتظار قصير للتأكيد"""
        try:
            import time

            max_attempts = 5
            for attempt in range(1, max_attempts + 1):
                time.sleep(1)

                order_data = client.get_order(symbol=symbol, orderId=order_id)
                if not isinstance(order_data, dict):
                    continue

                fetched_order_id = order_data.get("orderId")
                executed_qty = float(order_data.get("executedQty", 0) or 0)
                status = str(order_data.get("status", "")).upper()

                if (
                    fetched_order_id
                    and executed_qty > 0
                    and status in ["FILLED", "PARTIALLY_FILLED"]
                ):
                    self.logger.info(
                        f"🔍 تم تأكيد الأمر {order_id} من Binance "
                        f"(status={status}, executedQty={executed_qty})"
                    )
                    return order_data

                self.logger.debug(
                    f"⏳ انتظار تأكيد الأمر {order_id} "
                    f"(attempt={attempt}/{max_attempts}, status={status}, executedQty={executed_qty})"
                )

            self.logger.error(
                f"❌ تعذر تأكيد تنفيذ الأمر {order_id} بعد {max_attempts} محاولات"
            )
            return None

        except Exception as e:
            self.logger.error(f"⚠️ خطأ في سحب بيانات الأمر {order_id}: {e}")
            return None

    def _calculate_average_price(self, order: Dict[str, Any]) -> float:
        """حساب السعر المتوسط الحقيقي"""
        try:
            if order.get("fills"):
                total_qty = sum(float(fill["qty"]) for fill in order["fills"])
                if total_qty > 0:
                    weighted_price = sum(
                        float(fill["price"]) * float(fill["qty"])
                        for fill in order["fills"]
                    )
                    return weighted_price / total_qty
            return float(order.get("price", 0))
        except Exception:
            return 0.0

    def _calculate_total_commission(self, order: Dict[str, Any]) -> float:
        """حساب إجمالي العمولة الحقيقية"""
        try:
            total_commission = 0.0
            if order.get("fills"):
                for fill in order["fills"]:
                    commission = float(fill.get("commission", 0))
                    total_commission += commission
            return total_commission
        except Exception:
            return 0.0

    def _save_real_binance_order(self, user_id: int, order: Dict[str, Any]) -> None:
        """حفظ أمر Binance الحقيقي في قاعدة البيانات"""
        try:
            with self.db_manager.get_write_connection() as conn:
                # حساب البيانات الحقيقية
                avg_price = self._calculate_average_price(order)
                total_commission = self._calculate_total_commission(order)

                conn.execute(
                    """
                    INSERT INTO user_binance_orders
                    (user_id, binance_order_id, symbol, side, type, quantity,
                     price, status, executed_qty, executed_price, commission)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        user_id,
                        order["orderId"],
                        order["symbol"],
                        order["side"],
                        order["type"],
                        float(order["origQty"]),
                        float(order.get("price", 0)),
                        order["status"],
                        float(order["executedQty"]),
                        avg_price,  # السعر المتوسط الحقيقي
                        total_commission,  # العمولة الحقيقية
                    ),
                )

                self.logger.info(
                    f"🗄️ تم حفظ أمر حقيقي {order['symbol']} - {order['side']} برقم {
                        order['orderId']
                    }"
                )
                self.logger.info(
                    f"💰 السعر المتوسط: {avg_price:.8f} | العمولة: {
                        total_commission:.8f}"
                )

        except Exception as e:
            self.logger.error(f"❌ خطأ في حفظ الأمر الحقيقي: {e}")

    def _save_binance_order(
        self, user_id: int, order: Dict[str, Any], is_demo: bool = False
    ) -> None:
        """حفظ أمر Binance في قاعدة البيانات (للوهمي فقط)"""
        try:
            with self.db_manager.get_write_connection() as conn:
                # حساب السعر المتوسط
                avg_price = 0.0
                if order.get("fills"):
                    total_qty = sum(float(fill["qty"]) for fill in order["fills"])
                    if total_qty > 0:
                        weighted_price = sum(
                            float(fill["price"]) * float(fill["qty"])
                            for fill in order["fills"]
                        )
                        avg_price = weighted_price / total_qty
                else:
                    avg_price = float(order.get("price", 0))

                conn.execute(
                    """
                    INSERT INTO user_binance_orders
                    (user_id, binance_order_id, symbol, side, type, quantity,
                     price, status, executed_qty, executed_price, commission)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        user_id,
                        order["orderId"],
                        order["symbol"],
                        order["side"],
                        order["type"],
                        float(order["origQty"]),
                        float(order.get("price", 0)),
                        order["status"],
                        float(order["executedQty"]),
                        avg_price,
                        0.0,  # عمولة وهمية للحساب الوهمي
                    ),
                )

                # تسجيل نوع الأمر (حقيقي أو وهمي)
                order_type = "وهمي" if is_demo else "حقيقي"
                self.logger.info(
                    f"تم حفظ أمر {order_type} {order['symbol']} - {order['side']} برقم {
                        order['orderId']
                    }"
                )

        except Exception as e:
            self.logger.error(f"خطأ في حفظ الأمر: {e}")

    def get_user_real_balance(self, user_id: int) -> Dict[str, Any]:
        """جلب الرصيد الحقيقي للمستخدم"""
        try:
            with self.db_manager.get_connection() as conn:
                balances = conn.execute(
                    """
                    SELECT asset, free_balance, locked_balance, total_balance, updated_at
                    FROM user_binance_balance
                    WHERE user_id = %s
                    ORDER BY total_balance DESC
                """,
                    (user_id,),
                ).fetchall()

                balance_list = []
                total_usdt = 0.0
                free_usdt = 0.0
                locked_usdt = 0.0

                cached_summary = self._get_cached_balance_summary(user_id)
                if cached_summary is not None:
                    total_usdt = float(cached_summary.get("total_usdt", 0.0) or 0.0)
                    free_usdt = float(cached_summary.get("free_usdt", 0.0) or 0.0)
                    locked_usdt = float(cached_summary.get("locked_usdt", 0.0) or 0.0)
                    for balance in balances:
                        balance_list.append(
                            {
                                "asset": balance[0],
                                "free": balance[1],
                                "locked": balance[2],
                                "total": balance[3],
                                "last_sync": balance[4],
                            }
                        )
                    return {
                        "success": True,
                        "balances": balance_list,
                        "free_usdt": free_usdt,
                        "locked_usdt": locked_usdt,
                        "total_usdt": total_usdt,
                    }

                client = self._get_binance_client(user_id)

                for balance in balances:
                    balance_data = {
                        "asset": balance[0],
                        "free": balance[1],
                        "locked": balance[2],
                        "total": balance[3],
                        "last_sync": balance[4],
                    }
                    balance_list.append(balance_data)

                    price = Decimal("0")
                    if client:
                        price = self._get_asset_usdt_price(client, balance[0])
                    if price <= 0:
                        continue

                    free_usdt += float(Decimal(str(balance[1] or 0)) * price)
                    locked_usdt += float(Decimal(str(balance[2] or 0)) * price)
                    total_usdt += float(Decimal(str(balance[3] or 0)) * price)

                self._balance_cache[user_id] = {
                    "cached_at": datetime.now(),
                    "total_usdt": total_usdt,
                    "free_usdt": free_usdt,
                    "locked_usdt": locked_usdt,
                }

                return {
                    "success": True,
                    "balances": balance_list,
                    "free_usdt": free_usdt,
                    "locked_usdt": locked_usdt,
                    "total_usdt": total_usdt,
                }

        except Exception as e:
            self.logger.error(f"خطأ في جلب الرصيد: {e}")
            return {"success": False, "message": str(e)}

    def _execute_demo_buy_order(
        self, user_id: int, symbol: str, quantity: float, price: float
    ) -> Dict[str, Any]:
        """تنفيذ أمر شراء وهمي"""
        try:
            from datetime import datetime
            import uuid

            if price is None or float(price) <= 0:
                return {
                    "success": False,
                    "message": f"لا يمكن تنفيذ أمر وهمي بدون سعر سوقي صحيح لـ {symbol}",
                }

            # إنشاء رقم أمر وهمي
            demo_order_id = (
                f"DEMO_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            )

            # محاكاة استجابة Binance
            demo_order = {
                "symbol": symbol,
                "orderId": demo_order_id,
                "orderListId": -1,
                "clientOrderId": f"demo_{uuid.uuid4().hex[:16]}",
                "transactTime": int(datetime.now().timestamp() * 1000),
                "price": str(price) if price else "0.00000000",
                "origQty": str(quantity),
                "executedQty": str(quantity),
                "cummulativeQuoteQty": (
                    str(quantity * price) if price else "0.00000000"
                ),
                "status": "FILLED",
                "timeInForce": "GTC",
                "type": "MARKET",
                "side": "BUY",
                "fills": [
                    {
                        "price": str(price) if price else "0.00000000",
                        "qty": str(quantity),
                        "commission": "0.00000000",
                        "commissionAsset": "BNB",
                    }
                ],
            }

            # حفظ الأمر الوهمي في قاعدة البيانات
            self._save_binance_order(user_id, demo_order, is_demo=True)

            self.logger.info(
                f"تم تنفيذ أمر شراء وهمي {symbol}: {quantity} بسعر {price}"
            )

            return {
                "success": True,
                "order": demo_order,
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "total_amount": quantity * price if price else 0,
                "order_type": "virtual",
                "message": "تم تنفيذ أمر شراء وهمي بنجاح",
            }

        except Exception as e:
            self.logger.error(f"خطأ في تنفيذ أمر شراء وهمي: {e}")
            return {"success": False, "message": str(e)}

    def _execute_demo_sell_order(
        self, user_id: int, symbol: str, quantity: float
    ) -> Dict[str, Any]:
        """تنفيذ أمر بيع وهمي"""
        try:
            from datetime import datetime
            import uuid

            # جلب السعر الحالي
            current_price = self._get_current_price(symbol)
            if not current_price:
                return {
                    "success": False,
                    "message": f"لا يمكن جلب سعر {symbol}",
                }

            # إنشاء رقم أمر وهمي
            demo_order_id = (
                f"DEMO_SELL_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
            )

            # محاكاة استجابة Binance للبيع
            demo_order = {
                "symbol": symbol,
                "orderId": demo_order_id,
                "orderListId": -1,
                "clientOrderId": f"demo_sell_{uuid.uuid4().hex[:16]}",
                "transactTime": int(datetime.now().timestamp() * 1000),
                "price": str(current_price),
                "origQty": str(quantity),
                "executedQty": str(quantity),
                "cummulativeQuoteQty": str(quantity * current_price),
                "status": "FILLED",
                "timeInForce": "GTC",
                "type": "MARKET",
                "side": "SELL",
                "fills": [
                    {
                        "price": str(current_price),
                        "qty": str(quantity),
                        "commission": "0.00000000",
                        "commissionAsset": "USDT",
                        "tradeId": int(datetime.now().timestamp()),
                    }
                ],
            }

            # حفظ أمر البيع الوهمي
            self._save_binance_order(user_id, demo_order, is_demo=True)

            self.logger.info(
                f"تم تنفيذ أمر بيع وهمي {symbol}: {quantity} بسعر {current_price}"
            )

            return {
                "success": True,
                "order_id": demo_order_id,
                "symbol": symbol,
                "quantity": quantity,
                "price": current_price,
                "total_amount": quantity * current_price,
                "order_type": "virtual",
                "message": "تم تنفيذ أمر بيع وهمي بنجاح",
            }

        except Exception as e:
            self.logger.error(f"خطأ في تنفيذ أمر بيع وهمي: {e}")
            return {"success": False, "message": str(e)}

    def _get_current_price(self, symbol: str) -> Optional[float]:
        """جلب السعر الحالي للرمز من Binance"""
        try:
            from binance.client import Client

            client = Client()
            ticker = client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            self.logger.error(f"خطأ في جلب سعر {symbol}: {e}")
            return None

    def _get_user_balance(self, user_id: int) -> float:
        """جلب رصيد USDT للمستخدم من المحفظة"""
        try:
            with self.db_manager.get_connection() as conn:
                row = conn.execute(
                    """
                    SELECT total_balance
                    FROM portfolio
                    WHERE user_id = %s AND is_demo = FALSE
                    ORDER BY updated_at DESC
                    LIMIT 1
                """,
                    (user_id,),
                ).fetchone()
                return float(row[0]) if row and row[0] else 0.0
        except Exception as e:
            self.logger.error(f"خطأ في جلب الرصيد للمستخدم {user_id}: {e}")
            return 0.0

    def check_order_idempotency(
        self, user_id: int, symbol: str, side: str, quantity: float
    ) -> Optional[Dict]:
        """
        فحص ما إذا كان الأمر موجوداً مسبقاً (لمنع التكرار).
        Returns existing order if found, None otherwise.
        """
        try:
            with self.db_manager.get_connection() as conn:
                row = conn.execute(
                    """
                    SELECT order_id, status, created_at
                    FROM user_binance_orders
                    WHERE user_id = %s AND symbol = %s AND side = %s
                    AND orig_qty = %s AND status IN ('NEW', 'PARTIALLY_FILLED', 'FILLED')
                    ORDER BY created_at DESC
                    LIMIT 1
                """,
                    (user_id, symbol, side.upper(), str(quantity)),
                ).fetchone()

                if row:
                    return {
                        "order_id": row[0],
                        "status": row[1],
                        "created_at": row[2],
                    }
                return None
        except Exception:
            return None

    def is_user_api_active(self, user_id: int) -> bool:
        """التحقق من تفعيل API للمستخدم"""
        api_data = self.get_user_api_keys(user_id)
        return api_data and api_data["is_active"]


# إنشاء مثيل مشترك
binance_manager = BinanceManager()
