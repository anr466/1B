#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
استراتيجية سكالبنج القمم والقيعان المبسطة
تعتمد على RSI وBollinger Bands فقط
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
import logging
import traceback
from typing import Dict, Optional

from backend.strategies.strategy_base import StrategyBase

logger = logging.getLogger(__name__)


class PeakValleyScalpingStrategy(StrategyBase):
    """
    استراتيجية سكالبنج مبسطة تعتمد على RSI وBollinger Bands
    """

    def __init__(self, **params):
        """
        تهيئة استراتيجية سكالبنج مبسطة
        """
        self.name = "PeakValleyScalpingStrategy"
        self.description = "استراتيجية سكالبنج مبسطة"

        # معلمات مبسطة
        self.default_params = {
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "bb_period": 20,
            "bb_std": 2,
            "atr_period": 14,
            "volume_threshold": 1.2,
        }

        self.params = {**self.default_params, **params}
        self.required_candles = 50

        super().__init__(**self.params)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        حساب المؤشرات الفنية المطلوبة للاستراتيجية
        """
        try:
            # RSI
            df["rsi"] = ta.rsi(df["close"], length=self.params["rsi_period"])

            # Bollinger Bands - استخدام أسماء ديناميكية
            bb_period = self.params["bb_period"]
            bb_std = self.params["bb_std"]
            bb = ta.bbands(df["close"], length=bb_period, std=bb_std)

            # البحث عن الأعمدة الصحيحة بناءً على البارامترات الفعلية
            bb_upper_col = f"BBU_{bb_period}_{bb_std:.1f}"
            bb_middle_col = f"BBM_{bb_period}_{bb_std:.1f}"
            bb_lower_col = f"BBL_{bb_period}_{bb_std:.1f}"

            df["bb_upper"] = (
                bb[bb_upper_col]
                if bb_upper_col in bb.columns
                else bb.iloc[:, 0]
            )
            df["bb_middle"] = (
                bb[bb_middle_col]
                if bb_middle_col in bb.columns
                else bb.iloc[:, 1]
            )
            df["bb_lower"] = (
                bb[bb_lower_col]
                if bb_lower_col in bb.columns
                else bb.iloc[:, 2]
            )

            # ATR
            df["atr"] = ta.atr(
                df["high"],
                df["low"],
                df["close"],
                length=self.params["atr_period"],
            )

            # Volume ratio
            df["volume_ma"] = ta.sma(df["volume"], length=20)
            df["volume_ratio"] = df["volume"] / df["volume_ma"]

            return df

        except Exception as e:
            logger.error(f"خطأ في حساب المؤشرات: {str(e)}")
            return df

    def generate_signals(
        self,
        dataframe: pd.DataFrame,
        timeframe: str = "1h",
        candles_count: int = 100,
        mtf_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> pd.DataFrame:
        """
        توليد إشارات التداول بناءً على RSI وBollinger Bands
        """
        try:
            logger.info(
                f"بدء توليد إشارات التداول لاستراتيجية سكالبنج مبسطة - الإطار الزمني: {timeframe}")

            # نسخ البيانات لتجنب التعديل على الأصل
            df = dataframe.copy()

            # التحقق من وجود البيانات الكافية
            if len(df) < 30:
                logger.warning("البيانات غير كافية لتوليد إشارات موثوقة")
                return df

            # حساب المؤشرات الفنية
            df = self.calculate_indicators(df)

            # تعريف أعمدة الإشارات
            df["buy_signal"] = 0
            df["sell_signal"] = 0
            df["exit_signal"] = 0
            df["stop_loss"] = np.nan
            df["take_profit"] = np.nan

            # تكييف معايير الإشارات حسب الإطار الزمني
            rsi_oversold = 25 if timeframe in ["15m", "1h"] else 30
            rsi_overbought = 75 if timeframe in ["15m", "1h"] else 70
            volume_threshold = self.params["volume_threshold"]

            # توليد الإشارات
            for i in range(20, len(df)):
                try:
                    # شروط الشراء
                    buy_conditions = []

                    # RSI في منطقة التشبع البيعي
                    if "rsi" in df.columns:
                        buy_conditions.append(df["rsi"].iloc[i] < rsi_oversold)

                    # السعر قريب من الحد السفلي لـ Bollinger Bands
                    if all(col in df.columns for col in ["bb_lower", "close"]):
                        buy_conditions.append(
                            df["close"].iloc[i]
                            <= df["bb_lower"].iloc[i] * 1.01
                        )

                    # حجم جيد
                    if "volume_ratio" in df.columns:
                        buy_conditions.append(
                            df["volume_ratio"].iloc[i] > volume_threshold
                        )

                    # شروط البيع
                    sell_conditions = []

                    # RSI في منطقة التشبع الشرائي
                    if "rsi" in df.columns:
                        sell_conditions.append(
                            df["rsi"].iloc[i] > rsi_overbought
                        )

                    # السعر قريب من الحد العلوي لـ Bollinger Bands
                    if all(col in df.columns for col in ["bb_upper", "close"]):
                        sell_conditions.append(
                            df["close"].iloc[i]
                            >= df["bb_upper"].iloc[i] * 0.99
                        )

                    # حجم جيد
                    if "volume_ratio" in df.columns:
                        sell_conditions.append(
                            df["volume_ratio"].iloc[i] > volume_threshold
                        )

                    # توليد إشارة الشراء (يجب تحقق 2 من 3 شروط على الأقل)
                    if len(buy_conditions) >= 2 and sum(buy_conditions) >= 2:
                        df.loc[df.index[i], "buy_signal"] = 1

                        # حساب وقف الخسارة وجني الأرباح
                        if "atr" in df.columns:
                            atr_value = df["atr"].iloc[i]
                            df.loc[df.index[i], "stop_loss"] = df[
                                "close"
                            ].iloc[i] - (1.5 * atr_value)
                            df.loc[df.index[i], "take_profit"] = df[
                                "close"
                            ].iloc[i] + (2.5 * atr_value)

                    # توليد إشارة البيع (يجب تحقق 2 من 3 شروط على الأقل)
                    elif (
                        len(sell_conditions) >= 2 and sum(sell_conditions) >= 2
                    ):
                        df.loc[df.index[i], "sell_signal"] = 1

                        # حساب وقف الخسارة وجني الأرباح
                        if "atr" in df.columns:
                            atr_value = df["atr"].iloc[i]
                            df.loc[df.index[i], "stop_loss"] = df[
                                "close"
                            ].iloc[i] + (1.5 * atr_value)
                            df.loc[df.index[i], "take_profit"] = df[
                                "close"
                            ].iloc[i] - (2.5 * atr_value)

                    # شروط الخروج
                    exit_conditions = []

                    # RSI عاد إلى المنطقة المحايدة
                    if "rsi" in df.columns:
                        # خروج من الشراء إذا وصل RSI إلى 50 أو أعلى
                        if (
                            df["rsi"].iloc[i] > 50
                            and i > 0
                            and df["rsi"].iloc[i - 1] <= 50
                        ):
                            exit_conditions.append(True)
                        # خروج من البيع إذا وصل RSI إلى 50 أو أقل
                        elif (
                            df["rsi"].iloc[i] < 50
                            and i > 0
                            and df["rsi"].iloc[i - 1] >= 50
                        ):
                            exit_conditions.append(True)

                    # السعر عاد إلى المتوسط
                    if all(
                        col in df.columns for col in ["bb_middle", "close"]
                    ):
                        price_near_middle = (
                            abs(df["close"].iloc[i] - df["bb_middle"].iloc[i])
                            / df["bb_middle"].iloc[i]
                            < 0.005
                        )
                        exit_conditions.append(price_near_middle)

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
