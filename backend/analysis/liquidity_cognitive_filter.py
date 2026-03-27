#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Liquidity-Cognitive Filter
================================

طبقة وسيطة بين إشارات الاستراتيجية (Scalping V7) والتنفيذ الفعلي.

الهدف:
- تأكيد إشارات الدخول بناءً على منطق السيولة وSmart Money.
- رفض الإشارات ذات احتمالية أن تكون فخ سيولة / اختراق كاذب.
- تعديل حجم الصفقة (size_factor) عند الحاجة.

المدخلات:
- symbol: رمز العملة.
- df_1h: بيانات 1h مع مؤشرات V7.
- signal: إشارة من الاستراتيجية (side, score, confidence, ...).

المخرجات:
- dict يحتوي على:
  - decision: 'ACCEPT' / 'REJECT' / 'DOWNGRADE'
  - size_factor: معامل تعديل حجم الصفقة (0.0–1.0)
  - signal_score, liquidity_score, total_score
  - reasons: قائمة أسباب للقرار (للتعلّم والتحليل)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from backend.analysis.liquidity_analyzer import LiquidityAnalyzer
from backend.analysis.market_regime_detector import MarketRegimeDetector

try:
    from backend.analysis.smart_money_orchestrator import (
        SmartMoneyOrchestrator,
        SmartMoneySignal,
    )

    SMART_MONEY_AVAILABLE = True
except Exception:  # pragma: no cover - اختياري
    SmartMoneyOrchestrator = None  # type: ignore
    SmartMoneySignal = None  # type: ignore
    SMART_MONEY_AVAILABLE = False

logger = logging.getLogger(__name__)


class LiquidityCognitiveFilter:
    """فلتر معرفي/سيولة لإشارات الدخول.

    - يعمل فوق إشارات V7.
    - يستخدم LiquidityAnalyzer + SmartMoneyOrchestrator + MarketRegimeDetector.
    - يدعم أوضاع: conservative / balanced.
    """

    def __init__(self, data_provider: Any, mode: str = "balanced") -> None:
        self.data_provider = data_provider
        self.mode = (
            mode if mode in {"conservative", "balanced"} else "balanced"
        )
        self.logger = logging.getLogger(f"{__name__}.LiquidityCognitiveFilter")

        self.liquidity_analyzer = LiquidityAnalyzer()
        self.regime_detector = MarketRegimeDetector()
        self.smart_money: Optional[SmartMoneyOrchestrator] = None
        if SMART_MONEY_AVAILABLE:
            try:
                self.smart_money = SmartMoneyOrchestrator()
                self.logger.info(
                    "💧 Liquidity-Cognitive SmartMoney layer enabled"
                )
            except Exception as e:  # pragma: no cover - حماية تشغيلية
                self.logger.warning(
                    f"⚠️ Failed to init SmartMoneyOrchestrator: {e}"
                )
                self.smart_money = None

    # ------------------------------------------------------------------
    # واجهة رئيسية للدخول
    # ------------------------------------------------------------------
    def evaluate_entry(
        self, symbol: str, df_1h: pd.DataFrame, signal: Dict[str, Any]
    ) -> Dict[str, Any]:
        """تقييم إشارة دخول واحدة.

        Returns dict with:
            decision: 'ACCEPT' / 'REJECT' / 'DOWNGRADE'
            size_factor: float (0.0–1.0)
            signal_score, liquidity_score, total_score, reasons
        """
        result: Dict[str, Any] = {
            "decision": "ACCEPT",
            "size_factor": 1.0,
            "signal_score": 0.0,
            "liquidity_score": 0.0,
            "total_score": 0.0,
            "reasons": [],
        }

        try:
            side = str(signal.get("side", "LONG")).upper()

            # 1) قوة الإشارة نفسها (من V7)
            raw_score = float(signal.get("score", 0) or 0)
            confidence = float(signal.get("confidence", 0) or 0)
            # مزيج بسيط: الثقة أساس + مكافأة للـ score
            signal_score = max(
                0.0, min(100.0, confidence * 0.6 + raw_score * 4.0)
            )

            # 2) تحليل السيولة والسوق / Smart Money
            liquidity_score, reasons = self._compute_liquidity_score(
                symbol, df_1h, side
            )

            # 3) دمج النتيجتين
            total_score = 0.6 * signal_score + 0.4 * liquidity_score

            result["signal_score"] = signal_score
            result["liquidity_score"] = liquidity_score
            result["total_score"] = total_score
            result["reasons"] = reasons

            # 4) منطق العتبات حسب الوضع (متوازن/محافظ) + عدوانية عند الإشارات
            # القوية
            base_thresholds = {
                "conservative": {"liq_min": 65.0, "total_min": 75.0},
                "balanced": {"liq_min": 55.0, "total_min": 65.0},
            }
            thr = base_thresholds[self.mode]
            liq_min = thr["liq_min"]
            total_min = thr["total_min"]

            # Aggressive override: إذا الإشارة نفسها قوية جداً نخفف الشروط
            # قليلاً
            if signal_score >= 85.0:
                liq_min -= 10.0
                total_min -= 5.0

            # حماية: عدم التداول في حال سيولة ضعيفة جداً
            if liquidity_score <= 30.0:
                result["decision"] = "REJECT"
                result["size_factor"] = 0.0
                result["reasons"].append("Liquidity very weak")
                return result

            # قرار نهائي
            if liquidity_score < liq_min or total_score < total_min:
                # إشارة غير مقنعة من ناحية السيولة/السياق
                result["decision"] = "REJECT"
                result["size_factor"] = 0.0
            elif (
                liquidity_score < liq_min + 5.0
                or total_score < total_min + 5.0
            ):
                # حالة وسط: دخول مسموح لكن بحجم أقل
                result["decision"] = "DOWNGRADE"
                result["size_factor"] = 0.5
            else:
                result["decision"] = "ACCEPT"
                result["size_factor"] = 1.0

            self.logger.info(f"💧 [{symbol}] LiquidityFilter {
                result['decision']} " f"sig={
                signal_score:.1f} liq={
                liquidity_score:.1f} total={
                total_score:.1f}")
            return result

        except (
            Exception
        ) as e:  # pragma: no cover - في حال الخطأ نسمح بالإشارة ولا نكسر النظام
            self.logger.warning(f"⚠️ Liquidity filter error for {symbol}: {e}")
            return result

    # ------------------------------------------------------------------
    # حساب درجة السيولة + Smart Money + حالة السوق
    # ------------------------------------------------------------------
    def _compute_liquidity_score(
        self, symbol: str, df_1h: pd.DataFrame, side: str
    ) -> Tuple[float, List[str]]:
        reasons: List[str] = []
        score_components: List[float] = []

        # 1) سيولة عامة من LiquidityAnalyzer
        try:
            liq = self.liquidity_analyzer.analyze(symbol, df_1h)
            base = liq.get("liquidity_score", "POOR")
            if base == "EXCELLENT":
                liq_score = 80.0
            elif base == "GOOD":
                liq_score = 65.0
            elif base == "FAIR":
                liq_score = 50.0
            else:
                liq_score = 20.0
            score_components.append(liq_score)
            reasons.append(f"Base liquidity={base}")
        except Exception as e:  # pragma: no cover
            logger.debug(f"LiquidityAnalyzer failed for {symbol}: {e}")

        # 2) حالة السوق العامة من MarketRegimeDetector (على 1h)
        try:
            regime_info = self.regime_detector.detect_regime(df_1h)
            regime = regime_info.get("regime", "UNKNOWN")
            reasons.append(f"Regime={regime}")

            if regime == "CHOPPY_VOLATILE":
                score_components.append(30.0)  # نفضل تجنب هذه الحالة
            elif regime in ("TRENDING_VOLATILE", "TRENDING_CALM"):
                score_components.append(70.0)
            elif regime == "RANGING_TIGHT":
                score_components.append(55.0)
            else:
                score_components.append(50.0)
        except Exception as e:  # pragma: no cover
            logger.debug(f"MarketRegimeDetector failed for {symbol}: {e}")

        # 3) Smart Money / Liquidity Sweeps إذا متاح
        if self.smart_money is not None:
            try:
                df_15m = self.data_provider.get_historical_data(
                    symbol, "15m", limit=200
                )
                df_5m = self.data_provider.get_historical_data(
                    symbol, "5m", limit=200
                )
                if (
                    df_15m is not None
                    and len(df_15m) >= 60
                    and df_5m is not None
                    and len(df_5m) >= 60
                ):
                    sm_result = self.smart_money.analyze_smart_money_activity(
                        symbol, df_15m, df_5m
                    )
                    confluence = float(
                        sm_result.get("confluence_score", 0.0) or 0.0
                    )
                    score_components.append(confluence)
                    reasons.append(f"SmartMoney confluence={confluence:.1f}")

                    smart_sig: Optional[SmartMoneySignal] = sm_result.get(
                        "smart_money_signal"
                    )  # type: ignore
                    if smart_sig is not None:
                        # توافق الاتجاه بين إشارة V7 و Smart Money
                        if (
                            side == "LONG" and smart_sig.signal_type == "BUY"
                        ) or (
                            side == "SHORT" and smart_sig.signal_type == "SELL"
                        ):
                            reasons.append(f"SmartMoney aligned ({
                                smart_sig.signal_type})")
                            score_components.append(15.0)
                        elif smart_sig.signal_type in {"BUY", "SELL"}:
                            # تعارض مباشر
                            reasons.append(f"SmartMoney conflict ({
                                smart_sig.signal_type})")
                            score_components.append(-20.0)
            except Exception as e:  # pragma: no cover
                logger.debug(f"SmartMoney analysis failed for {symbol}: {e}")

        if not score_components:
            # لا بيانات كافية → نعود لنقطة متوسطة
            return 50.0, reasons

        # متوسط مبسط مع حدود 0–100
        raw_score = sum(score_components) / len(score_components)
        return max(0.0, min(100.0, raw_score)), reasons

    # ------------------------------------------------------------------
    # Early Exit Helper — لا يمنع الخروج الحالي، فقط يضيف خروجاً مبكراً عند الحاجة
    # ------------------------------------------------------------------
    def evaluate_early_exit(
        self, symbol: str, df_1h: pd.DataFrame, position: Dict[str, Any]
    ) -> Dict[str, Any]:
        """محاولة اقتراح خروج مبكر بناءً على السيولة والسياق.

        لا يُستخدم لإلغاء أي خروج قائم من الاستراتيجية/أنظمة الخروج؛
        يمكن أن يقترح خروجاً إضافياً عندما:
        - PnL سلبي أو قريب من الصفر، ودرجة السيولة/السياق سيئة.
        - أو الربح صغير لكن السياق السيولي ضد المركز بشكل واضح.

        Returns dict:
            should_exit: bool
            reason: str
            exit_price: float
            details: dict (اختياري للمراقبة)
        """
        result: Dict[str, Any] = {
            "should_exit": False,
            "reason": "HOLD",
            "exit_price": None,
            "details": {},
        }

        try:
            if df_1h is None or len(df_1h) < 30:
                return result

            entry_price = float(position.get("entry_price", 0.0) or 0.0)
            if entry_price <= 0:
                return result

            side = str(position.get("position_type", "long")).upper()
            current_price = float(df_1h["close"].iloc[-1])

            if side == "SHORT":
                pnl_frac = (entry_price - current_price) / entry_price
            else:
                pnl_frac = (current_price - entry_price) / entry_price

            # إعادة استخدام منطق السيولة نفسه
            liquidity_score, reasons = self._compute_liquidity_score(
                symbol, df_1h, side
            )

            result["details"] = {
                "pnl_pct": pnl_frac * 100.0,
                "liquidity_score": liquidity_score,
                "reasons": reasons,
            }

            # شروط الخروج المبكر (محافظة مع أولوية للسرعة عند السوء الواضح)
            trigger = False
            exit_reason = "LIQ_EARLY_EXIT"

            # 1) خسارة حالية أو حول التعادل + سيولة/سياق ضعيف
            if pnl_frac <= 0 and liquidity_score < 55.0:
                trigger = True
                exit_reason = "LIQ_EARLY_EXIT_NEGATIVE_OR_FLAT"

            # 2) ربح صغير (< 0.5%) لكن سيولة سيئة جداً → لا نستغل الحركة حتى
            # تتحول لفخ
            elif 0 < pnl_frac < 0.005 and liquidity_score < 45.0:
                trigger = True
                exit_reason = "LIQ_EARLY_EXIT_SMALL_PROFIT_WEAK_CONTEXT"

            if not trigger:
                return result

            result["should_exit"] = True
            result["reason"] = exit_reason
            result["exit_price"] = current_price
            return result

        except Exception as e:  # pragma: no cover - حماية تشغيلية
            self.logger.warning(
                f"⚠️ Liquidity early-exit error for {symbol}: {e}"
            )
            return result

    # ------------------------------------------------------------------
    # Exit Confirmation Filter — تأكيد/رفض خروجات الاستراتيجية (غير الطارئة)
    # ------------------------------------------------------------------
    def evaluate_exit_confirmation(
        self,
        symbol: str,
        df_exec: pd.DataFrame,
        position: Dict[str, Any],
        exit_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """تجميع تأكيدات سريعة للخروج مقابل الاستمرار.

        لا يُستخدم مع خروجات الطوارئ (SL/EMERGENCY) — هذه تُنفّذ مباشرة.

        يعتمد على:
            - PnL الحالي وحجمه.
            - نمط الشموع على إطار التنفيذ (df_exec).
            - اتجاه الإطار الأعلى (4h) مقابل اتجاه الصفقة.
            - درجة السيولة / Smart Money (نفس منطق _compute_liquidity_score).

        Returns dict:
            decision: 'CONFIRM_EXIT' or 'HOLD'
            exit_score: float
            hold_score: float
            reasons: List[str]
        """
        result: Dict[str, Any] = {
            "decision": "CONFIRM_EXIT",
            "exit_score": 0.0,
            "hold_score": 0.0,
            "reasons": [],
        }

        try:
            if df_exec is None or len(df_exec) < 30:
                return result

            entry_price = float(position.get("entry_price", 0.0) or 0.0)
            if entry_price <= 0:
                return result

            side = str(position.get("position_type", "long")).upper()
            current_price = float(df_exec["close"].iloc[-1])

            # 1) PnL الحالي
            if side == "SHORT":
                pnl_frac = (entry_price - current_price) / entry_price
            else:
                pnl_frac = (current_price - entry_price) / entry_price

            exit_score = 0.0
            hold_score = 0.0
            reasons: List[str] = []

            # PnL-based contribution
            if pnl_frac <= -0.01:  # خسارة أكبر من 1%
                exit_score += 25.0
                reasons.append(f"PnL loss {pnl_frac * 100:.2f}% → favors EXIT")
            elif -0.01 < pnl_frac < 0.003:
                exit_score += 10.0
                reasons.append(
                    f"PnL flat/weak {pnl_frac * 100:.2f}% → slight EXIT bias"
                )
            elif pnl_frac >= 0.02:  # ربح أكبر من 2%
                hold_score += 20.0
                reasons.append(f"PnL profit {
                    pnl_frac *
                    100:.2f}% → favors HOLD/let run")

            # 2) نمط الشموع على إطار التنفيذ
            try:
                last = df_exec.iloc[-1]
                prev = df_exec.iloc[-2]
                o, h, l, c = (
                    last["open"],
                    last["high"],
                    last["low"],
                    last["close"],
                )
                body = abs(c - o)
                range_ = max(h - l, 1e-8)
                body_ratio = body / range_

                # شمعة انعكاسية قوية ضد الصفقة
                if (
                    side == "LONG"
                    and c < o
                    and body_ratio > 0.6
                    and c < prev["close"]
                ):
                    exit_score += 20.0
                    reasons.append("Strong bearish candle against LONG → EXIT")
                elif (
                    side == "SHORT"
                    and c > o
                    and body_ratio > 0.6
                    and c > prev["close"]
                ):
                    exit_score += 20.0
                    reasons.append(
                        "Strong bullish candle against SHORT → EXIT"
                    )

                # شمعة استمرارية مع الصفقة
                if (
                    side == "LONG"
                    and c > o
                    and body_ratio > 0.6
                    and c > prev["close"]
                ):
                    hold_score += 15.0
                    reasons.append("Strong bullish continuation candle → HOLD")
                elif (
                    side == "SHORT"
                    and c < o
                    and body_ratio > 0.6
                    and c < prev["close"]
                ):
                    hold_score += 15.0
                    reasons.append("Strong bearish continuation candle → HOLD")
            except Exception:
                pass

            # 3) سياق الإطار الأعلى (4h)
            try:
                df_4h = self.data_provider.get_historical_data(
                    symbol, "4h", limit=80
                )
                if df_4h is not None and len(df_4h) >= 20:
                    close_now = float(df_4h["close"].iloc[-1])
                    close_past = float(df_4h["close"].iloc[-20])
                    delta_htf = (close_now - close_past) / close_past

                    if side == "LONG":
                        if delta_htf < -0.02:
                            exit_score += 20.0
                            reasons.append(
                                "4h trend turned down vs LONG → EXIT"
                            )
                        elif delta_htf > 0.03:
                            hold_score += 20.0
                            reasons.append(
                                "4h strong uptrend with LONG → HOLD"
                            )
                    else:  # SHORT
                        if delta_htf > 0.02:
                            exit_score += 20.0
                            reasons.append(
                                "4h trend turned up vs SHORT → EXIT"
                            )
                        elif delta_htf < -0.03:
                            hold_score += 20.0
                            reasons.append(
                                "4h strong downtrend with SHORT → HOLD"
                            )
            except Exception:
                pass

            # 4) سيولة / Smart Money (نفس منطق الدخول)
            try:
                liq_score, liq_reasons = self._compute_liquidity_score(
                    symbol, df_exec, side
                )
                reasons.extend([f"LIQ: {r}" for r in liq_reasons])

                if liq_score < 45.0:
                    exit_score += 20.0
                    reasons.append(f"Weak liquidity score {
                        liq_score:.1f} → favors EXIT")
                elif liq_score > 65.0:
                    hold_score += 20.0
                    reasons.append(f"Strong liquidity score {
                        liq_score:.1f} → favors HOLD")
            except Exception:
                pass

            result["exit_score"] = exit_score
            result["hold_score"] = hold_score
            result["reasons"] = reasons

            # قرار نهائي بسيط ومحافظ
            # إذا لم نكن واثقين بقوة من HOLD، نميل لتأكيد خروج الاستراتيجية.
            if hold_score >= 75.0 and hold_score > exit_score + 10.0:
                result["decision"] = "HOLD"
            else:
                result["decision"] = "CONFIRM_EXIT"

            self.logger.info(
                f"💧 [{symbol}] ExitConfirmation decision={result['decision']} "
                f"exit={exit_score:.1f} hold={hold_score:.1f}"
            )
            return result

        except (
            Exception
        ) as e:  # pragma: no cover - في حال الخطأ نؤكد الخروج ولا نعرقل
            self.logger.warning(f"⚠️ ExitConfirmation error for {symbol}: {e}")
            return result
