#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار خلفي شامل لنظام التداول المعرفي
رأس المال: 1000 USDT
حجم الصفقة: 100 USDT
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
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


@dataclass
class BacktestConfig:
    """إعدادات الاختبار الخلفي"""
    initial_capital: float = 1000.0
    position_size: float = 100.0
    max_positions: int = 5  # حد أقصى 5 صفقات (1000/100 = 10 لكن نحافظ على 50% احتياطي)
    commission_pct: float = 0.001  # 0.1% عمولة Binance
    slippage_pct: float = 0.0005  # 0.05% انزلاق سعري


@dataclass
class Trade:
    """صفقة واحدة"""
    symbol: str
    entry_time: datetime
    entry_price: float
    position_size: float
    strategy: str
    market_state: str
    asset_type: str
    objective: str
    stop_loss: float
    take_profit: float
    confidence: float
    risk_reward: float
    
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    is_open: bool = True


@dataclass
class BacktestResults:
    """نتائج الاختبار الخلفي"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_rr: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    
    # إحصائيات حسب القسم
    by_strategy: Dict = field(default_factory=dict)
    by_market_state: Dict = field(default_factory=dict)
    by_asset_type: Dict = field(default_factory=dict)
    by_objective: Dict = field(default_factory=dict)


class CognitiveBacktester:
    """نظام الاختبار الخلفي للتداول المعرفي"""
    
    SYMBOLS = [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
        'DOGE/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT', 'LINK/USDT',
        'MATIC/USDT', 'UNI/USDT', 'ATOM/USDT', 'LTC/USDT', 'FIL/USDT',
    ]
    
    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.engine = get_cognitive_trading_engine()
        self.exchange = ccxt.binance({'enableRateLimit': True}) if HAS_CCXT else None
        
        self.capital = self.config.initial_capital
        self.open_trades: List[Trade] = []
        self.closed_trades: List[Trade] = []
        self.equity_curve: List[float] = [self.config.initial_capital]
        
    def fetch_historical_data(self, symbol: str, timeframe: str = '4h', limit: int = 500) -> Optional[pd.DataFrame]:
        """جلب البيانات التاريخية"""
        if not self.exchange:
            return None
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"خطأ في جلب بيانات {symbol}: {e}")
            return None
    
    def run_backtest(self) -> BacktestResults:
        """تشغيل الاختبار الخلفي"""
        logger.info("=" * 70)
        logger.info("🚀 بدء الاختبار الخلفي")
        logger.info(f"💰 رأس المال: {self.config.initial_capital} USDT")
        logger.info(f"📊 حجم الصفقة: {self.config.position_size} USDT")
        logger.info(f"🎯 الحد الأقصى للمراكز: {self.config.max_positions}")
        logger.info("=" * 70)
        
        if not HAS_CCXT:
            logger.error("❌ ccxt غير متاح")
            return BacktestResults()
        
        # جلب البيانات لجميع العملات
        all_data = {}
        for symbol in self.SYMBOLS:
            df = self.fetch_historical_data(symbol, '4h', 500)
            if df is not None and len(df) >= 100:
                all_data[symbol] = df
                logger.info(f"✅ {symbol}: {len(df)} شمعة")
            else:
                logger.warning(f"⚠️ {symbol}: بيانات غير كافية")
        
        if not all_data:
            logger.error("❌ لا توجد بيانات متاحة")
            return BacktestResults()
        
        # محاكاة التداول على البيانات التاريخية
        min_len = min(len(df) for df in all_data.values())
        logger.info(f"\n📈 محاكاة التداول على {min_len} شمعة...")
        
        # نبدأ من الشمعة 100 لضمان وجود بيانات كافية للمؤشرات
        for i in range(100, min_len):
            # فحص الصفقات المفتوحة
            self._check_open_trades(all_data, i)
            
            # البحث عن فرص جديدة إذا كان هناك مساحة
            if len(self.open_trades) < self.config.max_positions:
                self._scan_for_entries(all_data, i)
            
            # تحديث منحنى رأس المال
            self._update_equity(all_data, i)
        
        # إغلاق جميع الصفقات المفتوحة في النهاية
        self._close_all_trades(all_data, min_len - 1)
        
        # حساب النتائج النهائية
        results = self._calculate_results()
        
        # طباعة التقرير
        self._print_report(results)
        
        return results
    
    def _check_open_trades(self, all_data: Dict, bar_index: int):
        """فحص الصفقات المفتوحة"""
        for trade in self.open_trades[:]:
            if trade.symbol not in all_data:
                continue
            
            df = all_data[trade.symbol]
            current_bar = df.iloc[bar_index]
            current_price = current_bar['close']
            high = current_bar['high']
            low = current_bar['low']
            
            exit_reason = None
            exit_price = None
            
            # فحص Stop Loss
            if low <= trade.stop_loss:
                exit_reason = "stop_loss"
                exit_price = trade.stop_loss
            # فحص Take Profit
            elif high >= trade.take_profit:
                exit_reason = "take_profit"
                exit_price = trade.take_profit
            
            if exit_reason:
                self._close_trade(trade, exit_price, exit_reason, df.index[bar_index])
    
    def _scan_for_entries(self, all_data: Dict, bar_index: int):
        """البحث عن فرص دخول جديدة"""
        for symbol, df in all_data.items():
            # تجنب فتح صفقة على نفس العملة
            if any(t.symbol == symbol for t in self.open_trades):
                continue
            
            # تحليل العملة
            df_slice = df.iloc[:bar_index+1].copy()
            result = self.engine.analyze(symbol, df_slice)
            
            if result.should_trade and result.decision == TradeDecision.EXECUTE:
                # فتح صفقة جديدة
                entry_price = df.iloc[bar_index]['close']
                
                # حساب الأسعار مع العمولة والانزلاق
                entry_price_adjusted = entry_price * (1 + self.config.slippage_pct)
                
                trade = Trade(
                    symbol=symbol,
                    entry_time=df.index[bar_index],
                    entry_price=entry_price_adjusted,
                    position_size=self.config.position_size,
                    strategy=result.strategy.strategy.value,
                    market_state=result.market_state.state.value,
                    asset_type=result.asset_class.asset_type.value,
                    objective=result.objective.objective.value,
                    stop_loss=result.stop_loss_price,
                    take_profit=result.take_profit_price,
                    confidence=result.confidence,
                    risk_reward=result.objective.risk_reward_ratio,
                )
                
                self.open_trades.append(trade)
                self.capital -= self.config.position_size * self.config.commission_pct
                
                logger.info(
                    f"📈 فتح صفقة: {symbol} @ {entry_price:.4f} | "
                    f"SL: {trade.stop_loss:.4f} | TP: {trade.take_profit:.4f} | "
                    f"Strategy: {trade.strategy}"
                )
                
                # التوقف إذا وصلنا للحد الأقصى
                if len(self.open_trades) >= self.config.max_positions:
                    break
    
    def _close_trade(self, trade: Trade, exit_price: float, exit_reason: str, exit_time: datetime):
        """إغلاق صفقة"""
        trade.exit_time = exit_time
        trade.exit_price = exit_price * (1 - self.config.slippage_pct)
        trade.exit_reason = exit_reason
        trade.is_open = False
        
        # حساب الربح/الخسارة
        price_change = (trade.exit_price - trade.entry_price) / trade.entry_price
        trade.pnl = trade.position_size * price_change
        trade.pnl_pct = price_change * 100
        
        # خصم العمولة
        trade.pnl -= trade.position_size * self.config.commission_pct
        
        self.capital += trade.position_size + trade.pnl
        
        self.open_trades.remove(trade)
        self.closed_trades.append(trade)
        
        emoji = "✅" if trade.pnl > 0 else "❌"
        logger.info(
            f"{emoji} إغلاق صفقة: {trade.symbol} | "
            f"الربح: {trade.pnl:.2f} USDT ({trade.pnl_pct:.2f}%) | "
            f"السبب: {exit_reason}"
        )
    
    def _close_all_trades(self, all_data: Dict, bar_index: int):
        """إغلاق جميع الصفقات المفتوحة"""
        for trade in self.open_trades[:]:
            if trade.symbol in all_data:
                df = all_data[trade.symbol]
                current_price = df.iloc[bar_index]['close']
                self._close_trade(trade, current_price, "end_of_backtest", df.index[bar_index])
    
    def _update_equity(self, all_data: Dict, bar_index: int):
        """تحديث منحنى رأس المال"""
        unrealized_pnl = 0
        for trade in self.open_trades:
            if trade.symbol in all_data:
                current_price = all_data[trade.symbol].iloc[bar_index]['close']
                price_change = (current_price - trade.entry_price) / trade.entry_price
                unrealized_pnl += trade.position_size * price_change
        
        total_equity = self.capital + unrealized_pnl
        self.equity_curve.append(total_equity)
    
    def _calculate_results(self) -> BacktestResults:
        """حساب النتائج النهائية"""
        results = BacktestResults()
        results.trades = self.closed_trades
        results.equity_curve = self.equity_curve
        results.total_trades = len(self.closed_trades)
        
        if results.total_trades == 0:
            return results
        
        # حساب الإحصائيات الأساسية
        wins = [t for t in self.closed_trades if t.pnl > 0]
        losses = [t for t in self.closed_trades if t.pnl <= 0]
        
        results.winning_trades = len(wins)
        results.losing_trades = len(losses)
        results.win_rate = (results.winning_trades / results.total_trades) * 100
        
        all_pnl = [t.pnl for t in self.closed_trades]
        results.total_pnl = sum(all_pnl)
        results.total_pnl_pct = (results.total_pnl / self.config.initial_capital) * 100
        
        if wins:
            results.avg_win = np.mean([t.pnl for t in wins])
            results.best_trade = max([t.pnl for t in wins])
        if losses:
            results.avg_loss = np.mean([t.pnl for t in losses])
            results.worst_trade = min([t.pnl for t in losses])
        
        # حساب R:R المتوسط
        results.avg_rr = np.mean([t.risk_reward for t in self.closed_trades])
        
        # حساب Profit Factor
        gross_profit = sum([t.pnl for t in wins]) if wins else 0
        gross_loss = abs(sum([t.pnl for t in losses])) if losses else 1
        results.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # حساب Max Drawdown
        equity = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak * 100
        results.max_drawdown = np.max(drawdown)
        
        # حساب Sharpe Ratio
        returns = np.diff(equity) / equity[:-1]
        if len(returns) > 1 and np.std(returns) > 0:
            results.sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
        
        # إحصائيات حسب القسم
        self._calculate_section_stats(results)
        
        return results
    
    def _calculate_section_stats(self, results: BacktestResults):
        """حساب إحصائيات كل قسم"""
        # حسب الاستراتيجية
        for trade in self.closed_trades:
            key = trade.strategy
            if key not in results.by_strategy:
                results.by_strategy[key] = {'trades': 0, 'wins': 0, 'pnl': 0}
            results.by_strategy[key]['trades'] += 1
            if trade.pnl > 0:
                results.by_strategy[key]['wins'] += 1
            results.by_strategy[key]['pnl'] += trade.pnl
        
        # حسب حالة السوق
        for trade in self.closed_trades:
            key = trade.market_state
            if key not in results.by_market_state:
                results.by_market_state[key] = {'trades': 0, 'wins': 0, 'pnl': 0}
            results.by_market_state[key]['trades'] += 1
            if trade.pnl > 0:
                results.by_market_state[key]['wins'] += 1
            results.by_market_state[key]['pnl'] += trade.pnl
        
        # حسب نوع الأصل
        for trade in self.closed_trades:
            key = trade.asset_type
            if key not in results.by_asset_type:
                results.by_asset_type[key] = {'trades': 0, 'wins': 0, 'pnl': 0}
            results.by_asset_type[key]['trades'] += 1
            if trade.pnl > 0:
                results.by_asset_type[key]['wins'] += 1
            results.by_asset_type[key]['pnl'] += trade.pnl
        
        # حسب الهدف
        for trade in self.closed_trades:
            key = trade.objective
            if key not in results.by_objective:
                results.by_objective[key] = {'trades': 0, 'wins': 0, 'pnl': 0}
            results.by_objective[key]['trades'] += 1
            if trade.pnl > 0:
                results.by_objective[key]['wins'] += 1
            results.by_objective[key]['pnl'] += trade.pnl
    
    def _print_report(self, results: BacktestResults):
        """طباعة التقرير النهائي"""
        logger.info("\n" + "=" * 70)
        logger.info("📊 التقرير النهائي - الاختبار الخلفي")
        logger.info("=" * 70)
        
        # الملخص العام
        logger.info("\n📈 الملخص العام:")
        logger.info(f"  💰 رأس المال الأولي: {self.config.initial_capital:.2f} USDT")
        logger.info(f"  💵 رأس المال النهائي: {self.capital:.2f} USDT")
        logger.info(f"  📊 إجمالي الربح/الخسارة: {results.total_pnl:.2f} USDT ({results.total_pnl_pct:.2f}%)")
        logger.info(f"  📉 الحد الأقصى للسحب: {results.max_drawdown:.2f}%")
        
        # إحصائيات الصفقات
        logger.info("\n📋 إحصائيات الصفقات:")
        logger.info(f"  🔢 إجمالي الصفقات: {results.total_trades}")
        logger.info(f"  ✅ الصفقات الرابحة: {results.winning_trades} ({results.win_rate:.1f}%)")
        logger.info(f"  ❌ الصفقات الخاسرة: {results.losing_trades}")
        logger.info(f"  📊 متوسط الربح: {results.avg_win:.2f} USDT")
        logger.info(f"  📉 متوسط الخسارة: {results.avg_loss:.2f} USDT")
        logger.info(f"  🎯 أفضل صفقة: {results.best_trade:.2f} USDT")
        logger.info(f"  💔 أسوأ صفقة: {results.worst_trade:.2f} USDT")
        
        # مقاييس الأداء
        logger.info("\n📏 مقاييس الأداء:")
        logger.info(f"  📊 Profit Factor: {results.profit_factor:.2f}")
        logger.info(f"  📈 Sharpe Ratio: {results.sharpe_ratio:.2f}")
        logger.info(f"  🎯 متوسط R:R: {results.avg_rr:.2f}")
        
        # تفاصيل حسب الاستراتيجية
        logger.info("\n🎲 الأداء حسب الاستراتيجية:")
        for strategy, stats in results.by_strategy.items():
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            logger.info(f"  {strategy}:")
            logger.info(f"    الصفقات: {stats['trades']} | الرابحة: {stats['wins']} ({win_rate:.1f}%) | الربح: {stats['pnl']:.2f} USDT")
        
        # تفاصيل حسب حالة السوق
        logger.info("\n📊 الأداء حسب حالة السوق:")
        for state, stats in results.by_market_state.items():
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            logger.info(f"  {state}:")
            logger.info(f"    الصفقات: {stats['trades']} | الرابحة: {stats['wins']} ({win_rate:.1f}%) | الربح: {stats['pnl']:.2f} USDT")
        
        # تفاصيل حسب نوع الأصل
        logger.info("\n💎 الأداء حسب نوع الأصل:")
        for asset_type, stats in results.by_asset_type.items():
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            logger.info(f"  {asset_type}:")
            logger.info(f"    الصفقات: {stats['trades']} | الرابحة: {stats['wins']} ({win_rate:.1f}%) | الربح: {stats['pnl']:.2f} USDT")
        
        # تفاصيل حسب الهدف
        logger.info("\n🎯 الأداء حسب الهدف:")
        for objective, stats in results.by_objective.items():
            win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
            logger.info(f"  {objective}:")
            logger.info(f"    الصفقات: {stats['trades']} | الرابحة: {stats['wins']} ({win_rate:.1f}%) | الربح: {stats['pnl']:.2f} USDT")
        
        # قائمة الصفقات
        logger.info("\n📝 تفاصيل الصفقات:")
        logger.info("-" * 90)
        for i, trade in enumerate(results.trades, 1):
            emoji = "✅" if trade.pnl > 0 else "❌"
            logger.info(
                f"{emoji} #{i} | {trade.symbol} | {trade.strategy} | "
                f"Entry: {trade.entry_price:.4f} | Exit: {trade.exit_price:.4f} | "
                f"PnL: {trade.pnl:.2f} USDT ({trade.pnl_pct:.2f}%) | "
                f"Reason: {trade.exit_reason}"
            )
        
        logger.info("\n" + "=" * 70)
        
        # التقييم النهائي
        if results.total_pnl > 0:
            logger.info("🎉 النظام مربح!")
        else:
            logger.info("⚠️ النظام يحتاج تحسين")
        
        logger.info("=" * 70)


def main():
    config = BacktestConfig(
        initial_capital=1000.0,
        position_size=100.0,
        max_positions=5,
    )
    
    backtester = CognitiveBacktester(config)
    results = backtester.run_backtest()
    
    return results


if __name__ == '__main__':
    main()
