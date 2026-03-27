#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
استراتيجية كسر الزخم (Momentum Breakout Strategy)
تركز على كسر المستويات مع تأكيد الزخم والحجم

المنطق:
1. كسر أعلى/أقل مستوى في فترة محددة
2. تأكيد بزيادة الحجم
3. تأكيد بقوة الزخم (RSI)
4. دخول سريع مع إدارة مخاطر واضحة
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import logging

from backend.strategies.strategy_base import StrategyBase

logger = logging.getLogger(__name__)


class MomentumBreakoutStrategy(StrategyBase):
    """استراتيجية كسر الزخم - بسيطة وفعالة"""

    def __init__(self, **params):
        """تهيئة الاستراتيجية"""
        self.name = "MomentumBreakoutStrategy"
        self.description = "استراتيجية كسر المستويات مع تأكيد الزخم"

        # معلمات محسّنة للدقة العالية
        self.default_params = {
            "breakout_period": 20,  # فترة أطول لكسر حقيقي (كان 10)
            "volume_multiplier": 1.5,  # حجم أعلى للتأكيد (كان 1.1)
            "rsi_period": 14,  # فترة RSI قياسية (كان 10)
            "rsi_breakout_min": 55,  # RSI أعلى للكسر الصاعد (كان 45)
            "rsi_breakout_max": 45,  # RSI أقل للكسر الهابط (كان 55)
            "atr_period": 14,  # فترة ATR قياسية (كان 10)
            "stop_loss_atr": 1.5,  # وقف خسارة
            "take_profit_atr": 3.0,  # هدف ربح أعلى (كان 2.5)
            "min_breakout_strength": 0.5,  # قوة كسر أعلى (كان 0.2)
            "adx_min": 25,  # جديد: قوة اتجاه مطلوبة
        }

        self.params = {**self.default_params, **params}
        super().__init__(**self.params)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """حساب المؤشرات الأساسية"""
        try:
            # 1. مستويات الكسر
            df["resistance"] = (
                df["high"].rolling(self.params["breakout_period"]).max()
            )
            df["support"] = (
                df["low"].rolling(self.params["breakout_period"]).min()
            )

            # 2. متوسط الحجم
            df["volume_ma"] = df["volume"].rolling(10).mean()
            df["volume_ratio"] = df["volume"] / df["volume_ma"]

            # 3. مؤشر RSI
            df["rsi"] = ta.rsi(df["close"], length=self.params["rsi_period"])

            # 4. مؤشر ADX لقوة الاتجاه
            adx = ta.adx(df["high"], df["low"], df["close"], length=14)
            df["adx"] = (
                adx["ADX_14"] if "ADX_14" in adx.columns else adx.iloc[:, 0]
            )

            # 5. مؤشر ATR
            df["atr"] = ta.atr(
                df["high"],
                df["low"],
                df["close"],
                length=self.params["atr_period"],
            )

            # 5. قوة الكسر
            df["breakout_strength"] = np.nan
            for i in range(1, len(df)):
                if df["close"].iloc[i] > df["resistance"].iloc[i - 1]:
                    strength = (
                        (df["close"].iloc[i] - df["resistance"].iloc[i - 1])
                        / df["resistance"].iloc[i - 1]
                    ) * 100
                    df.loc[df.index[i], "breakout_strength"] = strength
                elif df["close"].iloc[i] < df["support"].iloc[i - 1]:
                    strength = (
                        (df["support"].iloc[i - 1] - df["close"].iloc[i])
                        / df["support"].iloc[i - 1]
                    ) * 100
                    df.loc[df.index[i], "breakout_strength"] = strength

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

            for i in range(self.params["breakout_period"], len(df)):
                # شروط الكسر الصاعد - أكثر صرامة
                adx_ok = (
                    df["adx"].iloc[i] >= self.params.get("adx_min", 25)
                    if "adx" in df.columns
                    else True
                )
                bullish_breakout = (
                    # كسر المقاومة
                    df["close"].iloc[i] > df["resistance"].iloc[i - 1]
                    and
                    # حجم مرتفع
                    df["volume_ratio"].iloc[i]
                    >= self.params["volume_multiplier"]
                    and
                    # زخم إيجابي
                    df["rsi"].iloc[i] >= self.params["rsi_breakout_min"]
                    and
                    # قوة كسر كافية
                    df["breakout_strength"].iloc[i]
                    >= self.params["min_breakout_strength"]
                    and adx_ok  # اتجاه قوي
                )

                if bullish_breakout:
                    df.loc[df.index[i], "buy_signal"] = 1
                    # حساب وقف الخسارة وهدف الربح
                    current_price = df["close"].iloc[i]
                    atr_value = df["atr"].iloc[i]
                    df.loc[df.index[i], "stop_loss"] = current_price - (
                        self.params["stop_loss_atr"] * atr_value
                    )
                    df.loc[df.index[i], "take_profit"] = current_price + (
                        self.params["take_profit_atr"] * atr_value
                    )

                # شروط الكسر الهابط - أكثر صرامة
                bearish_breakout = (
                    df["close"].iloc[i]
                    < df["support"].iloc[i - 1]  # كسر الدعم
                    and
                    # حجم مرتفع
                    df["volume_ratio"].iloc[i]
                    >= self.params["volume_multiplier"]
                    and
                    # زخم سلبي
                    df["rsi"].iloc[i] <= self.params["rsi_breakout_max"]
                    and
                    # قوة كسر كافية
                    df["breakout_strength"].iloc[i]
                    >= self.params["min_breakout_strength"]
                    and adx_ok  # اتجاه قوي
                )

                if bearish_breakout:
                    df.loc[df.index[i], "sell_signal"] = 1
                    # حساب وقف الخسارة وهدف الربح
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
