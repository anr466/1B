#!/usr/bin/env python3
"""
Scalping Module
Handles quick scalping strategies for choppy/ranging markets.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from backend.core.strategy_interface import StrategyModule


class ScalpingModule(StrategyModule):
    def name(self) -> str:
        return "ScalpingModule"

    def supported_regimes(self) -> List[str]:
        return ["CHOPPY", "NARROW_RANGE"]

    def evaluate(self, df: pd.DataFrame, context: Dict) -> Optional[Dict]:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        current_price = close.iloc[-1]
        regime = context.get("regime", "CHOPPY")

        if regime not in self.supported_regimes():
            return None

        rsi = self._compute_rsi(close)
        support = low.tail(20).quantile(0.15)
        resistance = high.tail(20).quantile(0.85)
        range_w = (resistance - support) / support * 100 if support > 0 else 0

        if range_w < 0.3:
            return None

        dist_to_support = (
            (current_price - support) / support * 100 if support > 0 else 999
        )
        dist_to_resistance = (
            (resistance - current_price) / current_price * 100
            if current_price > 0
            else 999
        )

        if dist_to_support <= 1.5 and rsi < 45:
            return {
                "type": "LONG",
                "strategy": "Micro Scalp Support",
                "confidence": 55,
                "reason": f"Price near support ({dist_to_support:.1f}%), RSI={rsi:.0f}",
            }

        if dist_to_resistance <= 1.5 and rsi > 55:
            return {
                "type": "SHORT",
                "strategy": "Micro Scalp Resistance",
                "confidence": 55,
                "reason": f"Price near resistance ({dist_to_resistance:.1f}%), RSI={rsi:.0f}",
            }

        return None

    def get_entry_price(self, df: pd.DataFrame, signal: Dict) -> float:
        return df["close"].iloc[-1]

    def get_stop_loss(self, df: pd.DataFrame, signal: Dict) -> float:
        atr = self._compute_atr(df)
        current_price = df["close"].iloc[-1]
        if signal["type"] == "LONG":
            return current_price - (atr * 2.5)
        return current_price + (atr * 2.5)

    def get_take_profit(self, df: pd.DataFrame, signal: Dict) -> float:
        entry = self.get_entry_price(df, signal)
        sl = self.get_stop_loss(df, signal)
        risk = abs(entry - sl)
        if signal["type"] == "LONG":
            return entry + (risk * 1.5)
        return entry - (risk * 1.5)

    def _compute_rsi(self, close: pd.Series, period: int = 14) -> float:
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, float("inf"))
        return (100 - (100 / (1 + rs))).iloc[-1]

    def _compute_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        return tr.rolling(period).mean().iloc[-1]
