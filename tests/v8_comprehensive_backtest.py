#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V8 Comprehensive Backtest — Fixed-Risk + Multi-TP + Smart Entry/Exit
=====================================================================
- Fixed $-risk per trade (no compounding distortion)
- V8 Entry: market structure + confluence filter + blocked losers
- V8 Exit: Multi-TP partial exits + ATR trailing + smart SL
- Realistic: Commission + Slippage + H/L for SL checks
"""

import sys
import os
import json
import time
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from backend.strategies.scalping_v7_engine import ScalpingV7Engine, V7_CONFIG, _ema, _rsi, _macd, _atr, _bbands, _supertrend, _adx_calc

logging.basicConfig(level=logging.WARNING, format='%(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# 1. DATA FETCHER
# ============================================================

def fetch_binance_klines(symbol: str, interval: str = '1h',
                         days: int = 60, limit_per_req: int = 1000) -> pd.DataFrame:
    url = "https://api.binance.com/api/v3/klines"
    all_data = []
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
    current_start = start_time

    while current_start < end_time:
        params = {
            'symbol': symbol, 'interval': interval,
            'startTime': current_start, 'endTime': end_time,
            'limit': limit_per_req
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  ⚠️ Error fetching {symbol}: {e}")
            break
        if not data:
            break
        all_data.extend(data)
        current_start = data[-1][0] + 1
        if len(data) < limit_per_req:
            break
        time.sleep(0.2)

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]


# ============================================================
# 2. V8 CONFIGURATION
# ============================================================

V8_CONFIG = {
    **V7_CONFIG,

    # === V8 ENTRY: MINIMAL FILTERS (keep V7's high trade count) ===
    'min_confluence': 4,
    'min_timing': 1,
    'require_quality': True,
    'use_cognitive_entry': True,

    # Block only verified losers
    'blocked_cognitive': ['pullback', 'vol_expand'],
    'blocked_short': ['st_flip_bear', 'rsi_reject', 'macd_x_bear'],
    'v8_block_breakdown': False,       # Keep breakdown (was +$82 in V7)
    'v8_block_trend_short': False,

    # V8: Light structure filter (don't over-filter)
    'v8_require_structure': False,     # DISABLED — was removing too many trades
    'v8_structure_lookback': 20,

    # V8: Light quality filters
    'v8_min_adx': 15,                 # Lowered from 20 (many good trades at 15-20)
    'v8_rsi_long_max': 72,            # Relaxed from 68
    'v8_rsi_short_min': 28,           # Relaxed from 32
    'v8_min_volume_ratio': 0.7,       # Relaxed

    # === V8 EXIT: MULTI-TP + NO EARLY CUT ===
    'v8_use_multi_tp': True,
    'v8_tp1_pct': 0.008,              # TP1: +0.8% → close 30%
    'v8_tp1_close': 0.30,
    'v8_tp2_pct': 0.016,              # TP2: +1.6% → close 30% + move SL to entry
    'v8_tp2_close': 0.30,
    'v8_tp3_pct': 0.025,              # TP3: +2.5% → trailing handles rest
    'v8_tp3_close': 0.20,

    # SL: slightly wider than V7
    'sl_pct': 0.010,                  # Fallback SL: 1.0% (vs V7's 0.8%)
    'use_atr_sl': True,
    'atr_sl_multiplier': 2.0,

    # Trailing: same as V7 (proven 94% WR)
    'trailing_activation': 0.004,      # Same as V7
    'trailing_distance': 0.003,        # Same as V7
    'breakeven_trigger': 0.005,        # Move to BE at +0.5%

    # Time-based: DISABLE EARLY_CUT (saves $441)
    'early_cut_hours': 0,              # DISABLED — was 0% WR, -$441
    'early_cut_loss': 0,
    'stagnant_hours': 6,               # 6h (moderate)
    'stagnant_threshold': 0.002,
    'max_hold_hours': 14,              # 14h (slightly longer than 12)

    # Fixed risk sizing
    'v8_fixed_risk_per_trade': 60.0,
    'v8_max_risk_pct': 0.10,
}

# V8.2: More aggressive Multi-TP + tighter trailing for higher PF
V8_AGGRESSIVE_CONFIG = {
    **V8_CONFIG,
    'v8_tp1_pct': 0.006,              # TP1 earlier: +0.6% → close 35%
    'v8_tp1_close': 0.35,
    'v8_tp2_pct': 0.012,              # TP2: +1.2% → close 30%
    'v8_tp2_close': 0.30,
    'v8_tp3_pct': 0.020,              # TP3: +2.0% → close 20%
    'v8_tp3_close': 0.20,
    'trailing_activation': 0.003,      # Activate earlier
    'trailing_distance': 0.0025,       # Tighter trailing
    'breakeven_trigger': 0.004,        # BE earlier
}

# V8.3: Conservative — LONG only (SHORT has lower WR in V7)
V8_LONG_ONLY_CONFIG = {
    **V8_CONFIG,
    'v8_long_only': True,             # Only LONG trades
    'v8_tp1_pct': 0.010,
    'v8_tp1_close': 0.30,
    'v8_tp2_pct': 0.020,
    'v8_tp2_close': 0.30,
    'v8_tp3_pct': 0.030,
    'v8_tp3_close': 0.20,
}


# ============================================================
# 3. V8 ENGINE - Enhanced Entry + Multi-TP Exit
# ============================================================

class V8Engine:
    """
    V8 Trading Engine with:
    - Market structure entry filter
    - Blocked losing strategies
    - Multi-TP partial exit system
    - ATR-based adaptive SL
    - Trend-aware trailing
    """

    def __init__(self, config: Dict = None):
        self.config = {**V8_CONFIG, **(config or {})}
        # Reuse V7 for indicator preparation
        self._v7 = ScalpingV7Engine(self.config)

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add all indicators (reuse V7 + add V8 extras)"""
        df = self._v7.prepare_data(df)
        if df is None or len(df) < 60:
            return df

        # V8: Add market structure markers
        df = self._add_market_structure(df)
        return df

    def _add_market_structure(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Higher Highs/Higher Lows and Lower Highs/Lower Lows markers"""
        df = df.copy()
        lookback = self.config.get('v8_structure_lookback', 20)

        # Swing highs and lows (simple: local max/min over 5 bars)
        df['swing_high'] = df['high'].rolling(5, center=True).max() == df['high']
        df['swing_low'] = df['low'].rolling(5, center=True).min() == df['low']

        # Market structure: HH/HL for uptrend, LH/LL for downtrend
        structure = []
        last_high = 0
        last_low = float('inf')
        hh_count = 0
        ll_count = 0

        for i in range(len(df)):
            h = df['high'].iloc[i]
            l = df['low'].iloc[i]

            if df['swing_high'].iloc[i] and h > last_high:
                hh_count += 1
                last_high = h
            elif df['swing_high'].iloc[i] and h < last_high:
                hh_count = max(0, hh_count - 1)

            if df['swing_low'].iloc[i] and l < last_low:
                ll_count += 1
                last_low = l
            elif df['swing_low'].iloc[i] and l > last_low:
                ll_count = max(0, ll_count - 1)

            if hh_count >= 2:
                structure.append('BULLISH')
            elif ll_count >= 2:
                structure.append('BEARISH')
            else:
                structure.append('NEUTRAL')

        df['market_structure'] = structure
        return df

    def get_4h_trend(self, df: pd.DataFrame, idx: int = -1) -> str:
        return self._v7.get_4h_trend(df, idx)

    def detect_entry(self, df: pd.DataFrame, trend: str, idx: int = -1) -> Optional[Dict]:
        """V8 entry detection — keeps V7's logic, adds light filters"""
        if idx == -1:
            idx = len(df) - 2
        if idx < 55:
            return None
        if trend == 'NEUTRAL':
            return None

        # V8.3: Long-only mode
        if self.config.get('v8_long_only', False) and trend == 'DOWN':
            return None

        row = df.iloc[idx]

        # V8: Light market structure filter (only if enabled)
        if self.config.get('v8_require_structure', False):
            ms = row.get('market_structure', 'NEUTRAL')
            if trend == 'UP' and ms == 'BEARISH':
                return None
            if trend == 'DOWN' and ms == 'BULLISH':
                return None

        # V8: Light RSI filter — avoid extreme overbought/oversold entries
        rsi_val = row.get('rsi', 50)
        if not pd.isna(rsi_val):
            if trend == 'UP' and rsi_val > self.config.get('v8_rsi_long_max', 72):
                return None
            if trend == 'DOWN' and rsi_val < self.config.get('v8_rsi_short_min', 28):
                return None

        # Use V7's entry detection (cognitive + fallback) — proven system
        signal = self._v7.detect_entry(df, trend, idx)

        if signal is None:
            return None

        strategy = signal.get('strategy', '')

        # V8: Block only confirmed losing strategies
        if self.config.get('v8_block_breakdown', False) and strategy == 'breakdown':
            return None

        # V8: Improve SL placement with structure-aware ATR
        signal = self._improve_sl(df, idx, signal)

        return signal

    def _improve_sl(self, df: pd.DataFrame, idx: int, signal: Dict) -> Dict:
        """Place SL at structure level + ATR buffer"""
        row = df.iloc[idx]
        entry = signal['entry_price']
        atr = row.get('atr', 0)

        if pd.isna(atr) or atr <= 0:
            return signal

        mult = self.config.get('atr_sl_multiplier', 2.0)

        if signal['side'] == 'LONG':
            # SL below recent swing low or ATR-based, whichever is wider
            lookback = min(10, idx)
            recent_low = df['low'].iloc[idx - lookback:idx + 1].min()
            atr_sl = entry - atr * mult
            structure_sl = recent_low - atr * 0.3  # Small buffer below swing low

            # Use the tighter of the two, but not tighter than min SL
            sl = max(atr_sl, structure_sl)
            min_sl = entry * (1 - self.config['sl_pct'])
            sl = max(sl, min_sl)
            signal['stop_loss'] = sl

        else:  # SHORT
            lookback = min(10, idx)
            recent_high = df['high'].iloc[idx - lookback:idx + 1].max()
            atr_sl = entry + atr * mult
            structure_sl = recent_high + atr * 0.3

            sl = min(atr_sl, structure_sl)
            max_sl = entry * (1 + self.config['sl_pct'])
            sl = min(sl, max_sl)
            signal['stop_loss'] = sl

        return signal

    def check_exit_signal(self, df: pd.DataFrame, position: Dict) -> Dict:
        """
        V8 exit logic: Multi-TP + trailing + reversal detection.

        position keys:
            entry_price, side, peak, trail, sl, hold_hours,
            tp1_hit, tp2_hit, tp3_hit, remaining_pct (1.0 = full position)
        """
        if df is None or len(df) < 3:
            return {'should_exit': False, 'reason': 'HOLD'}

        idx = len(df) - 1
        row = df.iloc[idx]
        hi, lo, cl = row['high'], row['low'], row['close']

        entry = position['entry_price']
        side = position.get('side', 'LONG')
        peak = position.get('peak', entry)
        trail = position.get('trail', 0)
        sl = position.get('sl', 0)
        remaining = position.get('remaining_pct', 1.0)
        hold_hours = position.get('hold_hours', 0)

        updated = {}
        partial_exits = []

        # ---- STOP LOSS (always first) ----
        if side == 'LONG':
            if hi > peak:
                peak = hi
                updated['peak'] = peak
            if sl > 0 and lo <= sl:
                return {'should_exit': True, 'reason': 'STOP_LOSS', 'exit_price': sl,
                        'exit_pct': remaining, 'updated': updated}
        else:
            if lo < peak:
                peak = lo
                updated['peak'] = peak
            if sl > 0 and hi >= sl:
                return {'should_exit': True, 'reason': 'STOP_LOSS', 'exit_price': sl,
                        'exit_pct': remaining, 'updated': updated}

        # ---- CALCULATE PNL ----
        if side == 'LONG':
            pnl_pct = (cl - entry) / entry
            pnl_peak = (peak - entry) / entry
        else:
            pnl_pct = (entry - cl) / entry
            pnl_peak = (entry - peak) / entry

        # ---- MULTI-TP SYSTEM ----
        if self.config.get('v8_use_multi_tp', True):
            # TP1
            tp1_pct = self.config.get('v8_tp1_pct', 0.008)
            if not position.get('tp1_hit', False) and pnl_pct >= tp1_pct:
                close_pct = self.config.get('v8_tp1_close', 0.40)
                actual_close = remaining * close_pct
                remaining -= actual_close
                updated['tp1_hit'] = True
                updated['remaining_pct'] = remaining
                # Move SL to breakeven
                if side == 'LONG':
                    updated['sl'] = entry * 1.001
                else:
                    updated['sl'] = entry * 0.999
                partial_exits.append(('TP1', actual_close, cl))

            # TP2
            tp2_pct = self.config.get('v8_tp2_pct', 0.015)
            if not position.get('tp2_hit', False) and position.get('tp1_hit', False) and pnl_pct >= tp2_pct:
                close_pct = self.config.get('v8_tp2_close', 0.30)
                actual_close = remaining * close_pct
                remaining -= actual_close
                updated['tp2_hit'] = True
                updated['remaining_pct'] = remaining
                partial_exits.append(('TP2', actual_close, cl))

            # TP3
            tp3_pct = self.config.get('v8_tp3_pct', 0.025)
            if not position.get('tp3_hit', False) and position.get('tp2_hit', False) and pnl_pct >= tp3_pct:
                close_pct = self.config.get('v8_tp3_close', 0.30)
                actual_close = remaining * close_pct
                remaining -= actual_close
                updated['tp3_hit'] = True
                updated['remaining_pct'] = remaining
                partial_exits.append(('TP3', actual_close, cl))

        # If partial exits happened, return them
        if partial_exits:
            total_closed = sum(pe[1] for pe in partial_exits)
            # If all closed
            if remaining <= 0.01:
                return {'should_exit': True, 'reason': f'TP_FULL',
                        'exit_price': cl, 'exit_pct': 1.0, 'updated': updated,
                        'partial_exits': partial_exits}
            return {'should_exit': True, 'reason': f'{partial_exits[-1][0]}',
                    'exit_price': cl, 'exit_pct': total_closed, 'updated': updated,
                    'partial_exits': partial_exits, 'is_partial': True}

        # ---- BREAKEVEN TRIGGER ----
        be_trigger = self.config.get('breakeven_trigger', 0.006)
        if be_trigger > 0 and pnl_pct >= be_trigger:
            if side == 'LONG' and sl < entry:
                updated['sl'] = entry * 1.001
            elif side == 'SHORT' and sl > entry:
                updated['sl'] = entry * 0.999

        # ---- TRAILING STOP ----
        trail_act = self.config.get('trailing_activation', 0.005)
        trail_dist = self.config.get('trailing_distance', 0.003)

        # Progressive tightening
        if pnl_peak >= 0.025:
            trail_dist = min(trail_dist, 0.0015)
        elif pnl_peak >= 0.02:
            trail_dist = min(trail_dist, 0.002)
        elif pnl_peak >= 0.015:
            trail_dist = min(trail_dist, 0.0025)
        elif pnl_peak >= 0.01:
            trail_dist = min(trail_dist, 0.003)

        if pnl_peak >= trail_act:
            if side == 'LONG':
                ts = peak * (1 - trail_dist)
                if ts > trail:
                    trail = ts
                    updated['trail'] = trail
                if trail > 0 and lo <= trail:
                    return {'should_exit': True, 'reason': 'TRAILING',
                            'exit_price': trail, 'exit_pct': remaining, 'updated': updated}
            else:
                ts = peak * (1 + trail_dist)
                if trail == 0 or ts < trail:
                    trail = ts
                    updated['trail'] = trail
                if trail > 0 and hi >= trail:
                    return {'should_exit': True, 'reason': 'TRAILING',
                            'exit_price': trail, 'exit_pct': remaining, 'updated': updated}

        # ---- REVERSAL EXIT (only if in profit > 0.3%) ----
        if idx >= 2 and pnl_pct > 0.003:
            prev = df.iloc[idx - 1]
            rev_score = 0

            if side == 'LONG':
                if not pd.isna(row.get('st_dir')) and not pd.isna(prev.get('st_dir')):
                    if prev['st_dir'] == 1 and row['st_dir'] == -1:
                        rev_score += 3
                if prev.get('bull', True) and not row.get('bull', True):
                    if row.get('body', 0) > prev.get('body', 0):
                        rev_score += 2
                if not pd.isna(row.get('macd_l')) and not pd.isna(prev.get('macd_l')):
                    if prev['macd_l'] > prev['macd_s'] and row['macd_l'] < row['macd_s']:
                        rev_score += 2
            else:
                if not pd.isna(row.get('st_dir')) and not pd.isna(prev.get('st_dir')):
                    if prev['st_dir'] == -1 and row['st_dir'] == 1:
                        rev_score += 3
                if not prev.get('bull', False) and row.get('bull', False):
                    if row.get('body', 0) > prev.get('body', 0):
                        rev_score += 2
                if not pd.isna(row.get('macd_l')) and not pd.isna(prev.get('macd_l')):
                    if prev['macd_l'] < prev['macd_s'] and row['macd_l'] > row['macd_s']:
                        rev_score += 2

            if rev_score >= 3:
                return {'should_exit': True, 'reason': 'REVERSAL',
                        'exit_price': cl, 'exit_pct': remaining, 'updated': updated}

        # ---- TIME-BASED EXITS ----
        if hold_hours >= self.config['max_hold_hours']:
            return {'should_exit': True, 'reason': 'MAX_HOLD',
                    'exit_price': cl, 'exit_pct': remaining, 'updated': updated}

        stagnant_hours = self.config.get('stagnant_hours', 8)
        stagnant_threshold = self.config.get('stagnant_threshold', 0.002)
        if hold_hours >= stagnant_hours and abs(pnl_pct) < stagnant_threshold:
            return {'should_exit': True, 'reason': 'STAGNANT',
                    'exit_price': cl, 'exit_pct': remaining, 'updated': updated}

        # ---- HOLD ----
        return {
            'should_exit': False, 'reason': 'HOLD',
            'exit_price': cl, 'updated': updated,
            'pnl_pct': pnl_pct * 100, 'trail_level': trail, 'peak': peak,
        }


# ============================================================
# 4. FIXED-RISK BACKTESTER
# ============================================================

class FixedRiskBacktester:
    """
    Backtester with FIXED $ risk per trade to prevent compounding distortion.
    Accurately measures strategy quality independent of position sizing.
    """

    def __init__(self, engine, config: Dict = None, initial_balance: float = 1000.0):
        self.config = config or V8_CONFIG
        self.engine = engine
        self.initial_balance = initial_balance
        self.balance = initial_balance

        self.open_positions: List[Dict] = []
        self.closed_trades: List[Dict] = []
        self.equity_curve: List[Dict] = []

        self.commission_pct = self.config.get('commission_pct', 0.001)
        self.slippage_pct = self.config.get('slippage_pct', 0.0005)
        self.fixed_risk = self.config.get('v8_fixed_risk_per_trade', 60.0)
        self.max_positions = self.config.get('max_positions', 5)

    def run(self, symbol: str, df: pd.DataFrame) -> Dict:
        if df is None or len(df) < 80:
            return {'error': f'Insufficient data for {symbol}'}

        df_prepared = self.engine.prepare_data(df)
        if df_prepared is None:
            return {'error': f'Failed to prepare data for {symbol}'}

        for i in range(60, len(df_prepared)):
            current_bar = df_prepared.iloc[i]
            bar_time = current_bar.get('timestamp', i)

            unrealized = self._calc_unrealized_pnl(current_bar['close'])
            self.equity_curve.append({
                'time': bar_time, 'balance': self.balance,
                'equity': self.balance + unrealized,
                'open_positions': len(self.open_positions)
            })

            self._check_exits(df_prepared, i, symbol)

            if len(self.open_positions) < self.max_positions:
                trend = self.engine.get_4h_trend(df_prepared, i - 1)
                signal = self.engine.detect_entry(df_prepared, trend, i - 1)

                if signal:
                    entry_price = current_bar['open']
                    if signal['side'] == 'LONG':
                        entry_price *= (1 + self.slippage_pct)
                    else:
                        entry_price *= (1 - self.slippage_pct)
                    self._open_position(symbol, signal, entry_price, bar_time, i)

        return self._generate_report(symbol)

    def _open_position(self, symbol, signal, entry_price, bar_time, bar_idx):
        # Fixed risk: always $60 regardless of balance
        position_value = min(self.fixed_risk, self.balance * self.config.get('v8_max_risk_pct', 0.10))
        if position_value < 10:
            return

        quantity = position_value / entry_price
        entry_commission = position_value * self.commission_pct
        self.balance -= entry_commission

        sl = signal.get('stop_loss', 0)
        if sl <= 0:
            if signal['side'] == 'LONG':
                sl = entry_price * (1 - self.config['sl_pct'])
            else:
                sl = entry_price * (1 + self.config['sl_pct'])

        position = {
            'symbol': symbol, 'side': signal['side'],
            'entry_price': entry_price, 'quantity': quantity,
            'position_value': position_value, 'stop_loss': sl,
            'trailing_stop': 0, 'peak': entry_price,
            'entry_time': bar_time, 'entry_bar': bar_idx,
            'entry_commission': entry_commission,
            'signal_strategy': signal.get('strategy', 'unknown'),
            'signal_score': signal.get('score', 0),
            'signal_confidence': signal.get('confidence', 0),
            'signal_type': signal.get('signal_type', ''),
            'hold_bars': 0,
            'tp1_hit': False, 'tp2_hit': False, 'tp3_hit': False,
            'remaining_pct': 1.0,
            'realized_partial': 0.0,
        }
        self.open_positions.append(position)

    def _check_exits(self, df, bar_idx, symbol):
        positions_to_close = []
        positions_to_update = []

        for pos in self.open_positions:
            pos['hold_bars'] += 1

            pos_data = {
                'entry_price': pos['entry_price'], 'side': pos['side'],
                'peak': pos['peak'], 'trail': pos['trailing_stop'],
                'sl': pos['stop_loss'], 'hold_hours': pos['hold_bars'],
                'tp1_hit': pos['tp1_hit'], 'tp2_hit': pos['tp2_hit'],
                'tp3_hit': pos['tp3_hit'], 'remaining_pct': pos['remaining_pct'],
            }

            df_slice = df.iloc[:bar_idx + 1]
            exit_result = self.engine.check_exit_signal(df_slice, pos_data)

            if exit_result.get('should_exit', False):
                exit_price = exit_result.get('exit_price', df.iloc[bar_idx]['close'])

                if pos['side'] == 'LONG':
                    exit_price *= (1 - self.slippage_pct)
                else:
                    exit_price *= (1 + self.slippage_pct)

                exit_pct = exit_result.get('exit_pct', pos['remaining_pct'])
                is_partial = exit_result.get('is_partial', False)

                if is_partial and pos['remaining_pct'] - exit_pct > 0.01:
                    # Partial exit - record partial PnL but keep position open
                    self._record_partial_exit(pos, exit_price, exit_pct,
                                              exit_result.get('reason', 'PARTIAL'),
                                              df.iloc[bar_idx])
                    # Update position state
                    updated = exit_result.get('updated', {})
                    for k, v in updated.items():
                        pos[k] = v
                else:
                    # Full exit
                    positions_to_close.append((pos, exit_price,
                                               exit_result.get('reason', 'UNKNOWN'), bar_idx))
            else:
                updated = exit_result.get('updated', {})
                if 'peak' in updated: pos['peak'] = updated['peak']
                if 'trail' in updated: pos['trailing_stop'] = updated['trail']
                if 'sl' in updated: pos['stop_loss'] = updated['sl']
                if 'remaining_pct' in updated: pos['remaining_pct'] = updated['remaining_pct']
                if 'tp1_hit' in updated: pos['tp1_hit'] = updated['tp1_hit']
                if 'tp2_hit' in updated: pos['tp2_hit'] = updated['tp2_hit']
                if 'tp3_hit' in updated: pos['tp3_hit'] = updated['tp3_hit']

        for pos, exit_price, reason, idx in positions_to_close:
            self._close_position(pos, exit_price, reason, df.iloc[idx])

    def _record_partial_exit(self, pos, exit_price, exit_pct, reason, bar):
        """Record a partial exit without closing the position"""
        if pos['side'] == 'LONG':
            pnl_pct = (exit_price - pos['entry_price']) / pos['entry_price']
        else:
            pnl_pct = (pos['entry_price'] - exit_price) / pos['entry_price']

        partial_value = pos['position_value'] * exit_pct
        pnl_dollar = partial_value * pnl_pct
        commission = partial_value * self.commission_pct
        net_pnl = pnl_dollar - commission

        pos['realized_partial'] += net_pnl
        pos['remaining_pct'] -= exit_pct
        self.balance += partial_value + net_pnl

    def _close_position(self, pos, exit_price, reason, bar):
        remaining_value = pos['position_value'] * pos['remaining_pct']

        if pos['side'] == 'LONG':
            pnl_pct = (exit_price - pos['entry_price']) / pos['entry_price']
        else:
            pnl_pct = (pos['entry_price'] - exit_price) / pos['entry_price']

        pnl_dollar = remaining_value * pnl_pct
        exit_commission = (remaining_value * (1 + pnl_pct)) * self.commission_pct
        net_pnl = pnl_dollar - exit_commission + pos['realized_partial']

        self.balance += remaining_value + pnl_dollar - exit_commission

        trade = {
            'symbol': pos['symbol'], 'side': pos['side'],
            'entry_price': pos['entry_price'], 'exit_price': exit_price,
            'pnl_pct': round(pnl_pct * 100, 4),
            'pnl_dollar': round(net_pnl, 4),
            'position_value': pos['position_value'],
            'commission': round(pos['entry_commission'] + exit_commission, 4),
            'hold_hours': pos['hold_bars'],
            'exit_reason': reason, 'strategy': pos['signal_strategy'],
            'signal_score': pos['signal_score'],
            'entry_time': pos['entry_time'],
            'exit_time': bar.get('timestamp', ''),
            'is_win': net_pnl > 0,
            'tp1_hit': pos['tp1_hit'], 'tp2_hit': pos['tp2_hit'], 'tp3_hit': pos['tp3_hit'],
            'partial_realized': round(pos['realized_partial'], 4),
        }
        self.closed_trades.append(trade)
        self.open_positions.remove(pos)

    def _calc_unrealized_pnl(self, current_price):
        total = 0
        for pos in self.open_positions:
            rv = pos['position_value'] * pos['remaining_pct']
            if pos['side'] == 'LONG':
                pnl = (current_price - pos['entry_price']) / pos['entry_price']
            else:
                pnl = (pos['entry_price'] - current_price) / pos['entry_price']
            total += rv * pnl
        return total

    def _generate_report(self, symbol):
        trades = [t for t in self.closed_trades if t['symbol'] == symbol]
        if not trades:
            return {'symbol': symbol, 'total_trades': 0, 'message': 'No trades'}

        wins = [t for t in trades if t['is_win']]
        losses = [t for t in trades if not t['is_win']]
        total_pnl = sum(t['pnl_dollar'] for t in trades)
        gross_profit = sum(t['pnl_dollar'] for t in wins) if wins else 0
        gross_loss = abs(sum(t['pnl_dollar'] for t in losses)) if losses else 0.001

        max_dd = self._calc_max_drawdown()

        exit_reasons = defaultdict(lambda: {'count': 0, 'pnl': 0, 'wins': 0})
        for t in trades:
            r = t['exit_reason']
            exit_reasons[r]['count'] += 1
            exit_reasons[r]['pnl'] += t['pnl_dollar']
            if t['is_win']: exit_reasons[r]['wins'] += 1

        return {
            'symbol': symbol, 'total_trades': len(trades),
            'wins': len(wins), 'losses': len(losses),
            'win_rate': round(len(wins) / len(trades) * 100, 1),
            'total_pnl': round(total_pnl, 2),
            'total_pnl_pct': round(total_pnl / self.initial_balance * 100, 2),
            'profit_factor': round(gross_profit / gross_loss, 2) if gross_loss > 0 else 999,
            'avg_win': round(np.mean([t['pnl_pct'] for t in wins]), 3) if wins else 0,
            'avg_loss': round(np.mean([t['pnl_pct'] for t in losses]), 3) if losses else 0,
            'max_drawdown_pct': round(max_dd * 100, 2),
            'exit_reasons': dict(exit_reasons),
            'trades': trades,
        }

    def _calc_max_drawdown(self):
        if not self.equity_curve: return 0
        peak = self.equity_curve[0]['equity']
        max_dd = 0
        for p in self.equity_curve:
            eq = p['equity']
            if eq > peak: peak = eq
            dd = (peak - eq) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return max_dd

    def reset(self):
        self.balance = self.initial_balance
        self.open_positions = []
        self.closed_trades = []
        self.equity_curve = []


# ============================================================
# 5. MULTI-SYMBOL RUNNER
# ============================================================

def run_comparison(symbols=None, days=60, initial_balance=1000.0):
    """Run V7 (baseline) vs V8 (improved) comparison"""

    if symbols is None:
        symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
            'AVAXUSDT', 'NEARUSDT', 'SUIUSDT', 'ARBUSDT', 'APTUSDT',
            'INJUSDT', 'LINKUSDT', 'DOTUSDT', 'ADAUSDT',
        ]

    # Fetch data once
    print(f"\n{'='*70}")
    print(f"  📥 Fetching {days}-day data for {len(symbols)} symbols...")
    print(f"{'='*70}")
    all_data = {}
    for sym in symbols:
        print(f"  → {sym}...", end=" ", flush=True)
        df = fetch_binance_klines(sym, '1h', days)
        if not df.empty and len(df) >= 80:
            all_data[sym] = df
            print(f"✅ {len(df)} bars")
        else:
            print(f"❌ insufficient")
        time.sleep(0.3)

    results = {}

    # ========== V7 BASELINE (fixed risk) ==========
    print(f"\n{'='*70}")
    print(f"  🔬 TEST A: V7.1 BASELINE (Fixed $60 risk)")
    print(f"{'='*70}")

    v7_engine = ScalpingV7Engine(V7_CONFIG)
    v7_all_trades = []
    for sym, df in all_data.items():
        bt = FixedRiskBacktester(v7_engine, V7_CONFIG, initial_balance)
        r = bt.run(sym, df)
        if r.get('trades'): v7_all_trades.extend(r['trades'])
        n, wr, pf, pnl = r.get('total_trades',0), r.get('win_rate',0), r.get('profit_factor',0), r.get('total_pnl',0)
        s = "✅" if pnl > 0 else "❌"
        print(f"  {s} {sym:12s} | Trades:{n:3d} | WR:{wr:5.1f}% | PF:{pf:5.2f} | PnL:${pnl:+8.2f}")

    results['V7_BASELINE'] = _aggregate(v7_all_trades, initial_balance, 'V7.1 BASELINE')

    # ========== V8 IMPROVED ==========
    print(f"\n{'='*70}")
    print(f"  🚀 TEST B: V8 IMPROVED (Multi-TP + Smart Entry + Fixed Risk)")
    print(f"{'='*70}")

    v8_engine = V8Engine(V8_CONFIG)
    v8_all_trades = []
    for sym, df in all_data.items():
        bt = FixedRiskBacktester(v8_engine, V8_CONFIG, initial_balance)
        r = bt.run(sym, df)
        if r.get('trades'): v8_all_trades.extend(r['trades'])
        n, wr, pf, pnl = r.get('total_trades',0), r.get('win_rate',0), r.get('profit_factor',0), r.get('total_pnl',0)
        s = "✅" if pnl > 0 else "❌"
        print(f"  {s} {sym:12s} | Trades:{n:3d} | WR:{wr:5.1f}% | PF:{pf:5.2f} | PnL:${pnl:+8.2f}")

    results['V8_IMPROVED'] = _aggregate(v8_all_trades, initial_balance, 'V8 IMPROVED')

    # ========== V8.2 AGGRESSIVE MULTI-TP ==========
    print(f"\n{'='*70}")
    print(f"  🔥 TEST C: V8.2 AGGRESSIVE (Earlier TP + Tighter Trail)")
    print(f"{'='*70}")

    v8a_engine = V8Engine(V8_AGGRESSIVE_CONFIG)
    v8a_all_trades = []
    for sym, df in all_data.items():
        bt = FixedRiskBacktester(v8a_engine, V8_AGGRESSIVE_CONFIG, initial_balance)
        r = bt.run(sym, df)
        if r.get('trades'): v8a_all_trades.extend(r['trades'])
        n, wr, pf, pnl = r.get('total_trades',0), r.get('win_rate',0), r.get('profit_factor',0), r.get('total_pnl',0)
        s = "✅" if pnl > 0 else "❌"
        print(f"  {s} {sym:12s} | Trades:{n:3d} | WR:{wr:5.1f}% | PF:{pf:5.2f} | PnL:${pnl:+8.2f}")

    results['V8.2_AGGRESSIVE'] = _aggregate(v8a_all_trades, initial_balance, 'V8.2 AGGRESSIVE')

    # ========== V8.3 LONG ONLY ==========
    print(f"\n{'='*70}")
    print(f"  🛡️ TEST D: V8.3 LONG ONLY (Conservative)")
    print(f"{'='*70}")

    v8l_engine = V8Engine(V8_LONG_ONLY_CONFIG)
    v8l_all_trades = []
    for sym, df in all_data.items():
        bt = FixedRiskBacktester(v8l_engine, V8_LONG_ONLY_CONFIG, initial_balance)
        r = bt.run(sym, df)
        if r.get('trades'): v8l_all_trades.extend(r['trades'])
        n, wr, pf, pnl = r.get('total_trades',0), r.get('win_rate',0), r.get('profit_factor',0), r.get('total_pnl',0)
        s = "✅" if pnl > 0 else "❌"
        print(f"  {s} {sym:12s} | Trades:{n:3d} | WR:{wr:5.1f}% | PF:{pf:5.2f} | PnL:${pnl:+8.2f}")

    results['V8.3_LONG_ONLY'] = _aggregate(v8l_all_trades, initial_balance, 'V8.3 LONG ONLY')

    # ========== COMPARISON ==========
    print(f"\n{'='*70}")
    print(f"  📊 FINAL COMPARISON")
    print(f"{'='*70}")
    for name, r in results.items():
        wr = r.get('win_rate', 0)
        pf = r.get('profit_factor', 0)
        nt = r.get('total_trades', 0)
        pnl = r.get('total_pnl', 0)
        avg_w = r.get('avg_win_pct', 0)
        avg_l = r.get('avg_loss_pct', 0)
        rr = abs(avg_w / avg_l) if avg_l != 0 else 0
        print(f"  {name:20s} | WR:{wr:5.1f}% | PF:{pf:5.2f} | Trades:{nt:4d} | "
              f"PnL:${pnl:+.2f} | AvgW:{avg_w:+.3f}% | AvgL:{avg_l:+.3f}% | R:R={rr:.2f}")

    # Save results
    output_dir = os.path.join(PROJECT_ROOT, 'tests', 'backtest_results')
    os.makedirs(output_dir, exist_ok=True)
    for name, r in results.items():
        summary = {k: v for k, v in r.items() if k != 'all_trades'}
        with open(os.path.join(output_dir, f'{name.lower()}_results.json'), 'w') as f:
            json.dump(summary, f, indent=2, default=str)

    return results


def _aggregate(trades, initial_balance, label):
    if not trades:
        print(f"\n❌ No trades for {label}")
        return {'total_trades': 0}

    wins = [t for t in trades if t['is_win']]
    losses = [t for t in trades if not t['is_win']]
    total_pnl = sum(t['pnl_dollar'] for t in trades)
    gross_profit = sum(t['pnl_dollar'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl_dollar'] for t in losses)) if losses else 0.001

    exit_reasons = defaultdict(lambda: {'count': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        r = t['exit_reason']
        exit_reasons[r]['count'] += 1
        exit_reasons[r]['pnl'] += t['pnl_dollar']
        if t['is_win']: exit_reasons[r]['wins'] += 1

    strat_stats = defaultdict(lambda: {'count': 0, 'wins': 0, 'pnl': 0, 'avg': []})
    for t in trades:
        s = t['strategy']
        strat_stats[s]['count'] += 1
        strat_stats[s]['pnl'] += t['pnl_dollar']
        strat_stats[s]['avg'].append(t['pnl_pct'])
        if t['is_win']: strat_stats[s]['wins'] += 1

    longs = [t for t in trades if t['side'] == 'LONG']
    shorts = [t for t in trades if t['side'] == 'SHORT']

    print(f"\n  📊 {label} AGGREGATE:")
    print(f"  Total Trades:  {len(trades)}")
    print(f"  Win Rate:      {len(wins)/len(trades)*100:.1f}%")
    print(f"  Profit Factor: {gross_profit/gross_loss:.2f}")
    print(f"  Total PnL:     ${total_pnl:+.2f} ({total_pnl/initial_balance*100:+.1f}%)")
    print(f"  Avg Win:       {np.mean([t['pnl_pct'] for t in wins]):.3f}%" if wins else "  Avg Win: N/A")
    print(f"  Avg Loss:      {np.mean([t['pnl_pct'] for t in losses]):.3f}%" if losses else "  Avg Loss: N/A")
    print(f"  LONG:          {len(longs)} (WR:{sum(1 for t in longs if t['is_win'])/max(len(longs),1)*100:.1f}%)")
    print(f"  SHORT:         {len(shorts)} (WR:{sum(1 for t in shorts if t['is_win'])/max(len(shorts),1)*100:.1f}%)")

    print(f"\n  📤 Exit Reasons:")
    for reason, data in sorted(exit_reasons.items(), key=lambda x: x[1]['count'], reverse=True):
        wr = data['wins'] / max(data['count'], 1) * 100
        print(f"    {reason:15s} | N:{data['count']:3d} | WR:{wr:5.1f}% | PnL:${data['pnl']:+.2f}")

    print(f"\n  🎯 Strategy Performance:")
    for s, data in sorted(strat_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
        wr = data['wins'] / max(data['count'], 1) * 100
        avg = np.mean(data['avg']) if data['avg'] else 0
        print(f"    {s:22s} | N:{data['count']:3d} | WR:{wr:5.1f}% | Avg:{avg:+.3f}% | PnL:${data['pnl']:+.2f}")

    return {
        'label': label, 'total_trades': len(trades),
        'wins': len(wins), 'losses': len(losses),
        'win_rate': round(len(wins) / len(trades) * 100, 1),
        'profit_factor': round(gross_profit / gross_loss, 2),
        'total_pnl': round(total_pnl, 2),
        'total_pnl_pct': round(total_pnl / initial_balance * 100, 2),
        'avg_win_pct': round(np.mean([t['pnl_pct'] for t in wins]), 3) if wins else 0,
        'avg_loss_pct': round(np.mean([t['pnl_pct'] for t in losses]), 3) if losses else 0,
        'exit_reasons': {k: dict(v) for k, v in exit_reasons.items()},
        'strategy_stats': {k: {kk: vv for kk, vv in v.items() if kk != 'avg'} for k, v in strat_stats.items()},
        'all_trades': trades,
    }


if __name__ == '__main__':
    print("\n" + "🔬" * 35)
    print("  V8 COMPREHENSIVE BACKTEST — V7 vs V8 Comparison")
    print("  Fixed-Risk | Multi-TP | Smart Entry | Real Data")
    print("🔬" * 35)

    results = run_comparison(
        symbols=['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
                 'AVAXUSDT', 'NEARUSDT', 'SUIUSDT', 'ARBUSDT', 'APTUSDT',
                 'INJUSDT', 'LINKUSDT'],
        days=60,
        initial_balance=1000.0
    )
