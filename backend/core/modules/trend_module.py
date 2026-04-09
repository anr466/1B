#!/usr/bin/env python3
"""
Trend Module
Handles trend-following strategies for both Long and Short positions.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from backend.core.strategy_interface import StrategyModule


class TrendModule(StrategyModule):
    def name(self) -> str:
        return "TrendModule"

    def supported_regimes(self) -> List[str]:
        return ["STRONG_TREND", "WEAK_TREND"]

    def evaluate(self, df: pd.DataFrame, context: Dict) -> Optional[Dict]:
        close = df["close"]
        ema21 = close.ewm(span=21, adjust=False).mean()
        ema55 = close.ewm(span=55, adjust=False).mean()
        atr = self._compute_atr(df)
        current_price = close.iloc[-1]
        trend = context.get("trend", "NEUTRAL")
        regime = context.get("regime", "CHOPPY")

        if regime not in self.supported_regimes():
            return None

        if trend == "UP":
            if current_price > ema21.iloc[-1] and ema21.iloc[-1] > ema55.iloc[-1]:
                dist_to_ema21 = (current_price - ema21.iloc[-1]) / ema21.iloc[-1]
                if 0 <= dist_to_ema21 <= 0.03:
                    return {
                        "type": "LONG",
                        "strategy": "Trend Pullback",
                        "confidence": 80,
                        "reason": f"Strong uptrend, price pulling back to EMA21 ({dist_to_ema21 * 100:.1f}%)",
                    }
                elif current_price > df["high"].tail(20).quantile(0.85):
                    return {
                        "type": "LONG",
                        "strategy": "Trend Breakout",
                        "confidence": 70,
                        "reason": "Breakout above 20-period high in uptrend",
                    }

        elif trend == "DOWN":
            if current_price < ema21.iloc[-1] and ema21.iloc[-1] < ema55.iloc[-1]:
                dist_to_ema21 = (ema21.iloc[-1] - current_price) / ema21.iloc[-1]
                if 0 <= dist_to_ema21 <= 0.03:
                    return {
                        "type": "SHORT",
                        "side": "SHORT",
                        "strategy": "Trend Pullback Short",
                        "confidence": 80,
                        "reason": f"Strong downtrend, price pulling back to EMA21 ({dist_to_ema21 * 100:.1f}%)",
                    }

        return None

    def get_entry_price(self, df: pd.DataFrame, signal: Dict) -> float:
        return df["close"].iloc[-1]

    def get_stop_loss(self, df: pd.DataFrame, signal: Dict) -> float:
        atr = self._compute_atr(df)
        current_price = df["close"].iloc[-1]
        if signal["type"] == "LONG":
            return current_price - (atr * 3.5)
        return current_price + (atr * 3.5)

    def get_take_profit(self, df: pd.DataFrame, signal: Dict) -> float:
        entry = self.get_entry_price(df, signal)
        sl = self.get_stop_loss(df, signal)
        risk = abs(entry - sl)
        if signal["type"] == "LONG":
            return entry + (risk * 2.0)
        return entry - (risk * 2.0)

    def _compute_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        return tr.rolling(period).mean().iloc[-1]
