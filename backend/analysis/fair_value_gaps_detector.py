"""
Fair Value Gaps Detector - Smart Money Phase 1
Detects FVGs (imbalance zones) from 3-candle patterns.
"""

import pandas as pd
import numpy as np
import logging
from typing import List
from datetime import datetime

logger = logging.getLogger(__name__)


class FairValueGap:
    """Price imbalance zone (Fair Value Gap)"""

    def __init__(self, gap_type, top_price, bottom_price, strength, status, detected_at):
        self.gap_type = gap_type
        self.top_price = top_price
        self.bottom_price = bottom_price
        self.strength = strength
        self.status = status
        self.detected_at = detected_at

    def get_midpoint(self):
        return (self.top_price + self.bottom_price) / 2

    @property
    def price(self):
        return self.get_midpoint()

    def __repr__(self):
        return f"FairValueGap({self.gap_type} [{self.bottom_price:.6f}-{self.top_price:.6f}] str={self.strength:.0f} {self.status})"


class FairValueGapsDetector:
    """Detects Fair Value Gaps from price action"""

    def __init__(self):
        self.logger = logger
        self.min_gap_pct = 0.0005  # 0.05% minimum gap
        self.fill_tolerance = 0.3  # 30% overlap = filled

    def detect_fair_value_gaps(self, df_5m):
        gaps = []
        try:
            if df_5m is None or len(df_5m) < 10:
                return gaps

            # Detect from 3-candle patterns
            for i in range(2, len(df_5m)):
                try:
                    c0 = df_5m.iloc[i - 2]
                    c1 = df_5m.iloc[i - 1]
                    c2 = df_5m.iloc[i]

                    h0, l0 = float(c0["high"]), float(c0["low"])
                    h1, l1 = float(c1["high"]), float(c1["low"])
                    h2, l2 = float(c2["high"]), float(c2["low"])
                    vol = float(c2["volume"])
                    avg_vol = float(df_5m["volume"].iloc[max(0, i-20):i].mean()) if i >= 20 else vol

                    # Bullish FVG: candle 2 high < candle 0 low (gap up)
                    if l0 > h2 and (l0 - h2) / l0 > self.min_gap_pct:
                        vol_ratio = vol / avg_vol if avg_vol > 0 else 1
                        strength = min(100, 40 + (l0 - h2) / l0 * 500 + vol_ratio * 15)
                        gap = FairValueGap("bullish", l0, h2, strength, "unfilled", self._now(df_5m, i))
                        gaps.append(gap)

                    # Bearish FVG: candle 2 low > candle 0 high (gap down)
                    if h2 > h0 and (h2 - h0) / h0 > self.min_gap_pct:
                        vol_ratio = vol / avg_vol if avg_vol > 0 else 1
                        strength = min(100, 40 + (h2 - h0) / h0 * 500 + vol_ratio * 15)
                        gap = FairValueGap("bearish", h2, h0, strength, "unfilled", self._now(df_5m, i))
                        gaps.append(gap)
                except (IndexError, KeyError, ValueError, TypeError):
                    continue

            # Check which gaps have been filled
            current_price = float(df_5m["close"].iloc[-1]) if len(df_5m) > 0 else 0
            for gap in gaps:
                mid = gap.get_midpoint()
                if mid > 0:
                    if abs(current_price - mid) / mid < self.fill_tolerance * 0.01:
                        gap.status = "filled"
                        gap.strength = max(10, gap.strength * 0.3)

            # Sort by strength
            gaps.sort(key=lambda g: g.strength, reverse=True)
            return gaps[:10]

        except Exception as e:
            self.logger.error(f"FVG detection error: {e}")
            return gaps

    def _now(self, df, idx):
        try:
            return df.index[idx].to_pydatetime()
        except Exception:
            return datetime.now()
