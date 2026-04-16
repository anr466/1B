#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Portfolio Risk Manager — محرك النمو الذكي
================================================
يدير المخاطر وحجم الصفقات بذكاء بناءً على:
1. حجم المحفظة (وضع الإطلاق، النمو، الحماية).
2. الأداء الفعلي (تعلم ذاتي وتعديل Kelly).
3. نوع العملة (MAJOR, MEME, VOLATILE).
4. حرارة المحفظة (Portfolio Heat).
"""

import logging
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# ملف حفظ التعلم الذاتي
LEARNING_STATE_FILE = "data/risk_learning_state.json"


# ==================== 1. أوضاع النمو الذكية ====================


class GrowthMode(Enum):
    LAUNCH = "🚀 Launch Mode"  # للمحافظ الصغيرة جداً (<$100)
    GROWTH = "📈 Growth Mode"  # للمحافظ المتوسطة ($100 - $1k)
    STANDARD = "⚖️ Standard Mode"  # للمحافظ الكبيرة ($1k - $10k)
    PRO = "🛡️ Pro Mode"  # للمحافظ الضخمة (>$10k)


@dataclass
class RiskTier:
    mode: GrowthMode
    risk_pct: float  # نسبة المخاطرة لكل صفقة
    max_positions: int  # الحد الأقصى للصفقات المفتوحة
    max_heat_pct: float  # الحد الأقصى للحرارة الكلية
    max_daily_loss_pct: float  # حد الخسارة اليومي
    kelly_multiplier: float  # مضاعف Kelly (للتسريع أو التباطؤ)


# تعريف المستويات
TIERS = [
    # وضع الإطلاق: مخاطرة عالية لكسر حاجز الـ $10
    RiskTier(GrowthMode.LAUNCH, 0.20, 1, 0.20, 0.15, 1.5),
    # وضع النمو: توازن بين السرعة والأمان
    RiskTier(GrowthMode.GROWTH, 0.10, 2, 0.15, 0.10, 1.0),
    # الوضع القياسي: حماية رأس المال
    RiskTier(GrowthMode.STANDARD, 0.05, 4, 0.10, 0.05, 0.75),
    # وضع المحترفين: نمو بطيء ومستقر جداً
    RiskTier(GrowthMode.PRO, 0.02, 6, 0.08, 0.03, 0.5),
]


# ==================== 2. ملف مخاطر العملات ====================

COIN_RISK_PROFILE = {
    "MAJOR": {"max_pos_pct": 1.0, "sl_atr_mult": 3.5, "risk_weight": 1.0},
    "MID_CAP": {"max_pos_pct": 0.8, "sl_atr_mult": 4.0, "risk_weight": 1.2},
    "MEME": {"max_pos_pct": 0.4, "sl_atr_mult": 5.0, "risk_weight": 2.0},
    "VOLATILE": {"max_pos_pct": 0.5, "sl_atr_mult": 4.5, "risk_weight": 1.5},
}


class PortfolioRiskManager:
    def __init__(self):
        self.logger = logger
        # بيانات الأداء للتعلم الذاتي (يمكن ربطها بقاعدة البيانات لاحقاً)
        self.performance = {
            "total_trades": 0,
            "winning_trades": 0,
            "avg_win_pct": 0.015,  # افتراضي
            "avg_loss_pct": -0.010,  # افتراضي
            "consecutive_losses": 0,
            "last_10_results": [],
        }

    def get_tier(self, balance: float) -> RiskTier:
        """تحديد وضع النمو بناءً على الرصيد"""
        if balance < 100:
            return TIERS[0]  # Launch
        elif balance < 1000:
            return TIERS[1]  # Growth
        elif balance < 10000:
            return TIERS[2]  # Standard
        else:
            return TIERS[3]  # Pro

    def classify_tier(self, balance: float) -> RiskTier:
        """Alias for get_tier for backward compatibility"""
        return self.get_tier(balance)

    def update_performance(self, pnl_pct: float, is_win: bool):
        """تحديث الأداء الذاتي (يتم استدعاؤه بعد إغلاق كل صفقة)"""
        self.performance["total_trades"] += 1
        if is_win:
            self.performance["winning_trades"] += 1
            self.performance["consecutive_losses"] = 0
        else:
            self.performance["consecutive_losses"] += 1

        # تحديث المتوسطات المتحركة
        # (بسيط هنا، يمكن استخدام EMA للدقة)
        if self.performance["total_trades"] > 1:
            w = 0.1  # وزن للصفقة الجديدة
            self.performance["avg_win_pct"] = (
                (
                    self.performance["avg_win_pct"] * (1 - w)
                    + (pnl_pct if is_win else 0) * w
                )
                if is_win
                else self.performance["avg_win_pct"]
            )

            self.performance["avg_loss_pct"] = (
                (
                    self.performance["avg_loss_pct"] * (1 - w)
                    + (pnl_pct if not is_win else 0) * w
                )
                if not is_win
                else self.performance["avg_loss_pct"]
            )

        self.performance["last_10_results"].append(is_win)
        if len(self.performance["last_10_results"]) > 10:
            self.performance["last_10_results"].pop(0)

    def get_adaptive_kelly(self) -> float:
        """حساب Kelly بناءً على الأداء الفعلي"""
        p = self.performance["winning_trades"] / max(
            self.performance["total_trades"], 1
        )
        b = (
            abs(self.performance["avg_win_pct"] / self.performance["avg_loss_pct"])
            if self.performance["avg_loss_pct"] != 0
            else 1
        )

        if b == 0:
            return 0.0

        kelly = (p * b - (1 - p)) / b

        # عقوبة الخسائر المتتالية
        if self.performance["consecutive_losses"] >= 3:
            kelly *= 0.5  # تقليل المخاطرة للنصف
            self.logger.warning(f"⚠️ 3 consecutive losses: Kelly reduced by 50%")

        return max(0.01, min(kelly, 0.25))  # حدود 1% - 25%

    def get_position_size(
        self, balance: float, coin_type: str, confidence: float, risk_per_trade: float
    ) -> Dict:
        """
        حساب حجم الصفقة الذكي
        """
        tier = self.get_tier(balance)
        coin_profile = COIN_RISK_PROFILE.get(coin_type, COIN_RISK_PROFILE["MID_CAP"])

        # 1. حساب الحجم الأساسي بناءً على وضع النمو
        base_size = balance * tier.risk_pct

        # 2. تطبيق قيود نوع العملة
        max_coin_size = balance * coin_profile["max_pos_pct"]
        size = min(base_size, max_coin_size)

        # 3. تعديل الثقة (Confidence)
        # إذا كانت الثقة منخفضة، نقلل الحجم
        if confidence < 60:
            size *= 0.7
        elif confidence > 85:
            size *= 1.2

        # 4. تطبيق Kelly الديناميكي (اختياري، يمكن تفعيله)
        # kelly = self.get_adaptive_kelly()
        # size = min(size, balance * kelly * tier.kelly_multiplier)

        # 5. الحد الأدنى للصفقة (Binance Limit)
        min_size = 10.0
        can_trade = size >= min_size

        if not can_trade:
            self.logger.info(
                f"🚫 Size too small: ${size:.2f} < ${min_size} (Tier: {tier.mode.value})"
            )

        return {
            "position_usd": size,
            "position_pct": size / balance if balance > 0 else 0,
            "can_trade": can_trade,
            "tier": tier.mode.value,
            "max_positions": tier.max_positions,
            "reason": f"{tier.mode.value} | Risk={tier.risk_pct * 100:.0f}%",
        }

    def check_heat(self, open_positions: List[Dict], balance: float) -> Dict:
        """فحص حرارة المحفظة مع مراعاة وضع النمو"""
        tier = self.get_tier(balance)
        total_risk = 0

        for pos in open_positions:
            entry = pos.get("entry_price", 0)
            sl = pos.get("stop_loss", 0)
            qty = pos.get("quantity", 0)
            if entry > 0 and sl > 0 and qty > 0:
                total_risk += abs(entry - sl) * qty

        heat_pct = (total_risk / balance) * 100 if balance > 0 else 0
        max_heat_pct = tier.max_heat_pct * 100

        return {
            "current_heat_pct": heat_pct,
            "max_heat_pct": max_heat_pct,
            "available_heat_pct": max(0, max_heat_pct - heat_pct),
            "can_open_new": heat_pct < max_heat_pct,
            "positions_count": len(open_positions),
            "max_positions": tier.max_positions,
            "tier": tier.mode.value,
        }

    def can_open_new_positions(
        self, open_positions: List[Dict], balance: float
    ) -> tuple:
        """هل يمكننا فتح صفقة جديدة؟"""
        heat = self.check_heat(open_positions, balance)

        if not heat["can_open_new"]:
            return (
                False,
                f"Heat limit reached ({heat['current_heat_pct']:.1f}%/{heat['max_heat_pct']:.1f}%)",
            )

        if heat["positions_count"] >= heat["max_positions"]:
            return (
                False,
                f"Max positions reached for {heat['tier']} ({heat['positions_count']}/{heat['max_positions']})",
            )

        # فحص الخسائر المتتالية
        if self.performance["consecutive_losses"] >= 5:
            return False, f"Cooling down: 5 consecutive losses"

        return True, "OK"

    def save_state(self):
        """حفظ حالة التعلم الذاتي"""
        try:
            os.makedirs(os.path.dirname(LEARNING_STATE_FILE), exist_ok=True)
            with open(LEARNING_STATE_FILE, "w") as f:
                json.dump(self.performance, f, indent=2)
        except Exception as e:
            self.logger.error(f"❌ Failed to save risk learning state: {e}")

    def update_growth_mode_in_db(
        self, db_manager, user_id: int, is_demo: bool, balance: float
    ):
        """تحديث وضع النمو في قاعدة البيانات"""
        try:
            tier = self.get_tier(balance)
            mode_name = tier.mode.name  # LAUNCH, GROWTH, STANDARD, PRO

            with db_manager.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE portfolio 
                    SET growth_mode = %s, updated_at = CURRENT_TIMESTAMP 
                    WHERE user_id = %s AND is_demo = %s
                    """,
                    (mode_name, user_id, is_demo),
                )
                conn.commit()

                if cursor.rowcount == 0:
                    # لم يتم التحديث، ربما العمود غير موجود أو الصف غير موجود
                    self.logger.debug(
                        f"⚠️ growth_mode update skipped for user {user_id} (demo={is_demo})"
                    )
                else:
                    self.logger.info(
                        f"📊 Updated growth_mode to {mode_name} for user {user_id}"
                    )
        except Exception as e:
            self.logger.debug(f"⚠️ Failed to update growth_mode in DB: {e}")

    def load_state(self):
        """تحميل حالة التعلم الذاتي"""
        try:
            if os.path.exists(LEARNING_STATE_FILE):
                with open(LEARNING_STATE_FILE, "r") as f:
                    data = json.load(f)
                    self.performance.update(data)
                    self.logger.info(
                        f"🧠 Loaded learning state: {self.performance['total_trades']} trades, "
                        f"WR={self.performance['winning_trades'] / max(self.performance['total_trades'], 1):.1%}"
                    )
            else:
                self.logger.info("🧠 No previous learning state found. Starting fresh.")
        except Exception as e:
            self.logger.error(f"❌ Failed to load risk learning state: {e}")
