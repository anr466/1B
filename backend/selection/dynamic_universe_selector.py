"""
Dynamic Universe Selector - اختيار ديناميكي للعملات
يختار أفضل 15-20 عملة للتداول بناءً على حالة السوق
"""

import logging
from typing import List, Dict
from .coin_scorer import CoinScorer
from ..utils.data_provider import DataProvider

logger = logging.getLogger(__name__)


class DynamicUniverseSelector:
    """اختيار ديناميكي للعملات القابلة للتداول"""

    def __init__(self):
        self.logger = logger
        self.coin_scorer = CoinScorer()
        self.data_provider = DataProvider()

        # قائمة كاملة للعملات المحتملة
        self.all_coins = [
            "BTC/USDT",
            "ETH/USDT",
            "BNB/USDT",
            "XRP/USDT",
            "ADA/USDT",
            "SOL/USDT",
            "DOT/USDT",
            "DOGE/USDT",
            "MATIC/USDT",
            "LTC/USDT",
            "LINK/USDT",
            "UNI/USDT",
            "ATOM/USDT",
            "ETC/USDT",
            "XLM/USDT",
            "ALGO/USDT",
            "VET/USDT",
            "FIL/USDT",
            "TRX/USDT",
            "AVAX/USDT",
            "NEAR/USDT",
            "APT/USDT",
            "ARB/USDT",
            "OP/USDT",
            "INJ/USDT",
        ]

    def select_universe(
        self, market_condition: str = "NEUTRAL", max_coins: int = 20
    ) -> List[Dict]:
        """
        اختيار أفضل العملات

        Args:
            market_condition: حالة السوق العامة
            max_coins: الحد الأقصى للعملات

        Returns:
            قائمة بالعملات المختارة مع نقاطها
        """
        self.logger.info(f"🔍 اختيار العملات - حالة السوق: {market_condition}")

        candidates = []

        # تسجيل جميع العملات
        for symbol in self.all_coins:
            try:
                # جلب البيانات
                df = self.data_provider.get_historical_data(
                    symbol, "1d", limit=90
                )

                if df is None or len(df) < 50:
                    continue

                # تسجيل العملة
                score_result = self.coin_scorer.score_coin(
                    symbol, df, market_condition
                )

                if score_result["is_tradeable"]:
                    candidates.append(score_result)
                    self.logger.info(
                        f"  ✅ {symbol}: {score_result['total_score']:.1f}/100 ({score_result['rank']})"
                    )
                else:
                    self.logger.debug(f"  ❌ {symbol}: رفض - {
                        score_result['details'].get(
                            'rejection_reason',
                            'نقاط منخفضة')}")

            except Exception as e:
                self.logger.warning(f"  ⚠️ {symbol}: خطأ - {e}")

        # ترتيب حسب النقاط
        candidates = sorted(
            candidates, key=lambda x: x["total_score"], reverse=True
        )

        # اختيار الأفضل
        selected = candidates[:max_coins]

        self.logger.info(
            f"\n✅ تم اختيار {len(selected)} عملة من {len(self.all_coins)}"
        )

        return selected

    def get_universe_summary(self, selected_universe: List[Dict]) -> Dict:
        """ملخص للعملات المختارة"""
        if not selected_universe:
            return {"total": 0, "avg_score": 0, "distribution": {}}

        total = len(selected_universe)
        avg_score = sum(c["total_score"] for c in selected_universe) / total

        # توزيع الرتب
        distribution = {}
        for coin in selected_universe:
            rank = coin["rank"]
            distribution[rank] = distribution.get(rank, 0) + 1

        return {
            "total_selected": total,
            "avg_score": round(avg_score, 2),
            "distribution": distribution,
            "top_3": [c["symbol"] for c in selected_universe[:3]],
        }
