#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System-level Binance client for market data and fallback connections.
Uses lightweight requests-based client to bypass python-binance geo-block.
Provides multiple connection methods with automatic failover.
"""

import os
import time
import logging
import threading

logger = logging.getLogger(__name__)


class SystemBinanceClient:
    """
    نظام اتصال متعدد الطبقات بـ Binance باستخدام مفاتيح النظام.
    لا يُستخدم لمحافظ المستخدمين — فقط لبيانات السوق والاتصال الاحتياطي.

    يستخدم BinancePublicClient (requests-based) لتجاوز الحظر الجغرافي
    الذي يسببه مكتبة python-binance.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._client = None
        self._last_health_check = 0
        self._health_check_interval = 30
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
        """تهيئة عميل Binance العام باستخدام requests"""
        if self._initialized:
            return

        try:
            from backend.utils.binance_public_client import BinancePublicClient

            self._client = BinancePublicClient()
            self._client.ping()  # Test connection
            self._initialized = True
            logger.info(
                f"✅ System Binance client initialized with endpoint: {self._client.base_url}"
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize System Binance client: {e}")

    def get_client(self):
        """
        الحصول على عميل Binance نشط مع failover تلقائي.
        """
        if not self._initialized:
            self._initialize()

        if self._client is None:
            return None

        # فحص الصحة كل 30 ثانية
        now = time.time()
        if now - self._last_health_check > self._health_check_interval:
            if not self._client.health_check():
                logger.warning("⚠️ System Binance client health check failed")
            self._last_health_check = now

        return self._client

    def get_status(self) -> dict:
        """حالة العميل"""
        if self._client is None:
            return {"status": "uninitialized"}
        try:
            self._client.ping()
            return {"status": "healthy", "endpoint": self._client.base_url}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Singleton global
system_binance = SystemBinanceClient.get_instance()
