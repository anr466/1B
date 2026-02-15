"""
Liquidity Analyzer - محلل السيولة
يقيم سيولة العملة لتجنب العملات ذات السيولة المنخفضة
"""

import pandas as pd
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class LiquidityAnalyzer:
    """
    تحليل سيولة العملة
    - حجم التداول اليومي
    - قيمة التداول بالدولار
    - تصنيف السيولة
    """
    
    def __init__(self):
        self.logger = logger
        
        # عتبات السيولة (بالدولار)
        self.excellent_threshold = 100_000_000  # $100M+
        self.good_threshold = 50_000_000        # $50M+
        self.fair_threshold = 10_000_000        # $10M+
    
    def analyze(self, symbol: str, df: pd.DataFrame) -> Dict:
        """
        تحليل سيولة العملة
        
        Args:
            symbol: رمز العملة
            df: DataFrame مع OHLCV
        
        Returns:
            Dict مع تقييم السيولة
        """
        try:
            if df is None or len(df) < 30:
                return self._get_poor_liquidity()
            
            # حساب متوسط حجم التداول اليومي (30 يوم)
            avg_volume = df['volume'].rolling(30).mean().iloc[-1]
            
            # حساب القيمة بالدولار
            avg_price = df['close'].rolling(30).mean().iloc[-1]
            avg_value_usd = avg_volume * avg_price
            
            # تصنيف السيولة
            score, multiplier = self._classify_liquidity(avg_value_usd)
            
            return {
                'symbol': symbol,
                'avg_daily_volume': float(avg_volume),
                'avg_daily_value_usd': float(avg_value_usd),
                'liquidity_score': score,
                'position_size_multiplier': multiplier,
                'is_tradeable': multiplier > 0,
                'recommendation': self._get_recommendation(score)
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing liquidity for {symbol}: {e}")
            return self._get_poor_liquidity()
    
    def _classify_liquidity(self, avg_value_usd: float) -> tuple:
        """
        تصنيف السيولة
        
        Returns:
            (score, position_size_multiplier)
        """
        if avg_value_usd >= self.excellent_threshold:
            return 'EXCELLENT', 1.0
        elif avg_value_usd >= self.good_threshold:
            return 'GOOD', 0.8
        elif avg_value_usd >= self.fair_threshold:
            return 'FAIR', 0.5
        else:
            return 'POOR', 0.0  # لا نتداول
    
    def _get_recommendation(self, score: str) -> str:
        """توصية بناءً على السيولة"""
        recommendations = {
            'EXCELLENT': 'سيولة ممتازة - مناسب للتداول بجميع الأحجام',
            'GOOD': 'سيولة جيدة - مناسب للتداول بحجم متوسط',
            'FAIR': 'سيولة مقبولة - استخدم حجم صغير فقط',
            'POOR': 'سيولة ضعيفة - تجنب التداول'
        }
        return recommendations.get(score, 'غير معروف')
    
    def _get_poor_liquidity(self) -> Dict:
        """تحليل افتراضي للسيولة الضعيفة"""
        return {
            'symbol': 'UNKNOWN',
            'avg_daily_volume': 0,
            'avg_daily_value_usd': 0,
            'liquidity_score': 'POOR',
            'position_size_multiplier': 0.0,
            'is_tradeable': False,
            'recommendation': 'بيانات غير كافية - تجنب التداول'
        }
