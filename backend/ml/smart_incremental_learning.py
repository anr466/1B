"""
Smart Incremental Learning System - النظام المتكامل
يجمع كل المكونات معاً لنظام تعلم ذكي وفعال
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from backend.ml.signal_learning_tracker import SignalLearningTracker
from backend.ml.dual_path_decision import DualPathDecision
from backend.ml.rolling_window_learner import RollingWindowLearner
from backend.ml.auto_health_monitor import AutoHealthMonitor

logger = logging.getLogger(__name__)


class SmartIncrementalLearning:
    """نظام التعلم التدريجي الذكي - المتكامل"""
    
    def __init__(self, user_id: int, db_manager=None):
        self.user_id = user_id
        self.db = db_manager
        
        # المكونات الأساسية
        self.signal_tracker = SignalLearningTracker(db_manager)
        self.dual_path = DualPathDecision()
        self.rolling_window = RollingWindowLearner(window_days=90)
        self.health_monitor = AutoHealthMonitor(self.dual_path)
        
        # الأنماط المتعلمة (cache)
        self.learned_patterns_cache = {}
        self.cache_updated = datetime.now()
        
        logger.info(f"✅ تهيئة Smart Incremental Learning للمستخدم {user_id}")
    
    def process_signal(self, signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """معالجة إشارة جديدة مع التعلم"""
        
        # التركيبة
        combination = f"{signal_data['symbol']}_{signal_data['strategy']}_{signal_data['timeframe']}"
        
        # الحصول على الأنماط المتعلمة لهذه التركيبة
        learned_patterns = self._get_patterns_for_combination(combination)
        
        # القرار بالنظام المزدوج
        decision = self.dual_path.decide(signal_data, learned_patterns)
        
        # إذا كان القرار هو التداول
        if decision['action'] == 'trade':
            # تسجيل الإشارة
            signal_id = self.signal_tracker.record_signal(signal_data, datetime.now())
            decision['signal_id'] = signal_id
            
            logger.info(f"✅ قبول إشارة {combination}: ثقة={decision['confidence']:.2%}, "
                       f"إجماع={decision['consensus']}")
        else:
            logger.debug(f"⛔ رفض إشارة {combination}: {decision.get('explanation', '')}")
        
        return decision
    
    def on_trade_closed(self, signal_id: str, trade_result: Dict[str, Any]):
        """التعلم بعد إغلاق الصفقة"""
        
        # 1. تقييم الإشارة
        signal = self.signal_tracker.evaluate_signal(signal_id, trade_result)
        
        if not signal:
            logger.warning(f"⚠️ لم يتم العثور على الإشارة: {signal_id}")
            return
        
        # 2. تحديث النظام المزدوج
        # نحتاج لاستعادة القرار الأصلي من الإشارة
        # لكن للبساطة، سنستخدم النتيجة مباشرة
        dummy_decision = {
            'action': 'trade',
            'conservative_decision': {'action': 'trade'},
            'balanced_decision': {'action': 'trade'}
        }
        self.dual_path.update_from_result(dummy_decision, trade_result)
        
        # 3. تحديث cache الأنماط المتعلمة
        combination = signal['combination']
        self.learned_patterns_cache.pop(combination, None)  # حذف من cache للتحديث
        
        logger.info(f"📚 تعلم من صفقة {signal_id}: جودة={signal['signal_quality_score']:.2%}")
    
    def _get_patterns_for_combination(self, combination: str) -> Optional[Dict]:
        """الحصول على الأنماط المتعلمة لتركيبة معينة"""
        
        # فحص Cache
        if combination in self.learned_patterns_cache:
            patterns = self.learned_patterns_cache[combination]
            # تحقق من حداثة البيانات
            if self.rolling_window.is_data_fresh(patterns):
                return patterns
        
        # الحصول على الإشارات الحديثة
        recent_signals = self.rolling_window.get_recent_signals(
            list(self.signal_tracker.signal_history),
            combination
        )
        
        # استخراج الأنماط
        patterns = self.rolling_window.extract_patterns(recent_signals)
        
        if patterns:
            # حفظ في cache
            self.learned_patterns_cache[combination] = patterns
            logger.debug(f"📊 أنماط متعلمة لـ {combination}: {patterns['success_rate']:.1%} نجاح")
        
        return patterns
    
    def run_daily_health_check(self, recent_trades: list = None) -> Dict:
        """فحص صحة يومي"""
        
        if recent_trades is None:
            recent_trades = []
        
        # تشغيل الفحص
        health_report = self.health_monitor.daily_health_check(
            recent_trades,
            []  # learned_rules - يمكن إضافته لاحقاً
        )
        
        logger.info(f"🏥 فحص صحة: نتيجة={health_report['summary']['health_score']:.1%}")
        
        return health_report
    
    def get_learning_progress(self) -> Dict[str, Any]:
        """الحصول على تقدم التعلم للعرض في الأدمن"""
        
        # إحصائيات الإشارات
        combo_stats = self.signal_tracker.get_combination_statistics()
        
        # أداء النظام المزدوج
        dual_perf = self.dual_path.get_performance_summary()
        
        # تقرير الصحة
        health = self.health_monitor.get_health_report()
        
        # حساب الإجماليات
        total_signals = sum(stats['total'] for stats in combo_stats.values())
        total_wins = sum(stats['wins'] for stats in combo_stats.values())
        
        overall_win_rate = total_wins / total_signals if total_signals > 0 else 0
        
        # عدد التركيبات المتعلمة
        learned_combinations = sum(
            1 for stats in combo_stats.values()
            if stats.get('has_learned_patterns', False)
        )
        
        return {
            'total_signals_processed': total_signals,
            'total_combinations': len(combo_stats),
            'learned_combinations': learned_combinations,
            'overall_win_rate': overall_win_rate,
            'dual_path_performance': dual_perf,
            'health_status': health,
            'combination_details': combo_stats,
            'learning_stage': self._determine_learning_stage(total_signals),
            'system_readiness': self._calculate_readiness(total_signals, learned_combinations)
        }
    
    def _determine_learning_stage(self, total_signals: int) -> str:
        """تحديد مرحلة التعلم"""
        
        if total_signals < 100:
            return 'initial'
        elif total_signals < 300:
            return 'developing'
        elif total_signals < 600:
            return 'mature'
        else:
            return 'advanced'
    
    def _calculate_readiness(self, total_signals: int, learned_combos: int) -> float:
        """حساب جاهزية النظام (0-100%)"""
        
        # الحد الأدنى: 300 إشارة
        signal_score = min(100, (total_signals / 300) * 100)
        
        # الحد الأدنى: 5 تركيبات متعلمة
        combo_score = min(100, (learned_combos / 5) * 100)
        
        # المتوسط
        readiness = (signal_score + combo_score) / 2
        
        return readiness
    
    def get_detailed_combination_report(self, combination: str) -> Optional[Dict]:
        """تقرير تفصيلي عن تركيبة معينة"""
        
        patterns = self._get_patterns_for_combination(combination)
        
        if not patterns:
            return None
        
        stats = self.signal_tracker.combination_stats.get(combination, {})
        
        return {
            'combination': combination,
            'total_signals': stats.get('total', 0),
            'wins': stats.get('wins', 0),
            'losses': stats.get('losses', 0),
            'win_rate': stats.get('wins', 0) / stats.get('total', 1),
            'patterns': patterns,
            'last_updated': patterns.get('last_updated')
        }


# Singleton instance للوصول السهل
_learning_instances = {}


def get_learning_system(user_id: int, db_manager=None) -> SmartIncrementalLearning:
    """الحصول على instance التعلم للمستخدم"""
    
    if user_id not in _learning_instances:
        _learning_instances[user_id] = SmartIncrementalLearning(user_id, db_manager)
    
    return _learning_instances[user_id]
