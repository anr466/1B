#!/usr/bin/env python3
"""
Volatility Module — Updated for Continuous Signal Stream
Handles breakout strategies for high volatility environments.
Always returns SignalCandidate (never None).
"""

import pandas as pd
from typing import Dict, List
from backend.core.strategy_interface import StrategyModule
from backend.core.signal_candidate import SignalCandidate
from backend.utils.indicator_calculator import compute_atr


class VolatilityModule(StrategyModule):
    def name(self) -> str:
        return "VolatilityModule"

    def supported_regimes(self) -> List[str]:
        return ["STRONG_TREND", "WIDE_RANGE", "HIGH_VOLATILITY"]

    def evaluate(self, df: pd.DataFrame, context: Dict) -> SignalCandidate:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]
        current_price = close.iloc[-1]
        regime = context.get("regime", "CHOPPY")
        volatility = context.get("volatility", "LOW")

        atr = compute_atr(df).iloc[-1]
        atr_pct = (atr / current_price) * 100

        if regime not in self.supported_regimes() and volatility != "HIGH":
            return SignalCandidate.no_signal(
                reason=f"Regime {regime}/Volatility {volatility} not suitable for volatility strategies",
                regime=regime,
            )

        if atr_pct < 2.0:
            return SignalCandidate(
                symbol=context.get("symbol", ""),
                signal_type="NONE",
                strategy="Volatility (Low ATR)",
                confidence=10,
                reason=f"ATR% {atr_pct:.1f}% too low for volatility breakout",
                regime=regime,
            )

        resistance = high.tail(20).quantile(0.90)
        support = low.tail(20).quantile(0.10)
        vol_ratio = volume.iloc[-1] / volume.tail(20).mean()

        if current_price > resistance and vol_ratio > 1.5:
            return SignalCandidate(
                symbol=context.get("symbol", ""),
                signal_type="LONG",
                strategy="Volatility Breakout",
                confidence=75,
                reason=f"Breakout with {vol_ratio:.1f}x volume, ATR={atr_pct:.1f}%",
                regime=regime,
            )

        if current_price < support and vol_ratio > 1.5:
            return SignalCandidate(
                symbol=context.get("symbol", ""),
                signal_type="SHORT",
                strategy="Volatility Breakdown",
                confidence=75,
                reason=f"Breakdown with {vol_ratio:.1f}x volume, ATR={atr_pct:.1f}%",
                regime=regime,
            )

        return SignalCandidate(
            symbol=context.get("symbol", ""),
            signal_type="NONE",
            strategy="Volatility (No Breakout)",
            confidence=15,
            reason=f"Price within range, vol_ratio={vol_ratio:.1f}x",
            regime=regime,
        )

    def get_entry_price(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        return df["close"].iloc[-1]

    def get_stop_loss(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        atr = compute_atr(df).iloc[-1]
        current_price = df["close"].iloc[-1]
        if signal.signal_type == "LONG":
            return current_price - (atr * 4.0)
        return current_price + (atr * 4.0)

    def get_take_profit(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        entry = self.get_entry_price(df, signal)
        sl = self.get_stop_loss(df, signal)
        risk = abs(entry - sl)
        if signal.signal_type == "LONG":
            return entry + (risk * 2.5)
        return entry - (risk * 2.5)
