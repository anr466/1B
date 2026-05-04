#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExitManager — نظام خروج موحد
==============================
يجمع بين:
  1. MonitoringEngine: فحص SL/TP/Trailing/Time/Partial
  2. ExitEngine: حساب PnL + عمولة
  3. دعم LONG و SHORT بشكل متساوٍ

دورة الخروج:
  1. _check_hard_exits → SL أو Trailing Stop
  2. _update_trailing → تحديث وقف الخسارة المتحرك (LONG + SHORT)
  3. _check_breakeven → نقل SL إلى نقطة الدخول
  4. _check_time_exits → خروج زمني (راكد أو خسارة مبكرة)
  5. _check_partial_close → إغلاق جزئي عند مستويات TP
  6. calculate_pnl → حساب الربح/الخسارة الموحد
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ExitManager:
    def evaluate_position(self, pos: Dict, current_price: float) -> Optional[Dict]:
        """
        تقييم مركز مفتوح وإرجاع الإجراء المطلوب.

        Returns:
            None — لا إجراء
            {"type": "CLOSE", ...} — إغلاق كامل
            {"type": "PARTIAL_CLOSE", ...} — إغلاق جزئي
            {"type": "UPDATE", ...} — تحديث trailing SL أو highest_price
        """
        entry = pos.get("entry_price", 0)
        if entry <= 0:
            return None

        action = self._check_hard_exits(pos, current_price)
        if action:
            return action

        updates = self._update_trailing(pos, current_price)
        be_updates = self._check_breakeven(pos, current_price)
        if be_updates:
            updates = updates or {}
            updates.update(be_updates)
        if updates:
            return {"type": "UPDATE", "symbol": pos["symbol"], "updates": updates}

        action = self._check_time_exits(pos, current_price)
        if action:
            return action

        action = self._check_partial_close(pos, current_price)
        if action:
            return action

        return None

    def calculate_pnl(
        self,
        position: Dict,
        exit_price: float,
        reason: str,
        close_pct: float = 1.0,
    ) -> Dict:
        """
        حساب الربح/الخسارة بشكل موحد (يخصم العمولة دائماً).
        """
        symbol = position.get("symbol")
        entry = position.get("entry_price", 0)
        total_qty = position.get("quantity", 0)
        position_type = position.get("position_type", "long").upper()

        if entry <= 0 or total_qty <= 0:
            return {"success": False, "error": "invalid_position_data"}

        closing_qty = total_qty * close_pct

        if position_type == "LONG":
            pnl_raw = (exit_price - entry) * closing_qty
        else:
            pnl_raw = (entry - exit_price) * closing_qty

        entry_commission = position.get("entry_commission", 0)
        exit_notional = exit_price * closing_qty
        exit_commission = exit_notional * 0.001  # 0.1% Binance
        pnl = pnl_raw - exit_commission

        position_size = entry * total_qty
        pnl_pct = pnl / position_size if position_size > 0 else 0

        logger.info(
            f"   🚪 EXIT {symbol}: {reason} | "
            f"Entry ${entry:.4f} → Exit ${exit_price:.4f} | "
            f"Qty {closing_qty:.0f}/{total_qty:.0f} ({close_pct:.0%}) | "
            f"PnL ${pnl:.2f} ({pnl_pct * 100:+.2f}%)"
        )

        return {
            "success": True,
            "symbol": symbol,
            "reason": reason,
            "entry_price": entry,
            "exit_price": exit_price,
            "closing_quantity": closing_qty,
            "total_quantity": total_qty,
            "close_pct": close_pct,
            "pnl": pnl,
            "pnl_pct": pnl_pct * 100,
            "exit_commission": exit_commission,
            "entry_commission": entry_commission,
            "is_win": pnl > 0,
        }

    # ==================== Internal Checks ====================

    def _check_hard_exits(self, pos: Dict, price: float) -> Optional[Dict]:
        """فحص وقف الخسارة ووقف الخسارة المتحرك"""
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

    def _update_trailing(self, pos: Dict, price: float) -> Optional[Dict]:
        """تحديث وقف الخسارة المتحرك (LONG + SHORT)"""
        ptype = pos.get("position_type", "long").upper()
        entry = pos.get("entry_price", 0)
        peak = pos.get("highest_price", entry)

        if ptype == "LONG":
            pnl_pct = (price - entry) / entry if entry > 0 else 0
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
                return {
                    "trailing_sl_price": new_trail,
                    "highest_price": max(peak, price),
                }

        elif ptype == "SHORT":
            pnl_pct = (entry - price) / entry if entry > 0 else 0
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

            new_trail = peak * (1 + trail_dist)
            current_trail = pos.get("trailing_sl_price", 0)
            if current_trail == 0 or new_trail < current_trail:
                return {
                    "trailing_sl_price": new_trail,
                    "highest_price": min(peak, price),
                }

        return None

    def _check_breakeven(self, pos: Dict, price: float) -> Optional[Dict]:
        """نقل وقف الخسارة إلى نقطة الدخول عند ربح 1% — يدعم LONG و SHORT"""
        entry = pos.get("entry_price", 0)
        sl = pos.get("stop_loss", 0)
        if entry <= 0 or sl <= 0:
            return None

        ptype = pos.get("position_type", "long").upper()

        if ptype == "LONG":
            pnl_pct = (price - entry) / entry
            if pnl_pct < 0.01:
                return None
            # نقل SL فوق نقطة الدخول (يضمن ربح بسيط)
            if sl < entry:
                return {"stop_loss": entry * 1.0001}
        else:
            pnl_pct = (entry - price) / entry
            if pnl_pct < 0.01:
                return None
            # نقل SL تحت نقطة الدخول (يضمن ربح بسيط للـ SHORT)
            if sl > entry:
                return {"stop_loss": entry * 0.9999}

        return None

    def _check_time_exits(self, pos: Dict, price: float) -> Optional[Dict]:
        """خروج زمني — راكد أو خسارة مبكرة"""
        created = pos.get("created_at")
        if not created:
            return None
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except Exception:
                return None

        entry = pos.get("entry_price", 0)
        position_type = pos.get("position_type", "long").upper()
        if entry <= 0:
            return None

        if position_type == "LONG":
            pnl_pct = (price - entry) / entry
        else:
            pnl_pct = (entry - price) / entry

        now = datetime.now(created.tzinfo if created.tzinfo else None)
        hold_hours = (now - created).total_seconds() / 3600

        if hold_hours >= 8 and pnl_pct < 0.005:
            return {
                "type": "CLOSE",
                "symbol": pos["symbol"],
                "reason": "STAGNANT_8H",
                "price": price,
            }
        if hold_hours >= 6 and pnl_pct < -0.015:
            return {
                "type": "CLOSE",
                "symbol": pos["symbol"],
                "reason": "EARLY_CUT_6H",
                "price": price,
            }

        return None

    def _check_partial_close(self, pos: Dict, price: float) -> Optional[Dict]:
        """إغلاق جزئي عند مستويات TP"""
        entry = pos.get("entry_price", 0)
        sl = pos.get("stop_loss", 0)
        if entry <= 0:
            return None

        position_type = pos.get("position_type", "long").upper()
        if position_type == "LONG":
            pnl_pct = (price - entry) / entry
        else:
            pnl_pct = (entry - price) / entry

        risk = abs(entry - sl) / entry if entry > 0 and sl > 0 else 0.01
        if risk <= 0:
            return None

        tp_levels_hit = pos.get("tp_levels_hit", 0)

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

    def evaluate_positions(
        self, positions: List[Dict], current_prices: Dict[str, float]
    ) -> List[Dict]:
        """تقييم جميع المراكز المفتوحة وإرجاع الإجراءات المطلوبة"""
        actions = []
        for pos in positions:
            symbol = pos.get("symbol")
            current_price = current_prices.get(symbol)
            if not current_price:
                continue

            action = self.evaluate_position(pos, current_price)
            if action:
                # Time exits need current_price injected
                if action.get("price") is None:
                    action["price"] = current_price
                actions.append(action)

        return actions
