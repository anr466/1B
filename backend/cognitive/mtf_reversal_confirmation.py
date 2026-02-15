"""
Multi-Timeframe Reversal Confirmation System
نظام تأكيد الانعكاس متعدد الأطر الزمنية

الهدف:
- تأكيد الانعكاس الصعودي قبل الدخول (1H + 15m)
- تأكيد الانعكاس الهبوطي قبل الخروج (1H + 15m)
- موازنة التأخر في الشموع
- نظام مرن وموثوق
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum


class ReversalType(str, Enum):
    """نوع الانعكاس"""
    BULLISH = "bullish"  # صعودي
    BEARISH = "bearish"  # هبوطي
    NONE = "none"


class ReversalStrength(str, Enum):
    """قوة الانعكاس"""
    STRONG = "strong"          # قوي (80%+)
    MODERATE = "moderate"      # متوسط (60-80%)
    WEAK = "weak"              # ضعيف (40-60%)
    NONE = "none"              # لا يوجد


@dataclass
class ReversalSignal:
    """إشارة انعكاس"""
    type: ReversalType
    strength: ReversalStrength
    confidence: float  # 0-100
    timeframes_confirmed: List[str]  # الأطر المؤكدة
    patterns_detected: List[str]  # الأنماط المكتشفة
    indicators_aligned: int  # عدد المؤشرات الموافقة
    candles_since_reversal: int  # عدد الشموع منذ الانعكاس
    entry_quality: float  # جودة الدخول (0-100)
    reasoning: str


class MTFReversalConfirmation:
    """نظام تأكيد الانعكاس متعدد الأطر"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # معايير التأكيد (محدثة - منظور متداول محترف)
        # المتداول المحترف: يقبل ثقة 50-70% في سوق جيد
        self.MIN_CONFIDENCE_STRONG = 70    # كان 80 - صارم جداً
        self.MIN_CONFIDENCE_MODERATE = 50  # كان 60 - واقعي أكثر
        self.MIN_CONFIDENCE_WEAK = 30      # كان 40 - للأسواق الصعبة
        
        # التأخر المسموح
        self.MAX_CANDLES_DELAY = 3  # أقصى 3 شموع تأخر
        self.OPTIMAL_ENTRY_CANDLES = 1  # أفضل دخول بعد شمعة واحدة
        
        # وزن الأطر الزمنية
        self.TIMEFRAME_WEIGHTS = {
            '1h': 0.6,   # الإطار الأساسي
            '15m': 0.4,  # إطار التأكيد
        }
    
    def confirm_bullish_reversal(
        self,
        df_1h: pd.DataFrame,
        df_15m: pd.DataFrame,
        current_price: float
    ) -> ReversalSignal:
        """
        تأكيد الانعكاس الصعودي للدخول
        
        المنطق:
        1. كشف انعكاس على 1H
        2. تأكيد على 15m
        3. التحقق من المؤشرات
        4. حساب جودة الدخول
        """
        try:
            # 1. كشف الانعكاس على 1H
            reversal_1h = self._detect_bullish_reversal_signals(df_1h, '1h')
            
            # 2. تأكيد على 15m
            reversal_15m = self._detect_bullish_reversal_signals(df_15m, '15m')
            
            # 3. حساب الثقة الكلية
            confidence_1h = reversal_1h['confidence']
            confidence_15m = reversal_15m['confidence']
            
            total_confidence = (
                confidence_1h * self.TIMEFRAME_WEIGHTS['1h'] +
                confidence_15m * self.TIMEFRAME_WEIGHTS['15m']
            )
            
            # 4. تحديد الأطر المؤكدة
            confirmed_timeframes = []
            if reversal_1h['detected']:
                confirmed_timeframes.append('1h')
            if reversal_15m['detected']:
                confirmed_timeframes.append('15m')
            
            # 5. جمع الأنماط المكتشفة
            all_patterns = reversal_1h['patterns'] + reversal_15m['patterns']
            
            # 6. حساب المؤشرات الموافقة
            indicators_aligned = reversal_1h['indicators'] + reversal_15m['indicators']
            
            # 7. حساب التأخر (من 1H)
            candles_since = reversal_1h['candles_since_reversal']
            
            # 8. حساب جودة الدخول
            entry_quality = self._calculate_entry_quality(
                candles_since,
                total_confidence,
                len(confirmed_timeframes),
                indicators_aligned
            )
            
            # 9. تحديد القوة
            if total_confidence >= self.MIN_CONFIDENCE_STRONG:
                strength = ReversalStrength.STRONG
            elif total_confidence >= self.MIN_CONFIDENCE_MODERATE:
                strength = ReversalStrength.MODERATE
            elif total_confidence >= self.MIN_CONFIDENCE_WEAK:
                strength = ReversalStrength.WEAK
            else:
                strength = ReversalStrength.NONE
            
            # 10. التفسير
            reasoning = self._build_reasoning(
                'bullish', confirmed_timeframes, all_patterns,
                indicators_aligned, candles_since, entry_quality
            )
            
            return ReversalSignal(
                type=ReversalType.BULLISH if len(confirmed_timeframes) > 0 else ReversalType.NONE,
                strength=strength,
                confidence=total_confidence,
                timeframes_confirmed=confirmed_timeframes,
                patterns_detected=all_patterns,
                indicators_aligned=indicators_aligned,
                candles_since_reversal=candles_since,
                entry_quality=entry_quality,
                reasoning=reasoning
            )
            
        except Exception as e:
            self.logger.error(f"خطأ في تأكيد الانعكاس الصعودي: {e}")
            return self._default_signal()
    
    def confirm_bearish_reversal(
        self,
        df_1h: pd.DataFrame,
        df_15m: pd.DataFrame,
        current_price: float,
        entry_price: float
    ) -> ReversalSignal:
        """
        تأكيد الانعكاس الهبوطي للخروج
        
        المنطق:
        1. كشف انعكاس هبوطي على 1H
        2. تأكيد على 15m
        3. التحقق من المؤشرات
        4. قرار الخروج
        """
        try:
            # 1. كشف الانعكاس على 1H
            reversal_1h = self._detect_bearish_reversal_signals(df_1h, '1h')
            
            # 2. تأكيد على 15m
            reversal_15m = self._detect_bearish_reversal_signals(df_15m, '15m')
            
            # 3. حساب الثقة
            confidence_1h = reversal_1h['confidence']
            confidence_15m = reversal_15m['confidence']
            
            total_confidence = (
                confidence_1h * self.TIMEFRAME_WEIGHTS['1h'] +
                confidence_15m * self.TIMEFRAME_WEIGHTS['15m']
            )
            
            # 4. الأطر المؤكدة
            confirmed_timeframes = []
            if reversal_1h['detected']:
                confirmed_timeframes.append('1h')
            if reversal_15m['detected']:
                confirmed_timeframes.append('15m')
            
            # 5. الأنماط
            all_patterns = reversal_1h['patterns'] + reversal_15m['patterns']
            
            # 6. المؤشرات
            indicators_aligned = reversal_1h['indicators'] + reversal_15m['indicators']
            
            # 7. التأخر
            candles_since = reversal_1h['candles_since_reversal']
            
            # 8. جودة الخروج (عكس جودة الدخول)
            exit_quality = self._calculate_exit_quality(
                candles_since,
                total_confidence,
                len(confirmed_timeframes),
                indicators_aligned,
                current_price,
                entry_price
            )
            
            # 9. القوة
            if total_confidence >= self.MIN_CONFIDENCE_STRONG:
                strength = ReversalStrength.STRONG
            elif total_confidence >= self.MIN_CONFIDENCE_MODERATE:
                strength = ReversalStrength.MODERATE
            elif total_confidence >= self.MIN_CONFIDENCE_WEAK:
                strength = ReversalStrength.WEAK
            else:
                strength = ReversalStrength.NONE
            
            # 10. التفسير
            reasoning = self._build_reasoning(
                'bearish', confirmed_timeframes, all_patterns,
                indicators_aligned, candles_since, exit_quality
            )
            
            return ReversalSignal(
                type=ReversalType.BEARISH if len(confirmed_timeframes) > 0 else ReversalType.NONE,
                strength=strength,
                confidence=total_confidence,
                timeframes_confirmed=confirmed_timeframes,
                patterns_detected=all_patterns,
                indicators_aligned=indicators_aligned,
                candles_since_reversal=candles_since,
                entry_quality=exit_quality,
                reasoning=reasoning
            )
            
        except Exception as e:
            self.logger.error(f"خطأ في تأكيد الانعكاس الهبوطي: {e}")
            return self._default_signal()
    
    def _detect_bullish_reversal_signals(
        self,
        df: pd.DataFrame,
        timeframe: str
    ) -> Dict:
        """كشف إشارات الانعكاس الصعودي"""
        try:
            signals = {
                'detected': False,
                'confidence': 0,
                'patterns': [],
                'indicators': 0,
                'candles_since_reversal': 999
            }
            
            if len(df) < 10:
                return signals
            
            # 1. الشموع اليابانية
            candle_patterns = self._detect_bullish_candle_patterns(df)
            signals['patterns'].extend(candle_patterns['patterns'])
            
            # 2. المؤشرات الفنية
            indicator_signals = self._check_bullish_indicators(df)
            signals['indicators'] = indicator_signals['count']
            
            # 3. هيكل السعر (Higher Lows)
            structure_signals = self._check_bullish_structure(df)
            
            # 4. الحجم
            volume_confirmation = self._check_volume_increase(df)
            
            # 5. حساب الثقة
            confidence = 0
            
            # الشموع (0-40)
            if candle_patterns['detected']:
                confidence += candle_patterns['confidence']
                signals['candles_since_reversal'] = candle_patterns['candles_since']
            
            # المؤشرات (0-30)
            confidence += indicator_signals['confidence']
            
            # الهيكل (0-20)
            if structure_signals:
                confidence += 20
            
            # الحجم (0-10)
            if volume_confirmation:
                confidence += 10
                signals['patterns'].append('volume_surge')
            
            signals['confidence'] = min(confidence, 100)
            signals['detected'] = confidence >= self.MIN_CONFIDENCE_WEAK
            
            return signals
            
        except Exception as e:
            self.logger.error(f"خطأ في كشف الانعكاس الصعودي: {e}")
            return signals
    
    def _detect_bearish_reversal_signals(
        self,
        df: pd.DataFrame,
        timeframe: str
    ) -> Dict:
        """كشف إشارات الانعكاس الهبوطي"""
        try:
            signals = {
                'detected': False,
                'confidence': 0,
                'patterns': [],
                'indicators': 0,
                'candles_since_reversal': 999
            }
            
            if len(df) < 10:
                return signals
            
            # 1. الشموع
            candle_patterns = self._detect_bearish_candle_patterns(df)
            signals['patterns'].extend(candle_patterns['patterns'])
            
            # 2. المؤشرات
            indicator_signals = self._check_bearish_indicators(df)
            signals['indicators'] = indicator_signals['count']
            
            # 3. الهيكل (Lower Highs)
            structure_signals = self._check_bearish_structure(df)
            
            # 4. الحجم
            volume_confirmation = self._check_volume_increase(df)
            
            # 5. الثقة
            confidence = 0
            
            if candle_patterns['detected']:
                confidence += candle_patterns['confidence']
                signals['candles_since_reversal'] = candle_patterns['candles_since']
            
            confidence += indicator_signals['confidence']
            
            if structure_signals:
                confidence += 20
            
            if volume_confirmation:
                confidence += 10
                signals['patterns'].append('volume_surge')
            
            signals['confidence'] = min(confidence, 100)
            signals['detected'] = confidence >= self.MIN_CONFIDENCE_WEAK
            
            return signals
            
        except Exception as e:
            self.logger.error(f"خطأ في كشف الانعكاس الهبوطي: {e}")
            return signals
    
    def _detect_bullish_candle_patterns(self, df: pd.DataFrame) -> Dict:
        """كشف أنماط الشموع الصعودية"""
        try:
            result = {
                'detected': False,
                'patterns': [],
                'confidence': 0,
                'candles_since': 999
            }
            
            # آخر 10 شموع للبحث عن الأنماط (المرحلة 2 - توسيع النطاق)
            # المتداول المحترف يفحص آخر 10-20 شمعة، ليس فقط 3
            for i in range(1, min(11, len(df))):
                idx = -i
                o = df['open'].iloc[idx]
                h = df['high'].iloc[idx]
                l = df['low'].iloc[idx]
                c = df['close'].iloc[idx]
                
                body = abs(c - o)
                upper_wick = h - max(o, c)
                lower_wick = min(o, c) - l
                total_range = h - l
                
                if total_range == 0:
                    continue
                
                # Hammer (معايير مخففة جداً - المرحلة 2)
                # المرحلة 1: كان 1.5
                # المرحلة 2: 1.2 (نظام تدريجي)
                if body > 0:
                    if lower_wick > body * 1.2 and upper_wick < body * 0.4 and c > o:
                        # Hammer ضعيف
                        result['patterns'].append('hammer')
                        result['confidence'] = max(result['confidence'], 30)
                        result['candles_since'] = min(result['candles_since'], i)
                        result['detected'] = True
                    elif lower_wick > body * 1.5 and upper_wick < body * 0.3 and c > o:
                        # Hammer جيد
                        result['patterns'].append('hammer')
                        result['confidence'] = max(result['confidence'], 35)
                        result['candles_since'] = min(result['candles_since'], i)
                        result['detected'] = True
                    elif lower_wick > body * 2.0 and upper_wick < body * 0.2 and c > o:
                        # Hammer ممتاز
                        result['patterns'].append('hammer_strong')
                        result['confidence'] = max(result['confidence'], 40)
                        result['candles_since'] = min(result['candles_since'], i)
                        result['detected'] = True
                
                # Bullish Engulfing
                if idx > -len(df):
                    prev_o = df['open'].iloc[idx-1]
                    prev_c = df['close'].iloc[idx-1]
                    if prev_c < prev_o and c > o and c > prev_o and o < prev_c:
                        result['patterns'].append('bullish_engulfing')
                        result['confidence'] = max(result['confidence'], 40)
                        result['candles_since'] = min(result['candles_since'], i)
                        result['detected'] = True
                
                # Morning Doji Star
                if idx > -len(df) + 1:
                    prev_body = abs(df['close'].iloc[idx-1] - df['open'].iloc[idx-1])
                    if prev_body < total_range * 0.2 and c > o:
                        result['patterns'].append('doji_reversal')
                        result['confidence'] = max(result['confidence'], 30)
                        result['candles_since'] = min(result['candles_since'], i)
                        result['detected'] = True
            
            return result
            
        except Exception as e:
            self.logger.error(f"خطأ في كشف الشموع الصعودية: {e}")
            return result
    
    def _detect_bearish_candle_patterns(self, df: pd.DataFrame) -> Dict:
        """كشف أنماط الشموع الهبوطية"""
        try:
            result = {
                'detected': False,
                'patterns': [],
                'confidence': 0,
                'candles_since': 999
            }
            
            # آخر 10 شموع (المرحلة 2 - توسيع النطاق)
            for i in range(1, min(11, len(df))):
                idx = -i
                o = df['open'].iloc[idx]
                h = df['high'].iloc[idx]
                l = df['low'].iloc[idx]
                c = df['close'].iloc[idx]
                
                body = abs(c - o)
                upper_wick = h - max(o, c)
                lower_wick = min(o, c) - l
                total_range = h - l
                
                if total_range == 0:
                    continue
                
                # Shooting Star (نظام تدريجي متوازن)
                if body > 0:
                    # شرط أساسي: الذيل العلوي أطول من الجسم
                    if upper_wick > body * 0.8 and lower_wick < body * 0.5 and c < o:
                        # مستوى 1: ضعيف (ذيل > 0.8x الجسم)
                        if upper_wick > body * 0.8 and upper_wick <= body * 1.3:
                            result['patterns'].append('shooting_star_weak')
                            result['confidence'] = max(result['confidence'], 25)
                            result['candles_since'] = min(result['candles_since'], i)
                            result['detected'] = True
                        # مستوى 2: متوسط (ذيل > 1.3x الجسم)
                        elif upper_wick > body * 1.3 and upper_wick <= body * 1.8:
                            result['patterns'].append('shooting_star')
                            result['confidence'] = max(result['confidence'], 35)
                            result['candles_since'] = min(result['candles_since'], i)
                            result['detected'] = True
                        # مستوى 3: قوي (ذيل > 1.8x الجسم)
                        elif upper_wick > body * 1.8:
                            result['patterns'].append('shooting_star_strong')
                            result['confidence'] = max(result['confidence'], 45)
                            result['candles_since'] = min(result['candles_since'], i)
                            result['detected'] = True
                
                # Bearish Engulfing
                if idx > -len(df):
                    prev_o = df['open'].iloc[idx-1]
                    prev_c = df['close'].iloc[idx-1]
                    if prev_c > prev_o and c < o and c < prev_o and o > prev_c:
                        result['patterns'].append('bearish_engulfing')
                        result['confidence'] = max(result['confidence'], 40)
                        result['candles_since'] = min(result['candles_since'], i)
                        result['detected'] = True
                
                # Evening Doji Star
                if idx > -len(df) + 1:
                    prev_body = abs(df['close'].iloc[idx-1] - df['open'].iloc[idx-1])
                    if prev_body < total_range * 0.2 and c < o:
                        result['patterns'].append('doji_reversal')
                        result['confidence'] = max(result['confidence'], 30)
                        result['candles_since'] = min(result['candles_since'], i)
                        result['detected'] = True
            
            return result
            
        except Exception as e:
            self.logger.error(f"خطأ في كشف الشموع الهبوطية: {e}")
            return result
    
    def _check_bullish_indicators(self, df: pd.DataFrame) -> Dict:
        """فحص المؤشرات الصعودية"""
        try:
            count = 0
            confidence = 0
            
            # RSI oversold recovery (محدّث - زيادة النقاط)
            if 'rsi' in df.columns:
                rsi = df['rsi'].iloc[-1]
                prev_rsi = df['rsi'].iloc[-2] if len(df) > 1 else rsi
                if prev_rsi < 35 and rsi > prev_rsi:
                    count += 1
                    confidence += 15  # كان 10 - متداول محترف يعطي وزن أكبر
            
            # MACD bullish cross (محدّث)
            if 'macd' in df.columns and 'macd_signal' in df.columns:
                macd = df['macd'].iloc[-1]
                signal = df['macd_signal'].iloc[-1]
                prev_macd = df['macd'].iloc[-2] if len(df) > 1 else macd
                prev_signal = df['macd_signal'].iloc[-2] if len(df) > 1 else signal
                
                if prev_macd < prev_signal and macd > signal:
                    count += 1
                    confidence += 20  # كان 15 - MACD cross مهم جداً
            
            # Price above support (محدّث)
            if 'support' in df.columns:
                price = df['close'].iloc[-1]
                support = df['support'].iloc[-1]
                if price > support * 1.005:
                    count += 1
                    confidence += 10  # كان 5 - الدعم مهم
            
            return {'count': count, 'confidence': confidence}
            
        except Exception:
            return {'count': 0, 'confidence': 0}
    
    def _check_bearish_indicators(self, df: pd.DataFrame) -> Dict:
        """فحص المؤشرات الهبوطية"""
        try:
            count = 0
            confidence = 0
            
            # RSI overbought decline (محدّث)
            if 'rsi' in df.columns:
                rsi = df['rsi'].iloc[-1]
                prev_rsi = df['rsi'].iloc[-2] if len(df) > 1 else rsi
                if prev_rsi > 65 and rsi < prev_rsi:
                    count += 1
                    confidence += 15  # كان 10
            
            # MACD bearish cross (محدّث)
            if 'macd' in df.columns and 'macd_signal' in df.columns:
                macd = df['macd'].iloc[-1]
                signal = df['macd_signal'].iloc[-1]
                prev_macd = df['macd'].iloc[-2] if len(df) > 1 else macd
                prev_signal = df['macd_signal'].iloc[-2] if len(df) > 1 else signal
                
                if prev_macd > prev_signal and macd < signal:
                    count += 1
                    confidence += 20  # كان 15
            
            # Price at resistance (محدّث)
            if 'resistance' in df.columns:
                price = df['close'].iloc[-1]
                resistance = df['resistance'].iloc[-1]
                if price > resistance * 0.995:
                    count += 1
                    confidence += 10  # كان 5
            
            return {'count': count, 'confidence': confidence}
            
        except Exception:
            return {'count': 0, 'confidence': 0}
    
    def _check_bullish_structure(self, df: pd.DataFrame) -> bool:
        """فحص هيكل صعودي (Higher Lows)"""
        try:
            lows = df['low'].tail(10).values
            if len(lows) < 5:
                return False
            
            recent_low = min(lows[-3:])
            previous_low = min(lows[-6:-3])
            
            return recent_low > previous_low
            
        except Exception:
            return False
    
    def _check_bearish_structure(self, df: pd.DataFrame) -> bool:
        """فحص هيكل هبوطي (Lower Highs)"""
        try:
            highs = df['high'].tail(10).values
            if len(highs) < 5:
                return False
            
            recent_high = max(highs[-3:])
            previous_high = max(highs[-6:-3])
            
            return recent_high < previous_high
            
        except Exception:
            return False
    
    def _check_volume_increase(self, df: pd.DataFrame) -> bool:
        """فحص زيادة الحجم"""
        try:
            if 'volume' not in df.columns:
                return False
            
            current_vol = df['volume'].iloc[-1]
            avg_vol = df['volume'].tail(20).mean()
            
            return current_vol > avg_vol * 1.3
            
        except Exception:
            return False
    
    def _calculate_entry_quality(
        self,
        candles_since: int,
        confidence: float,
        timeframes_count: int,
        indicators_count: int
    ) -> float:
        """حساب جودة الدخول"""
        try:
            quality = 0
            
            # التوقيت (0-40)
            if candles_since == 1:
                quality += 40  # مثالي
            elif candles_since == 2:
                quality += 30  # جيد
            elif candles_since == 3:
                quality += 20  # مقبول
            else:
                quality += 10  # متأخر
            
            # الثقة (0-30)
            quality += (confidence / 100) * 30
            
            # الأطر (0-20)
            quality += timeframes_count * 10
            
            # المؤشرات (0-10)
            quality += min(indicators_count * 3, 10)
            
            return min(quality, 100)
            
        except Exception:
            return 0
    
    def _calculate_exit_quality(
        self,
        candles_since: int,
        confidence: float,
        timeframes_count: int,
        indicators_count: int,
        current_price: float,
        entry_price: float
    ) -> float:
        """حساب جودة الخروج"""
        try:
            quality = self._calculate_entry_quality(
                candles_since, confidence, timeframes_count, indicators_count
            )
            
            # تعديل بناءً على الربح/الخسارة
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            
            if pnl_pct > 0:
                # في ربح - خروج جيد
                quality += 10
            else:
                # في خسارة - خروج ضروري
                quality += 20
            
            return min(quality, 100)
            
        except Exception:
            return 0
    
    def _build_reasoning(
        self,
        direction: str,
        timeframes: List[str],
        patterns: List[str],
        indicators: int,
        candles: int,
        quality: float
    ) -> str:
        """بناء التفسير"""
        parts = []
        
        direction_ar = "صعودي" if direction == 'bullish' else "هبوطي"
        parts.append(f"انعكاس {direction_ar}")
        
        if len(timeframes) > 1:
            parts.append(f"مؤكد على {len(timeframes)} أطر")
        elif len(timeframes) == 1:
            parts.append(f"على {timeframes[0]} فقط")
        else:
            parts.append("غير مؤكد")
        
        if patterns:
            parts.append(f"{len(patterns)} أنماط")
        
        if indicators > 0:
            parts.append(f"{indicators} مؤشرات")
        
        if candles <= 2:
            parts.append(f"توقيت جيد ({candles} شمعة)")
        else:
            parts.append(f"متأخر ({candles} شموع)")
        
        parts.append(f"جودة {quality:.0f}%")
        
        return " | ".join(parts)
    
    def _default_signal(self) -> ReversalSignal:
        """إشارة افتراضية"""
        return ReversalSignal(
            type=ReversalType.NONE,
            strength=ReversalStrength.NONE,
            confidence=0,
            timeframes_confirmed=[],
            patterns_detected=[],
            indicators_aligned=0,
            candles_since_reversal=999,
            entry_quality=0,
            reasoning="لا يوجد انعكاس"
        )


# Singleton
_mtf_reversal_instance = None

def get_mtf_reversal_confirmation() -> MTFReversalConfirmation:
    """الحصول على نسخة واحدة من النظام"""
    global _mtf_reversal_instance
    if _mtf_reversal_instance is None:
        _mtf_reversal_instance = MTFReversalConfirmation()
    return _mtf_reversal_instance
