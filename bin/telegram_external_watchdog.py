#!/usr/bin/env python3
"""
External Health Watchdog
- Runs as a separate process from the API server
- Polls health endpoint
- Sends Telegram alerts on sustained failures and recovery

This ensures alerting still works even when the main server process is down.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger("external_watchdog")


@dataclass
class WatchdogConfig:
    health_url: str
    bot_token: str
    chat_id: str
    interval_seconds: int
    timeout_seconds: int
    failure_threshold: int
    recovery_threshold: int
    alert_cooldown_seconds: int


class ExternalHealthWatchdog:
    def __init__(self, config: WatchdogConfig):
        self.config = config
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._is_alerting = False
        self._last_alert_ts: Optional[float] = None

    def run_forever(self) -> None:
        logger.info("Starting external watchdog")
        logger.info("Health URL: %s", self.config.health_url)

        self._send_telegram(
            "🛰️ External Watchdog Started",
            f"Started at {datetime.utcnow().isoformat()}Z\n"
            f"Health URL: {self.config.health_url}\n"
            f"Interval: {self.config.interval_seconds}s",
            force=True,
        )

        while True:
            self._check_once()
            time.sleep(self.config.interval_seconds)

    def _check_once(self) -> None:
        ok, status_text, details = self._fetch_health()

        if ok:
            self._consecutive_successes += 1
            self._consecutive_failures = 0

            if self._is_alerting and self._consecutive_successes >= self.config.recovery_threshold:
                self._is_alerting = False
                self._send_telegram(
                    "✅ System Recovered",
                    f"Status: {status_text}\nDetails: {details}",
                    force=True,
                )
            return

        self._consecutive_failures += 1
        self._consecutive_successes = 0

        if self._consecutive_failures < self.config.failure_threshold:
            logger.warning(
                "Health check failed (%s/%s): %s",
                self._consecutive_failures,
                self.config.failure_threshold,
                details,
            )
            return

        self._is_alerting = True
        self._send_telegram(
            "🚨 System Health Alert",
            "External monitor detected sustained failure\n"
            f"Consecutive failures: {self._consecutive_failures}\n"
            f"Status: {status_text}\n"
            f"Details: {details}",
        )

    def _fetch_health(self) -> tuple[bool, str, str]:
        try:
            response = requests.get(self.config.health_url, timeout=self.config.timeout_seconds)
            if response.status_code != 200:
                return False, "http_error", f"HTTP {response.status_code}"

            payload: Dict[str, Any] = response.json() if response.content else {}
            data = payload.get("data") if isinstance(payload, dict) else None
            overall = (data or {}).get("overall_status")

            if overall in {"healthy"}:
                return True, str(overall), "healthy"

            if overall in {"warning", "error"}:
                return False, str(overall), f"overall_status={overall}"

            return False, "unknown", f"unexpected_payload={payload}"

        except requests.RequestException as exc:
            return False, "request_exception", str(exc)
        except ValueError as exc:
            return False, "json_error", str(exc)
        except Exception as exc:  # defensive
            return False, "unexpected_exception", str(exc)

    def _send_telegram(self, title: str, message: str, force: bool = False) -> None:
        now = time.time()
        if not force and self._last_alert_ts is not None:
            if now - self._last_alert_ts < self.config.alert_cooldown_seconds:
                logger.info("Skipping Telegram alert due to cooldown")
                return

        self._last_alert_ts = now

        text = (
            f"*{title}*\n\n"
            f"{message}\n\n"
            f"Time: {datetime.utcnow().isoformat()}Z"
        )

        url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
        payload = {
            "chat_id": self.config.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Telegram alert sent: %s", title)
            else:
                logger.error("Telegram send failed (%s): %s", response.status_code, response.text)
        except Exception as exc:  # defensive
            logger.error("Telegram send exception: %s", exc)


def _load_config_from_env() -> WatchdogConfig:
    token = os.getenv("WATCHDOG_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("WATCHDOG_TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        raise RuntimeError(
            "Missing WATCHDOG_TELEGRAM_BOT_TOKEN / WATCHDOG_TELEGRAM_CHAT_ID environment variables"
        )

    interval_seconds = int(os.getenv("WATCHDOG_INTERVAL_SECONDS", "30"))
    timeout_seconds = int(os.getenv("WATCHDOG_REQUEST_TIMEOUT_SECONDS", "8"))
    failure_threshold = int(os.getenv("WATCHDOG_FAILURE_THRESHOLD", "3"))
    recovery_threshold = int(os.getenv("WATCHDOG_RECOVERY_THRESHOLD", "1"))
    alert_cooldown_seconds = int(os.getenv("WATCHDOG_ALERT_COOLDOWN_SECONDS", "300"))

    return WatchdogConfig(
        health_url=os.getenv("WATCHDOG_HEALTH_URL", "http://127.0.0.1:3002/admin/system/health").strip(),
        bot_token=token,
        chat_id=chat_id,
        interval_seconds=max(5, interval_seconds),
        timeout_seconds=max(2, timeout_seconds),
        failure_threshold=max(1, failure_threshold),
        recovery_threshold=max(1, recovery_threshold),
        alert_cooldown_seconds=max(10, alert_cooldown_seconds),
    )


def main() -> int:
    logging.basicConfig(
        level=os.getenv("WATCHDOG_LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        config = _load_config_from_env()
    except Exception as exc:
        logger.error("Invalid watchdog configuration: %s", exc)
        return 1

    watchdog = ExternalHealthWatchdog(config)
    watchdog.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
