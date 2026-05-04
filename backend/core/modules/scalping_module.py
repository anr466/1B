#!/usr/bin/env python3
"""
Scalping Module — Updated for Continuous Signal Stream
Handles quick scalping strategies for choppy/ranging markets.
Always returns SignalCandidate (never None).
"""

import pandas as pd
from typing import Dict, List
from backend.core.strategy_interface import StrategyModule
from backend.core.signal_candidate import SignalCandidate
from backend.utils.indicator_calculator import compute_atr, compute_rsi


class ScalpingModule(StrategyModule):
    def name(self) -> str:
        return "ScalpingModule"

    def supported_regimes(self) -> List[str]:
        return ["CHOPPY", "NARROW_RANGE"]

    def evaluate(self, df: pd.DataFrame, context: Dict) -> SignalCandidate:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]
        current_price = close.iloc[-1]
        regime = context.get("regime", "CHOPPY")

        if regime not in self.supported_regimes():
            return SignalCandidate.no_signal(
                reason=f"Regime {regime} not supported by ScalpingModule",
                regime=regime,
            )

        rsi = compute_rsi(df).iloc[-1]
        support = low.tail(20).quantile(0.15)
        resistance = high.tail(20).quantile(0.85)
        range_w = (resistance - support) / support * 100 if support > 0 else 0

        if range_w < 0.3:
            return SignalCandidate(
                symbol=context.get("symbol", ""),
                signal_type="NONE",
                strategy="Scalp (Range Too Narrow)",
                confidence=5,
                reason=f"Range width {range_w:.2f}% too narrow for scalping",
                regime=regime,
            )

        vol_avg = volume.tail(20).mean()
        vol_ratio = volume.iloc[-1] / vol_avg if vol_avg > 0 else 1.0
        if vol_ratio < 0.6:
            return SignalCandidate(
                symbol=context.get("symbol", ""),
                signal_type="NONE",
                strategy="Scalp (Low Volume)",
                confidence=10,
                reason=f"Volume ratio {vol_ratio:.1f}x too low for scalping",
                regime=regime,
            )

        dist_to_support = (current_price - support) / support * 100 if support > 0 else 999
        dist_to_resistance = (resistance - current_price) / current_price * 100 if current_price > 0 else 999

        if dist_to_support <= 1.5 and rsi < 45:
            return SignalCandidate(
                symbol=context.get("symbol", ""),
                signal_type="LONG",
                strategy="Micro Scalp Support",
                confidence=60,
                reason=f"Price near support ({dist_to_support:.1f}%), RSI={rsi:.0f}, Vol={vol_ratio:.1f}x",
                regime=regime,
            )

        if dist_to_resistance <= 1.5 and rsi > 55:
            return SignalCandidate(
                symbol=context.get("symbol", ""),
                signal_type="SHORT",
                strategy="Micro Scalp Resistance",
                confidence=60,
                reason=f"Price near resistance ({dist_to_resistance:.1f}%), RSI={rsi:.0f}, Vol={vol_ratio:.1f}x",
                regime=regime,
            )

        return SignalCandidate(
            symbol=context.get("symbol", ""),
            signal_type="NONE",
            strategy="Scalp (No Setup)",
            confidence=15,
            reason=f"Price not near S/R (dist_s={dist_to_support:.1f}%, dist_r={dist_to_resistance:.1f}%), RSI={rsi:.0f}",
            regime=regime,
        )

    def get_entry_price(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        return df["close"].iloc[-1]

    def get_stop_loss(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        atr = compute_atr(df).iloc[-1]
        current_price = df["close"].iloc[-1]
        if signal.signal_type == "LONG":
            return current_price - (atr * 2.5)
        return current_price + (atr * 2.5)

    def get_take_profit(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        entry = self.get_entry_price(df, signal)
        sl = self.get_stop_loss(df, signal)
        risk = abs(entry - sl)
        if signal.signal_type == "LONG":
            return entry + (risk * 2.0)
        return entry - (risk * 2.0)
