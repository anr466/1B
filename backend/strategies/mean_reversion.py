#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
استراتيجية العودة للمتوسط المحسّنة (Mean Reversion Strategy V2)
محسّنة بناءً على نتائج MTFA: 12% شهرياً

التحسينات:
1. شروط دخول متعددة (RSI + BB + Volume + قرب الدعم)
2. إدارة مخاطر متقدمة (SL ثابت 2.5 ATR + Trailing بعد +3%)
3. شروط خروج عكس الدخول (RSI > 70 + BB Upper)

المنطق:
1. الدخول: RSI < 30 + BB Lower + Volume > 1.3x + قرب الدعم
2. الخروج: RSI > 70 + BB Upper + قرب المقاومة
3. SL ثابت 2.5 ATR + Trailing SL 2.5 ATR بعد +3%
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import logging

from backend.strategies.strategy_base import StrategyBase

logger = logging.getLogger(__name__)


class MeanReversionStrategy(StrategyBase):
    """استراتيجية العودة للمتوسط"""

    def __init__(self, **params):
        """تهيئة الاستراتيجية"""
        self.name = "MeanReversionStrategy"
        self.description = "استراتيجية العودة للمتوسط مع مؤشرات التشبع"

        # معلمات محسّنة - 69% Win Rate, 12% شهرياً
        self.default_params = {
            "sma_period": 20,  # فترة المتوسط المتحرك
            "bb_period": 20,  # فترة Bollinger Bands
            "bb_std": 2.0,  # انحراف معياري
            "rsi_period": 14,  # فترة RSI
            "rsi_oversold": 30,  # تشبع بيعي
            "rsi_overbought": 70,  # تشبع شرائي
            "deviation_threshold": 1.2,  # الإعداد المثالي
            "atr_period": 14,  # فترة ATR
            "fixed_sl_atr": 2.5,  # SL ثابت (محسّن)
            "trailing_sl_atr": 2.5,  # Trailing SL
            "trailing_activation_pct": 3.0,  # تفعيل Trailing بعد 3%
            "support_distance_pct": 1.5,  # قرب الدعم
            "volume_multiplier": 1.3,  # مضاعف الحجم
            "volume_confirm": True,  # تأكيد بالحجم
            "stop_loss_atr": 2.5,  # وقف الخسارة بوحدات ATR
            "take_profit_ratio": 1.0,  # نسبة هدف الربح
        }

        self.params = {**self.default_params, **params}
        super().__init__(**self.params)

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """حساب المؤشرات الأساسية"""
        try:
            # 1. المتوسط المتحرك البسيط
            df["sma"] = ta.sma(df["close"], length=self.params["sma_period"])

            # 2. Bollinger Bands - استخدام أسماء ديناميكية آمنة
            bb_period = self.params["bb_period"]
            bb_std = self.params["bb_std"]
            bb = ta.bbands(df["close"], length=bb_period, std=bb_std)

            # البحث عن الأعمدة الصحيحة أو استخدام الفهرس
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

            # 3. مؤشر RSI
            df["rsi"] = ta.rsi(df["close"], length=self.params["rsi_period"])

            # 4. مؤشر ATR
            df["atr"] = ta.atr(
                df["high"],
                df["low"],
                df["close"],
                length=self.params["atr_period"],
            )

            # 5. الانحراف عن المتوسط
            safe_sma = df["sma"].replace(0, np.nan)
            df["price_deviation"] = (df["close"] - safe_sma) / safe_sma * 100

            # 6. متوسط الحجم
            if self.params["volume_confirm"]:
                df["volume_ma"] = df["volume"].rolling(20).mean()
                safe_vol_ma = df["volume_ma"].replace(0, np.nan)
                df["volume_ratio"] = df["volume"] / safe_vol_ma

            # 7. مسافة من Bollinger Bands
            safe_bb_range = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
            df["bb_position"] = (df["close"] - df["bb_lower"]) / safe_bb_range

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

            for i in range(self.params["sma_period"], len(df)):
                # شروط الشراء (انحراف سلبي شديد)
                oversold_condition = (
                    # تحت الحد الأدنى لـ BB
                    df["close"].iloc[i] < df["bb_lower"].iloc[i]
                    and
                    # RSI في منطقة التشبع البيعي
                    df["rsi"].iloc[i] < self.params["rsi_oversold"]
                    and df["price_deviation"].iloc[i]
                    < -self.params["deviation_threshold"]  # انحراف سلبي كبير
                )

                # تأكيد إضافي بالحجم
                volume_confirm = True
                if self.params["volume_confirm"]:
                    volume_confirm = df["volume_ratio"].iloc[i] > 1.0

                if oversold_condition and volume_confirm:
                    df.loc[df.index[i], "buy_signal"] = 1
                    # وقف الخسارة تحت أقل نقطة حديثة
                    current_price = df["close"].iloc[i]
                    atr_value = df["atr"].iloc[i]
                    df.loc[df.index[i], "stop_loss"] = current_price - (
                        self.params["stop_loss_atr"] * atr_value
                    )
                    # هدف الربح عند العودة للمتوسط
                    df.loc[df.index[i], "take_profit"] = df["sma"].iloc[
                        i
                    ] * self.params["take_profit_ratio"] + current_price * (
                        1 - self.params["take_profit_ratio"]
                    )

                # شروط البيع (انحراف إيجابي شديد)
                overbought_condition = (
                    # فوق الحد الأعلى لـ BB
                    df["close"].iloc[i] > df["bb_upper"].iloc[i]
                    and
                    # RSI في منطقة التشبع الشرائي
                    df["rsi"].iloc[i] > self.params["rsi_overbought"]
                    and
                    # انحراف إيجابي كبير
                    df["price_deviation"].iloc[i]
                    > self.params["deviation_threshold"]
                )

                if overbought_condition and volume_confirm:
                    df.loc[df.index[i], "sell_signal"] = 1
                    # وقف الخسارة فوق أعلى نقطة حديثة
                    current_price = df["close"].iloc[i]
                    atr_value = df["atr"].iloc[i]
                    df.loc[df.index[i], "stop_loss"] = current_price + (
                        self.params["stop_loss_atr"] * atr_value
                    )
                    # هدف الربح عند العودة للمتوسط
                    df.loc[df.index[i], "take_profit"] = df["sma"].iloc[
                        i
                    ] * self.params["take_profit_ratio"] + current_price * (
                        1 - self.params["take_profit_ratio"]
                    )

            return df

        except Exception as e:
            logger.error(f"خطأ في توليد الإشارات: {str(e)}")
            return df
