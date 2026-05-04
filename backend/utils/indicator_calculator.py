#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Indicator Calculator — مصدر واحد لكل المؤشرات الفنية
=============================================================
Replaces duplicated indicator calculations across:
  - coin_state_analyzer.py
  - trading_orchestrator.py
  - entry_executor.py
  - mtf_confirmation.py

All functions are pure (no side effects) and accept/return DataFrames.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional


def compute_rsi(df: pd.DataFrame, period: int = 14, column: str = "close") -> pd.Series:
    """Relative Strength Index"""
    delta = df[column].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("inf"))
    return 100 - (100 / (1 + rs))


def compute_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average Directional Index"""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where(plus_dm > 0, 0)
    minus_dm = minus_dm.where(minus_dm > 0, 0)

    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(period).mean()

    plus_di = 100 * plus_dm.ewm(alpha=1 / period).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period).mean() / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.ewm(alpha=1 / period).mean()


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range — Wilder's smoothing (industry standard)"""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    # FIX: Use Wilder's smoothing instead of simple rolling mean
    return tr.ewm(alpha=1 / period, min_periods=period).mean()


def compute_ema(
    df: pd.DataFrame, spans: list = None, column: str = "close"
) -> Dict[str, pd.Series]:
    """Exponential Moving Averages for multiple spans"""
    if spans is None:
        spans = [8, 21, 55]
    result = {}
    for span in spans:
        result[f"ema{span}"] = df[column].ewm(span=span, adjust=False).mean()
    return result


def compute_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    column: str = "close",
) -> Dict[str, pd.Series]:
    """MACD Line, Signal Line, Histogram"""
    ema_fast = df[column].ewm(span=fast, adjust=False).mean()
    ema_slow = df[column].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd": macd_line,
        "macd_signal": signal_line,
        "macd_histogram": histogram,
    }


def compute_bollinger_bands(
    df: pd.DataFrame, period: int = 20, std_mult: float = 2.0, column: str = "close"
) -> Dict[str, pd.Series]:
    """Bollinger Bands"""
    sma = df[column].rolling(period).mean()
    std = df[column].rolling(period).std()
    return {
        "bb_upper": sma + std_mult * std,
        "bb_middle": sma,
        "bb_lower": sma - std_mult * std,
        "bb_width": ((sma + std_mult * std) - (sma - std_mult * std)) / sma * 100,
    }


def compute_obv(df: pd.DataFrame, column: str = "close") -> pd.Series:
    """On-Balance Volume"""
    direction = np.sign(df[column].diff())
    return (direction * df["volume"]).cumsum()


def compute_volume_ratio(df: pd.DataFrame, period: int = 20) -> float:
    """Current volume vs average volume"""
    vol = df["volume"]
    vol_avg = vol.rolling(period).mean().iloc[-1] if len(vol) >= period else vol.mean()
    current = vol.iloc[-1]
    return current / vol_avg if vol_avg > 0 else 1.0


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all standard indicators to a DataFrame in one call.
    Safe to call multiple times — skips columns that already exist.
    """
    result = df.copy()

    if "rsi" not in result.columns:
        result["rsi"] = compute_rsi(result)

    if "adx" not in result.columns:
        result["adx"] = compute_adx(result)

    if "atr" not in result.columns:
        result["atr"] = compute_atr(result)

    emas = compute_ema(result)
    for name, series in emas.items():
        if name not in result.columns:
            result[name] = series

    macd = compute_macd(result)
    for name, series in macd.items():
        if name not in result.columns:
            result[name] = series

    bb = compute_bollinger_bands(result)
    for name, series in bb.items():
        if name not in result.columns:
            result[name] = series

    if "obv" not in result.columns:
        result["obv"] = compute_obv(result)

    return result
