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
from backend.core.modules.trend_module import TrendModule
from backend.core.modules.range_module import RangeModule
from backend.core.modules.volatility_module import VolatilityModule
from backend.core.modules.scalping_module import ScalpingModule
from backend.core.dynamic_coin_selector import DynamicCoinSelector
from backend.utils.binance_public_client import BinancePublicClient
from backend.utils.trading_context import get_effective_is_demo

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ScannerWorker")


class ScannerWorker:
    def __init__(self):
        self.db = get_db_manager()
        # FIX: Use lightweight public client — bypasses python-binance geo-block
        self.binance = BinancePublicClient()
        self.coin_selector = DynamicCoinSelector(self.binance)

        self.analyzer = CoinStateAnalyzer()
        self.decision_matrix = CognitiveDecisionMatrix()
        self.modules = [
            TrendModule(),
            RangeModule(),
            VolatilityModule(),
            ScalpingModule(),
        ]

        self.market_cache = {}
        self.last_market_fetch = 0

    async def fetch_market_data(self):
        now = time.time()
        if now - self.last_market_fetch < 60:
            return self.market_cache

        logger.info("🌐 Fetching fresh market data for top coins...")

        try:
            # FIX: Use lightweight public client with working endpoints
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
                        # Convert to DataFrame format expected by analyzer
                        import pandas as pd

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
            for symbol, df in market_data.items():
                state = self.analyzer.analyze(symbol, df)
                if not state or state.recommendation == "AVOID":
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

                for module in self.modules:
                    if state.regime in module.supported_regimes():
                        signal = module.evaluate(df, context)
                        if signal:
                            signal["entry_price"] = module.get_entry_price(df, signal)
                            signal["stop_loss"] = module.get_stop_loss(df, signal)
                            signal["take_profit"] = module.get_take_profit(df, signal)

                            decision = self.decision_matrix.evaluate(signal, context)
                            if (
                                decision["decision"] in ["ENTER", "ENTER_REDUCED"]
                                and decision["score"] > best_score
                            ):
                                best_score = decision["score"]
                                best_signal = {**signal, **decision}

                if best_signal and best_score >= 50:
                    signals_to_insert.append(
                        {
                            "user_id": user_id,
                            "symbol": symbol,
                            "type": best_signal.get("type", "LONG"),
                            "entry_price": best_signal["entry_price"],
                            "stop_loss": best_signal["stop_loss"],
                            "take_profit": best_signal["take_profit"],
                            "score": best_score,
                            "strategy_name": best_signal.get("strategy", "Unknown"),
                            "expires_at": datetime.now(timezone.utc)
                            + timedelta(seconds=30),
                        }
                    )

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

    async def run(self):
        logger.info("🔍 Scanner Worker Started.")
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

                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"💥 Scanner loop error: {e}")
                await asyncio.sleep(10)


if __name__ == "__main__":
    worker = ScannerWorker()
    asyncio.run(worker.run())
