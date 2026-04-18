#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Performance Tracker — متتبع الأداء الذكي
===============================================
يربط بين تنفيذ الصفقات (Executor) والعقل المدبر (CognitiveLearningCore).
يقوم بجمع البيانات، تنظيفها، وإطعامها لنظام التعلم لضمان اتخاذ قرارات صحيحة.
"""

import logging
from backend.core.cognitive_learning_core import learning_core

logger = logging.getLogger(__name__)


class SmartPerformanceTracker:
    """
    متتبع الأداء الذي يضمن تغذية نظام التعلم ببيانات دقيقة ومصنفة.
    """

    def __init__(self):
        self.core = learning_core

    def record_trade(self, trade_data: dict):
        """
        تسجيل صفقة مغلقة وتحليلها للتعلم.
        """
        strategy = trade_data.get("strategy", "Unknown")
        pnl = trade_data.get("pnl", 0.0)
        is_demo = trade_data.get("is_demo", True)
        
        # استخراج نظام السوق (Regime) من البيانات إذا توفر، وإلا نستخدم "Unknown"
        # في التنفيذ الفعلي، يجب تمرير الـ Regime من Executor
        regime = trade_data.get("regime", "UNKNOWN")

        # التحقق من صحة البيانات
        if pnl == 0.0 and trade_data.get("exit_reason") != "BREAK_EVEN":
            logger.debug(f"⚠️ Trade ignored for learning (Zero PnL): {strategy}")
            return

        # تسجيل التجربة في العقل المدبر
        self.core.record_experience(
            strategy=strategy,
            regime=regime,
            pnl=pnl,
            is_real=not is_demo
        )

        logger.info(
            f"📚 [Learning] Recorded: {strategy} | Regime: {regime} | "
            f"PnL: {pnl:.2f} | {'Real' if not is_demo else 'Demo'}"
        )

    def get_strategy_weights(self, current_regime: str) -> dict:
        """الحصول على الأوزان الحالية للاستراتيجيات بناءً على النظام الحالي"""
        return self.core.get_weights(current_regime)

    def get_learning_health_report(self) -> dict:
        """الحصول على تقرير صحة التعلم"""
        return self.core.get_learning_report()


# Singleton Instance
performance_tracker = SmartPerformanceTracker()
