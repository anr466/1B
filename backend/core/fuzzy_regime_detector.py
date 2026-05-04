#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fuzzy Regime Detector — نظام اكتشاف الأنظمة بالنقاط المرجحة
===========================================================
بدلاً من المنطق الثنائي (if ADX > 30 → STRONG_TREND)،
يحسب هذا المكون درجات لكل نظام (Trend, Range, Choppy) بناءً على
عوامل متعددة، مما يسمح بفهم دقيق لحالة السوق.

المخرجات: dict يحتوي على درجات 0-100 لكل نظام + النظام الغالب.
"""

import pandas as pd
import numpy as np
from typing import Dict
from backend.utils.indicator_calculator import (
    compute_adx,
    compute_atr,
    compute_ema,
    compute_bollinger_bands,
    compute_rsi,
)


class FuzzyRegimeDetector:
    """
    يكتشف نظام السوق باستخدام درجات مرجحة بدلاً من العتبات الحادة.
    الأنظمة المدعومة: STRONG_TREND, WEAK_TREND, WIDE_RANGE, NARROW_RANGE, CHOPPY
    """

    def detect(self, df: pd.DataFrame) -> Dict:
        """
        يحسب درجات كل نظام ويعيد قاموس بالنتائج.

        Returns:
            {
                "dominant_regime": "STRONG_TREND",
                "trend_score": 85.0,
                "range_score": 15.0,
                "choppy_score": 5.0,
                "confidence": 0.85,  # قوة النظام الغالب
                "adx": 35.2,
                "bb_width": 4.5,
                "atr_pct": 2.1,
            }
        """
        if df is None or len(df) < 55:
            return self._default_result()

        # حساب المؤشرات اللازمة
        adx_series = compute_adx(df)
        adx = adx_series.iloc[-1] if len(adx_series) >= 14 else 20.0

        emas = compute_ema(df, spans=[21, 55])
        ema21 = emas["ema21"].iloc[-1]
        ema55 = emas["ema55"].iloc[-1]
        close = df["close"].iloc[-1]

        bb = compute_bollinger_bands(df)
        bb_width = bb["bb_width"].iloc[-1]

        atr_series = compute_atr(df)
        atr = atr_series.iloc[-1]
        atr_pct = (atr / close * 100) if close > 0 else 0.0

        # حساب اتجاه EMA
        ema_alignment = self._score_ema_alignment(ema21, ema55, close)

        # حساب درجات الأنظمة
        trend_score = self._score_trend(adx, ema_alignment, atr_pct)
        range_score = self._score_range(bb_width, adx, atr_pct)
        choppy_score = self._score_choppy(adx, bb_width, atr_pct)

        # تحديد النظام الغالب
        scores = {
            "STRONG_TREND": trend_score * 1.2
            if ema_alignment > 0.7
            else trend_score * 0.5,
            "WEAK_TREND": trend_score * 0.8
            if 0.3 < ema_alignment <= 0.7
            else trend_score * 0.3,
            "WIDE_RANGE": range_score * 1.2 if bb_width > 3.0 else range_score * 0.6,
            "NARROW_RANGE": range_score * 0.8
            if 1.0 < bb_width <= 3.0
            else range_score * 0.4,
            "CHOPPY": choppy_score,
        }

        dominant_regime = max(scores, key=scores.get)
        dominant_score = scores[dominant_regime]
        total_score = sum(scores.values())
        confidence = dominant_score / total_score if total_score > 0 else 0.33

        return {
            "dominant_regime": dominant_regime,
            "trend_score": round(trend_score, 1),
            "range_score": round(range_score, 1),
            "choppy_score": round(choppy_score, 1),
            "regime_scores": {k: round(v, 1) for k, v in scores.items()},
            "confidence": round(confidence, 2),
            "adx": round(adx, 1),
            "bb_width": round(bb_width, 2),
            "atr_pct": round(atr_pct, 2),
            "ema_alignment": round(ema_alignment, 2),
        }

    def _score_ema_alignment(self, ema21: float, ema55: float, close: float) -> float:
        """
        يحسب درجة اصطفاف المتوسطات المتحركة (0-1).
        1.0 = اصطفاف كامل (اتجاه قوي)
        0.0 = تشابك كامل (سوق عشوائي)
        """
        if ema55 == 0:
            return 0.0

        # المسافة بين EMA21 و EMA55 كنسبة
        ema_gap = abs(ema21 - ema55) / ema55

        # هل السعر فوق/تحت كلاهما؟ (اتجاه واضح)
        if (close > ema21 > ema55) or (close < ema21 < ema55):
            # اتجاه واضح: الدرجة تعتمد على قوة الفجوة
            gap_score = min(ema_gap / 0.05, 1.0)  # 5% فجوة = درجة كاملة
            return 0.5 + (gap_score * 0.5)
        else:
            # تشابك: الدرجة تعتمد على قرب السعر من المتوسطات
            dist_to_ema = min(abs(close - ema21) / ema21, abs(close - ema55) / ema55)
            return max(0.0, 0.5 - (dist_to_ema / 0.02))

    def _score_trend(self, adx: float, ema_alignment: float, atr_pct: float) -> float:
        """
        درجة الاتجاه (0-100).
        العوامل: ADX (40%)، EMA Alignment (40%)، ATR (20%)
        """
        # ADX Score (0-100)
        if adx >= 40:
            adx_score = 100.0
        elif adx >= 25:
            adx_score = 50.0 + ((adx - 25) / 15.0) * 50.0
        elif adx >= 15:
            adx_score = ((adx - 15) / 10.0) * 50.0
        else:
            adx_score = 0.0

        # EMA Score (0-100)
        ema_score = ema_alignment * 100.0

        # ATR Score (0-100) — الاتجاه يحتاج تقلب كافٍ
        if atr_pct >= 2.0:
            atr_score = 100.0
        elif atr_pct >= 1.0:
            atr_score = 50.0 + ((atr_pct - 1.0) / 1.0) * 50.0
        else:
            atr_score = atr_pct / 1.0 * 50.0

        # Weighted combination
        return (adx_score * 0.4) + (ema_score * 0.4) + (atr_score * 0.2)

    def _score_range(self, bb_width: float, adx: float, atr_pct: float) -> float:
        """
        درجة النطاق (0-100).
        العوامل: BB Width (50%)، ADX العكسي (30%)، ATR (20%)
        """
        # BB Width Score (0-100)
        if bb_width >= 4.0:
            bb_score = 100.0
        elif bb_width >= 2.0:
            bb_score = 50.0 + ((bb_width - 2.0) / 2.0) * 50.0
        elif bb_width >= 1.0:
            bb_score = ((bb_width - 1.0) / 1.0) * 50.0
        else:
            bb_score = 0.0

        # ADX Inverse Score (0-100) — النطاق يحتاج ADX منخفض
        if adx <= 15:
            adx_inv_score = 100.0
        elif adx <= 25:
            adx_inv_score = 100.0 - ((adx - 15) / 10.0) * 50.0
        else:
            adx_inv_score = max(0.0, 50.0 - ((adx - 25) / 15.0) * 50.0)

        # ATR Score (0-100) — النطاق يحتاج تقلب متوسط
        if 1.0 <= atr_pct <= 3.0:
            atr_score = 100.0
        elif atr_pct < 1.0:
            atr_score = atr_pct / 1.0 * 80.0
        else:
            atr_score = max(0.0, 100.0 - ((atr_pct - 3.0) / 2.0) * 50.0)

        # Weighted combination
        return (bb_score * 0.5) + (adx_inv_score * 0.3) + (atr_score * 0.2)

    def _score_choppy(self, adx: float, bb_width: float, atr_pct: float) -> float:
        """
        درجة العشوائية (0-100).
        العوامل: ADX المنخفض جداً (50%)، BB Width الضيق (30%)، ATR المنخفض (20%)
        """
        # ADX Very Low Score (0-100)
        if adx <= 10:
            adx_score = 100.0
        elif adx <= 20:
            adx_score = 100.0 - ((adx - 10) / 10.0) * 80.0
        else:
            adx_score = max(0.0, 20.0 - ((adx - 20) / 10.0) * 20.0)

        # BB Narrow Score (0-100)
        if bb_width <= 0.5:
            bb_score = 100.0
        elif bb_width <= 1.5:
            bb_score = 100.0 - ((bb_width - 0.5) / 1.0) * 60.0
        else:
            bb_score = max(0.0, 40.0 - ((bb_width - 1.5) / 2.0) * 40.0)

        # ATR Low Score (0-100)
        if atr_pct <= 0.5:
            atr_score = 100.0
        elif atr_pct <= 1.5:
            atr_score = 100.0 - ((atr_pct - 0.5) / 1.0) * 60.0
        else:
            atr_score = max(0.0, 40.0 - ((atr_pct - 1.5) / 1.5) * 40.0)

        # Weighted combination
        return (adx_score * 0.5) + (bb_score * 0.3) + (atr_score * 0.2)

    def _default_result(self) -> Dict:
        """نتيجة افتراضية عند عدم كفاية البيانات"""
        return {
            "dominant_regime": "CHOPPY",
            "trend_score": 20.0,
            "range_score": 30.0,
            "choppy_score": 50.0,
            "regime_scores": {
                "STRONG_TREND": 10.0,
                "WEAK_TREND": 15.0,
                "WIDE_RANGE": 15.0,
                "NARROW_RANGE": 20.0,
                "CHOPPY": 40.0,
            },
            "confidence": 0.40,
            "adx": 20.0,
            "bb_width": 1.0,
            "atr_pct": 1.0,
            "ema_alignment": 0.3,
        }
