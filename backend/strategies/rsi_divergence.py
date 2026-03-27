#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
استراتيجية تباعد RSI (RSI Divergence Strategy)
تركز على اكتشاف التباعد بين السعر ومؤشر RSI

المنطق:
1. تباعد إيجابي: السعر ينخفض و RSI يرتفع (إشارة شراء)
2. تباعد سلبي: السعر يرتفع و RSI ينخفض (إشارة بيع)
3. تأكيد بكسر مستوى مهم
4. إدارة مخاطر محكمة
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import logging
from typing import List, Tuple

from backend.strategies.strategy_base import StrategyBase

logger = logging.getLogger(__name__)


class RSIDivergenceStrategy(StrategyBase):
    """استراتيجية تباعد RSI"""

    def __init__(self, **params):
        """تهيئة الاستراتيجية"""
        self.name = "RSIDivergenceStrategy"
        self.description = "استراتيجية تباعد RSI مع تأكيد الكسر"

        # معلمات افتراضية
        self.default_params = {
            "rsi_period": 14,  # فترة RSI
            "lookback_period": 20,  # فترة البحث عن القمم والقيعان
            "min_peak_distance": 5,  # أقل مسافة بين القمم/القيعان
            "divergence_threshold": 1.5,  # عتبة التباعد مخففة
            "rsi_overbought": 70,  # مستوى التشبع الشرائي
            "rsi_oversold": 30,  # مستوى التشبع البيعي
            "confirmation_candles": 1,  # عدد الشموع للتأكيد مخفف
            "atr_period": 14,  # فترة ATR
            "stop_loss_atr": 2.0,  # وقف خسارة
            "take_profit_atr": 4.0,  # هدف ربح
            "volume_confirm": True,  # تأكيد بالحجم
        }

        self.params = {**self.default_params, **params}
        super().__init__(**self.params)

    def find_peaks_valleys(
        self, data: pd.Series, distance: int = 5
    ) -> Tuple[List[int], List[int]]:
        """العثور على القمم والقيعان بدون scipy"""
        try:
            peaks = []
            valleys = []

            if len(data) < distance * 2 + 1:
                return peaks, valleys

            # العثور على القمم
            for i in range(distance, len(data) - distance):
                is_peak = True
                current_val = data.iloc[i]

                # التحقق من أن القيمة أعلى من جميع النقاط المحيطة
                for j in range(1, distance + 1):
                    if (
                        data.iloc[i - j] >= current_val
                        or data.iloc[i + j] >= current_val
                    ):
                        is_peak = False
                        break

                if is_peak:
                    peaks.append(i)

            # العثور على القيعان
            for i in range(distance, len(data) - distance):
                is_valley = True
                current_val = data.iloc[i]

                # التحقق من أن القيمة أقل من جميع النقاط المحيطة
                for j in range(1, distance + 1):
                    if (
                        data.iloc[i - j] <= current_val
                        or data.iloc[i + j] <= current_val
                    ):
                        is_valley = False
                        break

                if is_valley:
                    valleys.append(i)

            return peaks, valleys

        except Exception as e:
            logger.error(f"خطأ في العثور على القمم والقيعان: {str(e)}")
            return [], []

    def detect_divergence(
        self,
        price_data: pd.Series,
        rsi_data: pd.Series,
        peaks: List[int],
        valleys: List[int],
    ) -> pd.Series:
        """اكتشاف التباعد"""
        try:
            divergence = pd.Series(0, index=price_data.index)

            # فحص التباعد الإيجابي (قيعان)
            for i in range(1, len(valleys)):
                if valleys[i] < len(price_data) and valleys[i - 1] < len(
                    price_data
                ):
                    current_valley = valleys[i]
                    prev_valley = valleys[i - 1]

                    # السعر ينخفض و RSI يرتفع
                    price_lower = (
                        price_data.iloc[current_valley]
                        < price_data.iloc[prev_valley]
                    )
                    rsi_higher = (
                        rsi_data.iloc[current_valley]
                        > rsi_data.iloc[prev_valley]
                    )

                    if price_lower and rsi_higher:
                        # تباعد إيجابي - إشارة شراء
                        divergence.iloc[current_valley] = 1

            # فحص التباعد السلبي (قمم)
            for i in range(1, len(peaks)):
                if peaks[i] < len(price_data) and peaks[i - 1] < len(
                    price_data
                ):
                    current_peak = peaks[i]
                    prev_peak = peaks[i - 1]

                    # السعر يرتفع و RSI ينخفض
                    price_higher = (
                        price_data.iloc[current_peak]
                        > price_data.iloc[prev_peak]
                    )
                    rsi_lower = (
                        rsi_data.iloc[current_peak] < rsi_data.iloc[prev_peak]
                    )

                    if price_higher and rsi_lower:
                        # تباعد سلبي - إشارة بيع
                        divergence.iloc[current_peak] = -1

            return divergence

        except Exception as e:
            logger.error(f"خطأ في اكتشاف التباعد: {str(e)}")
            return pd.Series(0, index=price_data.index)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """حساب المؤشرات الأساسية"""
        try:
            # 1. مؤشر RSI
            df["rsi"] = ta.rsi(df["close"], length=self.params["rsi_period"])

            # 2. مؤشر ATR
            df["atr"] = ta.atr(
                df["high"],
                df["low"],
                df["close"],
                length=self.params["atr_period"],
            )

            # 3. متوسط الحجم
            if self.params["volume_confirm"]:
                df["volume_ma"] = df["volume"].rolling(20).mean()
                df["volume_ratio"] = df["volume"] / df["volume_ma"]

            # 4. العثور على القمم والقيعان
            if len(df) >= self.params["lookback_period"]:
                price_peaks, price_valleys = self.find_peaks_valleys(
                    df["close"], distance=self.params["min_peak_distance"]
                )
                rsi_peaks, rsi_valleys = self.find_peaks_valleys(
                    df["rsi"].dropna(),
                    distance=self.params["min_peak_distance"],
                )

                # 5. اكتشاف التباعد
                df["divergence"] = self.detect_divergence(
                    df["close"], df["rsi"], price_peaks, price_valleys
                )
            else:
                df["divergence"] = 0

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

            for i in range(
                self.params["lookback_period"],
                len(df) - self.params["confirmation_candles"],
            ):
                # شروط الشراء (تباعد إيجابي)
                bullish_divergence = df["divergence"].iloc[i] == 1
                # مرونة في المستوى
                rsi_oversold = (
                    df["rsi"].iloc[i] < self.params["rsi_oversold"] + 10
                )

                # تأكيد بالحجم
                volume_confirm = True
                if self.params["volume_confirm"]:
                    volume_confirm = df["volume_ratio"].iloc[i] > 1.0

                # تأكيد بكسر مستوى
                price_confirmation = False
                for j in range(1, self.params["confirmation_candles"] + 1):
                    if i + j < len(df):
                        if df["close"].iloc[i + j] > df["high"].iloc[i]:
                            price_confirmation = True
                            break

                if (
                    bullish_divergence
                    and rsi_oversold
                    and volume_confirm
                    and price_confirmation
                ):
                    df.loc[df.index[i], "buy_signal"] = 1
                    current_price = df["close"].iloc[i]
                    atr_value = df["atr"].iloc[i]
                    df.loc[df.index[i], "stop_loss"] = current_price - (
                        self.params["stop_loss_atr"] * atr_value
                    )
                    df.loc[df.index[i], "take_profit"] = current_price + (
                        self.params["take_profit_atr"] * atr_value
                    )

                # شروط البيع (تباعد سلبي)
                bearish_divergence = df["divergence"].iloc[i] == -1
                # مرونة في المستوى
                rsi_overbought = (
                    df["rsi"].iloc[i] > self.params["rsi_overbought"] - 10
                )

                # تأكيد بكسر مستوى
                price_confirmation = False
                for j in range(1, self.params["confirmation_candles"] + 1):
                    if i + j < len(df):
                        if df["close"].iloc[i + j] < df["low"].iloc[i]:
                            price_confirmation = True
                            break

                if (
                    bearish_divergence
                    and rsi_overbought
                    and volume_confirm
                    and price_confirmation
                ):
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
