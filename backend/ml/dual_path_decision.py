"""
Dual Path Decision System - نظام القرار المزدوج
نظامين (محافظ ومتوازن) يتعاونان لاتخاذ قرارات أفضل
"""

import logging
from typing import Dict, Any, Optional
from collections import deque

logger = logging.getLogger(__name__)


class SimpleLearner:
    """متعلم بسيط مع معاملات قابلة للتخصيص"""

    def __init__(
        self,
        name: str,
        learning_rate: float,
        min_sample: int,
        confidence_threshold: float,
    ):
        self.name = name
        self.learning_rate = learning_rate
        self.min_sample = min_sample
        self.confidence_threshold = confidence_threshold

        # تتبع الأداء
        self.recent_decisions = deque(maxlen=100)
        self.accuracy_history = []

        logger.info(
            f"✅ تهيئة {name}: LR={learning_rate}, MinSample={min_sample}, Threshold={confidence_threshold}"
        )

    def evaluate(
        self, signal_data: Dict, learned_patterns: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """تقييم الإشارة"""

        base_confidence = signal_data.get("confidence", 0.7)

        # إذا لا توجد أنماط متعلمة
        if (
            not learned_patterns
            or learned_patterns.get("sample_size", 0) < self.min_sample
        ):
            return {
                "action": (
                    "trade"
                    if base_confidence >= self.confidence_threshold
                    else "skip"
                ),
                "confidence": base_confidence,
                "reason": "no_learned_patterns",
                "learner": self.name,
            }

        # تطبيق الأنماط المتعلمة
        adjusted_confidence = self._apply_learned_patterns(
            signal_data, learned_patterns, base_confidence
        )

        # القرار
        action = (
            "trade"
            if adjusted_confidence >= self.confidence_threshold
            else "skip"
        )

        return {
            "action": action,
            "confidence": adjusted_confidence,
            "base_confidence": base_confidence,
            "adjustment": adjusted_confidence - base_confidence,
            "reason": "learned_patterns_applied",
            "learner": self.name,
        }

    def _apply_learned_patterns(
        self, signal: Dict, patterns: Dict, base_confidence: float
    ) -> float:
        """تطبيق الأنماط المتعلمة"""

        confidence = base_confidence
        indicators = signal.get("indicators", {})

        # فحص RSI
        rsi = indicators.get("rsi", 50)
        rsi_range = patterns.get("optimal_rsi_range", {})

        if rsi_range:
            if (
                rsi_range.get("optimal_low", 0)
                <= rsi
                <= rsi_range.get("optimal_high", 100)
            ):
                confidence += 0.1 * self.learning_rate
            elif rsi < rsi_range.get("min", 0) or rsi > rsi_range.get(
                "max", 100
            ):
                confidence -= 0.2 * self.learning_rate

        # فحص Volatility
        volatility = signal.get("volatility", 0)
        vol_range = patterns.get("optimal_volatility_range", {})

        if vol_range:
            if (
                vol_range.get("optimal_low", 0)
                <= volatility
                <= vol_range.get("optimal_high", 1)
            ):
                confidence += 0.05 * self.learning_rate
            elif volatility > vol_range.get("max", 1):
                confidence -= 0.15 * self.learning_rate

        # فحص Volume
        volume = signal.get("volume", 0)
        vol_range = patterns.get("optimal_volume_range", {})

        if vol_range and volume > 0:
            if (
                vol_range.get("optimal_low", 0)
                <= volume
                <= vol_range.get("optimal_high", float("inf"))
            ):
                confidence += 0.05 * self.learning_rate

        return max(0.0, min(1.0, confidence))

    def record_decision(self, decision: Dict, was_correct: bool):
        """تسجيل القرار والنتيجة"""

        self.recent_decisions.append(
            {
                "decision": decision,
                "was_correct": was_correct,
                "timestamp": decision.get("timestamp"),
            }
        )

        # حساب الدقة
        if len(self.recent_decisions) >= 20:
            recent_accuracy = (
                sum(
                    1
                    for d in list(self.recent_decisions)[-20:]
                    if d["was_correct"]
                )
                / 20
            )
            self.accuracy_history.append(recent_accuracy)

    def get_accuracy(self) -> float:
        """الحصول على الدقة الحالية"""

        if not self.recent_decisions:
            return 0.5

        recent = list(self.recent_decisions)[-50:]
        return sum(1 for d in recent if d["was_correct"]) / len(recent)


class DualPathDecision:
    """نظام قرار مزدوج: محافظ ومتوازن"""

    def __init__(self):
        # النظام 1: محافظ
        self.conservative = SimpleLearner(
            name="conservative",
            learning_rate=0.5,
            min_sample=50,
            confidence_threshold=0.75,
        )

        # النظام 2: متوازن
        self.balanced = SimpleLearner(
            name="balanced",
            learning_rate=1.0,
            min_sample=30,
            confidence_threshold=0.65,
        )

        # الأوزان (تتحدث تلقائياً)
        self.weights = {"conservative": 0.4, "balanced": 0.6}

        # تتبع الأداء
        self.performance_history = {"conservative": [], "balanced": []}

        logger.info("✅ تم تهيئة Dual Path Decision System")

    def decide(
        self, signal_data: Dict, learned_patterns: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """اتخاذ القرار بناءً على النظامين"""

        # قرار كل نظام
        c_decision = self.conservative.evaluate(signal_data, learned_patterns)
        b_decision = self.balanced.evaluate(signal_data, learned_patterns)

        # التصويت المرجح
        final_confidence = (
            c_decision["confidence"] * self.weights["conservative"]
            + b_decision["confidence"] * self.weights["balanced"]
        )

        # الإجماع
        both_agree = c_decision["action"] == b_decision["action"]

        # القرار النهائي
        if final_confidence >= 0.65:
            action = "trade"
            # تقليل الحجم إذا لا إجماع
            position_multiplier = 1.0 if both_agree else 0.7
        else:
            action = "skip"
            position_multiplier = 0.0

        decision = {
            "action": action,
            "confidence": final_confidence,
            "consensus": both_agree,
            "position_multiplier": position_multiplier,
            "conservative_decision": c_decision,
            "balanced_decision": b_decision,
            "weights": self.weights.copy(),
            "explanation": self._generate_explanation(
                c_decision, b_decision, both_agree
            ),
        }

        logger.debug(f"🎯 قرار مزدوج: {action} (ثقة: {
            final_confidence:.2%}, إجماع: {both_agree})")

        return decision

    def _generate_explanation(
        self, c_dec: Dict, b_dec: Dict, consensus: bool
    ) -> str:
        """توليد شرح للقرار"""

        if consensus and c_dec["action"] == "trade":
            return f"✅ إجماع على التداول (محافظ: {
                c_dec['confidence']:.2%}, متوازن: {
                b_dec['confidence']:.2%})"
        elif consensus and c_dec["action"] == "skip":
            return f"⛔ إجماع على التجنب (محافظ: {
                c_dec['confidence']:.2%}, متوازن: {
                b_dec['confidence']:.2%})"
        elif c_dec["action"] == "trade" and b_dec["action"] == "skip":
            return f"⚠️ اختلاف: محافظ يوافق ({
                c_dec['confidence']:.2%}) لكن متوازن يرفض ({
                b_dec['confidence']:.2%})"
        else:
            return f"⚠️ اختلاف: متوازن يوافق ({
                b_dec['confidence']:.2%}) لكن محافظ يرفض ({
                c_dec['confidence']:.2%})"

    def update_from_result(self, decision: Dict, trade_result: Dict):
        """تحديث النظامين بناءً على النتيجة"""

        was_correct = self._evaluate_decision_quality(decision, trade_result)

        # تحديث كل نظام
        self.conservative.record_decision(
            decision["conservative_decision"], was_correct
        )
        self.balanced.record_decision(
            decision["balanced_decision"], was_correct
        )

        # تحديث الأوزان تلقائياً
        self._auto_adjust_weights()

    def _evaluate_decision_quality(self, decision: Dict, result: Dict) -> bool:
        """هل كان القرار صحيح؟"""

        action = decision["action"]
        profit_pct = result.get("profit_pct", 0)

        if action == "trade":
            # قررنا التداول - هل ربحنا؟
            return profit_pct > 0
        else:
            # قررنا التجنب - كان سيخسر؟
            # في هذه الحالة نفترض أن التجنب كان صحيح إذا الثقة كانت منخفضة
            return True  # افتراضي للتجنب

    def _auto_adjust_weights(self):
        """تعديل تلقائي للأوزان بناءً على الأداء"""

        # حساب دقة كل نظام
        c_accuracy = self.conservative.get_accuracy()
        b_accuracy = self.balanced.get_accuracy()

        if c_accuracy == 0 and b_accuracy == 0:
            return  # لا توجد بيانات كافية

        # تحويل لأوزان
        total = c_accuracy + b_accuracy
        if total > 0:
            new_weights = {
                "conservative": c_accuracy / total,
                "balanced": b_accuracy / total,
            }

            # تحديث تدريجي (لا نغير بشكل مفاجئ)
            alpha = 0.1  # معدل التحديث
            self.weights["conservative"] = (1 - alpha) * self.weights[
                "conservative"
            ] + alpha * new_weights["conservative"]
            self.weights["balanced"] = (1 - alpha) * self.weights[
                "balanced"
            ] + alpha * new_weights["balanced"]

            logger.debug(f"⚖️ تحديث الأوزان: محافظ={
                self.weights['conservative']:.2%}, متوازن={
                self.weights['balanced']:.2%}")

    def get_performance_summary(self) -> Dict:
        """ملخص الأداء"""

        return {
            "conservative": {
                "accuracy": self.conservative.get_accuracy(),
                "weight": self.weights["conservative"],
                "decisions_count": len(self.conservative.recent_decisions),
            },
            "balanced": {
                "accuracy": self.balanced.get_accuracy(),
                "weight": self.weights["balanced"],
                "decisions_count": len(self.balanced.recent_decisions),
            },
            "total_decisions": len(self.conservative.recent_decisions)
            + len(self.balanced.recent_decisions),
        }
