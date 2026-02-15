#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real Cognitive System Test - اختبار النظام المعرفي الفعلي
=========================================================

يطبق التدفق الفعلي الكامل:
1. Market State Detection
2. Asset Classification
3. Pattern Objective Analysis
4. Strategy Selection
5. Dynamic Parameters
6. Reversal Detection
7. Pre-Trade Reasoning
8. Confirmation Layer (1H → 15m)
9. Smart Exit Integration

Timeframe Doctrine:
- 4H = Execution timeframe
- 1H = Confirmation timeframe
- 15m = Fine confirmation (optional)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional

from cognitive import get_cognitive_trading_engine
from trade_management.smart_exit_system_v2 import SmartExitSystemV2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class RealCognitiveSystemTester:
    """اختبار النظام المعرفي الفعلي"""
    
    def __init__(self, timeframe_mode='4h_1h'):
        """
        Args:
            timeframe_mode: '4h_1h' (Doctrine) أو '1h_15m' (Fast Trading)
        """
        self.exchange = ccxt.binance()
        self.cognitive_engine = get_cognitive_trading_engine()
        self.exit_system = SmartExitSystemV2()
        self.timeframe_mode = timeframe_mode
        
        # تحديد الأطر الزمنية
        if timeframe_mode == '4h_1h':
            self.execution_tf = '4h'
            self.confirmation_tf = '1h'
            self.fine_tf = '15m'
            self.max_hold_hours = 96  # 4 أيام
        else:  # 1h_15m
            self.execution_tf = '1h'
            self.confirmation_tf = '15m'
            self.fine_tf = '5m'
            self.max_hold_hours = 24  # يوم واحد
        
        self.results = {}
        self.blacklist = ['MATIC/USDT']
        
        logger.info(f"🚀 تهيئة الاختبار - النمط: {timeframe_mode}")
        logger.info(f"   Execution: {self.execution_tf} | Confirmation: {self.confirmation_tf}")
    
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """جلب البيانات من Binance"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # إضافة المؤشرات الأساسية
            df = self._add_indicators(df)
            
            return df
        except Exception as e:
            logger.error(f"❌ خطأ في جلب البيانات {symbol} {timeframe}: {e}")
            return pd.DataFrame()
    
    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """إضافة المؤشرات الأساسية"""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain / loss))
        
        # EMAs
        df['ema_9'] = df['close'].ewm(span=9).mean()
        df['ema_20'] = df['close'].ewm(span=20).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # Bollinger Bands
        df['sma_20'] = df['close'].rolling(20).mean()
        df['std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['sma_20'] + (2 * df['std'])
        df['bb_lower'] = df['sma_20'] - (2 * df['std'])
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        
        return df
    
    def get_volume_24h(self, symbol: str) -> float:
        """جلب حجم التداول 24 ساعة"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker.get('quoteVolume', 0)
        except:
            return 0
    
    def run_backtest(self, symbol: str):
        """تشغيل backtest كامل"""
        if symbol in self.blacklist:
            logger.info(f"⚠️ {symbol} في القائمة السوداء")
            return
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🔬 {symbol} - النظام المعرفي الفعلي ({self.timeframe_mode})")
        logger.info(f"{'='*80}")
        
        # 1. جلب البيانات حسب Timeframe Doctrine
        df_exec = self.fetch_ohlcv(symbol, self.execution_tf, limit=500)
        df_conf = self.fetch_ohlcv(symbol, self.confirmation_tf, limit=1000)
        df_fine = self.fetch_ohlcv(symbol, self.fine_tf, limit=2000)
        
        if df_exec.empty or df_conf.empty:
            logger.error(f"❌ بيانات غير كافية")
            return
        
        logger.info(f"📊 البيانات: {self.execution_tf}={len(df_exec)} | {self.confirmation_tf}={len(df_conf)}")
        
        # 2. حجم التداول
        volume_24h = self.get_volume_24h(symbol)
        
        # 3. محاكاة التداول
        trades = []
        position = None
        signals_found = 0
        signals_confirmed = 0
        signals_executed = 0
        
        # البدء من index آمن
        start_idx = 100
        
        for idx in range(start_idx, len(df_exec) - 5):
            current_time = df_exec['timestamp'].iloc[idx]
            current_price = df_exec['close'].iloc[idx]
            
            # إدارة الصفقة المفتوحة
            if position:
                # تحديث أعلى سعر
                position['highest_price'] = max(position['highest_price'], current_price)
                
                # جمع بيانات الشمعة الحالية
                candle_data = {
                    'open': df_exec['open'].iloc[idx],
                    'high': df_exec['high'].iloc[idx],
                    'low': df_exec['low'].iloc[idx],
                    'close': current_price,
                    'volume': df_exec['volume'].iloc[idx],
                    'timestamp': current_time,
                    'rsi': df_exec['rsi'].iloc[idx],
                    'macd': df_exec['macd'].iloc[idx],
                    'macd_signal': df_exec['macd_signal'].iloc[idx],
                    'ema9': df_exec['ema_9'].iloc[idx],
                    'ema20': df_exec['ema_20'].iloc[idx],
                }
                
                # فحص الخروج
                exit_check = self.exit_system.check_exit_conditions(
                    position_id=position['id'],
                    current_price=current_price,
                    timestamp=current_time,
                    candle_data=candle_data
                )
                
                if exit_check.get('should_exit', False):
                    hold_hours = (current_time - position['entry_time']).total_seconds() / 3600
                    pnl_pct = ((exit_check['exit_price'] - position['entry_price']) / position['entry_price']) * 100
                    
                    trade = {
                        'symbol': symbol,
                        'entry_time': position['entry_time'],
                        'entry_price': position['entry_price'],
                        'exit_time': current_time,
                        'exit_price': exit_check['exit_price'],
                        'exit_reason': exit_check['reason'],
                        'pnl_pct': pnl_pct,
                        'hold_hours': hold_hours,
                        'is_win': pnl_pct > 0,
                        'confidence': position['confidence'],
                        'strategy': position['strategy'],
                        'market_state': position['market_state'],
                        'asset_type': position['asset_type']
                    }
                    
                    trades.append(trade)
                    
                    status = "✅" if trade['is_win'] else "❌"
                    logger.info(
                        f"{status} #{len(trades)} | {position['entry_price']:.2f} → {exit_check['exit_price']:.2f} | "
                        f"PnL: {pnl_pct:+.2f}% | {hold_hours:.1f}h | {exit_check['reason']}"
                    )
                    
                    # تسجيل النتيجة للتعلم
                    from cognitive.market_state_detector import MarketState
                    from cognitive.asset_classifier import AssetType
                    from cognitive.strategy_selector import StrategyType
                    
                    self.cognitive_engine.record_trade_outcome(
                        symbol=symbol,
                        market_state=MarketState[position['market_state']],
                        asset_type=AssetType[position['asset_type']],
                        strategy_type=StrategyType[position['strategy']],
                        is_win=trade['is_win'],
                        profit_pct=pnl_pct / 100
                    )
                    
                    position = None
            
            # البحث عن دخول جديد
            if not position:
                # الحصول على البيانات حتى الآن
                df_exec_current = df_exec.iloc[:idx+1]
                
                # البحث عن df_conf و df_fine المناسبة للوقت الحالي
                current_time = df_exec['timestamp'].iloc[idx]
                df_conf_current = df_conf[df_conf['timestamp'] <= current_time]
                df_fine_current = df_fine[df_fine['timestamp'] <= current_time]
                
                if len(df_conf_current) < 50:
                    continue
                
                # التحليل المعرفي الكامل
                try:
                    analysis = self.cognitive_engine.analyze(
                        symbol=symbol,
                        df=df_exec_current,
                        volume_24h_usd=volume_24h,
                        additional_context={
                            'df_1h': df_conf_current,
                            'df_15m': df_fine_current
                        }
                    )
                    
                    signals_found += 1
                    
                    # التحقق من القرار
                    if analysis.should_trade and analysis.confidence >= 65:
                        signals_confirmed += 1
                        
                        # الدخول
                        position_id = f"{symbol}_{current_time.strftime('%Y%m%d_%H%M')}"
                        entry_price = analysis.entry_price
                        
                        # تسجيل الصفقة في exit_system
                        self.exit_system.open_position(
                            position_id=position_id,
                            symbol=symbol,
                            entry_price=entry_price,
                            timestamp=current_time,
                            position_size=100.0,  # افتراضي
                            stop_loss_price=analysis.stop_loss_price,
                            take_profit_price=analysis.take_profit_price
                        )
                        
                        position = {
                            'id': position_id,
                            'entry_time': current_time,
                            'entry_price': entry_price,
                            'highest_price': entry_price,
                            'confidence': analysis.confidence,
                            'strategy': analysis.strategy.strategy.value,
                            'market_state': analysis.market_state.state.value,
                            'asset_type': analysis.asset_class.asset_type.value
                        }
                        
                        signals_executed += 1
                        
                        logger.info(
                            f"🎯 دخول #{signals_executed} | السعر: {entry_price:.2f} | "
                            f"الثقة: {analysis.confidence:.0f}% | {analysis.strategy.strategy.value}"
                        )
                        
                except Exception as e:
                    logger.error(f"خطأ في التحليل: {e}")
                    continue
        
        # إغلاق الصفقة المفتوحة إن وجدت
        if position:
            current_price = df_exec['close'].iloc[-1]
            current_time = df_exec['timestamp'].iloc[-1]
            hold_hours = (current_time - position['entry_time']).total_seconds() / 3600
            pnl_pct = ((current_price - position['entry_price']) / position['entry_price']) * 100
            
            trade = {
                'symbol': symbol,
                'entry_time': position['entry_time'],
                'entry_price': position['entry_price'],
                'exit_time': current_time,
                'exit_price': current_price,
                'exit_reason': 'Max_Hold_Time',
                'pnl_pct': pnl_pct,
                'hold_hours': hold_hours,
                'is_win': pnl_pct > 0,
                'confidence': position['confidence'],
                'strategy': position['strategy'],
                'market_state': position['market_state'],
                'asset_type': position['asset_type']
            }
            trades.append(trade)
        
        # حفظ النتائج
        self.results[symbol] = trades
        
        # الملخص
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 الإشارات: {signals_found} | المؤكدة: {signals_confirmed} | المنفذة: {signals_executed}")
        logger.info(f"{'='*60}")
        
        if trades:
            self._print_summary(trades, symbol)
    
    def _print_summary(self, trades: List[Dict], symbol: str):
        """ملخص النتائج"""
        total = len(trades)
        wins = [t for t in trades if t['is_win']]
        total_pnl = sum(t['pnl_pct'] for t in trades)
        win_rate = len(wins) / total * 100 if total > 0 else 0
        avg_hold = np.mean([t['hold_hours'] for t in trades])
        
        logger.info(f"\n📊 ملخص {symbol}:")
        logger.info(f"   الصفقات: {total} | النجاح: {win_rate:.1f}% | PnL: {total_pnl:+.2f}% | المدة: {avg_hold:.1f}h")
        
        # حسب الاستراتيجية
        by_strategy = {}
        for t in trades:
            s = t['strategy']
            if s not in by_strategy:
                by_strategy[s] = {'count': 0, 'wins': 0, 'pnl': 0}
            by_strategy[s]['count'] += 1
            by_strategy[s]['pnl'] += t['pnl_pct']
            if t['is_win']:
                by_strategy[s]['wins'] += 1
        
        if by_strategy:
            logger.info(f"\n   الاستراتيجيات:")
            for strategy, stats in sorted(by_strategy.items(), key=lambda x: x[1]['count'], reverse=True):
                wr = (stats['wins'] / stats['count']) * 100 if stats['count'] else 0
                logger.info(f"      {strategy}: {stats['count']} | نجاح {wr:.0f}% | PnL {stats['pnl']:+.2f}%")
        
        # أسباب الخروج
        exit_reasons = {}
        for t in trades:
            reason = t['exit_reason']
            if reason not in exit_reasons:
                exit_reasons[reason] = {'count': 0, 'pnl': 0, 'wins': 0}
            exit_reasons[reason]['count'] += 1
            exit_reasons[reason]['pnl'] += t['pnl_pct']
            if t['is_win']:
                exit_reasons[reason]['wins'] += 1
        
        logger.info(f"\n   أسباب الخروج:")
        for reason, stats in sorted(exit_reasons.items(), key=lambda x: x[1]['count'], reverse=True):
            wr = (stats['wins'] / stats['count']) * 100 if stats['count'] else 0
            logger.info(f"      {reason}: {stats['count']} | نجاح {wr:.0f}% | PnL {stats['pnl']:+.2f}%")
        
        logger.info("")
    
    def run_full_test(self):
        """اختبار شامل"""
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT']
        
        logger.info("\n🚀 النظام المعرفي الفعلي - اختبار شامل")
        logger.info("=" * 80)
        logger.info(f"النمط: {self.timeframe_mode}")
        logger.info(f"Execution: {self.execution_tf} | Confirmation: {self.confirmation_tf}")
        logger.info("=" * 80)
        
        for symbol in symbols:
            self.run_backtest(symbol)
        
        self._final_comparison()
    
    def _final_comparison(self):
        """مقارنة نهائية"""
        logger.info(f"\n{'='*80}")
        logger.info("📊 المقارنة النهائية")
        logger.info(f"{'='*80}\n")
        
        all_trades = []
        for symbol, trades in self.results.items():
            all_trades.extend(trades)
        
        if not all_trades:
            logger.warning("لا توجد صفقات!")
            return
        
        total = len(all_trades)
        wins = len([t for t in all_trades if t['is_win']])
        win_rate = wins / total * 100
        total_pnl = sum(t['pnl_pct'] for t in all_trades)
        avg_hold = np.mean([t['hold_hours'] for t in all_trades])
        
        logger.info(f"إجمالي الصفقات: {total}")
        logger.info(f"معدل النجاح: {win_rate:.1f}%")
        logger.info(f"الربح الإجمالي: {total_pnl:+.2f}%")
        logger.info(f"متوسط المدة: {avg_hold:.1f} ساعة ({avg_hold/24:.1f} يوم)")
        
        # حسب نوع العملة
        by_asset = {}
        for t in all_trades:
            asset = t['asset_type']
            if asset not in by_asset:
                by_asset[asset] = {'count': 0, 'wins': 0, 'pnl': 0}
            by_asset[asset]['count'] += 1
            by_asset[asset]['pnl'] += t['pnl_pct']
            if t['is_win']:
                by_asset[asset]['wins'] += 1
        
        if by_asset:
            logger.info(f"\nحسب نوع العملة:")
            for asset, stats in by_asset.items():
                wr = (stats['wins'] / stats['count']) * 100 if stats['count'] else 0
                logger.info(f"  {asset}: {stats['count']} | نجاح {wr:.0f}% | PnL {stats['pnl']:+.2f}%")
        
        # حسب حالة السوق
        by_state = {}
        for t in all_trades:
            state = t['market_state']
            if state not in by_state:
                by_state[state] = {'count': 0, 'wins': 0, 'pnl': 0}
            by_state[state]['count'] += 1
            by_state[state]['pnl'] += t['pnl_pct']
            if t['is_win']:
                by_state[state]['wins'] += 1
        
        if by_state:
            logger.info(f"\nحسب حالة السوق:")
            for state, stats in by_state.items():
                wr = (stats['wins'] / stats['count']) * 100 if stats['count'] else 0
                logger.info(f"  {state}: {stats['count']} | نجاح {wr:.0f}% | PnL {stats['pnl']:+.2f}%")
        
        logger.info(f"\n{'='*80}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Real Cognitive System Test')
    parser.add_argument('--mode', type=str, default='4h_1h',
                        choices=['4h_1h', '1h_15m'],
                        help='Timeframe mode: 4h_1h (Doctrine) or 1h_15m (Fast)')
    args = parser.parse_args()
    
    tester = RealCognitiveSystemTester(timeframe_mode=args.mode)
    tester.run_full_test()
