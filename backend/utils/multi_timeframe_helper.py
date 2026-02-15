"""
Multi-Timeframe Helper - مساعد تحليل الأطر الزمنية المتعددة
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class MultiTimeframeAnalyzer:
    """
    محلل الأطر الزمنية المتعددة
    يساعد في تحليل البيانات عبر أطر زمنية مختلفة
    """
    
    def __init__(self):
        """تهيئة المحلل"""
        self.timeframes = ['5m', '15m', '1h', '4h', '1d']
        self.logger = logger
    
    def analyze_multiple_timeframes(self, data: Dict[str, pd.DataFrame], 
                                    symbol: str) -> Dict[str, Any]:
        """
        تحليل عبر أطر زمنية متعددة
        
        Args:
            data: قاموس يحتوي على DataFrames لكل إطار زمني
            symbol: رمز العملة
            
        Returns:
            نتائج التحليل
        """
        try:
            results = {
                'symbol': symbol,
                'timeframes': {},
                'consensus': None
            }
            
            for timeframe, df in data.items():
                if df is None or df.empty:
                    continue
                    
                results['timeframes'][timeframe] = {
                    'trend': self._detect_trend(df),
                    'strength': self._calculate_strength(df),
                    'volume': self._analyze_volume(df)
                }
            
            # تحديد الإجماع
            results['consensus'] = self._determine_consensus(results['timeframes'])
            
            return results
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل الأطر الزمنية المتعددة: {e}")
            return {'error': str(e)}
    
    def _detect_trend(self, df: pd.DataFrame) -> str:
        """
        اكتشاف الاتجاه
        
        Returns:
            'bullish', 'bearish', أو 'neutral'
        """
        try:
            if len(df) < 20:
                return 'neutral'
            
            # استخدام المتوسطات المتحركة
            sma_20 = df['close'].rolling(window=20).mean()
            sma_50 = df['close'].rolling(window=50).mean() if len(df) >= 50 else sma_20
            
            current_price = df['close'].iloc[-1]
            sma_20_current = sma_20.iloc[-1]
            sma_50_current = sma_50.iloc[-1]
            
            if current_price > sma_20_current > sma_50_current:
                return 'bullish'
            elif current_price < sma_20_current < sma_50_current:
                return 'bearish'
            else:
                return 'neutral'
                
        except Exception:
            return 'neutral'
    
    def _calculate_strength(self, df: pd.DataFrame) -> float:
        """
        حساب قوة الاتجاه
        
        Returns:
            قيمة بين 0 و 1
        """
        try:
            if len(df) < 14:
                return 0.5
            
            # استخدام ADX (Average Directional Index) مبسط
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.rolling(window=14).mean()
            
            # تطبيع القيمة
            strength = min(1.0, atr.iloc[-1] / df['close'].iloc[-1] * 10)
            
            return strength
            
        except Exception:
            return 0.5
    
    def _analyze_volume(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        تحليل الحجم
        
        Returns:
            معلومات عن الحجم
        """
        try:
            if len(df) < 20 or 'volume' not in df.columns:
                return {'trend': 'neutral', 'ratio': 1.0}
            
            avg_volume = df['volume'].rolling(window=20).mean().iloc[-1]
            current_volume = df['volume'].iloc[-1]
            
            ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            return {
                'trend': 'increasing' if ratio > 1.2 else 'decreasing' if ratio < 0.8 else 'neutral',
                'ratio': ratio
            }
            
        except Exception:
            return {'trend': 'neutral', 'ratio': 1.0}
    
    def _determine_consensus(self, timeframes_data: Dict[str, Dict]) -> str:
        """
        تحديد الإجماع بين الأطر الزمنية
        
        Returns:
            'bullish', 'bearish', أو 'neutral'
        """
        try:
            if not timeframes_data:
                return 'neutral'
            
            bullish_count = 0
            bearish_count = 0
            total = 0
            
            for tf_data in timeframes_data.values():
                if 'trend' in tf_data:
                    total += 1
                    if tf_data['trend'] == 'bullish':
                        bullish_count += 1
                    elif tf_data['trend'] == 'bearish':
                        bearish_count += 1
            
            if total == 0:
                return 'neutral'
            
            bullish_ratio = bullish_count / total
            bearish_ratio = bearish_count / total
            
            if bullish_ratio >= 0.6:
                return 'bullish'
            elif bearish_ratio >= 0.6:
                return 'bearish'
            else:
                return 'neutral'
                
        except Exception:
            return 'neutral'
    
    def get_timeframe_weight(self, timeframe: str) -> float:
        """
        الحصول على وزن الإطار الزمني
        الأطر الزمنية الأكبر لها وزن أكبر
        
        Returns:
            وزن بين 0 و 1
        """
        weights = {
            '1m': 0.1,
            '5m': 0.2,
            '15m': 0.3,
            '1h': 0.5,
            '4h': 0.7,
            '1d': 1.0
        }
        
        return weights.get(timeframe, 0.5)
