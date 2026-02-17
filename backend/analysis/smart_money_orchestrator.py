#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Money Orchestrator - منسق تحليل الأموال الذكية
===================================================

المحرك الرئيسي الذي يدمج جميع مكونات Smart Money:
- LiquidityZonesDetector: مناطق السيولة (Swing, Equal, Fibonacci)
- VWAPAnalyzer: مركز السيولة اليومي
- LiquiditySweepDetector: كنس السيولة والفخاخ  
- OrderBlocksDetector: النشاط المؤسسي
- FairValueGapsDetector: فجوات القيمة العادلة

Phase 1 - Week 1-2 من خطة Precision Scalping v8.0
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

# Import Smart Money components
from .liquidity_zones_detector import LiquidityZonesDetector, LiquidityZone
from .vwap_analyzer import VWAPAnalyzer
from .liquidity_sweep_detector import LiquiditySweepDetector, LiquiditySweep
from .order_blocks_detector import OrderBlocksDetector, OrderBlock
from .fair_value_gaps_detector import FairValueGapsDetector, FairValueGap

logger = logging.getLogger(__name__)


class SmartMoneySignal:
    """فئة تمثل إشارة Smart Money مركبة"""
    
    def __init__(self, signal_type: str, confidence: float, 
                 price_target: float, reasons: List[str], 
                 supporting_data: Dict, timestamp: datetime):
        self.signal_type = signal_type        # 'BUY', 'SELL', 'WAIT'
        self.confidence = confidence          # 0-100 
        self.price_target = price_target      # السعر المستهدف
        self.reasons = reasons               # أسباب الإشارة
        self.supporting_data = supporting_data  # البيانات الداعمة
        self.timestamp = timestamp
        
    def __repr__(self):
        return f"SmartMoneySignal({self.signal_type}, {self.confidence:.1f}%, target={self.price_target:.6f})"


class SmartMoneyOrchestrator:
    """منسق تحليل الأموال الذكية - المحرك الرئيسي"""
    
    def __init__(self):
        self.logger = logger
        
        # تهيئة جميع المكونات
        self.liquidity_zones = LiquidityZonesDetector()
        self.vwap_analyzer = VWAPAnalyzer()
        self.liquidity_sweeps = LiquiditySweepDetector()
        self.order_blocks = OrderBlocksDetector()
        self.fair_value_gaps = FairValueGapsDetector()
        
        # إعدادات التوافق
        self.min_confluence_score = 60       # الحد الأدنى لنقاط التوافق
        self.component_weights = {
            'liquidity_zones': 0.25,
            'vwap_analysis': 0.20,
            'liquidity_sweeps': 0.20,
            'order_blocks': 0.20,
            'fair_value_gaps': 0.15
        }
        
    def analyze_smart_money_activity(self, symbol: str, df_15m: pd.DataFrame, 
                                   df_5m: pd.DataFrame) -> Dict:
        """
        التحليل الشامل لنشاط الأموال الذكية
        
        Args:
            symbol: رمز العملة
            df_15m: بيانات 15 دقيقة للتحليل الأساسي
            df_5m: بيانات 5 دقائق للدقة العالية
            
        Returns:
            تحليل شامل مع إشارة مركبة
        """
        self.logger.info(f"🧠 تحليل نشاط Smart Money لـ {symbol}")
        
        try:
            # Phase 1: جمع البيانات من جميع المكونات
            analysis_data = self._gather_component_data(symbol, df_15m, df_5m)
            
            # Phase 2: حساب نقاط التوافق
            confluence_score = self._calculate_confluence_score(analysis_data)
            
            # Phase 3: توليد الإشارة المركبة
            smart_money_signal = self._generate_composite_signal(
                analysis_data, confluence_score, df_5m['close'].iloc[-1]
            )
            
            # Phase 4: تقييم المخاطر والفرص
            risk_assessment = self._assess_risk_opportunities(analysis_data, df_5m)
            
            return {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'analysis_data': analysis_data,
                'confluence_score': confluence_score,
                'smart_money_signal': smart_money_signal,
                'risk_assessment': risk_assessment,
                'summary': self._create_analysis_summary(analysis_data, confluence_score)
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل Smart Money: {e}")
            return self._get_error_result(symbol, str(e))
    
    def _gather_component_data(self, symbol: str, df_15m: pd.DataFrame, 
                             df_5m: pd.DataFrame) -> Dict:
        """جمع البيانات من جميع مكونات Smart Money"""
        data = {}
        
        try:
            # 1. تحليل مناطق السيولة
            self.logger.debug("🔍 تحليل مناطق السيولة...")
            zones_result = self.liquidity_zones.detect_all_zones(symbol, df_15m, df_5m)
            data['liquidity_zones'] = zones_result
            
            # 2. تحليل VWAP
            self.logger.debug("📊 تحليل VWAP...")
            vwap_result = self.vwap_analyzer.analyze_vwap_structure(df_5m)
            data['vwap_analysis'] = vwap_result
            
            # 3. كشف كنس السيولة
            self.logger.debug("🕵️ كشف كنس السيولة...")
            liquidity_zones_list = zones_result.get('all_zones', [])
            sweeps_result = self.liquidity_sweeps.detect_liquidity_sweeps(df_5m, liquidity_zones_list)
            data['liquidity_sweeps'] = sweeps_result
            
            # 4. كشف كتل الأوامر
            self.logger.debug("🏦 كشف كتل الأوامر...")
            blocks_result = self.order_blocks.detect_order_blocks(df_15m)
            data['order_blocks'] = blocks_result
            
            # 5. كشف فجوات القيمة العادلة
            self.logger.debug("📊 كشف فجوات القيمة العادلة...")
            fvg_result = self.fair_value_gaps.detect_fair_value_gaps(df_5m)
            data['fair_value_gaps'] = fvg_result
            
            return data
            
        except Exception as e:
            self.logger.error(f"خطأ في جمع بيانات المكونات: {e}")
            return data
    
    def _calculate_confluence_score(self, analysis_data: Dict) -> float:
        """حساب نقاط التوافق بين جميع المكونات"""
        total_score = 0
        component_scores = {}
        
        try:
            # نقاط مناطق السيولة
            zones_data = analysis_data.get('liquidity_zones', {})
            zones_score = self._score_liquidity_zones(zones_data)
            component_scores['liquidity_zones'] = zones_score
            
            # نقاط VWAP
            vwap_data = analysis_data.get('vwap_analysis', {})
            vwap_score = self._score_vwap_analysis(vwap_data)
            component_scores['vwap_analysis'] = vwap_score
            
            # نقاط كنس السيولة
            sweeps_data = analysis_data.get('liquidity_sweeps', [])
            sweeps_score = self._score_liquidity_sweeps(sweeps_data)
            component_scores['liquidity_sweeps'] = sweeps_score
            
            # نقاط كتل الأوامر
            blocks_data = analysis_data.get('order_blocks', [])
            blocks_score = self._score_order_blocks(blocks_data)
            component_scores['order_blocks'] = blocks_score
            
            # نقاط فجوات القيمة العادلة
            fvg_data = analysis_data.get('fair_value_gaps', [])
            fvg_score = self._score_fair_value_gaps(fvg_data)
            component_scores['fair_value_gaps'] = fvg_score
            
            # حساب النقاط المرجحة
            for component, score in component_scores.items():
                weight = self.component_weights.get(component, 0)
                total_score += score * weight
            
            return min(100, total_score)
            
        except Exception as e:
            self.logger.debug(f"خطأ في حساب التوافق: {e}")
            return 0
    
    def _score_liquidity_zones(self, zones_data: Dict) -> float:
        """تسجيل نقاط مناطق السيولة"""
        try:
            all_zones = zones_data.get('all_zones', [])
            if not all_zones:
                return 0
                
            # متوسط قوة المناطق
            avg_strength = sum(zone.strength for zone in all_zones) / len(all_zones)
            
            # مكافأة تنوع المصادر
            sources = set(zone.source for zone in all_zones)
            diversity_bonus = min(20, len(sources) * 5)
            
            return min(100, avg_strength + diversity_bonus)
            
        except Exception:
            return 0
    
    def _score_vwap_analysis(self, vwap_data: Dict) -> float:
        """تسجيل نقاط تحليل VWAP"""
        try:
            if not vwap_data or 'error' in vwap_data:
                return 0
                
            strength_data = vwap_data.get('vwap_strength', {})
            overall_strength = strength_data.get('overall_strength', 0)
            reliability = strength_data.get('reliability_score', 0)
            
            return (overall_strength + reliability) / 2
            
        except Exception:
            return 0
    
    def _score_liquidity_sweeps(self, sweeps_data: List) -> float:
        """تسجيل نقاط كنس السيولة"""
        try:
            if not sweeps_data:
                return 0
                
            # متوسط قوة عمليات الكنس
            avg_strength = sum(sweep.strength for sweep in sweeps_data) / len(sweeps_data)
            
            # مكافأة عدد العمليات
            count_bonus = min(30, len(sweeps_data) * 5)
            
            return min(100, avg_strength + count_bonus)
            
        except Exception:
            return 0
    
    def _score_order_blocks(self, blocks_data: List) -> float:
        """تسجيل نقاط كتل الأوامر"""
        try:
            if not blocks_data:
                return 0
                
            # متوسط قوة الكتل
            avg_strength = sum(block.strength for block in blocks_data) / len(blocks_data)
            
            # مكافأة تنوع المصادر
            sources = set(block.block_source for block in blocks_data)
            diversity_bonus = min(25, len(sources) * 8)
            
            return min(100, avg_strength + diversity_bonus)
            
        except Exception:
            return 0
    
    def _score_fair_value_gaps(self, fvg_data: List) -> float:
        """تسجيل نقاط فجوات القيمة العادلة"""
        try:
            if not fvg_data:
                return 0
                
            # التركيز على الفجوات غير المملوءة
            active_gaps = [gap for gap in fvg_data if gap.status == 'unfilled']
            
            if not active_gaps:
                return 20  # نقاط أساسية للفجوات الموجودة
                
            avg_strength = sum(gap.strength for gap in active_gaps) / len(active_gaps)
            activity_bonus = min(40, len(active_gaps) * 10)
            
            return min(100, avg_strength + activity_bonus)
            
        except Exception:
            return 0
    
    def _generate_composite_signal(self, analysis_data: Dict, 
                                 confluence_score: float, 
                                 current_price: float) -> SmartMoneySignal:
        """توليد الإشارة المركبة من جميع المكونات"""
        try:
            reasons = []
            supporting_data = {}
            signal_type = 'WAIT'
            confidence = confluence_score
            price_target = current_price
            
            # تحليل الإشارات من كل مكون
            if confluence_score >= self.min_confluence_score:
                
                # إشارات مناطق السيولة
                zones_signal = self._analyze_zones_signal(analysis_data.get('liquidity_zones', {}), current_price)
                if zones_signal['signal'] != 'NEUTRAL':
                    reasons.append(f"Liquidity Zones: {zones_signal['reason']}")
                    supporting_data['zones'] = zones_signal
                
                # إشارات VWAP
                vwap_signals = analysis_data.get('vwap_analysis', {}).get('trading_signals', {})
                if vwap_signals.get('primary_signal') not in ['NEUTRAL', 'WAIT_FOR_DIRECTION']:
                    reasons.append(f"VWAP: {vwap_signals['primary_signal']}")
                    supporting_data['vwap'] = vwap_signals
                
                # إشارات كنس السيولة  
                sweeps_data = analysis_data.get('liquidity_sweeps', [])
                if sweeps_data:
                    recent_sweeps = [s for s in sweeps_data if s.get_age_hours() < 4]
                    if recent_sweeps:
                        sweep_signal = recent_sweeps[0].sweep_type
                        reasons.append(f"Recent Liquidity Sweep: {sweep_signal}")
                        supporting_data['sweeps'] = recent_sweeps
                        
                        if sweep_signal == 'bullish_sweep':
                            signal_type = 'BUY'
                        elif sweep_signal == 'bearish_sweep':
                            signal_type = 'SELL'
            
            return SmartMoneySignal(
                signal_type=signal_type,
                confidence=confidence,
                price_target=price_target,
                reasons=reasons,
                supporting_data=supporting_data,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.debug(f"خطأ في توليد الإشارة المركبة: {e}")
            return SmartMoneySignal('WAIT', 0, current_price, ['Analysis Error'], {}, datetime.now())
    
    def _analyze_zones_signal(self, zones_data: Dict, current_price: float) -> Dict:
        """تحليل إشارة مناطق السيولة"""
        signal = {'signal': 'NEUTRAL', 'reason': '', 'zones': []}
        
        try:
            all_zones = zones_data.get('all_zones', [])
            if not all_zones:
                return signal
                
            # البحث عن المناطق القريبة
            nearby_zones = []
            for zone in all_zones:
                distance_pct = abs(zone.price - current_price) / current_price * 100
                if distance_pct <= 2.0:  # ضمن 2%
                    nearby_zones.append((zone, distance_pct))
                    
            if not nearby_zones:
                return signal
                
            # ترتيب حسب القرب والقوة
            nearby_zones.sort(key=lambda x: (x[1], -x[0].strength))
            closest_zone = nearby_zones[0][0]
            
            if closest_zone.zone_type == 'support' and current_price > closest_zone.price:
                signal = {
                    'signal': 'BUY',
                    'reason': f'Near strong support zone ({closest_zone.source})',
                    'zones': [closest_zone]
                }
            elif closest_zone.zone_type == 'resistance' and current_price < closest_zone.price:
                signal = {
                    'signal': 'SELL', 
                    'reason': f'Near strong resistance zone ({closest_zone.source})',
                    'zones': [closest_zone]
                }
                
            return signal
            
        except Exception:
            return signal
    
    def _assess_risk_opportunities(self, analysis_data: Dict, df: pd.DataFrame) -> Dict:
        """تقييم المخاطر والفرص"""
        assessment = {
            'risk_level': 'MEDIUM',
            'opportunity_score': 0,
            'risk_factors': [],
            'opportunities': [],
            'suggested_position_size': 2.0  # نسبة مئوية من المحفظة
        }
        
        try:
            current_price = df['close'].iloc[-1]
            
            # تقييم المخاطر
            risk_score = 0
            
            # مخاطر من كنس السيولة الأخير
            sweeps_data = analysis_data.get('liquidity_sweeps', [])
            recent_sweeps = [s for s in sweeps_data if s.get_age_hours() < 2]
            if recent_sweeps:
                risk_score += 20
                assessment['risk_factors'].append('Recent liquidity sweep activity')
            
            # مخاطر من فجوات غير مملوءة
            fvg_data = analysis_data.get('fair_value_gaps', [])
            unfilled_gaps = [g for g in fvg_data if g.status == 'unfilled']
            nearby_gaps = [g for g in unfilled_gaps if abs(g.get_midpoint() - current_price) / current_price < 0.03]
            if nearby_gaps:
                risk_score += 15
                assessment['risk_factors'].append(f'{len(nearby_gaps)} unfilled gaps nearby')
            
            # تحديد مستوى المخاطر
            if risk_score > 50:
                assessment['risk_level'] = 'HIGH'
                assessment['suggested_position_size'] = 1.0
            elif risk_score < 20:
                assessment['risk_level'] = 'LOW'
                assessment['suggested_position_size'] = 4.0
                
            # تقييم الفرص
            zones_data = analysis_data.get('liquidity_zones', {})
            strong_zones = [z for z in zones_data.get('all_zones', []) if z.strength > 80]
            if strong_zones:
                assessment['opportunities'].append(f'{len(strong_zones)} high-strength liquidity zones')
                assessment['opportunity_score'] += 30
                
            return assessment
            
        except Exception as e:
            self.logger.debug(f"خطأ في تقييم المخاطر: {e}")
            return assessment
    
    def _create_analysis_summary(self, analysis_data: Dict, confluence_score: float) -> Dict:
        """إنشاء ملخص التحليل"""
        summary = {
            'confluence_score': confluence_score,
            'components_summary': {},
            'key_findings': [],
            'recommendation': 'NEUTRAL'
        }
        
        try:
            # ملخص المكونات
            summary['components_summary'] = {
                'liquidity_zones': len(analysis_data.get('liquidity_zones', {}).get('all_zones', [])),
                'liquidity_sweeps': len(analysis_data.get('liquidity_sweeps', [])),
                'order_blocks': len(analysis_data.get('order_blocks', [])),
                'fair_value_gaps': len(analysis_data.get('fair_value_gaps', [])),
                'vwap_strength': analysis_data.get('vwap_analysis', {}).get('vwap_strength', {}).get('overall_strength', 0)
            }
            
            # النتائج الرئيسية
            if confluence_score >= 80:
                summary['key_findings'].append('High confluence across multiple components')
                summary['recommendation'] = 'STRONG'
            elif confluence_score >= 60:
                summary['key_findings'].append('Moderate confluence detected')
                summary['recommendation'] = 'MODERATE'
            else:
                summary['key_findings'].append('Low confluence - mixed signals')
                summary['recommendation'] = 'WEAK'
                
            return summary
            
        except Exception:
            return summary
    
    def _get_error_result(self, symbol: str, error_msg: str) -> Dict:
        """نتيجة الخطأ"""
        return {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'error': True,
            'error_message': error_msg,
            'confluence_score': 0,
            'smart_money_signal': SmartMoneySignal('WAIT', 0, 0, ['Analysis Error'], {}, datetime.now())
        }
