#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cognitive Orchestrator - المُنسّق المعرفي الرئيسي
=================================================

الدماغ المركزي الذي يربط كل الأنظمة:
1. Market Understanding (MarketStateDetector + AssetClassifier)
2. Market Surveillance (continuous monitoring)
3. Multiple Entry Engines (via CognitiveTradingEngine)
4. Trade Management (dynamic SL, partial exits)
5. Multiple Exit Engines (5 independent systems)
6. Decision Brain (weighted signal aggregation)

الدورة المعرفية الإلزامية:
READ → ANALYZE → THINK → INFER → DECIDE → EXECUTE → MONITOR → ADAPT

القواعد الصارمة:
- لا دخول بدون سياق سوقي واضح
- لا خروج بدون سبب مُثبت
- السوق هو الحكم النهائي
- رأس المال أولوية
"""

import logging
import pandas as pd
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Optional: market state detector (may not exist)
try:
    from .market_state_detector import (
        MarketState,
        MarketStateResult,
        get_market_state_detector,
    )

    _MARKET_STATE_AVAILABLE = True
except ImportError:
    _MARKET_STATE_AVAILABLE = False
    MarketState = None
    MarketStateResult = None
    get_market_state_detector = None

# Optional: market surveillance (may not exist)
try:
    from .market_surveillance_engine import (
        MarketQuality,
        MarketPhase,
        BehaviorSignal,
        SurveillanceReport,
        get_surveillance_engine,
    )

    _SURVEILLANCE_AVAILABLE = True
except ImportError:
    _SURVEILLANCE_AVAILABLE = False
    MarketQuality = None
    MarketPhase = None
    BehaviorSignal = None
    SurveillanceReport = None
    get_surveillance_engine = None

from .multi_exit_engine import ExitUrgency, get_multi_exit_engine

logger = logging.getLogger(__name__)


class CognitiveAction(Enum):
    """القرارات الممكنة"""

    ENTER = "enter"
    HOLD = "hold"
    SCALE_IN = "scale_in"
    PARTIAL_EXIT = "partial_exit"
    FULL_EXIT = "full_exit"
    STAY_OUT = "stay_out"


class EntryStrategy(Enum):
    """استراتيجيات الدخول المتاحة"""

    TREND_CONTINUATION = "trend_continuation"
    PULLBACK_PRECISION = "pullback_precision"
    BREAKOUT_CONFIRMATION = "breakout_confirmation"
    VOLATILITY_EXPANSION = "volatility_expansion"
    REVERSAL_HIGH_CONF = "reversal_high_confidence"
    NONE = "none"


@dataclass
class CognitiveDecision:
    """القرار المعرفي النهائي"""

    action: CognitiveAction
    symbol: str
    timestamp: datetime

    # سياق السوق
    market_state: str
    market_quality: str
    market_phase: str

    # تفاصيل الدخول (إن وُجد)
    entry_strategy: EntryStrategy
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size_pct: Optional[float] = None

    # تفاصيل الخروج (إن وُجد)
    exit_pct: float = 0.0
    exit_reason: str = ""

    # النقاط
    confidence: float = 0.0
    opportunity_score: float = 0.0
    risk_score: float = 0.0

    # التحليل
    reasoning: str = ""
    entry_logic: str = ""
    exit_logic: str = ""
    invalidation: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "action": self.action.value,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "market_state": self.market_state,
            "market_quality": self.market_quality,
            "market_phase": self.market_phase,
            "entry_strategy": self.entry_strategy.value,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "position_size_pct": self.position_size_pct,
            "exit_pct": self.exit_pct,
            "exit_reason": self.exit_reason,
            "confidence": self.confidence,
            "opportunity_score": self.opportunity_score,
            "risk_score": self.risk_score,
            "reasoning": self.reasoning,
            "entry_logic": self.entry_logic,
            "exit_logic": self.exit_logic,
            "invalidation": self.invalidation,
            "warnings": self.warnings,
        }


class CognitiveOrchestrator:
    """
    المُنسّق المعرفي الرئيسي

    ينفذ الدورة المعرفية الكاملة:
    READ → ANALYZE → THINK → INFER → DECIDE → EXECUTE → MONITOR → ADAPT
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logger

        # الأنظمة الأساسية
        self.market_detector = None
        if _MARKET_STATE_AVAILABLE and get_market_state_detector:
            self.market_detector = get_market_state_detector(
                self.config.get("market_state", {})
            )
        self.surveillance = None
        if _SURVEILLANCE_AVAILABLE and get_surveillance_engine:
            self.surveillance = get_surveillance_engine(
                self.config.get("surveillance", {})
            )
        self.multi_exit = get_multi_exit_engine(
            self.config.get("exit", {"max_loss_pct": 0.02, "max_hold_hours": 72})
        )

        # ذاكرة التعلّم
        self._trade_history: List[Dict] = []
        self._adaptation_log: List[Dict] = []

        # إعدادات
        self.min_opportunity_score = self.config.get("min_opportunity_score", 60)
        self.max_risk_score = self.config.get("max_risk_score", 58)
        self.min_entry_confidence = self.config.get("min_entry_confidence", 72)

        # تصنيف العملات حسب الفئة - كل فئة لها حد ثقة مختلف
        self.coin_categories = {
            "large_cap": ["ETHUSDT", "BNBUSDT", "SOLUSDT", "BTCUSDT"],
            "mid_cap": ["AVAXUSDT", "NEARUSDT", "LINKUSDT", "APTUSDT"],
            "small_cap": ["SUIUSDT", "ARBUSDT", "INJUSDT"],
        }
        # Mid cap needs higher confidence (16.7% WR in backtest)
        self.category_confidence_adj = {
            "large_cap": 0,
            "mid_cap": 8,  # +8% confidence required
            "small_cap": 0,
        }

        self.logger.info("🧠 Cognitive Orchestrator initialized")

    # ==========================================
    # الدورة المعرفية الكاملة - للدخول الجديد
    # ==========================================

    def analyze_entry(
        self,
        symbol: str,
        df_4h: pd.DataFrame,
        df_1h: Optional[pd.DataFrame] = None,
        df_15m: Optional[pd.DataFrame] = None,
    ) -> CognitiveDecision:
        """
        تحليل فرصة دخول جديدة عبر الدورة المعرفية الكاملة

        READ → ANALYZE → THINK → INFER → DECIDE
        """
        try:
            self.logger.info(f"🧠 [{symbol}] Starting cognitive entry analysis")

            # ========== 1. READ: قراءة البيانات ==========
            if df_4h is None or len(df_4h) < 50:
                return self._stay_out(symbol, "Insufficient data")

            current_price = df_4h["close"].iloc[-1]

            # ========== 2. ANALYZE: تحليل السلوك ==========
            # 2a. فهم حالة السوق
            market_state = self.market_detector.detect_state(df_4h, symbol)

            # 2b. مراقبة السوق
            surveillance = self.surveillance.survey(symbol, df_4h, df_1h)

            # رفض فوري إذا السوق غير صالح
            if not surveillance.is_tradeable:
                return self._stay_out(
                    symbol,
                    f"Market not tradeable: {surveillance.market_quality.value}",
                    market_state=market_state.state.value,
                    market_quality=surveillance.market_quality.value,
                    market_phase=surveillance.market_phase.value,
                    risk_score=surveillance.risk_score,
                )

            # رفض فوري في downtrend أو near_top
            if market_state.state in [
                MarketState.DOWNTREND,
                MarketState.NEAR_TOP,
            ]:
                return self._stay_out(
                    symbol,
                    f"Unfavorable market state: {market_state.state.value}",
                    market_state=market_state.state.value,
                    market_quality=surveillance.market_quality.value,
                    market_phase=surveillance.market_phase.value,
                    risk_score=surveillance.risk_score,
                )

            # ===== 2c. فحص نقاط الفرصة والمخاطرة =====
            if surveillance.opportunity_score < self.min_opportunity_score:
                return self._stay_out(
                    symbol,
                    f"Opportunity too low: {surveillance.opportunity_score:.0f}% < {
                        self.min_opportunity_score
                    }%",
                    market_state=market_state.state.value,
                    market_quality=surveillance.market_quality.value,
                    market_phase=surveillance.market_phase.value,
                    opportunity_score=surveillance.opportunity_score,
                    risk_score=surveillance.risk_score,
                )

            if surveillance.risk_score > self.max_risk_score:
                return self._stay_out(
                    symbol,
                    f"Risk too high: {surveillance.risk_score:.0f}% > {
                        self.max_risk_score
                    }%",
                    market_state=market_state.state.value,
                    market_quality=surveillance.market_quality.value,
                    market_phase=surveillance.market_phase.value,
                    opportunity_score=surveillance.opportunity_score,
                    risk_score=surveillance.risk_score,
                )

            # ========== 3. THINK: تقييم السيناريوهات ==========
            # اختيار أفضل استراتيجية دخول بناءً على حالة السوق
            entry_strategy, entry_signal = self._select_best_entry(
                symbol, df_4h, df_1h, df_15m, market_state, surveillance
            )

            if entry_strategy == EntryStrategy.NONE or entry_signal is None:
                return self._stay_out(
                    symbol,
                    f"No valid entry strategy for {market_state.state.value}",
                    market_state=market_state.state.value,
                    market_quality=surveillance.market_quality.value,
                    market_phase=surveillance.market_phase.value,
                    opportunity_score=surveillance.opportunity_score,
                    risk_score=surveillance.risk_score,
                )

            # ========== 4. INFER: استنتاج الاحتمالات ==========
            confidence = entry_signal.get("confidence", 0)

            # تعديل الثقة بناءً على سياق السوق
            confidence = self._adjust_confidence(confidence, market_state, surveillance)

            # تعديل حد الثقة حسب فئة العملة
            category_adj = 0
            for cat, coins in self.coin_categories.items():
                if symbol in coins:
                    category_adj = self.category_confidence_adj.get(cat, 0)
                    break

            required_confidence = self.min_entry_confidence + category_adj

            # رفض إذا الثقة منخفضة
            if confidence < required_confidence:
                return self._stay_out(
                    symbol,
                    f"Confidence too low: {confidence:.0f}% < {required_confidence}%",
                    market_state=market_state.state.value,
                    market_quality=surveillance.market_quality.value,
                    market_phase=surveillance.market_phase.value,
                    opportunity_score=surveillance.opportunity_score,
                    risk_score=surveillance.risk_score,
                )

            # ========== 5. DECIDE: اتخاذ القرار ==========
            entry_price = entry_signal.get("entry_price", current_price)
            stop_loss = entry_signal.get("stop_loss", entry_price * 0.98)
            take_profit = entry_signal.get("take_profit", entry_price * 1.045)

            # ===== 5a. التحقق من نسبة المخاطرة/المكافأة (R:R >= 1.8) =====
            sl_dist = abs(entry_price - stop_loss)
            tp_dist = abs(take_profit - entry_price)
            rr_ratio = tp_dist / sl_dist if sl_dist > 0 else 0

            if rr_ratio < 1.8:
                return self._stay_out(
                    symbol,
                    f"R:R too low: 1:{rr_ratio:.1f} < 1:1.8",
                    market_state=market_state.state.value,
                    market_quality=surveillance.market_quality.value,
                    market_phase=surveillance.market_phase.value,
                    opportunity_score=surveillance.opportunity_score,
                    risk_score=surveillance.risk_score,
                )

            # حجم المركز بناءً على الثقة والمخاطرة
            position_size_pct = self._calculate_position_size(
                confidence, surveillance.risk_score, market_state
            )

            # بناء نقطة الإبطال
            invalidation = self._define_invalidation(
                entry_strategy, entry_price, stop_loss, market_state
            )

            # بناء منطق الدخول
            entry_logic = (
                f"Strategy: {entry_strategy.value} | "
                f"Market: {market_state.state.value} (conf {
                    market_state.confidence:.0f}%) | "
                f"Phase: {surveillance.market_phase.value} | "
                f"Quality: {surveillance.market_quality.value} | "
                f"Signal: {entry_signal.get('signal_type', 'combined')}"
            )

            # بناء منطق الخروج
            sl_pct = abs(entry_price - stop_loss) / entry_price * 100
            tp_pct = abs(take_profit - entry_price) / entry_price * 100
            rr = tp_pct / sl_pct if sl_pct > 0 else 0
            exit_logic = (
                f"SL: ${stop_loss:.2f} (-{sl_pct:.1f}%) | "
                f"TP: ${take_profit:.2f} (+{tp_pct:.1f}%) | "
                f"R:R = 1:{rr:.1f} | "
                f"Multi-exit system active"
            )

            self.logger.info(
                f"✅ [{symbol}] ENTER via {entry_strategy.value} | "
                f"Conf: {confidence:.0f}% | R:R: 1:{rr:.1f} | "
                f"Size: {position_size_pct * 100:.1f}%"
            )

            return CognitiveDecision(
                action=CognitiveAction.ENTER,
                symbol=symbol,
                timestamp=datetime.now(),
                market_state=market_state.state.value,
                market_quality=surveillance.market_quality.value,
                market_phase=surveillance.market_phase.value,
                entry_strategy=entry_strategy,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size_pct=position_size_pct,
                confidence=confidence,
                opportunity_score=surveillance.opportunity_score,
                risk_score=surveillance.risk_score,
                reasoning=f"Cognitive entry via {entry_strategy.value}",
                entry_logic=entry_logic,
                exit_logic=exit_logic,
                invalidation=invalidation,
                warnings=surveillance.warnings,
            )

        except Exception as e:
            self.logger.error(f"❌ [{symbol}] Cognitive analysis error: {e}")
            return self._stay_out(symbol, f"Error: {e}")

    # ==========================================
    # تقييم الخروج - للصفقات المفتوحة
    # ==========================================

    def analyze_exit(
        self, symbol: str, df: pd.DataFrame, position: Dict
    ) -> CognitiveDecision:
        """
        تحليل صفقة مفتوحة عبر الدورة المعرفية

        MONITOR → ANALYZE → THINK → DECIDE
        """
        try:
            current_price = df["close"].iloc[-1]
            entry_price = position.get("entry_price", current_price)
            pnl_pct = (current_price - entry_price) / entry_price

            # 1. MONITOR: مراقبة السوق
            surveillance = self.surveillance.survey(symbol, df)

            # 2. ANALYZE: تشغيل أنظمة الخروج المتعددة
            exit_decision = self.multi_exit.evaluate_exit(df, position)

            # 3. THINK: تقييم قرار الخروج في سياق السوق
            if exit_decision.should_exit:
                # خروج طوارئ = تنفيذ فوري
                if exit_decision.urgency == ExitUrgency.CRITICAL:
                    action = CognitiveAction.FULL_EXIT
                    exit_pct = 1.0
                # خروج جزئي أو كامل بناءً على النسبة
                elif exit_decision.exit_pct >= 0.7:
                    action = CognitiveAction.FULL_EXIT
                    exit_pct = 1.0
                elif exit_decision.exit_pct > 0:
                    action = CognitiveAction.PARTIAL_EXIT
                    exit_pct = exit_decision.exit_pct
                else:
                    action = CognitiveAction.HOLD
                    exit_pct = 0

                return CognitiveDecision(
                    action=action,
                    symbol=symbol,
                    timestamp=datetime.now(),
                    market_state=surveillance.market_quality.value,
                    market_quality=surveillance.market_quality.value,
                    market_phase=surveillance.market_phase.value,
                    entry_strategy=EntryStrategy.NONE,
                    exit_pct=exit_pct,
                    exit_reason=exit_decision.primary_reason.value,
                    confidence=exit_decision.confidence,
                    opportunity_score=surveillance.opportunity_score,
                    risk_score=surveillance.risk_score,
                    reasoning=exit_decision.reasoning,
                    exit_logic=f"Exit {exit_pct * 100:.0f}%: {
                        exit_decision.primary_reason.value
                    }",
                    warnings=surveillance.warnings,
                )

            # 4. DECIDE: البقاء في الصفقة
            return CognitiveDecision(
                action=CognitiveAction.HOLD,
                symbol=symbol,
                timestamp=datetime.now(),
                market_state=surveillance.market_quality.value,
                market_quality=surveillance.market_quality.value,
                market_phase=surveillance.market_phase.value,
                entry_strategy=EntryStrategy.NONE,
                confidence=100 - surveillance.risk_score,
                opportunity_score=surveillance.opportunity_score,
                risk_score=surveillance.risk_score,
                reasoning=f"HOLD: PnL {pnl_pct * 100:+.2f}% | Market: {surveillance.market_quality.value}",
                warnings=surveillance.warnings,
            )

        except Exception as e:
            self.logger.error(f"❌ [{symbol}] Exit analysis error: {e}")
            return CognitiveDecision(
                action=CognitiveAction.HOLD,
                symbol=symbol,
                timestamp=datetime.now(),
                market_state="error",
                market_quality="error",
                market_phase="error",
                entry_strategy=EntryStrategy.NONE,
                reasoning=f"Error: {e}",
            )

    # ==========================================
    # أنظمة الدخول المتعددة
    # ==========================================

    def _select_best_entry(
        self,
        symbol: str,
        df_4h: pd.DataFrame,
        df_1h: Optional[pd.DataFrame],
        df_15m: Optional[pd.DataFrame],
        market_state: MarketStateResult,
        surveillance: SurveillanceReport,
    ) -> Tuple[EntryStrategy, Optional[Dict]]:
        """
        اختيار أفضل استراتيجية دخول بناءً على حالة السوق

        كل استراتيجية لها شروط سوق محددة وحالات فشل معروفة
        """
        candidates = []

        # 1. Trend Continuation - أفضل في UPTREND مع ADX > 25
        if market_state.state == MarketState.UPTREND:
            signal = self._check_trend_continuation(df_4h, df_1h, market_state)
            if signal:
                candidates.append((EntryStrategy.TREND_CONTINUATION, signal))

        # 2. Pullback Precision - أفضل في UPTREND مع تراجع
        if market_state.state in [MarketState.UPTREND, MarketState.RANGE]:
            signal = self._check_pullback_entry(df_4h, df_1h, market_state)
            if signal:
                candidates.append((EntryStrategy.PULLBACK_PRECISION, signal))

        # 3. Breakout Confirmation - أفضل في RANGE مع تضييق
        if market_state.state == MarketState.RANGE:
            signal = self._check_breakout_entry(df_4h, market_state, surveillance)
            if signal:
                candidates.append((EntryStrategy.BREAKOUT_CONFIRMATION, signal))

        # 4. Volatility Expansion - أفضل بعد انكماش التقلب
        if surveillance.volatility_state in ["low", "normal"]:
            signal = self._check_volatility_expansion(df_4h, market_state)
            if signal:
                candidates.append((EntryStrategy.VOLATILITY_EXPANSION, signal))

        # 5. Reversal (High Confidence Only) - أفضل في NEAR_BOTTOM
        if market_state.state == MarketState.NEAR_BOTTOM:
            signal = self._check_reversal_entry(df_4h, df_1h, market_state)
            if signal:
                candidates.append((EntryStrategy.REVERSAL_HIGH_CONF, signal))

        if not candidates:
            return EntryStrategy.NONE, None

        # اختيار الأفضل بالثقة
        candidates.sort(key=lambda x: x[1].get("confidence", 0), reverse=True)
        best = candidates[0]

        self.logger.info(
            f"🎯 [{symbol}] Best entry: {best[0].value} | "
            f"Confidence: {best[1].get('confidence', 0):.0f}% | "
            f"Candidates: {len(candidates)}"
        )

        return best

    def _check_trend_continuation(
        self,
        df_4h: pd.DataFrame,
        df_1h: Optional[pd.DataFrame],
        market_state: MarketStateResult,
    ) -> Optional[Dict]:
        """
        Trend Continuation Engine

        لماذا الآن؟ الاتجاه قوي ومستمر
        لماذا هذا الاتجاه؟ ADX > 25, EMAs aligned
        ما يبطل الدخول؟ ADX < 20 أو كسر EMA21
        """
        try:
            close = df_4h["close"]
            current = close.iloc[-1]

            # شروط الدخول
            ema_8 = close.ewm(span=8).mean()
            ema_21 = close.ewm(span=21).mean()
            ema_55 = close.ewm(span=55).mean() if len(close) >= 55 else ema_21

            # EMAs aligned (8 > 21 > 55)
            ema_aligned = (
                ema_8.iloc[-1] > ema_21.iloc[-1] > ema_55.iloc[-1]
                and current > ema_8.iloc[-1]
            )

            # Trend strength (require stronger ADX)
            strong_trend = market_state.trend_strength >= 30

            # Price pulling back to EMA (not too far)
            dist_from_ema8 = (current - ema_8.iloc[-1]) / ema_8.iloc[-1]
            near_ema = dist_from_ema8 < 0.015  # Within 1.5% of EMA8

            # Momentum positive
            momentum_ok = market_state.momentum > 15

            # Volume confirmation
            vol = df_4h["volume"]
            vol_ratio = (
                vol.iloc[-1] / vol.rolling(20).mean().iloc[-1] if len(vol) >= 20 else 1
            )
            vol_ok = vol_ratio > 0.8

            if ema_aligned and strong_trend and momentum_ok and vol_ok:
                confidence = min(
                    88,
                    48
                    + market_state.trend_strength * 0.8
                    + market_state.momentum * 0.2,
                )
                if near_ema:
                    confidence += 8
                if vol_ratio > 1.2:
                    confidence += 5

                sl = min(ema_21.iloc[-1], current * 0.975)
                tp = current * 1.055

                return {
                    "signal_type": "TREND_CONTINUATION",
                    "entry_price": current,
                    "stop_loss": sl,
                    "take_profit": tp,
                    "confidence": confidence,
                    "reasons": [
                        f"Strong trend (ADX={market_state.trend_strength:.0f})",
                        f"EMAs aligned",
                        f"Momentum positive ({market_state.momentum:.0f})",
                    ],
                }
            return None
        except Exception as e:
            self.logger.debug(f"Trend continuation check error: {e}")
            return None

    def _check_pullback_entry(
        self,
        df_4h: pd.DataFrame,
        df_1h: Optional[pd.DataFrame],
        market_state: MarketStateResult,
    ) -> Optional[Dict]:
        """
        Pullback Precision Engine

        لماذا الآن؟ تراجع إلى منطقة دعم ديناميكية
        لماذا هذه النقطة؟ EMA21 + RSI pullback zone
        ما يبطل الدخول؟ كسر EMA55 أو RSI < 30
        """
        try:
            close = df_4h["close"]
            current = close.iloc[-1]

            ema_21 = close.ewm(span=21).mean()
            ema_55 = close.ewm(span=55).mean() if len(close) >= 55 else ema_21

            # Price pulled back to EMA21 zone (within 1%)
            dist_from_ema21 = (current - ema_21.iloc[-1]) / ema_21.iloc[-1]
            at_pullback_zone = -0.005 <= dist_from_ema21 <= 0.012

            # Still above EMA55 (trend intact)
            above_ema55 = current > ema_55.iloc[-1]

            # RSI in pullback zone (40-52 - tighter)
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = (100 - (100 / (1 + rs))).iloc[-1]
            rsi_pullback = 40 <= rsi <= 52

            # Bullish candle forming (MANDATORY bounce signal)
            bullish_candle = close.iloc[-1] > df_4h["open"].iloc[-1]

            # Volume not dropping (buying interest present)
            vol = df_4h["volume"]
            vol_ratio = (
                vol.iloc[-1] / vol.rolling(20).mean().iloc[-1] if len(vol) >= 20 else 1
            )

            if at_pullback_zone and above_ema55 and rsi_pullback and bullish_candle:
                confidence = 52
                if market_state.state == MarketState.UPTREND:
                    confidence += 15
                if vol_ratio > 1.0:
                    confidence += 8
                if market_state.trend_strength >= 25:
                    confidence += 5

                sl = min(ema_55.iloc[-1] * 0.998, current * 0.975)
                tp = current * 1.05

                return {
                    "signal_type": "PULLBACK_PRECISION",
                    "entry_price": current,
                    "stop_loss": sl,
                    "take_profit": tp,
                    "confidence": confidence,
                    "reasons": [
                        f"Pullback to EMA21 zone ({dist_from_ema21 * 100:.1f}%)",
                        f"RSI in pullback zone ({rsi:.0f})",
                        "Above EMA55 (trend intact)",
                    ],
                }
            return None
        except Exception as e:
            self.logger.debug(f"Pullback check error: {e}")
            return None

    def _check_breakout_entry(
        self,
        df_4h: pd.DataFrame,
        market_state: MarketStateResult,
        surveillance: SurveillanceReport,
    ) -> Optional[Dict]:
        """
        Breakout Confirmation Engine

        لماذا الآن؟ كسر مقاومة مع تأكيد حجم
        لماذا هذه النقطة؟ فوق المقاومة + volume > 1.5x
        ما يبطل الدخول؟ العودة تحت المقاومة (false breakout)
        """
        try:
            close = df_4h["close"]
            high = df_4h["high"]
            volume = df_4h["volume"]
            current = close.iloc[-1]

            # Find resistance (recent highs)
            resistance = high.tail(20).quantile(0.9)

            # Breakout above resistance
            breakout = current > resistance

            # Volume confirmation (>1.5x average - strict)
            avg_vol = volume.rolling(20).mean().iloc[-1]
            vol_confirmed = volume.iloc[-1] > avg_vol * 1.5

            # Bollinger Band squeeze release
            sma_20 = close.rolling(20).mean()
            std_20 = close.rolling(20).std()
            bb_width = (2 * std_20 / sma_20).iloc[-1]
            prev_bb_width = (
                (2 * std_20 / sma_20).iloc[-5] if len(close) > 5 else bb_width
            )
            squeeze_release = bb_width > prev_bb_width * 1.3

            # Must have both breakout + volume, AND either squeeze release or
            # very strong volume
            strong_vol = volume.iloc[-1] > avg_vol * 2.0

            if breakout and vol_confirmed and (squeeze_release or strong_vol):
                confidence = 58
                if squeeze_release:
                    confidence += 12
                if strong_vol:
                    confidence += 8
                if surveillance.market_phase == MarketPhase.ACCUMULATION:
                    confidence += 10

                sl = resistance * 0.985  # 1.5% below resistance (was 0.5%)
                tp = current + (current - sl) * 2.5  # R:R 1:2.5

                return {
                    "signal_type": "BREAKOUT_CONFIRMATION",
                    "entry_price": current,
                    "stop_loss": sl,
                    "take_profit": tp,
                    "confidence": confidence,
                    "reasons": [
                        f"Breakout above {resistance:.2f}",
                        f"Volume confirmed ({volume.iloc[-1] / avg_vol:.1f}x)",
                        (
                            "BB squeeze release"
                            if squeeze_release
                            else "Normal breakout"
                        ),
                    ],
                }
            return None
        except Exception as e:
            self.logger.debug(f"Breakout check error: {e}")
            return None

    def _check_volatility_expansion(
        self, df_4h: pd.DataFrame, market_state: MarketStateResult
    ) -> Optional[Dict]:
        """
        Volatility Expansion Engine

        لماذا الآن؟ التقلب كان منكمشاً وبدأ يتوسع صعوداً
        ما يبطل الدخول؟ التوسع هابط أو حجم ضعيف
        """
        try:
            close = df_4h["close"]
            current = close.iloc[-1]

            # BB width history
            sma_20 = close.rolling(20).mean()
            std_20 = close.rolling(20).std()
            bb_width = 2 * std_20 / sma_20

            # Was compressed, now expanding
            min_width = bb_width.tail(10).min()
            current_width = bb_width.iloc[-1]
            expanding = current_width > min_width * 1.8  # Stronger expansion required

            # Expansion is bullish (price above SMA AND rising)
            bullish_expansion = current > sma_20.iloc[-1]
            # Price rising over last 3 bars
            price_rising = close.iloc[-1] > close.iloc[-3]

            # Volume supporting (must be above average)
            vol = df_4h["volume"]
            vol_ratio = vol.iloc[-1] / vol.rolling(20).mean().iloc[-1]

            # Momentum confirmation (RSI rising)
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss_s = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss_s
            rsi = (100 - (100 / (1 + rs))).iloc[-1]
            rsi_ok = 45 < rsi < 72  # Not overbought, but positive

            if (
                expanding
                and bullish_expansion
                and price_rising
                and vol_ratio > 1.1
                and rsi_ok
            ):
                confidence = 50 + min(20, (current_width / min_width - 1) * 25)
                if vol_ratio > 1.5:
                    confidence += 8

                sl = sma_20.iloc[-1] * 0.975  # 2.5% below SMA (was 1%)
                tp = current * 1.055

                return {
                    "signal_type": "VOLATILITY_EXPANSION",
                    "entry_price": current,
                    "stop_loss": sl,
                    "take_profit": tp,
                    "confidence": confidence,
                    "reasons": [
                        f"Volatility expanding ({current_width / min_width:.1f}x)",
                        "Bullish direction",
                        f"Volume: {vol_ratio:.1f}x",
                    ],
                }
            return None
        except Exception as e:
            self.logger.debug(f"Volatility expansion check error: {e}")
            return None

    def _check_reversal_entry(
        self,
        df_4h: pd.DataFrame,
        df_1h: Optional[pd.DataFrame],
        market_state: MarketStateResult,
    ) -> Optional[Dict]:
        """
        Reversal Engine (High Confidence Only)

        لماذا الآن؟ قاع مؤكد + تباعد RSI + حجم شرائي
        ما يبطل الدخول؟ كسر القاع الأخير
        """
        try:
            close = df_4h["close"]
            current = close.iloc[-1]

            # Must be near bottom
            if market_state.state != MarketState.NEAR_BOTTOM:
                return None

            # RSI oversold with divergence
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            rsi_oversold = rsi.iloc[-1] < 35
            # Bullish divergence: price lower low but RSI higher low
            if len(rsi) > 10:
                price_lower = close.iloc[-1] < close.iloc[-10]
                rsi_higher = rsi.iloc[-1] > rsi.iloc[-10]
                divergence = price_lower and rsi_higher
            else:
                divergence = False

            # Volume spike (buying interest)
            vol = df_4h["volume"]
            vol_ratio = vol.iloc[-1] / vol.rolling(20).mean().iloc[-1]
            vol_spike = vol_ratio > 1.5

            # Bullish candle (hammer or engulfing)
            bullish_candle = close.iloc[-1] > df_4h["open"].iloc[-1]
            body = abs(close.iloc[-1] - df_4h["open"].iloc[-1])
            lower_wick = (
                min(close.iloc[-1], df_4h["open"].iloc[-1]) - df_4h["low"].iloc[-1]
            )
            hammer = lower_wick > body * 2  # Long lower wick

            confirmations = sum(
                [rsi_oversold, divergence, vol_spike, bullish_candle, hammer]
            )

            if confirmations >= 3:
                confidence = min(85, 50 + confirmations * 10)

                recent_low = df_4h["low"].tail(10).min()
                sl = recent_low * 0.995
                tp = current * 1.06  # Higher TP for reversals

                reasons = []
                if rsi_oversold:
                    reasons.append(f"RSI oversold ({rsi.iloc[-1]:.0f})")
                if divergence:
                    reasons.append("Bullish divergence")
                if vol_spike:
                    reasons.append(f"Volume spike ({vol_ratio:.1f}x)")
                if hammer:
                    reasons.append("Hammer pattern")

                return {
                    "signal_type": "REVERSAL_HIGH_CONF",
                    "entry_price": current,
                    "stop_loss": sl,
                    "take_profit": tp,
                    "confidence": confidence,
                    "reasons": reasons,
                }
            return None
        except Exception as e:
            self.logger.debug(f"Reversal check error: {e}")
            return None

    # ==========================================
    # أدوات مساعدة
    # ==========================================

    def _adjust_confidence(
        self,
        base_confidence: float,
        market_state: MarketStateResult,
        surveillance: SurveillanceReport,
    ) -> float:
        """تعديل الثقة بناءً على السياق"""
        adjusted = base_confidence

        # Market quality bonus/penalty (conservative - avoid overconfidence)
        quality_adj = {
            MarketQuality.EXCELLENT: 3,
            MarketQuality.GOOD: 5,
            MarketQuality.FAIR: -5,
            MarketQuality.POOR: -20,
            MarketQuality.DANGEROUS: -35,
        }
        adjusted += quality_adj.get(surveillance.market_quality, 0)

        # Phase bonus (stronger penalties for bad phases)
        phase_adj = {
            MarketPhase.ACCUMULATION: 8,
            MarketPhase.MARKUP: 10,
            MarketPhase.DISTRIBUTION: -15,
            MarketPhase.MARKDOWN: -25,
            MarketPhase.TRANSITION: -8,
        }
        adjusted += phase_adj.get(surveillance.market_phase, 0)

        # Risk penalty (stronger)
        if surveillance.risk_score > 40:
            adjusted -= (surveillance.risk_score - 40) * 0.5

        # Behavior signals
        if BehaviorSignal.MOMENTUM_DIVERGENCE in surveillance.behavior_signals:
            adjusted -= 10
        if BehaviorSignal.OPPORTUNITY_APPROACHING in surveillance.behavior_signals:
            adjusted += 5

        return max(0, min(100, adjusted))

    def _calculate_position_size(
        self,
        confidence: float,
        risk_score: float,
        market_state: MarketStateResult,
    ) -> float:
        """حساب حجم المركز بناءً على الثقة والمخاطرة"""
        # Base: 10% of portfolio
        base = 0.10

        # Confidence multiplier (0.7 - 1.3)
        if confidence >= 80:
            conf_mult = 1.3
        elif confidence >= 70:
            conf_mult = 1.1
        elif confidence >= 60:
            conf_mult = 0.9
        else:
            conf_mult = 0.7

        # Risk reduction
        risk_mult = max(0.5, 1 - risk_score / 200)

        size = base * conf_mult * risk_mult

        # Max 15% per position
        return min(0.15, max(0.05, size))

    def _define_invalidation(
        self,
        strategy: EntryStrategy,
        entry_price: float,
        stop_loss: float,
        market_state: MarketStateResult,
    ) -> str:
        """تحديد نقطة الإبطال"""
        sl_pct = abs(entry_price - stop_loss) / entry_price * 100

        invalidation_map = {
            EntryStrategy.TREND_CONTINUATION: f"Price closes below EMA21 or SL at ${stop_loss:.2f} (-{sl_pct:.1f}%)",
            EntryStrategy.PULLBACK_PRECISION: f"Price breaks below EMA55 or SL at ${stop_loss:.2f} (-{sl_pct:.1f}%)",
            EntryStrategy.BREAKOUT_CONFIRMATION: f"Price falls back below breakout level or SL at ${stop_loss:.2f} (-{sl_pct:.1f}%)",
            EntryStrategy.VOLATILITY_EXPANSION: f"Expansion reverses or SL at ${stop_loss:.2f} (-{sl_pct:.1f}%)",
            EntryStrategy.REVERSAL_HIGH_CONF: f"New lower low formed or SL at ${stop_loss:.2f} (-{sl_pct:.1f}%)",
        }
        return invalidation_map.get(
            strategy, f"SL at ${stop_loss:.2f} (-{sl_pct:.1f}%)"
        )

    def _stay_out(self, symbol: str, reason: str, **kwargs) -> CognitiveDecision:
        """قرار البقاء خارج السوق"""
        return CognitiveDecision(
            action=CognitiveAction.STAY_OUT,
            symbol=symbol,
            timestamp=datetime.now(),
            market_state=kwargs.get("market_state", "unknown"),
            market_quality=kwargs.get("market_quality", "unknown"),
            market_phase=kwargs.get("market_phase", "unknown"),
            entry_strategy=EntryStrategy.NONE,
            confidence=0,
            opportunity_score=kwargs.get("opportunity_score", 0),
            risk_score=kwargs.get("risk_score", 0),
            reasoning=reason,
            warnings=[reason],
        )

    # ==========================================
    # ADAPT: التكيّف والتعلّم
    # ==========================================

    def record_trade_result(
        self,
        symbol: str,
        strategy: str,
        pnl_pct: float,
        hold_hours: float,
        market_state: str,
        exit_reason: str,
    ):
        """تسجيل نتيجة صفقة للتعلّم والتكيّف"""
        result = {
            "symbol": symbol,
            "strategy": strategy,
            "pnl_pct": pnl_pct,
            "hold_hours": hold_hours,
            "market_state": market_state,
            "exit_reason": exit_reason,
            "timestamp": datetime.now().isoformat(),
            "is_win": pnl_pct > 0,
        }
        self._trade_history.append(result)

        # Keep last 100 trades
        if len(self._trade_history) > 100:
            self._trade_history = self._trade_history[-100:]

        self.logger.info(
            f"📝 [{symbol}] Trade recorded: {strategy} | "
            f"PnL: {pnl_pct * 100:+.2f}% | "
            f"{'✅ WIN' if pnl_pct > 0 else '❌ LOSS'}"
        )

    def get_performance_stats(self) -> Dict:
        """إحصائيات الأداء"""
        if not self._trade_history:
            return {"total_trades": 0, "win_rate": 0, "avg_pnl": 0}

        wins = sum(1 for t in self._trade_history if t["is_win"])
        total = len(self._trade_history)
        avg_pnl = sum(t["pnl_pct"] for t in self._trade_history) / total

        return {
            "total_trades": total,
            "win_rate": (wins / total * 100) if total > 0 else 0,
            "avg_pnl": avg_pnl * 100,
            "wins": wins,
            "losses": total - wins,
        }


# Singleton
_orchestrator = None


def get_cognitive_orchestrator(
    config: Optional[Dict] = None,
) -> CognitiveOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = CognitiveOrchestrator(config)
    return _orchestrator
