#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unified Trading Engine — طبقة واحدة تربط كل شيء
================================================
Architecture:
  Market Regime Detector → Strategy Router → Mode Router → Execution → Storage

Each layer has a clear responsibility:
  1. Regime Detector: What is the market doing? (BULL/BEAR/NEUTRAL/VOLATILE)
  2. Strategy Router: Which strategies work in this regime?
  3. Mode Router: Where should this signal go? (LONG→Spot, SHORT→Margin)
  4. Execution: Open/manage/close positions
  5. Storage: Log everything to DB
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from backend.infrastructure.db_access import get_db_manager
from backend.utils.data_provider import DataProvider
from backend.analysis.market_regime_detector import MarketRegimeDetector
from backend.strategies.scalping_v8_engine import ScalpingV8Engine, V8_CONFIG

logger = logging.getLogger(__name__)


class UnifiedTradingEngine:
    """محرك تداول موحد — يتعامل مع جميع أوضاع السوق"""

    def __init__(self, user_id: int, is_demo: bool = True):
        self.user_id = user_id
        self.is_demo = is_demo
        self.db = get_db_manager()
        self.data_provider = DataProvider()
        self.regime_detector = MarketRegimeDetector()
        self.v8_engine = ScalpingV8Engine(V8_CONFIG)

        settings = self._load_user_settings()
        self.spot_enabled = settings.get("spot_enabled", True)
        self.margin_enabled = settings.get("margin_enabled", False)

        self.open_positions: List[Dict] = []

        logger.info(
            f"UnifiedTradingEngine: user={user_id}, spot={self.spot_enabled}, "
            f"margin={self.margin_enabled}"
        )

    def _load_user_settings(self) -> Dict:
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT trading_enabled FROM user_settings WHERE user_id = %s AND is_demo = %s",
                    (self.user_id, self.is_demo),
                )
                row = cursor.fetchone()
                return {
                    "spot_enabled": bool(row[0]) if row else True,
                    "margin_enabled": False,
                }
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
        return {"spot_enabled": True, "margin_enabled": False}

    def scan_cycle(self, symbols: List[str]) -> Dict:
        results = {"regime": None, "signals": [], "actions": [], "errors": []}

        for symbol in symbols:
            try:
                df_1h = self.data_provider.get_ohlcv(symbol, "1h", limit=200)
                if df_1h is None or len(df_1h) < 100:
                    continue

                df_4h = self.data_provider.get_ohlcv(symbol, "4h", limit=100)

                regime_info = self.regime_detector.detect_regime(df_1h, df_4h)
                if results["regime"] is None:
                    results["regime"] = regime_info

                allowed_strategies = self.regime_detector.get_allowed_strategies(
                    regime_info["regime"], self.spot_enabled, self.margin_enabled
                )
                if not allowed_strategies:
                    continue

                df_1h = self.v8_engine.prepare_data(df_1h)
                trend = self.v8_engine.get_4h_trend(df_1h)
                signal = self.v8_engine.detect_entry(df_1h, trend)

                if signal and signal.get("strategy") in allowed_strategies:
                    side = signal.get("side", "LONG").upper()
                    mode = "spot" if side == "LONG" else "margin"

                    if mode == "margin" and not self.margin_enabled:
                        continue
                    if mode == "spot" and not self.spot_enabled:
                        continue

                    results["signals"].append(signal)
                    action = self._execute_signal(symbol, signal, df_1h, regime_info)
                    if action:
                        results["actions"].append(action)

            except Exception as e:
                results["errors"].append({"symbol": symbol, "error": str(e)})
                logger.error(f"Error scanning {symbol}: {e}")

        return results

    def _execute_signal(
        self, symbol: str, signal: Dict, df, regime_info: Dict
    ) -> Optional[Dict]:
        if any(p["symbol"] == symbol for p in self.open_positions):
            return None

        side = signal.get("side", "LONG").upper()
        mode = "spot" if side == "LONG" else "margin"
        current_price = df["close"].iloc[-1]
        entry_price = signal.get("entry_price", current_price)

        sl_mult = self.regime_detector.get_stop_loss_multiplier(regime_info["regime"])
        base_sl = V8_CONFIG.get("sl_pct", 0.010) * sl_mult

        if side == "LONG":
            sl = entry_price * (1 - base_sl)
        else:
            sl = entry_price * (1 + base_sl)

        size_mult = self.regime_detector.get_position_size_multiplier(
            regime_info["regime"]
        )
        size = (
            self._get_balance(mode)
            * V8_CONFIG.get("position_size_pct", 0.06)
            * size_mult
        )

        position = {
            "symbol": symbol,
            "side": side,
            "mode": mode,
            "entry_price": entry_price,
            "sl": sl,
            "peak": entry_price,
            "trail": 0,
            "size": size,
            "entry_time": datetime.utcnow(),
            "strategy": signal.get("strategy", "unknown"),
            "regime": regime_info["regime"],
        }

        self.open_positions.append(position)
        self._log_open(position)

        return {
            "action": "OPEN",
            "symbol": symbol,
            "side": side,
            "mode": mode,
            "price": entry_price,
            "size": size,
        }

    def manage_positions(self, symbols: List[str]) -> Dict:
        exits = []
        to_remove = []

        for pos in self.open_positions:
            if pos["symbol"] not in symbols:
                continue

            df = self.data_provider.get_ohlcv(pos["symbol"], "1h", limit=200)
            if df is None or len(df) < 3:
                continue

            current_price = df["close"].iloc[-1]
            hold_hours = (datetime.utcnow() - pos["entry_time"]).total_seconds() / 3600

            if pos["side"] == "LONG":
                pnl_pct = (current_price - pos["entry_price"]) / pos["entry_price"]
            else:
                pnl_pct = (pos["entry_price"] - current_price) / pos["entry_price"]

            trail_dist = V8_CONFIG.get("trailing_distance", 0.010)
            progressive = V8_CONFIG.get("v8_progressive_trail", {})
            if pos["side"] == "LONG" and current_price > pos.get(
                "peak", pos["entry_price"]
            ):
                pos["peak"] = current_price
                for profit_level, dist in sorted(progressive.items()):
                    if pnl_pct >= profit_level:
                        trail_dist = dist
                pos["trail"] = pos["peak"] * (1 - trail_dist)
            elif pos["side"] == "SHORT" and current_price < pos.get(
                "peak", pos["entry_price"]
            ):
                pos["peak"] = current_price
                for profit_level, dist in sorted(progressive.items()):
                    if pnl_pct >= profit_level:
                        trail_dist = dist
                pos["trail"] = pos["peak"] * (1 + trail_dist)

            trail_act = V8_CONFIG.get("trailing_activation", 0.015)
            max_hold = V8_CONFIG.get("max_hold_hours", 8)
            stagnant_h = V8_CONFIG.get("stagnant_hours", 8)
            stagnant_thresh = V8_CONFIG.get("stagnant_threshold", 0.005)

            should_exit = False
            exit_reason = ""

            if pos["side"] == "LONG":
                if current_price <= pos["sl"]:
                    should_exit, exit_reason = True, "STOP_LOSS"
                elif (
                    pos.get("trail", 0) > 0
                    and current_price <= pos["trail"]
                    and pnl_pct >= trail_act
                ):
                    should_exit, exit_reason = True, "TRAILING"
            else:
                if current_price >= pos["sl"]:
                    should_exit, exit_reason = True, "STOP_LOSS"
                elif (
                    pos.get("trail", 0) > 0
                    and current_price >= pos["trail"]
                    and pnl_pct >= trail_act
                ):
                    should_exit, exit_reason = True, "TRAILING"

            if hold_hours >= max_hold:
                should_exit, exit_reason = True, "MAX_HOLD"
            elif hold_hours >= stagnant_h and abs(pnl_pct) < stagnant_thresh:
                should_exit, exit_reason = True, "STAGNANT"

            if should_exit:
                net_pnl = pnl_pct - 0.001 - 0.0005
                pnl_amount = pos["size"] * net_pnl
                exits.append(
                    {
                        "symbol": pos["symbol"],
                        "side": pos["side"],
                        "mode": pos["mode"],
                        "entry_price": pos["entry_price"],
                        "exit_price": current_price,
                        "pnl_pct": net_pnl * 100,
                        "pnl": pnl_amount,
                        "exit_reason": exit_reason,
                        "strategy": pos.get("strategy", "unknown"),
                        "regime": pos.get("regime", "unknown"),
                    }
                )
                self._log_close(pos, current_price, exit_reason, net_pnl)
                to_remove.append(pos)

        for pos in to_remove:
            self.open_positions.remove(pos)

        return {"exits": exits}

    def _get_balance(self, mode: str) -> float:
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT available_balance FROM portfolio WHERE user_id = %s AND is_demo = %s",
                    (self.user_id, self.is_demo),
                )
                row = cursor.fetchone()
                return float(row[0]) if row else 1000.0
        except Exception:
            return 1000.0

    def _log_open(self, position: Dict):
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO active_positions
                    (user_id, is_demo, symbol, position_type, entry_price, stop_loss, quantity, strategy, entry_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        self.user_id,
                        self.is_demo,
                        position["symbol"],
                        position["side"],
                        position["entry_price"],
                        position["sl"],
                        position["size"],
                        position.get("strategy", "unknown"),
                        position["entry_time"],
                    ),
                )
        except Exception as e:
            logger.error(f"Error logging open: {e}")

    def _log_close(
        self, position: Dict, exit_price: float, exit_reason: str, net_pnl: float
    ):
        try:
            pnl_amount = position["size"] * net_pnl
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE active_positions SET is_active = FALSE, exit_price = %s,
                    profit_loss = %s, profit_pct = %s, exit_reason = %s, closed_at = %s
                    WHERE user_id = %s AND is_demo = %s AND symbol = %s AND is_active = TRUE""",
                    (
                        exit_price,
                        pnl_amount,
                        net_pnl * 100,
                        exit_reason,
                        datetime.utcnow(),
                        self.user_id,
                        self.is_demo,
                        position["symbol"],
                    ),
                )
        except Exception as e:
            logger.error(f"Error logging close: {e}")

    def get_status(self) -> Dict:
        return {
            "user_id": self.user_id,
            "spot_enabled": self.spot_enabled,
            "margin_enabled": self.margin_enabled,
            "open_positions": len(self.open_positions),
            "positions": [
                {
                    "symbol": p["symbol"],
                    "side": p["side"],
                    "mode": p["mode"],
                    "entry": p["entry_price"],
                    "regime": p.get("regime", "unknown"),
                }
                for p in self.open_positions
            ],
        }
