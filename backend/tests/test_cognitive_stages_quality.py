#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار جودة المراحل - Cognitive Stages Quality Test
يختبر كل مرحلة من المراحل العشرة بشكل منفصل على بيانات حقيقية
"""

import sys
import os
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

from cognitive import (
    get_cognitive_trading_engine,
    MarketState,
    ConfirmationStatus,
    ReversalPattern,
    ExitStrategy,
)

try:
    import ccxt
    HAS_CCXT = True
except ImportError:
    HAS_CCXT = False
    logger.warning("ccxt غير متاح")


class CognitiveStagesQualityTester:
    """اختبار جودة المراحل المعرفية"""
    
    def __init__(self):
        self.engine = get_cognitive_trading_engine()
        self.exchange = ccxt.binance({'enableRateLimit': True}) if HAS_CCXT else None
        
        # نتائج الاختبار
        self.results = {
            'stage_1_market_state': [],
            'stage_2_asset_classification': [],
            'stage_3_pattern_objective': [],
            'stage_4_strategy_selection': [],
            'stage_5_dynamic_parameters': [],
            'stage_6_reversal_detection': [],
            'stage_7_reasoning': [],
            'stage_8_confirmation': [],
            'stage_9_final_decision': [],
            'stage_10_exit_plan': [],
        }
        
        # تقييم الجودة
        self.quality_scores = {}
    
    def fetch_data(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        """جلب البيانات"""
        if not self.exchange:
            return None
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"خطأ في جلب البيانات: {e}")
            return None
    
    def run_full_test(self):
        """تشغيل الاختبار الكامل"""
        logger.info("=" * 100)
        logger.info("🧪 اختبار جودة المراحل المعرفية - Cognitive Stages Quality Test")
        logger.info("=" * 100)
        
        if not HAS_CCXT:
            logger.error("❌ ccxt غير متاح")
            return
        
        # قائمة العملات للاختبار
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
        
        for symbol in symbols:
            self._test_symbol_all_stages(symbol)
        
        # تقييم شامل
        self._evaluate_all_stages()
        
        # تقرير نهائي
        self._print_final_report()
    
    def _test_symbol_all_stages(self, symbol: str):
        """اختبار جميع المراحل لعملة واحدة"""
        logger.info(f"\n{'='*100}")
        logger.info(f"📊 اختبار العملة: {symbol}")
        logger.info(f"{'='*100}")
        
        try:
            # جلب البيانات
            df_1h = self.fetch_data(symbol, '1h', 200)
            df_15m = self.fetch_data(symbol, '15m', 200)
            
            if df_1h is None or len(df_1h) < 100:
                logger.warning(f"⚠️ بيانات 1H غير كافية لـ {symbol}")
                return
            
            if df_15m is None or len(df_15m) < 100:
                logger.warning(f"⚠️ بيانات 15m غير متاحة لـ {symbol}")
                df_15m = None
            
            # التحليل الكامل
            additional_context = {'df_15m': df_15m} if df_15m is not None else None
            result = self.engine.analyze(symbol, df_1h, additional_context=additional_context)
            
            # اختبار كل مرحلة
            self._test_stage_1_market_state(symbol, result)
            self._test_stage_2_asset_classification(symbol, result)
            self._test_stage_3_pattern_objective(symbol, result)
            self._test_stage_4_strategy_selection(symbol, result)
            self._test_stage_5_dynamic_parameters(symbol, result)
            self._test_stage_6_reversal_detection(symbol, result)
            self._test_stage_7_reasoning(symbol, result)
            self._test_stage_8_confirmation(symbol, result)
            self._test_stage_9_final_decision(symbol, result)
            self._test_stage_10_exit_plan(symbol, result)
            
        except Exception as e:
            logger.error(f"❌ خطأ في اختبار {symbol}: {e}")
    
    def _test_stage_1_market_state(self, symbol: str, result):
        """اختبار المرحلة 1: Market State Detection"""
        logger.info(f"\n🔍 المرحلة 1: Market State Detection")
        
        market_state = result.market_state
        
        # معايير الجودة
        quality = {
            'symbol': symbol,
            'state': market_state.state.value,
            'trend_strength': market_state.trend_strength,
            'confidence': market_state.confidence,
            'is_clear': market_state.confidence >= 40,
            'adx_appropriate': 20 <= market_state.trend_strength <= 60,
            'state_valid': market_state.state != MarketState.RANGE or market_state.trend_strength < 25,
        }
        
        # تقييم
        score = sum([
            quality['is_clear'],
            quality['adx_appropriate'],
            quality['state_valid']
        ]) / 3 * 100
        
        quality['quality_score'] = score
        
        self.results['stage_1_market_state'].append(quality)
        
        logger.info(f"  حالة السوق: {quality['state']}")
        logger.info(f"  قوة الاتجاه (ADX): {quality['trend_strength']:.1f}")
        logger.info(f"  الثقة: {quality['confidence']:.1f}%")
        logger.info(f"  {'✅' if quality['is_clear'] else '❌'} وضوح الحالة")
        logger.info(f"  {'✅' if quality['adx_appropriate'] else '❌'} ADX مناسب")
        logger.info(f"  {'✅' if quality['state_valid'] else '❌'} حالة صحيحة")
        logger.info(f"  📊 نقاط الجودة: {score:.1f}/100")
    
    def _test_stage_2_asset_classification(self, symbol: str, result):
        """اختبار المرحلة 2: Asset Classification"""
        logger.info(f"\n💎 المرحلة 2: Asset Classification")
        
        asset_class = result.asset_class
        
        quality = {
            'symbol': symbol,
            'asset_type': asset_class.asset_type.value,
            'risk_level': asset_class.risk_level,
            'volatility_level': asset_class.volatility_level,
            'liquidity_score': asset_class.liquidity_score,
            'appropriate_risk': asset_class.risk_level in ['low', 'medium'],
            'volatility_reasonable': asset_class.volatility_level in ['low', 'medium'],
            'liquid_enough': asset_class.liquidity_score >= 50.0,
        }
        
        score = sum([
            quality['appropriate_risk'],
            quality['volatility_reasonable'],
            quality['liquid_enough']
        ]) / 3 * 100
        
        quality['quality_score'] = score
        
        self.results['stage_2_asset_classification'].append(quality)
        
        logger.info(f"  نوع الأصل: {quality['asset_type']}")
        logger.info(f"  مستوى المخاطرة: {quality['risk_level']}")
        logger.info(f"  مستوى التقلب: {quality['volatility_level']}")
        logger.info(f"  السيولة: {quality['liquidity_score']:.1f}")
        logger.info(f"  {'✅' if quality['appropriate_risk'] else '⚠️'} مخاطرة مناسبة")
        logger.info(f"  {'✅' if quality['volatility_reasonable'] else '⚠️'} تقلب معقول")
        logger.info(f"  {'✅' if quality['liquid_enough'] else '❌'} سيولة كافية")
        logger.info(f"  📊 نقاط الجودة: {score:.1f}/100")
    
    def _test_stage_3_pattern_objective(self, symbol: str, result):
        """اختبار المرحلة 3: Pattern Objective"""
        logger.info(f"\n🎯 المرحلة 3: Pattern Objective")
        
        objective = result.objective
        
        quality = {
            'symbol': symbol,
            'objective': objective.objective.value,
            'risk_reward': objective.risk_reward_ratio,
            'expected_move': objective.expected_move * 100,
            'has_objective': objective.objective.value != 'abstain',
            'good_rr': objective.risk_reward_ratio >= 1.5,
            'realistic_move': 0.5 <= objective.expected_move * 100 <= 10.0,
        }
        
        score = sum([
            quality['has_objective'],
            quality['good_rr'],
            quality['realistic_move']
        ]) / 3 * 100
        
        quality['quality_score'] = score
        
        self.results['stage_3_pattern_objective'].append(quality)
        
        logger.info(f"  الهدف: {quality['objective']}")
        logger.info(f"  R:R: {quality['risk_reward']:.2f}")
        logger.info(f"  الحركة المتوقعة: {quality['expected_move']:.2f}%")
        logger.info(f"  {'✅' if quality['has_objective'] else '❌'} لديه هدف")
        logger.info(f"  {'✅' if quality['good_rr'] else '⚠️'} R:R جيد")
        logger.info(f"  {'✅' if quality['realistic_move'] else '⚠️'} حركة واقعية")
        logger.info(f"  📊 نقاط الجودة: {score:.1f}/100")
    
    def _test_stage_4_strategy_selection(self, symbol: str, result):
        """اختبار المرحلة 4: Strategy Selection"""
        logger.info(f"\n🎲 المرحلة 4: Strategy Selection")
        
        strategy = result.strategy
        market_state = result.market_state.state.value
        
        quality = {
            'symbol': symbol,
            'strategy': strategy.strategy.value,
            'confidence': strategy.confidence,
            'market_state': market_state,
            'has_strategy': strategy.strategy.value != 'abstain',
            'high_confidence': strategy.confidence >= 70,
            'state_match': self._check_strategy_state_match(strategy.strategy.value, market_state),
        }
        
        score = sum([
            quality['has_strategy'],
            quality['high_confidence'],
            quality['state_match']
        ]) / 3 * 100
        
        quality['quality_score'] = score
        
        self.results['stage_4_strategy_selection'].append(quality)
        
        logger.info(f"  الاستراتيجية: {quality['strategy']}")
        logger.info(f"  الثقة: {quality['confidence']:.1f}%")
        logger.info(f"  حالة السوق: {quality['market_state']}")
        logger.info(f"  {'✅' if quality['has_strategy'] else '❌'} لديه استراتيجية")
        logger.info(f"  {'✅' if quality['high_confidence'] else '⚠️'} ثقة عالية")
        logger.info(f"  {'✅' if quality['state_match'] else '❌'} توافق مع الحالة")
        logger.info(f"  📊 نقاط الجودة: {score:.1f}/100")
    
    def _test_stage_5_dynamic_parameters(self, symbol: str, result):
        """اختبار المرحلة 5: Dynamic Parameters"""
        logger.info(f"\n⚙️ المرحلة 5: Dynamic Parameters")
        
        params = result.parameters
        
        quality = {
            'symbol': symbol,
            'position_size': params.position_size_pct * 100,
            'stop_loss': params.stop_loss_pct * 100,
            'take_profit': params.take_profit_pct * 100,
            'rr_ratio': params.take_profit_pct / params.stop_loss_pct if params.stop_loss_pct > 0 else 0,
            'size_reasonable': 5 <= params.position_size_pct * 100 <= 25,
            'sl_appropriate': 0.5 <= params.stop_loss_pct * 100 <= 3.0,
            'tp_appropriate': 1.0 <= params.take_profit_pct * 100 <= 5.0,
            'good_rr': (params.take_profit_pct / params.stop_loss_pct) >= 1.5 if params.stop_loss_pct > 0 else False,
        }
        
        score = sum([
            quality['size_reasonable'],
            quality['sl_appropriate'],
            quality['tp_appropriate'],
            quality['good_rr']
        ]) / 4 * 100
        
        quality['quality_score'] = score
        
        self.results['stage_5_dynamic_parameters'].append(quality)
        
        logger.info(f"  حجم المركز: {quality['position_size']:.1f}%")
        logger.info(f"  Stop Loss: {quality['stop_loss']:.2f}%")
        logger.info(f"  Take Profit: {quality['take_profit']:.2f}%")
        logger.info(f"  R:R: {quality['rr_ratio']:.2f}")
        logger.info(f"  {'✅' if quality['size_reasonable'] else '⚠️'} حجم معقول")
        logger.info(f"  {'✅' if quality['sl_appropriate'] else '⚠️'} SL مناسب")
        logger.info(f"  {'✅' if quality['tp_appropriate'] else '⚠️'} TP مناسب")
        logger.info(f"  {'✅' if quality['good_rr'] else '⚠️'} R:R جيد")
        logger.info(f"  📊 نقاط الجودة: {score:.1f}/100")
    
    def _test_stage_6_reversal_detection(self, symbol: str, result):
        """اختبار المرحلة 6: Reversal Detection"""
        logger.info(f"\n🔄 المرحلة 6: Reversal Detection")
        
        reversal = result.reversal
        
        if reversal:
            quality = {
                'symbol': symbol,
                'has_reversal': reversal.has_reversal,
                'pattern': reversal.pattern.value if reversal.has_reversal else 'none',
                'confidence': reversal.confidence,
                'strength': reversal.strength,
                'strong_pattern': reversal.confidence >= 65 if reversal.has_reversal else False,
                'high_strength': reversal.strength >= 0.7 if reversal.has_reversal else False,
            }
            
            score = 0
            if reversal.has_reversal:
                score = sum([
                    quality['strong_pattern'],
                    quality['high_strength']
                ]) / 2 * 100
            else:
                score = 50  # لا يوجد انعكاس ليس بالضرورة سيء
            
            quality['quality_score'] = score
        else:
            quality = {
                'symbol': symbol,
                'has_reversal': False,
                'pattern': 'none',
                'quality_score': 50
            }
        
        self.results['stage_6_reversal_detection'].append(quality)
        
        if reversal and reversal.has_reversal:
            logger.info(f"  ✅ نمط انعكاس: {quality['pattern']}")
            logger.info(f"  الثقة: {quality['confidence']:.1f}%")
            logger.info(f"  القوة: {quality['strength']:.2f}")
            logger.info(f"  {'✅' if quality['strong_pattern'] else '⚠️'} نمط قوي")
            logger.info(f"  {'✅' if quality['high_strength'] else '⚠️'} قوة عالية")
        else:
            logger.info(f"  ❌ لا يوجد نمط انعكاس (ليس بالضرورة سيء)")
        
        logger.info(f"  📊 نقاط الجودة: {quality['quality_score']:.1f}/100")
    
    def _test_stage_7_reasoning(self, symbol: str, result):
        """اختبار المرحلة 7: Pre-Trade Reasoning"""
        logger.info(f"\n🧠 المرحلة 7: Pre-Trade Reasoning")
        
        reasoning = result.reasoning
        checklist_score = sum(1 for v in reasoning.checklist.values() if v)
        
        quality = {
            'symbol': symbol,
            'decision': reasoning.decision.value,
            'confidence': reasoning.confidence,
            'checklist_score': checklist_score,
            'warnings_count': len(reasoning.warnings),
            'high_checklist': checklist_score >= 6,
            'high_confidence': reasoning.confidence >= 65,
            'few_warnings': len(reasoning.warnings) <= 2,
        }
        
        score = sum([
            quality['high_checklist'],
            quality['high_confidence'],
            quality['few_warnings']
        ]) / 3 * 100
        
        quality['quality_score'] = score
        
        self.results['stage_7_reasoning'].append(quality)
        
        logger.info(f"  القرار: {quality['decision']}")
        logger.info(f"  الثقة: {quality['confidence']:.1f}%")
        logger.info(f"  Checklist: {quality['checklist_score']}/8")
        logger.info(f"  التحذيرات: {quality['warnings_count']}")
        logger.info(f"  {'✅' if quality['high_checklist'] else '⚠️'} checklist عالي")
        logger.info(f"  {'✅' if quality['high_confidence'] else '⚠️'} ثقة عالية")
        logger.info(f"  {'✅' if quality['few_warnings'] else '⚠️'} تحذيرات قليلة")
        logger.info(f"  📊 نقاط الجودة: {score:.1f}/100")
    
    def _test_stage_8_confirmation(self, symbol: str, result):
        """اختبار المرحلة 8: Confirmation Layer (15m)"""
        logger.info(f"\n🔍 المرحلة 8: Confirmation Layer (15m)")
        
        confirmation = result.confirmation
        
        if confirmation:
            quality = {
                'symbol': symbol,
                'status': confirmation.status.value,
                'confidence': confirmation.confidence,
                'trend_aligned': confirmation.trend_alignment,
                'momentum_aligned': confirmation.momentum_alignment,
                'volume_confirmed': confirmation.volume_confirmation,
                'structure_aligned': confirmation.structure_alignment,
                'is_confirmed': confirmation.status == ConfirmationStatus.CONFIRMED,
                'high_confidence': confirmation.confidence >= 70,
                'all_aligned': all([
                    confirmation.trend_alignment,
                    confirmation.momentum_alignment,
                    confirmation.volume_confirmation,
                    confirmation.structure_alignment
                ]),
            }
            
            score = sum([
                quality['is_confirmed'] or quality['status'] == 'weak',
                quality['high_confidence'] if quality['is_confirmed'] else True,
                sum([
                    quality['trend_aligned'],
                    quality['momentum_aligned'],
                    quality['volume_confirmed'],
                    quality['structure_aligned']
                ]) >= 3
            ]) / 3 * 100
            
            quality['quality_score'] = score
        else:
            quality = {
                'symbol': symbol,
                'status': 'no_15m_data',
                'quality_score': 0
            }
        
        self.results['stage_8_confirmation'].append(quality)
        
        if confirmation:
            logger.info(f"  حالة التأكيد: {quality['status']}")
            logger.info(f"  الثقة: {quality['confidence']:.1f}%")
            logger.info(f"  {'✅' if quality['trend_aligned'] else '❌'} توافق الاتجاه")
            logger.info(f"  {'✅' if quality['momentum_aligned'] else '❌'} توافق الزخم")
            logger.info(f"  {'✅' if quality['volume_confirmed'] else '❌'} تأكيد الحجم")
            logger.info(f"  {'✅' if quality['structure_aligned'] else '❌'} توافق البنية")
            logger.info(f"  📊 نقاط الجودة: {quality['quality_score']:.1f}/100")
        else:
            logger.info(f"  ⚠️ لا توجد بيانات 15m")
            logger.info(f"  📊 نقاط الجودة: 0/100 (بيانات غير متاحة)")
    
    def _test_stage_9_final_decision(self, symbol: str, result):
        """اختبار المرحلة 9: Final Decision"""
        logger.info(f"\n🎯 المرحلة 9: Final Decision")
        
        quality = {
            'symbol': symbol,
            'decision': result.decision.value,
            'should_trade': result.should_trade,
            'confidence': result.confidence,
            'has_entry': result.entry_price is not None,
            'has_sl': result.stop_loss_price is not None,
            'has_tp': result.take_profit_price is not None,
            'complete_plan': all([
                result.entry_price is not None,
                result.stop_loss_price is not None,
                result.take_profit_price is not None
            ]) if result.should_trade else True,
        }
        
        score = 100 if quality['complete_plan'] else 50
        quality['quality_score'] = score
        
        self.results['stage_9_final_decision'].append(quality)
        
        logger.info(f"  القرار النهائي: {quality['decision']}")
        logger.info(f"  يجب التداول: {quality['should_trade']}")
        logger.info(f"  الثقة: {quality['confidence']:.1f}%")
        
        if result.should_trade:
            logger.info(f"  {'✅' if quality['has_entry'] else '❌'} سعر الدخول")
            logger.info(f"  {'✅' if quality['has_sl'] else '❌'} Stop Loss")
            logger.info(f"  {'✅' if quality['has_tp'] else '❌'} Take Profit")
            logger.info(f"  {'✅' if quality['complete_plan'] else '❌'} خطة كاملة")
        
        logger.info(f"  📊 نقاط الجودة: {score:.1f}/100")
    
    def _test_stage_10_exit_plan(self, symbol: str, result):
        """اختبار المرحلة 10: Smart Exit Plan"""
        logger.info(f"\n🚪 المرحلة 10: Smart Exit Plan")
        
        exit_plan = result.exit_plan
        
        if exit_plan and result.should_trade:
            quality = {
                'symbol': symbol,
                'strategy': exit_plan.strategy.value,
                'has_trailing': exit_plan.trailing_activation_pct > 0,
                'has_breakeven': exit_plan.breakeven_at_pct > 0,
                'has_partial_tp': len(exit_plan.partial_tp_levels) > 0,
                'reasonable_max_hold': 12 <= exit_plan.max_hold_hours <= 96,
                'appropriate_strategy': exit_plan.strategy != ExitStrategy.STANDARD or result.objective.objective.value == 'capture_range',
            }
            
            score = sum([
                quality['has_trailing'] or quality['has_partial_tp'],
                quality['has_breakeven'],
                quality['reasonable_max_hold'],
                quality['appropriate_strategy']
            ]) / 4 * 100
            
            quality['quality_score'] = score
        else:
            quality = {
                'symbol': symbol,
                'strategy': 'none' if not exit_plan else exit_plan.strategy.value,
                'quality_score': 0 if not result.should_trade else 50
            }
        
        self.results['stage_10_exit_plan'].append(quality)
        
        if exit_plan and result.should_trade:
            logger.info(f"  استراتيجية الخروج: {quality['strategy']}")
            logger.info(f"  {'✅' if quality['has_trailing'] else '❌'} Trailing Stop")
            logger.info(f"  {'✅' if quality['has_breakeven'] else '❌'} Breakeven")
            logger.info(f"  {'✅' if quality['has_partial_tp'] else '❌'} Partial TP")
            logger.info(f"  {'✅' if quality['reasonable_max_hold'] else '⚠️'} Max Hold معقول")
            logger.info(f"  📊 نقاط الجودة: {quality['quality_score']:.1f}/100")
        else:
            logger.info(f"  ⚠️ لا توجد خطة خروج (لا صفقة)")
            logger.info(f"  📊 نقاط الجودة: {quality['quality_score']:.1f}/100")
    
    def _check_strategy_state_match(self, strategy: str, market_state: str) -> bool:
        """التحقق من توافق الاستراتيجية مع حالة السوق"""
        valid_combinations = {
            'uptrend': ['trend_following', 'pullback_entry'],
            'downtrend': ['abstain'],
            'range': ['mean_reversion', 'rsi_divergence', 'range_scalping'],
            'near_top': ['abstain'],
            'near_bottom': ['pullback_entry', 'reversal'],
        }
        
        if market_state in valid_combinations:
            return strategy in valid_combinations[market_state] or strategy == 'abstain'
        
        return True
    
    def _evaluate_all_stages(self):
        """تقييم جميع المراحل"""
        logger.info(f"\n{'='*100}")
        logger.info("📊 تقييم جودة جميع المراحل")
        logger.info(f"{'='*100}")
        
        for stage_name, stage_results in self.results.items():
            if not stage_results:
                continue
            
            scores = [r['quality_score'] for r in stage_results]
            avg_score = np.mean(scores)
            
            self.quality_scores[stage_name] = {
                'average': avg_score,
                'min': min(scores),
                'max': max(scores),
                'count': len(scores)
            }
            
            # تحديد التقييم
            if avg_score >= 80:
                rating = "ممتاز ⭐⭐⭐⭐⭐"
            elif avg_score >= 70:
                rating = "جيد جداً ⭐⭐⭐⭐"
            elif avg_score >= 60:
                rating = "جيد ⭐⭐⭐"
            elif avg_score >= 50:
                rating = "مقبول ⭐⭐"
            else:
                rating = "ضعيف ⭐"
            
            logger.info(f"\n{stage_name}:")
            logger.info(f"  متوسط الجودة: {avg_score:.1f}/100")
            logger.info(f"  النطاق: {min(scores):.1f} - {max(scores):.1f}")
            logger.info(f"  التقييم: {rating}")
    
    def _print_final_report(self):
        """طباعة التقرير النهائي"""
        logger.info(f"\n{'='*100}")
        logger.info("📋 التقرير النهائي - Final Report")
        logger.info(f"{'='*100}")
        
        # ملخص عام
        all_scores = []
        for stage_scores in self.quality_scores.values():
            all_scores.append(stage_scores['average'])
        
        overall_avg = np.mean(all_scores) if all_scores else 0
        
        logger.info(f"\n🎯 الجودة الإجمالية: {overall_avg:.1f}/100")
        
        # ترتيب المراحل
        sorted_stages = sorted(
            self.quality_scores.items(),
            key=lambda x: x[1]['average'],
            reverse=True
        )
        
        logger.info(f"\n📊 ترتيب المراحل حسب الجودة:")
        for i, (stage, scores) in enumerate(sorted_stages, 1):
            logger.info(f"{i}. {stage}: {scores['average']:.1f}/100")
        
        # نقاط القوة والضعف
        if sorted_stages:
            best_stage = sorted_stages[0]
            worst_stage = sorted_stages[-1]
            
            logger.info(f"\n💪 أقوى مرحلة: {best_stage[0]} ({best_stage[1]['average']:.1f}/100)")
            logger.info(f"⚠️ أضعف مرحلة: {worst_stage[0]} ({worst_stage[1]['average']:.1f}/100)")
        
        # التوصيات
        logger.info(f"\n💡 التوصيات:")
        for stage, scores in sorted_stages:
            if scores['average'] < 70:
                logger.info(f"  - تحسين {stage} (حالياً {scores['average']:.1f}/100)")
        
        logger.info(f"\n{'='*100}")
        logger.info("✅ اكتمل الاختبار بنجاح!")
        logger.info(f"{'='*100}")


def main():
    tester = CognitiveStagesQualityTester()
    tester.run_full_test()


if __name__ == '__main__':
    main()
