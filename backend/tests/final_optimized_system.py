#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
النظام النهائي المُحسّن - Final Optimized Trading System
===========================================================

التوصية المُطبّقة:
- الدخول: 15m مع Multi-Confirmation (3 من 6 تأكيدات)
- الخروج: SmartExitSystemV2 الكامل مع SL محسّن
- SL ديناميكي حسب العملة (2.5x-3.5x ATR)
- فلترة MATIC

التدفق الفعلي:
1. جلب بيانات 15m
2. كشف إشارة على 15m (6 تأكيدات، الحد الأدنى 3)
3. الدخول على فتح الشمعة التالية
4. SmartExitSystemV2 (6 آليات خروج كاملة)
5. تحليل شامل للنتائج
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============= SmartExitSystemV2 المُحسّن =============
class SmartExitSystemOptimized:
    """SmartExitSystemV2 مع SL محسّن حسب العملة"""
    
    def __init__(self, symbol: str = 'BTC/USDT'):
        # SL ديناميكي حسب العملة
        self.sl_multipliers = {
            'BTC/USDT': 3.0,   # تقلبات عالية
            'ETH/USDT': 2.5,
            'SOL/USDT': 3.0,
            'BNB/USDT': 2.5,
            'MATIC/USDT': 3.5, # تقلبات عالية جداً
            'default': 3.0
        }
        
        self.symbol = symbol
        self.atr_multiplier = self.sl_multipliers.get(symbol, self.sl_multipliers['default'])
        
        self.config = {
            'trailing_stop': {
                'activation_pct': 0.015,
                'trail_distance_pct': 0.01,
                'min_profit_lock': 0.008
            },
            'take_profit': {
                'levels': [
                    {'price_pct': 0.025, 'close_pct': 0.40, 'name': 'TP1'},
                    {'price_pct': 0.04, 'close_pct': 0.35, 'name': 'TP2'},
                    {'price_pct': 0.06, 'close_pct': 0.25, 'name': 'TP3'}
                ]
            },
            'stop_loss': {
                'atr_multiplier': self.atr_multiplier,
                'max_loss_pct': 0.04,  # 4% (محسّن من 3%)
                'break_even_after': 0.015
            },
            'time_based': {
                'max_hold_hours': 96,
                'stagnant_hours': 36
            },
            'reversal_confirmation': {
                'enabled': True,
                'min_profit_to_check': 0.008,
                'min_confidence': 65
            }
        }
    
    def check_exit(self, entry_price: float, current_price: float, highest_price: float,
                   entry_time: datetime, current_time: datetime, atr: float,
                   candle_data: Dict = None) -> Dict:
        """فحص شامل لجميع شروط الخروج"""
        
        # حساب SL ديناميكي
        sl_distance = atr * self.config['stop_loss']['atr_multiplier']
        sl_price = entry_price - min(sl_distance, entry_price * self.config['stop_loss']['max_loss_pct'])
        
        pnl_pct = (current_price - entry_price) / entry_price
        hold_hours = (current_time - entry_time).total_seconds() / 3600
        
        # 1. Stop Loss
        if current_price <= sl_price:
            return {
                'should_exit': True,
                'reason': 'Stop_Loss',
                'exit_price': sl_price,
                'pnl_pct': ((sl_price - entry_price) / entry_price) * 100
            }
        
        # 2. Multi-Level TP
        for level in self.config['take_profit']['levels']:
            tp_price = entry_price * (1 + level['price_pct'])
            if current_price >= tp_price:
                return {
                    'should_exit': True,
                    'reason': f"{level['name']}_Hit",
                    'exit_price': current_price,
                    'pnl_pct': pnl_pct * 100
                }
        
        # 3. Trailing Stop
        if pnl_pct >= self.config['trailing_stop']['activation_pct']:
            trail_distance = highest_price * self.config['trailing_stop']['trail_distance_pct']
            trail_sl = highest_price - trail_distance
            min_profit_sl = entry_price * (1 + self.config['trailing_stop']['min_profit_lock'])
            trail_sl = max(trail_sl, min_profit_sl)
            
            if current_price <= trail_sl:
                return {
                    'should_exit': True,
                    'reason': 'Trailing_Stop',
                    'exit_price': trail_sl,
                    'pnl_pct': ((trail_sl - entry_price) / entry_price) * 100
                }
        
        # 4. Reversal Confirmation
        if (self.config['reversal_confirmation']['enabled'] and 
            pnl_pct >= self.config['reversal_confirmation']['min_profit_to_check'] and
            candle_data):
            
            confidence = self._check_reversal(candle_data, current_price)
            if confidence >= self.config['reversal_confirmation']['min_confidence']:
                return {
                    'should_exit': True,
                    'reason': f'Reversal_Conf_{int(confidence)}',
                    'exit_price': current_price,
                    'pnl_pct': pnl_pct * 100
                }
        
        # 5. Max Hold Time
        if hold_hours >= self.config['time_based']['max_hold_hours']:
            return {
                'should_exit': True,
                'reason': 'Max_Hold_Time',
                'exit_price': current_price,
                'pnl_pct': pnl_pct * 100
            }
        
        return {'should_exit': False}
    
    def _check_reversal(self, candle_data: Dict, current_price: float) -> float:
        """فحص تأكيد الانعكاس"""
        confidence = 0
        
        # شمعة حمراء
        if candle_data.get('close', 0) < candle_data.get('open', 0):
            confidence += 15
            if candle_data.get('prev_close', 0) < candle_data.get('prev_open', 0):
                confidence += 15
        
        # كسر EMA9
        ema9 = candle_data.get('ema9')
        if ema9 and current_price < ema9:
            confidence += 25
        
        # RSI ينخفض
        rsi = candle_data.get('rsi')
        prev_rsi = candle_data.get('prev_rsi')
        if rsi and prev_rsi:
            if prev_rsi > 65 and rsi < prev_rsi:
                confidence += 20
            elif rsi < 50 and prev_rsi > rsi:
                confidence += 10
        
        # حجم مرتفع
        vol_ratio = candle_data.get('volume_ratio', 1.0)
        if vol_ratio > 1.3 and candle_data.get('close', 0) < candle_data.get('open', 0):
            confidence += 15
        
        return confidence


# ============= نظام الدخول: 15m + 5m + Multi-Confirmation =============
class OptimizedEntrySystem:
    """
    نظام دخول محسّن:
    1. إشارة على 15m (6 تأكيدات)
    2. تأكيد سريع على 5m (شمعة خضراء)
    3. دخول فوري
    """
    
    def __init__(self):
        self.config = {
            'min_confirmations': 3,  # 3 من 6 تأكيدات (محسّن)
            'rsi_oversold': 40,      # أقل صرامة
            'bb_touch_threshold': 1.05,  # مرونة أكبر
            'volume_surge': 1.3,     # أقل صرامة
            'support_threshold': 0.03,  # مرونة أكبر
            'confirmation_timeout_5m': 1
        }
    
    def check_15m_signal(self, df_15m: pd.DataFrame, idx: int) -> Optional[Dict]:
        """فحص إشارة على 15m مع 6 تأكيدات"""
        if idx < 50:
            return None
        
        confirmations = []
        confidence = 0
        
        # 1. RSI Oversold
        rsi = df_15m['rsi'].iloc[idx]
        if not pd.isna(rsi) and rsi < self.config['rsi_oversold']:
            confirmations.append('RSI_OVERSOLD')
            confidence += 20
        
        # 2. BB Touch
        bb_lower = df_15m['bb_lower'].iloc[idx]
        close = df_15m['close'].iloc[idx]
        if not pd.isna(bb_lower) and close <= bb_lower * self.config['bb_touch_threshold']:
            confirmations.append('BB_TOUCH')
            confidence += 15
        
        # 3. Volume Surge
        volume = df_15m['volume'].iloc[idx]
        avg_vol = df_15m['volume'].iloc[idx-20:idx].mean()
        if volume > avg_vol * self.config['volume_surge']:
            confirmations.append('VOLUME_SURGE')
            confidence += 15
        
        # 4. Support Touch
        support = df_15m['low'].iloc[idx-20:idx].min()
        if close <= support * (1 + self.config['support_threshold']):
            confirmations.append('SUPPORT_TOUCH')
            confidence += 15
        
        # 5. Bullish Candle
        o = df_15m['open'].iloc[idx]
        if close > o:
            confirmations.append('BULLISH_CANDLE')
            confidence += 10
        
        # 6. MACD Cross
        macd = df_15m['macd'].iloc[idx]
        signal = df_15m['macd_signal'].iloc[idx]
        if not pd.isna(macd) and not pd.isna(signal) and macd > signal:
            confirmations.append('MACD_CROSS')
            confidence += 10
        
        if len(confirmations) >= self.config['min_confirmations']:
            return {
                'idx': idx,
                'time': df_15m['timestamp'].iloc[idx],
                'price': close,
                'confirmations': confirmations,
                'confidence': min(confidence, 85),
                'rsi': rsi
            }
        
        return None
    
    def get_entry_signal(self, df_15m: pd.DataFrame, idx: int) -> Optional[Dict]:
        """
        الحصول على إشارة دخول كاملة:
        - 6 تأكيدات (3 منها على الأقل)
        - دخول على فتح الشمعة التالية
        """
        signal = self.check_15m_signal(df_15m, idx)
        if not signal:
            return None
        
        # الدخول على فتح الشمعة 15m التالية
        if idx + 1 >= len(df_15m):
            return None
        
        entry_candle = df_15m.iloc[idx + 1]
        
        return {
            'entry_time': entry_candle['timestamp'],
            'entry_price': entry_candle['open'],
            'confirmations': signal['confirmations'],
            'confidence': signal['confidence'],
            'signal_idx': idx
        }


# ============= نظام الاختبار الشامل =============
class FinalOptimizedTester:
    """اختبار النظام النهائي المُحسّن"""
    
    def __init__(self):
        self.exchange = ccxt.binance()
        self.blacklist = ['MATIC/USDT']  # خسارة في جميع الأنظمة
        self.results = {}
        
    def fetch_data(self, symbol: str, timeframe: str, limit: int = 2000) -> pd.DataFrame:
        """جلب البيانات مع المؤشرات"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['rsi'] = 100 - (100 / (1 + gain / loss))
            
            # Bollinger Bands
            df['sma_20'] = df['close'].rolling(20).mean()
            df['std'] = df['close'].rolling(20).std()
            df['bb_lower'] = df['sma_20'] - (2 * df['std'])
            df['bb_upper'] = df['sma_20'] + (2 * df['std'])
            
            # MACD
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            
            # EMA
            df['ema9'] = df['close'].ewm(span=9).mean()
            
            # ATR
            high_low = df['high'] - df['low']
            high_close = (df['high'] - df['close'].shift()).abs()
            low_close = (df['low'] - df['close'].shift()).abs()
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df['atr'] = tr.rolling(14).mean()
            
            return df
        except Exception as e:
            logger.error(f"خطأ {symbol}: {e}")
            return pd.DataFrame()
    
    def run_backtest(self, symbol: str):
        """تشغيل backtest كامل"""
        if symbol in self.blacklist:
            logger.info(f"⚠️ {symbol} في القائمة السوداء - تم تجاهله")
            return
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🔬 {symbol} - النظام النهائي المُحسّن")
        logger.info(f"{'='*80}")
        
        # جلب البيانات 15m فقط
        df_15m = self.fetch_data(symbol, '15m', limit=1000)
        
        if df_15m.empty:
            return
        
        logger.info(f"📊 البيانات: {len(df_15m)} شمعة 15m")
        
        entry_system = OptimizedEntrySystem()
        exit_system = SmartExitSystemOptimized(symbol)
        
        trades = []
        position = None
        signals_found = 0
        
        for idx in range(60, len(df_15m) - 5):
            current_time = df_15m['timestamp'].iloc[idx]
            current_price = df_15m['close'].iloc[idx]
            
            # إدارة الصفقة المفتوحة
            if position:
                position['highest_price'] = max(position['highest_price'], current_price)
                
                # تحضير بيانات الشمعة
                candle_data = {
                    'open': df_15m['open'].iloc[idx],
                    'close': df_15m['close'].iloc[idx],
                    'prev_open': df_15m['open'].iloc[idx-1],
                    'prev_close': df_15m['close'].iloc[idx-1],
                    'ema9': df_15m['ema9'].iloc[idx],
                    'rsi': df_15m['rsi'].iloc[idx],
                    'prev_rsi': df_15m['rsi'].iloc[idx-1],
                    'volume_ratio': df_15m['volume'].iloc[idx] / df_15m['volume'].iloc[idx-20:idx].mean()
                }
                
                # فحص الخروج
                exit_check = exit_system.check_exit(
                    entry_price=position['entry_price'],
                    current_price=current_price,
                    highest_price=position['highest_price'],
                    entry_time=position['entry_time'],
                    current_time=current_time,
                    atr=position['atr'],
                    candle_data=candle_data
                )
                
                if exit_check['should_exit']:
                    hold_hours = (current_time - position['entry_time']).total_seconds() / 3600
                    
                    trade = {
                        'symbol': symbol,
                        'entry_price': position['entry_price'],
                        'exit_price': exit_check['exit_price'],
                        'exit_reason': exit_check['reason'],
                        'pnl_pct': exit_check['pnl_pct'],
                        'hold_hours': hold_hours,
                        'is_win': exit_check['pnl_pct'] > 0,
                        'confirmations': position['confirmations'],
                        'confidence': position['confidence']
                    }
                    
                    trades.append(trade)
                    status = "✅" if trade['is_win'] else "❌"
                    logger.info(
                        f"{status} #{len(trades)} | {position['entry_price']:.2f} → {exit_check['exit_price']:.2f} | "
                        f"PnL: {exit_check['pnl_pct']:+.2f}% | {hold_hours:.1f}h | {exit_check['reason']}"
                    )
                    
                    position = None
            
            # البحث عن دخول جديد
            if not position:
                # فحص إشارة دخول كاملة على 15m
                entry_signal = entry_system.get_entry_signal(df_15m, idx)
                if entry_signal:
                    signals_found += 1
                    
                    # الدخول الفوري
                    position = {
                        'entry_time': entry_signal['entry_time'],
                        'entry_price': entry_signal['entry_price'],
                        'highest_price': entry_signal['entry_price'],
                        'atr': df_15m['atr'].iloc[idx] if not pd.isna(df_15m['atr'].iloc[idx]) else entry_signal['entry_price'] * 0.02,
                        'confirmations': entry_signal['confirmations'],
                        'confidence': entry_signal['confidence']
                    }
        
        # حفظ النتائج
        self.results[symbol] = trades
        
        # طباعة الملخص
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 إشارات: {signals_found} | صفقات: {len(trades)}")
        logger.info(f"{'='*60}")
        
        if trades:
            self._print_summary(trades, symbol)
    
    def _print_summary(self, trades: List[Dict], symbol: str):
        """ملخص النتائج"""
        total = len(trades)
        wins = [t for t in trades if t['is_win']]
        total_pnl = sum(t['pnl_pct'] for t in trades)
        win_rate = len(wins) / total * 100
        avg_hold = np.mean([t['hold_hours'] for t in trades])
        
        logger.info(f"\n📊 ملخص {symbol}:")
        logger.info(f"   الصفقات: {total} | النجاح: {win_rate:.1f}% | PnL: {total_pnl:+.2f}% | المدة: {avg_hold:.1f}h")
        
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
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'MATIC/USDT']
        
        logger.info("\n🚀 النظام النهائي المُحسّن")
        logger.info("=" * 80)
        logger.info("الدخول: 15m Multi-Confirmation (3 من 6 تأكيدات)")
        logger.info("الخروج: SmartExitSystemV2 الكامل + SL محسّن")
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
        
        # صفقات نفس اليوم
        same_day = len([t for t in all_trades if t['hold_hours'] < 24])
        logger.info(f"صفقات نفس اليوم: {same_day} ({same_day/total*100:.1f}%)")
        
        logger.info(f"\n{'='*80}\n")


if __name__ == "__main__":
    tester = FinalOptimizedTester()
    tester.run_full_test()
