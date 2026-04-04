#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Market Regime Detector — كشف حالة السوق
========================================
يحدد حالة السوق الحالية باستخدام تحليل متعدد الأطر الزمنية:
  - الاتجاه العام (1h, 4h, 1d)
  - قوة الاتجاه (ADX)
  - التقلب (ATR%)
  - الزخم (RSI, MACD)

المخرجات:
  BULL_STRONG, BULL_WEAK, NEUTRAL, BEAR_WEAK, BEAR_STRONG, HIGH_VOLATILITY
"""

import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class MarketRegimeDetector:
    """كشف حالة السوق"""

    def __init__(self):
        pass

    def detect_regime(
        self,
        df_1h: pd.DataFrame,
        df_4h: pd.DataFrame = None,
        df_1d: pd.DataFrame = None,
    ) -> dict:
        """
        كشف حالة السوق من بيانات متعددة الأطر

        Returns:
            dict with:
                regime: BULL_STRONG, BULL_WEAK, NEUTRAL, BEAR_WEAK, BEAR_STRONG, HIGH_VOLATILITY
                trend: UP, DOWN, NEUTRAL
                trend_strength: 0-100 (ADX)
                volatility: float (ATR%)
                momentum: float (RSI-50)
                confidence: 0-100
        """
        if df_1h is None or len(df_1h) < 100:
            return self._default_regime()

        # Multi-timeframe trend
        trend_1h = self._get_trend(df_1h)
        trend_4h = (
            self._get_trend(df_4h)
            if df_4h is not None and len(df_4h) >= 100
            else trend_1h
        )
        trend_1d = (
            self._get_trend(df_1d)
            if df_1d is not None and len(df_1d) >= 100
            else trend_4h
        )

        # ADX for trend strength
        adx = self._calculate_adx(df_1h)

        # Volatility
        atr_pct = self._calculate_atr_pct(df_1h)

        # Momentum
        rsi = self._calculate_rsi(df_1h)
        momentum = rsi - 50

        # Composite score
        trend_score = self._composite_trend_score(trend_1h, trend_4h, trend_1d)

        # Determine regime
        regime = self._classify_regime(trend_score, adx, atr_pct, momentum)

        confidence = min(100, max(0, adx + abs(momentum)))

        return {
            "regime": regime,
            "trend": trend_1h,
            "trend_1h": trend_1h,
            "trend_4h": trend_4h,
            "trend_1d": trend_1d,
            "trend_strength": round(adx, 1),
            "volatility": round(atr_pct, 3),
            "momentum": round(momentum, 1),
            "rsi": round(rsi, 1),
            "confidence": round(confidence, 1),
        }

    def _get_trend(self, df: pd.DataFrame) -> str:
        close = df["close"]
        ema8 = close.ewm(span=8).mean()
        ema21 = close.ewm(span=21).mean()
        ema55 = close.ewm(span=55).mean()

        last = len(df) - 1
        if ema8.iloc[last] > ema21.iloc[last] > ema55.iloc[last]:
            return "UP"
        elif ema8.iloc[last] < ema21.iloc[last] < ema55.iloc[last]:
            return "DOWN"
        return "NEUTRAL"

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        high = df["high"]
        low = df["low"]
        close = df["close"]

        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        atr = self._atr(high, low, close, period)
        plus_di = 100 * plus_dm.ewm(span=period).mean() / atr
        minus_di = 100 * minus_dm.ewm(span=period).mean() / atr

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(span=period).mean()

        return adx.iloc[-1] if not adx.empty else 25.0

    def _atr(self, high, low, close, period: int) -> pd.Series:
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(span=period).mean()

    def _calculate_atr_pct(self, df: pd.DataFrame, period: int = 14) -> float:
        atr = self._atr(df["high"], df["low"], df["close"], period)
        return (atr.iloc[-1] / df["close"].iloc[-1]) * 100 if not atr.empty else 1.0

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> float:
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).ewm(span=period).mean()
        loss = -delta.where(delta < 0, 0).ewm(span=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not rsi.empty else 50.0

    def _composite_trend_score(self, t_1h: str, t_4h: str, t_1d: str) -> float:
        mapping = {"UP": 1, "NEUTRAL": 0, "DOWN": -1}
        score = (
            mapping.get(t_1h, 0) * 0.3
            + mapping.get(t_4h, 0) * 0.4
            + mapping.get(t_1d, 0) * 0.3
        )
        return score

    def _classify_regime(
        self, trend_score: float, adx: float, atr_pct: float, momentum: float
    ) -> str:
        if atr_pct > 3.0:
            return "HIGH_VOLATILITY"

        if trend_score > 0.5 and adx > 25:
            return "BULL_STRONG"
        elif trend_score > 0.2:
            return "BULL_WEAK"
        elif trend_score < -0.5 and adx > 25:
            return "BEAR_STRONG"
        elif trend_score < -0.2:
            return "BEAR_WEAK"
        return "NEUTRAL"

    def _default_regime(self) -> dict:
        return {
            "regime": "NEUTRAL",
            "trend": "NEUTRAL",
            "trend_1h": "NEUTRAL",
            "trend_4h": "NEUTRAL",
            "trend_1d": "NEUTRAL",
            "trend_strength": 25.0,
            "volatility": 1.0,
            "momentum": 0.0,
            "rsi": 50.0,
            "confidence": 50.0,
        }

    def get_allowed_strategies(
        self, regime: str, spot_enabled: bool, margin_enabled: bool
    ) -> list:
        """
        Return list of allowed strategies based on regime and trading mode
        """
        strategy_map = {
            "BULL_STRONG": {
                "long": ["trend_cont", "breakout"],
                "short": ["breakdown"],
            },
            "BULL_WEAK": {
                "long": ["breakout"],
                "short": [],
            },
            "NEUTRAL": {
                "long": ["breakout"],
                "short": [],
            },
            "BEAR_WEAK": {
                "long": [],
                "short": ["trend_cont_short"],
            },
            "BEAR_STRONG": {
                "long": [],
                "short": ["trend_cont_short", "breakdown"],
            },
            "HIGH_VOLATILITY": {
                "long": [],
                "short": [],
            },
        }

        allowed = strategy_map.get(regime, {"long": [], "short": []})

        result = []
        if spot_enabled:
            result.extend(allowed["long"])
        if margin_enabled:
            result.extend(allowed["short"])

        return result

    def get_position_size_multiplier(self, regime: str) -> float:
        multipliers = {
            "BULL_STRONG": 1.0,
            "BULL_WEAK": 0.7,
            "NEUTRAL": 0.5,
            "BEAR_WEAK": 0.7,
            "BEAR_STRONG": 1.0,
            "HIGH_VOLATILITY": 0.3,
        }
        return multipliers.get(regime, 0.5)

    def get_stop_loss_multiplier(self, regime: str) -> float:
        multipliers = {
            "BULL_STRONG": 1.0,
            "BULL_WEAK": 1.2,
            "NEUTRAL": 1.5,
            "BEAR_WEAK": 1.2,
            "BEAR_STRONG": 1.0,
            "HIGH_VOLATILITY": 2.0,
        }
        return multipliers.get(regime, 1.5)
