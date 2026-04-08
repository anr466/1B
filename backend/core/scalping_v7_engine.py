#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Scalping V7.1 Engine - Live Trading Integration
====================================================
V7 + Cognitive Entry + ATR-based Adaptive SL

Performance (45-day backtest, $1000, 10% position, 19 coins):
- V7 EXP10:  PF=1.49 | WR=50.8% | PnL=+15.6%
- V7.1 F5:   PF=1.87 | WR=78.3% | PnL=+66.3%  ← CURRENT
- Validated: 35 experiments across 3 rounds, split-sample stable

Key features (V7.1):
1. Cognitive entry: 5 strategies (trend_cont, breakout, reversal,
   trend_cont_short) + V7 fallback — blocked: pullback, vol_expand
2. ATR-based adaptive SL (2.5x ATR via VolatilityAnalyzer)
3. Trailing-only exit (0.4% activation, 0.3% distance)
4. Reversal exit, max hold 12h, stagnant 4h exit
5. Breakeven trigger at +0.5%, early cut at 3h/-0.5%
6. Blocked losing patterns: st_flip_bear, rsi_reject, macd_x_bear
7. Manual indicators (no pandas_ta dependency)
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Lazy import for VolatilityAnalyzer (avoid circular imports)
_vol_analyzer = None


def _get_vol_analyzer():
    global _vol_analyzer
    if _vol_analyzer is None:
        try:
            from backend.analysis.volatility_analyzer import VolatilityAnalyzer

            _vol_analyzer = VolatilityAnalyzer()
        except Exception as e:
            logger.warning(f"VolatilityAnalyzer unavailable, using fixed SL: {e}")
    return _vol_analyzer


# ============================================================
# V7.1 CONFIGURATION - F5 optimized (35 experiments, 3 rounds, 19 coins, split-sample stable)
# ============================================================
V7_CONFIG = {
    # Position sizing
    "position_size_pct": 0.06,  # 6% of balance per trade
    "max_positions": 5,  # Max concurrent positions
    "max_hold_hours": 12,  # Max hold time
    # Entry thresholds (V7 fallback)
    "min_confluence": 4,  # Minimum confluence score
    "min_timing": 1,  # Minimum timing signals
    "require_quality": True,  # Require breakout OR 2+ timing
    # V7.1: Cognitive entry (5 strategies + V7 fallback)
    "use_cognitive_entry": True,  # Enable cognitive entry strategies
    # Losing strategies blocked
    "blocked_cognitive": ["pullback", "vol_expand"],
    # V7.1: ATR-based adaptive SL (replaces fixed 0.8%)
    "use_atr_sl": True,  # Enable ATR-based stop loss
    "atr_sl_multiplier": 4.0,  # ATR multiplier for SL distance (was 2.5)
    "sl_pct": 0.035,  # Fallback fixed SL if ATR unavailable (was 0.8%)
    # Exit - trailing only (EXP10 optimized)
    "trailing_activation": 0.015,  # Activate trailing at +1.5% (was 0.4%)
    "trailing_distance": 0.010,  # 1.0% trailing distance (was 0.3%)
    "breakeven_trigger": 0.010,  # Move SL to breakeven at +1.0% (was 0.5%)
    # Early exit
    "early_cut_hours": 6,  # Cut losing trades after 6h (was 3h)
    "early_cut_loss": 0.015,  # if loss exceeds 1.5% (was 0.5%)
    "stagnant_hours": 8,  # Stagnant exit after 8h (was 4h)
    "stagnant_threshold": 0.005,  # Less than 0.5% movement (was 0.2%)
    # Blocked SHORT patterns (verified net negative PnL)
    "blocked_short": ["st_flip_bear", "rsi_reject", "macd_x_bear"],
    # Costs (for demo mode)
    "commission_pct": 0.001,  # 0.1% commission
    "slippage_pct": 0.0005,  # 0.05% slippage
    # Data requirements
    "min_bars": 60,  # Minimum bars needed for indicators
    "data_timeframe": "1h",  # Execution timeframe
    # Signal quality
    "min_signal_strength": 70,  # Minimum signal score to enter (new)
}


# ============================================================
# INDICATORS (manual calculation, no external dependencies)
# ============================================================
def _ema(series, period):
    """Exponential Moving Average"""
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series, period=14):
    """Relative Strength Index"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    return 100 - 100 / (1 + gain / loss)


def _macd(series, fast=12, slow=26, signal=9):
    """MACD Line, Signal, Histogram"""
    macd_line = _ema(series, fast) - _ema(series, slow)
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _atr(high, low, close, period=14):
    """Average True Range"""
    tr = pd.concat(
        [high - low, abs(high - close.shift(1)), abs(low - close.shift(1))],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _supertrend(high, low, close, period=10, multiplier=3.0):
    """SuperTrend indicator"""
    atr_val = _atr(high, low, close, period)
    hl2 = (high + low) / 2
    upper_band = hl2 + multiplier * atr_val
    lower_band = hl2 - multiplier * atr_val

    st = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=float)
    st.iloc[0] = upper_band.iloc[0]
    direction.iloc[0] = -1

    for i in range(1, len(close)):
        if pd.isna(upper_band.iloc[i]) or pd.isna(lower_band.iloc[i]):
            st.iloc[i] = st.iloc[i - 1]
            direction.iloc[i] = direction.iloc[i - 1]
            continue

        if close.iloc[i - 1] <= st.iloc[i - 1]:
            if close.iloc[i] > upper_band.iloc[i]:
                st.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
            else:
                st.iloc[i] = min(
                    upper_band.iloc[i],
                    (st.iloc[i - 1] if st.iloc[i - 1] > 0 else upper_band.iloc[i]),
                )
                direction.iloc[i] = -1
        else:
            if close.iloc[i] < lower_band.iloc[i]:
                st.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                st.iloc[i] = max(
                    lower_band.iloc[i],
                    (st.iloc[i - 1] if st.iloc[i - 1] > 0 else lower_band.iloc[i]),
                )
                direction.iloc[i] = 1

    return st, direction


def _bbands(series, period=20, std_dev=2.0):
    """Bollinger Bands (upper, middle, lower)"""
    middle = series.rolling(period).mean()
    std = series.rolling(period).std()
    return middle + std_dev * std, middle, middle - std_dev * std


def _adx_calc(high, low, close, period=14):
    """Average Directional Index with +DI and -DI"""
    n = len(close)
    hv = high.values
    lv = low.values
    cv = close.values

    tr = np.zeros(n)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)

    for i in range(1, n):
        h_diff = hv[i] - hv[i - 1]
        l_diff = lv[i - 1] - lv[i]
        tr[i] = max(hv[i] - lv[i], abs(hv[i] - cv[i - 1]), abs(lv[i] - cv[i - 1]))
        plus_dm[i] = h_diff if (h_diff > l_diff and h_diff > 0) else 0
        minus_dm[i] = l_diff if (l_diff > h_diff and l_diff > 0) else 0

    smooth_tr = np.zeros(n)
    smooth_plus = np.zeros(n)
    smooth_minus = np.zeros(n)

    if n > period:
        smooth_tr[period] = np.mean(tr[1 : period + 1])
        smooth_plus[period] = np.mean(plus_dm[1 : period + 1])
        smooth_minus[period] = np.mean(minus_dm[1 : period + 1])
        for i in range(period + 1, n):
            smooth_tr[i] = (smooth_tr[i - 1] * (period - 1) + tr[i]) / period
            smooth_plus[i] = (smooth_plus[i - 1] * (period - 1) + plus_dm[i]) / period
            smooth_minus[i] = (
                smooth_minus[i - 1] * (period - 1) + minus_dm[i]
            ) / period

    with np.errstate(divide="ignore", invalid="ignore"):
        plus_di = np.where(smooth_tr > 0, smooth_plus / smooth_tr * 100, 0)
        minus_di = np.where(smooth_tr > 0, smooth_minus / smooth_tr * 100, 0)
        dx = np.where(
            (plus_di + minus_di) > 0,
            np.abs(plus_di - minus_di) / (plus_di + minus_di) * 100,
            0,
        )

    adx = np.zeros(n)
    start_idx = period * 2
    if start_idx < n:
        adx[start_idx] = np.mean(dx[period : start_idx + 1])
        for i in range(start_idx + 1, n):
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

    return (
        pd.Series(adx, index=close.index),
        pd.Series(plus_di, index=close.index),
        pd.Series(minus_di, index=close.index),
    )


# ============================================================
# SCALPING V7 ENGINE
# ============================================================
class ScalpingV7Engine:
    """
    Live trading engine implementing exact v7 backtester logic.

    Usage:
        engine = ScalpingV7Engine()
        df = engine.prepare_data(raw_df)
        trend = engine.get_4h_trend(df)
        entry = engine.detect_entry(df, trend)
        exit_signal = engine.check_exit_signal(df, position_data)
    """

    def __init__(self, config: Dict = None):
        self.config = {**V7_CONFIG, **(config or {})}
        self.logger = logging.getLogger(f"{__name__}.ScalpingV7Engine")
        self.logger.info(
            f"🚀 ScalpingV7Engine initialized | "
            f"SL={self.config['sl_pct'] * 100}% | "
            f"Trail={self.config['trailing_activation'] * 100}%/{
                self.config['trailing_distance'] * 100
            }% | "
            f"Confluence≥{self.config['min_confluence']} | "
            f"MaxPos={self.config['max_positions']}"
        )

    # ============================================================
    # DATA PREPARATION
    # ============================================================
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add all required indicators to raw OHLCV DataFrame.
        Expects columns: open, high, low, close, volume, timestamp
        Returns DataFrame with all indicators added.
        """
        if df is None or len(df) < self.config["min_bars"]:
            return df

        df = df.copy()

        # EMAs
        df["ema8"] = _ema(df["close"], 8)
        df["ema21"] = _ema(df["close"], 21)
        df["ema55"] = _ema(df["close"], 55)

        # RSI
        df["rsi"] = _rsi(df["close"])

        # MACD
        df["macd_l"], df["macd_s"], df["macd_h"] = _macd(df["close"])

        # ATR
        df["atr"] = _atr(df["high"], df["low"], df["close"])

        # SuperTrend
        df["st"], df["st_dir"] = _supertrend(df["high"], df["low"], df["close"])

        # Bollinger Bands
        df["bbu"], df["bbm"], df["bbl"] = _bbands(df["close"])

        # ADX
        df["adx"], df["pdi"], df["mdi"] = _adx_calc(df["high"], df["low"], df["close"])

        # Volume
        df["vol_ma"] = df["volume"].rolling(20).mean()
        df["vol_r"] = df["volume"] / df["vol_ma"]

        # Candle anatomy
        df["body"] = abs(df["close"] - df["open"])
        df["range"] = df["high"] - df["low"]
        df["uwk"] = df["high"] - df[["close", "open"]].max(axis=1)
        df["lwk"] = df[["close", "open"]].min(axis=1) - df["low"]
        df["bull"] = df["close"] > df["open"]

        # Support/Resistance
        df["res20"] = df["high"].rolling(20).max()
        df["sup20"] = df["low"].rolling(20).min()

        return df

    # ============================================================
    # 4H TREND (from 1H data)
    # ============================================================
    def get_4h_trend(self, df: pd.DataFrame, idx: int = -1) -> str:
        """
        Determine 4H trend direction from 1H data.
        Uses EMA21 vs EMA55 relationship + price position.

        Returns: 'UP', 'DOWN', or 'NEUTRAL'
        """
        if idx == -1:
            idx = len(df) - 2

        if idx < 20:
            return "NEUTRAL"

        row = df.iloc[idx]
        e21 = row.get("ema21")
        e55 = row.get("ema55")

        if pd.isna(e21) or pd.isna(e55):
            return "NEUTRAL"

        close = row["close"]
        if e21 > e55 and close > e21:
            return "UP"
        elif e21 < e55 and close < e21:
            return "DOWN"
        return "NEUTRAL"

    # ============================================================
    # ENTRY DETECTION
    # ============================================================
    def detect_entry(self, df: pd.DataFrame, context, idx: int = -1) -> Optional[Dict]:
        """Detect entry signal — V7.1 cognitive + V7 fallback."""
        if isinstance(context, dict):
            trend = context.get("trend", "NEUTRAL")
        else:
            trend = str(context) if context else "NEUTRAL"

        if idx == -1:
            idx = len(df) - 2

        if idx < 55:
            return None

        # V7.1: Try cognitive entry first (runs even in NEUTRAL — breakout
        # doesn't need trend)
        if self.config.get("use_cognitive_entry", False):
            cog_signal = self._detect_cognitive(df, idx, trend)
            if cog_signal:
                cog_signal = self._apply_atr_sl(df, idx, cog_signal)
                return cog_signal

        # V7 fallback requires directional trend
        if trend == "NEUTRAL":
            return None
        row = df.iloc[idx]

        if trend == "UP":
            st_dir = row.get("st_dir")
            if not pd.isna(st_dir) and st_dir != 1:
                return None
            pdi = row.get("pdi", 0)
            mdi = row.get("mdi", 0)
            if not pd.isna(pdi) and not pd.isna(mdi) and pdi <= mdi:
                return None
            result = self._detect_long(df, idx)
            if result:
                result = self._apply_atr_sl(df, idx, result)
                return result

        if trend == "DOWN":
            st_dir = row.get("st_dir")
            if not pd.isna(st_dir) and st_dir != -1:
                return None
            pdi = row.get("pdi", 0)
            mdi = row.get("mdi", 0)
            if not pd.isna(pdi) and not pd.isna(mdi) and mdi <= pdi:
                return None
            result = self._detect_short(df, idx)
            if result:
                result = self._apply_atr_sl(df, idx, result)
                return result

        return None

    # ============================================================
    # V7.1 COGNITIVE ENTRY STRATEGIES
    # ============================================================
    def _detect_cognitive(
        self, df: pd.DataFrame, idx: int, trend: str
    ) -> Optional[Dict]:
        """
        Cognitive entry: 5 strategies verified across 35 experiments.
        Winning strategies: trend_cont, trend_cont_short, breakout, reversal
        Blocked strategies: pullback (-$11), vol_expand (-$7)
        """
        blocked = self.config.get("blocked_cognitive", [])
        ds = df.iloc[max(0, idx - 60) : idx + 1]
        if len(ds) < 20:
            return None

        cur = ds["close"].iloc[-1]
        cl = ds["close"]
        row = df.iloc[idx]

        e8 = cl.ewm(span=8, adjust=False).mean()
        e21 = cl.ewm(span=21, adjust=False).mean()
        e55 = cl.ewm(span=55, adjust=False).mean() if len(cl) >= 55 else e21

        rsi_val = row.get("rsi", 50)
        if pd.isna(rsi_val):
            rsi_val = 50
        adx_val = row.get("adx", 20)
        if pd.isna(adx_val):
            adx_val = 20
        vol = ds["volume"]
        vol_avg = vol.rolling(20).mean().iloc[-1] if len(vol) >= 20 else vol.mean()
        vr = vol.iloc[-1] / vol_avg if vol_avg > 0 else 1

        # Strategy 1: Trend Continuation LONG — دخول عند pullback لا عند القمة
        if trend == "UP" and e8.iloc[-1] > e21.iloc[-1] and cur > e55.iloc[-1]:
            dist21 = (cur - e21.iloc[-1]) / e21.iloc[-1]
            dist55 = (cur - e55.iloc[-1]) / e55.iloc[-1]
            if 0 <= dist21 <= 0.03 or 0 <= dist55 <= 0.05:
                sl = min(e55.iloc[-1] * 0.995, cur * 0.965)
                return self._cog_signal(
                    "LONG",
                    cur,
                    sl,
                    "trend_cont",
                    8,
                    min(85, 50 + adx_val * 0.8),
                )

        # Strategy 2: Pullback LONG — دخول عند ارتداد من EMA21
        if "pullback" not in blocked and trend == "UP":
            dist21 = (cur - e21.iloc[-1]) / e21.iloc[-1]
            bull = cl.iloc[-1] > ds["open"].iloc[-1]
            if -0.01 <= dist21 <= 0.015 and cur > e55.iloc[-1] and 35 <= rsi_val <= 60:
                sl = min(e55.iloc[-1] * 0.995, cur * 0.97)
                return self._cog_signal("LONG", cur, sl, "pullback", 7, 65)

        # Strategy 3: Breakout LONG — اختراق مع حجم مقبول
        if len(ds) >= 20:
            resistance = ds["high"].tail(20).quantile(0.85)
            if cur > resistance and vr > 1.2:
                sl = resistance * 0.965
                return self._cog_signal("LONG", cur, sl, "breakout", 8, 70)

        # Strategy 4: EMA Bounce — ارتداد من EMA8 أو EMA21
        if trend == "UP" and len(cl) >= 20:
            dist8 = (
                (cur - e8.iloc[-1]) / e8.iloc[-1] if not pd.isna(e8.iloc[-1]) else 999
            )
            if -0.005 <= dist8 <= 0.005 and vr > 0.9:
                prev_bull = cl.iloc[-1] > ds["open"].iloc[-1]
                if prev_bull or rsi_val > 45:
                    sl = (
                        e21.iloc[-1] * 0.995
                        if not pd.isna(e21.iloc[-1])
                        else cur * 0.97
                    )
                    return self._cog_signal("LONG", cur, sl, "ema_bounce", 7, 60)

        # Strategy 5: RSI Reversal — دخول عند تشبع بيعي في اتجاه صاعد
        if trend == "UP" and rsi_val < 40:
            bull = cl.iloc[-1] > ds["open"].iloc[-1]
            if bull and vr > 0.8:
                sl = ds["low"].tail(10).min() * 0.995
                return self._cog_signal("LONG", cur, sl, "rsi_reversal", 6, 55)

        # Strategy 6: Trend Continuation SHORT
        if (
            trend == "DOWN"
            and e8.iloc[-1] < e21.iloc[-1]
            and adx_val > 25
            and cur < e8.iloc[-1]
            and vr > 0.8
        ):
            dist = (e8.iloc[-1] - cur) / e8.iloc[-1]
            if dist < 0.015:
                sl = max(e21.iloc[-1], cur * 1.008)
                return self._cog_signal(
                    "SHORT",
                    cur,
                    sl,
                    "trend_cont_short",
                    7,
                    min(80, 50 + adx_val * 0.7),
                )

        return None

    def _cog_signal(self, side, price, sl, strategy, score, confidence):
        """Build cognitive entry signal dict with TP levels"""
        risk = abs(price - sl) / price
        tp1 = price * (1 + risk * 1.5)
        tp2 = price * (1 + risk * 2.5)
        tp3 = price * (1 + risk * 4.0)
        return {
            "side": side,
            "entry_price": price,
            "stop_loss": sl,
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "take_profit_3": tp3,
            "risk_pct": risk * 100,
            "score": score,
            "timing_count": 1,
            "signals": [strategy],
            "strategy": strategy,
            "signal_type": f"SCALP_V71_COG_{strategy.upper()}",
            "confidence": min(95, confidence),
        }

    # ============================================================
    # V7.1 ATR-BASED ADAPTIVE SL
    # ============================================================
    def _apply_atr_sl(self, df: pd.DataFrame, idx: int, signal: Dict) -> Dict:
        """Replace fixed SL with ATR-based adaptive SL if enabled"""
        if not self.config.get("use_atr_sl", False):
            return signal

        va = _get_vol_analyzer()
        if va is None:
            return signal

        try:
            df_slice = df.iloc[max(0, idx - 50) : idx + 1]
            vol_result = va.analyze(df_slice)
            atr = vol_result.get("atr", 0)
            if atr <= 0:
                return signal

            mult = self.config.get("atr_sl_multiplier", 2.5)
            entry = signal["entry_price"]

            if signal["side"] == "LONG":
                signal["stop_loss"] = entry - atr * mult
            else:
                signal["stop_loss"] = entry + atr * mult
        except Exception as e:
            self.logger.debug(f"ATR SL fallback to fixed: {e}")

        return signal

    def _detect_long(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """Detect LONG entry signals - exact v7 logic"""
        row = df.iloc[idx]
        prev = df.iloc[idx - 1]
        timing = []
        cond = []
        score = 0
        current = row["close"]

        # Volume filter
        if pd.isna(row.get("vol_r")) or row["vol_r"] < 0.9:
            return None

        # ---- TIMING SIGNALS (2 points each) ----

        # SuperTrend flip bullish
        if not pd.isna(row["st_dir"]) and not pd.isna(prev["st_dir"]):
            if prev["st_dir"] == -1 and row["st_dir"] == 1:
                timing.append("st_flip")
                score += 2

        # MACD crossover bullish
        if not pd.isna(row["macd_l"]) and not pd.isna(prev["macd_l"]):
            if prev["macd_l"] < prev["macd_s"] and row["macd_l"] > row["macd_s"]:
                timing.append("macd_x")
                score += 2

        # RSI bounce from oversold
        if not pd.isna(row["rsi"]) and not pd.isna(prev["rsi"]):
            if prev["rsi"] < 35 and row["rsi"] > prev["rsi"] and row["rsi"] < 55:
                timing.append("rsi_bounce")
                score += 2

        # Bullish engulfing
        if row["range"] > 0 and row["body"] > 0:
            if (
                not prev["bull"]
                and row["bull"]
                and row["close"] > prev["open"]
                and row["open"] < prev["close"]
            ):
                timing.append("engulf")
                score += 2

        # Breakout with volume
        if not pd.isna(row.get("res20")):
            prev_res = df["high"].iloc[max(0, idx - 21) : idx - 1].max()
            if not pd.isna(prev_res) and current > prev_res and row["vol_r"] > 1.5:
                timing.append("breakout")
                score += 2

        # Bollinger Band bounce
        if not pd.isna(row["bbl"]) and not pd.isna(prev["bbl"]):
            if prev["low"] <= prev["bbl"] and current > row["bbl"] and row["bull"]:
                timing.append("bb_bounce")
                score += 2

        # Hammer candle
        if row["range"] > 0 and row["body"] > 0:
            if (
                row["lwk"] > row["body"] * 2
                and row["uwk"] < row["body"] * 0.3
                and row["bull"]
            ):
                timing.append("hammer")
                score += 2

        # ---- CONDITION SIGNALS (1 point each) ----

        # EMA alignment bullish
        if (
            not pd.isna(row["ema8"])
            and not pd.isna(row["ema21"])
            and not pd.isna(row["ema55"])
        ):
            if row["ema8"] > row["ema21"] > row["ema55"]:
                cond.append("ema_up")
                score += 1

        # SuperTrend bullish (not counting flip twice)
        if (
            not pd.isna(row["st_dir"])
            and row["st_dir"] == 1
            and "st_flip" not in timing
        ):
            cond.append("st_bull")
            score += 1

        # RSI momentum
        if not pd.isna(row["rsi"]) and not pd.isna(prev["rsi"]):
            if 40 < row["rsi"] < 65 and row["rsi"] > prev["rsi"]:
                cond.append("rsi_mom")
                score += 1

        # MACD rising
        if not pd.isna(row["macd_h"]) and not pd.isna(prev["macd_h"]):
            if row["macd_h"] > 0 and row["macd_h"] > prev["macd_h"]:
                cond.append("macd_up")
                score += 1

        # Near EMA8
        if not pd.isna(row["ema8"]):
            if abs(current - row["ema8"]) / current < 0.004:
                cond.append("near_ema")
                score += 1

        # ADX trend bullish
        if (
            not pd.isna(row["adx"])
            and row["adx"] > 20
            and not pd.isna(row["pdi"])
            and not pd.isna(row["mdi"])
        ):
            if row["pdi"] > row["mdi"]:
                cond.append("adx_bull")
                score += 1

        # High volume
        if not pd.isna(row["vol_r"]) and row["vol_r"] > 1.3:
            cond.append("hi_vol")
            score += 1

        # ---- PENALTIES ----
        if not pd.isna(row["rsi"]) and row["rsi"] > 72:
            score -= 3
        if not pd.isna(row["st_dir"]) and row["st_dir"] == -1:
            score -= 2

        # ---- QUALITY GATE ----
        all_signals = timing + cond
        timing_count = len(timing)

        if score < self.config["min_confluence"]:
            return None
        if timing_count < self.config["min_timing"]:
            return None
        if (
            self.config["require_quality"]
            and timing_count < 2
            and "breakout" not in all_signals
        ):
            return None

        # Determine primary strategy
        strategy = "mixed"
        for s in [
            "breakout",
            "st_flip",
            "macd_x",
            "rsi_bounce",
            "engulf",
            "bb_bounce",
            "hammer",
        ]:
            if s in all_signals:
                strategy = s
                break

        # A3: Block losing LONG patterns (backtest verified: negative PnL)
        if strategy in ("macd_x", "st_flip", "engulf"):
            return None

        # Entry price = current close (will be executed at next bar open in
        # live)
        entry_price = current
        sl_price = entry_price * (1 - self.config["sl_pct"])
        risk = abs(entry_price - sl_price) / entry_price

        return {
            "side": "LONG",
            "entry_price": entry_price,
            "stop_loss": sl_price,
            "take_profit_1": entry_price * (1 + risk * 1.5),
            "take_profit_2": entry_price * (1 + risk * 2.5),
            "take_profit_3": entry_price * (1 + risk * 4.0),
            "risk_pct": risk * 100,
            "score": score,
            "timing_count": timing_count,
            "signals": all_signals,
            "strategy": strategy,
            "signal_type": f"SCALP_V7_LONG_{strategy.upper()}",
            "confidence": min(95, 50 + score * 5),
        }

    def _detect_short(self, df: pd.DataFrame, idx: int) -> Optional[Dict]:
        """Detect SHORT entry signals - exact v7 logic"""
        row = df.iloc[idx]
        prev = df.iloc[idx - 1]
        timing = []
        cond = []
        score = 0
        current = row["close"]

        # Volume filter
        if pd.isna(row.get("vol_r")) or row["vol_r"] < 0.9:
            return None

        # ---- TIMING SIGNALS (2 points each) ----

        # SuperTrend flip bearish
        if not pd.isna(row["st_dir"]) and not pd.isna(prev["st_dir"]):
            if prev["st_dir"] == 1 and row["st_dir"] == -1:
                timing.append("st_flip_bear")
                score += 2

        # MACD crossover bearish
        if not pd.isna(row["macd_l"]) and not pd.isna(prev["macd_l"]):
            if prev["macd_l"] > prev["macd_s"] and row["macd_l"] < row["macd_s"]:
                timing.append("macd_x_bear")
                score += 2

        # RSI rejection from overbought
        if not pd.isna(row["rsi"]) and not pd.isna(prev["rsi"]):
            if prev["rsi"] > 65 and row["rsi"] < prev["rsi"] and row["rsi"] > 45:
                timing.append("rsi_reject")
                score += 2

        # Bearish engulfing
        if row["range"] > 0 and row["body"] > 0:
            if (
                prev["bull"]
                and not row["bull"]
                and row["open"] > prev["close"]
                and row["close"] < prev["open"]
            ):
                timing.append("engulf_bear")
                score += 2

        # Breakdown with volume
        if not pd.isna(row.get("sup20")):
            prev_sup = df["low"].iloc[max(0, idx - 21) : idx - 1].min()
            if not pd.isna(prev_sup) and current < prev_sup and row["vol_r"] > 1.5:
                timing.append("breakdown")
                score += 2

        # Bollinger Band rejection
        if not pd.isna(row["bbu"]) and not pd.isna(prev["bbu"]):
            if prev["high"] >= prev["bbu"] and current < row["bbu"] and not row["bull"]:
                timing.append("bb_reject")
                score += 2

        # Shooting star
        if row["range"] > 0 and row["body"] > 0:
            if (
                row["uwk"] > row["body"] * 2
                and row["lwk"] < row["body"] * 0.3
                and not row["bull"]
            ):
                timing.append("shooting_star")
                score += 2

        # ---- CONDITION SIGNALS (1 point each) ----

        # EMA alignment bearish
        if (
            not pd.isna(row["ema8"])
            and not pd.isna(row["ema21"])
            and not pd.isna(row["ema55"])
        ):
            if row["ema8"] < row["ema21"] < row["ema55"]:
                cond.append("ema_dn")
                score += 1

        # SuperTrend bearish
        if (
            not pd.isna(row["st_dir"])
            and row["st_dir"] == -1
            and "st_flip_bear" not in timing
        ):
            cond.append("st_bear")
            score += 1

        # RSI declining
        if not pd.isna(row["rsi"]) and not pd.isna(prev["rsi"]):
            if 35 < row["rsi"] < 60 and row["rsi"] < prev["rsi"]:
                cond.append("rsi_dn")
                score += 1

        # MACD falling
        if not pd.isna(row["macd_h"]) and not pd.isna(prev["macd_h"]):
            if row["macd_h"] < 0 and row["macd_h"] < prev["macd_h"]:
                cond.append("macd_dn")
                score += 1

        # ADX trend bearish
        if (
            not pd.isna(row["adx"])
            and row["adx"] > 20
            and not pd.isna(row["pdi"])
            and not pd.isna(row["mdi"])
        ):
            if row["mdi"] > row["pdi"]:
                cond.append("adx_bear")
                score += 1

        # High volume
        if not pd.isna(row["vol_r"]) and row["vol_r"] > 1.3:
            cond.append("hi_vol")
            score += 1

        # ---- PENALTIES ----
        if not pd.isna(row["rsi"]) and row["rsi"] < 28:
            score -= 3
        if not pd.isna(row["st_dir"]) and row["st_dir"] == 1:
            score -= 2

        # ---- QUALITY GATE ----
        all_signals = timing + cond
        timing_count = len(timing)

        if score < self.config["min_confluence"]:
            return None
        if timing_count < self.config["min_timing"]:
            return None
        if (
            self.config["require_quality"]
            and timing_count < 2
            and "breakdown" not in all_signals
        ):
            return None

        # Determine primary strategy
        strategy = "mixed"
        for s in [
            "breakdown",
            "st_flip_bear",
            "macd_x_bear",
            "rsi_reject",
            "engulf_bear",
            "bb_reject",
            "shooting_star",
        ]:
            if s in all_signals:
                strategy = s
                break

        # Block losing SHORT patterns (EXP10: verified net negative PnL)
        blocked_short = self.config.get("blocked_short", [])
        if strategy in blocked_short:
            return None

        entry_price = current
        sl_price = entry_price * (1 + self.config["sl_pct"])
        risk = abs(sl_price - entry_price) / entry_price

        return {
            "side": "SHORT",
            "entry_price": entry_price,
            "stop_loss": sl_price,
            "take_profit_1": entry_price * (1 - risk * 1.5),
            "take_profit_2": entry_price * (1 - risk * 2.5),
            "take_profit_3": entry_price * (1 - risk * 4.0),
            "risk_pct": risk * 100,
            "score": score,
            "timing_count": timing_count,
            "signals": all_signals,
            "strategy": strategy,
            "signal_type": f"SCALP_V7_SHORT_{strategy.upper()}",
            "confidence": min(95, 50 + score * 5),
        }

    # ============================================================
    # EXIT CHECK (for live position management)
    # ============================================================
    def check_exit_signal(self, df: pd.DataFrame, position: Dict) -> Dict:
        """
        Check exit conditions for an open position.
        Implements exact v7 trailing-only exit logic.

        Args:
            df: DataFrame with indicators (from prepare_data)
            position: Dict with keys:
                - entry_price: float
                - side: 'LONG' or 'SHORT'
                - peak: float (highest price for LONG, lowest for SHORT)
                - trail: float (current trailing stop level, 0 if not active)
                - sl: float (stop loss price)
                - entry_time: datetime
                - hold_hours: float (hours held)

        Returns:
            Dict with: should_exit, reason, exit_price, updated position fields
        """
        if df is None or len(df) < 3:
            return {"should_exit": False, "reason": "HOLD"}

        idx = len(df) - 1
        row = df.iloc[idx]
        hi = row["high"]
        lo = row["low"]
        cl = row["close"]

        entry = position["entry_price"]
        side = position.get("side", "LONG")
        peak = position.get("peak", entry)
        trail = position.get("trail", 0)
        sl = position.get(
            "sl",
            (
                entry * (1 - self.config["sl_pct"])
                if side == "LONG"
                else entry * (1 + self.config["sl_pct"])
            ),
        )

        updated = {}

        # ---- STOP LOSS ----
        if side == "LONG":
            # Update peak
            if hi > peak:
                peak = hi
                updated["peak"] = peak

            if lo <= sl:
                return {
                    "should_exit": True,
                    "reason": "STOP_LOSS",
                    "exit_price": sl,
                    "updated": updated,
                }

            # Trailing stop with B3: progressive tightening
            profit_pct = (peak - entry) / entry
            trail_dist = self.config["trailing_distance"]
            # B3: Tighten as profit grows (verified: PnL +$128, PF +0.09)
            if profit_pct >= 0.02:
                trail_dist = min(trail_dist, 0.002)  # +2% → 0.2% distance
            elif profit_pct >= 0.015:
                trail_dist = min(trail_dist, 0.003)  # +1.5% → 0.3%
            elif profit_pct >= 0.01:
                trail_dist = min(trail_dist, 0.0035)  # +1% → 0.35%

            if profit_pct >= self.config["trailing_activation"]:
                ts = peak * (1 - trail_dist)
                if ts > trail:
                    trail = ts
                    updated["trail"] = trail
                if trail > 0 and lo <= trail:
                    return {
                        "should_exit": True,
                        "reason": "TRAILING",
                        "exit_price": trail,
                        "updated": updated,
                    }

            # Breakeven trigger: move SL to entry when profit reaches threshold
            be_trigger = self.config.get("breakeven_trigger", 0)
            if be_trigger > 0 and profit_pct >= be_trigger and sl < entry:
                sl = entry * 1.0001
                updated["sl"] = sl

        else:  # SHORT
            # Update peak (lowest point)
            if lo < peak:
                peak = lo
                updated["peak"] = peak

            if hi >= sl:
                return {
                    "should_exit": True,
                    "reason": "STOP_LOSS",
                    "exit_price": sl,
                    "updated": updated,
                }

            # Trailing stop with B3: progressive tightening
            profit_pct = (entry - peak) / entry
            trail_dist = self.config["trailing_distance"]
            if profit_pct >= 0.02:
                trail_dist = min(trail_dist, 0.002)
            elif profit_pct >= 0.015:
                trail_dist = min(trail_dist, 0.003)
            elif profit_pct >= 0.01:
                trail_dist = min(trail_dist, 0.0035)

            if profit_pct >= self.config["trailing_activation"]:
                ts = peak * (1 + trail_dist)
                if trail == 0 or ts < trail:
                    trail = ts
                    updated["trail"] = trail
                if trail > 0 and hi >= trail:
                    return {
                        "should_exit": True,
                        "reason": "TRAILING",
                        "exit_price": trail,
                        "updated": updated,
                    }

            # Breakeven trigger: move SL to entry when profit reaches threshold
            be_trigger = self.config.get("breakeven_trigger", 0)
            if be_trigger > 0 and profit_pct >= be_trigger and sl > entry:
                sl = entry * 0.9999
                updated["sl"] = sl

        # ---- REVERSAL EXIT (only if in profit > 0.3%) ----
        if idx >= 2:
            prev = df.iloc[idx - 1]
            rev_score = 0

            if side == "LONG":
                pnl = (cl - entry) / entry
                if pnl > 0.003:
                    # SuperTrend flip bearish
                    if not pd.isna(row["st_dir"]) and not pd.isna(prev["st_dir"]):
                        if prev["st_dir"] == 1 and row["st_dir"] == -1:
                            rev_score += 3
                    # Bearish engulfing
                    if (
                        prev["bull"]
                        and not row["bull"]
                        and row["open"] > prev["close"]
                        and cl < prev["open"]
                    ):
                        rev_score += 2
                    # MACD cross bearish
                    if not pd.isna(row["macd_l"]) and not pd.isna(prev["macd_l"]):
                        if (
                            prev["macd_l"] > prev["macd_s"]
                            and row["macd_l"] < row["macd_s"]
                        ):
                            rev_score += 2
            else:  # SHORT
                pnl = (entry - cl) / entry
                if pnl > 0.003:
                    # SuperTrend flip bullish
                    if not pd.isna(row["st_dir"]) and not pd.isna(prev["st_dir"]):
                        if prev["st_dir"] == -1 and row["st_dir"] == 1:
                            rev_score += 3
                    # Bullish engulfing
                    if (
                        not prev["bull"]
                        and row["bull"]
                        and row["close"] > prev["open"]
                        and row["open"] < prev["close"]
                    ):
                        rev_score += 2
                    # MACD cross bullish
                    if not pd.isna(row["macd_l"]) and not pd.isna(prev["macd_l"]):
                        if (
                            prev["macd_l"] < prev["macd_s"]
                            and row["macd_l"] > row["macd_s"]
                        ):
                            rev_score += 2

            if rev_score >= 3:
                return {
                    "should_exit": True,
                    "reason": "REVERSAL",
                    "exit_price": cl,
                    "updated": updated,
                }

        # ---- TIME-BASED EXITS ----
        hold_hours = position.get("hold_hours", 0)

        # Max hold time
        if hold_hours >= self.config["max_hold_hours"]:
            return {
                "should_exit": True,
                "reason": "MAX_HOLD",
                "exit_price": cl,
                "updated": updated,
            }

        # Stagnant position (configurable hours, less than threshold movement)
        pnl_now = (cl - entry) / entry if side == "LONG" else (entry - cl) / entry
        stagnant_hours = self.config.get("stagnant_hours", 4)
        stagnant_threshold = self.config.get("stagnant_threshold", 0.002)
        if hold_hours >= stagnant_hours and abs(pnl_now) < stagnant_threshold:
            return {
                "should_exit": True,
                "reason": "STAGNANT",
                "exit_price": cl,
                "updated": updated,
            }

        # Early cut: exit losing trades after N hours if loss exceeds threshold
        early_cut_hours = self.config.get("early_cut_hours", 0)
        early_cut_loss = self.config.get("early_cut_loss", 0)
        if early_cut_hours > 0 and early_cut_loss > 0:
            if hold_hours >= early_cut_hours and pnl_now < -early_cut_loss:
                return {
                    "should_exit": True,
                    "reason": "EARLY_CUT",
                    "exit_price": cl,
                    "updated": updated,
                }

        # ---- HOLD ----
        return {
            "should_exit": False,
            "reason": "HOLD",
            "exit_price": cl,
            "updated": updated,
            "pnl_pct": pnl_now * 100 if "pnl_now" in dir() else 0,
            "trail_level": trail,
            "peak": peak,
        }


# ============================================================
# SINGLETON
# ============================================================
_scalping_v7_instance = None


def get_scalping_v7_engine(config: Dict = None) -> ScalpingV7Engine:
    """Get singleton ScalpingV7Engine instance"""
    global _scalping_v7_instance
    if _scalping_v7_instance is None:
        _scalping_v7_instance = ScalpingV7Engine(config)
    return _scalping_v7_instance
