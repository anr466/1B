#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تحليل مشكلة التأخير في إشارات الدخول
=========================================

الهدف:
1. قياس التأخير بين الإشارة الفعلية والدخول
2. قياس متوسط مدة الصفقات
3. تحليل نسبة الأرباح حسب وقت الدخول
4. مقارنة 1H+15m vs 15m+5m
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
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class TimingAnalyzer:
    """تحليل التوقيت ومشكلة التأخير"""
    
    def __init__(self):
        self.exchange = ccxt.binance()
        
    def fetch_data(self, symbol, timeframe, limit=1000):
        """جلب البيانات"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
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
    
    def detect_reversal_signal(self, df, idx):
        """كشف إشارة الانعكاس الحقيقية"""
        if idx < 20 or idx >= len(df) - 1:
            return None
        
        # RSI
        rsi = df['rsi'].iloc[idx]
        if pd.isna(rsi) or rsi > 35:
            return None
        
        # Hammer Pattern
        o = df['open'].iloc[idx]
        h = df['high'].iloc[idx]
        l = df['low'].iloc[idx]
        c = df['close'].iloc[idx]
        
        body = abs(c - o)
        lower_wick = min(o, c) - l
        upper_wick = h - max(o, c)
        
        if body == 0:
            return None
        
        # Hammer: lower_wick > body * 1.5
        if lower_wick > body * 1.5 and c > o:
            return {
                'idx': idx,
                'time': df['timestamp'].iloc[idx],
                'price': df['close'].iloc[idx],
                'type': 'hammer',
                'rsi': rsi,
                'strength': min(lower_wick / body, 3.0)
            }
        
        return None
    
    def confirm_with_mtf(self, df_primary, df_confirm, signal_idx_primary):
        """تأكيد الإشارة بإطار زمني أقصر"""
        # النسبة بين الأطر
        # 1H:15m = 4:1
        # 15m:5m = 3:1
        
        signal_time = df_primary['timestamp'].iloc[signal_idx_primary]
        
        # البحث عن التأكيد في الإطار الأقصر
        confirm_candles = df_confirm[df_confirm['timestamp'] <= signal_time + timedelta(minutes=60)]
        confirm_candles = confirm_candles[confirm_candles['timestamp'] >= signal_time]
        
        if len(confirm_candles) == 0:
            return None
        
        # التحقق من التأكيد
        for i in range(len(confirm_candles)):
            candle = confirm_candles.iloc[i]
            
            # تأكيد بسيط: السعر يرتد
            if i > 0:
                prev_close = confirm_candles.iloc[i-1]['close']
                current_close = candle['close']
                
                if current_close > prev_close * 1.002:  # ارتداد +0.2%
                    return {
                        'confirmed': True,
                        'confirm_time': candle['timestamp'],
                        'confirm_price': candle['close'],
                        'delay_minutes': (candle['timestamp'] - signal_time).total_seconds() / 60
                    }
        
        return None
    
    def simulate_entry_scenarios(self, symbol, df_1h, df_15m, df_5m=None):
        """محاكاة سيناريوهات الدخول المختلفة"""
        results = {
            'immediate_1h': [],      # دخول فوري على إشارة 1H
            'confirmed_1h_15m': [],  # دخول بعد تأكيد 15m
            'immediate_15m': [],     # دخول فوري على إشارة 15m
            'confirmed_15m_5m': []   # دخول بعد تأكيد 5m
        }
        
        # سيناريو 1: النظام الحالي (1H إشارة + 15m تأكيد)
        for i in range(50, len(df_1h) - 96):
            signal = self.detect_reversal_signal(df_1h, i)
            if not signal:
                continue
            
            entry_price = signal['price']
            entry_time = signal['time']
            
            # دخول فوري
            result_immediate = self.simulate_trade(df_1h, i, entry_price, 'immediate_1h')
            if result_immediate:
                results['immediate_1h'].append(result_immediate)
            
            # دخول بعد تأكيد 15m
            confirmation = self.confirm_with_mtf(df_1h, df_15m, i)
            if confirmation:
                # الدخول بعد التأكيد
                delay_hours = confirmation['delay_minutes'] / 60
                entry_idx_delayed = min(i + int(delay_hours), len(df_1h) - 96)
                entry_price_delayed = df_1h['close'].iloc[entry_idx_delayed]
                
                result_confirmed = self.simulate_trade(df_1h, entry_idx_delayed, entry_price_delayed, 'confirmed_1h_15m')
                if result_confirmed:
                    result_confirmed['delay_minutes'] = confirmation['delay_minutes']
                    result_confirmed['price_slippage'] = ((entry_price_delayed - entry_price) / entry_price) * 100
                    results['confirmed_1h_15m'].append(result_confirmed)
        
        # سيناريو 2: النظام المقترح (15m إشارة + 5m تأكيد)
        if df_5m is not None:
            for i in range(50, len(df_15m) - 288):  # 288 = 72 ساعة / 15 دقيقة
                signal = self.detect_reversal_signal(df_15m, i)
                if not signal:
                    continue
                
                entry_price = signal['price']
                
                # دخول فوري
                result_immediate = self.simulate_trade(df_15m, i, entry_price, 'immediate_15m')
                if result_immediate:
                    results['immediate_15m'].append(result_immediate)
                
                # دخول بعد تأكيد 5m
                confirmation = self.confirm_with_mtf(df_15m, df_5m, i)
                if confirmation:
                    delay_candles = int(confirmation['delay_minutes'] / 15)
                    entry_idx_delayed = min(i + delay_candles, len(df_15m) - 288)
                    entry_price_delayed = df_15m['close'].iloc[entry_idx_delayed]
                    
                    result_confirmed = self.simulate_trade(df_15m, entry_idx_delayed, entry_price_delayed, 'confirmed_15m_5m')
                    if result_confirmed:
                        result_confirmed['delay_minutes'] = confirmation['delay_minutes']
                        result_confirmed['price_slippage'] = ((entry_price_delayed - entry_price) / entry_price) * 100
                        results['confirmed_15m_5m'].append(result_confirmed)
        
        return results
    
    def simulate_trade(self, df, entry_idx, entry_price, scenario_type):
        """محاكاة صفقة واحدة"""
        stop_loss = entry_price * 0.97
        take_profit = entry_price * 1.06
        
        # تحديد عدد الشموع حسب الإطار الزمني
        if '1h' in scenario_type:
            max_hold_candles = 96  # 96 ساعة
        else:  # 15m
            max_hold_candles = 288  # 72 ساعة (لنقارن بنفس المدة)
        
        exit_idx = None
        exit_price = None
        exit_reason = None
        
        for i in range(entry_idx + 1, min(entry_idx + max_hold_candles, len(df))):
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            close = df['close'].iloc[i]
            
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
        
        # Max Hold Time
        if exit_idx is None:
            exit_idx = min(entry_idx + max_hold_candles, len(df) - 1)
            exit_price = df['close'].iloc[exit_idx]
            exit_reason = 'Max Hold Time'
        
        # حساب النتائج
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        pnl_usd = pnl_pct  # افتراض 100 USDT
        
        # المدة
        if '1h' in scenario_type:
            hold_hours = exit_idx - entry_idx
        else:  # 15m
            hold_hours = (exit_idx - entry_idx) * 0.25
        
        return {
            'scenario': scenario_type,
            'entry_time': df['timestamp'].iloc[entry_idx],
            'entry_price': entry_price,
            'exit_time': df['timestamp'].iloc[exit_idx],
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct,
            'pnl_usd': pnl_usd,
            'hold_hours': hold_hours,
            'is_win': pnl_usd > 0
        }
    
    def analyze_results(self, results):
        """تحليل النتائج"""
        logger.info(f"\n{'='*80}")
        logger.info("📊 تحليل مشكلة التأخير والتوقيت")
        logger.info(f"{'='*80}\n")
        
        scenarios = {
            'immediate_1h': '1H دخول فوري',
            'confirmed_1h_15m': '1H + تأكيد 15m',
            'immediate_15m': '15m دخول فوري',
            'confirmed_15m_5m': '15m + تأكيد 5m'
        }
        
        summary = {}
        
        for scenario_key, scenario_name in scenarios.items():
            trades = results.get(scenario_key, [])
            
            if not trades:
                continue
            
            wins = [t for t in trades if t['is_win']]
            losses = [t for t in trades if not t['is_win']]
            
            total_pnl = sum(t['pnl_usd'] for t in trades)
            win_rate = (len(wins) / len(trades)) * 100 if trades else 0
            avg_hold = np.mean([t['hold_hours'] for t in trades]) if trades else 0
            
            # حساب التأخير
            delayed_trades = [t for t in trades if 'delay_minutes' in t]
            avg_delay = np.mean([t['delay_minutes'] for t in delayed_trades]) if delayed_trades else 0
            avg_slippage = np.mean([abs(t['price_slippage']) for t in delayed_trades]) if delayed_trades else 0
            
            # صفقات نفس اليوم
            same_day = [t for t in trades if t['hold_hours'] <= 24]
            same_day_pct = (len(same_day) / len(trades)) * 100 if trades else 0
            
            summary[scenario_key] = {
                'name': scenario_name,
                'total_trades': len(trades),
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'avg_hold': avg_hold,
                'avg_delay': avg_delay,
                'avg_slippage': avg_slippage,
                'same_day_pct': same_day_pct
            }
        
        # عرض النتائج
        for key in ['immediate_1h', 'confirmed_1h_15m', 'immediate_15m', 'confirmed_15m_5m']:
            if key not in summary:
                continue
            
            s = summary[key]
            
            logger.info(f"{'='*80}")
            logger.info(f"📈 {s['name']}")
            logger.info(f"{'='*80}")
            logger.info(f"   إجمالي الصفقات: {s['total_trades']}")
            logger.info(f"   الربح/الخسارة: {s['total_pnl']:+.2f} USDT")
            logger.info(f"   معدل النجاح: {s['win_rate']:.1f}%")
            logger.info(f"   متوسط المدة: {s['avg_hold']:.1f} ساعة")
            
            if s['avg_delay'] > 0:
                logger.info(f"   متوسط التأخير: {s['avg_delay']:.1f} دقيقة")
                logger.info(f"   متوسط الانزلاق: {s['avg_slippage']:.3f}%")
            
            logger.info(f"   صفقات نفس اليوم: {s['same_day_pct']:.1f}%")
            logger.info("")
        
        # المقارنة
        logger.info(f"\n{'='*80}")
        logger.info("🔍 المقارنة والتوصيات")
        logger.info(f"{'='*80}\n")
        
        if 'immediate_1h' in summary and 'confirmed_1h_15m' in summary:
            imm = summary['immediate_1h']
            conf = summary['confirmed_1h_15m']
            
            logger.info("📊 النظام الحالي (1H):")
            logger.info(f"   التأخير يؤثر: {conf['avg_delay']:.1f} دقيقة تأخير")
            logger.info(f"   الانزلاق: {conf['avg_slippage']:.3f}% في السعر")
            logger.info(f"   التأثير على الربح: {(conf['total_pnl'] - imm['total_pnl']):.2f} USDT")
            
            if conf['total_pnl'] < imm['total_pnl']:
                logger.info(f"   ⚠️ التأكيد يقلل الربح بنسبة {((imm['total_pnl'] - conf['total_pnl']) / abs(imm['total_pnl']) * 100):.1f}%")
            else:
                logger.info(f"   ✅ التأكيد يحسن الربح")
        
        if 'immediate_15m' in summary and 'confirmed_15m_5m' in summary:
            logger.info("\n📊 النظام المقترح (15m):")
            imm = summary['immediate_15m']
            conf = summary['confirmed_15m_5m']
            
            logger.info(f"   فرص أكثر: {imm['total_trades']} صفقة")
            logger.info(f"   مدة أقصر: {imm['avg_hold']:.1f} ساعة")
            logger.info(f"   صفقات يومية: {imm['same_day_pct']:.1f}%")
        
        # التوصية النهائية
        logger.info(f"\n{'='*80}")
        logger.info("✅ التوصية النهائية:")
        logger.info(f"{'='*80}")
        
        if 'immediate_15m' in summary and 'immediate_1h' in summary:
            if summary['immediate_15m']['total_pnl'] > summary['immediate_1h']['total_pnl']:
                improvement = ((summary['immediate_15m']['total_pnl'] - summary['immediate_1h']['total_pnl']) / abs(summary['immediate_1h']['total_pnl']) * 100)
                logger.info(f"🚀 التحول إلى 15m + 5m")
                logger.info(f"   التحسين المتوقع: +{improvement:.1f}%")
                logger.info(f"   فرص أكثر: {summary['immediate_15m']['total_trades'] - summary['immediate_1h']['total_trades']} صفقة إضافية")
                logger.info(f"   تداول يومي: {summary['immediate_15m']['same_day_pct']:.0f}% من الصفقات")
            else:
                logger.info("⚖️ البقاء على 1H + 15m")
                logger.info("   النظام الحالي أفضل")
        
        logger.info(f"{'='*80}\n")
        
        return summary
    
    def run_analysis(self, symbol='BTC/USDT'):
        """تشغيل التحليل الكامل"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔬 تحليل التوقيت والتأخير - {symbol}")
        logger.info(f"{'='*80}\n")
        
        # جلب البيانات
        logger.info("📊 جلب البيانات...")
        df_1h = self.fetch_data(symbol, '1h', limit=1000)
        df_15m = self.fetch_data(symbol, '15m', limit=2000)
        df_5m = self.fetch_data(symbol, '5m', limit=3000)
        
        if df_1h.empty or df_15m.empty:
            logger.error("فشل جلب البيانات!")
            return
        
        logger.info(f"   1H: {len(df_1h)} شمعة")
        logger.info(f"   15m: {len(df_15m)} شمعة")
        logger.info(f"   5m: {len(df_5m)} شمعة")
        
        # محاكاة السيناريوهات
        logger.info("\n🔄 محاكاة سيناريوهات الدخول...")
        results = self.simulate_entry_scenarios(symbol, df_1h, df_15m, df_5m)
        
        # تحليل النتائج
        summary = self.analyze_results(results)
        
        return summary


if __name__ == "__main__":
    analyzer = TimingAnalyzer()
    
    logger.info("\n🚀 بدء تحليل مشكلة التأخير والتوقيت\n")
    
    # تحليل BTC
    summary = analyzer.run_analysis('BTC/USDT')
