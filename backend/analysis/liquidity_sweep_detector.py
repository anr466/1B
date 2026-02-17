#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Liquidity Sweep Detector - كاشف كنس السيولة
============================================

يكشف عمليات كنس السيولة والفخاخ (Fakeouts) التي يستخدمها Smart Money:
- فخ الاختراق الوهمي (Fakeout Trap)  
- كنس القمم المتساوية (Equal Highs Sweep)
- كنس السيولة مع ارتداد سريع
- تحليل الحجم لتأكيد الكنس

من استراتيجية السيولة: "الحيتان تدفع السعر إلى مناطق سيولة لتفعيل أوامر الإيقاف، ثم تعكس الاتجاه"

Phase 1 - Week 1-2 من خطة Precision Scalping v8.0
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from .liquidity_zones_detector import LiquidityZone

logger = logging.getLogger(__name__)


class LiquiditySweep:
    """فئة تمثل عملية كنس سيولة واحدة"""
    
    def __init__(self, sweep_type: str, trigger_price: float, sweep_price: float,
                 reversal_price: float, volume: float, timestamp: datetime, 
                 strength: float, pattern: str):
        self.sweep_type = sweep_type          # 'bullish_sweep', 'bearish_sweep'
        self.trigger_price = trigger_price    # السعر المستهدف 
        self.sweep_price = sweep_price        # أعلى/أقل نقطة في الكنس
        self.reversal_price = reversal_price  # سعر الارتداد
        self.volume = volume                  # حجم التداول
        self.timestamp = timestamp
        self.strength = strength              # قوة الكنس (0-100)
        self.pattern = pattern               # نوع النمط
        self.success_rate = 0                # نسبة نجاح التنبؤ
        
    def calculate_sweep_distance(self) -> float:
        """حساب مسافة الكنس"""
        return abs(self.sweep_price - self.trigger_price) / self.trigger_price * 100
        
    def calculate_reversal_strength(self) -> float:
        """حساب قوة الارتداد"""
        return abs(self.reversal_price - self.sweep_price) / self.sweep_price * 100
        
    def __repr__(self):
        return f"LiquiditySweep({self.pattern}:{self.sweep_type} @ {self.sweep_price:.6f}, strength={self.strength:.1f})"


class LiquiditySweepDetector:
    """كاشف عمليات كنس السيولة المتقدم"""
    
    def __init__(self):
        self.logger = logger
        
        # إعدادات كشف الفخاخ
        self.fakeout_min_penetration = 0.001    # اختراق أدنى 0.1%
        self.fakeout_max_penetration = 0.005    # اختراق أقصى 0.5%
        self.fakeout_reversal_min = 0.002       # ارتداد أدنى 0.2%
        
        # إعدادات الحجم
        self.volume_spike_threshold = 1.5       # مضاعف الحجم المطلوب
        self.volume_confirmation_period = 3     # فترة تأكيد الحجم
        
        # إعدادات الوقت
        self.max_sweep_duration = 5             # الحد الأقصى لمدة الكنس (شموع)
        self.min_reversal_speed = 2             # سرعة الارتداد المطلوبة (شموع)
        
    def detect_liquidity_sweeps(self, df: pd.DataFrame, 
                               liquidity_zones: List[LiquidityZone]) -> List[LiquiditySweep]:
        """
        كشف عمليات كنس السيولة
        
        Args:
            df: بيانات السعر (5M أو 15M)
            liquidity_zones: مناطق السيولة المكتشفة
            
        Returns:
            قائمة بعمليات الكنس المكتشفة
        """
        self.logger.info("🕵️ كشف عمليات كنس السيولة...")
        
        sweeps = []
        
        try:
            # كشف الفخاخ العامة
            general_fakeouts = self._detect_general_fakeouts(df)
            sweeps.extend(general_fakeouts)
            
            # كشف كنس المستويات المحددة
            zone_sweeps = self._detect_zone_sweeps(df, liquidity_zones)
            sweeps.extend(zone_sweeps)
            
            # كشف كنس القمم/القيعان المتساوية
            equal_level_sweeps = self._detect_equal_level_sweeps(df)
            sweeps.extend(equal_level_sweeps)
            
            # تنظيف وترتيب النتائج
            sweeps = self._filter_and_rank_sweeps(sweeps)
            
            self.logger.info(f"✅ تم العثور على {len(sweeps)} عملية كنس سيولة")
            return sweeps
            
        except Exception as e:
            self.logger.error(f"خطأ في كشف كنس السيولة: {e}")
            return []
    
    def _detect_general_fakeouts(self, df: pd.DataFrame) -> List[LiquiditySweep]:
        """كشف الفخاخ العامة في البيانات"""
        fakeouts = []
        
        if len(df) < 10:
            return fakeouts
            
        try:
            for i in range(5, len(df) - 2):
                # البحث عن فخ صاعد (كسر مؤقت للأعلى ثم هبوط)
                bullish_fakeout = self._check_bullish_fakeout(df, i)
                if bullish_fakeout:
                    fakeouts.append(bullish_fakeout)
                
                # البحث عن فخ هابط (كسر مؤقت للأسفل ثم صعود)
                bearish_fakeout = self._check_bearish_fakeout(df, i)
                if bearish_fakeout:
                    fakeouts.append(bearish_fakeout)
                    
            return fakeouts
            
        except Exception as e:
            self.logger.debug(f"خطأ في كشف الفخاخ العامة: {e}")
            return []
    
    def _check_bullish_fakeout(self, df: pd.DataFrame, index: int) -> Optional[LiquiditySweep]:
        """فحص فخ صاعد في نقطة محددة"""
        try:
            current_candle = df.iloc[index]
            
            # البحث عن أعلى نقطة في الفترة السابقة
            lookback_highs = df['high'].iloc[max(0, index-10):index]
            if len(lookback_highs) == 0:
                return None
                
            resistance_level = lookback_highs.max()
            
            # شروط الفخ الصاعد
            conditions = []
            
            # 1. اختراق المقاومة
            penetration = (current_candle['high'] - resistance_level) / resistance_level
            if self.fakeout_min_penetration <= penetration <= self.fakeout_max_penetration:
                conditions.append('penetration_ok')
            
            # 2. إغلاق أسفل المستوى
            if current_candle['close'] < resistance_level:
                conditions.append('close_below')
            
            # 3. حجم مرتفع
            avg_volume = df['volume'].iloc[max(0, index-10):index].mean()
            if current_candle['volume'] > avg_volume * self.volume_spike_threshold:
                conditions.append('high_volume')
            
            # 4. فحص الارتداد في الشموع التالية
            if index + 2 < len(df):
                next_candles = df.iloc[index+1:index+3]
                lowest_after = next_candles['low'].min()
                
                reversal_strength = (current_candle['close'] - lowest_after) / current_candle['close']
                if reversal_strength >= self.fakeout_reversal_min:
                    conditions.append('strong_reversal')
            
            # إنشاء الفخ إذا تحققت الشروط
            if len(conditions) >= 3:  # 3 من 4 شروط
                strength = len(conditions) * 20 + penetration * 1000  # تسجيل القوة
                
                return LiquiditySweep(
                    sweep_type='bearish_sweep',  # فخ صاعد يؤدي لهبوط
                    trigger_price=resistance_level,
                    sweep_price=current_candle['high'],
                    reversal_price=current_candle['close'],
                    volume=current_candle['volume'],
                    timestamp=current_candle.name,
                    strength=min(100, strength),
                    pattern='bullish_fakeout'
                )
                
            return None
            
        except Exception as e:
            self.logger.debug(f"خطأ في فحص الفخ الصاعد: {e}")
            return None
    
    def _check_bearish_fakeout(self, df: pd.DataFrame, index: int) -> Optional[LiquiditySweep]:
        """فحص فخ هابط في نقطة محددة"""
        try:
            current_candle = df.iloc[index]
            
            # البحث عن أقل نقطة في الفترة السابقة
            lookback_lows = df['low'].iloc[max(0, index-10):index]
            if len(lookback_lows) == 0:
                return None
                
            support_level = lookback_lows.min()
            
            # شروط الفخ الهابط
            conditions = []
            
            # 1. اختراق الدعم
            penetration = (support_level - current_candle['low']) / support_level
            if self.fakeout_min_penetration <= penetration <= self.fakeout_max_penetration:
                conditions.append('penetration_ok')
            
            # 2. إغلاق فوق المستوى
            if current_candle['close'] > support_level:
                conditions.append('close_above')
            
            # 3. حجم مرتفع
            avg_volume = df['volume'].iloc[max(0, index-10):index].mean()
            if current_candle['volume'] > avg_volume * self.volume_spike_threshold:
                conditions.append('high_volume')
            
            # 4. فحص الارتداد في الشموع التالية
            if index + 2 < len(df):
                next_candles = df.iloc[index+1:index+3]
                highest_after = next_candles['high'].max()
                
                reversal_strength = (highest_after - current_candle['close']) / current_candle['close']
                if reversal_strength >= self.fakeout_reversal_min:
                    conditions.append('strong_reversal')
            
            # إنشاء الفخ إذا تحققت الشروط
            if len(conditions) >= 3:  # 3 من 4 شروط
                strength = len(conditions) * 20 + penetration * 1000  # تسجيل القوة
                
                return LiquiditySweep(
                    sweep_type='bullish_sweep',  # فخ هابط يؤدي لصعود
                    trigger_price=support_level,
                    sweep_price=current_candle['low'],
                    reversal_price=current_candle['close'],
                    volume=current_candle['volume'],
                    timestamp=current_candle.name,
                    strength=min(100, strength),
                    pattern='bearish_fakeout'
                )
                
            return None
            
        except Exception as e:
            self.logger.debug(f"خطأ في فحص الفخ الهابط: {e}")
            return None
    
    def _detect_zone_sweeps(self, df: pd.DataFrame, 
                           liquidity_zones: List[LiquidityZone]) -> List[LiquiditySweep]:
        """كشف كنس مناطق السيولة المحددة"""
        sweeps = []
        
        try:
            for zone in liquidity_zones:
                zone_sweeps = self._check_zone_sweep(df, zone)
                sweeps.extend(zone_sweeps)
                
            return sweeps
            
        except Exception as e:
            self.logger.debug(f"خطأ في كشف كنس المناطق: {e}")
            return []
    
    def _check_zone_sweep(self, df: pd.DataFrame, zone: LiquidityZone) -> List[LiquiditySweep]:
        """فحص كنس منطقة سيولة محددة"""
        sweeps = []
        
        try:
            zone_price = zone.price
            tolerance = 0.003  # تسامح 0.3%
            
            for i in range(5, len(df)):
                current_candle = df.iloc[i]
                
                # فحص كنس منطقة مقاومة
                if zone.zone_type in ['resistance', 'pivot']:
                    if (current_candle['high'] > zone_price * (1 + tolerance/2) and
                        current_candle['close'] < zone_price):
                        
                        # تأكيد بالحجم
                        avg_volume = df['volume'].iloc[max(0, i-5):i].mean()
                        if current_candle['volume'] > avg_volume * 1.3:
                            
                            sweep = LiquiditySweep(
                                sweep_type='bearish_sweep',
                                trigger_price=zone_price,
                                sweep_price=current_candle['high'],
                                reversal_price=current_candle['close'],
                                volume=current_candle['volume'],
                                timestamp=current_candle.name,
                                strength=zone.strength * 0.8,  # قوة نسبية للمنطقة
                                pattern=f'zone_sweep_{zone.source}'
                            )
                            sweeps.append(sweep)
                
                # فحص كنس منطقة دعم
                elif zone.zone_type == 'support':
                    if (current_candle['low'] < zone_price * (1 - tolerance/2) and
                        current_candle['close'] > zone_price):
                        
                        # تأكيد بالحجم
                        avg_volume = df['volume'].iloc[max(0, i-5):i].mean()
                        if current_candle['volume'] > avg_volume * 1.3:
                            
                            sweep = LiquiditySweep(
                                sweep_type='bullish_sweep',
                                trigger_price=zone_price,
                                sweep_price=current_candle['low'],
                                reversal_price=current_candle['close'],
                                volume=current_candle['volume'],
                                timestamp=current_candle.name,
                                strength=zone.strength * 0.8,
                                pattern=f'zone_sweep_{zone.source}'
                            )
                            sweeps.append(sweep)
            
            return sweeps
            
        except Exception as e:
            self.logger.debug(f"خطأ في فحص كنس المنطقة: {e}")
            return []
    
    def _detect_equal_level_sweeps(self, df: pd.DataFrame) -> List[LiquiditySweep]:
        """كشف كنس القمم/القيعان المتساوية"""
        sweeps = []
        
        try:
            # البحث عن القمم المتساوية
            equal_highs = self._find_equal_highs(df)
            for level_price, indices in equal_highs.items():
                level_sweeps = self._check_equal_high_sweep(df, level_price, indices)
                sweeps.extend(level_sweeps)
            
            # البحث عن القيعان المتساوية
            equal_lows = self._find_equal_lows(df)
            for level_price, indices in equal_lows.items():
                level_sweeps = self._check_equal_low_sweep(df, level_price, indices)
                sweeps.extend(level_sweeps)
            
            return sweeps
            
        except Exception as e:
            self.logger.debug(f"خطأ في كشف كنس المستويات المتساوية: {e}")
            return []
    
    def _find_equal_highs(self, df: pd.DataFrame, tolerance: float = 0.002) -> Dict[float, List[int]]:
        """البحث عن القمم المتساوية"""
        equal_highs = {}
        
        # استخراج القمم المحلية
        local_highs = []
        for i in range(3, len(df) - 3):
            if (df['high'].iloc[i] == df['high'].iloc[i-3:i+4].max()):
                local_highs.append((i, df['high'].iloc[i]))
        
        # تجميع القمم المتساوية
        for i, (idx1, price1) in enumerate(local_highs):
            for idx2, price2 in local_highs[i+1:]:
                if abs(price1 - price2) / price1 <= tolerance:
                    avg_price = (price1 + price2) / 2
                    if avg_price not in equal_highs:
                        equal_highs[avg_price] = []
                    equal_highs[avg_price].extend([idx1, idx2])
        
        # تنظيف النتائج
        cleaned_highs = {}
        for price, indices in equal_highs.items():
            unique_indices = list(set(indices))
            if len(unique_indices) >= 2:
                cleaned_highs[price] = unique_indices
                
        return cleaned_highs
    
    def _find_equal_lows(self, df: pd.DataFrame, tolerance: float = 0.002) -> Dict[float, List[int]]:
        """البحث عن القيعان المتساوية"""
        equal_lows = {}
        
        # استخراج القيعان المحلية
        local_lows = []
        for i in range(3, len(df) - 3):
            if (df['low'].iloc[i] == df['low'].iloc[i-3:i+4].min()):
                local_lows.append((i, df['low'].iloc[i]))
        
        # تجميع القيعان المتساوية
        for i, (idx1, price1) in enumerate(local_lows):
            for idx2, price2 in local_lows[i+1:]:
                if abs(price1 - price2) / price1 <= tolerance:
                    avg_price = (price1 + price2) / 2
                    if avg_price not in equal_lows:
                        equal_lows[avg_price] = []
                    equal_lows[avg_price].extend([idx1, idx2])
        
        # تنظيف النتائج
        cleaned_lows = {}
        for price, indices in equal_lows.items():
            unique_indices = list(set(indices))
            if len(unique_indices) >= 2:
                cleaned_lows[price] = unique_indices
                
        return cleaned_lows
    
    def _check_equal_high_sweep(self, df: pd.DataFrame, level_price: float, 
                               indices: List[int]) -> List[LiquiditySweep]:
        """فحص كنس القمم المتساوية"""
        sweeps = []
        
        try:
            # البحث عن كنس بعد آخر قمة
            last_peak_idx = max(indices)
            
            for i in range(last_peak_idx + 1, len(df)):
                current_candle = df.iloc[i]
                
                # شروط كنس القمم المتساوية
                if (current_candle['high'] > level_price * 1.001 and  # كسر 0.1%
                    current_candle['close'] < level_price * 0.999):   # إغلاق أسفل
                    
                    # تأكيد بالحجم
                    avg_volume = df['volume'].iloc[max(0, i-5):i].mean()
                    if current_candle['volume'] > avg_volume * 1.4:
                        
                        # قوة بناءً على عدد القمم المتساوية
                        strength = min(90, 60 + len(indices) * 10)
                        
                        sweep = LiquiditySweep(
                            sweep_type='bearish_sweep',
                            trigger_price=level_price,
                            sweep_price=current_candle['high'],
                            reversal_price=current_candle['close'],
                            volume=current_candle['volume'],
                            timestamp=current_candle.name,
                            strength=strength,
                            pattern='equal_highs_sweep'
                        )
                        sweeps.append(sweep)
                        break  # كنس واحد لكل مستوى
            
            return sweeps
            
        except Exception as e:
            self.logger.debug(f"خطأ في فحص كنس القمم المتساوية: {e}")
            return []
    
    def _check_equal_low_sweep(self, df: pd.DataFrame, level_price: float, 
                              indices: List[int]) -> List[LiquiditySweep]:
        """فحص كنس القيعان المتساوية"""
        sweeps = []
        
        try:
            # البحث عن كنس بعد آخر قاع
            last_trough_idx = max(indices)
            
            for i in range(last_trough_idx + 1, len(df)):
                current_candle = df.iloc[i]
                
                # شروط كنس القيعان المتساوية
                if (current_candle['low'] < level_price * 0.999 and   # كسر 0.1%
                    current_candle['close'] > level_price * 1.001):  # إغلاق فوق
                    
                    # تأكيد بالحجم
                    avg_volume = df['volume'].iloc[max(0, i-5):i].mean()
                    if current_candle['volume'] > avg_volume * 1.4:
                        
                        # قوة بناءً على عدد القيعان المتساوية
                        strength = min(90, 60 + len(indices) * 10)
                        
                        sweep = LiquiditySweep(
                            sweep_type='bullish_sweep',
                            trigger_price=level_price,
                            sweep_price=current_candle['low'],
                            reversal_price=current_candle['close'],
                            volume=current_candle['volume'],
                            timestamp=current_candle.name,
                            strength=strength,
                            pattern='equal_lows_sweep'
                        )
                        sweeps.append(sweep)
                        break  # كنس واحد لكل مستوى
            
            return sweeps
            
        except Exception as e:
            self.logger.debug(f"خطأ في فحص كنس القيعان المتساوية: {e}")
            return []
    
    def _filter_and_rank_sweeps(self, sweeps: List[LiquiditySweep]) -> List[LiquiditySweep]:
        """تصفية وترتيب عمليات الكنس"""
        try:
            # إزالة المتكررة
            unique_sweeps = []
            seen_timestamps = set()
            
            for sweep in sweeps:
                if sweep.timestamp not in seen_timestamps:
                    unique_sweeps.append(sweep)
                    seen_timestamps.add(sweep.timestamp)
            
            # ترتيب حسب القوة والوقت
            unique_sweeps.sort(key=lambda s: (s.strength, s.timestamp), reverse=True)
            
            # الاحتفاظ بأفضل النتائج
            return unique_sweeps[:20]  # أفضل 20 عملية كنس
            
        except Exception as e:
            self.logger.debug(f"خطأ في تصفية الكنس: {e}")
            return sweeps[:20]  # احتياطي
    
    def analyze_sweep_patterns(self, sweeps: List[LiquiditySweep]) -> Dict:
        """تحليل أنماط الكنس"""
        analysis = {
            'total_sweeps': len(sweeps),
            'by_type': {},
            'by_pattern': {},
            'recent_sweeps': [],
            'strongest_sweeps': [],
            'success_rate_estimate': 0
        }
        
        try:
            # تصنيف حسب النوع
            for sweep in sweeps:
                sweep_type = sweep.sweep_type
                pattern = sweep.pattern
                
                if sweep_type not in analysis['by_type']:
                    analysis['by_type'][sweep_type] = 0
                analysis['by_type'][sweep_type] += 1
                
                if pattern not in analysis['by_pattern']:
                    analysis['by_pattern'][pattern] = 0
                analysis['by_pattern'][pattern] += 1
            
            # أحدث العمليات (آخر 24 ساعة)
            now = datetime.now()
            recent_threshold = now - timedelta(hours=24)
            
            analysis['recent_sweeps'] = [
                s for s in sweeps 
                if isinstance(s.timestamp, datetime) and s.timestamp > recent_threshold
            ]
            
            # أقوى العمليات
            analysis['strongest_sweeps'] = sorted(sweeps, key=lambda s: s.strength, reverse=True)[:5]
            
            # تقدير نسبة النجاح
            if sweeps:
                avg_strength = sum(s.strength for s in sweeps) / len(sweeps)
                analysis['success_rate_estimate'] = min(95, avg_strength * 0.8)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل أنماط الكنس: {e}")
            return analysis
