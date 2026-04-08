#!/usr/bin/env python3
"""
Cognitive Decision Matrix
Evaluates trading signals contextually based on market regime, coin type, and risk profile.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class CognitiveDecisionMatrix:
    def __init__(self):
        self.weights = {
            "trend_clarity": 0.20,
            "mtf_alignment": 0.25,
            "volume_confirmation": 0.15,
            "risk_reward_ratio": 0.20,
            "volatility_fit": 0.10,
            "coin_profile_fit": 0.10,
        }

    def evaluate(self, signal: Dict, context: Dict) -> Dict:
        scores = {}

        scores["trend_clarity"] = self._score_trend_clarity(signal, context)
        scores["mtf_alignment"] = self._score_mtf_alignment(signal, context)
        scores["volume_confirmation"] = self._score_volume(signal, context)
        scores["risk_reward_ratio"] = self._score_risk_reward(signal, context)
        scores["volatility_fit"] = self._score_volatility_fit(signal, context)
        scores["coin_profile_fit"] = self._score_coin_profile(signal, context)

        final_score = sum(scores[k] * self.weights[k] for k in scores)

        decision = self._make_decision(final_score, context)

        return {
            "score": round(final_score, 2),
            "scores": scores,
            "decision": decision,
            "reason": self._generate_reason(scores, decision),
        }

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
        mtf_score = context.get("mtf_score", 50)
        return mtf_score

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

    def _make_decision(self, score: float, context: Dict) -> str:
        if score >= 80:
            return "ENTER"
        if score >= 65:
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
