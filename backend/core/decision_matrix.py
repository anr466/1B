#!/usr/bin/env python3
"""
Decision Matrix - مصفوفة القرارات المنطقية
===========================================

نظام واضح ومنطقي لاتخاذ قرارات الدخول والخروج
يحدد بوضوح متى يدخل النظام ومتى يخرج بناءً على معايير محددة
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    ENTER_LONG = "enter_long"
    ENTER_SHORT = "enter_short"
    EXIT_FULL = "exit_full"
    EXIT_PARTIAL = "exit_partial"
    HOLD = "hold"
    WAIT = "wait"


class ExitPriority(Enum):
    CRITICAL = "critical"  # خروج فوري
    HIGH = "high"  # خروج سريع
    MEDIUM = "medium"  # خروج عند الفرصة
    LOW = "low"  # مراجعة فقط


@dataclass
class MarketCondition:
    regime: str  # UP/DOWN/SIDEWAYS/VOLATILE
    quality: int  # 0-100 جودة السوق
    volatility: float  # مستوى التقلبات
    volume_strength: int  # 0-100 قوة الحجم
    trend_confidence: int  # 0-100 ثقة الاتجاه


@dataclass
class SignalStrength:
    technical_score: int  # 0-100 النقاط الفنية
    smart_money_score: int  # 0-100 نقاط الأموال الذكية
    confluence_score: int  # 0-100 نقاط التوافق
    timing_score: int  # 0-100 نقاط التوقيت
    overall_confidence: int  # 0-100 الثقة الإجمالية


@dataclass
class RiskAssessment:
    portfolio_risk: float  # 0-1 مخاطر المحفظة
    position_risk: float  # 0-1 مخاطر المركز
    market_risk: int  # 0-100 مخاطر السوق
    risk_reward_ratio: float  # نسبة المخاطرة للعائد
    max_loss_pct: float  # أقصى خسارة متوقعة


@dataclass
class DecisionResult:
    decision: DecisionType
    confidence: int  # 0-100
    reasoning: str
    entry_score: Optional[int] = None
    exit_priority: Optional[ExitPriority] = None
    position_size_pct: Optional[float] = None
    metadata: Optional[Dict] = None


class TradingDecisionMatrix:
    """
    مصفوفة القرارات الرئيسية للنظام
    تحدد بوضوح ومنطق متى يدخل النظام ومتى يخرج
    """

    def __init__(self, config: Dict = None):
        self.config = config or {}

        # معايير الدخول
        self.entry_thresholds = {
            "minimum_entry_score": self.config.get("min_entry_score", 75),
            "minimum_market_quality": self.config.get(
                "min_market_quality", 60
            ),
            "minimum_confluence": self.config.get("min_confluence", 65),
            "maximum_portfolio_risk": self.config.get(
                "max_portfolio_risk", 0.15
            ),
            "minimum_rr_ratio": self.config.get("min_rr_ratio", 1.8),
        }

        # أوزان معايير الدخول
        self.entry_weights = {
            "market_regime": 0.30,  # 30% - أهمية عالية
            "signal_quality": 0.25,  # 25% - أهمية عالية
            "smart_money": 0.20,  # 20% - أهمية متوسطة
            "risk_level": 0.15,  # 15% - أهمية متوسطة
            "timing": 0.10,  # 10% - أهمية منخفضة
        }

        # معايير الخروج
        self.exit_criteria = {
            "stop_loss_hit": {
                "priority": ExitPriority.CRITICAL,
                "exit_pct": 1.0,
            },
            "take_profit_hit": {
                "priority": ExitPriority.HIGH,
                "exit_pct": 0.7,
            },
            "strong_exit_signal": {
                "priority": ExitPriority.HIGH,
                "exit_pct": 0.8,
            },
            "market_deterioration": {
                "priority": ExitPriority.MEDIUM,
                "exit_pct": 0.5,
            },
            "time_limit_reached": {
                "priority": ExitPriority.LOW,
                "exit_pct": 1.0,
            },
            "profit_protection": {
                "priority": ExitPriority.MEDIUM,
                "exit_pct": 0.3,
            },
        }

        logger.info(
            "Decision Matrix initialized with entry threshold: {}".format(
                self.entry_thresholds["minimum_entry_score"]
            )
        )

    def evaluate_entry(
        self,
        market_condition: MarketCondition,
        signal_strength: SignalStrength,
        risk_assessment: RiskAssessment,
    ) -> DecisionResult:
        """
        تقييم قرار الدخول بناءً على المعايير المحددة
        """
        try:
            # 1. حساب نقاط كل معيار
            market_score = self._score_market_condition(market_condition)
            signal_score = signal_strength.overall_confidence
            smart_money_score = signal_strength.smart_money_score
            risk_score = self._score_risk_level(risk_assessment)
            timing_score = signal_strength.timing_score

            # 2. حساب النقاط الإجمالية بالأوزان
            entry_score = (
                market_score * self.entry_weights["market_regime"]
                + signal_score * self.entry_weights["signal_quality"]
                + smart_money_score * self.entry_weights["smart_money"]
                + risk_score * self.entry_weights["risk_level"]
                + timing_score * self.entry_weights["timing"]
            )

            # 3. فحص المعايير الأساسية
            rejections = self._check_entry_rejections(
                market_condition, signal_strength, risk_assessment, entry_score
            )

            if rejections:
                return DecisionResult(
                    decision=DecisionType.WAIT,
                    confidence=0,
                    reasoning=f"Entry rejected: {', '.join(rejections)}",
                    entry_score=int(entry_score),
                )

            # 4. تحديد نوع الدخول وحجم المركز
            if entry_score >= self.entry_thresholds["minimum_entry_score"]:
                decision_type = (
                    DecisionType.ENTER_LONG
                    if market_condition.regime in ["UP", "SIDEWAYS"]
                    else DecisionType.ENTER_SHORT
                )

                position_size = self._calculate_position_size(
                    entry_score, risk_assessment
                )

                return DecisionResult(
                    decision=decision_type,
                    confidence=int(entry_score),
                    reasoning=f"Entry approved with score {entry_score:.1f}",
                    entry_score=int(entry_score),
                    position_size_pct=position_size,
                    metadata={
                        "market_score": market_score,
                        "signal_score": signal_score,
                        "smart_money_score": smart_money_score,
                        "risk_score": risk_score,
                        "timing_score": timing_score,
                    },
                )
            else:
                return DecisionResult(
                    decision=DecisionType.WAIT,
                    confidence=int(entry_score),
                    reasoning=f"Entry score too low: {
                        entry_score:.1f} < {
                        self.entry_thresholds['minimum_entry_score']}",
                    entry_score=int(entry_score),
                )

        except Exception as e:
            logger.error(f"Entry evaluation error: {e}")
            return DecisionResult(
                decision=DecisionType.WAIT,
                confidence=0,
                reasoning=f"Evaluation error: {e}",
            )

    def evaluate_exit(
        self,
        position: Dict,
        current_market: MarketCondition,
        current_price: float,
    ) -> DecisionResult:
        """
        تقييم قرار الخروج للصفقات المفتوحة
        """
        try:
            position.get("entry_price", 0)
            stop_loss = position.get("stop_loss", 0)
            take_profit = position.get("take_profit", 0)
            position_type = position.get("position_type", "long")

            # 1. فحص الخروج الحرج (Stop Loss)
            if self._is_stop_loss_hit(current_price, stop_loss, position_type):
                return DecisionResult(
                    decision=DecisionType.EXIT_FULL,
                    confidence=100,
                    reasoning="Stop Loss hit - immediate exit",
                    exit_priority=ExitPriority.CRITICAL,
                )

            # 2. فحص جني الأرباح
            if take_profit and self._is_take_profit_hit(
                current_price, take_profit, position_type
            ):
                return DecisionResult(
                    decision=DecisionType.EXIT_PARTIAL,
                    confidence=90,
                    reasoning="Take Profit reached - partial exit",
                    exit_priority=ExitPriority.HIGH,
                    metadata={"exit_percentage": 70},
                )

            # 3. فحص إشارات الخروج الأخرى
            exit_signals = self._analyze_exit_signals(
                position, current_market, current_price
            )

            if exit_signals:
                strongest_signal = max(
                    exit_signals, key=lambda x: x["strength"]
                )

                if strongest_signal["strength"] >= 80:
                    return DecisionResult(
                        decision=DecisionType.EXIT_FULL,
                        confidence=strongest_signal["strength"],
                        reasoning=strongest_signal["reason"],
                        exit_priority=ExitPriority.HIGH,
                    )
                elif strongest_signal["strength"] >= 60:
                    return DecisionResult(
                        decision=DecisionType.EXIT_PARTIAL,
                        confidence=strongest_signal["strength"],
                        reasoning=strongest_signal["reason"],
                        exit_priority=ExitPriority.MEDIUM,
                        metadata={"exit_percentage": 50},
                    )

            # 4. لا يوجد إشارة خروج - استمرار
            return DecisionResult(
                decision=DecisionType.HOLD,
                confidence=75,
                reasoning="No exit signals - continue holding",
            )

        except Exception as e:
            logger.error(f"Exit evaluation error: {e}")
            return DecisionResult(
                decision=DecisionType.HOLD,
                confidence=0,
                reasoning=f"Exit evaluation error: {e}",
            )

    def _score_market_condition(self, market: MarketCondition) -> int:
        """تسجيل نقاط حالة السوق"""
        base_score = market.quality

        # مكافآت للظروف المناسبة
        if market.regime in ["UP", "DOWN"]:
            base_score += 15  # ترند واضح
        elif market.regime == "SIDEWAYS":
            base_score += 5  # جانبي مقبول

        if market.trend_confidence >= 70:
            base_score += 10

        if market.volume_strength >= 60:
            base_score += 5

        return min(100, base_score)

    def _score_risk_level(self, risk: RiskAssessment) -> int:
        """تسجيل نقاط مستوى المخاطر (أقل مخاطر = نقاط أكثر)"""
        risk_score = 100

        # خصم نقاط للمخاطر العالية
        if risk.portfolio_risk > 0.10:
            risk_score -= 30
        elif risk.portfolio_risk > 0.05:
            risk_score -= 15

        if risk.market_risk > 70:
            risk_score -= 25
        elif risk.market_risk > 50:
            risk_score -= 10

        if risk.risk_reward_ratio < 2.0:
            risk_score -= 20
        elif risk.risk_reward_ratio < 1.5:
            risk_score -= 35

        return max(0, risk_score)

    def _check_entry_rejections(
        self,
        market: MarketCondition,
        signal: SignalStrength,
        risk: RiskAssessment,
        entry_score: float,
    ) -> List[str]:
        """فحص أسباب رفض الدخول"""
        rejections = []

        if market.quality < self.entry_thresholds["minimum_market_quality"]:
            rejections.append(f"Market quality too low: {market.quality}")

        if (
            signal.confluence_score
            < self.entry_thresholds["minimum_confluence"]
        ):
            rejections.append(f"Confluence too low: {signal.confluence_score}")

        if (
            risk.portfolio_risk
            > self.entry_thresholds["maximum_portfolio_risk"]
        ):
            rejections.append(f"Portfolio risk too high: {
                risk.portfolio_risk:.2f}")

        if risk.risk_reward_ratio < self.entry_thresholds["minimum_rr_ratio"]:
            rejections.append(f"R:R ratio too low: {
                risk.risk_reward_ratio:.2f}")

        return rejections

    def _calculate_position_size(
        self, entry_score: float, risk: RiskAssessment
    ) -> float:
        """حساب حجم المركز بناءً على النقاط والمخاطر"""
        base_size = 0.05  # 5% أساسي

        # تعديل حسب قوة الإشارة
        if entry_score >= 90:
            size_multiplier = 1.5
        elif entry_score >= 85:
            size_multiplier = 1.3
        elif entry_score >= 80:
            size_multiplier = 1.1
        else:
            size_multiplier = 1.0

        # تعديل حسب المخاطر
        if risk.portfolio_risk > 0.08:
            size_multiplier *= 0.7
        elif risk.market_risk > 60:
            size_multiplier *= 0.8

        position_size = base_size * size_multiplier
        return min(0.10, max(0.02, position_size))  # بين 2%-10%

    def _is_stop_loss_hit(
        self, current_price: float, stop_loss: float, position_type: str
    ) -> bool:
        """فحص إذا تم ضرب الـ Stop Loss"""
        if stop_loss <= 0:
            return False

        if position_type.lower() == "long":
            return current_price <= stop_loss
        else:
            return current_price >= stop_loss

    def _is_take_profit_hit(
        self, current_price: float, take_profit: float, position_type: str
    ) -> bool:
        """فحص إذا تم الوصول للـ Take Profit"""
        if take_profit <= 0:
            return False

        if position_type.lower() == "long":
            return current_price >= take_profit
        else:
            return current_price <= take_profit

    def _analyze_exit_signals(
        self, position: Dict, market: MarketCondition, current_price: float
    ) -> List[Dict]:
        """تحليل إشارات الخروج المختلفة"""
        signals = []

        # إشارة تدهور السوق
        if market.quality < 40:
            signals.append(
                {
                    "reason": f"Market quality deteriorated: {market.quality}",
                    "strength": 70,
                }
            )

        # إشارة التقلبات العالية
        if market.volatility > 0.05:  # تقلبات أكثر من 5%
            signals.append(
                {
                    "reason": f"High volatility detected: {market.volatility:.2%}",
                    "strength": 60,
                }
            )

        # إشارة ضعف الحجم
        if market.volume_strength < 30:
            signals.append(
                {
                    "reason": f"Volume weakness: {market.volume_strength}",
                    "strength": 50,
                }
            )

        # فحص الوقت (مثال: أكثر من 24 ساعة)
        entry_time = position.get("created_at")
        if entry_time:
            if isinstance(entry_time, str):
                try:
                    entry_time = datetime.fromisoformat(
                        entry_time.replace("Z", "+00:00")
                    )
                except Exception:
                    entry_time = None
            if isinstance(entry_time, datetime):
                now_dt = (
                    datetime.now(entry_time.tzinfo)
                    if entry_time.tzinfo
                    else datetime.now()
                )
                hours_held = (now_dt - entry_time).total_seconds() / 3600
                if hours_held > 24:
                    signals.append(
                        {
                            "reason": f"Position held too long: {hours_held:.1f} hours",
                            "strength": 40,
                        }
                    )

        return signals
