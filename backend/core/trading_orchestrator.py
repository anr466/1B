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
from backend.core.portfolio_risk_manager import PortfolioRiskManager
from backend.core.mtf_confirmation import MTFConfirmationEngine
from backend.core.cognitive_decision_matrix import CognitiveDecisionMatrix
from backend.core.modules.trend_module import TrendModule
from backend.core.modules.range_module import RangeModule
from backend.core.modules.volatility_module import VolatilityModule
from backend.core.modules.scalping_module import ScalpingModule

logger = logging.getLogger(__name__)


class TradingOrchestrator:
    def __init__(
        self,
        data_provider=None,
        db=None,
        position_manager=None,
        is_demo_trading: bool = True,
        user_id: int = None,
        trading_brain=None,
        adaptive_optimizer=None,
        ml_training_manager=None,
    ):
        self.data_provider = data_provider
        self.db = db
        self.position_manager = position_manager
        self.is_demo_trading = is_demo_trading
        self.user_id = user_id
        self.trading_brain = trading_brain
        self.adaptive_optimizer = adaptive_optimizer
        self.ml_training_manager = ml_training_manager

        self.state_analyzer = CoinStateAnalyzer()
        self.strategy_router = StrategyRouter()
        self.entry_executor = EntryExecutor()
        self.monitoring_engine = MonitoringEngine()
        self.exit_engine = ExitEngine()
        self.risk_manager = PortfolioRiskManager()
        self.mtf = MTFConfirmationEngine(data_provider=data_provider)
        self.decision_matrix = CognitiveDecisionMatrix()

        self.strategy_modules = [
            TrendModule(),
            RangeModule(),
            VolatilityModule(),
            ScalpingModule(),
        ]

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

        balance = self._get_balance()
        tier = self.risk_manager.classify_tier(balance)
        result["tier"] = tier.name

        open_positions = self._get_open_positions()
        result["positions_monitored"] = len(open_positions)

        closed = self._monitor_and_exit(open_positions)
        result["positions_closed"] = len(closed)

        heat = self.risk_manager.check_heat(open_positions, balance)
        result["heat"] = heat

        can_open, reason = self._can_open_new_positions(open_positions, balance)
        if can_open:
            new_signals = self._scan_and_enter(symbols, open_positions, balance)
            result["signals"] = new_signals
            result["positions_opened"] = len(new_signals)
        else:
            logger.info(f"   ⏸️ Cannot open: {reason}")

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
                            "coin_type": state.coin_type,
                        }
                    )
            except Exception as e:
                result["errors"].append(f"{sym}: {e}")

        return result

    def _scan_and_enter(self, symbols, open_positions, balance) -> List[Dict]:
        logger.info(f"   🔎 Scanning {len(symbols)} symbols for entries...")
        opened = []
        open_symbols = {p["symbol"] for p in open_positions}
        tier = self.risk_manager.classify_tier(balance)

        for symbol in symbols:
            if symbol in open_symbols:
                continue

            heat = self.risk_manager.check_heat(
                open_positions + [{"symbol": s} for s in opened], balance
            )
            if not heat["can_open"]:
                logger.info(f"   ⏸️ Heat limit reached, stopping scan")
                break

            try:
                df = self.data_provider.get_historical_data(symbol, "1h", limit=200)
                if df is None or len(df) < 55:
                    continue

                df = self._add_indicators(df)
                state = self.state_analyzer.analyze(symbol, df)
                if not state or state.recommendation == "AVOID":
                    if symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
                        logger.info(
                            f"   ⏭️ [{symbol}] AVOID (trend={state.trend if state else 'N/A'}, regime={state.regime if state else 'N/A'})"
                        )
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

                for module in self.strategy_modules:
                    if state.regime not in module.supported_regimes():
                        continue

                    signal = module.evaluate(df, context)
                    if not signal:
                        continue

                    logger.info(
                        f"   📈 [{symbol}] {module.name()} signal: {signal['strategy']} ({signal['type']})"
                    )
                    signal["entry_price"] = module.get_entry_price(df, signal)
                    signal["stop_loss"] = module.get_stop_loss(df, signal)
                    signal["take_profit"] = module.get_take_profit(df, signal)

                    decision = self.decision_matrix.evaluate(signal, context)
                    logger.info(
                        f"   📊 [{symbol}] {module.name()}: score={decision['score']}, decision={decision['decision']}"
                    )
                    if decision["decision"] in ["ENTER", "ENTER_REDUCED"]:
                        if decision["score"] > best_score:
                            best_score = decision["score"]
                            best_signal = {**signal, **decision}

                if not best_signal:
                    logger.info(
                        f"   ⏭️ [{symbol}] No qualifying signal (regime={state.regime})"
                    )
                    continue

                if self.trading_brain:
                    market_data = {
                        "rsi": best_signal.get("rsi", 50),
                        "adx": best_signal.get("adx", 20),
                        "volatility": state.atr_pct,
                        "trend": state.trend,
                        "volume_ratio": 1.0,
                        "bb_position": 0.5,
                    }
                    brain_decision = self.trading_brain.think(best_signal, market_data)
                    if brain_decision.get("action") == "REJECT":
                        logger.info(
                            f"   🧠 [{symbol}] Brain rejected: {brain_decision.get('reason', 'unknown')}"
                        )
                        continue

                mtf_result = self.mtf.confirm_entry(symbol, best_signal, df)
                if not mtf_result["confirmed"]:
                    logger.info(
                        f"   ⏳ [{symbol}] MTF not confirmed: {mtf_result['reason']}"
                    )
                    continue
                best_signal["mtf_score"] = mtf_result["score"]

                size_result = self.risk_manager.get_position_size(
                    balance, state.coin_type, best_signal["confidence"], 0.05
                )
                if not size_result["can_trade"]:
                    continue

                logger.info(
                    f"   🎯 [{symbol}] {best_signal['strategy']} | "
                    f"State: {state.trend}/{state.regime} | "
                    f"Tier: {tier.name} | Size: ${size_result['position_usd']:.0f} | "
                    f"CognitiveScore: {best_signal['score']} | Decision: {best_signal['decision']}"
                )

                best_signal["position_size"] = size_result["position_usd"]
                success = self._open_position(symbol, best_signal)
                if success:
                    opened.append(best_signal)

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

                # MTF Exit Confirmation for discretionary exits (not SL)
                reason = action.get("reason", "")
                if reason not in ("STOP_LOSS",):
                    mtf_exit = self.mtf.confirm_exit(symbol, pos)
                    if mtf_exit["confirmed"]:
                        logger.info(
                            f"   📉 [{symbol}] MTF exit confirmed: {mtf_exit['reason']} (score={mtf_exit['score']})"
                        )
                    else:
                        logger.debug(
                            f"   ⏳ [{symbol}] MTF exit not confirmed: {mtf_exit['reason']}, proceeding anyway"
                        )

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
        if "ema21" not in df.columns:
            close = df["close"]
            df["ema21"] = close.ewm(span=21, adjust=False).mean()
            df["ema55"] = close.ewm(span=55, adjust=False).mean()
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

    def _get_balance(self):
        if not self.db:
            return 1000.0
        try:
            row = (
                self.db.get_connection()
                .execute(
                    "SELECT available_balance FROM portfolio WHERE user_id = %s AND is_demo = %s LIMIT 1",
                    (self.user_id, self.is_demo_trading),
                )
                .fetchone()
            )
            return float(row[0]) if row and row[0] else 1000.0
        except Exception:
            return 1000.0

    def _can_open_new_positions(self, open_positions, balance):
        heat = self.risk_manager.check_heat(open_positions, balance)
        if not heat["can_open"]:
            return (
                False,
                f"Heat limit: {heat['current_heat_pct']}%/{heat['max_heat_pct']}%",
            )
        if heat["positions_count"] >= heat["max_positions"]:
            return (
                False,
                f"Max positions: {heat['positions_count']}/{heat['max_positions']}",
            )
        return True, "OK"

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

            # Record trade for ML learning
            if self.ml_training_manager:
                try:
                    self.ml_training_manager.add_real_trade(
                        symbol=position.get("symbol", ""),
                        strategy=position.get("strategy", "unknown"),
                        timeframe="1h",
                        entry_price=position.get("entry_price", 0),
                        exit_price=result["exit_price"],
                        profit_loss=result["pnl"],
                        profit_pct=result["pnl_pct"],
                        indicators={
                            "rsi": position.get("rsi", 50),
                            "adx": position.get("adx", 20),
                            "atr_pct": position.get("atr_pct", 0),
                        },
                        source="demo_trading"
                        if self.is_demo_trading
                        else "real_trading",
                    )
                except Exception as ml_err:
                    logger.debug(f"   ⚠️ ML recording failed: {ml_err}")

            # Learn from result via TradingBrain
            if self.trading_brain and result.get("reason"):
                try:
                    self.trading_brain.learn_from_result(
                        position.get("symbol", ""),
                        {
                            "profit_loss": result["pnl"],
                            "pnl_pct": result["pnl_pct"],
                            "exit_reason": result["reason"],
                            "is_win": result.get("is_win", False),
                        },
                    )
                except Exception as learn_err:
                    logger.debug(f"   ⚠️ Brain learning failed: {learn_err}")

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
