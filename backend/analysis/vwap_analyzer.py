"""
VWAP Analyzer — محلل VWAP (Volume Weighted Average Price)
===========================================================
يحسب VWAP ويحلل موقعه بالنسبة للسعر الحالي لتحديد:
- اتجاه السيولة المؤسسية
- قوة الاتجاه
- إشارات التداول

متوافق مع Smart Money Orchestrator
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class VWAPAnalyzer:
    """محلل VWAP للسيولة المؤسسية"""

    def __init__(self):
        self.logger = logger
        self.vwap_deviation_threshold = 0.02  # 2% deviation
        self.volume_spike_threshold = 2.0     # 2x average volume

    def analyze_vwap_structure(self, df_5m: pd.DataFrame) -> Dict:
        """تحليل هيكل VWAP وتوليد الإشارات"""
        try:
            if df_5m is None or len(df_5m) < 20:
                return self._empty_result("Insufficient data")

            df = df_5m.copy()
            df["vwap"] = self._calculate_vwap(df)
            df["vwap_deviation"] = (df["close"] - df["vwap"]) / df["vwap"] * 100

            current_price = float(df["close"].iloc[-1])
            current_vwap = float(df["vwap"].iloc[-1])
            deviation = float(df["vwap_deviation"].iloc[-1])

            # VWAP strength analysis
            strength = self._analyze_strength(df, current_price, current_vwap)
            reliability = self._calculate_reliability(df)
            signals = self._generate_signals(df, deviation, current_price)

            return {
                "current_vwap": round(current_vwap, 8),
                "current_price": round(current_price, 8),
                "deviation_pct": round(deviation, 4),
                "vwap_strength": {
                    "overall_strength": round(strength["overall"], 1),
                    "reliability_score": round(reliability, 1),
                    "trend_alignment": strength["trend_alignment"],
                    "volume_confirmation": strength["volume_confirmation"],
                },
                "trading_signals": {
                    "primary_signal": signals["primary"],
                    "secondary_signal": signals["secondary"],
                    "bias": signals["bias"],
                    "confidence": signals["confidence"],
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error analyzing VWAP: {e}")
            return self._empty_result(f"Error: {str(e)}")

    def _calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """حساب VWAP تراكمي"""
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        price_volume = typical_price * df["volume"]
        cumulative_pv = price_volume.cumsum()
        cumulative_volume = df["volume"].cumsum()
        vwap = cumulative_pv / cumulative_volume.replace(0, np.nan)
        return vwap

    def _analyze_strength(
        self, df: pd.DataFrame, current_price: float, current_vwap: float
    ) -> Dict:
        """تحليل قوة VWAP"""
        # Trend alignment: is price above/below VWAP consistently?
        above_vwap = (df["close"] > df["vwap"]).sum()
        below_vwap = (df["close"] < df["vwap"]).sum()
        total = above_vwap + below_vwap

        if total > 0:
            consistency = max(above_vwap, below_vwap) / total * 100
            if above_vwap > below_vwap:
                trend_alignment = "ABOVE"  # Bullish bias
                overall = max(60, consistency)
            else:
                trend_alignment = "BELOW"  # Bearish bias
                overall = max(60, consistency)
        else:
            trend_alignment = "NEUTRAL"
            overall = 50

        # Volume confirmation
        avg_volume = df["volume"].iloc[-20:].mean()
        recent_volume = df["volume"].iloc[-5:].mean()
        vol_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        volume_confirmation = vol_ratio > self.volume_spike_threshold

        # Adjust strength based on volume
        if volume_confirmation:
            overall = min(100, overall + 15)
        elif vol_ratio < 0.5:
            overall = max(10, overall - 10)

        return {
            "overall": overall,
            "trend_alignment": trend_alignment,
            "volume_confirmation": volume_confirmation,
        }

    def _calculate_reliability(self, df: pd.DataFrame) -> float:
        """حساب موثوقية VWAP الحالية"""
        try:
            # How often does price bounce from VWAP?
            df_copy = df.copy()
            df_copy["cross_above"] = (df_copy["low"].shift(1) < df_copy["vwap"].shift(1)) & (df_copy["close"] > df_copy["vwap"])
            df_copy["cross_below"] = (df_copy["high"].shift(1) > df_copy["vwap"].shift(1)) & (df_copy["close"] < df_copy["vwap"])

            # Count successful bounces
            touches = df_copy["cross_above"].sum() + df_copy["cross_below"].sum()
            if touches > 0:
                reliability = min(100, touches / len(df_copy) * 100 * 5)
            else:
                reliability = 40  # Default moderate reliability

            return float(reliability)
        except Exception:
            return 40.0

    def _generate_signals(
        self, df: pd.DataFrame, deviation: float, current_price: float
    ) -> Dict:
        """توليد إشارات التداول من VWAP"""
        vwap_val = float(df["vwap"].iloc[-1])

        # Determine bias
        if deviation > self.vwap_deviation_threshold * 100:
            bias = "BEARISH"  # Overextended above VWAP
        elif deviation < -self.vwap_deviation_threshold * 100:
            bias = "BULLISH"  # Oversold below VWAP
        elif deviation > 0:
            bias = "MILDLY_BULLISH"
        elif deviation < 0:
            bias = "MILDLY_BEARISH"
        else:
            bias = "NEUTRAL"

        # Primary signal
        abs_dev = abs(deviation)
        if abs_dev < 0.5 and current_price > vwap_val:
            primary_signal = "BUY_BOUNCE"
            confidence = 70
        elif abs_dev < 0.5 and current_price < vwap_val:
            primary_signal = "SELL_BOUNCE"
            confidence = 70
        elif deviation > self.vwap_deviation_threshold * 100:
            primary_signal = "MEAN_REVERT_SHORT"
            confidence = 65
        elif deviation < -self.vwap_deviation_threshold * 100:
            primary_signal = "MEAN_REVERT_LONG"
            confidence = 65
        else:
            # Check recent momentum
            recent = df["close"].iloc[-10:].values
            if len(recent) >= 2 and recent[-1] > recent[0]:
                primary_signal = "BULLISH_TREND"
                confidence = 55
            else:
                primary_signal = "WAIT_FOR_DIRECTION"
                confidence = 40

        return {
            "primary": primary_signal,
            "secondary": "NEUTRAL",
            "bias": bias,
            "confidence": confidence,
        }

    def _empty_result(self, error_msg: str = "") -> Dict:
        return {
            "current_vwap": 0,
            "current_price": 0,
            "deviation_pct": 0,
            "error": error_msg,
            "vwap_strength": {
                "overall_strength": 0,
                "reliability_score": 0,
                "trend_alignment": "NEUTRAL",
                "volume_confirmation": False,
            },
            "trading_signals": {
                "primary_signal": "NEUTRAL",
                "secondary_signal": "NEUTRAL",
                "bias": "NEUTRAL",
                "confidence": 0,
            },
        }
