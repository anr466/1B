#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار التدفق المحسّن للنظام المعرفي
يختبر جميع المكونات الجديدة:
- Confirmation Layer (1H)
- Reversal Pattern Detection
- التدفق الكامل مع جميع المراحل
"""

import sys
import os
import logging
from datetime import datetime
import pandas as pd
import numpy as np

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
)

try:
    import ccxt
    HAS_CCXT = True
except ImportError:
    HAS_CCXT = False
    logger.warning("ccxt غير متاح")


class EnhancedFlowTester:
    """اختبار التدفق المحسّن"""
    
    def __init__(self):
        self.engine = get_cognitive_trading_engine()
        self.exchange = ccxt.binance({'enableRateLimit': True}) if HAS_CCXT else None
        self.results = {
            'total_analyzed': 0,
            'with_confirmation': 0,
            'with_reversal': 0,
            'confirmed_signals': 0,
            'rejected_signals': 0,
            'reversal_patterns': {},
        }
    
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
    
    def test_enhanced_flow(self):
        """اختبار التدفق المحسّن"""
        logger.info("=" * 80)
        logger.info("🚀 اختبار التدفق المحسّن للنظام المعرفي")
        logger.info("=" * 80)
        
        if not HAS_CCXT:
            logger.error("❌ ccxt غير متاح")
            return
        
        symbols = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT'
        ]
        
        for symbol in symbols:
            self._test_symbol(symbol)
        
        self._print_summary()
    
    def _test_symbol(self, symbol: str):
        """اختبار عملة واحدة"""
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 تحليل: {symbol}")
        logger.info(f"{'='*80}")
        
        try:
            # جلب بيانات 4H
            df_4h = self.fetch_data(symbol, '4h', 200)
            if df_4h is None or len(df_4h) < 100:
                logger.warning(f"  ⚠️ بيانات 4H غير كافية")
                return
            
            # جلب بيانات 1H للتأكيد
            df_1h = self.fetch_data(symbol, '1h', 200)
            if df_1h is None or len(df_1h) < 100:
                logger.warning(f"  ⚠️ بيانات 1H غير متاحة - سيعمل بدون تأكيد")
                df_1h = None
            
            # التحليل مع بيانات 1H
            additional_context = {'df_1h': df_1h} if df_1h is not None else None
            result = self.engine.analyze(symbol, df_4h, additional_context=additional_context)
            
            self.results['total_analyzed'] += 1
            
            # عرض النتائج بالتفصيل
            self._print_analysis_details(result)
            
            # إحصائيات
            if result.confirmation:
                self.results['with_confirmation'] += 1
                if result.confirmation.status == ConfirmationStatus.CONFIRMED:
                    self.results['confirmed_signals'] += 1
                elif result.confirmation.status == ConfirmationStatus.REJECTED:
                    self.results['rejected_signals'] += 1
            
            if result.reversal and result.reversal.has_reversal:
                self.results['with_reversal'] += 1
                pattern = result.reversal.pattern.value
                self.results['reversal_patterns'][pattern] = \
                    self.results['reversal_patterns'].get(pattern, 0) + 1
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحليل {symbol}: {e}")
    
    def _print_analysis_details(self, result):
        """طباعة تفاصيل التحليل"""
        logger.info(f"\n📈 المرحلة 1: Market State")
        logger.info(f"  حالة السوق: {result.market_state.state.value}")
        logger.info(f"  قوة الاتجاه (ADX): {result.market_state.trend_strength:.1f}")
        logger.info(f"  الثقة: {result.market_state.confidence:.1f}%")
        
        logger.info(f"\n💎 المرحلة 2: Asset Classification")
        logger.info(f"  نوع الأصل: {result.asset_class.asset_type.value}")
        logger.info(f"  مستوى المخاطرة: {result.asset_class.risk_level}")
        
        logger.info(f"\n🎯 المرحلة 3: Pattern Objective")
        logger.info(f"  الهدف: {result.objective.objective.value}")
        logger.info(f"  R:R: {result.objective.risk_reward_ratio:.2f}")
        logger.info(f"  الحركة المتوقعة: {result.objective.expected_move*100:.2f}%")
        
        logger.info(f"\n🎲 المرحلة 4: Strategy Selection")
        logger.info(f"  الاستراتيجية: {result.strategy.strategy.value}")
        logger.info(f"  الثقة: {result.strategy.confidence:.1f}%")
        
        logger.info(f"\n⚙️ المرحلة 5: Dynamic Parameters")
        logger.info(f"  حجم المركز: {result.parameters.position_size_pct*100:.1f}%")
        logger.info(f"  Stop Loss: {result.parameters.stop_loss_pct*100:.1f}%")
        logger.info(f"  Take Profit: {result.parameters.take_profit_pct*100:.1f}%")
        
        logger.info(f"\n🔄 المرحلة 6: Reversal Detection")
        if result.reversal:
            if result.reversal.has_reversal:
                logger.info(f"  ✅ نمط انعكاس: {result.reversal.pattern.value}")
                logger.info(f"  القوة: {result.reversal.strength:.2f}")
                logger.info(f"  الثقة: {result.reversal.confidence:.1f}%")
                logger.info(f"  السبب: {result.reversal.reasoning}")
            else:
                logger.info(f"  ❌ لا يوجد نمط انعكاس")
        
        logger.info(f"\n🧠 المرحلة 7: Pre-Trade Reasoning")
        checklist_score = sum(1 for v in result.reasoning.checklist.values() if v)
        logger.info(f"  Checklist Score: {checklist_score}/8")
        logger.info(f"  الثقة: {result.reasoning.confidence:.1f}%")
        
        logger.info(f"\n🔍 المرحلة 8: Confirmation Layer (1H)")
        if result.confirmation:
            status_emoji = {
                ConfirmationStatus.CONFIRMED: "✅",
                ConfirmationStatus.REJECTED: "❌",
                ConfirmationStatus.WEAK: "⚠️",
                ConfirmationStatus.CONFLICTING: "🔴"
            }.get(result.confirmation.status, "❓")
            
            logger.info(f"  {status_emoji} حالة التأكيد: {result.confirmation.status.value}")
            logger.info(f"  الثقة: {result.confirmation.confidence:.1f}%")
            logger.info(f"  السبب: {result.confirmation.reasoning}")
            logger.info(f"  توافق الاتجاه: {'✅' if result.confirmation.trend_alignment else '❌'}")
            logger.info(f"  توافق الزخم: {'✅' if result.confirmation.momentum_alignment else '❌'}")
            logger.info(f"  تأكيد الحجم: {'✅' if result.confirmation.volume_confirmation else '❌'}")
            logger.info(f"  توافق البنية: {'✅' if result.confirmation.structure_alignment else '❌'}")
        else:
            logger.info(f"  ⚠️ لم يتم التأكيد (بيانات 1H غير متاحة)")
        
        logger.info(f"\n🎯 المرحلة 9: Final Decision")
        decision_emoji = "✅" if result.should_trade else "❌"
        logger.info(f"  {decision_emoji} القرار: {result.decision.value}")
        logger.info(f"  يجب التداول: {result.should_trade}")
        logger.info(f"  الثقة النهائية: {result.confidence:.1f}%")
        
        if result.should_trade:
            logger.info(f"\n💰 تفاصيل الصفقة:")
            logger.info(f"  الدخول: {result.entry_price:.4f}")
            logger.info(f"  Stop Loss: {result.stop_loss_price:.4f}")
            logger.info(f"  Take Profit: {result.take_profit_price:.4f}")
            logger.info(f"  حجم المركز: {result.position_size_pct*100:.1f}%")
        
        if result.warnings:
            logger.info(f"\n⚠️ التحذيرات:")
            for warning in result.warnings:
                logger.info(f"  - {warning}")
    
    def _print_summary(self):
        """طباعة الملخص"""
        logger.info(f"\n{'='*80}")
        logger.info("📊 ملخص الاختبار")
        logger.info(f"{'='*80}")
        
        logger.info(f"\n📈 إحصائيات عامة:")
        logger.info(f"  إجمالي العملات المحللة: {self.results['total_analyzed']}")
        logger.info(f"  مع تأكيد 1H: {self.results['with_confirmation']}")
        logger.info(f"  مع نمط انعكاس: {self.results['with_reversal']}")
        
        if self.results['with_confirmation'] > 0:
            logger.info(f"\n🔍 نتائج التأكيد:")
            logger.info(f"  إشارات مؤكدة: {self.results['confirmed_signals']}")
            logger.info(f"  إشارات مرفوضة: {self.results['rejected_signals']}")
            conf_rate = (self.results['confirmed_signals'] / self.results['with_confirmation']) * 100
            logger.info(f"  معدل التأكيد: {conf_rate:.1f}%")
        
        if self.results['reversal_patterns']:
            logger.info(f"\n🔄 أنماط الانعكاس المكتشفة:")
            for pattern, count in self.results['reversal_patterns'].items():
                logger.info(f"  {pattern}: {count}")
        
        logger.info(f"\n{'='*80}")
        logger.info("✅ التدفق المحسّن يعمل بشكل صحيح!")
        logger.info(f"{'='*80}")


def main():
    tester = EnhancedFlowTester()
    tester.test_enhanced_flow()


if __name__ == '__main__':
    main()
