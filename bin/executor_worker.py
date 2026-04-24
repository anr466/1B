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
from backend.core.smart_exit_engine import SmartExitEngine
from backend.core.smart_performance_tracker import performance_tracker
from backend.utils.binance_utils import place_oco_order, cancel_oco_order, get_symbol_filters, prepare_order_params

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ExecutorWorker")


class ExecutorWorker:
    def __init__(self):
        self.db = get_db_manager()
        self.binance_manager = BinanceManager()
        self.data_provider = DataProvider()
        self.smart_exit = SmartExitEngine(atr_multiplier=2.5)
        self._price_cache = {}
        self._price_cache_ts = 0
        self._price_cache_ttl = 30

    async def run(self):
        logger.info("⚡ Executor Worker Started.")
        try:
            # 1. Run Reconciliation on Startup
            await self.reconcile_positions()
        except Exception as e:
            logger.error(f"💥 Fatal error during Reconciliation: {e}")
            # Continue to main loop even if reconciliation fails

        # 2. Main Loop
        while True:
            try:
                await self.process_pending_signals()
                await self.monitor_open_positions()
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"💥 Executor loop error: {e}")
                await asyncio.sleep(10)

    async def reconcile_positions(self):
        """
        مقارنة الصفحات المفتوحة في Binance مع قاعدة البيانات وإصلاح أي اختلاف.
        يضمن عدم وجود 'Zombie Trades'.
        """
        logger.info("🔄 Starting Position Reconciliation...")
        try:
            with get_db_connection() as conn:
                users = conn.execute("SELECT DISTINCT user_id FROM user_settings WHERE trading_enabled = TRUE").fetchall()

                for (user_id,) in users:
                    is_demo = bool(get_effective_is_demo(self.db, user_id))
                    if is_demo:
                        continue

                    client = self.binance_manager._get_binance_client(user_id)
                    if not client:
                        continue

                    try:
                        # Wrap blocking Binance API call in asyncio.to_thread
                        open_orders = await asyncio.to_thread(client.get_open_orders)
                        db_positions = conn.execute(
                            "SELECT id, symbol, quantity_remaining, take_profit, stop_loss FROM active_positions WHERE user_id = %s AND is_active = TRUE AND is_demo = FALSE",
                            (user_id,)
                        ).fetchall()

                        for pos_id, symbol, qty, tp, sl in db_positions:
                            symbol_orders = [o for o in open_orders if o['symbol'] == symbol]
                            if not symbol_orders:
                                logger.warning(f"⚠️ Missing OCO for Position {pos_id} ({symbol}). Attempting to place.")
                                pass
                    except Exception as e:
                        logger.error(f"❌ Reconciliation error for User {user_id}: {e}")

        except Exception as e:
            logger.error(f"❌ Global Reconciliation error: {e}")

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
                    sig_id, user_id, symbol, pos_type, entry_price, sl, tp, strategy = row

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
                    if not is_demo:
                        client = self.binance_manager._get_binance_client(user_id)
                        if not client:
                            conn.execute(
                                "UPDATE signals_queue SET status = 'REJECTED', rejection_reason = 'Binance client unavailable', processed_at = NOW() WHERE id = %s",
                                (sig_id,),
                            )
                            continue

                    quantity = self._calculate_quantity(user_id, symbol, entry_price, settings)
                    if quantity <= 0:
                         conn.execute(
                            "UPDATE signals_queue SET status = 'REJECTED', rejection_reason = 'Invalid quantity', processed_at = NOW() WHERE id = %s",
                            (sig_id,),
                        )
                         continue

                    logger.info(f"⚡ Executing {pos_type} for User {user_id}: {symbol} @ {entry_price} qty={quantity:.6f}")

                    filled_price = entry_price
                    order_id = None

                    try:
                        if not is_demo:
                            client = self.binance_manager._get_binance_client(user_id)
                            # Wrap blocking Binance API call in asyncio.to_thread
                            order = await asyncio.to_thread(
                                client.create_order,
                                symbol=symbol,
                                side="BUY" if pos_type == "LONG" else "SELL",
                                type="MARKET",
                                quantity=quantity,
                            )
                            filled_price = float(order.get("fills", [{}])[0].get("price", entry_price))
                            order_id = str(order.get("orderId", ""))
                            logger.info(f"📤 Binance order executed: {symbol} qty={quantity:.6f}")
                        else:
                            logger.info(f"📝 Demo mode for User {user_id} — simulating fill")
                    except Exception as e:
                        logger.error(f"❌ Execution failed for {symbol}: {e}")
                        conn.execute(
                            "UPDATE signals_queue SET status = 'REJECTED', rejection_reason = %s, processed_at = NOW() WHERE id = %s",
                            (str(e), sig_id),
                        )
                        continue

                    # Insert Position
                    conn.execute(
                        """
                        INSERT INTO active_positions (
                            user_id, symbol, position_type, entry_price, stop_loss, take_profit,
                            strategy, timeframe, is_active, is_demo, entry_date, quantity, quantity_remaining, position_size,
                            order_id, trailing_sl_price, highest_price
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s, NOW(), %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user_id, symbol, pos_type, filled_price, sl, tp,
                            strategy, "1h", is_demo, quantity, quantity, quantity * filled_price,
                            order_id, filled_price, filled_price,
                        ),
                    )

                    pos_id = conn.execute("SELECT currval('active_positions_id_seq')").fetchone()[0]

                    # FIX 2: Place OCO Order for Safety Net
                    if not is_demo:
                        client = self.binance_manager._get_binance_client(user_id)
                        oco_side = "SELL" if pos_type == "LONG" else "BUY"
                        # Wrap blocking Binance API call in asyncio.to_thread
                        oco_order = await asyncio.to_thread(place_oco_order, client, symbol, oco_side, quantity, tp, sl)
                         
                        if oco_order:
                            order_list_id = oco_order.get("orderListId")
                            conn.execute(
                                "UPDATE active_positions SET order_list_id = %s WHERE id = %s",
                                (order_list_id, pos_id)
                            )
                            logger.info(f"🛡️ OCO Order placed for Position {pos_id}: ListID {order_list_id}")
                        else:
                            logger.error(f"❌ Failed to place OCO for Position {pos_id}. Manual monitoring required!")

                    conn.execute(
                        "UPDATE signals_queue SET status = 'FILLED', processed_at = NOW(), trade_id = %s WHERE id = %s",
                        (pos_id, sig_id),
                    )
                    logger.info(f"✅ Filled {symbol} for User {user_id} @ {filled_price} qty={quantity:.6f}")

        except Exception as e:
            logger.error(f"❌ Error processing signals: {e}")

    async def monitor_open_positions(self):
        try:
            with get_db_connection() as conn:
                positions = conn.execute("""
                    SELECT id, user_id, symbol, position_type, entry_price, stop_loss, take_profit,
                           trailing_sl_price, highest_price, is_demo, quantity, quantity_remaining, 
                           exit_phase, break_even_activated, strategy, order_list_id
                    FROM active_positions WHERE is_active = TRUE
                """).fetchall()

            if not positions:
                return

            symbols = list(set(pos[2] for pos in positions))
            price_map = self._refresh_price_cache(symbols)
            if not price_map:
                return

            atr_map, regime_map = self._analyze_market_for_symbols(symbols)

            for pos in positions:
                (
                    pos_id, user_id, symbol, pos_type, entry, sl, tp,
                    trail_sl, highest, is_demo, quantity, quantity_remaining,
                    exit_phase, break_even_activated, strategy, order_list_id,
                ) = pos
                 
                try:
                    current_price = price_map.get(symbol)
                    if not current_price:
                        continue

                    regime, regime_conf = regime_map.get(symbol, ("UNKNOWN", 0.0))

                    position_data = {
                        "position_type": pos_type,
                        "entry_price": entry,
                        "stop_loss": sl,
                        "take_profit": tp,
                        "highest_price": highest or entry,
                        "quantity": quantity,
                        "quantity_remaining": quantity_remaining or quantity,
                        "exit_phase": exit_phase or "ACTIVE",
                        "break_even_activated": break_even_activated or False,
                    }

                    atr = atr_map.get(symbol, entry * 0.01)

                    decision = self.smart_exit.evaluate(
                        position_data, current_price, atr, 
                        regime, regime_conf
                    )

                    # Execute decision
                    if decision.action == "NONE":
                        # Just update highest price and maybe trail SL in DB
                        new_highest = max(highest or entry, current_price) if pos_type == "LONG" else min(highest or entry, current_price)
                         
                        # If trailing SL changed, we MUST update OCO on Binance
                        if decision.new_sl and decision.new_sl != trail_sl:
                            if not is_demo and order_list_id:
                                client = self.binance_manager._get_binance_client(user_id)
                                # Wrap blocking Binance API calls in asyncio.to_thread
                                await asyncio.to_thread(cancel_oco_order, client, symbol, order_list_id)
                                # Place new OCO
                                oco_side = "SELL" if pos_type == "LONG" else "BUY"
                                new_oco = await asyncio.to_thread(place_oco_order, client, symbol, oco_side, quantity_remaining, tp, decision.new_sl)
                                if new_oco:
                                    with get_db_write_connection() as conn:
                                        conn.execute(
                                            "UPDATE active_positions SET order_list_id = %s, stop_loss = %s, trailing_sl_price = %s, highest_price = %s WHERE id = %s",
                                            (new_oco.get("orderListId"), decision.new_sl, decision.new_sl, new_highest, pos_id)
                                        )
                                    logger.info(f"🔄 OCO Updated for {symbol}: New SL {decision.new_sl}")
                                else:
                                    logger.error(f"❌ Failed to update OCO for {symbol}")
                            else:
                                with get_db_write_connection() as conn:
                                    conn.execute(
                                        "UPDATE active_positions SET stop_loss = %s, trailing_sl_price = %s, highest_price = %s WHERE id = %s",
                                        (decision.new_sl, decision.new_sl, new_highest, pos_id)
                                    )
                        else:
                            with get_db_write_connection() as conn:
                                conn.execute(
                                    "UPDATE active_positions SET highest_price = %s WHERE id = %s",
                                    (new_highest, pos_id)
                                )
                        continue

                    elif decision.action == "UPDATE_SL":
                        # Similar to NONE but explicit SL update
                        new_highest = max(highest or entry, current_price) if pos_type == "LONG" else min(highest or entry, current_price)
                         
                        if not is_demo and order_list_id:
                             client = self.binance_manager._get_binance_client(user_id)
                             # Wrap blocking Binance API calls in asyncio.to_thread
                             await asyncio.to_thread(cancel_oco_order, client, symbol, order_list_id)
                             oco_side = "SELL" if pos_type == "LONG" else "BUY"
                             new_oco = await asyncio.to_thread(place_oco_order, client, symbol, oco_side, quantity_remaining, tp, decision.new_sl)
                             if new_oco:
                                 with get_db_write_connection() as conn:
                                     conn.execute(
                                         "UPDATE active_positions SET order_list_id = %s, stop_loss = %s, trailing_sl_price = %s, highest_price = %s, exit_phase = %s, break_even_activated = %s WHERE id = %s",
                                         (new_oco.get("orderListId"), decision.new_sl, decision.new_sl, new_highest, decision.new_phase or exit_phase, True if decision.new_phase == "BREAK_EVEN" else break_even_activated, pos_id)
                                     )
                                 logger.info(f"🛡️ SL Updated via OCO for {symbol}: New SL {decision.new_sl}")
                        else:
                            with get_db_write_connection() as conn:
                                conn.execute(
                                    "UPDATE active_positions SET stop_loss = %s, trailing_sl_price = %s, highest_price = %s, exit_phase = %s, break_even_activated = %s WHERE id = %s",
                                    (decision.new_sl, decision.new_sl, new_highest, decision.new_phase or exit_phase, True if decision.new_phase == "BREAK_EVEN" else break_even_activated, pos_id)
                                )

                    elif decision.action == "PARTIAL_CLOSE_50":
                        await self._execute_partial_close(
                            pos_id, user_id, symbol, pos_type, is_demo,
                            decision.close_quantity, decision.exit_price,
                            entry, decision.new_phase, strategy, regime, order_list_id
                        )

                    elif decision.action == "CLOSE_ALL":
                        await self._execute_full_close(
                            pos_id, user_id, symbol, pos_type, is_demo,
                            quantity_remaining or quantity, decision.exit_price,
                            decision.reason, entry, strategy, regime, order_list_id
                        )

                except Exception as e:
                    logger.warning(f"⚠️ Error monitoring {symbol}: {e}")

        except Exception as e:
            logger.error(f"❌ Error in monitor loop: {e}")

    def _analyze_market_for_symbols(self, symbols: list) -> tuple:
        """حساب ATR وتحليل نظام السوق (Regime) لكل العملات المفتوحة"""
        atr_map = {}
        regime_map = {}
        
        for symbol in symbols:
            try:
                klines = self.data_provider.client.get_klines(symbol=symbol, interval='1h', limit=50)
                if klines:
                    closes = [float(k[4]) for k in klines]
                    trs = []
                    for i in range(1, len(closes)):
                        high = float(klines[i][2])
                        low = float(klines[i][3])
                        prev_close = closes[i-1]
                        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                        trs.append(tr)
                    atr_map[symbol] = sum(trs[-14:]) / 14 if len(trs) >= 14 else sum(trs) / len(trs)

                    # Simple EMA(20) for Regime
                    ema_period = 20
                    multiplier = 2 / (ema_period + 1)
                    ema = closes[0]
                    for price in closes[1:]:
                        ema = (price - ema) * multiplier + ema
                    
                    current_price = closes[-1]
                    prev_price = closes[-5]
                    
                    if current_price > ema * 1.005 and ema > prev_price:
                        regime_map[symbol] = ("STRONG_TREND", 0.8)
                    elif current_price < ema * 0.995 and ema < prev_price:
                        regime_map[symbol] = ("STRONG_TREND", 0.8)
                    elif abs(current_price - ema) / ema < 0.01:
                        regime_map[symbol] = ("CHOPPY", 0.7)
                    else:
                        regime_map[symbol] = ("NARROW_RANGE", 0.6)

            except Exception as e:
                logger.debug(f"⚠️ Could not analyze {symbol}: {e}")
                atr_map[symbol] = 0.0
                regime_map[symbol] = ("UNKNOWN", 0.0)
                
        return atr_map, regime_map

    def _calculate_quantity(self, user_id: int, symbol: str, entry_price: float, settings: dict) -> float:
        trade_amount = settings.get("trade_amount", 100.0)
        position_size_pct = settings.get("position_size_percentage", 10.0) / 100.0
        budget = trade_amount * position_size_pct
        if budget <= 0 or entry_price <= 0: return 0.0
        raw_qty = budget / entry_price
        
        # Apply Filters
        try:
            client = self.binance_manager._get_binance_client(user_id)
            if client:
                filters = get_symbol_filters(client, symbol)
                lot_size = filters.get('LOT_SIZE', {})
                min_qty = float(lot_size.get('minQty', 0))
                step_size = lot_size.get('stepSize', '0.00000001')
                raw_qty = max(raw_qty, min_qty)
                raw_qty = round(raw_qty - (raw_qty % float(step_size)), 8)
        except Exception: pass
        return raw_qty if raw_qty > 0 else 0.0

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

    async def _execute_partial_close(self, pos_id, user_id, symbol, pos_type, is_demo, close_qty, exit_price, 
        entry_price, new_phase, strategy, regime, order_list_id
    ):
        logger.info(f"✂️ Partial Close: {symbol} qty={close_qty:.6f} @ {exit_price}")
         
        FEE_RATE = 0.001
        gross_pnl = (exit_price - entry_price) * close_qty if pos_type == "LONG" else (entry_price - exit_price) * close_qty
        fees = (entry_price * close_qty * FEE_RATE) + (exit_price * close_qty * FEE_RATE)
        net_pnl = gross_pnl - fees

        binance_success = True
        if not is_demo:
            try:
                client = self.binance_manager._get_binance_client(user_id)
                if client and close_qty > 0:
                    # Cancel old OCO first
                    if order_list_id:
                        await asyncio.to_thread(cancel_oco_order, client, symbol, order_list_id)
                     
                    # Wrap blocking Binance API call in asyncio.to_thread
                    await asyncio.to_thread(
                        client.create_order,
                        symbol=symbol,
                        side="SELL" if pos_type == "LONG" else "BUY",
                        type="MARKET",
                        quantity=close_qty,
                    )
            except Exception as e:
                logger.error(f"❌ Partial sell failed: {e}")
                binance_success = False

        if binance_success or is_demo:
            with get_db_write_connection() as conn:
                remaining_qty = conn.execute("SELECT quantity_remaining FROM active_positions WHERE id = %s", (pos_id,)).fetchone()[0]
                new_remaining = remaining_qty - close_qty
                 
                conn.execute(
                    """UPDATE active_positions
                       SET quantity_remaining = %s, quantity_closed = quantity_closed + %s,
                           exit_phase = %s, partial_close_1_price = %s, partial_close_1_pnl = %s
                       WHERE id = %s""",
                    (new_remaining, close_qty, new_phase, exit_price, net_pnl, pos_id)
                )

                # Place new OCO for the remaining quantity
                if not is_demo and order_list_id and new_remaining > 0:
                    try:
                        client = self.binance_manager._get_binance_client(user_id)
                        if client:
                            # Get current SL and TP from DB
                            pos_row = conn.execute(
                                "SELECT stop_loss, take_profit FROM active_positions WHERE id = %s",
                                (pos_id,)
                            ).fetchone()
                            if pos_row:
                                sl, tp = pos_row
                                oco_side = "SELL" if pos_type == "LONG" else "BUY"
                                # Wrap blocking Binance API call in asyncio.to_thread
                                new_oco = await asyncio.to_thread(place_oco_order, client, symbol, oco_side, new_remaining, tp, sl)
                                if new_oco:
                                    conn.execute(
                                        "UPDATE active_positions SET order_list_id = %s WHERE id = %s",
                                        (new_oco.get("orderListId"), pos_id)
                                    )
                                    logger.info(f"🛡️ New OCO placed for remaining {new_remaining:.6f} of {symbol}: ListID {new_oco.get('orderListId')}")
                                else:
                                    logger.error(f"❌ Failed to place OCO for remaining {symbol}")
                    except Exception as e:
                        logger.error(f"❌ Error placing OCO for remaining {symbol}: {e}")

            performance_tracker.record_trade({
                "symbol": symbol, "strategy": strategy, "type": pos_type,
                "entry_price": entry_price, "exit_price": exit_price,
                "quantity": close_qty, "pnl": net_pnl, "exit_reason": f"PARTIAL_CLOSE_{new_phase}",
                "is_demo": is_demo, "regime": regime
            })

    async def _execute_full_close(self, pos_id, user_id, symbol, pos_type, is_demo, quantity, exit_price, 
        reason, entry_price, strategy, regime, order_list_id
    ):
        logger.info(f"🚪 Full Close: {symbol} qty={quantity:.6f} @ {exit_price} (Reason: {reason})")
         
        binance_sell_ok = True
        if not is_demo:
            try:
                client = self.binance_manager._get_binance_client(user_id)
                if client and quantity > 0:
                    # Cancel OCO
                    if order_list_id:
                        await asyncio.to_thread(cancel_oco_order, client, symbol, order_list_id)
                     
                    # Wrap blocking Binance API call in asyncio.to_thread
                    await asyncio.to_thread(
                        client.create_order,
                        symbol=symbol,
                        side="SELL" if pos_type == "LONG" else "BUY",
                        type="MARKET",
                        quantity=quantity,
                    )
            except Exception as e:
                logger.error(f"❌ Full sell failed: {e}")
                binance_sell_ok = False

        if binance_sell_ok or is_demo:
            FEE_RATE = 0.001
            gross_pnl = (exit_price - entry_price) * quantity if pos_type == "LONG" else (entry_price - exit_price) * quantity
            fees = (entry_price * quantity * FEE_RATE) + (exit_price * quantity * FEE_RATE)
            net_pnl = gross_pnl - fees
            pnl_pct = (net_pnl / (entry_price * quantity) * 100) if entry_price > 0 else 0

            with get_db_write_connection() as conn:
                conn.execute(
                    """UPDATE active_positions
                       SET is_active = FALSE, exit_price = %s, exit_reason = %s,
                           profit_loss = %s, profit_pct = %s, closed_at = NOW()
                       WHERE id = %s""",
                    (exit_price, reason, net_pnl, pnl_pct, pos_id),
                )
                conn.execute(
                    """UPDATE portfolio
                       SET total_balance = total_balance + %s, available_balance = available_balance + %s
                       WHERE user_id = %s AND is_demo = %s""",
                    (net_pnl, net_pnl, user_id, is_demo),
                )
            logger.info(f"✅ Position {pos_id} closed in DB: {symbol} PnL={net_pnl:.2f}")
             
            performance_tracker.record_trade({
                "symbol": symbol, "strategy": strategy, "type": pos_type,
                "entry_price": entry_price, "exit_price": exit_price,
                "quantity": quantity, "pnl": net_pnl, "exit_reason": reason,
                "is_demo": is_demo, "regime": regime
            })
        else:
            logger.warning(f"⏸️ Position {pos_id} ({symbol}) NOT closed in DB")


if __name__ == "__main__":
    worker = ExecutorWorker()
    asyncio.run(worker.run())
