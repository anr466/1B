#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
استراتيجية سكالبينج EMA (EMA Scalping Strategy)
تركز على التقاطعات السريعة للمتوسطات المتحركة الأسية

المنطق:
1. تقاطع EMA سريع مع EMA بطيء
2. تأكيد بالاتجاه العام (EMA أطول)
3. فلتر الحجم للتأكيد
4. دخول وخروج سريع
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import logging

from backend.strategies.strategy_base import StrategyBase

logger = logging.getLogger(__name__)


class ScalpingEMAStrategy(StrategyBase):
    """استراتيجية سكالبينج المتوسطات المتحركة الأسية"""

    def __init__(self, **params):
        """تهيئة الاستراتيجية"""
        self.name = "ScalpingEMAStrategy"
        self.description = "استراتيجية سكالبينج بتقاطع EMA السريع"

        # معلمات محسّنة - أكثر صرامة
        self.default_params = {
            "ema_fast": 8,  # EMA سريع (كان 5)
            "ema_slow": 21,  # EMA بطيء (كان 13)
            "ema_trend": 50,  # EMA الاتجاه العام
            "volume_multiplier": 1.3,  # حجم أعلى (كان 1.1)
            "atr_period": 14,  # فترة ATR (كان 10)
            "stop_loss_atr": 1.2,  # وقف خسارة (كان 1.0)
            "take_profit_atr": 2.5,  # هدف ربح أعلى (كان 2.0)
            "trend_filter": True,  # فلتر الاتجاه العام
            "volume_filter": True,  # فلتر الحجم
            "rsi_filter": True,  # جديد: فلتر RSI
            "rsi_max": 60,  # جديد: لا يشتري إذا RSI عالي
        }

        self.params = {**self.default_params, **params}
        super().__init__(**self.params)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """حساب المؤشرات الأساسية"""
        try:
            # 1. المتوسطات المتحركة الأسية
            df["ema_fast"] = ta.ema(
                df["close"], length=self.params["ema_fast"]
            )
            df["ema_slow"] = ta.ema(
                df["close"], length=self.params["ema_slow"]
            )

            if self.params["trend_filter"]:
                df["ema_trend"] = ta.ema(
                    df["close"], length=self.params["ema_trend"]
                )

            # 2. مؤشر ATR
            df["atr"] = ta.atr(
                df["high"],
                df["low"],
                df["close"],
                length=self.params["atr_period"],
            )

            # 3. متوسط الحجم
            if self.params["volume_filter"]:
                df["volume_ma"] = df["volume"].rolling(20).mean()
                df["volume_ratio"] = df["volume"] / df["volume_ma"]

            # 4. تحديد التقاطعات
            df["ema_cross_up"] = (df["ema_fast"] > df["ema_slow"]) & (
                df["ema_fast"].shift(1) <= df["ema_slow"].shift(1)
            )
            df["ema_cross_down"] = (df["ema_fast"] < df["ema_slow"]) & (
                df["ema_fast"].shift(1) >= df["ema_slow"].shift(1)
            )

            # 5. RSI للفلترة
            if self.params.get("rsi_filter", True):
                delta = df["close"].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                df["rsi"] = 100 - (100 / (1 + gain / (loss + 0.0001)))

            return df

        except Exception as e:
            logger.error(f"خطأ في حساب المؤشرات: {str(e)}")
            return df

    def generate_signals(self, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """توليد إشارات التداول"""
        try:
            df = df.copy()
            df = self.calculate_indicators(df)

            # تهيئة أعمدة الإشارات
            df["buy_signal"] = 0
            df["sell_signal"] = 0
            df["stop_loss"] = np.nan
            df["take_profit"] = np.nan

            for i in range(max(self.params["ema_trend"], 20), len(df)):
                # شروط الشراء
                buy_conditions = []

                # 1. تقاطع صاعد
                buy_conditions.append(df["ema_cross_up"].iloc[i])

                # 2. فلتر الاتجاه العام
                if self.params["trend_filter"]:
                    trend_up = df["close"].iloc[i] > df["ema_trend"].iloc[i]
                    buy_conditions.append(trend_up)

                # 3. فلتر الحجم
                if self.params["volume_filter"]:
                    volume_ok = (
                        df["volume_ratio"].iloc[i]
                        >= self.params["volume_multiplier"]
                    )
                    buy_conditions.append(volume_ok)

                # 4. فلتر RSI - جديد
                if self.params.get("rsi_filter", True) and "rsi" in df.columns:
                    rsi_ok = df["rsi"].iloc[i] < self.params.get("rsi_max", 60)
                    buy_conditions.append(rsi_ok)

                # تنفيذ إشارة الشراء - يجب تحقق جميع الشروط
                if all(buy_conditions):  # كل الشروط بدل len-1
                    df.loc[df.index[i], "buy_signal"] = 1
                    current_price = df["close"].iloc[i]
                    atr_value = df["atr"].iloc[i]
                    df.loc[df.index[i], "stop_loss"] = current_price - (
                        self.params["stop_loss_atr"] * atr_value
                    )
                    df.loc[df.index[i], "take_profit"] = current_price + (
                        self.params["take_profit_atr"] * atr_value
                    )

                # شروط البيع
                sell_conditions = []

                # 1. تقاطع هابط
                sell_conditions.append(df["ema_cross_down"].iloc[i])

                # 2. فلتر الاتجاه العام
                if self.params["trend_filter"]:
                    trend_down = df["close"].iloc[i] < df["ema_trend"].iloc[i]
                    sell_conditions.append(trend_down)

                # 3. فلتر الحجم
                if self.params["volume_filter"]:
                    volume_ok = (
                        df["volume_ratio"].iloc[i]
                        >= self.params["volume_multiplier"]
                    )
                    sell_conditions.append(volume_ok)

                # تنفيذ إشارة البيع
                if all(sell_conditions):
                    df.loc[df.index[i], "sell_signal"] = 1
                    current_price = df["close"].iloc[i]
                    atr_value = df["atr"].iloc[i]
                    df.loc[df.index[i], "stop_loss"] = current_price + (
                        self.params["stop_loss_atr"] * atr_value
                    )
                    df.loc[df.index[i], "take_profit"] = current_price - (
                        self.params["take_profit_atr"] * atr_value
                    )

            return df

        except Exception as e:
            logger.error(f"خطأ في توليد الإشارات: {str(e)}")
            return df
