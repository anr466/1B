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
from backend.utils.binance_manager import BinanceManager
from backend.utils.data_provider import DataProvider
from backend.utils.trading_context import get_effective_is_demo

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ExecutorWorker")


class ExecutorWorker:
    def __init__(self):
        self.db = get_db_manager()
        self.binance_manager = BinanceManager()
        self.data_provider = DataProvider()
        self._price_cache = {}
        self._price_cache_ts = 0
        self._price_cache_ttl = 30

    def _get_cached_price(self, symbol: str) -> float:
        cached = self._price_cache.get(symbol)
        if cached and (time.time() - self._price_cache_ts) < self._price_cache_ttl:
            return cached
        return 0.0

    def _refresh_price_cache(self, symbols: list) -> dict:
        try:
            all_tickers = self.data_provider.client.get_symbol_ticker()
            price_map = {t["symbol"]: float(t["price"]) for t in all_tickers}
            self._price_cache = price_map
            self._price_cache_ts = time.time()
            return price_map
        except Exception as e:
            logger.warning(f"⚠️ Batch price fetch failed: {e}")
            return {}

    def _calculate_quantity(
        self, user_id: int, symbol: str, entry_price: float, settings: dict
    ) -> float:
        """حساب حجم الصفقة ديناميكياً من إعدادات المستخدم"""
        trade_amount = settings.get("trade_amount", 100.0)
        position_size_pct = settings.get("position_size_percentage", 10.0) / 100.0

        budget = trade_amount * position_size_pct
        if budget <= 0 or entry_price <= 0:
            return 0.001

        raw_qty = budget / entry_price

        try:
            info = self.data_provider.client.get_symbol_info(symbol)
            if info:
                for f in info.get("filters", []):
                    if f["filterType"] == "LOT_SIZE":
                        step = float(f["stepSize"])
                        min_qty = float(f["minQty"])
                        raw_qty = max(raw_qty, min_qty)
                        raw_qty = round(raw_qty - (raw_qty % step), 8)
                        break
        except Exception:
            pass

        return max(raw_qty, 0.001)

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

                    is_demo = bool(get_effective_is_demo(self.db, user_id))
                    settings = self.db.get_trading_settings(user_id, is_demo=is_demo)
                    if not settings or not settings.get("trading_enabled", False):
                        conn.execute(
                            "UPDATE signals_queue SET status = 'REJECTED', rejection_reason = 'Trading disabled', processed_at = NOW() WHERE id = %s",
                            (sig_id,),
                        )
                        continue

                    open_count = conn.execute(
                        "SELECT COUNT(*) FROM active_positions WHERE user_id = %s AND is_active = TRUE AND is_demo = %s",
                        (user_id, is_demo),
                    ).fetchone()[0]
                    if open_count >= settings.get("max_positions", 4):
                        conn.execute(
                            "UPDATE signals_queue SET status = 'REJECTED', rejection_reason = 'Max positions reached', processed_at = NOW() WHERE id = %s",
                            (sig_id,),
                        )
                        continue

                    # FIX 1: Reject real signals when Binance client is unavailable
                    # Previously: fell through to demo simulation (dangerous!)
                    if not is_demo:
                        client = self.binance_manager._get_binance_client(user_id)
                        if not client:
                            conn.execute(
                                "UPDATE signals_queue SET status = 'REJECTED', rejection_reason = 'Binance client unavailable — no API keys or connection failed', processed_at = NOW() WHERE id = %s",
                                (sig_id,),
                            )
                            logger.warning(
                                f"⛔ REJECTED real signal for User {user_id}: {symbol} — Binance client unavailable"
                            )
                            continue

                    quantity = self._calculate_quantity(
                        user_id, symbol, entry_price, settings
                    )
                    position_size = quantity * entry_price

                    # FIX: Re-validate signal before execution
                    # Check if price has moved >2% from signal entry (stale signal)
                    try:
                        current_price_data = self.data_provider._get_active_client()
                        if current_price_data:
                            live_ticker = current_price_data.get_symbol_ticker(
                                symbol=symbol
                            )
                            if live_ticker:
                                live_price = float(live_ticker["price"])
                                price_move_pct = (
                                    abs(live_price - entry_price) / entry_price
                                )
                                if price_move_pct > 0.02:  # 2% threshold
                                    logger.warning(
                                        f"⚠️ Signal stale for {symbol}: price moved {price_move_pct * 100:.1f}% "
                                        f"(signal: {entry_price}, live: {live_price}) — rejecting"
                                    )
                                    conn.execute(
                                        "UPDATE signals_queue SET status = 'REJECTED', rejection_reason = 'Price moved >2% from signal entry', processed_at = NOW() WHERE id = %s",
                                        (sig_id,),
                                    )
                                    continue
                                # Update entry_price to live price for better execution
                                entry_price = live_price
                                logger.info(
                                    f"🔄 Re-validated {symbol}: using live price {live_price} (signal was {entry_price})"
                                )
                    except Exception as reval_err:
                        logger.debug(
                            f"⚠️ Re-validation failed for {symbol}: {reval_err}"
                        )
                        # Continue with signal price if re-validation fails

                    logger.info(
                        f"⚡ Executing {pos_type} for User {user_id}: {symbol} @ {entry_price} qty={quantity:.6f}"
                    )

                    filled_price = entry_price
                    order_id = None

                    try:
                        if not is_demo:
                            client = self.binance_manager._get_binance_client(user_id)
                            order = client.create_order(
                                symbol=symbol,
                                side="BUY" if pos_type == "LONG" else "SELL",
                                type="MARKET",
                                quantity=quantity,
                            )
                            filled_price = float(
                                order.get("fills", [{}])[0].get("price", entry_price)
                            )
                            order_id = str(order.get("orderId", ""))
                            logger.info(
                                f"📤 Binance order executed: {symbol} qty={quantity:.6f}"
                            )
                        else:
                            logger.info(
                                f"📝 Demo mode for User {user_id} — simulating fill"
                            )
                    except Exception as e:
                        logger.error(f"❌ Execution failed for {symbol}: {e}")
                        conn.execute(
                            "UPDATE signals_queue SET status = 'REJECTED', rejection_reason = %s, processed_at = NOW() WHERE id = %s",
                            (str(e), sig_id),
                        )
                        continue

                    conn.execute(
                        """
                        INSERT INTO active_positions (
                            user_id, symbol, position_type, entry_price, stop_loss, take_profit,
                            strategy, timeframe, is_active, is_demo, entry_date, quantity, position_size,
                            order_id, trailing_sl_price, highest_price
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s, NOW(), %s, %s, %s, %s, %s)
                        """,
                        (
                            user_id,
                            symbol,
                            pos_type,
                            filled_price,
                            sl,
                            tp,
                            strategy,
                            "1h",
                            is_demo,
                            quantity,
                            position_size,
                            order_id,
                            filled_price,
                            filled_price,
                        ),
                    )

                    # FIX: Validate SL/TP at entry — reject if price already beyond SL
                    if pos_type == "LONG" and filled_price <= sl:
                        logger.warning(
                            f"⚠️ Entry price {filled_price} already at/below SL {sl} for {symbol} — closing immediately"
                        )
                        conn.execute(
                            """
                            UPDATE active_positions
                            SET is_active = FALSE, exit_price = %s, exit_reason = %s,
                                profit_loss = 0, profit_pct = 0, closed_at = NOW()
                            WHERE id = currval('active_positions_id_seq')
                            """,
                            (filled_price, "INVALID_SL_AT_ENTRY"),
                        )
                        continue
                    elif pos_type == "SHORT" and filled_price >= sl:
                        logger.warning(
                            f"⚠️ Entry price {filled_price} already at/above SL {sl} for {symbol} — closing immediately"
                        )
                        conn.execute(
                            """
                            UPDATE active_positions
                            SET is_active = FALSE, exit_price = %s, exit_reason = %s,
                                profit_loss = 0, profit_pct = 0, closed_at = NOW()
                            WHERE id = currval('active_positions_id_seq')
                            """,
                            (filled_price, "INVALID_SL_AT_ENTRY"),
                        )
                        continue

                    conn.execute(
                        "UPDATE signals_queue SET status = 'FILLED', processed_at = NOW(), trade_id = currval('active_positions_id_seq') WHERE id = %s",
                        (sig_id,),
                    )
                    logger.info(
                        f"✅ Filled {symbol} for User {user_id} @ {filled_price} qty={quantity:.6f}"
                    )

        except Exception as e:
            logger.error(f"❌ Error processing signals: {e}")

    async def monitor_open_positions(self):
        try:
            with get_db_connection() as conn:
                positions = conn.execute("""
                    SELECT id, user_id, symbol, position_type, entry_price, stop_loss, take_profit,
                           trailing_sl_price, highest_price, is_demo, quantity, position_size
                    FROM active_positions WHERE is_active = TRUE
                """).fetchall()

            if not positions:
                return

            symbols = list(set(pos[2] for pos in positions))

            # FIX 3: Use cached prices when fetch fails — don't skip monitoring
            price_map = self._refresh_price_cache(symbols)
            if not price_map:
                logger.warning(
                    "⚠️ Price fetch failed — using cached prices for SL/TP monitoring"
                )
                price_map = {
                    sym: self._get_cached_price(sym)
                    for sym in symbols
                    if self._get_cached_price(sym) > 0
                }
                if not price_map:
                    logger.error(
                        "❌ No prices available (fresh or cached) — skipping monitoring"
                    )
                    return

            for pos in positions:
                (
                    pos_id,
                    user_id,
                    symbol,
                    pos_type,
                    entry,
                    sl,
                    tp,
                    trail_sl,
                    highest,
                    is_demo,
                    quantity,
                    position_size,
                ) = pos
                try:
                    current_price = price_map.get(symbol)
                    if not current_price:
                        cached = self._get_cached_price(symbol)
                        if cached > 0:
                            current_price = cached
                        else:
                            continue

                    new_trail_sl = trail_sl or 0.0
                    new_highest = highest or entry

                    if pos_type == "LONG":
                        if current_price > new_highest:
                            new_highest = current_price
                            trail_distance = entry * 0.03
                            new_trail_sl = max(
                                new_trail_sl, current_price - trail_distance
                            )
                            new_trail_sl = max(new_trail_sl, entry)

                        if new_trail_sl > 0 and current_price <= new_trail_sl:
                            sl = new_trail_sl

                        if current_price <= sl:
                            should_exit, exit_reason, exit_price = (
                                True,
                                "STOP_LOSS",
                                sl,
                            )
                        elif current_price >= tp:
                            should_exit, exit_reason, exit_price = (
                                True,
                                "TAKE_PROFIT",
                                tp,
                            )
                        else:
                            should_exit, exit_reason, exit_price = (
                                False,
                                "",
                                current_price,
                            )
                    else:
                        if current_price < new_highest:
                            new_highest = current_price
                            trail_distance = entry * 0.03
                            new_trail_sl = min(
                                new_trail_sl if new_trail_sl > 0 else current_price,
                                current_price + trail_distance,
                            )
                            new_trail_sl = min(new_trail_sl, entry)

                        if new_trail_sl > 0 and current_price >= new_trail_sl:
                            sl = new_trail_sl

                        if current_price >= sl:
                            should_exit, exit_reason, exit_price = (
                                True,
                                "STOP_LOSS",
                                sl,
                            )
                        elif current_price <= tp:
                            should_exit, exit_reason, exit_price = (
                                True,
                                "TAKE_PROFIT",
                                tp,
                            )
                        else:
                            should_exit, exit_reason, exit_price = (
                                False,
                                "",
                                current_price,
                            )

                    with get_db_write_connection() as conn:
                        conn.execute(
                            """
                            UPDATE active_positions
                            SET trailing_sl_price = %s, highest_price = %s
                            WHERE id = %s AND is_active = TRUE
                            """,
                            (new_trail_sl, new_highest, pos_id),
                        )

                    if should_exit:
                        logger.info(
                            f"🚪 Exiting {symbol} for User {user_id} via {exit_reason} @ {exit_price}"
                        )

                        # FIX 2: Don't close DB position if Binance sell fails
                        binance_sell_ok = True
                        if not is_demo:
                            try:
                                client = self.binance_manager._get_binance_client(
                                    user_id
                                )
                                if client and quantity and quantity > 0:
                                    client.create_order(
                                        symbol=symbol,
                                        side="SELL" if pos_type == "LONG" else "BUY",
                                        type="MARKET",
                                        quantity=quantity,
                                    )
                                    logger.info(
                                        f"📤 Binance sell order executed for {symbol}"
                                    )
                                else:
                                    logger.error(
                                        f"❌ Cannot sell {symbol}: no Binance client or invalid quantity"
                                    )
                                    binance_sell_ok = False
                            except Exception as sell_err:
                                logger.error(
                                    f"❌ Binance sell failed for {symbol}: {sell_err}"
                                )
                                binance_sell_ok = False

                        # Only close in DB if Binance sell succeeded OR it's demo mode
                        if binance_sell_ok or is_demo:
                            pnl = (
                                (exit_price - entry)
                                if pos_type == "LONG"
                                else (entry - exit_price)
                            )
                            pnl_pct = (pnl / entry * 100) if entry > 0 else 0
                            realized_pnl = pnl * quantity if quantity else pnl

                            with get_db_write_connection() as conn:
                                conn.execute(
                                    """
                                    UPDATE active_positions
                                    SET is_active = FALSE, exit_price = %s, exit_reason = %s,
                                        profit_loss = %s, profit_pct = %s, closed_at = NOW()
                                    WHERE id = %s
                                    """,
                                    (
                                        exit_price,
                                        exit_reason,
                                        realized_pnl,
                                        pnl_pct,
                                        pos_id,
                                    ),
                                )

                                conn.execute(
                                    """
                                    UPDATE portfolio
                                    SET total_balance = total_balance + %s,
                                        available_balance = available_balance + %s
                                    WHERE user_id = %s AND is_demo = %s
                                    """,
                                    (realized_pnl, realized_pnl, user_id, is_demo),
                                )

                            logger.info(
                                f"✅ Position {pos_id} closed in DB: {symbol} PnL={realized_pnl:.2f}"
                            )
                        else:
                            logger.warning(
                                f"⏸️ Position {pos_id} ({symbol}) NOT closed in DB — Binance sell failed, will retry next cycle"
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
