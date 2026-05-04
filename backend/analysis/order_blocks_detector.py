"""
Order Blocks Detector - Smart Money Phase 1
Detects institutional order blocks from price and volume patterns.
"""

import pandas as pd
import numpy as np
import logging
from typing import List
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderBlock:
    """Institutional order block zone"""

    def __init__(self, block_type, top_price, bottom_price, strength, block_source, volume_ratio, detected_at):
        self.block_type = block_type
        self.top_price = top_price
        self.bottom_price = bottom_price
        self.strength = strength
        self.block_source = block_source
        self.volume_ratio = volume_ratio
        self.detected_at = detected_at

    @property
    def price(self):
        return (self.top_price + self.bottom_price) / 2

    def get_midpoint(self):
        return self.price

    def __repr__(self):
        return f"OrderBlock({self.block_type} str={self.strength:.0f} src={self.block_source})"


class OrderBlocksDetector:
    """Detects institutional order blocks"""

    def __init__(self):
        self.logger = logger
        self.min_volume_ratio = 1.3
        self.min_body_ratio = 0.4

    def detect_order_blocks(self, df_15m):
        blocks = []
        try:
            if df_15m is None or len(df_15m) < 30:
                return blocks

            impulse = self._detect_impulse(df_15m)
            blocks.extend(impulse)

            reversal = self._detect_reversal(df_15m)
            blocks.extend(reversal)

            consolidation = self._detect_consolidation(df_15m)
            blocks.extend(consolidation)

            blocks.sort(key=lambda b: b.strength, reverse=True)
            return blocks[:15]
        except Exception as e:
            self.logger.error(f"OrderBlock detection error: {e}")
            return blocks

    def _detect_impulse(self, df):
        blocks = []
        if len(df) < 30:
            return blocks
        avg_vol = float(df["volume"].iloc[-30:].mean())
        if avg_vol <= 0:
            return blocks

        for i in range(5, len(df) - 5):
            try:
                c = df.iloc[i]
                nxt = df.iloc[i + 1]
                vol = float(c["volume"])
                body = abs(float(c["close"]) - float(c["open"]))
                rng = float(c["high"]) - float(c["low"])
                if rng <= 0:
                    continue
                vr = vol / avg_vol
                br = body / rng

                # Bullish impulse: big green candle followed by red candle
                if float(c["close"]) > float(c["open"]) and float(nxt["close"]) < float(nxt["open"]) and vr > self.min_volume_ratio:
                    strength = min(100, 50 + vr * 20 + br * 30)
                    blocks.append(OrderBlock("bullish", float(c["high"]), float(c["low"]), strength, "impulse", round(vr, 2), self._now(df, i)))

                # Bearish impulse: big red candle followed by green candle
                if float(c["close"]) < float(c["open"]) and float(nxt["close"]) > float(nxt["open"]) and vr > self.min_volume_ratio:
                    strength = min(100, 50 + vr * 20 + br * 30)
                    blocks.append(OrderBlock("bearish", float(c["high"]), float(c["low"]), strength, "impulse", round(vr, 2), self._now(df, i)))
            except (IndexError, KeyError, ValueError, TypeError):
                continue
        return blocks

    def _detect_reversal(self, df):
        blocks = []
        if len(df) < 20:
            return blocks
        avg_vol = float(df["volume"].iloc[-20:].mean())
        if avg_vol <= 0:
            return blocks

        for i in range(10, len(df) - 3):
            try:
                c = df.iloc[i]
                vol = float(c["volume"])
                rng = float(c["high"]) - float(c["low"])
                if rng <= 0:
                    continue
                vr = vol / avg_vol
                body = abs(float(c["close"]) - float(c["open"]))
                br = body / rng

                # Look for exhaustion + reversal pattern
                prev3 = df.iloc[i - 3 : i]
                if len(prev3) < 3:
                    continue

                # Bullish reversal: 3+ red candles then strong green
                red_count = sum(1 for j in range(len(prev3)) if float(prev3.iloc[j]["close"]) < float(prev3.iloc[j]["open"]))
                if red_count >= 2 and float(c["close"]) > float(c["open"]) and vr > 1.5 and br > self.min_body_ratio:
                    strength = min(100, 60 + vr * 15 + br * 25)
                    blocks.append(OrderBlock("bullish", float(c["high"]), float(c["low"]), strength, "reversal", round(vr, 2), self._now(df, i)))

                # Bearish reversal: 3+ green candles then strong red
                green_count = sum(1 for j in range(len(prev3)) if float(prev3.iloc[j]["close"]) > float(prev3.iloc[j]["open"]))
                if green_count >= 2 and float(c["close"]) < float(c["open"]) and vr > 1.5 and br > self.min_body_ratio:
                    strength = min(100, 60 + vr * 15 + br * 25)
                    blocks.append(OrderBlock("bearish", float(c["high"]), float(c["low"]), strength, "reversal", round(vr, 2), self._now(df, i)))
            except (IndexError, KeyError, ValueError, TypeError):
                continue
        return blocks

    def _detect_consolidation(self, df):
        blocks = []
        if len(df) < 30:
            return blocks
        avg_vol = float(df["volume"].iloc[-20:].mean())
        if avg_vol <= 0:
            return blocks

        for i in range(15, len(df) - 5):
            try:
                window = df.iloc[i - 10 : i]
                if len(window) < 10:
                    continue
                highs = window["high"].values.astype(float)
                lows = window["low"].values.astype(float)
                range_total = highs.max() - lows.min()
                avg_range = (highs - lows).mean()
                if avg_range <= 0:
                    continue
                is_tight = range_total / avg_range < 1.5 if avg_range > 0 else False

                c = df.iloc[i]
                vol = float(c["volume"])
                vr = vol / avg_vol

                if is_tight and vr > self.min_volume_ratio:
                    if float(c["close"]) > float(c["open"]):
                        blocks.append(OrderBlock("bullish", float(highs.max()), float(lows.min()), 65, "consolidation", round(vr, 2), self._now(df, i)))
                    else:
                        blocks.append(OrderBlock("bearish", float(highs.max()), float(lows.min()), 65, "consolidation", round(vr, 2), self._now(df, i)))
            except (IndexError, KeyError, ValueError, TypeError):
                continue
        return blocks

    def _now(self, df, idx):
        try:
            return df.index[idx].to_pydatetime()
        except Exception:
            return datetime.now()
