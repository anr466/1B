#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lightweight Binance API client using requests.
Bypasses python-binance library which hardcodes api.binance.com.
Uses only official public endpoints — no API keys needed.
"""

import time
import logging
import requests
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# Working endpoints (tested from Docker containers)
# api.binance.com, api2.binance.com, api4.binance.com are geo-blocked from some IPs
# www.binance.com works from all tested locations
WORKING_ENDPOINTS = [
    "https://www.binance.com",  # Primary — works from most locations
    "https://api1.binance.com",  # Alternate — works from some
    "https://api3.binance.com",  # Alternate — works from some
    "https://api.binance.com",  # Last resort — may be geo-blocked
]


class BinancePublicClient:
    """
    Lightweight Binance public API client.
    Uses requests directly to bypass python-binance's hardcoded URL.
    """

    def __init__(self, base_url: str = None):
        self._base_url = base_url or WORKING_ENDPOINTS[0]
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "TradingAI/1.0",
                "Accept": "application/json",
            }
        )
        self._endpoint_index = 0
        self._last_health_check = 0

    @property
    def base_url(self):
        return self._base_url

    def ping(self) -> Dict:
        """Test connectivity."""
        return self._get("/api/v3/ping")

    def get_server_time(self) -> Dict:
        """Get server time."""
        return self._get("/api/v3/time")

    def get_symbol_ticker(self, symbol: str = None) -> Any:
        """Get current price for a symbol or all symbols."""
        if symbol:
            return self._get(f"/api/v3/ticker/price", {"symbol": symbol})
        return self._get("/api/v3/ticker/price")

    def get_ticker(self) -> List[Dict]:
        """Get 24hr ticker price change statistics for all symbols."""
        return self._get("/api/v3/ticker/24hr")

    def get_klines(
        self, symbol: str, interval: str = "1h", limit: int = 500
    ) -> List[List]:
        """Get kline/candlestick data."""
        return self._get(
            "/api/v3/klines",
            {
                "symbol": symbol,
                "interval": interval,
                "limit": min(limit, 1000),
            },
        )

    def get_exchange_info(self, symbol: str = None) -> Dict:
        """Get exchange trading rules and symbol information."""
        params = {"symbol": symbol} if symbol else {}
        return self._get("/api/v3/exchangeInfo", params)

    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get trading rules for a specific symbol."""
        info = self.get_exchange_info(symbol)
        symbols = info.get("symbols", [])
        return symbols[0] if symbols else None

    def _get(self, path: str, params: Dict = None) -> Any:
        """
        Make a GET request with automatic endpoint failover.
        """
        for attempt in range(len(WORKING_ENDPOINTS)):
            url = f"{self._base_url}{path}"
            try:
                resp = self._session.get(url, params=params, timeout=15)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 451:
                    logger.warning(f"⚠️ Geo-blocked on {self._base_url}{path}")
                    self._try_next_endpoint()
                else:
                    raise requests.exceptions.HTTPError(
                        f"HTTP {resp.status_code}: {resp.text[:200]}"
                    )
            except requests.exceptions.ConnectionError as e:
                logger.debug(f"Connection error on {self._base_url}: {e}")
                self._try_next_endpoint()
            except requests.exceptions.Timeout:
                logger.debug(f"Timeout on {self._base_url}")
                self._try_next_endpoint()

        raise ConnectionError(
            f"All Binance endpoints failed. Last tried: {self._base_url}"
        )

    def _try_next_endpoint(self):
        """Switch to the next endpoint."""
        self._endpoint_index = (self._endpoint_index + 1) % len(WORKING_ENDPOINTS)
        self._base_url = WORKING_ENDPOINTS[self._endpoint_index]
        logger.info(f"🔄 Switched Binance endpoint to: {self._base_url}")

    def health_check(self) -> bool:
        """Check if current endpoint is healthy."""
        try:
            self.ping()
            return True
        except Exception:
            self._try_next_endpoint()
            try:
                self.ping()
                return True
            except Exception:
                return False
