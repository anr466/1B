#!/usr/bin/env python3
"""
Comprehensive Scenario Test for Cognitive Trading System.
Verifies that all market scenarios are handled intelligently without conflicts.
"""

import sys
import os

sys.path.insert(0, "/root/trading_ai_bot-1")

import pandas as pd
import numpy as np
from backend.core.modules.trend_module import TrendModule
from backend.core.modules.range_module import RangeModule
from backend.core.modules.volatility_module import VolatilityModule
from backend.core.cognitive_decision_matrix import CognitiveDecisionMatrix

# --- Mock Data Generators ---


def make_trend_data(direction="UP", strength="STRONG"):
    """Generates mock OHLCV data for a trend."""
    base = 100.0
    data = []
    for i in range(60):
        if direction == "UP":
            change = 0.5 if strength == "STRONG" else 0.1
            noise = np.random.normal(0, 0.2)
        else:
            change = -0.5 if strength == "STRONG" else -0.1
            noise = np.random.normal(0, 0.2)

        close = base + (change * i) + noise
        high = close + abs(np.random.normal(0, 0.5))
        low = close - abs(np.random.normal(0, 0.5))
        vol = 100 + (50 if strength == "STRONG" else 0)
        data.append({"close": close, "high": high, "low": low, "volume": vol})
    df = pd.DataFrame(data)
    df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()
    df["ema55"] = df["close"].ewm(span=55, adjust=False).mean()
    return df


def make_range_data(width="WIDE"):
    """Generates mock OHLCV data for a ranging market."""
    center = 100.0
    amplitude = 5.0 if width == "WIDE" else 1.0
    data = []
    for i in range(60):
        angle = (i / 60) * 2 * np.pi * 3  # 3 cycles
        close = center + amplitude * np.sin(angle) + np.random.normal(0, 0.1)
        high = close + 0.2
        low = close - 0.2
        vol = 100
        data.append({"close": close, "high": high, "low": low, "volume": vol})
    df = pd.DataFrame(data)
    df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()
    df["ema55"] = df["close"].ewm(span=55, adjust=False).mean()
    return df


def make_breakout_data():
    """Generates mock data ending with a high-volume breakout."""
    df = make_range_data("WIDE")
    # Last candle breakout
    df.loc[df.index[-1], "close"] = 106.0  # Above resistance ~105
    df.loc[df.index[-1], "high"] = 107.0
    df.loc[df.index[-1], "volume"] = 300.0  # High volume
    return df


# --- Test Runner ---


class ScenarioTest:
    def __init__(self):
        self.trend_mod = TrendModule()
        self.range_mod = RangeModule()
        self.vol_mod = VolatilityModule()
        self.matrix = CognitiveDecisionMatrix()
        self.passed = 0
        self.failed = 0

    def run(self):
        print("=" * 80)
        print("COGNITIVE TRADING SYSTEM - SCENARIO VERIFICATION")
        print("=" * 80)

        self.test_strong_uptrend_pullback()
        self.test_strong_downtrend_pullback()
        self.test_wide_range_support()
        self.test_wide_range_resistance()
        self.test_volatility_breakout()
        self.test_choppy_market()
        self.test_conflict_range_vs_breakout()

        print("=" * 80)
        print(f"RESULTS: {self.passed} PASSED, {self.failed} FAILED")
        print("=" * 80)

    def evaluate_scenario(self, name, df, context, expected_action, expected_type=None):
        print(f"\n🧪 SCENARIO: {name}")
        print(f"   Context: {context}")

        active_modules = []
        signals = []

        # 1. Module Filtering & Evaluation
        for mod in [self.trend_mod, self.range_mod, self.vol_mod]:
            if context["regime"] in mod.supported_regimes():
                active_modules.append(mod.name())
                sig = mod.evaluate(df, context)
                if sig:
                    sig["entry_price"] = mod.get_entry_price(df, sig)
                    sig["stop_loss"] = mod.get_stop_loss(df, sig)
                    sig["take_profit"] = mod.get_take_profit(df, sig)
                    signals.append((mod.name(), sig))

        print(f"   Active Modules: {active_modules}")
        print(f"   Raw Signals: {[s[0] for s in signals]}")

        # 2. Cognitive Decision
        best_signal = None
        best_score = -1
        best_decision = "REJECT"

        for mod_name, sig in signals:
            decision = self.matrix.evaluate(sig, context)
            print(
                f"   -> {mod_name}: Score={decision['score']}, Decision={decision['decision']}"
            )
            if decision["score"] > best_score and decision["decision"] in [
                "ENTER",
                "ENTER_REDUCED",
            ]:
                best_score = decision["score"]
                best_signal = sig
                best_decision = decision["decision"]

        # 3. Assertion
        success = False
        if expected_action == "REJECT":
            if best_decision == "REJECT":
                success = True
        elif expected_action == "ENTER":
            if best_decision in ["ENTER", "ENTER_REDUCED"]:
                if expected_type is None or best_signal["type"] == expected_type:
                    success = True

        if success:
            print(f"   ✅ PASS: Expected {expected_action}, Got {best_decision}")
            self.passed += 1
        else:
            print(
                f"   ❌ FAIL: Expected {expected_action} ({expected_type}), Got {best_decision} ({best_signal['type'] if best_signal else 'None'})"
            )
            self.failed += 1

    # --- Specific Scenarios ---

    def test_strong_uptrend_pullback(self):
        df = make_trend_data("UP", "STRONG")
        context = {
            "trend": "UP",
            "regime": "STRONG_TREND",
            "volatility": "MEDIUM",
            "coin_type": "MAJOR",
        }
        self.evaluate_scenario("Strong Uptrend Pullback", df, context, "ENTER", "LONG")

    def test_strong_downtrend_pullback(self):
        df = make_trend_data("DOWN", "STRONG")
        context = {
            "trend": "DOWN",
            "regime": "STRONG_TREND",
            "volatility": "MEDIUM",
            "coin_type": "MAJOR",
        }
        self.evaluate_scenario(
            "Strong Downtrend Pullback", df, context, "ENTER", "SHORT"
        )

    def test_wide_range_support(self):
        df = make_range_data("WIDE")
        # Force price to support
        df.loc[df.index[-1], "close"] = 95.1
        context = {
            "trend": "NEUTRAL",
            "regime": "WIDE_RANGE",
            "volatility": "LOW",
            "coin_type": "MAJOR",
        }
        self.evaluate_scenario("Wide Range at Support", df, context, "ENTER", "LONG")

    def test_wide_range_resistance(self):
        df = make_range_data("WIDE")
        # Force price to resistance
        df.loc[df.index[-1], "close"] = 104.9
        context = {
            "trend": "NEUTRAL",
            "regime": "WIDE_RANGE",
            "volatility": "LOW",
            "coin_type": "MAJOR",
        }
        self.evaluate_scenario(
            "Wide Range at Resistance", df, context, "ENTER", "SHORT"
        )

    def test_volatility_breakout(self):
        df = make_breakout_data()
        context = {
            "trend": "NEUTRAL",
            "regime": "WIDE_RANGE",
            "volatility": "HIGH",
            "coin_type": "MEME",
        }
        self.evaluate_scenario("Volatility Breakout", df, context, "ENTER", "LONG")

    def test_choppy_market(self):
        df = make_range_data("NARROW")
        context = {
            "trend": "NEUTRAL",
            "regime": "CHOPPY",
            "volatility": "LOW",
            "coin_type": "MAJOR",
        }
        self.evaluate_scenario("Choppy Market", df, context, "REJECT")

    def test_conflict_range_vs_breakout(self):
        """Scenario: Price at resistance (Range says Sell), but Volume Breakout (Vol says Buy)."""
        df = make_breakout_data()
        # Regime is Wide Range, so BOTH Range and Vol modules are active.
        context = {
            "trend": "NEUTRAL",
            "regime": "WIDE_RANGE",
            "volatility": "HIGH",
            "coin_type": "MEME",
        }
        # Volatility Breakout should win due to higher score/volume confirmation.
        self.evaluate_scenario(
            "Conflict: Range Resistance vs Vol Breakout", df, context, "ENTER", "LONG"
        )


if __name__ == "__main__":
    test = ScenarioTest()
    test.run()
