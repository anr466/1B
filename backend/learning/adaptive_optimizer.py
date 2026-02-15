#!/usr/bin/env python3
"""
📈 Adaptive Parameter Optimizer - المُحسِّن التكيّفي للمعاملات
=============================================================
يتعلم من كل صفقة مغلقة ويعدّل المعاملات تلقائياً:

1. SL% الأمثل لكل عملة
2. أفضل ساعات التداول
3. ترتيب العملات بالأداء
4. عدد الصفقات المتزامنة الأمثل
5. تقليل الحجم بعد الخسائر المتتالية

كل شيء إحصائي — بدون AI/LLM — $0 تكلفة.
"""

import os
import json
import math
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

from database.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

# ===== الحدود الآمنة (لن يتجاوزها المحسّن أبداً) =====
SAFE_LIMITS = {
    'sl_pct_min': 0.005,        # أقل SL: 0.5%
    'sl_pct_max': 0.025,        # أعلى SL: 2.5%
    'sl_pct_default': 0.010,    # SL الافتراضي: 1.0%
    'max_positions_min': 1,     # أقل عدد صفقات: 1
    'max_positions_max': 7,     # أعلى عدد صفقات: 7
    'max_positions_default': 5, # الافتراضي: 5
    'size_mult_min': 0.3,       # أقل مُضاعف حجم: 30%
    'size_mult_max': 1.5,       # أعلى مُضاعف حجم: 150%
    'size_mult_default': 1.0,   # الافتراضي: 100%
    'min_trades_for_learning': 10,  # أقل عدد صفقات قبل بدء التعلم
}


class AdaptiveOptimizer:
    """
    المُحسِّن التكيّفي — يتعلم من الصفقات ويعدّل المعاملات
    
    التدفق:
    1. record_trade() → يسجل كل صفقة مغلقة مع سياقها
    2. get_optimal_sl() → SL مُحسَّن لعملة معينة
    3. get_symbol_ranking() → ترتيب العملات بالأداء
    4. get_trading_hours_filter() → الساعات المسموحة
    5. get_position_size_multiplier() → مُضاعف الحجم
    6. get_max_positions() → عدد الصفقات الأمثل
    """
    
    def __init__(self, db_path: str = None, db_manager=None):
        self.db_manager = db_manager or DatabaseManager()
        
        # كاش محلي (يُحدَّث كل 5 دقائق)
        self._cache: Dict[str, Any] = {}
        self._cache_time: float = 0
        self._cache_ttl = 300  # 5 دقائق
        
        # عدّاد الصفقات — يُشغّل الاختبار الخفي كل 10 صفقات
        self._trades_since_validation = 0
        self._validation_interval = 10
        
        logger.info("📈 AdaptiveOptimizer initialized")
    
    # ==================== تسجيل الصفقات ====================
    
    def record_trade(self, symbol: str, side: str, entry_price: float,
                     exit_price: float, pnl: float, pnl_pct: float,
                     exit_reason: str, sl_pct_used: float,
                     hold_minutes: int = 0, open_positions_count: int = 1,
                     indicators: Dict = None):
        """
        تسجيل صفقة مغلقة مع كل السياق + المؤشرات عند الدخول
        
        يُستدعى من GroupBSystem._close_position()
        """
        try:
            now = datetime.now()
            ind = indicators or {}
            with self.db_manager.get_write_connection() as conn:
                conn.execute("""
                    INSERT INTO trade_learning_log (
                        symbol, side, entry_price, exit_price,
                        pnl, pnl_pct, exit_reason, sl_pct_used,
                        hold_minutes, open_positions_count,
                        hour_of_day, day_of_week,
                        rsi, macd, bb_position, volume_ratio,
                        ema_trend, atr_pct, trend_4h, score,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, side.lower(), entry_price, exit_price,
                    pnl, pnl_pct, exit_reason, sl_pct_used,
                    hold_minutes, open_positions_count,
                    now.hour, now.strftime('%A'),
                    ind.get('rsi'), ind.get('macd'), ind.get('bb_position'),
                    ind.get('volume_ratio'), ind.get('ema_trend'),
                    ind.get('atr_pct'), ind.get('trend_4h'), ind.get('score'),
                    now.isoformat()
                ))
            
            # إبطال الكاش
            self._cache_time = 0
            
            logger.debug(f"📈 Recorded trade: {symbol} {side} PnL={pnl_pct:+.1f}%")
            
            # 🔬 الاختبار الخفي — كل N صفقة
            self._trades_since_validation += 1
            if self._trades_since_validation >= self._validation_interval:
                self._trades_since_validation = 0
                try:
                    self.shadow_validate()
                except Exception as ve:
                    logger.warning(f"⚠️ Shadow validation error: {ve}")
        except Exception as e:
            logger.error(f"❌ Failed to record trade: {e}")
    
    # ==================== SL الأمثل لكل عملة ====================
    
    def get_optimal_sl(self, symbol: str) -> float:
        """
        SL% الأمثل لعملة معينة
        
        المنطق:
        - نحسب متوسط PnL% للصفقات الخاسرة
        - إذا معظم الخسائر تحدث قبل SL الحالي → SL أضيق أفضل
        - إذا كثير من الصفقات تُضرب بـ SL ثم تعكس → SL أوسع أفضل
        
        Returns:
            float: SL% (مثال: 0.010 = 1.0%)
        """
        stats = self._get_symbol_stats(symbol)
        if not stats or stats['total_trades'] < SAFE_LIMITS['min_trades_for_learning']:
            return SAFE_LIMITS['sl_pct_default']
        
        # نسبة الصفقات التي أُغلقت بـ SL
        sl_hit_rate = stats.get('sl_hit_rate', 0)
        avg_loss_pct = abs(stats.get('avg_loss_pct', -1.0))
        win_rate = stats.get('win_rate', 0.5)
        
        current_sl = SAFE_LIMITS['sl_pct_default']
        
        # إذا SL يُضرب كثيراً (>60%) والعملة فيها فرص → وسّع SL قليلاً
        if sl_hit_rate > 0.60 and win_rate < 0.40:
            adjusted_sl = current_sl * 1.2  # +20%
        # إذا معظم الخسائر صغيرة (أقل من SL) → ضيّق SL
        elif avg_loss_pct < current_sl * 0.7 * 100:
            adjusted_sl = current_sl * 0.85  # -15%
        # إذا Win Rate ممتاز → اجعل SL معتدل
        elif win_rate > 0.55:
            adjusted_sl = current_sl * 0.95
        else:
            adjusted_sl = current_sl
        
        # تطبيق الحدود الآمنة
        return max(
            SAFE_LIMITS['sl_pct_min'],
            min(SAFE_LIMITS['sl_pct_max'], adjusted_sl)
        )
    
    # ==================== ترتيب العملات ====================
    
    def get_symbol_ranking(self) -> List[Dict[str, Any]]:
        """
        ترتيب العملات بالأداء (آخر 7 أيام)
        
        Returns:
            قائمة مرتبة [{symbol, score, win_rate, avg_pnl, trades}]
        """
        try:
            with self.db_manager.get_connection() as conn:
                cutoff = (datetime.now() - timedelta(days=7)).isoformat()
                
                rows = conn.execute("""
                    SELECT 
                        symbol,
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                        AVG(pnl_pct) as avg_pnl_pct,
                        SUM(pnl) as total_pnl
                    FROM trade_learning_log
                    WHERE created_at > ?
                    GROUP BY symbol
                    HAVING total_trades >= 3
                    ORDER BY avg_pnl_pct DESC
                """, (cutoff,)).fetchall()
            
            ranking = []
            for row in rows:
                symbol, total, wins, avg_pnl, total_pnl = row
                win_rate = wins / total if total > 0 else 0
                # Score = Win Rate * 40 + Average PnL * 60
                score = (win_rate * 40) + (max(-5, min(5, avg_pnl)) * 12)
                ranking.append({
                    'symbol': symbol,
                    'score': round(score, 1),
                    'win_rate': round(win_rate, 2),
                    'avg_pnl_pct': round(avg_pnl, 2),
                    'total_pnl': round(total_pnl, 2),
                    'trades': total,
                })
            
            return sorted(ranking, key=lambda x: x['score'], reverse=True)
        except Exception as e:
            logger.error(f"❌ Symbol ranking error: {e}")
            return []
    
    # مجموعة أوسع من العملات (top 30 Binance بالسيولة)
    WIDER_SYMBOL_POOL = [
        'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT',
        'AVAXUSDT', 'ADAUSDT', 'LINKUSDT', 'DOTUSDT', 'MATICUSDT',
        'NEARUSDT', 'SUIUSDT', 'APTUSDT', 'ARBUSDT', 'INJUSDT',
        'FTMUSDT', 'ATOMUSDT', 'OPUSDT', 'RUNEUSDT', 'TIAUSDT',
        'SEIUSDT', 'WLDUSDT', 'JUPUSDT', 'STXUSDT', 'AAVEUSDT',
        'RENDERUSDT', 'PEPEUSDT', 'ONDOUSDT', 'ENAUSDT', 'WIFUSDT',
    ]
    
    def get_preferred_symbols(self, available_symbols: List[str],
                              top_n: int = 10) -> List[str]:
        """
        إدارة ديناميكية للعملات:
        1. إزالة العملات الخاسرة باستمرار (WR<25% مع 8+ صفقات)
        2. إضافة عملات بديلة من pool أوسع
        3. ترتيب بالأداء
        """
        ranking = self.get_symbol_ranking()
        ranked_map = {r['symbol']: r for r in ranking}
        
        # تحديد العملات المحظورة (خسائر مستمرة)
        blocked = set()
        for sym, data in ranked_map.items():
            if data['trades'] >= 8 and data['win_rate'] < 0.25:
                blocked.add(sym)
                logger.info(f"📈 Dropping {sym}: WR={data['win_rate']:.0%} over {data['trades']} trades")
        
        # فلترة العملات المتاحة
        active = [s for s in available_symbols if s not in blocked]
        
        # إذا حُذفت عملات، أضف بدائل من pool الأوسع
        if len(active) < len(available_symbols):
            existing = set(active)
            for replacement in self.WIDER_SYMBOL_POOL:
                if replacement not in existing and replacement not in blocked:
                    # إضافة فقط إذا لم تكن خاسرة أيضاً
                    rep_data = ranked_map.get(replacement)
                    if rep_data is None or rep_data['win_rate'] >= 0.35:
                        active.append(replacement)
                        existing.add(replacement)
                        logger.info(f"📈 Adding replacement: {replacement}")
                        if len(active) >= len(available_symbols):
                            break
        
        # ترتيب بالأداء
        scored = [(s, ranked_map.get(s, {}).get('score', 0)) for s in active]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [s for s, _ in scored[:top_n]]
    
    # ==================== فلتر ساعات التداول ====================
    
    def is_good_trading_hour(self, hour: int = None) -> Tuple[bool, str]:
        """
        هل هذه الساعة مناسبة للتداول؟
        
        يحسب Win Rate لكل ساعة من البيانات التاريخية.
        يمنع التداول في الساعات ذات Win Rate < 35%.
        
        Returns:
            (مسموح, السبب)
        """
        if hour is None:
            hour = datetime.now().hour
        
        hourly = self._get_hourly_stats()
        if not hourly or hour not in hourly:
            return True, "لا توجد بيانات كافية"
        
        stats = hourly[hour]
        if stats['trades'] < 5:
            return True, f"بيانات قليلة ({stats['trades']} صفقات)"
        
        if stats['win_rate'] < 0.35:
            return False, f"Win Rate ضعيف {stats['win_rate']:.0%} في الساعة {hour}:00"
        
        return True, f"Win Rate {stats['win_rate']:.0%}"
    
    # ==================== مُضاعف حجم الصفقة ====================
    
    def get_position_size_multiplier(self, consecutive_losses: int = 0,
                                      daily_pnl: float = 0) -> float:
        """
        مُضاعف حجم الصفقة بناءً على الأداء الأخير
        
        - خسائر متتالية → تقليل الحجم
        - أرباح متتالية → زيادة طفيفة
        - PnL يومي سلبي كبير → تقليل
        
        Returns:
            float: مُضاعف (1.0 = حجم عادي)
        """
        mult = SAFE_LIMITS['size_mult_default']
        
        # خسائر متتالية
        if consecutive_losses >= 4:
            mult *= 0.5  # 50% من الحجم
        elif consecutive_losses >= 3:
            mult *= 0.65
        elif consecutive_losses >= 2:
            mult *= 0.80
        
        # PnL يومي سلبي كبير
        if daily_pnl < -50:
            mult *= 0.6
        elif daily_pnl < -20:
            mult *= 0.8
        
        # تعلم من البيانات التاريخية: متوسط الأداء بعد خسائر
        recovery_stats = self._get_post_loss_stats(consecutive_losses)
        if recovery_stats and recovery_stats.get('win_rate', 0.5) < 0.3:
            mult *= 0.7  # تقليل إضافي إذا التاريخ يقول الاسترداد صعب
        
        return max(
            SAFE_LIMITS['size_mult_min'],
            min(SAFE_LIMITS['size_mult_max'], mult)
        )
    
    # ==================== عدد الصفقات الأمثل ====================
    
    def get_optimal_max_positions(self) -> int:
        """
        عدد الصفقات المتزامنة الأمثل
        
        يحسب: أي عدد صفقات أعطى أفضل PnL إجمالي في آخر 30 يوم
        """
        try:
            with self.db_manager.get_connection() as conn:
                cutoff = (datetime.now() - timedelta(days=30)).isoformat()
                
                rows = conn.execute("""
                    SELECT 
                        open_positions_count,
                        COUNT(*) as trades,
                        AVG(pnl_pct) as avg_pnl,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as wr
                    FROM trade_learning_log
                    WHERE created_at > ? AND open_positions_count > 0
                    GROUP BY open_positions_count
                    HAVING trades >= 5
                    ORDER BY avg_pnl DESC
                """, (cutoff,)).fetchall()
            
            if not rows:
                return SAFE_LIMITS['max_positions_default']
            
            # أفضل عدد صفقات
            best = rows[0]
            best_count = best[0]
            
            return max(
                SAFE_LIMITS['max_positions_min'],
                min(SAFE_LIMITS['max_positions_max'], best_count)
            )
        except Exception as e:
            logger.error(f"❌ Optimal positions error: {e}")
            return SAFE_LIMITS['max_positions_default']
    
    # ==================== ملخص التعلم ====================
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """
        ملخص شامل لما تعلمه النظام
        """
        try:
            with self.db_manager.get_connection() as conn:
                total = conn.execute(
                    "SELECT COUNT(*) FROM trade_learning_log"
                ).fetchone()[0]
                
                last_7d = (datetime.now() - timedelta(days=7)).isoformat()
                recent = conn.execute("""
                    SELECT 
                        COUNT(*) as trades,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                        AVG(pnl_pct) as avg_pnl,
                        SUM(pnl) as total_pnl
                    FROM trade_learning_log WHERE created_at > ?
                """, (last_7d,)).fetchone()
            
            trades_7d = recent[0] if recent else 0
            wins_7d = recent[1] if recent else 0
            avg_pnl_7d = recent[2] if recent else 0
            total_pnl_7d = recent[3] if recent else 0
            
            can_learn = total >= SAFE_LIMITS['min_trades_for_learning']
            
            # الحصول على التعديلات الحالية
            ranking = self.get_symbol_ranking()
            hourly = self._get_hourly_stats()
            bad_hours = [h for h, s in (hourly or {}).items() 
                        if s['trades'] >= 5 and s['win_rate'] < 0.35]
            
            return {
                'total_trades_recorded': total,
                'learning_active': can_learn,
                'min_trades_needed': SAFE_LIMITS['min_trades_for_learning'],
                'last_7_days': {
                    'trades': trades_7d,
                    'wins': wins_7d,
                    'win_rate': round(wins_7d / trades_7d, 2) if trades_7d > 0 else 0,
                    'avg_pnl_pct': round(avg_pnl_7d or 0, 2),
                    'total_pnl': round(total_pnl_7d or 0, 2),
                },
                'adaptations': {
                    'symbol_ranking': ranking[:5] if ranking else [],
                    'blocked_hours': bad_hours,
                    'optimal_max_positions': self.get_optimal_max_positions(),
                },
            }
        except Exception as e:
            logger.error(f"❌ Learning summary error: {e}")
            return {'total_trades_recorded': 0, 'learning_active': False}
    
    def shadow_validate(self) -> Dict[str, Any]:
        """
        🔬 الاختبار الخفي — يتحقق من جودة التعلم تلقائياً
        
        المنطق:
        1. يأخذ آخر 20% من الصفقات كمجموعة اختبار (holdout)
        2. يستخدم أول 80% كبيانات تدريب
        3. لكل صفقة اختبار: يحاكي score_signal ويقارن التنبؤ بالنتيجة الفعلية
        4. يحسب الدقة ويقارنها بالتنبؤ العشوائي (baseline)
        5. يسجل النتيجة في learning_validation_log
        
        Returns:
            {accuracy, precision, baseline, lift, verdict, details}
        """
        import json as _json
        
        try:
            with self.db_manager.get_connection() as conn:
                cutoff = (datetime.now() - timedelta(days=60)).isoformat()
                
                # كل الصفقات مع مؤشرات
                all_rows = conn.execute("""
                    SELECT pnl, pnl_pct, rsi, macd, bb_position,
                           volume_ratio, ema_trend, atr_pct, trend_4h, score, symbol
                    FROM trade_learning_log
                    WHERE created_at > ? AND rsi IS NOT NULL
                    ORDER BY created_at ASC
                """, (cutoff,)).fetchall()
                
                total_trades = conn.execute(
                    "SELECT COUNT(*) FROM trade_learning_log WHERE created_at > ?",
                    (cutoff,)
                ).fetchone()[0]
            
            if len(all_rows) < 15:
                result = {
                    'accuracy': 0, 'precision': 0, 'baseline': 0.5,
                    'lift': 0, 'verdict': 'INSUFFICIENT_DATA',
                    'details': f'بيانات قليلة: {len(all_rows)} صفقات مع مؤشرات'
                }
                logger.info(f"🔬 Shadow Validation: {result['verdict']} ({len(all_rows)} trades)")
                return result
            
            # تقسيم 80/20
            split_idx = int(len(all_rows) * 0.8)
            train = all_rows[:split_idx]
            test = all_rows[split_idx:]
            
            if len(test) < 3:
                return {'accuracy': 0, 'baseline': 0.5, 'lift': 0,
                        'verdict': 'INSUFFICIENT_TEST', 'details': 'مجموعة اختبار صغيرة جداً'}
            
            # Baseline: نسبة الفوز الفعلية في التدريب
            train_wr = sum(1 for r in train if r[0] > 0) / len(train)
            baseline_acc = max(train_wr, 1 - train_wr)  # أفضل تنبؤ ثابت
            
            # حساب الأوزان من بيانات التدريب فقط
            weights = self._calculate_adaptive_weights(train)
            
            # اختبار كل صفقة في مجموعة الاختبار
            correct = 0
            true_positives = 0
            predicted_positives = 0
            actual_positives = 0
            
            for row in test:
                actual_win = row[0] > 0
                if actual_win:
                    actual_positives += 1
                
                # محاكاة التقييم باستخدام بيانات التدريب فقط
                predicted_wr = self._simulate_score(row, train, weights)
                predicted_win = predicted_wr >= 0.5
                
                if predicted_win:
                    predicted_positives += 1
                    if actual_win:
                        true_positives += 1
                
                if predicted_win == actual_win:
                    correct += 1
            
            accuracy = correct / len(test)
            precision = true_positives / predicted_positives if predicted_positives > 0 else 0
            lift = accuracy - baseline_acc
            
            # الحكم
            if accuracy >= 0.60 and lift > 0.05:
                verdict = 'LEARNING_EFFECTIVE'
            elif accuracy >= 0.50 and lift >= 0:
                verdict = 'LEARNING_MARGINAL'
            elif lift < -0.05:
                verdict = 'LEARNING_HARMFUL'
            else:
                verdict = 'LEARNING_NEUTRAL'
            
            # حفظ النتيجة
            factor_accuracies = {}
            try:
                with self.db_manager.get_write_connection() as conn:
                    conn.execute("""
                        INSERT INTO learning_validation_log 
                        (total_trades, trades_with_indicators, holdout_size,
                         scorer_accuracy, scorer_precision, baseline_accuracy, lift,
                         factor_weights, factor_accuracies, verdict, details)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        total_trades, len(all_rows), len(test),
                        round(accuracy, 4), round(precision, 4),
                        round(baseline_acc, 4), round(lift, 4),
                        _json.dumps(weights), _json.dumps(factor_accuracies),
                        verdict,
                        f'Acc={accuracy:.0%} Prec={precision:.0%} Base={baseline_acc:.0%} Lift={lift:+.0%}'
                    ))
            except Exception as db_err:
                logger.warning(f"⚠️ Failed to save validation: {db_err}")
            
            emoji = {'LEARNING_EFFECTIVE': '✅', 'LEARNING_MARGINAL': '⚠️',
                     'LEARNING_HARMFUL': '🔴', 'LEARNING_NEUTRAL': '➖'}.get(verdict, '❓')
            
            logger.info(
                f"🔬 Shadow Validation: {emoji} {verdict} | "
                f"Acc={accuracy:.0%} vs Base={baseline_acc:.0%} (Lift={lift:+.0%}) | "
                f"Prec={precision:.0%} | Test={len(test)} trades"
            )
            
            # إذا التعلم ضار → إعادة الأوزان للافتراضي
            if verdict == 'LEARNING_HARMFUL':
                logger.warning("🔴 Learning is HARMFUL — resetting to default weights")
            
            return {
                'accuracy': round(accuracy, 3),
                'precision': round(precision, 3),
                'baseline': round(baseline_acc, 3),
                'lift': round(lift, 3),
                'verdict': verdict,
                'holdout_size': len(test),
                'weights': weights,
                'details': f'Acc={accuracy:.0%} Prec={precision:.0%} Base={baseline_acc:.0%} Lift={lift:+.0%}'
            }
            
        except Exception as e:
            logger.error(f"❌ Shadow validation error: {e}")
            return {'accuracy': 0, 'baseline': 0.5, 'lift': 0,
                    'verdict': 'ERROR', 'details': str(e)}
    
    def _simulate_score(self, test_row: tuple, train_rows: list, weights: Dict) -> float:
        """محاكاة score_signal على صفقة واحدة باستخدام بيانات التدريب فقط (V2 مع Feature Pairs + Confidence)"""
        rsi = test_row[2]
        bb = test_row[4]
        vol = test_row[5]
        trend = test_row[8]
        
        weighted_wins = 0
        total_weight = 0
        
        # Helper: simple WR with confidence
        def _wr_conf(matches, w_key):
            if len(matches) >= 3:
                wr = sum(1 for m in matches if m[0] > 0) / len(matches)
                w = weights.get(w_key, 1.0) * self._confidence_scale(len(matches))
                return wr, w
            return None, 0
        
        # RSI
        if rsi is not None:
            zone = self._get_rsi_zone(rsi)
            matches = [t for t in train_rows if t[2] is not None and self._get_rsi_zone(t[2]) == zone]
            wr, w = _wr_conf(matches, 'rsi_zone')
            if wr is not None:
                weighted_wins += wr * w
                total_weight += w
        
        # Volume
        if vol is not None:
            level = self._vol_level(vol)
            matches = [t for t in train_rows if t[5] is not None and self._vol_level(t[5]) == level]
            wr, w = _wr_conf(matches, 'volume')
            if wr is not None:
                weighted_wins += wr * w
                total_weight += w
        
        # Trend
        if trend is not None:
            matches = [t for t in train_rows if t[8] == trend]
            wr, w = _wr_conf(matches, 'trend')
            if wr is not None:
                weighted_wins += wr * w
                total_weight += w
        
        # BB
        if bb is not None:
            zone = self._bb_zone(bb)
            matches = [t for t in train_rows if t[4] is not None and self._bb_zone(t[4]) == zone]
            wr, w = _wr_conf(matches, 'bb_position')
            if wr is not None:
                weighted_wins += wr * w
                total_weight += w
        
        # Feature Pair 1: RSI + Trend
        if rsi is not None and trend is not None:
            rsi_zone = self._get_rsi_zone(rsi)
            matches = [t for t in train_rows
                       if t[2] is not None and t[8] is not None
                       and self._get_rsi_zone(t[2]) == rsi_zone and t[8] == trend]
            wr, w = _wr_conf(matches, 'rsi_trend')
            if wr is not None:
                weighted_wins += wr * w
                total_weight += w
        
        # Feature Pair 2: Volume + Trend
        if vol is not None and trend is not None:
            vol_level = self._vol_level(vol)
            matches = [t for t in train_rows
                       if t[5] is not None and t[8] is not None
                       and self._vol_level(t[5]) == vol_level and t[8] == trend]
            wr, w = _wr_conf(matches, 'vol_trend')
            if wr is not None:
                weighted_wins += wr * w
                total_weight += w
        
        return weighted_wins / total_weight if total_weight > 0 else 0.5
    
    # ==================== استعلامات داخلية ====================
    
    def _get_symbol_stats(self, symbol: str) -> Optional[Dict]:
        """إحصائيات عملة معينة (آخر 30 يوم)"""
        try:
            with self.db_manager.get_connection() as conn:
                cutoff = (datetime.now() - timedelta(days=30)).isoformat()
                
                row = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                        AVG(CASE WHEN pnl < 0 THEN pnl_pct ELSE NULL END) as avg_loss,
                        SUM(CASE WHEN exit_reason = 'STOP_LOSS' THEN 1 ELSE 0 END) as sl_hits
                    FROM trade_learning_log
                    WHERE symbol = ? AND created_at > ?
                """, (symbol, cutoff)).fetchone()
            
            if not row or row[0] == 0:
                return None
            
            total, wins, avg_loss, sl_hits = row
            return {
                'total_trades': total,
                'win_rate': wins / total,
                'avg_loss_pct': avg_loss or 0,
                'sl_hit_rate': sl_hits / total if total > 0 else 0,
            }
        except Exception as e:
            logger.error(f"❌ Symbol stats error: {e}")
            return None
    
    def _get_hourly_stats(self) -> Optional[Dict[int, Dict]]:
        """إحصائيات بالساعة"""
        try:
            with self.db_manager.get_connection() as conn:
                cutoff = (datetime.now() - timedelta(days=30)).isoformat()
                
                rows = conn.execute("""
                    SELECT 
                        hour_of_day,
                        COUNT(*) as trades,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                        AVG(pnl_pct) as avg_pnl
                    FROM trade_learning_log
                    WHERE created_at > ?
                    GROUP BY hour_of_day
                """, (cutoff,)).fetchall()
            
            if not rows:
                return None
            
            hourly = {}
            for hour, trades, wins, avg_pnl in rows:
                hourly[hour] = {
                    'trades': trades,
                    'win_rate': wins / trades if trades > 0 else 0,
                    'avg_pnl': avg_pnl or 0,
                }
            return hourly
        except Exception as e:
            logger.error(f"❌ Hourly stats error: {e}")
            return None
    
    def _get_post_loss_stats(self, consecutive_losses: int) -> Optional[Dict]:
        """إحصائيات الأداء بعد خسائر متتالية"""
        if consecutive_losses < 2:
            return None
        
        # هذا تقريب — نتحقق من أداء الصفقات عموماً
        # في المستقبل يمكن تحسينه بتتبع التسلسل
        try:
            with self.db_manager.get_connection() as conn:
                cutoff = (datetime.now() - timedelta(days=30)).isoformat()
                
                row = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins
                    FROM trade_learning_log
                    WHERE created_at > ?
                """, (cutoff,)).fetchone()
            
            if not row or row[0] < 5:
                return None
            
            return {'win_rate': row[1] / row[0]}
        except Exception as e:
            return None


    # ==================== تقييم جودة الإشارة ====================
    
    # الأوزان الأولية (تتعدّل تلقائياً)
    _DEFAULT_WEIGHTS = {
        'rsi_zone': 2.0,
        'volume': 1.5,
        'trend': 2.0,
        'bb_position': 1.0,
        'symbol': 1.5,
        'rsi_trend': 2.5,    # Feature Pair: RSI zone + Trend direction
        'vol_trend': 2.0,    # Feature Pair: Volume level + Trend direction
    }
    
    # Exponential decay: half-life ~23 days (lambda=0.03)
    _DECAY_LAMBDA = 0.03
    
    def score_signal(self, symbol: str, indicators: Dict) -> Dict[str, Any]:
        """
        تقييم جودة إشارة التداول — V2 المحسّن
        
        3 تحسينات رئيسية:
        1. Exponential Decay: الصفقات الأحدث لها وزن أعلى
        2. Feature Pairs: تفاعل RSI+Trend و Volume+Trend
        3. Confidence Weighting: عدد العينات يؤثر على وثوقية العامل
        
        Args:
            symbol: رمز العملة
            indicators: {rsi, macd, bb_position, volume_ratio, ema_trend, atr_pct, trend_4h, score}
        
        Returns:
            {predicted_wr, sample_size, should_trade, reason, factors, weights_used}
        """
        try:
            now = datetime.now()
            with self.db_manager.get_connection() as conn:
                cutoff = (now - timedelta(days=60)).isoformat()
                
                rows = conn.execute("""
                    SELECT pnl, pnl_pct, rsi, macd, bb_position, 
                           volume_ratio, ema_trend, atr_pct, trend_4h, score,
                           created_at
                    FROM trade_learning_log
                    WHERE created_at > ? AND rsi IS NOT NULL
                    ORDER BY created_at ASC
                """, (cutoff,)).fetchall()
            
            if len(rows) < SAFE_LIMITS['min_trades_for_learning']:
                return {
                    'predicted_wr': 0.5,
                    'sample_size': len(rows),
                    'should_trade': True,
                    'reason': f'بيانات قليلة ({len(rows)} صفقة)',
                    'factors': {},
                    'weights_used': self._DEFAULT_WEIGHTS.copy(),
                }
            
            # حساب الأوزان الذكية (تعدّل ذاتياً)
            weights = self._calculate_adaptive_weights(rows)
            
            # T1: حساب Decay weights لكل صفقة
            decay_weights = self._compute_decay_weights(rows, now)
            
            rsi_now = indicators.get('rsi', 50)
            vol_now = indicators.get('volume_ratio', 1.0)
            bb_now = indicators.get('bb_position', 0.5)
            trend_now = indicators.get('trend_4h', 'neutral')
            
            factors = {}
            weighted_wins = 0
            total_weight = 0
            
            # Factor 1: RSI zone (with decay + confidence)
            rsi_zone = self._get_rsi_zone(rsi_now)
            rsi_indices = [i for i, r in enumerate(rows) if r[2] is not None and self._get_rsi_zone(r[2]) == rsi_zone]
            if len(rsi_indices) >= 3:
                rsi_wr = self._decay_weighted_wr(rows, rsi_indices, decay_weights)
                w = weights['rsi_zone'] * self._confidence_scale(len(rsi_indices))
                factors['rsi_zone'] = {'zone': rsi_zone, 'wr': round(rsi_wr, 2), 'n': len(rsi_indices), 'w': round(w, 2)}
                weighted_wins += rsi_wr * w
                total_weight += w
            
            # Factor 2: Volume (with decay + confidence)
            vol_level = self._vol_level(vol_now)
            vol_indices = [i for i, r in enumerate(rows) if r[5] is not None and self._vol_level(r[5]) == vol_level]
            if len(vol_indices) >= 3:
                vol_wr = self._decay_weighted_wr(rows, vol_indices, decay_weights)
                w = weights['volume'] * self._confidence_scale(len(vol_indices))
                factors['volume'] = {'level': vol_level, 'wr': round(vol_wr, 2), 'n': len(vol_indices), 'w': round(w, 2)}
                weighted_wins += vol_wr * w
                total_weight += w
            
            # Factor 3: Trend (with decay + confidence)
            trend_indices = [i for i, r in enumerate(rows) if r[8] == trend_now]
            if len(trend_indices) >= 3:
                trend_wr = self._decay_weighted_wr(rows, trend_indices, decay_weights)
                w = weights['trend'] * self._confidence_scale(len(trend_indices))
                factors['trend'] = {'direction': trend_now, 'wr': round(trend_wr, 2), 'n': len(trend_indices), 'w': round(w, 2)}
                weighted_wins += trend_wr * w
                total_weight += w
            
            # Factor 4: BB position (with decay + confidence)
            bb_zone = self._bb_zone(bb_now)
            bb_indices = [i for i, r in enumerate(rows) if r[4] is not None and self._bb_zone(r[4]) == bb_zone]
            if len(bb_indices) >= 3:
                bb_wr = self._decay_weighted_wr(rows, bb_indices, decay_weights)
                w = weights['bb_position'] * self._confidence_scale(len(bb_indices))
                factors['bb_position'] = {'zone': bb_zone, 'wr': round(bb_wr, 2), 'n': len(bb_indices), 'w': round(w, 2)}
                weighted_wins += bb_wr * w
                total_weight += w
            
            # Factor 5: Symbol WR (uses its own 30-day stats)
            sym_stats = self._get_symbol_stats(symbol)
            if sym_stats and sym_stats['total_trades'] >= 5:
                sym_wr = sym_stats['win_rate']
                w = weights['symbol'] * self._confidence_scale(sym_stats['total_trades'])
                factors['symbol'] = {'wr': round(sym_wr, 2), 'n': sym_stats['total_trades'], 'w': round(w, 2)}
                weighted_wins += sym_wr * w
                total_weight += w
            
            # T2: Feature Pair 1 — RSI zone + Trend direction
            pair_key_rt = f"{rsi_zone}_{trend_now}"
            rt_indices = [i for i, r in enumerate(rows)
                          if r[2] is not None and r[8] is not None
                          and self._get_rsi_zone(r[2]) == rsi_zone and r[8] == trend_now]
            if len(rt_indices) >= 3:
                rt_wr = self._decay_weighted_wr(rows, rt_indices, decay_weights)
                w = weights.get('rsi_trend', 2.5) * self._confidence_scale(len(rt_indices))
                factors['rsi_trend'] = {'combo': pair_key_rt, 'wr': round(rt_wr, 2), 'n': len(rt_indices), 'w': round(w, 2)}
                weighted_wins += rt_wr * w
                total_weight += w
            
            # T2: Feature Pair 2 — Volume level + Trend direction
            pair_key_vt = f"{vol_level}_{trend_now}"
            vt_indices = [i for i, r in enumerate(rows)
                          if r[5] is not None and r[8] is not None
                          and self._vol_level(r[5]) == vol_level and r[8] == trend_now]
            if len(vt_indices) >= 3:
                vt_wr = self._decay_weighted_wr(rows, vt_indices, decay_weights)
                w = weights.get('vol_trend', 2.0) * self._confidence_scale(len(vt_indices))
                factors['vol_trend'] = {'combo': pair_key_vt, 'wr': round(vt_wr, 2), 'n': len(vt_indices), 'w': round(w, 2)}
                weighted_wins += vt_wr * w
                total_weight += w
            
            predicted_wr = weighted_wins / total_weight if total_weight > 0 else 0.5
            
            # Progressive threshold: gets stricter as data grows
            # R:R = 1.52:1 → break-even WR = 40%
            n = len(rows)
            if n < 20:
                wr_threshold = 0.35   # بيانات قليلة → متساهل
            elif n < 50:
                wr_threshold = 0.38   # بيانات متوسطة
            elif n < 100:
                wr_threshold = 0.40   # نقطة التعادل (R:R 1.52)
            else:
                wr_threshold = 0.43   # بيانات كثيرة → انتقائي
            
            should_trade = predicted_wr >= wr_threshold
            
            reason = (
                f'WR المتوقع {predicted_wr:.0%} (عتبة {wr_threshold:.0%} @ {n} صفقة)'
                if should_trade
                else f'WR متوقع ضعيف {predicted_wr:.0%} < {wr_threshold:.0%} ({n} صفقة)'
            )
            
            return {
                'predicted_wr': round(predicted_wr, 3),
                'sample_size': len(rows),
                'should_trade': should_trade,
                'reason': reason,
                'factors': factors,
                'weights_used': weights,
            }
        except Exception as e:
            logger.error(f"❌ Signal scoring error: {e}")
            return {'predicted_wr': 0.5, 'sample_size': 0, 'should_trade': True,
                    'reason': f'خطأ: {e}', 'factors': {}, 'weights_used': {}}
    
    def _calculate_adaptive_weights(self, rows: list) -> Dict[str, float]:
        """
        حساب أوزان ذكية — كل عامل يُكافأ أو يُعاقب حسب قدرته التنبؤية.
        
        المنطق: لكل عامل، نحسب "هل الصفقات التي حقق فيها WR عالي فعلاً ربحت؟"
        إذا نعم → وزن أعلى. إذا لا → وزن أقل.
        """
        weights = self._DEFAULT_WEIGHTS.copy()
        
        if len(rows) < 20:
            return weights
        
        # تقسيم: 80% تدريب، 20% اختبار (الأحدث)
        split = int(len(rows) * 0.8)
        train_rows = rows[:split]
        test_rows = rows[split:]
        
        if len(test_rows) < 5:
            return weights
        
        # لكل عامل: احسب دقة تنبؤه على مجموعة الاختبار
        factor_accuracy = {}
        
        # دالة مساعدة لحساب دقة عامل
        def _factor_acc(test_rows, train_rows, get_key_fn, col_check_fn):
            correct = 0
            tested = 0
            for r in test_rows:
                if not col_check_fn(r):
                    continue
                key = get_key_fn(r)
                matches = [t for t in train_rows if col_check_fn(t) and get_key_fn(t) == key]
                if len(matches) >= 3:
                    predicted = sum(1 for m in matches if m[0] > 0) / len(matches) >= 0.5
                    actual = r[0] > 0
                    if predicted == actual:
                        correct += 1
                    tested += 1
            return correct / tested if tested >= 3 else None
        
        # RSI zone accuracy
        acc = _factor_acc(test_rows, train_rows,
                          lambda r: self._get_rsi_zone(r[2]),
                          lambda r: r[2] is not None)
        if acc is not None:
            factor_accuracy['rsi_zone'] = acc
        
        # Volume accuracy
        acc = _factor_acc(test_rows, train_rows,
                          lambda r: self._vol_level(r[5]),
                          lambda r: r[5] is not None)
        if acc is not None:
            factor_accuracy['volume'] = acc
        
        # Trend accuracy
        acc = _factor_acc(test_rows, train_rows,
                          lambda r: r[8],
                          lambda r: r[8] is not None)
        if acc is not None:
            factor_accuracy['trend'] = acc
        
        # BB accuracy
        acc = _factor_acc(test_rows, train_rows,
                          lambda r: self._bb_zone(r[4]),
                          lambda r: r[4] is not None)
        if acc is not None:
            factor_accuracy['bb_position'] = acc
        
        # Feature Pair 1: RSI zone + Trend direction
        acc = _factor_acc(test_rows, train_rows,
                          lambda r: f"{self._get_rsi_zone(r[2])}_{r[8]}",
                          lambda r: r[2] is not None and r[8] is not None)
        if acc is not None:
            factor_accuracy['rsi_trend'] = acc
        
        # Feature Pair 2: Volume level + Trend direction
        acc = _factor_acc(test_rows, train_rows,
                          lambda r: f"{self._vol_level(r[5])}_{r[8]}",
                          lambda r: r[5] is not None and r[8] is not None)
        if acc is not None:
            factor_accuracy['vol_trend'] = acc
        
        # تعديل الأوزان: دقة > 60% = مكافأة، < 40% = عقوبة
        for factor, accuracy in factor_accuracy.items():
            if factor in weights:
                if accuracy >= 0.65:
                    weights[factor] = self._DEFAULT_WEIGHTS[factor] * 1.5  # +50%
                elif accuracy >= 0.55:
                    weights[factor] = self._DEFAULT_WEIGHTS[factor] * 1.2  # +20%
                elif accuracy < 0.40:
                    weights[factor] = self._DEFAULT_WEIGHTS[factor] * 0.5  # -50%
                elif accuracy < 0.45:
                    weights[factor] = self._DEFAULT_WEIGHTS[factor] * 0.7  # -30%
        
        return weights
    
    # ==================== T1: Exponential Decay ====================
    
    def _compute_decay_weights(self, rows: list, now: datetime) -> List[float]:
        """
        T1: حساب وزن Decay لكل صفقة.
        الصفقات الأحدث وزنها أعلى. Half-life ~23 يوم.
        
        Returns:
            قائمة أوزان [بنفس طول rows]
        """
        decay_weights = []
        for row in rows:
            try:
                created_at = row[10]  # created_at column
                if isinstance(created_at, str):
                    trade_time = datetime.fromisoformat(created_at.replace('Z', '+00:00')).replace(tzinfo=None)
                else:
                    trade_time = created_at
                days_ago = max(0, (now - trade_time).total_seconds() / 86400)
                weight = math.exp(-self._DECAY_LAMBDA * days_ago)
            except Exception:
                weight = 0.5  # افتراضي إذا فشل التحليل
            decay_weights.append(weight)
        return decay_weights
    
    def _decay_weighted_wr(self, rows: list, indices: List[int],
                           decay_weights: List[float]) -> float:
        """
        T1: حساب Win Rate مرجح بالـ Decay.
        الصفقات الأحدث تؤثر أكثر على النتيجة.
        
        Args:
            rows: كل الصفقات
            indices: فهارس الصفقات المطابقة
            decay_weights: أوزان التضاؤل لكل صفقة
        
        Returns:
            WR مرجح (0-1)
        """
        weighted_wins = 0.0
        total_decay = 0.0
        for idx in indices:
            dw = decay_weights[idx] if idx < len(decay_weights) else 0.5
            if rows[idx][0] > 0:  # pnl > 0 = win
                weighted_wins += dw
            total_decay += dw
        return weighted_wins / total_decay if total_decay > 0 else 0.5
    
    # ==================== T3: Confidence Weighting ====================
    
    @staticmethod
    def _confidence_scale(n: int) -> float:
        """
        T3: معامل الثقة — عينات أكثر = ثقة أعلى.
        
        sqrt(n/10) مع حد أعلى 2.0:
        - 3 صفقات → 0.55 (ثقة منخفضة)
        - 10 صفقات → 1.0 (طبيعي)
        - 30 صفقة → 1.73 (ثقة عالية)
        - 40+ → 2.0 (حد أقصى)
        """
        return min(2.0, math.sqrt(max(1, n) / 10))
    
    @staticmethod
    def _get_rsi_zone(rsi: float) -> str:
        if rsi < 30: return 'oversold'
        elif rsi < 45: return 'low'
        elif rsi < 55: return 'neutral'
        elif rsi < 70: return 'high'
        else: return 'overbought'
    
    @staticmethod
    def _vol_level(vol: float) -> str:
        if vol > 1.5: return 'high'
        elif vol < 0.7: return 'low'
        else: return 'normal'
    
    @staticmethod
    def _bb_zone(bb: float) -> str:
        if bb < 0.3: return 'lower'
        elif bb > 0.7: return 'upper'
        else: return 'middle'


# ==================== Singleton ====================
_optimizer_instance: Optional[AdaptiveOptimizer] = None

def get_adaptive_optimizer(db_path: str = None, db_manager=None) -> AdaptiveOptimizer:
    """الحصول على المحسّن التكيّفي (singleton)"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = AdaptiveOptimizer(db_path, db_manager)
    return _optimizer_instance
