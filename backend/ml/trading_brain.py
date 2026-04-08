#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trading Brain - طبقة التفكير المركزية
العقل الذي يفكر قبل كل صفقة ويتعلم من الأخطاء

يجمع بين:
1. MLSignalClassifier - تصنيف الإشارات
2. PatternSimilarityMatcher - مطابقة الأنماط
3. DualPathDecision - قرار مزدوج
4. HybridMLSystem - تعلم هجين
5. DynamicBlacklist - القائمة السوداء الديناميكية
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class MistakeMemory:
    """ذاكرة الأخطاء - يتذكر الأخطاء السابقة ويتجنب تكرارها"""

    def __init__(self, max_mistakes: int = 500):
        self.mistakes: List[Dict] = []
        self.max_mistakes = max_mistakes
        self.mistake_patterns: Dict[str, Dict] = defaultdict(
            lambda: {
                "count": 0,
                "total_loss": 0,
                "last_occurrence": None,
                "conditions": [],
            }
        )

        # أنماط الأخطاء المكتشفة
        self.discovered_patterns = []

    def record_mistake(self, trade_data: Dict, market_conditions: Dict, reason: str):
        """تسجيل خطأ جديد"""
        mistake = {
            "timestamp": datetime.now().isoformat(),
            "symbol": trade_data.get("symbol"),
            "entry_price": trade_data.get("entry_price"),
            "exit_price": trade_data.get("exit_price"),
            "loss": trade_data.get("profit_loss", 0),
            "reason": reason,
            "market_conditions": {
                "rsi": market_conditions.get("rsi"),
                "volatility": market_conditions.get("volatility"),
                "trend": market_conditions.get("trend"),
                "volume": market_conditions.get("volume_ratio"),
                "bb_position": market_conditions.get("bb_position"),
            },
            "signal_confidence": trade_data.get("confidence"),
            "strategy": trade_data.get("strategy"),
        }

        self.mistakes.append(mistake)

        # تحديث أنماط الأخطاء
        self._update_patterns(mistake)

        # الحفاظ على الحد الأقصى
        if len(self.mistakes) > self.max_mistakes:
            self.mistakes = self.mistakes[-self.max_mistakes :]

        logger.warning(
            f"🧠 تم تسجيل خطأ: {reason} | {trade_data.get('symbol')} | خسارة: ${
                abs(trade_data.get('profit_loss', 0)):.2f}"
        )

    def _update_patterns(self, mistake: Dict):
        """تحديث أنماط الأخطاء"""
        # تصنيف الخطأ
        pattern_key = self._classify_mistake(mistake)

        pattern = self.mistake_patterns[pattern_key]
        pattern["count"] += 1
        pattern["total_loss"] += abs(mistake.get("loss", 0))
        pattern["last_occurrence"] = mistake["timestamp"]
        pattern["conditions"].append(mistake["market_conditions"])

        # اكتشاف أنماط جديدة
        if pattern["count"] >= 3:
            self._analyze_pattern(pattern_key, pattern)

    def _classify_mistake(self, mistake: Dict) -> str:
        """تصنيف الخطأ إلى نمط"""
        conditions = mistake.get("market_conditions", {})

        # تصنيف حسب RSI
        rsi = conditions.get("rsi", 50)
        if rsi > 70:
            rsi_class = "overbought"
        elif rsi < 30:
            rsi_class = "oversold"
        else:
            rsi_class = "neutral"

        # تصنيف حسب التقلب
        vol = conditions.get("volatility", 0)
        if vol > 0.05:
            vol_class = "high_vol"
        elif vol < 0.02:
            vol_class = "low_vol"
        else:
            vol_class = "med_vol"

        # تصنيف حسب الاتجاه
        trend = conditions.get("trend", 0)
        if trend > 0.02:
            trend_class = "uptrend"
        elif trend < -0.02:
            trend_class = "downtrend"
        else:
            trend_class = "sideways"

        return f"{rsi_class}_{vol_class}_{trend_class}"

    def _analyze_pattern(self, pattern_key: str, pattern: Dict):
        """تحليل النمط واكتشاف القواعد"""
        if pattern_key in [p["key"] for p in self.discovered_patterns]:
            return

        avg_loss = pattern["total_loss"] / pattern["count"]

        # إذا الخسارة المتوسطة كبيرة، أضف كنمط مكتشف
        if avg_loss > 3 and pattern["count"] >= 3:
            discovered = {
                "key": pattern_key,
                "count": pattern["count"],
                "avg_loss": avg_loss,
                "rule": self._generate_rule(pattern_key),
                "discovered_at": datetime.now().isoformat(),
            }
            self.discovered_patterns.append(discovered)
            logger.info(
                f"🧠 اكتشاف نمط خطأ جديد: {pattern_key} | تكرار: {
                    pattern['count']
                } | متوسط الخسارة: ${avg_loss:.2f}"
            )

    def _generate_rule(self, pattern_key: str) -> str:
        """توليد قاعدة لتجنب الخطأ"""
        parts = pattern_key.split("_")
        rules = []

        if "overbought" in parts:
            rules.append("تجنب الشراء عند RSI > 70")
        if "high_vol" in parts:
            rules.append("تقليل الحجم في التقلب العالي")
        if "downtrend" in parts:
            rules.append("تجنب الشراء في الاتجاه الهابط")

        return " | ".join(rules) if rules else "مراجعة الشروط"

    def should_avoid(self, market_conditions: Dict) -> Dict[str, Any]:
        """هل يجب تجنب هذه الصفقة بناءً على الأخطاء السابقة؟"""
        current_pattern = self._classify_mistake(
            {"market_conditions": market_conditions}
        )

        # فحص الأنماط المكتشفة
        for pattern in self.discovered_patterns:
            if pattern["key"] == current_pattern:
                return {
                    "avoid": True,
                    "reason": f"نمط خطأ مكتشف: {pattern['rule']}",
                    "occurrences": pattern["count"],
                    "avg_loss": pattern["avg_loss"],
                }

        # فحص الأنماط المتكررة
        if current_pattern in self.mistake_patterns:
            pattern = self.mistake_patterns[current_pattern]
            if pattern["count"] >= 2:
                return {
                    "avoid": True,
                    "reason": f"تكرار خطأ سابق ({pattern['count']} مرات)",
                    "occurrences": pattern["count"],
                    "avg_loss": pattern["total_loss"] / pattern["count"],
                }

        return {"avoid": False}


class TradingBrain:
    """
    العقل المركزي للتداول
    يفكر قبل كل صفقة ويتعلم من الأخطاء
    """

    def __init__(self, db_manager=None):
        self.logger = logger
        self.db = db_manager

        # ذاكرة الأخطاء
        self.mistake_memory = MistakeMemory()

        # إحصائيات التفكير
        self.stats = {
            "total_decisions": 0,
            "approved": 0,
            "rejected": 0,
            "rejection_reasons": defaultdict(int),
            "accuracy": 0.0,
        }

        # تتبع القرارات للتعلم
        self.pending_decisions: Dict[str, Dict] = {}

        # حدود الثقة المتكيفة
        self.confidence_thresholds = {
            "BTCUSDT": 0.55,
            "ETHUSDT": 0.55,
            "default": 0.60,
        }

        # قواعد التعلم
        self.learned_rules: List[Dict] = []

        # ===== Phase-Aware Trading System =====
        from backend.ml.backtest_importer import (
            PHASE_BACKTEST,
            PHASE_PAPER,
            PHASE_VALIDATION,
            PHASE_LIVE,
        )

        self.current_phase = PHASE_BACKTEST
        self.PHASE_BACKTEST = PHASE_BACKTEST
        self.PHASE_PAPER = PHASE_PAPER
        self.PHASE_VALIDATION = PHASE_VALIDATION
        self.PHASE_LIVE = PHASE_LIVE

        # Paper Trading Engine
        from backend.ml.paper_trading import get_paper_engine

        self.paper_engine = get_paper_engine(db_manager)

        # Live Validator
        from backend.ml.live_validator import get_validator

        self.validator = get_validator()

        # تحميل ML إذا متوفر
        self._init_ml_systems()

        # تحميل المرحلة من قاعدة البيانات
        self._load_phase_from_db()

        logger.info(f"🧠 Trading Brain initialized | Phase: {self.current_phase}")

    def set_phase(self, phase: str):
        valid = (
            self.PHASE_BACKTEST,
            self.PHASE_PAPER,
            self.PHASE_VALIDATION,
            self.PHASE_LIVE,
        )
        if phase in valid:
            self.current_phase = phase
            self._save_phase_to_db()
            logger.info(f"🔄 Phase set: {phase}")

    def _init_ml_systems(self):
        try:
            from backend.ml.signal_classifier import get_ml_classifier
            from backend.ml.pattern_similarity_matcher import (
                get_similarity_matcher,
            )
            from backend.ml.dual_path_decision import DualPathDecision
            from backend.ml.hybrid_learning_system import HybridMLSystem

            self.ml_classifier = get_ml_classifier()
            self.similarity_matcher = get_similarity_matcher()
            self.dual_decision = DualPathDecision()
            self.hybrid_system = HybridMLSystem()

            self.ml_available = True
            logger.info("🧠 أنظمة ML متصلة")

        except Exception as e:
            self.ml_available = False
            self.ml_classifier = None
            self.similarity_matcher = None
            self.dual_decision = None
            self.hybrid_system = None
            logger.warning(f"⚠️ ML غير متوفر: {e}")

    def _load_phase_from_db(self):
        try:
            if not self.db:
                return
            with self.db.get_connection() as conn:
                row = conn.execute(
                    "SELECT current_phase FROM trading_phase_state WHERE id = 1"
                ).fetchone()
                if row and row[0] in (
                    self.PHASE_BACKTEST,
                    self.PHASE_PAPER,
                    self.PHASE_VALIDATION,
                    self.PHASE_LIVE,
                ):
                    self.current_phase = row[0]
                    logger.info(f"📥 Phase loaded from DB: {self.current_phase}")
        except Exception as e:
            if "trading_phase_state" in str(e):
                logger.debug("trading_phase_state table not found, using default phase")
            else:
                logger.warning(f"⚠️ Failed to load phase from DB: {e}")

    def _save_phase_to_db(self):
        try:
            if not self.db:
                return
            with self.db.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO trading_phase_state (id, current_phase, updated_at)
                    VALUES (1, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO UPDATE SET current_phase = %s, updated_at = CURRENT_TIMESTAMP
                """,
                    (self.current_phase, self.current_phase),
                )
                conn.commit()
                logger.info(f"💾 Phase saved to DB: {self.current_phase}")
        except Exception as e:
            if "trading_phase_state" in str(e):
                logger.debug("trading_phase_state table not found, skipping save")
            else:
                logger.warning(f"⚠️ Failed to save phase to DB: {e}")

    def think(self, signal: Dict, market_data: Dict) -> Dict[str, Any]:
        """
        التفكير قبل اتخاذ قرار التداول — Phase-Aware.
        """
        self.stats["total_decisions"] += 1

        symbol = signal.get("symbol", market_data.get("symbol", "UNKNOWN"))
        confidence = signal.get("confidence", 0) / 100

        decision = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "phase": self.current_phase,
            "original_confidence": confidence,
            "checks_passed": [],
            "checks_failed": [],
            "final_decision": "pending",
            "adjusted_confidence": confidence,
            "reasoning": [],
        }

        # ===== Phase-Specific Logic =====
        if self.current_phase == self.PHASE_BACKTEST:
            return self._decide_bootstrap(signal, decision)

        if self.current_phase == self.PHASE_PAPER:
            return self._decide_paper(signal, market_data, decision)

        if self.current_phase == self.PHASE_VALIDATION:
            return self._decide_validation(signal, market_data, decision)

        # PHASE_LIVE — full ML filtering
        return self._decide_live(signal, market_data, decision)

    def _decide_bootstrap(self, signal: Dict, decision: Dict) -> Dict[str, Any]:
        """Phase 1: Bootstrap — approve all signals for paper trading."""
        decision["final_decision"] = "APPROVE"
        decision["execution_mode"] = "PAPER"
        decision["reasoning"].append("✅ Bootstrap phase — routing to paper trading")
        self.stats["approved"] += 1
        return decision

    def _decide_paper(
        self, signal: Dict, market_data: Dict, decision: Dict
    ) -> Dict[str, Any]:
        """Phase 2: Paper Trading — approve signals, track results."""
        mistake_check = self.mistake_memory.should_avoid(market_data)
        if mistake_check["avoid"]:
            decision["checks_failed"].append("mistake_memory")
            decision["final_decision"] = "REJECT"
            decision["rejection_reason"] = "repeated_mistake_pattern"
            self._record_rejection(decision)
            return decision

        decision["final_decision"] = "APPROVE"
        decision["execution_mode"] = "PAPER"
        decision["reasoning"].append(
            "✅ Paper trading — signal approved for simulation"
        )
        self.stats["approved"] += 1

        # Route to paper engine
        paper_result = self.paper_engine.process_signal(signal)
        decision["paper_trade"] = paper_result

        return decision

    def _decide_validation(
        self, signal: Dict, market_data: Dict, decision: Dict
    ) -> Dict[str, Any]:
        """Phase 3: Validation — paper trading + periodic validation check."""
        mistake_check = self.mistake_memory.should_avoid(market_data)
        if mistake_check["avoid"]:
            decision["checks_failed"].append("mistake_memory")
            decision["final_decision"] = "REJECT"
            decision["rejection_reason"] = "repeated_mistake_pattern"
            self._record_rejection(decision)
            return decision

        decision["final_decision"] = "APPROVE"
        decision["execution_mode"] = "PAPER"
        decision["reasoning"].append(
            "✅ Validation phase — paper trading with validation"
        )
        self.stats["approved"] += 1

        paper_result = self.paper_engine.process_signal(signal)
        decision["paper_trade"] = paper_result

        # Run validation check
        paper_stats = self.paper_engine.get_stats()
        self.validator.update_paper_results(paper_stats)
        validation = self.validator.validate()
        decision["validation"] = validation

        if validation["ready"]:
            self.current_phase = self.PHASE_LIVE
            self._save_phase_to_db()
            decision["phase_transition"] = "PAPER → LIVE"
            logger.info("🚀 Phase transition: PAPER_TRADING → LIVE_TRADING")

        return decision

    def _decide_live(
        self, signal: Dict, market_data: Dict, decision: Dict
    ) -> Dict[str, Any]:
        """Phase 4: Live Trading — full ML filtering."""
        # Existing ML filtering logic
        mistake_check = self.mistake_memory.should_avoid(market_data)
        if mistake_check["avoid"]:
            decision["checks_failed"].append("mistake_memory")
            decision["reasoning"].append(f"❌ {mistake_check['reason']}")
            decision["final_decision"] = "REJECT"
            decision["rejection_reason"] = "repeated_mistake_pattern"
            self._record_rejection(decision)
            return decision
        decision["checks_passed"].append("mistake_memory")

        if self.ml_available and self.ml_classifier:
            ml_result = self._check_ml_classifier(signal, market_data)
            if not ml_result["approved"]:
                decision["checks_failed"].append("ml_classifier")
                decision["reasoning"].append(f"❌ ML: {ml_result['reason']}")
                decision["final_decision"] = "REJECT"
                decision["rejection_reason"] = "ml_rejected"
                self._record_rejection(decision)
                return decision
            decision["checks_passed"].append("ml_classifier")
            decision["adjusted_confidence"] *= ml_result.get(
                "confidence_multiplier", 1.0
            )

        if self.ml_available and self.similarity_matcher:
            similarity_result = self._check_pattern_similarity(market_data)
            if similarity_result["similarity"] < 0.4:
                decision["checks_failed"].append("pattern_similarity")
                decision["adjusted_confidence"] *= 0.85
            else:
                decision["checks_passed"].append("pattern_similarity")

        if self.ml_available and self.dual_decision:
            dual_result = self._check_dual_decision(signal, market_data)
            if dual_result["action"] == "skip":
                decision["checks_failed"].append("dual_decision")
                decision["adjusted_confidence"] *= 0.9
            else:
                decision["checks_passed"].append("dual_decision")

        rules_result = self._check_learned_rules(signal, market_data)
        if rules_result["violations"]:
            decision["checks_failed"].extend(["learned_rules"])
            decision["adjusted_confidence"] *= 0.8
        else:
            decision["checks_passed"].append("learned_rules")

        threshold = self.confidence_thresholds.get(
            symbol, self.confidence_thresholds["default"]
        )

        if decision["adjusted_confidence"] >= threshold:
            decision["final_decision"] = "APPROVE"
            decision["execution_mode"] = "LIVE"
            decision["reasoning"].append(
                f"✅ Live trading approved: {decision['adjusted_confidence']:.0%} >= {threshold:.0%}"
            )
            self.stats["approved"] += 1
        else:
            decision["final_decision"] = "REJECT"
            decision["rejection_reason"] = "low_confidence"
            decision["reasoning"].append(
                f"❌ Low confidence: {decision['adjusted_confidence']:.0%} < {threshold:.0%}"
            )
            self._record_rejection(decision)

        decision_id = f"{symbol}_{datetime.now().timestamp()}"
        self.pending_decisions[decision_id] = decision
        decision["decision_id"] = decision_id

        self._log_decision(decision)
        return decision

    def _check_ml_classifier(self, signal: Dict, market_data: Dict) -> Dict:
        """فحص ML Classifier"""
        try:
            if not self.ml_classifier or not self.ml_classifier.is_ready():
                return {
                    "approved": True,
                    "reason": "ML not ready",
                    "confidence_multiplier": 1.0,
                }

            # تحضير الميزات
            features = self._prepare_features(signal, market_data)
            result = self.ml_classifier.predict(features)

            if result.get("should_trade", True):
                return {
                    "approved": True,
                    "confidence_multiplier": result.get("confidence", 0.7),
                    "reason": "ML approved",
                }
            else:
                return {
                    "approved": False,
                    "reason": f"ML confidence: {result.get('confidence', 0):.0%}",
                }

        except Exception as e:
            logger.warning(f"خطأ في ML: {e}")
            return {
                "approved": True,
                "reason": "ML error",
                "confidence_multiplier": 1.0,
            }

    def _check_pattern_similarity(self, market_data: Dict) -> Dict:
        """فحص تشابه الأنماط"""
        try:
            # نمط مرجعي (ناجح)
            reference_pattern = {
                "indicators": {"rsi": 35, "macd": 0.5},
                "trend": 0.02,
                "volume": 1.2,
            }

            current = {
                "indicators": {
                    "rsi": market_data.get("rsi", 50),
                    "macd": market_data.get("macd", 0),
                },
                "trend": market_data.get("trend", 0),
                "volume": market_data.get("volume_ratio", 1),
            }

            similarity = self.similarity_matcher.calculate_similarity(
                current, reference_pattern
            )
            return {"similarity": similarity}

        except Exception as e:
            logger.warning(f"خطأ في Pattern Similarity: {e}")
            return {"similarity": 0.5}

    def _check_dual_decision(self, signal: Dict, market_data: Dict) -> Dict:
        """فحص القرار المزدوج"""
        try:
            signal_data = {
                "confidence": signal.get("confidence", 50) / 100,
                "indicators": market_data,
                "volatility": market_data.get("volatility", 0.03),
            }

            result = self.dual_decision.decide(signal_data)
            return result

        except Exception as e:
            logger.warning(f"خطأ في Dual Decision: {e}")
            return {"action": "trade"}

    def _check_learned_rules(self, signal: Dict, market_data: Dict) -> Dict:
        """فحص القواعد المتعلمة"""
        violations = []

        # قواعد ثابتة مبنية على التجربة
        rsi = market_data.get("rsi", 50)
        volatility = market_data.get("volatility", 0.03)
        trend = market_data.get("trend", 0)

        # قاعدة 1: لا تشتري في RSI عالي جداً
        if rsi > 75:
            violations.append("RSI > 75")

        # قاعدة 2: حذر في التقلب العالي جداً
        if volatility > 0.08:
            violations.append("Volatility > 8%")

        # قاعدة 3: لا تشتري في اتجاه هابط قوي
        if trend < -0.05:
            violations.append("Strong downtrend")

        # القواعد المتعلمة من الأخطاء
        for rule in self.learned_rules:
            if self._rule_violated(rule, market_data):
                violations.append(rule["name"])

        return {"violations": violations}

    def _rule_violated(self, rule: Dict, market_data: Dict) -> bool:
        """فحص انتهاك قاعدة"""
        try:
            field = rule.get("field")
            operator = rule.get("operator")
            value = rule.get("value")

            actual = market_data.get(field, 0)

            if operator == ">":
                return actual > value
            elif operator == "<":
                return actual < value
            elif operator == "==":
                return actual == value

            return False
        except Exception:
            return False

    def _prepare_features(self, signal: Dict, market_data: Dict) -> Dict:
        """تحضير الميزات لـ ML"""
        return {
            "rsi": market_data.get("rsi", 50),
            "macd": market_data.get("macd", 0),
            "bb_position": market_data.get("bb_position", 0.5),
            "volume_ratio": market_data.get("volume_ratio", 1),
            "volatility": market_data.get("volatility", 0.03),
            "trend": market_data.get("trend", 0),
            "confidence": signal.get("confidence", 50) / 100,
        }

    def _record_rejection(self, decision: Dict):
        """تسجيل الرفض"""
        self.stats["rejected"] += 1
        reason = decision.get("rejection_reason", "unknown")
        self.stats["rejection_reasons"][reason] += 1

    def _log_decision(self, decision: Dict):
        """تسجيل القرار"""
        status = (
            "✅ APPROVE" if decision["final_decision"] == "APPROVE" else "❌ REJECT"
        )
        logger.info(
            f"🧠 {decision['symbol']} | {status} | "
            f"الثقة: {decision['adjusted_confidence']:.0%} | "
            f"الفحوصات: {len(decision['checks_passed'])}/{len(decision['checks_passed']) + len(decision['checks_failed'])}"
        )

    def learn_from_result(self, decision_id: str, trade_result: Dict):
        """
        التعلم من نتيجة الصفقة

        Args:
            decision_id: معرف القرار
            trade_result: نتيجة الصفقة
        """
        if decision_id not in self.pending_decisions:
            return

        decision = self.pending_decisions.pop(decision_id)
        is_win = trade_result.get("profit_loss", 0) > 0

        if decision["final_decision"] == "APPROVE":
            if is_win:
                # قرار صحيح - ربح
                logger.info(f"🧠 تعلم: قرار صحيح ✅ | {decision['symbol']}")
            else:
                # قرار خاطئ - خسارة
                logger.warning(f"🧠 تعلم: قرار خاطئ ❌ | {decision['symbol']}")

                # تسجيل الخطأ
                self.mistake_memory.record_mistake(
                    trade_data={
                        "symbol": decision["symbol"],
                        "entry_price": trade_result.get("entry_price"),
                        "exit_price": trade_result.get("exit_price"),
                        "profit_loss": trade_result.get("profit_loss"),
                        "confidence": decision["original_confidence"],
                        "strategy": trade_result.get("strategy"),
                    },
                    market_conditions=trade_result.get("market_conditions", {}),
                    reason=f"خسارة رغم الموافقة (ثقة: {decision['original_confidence']:.0%})",
                )

                # تعديل عتبة الثقة
                symbol = decision["symbol"]
                if symbol in self.confidence_thresholds:
                    self.confidence_thresholds[symbol] = min(
                        0.75, self.confidence_thresholds[symbol] + 0.02
                    )
                    logger.info(
                        f"🧠 رفع عتبة الثقة لـ {symbol}: {
                            self.confidence_thresholds[symbol]:.0%}"
                    )

        # تحديث الدقة
        self._update_accuracy()

    def _update_accuracy(self):
        """تحديث الدقة"""
        total = self.stats["approved"] + self.stats["rejected"]
        if total > 0:
            # الدقة = القرارات الصحيحة / الإجمالي
            # (يحتاج تتبع أكثر دقة)
            pass

    def get_status(self) -> Dict:
        """الحصول على حالة العقل"""
        return {
            "total_decisions": self.stats["total_decisions"],
            "approved": self.stats["approved"],
            "rejected": self.stats["rejected"],
            "rejection_reasons": dict(self.stats["rejection_reasons"]),
            "ml_available": self.ml_available,
            "mistakes_recorded": len(self.mistake_memory.mistakes),
            "discovered_patterns": len(self.mistake_memory.discovered_patterns),
            "learned_rules": len(self.learned_rules),
            "confidence_thresholds": self.confidence_thresholds,
        }


# Singleton
_trading_brain = None


def get_trading_brain(db_manager=None) -> TradingBrain:
    """الحصول على instance واحد"""
    global _trading_brain
    if _trading_brain is None:
        _trading_brain = TradingBrain(db_manager)
    return _trading_brain
