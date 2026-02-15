#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار النظام المحسّن v3.1
يختبر التحسينات على بيانات حقيقية من Binance مع دعم 15m
"""

import sys
import os
import logging
from datetime import datetime
import pandas as pd
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

from cognitive import get_cognitive_trading_engine

try:
    import ccxt
    HAS_CCXT = True
except ImportError:
    HAS_CCXT = False
    logger.warning("ccxt غير متاح")


class ImprovedSystemTester:
    """اختبار النظام المحسّن"""
    
    def __init__(self):
        self.engine = get_cognitive_trading_engine()
        self.exchange = ccxt.binance({'enableRateLimit': True}) if HAS_CCXT else None
        
        # نتائج الاختبار
        self.results = []
        self.stats = {
            'total': 0,
            'execute': 0,
            'wait': 0,
            'abstain': 0,
            'avg_confidence': 0.0,
            'avg_rr': 0.0,
            'avg_checklist': 0.0
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
    
    def test_symbol(self, symbol: str) -> Dict:
        """اختبار عملة واحدة"""
        logger.info(f"\n{'='*100}")
        logger.info(f"📊 تحليل: {symbol}")
        logger.info(f"{'='*100}")
        
        try:
            # جلب بيانات 1H و 15m
            df_1h = self.fetch_data(symbol, '1h', 200)
            df_15m = self.fetch_data(symbol, '15m', 200)
            
            if df_1h is None or len(df_1h) < 100:
                logger.warning(f"⚠️ بيانات 1H غير كافية")
                return None
            
            if df_15m is None or len(df_15m) < 100:
                logger.warning(f"⚠️ بيانات 15m غير متاحة")
                df_15m = None
            
            # التحليل مع 15m
            additional_context = {'df_15m': df_15m} if df_15m is not None else None
            result = self.engine.analyze(symbol, df_1h, additional_context=additional_context)
            
            # استخراج المعلومات
            checklist_score = sum(1 for v in result.reasoning.checklist.values() if v)
            
            analysis = {
                'symbol': symbol,
                'decision': result.decision.value,
                'should_trade': result.should_trade,
                'confidence': result.confidence,
                'checklist_score': checklist_score,
                'market_state': result.market_state.state.value,
                'strategy': result.strategy.strategy.value,
                'rr': result.objective.risk_reward_ratio,
                'sl_pct': result.parameters.stop_loss_pct * 100 if result.parameters else 0,
                'tp_pct': result.parameters.take_profit_pct * 100 if result.parameters else 0,
                'has_reversal': result.reversal.has_reversal if result.reversal else False,
                'reversal_pattern': result.reversal.pattern.value if (result.reversal and result.reversal.has_reversal) else 'none',
                'confirmation_status': result.confirmation.status.value if result.confirmation else 'no_15m',
                'exit_strategy': result.exit_plan.strategy.value if result.exit_plan else 'none',
                'warnings': result.warnings
            }
            
            # طباعة النتائج
            self._print_analysis(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحليل {symbol}: {e}")
            return None
    
    def _print_analysis(self, analysis: Dict):
        """طباعة نتائج التحليل"""
        logger.info(f"\n📈 حالة السوق: {analysis['market_state']}")
        logger.info(f"🎲 الاستراتيجية: {analysis['strategy']}")
        logger.info(f"🎯 القرار: {analysis['decision'].upper()}")
        logger.info(f"✅ يجب التداول: {'نعم' if analysis['should_trade'] else 'لا'}")
        logger.info(f"💯 الثقة: {analysis['confidence']:.1f}%")
        logger.info(f"📋 Checklist: {analysis['checklist_score']}/8")
        logger.info(f"⚖️ R:R: {analysis['rr']:.2f}")
        
        if analysis['should_trade']:
            logger.info(f"\n💰 تفاصيل الصفقة:")
            logger.info(f"  Stop Loss: {analysis['sl_pct']:.2f}%")
            logger.info(f"  Take Profit: {analysis['tp_pct']:.2f}%")
            logger.info(f"  استراتيجية الخروج: {analysis['exit_strategy']}")
        
        if analysis['has_reversal']:
            logger.info(f"\n🔄 نمط الانعكاس: {analysis['reversal_pattern']}")
        
        if analysis['confirmation_status'] != 'no_15m':
            logger.info(f"🔍 التأكيد (15m): {analysis['confirmation_status']}")
        
        if analysis['warnings']:
            logger.info(f"\n⚠️ التحذيرات:")
            for warning in analysis['warnings']:
                logger.info(f"  - {warning}")
    
    def run_test(self, symbols: List[str]):
        """تشغيل الاختبار على عدة عملات"""
        logger.info("=" * 100)
        logger.info("🚀 اختبار النظام المحسّن v3.1")
        logger.info("=" * 100)
        logger.info(f"\n📋 التحسينات:")
        logger.info(f"  ✅ MIN_CHECKLIST_SCORE: 6 → 4")
        logger.info(f"  ✅ MIN_CONFIDENCE: 70% → 50%")
        logger.info(f"  ✅ MIN_RISK_REWARD: 2.0 → 1.5")
        logger.info(f"  ✅ UPTREND SL: 1.5% → 1.2%")
        logger.info(f"  ✅ UPTREND TP: 2.0% → 2.4% (R:R = 2.0)")
        logger.info(f"  ✅ NEAR_BOTTOM SL: 3.5% → 2.5%")
        logger.info(f"  ✅ NEAR_BOTTOM TP: 7.0% → 5.5% (R:R = 2.2)")
        logger.info(f"\n🔍 الإطارات الزمنية: 1H (تنفيذ) + 15m (تأكيد)")
        
        if not HAS_CCXT:
            logger.error("❌ ccxt غير متاح")
            return
        
        # اختبار كل عملة
        for symbol in symbols:
            analysis = self.test_symbol(symbol)
            if analysis:
                self.results.append(analysis)
        
        # حساب الإحصائيات
        self._calculate_stats()
        
        # طباعة التقرير النهائي
        self._print_report()
    
    def _calculate_stats(self):
        """حساب الإحصائيات"""
        if not self.results:
            return
        
        self.stats['total'] = len(self.results)
        self.stats['execute'] = sum(1 for r in self.results if r['should_trade'])
        self.stats['wait'] = sum(1 for r in self.results if r['decision'] == 'wait')
        self.stats['abstain'] = sum(1 for r in self.results if r['decision'] == 'abstain')
        
        self.stats['avg_confidence'] = sum(r['confidence'] for r in self.results) / len(self.results)
        self.stats['avg_rr'] = sum(r['rr'] for r in self.results) / len(self.results)
        self.stats['avg_checklist'] = sum(r['checklist_score'] for r in self.results) / len(self.results)
    
    def _print_report(self):
        """طباعة التقرير النهائي"""
        logger.info(f"\n{'='*100}")
        logger.info("📊 التقرير النهائي - Final Report")
        logger.info(f"{'='*100}")
        
        logger.info(f"\n📈 الإحصائيات العامة:")
        logger.info(f"  إجمالي العملات: {self.stats['total']}")
        logger.info(f"  ✅ صفقات للتنفيذ: {self.stats['execute']} ({self.stats['execute']/self.stats['total']*100:.1f}%)")
        logger.info(f"  ⏳ انتظار: {self.stats['wait']} ({self.stats['wait']/self.stats['total']*100:.1f}%)")
        logger.info(f"  ❌ امتناع: {self.stats['abstain']} ({self.stats['abstain']/self.stats['total']*100:.1f}%)")
        
        logger.info(f"\n💯 المتوسطات:")
        logger.info(f"  الثقة: {self.stats['avg_confidence']:.1f}%")
        logger.info(f"  R:R: {self.stats['avg_rr']:.2f}")
        logger.info(f"  Checklist: {self.stats['avg_checklist']:.1f}/8")
        
        # الصفقات القابلة للتنفيذ
        execute_trades = [r for r in self.results if r['should_trade']]
        if execute_trades:
            logger.info(f"\n🎯 الصفقات القابلة للتنفيذ ({len(execute_trades)}):")
            for trade in execute_trades:
                logger.info(f"  {trade['symbol']}: {trade['strategy']} | "
                          f"R:R {trade['rr']:.2f} | "
                          f"SL {trade['sl_pct']:.2f}% | "
                          f"TP {trade['tp_pct']:.2f}% | "
                          f"الثقة {trade['confidence']:.1f}%")
        
        # مقارنة مع النتائج السابقة
        logger.info(f"\n📊 المقارنة مع الاختبار السابق:")
        logger.info(f"  قبل التحسينات:")
        logger.info(f"    - الجودة الإجمالية: 60.5/100")
        logger.info(f"    - Reasoning: 46.7/100 (ضعيف)")
        logger.info(f"    - صفقات للتنفيذ: 0% (جميعها ABSTAIN)")
        logger.info(f"  ")
        logger.info(f"  بعد التحسينات:")
        logger.info(f"    - صفقات للتنفيذ: {self.stats['execute']/self.stats['total']*100:.1f}%")
        logger.info(f"    - متوسط الثقة: {self.stats['avg_confidence']:.1f}%")
        logger.info(f"    - متوسط R:R: {self.stats['avg_rr']:.2f}")
        
        improvement = (self.stats['execute']/self.stats['total']*100) if self.stats['total'] > 0 else 0
        logger.info(f"\n✨ التحسن: من 0% إلى {improvement:.1f}% (+{improvement:.1f}%)")
        
        logger.info(f"\n{'='*100}")
        logger.info("✅ اكتمل الاختبار!")
        logger.info(f"{'='*100}")


def main():
    """تشغيل الاختبار"""
    tester = ImprovedSystemTester()
    
    # قائمة العملات للاختبار
    symbols = [
        'BTC/USDT',
        'ETH/USDT',
        'BNB/USDT',
        'SOL/USDT',
        'XRP/USDT',
        'ADA/USDT',
        'DOGE/USDT',
        'AVAX/USDT',
        'DOT/USDT',
        'MATIC/USDT'
    ]
    
    tester.run_test(symbols)


if __name__ == '__main__':
    main()
