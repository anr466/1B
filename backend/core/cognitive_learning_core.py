#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cognitive Learning Core — العقل المدبر للنظام
=============================================
هذا الملف يدمج الذاكرة (Memory)، التعلم (Learning)، والتصحيح الذاتي (Self-Correction).
النظام هنا لا يحسب الأوزان فحسب، بل:
1. يتذكر الأداء بناءً على نظام السوق (Contextual Memory).
2. ينسى البيانات القديمة تلقائياً (Time Decay).
3. يميز بين التداول الحقيقي والتجريبي (Real vs Demo Bias).
4. يصحح نفسه إذا كان واثقاً من استراتيجية وخسرت (Meta-Cognition).
"""

import time
import logging
from collections import defaultdict
from typing import Dict

logger = logging.getLogger(__name__)


class CognitiveLearningCore:
    """
    العقل المدبر: يدير أوزان الاستراتيجيات بناءً على الخبرة المتراكمة والتصحيح الذاتي.
    """

    def __init__(self):
        # هيكل الذاكرة: { Strategy: { Regime: { Score, Trades, LastUpdate } } }
        # Score ranges from -1.0 (Terrible) to 1.0 (Excellent)
        self.memory = defaultdict(lambda: defaultdict(lambda: {
            'score': 0.0,
            'trades': 0,
            'last_update': time.time(),
            'consecutive_losses': 0
        }))

        # إعدادات التعلم
        self.learning_rate = 0.15  # سرعة التكيف مع المعلومات الجديدة
        self.decay_factor = 0.98   # عامل النسيان (كلما اقترب من 1، الذاكرة أطول)
        self.real_trade_impact = 3.0  # التداول الحقيقي يؤثر 3 أضعاف التجريبي
        self.confidence_threshold = 0.6  # الحد الذي نعتبر فوقه الاستراتيجية "موثوقة"

    def record_experience(self, strategy: str, regime: str, pnl: float, is_real: bool):
        """
        تسجيل تجربة جديدة (نتيجة صفقة) وتحديث الذاكرة.
        """
        if not strategy:
            return

        # 1. التهيئة إذا كانت استراتيجية جديدة
        if strategy not in self.memory:
            logger.info(f"🧠 [Discovery] استراتيجية جديدة مكتشفة: {strategy}. بدء التعلم من الصفر.")

        strategy_memory = self.memory[strategy][regime]

        # 2. النسيان الزمني (Time Decay)
        # نقلل من تأثير النتائج القديمة تدريجياً
        self._apply_decay(strategy_memory)

        # 3. حساب جودة النتيجة
        # ربح = +1، خسارة = -1
        outcome_quality = 1.0 if pnl > 0 else -1.0

        # 4. حساب قوة التأثير (Impact Weight)
        # الصفقات الحقيقية أهم، والخسائر المتتالية تزيد الحساسية
        impact_weight = self.real_trade_impact if is_real else 1.0
        if strategy_memory['consecutive_losses'] >= 3:
            impact_weight *= 1.5  # زيادة الحساسية بعد 3 خسائر متتالية

        # 5. تحديث النتيجة (Score Update)
        delta = outcome_quality * impact_weight * self.learning_rate
        old_score = strategy_memory['score']
        strategy_memory['score'] += delta
        strategy_memory['trades'] += 1
        strategy_memory['last_update'] = time.time()

        # تحديث عداد الخسائر المتتالية
        if pnl <= 0:
            strategy_memory['consecutive_losses'] += 1
        else:
            strategy_memory['consecutive_losses'] = 0

        # تثبيت النتيجة بين -1 و 1
        strategy_memory['score'] = max(-1.0, min(1.0, strategy_memory['score']))

        # 6. التصحيح الذاتي (Meta-Cognition / Self-Correction)
        self._self_correct(strategy, regime, old_score, strategy_memory['score'], pnl)

    def _self_correct(self, strategy: str, regime: str, old_score: float, new_score: float, pnl: float):
        """
        منطق التفكير العميق: هل كنت واثقاً جداً وأخطأت؟ هل كنت متشائماً جداً وأصبت؟
        """
        # حالة 1: الثقة العمياء (Overconfidence)
        # كنا نعتقد أن الاستراتيجية ممتازة (> 0.6) وخسرنا
        if old_score > self.confidence_threshold and pnl < 0:
            penalty = 0.2  # عقوبة إضافية
            self.memory[strategy][regime]['score'] -= penalty
            logger.warning(
                f"🧠 [Self-Correction] ثقة عمياء! '{strategy}' في {regime} خسرت رغم ثقتنا العالية. "
                f"تم تطبيق عقوبة تصحيحية (-{penalty})."
            )

        # حالة 2: التشاؤم المفرط (Underestimation)
        # كنا نعتقد أن الاستراتيجية سيئة (< -0.4) وربحت
        elif old_score < -0.4 and pnl > 0:
            boost = 0.15  # دفعة لإعادة التقييم
            self.memory[strategy][regime]['score'] += boost
            logger.info(
                f"🧠 [Re-Evaluation] إعادة نظر! '{strategy}' في {regime} ربحت رغم تشاؤمنا. "
                f"تم إعطاء فرصة ثانية (+{boost})."
            )

    def get_weights(self, current_regime: str) -> Dict[str, float]:
        """
        استخراج الأوزان الحالية للاستراتيجيات بناءً على نظام السوق الحالي.
        """
        weights = {}

        for strategy, regimes in self.memory.items():
            # هل لدينا ذاكرة عن هذه الاستراتيجية في النظام الحالي؟
            if current_regime in regimes:
                score = regimes[current_regime]['score']
            else:
                # إذا لم نجد بيانات محددة، نأخذ متوسط الأداء العام (Fallback)
                # أو نبدأ بوزن محايد
                total_score = sum(r['score'] for r in regimes.values())
                count = len(regimes)
                score = (total_score / count) if count > 0 else 0.0

            # تحويل النتيجة (-1 إلى 1) إلى وزن (0.1 إلى 1.0)
            # المعادلة: Weight = 0.1 + (0.9 * (Score + 1) / 2)
            weight = 0.1 + (0.9 * ((score + 1) / 2))
            weights[strategy] = round(weight, 3)

        return weights

    def _apply_decay(self, memory_entry: dict):
        """تطبيق عامل النسيان على النتيجة الموجودة"""
        memory_entry['score'] *= self.decay_factor

    def get_learning_report(self) -> Dict:
        """تقرير شامل عن حالة التعلم والذاكرة"""
        report = {}
        for strategy, regimes in self.memory.items():
            report[strategy] = {}
            for regime, data in regimes.items():
                report[strategy][regime] = {
                    "score": round(data['score'], 3),
                    "trades": data['trades'],
                    "status": "Excellent" if data['score'] > 0.5 else ("Poor" if data['score'] < -0.2 else "Neutral")
                }
        return report


# Singleton Instance
learning_core = CognitiveLearningCore()
