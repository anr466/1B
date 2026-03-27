#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Exit Engine - أنظمة خروج ذكية متعددة ومستقلة
====================================================

❗ الخروج ليس واحداً - 5 أنظمة مستقلة:
1. WeaknessExit - خروج عند ضعف الاتجاه
2. StructureBreakExit - خروج عند كسر البنية
3. VolatilityShiftExit - خروج عند تغير التقلب
4. ReversalExit - خروج عند انعكاس مؤكد
5. EmergencyExit - خروج طوارئ لحماية رأس المال

الخروج يتم فقط عندما:
- يوجد سبب سوقي مُثبت
- أو تأكيد انعكاس واضح
"""

import logging
import pandas as pd
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ExitReason(Enum):
    """أسباب الخروج"""

    HOLD = "hold"
    WEAKNESS = "weakness"
    STRUCTURE_BREAK = "structure_break"
    VOLATILITY_SHIFT = "volatility_shift"
    REVERSAL_CONFIRMED = "reversal_confirmed"
    EMERGENCY = "emergency"
    TP_HIT = "tp_hit"
    SL_HIT = "sl_hit"
    TRAILING_STOP = "trailing_stop"
    TIME_DECAY = "time_decay"
    STAGNATION = "stagnation"


class ExitUrgency(Enum):
    """مستوى إلحاح الخروج"""

    NONE = "none"  # لا خروج
    LOW = "low"  # يمكن الانتظار
    MEDIUM = "medium"  # يُفضّل الخروج قريباً
    HIGH = "high"  # خروج الآن
    CRITICAL = "critical"  # خروج فوري - حماية رأس المال


@dataclass
class ExitSignal:
    """إشارة خروج من نظام واحد"""

    engine_name: str
    reason: ExitReason
    urgency: ExitUrgency
    confidence: float  # 0-100
    exit_pct: float  # 0-1 (نسبة الصفقة المطلوب إغلاقها)
    reasoning: str


@dataclass
class MultiExitDecision:
    """القرار النهائي المُجمّع من كل الأنظمة"""

    should_exit: bool
    exit_pct: float  # 0-1
    primary_reason: ExitReason
    urgency: ExitUrgency
    confidence: float
    signals: List[ExitSignal]
    reasoning: str

    def to_dict(self) -> Dict:
        return {
            "should_exit": self.should_exit,
            "exit_pct": self.exit_pct,
            "primary_reason": self.primary_reason.value,
            "urgency": self.urgency.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "signals_count": len(self.signals),
        }


class WeaknessExitEngine:
    """خروج عند ضعف الاتجاه"""

    def evaluate(self, df: pd.DataFrame, position: Dict) -> ExitSignal:
        try:
            close = df["close"]
            current = close.iloc[-1]
            entry_price = position.get("entry_price", current)
            pnl_pct = (current - entry_price) / entry_price

            # EMA convergence (trend weakening)
            ema_8 = close.ewm(span=8).mean()
            ema_21 = close.ewm(span=21).mean()

            ema_diff = (ema_8.iloc[-1] - ema_21.iloc[-1]) / ema_21.iloc[-1]
            ema_diff_prev = (
                (ema_8.iloc[-3] - ema_21.iloc[-3]) / ema_21.iloc[-3]
                if len(close) > 3
                else ema_diff
            )

            # RSI declining
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            rsi_declining = (
                rsi.iloc[-1] < rsi.iloc[-3] if len(rsi) > 3 else False
            )

            # MACD histogram shrinking
            ema_12 = close.ewm(span=12).mean()
            ema_26 = close.ewm(span=26).mean()
            macd = ema_12 - ema_26
            signal = macd.ewm(span=9).mean()
            hist = macd - signal
            hist_shrinking = (
                len(hist) > 3
                and hist.iloc[-1] < hist.iloc[-2] < hist.iloc[-3]
                and hist.iloc[-1] > 0
            )

            weakness_score = 0
            reasons = []

            # EMAs converging (trend losing strength)
            if ema_diff < ema_diff_prev and ema_diff < 0.005:
                weakness_score += 30
                reasons.append("EMAs converging")

            # RSI declining from high
            if rsi_declining and rsi.iloc[-1] < 55:
                weakness_score += 25
                reasons.append(f"RSI declining ({rsi.iloc[-1]:.0f})")

            # MACD histogram shrinking
            if hist_shrinking:
                weakness_score += 25
                reasons.append("MACD histogram shrinking")

            # Only exit on weakness if in profit (let it protect gains)
            if pnl_pct > 0.01 and weakness_score >= 50:
                # Scale exit by weakness
                exit_pct = min(0.5, weakness_score / 100)
                return ExitSignal(
                    engine_name="WeaknessExit",
                    reason=ExitReason.WEAKNESS,
                    urgency=(
                        ExitUrgency.MEDIUM
                        if weakness_score > 70
                        else ExitUrgency.LOW
                    ),
                    confidence=weakness_score,
                    exit_pct=exit_pct,
                    reasoning=f"Trend weakening: {
                        ', '.join(reasons)}",
                )

            return ExitSignal(
                "WeaknessExit",
                ExitReason.HOLD,
                ExitUrgency.NONE,
                0,
                0,
                "Trend healthy",
            )

        except Exception as e:
            logger.debug(f"WeaknessExit error: {e}")
            return ExitSignal(
                "WeaknessExit",
                ExitReason.HOLD,
                ExitUrgency.NONE,
                0,
                0,
                f"Error: {e}",
            )


class StructureBreakExitEngine:
    """خروج عند كسر بنية السوق"""

    def evaluate(self, df: pd.DataFrame, position: Dict) -> ExitSignal:
        try:
            close = df["close"]
            low = df["low"]
            high = df["high"]
            current = close.iloc[-1]

            # Find recent swing low (support)
            lookback = min(20, len(low) - 1)
            recent_lows = low.tail(lookback)
            swing_low = recent_lows.min()

            # Find recent swing high
            recent_highs = high.tail(lookback)
            recent_highs.max()

            # Previous structure lows (for lower low detection)
            if len(low) > 30:
                prev_lows = low.iloc[-30:-15]
                prev_swing_low = prev_lows.min()
            else:
                prev_swing_low = swing_low

            # Structure break = price closes below recent swing low
            # AND makes a lower low than previous swing low
            structure_broken = (
                current < swing_low and swing_low < prev_swing_low
            )

            # Also check if price broke below key EMA
            ema_55 = (
                close.ewm(span=55).mean().iloc[-1]
                if len(close) >= 55
                else close.mean()
            )
            below_key_ema = current < ema_55

            if structure_broken:
                return ExitSignal(
                    engine_name="StructureBreakExit",
                    reason=ExitReason.STRUCTURE_BREAK,
                    urgency=ExitUrgency.HIGH,
                    confidence=85,
                    exit_pct=0.7,  # Exit 70% on structure break
                    reasoning=f"Structure broken: price {
                        current:.2f} < swing low {
                        swing_low:.2f}",
                )

            if below_key_ema and current < swing_low:
                return ExitSignal(
                    engine_name="StructureBreakExit",
                    reason=ExitReason.STRUCTURE_BREAK,
                    urgency=ExitUrgency.MEDIUM,
                    confidence=65,
                    exit_pct=0.5,
                    reasoning=f"Below EMA55 ({ema_55:.2f}) and near swing low",
                )

            return ExitSignal(
                "StructureBreakExit",
                ExitReason.HOLD,
                ExitUrgency.NONE,
                0,
                0,
                "Structure intact",
            )

        except Exception as e:
            logger.debug(f"StructureBreakExit error: {e}")
            return ExitSignal(
                "StructureBreakExit",
                ExitReason.HOLD,
                ExitUrgency.NONE,
                0,
                0,
                f"Error: {e}",
            )


class VolatilityShiftExitEngine:
    """خروج عند تغير مفاجئ في التقلب"""

    def evaluate(self, df: pd.DataFrame, position: Dict) -> ExitSignal:
        try:
            close = df["close"]

            # ATR comparison: recent vs historical
            tr = pd.concat(
                [
                    df["high"] - df["low"],
                    abs(df["high"] - close.shift(1)),
                    abs(df["low"] - close.shift(1)),
                ],
                axis=1,
            ).max(axis=1)

            atr_recent = tr.tail(5).mean()
            atr_baseline = tr.tail(20).mean()

            if atr_baseline == 0:
                return ExitSignal(
                    "VolatilityShiftExit",
                    ExitReason.HOLD,
                    ExitUrgency.NONE,
                    0,
                    0,
                    "No data",
                )

            volatility_ratio = atr_recent / atr_baseline

            # Sudden volatility expansion (>2x normal)
            if volatility_ratio > 2.5:
                return ExitSignal(
                    engine_name="VolatilityShiftExit",
                    reason=ExitReason.VOLATILITY_SHIFT,
                    urgency=ExitUrgency.HIGH,
                    confidence=80,
                    exit_pct=0.5,
                    reasoning=f"Extreme volatility expansion: {
                        volatility_ratio:.1f}x normal",
                )
            elif volatility_ratio > 1.8:
                return ExitSignal(
                    engine_name="VolatilityShiftExit",
                    reason=ExitReason.VOLATILITY_SHIFT,
                    urgency=ExitUrgency.MEDIUM,
                    confidence=60,
                    exit_pct=0.3,
                    reasoning=f"High volatility expansion: {
                        volatility_ratio:.1f}x normal",
                )

            return ExitSignal(
                "VolatilityShiftExit",
                ExitReason.HOLD,
                ExitUrgency.NONE,
                0,
                0,
                f"Volatility normal ({
                    volatility_ratio:.1f}x)",
            )

        except Exception as e:
            logger.debug(f"VolatilityShiftExit error: {e}")
            return ExitSignal(
                "VolatilityShiftExit",
                ExitReason.HOLD,
                ExitUrgency.NONE,
                0,
                0,
                f"Error: {e}",
            )


class ReversalExitEngine:
    """خروج عند انعكاس مؤكد"""

    def evaluate(self, df: pd.DataFrame, position: Dict) -> ExitSignal:
        try:
            close = df["close"]

            # Multiple reversal confirmations needed
            confirmations = 0
            reasons = []

            # 1. MACD cross below signal
            ema_12 = close.ewm(span=12).mean()
            ema_26 = close.ewm(span=26).mean()
            macd = ema_12 - ema_26
            signal = macd.ewm(span=9).mean()

            if (
                macd.iloc[-1] < signal.iloc[-1]
                and macd.iloc[-2] >= signal.iloc[-2]
            ):
                confirmations += 1
                reasons.append("MACD bearish cross")

            # 2. RSI dropped below 50 from above
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            if rsi.iloc[-1] < 45 and rsi.iloc[-3] > 55:
                confirmations += 1
                reasons.append(
                    f"RSI reversal ({rsi.iloc[-3]:.0f}→{rsi.iloc[-1]:.0f})"
                )

            # 3. Price crossed below EMA21
            ema_21 = close.ewm(span=21).mean()
            if (
                close.iloc[-1] < ema_21.iloc[-1]
                and close.iloc[-2] >= ema_21.iloc[-2]
            ):
                confirmations += 1
                reasons.append("Price crossed below EMA21")

            # 4. Bearish engulfing or similar pattern
            if len(close) > 2:
                body_prev = close.iloc[-2] - df["open"].iloc[-2]
                body_curr = close.iloc[-1] - df["open"].iloc[-1]
                if (
                    body_prev > 0
                    and body_curr < 0
                    and abs(body_curr) > abs(body_prev)
                ):
                    confirmations += 1
                    reasons.append("Bearish engulfing")

            # Need at least 2 confirmations for reversal
            if confirmations >= 3:
                return ExitSignal(
                    engine_name="ReversalExit",
                    reason=ExitReason.REVERSAL_CONFIRMED,
                    urgency=ExitUrgency.HIGH,
                    confidence=min(95, 60 + confirmations * 10),
                    exit_pct=0.8,
                    reasoning=f"Reversal confirmed ({confirmations}/4): {', '.join(reasons)}",
                )
            elif confirmations >= 2:
                return ExitSignal(
                    engine_name="ReversalExit",
                    reason=ExitReason.REVERSAL_CONFIRMED,
                    urgency=ExitUrgency.MEDIUM,
                    confidence=min(80, 50 + confirmations * 10),
                    exit_pct=0.5,
                    reasoning=f"Possible reversal ({confirmations}/4): {', '.join(reasons)}",
                )

            return ExitSignal(
                "ReversalExit",
                ExitReason.HOLD,
                ExitUrgency.NONE,
                0,
                0,
                "No reversal signals",
            )

        except Exception as e:
            logger.debug(f"ReversalExit error: {e}")
            return ExitSignal(
                "ReversalExit",
                ExitReason.HOLD,
                ExitUrgency.NONE,
                0,
                0,
                f"Error: {e}",
            )


class EmergencyExitEngine:
    """خروج طوارئ - حماية رأس المال"""

    def __init__(self, max_loss_pct: float = 0.03, max_hold_hours: int = 72):
        self.max_loss_pct = max_loss_pct  # أقصى خسارة 3%
        self.max_hold_hours = max_hold_hours

    def evaluate(self, df: pd.DataFrame, position: Dict) -> ExitSignal:
        try:
            current_price = df["close"].iloc[-1]
            entry_price = position.get("entry_price", current_price)
            pnl_pct = (current_price - entry_price) / entry_price

            # 1. Emergency stop: max loss exceeded
            if pnl_pct < -self.max_loss_pct:
                return ExitSignal(
                    engine_name="EmergencyExit",
                    reason=ExitReason.EMERGENCY,
                    urgency=ExitUrgency.CRITICAL,
                    confidence=100,
                    exit_pct=1.0,
                    reasoning=f"MAX LOSS EXCEEDED: {pnl_pct * 100:.2f}% > {self.max_loss_pct * 100:.1f}%",
                )

            # 2. Flash crash detection (>5% drop in last 3 candles)
            if len(df) > 3:
                recent_drop = (
                    df["close"].iloc[-1] - df["close"].iloc[-3]
                ) / df["close"].iloc[-3]
                if recent_drop < -0.05:
                    return ExitSignal(
                        engine_name="EmergencyExit",
                        reason=ExitReason.EMERGENCY,
                        urgency=ExitUrgency.CRITICAL,
                        confidence=95,
                        exit_pct=1.0,
                        reasoning=f"Flash crash detected: {
                            recent_drop *
                            100:.1f}% in 3 candles",
                    )

            # 3. Time decay (stagnant position)
            hold_hours = position.get("hold_hours", 0)
            if hold_hours > self.max_hold_hours:
                if abs(pnl_pct) < 0.005:  # Less than 0.5% movement
                    return ExitSignal(
                        engine_name="EmergencyExit",
                        reason=ExitReason.STAGNATION,
                        urgency=ExitUrgency.MEDIUM,
                        confidence=70,
                        exit_pct=1.0,
                        reasoning=f"Stagnant position: {
                            hold_hours:.0f}h with {
                            pnl_pct * 100:.2f}% PnL",
                    )
                elif hold_hours > self.max_hold_hours * 1.5:
                    return ExitSignal(
                        engine_name="EmergencyExit",
                        reason=ExitReason.TIME_DECAY,
                        urgency=ExitUrgency.HIGH,
                        confidence=80,
                        exit_pct=1.0,
                        reasoning=f"Max hold time exceeded: {hold_hours:.0f}h",
                    )

            return ExitSignal(
                "EmergencyExit",
                ExitReason.HOLD,
                ExitUrgency.NONE,
                0,
                0,
                "No emergency",
            )

        except Exception as e:
            logger.debug(f"EmergencyExit error: {e}")
            return ExitSignal(
                "EmergencyExit",
                ExitReason.HOLD,
                ExitUrgency.NONE,
                0,
                0,
                f"Error: {e}",
            )


class MultiExitEngine:
    """
    مدير أنظمة الخروج المتعددة

    يدمج مخرجات 5 أنظمة خروج مستقلة ويتخذ قراراً واحداً:
    - HOLD: البقاء في الصفقة
    - PARTIAL_EXIT: خروج جزئي
    - FULL_EXIT: خروج كامل
    """

    def __init__(self, config: Optional[Dict] = None):
        config = config or {}
        self.logger = logger

        self.weakness_engine = WeaknessExitEngine()
        self.structure_engine = StructureBreakExitEngine()
        self.volatility_engine = VolatilityShiftExitEngine()
        self.reversal_engine = ReversalExitEngine()
        self.emergency_engine = EmergencyExitEngine(
            max_loss_pct=config.get("max_loss_pct", 0.03),
            max_hold_hours=config.get("max_hold_hours", 72),
        )

    def evaluate_exit(
        self, df: pd.DataFrame, position: Dict
    ) -> MultiExitDecision:
        """
        تقييم كل أنظمة الخروج وتجميع القرار النهائي

        Args:
            df: بيانات OHLCV
            position: معلومات الصفقة {'entry_price', 'hold_hours', 'quantity', ...}

        Returns:
            MultiExitDecision
        """
        try:
            # تشغيل كل الأنظمة بالتوازي
            signals = [
                self.emergency_engine.evaluate(df, position),
                self.reversal_engine.evaluate(df, position),
                self.structure_engine.evaluate(df, position),
                self.volatility_engine.evaluate(df, position),
                self.weakness_engine.evaluate(df, position),
            ]

            # فلترة الإشارات النشطة (غير HOLD)
            active_signals = [
                s for s in signals if s.reason != ExitReason.HOLD
            ]

            if not active_signals:
                return MultiExitDecision(
                    should_exit=False,
                    exit_pct=0,
                    primary_reason=ExitReason.HOLD,
                    urgency=ExitUrgency.NONE,
                    confidence=0,
                    signals=signals,
                    reasoning="All systems: HOLD",
                )

            # ترتيب بالأولوية (الأعلى إلحاحاً أولاً)
            urgency_order = {
                ExitUrgency.CRITICAL: 5,
                ExitUrgency.HIGH: 4,
                ExitUrgency.MEDIUM: 3,
                ExitUrgency.LOW: 2,
                ExitUrgency.NONE: 1,
            }
            active_signals.sort(
                key=lambda s: (urgency_order.get(s.urgency, 0), s.confidence),
                reverse=True,
            )

            primary = active_signals[0]

            # حساب نسبة الخروج المُجمّعة
            # إذا CRITICAL → خروج كامل فوراً
            if primary.urgency == ExitUrgency.CRITICAL:
                exit_pct = 1.0
            else:
                # تجميع من كل الأنظمة
                exit_pct = max(s.exit_pct for s in active_signals)
                # إذا أكثر من نظامين يطلب الخروج → زد النسبة
                if len(active_signals) >= 3:
                    exit_pct = min(1.0, exit_pct + 0.2)
                elif len(active_signals) >= 2:
                    exit_pct = min(1.0, exit_pct + 0.1)

            # حساب الثقة المُجمّعة
            avg_confidence = sum(s.confidence for s in active_signals) / len(
                active_signals
            )
            max_confidence = max(s.confidence for s in active_signals)
            combined_confidence = avg_confidence * 0.4 + max_confidence * 0.6

            # بناء التحليل
            reasoning_parts = [
                f"{s.engine_name}: {s.reasoning}" for s in active_signals[:3]
            ]
            reasoning = " | ".join(reasoning_parts)

            decision = MultiExitDecision(
                should_exit=True,
                exit_pct=exit_pct,
                primary_reason=primary.reason,
                urgency=primary.urgency,
                confidence=combined_confidence,
                signals=signals,
                reasoning=reasoning,
            )

            self.logger.info(
                f"🚪 Exit Decision: {primary.reason.value} | "
                f"Urgency: {primary.urgency.value} | "
                f"Exit: {exit_pct * 100:.0f}% | "
                f"Confidence: {combined_confidence:.0f}% | "
                f"Engines: {len(active_signals)}/5"
            )

            return decision

        except Exception as e:
            self.logger.error(f"MultiExitEngine error: {e}")
            return MultiExitDecision(
                should_exit=False,
                exit_pct=0,
                primary_reason=ExitReason.HOLD,
                urgency=ExitUrgency.NONE,
                confidence=0,
                signals=[],
                reasoning=f"Error: {e}",
            )


# Singleton
_multi_exit_engine = None


def get_multi_exit_engine(config: Optional[Dict] = None) -> MultiExitEngine:
    global _multi_exit_engine
    if _multi_exit_engine is None:
        _multi_exit_engine = MultiExitEngine(config)
    return _multi_exit_engine
