#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار نظام التداول المعرفي على بيانات Binance حقيقية
يجلب بيانات شهر سابق ويختبر النظام عليها
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List
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
    AssetType,
    PatternObjective,
    StrategyType,
    TradeDecision,
)

try:
    import ccxt
    HAS_CCXT = True
except ImportError:
    HAS_CCXT = False
    logger.warning("ccxt غير متاح")


class SimpleDataProvider:
    """مزود بيانات بسيط باستخدام ccxt"""
    
    def __init__(self):
        if not HAS_CCXT:
            raise ImportError("ccxt غير متاح")
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
    
    def get_historical_data(self, symbol: str, timeframe: str = '4h', limit: int = 200) -> pd.DataFrame:
        """جلب البيانات التاريخية"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
        except Exception as e:
            logger.error(f"خطأ في جلب البيانات: {e}")
            return None


class RealDataTester:
    """اختبار على بيانات Binance حقيقية"""
    
    SYMBOLS = [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
        'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT',
    ]
    
    def __init__(self):
        self.engine = get_cognitive_trading_engine()
        self.data_provider = SimpleDataProvider() if HAS_CCXT else None
        
        self.results = {
            'analyses': [],
            'decisions': {'execute': 0, 'abstain': 0, 'wait': 0, 'exit': 0},
            'by_state': {},
            'by_strategy': {},
            'signals': [],
        }
    
    def run_test(self):
        """تشغيل الاختبار"""
        logger.info("=" * 60)
        logger.info("🚀 اختبار على بيانات Binance حقيقية")
        logger.info("=" * 60)
        
        if not self.data_provider:
            logger.error("❌ Data Provider غير متاح")
            return self.results
        
        for symbol in self.SYMBOLS:
            self._analyze_symbol(symbol)
        
        self._print_summary()
        return self.results
    
    def _analyze_symbol(self, symbol: str):
        """تحليل عملة واحدة"""
        logger.info(f"\n📊 تحليل {symbol}...")
        
        try:
            # جلب بيانات 4H
            df = self.data_provider.get_historical_data(
                symbol=symbol,
                timeframe='4h',
                limit=200
            )
            
            if df is None or len(df) < 50:
                logger.warning(f"  ⚠️ بيانات غير كافية")
                return
            
            # تحليل
            result = self.engine.analyze(symbol, df)
            
            # تسجيل النتائج
            analysis = {
                'symbol': symbol,
                'decision': result.decision.value,
                'should_trade': result.should_trade,
                'confidence': result.confidence,
                'market_state': result.market_state.state.value,
                'asset_type': result.asset_class.asset_type.value,
                'objective': result.objective.objective.value,
                'strategy': result.strategy.strategy.value,
                'risk_reward': result.objective.risk_reward_ratio,
                'entry_price': result.entry_price,
                'stop_loss': result.stop_loss_price,
                'take_profit': result.take_profit_price,
            }
            self.results['analyses'].append(analysis)
            
            # تحديث الإحصائيات
            self.results['decisions'][result.decision.value] += 1
            
            state = result.market_state.state.value
            if state not in self.results['by_state']:
                self.results['by_state'][state] = {'total': 0, 'trades': 0}
            self.results['by_state'][state]['total'] += 1
            if result.should_trade:
                self.results['by_state'][state]['trades'] += 1
            
            strategy = result.strategy.strategy.value
            if strategy not in self.results['by_strategy']:
                self.results['by_strategy'][strategy] = 0
            self.results['by_strategy'][strategy] += 1
            
            # طباعة النتيجة
            emoji = "✅" if result.should_trade else "❌"
            logger.info(
                f"  {emoji} State: {state} | Strategy: {strategy} | "
                f"Conf: {result.confidence:.1f}% | R:R: {result.objective.risk_reward_ratio:.2f}"
            )
            
            # إضافة للإشارات إذا كان يجب التداول
            if result.should_trade:
                signal = self.engine.get_trade_signal(result)
                self.results['signals'].append(signal)
                logger.info(f"  💰 Entry: {signal['entry_price']:.4f} | SL: {signal['stop_loss']:.4f} | TP: {signal['take_profit']:.4f}")
            
        except Exception as e:
            logger.error(f"  ❌ خطأ: {e}")
    
    def _print_summary(self):
        """طباعة الملخص"""
        logger.info("\n" + "=" * 60)
        logger.info("📋 ملخص النتائج")
        logger.info("=" * 60)
        
        total = len(self.results['analyses'])
        trades = self.results['decisions']['execute']
        
        logger.info(f"\n📊 إجمالي التحليلات: {total}")
        logger.info(f"✅ قرارات تداول: {trades} ({trades/total*100:.1f}%)" if total > 0 else "✅ قرارات تداول: 0")
        logger.info(f"❌ قرارات امتناع: {self.results['decisions']['abstain']}")
        
        logger.info("\n📈 حسب حالة السوق:")
        for state, data in self.results['by_state'].items():
            logger.info(f"  {state}: {data['trades']}/{data['total']} صفقات")
        
        logger.info("\n🎲 حسب الاستراتيجية:")
        for strategy, count in self.results['by_strategy'].items():
            logger.info(f"  {strategy}: {count}")
        
        if self.results['signals']:
            logger.info("\n💰 الإشارات المولدة:")
            for signal in self.results['signals']:
                logger.info(f"  {signal['symbol']}: {signal['strategy']} @ {signal['entry_price']:.4f}")
        
        logger.info("\n" + "=" * 60)


def main():
    tester = RealDataTester()
    results = tester.run_test()
    return results


if __name__ == '__main__':
    main()
