#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Live Validation System — مقارنة نتائج Paper Trading مع Backtest baseline.

يقرر متى ينتقل النظام من المرحلة التجريبية للتداول الحقيقي.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class LiveValidator:
    """مقارن الأداء — Paper Trading vs Backtest."""

    def __init__(self):
        self.backtest_baseline: Optional[Dict] = None
        self.paper_results: Optional[Dict] = None
        self.validation_log = []

    def set_backtest_baseline(self, stats: Dict):
        """تعيين baseline من نتائج backtest."""
        self.backtest_baseline = {
            "win_rate": stats.get("win_rate", 0),
            "avg_profit_pct": stats.get("avg_profit_pct", 0),
            "total_trades": stats.get("total_trades", 0),
            "max_drawdown_pct": stats.get("max_drawdown_pct", 0),
            "sharpe_ratio": stats.get("sharpe_ratio", 0),
        }
        logger.info(
            f"📊 Backtest baseline set: WR={self.backtest_baseline['win_rate']:.1%}"
        )

    def update_paper_results(self, paper_stats: Dict):
        """تحديث نتائج paper trading."""
        self.paper_results = {
            "win_rate": paper_stats.get("win_rate", 0),
            "avg_profit_pct": (
                paper_stats.get("total_pnl_pct", 0)
                / paper_stats.get("completed_trades", 1)
            ),
            "total_trades": paper_stats.get("completed_trades", 0),
            "total_pnl_pct": paper_stats.get("total_pnl_pct", 0),
        }

    def validate(self) -> Dict[str, Any]:
        """
        مقارنة Paper مع Backtest.

        معايير النجاح:
        - Win Rate within ±15% of backtest
        - على الأقل 15 صفقة مكتملة
        - PnL direction matches (كلاهما ربح أو كلاهما خسارة)
        """
        if not self.backtest_baseline or not self.paper_results:
            return {
                "ready": False,
                "reason": "Missing baseline or paper results",
                "phase": "PAPER_TRADING",
            }

        bt = self.backtest_baseline
        pp = self.paper_results

        min_trades = 15
        wr_tolerance = 0.15

        checks = {
            "min_trades_met": pp["total_trades"] >= min_trades,
            "win_rate_close": abs(pp["win_rate"] - bt["win_rate"]) <= wr_tolerance,
            "pnl_direction_match": (pp["total_pnl_pct"] > 0)
            == (bt["avg_profit_pct"] > 0),
        }

        all_passed = all(checks.values())
        failed_checks = [k for k, v in checks.items() if not v]

        result = {
            "ready": all_passed,
            "phase": "LIVE_TRADING" if all_passed else "PAPER_TRADING",
            "checks": checks,
            "failed": failed_checks,
            "backtest": {
                "win_rate": bt["win_rate"],
                "avg_profit_pct": bt["avg_profit_pct"],
                "total_trades": bt["total_trades"],
            },
            "paper": {
                "win_rate": pp["win_rate"],
                "avg_profit_pct": round(pp["avg_profit_pct"], 3),
                "total_trades": pp["total_trades"],
                "total_pnl_pct": pp["total_pnl_pct"],
            },
            "wr_gap": round(abs(pp["win_rate"] - bt["win_rate"]) * 100, 1),
            "validated_at": datetime.now().isoformat(),
        }

        self.validation_log.append(result)

        if all_passed:
            logger.info(f"✅ VALIDATION PASSED → Ready for LIVE TRADING")
            logger.info(
                f"   Backtest WR: {bt['win_rate']:.1%} | Paper WR: {pp['win_rate']:.1%}"
            )
            logger.info(
                f"   Gap: {result['wr_gap']}% (tolerance: {wr_tolerance * 100}%)"
            )
        else:
            logger.info(f"⏳ Validation pending: {failed_checks}")

        return result


_validator = None


def get_validator() -> LiveValidator:
    global _validator
    if _validator is None:
        _validator = LiveValidator()
    return _validator
