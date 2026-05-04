#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Strategy Ensemble — تشغيل متعدد الاستراتيجيات بتسلسل ذكي
==========================================================
يشغّل جميع الاستراتيجيات على كل عملة، يجمع إشارات LONG فقط (Spot).
يعطي إشارة موحدة بدرجة ثقة مجمّعة — لا يتعارض مع المحرك الحالي.

الاستراتيجيات المُفعّلة:
  1. scalping_v8      — الأساس (trend continuation + breakout)
  2. momentum_breakout — كشف الانفجار السعري
  3. trend_following  — بداية الترند الصاعد
  4. rsi_divergence   — انعكاس الشموع
  5. volume_price_trend — تأكيد الاتجاه بالحجم

الاستراتيجيات المعطّلة (Short/Margin):
  - mean_reversion (يحتاج SHORT)
  - peak_valley_scalping (يحتاج SHORT)

التنفيذ:
  - كل استراتيجية تُفحَص بالتسلسل
  - إشارات LONG فقط تُجمع
  - درجة الثقة = متوسط مرجّح حسب وزن كل استراتيجية
  - الإشارة النهائية = أقوى إشارة + دعم الاستراتيجيات الأخرى
"""

import logging
from typing import Dict, List, Optional

from backend.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

# وزن كل استراتيجية (الأعلى = الأكثر تأثيراً)
STRATEGY_WEIGHTS = {
    "scalping_v8": 0.35,
    "momentum_breakout": 0.20,
    "trend_following": 0.20,
    "rsi_divergence": 0.15,
    "volume_price_trend": 0.10,
}


class StrategyEnsemble(BaseStrategy):
    """تشغيل متعدد الاستراتيجيات — LONG فقط (Spot)"""

    def __init__(self, strategies: List[BaseStrategy]):
        self._strategies = strategies
        self._name = "ensemble"

    @property
    def name(self) -> str:
        return self._name

    def detect_entry(self, df, context: Dict) -> Optional[Dict]:
        trend = context.get("trend", "NEUTRAL")

        # Spot only: LONG فقط — تجاهل الإشارات في اتجاه هابط
        if trend == "DOWN":
            return None

        signals = []
        for strategy in self._strategies:
            try:
                sig = strategy.detect_entry(df, context)
                if sig and sig.get("side", "").upper() == "LONG":
                    # إضافة وزن الاستراتيجية
                    weight = STRATEGY_WEIGHTS.get(strategy.name, 0.10)
                    sig["_weight"] = weight
                    sig["_strategy_name"] = strategy.name
                    signals.append(sig)
            except Exception as e:
                logger.debug(f"Strategy {strategy.name} error: {e}")

        if not signals:
            return None

        return self._aggregate(signals, trend)

    def _aggregate(self, signals: List[Dict], trend: str) -> Dict:
        total_weight = sum(s.get("_weight", 0.10) for s in signals)
        if total_weight == 0:
            total_weight = 1.0

        # متوسط مرجّح للسعر والدخول
        weighted_entry = (
            sum(
                float(s.get("entry_price", 0)) * s.get("_weight", 0.10) for s in signals
            )
            / total_weight
        )

        # متوسط مرجّح لدرجة الثقة
        weighted_confidence = (
            sum(
                float(s.get("confidence", 50)) * s.get("_weight", 0.10) for s in signals
            )
            / total_weight
        )

        # متوسط مرجّح للـ score
        weighted_score = (
            sum(float(s.get("score", 0)) * s.get("_weight", 0.10) for s in signals)
            / total_weight
        )

        # Stop Loss: الأكثر تحفظاً (أعلى SL)
        sl_prices = [
            float(s.get("stop_loss", 0)) for s in signals if s.get("stop_loss")
        ]
        stop_loss = max(sl_prices) if sl_prices else weighted_entry * 0.992

        # Take Profit: متوسط الأهداف
        tp_prices = [
            float(s.get("take_profit", 0)) for s in signals if s.get("take_profit")
        ]
        take_profit = (
            sum(tp_prices) / len(tp_prices) if tp_prices else weighted_entry * 1.015
        )

        # أسماء الاستراتيجيات المساندة
        supporting = [s.get("_strategy_name", "unknown") for s in signals]

        return {
            "side": "LONG",
            "entry_price": weighted_entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "score": round(weighted_score, 1),
            "confidence": round(min(95, weighted_confidence), 1),
            "strategy": "ensemble",
            "supporting_strategies": supporting,
            "strategy_count": len(signals),
            "trend": trend,
        }

    def get_market_trend(self, df) -> str:
        # استخدام V8 لتحديد الاتجاه (الأكثر موثوقية)
        for s in self._strategies:
            if "v8" in s.name.lower():
                return s.get_market_trend(df)
        return "NEUTRAL"

    def prepare_data(self, df):
        # تحضير البيانات لكل الاستراتيجيات
        result = df.copy()
        for s in self._strategies:
            try:
                result = s.prepare_data(result)
            except Exception:
                pass
        return result

    def get_config(self) -> Dict:
        for s in self._strategies:
            if "v8" in s.name.lower():
                return s.get_config()
        return {"timeframe": "1h", "sl_pct": 0.008, "max_positions": 5}

    def check_exit(self, df, position: Dict) -> Dict:
        for s in self._strategies:
            if "v8" in s.name.lower() and hasattr(s, "check_exit"):
                return s.check_exit(df, position)
        return {"should_exit": False, "reason": "HOLD"}
