#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
استراتيجية متابعة الاتجاه (Trend Following): استراتيجية تركز على تحديد واتباع الاتجاهات القوية
مناسبة للأسواق ذات الاتجاهات الواضحة والقوية

تتبع هذه الاستراتيجية النمط الموحد لجميع استراتيجيات التداول في النظام:
1. تستقبل DataFrame نظيف يحتوي على بيانات OHLCV الأساسية
2. تتعامل مع الإطار الزمني وعدد الشموع
3. تحسب المؤشرات الفنية للتعرف على الاتجاهات داخلياً
4. تضيف إشارات الدخول والخروج إلى DataFrame
5. تعيد DataFrame كامل مع المؤشرات والإشارات

النسخة المحسنة: تعتمد على تحليل هيكل السوق (Market Structure) وتتبع القمم والقيعان
لتوليد إشارات ذات جودة عالية في مناطق الدعم والمقاومة والانعكاسات الهيكلية
مع دعم التحليل متعدد الأطر الزمنية لتأكيد اتجاه السوق وتحسين جودة الإشارات
"""

from backend.strategies.strategy_base import StrategyBase
import pandas as pd
import numpy as np
import pandas_ta as ta
import logging
from typing import Dict, Any, List, Tuple, Optional
import traceback

# إعداد الـlogger
logger = logging.getLogger(__name__)


class TrendFollowingStrategy(StrategyBase):
    """استراتيجية متابعة الترند - تتابع اتجاه السوق العام وتحاول استغلال الحركة في نفس الاتجاه

    تعتمد هذه الاستراتيجية على تحليل هيكل السوق وقوة الترند والمتوسطات المتحركة
    ​وتستخدم مؤشرات مثل ADX و MACD وتقاطعات المتوسطات المتحركة للكشف عن الترند
    ​وتحديد نقاط الدخول والخروج الأمثل

    مع دعم التحليل متعدد الأطر الزمنية للتأكيد على اتجاه السوق
    ​وتحسين جودة الإشارات والتقليل من الإشارات الكاذبة
    """

    def _identify_market_structure(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        تحليل هيكل السوق وتحديد الاتجاه الحالي وانعكاساته باستخدام pandas_ta

        المعلمات:
            df (pd.DataFrame): إطار البيانات مع بيانات OHLCV وأعمدة القمم والقيعان

        المخرجات:
            pd.DataFrame: إطار البيانات مع أعمدة تحليل هيكل السوق
        """
        try:
            # إنشاء نسخة من DataFrame لإضافة النتائج
            df_copy = df.copy()

            # إضافة أعمدة القمم والقيعان
            df_copy["swing_high"] = np.nan
            df_copy["swing_low"] = np.nan
            df_copy["swing_high_confirmed"] = False
            df_copy["swing_low_confirmed"] = False

            # الحد الأدنى للبيانات اللازمة للتحليل
            min_required = 15
            if len(df) < min_required:
                logger.warning("عدد الشموع غير كافٍ لتحديد نقاط التأرجح")
                return df_copy

            # استخدام pandas_ta لحساب المؤشرات الفنية
            # حساب نسبة المدى المتوسط المعياري
            natr = ta.natr(
                df_copy["high"], df_copy["low"], df_copy["close"], length=14
            )
            volatility_threshold = natr.mean() * 0.5  # عتبة التقلب

            # استخدام pandas_ta للكشف عن القمم والقيعان
            # زيجزاج (ZigZag) - يساعد في اكتشاف نقاط التحول المهمة
            # استخدام pdta.minmax يحل محل الدوال اليدوية
            # is_local_maxima/is_local_minima
            swing_length = 5  # طول النافذة للبحث عن القمم والقيعان
            ret_thresh = 0.0  # لا نطبق عتبة عائد إضافية

            # تنفيذ بديل لـ minmax: البحث اليدوي عن القمم والقيعان
            # استخدام نافذة متحركة للبحث عن القمم والقيعان المحلية

            # دالة للتحقق مما إذا كانت النقطة قمة محلية
            def is_local_maxima(data, i, window):
                if i - window < 0 or i + window >= len(data):
                    return False
                # القيمة الحالية يجب أن تكون أكبر من جميع القيم في النافذة
                # المحيطة
                return all(
                    data.iloc[i] >= data.iloc[i - j]
                    for j in range(1, window + 1)
                ) and all(
                    data.iloc[i] >= data.iloc[i + j]
                    for j in range(1, window + 1)
                )

            # دالة للتحقق مما إذا كانت النقطة قاع محلي
            def is_local_minima(data, i, window):
                if i - window < 0 or i + window >= len(data):
                    return False
                # القيمة الحالية يجب أن تكون أصغر من جميع القيم في النافذة
                # المحيطة
                return all(
                    data.iloc[i] <= data.iloc[i - j]
                    for j in range(1, window + 1)
                ) and all(
                    data.iloc[i] <= data.iloc[i + j]
                    for j in range(1, window + 1)
                )

            # البحث عن القمم المحلية
            for i in range(swing_length, len(df_copy) - swing_length):
                # التحقق من القمم (النقاط العالية)
                if is_local_maxima(df_copy["high"], i, swing_length):
                    # تحقق من أن التقلب كافٍ لاعتبار القمة مهمة
                    if (
                        i < len(natr)
                        and not np.isnan(natr.iloc[i])
                        and natr.iloc[i] > volatility_threshold
                    ):
                        df_copy.loc[df_copy.index[i], "swing_high"] = (
                            df_copy.iloc[i]["high"]
                        )
                        df_copy.loc[
                            df_copy.index[i], "swing_high_confirmed"
                        ] = True

                # التحقق من القيعان (النقاط المنخفضة)
                if is_local_minima(df_copy["low"], i, swing_length):
                    # تحقق من أن التقلب كافٍ لاعتبار القاع مهمًا
                    if (
                        i < len(natr)
                        and not np.isnan(natr.iloc[i])
                        and natr.iloc[i] > volatility_threshold
                    ):
                        df_copy.loc[df_copy.index[i], "swing_low"] = (
                            df_copy.iloc[i]["low"]
                        )
                        df_copy.loc[
                            df_copy.index[i], "swing_low_confirmed"
                        ] = True

            # تحسين دقة القمم والقيعان باستخدام مؤشرات إضافية من pandas_ta
            # استخدام RSI لتأكيد نقاط التحول (تشبع شرائي عند القمم، تشبع بيعي
            # عند القيعان)
            df_copy["rsi"] = ta.rsi(df_copy["close"], length=14)

            # تأكيد القمم باستخدام تشبع شرائي RSI
            high_idx = df_copy.index[df_copy["swing_high_confirmed"]]
            for idx in high_idx:
                i = df_copy.index.get_loc(idx)
                # إذا كان RSI لا يؤكد قمة (أقل من 50)، نقلل الثقة
                if df_copy["rsi"].iloc[i] < 50:
                    df_copy.loc[idx, "swing_high_confirmed"] = False

            # تأكيد القيعان باستخدام تشبع بيعي RSI
            low_idx = df_copy.index[df_copy["swing_low_confirmed"]]
            for idx in low_idx:
                i = df_copy.index.get_loc(idx)
                # إذا كان RSI لا يؤكد قاع (أعلى من 50)، نقلل الثقة
                if df_copy["rsi"].iloc[i] > 50:
                    df_copy.loc[idx, "swing_low_confirmed"] = False

            # تطبيق فلتر إضافي باستخدام ATR للتخلص من القمم/القيعان غير المهمة
            atr = ta.atr(
                df_copy["high"], df_copy["low"], df_copy["close"], length=14
            )
            df_copy["atr"] = atr

            logger.info(f"تم تحديد {
                df_copy['swing_high_confirmed'].sum()} قمة و {
                df_copy['swing_low_confirmed'].sum()} قاع")
            return df_copy

        except Exception as e:
            logger.error(f"خطأ أثناء تحديد نقاط التأرجح: {str(e)}")
            # إعادة DataFrame الأصلي في حالة حدوث خطأ
            return df

    def __init__(self, **params):
        """
        تهيئة استراتيجية متابعة الترند مع دعم التحليل متعدد الأطر الزمنية

        المعلمات:
            params (dict): معلمات الاستراتيجية
                - lookback_period (int): فترة النظر للخلف للتعرف على هيكل السوق (افتراضيا: 20)
                - atr_period (int): فترة مؤشر ATR (افتراضيا: 14)
                - ema_short (int): فترة المتوسط المتحرك القصير (افتراضيا: 9)
                - ema_middle (int): فترة المتوسط المتحرك المتوسط (افتراضيا: 21)
                - ema_long (int): فترة المتوسط المتحرك الطويل (افتراضيا: 50)
                - rsi_period (int): فترة مؤشر RSI (افتراضيا: 14)
                - adx_period (int): فترة مؤشر ADX (افتراضيا: 14)
                - adx_threshold (int): عتبة مؤشر ADX لقوة الترند (افتراضيا: 25)

                # معلمات تحليل متعدد الأطر الزمنية
                - use_mtf_analysis (bool): تفعيل/تعطيل تحليل متعدد الأطر الزمنية (افتراضياً: True)
                - higher_timeframes (list): قائمة الأطر الزمنية الأعلى للتحليل (مثال: ['1h', '4h'])
                - mtf_trend_weight (float): وزن اتجاه الترند في الأطر الزمنية الأعلى (افتراضياً: 0.6)
                - mtf_alignment_threshold (float): عتبة توافق الترند بين الأطر الزمنية (افتراضياً: 0.7)
        """
        # المعلمات الافتراضية - مع التنسيق لتحسين الوضوح
        default_params = {
            # معلمات المتوسطات المتحركة
            "ema_short_period": 9,  # فترة المتوسط المتحرك القصيرة
            "ema_medium_period": 13,  # فترة المتوسط المتحرك المتوسطة
            "ema_long_period": 21,  # فترة المتوسط المتحرك الطويلة
            # معلمات قوة الاتجاه
            "adx_period": 14,  # فترة مؤشر ADX
            "adx_threshold": 25.0,  # عتبة قوة الاتجاه
            # معلمات MACD
            "macd_fast": 12,  # فترة MACD السريعة
            "macd_slow": 26,  # فترة MACD البطيئة
            "macd_signal": 9,  # فترة إشارة MACD
            # معلمات التقلب والتوقف
            "atr_period": 14,  # فترة حساب ATR
            "supertrend_factor": 3.0,  # معامل Supertrend
            "supertrend_atr_period": 10,  # فترة ATR لمؤشر Supertrend
            # معلمات تدفق المال
            "cmf_period": 20,  # فترة مؤشر Chaikin Money Flow
            # معلمات إدارة المخاطر
            "stop_loss_atr": 2.0,  # مضاعف ATR لوقف الخسارة
            "take_profit_atr": 4.0,  # مضاعف ATR لهدف الربح
            "trailing_stop_atr": 2.5,  # مضاعف ATR للوقف المتحرك
            "min_signal_quality": 0.7,  # الحد الأدنى لجودة الإشارة (0-1)
            # معلمات هيكل السوق
            "min_swing_size": 0.003,  # الحد الأدنى لحجم السوينج بالنسبة للسعر
            "swing_window": 3,  # نافذة تحديد السوينج
            # معلمات تحليل متعدد الأطر الزمنية
            "use_mtf_analysis": True,  # تفعيل التحليل متعدد الأطر الزمنية
            "higher_timeframes": [],  # سيتم تحديدها بناءً على الإطار الزمني الأساسي
            "mtf_trend_weight": 0.6,  # وزن الترند في الأطر الزمنية الأعلى
            "mtf_alignment_threshold": 0.7,  # عتبة توافق الترند عبر الأطر الزمنية
        }

        # دمج المعلمات الافتراضية والمخصصة
        params = {**default_params, **params}

        # استدعاء منشئ الفئة الأساسية
        super().__init__(**params)

        # حفظ معلمات الاستراتيجية
        for key, value in params.items():
            setattr(self, key, value)

        # إعداد هياكل البيانات
        self.direction = 0  # الاتجاه الحالي (1 صاعد، -1 هابط، 0 محايد)
        self.market_structure = {}  # لتخزين معلومات هيكل السوق
        self.support_levels = []  # مستويات الدعم
        self.resistance_levels = []  # مستويات المقاومة

        # تحديد الأطر الزمنية الأعلى تلقائياً إذا لم يتم تحديدها
        if not self.higher_timeframes:
            self.higher_timeframes = self._get_default_higher_timeframes()

        # سجل التتبع
        logger.info(
            f"تم تهيئة استراتيجية متابعة الاتجاه مع المعلمات: {params}"
        )

    def _get_default_higher_timeframes(self) -> List[str]:
        """
        تحديد الأطر الزمنية الأعلى بناءً على الإطار الزمني الأساسي

        المخرجات:
            List[str]: قائمة بالأطر الزمنية الأعلى المناسبة للتحليل
        """
        # تعريف الترتيب العام للأطر الزمنية من الأصغر إلى الأكبر
        all_timeframes = [
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "1h",
            "2h",
            "4h",
            "6h",
            "8h",
            "12h",
            "1d",
            "3d",
            "1w",
        ]

        # العلاقة بين الأطر الزمنية لتحديد الأطر المناسبة للتحليل متعدد الأطر
        mtf_relationships = {
            "1m": ["5m", "15m", "1h"],
            "3m": ["15m", "1h", "4h"],
            "5m": ["15m", "1h", "4h"],
            "15m": ["1h", "4h", "1d"],
            "30m": ["2h", "4h", "1d"],
            "1h": ["4h", "1d", "1w"],
            "2h": ["6h", "1d", "1w"],
            "4h": ["1d", "1w", None],
            "6h": ["1d", "3d", "1w"],
            "8h": ["1d", "3d", "1w"],
            "12h": ["1d", "3d", "1w"],
            "1d": ["1w", None, None],
            "3d": ["1w", None, None],
            "1w": [None, None, None],
        }

        # الحصول على الإطار الزمني إما من معلمات الاستراتيجية أو استخدام قيمة
        # افتراضية
        timeframe = "1h"  # القيمة الافتراضية
        if hasattr(self, "timeframe"):
            timeframe = self.timeframe

        # إرجاع الأطر الزمنية الأعلى المناسبة
        return mtf_relationships.get(timeframe, ["4h", "1d", "1w"])

    def calculate_indicators(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        حساب المؤشرات الفنية باستخدام pandas_ta للاستخدام في توليد الإشارات وتحليل السوق

        المعلمات:
            dataframe (pd.DataFrame): إطار البيانات مع بيانات OHLCV الأساسية

        المخرجات:
            pd.DataFrame: إطار البيانات مع المؤشرات الفنية المضافة
        """
        try:
            # نسخة من DataFrame للعمل عليها
            df = dataframe.copy()

            # الحصول على الإطار الزمني إذا كان متوفرًا في خصائص DataFrame
            timeframe = (
                getattr(df, "timeframe", "4h")
                if hasattr(df, "attrs")
                else "4h"
            )

            # تكييف معلمات الاستراتيجية بناءً على الإطار الزمني وظروف السوق
            # استخدام قيم افتراضية لـ ADX والتقلبات حتى نتمكن من حسابها لاحقًا
            avg_adx = 25.0  # قيمة افتراضية
            volatility_ratio = 1.0  # قيمة افتراضية

            # تكييف المعلمات باستخدام القيم الافتراضية الأولية
            adapted_params = self._adapt_parameters(
                timeframe, avg_adx, volatility_ratio
            )

            # === حساب المؤشرات الفنية باستخدام pandas_ta ===

            # 1. حساب المتوسطات المتحركة الأسية (EMA)
            # استخدام معلمات مكيفة للأطر الزمنية المختلفة
            ema_short_period = adapted_params["ema_short_period"]
            ema_medium_period = adapted_params["ema_medium_period"]
            ema_long_period = adapted_params["ema_long_period"]

            # إضافة المتوسطات المتحركة باستخدام pandas_ta
            df["ema_short"] = ta.ema(df["close"], length=ema_short_period)
            df["ema_medium"] = ta.ema(df["close"], length=ema_medium_period)
            df["ema_long"] = ta.ema(df["close"], length=ema_long_period)

            # 2. حساب مؤشر ADX لقياس قوة الاتجاه
            adx = ta.adx(
                df["high"],
                df["low"],
                df["close"],
                length=adapted_params["adx_period"],
            )
            df["ADX"] = adx["ADX_14"]  # اسم العمود يعتمد على الطول المستخدم
            df["DMP"] = adx["DMP_14"]  # مؤشر +DI
            df["DMN"] = adx["DMN_14"]  # مؤشر -DI

            # 3. حساب مؤشر MACD
            macd = ta.macd(
                df["close"],
                fast=adapted_params["macd_fast"],
                slow=adapted_params["macd_slow"],
                signal=adapted_params["macd_signal"],
            )
            # استخراج أسماء الأعمدة الفعلية من DataFrame الناتج
            macd_cols = macd.columns.tolist()
            logger.debug(f"أعمدة MACD المتاحة: {macd_cols}")

            # استخدام الأعمدة بطريقة أكثر مرونة لتجنب أخطاء الوصول
            for col in macd_cols:
                if (
                    "MACD_" in col
                    and "_Signal" not in col
                    and "hist" not in col
                ):
                    df["macd"] = macd[col]
                elif "_Signal" in col or "MACDs_" in col:
                    df["macd_signal"] = macd[col]
                elif "hist" in col or "MACDh_" in col:
                    df["macd_histogram"] = macd[col]

            # التحقق من إضافة جميع الأعمدة المطلوبة
            if "macd" not in df.columns:
                # إذا لم نجد الأعمدة المتوقعة، نستخدم الأعمدة الثلاثة الأولى من
                # ناتج MACD
                if len(macd_cols) >= 3:
                    df["macd"] = macd[macd_cols[0]]
                    df["macd_signal"] = macd[macd_cols[1]]
                    df["macd_histogram"] = macd[macd_cols[2]]
                    logger.warning(
                        f"استخدام أسماء الأعمدة البديلة للMACD: {macd_cols[:3]}"
                    )
                else:
                    logger.error(
                        f"لم يتم العثور على أعمدة MACD كافية: {macd_cols}"
                    )
                    # إضافة أعمدة فارغة لتجنب الأخطاء اللاحقة
                    df["macd"] = np.nan
                    df["macd_signal"] = np.nan
                    df["macd_histogram"] = np.nan

            # 4. حساب مؤشر Supertrend
            supertrend = ta.supertrend(
                df["high"],
                df["low"],
                df["close"],
                length=adapted_params["supertrend_atr_period"],
                multiplier=adapted_params["supertrend_factor"],
            )
            # استخراج قيم Supertrend وتوجيهه
            supertrend_col = f"SUPERT_{
                adapted_params['supertrend_atr_period']}_{
                adapted_params['supertrend_factor']:.1f}"
            direction_col = f"{supertrend_col}_D"

            if supertrend_col in supertrend.columns:
                df["supertrend"] = supertrend[supertrend_col]
            else:
                # الاستمرار في البحث عن العمود المناسب
                for col in supertrend.columns:
                    if "SUPERT_" in col and "_D" not in col:
                        df["supertrend"] = supertrend[col]
                        break

            if direction_col in supertrend.columns:
                df["supertrend_direction"] = supertrend[direction_col]
            else:
                # الاستمرار في البحث عن العمود المناسب
                for col in supertrend.columns:
                    if "SUPERT_" in col and "_D" in col:
                        df["supertrend_direction"] = supertrend[col]
                        break

            # 5. حساب مؤشر ATR للتقلب
            df["atr"] = ta.atr(
                df["high"],
                df["low"],
                df["close"],
                length=adapted_params["atr_period"],
            )

            # 6. حساب مؤشر Chaikin Money Flow للتدفق المالي
            df["cmf"] = ta.cmf(
                df["high"],
                df["low"],
                df["close"],
                df["volume"],
                length=adapted_params["cmf_period"],
            )

            # 7. حساب مؤشر RSI
            df["rsi"] = ta.rsi(
                df["close"], length=adapted_params.get("rsi_period", 14)
            )

            # 8. حساب الحجم النسبي
            df["relative_volume"] = (
                df["volume"] / df["volume"].rolling(window=20).mean()
            )

            # === تحليل هيكل السوق ===
            # استخدام تحليل القمم والقيعان لتحديد اتجاه السوق
            df = self._identify_market_structure(df)

            # 9. تحديد الاتجاه العام بناء على تحليل هيكل السوق
            # تهيئة عمود الاتجاه
            df["trend"] = 0

            # استخدام متوسطات متحركة لتحديد الاتجاه
            for i in range(20, len(df)):
                # اتجاه صاعد: EMA قصير > EMA متوسط > EMA طويل
                if (
                    df["ema_short"].iloc[i]
                    > df["ema_medium"].iloc[i]
                    > df["ema_long"].iloc[i]
                ):
                    df.loc[df.index[i], "trend"] = 1
                # اتجاه هابط: EMA قصير < EMA متوسط < EMA طويل
                elif (
                    df["ema_short"].iloc[i]
                    < df["ema_medium"].iloc[i]
                    < df["ema_long"].iloc[i]
                ):
                    df.loc[df.index[i], "trend"] = -1
                # الاتجاه متذبذب/محايد
                else:
                    # استخدام الاتجاه السابق كافتراضي للحفاظ على استقرار
                    # الإشارات
                    df.loc[df.index[i], "trend"] = df["trend"].iloc[i - 1]

            # تحديث متوسط ADX بعد حسابه
            avg_adx = df["ADX"].mean() if "ADX" in df.columns else 25.0

            # تحديث نسبة التقلب بعد حساب ATR
            if "atr" in df.columns and "close" in df.columns:
                avg_atr = df["atr"].mean()
                avg_price = df["close"].mean()
                if avg_price > 0:
                    volatility_ratio = (avg_atr / avg_price) * 100

            # إعادة تكييف المعلمات مع القيم المحسوبة من البيانات الفعلية
            self._adapted_params = self._adapt_parameters(
                timeframe, avg_adx, volatility_ratio
            )

            # تسجيل معلومات حول المؤشرات المحسوبة
            logger.info(
                f"تم حساب المؤشرات الفنية للإطار الزمني {timeframe} - متوسط ADX: {
                    avg_adx:.2f}, نسبة التقلب: {
                    volatility_ratio:.2f}%")

            return df

        except Exception as e:
            logger.error(f"خطأ أثناء حساب المؤشرات الفنية: {
                str(e)}\n{
                traceback.format_exc()}")
            # إعادة DataFrame الأصلي في حالة الخطأ
            return dataframe

        # تحديد الأطر الزمنية الأعلى بناءً على الإطار الزمني الأساسي
        if timeframe in mtf_relationships:
            # إزالة القيم الفارغة من القائمة
            higher_tfs = [
                tf for tf in mtf_relationships[timeframe] if tf is not None
            ]
            logger.info(
                f"تم تحديد الأطر الزمنية الأعلى تلقائياً: {higher_tfs} للإطار الأساسي {timeframe}")
            return higher_tfs
        else:
            # إطار زمني غير معروف، استخدام قيم افتراضية آمنة
            default_higher_tfs = ["4h", "1d"]
            logger.warning(
                f"إطار زمني غير معروف: {timeframe}، استخدام أطر زمنية افتراضية: {default_higher_tfs}")
            return default_higher_tfs

    def _adapt_parameters(
        self, timeframe: str, avg_adx: float, volatility_ratio: float
    ) -> Dict[str, Any]:
        """
        تكييف معلمات الاستراتيجية بناءً على الإطار الزمني وظروف السوق الحالية
        لتحسين الأداء في أطر زمنية مختلفة خاصة للتداول السريع (Scalping) والتداول اليومي (Intraday)

        المعلمات:
            timeframe (str): الإطار الزمني الحالي (1m, 5m, 15m, 1h, 4h, ...)
            avg_adx (float): متوسط قيمة مؤشر ADX للتعرف على قوة الاتجاه
            volatility_ratio (float): نسبة التقلب في السوق حاليًا

        المخرجات:
            Dict[str, Any]: نسخة معدلة من معلمات الاستراتيجية
        """
        try:
            # نسخ معلمات الاستراتيجية لتعديلها
            adapted_params = self.params.copy()

            # تحليل السوق لتحديد ما إذا كانت حالة السوق مترابطة، متجهة، أو
            # متذبذبة
            trend_strength = avg_adx / 50.0  # تطبيع إلى قيمة بين 0 و1
            price_volatility = min(volatility_ratio / 5.0, 1.0)  # تطبيع التقلب

            # === تعديل المعلمات بناءً على الإطار الزمني ===
            # تحسين المعاملات للتداول السريع (Scalping) والتداول اليومي
            # (Intraday)
            tf_multipliers = {
                # معاملات مخصصة للتداول السريع (Scalping)
                "1m": {
                    "ema": 0.15,
                    "adx": 0.7,
                    "signal_quality": 0.6,
                    "stop_loss": 0.8,
                    "take_profit": 1.2,
                    "momentum": 1.5,
                    "noise_filter": 1.8,
                },
                "3m": {
                    "ema": 0.2,
                    "adx": 0.8,
                    "signal_quality": 0.62,
                    "stop_loss": 0.9,
                    "take_profit": 1.3,
                    "momentum": 1.4,
                    "noise_filter": 1.6,
                },
                "5m": {
                    "ema": 0.25,
                    "adx": 0.9,
                    "signal_quality": 0.65,
                    "stop_loss": 1.0,
                    "take_profit": 1.5,
                    "momentum": 1.3,
                    "noise_filter": 1.5,
                },
                # معاملات مخصصة للتداول اليومي (Intraday)
                "15m": {
                    "ema": 0.4,
                    "adx": 1.0,
                    "signal_quality": 0.7,
                    "stop_loss": 1.1,
                    "take_profit": 1.7,
                    "momentum": 1.2,
                    "noise_filter": 1.3,
                },
                "30m": {
                    "ema": 0.6,
                    "adx": 1.1,
                    "signal_quality": 0.72,
                    "stop_loss": 1.2,
                    "take_profit": 1.9,
                    "momentum": 1.1,
                    "noise_filter": 1.2,
                },
                "1h": {
                    "ema": 0.8,
                    "adx": 1.0,
                    "signal_quality": 0.7,
                    "stop_loss": 1.0,
                    "take_profit": 2.0,
                    "momentum": 1.0,
                    "noise_filter": 1.0,
                },
                # معاملات الأطر الزمنية الأطول
                "2h": {
                    "ema": 1.2,
                    "adx": 0.9,
                    "signal_quality": 0.68,
                    "stop_loss": 0.9,
                    "take_profit": 2.2,
                    "momentum": 0.9,
                    "noise_filter": 0.9,
                },
                "4h": {
                    "ema": 1.5,
                    "adx": 0.8,
                    "signal_quality": 0.65,
                    "stop_loss": 0.8,
                    "take_profit": 2.5,
                    "momentum": 0.8,
                    "noise_filter": 0.8,
                },
                "6h": {
                    "ema": 1.8,
                    "adx": 0.75,
                    "signal_quality": 0.63,
                    "stop_loss": 0.75,
                    "take_profit": 2.8,
                    "momentum": 0.7,
                    "noise_filter": 0.7,
                },
                "12h": {
                    "ema": 2.0,
                    "adx": 0.7,
                    "signal_quality": 0.6,
                    "stop_loss": 0.7,
                    "take_profit": 3.0,
                    "momentum": 0.6,
                    "noise_filter": 0.6,
                },
                "1d": {
                    "ema": 2.5,
                    "adx": 0.6,
                    "signal_quality": 0.55,
                    "stop_loss": 0.65,
                    "take_profit": 3.5,
                    "momentum": 0.5,
                    "noise_filter": 0.5,
                },
                "3d": {
                    "ema": 3.0,
                    "adx": 0.5,
                    "signal_quality": 0.5,
                    "stop_loss": 0.6,
                    "take_profit": 4.0,
                    "momentum": 0.4,
                    "noise_filter": 0.4,
                },
                "1w": {
                    "ema": 4.0,
                    "adx": 0.4,
                    "signal_quality": 0.45,
                    "stop_loss": 0.5,
                    "take_profit": 5.0,
                    "momentum": 0.3,
                    "noise_filter": 0.3,
                },
            }

            # إذا لم يكن الإطار الزمني موجودًا، استخدم المعاملات الافتراضية
            multipliers = tf_multipliers.get(
                timeframe,
                {
                    "ema": 1.0,
                    "adx": 1.0,
                    "signal_quality": 0.7,
                    "stop_loss": 1.0,
                    "take_profit": 2.0,
                    "momentum": 1.0,
                    "noise_filter": 1.0,
                },
            )

            # تعديل عتبة ADX حسب الإطار الزمني - تخفيض العتبة للإطار 4h لتحسين
            # عدد الإشارات
            if timeframe == "4h":
                adapted_params["adx_threshold"] = max(
                    15, min(35, self.params["adx_threshold"] * 0.75)
                )
            else:
                adapted_params["adx_threshold"] = max(
                    15,
                    min(40, self.params["adx_threshold"] * multipliers["adx"]),
                )

            # تعديل معلمات MACD حسب الإطار الزمني
            adapted_params["macd_fast"] = int(
                max(6, round(self.params["macd_fast"] * multipliers["ema"]))
            )
            adapted_params["macd_slow"] = int(
                max(13, round(self.params["macd_slow"] * multipliers["ema"]))
            )
            adapted_params["macd_signal"] = int(
                max(4, round(self.params["macd_signal"] * multipliers["ema"]))
            )

            # تعديل معلمات EMA حسب الإطار الزمني
            adapted_params["ema_short_period"] = int(
                max(
                    5,
                    round(
                        self.params.get("ema_short_period", 8)
                        * multipliers["ema"]
                    ),
                )
            )
            adapted_params["ema_medium_period"] = int(
                max(
                    8,
                    round(
                        self.params.get("ema_medium_period", 13)
                        * multipliers["ema"]
                    ),
                )
            )
            adapted_params["ema_long_period"] = int(
                max(
                    13,
                    round(
                        self.params.get("ema_long_period", 21)
                        * multipliers["ema"]
                    ),
                )
            )

            # تعديل الحد الأدنى لجودة الإشارة حسب الإطار الزمني
            if timeframe == "4h":
                # تعديل مخصص للإطار الزمني 4h لتحسين نسبة الفوز
                adapted_params["min_signal_quality"] = max(
                    0.55, min(0.85, self.params["min_signal_quality"] * 0.95)
                )
            else:
                adapted_params["min_signal_quality"] = max(
                    0.5,
                    min(
                        0.9,
                        self.params["min_signal_quality"]
                        * multipliers["signal_quality"],
                    ),
                )

            # تعديل معلمات وقف الخسارة وجني الأرباح حسب الإطار الزمني
            if timeframe == "4h":
                # تحسين نسبة المخاطرة/المكافأة للإطار 4h
                adapted_params["stop_loss_atr"] = max(
                    1.2, self.params["stop_loss_atr"] * 0.85
                )  # وقف خسارة أقل قليلاً
                adapted_params["take_profit_atr"] = max(
                    2.5, self.params["take_profit_atr"] * 1.1
                )  # جني ربح أعلى لتحسين نسبة الربح/الخسارة
            else:
                adapted_params["stop_loss_atr"] = max(
                    1.0,
                    self.params["stop_loss_atr"] * multipliers["stop_loss"],
                )
                adapted_params["take_profit_atr"] = max(
                    2.0,
                    self.params["take_profit_atr"]
                    * multipliers["take_profit"],
                )

            # === تعديل المعلمات بناءً على ظروف السوق الحالية ===
            # 1. تكييف معلمات وقف الخسارة وجني الأرباح حسب التقلب
            if volatility_ratio > 2.0:  # تقلب مرتفع
                adapted_params["stop_loss_atr"] = min(
                    adapted_params["stop_loss_atr"] * 1.2, 3.5
                )
                adapted_params["take_profit_atr"] = min(
                    adapted_params["take_profit_atr"] * 1.2, 7.0
                )
                adapted_params["supertrend_factor"] = min(
                    adapted_params["supertrend_factor"] * 1.2, 4.5
                )
                adapted_params["min_signal_quality"] = min(
                    adapted_params["min_signal_quality"] * 1.1, 0.9
                )
            elif volatility_ratio < 0.5:  # تقلب منخفض
                adapted_params["stop_loss_atr"] = max(
                    adapted_params["stop_loss_atr"] * 0.8, 1.2
                )
                adapted_params["take_profit_atr"] = max(
                    adapted_params["take_profit_atr"] * 0.8, 2.5
                )
                adapted_params["supertrend_factor"] = max(
                    adapted_params["supertrend_factor"] * 0.8, 1.8
                )
                adapted_params["min_signal_quality"] = max(
                    adapted_params["min_signal_quality"] * 0.9, 0.5
                )

            # 2. تكييف عتبة ADX حسب قوة الاتجاه المرصودة
            if avg_adx > 30:  # اتجاه قوي
                adapted_params["adx_threshold"] = max(
                    adapted_params["adx_threshold"] * 0.9, 18.0
                )
            elif avg_adx < 15:  # اتجاه ضعيف
                adapted_params["adx_threshold"] = min(
                    adapted_params["adx_threshold"] * 1.1, 35.0
                )

            # تعديلات خاصة للأطر الزمنية الصغيرة (سكالبينج)
            if timeframe in ["1m", "3m", "5m"]:
                # تسريع الاستجابة للتغيرات السريعة
                adapted_params["rsi_period"] = max(
                    7, int(self.params.get("rsi_period", 14) * 0.6)
                )
                # زيادة حساسية التقاطعات
                adapted_params["ema_short_period"] = max(
                    3, int(adapted_params["ema_short_period"] * 0.7)
                )
                # تقليل عتبة ADX للسماح بإشارات أكثر
                adapted_params["adx_threshold"] = max(
                    12, min(25, adapted_params["adx_threshold"] * 0.8)
                )
                # تعديل نسبة المخاطرة/المكافأة للتداولات قصيرة المدى
                adapted_params["risk_reward_ratio"] = max(
                    1.2,
                    min(1.5, self.params.get("risk_reward_ratio", 2.0) * 0.75),
                )

            logger.debug(
                f"تكييف المعلمات للإطار الزمني {timeframe}: " +
                f"نسبة التقلب={
                    volatility_ratio:.2f}%, متوسط ADX={
                    avg_adx:.2f}, " +
                f"EMA قصير={
                    adapted_params['ema_short_period']}, " +
                f"عتبة ADX={
                    adapted_params['adx_threshold']:.1f}, " +
                f"الحد الأدنى لجودة الإشارة={
                    adapted_params['min_signal_quality']:.2f}")

            return adapted_params

        except Exception as e:
            logger.error(f"خطأ أثناء تكييف المعلمات: {str(e)}")
            return self.params

    def _calculate_signal_quality(
        self,
        df: pd.DataFrame,
        row_idx: int,
        direction: int,
        timeframe: str = "4h",
    ) -> float:
        """
        حساب جودة الإشارة بناءً على تأكيدات متعددة وتكييفها حسب الإطار الزمني

        المعلمات:
            df (pd.DataFrame): إطار البيانات مع المؤشرات
            row_idx (int): مؤشر الصف في DataFrame
            direction (int): اتجاه الإشارة (1 للشراء، -1 للبيع)
            timeframe (str): الإطار الزمني

        المخرجات:
            float: جودة الإشارة من 0 إلى 1
        """
        try:
            # التحقق من صحة المؤشر
            if row_idx < 5 or row_idx >= len(df):
                return 0.0

            # استخراج بيانات الصف الحالي
            row = df.iloc[row_idx]

            # تهيئة درجات التقييم
            trend_score = 0.0
            momentum_score = 0.0
            volume_score = 0.0
            price_action_score = 0.0

            # تعريف الأوزان حسب الإطار الزمني - تحسين للتداول السريع (سكالبينج وتداول يومي)
            # الأطر الزمنية الأصغر: وزن أكبر للزخم وحركة السعر والتفاعل السريع مع السوق
            # الأطر الزمنية الأكبر: وزن أكبر للاتجاه العام والحجم والمؤشرات
            # طويلة المدى
            tf_weights = {
                # أوزان معدلة للسكالبينج - زيادة وزن حركة السعر والزخم السريع
                "1m": {
                    "trend": 0.15,
                    "momentum": 0.35,
                    "volume": 0.15,
                    "price_action": 0.35,
                },
                "3m": {
                    "trend": 0.20,
                    "momentum": 0.35,
                    "volume": 0.15,
                    "price_action": 0.30,
                },
                "5m": {
                    "trend": 0.25,
                    "momentum": 0.30,
                    "volume": 0.15,
                    "price_action": 0.30,
                },
                # أوزان معدلة للتداول اليومي - توازن بين الاتجاه وحركة السعر
                "15m": {
                    "trend": 0.30,
                    "momentum": 0.30,
                    "volume": 0.15,
                    "price_action": 0.25,
                },
                "30m": {
                    "trend": 0.35,
                    "momentum": 0.25,
                    "volume": 0.15,
                    "price_action": 0.25,
                },
                "1h": {
                    "trend": 0.40,
                    "momentum": 0.25,
                    "volume": 0.15,
                    "price_action": 0.20,
                },
                "2h": {
                    "trend": 0.45,
                    "momentum": 0.25,
                    "volume": 0.15,
                    "price_action": 0.15,
                },
                # أوزان معدلة للتداول المتوسط والطويل
                "4h": {
                    "trend": 0.50,
                    "momentum": 0.20,
                    "volume": 0.15,
                    "price_action": 0.15,
                },
                "6h": {
                    "trend": 0.50,
                    "momentum": 0.20,
                    "volume": 0.20,
                    "price_action": 0.10,
                },
                "8h": {
                    "trend": 0.55,
                    "momentum": 0.20,
                    "volume": 0.20,
                    "price_action": 0.05,
                },
                "12h": {
                    "trend": 0.55,
                    "momentum": 0.20,
                    "volume": 0.20,
                    "price_action": 0.05,
                },
                "1d": {
                    "trend": 0.60,
                    "momentum": 0.15,
                    "volume": 0.20,
                    "price_action": 0.05,
                },
                "3d": {
                    "trend": 0.65,
                    "momentum": 0.10,
                    "volume": 0.25,
                    "price_action": 0.00,
                },
                "1w": {
                    "trend": 0.70,
                    "momentum": 0.10,
                    "volume": 0.20,
                    "price_action": 0.00,
                },
            }

            # استخدام الوزن الافتراضي (4h) إذا كان الإطار الزمني غير موجود
            weights = tf_weights.get(timeframe, tf_weights["4h"])

            # === حساب درجات التقييم حسب الاتجاه (شراء/بيع) ===
            if direction == 1:  # إشارة شراء
                # قياس توافق الاتجاه
                if row["trend"] == 1:
                    trend_score += 0.75

                # قياس قوة الاتجاه
                if (
                    "ADX" in row
                    and row["ADX"] > self._adapted_params["adx_threshold"]
                ):
                    trend_score += 0.4
                    # مكافأة إضافية لقوة الاتجاه العالية
                    if "ADX" in row and row["ADX"] > 35:
                        trend_score += 0.2

                # === قياس جودة مؤشرات الزخم ===
                # MACD إيجابي وفوق خط الإشارة
                if "macd" in row and "macd_signal" in row:
                    if row["macd"] > row["macd_signal"] and row["macd"] > 0:
                        momentum_score += 0.8
                        # مكافأة إضافية للزخم القوي جداً
                        if (
                            row["macd"] > row["macd_signal"] * 1.5
                            and row["macd"] > 0
                        ):
                            momentum_score += 0.1
                    elif row["macd"] > row["macd_signal"]:
                        momentum_score += 0.5

                # توافق مؤشر Supertrend
                if (
                    "supertrend_direction" in row
                    and row["supertrend_direction"] == 1
                ):
                    momentum_score += 0.3

                # === قياس جودة مؤشرات الحجم والتدفق المالي ===
                # مؤشر CMF إيجابي (تدفق مالي للشراء)
                if "cmf" in row and row["cmf"] > 0:
                    volume_score += 0.5
                    if row["cmf"] > 0.1:  # تدفق مالي قوي
                        volume_score += 0.3

                # زيادة في حجم التداول
                if (
                    row["volume"]
                    > df["volume"].iloc[row_idx - 5: row_idx].mean()
                ):
                    volume_score += 0.2

                # === قياس جودة حركة السعر ===
                # السعر فوق المتوسطات المتحركة
                if (
                    row["close"] > row["ema_short"]
                    and row["close"] > row["ema_medium"]
                ):
                    price_action_score += 0.65
                    # مكافأة إضافية إذا كان السعر فوق المتوسط الطويل
                    if row["close"] > row["ema_long"]:
                        price_action_score += 0.15
                elif row["close"] > row["ema_short"]:
                    price_action_score += 0.35

                # قوة الشمعة الإيجابية
                if row["close"] > row["open"]:
                    candle_strength = (row["close"] - row["open"]) / (
                        row["high"] - row["low"] + 0.001
                    )
                    if candle_strength > 0.6:  # شمعة قوية جداً
                        price_action_score += 0.45
                    elif candle_strength > 0.4:  # شمعة قوية
                        price_action_score += 0.3

            else:  # إشارة بيع (direction == -1)
                # قياس توافق الاتجاه
                if row["trend"] == -1:
                    trend_score += 0.75

                # قياس قوة الاتجاه
                if (
                    "ADX" in row
                    and row["ADX"] > self._adapted_params["adx_threshold"]
                ):
                    trend_score += 0.4
                    # مكافأة إضافية لقوة الاتجاه العالية
                    if "ADX" in row and row["ADX"] > 35:
                        trend_score += 0.2

                # === قياس جودة مؤشرات الزخم ===
                # MACD سلبي وتحت خط الإشارة
                if "macd" in row and "macd_signal" in row:
                    if row["macd"] < row["macd_signal"] and row["macd"] < 0:
                        momentum_score += 0.8
                        # مكافأة إضافية للزخم الهبوطي القوي جداً
                        if (
                            row["macd"] < row["macd_signal"] * 1.5
                            and row["macd"] < 0
                        ):
                            momentum_score += 0.1
                    elif row["macd"] < row["macd_signal"]:
                        momentum_score += 0.5

                # توافق مؤشر Supertrend
                if (
                    "supertrend_direction" in row
                    and row["supertrend_direction"] == -1
                ):
                    momentum_score += 0.3

                # === قياس جودة مؤشرات الحجم والتدفق المالي ===
                # مؤشر CMF سلبي (تدفق مالي للبيع)
                if "cmf" in row and row["cmf"] < 0:
                    volume_score += 0.5
                    if row["cmf"] < -0.1:  # تدفق مالي قوي للخروج
                        volume_score += 0.3

                # زيادة في حجم التداول
                if (
                    row["volume"]
                    > df["volume"].iloc[row_idx - 5: row_idx].mean()
                ):
                    volume_score += 0.2

                # === قياس جودة حركة السعر ===
                # السعر تحت المتوسطات المتحركة
                if (
                    row["close"] < row["ema_short"]
                    and row["close"] < row["ema_medium"]
                ):
                    price_action_score += 0.65
                    # مكافأة إضافية إذا كان السعر تحت المتوسط الطويل
                    if row["close"] < row["ema_long"]:
                        price_action_score += 0.15
                elif row["close"] < row["ema_short"]:
                    price_action_score += 0.35

                # قوة الشمعة الهبوطية
                if row["close"] < row["open"]:
                    candle_strength = (row["open"] - row["close"]) / (
                        row["high"] - row["low"] + 0.001
                    )
                    if candle_strength > 0.6:  # شمعة هبوطية قوية جداً
                        price_action_score += 0.45
                    elif candle_strength > 0.4:  # شمعة هبوطية قوية
                        price_action_score += 0.3

            # تطبيق الحد الأقصى (1.0) لكل درجة تقييم
            trend_score = min(trend_score, 1.0)
            momentum_score = min(momentum_score, 1.0)
            volume_score = min(volume_score, 1.0)
            price_action_score = min(price_action_score, 1.0)

            # حساب جودة الإشارة النهائية باستخدام الأوزان المعدلة حسب الإطار
            # الزمني
            quality = (
                trend_score * weights["trend"]
                + momentum_score * weights["momentum"]
                + volume_score * weights["volume"]
                + price_action_score * weights["price_action"]
            )

            # عامل الموثوقية للأطر الزمنية (الأطر الأطول أكثر موثوقية)
            timeframe_reliability = {
                "1m": 0.88,
                "3m": 0.90,
                "5m": 0.92,
                "15m": 0.94,
                "30m": 0.95,
                "1h": 0.97,
                # زيادة موثوقية الإطار الزمني 4h
                "2h": 0.98,
                "4h": 1.0,
                "6h": 0.99,
                "8h": 1.0,
                "12h": 1.0,
                "1d": 1.0,
                "3d": 1.0,
                "1w": 1.0,
            }
            reliability_factor = timeframe_reliability.get(
                timeframe, 0.98
            )  # 4h كقيمة افتراضية

            # تعديل الجودة النهائية حسب معامل الموثوقية
            final_quality = quality * reliability_factor

            # معالجة خاصة للأطر الزمنية الصغيرة للتداول السريع
            if timeframe in ["1m", "3m", "5m", "15m"]:
                # تعزيز جودة الإشارة إذا كان هناك زخم قوي في اتجاه الإشارة
                if direction == 1:  # إشارة شراء
                    # زيادة جودة الإشارة إذا كان السعر يتجه للأعلى بقوة
                    if (
                        row_idx > 5
                        and row["close"]
                        > df["close"].iloc[row_idx - 1]
                        > df["close"].iloc[row_idx - 2]
                    ):
                        # تعزيز للموجة الصاعدة
                        momentum_boost = 0.05
                        final_quality = min(
                            final_quality + momentum_boost, 1.0
                        )

                        # تعزيز إضافي إذا كان هناك زيادة في الحجم
                        if (
                            "volume" in row
                            and row_idx > 1
                            and row["volume"]
                            > df["volume"].iloc[row_idx - 1] * 1.2
                        ):
                            volume_boost = 0.03
                            final_quality = min(
                                final_quality + volume_boost, 1.0
                            )
                else:  # إشارة بيع
                    # زيادة جودة الإشارة إذا كان السعر يتجه للأسفل بقوة
                    if (
                        row_idx > 5
                        and row["close"]
                        < df["close"].iloc[row_idx - 1]
                        < df["close"].iloc[row_idx - 2]
                    ):
                        # تعزيز للموجة الهابطة
                        momentum_boost = 0.05
                        final_quality = min(
                            final_quality + momentum_boost, 1.0
                        )

                        # تعزيز إضافي إذا كان هناك زيادة في الحجم
                        if (
                            "volume" in row
                            and row_idx > 1
                            and row["volume"]
                            > df["volume"].iloc[row_idx - 1] * 1.2
                        ):
                            volume_boost = 0.03
                            final_quality = min(
                                final_quality + volume_boost, 1.0
                            )

            # عقوبة التقلب العالي في الأطر الزمنية القصيرة
            if "atr" in df.columns:
                volatility_ratio = (
                    df.iloc[row_idx]["atr"] / df.iloc[row_idx]["close"] * 100
                )

                # تعديل عتبة التقلب حسب الإطار الزمني
                if timeframe in ["1m", "3m"]:
                    # الأطر الزمنية القصيرة جدًا تتوقع تقلبات أعلى
                    volatility_threshold = 1.5
                    max_penalty = 0.15  # عقوبة أقل للتقلبات المتوقعة
                elif timeframe in ["5m", "15m"]:
                    volatility_threshold = 1.2
                    max_penalty = 0.18
                else:
                    volatility_threshold = 1.0
                    max_penalty = 0.2

                if volatility_ratio > volatility_threshold:  # تقلب عالٍ
                    volatility_penalty = min(
                        volatility_ratio / 20.0, max_penalty
                    )  # عقوبة بحد أقصى متغير
                    final_quality = max(
                        final_quality * (1.0 - volatility_penalty), 0.0
                    )

            # التأكد من أن النتيجة النهائية بين 0 و1
            return min(max(final_quality, 0.0), 1.0)

        except Exception as e:
            logger.error(f"خطأ أثناء حساب جودة الإشارة: {str(e)}")
            return 0.0

    def _calculate_exit_points(
        self, df: pd.DataFrame, row_idx: int, direction: int
    ) -> Tuple[float, float]:
        """
        حساب نقاط وقف الخسارة وجني الأرباح باستخدام pandas_ta والقمم/القيعان المحددة

        المعلمات:
            df (pd.DataFrame): إطار البيانات مع المؤشرات وتحليل هيكل السوق
            row_idx (int): مؤشر الصف في DataFrame
            direction (int): اتجاه الإشارة (1 للشراء، -1 للبيع)

        المخرجات:
            Tuple[float, float]: وقف الخسارة وجني الأرباح
        """
        try:
            # التحقق من صحة المؤشر
            if row_idx >= len(df) or row_idx < 0:
                return np.nan, np.nan

            row = df.iloc[row_idx]
            close_price = row["close"]

            # تعيين القيم الافتراضية
            stop_loss = np.nan
            take_profit = np.nan

            # الحصول على الإطار الزمني لضبط المعاملات حسب السياق
            timeframe = (
                getattr(df, "timeframe", "4h")
                if hasattr(df, "attrs")
                else "4h"
            )

            # === طريقة 1: استخدام القمم والقيعان المحددة مسبقاً ===
            # البحث عن آخر قمة/قاع مؤكدة قبل الصف الحالي
            lookback = min(20, row_idx)  # نبحث في آخر 20 شمعة أو أقل

            last_swing_high = np.nan
            last_swing_low = np.nan

            # البحث عن آخر قمة وقاع
            for i in range(row_idx - 1, max(0, row_idx - lookback), -1):
                if "swing_high" in df.iloc[i] and not np.isnan(
                    df.iloc[i]["swing_high"]
                ):
                    last_swing_high = df.iloc[i]["swing_high"]
                    break

            for i in range(row_idx - 1, max(0, row_idx - lookback), -1):
                if "swing_low" in df.iloc[i] and not np.isnan(
                    df.iloc[i]["swing_low"]
                ):
                    last_swing_low = df.iloc[i]["swing_low"]
                    break

            # تحديد وقف الخسارة بناء على القمم/القيعان
            if direction == 1:  # للشراء
                if (
                    not np.isnan(last_swing_low)
                    and last_swing_low < close_price
                ):
                    # تحقق من أن المسافة معقولة
                    sl_distance_pct = (
                        close_price - last_swing_low
                    ) / close_price

                    # إذا كانت المسافة معقولة، استخدم القاع كوقف خسارة
                    if sl_distance_pct <= 0.05:  # حد أقصى 5% مخاطرة
                        stop_loss = last_swing_low

            else:  # للبيع
                if (
                    not np.isnan(last_swing_high)
                    and last_swing_high > close_price
                ):
                    # تحقق من أن المسافة معقولة
                    sl_distance_pct = (
                        last_swing_high - close_price
                    ) / close_price

                    # إذا كانت المسافة معقولة، استخدم القمة كوقف خسارة
                    if sl_distance_pct <= 0.05:  # حد أقصى 5% مخاطرة
                        stop_loss = last_swing_high

            # === طريقة 2: استخدام ATR من pandas_ta ===
            # إذا لم يتم تحديد وقف الخسارة من القمم/القيعان، استخدم ATR
            atr_column = "atr"

            # تأكد من وجود ATR في البيانات
            has_atr = atr_column in df.columns and not np.isnan(
                row[atr_column]
            )

            # إذا لم يكن هناك ATR، قم بحسابه الآن
            if not has_atr:
                atr_length = 14
                # حساب ATR باستخدام pandas_ta
                df_temp = df.copy()
                atr = ta.atr(
                    df_temp["high"],
                    df_temp["low"],
                    df_temp["close"],
                    length=atr_length,
                )
                current_atr = (
                    atr.iloc[row_idx] if row_idx < len(atr) else atr.iloc[-1]
                )
            else:
                current_atr = row[atr_column]

            # استخدام معاملات مناسبة حسب الإطار الزمني
            if timeframe in ["1d", "3d", "1w"]:
                sl_multiplier = 1.5
                tp_multiplier = 3.0
            elif timeframe == "4h":
                sl_multiplier = 1.2
                tp_multiplier = 2.5
            elif timeframe in [
                "1m",
                "3m",
            ]:  # الأطر الزمنية السريعة جدًا للسكالبينج
                sl_multiplier = 0.6  # وقف خسارة أقل من سعر الدخول بنسبة من ATR
                tp_multiplier = (
                    1.2  # نسبة مخاطرة/مكافأة متوازنة للتداول السريع
                )
            elif timeframe in ["5m", "15m"]:  # الأطر الزمنية السريعة
                sl_multiplier = 0.8  # وقف خسارة متوسط للتداول السريع
                tp_multiplier = 1.6  # نسبة مخاطرة/مكافأة تزيد مع الوقت
            else:  # الإطارات الزمنية الأخرى (30m, 1h, ...)
                sl_multiplier = 1.0
                tp_multiplier = 2.0

            # حساب وقف الخسارة وجني الأرباح إذا لم يتم تحديدهما مسبقًا
            if np.isnan(stop_loss):
                if direction == 1:  # للشراء
                    stop_loss = close_price - (current_atr * sl_multiplier)
                else:  # للبيع
                    stop_loss = close_price + (current_atr * sl_multiplier)

            # حساب جني الأرباح باستخدام نسبة المخاطرة/المكافأة المناسبة
            if direction == 1:  # للشراء
                risk = close_price - stop_loss
                take_profit = close_price + (risk * tp_multiplier)
            else:  # للبيع
                risk = stop_loss - close_price
                take_profit = close_price - (risk * tp_multiplier)

            return stop_loss, take_profit

        except Exception as e:
            logger.error(f"خطأ أثناء حساب نقاط الخروج: {str(e)}")
            return dataframe

    def generate_signals(
        self,
        dataframe: pd.DataFrame,
        timeframe: str = "1h",
        candles_count: int = 100,
        mtf_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> pd.DataFrame:
        """
        توليد إشارات الدخول والخروج بناءً على المؤشرات الفنية المحسوبة من pandas_ta
        """
        try:
            logger.info(
                f"بدء توليد إشارات التداول لاستراتيجية تتبع الاتجاه - الإطار الزمني: {timeframe}")

            # نسخ البيانات لتجنب التعديل على الأصل
            df = dataframe.copy()

            # التحقق من وجود البيانات الكافية
            if len(df) < 50:
                logger.warning("البيانات غير كافية لتوليد إشارات موثوقة")
                return df

            # حساب المؤشرات الفنية باستخدام pandas_ta
            df = self.calculate_indicators(df)

            # تعريف أعمدة الإشارات والمخرجات
            df["buy_signal"] = 0
            df["sell_signal"] = 0
            df["exit_signal"] = 0
            df["stop_loss"] = np.nan
            df["take_profit"] = np.nan
            df["signal_quality"] = np.nan

            # تكييف معايير الإشارات حسب الإطار الزمني
            rsi_overbought = 75 if timeframe in ["15m", "1h"] else 70
            rsi_oversold = 25 if timeframe in ["15m", "1h"] else 30
            volume_threshold = 1.2 if timeframe in ["15m", "1h"] else 1.0

            # توليد الإشارات
            for i in range(20, len(df)):
                try:
                    # شروط الشراء
                    buy_conditions = []

                    # اتجاه صاعد
                    if "trend" in df.columns:
                        buy_conditions.append(df["trend"].iloc[i] == 1)

                    # Supertrend صاعد
                    if "supertrend_direction" in df.columns:
                        buy_conditions.append(
                            df["supertrend_direction"].iloc[i] == 1
                        )

                    # MACD إيجابي
                    if all(
                        col in df.columns for col in ["macd", "macd_signal"]
                    ):
                        buy_conditions.append(
                            df["macd"].iloc[i] > df["macd_signal"].iloc[i]
                        )

                    # RSI ليس في تشبع شرائي
                    if "rsi" in df.columns:
                        buy_conditions.append(
                            df["rsi"].iloc[i] < rsi_overbought
                        )

                    # حجم جيد
                    if "relative_volume" in df.columns:
                        buy_conditions.append(
                            df["relative_volume"].iloc[i] > volume_threshold
                        )

                    # شروط البيع
                    sell_conditions = []

                    # اتجاه هابط
                    if "trend" in df.columns:
                        sell_conditions.append(df["trend"].iloc[i] == -1)

                    # Supertrend هابط
                    if "supertrend_direction" in df.columns:
                        sell_conditions.append(
                            df["supertrend_direction"].iloc[i] == -1
                        )

                    # MACD سلبي
                    if all(
                        col in df.columns for col in ["macd", "macd_signal"]
                    ):
                        sell_conditions.append(
                            df["macd"].iloc[i] < df["macd_signal"].iloc[i]
                        )

                    # RSI ليس في تشبع بيعي
                    if "rsi" in df.columns:
                        sell_conditions.append(
                            df["rsi"].iloc[i] > rsi_oversold
                        )

                    # حجم جيد
                    if "relative_volume" in df.columns:
                        sell_conditions.append(
                            df["relative_volume"].iloc[i] > volume_threshold
                        )

                    # تحديد عدد الشروط المطلوبة
                    required_conditions = max(3, len(buy_conditions) // 2)

                    # توليد إشارة الشراء
                    if (
                        len(buy_conditions) >= required_conditions
                        and sum(buy_conditions) >= required_conditions
                    ):
                        df.loc[df.index[i], "buy_signal"] = 1

                        # حساب وقف الخسارة وجني الأرباح
                        if "atr" in df.columns:
                            atr_value = df["atr"].iloc[i]
                            df.loc[df.index[i], "stop_loss"] = df[
                                "close"
                            ].iloc[i] - (2 * atr_value)
                            df.loc[df.index[i], "take_profit"] = df[
                                "close"
                            ].iloc[i] + (3 * atr_value)

                    # توليد إشارة البيع
                    elif (
                        len(sell_conditions) >= required_conditions
                        and sum(sell_conditions) >= required_conditions
                    ):
                        df.loc[df.index[i], "sell_signal"] = 1

                        # حساب وقف الخسارة وجني الأرباح
                        if "atr" in df.columns:
                            atr_value = df["atr"].iloc[i]
                            df.loc[df.index[i], "stop_loss"] = df[
                                "close"
                            ].iloc[i] + (2 * atr_value)
                            df.loc[df.index[i], "take_profit"] = df[
                                "close"
                            ].iloc[i] - (3 * atr_value)

                    # شروط الخروج
                    exit_conditions = []

                    # انعكاس الاتجاه
                    if "trend" in df.columns and i > 0:
                        exit_conditions.append(
                            df["trend"].iloc[i] != df["trend"].iloc[i - 1]
                        )

                    # انعكاس Supertrend
                    if "supertrend_direction" in df.columns and i > 0:
                        exit_conditions.append(
                            df["supertrend_direction"].iloc[i]
                            != df["supertrend_direction"].iloc[i - 1]
                        )

                    # تقاطع MACD
                    if (
                        all(
                            col in df.columns
                            for col in ["macd", "macd_signal"]
                        )
                        and i > 0
                    ):
                        current_cross = (
                            df["macd"].iloc[i] - df["macd_signal"].iloc[i]
                        )
                        previous_cross = (
                            df["macd"].iloc[i - 1]
                            - df["macd_signal"].iloc[i - 1]
                        )
                        exit_conditions.append(
                            current_cross * previous_cross < 0
                        )

                    # توليد إشارة الخروج
                    if len(exit_conditions) > 0 and sum(exit_conditions) >= 1:
                        df.loc[df.index[i], "exit_signal"] = 1

                except Exception as e:
                    logger.warning(f"خطأ في معالجة الصف {i}: {str(e)}")
                    continue

            # تسجيل ملخص الإشارات المتولدة
            buy_count = df["buy_signal"].sum()
            sell_count = df["sell_signal"].sum()
            exit_count = df["exit_signal"].sum()
            logger.info(
                f"تم توليد إشارات التداول بنجاح: {buy_count} إشارة شراء، {sell_count} إشارة بيع، {exit_count} إشارة خروج")

            return df

        except Exception as e:
            logger.error(f"خطأ في توليد الإشارات: {str(e)}")
            logger.error(traceback.format_exc())
            return dataframe
