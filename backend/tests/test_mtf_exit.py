#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار MTF Reversal Exit
مقارنة النتائج قبل وبعد تفعيل نظام الخروج عند تأكيد الانعكاس
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class MTFExitTester:
    """اختبار نظام MTF Exit"""
    
    def __init__(self):
        self.initial_capital = 1000
        self.position_size = 100
        self.trades_without_mtf = []
        self.trades_with_mtf = []
        
    def fetch_data(self, symbol, timeframe='1h', limit=500):
        """جلب البيانات"""
        try:
            exchange = ccxt.binance()
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
            
            return df
            
        except Exception as e:
            logger.error(f"خطأ في جلب {symbol}: {e}")
            return pd.DataFrame()
    
    def check_mtf_reversal(self, df_1h, df_15m, entry_idx, current_idx, entry_price, current_price):
        """فحص انعكاس MTF"""
        try:
            # الاستيراد المباشر
            import sys
            import os
            cognitive_path = os.path.join(os.path.dirname(__file__), '..', 'cognitive')
            if cognitive_path not in sys.path:
                sys.path.insert(0, cognitive_path)
            
            from mtf_reversal_confirmation import get_mtf_reversal_confirmation
            
            mtf = get_mtf_reversal_confirmation()
            
            # البيانات حتى current_idx
            df_1h_slice = df_1h.iloc[:current_idx+1].copy()
            df_15m_slice = df_15m.iloc[:(current_idx+1)*4].copy() if len(df_15m) >= (current_idx+1)*4 else df_15m.copy()
            
            if len(df_1h_slice) < 50 or len(df_15m_slice) < 100:
                return {'should_exit': False, 'confidence': 0}
            
            signal = mtf.confirm_bearish_reversal(
                df_1h=df_1h_slice,
                df_15m=df_15m_slice,
                current_price=current_price,
                entry_price=entry_price
            )
            
            # حساب الربح
            pnl_pct = (current_price - entry_price) / entry_price
            
            # عتبة الثقة المتوازنة
            if pnl_pct >= 0.03:
                threshold = 55.0
            elif pnl_pct >= 0.015:
                threshold = 60.0
            else:
                threshold = 65.0
            
            return {
                'should_exit': signal.confidence >= threshold,
                'confidence': signal.confidence,
                'timeframes': len(signal.timeframes_confirmed)
            }
            
        except Exception as e:
            logger.error(f"خطأ في MTF check: {e}")
            return {'should_exit': False, 'confidence': 0}
    
    def simulate_trade(self, symbol, df_1h, df_15m, entry_idx, use_mtf=False):
        """محاكاة صفقة واحدة"""
        entry_price = df_1h['close'].iloc[entry_idx]
        entry_time = df_1h['timestamp'].iloc[entry_idx]
        
        # مستويات الخروج
        stop_loss = entry_price * 0.97  # -3%
        take_profit = entry_price * 1.06  # +6%
        trailing_activation = entry_price * 1.015  # +1.5%
        
        exit_idx = None
        exit_price = None
        exit_reason = None
        trailing_sl = 0
        highest_price = entry_price
        
        max_hold = min(entry_idx + 96, len(df_1h) - 1)  # 96 ساعة
        
        for i in range(entry_idx + 1, max_hold):
            current_price = df_1h['close'].iloc[i]
            high = df_1h['high'].iloc[i]
            low = df_1h['low'].iloc[i]
            
            # تحديث أعلى سعر
            if high > highest_price:
                highest_price = high
            
            # Stop Loss
            if low <= stop_loss:
                exit_idx = i
                exit_price = stop_loss
                exit_reason = 'Stop Loss'
                break
            
            # Take Profit
            if high >= take_profit:
                exit_idx = i
                exit_price = take_profit
                exit_reason = 'Take Profit'
                break
            
            # Trailing Stop
            if current_price >= trailing_activation:
                trail_distance = highest_price * 0.01
                new_trailing = highest_price - trail_distance
                min_profit = entry_price * 1.008
                new_trailing = max(new_trailing, min_profit)
                
                if new_trailing > trailing_sl:
                    trailing_sl = new_trailing
                
                if trailing_sl > 0 and low <= trailing_sl:
                    exit_idx = i
                    exit_price = trailing_sl
                    exit_reason = 'Trailing Stop'
                    break
            
            # MTF Reversal Exit (إذا مفعّل)
            if use_mtf:
                pnl_pct = (current_price - entry_price) / entry_price
                if pnl_pct >= 0.008:  # ربح +0.8% على الأقل
                    mtf_check = self.check_mtf_reversal(
                        df_1h, df_15m, entry_idx, i, entry_price, current_price
                    )
                    
                    if mtf_check['should_exit']:
                        exit_idx = i
                        exit_price = current_price
                        exit_reason = f"MTF Reversal ({mtf_check['confidence']:.0f}%)"
                        break
        
        # إغلاق عند نهاية الفترة
        if exit_idx is None:
            exit_idx = max_hold
            exit_price = df_1h['close'].iloc[max_hold]
            exit_reason = 'Max Hold Time'
        
        # حساب النتائج
        pnl = exit_price - entry_price
        pnl_pct = (pnl / entry_price) * 100
        pnl_usd = pnl_pct * (self.position_size / 100)
        hold_hours = exit_idx - entry_idx
        
        return {
            'symbol': symbol,
            'entry_time': entry_time,
            'entry_price': entry_price,
            'exit_time': df_1h['timestamp'].iloc[exit_idx],
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct,
            'pnl_usd': pnl_usd,
            'hold_hours': hold_hours,
            'highest_price': highest_price
        }
    
    def find_entries(self, df):
        """إيجاد نقاط الدخول"""
        entries = []
        
        for i in range(50, len(df) - 100):
            rsi = df['rsi'].iloc[i]
            close = df['close'].iloc[i]
            sma_20 = df['sma_20'].iloc[i]
            
            if rsi < 35 and close < sma_20:
                o = df['open'].iloc[i]
                h = df['high'].iloc[i]
                l = df['low'].iloc[i]
                c = df['close'].iloc[i]
                
                body = abs(c - o)
                lower_wick = min(o, c) - l
                
                if body > 0 and lower_wick > body * 1.2 and c > o:
                    entries.append(i)
        
        return entries
    
    def run_test(self, symbols=['BTC/USDT', 'ETH/USDT', 'BNB/USDT']):
        """تشغيل الاختبار على عملات متعددة"""
        if isinstance(symbols, str):
            symbols = [symbols]
        
        for symbol in symbols:
            self._test_single_symbol(symbol)
        
        # المقارنة الإجمالية
        self.compare_overall()
    
    def _test_single_symbol(self, symbol='BTC/USDT'):
        """تشغيل الاختبار لعملة واحدة"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔬 اختبار MTF Reversal Exit - {symbol}")
        logger.info(f"{'='*80}")
        
        # جلب البيانات
        df_1h = self.fetch_data(symbol, '1h', limit=500)
        df_15m = self.fetch_data(symbol, '15m', limit=2000)
        
        if df_1h.empty or df_15m.empty:
            logger.error("فشل جلب البيانات")
            return
        
        logger.info(f"📊 البيانات: {len(df_1h)} شمعة (1H), {len(df_15m)} شمعة (15m)")
        
        # إيجاد نقاط الدخول
        entry_points = self.find_entries(df_1h)
        logger.info(f"📍 نقاط دخول: {len(entry_points)}")
        
        if not entry_points:
            logger.warning("لا توجد نقاط دخول!")
            return
        
        # اختبار بدون MTF
        logger.info(f"\n{'='*80}")
        logger.info("🔵 الاختبار 1: بدون MTF Reversal Exit (النظام الحالي)")
        logger.info(f"{'='*80}")
        
        for entry_idx in entry_points[:10]:  # أول 10 صفقات
            trade = self.simulate_trade(symbol, df_1h, df_15m, entry_idx, use_mtf=False)
            self.trades_without_mtf.append(trade)
        
        # اختبار مع MTF
        logger.info(f"\n{'='*80}")
        logger.info("🟢 الاختبار 2: مع MTF Reversal Exit (النظام المحسّن)")
        logger.info(f"{'='*80}")
        
        for entry_idx in entry_points[:10]:
            trade = self.simulate_trade(symbol, df_1h, df_15m, entry_idx, use_mtf=True)
            self.trades_with_mtf.append(trade)
        
        # لا نقارن هنا - سنقارن في النهاية
    
    def compare_results(self):
        """مقارنة النتائج"""
        logger.info(f"\n{'='*80}")
        logger.info("📊 المقارنة والنتائج")
        logger.info(f"{'='*80}")
        
        # بدون MTF
        without_mtf_pnl = sum(t['pnl_usd'] for t in self.trades_without_mtf)
        without_mtf_wins = sum(1 for t in self.trades_without_mtf if t['pnl_usd'] > 0)
        without_mtf_wr = (without_mtf_wins / len(self.trades_without_mtf)) * 100 if self.trades_without_mtf else 0
        without_mtf_avg_hold = np.mean([t['hold_hours'] for t in self.trades_without_mtf]) if self.trades_without_mtf else 0
        
        # مع MTF
        with_mtf_pnl = sum(t['pnl_usd'] for t in self.trades_with_mtf)
        with_mtf_wins = sum(1 for t in self.trades_with_mtf if t['pnl_usd'] > 0)
        with_mtf_wr = (with_mtf_wins / len(self.trades_with_mtf)) * 100 if self.trades_with_mtf else 0
        with_mtf_avg_hold = np.mean([t['hold_hours'] for t in self.trades_with_mtf]) if self.trades_with_mtf else 0
        
        # حساب تأثير MTF
        mtf_exits = sum(1 for t in self.trades_with_mtf if 'MTF' in t['exit_reason'])
        
        logger.info(f"\n🔵 بدون MTF Reversal Exit:")
        logger.info(f"   الربح/الخسارة: {without_mtf_pnl:+.2f} USDT")
        logger.info(f"   معدل النجاح: {without_mtf_wr:.1f}% ({without_mtf_wins}/{len(self.trades_without_mtf)})")
        logger.info(f"   متوسط المدة: {without_mtf_avg_hold:.1f} ساعة")
        
        logger.info(f"\n🟢 مع MTF Reversal Exit:")
        logger.info(f"   الربح/الخسارة: {with_mtf_pnl:+.2f} USDT")
        logger.info(f"   معدل النجاح: {with_mtf_wr:.1f}% ({with_mtf_wins}/{len(self.trades_with_mtf)})")
        logger.info(f"   متوسط المدة: {with_mtf_avg_hold:.1f} ساعة")
        logger.info(f"   خروج MTF: {mtf_exits} صفقة")
        
        # الفرق
        diff_pnl = with_mtf_pnl - without_mtf_pnl
        diff_wr = with_mtf_wr - without_mtf_wr
        diff_hold = with_mtf_avg_hold - without_mtf_avg_hold
        
        logger.info(f"\n{'='*80}")
        logger.info("📈 التحسين:")
        logger.info(f"   الربح/الخسارة: {diff_pnl:+.2f} USDT ({(diff_pnl/abs(without_mtf_pnl)*100) if without_mtf_pnl != 0 else 0:+.1f}%)")
        logger.info(f"   معدل النجاح: {diff_wr:+.1f}%")
        logger.info(f"   متوسط المدة: {diff_hold:+.1f} ساعة")
        
        # التفاصيل
        logger.info(f"\n{'='*80}")
        logger.info("📋 تفاصيل صفقات MTF Exit:")
        logger.info(f"{'='*80}")
        
        for i, trade in enumerate(self.trades_with_mtf, 1):
            if 'MTF' in trade['exit_reason']:
                logger.info(f"\n🔹 صفقة #{i}")
                logger.info(f"   الدخول: {trade['entry_time'].strftime('%Y-%m-%d %H:%M')} @ {trade['entry_price']:.2f}")
                logger.info(f"   الخروج: {trade['exit_time'].strftime('%Y-%m-%d %H:%M')} @ {trade['exit_price']:.2f}")
                logger.info(f"   السبب: {trade['exit_reason']}")
                logger.info(f"   الربح: {trade['pnl_usd']:+.2f} USDT ({trade['pnl_pct']:+.2f}%)")
                logger.info(f"   المدة: {trade['hold_hours']} ساعة")
                logger.info(f"   أعلى سعر: {trade['highest_price']:.2f}")
        
        # التقييم النهائي
        logger.info(f"\n{'='*80}")
        if diff_pnl > 0:
            logger.info("✅ MTF Reversal Exit يحسّن النتائج")
            logger.info(f"   التحسين: +{diff_pnl:.2f} USDT")
        elif diff_pnl < -2:
            logger.info("❌ MTF Reversal Exit يضر بالنتائج")
            logger.info(f"   الانخفاض: {diff_pnl:.2f} USDT")
        else:
            logger.info("⚖️ MTF Reversal Exit محايد")
            logger.info(f"   الفرق: {diff_pnl:.2f} USDT")
        
        logger.info(f"{'='*80}")
    
    def compare_overall(self):
        """مقارنة شاملة لكل العملات"""
        if not self.trades_without_mtf or not self.trades_with_mtf:
            logger.warning("لا توجد بيانات للمقارنة!")
            return
        
        logger.info(f"\n{'='*80}")
        logger.info("📊 المقارنة الشاملة - جميع العملات")
        logger.info(f"{'='*80}")
        
        # بدون MTF
        without_pnl = sum(t['pnl_usd'] for t in self.trades_without_mtf)
        without_wins = sum(1 for t in self.trades_without_mtf if t['pnl_usd'] > 0)
        without_wr = (without_wins / len(self.trades_without_mtf)) * 100
        without_avg_hold = np.mean([t['hold_hours'] for t in self.trades_without_mtf])
        
        # مع MTF
        with_pnl = sum(t['pnl_usd'] for t in self.trades_with_mtf)
        with_wins = sum(1 for t in self.trades_with_mtf if t['pnl_usd'] > 0)
        with_wr = (with_wins / len(self.trades_with_mtf)) * 100
        with_avg_hold = np.mean([t['hold_hours'] for t in self.trades_with_mtf])
        
        # MTF Exits
        mtf_exits = [t for t in self.trades_with_mtf if 'MTF' in t['exit_reason']]
        
        logger.info(f"\n🔵 بدون MTF:")
        logger.info(f"   إجمالي الصفقات: {len(self.trades_without_mtf)}")
        logger.info(f"   الربح/الخسارة: {without_pnl:+.2f} USDT")
        logger.info(f"   معدل النجاح: {without_wr:.1f}%")
        logger.info(f"   متوسط المدة: {without_avg_hold:.1f} ساعة")
        
        logger.info(f"\n🟢 مع MTF:")
        logger.info(f"   إجمالي الصفقات: {len(self.trades_with_mtf)}")
        logger.info(f"   الربح/الخسارة: {with_pnl:+.2f} USDT")
        logger.info(f"   معدل النجاح: {with_wr:.1f}%")
        logger.info(f"   متوسط المدة: {with_avg_hold:.1f} ساعة")
        logger.info(f"   خروج MTF: {len(mtf_exits)} صفقة")
        
        # التحسين
        diff_pnl = with_pnl - without_pnl
        diff_wr = with_wr - without_wr
        
        logger.info(f"\n📈 الفرق:")
        logger.info(f"   الربح: {diff_pnl:+.2f} USDT ({(diff_pnl/abs(without_pnl)*100) if without_pnl != 0 else 0:+.1f}%)")
        logger.info(f"   معدل النجاح: {diff_wr:+.1f}%")
        
        # تفاصيل MTF Exits
        if mtf_exits:
            logger.info(f"\n{'='*80}")
            logger.info(f"📋 تفاصيل صفقات MTF Exit ({len(mtf_exits)} صفقة)")
            logger.info(f"{'='*80}")
            
            mtf_wins = sum(1 for t in mtf_exits if t['pnl_usd'] > 0)
            mtf_pnl = sum(t['pnl_usd'] for t in mtf_exits)
            
            logger.info(f"   رابحة: {mtf_wins}/{len(mtf_exits)} ({mtf_wins/len(mtf_exits)*100:.1f}%)")
            logger.info(f"   الربح/الخسارة: {mtf_pnl:+.2f} USDT")
            
            for i, trade in enumerate(mtf_exits[:5], 1):  # أول 5
                logger.info(f"\n   #{i} {trade['symbol']}:")
                logger.info(f"      الدخول: {trade['entry_price']:.2f} | الخروج: {trade['exit_price']:.2f}")
                logger.info(f"      السبب: {trade['exit_reason']}")
                logger.info(f"      الربح: {trade['pnl_usd']:+.2f} USDT ({trade['pnl_pct']:+.2f}%)")
        
        # التقييم النهائي
        logger.info(f"\n{'='*80}")
        if diff_pnl > 2:
            logger.info("✅ النتيجة: MTF Reversal Exit يحسّن النتائج بشكل واضح")
            rating = "ممتاز"
        elif diff_pnl > 0:
            logger.info("✅ النتيجة: MTF Reversal Exit يحسّن النتائج قليلاً")
            rating = "جيد"
        elif diff_pnl > -2:
            logger.info("⚖️ النتيجة: MTF Reversal Exit محايد")
            rating = "محايد"
        else:
            logger.info("❌ النتيجة: MTF Reversal Exit يضر بالنتائج")
            rating = "ضعيف"
        
        logger.info(f"   التقييم: {rating}")
        logger.info(f"   التحسين: {diff_pnl:+.2f} USDT")
        logger.info(f"{'='*80}")


if __name__ == "__main__":
    tester = MTFExitTester()
    
    # اختبار على عملات متعددة
    logger.info("\n🚀 بدء الاختبار الشامل لـ MTF Reversal Exit")
    tester.run_test(['BTC/USDT', 'ETH/USDT', 'BNB/USDT'])
