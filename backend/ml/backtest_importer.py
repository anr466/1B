#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest Importer - استيراد نتائج الاختبار التاريخي كبيانات أساسية
====================================================================

الهدف: كسر الحلقة المفرغة (لا يتداول ← لا بيانات ← WR=0% ← يرفض)
الحل: استيراد نتائج backtest كبيانات baseline → يبدأ النظام بثقة مبدئية

المراحل:
  Phase 1 (BACKTEST_BOOTSTRAP): استيراد نتائج backtest كـ baseline
  Phase 2 (PAPER_TRADING): تداول تجريبي على بيانات حية بدون مال
  Phase 3 (LIVE_VALIDATION): مقارنة نتائج Demo مع Backtest
  Phase 4 (LIVE_TRADING): تداول حقيقي مع تعلم مستمر
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ============================================================
# Trading Phases
# ============================================================

PHASE_BACKTEST = "BACKTEST_BOOTSTRAP"  # مرحلة 1: استيراد backtest
PHASE_PAPER = "PAPER_TRADING"  # مرحلة 2: تداول تجريبي
PHASE_VALIDATION = "LIVE_VALIDATION"  # مرحلة 3: مقارنة Demo مع Backtest
PHASE_LIVE = "LIVE_TRADING"  # مرحلة 4: تداول حقيقي

PHASE_ORDER = [PHASE_BACKTEST, PHASE_PAPER, PHASE_VALIDATION, PHASE_LIVE]

# معايير الانتقال بين المراحل
PHASE_TRANSITION_RULES = {
    PHASE_BACKTEST: {
        "min_backtest_trades": 30,  # حد أدنى 30 صفقة backtest
        "min_backtest_win_rate": 0.35,  # Win Rate > 35%
        "description": "استيراد نتائج backtest كـ baseline",
    },
    PHASE_PAPER: {
        "min_paper_trades": 20,  # حد أدنى 20 صفقة paper
        "min_paper_days": 3,  # على الأقل 3 أيام
        "description": "تداول تجريبي على بيانات حية",
    },
    PHASE_VALIDATION: {
        "win_rate_tolerance": 0.15,  # ±15% تفاوت مسموح
        "min_validation_trades": 15,  # 15 صفقة تحقق
        "description": "مقارنة نتائج Demo مع Backtest",
    },
    PHASE_LIVE: {"description": "تداول حقيقي مع تعلم مستمر"},
}


class BacktestImporter:
    """
    استيراد نتائج الاختبار التاريخي كبيانات أساسية للـ ML.

    لا يستبدل البيانات الحية - يوفر نقطة بداية فقط.
    """

    def __init__(self, db_manager=None):
        self.db = db_manager
        self.import_history = []

    def import_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        استيراد نتائج backtest من ملف JSON.

        Format متوقع:
        [
            {
                "symbol": "BTCUSDT",
                "strategy": "ScalpingV8",
                "timeframe": "1h",
                "entry_price": 50000,
                "exit_price": 50500,
                "profit_pct": 1.0,
                "is_win": true,
                "indicators": {"rsi": 35, "macd": 0.5, ...},
                "timestamp": "2024-01-01T00:00:00"
            }
        ]
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            with open(path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            if not isinstance(raw_data, list):
                raw_data = [raw_data]

            return self._process_trades(raw_data, source="backtest_file")

        except Exception as e:
            logger.error(f"❌ Backtest import from file failed: {e}")
            return {"success": False, "error": str(e)}

    def import_from_db(self) -> Dict[str, Any]:
        """استيراد نتائج backtest من قاعدة البيانات."""
        if not self.db:
            return {"success": False, "error": "DB not available"}

        try:
            with self.db.get_connection() as conn:
                # Check if backtest_results table exists
                rows = conn.execute("""
                    SELECT symbol, strategy, timeframe, entry_price, exit_price,
                           profit_pct, is_win, indicators, timestamp
                    FROM backtest_results
                    WHERE imported_to_ml = FALSE
                    ORDER BY timestamp
                    LIMIT 1000
                """).fetchall()

                if not rows:
                    return {
                        "success": True,
                        "imported": 0,
                        "message": "No pending backtest results",
                    }

                trades = []
                for row in rows:
                    indicators = {}
                    if row[7]:
                        try:
                            indicators = (
                                json.loads(row[7])
                                if isinstance(row[7], str)
                                else row[7]
                            )
                        except Exception:
                            indicators = {}

                    trades.append(
                        {
                            "symbol": row[0],
                            "strategy": row[1],
                            "timeframe": row[2],
                            "entry_price": float(row[3] or 0),
                            "exit_price": float(row[4] or 0),
                            "profit_pct": float(row[5] or 0),
                            "is_win": bool(row[6]),
                            "indicators": indicators,
                            "timestamp": str(row[8])
                            if row[8]
                            else datetime.now().isoformat(),
                        }
                    )

                result = self._process_trades(trades, source="backtest_db")

                # Mark as imported
                if result["success"]:
                    conn.execute("""
                        UPDATE backtest_results SET imported_to_ml = TRUE
                        WHERE imported_to_ml = FALSE
                    """)
                    conn.commit()

                return result

        except Exception as e:
            # Table might not exist yet - that's OK
            if "backtest_results" in str(e):
                return {
                    "success": True,
                    "imported": 0,
                    "message": "backtest_results table not found (skip)",
                }
            logger.error(f"❌ Backtest import from DB failed: {e}")
            return {"success": False, "error": str(e)}

    def _process_trades(
        self, trades: List[Dict], source: str = "backtest"
    ) -> Dict[str, Any]:
        """معالجة الصفقات وتحويلها لصيغة ML training."""
        if not trades:
            return {"success": True, "imported": 0, "message": "No trades to import"}

        # تحويل للصيغة المتوقعة من ML Signal Classifier
        ml_data = []
        stats = {
            "total": len(trades),
            "wins": 0,
            "losses": 0,
            "total_profit_pct": 0,
            "strategies": {},
            "symbols": {},
        }

        for trade in trades:
            is_win = trade.get("is_win", trade.get("profit_pct", 0) > 0)
            profit_pct = trade.get("profit_pct", 0)
            indicators = trade.get("indicators", {})

            if is_win:
                stats["wins"] += 1
            else:
                stats["losses"] += 1

            stats["total_profit_pct"] += profit_pct

            # تتبع الاستراتيجيات
            strategy = trade.get("strategy", "unknown")
            if strategy not in stats["strategies"]:
                stats["strategies"][strategy] = {"trades": 0, "wins": 0}
            stats["strategies"][strategy]["trades"] += 1
            if is_win:
                stats["strategies"][strategy]["wins"] += 1

            # تتبع العملات
            symbol = trade.get("symbol", "unknown")
            if symbol not in stats["symbols"]:
                stats["symbols"][symbol] = {"trades": 0, "wins": 0}
            stats["symbols"][symbol]["trades"] += 1
            if is_win:
                stats["symbols"][symbol]["wins"] += 1

            # تحويل لصيغة ML
            ml_trade = {
                "symbol": symbol,
                "strategy": strategy,
                "timeframe": trade.get("timeframe", "1h"),
                "entry_price": trade.get("entry_price", 0),
                "exit_price": trade.get("exit_price", 0),
                "profit_loss": profit_pct,
                "profit_pct": profit_pct,
                "is_winning": is_win,
                "indicators": indicators,
                "source": "adjusted_backtest",  # مهم: ليس "backtesting"
                "weight": 0.6,  # وزن مخفض للبيانات التاريخية
                "timestamp": trade.get("timestamp", datetime.now().isoformat()),
            }
            ml_data.append(ml_trade)

        win_rate = stats["wins"] / stats["total"] if stats["total"] > 0 else 0

        result = {
            "success": True,
            "imported": len(ml_data),
            "source": source,
            "stats": {
                "total_trades": stats["total"],
                "win_rate": round(win_rate, 3),
                "wins": stats["wins"],
                "losses": stats["losses"],
                "avg_profit_pct": round(stats["total_profit_pct"] / stats["total"], 3)
                if stats["total"] > 0
                else 0,
                "strategies": stats["strategies"],
                "symbols": stats["symbols"],
            },
            "ml_data": ml_data,
        }

        self.import_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "source": source,
                "trades_imported": len(ml_data),
                "win_rate": win_rate,
            }
        )

        logger.info(
            f"✅ Backtest Import: {len(ml_data)} trades | WR={win_rate:.1%} | "
            f"PnL={stats['total_profit_pct']:.1f}%"
        )

        return result

    def get_phase_info(self) -> Dict[str, Any]:
        """معلومات عن المرحلة الحالية وقواعد الانتقال."""
        return {
            "phases": {
                PHASE_BACKTEST: PHASE_TRANSITION_RULES[PHASE_BACKTEST],
                PHASE_PAPER: PHASE_TRANSITION_RULES[PHASE_PAPER],
                PHASE_VALIDATION: PHASE_TRANSITION_RULES[PHASE_VALIDATION],
                PHASE_LIVE: PHASE_TRANSITION_RULES[PHASE_LIVE],
            },
            "import_history": self.import_history,
        }


# Singleton
_importer = None


def get_backtest_importer(db_manager=None) -> BacktestImporter:
    global _importer
    if _importer is None:
        _importer = BacktestImporter(db_manager)
    return _importer
