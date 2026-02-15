#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Market Regime Detector - كاشف حالة السوق
يحدد حالة السوق (Bull/Bear/Sideways) لتحسين قرارات التداول
"""

import numpy as np
import pandas as pd
from typing import Dict, Literal, Tuple
import logging

MarketRegime = Literal['bull', 'bear', 'sideways', 'volatile']

class MarketRegimeDetector:
    """
    كاشف حالة السوق باستخدام مؤشرات متعددة
    
    المنطق:
    - Bull: اتجاه صاعد قوي (EMA 20 > EMA 50, ADX > 25, RSI > 50)
    - Bear: اتجاه هابط قوي (EMA 20 < EMA 50, ADX > 25, RSI < 50)
    - Sideways: تذبذب جانبي (ADX < 25)
    - Volatile: تقلبات عالية (ATR > 5%)
    """
    
    # العتبات
    ADX_TREND_THRESHOLD = 25.0      # ADX > 25 = اتجاه قوي
    ATR_VOLATILITY_THRESHOLD = 5.0  # ATR > 5% = تقلبات عالية
    RSI_NEUTRAL_LOW = 45.0          # RSI < 45 = ضغط بيعي
    RSI_NEUTRAL_HIGH = 55.0         # RSI > 55 = ضغط شرائي
    
    def __init__(self, logger=None):
        """تهيئة الكاشف"""
        self.logger = logger or logging.getLogger(__name__)
    
    def detect_regime(self, df: pd.DataFrame, symbol: str = None) -> Dict:
        """
        كشف حالة السوق من البيانات
        
        Args:
            df: DataFrame مع الأعمدة: close, high, low, volume
            symbol: رمز العملة (اختياري)
        
        Returns:
            Dict مع الحالة والثقة والتفاصيل
        """
        try:
            if df is None or len(df) < 50:
                return self._default_regime("بيانات غير كافية")
            
            # حساب المؤشرات
            indicators = self._calculate_indicators(df)
            
            # تحديد الحالة
            regime, confidence, reasons = self._determine_regime(indicators)
            
            return {
                'regime': regime,
                'confidence': confidence,
                'reasons': reasons,
                'indicators': indicators,
                'symbol': symbol,
                'timestamp': pd.Timestamp.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في كشف حالة السوق: {e}")
            return self._default_regime(f"خطأ: {e}")
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """حساب المؤشرات الفنية"""
        try:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            
            # EMA 20 و 50
            ema_20 = self._ema(close, 20)
            ema_50 = self._ema(close, 50)
            ema_trend = 'up' if ema_20 > ema_50 else 'down'
            ema_distance = ((ema_20 - ema_50) / ema_50) * 100
            
            # ADX (قوة الاتجاه)
            adx = self._calculate_adx(high, low, close, period=14)
            
            # RSI
            rsi = self._calculate_rsi(close, period=14)
            
            # ATR (التقلب)
            atr = self._calculate_atr(high, low, close, period=14)
            atr_pct = (atr / close[-1]) * 100
            
            # تغير السعر
            price_change_pct = ((close[-1] - close[-50]) / close[-50]) * 100
            
            return {
                'ema_20': float(ema_20),
                'ema_50': float(ema_50),
                'ema_trend': ema_trend,
                'ema_distance': float(ema_distance),
                'adx': float(adx),
                'rsi': float(rsi),
                'atr_pct': float(atr_pct),
                'price_change_pct': float(price_change_pct),
                'current_price': float(close[-1])
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في حساب المؤشرات: {e}")
            return {}
    
    def _determine_regime(self, indicators: Dict) -> Tuple[MarketRegime, float, list]:
        """تحديد حالة السوق"""
        if not indicators:
            return 'sideways', 0.5, ['بيانات غير كافية']
        
        ema_trend = indicators.get('ema_trend', 'unknown')
        ema_distance = abs(indicators.get('ema_distance', 0))
        adx = indicators.get('adx', 0)
        rsi = indicators.get('rsi', 50)
        atr_pct = indicators.get('atr_pct', 0)
        price_change = indicators.get('price_change_pct', 0)
        
        reasons = []
        scores = {'bull': 0, 'bear': 0, 'sideways': 0, 'volatile': 0}
        
        # 1. فحص التقلبات أولاً
        if atr_pct > self.ATR_VOLATILITY_THRESHOLD:
            scores['volatile'] += 3
            reasons.append(f"تقلبات عالية (ATR: {atr_pct:.1f}%)")
        
        # 2. فحص قوة الاتجاه (ADX)
        if adx > self.ADX_TREND_THRESHOLD:
            # اتجاه قوي - فحص الاتجاه
            if ema_trend == 'up' and rsi > self.RSI_NEUTRAL_HIGH:
                scores['bull'] += 3
                reasons.append(f"اتجاه صاعد قوي (ADX: {adx:.1f})")
            elif ema_trend == 'down' and rsi < self.RSI_NEUTRAL_LOW:
                scores['bear'] += 3
                reasons.append(f"اتجاه هابط قوي (ADX: {adx:.1f})")
            else:
                scores['sideways'] += 1
        else:
            # اتجاه ضعيف = جانبي
            scores['sideways'] += 3
            reasons.append(f"اتجاه ضعيف (ADX: {adx:.1f})")
        
        # 3. فحص EMA Distance
        if ema_distance > 2.0:
            if ema_trend == 'up':
                scores['bull'] += 2
                reasons.append(f"EMA متباعدة صعوداً ({ema_distance:.1f}%)")
            else:
                scores['bear'] += 2
                reasons.append(f"EMA متباعدة هبوطاً ({ema_distance:.1f}%)")
        elif ema_distance < 0.5:
            scores['sideways'] += 2
            reasons.append("EMA متقاربة")
        
        # 4. فحص RSI
        if rsi > 60:
            scores['bull'] += 1
            reasons.append(f"RSI صاعد ({rsi:.1f})")
        elif rsi < 40:
            scores['bear'] += 1
            reasons.append(f"RSI هابط ({rsi:.1f})")
        else:
            scores['sideways'] += 1
        
        # 5. فحص تغير السعر
        if abs(price_change) > 10:
            if price_change > 0:
                scores['bull'] += 1
            else:
                scores['bear'] += 1
        
        # اختيار الحالة الأعلى نقاطاً
        regime = max(scores, key=scores.get)
        max_score = scores[regime]
        total_score = sum(scores.values())
        confidence = max_score / total_score if total_score > 0 else 0.5
        
        return regime, confidence, reasons
    
    def _ema(self, data: np.ndarray, period: int) -> float:
        """حساب EMA"""
        if len(data) < period:
            return float(np.mean(data))
        
        multiplier = 2 / (period + 1)
        ema = np.mean(data[:period])
        
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        
        return float(ema)
    
    def _calculate_rsi(self, close: np.ndarray, period: int = 14) -> float:
        """حساب RSI"""
        if len(close) < period + 1:
            return 50.0
        
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    def _calculate_adx(self, high: np.ndarray, low: np.ndarray, 
                       close: np.ndarray, period: int = 14) -> float:
        """حساب ADX (مبسط)"""
        if len(close) < period + 1:
            return 0.0
        
        # حساب True Range
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                abs(high[1:] - close[:-1]),
                abs(low[1:] - close[:-1])
            )
        )
        
        # حساب +DM و -DM
        up_move = high[1:] - high[:-1]
        down_move = low[:-1] - low[1:]
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # حساب ATR و +DI و -DI
        atr = np.mean(tr[-period:])
        plus_di = 100 * np.mean(plus_dm[-period:]) / atr if atr > 0 else 0
        minus_di = 100 * np.mean(minus_dm[-period:]) / atr if atr > 0 else 0
        
        # حساب DX و ADX
        dx = 0
        if (plus_di + minus_di) > 0:
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        
        return float(dx)
    
    def _calculate_atr(self, high: np.ndarray, low: np.ndarray,
                       close: np.ndarray, period: int = 14) -> float:
        """حساب ATR"""
        if len(close) < period + 1:
            return 0.0
        
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                abs(high[1:] - close[:-1]),
                abs(low[1:] - close[:-1])
            )
        )
        
        atr = np.mean(tr[-period:])
        return float(atr)
    
    def _default_regime(self, reason: str) -> Dict:
        """حالة افتراضية عند الفشل"""
        return {
            'regime': 'sideways',
            'confidence': 0.5,
            'reasons': [reason],
            'indicators': {},
            'symbol': None,
            'timestamp': pd.Timestamp.now().isoformat()
        }
    
    def should_trade_in_regime(self, regime: MarketRegime, strategy: str) -> Tuple[bool, str]:
        """
        تحديد ما إذا كان يجب التداول في هذه الحالة
        
        Args:
            regime: حالة السوق
            strategy: اسم الاستراتيجية
        
        Returns:
            Tuple[bool, str]: (يجب التداول, السبب)
        """
        strategy_lower = strategy.lower()
        
        # TrendFollowing - يفضل Bull/Bear
        if 'trend' in strategy_lower:
            if regime in ['bull', 'bear']:
                return True, f"اتجاه واضح - مناسب لـ {strategy}"
            else:
                return False, "لا يوجد اتجاه واضح"
        
        # MeanReversion - يفضل Sideways
        if 'reversion' in strategy_lower or 'mean' in strategy_lower:
            if regime == 'sideways':
                return True, f"سوق جانبي - مناسب لـ {strategy}"
            else:
                return False, "سوق متجه - غير مناسب للـ Mean Reversion"
        
        # Scalping - يفضل Sideways/Volatile
        if 'scalp' in strategy_lower:
            if regime in ['sideways', 'volatile']:
                return True, f"حركة سريعة - مناسب لـ {strategy}"
            else:
                return False, "اتجاه قوي - غير مناسب للـ Scalping"
        
        # Momentum/Breakout - يفضل Bull/Volatile
        if 'momentum' in strategy_lower or 'breakout' in strategy_lower:
            if regime in ['bull', 'volatile']:
                return True, f"زخم قوي - مناسب لـ {strategy}"
            else:
                return False, "لا يوجد زخم كافي"
        
        # استراتيجيات أخرى - تداول عادي
        return True, "استراتيجية عامة"


# وظائف مساعدة للاستخدام السريع
def detect_market_regime(df: pd.DataFrame, symbol: str = None, logger=None) -> Dict:
    """
    وظيفة سريعة لكشف حالة السوق
    
    Args:
        df: البيانات
        symbol: رمز العملة
        logger: مسجل الأحداث
    
    Returns:
        حالة السوق
    """
    detector = MarketRegimeDetector(logger=logger)
    return detector.detect_regime(df, symbol)
