#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Order Blocks Detector - كاشف كتل الأوامر المؤسسية
==================================================

يكشف Order Blocks - المناطق التي تراكمت فيها أوامر كبيرة من المؤسسات:
- تحديد مناطق تجميع الأوامر الكبيرة
- تحليل الحجم غير المتوازن
- كشف النشاط المؤسسي المخفي
- مناطق الدعم/المقاومة القوية

من استراتيجية السيولة: "البنوك والمؤسسات تترك آثار أوامرها في مناطق محددة"

Phase 1 - Week 1-2 من خطة Precision Scalping v8.0
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class OrderBlock:
    """فئة تمثل كتلة أوامر واحدة"""
    
    def __init__(self, block_type: str, price_range: Tuple[float, float], 
                 volume: float, timestamp: datetime, strength: float, 
                 block_source: str):
        self.block_type = block_type      # 'bullish', 'bearish'
        self.price_range = price_range    # (low, high) للمنطقة
        self.volume = volume              # إجمالي الحجم
        self.timestamp = timestamp
        self.strength = strength          # قوة الكتلة (0-100)
        self.block_source = block_source  # مصدر الكشف
        self.tests = 0                   # عدد اختبارات المنطقة
        self.broken = False              # هل انكسرت الكتلة
        self.last_test = None            # آخر اختبار
        
    def get_midpoint(self) -> float:
        """نقطة الوسط للكتلة"""
        return (self.price_range[0] + self.price_range[1]) / 2
        
    def get_range_pct(self) -> float:
        """نطاق الكتلة كنسبة مئوية"""
        return (self.price_range[1] - self.price_range[0]) / self.price_range[0] * 100
        
    def test_interaction(self, price: float, timestamp: datetime) -> bool:
        """اختبار تفاعل السعر مع الكتلة"""
        if self.price_range[0] <= price <= self.price_range[1]:
            self.tests += 1
            self.last_test = timestamp
            return True
        return False
        
    def __repr__(self):
        return f"OrderBlock({self.block_type} @ {self.price_range[0]:.6f}-{self.price_range[1]:.6f}, strength={self.strength:.1f})"


class OrderBlocksDetector:
    """كاشف كتل الأوامر المؤسسية المتقدم"""
    
    def __init__(self):
        self.logger = logger
        
        # إعدادات كشف كتل الأوامر
        self.min_volume_multiplier = 2.0     # مضاعف الحجم المطلوب
        self.min_block_strength = 30         # الحد الأدنى لقوة الكتلة
        self.max_block_age_hours = 48        # عمر الكتلة الأقصى
        
        # إعدادات تحليل الحجم
        self.volume_lookback = 20            # فترة حساب متوسط الحجم
        self.imbalance_threshold = 1.5       # عتبة عدم التوازن
        
        # إعدادات مناطق التراكم
        self.accumulation_min_candles = 3    # الحد الأدنى للشموع
        self.distribution_min_candles = 3    # الحد الأدنى للتوزيع
        
    def detect_order_blocks(self, df: pd.DataFrame) -> List[OrderBlock]:
        """
        كشف كتل الأوامر المؤسسية
        
        Args:
            df: بيانات السعر والحجم (5M أو 15M)
            
        Returns:
            قائمة بكتل الأوامر المكتشفة
        """
        self.logger.info("🏦 كشف كتل الأوامر المؤسسية...")
        
        order_blocks = []
        
        try:
            # كشف مناطق الحجم العالي
            high_volume_blocks = self._detect_high_volume_blocks(df)
            order_blocks.extend(high_volume_blocks)
            
            # كشف مناطق التراكم والتوزيع
            accumulation_blocks = self._detect_accumulation_zones(df)
            order_blocks.extend(accumulation_blocks)
            
            # كشف عدم التوازن في الحجم
            imbalance_blocks = self._detect_volume_imbalance(df)
            order_blocks.extend(imbalance_blocks)
            
            # تنظيف وترتيب النتائج
            order_blocks = self._filter_and_merge_blocks(order_blocks)
            
            self.logger.info(f"✅ تم العثور على {len(order_blocks)} كتلة أوامر")
            return order_blocks
            
        except Exception as e:
            self.logger.error(f"خطأ في كشف كتل الأوامر: {e}")
            return []
    
    def _detect_high_volume_blocks(self, df: pd.DataFrame) -> List[OrderBlock]:
        """كشف كتل الحجم العالي"""
        blocks = []
        
        if len(df) < self.volume_lookback:
            return blocks
            
        try:
            # حساب متوسط الحجم المتحرك
            df = df.copy()
            df['volume_avg'] = df['volume'].rolling(window=self.volume_lookback).mean()
            
            for i in range(self.volume_lookback, len(df)):
                current_candle = df.iloc[i]
                avg_volume = current_candle['volume_avg']
                
                # شرط الحجم العالي
                if current_candle['volume'] > avg_volume * self.min_volume_multiplier:
                    
                    # تحديد نوع الكتلة بناءً على اتجاه الشمعة
                    if current_candle['close'] > current_candle['open']:
                        # شمعة صاعدة = منطقة دعم (Bullish Order Block)
                        block_type = 'bullish'
                        price_range = (current_candle['low'], current_candle['open'])
                    else:
                        # شمعة هابطة = منطقة مقاومة (Bearish Order Block)
                        block_type = 'bearish'
                        price_range = (current_candle['close'], current_candle['high'])
                    
                    # حساب قوة الكتلة
                    volume_ratio = current_candle['volume'] / avg_volume
                    price_range_pct = (price_range[1] - price_range[0]) / price_range[0] * 100
                    
                    strength = min(100, (volume_ratio * 20) + (price_range_pct * 100))
                    
                    if strength >= self.min_block_strength:
                        block = OrderBlock(
                            block_type=block_type,
                            price_range=price_range,
                            volume=current_candle['volume'],
                            timestamp=current_candle.name,
                            strength=strength,
                            block_source='high_volume'
                        )
                        blocks.append(block)
                        
            self.logger.debug(f"🔍 High volume blocks: {len(blocks)} كتلة")
            return blocks
            
        except Exception as e:
            self.logger.debug(f"خطأ في كشف كتل الحجم العالي: {e}")
            return []
    
    def _detect_accumulation_zones(self, df: pd.DataFrame) -> List[OrderBlock]:
        """كشف مناطق التراكم والتوزيع"""
        blocks = []
        
        try:
            # البحث عن مناطق التداول الضيقة بحجم عالي
            for i in range(10, len(df) - 5):
                window = df.iloc[i-5:i+5]  # نافذة 10 شموع
                
                # حساب نطاق التداول
                price_range_high = window['high'].max()
                price_range_low = window['low'].min()
                range_pct = (price_range_high - price_range_low) / price_range_low * 100
                
                # إذا كان النطاق ضيق نسبياً
                if range_pct < 2.0:  # أقل من 2%
                    total_volume = window['volume'].sum()
                    avg_volume_before = df['volume'].iloc[max(0, i-20):i-5].mean()
                    
                    # حجم عالي في منطقة ضيقة = تراكم/توزيع
                    if total_volume > avg_volume_before * len(window) * 1.5:
                        
                        # تحديد نوع المنطقة بناءً على السعر الختام
                        close_start = window['close'].iloc[0]
                        close_end = window['close'].iloc[-1]
                        
                        if close_end > close_start:
                            block_type = 'bullish'  # تراكم
                        else:
                            block_type = 'bearish'  # توزيع
                        
                        # قوة بناءً على الحجم ومدة التراكم
                        volume_ratio = total_volume / (avg_volume_before * len(window))
                        duration_bonus = min(20, len(window) * 2)
                        strength = min(95, (volume_ratio * 30) + duration_bonus)
                        
                        if strength >= self.min_block_strength:
                            block = OrderBlock(
                                block_type=block_type,
                                price_range=(price_range_low, price_range_high),
                                volume=total_volume,
                                timestamp=window.index[-1],
                                strength=strength,
                                block_source='accumulation'
                            )
                            blocks.append(block)
                            
            self.logger.debug(f"🔍 Accumulation zones: {len(blocks)} كتلة")
            return blocks
            
        except Exception as e:
            self.logger.debug(f"خطأ في كشف مناطق التراكم: {e}")
            return []
    
    def _detect_volume_imbalance(self, df: pd.DataFrame) -> List[OrderBlock]:
        """كشف عدم التوازن في الحجم"""
        blocks = []
        
        try:
            # تحليل عدم التوازن بين الشراء والبيع
            df = df.copy()
            
            # تقدير حجم الشراء/البيع بناءً على حركة السعر
            df['price_change'] = df['close'] - df['open']
            df['buying_volume'] = np.where(df['price_change'] > 0, 
                                         df['volume'] * (df['price_change'] / (df['high'] - df['low'])), 
                                         0)
            df['selling_volume'] = np.where(df['price_change'] < 0, 
                                          df['volume'] * (abs(df['price_change']) / (df['high'] - df['low'])), 
                                          0)
            
            # متوسطات متحركة للحجم
            window = 10
            df['buy_vol_avg'] = df['buying_volume'].rolling(window).mean()
            df['sell_vol_avg'] = df['selling_volume'].rolling(window).mean()
            
            for i in range(window, len(df)):
                current_row = df.iloc[i]
                
                buy_vol = current_row['buying_volume']
                sell_vol = current_row['selling_volume']
                buy_avg = current_row['buy_vol_avg']
                sell_avg = current_row['sell_vol_avg']
                
                # كشف عدم التوازن الشديد
                if buy_vol > buy_avg * self.imbalance_threshold and buy_vol > sell_vol * 2:
                    # عدم توازن شرائي قوي
                    strength = min(90, (buy_vol / buy_avg) * 25)
                    
                    if strength >= self.min_block_strength:
                        block = OrderBlock(
                            block_type='bullish',
                            price_range=(current_row['low'], current_row['close']),
                            volume=current_row['volume'],
                            timestamp=current_row.name,
                            strength=strength,
                            block_source='buy_imbalance'
                        )
                        blocks.append(block)
                
                elif sell_vol > sell_avg * self.imbalance_threshold and sell_vol > buy_vol * 2:
                    # عدم توازن بيعي قوي
                    strength = min(90, (sell_vol / sell_avg) * 25)
                    
                    if strength >= self.min_block_strength:
                        block = OrderBlock(
                            block_type='bearish',
                            price_range=(current_row['close'], current_row['high']),
                            volume=current_row['volume'],
                            timestamp=current_row.name,
                            strength=strength,
                            block_source='sell_imbalance'
                        )
                        blocks.append(block)
                        
            self.logger.debug(f"🔍 Volume imbalance blocks: {len(blocks)} كتلة")
            return blocks
            
        except Exception as e:
            self.logger.debug(f"خطأ في كشف عدم توازن الحجم: {e}")
            return []
    
    def _filter_and_merge_blocks(self, blocks: List[OrderBlock]) -> List[OrderBlock]:
        """تصفية ودمج كتل الأوامر المتداخلة"""
        if not blocks:
            return []
            
        try:
            # ترتيب حسب القوة
            blocks.sort(key=lambda b: b.strength, reverse=True)
            
            # إزالة الكتل القديمة
            now = datetime.now()
            fresh_blocks = []
            
            for block in blocks:
                if isinstance(block.timestamp, datetime):
                    age_hours = (now - block.timestamp).total_seconds() / 3600
                    if age_hours <= self.max_block_age_hours:
                        fresh_blocks.append(block)
                else:
                    fresh_blocks.append(block)  # الاحتفاظ بالكتل بدون timestamp
            
            # دمج الكتل المتداخلة
            merged_blocks = []
            
            for block in fresh_blocks:
                merged = False
                
                for existing_block in merged_blocks:
                    if self._blocks_overlap(block, existing_block):
                        # دمج الكتل المتداخلة
                        if block.strength > existing_block.strength:
                            merged_blocks.remove(existing_block)
                            merged_blocks.append(block)
                        merged = True
                        break
                
                if not merged:
                    merged_blocks.append(block)
            
            # الاحتفاظ بأقوى الكتل
            final_blocks = sorted(merged_blocks, key=lambda b: b.strength, reverse=True)[:15]
            
            return final_blocks
            
        except Exception as e:
            self.logger.debug(f"خطأ في تصفية الكتل: {e}")
            return blocks[:15]  # احتياطي
    
    def _blocks_overlap(self, block1: OrderBlock, block2: OrderBlock, tolerance: float = 0.001) -> bool:
        """فحص تداخل كتلتين"""
        try:
            range1_low, range1_high = block1.price_range
            range2_low, range2_high = block2.price_range
            
            # فحص التداخل
            overlap = not (range1_high < range2_low or range2_high < range1_low)
            
            # فحص القرب (ضمن تسامح معين)
            distance = min(abs(range1_low - range2_high), abs(range2_low - range1_high))
            close_proximity = distance / max(range1_low, range2_low) <= tolerance
            
            return overlap or close_proximity
            
        except Exception:
            return False
    
    def analyze_block_interactions(self, blocks: List[OrderBlock], df: pd.DataFrame) -> Dict:
        """تحليل تفاعل السعر مع كتل الأوامر"""
        analysis = {
            'total_blocks': len(blocks),
            'active_blocks': 0,
            'tested_blocks': 0,
            'broken_blocks': 0,
            'block_efficiency': 0,
            'strongest_blocks': [],
            'recent_interactions': []
        }
        
        try:
            if not blocks:
                return analysis
                
            current_price = df['close'].iloc[-1]
            
            # تحليل كل كتلة
            for block in blocks:
                # فحص التفاعلات التاريخية
                for i in range(len(df)):
                    price = df['close'].iloc[i]
                    timestamp = df.index[i]
                    
                    if block.test_interaction(price, timestamp):
                        analysis['recent_interactions'].append({
                            'block': block,
                            'price': price,
                            'timestamp': timestamp,
                            'interaction_type': 'test'
                        })
                
                # تصنيف الكتلة
                if block.tests > 0:
                    analysis['tested_blocks'] += 1
                    
                if block.broken:
                    analysis['broken_blocks'] += 1
                else:
                    analysis['active_blocks'] += 1
            
            # أقوى الكتل
            analysis['strongest_blocks'] = sorted(blocks, key=lambda b: b.strength, reverse=True)[:5]
            
            # كفاءة الكتل
            if analysis['tested_blocks'] > 0:
                analysis['block_efficiency'] = (analysis['active_blocks'] / analysis['tested_blocks']) * 100
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل تفاعل الكتل: {e}")
            return analysis
    
    def get_relevant_blocks(self, blocks: List[OrderBlock], 
                           current_price: float, 
                           distance_pct: float = 3.0) -> List[OrderBlock]:
        """الحصول على الكتل ذات الصلة بالسعر الحالي"""
        relevant_blocks = []
        
        try:
            for block in blocks:
                block_midpoint = block.get_midpoint()
                distance = abs(current_price - block_midpoint) / current_price * 100
                
                if distance <= distance_pct:
                    relevant_blocks.append(block)
            
            # ترتيب حسب القرب والقوة
            relevant_blocks.sort(key=lambda b: (abs(current_price - b.get_midpoint()), -b.strength))
            
            return relevant_blocks
            
        except Exception as e:
            self.logger.debug(f"خطأ في الحصول على الكتل ذات الصلة: {e}")
            return []
