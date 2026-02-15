#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
استراتيجية اتجاه السعر والحجم (Volume Price Trend Strategy)
تركز على العلاقة بين حركة السعر والحجم

المنطق:
1. زيادة الحجم مع ارتفاع السعر = قوة صاعدة
2. زيادة الحجم مع انخفاض السعر = قوة هابطة
3. تأكيد بمؤشر VPT وتقاطع المتوسطات
4. فلتر بمؤشر الزخم
"""

import pandas as pd
import numpy as np
import pandas_ta as ta
import logging
from typing import Dict, Any, Optional

from backend.strategies.strategy_base import StrategyBase

logger = logging.getLogger(__name__)

class VolumePriceTrendStrategy(StrategyBase):
    """استراتيجية اتجاه السعر والحجم"""
    
    def __init__(self, **params):
        """تهيئة الاستراتيجية"""
        self.name = "VolumePriceTrendStrategy"
        self.description = "استراتيجية اتجاه السعر والحجم مع مؤشر VPT"
        
        # معلمات افتراضية
        self.default_params = {
            'vpt_ma_period': 14,        # فترة متوسط VPT
            'price_ma_fast': 10,        # متوسط سعر سريع
            'price_ma_slow': 20,        # متوسط سعر بطيء
            'volume_ma_period': 20,     # فترة متوسط الحجم
            'volume_threshold': 1.5,    # عتبة الحجم المطلوبة
            'momentum_period': 10,      # فترة مؤشر الزخم
            'atr_period': 14,           # فترة ATR
            'stop_loss_atr': 2.0,       # وقف خسارة
            'take_profit_atr': 3.0,     # هدف ربح
            'trend_strength_min': 0.6   # قوة الاتجاه المطلوبة
        }
        
        self.params = {**self.default_params, **params}
        super().__init__(**self.params)
        
    def calculate_vpt(self, df: pd.DataFrame) -> pd.Series:
        """حساب مؤشر Volume Price Trend"""
        try:
            vpt = pd.Series(0.0, index=df.index)
            
            for i in range(1, len(df)):
                price_change = (df['close'].iloc[i] - df['close'].iloc[i-1]) / df['close'].iloc[i-1]
                vpt.iloc[i] = vpt.iloc[i-1] + (df['volume'].iloc[i] * price_change)
            
            return vpt
            
        except Exception as e:
            logger.error(f"خطأ في حساب VPT: {str(e)}")
            return pd.Series(0.0, index=df.index)
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """حساب المؤشرات الأساسية"""
        try:
            # 1. مؤشر Volume Price Trend
            df['vpt'] = self.calculate_vpt(df)
            df['vpt_ma'] = df['vpt'].rolling(self.params['vpt_ma_period']).mean()
            
            # 2. المتوسطات المتحركة للسعر
            df['price_ma_fast'] = ta.sma(df['close'], length=self.params['price_ma_fast'])
            df['price_ma_slow'] = ta.sma(df['close'], length=self.params['price_ma_slow'])
            
            # 3. متوسط الحجم
            df['volume_ma'] = df['volume'].rolling(self.params['volume_ma_period']).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            # 4. مؤشر الزخم
            df['momentum'] = ta.mom(df['close'], length=self.params['momentum_period'])
            
            # 5. مؤشر ATR
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.params['atr_period'])
            
            # 6. قوة الاتجاه
            df['trend_strength'] = np.abs(df['price_ma_fast'] - df['price_ma_slow']) / df['price_ma_slow']
            
            # 7. إشارات VPT
            df['vpt_signal'] = 0
            for i in range(self.params['vpt_ma_period'], len(df)):
                if df['vpt'].iloc[i] > df['vpt_ma'].iloc[i] and df['vpt'].iloc[i-1] <= df['vpt_ma'].iloc[i-1]:
                    df.loc[df.index[i], 'vpt_signal'] = 1  # إشارة صاعدة
                elif df['vpt'].iloc[i] < df['vpt_ma'].iloc[i] and df['vpt'].iloc[i-1] >= df['vpt_ma'].iloc[i-1]:
                    df.loc[df.index[i], 'vpt_signal'] = -1  # إشارة هابطة
            
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
            df['buy_signal'] = 0
            df['sell_signal'] = 0
            df['stop_loss'] = np.nan
            df['take_profit'] = np.nan
            
            for i in range(max(self.params['price_ma_slow'], self.params['vpt_ma_period']), len(df)):
                # شروط الشراء
                buy_conditions = []
                
                # 1. إشارة VPT صاعدة
                buy_conditions.append(df['vpt_signal'].iloc[i] == 1)
                
                # 2. تقاطع المتوسطات صاعد
                ma_cross_up = (df['price_ma_fast'].iloc[i] > df['price_ma_slow'].iloc[i] and 
                              df['price_ma_fast'].iloc[i-1] <= df['price_ma_slow'].iloc[i-1])
                buy_conditions.append(ma_cross_up)
                
                # 3. حجم مرتفع
                buy_conditions.append(df['volume_ratio'].iloc[i] >= self.params['volume_threshold'])
                
                # 4. زخم إيجابي
                buy_conditions.append(df['momentum'].iloc[i] > 0)
                
                # 5. قوة اتجاه كافية
                buy_conditions.append(df['trend_strength'].iloc[i] >= self.params['trend_strength_min'])
                
                # تنفيذ إشارة الشراء (3 من 5 شروط)
                if sum(buy_conditions) >= 3:
                    df.loc[df.index[i], 'buy_signal'] = 1
                    current_price = df['close'].iloc[i]
                    atr_value = df['atr'].iloc[i]
                    df.loc[df.index[i], 'stop_loss'] = current_price - (self.params['stop_loss_atr'] * atr_value)
                    df.loc[df.index[i], 'take_profit'] = current_price + (self.params['take_profit_atr'] * atr_value)
                
                # شروط البيع
                sell_conditions = []
                
                # 1. إشارة VPT هابطة
                sell_conditions.append(df['vpt_signal'].iloc[i] == -1)
                
                # 2. تقاطع المتوسطات هابط
                ma_cross_down = (df['price_ma_fast'].iloc[i] < df['price_ma_slow'].iloc[i] and 
                                df['price_ma_fast'].iloc[i-1] >= df['price_ma_slow'].iloc[i-1])
                sell_conditions.append(ma_cross_down)
                
                # 3. حجم مرتفع
                sell_conditions.append(df['volume_ratio'].iloc[i] >= self.params['volume_threshold'])
                
                # 4. زخم سلبي
                sell_conditions.append(df['momentum'].iloc[i] < 0)
                
                # 5. قوة اتجاه كافية
                sell_conditions.append(df['trend_strength'].iloc[i] >= self.params['trend_strength_min'])
                
                # تنفيذ إشارة البيع (3 من 5 شروط)
                if sum(sell_conditions) >= 3:
                    df.loc[df.index[i], 'sell_signal'] = 1
                    current_price = df['close'].iloc[i]
                    atr_value = df['atr'].iloc[i]
                    df.loc[df.index[i], 'stop_loss'] = current_price + (self.params['stop_loss_atr'] * atr_value)
                    df.loc[df.index[i], 'take_profit'] = current_price - (self.params['take_profit_atr'] * atr_value)
            
            return df
            
        except Exception as e:
            logger.error(f"خطأ في توليد الإشارات: {str(e)}")
            return df
