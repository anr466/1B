#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Exit Engine — محرك الخروج الذكي
======================================
يدير خروج الصفقات عبر 4 مراحل متكاملة:
1. التأمين (Secure the Bag): إغلاق 50% عند RR 1.5:1
2. نقطة التعادل (Break Even): نقل SL لسعر الدخول عند RR 2:1
3. الزيل الذكي (Dynamic Trailing): Trailing Stop ديناميكي يعتمد على ATR
4. التقييم المعرفي (Cognitive Override): خروج استباقي عند تغير النظام

يعمل بشكل مستقل عن ExecutorWorker ويتكامل معه عبر واجهة موحدة.
"""

import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExitDecision:
    """قرار الخروج من المحرك"""
    action: str  # NONE, PARTIAL_CLOSE_50, UPDATE_SL, CLOSE_ALL
    reason: str
    new_sl: Optional[float] = None
    new_phase: Optional[str] = None
    close_quantity: Optional[float] = None
    exit_price: Optional[float] = None


class SmartExitEngine:
    """
    محرك الخروج الذكي.
    يقيم الصفقة كل 5 ثوانٍ ويقرر الإجراء الأمثل.
    """

    def __init__(self, atr_multiplier: float = 2.5):
        self.atr_multiplier = atr_multiplier

    def evaluate(
        self,
        position: Dict,
        current_price: float,
        atr: float,
        regime: str = "UNKNOWN",
        regime_confidence: float = 0.0,
    ) -> ExitDecision:
        """
        تقييم الصفقة واتخاذ قرار الخروج.
        
        Args:
            position: بيانات الصفقة من قاعدة البيانات
            current_price: السعر الحالي
            atr: مؤشر التقلب (ATR)
            regime: نظام السوق الحالي
            regime_confidence: ثقة النظام
            
        Returns:
            ExitDecision: القرار المتخذ
        """
        pos_type = position.get("position_type", "LONG")
        entry = position.get("entry_price", 0)
        sl = position.get("stop_loss", 0)
        tp = position.get("take_profit", 0)
        phase = position.get("exit_phase", "ACTIVE")
        quantity = position.get("quantity", 0)
        quantity_remaining = position.get("quantity_remaining", quantity)
        break_even_activated = position.get("break_even_activated", False)

        # حساب المخاطرة والربح
        risk = abs(entry - sl) if sl > 0 else 0
        if pos_type == "LONG":
            reward = current_price - entry
        else:
            reward = entry - current_price
        rr = reward / risk if risk > 0 else 0

        # 4. التقييم المعرفي (Cognitive Override) - الأولوية القصوى
        # إذا تغير النظام بشكل جذري، نخرج فوراً
        if self._should_cognitive_exit(regime, regime_confidence, pos_type, entry, current_price):
            return ExitDecision(
                action="CLOSE_ALL",
                reason=f"Cognitive Override: Regime changed to {regime} (Confidence: {regime_confidence:.2f})",
                exit_price=current_price,
            )

        # 3. الزيل الذكي (Dynamic Trailing)
        if phase in ("BREAK_EVEN", "TRAILING"):
            decision = self._dynamic_trail(position, current_price, atr, rr)
            if decision:
                return decision

        # 2. نقطة التعادل (Break Even)
        if phase == "SECURED" and not break_even_activated:
            if rr >= 2.0:
                new_sl = entry + (risk * 0.1) if pos_type == "LONG" else entry - (risk * 0.1)
                return ExitDecision(
                    action="UPDATE_SL",
                    reason=f"Break Even activated at RR {rr:.2f}:1",
                    new_sl=new_sl,
                    new_phase="BREAK_EVEN",
                )

        # 1. التأمين (Secure the Bag)
        if phase == "ACTIVE" and rr >= 1.5:
            close_qty = quantity_remaining * 0.5
            return ExitDecision(
                action="PARTIAL_CLOSE_50",
                reason=f"Secure the Bag at RR {rr:.2f}:1",
                close_quantity=close_qty,
                exit_price=current_price,
                new_phase="SECURED",
            )

        # فحص وقف الخسارة العادي
        if self._hit_stop_loss(pos_type, current_price, sl):
            return ExitDecision(
                action="CLOSE_ALL",
                reason="Stop Loss Hit",
                exit_price=sl,
            )

        # فحص الهدف العادي
        if self._hit_take_profit(pos_type, current_price, tp):
            return ExitDecision(
                action="CLOSE_ALL",
                reason="Take Profit Hit",
                exit_price=tp,
            )

        return ExitDecision(action="NONE", reason="Holding")

    def _should_cognitive_exit(self, regime: str, confidence: float, pos_type: str, entry_price: float = 0, current_price: float = 0) -> bool:
        """هل يجب الخروج بناءً على تغير النظام؟"""
        if regime == "CHOPPY" and confidence > 0.6:
            return True
        if pos_type == "LONG" and regime == "STRONG_TREND" and confidence > 0.7:
            if entry_price > 0 and current_price < entry_price:
                return True
        if pos_type == "SHORT" and regime == "STRONG_TREND" and confidence > 0.7:
            if entry_price > 0 and current_price > entry_price:
                return True
        return False

    def _dynamic_trail(
        self, position: Dict, current_price: float, atr: float, rr: float
    ) -> Optional[ExitDecision]:
        """حساب Trailing Stop ديناميكي"""
        pos_type = position.get("position_type", "LONG")
        highest = position.get("highest_price", position.get("entry_price", 0))
        current_sl = position.get("stop_loss", 0)
        
        # حساب الـ Trailing Stop الجديد
        if pos_type == "LONG":
            new_trail = highest - (self.atr_multiplier * atr)
            # لا ننزل الـ SL أبداً
            final_sl = max(current_sl, new_trail)
            # إذا ضرب السعر الـ Trail
            if current_price <= final_sl:
                return ExitDecision(
                    action="CLOSE_ALL",
                    reason=f"Dynamic Trailing Stop Hit at {final_sl:.4f}",
                    exit_price=final_sl,
                )
            # فقط نحدث إذا كان هناك تغيير ملحوظ (> 0.1%)
            if current_sl > 0 and abs(final_sl - current_sl) / current_sl < 0.001:
                return None
            return ExitDecision(
                action="UPDATE_SL",
                reason=f"Dynamic Trail updated to {final_sl:.4f}",
                new_sl=final_sl,
                new_phase="TRAILING",
            )
        else:  # SHORT
            new_trail = highest + (self.atr_multiplier * atr)
            final_sl = min(current_sl, new_trail) if current_sl > 0 else new_trail
            if current_price >= final_sl:
                return ExitDecision(
                    action="CLOSE_ALL",
                    reason=f"Dynamic Trailing Stop Hit at {final_sl:.4f}",
                    exit_price=final_sl,
                )
            # فقط نحدث إذا كان هناك تغيير ملحوظ (> 0.1%)
            if current_sl > 0 and abs(final_sl - current_sl) / current_sl < 0.001:
                return None
            return ExitDecision(
                action="UPDATE_SL",
                reason=f"Dynamic Trail updated to {final_sl:.4f}",
                new_sl=final_sl,
                new_phase="TRAILING",
            )

    def _hit_stop_loss(self, pos_type: str, current_price: float, sl: float) -> bool:
        if sl <= 0:
            return False
        return current_price <= sl if pos_type == "LONG" else current_price >= sl

    def _hit_take_profit(self, pos_type: str, current_price: float, tp: float) -> bool:
        if tp <= 0:
            return False
        return current_price >= tp if pos_type == "LONG" else current_price <= tp
