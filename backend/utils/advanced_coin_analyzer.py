#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محلل العملات المتقدم - بدائل مجانية موثوقة
- Volatility Filter (ATR)
- Correlation Check
- Technical Analysis (بدل Grok)
- Slippage Calculation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AdvancedCoinAnalyzer:
    """محلل العملات المتقدم مع ميزات مجانية موثوقة"""
    
    def __init__(self):
        """تهيئة المحلل"""
        self.logger = logger
        
        # معايير Volatility
        self.volatility_criteria = {
            'min_atr_pct': 0.5,      # حد أدنى: 0.5% ATR
            'max_atr_pct': 5.0,      # حد أقصى: 5% ATR
            'ideal_atr_pct': 1.5,    # مثالي: 1.5% ATR
        }
        
        # معايير Correlation
        self.correlation_threshold = 0.7  # تجنب العملات المرتبطة بـ > 0.7
        
        # معايير Slippage
        self.slippage_pct = 0.05  # 0.05% slippage
        
    # ==========================================
    # 1. Volatility Filter (ATR)
    # ==========================================
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        حساب Average True Range (ATR)
        
        Args:
            df: DataFrame مع أعمدة high, low, close
            period: فترة ATR (افتراضي: 14)
            
        Returns:
            Series مع قيم ATR
        """
        try:
            # حساب True Range
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift())
            low_close = abs(df['low'] - df['close'].shift())
            
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            
            # حساب ATR
            atr = true_range.rolling(period).mean()
            
            return atr
            
        except Exception as e:
            self.logger.error(f"خطأ في حساب ATR: {e}")
            return pd.Series([0] * len(df))
    
    def check_volatility(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        فحص تقلبات العملة
        
        Args:
            df: DataFrame مع البيانات التاريخية
            symbol: رمز العملة
            
        Returns:
            Dict مع نتائج الفحص
        """
        try:
            if df is None or len(df) < 20:
                return {
                    'passed': False,
                    'reason': 'بيانات غير كافية',
                    'atr_pct': 0
                }
            
            # حساب ATR
            atr = self.calculate_atr(df, period=14)
            current_atr = atr.iloc[-1]
            current_price = df['close'].iloc[-1]
            
            # حساب ATR كنسبة مئوية
            atr_pct = (current_atr / current_price) * 100
            
            # فحص المعايير
            passed = (self.volatility_criteria['min_atr_pct'] <= atr_pct <= 
                     self.volatility_criteria['max_atr_pct'])
            
            reason = None
            if atr_pct < self.volatility_criteria['min_atr_pct']:
                reason = f"تقلبات منخفضة جداً ({atr_pct:.2f}%)"
            elif atr_pct > self.volatility_criteria['max_atr_pct']:
                reason = f"تقلبات عالية جداً ({atr_pct:.2f}%)"
            
            return {
                'passed': passed,
                'atr_pct': atr_pct,
                'atr_value': current_atr,
                'reason': reason,
                'quality': 'مثالي' if abs(atr_pct - self.volatility_criteria['ideal_atr_pct']) < 0.5 else 'مقبول' if passed else 'مرفوض'
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في فحص التقلبات لـ {symbol}: {e}")
            return {'passed': False, 'reason': str(e), 'atr_pct': 0}
    
    # ==========================================
    # 2. Correlation Check
    # ==========================================
    
    def calculate_correlation(self, df1: pd.DataFrame, df2: pd.DataFrame) -> float:
        """
        حساب الارتباط بين عملتين
        
        Args:
            df1: DataFrame الأولى
            df2: DataFrame الثانية
            
        Returns:
            معامل الارتباط (0-1)
        """
        try:
            if df1 is None or df2 is None or len(df1) == 0 or len(df2) == 0:
                return 0.0
            
            # استخدام آخر 50 شمعة
            returns1 = df1['close'].tail(50).pct_change().dropna()
            returns2 = df2['close'].tail(50).pct_change().dropna()
            
            if len(returns1) == 0 or len(returns2) == 0:
                return 0.0
            
            # محاذاة الفهارس
            common_index = returns1.index.intersection(returns2.index)
            if len(common_index) == 0:
                return 0.0
            
            correlation = returns1[common_index].corr(returns2[common_index])
            
            return float(correlation) if not pd.isna(correlation) else 0.0
            
        except Exception as e:
            self.logger.debug(f"خطأ في حساب الارتباط: {e}")
            return 0.0
    
    def check_correlation_with_group(self, symbol: str, group_symbols: List[str], 
                                     data_provider: Any) -> Dict[str, Any]:
        """
        فحص الارتباط مع مجموعة من العملات
        
        Args:
            symbol: رمز العملة المراد فحصها
            group_symbols: قائمة العملات الأخرى
            data_provider: مزود البيانات
            
        Returns:
            Dict مع نتائج الفحص
        """
        try:
            # جلب بيانات العملة الحالية
            ccxt_symbol = symbol.replace('USDT', '/USDT')
            df_current = data_provider.get_historical_data(ccxt_symbol, '1h', limit=100)
            
            if df_current is None or len(df_current) < 50:
                return {
                    'passed': True,
                    'reason': 'بيانات غير كافية للفحص',
                    'correlations': {}
                }
            
            correlations = {}
            high_correlation_count = 0
            
            for other_symbol in group_symbols:
                if other_symbol == symbol:
                    continue
                
                try:
                    ccxt_other = other_symbol.replace('USDT', '/USDT')
                    df_other = data_provider.get_historical_data(ccxt_other, '1h', limit=100)
                    
                    if df_other is not None and len(df_other) >= 50:
                        corr = self.calculate_correlation(df_current, df_other)
                        correlations[other_symbol] = corr
                        
                        if corr > self.correlation_threshold:
                            high_correlation_count += 1
                
                except Exception as e:
                    self.logger.debug(f"خطأ في فحص الارتباط مع {other_symbol}: {e}")
                    continue
            
            # تقرير النتائج
            passed = high_correlation_count == 0
            
            return {
                'passed': passed,
                'correlations': correlations,
                'high_correlation_count': high_correlation_count,
                'reason': f'ارتباط عالي مع {high_correlation_count} عملة' if not passed else 'لا توجد ارتباطات عالية'
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في فحص الارتباط لـ {symbol}: {e}")
            return {'passed': True, 'reason': str(e), 'correlations': {}}
    
    # ==========================================
    # 3. Technical Analysis (بدل Grok)
    # ==========================================
    
    def analyze_technical_indicators(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        تحليل المؤشرات التقنية (بدل Grok)
        
        Args:
            df: DataFrame مع البيانات
            symbol: رمز العملة
            
        Returns:
            Dict مع التحليل التقني
        """
        try:
            if df is None or len(df) < 50:
                return {
                    'passed': False,
                    'reason': 'بيانات غير كافية',
                    'score': 0
                }
            
            last_row = df.iloc[-1]
            score = 0
            signals = []
            
            # 1. RSI (Relative Strength Index)
            rsi = self._calculate_rsi(df, period=14)
            current_rsi = rsi.iloc[-1]
            
            if 30 < current_rsi < 70:
                score += 20
                signals.append(f"RSI محايد ({current_rsi:.1f})")
            elif current_rsi <= 30:
                score += 30
                signals.append(f"RSI منخفض - شراء ({current_rsi:.1f})")
            elif current_rsi >= 70:
                score += 10
                signals.append(f"RSI مرتفع - بيع ({current_rsi:.1f})")
            
            # 2. MACD
            macd_data = self._calculate_macd(df)
            if macd_data['histogram'].iloc[-1] > 0:
                score += 20
                signals.append("MACD إيجابي")
            else:
                signals.append("MACD سلبي")
            
            # 3. Moving Averages
            ema_20 = df['close'].ewm(span=20).mean()
            ema_50 = df['close'].ewm(span=50).mean()
            current_price = df['close'].iloc[-1]
            
            if ema_20.iloc[-1] > ema_50.iloc[-1]:
                score += 15
                signals.append("EMA 20 > EMA 50 (اتجاه صاعد)")
            else:
                signals.append("EMA 20 < EMA 50 (اتجاه هابط)")
            
            if current_price > ema_20.iloc[-1]:
                score += 15
                signals.append("السعر > EMA 20")
            
            # 4. Bollinger Bands
            bb_data = self._calculate_bollinger_bands(df, period=20)
            bb_position = (current_price - bb_data['lower'].iloc[-1]) / (bb_data['upper'].iloc[-1] - bb_data['lower'].iloc[-1])
            
            if 0.3 < bb_position < 0.7:
                score += 10
                signals.append("السعر في منتصف Bollinger Bands")
            elif bb_position < 0.3:
                score += 15
                signals.append("السعر قريب من الحد الأدنى")
            
            # 5. Volume
            volume_avg = df['volume'].tail(20).mean()
            current_volume = df['volume'].iloc[-1]
            
            if current_volume > volume_avg * 1.2:
                score += 10
                signals.append("حجم تداول مرتفع")
            
            # تحديد الإجراء
            action = 'شراء' if score >= 70 else 'انتظر' if score >= 50 else 'بيع'
            passed = score >= 50
            
            return {
                'passed': passed,
                'score': score,
                'action': action,
                'signals': signals,
                'indicators': {
                    'rsi': float(current_rsi),
                    'macd_histogram': float(macd_data['histogram'].iloc[-1]),
                    'ema_20': float(ema_20.iloc[-1]),
                    'ema_50': float(ema_50.iloc[-1]),
                    'bb_position': float(bb_position),
                    'volume_ratio': float(current_volume / volume_avg)
                }
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في التحليل التقني لـ {symbol}: {e}")
            return {'passed': False, 'reason': str(e), 'score': 0}
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """حساب RSI"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """حساب MACD"""
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        histogram = macd - signal
        
        return {
            'macd': macd,
            'signal': signal,
            'histogram': histogram
        }
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20) -> Dict[str, pd.Series]:
        """حساب Bollinger Bands"""
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        
        return {
            'upper': upper,
            'middle': sma,
            'lower': lower
        }
    
    # ==========================================
    # 4. Slippage Calculation
    # ==========================================
    
    def calculate_slippage(self, entry_price: float, exit_price: float) -> Dict[str, float]:
        """
        حساب تأثير Slippage
        
        Args:
            entry_price: سعر الدخول
            exit_price: سعر الخروج
            
        Returns:
            Dict مع تأثير Slippage
        """
        try:
            # Slippage على الدخول
            entry_slippage = entry_price * (self.slippage_pct / 100)
            actual_entry = entry_price + entry_slippage
            
            # Slippage على الخروج
            exit_slippage = exit_price * (self.slippage_pct / 100)
            actual_exit = exit_price - exit_slippage
            
            # الربح/الخسارة بدون Slippage
            profit_without_slippage = ((exit_price - entry_price) / entry_price) * 100
            
            # الربح/الخسارة مع Slippage
            profit_with_slippage = ((actual_exit - actual_entry) / actual_entry) * 100
            
            # التأثير
            slippage_impact = profit_without_slippage - profit_with_slippage
            
            return {
                'entry_price': entry_price,
                'actual_entry': actual_entry,
                'exit_price': exit_price,
                'actual_exit': actual_exit,
                'profit_without_slippage': profit_without_slippage,
                'profit_with_slippage': profit_with_slippage,
                'slippage_impact': slippage_impact,
                'slippage_pct': self.slippage_pct
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في حساب Slippage: {e}")
            return {}
    
    # ==========================================
    # 5. Comprehensive Analysis
    # ==========================================
    
    def analyze_coin_comprehensive(self, symbol: str, df: pd.DataFrame, 
                                   group_symbols: List[str] = None,
                                   data_provider: Any = None) -> Dict[str, Any]:
        """
        تحليل شامل للعملة
        
        Args:
            symbol: رمز العملة
            df: DataFrame مع البيانات
            group_symbols: قائمة العملات الأخرى (للفحص الارتباط)
            data_provider: مزود البيانات
            
        Returns:
            Dict مع التحليل الشامل
        """
        try:
            results = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'analyses': {}
            }
            
            # 1. فحص التقلبات
            volatility = self.check_volatility(df, symbol)
            results['analyses']['volatility'] = volatility
            
            # 2. التحليل التقني
            technical = self.analyze_technical_indicators(df, symbol)
            results['analyses']['technical'] = technical
            
            # 3. فحص الارتباط (إذا توفرت البيانات)
            if group_symbols and data_provider:
                correlation = self.check_correlation_with_group(symbol, group_symbols, data_provider)
                results['analyses']['correlation'] = correlation
            
            # 4. القرار النهائي
            volatility_ok = volatility.get('passed', False)
            technical_ok = technical.get('passed', False)
            correlation_ok = results['analyses'].get('correlation', {}).get('passed', True)
            
            results['final_decision'] = {
                'approved': volatility_ok and technical_ok and correlation_ok,
                'score': technical.get('score', 0),
                'reasons': []
            }
            
            if not volatility_ok:
                results['final_decision']['reasons'].append(f"التقلبات: {volatility.get('reason', 'غير مناسبة')}")
            if not technical_ok:
                results['final_decision']['reasons'].append(f"التحليل التقني: {technical.get('reason', 'سلبي')}")
            if not correlation_ok:
                results['final_decision']['reasons'].append(f"الارتباط: {results['analyses'].get('correlation', {}).get('reason', 'عالي')}")
            
            if results['final_decision']['approved']:
                results['final_decision']['reasons'].append("✅ العملة مقبولة للتداول")
            
            return results
            
        except Exception as e:
            self.logger.error(f"خطأ في التحليل الشامل لـ {symbol}: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'final_decision': {'approved': False}
            }


if __name__ == "__main__":
    # اختبار بسيط
    analyzer = AdvancedCoinAnalyzer()
    print("✅ محلل العملات المتقدم جاهز للاستخدام")
