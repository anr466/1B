#!/usr/bin/env python3
"""
Volatility Module
Handles breakout strategies for high volatility environments.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from backend.core.strategy_interface import StrategyModule


class VolatilityModule(StrategyModule):
    def name(self) -> str:
        return "VolatilityModule"

    def supported_regimes(self) -> List[str]:
        return ["STRONG_TREND", "WIDE_RANGE", "HIGH_VOLATILITY"]

    def evaluate(self, df: pd.DataFrame, context: Dict) -> Optional[Dict]:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]
        current_price = close.iloc[-1]
        regime = context.get("regime", "CHOPPY")
        volatility = context.get("volatility", "LOW")

        if regime not in self.supported_regimes() and volatility != "HIGH":
            return None

        atr = self._compute_atr(df)
        atr_pct = (atr / current_price) * 100

        if atr_pct < 2.0:
            return None

        resistance = high.tail(20).quantile(0.90)
        support = low.tail(20).quantile(0.10)

        vol_ratio = volume.iloc[-1] / volume.tail(20).mean()

        if current_price > resistance and vol_ratio > 1.5:
            return {
                "type": "LONG",
                "strategy": "Volatility Breakout",
                "confidence": 75,
                "reason": f"Breakout with {vol_ratio:.1f}x volume, ATR={atr_pct:.1f}%",
            }

        if current_price < support and vol_ratio > 1.5:
            return {
                "type": "SHORT",
                "strategy": "Volatility Breakdown",
                "confidence": 75,
                "reason": f"Breakdown with {vol_ratio:.1f}x volume, ATR={atr_pct:.1f}%",
            }

        return None

    def get_entry_price(self, df: pd.DataFrame, signal: Dict) -> float:
        return df["close"].iloc[-1]

    def get_stop_loss(self, df: pd.DataFrame, signal: Dict) -> float:
        atr = self._compute_atr(df)
        current_price = df["close"].iloc[-1]
        if signal["type"] == "LONG":
            return current_price - (atr * 4.0)
        return current_price + (atr * 4.0)

    def get_take_profit(self, df: pd.DataFrame, signal: Dict) -> float:
        entry = self.get_entry_price(df, signal)
        sl = self.get_stop_loss(df, signal)
        risk = abs(entry - sl)
        if signal["type"] == "LONG":
            return entry + (risk * 2.5)
        return entry - (risk * 2.5)

    def _compute_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        return tr.rolling(period).mean().iloc[-1]
