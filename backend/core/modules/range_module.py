#!/usr/bin/env python3
"""
Range Module — Updated for Continuous Signal Stream
Handles mean reversion strategies for ranging markets.
Always returns SignalCandidate (never None).
"""

import pandas as pd
from typing import Dict, List
from backend.core.strategy_interface import StrategyModule
from backend.core.signal_candidate import SignalCandidate
from backend.utils.indicator_calculator import compute_atr, compute_rsi


class RangeModule(StrategyModule):
    def name(self) -> str:
        return "RangeModule"

    def supported_regimes(self) -> List[str]:
        return ["WIDE_RANGE", "NARROW_RANGE"]

    def evaluate(self, df: pd.DataFrame, context: Dict) -> SignalCandidate:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        current_price = close.iloc[-1]
        regime = context.get("regime", "CHOPPY")
        regime_scores = context.get("regime_scores", {})
        range_score = regime_scores.get("WIDE_RANGE", 0) + regime_scores.get("NARROW_RANGE", 0)

        if regime not in self.supported_regimes():
            return SignalCandidate.no_signal(
                reason=f"Regime {regime} not supported by RangeModule",
                regime=regime,
            )

        # Volatility filter
        range_30 = (high.tail(30).max() - low.tail(30).min()) / low.tail(30).min()
        if range_30 > 0.25:
            return SignalCandidate(
                symbol=context.get("symbol", ""),
                signal_type="NONE",
                strategy="Range (Too Volatile)",
                confidence=10,
                reason=f"30-period range {range_30*100:.1f}% too volatile for mean reversion",
                regime=regime,
            )

        # Trend filter
        ema_21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
        ema_55 = close.ewm(span=55, adjust=False).mean().iloc[-1]
        if ema_21 < ema_55 * 0.95:
            return SignalCandidate(
                symbol=context.get("symbol", ""),
                signal_type="NONE",
                strategy="Range (Strong Downtrend)",
                confidence=10,
                reason="Strong downtrend — not suitable for range bounce",
                regime=regime,
            )

        support = low.tail(30).quantile(0.15)
        resistance = high.tail(30).quantile(0.85)
        range_width = (resistance - support) / support

        if range_width < 0.005:
            return SignalCandidate.no_signal(
                reason=f"Range width {range_width*100:.2f}% too narrow",
                regime=regime,
            )

        dist_to_support = (current_price - support) / support
        dist_to_resistance = (resistance - current_price) / current_price

        if dist_to_support <= 0.03:
            rsi = compute_rsi(df).iloc[-1]
            if rsi < 45:
                confidence = min(70 + (range_score - 50) * 0.4, 90)
                return SignalCandidate(
                    symbol=context.get("symbol", ""),
                    signal_type="LONG",
                    strategy="Range Support Bounce",
                    confidence=confidence,
                    reason=f"Price near support ({dist_to_support * 100:.1f}%), RSI={rsi:.0f}, range={range_width * 100:.1f}%",
                    regime=regime,
                )

        if dist_to_resistance <= 0.03:
            rsi = compute_rsi(df).iloc[-1]
            if rsi > 55:
                confidence = min(70 + (range_score - 50) * 0.4, 90)
                return SignalCandidate(
                    symbol=context.get("symbol", ""),
                    signal_type="SHORT",
                    strategy="Range Resistance Rejection",
                    confidence=confidence,
                    reason=f"Price near resistance ({dist_to_resistance * 100:.1f}%), RSI={rsi:.0f}, range={range_width * 100:.1f}%",
                    regime=regime,
                )

        return SignalCandidate(
            symbol=context.get("symbol", ""),
            signal_type="NONE",
            strategy="Range (No Setup)",
            confidence=15,
            reason=f"Price not near support/resistance (dist_s={dist_to_support*100:.1f}%, dist_r={dist_to_resistance*100:.1f}%)",
            regime=regime,
        )

    def get_entry_price(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        return df["close"].iloc[-1]

    def get_stop_loss(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        atr = compute_atr(df).iloc[-1]
        if signal.signal_type == "LONG":
            entry = df["close"].iloc[-1]
            sl = entry - (2.0 * atr)
            support = df["low"].tail(30).quantile(0.15)
            return min(sl, support * 0.975)
        else:
            entry = df["close"].iloc[-1]
            sl = entry + (2.0 * atr)
            resistance = df["high"].tail(30).quantile(0.85)
            return max(sl, resistance * 1.025)

    def get_take_profit(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        entry = df["close"].iloc[-1]
        sl = self.get_stop_loss(df, signal)
        risk = abs(entry - sl)

        if signal.signal_type == "LONG":
            tp_rr = entry + (2.0 * risk)
            resistance = df["high"].tail(30).quantile(0.85)
            tp_capped = resistance * 0.99
            tp_min = entry + (risk * 1.5)
            return max(tp_min, tp_rr) if tp_capped < tp_min else min(tp_rr, tp_capped)
        else:
            tp_rr = entry - (2.0 * risk)
            support = df["low"].tail(30).quantile(0.15)
            tp_capped = support * 1.01
            tp_min = entry - (risk * 1.5)
            return min(tp_min, tp_rr) if tp_capped > tp_min else max(tp_rr, tp_capped)
