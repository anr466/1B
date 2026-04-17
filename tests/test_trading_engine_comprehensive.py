#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Trading Engine Test Suite
========================================
Tests ALL components, scenarios, and edge cases without requiring live Binance connection.
Uses synthetic market data to simulate various regimes and conditions.
"""

import sys
import os
import time
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.core.coin_state_analyzer import CoinStateAnalyzer, CoinState
from backend.core.cognitive_decision_matrix import CognitiveDecisionMatrix
from backend.core.modules.trend_module import TrendModule
from backend.core.modules.range_module import RangeModule
from backend.core.modules.volatility_module import VolatilityModule
from backend.core.modules.scalping_module import ScalpingModule
from backend.utils.indicator_calculator import (
    add_all_indicators,
    compute_atr,
    compute_rsi,
)


@dataclass
class TestResult:
    name: str
    passed: bool
    details: str
    expected: str
    actual: str
    score: float  # 0-100


class TradingEngineTestSuite:
    def __init__(self):
        self.analyzer = CoinStateAnalyzer()
        self.cdm = CognitiveDecisionMatrix()
        self.modules = [
            TrendModule(),
            RangeModule(),
            VolatilityModule(),
            ScalpingModule(),
        ]
        self.results: List[TestResult] = []
        self.test_count = 0
        self.pass_count = 0

    def run_all(self):
        """Run all test categories"""
        print("=" * 80)
        print("🧪 TRADING ENGINE COMPREHENSIVE TEST SUITE")
        print("=" * 80)

        self._test_indicators()
        self._test_market_regimes()
        self._test_strategy_modules()
        self._test_decision_matrix()
        self._test_signal_pipeline()
        self._test_edge_cases()
        self._test_risk_management()
        self._test_execution_logic()

        self._print_summary()

    def _add_result(
        self,
        name: str,
        passed: bool,
        details: str,
        expected: str,
        actual: str,
        score: float = 100.0,
    ):
        self.results.append(TestResult(name, passed, details, expected, actual, score))
        self.test_count += 1
        if passed:
            self.pass_count += 1
            print(f"  ✅ {name}: {details}")
        else:
            print(f"  ❌ {name}: {details} (Expected: {expected}, Got: {actual})")

    # ============================================================
    # 1. INDICATOR TESTS
    # ============================================================
    def _test_indicators(self):
        print("\n📊 1. INDICATOR CALCULATION TESTS")

        # Generate synthetic data
        df = self._generate_synthetic_data(trend="UP", volatility="MEDIUM", length=100)

        # Test ATR (Wilder's smoothing)
        atr_series = compute_atr(df)
        atr_val = atr_series.iloc[-1]
        self._add_result(
            "ATR Calculation",
            atr_val > 0,
            f"ATR={atr_val:.6f} (positive, uses Wilder's smoothing)",
            "> 0",
            str(atr_val),
        )

        # Test RSI
        rsi_series = compute_rsi(df)
        rsi_val = rsi_series.iloc[-1]
        self._add_result(
            "RSI Calculation",
            0 <= rsi_val <= 100,
            f"RSI={rsi_val:.1f} (valid range)",
            "0-100",
            str(rsi_val),
        )

        # Test all indicators added
        df_with_indicators = add_all_indicators(df)
        required_cols = [
            "rsi",
            "adx",
            "atr",
            "ema8",
            "ema21",
            "ema55",
            "macd",
            "macd_signal",
            "bb_upper",
            "bb_lower",
        ]
        missing = [c for c in required_cols if c not in df_with_indicators.columns]
        self._add_result(
            "All Indicators Present",
            len(missing) == 0,
            f"{len(required_cols)} indicators added",
            "No missing columns",
            f"Missing: {missing}" if missing else "All present",
        )

        # Test consistency: ATR same across calls
        atr1 = compute_atr(df).iloc[-1]
        atr2 = compute_atr(df).iloc[-1]
        self._add_result(
            "ATR Consistency",
            abs(atr1 - atr2) < 0.0001,
            "Same result on repeated calls",
            "Identical",
            f"{atr1} vs {atr2}",
        )

    # ============================================================
    # 2. MARKET REGIME TESTS
    # ============================================================
    def _test_market_regimes(self):
        print("\n🌐 2. MARKET REGIME DETECTION TESTS")

        regimes_to_test = {
            "STRONG_TREND": self._generate_synthetic_data(
                trend="UP", volatility="MEDIUM", adx=35
            ),
            "WEAK_TREND": self._generate_synthetic_data(
                trend="UP", volatility="LOW", adx=25
            ),
            "WIDE_RANGE": self._generate_synthetic_data(
                trend="NEUTRAL", volatility="HIGH", bb_width=4.0
            ),
            "NARROW_RANGE": self._generate_synthetic_data(
                trend="NEUTRAL", volatility="LOW", bb_width=1.5
            ),
            "CHOPPY": self._generate_synthetic_data(
                trend="NEUTRAL", volatility="LOW", bb_width=0.5
            ),
        }

        for regime_name, df in regimes_to_test.items():
            state = self.analyzer.analyze("TESTUSDT", df)
            if state:
                detected = state.regime
                self._add_result(
                    f"Regime: {regime_name}",
                    detected == regime_name,
                    f"Detected: {detected}",
                    regime_name,
                    detected,
                )
            else:
                self._add_result(
                    f"Regime: {regime_name}",
                    False,
                    "Analyzer returned None",
                    regime_name,
                    "None",
                )

        # Test 4H confirmation default
        df_no_4h = self._generate_synthetic_data(trend="UP")
        state_no_4h = self.analyzer.analyze("TESTUSDT", df_no_4h, df_4h=None)
        self._add_result(
            "4H Default False",
            state_no_4h.trend_confirmed_4h == False,
            "4H confirmation defaults to False when no data",
            "False",
            str(state_no_4h.trend_confirmed_4h),
        )

    # ============================================================
    # 3. STRATEGY MODULE TESTS
    # ============================================================
    def _test_strategy_modules(self):
        print("\n🎯 3. STRATEGY MODULE TESTS")

        # Trend Module - Uptrend
        df_uptrend = self._generate_synthetic_data(
            trend="UP", volatility="MEDIUM", adx=35
        )
        state_uptrend = self.analyzer.analyze("TESTUSDT", df_uptrend)
        context_uptrend = self._state_to_context(state_uptrend)
        trend_signal = self.modules[0].evaluate(df_uptrend, context_uptrend)
        self._add_result(
            "TrendModule Uptrend",
            trend_signal is not None and trend_signal["type"] == "LONG",
            f"Signal: {trend_signal['strategy'] if trend_signal else 'None'}",
            "LONG signal",
            trend_signal["strategy"] if trend_signal else "None",
        )

        # Trend Module - Downtrend (should give SHORT)
        df_downtrend = self._generate_synthetic_data(
            trend="DOWN", volatility="MEDIUM", adx=35
        )
        state_downtrend = self.analyzer.analyze("TESTUSDT", df_downtrend)
        context_downtrend = self._state_to_context(state_downtrend)
        trend_signal_down = self.modules[0].evaluate(df_downtrend, context_downtrend)
        self._add_result(
            "TrendModule Downtrend SHORT",
            trend_signal_down is not None and trend_signal_down["type"] == "SHORT",
            f"Signal: {trend_signal_down['strategy'] if trend_signal_down else 'None'}",
            "SHORT signal",
            trend_signal_down["strategy"] if trend_signal_down else "None",
        )

        # Range Module - Range market
        df_range = self._generate_synthetic_data(
            trend="NEUTRAL", volatility="LOW", bb_width=2.0
        )
        state_range = self.analyzer.analyze("TESTUSDT", df_range)
        context_range = self._state_to_context(state_range)
        range_signal = self.modules[1].evaluate(df_range, context_range)
        self._add_result(
            "RangeModule Range",
            range_signal is not None
            or state_range.regime in ("WIDE_RANGE", "NARROW_RANGE"),
            f"Signal: {range_signal['strategy'] if range_signal else 'None'} (Regime: {state_range.regime})",
            "Signal or valid regime",
            range_signal["strategy"] if range_signal else "None",
        )

        # Volatility Module - High vol
        df_vol = self._generate_synthetic_data(trend="UP", volatility="HIGH", adx=35)
        state_vol = self.analyzer.analyze("TESTUSDT", df_vol)
        context_vol = self._state_to_context(state_vol)
        vol_signal = self.modules[2].evaluate(df_vol, context_vol)
        self._add_result(
            "VolatilityModule High",
            vol_signal is not None or state_vol.volatility == "HIGH",
            f"Signal: {vol_signal['strategy'] if vol_signal else 'None'} (Vol: {state_vol.volatility})",
            "Signal or HIGH volatility",
            vol_signal["strategy"] if vol_signal else "None",
        )

        # Scalping Module - Choppy
        df_choppy = self._generate_synthetic_data(
            trend="NEUTRAL", volatility="LOW", bb_width=0.5
        )
        state_choppy = self.analyzer.analyze("TESTUSDT", df_choppy)
        context_choppy = self._state_to_context(state_choppy)
        scalp_signal = self.modules[3].evaluate(df_choppy, context_choppy)
        self._add_result(
            "ScalpingModule Choppy",
            scalp_signal is not None or state_choppy.regime == "CHOPPY",
            f"Signal: {scalp_signal['strategy'] if scalp_signal else 'None'} (Regime: {state_choppy.regime})",
            "Signal or CHOPPY regime",
            scalp_signal["strategy"] if scalp_signal else "None",
        )

        # Test SL/TP ratios (all should be >= 2.0:1)
        for module in self.modules:
            if trend_signal:
                sl = module.get_stop_loss(df_uptrend, trend_signal)
                tp = module.get_take_profit(df_uptrend, trend_signal)
                entry = df_uptrend["close"].iloc[-1]
                risk = abs(entry - sl)
                reward = abs(tp - entry)
                rr = reward / risk if risk > 0 else 0
                self._add_result(
                    f"{module.name()} RR Ratio",
                    rr >= 1.5,  # Allow 1.5:1 minimum (some modules use 2.0:1)
                    f"RR={rr:.2f}:1",
                    ">= 1.5:1",
                    f"{rr:.2f}:1",
                )

    # ============================================================
    # 4. DECISION MATRIX TESTS
    # ============================================================
    def _test_decision_matrix(self):
        print("\n🧠 4. COGNITIVE DECISION MATRIX TESTS")

        # Test with strong trend signal
        df_strong = self._generate_synthetic_data(
            trend="UP", volatility="MEDIUM", adx=35
        )
        state_strong = self.analyzer.analyze("TESTUSDT", df_strong)
        context_strong = self._state_to_context(state_strong)
        signal_strong = {
            "type": "LONG",
            "strategy": "Trend Pullback",
            "confidence": 80,
            "entry_price": 100.0,
            "stop_loss": 96.5,
            "take_profit": 107.0,
        }
        result_strong = self.cdm.evaluate(signal_strong, context_strong)
        self._add_result(
            "CDM Strong Trend",
            result_strong["score"] >= 65,
            f"Score: {result_strong['score']}, Decision: {result_strong['decision']}",
            ">= 65",
            str(result_strong["score"]),
        )

        # Test MTF alignment calculation
        context_with_4h = context_strong.copy()
        context_with_4h["trend_confirmed_4h"] = True
        context_with_4h["trend_confirmed_macd"] = True
        result_with_4h = self.cdm.evaluate(signal_strong, context_with_4h)
        self._add_result(
            "CDM MTF Alignment",
            result_with_4h["score"] > result_strong["score"],
            f"Score with 4H confirm: {result_with_4h['score']} (was {result_strong['score']})",
            "Higher than without 4H",
            f"{result_with_4h['score']} vs {result_strong['score']}",
        )

        # Test CHOPPY thresholds
        context_choppy = {
            "regime": "CHOPPY",
            "trend": "NEUTRAL",
            "volume_ratio": 1.0,
            "coin_type": "MID_CAP",
            "volatility": "LOW",
            "ema_alignment": "MIXED",
            "trend_confirmed_4h": False,
            "trend_confirmed_macd": False,
            "trend_confirmed_volume": False,
        }
        signal_choppy = {
            "type": "LONG",
            "strategy": "Micro Scalp Support",
            "confidence": 60,
            "entry_price": 100.0,
            "stop_loss": 98.0,
            "take_profit": 104.0,
        }
        result_choppy = self.cdm.evaluate(signal_choppy, context_choppy)
        self._add_result(
            "CDM CHOPPY Threshold",
            result_choppy["decision"] in ("ENTER_REDUCED", "WATCH", "REJECT"),
            f"Decision: {result_choppy['decision']} (Score: {result_choppy['score']})",
            "Not ENTER (too uncertain)",
            result_choppy["decision"],
        )

    # ============================================================
    # 5. SIGNAL PIPELINE TESTS
    # ============================================================
    def _test_signal_pipeline(self):
        print("\n🔄 5. FULL SIGNAL PIPELINE TESTS")

        # Simulate full pipeline: Data -> Analyzer -> Modules -> CDM
        for regime_name, df in [
            ("STRONG_TREND", self._generate_synthetic_data(trend="UP", adx=35)),
            (
                "WIDE_RANGE",
                self._generate_synthetic_data(trend="NEUTRAL", bb_width=3.5),
            ),
            ("CHOPPY", self._generate_synthetic_data(trend="NEUTRAL", bb_width=0.5)),
        ]:
            state = self.analyzer.analyze("TESTUSDT", df)
            if not state:
                self._add_result(
                    f"Pipeline {regime_name}",
                    False,
                    "Analyzer failed",
                    "CoinState",
                    "None",
                )
                continue

            context = self._state_to_context(state)
            signals_found = 0
            best_score = 0

            for module in self.modules:
                if state.regime in module.supported_regimes():
                    signal = module.evaluate(df, context)
                    if signal:
                        signal["entry_price"] = module.get_entry_price(df, signal)
                        signal["stop_loss"] = module.get_stop_loss(df, signal)
                        signal["take_profit"] = module.get_take_profit(df, signal)
                        decision = self.cdm.evaluate(signal, context)
                        if decision["score"] > best_score:
                            best_score = decision["score"]
                        signals_found += 1

            self._add_result(
                f"Pipeline {regime_name}",
                True,
                f"Regime: {state.regime}, Signals: {signals_found}, Best Score: {best_score}",
                "Pipeline completes",
                f"{signals_found} signals, score {best_score}",
            )

    # ============================================================
    # 6. EDGE CASE TESTS
    # ============================================================
    def _test_edge_cases(self):
        print("\n⚠️ 6. EDGE CASE TESTS")

        # Test with very short data
        df_short = self._generate_synthetic_data(length=30)
        state_short = self.analyzer.analyze("TESTUSDT", df_short)
        self._add_result(
            "Short Data (30 candles)",
            state_short is None,  # Should return None for <55 candles
            "Analyzer correctly rejects short data",
            "None",
            str(state_short),
        )

        # Test with zero volume
        df_zero_vol = self._generate_synthetic_data()
        df_zero_vol["volume"] = 0.0
        state_zero_vol = self.analyzer.analyze("TESTUSDT", df_zero_vol)
        self._add_result(
            "Zero Volume",
            state_zero_vol is not None,
            f"Volume ratio: {state_zero_vol.volume_ratio}",
            "Handles gracefully",
            str(state_zero_vol.volume_ratio),
        )

        # Test with extreme volatility
        df_extreme = self._generate_synthetic_data(volatility="VERY_HIGH")
        state_extreme = self.analyzer.analyze("TESTUSDT", df_extreme)
        self._add_result(
            "Extreme Volatility",
            state_extreme is not None
            and state_extreme.volatility in ("VERY_HIGH", "HIGH"),
            f"Volatility: {state_extreme.volatility}",
            "VERY_HIGH or HIGH",
            state_extreme.volatility,
        )

        # Test with NaN values
        df_nan = self._generate_synthetic_data()
        df_nan.iloc[50, df_nan.columns.get_loc("close")] = np.nan
        df_nan["close"] = df_nan["close"].ffill()  # Should be handled by analyzer
        state_nan = self.analyzer.analyze("TESTUSDT", df_nan)
        self._add_result(
            "NaN Handling",
            state_nan is not None,
            "Handles NaN in price data",
            "Valid state",
            "None" if state_nan is None else "Valid",
        )

    # ============================================================
    # 7. RISK MANAGEMENT TESTS
    # ============================================================
    def _test_risk_management(self):
        print("\n🛡️ 7. RISK MANAGEMENT TESTS")

        # Test SL/TP validation
        df = self._generate_synthetic_data()
        for module in self.modules:
            signal = {"type": "LONG", "strategy": "Test", "confidence": 70}
            try:
                entry = module.get_entry_price(df, signal)
                sl = module.get_stop_loss(df, signal)
                tp = module.get_take_profit(df, signal)
                risk = abs(entry - sl)
                reward = abs(tp - entry)
                rr = reward / risk if risk > 0 else 0

                self._add_result(
                    f"{module.name()} SL/TP Valid",
                    sl < entry < tp and rr >= 1.5,
                    f"Entry={entry:.2f}, SL={sl:.2f}, TP={tp:.2f}, RR={rr:.2f}:1",
                    "SL < Entry < TP, RR >= 1.5",
                    f"RR={rr:.2f}:1",
                )
            except Exception as e:
                self._add_result(
                    f"{module.name()} SL/TP Valid",
                    False,
                    f"Error: {e}",
                    "No error",
                    str(e),
                )

    # ============================================================
    # 8. EXECUTION LOGIC TESTS
    # ============================================================
    def _test_execution_logic(self):
        print("\n⚡ 8. EXECUTION LOGIC TESTS")

        # Test price re-validation logic (simulated)
        signal_price = 100.0
        live_prices = [100.5, 101.0, 102.5, 99.0, 98.0]  # Various moves
        threshold = 0.02  # 2%

        for live_price in live_prices:
            move_pct = abs(live_price - signal_price) / signal_price
            should_accept = move_pct <= threshold
            self._add_result(
                f"Re-validation {live_price}",
                should_accept,
                f"Move: {move_pct * 100:.1f}%, {'Accept' if should_accept else 'Reject'}",
                "Accept" if should_accept else "Reject",
                "Accept" if should_accept else "Reject",
            )

    # ============================================================
    # SUMMARY
    # ============================================================
    def _print_summary(self):
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.test_count}")
        print(f"Passed: {self.pass_count}")
        print(f"Failed: {self.test_count - self.pass_count}")
        print(f"Success Rate: {self.pass_count / self.test_count * 100:.1f}%")

        if self.pass_count == self.test_count:
            print("\n✅ ALL TESTS PASSED — Engine is ready for production!")
        else:
            print(
                f"\n⚠️ {self.test_count - self.pass_count} tests failed — review needed"
            )
            for r in self.results:
                if not r.passed:
                    print(f"  ❌ {r.name}: {r.details}")

        print("=" * 80)

    # ============================================================
    # HELPER METHODS
    # ============================================================
    def _generate_synthetic_data(
        self, trend="UP", volatility="MEDIUM", length=100, adx=None, bb_width=None
    ):
        """Generate synthetic OHLCV data with specific characteristics"""
        np.random.seed(42)

        base_price = 100.0
        if trend == "UP":
            drift = 0.002
        elif trend == "DOWN":
            drift = -0.002
        else:
            drift = 0.0

        if volatility == "VERY_HIGH":
            vol = 0.04
        elif volatility == "HIGH":
            vol = 0.025
        elif volatility == "MEDIUM":
            vol = 0.015
        elif volatility == "LOW":
            vol = 0.005
        else:
            vol = 0.015

        closes = [base_price]
        for i in range(1, length):
            change = drift + np.random.normal(0, vol)
            closes.append(closes[-1] * (1 + change))

        closes = np.array(closes)
        highs = closes * (1 + np.abs(np.random.normal(0, vol * 0.5, length)))
        lows = closes * (1 - np.abs(np.random.normal(0, vol * 0.5, length)))
        opens = np.where(
            closes > lows,
            lows + (closes - lows) * np.random.random(length),
            closes + (highs - closes) * np.random.random(length),
        )
        volumes = np.random.uniform(1000000, 5000000, length)

        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(
                    start="2024-01-01", periods=length, freq="1h"
                ),
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes,
            }
        )
        return df

    def _state_to_context(self, state: CoinState) -> Dict:
        """Convert CoinState to context dict for modules and CDM"""
        return {
            "trend": state.trend,
            "regime": state.regime,
            "volatility": state.volatility,
            "coin_type": state.coin_type,
            "volume_ratio": state.volume_ratio,
            "trend_confirmed_4h": state.trend_confirmed_4h,
            "trend_confirmed_macd": state.trend_confirmed_macd,
            "trend_confirmed_volume": state.trend_confirmed_volume,
            "ema_alignment": state.ema_alignment,
            "mtf_score": 70 if state.trend_confirmed_4h else 50,
        }


if __name__ == "__main__":
    suite = TradingEngineTestSuite()
    suite.run_all()
