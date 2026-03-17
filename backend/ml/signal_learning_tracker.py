"""
Signal Learning Tracker - نظام تتبع وتعلم الإشارات
يتتبع جودة الإشارات ويتعلم من النتائج لكل تركيبة (Symbol + Strategy + Timeframe)
"""

import logging
from collections import deque, defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np
import json

logger = logging.getLogger(__name__)


class SignalLearningTracker:
    """تتبع وتقييم جودة الإشارات مع تعلم منفصل لكل تركيبة"""
    
    def __init__(self, db_manager=None):
        self.db = db_manager
        self.signal_history = deque(maxlen=1000)  # آخر 1000 إشارة
        self.combination_stats = {}  # إحصائيات لكل تركيبة
        
        logger.info("✅ تم تهيئة Signal Learning Tracker")
    
    def record_signal(self, signal_data: Dict[str, Any], execution_time: datetime) -> str:
        """تسجيل الإشارة عند التنفيذ"""
        
        import uuid
        signal_id = str(uuid.uuid4())
        
        # التركيبة المحددة
        combination = f"{signal_data['symbol']}_{signal_data['strategy']}_{signal_data['timeframe']}"
        
        signal_record = {
            'signal_id': signal_id,
            'timestamp': execution_time,
            'combination': combination,
            'symbol': signal_data['symbol'],
            'strategy': signal_data['strategy'],
            'timeframe': signal_data['timeframe'],
            
            # معلومات الدخول
            'entry_price': signal_data.get('entry_price', 0),
            'entry_rsi': signal_data.get('indicators', {}).get('rsi', 50),
            'entry_macd': signal_data.get('indicators', {}).get('macd', 0),
            'entry_volume': signal_data.get('volume', 0),
            'market_regime': signal_data.get('market_regime', 'unknown'),
            'volatility': signal_data.get('volatility', 0),
            
            # السياق
            'support_distance': signal_data.get('support_distance', 0),
            'resistance_distance': signal_data.get('resistance_distance', 0),
            
            # سيتم ملؤها عند الإغلاق
            'actual_profit_pct': None,
            'exit_reason': None,
            'signal_quality_score': None,
            'was_correct': None
        }
        
        self.signal_history.append(signal_record)
        
        # حفظ في قاعدة البيانات
        if self.db:
            self._save_to_db(signal_record)
        
        return signal_id
    
    def evaluate_signal(self, signal_id: str, trade_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """تقييم الإشارة بعد إغلاق الصفقة"""
        
        # البحث عن الإشارة
        signal = None
        for s in self.signal_history:
            if s['signal_id'] == signal_id:
                signal = s
                break
        
        if not signal:
            logger.warning(f"⚠️ لم يتم العثور على الإشارة: {signal_id}")
            return None
        
        # تحديث النتيجة الفعلية
        signal['actual_profit_pct'] = trade_result.get('profit_pct', 0)
        signal['exit_reason'] = trade_result.get('exit_reason', 'unknown')
        signal['holding_time_minutes'] = trade_result.get('holding_time_minutes', 0)
        
        # حساب جودة الإشارة
        quality_score = self._calculate_quality_score(signal, trade_result)
        signal['signal_quality_score'] = quality_score
        signal['was_correct'] = quality_score > 0.6
        
        # تحديث في قاعدة البيانات
        if self.db:
            self._update_db(signal)
        
        # التعلم من النتيجة
        self._learn_from_result(signal)
        
        logger.info(f"📊 تقييم إشارة {signal['combination']}: جودة = {quality_score:.2%}")
        
        return signal
    
    def _calculate_quality_score(self, signal: Dict, result: Dict) -> float:
        """حساب جودة الإشارة من 0 إلى 1"""
        
        score = 0.0
        profit_pct = result.get('profit_pct', 0)
        
        # 1. هل حققت ربح؟ (40%)
        if profit_pct > 0:
            score += 0.4
            # مكافأة للأرباح الكبيرة
            if profit_pct >= 0.03:  # 3%+
                score += 0.1
        
        # 2. نسبة الربح/الخسارة (30%)
        if profit_pct > 0:
            score += min(0.3, profit_pct * 10)  # max 0.3
        else:
            score += max(-0.3, profit_pct * 10)  # min -0.3
        
        # 3. الوقت (15%)
        holding_time = result.get('holding_time_minutes', 0)
        if holding_time > 0:
            if holding_time < 60:  # أقل من ساعة
                score += 0.15
            elif holding_time < 240:  # أقل من 4 ساعات
                score += 0.10
            elif holding_time < 480:  # أقل من 8 ساعات
                score += 0.05
        
        # 4. سبب الخروج (15%)
        exit_reason = result.get('exit_reason', '')
        if exit_reason == 'take_profit':
            score += 0.15
        elif exit_reason == 'trailing_stop' and profit_pct > 0:
            score += 0.10
        elif exit_reason == 'stop_loss':
            score -= 0.15
        
        return max(0.0, min(1.0, score))
    
    def _learn_from_result(self, signal: Dict):
        """التعلم الفوري من نتيجة الإشارة"""
        
        combination = signal['combination']
        
        # تهيئة إذا لم تكن موجودة
        if combination not in self.combination_stats:
            self.combination_stats[combination] = {
                'total': 0,
                'wins': 0,
                'losses': 0,
                'total_profit': 0,
                'optimal_conditions': {
                    'rsi': [],
                    'volume': [],
                    'volatility': []
                },
                'avoid_conditions': []
            }
        
        stats = self.combination_stats[combination]
        stats['total'] += 1
        stats['total_profit'] += signal['actual_profit_pct'] or 0
        
        quality = signal['signal_quality_score']
        
        if quality > 0.7:  # إشارة ناجحة
            stats['wins'] += 1
            # تسجيل الظروف المثلى
            stats['optimal_conditions']['rsi'].append(signal['entry_rsi'])
            stats['optimal_conditions']['volume'].append(signal['entry_volume'])
            stats['optimal_conditions']['volatility'].append(signal['volatility'])
            
        elif quality < 0.4:  # إشارة فاشلة
            stats['losses'] += 1
            # تسجيل ظروف يجب تجنبها
            avoid_condition = {
                'rsi': signal['entry_rsi'],
                'volatility': signal['volatility'],
                'market_regime': signal['market_regime'],
                'timestamp': signal['timestamp']
            }
            stats['avoid_conditions'].append(avoid_condition)
            
            # الاحتفاظ بآخر 20 فقط
            if len(stats['avoid_conditions']) > 20:
                stats['avoid_conditions'].pop(0)
    
    def get_learned_patterns(self, combination: str, days: int = 90) -> Optional[Dict]:
        """الحصول على الأنماط المتعلمة لتركيبة معينة"""
        
        # فلترة حسب الوقت (آخر X يوم)
        cutoff = datetime.now() - timedelta(days=days)
        recent_signals = [
            s for s in self.signal_history
            if s['combination'] == combination
            and s['timestamp'] > cutoff
            and s['signal_quality_score'] is not None
        ]
        
        if len(recent_signals) < 30:
            return None  # عينة صغيرة جداً
        
        # الإشارات الناجحة
        good_signals = [s for s in recent_signals if s['signal_quality_score'] > 0.7]
        
        if len(good_signals) < 10:
            return None
        
        # حساب النطاقات المثلى
        return {
            'combination': combination,
            'sample_size': len(recent_signals),
            'success_count': len(good_signals),
            'success_rate': len(good_signals) / len(recent_signals),
            'optimal_rsi_range': self._get_percentile_range([s['entry_rsi'] for s in good_signals]),
            'optimal_volume_range': self._get_percentile_range([s['entry_volume'] for s in good_signals]),
            'optimal_volatility_range': self._get_percentile_range([s['volatility'] for s in good_signals]),
            'last_updated': datetime.now()
        }
    
    def _get_percentile_range(self, values: List[float]) -> Dict:
        """حساب النطاق بناءً على Percentiles"""
        
        if not values:
            return {}
        
        values = [v for v in values if v is not None and v > 0]
        if not values:
            return {}
        
        return {
            'min': float(np.percentile(values, 10)),
            'optimal_low': float(np.percentile(values, 25)),
            'median': float(np.median(values)),
            'optimal_high': float(np.percentile(values, 75)),
            'max': float(np.percentile(values, 90)),
            'mean': float(np.mean(values))
        }
    
    def get_combination_statistics(self) -> Dict:
        """إحصائيات شاملة لجميع التركيبات"""
        
        all_stats = {}
        
        for combo, stats in self.combination_stats.items():
            if stats['total'] > 0:
                all_stats[combo] = {
                    'total': stats['total'],
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'win_rate': stats['wins'] / stats['total'] if stats['total'] > 0 else 0,
                    'avg_profit': stats['total_profit'] / stats['total'] if stats['total'] > 0 else 0,
                    'has_learned_patterns': len(stats.get('optimal_conditions', {}).get('rsi', [])) >= 10
                }
        
        return all_stats
    
    def _save_to_db(self, signal: Dict):
        """حفظ الإشارة في قاعدة البيانات"""
        
        if not self.db:
            return
        
        try:
            query = """
                INSERT INTO signal_learning (
                    signal_id, timestamp, combination, symbol, strategy, timeframe,
                    entry_price, entry_rsi, entry_macd, entry_volume,
                    market_regime, volatility, support_distance, resistance_distance
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            self.db.execute_query(query, (
                signal['signal_id'],
                signal['timestamp'].isoformat(),
                signal['combination'],
                signal['symbol'],
                signal['strategy'],
                signal['timeframe'],
                signal['entry_price'],
                signal['entry_rsi'],
                signal['entry_macd'],
                signal['entry_volume'],
                signal['market_regime'],
                signal['volatility'],
                signal['support_distance'],
                signal['resistance_distance']
            ))
            
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الإشارة: {e}")
    
    def _update_db(self, signal: Dict):
        """تحديث الإشارة في قاعدة البيانات"""
        
        if not self.db:
            return
        
        try:
            query = """
                UPDATE signal_learning
                SET actual_profit_pct = %s,
                    exit_reason = %s,
                    signal_quality_score = %s,
                    was_correct = %s,
                    holding_time_minutes = %s
                WHERE signal_id = %s
            """
            
            self.db.execute_query(query, (
                signal.get('actual_profit_pct'),
                signal.get('exit_reason'),
                signal.get('signal_quality_score'),
                1 if signal.get('was_correct') else 0,
                signal.get('holding_time_minutes'),
                signal['signal_id']
            ))
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث الإشارة: {e}")
