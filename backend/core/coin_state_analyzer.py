#!/usr/bin/env python3

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CoinState:
    symbol: str
    coin_type: str  # MAJOR / MID_CAP / MEME / VOLATILE
    trend: str  # UP / DOWN / NEUTRAL
    trend_strength: str  # STRONG / MODERATE / WEAK
    trend_confirmed_4h: bool
    volatility: str  # VERY_HIGH / HIGH / MEDIUM / LOW / VERY_LOW
    regime: str  # STRONG_TREND / WEAK_TREND / WIDE_RANGE / NARROW_RANGE / CHOPPY
    range_width_pct: float
    support_level: float
    resistance_level: float
    adx: float
    rsi: float
    macd_histogram: float
    atr_pct: float
    bb_width_pct: float
    volume_trend: str  # SURGE / INCREASING / FLAT / DECLINING
    obv_trend: str  # RISING / FALLING / FLAT
    momentum: str  # ACCELERATING / STEADY / DECAYING / NONE
    ema_alignment: (
        str  # FULL_BULLISH / PARTIAL_BULLISH / MIXED / PARTIAL_BEARISH / FULL_BEARISH
    )
    recommendation: str  # TREND_CONT / BREAKOUT / RANGE / AVOID
    confidence: float
    risk_profile: str  # LOW_RISK / MEDIUM_RISK / HIGH_RISK


class CoinStateAnalyzer:
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

        ema8 = close.ewm(span=8, adjust=False).mean()
        ema21 = close.ewm(span=21, adjust=False).mean()
        ema55 = close.ewm(span=55, adjust=False).mean() if len(close) >= 55 else ema21
        e8, e21, e55 = ema8.iloc[-1], ema21.iloc[-1], ema55.iloc[-1]

        # === 1. TREND (3 confirmations: EMA alignment + price position + slope) ===
        trend, ema_align = self._analyze_trend(e8, e21, e55, cur, close)

        # === 2. 4H TREND CONFIRMATION ===
        trend_confirmed_4h = (
            self._confirm_trend_4h(df_4h, trend) if df_4h is not None else True
        )

        # === 3. TREND STRENGTH (multi-factor) ===
        trend_strength = self._analyze_trend_strength(e8, e21, e55, cur, trend)

        # === 4. VOLATILITY (ATR% + BB Width) ===
        atr, atr_pct = self._compute_atr(high, low, close, cur)
        bb_width_pct = self._compute_bb_width(close, cur)
        coin_type = self._classify_coin_type(symbol, atr_pct)
        volatility = self._classify_volatility(atr_pct, coin_type)

        # === 5. RANGE ANALYSIS ===
        support, resistance, range_width_pct = self._analyze_range(high, low, cur)

        # === 6. REGIME (ADX + BB Width + Range combined) ===
        adx_val = self._get_indicator(df, "adx", 20)
        regime = self._classify_regime(adx_val, trend, range_width_pct, bb_width_pct)

        # === 7. VOLUME ANALYSIS (ratio + OBV trend) ===
        vol_ratio, volume_trend = self._analyze_volume_trend(volume)
        obv_trend = self._analyze_obv_trend(close, volume)

        # === 8. MOMENTUM (RSI + MACD + rate of change) ===
        rsi_val = self._get_indicator(df, "rsi", 50)
        macd_hist = self._compute_macd_histogram(close)
        momentum = self._analyze_momentum(rsi_val, macd_hist, vol_ratio, trend)

        # === 9. RECOMMENDATION (all factors combined) ===
        recommendation = self._recommend(
            trend,
            trend_strength,
            trend_confirmed_4h,
            regime,
            range_width_pct,
            volatility,
            momentum,
            volume_trend,
        )

        # === 10. CONFIDENCE (weighted multi-factor) ===
        confidence = self._confidence(
            trend,
            trend_strength,
            trend_confirmed_4h,
            adx_val,
            vol_ratio,
            rsi_val,
            range_width_pct,
            momentum,
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
            volatility=volatility,
            regime=regime,
            range_width_pct=round(range_width_pct, 2),
            support_level=round(support, 8),
            resistance_level=round(resistance, 8),
            adx=round(adx_val, 1),
            rsi=round(rsi_val, 1),
            macd_histogram=round(macd_hist, 6),
            atr_pct=round(atr_pct, 2),
            bb_width_pct=round(bb_width_pct, 2),
            volume_trend=volume_trend,
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
        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        atr_pct = (atr / cur * 100) if cur > 0 else 0
        return atr, atr_pct

    def _compute_bb_width(self, close, cur):
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        upper = sma20 + 2 * std20
        lower = sma20 - 2 * std20
        width = (
            (upper.iloc[-1] - lower.iloc[-1]) / sma20.iloc[-1] * 100
            if sma20.iloc[-1] > 0
            else 0
        )
        return width

    def _analyze_range(self, high, low, cur):
        support = low.tail(30).quantile(0.15)
        resistance = high.tail(30).quantile(0.85)
        range_w = (resistance - support) / support * 100 if support > 0 else 0
        return support, resistance, range_w

    def _classify_regime(self, adx, trend, range_w, bb_width):
        if adx > 30 and trend != "NEUTRAL":
            return "STRONG_TREND"
        if adx > 20 and trend != "NEUTRAL":
            return "WEAK_TREND"
        if range_w > 2.0 and adx < 20:
            return "WIDE_RANGE"
        if range_w > 0.8 and adx < 25:
            return "NARROW_RANGE"
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
        obv_slope = (obv.iloc[-1] - obv.iloc[-20]) / max(obv.iloc[-20], 1)
        if obv_slope > 0.05:
            return "RISING"
        if obv_slope < -0.05:
            return "FALLING"
        return "FLAT"

    def _compute_macd_histogram(self, close):
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = (macd - signal).iloc[-1]
        return hist

    def _analyze_momentum(self, rsi, macd_hist, vol_ratio, trend):
        if trend == "UP" and rsi > 55 and macd_hist > 0 and vol_ratio > 1.0:
            return "ACCELERATING"
        if trend == "UP" and rsi > 50 and macd_hist > 0:
            return "STEADY"
        if trend == "UP" and macd_hist < 0:
            return "DECAYING"
        if trend == "DOWN" and rsi < 45 and macd_hist < 0:
            return "ACCELERATING"
        if abs(rsi - 50) < 10 and abs(macd_hist) < 0.001:
            return "NONE"
        return "STEADY"

    def _recommend(
        self,
        trend,
        strength,
        confirmed_4h,
        regime,
        range_w,
        volatility,
        momentum,
        vol_trend,
    ):
        if trend == "DOWN":
            return "AVOID"
        if regime == "CHOPPY" and range_w < 0.8:
            return "AVOID"
        if volatility == "VERY_HIGH" and momentum == "DECAYING":
            return "AVOID"
        if regime in ("STRONG_TREND", "WEAK_TREND") and trend == "UP" and confirmed_4h:
            if strength in ("STRONG", "MODERATE") and momentum in (
                "ACCELERATING",
                "STEADY",
            ):
                return "TREND_CONT"
            return "BREAKOUT"
        if regime == "WIDE_RANGE" and range_w > 1.5:
            return "RANGE"
        if trend == "UP" and range_w > 1.0:
            return "BREAKOUT"
        if trend == "NEUTRAL" and regime == "NARROW_RANGE" and range_w > 0.8:
            return "RANGE"
        return "AVOID"

    def _confidence(
        self, trend, strength, confirmed_4h, adx, vol_ratio, rsi, range_w, momentum
    ):
        score = 40.0
        if trend == "UP":
            score += 10
        if strength == "STRONG":
            score += 10
        elif strength == "MODERATE":
            score += 5
        if confirmed_4h:
            score += 8
        if adx > 30:
            score += 8
        elif adx > 20:
            score += 4
        if vol_ratio > 2.0:
            score += 8
        elif vol_ratio > 1.3:
            score += 4
        if 40 < rsi < 70:
            score += 5
        if momentum == "ACCELERATING":
            score += 7
        elif momentum == "STEADY":
            score += 3
        if range_w > 1.5:
            score += 5
        elif range_w > 0.8:
            score += 2
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
