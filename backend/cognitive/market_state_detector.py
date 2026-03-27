#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Market State Detector - نظام تصنيف حالة السوق
يحلل هيكل السوق ويصنفه إلى حالات واضحة قبل أي قرار تداول

الحالات الممكنة:
1. UPTREND - اتجاه صاعد (Higher Highs + Higher Lows)
2. DOWNTREND - اتجاه هابط (Lower Highs + Lower Lows)
3. RANGE - تذبذب جانبي (Sideways within bounds)
4. NEAR_TOP - قرب القمة (RSI>70, resistance, momentum fading)
5. NEAR_BOTTOM - قرب القاع (RSI<30, support, momentum building)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum

try:
    import pandas_ta as ta
except ImportError:
    ta = None

logger = logging.getLogger(__name__)


class MarketState(Enum):
    """حالات السوق الممكنة"""

    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    RANGE = "range"
    NEAR_TOP = "near_top"
    NEAR_BOTTOM = "near_bottom"
    UNDEFINED = "undefined"


@dataclass
class MarketStateResult:
    """نتيجة تحليل حالة السوق"""

    state: MarketState
    confidence: float  # 0-100
    trend_strength: float  # 0-100 (ADX)
    momentum: float  # -100 to +100
    volatility: float  # percentage
    support_level: float
    resistance_level: float
    reasoning: str
    indicators: Dict


class MarketStateDetector:
    """
    نظام تصنيف حالة السوق الذكي

    يستخدم:
    1. Market Structure Analysis (HH, HL, LH, LL)
    2. ADX for trend strength
    3. RSI for momentum extremes
    4. Bollinger Bands for volatility
    5. Volume Analysis for confirmation
    6. Support/Resistance detection
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # معايير التصنيف
        self.thresholds = {
            # Trend Strength
            "adx_strong_trend": self.config.get("adx_strong_trend", 25),
            "adx_very_strong_trend": self.config.get(
                "adx_very_strong_trend", 40
            ),
            # RSI Extremes
            "rsi_overbought": self.config.get("rsi_overbought", 70),
            "rsi_oversold": self.config.get("rsi_oversold", 30),
            "rsi_extreme_overbought": self.config.get(
                "rsi_extreme_overbought", 80
            ),
            "rsi_extreme_oversold": self.config.get(
                "rsi_extreme_oversold", 20
            ),
            # Volatility
            "volatility_high": self.config.get("volatility_high", 0.05),  # 5%
            # 1.5%
            "volatility_low": self.config.get("volatility_low", 0.015),
            # Structure
            "swing_lookback": self.config.get("swing_lookback", 5),
            "structure_min_swings": self.config.get("structure_min_swings", 3),
            # Confirmation
            "min_confidence": self.config.get("min_confidence", 60),
        }

        self.logger = logger

    def detect_state(
        self, df: pd.DataFrame, symbol: str = ""
    ) -> MarketStateResult:
        """
        تحليل حالة السوق الحالية

        Args:
            df: DataFrame مع OHLCV data
            symbol: رمز العملة (للتسجيل)

        Returns:
            MarketStateResult مع التصنيف والتفاصيل
        """
        try:
            if df is None or len(df) < 50:
                return self._undefined_result("بيانات غير كافية")

            df = df.copy()

            # 1. حساب المؤشرات الأساسية
            indicators = self._calculate_indicators(df)

            # 2. تحليل هيكل السوق (Swing Points)
            structure = self._analyze_market_structure(df)

            # 3. تحديد مستويات الدعم والمقاومة
            support, resistance = self._find_support_resistance(df)

            # 4. تصنيف الحالة
            state, confidence, reasoning = self._classify_state(
                indicators, structure, df, support, resistance
            )

            # 5. حساب الزخم
            momentum = self._calculate_momentum(indicators)

            # 6. حساب التقلب
            volatility = indicators.get("volatility", 0)

            result = MarketStateResult(
                state=state,
                confidence=confidence,
                trend_strength=indicators.get("adx", 0),
                momentum=momentum,
                volatility=volatility,
                support_level=support,
                resistance_level=resistance,
                reasoning=reasoning,
                indicators=indicators,
            )

            self.logger.info(f"🔍 [{symbol}] Market State: {
                state.value} | " f"Confidence: {
                confidence:.1f}% | ADX: {
                indicators.get(
                    'adx',
                    0):.1f}")

            return result

        except Exception as e:
            self.logger.error(f"خطأ في تحليل حالة السوق: {e}")
            return self._undefined_result(f"خطأ: {str(e)}")

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """حساب جميع المؤشرات المطلوبة"""
        indicators = {}

        try:
            # RSI
            if ta:
                rsi = ta.rsi(df["close"], length=14)
                indicators["rsi"] = (
                    rsi.iloc[-1] if rsi is not None and len(rsi) > 0 else 50
                )
            else:
                indicators["rsi"] = self._calculate_rsi_manual(df["close"])

            # ADX + DI (with manual fallback)
            if ta:
                adx_df = ta.adx(df["high"], df["low"], df["close"], length=14)
                if adx_df is not None and "ADX_14" in adx_df.columns:
                    indicators["adx"] = adx_df["ADX_14"].iloc[-1]
                    indicators["plus_di"] = (
                        adx_df["DMP_14"].iloc[-1]
                        if "DMP_14" in adx_df.columns
                        else 0
                    )
                    indicators["minus_di"] = (
                        adx_df["DMN_14"].iloc[-1]
                        if "DMN_14" in adx_df.columns
                        else 0
                    )
                else:
                    adx_vals = self._calculate_adx_manual(df)
                    indicators.update(adx_vals)
            else:
                adx_vals = self._calculate_adx_manual(df)
                indicators.update(adx_vals)

            # Moving Averages
            indicators["sma_20"] = df["close"].rolling(20).mean().iloc[-1]
            indicators["sma_50"] = (
                df["close"].rolling(50).mean().iloc[-1]
                if len(df) >= 50
                else df["close"].mean()
            )
            indicators["ema_9"] = df["close"].ewm(span=9).mean().iloc[-1]
            indicators["ema_21"] = df["close"].ewm(span=21).mean().iloc[-1]

            # Current price position relative to MAs
            current_price = df["close"].iloc[-1]
            indicators["price_vs_sma20"] = (
                (current_price - indicators["sma_20"])
                / indicators["sma_20"]
                * 100
            )
            indicators["price_vs_sma50"] = (
                (current_price - indicators["sma_50"])
                / indicators["sma_50"]
                * 100
            )

            # Bollinger Bands
            if ta:
                bb = ta.bbands(df["close"], length=20)
                if bb is not None:
                    indicators["bb_upper"] = (
                        bb["BBU_20_2.0"].iloc[-1]
                        if "BBU_20_2.0" in bb.columns
                        else current_price * 1.02
                    )
                    indicators["bb_lower"] = (
                        bb["BBL_20_2.0"].iloc[-1]
                        if "BBL_20_2.0" in bb.columns
                        else current_price * 0.98
                    )
                    indicators["bb_mid"] = (
                        bb["BBM_20_2.0"].iloc[-1]
                        if "BBM_20_2.0" in bb.columns
                        else indicators["sma_20"]
                    )
                    indicators["bb_width"] = (
                        indicators["bb_upper"] - indicators["bb_lower"]
                    ) / indicators["bb_mid"]
                else:
                    self._set_default_bb(indicators, current_price)
            else:
                self._set_default_bb(indicators, current_price)

            # BB Position (0-100)
            bb_range = indicators["bb_upper"] - indicators["bb_lower"]
            if bb_range > 0:
                indicators["bb_position"] = (
                    (current_price - indicators["bb_lower"]) / bb_range * 100
                )
            else:
                indicators["bb_position"] = 50

            # Volatility (ATR based)
            if ta:
                atr = ta.atr(df["high"], df["low"], df["close"], length=14)
                indicators["atr"] = (
                    atr.iloc[-1] if atr is not None and len(atr) > 0 else 0
                )
            else:
                indicators["atr"] = self._calculate_atr_manual(df)

            indicators["volatility"] = (
                indicators["atr"] / current_price if current_price > 0 else 0
            )

            # MACD
            if ta:
                macd_df = ta.macd(df["close"])
                if macd_df is not None:
                    indicators["macd"] = (
                        macd_df["MACD_12_26_9"].iloc[-1]
                        if "MACD_12_26_9" in macd_df.columns
                        else 0
                    )
                    indicators["macd_signal"] = (
                        macd_df["MACDs_12_26_9"].iloc[-1]
                        if "MACDs_12_26_9" in macd_df.columns
                        else 0
                    )
                    indicators["macd_hist"] = (
                        macd_df["MACDh_12_26_9"].iloc[-1]
                        if "MACDh_12_26_9" in macd_df.columns
                        else 0
                    )
                else:
                    indicators["macd"] = indicators["macd_signal"] = (
                        indicators["macd_hist"]
                    ) = 0
            else:
                indicators["macd"] = indicators["macd_signal"] = indicators[
                    "macd_hist"
                ] = 0

            # Volume Analysis
            avg_volume = df["volume"].rolling(20).mean().iloc[-1]
            current_volume = df["volume"].iloc[-1]
            indicators["volume_ratio"] = (
                current_volume / avg_volume if avg_volume > 0 else 1
            )

            # Price change
            indicators["price_change_1d"] = (
                (df["close"].iloc[-1] - df["close"].iloc[-2])
                / df["close"].iloc[-2]
                * 100
                if len(df) > 1
                else 0
            )
            indicators["price_change_5d"] = (
                (df["close"].iloc[-1] - df["close"].iloc[-5])
                / df["close"].iloc[-5]
                * 100
                if len(df) > 5
                else 0
            )

            indicators["current_price"] = current_price

        except Exception as e:
            self.logger.error(f"خطأ في حساب المؤشرات: {e}")
            indicators = self._get_default_indicators(df)

        return indicators

    def _set_default_bb(self, indicators: Dict, current_price: float):
        """تعيين قيم افتراضية لـ Bollinger Bands"""
        indicators["bb_upper"] = current_price * 1.02
        indicators["bb_lower"] = current_price * 0.98
        indicators["bb_mid"] = current_price
        indicators["bb_width"] = 0.04

    def _analyze_market_structure(self, df: pd.DataFrame) -> Dict:
        """
        تحليل هيكل السوق - Higher Highs, Higher Lows, etc.
        """
        structure = {
            "swing_highs": [],
            "swing_lows": [],
            "hh_count": 0,  # Higher Highs
            "hl_count": 0,  # Higher Lows
            "lh_count": 0,  # Lower Highs
            "ll_count": 0,  # Lower Lows
            "trend_structure": "undefined",
            "last_swing_high": None,
            "last_swing_low": None,
        }

        try:
            lookback = self.thresholds["swing_lookback"]
            highs = df["high"].values
            lows = df["low"].values

            # Find swing highs and lows
            for i in range(lookback, len(df) - lookback):
                # Swing High
                if all(
                    highs[i] >= highs[i - j] for j in range(1, lookback + 1)
                ) and all(
                    highs[i] >= highs[i + j] for j in range(1, lookback + 1)
                ):
                    structure["swing_highs"].append(
                        {
                            "index": i,
                            "price": highs[i],
                            "time": (
                                df.index[i]
                                if hasattr(df.index, "__getitem__")
                                else i
                            ),
                        }
                    )

                # Swing Low
                if all(
                    lows[i] <= lows[i - j] for j in range(1, lookback + 1)
                ) and all(
                    lows[i] <= lows[i + j] for j in range(1, lookback + 1)
                ):
                    structure["swing_lows"].append(
                        {
                            "index": i,
                            "price": lows[i],
                            "time": (
                                df.index[i]
                                if hasattr(df.index, "__getitem__")
                                else i
                            ),
                        }
                    )

            # Analyze the structure
            if len(structure["swing_highs"]) >= 2:
                for i in range(1, len(structure["swing_highs"])):
                    if (
                        structure["swing_highs"][i]["price"]
                        > structure["swing_highs"][i - 1]["price"]
                    ):
                        structure["hh_count"] += 1
                    else:
                        structure["lh_count"] += 1
                structure["last_swing_high"] = structure["swing_highs"][-1][
                    "price"
                ]

            if len(structure["swing_lows"]) >= 2:
                for i in range(1, len(structure["swing_lows"])):
                    if (
                        structure["swing_lows"][i]["price"]
                        > structure["swing_lows"][i - 1]["price"]
                    ):
                        structure["hl_count"] += 1
                    else:
                        structure["ll_count"] += 1
                structure["last_swing_low"] = structure["swing_lows"][-1][
                    "price"
                ]

            # Determine trend structure
            if structure["hh_count"] >= 2 and structure["hl_count"] >= 2:
                structure["trend_structure"] = "bullish"
            elif structure["lh_count"] >= 2 and structure["ll_count"] >= 2:
                structure["trend_structure"] = "bearish"
            elif structure["hh_count"] >= 1 and structure["ll_count"] >= 1:
                structure["trend_structure"] = "mixed"
            else:
                structure["trend_structure"] = "ranging"

        except Exception as e:
            self.logger.error(f"خطأ في تحليل هيكل السوق: {e}")

        return structure

    def _find_support_resistance(
        self, df: pd.DataFrame
    ) -> Tuple[float, float]:
        """تحديد مستويات الدعم والمقاومة"""
        try:
            lookback = min(50, len(df))
            recent_df = df.tail(lookback)

            # Simple approach: use recent lows and highs
            support = recent_df["low"].min()
            resistance = recent_df["high"].max()

            # Refine using clustering
            lows = recent_df["low"].values
            highs = recent_df["high"].values

            # Find common support zones
            low_clusters = self._cluster_prices(lows, threshold=0.02)
            if low_clusters:
                support = np.mean(low_clusters[-1])  # Most recent cluster

            # Find common resistance zones
            high_clusters = self._cluster_prices(highs, threshold=0.02)
            if high_clusters:
                resistance = np.mean(high_clusters[-1])

            return support, resistance

        except Exception as e:
            self.logger.error(f"خطأ في تحديد الدعم/المقاومة: {e}")
            current_price = df["close"].iloc[-1]
            return current_price * 0.95, current_price * 1.05

    def _cluster_prices(
        self, prices: np.ndarray, threshold: float = 0.02
    ) -> List[List[float]]:
        """تجميع الأسعار المتقاربة"""
        if len(prices) == 0:
            return []

        sorted_prices = np.sort(prices)
        clusters = [[sorted_prices[0]]]

        for price in sorted_prices[1:]:
            if abs(price - clusters[-1][-1]) / clusters[-1][-1] <= threshold:
                clusters[-1].append(price)
            else:
                clusters.append([price])

        # Return clusters with at least 2 touches
        return [c for c in clusters if len(c) >= 2]

    def _classify_state(
        self,
        indicators: Dict,
        structure: Dict,
        df: pd.DataFrame,
        support: float,
        resistance: float,
    ) -> Tuple[MarketState, float, str]:
        """تصنيف حالة السوق النهائية"""

        scores = {
            MarketState.UPTREND: 0,
            MarketState.DOWNTREND: 0,
            MarketState.RANGE: 0,
            MarketState.NEAR_TOP: 0,
            MarketState.NEAR_BOTTOM: 0,
        }

        reasons = []
        adx = indicators.get("adx", 20)
        rsi = indicators.get("rsi", 50)
        current_price = indicators.get("current_price", df["close"].iloc[-1])
        bb_position = indicators.get("bb_position", 50)
        price_vs_sma20 = indicators.get("price_vs_sma20", 0)
        price_vs_sma50 = indicators.get("price_vs_sma50", 0)
        macd_hist = indicators.get("macd_hist", 0)
        plus_di = indicators.get("plus_di", 0)
        minus_di = indicators.get("minus_di", 0)

        # 1. Trend Analysis (ADX + Structure)
        if adx >= self.thresholds["adx_strong_trend"]:
            if structure["trend_structure"] == "bullish" or (
                plus_di > minus_di and price_vs_sma20 > 0
            ):
                scores[MarketState.UPTREND] += 35
                reasons.append(f"ADX قوي ({adx:.1f}) + هيكل صاعد")
            elif structure["trend_structure"] == "bearish" or (
                minus_di > plus_di and price_vs_sma20 < 0
            ):
                scores[MarketState.DOWNTREND] += 35
                reasons.append(f"ADX قوي ({adx:.1f}) + هيكل هابط")
        elif adx >= 15:
            # Moderate trend - still directional
            if plus_di > minus_di and price_vs_sma20 > 1:
                scores[MarketState.UPTREND] += 20
                reasons.append(f"ADX معتدل ({adx:.1f}) + اتجاه صاعد")
            elif minus_di > plus_di and price_vs_sma20 < -1:
                scores[MarketState.DOWNTREND] += 20
                reasons.append(f"ADX معتدل ({adx:.1f}) + اتجاه هابط")
            else:
                scores[MarketState.RANGE] += 12
        else:
            scores[MarketState.RANGE] += 15
            reasons.append(f"ADX ضعيف ({adx:.1f}) - سوق متذبذب")

        # 2. Price Position (stronger weight for clear positioning)
        if price_vs_sma20 > 1.5 and price_vs_sma50 > 2:
            scores[MarketState.UPTREND] += 25
            reasons.append("السعر فوق المتوسطات")
        elif price_vs_sma20 > 0.5:
            scores[MarketState.UPTREND] += 10
        elif price_vs_sma20 < -1.5 and price_vs_sma50 < -2:
            scores[MarketState.DOWNTREND] += 25
            reasons.append("السعر تحت المتوسطات")
        elif price_vs_sma20 < -0.5:
            scores[MarketState.DOWNTREND] += 10
        else:
            scores[MarketState.RANGE] += 10

        # 3. RSI Extremes
        if rsi >= self.thresholds["rsi_extreme_overbought"]:
            scores[MarketState.NEAR_TOP] += 35
            reasons.append(f"RSI مفرط ({rsi:.1f}) - قرب القمة")
        elif rsi >= self.thresholds["rsi_overbought"]:
            scores[MarketState.NEAR_TOP] += 20
            scores[MarketState.UPTREND] += 10
            reasons.append(f"RSI مرتفع ({rsi:.1f})")
        elif rsi <= self.thresholds["rsi_extreme_oversold"]:
            scores[MarketState.NEAR_BOTTOM] += 35
            reasons.append(f"RSI منخفض جداً ({rsi:.1f}) - قرب القاع")
        elif rsi <= self.thresholds["rsi_oversold"]:
            scores[MarketState.NEAR_BOTTOM] += 20
            scores[MarketState.DOWNTREND] += 10
            reasons.append(f"RSI منخفض ({rsi:.1f})")

        # 4. Bollinger Band Position
        if bb_position >= 90:
            scores[MarketState.NEAR_TOP] += 20
            reasons.append("السعر عند الحد العلوي للبولينجر")
        elif bb_position <= 10:
            scores[MarketState.NEAR_BOTTOM] += 20
            reasons.append("السعر عند الحد السفلي للبولينجر")
        elif 30 <= bb_position <= 70:
            scores[MarketState.RANGE] += 10

        # 5. Price near Support/Resistance
        price_range = resistance - support
        if price_range > 0:
            price_position = (current_price - support) / price_range

            if price_position >= 0.9:
                scores[MarketState.NEAR_TOP] += 15
                reasons.append("السعر قريب من المقاومة")
            elif price_position <= 0.1:
                scores[MarketState.NEAR_BOTTOM] += 15
                reasons.append("السعر قريب من الدعم")

        # 6. MACD Momentum
        if macd_hist > 0 and indicators.get("macd", 0) > indicators.get(
            "macd_signal", 0
        ):
            scores[MarketState.UPTREND] += 10
        elif macd_hist < 0 and indicators.get("macd", 0) < indicators.get(
            "macd_signal", 0
        ):
            scores[MarketState.DOWNTREND] += 10

        # 7. Market Structure
        if structure["trend_structure"] == "bullish":
            scores[MarketState.UPTREND] += 15
        elif structure["trend_structure"] == "bearish":
            scores[MarketState.DOWNTREND] += 15
        elif structure["trend_structure"] == "ranging":
            scores[MarketState.RANGE] += 15

        # Determine final state
        best_state = max(scores, key=scores.get)
        max_score = scores[best_state]

        # Calculate confidence
        total_score = sum(scores.values())
        if total_score > 0:
            confidence = (max_score / total_score) * 100
        else:
            confidence = 50

        # Boost confidence if multiple signals agree
        if max_score >= 50:
            confidence = min(95, confidence + 10)

        reasoning = " | ".join(reasons[:3])  # Top 3 reasons

        return best_state, confidence, reasoning

    def _calculate_momentum(self, indicators: Dict) -> float:
        """حساب الزخم (-100 to +100)"""
        momentum = 0

        # RSI contribution
        rsi = indicators.get("rsi", 50)
        momentum += (rsi - 50) * 0.5  # -25 to +25

        # MACD contribution
        macd_hist = indicators.get("macd_hist", 0)
        if macd_hist != 0:
            # Normalize MACD
            momentum += np.clip(macd_hist * 100, -25, 25)

        # Price vs MA contribution
        price_vs_sma20 = indicators.get("price_vs_sma20", 0)
        momentum += np.clip(price_vs_sma20 * 2, -25, 25)

        # ADX direction contribution
        plus_di = indicators.get("plus_di", 0)
        minus_di = indicators.get("minus_di", 0)
        if plus_di + minus_di > 0:
            di_diff = (plus_di - minus_di) / (plus_di + minus_di) * 25
            momentum += di_diff

        return np.clip(momentum, -100, 100)

    def _calculate_adx_manual(
        self, df: pd.DataFrame, period: int = 14
    ) -> Dict:
        """حساب ADX و +DI و -DI يدوياً (بديل عن pandas_ta)"""
        try:
            high = df["high"].values
            low = df["low"].values
            close = df["close"].values
            n = len(df)

            if n < period + 1:
                return {"adx": 20, "plus_di": 0, "minus_di": 0}

            # True Range
            tr = np.zeros(n)
            plus_dm = np.zeros(n)
            minus_dm = np.zeros(n)

            for i in range(1, n):
                h_diff = high[i] - high[i - 1]
                l_diff = low[i - 1] - low[i]

                tr[i] = max(
                    high[i] - low[i],
                    abs(high[i] - close[i - 1]),
                    abs(low[i] - close[i - 1]),
                )

                plus_dm[i] = h_diff if (h_diff > l_diff and h_diff > 0) else 0
                minus_dm[i] = l_diff if (l_diff > h_diff and l_diff > 0) else 0

            # Smoothed averages (Wilder's smoothing)
            atr = np.zeros(n)
            smooth_plus = np.zeros(n)
            smooth_minus = np.zeros(n)

            atr[period] = np.mean(tr[1: period + 1])
            smooth_plus[period] = np.mean(plus_dm[1: period + 1])
            smooth_minus[period] = np.mean(minus_dm[1: period + 1])

            for i in range(period + 1, n):
                atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
                smooth_plus[i] = (
                    smooth_plus[i - 1] * (period - 1) + plus_dm[i]
                ) / period
                smooth_minus[i] = (
                    smooth_minus[i - 1] * (period - 1) + minus_dm[i]
                ) / period

            # +DI and -DI
            plus_di = np.zeros(n)
            minus_di = np.zeros(n)
            dx = np.zeros(n)

            for i in range(period, n):
                if atr[i] > 0:
                    plus_di[i] = (smooth_plus[i] / atr[i]) * 100
                    minus_di[i] = (smooth_minus[i] / atr[i]) * 100

                di_sum = plus_di[i] + minus_di[i]
                if di_sum > 0:
                    dx[i] = abs(plus_di[i] - minus_di[i]) / di_sum * 100

            # ADX (smoothed DX)
            adx = np.zeros(n)
            start = period * 2
            if start < n:
                adx[start] = np.mean(dx[period: start + 1])
                for i in range(start + 1, n):
                    adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

            final_adx = adx[-1] if not np.isnan(adx[-1]) else 20
            final_plus = plus_di[-1] if not np.isnan(plus_di[-1]) else 0
            final_minus = minus_di[-1] if not np.isnan(minus_di[-1]) else 0

            return {
                "adx": float(final_adx),
                "plus_di": float(final_plus),
                "minus_di": float(final_minus),
            }
        except Exception as e:
            self.logger.debug(f"Manual ADX calculation error: {e}")
            return {"adx": 20, "plus_di": 0, "minus_di": 0}

    def _calculate_rsi_manual(
        self, close: pd.Series, period: int = 14
    ) -> float:
        """حساب RSI يدوياً"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1] if not np.isnan(rsi.iloc[-1]) else 50

    def _calculate_atr_manual(
        self, df: pd.DataFrame, period: int = 14
    ) -> float:
        """حساب ATR يدوياً"""
        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr.iloc[-1] if not np.isnan(atr.iloc[-1]) else 0

    def _get_default_indicators(self, df: pd.DataFrame) -> Dict:
        """مؤشرات افتراضية في حالة الخطأ"""
        current_price = df["close"].iloc[-1] if len(df) > 0 else 0
        return {
            "rsi": 50,
            "adx": 20,
            "plus_di": 0,
            "minus_di": 0,
            "sma_20": current_price,
            "sma_50": current_price,
            "ema_9": current_price,
            "ema_21": current_price,
            "price_vs_sma20": 0,
            "price_vs_sma50": 0,
            "bb_upper": current_price * 1.02,
            "bb_lower": current_price * 0.98,
            "bb_mid": current_price,
            "bb_width": 0.04,
            "bb_position": 50,
            "atr": 0,
            "volatility": 0.02,
            "macd": 0,
            "macd_signal": 0,
            "macd_hist": 0,
            "volume_ratio": 1,
            "price_change_1d": 0,
            "price_change_5d": 0,
            "current_price": current_price,
        }

    def _undefined_result(self, reason: str) -> MarketStateResult:
        """نتيجة غير محددة"""
        return MarketStateResult(
            state=MarketState.UNDEFINED,
            confidence=0,
            trend_strength=0,
            momentum=0,
            volatility=0,
            support_level=0,
            resistance_level=0,
            reasoning=reason,
            indicators={},
        )

    def get_allowed_strategies(self, state: MarketState) -> List[str]:
        """
        يرجع الاستراتيجيات المسموحة حسب حالة السوق

        هذا هو State-Strategy Binding الأساسي
        """
        strategy_map = {
            MarketState.UPTREND: [
                "trend_following",
                "momentum_breakout",
                "pullback_entry",
                "mtfa_trend",
            ],
            MarketState.DOWNTREND: [
                "exit_only",
                "short_strategy",
                "reversal_watch",
            ],
            MarketState.RANGE: [
                "mean_reversion",
                "rsi_divergence",
                "bollinger_bounce",
                "range_scalping",
            ],
            MarketState.NEAR_TOP: [
                "exit_only",
                "reversal_pattern",
                "profit_protection",
            ],
            MarketState.NEAR_BOTTOM: [
                "reversal_pattern",
                "accumulation",
                "buy_the_dip",
                "bottom_fishing",
            ],
            MarketState.UNDEFINED: [
                "abstain",
            ],
        }

        return strategy_map.get(state, ["abstain"])


# Singleton instance
_market_state_detector = None


def get_market_state_detector(
    config: Optional[Dict] = None,
) -> MarketStateDetector:
    """الحصول على instance من MarketStateDetector"""
    global _market_state_detector
    if _market_state_detector is None:
        _market_state_detector = MarketStateDetector(config)
    return _market_state_detector
