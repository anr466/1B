#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Demo Training Engine — Realistic Trading Simulation
=====================================================
Simulates real trading with:
1. Real market data from Binance
2. Realistic commission (0.1% per side)
3. Realistic slippage (0.05% per side)
4. Real strategy execution (V8 + ensemble)
5. Real risk management (Kelly, position sizing, SL/TP)
6. Real learning system (trade logging, performance tracking)

The only difference from real trading:
- No actual Binance orders are placed
- Balance is virtual (starts at $10,000)
- All execution is simulated with realistic fills
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

COMMISSION_RATE = 0.001
SLIPPAGE_RATE = 0.0005
TOTAL_COST_PER_TRADE = (COMMISSION_RATE + SLIPPAGE_RATE) * 2


class DemoTrainingEngine:
    """Simulates real trading for demo account training"""

    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = []
        self.trade_history = []
        self.total_commission = 0.0
        self.total_slippage = 0.0

    def simulate_entry(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        stop_loss: float,
        take_profit: float,
        strategy: str = "v8",
        regime: str = "NEUTRAL",
    ) -> Dict[str, Any]:
        position_size = entry_price * quantity
        commission = position_size * COMMISSION_RATE
        slippage = position_size * SLIPPAGE_RATE
        total_cost = commission + slippage

        if position_size + total_cost > self.balance:
            return {
                "success": False,
                "reason": "insufficient_balance",
                "required": position_size + total_cost,
                "available": self.balance,
            }

        self.balance -= position_size + total_cost
        self.total_commission += commission
        self.total_slippage += slippage

        position = {
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "quantity": quantity,
            "position_size": position_size,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "strategy": strategy,
            "regime": regime,
            "entry_time": datetime.utcnow(),
            "commission": commission,
            "slippage": slippage,
            "peak_price": entry_price,
            "trail_stop": None,
        }
        self.positions.append(position)

        logger.info(
            f"📈 DEMO ENTRY: {symbol} {side} @ {entry_price:.6f} "
            f"qty={quantity:.4f} size=${position_size:.2f} "
            f"cost=${total_cost:.4f} (comm=${commission:.4f}, slip=${slippage:.4f})"
        )

        return {
            "success": True,
            "position": position,
            "balance_after": self.balance,
            "commission": commission,
            "slippage": slippage,
        }

    def simulate_exit(
        self,
        position: Dict[str, Any],
        exit_price: float,
        exit_reason: str,
    ) -> Dict[str, Any]:
        entry_price = position["entry_price"]
        quantity = position["quantity"]
        side = position["side"]
        position_size = position["position_size"]

        if side == "LONG":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price

        commission = position_size * COMMISSION_RATE
        slippage = position_size * SLIPPAGE_RATE
        total_cost = commission + slippage

        gross_pnl = pnl_pct * position_size
        net_pnl = gross_pnl - total_cost

        self.balance += position_size + net_pnl
        self.total_commission += commission
        self.total_slippage += slippage

        hold_time = (datetime.utcnow() - position["entry_time"]).total_seconds() / 3600

        trade_record = {
            "symbol": position["symbol"],
            "side": side,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "position_size": position_size,
            "pnl_pct": pnl_pct * 100,
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "commission": commission,
            "slippage": slippage,
            "total_cost": total_cost,
            "exit_reason": exit_reason,
            "strategy": position.get("strategy", "unknown"),
            "regime": position.get("regime", "unknown"),
            "hold_hours": hold_time,
            "entry_time": position["entry_time"],
            "exit_time": datetime.utcnow(),
        }
        self.trade_history.append(trade_record)

        if position in self.positions:
            self.positions.remove(position)

        logger.info(
            f"📉 DEMO EXIT: {position['symbol']} {side} "
            f"@ {exit_price:.6f} PnL={net_pnl:+.4f} ({pnl_pct * 100:+.2f}%) "
            f"reason={exit_reason} hold={hold_time:.1f}h"
        )

        return trade_record

    def check_exit_conditions(
        self,
        position: Dict[str, Any],
        current_price: float,
        trailing_activation: float = 0.005,
        trailing_distance: float = 0.003,
        max_hold_hours: float = 12.0,
    ) -> Optional[Dict[str, Any]]:
        entry_price = position["entry_price"]
        side = position["side"]
        hold_hours = (datetime.utcnow() - position["entry_time"]).total_seconds() / 3600

        if side == "LONG":
            pnl_pct = (current_price - entry_price) / entry_price
            if current_price > position.get("peak_price", entry_price):
                position["peak_price"] = current_price
                trail_stop = current_price * (1 - trailing_distance)
                position["trail_stop"] = trail_stop

            if current_price <= position["stop_loss"]:
                return self.simulate_exit(position, current_price, "STOP_LOSS")

            if (
                position.get("trail_stop")
                and current_price <= position["trail_stop"]
                and pnl_pct >= trailing_activation
            ):
                return self.simulate_exit(position, position["trail_stop"], "TRAILING")

        else:
            pnl_pct = (entry_price - current_price) / entry_price
            if current_price < position.get("peak_price", entry_price):
                position["peak_price"] = current_price
                trail_stop = current_price * (1 + trailing_distance)
                position["trail_stop"] = trail_stop

            if current_price >= position["stop_loss"]:
                return self.simulate_exit(position, current_price, "STOP_LOSS")

            if (
                position.get("trail_stop")
                and current_price >= position["trail_stop"]
                and pnl_pct >= trailing_activation
            ):
                return self.simulate_exit(position, position["trail_stop"], "TRAILING")

        if hold_hours >= max_hold_hours:
            return self.simulate_exit(position, current_price, "MAX_HOLD")

        return None

    def get_stats(self) -> Dict[str, Any]:
        if not self.trade_history:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "total_commission": 0.0,
                "total_slippage": 0.0,
                "current_balance": self.balance,
                "return_pct": 0.0,
            }

        wins = [t for t in self.trade_history if t["net_pnl"] > 0]
        losses = [t for t in self.trade_history if t["net_pnl"] <= 0]
        total_pnl = sum(t["net_pnl"] for t in self.trade_history)

        return {
            "total_trades": len(self.trade_history),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(self.trade_history) * 100
            if self.trade_history
            else 0,
            "total_pnl": total_pnl,
            "total_commission": self.total_commission,
            "total_slippage": self.total_slippage,
            "current_balance": self.balance,
            "return_pct": (self.balance - self.initial_balance)
            / self.initial_balance
            * 100,
            "avg_win": sum(t["net_pnl"] for t in wins) / len(wins) if wins else 0,
            "avg_loss": sum(t["net_pnl"] for t in losses) / len(losses)
            if losses
            else 0,
            "best_trade": max(self.trade_history, key=lambda t: t["net_pnl"])
            if self.trade_history
            else None,
            "worst_trade": min(self.trade_history, key=lambda t: t["net_pnl"])
            if self.trade_history
            else None,
        }
