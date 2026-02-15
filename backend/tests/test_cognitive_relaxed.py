#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cognitive System Test - Relaxed Mode
====================================
نسخة معدّلة من النظام المعرفي مع معايير أخف للحصول على نتائج فعلية

التعديلات:
1. تخفيف معايير ReasoningEngine
2. قبول القرارات بثقة ≥ 70%
3. تجاوز فحص "ثقة الاستراتيجية"
4. Timeframe: 1H + 15m (للتداول السريع)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Dict, List

from cognitive import get_cognitive_trading_engine
from cognitive.reasoning_engine import TradeDecision
from trade_management.smart_exit_system_v2 import SmartExitSystemV2

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CognitiveRelaxedTester:
    """اختبار النظام المعرفي - معايير مخففة"""
    
    def __init__(self):
        self.exchange = ccxt.binance()
        self.cognitive_engine = get_cognitive_trading_engine()
        self.exit_system = SmartExitSystemV2()
        self.results = {}
        
        # معايير مخففة
        self.min_confidence = 70  # بدلاً من 80-90
        self.allow_wait_as_trade = True  # قبول "wait" كإشارة تداول
        
        logger.info("🚀 النظام المعرفي - معايير مخففة")
        logger.info("   Execution: 1H | Confirmation: 15m")
    
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """جلب البيانات"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # المؤشرات
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['rsi'] = 100 - (100 / (1 + gain / loss))
            
            df['ema_9'] = df['close'].ewm(span=9).mean()
            df['ema_20'] = df['close'].ewm(span=20).mean()
            
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            
            high_low = df['high'] - df['low']
            high_close = (df['high'] - df['close'].shift()).abs()
            low_close = (df['low'] - df['close'].shift()).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['atr'] = tr.rolling(14).mean()
            
            return df
        except Exception as e:
            logger.error(f"❌ {symbol} {timeframe}: {e}")
            return pd.DataFrame()
    
    def run_backtest(self, symbol: str):
        """backtest كامل"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔬 {symbol}")
        logger.info(f"{'='*80}")
        
        df_1h = self.fetch_ohlcv(symbol, '1h', limit=500)
        df_15m = self.fetch_ohlcv(symbol, '15m', limit=1000)
        
        if df_1h.empty or df_15m.empty:
            return
        
        logger.info(f"📊 1H={len(df_1h)} | 15m={len(df_15m)}")
        
        trades = []
        position = None
        signals = 0
        executed = 0
        
        for idx in range(100, len(df_1h) - 5):
            current_time = df_1h['timestamp'].iloc[idx]
            current_price = df_1h['close'].iloc[idx]
            
            # إدارة الصفقة
            if position:
                position['highest_price'] = max(position['highest_price'], current_price)
                
                candle = {
                    'open': df_1h['open'].iloc[idx],
                    'high': df_1h['high'].iloc[idx],
                    'low': df_1h['low'].iloc[idx],
                    'close': current_price,
                    'timestamp': current_time,
                    'rsi': df_1h['rsi'].iloc[idx],
                    'macd': df_1h['macd'].iloc[idx],
                    'macd_signal': df_1h['macd_signal'].iloc[idx],
                    'ema9': df_1h['ema_9'].iloc[idx],
                }
                
                exit_check = self.exit_system.check_exit_conditions(
                    position['id'], current_price, current_time, candle
                )
                
                if exit_check.get('should_exit'):
                    hold_h = (current_time - position['entry_time']).total_seconds() / 3600
                    pnl = ((exit_check['exit_price'] - position['entry_price']) / position['entry_price']) * 100
                    
                    trade = {
                        'entry_price': position['entry_price'],
                        'exit_price': exit_check['exit_price'],
                        'exit_reason': exit_check['reason'],
                        'pnl_pct': pnl,
                        'hold_hours': hold_h,
                        'is_win': pnl > 0,
                        'strategy': position['strategy']
                    }
                    
                    trades.append(trade)
                    status = "✅" if trade['is_win'] else "❌"
                    logger.info(
                        f"{status} #{len(trades)} | {position['entry_price']:.2f} → {exit_check['exit_price']:.2f} | "
                        f"{pnl:+.2f}% | {hold_h:.1f}h | {exit_check['reason']}"
                    )
                    
                    position = None
            
            # بحث عن دخول
            if not position:
                df_1h_cur = df_1h.iloc[:idx+1]
                df_15m_cur = df_15m[df_15m['timestamp'] <= current_time]
                
                if len(df_15m_cur) < 50:
                    continue
                
                try:
                    analysis = self.cognitive_engine.analyze(
                        symbol=symbol,
                        df=df_1h_cur,
                        volume_24h_usd=None,
                        additional_context={'df_15m': df_15m_cur}
                    )
                    
                    signals += 1
                    
                    # معايير مخففة:
                    # 1. قبول EXECUTE مباشرة
                    # 2. قبول WAIT إذا كانت الثقة ≥ 70%
                    should_trade = False
                    
                    if analysis.decision == TradeDecision.EXECUTE:
                        should_trade = True
                    elif analysis.decision == TradeDecision.WAIT and self.allow_wait_as_trade:
                        if analysis.confidence >= self.min_confidence:
                            should_trade = True
                    
                    if should_trade and analysis.entry_price:
                        pos_id = f"{symbol}_{current_time.strftime('%Y%m%d_%H%M')}"
                        
                        self.exit_system.open_position(
                            position_id=pos_id,
                            symbol=symbol,
                            entry_price=analysis.entry_price,
                            timestamp=current_time,
                            position_size=100.0,
                            stop_loss_price=analysis.stop_loss_price,
                            take_profit_price=analysis.take_profit_price
                        )
                        
                        position = {
                            'id': pos_id,
                            'entry_time': current_time,
                            'entry_price': analysis.entry_price,
                            'highest_price': analysis.entry_price,
                            'strategy': analysis.strategy.strategy.value
                        }
                        
                        executed += 1
                        logger.info(
                            f"🎯 دخول #{executed} | {analysis.entry_price:.2f} | "
                            f"ثقة {analysis.confidence:.0f}% | {analysis.decision.value}"
                        )
                        
                except Exception as e:
                    continue
        
        # إغلاق الصفقة المفتوحة
        if position:
            pnl = ((df_1h['close'].iloc[-1] - position['entry_price']) / position['entry_price']) * 100
            trades.append({
                'entry_price': position['entry_price'],
                'exit_price': df_1h['close'].iloc[-1],
                'exit_reason': 'End_Of_Data',
                'pnl_pct': pnl,
                'hold_hours': 24.0,
                'is_win': pnl > 0,
                'strategy': position['strategy']
            })
        
        self.results[symbol] = trades
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 إشارات: {signals} | منفذة: {executed} | صفقات: {len(trades)}")
        logger.info(f"{'='*60}")
        
        if trades:
            self._summary(trades, symbol)
    
    def _summary(self, trades: List[Dict], symbol: str):
        """ملخص"""
        total = len(trades)
        wins = [t for t in trades if t['is_win']]
        pnl = sum(t['pnl_pct'] for t in trades)
        wr = len(wins) / total * 100 if total > 0 else 0
        
        logger.info(f"\n{symbol}: {total} صفقة | نجاح {wr:.1f}% | PnL {pnl:+.2f}%")
        
        # أسباب الخروج
        exits = {}
        for t in trades:
            r = t['exit_reason']
            if r not in exits:
                exits[r] = {'count': 0, 'pnl': 0, 'wins': 0}
            exits[r]['count'] += 1
            exits[r]['pnl'] += t['pnl_pct']
            if t['is_win']:
                exits[r]['wins'] += 1
        
        logger.info("\nالخروج:")
        for reason, stats in sorted(exits.items(), key=lambda x: x[1]['count'], reverse=True):
            wr2 = (stats['wins'] / stats['count']) * 100 if stats['count'] else 0
            logger.info(f"  {reason}: {stats['count']} | نجاح {wr2:.0f}% | {stats['pnl']:+.2f}%")
    
    def run_full_test(self):
        """اختبار شامل"""
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT']
        
        logger.info("\n🚀 النظام المعرفي - معايير مخففة")
        logger.info("=" * 80)
        
        for symbol in symbols:
            self.run_backtest(symbol)
        
        # مقارنة نهائية
        all_trades = []
        for trades in self.results.values():
            all_trades.extend(trades)
        
        if all_trades:
            logger.info(f"\n{'='*80}")
            logger.info("📊 الإجمالي")
            logger.info(f"{'='*80}")
            
            total = len(all_trades)
            wins = len([t for t in all_trades if t['is_win']])
            pnl = sum(t['pnl_pct'] for t in all_trades)
            wr = wins / total * 100
            
            logger.info(f"الصفقات: {total}")
            logger.info(f"النجاح: {wr:.1f}%")
            logger.info(f"الربح: {pnl:+.2f}%")
            logger.info(f"{'='*80}\n")
        else:
            logger.warning("لا توجد صفقات!")


if __name__ == "__main__":
    tester = CognitiveRelaxedTester()
    tester.run_full_test()
