#!/usr/bin/env python3

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ExitEngine:
    def execute_exit(
        self,
        position: Dict,
        exit_price: Optional[float],
        reason: str,
        close_pct: float = 1.0,
    ) -> Dict:
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
        exit_commission = pnl_raw * 0.001
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

    def get_exit_price(
        self,
        position: Dict,
        current_price: float,
        trigger_price: Optional[float] = None,
    ) -> float:
        position_type = position.get("position_type", "long").upper()
        trail = position.get("trailing_sl_price", 0)
        sl = position.get("stop_loss", 0)

        if trigger_price and trigger_price > 0:
            return trigger_price

        if trail > 0:
            return trail

        if sl > 0:
            return sl

        return current_price
