#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML Status Endpoints - واجهات API لحالة نظام التعلم الآلي
للأدمن فقط
"""

from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)

# 🔒 حماية endpoints الأدمن
try:
    from backend.utils.admin_auth import require_admin
except (ImportError, ModuleNotFoundError):
    from functools import wraps
    logger.error("❌ CRITICAL: admin_auth not available - ML endpoints will be blocked")
    def require_admin(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            return jsonify({'success': False, 'error': 'Auth system unavailable'}), 503
        return decorated

from backend.infrastructure.db_access import get_db_manager

# إنشاء Blueprint
ml_status_bp = Blueprint('ml_status', __name__, url_prefix='/ml')
db_manager = get_db_manager()


@ml_status_bp.route('/status', methods=['GET'])
@require_admin
def get_ml_status():
    """
    الحصول على حالة نظام ML الشاملة
    """
    try:
        from backend.ml.hybrid_learning_system import get_hybrid_system, get_all_patterns_status
        from backend.ml.signal_classifier import get_ml_classifier
        
        # حالة النظام الهجين
        hybrid_system = get_hybrid_system()
        hybrid_status = hybrid_system.get_system_status()
        
        # حالة المصنف
        classifier = get_ml_classifier()
        classifier_status = classifier.get_status()
        
        # حالة جميع العملات
        try:
            coins_response = get_monitored_coins()
            payload = coins_response[0].get_json() if isinstance(coins_response, tuple) else coins_response.get_json()
            coins = payload.get('coins', []) if isinstance(payload, dict) else []
        except Exception:
            coins = []
        
        # إحصائيات العملات
        coins_stats = {
            'total': len(coins),
            'strong': len([c for c in coins if c['status'] == 'strong']),
            'normal': len([c for c in coins if c['status'] == 'normal']),
            'weak': len([c for c in coins if c['status'] == 'weak']),
            'blocked': len([c for c in coins if c['status'] == 'blocked']),
            'waiting': len([c for c in coins if c['status'] == 'waiting']),
        }
        
        return jsonify({
            'success': True,
            'coins': coins,
            'hybrid_status': hybrid_status,
            'classifier_status': classifier_status,
            'summary': {
                'total': len(coins),
                'strong': len([c for c in coins if c['status'] == 'strong']),
                'normal': len([c for c in coins if c['status'] == 'normal']),
                'weak': len([c for c in coins if c['status'] == 'weak']),
                'blocked': len([c for c in coins if c['status'] == 'blocked']),
                'waiting': len([c for c in coins if c['status'] == 'waiting']),
            }
        }), 200
        
    except Exception as e:
        logger.error(f"خطأ في جلب حالة ML: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_status_bp.route('/health', methods=['GET'])
@require_admin
def get_ml_health():
    """فحص صحة نظام ML"""
    try:
        from backend.ml.signal_classifier import get_ml_classifier, ML_AVAILABLE
        from backend.ml.trading_brain import get_trading_brain
        
        classifier = get_ml_classifier()
        brain = get_trading_brain()
        
        return jsonify({
            'success': True,
            'ml_available': ML_AVAILABLE,
            'classifier_enabled': classifier.enabled if classifier else False,
            'brain_available': brain is not None,
            'is_ready': classifier.get_status().get('is_ready', False) if classifier else False,
        }), 200
    except Exception as e:
        logger.error(f"خطأ في فحص صحة ML: {e}")
        return jsonify({
            'success': True,
            'ml_available': False,
            'error': str(e)
        }), 200


@ml_status_bp.route('/patterns', methods=['GET'])
@require_admin
def get_patterns_performance():
    """
    الحصول على أداء جميع الأنماط
    """
    try:
        from backend.ml.hybrid_learning_system import get_all_patterns_status
        
        patterns = get_all_patterns_status()
        
        # ترتيب حسب الأداء
        patterns_sorted = sorted(
            patterns,
            key=lambda x: x['confidence'],
            reverse=True
        )
        
        return jsonify({
            'success': True,
            'patterns': patterns_sorted,
            'total': len(patterns_sorted)
        }), 200
        
    except Exception as e:
        logger.error(f"خطأ في جلب أداء الأنماط: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_status_bp.route('/learning-progress', methods=['GET'])
@require_admin
def get_learning_progress():
    """
    الحصول على تقدم التعلم - للمؤشر في لوحة الأدمن
    """
    try:
        from backend.ml.hybrid_learning_system import get_hybrid_system
        from backend.ml.signal_classifier import get_ml_classifier
        
        hybrid_system = get_hybrid_system()
        classifier = get_ml_classifier()
        
        status = hybrid_system.get_system_status()
        classifier_status = classifier.get_status()
        
        # حساب النسبة المئوية للتقدم
        readiness_pct = status['readiness_percentage']
        
        # تحديد المرحلة
        phase = status['current_phase']
        phase_names = {
            'initial': 'المرحلة الأولية',
            'intermediate': 'المرحلة المتوسطة',
            'advanced': 'المرحلة المتقدمة',
            'mature': 'مرحلة النضج'
        }
        
        # حساب الصفقات المتبقية
        remaining_trades = max(0, 200 - status['total_real_trades'])
        
        return jsonify({
            'success': True,
            'progress': {
                'percentage': round(readiness_pct, 1),
                'phase': phase,
                'phase_name': phase_names.get(phase, phase),
                'phase_description': status['phase_description'],
                'is_ready': classifier_status.get('is_ready', False),
                'real_trades': status['total_real_trades'],
                'backtest_data': status['total_backtest_data'],
                'remaining_trades': remaining_trades,
                'current_weights': {
                    'backtest': status['backtest_weight'],
                    'real': status['real_weight']
                },
                'milestones': {
                    'initial': 50,
                    'intermediate': 100,
                    'advanced': 150,
                    'mature': 200
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"خطأ في جلب تقدم التعلم: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_status_bp.route('/pattern/<pattern_id>', methods=['GET'])
@require_admin
def get_pattern_details(pattern_id):
    """
    الحصول على تفاصيل نمط معين
    """
    try:
        from backend.ml.hybrid_learning_system import get_confidence_system
        
        # محاولة الحصول على النظام
        try:
            confidence_system = get_confidence_system(pattern_id)
            summary = confidence_system.get_performance_summary()
            
            return jsonify({
                'success': True,
                'pattern': summary
            }), 200
            
        except KeyError:
            return jsonify({
                'success': False,
                'error': 'Pattern not found'
            }), 404
        
    except Exception as e:
        logger.error(f"خطأ في جلب تفاصيل النمط: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_status_bp.route('/reset-pattern/<pattern_id>', methods=['POST'])
@require_admin
def reset_pattern(pattern_id):
    """
    إعادة تعيين نمط متوقف (للأدمن فقط)
    """
    try:
        from backend.ml.hybrid_learning_system import get_confidence_system
        
        confidence_system = get_confidence_system(pattern_id)
        
        # إعادة تعيين الحالة
        confidence_system.status = 'learning'
        confidence_system.paused_at = None
        confidence_system.current_confidence = confidence_system.initial_confidence
        confidence_system.retry_count += 1
        
        logger.info(f"✅ تم إعادة تعيين النمط: {pattern_id}")
        
        return jsonify({
            'success': True,
            'message': f'تم إعادة تعيين النمط: {pattern_id}',
            'new_status': confidence_system.get_performance_summary()
        }), 200
        
    except Exception as e:
        logger.error(f"خطأ في إعادة تعيين النمط: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_status_bp.route('/learning-status', methods=['GET'])
@require_admin
def get_learning_status():
    """
    حالة نظام التعلم التكيّفي — مؤشر الأدمن
    
    يُرجع: آخر اختبار خفي + إحصائيات التعلم + اتجاه الأداء
    """
    try:
        db = db_manager
        with db.get_connection() as conn:
            # 1. آخر اختبار خفي
            last_validation = conn.execute("""
                SELECT verdict, scorer_accuracy, baseline_accuracy, lift,
                       holdout_size, factor_weights, details, validated_at
                FROM learning_validation_log
                ORDER BY id DESC LIMIT 1
            """).fetchone()
            
            # 2. آخر 5 اختبارات (لتحديد الاتجاه)
            recent_validations = conn.execute("""
                SELECT verdict, scorer_accuracy, lift, validated_at
                FROM learning_validation_log
                ORDER BY id DESC LIMIT 5
            """).fetchall()
            
            # 3. إحصائيات التعلم
            trade_stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN rsi IS NOT NULL THEN 1 ELSE 0 END) as trades_with_indicators,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    ROUND(AVG(pnl_pct), 2) as avg_pnl_pct
                FROM trade_learning_log
            """).fetchone()
            
            # 4. عدد العملات المحظورة
            blocked_symbols = conn.execute("""
                SELECT symbol, 
                       COUNT(*) as trades,
                       ROUND(SUM(CASE WHEN pnl > 0 THEN 1.0 ELSE 0 END) / COUNT(*), 2) as wr
                FROM trade_learning_log
                GROUP BY symbol
                HAVING trades >= 8 AND wr < 0.25
            """).fetchall()
        
        # بناء الاستجابة
        total = trade_stats['total_trades'] if trade_stats else 0
        with_indicators = trade_stats['trades_with_indicators'] if trade_stats else 0
        wins = trade_stats['wins'] if trade_stats else 0
        avg_pnl = trade_stats['avg_pnl_pct'] if trade_stats else 0
        win_rate = round(wins / total, 3) if total > 0 else 0
        
        # تحديد الاتجاه
        trend = 'stable'
        if len(recent_validations) >= 3:
            lifts = [r['lift'] for r in recent_validations]
            if all(l > 0 for l in lifts[:3]):
                trend = 'improving'
            elif all(l < 0 for l in lifts[:3]):
                trend = 'declining'
        
        result = {
            'success': True,
            'learning': {
                'total_trades': total,
                'trades_with_indicators': with_indicators,
                'overall_win_rate': win_rate,
                'avg_pnl_pct': avg_pnl or 0,
                'blocked_symbols': len(blocked_symbols),
                'blocked_list': [dict(r) for r in blocked_symbols],
            },
            'last_validation': None,
            'trend': trend,
            'validation_count': len(recent_validations),
        }
        
        if last_validation:
            result['last_validation'] = {
                'verdict': last_validation['verdict'],
                'accuracy': last_validation['scorer_accuracy'],
                'baseline': last_validation['baseline_accuracy'],
                'lift': last_validation['lift'],
                'holdout_size': last_validation['holdout_size'],
                'validated_at': last_validation['validated_at'],
            }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"❌ Learning status error: {e}")
        return jsonify({
            'success': True,
            'learning': {
                'total_trades': 0,
                'trades_with_indicators': 0,
                'overall_win_rate': 0,
                'avg_pnl_pct': 0,
                'blocked_symbols': 0,
            },
            'last_validation': None,
            'trend': 'unknown',
            'error': str(e),
        }), 200


@ml_status_bp.route('/monitored-coins', methods=['GET'])
@require_admin
def get_monitored_coins():
    """
    العملات المُراقبة مرتبة بالأداء — للعرض في الشاشة الرئيسية
    
    يُرجع: قائمة العملات + ترتيب + WR + عدد الصفقات + متوسط الربح + حالة
    """
    try:
        current_symbols = [
            'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT', 'NEARUSDT',
            'SUIUSDT', 'ARBUSDT', 'APTUSDT', 'INJUSDT', 'LINKUSDT',
        ]
        
        db = db_manager
        with db.get_connection() as conn:
            # إحصائيات كل عملة (آخر 30 يوم)
            from datetime import datetime, timedelta
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            
            try:
                symbol_stats = conn.execute("""
                    SELECT 
                        symbol,
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                        ROUND(AVG(pnl_pct), 2) as avg_pnl_pct,
                        ROUND(SUM(pnl), 2) as total_pnl,
                        MAX(created_at) as last_trade
                    FROM trade_learning_log
                    WHERE created_at > %s
                    GROUP BY symbol
                    ORDER BY avg_pnl_pct DESC
                """, (cutoff,)).fetchall()
            except Exception:
                symbol_stats = []
            
            # عدد الصفقات النشطة لكل عملة
            active_counts = {}
            try:
                active_rows = conn.execute("""
                    SELECT symbol, COUNT(*) as cnt
                    FROM active_positions 
                    WHERE is_active = TRUE
                    GROUP BY symbol
                """).fetchall()
                active_counts = {}
                for r in active_rows:
                    try:
                        active_counts[r['symbol']] = r['cnt']
                    except Exception:
                        active_counts[r[0]] = r[1]
            except Exception:
                pass
        
        # بناء خريطة الإحصائيات
        stats_map = {}
        for row in symbol_stats:
            try:
                symbol = row['symbol']
                total = row['total_trades']
                wins = row['wins']
                avg_pnl_pct = row['avg_pnl_pct']
                total_pnl = row['total_pnl']
                last_trade = row['last_trade']
            except Exception:
                symbol, total, wins, avg_pnl_pct, total_pnl, last_trade = row
            wr = round(wins / total, 2) if total > 0 else 0
            stats_map[symbol] = {
                'total_trades': total,
                'wins': wins,
                'win_rate': wr,
                'avg_pnl_pct': avg_pnl_pct or 0,
                'total_pnl': total_pnl or 0,
                'last_trade': last_trade,
            }
        
        # ترتيب العملات الحالية بالأداء
        coins = []
        for i, symbol in enumerate(current_symbols):
            s = stats_map.get(symbol, {})
            total = s.get('total_trades', 0)
            wr = s.get('win_rate', 0)
            avg_pnl = s.get('avg_pnl_pct', 0)
            
            # حساب score
            score = round(wr * 0.6 + max(min(avg_pnl / 5, 0.4), -0.4), 2) if total >= 3 else 0
            
            # تحديد الحالة
            if total == 0:
                status = 'waiting'
            elif wr >= 0.55:
                status = 'strong'
            elif wr >= 0.40:
                status = 'normal'
            elif total >= 8 and wr < 0.25:
                status = 'blocked'
            else:
                status = 'weak'
            
            coins.append({
                'symbol': symbol,
                'rank': i + 1,
                'total_trades': total,
                'wins': s.get('wins', 0),
                'win_rate': wr,
                'avg_pnl_pct': avg_pnl,
                'total_pnl': s.get('total_pnl', 0),
                'score': score,
                'status': status,
                'active_positions': active_counts.get(symbol, 0),
                'last_trade': s.get('last_trade'),
            })
        
        # ترتيب بالـ score
        coins.sort(key=lambda c: c['score'], reverse=True)
        for i, coin in enumerate(coins):
            coin['rank'] = i + 1
        
        return jsonify({
            'success': True,
            'coins': coins,
            'total': len(coins),
            'period_days': 30,
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Monitored coins error: {e}")
        return jsonify({
            'success': True,
            'coins': [],
            'total': 0,
            'period_days': 30,
            'error': str(e),
        }), 200
