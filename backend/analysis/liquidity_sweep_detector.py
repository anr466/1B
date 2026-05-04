"""
Liquidity Sweep Detector — كاشف كنس السيولة والفخاخ
=====================================================
يكتشف عمليات كنس السيولة (Stop Hunts) التي تستخدمها المؤسسات
لجمع السيولة قبل الحركة الحقيقية للسعر.

متوافق مع Smart Money Orchestrator
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class LiquiditySweep:
    """عملية كنس سيولة — Stop Hunt"""

    def __init__(
        self,
        sweep_type: str,
        price: float,
        strength: float,
        volume_multiplier: float,
        detected_at: datetime,
        zone_price: float = None,
    ):
        self.sweep_type = sweep_type      # 'bullish_sweep' or 'bearish_sweep'
        self.price = price
        self.strength = strength          # 0-100
        self.volume_multiplier = volume_multiplier
        self.detected_at = detected_at
        self.zone_price = zone_price

    def get_age_hours(self) -> float:
        """عمر عملية الكنس بالساعات"""
        if self.detected_at is None:
            return 999
        delta = datetime.now() - self.detected_at
        if hasattr(delta, 'total_seconds'):
            return delta.total_seconds() / 3600.0
        return 0

    def __repr__(self):
        return f"LiquiditySweep({self.sweep_type}@{self.price:.6f} str={self.strength:.0f} age={self.get_age_hours():.1f}h)"


class LiquiditySweepDetector:
    """كاشف عمليات كنس السيولة"""

    def __init__(self):
        self.logger = logger
        self.wick_threshold = 0.003   # 0.3% wick
        self.recovery_threshold = 0.5  # 50% recovery
        self.volume_spike = 1.5       # 1.5x volume

    def detect_liquidity_sweeps(
        self, df_5m: pd.DataFrame, liquidity_zones: List
    ) -> List[LiquiditySweep]:
        """كشف جميع عمليات كنس السيولة في البيانات"""
        sweeps = []

        try:
            if df_5m is None or len(df_5m) < 10:
                return sweeps

            # 1. Detect wick-based sweeps
            wick_sweeps = self._detect_wick_sweeps(df_5m)
            sweeps.extend(wick_sweeps)

            # 2. Detect zone-based sweeps (price briefly breaks then reverses)
            if liquidity_zones:
                zone_sweeps = self._detect_zone_sweeps(df_5m, liquidity_zones)
                sweeps.extend(zone_sweeps)

            # 3. Detect volume-based sweeps
            vol_sweeps = self._detect_volume_sweeps(df_5m)
            sweeps.extend(vol_sweeps)

            # Sort by recency
            sweeps.sort(key=lambda s: s.detected_at, reverse=True)

            return sweeps

        except Exception as e:
            self.logger.error(f"Error detecting liquidity sweeps: {e}")
            return sweeps

    def _detect_wick_sweeps(self, df: pd.DataFrame) -> List[LiquiditySweep]:
        """كشف عمليات الكنس عبر الظلال الطويلة"""
        sweeps = []

        for i in range(5, len(df)):
            try:
                candle = df.iloc[i]
                body = abs(float(candle["close"]) - float(candle["open"]))
                high = float(candle["high"])
                low = float(candle["low"])
                close = float(candle["close"])
                open_price = float(candle["open"])
                volume = float(candle["volume"])
                price_range = high - low

                if price_range <= 0:
                    continue

                upper_wick = high - max(close, open_price)
                lower_wick = min(close, open_price) - low
                avg_volume = float(df["volume"].iloc[max(0, i-20):i].mean())

                # Bullish sweep: long lower wick, closes high
                if (
                    lower_wick > price_range * 0.5
                    and lower_wick / price_range > self.wick_threshold * 10
                    and close > open_price
                ):
                    vol_ratio = volume / avg_volume if avg_volume > 0 else 1
                    strength = min(100, 40 + vol_ratio * 25 + (lower_wick / price_range) * 35)
                    sweeps.append(
                        LiquiditySweep(
                            sweep_type="bullish_sweep",
                            price=low,
                            strength=strength,
                            volume_multiplier=round(vol_ratio, 2),
                            detected_at=df.index[i].to_pydatetime() if hasattr(df.index[i], 'to_pydatetime') else datetime.now(),
                            zone_price=None,
                        )
                    )

                # Bearish sweep: long upper wick, closes low
                if (
                    upper_wick > price_range * 0.5
                    and upper_wick / price_range > self.wick_threshold * 10
                    and close < open_price
                ):
                    vol_ratio = volume / avg_volume if avg_volume > 0 else 1
                    strength = min(100, 40 + vol_ratio * 25 + (upper_wick / price_range) * 35)
                    sweeps.append(
                        LiquiditySweep(
                            sweep_type="bearish_sweep",
                            price=high,
                            strength=strength,
                            volume_multiplier=round(vol_ratio, 2),
                            detected_at=df.index[i].to_pydatetime() if hasattr(df.index[i], 'to_pydatetime') else datetime.now(),
                            zone_price=None,
                        )
                    )
            except (IndexError, KeyError, ValueError, TypeError):
                continue

        return sweeps

    def _detect_zone_sweeps(
        self, df: pd.DataFrame, liquidity_zones: List
    ) -> List[LiquiditySweep]:
        """كشف عمليات الكنس عند مناطق السيولة المحددة"""
        sweeps = []
        lookback = min(10, len(df) - 1)

        for zone in liquidity_zones:
            try:
                zone_price = float(zone.price)
                zone_type = getattr(zone, "zone_type", "")
                zone_strength = getattr(zone, "strength", 50)

                # Check recent candles for price sweeping the zone
                for i in range(len(df) - lookback, len(df)):
                    if i < 0:
                        continue
                    try:
                        candle = df.iloc[i]
                        high = float(candle["high"])
                        low = float(candle["low"])
                        close = float(candle["close"])

                        # Support zone sweep: price briefly breaks below then closes above
                        if zone_type == "support":
                            if low < zone_price * (1 - 0.002) and close > zone_price:
                                strength = zone_strength + 20
                                sweeps.append(
                                    LiquiditySweep(
                                        sweep_type="bullish_sweep",
                                        price=float(low),
                                        strength=min(100, strength),
                                        volume_multiplier=1.5,
                                        detected_at=df.index[i].to_pydatetime() if hasattr(df.index[i], 'to_pydatetime') else datetime.now(),
                                        zone_price=zone_price,
                                    )
                                )

                        # Resistance zone sweep: price briefly breaks above then closes below
                        elif zone_type == "resistance":
                            if high > zone_price * (1 + 0.002) and close < zone_price:
                                strength = zone_strength + 20
                                sweeps.append(
                                    LiquiditySweep(
                                        sweep_type="bearish_sweep",
                                        price=float(high),
                                        strength=min(100, strength),
                                        volume_multiplier=1.5,
                                        detected_at=df.index[i].to_pydatetime() if hasattr(df.index[i], 'to_pydatetime') else datetime.now(),
                                        zone_price=zone_price,
                                    )
                                )
                    except (IndexError, KeyError, ValueError, TypeError):
                        continue

            except (AttributeError, TypeError, ValueError):
                continue

        return sweeps

    def _detect_volume_sweeps(self, df: pd.DataFrame) -> List[LiquiditySweep]:
        """كشف عمليات الكنس عبر حجم التداول غير الطبيعي"""
        sweeps = []

        if len(df) < 20:
            return sweeps

        avg_volume = float(df["volume"].iloc[-20:].mean())
        if avg_volume <= 0:
            return sweeps

        # Check last 5 candles for volume spikes
        for i in range(max(len(df) - 5, 0), len(df)):
            try:
                candle = df.iloc[i]
                volume = float(candle["volume"])
                vol_ratio = volume / avg_volume
                close = float(candle["close"])
                open_price = float(candle["open"])

                if vol_ratio > self.volume_spike:
                    direction = "bullish" if close > open_price else "bearish"
                    strength = min(100, 30 + vol_ratio * 20)
                    sweeps.append(
                        LiquiditySweep(
                            sweep_type=f"{direction}_sweep",
                            price=close,
                            strength=strength,
                            volume_multiplier=round(vol_ratio, 2),
                            detected_at=df.index[i].to_pydatetime() if hasattr(df.index[i], 'to_pydatetime') else datetime.now(),
                            zone_price=None,
                        )
                    )
            except (IndexError, KeyError, ValueError, TypeError):
                continue

        return sweeps
