#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CoinState:
    symbol: str
    trend: str  # UP / DOWN / NEUTRAL
    trend_strength: str  # STRONG / WEAK
    volatility: str  # HIGH / MEDIUM / LOW
    regime: str  # TRENDING / RANGING / CHOPPY
    range_width_pct: float
    adx: float
    rsi: float
    atr_pct: float
    volume_trend: str  # INCREASING / DECREASING / FLAT
    momentum: str  # STRONG / WEAK / NONE
    ema_alignment: str  # BULLISH / BEARISH / MIXED
    recommendation: str  # TREND_CONT / BREAKOUT / RANGE / AVOID
    confidence: float  # 0-100


class CoinStateAnalyzer:
    def analyze(self, symbol: str, df: pd.DataFrame) -> Optional[CoinState]:
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

        # === TREND ===
        if e8 > e21 > e55 and cur > e21:
            trend = "UP"
            ema_align = "BULLISH"
        elif e8 < e21 < e55 and cur < e21:
            trend = "DOWN"
            ema_align = "BEARISH"
        else:
            trend = "NEUTRAL"
            ema_align = "MIXED"

        # === TREND STRENGTH ===
        if trend == "UP":
            gap_8_21 = (e8 - e21) / e21
            gap_21_55 = (e21 - e55) / e55
            trend_strength = (
                "STRONG" if (gap_8_21 > 0.01 and gap_21_55 > 0.015) else "WEAK"
            )
        elif trend == "DOWN":
            gap_8_21 = (e21 - e8) / e21
            gap_21_55 = (e55 - e21) / e55
            trend_strength = (
                "STRONG" if (gap_8_21 > 0.01 and gap_21_55 > 0.015) else "WEAK"
            )
        else:
            trend_strength = "WEAK"

        # === VOLATILITY (ATR%) ===
        tr = pd.concat(
            [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        atr_pct = (atr / cur * 100) if cur > 0 else 0

        if atr_pct > 5:
            volatility = "HIGH"
        elif atr_pct > 2:
            volatility = "MEDIUM"
        else:
            volatility = "LOW"

        # === RANGE WIDTH ===
        support = low.tail(30).quantile(0.15)
        resistance = high.tail(30).quantile(0.85)
        range_width_pct = ((resistance - support) / support * 100) if support > 0 else 0

        # === REGIME ===
        adx_val = df.get("adx", pd.Series([20] * len(df))).iloc[-1]
        if pd.isna(adx_val):
            adx_val = 20

        if adx_val > 25 and trend != "NEUTRAL":
            regime = "TRENDING"
        elif range_width_pct > 1.5 and adx_val < 20:
            regime = "RANGING"
        else:
            regime = "CHOPPY"

        # === VOLUME TREND ===
        vol_20 = volume.rolling(20).mean()
        vol_recent = volume.tail(5).mean()
        vol_avg = vol_20.iloc[-1] if len(vol_20) >= 20 else volume.mean()
        vol_ratio = vol_recent / vol_avg if vol_avg > 0 else 1

        if vol_ratio > 1.3:
            volume_trend = "INCREASING"
        elif vol_ratio < 0.7:
            volume_trend = "DECREASING"
        else:
            volume_trend = "FLAT"

        # === MOMENTUM ===
        rsi_val = df.get("rsi", pd.Series([50] * len(df))).iloc[-1]
        if pd.isna(rsi_val):
            rsi_val = 50

        if trend == "UP" and rsi_val > 55 and vol_ratio > 1.0:
            momentum = "STRONG"
        elif trend == "DOWN" and rsi_val < 45:
            momentum = "STRONG"
        elif abs(rsi_val - 50) < 10:
            momentum = "NONE"
        else:
            momentum = "WEAK"

        # === RECOMMENDATION ===
        recommendation = self._recommend(
            trend, trend_strength, regime, range_width_pct, volatility, momentum
        )

        confidence = self._confidence(
            trend, adx_val, vol_ratio, rsi_val, range_width_pct
        )

        return CoinState(
            symbol=symbol,
            trend=trend,
            trend_strength=trend_strength,
            volatility=volatility,
            regime=regime,
            range_width_pct=round(range_width_pct, 2),
            adx=round(adx_val, 1),
            rsi=round(rsi_val, 1),
            atr_pct=round(atr_pct, 2),
            volume_trend=volume_trend,
            momentum=momentum,
            ema_alignment=ema_align,
            recommendation=recommendation,
            confidence=round(confidence, 1),
        )

    def _recommend(self, trend, strength, regime, range_w, vol, momentum) -> str:
        if trend == "DOWN":
            return "AVOID"

        if regime == "RANGING" and range_w > 1.0:
            return "RANGE"

        if trend == "UP" and strength == "STRONG" and momentum == "STRONG":
            return "TREND_CONT"

        if trend == "UP" and regime == "TRENDING":
            return "TREND_CONT"

        if trend == "UP" and range_w > 0.5:
            return "BREAKOUT"

        if regime == "CHOPPY" and range_w < 0.5:
            return "AVOID"

        if trend == "NEUTRAL" and range_w > 1.0:
            return "RANGE"

        return "AVOID"

    def _confidence(self, trend, adx, vol_ratio, rsi, range_w) -> float:
        score = 50.0
        if trend == "UP":
            score += 10
        if adx > 25:
            score += 10
        elif adx > 15:
            score += 5
        if vol_ratio > 1.5:
            score += 10
        elif vol_ratio > 1.0:
            score += 5
        if 45 < rsi < 65:
            score += 5
        if range_w > 1.0:
            score += 5
        return min(95, max(20, score))
