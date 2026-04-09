#!/usr/bin/env python3

import logging
import pandas as pd
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class MTFConfirmationEngine:
    def __init__(self, data_provider=None):
        self.data_provider = data_provider

    def confirm_entry(
        self, symbol: str, signal_1h: Dict, df_1h: pd.DataFrame = None
    ) -> Dict:
        df_15m = self._get_data(symbol, "15m", 100)
        df_5m = self._get_data(symbol, "5m", 100)
        if df_15m is None or df_5m is None:
            return {"confirmed": False, "reason": "Data unavailable", "score": 0}

        df_15m = self._add_indicators(df_15m)
        df_5m = self._add_indicators(df_5m)

        strategy = signal_1h.get("strategy", "")
        is_trend_strategy = "Trend" in strategy

        reversal_15m = self._check_reversal_15m(df_15m, is_trend_strategy)
        momentum_5m = self._check_momentum_5m(df_5m, is_trend_strategy)
        trend_alignment = (
            self._check_trend_alignment(df_1h, df_15m, df_5m)
            if df_1h is not None
            else True
        )

        score = 0
        reasons = []

        if reversal_15m["confirmed"]:
            score += 40
            reasons.append(reversal_15m["reason"])
        elif reversal_15m.get("acceptable"):
            score += 30
            reasons.append("15m Pullback acceptable")

        if momentum_5m["confirmed"]:
            score += 35
            reasons.append(momentum_5m["reason"])
        elif momentum_5m.get("acceptable"):
            score += 25
            reasons.append("5m Momentum acceptable")

        if trend_alignment:
            score += 25
            reasons.append("Trend aligned across timeframes")

        confirmed = score >= 50
        return {
            "confirmed": confirmed,
            "score": score,
            "reason": "; ".join(reasons) if reasons else "No confirmation",
            "reversal_15m": reversal_15m,
            "momentum_5m": momentum_5m,
            "trend_alignment": trend_alignment,
        }

    def confirm_exit(
        self, symbol: str, position: Dict, df_1h: pd.DataFrame = None
    ) -> Dict:
        df_15m = self._get_data(symbol, "15m", 100)
        df_5m = self._get_data(symbol, "5m", 100)
        if df_15m is None or df_5m is None:
            return {"confirmed": False, "reason": "Data unavailable", "score": 0}

        df_15m = self._add_indicators(df_15m)
        df_5m = self._add_indicators(df_5m)

        weakness_15m = self._check_weakness_15m(df_15m)
        bearish_5m = self._check_bearish_5m(df_5m)

        score = 0
        reasons = []

        if weakness_15m["confirmed"]:
            score += 50
            reasons.append(weakness_15m["reason"])
        if bearish_5m["confirmed"]:
            score += 50
            reasons.append(bearish_5m["reason"])

        confirmed = score >= 50
        return {
            "confirmed": confirmed,
            "score": score,
            "reason": "; ".join(reasons) if reasons else "No exit confirmation",
            "weakness_15m": weakness_15m,
            "bearish_5m": bearish_5m,
        }

    def _get_data(
        self, symbol: str, timeframe: str, limit: int
    ) -> Optional[pd.DataFrame]:
        if not self.data_provider:
            return None
        try:
            return self.data_provider.get_historical_data(symbol, timeframe, limit)
        except Exception as e:
            logger.debug(f"   ⚠️ MTF {symbol} {timeframe} data failed: {e}")
            return None

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        close = df["close"]
        df["rsi"] = self._compute_rsi(close)
        df["ema8"] = close.ewm(span=8, adjust=False).mean()
        df["ema21"] = close.ewm(span=21, adjust=False).mean()

        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        return df

    def _compute_rsi(self, close, period=14):
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, float("inf"))
        return 100 - (100 / (1 + rs))

    def _check_reversal_15m(self, df: pd.DataFrame, is_trend_strategy=False) -> Dict:
        rsi = df["rsi"].iloc[-1]
        rsi_prev = df["rsi"].iloc[-2] if len(df) >= 2 else rsi
        macd_hist = df["macd_hist"].iloc[-1]
        macd_hist_prev = df["macd_hist"].iloc[-2] if len(df) >= 2 else macd_hist

        rsi_oversold = rsi < 40
        rsi_turning_up = rsi > rsi_prev
        macd_bullish_cross = macd_hist_prev < 0 and macd_hist > macd_hist_prev

        if rsi_oversold and rsi_turning_up:
            return {
                "confirmed": True,
                "reason": f"15m RSI oversold ({rsi:.0f}) and turning up",
            }
        if macd_bullish_cross:
            return {"confirmed": True, "reason": "15m MACD histogram turning up"}

        if is_trend_strategy and 40 <= rsi <= 65:
            return {
                "confirmed": False,
                "acceptable": True,
                "reason": f"15m RSI neutral ({rsi:.0f}) - Pullback OK",
            }

        return {
            "confirmed": False,
            "acceptable": False,
            "reason": f"15m RSI={rsi:.0f} no reversal",
        }

    def _check_momentum_5m(self, df: pd.DataFrame, is_trend_strategy=False) -> Dict:
        close = df["close"].iloc[-1]
        ema8 = df["ema8"].iloc[-1]
        ema21 = df["ema21"].iloc[-1]
        rsi = df["rsi"].iloc[-1]
        macd_hist = df["macd_hist"].iloc[-1]

        price_above_ema8 = close > ema8
        ema8_above_ema21 = ema8 > ema21
        rsi_bullish = rsi > 40
        macd_positive = macd_hist > 0

        score = sum([price_above_ema8, ema8_above_ema21, rsi_bullish, macd_positive])
        if score >= 3:
            return {"confirmed": True, "reason": f"5m momentum bullish ({score}/4)"}

        if score >= 2 and rsi < 75:
            return {
                "confirmed": False,
                "acceptable": True,
                "reason": f"5m momentum neutral ({score}/4) - Entry OK",
            }

        return {
            "confirmed": False,
            "acceptable": False,
            "reason": f"5m momentum weak ({score}/4)",
        }

    def _check_trend_alignment(
        self, df_1h: pd.DataFrame, df_15m: pd.DataFrame, df_5m: pd.DataFrame
    ) -> bool:
        ema21_1h = df_1h["ema21"].iloc[-1]
        ema55_1h = df_1h["ema55"].iloc[-1] if "ema55" in df_1h.columns else ema21_1h
        close_1h = df_1h["close"].iloc[-1]

        trend_1h_up = close_1h > ema21_1h and ema21_1h >= ema55_1h
        trend_1h_down = close_1h < ema21_1h and ema21_1h <= ema55_1h

        rsi_15m = df_15m["rsi"].iloc[-1]
        rsi_5m = df_5m["rsi"].iloc[-1]

        if trend_1h_up:
            if rsi_15m > 75 or rsi_5m > 80:
                return False
            return True

        if trend_1h_down:
            if rsi_15m < 25 or rsi_5m < 20:
                return False
            return True

        return False

    def _check_weakness_15m(self, df: pd.DataFrame) -> Dict:
        rsi = df["rsi"].iloc[-1]
        rsi_prev = df["rsi"].iloc[-2] if len(df) >= 2 else rsi
        macd_hist = df["macd_hist"].iloc[-1]
        macd_hist_prev = df["macd_hist"].iloc[-2] if len(df) >= 2 else macd_hist

        rsi_overbought = rsi > 65
        rsi_turning_down = rsi < rsi_prev
        macd_bearish = macd_hist < macd_hist_prev and macd_hist < 0

        if rsi_overbought and rsi_turning_down:
            return {
                "confirmed": True,
                "reason": f"15m RSI overbought ({rsi:.0f}) and turning down",
            }
        if macd_bearish:
            return {"confirmed": True, "reason": "15m MACD histogram bearish"}
        return {"confirmed": False, "reason": f"15m RSI={rsi:.0f} no weakness"}

    def _check_bearish_5m(self, df: pd.DataFrame) -> Dict:
        close = df["close"].iloc[-1]
        ema8 = df["ema8"].iloc[-1]
        ema21 = df["ema21"].iloc[-1]
        rsi = df["rsi"].iloc[-1]
        macd_hist = df["macd_hist"].iloc[-1]

        price_below_ema8 = close < ema8
        ema8_below_ema21 = ema8 < ema21
        rsi_bearish = rsi < 55
        macd_negative = macd_hist < 0

        score = sum([price_below_ema8, ema8_below_ema21, rsi_bearish, macd_negative])
        if score >= 3:
            return {"confirmed": True, "reason": f"5m bearish ({score}/4)"}
        return {"confirmed": False, "reason": f"5m not bearish ({score}/4)"}
