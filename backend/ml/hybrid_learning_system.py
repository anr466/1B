#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام التعلم الهجين المتكيف
يجمع بين Backtesting والتداول الفعلي مع تكيف ذكي
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import numpy as np
from enum import Enum

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """أنواع أنظمة السوق"""
    BULL = 'bull'          # سوق صاعد
    BEAR = 'bear'          # سوق هابط
    SIDEWAYS = 'sideways'  # سوق جانبي
    VOLATILE = 'volatile'  # سوق متقلب
    UNKNOWN = 'unknown'    # غير محدد


class HybridMLSystem:
    """
    نظام تعلم هجين يستخدم Backtesting في البداية
    ثم يتحول تدريجياً للبيانات الحقيقية
    """
    
    def __init__(self):
        self.real_trades_count = 0
        self.backtest_count = 0
        self.data_window_days = 30  # نافذة زمنية متحركة
        
        # تتبع أنظمة السوق
        self.current_market_regime = MarketRegime.UNKNOWN
        self.backtest_market_regime = MarketRegime.UNKNOWN
        
        # تتبع تواريخ البيانات للـ Data Staleness
        self.trade_dates = []  # قائمة تواريخ الصفقات
        
        logger.info("✅ تم تهيئة Hybrid ML System")
    
    def calculate_data_weights(self) -> Dict[str, float]:
        """
        حساب الأوزان الديناميكية حسب عدد الصفقات الحقيقية
        """
        if self.real_trades_count < 50:
            # في البداية: استخدم Backtesting بوزن عالي
            return {
                'backtest_weight': 0.7,
                'real_weight': 0.3,
                'phase': 'initial',
                'description': 'بيانات قليلة - اعتماد على Backtesting'
            }
        
        elif self.real_trades_count < 100:
            # مرحلة متوسطة: تقليل Backtesting
            return {
                'backtest_weight': 0.4,
                'real_weight': 0.6,
                'phase': 'intermediate',
                'description': 'توازن بين Backtesting والبيانات الحقيقية'
            }
        
        elif self.real_trades_count < 200:
            # مرحلة متقدمة: الأولوية للبيانات الحقيقية
            return {
                'backtest_weight': 0.2,
                'real_weight': 0.8,
                'phase': 'advanced',
                'description': 'أولوية عالية للبيانات الحقيقية'
            }
        
        else:
            # مرحلة النضج: استخدام البيانات الحقيقية فقط
            return {
                'backtest_weight': 0.0,
                'real_weight': 1.0,
                'phase': 'mature',
                'description': 'بيانات حقيقية فقط'
            }
    
    def detect_market_regime(self, price_data: Dict[str, Any]) -> MarketRegime:
        """
        كشف نظام السوق الحالي بناءً على بيانات السعر
        
        Args:
            price_data: بيانات السعر (يجب أن تحتوي على trend, volatility, volume_trend)
        
        Returns:
            MarketRegime: نظام السوق المكتشف
        """
        try:
            trend = price_data.get('trend', 0)  # 1=صاعد, -1=هابط, 0=جانبي
            volatility = price_data.get('volatility', 0)  # نسبة التقلب
            volume_trend = price_data.get('volume_trend', 0)  # اتجاه الحجم
            
            # سوق متقلب: تقلب عالي
            if volatility > 0.05:  # أكثر من 5% تقلب يومي
                return MarketRegime.VOLATILE
            
            # سوق صاعد: اتجاه صاعد + حجم متزايد
            if trend > 0.02 and volume_trend > 0:
                return MarketRegime.BULL
            
            # سوق هابط: اتجاه هابط + حجم متزايد
            if trend < -0.02 and volume_trend > 0:
                return MarketRegime.BEAR
            
            # سوق جانبي: لا اتجاه واضح
            if abs(trend) <= 0.02:
                return MarketRegime.SIDEWAYS
            
            return MarketRegime.UNKNOWN
            
        except Exception as e:
            logger.warning(f"خطأ في كشف نظام السوق: {e}")
            return MarketRegime.UNKNOWN
    
    def calculate_data_weight_by_age(self, trade_date: datetime) -> float:
        """
        حساب وزن البيانات بناءً على عمرها
        البيانات الأحدث لها وزن أعلى
        
        Args:
            trade_date: تاريخ الصفقة
        
        Returns:
            float: وزن البيانات (0.2 - 1.0)
        """
        try:
            days_old = (datetime.now() - trade_date).days
            
            if days_old <= 7:
                return 1.0  # بيانات حديثة جداً (أسبوع واحد)
            elif days_old <= 30:
                return 0.8  # بيانات حديثة (شهر واحد)
            elif days_old <= 90:
                return 0.5  # بيانات متوسطة (3 أشهر)
            else:
                return 0.2  # بيانات قديمة (أكثر من 3 أشهر)
                
        except Exception as e:
            logger.warning(f"خطأ في حساب وزن البيانات: {e}")
            return 0.5  # قيمة افتراضية متوسطة
    
    def should_use_backtest_data(self, symbol: str, strategy: str, timeframe: str) -> bool:
        """
        تحديد إذا كان يجب استخدام بيانات Backtesting لهذه التركيبة
        """
        # إذا في مرحلة النضج، لا تستخدم Backtesting
        weights = self.calculate_data_weights()
        if weights['backtest_weight'] == 0.0:
            return False
        
        # إذا نظام السوق مختلف، قلل الاعتماد على Backtesting
        if (self.current_market_regime != MarketRegime.UNKNOWN and 
            self.backtest_market_regime != MarketRegime.UNKNOWN and
            self.current_market_regime != self.backtest_market_regime):
            logger.info(f"⚠️ نظام السوق مختلف: {self.current_market_regime.value} vs {self.backtest_market_regime.value}")
            return False
        
        return True
    
    def adjust_backtest_for_reality(self, backtest_result: Dict) -> Dict:
        """
        تعديل نتائج Backtesting لتكون أقرب للواقع
        """
        # عوامل التصحيح
        REALITY_FACTOR = 0.85  # خصم 15% للواقعية
        FEE_DEDUCTION = 0.001  # 0.1% رسوم
        SLIPPAGE_DEDUCTION = 0.0005  # 0.05% انزلاق
        
        original_profit_pct = backtest_result.get('profit_pct', 0)
        
        # تطبيق التعديلات
        adjusted_profit = original_profit_pct * REALITY_FACTOR
        adjusted_profit -= (FEE_DEDUCTION * 100)  # تحويل لنسبة
        adjusted_profit -= (SLIPPAGE_DEDUCTION * 100)
        
        # تقليل Win Rate بنسبة 10%
        original_win_rate = backtest_result.get('win_rate', 0)
        adjusted_win_rate = original_win_rate * 0.90
        
        return {
            'source': 'adjusted_backtest',
            'original_profit_pct': original_profit_pct,
            'adjusted_profit_pct': adjusted_profit,
            'original_win_rate': original_win_rate,
            'adjusted_win_rate': adjusted_win_rate,
            'weight': self.calculate_data_weights()['backtest_weight'],
            'is_synthetic': True,
            'adjustments_applied': {
                'reality_factor': REALITY_FACTOR,
                'fees': FEE_DEDUCTION,
                'slippage': SLIPPAGE_DEDUCTION
            }
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        الحصول على حالة النظام المحسّنة
        """
        weights = self.calculate_data_weights()
        
        avg_data_age = 0
        if self.trade_dates:
            total_age = sum((datetime.now() - date).days for date in self.trade_dates)
            avg_data_age = total_age / len(self.trade_dates)
        
        return {
            'total_real_trades': self.real_trades_count,
            'total_backtest_data': self.backtest_count,
            'current_phase': weights['phase'],
            'phase_description': weights['description'],
            'backtest_weight': weights['backtest_weight'],
            'real_weight': weights['real_weight'],
            'data_window_days': self.data_window_days,
            'is_mature': weights['phase'] == 'mature',
            'readiness_percentage': min(100, (self.real_trades_count / 200) * 100),
            'current_market_regime': self.current_market_regime.value,
            'backtest_market_regime': self.backtest_market_regime.value,
            'regime_match': self.current_market_regime == self.backtest_market_regime,
            'avg_data_age_days': round(avg_data_age, 1),
            'data_freshness': 'fresh' if avg_data_age <= 30 else 'moderate' if avg_data_age <= 90 else 'stale'
        }


class DynamicConfidenceSystem:
    """
    نظام الثقة الديناميكية - يتكيف مع الأداء الفعلي
    """
    
    def __init__(self, pattern_id: str, initial_confidence: float = 0.70):
        self.pattern_id = pattern_id
        self.initial_confidence = initial_confidence
        self.current_confidence = initial_confidence
        
        # سجل الأداء
        self.real_trades = {
            'total': 0,
            'wins': 0,
            'losses': 0,
            'win_rate_real': 0.0,
            'avg_profit': 0.0,
            'avg_loss': 0.0
        }
        
        # تتبع الصفقات الأخيرة للحماية من الانهيار
        self.recent_trades_results = []  # قائمة آخر النتائج (profit/loss)
        self.consecutive_losses = 0
        
        # حالة النمط
        self.status = 'learning'  # learning, proven, paused, expired
        self.paused_at = None
        self.retry_count = 0
        
        # معايير محسّنة
        self.MIN_SAMPLE_SIZE = 30  # زيادة من 5 إلى 30
        self.CONFIDENCE_THRESHOLD = 50  # للقرارات الحرجة
        self.MAX_CONSECUTIVE_LOSSES = 5  # إيقاف بعد 5 خسائر متتالية
    
    def update_after_trade(self, profit: float, profit_pct: float) -> Dict[str, Any]:
        """
        تحديث الثقة بعد كل صفقة
        """
        self.real_trades['total'] += 1
        
        # تتبع النتائج الأخيرة (آخر 20 صفقة)
        self.recent_trades_results.append(profit)
        if len(self.recent_trades_results) > 20:
            self.recent_trades_results.pop(0)
        
        if profit > 0:
            self.real_trades['wins'] += 1
            # نجاح الصفقة → زيادة الثقة
            self.current_confidence = min(0.95, self.current_confidence + 0.02)
            # إعادة تعيين عداد الخسائر المتتالية
            self.consecutive_losses = 0
        else:
            self.real_trades['losses'] += 1
            # خسارة الصفقة → تقليل الثقة
            self.current_confidence = max(0.30, self.current_confidence - 0.05)
            # زيادة عداد الخسائر المتتالية
            self.consecutive_losses += 1
        
        # حساب Win Rate الحقيقي
        self.real_trades['win_rate_real'] = (
            self.real_trades['wins'] / self.real_trades['total']
        )
        
        # فحص الخسائر المتتالية (Drawdown Protection)
        if self.consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES:
            self.status = 'paused'
            self.paused_at = datetime.now()
            logger.warning(f"⚠️ إيقاف مؤقت للنمط {self.pattern_id}: {self.consecutive_losses} خسائر متتالية")
            return {
                'status': 'paused',
                'action': 'pause_trading',
                'confidence': self.current_confidence,
                'reason': f'{self.consecutive_losses} خسائر متتالية - إيقاف لمدة 7 أيام',
                'pause_until': (datetime.now() + timedelta(days=7)).isoformat()
            }
        
        # تحليل الأداء
        return self._analyze_performance()
    
    def calculate_confidence_interval(self) -> Dict[str, float]:
        """
        حساب فترة الثقة الإحصائية للـ Win Rate
        """
        total = self.real_trades['total']
        if total < self.MIN_SAMPLE_SIZE:
            return {
                'win_rate': self.real_trades['win_rate_real'],
                'lower_bound': 0.0,
                'upper_bound': 1.0,
                'confidence_level': 'low',
                'margin_of_error': 1.0
            }
        
        win_rate = self.real_trades['win_rate_real']
        
        # حساب هامش الخطأ (95% confidence interval)
        # Margin of Error = 1.96 * sqrt(p(1-p)/n)
        margin_of_error = 1.96 * np.sqrt((win_rate * (1 - win_rate)) / total)
        
        confidence_level = 'high' if total >= self.CONFIDENCE_THRESHOLD else 'medium'
        
        return {
            'win_rate': win_rate,
            'lower_bound': max(0.0, win_rate - margin_of_error),
            'upper_bound': min(1.0, win_rate + margin_of_error),
            'confidence_level': confidence_level,
            'margin_of_error': margin_of_error,
            'sample_size': total
        }
    
    def check_pattern_expiry(self) -> bool:
        """
        فحص إذا كان النمط قد انتهت صلاحيته
        يفحص آخر 10 صفقات فقط
        """
        if len(self.recent_trades_results) < 10:
            return False  # لا توجد بيانات كافية
        
        # آخر 10 صفقات
        last_10 = self.recent_trades_results[-10:]
        wins_in_last_10 = sum(1 for profit in last_10 if profit > 0)
        recent_win_rate = wins_in_last_10 / 10
        
        # إذا Win Rate آخر 10 صفقات أقل من 30%، النمط منتهي الصلاحية
        if recent_win_rate < 0.30:
            self.status = 'expired'
            logger.warning(f"⚠️ النمط {self.pattern_id} انتهت صلاحيته: Win Rate آخر 10 صفقات = {recent_win_rate:.1%}")
            return True
        
        return False
    
    def _analyze_performance(self) -> Dict[str, Any]:
        """
        تحليل الأداء واتخاذ قرار
        """
        total = self.real_trades['total']
        
        # فحص إذا النمط منتهي الصلاحية
        if self.check_pattern_expiry():
            return {
                'status': 'expired',
                'action': 'stop_using',
                'confidence': 0.0,
                'reason': 'النمط أصبح قديماً - آخر 10 صفقات سيئة'
            }
        
        # حساب فترة الثقة
        confidence_interval = self.calculate_confidence_interval()
        
        # حالة 1: بداية التعلم (أقل من MIN_SAMPLE_SIZE)
        if total < self.MIN_SAMPLE_SIZE:
            return {
                'status': 'learning',
                'action': 'continue',
                'confidence': self.current_confidence,
                'reason': f'بيانات قليلة - يحتاج {self.MIN_SAMPLE_SIZE - total} صفقة إضافية',
                'confidence_interval': confidence_interval
            }
        
        # حالة 2: أداء ممتاز (Win Rate > 70%)
        win_rate = self.real_trades['win_rate_real']
        
        if win_rate > 0.70:
            self.status = 'proven'
            return {
                'status': 'excellent',
                'action': 'increase_exposure',
                'confidence': min(0.95, self.current_confidence + 0.05),
                'reason': f'أداء ممتاز - Win Rate: {win_rate:.1%}',
                'confidence_interval': confidence_interval,
                'sample_size': total
            }
        
        # حالة 3: أداء جيد (Win Rate 50-70%)
        elif win_rate >= 0.50:
            self.status = 'learning'
            return {
                'status': 'good',
                'action': 'maintain',
                'confidence': self.current_confidence,
                'reason': f'أداء جيد - Win Rate: {win_rate:.1%}',
                'confidence_interval': confidence_interval,
                'sample_size': total
            }
        
        # حالة 4: أداء ضعيف (Win Rate < 50%)
        else:
            if total >= self.MIN_SAMPLE_SIZE:  # عينة كافية لاتخاذ قرار
                self.status = 'paused'
                self.paused_at = datetime.now()
                return {
                    'status': 'poor',
                    'action': 'pause',
                    'confidence': max(0.30, self.current_confidence - 0.10),
                    'reason': f'أداء ضعيف - Win Rate: {win_rate:.1%} - إيقاف مؤقت',
                    'confidence_interval': confidence_interval,
                    'sample_size': total,
                    'pause_until': (datetime.now() + timedelta(days=14)).isoformat()
                }
            else:
                return {
                    'status': 'learning',
                    'action': 'continue',
                    'confidence': self.current_confidence,
                    'reason': f'أداء منخفض - Win Rate: {win_rate:.1%} - يحتاج مزيد من البيانات',
                    'confidence_interval': confidence_interval,
                    'sample_size': total
                }
    
    def calculate_dynamic_threshold(self) -> float:
        """
        حساب العتبة الديناميكية
        """
        base_threshold = 0.60  # العتبة الأساسية
        
        # تعديل العتبة حسب الأداء
        if self.real_trades['total'] >= 10:
            win_rate = self.real_trades['win_rate_real']
            
            # أداء ممتاز → خفض العتبة (أسهل للدخول)
            if win_rate > 0.70:
                return max(0.50, base_threshold - 0.10)
            
            # أداء ضعيف → رفع العتبة (أصعب للدخول)
            elif win_rate < 0.50:
                return min(0.80, base_threshold + 0.20)
        
        return base_threshold
    
    def should_trade(self, pattern_similarity: float) -> Dict[str, Any]:
        """
        تحديد إذا كان يجب الدخول في صفقة (محسّن)
        """
        # إذا النمط منتهي الصلاحية
        if self.status == 'expired':
            return {
                'should_trade': False,
                'reason': 'النمط منتهي الصلاحية - أداء ضعيف في آخر 10 صفقات',
                'confidence': 0.0
            }
        
        # إذا النمط موقوف مؤقتاً
        if self.status == 'paused' and self.paused_at:
            days_paused = (datetime.now() - self.paused_at).days
            pause_duration = 14 if self.consecutive_losses >= self.MAX_CONSECUTIVE_LOSSES else 7
            
            if days_paused < pause_duration:
                return {
                    'should_trade': False,
                    'reason': f'موقوف مؤقتاً - متبقي {pause_duration - days_paused} أيام',
                    'pause_reason': f'{self.consecutive_losses} خسائر متتالية' if self.consecutive_losses > 0 else 'أداء ضعيف'
                }
            else:
                # إعادة تفعيل بعد فترة الإيقاف
                self.status = 'learning'
                self.paused_at = None
                self.consecutive_losses = 0
                self.retry_count += 1
                logger.info(f"✅ إعادة تفعيل النمط {self.pattern_id} بعد {days_paused} يوم")
        
        # حساب الثقة النهائية
        final_confidence = self.current_confidence * pattern_similarity
        
        # حد التنفيذ (ديناميكي)
        execution_threshold = self.calculate_dynamic_threshold()
        
        return {
            'should_trade': final_confidence >= execution_threshold,
            'final_confidence': final_confidence,
            'threshold': execution_threshold,
            'pattern_confidence': self.current_confidence,
            'pattern_similarity': pattern_similarity,
            'pattern_status': self.status
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        ملخص الأداء
        """
        return {
            'pattern_id': self.pattern_id,
            'status': self.status,
            'confidence': self.current_confidence,
            'initial_confidence': self.initial_confidence,
            'confidence_change': self.current_confidence - self.initial_confidence,
            'trades': self.real_trades,
            'threshold': self.calculate_dynamic_threshold(),
            'paused_at': self.paused_at.isoformat() if self.paused_at else None
        }


# Singleton instances
_hybrid_system = None
_confidence_systems = {}


def get_hybrid_system() -> HybridMLSystem:
    """الحصول على مثيل واحد من النظام الهجين"""
    global _hybrid_system
    if _hybrid_system is None:
        _hybrid_system = HybridMLSystem()
    return _hybrid_system


def get_confidence_system(pattern_id: str, initial_confidence: float = 0.70) -> DynamicConfidenceSystem:
    """الحصول على نظام الثقة لنمط معين"""
    global _confidence_systems
    if pattern_id not in _confidence_systems:
        _confidence_systems[pattern_id] = DynamicConfidenceSystem(pattern_id, initial_confidence)
    return _confidence_systems[pattern_id]


def get_all_patterns_status() -> List[Dict[str, Any]]:
    """الحصول على حالة جميع الأنماط"""
    return [
        system.get_performance_summary() 
        for system in _confidence_systems.values()
    ]
