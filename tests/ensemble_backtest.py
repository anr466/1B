#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Ensemble Backtest — اختبار الاستراتيجيات الخمس على بيانات شهر سابق
===================================================================
يختبر StrategyEnsemble (5 استراتيجيات LONG فقط) على بيانات Binance الحقيقية.
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

from backend.strategies.scalping_v8_strategy import get_scalping_v8_strategy
from backend.strategies.momentum_breakout import MomentumBreakoutStrategy
from backend.strategies.trend_following import TrendFollowingStrategy
from backend.strategies.rsi_divergence import RSIDivergenceStrategy
from backend.strategies.volume_price_trend import VolumePriceTrendStrategy
from backend.strategies.strategy_ensemble import StrategyEnsemble

# Test symbols (same as production)
SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "DOGEUSDT",
    "AVAXUSDT",
    "DOTUSDT",
    "LINKUSDT",
    "MATICUSDT",
    "LTCUSDT",
    "BCHUSDT",
    "ETCUSDT",
    "FILUSDT",
    "APTUSDT",
    "ARBUSDT",
    "OPUSDT",
    "SUIUSDT",
    "INJUSDT",
    "NEARUSDT",
    "PEPEUSDT",
    "WIFUSDT",
    "FETUSDT",
    "RENDERUSDT",
]

# Timeframe
TIMEFRAME = "1h"

# Backtest settings
INITIAL_BALANCE = 1000.0
POSITION_SIZE_PCT = 0.07  # 7% per trade
COMMISSION = 0.001  # 0.1% per side
SL_PCT = 0.008  # 0.8% stop loss
MAX_POSITIONS = 5


def fetch_historical_data(client, symbol, timeframe, start_str, end_str):
    """Fetch historical klines from Binance"""
    klines = client.get_historical_klines(
        symbol, timeframe, start_str, end_str, limit=1000
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


def run_backtest():
    """Run ensemble backtest on historical data"""
    print("=" * 70)
    print("🧪 ENSEMBLE BACKTEST — 5 Strategies, LONG Only (Spot)")
    print("=" * 70)

    # Initialize Binance client (public data only)
    client = Client("", "")

    # Date range: last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    start_str = start_date.strftime("%d %b %Y")
    end_str = end_date.strftime("%d %b %Y")

    print(f"\n📅 Period: {start_str} → {end_str}")
    print(f"📊 Timeframe: {TIMEFRAME}")
    print(f"💰 Initial Balance: ${INITIAL_BALANCE:.2f}")
    print(f"📈 Position Size: {POSITION_SIZE_PCT * 100}%")
    print(f"🛡️ Stop Loss: {SL_PCT * 100}%")
    print(f"💸 Commission: {COMMISSION * 100}% per side")
    print(f"🔢 Max Positions: {MAX_POSITIONS}")

    # Initialize ensemble
    v8 = get_scalping_v8_strategy()
    strategies = [
        v8,
        MomentumBreakoutStrategy(),
        TrendFollowingStrategy(),
        RSIDivergenceStrategy(),
        VolumePriceTrendStrategy(),
    ]
    ensemble = StrategyEnsemble(strategies)

    print(f"\n🎯 Strategies: {[s.name for s in strategies]}")
    print(f"📦 Testing {len(SYMBOLS)} symbols...\n")

    # Backtest state
    balance = INITIAL_BALANCE
    trades = []
    open_positions = []
    total_signals = 0
    rejected_signals = 0
    symbol_results = {}

    for symbol in SYMBOLS:
        print(f"  📊 Fetching {symbol}...")
        df = fetch_historical_data(client, symbol, TIMEFRAME, start_str, end_str)
        if df is None or len(df) < 100:
            print(
                f"     ⚠️  Insufficient data ({len(df) if df is not None else 0} candles)"
            )
            continue

        # Prepare data with indicators
        df = ensemble.prepare_data(df)

        symbol_trades = []
        symbol_signals = 0
        symbol_rejected = 0

        # Walk through data
        for i in range(100, len(df) - 1):
            window = df.iloc[: i + 1].copy()
            current_price = df.iloc[i]["close"]

            # Check open positions for exit
            positions_to_close = []
            for pos in open_positions:
                if pos["symbol"] != symbol:
                    continue

                exit_result = ensemble.check_exit(window, pos)
                if exit_result.get("should_exit", False):
                    exit_price = current_price
                    pnl_pct = (exit_price - pos["entry_price"]) / pos["entry_price"]
                    pnl = pos["size"] * pnl_pct
                    commission_cost = pos["size"] * COMMISSION * 2
                    net_pnl = pnl - commission_cost

                    balance += pos["size"] + net_pnl

                    trade = {
                        "symbol": symbol,
                        "entry_price": pos["entry_price"],
                        "exit_price": exit_price,
                        "entry_time": pos["entry_time"],
                        "exit_time": str(df.index[i]),
                        "pnl_pct": pnl_pct * 100,
                        "pnl": net_pnl,
                        "size": pos["size"],
                        "supporting": pos.get("supporting_strategies", []),
                    }
                    trades.append(trade)
                    symbol_trades.append(trade)
                    positions_to_close.append(pos)

            for pos in positions_to_close:
                open_positions.remove(pos)

            # Check for entry signals
            if len(open_positions) >= MAX_POSITIONS:
                continue

            trend = ensemble.get_market_trend(window)
            context = {"trend": trend}
            signal = ensemble.detect_entry(window, context)

            if signal:
                symbol_signals += 1
                total_signals += 1

                # Simulate entry
                entry_price = signal.get("entry_price", current_price)
                position_size = balance * POSITION_SIZE_PCT
                sl = entry_price * (1 - SL_PCT)

                open_positions.append(
                    {
                        "symbol": symbol,
                        "entry_price": entry_price,
                        "entry_time": str(df.index[i]),
                        "size": position_size,
                        "sl": sl,
                        "supporting_strategies": signal.get(
                            "supporting_strategies", []
                        ),
                        "strategy_count": signal.get("strategy_count", 1),
                    }
                )
                balance -= position_size

        # Symbol summary
        wins = sum(1 for t in symbol_trades if t["pnl"] > 0)
        losses = sum(1 for t in symbol_trades if t["pnl"] <= 0)
        total_pnl = sum(t["pnl"] for t in symbol_trades)

        symbol_results[symbol] = {
            "signals": symbol_signals,
            "trades": len(symbol_trades),
            "wins": wins,
            "losses": losses,
            "win_rate": wins / len(symbol_trades) * 100 if symbol_trades else 0,
            "total_pnl": total_pnl,
        }

        print(
            f"     ✅ {symbol}: {symbol_signals} signals, {len(symbol_trades)} trades, "
            f"WR={wins / len(symbol_trades) * 100 if symbol_trades else 0:.0f}% ({wins}W/{losses}L), "
            f"PnL=${total_pnl:.2f}"
        )

    # Final results
    print("\n" + "=" * 70)
    print("📊 BACKTEST RESULTS")
    print("=" * 70)

    total_trades = len(trades)
    wins = sum(1 for t in trades if t["pnl"] > 0)
    losses = sum(1 for t in trades if t["pnl"] <= 0)
    total_pnl = sum(t["pnl"] for t in trades)
    final_balance = balance + sum(t["size"] for t in open_positions) + total_pnl
    win_rate = wins / total_trades * 100 if total_trades > 0 else 0

    avg_win = sum(t["pnl"] for t in trades if t["pnl"] > 0) / wins if wins > 0 else 0
    avg_loss = (
        sum(t["pnl"] for t in trades if t["pnl"] <= 0) / losses if losses > 0 else 0
    )
    profit_factor = (
        abs(avg_win * wins / (avg_loss * losses))
        if losses > 0 and avg_loss != 0
        else float("inf")
    )

    best_trade = max(trades, key=lambda t: t["pnl"]) if trades else None
    worst_trade = min(trades, key=lambda t: t["pnl"]) if trades else None

    print(f"\n💰 Initial Balance:    ${INITIAL_BALANCE:.2f}")
    print(f"💰 Final Balance:      ${final_balance:.2f}")
    print(
        f"📈 Total Return:       {((final_balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100:.2f}%"
    )
    print(f"📊 Total P&L:          ${total_pnl:.2f}")
    print(f"")
    print(f"🔢 Total Signals:      {total_signals}")
    print(f"📋 Total Trades:       {total_trades}")
    print(f"✅ Wins:               {wins}")
    print(f"❌ Losses:             {losses}")
    print(f"📊 Win Rate:           {win_rate:.1f}%")
    print(f"📈 Profit Factor:      {profit_factor:.2f}")
    print(f"💵 Avg Win:            ${avg_win:.2f}")
    print(f"💸 Avg Loss:           ${avg_loss:.2f}")

    if best_trade:
        print(
            f"\n🏆 Best Trade:       {best_trade['symbol']} ${best_trade['pnl']:.2f} ({best_trade['pnl_pct']:.2f}%)"
        )
    if worst_trade:
        print(
            f"📉 Worst Trade:      {worst_trade['symbol']} ${worst_trade['pnl']:.2f} ({worst_trade['pnl_pct']:.2f}%)"
        )

    # Strategy support analysis
    print(f"\n🎯 Strategy Support Analysis:")
    strategy_stats = {}
    for t in trades:
        for s in t.get("supporting", []):
            if s not in strategy_stats:
                strategy_stats[s] = {"trades": 0, "wins": 0, "pnl": 0}
            strategy_stats[s]["trades"] += 1
            if t["pnl"] > 0:
                strategy_stats[s]["wins"] += 1
            strategy_stats[s]["pnl"] += t["pnl"]

    for name, stats in sorted(
        strategy_stats.items(), key=lambda x: x[1]["pnl"], reverse=True
    ):
        wr = stats["wins"] / stats["trades"] * 100 if stats["trades"] > 0 else 0
        print(
            f"   {name:25s}: {stats['trades']:3d} trades, {wr:5.1f}% WR, ${stats['pnl']:8.2f} PnL"
        )

    # Save results
    results = {
        "period": f"{start_str} → {end_str}",
        "initial_balance": INITIAL_BALANCE,
        "final_balance": final_balance,
        "total_return_pct": ((final_balance - INITIAL_BALANCE) / INITIAL_BALANCE) * 100,
        "total_pnl": total_pnl,
        "total_signals": total_signals,
        "total_trades": total_trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "strategy_stats": strategy_stats,
        "symbol_results": symbol_results,
    }

    output_file = os.path.join(
        os.path.dirname(__file__),
        "backtest_results",
        f"ensemble_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n💾 Results saved to: {output_file}")
    print("=" * 70)


if __name__ == "__main__":
    run_backtest()
