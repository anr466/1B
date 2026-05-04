#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Tracker — متتبع الأداء
====================================
يراقب نتائج الصفقات المغلقة ويحدث أداء الاستراتيجيات تلقائياً.
يُغذي DynamicWeightMatrix بالبيانات لتعديل الأوزان.

يعمل بشكل مستقل كـ background process أو يُستدعى عند إغلاق كل صفقة.
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """
    يتتبع أداء الاستراتيجيات ويحدث الأوزان تلقائياً.
    """

    def __init__(self, decision_matrix=None):
        self.decision_matrix = decision_matrix  # Reference to CognitiveDecisionMatrix

        # سجل الصفقات (مؤقت — يمكن حفظه في DB لاحقاً)
        self.trade_history: list = []

        # إحصائيات عامة
        self.total_trades = 0
        self.total_wins = 0
        self.total_losses = 0
        self.total_pnl = 0.0

    def record_trade(self, trade_data: Dict):
        """
        تسجيل نتيجة صفقة مغلقة.

        Args:
            trade_data: {
                "symbol": "BTCUSDT",
                "strategy": "Trend Pullback",
                "type": "LONG",
                "entry_price": 50000.0,
                "exit_price": 51000.0,
                "quantity": 0.01,
                "pnl": 10.0,
                "exit_reason": "TAKE_PROFIT",
                "closed_at": "2024-01-01T12:00:00",
            }
        """
        self.trade_history.append(trade_data)
        self.total_trades += 1

        pnl = trade_data.get("pnl", 0.0)
        self.total_pnl += pnl

        if pnl > 0:
            self.total_wins += 1
            win = True
            profit = pnl
            loss = 0.0
        else:
            self.total_losses += 1
            win = False
            profit = 0.0
            loss = abs(pnl)

        strategy = trade_data.get("strategy", "Unknown")

        # تحديث أداء الاستراتيجية
        if self.decision_matrix:
            self.decision_matrix.update_strategy_performance(
                strategy, win, profit, loss
            )
            logger.info(
                f"📊 Trade recorded: {trade_data['symbol']} {strategy} "
                f"{'WIN' if win else 'LOSS'} ${pnl:.2f} "
                f"(Total: {self.total_trades} trades, PnL: ${self.total_pnl:.2f})"
            )

    def get_performance_summary(self) -> Dict:
        """ملخص الأداء العام"""
        win_rate = self.total_wins / self.total_trades if self.total_trades > 0 else 0.0
        avg_win = 0.0
        avg_loss = 0.0

        wins = [t for t in self.trade_history if t.get("pnl", 0) > 0]
        losses = [t for t in self.trade_history if t.get("pnl", 0) <= 0]

        if wins:
            avg_win = sum(t["pnl"] for t in wins) / len(wins)
        if losses:
            avg_loss = sum(abs(t["pnl"]) for t in losses) / len(losses)

        profit_factor = (
            sum(t["pnl"] for t in wins) / sum(abs(t["pnl"]) for t in losses)
            if losses and sum(abs(t["pnl"]) for t in losses) > 0
            else float("inf")
            if wins
            else 1.0
        )

        return {
            "total_trades": self.total_trades,
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
            "win_rate": round(win_rate, 3),
            "total_pnl": round(self.total_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2)
            if profit_factor != float("inf")
            else "∞",
            "strategy_health": self.decision_matrix.get_strategy_health()
            if self.decision_matrix
            else {},
        }

    def get_strategy_rankings(self) -> list:
        """ترتيب الاستراتيجيات حسب الأداء"""
        if not self.decision_matrix:
            return []

        health = self.decision_matrix.get_strategy_health()
        ranked = sorted(
            health.items(),
            key=lambda x: x[1].get("profit_factor", 0),
            reverse=True,
        )
        return [
            {"strategy": name, **stats}
            for name, stats in ranked
            if stats.get("trades", 0) >= 10
        ]
