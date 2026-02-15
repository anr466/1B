#!/usr/bin/env python3
"""
🚀 Scalping Backtest System - 6 Months
=========================================
- 1H execution bars with 4H trend context
- Multi-strategy: SuperTrend, EMA Crossover, RSI Bounce, Breakout, Reversal Patterns
- Smart exit: Multi-level TP + Trailing Stop + Reversal Exit
- Targets: WR>60%, daily trades, realistic commissions/slippage
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================
COINS = [
    'ETHUSDT', 'BNBUSDT', 'SOLUSDT',       # Large Cap
    'AVAXUSDT', 'NEARUSDT', 'LINKUSDT', 'APTUSDT',  # Mid Cap
    'SUIUSDT', 'ARBUSDT', 'INJUSDT',        # Small Cap
]

CATEGORIES = {
    'Large Cap': ['ETHUSDT', 'BNBUSDT', 'SOLUSDT'],
    'Mid Cap': ['AVAXUSDT', 'NEARUSDT', 'LINKUSDT', 'APTUSDT'],
    'Small Cap': ['SUIUSDT', 'ARBUSDT', 'INJUSDT'],
}

INITIAL_BALANCE = 10_000
COMMISSION_PCT = 0.001       # 0.1% Binance
SLIPPAGE_PCT = 0.0005        # 0.05%
MAX_POSITIONS = 5            # Max 5 concurrent positions
POSITION_SIZE_PCT = 0.06     # 6% per trade (lower per trade, more diversified)
MAX_HOLD_HOURS = 8           # Max 8h hold (pure scalping)

# Entry thresholds
MIN_CONFLUENCE_SCORE = 4     # Need 4+ total score
MIN_TIMING_SIGNALS = 1       # Need at least 1 timing signal (event-based)
MIN_VOLUME_RATIO = 0.9       # Min volume vs average

# Exit configuration - FIXED TP/SL + trailing for runners
SL_PCT = 0.008              # 0.8% stop loss
TP_PCT = 0.012              # 1.2% take profit (R:R = 1.5:1)
TRAILING_ACTIVATION = 0.010  # Activate trailing at +1.0% (for runners past TP zone)
TRAILING_DISTANCE = 0.005    # 0.5% trailing distance


# ============================================================
# MANUAL INDICATOR CALCULATIONS (no pandas_ta dependency)
# ============================================================

def calc_ema(series, period):
    """Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()

def calc_rsi(series, period=14):
    """RSI"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_macd(series, fast=12, slow=26, signal=9):
    """MACD"""
    ema_fast = calc_ema(series, fast)
    ema_slow = calc_ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calc_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calc_atr(high, low, close, period=14):
    """ATR"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calc_supertrend(high, low, close, period=10, multiplier=3.0):
    """SuperTrend indicator"""
    atr = calc_atr(high, low, close, period)
    hl2 = (high + low) / 2
    
    upper_band = hl2 + multiplier * atr
    lower_band = hl2 - multiplier * atr
    
    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=float)
    
    supertrend.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = -1
    
    for i in range(1, len(close)):
        if pd.isna(upper_band.iloc[i]) or pd.isna(lower_band.iloc[i]):
            supertrend.iloc[i] = supertrend.iloc[i-1]
            direction.iloc[i] = direction.iloc[i-1]
            continue
            
        if close.iloc[i-1] <= supertrend.iloc[i-1]:
            # Was bearish
            if close.iloc[i] > upper_band.iloc[i]:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1  # Flip to bullish
            else:
                supertrend.iloc[i] = min(upper_band.iloc[i], 
                                         supertrend.iloc[i-1] if supertrend.iloc[i-1] > 0 else upper_band.iloc[i])
                direction.iloc[i] = -1
        else:
            # Was bullish
            if close.iloc[i] < lower_band.iloc[i]:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1  # Flip to bearish
            else:
                supertrend.iloc[i] = max(lower_band.iloc[i],
                                         supertrend.iloc[i-1] if supertrend.iloc[i-1] > 0 else lower_band.iloc[i])
                direction.iloc[i] = 1
    
    return supertrend, direction

def calc_bollinger_bands(series, period=20, std=2.0):
    """Bollinger Bands"""
    sma = series.rolling(window=period).mean()
    std_dev = series.rolling(window=period).std()
    upper = sma + std * std_dev
    lower = sma - std * std_dev
    return upper, sma, lower

def calc_adx(high, low, close, period=14):
    """ADX with +DI and -DI"""
    n = len(close)
    tr = np.zeros(n)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    
    h = high.values
    l = low.values
    c = close.values
    
    for i in range(1, n):
        h_diff = h[i] - h[i-1]
        l_diff = l[i-1] - l[i]
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1]))
        plus_dm[i] = h_diff if (h_diff > l_diff and h_diff > 0) else 0
        minus_dm[i] = l_diff if (l_diff > h_diff and l_diff > 0) else 0
    
    atr = np.zeros(n)
    sp = np.zeros(n)
    sm = np.zeros(n)
    
    if n > period:
        atr[period] = np.mean(tr[1:period+1])
        sp[period] = np.mean(plus_dm[1:period+1])
        sm[period] = np.mean(minus_dm[1:period+1])
        
        for i in range(period + 1, n):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
            sp[i] = (sp[i-1] * (period - 1) + plus_dm[i]) / period
            sm[i] = (sm[i-1] * (period - 1) + minus_dm[i]) / period
    
    plus_di = np.where(atr > 0, (sp / atr) * 100, 0)
    minus_di = np.where(atr > 0, (sm / atr) * 100, 0)
    
    dx = np.where((plus_di + minus_di) > 0, 
                  np.abs(plus_di - minus_di) / (plus_di + minus_di) * 100, 0)
    
    adx = np.zeros(n)
    start = period * 2
    if start < n:
        adx[start] = np.mean(dx[period:start+1])
        for i in range(start + 1, n):
            adx[i] = (adx[i-1] * (period - 1) + dx[i]) / period
    
    return (pd.Series(adx, index=close.index), 
            pd.Series(plus_di, index=close.index), 
            pd.Series(minus_di, index=close.index))


# ============================================================
# DATA FETCHING
# ============================================================

def fetch_binance_klines(symbol, interval='1h', months=6):
    """Fetch historical klines from Binance"""
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = int((datetime.now() - timedelta(days=months * 30)).timestamp() * 1000)
    
    all_klines = []
    current = start_time
    
    while current < end_time:
        url = 'https://api.binance.com/api/v3/klines'
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': current,
            'endTime': end_time,
            'limit': 1000,
        }
        
        try:
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
            if not data or not isinstance(data, list):
                break
            all_klines.extend(data)
            current = data[-1][0] + 1
            if len(data) < 1000:
                break
            time.sleep(0.2)
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            break
    
    if not all_klines:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
        'taker_buy_quote', 'ignore'
    ])
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    
    df = df.drop_duplicates(subset='timestamp').sort_values('timestamp').reset_index(drop=True)
    return df


def prepare_indicators(df):
    """Calculate all indicators for the dataframe"""
    if len(df) < 60:
        return df
    
    # EMAs
    df['ema_8'] = calc_ema(df['close'], 8)
    df['ema_21'] = calc_ema(df['close'], 21)
    df['ema_55'] = calc_ema(df['close'], 55)
    
    # RSI
    df['rsi'] = calc_rsi(df['close'], 14)
    
    # MACD
    df['macd'], df['macd_signal'], df['macd_hist'] = calc_macd(df['close'])
    
    # ATR
    df['atr'] = calc_atr(df['high'], df['low'], df['close'], 14)
    
    # SuperTrend
    df['supertrend'], df['supertrend_dir'] = calc_supertrend(
        df['high'], df['low'], df['close'], 10, 3.0
    )
    
    # Bollinger Bands
    df['bb_upper'], df['bb_mid'], df['bb_lower'] = calc_bollinger_bands(df['close'], 20, 2.0)
    
    # ADX
    df['adx'], df['plus_di'], df['minus_di'] = calc_adx(df['high'], df['low'], df['close'], 14)
    
    # Volume ratio
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']
    
    # Candle body analysis
    df['body'] = abs(df['close'] - df['open'])
    df['total_range'] = df['high'] - df['low']
    df['upper_wick'] = df['high'] - df[['close', 'open']].max(axis=1)
    df['lower_wick'] = df[['close', 'open']].min(axis=1) - df['low']
    df['is_bullish'] = df['close'] > df['open']
    
    # Support/Resistance (rolling 20-bar)
    df['resistance_20'] = df['high'].rolling(20).max()
    df['support_20'] = df['low'].rolling(20).min()
    
    return df


# ============================================================
# ENTRY SIGNAL DETECTION
# ============================================================

def get_4h_trend(df, idx):
    """
    Calculate 4H trend from 1H data by looking at 4-bar aggregates.
    Returns: 'UP', 'DOWN', or 'NEUTRAL'
    """
    if idx < 20:
        return 'NEUTRAL'
    
    # Use EMAs calculated on 1H (EMA55 on 1H ≈ EMA14 on 4H)
    row = df.iloc[idx]
    
    # 4H trend: EMA21 > EMA55 and price above both
    ema21 = row.get('ema_21', 0)
    ema55 = row.get('ema_55', 0)
    close = row['close']
    
    if pd.isna(ema21) or pd.isna(ema55):
        return 'NEUTRAL'
    
    # Strong uptrend on higher timeframe
    if ema21 > ema55 and close > ema21:
        return 'UP'
    elif ema21 < ema55 and close < ema21:
        return 'DOWN'
    else:
        return 'NEUTRAL'


def detect_entry_signals(df, idx):
    """
    Detect entry signals with TIMING vs CONDITION separation.
    
    TIMING signals (something CHANGED - events, worth 2 pts):
      supertrend_flip, macd_cross, rsi_bounce, bullish_engulfing, breakout_volume, bb_bounce
    
    CONDITION signals (current state, worth 1 pt):
      ema_aligned, supertrend_bullish, rsi_momentum, macd_rising, near_ema8, adx_bullish
    
    Requires: score >= MIN_CONFLUENCE_SCORE AND timing_count >= MIN_TIMING_SIGNALS
    Also requires: 4H trend = UP or NEUTRAL (not DOWN)
    
    Returns: (score, signals_list, timing_count, entry_price, sl)
    """
    if idx < 55:
        return 0, [], 0, 0, 0
    
    row = df.iloc[idx]
    prev = df.iloc[idx - 1]
    
    timing_signals = []
    condition_signals = []
    score = 0
    
    current = row['close']
    
    # Skip if volume too low
    if pd.isna(row['vol_ratio']) or row['vol_ratio'] < MIN_VOLUME_RATIO:
        return 0, ['low_volume'], 0, 0, 0
    
    # ---- 4H TREND FILTER ----
    trend_4h = get_4h_trend(df, idx)
    if trend_4h == 'DOWN':
        return 0, ['trend_down'], 0, 0, 0
    
    # ============ TIMING SIGNALS (events - 2 points each) ============
    
    # T1: SuperTrend Flip (bearish → bullish)
    if (not pd.isna(row['supertrend_dir']) and not pd.isna(prev['supertrend_dir'])):
        if prev['supertrend_dir'] == -1 and row['supertrend_dir'] == 1:
            timing_signals.append('supertrend_flip')
            score += 2
    
    # T2: MACD Bullish Crossover
    if (not pd.isna(row['macd']) and not pd.isna(row['macd_signal']) and
        not pd.isna(prev['macd']) and not pd.isna(prev['macd_signal'])):
        if prev['macd'] < prev['macd_signal'] and row['macd'] > row['macd_signal']:
            timing_signals.append('macd_cross')
            score += 2
    
    # T3: RSI Bounce from Oversold
    if not pd.isna(row['rsi']) and not pd.isna(prev['rsi']):
        if prev['rsi'] < 35 and row['rsi'] > prev['rsi'] and row['rsi'] < 55:
            timing_signals.append('rsi_bounce')
            score += 2
    
    # T4: Bullish Engulfing
    if row['total_range'] > 0 and row['body'] > 0:
        if (not prev['is_bullish'] and row['is_bullish'] and
            row['close'] > prev['open'] and row['open'] < prev['close']):
            timing_signals.append('bullish_engulfing')
            score += 2
    
    # T5: Breakout with Strong Volume
    if not pd.isna(row.get('resistance_20')):
        prev_resistance = df['high'].iloc[max(0, idx-21):idx-1].max()
        if not pd.isna(prev_resistance) and current > prev_resistance and row['vol_ratio'] > 1.5:
            timing_signals.append('breakout_volume')
            score += 2
    
    # T6: Bollinger Band Bounce
    if not pd.isna(row['bb_lower']) and not pd.isna(prev['bb_lower']):
        if prev['low'] <= prev['bb_lower'] and current > row['bb_lower'] and row['is_bullish']:
            timing_signals.append('bb_bounce')
            score += 2
    
    # T7: Hammer candle
    if row['total_range'] > 0 and row['body'] > 0:
        if (row['lower_wick'] > row['body'] * 2.0 and 
            row['upper_wick'] < row['body'] * 0.3 and 
            row['is_bullish']):
            timing_signals.append('hammer')
            score += 2
    
    # ============ CONDITION SIGNALS (state - 1 point each) ============
    
    # C1: EMA Alignment (8 > 21 > 55)
    if (not pd.isna(row['ema_8']) and not pd.isna(row['ema_21']) and not pd.isna(row['ema_55'])):
        if row['ema_8'] > row['ema_21'] > row['ema_55']:
            condition_signals.append('ema_aligned')
            score += 1
    
    # C2: SuperTrend already bullish
    if not pd.isna(row['supertrend_dir']) and row['supertrend_dir'] == 1:
        if 'supertrend_flip' not in timing_signals:
            condition_signals.append('supertrend_bullish')
            score += 1
    
    # C3: RSI Momentum (rising in sweet zone)
    if not pd.isna(row['rsi']) and not pd.isna(prev['rsi']):
        if 40 < row['rsi'] < 65 and row['rsi'] > prev['rsi']:
            condition_signals.append('rsi_momentum')
            score += 1
    
    # C4: MACD Histogram Rising
    if not pd.isna(row['macd_hist']) and not pd.isna(prev['macd_hist']):
        if row['macd_hist'] > 0 and row['macd_hist'] > prev['macd_hist']:
            condition_signals.append('macd_rising')
            score += 1
    
    # C5: Price near EMA8 (pullback zone)
    if not pd.isna(row['ema_8']):
        dist = abs(current - row['ema_8']) / current
        if dist < 0.004:
            condition_signals.append('near_ema8')
            score += 1
    
    # C6: ADX confirms trend
    if not pd.isna(row['adx']) and row['adx'] > 20:
        if not pd.isna(row['plus_di']) and not pd.isna(row['minus_di']):
            if row['plus_di'] > row['minus_di']:
                condition_signals.append('adx_bullish')
                score += 1
    
    # C7: Volume above average
    if not pd.isna(row['vol_ratio']) and row['vol_ratio'] > 1.3:
        condition_signals.append('high_volume')
        score += 1
    
    # ============ BEARISH PENALTIES ============
    if not pd.isna(row['rsi']) and row['rsi'] > 65:
        score -= 3  # Overbought = strong penalty (was 72, now 65)
    
    if not pd.isna(row['supertrend_dir']) and row['supertrend_dir'] == -1:
        score -= 2  # Against SuperTrend
    
    # Price far above EMA21 = overextended
    if not pd.isna(row['ema_21']):
        dist_ema21 = (current - row['ema_21']) / row['ema_21']
        if dist_ema21 > 0.03:  # >3% above EMA21
            score -= 2
    
    # Calculate SL (capped at SL_PCT)
    atr_val = row['atr'] if not pd.isna(row['atr']) else current * SL_PCT
    sl = current * (1 - SL_PCT)  # Fixed % SL for consistency
    
    all_signals = timing_signals + condition_signals
    timing_count = len(timing_signals)
    
    return score, all_signals, timing_count, current, sl


# ============================================================
# EXIT SIGNAL DETECTION
# ============================================================

def check_exit(df, idx, trade):
    """
    Trailing-only exit system for scalping.
    
    Exit logic:
    1. Stop Loss (fixed)
    2. Breakeven stop (move SL to entry when profit >= BREAKEVEN_TRIGGER)
    3. Trailing stop (activate at TRAILING_ACTIVATION, trail at TRAILING_DISTANCE)
    4. Bearish reversal exit (confirmed reversal while in profit)
    5. Max hold time
    
    Returns: (should_exit, exit_type, close_ratio, exit_price)
    """
    row = df.iloc[idx]
    current_high = row['high']
    current_low = row['low']
    current_close = row['close']
    
    entry_price = trade['entry_price']
    sl = trade['sl']
    peak_price = trade['peak_price']
    
    # Update peak price
    if current_high > peak_price:
        trade['peak_price'] = current_high
        peak_price = current_high
    
    pnl_pct = (current_close - entry_price) / entry_price
    peak_profit = (peak_price - entry_price) / entry_price
    
    # ---- 1. STOP LOSS (check against low) ----
    if current_low <= sl:
        return True, 'STOP_LOSS', 1.0, sl
    
    # ---- 2. FIXED TAKE PROFIT (R:R = 1.5:1) ----
    tp_price = entry_price * (1 + TP_PCT)
    if current_high >= tp_price:
        return True, 'TAKE_PROFIT', 1.0, tp_price
    
    # ---- 3. TRAILING STOP (for runners that go past TP zone) ----
    if peak_profit >= TRAILING_ACTIVATION:
        trailing_stop = peak_price * (1 - TRAILING_DISTANCE)
        # Only tighten, never loosen
        if trailing_stop > trade.get('trailing_stop', 0):
            trade['trailing_stop'] = trailing_stop
        
        actual_trailing = trade.get('trailing_stop', 0)
        if actual_trailing > 0 and current_low <= actual_trailing:
            return True, 'TRAILING_STOP', 1.0, actual_trailing
    
    # ---- 4. BEARISH REVERSAL EXIT (only if in profit) ----
    if idx >= 2 and pnl_pct > 0.003:
        prev = df.iloc[idx - 1]
        reversal_score = 0
        
        # SuperTrend flip bearish (strongest signal)
        if (not pd.isna(row['supertrend_dir']) and not pd.isna(prev['supertrend_dir'])):
            if prev['supertrend_dir'] == 1 and row['supertrend_dir'] == -1:
                reversal_score += 3
        
        # Bearish engulfing
        if (prev['is_bullish'] and not row['is_bullish'] and
            row['open'] > prev['close'] and current_close < prev['open']):
            reversal_score += 2
        
        # MACD bearish cross
        if (not pd.isna(row['macd']) and not pd.isna(row['macd_signal']) and
            not pd.isna(prev['macd']) and not pd.isna(prev['macd_signal'])):
            if prev['macd'] > prev['macd_signal'] and row['macd'] < row['macd_signal']:
                reversal_score += 2
        
        # RSI overbought declining
        if not pd.isna(row['rsi']) and not pd.isna(prev['rsi']):
            if prev['rsi'] > 68 and row['rsi'] < prev['rsi']:
                reversal_score += 1
        
        # Confirmed reversal = full exit
        if reversal_score >= 3:
            return True, 'REVERSAL_EXIT', 1.0, current_close
    
    # ---- 5. MAX HOLD TIME ----
    entry_time = trade['entry_time']
    current_time = row['timestamp']
    if isinstance(current_time, pd.Timestamp):
        current_time = current_time.to_pydatetime()
    if isinstance(entry_time, pd.Timestamp):
        entry_time = entry_time.to_pydatetime()
    
    hours_held = (current_time - entry_time).total_seconds() / 3600
    if hours_held >= MAX_HOLD_HOURS:
        return True, 'MAX_HOLD', 1.0, current_close
    
    # ---- 6. STAGNANT (12h with no movement) ----
    if hours_held >= 12 and abs(pnl_pct) < 0.002:
        return True, 'STAGNANT', 1.0, current_close
    
    return False, 'HOLD', 0, 0


# ============================================================
# MAIN BACKTESTER
# ============================================================

def run_backtest():
    print("\n" + "=" * 70)
    print("  🚀 SCALPING BACKTEST - 6 MONTHS (1H BARS)")
    print("=" * 70)
    
    # Fetch data for all coins
    all_data = {}
    print("\n📊 Fetching 6 months of 1H data...")
    for symbol in COINS:
        print(f"  Fetching {symbol}...", end=" ", flush=True)
        df = fetch_binance_klines(symbol, '1h', 6)
        if len(df) > 100:
            df = prepare_indicators(df)
            all_data[symbol] = df
            print(f"✓ {len(df)} bars")
        else:
            print(f"✗ insufficient data ({len(df)} bars)")
    
    if not all_data:
        print("❌ No data fetched!")
        return
    
    # Run backtest
    balance = INITIAL_BALANCE
    open_positions = {}  # symbol -> trade
    closed_trades = []
    total_commission = 0
    total_slippage = 0
    peak_balance = balance
    max_drawdown = 0
    
    # Get unified timeline
    min_bars = min(len(df) for df in all_data.values())
    
    print(f"\n🏃 Running backtest on {min_bars} bars across {len(all_data)} coins...")
    print(f"  Config: SL={SL_PCT*100}% | TP={TP_PCT*100}% | R:R=1:{TP_PCT/SL_PCT:.1f}")
    print(f"  Trailing: activate at +{TRAILING_ACTIVATION*100}%, distance {TRAILING_DISTANCE*100}%")
    print(f"  Min confluence: {MIN_CONFLUENCE_SCORE} signals | Max hold: {MAX_HOLD_HOURS}h")
    
    signals_analyzed = 0
    rejections = {'low_confluence': 0, 'max_positions': 0, 'already_open': 0, 'low_volume': 0}
    
    for bar_idx in range(60, min_bars):
        # ---- CHECK EXITS FIRST ----
        for symbol in list(open_positions.keys()):
            trade = open_positions[symbol]
            df = all_data[symbol]
            
            if bar_idx >= len(df):
                continue
            
            should_exit, exit_type, close_ratio, exit_price = check_exit(df, bar_idx, trade)
            
            if should_exit:
                # Apply slippage
                exit_price_actual = exit_price * (1 - SLIPPAGE_PCT)
                commission = trade['position_value'] * COMMISSION_PCT
                total_commission += commission
                slippage_cost = trade['position_value'] * SLIPPAGE_PCT
                total_slippage += slippage_cost
                
                closed_value = trade['remaining_qty'] * exit_price_actual
                cost_basis = trade['remaining_qty'] * trade['entry_price']
                pnl = closed_value - cost_basis - commission - slippage_cost
                pnl_pct = (exit_price_actual - trade['entry_price']) / trade['entry_price'] * 100
                
                balance += pnl
                
                # Track peak balance and drawdown
                if balance > peak_balance:
                    peak_balance = balance
                dd = (peak_balance - balance) / peak_balance * 100
                if dd > max_drawdown:
                    max_drawdown = dd
                
                entry_time = trade['entry_time']
                exit_time = df['timestamp'].iloc[bar_idx]
                if isinstance(exit_time, pd.Timestamp):
                    exit_time = exit_time.to_pydatetime()
                if isinstance(entry_time, pd.Timestamp):
                    entry_time = entry_time.to_pydatetime()
                
                hours_held = (exit_time - entry_time).total_seconds() / 3600
                
                closed_trades.append({
                    'symbol': symbol,
                    'entry_price': trade['entry_price'],
                    'exit_price': exit_price_actual,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'entry_time': entry_time,
                    'exit_time': exit_time,
                    'hours_held': hours_held,
                    'exit_type': exit_type,
                    'signals': trade['signals'],
                    'strategy': trade.get('primary_strategy', 'mixed'),
                })
                
                # All exits are full close now
                del open_positions[symbol]
        
        # ---- CHECK ENTRIES ----
        for symbol, df in all_data.items():
            if bar_idx >= len(df):
                continue
            
            signals_analyzed += 1
            
            # Skip if already in position
            if symbol in open_positions:
                rejections['already_open'] += 1
                continue
            
            # Skip if max positions reached
            if len(open_positions) >= MAX_POSITIONS:
                rejections['max_positions'] += 1
                continue
            
            # Detect signals (use bar_idx - 1 for signal, enter on bar_idx)
            score, signals, timing_count, entry_price, sl = detect_entry_signals(df, bar_idx - 1)
            
            if 'low_volume' in signals:
                rejections['low_volume'] += 1
                continue
            
            if 'trend_down' in signals:
                rejections['trend_down'] = rejections.get('trend_down', 0) + 1
                continue
            
            # Need minimum confluence AND at least 1 timing signal
            if score < MIN_CONFLUENCE_SCORE:
                rejections['low_confluence'] += 1
                continue
            
            if timing_count < MIN_TIMING_SIGNALS:
                rejections['no_timing'] = rejections.get('no_timing', 0) + 1
                continue
            
            # Enter on current bar open (execution delay simulation)
            actual_entry = df['open'].iloc[bar_idx] * (1 + SLIPPAGE_PCT)
            
            # Position sizing
            position_value = balance * POSITION_SIZE_PCT
            qty = position_value / actual_entry
            
            commission = position_value * COMMISSION_PCT
            total_commission += commission
            slippage_cost = position_value * SLIPPAGE_PCT
            total_slippage += slippage_cost
            
            # Determine primary strategy (first timing signal)
            primary = 'mixed'
            if 'supertrend_flip' in signals:
                primary = 'supertrend'
            elif 'breakout_volume' in signals:
                primary = 'breakout'
            elif 'rsi_bounce' in signals:
                primary = 'rsi_bounce'
            elif 'bullish_engulfing' in signals:
                primary = 'reversal_pattern'
            elif 'macd_cross' in signals:
                primary = 'macd_cross'
            elif 'bb_bounce' in signals:
                primary = 'bb_bounce'
            elif 'hammer' in signals:
                primary = 'hammer'
            
            # Fixed SL from actual entry
            sl_price = actual_entry * (1 - SL_PCT)
            
            entry_time = df['timestamp'].iloc[bar_idx]
            
            open_positions[symbol] = {
                'entry_price': actual_entry,
                'sl': sl_price,
                'position_value': position_value,
                'remaining_qty': qty,
                'entry_time': entry_time,
                'peak_price': actual_entry,
                'signals': signals,
                'primary_strategy': primary,
                'score': score,
                'timing_count': timing_count,
            }
    
    # Force close remaining positions
    for symbol, trade in open_positions.items():
        df = all_data[symbol]
        last_price = df['close'].iloc[-1]
        pnl_pct = (last_price - trade['entry_price']) / trade['entry_price'] * 100
        cost_basis = trade['remaining_qty'] * trade['entry_price']
        closed_value = trade['remaining_qty'] * last_price
        pnl = closed_value - cost_basis
        balance += pnl
        
        entry_time = trade['entry_time']
        exit_time = df['timestamp'].iloc[-1]
        if isinstance(exit_time, pd.Timestamp):
            exit_time = exit_time.to_pydatetime()
        if isinstance(entry_time, pd.Timestamp):
            entry_time = entry_time.to_pydatetime()
        
        hours_held = (exit_time - entry_time).total_seconds() / 3600
        
        closed_trades.append({
            'symbol': symbol,
            'entry_price': trade['entry_price'],
            'exit_price': last_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'hours_held': hours_held,
            'exit_type': 'FORCED_CLOSE',
            'signals': trade['signals'],
            'strategy': trade.get('primary_strategy', 'mixed'),
            'close_ratio': 1.0,
            'tp_hits': trade.get('tp_hits', 0),
        })
    
    # ============================================================
    # RESULTS ANALYSIS
    # ============================================================
    
    print("\n" + "=" * 70)
    print("  SCALPING SYSTEM - 6-MONTH BACKTEST RESULTS")
    print("=" * 70)
    
    if not closed_trades:
        print("  ❌ No trades executed!")
        return
    
    wins = [t for t in closed_trades if t['pnl'] > 0]
    losses = [t for t in closed_trades if t['pnl'] <= 0]
    total_pnl = sum(t['pnl'] for t in closed_trades)
    
    win_rate = len(wins) / len(closed_trades) * 100 if closed_trades else 0
    avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
    avg_loss = np.mean([t['pnl_pct'] for t in losses]) if losses else 0
    
    gross_profit = sum(t['pnl'] for t in wins)
    gross_loss = abs(sum(t['pnl'] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    avg_hold = np.mean([t['hours_held'] for t in closed_trades])
    
    # Trades per day
    if closed_trades:
        first_trade = min(t['entry_time'] for t in closed_trades)
        last_trade = max(t['exit_time'] for t in closed_trades)
        total_days = (last_trade - first_trade).total_seconds() / 86400
        trades_per_day = len(closed_trades) / total_days if total_days > 0 else 0
    else:
        trades_per_day = 0
    
    print(f"\n  --- OVERALL PERFORMANCE ---")
    print(f"  Initial Balance:    $ {INITIAL_BALANCE:>12,.2f}")
    print(f"  Final Balance:      $ {balance:>12,.2f}")
    print(f"  Total P&L:          $ {total_pnl:>12,.2f} ({total_pnl/INITIAL_BALANCE*100:+.2f}%)")
    print(f"  Total Commission:   $ {total_commission:>12,.2f}")
    print(f"  Total Slippage:     $ {total_slippage:>12,.2f}")
    print(f"  Net After Costs:    $ {total_pnl - total_commission - total_slippage:>12,.2f}")
    
    print(f"\n  --- TRADE STATISTICS ---")
    print(f"  Total Trades:       {len(closed_trades)}")
    print(f"  Wins:               {len(wins)} ({win_rate:.1f}%)")
    print(f"  Losses:             {len(losses)} ({100-win_rate:.1f}%)")
    print(f"  Profit Factor:      {profit_factor:.2f}")
    print(f"  Avg Win:            {avg_win:+.2f}%")
    print(f"  Avg Loss:           {avg_loss:+.2f}%")
    if closed_trades:
        print(f"  Best Trade:         {max(t['pnl_pct'] for t in closed_trades):+.2f}%")
        print(f"  Worst Trade:        {min(t['pnl_pct'] for t in closed_trades):+.2f}%")
    print(f"  Avg Hold Time:      {avg_hold:.1f} hours")
    print(f"  Max Drawdown:       {max_drawdown:.2f}%")
    print(f"  Trades/Day:         {trades_per_day:.1f}")
    
    # BY STRATEGY
    print(f"\n  --- BY STRATEGY ---")
    strategies = {}
    for t in closed_trades:
        s = t['strategy']
        if s not in strategies:
            strategies[s] = {'trades': 0, 'wins': 0, 'pnl': 0, 'pnl_pcts': []}
        strategies[s]['trades'] += 1
        if t['pnl'] > 0:
            strategies[s]['wins'] += 1
        strategies[s]['pnl'] += t['pnl']
        strategies[s]['pnl_pcts'].append(t['pnl_pct'])
    
    for name, data in sorted(strategies.items(), key=lambda x: -x[1]['pnl']):
        wr = data['wins'] / data['trades'] * 100 if data['trades'] > 0 else 0
        avg = np.mean(data['pnl_pcts'])
        print(f"  {name:<22} | Trades: {data['trades']:>3} | WR: {wr:>5.1f}% | PnL: ${data['pnl']:>8.2f} | Avg: {avg:+.2f}%")
    
    # BY COIN
    print(f"\n  --- BY COIN ---")
    coins = {}
    for t in closed_trades:
        s = t['symbol']
        if s not in coins:
            coins[s] = {'trades': 0, 'wins': 0, 'pnl': 0}
        coins[s]['trades'] += 1
        if t['pnl'] > 0:
            coins[s]['wins'] += 1
        coins[s]['pnl'] += t['pnl']
    
    for name in sorted(coins.keys()):
        data = coins[name]
        wr = data['wins'] / data['trades'] * 100 if data['trades'] > 0 else 0
        print(f"  {name:<12} | Trades: {data['trades']:>3} | WR: {wr:>5.1f}% | PnL: ${data['pnl']:>8.2f}")
    
    # BY CATEGORY
    print(f"\n  --- BY CATEGORY ---")
    for cat_name, cat_coins in CATEGORIES.items():
        cat_trades = [t for t in closed_trades if t['symbol'] in cat_coins]
        if cat_trades:
            cat_wins = len([t for t in cat_trades if t['pnl'] > 0])
            cat_wr = cat_wins / len(cat_trades) * 100
            cat_pnl = sum(t['pnl'] for t in cat_trades)
            cat_hold = np.mean([t['hours_held'] for t in cat_trades])
            print(f"  {cat_name:<12} | Trades: {len(cat_trades):>3} | WR: {cat_wr:>5.1f}% | PnL: ${cat_pnl:>8.2f} | Avg Hold: {cat_hold:.0f}h")
    
    # BY EXIT TYPE
    print(f"\n  --- EXIT REASONS ---")
    exit_types = {}
    for t in closed_trades:
        et = t['exit_type']
        if et not in exit_types:
            exit_types[et] = {'count': 0, 'wins': 0, 'pnl': 0}
        exit_types[et]['count'] += 1
        if t['pnl'] > 0:
            exit_types[et]['wins'] += 1
        exit_types[et]['pnl'] += t['pnl']
    
    for name, data in sorted(exit_types.items(), key=lambda x: -x[1]['count']):
        wr = data['wins'] / data['count'] * 100 if data['count'] > 0 else 0
        print(f"  {name:<25} | Count: {data['count']:>3} | WR: {wr:>5.1f}% | PnL: ${data['pnl']:>8.2f}")
    
    # SIGNAL REJECTIONS
    print(f"\n  --- SIGNAL REJECTIONS ---")
    print(f"  Total signals analyzed: {signals_analyzed}")
    total_rejected = sum(rejections.values())
    print(f"  Total rejected: {total_rejected}")
    for reason, count in sorted(rejections.items(), key=lambda x: -x[1]):
        print(f"  {reason:<25}: {count:>5}")
    
    # MONTHLY PERFORMANCE
    print(f"\n  --- MONTHLY PERFORMANCE ---")
    monthly = {}
    for t in closed_trades:
        month_key = t['exit_time'].strftime('%Y-%m') if isinstance(t['exit_time'], datetime) else str(t['exit_time'])[:7]
        if month_key not in monthly:
            monthly[month_key] = {'trades': 0, 'wins': 0, 'pnl': 0}
        monthly[month_key]['trades'] += 1
        if t['pnl'] > 0:
            monthly[month_key]['wins'] += 1
        monthly[month_key]['pnl'] += t['pnl']
    
    for month in sorted(monthly.keys()):
        data = monthly[month]
        wr = data['wins'] / data['trades'] * 100 if data['trades'] > 0 else 0
        print(f"  {month} | Trades: {data['trades']:>3} | WR: {wr:>5.1f}% | PnL: ${data['pnl']:>8.2f}")
    
    # DAILY PERFORMANCE SUMMARY
    print(f"\n  --- DAILY TRADING FREQUENCY ---")
    daily = {}
    for t in closed_trades:
        day_key = t['entry_time'].strftime('%Y-%m-%d') if isinstance(t['entry_time'], datetime) else str(t['entry_time'])[:10]
        if day_key not in daily:
            daily[day_key] = 0
        daily[day_key] += 1
    
    if daily:
        days_with_trades = len(daily)
        avg_trades_on_active_days = np.mean(list(daily.values()))
        max_trades_day = max(daily.values())
        print(f"  Days with trades:       {days_with_trades}")
        print(f"  Avg trades/active day:  {avg_trades_on_active_days:.1f}")
        print(f"  Max trades in one day:  {max_trades_day}")
    
    # TOP WINNING SIGNALS
    print(f"\n  --- TOP SIGNAL COMBINATIONS ---")
    signal_combos = {}
    for t in closed_trades:
        key = '+'.join(sorted(t['signals'][:3]))  # Top 3 signals
        if key not in signal_combos:
            signal_combos[key] = {'count': 0, 'wins': 0, 'pnl': 0}
        signal_combos[key]['count'] += 1
        if t['pnl'] > 0:
            signal_combos[key]['wins'] += 1
        signal_combos[key]['pnl'] += t['pnl']
    
    sorted_combos = sorted(signal_combos.items(), key=lambda x: -x[1]['pnl'])[:10]
    for combo, data in sorted_combos:
        wr = data['wins'] / data['count'] * 100 if data['count'] > 0 else 0
        print(f"  {combo[:45]:<45} | N={data['count']:>2} | WR: {wr:>5.1f}% | PnL: ${data['pnl']:>7.2f}")
    
    # RECOMMENDATIONS
    print(f"\n  --- RECOMMENDATIONS ---")
    if win_rate >= 60:
        print(f"  ✅ Win rate {win_rate:.1f}% meets target (>60%)")
    else:
        print(f"  ⚠️ Win rate {win_rate:.1f}% below target 60%. Consider tightening entry filters.")
    
    if trades_per_day >= 1:
        print(f"  ✅ Trade frequency {trades_per_day:.1f}/day is good for scalping")
    else:
        print(f"  ⚠️ Trade frequency {trades_per_day:.1f}/day is low. Consider lowering MIN_CONFLUENCE_SCORE.")
    
    if profit_factor >= 1.5:
        print(f"  ✅ SYSTEM IS PROFITABLE with PF {profit_factor:.2f}")
    elif profit_factor >= 1.0:
        print(f"  🟡 SYSTEM IS MARGINALLY PROFITABLE. PF {profit_factor:.2f}")
    else:
        print(f"  ❌ SYSTEM IS LOSING MONEY. PF {profit_factor:.2f}")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    run_backtest()
