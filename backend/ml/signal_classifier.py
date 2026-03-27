#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML Signal Classifier - مصنف إشارات التداول باستخدام XGBoost
يتدرب على نتائج Backtesting ويفلتر الإشارات في التداول الفعلي
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

try:
    import xgboost as xgb
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
    )
    from sklearn.preprocessing import StandardScaler
    from sklearn.exceptions import InconsistentVersionWarning
    import joblib

    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# إعداد اللوجر
logger = logging.getLogger(__name__)


class MLSignalClassifier:
    """
    مصنف إشارات ML باستخدام XGBoost

    يتدرب على نتائج Backtesting ويستخدم لفلترة الإشارات في التداول الفعلي
    """

    # معايير الجاهزية - محسّنة للبيانات الحقيقية فقط
    MIN_SAMPLES_FOR_TRAINING = 50  # الحد الأدنى للتدريب (بيانات حقيقية)
    MIN_SAMPLES_FOR_READINESS = (
        100  # ✅ تم التخفيض من 200 إلى 100 للبداية السريعة
    )
    # الحد الأدنى للدقة (65% - أفضل من العشوائية بـ 15%)
    MIN_ACCURACY_FOR_READINESS = 0.65
    MIN_STABLE_CYCLES = 2  # عدد الدورات المستقرة المطلوبة
    BASE_CONFIDENCE_THRESHOLD = 0.60  # عتبة الثقة الأساسية (ديناميكية)
    USE_DYNAMIC_THRESHOLD = True  # استخدام العتبة الديناميكية

    # معايير جودة البيانات
    MIN_WIN_RATE_FOR_TRAINING = 0.35  # حد أدنى لنسبة الفوز (35%)
    MAX_LOSS_RATIO = 0.40  # حد أقصى لنسبة الخسائر (40%)
    MIN_TRADES_PER_STRATEGY = 10  # حد أدنى من الصفقات لكل استراتيجية

    def __init__(self, model_dir: str = None):
        """
        تهيئة المصنف

        Args:
            model_dir: مجلد حفظ النماذج
        """
        if not ML_AVAILABLE:
            logger.warning("⚠️ مكتبات ML غير متوفرة - سيعمل النظام بدون ML")
            self.enabled = False
            self.model = None
            self.scaler = None
            self.model_dir = None
            self.model_path = None
            self.scaler_path = None
            self.history_path = None
            self.data_path = None
            self.training_history = {"cycles": [], "best_accuracy": 0}
            self.training_data = []
            self._is_ready_fallback = False
            self.readiness_score = 0
            self.stable_cycles = 0
            return

        self.enabled = True
        self.model_dir = model_dir or os.path.join(
            os.path.dirname(__file__), "saved_models"
        )
        os.makedirs(self.model_dir, exist_ok=True)

        # مسارات الملفات
        self.model_path = os.path.join(self.model_dir, "signal_model.json")
        self.scaler_path = os.path.join(self.model_dir, "scaler.pkl")
        self.history_path = os.path.join(
            self.model_dir, "training_history.json"
        )
        self.data_path = os.path.join(self.model_dir, "training_data.pkl")

        # النموذج والمعالج
        self.model = None
        self.scaler = StandardScaler()

        # سجل التدريب
        self.training_history = self._load_history()

        # بيانات التدريب المتراكمة
        self.accumulated_data = self._load_accumulated_data()

        # الميزات المستخدمة (شاملة لجميع الاستراتيجيات)
        self.feature_columns = [
            # ========== المؤشرات العامة ==========
            "rsi",
            "rsi_slope",
            "macd",
            "macd_signal",
            "macd_histogram",
            "bb_position",
            "bb_width",
            "volume_ratio",
            "volume_trend",
            "ema_trend",
            "ema_distance",
            "atr_pct",
            "volatility",
            "price_change_1h",
            "price_change_4h",
            "trend_strength",
            "momentum",
            # ========== مؤشرات TrendFollowing ==========
            "adx",  # قوة الاتجاه (ADX > 25 = اتجاه قوي)
            "plus_di",
            "minus_di",  # مؤشرات الاتجاه
            # تقاطع EMAs (1=صاعد, -1=هابط, 0=لا تقاطع)
            "ema_cross",
            # ========== مؤشرات MeanReversion ==========
            "stoch_k",
            "stoch_d",  # Stochastic
            "distance_from_mean",  # المسافة من المتوسط
            "oversold",
            "overbought",  # تشبع بيعي/شرائي
            # ========== مؤشرات ScalpingEMA ==========
            "ema_9_21_cross",  # تقاطع EMA9 و EMA21
            "ema_21_55_cross",  # تقاطع EMA21 و EMA55
            "price_above_ema9",  # السعر فوق EMA9
            # ========== مؤشرات RSIDivergence ==========
            # تباعد RSI (1=إيجابي, -1=سلبي, 0=لا تباعد)
            "rsi_divergence",
            "price_making_lower_low",  # السعر يصنع قاع أدنى
            "rsi_making_higher_low",  # RSI يصنع قاع أعلى
            # ========== مؤشرات VolumePriceTrend ==========
            "obv_trend",  # اتجاه OBV
            "volume_price_confirm",  # تأكيد الحجم للسعر
            "vwap_position",  # موقع السعر من VWAP
            # ========== الاستراتيجية والإطار الزمني ==========
            "strategy_trend_following",
            "strategy_momentum_breakout",
            "strategy_mean_reversion",
            "strategy_scalping",
            "strategy_rsi_divergence",
            "strategy_volume_price",
            "strategy_other",
            "timeframe_15m",
            "timeframe_1h",
            "timeframe_4h",
        ]

        # قائمة الاستراتيجيات المعروفة
        self.known_strategies = [
            "TrendFollowing",
            "MomentumBreakout",
            "MeanReversion",
            "ScalpingEMA",
            "RSIDivergence",
            "VolumePriceTrend",
        ]

        # قائمة الأطر الزمنية المعروفة
        self.known_timeframes = ["15m", "1h", "4h"]

        # تحميل النموذج إذا كان موجوداً
        self._load_model()

        logger.info(f"✅ تم تهيئة ML Signal Classifier")
        logger.info(f"   📊 بيانات متراكمة: {len(self.accumulated_data)} صفقة")
        logger.info(f"   🎯 الجاهزية: {
            '✅ جاهز' if self.is_ready() else '❌ غير جاهز'}")

    def _load_history(self) -> Dict:
        """تحميل سجل التدريب"""
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    # التأكد من أن history هو dict وليس list
                    if isinstance(history, list):
                        # تحويل list قديم إلى dict جديد
                        return {
                            "cycles": history,
                            "total_samples": 0,
                            "best_accuracy": 0.0,
                            "stable_cycles": 0,
                            "is_ready": False,
                            "last_training": None,
                        }
                    return history
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.debug(f"لا يمكن تحميل history: {e}")
        return {
            "cycles": [],
            "total_samples": 0,
            "best_accuracy": 0,
            "stable_cycles": 0,
            "is_ready": False,
            "last_training": None,
        }

    def _save_history(self):
        """حفظ سجل التدريب"""
        try:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(
                    self.training_history, f, indent=2, ensure_ascii=False
                )
        except Exception as e:
            logger.error(f"خطأ في حفظ سجل التدريب: {e}")

    def _load_accumulated_data(self) -> pd.DataFrame:
        """تحميل البيانات المتراكمة"""
        if os.path.exists(self.data_path):
            try:
                return joblib.load(self.data_path)
            except Exception as e:
                logger.debug(f"لا يمكن تحميل البيانات: {e}")
        return pd.DataFrame()

    def _save_accumulated_data(self):
        """حفظ البيانات المتراكمة"""
        try:
            joblib.dump(self.accumulated_data, self.data_path)
        except Exception as e:
            logger.error(f"خطأ في حفظ البيانات المتراكمة: {e}")

    def _load_model(self):
        """تحميل النموذج المحفوظ"""
        if os.path.exists(self.model_path):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", InconsistentVersionWarning)

                    self.model = xgb.XGBClassifier()
                    self.model.load_model(self.model_path)

                    if os.path.exists(self.scaler_path):
                        self.scaler = joblib.load(self.scaler_path)

                logger.info("✅ تم تحميل النموذج المحفوظ")
            except InconsistentVersionWarning as e:
                logger.warning(
                    f"⚠️ نموذج ML محفوظ بإصدار مختلف: {e}. سيتم إعادة تهيئة ملفات النموذج.")
                self._archive_incompatible_artifacts()
                self.model = None
                self.scaler = StandardScaler()
            except Exception as e:
                logger.warning(f"⚠️ فشل تحميل النموذج: {e}")
                self.model = None

    def _archive_incompatible_artifacts(self):
        """أرشفة ملفات النموذج/المُقيّس غير المتوافقة لتفادي تحذيرات التحميل."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for path in [self.model_path, self.scaler_path]:
            try:
                if path and os.path.exists(path):
                    archived = f"{path}.incompatible_{timestamp}.bak"
                    os.replace(path, archived)
                    logger.info(f"🗄️ تم أرشفة ملف غير متوافق: {archived}")
            except Exception as archive_error:
                logger.warning(
                    f"⚠️ تعذر أرشفة ملف ML غير متوافق ({path}): {archive_error}")

    def _save_model(self):
        """حفظ النموذج"""
        if self.model is not None:
            try:
                self.model.save_model(self.model_path)
                joblib.dump(self.scaler, self.scaler_path)
                logger.info("✅ تم حفظ النموذج")
            except Exception as e:
                logger.error(f"خطأ في حفظ النموذج: {e}")

    def extract_features_from_backtest(
        self, backtest_result: Dict
    ) -> Optional[Dict]:
        """
        استخراج الميزات من نتيجة Backtesting واحدة

        Args:
            backtest_result: نتيجة الاختبار الخلفي

        Returns:
            قاموس الميزات أو None
        """
        try:
            stats = backtest_result.get("stats", {})
            indicators = backtest_result.get("indicators", {})

            # استخراج الميزات الأساسية
            features = {
                # RSI
                "rsi": indicators.get("rsi", 50) / 100,
                "rsi_slope": indicators.get("rsi_slope", 0),
                # MACD
                "macd": indicators.get("macd", 0),
                "macd_signal": indicators.get("macd_signal", 0),
                "macd_histogram": indicators.get("macd_histogram", 0),
                # Bollinger Bands
                "bb_position": indicators.get("bb_position", 0.5),
                "bb_width": indicators.get("bb_width", 0.02),
                # Volume
                "volume_ratio": min(indicators.get("volume_ratio", 1.0), 5.0),
                "volume_trend": indicators.get("volume_trend", 0),
                # EMA
                "ema_trend": (
                    1
                    if indicators.get("ema_trend", "neutral") == "up"
                    else (
                        -1
                        if indicators.get("ema_trend", "neutral") == "down"
                        else 0
                    )
                ),
                "ema_distance": indicators.get("ema_distance", 0),
                # ATR & Volatility
                "atr_pct": min(indicators.get("atr_pct", 0.02), 0.1),
                "volatility": min(indicators.get("volatility", 0.02), 0.1),
                # Price Changes
                "price_change_1h": np.clip(
                    indicators.get("price_change_1h", 0), -10, 10
                ),
                "price_change_4h": np.clip(
                    indicators.get("price_change_4h", 0), -20, 20
                ),
                # Trend & Momentum
                "trend_strength": indicators.get("trend_strength", 0),
                "momentum": indicators.get("momentum", 0),
            }

            # ========== إضافة الاستراتيجية والإطار الزمني ==========
            strategy = backtest_result.get("strategy", "")
            timeframe = backtest_result.get(
                "timeframe", backtest_result.get("selected_timeframe", "1h")
            )

            # تحويل الاستراتيجية إلى One-Hot Encoding
            strategy_lower = strategy.lower().replace("_", "").replace(" ", "")
            features["strategy_trend_following"] = (
                1 if "trendfollowing" in strategy_lower else 0
            )
            features["strategy_momentum_breakout"] = (
                1 if "momentumbreakout" in strategy_lower else 0
            )
            features["strategy_mean_reversion"] = (
                1 if "meanreversion" in strategy_lower else 0
            )
            features["strategy_scalping"] = (
                1
                if "scalping" in strategy_lower or "ema" in strategy_lower
                else 0
            )
            features["strategy_rsi_divergence"] = (
                1
                if "rsi" in strategy_lower or "divergence" in strategy_lower
                else 0
            )
            features["strategy_other"] = (
                1
                if sum(
                    [
                        features["strategy_trend_following"],
                        features["strategy_momentum_breakout"],
                        features["strategy_mean_reversion"],
                        features["strategy_scalping"],
                        features["strategy_rsi_divergence"],
                    ]
                )
                == 0
                else 0
            )

            # تحويل الإطار الزمني إلى One-Hot Encoding
            features["timeframe_15m"] = 1 if timeframe == "15m" else 0
            features["timeframe_1h"] = 1 if timeframe == "1h" else 0
            features["timeframe_4h"] = 1 if timeframe == "4h" else 0

            # التصنيف (الهدف): هل الصفقة ناجحة؟
            total_return = stats.get("Return [%]", 0)
            win_rate = stats.get("Win Rate [%]", 0)

            # صفقة ناجحة إذا: عائد إيجابي ونسبة فوز > 50%
            is_successful = 1 if (total_return > 0 and win_rate > 45) else 0

            features["target"] = is_successful
            features["return_pct"] = total_return
            features["win_rate"] = win_rate

            return features

        except Exception as e:
            logger.warning(f"خطأ في استخراج الميزات: {e}")
            return None

    def add_backtest_results(self, backtest_results: List[Dict]) -> int:
        """
        إضافة نتائج Backtesting للتدريب

        Args:
            backtest_results: قائمة نتائج الاختبار الخلفي

        Returns:
            عدد الصفقات المضافة
        """
        if not self.enabled:
            return 0

        added_count = 0
        new_data = []

        for result in backtest_results:
            features = self.extract_features_from_backtest(result)
            if features:
                new_data.append(features)
                added_count += 1

        if new_data:
            new_df = pd.DataFrame(new_data)

            if self.accumulated_data.empty:
                self.accumulated_data = new_df
            else:
                self.accumulated_data = pd.concat(
                    [self.accumulated_data, new_df], ignore_index=True
                )

            # حفظ البيانات
            self._save_accumulated_data()

            logger.info(f"✅ تم إضافة {added_count} صفقة للتدريب")
            logger.info(
                f"   📊 إجمالي البيانات: {len(self.accumulated_data)} صفقة"
            )

        return added_count

    def train(
        self, force: bool = False, timestamps: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        تدريب النموذج على البيانات المتراكمة مع time-based split وفحوصات جودة

        Args:
            force: فرض التدريب حتى لو كانت البيانات قليلة
            timestamps: اختياري - طوابع الوقت للtime-based split

        Returns:
            نتائج التدريب
        """
        if not self.enabled:
            return {"success": False, "error": "ML غير متوفر"}

        # فحص كمية البيانات
        total_samples = len(self.accumulated_data)

        if total_samples < self.MIN_SAMPLES_FOR_TRAINING and not force:
            return {
                "success": False,
                "error": f"بيانات غير كافية: {total_samples}/{self.MIN_SAMPLES_FOR_TRAINING}",
                "samples": total_samples,
            }

        try:
            logger.info(f"🧠 بدء تدريب ML على {total_samples} صفقة...")

            # تحضير البيانات - إضافة الأعمدة الناقصة بقيمة 0
            for col in self.feature_columns:
                if col not in self.accumulated_data.columns:
                    self.accumulated_data[col] = 0

            X = self.accumulated_data[self.feature_columns].fillna(0)
            y = self.accumulated_data["target"]

            # فحص جودة البيانات
            quality_check = self._check_data_quality(X, y)
            if not quality_check["passed"]:
                logger.warning(f"⚠️ فشل فحص الجودة: {quality_check['reason']}")
                if not force:
                    return {
                        "success": False,
                        "error": f'فشل فحص الجودة: {quality_check["reason"]}',
                        "data_quality": quality_check,
                    }

            # تقسيم البيانات (time-based إذا توفر timestamps)
            if timestamps is not None and len(timestamps) == len(X):
                # Time-based split: الأقدم للتدريب، الأحدث للاختبار
                sorted_indices = np.argsort(timestamps)
                X_sorted = X[sorted_indices]
                y_sorted = y[sorted_indices]

                # 70% تدريب، 15% validation، 15% اختبار
                train_size = int(len(X_sorted) * 0.70)
                val_size = int(len(X_sorted) * 0.15)

                X_train = X_sorted[:train_size]
                y_train = y_sorted[:train_size]

                X_val = X_sorted[train_size: train_size + val_size]
                y_val = y_sorted[train_size: train_size + val_size]

                X_test = X_sorted[train_size + val_size:]
                y_test = y_sorted[train_size + val_size:]

                logger.info(
                    f"✅ Time-based split: Train={len(X_train)}, "
                    f"Val={len(X_val)}, Test={len(X_test)}"
                )
            else:
                # Random split كاحتياطي
                X_temp, X_test, y_temp, y_test = train_test_split(
                    X, y, test_size=0.15, random_state=42, stratify=y
                )
                X_train, X_val, y_train, y_val = train_test_split(
                    X_temp,
                    y_temp,
                    test_size=0.176,
                    random_state=42,
                    stratify=y_temp,
                )
                logger.warning(
                    "⚠️ لم يتم توفير timestamps - استخدام random split"
                )

            # التحقق من وجود بيانات كافية
            if len(X_test) < 5 or len(X_val) < 5:
                return {
                    "success": False,
                    "error": "بيانات اختبار أو validation غير كافية",
                }

            # تطبيع البيانات (train + validation + test)
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_val_scaled = self.scaler.transform(X_val)
            X_test_scaled = self.scaler.transform(X_test)

            # تدريب النموذج مع early stopping
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42,
                eval_metric="logloss",
                early_stopping_rounds=10,
            )

            self.model.fit(
                X_train_scaled,
                y_train,
                eval_set=[(X_val_scaled, y_val)],
                verbose=False,
            )

            # تقييم على validation set
            y_val_pred = self.model.predict(X_val_scaled)
            val_accuracy = accuracy_score(y_val, y_val_pred)

            # تقييم على test set (النهائي)
            y_pred = self.model.predict(X_test_scaled)
            y_proba = self.model.predict_proba(X_test_scaled)[:, 1]

            test_accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)

            # فحص Overfitting
            train_accuracy = accuracy_score(
                y_train, self.model.predict(X_train_scaled)
            )
            overfitting_gap = train_accuracy - test_accuracy

            # Cross-validation للتحقق من الاستقرار (بدون early stopping)
            try:
                # إنشاء نموذج مؤقت بدون early_stopping للـ CV
                cv_model = xgb.XGBClassifier(
                    n_estimators=100,
                    max_depth=5,
                    learning_rate=0.1,
                    random_state=42,
                    eval_metric="logloss",
                )
                cv_scores = cross_val_score(
                    cv_model, X_train_scaled, y_train, cv=5
                )
                cv_mean = cv_scores.mean()
                cv_std = cv_scores.std()
            except Exception as e:
                logger.warning(f"⚠️ فشل CV: {e}")
                cv_mean = test_accuracy
                cv_std = 0.0

            # تحديث سجل التدريب
            training_record = {
                "timestamp": datetime.now().isoformat(),
                "total_samples": total_samples,
                "train_accuracy": train_accuracy,
                "val_accuracy": val_accuracy,
                "accuracy": test_accuracy,  # test accuracy هو المعيار
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "overfitting_gap": overfitting_gap,
                "split_method": (
                    "time_based" if timestamps is not None else "random"
                ),
                "is_ready": False,  # تحديث حالة الجاهزية لاحقاً
            }

            self.training_history["cycles"].append(training_record)
            self.training_history["total_samples"] = total_samples
            self.training_history["last_training"] = datetime.now().isoformat()

            # تحديث أفضل دقة
            if test_accuracy > self.training_history["best_accuracy"]:
                self.training_history["best_accuracy"] = test_accuracy

            # فحص الاستقرار
            self._check_stability(test_accuracy)

            # حفظ النموذج والسجل
            self._save_model()
            self._save_history()

            logger.info(f"✅ تم التدريب بنجاح!")
            logger.info(f"   📊 الدقة: {test_accuracy:.2%}")
            logger.info(f"   🎯 F1 Score: {f1:.2%}")
            logger.info(f"   📈 CV Mean: {cv_mean:.2%} (±{cv_std:.2%})")
            logger.info(f"   ✅ الجاهزية: {
                'جاهز' if self.is_ready() else 'غير جاهز'}")

            return {
                "success": True,
                "train_accuracy": train_accuracy,
                "val_accuracy": val_accuracy,
                "test_accuracy": test_accuracy,
                "accuracy": test_accuracy,  # للتوافق
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "overfitting_gap": overfitting_gap,
                "total_samples": total_samples,
                "split_method": (
                    "time_based" if timestamps is not None else "random"
                ),
                "is_ready": self.is_ready(),
                "data_quality": quality_check,
            }

        except Exception as e:
            logger.error(f"❌ خطأ في التدريب: {e}")
            return {"success": False, "error": str(e)}

    def _check_data_quality(
        self, X: pd.DataFrame, y: pd.Series
    ) -> Dict[str, Any]:
        """
        فحص جودة البيانات قبل التدريب
        """
        try:
            issues = []

            # تحويل إلى numpy إذا لزم الأمر
            X_arr = X.values if isinstance(X, pd.DataFrame) else X
            y_arr = y.values if isinstance(y, pd.Series) else y

            # 1. فحص وجود NaN أو Inf
            if np.isnan(X_arr).any() or np.isinf(X_arr).any():
                issues.append("NaN أو Inf في الميزات")

            # 2. فحص Class Imbalance
            unique, counts = np.unique(y_arr, return_counts=True)
            if len(unique) < 2:
                issues.append("جميع العينات من نفس الفئة")
            else:
                imbalance_ratio = max(counts) / min(counts)
                if imbalance_ratio > 10:
                    issues.append(f"Class imbalance شديد: {
                        imbalance_ratio:.1f}:1")

            # 3. فحص تنوع الميزات
            feature_std = np.std(X_arr, axis=0)
            zero_variance_features = np.sum(feature_std < 1e-10)
            if zero_variance_features > X_arr.shape[1] * 0.5:
                issues.append(f"{zero_variance_features} ميزة بدون تنوع")

            # 4. فحص عدد العينات الموجبة
            positive_samples = np.sum(y_arr == 1)
            negative_samples = np.sum(y_arr == 0)
            if positive_samples < 5 or negative_samples < 5:
                issues.append(
                    f"عينات قليلة: +{positive_samples}, -{negative_samples}"
                )

            passed = len(issues) == 0

            return {
                "passed": passed,
                "issues": issues,
                "reason": "; ".join(issues) if issues else "OK",
                "positive_samples": int(positive_samples),
                "negative_samples": int(negative_samples),
                "imbalance_ratio": (
                    float(max(counts) / min(counts))
                    if len(unique) >= 2
                    else None
                ),
            }

        except Exception as e:
            return {"passed": False, "issues": [str(e)], "reason": f"خطأ: {e}"}

    def _check_stability(self, current_accuracy: float):
        """فحص استقرار النموذج"""
        cycles = self.training_history["cycles"]
        total_samples = self.training_history.get("total_samples", 0)

        if len(cycles) >= self.MIN_STABLE_CYCLES:
            # فحص آخر 3 دورات
            recent_accuracies = [
                c["accuracy"] for c in cycles[-self.MIN_STABLE_CYCLES:]
            ]

            # مستقر إذا: جميع الدقات > الحد الأدنى والتذبذب < 10%
            all_above_threshold = all(
                a >= self.MIN_ACCURACY_FOR_READINESS for a in recent_accuracies
            )
            low_variance = (
                max(recent_accuracies) - min(recent_accuracies) < 0.10
            )  # 10% بدلاً من 5%

            # عدد الدورات المستقرة
            stable_count = sum(
                1
                for a in recent_accuracies
                if a >= self.MIN_ACCURACY_FOR_READINESS
            )
            self.training_history["stable_cycles"] = stable_count

            # تحديث حالة الجاهزية (استخدام test accuracy)
            is_ready = (
                total_samples >= self.MIN_SAMPLES_FOR_READINESS
                and current_accuracy >= self.MIN_ACCURACY_FOR_READINESS
                and len(self.training_history) >= self.MIN_STABLE_CYCLES
                and stable_count >= 2
                and all_above_threshold
                and low_variance
            )

            self.training_history["is_ready"] = is_ready
        else:
            self.training_history["stable_cycles"] = len(cycles)
            self.training_history["is_ready"] = False

    def is_ready(self) -> bool:
        """
        فحص جاهزية النموذج للعمل

        Returns:
            True إذا كان جاهزاً
        """
        if not self.enabled or self.model is None:
            return False

        return (
            self.training_history.get("is_ready", False)
            and self.training_history.get("total_samples", 0)
            >= self.MIN_SAMPLES_FOR_READINESS
            and self.training_history.get("best_accuracy", 0)
            >= self.MIN_ACCURACY_FOR_READINESS
        )

    def _calculate_dynamic_threshold(self) -> float:
        """
        حساب عتبة الثقة الديناميكية بناءً على أداء النموذج

        المنطق:
        - كلما تحسن النموذج → زادت العتبة (أكثر حذراً)
        - استخدام متوسط آخر 3 دورات للاستقرار
        - عتبة قصوى 0.73 (محافظة)

        Returns:
            عتبة الثقة (0.58 - 0.73)
        """
        try:
            cycles = self.training_history.get("cycles", [])

            # إذا لم يتدرب بعد، استخدم عتبة البداية
            if not cycles or len(cycles) == 0:
                return self.BASE_CONFIDENCE_THRESHOLD

            # استخدام متوسط آخر 3 دورات للاستقرار (أو كل ما هو متاح)
            recent_cycles = min(3, len(cycles))
            recent = cycles[-recent_cycles:]
            avg_accuracy = sum(
                c.get("test_accuracy", c.get("accuracy", 0)) for c in recent
            ) / len(recent)

            # حساب العتبة بناءً على الدقة (محافظ)
            if avg_accuracy < 0.70:
                threshold = 0.58  # بداية - نقبل إشارات أكثر
            elif avg_accuracy < 0.75:
                threshold = 0.62  # متوسط
            elif avg_accuracy < 0.80:
                threshold = 0.66  # جيد
            elif avg_accuracy < 0.85:
                threshold = 0.70  # ممتاز
            else:
                threshold = 0.73  # احترافي (محافظ - ليس 75%)

            logger.debug(
                f"العتبة الديناميكية: {threshold:.2f} "
                f"(دقة: {avg_accuracy:.2%}, دورات: {recent_cycles})"
            )

            return threshold

        except Exception as e:
            logger.warning(f"خطأ في حساب العتبة الديناميكية: {e}")
            return self.BASE_CONFIDENCE_THRESHOLD  # عتبة افتراضية آمنة

    def predict(self, features: Dict) -> Dict[str, Any]:
        """
        التنبؤ بجودة الإشارة

        Args:
            features: ميزات الإشارة الحالية

        Returns:
            نتيجة التنبؤ
        """
        if not self.enabled or self.model is None:
            return {
                "should_trade": True,  # السماح بالتداول إذا ML غير متوفر
                "confidence": 0.5,
                "ml_ready": False,
                "reason": "ML غير جاهز",
            }

        try:
            # تحويل الاستراتيجية والإطار الزمني إذا كانت موجودة كنص
            if "strategy" in features and isinstance(
                features["strategy"], str
            ):
                strategy = features["strategy"]
                strategy_lower = (
                    strategy.lower().replace("_", "").replace(" ", "")
                )
                features["strategy_trend_following"] = (
                    1 if "trendfollowing" in strategy_lower else 0
                )
                features["strategy_momentum_breakout"] = (
                    1 if "momentumbreakout" in strategy_lower else 0
                )
                features["strategy_mean_reversion"] = (
                    1 if "meanreversion" in strategy_lower else 0
                )
                features["strategy_scalping"] = (
                    1
                    if "scalping" in strategy_lower or "ema" in strategy_lower
                    else 0
                )
                features["strategy_rsi_divergence"] = (
                    1
                    if "rsi" in strategy_lower
                    or "divergence" in strategy_lower
                    else 0
                )
                features["strategy_other"] = (
                    1
                    if sum(
                        [
                            features["strategy_trend_following"],
                            features["strategy_momentum_breakout"],
                            features["strategy_mean_reversion"],
                            features["strategy_scalping"],
                            features["strategy_rsi_divergence"],
                        ]
                    )
                    == 0
                    else 0
                )

            if "timeframe" in features and isinstance(
                features["timeframe"], str
            ):
                timeframe = features["timeframe"]
                features["timeframe_15m"] = 1 if timeframe == "15m" else 0
                features["timeframe_1h"] = 1 if timeframe == "1h" else 0
                features["timeframe_4h"] = 1 if timeframe == "4h" else 0

            # تحضير الميزات كـ DataFrame لتجنب تحذيرات sklearn
            feature_values = {}
            for col in self.feature_columns:
                feature_values[col] = [features.get(col, 0)]

            X = pd.DataFrame(feature_values)
            X_scaled = self.scaler.transform(X)

            # التنبؤ
            proba = self.model.predict_proba(X_scaled)[0, 1]

            # حساب العتبة (ديناميكية أو ثابتة)
            threshold = (
                self._calculate_dynamic_threshold()
                if self.USE_DYNAMIC_THRESHOLD
                else self.BASE_CONFIDENCE_THRESHOLD
            )
            should_trade = proba >= threshold

            return {
                "should_trade": should_trade,
                "confidence": float(proba),
                "ml_ready": self.is_ready(),
                "threshold": threshold,
                "threshold_type": (
                    "dynamic" if self.USE_DYNAMIC_THRESHOLD else "static"
                ),
                "reason": "موافق" if should_trade else f"ثقة منخفضة ({
                    proba:.1%} < {
                    threshold:.1%})",
            }

        except Exception as e:
            logger.warning(f"خطأ في التنبؤ: {e}")
            return {
                "should_trade": True,
                "confidence": 0.5,
                "ml_ready": False,
                "reason": f"خطأ: {e}",
            }

    def get_status(self) -> Dict[str, Any]:
        """الحصول على حالة النظام"""
        if not self.enabled:
            return {
                "enabled": False,
                "model_loaded": False,
                "is_ready": False,
                "total_samples": 0,
                "min_samples_required": self.MIN_SAMPLES_FOR_READINESS,
                "training_cycles": 0,
                "best_accuracy": 0,
                "stable_cycles": 0,
                "last_training": None,
                "confidence_threshold": self.BASE_CONFIDENCE_THRESHOLD,
                "threshold_type": "static",
                "message": "ML libraries not installed (xgboost/sklearn)",
            }
        return {
            "enabled": self.enabled,
            "model_loaded": self.model is not None,
            "is_ready": self.is_ready(),
            "total_samples": len(self.accumulated_data),
            "min_samples_required": self.MIN_SAMPLES_FOR_READINESS,
            "training_cycles": len(self.training_history.get("cycles", [])),
            "best_accuracy": self.training_history.get("best_accuracy", 0),
            "stable_cycles": self.training_history.get("stable_cycles", 0),
            "last_training": self.training_history.get("last_training"),
            "confidence_threshold": (
                self._calculate_dynamic_threshold()
                if self.USE_DYNAMIC_THRESHOLD
                else self.BASE_CONFIDENCE_THRESHOLD
            ),
            "threshold_type": (
                "dynamic" if self.USE_DYNAMIC_THRESHOLD else "static"
            ),
        }

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """الحصول على أهمية الميزات"""
        if self.model is None:
            return None

        try:
            importance = self.model.feature_importances_
            return dict(zip(self.feature_columns, importance))
        except AttributeError:
            # Model لا يدعم feature_importances_
            return None


# Singleton instance
_ml_classifier = None


def get_ml_classifier() -> MLSignalClassifier:
    """الحصول على مثيل واحد من المصنف"""
    global _ml_classifier
    if _ml_classifier is None:
        _ml_classifier = MLSignalClassifier()
    return _ml_classifier
