"""
Coin Scorer - تسجيل العملات
يعطي نقاط لكل عملة بناءً على معايير متعددة
"""

import pandas as pd
import logging
from typing import Dict
from ..analysis.market_regime_detector import MarketRegimeDetector
from ..analysis.volatility_analyzer import VolatilityAnalyzer
from ..analysis.liquidity_analyzer import LiquidityAnalyzer

logger = logging.getLogger(__name__)


class CoinScorer:
    """تسجيل العملات لتحديد الأفضل للتداول"""

    def __init__(self):
        self.logger = logger
        self.regime_detector = MarketRegimeDetector()
        self.volatility_analyzer = VolatilityAnalyzer()
        self.liquidity_analyzer = LiquidityAnalyzer()

    def score_coin(
        self, symbol: str, df: pd.DataFrame, market_condition: str = "NEUTRAL"
    ) -> Dict:
        """
        تسجيل عملة واحدة (0-100)

        Args:
            symbol: رمز العملة
            df: DataFrame مع OHLCV
            market_condition: حالة السوق العامة

        Returns:
            Dict مع النقاط والتفاصيل
        """
        try:
            if df is None or len(df) < 50:
                return self._get_zero_score(symbol, "بيانات غير كافية")

            total_score = 0
            details = {}

            # 1. السيولة (30 نقطة) - حرج
            liquidity = self.liquidity_analyzer.analyze(symbol, df)
            liquidity_score = liquidity["position_size_multiplier"] * 30
            total_score += liquidity_score
            details["liquidity"] = {
                "score": liquidity_score,
                "status": liquidity["liquidity_score"],
                "tradeable": liquidity["is_tradeable"],
            }

            # إذا سيولة ضعيفة - رفض مباشرة
            if not liquidity["is_tradeable"]:
                return self._get_zero_score(symbol, "سيولة ضعيفة")

            # 2. التقلب المناسب (25 نقطة)
            volatility = self.volatility_analyzer.analyze(df)
            vol_score = self._score_volatility(volatility, market_condition)
            total_score += vol_score
            details["volatility"] = {
                "score": vol_score,
                "regime": volatility["regime"],
                "atr_pct": volatility["atr_pct"],
            }

            # 3. الزخم (Momentum) (20 نقطة)
            momentum_score = self._calculate_momentum_score(df)
            total_score += momentum_score
            details["momentum"] = {
                "score": momentum_score,
                "value": self._calculate_momentum(df),
            }

            # 4. جودة الاتجاه (15 نقطة)
            trend_score = self._calculate_trend_quality_score(df)
            total_score += trend_score
            details["trend_quality"] = {"score": trend_score}

            # 5. Volume Profile (10 نقطة)
            volume_score = self._calculate_volume_score(df)
            total_score += volume_score
            details["volume"] = {"score": volume_score}

            return {
                "symbol": symbol,
                "total_score": round(total_score, 2),
                "rank": self._get_rank(total_score),
                "details": details,
                "is_tradeable": total_score >= 40,  # حد أدنى 40/100
            }

        except Exception as e:
            self.logger.error(f"Error scoring {symbol}: {e}")
            return self._get_zero_score(symbol, f"خطأ: {str(e)}")

    def _score_volatility(
        self, volatility: Dict, market_condition: str
    ) -> float:
        """
        تسجيل التقلب (0-25)

        التقلب المناسب يعتمد على حالة السوق:
        - Trending: نريد تقلب متوسط-عالي
        - Ranging: نريد تقلب منخفض-متوسط
        """
        regime = volatility["regime"]

        if "TRENDING" in market_condition:
            # في اتجاه - نفضل تقلب متوسط لعالي
            score_map = {
                "HIGH": 25,
                "MEDIUM": 20,
                "LOW": 10,
                "VERY_HIGH": 15,
                "VERY_LOW": 5,
            }
        elif "RANGING" in market_condition:
            # حركة جانبية - نفضل تقلب منخفض
            score_map = {
                "LOW": 25,
                "MEDIUM": 20,
                "HIGH": 10,
                "VERY_LOW": 15,
                "VERY_HIGH": 5,
            }
        else:
            # محايد - تقلب متوسط أفضل
            score_map = {
                "MEDIUM": 25,
                "HIGH": 20,
                "LOW": 20,
                "VERY_HIGH": 10,
                "VERY_LOW": 10,
            }

        return score_map.get(regime, 15)

    def _calculate_momentum(self, df: pd.DataFrame) -> float:
        """حساب الزخم (آخر 14 يوم)"""
        try:
            returns = df["close"].pct_change(14).iloc[-1]
            return float(returns) if not pd.isna(returns) else 0
        except Exception:
            return 0

    def _calculate_momentum_score(self, df: pd.DataFrame) -> float:
        """تسجيل الزخم (0-20)"""
        momentum = self._calculate_momentum(df)

        # زخم إيجابي أفضل
        if momentum > 0.10:  # +10%
            return 20
        elif momentum > 0.05:  # +5%
            return 15
        elif momentum > 0:  # إيجابي
            return 10
        elif momentum > -0.05:  # خسارة صغيرة
            return 5
        else:
            return 0

    def _calculate_trend_quality_score(self, df: pd.DataFrame) -> float:
        """
        تسجيل جودة الاتجاه (0-15)

        اتجاه جيد = أعلى سعر قريب من السعر الحالي
        """
        try:
            current_price = df["close"].iloc[-1]
            high_20 = df["high"].rolling(20).max().iloc[-1]

            # المسافة من أعلى سعر
            distance_from_high = (high_20 - current_price) / high_20

            if distance_from_high < 0.02:  # أقل من 2%
                return 15
            elif distance_from_high < 0.05:  # 2-5%
                return 10
            elif distance_from_high < 0.10:  # 5-10%
                return 5
            else:
                return 0

        except Exception:
            return 0

    def _calculate_volume_score(self, df: pd.DataFrame) -> float:
        """
        تسجيل Volume Profile (0-10)

        حجم تداول متزايد = إشارة قوة
        """
        try:
            recent_volume = df["volume"].rolling(5).mean().iloc[-1]
            avg_volume = df["volume"].rolling(20).mean().iloc[-1]

            ratio = recent_volume / avg_volume if avg_volume > 0 else 0

            if ratio > 1.5:  # +50% حجم
                return 10
            elif ratio > 1.2:  # +20% حجم
                return 7
            elif ratio > 1.0:  # فوق المتوسط
                return 5
            elif ratio > 0.8:  # قريب من المتوسط
                return 3
            else:
                return 0

        except Exception:
            return 0

    def _get_rank(self, score: float) -> str:
        """تصنيف العملة بناءً على النقاط"""
        if score >= 80:
            return "EXCELLENT"
        elif score >= 65:
            return "GOOD"
        elif score >= 50:
            return "FAIR"
        elif score >= 40:
            return "ACCEPTABLE"
        else:
            return "POOR"

    def _get_zero_score(self, symbol: str, reason: str) -> Dict:
        """نقاط صفر مع السبب"""
        return {
            "symbol": symbol,
            "total_score": 0,
            "rank": "REJECTED",
            "details": {"rejection_reason": reason},
            "is_tradeable": False,
        }
