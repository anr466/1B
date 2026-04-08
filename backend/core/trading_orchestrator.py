#!/usr/bin/env python3

import logging
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime

from backend.core.coin_state_analyzer import CoinStateAnalyzer, CoinState
from backend.core.strategy_router import StrategyRouter
from backend.core.entry_executor import EntryExecutor
from backend.core.monitoring_engine import MonitoringEngine
from backend.core.exit_engine import ExitEngine

logger = logging.getLogger(__name__)


class TradingOrchestrator:
    def __init__(
        self,
        data_provider=None,
        db=None,
        position_manager=None,
        is_demo_trading: bool = True,
        user_id: int = None,
    ):
        self.data_provider = data_provider
        self.db = db
        self.position_manager = position_manager
        self.is_demo_trading = is_demo_trading
        self.user_id = user_id

        self.state_analyzer = CoinStateAnalyzer()
        self.strategy_router = StrategyRouter()
        self.entry_executor = EntryExecutor()
        self.monitoring_engine = MonitoringEngine()
        self.exit_engine = ExitEngine()

    def run_cycle(self, symbols: List[str]) -> Dict:
        result = {
            "timestamp": datetime.now().isoformat(),
            "user_id": self.user_id,
            "mode": "demo" if self.is_demo_trading else "real",
            "states": [],
            "signals": [],
            "positions_opened": 0,
            "positions_monitored": 0,
            "positions_closed": 0,
            "errors": [],
        }

        open_positions = self._get_open_positions()
        result["positions_monitored"] = len(open_positions)

        closed = self._monitor_and_exit(open_positions)
        result["positions_closed"] = len(closed)

        can_open = self._can_open_new_positions(open_positions)
        if can_open:
            new_signals = self._scan_and_enter(symbols, open_positions)
            result["signals"] = new_signals
            result["positions_opened"] = len(new_signals)

        for sym in symbols:
            try:
                df = self.data_provider.get_historical_data(sym, "1h", limit=200)
                if df is None or len(df) < 55:
                    continue

                df = self._add_indicators(df)
                state = self.state_analyzer.analyze(sym, df)
                if state:
                    result["states"].append(
                        {
                            "symbol": state.symbol,
                            "trend": state.trend,
                            "regime": state.regime,
                            "recommendation": state.recommendation,
                            "confidence": state.confidence,
                        }
                    )
            except Exception as e:
                result["errors"].append(f"{sym}: {e}")

        return result

    def _scan_and_enter(self, symbols, open_positions) -> List[Dict]:
        opened = []
        open_symbols = {p["symbol"] for p in open_positions}

        for symbol in symbols:
            if symbol in open_symbols:
                continue

            try:
                df = self.data_provider.get_historical_data(symbol, "1h", limit=200)
                if df is None or len(df) < 55:
                    continue

                df = self._add_indicators(df)

                state = self.state_analyzer.analyze(symbol, df)
                if not state or state.recommendation == "AVOID":
                    continue

                route = self.strategy_router.route(state)
                if not route:
                    continue

                signal = self.entry_executor.confirm_entry(symbol, df, state, route)
                if not signal:
                    continue

                logger.info(
                    f"   🎯 [{symbol}] {route['strategy']} | "
                    f"State: {state.trend}/{state.regime} | "
                    f"Score: {signal['score']} | "
                    f"Confidence: {signal['confidence']:.0f}"
                )

                success = self._open_position(symbol, signal)
                if success:
                    opened.append(signal)

            except Exception as e:
                logger.error(f"   ❌ [{symbol}] Error: {e}")

        return opened

    def _monitor_and_exit(self, positions) -> List[Dict]:
        if not positions:
            return []

        current_prices = {}
        for pos in positions:
            price = self._get_current_price(pos["symbol"])
            if price:
                current_prices[pos["symbol"]] = price

        actions = self.monitoring_engine.monitor_positions(positions, current_prices)
        closed = []

        for action in actions:
            symbol = action.get("symbol")
            pos = next((p for p in positions if p["symbol"] == symbol), None)
            if not pos:
                continue

            if action["type"] == "CLOSE":
                exit_price = action.get("price") or current_prices.get(symbol)
                if not exit_price:
                    continue

                result = self.exit_engine.execute_exit(
                    pos, exit_price, action["reason"], close_pct=1.0
                )
                if result["success"]:
                    self._close_position_in_db(pos, result)
                    closed.append(result)

            elif action["type"] == "PARTIAL_CLOSE":
                exit_price = current_prices.get(symbol)
                if not exit_price:
                    continue

                result = self.exit_engine.execute_exit(
                    pos, exit_price, action["reason"], close_pct=action["close_pct"]
                )
                if result["success"]:
                    self._partial_close_in_db(pos, result)
                    closed.append(result)

            elif action["type"] == "UPDATE":
                self._update_position_in_db(pos, action["updates"])

        return closed

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if "rsi" not in df.columns:
            df = self._compute_rsi(df)
        if "adx" not in df.columns:
            df = self._compute_adx(df)
        return df

    def _compute_rsi(self, df, period=14):
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, float("inf"))
        df["rsi"] = 100 - (100 / (1 + rs))
        return df

    def _compute_adx(self, df, period=14):
        high = df["high"]
        low = df["low"]
        close = df["close"]

        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        atr = (
            pd.concat(
                [
                    high - low,
                    (high - close.shift(1)).abs(),
                    (low - close.shift(1)).abs(),
                ],
                axis=1,
            )
            .max(axis=1)
            .rolling(period)
            .mean()
        )

        plus_di = 100 * plus_dm.ewm(alpha=1 / period).mean() / atr
        minus_di = 100 * minus_dm.ewm(alpha=1 / period).mean() / atr

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        df["adx"] = dx.ewm(alpha=1 / period).mean()
        return df

    def _get_open_positions(self):
        if not self.db:
            return []
        try:
            return (
                self.db.get_user_active_positions(
                    self.user_id, is_demo=self.is_demo_trading
                )
                or []
            )
        except Exception:
            return []

    def _get_current_price(self, symbol):
        try:
            if self.data_provider:
                return self.data_provider.get_current_price(symbol)
        except Exception:
            pass
        return None

    def _can_open_new_positions(self, open_positions):
        return len(open_positions) < 5

    def _open_position(self, symbol, signal):
        if self.position_manager:
            return self.position_manager._open_position(symbol, signal) is not None
        return False

    def _close_position_in_db(self, position, result):
        if not self.db:
            return
        try:
            with self.db.get_write_connection() as conn:
                self.db.close_position_on_conn(
                    conn,
                    position["id"],
                    result["exit_price"],
                    result["reason"],
                    result["pnl"],
                    exit_commission=result["exit_commission"],
                )
                balance_row = conn.execute(
                    "SELECT available_balance FROM portfolio WHERE user_id = %s AND is_demo = %s LIMIT 1",
                    (self.user_id, self.is_demo_trading),
                ).fetchone()
                if balance_row and len(balance_row) > 0:
                    current = float(balance_row[0] or 0)
                    new_balance = current + result["pnl"]
                    self.db.update_user_balance_on_conn(
                        conn, self.user_id, new_balance, self.is_demo_trading
                    )
        except Exception as e:
            logger.error(f"   ❌ DB close error: {e}")

    def _partial_close_in_db(self, position, result):
        if not self.db:
            return
        try:
            with self.db.get_write_connection() as conn:
                remaining_qty = position["quantity"] * (1 - result["close_pct"])
                conn.execute(
                    "UPDATE active_positions SET quantity = %s, updated_at = NOW() WHERE id = %s",
                    (remaining_qty, position["id"]),
                )
        except Exception as e:
            logger.error(f"   ❌ DB partial close error: {e}")

    def _update_position_in_db(self, position, updates):
        if not self.db or not updates:
            return
        try:
            with self.db.get_write_connection() as conn:
                if "trailing_sl_price" in updates:
                    conn.execute(
                        "UPDATE active_positions SET trailing_sl_price = %s, updated_at = NOW() WHERE id = %s",
                        (updates["trailing_sl_price"], position["id"]),
                    )
                if "highest_price" in updates:
                    conn.execute(
                        "UPDATE active_positions SET highest_price = %s WHERE id = %s",
                        (updates["highest_price"], position["id"]),
                    )
        except Exception as e:
            logger.error(f"   ❌ DB update error: {e}")
