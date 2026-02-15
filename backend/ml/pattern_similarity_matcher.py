#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pattern Similarity Matcher - قياس تشابه الأنماط
يحسب درجة التشابه بين النمط الحالي والنمط المرجعي من Backtesting
"""

import logging
from typing import Dict, List, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


class PatternSimilarityMatcher:
    """
    قياس تشابه النمط الحالي مع النمط الناجح من Backtesting
    """
    
    def __init__(self):
        # أوزان مكونات التشابه
        self.weights = {
            'price_action': 0.25,
            'volume_profile': 0.20,
            'indicators': 0.30,
            'market_structure': 0.25
        }
        
        logger.info("✅ تم تهيئة Pattern Similarity Matcher")
    
    def calculate_similarity(self, 
                            current_market: Dict[str, Any],
                            reference_pattern: Dict[str, Any]) -> float:
        """
        حساب نسبة التشابه الإجمالية
        
        Args:
            current_market: بيانات السوق الحالية
            reference_pattern: النمط المرجعي من Backtesting
            
        Returns:
            float: درجة التشابه (0.0 - 1.0)
        """
        try:
            similarity_score = 0.0
            
            # 1. Price Action (حركة السعر)
            if 'price_data' in current_market and 'price_data' in reference_pattern:
                price_similarity = self._compare_price_action(
                    current_market['price_data'],
                    reference_pattern['price_data']
                )
                similarity_score += price_similarity * self.weights['price_action']
            
            # 2. Volume Profile (حجم التداول)
            if 'volume' in current_market and 'volume' in reference_pattern:
                volume_similarity = self._compare_volume(
                    current_market['volume'],
                    reference_pattern['volume']
                )
                similarity_score += volume_similarity * self.weights['volume_profile']
            
            # 3. Technical Indicators (المؤشرات الفنية)
            if 'indicators' in current_market and 'indicators' in reference_pattern:
                indicator_similarity = self._compare_indicators(
                    current_market['indicators'],
                    reference_pattern['indicators']
                )
                similarity_score += indicator_similarity * self.weights['indicators']
            
            # 4. Market Structure (بنية السوق)
            if 'trend' in current_market and 'trend' in reference_pattern:
                structure_similarity = self._compare_structure(
                    current_market['trend'],
                    reference_pattern['trend']
                )
                similarity_score += structure_similarity * self.weights['market_structure']
            
            return min(1.0, max(0.0, similarity_score))
            
        except Exception as e:
            logger.error(f"خطأ في حساب التشابه: {e}")
            return 0.5  # قيمة افتراضية متوسطة
    
    def _compare_price_action(self, current: Dict, reference: Dict) -> float:
        """
        مقارنة حركة السعر
        """
        try:
            scores = []
            
            # اتجاه الحركة (صعود/هبوط)
            current_direction = current.get('direction', 0)
            ref_direction = reference.get('direction', 0)
            
            if current_direction * ref_direction > 0:  # نفس الاتجاه
                scores.append(1.0)
            else:
                scores.append(0.0)
            
            # تقلبات السعر (Volatility)
            current_volatility = current.get('volatility', 0)
            ref_volatility = reference.get('volatility', 0)
            
            if ref_volatility > 0:
                volatility_ratio = min(current_volatility, ref_volatility) / max(current_volatility, ref_volatility)
                scores.append(volatility_ratio)
            
            # نطاق السعر (Price Range)
            current_range = current.get('price_range', 0)
            ref_range = reference.get('price_range', 0)
            
            if ref_range > 0:
                range_ratio = min(current_range, ref_range) / max(current_range, ref_range)
                scores.append(range_ratio)
            
            return sum(scores) / len(scores) if scores else 0.5
            
        except Exception as e:
            logger.warning(f"خطأ في مقارنة Price Action: {e}")
            return 0.5
    
    def _compare_volume(self, current: float, reference: float) -> float:
        """
        مقارنة حجم التداول
        """
        try:
            if reference == 0:
                return 0.5
            
            # نسبة الحجم الحالي للمرجعي
            volume_ratio = current / reference
            
            # الأفضل أن يكون بين 0.7 - 1.3
            if 0.7 <= volume_ratio <= 1.3:
                return 1.0
            elif 0.5 <= volume_ratio <= 1.5:
                return 0.8
            elif 0.3 <= volume_ratio <= 2.0:
                return 0.6
            else:
                return 0.3
                
        except Exception as e:
            logger.warning(f"خطأ في مقارنة Volume: {e}")
            return 0.5
    
    def _compare_indicators(self, current: Dict, reference: Dict) -> float:
        """
        مقارنة المؤشرات الفنية
        """
        try:
            scores = []
            
            # RSI
            if 'rsi' in current and 'rsi' in reference:
                rsi_diff = abs(current['rsi'] - reference['rsi'])
                rsi_score = max(0, 1 - (rsi_diff / 100))
                scores.append(rsi_score)
            
            # MACD
            if 'macd' in current and 'macd' in reference:
                macd_similarity = self._check_macd_alignment(
                    current['macd'],
                    reference['macd']
                )
                scores.append(macd_similarity)
            
            # Moving Averages
            if 'ma' in current and 'ma' in reference:
                ma_similarity = self._check_ma_alignment(
                    current['ma'],
                    reference['ma']
                )
                scores.append(ma_similarity)
            
            # Bollinger Bands
            if 'bb' in current and 'bb' in reference:
                bb_similarity = self._compare_bb_position(
                    current['bb'],
                    reference['bb']
                )
                scores.append(bb_similarity)
            
            return sum(scores) / len(scores) if scores else 0.5
            
        except Exception as e:
            logger.warning(f"خطأ في مقارنة Indicators: {e}")
            return 0.5
    
    def _check_macd_alignment(self, current: Dict, reference: Dict) -> float:
        """
        فحص توافق MACD
        """
        try:
            # اتجاه MACD (إيجابي/سلبي)
            current_signal = 1 if current.get('value', 0) > 0 else -1
            ref_signal = 1 if reference.get('value', 0) > 0 else -1
            
            if current_signal == ref_signal:
                return 1.0
            else:
                return 0.3
                
        except Exception as e:
            return 0.5
    
    def _check_ma_alignment(self, current: Dict, reference: Dict) -> float:
        """
        فحص توافق المتوسطات المتحركة
        """
        try:
            # تحقق من نفس الترتيب (MA20 > MA50 > MA200)
            current_order = current.get('order', '')
            ref_order = reference.get('order', '')
            
            if current_order == ref_order:
                return 1.0
            else:
                return 0.4
                
        except Exception as e:
            return 0.5
    
    def _compare_bb_position(self, current: Dict, reference: Dict) -> float:
        """
        مقارنة موقع السعر في Bollinger Bands
        """
        try:
            # موقع السعر (upper/middle/lower)
            current_position = current.get('position', 'middle')
            ref_position = reference.get('position', 'middle')
            
            if current_position == ref_position:
                return 1.0
            elif abs(ord(current_position[0]) - ord(ref_position[0])) == 1:
                return 0.6  # مواقع متجاورة
            else:
                return 0.3
                
        except Exception as e:
            return 0.5
    
    def _compare_structure(self, current: str, reference: str) -> float:
        """
        مقارنة بنية السوق (trend, consolidation, reversal)
        """
        try:
            # تطابق تام
            if current == reference:
                return 1.0
            
            # تطابق جزئي
            compatible_structures = {
                'uptrend': ['consolidation'],
                'downtrend': ['consolidation'],
                'consolidation': ['uptrend', 'downtrend']
            }
            
            if reference in compatible_structures.get(current, []):
                return 0.6
            
            # لا تطابق
            return 0.3
            
        except Exception as e:
            logger.warning(f"خطأ في مقارنة Structure: {e}")
            return 0.5
    
    def get_detailed_similarity_report(self,
                                      current_market: Dict[str, Any],
                                      reference_pattern: Dict[str, Any]) -> Dict[str, Any]:
        """
        تقرير مفصل عن التشابه
        """
        report = {
            'overall_similarity': self.calculate_similarity(current_market, reference_pattern),
            'components': {}
        }
        
        # تفاصيل كل مكون
        if 'price_data' in current_market and 'price_data' in reference_pattern:
            report['components']['price_action'] = self._compare_price_action(
                current_market['price_data'],
                reference_pattern['price_data']
            )
        
        if 'volume' in current_market and 'volume' in reference_pattern:
            report['components']['volume'] = self._compare_volume(
                current_market['volume'],
                reference_pattern['volume']
            )
        
        if 'indicators' in current_market and 'indicators' in reference_pattern:
            report['components']['indicators'] = self._compare_indicators(
                current_market['indicators'],
                reference_pattern['indicators']
            )
        
        if 'trend' in current_market and 'trend' in reference_pattern:
            report['components']['market_structure'] = self._compare_structure(
                current_market['trend'],
                reference_pattern['trend']
            )
        
        return report


# Singleton instance
_similarity_matcher = None


def get_similarity_matcher() -> PatternSimilarityMatcher:
    """الحصول على مثيل واحد من المطابق"""
    global _similarity_matcher
    if _similarity_matcher is None:
        _similarity_matcher = PatternSimilarityMatcher()
    return _similarity_matcher
