#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dual-Mode Trading Engine — Spot + Margin simultaneously
========================================================
يدير التداول في الوضعين معاً:
  - Spot: LONG فقط (breakout + trend_cont)
  - Margin: LONG + SHORT (جميع الاستراتيجيات الأربع)

كل وضع له:
  - محفظة منفصلة
  - صفقات منفصلة
  - إشارات منفصلة
  - سجل تعلم منفصل
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

from backend.infrastructure.db_access import get_db_manager
from backend.utils.data_provider import DataProvider
from backend.strategies.scalping_v8_engine import ScalpingV8Engine, V8_CONFIG

logger = logging.getLogger(__name__)


class DualModeEngine:
    """محرك تداول مزدوج — Spot + Margin"""

    def __init__(self, user_id: int, is_demo: bool = True):
        self.user_id = user_id
        self.is_demo = is_demo
        self.db = get_db_manager()
        self.data_provider = DataProvider()

        # Load user settings
        settings = self._load_user_settings()
        self.spot_enabled = settings.get("spot_enabled", True)
        self.margin_enabled = settings.get("margin_enabled", False)

        # V8 engine (shared — detects all signals)
        self.v8_engine = ScalpingV8Engine(V8_CONFIG)

        # Position tracking per mode
        self.spot_positions: List[Dict] = []
        self.margin_positions: List[Dict] = []

        logger.info(
            f"DualModeEngine: user={user_id}, spot={self.spot_enabled}, "
            f"margin={self.margin_enabled}"
        )

    def _load_user_settings(self) -> Dict:
        try:
            with self.db.get_read_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT trading_enabled, trading_mode
                    FROM user_settings
                    WHERE user_id = %s AND is_demo = %s
                    """,
                    (self.user_id, self.is_demo),
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "spot_enabled": row[0],
                        "margin_enabled": False,  # Default off until configured
                    }
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
        return {"spot_enabled": True, "margin_enabled": False}

    def scan_and_trade(self, symbols: List[str]) -> Dict:
        """
        فحص جميع العملات وتوليد إشارات لكلا الوضعين

        Returns:
            Dict with spot_signals, margin_signals, actions_taken
        """
        results = {
            "spot_signals": [],
            "margin_signals": [],
            "spot_actions": [],
            "margin_actions": [],
            "errors": [],
        }

        for symbol in symbols:
            try:
                df = self.data_provider.get_ohlcv(symbol, "1h", limit=200)
                if df is None or len(df) < 100:
                    continue

                # Prepare indicators
                df = self.v8_engine.prepare_data(df)

                # Get trend
                trend = self.v8_engine.get_4h_trend(df)

                # Detect entry (returns signal with side: LONG or SHORT)
                signal = self.v8_engine.detect_entry(df, trend)
                if not signal:
                    continue

                side = signal.get("side", "").upper()

                # Route signal to appropriate mode
                if side == "LONG":
                    # LONG → Spot (always) + Margin (if enabled)
                    if self.spot_enabled:
                        results["spot_signals"].append(signal)
                        action = self._execute_spot_signal(symbol, signal, df)
                        if action:
                            results["spot_actions"].append(action)

                    if self.margin_enabled:
                        results["margin_signals"].append(signal)
                        action = self._execute_margin_signal(symbol, signal, df)
                        if action:
                            results["margin_actions"].append(action)

                elif side == "SHORT":
                    # SHORT → Margin only (if enabled)
                    if self.margin_enabled:
                        results["margin_signals"].append(signal)
                        action = self._execute_margin_signal(symbol, signal, df)
                        if action:
                            results["margin_actions"].append(action)
                    else:
                        logger.debug(
                            f"SHORT signal for {symbol} ignored — margin disabled"
                        )

            except Exception as e:
                results["errors"].append({"symbol": symbol, "error": str(e)})
                logger.error(f"Error scanning {symbol}: {e}")

        return results

    def _execute_spot_signal(self, symbol: str, signal: Dict, df) -> Optional[Dict]:
        """تنفيذ إشارة Spot (LONG فقط)"""
        # Check max positions
        if len(self.spot_positions) >= V8_CONFIG.get("max_positions", 5):
            return None

        # Check if already have position in this symbol
        if any(p["symbol"] == symbol for p in self.spot_positions):
            return None

        current_price = df["close"].iloc[-1]
        entry_price = signal.get("entry_price", current_price)
        sl = entry_price * (1 - V8_CONFIG.get("sl_pct", 0.010))
        size = self._get_spot_balance() * V8_CONFIG.get("position_size_pct", 0.06)

        position = {
            "symbol": symbol,
            "side": "LONG",
            "mode": "spot",
            "entry_price": entry_price,
            "sl": sl,
            "peak": entry_price,
            "trail": 0,
            "size": size,
            "entry_time": datetime.utcnow(),
            "strategy": signal.get("strategy", "unknown"),
            "confidence": signal.get("confidence", 50),
        }

        self.spot_positions.append(position)
        self._log_position_opened(position)

        return {
            "action": "OPEN",
            "symbol": symbol,
            "side": "LONG",
            "mode": "spot",
            "price": entry_price,
            "size": size,
        }

    def _execute_margin_signal(self, symbol: str, signal: Dict, df) -> Optional[Dict]:
        """تنفيذ إشارة Margin (LONG أو SHORT)"""
        # Check max positions
        if len(self.margin_positions) >= V8_CONFIG.get("max_positions", 5):
            return None

        # Check if already have position in this symbol
        if any(p["symbol"] == symbol for p in self.margin_positions):
            return None

        current_price = df["close"].iloc[-1]
        entry_price = signal.get("entry_price", current_price)
        side = signal.get("side", "LONG").upper()

        if side == "LONG":
            sl = entry_price * (1 - V8_CONFIG.get("sl_pct", 0.010))
        else:  # SHORT
            sl = entry_price * (1 + V8_CONFIG.get("sl_pct", 0.010))

        size = self._get_margin_balance() * V8_CONFIG.get("position_size_pct", 0.06)

        position = {
            "symbol": symbol,
            "side": side,
            "mode": "margin",
            "entry_price": entry_price,
            "sl": sl,
            "peak": entry_price,
            "trail": 0,
            "size": size,
            "entry_time": datetime.utcnow(),
            "strategy": signal.get("strategy", "unknown"),
            "confidence": signal.get("confidence", 50),
        }

        self.margin_positions.append(position)
        self._log_position_opened(position)

        return {
            "action": "OPEN",
            "symbol": symbol,
            "side": side,
            "mode": "margin",
            "price": entry_price,
            "size": size,
        }

    def manage_positions(self, symbols: List[str]) -> Dict:
        """إدارة الصفقات المفتوحة في كلا الوضعين"""
        results = {"spot_exits": [], "margin_exits": [], "errors": []}

        # Manage Spot positions
        results["spot_exits"] = self._manage_mode_positions(
            self.spot_positions, "spot", symbols
        )

        # Manage Margin positions
        results["margin_exits"] = self._manage_mode_positions(
            self.margin_positions, "margin", symbols
        )

        return results

    def _manage_mode_positions(
        self, positions: List[Dict], mode: str, symbols: List[str]
    ) -> List[Dict]:
        exits = []
        positions_to_remove = []

        for pos in positions:
            try:
                symbol = pos["symbol"]
                if symbol not in symbols:
                    continue

                df = self.data_provider.get_ohlcv(symbol, "1h", limit=200)
                if df is None or len(df) < 3:
                    continue

                current_price = df["close"].iloc[-1]
                hold_hours = (
                    datetime.utcnow() - pos["entry_time"]
                ).total_seconds() / 3600

                if pos["side"] == "LONG":
                    pnl_pct = (current_price - pos["entry_price"]) / pos["entry_price"]
                else:
                    pnl_pct = (pos["entry_price"] - current_price) / pos["entry_price"]

                if pos["side"] == "LONG" and current_price > pos.get(
                    "peak", pos["entry_price"]
                ):
                    pos["peak"] = current_price
                    td = V8_CONFIG.get("trailing_distance", 0.0015)
                    for profit_level, dist in sorted(
                        V8_CONFIG.get("v8_progressive_trail", {}).items()
                    ):
                        if pnl_pct >= profit_level:
                            td = dist
                    pos["trail"] = pos["peak"] * (1 - td)
                elif pos["side"] == "SHORT" and current_price < pos.get(
                    "peak", pos["entry_price"]
                ):
                    pos["peak"] = current_price
                    td = V8_CONFIG.get("trailing_distance", 0.0015)
                    for profit_level, dist in sorted(
                        V8_CONFIG.get("v8_progressive_trail", {}).items()
                    ):
                        if pnl_pct >= profit_level:
                            td = dist
                    pos["trail"] = pos["peak"] * (1 + td)

                # Check exit conditions
                should_exit = False
                exit_reason = ""

                if pos["side"] == "LONG":
                    if current_price <= pos["sl"]:
                        should_exit, exit_reason = True, "STOP_LOSS"
                    elif (
                        pos.get("trail", 0) > 0
                        and current_price <= pos["trail"]
                        and pnl_pct >= V8_CONFIG.get("trailing_activation", 0.002)
                    ):
                        should_exit, exit_reason = True, "TRAILING"
                else:  # SHORT
                    if current_price >= pos["sl"]:
                        should_exit, exit_reason = True, "STOP_LOSS"
                    elif (
                        pos.get("trail", 0) > 0
                        and current_price >= pos["trail"]
                        and pnl_pct >= V8_CONFIG.get("trailing_activation", 0.002)
                    ):
                        should_exit, exit_reason = True, "TRAILING"

                if hold_hours >= V8_CONFIG.get("max_hold_hours", 6):
                    should_exit, exit_reason = True, "MAX_HOLD"

                if should_exit:
                    net_pnl = pnl_pct - 0.001 - 0.0005  # commission + slippage
                    pnl_amount = pos["size"] * net_pnl

                    exits.append(
                        {
                            "symbol": symbol,
                            "side": pos["side"],
                            "mode": mode,
                            "entry_price": pos["entry_price"],
                            "exit_price": current_price,
                            "pnl_pct": net_pnl * 100,
                            "pnl": pnl_amount,
                            "exit_reason": exit_reason,
                            "strategy": pos.get("strategy", "unknown"),
                        }
                    )

                    self._log_position_closed(pos, current_price, exit_reason, net_pnl)
                    positions_to_remove.append(pos)

            except Exception as e:
                logger.error(f"Error managing {pos.get('symbol')}: {e}")

        for pos in positions_to_remove:
            positions.remove(pos)

        return exits

    def _get_spot_balance(self) -> float:
        try:
            with self.db.get_read_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT available_balance FROM portfolio
                    WHERE user_id = %s AND is_demo = %s AND mode = 'spot'
                    """,
                    (self.user_id, self.is_demo),
                )
                row = cursor.fetchone()
                return float(row[0]) if row else 1000.0
        except Exception:
            return 1000.0

    def _get_margin_balance(self) -> float:
        try:
            with self.db.get_read_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT available_balance FROM portfolio
                    WHERE user_id = %s AND is_demo = %s AND mode = 'margin'
                    """,
                    (self.user_id, self.is_demo),
                )
                row = cursor.fetchone()
                return float(row[0]) if row else 1000.0
        except Exception:
            return 1000.0

    def _log_position_opened(self, position: Dict):
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO active_positions
                    (user_id, is_demo, symbol, position_type, mode, entry_price,
                     stop_loss, quantity, strategy, entry_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        self.user_id,
                        self.is_demo,
                        position["symbol"],
                        position["side"],
                        position["mode"],
                        position["entry_price"],
                        position["sl"],
                        position["size"],
                        position.get("strategy", "unknown"),
                        position["entry_time"],
                    ),
                )
        except Exception as e:
            logger.error(f"Error logging position open: {e}")

    def _log_position_closed(
        self, position: Dict, exit_price: float, exit_reason: str, net_pnl: float
    ):
        try:
            pnl_amount = position["size"] * net_pnl
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE active_positions
                    SET is_active = FALSE, exit_price = %s, profit_loss = %s,
                        profit_pct = %s, exit_reason = %s, closed_at = %s
                    WHERE user_id = %s AND is_demo = %s AND symbol = %s
                    AND mode = %s AND is_active = TRUE
                    """,
                    (
                        exit_price,
                        pnl_amount,
                        net_pnl * 100,
                        exit_reason,
                        datetime.utcnow(),
                        self.user_id,
                        self.is_demo,
                        position["symbol"],
                        position["mode"],
                    ),
                )
        except Exception as e:
            logger.error(f"Error logging position close: {e}")

    def get_status(self) -> Dict:
        return {
            "user_id": self.user_id,
            "spot_enabled": self.spot_enabled,
            "margin_enabled": self.margin_enabled,
            "spot_positions": len(self.spot_positions),
            "margin_positions": len(self.margin_positions),
            "spot_pnl": sum(
                (p.get("peak", p["entry_price"]) - p["entry_price"])
                / p["entry_price"]
                * p["size"]
                for p in self.spot_positions
            ),
            "margin_pnl": sum(
                (
                    (p.get("peak", p["entry_price"]) - p["entry_price"])
                    if p["side"] == "LONG"
                    else (p["entry_price"] - p.get("peak", p["entry_price"]))
                )
                / p["entry_price"]
                * p["size"]
                for p in self.margin_positions
            ),
        }
