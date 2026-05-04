#!/usr/bin/env python3
"""
Trend Module — Updated for Continuous Signal Stream
Handles trend-following strategies for both Long and Short positions.
Always returns SignalCandidate (never None).
"""

import pandas as pd
from typing import Dict, List
from backend.core.strategy_interface import StrategyModule
from backend.core.signal_candidate import SignalCandidate
from backend.utils.indicator_calculator import compute_atr


class TrendModule(StrategyModule):
    def name(self) -> str:
        return "TrendModule"

    def supported_regimes(self) -> List[str]:
        return ["STRONG_TREND", "WEAK_TREND"]

    def evaluate(self, df: pd.DataFrame, context: Dict) -> SignalCandidate:
        close = df["close"]
        ema21 = close.ewm(span=21, adjust=False).mean()
        ema55 = close.ewm(span=55, adjust=False).mean()
        current_price = close.iloc[-1]
        trend = context.get("trend", "NEUTRAL")
        regime = context.get("regime", "CHOPPY")
        regime_scores = context.get("regime_scores", {})
        trend_score = regime_scores.get("STRONG_TREND", 0) + regime_scores.get("WEAK_TREND", 0)

        if regime not in self.supported_regimes():
            return SignalCandidate.no_signal(
                reason=f"Regime {regime} not supported by TrendModule",
                regime=regime,
            )

        if trend == "UP":
            if current_price > ema21.iloc[-1] and ema21.iloc[-1] > ema55.iloc[-1]:
                dist_to_ema21 = (current_price - ema21.iloc[-1]) / ema21.iloc[-1]
                if -0.015 <= dist_to_ema21 <= 0.03:
                    confidence = min(80 + (trend_score - 50) * 0.4, 95)
                    return SignalCandidate(
                        symbol=context.get("symbol", ""),
                        signal_type="LONG",
                        strategy="Trend Pullback",
                        confidence=confidence,
                        reason=f"Strong uptrend, price pulling back to EMA21 ({dist_to_ema21 * 100:.1f}%), TrendScore={trend_score:.0f}",
                        regime=regime,
                    )
                elif current_price > df["high"].tail(20).quantile(0.85):
                    confidence = min(70 + (trend_score - 50) * 0.3, 85)
                    return SignalCandidate(
                        symbol=context.get("symbol", ""),
                        signal_type="LONG",
                        strategy="Trend Breakout",
                        confidence=confidence,
                        reason=f"Breakout above 20-period high in uptrend, TrendScore={trend_score:.0f}",
                        regime=regime,
                    )
            return SignalCandidate(
                symbol=context.get("symbol", ""),
                signal_type="LONG",
                strategy="Trend Pullback (Weak)",
                confidence=20,
                reason="Uptrend present but setup not optimal",
                regime=regime,
            )

        elif trend == "DOWN":
            if current_price < ema21.iloc[-1] and ema21.iloc[-1] < ema55.iloc[-1]:
                dist_to_ema21 = (ema21.iloc[-1] - current_price) / ema21.iloc[-1]
                if -0.015 <= dist_to_ema21 <= 0.03:
                    confidence = min(80 + (trend_score - 50) * 0.4, 95)
                    return SignalCandidate(
                        symbol=context.get("symbol", ""),
                        signal_type="SHORT",
                        strategy="Trend Pullback Short",
                        confidence=confidence,
                        reason=f"Strong downtrend, price pulling back to EMA21 ({dist_to_ema21 * 100:.1f}%), TrendScore={trend_score:.0f}",
                        regime=regime,
                    )
                elif current_price < df["low"].tail(20).quantile(0.15):
                    confidence = min(70 + (trend_score - 50) * 0.3, 85)
                    return SignalCandidate(
                        symbol=context.get("symbol", ""),
                        signal_type="SHORT",
                        strategy="Trend Breakdown",
                        confidence=confidence,
                        reason=f"Breakdown below 20-period low in downtrend, TrendScore={trend_score:.0f}",
                        regime=regime,
                    )
            return SignalCandidate(
                symbol=context.get("symbol", ""),
                signal_type="SHORT",
                strategy="Trend Pullback Short (Weak)",
                confidence=20,
                reason="Downtrend present but setup not optimal",
                regime=regime,
            )

        return SignalCandidate.no_signal(
            reason=f"Trend is {trend}, not suitable for trend strategies",
            regime=regime,
        )

    def get_entry_price(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        return df["close"].iloc[-1]

    def get_stop_loss(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        atr = compute_atr(df).iloc[-1]
        current_price = df["close"].iloc[-1]
        if signal.signal_type == "LONG":
            return current_price - (atr * 3.5)
        return current_price + (atr * 3.5)

    def get_take_profit(self, df: pd.DataFrame, signal: SignalCandidate) -> float:
        entry = self.get_entry_price(df, signal)
        sl = self.get_stop_loss(df, signal)
        risk = abs(entry - sl)
        if signal.signal_type == "LONG":
            return entry + (risk * 2.0)
        return entry - (risk * 2.0)
