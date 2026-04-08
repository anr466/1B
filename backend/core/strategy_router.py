#!/usr/bin/env python3

import logging
from typing import Dict, Optional
from backend.core.coin_state_analyzer import CoinState

logger = logging.getLogger(__name__)


STRATEGY_CONFIG = {
    "TREND_CONT": {
        "name": "trend_continuation",
        "min_adx": 15,
        "min_volume_ratio": 0.8,
        "entry_strategy": "pullback_to_ema",
        "sl_atr_mult": 3.5,
        "tp_ratio": 2.0,
        "allowed_regimes": {"STRONG_TREND", "WEAK_TREND"},
        "allowed_volatility": {"LOW", "MEDIUM", "HIGH"},
        "reject_if": {"momentum": "DECAYING"},
    },
    "BREAKOUT": {
        "name": "breakout",
        "min_adx": 10,
        "min_volume_ratio": 1.5,
        "entry_strategy": "resistance_break",
        "sl_atr_mult": 4.0,
        "tp_ratio": 2.5,
        "allowed_regimes": {"STRONG_TREND", "WEAK_TREND", "WIDE_RANGE"},
        "allowed_volatility": {"LOW", "MEDIUM", "HIGH", "VERY_HIGH"},
        "reject_if": {"volume_trend": "DECLINING"},
    },
    "RANGE": {
        "name": "range_trading",
        "min_adx": 0,
        "min_volume_ratio": 0.5,
        "entry_strategy": "support_bounce",
        "sl_atr_mult": 3.0,
        "tp_ratio": 1.5,
        "allowed_regimes": {"WIDE_RANGE", "NARROW_RANGE"},
        "allowed_volatility": {"LOW", "MEDIUM", "HIGH"},
        "reject_if": {"momentum": "ACCELERATING"},
    },
}


class StrategyRouter:
    def route(self, state: CoinState) -> Optional[Dict]:
        if state.recommendation == "AVOID":
            return None

        config = STRATEGY_CONFIG.get(state.recommendation)
        if not config:
            return None

        if state.regime not in config["allowed_regimes"]:
            return None

        if state.volatility not in config["allowed_volatility"]:
            return None

        for key, val in config["reject_if"].items():
            if getattr(state, key, None) == val:
                return None

        if config["min_adx"] > 0 and state.adx < config["min_adx"]:
            return None

        if state.risk_profile == "HIGH_RISK":
            config = {
                **config,
                "sl_atr_mult": config["sl_atr_mult"] * 1.3,
                "tp_ratio": config["tp_ratio"] * 0.8,
            }

        return {
            "strategy": config["name"],
            "entry_type": config["entry_strategy"],
            "sl_atr_mult": config["sl_atr_mult"],
            "tp_ratio": config["tp_ratio"],
            "min_volume_ratio": config["min_volume_ratio"],
            "state": state,
        }
