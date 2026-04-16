#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System-level Binance client for market data and fallback connections.
Uses .env keys (BINANCE_BACKEND_API_KEY/SECRET) — NOT user keys.
Provides multiple connection methods with automatic failover.
"""

import os
import time
import logging
import threading
from typing import Optional
from binance.client import Client

logger = logging.getLogger(__name__)


class SystemBinanceClient:
    """
    نظام اتصال متعدد الطبقات بـ Binance باستخدام مفاتيح النظام.
    لا يُستخدم لمحافظ المستخدمين — فقط لبيانات السوق والاتصال الاحتياطي.

    طبقات الاتصال (بالترتيب):
    1. Primary: مفاتيح BINANCE_BACKEND من .env
    2. Fallback: مفاتيح بديلة (إذا وُجدت في .env)
    3. Public: واجهات Binance العامة (بدون مفاتيح)
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._clients = {}
        self._active_client = None
        self._last_health_check = 0
        self._health_check_interval = 30
        self._failure_count = 0
        self._max_failures_before_switch = 3
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "SystemBinanceClient":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """تهيئة جميع عملاء Binance المتاحين"""
        if self._initialized:
            return

        # الطبقة 1: مفاتيح النظام من .env
        primary_key = os.getenv("BINANCE_BACKEND_API_KEY")
        primary_secret = os.getenv("BINANCE_BACKEND_API_SECRET")

        if primary_key and primary_secret:
            try:
                self._clients["primary"] = {
                    "client": Client(
                        api_key=primary_key,
                        api_secret=primary_secret,
                        testnet=False,
                        requests_params={"timeout": 10},
                    ),
                    "name": "primary",
                    "failures": 0,
                    "last_success": time.time(),
                }
                logger.info("✅ System Binance client (primary) initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to create primary Binance client: {e}")

        # الطبقة 2: مفاتيح بديلة (إذا وُجدت)
        fallback_key = os.getenv("BINANCE_FALLBACK_API_KEY")
        fallback_secret = os.getenv("BINANCE_FALLBACK_API_SECRET")

        if fallback_key and fallback_secret:
            try:
                self._clients["fallback"] = {
                    "client": Client(
                        api_key=fallback_key,
                        api_secret=fallback_secret,
                        testnet=False,
                        requests_params={"timeout": 10},
                    ),
                    "name": "fallback",
                    "failures": 0,
                    "last_success": time.time(),
                }
                logger.info("✅ System Binance client (fallback) initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to create fallback Binance client: {e}")

        # الطبقة 3: عميل عام بدون مفاتيح (للأسعار فقط)
        try:
            self._clients["public"] = {
                "client": Client(requests_params={"timeout": 10}),
                "name": "public",
                "failures": 0,
                "last_success": time.time(),
                "public_only": True,
            }
            logger.info("✅ System Binance client (public) initialized")
        except Exception as e:
            logger.warning(f"⚠️ Failed to create public Binance client: {e}")

        # تحديد العميل النشط
        if self._clients:
            self._active_client = next(iter(self._clients))
            self._initialized = True
            logger.info(
                f"✅ System Binance initialized with {len(self._clients)} client(s): "
                f"active='{self._active_client}'"
            )
        else:
            logger.error("❌ No System Binance clients available")

    def get_client(self) -> Optional[Client]:
        """
        الحصول على عميل Binance نشط مع failover تلقائي.
        يحاول العميل النشط أولاً، ثم ينتقل للتالي عند الفشل.
        """
        if not self._initialized:
            self._initialize()

        if not self._clients:
            return None

        # فحص الصحة كل 30 ثانية
        now = time.time()
        if now - self._last_health_check > self._health_check_interval:
            self._health_check()
            self._last_health_check = now

        if self._active_client and self._active_client in self._clients:
            return self._clients[self._active_client]["client"]

        # Failover: حاول أي عميل متاح
        for name, client_data in self._clients.items():
            try:
                client_data["client"].ping()
                self._active_client = name
                client_data["failures"] = 0
                client_data["last_success"] = time.time()
                return client_data["client"]
            except Exception:
                continue

        return None

    def _health_check(self):
        """فحص صحة جميع العملاء وتبديل العميل النشط عند الحاجة"""
        if not self._active_client or self._active_client not in self._clients:
            # حاول إيجاد عميل نشط
            for name, client_data in self._clients.items():
                try:
                    client_data["client"].ping()
                    self._active_client = name
                    client_data["failures"] = 0
                    logger.info(f"🔄 Switched active client to: {name}")
                    return
                except Exception:
                    continue
            return

        # فحص العميل النشط
        try:
            self._clients[self._active_client]["client"].ping()
            self._clients[self._active_client]["failures"] = 0
            self._clients[self._active_client]["last_success"] = time.time()
        except Exception:
            self._clients[self._active_client]["failures"] += 1
            failures = self._clients[self._active_client]["failures"]

            if failures >= self._max_failures_before_switch:
                logger.warning(
                    f"⚠️ Active client '{self._active_client}' failed {failures} times — switching"
                )
                self._failover()

    def _failover(self):
        """التبديل إلى عميل بديل"""
        current = self._active_client
        for name, client_data in self._clients.items():
            if name == current:
                continue
            try:
                client_data["client"].ping()
                self._active_client = name
                client_data["failures"] = 0
                client_data["last_success"] = time.time()
                logger.info(f"🔄 Failover: switched from '{current}' to '{name}'")
                return
            except Exception:
                continue

        logger.error(f"❌ All System Binance clients failed — no failover available")

    def get_status(self) -> dict:
        """حالة جميع العملاء"""
        status = {}
        for name, data in self._clients.items():
            try:
                data["client"].ping()
                status[name] = {"status": "healthy", "failures": data["failures"]}
            except Exception as e:
                status[name] = {"status": "unhealthy", "error": str(e)}
        status["active"] = self._active_client
        return status


# Singleton global
system_binance = SystemBinanceClient.get_instance()
