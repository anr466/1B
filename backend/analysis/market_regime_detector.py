"""
Market Regime Detector - كاشف حالة السوق
يحدد ما إذا كان السوق في حالة trending, ranging, volatile, أو calm
"""

import pandas as pd
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class MarketRegimeDetector:
    """
    كشف حالة السوق (Market Regime)

    الحالات المحتملة:
    - TRENDING_VOLATILE: اتجاه قوي + تقلب عالي (أفضل للـ Momentum)
    - TRENDING_CALM: اتجاه قوي + تقلب منخفض (أفضل للـ Trend Following)
    - RANGING_TIGHT: حركة جانبية + تقلب منخفض (أفضل للـ Mean Reversion)
    - CHOPPY_VOLATILE: حركة عشوائية + تقلب عالي (تجنب التداول)
    - NEUTRAL: غير واضح
    """

    def __init__(self):
        self.logger = logger

        # عتبات ADX
        self.adx_trending_threshold = 25
        self.adx_ranging_threshold = 20

        # عتبات ATR (normalized)
        self.atr_high_threshold = 0.025  # 2.5%
        self.atr_low_threshold = 0.015  # 1.5%

        # عتبات Bollinger Bands Width
        self.bb_tight_threshold = 0.03  # 3%

    def detect_regime(self, df: pd.DataFrame) -> Dict:
        """
        كشف حالة السوق

        Args:
            df: DataFrame مع OHLCV

        Returns:
            Dict مع regime و metadata
        """
        try:
            if df is None or len(df) < 50:
                return {
                    "regime": "UNKNOWN",
                    "reason": "Insufficient data",
                    "confidence": 0,
                }

            # حساب المؤشرات
            adx = self._calculate_adx(df)
            atr_normalized = self._calculate_normalized_atr(df)
            bb_width = self._calculate_bb_width(df)

            # تصنيف الحالة
            regime, confidence = self._classify_regime(
                adx, atr_normalized, bb_width
            )

            return {
                "regime": regime,
                "adx": adx,
                "atr_pct": atr_normalized * 100,
                "bb_width_pct": bb_width * 100,
                "confidence": confidence,
                "suitable_strategies": self._get_suitable_strategies(regime),
            }

        except Exception as e:
            self.logger.error(f"Error detecting regime: {e}")
            return {"regime": "ERROR", "reason": str(e), "confidence": 0}

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        حساب ADX (Average Directional Index)

        ADX > 25: اتجاه قوي
        ADX < 20: حركة جانبية
        """
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]

            # True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # Directional Movement
            dm_plus = high - high.shift(1)
            dm_minus = low.shift(1) - low

            dm_plus[dm_plus < 0] = 0
            dm_minus[dm_minus < 0] = 0
            dm_plus[(dm_plus < dm_minus)] = 0
            dm_minus[(dm_minus < dm_plus)] = 0

            # Smoothed values
            atr = tr.rolling(window=period).mean()
            di_plus = 100 * (dm_plus.rolling(window=period).mean() / atr)
            di_minus = 100 * (dm_minus.rolling(window=period).mean() / atr)

            # ADX
            dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
            adx = dx.rolling(window=period).mean()

            return float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else 0

        except Exception as e:
            self.logger.error(f"Error calculating ADX: {e}")
            return 0

    def _calculate_normalized_atr(
        self, df: pd.DataFrame, period: int = 14
    ) -> float:
        """
        حساب ATR normalized (كنسبة من السعر)
        """
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]

            # True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # ATR
            atr = tr.rolling(window=period).mean()

            # Normalize بالسعر
            atr_normalized = atr / close

            return (
                float(atr_normalized.iloc[-1])
                if not pd.isna(atr_normalized.iloc[-1])
                else 0
            )

        except Exception as e:
            self.logger.error(f"Error calculating normalized ATR: {e}")
            return 0

    def _calculate_bb_width(
        self, df: pd.DataFrame, period: int = 20, std_dev: int = 2
    ) -> float:
        """
        حساب Bollinger Bands Width (كنسبة)

        Width صغير: السوق هادئ (tight range)
        Width كبير: السوق متقلب
        """
        try:
            close = df["close"]

            # Bollinger Bands
            sma = close.rolling(window=period).mean()
            std = close.rolling(window=period).std()

            upper = sma + (std_dev * std)
            lower = sma - (std_dev * std)

            # Width (normalized)
            width = (upper - lower) / sma

            return float(width.iloc[-1]) if not pd.isna(width.iloc[-1]) else 0

        except Exception as e:
            self.logger.error(f"Error calculating BB width: {e}")
            return 0

    def _classify_regime(
        self, adx: float, atr_normalized: float, bb_width: float
    ) -> tuple:
        """
        تصنيف حالة السوق بناءً على المؤشرات

        Returns:
            (regime_name, confidence)
        """
        confidence = 0

        # Trending + Volatile
        if (
            adx > self.adx_trending_threshold
            and atr_normalized > self.atr_high_threshold
        ):
            confidence = min((adx / 40) * 100, 100)
            return "TRENDING_VOLATILE", confidence

        # Trending + Calm
        elif (
            adx > self.adx_trending_threshold
            and atr_normalized < self.atr_low_threshold
        ):
            confidence = min((adx / 35) * 100, 100)
            return "TRENDING_CALM", confidence

        # Ranging + Tight
        elif (
            adx < self.adx_ranging_threshold
            and bb_width < self.bb_tight_threshold
        ):
            confidence = min((1 - adx / 30) * 100, 100)
            return "RANGING_TIGHT", confidence

        # Choppy + Volatile (سيء)
        elif (
            adx < self.adx_ranging_threshold
            and atr_normalized > self.atr_high_threshold
        ):
            confidence = 70
            return "CHOPPY_VOLATILE", confidence

        # Neutral
        else:
            confidence = 50
            return "NEUTRAL", confidence

    def _get_suitable_strategies(self, regime: str) -> list:
        """
        الاستراتيجيات المناسبة لكل حالة سوق
        """
        strategy_map = {
            "TRENDING_VOLATILE": ["MomentumBreakout", "TrendFollowing"],
            "TRENDING_CALM": ["TrendFollowing", "SwingTrading"],
            "RANGING_TIGHT": ["MeanReversion", "SupportResistance"],
            "CHOPPY_VOLATILE": [],  # تجنب التداول
            "NEUTRAL": ["VolatilityBreakout", "SmartMoney"],
        }

        return strategy_map.get(regime, [])

    def get_regime_description(self, regime: str) -> str:
        """
        وصف نصي لحالة السوق
        """
        descriptions = {
            "TRENDING_VOLATILE": "اتجاه قوي مع تقلب عالي - مناسب للمومنتم",
            "TRENDING_CALM": "اتجاه قوي مع استقرار - مناسب لمتابعة الاتجاه",
            "RANGING_TIGHT": "حركة جانبية ضيقة - مناسب للمين ريفيرجن",
            "CHOPPY_VOLATILE": "حركة عشوائية متقلبة - تجنب التداول",
            "NEUTRAL": "غير واضح - استخدم استراتيجيات محايدة",
            "UNKNOWN": "بيانات غير كافية",
            "ERROR": "خطأ في التحليل",
        }

        return descriptions.get(regime, "غير معروف")
