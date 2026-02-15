#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cognitive Trading System - 6-Month Realistic Backtest
=====================================================

Realistic simulation including:
- Bar-by-bar walk-forward (no future data leakage)
- Commission: 0.1% per trade (Binance spot)
- Slippage: 0.05% per trade
- Execution delay: 1 bar (entry on next bar open after signal)
- SL/TP checked against high/low (realistic fills)
- Max 1 position per coin, max 5 total positions
- $10,000 starting balance
- Position sizing from cognitive system (5-15%)

Coins: ETH, BNB, SOL, AVAX, NEAR, SUI, ARB, APT, INJ, LINK
Timeframe: 4h execution, 1h confirmation
Period: 6 months
"""

import sys
import os
import time
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

sys.path.insert(0, '/Users/anr/Desktop/trading_ai_bot-1')
os.chdir('/Users/anr/Desktop/trading_ai_bot-1')
from dotenv import load_dotenv
load_dotenv()

# Suppress verbose logging during backtest
logging.basicConfig(level=logging.WARNING)
for name in ['backend', 'urllib3', 'requests']:
    logging.getLogger(name).setLevel(logging.WARNING)

from backend.cognitive.cognitive_orchestrator import (
    CognitiveOrchestrator, CognitiveAction, EntryStrategy, CognitiveDecision
)
from backend.cognitive.multi_exit_engine import (
    MultiExitEngine, ExitReason, ExitUrgency
)
from backend.cognitive.market_surveillance_engine import (
    MarketSurveillanceEngine, MarketQuality, MarketPhase
)

# ===== CONFIGURATION =====
INITIAL_BALANCE = 10000.0
COMMISSION_PCT = 0.001      # 0.1% Binance spot
SLIPPAGE_PCT = 0.0005       # 0.05% realistic slippage
MAX_POSITIONS = 5
MAX_HOLD_BARS = 18          # 18 bars * 4h = 72 hours max
LOOKBACK_BARS = 60          # Minimum bars needed for indicators

COINS = [
    'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'AVAXUSDT', 'NEARUSDT',
    'SUIUSDT', 'ARBUSDT', 'APTUSDT', 'INJUSDT', 'LINKUSDT'
]

COIN_CATEGORIES = {
    'Large Cap': ['ETHUSDT', 'BNBUSDT', 'SOLUSDT'],
    'Mid Cap': ['AVAXUSDT', 'NEARUSDT', 'LINKUSDT', 'APTUSDT'],
    'Small Cap': ['SUIUSDT', 'ARBUSDT', 'INJUSDT'],
}

# ===== DATA FETCHER =====

def fetch_binance_klines(symbol: str, interval: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    """Fetch klines from Binance API with pagination"""
    all_data = []
    current_start = start_ms
    
    while current_start < end_ms:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': current_start,
            'endTime': end_ms,
            'limit': 1000
        }
        
        for attempt in range(3):
            try:
                resp = requests.get(url, params=params, timeout=15)
                if resp.status_code == 429:
                    wait = int(resp.headers.get('Retry-After', 60))
                    print(f"  Rate limit. Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    print(f"  ERROR fetching {symbol}: {e}")
                    return pd.DataFrame()
        
        if not data:
            break
        
        all_data.extend(data)
        current_start = data[-1][6] + 1  # close_time + 1ms
        
        if len(data) < 1000:
            break
        
        time.sleep(0.15)  # Rate limit respect
    
    if not all_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
        df[col] = pd.to_numeric(df[col])
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
    df.set_index('timestamp', inplace=True)
    
    return df


def fetch_6months_data(coins: list) -> Dict[str, pd.DataFrame]:
    """Fetch 6 months of 4h data for all coins"""
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=183)  # ~6 months
    
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)
    
    print(f"\n{'='*60}")
    print(f"FETCHING 6-MONTH DATA")
    print(f"Period: {start_dt.strftime('%Y-%m-%d')} → {end_dt.strftime('%Y-%m-%d')}")
    print(f"{'='*60}")
    
    all_data = {}
    for coin in coins:
        print(f"  Fetching {coin}...", end=" ", flush=True)
        df = fetch_binance_klines(coin, '4h', start_ms, end_ms)
        if len(df) > 0:
            all_data[coin] = df
            print(f"{len(df)} bars OK")
        else:
            print("FAILED - skipping")
        time.sleep(0.3)
    
    return all_data


# ===== TRADE TRACKING =====

@dataclass
class Trade:
    """Single trade record"""
    symbol: str
    strategy: str
    entry_bar: int
    entry_time: datetime
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size_usd: float
    position_size_pct: float
    confidence: float
    market_state: str
    market_quality: str
    market_phase: str
    opportunity_score: float
    risk_score: float
    
    # Filled on exit
    exit_bar: int = 0
    exit_time: Optional[datetime] = None
    exit_price: float = 0.0
    exit_reason: str = ""
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    commission_paid: float = 0.0
    slippage_cost: float = 0.0
    hold_bars: int = 0
    is_win: bool = False


@dataclass
class BacktestState:
    """Current backtest state"""
    balance: float = INITIAL_BALANCE
    equity_curve: List[float] = field(default_factory=list)
    open_positions: Dict[str, Trade] = field(default_factory=dict)
    closed_trades: List[Trade] = field(default_factory=list)
    signals_generated: int = 0
    signals_rejected: int = 0
    rejection_reasons: Dict[str, int] = field(default_factory=dict)
    bars_processed: int = 0


# ===== BACKTESTER =====

class CognitiveBacktester:
    """
    Realistic bar-by-bar backtester for the Cognitive Trading System
    """
    
    def __init__(self):
        # Fresh instances (not singletons) to avoid state leakage
        self.orchestrator = CognitiveOrchestrator({
            'exit': {'max_loss_pct': 0.02, 'max_hold_hours': 72},
            'min_opportunity_score': 60,
            'max_risk_score': 58,
            'min_entry_confidence': 72,
        })
        self.exit_engine = MultiExitEngine({
            'max_loss_pct': 0.02,
            'max_hold_hours': 72
        })
        self.state = BacktestState()
    
    def run(self, data: Dict[str, pd.DataFrame]) -> BacktestState:
        """Run full 6-month backtest"""
        
        # Find common date range
        all_indices = []
        for df in data.values():
            all_indices.extend(df.index.tolist())
        
        # Use the first coin's index as the timeline
        reference_coin = list(data.keys())[0]
        timeline = data[reference_coin].index[LOOKBACK_BARS:]
        total_bars = len(timeline)
        
        print(f"\n{'='*60}")
        print(f"RUNNING BACKTEST")
        print(f"Bars: {total_bars} | Coins: {len(data)} | Balance: ${INITIAL_BALANCE:,.0f}")
        print(f"Commission: {COMMISSION_PCT*100:.2f}% | Slippage: {SLIPPAGE_PCT*100:.3f}%")
        print(f"{'='*60}")
        
        last_pct = 0
        check_interval = max(1, total_bars // 4)  # Check entries every N bars
        
        for bar_idx in range(LOOKBACK_BARS, LOOKBACK_BARS + total_bars):
            self.state.bars_processed += 1
            
            # Progress
            pct = int((self.state.bars_processed / total_bars) * 100)
            if pct >= last_pct + 10:
                open_pos = len(self.state.open_positions)
                closed = len(self.state.closed_trades)
                print(f"  [{pct:3d}%] Bar {self.state.bars_processed}/{total_bars} | "
                      f"Balance: ${self.state.balance:,.2f} | "
                      f"Open: {open_pos} | Closed: {closed}")
                last_pct = pct
            
            # ===== 1. MANAGE OPEN POSITIONS (every bar) =====
            symbols_to_close = []
            for symbol, trade in list(self.state.open_positions.items()):
                if symbol not in data:
                    continue
                
                coin_df = data[symbol]
                if bar_idx >= len(coin_df):
                    continue
                
                bar = coin_df.iloc[bar_idx]
                current_high = bar['high']
                current_low = bar['low']
                current_close = bar['close']
                hold_bars = bar_idx - trade.entry_bar
                
                exit_price = None
                exit_reason = ""
                
                # 1a. Check SL hit (using low of bar)
                if current_low <= trade.stop_loss:
                    exit_price = trade.stop_loss
                    exit_reason = "STOP_LOSS"
                
                # 1b. Check TP hit (using high of bar)
                elif current_high >= trade.take_profit:
                    exit_price = trade.take_profit
                    exit_reason = "TAKE_PROFIT"
                
                # 1c. Max hold time exceeded
                elif hold_bars >= MAX_HOLD_BARS:
                    exit_price = current_close
                    exit_reason = "MAX_HOLD_TIME"
                
                # 1d. Cognitive exit analysis (every 2 bars = 8h)
                elif hold_bars > 2 and hold_bars % 2 == 0:
                    try:
                        df_slice = coin_df.iloc[max(0, bar_idx-100):bar_idx+1].copy()
                        if len(df_slice) >= 50:
                            pos_data = {
                                'entry_price': trade.entry_price,
                                'hold_hours': hold_bars * 4,
                                'quantity': trade.position_size_usd / trade.entry_price,
                            }
                            exit_dec = self.exit_engine.evaluate_exit(df_slice, pos_data)
                            
                            if exit_dec.should_exit and exit_dec.urgency in [ExitUrgency.CRITICAL, ExitUrgency.HIGH]:
                                exit_price = current_close
                                exit_reason = f"COGNITIVE_{exit_dec.primary_reason.value.upper()}"
                    except Exception:
                        pass
                
                # Execute exit
                if exit_price is not None:
                    self._close_trade(trade, bar_idx, coin_df.index[bar_idx], 
                                     exit_price, exit_reason)
                    symbols_to_close.append(symbol)
            
            # Remove closed positions
            for s in symbols_to_close:
                del self.state.open_positions[s]
            
            # ===== 2. SCAN FOR NEW ENTRIES (every 2 bars = 8h) =====
            if self.state.bars_processed % 2 == 0:
                if len(self.state.open_positions) < MAX_POSITIONS:
                    self._scan_entries(data, bar_idx)
            
            # Record equity
            equity = self.state.balance
            for symbol, trade in self.state.open_positions.items():
                if symbol in data and bar_idx < len(data[symbol]):
                    current = data[symbol].iloc[bar_idx]['close']
                    unrealized = (current - trade.entry_price) / trade.entry_price
                    equity += trade.position_size_usd * (1 + unrealized)
            self.state.equity_curve.append(equity)
        
        # Close all remaining positions at last bar
        for symbol, trade in list(self.state.open_positions.items()):
            if symbol in data:
                last_bar = min(bar_idx, len(data[symbol]) - 1)
                last_price = data[symbol].iloc[last_bar]['close']
                self._close_trade(trade, last_bar, data[symbol].index[last_bar],
                                 last_price, "BACKTEST_END")
        self.state.open_positions.clear()
        
        return self.state
    
    def _scan_entries(self, data: Dict[str, pd.DataFrame], bar_idx: int):
        """Scan all coins for entry signals"""
        for symbol in data:
            if symbol in self.state.open_positions:
                continue
            if len(self.state.open_positions) >= MAX_POSITIONS:
                break
            
            coin_df = data[symbol]
            if bar_idx >= len(coin_df):
                continue
            
            # Slice data up to current bar (no future leakage)
            df_4h = coin_df.iloc[max(0, bar_idx-LOOKBACK_BARS):bar_idx+1].copy()
            
            if len(df_4h) < 50:
                continue
            
            # Volume filter
            avg_vol = df_4h['volume'].tail(20).mean()
            recent_vol = df_4h['volume'].iloc[-1]
            if recent_vol < avg_vol * 0.5:
                self._record_rejection("LOW_VOLUME")
                continue
            
            try:
                # Cognitive entry analysis
                decision = self.orchestrator.analyze_entry(
                    symbol=symbol, df_4h=df_4h, df_1h=None
                )
                
                self.state.signals_generated += 1
                
                if decision.action == CognitiveAction.ENTER:
                    # Calculate position size
                    size_pct = decision.position_size_pct or 0.10
                    position_usd = self.state.balance * size_pct
                    
                    if position_usd < 50:  # Min position
                        self._record_rejection("INSUFFICIENT_BALANCE")
                        continue
                    
                    # Entry on NEXT bar open (execution delay)
                    if bar_idx + 1 < len(coin_df):
                        next_bar = coin_df.iloc[bar_idx + 1]
                        entry_price = next_bar['open']
                    else:
                        entry_price = decision.entry_price
                    
                    # Apply slippage (buy higher)
                    entry_price *= (1 + SLIPPAGE_PCT)
                    
                    # Commission on entry
                    entry_commission = position_usd * COMMISSION_PCT
                    
                    # Recalculate SL/TP from actual entry
                    sl_pct = abs(decision.entry_price - decision.stop_loss) / decision.entry_price if decision.entry_price else 0.02
                    tp_pct = abs(decision.take_profit - decision.entry_price) / decision.entry_price if decision.entry_price else 0.045
                    
                    stop_loss = entry_price * (1 - sl_pct)
                    take_profit = entry_price * (1 + tp_pct)
                    
                    # Deduct from balance
                    self.state.balance -= position_usd
                    
                    trade = Trade(
                        symbol=symbol,
                        strategy=decision.entry_strategy.value,
                        entry_bar=bar_idx + 1,
                        entry_time=coin_df.index[bar_idx],
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        position_size_usd=position_usd,
                        position_size_pct=size_pct,
                        confidence=decision.confidence,
                        market_state=decision.market_state,
                        market_quality=decision.market_quality,
                        market_phase=decision.market_phase,
                        opportunity_score=decision.opportunity_score,
                        risk_score=decision.risk_score,
                        commission_paid=entry_commission,
                    )
                    
                    self.state.open_positions[symbol] = trade
                else:
                    self.state.signals_rejected += 1
                    reason = "STAY_OUT"
                    if "Confidence" in decision.reasoning:
                        reason = "LOW_CONFIDENCE"
                    elif "not tradeable" in decision.reasoning:
                        reason = "MARKET_UNTRADEABLE"
                    elif "Unfavorable" in decision.reasoning:
                        reason = "UNFAVORABLE_STATE"
                    elif "No valid" in decision.reasoning:
                        reason = "NO_STRATEGY_MATCH"
                    elif "Insufficient" in decision.reasoning:
                        reason = "INSUFFICIENT_DATA"
                    self._record_rejection(reason)
                    
            except Exception:
                pass
    
    def _close_trade(self, trade: Trade, bar_idx: int, bar_time, 
                     exit_price: float, reason: str):
        """Close a trade and record results"""
        # Apply slippage (sell lower)
        exit_price *= (1 - SLIPPAGE_PCT)
        
        # Commission on exit
        exit_commission = trade.position_size_usd * COMMISSION_PCT
        
        # Calculate PnL
        gross_pnl_pct = (exit_price - trade.entry_price) / trade.entry_price
        gross_pnl_usd = trade.position_size_usd * gross_pnl_pct
        
        total_commission = trade.commission_paid + exit_commission
        total_slippage = trade.position_size_usd * SLIPPAGE_PCT * 2
        
        net_pnl_usd = gross_pnl_usd - total_commission
        net_pnl_pct = net_pnl_usd / trade.position_size_usd
        
        # Return capital + PnL to balance
        self.state.balance += trade.position_size_usd + net_pnl_usd
        
        trade.exit_bar = bar_idx
        trade.exit_time = bar_time
        trade.exit_price = exit_price
        trade.exit_reason = reason
        trade.pnl_usd = net_pnl_usd
        trade.pnl_pct = net_pnl_pct
        trade.commission_paid = total_commission
        trade.slippage_cost = total_slippage
        trade.hold_bars = bar_idx - trade.entry_bar
        trade.is_win = net_pnl_usd > 0
        
        self.state.closed_trades.append(trade)
    
    def _record_rejection(self, reason: str):
        """Record why a signal was rejected"""
        self.state.rejection_reasons[reason] = \
            self.state.rejection_reasons.get(reason, 0) + 1


# ===== ANALYSIS =====

def analyze_results(state: BacktestState, data: Dict[str, pd.DataFrame]):
    """Comprehensive analysis of backtest results"""
    trades = state.closed_trades
    
    if not trades:
        print("\n  NO TRADES EXECUTED. System too conservative or no opportunities.")
        print(f"  Signals generated: {state.signals_generated}")
        print(f"  Signals rejected: {state.signals_rejected}")
        print(f"  Rejection reasons: {state.rejection_reasons}")
        return
    
    total = len(trades)
    wins = [t for t in trades if t.is_win]
    losses = [t for t in trades if not t.is_win]
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = win_count / total * 100
    
    total_pnl = sum(t.pnl_usd for t in trades)
    total_pnl_pct = total_pnl / INITIAL_BALANCE * 100
    total_commission = sum(t.commission_paid for t in trades)
    total_slippage = sum(t.slippage_cost for t in trades)
    
    avg_win = np.mean([t.pnl_pct * 100 for t in wins]) if wins else 0
    avg_loss = np.mean([t.pnl_pct * 100 for t in losses]) if losses else 0
    max_win = max([t.pnl_pct * 100 for t in trades]) if trades else 0
    max_loss = min([t.pnl_pct * 100 for t in trades]) if trades else 0
    
    avg_hold = np.mean([t.hold_bars * 4 for t in trades])
    
    # Profit factor
    gross_profit = sum(t.pnl_usd for t in wins) if wins else 0
    gross_loss = abs(sum(t.pnl_usd for t in losses)) if losses else 1
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Max drawdown from equity curve
    equity = state.equity_curve
    peak = equity[0]
    max_dd = 0
    for e in equity:
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100
        if dd > max_dd:
            max_dd = dd
    
    # Final balance
    final_balance = state.balance
    
    print(f"\n{'='*70}")
    print(f"  COGNITIVE TRADING SYSTEM - 6-MONTH BACKTEST RESULTS")
    print(f"{'='*70}")
    
    print(f"\n  --- OVERALL PERFORMANCE ---")
    print(f"  Initial Balance:    ${INITIAL_BALANCE:>12,.2f}")
    print(f"  Final Balance:      ${final_balance:>12,.2f}")
    print(f"  Total P&L:          ${total_pnl:>12,.2f} ({total_pnl_pct:+.2f}%)")
    print(f"  Total Commission:   ${total_commission:>12,.2f}")
    print(f"  Total Slippage:     ${total_slippage:>12,.2f}")
    print(f"  Net After Costs:    ${total_pnl - total_commission:>12,.2f}")
    
    print(f"\n  --- TRADE STATISTICS ---")
    print(f"  Total Trades:       {total}")
    print(f"  Wins:               {win_count} ({win_rate:.1f}%)")
    print(f"  Losses:             {loss_count} ({100-win_rate:.1f}%)")
    print(f"  Profit Factor:      {profit_factor:.2f}")
    print(f"  Avg Win:            {avg_win:+.2f}%")
    print(f"  Avg Loss:           {avg_loss:+.2f}%")
    print(f"  Best Trade:         {max_win:+.2f}%")
    print(f"  Worst Trade:        {max_loss:+.2f}%")
    print(f"  Avg Hold Time:      {avg_hold:.1f} hours")
    print(f"  Max Drawdown:       {max_dd:.2f}%")
    
    # By strategy
    print(f"\n  --- BY STRATEGY ---")
    strategies = set(t.strategy for t in trades)
    for strat in sorted(strategies):
        strat_trades = [t for t in trades if t.strategy == strat]
        strat_wins = [t for t in strat_trades if t.is_win]
        strat_wr = len(strat_wins) / len(strat_trades) * 100 if strat_trades else 0
        strat_pnl = sum(t.pnl_usd for t in strat_trades)
        avg_conf = np.mean([t.confidence for t in strat_trades])
        print(f"  {strat:<25s} | Trades: {len(strat_trades):3d} | "
              f"WR: {strat_wr:5.1f}% | PnL: ${strat_pnl:>8,.2f} | "
              f"Avg Conf: {avg_conf:.0f}%")
    
    # By coin
    print(f"\n  --- BY COIN ---")
    coins_traded = set(t.symbol for t in trades)
    for coin in sorted(coins_traded):
        coin_trades = [t for t in trades if t.symbol == coin]
        coin_wins = [t for t in coin_trades if t.is_win]
        coin_wr = len(coin_wins) / len(coin_trades) * 100 if coin_trades else 0
        coin_pnl = sum(t.pnl_usd for t in coin_trades)
        print(f"  {coin:<12s} | Trades: {len(coin_trades):3d} | "
              f"WR: {coin_wr:5.1f}% | PnL: ${coin_pnl:>8,.2f}")
    
    # By category
    print(f"\n  --- BY CATEGORY ---")
    for cat, cat_coins in COIN_CATEGORIES.items():
        cat_trades = [t for t in trades if t.symbol in cat_coins]
        if not cat_trades:
            print(f"  {cat:<12s} | No trades")
            continue
        cat_wins = [t for t in cat_trades if t.is_win]
        cat_wr = len(cat_wins) / len(cat_trades) * 100
        cat_pnl = sum(t.pnl_usd for t in cat_trades)
        cat_avg_hold = np.mean([t.hold_bars * 4 for t in cat_trades])
        print(f"  {cat:<12s} | Trades: {len(cat_trades):3d} | "
              f"WR: {cat_wr:5.1f}% | PnL: ${cat_pnl:>8,.2f} | "
              f"Avg Hold: {cat_avg_hold:.0f}h")
    
    # By market state
    print(f"\n  --- BY MARKET STATE ---")
    states = set(t.market_state for t in trades)
    for ms in sorted(states):
        ms_trades = [t for t in trades if t.market_state == ms]
        ms_wins = [t for t in ms_trades if t.is_win]
        ms_wr = len(ms_wins) / len(ms_trades) * 100
        ms_pnl = sum(t.pnl_usd for t in ms_trades)
        print(f"  {ms:<15s} | Trades: {len(ms_trades):3d} | "
              f"WR: {ms_wr:5.1f}% | PnL: ${ms_pnl:>8,.2f}")
    
    # By market quality
    print(f"\n  --- BY MARKET QUALITY ---")
    qualities = set(t.market_quality for t in trades)
    for mq in sorted(qualities):
        mq_trades = [t for t in trades if t.market_quality == mq]
        mq_wins = [t for t in mq_trades if t.is_win]
        mq_wr = len(mq_wins) / len(mq_trades) * 100
        mq_pnl = sum(t.pnl_usd for t in mq_trades)
        print(f"  {mq:<15s} | Trades: {len(mq_trades):3d} | "
              f"WR: {mq_wr:5.1f}% | PnL: ${mq_pnl:>8,.2f}")
    
    # Exit reason analysis
    print(f"\n  --- EXIT REASONS ---")
    reasons = {}
    for t in trades:
        r = t.exit_reason
        if r not in reasons:
            reasons[r] = {'count': 0, 'wins': 0, 'pnl': 0.0}
        reasons[r]['count'] += 1
        reasons[r]['pnl'] += t.pnl_usd
        if t.is_win:
            reasons[r]['wins'] += 1
    
    for reason, stats in sorted(reasons.items(), key=lambda x: x[1]['count'], reverse=True):
        wr = stats['wins'] / stats['count'] * 100 if stats['count'] > 0 else 0
        print(f"  {reason:<30s} | Count: {stats['count']:3d} | "
              f"WR: {wr:5.1f}% | PnL: ${stats['pnl']:>8,.2f}")
    
    # Rejection analysis
    print(f"\n  --- SIGNAL REJECTIONS ---")
    print(f"  Total signals analyzed: {state.signals_generated}")
    print(f"  Total rejected: {state.signals_rejected}")
    for reason, count in sorted(state.rejection_reasons.items(), key=lambda x: x[1], reverse=True):
        print(f"  {reason:<25s}: {count:>5d}")
    
    # Failure analysis
    print(f"\n  --- FAILURE ANALYSIS ---")
    if losses:
        # Worst trades
        worst = sorted(losses, key=lambda t: t.pnl_pct)[:5]
        print(f"  Top 5 worst trades:")
        for i, t in enumerate(worst, 1):
            print(f"    {i}. {t.symbol} | {t.strategy} | PnL: {t.pnl_pct*100:+.2f}% | "
                  f"Exit: {t.exit_reason} | Hold: {t.hold_bars*4}h | "
                  f"Quality: {t.market_quality}")
        
        # Common failure patterns
        loss_by_strategy = {}
        for t in losses:
            if t.strategy not in loss_by_strategy:
                loss_by_strategy[t.strategy] = []
            loss_by_strategy[t.strategy].append(t)
        
        print(f"\n  Loss patterns by strategy:")
        for strat, strat_losses in sorted(loss_by_strategy.items(), 
                                            key=lambda x: len(x[1]), reverse=True):
            avg_loss_pct = np.mean([t.pnl_pct * 100 for t in strat_losses])
            avg_conf = np.mean([t.confidence for t in strat_losses])
            exit_reasons = {}
            for t in strat_losses:
                exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1
            top_exit = max(exit_reasons, key=exit_reasons.get)
            print(f"    {strat}: {len(strat_losses)} losses | "
                  f"Avg loss: {avg_loss_pct:.2f}% | Avg conf: {avg_conf:.0f}% | "
                  f"Main exit: {top_exit} ({exit_reasons[top_exit]}x)")
    
    # Monthly breakdown
    print(f"\n  --- MONTHLY PERFORMANCE ---")
    monthly = {}
    for t in trades:
        month = t.entry_time.strftime('%Y-%m')
        if month not in monthly:
            monthly[month] = {'trades': 0, 'wins': 0, 'pnl': 0.0}
        monthly[month]['trades'] += 1
        monthly[month]['pnl'] += t.pnl_usd
        if t.is_win:
            monthly[month]['wins'] += 1
    
    for month in sorted(monthly):
        m = monthly[month]
        wr = m['wins'] / m['trades'] * 100 if m['trades'] > 0 else 0
        print(f"  {month} | Trades: {m['trades']:3d} | "
              f"WR: {wr:5.1f}% | PnL: ${m['pnl']:>8,.2f}")
    
    # Recommendations
    print(f"\n  --- RECOMMENDATIONS ---")
    
    if win_rate < 45:
        print(f"  WARNING: Win rate {win_rate:.1f}% is below 45%. Confidence thresholds need increasing.")
    if profit_factor < 1.0:
        print(f"  WARNING: Profit factor {profit_factor:.2f} < 1.0. System is losing money.")
    if max_dd > 15:
        print(f"  WARNING: Max drawdown {max_dd:.1f}% is high. Reduce position sizes.")
    if avg_hold < 8:
        print(f"  NOTE: Average hold {avg_hold:.0f}h is short. Consider wider TP targets.")
    
    # Category-specific recommendations
    for cat, cat_coins in COIN_CATEGORIES.items():
        cat_trades = [t for t in trades if t.symbol in cat_coins]
        if not cat_trades:
            continue
        cat_wr = len([t for t in cat_trades if t.is_win]) / len(cat_trades) * 100
        if cat_wr < 40:
            print(f"  {cat}: Win rate {cat_wr:.0f}% is low. Consider tighter filters for this category.")
    
    if profit_factor >= 1.3 and win_rate >= 50:
        print(f"\n  SYSTEM IS PROFITABLE. Profit factor {profit_factor:.2f}, WR {win_rate:.1f}%")
    elif profit_factor >= 1.0:
        print(f"\n  SYSTEM IS MARGINALLY PROFITABLE. Needs optimization.")
    else:
        print(f"\n  SYSTEM IS UNPROFITABLE. Major tuning needed.")
    
    print(f"\n{'='*70}")


# ===== MAIN =====

if __name__ == '__main__':
    print("=" * 70)
    print("  COGNITIVE TRADING SYSTEM - 6-MONTH REALISTIC BACKTEST")
    print("  Commission: 0.1% | Slippage: 0.05% | Execution delay: 1 bar")
    print("=" * 70)
    
    # 1. Fetch data
    data = fetch_6months_data(COINS)
    
    if not data:
        print("ERROR: Could not fetch data. Check API connection.")
        sys.exit(1)
    
    print(f"\nData loaded: {len(data)} coins")
    for coin, df in data.items():
        print(f"  {coin}: {len(df)} bars | "
              f"{df.index[0].strftime('%Y-%m-%d')} → {df.index[-1].strftime('%Y-%m-%d')}")
    
    # 2. Run backtest
    backtester = CognitiveBacktester()
    state = backtester.run(data)
    
    # 3. Analyze
    analyze_results(state, data)
