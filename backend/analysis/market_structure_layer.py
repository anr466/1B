#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Market Structure Context Layer
==============================

طبقة السياق الهيكلي للسوق - تعمل قبل أي إشارات تداول

الغرض:
- فهم موقع السعر ضمن الهيكل السوقي
- تحديد إذا كان السوق قرب قمة أو قاع هيكلي
- التحكم في أنواع الصفقات المسموحة
- لا تولّد إشارات دخول مباشرة

المبدأ الأساسي:
القمم والقيعان = سياق، وليس إشارات

References:
- Smart Money Concepts (SMC)
- Wyckoff Method
- Price Action Structure
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class ContextState(Enum):
    """حالات السياق الهيكلي"""
    HIGH = "HIGH"           # قرب قمة هيكلية - منع الشراء
    LOW = "LOW"             # قرب قاع هيكلي - منع البيع
    MID = "MID"             # منتصف الهيكل - السماح بالكل
    UNKNOWN = "UNKNOWN"     # غير واضح - منع الكل


class TrendDirection(Enum):
    """اتجاه الترند"""
    BULLISH = "BULLISH"     # صاعد
    BEARISH = "BEARISH"     # هابط
    RANGING = "RANGING"     # جانبي


@dataclass
class StructureLevel:
    """مستوى هيكلي (قمة أو قاع)"""
    price: float
    timestamp: pd.Timestamp
    level_type: str  # 'HH', 'HL', 'LH', 'LL'
    strength: float  # 0-1


@dataclass
class MarketContext:
    """نتيجة تحليل السياق الهيكلي"""
    state: ContextState
    trend: TrendDirection
    htf_state: ContextState      # Higher Timeframe
    etf_state: ContextState      # Execution Timeframe
    nearest_high: Optional[float]
    nearest_low: Optional[float]
    distance_to_high_pct: float
    distance_to_low_pct: float
    permitted_actions: List[str]
    confidence: float            # 0-1
    reasoning: List[str]


class MarketStructureLayer:
    """
    طبقة السياق الهيكلي للسوق
    
    تعمل على إطارين زمنيين:
    - HTF (Higher Timeframe): للسياق العام (4h أو 1d)
    - ETF (Execution Timeframe): للدقة (1h أو 15m)
    
    القواعد:
    - HTF يسيطر على ETF
    - إذا HTF = HIGH → ETF long signals مقيدة
    - إذا HTF = LOW → ETF short signals مقيدة
    """
    
    # معاملات قابلة للضبط
    SWING_LOOKBACK = 20          # عدد الشموع للبحث عن القمم/القيعان
    ZONE_THRESHOLD_PCT = 0.02    # 2% = اعتبار السعر "قريب" من المستوى
    MIN_SWING_STRENGTH = 0.3     # الحد الأدنى لقوة القمة/القاع
    
    def __init__(self, htf: str = '4h', etf: str = '1h'):
        """
        تهيئة الطبقة
        
        Args:
            htf: الإطار الزمني الأعلى (Higher Timeframe)
            etf: إطار التنفيذ (Execution Timeframe)
        """
        self.htf = htf
        self.etf = etf
        self.logger = logger
        
        # تخزين المستويات المكتشفة
        self.structure_levels: List[StructureLevel] = []
        
        self.logger.info(f"✅ تم تهيئة Market Structure Layer (HTF={htf}, ETF={etf})")
    
    def analyze(self, df_htf: pd.DataFrame, df_etf: pd.DataFrame, 
                current_price: float) -> MarketContext:
        """
        تحليل السياق الهيكلي الكامل
        
        Args:
            df_htf: بيانات الإطار الزمني الأعلى
            df_etf: بيانات إطار التنفيذ
            current_price: السعر الحالي
            
        Returns:
            MarketContext مع الحالة والإجراءات المسموحة
        """
        reasoning = []
        
        # 1. تحليل HTF
        htf_result = self._analyze_structure(df_htf, current_price, "HTF")
        reasoning.append(f"HTF ({self.htf}): {htf_result['state'].value}")
        
        # 2. تحليل ETF
        etf_result = self._analyze_structure(df_etf, current_price, "ETF")
        reasoning.append(f"ETF ({self.etf}): {etf_result['state'].value}")
        
        # 3. دمج النتائج - HTF يسيطر
        final_state = self._resolve_context(htf_result['state'], etf_result['state'])
        reasoning.append(f"Final State: {final_state.value}")
        
        # 4. تحديد الاتجاه
        trend = self._detect_trend(df_htf)
        reasoning.append(f"Trend: {trend.value}")
        
        # 5. تحديد الإجراءات المسموحة
        permitted = self._get_permitted_actions(final_state, trend)
        
        # 6. حساب المسافات
        nearest_high = htf_result.get('nearest_high')
        nearest_low = htf_result.get('nearest_low')
        
        dist_high = abs(nearest_high - current_price) / current_price if nearest_high else 0
        dist_low = abs(current_price - nearest_low) / current_price if nearest_low else 0
        
        # 7. حساب الثقة
        confidence = self._calculate_confidence(htf_result, etf_result)
        
        return MarketContext(
            state=final_state,
            trend=trend,
            htf_state=htf_result['state'],
            etf_state=etf_result['state'],
            nearest_high=nearest_high,
            nearest_low=nearest_low,
            distance_to_high_pct=dist_high * 100,
            distance_to_low_pct=dist_low * 100,
            permitted_actions=permitted,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def _analyze_structure(self, df: pd.DataFrame, current_price: float, 
                          tf_name: str) -> Dict:
        """
        تحليل الهيكل لإطار زمني واحد
        
        يستخدم:
        - Swing Highs/Lows Detection
        - Higher Highs / Higher Lows Pattern
        - Distance from Structure
        """
        if df is None or len(df) < self.SWING_LOOKBACK * 2:
            return {
                'state': ContextState.UNKNOWN,
                'nearest_high': None,
                'nearest_low': None,
                'swings': []
            }
        
        # 1. اكتشاف Swing Points
        swing_highs, swing_lows = self._detect_swing_points(df)
        
        if not swing_highs and not swing_lows:
            return {
                'state': ContextState.MID,
                'nearest_high': None,
                'nearest_low': None,
                'swings': []
            }
        
        # 2. تحديد أقرب قمة وقاع
        nearest_high = max(swing_highs) if swing_highs else None
        nearest_low = min(swing_lows) if swing_lows else None
        
        # 3. حساب المسافة من المستويات
        state = ContextState.MID
        
        if nearest_high and nearest_low:
            range_size = nearest_high - nearest_low
            position_in_range = (current_price - nearest_low) / range_size if range_size > 0 else 0.5
            
            # قرب القمة (أعلى 95% من النطاق) - أقل صرامة
            if position_in_range >= 0.95:
                state = ContextState.HIGH
            # قرب القاع (أسفل 5% من النطاق) - أقل صرامة
            elif position_in_range <= 0.05:
                state = ContextState.LOW
            else:
                state = ContextState.MID
        
        elif nearest_high:
            dist_pct = (nearest_high - current_price) / current_price
            if dist_pct <= self.ZONE_THRESHOLD_PCT:
                state = ContextState.HIGH
        
        elif nearest_low:
            dist_pct = (current_price - nearest_low) / current_price
            if dist_pct <= self.ZONE_THRESHOLD_PCT:
                state = ContextState.LOW
        
        return {
            'state': state,
            'nearest_high': nearest_high,
            'nearest_low': nearest_low,
            'swings': {'highs': swing_highs, 'lows': swing_lows}
        }
    
    def _detect_swing_points(self, df: pd.DataFrame) -> Tuple[List[float], List[float]]:
        """
        اكتشاف نقاط Swing (القمم والقيعان)
        
        Swing High: شمعة أعلى من N شموع قبلها وبعدها
        Swing Low: شمعة أدنى من N شموع قبلها وبعدها
        """
        lookback = min(self.SWING_LOOKBACK, len(df) // 4)
        if lookback < 3:
            return [], []
        
        highs = df['high'].values
        lows = df['low'].values
        
        swing_highs = []
        swing_lows = []
        
        for i in range(lookback, len(df) - lookback):
            # Swing High
            is_swing_high = True
            for j in range(1, lookback + 1):
                if highs[i] <= highs[i - j] or highs[i] <= highs[i + j]:
                    is_swing_high = False
                    break
            if is_swing_high:
                swing_highs.append(highs[i])
            
            # Swing Low
            is_swing_low = True
            for j in range(1, lookback + 1):
                if lows[i] >= lows[i - j] or lows[i] >= lows[i + j]:
                    is_swing_low = False
                    break
            if is_swing_low:
                swing_lows.append(lows[i])
        
        # الاحتفاظ بأحدث القمم والقيعان فقط
        return swing_highs[-5:], swing_lows[-5:]
    
    def _detect_trend(self, df: pd.DataFrame) -> TrendDirection:
        """
        تحديد اتجاه الترند باستخدام:
        - EMA 20/50 Cross
        - Higher Highs / Higher Lows Pattern
        - ADX for trend strength
        """
        if df is None or len(df) < 50:
            return TrendDirection.RANGING
        
        close = df['close'].values
        
        # EMA Cross
        ema_20 = pd.Series(close).ewm(span=20, adjust=False).mean().iloc[-1]
        ema_50 = pd.Series(close).ewm(span=50, adjust=False).mean().iloc[-1]
        
        # Swing Pattern
        swing_highs, swing_lows = self._detect_swing_points(df)
        
        # Higher Highs / Higher Lows
        hh_hl = False
        lh_ll = False
        
        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            hh_hl = swing_highs[-1] > swing_highs[-2] and swing_lows[-1] > swing_lows[-2]
            lh_ll = swing_highs[-1] < swing_highs[-2] and swing_lows[-1] < swing_lows[-2]
        
        # Combined Decision
        if ema_20 > ema_50 and hh_hl:
            return TrendDirection.BULLISH
        elif ema_20 < ema_50 and lh_ll:
            return TrendDirection.BEARISH
        elif ema_20 > ema_50:
            return TrendDirection.BULLISH
        elif ema_20 < ema_50:
            return TrendDirection.BEARISH
        else:
            return TrendDirection.RANGING
    
    def _resolve_context(self, htf_state: ContextState, 
                        etf_state: ContextState) -> ContextState:
        """
        دمج حالات الإطارين الزمنيين
        
        القاعدة: HTF يسيطر دائماً
        """
        # HTF UNKNOWN = كل شيء UNKNOWN
        if htf_state == ContextState.UNKNOWN:
            return ContextState.UNKNOWN
        
        # HTF HIGH = النتيجة HIGH (حتى لو ETF مختلف)
        if htf_state == ContextState.HIGH:
            return ContextState.HIGH
        
        # HTF LOW = النتيجة LOW
        if htf_state == ContextState.LOW:
            return ContextState.LOW
        
        # HTF MID = ETF يحدد
        return etf_state
    
    def _get_permitted_actions(self, state: ContextState, 
                              trend: TrendDirection) -> List[str]:
        """
        تحديد الإجراءات المسموحة بناءً على السياق
        """
        if state == ContextState.UNKNOWN:
            return ['TRADE_MANAGEMENT', 'EXIT', 'REDUCE_RISK']
        
        if state == ContextState.HIGH:
            actions = ['EXIT', 'PARTIAL_PROFIT', 'REDUCE_RISK', 'TRAILING_STOP']
            # Short مسموح فقط في ترند هابط
            if trend == TrendDirection.BEARISH:
                actions.append('SHORT_WITH_CONFIRMATION')
            return actions
        
        if state == ContextState.LOW:
            actions = ['EXIT', 'TRADE_MANAGEMENT']
            # Long مسموح فقط في ترند صاعد
            if trend == TrendDirection.BULLISH:
                actions.append('LONG_WITH_CONFIRMATION')
            return actions
        
        # MID = كل الإجراءات مسموحة
        return ['LONG', 'SHORT', 'EXIT', 'SCALE_IN', 'SCALE_OUT', 
                'TRADE_MANAGEMENT', 'FULL_STRATEGY']
    
    def _calculate_confidence(self, htf_result: Dict, etf_result: Dict) -> float:
        """حساب درجة الثقة في التحليل"""
        confidence = 0.5
        
        # تطابق الإطارين يزيد الثقة
        if htf_result['state'] == etf_result['state']:
            confidence += 0.3
        
        # وجود swing points يزيد الثقة
        if htf_result.get('swings'):
            if htf_result['swings'].get('highs') and htf_result['swings'].get('lows'):
                confidence += 0.2
        
        return min(confidence, 1.0)
    
    def is_long_allowed(self, context: MarketContext) -> Tuple[bool, str]:
        """
        هل الشراء مسموح؟
        
        Returns:
            (allowed, reason)
        """
        # في الترند الصاعد، HIGH لا يمنع الشراء لكن يُحذّر
        if context.state == ContextState.HIGH and context.trend == TrendDirection.BULLISH:
            return True, "⚠️ قرب قمة في ترند صاعد - شراء بحذر"
        
        if context.state == ContextState.HIGH:
            return True, "⚠️ قرب قمة - تقليل الحجم"  # تحذير بدلاً من منع
        
        if context.state == ContextState.UNKNOWN:
            return True, "⚠️ السياق غير واضح - تداول بحذر"
        
        return True, "✅ الشراء مسموح"
    
    def is_short_allowed(self, context: MarketContext) -> Tuple[bool, str]:
        """
        هل البيع مسموح؟
        
        Returns:
            (allowed, reason)
        """
        if context.state == ContextState.LOW:
            return False, "السعر قرب قاع هيكلي - البيع ممنوع"
        
        if context.state == ContextState.UNKNOWN:
            return False, "السياق غير واضح - جميع الصفقات ممنوعة"
        
        if 'SHORT' in context.permitted_actions or 'SHORT_WITH_CONFIRMATION' in context.permitted_actions:
            return True, "البيع مسموح"
        
        return False, "البيع غير مسموح في هذا السياق"
    
    def get_position_size_multiplier(self, context: MarketContext) -> float:
        """
        معامل تعديل حجم الصفقة بناءً على السياق
        
        Returns:
            0.0-1.0 (0.5 = نصف الحجم، 1.0 = حجم كامل)
        """
        # MID = حجم كامل
        if context.state == ContextState.MID:
            return 1.0
        
        # HIGH في ترند صاعد = 70% من الحجم
        if context.state == ContextState.HIGH:
            if context.trend == TrendDirection.BULLISH:
                return 0.7
            return 0.5  # HIGH في ترند هابط = 50%
        
        # LOW = حجم كامل للشراء
        if context.state == ContextState.LOW:
            if context.trend == TrendDirection.BULLISH:
                return 1.0  # فرصة جيدة للشراء
            return 0.7
        
        # UNKNOWN = نصف الحجم
        return 0.5
    
    def get_context_summary(self, context: MarketContext) -> str:
        """ملخص السياق للعرض"""
        emoji = {
            ContextState.HIGH: "🔴",
            ContextState.LOW: "🟢", 
            ContextState.MID: "🟡",
            ContextState.UNKNOWN: "⚪"
        }
        
        return (
            f"{emoji[context.state]} Structure: {context.state.value} | "
            f"Trend: {context.trend.value} | "
            f"Confidence: {context.confidence*100:.0f}% | "
            f"Dist to High: {context.distance_to_high_pct:.1f}% | "
            f"Dist to Low: {context.distance_to_low_pct:.1f}%"
        )


# Singleton instance
_market_structure_layer = None

def get_market_structure_layer(htf: str = '4h', etf: str = '1h') -> MarketStructureLayer:
    """الحصول على instance واحد"""
    global _market_structure_layer
    if _market_structure_layer is None:
        _market_structure_layer = MarketStructureLayer(htf=htf, etf=etf)
    return _market_structure_layer
