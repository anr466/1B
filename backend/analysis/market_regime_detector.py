"""
Market Regime Detector — كاشف حالة السوق الموحد
================================================
يوفر نسختين متكاملتين:
1. SimpleRegimeDetector — كشف بإطار زمني واحد (للتحليل السريع)
2. MarketRegimeDetector — كشف متعدد الأطر الزمنية (1h, 4h, 1d)

الحالات (Single-TF):
  TRENDING_VOLATILE, TRENDING_CALM, RANGING_TIGHT, CHOPPY_VOLATILE, NEUTRAL

الحالات (Multi-TF):
  BULL_STRONG, BULL_WEAK, NEUTRAL, BEAR_WEAK, BEAR_STRONG, HIGH_VOLATILITY
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# ============================================================
# SimpleRegimeDetector — كشف بإطار زمني واحد
# ============================================================


class SimpleRegimeDetector:
    """كشف حالة السوق بإطار زمني واحد"""

    def __init__(self):
        self.logger = logger
        self.adx_trending_threshold = 25
        self.adx_ranging_threshold = 20
        self.atr_high_threshold = 0.025
        self.atr_low_threshold = 0.015
        self.bb_tight_threshold = 0.03

    def detect_regime(self, df: pd.DataFrame) -> Dict:
        try:
            if df is None or len(df) < 50:
                return {
                    "regime": "UNKNOWN",
                    "reason": "Insufficient data",
                    "confidence": 0,
                }

            adx = self._calculate_adx(df)
            atr_normalized = self._calculate_normalized_atr(df)
            bb_width = self._calculate_bb_width(df)
            regime, confidence = self._classify_regime(adx, atr_normalized, bb_width)

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
        try:
            high, low, close = df["high"], df["low"], df["close"]
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            dm_plus = high - high.shift(1)
            dm_minus = low.shift(1) - low
            dm_plus[dm_plus < 0] = 0
            dm_minus[dm_minus < 0] = 0
            dm_plus[(dm_plus < dm_minus)] = 0
            dm_minus[(dm_minus < dm_plus)] = 0

            atr = tr.rolling(window=period).mean()
            di_plus = 100 * (dm_plus.rolling(window=period).mean() / atr)
            di_minus = 100 * (dm_minus.rolling(window=period).mean() / atr)
            dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
            adx = dx.rolling(window=period).mean()

            return float(adx.iloc[-1]) if not pd.isna(adx.iloc[-1]) else 0
        except Exception as e:
            self.logger.error(f"Error calculating ADX: {e}")
            return 0

    def _calculate_normalized_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        try:
            high, low, close = df["high"], df["low"], df["close"]
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
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
        try:
            close = df["close"]
            sma = close.rolling(window=period).mean()
            std = close.rolling(window=period).std()
            upper = sma + (std_dev * std)
            lower = sma - (std_dev * std)
            width = (upper - lower) / sma
            return float(width.iloc[-1]) if not pd.isna(width.iloc[-1]) else 0
        except Exception as e:
            self.logger.error(f"Error calculating BB width: {e}")
            return 0

    def _classify_regime(
        self, adx: float, atr_normalized: float, bb_width: float
    ) -> tuple:
        if (
            adx > self.adx_trending_threshold
            and atr_normalized > self.atr_high_threshold
        ):
            return "TRENDING_VOLATILE", min((adx / 40) * 100, 100)
        elif (
            adx > self.adx_trending_threshold
            and atr_normalized < self.atr_low_threshold
        ):
            return "TRENDING_CALM", min((adx / 35) * 100, 100)
        elif adx < self.adx_ranging_threshold and bb_width < self.bb_tight_threshold:
            return "RANGING_TIGHT", min((1 - adx / 30) * 100, 100)
        elif (
            adx < self.adx_ranging_threshold
            and atr_normalized > self.atr_high_threshold
        ):
            return "CHOPPY_VOLATILE", 70
        else:
            return "NEUTRAL", 50

    def _get_suitable_strategies(self, regime: str) -> list:
        strategy_map = {
            "TRENDING_VOLATILE": ["MomentumBreakout", "TrendFollowing"],
            "TRENDING_CALM": ["TrendFollowing", "SwingTrading"],
            "RANGING_TIGHT": ["MeanReversion", "SupportResistance"],
            "CHOPPY_VOLATILE": [],
            "NEUTRAL": ["VolatilityBreakout", "SmartMoney"],
        }
        return strategy_map.get(regime, [])

    def get_regime_description(self, regime: str) -> str:
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


# ============================================================
# MarketRegimeDetector — كشف متعدد الأطر الزمنية
# ============================================================


class MarketRegimeDetector:
    """كشف حالة السوق باستخدام تحليل متعدد الأطر الزمنية"""

    def detect_regime(
        self,
        df_1h: pd.DataFrame,
        df_4h: pd.DataFrame = None,
        df_1d: pd.DataFrame = None,
    ) -> dict:
        if df_1h is None or len(df_1h) < 100:
            return self._default_regime()

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

        adx = self._calculate_adx(df_1h)
        atr_pct = self._calculate_atr_pct(df_1h)
        rsi = self._calculate_rsi(df_1h)
        momentum = rsi - 50
        trend_score = self._composite_trend_score(trend_1h, trend_4h, trend_1d)
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
        high, low, close = df["high"], df["low"], df["close"]
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
        return (
            mapping.get(t_1h, 0) * 0.3
            + mapping.get(t_4h, 0) * 0.4
            + mapping.get(t_1d, 0) * 0.3
        )

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
        strategy_map = {
            "BULL_STRONG": {"long": ["trend_cont", "breakout"], "short": ["breakdown"]},
            "BULL_WEAK": {"long": ["breakout"], "short": []},
            "NEUTRAL": {"long": ["breakout"], "short": []},
            "BEAR_WEAK": {"long": [], "short": ["trend_cont_short"]},
            "BEAR_STRONG": {"long": [], "short": ["trend_cont_short", "breakdown"]},
            "HIGH_VOLATILITY": {"long": [], "short": []},
        }
        allowed = strategy_map.get(regime, {"long": [], "short": []})
        result = []
        if spot_enabled:
            result.extend(allowed["long"])
        if margin_enabled:
            result.extend(allowed["short"])
        return result

    def get_position_size_multiplier(self, regime: str) -> float:
        return {
            "BULL_STRONG": 1.0,
            "BULL_WEAK": 0.7,
            "NEUTRAL": 0.5,
            "BEAR_WEAK": 0.7,
            "BEAR_STRONG": 1.0,
            "HIGH_VOLATILITY": 0.3,
        }.get(regime, 0.5)

    def get_stop_loss_multiplier(self, regime: str) -> float:
        return {
            "BULL_STRONG": 1.0,
            "BULL_WEAK": 1.2,
            "NEUTRAL": 1.5,
            "BEAR_WEAK": 1.2,
            "BEAR_STRONG": 1.0,
            "HIGH_VOLATILITY": 2.0,
        }.get(regime, 1.5)
