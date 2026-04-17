#!/usr/bin/env python3
"""
Cognitive Decision Matrix — محسّنة مع DynamicWeightMatrix
==========================================================
تقييم الإشارات بشكل سياقي بناءً على:
1. نظام السوق (Regime-aware weights)
2. أداء الاستراتيجيات (Performance-based weights)
3. نوع العملة
4. ملف المخاطر
5. التأكيدات المتعددة
"""

import logging
from typing import Dict, List, Optional
from backend.core.dynamic_weight_matrix import DynamicWeightMatrix

logger = logging.getLogger(__name__)


class CognitiveDecisionMatrix:
    def __init__(self):
        # Dynamic Weight Matrix for adaptive scoring
        self.weight_matrix = DynamicWeightMatrix()

        # أوزان افتراضية (fallback)
        self.default_weights = {
            "trend_clarity": 0.20,
            "mtf_alignment": 0.20,
            "volume_confirmation": 0.15,
            "risk_reward_ratio": 0.20,
            "volatility_fit": 0.10,
            "coin_profile_fit": 0.10,
            "signal_quality": 0.05,
        }

    def evaluate(self, signal: Dict, context: Dict) -> Dict:
        regime = context.get("regime", "CHOPPY")
        signal_strategy = signal.get("strategy", "")

        # FIX: Get dynamic weights based on regime AND strategy performance
        weights = self.weight_matrix.get_weights(regime, signal_strategy)

        scores = {}
        scores["trend_clarity"] = self._score_trend_clarity(signal, context)
        scores["mtf_alignment"] = self._score_mtf_alignment(signal, context)
        scores["volume_confirmation"] = self._score_volume(signal, context)
        scores["risk_reward_ratio"] = self._score_risk_reward(signal, context)
        scores["volatility_fit"] = self._score_volatility_fit(signal, context)
        scores["coin_profile_fit"] = self._score_coin_profile(signal, context)
        scores["signal_quality"] = self._score_signal_quality(signal, context)

        final_score = sum(scores.get(k, 0) * weights.get(k, 0) for k in weights)

        # عقوبة إذا كانت التأكيدات ضعيفة
        confirmations = sum(
            [
                context.get("trend_confirmed_4h", True),
                context.get("trend_confirmed_macd", True),
                context.get("trend_confirmed_volume", True),
            ]
        )
        if confirmations < 2 and regime in ("STRONG_TREND", "WEAK_TREND"):
            final_score *= 0.85

        decision = self._make_decision(final_score, context)

        return {
            "score": round(final_score, 2),
            "scores": scores,
            "weights": {k: round(v, 3) for k, v in weights.items()},
            "decision": decision,
            "reason": self._generate_reason(scores, decision),
        }

    def update_strategy_performance(
        self, strategy: str, win: bool, profit: float, loss: float
    ):
        """
        تحديث أداء الاستراتيجية — يُستدعى من PerformanceTracker.
        """
        self.weight_matrix.update_strategy_performance(strategy, win, profit, loss)

    def get_strategy_health(self) -> Dict:
        """الحصول على تقرير صحة الاستراتيجيات"""
        return self.weight_matrix.get_strategy_health_report()

    def _score_trend_clarity(self, signal: Dict, context: Dict) -> float:
        trend = context.get("trend", "NEUTRAL")
        if signal["type"] == "LONG" and trend == "UP":
            return 90
        if signal["type"] == "SHORT" and trend == "DOWN":
            return 90
        if trend == "NEUTRAL":
            return 40
        return 20

    def _score_mtf_alignment(self, signal: Dict, context: Dict) -> float:
        # FIX: Actually calculate MTF alignment instead of passthrough
        trend = context.get("trend", "NEUTRAL")
        confirmed_4h = context.get("trend_confirmed_4h", False)
        confirmed_macd = context.get("trend_confirmed_macd", False)

        if trend == "NEUTRAL":
            return 50

        if confirmed_4h and confirmed_macd:
            return 90
        if confirmed_4h or confirmed_macd:
            return 70

        ema_alignment = context.get("ema_alignment", "MIXED")
        if "FULL" in ema_alignment:
            return 80
        if "PARTIAL" in ema_alignment:
            return 60
        return 50

    def _score_volume(self, signal: Dict, context: Dict) -> float:
        vol_ratio = context.get("volume_ratio", 1.0)
        if vol_ratio > 2.0:
            return 100
        if vol_ratio > 1.5:
            return 80
        if vol_ratio > 1.0:
            return 60
        return 30

    def _score_risk_reward(self, signal: Dict, context: Dict) -> float:
        entry = signal.get("entry_price", 0)
        sl = signal.get("stop_loss", 0)
        tp = signal.get("take_profit", 0)

        if entry == 0 or sl == 0 or tp == 0:
            return 50

        risk = abs(entry - sl)
        reward = abs(tp - entry)

        if risk == 0:
            return 50

        rr = reward / risk
        if rr >= 3.0:
            return 100
        if rr >= 2.0:
            return 80
        if rr >= 1.5:
            return 60
        return 30

    def _score_volatility_fit(self, signal: Dict, context: Dict) -> float:
        volatility = context.get("volatility", "MEDIUM")
        strategy = signal.get("strategy", "")

        if "Volatility" in strategy and volatility in ["HIGH", "VERY_HIGH"]:
            return 100
        if "Range" in strategy and volatility in ["LOW", "MEDIUM"]:
            return 90
        if "Trend" in strategy and volatility in ["MEDIUM", "HIGH"]:
            return 80
        if "Scalp" in strategy and volatility in ["LOW", "MEDIUM", "HIGH"]:
            return 75
        return 50

    def _score_coin_profile(self, signal: Dict, context: Dict) -> float:
        coin_type = context.get("coin_type", "MID_CAP")
        strategy = signal.get("strategy", "")

        if coin_type == "MAJOR" and "Trend" in strategy:
            return 95
        if coin_type == "MEME" and ("Range" in strategy or "Scalp" in strategy):
            return 90
        if coin_type == "VOLATILE" and "Volatility" in strategy:
            return 95
        return 70

    def _score_signal_quality(self, signal: Dict, context: Dict) -> float:
        """جودة الإشارة الأساسية — confidence من الوحدة"""
        return signal.get("confidence", 50)

    def _make_decision(self, score: float, context: Dict) -> str:
        regime = context.get("regime", "CHOPPY")

        # Balanced thresholds per regime
        if regime == "CHOPPY":
            enter_threshold = 75
            reduced_threshold = 60
        elif regime in ("WIDE_RANGE", "NARROW_RANGE"):
            enter_threshold = 65
            reduced_threshold = 50
        else:  # STRONG_TREND, WEAK_TREND
            enter_threshold = 65
            reduced_threshold = 50

        if score >= enter_threshold:
            return "ENTER"
        if score >= reduced_threshold:
            return "ENTER_REDUCED"
        if score >= 50:
            return "WATCH"
        return "REJECT"

    def _generate_reason(self, scores: Dict, decision: str) -> str:
        reasons = []
        for k, v in sorted(scores.items(), key=lambda x: x[1]):
            if v < 50:
                reasons.append(f"Low {k} ({v})")
            elif v > 80:
                reasons.append(f"Strong {k} ({v})")
        return f"{decision}: {'; '.join(reasons)}" if reasons else decision
