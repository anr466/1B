#!/usr/bin/env python3

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MonitoringEngine:
    def monitor_positions(
        self, positions: List[Dict], current_prices: Dict[str, float]
    ) -> List[Dict]:
        actions = []
        for pos in positions:
            symbol = pos.get("symbol")
            current_price = current_prices.get(symbol)
            if not current_price:
                continue

            action = self._evaluate_position(pos, current_price)
            if action:
                actions.append(action)

        return actions

    def _evaluate_position(self, pos: Dict, current_price: float) -> Optional[Dict]:
        entry = pos.get("entry_price", 0)
        sl = pos.get("stop_loss", 0)
        tp = pos.get("take_profit", 0)
        trail = pos.get("trailing_sl_price", 0)
        peak = pos.get("highest_price", entry)
        position_type = pos.get("position_type", "long").upper()

        if entry <= 0:
            return None

        if position_type == "LONG":
            pnl_pct = (current_price - entry) / entry
        else:
            pnl_pct = (entry - current_price) / entry

        action = self._check_hard_exits(pos, current_price, pnl_pct)
        if action:
            return action

        updates = self._update_trailing(pos, current_price, peak, pnl_pct)
        be_updates = self._check_breakeven(pos, current_price, pnl_pct)
        if be_updates:
            updates = updates or {}
            updates.update(be_updates)
        if updates:
            return {"type": "UPDATE", "symbol": pos["symbol"], "updates": updates}

        action = self._check_time_exits(pos, pnl_pct)
        if action:
            return action

        action = self._check_partial_close(pos, pnl_pct)
        if action:
            return action

        return None

    def _check_hard_exits(self, pos, price, pnl_pct):
        symbol = pos["symbol"]
        sl = pos.get("stop_loss", 0)
        trail = pos.get("trailing_sl_price", 0)
        position_type = pos.get("position_type", "long").upper()

        if position_type == "LONG":
            if sl > 0 and price <= sl:
                return {
                    "type": "CLOSE",
                    "symbol": symbol,
                    "reason": "STOP_LOSS",
                    "price": sl,
                }
            if trail > 0 and price <= trail:
                return {
                    "type": "CLOSE",
                    "symbol": symbol,
                    "reason": "TRAILING_STOP",
                    "price": trail,
                }
        else:
            if sl > 0 and price >= sl:
                return {
                    "type": "CLOSE",
                    "symbol": symbol,
                    "reason": "STOP_LOSS",
                    "price": sl,
                }
            if trail > 0 and price >= trail:
                return {
                    "type": "CLOSE",
                    "symbol": symbol,
                    "reason": "TRAILING_STOP",
                    "price": trail,
                }

        return None

    def _update_trailing(self, pos, price, peak, pnl_pct):
        ptype = pos.get("position_type", "long").upper()
        if ptype != "LONG":
            return None
        if pnl_pct < 0.015:
            return None

        trail_dist = 0.015
        if pnl_pct >= 0.030:
            trail_dist = 0.0050
        elif pnl_pct >= 0.025:
            trail_dist = 0.0080
        elif pnl_pct >= 0.020:
            trail_dist = 0.0100
        elif pnl_pct >= 0.015:
            trail_dist = 0.0150

        new_trail = peak * (1 - trail_dist)
        current_trail = pos.get("trailing_sl_price", 0)
        if new_trail > current_trail:
            return {"trailing_sl_price": new_trail, "highest_price": max(peak, price)}
        return None

    def _check_breakeven(self, pos, price, pnl_pct):
        if pos.get("position_type", "long").upper() != "LONG":
            return None
        if pnl_pct < 0.01:
            return None
        sl = pos.get("stop_loss", 0)
        entry = pos.get("entry_price", 0)
        if sl > 0 and sl < entry and pnl_pct >= 0.01:
            return {"stop_loss": entry * 1.0001}
        return None

    def _check_time_exits(self, pos, pnl_pct):
        created = pos.get("created_at")
        if not created:
            return None
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except Exception:
                return None
        hold_hours = (
            datetime.now(created.tzinfo if created.tzinfo else None) - created
        ).total_seconds() / 3600
        if hold_hours >= 8 and pnl_pct < 0.005:
            return {
                "type": "CLOSE",
                "symbol": pos["symbol"],
                "reason": "STAGNANT_8H",
                "price": None,
            }
        if hold_hours >= 6 and pnl_pct < -0.015:
            return {
                "type": "CLOSE",
                "symbol": pos["symbol"],
                "reason": "EARLY_CUT_6H",
                "price": None,
            }
        return None

    def _check_partial_close(self, pos, pnl_pct):
        tp_levels_hit = pos.get("tp_levels_hit", 0)
        entry = pos.get("entry_price", 0)
        sl = pos.get("stop_loss", 0)
        risk = (entry - sl) / entry if entry > 0 and sl > 0 else 0.01
        if risk <= 0:
            return None

        if pnl_pct >= risk * 1.5 and tp_levels_hit < 1:
            return {
                "type": "PARTIAL_CLOSE",
                "symbol": pos["symbol"],
                "reason": "TP1_1.5R",
                "close_pct": 0.40,
            }
        if pnl_pct >= risk * 2.5 and tp_levels_hit < 2:
            return {
                "type": "PARTIAL_CLOSE",
                "symbol": pos["symbol"],
                "reason": "TP2_2.5R",
                "close_pct": 0.35,
            }
        return None
