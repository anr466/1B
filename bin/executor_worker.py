#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.infrastructure.db_access import (
    get_db_manager,
    get_db_connection,
    get_db_write_connection,
)
from backend.utils.binance_manager import BinanceManager
from backend.utils.data_provider import DataProvider

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ExecutorWorker")


class ExecutorWorker:
    def __init__(self):
        self.db = get_db_manager()
        self.binance_manager = BinanceManager()
        self.data_provider = DataProvider()

    async def process_pending_signals(self):
        try:
            with get_db_write_connection() as conn:
                rows = conn.execute("""
                    SELECT id, user_id, symbol, type, entry_price, stop_loss, take_profit, strategy_name
                    FROM signals_queue
                    WHERE status = 'PENDING' AND expires_at > NOW()
                    ORDER BY score DESC
                    FOR UPDATE SKIP LOCKED
                    LIMIT 10
                """).fetchall()

                if not rows:
                    return

                for row in rows:
                    sig_id, user_id, symbol, pos_type, entry_price, sl, tp, strategy = (
                        row
                    )

                    settings = self.db.get_trading_settings(user_id, is_demo=True)
                    if not settings or not settings.get("trading_enabled", False):
                        conn.execute(
                            "UPDATE signals_queue SET status = 'REJECTED', rejection_reason = 'Trading disabled', processed_at = NOW() WHERE id = %s",
                            (sig_id,),
                        )
                        continue

                    open_count = conn.execute(
                        "SELECT COUNT(*) FROM active_positions WHERE user_id = %s AND is_active = TRUE",
                        (user_id,),
                    ).fetchone()[0]
                    if open_count >= settings.get("max_positions", 4):
                        conn.execute(
                            "UPDATE signals_queue SET status = 'REJECTED', rejection_reason = 'Max positions reached', processed_at = NOW() WHERE id = %s",
                            (sig_id,),
                        )
                        continue

                    logger.info(
                        f"⚡ Executing {pos_type} for User {user_id}: {symbol} @ {entry_price}"
                    )

                    try:
                        client = self.binance_manager._get_binance_client(user_id)
                        if client:
                            order = client.create_order(
                                symbol=symbol,
                                side="BUY" if pos_type == "LONG" else "SELL",
                                type="MARKET",
                                quantity=0.001,
                            )
                            filled_price = float(
                                order.get("fills", [{}])[0].get("price", entry_price)
                            )
                        else:
                            filled_price = entry_price
                    except Exception as e:
                        logger.error(f"❌ Execution failed for {symbol}: {e}")
                        conn.execute(
                            "UPDATE signals_queue SET status = 'REJECTED', rejection_reason = %s, processed_at = NOW() WHERE id = %s",
                            (str(e), sig_id),
                        )
                        continue

                    conn.execute(
                        """
                        INSERT INTO active_positions (user_id, symbol, position_type, entry_price, stop_loss, take_profit, strategy, is_active, entry_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, NOW())
                    """,
                        (user_id, symbol, pos_type, filled_price, sl, tp, strategy),
                    )

                    conn.execute(
                        "UPDATE signals_queue SET status = 'FILLED', processed_at = NOW(), trade_id = currval('active_positions_id_seq') WHERE id = %s",
                        (sig_id,),
                    )
                    logger.info(
                        f"✅ Filled {symbol} for User {user_id} @ {filled_price}"
                    )

        except Exception as e:
            logger.error(f"❌ Error processing signals: {e}")

    async def monitor_open_positions(self):
        try:
            with get_db_connection() as conn:
                positions = conn.execute("""
                    SELECT id, user_id, symbol, position_type, entry_price, stop_loss, take_profit, trailing_sl_price, highest_price
                    FROM active_positions WHERE is_active = TRUE
                """).fetchall()

            if not positions:
                return

            symbols = list(set(pos[2] for pos in positions))
            try:
                all_tickers = self.data_provider.client.get_symbol_ticker()
                price_map = {t["symbol"]: float(t["price"]) for t in all_tickers}
            except Exception as e:
                logger.warning(f"⚠️ Batch price fetch failed: {e}")
                return

            for pos in positions:
                pos_id, user_id, symbol, pos_type, entry, sl, tp, trail_sl, highest = (
                    pos
                )
                try:
                    current_price = price_map.get(symbol)
                    if not current_price:
                        continue

                    should_exit = False
                    exit_reason = ""
                    exit_price = current_price

                    if pos_type == "LONG":
                        if current_price <= sl:
                            should_exit, exit_reason, exit_price = True, "STOP_LOSS", sl
                        elif current_price >= tp:
                            should_exit, exit_reason, exit_price = (
                                True,
                                "TAKE_PROFIT",
                                tp,
                            )

                    if should_exit:
                        logger.info(
                            f"🚪 Exiting {symbol} for User {user_id} via {exit_reason} @ {exit_price}"
                        )
                        pnl = exit_price - entry

                        with get_db_write_connection() as conn:
                            conn.execute(
                                """
                                UPDATE active_positions SET is_active = FALSE, exit_price = %s, exit_reason = %s, profit_loss = %s, closed_at = NOW()
                                WHERE id = %s
                            """,
                                (exit_price, exit_reason, pnl, pos_id),
                            )

                            conn.execute(
                                """
                                INSERT INTO trading_history (user_id, symbol, entry_price, exit_price, profit_loss, exit_reason, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                            """,
                                (
                                    user_id,
                                    symbol,
                                    entry,
                                    exit_price,
                                    pnl,
                                    exit_reason,
                                ),
                            )

                            conn.execute(
                                """
                                UPDATE portfolio SET total_balance = total_balance + %s, available_balance = available_balance + %s
                                WHERE user_id = %s
                            """,
                                (pnl, pnl, user_id),
                            )

                except Exception as e:
                    logger.warning(f"⚠️ Error monitoring {symbol}: {e}")

        except Exception as e:
            logger.error(f"❌ Error in monitor loop: {e}")

    async def run(self):
        logger.info("⚡ Executor Worker Started.")
        while True:
            try:
                await self.process_pending_signals()
                await self.monitor_open_positions()
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"💥 Executor loop error: {e}")
                await asyncio.sleep(10)


if __name__ == "__main__":
    worker = ExecutorWorker()
    asyncio.run(worker.run())
