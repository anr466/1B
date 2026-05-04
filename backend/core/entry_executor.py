#!/usr/bin/env python3

import logging
import pandas as pd
from typing import Dict, Optional
from backend.core.coin_state_analyzer import CoinState
from backend.utils.indicator_calculator import compute_atr

logger = logging.getLogger(__name__)


class EntryExecutor:
    def confirm_entry(
        self, symbol: str, df: pd.DataFrame, state: CoinState, route: Dict
    ) -> Optional[Dict]:
        if df is None or len(df) < 55:
            return None

        close = df["close"]
        cur = close.iloc[-1]
        prev_close = close.iloc[-2]
        prev_open = df["open"].iloc[-2]
        prev2_close = close.iloc[-3]
        prev2_open = df["open"].iloc[-3]
        prev_bull = prev_close > prev_open
        prev2_bull = prev2_close > prev2_open

        e8 = close.ewm(span=8, adjust=False).mean().iloc[-1]
        e21 = close.ewm(span=21, adjust=False).mean().iloc[-1]
        e55 = (
            close.ewm(span=55, adjust=False).mean().iloc[-1]
            if len(close) >= 55
            else e21
        )

        rsi_val = self._get(df, "rsi", 50)
        adx_val = self._get(df, "adx", 20)
        atr, _ = self._compute_atr(df)
        vol_ratio = self._vol_ratio(df)

        entry_type = route.get("entry_type", "")
        sl_mult = route.get("sl_atr_mult", 3.5)
        tp_ratio = route.get("tp_ratio", 2.0)

        signal = None
        if entry_type == "pullback_to_ema":
            signal = self._pullback_entry(
                cur,
                e8,
                e21,
                e55,
                rsi_val,
                vol_ratio,
                prev_bull,
                prev2_bull,
                atr,
                sl_mult,
                tp_ratio,
                state,
            )
        elif entry_type == "resistance_break":
            signal = self._breakout_entry(
                cur, df, vol_ratio, prev_bull, prev2_bull, atr, sl_mult, tp_ratio, state
            )
        elif entry_type == "support_bounce":
            signal = self._range_entry(
                cur, df, rsi_val, vol_ratio, prev_bull, atr, sl_mult, tp_ratio, state
            )

        if signal:
            signal.update(
                {
                    "symbol": symbol,
                    "state": state,
                    "entry_type": entry_type,
                    "rsi": round(rsi_val, 1),
                    "adx": round(adx_val, 1),
                    "atr_pct": round(atr / cur * 100, 2) if cur > 0 else 0,
                    "vol_ratio": round(vol_ratio, 2),
                }
            )

        return signal

    def _pullback_entry(
        self,
        cur,
        e8,
        e21,
        e55,
        rsi,
        vol_ratio,
        prev_bull,
        prev2_bull,
        atr,
        sl_mult,
        tp_ratio,
        state,
    ):
        if e8 <= e21 or cur <= e55:
            return None
        dist21 = (cur - e21) / e21 if e21 > 0 else 999
        dist55 = (cur - e55) / e55 if e55 > 0 else 999
        in_pullback = (0 <= dist21 <= 0.03) or (0 <= dist55 <= 0.05)
        if not in_pullback:
            return None
        if not prev_bull and rsi < 40:
            return None
        if state.momentum == "DECAYING":
            return None
        sl = min(e55 * 0.995, cur - atr * sl_mult) if e55 > 0 else cur * 0.965
        risk = (cur - sl) / cur
        tp = cur + risk * tp_ratio * cur
        score = 75
        if prev_bull and prev2_bull:
            score += 5
        if state.trend_confirmed_4h:
            score += 5
        return {
            "side": "LONG",
            "entry_price": cur,
            "stop_loss": sl,
            "take_profit": tp,
            "risk_pct": round(risk * 100, 2),
            "score": score,
            "confidence": min(90, 55 + rsi * 0.3),
        }

    def _breakout_entry(
        self, cur, df, vol_ratio, prev_bull, prev2_bull, atr, sl_mult, tp_ratio, state
    ):
        if len(df) < 20:
            return None
        resistance = df["high"].tail(20).quantile(0.95)
        if cur <= resistance:
            return None
        if vol_ratio < 1.5:
            return None
        if not prev_bull:
            return None
        if state.volume_trend == "DECLINING":
            return None
        sl = resistance * 0.965
        risk = (cur - sl) / cur
        tp = cur + risk * tp_ratio * cur
        score = 80
        if prev_bull and prev2_bull:
            score += 5
        if vol_ratio > 2.0:
            score += 5
        return {
            "side": "LONG",
            "entry_price": cur,
            "stop_loss": sl,
            "take_profit": tp,
            "risk_pct": round(risk * 100, 2),
            "score": score,
            "confidence": min(85, 60 + vol_ratio * 5),
        }

    def _range_entry(
        self, cur, df, rsi, vol_ratio, prev_bull, atr, sl_mult, tp_ratio, state
    ):
        if len(df) < 30:
            return None
        support = df["low"].tail(30).quantile(0.15)
        resistance = df["high"].tail(30).quantile(0.85)
        range_w = (resistance - support) / support if support > 0 else 0
        if range_w < 0.5:
            return None
        dist_to_support = (cur - support) / support if support > 0 else 999
        if dist_to_support > 0.03:
            return None
        if vol_ratio < 0.5:
            return None
        if not prev_bull and rsi > 55:
            return None
        sl = support * 0.975
        risk = (cur - sl) / cur
        tp = cur + risk * tp_ratio * cur
        rr_ratio = (tp - cur) / (cur - sl) if cur > sl else 0
        if rr_ratio < 1.2:
            return None
        score = 65
        if state.obv_trend == "RISING":
            score += 5
        return {
            "side": "LONG",
            "entry_price": cur,
            "stop_loss": sl,
            "take_profit": tp,
            "risk_pct": round(risk * 100, 2),
            "score": score,
            "confidence": 60,
        }

    def _get(self, df, name, default):
        val = df.get(name, pd.Series([default] * len(df))).iloc[-1]
        return default if pd.isna(val) else val

    def _compute_atr(self, df):
        atr_series = compute_atr(df)
        atr = atr_series.iloc[-1]
        return atr, atr

    def _vol_ratio(self, df):
        vol = df["volume"]
        vol_avg = vol.rolling(20).mean().iloc[-1] if len(vol) >= 20 else vol.mean()
        return vol.iloc[-1] / vol_avg if vol_avg > 0 else 1
