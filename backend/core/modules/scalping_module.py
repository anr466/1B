#!/usr/bin/env python3
"""
Scalping Module
Handles quick scalping strategies for choppy/ranging markets.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from backend.core.strategy_interface import StrategyModule
from backend.utils.indicator_calculator import compute_atr, compute_rsi


class ScalpingModule(StrategyModule):
    def name(self) -> str:
        return "ScalpingModule"

    def supported_regimes(self) -> List[str]:
        return ["CHOPPY", "NARROW_RANGE"]

    def evaluate(self, df: pd.DataFrame, context: Dict) -> Optional[Dict]:
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]
        current_price = close.iloc[-1]
        regime = context.get("regime", "CHOPPY")

        if regime not in self.supported_regimes():
            return None

        # FIX: Use unified RSI
        rsi = compute_rsi(df).iloc[-1]
        support = low.tail(20).quantile(0.15)
        resistance = high.tail(20).quantile(0.85)
        range_w = (resistance - support) / support * 100 if support > 0 else 0

        if range_w < 0.3:
            return None

        # Volume confirmation — relaxed threshold
        vol_avg = volume.tail(20).mean()
        vol_ratio = volume.iloc[-1] / vol_avg if vol_avg > 0 else 1.0
        if vol_ratio < 0.6:  # Relaxed from 0.8
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
                "confidence": 60,  # Raised from 55
                "reason": f"Price near support ({dist_to_support:.1f}%), RSI={rsi:.0f}, Vol={vol_ratio:.1f}x",
            }

        if dist_to_resistance <= 1.5 and rsi > 55:
            return {
                "type": "SHORT",
                "strategy": "Micro Scalp Resistance",
                "confidence": 60,  # Raised from 55
                "reason": f"Price near resistance ({dist_to_resistance:.1f}%), RSI={rsi:.0f}, Vol={vol_ratio:.1f}x",
            }

        return None

    def get_entry_price(self, df: pd.DataFrame, signal: Dict) -> float:
        return df["close"].iloc[-1]

    def get_stop_loss(self, df: pd.DataFrame, signal: Dict) -> float:
        atr = compute_atr(df).iloc[-1]
        current_price = df["close"].iloc[-1]
        if signal["type"] == "LONG":
            return current_price - (atr * 2.5)
        return current_price + (atr * 2.5)

    def get_take_profit(self, df: pd.DataFrame, signal: Dict) -> float:
        entry = self.get_entry_price(df, signal)
        sl = self.get_stop_loss(df, signal)
        risk = abs(entry - sl)
        # FIX: Unify minimum RR to 2.0:1 across all modules (was 1.5:1)
        if signal["type"] == "LONG":
            return entry + (risk * 2.0)
        return entry - (risk * 2.0)
