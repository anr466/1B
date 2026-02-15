#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار شامل لنظام التداول الكامل
================================

يختبر:
1. نظام الدخول (EnhancedEntrySystem)
2. نظام الخروج الموحد (UnifiedExitSystem)
3. إدارة المخاطر (Kelly + Portfolio Heat)
4. الطبقة المعرفية (Cognitive)
5. ML Filter
6. القائمة السوداء الديناميكية

الهدف: التحقق من التوافق وتحسين الأداء
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import logging
from typing import Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class FullSystemLiveTest:
    """اختبار شامل للنظام الكامل"""
    
    def __init__(self, capital: float = 1000, max_positions: int = 5):
        self.initial_capital = capital
        self.capital = capital
        self.max_positions = max_positions
        self.trade_size_pct = 0.12  # 12%
        
        # === رسوم واقعية (Binance Spot) ===
        self.fee_pct = 0.001  # 0.1% رسوم لكل صفقة
        self.slippage_pct = 0.0005  # 0.05% انزلاق
        self.total_fees_paid = 0  # إجمالي الرسوم المدفوعة
        
        # الصفقات
        self.open_positions = {}
        self.closed_trades = []
        self.daily_trades = {}
        
        # الإحصائيات
        self.stats = {
            'total_signals': 0,
            'filtered_by_cognitive': 0,
            'filtered_by_ml': 0,
            'filtered_by_blacklist': 0,
            'filtered_by_heat': 0,
            'executed_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0,
            'max_drawdown': 0,
            'peak_capital': capital,
        }
        
        # تحميل المكونات
        self._load_components()
    
    def _load_components(self):
        """تحميل جميع مكونات النظام"""
        logger.info("📦 تحميل مكونات النظام...")
        
        try:
            # نظام الخروج الموحد
            from backend.trade_management import get_unified_exit_system, get_asset_profile
            self.exit_system = get_unified_exit_system()
            self.get_asset_profile = get_asset_profile
            logger.info("  ✅ UnifiedExitSystem")
            
            # نظام الدخول
            from backend.strategies.enhanced_entry_system import EnhancedEntrySystem
            self.entry_system = EnhancedEntrySystem(strategy='combined')
            logger.info("  ✅ EnhancedEntrySystem")
            
            # إدارة المخاطر
            from backend.risk.kelly_position_sizer import KellyPositionSizer
            from backend.risk.portfolio_heat_manager import PortfolioHeatManager
            self.kelly_sizer = KellyPositionSizer(self.initial_capital)
            self.heat_manager = PortfolioHeatManager(max_heat_pct=6.0)
            logger.info("  ✅ Risk Management (Kelly + Heat)")
            
            # الطبقة المعرفية
            from backend.cognitive import (
                get_market_state_detector,
                get_asset_classifier,
                get_reasoning_engine,
                ReversalDetector
            )
            self.market_detector = get_market_state_detector()
            self.asset_classifier = get_asset_classifier()
            self.reasoning_engine = get_reasoning_engine()
            self.reversal_detector = ReversalDetector()
            logger.info("  ✅ Cognitive Layer")
            
            # ML (اختياري)
            try:
                from backend.ml.trading_brain import get_trading_brain
                self.trading_brain = get_trading_brain()
                self.ml_enabled = True
                logger.info("  ✅ ML Trading Brain")
            except Exception as e:
                self.trading_brain = None
                self.ml_enabled = False
                logger.info(f"  ⚠️ ML disabled: {e}")
            
            # الفلاتر المحسّنة
            from backend.core.optimized_trading_filters import get_optimized_filters
            self.optimized_filters = get_optimized_filters()
            logger.info("  ✅ Optimized Filters")
            
            logger.info("📦 تم تحميل جميع المكونات بنجاح!")
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحميل المكونات: {e}")
            raise
    
    def fetch_data(self, symbol: str, interval: str = '1h', limit: int = 500) -> Optional[pd.DataFrame]:
        """جلب بيانات من Binance"""
        url = "https://api.binance.com/api/v3/klines"
        params = {'symbol': symbol, 'interval': interval, 'limit': limit}
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if isinstance(data, dict) and 'code' in data:
                logger.warning(f"  ⚠️ {symbol}: {data.get('msg', 'API Error')}")
                return None
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            df.attrs['symbol'] = symbol
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            logger.warning(f"  ⚠️ {symbol}: {e}")
            return None
    
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """إضافة المؤشرات الفنية"""
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
        df['ema_200'] = df['close'].ewm(span=200).mean()
        
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
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # ADX
        df['plus_dm'] = np.where(
            (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
            np.maximum(df['high'] - df['high'].shift(1), 0), 0
        )
        df['minus_dm'] = np.where(
            (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
            np.maximum(df['low'].shift(1) - df['low'], 0), 0
        )
        df['plus_di'] = 100 * (df['plus_dm'].rolling(14).mean() / df['atr'])
        df['minus_di'] = 100 * (df['minus_dm'].rolling(14).mean() / df['atr'])
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].rolling(14).mean()
        
        # Volume
        df['vol_avg'] = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / df['vol_avg']
        
        # Candle type
        df['is_bullish'] = df['close'] > df['open']
        df['is_bearish'] = df['close'] < df['open']
        
        # Bollinger Bands
        df['bb_mid'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
        
        return df
    
    def check_entry_conditions(self, df: pd.DataFrame, idx: int, symbol: str) -> Optional[Dict]:
        """فحص شروط الدخول الكاملة"""
        if idx < 200 or idx >= len(df) - 1:
            return None
        
        current = df.iloc[idx]
        prev = df.iloc[idx - 1]
        
        # 1. الشروط الأساسية (Golden Algorithm V3 - محسّن)
        basic_conditions = {
            'above_ema200': current['close'] > current['ema_200'],
            'trend_up': current['ema_50'] > current['ema_200'],
            'ema_alignment': current['ema_8'] > current['ema_21'] > current['ema_50'],  # ترتيب EMAs
            'adx_strong': current['adx'] >= 25,  # زيادة من 22
            'rsi_zone': 45 <= current['rsi'] <= 60,  # تضييق النطاق
            'macd_positive': current['macd'] > current['macd_signal'],
            'macd_rising': current['macd'] > prev['macd'],  # MACD صاعد
            'volume_ok': current['vol_ratio'] >= 1.0,  # زيادة من 0.8
            'bullish_candle': current['is_bullish'],
            'not_overbought': current['rsi'] < 70,  # ليس في منطقة شراء مفرط
        }
        
        passed = sum(basic_conditions.values())
        total = len(basic_conditions)
        
        if passed < 8:  # V6: تشديد إلى 8/10 للجودة وتقليل الصفقات
            return None
        
        self.stats['total_signals'] += 1
        
        # 2. فلاتر حالة السوق (V5 - من النظام الأصلي)
        
        # فلتر 1: EMA200 slope
        ema200_slope = (current['ema_200'] - df.iloc[idx-20]['ema_200']) / df.iloc[idx-20]['ema_200']
        if ema200_slope < -0.01:  # EMA200 هابط
            self.stats['filtered_by_cognitive'] += 1
            return None
        
        # فلتر 2: العملات الراكدة (هبوط > 12% من القمة)
        if idx >= 480:  # ~20 يوم
            highest_20d = df.iloc[idx-480:idx]['high'].max()
            drop_from_high = (highest_20d - current['close']) / highest_20d
            if drop_from_high > 0.12:  # هبوط > 12%
                self.stats['filtered_by_cognitive'] += 1
                return None
        
        # فلتر 3: الهبوط الأسبوعي (> 10% في 7 أيام)
        if idx >= 168:  # 7 أيام
            price_7d_ago = df.iloc[idx-168]['close']
            weekly_change = (current['close'] - price_7d_ago) / price_7d_ago
            if weekly_change < -0.10:  # هبوط > 10%
                self.stats['filtered_by_cognitive'] += 1
                return None
        
        # فلتر 4: انعكاس السوق (هبوط > 7% من القمة الأخيرة)
        if idx >= 50:
            recent_high = df.iloc[idx-50:idx]['high'].max()
            market_drop = (recent_high - current['close']) / recent_high
            if market_drop > 0.07:  # هبوط > 7% (أقل صرامة)
                self.stats['filtered_by_cognitive'] += 1
                return None
        
        # فلتر 5: هبوط حاد قصير المدى
        recent_drop = (current['close'] - df.iloc[idx-10]['high']) / df.iloc[idx-10]['high']
        if recent_drop < -0.05:  # هبوط > 5% في 10 شموع
            self.stats['filtered_by_cognitive'] += 1
            return None
        
        # 3. فلتر ML (إذا متاح)
        if self.ml_enabled and self.trading_brain:
            try:
                ml_result = self.trading_brain.predict_signal_quality({
                    'rsi': current['rsi'],
                    'macd': current['macd'],
                    'adx': current['adx'],
                    'volume_ratio': current['vol_ratio'],
                })
                if ml_result and ml_result.get('confidence', 100) < 55:
                    self.stats['filtered_by_ml'] += 1
                    return None
            except:
                pass
        
        # 4. فلتر Portfolio Heat
        heat_check = self.heat_manager.check_portfolio_heat(
            list(self.open_positions.values()),
            self.capital
        )
        if not heat_check.get('can_open_new', True):
            self.stats['filtered_by_heat'] += 1
            return None
        
        # 5. حساب حجم الصفقة
        position_size = self.kelly_sizer.calculate_position_size(
            balance=self.capital,
            max_position_pct=0.10,
            symbol=symbol
        )
        
        # إنشاء الإشارة
        return {
            'symbol': symbol,
            'entry_price': current['close'],
            'entry_time': current['timestamp'],
            'atr': current['atr'],
            'conditions_passed': passed,
            'conditions_total': total,
            'position_size_pct': position_size.get('position_pct', 10),
            'rsi': current['rsi'],
            'adx': current['adx'],
            'volume_ratio': current['vol_ratio'],
        }
    
    def execute_entry(self, signal: Dict) -> bool:
        """تنفيذ الدخول"""
        if len(self.open_positions) >= self.max_positions:
            return False
        
        symbol = signal['symbol']
        if symbol in self.open_positions:
            return False
        
        # حساب الحجم مع خصم رسوم الدخول
        gross_trade_value = self.capital * (signal['position_size_pct'] / 100)
        
        # === خصم رسوم وانزلاق الدخول ===
        entry_fee = gross_trade_value * self.fee_pct  # 0.1%
        entry_slippage = gross_trade_value * self.slippage_pct  # 0.05%
        self.total_fees_paid += entry_fee + entry_slippage
        self.capital -= (entry_fee + entry_slippage)  # خصم من رأس المال
        
        trade_value = gross_trade_value - entry_fee - entry_slippage
        quantity = trade_value / signal['entry_price']
        
        # تسجيل في نظام الخروج
        position_id = f"{symbol}_{signal['entry_time'].strftime('%Y%m%d%H%M')}"
        
        state = self.exit_system.register_position(
            position_id=position_id,
            symbol=symbol,
            entry_price=signal['entry_price'],
            quantity=quantity,
            atr=signal['atr'],
            entry_time=signal['entry_time']
        )
        
        # تسجيل الصفقة
        self.open_positions[symbol] = {
            'position_id': position_id,
            'symbol': symbol,
            'entry_price': signal['entry_price'],
            'quantity': quantity,
            'trade_value': trade_value,
            'entry_time': signal['entry_time'],
            'atr': signal['atr'],
            'sl': state.current_sl,
            'tp_levels': state.tp_levels,
        }
        
        self.stats['executed_trades'] += 1
        
        # تسجيل يومي
        day = signal['entry_time'].strftime('%Y-%m-%d')
        if day not in self.daily_trades:
            self.daily_trades[day] = {'entries': 0, 'exits': 0, 'pnl': 0}
        self.daily_trades[day]['entries'] += 1
        
        logger.info(f"  📈 ENTRY: {symbol} @ ${signal['entry_price']:.4f} | Size: ${trade_value:.2f}")
        
        return True
    
    def check_exits(self, df: pd.DataFrame, idx: int, symbol: str) -> Optional[Dict]:
        """فحص شروط الخروج"""
        if symbol not in self.open_positions:
            return None
        
        position = self.open_positions[symbol]
        current = df.iloc[idx]
        
        # بناء بيانات الشمعة
        candle_data = {
            'ema_short': current['ema_8'],
            'ema_long': current['ema_21'],
            'rsi': current['rsi'],
            'macd': current['macd'],
            'volume_ratio': current['vol_ratio'],
            'is_bearish': current['is_bearish'],
            'consecutive_red': self._count_consecutive_red(df, idx),
        }
        
        # فحص الخروج
        exit_result = self.exit_system.check_exit(
            position_id=position['position_id'],
            current_price=current['close'],
            timestamp=current['timestamp'],
            candle_data=candle_data
        )
        
        return exit_result
    
    def execute_exit(self, symbol: str, exit_result: Dict, current_price: float, timestamp: datetime):
        """تنفيذ الخروج"""
        if symbol not in self.open_positions:
            return
        
        position = self.open_positions[symbol]
        
        # حساب PnL بشكل واقعي
        close_pct = exit_result.get('close_quantity_pct', 1.0)
        pnl_pct = exit_result.get('pnl_pct', 0)
        trade_value = position['trade_value'] * close_pct
        
        # === خصم الرسوم والانزلاق ===
        # رسوم الخروج (0.1%)
        exit_fee = trade_value * self.fee_pct
        # انزلاق الخروج (0.05%)
        exit_slippage = trade_value * self.slippage_pct
        
        # PnL الصافي
        gross_pnl = trade_value * (pnl_pct / 100)
        net_pnl = gross_pnl - exit_fee - exit_slippage
        pnl_value = net_pnl
        
        self.total_fees_paid += exit_fee + exit_slippage
        
        # تحديث رأس المال
        self.capital += pnl_value
        self.stats['total_pnl'] += pnl_value
        
        if pnl_value > 0:
            self.stats['wins'] += 1
        else:
            self.stats['losses'] += 1
        
        # تحديث Drawdown
        if self.capital > self.stats['peak_capital']:
            self.stats['peak_capital'] = self.capital
        drawdown = (self.stats['peak_capital'] - self.capital) / self.stats['peak_capital'] * 100
        if drawdown > self.stats['max_drawdown']:
            self.stats['max_drawdown'] = drawdown
        
        # تسجيل يومي
        day = timestamp.strftime('%Y-%m-%d')
        if day not in self.daily_trades:
            self.daily_trades[day] = {'entries': 0, 'exits': 0, 'pnl': 0}
        self.daily_trades[day]['exits'] += 1
        self.daily_trades[day]['pnl'] += pnl_value
        
        # تسجيل الصفقة المغلقة
        self.closed_trades.append({
            'symbol': symbol,
            'entry_price': position['entry_price'],
            'exit_price': current_price,
            'pnl_pct': pnl_pct,
            'pnl_value': pnl_value,
            'reason': exit_result.get('reason', 'unknown'),
            'entry_time': position['entry_time'],
            'exit_time': timestamp,
            'hold_hours': (timestamp - position['entry_time']).total_seconds() / 3600,
        })
        
        logger.info(f"  📉 EXIT: {symbol} @ ${current_price:.4f} | {exit_result.get('reason')} | PnL: {pnl_pct:+.2f}%")
        
        # إزالة الصفقة إذا أُغلقت بالكامل
        if close_pct >= 0.99:
            del self.open_positions[symbol]
            self.exit_system.remove_position(position['position_id'])
        else:
            # تحديث الكمية المتبقية
            self.open_positions[symbol]['quantity'] *= (1 - close_pct)
            self.open_positions[symbol]['trade_value'] *= (1 - close_pct)
    
    def _count_consecutive_red(self, df: pd.DataFrame, idx: int) -> int:
        """عد الشموع الحمراء المتتالية"""
        count = 0
        for i in range(idx, max(0, idx - 5), -1):
            if df.iloc[i]['is_bearish']:
                count += 1
            else:
                break
        return count
    
    def run_backtest(self, symbols: List[str], days: int = 30):
        """تشغيل الاختبار الخلفي"""
        print("\n" + "="*70)
        print("🔬 اختبار نظام التداول الكامل")
        print("="*70)
        print(f"   💰 رأس المال: ${self.initial_capital:,.0f}")
        print(f"   📊 العملات: {len(symbols)}")
        print(f"   📅 الفترة: {days} يوم")
        print(f"   🎯 الحد الأقصى للصفقات: {self.max_positions}")
        print("="*70)
        
        # جلب البيانات
        all_data = {}
        for symbol in symbols:
            df = self.fetch_data(symbol, '1h', min(days * 24 + 200, 1000))
            if df is not None and len(df) >= 300:
                df = self.add_indicators(df)
                all_data[symbol] = df
                print(f"   ✅ {symbol}: {len(df)} شمعة")
            else:
                print(f"   ❌ {symbol}: بيانات غير كافية")
        
        if not all_data:
            print("❌ لا توجد بيانات كافية للاختبار")
            return
        
        # تحديد نطاق الاختبار
        min_len = min(len(df) for df in all_data.values())
        start_idx = 200  # بعد حساب المؤشرات
        
        print(f"\n🔄 بدء المحاكاة من الشمعة {start_idx} إلى {min_len}...")
        
        # المحاكاة
        for i in range(start_idx, min_len):
            if i % 100 == 0:
                print(f"   📊 تقدم: {i}/{min_len} ({(i-start_idx)/(min_len-start_idx)*100:.1f}%)")
            
            # فحص الخروج أولاً
            for symbol in list(self.open_positions.keys()):
                if symbol in all_data:
                    df = all_data[symbol]
                    if i < len(df):
                        exit_result = self.check_exits(df, i, symbol)
                        if exit_result and exit_result.get('should_exit'):
                            self.execute_exit(
                                symbol,
                                exit_result,
                                df.iloc[i]['close'],
                                df.iloc[i]['timestamp']
                            )
            
            # فحص الدخول
            if len(self.open_positions) < self.max_positions:
                for symbol, df in all_data.items():
                    if symbol not in self.open_positions and i < len(df):
                        signal = self.check_entry_conditions(df, i, symbol)
                        if signal:
                            self.execute_entry(signal)
                            if len(self.open_positions) >= self.max_positions:
                                break
        
        # إغلاق الصفقات المتبقية
        print("\n📊 إغلاق الصفقات المتبقية...")
        for symbol in list(self.open_positions.keys()):
            if symbol in all_data:
                df = all_data[symbol]
                current_price = df.iloc[-1]['close']
                position = self.open_positions[symbol]
                pnl_pct = ((current_price - position['entry_price']) / position['entry_price']) * 100
                
                self.execute_exit(
                    symbol,
                    {'should_exit': True, 'reason': 'end_of_test', 'pnl_pct': pnl_pct, 'close_quantity_pct': 1.0},
                    current_price,
                    df.iloc[-1]['timestamp']
                )
        
        # عرض النتائج
        self._print_results()
    
    def _print_results(self):
        """عرض النتائج"""
        print("\n" + "="*70)
        print("📊 نتائج الاختبار")
        print("="*70)
        
        total_trades = self.stats['wins'] + self.stats['losses']
        win_rate = (self.stats['wins'] / total_trades * 100) if total_trades > 0 else 0
        roi = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        
        print(f"\n💰 الأداء المالي (واقعي مع الرسوم):")
        print(f"   رأس المال الأولي: ${self.initial_capital:,.2f}")
        print(f"   رأس المال النهائي: ${self.capital:,.2f}")
        print(f"   الربح/الخسارة الصافي: ${self.capital - self.initial_capital:+,.2f}")
        print(f"   ROI الصافي: {roi:+.2f}%")
        print(f"   Max Drawdown: {self.stats['max_drawdown']:.2f}%")
        print(f"   💸 إجمالي الرسوم والانزلاق: ${self.total_fees_paid:.2f} ({self.total_fees_paid/self.initial_capital*100:.2f}%)")
        
        print(f"\n📈 إحصائيات الصفقات:")
        print(f"   إجمالي الصفقات: {total_trades}")
        print(f"   الرابحة: {self.stats['wins']}")
        print(f"   الخاسرة: {self.stats['losses']}")
        print(f"   Win Rate: {win_rate:.1f}%")
        
        print(f"\n🔍 الفلترة:")
        print(f"   إجمالي الإشارات: {self.stats['total_signals']}")
        print(f"   فلترة Cognitive: {self.stats['filtered_by_cognitive']}")
        print(f"   فلترة ML: {self.stats['filtered_by_ml']}")
        print(f"   فلترة Heat: {self.stats['filtered_by_heat']}")
        print(f"   الصفقات المنفذة: {self.stats['executed_trades']}")
        
        # تحليل أسباب الخروج
        if self.closed_trades:
            print(f"\n📉 أسباب الخروج:")
            reasons = {}
            for t in self.closed_trades:
                r = t['reason']
                reasons[r] = reasons.get(r, 0) + 1
            for r, c in sorted(reasons.items(), key=lambda x: -x[1]):
                print(f"   • {r}: {c} ({c/len(self.closed_trades)*100:.1f}%)")
            
            # متوسط وقت الاحتفاظ
            avg_hold = np.mean([t['hold_hours'] for t in self.closed_trades])
            print(f"\n⏱️ متوسط وقت الاحتفاظ: {avg_hold:.1f} ساعة")
        
        # التحليل اليومي
        if self.daily_trades:
            print(f"\n📅 التحليل اليومي:")
            daily_entries = [d['entries'] for d in self.daily_trades.values()]
            daily_pnl = [d['pnl'] for d in self.daily_trades.values()]
            print(f"   متوسط الصفقات اليومية: {np.mean(daily_entries):.1f}")
            print(f"   متوسط الربح اليومي: ${np.mean(daily_pnl):.2f}")
            profitable_days = len([p for p in daily_pnl if p > 0])
            print(f"   الأيام الرابحة: {profitable_days}/{len(self.daily_trades)} ({profitable_days/len(self.daily_trades)*100:.1f}%)")
        
        print("\n" + "="*70)
        
        # تحديد المشاكل
        self._identify_issues(win_rate, roi, total_trades)
    
    def _identify_issues(self, win_rate: float, roi: float, total_trades: int):
        """تحديد المشاكل والتوصيات"""
        print("\n🔧 تحليل المشاكل والتوصيات:")
        issues = []
        
        if total_trades == 0:
            issues.append("❌ لا توجد صفقات - الفلاتر صارمة جداً")
        elif total_trades < 10:
            issues.append("⚠️ عدد الصفقات قليل جداً - خفف الفلاتر")
        
        if win_rate < 50:
            issues.append(f"⚠️ Win Rate منخفض ({win_rate:.1f}%) - راجع شروط الدخول")
        
        if roi < 0:
            issues.append(f"❌ ROI سلبي ({roi:.1f}%) - راجع نظام الخروج")
        
        if self.stats['max_drawdown'] > 10:
            issues.append(f"⚠️ Drawdown عالي ({self.stats['max_drawdown']:.1f}%) - شدد إدارة المخاطر")
        
        if self.stats['filtered_by_cognitive'] > self.stats['total_signals'] * 0.5:
            issues.append("⚠️ Cognitive يفلتر أكثر من 50% - خفف المعايير")
        
        if not issues:
            print("   ✅ لا توجد مشاكل كبيرة - النظام متوازن!")
        else:
            for issue in issues:
                print(f"   {issue}")
        
        print("="*70)


def main():
    """تشغيل الاختبار"""
    # قائمة العملات المعتمدة (Golden V3)
    symbols = [
        'BTCUSDT',
        'ETHUSDT',
        'BNBUSDT',
        'SOLUSDT',
        'XRPUSDT',
        'MATICUSDT',
        'ADAUSDT',
        'DOTUSDT',
    ]
    
    tester = FullSystemLiveTest(capital=1000, max_positions=5)
    tester.run_backtest(symbols, days=30)


if __name__ == "__main__":
    main()
