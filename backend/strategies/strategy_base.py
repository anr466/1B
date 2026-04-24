#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
الاستراتيجية الأساسية: توفر الهيكل الأساسي لجميع استراتيجيات التداول
مع دعم التحليل متعدد الأطر الزمنية لتحسين جودة الإشارات
"""

import pandas as pd
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from backend.utils.multi_timeframe_helper import MultiTimeframeAnalyzer

logger = logging.getLogger(__name__)


class StrategyBase(ABC):
    """
    الفئة الأساسية لجميع استراتيجيات التداول.
    توفر الهيكل والدوال المشتركة التي يجب أن تنفذها جميع الاستراتيجيات.
    تدعم الآن التحليل متعدد الأطر الزمنية (Multi-Timeframe Analysis)
    لتحسين جودة الإشارات وتأكيد الاتجاه العام للسوق.
    """

    def __init__(self, **params):
        """
        تهيئة الاستراتيجية الأساسية

        المعلمات:
            params (Dict): معلمات خاصة بالاستراتيجية
        """
        self.name = self.__class__.__name__
        self.params = params
        self.required_candles = (
            200  # الحد الأدنى لعدد الشموع المطلوبة للاستراتيجية
        )

        # إعداد محلل الأطر الزمنية المتعددة
        self.mtf_analyzer = MultiTimeframeAnalyzer()

        # المعلمات الافتراضية للتحليل متعدد الأطر الزمنية
        # تفعيل/تعطيل التحليل متعدد الأطر الزمنية
        self.use_mtf_analysis = params.get("use_mtf_analysis", True)
        self.higher_timeframes = params.get(
            "higher_timeframes", []
        )  # الأطر الزمنية الأعلى للتحليل

    @abstractmethod
    def calculate_indicators(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        حساب المؤشرات الفنية المطلوبة للاستراتيجية

        المعلمات:
            dataframe (pd.DataFrame): إطار البيانات مع بيانات OHLCV

        المخرجات:
            pd.DataFrame: إطار البيانات مع المؤشرات المحسوبة
        """

    @abstractmethod
    def generate_signals(
        self,
        dataframe: pd.DataFrame,
        timeframe: str = "1h",
        candles_count: int = 100,
        mtf_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> pd.DataFrame:
        """
        استقبال DataFrame نظيف وإضافة المؤشرات وإشارات التداول

        المعلمات:
            dataframe (pd.DataFrame): إطار البيانات النظيف مع أعمدة OHLCV الأساسية
            timeframe (str): الإطار الزمني للبيانات (مثل '1h', '4h', '1d')
            candles_count (int): عدد الشموع المستخدمة في التحليل
            mtf_data (Dict[str, pd.DataFrame], optional): بيانات من أطر زمنية متعددة للتحليل المتقدم

        المخرجات:
            pd.DataFrame: إطار البيانات مع المؤشرات وإشارات التداول
        """

    def run(
        self,
        dataframe: pd.DataFrame,
        timeframe: str = "1h",
        symbol: str = None,
    ) -> pd.DataFrame:
        """
        دالة الواجهة الموحدة لتشغيل الاستراتيجية
        تعمل كواجهة موحدة لدالة run_strategy للحفاظ على التوافقية

        المعلمات:
            dataframe (pd.DataFrame): إطار البيانات مع بيانات OHLCV
            timeframe (str): الإطار الزمني للبيانات
            symbol (str, optional): رمز العملة (مطلوب للتحليل متعدد الأطر الزمنية)

        المخرجات:
            pd.DataFrame: إطار البيانات مع المؤشرات والإشارات
        """
        return self.run_strategy(dataframe, timeframe, symbol)

    def run_strategy(
        self,
        dataframe: pd.DataFrame,
        timeframe: str = "1h",
        symbol: str = None,
    ) -> pd.DataFrame:
        """
        تشغيل الاستراتيجية بالكامل بتنفيذ موحد لكافة الاستراتيجيات

        هذه الدالة تنفذ تدفق استخدام الاستراتيجية بالكامل بخطوات موحدة:
        1. التأكد من البيانات كافية (required_candles)
        2. جلب وتحليل البيانات متعددة الأطر الزمنية إذا كان مفعلاً
        3. حساب المؤشرات الفنية
        4. توليد الإشارات (مع دمج تحليل الأطر الزمنية المتعددة)
        5. توحيد أسماء الأعمدة
        6. التأكد من وجود أعمدة الإشارات الضرورية

        المعلمات:
            dataframe (pd.DataFrame): إطار البيانات مع بيانات OHLCV
            timeframe (str): الإطار الزمني للبيانات
            symbol (str, optional): رمز العملة (مطلوب للتحليل متعدد الأطر الزمنية)

        المخرجات:
            pd.DataFrame: إطار البيانات مع المؤشرات والإشارات
        """
        if dataframe is None or len(dataframe) < self.required_candles:
            logger.error(f"البيانات غير كافية، مطلوب {
                self.required_candles} شمعة على الأقل")
            return None

        try:
            # تهيئة متغيرات لبيانات الأطر الزمنية المتعددة
            mtf_data = None
            aligned_df = dataframe.copy()

            # إذا كان التحليل متعدد الأطر الزمنية مفعلاً وتم تحديد رمز العملة
            if self.use_mtf_analysis and self.higher_timeframes and symbol:
                # جلب بيانات من أطر زمنية متعددة
                logger.info(
                    f"جلب بيانات متعددة الأطر الزمنية لـ {symbol}: {timeframe} (أساسي) + {
                        self.higher_timeframes}")

                try:
                    # جلب البيانات وحساب المؤشرات لكل إطار زمني
                    mtf_data = self.mtf_analyzer.get_multi_timeframe_data(
                        symbol,
                        timeframe,
                        self.higher_timeframes,
                        len(dataframe),
                    )

                    if mtf_data and timeframe in mtf_data:
                        # محاذاة الأطر الزمنية
                        aligned_mtf = self.mtf_analyzer.align_timeframes(
                            mtf_data, timeframe
                        )

                        # حساب المؤشرات لكل إطار زمني
                        mtf_with_indicators = (
                            self.mtf_analyzer.calculate_mtf_indicators(
                                aligned_mtf
                            )
                        )

                        # دمج بيانات الأطر الزمنية المختلفة في إطار زمني واحد
                        aligned_df = (
                            self.mtf_analyzer.resample_to_base_timeframe(
                                mtf_with_indicators, timeframe
                            )
                        )
                        logger.info(
                            f"تم دمج بيانات {len(self.higher_timeframes) + 1} إطار زمني بنجاح"
                        )
                    else:
                        logger.warning(
                            "لم يتم العثور على بيانات متعددة الأطر الزمنية، سيتم استخدام البيانات الأساسية فقط"
                        )
                        aligned_df = dataframe.copy()
                        mtf_data = None
                except Exception as e:
                    logger.error(f"خطأ في جلب بيانات متعددة الأطر الزمنية: {
                        str(e)}")
                    aligned_df = dataframe.copy()
                    mtf_data = None

            # حساب المؤشرات على البيانات الموحدة
            df_with_indicators = self.calculate_indicators(aligned_df)

            # توليد الإشارات - تمرير بيانات الأطر الزمنية المتعددة إذا كانت
            # متوفرة
            result = self.generate_signals(
                df_with_indicators, timeframe, len(dataframe), mtf_data
            )

            # توحيد أسماء الأعمدة
            result = self._standardize_column_names(result)

            # التأكد من وجود الأعمدة الضرورية
            required_columns = ["buy_signal", "sell_signal"]
            for col in required_columns:
                if col not in result.columns:
                    logger.warning(f"عمود {col} غير موجود في النتائج")
                    result[col] = 0

            # سجل تفصيلي للتحقق من الإشارات
            signal_count = {
                "buy_signal": (
                    result["buy_signal"].sum()
                    if "buy_signal" in result.columns
                    else 0
                ),
                "sell_signal": (
                    result["sell_signal"].sum()
                    if "sell_signal" in result.columns
                    else 0
                ),
                "stop_loss_signal": (
                    result["stop_loss_signal"].sum()
                    if "stop_loss_signal" in result.columns
                    else 0
                ),
                "take_profit_signal": (
                    result["take_profit_signal"].sum()
                    if "take_profit_signal" in result.columns
                    else 0
                ),
                "partial_exit_signal": (
                    result["partial_exit_signal"].sum()
                    if "partial_exit_signal" in result.columns
                    else 0
                ),
            }

            logger.info(f"استراتيجية {self.name} ولدت إشارات: {signal_count}")

            return result

        except Exception as e:
            logger.error(f"خطأ في تنفيذ الاستراتيجية: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            return dataframe

    def _standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        توحيد أسماء الأعمدة للإشارات والبيانات

        المعلمات:
            df (pd.DataFrame): إطار البيانات للتوحيد

        المخرجات:
            pd.DataFrame: إطار البيانات مع أسماء الأعمدة الموحدة
        """
        # توحيد أسماء أعمدة OHLCV - تحويل كل الأعمدة إلى الأحرف الصغيرة
        ohlcv_map = {
            "Open": "open",
            "open": "open",
            "High": "high",
            "high": "high",
            "Low": "low",
            "low": "low",
            "Close": "close",
            "close": "close",
            "Volume": "volume",
            "volume": "volume",
        }

        # توحيد أسماء أعمدة الإشارات لاستخدام المسميات الموحدة
        signal_map = {
            "buy": "buy_signal",
            "sell": "sell_signal",
            "exit": "exit_signal",
            "exit_signal": "exit_signal",
            "stop_loss": "stop_loss_signal",
            "sl_signal": "stop_loss_signal",
            "take_profit": "take_profit_signal",
            "tp_signal": "take_profit_signal",
            "partial_exit": "partial_exit_signal",
        }

        # أولاً: توحيد أعمدة OHLCV إلى أحرف صغيرة
        for old_col, new_col in ohlcv_map.items():
            if old_col in df.columns and old_col != new_col:
                df[new_col] = df[old_col]
                # لا نحذف العمود القديم للحفاظ على التوافقية الخلفية

        # ثانياً: توحيد أسماء الإشارات
        for old_col, new_col in signal_map.items():
            if old_col in df.columns and old_col != new_col:
                df[new_col] = df[old_col]
                # لا نحذف العمود القديم للحفاظ على التوافقية الخلفية

        return df

    def backtest(
        self,
        dataframe: pd.DataFrame,
        initial_capital: float = 1000.0,
        commission: float = 0.001,
        risk_per_trade: float = 0.1,
    ) -> Dict[str, Any]:
        """
        إجراء اختبار خلفي للاستراتيجية على البيانات التاريخية

        المعلمات:
            dataframe (pd.DataFrame): إطار البيانات مع إشارات التداول
            initial_capital (float): رأس المال الأولي
            commission (float): عمولة التداول
            risk_per_trade (float): نسبة المخاطرة لكل صفقة

        المخرجات:
            Dict[str, Any]: نتائج الاختبار الخلفي
        """
        df = dataframe.copy()

        # التأكد من وجود إشارات التداول حسب المسميات الموحدة
        if "buy_signal" not in df.columns or "sell_signal" not in df.columns:
            df = self.generate_signals(df)

        # توحيد أسماء الأعمدة للمؤشرات
        df = self._standardize_column_names(df)

        # تسجيل تشخيصي للتحقق من الإشارات والأعمدة
        buy_signals_count = (
            df["buy_signal"].sum() if "buy_signal" in df.columns else 0
        )
        sell_signals_count = (
            df["sell_signal"].sum() if "sell_signal" in df.columns else 0
        )
        logger.debug(
            f"[تشخيص backtest] عدد إشارات الشراء: {buy_signals_count}, عدد إشارات البيع: {sell_signals_count}"
        )
        logger.debug(f"[تشخيص backtest] أسماء الأعمدة المتاحة: {
            ', '.join(
                df.columns.tolist()[
                    :10])} ...")

        # إعداد متغيرات للاختبار الخلفي
        capital = initial_capital
        position = 0
        entry_price = 0
        trades = []

        # تتبع الصفقات
        for i in range(1, len(df)):
            current_price = df["close"].iloc[i]

            # إشارة شراء وليس لدينا مركز - استخدام المسميات الموحدة
            buy_signal = (
                df["buy_signal"].iloc[i - 1] == 1
                if "buy_signal" in df.columns
                else False
            )
            if buy_signal and position == 0:
                position_size = (capital * risk_per_trade) / current_price
                cost = position_size * current_price * (1 + commission)

                if cost <= capital:
                    position = position_size
                    entry_price = current_price
                    entry_date = df.index[i]
                    capital -= cost
                    logger.debug(
                        f"[تشخيص backtest] فتح صفقة شراء: التاريخ={entry_date}, السعر={
                            entry_price:.2f}, الحجم={
                            position_size:.6f}")

            # إشارة بيع ولدينا مركز - استخدام المسميات الموحدة
            sell_signal = (
                df["sell_signal"].iloc[i - 1] == 1
                if "sell_signal" in df.columns
                else False
            )
            stop_loss = (
                df["stop_loss_signal"].iloc[i - 1] == 1
                if "stop_loss_signal" in df.columns
                else False
            )
            take_profit = (
                df["take_profit_signal"].iloc[i - 1] == 1
                if "take_profit_signal" in df.columns
                else False
            )

            if (sell_signal or stop_loss or take_profit) and position > 0:
                revenue = position * current_price * (1 - commission)
                profit = revenue - (position * entry_price * (1 + commission))
                profit_pct = (current_price / entry_price - 1) * 100

                exit_reason = (
                    "بيع"
                    if sell_signal
                    else "وقف خسارة" if stop_loss else "جني أرباح"
                )
                logger.debug(
                    f"[تشخيص backtest] إغلاق صفقة [{exit_reason}]: التاريخ={
                        df.index[i]}, دخول={
                        entry_price:.2f}, خروج={
                        current_price:.2f}, ربح={
                        profit_pct:.2f}%"
                )

                trades.append(
                    {
                        "entry_date": entry_date,
                        "exit_date": df.index[i],
                        "entry_price": entry_price,
                        "exit_price": current_price,
                        "position_size": position,
                        "profit": profit,
                        "profit_pct": profit_pct,
                        "is_win": profit > 0,
                        "exit_reason": exit_reason,
                    }
                )

                capital += revenue
                position = 0

        # إذا كان لدينا مركز مفتوح في نهاية الاختبار، نغلقه بسعر الإغلاق الأخير
        if position > 0:
            # استخدام عمود close (بأحرف صغيرة فقط) بعد توحيد الأعمدة
            current_price = df["close"].iloc[-1]
            revenue = position * current_price * (1 - commission)
            profit = revenue - (position * entry_price * (1 + commission))
            profit_pct = (current_price / entry_price - 1) * 100

            logger.debug(f"[تشخيص backtest] إغلاق صفقة نهائية: الربح={
                profit_pct:.2f}%")

            trades.append(
                {
                    "entry_date": entry_date,
                    "exit_date": df.index[-1],
                    "entry_price": entry_price,
                    "exit_price": current_price,
                    "position_size": position,
                    "profit": profit,
                    "profit_pct": profit_pct,
                    "is_win": profit > 0,
                }
            )

            capital += revenue

        # حساب المقاييس
        total_trades = len(trades)
        winning_trades = sum(1 for trade in trades if trade["is_win"])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        total_profit = capital - initial_capital
        profit_pct = (capital / initial_capital - 1) * 100

        # إضافة تسجيلات تشخيصية مفصلة
        logger.info(f"[نتائج backtest] اسم الاستراتيجية: {self.name}")
        logger.info(
            f"[نتائج backtest] عدد الصفقات: {total_trades}, إجمالي الربح: {
                profit_pct:.2f}%, نسبة الفوز: {
                win_rate * 100:.1f}%"
        )
        if total_trades > 0:
            avg_profit = (
                sum(trade["profit_pct"] for trade in trades) / total_trades
            )
            max_profit = (
                max(trade["profit_pct"] for trade in trades) if trades else 0
            )
            max_loss = (
                min(trade["profit_pct"] for trade in trades) if trades else 0
            )
            logger.info(f"[نتائج backtest] متوسط الربح: {
                avg_profit:.2f}%, أعلى ربح: {
                max_profit:.2f}%, أعلى خسارة: {
                max_loss:.2f}%")
        else:
            logger.warning(
                f"[نتائج backtest] لم يتم تنفيذ أي صفقات! التحقق من إشارات التداول ومعايير الدخول/الخروج.")

        return {
            "name": self.name,
            "initial_capital": initial_capital,
            "final_capital": capital,
            "total_profit": total_profit,
            "profit_pct": profit_pct,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": total_trades - winning_trades,
            "win_rate": win_rate,
            "trades": trades,
        }

    def _add_stop_loss(
        self, dataframe: pd.DataFrame, stop_loss_pct: float = 0.02
    ) -> pd.DataFrame:
        """
        إضافة إشارات وقف الخسارة إلى إطار البيانات

        المعلمات:
            dataframe (pd.DataFrame): إطار البيانات مع إشارات التداول
            stop_loss_pct (float): نسبة وقف الخسارة

        المخرجات:
            pd.DataFrame: إطار البيانات مع إشارات وقف الخسارة
        """
        df = dataframe.copy()
        df["stop_loss_signal"] = 0

        in_position = False
        entry_price = 0

        for i in range(1, len(df)):
            # إشارة شراء وليس لدينا مركز - دعم كلا الاسمين للإشارات
            buy_col = "buy" if "buy" in df.columns else "buy_signal"

            if df[buy_col].iloc[i - 1] == 1 and not in_position:
                in_position = True
                entry_price = (
                    df["Close"].iloc[i]
                    if "Close" in df.columns
                    else df["close"].iloc[i]
                )

            # تحقق من وقف الخسارة
            if in_position:
                current_price = (
                    df["Close"].iloc[i]
                    if "Close" in df.columns
                    else df["close"].iloc[i]
                )

                if current_price < entry_price * (1 - stop_loss_pct):
                    df.loc[df.index[i], "stop_loss_signal"] = 1
                    in_position = False

            # إغلاق مركز
            if df["sell_signal"].iloc[i - 1] == 1 and in_position:
                in_position = False

        return df

    def _identify_swing_points(
        self, dataframe: pd.DataFrame, window: int = 3, min_size: float = 0.003
    ) -> pd.DataFrame:
        """
        تحديد نقاط التأرجح (القمم والقيعان) في البيانات

        المعلمات:
            dataframe (pd.DataFrame): إطار البيانات
            window (int): حجم النافذة لتحديد القمم والقيعان
            min_size (float): الحد الأدنى لحجم التأرجح كنسبة من السعر

        المخرجات:
            pd.DataFrame: إطار البيانات مع نقاط التأرجح المحددة
        """
        df = dataframe.copy()

        # إضافة أعمدة للقمم والقيعان
        df["Swing_High"] = 0
        df["Swing_Low"] = 0

        # لا يمكن تحديد نقاط التأرجح للنقاط الأولى والأخيرة في البيانات
        for i in range(window, len(df) - window):
            # تحديد القمم
            if all(
                df["high"].iloc[i] > df["high"].iloc[i - j]
                for j in range(1, window + 1)
            ) and all(
                df["high"].iloc[i] > df["high"].iloc[i + j]
                for j in range(1, window + 1)
            ):

                # التحقق من حجم التأرجح
                price_range = (
                    df["high"].iloc[i]
                    - min(df["low"].iloc[i - window: i + window + 1])
                ) / df["close"].iloc[i]
                if price_range >= min_size:
                    df.loc[df.index[i], "Swing_High"] = 1

            # تحديد القيعان
            if all(
                df["low"].iloc[i] < df["low"].iloc[i - j]
                for j in range(1, window + 1)
            ) and all(
                df["low"].iloc[i] < df["low"].iloc[i + j]
                for j in range(1, window + 1)
            ):

                # التحقق من حجم التأرجح
                price_range = (
                    max(df["high"].iloc[i - window: i + window + 1])
                    - df["low"].iloc[i]
                ) / df["close"].iloc[i]
                if price_range >= min_size:
                    df.loc[df.index[i], "Swing_Low"] = 1

        return df

    def _calculate_bollinger_bands(
        self, dataframe: pd.DataFrame, window: int = 20, num_std: float = 2.0
    ) -> pd.DataFrame:
        """
        حساب مؤشر بولينجر باند

        المعلمات:
            dataframe (pd.DataFrame): إطار البيانات
            window (int): فترة النافذة لحساب المتوسط المتحرك
            num_std (float): عدد الانحرافات المعيارية

        المخرجات:
            pd.DataFrame: إطار البيانات مع مؤشر بولينجر باند
        """
        df = dataframe.copy()

        # حساب المتوسط المتحرك البسيط
        df["bb_middle"] = df["close"].rolling(window=window).mean()

        # حساب الانحراف المعياري
        rolling_std = df["close"].rolling(window=window).std()

        # حساب النطاقات العليا والسفلى
        df["bb_upper"] = df["bb_middle"] + (rolling_std * num_std)
        df["bb_lower"] = df["bb_middle"] - (rolling_std * num_std)

        # حساب عرض النطاق
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]

        return df

    def _calculate_stochastic(
        self, dataframe: pd.DataFrame, k_period: int = 14, d_period: int = 3
    ) -> pd.DataFrame:
        """
        حساب مؤشر ستوكاستك

        المعلمات:
            dataframe (pd.DataFrame): إطار البيانات
            k_period (int): فترة K
            d_period (int): فترة D

        المخرجات:
            pd.DataFrame: إطار البيانات مع مؤشر ستوكاستك
        """
        df = dataframe.copy()

        # حساب الحد الأدنى والأقصى ضمن الفترة
        low_min = df["low"].rolling(window=k_period).min()
        high_max = df["high"].rolling(window=k_period).max()

        # حساب %K
        df["stoch_k"] = 100 * ((df["close"] - low_min) / (high_max - low_min))

        # حساب %D (المتوسط المتحرك لـ %K)
        df["stoch_d"] = df["stoch_k"].rolling(window=d_period).mean()

        return df
