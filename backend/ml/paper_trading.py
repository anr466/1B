#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Paper Trading Mode — تداول تجريبي على بيانات حية بدون مال حقيقي.

يُنفّذ نفس منطق التداول الحقيقي لكن بدون إرسال أوامر لبينانس.
يسجل النتائج للمقارنة مع backtest لاحقاً.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """محاكي التداول — يطبق إشارات الاستراتيجية بدون تنفيذ حقيقي."""

    def __init__(self, db_manager=None, initial_balance: float = 10000.0):
        self.db = db_manager
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.open_positions: List[Dict] = []
        self.trade_log: List[Dict] = []
        self.stats = {
            "total_signals": 0,
            "executed_trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl_pct": 0,
            "started_at": None,
        }

    def start_session(self):
        self.stats["started_at"] = datetime.now().isoformat()
        logger.info(f"📝 Paper Trading started | Balance: ${self.initial_balance:,.2f}")

    def process_signal(self, signal: Dict) -> Optional[Dict]:
        """معالجة إشارة تداول — تسجيل بدون تنفيذ."""
        self.stats["total_signals"] += 1

        symbol = signal.get("symbol", "UNKNOWN")
        entry_price = signal.get("entry_price", signal.get("price", 0))
        strategy = signal.get("strategy", "unknown")
        side = signal.get("side", "LONG")

        if entry_price <= 0:
            return None

        has_open = any(p["symbol"] == symbol for p in self.open_positions)
        if has_open:
            return None

        position = {
            "symbol": symbol,
            "side": side,
            "strategy": strategy,
            "entry_price": entry_price,
            "entry_time": datetime.now().isoformat(),
            "sl": signal.get("stop_loss", entry_price * 0.99),
            "tp": signal.get("take_profit", entry_price * 1.02),
            "size_pct": signal.get("position_size_pct", 6),
            "peak": entry_price,
        }

        self.open_positions.append(position)
        self.stats["executed_trades"] += 1

        logger.info(f"📝 PAPER OPEN: {symbol} @ {entry_price} | {strategy} | {side}")
        return {"action": "PAPER_OPEN", **position}

    def manage_positions(self, current_prices: Dict[str, float]) -> List[Dict]:
        """إدارة الصفقات المفتوحة — فحص SL/TP/Trailing."""
        exits = []

        for pos in list(self.open_positions):
            symbol = pos["symbol"]
            if symbol not in current_prices:
                continue

            current = current_prices[symbol]
            side = pos["side"]

            if side == "LONG":
                pnl_pct = (current - pos["entry_price"]) / pos["entry_price"]
            else:
                pnl_pct = (pos["entry_price"] - current) / pos["entry_price"]

            if side == "LONG" and current > pos.get("peak", pos["entry_price"]):
                pos["peak"] = current

            exit_reason = None
            if side == "LONG" and current <= pos["sl"]:
                exit_reason = "STOP_LOSS"
            elif side == "SHORT" and current >= pos["sl"]:
                exit_reason = "STOP_LOSS"
            elif side == "LONG" and current >= pos.get("tp", float("inf")):
                exit_reason = "TAKE_PROFIT"
            elif side == "SHORT" and current <= pos.get("tp", 0):
                exit_reason = "TAKE_PROFIT"

            if exit_reason:
                net_pnl = pnl_pct - 0.0015
                exit_data = {
                    "symbol": symbol,
                    "side": side,
                    "strategy": pos["strategy"],
                    "entry_price": pos["entry_price"],
                    "exit_price": current,
                    "pnl_pct": round(net_pnl * 100, 3),
                    "is_win": net_pnl > 0,
                    "exit_reason": exit_reason,
                    "exit_time": datetime.now().isoformat(),
                    "hold_from": pos["entry_time"],
                }

                self.trade_log.append(exit_data)
                self.open_positions.remove(pos)

                if net_pnl > 0:
                    self.stats["wins"] += 1
                else:
                    self.stats["losses"] += 1
                self.stats["total_pnl_pct"] += net_pnl

                logger.info(
                    f"📝 PAPER CLOSE: {symbol} | {exit_reason} | "
                    f"PnL: {net_pnl * 100:+.2f}% | WR: {self._win_rate():.1%}"
                )
                exits.append(exit_data)

        return exits

    def _win_rate(self) -> float:
        total = self.stats["wins"] + self.stats["losses"]
        return self.stats["wins"] / total if total > 0 else 0

    def get_stats(self) -> Dict[str, Any]:
        total = self.stats["wins"] + self.stats["losses"]
        return {
            "mode": "PAPER_TRADING",
            "initial_balance": self.initial_balance,
            "current_balance": self.initial_balance
            * (1 + self.stats["total_pnl_pct"] / 100),
            "total_signals": self.stats["total_signals"],
            "executed_trades": self.stats["executed_trades"],
            "open_positions": len(self.open_positions),
            "completed_trades": total,
            "wins": self.stats["wins"],
            "losses": self.stats["losses"],
            "win_rate": round(self._win_rate(), 3),
            "total_pnl_pct": round(self.stats["total_pnl_pct"], 3),
            "started_at": self.stats["started_at"],
            "trade_log": self.trade_log[-50:],
        }


_engine = None


def get_paper_engine(db_manager=None) -> PaperTradingEngine:
    global _engine
    if _engine is None:
        _engine = PaperTradingEngine(db_manager)
    return _engine
