#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Market Surveillance Engine - نظام المراقبة الذكية للسوق
=====================================================

مهمته:
- المراقبة المستمرة دون دخول
- كشف تغيرات السلوك (Behavior Shift)
- كشف ضعف/تسارع الاتجاه
- تحديد متى السوق صالح/غير صالح للتداول
- تحديد متى السوق يقترب من فرصة

لا يتخذ قرارات تداول - فقط يراقب ويُبلّغ
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class MarketQuality(Enum):
    """جودة السوق للتداول"""
    EXCELLENT = "excellent"       # ظروف مثالية
    GOOD = "good"                 # ظروف جيدة
    FAIR = "fair"                 # مقبولة بحذر
    POOR = "poor"                 # غير مناسب
    DANGEROUS = "dangerous"       # خطر - لا تداول


class BehaviorSignal(Enum):
    """إشارات تغير السلوك"""
    TREND_WEAKENING = "trend_weakening"
    TREND_STRENGTHENING = "trend_strengthening"
    VOLATILITY_EXPANSION = "volatility_expansion"
    VOLATILITY_CONTRACTION = "volatility_contraction"
    MOMENTUM_DIVERGENCE = "momentum_divergence"
    VOLUME_ANOMALY = "volume_anomaly"
    STRUCTURE_BREAK = "structure_break"
    ACCUMULATION_DETECTED = "accumulation_detected"
    DISTRIBUTION_DETECTED = "distribution_detected"
    OPPORTUNITY_APPROACHING = "opportunity_approaching"
    NONE = "none"


class MarketPhase(Enum):
    """مراحل السوق (Wyckoff)"""
    ACCUMULATION = "accumulation"
    MARKUP = "markup"
    DISTRIBUTION = "distribution"
    MARKDOWN = "markdown"
    TRANSITION = "transition"
    UNKNOWN = "unknown"


@dataclass
class SurveillanceReport:
    """تقرير المراقبة"""
    symbol: str
    timestamp: datetime
    market_quality: MarketQuality
    market_phase: MarketPhase
    behavior_signals: List[BehaviorSignal]
    is_tradeable: bool
    opportunity_score: float  # 0-100
    risk_score: float  # 0-100
    
    # تفاصيل التحليل
    trend_health: float  # 0-100
    momentum_health: float  # 0-100
    volatility_state: str
    volume_profile: str
    structure_intact: bool
    
    reasoning: str
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'market_quality': self.market_quality.value,
            'market_phase': self.market_phase.value,
            'behavior_signals': [s.value for s in self.behavior_signals],
            'is_tradeable': self.is_tradeable,
            'opportunity_score': self.opportunity_score,
            'risk_score': self.risk_score,
            'trend_health': self.trend_health,
            'momentum_health': self.momentum_health,
            'reasoning': self.reasoning,
            'warnings': self.warnings,
        }


class MarketSurveillanceEngine:
    """
    نظام المراقبة الذكية
    
    يراقب باستمرار دون اتخاذ قرارات:
    1. صحة الاتجاه (Trend Health)
    2. صحة الزخم (Momentum Health)
    3. مرحلة السوق (Wyckoff Phase)
    4. جودة التداول (Market Quality)
    5. كشف الشذوذ (Anomaly Detection)
    6. قرب الفرص (Opportunity Proximity)
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logger
        
        # ذاكرة المراقبة - تتبع التغيرات عبر الزمن
        self._history: Dict[str, List[SurveillanceReport]] = {}
        self._max_history = 50
    
    def survey(self, symbol: str, df: pd.DataFrame,
               df_1h: Optional[pd.DataFrame] = None) -> SurveillanceReport:
        """
        تنفيذ مراقبة شاملة للعملة
        
        Args:
            symbol: رمز العملة
            df: بيانات 4H OHLCV
            df_1h: بيانات 1H اختيارية للتأكيد
        """
        try:
            if df is None or len(df) < 50:
                return self._empty_report(symbol, "بيانات غير كافية")
            
            signals = []
            warnings = []
            
            # 1. تحليل صحة الاتجاه
            trend_health = self._assess_trend_health(df)
            
            # 2. تحليل صحة الزخم
            momentum_health = self._assess_momentum_health(df)
            
            # 3. تحليل التقلب
            volatility_state = self._assess_volatility(df)
            
            # 4. تحليل الحجم
            volume_profile = self._assess_volume_profile(df)
            
            # 5. تحليل البنية
            structure_intact = self._check_structure_integrity(df)
            
            # 6. كشف مرحلة السوق (Wyckoff)
            market_phase = self._detect_market_phase(df)
            
            # 7. كشف تغيرات السلوك
            signals = self._detect_behavior_changes(
                df, trend_health, momentum_health, volatility_state, volume_profile
            )
            
            # 8. حساب جودة السوق
            market_quality = self._calculate_market_quality(
                trend_health, momentum_health, volatility_state,
                volume_profile, structure_intact
            )
            
            # 9. حساب نقاط الفرصة والمخاطرة
            opportunity_score = self._calculate_opportunity_score(
                trend_health, momentum_health, market_phase,
                volatility_state, signals
            )
            risk_score = self._calculate_risk_score(
                volatility_state, structure_intact, market_phase, df
            )
            
            # 10. تحديد قابلية التداول
            is_tradeable = (
                market_quality in [MarketQuality.EXCELLENT, MarketQuality.GOOD, MarketQuality.FAIR]
                and risk_score < 75
            )
            
            # 11. جمع التحذيرات
            if risk_score > 60:
                warnings.append(f"مخاطرة عالية ({risk_score:.0f}%)")
            if not structure_intact:
                warnings.append("البنية مكسورة")
            if volatility_state == 'extreme':
                warnings.append("تقلب شديد")
            if BehaviorSignal.MOMENTUM_DIVERGENCE in signals:
                warnings.append("تباعد في الزخم")
            
            # بناء التقرير
            reasoning = self._build_reasoning(
                symbol, market_quality, market_phase, trend_health,
                momentum_health, volatility_state, signals
            )
            
            report = SurveillanceReport(
                symbol=symbol,
                timestamp=datetime.now(),
                market_quality=market_quality,
                market_phase=market_phase,
                behavior_signals=signals if signals else [BehaviorSignal.NONE],
                is_tradeable=is_tradeable,
                opportunity_score=opportunity_score,
                risk_score=risk_score,
                trend_health=trend_health,
                momentum_health=momentum_health,
                volatility_state=volatility_state,
                volume_profile=volume_profile,
                structure_intact=structure_intact,
                reasoning=reasoning,
                warnings=warnings
            )
            
            # حفظ في الذاكرة
            self._store_report(symbol, report)
            
            self.logger.info(
                f"👁️ [{symbol}] Surveillance: {market_quality.value} | "
                f"Phase: {market_phase.value} | Opp: {opportunity_score:.0f}% | "
                f"Risk: {risk_score:.0f}% | Trade: {'✅' if is_tradeable else '❌'}"
            )
            
            return report
            
        except Exception as e:
            self.logger.error(f"خطأ في المراقبة [{symbol}]: {e}")
            return self._empty_report(symbol, f"خطأ: {e}")
    
    def _assess_trend_health(self, df: pd.DataFrame) -> float:
        """تقييم صحة الاتجاه (0-100)"""
        try:
            close = df['close']
            
            # EMA alignment
            ema_8 = close.ewm(span=8).mean()
            ema_21 = close.ewm(span=21).mean()
            ema_55 = close.ewm(span=55).mean() if len(close) >= 55 else ema_21
            
            score = 0
            
            # Price above EMAs (bullish trend health)
            current = close.iloc[-1]
            if current > ema_8.iloc[-1]:
                score += 20
            if current > ema_21.iloc[-1]:
                score += 20
            if current > ema_55.iloc[-1]:
                score += 15
            
            # EMA alignment (8 > 21 > 55)
            if ema_8.iloc[-1] > ema_21.iloc[-1]:
                score += 15
            if ema_21.iloc[-1] > ema_55.iloc[-1]:
                score += 10
            
            # Trend consistency (last 5 candles)
            recent = close.tail(5)
            if recent.is_monotonic_increasing:
                score += 10
            elif recent.iloc[-1] > recent.iloc[0]:
                score += 5
            
            # Higher lows check (last 10 candles)
            lows = df['low'].tail(10)
            if lows.iloc[-1] > lows.iloc[0] and lows.iloc[-3] > lows.iloc[0]:
                score += 10
            
            return min(100, score)
        except Exception as e:
            self.logger.debug(f"Trend health error: {e}")
            return 50
    
    def _assess_momentum_health(self, df: pd.DataFrame) -> float:
        """تقييم صحة الزخم (0-100)"""
        try:
            close = df['close']
            score = 0
            
            # RSI
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]
            
            # RSI في منطقة صحية (40-65 = أفضل للشراء)
            if 45 <= current_rsi <= 65:
                score += 30
            elif 35 <= current_rsi <= 75:
                score += 20
            elif current_rsi < 30:
                score += 15  # oversold = potential reversal
            else:
                score += 5
            
            # RSI trending (rising RSI)
            if len(rsi) > 5 and rsi.iloc[-1] > rsi.iloc[-5]:
                score += 15
            
            # MACD
            ema_12 = close.ewm(span=12).mean()
            ema_26 = close.ewm(span=26).mean()
            macd = ema_12 - ema_26
            signal = macd.ewm(span=9).mean()
            histogram = macd - signal
            
            # MACD above signal
            if macd.iloc[-1] > signal.iloc[-1]:
                score += 20
            
            # Histogram growing
            if len(histogram) > 2 and histogram.iloc[-1] > histogram.iloc[-2]:
                score += 15
            
            # Rate of change
            roc_5 = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] * 100 if len(close) > 5 else 0
            if roc_5 > 0:
                score += min(20, roc_5 * 5)
            
            return min(100, score)
        except Exception as e:
            self.logger.debug(f"Momentum health error: {e}")
            return 50
    
    def _assess_volatility(self, df: pd.DataFrame) -> str:
        """تقييم حالة التقلب"""
        try:
            close = df['close']
            
            # ATR-based volatility
            tr = pd.concat([
                df['high'] - df['low'],
                abs(df['high'] - close.shift(1)),
                abs(df['low'] - close.shift(1))
            ], axis=1).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]
            atr_pct = atr / close.iloc[-1]
            
            # Bollinger Band width
            sma_20 = close.rolling(20).mean()
            std_20 = close.rolling(20).std()
            bb_width = (2 * std_20.iloc[-1]) / sma_20.iloc[-1] if sma_20.iloc[-1] > 0 else 0
            
            if atr_pct > 0.06 or bb_width > 0.08:
                return 'extreme'
            elif atr_pct > 0.04 or bb_width > 0.06:
                return 'high'
            elif atr_pct > 0.02 or bb_width > 0.03:
                return 'normal'
            else:
                return 'low'
        except Exception as e:
            self.logger.debug(f"Volatility assessment error: {e}")
            return 'normal'
    
    def _assess_volume_profile(self, df: pd.DataFrame) -> str:
        """تقييم ملف الحجم"""
        try:
            vol = df['volume']
            avg_20 = vol.rolling(20).mean().iloc[-1]
            current = vol.iloc[-1]
            ratio = current / avg_20 if avg_20 > 0 else 1
            
            # Check volume trend (5 candles)
            vol_trend = vol.tail(5).mean() / avg_20 if avg_20 > 0 else 1
            
            if ratio > 2.0:
                return 'spike'
            elif ratio > 1.3:
                return 'above_average'
            elif ratio > 0.7:
                return 'normal'
            elif vol_trend < 0.5:
                return 'drying_up'
            else:
                return 'below_average'
        except Exception as e:
            self.logger.debug(f"Volume profile error: {e}")
            return 'normal'
    
    def _check_structure_integrity(self, df: pd.DataFrame) -> bool:
        """فحص سلامة بنية السوق"""
        try:
            close = df['close']
            high = df['high']
            low = df['low']
            
            # Check for Higher Highs and Higher Lows (bullish structure)
            recent_highs = high.tail(20)
            recent_lows = low.tail(20)
            
            # Find swing points (simplified)
            swing_high_1 = recent_highs.iloc[-10:].max()
            swing_high_2 = recent_highs.iloc[:10].max()
            swing_low_1 = recent_lows.iloc[-10:].min()
            swing_low_2 = recent_lows.iloc[:10].min()
            
            # Bullish structure: HH + HL
            bullish = swing_high_1 >= swing_high_2 and swing_low_1 >= swing_low_2
            # Bearish structure: LH + LL
            bearish = swing_high_1 <= swing_high_2 and swing_low_1 <= swing_low_2
            
            # Structure is intact if either bullish or bearish pattern holds
            return bullish or bearish
        except Exception as e:
            self.logger.debug(f"Structure check error: {e}")
            return True
    
    def _detect_market_phase(self, df: pd.DataFrame) -> MarketPhase:
        """كشف مرحلة السوق (Wyckoff)"""
        try:
            close = df['close']
            volume = df['volume']
            
            # Price trend (20 candles)
            price_change = (close.iloc[-1] - close.iloc[-20]) / close.iloc[-20] * 100
            
            # Volume trend
            vol_early = volume.iloc[-20:-10].mean()
            vol_late = volume.iloc[-10:].mean()
            vol_change = (vol_late - vol_early) / vol_early if vol_early > 0 else 0
            
            # Volatility trend
            atr_early = (df['high'] - df['low']).iloc[-20:-10].mean()
            atr_late = (df['high'] - df['low']).iloc[-10:].mean()
            vol_expanding = atr_late > atr_early * 1.1
            vol_contracting = atr_late < atr_early * 0.9
            
            # Accumulation: Price flat/down, volume increasing, volatility contracting
            if abs(price_change) < 3 and vol_change > 0.1 and vol_contracting:
                return MarketPhase.ACCUMULATION
            
            # Markup: Price up, volume supporting, momentum positive
            if price_change > 3 and vol_change > -0.2:
                return MarketPhase.MARKUP
            
            # Distribution: Price flat/up slightly, volume decreasing, volatility expanding
            if abs(price_change) < 3 and vol_change < -0.1 and vol_expanding:
                return MarketPhase.DISTRIBUTION
            
            # Markdown: Price down, volume may spike
            if price_change < -3:
                return MarketPhase.MARKDOWN
            
            return MarketPhase.TRANSITION
            
        except Exception as e:
            self.logger.debug(f"Phase detection error: {e}")
            return MarketPhase.UNKNOWN
    
    def _detect_behavior_changes(self, df: pd.DataFrame, trend_health: float,
                                  momentum_health: float, volatility_state: str,
                                  volume_profile: str) -> List[BehaviorSignal]:
        """كشف تغيرات السلوك"""
        signals = []
        
        try:
            close = df['close']
            
            # Trend weakening
            if trend_health < 40:
                signals.append(BehaviorSignal.TREND_WEAKENING)
            elif trend_health > 75:
                signals.append(BehaviorSignal.TREND_STRENGTHENING)
            
            # Volatility changes
            if volatility_state == 'extreme':
                signals.append(BehaviorSignal.VOLATILITY_EXPANSION)
            elif volatility_state == 'low':
                signals.append(BehaviorSignal.VOLATILITY_CONTRACTION)
            
            # Volume anomaly
            if volume_profile == 'spike':
                signals.append(BehaviorSignal.VOLUME_ANOMALY)
            
            # Momentum divergence (price up but momentum down)
            if len(close) > 10:
                price_up = close.iloc[-1] > close.iloc[-10]
                # Simple momentum check
                ema_12 = close.ewm(span=12).mean()
                ema_26 = close.ewm(span=26).mean()
                macd = ema_12 - ema_26
                macd_falling = macd.iloc[-1] < macd.iloc[-5] if len(macd) > 5 else False
                
                if price_up and macd_falling:
                    signals.append(BehaviorSignal.MOMENTUM_DIVERGENCE)
            
            # Structure break
            if not self._check_structure_integrity(df):
                signals.append(BehaviorSignal.STRUCTURE_BREAK)
            
            # Opportunity approaching (high trend + high momentum + normal vol)
            if trend_health > 60 and momentum_health > 60 and volatility_state in ['normal', 'low']:
                signals.append(BehaviorSignal.OPPORTUNITY_APPROACHING)
            
        except Exception as e:
            self.logger.debug(f"Behavior detection error: {e}")
        
        return signals
    
    def _calculate_market_quality(self, trend_health: float, momentum_health: float,
                                   volatility_state: str, volume_profile: str,
                                   structure_intact: bool) -> MarketQuality:
        """حساب جودة السوق"""
        score = 0
        
        # Trend health (30%)
        score += (trend_health / 100) * 30
        
        # Momentum health (25%)
        score += (momentum_health / 100) * 25
        
        # Structure (20%)
        score += 20 if structure_intact else 0
        
        # Volatility (15%)
        vol_scores = {'low': 10, 'normal': 15, 'high': 8, 'extreme': 0}
        score += vol_scores.get(volatility_state, 10)
        
        # Volume (10%)
        vol_profile_scores = {'above_average': 10, 'normal': 8, 'spike': 5,
                              'below_average': 4, 'drying_up': 2}
        score += vol_profile_scores.get(volume_profile, 5)
        
        if score >= 88:
            return MarketQuality.EXCELLENT
        elif score >= 72:
            return MarketQuality.GOOD
        elif score >= 50:
            return MarketQuality.FAIR
        elif score >= 30:
            return MarketQuality.POOR
        else:
            return MarketQuality.DANGEROUS
    
    def _calculate_opportunity_score(self, trend_health: float, momentum_health: float,
                                      market_phase: MarketPhase, volatility_state: str,
                                      signals: List[BehaviorSignal]) -> float:
        """حساب نقاط الفرصة (0-100)"""
        score = 0
        
        # Trend + Momentum base
        score += (trend_health * 0.3) + (momentum_health * 0.3)
        
        # Phase bonus
        phase_bonus = {
            MarketPhase.ACCUMULATION: 20,
            MarketPhase.MARKUP: 15,
            MarketPhase.TRANSITION: 5,
            MarketPhase.DISTRIBUTION: -10,
            MarketPhase.MARKDOWN: -20,
        }
        score += phase_bonus.get(market_phase, 0)
        
        # Volatility (normal is best for entries)
        if volatility_state == 'normal':
            score += 10
        elif volatility_state == 'low':
            score += 15  # compression = potential breakout
        
        # Opportunity signal bonus
        if BehaviorSignal.OPPORTUNITY_APPROACHING in signals:
            score += 10
        
        return max(0, min(100, score))
    
    def _calculate_risk_score(self, volatility_state: str, structure_intact: bool,
                               market_phase: MarketPhase, df: pd.DataFrame) -> float:
        """حساب نقاط المخاطرة (0-100)"""
        score = 0
        
        # Volatility risk
        vol_risk = {'low': 10, 'normal': 20, 'high': 50, 'extreme': 80}
        score += vol_risk.get(volatility_state, 30) * 0.3
        
        # Structure risk
        if not structure_intact:
            score += 25
        
        # Phase risk
        phase_risk = {
            MarketPhase.ACCUMULATION: 20,
            MarketPhase.MARKUP: 15,
            MarketPhase.DISTRIBUTION: 60,
            MarketPhase.MARKDOWN: 80,
            MarketPhase.TRANSITION: 40,
        }
        score += phase_risk.get(market_phase, 30) * 0.3
        
        # Drawdown risk (distance from recent high)
        try:
            current = df['close'].iloc[-1]
            recent_high = df['high'].tail(20).max()
            drawdown = (recent_high - current) / recent_high * 100
            if drawdown > 10:
                score += 20
            elif drawdown > 5:
                score += 10
        except Exception:
            pass
        
        return max(0, min(100, score))
    
    def _build_reasoning(self, symbol: str, quality: MarketQuality, phase: MarketPhase,
                          trend_h: float, momentum_h: float, volatility: str,
                          signals: List[BehaviorSignal]) -> str:
        """بناء نص التحليل"""
        signals_text = ', '.join(s.value for s in signals) if signals else 'none'
        return (
            f"[{symbol}] Quality: {quality.value} | Phase: {phase.value} | "
            f"Trend: {trend_h:.0f}% | Momentum: {momentum_h:.0f}% | "
            f"Volatility: {volatility} | Signals: {signals_text}"
        )
    
    def _store_report(self, symbol: str, report: SurveillanceReport):
        """حفظ التقرير في الذاكرة"""
        if symbol not in self._history:
            self._history[symbol] = []
        self._history[symbol].append(report)
        if len(self._history[symbol]) > self._max_history:
            self._history[symbol] = self._history[symbol][-self._max_history:]
    
    def get_history(self, symbol: str, limit: int = 10) -> List[SurveillanceReport]:
        """جلب تاريخ المراقبة"""
        return self._history.get(symbol, [])[-limit:]
    
    def has_behavior_changed(self, symbol: str) -> bool:
        """هل تغير سلوك السوق مؤخراً؟"""
        history = self.get_history(symbol, 3)
        if len(history) < 2:
            return False
        return history[-1].market_quality != history[-2].market_quality
    
    def _empty_report(self, symbol: str, reason: str) -> SurveillanceReport:
        return SurveillanceReport(
            symbol=symbol, timestamp=datetime.now(),
            market_quality=MarketQuality.POOR, market_phase=MarketPhase.UNKNOWN,
            behavior_signals=[BehaviorSignal.NONE], is_tradeable=False,
            opportunity_score=0, risk_score=100,
            trend_health=0, momentum_health=0,
            volatility_state='unknown', volume_profile='unknown',
            structure_intact=False, reasoning=reason, warnings=[reason]
        )


# Singleton
_surveillance_engine = None

def get_surveillance_engine(config: Optional[Dict] = None) -> MarketSurveillanceEngine:
    global _surveillance_engine
    if _surveillance_engine is None:
        _surveillance_engine = MarketSurveillanceEngine(config)
    return _surveillance_engine
