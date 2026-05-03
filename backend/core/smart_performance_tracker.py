#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Performance Tracker — Persistent & Distributed
====================================================
يربط بين تنفيذ الصفقات (Executor) والعقل المدبر (CognitiveLearningCore).
يتميز الآن بالحفظ في قاعدة البيانات لضمان مشاركة التعلم بين جميع الحاويات.
"""

import logging
from backend.core.cognitive_learning_core import learning_core
from backend.infrastructure.db_access import get_db_write_connection, get_db_connection

logger = logging.getLogger(__name__)


class SmartPerformanceTracker:
    """
    متتبع الأداء الذي يضمن تغذية نظام التعلم ببيانات دقيقة ومصنفة ومخزنة.
    """

    def __init__(self):
        self.core = learning_core

    def record_trade(self, trade_data: dict):
        """
        تسجيل صفقة مغلقة وتحديث الذاكرة وقاعدة البيانات.
        """
        strategy = trade_data.get("strategy", "Unknown")
        pnl = trade_data.get("pnl", 0.0)
        is_demo = trade_data.get("is_demo", True)
        regime = trade_data.get("regime", "UNKNOWN")

        if pnl == 0.0 and trade_data.get("exit_reason") != "BREAK_EVEN":
            return

        # 1. تحديث العقل المدبر (RAM)
        self.core.record_experience(
            strategy=strategy,
            regime=regime,
            pnl=pnl,
            is_real=not is_demo
        )

        # 2. الحفظ في قاعدة البيانات (Persistence for Distributed Systems)
        self._save_learning_to_db(strategy, regime, pnl, is_demo)

        logger.info(
            f"📚 [Learning] Recorded: {strategy} | Regime: {regime} | "
            f"PnL: {pnl:.2f} | {'Real' if not is_demo else 'Demo'}"
        )

    def _save_learning_to_db(self, strategy: str, regime: str, pnl: float, is_real: bool):
        """حساب النتيجة الجديدة وحفظها في DB"""
        # جلب البيانات الحالية
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT score, trades FROM strategy_learning WHERE strategy_name = %s AND regime = %s",
                (strategy, regime)
            ).fetchone()

        current_score = row[0] if row else 0.0
        current_trades = row[1] if row else 0

        # حساب النتيجة الجديدة (نفس منطق CognitiveLearningCore)
        outcome_quality = 1.0 if pnl > 0 else -1.0
        impact_weight = 3.0 if is_real else 1.0
        learning_rate = 0.15
        
        # Decay
        new_score = current_score * 0.98 # Decay factor
        
        delta = outcome_quality * impact_weight * learning_rate
        new_score += delta
        new_score = max(-1.0, min(1.0, new_score))
        new_trades = current_trades + 1

        # Upsert
        with get_db_write_connection() as conn:
            conn.execute(
                """
                INSERT INTO strategy_learning (strategy_name, regime, score, trades, last_updated)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (strategy_name, regime) 
                DO UPDATE SET score = %s, trades = %s, last_updated = NOW()
                """,
                (strategy, regime, new_score, new_trades, new_score, new_trades)
            )

    def get_strategy_weights(self, current_regime: str) -> dict:
        """الحصول على الأوزان الحالية من قاعدة البيانات"""
        weights = {}
        
        with get_db_connection() as conn:
            rows = conn.execute(
                "SELECT strategy_name, score FROM strategy_learning WHERE regime = %s",
                (current_regime,)
            ).fetchall()

            if not rows:
                # Fallback: Get global average if no regime specific data
                rows = conn.execute(
                    "SELECT strategy_name, AVG(score) FROM strategy_learning GROUP BY strategy_name"
                ).fetchall()

            for strategy, score in rows:
                # Convert score (-1 to 1) to weight (0.1 to 1.0)
                weight = 0.1 + (0.9 * ((score + 1) / 2))
                weights[strategy] = round(weight, 3)

        return weights

    def get_learning_health_report(self) -> dict:
        """الحصول على تقرير صحة التعلم من DB"""
        report = {}
        with get_db_connection() as conn:
            rows = conn.execute("SELECT strategy_name, regime, score, trades FROM strategy_learning LIMIT 1000").fetchall()
            for strategy, regime, score, trades in rows:
                if strategy not in report:
                    report[strategy] = {}
                report[strategy][regime] = {
                    "score": round(score, 3),
                    "trades": trades,
                    "status": "Excellent" if score > 0.5 else ("Poor" if score < -0.2 else "Neutral")
                }
        return report


# Singleton Instance
performance_tracker = SmartPerformanceTracker()
