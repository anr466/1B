#!/usr/bin/env python3

import sys
import os
import pandas as pd
import logging
from binance.client import Client

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("EngineTest")

from backend.core.coin_state_analyzer import CoinStateAnalyzer
from backend.core.cognitive_decision_matrix import CognitiveDecisionMatrix
from backend.core.modules.trend_module import TrendModule
from backend.core.modules.range_module import RangeModule
from backend.core.modules.volatility_module import VolatilityModule
from backend.core.modules.scalping_module import ScalpingModule


def fetch_data(symbol, timeframe="1h", limit=200):
    client = Client(None, None)
    klines = client.get_klines(symbol=symbol, interval=timeframe, limit=limit)
    df = pd.DataFrame(
        klines,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
            "ignore",
        ],
    )
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df


def run_test():
    logger.info("🚀 Starting Trading Engine Logic Test...")

    analyzer = CoinStateAnalyzer()
    decision_matrix = CognitiveDecisionMatrix()
    modules = [TrendModule(), RangeModule(), VolatilityModule(), ScalpingModule()]

    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "ENJUSDT"]
    total_signals = 0

    for symbol in symbols:
        logger.info(f"\n📊 Testing {symbol} (Last 100 Candles)...")
        df = fetch_data(symbol, timeframe="1h", limit=100)

        if df is None or len(df) < 60:
            logger.warning(f"❌ Not enough data for {symbol}")
            continue

        current_data = df.iloc[:-1]

        try:
            state = analyzer.analyze(symbol, current_data)
            if not state:
                logger.info(f"   ⏭️ State analysis returned None")
                continue

            logger.info(
                f"   🧠 State: Trend={state.trend}, Regime={state.regime}, Rec={state.recommendation}"
            )

            if state.recommendation == "AVOID":
                logger.info(f"   🛡️ Recommendation is AVOID - Skipping modules")
                continue

            context = {
                "trend": state.trend,
                "regime": state.regime,
                "volatility": state.volatility,
                "coin_type": state.coin_type,
                "volume_ratio": 1.0,
            }

            best_signal = None
            best_score = -1

            for module in modules:
                if state.regime in module.supported_regimes():
                    signal = module.evaluate(current_data, context)
                    if signal:
                        logger.info(
                            f"   📈 Signal Found: {module.name()} -> {signal['strategy']}"
                        )

                        signal["entry_price"] = module.get_entry_price(
                            current_data, signal
                        )
                        signal["stop_loss"] = module.get_stop_loss(current_data, signal)
                        signal["take_profit"] = module.get_take_profit(
                            current_data, signal
                        )

                        decision = decision_matrix.evaluate(signal, context)
                        logger.info(
                            f"   📊 Score: {decision['score']}, Decision: {decision['decision']}"
                        )

                        if decision["decision"] in ["ENTER", "ENTER_REDUCED"]:
                            if decision["score"] > best_score:
                                best_score = decision["score"]
                                best_signal = {**signal, **decision}

            if best_signal:
                total_signals += 1
                logger.info(
                    f"   ✅ VALID SIGNAL: {symbol} | {best_signal['strategy']} | Score: {best_score}"
                )
                logger.info(
                    f"      Entry: {best_signal['entry_price']}, SL: {best_signal['stop_loss']}, TP: {best_signal['take_profit']}"
                )
            else:
                logger.info(f"   ❌ No valid signals passed the threshold.")

        except Exception as e:
            logger.error(f"   ❌ Error testing {symbol}: {e}")

    logger.info(f"\n🏁 Test Complete. Total Valid Signals Generated: {total_signals}")


if __name__ == "__main__":
    run_test()
