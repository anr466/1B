#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Strategy Optimizer — تحسين معاملات V8 للوصول لأفضل WR
======================================================
يختبر تركيبات متعددة من المعاملات ويختار الأفضل استقراراً.
"""

import sys
import os
import json
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from binance.client import Client
import pandas as pd
import numpy as np

from backend.strategies.scalping_v8_engine import ScalpingV8Engine, V8_CONFIG

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT"]
TIMEFRAME = "1h"
INITIAL_BALANCE = 1000.0
COMMISSION = 0.001


def fetch_data(client, symbol, start_str, end_str):
    klines = client.get_historical_klines(
        symbol, TIMEFRAME, start_str, end_str, limit=1000
    )
    if not klines:
        return None
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
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ],
    )
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df[["open", "high", "low", "close", "volume"]]


def run_single_backtest(engine, df, config):
    balance = INITIAL_BALANCE
    trades = []
    open_pos = None

    sl_pct = config.get("sl_pct", 0.015)
    tp_pct = config.get("tp_pct", 0.025)
    trail_act = config.get("trailing_activation", 0.003)
    trail_dist = config.get("trailing_distance", 0.002)
    min_conf = config.get("min_confidence", 55)
    max_pos = config.get("max_positions", 3)
    max_hold = config.get("max_hold_hours", 12)

    for i in range(100, len(df) - 1):
        window = df.iloc[: i + 1].copy()
        current_price = window["close"].iloc[-1]

        # Exit check
        if open_pos:
            hold_hours = (
                window.index[-1] - open_pos["entry_time"]
            ).total_seconds() / 3600
            pnl_pct = (current_price - open_pos["entry_price"]) / open_pos[
                "entry_price"
            ]

            # Peak tracking
            if current_price > open_pos.get("peak", open_pos["entry_price"]):
                open_pos["peak"] = current_price
                open_pos["trail"] = open_pos["peak"] * (1 - trail_dist)

            should_exit = False
            exit_reason = ""

            # Stop loss
            if current_price <= open_pos["sl"]:
                should_exit = True
                exit_reason = "SL"
            # Take profit
            elif pnl_pct >= tp_pct:
                should_exit = True
                exit_reason = "TP"
            # Trailing stop
            elif open_pos.get("trail", 0) > 0 and current_price <= open_pos["trail"]:
                should_exit = True
                exit_reason = "TRAIL"
            # Max hold
            elif hold_hours >= max_hold:
                should_exit = True
                exit_reason = "MAX_HOLD"

            if should_exit:
                exit_price = current_price
                gross_pnl = (exit_price - open_pos["entry_price"]) / open_pos[
                    "entry_price"
                ]
                net_pnl = gross_pnl - COMMISSION * 2
                balance *= 1 + net_pnl * open_pos["size_pct"]

                trades.append(
                    {
                        "entry_price": open_pos["entry_price"],
                        "exit_price": exit_price,
                        "pnl_pct": net_pnl * 100,
                        "hold_hours": hold_hours,
                        "exit_reason": exit_reason,
                        "entry_conf": open_pos.get("confidence", 0),
                    }
                )
                open_pos = None

        # Entry check
        if not open_pos:
            trend = engine.get_4h_trend(window)
            if trend == "DOWN":
                continue

            signal = engine.detect_entry(window, trend)
            if signal and signal.get("confidence", 0) >= min_conf:
                entry_price = signal.get("entry_price", current_price)
                sl = entry_price * (1 - sl_pct)

                open_pos = {
                    "entry_price": entry_price,
                    "entry_time": window.index[-1],
                    "sl": sl,
                    "peak": entry_price,
                    "trail": 0,
                    "size_pct": config.get("position_size_pct", 0.07),
                    "confidence": signal.get("confidence", 50),
                }

    # Close any open position at end
    if open_pos:
        exit_price = df.iloc[-1]["close"]
        gross_pnl = (exit_price - open_pos["entry_price"]) / open_pos["entry_price"]
        net_pnl = gross_pnl - COMMISSION * 2
        balance *= 1 + net_pnl * open_pos["size_pct"]
        trades.append(
            {
                "entry_price": open_pos["entry_price"],
                "exit_price": exit_price,
                "pnl_pct": net_pnl * 100,
                "hold_hours": 0,
                "exit_reason": "END",
                "entry_conf": open_pos.get("confidence", 0),
            }
        )

    wins = sum(1 for t in trades if t["pnl_pct"] > 0)
    losses = sum(1 for t in trades if t["pnl_pct"] <= 0)
    total_pnl = balance - INITIAL_BALANCE
    wr = wins / len(trades) * 100 if trades else 0

    avg_win = (
        sum(t["pnl_pct"] for t in trades if t["pnl_pct"] > 0) / wins if wins else 0
    )
    avg_loss = (
        sum(t["pnl_pct"] for t in trades if t["pnl_pct"] <= 0) / losses if losses else 0
    )
    pf = (
        abs(avg_win * wins / (avg_loss * losses))
        if losses and avg_loss
        else float("inf")
    )

    return {
        "balance": balance,
        "total_return": total_pnl / INITIAL_BALANCE * 100,
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": wr,
        "profit_factor": pf,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "total_pnl": total_pnl,
    }


def optimize():
    print("=" * 70)
    print("🧪 STRATEGY OPTIMIZER — Finding Best V8 Parameters")
    print("=" * 70)

    client = Client("", "")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    start_str = start_date.strftime("%d %b %Y")
    end_str = end_date.strftime("%d %b %Y")

    print(f"\n📅 Period: {start_str} → {end_str}")
    print(f"📊 Symbols: {len(SYMBOLS)}")

    # Fetch data
    data = {}
    for sym in SYMBOLS:
        df = fetch_data(client, sym, start_str, end_str)
        if df is not None and len(df) >= 100:
            data[sym] = df
            print(f"  ✅ {sym}: {len(df)} candles")

    # Parameter grid
    param_grid = {
        "sl_pct": [0.010, 0.015, 0.020, 0.025],
        "tp_pct": [0.015, 0.020, 0.025, 0.030, 0.040],
        "trailing_activation": [0.002, 0.003, 0.004, 0.005],
        "trailing_distance": [0.0015, 0.002, 0.0025, 0.003],
        "min_confidence": [50, 55, 60, 65, 70],
        "position_size_pct": [0.05, 0.07, 0.10],
    }

    # Smart sampling: test most promising combos first
    configs = []
    for sl in param_grid["sl_pct"]:
        for tp in param_grid["tp_pct"]:
            for ta in param_grid["trailing_activation"]:
                for td in param_grid["trailing_distance"]:
                    for mc in param_grid["min_confidence"]:
                        for ps in param_grid["position_size_pct"]:
                            # Filter: trailing_activation must be >= trailing_distance
                            if ta < td:
                                continue
                            # Filter: TP must be > SL
                            if tp <= sl:
                                continue
                            # Filter: confidence must be reasonable
                            if mc < 50 or mc > 70:
                                continue

                            configs.append(
                                {
                                    "sl_pct": sl,
                                    "tp_pct": tp,
                                    "trailing_activation": ta,
                                    "trailing_distance": td,
                                    "min_confidence": mc,
                                    "position_size_pct": ps,
                                    "max_positions": 3,
                                    "max_hold_hours": 12,
                                }
                            )

    print(f"\n🔍 Testing {len(configs)} parameter combinations...\n")

    results = []
    best_wr = 0
    best_config = None
    tested = 0

    for i, config in enumerate(configs):
        tested += 1
        total_wr = 0
        total_trades = 0
        total_pnl = 0
        symbol_count = 0

        engine = ScalpingV8Engine(config)

        for sym, df in data.items():
            try:
                r = run_single_backtest(engine, df, config)
                if r["trades"] >= 5:  # Need minimum trades for statistical significance
                    total_wr += r["win_rate"]
                    total_trades += r["trades"]
                    total_pnl += r["total_pnl"]
                    symbol_count += 1
            except Exception:
                continue

        if symbol_count >= 3:  # At least 3 symbols with valid results
            avg_wr = total_wr / symbol_count
            avg_pnl = total_pnl / symbol_count

            result = {
                "config": config,
                "avg_win_rate": avg_wr,
                "total_trades": total_trades,
                "avg_pnl": avg_pnl,
                "symbols_tested": symbol_count,
            }
            results.append(result)

            if avg_wr > best_wr:
                best_wr = avg_wr
                best_config = config
                print(
                    f"  🏆 New best: WR={avg_wr:.1f}% | SL={sl * 100:.1f}% | TP={tp * 100:.1f}% | "
                    f"TA={ta * 100:.2f}% | TD={td * 100:.2f}% | MC={mc} | PS={ps * 100:.0f}% | "
                    f"Trades={total_trades} | PnL=${avg_pnl:.2f}"
                )

        if tested % 50 == 0:
            print(f"  ... tested {tested}/{len(configs)}")

    # Sort by win rate
    results.sort(key=lambda x: x["avg_win_rate"], reverse=True)

    print(f"\n{'=' * 70}")
    print(f"📊 TOP 10 CONFIGURATIONS")
    print(f"{'=' * 70}")

    for i, r in enumerate(results[:10]):
        c = r["config"]
        print(
            f"\n#{i + 1}: WR={r['avg_win_rate']:.1f}% | Trades={r['total_trades']} | PnL=${r['avg_pnl']:.2f}"
        )
        print(
            f"    SL={c['sl_pct'] * 100:.1f}% | TP={c['tp_pct'] * 100:.1f}% | "
            f"TA={c['trailing_activation'] * 100:.2f}% | TD={c['trailing_distance'] * 100:.2f}% | "
            f"MinConf={c['min_confidence']} | PosSize={c['position_size_pct'] * 100:.0f}%"
        )

    # Save best config
    if best_config:
        output = {
            "best_config": best_config,
            "best_win_rate": best_wr,
            "top_10": results[:10],
            "total_tested": tested,
            "period": f"{start_str} → {end_str}",
        }
        output_file = os.path.join(
            os.path.dirname(__file__),
            "backtest_results",
            f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\n💾 Best config saved to: {output_file}")

    return best_config, best_wr


if __name__ == "__main__":
    optimize()
