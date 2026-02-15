"""
Volatility Analyzer - محلل التقلب المتقدم
تحليل شامل للتقلب: ATR, Historical, Parkinson, GARCH
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class VolatilityAnalyzer:
    """
    تحليل متقدم للتقلب
    يستخدم عدة طرق لحساب التقلب بدقة
    """
    
    def __init__(self):
        self.logger = logger
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        تحليل شامل للتقلب
        
        Returns:
            Dict مع جميع مقاييس التقلب
        """
        try:
            if df is None or len(df) < 20:
                return self._get_empty_analysis()
            
            # حساب مختلف أنواع التقلب
            atr = self._calculate_atr(df)
            atr_pct = atr / df['close'].iloc[-1]
            
            historical_vol = self._calculate_historical_volatility(df)
            parkinson_vol = self._calculate_parkinson_volatility(df)
            
            # تصنيف التقلب
            regime = self._classify_volatility(atr_pct, historical_vol)
            
            # حساب مضاعف ATR للـ SL/TP
            sl_multiplier = self._calculate_sl_multiplier(regime)
            tp_multiplier = self._calculate_tp_multiplier(regime)
            
            return {
                'atr': float(atr),
                'atr_pct': float(atr_pct),
                'historical_vol': float(historical_vol),
                'parkinson_vol': float(parkinson_vol),
                'regime': regime,
                'sl_multiplier': sl_multiplier,
                'tp_multiplier': tp_multiplier,
                'position_size_adjustment': self._get_position_adjustment(regime)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing volatility: {e}")
            return self._get_empty_analysis()
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """حساب ATR (Average True Range)"""
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            atr = tr.rolling(window=period).mean()
            return float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else 0
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR: {e}")
            return 0
    
    def _calculate_historical_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """
        حساب Historical Volatility (سنوي)
        """
        try:
            returns = df['close'].pct_change()
            hist_vol = returns.rolling(window=period).std() * np.sqrt(365)
            return float(hist_vol.iloc[-1]) if not pd.isna(hist_vol.iloc[-1]) else 0
            
        except Exception as e:
            self.logger.error(f"Error calculating historical volatility: {e}")
            return 0
    
    def _calculate_parkinson_volatility(self, df: pd.DataFrame, period: int = 20) -> float:
        """
        Parkinson Volatility - أدق من Historical
        يستخدم High-Low بدلاً من Close فقط
        """
        try:
            high = df['high']
            low = df['low']
            
            hl_ratio = np.log(high / low)
            parkinson = hl_ratio.rolling(window=period).apply(
                lambda x: np.sqrt((1 / (4 * len(x) * np.log(2))) * np.sum(x**2))
            ) * np.sqrt(365)
            
            return float(parkinson.iloc[-1]) if not pd.isna(parkinson.iloc[-1]) else 0
            
        except Exception as e:
            self.logger.error(f"Error calculating Parkinson volatility: {e}")
            return 0
    
    def _classify_volatility(self, atr_pct: float, hist_vol: float) -> str:
        """
        تصنيف مستوى التقلب
        
        Returns:
            'VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW', 'VERY_LOW'
        """
        # تصنيف بناءً على ATR %
        if atr_pct > 0.04:  # 4%+
            return 'VERY_HIGH'
        elif atr_pct > 0.025:  # 2.5-4%
            return 'HIGH'
        elif atr_pct > 0.015:  # 1.5-2.5%
            return 'MEDIUM'
        elif atr_pct > 0.008:  # 0.8-1.5%
            return 'LOW'
        else:  # < 0.8%
            return 'VERY_LOW'
    
    def _calculate_sl_multiplier(self, regime: str) -> float:
        """
        حساب مضاعف ATR لـ Stop Loss حسب التقلب
        
        تقلب عالي → SL أوسع (لتجنب الضرب المبكر)
        تقلب منخفض → SL أضيق (لحماية أفضل)
        """
        multiplier_map = {
            'VERY_HIGH': 2.5,
            'HIGH': 2.0,
            'MEDIUM': 1.75,
            'LOW': 1.5,
            'VERY_LOW': 1.25
        }
        return multiplier_map.get(regime, 2.0)
    
    def _calculate_tp_multiplier(self, regime: str) -> float:
        """
        حساب مضاعف ATR لـ Take Profit حسب التقلب
        
        تقلب عالي → TP أبعد (احتمال حركة كبيرة)
        تقلب منخفض → TP أقرب (حركة محدودة)
        """
        multiplier_map = {
            'VERY_HIGH': 5.0,
            'HIGH': 4.0,
            'MEDIUM': 3.5,
            'LOW': 3.0,
            'VERY_LOW': 2.5
        }
        return multiplier_map.get(regime, 3.5)
    
    def _get_position_adjustment(self, regime: str) -> float:
        """
        تعديل حجم الصفقة حسب التقلب
        
        تقلب عالي → حجم أصغر (تقليل مخاطرة)
        تقلب منخفض → حجم عادي
        
        Returns:
            multiplier (0.5 - 1.0)
        """
        adjustment_map = {
            'VERY_HIGH': 0.5,   # نصف الحجم
            'HIGH': 0.7,        # 70%
            'MEDIUM': 0.9,      # 90%
            'LOW': 1.0,         # حجم كامل
            'VERY_LOW': 1.0     # حجم كامل
        }
        return adjustment_map.get(regime, 0.9)
    
    def _get_empty_analysis(self) -> Dict:
        """تحليل فارغ عند عدم توفر البيانات"""
        return {
            'atr': 0,
            'atr_pct': 0,
            'historical_vol': 0,
            'parkinson_vol': 0,
            'regime': 'UNKNOWN',
            'sl_multiplier': 2.0,
            'tp_multiplier': 3.5,
            'position_size_adjustment': 0.9
        }
