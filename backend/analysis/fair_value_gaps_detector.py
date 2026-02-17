#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fair Value Gaps Detector - كاشف فجوات القيمة العادلة
====================================================

يكشف Fair Value Gaps (FVG) - المناطق غير المملوءة في السعر:
- فجوات صاعدة (Bullish FVG) - مناطق دعم
- فجوات هابطة (Bearish FVG) - مناطق مقاومة  
- تتبع حالة الملء للفجوات
- أولوية الفجوات حسب الحجم والعمر

من استراتيجية السيولة: "السوق يميل لملء الفجوات - مناطق عدم توازن قوية"

Phase 1 - Week 1-2 من خطة Precision Scalping v8.0
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class FairValueGap:
    """فئة تمثل فجوة قيمة عادلة واحدة"""
    
    def __init__(self, gap_type: str, top_price: float, bottom_price: float,
                 timestamp: datetime, strength: float, volume: float, 
                 formation_pattern: str):
        self.gap_type = gap_type              # 'bullish', 'bearish'
        self.top_price = top_price            # السعر العلوي للفجوة
        self.bottom_price = bottom_price      # السعر السفلي للفجوة
        self.timestamp = timestamp            # وقت التكوين
        self.strength = strength              # قوة الفجوة (0-100)
        self.volume = volume                  # حجم التداول عند التكوين
        self.formation_pattern = formation_pattern  # نمط التكوين
        
        # حالة الفجوة
        self.status = 'unfilled'             # 'unfilled', 'partial', 'filled'
        self.fill_percentage = 0.0           # نسبة الملء
        self.first_touch = None              # أول لمسة
        self.fill_timestamp = None           # وقت الملء الكامل
        self.retest_count = 0               # عدد إعادة الاختبار
        
    def get_midpoint(self) -> float:
        """نقطة الوسط للفجوة"""
        return (self.top_price + self.bottom_price) / 2
        
    def get_range_pct(self) -> float:
        """حجم الفجوة كنسبة مئوية"""
        return (self.top_price - self.bottom_price) / self.bottom_price * 100
        
    def update_fill_status(self, price: float, timestamp: datetime) -> str:
        """تحديث حالة ملء الفجوة"""
        # فحص ما إذا كان السعر داخل الفجوة
        if self.bottom_price <= price <= self.top_price:
            if self.first_touch is None:
                self.first_touch = timestamp
                
            # حساب نسبة الملء
            if self.gap_type == 'bullish':
                self.fill_percentage = (price - self.bottom_price) / (self.top_price - self.bottom_price) * 100
            else:
                self.fill_percentage = (self.top_price - price) / (self.top_price - self.bottom_price) * 100
                
            if self.fill_percentage >= 80:
                self.status = 'filled'
                if self.fill_timestamp is None:
                    self.fill_timestamp = timestamp
            elif self.fill_percentage >= 30:
                self.status = 'partial'
            
            return self.status
            
        # فحص إعادة الاختبار
        tolerance = 0.001  # تسامح 0.1%
        if (abs(price - self.bottom_price) / self.bottom_price <= tolerance or 
            abs(price - self.top_price) / self.top_price <= tolerance):
            self.retest_count += 1
            
        return self.status
        
    def get_age_hours(self) -> float:
        """عمر الفجوة بالساعات"""
        return (datetime.now() - self.timestamp).total_seconds() / 3600
        
    def is_active(self, max_age_hours: int = 72) -> bool:
        """هل الفجوة نشطة (غير مملوءة وجديدة نسبياً)"""
        return (self.status in ['unfilled', 'partial'] and 
                self.get_age_hours() < max_age_hours)
        
    def __repr__(self):
        return f"FVG({self.gap_type} @ {self.bottom_price:.6f}-{self.top_price:.6f}, {self.status}, strength={self.strength:.1f})"


class FairValueGapsDetector:
    """كاشف فجوات القيمة العادلة المتقدم"""
    
    def __init__(self):
        self.logger = logger
        
        # إعدادات كشف الفجوات
        self.min_gap_size_pct = 0.1          # حد أدنى لحجم الفجوة (0.1%)
        self.max_gap_size_pct = 2.0          # حد أقصى لحجم الفجوة (2.0%)
        self.min_gap_strength = 25           # قوة الفجوة الأدنى
        self.max_gap_age_hours = 72          # عمر الفجوة الأقصى
        
        # إعدادات التحقق
        self.formation_lookback = 3          # عدد الشموع للتحقق من التكوين
        self.volume_confirmation = 1.2       # مضاعف الحجم المطلوب
        
    def detect_fair_value_gaps(self, df: pd.DataFrame) -> List[FairValueGap]:
        """
        كشف فجوات القيمة العادلة
        
        Args:
            df: بيانات السعر والحجم (5M أو 15M مفضل)
            
        Returns:
            قائمة بالفجوات المكتشفة
        """
        self.logger.info("📊 كشف فجوات القيمة العادلة...")
        
        gaps = []
        
        try:
            # كشف الفجوات الصاعدة
            bullish_gaps = self._detect_bullish_fvgs(df)
            gaps.extend(bullish_gaps)
            
            # كشف الفجوات الهابطة
            bearish_gaps = self._detect_bearish_fvgs(df)
            gaps.extend(bearish_gaps)
            
            # تحديث حالات الفجوات
            gaps = self._update_gap_statuses(gaps, df)
            
            # تصفية وترتيب
            gaps = self._filter_and_rank_gaps(gaps)
            
            self.logger.info(f"✅ تم العثور على {len(gaps)} فجوة قيمة عادلة")
            return gaps
            
        except Exception as e:
            self.logger.error(f"خطأ في كشف فجوات القيمة العادلة: {e}")
            return []
    
    def _detect_bullish_fvgs(self, df: pd.DataFrame) -> List[FairValueGap]:
        """كشف الفجوات الصاعدة (Bullish FVG)"""
        gaps = []
        
        if len(df) < 5:
            return gaps
            
        try:
            for i in range(2, len(df) - 1):  # نحتاج 3 شموع للتحليل
                # نمط الفجوة الصاعدة: الشمعة الوسطى لا تلمس الشموع المجاورة
                candle_before = df.iloc[i-1]  # الشمعة السابقة
                candle_current = df.iloc[i]   # الشمعة الحالية (وسطى)
                candle_after = df.iloc[i+1]   # الشمعة التالية
                
                # شروط الفجوة الصاعدة:
                # 1. أقل نقطة في الشمعة التالية > أعلى نقطة في الشمعة السابقة
                if candle_after['low'] > candle_before['high']:
                    
                    # تحديد حدود الفجوة
                    gap_bottom = candle_before['high']
                    gap_top = candle_after['low']
                    
                    # التحقق من حجم الفجوة
                    gap_size_pct = (gap_top - gap_bottom) / gap_bottom * 100
                    
                    if self.min_gap_size_pct <= gap_size_pct <= self.max_gap_size_pct:
                        
                        # التحقق من قوة الحركة (حجم)
                        avg_volume = df['volume'].iloc[max(0, i-10):i].mean()
                        formation_volume = (candle_before['volume'] + candle_current['volume'] + candle_after['volume']) / 3
                        
                        volume_strength = formation_volume / avg_volume if avg_volume > 0 else 1
                        
                        # حساب قوة الفجوة
                        price_momentum = (candle_after['close'] - candle_before['open']) / candle_before['open'] * 100
                        gap_strength = min(100, 
                                         (gap_size_pct * 20) + 
                                         (volume_strength * 15) + 
                                         (abs(price_momentum) * 5))
                        
                        if gap_strength >= self.min_gap_strength:
                            # تحديد نمط التكوين
                            if (candle_before['close'] > candle_before['open'] and
                                candle_current['close'] > candle_current['open'] and
                                candle_after['close'] > candle_after['open']):
                                pattern = 'three_bullish_candles'
                            elif volume_strength > self.volume_confirmation:
                                pattern = 'high_volume_breakout'
                            else:
                                pattern = 'standard_bullish_fvg'
                            
                            gap = FairValueGap(
                                gap_type='bullish',
                                top_price=gap_top,
                                bottom_price=gap_bottom,
                                timestamp=candle_after.name,
                                strength=gap_strength,
                                volume=formation_volume,
                                formation_pattern=pattern
                            )
                            gaps.append(gap)
                            
            self.logger.debug(f"🔍 Bullish FVGs: {len(gaps)} فجوة")
            return gaps
            
        except Exception as e:
            self.logger.debug(f"خطأ في كشف الفجوات الصاعدة: {e}")
            return []
    
    def _detect_bearish_fvgs(self, df: pd.DataFrame) -> List[FairValueGap]:
        """كشف الفجوات الهابطة (Bearish FVG)"""
        gaps = []
        
        if len(df) < 5:
            return gaps
            
        try:
            for i in range(2, len(df) - 1):
                # نمط الفجوة الهابطة: الشمعة الوسطى لا تلمس الشموع المجاورة
                candle_before = df.iloc[i-1]  # الشمعة السابقة
                candle_current = df.iloc[i]   # الشمعة الحالية (وسطى)
                candle_after = df.iloc[i+1]   # الشمعة التالية
                
                # شروط الفجوة الهابطة:
                # 1. أعلى نقطة في الشمعة التالية < أقل نقطة في الشمعة السابقة
                if candle_after['high'] < candle_before['low']:
                    
                    # تحديد حدود الفجوة
                    gap_top = candle_before['low']
                    gap_bottom = candle_after['high']
                    
                    # التحقق من حجم الفجوة
                    gap_size_pct = (gap_top - gap_bottom) / gap_bottom * 100
                    
                    if self.min_gap_size_pct <= gap_size_pct <= self.max_gap_size_pct:
                        
                        # التحقق من قوة الحركة (حجم)
                        avg_volume = df['volume'].iloc[max(0, i-10):i].mean()
                        formation_volume = (candle_before['volume'] + candle_current['volume'] + candle_after['volume']) / 3
                        
                        volume_strength = formation_volume / avg_volume if avg_volume > 0 else 1
                        
                        # حساب قوة الفجوة
                        price_momentum = (candle_after['close'] - candle_before['open']) / candle_before['open'] * 100
                        gap_strength = min(100, 
                                         (gap_size_pct * 20) + 
                                         (volume_strength * 15) + 
                                         (abs(price_momentum) * 5))
                        
                        if gap_strength >= self.min_gap_strength:
                            # تحديد نمط التكوين
                            if (candle_before['close'] < candle_before['open'] and
                                candle_current['close'] < candle_current['open'] and
                                candle_after['close'] < candle_after['open']):
                                pattern = 'three_bearish_candles'
                            elif volume_strength > self.volume_confirmation:
                                pattern = 'high_volume_breakdown'
                            else:
                                pattern = 'standard_bearish_fvg'
                            
                            gap = FairValueGap(
                                gap_type='bearish',
                                top_price=gap_top,
                                bottom_price=gap_bottom,
                                timestamp=candle_after.name,
                                strength=gap_strength,
                                volume=formation_volume,
                                formation_pattern=pattern
                            )
                            gaps.append(gap)
                            
            self.logger.debug(f"🔍 Bearish FVGs: {len(gaps)} فجوة")
            return gaps
            
        except Exception as e:
            self.logger.debug(f"خطأ في كشف الفجوات الهابطة: {e}")
            return []
    
    def _update_gap_statuses(self, gaps: List[FairValueGap], df: pd.DataFrame) -> List[FairValueGap]:
        """تحديث حالات ملء الفجوات"""
        try:
            for gap in gaps:
                # فحص كل شمعة بعد تكوين الفجوة
                gap_formation_idx = None
                
                # العثور على فهرس تكوين الفجوة
                for idx, timestamp in enumerate(df.index):
                    if timestamp >= gap.timestamp:
                        gap_formation_idx = idx
                        break
                        
                if gap_formation_idx is not None:
                    # فحص الشموع بعد التكوين
                    for i in range(gap_formation_idx, len(df)):
                        candle = df.iloc[i]
                        
                        # تحديث حالة الملء
                        old_status = gap.status
                        new_status = gap.update_fill_status(candle['close'], candle.name)
                        
                        # فحص اختراق كامل للفجوة
                        if (gap.gap_type == 'bullish' and candle['low'] < gap.bottom_price) or \
                           (gap.gap_type == 'bearish' and candle['high'] > gap.top_price):
                            gap.status = 'filled'
                            gap.fill_percentage = 100
                            if gap.fill_timestamp is None:
                                gap.fill_timestamp = candle.name
                            break
                            
            return gaps
            
        except Exception as e:
            self.logger.debug(f"خطأ في تحديث حالات الفجوات: {e}")
            return gaps
    
    def _filter_and_rank_gaps(self, gaps: List[FairValueGap]) -> List[FairValueGap]:
        """تصفية وترتيب الفجوات"""
        try:
            if not gaps:
                return []
                
            # تصفية الفجوات القديمة جداً
            fresh_gaps = [gap for gap in gaps if gap.get_age_hours() <= self.max_gap_age_hours]
            
            # ترتيب حسب الأولوية: غير مملوءة > جزئي > قوة > حداثة
            def gap_priority(gap):
                status_priority = {'unfilled': 3, 'partial': 2, 'filled': 1}[gap.status]
                age_factor = max(0, 1 - (gap.get_age_hours() / self.max_gap_age_hours))
                return (status_priority, gap.strength, age_factor)
            
            sorted_gaps = sorted(fresh_gaps, key=gap_priority, reverse=True)
            
            # الاحتفاظ بأفضل الفجوات
            return sorted_gaps[:20]
            
        except Exception as e:
            self.logger.debug(f"خطأ في تصفية الفجوات: {e}")
            return gaps[:20]  # احتياطي
    
    def analyze_gap_patterns(self, gaps: List[FairValueGap]) -> Dict:
        """تحليل أنماط الفجوات"""
        analysis = {
            'total_gaps': len(gaps),
            'by_type': {'bullish': 0, 'bearish': 0},
            'by_status': {'unfilled': 0, 'partial': 0, 'filled': 0},
            'by_pattern': {},
            'active_gaps': [],
            'filled_gaps': [],
            'average_fill_time': 0,
            'fill_rate': 0
        }
        
        try:
            if not gaps:
                return analysis
                
            fill_times = []
            
            for gap in gaps:
                # تصنيف حسب النوع
                analysis['by_type'][gap.gap_type] += 1
                
                # تصنيف حسب الحالة
                analysis['by_status'][gap.status] += 1
                
                # تصنيف حسب النمط
                pattern = gap.formation_pattern
                if pattern not in analysis['by_pattern']:
                    analysis['by_pattern'][pattern] = 0
                analysis['by_pattern'][pattern] += 1
                
                # الفجوات النشطة
                if gap.is_active():
                    analysis['active_gaps'].append(gap)
                
                # الفجوات المملوءة
                if gap.status == 'filled':
                    analysis['filled_gaps'].append(gap)
                    if gap.fill_timestamp and isinstance(gap.timestamp, datetime) and isinstance(gap.fill_timestamp, datetime):
                        fill_time = (gap.fill_timestamp - gap.timestamp).total_seconds() / 3600
                        fill_times.append(fill_time)
            
            # متوسط وقت الملء
            if fill_times:
                analysis['average_fill_time'] = sum(fill_times) / len(fill_times)
                
            # معدل الملء
            if analysis['total_gaps'] > 0:
                analysis['fill_rate'] = (analysis['by_status']['filled'] / analysis['total_gaps']) * 100
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل أنماط الفجوات: {e}")
            return analysis
    
    def get_relevant_gaps(self, gaps: List[FairValueGap], 
                         current_price: float, 
                         distance_pct: float = 5.0) -> List[FairValueGap]:
        """الحصول على الفجوات ذات الصلة بالسعر الحالي"""
        relevant_gaps = []
        
        try:
            for gap in gaps:
                gap_midpoint = gap.get_midpoint()
                distance = abs(current_price - gap_midpoint) / current_price * 100
                
                if distance <= distance_pct and gap.is_active():
                    relevant_gaps.append(gap)
            
            # ترتيب حسب القرب والقوة
            relevant_gaps.sort(key=lambda g: (abs(current_price - g.get_midpoint()), -g.strength))
            
            return relevant_gaps
            
        except Exception as e:
            self.logger.debug(f"خطأ في الحصول على الفجوات ذات الصلة: {e}")
            return []
    
    def get_nearest_gaps(self, gaps: List[FairValueGap], 
                        current_price: float, 
                        direction: str = 'both') -> Dict:
        """الحصول على أقرب الفجوات في اتجاه محدد"""
        result = {
            'nearest_above': None,
            'nearest_below': None,
            'distance_above': float('inf'),
            'distance_below': float('inf')
        }
        
        try:
            active_gaps = [gap for gap in gaps if gap.is_active()]
            
            for gap in active_gaps:
                gap_midpoint = gap.get_midpoint()
                
                if gap_midpoint > current_price and direction in ['both', 'above']:
                    distance = gap_midpoint - current_price
                    if distance < result['distance_above']:
                        result['nearest_above'] = gap
                        result['distance_above'] = distance
                        
                elif gap_midpoint < current_price and direction in ['both', 'below']:
                    distance = current_price - gap_midpoint
                    if distance < result['distance_below']:
                        result['nearest_below'] = gap
                        result['distance_below'] = distance
                        
            return result
            
        except Exception as e:
            self.logger.debug(f"خطأ في الحصول على أقرب الفجوات: {e}")
            return result
    
    def generate_fvg_signals(self, gaps: List[FairValueGap], 
                           current_price: float, 
                           price_trend: str = 'neutral') -> Dict:
        """توليد إشارات تداول بناءً على الفجوات"""
        signals = {
            'primary_signal': 'NEUTRAL',
            'confidence': 0,
            'target_gaps': [],
            'support_gaps': [],
            'resistance_gaps': []
        }
        
        try:
            relevant_gaps = self.get_relevant_gaps(gaps, current_price, 3.0)
            nearest = self.get_nearest_gaps(gaps, current_price)
            
            support_gaps = [gap for gap in relevant_gaps if gap.gap_type == 'bullish' and gap.get_midpoint() < current_price]
            resistance_gaps = [gap for gap in relevant_gaps if gap.gap_type == 'bearish' and gap.get_midpoint() > current_price]
            
            signals['support_gaps'] = support_gaps
            signals['resistance_gaps'] = resistance_gaps
            
            # إشارات بناءً على اتجاه السعر والفجوات
            if price_trend == 'upward' and resistance_gaps:
                # اتجاه صاعد مع وجود فجوات مقاومة أعلاه
                nearest_resistance = min(resistance_gaps, key=lambda g: abs(g.get_midpoint() - current_price))
                signals['primary_signal'] = 'APPROACH_RESISTANCE_GAP'
                signals['confidence'] = min(80, nearest_resistance.strength)
                signals['target_gaps'] = [nearest_resistance]
                
            elif price_trend == 'downward' and support_gaps:
                # اتجاه هابط مع وجود فجوات دعم أسفله
                nearest_support = min(support_gaps, key=lambda g: abs(g.get_midpoint() - current_price))
                signals['primary_signal'] = 'APPROACH_SUPPORT_GAP'
                signals['confidence'] = min(80, nearest_support.strength)
                signals['target_gaps'] = [nearest_support]
                
            elif nearest['nearest_below'] and nearest['distance_below'] / current_price < 0.02:  # أقل من 2%
                # قريب من فجوة سفلية
                signals['primary_signal'] = 'NEAR_SUPPORT_GAP'
                signals['confidence'] = 60
                signals['target_gaps'] = [nearest['nearest_below']]
                
            elif nearest['nearest_above'] and nearest['distance_above'] / current_price < 0.02:  # أقل من 2%
                # قريب من فجوة علوية  
                signals['primary_signal'] = 'NEAR_RESISTANCE_GAP'
                signals['confidence'] = 60
                signals['target_gaps'] = [nearest['nearest_above']]
            
            return signals
            
        except Exception as e:
            self.logger.error(f"خطأ في توليد إشارات FVG: {e}")
            return signals
