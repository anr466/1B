#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام فلترة متقدم للعملات
يجمع بين الفلترة الذكية وتحليل الأداء التاريخي
"""

import logging
import pandas as pd
from typing import Dict, List

logger = logging.getLogger(__name__)


class AdvancedCoinFilter:
    """
    نظام فلترة متقدم للعملات

    يفحص:
    1. جودة البيانات
    2. السيولة والحجم
    3. التقلب المناسب
    4. الاتجاه والزخم
    5. الأداء التاريخي
    """

    def __init__(self):
        self.logger = logger

        # معايير الفلترة المُحسّنة
        self.criteria = {
            "min_volume_usd": 500_000,
            "min_data_quality": 0.90,
            "min_volatility": 0.005,
            "max_volatility": 0.15,
            "min_liquidity_score": 0.5,
            "min_trend_score": 0.4,
            "min_total_score": 50,
        }

        # قائمة العملات المستبعدة (بناءً على الأداء السيء)
        self.blacklist = set()

    def filter_coins(self, coin_data_list: List[Dict]) -> List[Dict]:
        """
        فلترة قائمة العملات

        Args:
            coin_data_list: قائمة بيانات العملات [{'symbol': str, 'data': DataFrame}]

        Returns:
            قائمة العملات المفلترة مع النقاط
        """
        filtered_coins = []

        for coin in coin_data_list:
            symbol = coin.get("symbol", "")
            df = coin.get("data")

            if symbol in self.blacklist:
                self.logger.debug(f"⛔ {symbol} في القائمة السوداء")
                continue

            if df is None or len(df) < 100:
                self.logger.debug(f"⚠️ {symbol} بيانات غير كافية")
                continue

            # حساب النقاط
            scores = self._calculate_scores(df)

            if scores["total"] >= self.criteria["min_total_score"]:
                filtered_coins.append(
                    {
                        "symbol": symbol,
                        "data": df,
                        "quality_score": scores["total"],
                        "scores": scores,
                    }
                )
                self.logger.debug(f"✅ {symbol} اجتاز ({
                    scores['total']:.1f}/100)")
            else:
                self.logger.debug(f"❌ {symbol} لم يجتاز ({
                    scores['total']:.1f}/100)")

        # ترتيب حسب النقاط
        filtered_coins.sort(key=lambda x: x["quality_score"], reverse=True)

        self.logger.info(f"📊 تم فلترة {
            len(filtered_coins)} عملة من {
            len(coin_data_list)}")

        return filtered_coins

    def _calculate_scores(self, df: pd.DataFrame) -> Dict:
        """حساب نقاط العملة"""
        scores = {}

        # 1. جودة البيانات
        scores["data_quality"] = self._score_data_quality(df) * 20

        # 2. السيولة
        scores["liquidity"] = self._score_liquidity(df) * 20

        # 3. التقلب
        scores["volatility"] = self._score_volatility(df) * 20

        # 4. الاتجاه
        scores["trend"] = self._score_trend(df) * 20

        # 5. الأداء التاريخي
        scores["performance"] = self._score_performance(df) * 20

        # المجموع
        scores["total"] = sum(
            [
                scores["data_quality"],
                scores["liquidity"],
                scores["volatility"],
                scores["trend"],
                scores["performance"],
            ]
        )

        return scores

    def _score_data_quality(self, df: pd.DataFrame) -> float:
        """تقييم جودة البيانات (0-1)"""
        # نسبة البيانات الكاملة
        total_cells = len(df) * 5  # OHLCV
        missing = (
            df[["open", "high", "low", "close", "volume"]].isna().sum().sum()
        )
        quality = 1 - (missing / total_cells) if total_cells > 0 else 0

        return min(1.0, quality)

    def _score_liquidity(self, df: pd.DataFrame) -> float:
        """تقييم السيولة (0-1)"""
        if "volume" not in df.columns:
            return 0

        avg_volume_usd = (df["volume"] * df["close"]).mean()

        if avg_volume_usd >= self.criteria["min_volume_usd"] * 2:
            return 1.0
        elif avg_volume_usd >= self.criteria["min_volume_usd"]:
            return 0.7
        elif avg_volume_usd >= self.criteria["min_volume_usd"] * 0.5:
            return 0.4
        else:
            return 0.2

    def _score_volatility(self, df: pd.DataFrame) -> float:
        """تقييم التقلب (0-1)"""
        returns = df["close"].pct_change().dropna()
        volatility = returns.std()

        # التقلب المثالي: 2-5%
        if 0.02 <= volatility <= 0.05:
            return 1.0
        elif 0.015 <= volatility <= 0.08:
            return 0.7
        elif (
            self.criteria["min_volatility"]
            <= volatility
            <= self.criteria["max_volatility"]
        ):
            return 0.5
        else:
            return 0.2

    def _score_trend(self, df: pd.DataFrame) -> float:
        """تقييم الاتجاه (0-1)"""
        # حساب SMA
        df["close"].rolling(20).mean()
        sma_50 = df["close"].rolling(50).mean()

        valid = sma_50.dropna()
        if len(valid) == 0:
            return 0.5

        # نسبة الأيام فوق SMA50
        above_sma = (df["close"].iloc[-len(valid):] > valid).sum() / len(
            valid
        )

        # قوة الاتجاه
        if above_sma >= 0.7:
            return 1.0
        elif above_sma >= 0.5:
            return 0.7
        elif above_sma >= 0.3:
            return 0.5
        else:
            return 0.3

    def _score_performance(self, df: pd.DataFrame) -> float:
        """تقييم الأداء التاريخي (0-1)"""
        returns = df["close"].pct_change().dropna()

        # نسبة الأيام الإيجابية
        positive_days = (
            (returns > 0).sum() / len(returns) if len(returns) > 0 else 0.5
        )

        # متوسط العائد
        avg_return = returns.mean()

        # Sharpe Ratio تقريبي
        sharpe = (avg_return / returns.std()) if returns.std() > 0 else 0

        score = 0
        score += positive_days * 0.4
        score += (0.5 + (avg_return * 100)) * 0.3  # تحويل العائد لمقياس
        score += min(1.0, max(0, (sharpe + 1) / 2)) * 0.3  # تحويل Sharpe

        return min(1.0, max(0, score))

    def add_to_blacklist(self, symbol: str):
        """إضافة عملة للقائمة السوداء"""
        self.blacklist.add(symbol)
        self.logger.info(f"⛔ تم إضافة {symbol} للقائمة السوداء")

    def remove_from_blacklist(self, symbol: str):
        """إزالة عملة من القائمة السوداء"""
        self.blacklist.discard(symbol)
        self.logger.info(f"✅ تم إزالة {symbol} من القائمة السوداء")

    def get_top_coins(
        self, coin_data_list: List[Dict], top_n: int = 10
    ) -> List[Dict]:
        """الحصول على أفضل العملات"""
        filtered = self.filter_coins(coin_data_list)
        return filtered[:top_n]
