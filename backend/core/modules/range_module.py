#!/usr/bin/env python3
"""
Range Module
Handles mean reversion strategies for ranging markets.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from backend.core.strategy_interface import StrategyModule


class RangeModule(StrategyModule):
    def name(self) -> str:
        return "RangeModule"

    def supported_regimes(self) -> List[str]:
        return ["WIDE_RANGE", "NARROW_RANGE"]

    def evaluate(self, df: pd.DataFrame, context: Dict) -> Optional[Dict]:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        current_price = close.iloc[-1]
        regime = context.get("regime", "CHOPPY")

        if regime not in self.supported_regimes():
            return None

        support = low.tail(30).quantile(0.15)
        resistance = high.tail(30).quantile(0.85)
        range_width = (resistance - support) / support

        if range_width < 0.005:
            return None

        dist_to_support = (current_price - support) / support
        dist_to_resistance = (resistance - current_price) / current_price

        if dist_to_support <= 0.02:
            rsi = self._compute_rsi(close)
            if rsi < 45:
                return {
                    "type": "LONG",
                    "strategy": "Range Support Bounce",
                    "confidence": 65,
                    "reason": f"Price near support ({dist_to_support * 100:.1f}%), RSI={rsi:.0f}",
                }

        if dist_to_resistance <= 0.02:
            rsi = self._compute_rsi(close)
            if rsi > 55:
                return {
                    "type": "SHORT",
                    "strategy": "Range Resistance Rejection",
                    "confidence": 65,
                    "reason": f"Price near resistance ({dist_to_resistance * 100:.1f}%), RSI={rsi:.0f}",
                }

        return None

    def get_entry_price(self, df: pd.DataFrame, signal: Dict) -> float:
        return df["close"].iloc[-1]

    def get_stop_loss(self, df: pd.DataFrame, signal: Dict) -> float:
        high = df["high"]
        low = df["low"]
        support = low.tail(30).quantile(0.15)
        resistance = high.tail(30).quantile(0.85)

        if signal["type"] == "LONG":
            return support * 0.975
        return resistance * 1.025

    def get_take_profit(self, df: pd.DataFrame, signal: Dict) -> float:
        high = df["high"]
        low = df["low"]
        support = low.tail(30).quantile(0.15)
        resistance = high.tail(30).quantile(0.85)

        if signal["type"] == "LONG":
            return resistance * 0.99
        return support * 1.01

    def _compute_rsi(self, close: pd.Series, period: int = 14) -> float:
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, float("inf"))
        return (100 - (100 / (1 + rs))).iloc[-1]
