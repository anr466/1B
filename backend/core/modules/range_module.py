#!/usr/bin/env python3
"""
Range Module — FIXED
Handles mean reversion strategies for ranging markets.
Fixes: volatility filter, trend filter, ATR-based SL, higher confidence threshold.
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

        # FIX 1: Volatility filter — range strategies need LOW volatility
        # Skip if 30-period range > 15% (too volatile for mean reversion)
        range_30 = (high.tail(30).max() - low.tail(30).min()) / low.tail(30).min()
        if range_30 > 0.15:
            return None  # Too volatile for range trading

        # FIX 2: Trend filter — don't LONG in strong downtrend
        ema_21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
        ema_55 = close.ewm(span=55, adjust=False).mean().iloc[-1]
        if ema_21 < ema_55 * 0.98:
            return None  # Strong downtrend — no range bounces

        support = low.tail(30).quantile(0.15)
        resistance = high.tail(30).quantile(0.85)
        range_width = (resistance - support) / support

        if range_width < 0.005:
            return None

        dist_to_support = (current_price - support) / support
        dist_to_resistance = (resistance - current_price) / current_price

        if dist_to_support <= 0.02:
            rsi = self._compute_rsi(close)
            # FIX 3: Require stronger oversignal for range bounce
            if rsi < 40:  # Was 45 — now requires deeper oversold
                # FIX 4: Higher confidence threshold
                confidence = 70 if range_width > 0.05 else 65
                return {
                    "type": "LONG",
                    "strategy": "Range Support Bounce",
                    "confidence": confidence,
                    "reason": f"Price near support ({dist_to_support * 100:.1f}%), RSI={rsi:.0f}, range={range_width * 100:.1f}%",
                }

        if dist_to_resistance <= 0.02:
            rsi = self._compute_rsi(close)
            if rsi > 60:  # Was 55 — now requires stronger overbought
                confidence = 70 if range_width > 0.05 else 65
                return {
                    "type": "SHORT",
                    "strategy": "Range Resistance Rejection",
                    "confidence": confidence,
                    "reason": f"Price near resistance ({dist_to_resistance * 100:.1f}%), RSI={rsi:.0f}, range={range_width * 100:.1f}%",
                }

        return None

    def get_entry_price(self, df: pd.DataFrame, signal: Dict) -> float:
        return df["close"].iloc[-1]

    def get_stop_loss(self, df: pd.DataFrame, signal: Dict) -> float:
        """FIX 5: ATR-based SL instead of fixed percentage below support"""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # Calculate ATR (14-period)
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.tail(14).mean()

        if signal["type"] == "LONG":
            # SL = entry - 2*ATR (wider for volatile coins)
            entry = df["close"].iloc[-1]
            sl = entry - (2.0 * atr)
            # Also ensure SL is below recent support
            support = low.tail(30).quantile(0.15)
            return min(sl, support * 0.975)
        else:
            entry = df["close"].iloc[-1]
            sl = entry + (2.0 * atr)
            resistance = high.tail(30).quantile(0.85)
            return max(sl, resistance * 1.025)

    def get_take_profit(self, df: pd.DataFrame, signal: Dict) -> float:
        """FIX 6: Risk-reward based TP (minimum 2:1)"""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # Calculate ATR
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.tail(14).mean()

        entry = df["close"].iloc[-1]
        sl = self.get_stop_loss(df, signal)
        risk = abs(entry - sl)

        if signal["type"] == "LONG":
            # TP = entry + 2*risk (minimum 2:1 RR)
            tp_rr = entry + (2.0 * risk)
            # Also cap at resistance
            resistance = high.tail(30).quantile(0.85)
            return min(tp_rr, resistance * 0.99)
        else:
            tp_rr = entry - (2.0 * risk)
            support = low.tail(30).quantile(0.15)
            return max(tp_rr, support * 1.01)

    def _compute_rsi(self, close: pd.Series, period: int = 14) -> float:
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, float("inf"))
        return (100 - (100 / (1 + rs))).iloc[-1]
