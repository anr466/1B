#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧭 Market State Classifier - تصنيف حالة السوق
==============================================

WindSurf Law Mandatory Requirement:
"No classification → No trade"

الحالات:
- STRONG_UPTREND: صعود قوي
- UPTREND: صعود
- RANGE: نطاق جانبي
- DOWNTREND: هبوط
- STRONG_DOWNTREND: هبوط قوي
- NEAR_TOP: قرب قمة
- NEAR_BOTTOM: قرب قاع

تاريخ الإنشاء: 2026-01-31
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class MarketState(Enum):
    """حالات السوق"""
    STRONG_UPTREND = "strong_uptrend"
    UPTREND = "uptrend"
    RANGE = "range"
    DOWNTREND = "downtrend"
    STRONG_DOWNTREND = "strong_downtrend"
    NEAR_TOP = "near_top"
    NEAR_BOTTOM = "near_bottom"
    UNKNOWN = "unknown"


@dataclass
class MarketStateAnalysis:
    """نتيجة تحليل حالة السوق"""
    state: MarketState
    confidence: int
    trend_strength: float
    price_position: str
    volume_trend: str
    momentum: str
    details: Dict


class MarketStateClassifier:
    """
    مُصنف حالة السوق
    
    يستخدم:
    1. EMA Alignment (50, 100, 200)
    2. ADX (قوة الاتجاه)
    3. RSI (momentum & extremes)
    4. Price position relative to EMAs
    5. Volume trend
    6. MACD
    """
    
    def __init__(self):
        self.logger = logger
        self.config = {
            'ema_periods': [50, 100, 200],
            'adx_strong_threshold': 25,
            'adx_very_strong_threshold': 40,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'rsi_extreme_oversold': 20,
            'rsi_extreme_overbought': 80,
        }
    
    def classify(
        self,
        df: pd.DataFrame,
        idx: int = -1
    ) -> MarketStateAnalysis:
        """
        تصنيف حالة السوق
        
        Args:
            df: DataFrame with OHLCV + indicators
            idx: Index to analyze (default: latest)
            
        Returns:
            MarketStateAnalysis
        """
        if len(df) < 200:
            return MarketStateAnalysis(
                state=MarketState.UNKNOWN,
                confidence=0,
                trend_strength=0,
                price_position="insufficient_data",
                volume_trend="unknown",
                momentum="unknown",
                details={"error": "Need at least 200 candles"}
            )
        
        row = df.iloc[idx]
        price = row['close']
        
        # حساب المؤشرات إن لم تكن موجودة
        df = self._ensure_indicators(df)
        row = df.iloc[idx]
        
        # 1. تحليل الاتجاه (EMA Alignment)
        trend_score, trend_details = self._analyze_trend(df, idx)
        
        # 2. قوة الاتجاه (ADX)
        trend_strength, adx_details = self._analyze_trend_strength(df, idx)
        
        # 3. موقع السعر
        price_position, position_details = self._analyze_price_position(df, idx)
        
        # 4. الزخم (RSI + MACD)
        momentum, momentum_details = self._analyze_momentum(df, idx)
        
        # 5. حجم التداول
        volume_trend, volume_details = self._analyze_volume(df, idx)
        
        # 6. دمج التحليلات لتحديد الحالة
        state, confidence = self._determine_state(
            trend_score=trend_score,
            trend_strength=trend_strength,
            price_position=price_position,
            momentum=momentum,
            volume_trend=volume_trend,
            row=row
        )
        
        # جمع التفاصيل
        details = {
            'trend': trend_details,
            'strength': adx_details,
            'position': position_details,
            'momentum': momentum_details,
            'volume': volume_details
        }
        
        return MarketStateAnalysis(
            state=state,
            confidence=confidence,
            trend_strength=trend_strength,
            price_position=price_position,
            volume_trend=volume_trend,
            momentum=momentum,
            details=details
        )
    
    def _ensure_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """التأكد من وجود المؤشرات"""
        df = df.copy()
        
        # EMAs
        for period in [50, 100, 200]:
            col = f'ema_{period}'
            if col not in df.columns:
                df[col] = df['close'].ewm(span=period, adjust=False).mean()
        
        # RSI
        if 'rsi' not in df.columns:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / (loss + 1e-10)
            df['rsi'] = 100 - (100 / (1 + rs))
        
        # ADX
        if 'adx' not in df.columns:
            high, low, close = df['high'], df['low'], df['close']
            
            plus_dm = high.diff()
            minus_dm = -low.diff()
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()
            
            plus_di = 100 * (plus_dm.rolling(14).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(14).mean() / atr)
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
            df['adx'] = dx.rolling(14).mean()
        
        # MACD
        if 'macd' not in df.columns:
            ema12 = df['close'].ewm(span=12, adjust=False).mean()
            ema26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = ema12 - ema26
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Volume MA
        if 'volume_ma' not in df.columns:
            df['volume_ma'] = df['volume'].rolling(20).mean()
        
        return df
    
    def _analyze_trend(self, df: pd.DataFrame, idx: int) -> Tuple[float, Dict]:
        """تحليل الاتجاه عبر EMA Alignment"""
        row = df.iloc[idx]
        price = row['close']
        ema50 = row.get('ema_50', 0)
        ema100 = row.get('ema_100', 0)
        ema200 = row.get('ema_200', 0)
        
        score = 0
        
        # Price vs EMAs (40 points)
        if price > ema50:
            score += 15
        if price > ema100:
            score += 12
        if price > ema200:
            score += 13
        
        # EMA Alignment (30 points)
        if ema50 > ema100:
            score += 15
        if ema100 > ema200:
            score += 15
        
        # EMA Slope (30 points)
        if idx >= 5:
            ema50_slope = (row['ema_50'] - df['ema_50'].iloc[idx-5]) / df['ema_50'].iloc[idx-5]
            ema100_slope = (row['ema_100'] - df['ema_100'].iloc[idx-5]) / df['ema_100'].iloc[idx-5]
            
            if ema50_slope > 0:
                score += 15
            if ema100_slope > 0:
                score += 15
        
        details = {
            'score': score,
            'price_vs_ema50': 'above' if price > ema50 else 'below',
            'price_vs_ema100': 'above' if price > ema100 else 'below',
            'price_vs_ema200': 'above' if price > ema200 else 'below',
            'ema_aligned': ema50 > ema100 > ema200
        }
        
        return score, details
    
    def _analyze_trend_strength(self, df: pd.DataFrame, idx: int) -> Tuple[float, Dict]:
        """تحليل قوة الاتجاه عبر ADX"""
        row = df.iloc[idx]
        adx = row.get('adx', 0)
        
        if adx >= self.config['adx_very_strong_threshold']:
            strength = 'very_strong'
        elif adx >= self.config['adx_strong_threshold']:
            strength = 'strong'
        else:
            strength = 'weak'
        
        details = {
            'adx': round(adx, 2),
            'strength': strength
        }
        
        return adx, details
    
    def _analyze_price_position(self, df: pd.DataFrame, idx: int) -> Tuple[str, Dict]:
        """تحليل موقع السعر"""
        row = df.iloc[idx]
        price = row['close']
        
        # حساب Bollinger Bands
        if 'bb_upper' not in df.columns:
            bb_mid = df['close'].rolling(20).mean()
            bb_std = df['close'].rolling(20).std()
            df['bb_upper'] = bb_mid + 2 * bb_std
            df['bb_lower'] = bb_mid - 2 * bb_std
            row = df.iloc[idx]
        
        bb_upper = row.get('bb_upper', price * 1.02)
        bb_lower = row.get('bb_lower', price * 0.98)
        
        # موقع السعر
        if price >= bb_upper * 0.98:
            position = 'near_top'
        elif price <= bb_lower * 1.02:
            position = 'near_bottom'
        elif price > (bb_upper + bb_lower) / 2:
            position = 'upper_half'
        else:
            position = 'lower_half'
        
        details = {
            'position': position,
            'bb_upper': round(bb_upper, 2),
            'bb_lower': round(bb_lower, 2),
            'price': round(price, 2)
        }
        
        return position, details
    
    def _analyze_momentum(self, df: pd.DataFrame, idx: int) -> Tuple[str, Dict]:
        """تحليل الزخم"""
        row = df.iloc[idx]
        rsi = row.get('rsi', 50)
        macd_hist = row.get('macd_hist', 0)
        
        # RSI
        if rsi >= self.config['rsi_extreme_overbought']:
            rsi_state = 'extreme_overbought'
        elif rsi >= self.config['rsi_overbought']:
            rsi_state = 'overbought'
        elif rsi <= self.config['rsi_extreme_oversold']:
            rsi_state = 'extreme_oversold'
        elif rsi <= self.config['rsi_oversold']:
            rsi_state = 'oversold'
        else:
            rsi_state = 'neutral'
        
        # MACD
        macd_state = 'bullish' if macd_hist > 0 else 'bearish'
        
        # Combined momentum
        if rsi_state in ['extreme_overbought', 'overbought'] and macd_state == 'bearish':
            momentum = 'weakening'
        elif rsi_state in ['extreme_oversold', 'oversold'] and macd_state == 'bullish':
            momentum = 'strengthening'
        elif rsi > 50 and macd_state == 'bullish':
            momentum = 'strong_bullish'
        elif rsi < 50 and macd_state == 'bearish':
            momentum = 'strong_bearish'
        else:
            momentum = 'neutral'
        
        details = {
            'rsi': round(rsi, 2),
            'rsi_state': rsi_state,
            'macd_hist': round(macd_hist, 6),
            'macd_state': macd_state,
            'momentum': momentum
        }
        
        return momentum, details
    
    def _analyze_volume(self, df: pd.DataFrame, idx: int) -> Tuple[str, Dict]:
        """تحليل حجم التداول"""
        row = df.iloc[idx]
        volume = row['volume']
        volume_ma = row.get('volume_ma', volume)
        
        if volume > volume_ma * 1.5:
            trend = 'high'
        elif volume > volume_ma * 1.2:
            trend = 'above_average'
        elif volume < volume_ma * 0.8:
            trend = 'low'
        else:
            trend = 'average'
        
        details = {
            'volume': int(volume),
            'volume_ma': int(volume_ma),
            'ratio': round(volume / volume_ma, 2),
            'trend': trend
        }
        
        return trend, details
    
    def _determine_state(
        self,
        trend_score: float,
        trend_strength: float,
        price_position: str,
        momentum: str,
        volume_trend: str,
        row: pd.Series
    ) -> Tuple[MarketState, int]:
        """تحديد حالة السوق النهائية"""
        rsi = row.get('rsi', 50)
        
        # NEAR_TOP / NEAR_BOTTOM (أولوية)
        if price_position == 'near_top' and rsi >= 70:
            return MarketState.NEAR_TOP, 85
        
        if price_position == 'near_bottom' and rsi <= 30:
            return MarketState.NEAR_BOTTOM, 85
        
        # STRONG_UPTREND
        if (trend_score >= 80 and 
            trend_strength >= 25 and 
            momentum in ['strong_bullish', 'strengthening']):
            confidence = min(95, int(trend_score + trend_strength / 2))
            return MarketState.STRONG_UPTREND, confidence
        
        # UPTREND
        if trend_score >= 60:
            confidence = min(85, int(trend_score))
            return MarketState.UPTREND, confidence
        
        # STRONG_DOWNTREND
        if (trend_score <= 20 and 
            trend_strength >= 25 and 
            momentum in ['strong_bearish', 'weakening']):
            confidence = min(95, int(100 - trend_score + trend_strength / 2))
            return MarketState.STRONG_DOWNTREND, confidence
        
        # DOWNTREND
        if trend_score <= 40:
            confidence = min(85, int(100 - trend_score))
            return MarketState.DOWNTREND, confidence
        
        # RANGE
        confidence = 70
        return MarketState.RANGE, confidence
    
    def is_tradeable_state(
        self,
        state: MarketState,
        strategy_type: str = 'trend_following'
    ) -> bool:
        """
        هل يمكن التداول في هذه الحالة؟
        
        Args:
            state: Market state
            strategy_type: 'trend_following', 'mean_reversion', 'momentum'
        """
        if strategy_type == 'trend_following':
            return state in [
                MarketState.STRONG_UPTREND,
                MarketState.UPTREND
            ]
        
        elif strategy_type == 'mean_reversion':
            return state in [
                MarketState.RANGE,
                MarketState.NEAR_BOTTOM
            ]
        
        elif strategy_type == 'momentum':
            return state in [
                MarketState.STRONG_UPTREND,
                MarketState.UPTREND,
                MarketState.NEAR_BOTTOM
            ]
        
        return False


# Singleton
_market_state_classifier = None

def get_market_state_classifier() -> MarketStateClassifier:
    """Get singleton instance"""
    global _market_state_classifier
    if _market_state_classifier is None:
        _market_state_classifier = MarketStateClassifier()
    return _market_state_classifier
