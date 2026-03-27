#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Liquidity Zones Detector - كاشف مناطق السيولة المتقدم
=====================================================

يكشف مناطق السيولة الرئيسية التي يستهدفها Smart Money:
- Swing Points (قمم وقيعان السوينغ)
- Equal Highs/Lows (المستويات المتساوية)
- Fibonacci Retracement Levels
- VWAP Deviation Zones

Phase 1 - Week 1-2 من خطة Precision Scalping v8.0
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class LiquidityZone:
    """فئة تمثل منطقة سيولة واحدة"""

    def __init__(
        self,
        price: float,
        zone_type: str,
        strength: float,
        timestamp: datetime,
        source: str,
    ):
        self.price = price
        self.zone_type = zone_type  # 'resistance', 'support', 'pivot'
        self.strength = strength  # 0-100 قوة المنطقة
        self.timestamp = timestamp
        self.source = source  # 'swing', 'equal', 'fibonacci', 'vwap'
        self.hits = 0  # عدد مرات اللمس
        self.last_test = None  # آخر اختبار للمستوى

    def test_zone(
        self, price: float, timestamp: datetime, tolerance: float = 0.002
    ):
        """اختبار ما إذا كان السعر يلمس المنطقة"""
        distance = abs(price - self.price) / self.price
        if distance <= tolerance:
            self.hits += 1
            self.last_test = timestamp
            return True
        return False

    def get_age_hours(self) -> float:
        """عمر المنطقة بالساعات"""
        return (datetime.now() - self.timestamp).total_seconds() / 3600

    def is_fresh(self, max_age_hours: int = 48) -> bool:
        """هل المنطقة جديدة (أقل من 48 ساعة)"""
        return self.get_age_hours() < max_age_hours

    def __repr__(self):
        return f"LiquidityZone({
            self.source}:{
            self.zone_type} @ {
            self.price:.6f}, strength={
                self.strength:.1f})"


class LiquidityZonesDetector:
    """كاشف مناطق السيولة المتقدم لاستراتيجية Smart Money"""

    def __init__(self):
        self.logger = logger

        # إعدادات كشف Swing Points
        self.swing_lookback = 10  # نافذة البحث عن القمم/القيعان
        self.swing_min_strength = 3  # الحد الأدنى لقوة السوينغ

        # إعدادات Equal Levels
        self.equal_tolerance = 0.003  # تسامح 0.3% للمستويات المتساوية
        self.equal_min_distance = 5  # الحد الأدنى للمسافة بين النقاط

        # إعدادات Fibonacci
        self.fib_levels = [
            0.236,
            0.382,
            0.5,
            0.618,
            0.786,
        ]  # مستويات فيبوناتشي
        self.fib_lookback = 50  # نافزة البحث عن القمم/القيعان للفيبوناتشي

        # إعدادات VWAP
        self.vwap_std_multipliers = [
            1.0,
            1.5,
            2.0,
            2.5,
        ]  # مضاعفات الانحراف المعياري

    def detect_all_zones(
        self, symbol: str, df_15m: pd.DataFrame, df_5m: pd.DataFrame
    ) -> Dict[str, List[LiquidityZone]]:
        """
        كشف جميع مناطق السيولة

        Args:
            symbol: رمز العملة
            df_15m: بيانات 15 دقيقة للتحليل الأساسي
            df_5m: بيانات 5 دقائق للدقة

        Returns:
            Dict مع جميع المناطق مصنفة حسب النوع
        """
        self.logger.info(f"🔍 كشف مناطق السيولة لـ {symbol}")

        zones = {
            "swing_zones": self.detect_swing_zones(df_15m),
            "equal_zones": self.detect_equal_levels(df_15m),
            "fibonacci_zones": self.detect_fibonacci_levels(df_15m),
            "vwap_zones": self.detect_vwap_zones(df_5m),
        }

        # دمج وتصنيف حسب القوة
        all_zones = []
        for zone_type, zone_list in zones.items():
            all_zones.extend(zone_list)

        # ترتيب حسب القوة
        all_zones.sort(key=lambda z: z.strength, reverse=True)

        zones["all_zones"] = all_zones
        zones["summary"] = self._create_zones_summary(zones)

        self.logger.info(f"✅ تم العثور على {len(all_zones)} منطقة سيولة")
        return zones

    def detect_swing_zones(self, df: pd.DataFrame) -> List[LiquidityZone]:
        """
        كشف مناطق سيولة Swing Points

        قمم وقيعان السوينغ هي نقاط تجميع أوامر الإيقاف
        """
        zones = []

        if len(df) < self.swing_lookback * 2:
            return zones

        try:
            for i in range(self.swing_lookback, len(df) - self.swing_lookback):
                # البحث عن قمة سوينغ
                high_window = df["high"].iloc[
                    i - self.swing_lookback: i + self.swing_lookback + 1
                ]
                if df["high"].iloc[i] == high_window.max():
                    # قمة سوينغ محتملة
                    strength = self._calculate_swing_strength(df, i, "high")
                    if strength >= self.swing_min_strength:
                        zone = LiquidityZone(
                            price=df["high"].iloc[i],
                            zone_type="resistance",
                            strength=strength * 15,  # تحويل لمقياس 0-100
                            timestamp=df.index[i],
                            source="swing",
                        )
                        zones.append(zone)

                # البحث عن قاع سوينغ
                low_window = df["low"].iloc[
                    i - self.swing_lookback: i + self.swing_lookback + 1
                ]
                if df["low"].iloc[i] == low_window.min():
                    # قاع سوينغ محتمل
                    strength = self._calculate_swing_strength(df, i, "low")
                    if strength >= self.swing_min_strength:
                        zone = LiquidityZone(
                            price=df["low"].iloc[i],
                            zone_type="support",
                            strength=strength * 15,  # تحويل لمقياس 0-100
                            timestamp=df.index[i],
                            source="swing",
                        )
                        zones.append(zone)

            self.logger.debug(f"🔍 Swing zones: {len(zones)} منطقة")
            return zones

        except Exception as e:
            self.logger.error(f"خطأ في كشف Swing zones: {e}")
            return []

    def detect_equal_levels(self, df: pd.DataFrame) -> List[LiquidityZone]:
        """
        كشف Equal Highs/Lows - المستويات المتساوية

        هذه المستويات تجمع سيولة كبيرة لأن المتداولين يضعون
        أوامر إيقاف عند نفس المستويات النفسية
        """
        zones = []

        try:
            # جمع جميع القمم والقيعان الهامة
            swing_highs = []
            swing_lows = []

            lookback = min(20, len(df) // 4)

            for i in range(lookback, len(df) - lookback):
                # قمم
                high_window = df["high"].iloc[i - lookback: i + lookback + 1]
                if df["high"].iloc[i] == high_window.max():
                    swing_highs.append(
                        {
                            "price": df["high"].iloc[i],
                            "timestamp": df.index[i],
                            "volume": df["volume"].iloc[i],
                        }
                    )

                # قيعان
                low_window = df["low"].iloc[i - lookback: i + lookback + 1]
                if df["low"].iloc[i] == low_window.min():
                    swing_lows.append(
                        {
                            "price": df["low"].iloc[i],
                            "timestamp": df.index[i],
                            "volume": df["volume"].iloc[i],
                        }
                    )

            # البحث عن المستويات المتساوية في القمم
            equal_highs = self._find_equal_levels(swing_highs, "resistance")
            zones.extend(equal_highs)

            # البحث عن المستويات المتساوية في القيعان
            equal_lows = self._find_equal_levels(swing_lows, "support")
            zones.extend(equal_lows)

            self.logger.debug(f"🔍 Equal levels: {len(zones)} منطقة")
            return zones

        except Exception as e:
            self.logger.error(f"خطأ في كشف Equal levels: {e}")
            return []

    def detect_fibonacci_levels(self, df: pd.DataFrame) -> List[LiquidityZone]:
        """
        كشف مستويات فيبوناتشي كمناطق سيولة

        المتداولون يستخدمون هذه المستويات بكثرة مما يخلق سيولة
        """
        zones = []

        if len(df) < self.fib_lookback:
            return zones

        try:
            # البحث عن آخر موجة هامة
            recent_data = df.tail(self.fib_lookback)

            # أعلى وأقل نقطة في النافزة
            swing_high = recent_data["high"].max()
            swing_low = recent_data["low"].min()

            high_idx = recent_data["high"].idxmax()
            low_idx = recent_data["low"].idxmin()

            # تحديد اتجاه الموجة
            if high_idx > low_idx:
                # موجة صاعدة: من القاع إلى القمة
                fib_range = swing_high - swing_low
                base_price = swing_low
                wave_direction = "upward"
            else:
                # موجة هابطة: من القمة إلى القاع
                fib_range = swing_high - swing_low
                base_price = swing_high
                wave_direction = "downward"

            # حساب مستويات فيبوناتشي
            for fib_level in self.fib_levels:
                if wave_direction == "upward":
                    fib_price = base_price + (fib_range * fib_level)
                    zone_type = "support" if fib_level < 0.5 else "resistance"
                else:
                    fib_price = base_price - (fib_range * fib_level)
                    zone_type = "resistance" if fib_level < 0.5 else "support"

                # قوة المستوى تعتمد على أهمية النسبة
                if fib_level in [0.382, 0.618]:
                    strength = 80  # المستويات الذهبية
                elif fib_level == 0.5:
                    strength = 75  # نصف المدى
                else:
                    strength = 60  # مستويات أخرى

                zone = LiquidityZone(
                    price=fib_price,
                    zone_type=zone_type,
                    strength=strength,
                    timestamp=max(high_idx, low_idx),
                    source="fibonacci",
                )
                zones.append(zone)

            self.logger.debug(f"🔍 Fibonacci zones: {len(zones)} منطقة")
            return zones

        except Exception as e:
            self.logger.error(f"خطأ في كشف Fibonacci levels: {e}")
            return []

    def detect_vwap_zones(self, df: pd.DataFrame) -> List[LiquidityZone]:
        """
        كشف مناطق انحراف VWAP كمناطق سيولة

        VWAP هو مركز السيولة اليومي، والانحرافات المعيارية
        تشكل مناطق دعم ومقاومة قوية
        """
        zones = []

        if len(df) < 50:
            return zones

        try:
            # حساب VWAP
            df = df.copy()
            df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
            df["volume_price"] = df["typical_price"] * df["volume"]

            # VWAP تراكمي
            df["cumulative_volume"] = df["volume"].cumsum()
            df["cumulative_volume_price"] = df["volume_price"].cumsum()
            df["vwap"] = (
                df["cumulative_volume_price"] / df["cumulative_volume"]
            )

            # حساب الانحراف المعياري
            df["price_variance"] = (
                df["typical_price"] - df["vwap"]
            ) ** 2 * df["volume"]
            df["cumulative_price_variance"] = df["price_variance"].cumsum()
            df["variance"] = (
                df["cumulative_price_variance"] / df["cumulative_volume"]
            )
            df["vwap_std"] = np.sqrt(df["variance"])

            # آخر قيم VWAP
            current_vwap = df["vwap"].iloc[-1]
            current_std = df["vwap_std"].iloc[-1]
            latest_timestamp = df.index[-1]

            # إنشاء مناطق الانحراف المعياري
            for multiplier in self.vwap_std_multipliers:
                # مستوى علوي
                upper_level = current_vwap + (current_std * multiplier)
                upper_zone = LiquidityZone(
                    price=upper_level,
                    zone_type="resistance",
                    # كلما زاد المضاعف قلت القوة
                    strength=70 - (multiplier * 10),
                    timestamp=latest_timestamp,
                    source="vwap",
                )
                zones.append(upper_zone)

                # مستوى سفلي
                lower_level = current_vwap - (current_std * multiplier)
                lower_zone = LiquidityZone(
                    price=lower_level,
                    zone_type="support",
                    strength=70 - (multiplier * 10),
                    timestamp=latest_timestamp,
                    source="vwap",
                )
                zones.append(lower_zone)

            # VWAP نفسه كمنطقة محورية
            vwap_zone = LiquidityZone(
                price=current_vwap,
                zone_type="pivot",
                strength=85,  # قوة عالية للـ VWAP
                timestamp=latest_timestamp,
                source="vwap",
            )
            zones.append(vwap_zone)

            self.logger.debug(f"🔍 VWAP zones: {len(zones)} منطقة")
            return zones

        except Exception as e:
            self.logger.error(f"خطأ في كشف VWAP zones: {e}")
            return []

    def _calculate_swing_strength(
        self, df: pd.DataFrame, index: int, swing_type: str
    ) -> float:
        """حساب قوة نقطة السوينغ"""
        try:
            if swing_type == "high":
                price = df["high"].iloc[index]
                # قوة بناءً على المسافة من الأسعار المجاورة
                left_prices = df["high"].iloc[max(0, index - 10): index]
                right_prices = df["high"].iloc[
                    index + 1: min(len(df), index + 11)
                ]
            else:
                price = df["low"].iloc[index]
                left_prices = df["low"].iloc[max(0, index - 10): index]
                right_prices = df["low"].iloc[
                    index + 1: min(len(df), index + 11)
                ]

            # حساب القوة بناءً على التفرد في المنطقة
            all_nearby = pd.concat([left_prices, right_prices])

            if swing_type == "high":
                strength = sum(price > p for p in all_nearby) / len(all_nearby)
            else:
                strength = sum(price < p for p in all_nearby) / len(all_nearby)

            # تعديل بناءً على الحجم
            volume_strength = (
                df["volume"].iloc[index]
                / df["volume"].iloc[max(0, index - 20): index + 20].mean()
            )

            return strength * 5 + min(volume_strength, 2)  # مقياس 0-7

        except Exception as e:
            self.logger.debug(f"خطأ في حساب قوة السوينغ: {e}")
            return 0

    def _find_equal_levels(
        self, swing_points: List[Dict], zone_type: str
    ) -> List[LiquidityZone]:
        """البحث عن المستويات المتساوية في مجموعة نقاط"""
        equal_zones = []

        if len(swing_points) < 2:
            return equal_zones

        # مجموعة النقاط حسب القرب من بعضها
        price_groups = []

        for point in swing_points:
            price = point["price"]
            added_to_group = False

            # البحث عن مجموعة مناسبة
            for group in price_groups:
                group_avg = sum(p["price"] for p in group) / len(group)
                if abs(price - group_avg) / group_avg <= self.equal_tolerance:
                    group.append(point)
                    added_to_group = True
                    break

            if not added_to_group:
                price_groups.append([point])

        # إنشاء مناطق للمجموعات التي تحتوي على نقطتين أو أكثر
        for group in price_groups:
            if len(group) >= 2:
                avg_price = sum(p["price"] for p in group) / len(group)
                total_volume = sum(p["volume"] for p in group)
                latest_timestamp = max(p["timestamp"] for p in group)

                # قوة المستوى تعتمد على عدد النقاط والحجم
                strength = min(
                    90,
                    50 + (len(group) * 10) + min(20, total_volume / 1000000),
                )

                zone = LiquidityZone(
                    price=avg_price,
                    zone_type=zone_type,
                    strength=strength,
                    timestamp=latest_timestamp,
                    source="equal",
                )
                equal_zones.append(zone)

        return equal_zones

    def _create_zones_summary(self, zones: Dict) -> Dict:
        """إنشاء ملخص لمناطق السيولة"""
        summary = {
            "total_zones": len(zones.get("all_zones", [])),
            "by_source": {},
            "by_type": {},
            "strongest_zones": [],
            "fresh_zones": [],
        }

        all_zones = zones.get("all_zones", [])

        # تصنيف حسب المصدر
        for zone in all_zones:
            source = zone.source
            if source not in summary["by_source"]:
                summary["by_source"][source] = 0
            summary["by_source"][source] += 1

        # تصنيف حسب النوع
        for zone in all_zones:
            zone_type = zone.zone_type
            if zone_type not in summary["by_type"]:
                summary["by_type"][zone_type] = 0
            summary["by_type"][zone_type] += 1

        # أقوى 5 مناطق
        summary["strongest_zones"] = sorted(
            all_zones, key=lambda z: z.strength, reverse=True
        )[:5]

        # المناطق الجديدة (أقل من 24 ساعة)
        summary["fresh_zones"] = [z for z in all_zones if z.is_fresh(24)]

        return summary

    def get_zones_near_price(
        self,
        zones: List[LiquidityZone],
        current_price: float,
        distance_pct: float = 2.0,
    ) -> List[LiquidityZone]:
        """الحصول على المناطق القريبة من السعر الحالي"""
        nearby_zones = []

        for zone in zones:
            distance = abs(zone.price - current_price) / current_price * 100
            if distance <= distance_pct:
                nearby_zones.append(zone)

        # ترتيب حسب القرب من السعر
        nearby_zones.sort(key=lambda z: abs(z.price - current_price))
        return nearby_zones
