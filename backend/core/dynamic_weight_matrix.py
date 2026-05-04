#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dynamic Weight Matrix — مصفوفة الأوزان التكيفية
================================================
بدلاً من الأوزان الثابتة، تعدل هذه المصفوفة أوزان التقييم بناءً على:
1. نظام السوق الحالي (Regime-aware)
2. أداء الاستراتيجيات السابق (Performance-based)
3. ظروف السوق الحالية (Volatility, Volume)

هذا يسمح للنظام بالتكيف مع تغير ظروف السوق تلقائياً.
"""

from typing import Dict, List, Optional
import time
import logging

logger = logging.getLogger(__name__)


class DynamicWeightMatrix:
    """
    يدير أوزان التقييم بشكل ديناميكي بناءً على أداء السوق والاستراتيجيات.
    """

    def __init__(self):
        # الأوزان الأساسية لكل نظام
        self.base_regime_weights = {
            "STRONG_TREND": {
                "trend_clarity": 0.25,
                "mtf_alignment": 0.20,
                "volume_confirmation": 0.15,
                "risk_reward_ratio": 0.15,
                "volatility_fit": 0.10,
                "coin_profile_fit": 0.10,
                "signal_quality": 0.05,
            },
            "WEAK_TREND": {
                "trend_clarity": 0.15,
                "mtf_alignment": 0.25,
                "volume_confirmation": 0.20,
                "risk_reward_ratio": 0.15,
                "volatility_fit": 0.10,
                "coin_profile_fit": 0.10,
                "signal_quality": 0.05,
            },
            "WIDE_RANGE": {
                "trend_clarity": 0.10,
                "mtf_alignment": 0.15,
                "volume_confirmation": 0.15,
                "risk_reward_ratio": 0.25,
                "volatility_fit": 0.15,
                "coin_profile_fit": 0.10,
                "signal_quality": 0.10,
            },
            "NARROW_RANGE": {
                "trend_clarity": 0.10,
                "mtf_alignment": 0.15,
                "volume_confirmation": 0.10,
                "risk_reward_ratio": 0.30,
                "volatility_fit": 0.15,
                "coin_profile_fit": 0.10,
                "signal_quality": 0.10,
            },
            "CHOPPY": {
                "trend_clarity": 0.05,
                "mtf_alignment": 0.10,
                "volume_confirmation": 0.10,
                "risk_reward_ratio": 0.35,
                "volatility_fit": 0.20,
                "coin_profile_fit": 0.10,
                "signal_quality": 0.10,
            },
        }

        # أداء الاستراتيجيات (يتم تحديثه بواسطة PerformanceTracker)
        self.strategy_performance: Dict[str, Dict] = {
            "Trend Pullback": {
                "win_rate": 0.50,
                "profit_factor": 1.0,
                "trades": 0,
                "total_profit": 0.0,
                "total_loss": 0.0,
            },
            "Trend Breakout": {
                "win_rate": 0.50,
                "profit_factor": 1.0,
                "trades": 0,
                "total_profit": 0.0,
                "total_loss": 0.0,
            },
            "Trend Pullback Short": {
                "win_rate": 0.50,
                "profit_factor": 1.0,
                "trades": 0,
                "total_profit": 0.0,
                "total_loss": 0.0,
            },
            "Trend Breakdown": {
                "win_rate": 0.50,
                "profit_factor": 1.0,
                "trades": 0,
                "total_profit": 0.0,
                "total_loss": 0.0,
            },
            "Range Support Bounce": {
                "win_rate": 0.50,
                "profit_factor": 1.0,
                "trades": 0,
                "total_profit": 0.0,
                "total_loss": 0.0,
            },
            "Range Resistance Rejection": {
                "win_rate": 0.50,
                "profit_factor": 1.0,
                "trades": 0,
                "total_profit": 0.0,
                "total_loss": 0.0,
            },
            "Volatility Breakout": {
                "win_rate": 0.50,
                "profit_factor": 1.0,
                "trades": 0,
                "total_profit": 0.0,
                "total_loss": 0.0,
            },
            "Volatility Breakdown": {
                "win_rate": 0.50,
                "profit_factor": 1.0,
                "trades": 0,
                "total_profit": 0.0,
                "total_loss": 0.0,
            },
            "Micro Scalp Support": {
                "win_rate": 0.50,
                "profit_factor": 1.0,
                "trades": 0,
                "total_profit": 0.0,
                "total_loss": 0.0,
            },
            "Micro Scalp Resistance": {
                "win_rate": 0.50,
                "profit_factor": 1.0,
                "trades": 0,
                "total_profit": 0.0,
                "total_loss": 0.0,
            },
        }

        # آخر تحديث للأوزان
        self._last_update = time.time()
        self._update_interval = 300  # تحديث كل 5 دقائق

    def get_weights(self, regime: str, signal_strategy: str = None) -> Dict[str, float]:
        """
        الحصول على الأوزان المكيفة للنظام والاستراتيجية الحالية.

        Args:
            regime: نظام السوق الحالي
            signal_strategy: اسم الاستراتيجية (اختياري)

        Returns:
            قاموس بالأوزان المكيفة (مجموعها = 1.0)
        """
        # 1. الحصول على الأوزان الأساسية للنظام
        base_weights = self.base_regime_weights.get(
            regime, self.base_regime_weights["CHOPPY"]
        ).copy()

        # 2. تعديل الأوزان بناءً على أداء الاستراتيجية
        if signal_strategy and signal_strategy in self.strategy_performance:
            perf = self.strategy_performance[signal_strategy]
            performance_modifier = self._calculate_performance_modifier(perf)
            base_weights = self._apply_performance_modifier(
                base_weights, performance_modifier, regime
            )

        # 3. تطبيع الأوزان (مجموعها = 1.0)
        total = sum(base_weights.values())
        if total > 0:
            base_weights = {k: v / total for k, v in base_weights.items()}

        return base_weights

    def update_strategy_performance(
        self, strategy: str, win: bool, profit: float, loss: float
    ):
        """
        تحديث أداء استراتيجية بناءً على نتيجة صفقة.

        Args:
            strategy: اسم الاستراتيجية
            win: هل كانت الصفقة رابحة؟
            profit: مبلغ الربح (إذا كانت رابحة)
            loss: مبلغ الخسارة (إذا كانت خاسرة)
        """
        if strategy not in self.strategy_performance:
            self.strategy_performance[strategy] = {
                "win_rate": 0.50,
                "profit_factor": 1.0,
                "trades": 0,
                "total_profit": 0.0,
                "total_loss": 0.0,
            }

        perf = self.strategy_performance[strategy]
        perf["trades"] += 1

        if win:
            perf["total_profit"] = perf.get("total_profit", 0.0) + profit
        else:
            perf["total_loss"] = perf.get("total_loss", 0.0) + abs(loss)

        # حساب Win Rate (بسيط — يحتاج لبيانات أكثر)
        # في الواقع، يجب تتبع كل صفقة على حدة
        if perf["trades"] >= 10:  # نبدأ التعديل بعد 10 صفقات على الأقل
            if perf["total_loss"] > 0:
                perf["profit_factor"] = perf["total_profit"] / perf["total_loss"]
            else:
                perf["profit_factor"] = (
                    perf["total_profit"] if perf["total_profit"] > 0 else 1.0
                )

            # تقدير Win Rate من Profit Factor (تقريبي)
            if perf["profit_factor"] > 2.0:
                perf["win_rate"] = min(
                    0.80, 0.50 + (perf["profit_factor"] - 1.0) * 0.15
                )
            elif perf["profit_factor"] > 1.0:
                perf["win_rate"] = 0.50 + (perf["profit_factor"] - 1.0) * 0.10
            else:
                perf["win_rate"] = max(
                    0.20, 0.50 - (1.0 - perf["profit_factor"]) * 0.15
                )

        logger.debug(
            f"Updated {strategy}: trades={perf['trades']}, "
            f"win_rate={perf['win_rate']:.2f}, pf={perf['profit_factor']:.2f}"
        )

    def _calculate_performance_modifier(self, perf: Dict) -> float:
        """
        حساب معامل التعديل بناءً على الأداء.
        يعود بقيمة بين 0.5 (أداء سيء) و 1.5 (أداء ممتاز).
        """
        trades = perf.get("trades", 0)
        if trades < 10:
            return 1.0  # لا تعديل قبل 10 صفقات

        win_rate = perf.get("win_rate", 0.50)
        profit_factor = perf.get("profit_factor", 1.0)

        # دمج Win Rate و Profit Factor
        score = (win_rate * 0.4) + (min(profit_factor / 2.0, 1.0) * 0.6)

        # تحويل إلى معامل (0.5 - 1.5)
        modifier = 0.5 + (score * 1.0)
        return max(0.5, min(1.5, modifier))

    def _apply_performance_modifier(
        self, weights: Dict, modifier: float, regime: str
    ) -> Dict:
        """
        تطبيق معامل الأداء على الأوزان.
        الاستراتيجيات الأفضل تحصل على وزن أعلى في 'signal_quality' و 'risk_reward_ratio'.
        """
        if modifier > 1.2:
            # أداء ممتاز — زيادة وزن signal_quality و risk_reward
            weights["signal_quality"] *= modifier
            weights["risk_reward_ratio"] *= 1.1
        elif modifier < 0.8:
            # أداء سيء — تقليل وزن signal_quality وزيادة volume_confirmation
            weights["signal_quality"] *= modifier
            weights["volume_confirmation"] *= 1.2

        return weights

    def get_strategy_health_report(self) -> Dict:
        """تقرير صحة الاستراتيجيات"""
        report = {}
        for strategy, perf in self.strategy_performance.items():
            if perf.get("trades", 0) >= 10:
                if perf["profit_factor"] > 1.5:
                    status = "EXCELLENT"
                elif perf["profit_factor"] > 1.0:
                    status = "GOOD"
                elif perf["profit_factor"] > 0.7:
                    status = "DEGRADED"
                else:
                    status = "POOR"
            else:
                status = "INSUFFICIENT_DATA"

            report[strategy] = {
                "status": status,
                "trades": perf.get("trades", 0),
                "win_rate": perf.get("win_rate", 0.50),
                "profit_factor": perf.get("profit_factor", 1.0),
            }

        return report
