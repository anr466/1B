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
from backend.utils.indicator_calculator import compute_atr
from backend.core.smart_performance_tracker import performance_tracker

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
                           trailing_sl_price, highest_price, is_demo, quantity, position_size,
                           quantity_remaining, exit_phase, break_even_activated, strategy
                    FROM active_positions WHERE is_active = TRUE
                """).fetchall()

            if not positions:
                return

            symbols = list(set(pos[2] for pos in positions))

            # FIX 3: Use cached prices when fetch fails
            price_map = self._refresh_price_cache(symbols)
            if not price_map:
                price_map = {
                    sym: self._get_cached_price(sym)
                    for sym in symbols
                    if self._get_cached_price(sym) > 0
                }
                if not price_map:
                    logger.error("❌ No prices available — skipping monitoring")
                    return

            # FIX 1: Calculate real ATR and Regime for each symbol
            atr_map, regime_map = self._analyze_market_for_symbols(symbols)

            for pos in positions:
                (
                    pos_id, user_id, symbol, pos_type, entry, sl, tp,
                    trail_sl, highest, is_demo, quantity, position_size,
                    quantity_remaining, exit_phase, break_even_activated, strategy,
                ) = pos
                
                try:
                    current_price = price_map.get(symbol)
                    if not current_price:
                        continue

                    # FIX 3: Use the dynamically determined regime
                    regime, regime_conf = regime_map.get(symbol, ("UNKNOWN", 0.0))

                    # Prepare position dict for Smart Exit Engine
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

                    # Get real ATR
                    atr = atr_map.get(symbol, entry * 0.01)

                    # Evaluate with Smart Exit Engine
                    decision = self.smart_exit.evaluate(
                        position_data, current_price, atr, 
                        regime, regime_conf
                    )

                    # Execute decision
                    if decision.action == "NONE":
                        new_highest = max(highest or entry, current_price) if pos_type == "LONG" else min(highest or entry, current_price)
                        with get_db_write_connection() as conn:
                            conn.execute(
                                """
                                UPDATE active_positions
                                SET trailing_sl_price = %s, highest_price = %s
                                WHERE id = %s AND is_active = TRUE
                                """,
                                (decision.new_sl or trail_sl, new_highest, pos_id),
                            )
                        continue

                    elif decision.action == "UPDATE_SL":
                        new_highest = max(highest or entry, current_price) if pos_type == "LONG" else min(highest or entry, current_price)
                        with get_db_write_connection() as conn:
                            conn.execute(
                                """
                                UPDATE active_positions
                                SET stop_loss = %s, trailing_sl_price = %s, highest_price = %s,
                                    exit_phase = %s, break_even_activated = %s
                                WHERE id = %s AND is_active = TRUE
                                """,
                                (
                                    decision.new_sl,
                                    decision.new_sl,
                                    new_highest,
                                    decision.new_phase or exit_phase,
                                    True if decision.new_phase == "BREAK_EVEN" else break_even_activated,
                                    pos_id,
                                ),
                            )
                        logger.info(f"🛡️ {decision.reason} for {symbol} (New SL: {decision.new_sl})")

                    elif decision.action == "PARTIAL_CLOSE_50":
                        await self._execute_partial_close(
                            pos_id, user_id, symbol, pos_type, is_demo,
                            decision.close_quantity, decision.exit_price,
                            entry, decision.new_phase, strategy, regime
                        )

                    elif decision.action == "CLOSE_ALL":
                        await self._execute_full_close(
                            pos_id, user_id, symbol, pos_type, is_demo,
                            quantity_remaining or quantity, decision.exit_price,
                            decision.reason, entry, strategy, regime
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
                # Fetch last 50 1h candles for better analysis
                klines = self.data_provider.client.get_klines(symbol=symbol, interval='1h', limit=50)
                if klines:
                    closes = [float(k[4]) for k in klines]
                    highs = [float(k[2]) for k in klines]
                    lows = [float(k[3]) for k in klines]
                    
                    # 1. Calculate ATR (Average True Range)
                    trs = []
                    for i in range(1, len(closes)):
                        high = highs[i]
                        low = lows[i]
                        prev_close = closes[i-1]
                        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
                        trs.append(tr)
                    atr_map[symbol] = sum(trs[-14:]) / 14 if len(trs) >= 14 else sum(trs) / len(trs)

                    # 2. Determine Regime using EMA(20)
                    # Simple EMA calculation
                    ema_period = 20
                    multiplier = 2 / (ema_period + 1)
                    ema = closes[0]
                    for price in closes[1:]:
                        ema = (price - ema) * multiplier + ema
                    
                    current_price = closes[-1]
                    prev_price = closes[-5] # Price 5 hours ago
                    
                    # Logic:
                    # If Price > EMA and EMA is rising -> STRONG_TREND (Up)
                    # If Price < EMA and EMA is falling -> STRONG_TREND (Down)
                    # Otherwise -> CHOPPY / RANGE
                    
                    # For Exit Engine, we care if the trend is *favorable* for the position
                    # But here we return the absolute market regime
                    if current_price > ema * 1.005 and ema > prev_price:
                        regime_map[symbol] = ("STRONG_TREND", 0.8)
                    elif current_price < ema * 0.995 and ema < prev_price:
                        regime_map[symbol] = ("STRONG_TREND", 0.8) # Strong trend, just down
                    elif abs(current_price - ema) / ema < 0.01:
                        regime_map[symbol] = ("CHOPPY", 0.7)
                    else:
                        regime_map[symbol] = ("NARROW_RANGE", 0.6)

            except Exception as e:
                logger.debug(f"⚠️ Could not analyze {symbol}: {e}")
                atr_map[symbol] = 0.0
                regime_map[symbol] = ("UNKNOWN", 0.0)
                
        return atr_map, regime_map

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

    async def _execute_partial_close(
        self, pos_id, user_id, symbol, pos_type, is_demo, close_qty, exit_price, 
        entry_price, new_phase, strategy, regime
    ):
        """تنفيذ إغلاق جزئي للصفقة مع التعلم الذكي"""
        logger.info(
            f"✂️ Partial Close: {symbol} qty={close_qty:.6f} @ {exit_price} (Phase: {new_phase})"
        )
        
        # FIX: حساب الربح الصافي بعد خصم الرسوم (0.1% للدخول + 0.1% للخروج)
        FEE_RATE = 0.001
        gross_pnl = (exit_price - entry_price) * close_qty if pos_type == "LONG" else (entry_price - exit_price) * close_qty
        fees = (entry_price * close_qty * FEE_RATE) + (exit_price * close_qty * FEE_RATE)
        net_pnl = gross_pnl - fees

        if not is_demo:
            try:
                client = self.binance_manager._get_binance_client(user_id)
                if client and close_qty and close_qty > 0:
                    client.create_order(
                        symbol=symbol,
                        side="SELL" if pos_type == "LONG" else "BUY",
                        type="MARKET",
                        quantity=close_qty,
                    )
                    logger.info(f"📤 Binance partial sell executed for {symbol}")
                else:
                    logger.error(f"❌ Cannot partial sell {symbol}: invalid quantity")
                    return
            except Exception as sell_err:
                logger.error(f"❌ Binance partial sell failed for {symbol}: {sell_err}")
                return

        # FIX: تحديث قاعدة البيانات بالربح الصافي
        with get_db_write_connection() as conn:
            conn.execute(
                """
                UPDATE active_positions
                SET quantity_remaining = quantity_remaining - %s,
                    quantity_closed = quantity_closed + %s,
                    exit_phase = %s,
                    partial_close_1_price = %s,
                    partial_close_1_pnl = %s
                WHERE id = %s AND is_active = TRUE
                """,
                (close_qty, close_qty, new_phase, exit_price, net_pnl, pos_id),
            )

        # FIX: تسجيل التجربة للتعلم الذكي
        performance_tracker.record_trade({
            "symbol": symbol,
            "strategy": strategy,
            "type": pos_type,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": close_qty,
            "pnl": net_pnl,
            "exit_reason": f"PARTIAL_CLOSE_{new_phase}",
            "is_demo": is_demo,
            "regime": regime
        })

    async def _execute_full_close(
        self, pos_id, user_id, symbol, pos_type, is_demo, quantity, exit_price, 
        reason, entry_price, strategy, regime
    ):
        """تنفيذ إغلاق كامل للصفقة مع التعلم الذكي"""
        logger.info(
            f"🚪 Full Close: {symbol} qty={quantity:.6f} @ {exit_price} (Reason: {reason})"
        )
        
        binance_sell_ok = True
        if not is_demo:
            try:
                client = self.binance_manager._get_binance_client(user_id)
                if client and quantity and quantity > 0:
                    client.create_order(
                        symbol=symbol,
                        side="SELL" if pos_type == "LONG" else "BUY",
                        type="MARKET",
                        quantity=quantity,
                    )
                    logger.info(f"📤 Binance full sell executed for {symbol}")
                else:
                    logger.error(f"❌ Cannot full sell {symbol}: invalid quantity")
                    binance_sell_ok = False
            except Exception as sell_err:
                logger.error(f"❌ Binance full sell failed for {symbol}: {sell_err}")
                binance_sell_ok = False

        if binance_sell_ok or is_demo:
            # FIX: حساب الربح الصافي بعد الرسوم
            FEE_RATE = 0.001
            gross_pnl = (exit_price - entry_price) * quantity if pos_type == "LONG" else (entry_price - exit_price) * quantity
            fees = (entry_price * quantity * FEE_RATE) + (exit_price * quantity * FEE_RATE)
            net_pnl = gross_pnl - fees
            pnl_pct = (net_pnl / (entry_price * quantity) * 100) if entry_price > 0 else 0

            with get_db_write_connection() as conn:
                conn.execute(
                    """
                    UPDATE active_positions
                    SET is_active = FALSE, exit_price = %s, exit_reason = %s,
                        profit_loss = %s, profit_pct = %s, closed_at = NOW()
                    WHERE id = %s
                    """,
                    (exit_price, reason, net_pnl, pnl_pct, pos_id),
                )

                conn.execute(
                    """
                    UPDATE portfolio
                    SET total_balance = total_balance + %s,
                        available_balance = available_balance + %s
                    WHERE user_id = %s AND is_demo = %s
                    """,
                    (net_pnl, net_pnl, user_id, is_demo),
                )

            logger.info(f"✅ Position {pos_id} closed in DB: {symbol} PnL={net_pnl:.2f}")

            # FIX: تسجيل التجربة للتعلم الذكي
            performance_tracker.record_trade({
                "symbol": symbol,
                "strategy": strategy,
                "type": pos_type,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "quantity": quantity,
                "pnl": net_pnl,
                "exit_reason": reason,
                "is_demo": is_demo,
                "regime": regime
            })
        else:
            logger.warning(f"⏸️ Position {pos_id} ({symbol}) NOT closed in DB — Binance sell failed")


if __name__ == "__main__":
    worker = ExecutorWorker()
    asyncio.run(worker.run())
