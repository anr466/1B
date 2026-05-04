#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scalping V8 Strategy — Adapter for BaseStrategy interface
==========================================================
Wraps ScalpingV8Engine with the unified BaseStrategy interface.
Drop-in replacement for ScalpingV7Strategy.

Performance (60-day backtest, $1000, 12 coins):
- V8: PF=1.72 | WR=62.2% | R:R=1.24 | All 12 symbols profitable
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Optional

from backend.strategies.base_strategy import BaseStrategy
from backend.strategies.scalping_v8_engine import ScalpingV8Engine


class ScalpingV8Strategy(BaseStrategy):
    """
    Adapter: wraps ScalpingV8Engine with BaseStrategy interface.
    Supports 3 modes: normal, aggressive, conservative.
    """

    name = "scalping_v8"
    version = "8.0"
    description = "Scalping V8 — smart exit, PF=1.72, WR=62.2%"

    def __init__(self, config: Dict = None, mode: str = "normal"):
        super().__init__()
        self._engine = ScalpingV8Engine(config, mode)
        self._config = self._engine.config
        self._mode = mode

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._engine.prepare_data(df)

    def detect_entry(self, df: pd.DataFrame, context: Dict) -> Optional[Dict]:
        trend = context.get("trend", "NEUTRAL")
        signal = self._engine.detect_entry(df, trend)

        if signal is None:
            return None

        return {
            "signal": signal.get("side", "LONG"),
            "side": signal.get("side", "LONG"),
            "strategy": signal.get("strategy", self.name),
            "entry_price": signal.get("entry_price", 0),
            "stop_loss": signal.get("stop_loss", 0),
            "take_profit": 0,
            "score": signal.get("score", 0),
            "confidence": signal.get("confidence", 50),
            "reasons": signal.get("signals", []),
            "metadata": {
                "timing_count": signal.get("timing_count", 0),
                "signal_type": signal.get("signal_type", ""),
                "engine_version": "v8",
                "mode": self._mode,
            },
            "_raw_signal": signal,
        }

    def check_exit(self, df: pd.DataFrame, position: Dict) -> Dict:
        entry_price = position.get("entry_price", 0)
        position_type = position.get("position_type", "long").upper()
        peak = position.get("highest_price", entry_price)
        trail = position.get("trailing_sl_price", 0) or 0
        sl = position.get("stop_loss", 0)

        entry_time = position.get("created_at")
        hold_hours = 0
        if entry_time:
            if isinstance(entry_time, str):
                try:
                    entry_time = datetime.fromisoformat(
                        entry_time.replace("Z", "+00:00")
                    )
                except Exception:
                    entry_time = None
            if isinstance(entry_time, datetime):
                now_dt = (
                    datetime.now(entry_time.tzinfo)
                    if entry_time.tzinfo
                    else datetime.now()
                )
                hold_hours = (now_dt - entry_time).total_seconds() / 3600

        if position_type == "SHORT":
            if peak == 0 or peak >= entry_price:
                peak = entry_price
        else:
            if peak == 0 or peak <= entry_price:
                peak = entry_price

        if not sl or sl <= 0:
            if position_type == "SHORT":
                sl = entry_price * (1 + self._config.get("sl_pct", 0.008))
            else:
                sl = entry_price * (1 - self._config.get("sl_pct", 0.008))

        pos_data = {
            "entry_price": entry_price,
            "side": position_type,
            "peak": peak,
            "trail": trail,
            "sl": sl,
            "entry_time": entry_time,
            "hold_hours": hold_hours,
        }

        result = self._engine.check_exit_signal(df, pos_data)

        return {
            "should_exit": result.get("should_exit", False),
            "reason": result.get("reason", "HOLD"),
            "exit_price": result.get("exit_price", 0),
            "updated": result.get("updated", {}),
            "pnl_pct": result.get("pnl_pct", 0),
            "trail_level": result.get("trail_level", 0),
            "peak": result.get("peak", peak),
        }

    def get_config(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "mode": self._mode,
            "timeframe": "1h",
            "sl_pct": self._config.get("sl_pct", 0.008),
            "trailing_activation": self._config["trailing_activation"],
            "trailing_distance": self._config["trailing_distance"],
            "breakeven_trigger": self._config["breakeven_trigger"],
            "max_positions": self._config["max_positions"],
            "max_hold_hours": self._config["max_hold_hours"],
            "stagnant_hours": self._config.get("stagnant_hours", 6),
            "breakeven_at": self._config.get("breakeven_at", 0.01),
        }

    def get_market_trend(self, df: pd.DataFrame) -> str:
        return self._engine.get_4h_trend(df, len(df) - 2)

    def extract_entry_indicators(self, df: pd.DataFrame) -> Dict:
        try:
            last_row = df.iloc[-2]
            return {
                "rsi": (
                    float(last_row.get("rsi", 50))
                    if not pd.isna(last_row.get("rsi"))
                    else None
                ),
                "macd": (
                    float(last_row.get("macd_l", 0))
                    if not pd.isna(last_row.get("macd_l"))
                    else None
                ),
                "volume_ratio": (
                    float(last_row.get("vol_r", 1.0))
                    if not pd.isna(last_row.get("vol_r"))
                    else None
                ),
                "ema_trend": (
                    "up"
                    if (
                        not pd.isna(last_row.get("ema8"))
                        and not pd.isna(last_row.get("ema21"))
                        and last_row["ema8"] > last_row["ema21"]
                    )
                    else "down"
                ),
                "atr_pct": (
                    float(last_row.get("atr", 0) / last_row["close"] * 100)
                    if not pd.isna(last_row.get("atr"))
                    else None
                ),
            }
        except Exception:
            return {}


_v8_strategy_instance = None


def get_scalping_v8_strategy(
    config: Dict = None, mode: str = "normal"
) -> ScalpingV8Strategy:
    global _v8_strategy_instance
    if _v8_strategy_instance is None:
        _v8_strategy_instance = ScalpingV8Strategy(config, mode)
    return _v8_strategy_instance
