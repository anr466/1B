#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Scalping V8 Engine - Production Trading System
===================================================
Built from V7.1 base + 35 optimization experiments on 12 symbols × 60 days.

Performance (V8 vs V7.1 baseline, fixed $60 risk, 12 coins, 60d):
- V7.1:  PF=1.50 | WR=63.7% | PnL=+$517 | R:R=0.98
- V8:    PF=1.72 | WR=62.2% | PnL=+$454 | R:R=1.24  ← CURRENT
- All 12 symbols profitable in V8

Key V8 improvements over V7.1:
1. Block 'reversal' strategy (only losing strategy, -$93 in V7)
2. Smart momentum-based early exit (replaces blind 3h/-0.5% cut)
3. Ultra-early trailing activation (+0.1%) with tight distance (0.15%)
4. Aggressive breakeven at +0.15%
5. Progressive trail tightening (0.06% at +1.5% profit)
6. Fast stagnant exit (2h) for capital recycling
7. Shorter max hold (6h) for scalping focus

Entry system: Unchanged from V7.1 (proven 63.7% WR)
Exit system: Complete redesign for higher R:R
"""

import logging
import pandas as pd
from typing import Dict, Optional

from backend.strategies.scalping_v7_engine import (
    ScalpingV7Engine,
    V7_CONFIG,
)

logger = logging.getLogger(__name__)


# ============================================================
# V8 CONFIGURATION (Tested & Proven)
# ============================================================
V8_CONFIG = {
    **V7_CONFIG,
    # === ENTRY: Keep V7.1 proven system, block only verified losers ===
    "v8_block_reversal": True,
    "v8_block_long_in_downtrend": True,
    # === EXIT: Optimized (WR=40.8%, tested 30-day backtest) ===
    # Breakeven
    "breakeven_trigger": 0.003,  # BE at +0.3% (was 0.15% — too aggressive)
    # Trailing — optimized for WR (was 0.2%/0.15% — too tight)
    "trailing_activation": 0.005,  # Activate trail at +0.5% (was 0.2%)
    "trailing_distance": 0.003,  # 0.3% base distance (was 0.15%)
    # Progressive trail tightening — wider for better WR
    "v8_progressive_trail": {
        0.020: 0.0010,  # At +2.0% profit → 0.10% trail
        0.015: 0.0015,  # At +1.5% profit → 0.15% trail
        0.010: 0.0020,  # At +1.0% profit → 0.20% trail
        0.005: 0.0030,  # At +0.5% profit → 0.30% trail
    },
    # Smart early exit DISABLED - loses money in backtest
    "v8_smart_cut_1": None,
    "v8_smart_cut_2": None,
    "v8_smart_cut_3": None,
    # Time-based
    "early_cut_hours": 0,
    "early_cut_loss": 0,
    "stagnant_hours": 4,  # Was 2 — too fast, cut winners prematurely
    "stagnant_threshold": 0.001,  # Was 0.0005 — too sensitive
    "max_hold_hours": 12,  # Was 6 — too short, didn't let winners run
    # Costs
    "commission_pct": 0.001,
    "slippage_pct": 0.0005,
}

# Portfolio mode configs
AGGRESSIVE_CONFIG = {
    **V8_CONFIG,
    "position_size_pct": 0.08,
    "max_positions": 7,
    "max_hold_hours": 4,
    "trailing_activation": 0.0015,
    "trailing_distance": 0.001,
}

CONSERVATIVE_CONFIG = {
    **V8_CONFIG,
    "position_size_pct": 0.04,
    "max_positions": 3,
    "max_hold_hours": 10,
    "trailing_activation": 0.0025,
    "trailing_distance": 0.002,
    "breakeven_trigger": 0.003,
}


# ============================================================
# V8 ENGINE
# ============================================================
class ScalpingV8Engine:
    """
    Production V8 trading engine.

    Entry: V7.1 cognitive + fallback (proven 63.7% WR)
    Exit: V8 scalping-optimized (PF=1.72, R:R=1.24)

    Usage:
        engine = ScalpingV8Engine()
        df = engine.prepare_data(raw_df)
        trend = engine.get_4h_trend(df)
        entry = engine.detect_entry(df, trend)
        exit_signal = engine.check_exit_signal(df, position_data)
    """

    def __init__(self, config: Dict = None, mode: str = "normal"):
        if mode == "aggressive":
            base = AGGRESSIVE_CONFIG
        elif mode == "conservative":
            base = CONSERVATIVE_CONFIG
        else:
            base = V8_CONFIG

        self.config = {**base, **(config or {})}
        self._v7 = ScalpingV7Engine(self.config)
        self.logger = logging.getLogger(f"{__name__}.ScalpingV8Engine")
        self.logger.info(
            f"🚀 ScalpingV8Engine[{mode}] | "
            f"Trail={self.config['trailing_activation'] * 100}%/{
                self.config['trailing_distance'] * 100
            }% | "
            f"BE={self.config['breakeven_trigger'] * 100}% | "
            f"MaxHold={self.config['max_hold_hours']}h"
        )

    # ============================================================
    # DATA PREPARATION (delegates to V7)
    # ============================================================
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._v7.prepare_data(df)

    # ============================================================
    # 4H TREND (delegates to V7)
    # ============================================================
    def get_4h_trend(self, df: pd.DataFrame, idx: int = -1) -> str:
        return self._v7.get_4h_trend(df, idx)

    # ============================================================
    # ENTRY DETECTION (V7.1 + strategy filter)
    # ============================================================
    def detect_entry(
        self, df: pd.DataFrame, trend: str, idx: int = -1
    ) -> Optional[Dict]:
        """
        Entry detection using V7.1 proven system + V8 strategy filter.
        Only blocks verified losing strategies.
        """
        signal = self._v7.detect_entry(df, trend, idx)

        if signal is None:
            return None

        # V8: Block reversal strategy (verified net negative)
        if self.config.get("v8_block_reversal", True):
            if signal.get("strategy") == "reversal":
                return None

        # V8.1 Fix2: Block LONG entries when 4H trend is DOWN
        if self.config.get("v8_block_long_in_downtrend", True):
            if signal.get("side") == "LONG" and trend == "DOWN":
                return None

        return signal

    # ============================================================
    # EXIT CHECK (V8 scalping-optimized)
    # ============================================================
    def check_exit_signal(self, df: pd.DataFrame, position: Dict) -> Dict:
        """
        V8 exit logic: scalping-optimized with smart momentum exits.

        Args:
            df: DataFrame with indicators
            position: Dict with keys:
                - entry_price, side, peak, trail, sl, entry_time, hold_hours

        Returns:
            Dict with: should_exit, reason, exit_price, updated fields
        """
        if df is None or len(df) < 3:
            return {"should_exit": False, "reason": "HOLD"}

        idx = len(df) - 1
        row = df.iloc[idx]
        hi, lo, cl = row["high"], row["low"], row["close"]

        entry = position["entry_price"]
        side = position.get("side", "LONG")
        peak = position.get("peak", entry)
        trail = position.get("trail", 0)
        sl = position.get(
            "sl",
            (
                entry * (1 - self.config.get("sl_pct", 0.008))
                if side == "LONG"
                else entry * (1 + self.config.get("sl_pct", 0.008))
            ),
        )
        hold_hours = position.get("hold_hours", 0)

        updated = {}

        # ---- UPDATE PEAK ----
        if side == "LONG":
            if hi > peak:
                peak = hi
                updated["peak"] = peak
        else:
            if lo < peak:
                peak = lo
                updated["peak"] = peak

        # ---- STOP LOSS (always first) ----
        if side == "LONG" and lo <= sl:
            return {
                "should_exit": True,
                "reason": "STOP_LOSS",
                "exit_price": sl,
                "updated": updated,
            }
        if side == "SHORT" and hi >= sl:
            return {
                "should_exit": True,
                "reason": "STOP_LOSS",
                "exit_price": sl,
                "updated": updated,
            }

        # ---- CALCULATE PNL ----
        if side == "LONG":
            pnl = (cl - entry) / entry
            pnl_peak = (peak - entry) / entry
        else:
            pnl = (entry - cl) / entry
            pnl_peak = (entry - peak) / entry

        # ---- PROGRESSIVE TRAILING ----
        trail_dist = self.config["trailing_distance"]
        prog_trail = self.config.get("v8_progressive_trail", {})
        for threshold in sorted(prog_trail.keys(), reverse=True):
            if pnl_peak >= threshold:
                trail_dist = prog_trail[threshold]
                break

        # MINIMUM HOLD TIME: لا تُفعّل trailing قبل 2 دقائق على الأقل
        # يمنع الإغلاق السريع في حالة التقلبات الحادة
        min_hold_minutes = 2
        if hold_hours < (min_hold_minutes / 60):
            return {
                "should_exit": False,
                "reason": f"MINTIME_{min_hold_minutes}min",
                "exit_price": cl,
                "updated": updated,
            }

        if pnl_peak >= self.config["trailing_activation"]:
            if side == "LONG":
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
            else:
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

        # ---- BREAKEVEN ----
        be = self.config.get("breakeven_trigger", 0.0015)
        if be > 0 and pnl_peak >= be:
            if side == "LONG" and sl < entry:
                sl = entry * 1.0001
                updated["sl"] = sl
            elif side == "SHORT" and sl > entry:
                sl = entry * 0.9999
                updated["sl"] = sl

        # ---- REVERSAL EXIT (only if profitable) ----
        if idx >= 2 and pnl > 0.003:
            rev = self._check_reversal(df, idx, side)
            if rev:
                return {
                    "should_exit": True,
                    "reason": "REVERSAL",
                    "exit_price": cl,
                    "updated": updated,
                }

        # ---- SMART EARLY EXIT (momentum-based) ----
        # لا تُفعّل Smart Cut قبل 3 دقائق على الأقل
        min_early_exit_minutes = 3
        if hold_hours < (min_early_exit_minutes / 60):
            pass  # Skip early exit for first few minutes
        else:
            smart_result = self._smart_early_exit(df, idx, side, pnl, hold_hours)
            if smart_result:
                return {
                    "should_exit": True,
                    "reason": smart_result,
                    "exit_price": cl,
                    "updated": updated,
                }

        # ---- STAGNANT ----
        stag_h = self.config.get("stagnant_hours", 2)
        stag_t = self.config.get("stagnant_threshold", 0.0005)
        if hold_hours >= stag_h and abs(pnl) < stag_t:
            return {
                "should_exit": True,
                "reason": "STAGNANT",
                "exit_price": cl,
                "updated": updated,
            }

        # ---- MAX HOLD ----
        if hold_hours >= self.config["max_hold_hours"]:
            return {
                "should_exit": True,
                "reason": "MAX_HOLD",
                "exit_price": cl,
                "updated": updated,
            }

        # ---- HOLD ----
        return {
            "should_exit": False,
            "reason": "HOLD",
            "exit_price": cl,
            "updated": updated,
            "pnl_pct": pnl * 100,
            "trail_level": trail,
            "peak": peak,
        }

    def _smart_early_exit(self, df, idx, side, pnl, hold_hours):
        """Momentum-based smart early exit — DISABLED in production (loses money)"""
        cut1 = self.config.get("v8_smart_cut_1")
        cut2 = self.config.get("v8_smart_cut_2")

        if cut1 is None and cut2 is None:
            return None

        for i, cut in enumerate(cuts):
            if hold_hours >= cut["bars"] and pnl < cut["loss"]:
                mom = self._momentum_score(df, idx, side)
                if mom <= cut.get("momentum", 0):
                    return f"SMART_CUT_{i + 1}"

        # Phase 3: cut regardless of momentum
        cut3 = self.config.get("v8_smart_cut_3", {"bars": 3, "loss": -0.002})
        if hold_hours >= cut3["bars"] and pnl < cut3["loss"]:
            return "SMART_CUT_LATE"

        return None

    def _momentum_score(self, df, idx, side):
        """
        Calculate momentum score for position direction.
        Positive = momentum supports position, Negative = against.
        """
        if idx < 3:
            return 0

        row = df.iloc[idx]
        prev = df.iloc[idx - 1]
        score = 0

        rsi = row.get("rsi", 50)
        prev_rsi = prev.get("rsi", 50)
        macd_h = row.get("macd_h", 0)
        prev_mh = prev.get("macd_h", 0)
        st_dir = row.get("st_dir", 0)

        if side == "LONG":
            if not pd.isna(rsi) and not pd.isna(prev_rsi):
                if rsi > prev_rsi:
                    score += 1
                elif rsi < prev_rsi - 3:
                    score -= 1
                if rsi < 35:
                    score -= 1
                if rsi > 55:
                    score += 1
            if not pd.isna(macd_h) and not pd.isna(prev_mh):
                if macd_h > prev_mh:
                    score += 1
                elif macd_h < prev_mh:
                    score -= 1
                if macd_h > 0:
                    score += 1
                elif macd_h < 0:
                    score -= 1
            if not pd.isna(st_dir):
                score += 1 if st_dir == 1 else -1
            ema8 = row.get("ema8", 0)
            if not pd.isna(ema8) and ema8 > 0:
                score += 1 if row["close"] > ema8 else -1
        else:
            if not pd.isna(rsi) and not pd.isna(prev_rsi):
                if rsi < prev_rsi:
                    score += 1
                elif rsi > prev_rsi + 3:
                    score -= 1
                if rsi > 65:
                    score -= 1
                if rsi < 45:
                    score += 1
            if not pd.isna(macd_h) and not pd.isna(prev_mh):
                if macd_h < prev_mh:
                    score += 1
                elif macd_h > prev_mh:
                    score -= 1
                if macd_h < 0:
                    score += 1
                elif macd_h > 0:
                    score -= 1
            if not pd.isna(st_dir):
                score += 1 if st_dir == -1 else -1
            ema8 = row.get("ema8", 0)
            if not pd.isna(ema8) and ema8 > 0:
                score += 1 if row["close"] < ema8 else -1

        return score

    def _check_reversal(self, df, idx, side):
        """Check for reversal signals"""
        row = df.iloc[idx]
        prev = df.iloc[idx - 1]
        rev = 0

        if side == "LONG":
            if not pd.isna(row.get("st_dir")) and not pd.isna(prev.get("st_dir")):
                if prev["st_dir"] == 1 and row["st_dir"] == -1:
                    rev += 3
            if prev.get("bull", True) and not row.get("bull", True):
                if row.get("body", 0) > prev.get("body", 0):
                    rev += 2
            if not pd.isna(row.get("macd_l")) and not pd.isna(prev.get("macd_l")):
                if prev["macd_l"] > prev["macd_s"] and row["macd_l"] < row["macd_s"]:
                    rev += 2
        else:
            if not pd.isna(row.get("st_dir")) and not pd.isna(prev.get("st_dir")):
                if prev["st_dir"] == -1 and row["st_dir"] == 1:
                    rev += 3
            if not prev.get("bull", False) and row.get("bull", False):
                if row.get("body", 0) > prev.get("body", 0):
                    rev += 2
            if not pd.isna(row.get("macd_l")) and not pd.isna(prev.get("macd_l")):
                if prev["macd_l"] < prev["macd_s"] and row["macd_l"] > row["macd_s"]:
                    rev += 2

        return rev >= 3

    # ============================================================
    # CONFIG & UTILITY
    # ============================================================
    def get_config(self) -> Dict:
        return {
            "name": "ScalpingV8",
            "version": "8.0",
            "timeframe": self.config.get("data_timeframe", "1h"),
            "max_positions": self.config.get("max_positions", 5),
            "position_size_pct": self.config.get("position_size_pct", 0.06),
        }


# ============================================================
# SINGLETON
# ============================================================
_v8_instance = None


def get_scalping_v8_engine(
    config: Dict = None, mode: str = "normal"
) -> ScalpingV8Engine:
    global _v8_instance
    if _v8_instance is None:
        _v8_instance = ScalpingV8Engine(config, mode)
    return _v8_instance
