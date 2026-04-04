#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Iterative Fix Tester — اصلاح واختبار كل نقطة ضعف
====================================================
يختبر كل تعديل على حدة ثم مجتمعة حتى نصل لنتيجة رابحة.
"""

import sys, json, os
from datetime import datetime, timedelta

sys.path.insert(0, "/app")

from binance.client import Client
import pandas as pd

from backend.strategies.scalping_v8_engine import ScalpingV8Engine, V8_CONFIG

SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "AVAXUSDT",
    "NEARUSDT",
    "SUIUSDT",
    "ARBUSDT",
    "APTUSDT",
    "INJUSDT",
    "LINKUSDT",
    "PEPEUSDT",
    "OPUSDT",
]
TIMEFRAME = "1h"
INITIAL_BALANCE = 1000.0
COMMISSION = 0.001
SLIPPAGE = 0.0005


def fetch_data(client, symbol, start_str, end_str):
    klines = client.get_historical_klines(
        symbol, TIMEFRAME, start_str, end_str, limit=1500
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


def backtest_with_config(engine, df, config):
    balance = INITIAL_BALANCE
    trades = []
    open_pos = None

    sl_pct = config.get("sl_pct", 0.010)
    trail_act = config.get("trailing_activation", 0.002)
    trail_dist = config.get("trailing_distance", 0.0015)
    max_hold = config.get("max_hold_hours", 6)
    stagnant_h = config.get("stagnant_hours", 2)
    stagnant_thresh = config.get("stagnant_threshold", 0.0005)
    progressive = config.get("v8_progressive_trail", {})
    min_vol_ratio = config.get("min_volume_ratio", 1.0)
    min_rsi = config.get("min_rsi", 0)

    for i in range(100, len(df) - 1):
        window = df.iloc[: i + 1].copy()
        current_price = window["close"].iloc[-1]

        if open_pos:
            hold_hours = (
                window.index[-1] - open_pos["entry_time"]
            ).total_seconds() / 3600
            pnl_pct = (current_price - open_pos["entry_price"]) / open_pos[
                "entry_price"
            ]

            if current_price > open_pos.get("peak", open_pos["entry_price"]):
                open_pos["peak"] = current_price
                td = trail_dist
                for pl, dist in sorted(progressive.items()):
                    if pnl_pct >= pl:
                        td = dist
                open_pos["trail"] = open_pos["peak"] * (1 - td)

            should_exit = False
            exit_reason = ""

            if current_price <= open_pos["sl"]:
                should_exit, exit_reason = True, "STOP_LOSS"
            elif (
                open_pos.get("trail", 0) > 0
                and current_price <= open_pos["trail"]
                and pnl_pct >= trail_act
            ):
                should_exit, exit_reason = True, "TRAILING"
            elif hold_hours >= max_hold:
                should_exit, exit_reason = True, "MAX_HOLD"
            elif hold_hours >= stagnant_h and abs(pnl_pct) < stagnant_thresh:
                should_exit, exit_reason = True, "STAGNANT"

            if should_exit:
                net_pnl = pnl_pct - COMMISSION - SLIPPAGE
                pnl_amount = open_pos["size"] * net_pnl
                balance += open_pos["size"] + pnl_amount

                trades.append(
                    {
                        "entry_price": open_pos["entry_price"],
                        "exit_price": current_price,
                        "pnl_pct": net_pnl * 100,
                        "pnl": pnl_amount,
                        "hold_hours": hold_hours,
                        "exit_reason": exit_reason,
                        "strategy": open_pos.get("strategy", "unknown"),
                    }
                )
                open_pos = None

        if not open_pos:
            trend = engine.get_4h_trend(window)
            if trend == "DOWN":
                continue
            signal = engine.detect_entry(window, trend)
            if signal:
                entry_price = signal.get("entry_price", current_price)
                sl = entry_price * (1 - sl_pct)
                size = balance * config.get("position_size_pct", 0.06)

                if min_vol_ratio > 1.0:
                    vol_ma = window["volume"].rolling(20).mean()
                    if len(vol_ma) > 0 and vol_ma.iloc[-1] > 0:
                        vol_ratio = window["volume"].iloc[-1] / vol_ma.iloc[-1]
                        if vol_ratio < min_vol_ratio:
                            continue

                if min_rsi > 0:
                    delta = window["close"].diff()
                    gain = delta.where(delta > 0, 0).ewm(span=14).mean()
                    loss = -delta.where(delta < 0, 0).ewm(span=14).mean()
                    rs = gain / loss
                    rsi = 100 - (100 / (1 + rs))
                    if len(rsi) > 0 and rsi.iloc[-1] < min_rsi:
                        continue

                open_pos = {
                    "entry_price": entry_price,
                    "entry_time": window.index[-1],
                    "sl": sl,
                    "peak": entry_price,
                    "trail": 0,
                    "size": size,
                    "strategy": signal.get("strategy", "unknown"),
                }

    if open_pos:
        exit_price = df.iloc[-1]["close"]
        pnl_pct = (exit_price - open_pos["entry_price"]) / open_pos["entry_price"]
        net_pnl = pnl_pct - COMMISSION - SLIPPAGE
        pnl_amount = open_pos["size"] * net_pnl
        balance += open_pos["size"] + pnl_amount
        trades.append(
            {
                "entry_price": open_pos["entry_price"],
                "exit_price": exit_price,
                "pnl_pct": net_pnl * 100,
                "pnl": pnl_amount,
                "hold_hours": 0,
                "exit_reason": "END",
                "strategy": open_pos.get("strategy", "unknown"),
            }
        )

    return trades


def run_tests():
    sep = "=" * 70
    print(sep)
    print("ITERATIVE FIX TESTER — اصلاح كل نقطة ضعف")
    print(sep)

    client = Client("", "")
    end_date = datetime(2026, 4, 4)
    start_date = end_date - timedelta(days=60)
    start_str = start_date.strftime("%d %b %Y")
    end_str = end_date.strftime("%d %b %Y")

    print("Period: " + start_str + " to " + end_str + " (60 days)")
    print()

    data = {}
    for sym in SYMBOLS:
        df = fetch_data(client, sym, start_str, end_str)
        if df is not None and len(df) >= 100:
            data[sym] = df

    tests = {
        "BASELINE (original)": V8_CONFIG.copy(),
        "FIX 1: SL 2.5% (was 1.0%)": {
            **V8_CONFIG,
            "sl_pct": 0.025,
        },
        "FIX 2: SL 2.5% + Stagnant 6h/0.1%": {
            **V8_CONFIG,
            "sl_pct": 0.025,
            "stagnant_hours": 6,
            "stagnant_threshold": 0.001,
        },
        "FIX 3: SL 2.5% + Stagnant + Vol 2x": {
            **V8_CONFIG,
            "sl_pct": 0.025,
            "stagnant_hours": 6,
            "stagnant_threshold": 0.001,
            "min_volume_ratio": 2.0,
        },
        "FIX 4: SL 2.5% + Stagnant + Vol 2x + RSI>50": {
            **V8_CONFIG,
            "sl_pct": 0.025,
            "stagnant_hours": 6,
            "stagnant_threshold": 0.001,
            "min_volume_ratio": 2.0,
            "min_rsi": 50,
        },
        "FIX 5: SL 3.0% + Stagnant 8h + Vol 1.5x + RSI>45": {
            **V8_CONFIG,
            "sl_pct": 0.030,
            "stagnant_hours": 8,
            "stagnant_threshold": 0.001,
            "min_volume_ratio": 1.5,
            "min_rsi": 45,
            "trailing_activation": 0.005,
            "trailing_distance": 0.003,
        },
        "FIX 6: SL 2.0% + Trailing 0.5%/0.3% + MaxHold 12h": {
            **V8_CONFIG,
            "sl_pct": 0.020,
            "trailing_activation": 0.005,
            "trailing_distance": 0.003,
            "max_hold_hours": 12,
            "stagnant_hours": 6,
            "stagnant_threshold": 0.001,
        },
    }

    all_results = {}

    for test_name, config in tests.items():
        print()
        print("=" * 50)
        print("TEST: " + test_name)
        print("=" * 50)

        all_trades = []
        engine = ScalpingV8Engine(config)

        for sym, df in data.items():
            trades = backtest_with_config(engine, df, config)
            all_trades.extend(trades)

        total_trades = len(all_trades)
        wins = sum(1 for t in all_trades if t["pnl"] > 0)
        losses = sum(1 for t in all_trades if t["pnl"] <= 0)
        total_pnl = sum(t["pnl"] for t in all_trades)
        final_balance = INITIAL_BALANCE + total_pnl
        wr = wins / total_trades * 100 if total_trades else 0
        avg_win = (
            sum(t["pnl"] for t in all_trades if t["pnl"] > 0) / wins if wins else 0
        )
        avg_loss = (
            sum(t["pnl"] for t in all_trades if t["pnl"] <= 0) / losses if losses else 0
        )
        pf = (
            abs(avg_win * wins / (avg_loss * losses))
            if losses and avg_loss != 0
            else float("inf")
        )

        print("Trades:        " + str(total_trades))
        print("Wins:          " + str(wins))
        print("Losses:        " + str(losses))
        print("Win Rate:      " + str(round(wr, 1)) + "%")
        print("Profit Factor: " + str(round(pf, 2)))
        print("Total PnL:     $" + str(round(total_pnl, 2)))
        print("Final Balance: $" + str(round(final_balance, 2)))
        print(
            "Return:        "
            + str(round((final_balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100, 2))
            + "%"
        )

        exits = {}
        for t in all_trades:
            r = t["exit_reason"]
            if r not in exits:
                exits[r] = {"count": 0, "pnl": 0, "wins": 0}
            exits[r]["count"] += 1
            exits[r]["pnl"] += t["pnl"]
            if t["pnl"] > 0:
                exits[r]["wins"] += 1

        if exits:
            print()
            print("Exit Reasons:")
            for reason, stats in sorted(
                exits.items(), key=lambda x: x[1]["pnl"], reverse=True
            ):
                ewr = stats["wins"] / stats["count"] * 100 if stats["count"] else 0
                print(
                    "  "
                    + reason.ljust(15)
                    + ": "
                    + str(stats["count"]).rjust(4)
                    + " | WR="
                    + str(round(ewr, 1)).rjust(5)
                    + "% | PnL=$"
                    + str(round(stats["pnl"], 2)).rjust(8)
                )

        all_results[test_name] = {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wr, 1),
            "profit_factor": round(pf, 2),
            "total_pnl": round(total_pnl, 2),
            "final_balance": round(final_balance, 2),
            "return_pct": round(
                (final_balance - INITIAL_BALANCE) / INITIAL_BALANCE * 100, 2
            ),
        }

    print()
    print(sep)
    print("COMPARISON — ALL FIXES")
    print(sep)
    header = (
        "Test".ljust(40)
        + " | "
        + "Trades".rjust(6)
        + " | "
        + "WR".rjust(5)
        + " | "
        + "PF".rjust(5)
        + " | "
        + "PnL".rjust(8)
        + " | "
        + "Return".rjust(7)
    )
    print(header)
    print("-" * 85)
    for name, r in all_results.items():
        line = (
            name.ljust(40)
            + " | "
            + str(r["total_trades"]).rjust(6)
            + " | "
            + str(r["win_rate"]).rjust(4)
            + "% | "
            + str(r["profit_factor"]).rjust(5)
            + " | $"
            + str(r["total_pnl"]).rjust(7)
            + " | "
            + str(r["return_pct"]).rjust(6)
            + "%"
        )
        print(line)

    best = max(all_results.items(), key=lambda x: x[1]["total_pnl"])
    print()
    print("BEST FIX: " + best[0])
    print("  PnL: $" + str(best[1]["total_pnl"]))
    print("  WR: " + str(best[1]["win_rate"]) + "%")
    print("  PF: " + str(best[1]["profit_factor"]))

    output_file = (
        "/app/tests/backtest_results/iterative_fixes_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".json"
    )
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print()
    print("Saved to: " + output_file)


if __name__ == "__main__":
    run_tests()
