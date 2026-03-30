"""
Scanner Mixin — البحث عن فرص دخول جديدة وفحص حالة السوق
==========================================================
Extracted from group_b_system.py (God Object split)

Methods:
    _scan_for_entries, _check_market_regime, _add_indicators
"""

from typing import Dict, List, Optional
import pandas as pd

# Cognitive imports (optional)
try:
    from backend.cognitive.cognitive_orchestrator import CognitiveAction

    COGNITIVE_IMPORT_OK = True
except ImportError:
    COGNITIVE_IMPORT_OK = False

# Smart Money imports (optional)
try:
    from backend.analysis.smart_money_orchestrator import (
        SmartMoneyOrchestrator,
    )

    SMART_MONEY_AVAILABLE = True
except ImportError:
    SMART_MONEY_AVAILABLE = False


class ScannerMixin:
    """Mixin for market scanning and entry signal detection"""

    def _persist_detected_signals(self, signals: List[Dict]) -> None:
        """حفظ الإشارات المكتشفة في trading_signals حتى لو لم تتحول مباشرة إلى صفقات."""
        if not signals:
            return

        try:
            with self.db.get_write_connection() as conn:
                for signal in signals:
                    conn.execute(
                        """
                        INSERT INTO trading_signals
                        (symbol, signal_type, strategy, timeframe, price, confidence)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            signal.get("symbol"),
                            signal.get("signal_type"),
                            signal.get("strategy"),
                            signal.get("timeframe"),
                            signal.get("price"),
                            signal.get("confidence", 0.0),
                        ),
                    )
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to persist detected signals: {e}")

    def _scan_for_entries(self) -> List[Dict]:
        """
        البحث عن فرص دخول جديدة
        ===== Strategy Interface (BaseStrategy) =====
        النظام يستدعي self.strategy فقط — لا يعرف أي استراتيجية يشغّل

        ✅ Phase 0+1: Risk Protection مفعّلة

        🎯 PRODUCTION VALIDATION MODE:
        - يفحش: Daily Loss, Max Drawdown, Cooldown ( حماية أساسية)
        - يتخطى: WR Gate, Liquidity Filter (للسماح بتوليد الإشارات)
        - يحتفظ: Max Positions, Directional Stress
        """
        entries = []
        symbols_to_scan = self.config["symbols_pool"]
        strategy_name = self.strategy.name if self.strategy else "none"

        # 🎯 PRODUCTION VALIDATION MODE: محاذاة نتائج الاختبار الخلفي
        validation_mode = self.config.get("production_validation_mode", False)
        backtest_mode = self.config.get("backtest_mode", False)

        if backtest_mode:
            self.logger.info(
                f"\n🎯 [{strategy_name}] BACKTEST MODE - Scanning {len(symbols_to_scan)} symbols"
            )
        elif validation_mode:
            self.logger.info(
                f"\n🔬 [{strategy_name}] PRODUCTION VALIDATION - Scanning {len(symbols_to_scan)} symbols"
            )
        else:
            self.logger.info(
                f"\n🔍 [{strategy_name}] Scanning {len(symbols_to_scan)} symbols for entries..."
            )

        # ===== Phase 0: فحص بوابات الحماية الأساسية (دائماً مفعلة) =====
        portfolio = self._load_user_portfolio()
        balance = portfolio.get("balance", 0)
        risk_balance = portfolio.get("total_value", balance)
        open_positions = self._get_open_positions()

        # 🔒 حماية أساسية: حد أقصى للصفقات المفتوحة
        max_open = self.config.get("max_positions", 5)
        if len(open_positions) >= max_open:
            self.logger.info(
                f"   🛡️ Max positions reached ({len(open_positions)}/{max_open})"
            )
            return entries

        # 🔒 حماية أساسية: Cooldown بعد خسائر متتالية
        if not backtest_mode:
            can_trade, gate_reason = self._check_risk_gates(
                open_positions, risk_balance
            )
            if not can_trade:
                self.logger.info(f"   🛡️ Risk Gate BLOCKED: {gate_reason}")
                return entries

        # 🌡️ فحص حالة السوق - تحذير فقط في validation_mode
        if not backtest_mode and not validation_mode:
            market_ok = self._check_market_regime()
            if not market_ok:
                self.logger.info(
                    "   ⚠️ Market regime unfavorable - skipping new entries"
                )
                return entries
        elif validation_mode:
            # في validation_mode: نفحص السوق لكن لا نمنع الإشارات
            self._check_market_regime()  # تسجيل الحالة فقط

        # 📈 فلتر ساعات التداول (التعلم التكيّفي)
        if self.optimizer and not backtest_mode:
            try:
                hour_ok, hour_reason = self.optimizer.is_good_trading_hour(
                    self.user_id, bool(self.is_demo_trading)
                )
                if not hour_ok and not validation_mode:
                    self.logger.warning(
                        f"   📈 Adaptive hour warning (non-blocking): {hour_reason}"
                    )
            except Exception as e:
                self.logger.warning(f"⚠️ Hour filter error: {e}")

        # 📈 ترتيب العملات بالأداء (التعلم التكيّفي)
        if self.optimizer:
            try:
                symbols_to_scan = self.optimizer.get_preferred_symbols(
                    self.user_id,
                    bool(self.is_demo_trading),
                    symbols_to_scan,
                    top_n=len(symbols_to_scan),
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Symbol ranking error: {e}")

        # ========== Strategy Entry Detection (via BaseStrategy interface) ====
        # ✅ النظام يستدعي self.strategy فقط — لا يعرف أي استراتيجية يشغّل
        if self.strategy:
            # NOTE: نحفظ أيضاً DataFrame المعالج لكل رمز لاستخدامه لاحقاً في
            # فلتر السيولة
            # [(symbol, signal, predicted_wr, score, df_prepared)]
            qualified_signals = []
            signals_to_persist = []
            timeframe = self.config.get("execution_timeframe", "1h")

            for symbol in symbols_to_scan:
                try:
                    # فحص القائمة السوداء
                    if self.dynamic_blacklist.is_blacklisted(symbol):
                        continue

                    # جلب البيانات بالإطار الزمني المحدد من الاستراتيجية
                    df = self.data_provider.get_historical_data(
                        symbol, timeframe, limit=200
                    )
                    if df is None or len(df) < 70:
                        continue

                    # تحضير البيانات (إضافة المؤشرات — عبر الواجهة الموحدة)
                    df = self.strategy.prepare_data(df)

                    # تحديد اتجاه السوق (عبر الواجهة الموحدة)
                    trend = self.strategy.get_market_trend(df)

                    # كشف إشارة الدخول (عبر الواجهة الموحدة)
                    signal = self.strategy.detect_entry(df, {"trend": trend})
                    if not signal:
                        self.logger.info(f"   ⏭️ [{symbol}] trend={trend} → no signal")

                    # ===== Smart Money Enhancement =====
                    # تحسين الإشارة بتحليل Smart Money إذا كان متاحاً
                    if signal and SMART_MONEY_AVAILABLE:
                        try:
                            smart_money_enhancement = (
                                self._analyze_smart_money_confluence(symbol, df, signal)
                            )
                            if smart_money_enhancement:
                                # تحسين نقاط الإشارة بناءً على تحليل Smart
                                # Money
                                signal = self._enhance_signal_with_smart_money(
                                    signal, smart_money_enhancement
                                )
                        except Exception as e:
                            self.logger.warning(
                                f"⚠️ Smart Money analysis error for {symbol}: {e}"
                            )

                    if signal:
                        signals_to_persist.append(
                            {
                                "symbol": symbol,
                                "strategy": signal.get("strategy", strategy_name),
                                "timeframe": timeframe,
                                "signal_type": signal.get(
                                    "signal_type",
                                    signal.get("side", "UNKNOWN"),
                                ),
                                "price": float(
                                    signal.get("entry_price") or df["close"].iloc[-1]
                                ),
                                "confidence": float(
                                    signal.get("confidence", signal.get("score", 0.0))
                                    or 0.0
                                ),
                            }
                        )

                        # ===== Phase 1: Capital Stress — فحص تكدس الاتجاه ====
                        # 🔒 حماية أساسية في الوضع العادي فقط
                        if not backtest_mode and not validation_mode:
                            dir_ok, dir_reason = self._check_directional_stress(
                                open_positions, signal["side"]
                            )
                            if not dir_ok:
                                self.logger.info(
                                    f"   🛡️ [{symbol}] Directional Stress BLOCKED: {dir_reason}"
                                )
                                continue

                        # 📈 استخراج المؤشرات للتعلم (عبر الواجهة الموحدة)
                        entry_indicators = self.strategy.extract_entry_indicators(df)
                        entry_indicators["trend_4h"] = trend
                        entry_indicators["score"] = signal.get("score", 0)
                        signal["_entry_indicators"] = entry_indicators

                        # 📈 تقييم جودة الإشارة (التعلم التكيّفي)
                        # 🎯 validation_mode/backtest_mode: تخطي WR Gate للسماح بالإشارات
                        predicted_wr = 0.5
                        if (
                            not backtest_mode
                            and not validation_mode
                            and self.optimizer
                            and entry_indicators
                        ):
                            try:
                                sig_score = self.optimizer.score_signal(
                                    self.user_id,
                                    bool(self.is_demo_trading),
                                    symbol,
                                    entry_indicators,
                                )
                                predicted_wr = sig_score.get("predicted_wr", 0.5)
                                if not sig_score.get("should_trade", True):
                                    self.logger.info(
                                        f"   📈 [{symbol}] Signal REJECTED: "
                                        f"{sig_score.get('reason', '%s')} "
                                        f"(WR={predicted_wr:.0%})"
                                    )
                                    continue
                            except Exception as e:
                                self.logger.warning(f"⚠️ Signal scoring error: {e}")

                        # ✅ إضافة للمرشحين بدلاً من الدخول فوراً
                        sig_score_val = signal.get("score", 0)
                        # نحتفظ بـ df المعالج لهذا الرمز لاستخدامه في فلتر
                        # السيولة لاحقاً
                        qualified_signals.append(
                            (symbol, signal, predicted_wr, sig_score_val, df)
                        )
                        self.logger.info(
                            f"   🎯 [{symbol}] {signal['side']} QUALIFIED: "
                            f"{signal.get('strategy', strategy_name)} | Score={
                                sig_score_val
                            } | "
                            f"WR={predicted_wr:.0%} | Trend: {trend}"
                        )

                except Exception as e:
                    self.logger.error(f"Error scanning {symbol}: {e}")

            self._persist_detected_signals(signals_to_persist)

            # ✅ اختيار الأفضل من المرشحين
            if qualified_signals:
                # ترتيب: الأولوية لـ predicted_wr ثم score
                qualified_signals.sort(
                    key=lambda x: (x[2], x[3]),  # (predicted_wr, score)
                    reverse=True,
                )

                self.logger.info(
                    f"   📊 {len(qualified_signals)} qualified signals — "
                    f"picking best (max 2):"
                )
                for i, (sym, sig, wr, sc, _df_prepared) in enumerate(qualified_signals):
                    marker = "→ ✅" if i < 2 else "  ⏭️"
                    self.logger.info(
                        f"   {marker} #{i + 1} {sym}: WR={wr:.0%} Score={sc} "
                        f"{sig['side']} {sig.get('strategy', strategy_name)}"
                    )

                # فتح أفضل 1-2 إشارات مع فلتر السيولة/المعرفة (إن وجد)
                for sym, sig, wr, sc, df_prepared in qualified_signals:
                    if len(entries) >= 2:
                        break

                    filtered_signal = sig

                    # 🎯 validation_mode/backtest_mode: تخطي فلتر السيولة للسماح بالإشارات
                    if not backtest_mode and not validation_mode:
                        # فلتر السيولة/المعرفة — يعمل فقط إذا كان موجوداً على
                        # النظام
                        if (
                            hasattr(self, "liquidity_filter")
                            and getattr(self, "liquidity_filter") is not None
                        ):
                            try:
                                lf_result = self.liquidity_filter.evaluate_entry(
                                    sym, df_prepared, sig
                                )
                                decision = lf_result.get("decision", "ACCEPT")
                                size_factor = float(
                                    lf_result.get("size_factor", 1.0) or 1.0
                                )

                                if decision == "REJECT" or size_factor <= 0:
                                    self.logger.info(
                                        f"   💧 [{sym}] Entry REJECTED by LiquidityFilter "
                                        f"(sig={lf_result.get('signal_score', 0):.1f} "
                                        f"liq={lf_result.get('liquidity_score', 0):.1f})"
                                    )
                                    continue
                                elif decision == "DOWNGRADE" and size_factor < 1.0:
                                    # نعمل نسخة من الإشارة ولا نعدل الأصل مباشرة
                                    filtered_signal = dict(sig)
                                    filtered_signal["_size_factor"] = max(
                                        0.0, min(size_factor, 1.0)
                                    )
                                    self.logger.info(
                                        f"   💧 [{sym}] Entry DOWNGRADED by LiquidityFilter "
                                        f"(size_factor={size_factor:.2f})"
                                    )
                                else:
                                    filtered_signal = sig
                            except Exception as e:
                                # أي خطأ في الفلتر لا يجب أن يكسر دورة التداول
                                self.logger.warning(
                                    f"⚠️ LiquidityFilter error for {sym}: {e}"
                                )
                                filtered_signal = sig

                    # 🔒 حماية أساسية: فحص المخاطر قبل الدخول الفعلي (TOCTOU prevention)
                    # 🎯 validation_mode/backtest_mode: تخطي فحص المخاطر الثاني
                    if not backtest_mode and not validation_mode:
                        open_positions_for_entry = self._get_open_positions()
                        portfolio_for_entry = self._load_user_portfolio()
                        risk_balance_for_entry = portfolio_for_entry.get(
                            "total_value", portfolio_for_entry.get("balance", 0)
                        )

                        can_trade_entry, gate_reason_entry = self._check_risk_gates(
                            open_positions_for_entry, risk_balance_for_entry
                        )

                        if not can_trade_entry:
                            self.logger.warning(
                                f"   🛡️ [{sym}] Pre-entry risk gate BLOCKED: {gate_reason_entry}"
                            )
                            continue

                    entry = self._open_position(sym, filtered_signal)
                    if entry:
                        entries.append(entry)
                        open_positions = self._get_open_positions()
            else:
                self.logger.info("   📊 No qualified signals this cycle")

            return entries

        # ========== Fallback: النظام المعرفي (إذا V7 غير متاح) ==========
        exec_tf = self.config.get("execution_timeframe", "4h")
        conf_tf = self.config.get("confirmation_timeframe", "1h")
        self.config.get("min_entry_confidence", 60)

        for symbol in symbols_to_scan:
            try:
                if self.dynamic_blacklist.is_blacklisted(symbol):
                    continue

                df_4h = self.data_provider.get_historical_data(
                    symbol, exec_tf, limit=100
                )
                if df_4h is None or len(df_4h) < 50:
                    continue

                df_1h = self.data_provider.get_historical_data(
                    symbol, conf_tf, limit=50
                )

                if self.cognitive_orchestrator:
                    cognitive_decision = self.cognitive_orchestrator.analyze_entry(
                        symbol=symbol, df_4h=df_4h, df_1h=df_1h
                    )

                    if (
                        COGNITIVE_IMPORT_OK
                        and cognitive_decision.action == CognitiveAction.ENTER
                    ):
                        signal = {
                            "signal_type": cognitive_decision.entry_strategy.value,
                            "confidence": cognitive_decision.confidence,
                            "entry_price": cognitive_decision.entry_price,
                            "stop_loss": cognitive_decision.stop_loss,
                            "take_profit": cognitive_decision.take_profit,
                            "side": "LONG",
                            "reasons": [cognitive_decision.entry_logic],
                        }
                        self._persist_detected_signals(
                            [
                                {
                                    "symbol": symbol,
                                    "strategy": "cognitive_fallback",
                                    "timeframe": exec_tf,
                                    "signal_type": signal.get(
                                        "signal_type", "COGNITIVE"
                                    ),
                                    "price": float(signal.get("entry_price") or 0.0),
                                    "confidence": float(
                                        signal.get("confidence", 0.0) or 0.0
                                    ),
                                }
                            ]
                        )

                        entry = self._open_position(symbol, signal)
                        if entry:
                            entries.append(entry)
                            if len(entries) >= 2:
                                break

            except Exception as e:
                self.logger.error(f"Error scanning {symbol}: {e}")

        return entries

    def _check_market_regime(self) -> bool:
        """
        فحص حالة السوق العامة عبر BTC
        لا ندخل صفقات جديدة إذا كان السوق في حالة هبوط حاد أو تقلب شديد

        يضبط self._market_caution_factor (0.5–1.0) الذي يُطبّقه
        _calculate_position_size لتخفيض حجم الصفقة عند الحالات الحذرة.
        """
        # إعادة تعيين المعامل افتراضياً (1.0 = بدون تخفيض)
        self._market_caution_factor = 1.0

        try:
            df = self.data_provider.get_historical_data("BTCUSDT", "1h", limit=50)
            if df is None or len(df) < 30:
                return True  # في حال عدم توفر بيانات BTC، نسمح بالدخول

            df = self._add_indicators(df)

            last = df.iloc[-1]
            rsi = last.get("rsi", 50)

            # Fix-A: RSI < 25 = ذعر بيع شديد → تقليل حجم الصفقة 50%
            if rsi < 25:
                self._market_caution_factor = 0.5
                self.logger.warning(
                    f"   🌡️ BTC RSI={rsi:.1f} (extreme oversold) "
                    f"— position size ×0.5 (caution mode)"
                )

            # فحص الانهيار الحاد (أكثر من 5% هبوط في 24 ساعة)
            if len(df) >= 24:
                price_24h_ago = df.iloc[-24]["close"]
                price_now = df.iloc[-1]["close"]
                change_24h = (price_now - price_24h_ago) / price_24h_ago

                if change_24h < -0.05:
                    self.logger.warning(
                        f"   🚨 BTC crashed {
                            change_24h * 100:.1f}% in 24h - blocking entries"
                    )
                    # لن يُستخدم (نرجع False)
                    self._market_caution_factor = 0.0
                    return False

                # Fix-A: هبوط 3–5% → تقليل حجم الصفقة 30%
                if change_24h < -0.03:
                    self._market_caution_factor = min(self._market_caution_factor, 0.7)
                    self.logger.info(
                        f"   ⚠️ BTC down {change_24h * 100:.1f}% in 24h "
                        f"— position size ×{self._market_caution_factor:.1f}"
                    )

            # فحص التقلب العالي (ATR > 3% من السعر)
            if len(df) >= 14:
                atr = df["close"].diff().abs().rolling(14).mean().iloc[-1]
                atr_pct = atr / df.iloc[-1]["close"]
                if atr_pct > 0.03:
                    self.logger.warning(
                        f"   🌊 BTC volatility too high (ATR={
                            atr_pct * 100:.1f}%) - blocking entries"
                    )
                    # لن يُستخدم (نرجع False)
                    self._market_caution_factor = 0.0
                    return False

            return True

        except Exception as e:
            self.logger.warning(
                f"⚠️ Market regime check failed: {e} — blocking entries (No classification → No trade)"
            )
            self._market_caution_factor = 0.0
            return False  # قانون: لا تصنيف = لا تداول

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """إضافة المؤشرات الفنية"""
        df = df.copy()

        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        df["sma_20"] = df["close"].rolling(window=20).mean()
        df["std"] = df["close"].rolling(window=20).std()
        df["bb_lower"] = df["sma_20"] - (2 * df["std"])
        df["bb_upper"] = df["sma_20"] + (2 * df["std"])

        # MACD
        exp1 = df["close"].ewm(span=12, adjust=False).mean()
        exp2 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = exp1 - exp2
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        return df

    def _analyze_smart_money_confluence(
        self, symbol: str, df: pd.DataFrame, signal: Dict
    ) -> Optional[Dict]:
        """
        تحليل التوافق مع Smart Money للإشارة الحالية

        Args:
            symbol: رمز العملة
            df: بيانات السعر والحجم
            signal: الإشارة الأصلية

        Returns:
            نتائج تحليل Smart Money أو None
        """
        if not SMART_MONEY_AVAILABLE:
            return None

        try:
            # إنشاء Smart Money Orchestrator
            if not hasattr(self, "_smart_money_orchestrator"):
                self._smart_money_orchestrator = SmartMoneyOrchestrator()

            # تحضير البيانات - نحتاج إطارين زمنيين
            df_15m = self.data_provider.get_historical_data(symbol, "15m", limit=200)
            df_5m = self.data_provider.get_historical_data(symbol, "5m", limit=200)

            if df_15m is None or df_5m is None:
                return None

            # التحليل الشامل لنشاط Smart Money
            analysis = self._smart_money_orchestrator.analyze_smart_money_activity(
                symbol=symbol, df_15m=df_15m, df_5m=df_5m
            )

            if analysis.get("error"):
                self.logger.debug(
                    f"Smart Money analysis error for {symbol}: {
                        analysis.get('error_message')
                    }"
                )
                return None

            # استخراج المعلومات المهمة
            confluence_score = analysis.get("confluence_score", 0)
            smart_signal = analysis.get("smart_money_signal")

            if confluence_score < 40:  # عتبة التوافق الأدنى
                return None

            return {
                "confluence_score": confluence_score,
                "smart_money_signal": smart_signal,
                "analysis_data": analysis.get("analysis_data", {}),
                "risk_assessment": analysis.get("risk_assessment", {}),
            }

        except Exception as e:
            self.logger.debug(f"Smart Money confluence analysis error: {e}")
            return None

    def _enhance_signal_with_smart_money(
        self, original_signal: Dict, smart_money_data: Dict
    ) -> Dict:
        """
        تحسين الإشارة الأصلية بناءً على تحليل Smart Money

        Args:
            original_signal: الإشارة الأصلية من الاستراتيجية
            smart_money_data: بيانات تحليل Smart Money

        Returns:
            الإشارة المحسنة
        """
        enhanced_signal = original_signal.copy()

        try:
            confluence_score = smart_money_data.get("confluence_score", 0)
            smart_signal = smart_money_data.get("smart_money_signal")
            analysis_data = smart_money_data.get("analysis_data", {})

            # تحسين نقاط الإشارة
            # مكافأة تصل إلى 20 نقطة
            score_boost = min(20, confluence_score * 0.2)
            enhanced_signal["score"] = enhanced_signal.get("score", 0) + score_boost

            # إضافة معلومات Smart Money
            enhanced_signal["smart_money"] = {
                "confluence_score": confluence_score,
                "enhancement_applied": True,
                "score_boost": score_boost,
            }

            # تحسين مستوى الثقة إذا كانت إشارة Smart Money متوافقة
            if smart_signal and smart_signal.signal_type in ["BUY", "SELL"]:
                signal_alignment = (
                    enhanced_signal.get("side") == "LONG"
                    and smart_signal.signal_type == "BUY"
                ) or (
                    enhanced_signal.get("side") == "SHORT"
                    and smart_signal.signal_type == "SELL"
                )

                if signal_alignment:
                    enhanced_signal["smart_money"]["aligned"] = True
                    enhanced_signal["smart_money"]["smart_confidence"] = (
                        smart_signal.confidence
                    )
                    enhanced_signal["smart_money"]["reasons"] = smart_signal.reasons

                    # مكافأة إضافية للتوافق
                    enhanced_signal["score"] += 10
                    enhanced_signal["smart_money"]["alignment_boost"] = 10

                    self.logger.info(
                        f"   🧠 Smart Money ALIGNED: {
                            enhanced_signal.get('side')
                        } signal "
                        f"supported by {smart_signal.signal_type} (confidence: {
                            smart_signal.confidence:.1f}%)"
                    )
                else:
                    enhanced_signal["smart_money"]["aligned"] = False
                    self.logger.debug(
                        f"   🧠 Smart Money conflict: {enhanced_signal.get('side')} vs {
                            smart_signal.signal_type
                        }"
                    )

            # إضافة معلومات مناطق السيولة المهمة
            zones_data = analysis_data.get("liquidity_zones", {})
            if zones_data:
                all_zones = zones_data.get("all_zones", [])
                if all_zones:
                    strong_zones = [z for z in all_zones if z.strength > 70]
                    enhanced_signal["smart_money"]["liquidity_zones_count"] = len(
                        strong_zones
                    )

            # إضافة معلومات VWAP
            vwap_data = analysis_data.get("vwap_analysis", {})
            if vwap_data:
                vwap_strength = vwap_data.get("vwap_strength", {}).get(
                    "overall_strength", 0
                )
                if vwap_strength > 60:
                    enhanced_signal["smart_money"]["vwap_support"] = True
                    enhanced_signal["smart_money"]["vwap_strength"] = vwap_strength

            return enhanced_signal

        except Exception as e:
            self.logger.debug(f"Smart Money signal enhancement error: {e}")
            return original_signal
