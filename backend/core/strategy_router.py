#!/usr/bin/env python3

import logging
from typing import Dict, Optional
from backend.core.coin_state_analyzer import CoinState

logger = logging.getLogger(__name__)


STRATEGY_MAP = {
    "TREND_CONT": {
        "name": "trend_continuation",
        "min_adx": 20,
        "min_volume_ratio": 1.0,
        "entry_strategy": "pullback_to_ema",
        "sl_atr_mult": 3.5,
        "tp_ratio": 2.0,
    },
    "BREAKOUT": {
        "name": "breakout",
        "min_adx": 10,
        "min_volume_ratio": 2.0,
        "entry_strategy": "resistance_break",
        "sl_atr_mult": 4.0,
        "tp_ratio": 2.5,
    },
    "RANGE": {
        "name": "range_trading",
        "min_adx": 0,
        "min_volume_ratio": 0.6,
        "entry_strategy": "support_bounce",
        "sl_atr_mult": 3.0,
        "tp_ratio": 1.5,
    },
}


class StrategyRouter:
    def route(self, state: CoinState) -> Optional[Dict]:
        if state.recommendation == "AVOID":
            logger.debug(
                f"   ⏭️ [{state.symbol}] AVOID: trend={state.trend} regime={state.regime}"
            )
            return None

        config = STRATEGY_MAP.get(state.recommendation)
        if not config:
            return None

        if config["min_adx"] > 0 and state.adx < config["min_adx"]:
            logger.debug(
                f"   🚫 [{state.symbol}] {state.recommendation} blocked: "
                f"ADX {state.adx:.0f} < {config['min_adx']}"
            )
            return None

        return {
            "strategy": config["name"],
            "entry_type": config["entry_strategy"],
            "sl_atr_mult": config["sl_atr_mult"],
            "tp_ratio": config["tp_ratio"],
            "min_volume_ratio": config["min_volume_ratio"],
            "state": state,
        }
