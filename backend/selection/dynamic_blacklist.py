#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام القائمة السوداء الديناميكية
يتعلم من أداء الصفقات السابقة ويحدث تلقائياً
"""

import logging
from typing import Dict, Set
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class DynamicBlacklist:
    """
    نظام ذكي يحدد العملات السيئة تلقائياً

    المنطق:
    1. يتتبع أداء كل عملة من الصفقات الفعلية
    2. يضيف للقائمة السوداء إذا: WinRate < 35% أو خسارة متتالية >= 3
    3. يزيل من القائمة بعد فترة (يعطي فرصة جديدة)
    4. يكيّف الإعدادات حسب تصنيف العملة
    """

    def __init__(self, db_manager=None):
        self.logger = logger
        self.db = db_manager

        # سجل الأداء لكل عملة
        self.performance: Dict[str, Dict] = defaultdict(
            lambda: {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "consecutive_losses": 0,
                "total_pnl": 0.0,
                "last_trade_time": None,
                "blacklisted_at": None,
                "blacklist_reason": None,
            }
        )

        # القائمة السوداء الديناميكية
        self.blacklist: Set[str] = set()

        # إعدادات
        self.config = {
            "min_trades_for_decision": 3,  # الحد الأدنى للصفقات قبل الحكم
            "min_win_rate": 0.35,  # أقل من 35% = قائمة سوداء
            "max_consecutive_losses": 3,  # 3 خسائر متتالية = قائمة سوداء
            "blacklist_duration_hours": 72,  # مدة البقاء في القائمة (3 أيام)
            "redemption_trades": 2,  # صفقات ناجحة للخروج من القائمة
        }

        # تصنيفات العملات وإعداداتها
        self.coin_profiles: Dict[str, Dict] = {}

    def record_trade(self, symbol: str, is_win: bool, pnl: float):
        """
        تسجيل نتيجة صفقة

        Args:
            symbol: رمز العملة
            is_win: هل ربحت؟
            pnl: الربح/الخسارة بالدولار
        """
        perf = self.performance[symbol]
        perf["total_trades"] += 1
        perf["total_pnl"] += pnl
        perf["last_trade_time"] = datetime.now()

        if is_win:
            perf["wins"] += 1
            perf["consecutive_losses"] = 0  # إعادة العداد
        else:
            perf["losses"] += 1
            perf["consecutive_losses"] += 1

        # فحص إذا يجب إضافتها للقائمة السوداء
        self._check_blacklist_status(symbol)

        self.logger.info(
            f"📊 {symbol}: {'✅' if is_win else '❌'} | "
            f"WR: {self._get_win_rate(symbol):.0%} | "
            f"PnL: ${pnl:+.2f}"
        )

    def _check_blacklist_status(self, symbol: str):
        """فحص وتحديث حالة القائمة السوداء"""
        perf = self.performance[symbol]

        # لا نحكم قبل الحد الأدنى من الصفقات
        if perf["total_trades"] < self.config["min_trades_for_decision"]:
            return

        win_rate = self._get_win_rate(symbol)
        consecutive_losses = perf["consecutive_losses"]

        # أسباب الإضافة للقائمة السوداء
        should_blacklist = False
        reason = None

        if win_rate < self.config["min_win_rate"]:
            should_blacklist = True
            reason = f"معدل نجاح منخفض ({win_rate:.0%})"

        elif consecutive_losses >= self.config["max_consecutive_losses"]:
            should_blacklist = True
            reason = f"خسائر متتالية ({consecutive_losses})"

        if should_blacklist and symbol not in self.blacklist:
            self._add_to_blacklist(symbol, reason)

    def _add_to_blacklist(self, symbol: str, reason: str):
        """إضافة عملة للقائمة السوداء"""
        self.blacklist.add(symbol)
        self.performance[symbol]["blacklisted_at"] = datetime.now()
        self.performance[symbol]["blacklist_reason"] = reason

        self.logger.warning(f"🚫 {symbol} → القائمة السوداء: {reason}")

    def _remove_from_blacklist(self, symbol: str, reason: str):
        """إزالة عملة من القائمة السوداء"""
        self.blacklist.discard(symbol)
        self.performance[symbol]["blacklisted_at"] = None
        self.performance[symbol]["blacklist_reason"] = None
        self.performance[symbol]["consecutive_losses"] = 0

        self.logger.info(f"✅ {symbol} ← خرجت من القائمة السوداء: {reason}")

    def is_blacklisted(self, symbol: str) -> bool:
        """
        هل العملة في القائمة السوداء؟
        مع فحص انتهاء المدة
        """
        if symbol not in self.blacklist:
            return False

        # فحص انتهاء مدة القائمة السوداء
        perf = self.performance[symbol]
        blacklisted_at = perf.get("blacklisted_at")

        if blacklisted_at:
            duration = datetime.now() - blacklisted_at
            max_duration = timedelta(hours=self.config["blacklist_duration_hours"])

            if duration > max_duration:
                self._remove_from_blacklist(symbol, "انتهت مدة الحظر")
                return False

        return True

    def _get_win_rate(self, symbol: str) -> float:
        """حساب معدل النجاح"""
        perf = self.performance[symbol]
        total = perf["total_trades"]
        if total == 0:
            return 0.5  # افتراضي
        return perf["wins"] / total

    def get_adaptive_settings(self, symbol: str, volatility: float) -> Dict:
        """
        الحصول على إعدادات متكيفة حسب العملة

        Returns:
            إعدادات SL/TP/Size مخصصة
        """
        win_rate = self._get_win_rate(symbol)
        perf = self.performance[symbol]

        # تصنيف العملة
        if symbol in ["BTCUSDT", "BTC/USDT"]:
            coin_type = "MAJOR"
        elif volatility < 0.03:
            coin_type = "STABLE"
        elif volatility > 0.06:
            coin_type = "VOLATILE"
        else:
            coin_type = "MEDIUM"

        # إعدادات أساسية حسب النوع
        base_settings = {
            "MAJOR": {"sl": 0.025, "tp": 0.05, "size_mult": 1.2},
            "STABLE": {"sl": 0.02, "tp": 0.04, "size_mult": 1.1},
            "MEDIUM": {"sl": 0.03, "tp": 0.06, "size_mult": 1.0},
            "VOLATILE": {"sl": 0.04, "tp": 0.08, "size_mult": 0.8},
        }

        settings = base_settings.get(coin_type, base_settings["MEDIUM"])

        # تعديل حسب الأداء التاريخي
        if perf["total_trades"] >= 5:
            if win_rate > 0.6:
                # عملة ناجحة - زيادة الحجم
                settings["size_mult"] *= 1.2
                settings["tp"] *= 1.1  # هدف أعلى
            elif win_rate < 0.4:
                # عملة ضعيفة - تقليل الحجم
                settings["size_mult"] *= 0.8
                settings["sl"] *= 0.9  # SL أضيق

        return {
            "stop_loss_pct": settings["sl"],
            "take_profit_pct": settings["tp"],
            "position_size_multiplier": settings["size_mult"],
            "coin_type": coin_type,
            "win_rate": win_rate,
            "total_trades": perf["total_trades"],
        }

    def get_status(self) -> Dict:
        """الحصول على حالة النظام"""
        return {
            "blacklisted_coins": list(self.blacklist),
            "tracked_coins": len(self.performance),
            "total_trades_recorded": sum(
                p["total_trades"] for p in self.performance.values()
            ),
            "config": self.config,
        }

    def load_from_database(self):
        """تحميل الأداء من قاعدة البيانات — بدون إضافة للقائمة السوداء عند البدء"""
        if not self.db:
            self.logger.warning("لا يوجد اتصال بقاعدة البيانات")
            return

        try:
            with self.db.get_connection() as conn:
                trades = conn.execute("""
                    SELECT symbol, profit_loss, closed_at
                    FROM active_positions
                    WHERE is_active = FALSE AND profit_loss IS NOT NULL
                    ORDER BY closed_at ASC
                    LIMIT 500
                """).fetchall()

                for trade in trades:
                    symbol = trade["symbol"]
                    pnl = trade["profit_loss"]
                    is_win = pnl > 0

                    perf = self.performance[symbol]
                    perf["total_trades"] += 1
                    perf["total_pnl"] += pnl
                    if is_win:
                        perf["wins"] += 1
                        perf["consecutive_losses"] = 0
                    else:
                        perf["losses"] += 1
                        perf["consecutive_losses"] += 1

                self.logger.info(
                    "تم تحميل {} صفقة من قاعدة البيانات".format(len(trades))
                )
                self.logger.info(
                    "القائمة السوداء: {} (فارغة عند البدء)".format(self.blacklist)
                )

        except Exception as e:
            self.logger.error("خطأ في تحميل البيانات: {}".format(e))


# Singleton instance
_dynamic_blacklist = None


def get_dynamic_blacklist(db_manager=None) -> DynamicBlacklist:
    """الحصول على instance واحد"""
    global _dynamic_blacklist
    if _dynamic_blacklist is None:
        _dynamic_blacklist = DynamicBlacklist(db_manager)
    return _dynamic_blacklist
