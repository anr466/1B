#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VWAP Analyzer - محلل مؤشر VWAP المتقدم
=======================================

يحلل VWAP (Volume Weighted Average Price) كمركز سيولة يومي
ويكشف انحرافاته المعيارية كمناطق دعم ومقاومة ديناميكية

يطبق استراتيجية السيولة: "VWAP: مركز سيولة اليوم التداولي"

Phase 1 - Week 1-2 من خطة Precision Scalping v8.0
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from .liquidity_zones_detector import LiquidityZone

logger = logging.getLogger(__name__)


class VWAPBand:
    """فئة تمثل نطاق VWAP واحد"""
    
    def __init__(self, level: float, band_type: str, std_multiplier: float, 
                 strength: float, timestamp: datetime):
        self.level = level              # مستوى النطاق
        self.band_type = band_type      # 'upper', 'lower', 'vwap'
        self.std_multiplier = std_multiplier  # مضاعف الانحراف المعياري
        self.strength = strength        # قوة النطاق (0-100)
        self.timestamp = timestamp
        self.touches = 0               # عدد مرات اللمس
        self.last_touch = None         # آخر لمسة
        self.is_active = True          # هل النطاق نشط
        
    def test_touch(self, price: float, timestamp: datetime, tolerance: float = 0.001):
        """اختبار لمس النطاق"""
        distance = abs(price - self.level) / self.level
        if distance <= tolerance:
            self.touches += 1
            self.last_touch = timestamp
            return True
        return False
    
    def get_age_minutes(self) -> float:
        """عمر النطاق بالدقائق"""
        return (datetime.now() - self.timestamp).total_seconds() / 60
        
    def __repr__(self):
        return f"VWAPBand({self.band_type} @ {self.level:.6f}, σ={self.std_multiplier}, strength={self.strength:.1f})"


class VWAPAnalyzer:
    """محلل VWAP المتقدم لاستراتيجية Smart Money"""
    
    def __init__(self):
        self.logger = logger
        
        # إعدادات VWAP
        self.session_start_hour = 0    # بداية الجلسة (UTC)
        self.min_data_points = 20      # الحد الأدنى لنقاط البيانات
        
        # مضاعفات الانحراف المعياري
        self.std_multipliers = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        
        # أوزان القوة لكل مضاعف
        self.strength_weights = {
            0.5: 95,  # قريب جداً من VWAP
            1.0: 85,  # انحراف معياري واحد
            1.5: 75,  # انحراف قوي
            2.0: 65,  # انحراف كبير
            2.5: 55,  # انحراف كبير جداً
            3.0: 45   # انحراف استثنائي
        }
        
    def analyze_vwap_structure(self, df: pd.DataFrame) -> Dict:
        """
        تحليل شامل لهيكل VWAP
        
        Args:
            df: DataFrame مع بيانات OHLCV (مفضل 5M أو 1M)
            
        Returns:
            Dict مع تحليل VWAP الشامل
        """
        self.logger.info("📊 تحليل هيكل VWAP...")
        
        if len(df) < self.min_data_points:
            return self._get_insufficient_data_result()
            
        try:
            # حساب VWAP والانحرافات المعيارية
            vwap_data = self._calculate_vwap_with_std(df)
            
            # تحليل النطاقات
            bands_analysis = self._analyze_vwap_bands(vwap_data)
            
            # كشف مناطق السيولة VWAP
            liquidity_zones = self._detect_vwap_liquidity_zones(vwap_data)
            
            # تحليل سلوك السعر مع VWAP
            price_behavior = self._analyze_price_behavior_with_vwap(vwap_data)
            
            # تقييم قوة VWAP كمركز سيولة
            vwap_strength = self._evaluate_vwap_strength(vwap_data, price_behavior)
            
            return {
                'vwap_data': vwap_data,
                'bands': bands_analysis,
                'liquidity_zones': liquidity_zones,
                'price_behavior': price_behavior,
                'vwap_strength': vwap_strength,
                'current_analysis': self._get_current_analysis(vwap_data),
                'trading_signals': self._generate_vwap_signals(vwap_data, price_behavior)
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل VWAP: {e}")
            return self._get_error_result(str(e))
    
    def _calculate_vwap_with_std(self, df: pd.DataFrame) -> pd.DataFrame:
        """حساب VWAP مع الانحرافات المعيارية"""
        df = df.copy()
        
        # السعر النموذجي
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['volume_price'] = df['typical_price'] * df['volume']
        
        # VWAP تراكمي (يعيد تعيين يومياً)
        df['date'] = df.index.date
        
        # حساب VWAP لكل يوم
        vwap_by_date = {}
        for date in df['date'].unique():
            day_data = df[df['date'] == date].copy()
            
            # VWAP تراكمي لليوم
            day_data['cumulative_volume'] = day_data['volume'].cumsum()
            day_data['cumulative_volume_price'] = day_data['volume_price'].cumsum()
            day_data['vwap'] = day_data['cumulative_volume_price'] / day_data['cumulative_volume']
            
            # حساب الانحراف المعياري
            day_data['price_variance'] = (day_data['typical_price'] - day_data['vwap']) ** 2 * day_data['volume']
            day_data['cumulative_price_variance'] = day_data['price_variance'].cumsum()
            day_data['variance'] = day_data['cumulative_price_variance'] / day_data['cumulative_volume']
            day_data['vwap_std'] = np.sqrt(day_data['variance'])
            
            vwap_by_date[date] = day_data
        
        # دمج البيانات
        result_df = pd.concat(vwap_by_date.values(), sort=False)
        result_df = result_df.sort_index()
        
        # حساب النطاقات
        for multiplier in self.std_multipliers:
            result_df[f'vwap_upper_{multiplier}'] = result_df['vwap'] + (result_df['vwap_std'] * multiplier)
            result_df[f'vwap_lower_{multiplier}'] = result_df['vwap'] - (result_df['vwap_std'] * multiplier)
        
        return result_df
    
    def _analyze_vwap_bands(self, df: pd.DataFrame) -> Dict:
        """تحليل نطاقات VWAP"""
        bands_data = {
            'current_bands': [],
            'band_interactions': [],
            'strongest_bands': []
        }
        
        try:
            current_vwap = df['vwap'].iloc[-1]
            current_std = df['vwap_std'].iloc[-1]
            current_price = df['close'].iloc[-1]
            latest_timestamp = df.index[-1]
            
            # إنشاء النطاقات الحالية
            for multiplier in self.std_multipliers:
                upper_level = df[f'vwap_upper_{multiplier}'].iloc[-1]
                lower_level = df[f'vwap_lower_{multiplier}'].iloc[-1]
                
                # نطاق علوي
                upper_band = VWAPBand(
                    level=upper_level,
                    band_type='upper',
                    std_multiplier=multiplier,
                    strength=self.strength_weights[multiplier],
                    timestamp=latest_timestamp
                )
                bands_data['current_bands'].append(upper_band)
                
                # نطاق سفلي
                lower_band = VWAPBand(
                    level=lower_level,
                    band_type='lower',
                    std_multiplier=multiplier,
                    strength=self.strength_weights[multiplier],
                    timestamp=latest_timestamp
                )
                bands_data['current_bands'].append(lower_band)
            
            # VWAP نفسه
            vwap_band = VWAPBand(
                level=current_vwap,
                band_type='vwap',
                std_multiplier=0.0,
                strength=100,  # أقوى مستوى
                timestamp=latest_timestamp
            )
            bands_data['current_bands'].append(vwap_band)
            
            # تحليل التفاعلات التاريخية
            bands_data['band_interactions'] = self._analyze_historical_interactions(df)
            
            # أقوى النطاقات (الأكثر تفاعلاً)
            bands_data['strongest_bands'] = sorted(
                bands_data['current_bands'], 
                key=lambda b: b.strength, 
                reverse=True
            )[:5]
            
            return bands_data
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل نطاقات VWAP: {e}")
            return bands_data
    
    def _detect_vwap_liquidity_zones(self, df: pd.DataFrame) -> List[LiquidityZone]:
        """كشف مناطق السيولة بناءً على VWAP"""
        zones = []
        
        try:
            current_vwap = df['vwap'].iloc[-1]
            current_std = df['vwap_std'].iloc[-1]
            latest_timestamp = df.index[-1]
            
            # VWAP كمنطقة محورية رئيسية
            vwap_zone = LiquidityZone(
                price=current_vwap,
                zone_type='pivot',
                strength=95,  # قوة عالية جداً
                timestamp=latest_timestamp,
                source='vwap_center'
            )
            zones.append(vwap_zone)
            
            # النطاقات كمناطق سيولة
            key_multipliers = [1.0, 2.0]  # التركيز على النطاقات المهمة
            
            for multiplier in key_multipliers:
                upper_level = df[f'vwap_upper_{multiplier}'].iloc[-1]
                lower_level = df[f'vwap_lower_{multiplier}'].iloc[-1]
                
                # قوة بناءً على المضاعف
                strength = 85 if multiplier == 1.0 else 75
                
                # منطقة علوية
                upper_zone = LiquidityZone(
                    price=upper_level,
                    zone_type='resistance',
                    strength=strength,
                    timestamp=latest_timestamp,
                    source=f'vwap_upper_{multiplier}'
                )
                zones.append(upper_zone)
                
                # منطقة سفلية
                lower_zone = LiquidityZone(
                    price=lower_level,
                    zone_type='support',
                    strength=strength,
                    timestamp=latest_timestamp,
                    source=f'vwap_lower_{multiplier}'
                )
                zones.append(lower_zone)
            
            return zones
            
        except Exception as e:
            self.logger.error(f"خطأ في كشف مناطق سيولة VWAP: {e}")
            return []
    
    def _analyze_price_behavior_with_vwap(self, df: pd.DataFrame) -> Dict:
        """تحليل سلوك السعر مع VWAP"""
        behavior = {
            'position_relative_to_vwap': 'neutral',
            'vwap_slope': 'flat',
            'price_distance_pct': 0.0,
            'volume_profile': 'balanced',
            'recent_interactions': [],
            'behavioral_signals': []
        }
        
        try:
            current_price = df['close'].iloc[-1]
            current_vwap = df['vwap'].iloc[-1]
            
            # موقع السعر بالنسبة للـ VWAP
            price_distance = (current_price - current_vwap) / current_vwap * 100
            behavior['price_distance_pct'] = price_distance
            
            if price_distance > 0.5:
                behavior['position_relative_to_vwap'] = 'above'
            elif price_distance < -0.5:
                behavior['position_relative_to_vwap'] = 'below'
            else:
                behavior['position_relative_to_vwap'] = 'at_vwap'
            
            # اتجاه VWAP
            recent_vwap = df['vwap'].tail(10)
            vwap_change = (recent_vwap.iloc[-1] - recent_vwap.iloc[0]) / recent_vwap.iloc[0] * 100
            
            if vwap_change > 0.1:
                behavior['vwap_slope'] = 'rising'
            elif vwap_change < -0.1:
                behavior['vwap_slope'] = 'falling'
            else:
                behavior['vwap_slope'] = 'flat'
            
            # تحليل الحجم
            behavior['volume_profile'] = self._analyze_volume_profile_with_vwap(df)
            
            # التفاعلات الأخيرة
            behavior['recent_interactions'] = self._find_recent_vwap_interactions(df)
            
            # إشارات السلوك
            behavior['behavioral_signals'] = self._generate_behavioral_signals(df, behavior)
            
            return behavior
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل سلوك السعر: {e}")
            return behavior
    
    def _analyze_volume_profile_with_vwap(self, df: pd.DataFrame) -> str:
        """تحليل الحجم بالنسبة للـ VWAP"""
        try:
            # تقسيم البيانات حسب موقع السعر من VWAP
            above_vwap = df[df['close'] > df['vwap']]
            below_vwap = df[df['close'] < df['vwap']]
            at_vwap = df[abs(df['close'] - df['vwap']) / df['vwap'] <= 0.001]
            
            volume_above = above_vwap['volume'].sum() if len(above_vwap) > 0 else 0
            volume_below = below_vwap['volume'].sum() if len(below_vwap) > 0 else 0
            volume_at = at_vwap['volume'].sum() if len(at_vwap) > 0 else 0
            
            total_volume = volume_above + volume_below + volume_at
            
            if total_volume == 0:
                return 'no_data'
            
            ratio_above = volume_above / total_volume
            ratio_below = volume_below / total_volume
            
            if ratio_above > 0.6:
                return 'bullish'  # حجم أكبر فوق VWAP
            elif ratio_below > 0.6:
                return 'bearish'  # حجم أكبر تحت VWAP
            else:
                return 'balanced'  # حجم متوازن
                
        except Exception as e:
            self.logger.debug(f"خطأ في تحليل حجم VWAP: {e}")
            return 'unknown'
    
    def _find_recent_vwap_interactions(self, df: pd.DataFrame, lookback: int = 20) -> List[Dict]:
        """البحث عن التفاعلات الأخيرة مع VWAP"""
        interactions = []
        
        try:
            recent_data = df.tail(lookback)
            
            for i in range(1, len(recent_data)):
                current_row = recent_data.iloc[i]
                prev_row = recent_data.iloc[i-1]
                
                # كشف عبور VWAP
                if (prev_row['close'] < prev_row['vwap'] and 
                    current_row['close'] > current_row['vwap']):
                    # عبور صاعد
                    interactions.append({
                        'type': 'bullish_cross',
                        'timestamp': current_row.name,
                        'price': current_row['close'],
                        'vwap': current_row['vwap'],
                        'volume': current_row['volume']
                    })
                    
                elif (prev_row['close'] > prev_row['vwap'] and 
                      current_row['close'] < current_row['vwap']):
                    # عبور هابط
                    interactions.append({
                        'type': 'bearish_cross',
                        'timestamp': current_row.name,
                        'price': current_row['close'],
                        'vwap': current_row['vwap'],
                        'volume': current_row['volume']
                    })
                
                # اختبار النطاقات
                for multiplier in [1.0, 2.0]:
                    upper_band = current_row[f'vwap_upper_{multiplier}']
                    lower_band = current_row[f'vwap_lower_{multiplier}']
                    
                    # لمس النطاق العلوي
                    if (current_row['high'] >= upper_band and 
                        prev_row['high'] < prev_row[f'vwap_upper_{multiplier}']):
                        interactions.append({
                            'type': f'upper_band_touch_{multiplier}',
                            'timestamp': current_row.name,
                            'price': current_row['high'],
                            'band_level': upper_band,
                            'volume': current_row['volume']
                        })
                    
                    # لمس النطاق السفلي
                    if (current_row['low'] <= lower_band and 
                        prev_row['low'] > prev_row[f'vwap_lower_{multiplier}']):
                        interactions.append({
                            'type': f'lower_band_touch_{multiplier}',
                            'timestamp': current_row.name,
                            'price': current_row['low'],
                            'band_level': lower_band,
                            'volume': current_row['volume']
                        })
            
            return interactions
            
        except Exception as e:
            self.logger.debug(f"خطأ في البحث عن تفاعلات VWAP: {e}")
            return []
    
    def _generate_behavioral_signals(self, df: pd.DataFrame, behavior: Dict) -> List[str]:
        """توليد إشارات السلوك"""
        signals = []
        
        try:
            current_price = df['close'].iloc[-1]
            current_vwap = df['vwap'].iloc[-1]
            
            # إشارة الموقع
            if behavior['position_relative_to_vwap'] == 'above' and behavior['vwap_slope'] == 'rising':
                signals.append('STRONG_BULLISH_MOMENTUM')
            elif behavior['position_relative_to_vwap'] == 'below' and behavior['vwap_slope'] == 'falling':
                signals.append('STRONG_BEARISH_MOMENTUM')
            
            # إشارة العودة لـ VWAP
            distance_pct = abs(behavior['price_distance_pct'])
            if distance_pct > 2.0:  # بعيد عن VWAP
                if behavior['position_relative_to_vwap'] == 'above':
                    signals.append('POTENTIAL_REVERSION_DOWN')
                else:
                    signals.append('POTENTIAL_REVERSION_UP')
            
            # إشارة الحجم
            if behavior['volume_profile'] == 'bullish' and behavior['position_relative_to_vwap'] == 'above':
                signals.append('VOLUME_CONFIRMS_BULLISH')
            elif behavior['volume_profile'] == 'bearish' and behavior['position_relative_to_vwap'] == 'below':
                signals.append('VOLUME_CONFIRMS_BEARISH')
            
            return signals
            
        except Exception as e:
            self.logger.debug(f"خطأ في توليد إشارات السلوك: {e}")
            return []
    
    def _evaluate_vwap_strength(self, df: pd.DataFrame, behavior: Dict) -> Dict:
        """تقييم قوة VWAP كمركز سيولة"""
        strength_evaluation = {
            'overall_strength': 0,
            'reliability_score': 0,
            'factors': {}
        }
        
        try:
            # عدد التفاعلات
            interactions_count = len(behavior['recent_interactions'])
            interaction_score = min(30, interactions_count * 3)
            
            # تنوع التفاعلات
            interaction_types = set(i['type'] for i in behavior['recent_interactions'])
            diversity_score = min(20, len(interaction_types) * 4)
            
            # استقرار VWAP
            vwap_volatility = df['vwap'].rolling(20).std().iloc[-1] / df['vwap'].iloc[-1]
            stability_score = max(0, 30 - (vwap_volatility * 1000))  # كلما قل التقلب زادت النقاط
            
            # حجم التداول
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            recent_volume = df['volume'].tail(5).mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            volume_score = min(20, volume_ratio * 10)
            
            strength_evaluation['factors'] = {
                'interactions': interaction_score,
                'diversity': diversity_score,
                'stability': stability_score,
                'volume': volume_score
            }
            
            # النقاط الإجمالية
            total_score = sum(strength_evaluation['factors'].values())
            strength_evaluation['overall_strength'] = min(100, total_score)
            
            # درجة الموثوقية
            if total_score >= 80:
                strength_evaluation['reliability_score'] = 95
            elif total_score >= 60:
                strength_evaluation['reliability_score'] = 80
            elif total_score >= 40:
                strength_evaluation['reliability_score'] = 65
            else:
                strength_evaluation['reliability_score'] = 45
            
            return strength_evaluation
            
        except Exception as e:
            self.logger.error(f"خطأ في تقييم قوة VWAP: {e}")
            return strength_evaluation
    
    def _get_current_analysis(self, df: pd.DataFrame) -> Dict:
        """تحليل الوضع الحالي"""
        try:
            current_row = df.iloc[-1]
            
            return {
                'current_price': current_row['close'],
                'current_vwap': current_row['vwap'],
                'vwap_distance_pct': ((current_row['close'] - current_row['vwap']) / current_row['vwap']) * 100,
                'current_std': current_row['vwap_std'],
                'nearest_upper_band': current_row['vwap_upper_1.0'],
                'nearest_lower_band': current_row['vwap_lower_1.0'],
                'timestamp': current_row.name
            }
        except Exception:
            return {}
    
    def _generate_vwap_signals(self, df: pd.DataFrame, behavior: Dict) -> Dict:
        """توليد إشارات تداول VWAP"""
        signals = {
            'primary_signal': 'NEUTRAL',
            'confidence': 0,
            'entry_zones': [],
            'exit_zones': [],
            'risk_management': {}
        }
        
        try:
            current_analysis = self._get_current_analysis(df)
            distance_pct = current_analysis['vwap_distance_pct']
            
            # إشارات بناءً على المسافة من VWAP
            if -0.5 <= distance_pct <= 0.5:
                # قريب من VWAP - انتظار اتجاه
                signals['primary_signal'] = 'WAIT_FOR_DIRECTION'
                signals['confidence'] = 60
                
            elif distance_pct > 1.5:
                # بعيد للأعلى - احتمال انعكاس
                signals['primary_signal'] = 'POTENTIAL_SHORT'
                signals['confidence'] = 70
                signals['entry_zones'] = [current_analysis['nearest_upper_band']]
                
            elif distance_pct < -1.5:
                # بعيد للأسفل - احتمال انعكاس
                signals['primary_signal'] = 'POTENTIAL_LONG'
                signals['confidence'] = 70
                signals['entry_zones'] = [current_analysis['nearest_lower_band']]
            
            # تعديل الثقة بناءً على السلوك
            if 'VOLUME_CONFIRMS_BULLISH' in behavior['behavioral_signals']:
                if signals['primary_signal'] == 'POTENTIAL_LONG':
                    signals['confidence'] += 15
            elif 'VOLUME_CONFIRMS_BEARISH' in behavior['behavioral_signals']:
                if signals['primary_signal'] == 'POTENTIAL_SHORT':
                    signals['confidence'] += 15
            
            return signals
            
        except Exception as e:
            self.logger.error(f"خطأ في توليد إشارات VWAP: {e}")
            return signals
    
    def _analyze_historical_interactions(self, df: pd.DataFrame) -> List[Dict]:
        """تحليل التفاعلات التاريخية مع النطاقات"""
        # تطبيق مبسط - يمكن توسيعه لاحقاً
        return []
    
    def _get_insufficient_data_result(self) -> Dict:
        """نتيجة عدم كفاية البيانات"""
        return {
            'error': 'insufficient_data',
            'message': 'بيانات غير كافية لتحليل VWAP',
            'min_required': self.min_data_points
        }
    
    def _get_error_result(self, error_msg: str) -> Dict:
        """نتيجة خطأ"""
        return {
            'error': 'analysis_error',
            'message': error_msg
        }
