#!/usr/bin/env python3

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from backend.utils.indicator_calculator import (
    compute_rsi,
    compute_adx,
    compute_atr,
    compute_ema,
    compute_macd,
    compute_bollinger_bands,
    compute_obv,
)
from backend.core.fuzzy_regime_detector import FuzzyRegimeDetector

logger = logging.getLogger(__name__)


@dataclass
class CoinState:
    symbol: str
    coin_type: str
    trend: str
    trend_strength: str
    trend_confirmed_4h: bool
    trend_confirmed_macd: bool
    trend_confirmed_volume: bool
    volatility: str
    regime: str
    regime_scores: Dict[str, float]  # NEW: Fuzzy scores for each regime
    regime_confidence: float  # NEW: Confidence in dominant regime
    range_width_pct: float
    support_level: float
    resistance_level: float
    adx: float
    rsi: float
    macd_histogram: float
    atr_pct: float
    bb_width_pct: float
    bb_position: float
    volume_trend: str
    volume_ratio: float
    obv_trend: str
    momentum: str
    ema_alignment: str
    recommendation: str
    confidence: float
    risk_profile: str


class CoinStateAnalyzer:
    """
    محلل حالة العملة — محسّن بـ:
    1. Fuzzy Regime Detection (نقاط مرجحة بدلاً من عتبات حادة)
    2. Multi-factor confirmation (EMA + MACD + Volume + Price)
    3. Divergence detection (RSI/Price)
    4. Regime-aware confidence scoring
    5. Volume profile analysis
    """

    def __init__(self):
        # NEW: Fuzzy regime detector replaces hard threshold logic
        self.regime_detector = FuzzyRegimeDetector()

    VOLATILITY_THRESHOLDS = {
        "MAJOR": {"very_high": 4.0, "high": 2.0, "medium": 1.0, "low": 0.5},
        "MID_CAP": {"very_high": 6.0, "high": 3.5, "medium": 1.5, "low": 0.8},
        "MEME": {"very_high": 10.0, "high": 6.0, "medium": 3.0, "low": 1.5},
        "VOLATILE": {"very_high": 8.0, "high": 4.5, "medium": 2.0, "low": 1.0},
    }

    MEME_SYMBOLS = {
        "PEPEUSDT",
        "SHIBUSDT",
        "DOGEUSDT",
        "FLOKIUSDT",
        "BONKUSDT",
        "MEMEUSDT",
        "TURBOUSDT",
        "WIFUSDT",
    }
    MAJOR_SYMBOLS = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"}
    VOLATILE_SYMBOLS = {"INJUSDT", "SUIUSDT", "APTUSDT", "ARBUSDT", "OPUSDT"}

    def _classify_coin_type(self, symbol: str, atr_pct: float) -> str:
        if symbol in self.MAJOR_SYMBOLS:
            return "MAJOR"
        if symbol in self.MEME_SYMBOLS:
            return "MEME"
        if symbol in self.VOLATILE_SYMBOLS:
            return "VOLATILE"
        return "MID_CAP"

    def _classify_volatility(self, atr_pct: float, coin_type: str) -> str:
        thresholds = self.VOLATILITY_THRESHOLDS.get(
            coin_type, self.VOLATILITY_THRESHOLDS["MID_CAP"]
        )
        if atr_pct > thresholds["very_high"]:
            return "VERY_HIGH"
        if atr_pct > thresholds["high"]:
            return "HIGH"
        if atr_pct > thresholds["medium"]:
            return "MEDIUM"
        if atr_pct > thresholds["low"]:
            return "LOW"
        return "VERY_LOW"

    def analyze(
        self, symbol: str, df: pd.DataFrame, df_4h: pd.DataFrame = None
    ) -> Optional[CoinState]:
        if df is None or len(df) < 55:
            return None

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]
        cur = close.iloc[-1]

        # === المؤشرات الأساسية ===
        emas = compute_ema(df)
        e8, e21, e55 = (
            emas["ema8"].iloc[-1],
            emas["ema21"].iloc[-1],
            emas["ema55"].iloc[-1],
        )
        adx_val = self._get_indicator(df, "adx", 20)
        rsi_val = self._get_indicator(df, "rsi", 50)
        atr, atr_pct = self._compute_atr(high, low, close, cur)
        bb = compute_bollinger_bands(df)
        bb_width_pct = bb["bb_width"].iloc[-1]
        bb_position = (
            (cur - bb["bb_lower"].iloc[-1])
            / (bb["bb_upper"].iloc[-1] - bb["bb_lower"].iloc[-1])
            if bb["bb_upper"].iloc[-1] != bb["bb_lower"].iloc[-1]
            else 0.5
        )
        macd = compute_macd(df)
        macd_hist = macd["macd_histogram"].iloc[-1]
        vol_ratio, volume_trend = self._analyze_volume_trend(volume)
        obv_trend = self._analyze_obv_trend(close, volume)

        # === 1. TREND (EMA alignment) ===
        trend, ema_align = self._analyze_trend(e8, e21, e55, cur, close)

        # === 2. TREND CONFIRMATIONS (3 عوامل مستقلة) ===
        # FIX: Default to False if 4H data unavailable (prevents false positives)
        trend_confirmed_4h = (
            self._confirm_trend_4h(df_4h, trend) if df_4h is not None else False
        )
        trend_confirmed_macd = self._confirm_trend_macd(
            macd_hist, macd["macd"].iloc[-1], macd["macd_signal"].iloc[-1], trend
        )
        trend_confirmed_volume = self._confirm_trend_volume(
            volume_trend, obv_trend, trend
        )

        # === 3. TREND STRENGTH ===
        trend_strength = self._analyze_trend_strength(e8, e21, e55, cur, trend)

        # === 4. VOLATILITY ===
        coin_type = self._classify_coin_type(symbol, atr_pct)
        volatility = self._classify_volatility(atr_pct, coin_type)

        # === 5. RANGE ===
        support, resistance, range_width_pct = self._analyze_range(high, low, cur)

        # === 6. REGIME (Fuzzy Detection — replaces hard thresholds) ===
        regime_result = self.regime_detector.detect(df)
        regime = regime_result["dominant_regime"]
        regime_scores = regime_result["regime_scores"]
        regime_confidence = regime_result["confidence"]

        # === 7. MOMENTUM (محسّن) ===
        momentum = self._analyze_momentum(
            rsi_val, macd_hist, vol_ratio, trend, bb_position
        )

        # === 8. DIVERGENCE DETECTION ===
        has_bullish_div = self._detect_bullish_divergence(close, rsi_val, df)
        has_bearish_div = self._detect_bearish_divergence(close, rsi_val, df)

        # === 9. RECOMMENDATION (multi-factor) ===
        recommendation = self._recommend(
            trend,
            trend_strength,
            trend_confirmed_4h,
            trend_confirmed_macd,
            trend_confirmed_volume,
            regime,
            range_width_pct,
            volatility,
            momentum,
            volume_trend,
            has_bullish_div,
            has_bearish_div,
        )

        # === 10. CONFIDENCE (regime-aware weighted scoring) ===
        confidence = self._confidence(
            trend,
            trend_strength,
            trend_confirmed_4h,
            trend_confirmed_macd,
            trend_confirmed_volume,
            adx_val,
            vol_ratio,
            rsi_val,
            range_width_pct,
            momentum,
            bb_position,
            has_bullish_div,
            has_bearish_div,
        )

        # === 11. RISK PROFILE ===
        risk_profile = self._risk_profile(
            coin_type, volatility, atr_pct, range_width_pct
        )

        return CoinState(
            symbol=symbol,
            coin_type=coin_type,
            trend=trend,
            trend_strength=trend_strength,
            trend_confirmed_4h=trend_confirmed_4h,
            trend_confirmed_macd=trend_confirmed_macd,
            trend_confirmed_volume=trend_confirmed_volume,
            volatility=volatility,
            regime=regime,
            regime_scores=regime_scores,  # NEW: Fuzzy scores
            regime_confidence=regime_confidence,  # NEW: Confidence in regime
            range_width_pct=round(range_width_pct, 2),
            support_level=round(support, 8),
            resistance_level=round(resistance, 8),
            adx=round(adx_val, 1),
            rsi=round(rsi_val, 1),
            macd_histogram=round(macd_hist, 6),
            atr_pct=round(atr_pct, 2),
            bb_width_pct=round(bb_width_pct, 2),
            bb_position=round(bb_position, 3),
            volume_trend=volume_trend,
            volume_ratio=round(vol_ratio, 2),
            obv_trend=obv_trend,
            momentum=momentum,
            ema_alignment=ema_align,
            recommendation=recommendation,
            confidence=round(confidence, 1),
            risk_profile=risk_profile,
        )

    def _analyze_trend(self, e8, e21, e55, cur, close):
        if e8 > e21 > e55 and cur > e21:
            return "UP", "FULL_BULLISH"
        if e8 > e21 and cur > e55:
            return "UP", "PARTIAL_BULLISH"
        if e8 < e21 < e55 and cur < e21:
            return "DOWN", "FULL_BEARISH"
        if e8 < e21 and cur < e55:
            return "DOWN", "PARTIAL_BEARISH"
        return "NEUTRAL", "MIXED"

    def _confirm_trend_4h(self, df_4h, current_trend):
        if df_4h is None or len(df_4h) < 55:
            return True
        c4 = df_4h["close"]
        e21_4 = c4.ewm(span=21, adjust=False).mean().iloc[-1]
        e55_4 = (
            c4.ewm(span=55, adjust=False).mean().iloc[-1] if len(c4) >= 55 else e21_4
        )
        cur_4 = c4.iloc[-1]
        if current_trend == "UP":
            return cur_4 > e21_4 and e21_4 >= e55_4
        if current_trend == "DOWN":
            return cur_4 < e21_4 and e21_4 <= e55_4
        return True

    def _confirm_trend_macd(self, macd_hist, macd_line, macd_signal, trend):
        """تأكيد الاتجاه من MACD (خط MACD فوق/تحت signal + histogram متوافق)"""
        if trend == "UP":
            return macd_line > macd_signal and macd_hist > 0
        if trend == "DOWN":
            return macd_line < macd_signal and macd_hist < 0
        return True

    def _confirm_trend_volume(self, volume_trend, obv_trend, trend):
        """تأكيد الاتجاه من الحجم (حجم متزايد + OBV متوافق)"""
        if trend == "UP":
            return volume_trend in ("SURGE", "INCREASING") or obv_trend == "RISING"
        if trend == "DOWN":
            return volume_trend in ("SURGE", "INCREASING") or obv_trend == "FALLING"
        return True

    def _analyze_trend_strength(self, e8, e21, e55, cur, trend):
        if trend == "NEUTRAL":
            return "WEAK"
        if trend == "UP":
            gap_8_21 = (e8 - e21) / e21 if e21 > 0 else 0
            gap_21_55 = (e21 - e55) / e55 if e55 > 0 else 0
            above_21 = (cur - e21) / e21 if e21 > 0 else 0
            if gap_8_21 > 0.015 and gap_21_55 > 0.02 and above_21 > 0:
                return "STRONG"
            if gap_8_21 > 0.005 and gap_21_55 > 0.01:
                return "MODERATE"
            return "WEAK"
        gap_8_21 = (e21 - e8) / e21 if e21 > 0 else 0
        gap_21_55 = (e55 - e21) / e55 if e55 > 0 else 0
        if gap_8_21 > 0.015 and gap_21_55 > 0.02:
            return "STRONG"
        if gap_8_21 > 0.005 and gap_21_55 > 0.01:
            return "MODERATE"
        return "WEAK"

    def _compute_atr(self, high, low, close, cur):
        df_temp = pd.DataFrame({"high": high, "low": low, "close": close})
        atr_series = compute_atr(df_temp)
        atr = atr_series.iloc[-1]
        atr_pct = (atr / cur * 100) if cur > 0 else 0
        return atr, atr_pct

    def _analyze_range(self, high, low, cur):
        support = low.tail(30).quantile(0.15)
        resistance = high.tail(30).quantile(0.85)
        range_w = (resistance - support) / support * 100 if support > 0 else 0
        return support, resistance, range_w

    def _classify_regime(self, adx, trend, range_w, bb_width, atr_pct):
        """تصنيف نظام السوق — dynamic thresholds"""
        # نظام اتجاه قوي: ADX عالي + اتجاه واضح
        if adx > 30 and trend != "NEUTRAL":
            return "STRONG_TREND"
        # نظام اتجاه ضعيف: ADX متوسط + اتجاه
        if adx > 20 and trend != "NEUTRAL":
            return "WEAK_TREND"
        # نظام نطاق واسع: BB Width عالي + ADX منخفض
        if bb_width > 3.0 and adx < 20:
            return "WIDE_RANGE"
        # نظام نطاق ضيق: BB Width متوسط + ADX منخفض
        if bb_width > 1.0 and adx < 25:
            return "NARROW_RANGE"
        # نظام عشوائي (choppy): لا اتجاه + تقلب منخفض
        return "CHOPPY"

    def _analyze_volume_trend(self, volume):
        vol_20 = volume.rolling(20).mean()
        vol_5 = volume.tail(5).mean()
        vol_avg = vol_20.iloc[-1] if len(vol_20) >= 20 else volume.mean()
        ratio = vol_5 / vol_avg if vol_avg > 0 else 1
        if ratio > 2.0:
            return ratio, "SURGE"
        if ratio > 1.3:
            return ratio, "INCREASING"
        if ratio < 0.6:
            return ratio, "DECLINING"
        return ratio, "FLAT"

    def _analyze_obv_trend(self, close, volume):
        obv = (np.sign(close.diff()) * volume).cumsum()
        if len(obv) < 20:
            return "FLAT"
        obv_slope = (obv.iloc[-1] - obv.iloc[-20]) / max(abs(obv.iloc[-20]), 1)
        if obv_slope > 0.05:
            return "RISING"
        if obv_slope < -0.05:
            return "FALLING"
        return "FLAT"

    def _analyze_momentum(self, rsi, macd_hist, vol_ratio, trend, bb_position):
        """تحليل الزخم — محسّن مع BB position"""
        if trend == "UP":
            if rsi > 55 and macd_hist > 0 and vol_ratio > 1.0 and bb_position > 0.5:
                return "ACCELERATING"
            if rsi > 50 and macd_hist > 0:
                return "STEADY"
            if macd_hist < 0 and rsi > 65:
                return "DECAYING"  # RSI مرتفع لكن MACD يتراجع = ضعف
        elif trend == "DOWN":
            if rsi < 45 and macd_hist < 0 and vol_ratio > 1.0:
                return "ACCELERATING"
            if rsi < 50 and macd_hist < 0:
                return "STEADY"
        if abs(rsi - 50) < 10 and abs(macd_hist) < 0.001:
            return "NONE"
        return "STEADY"

    def _detect_bullish_divergence(self, close, rsi, df, lookback=20):
        """كشف تباعد صاعد: سعر ينخفض لكن RSI يرتفع"""
        if len(close) < lookback * 2:
            return False
        recent_close = close.tail(lookback)
        recent_rsi = df.get("rsi", pd.Series([50] * len(close))).tail(lookback)
        if len(recent_rsi) < lookback:
            return False
        price_low_1 = recent_close.iloc[: lookback // 2].min()
        price_low_2 = recent_close.iloc[lookback // 2 :].min()
        rsi_low_1 = recent_rsi.iloc[: lookback // 2].min()
        rsi_low_2 = recent_rsi.iloc[lookback // 2 :].min()
        return price_low_2 < price_low_1 and rsi_low_2 > rsi_low_1

    def _detect_bearish_divergence(self, close, rsi, df, lookback=20):
        """كشف تباعد هابط: سعر يرتفع لكن RSI ينخفض"""
        if len(close) < lookback * 2:
            return False
        recent_close = close.tail(lookback)
        recent_rsi = df.get("rsi", pd.Series([50] * len(close))).tail(lookback)
        if len(recent_rsi) < lookback:
            return False
        price_high_1 = recent_close.iloc[: lookback // 2].max()
        price_high_2 = recent_close.iloc[lookback // 2 :].max()
        rsi_high_1 = recent_rsi.iloc[: lookback // 2].max()
        rsi_high_2 = recent_rsi.iloc[lookback // 2 :].max()
        return price_high_2 > price_high_1 and rsi_high_2 < rsi_high_1

    def _recommend(
        self,
        trend,
        strength,
        confirmed_4h,
        confirmed_macd,
        confirmed_volume,
        regime,
        range_w,
        volatility,
        momentum,
        vol_trend,
        has_bullish_div,
        has_bearish_div,
    ):
        """توصية محسّنة — multi-factor confirmation + SHORT support"""
        # FIX: Allow SHORT signals instead of auto-rejecting all downtrends
        if trend == "DOWN":
            confirmations = sum([confirmed_4h, confirmed_macd, confirmed_volume])
            if (
                confirmations >= 2
                and strength in ("STRONG", "MODERATE")
                and momentum in ("ACCELERATING", "STEADY")
            ):
                return "SHORT_TREND"
            return "AVOID"

        # رفض التشويش الشديد
        if regime == "CHOPPY" and range_w < 0.8:
            return "AVOID"

        # رفض التقلب العالي مع زخم متدهور
        if volatility == "VERY_HIGH" and momentum == "DECAYING":
            return "AVOID"

        # تباعد هابط = تحذير
        if has_bearish_div and momentum != "ACCELERATING":
            return "AVOID"

        # نظام اتجاه + تأكيد 4H + MACD
        if regime in ("STRONG_TREND", "WEAK_TREND") and trend == "UP":
            confirmations = sum([confirmed_4h, confirmed_macd, confirmed_volume])
            if (
                confirmations >= 2
                and strength in ("STRONG", "MODERATE")
                and momentum in ("ACCELERATING", "STEADY")
            ):
                return "TREND_CONT"
            if confirmations >= 2:
                return "BREAKOUT"

        # نظام نطاق واسع
        if regime == "WIDE_RANGE" and range_w > 1.5:
            return "RANGE"

        # تباعد صاعد + اتجاه صاعد = فرصة
        if has_bullish_div and trend == "UP" and momentum != "DECAYING":
            return "BREAKOUT"

        # نطاق ضيق
        if trend == "NEUTRAL" and regime == "NARROW_RANGE" and range_w > 0.8:
            return "RANGE"

        return "AVOID"

    def _confidence(
        self,
        trend,
        strength,
        confirmed_4h,
        confirmed_macd,
        confirmed_volume,
        adx,
        vol_ratio,
        rsi,
        range_w,
        momentum,
        bb_position,
        has_bullish_div,
        has_bearish_div,
    ):
        """Confidence scoring — regime-aware weighted"""
        score = 35.0

        # الاتجاه (15 نقطة)
        if trend == "UP":
            score += 10
            if strength == "STRONG":
                score += 5
            elif strength == "MODERATE":
                score += 3

        # التأكيدات المتعددة (18 نقطة — 6 لكل تأكيد)
        if confirmed_4h:
            score += 6
        if confirmed_macd:
            score += 6
        if confirmed_volume:
            score += 6

        # قوة الاتجاه (ADX) (8 نقاط)
        if adx > 30:
            score += 8
        elif adx > 20:
            score += 4

        # الحجم (8 نقاط)
        if vol_ratio > 2.0:
            score += 8
        elif vol_ratio > 1.3:
            score += 4

        # RSI في المنطقة المثالية (5 نقاط)
        if 40 < rsi < 70:
            score += 5
        elif rsi > 75 or rsi < 25:
            score -= 3  # مناطق متطرفة

        # الزخم (7 نقاط)
        if momentum == "ACCELERATING":
            score += 7
        elif momentum == "STEADY":
            score += 3
        elif momentum == "DECAYING":
            score -= 3

        # BB position (3 نقاط)
        if 0.3 < bb_position < 0.8:
            score += 3  # ليس عند الحدود المتطرفة

        # التباعد
        if has_bullish_div:
            score += 5
        if has_bearish_div:
            score -= 5

        return min(98, max(15, score))

    def _risk_profile(self, coin_type, volatility, atr_pct, range_w):
        if coin_type == "MAJOR" and volatility in ("LOW", "MEDIUM"):
            return "LOW_RISK"
        if coin_type == "MEME" or volatility in ("VERY_HIGH", "HIGH"):
            return "HIGH_RISK"
        return "MEDIUM_RISK"

    def _get_indicator(self, df, name, default):
        val = df.get(name, pd.Series([default] * len(df))).iloc[-1]
        return default if pd.isna(val) else val
