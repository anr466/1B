"""
Liquidity Zones Detector — كاشف مناطق السيولة
===============================================
يكتشف مناطق الدعم والمقاومة عالية السيولة باستخدام:
- Swing High/Low (القمم والقيعان المتأرجحة)
- Equal High/Low (القمم والقيعان المتساوية)
- Fibonacci Retracement (تصحيحات فيبوناتشي)

متوافق مع Smart Money Orchestrator — Phase 1 Week 1-2
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class LiquidityZone:
    """منطقة سيولة — دعم أو مقاومة"""

    def __init__(
        self,
        price: float,
        zone_type: str,
        strength: float,
        source: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ):
        self.price = price
        self.zone_type = zone_type  # 'support' or 'resistance'
        self.strength = strength    # 0-100
        self.source = source        # 'swing', 'equal', 'fibonacci'
        self.start = start
        self.end = end

    def __repr__(self):
        return f"LiquidityZone({self.zone_type}@{self.price:.6f} str={self.strength:.0f} src={self.source})"


class LiquidityZonesDetector:
    """كاشف مناطق السيولة — المحرك الأساسي"""

    def __init__(self):
        self.logger = logger
        self.swing_lookback = 10
        self.equal_tolerance = 0.001  # 0.1% tolerance
        self.fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]

    def detect_all_zones(
        self, symbol: str, df_15m: pd.DataFrame, df_5m: pd.DataFrame
    ) -> Dict:
        """جمع كل مناطق السيولة من جميع المصادر"""
        try:
            if df_15m is None or len(df_15m) < 30:
                return {"all_zones": [], "symbol": symbol, "error": "Insufficient data"}

            all_zones = []

            # 1. Swing High/Low zones
            swing_zones = self._detect_swing_zones(df_15m)
            all_zones.extend(swing_zones)

            # 2. Equal High/Low zones
            equal_zones = self._detect_equal_zones(df_15m)
            all_zones.extend(equal_zones)

            # 3. Fibonacci zones
            fib_zones = self._detect_fibonacci_zones(df_15m)
            all_zones.extend(fib_zones)

            # Deduplicate — merge zones very close to each other
            merged = self._merge_nearby_zones(all_zones)

            self.logger.debug(
                f"🔍 Liquidity Zones for {symbol}: {len(all_zones)} raw → {len(merged)} merged"
            )

            return {
                "symbol": symbol,
                "all_zones": merged,
                "raw_count": len(all_zones),
                "merged_count": len(merged),
                "sources": {
                    "swing": len(swing_zones),
                    "equal": len(equal_zones),
                    "fibonacci": len(fib_zones),
                },
            }

        except Exception as e:
            self.logger.error(f"Error detecting liquidity zones: {e}")
            return {"all_zones": [], "symbol": symbol, "error": str(e)}

    def _detect_swing_zones(self, df: pd.DataFrame) -> List[LiquidityZone]:
        """كشف مناطق السيولة من القمم والقيعان المتأرجحة"""
        zones = []
        lookback = self.swing_lookback

        if len(df) < lookback * 2:
            return zones

        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values

        for i in range(lookback, len(df) - lookback):
            # Swing High
            if all(high[i] >= high[j] for j in range(i - lookback, i + lookback + 1)):
                count = sum(
                    1
                    for j in range(i - lookback, i + lookback + 1)
                    if j != i and abs(high[i] - high[j]) / high[i] < self.equal_tolerance
                )
                strength = min(100, 40 + count * 15 + (volume[i] / volume[i-lookback:i].mean() * 20))
                zones.append(
                    LiquidityZone(
                        price=float(high[i]),
                        zone_type="resistance",
                        strength=strength,
                        source="swing",
                    )
                )

            # Swing Low
            if all(low[i] <= low[j] for j in range(i - lookback, i + lookback + 1)):
                count = sum(
                    1
                    for j in range(i - lookback, i + lookback + 1)
                    if j != i and abs(low[i] - low[j]) / low[i] < self.equal_tolerance
                )
                strength = min(100, 40 + count * 15 + (volume[i] / volume[i-lookback:i].mean() * 20))
                zones.append(
                    LiquidityZone(
                        price=float(low[i]),
                        zone_type="support",
                        strength=strength,
                        source="swing",
                    )
                )

        return zones

    def _detect_equal_zones(self, df: pd.DataFrame) -> List[LiquidityZone]:
        """كشف مناطق السيولة من القمم والقيعان المتساوية"""
        zones = []
        lookback = self.swing_lookback

        if len(df) < lookback * 3:
            return zones

        close = df["close"].values
        high = df["high"].values
        low = df["low"].values

        for i in range(lookback, len(df) - lookback):
            # Equal Highs
            equal_highs = []
            for j in range(max(0, i - lookback * 2), i):
                if abs(high[i] - high[j]) / high[i] < self.equal_tolerance:
                    equal_highs.append(j)

            if len(equal_highs) >= 1:
                strength = min(100, 30 + len(equal_highs) * 20)
                zones.append(
                    LiquidityZone(
                        price=float(high[i]),
                        zone_type="resistance",
                        strength=strength,
                        source="equal",
                    )
                )

            # Equal Lows
            equal_lows = []
            for j in range(max(0, i - lookback * 2), i):
                if abs(low[i] - low[j]) / low[i] < self.equal_tolerance:
                    equal_lows.append(j)

            if len(equal_lows) >= 1:
                strength = min(100, 30 + len(equal_lows) * 20)
                zones.append(
                    LiquidityZone(
                        price=float(low[i]),
                        zone_type="support",
                        strength=strength,
                        source="equal",
                    )
                )

        return zones

    def _detect_fibonacci_zones(self, df: pd.DataFrame) -> List[LiquidityZone]:
        """كشف مناطق السيولة من تصحيحات فيبوناتشي"""
        zones = []
        lookback = self.swing_lookback

        if len(df) < lookback * 2:
            return zones

        high = df["high"].values
        low = df["low"].values
        close = df["close"].values

        # Find major swing high and low in recent window
        window = min(50, len(df))
        recent_high = high[-window:].max()
        recent_low = low[-window:].min()
        price_range = recent_high - recent_low

        if price_range <= 0:
            return zones

        # Determine direction
        is_uptrend = close[-1] > close[-20:].mean()

        if is_uptrend:
            # Uptrend fibs from swing low
            base = recent_low
            for level in self.fib_levels:
                fib_price = base + price_range * level
                direction = "support" if level <= 0.5 else "resistance"
                strength = 60 + (1.0 - abs(level - 0.618)) * 40
                zones.append(
                    LiquidityZone(
                        price=float(fib_price),
                        zone_type=direction,
                        strength=min(100, strength),
                        source="fibonacci",
                    )
                )
        else:
            # Downtrend fibs from swing high
            base = recent_high
            for level in self.fib_levels:
                fib_price = base - price_range * level
                direction = "resistance" if level <= 0.5 else "support"
                strength = 60 + (1.0 - abs(level - 0.618)) * 40
                zones.append(
                    LiquidityZone(
                        price=float(fib_price),
                        zone_type=direction,
                        strength=min(100, strength),
                        source="fibonacci",
                    )
                )

        return zones

    def _merge_nearby_zones(self, zones: List[LiquidityZone]) -> List[LiquidityZone]:
        """دمج المناطق المتقاربة جداً"""
        if not zones:
            return []

        # Aggregate by price proximity
        merged = []
        used = set()

        for i, z1 in enumerate(zones):
            if i in used:
                continue

            cluster = [z1]
            used.add(i)

            for j, z2 in enumerate(zones):
                if j in used:
                    continue
                if z1.zone_type == z2.zone_type:
                    if abs(z1.price - z2.price) / z1.price < self.equal_tolerance * 2:
                        cluster.append(z2)
                        used.add(j)

            # Merge cluster: weighted average price, max strength, combined sources
            if len(cluster) > 1:
                avg_price = sum(z.price for z in cluster) / len(cluster)
                max_strength = max(z.strength for z in cluster) + min(10, len(cluster) * 3)
                sources = list(set(z.source for z in cluster))
                merged.append(
                    LiquidityZone(
                        price=avg_price,
                        zone_type=z1.zone_type,
                        strength=min(100, max_strength),
                        source="+".join(sources),
                    )
                )
            else:
                merged.append(z1)

        # Sort by strength descending
        merged.sort(key=lambda z: z.strength, reverse=True)
        return merged[:20]  # Keep top 20 zones
