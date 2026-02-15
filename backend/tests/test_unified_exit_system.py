#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار نظام الخروج الموحد - مقارنة مع الأنظمة القديمة
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class ExitSystemComparison:
    """مقارنة أنظمة الخروج"""
    
    def __init__(self):
        self.capital = 1000
        self.trade_size_pct = 0.12
    
    def fetch_data(self, symbol: str, interval: str = '1h', limit: int = 720) -> pd.DataFrame:
        """جلب بيانات من Binance"""
        url = "https://api.binance.com/api/v3/klines"
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            return None
    
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """إضافة المؤشرات"""
        df = df.copy()
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # EMAs
        df['ema_8'] = df['close'].ewm(span=8).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # Volume
        df['vol_avg'] = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / df['vol_avg']
        
        # Candle type
        df['is_bullish'] = df['close'] > df['open']
        df['is_bearish'] = df['close'] < df['open']
        
        return df
    
    def simulate_trade_unified(self, df: pd.DataFrame, symbol: str, entry_idx: int) -> dict:
        """محاكاة صفقة بنظام الخروج الموحد"""
        from backend.trade_management.unified_exit_system import UnifiedExitSystem, get_asset_profile
        
        exit_system = UnifiedExitSystem()
        profile = get_asset_profile(symbol)
        
        entry_price = df.iloc[entry_idx]['close']
        entry_time = df.iloc[entry_idx]['timestamp']
        atr = df.iloc[entry_idx]['atr']
        
        # تسجيل الصفقة
        position_id = f"test_{entry_idx}"
        state = exit_system.register_position(
            position_id=position_id,
            symbol=symbol,
            entry_price=entry_price,
            quantity=1,
            atr=atr,
            entry_time=entry_time
        )
        
        # محاكاة
        for i in range(entry_idx + 1, len(df)):
            current = df.iloc[i]
            candle_data = {
                'ema_short': current['ema_8'],
                'ema_long': current['ema_21'],
                'rsi': current['rsi'],
                'macd': current['macd'],
                'volume_ratio': current['vol_ratio'],
                'is_bearish': current['is_bearish'],
                'consecutive_red': self._count_consecutive_red(df, i)
            }
            
            result = exit_system.check_exit(
                position_id=position_id,
                current_price=current['close'],
                timestamp=current['timestamp'],
                candle_data=candle_data
            )
            
            if result and result.get('should_exit'):
                return {
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': result['exit_price'],
                    'pnl_pct': result['pnl_pct'],
                    'reason': result['reason'],
                    'hold_bars': i - entry_idx,
                    'system': 'unified'
                }
        
        # لم يخرج
        exit_price = df.iloc[-1]['close']
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        return {
            'entry_idx': entry_idx,
            'exit_idx': len(df) - 1,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'reason': 'end_of_data',
            'hold_bars': len(df) - 1 - entry_idx,
            'system': 'unified'
        }
    
    def simulate_trade_old(self, df: pd.DataFrame, symbol: str, entry_idx: int) -> dict:
        """محاكاة صفقة بنظام الخروج القديم (SmartExitSystemV2)"""
        from backend.trade_management.smart_exit_system_v2 import SmartExitSystemV2
        
        exit_system = SmartExitSystemV2()
        
        entry_price = df.iloc[entry_idx]['close']
        entry_time = df.iloc[entry_idx]['timestamp']
        atr = df.iloc[entry_idx]['atr']
        
        # تسجيل الصفقة
        position_id = f"test_{entry_idx}"
        exit_system.on_position_open(
            position_id=position_id,
            entry_price=entry_price,
            quantity=1,
            atr=atr,
            timestamp=entry_time
        )
        
        # محاكاة
        for i in range(entry_idx + 1, len(df)):
            current = df.iloc[i]
            candle_data = {
                'ema_short': current['ema_8'],
                'ema_long': current['ema_21'],
                'rsi': current['rsi'],
                'macd': current['macd'],
            }
            
            result = exit_system.check_exit_conditions(
                position_id=position_id,
                current_price=current['close'],
                timestamp=current['timestamp'],
                candle_data=candle_data
            )
            
            if result.get('should_exit'):
                pnl_pct = ((result['exit_price'] - entry_price) / entry_price) * 100
                return {
                    'entry_idx': entry_idx,
                    'exit_idx': i,
                    'entry_price': entry_price,
                    'exit_price': result['exit_price'],
                    'pnl_pct': pnl_pct,
                    'reason': result['reason'],
                    'hold_bars': i - entry_idx,
                    'system': 'old_v2'
                }
        
        # لم يخرج
        exit_price = df.iloc[-1]['close']
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        return {
            'entry_idx': entry_idx,
            'exit_idx': len(df) - 1,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pct': pnl_pct,
            'reason': 'end_of_data',
            'hold_bars': len(df) - 1 - entry_idx,
            'system': 'old_v2'
        }
    
    def _count_consecutive_red(self, df: pd.DataFrame, idx: int) -> int:
        """عد الشموع الحمراء المتتالية"""
        count = 0
        for i in range(idx, max(0, idx - 5), -1):
            if df.iloc[i]['is_bearish']:
                count += 1
            else:
                break
        return count
    
    def find_entry_signals(self, df: pd.DataFrame) -> list:
        """إيجاد نقاط دخول للاختبار"""
        entries = []
        
        for i in range(60, len(df) - 50):
            # شروط دخول بسيطة للاختبار
            if (df.iloc[i]['ema_8'] > df.iloc[i]['ema_21'] and
                df.iloc[i]['rsi'] > 40 and df.iloc[i]['rsi'] < 65 and
                df.iloc[i]['macd'] > df.iloc[i]['macd_signal'] and
                df.iloc[i]['is_bullish']):
                
                # تجنب دخولين متقاربين
                if not entries or i - entries[-1] > 10:
                    entries.append(i)
        
        return entries[:20]  # أقصى 20 صفقة للاختبار
    
    def run_comparison(self):
        """تشغيل المقارنة"""
        print("\n" + "="*70)
        print("🔬 مقارنة أنظمة الخروج: الموحد vs القديم")
        print("="*70)
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
        
        all_unified = []
        all_old = []
        
        for symbol in symbols:
            print(f"\n📊 {symbol}...")
            
            df = self.fetch_data(symbol)
            if df is None or len(df) < 100:
                print(f"   ⚠️ بيانات غير كافية")
                continue
            
            df = self.add_indicators(df)
            entries = self.find_entry_signals(df)
            
            if not entries:
                print(f"   ⚠️ لا توجد نقاط دخول")
                continue
            
            print(f"   📍 {len(entries)} نقاط دخول")
            
            for entry_idx in entries:
                # اختبار النظام الموحد
                try:
                    unified_result = self.simulate_trade_unified(df, symbol, entry_idx)
                    unified_result['symbol'] = symbol
                    all_unified.append(unified_result)
                except Exception as e:
                    logger.error(f"Unified error: {e}")
                
                # اختبار النظام القديم
                try:
                    old_result = self.simulate_trade_old(df, symbol, entry_idx)
                    old_result['symbol'] = symbol
                    all_old.append(old_result)
                except Exception as e:
                    logger.error(f"Old error: {e}")
        
        # تحليل النتائج
        self._analyze_results(all_unified, all_old)
    
    def _analyze_results(self, unified: list, old: list):
        """تحليل النتائج"""
        print("\n" + "="*70)
        print("📊 نتائج المقارنة")
        print("="*70)
        
        if not unified or not old:
            print("❌ لا توجد نتائج كافية للمقارنة")
            return
        
        # النظام الموحد
        unified_pnl = [t['pnl_pct'] for t in unified]
        unified_wins = len([p for p in unified_pnl if p > 0])
        unified_wr = unified_wins / len(unified_pnl) * 100
        unified_avg = np.mean(unified_pnl)
        unified_total = sum(unified_pnl)
        
        # النظام القديم
        old_pnl = [t['pnl_pct'] for t in old]
        old_wins = len([p for p in old_pnl if p > 0])
        old_wr = old_wins / len(old_pnl) * 100
        old_avg = np.mean(old_pnl)
        old_total = sum(old_pnl)
        
        print(f"\n┌{'─'*68}┐")
        print(f"│{'المقياس':^20}│{'النظام الموحد':^22}│{'النظام القديم':^22}│")
        print(f"├{'─'*68}┤")
        print(f"│{'عدد الصفقات':^20}│{len(unified):^22}│{len(old):^22}│")
        print(f"│{'Win Rate':^20}│{unified_wr:^22.1f}%│{old_wr:^22.1f}%│")
        print(f"│{'متوسط PnL':^20}│{unified_avg:^22.2f}%│{old_avg:^22.2f}%│")
        print(f"│{'إجمالي PnL':^20}│{unified_total:^22.2f}%│{old_total:^22.2f}%│")
        print(f"└{'─'*68}┘")
        
        # تحليل أسباب الخروج
        print(f"\n📊 أسباب الخروج (النظام الموحد):")
        unified_reasons = {}
        for t in unified:
            r = t['reason']
            unified_reasons[r] = unified_reasons.get(r, 0) + 1
        for r, c in sorted(unified_reasons.items(), key=lambda x: -x[1]):
            print(f"   • {r}: {c} ({c/len(unified)*100:.1f}%)")
        
        print(f"\n📊 أسباب الخروج (النظام القديم):")
        old_reasons = {}
        for t in old:
            r = t['reason']
            old_reasons[r] = old_reasons.get(r, 0) + 1
        for r, c in sorted(old_reasons.items(), key=lambda x: -x[1]):
            print(f"   • {r}: {c} ({c/len(old)*100:.1f}%)")
        
        # الفائز
        print("\n" + "="*70)
        if unified_total > old_total:
            improvement = unified_total - old_total
            print(f"🏆 الفائز: النظام الموحد (+{improvement:.2f}% تحسن)")
        elif old_total > unified_total:
            diff = old_total - unified_total
            print(f"⚠️ النظام القديم أفضل بـ +{diff:.2f}%")
        else:
            print(f"🤝 النتائج متساوية")
        print("="*70)


def main():
    """تشغيل الاختبار"""
    comparison = ExitSystemComparison()
    comparison.run_comparison()


if __name__ == "__main__":
    main()
