#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simplified Backtesting - MTF System
اختبار خلفي مبسط مع نتائج تفصيلية

رأس المال: 1000 USDT
حجم الصفقة: 100 USDT
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SimpleBacktest:
    """اختبار خلفي مبسط"""
    
    def __init__(self):
        self.initial_capital = 1000
        self.position_size = 100
        self.current_capital = 1000
        self.trades = []
        
    def fetch_data(self, symbol, timeframe='1h', limit=500):
        """جلب البيانات"""
        try:
            exchange = ccxt.binance()
            time.sleep(0.5)  # تجنب rate limiting
            
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            if not ohlcv:
                return pd.DataFrame()
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # SMA
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            
            logger.info(f"✅ {symbol}: {len(df)} شموع")
            return df
            
        except Exception as e:
            logger.error(f"خطأ في جلب {symbol}: {e}")
            return pd.DataFrame()
    
    def find_entry_signals(self, df):
        """إيجاد إشارات الدخول (Bullish Reversal)"""
        signals = []
        
        for i in range(50, len(df) - 50):  # ترك مساحة
            # شروط الدخول البسيطة
            rsi = df['rsi'].iloc[i]
            close = df['close'].iloc[i]
            sma_20 = df['sma_20'].iloc[i]
            sma_50 = df['sma_50'].iloc[i]
            
            # RSI oversold + price below SMA
            if rsi < 35 and close < sma_20:
                # Hammer pattern check
                o = df['open'].iloc[i]
                h = df['high'].iloc[i]
                l = df['low'].iloc[i]
                c = df['close'].iloc[i]
                
                body = abs(c - o)
                lower_wick = min(o, c) - l
                upper_wick = h - max(o, c)
                
                if body > 0 and lower_wick > body * 1.2 and c > o:
                    signals.append({
                        'index': i,
                        'price': close,
                        'rsi': rsi,
                        'reason': 'RSI oversold + Hammer',
                        'confidence': 60 if lower_wick > body * 2 else 50
                    })
        
        return signals
    
    def simulate_trades(self, symbol, df):
        """محاكاة الصفقات"""
        entry_signals = self.find_entry_signals(df)
        
        if not entry_signals:
            logger.warning(f"⚠️ {symbol}: لا توجد إشارات دخول")
            return []
        
        logger.info(f"📊 {symbol}: {len(entry_signals)} إشارات دخول")
        
        symbol_trades = []
        
        for signal in entry_signals:
            entry_idx = signal['index']
            entry_price = signal['price']
            
            # Stop Loss & Take Profit
            stop_loss = entry_price * 0.97  # -3%
            take_profit = entry_price * 1.06  # +6% (R:R = 2:1)
            
            # محاكاة الصفقة
            exit_idx = None
            exit_price = None
            exit_reason = None
            
            max_hold = min(entry_idx + 72, len(df) - 1)  # 3 أيام
            
            for i in range(entry_idx + 1, max_hold):
                high = df['high'].iloc[i]
                low = df['low'].iloc[i]
                
                # Stop Loss hit
                if low <= stop_loss:
                    exit_idx = i
                    exit_price = stop_loss
                    exit_reason = 'Stop Loss'
                    break
                
                # Take Profit hit
                if high >= take_profit:
                    exit_idx = i
                    exit_price = take_profit
                    exit_reason = 'Take Profit'
                    break
            
            # إغلاق عند نهاية الفترة
            if exit_idx is None:
                exit_idx = max_hold
                exit_price = df['close'].iloc[max_hold]
                exit_reason = 'Max Hold Time'
            
            # حساب الربح/الخسارة
            pnl = exit_price - entry_price
            pnl_pct = (pnl / entry_price) * 100
            pnl_usd = pnl_pct * (self.position_size / 100)
            
            trade = {
                'symbol': symbol,
                'entry_time': df['timestamp'].iloc[entry_idx],
                'entry_price': entry_price,
                'exit_time': df['timestamp'].iloc[exit_idx],
                'exit_price': exit_price,
                'exit_reason': exit_reason,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'pnl_pct': pnl_pct,
                'pnl_usd': pnl_usd,
                'hold_hours': exit_idx - entry_idx,
                'confidence': signal['confidence'],
                'entry_reason': signal['reason']
            }
            
            symbol_trades.append(trade)
            self.current_capital += pnl_usd
        
        return symbol_trades
    
    def run(self):
        """تشغيل الاختبار"""
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 بدء الاختبار الخلفي المبسط")
        logger.info(f"{'='*80}")
        logger.info(f"💰 رأس المال: {self.initial_capital} USDT")
        logger.info(f"📊 حجم الصفقة: {self.position_size} USDT")
        logger.info(f"🎯 العملات: {', '.join(symbols)}")
        
        all_trades = []
        
        for symbol in symbols:
            logger.info(f"\n{'='*80}")
            logger.info(f"📈 تحليل {symbol}")
            logger.info(f"{'='*80}")
            
            df = self.fetch_data(symbol)
            
            if df.empty or len(df) < 100:
                logger.error(f"❌ {symbol}: بيانات غير كافية")
                continue
            
            trades = self.simulate_trades(symbol, df)
            all_trades.extend(trades)
        
        self.trades = all_trades
        self.print_report()
    
    def print_report(self):
        """طباعة التقرير"""
        if not self.trades:
            logger.warning("❌ لا توجد صفقات!")
            return
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 التقرير النهائي")
        logger.info(f"{'='*80}")
        
        # الإحصائيات العامة
        total_trades = len(self.trades)
        winning = [t for t in self.trades if t['pnl_usd'] > 0]
        losing = [t for t in self.trades if t['pnl_usd'] <= 0]
        
        total_pnl = sum(t['pnl_usd'] for t in self.trades)
        total_pnl_pct = (total_pnl / self.initial_capital) * 100
        
        win_rate = (len(winning) / total_trades) * 100 if total_trades > 0 else 0
        
        logger.info(f"\n💰 رأس المال:")
        logger.info(f"   الأولي: {self.initial_capital:.2f} USDT")
        logger.info(f"   النهائي: {self.current_capital:.2f} USDT")
        logger.info(f"   الربح/الخسارة: {total_pnl:.2f} USDT ({total_pnl_pct:.2f}%)")
        
        logger.info(f"\n📈 الإحصائيات:")
        logger.info(f"   إجمالي الصفقات: {total_trades}")
        logger.info(f"   صفقات رابحة: {len(winning)} ({win_rate:.1f}%)")
        logger.info(f"   صفقات خاسرة: {len(losing)} ({100-win_rate:.1f}%)")
        
        if winning:
            avg_win = np.mean([t['pnl_usd'] for t in winning])
            logger.info(f"   متوسط الربح: {avg_win:.2f} USDT")
        
        if losing:
            avg_loss = np.mean([t['pnl_usd'] for t in losing])
            logger.info(f"   متوسط الخسارة: {avg_loss:.2f} USDT")
        
        # تفاصيل كل صفقة
        logger.info(f"\n📋 تفاصيل الصفقات:")
        logger.info(f"{'='*80}")
        
        for i, trade in enumerate(self.trades, 1):
            status = "✅ ربح" if trade['pnl_usd'] > 0 else "❌ خسارة"
            
            logger.info(f"\n🔹 صفقة #{i} - {trade['symbol']}")
            logger.info(f"   الحالة: {status}")
            logger.info(f"   الدخول: {trade['entry_time'].strftime('%Y-%m-%d %H:%M')} @ {trade['entry_price']:.4f}")
            logger.info(f"   السبب: {trade['entry_reason']} (ثقة {trade['confidence']}%)")
            logger.info(f"   الخروج: {trade['exit_time'].strftime('%Y-%m-%d %H:%M')} @ {trade['exit_price']:.4f}")
            logger.info(f"   السبب: {trade['exit_reason']}")
            logger.info(f"   الربح/الخسارة: {trade['pnl_usd']:.2f} USDT ({trade['pnl_pct']:.2f}%)")
            logger.info(f"   Stop Loss: {trade['stop_loss']:.4f} | Take Profit: {trade['take_profit']:.4f}")
            logger.info(f"   المدة: {trade['hold_hours']} ساعة")
        
        # أفضل وأسوأ صفقة
        best = max(self.trades, key=lambda x: x['pnl_usd'])
        worst = min(self.trades, key=lambda x: x['pnl_usd'])
        
        logger.info(f"\n🏆 أفضل صفقة:")
        logger.info(f"   {best['symbol']}: {best['pnl_usd']:.2f} USDT ({best['pnl_pct']:.2f}%)")
        logger.info(f"   {best['entry_time'].strftime('%Y-%m-%d')} → {best['exit_time'].strftime('%Y-%m-%d')}")
        
        logger.info(f"\n💀 أسوأ صفقة:")
        logger.info(f"   {worst['symbol']}: {worst['pnl_usd']:.2f} USDT ({worst['pnl_pct']:.2f}%)")
        logger.info(f"   {worst['entry_time'].strftime('%Y-%m-%d')} → {worst['exit_time'].strftime('%Y-%m-%d')}")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ اكتمل الاختبار!")
        logger.info(f"{'='*80}")


if __name__ == "__main__":
    backtest = SimpleBacktest()
    backtest.run()
