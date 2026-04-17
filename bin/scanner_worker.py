#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.infrastructure.db_access import (
    get_db_manager,
    get_db_connection,
    get_db_write_connection,
)
from backend.core.coin_state_analyzer import CoinStateAnalyzer
from backend.core.cognitive_decision_matrix import CognitiveDecisionMatrix
from backend.core.performance_tracker import PerformanceTracker
from backend.core.modules.trend_module import TrendModule
from backend.core.modules.range_module import RangeModule
from backend.core.modules.volatility_module import VolatilityModule
from backend.core.modules.scalping_module import ScalpingModule
from backend.core.dynamic_coin_selector import DynamicCoinSelector
from backend.core.signal_candidate import SignalCandidate
from backend.utils.binance_public_client import BinancePublicClient
from backend.utils.trading_context import get_effective_is_demo

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ScannerWorker")


class ScannerWorker:
    def __init__(self):
        self.db = get_db_manager()
        self.binance = BinancePublicClient()
        self.coin_selector = DynamicCoinSelector(self.binance)

        self.analyzer = CoinStateAnalyzer()
        self.decision_matrix = CognitiveDecisionMatrix()
        self.performance_tracker = PerformanceTracker(self.decision_matrix)
        self.modules = [
            TrendModule(),
            RangeModule(),
            VolatilityModule(),
            ScalpingModule(),
        ]

        self.market_cache = {}
        self.last_market_fetch = 0
        self._signal_cooldown = {}
        self._cooldown_seconds = 600  # 10 minutes

    async def fetch_market_data(self):
        now = time.time()
        if now - self.last_market_fetch < 60:
            return self.market_cache

        logger.info("🌐 Fetching fresh market data for top coins...")

        try:
            tickers = self.binance.get_ticker()
            usdt_pairs = {
                t["symbol"]: t for t in tickers if t["symbol"].endswith("USDT")
            }

            coins = self.coin_selector.get_all_tradeable_coins()[:50]
            symbols = [c["symbol"] for c in coins]

            new_cache = {}
            for i, symbol in enumerate(symbols):
                if symbol not in usdt_pairs:
                    continue
                try:
                    klines = self.binance.get_klines(symbol, "1h", limit=100)
                    if klines and len(klines) >= 60:
                        import pandas as pd
                        df = pd.DataFrame(
                            klines,
                            columns=[
                                "timestamp", "open", "high", "low", "close", "volume",
                                "close_time", "quote_volume", "trades", "taker_buy_base",
                                "taker_buy_quote", "ignore"
                            ],
                        )
                        df["open"] = df["open"].astype(float)
                        df["high"] = df["high"].astype(float)
                        df["low"] = df["low"].astype(float)
                        df["close"] = df["close"].astype(float)
                        df["volume"] = df["volume"].astype(float)
                        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                        df.set_index("timestamp", inplace=True)
                        new_cache[symbol] = df
                    if i % 10 == 9:
                        time.sleep(2)
                except Exception as e:
                    logger.debug(f"⚠️ Skip {symbol}: {e}")

            self.market_cache = new_cache
            self.last_market_fetch = now
            logger.info(f"✅ Market cache updated: {len(new_cache)} symbols ready.")
            return new_cache
        except Exception as e:
            logger.error(f"❌ Market fetch failed: {e}")
            return self.market_cache

    async def analyze_user(self, user_id: int, market_data: dict):
        try:
            is_demo = bool(get_effective_is_demo(self.db, user_id))
            settings = self.db.get_trading_settings(user_id, is_demo=is_demo)
            if not settings or not settings.get("trading_enabled", False):
                return

            with get_db_connection() as conn:
                open_count = conn.execute(
                    "SELECT COUNT(*) FROM active_positions WHERE user_id = %s AND is_active = TRUE AND is_demo = %s",
                    (user_id, is_demo),
                ).fetchone()[0]

                max_pos = settings.get("max_positions", 4)
                if open_count >= max_pos:
                    return

                daily_loss = conn.execute(
                    """
                    SELECT COALESCE(SUM(profit_loss), 0)
                    FROM active_positions
                    WHERE user_id = %s AND is_demo = %s
                      AND is_active = FALSE
                      AND closed_at >= CURRENT_DATE
                    """,
                    (user_id, is_demo),
                ).fetchone()[0]

                total_balance = settings.get("total_balance", 1000.0)
                if total_balance <= 0:
                    portfolio_row = conn.execute(
                        "SELECT total_balance FROM portfolio WHERE user_id = %s AND is_demo = %s",
                        (user_id, is_demo),
                    ).fetchone()
                    total_balance = portfolio_row[0] if portfolio_row else 1000.0

                max_loss = (
                    settings.get("max_daily_loss_pct", 10.0) / 100 * total_balance
                )
                if daily_loss <= -max_loss:
                    return

            signals_to_insert = []
            now_ts = time.time()
            for symbol, df in market_data.items():
                # Cooldown check
                last_signaled = self._signal_cooldown.get(symbol, 0)
                if now_ts - last_signaled < self._cooldown_seconds:
                    continue

                state = self.analyzer.analyze(symbol, df)
                if not state:
                    continue

                # Build context with regime scores for modules
                context = {
                    "symbol": symbol,
                    "trend": state.trend,
                    "regime": state.regime,
                    "volatility": state.volatility,
                    "coin_type": state.coin_type,
                    "volume_ratio": state.volume_ratio,
                    "trend_confirmed_4h": state.trend_confirmed_4h,
                    "trend_confirmed_macd": state.trend_confirmed_macd,
                    "trend_confirmed_volume": state.trend_confirmed_volume,
                    "ema_alignment": state.ema_alignment,
                    "regime_scores": state.regime_scores,
                }

                # Evaluate all modules — each returns SignalCandidate (never None)
                best_candidate = None
                best_score = -1

                for module in self.modules:
                    if state.regime in module.supported_regimes():
                        candidate = module.evaluate(df, context)
                        if candidate.is_valid:
                            # Set prices
                            candidate.entry_price = module.get_entry_price(df, candidate)
                            candidate.stop_loss = module.get_stop_loss(df, candidate)
                            candidate.take_profit = module.get_take_profit(df, candidate)

                            # Score via decision matrix (now uses dynamic weights)
                            decision = self.decision_matrix.evaluate(candidate.to_dict(), context)
                            if decision["score"] > best_score:
                                best_score = decision["score"]
                                best_candidate = candidate
                                best_candidate.confidence = decision["score"]
                                best_candidate.metadata["decision"] = decision["decision"]
                                best_candidate.metadata["reason"] = decision["reason"]
                                best_candidate.metadata["weights"] = decision["weights"]

                if best_candidate and best_score >= 55:
                    signals_to_insert.append(
                        {
                            "user_id": user_id,
                            "symbol": best_candidate.symbol,
                            "type": best_candidate.signal_type,
                            "entry_price": best_candidate.entry_price,
                            "stop_loss": best_candidate.stop_loss,
                            "take_profit": best_candidate.take_profit,
                            "score": best_score,
                            "strategy_name": best_candidate.strategy,
                            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=30),
                        }
                    )
                    self._signal_cooldown[symbol] = now_ts

            if signals_to_insert:
                with get_db_write_connection() as conn:
                    for sig in signals_to_insert:
                        conn.execute(
                            """
                            INSERT INTO signals_queue
                            (user_id, symbol, type, entry_price, stop_loss, take_profit, score, strategy_name, expires_at)
                            VALUES (%(user_id)s, %(symbol)s, %(type)s, %(entry_price)s, %(stop_loss)s, %(take_profit)s, %(score)s, %(strategy_name)s, %(expires_at)s)
                        """,
                            sig,
                        )
                logger.info(
                    f"📝 User {user_id}: Generated {len(signals_to_insert)} signals."
                )

        except Exception as e:
            logger.error(f"❌ Error analyzing user {user_id}: {e}")

    def load_closed_trades_for_learning(self):
        """تحميل الصفقات المغلقة من قاعدة البيانات للتعلم"""
        try:
            with get_db_connection() as conn:
                rows = conn.execute("""
                    SELECT ap.symbol, ap.strategy, ap.position_type, ap.entry_price,
                           ap.exit_price, ap.quantity, ap.profit_loss, ap.exit_reason,
                           ap.closed_at
                    FROM active_positions ap
                    WHERE ap.is_active = FALSE
                      AND ap.profit_loss IS NOT NULL
                      AND ap.closed_at > NOW() - INTERVAL '30 days'
                    ORDER BY ap.closed_at DESC
                """).fetchall()

                loaded = 0
                for row in rows:
                    trade_data = {
                        "symbol": row[0],
                        "strategy": row[1] or "Unknown",
                        "type": row[2],
                        "entry_price": float(row[3] or 0),
                        "exit_price": float(row[4] or 0),
                        "quantity": float(row[5] or 0),
                        "pnl": float(row[6] or 0),
                        "exit_reason": row[7] or "UNKNOWN",
                        "closed_at": str(row[8]) if row[8] else "",
                    }
                    self.performance_tracker.record_trade(trade_data)
                    loaded += 1

                if loaded > 0:
                    logger.info(f"📚 Loaded {loaded} closed trades for learning")
                    summary = self.performance_tracker.get_performance_summary()
                    logger.info(
                        f"📊 Performance: {summary['total_trades']} trades, "
                        f"WR={summary['win_rate']:.1%}, PnL=${summary['total_pnl']:.2f}"
                    )
        except Exception as e:
            logger.error(f"❌ Failed to load closed trades: {e}")

    async def run(self):
        logger.info("🔍 Scanner Worker Started.")

        # Load historical trades for learning
        self.load_closed_trades_for_learning()

        while True:
            try:
                market_data = await self.fetch_market_data()
                if not market_data:
                    await asyncio.sleep(5)
                    continue

                with get_db_connection() as conn:
                    users = conn.execute(
                        "SELECT DISTINCT user_id FROM user_settings WHERE trading_enabled = TRUE"
                    ).fetchall()

                if users:
                    tasks = [self.analyze_user(u[0], market_data) for u in users]
                    await asyncio.gather(*tasks)

                # Log performance summary every 10 minutes
                if self.performance_tracker.total_trades > 0 and self.performance_tracker.total_trades % 5 == 0:
                    summary = self.performance_tracker.get_performance_summary()
                    logger.info(
                        f"📊 Live Performance: {summary['total_trades']} trades, "
                        f"WR={summary['win_rate']:.1%}, PnL=${summary['total_pnl']:.2f}"
                    )

                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"💥 Scanner loop error: {e}")
                await asyncio.sleep(10)


if __name__ == "__main__":
    worker = ScannerWorker()
    asyncio.run(worker.run())
