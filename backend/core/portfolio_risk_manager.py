#!/usr/bin/env python3

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PortfolioTier:
    name: str
    min_balance: float
    max_balance: float
    max_position_pct: float
    max_heat_pct: float
    max_daily_loss_pct: float
    max_drawdown_pct: float
    max_positions: int
    max_same_direction: int
    kelly_fraction: float
    min_position_usd: float


TIERS = [
    PortfolioTier("MICRO", 0, 100, 0.05, 0.03, 0.03, 0.10, 2, 1, 0.25, 5),
    PortfolioTier("SMALL", 100, 500, 0.08, 0.04, 0.04, 0.15, 3, 2, 0.33, 8),
    PortfolioTier("MEDIUM", 500, 2000, 0.10, 0.05, 0.05, 0.20, 4, 2, 0.50, 10),
    PortfolioTier("LARGE", 2000, 10000, 0.12, 0.06, 0.06, 0.25, 5, 3, 0.50, 15),
    PortfolioTier("XLARGE", 10000, 50000, 0.15, 0.08, 0.08, 0.30, 6, 3, 0.50, 20),
    PortfolioTier("WHALE", 50000, float("inf"), 0.20, 0.10, 0.10, 0.35, 8, 4, 0.50, 50),
]


COIN_RISK_PROFILE = {
    "MAJOR": {"max_pos_pct": 1.0, "sl_atr_mult": 3.5, "risk_weight": 1.0},
    "MID_CAP": {"max_pos_pct": 0.8, "sl_atr_mult": 4.0, "risk_weight": 1.2},
    "MEME": {"max_pos_pct": 0.4, "sl_atr_mult": 5.0, "risk_weight": 2.0},
    "VOLATILE": {"max_pos_pct": 0.5, "sl_atr_mult": 4.5, "risk_weight": 1.5},
}


class PortfolioRiskManager:
    def __init__(self):
        self.tier: Optional[PortfolioTier] = None
        self.balance = 0.0

    def classify_tier(self, balance: float) -> PortfolioTier:
        for t in TIERS:
            if t.min_balance <= balance < t.max_balance:
                self.tier = t
                self.balance = balance
                return t
        self.tier = TIERS[-1]
        self.balance = balance
        return self.tier

    def get_position_size(
        self, balance: float, coin_type: str, signal_confidence: float, kelly_pct: float
    ) -> Dict:
        tier = self.classify_tier(balance)
        coin = COIN_RISK_PROFILE.get(coin_type, COIN_RISK_PROFILE["MID_CAP"])

        base_pct = tier.max_position_pct
        coin_limit_pct = base_pct * coin["max_pos_pct"]

        confidence_adj = 0.5 + (signal_confidence / 100.0) * 0.5
        kelly_adj = min(kelly_pct, tier.max_position_pct * 0.5)

        position_pct = min(
            coin_limit_pct, max(kelly_adj, base_pct * 0.3 * confidence_adj)
        )

        position_usd = balance * position_pct
        position_usd = max(tier.min_position_usd, position_usd)

        max_usd = balance * coin_limit_pct
        position_usd = min(position_usd, max_usd)

        if position_usd < tier.min_position_usd:
            return {
                "can_trade": False,
                "reason": f"Below minimum ${tier.min_position_usd}",
                "position_usd": 0,
                "position_pct": 0,
            }

        return {
            "can_trade": True,
            "position_usd": round(position_usd, 2),
            "position_pct": round(position_usd / balance * 100, 2),
            "tier": tier.name,
            "coin_type": coin_type,
            "coin_limit_pct": round(coin_limit_pct * 100, 2),
            "kelly_used_pct": round(kelly_adj * 100, 2),
        }

    def check_heat(self, open_positions: List[Dict], balance: float) -> Dict:
        tier = self.classify_tier(balance)
        total_risk = 0
        risks = []

        for pos in open_positions:
            entry = pos.get("entry_price", 0)
            sl = pos.get("stop_loss", 0)
            qty = pos.get("quantity", 0)
            coin_type = pos.get("coin_type", "MID_CAP")
            risk = abs(entry - sl) * qty if entry > 0 and sl > 0 else 0
            risk_pct = (risk / balance * 100) if balance > 0 else 0
            total_risk += risk
            risks.append(
                {
                    "symbol": pos.get("symbol"),
                    "risk_usd": round(risk, 2),
                    "risk_pct": round(risk_pct, 3),
                }
            )

        heat_pct = (total_risk / balance * 100) if balance > 0 else 0
        available = max(0, tier.max_heat_pct * 100 - heat_pct)

        return {
            "tier": tier.name,
            "current_heat_pct": round(heat_pct, 2),
            "max_heat_pct": round(tier.max_heat_pct * 100, 2),
            "available_heat_pct": round(available, 2),
            "can_open": heat_pct < tier.max_heat_pct * 100,
            "positions_count": len(open_positions),
            "max_positions": tier.max_positions,
            "risks": risks,
        }

    def check_daily_limits(self, daily_state: Dict, balance: float) -> Tuple[bool, str]:
        tier = self.classify_tier(balance)

        if daily_state.get("trades_today", 0) >= tier.max_positions * 2:
            return (
                False,
                f"Daily trade limit: {daily_state['trades_today']}/{tier.max_positions * 2}",
            )

        max_loss = balance * tier.max_daily_loss_pct
        if daily_state.get("daily_pnl", 0) < -max_loss:
            return (
                False,
                f"Daily loss limit: ${daily_state['daily_pnl']:.2f} (limit: -${max_loss:.2f})",
            )

        peak = daily_state.get("peak_balance", balance)
        if peak > 0:
            drawdown = (peak - balance) / peak
            if drawdown >= tier.max_drawdown_pct:
                return (
                    False,
                    f"Max drawdown: {drawdown * 100:.1f}% (limit: {tier.max_drawdown_pct * 100:.0f}%)",
                )

        cooldown = daily_state.get("cooldown_until")
        if cooldown and datetime.now() < cooldown:
            remaining = (cooldown - datetime.now()).total_seconds() / 60
            return False, f"Cooldown: {remaining:.0f}min remaining"

        return True, "OK"

    def check_directional_stress(
        self, open_positions: List[Dict], new_side: str
    ) -> Tuple[bool, str]:
        tier = self.classify_tier(self.balance)
        same_count = sum(
            1
            for p in open_positions
            if p.get("position_type", "long").upper() == new_side.upper()
        )
        if same_count >= tier.max_same_direction:
            return (
                False,
                f"Directional stress: {same_count} {new_side} positions (max: {tier.max_same_direction})",
            )
        return True, "OK"

    def check_concentration(
        self, open_positions: List[Dict], new_symbol: str
    ) -> Tuple[bool, str]:
        existing = [p for p in open_positions if p.get("symbol") == new_symbol]
        if existing:
            return False, f"Already have position in {new_symbol}"
        return True, "OK"

    def get_summary(
        self, balance: float, open_positions: List[Dict], daily_state: Dict
    ) -> Dict:
        tier = self.classify_tier(balance)
        heat = self.check_heat(open_positions, balance)
        daily_ok, daily_reason = self.check_daily_limits(daily_state, balance)

        return {
            "tier": tier.name,
            "balance": round(balance, 2),
            "balance_range": f"${tier.min_balance:.0f} - ${tier.max_balance:.0f}"
            if tier.max_balance != float("inf")
            else f"${tier.min_balance:.0f}+",
            "max_position_pct": f"{tier.max_position_pct * 100:.0f}%",
            "max_heat_pct": f"{tier.max_heat_pct * 100:.0f}%",
            "max_daily_loss_pct": f"{tier.max_daily_loss_pct * 100:.0f}%",
            "max_drawdown_pct": f"{tier.max_drawdown_pct * 100:.0f}%",
            "max_positions": tier.max_positions,
            "current_positions": len(open_positions),
            "heat": heat,
            "daily_ok": daily_ok,
            "daily_reason": daily_reason,
        }
