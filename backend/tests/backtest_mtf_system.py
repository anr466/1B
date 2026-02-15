#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtesting MTF Reversal System
اختبار خلفي شامل لنظام MTF على بيانات حقيقية

رأس المال: 1000 USDT
حجم الصفقة: 100 USDT
الهدف: اختبار النظام على عملات متنوعة وحساب العوائد
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple

from cognitive import (
    get_market_state_detector,
    get_asset_classifier,
    get_pattern_objective_analyzer,
    get_strategy_selector,
    get_dynamic_parameters_engine,
    get_reasoning_engine,
    get_smart_exit_integration,
    MarketState
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class BacktestEngine:
    """محرك الاختبار الخلفي"""
    
    def __init__(self, initial_capital: float = 1000, position_size: float = 100):
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.current_capital = initial_capital
        self.trades = []
        self.open_positions = []
        
        # الأنظمة المعرفية
        self.market_detector = get_market_state_detector()
        self.asset_classifier = get_asset_classifier()
        self.pattern_analyzer = get_pattern_objective_analyzer()
        self.strategy_selector = get_strategy_selector()
        self.params_engine = get_dynamic_parameters_engine()
        self.reasoning_engine = get_reasoning_engine()
        self.smart_exit = get_smart_exit_integration()
        
        logger.info(f"💰 رأس المال الأولي: {initial_capital} USDT")
        logger.info(f"📊 حجم الصفقة: {position_size} USDT")
    
    def fetch_historical_data(self, symbol: str, timeframe: str, days: int = 30):
        """جلب البيانات التاريخية"""
        try:
            exchange = ccxt.binance()
            since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
            
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            
            if not ohlcv or len(ohlcv) == 0:
                logger.warning(f"لا توجد بيانات لـ {symbol} {timeframe}")
                return pd.DataFrame()  # إرجاع DataFrame فارغ بدلاً من None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # حساب المؤشرات
            df = self._add_indicators(df)
            
            logger.info(f"✅ تم جلب {len(df)} شمعة لـ {symbol} ({timeframe})")
            
            return df
        except Exception as e:
            logger.error(f"خطأ في جلب {symbol} {timeframe}: {e}")
            return pd.DataFrame()  # إرجاع DataFrame فارغ بدلاً من None
    
    def _add_indicators(self, df):
        """إضافة المؤشرات الفنية"""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        # ADX
        df['adx'] = self._calculate_adx(df)
        
        # Support/Resistance
        df['support'] = df['low'].rolling(window=20).min()
        df['resistance'] = df['high'].rolling(window=20).max()
        
        return df
    
    def _calculate_adx(self, df, period=14):
        """حساب ADX"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm > 0] = 0
        
        tr = pd.concat([high - low, 
                       abs(high - close.shift()), 
                       abs(low - close.shift())], axis=1).max(axis=1)
        
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (abs(minus_dm).rolling(period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()
        
        return adx
    
    def analyze_entry(self, symbol: str, df_1h: pd.DataFrame, df_15m: pd.DataFrame, 
                     current_idx: int) -> Dict:
        """تحليل فرصة الدخول"""
        try:
            # استخدام البيانات حتى current_idx فقط (لمحاكاة الواقع)
            df_1h_slice = df_1h.iloc[:current_idx+1].copy()
            # 1H = 60 min, 15m = 15 min → نسبة 4:1
            df_15m_slice = df_15m.iloc[:(current_idx+1)*4].copy() if len(df_15m) >= (current_idx+1)*4 else df_15m.copy()
            
            if len(df_1h_slice) < 50 or len(df_15m_slice) < 50:
                return {'execute': False, 'reason': 'بيانات غير كافية'}
            
            # التحليل الكامل
            market_state = self.market_detector.detect_state(df_1h_slice, symbol)
            asset_class = self.asset_classifier.classify_asset(symbol, df_1h_slice)
            
            # تحليل الهدف مع MTF
            objective = self.pattern_analyzer.determine_objective(
                market_state=market_state,
                asset_class=asset_class,
                df=df_1h_slice,
                df_15m=df_15m_slice,
                symbol=symbol
            )
            
            # اختيار الاستراتيجية
            strategy = self.strategy_selector.select_strategy(
                market_state=market_state,
                asset_class=asset_class,
                objective=objective,
                df=df_1h_slice,  # إضافة المعامل المفقود
                symbol=symbol
            )
            
            # المعلمات الديناميكية
            params = self.params_engine.calculate_parameters(
                market_state=market_state,
                asset_class=asset_class,
                objective=objective,
                strategy=strategy,
                symbol=symbol
            )
            
            # التفكير النهائي
            reasoning = self.reasoning_engine.reason_before_trade(
                market_state=market_state,
                asset_class=asset_class,
                objective=objective,
                strategy=strategy,
                parameters=params,
                symbol=symbol
            )
            
            # قرار التنفيذ
            if reasoning.decision == 'EXECUTE':
                current_price = df_1h_slice['close'].iloc[-1]
                
                return {
                    'execute': True,
                    'price': current_price,
                    'stop_loss': current_price * (1 - params.stop_loss_pct),
                    'take_profit': current_price * (1 + params.take_profit_pct),
                    'confidence': objective.confidence,
                    'mtf_confirmed': objective.reversal_confirmed if hasattr(objective, 'reversal_confirmed') else False,
                    'mtf_confidence': objective.reversal_confidence if hasattr(objective, 'reversal_confidence') else 0,
                    'entry_quality': objective.entry_quality if hasattr(objective, 'entry_quality') else 0,
                    'reasoning': reasoning.reasoning_text,
                    'market_state': market_state.state.value,
                    'objective': objective.objective.value,
                    'strategy': strategy.strategy.value,
                    'risk_reward': objective.risk_reward_ratio
                }
            else:
                return {
                    'execute': False,
                    'reason': reasoning.rejection_reasons[0] if reasoning.rejection_reasons else 'لا يوجد سبب'
                }
                
        except Exception as e:
            logger.error(f"خطأ في تحليل الدخول: {e}")
            return {'execute': False, 'reason': f'خطأ: {e}'}
    
    def simulate_trade(self, symbol: str, entry_signal: Dict, df_1h: pd.DataFrame, 
                      entry_idx: int) -> Dict:
        """محاكاة تنفيذ الصفقة"""
        entry_price = entry_signal['price']
        stop_loss = entry_signal['stop_loss']
        take_profit = entry_signal['take_profit']
        
        # محاكاة الصفقة على البيانات المستقبلية
        max_hold_hours = 72  # 3 أيام كحد أقصى
        
        for i in range(entry_idx + 1, min(entry_idx + max_hold_hours, len(df_1h))):
            current_price = df_1h['close'].iloc[i]
            current_high = df_1h['high'].iloc[i]
            current_low = df_1h['low'].iloc[i]
            
            # فحص Stop Loss
            if current_low <= stop_loss:
                pnl = stop_loss - entry_price
                pnl_pct = (pnl / entry_price) * 100
                return {
                    'exit_price': stop_loss,
                    'exit_reason': 'Stop Loss',
                    'pnl': pnl * (self.position_size / entry_price),
                    'pnl_pct': pnl_pct,
                    'hold_hours': i - entry_idx,
                    'exit_idx': i
                }
            
            # فحص Take Profit
            if current_high >= take_profit:
                pnl = take_profit - entry_price
                pnl_pct = (pnl / entry_price) * 100
                return {
                    'exit_price': take_profit,
                    'exit_reason': 'Take Profit',
                    'pnl': pnl * (self.position_size / entry_price),
                    'pnl_pct': pnl_pct,
                    'hold_hours': i - entry_idx,
                    'exit_idx': i
                }
        
        # إغلاق عند نهاية الفترة
        final_price = df_1h['close'].iloc[min(entry_idx + max_hold_hours, len(df_1h) - 1)]
        pnl = final_price - entry_price
        pnl_pct = (pnl / entry_price) * 100
        
        return {
            'exit_price': final_price,
            'exit_reason': 'Max Hold Time',
            'pnl': pnl * (self.position_size / entry_price),
            'pnl_pct': pnl_pct,
            'hold_hours': max_hold_hours,
            'exit_idx': min(entry_idx + max_hold_hours, len(df_1h) - 1)
        }
    
    def backtest_symbol(self, symbol: str, days: int = 30):
        """اختبار عملة واحدة"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 اختبار {symbol}")
        logger.info(f"{'='*80}")
        
        # جلب البيانات
        df_1h = self.fetch_historical_data(symbol, '1h', days)
        df_15m = self.fetch_historical_data(symbol, '15m', days)
        
        if df_1h.empty or df_15m.empty or len(df_1h) < 100 or len(df_15m) < 200:
            logger.error(f"❌ بيانات غير كافية لـ {symbol} (1H: {len(df_1h)}, 15m: {len(df_15m)})")
            return []
        
        logger.info(f"📊 البيانات: {len(df_1h)} شمعة (1H), {len(df_15m)} شمعة (15m)")
        
        symbol_trades = []
        
        # المرور على البيانات التاريخية
        for i in range(50, len(df_1h) - 72):  # ترك مساحة للتنفيذ
            # تحليل فرصة الدخول
            entry_signal = self.analyze_entry(symbol, df_1h, df_15m, i)
            
            if entry_signal['execute']:
                # محاكاة الصفقة
                trade_result = self.simulate_trade(symbol, entry_signal, df_1h, i)
                
                # حفظ تفاصيل الصفقة
                trade = {
                    'symbol': symbol,
                    'entry_time': df_1h['timestamp'].iloc[i],
                    'entry_price': entry_signal['price'],
                    'exit_time': df_1h['timestamp'].iloc[trade_result['exit_idx']],
                    'exit_price': trade_result['exit_price'],
                    'exit_reason': trade_result['exit_reason'],
                    'pnl': trade_result['pnl'],
                    'pnl_pct': trade_result['pnl_pct'],
                    'hold_hours': trade_result['hold_hours'],
                    'stop_loss': entry_signal['stop_loss'],
                    'take_profit': entry_signal['take_profit'],
                    'confidence': entry_signal['confidence'],
                    'mtf_confirmed': entry_signal['mtf_confirmed'],
                    'mtf_confidence': entry_signal['mtf_confidence'],
                    'entry_quality': entry_signal['entry_quality'],
                    'market_state': entry_signal['market_state'],
                    'objective': entry_signal['objective'],
                    'strategy': entry_signal['strategy'],
                    'risk_reward': entry_signal['risk_reward'],
                    'position_size': self.position_size
                }
                
                symbol_trades.append(trade)
                
                # تحديث رأس المال
                self.current_capital += trade_result['pnl']
                
                logger.info(f"\n✅ صفقة #{len(symbol_trades)}")
                logger.info(f"   الدخول: {trade['entry_time'].strftime('%Y-%m-%d %H:%M')} @ {trade['entry_price']:.4f}")
                logger.info(f"   الخروج: {trade['exit_time'].strftime('%Y-%m-%d %H:%M')} @ {trade['exit_price']:.4f}")
                logger.info(f"   السبب: {trade['exit_reason']}")
                logger.info(f"   الربح/الخسارة: {trade['pnl']:.2f} USDT ({trade['pnl_pct']:.2f}%)")
                logger.info(f"   الثقة: {trade['confidence']:.0f}% | MTF: {trade['mtf_confidence']:.0f}% | جودة: {trade['entry_quality']:.0f}%")
                logger.info(f"   المدة: {trade['hold_hours']} ساعة")
                
                # تجاوز فترة الانتظار
                i = trade_result['exit_idx'] + 24  # انتظار 24 ساعة بعد الخروج
        
        logger.info(f"\n📊 إجمالي صفقات {symbol}: {len(symbol_trades)}")
        return symbol_trades
    
    def run_backtest(self, symbols: List[str], days: int = 30):
        """تشغيل الاختبار على عدة عملات"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 بدء الاختبار الخلفي")
        logger.info(f"{'='*80}")
        logger.info(f"العملات: {', '.join(symbols)}")
        logger.info(f"الفترة: {days} يوم")
        
        all_trades = []
        
        for symbol in symbols:
            trades = self.backtest_symbol(symbol, days)
            all_trades.extend(trades)
        
        self.trades = all_trades
        return self.generate_report()
    
    def generate_report(self):
        """إنشاء تقرير شامل"""
        if not self.trades:
            logger.warning("لا توجد صفقات للتحليل!")
            return {}
        
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        total_pnl_pct = (total_pnl / self.initial_capital) * 100
        
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
        
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        
        avg_hold = np.mean([t['hold_hours'] for t in self.trades])
        
        # أفضل وأسوأ صفقة
        best_trade = max(self.trades, key=lambda x: x['pnl'])
        worst_trade = min(self.trades, key=lambda x: x['pnl'])
        
        report = {
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_hold_hours': avg_hold,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'trades': self.trades
        }
        
        # طباعة التقرير
        self._print_report(report)
        
        return report
    
    def _print_report(self, report):
        """طباعة التقرير"""
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 التقرير النهائي - Backtest Results")
        logger.info(f"{'='*80}")
        
        logger.info(f"\n💰 رأس المال:")
        logger.info(f"   الأولي: {report['initial_capital']:.2f} USDT")
        logger.info(f"   النهائي: {report['final_capital']:.2f} USDT")
        logger.info(f"   الربح/الخسارة: {report['total_pnl']:.2f} USDT ({report['total_pnl_pct']:.2f}%)")
        
        logger.info(f"\n📈 الإحصائيات:")
        logger.info(f"   إجمالي الصفقات: {report['total_trades']}")
        logger.info(f"   صفقات رابحة: {report['winning_trades']} ({report['win_rate']:.1f}%)")
        logger.info(f"   صفقات خاسرة: {report['losing_trades']} ({100-report['win_rate']:.1f}%)")
        logger.info(f"   متوسط الربح: {report['avg_win']:.2f} USDT")
        logger.info(f"   متوسط الخسارة: {report['avg_loss']:.2f} USDT")
        logger.info(f"   متوسط المدة: {report['avg_hold_hours']:.1f} ساعة")
        
        logger.info(f"\n🏆 أفضل صفقة:")
        best = report['best_trade']
        logger.info(f"   {best['symbol']}: {best['pnl']:.2f} USDT ({best['pnl_pct']:.2f}%)")
        logger.info(f"   {best['entry_time'].strftime('%Y-%m-%d')} → {best['exit_time'].strftime('%Y-%m-%d')}")
        
        logger.info(f"\n💀 أسوأ صفقة:")
        worst = report['worst_trade']
        logger.info(f"   {worst['symbol']}: {worst['pnl']:.2f} USDT ({worst['pnl_pct']:.2f}%)")
        logger.info(f"   {worst['entry_time'].strftime('%Y-%m-%d')} → {worst['exit_time'].strftime('%Y-%m-%d')}")
        
        logger.info(f"\n{'='*80}")


def main():
    """الدالة الرئيسية"""
    
    # إعدادات الاختبار
    INITIAL_CAPITAL = 1000  # USDT
    POSITION_SIZE = 100     # USDT لكل صفقة
    BACKTEST_DAYS = 30      # آخر 30 يوم
    
    # العملات للاختبار (متنوعة)
    SYMBOLS = [
        'BTC/USDT',    # Large cap
        'ETH/USDT',    # Large cap
        'BNB/USDT',    # Large cap
        'SOL/USDT',    # Mid cap
        'MATIC/USDT',  # Mid cap
    ]
    
    # إنشاء محرك الاختبار
    engine = BacktestEngine(
        initial_capital=INITIAL_CAPITAL,
        position_size=POSITION_SIZE
    )
    
    # تشغيل الاختبار
    report = engine.run_backtest(SYMBOLS, BACKTEST_DAYS)
    
    return report


if __name__ == "__main__":
    main()
