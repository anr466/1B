"""
Database Trading Mixin — extracted from database_manager.py (God Object split)
===============================================================================
Methods: successful coins, active positions, signals, GroupB position management
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


class DbTradingMixin:
    """Trading-related database methods (coins, positions, signals)"""

    # ==================== العملات الناجحة ====================

    def save_successful_coins(self, coins_data):
        """حفظ العملات الناجحة مع الحفاظ على حد أقصى ثابت (25 عملة) - توازن بين التنويع والأداء"""
        normalized_new = self._normalize_coins_data(coins_data)

        if not normalized_new:
            self.logger.warning("لا توجد بيانات عملات للحفظ بعد التطبيع")
            return

        MAX_COINS = 50

        with self.get_write_connection() as conn:
            existing_rows = conn.execute("""
                SELECT symbol, score FROM successful_coins 
                WHERE is_active = TRUE
                ORDER BY score DESC
            """).fetchall()

            existing_symbols = {row[0]: row[1] for row in existing_rows}

            all_coins = {}
            for row in existing_rows:
                all_coins[row[0]] = {"score": row[1], "source": "existing"}

            for coin in normalized_new:
                symbol = coin["symbol"]
                score = coin.get("score", 0)
                all_coins[symbol] = {"score": score, "source": "new", "data": coin}

            sorted_coins = sorted(
                all_coins.items(), key=lambda x: x[1]["score"], reverse=True
            )
            top_coins = sorted_coins[:MAX_COINS]
            removed_coins = sorted_coins[MAX_COINS:]

            if removed_coins:
                removed_symbols = [c[0] for c in removed_coins]
                placeholders = ",".join(["%s" for _ in removed_symbols])
                conn.execute(
                    f"""
                    UPDATE successful_coins SET is_active = FALSE 
                    WHERE symbol IN ({placeholders})
                """,
                    removed_symbols,
                )
                self.logger.info(f"🔄 تم إلغاء تفعيل {len(removed_symbols)} عملة ضعيفة")

            for symbol, info in top_coins:
                if info["source"] == "new":
                    coin_data = info["data"]
                    self._insert_coin_data_direct(conn, coin_data)

            self.logger.info(
                f"✅ تم حفظ {len(top_coins)} عملة (الحد الأقصى: {MAX_COINS})"
            )

            self._cleanup_old_records(conn)

    def _insert_coin_data(self, conn, symbol, data):
        """إدراج بيانات عملة واحدة في قاعدة البيانات"""
        try:
            score = float(data.get("score", 0))
            profit_pct = float(data.get("profit_pct", 0))
            win_rate = float(data.get("win_rate", 0))
            total_trades = int(data.get("total_trades", 0))

            conn.execute(
                """
                INSERT OR REPLACE INTO successful_coins 
                (symbol, strategy, timeframe, score, profit_pct, win_rate, 
                 total_trades, market_trend, analysis_date, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            """,
                (
                    str(symbol),
                    str(data.get("strategy", "unknown")),
                    str(data.get("timeframe", "1h")),
                    score,
                    profit_pct,
                    win_rate,
                    total_trades,
                    str(data.get("market_trend", "neutral")),
                    str(data.get("analysis_date", datetime.now().isoformat())),
                ),
            )
        except (ValueError, TypeError) as e:
            self.logger.warning(f"تخطي العملة {symbol} بسبب خطأ في البيانات: {e}")

    def _normalize_coins_data(self, coins_data):
        """تطبيع بيانات العملات إلى تنسيق موحد"""
        normalized = []

        try:
            if isinstance(coins_data, dict):
                for symbol, data in coins_data.items():
                    if isinstance(data, dict):
                        normalized.append(self._normalize_single_coin(symbol, data))
            elif isinstance(coins_data, list):
                for item in coins_data:
                    if isinstance(item, dict):
                        symbol = item.get("symbol", "UNKNOWN")
                        normalized.append(self._normalize_single_coin(symbol, item))

            return normalized
        except Exception as e:
            self.logger.error(f"خطأ في تطبيع بيانات العملات: {e}")
            return []

    def _normalize_single_coin(self, symbol, data):
        """تطبيع بيانات عملة واحدة"""
        return {
            "symbol": str(symbol),
            "strategy": str(data.get("strategy", "unknown")),
            "timeframe": str(data.get("timeframe", "1h")),
            "score": float(data.get("score", 0)),
            "profit_pct": float(data.get("profit_pct", 0)),
            "win_rate": float(data.get("win_rate", 0)),
            "total_trades": int(data.get("total_trades", 0)),
            "market_trend": str(data.get("market_trend", "neutral")),
            "analysis_date": str(data.get("analysis_date", datetime.now().isoformat())),
            "avg_trade_duration_hours": float(
                data.get("avg_trade_duration_hours", 0.0)
            ),
            "trading_style": str(data.get("trading_style", "swing")),
        }

    def _insert_coin_data_direct(self, conn, coin_data):
        """إدراج بيانات عملة مطبعة مباشرة في قاعدة البيانات"""
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO successful_coins 
                (symbol, strategy, timeframe, score, profit_pct, win_rate, 
                 total_trades, market_trend, analysis_date, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            """,
                (
                    coin_data["symbol"],
                    coin_data["strategy"],
                    coin_data["timeframe"],
                    coin_data["score"],
                    coin_data["profit_pct"],
                    coin_data["win_rate"],
                    coin_data["total_trades"],
                    coin_data["market_trend"],
                    coin_data["analysis_date"],
                ),
            )
        except Exception as e:
            self.logger.warning(
                f"تخطي العملة {coin_data.get('symbol', 'UNKNOWN')} بسبب خطأ في الإدراج: {e}"
            )

    def get_successful_coins(self) -> List[Dict[str, Any]]:
        """الحصول على العملات الناجحة الحالية"""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT symbol, strategy, timeframe, score, profit_pct, win_rate,
                       total_trades, market_trend, analysis_date, is_active
                FROM successful_coins 
                WHERE is_active = TRUE 
                ORDER BY score DESC
            """).fetchall()

            result = []
            for row in rows:
                result.append(
                    {
                        "symbol": row["symbol"],
                        "strategy": row["strategy"],
                        "timeframe": row["timeframe"],
                        "score": row["score"],
                        "profit_pct": row["profit_pct"],
                        "win_rate": row["win_rate"],
                        "total_trades": row["total_trades"],
                        "market_trend": row["market_trend"],
                        "analysis_date": row["analysis_date"],
                        "is_active": row["is_active"],
                    }
                )

            return result

    def _cleanup_old_records(self, conn):
        """تنظيف السجلات القديمة من الجداول الأخرى للاحتفاظ بسجل واحد فقط"""
        try:
            try:
                conn.execute("""
                    DELETE FROM successful_coins 
                    WHERE is_active = FALSE 
                    AND datetime(analysis_date) < datetime('now', '-7 days')
                """)
            except Exception as e:
                self.logger.debug(f"ملاحظة في تنظيف successful_coins: {e}")

            try:
                conn.execute("""
                    DELETE FROM trading_signals 
                    WHERE is_processed = TRUE 
                    AND datetime(generated_at) < datetime('now', '-3 days')
                """)
            except Exception as e:
                self.logger.debug(f"ملاحظة في تنظيف trading_signals: {e}")

            try:
                conn.execute("""
                    DELETE FROM active_positions 
                    WHERE is_active = FALSE 
                    AND datetime(updated_at) < datetime('now', '-30 days')
                """)
            except Exception as e:
                self.logger.debug(f"ملاحظة في تنظيف active_positions: {e}")

            try:
                conn.execute("""
                    DELETE FROM activity_logs 
                    WHERE datetime(created_at) < datetime('now', '-30 days')
                """)
            except Exception as e:
                self.logger.debug(f"ملاحظة في تنظيف activity_logs: {e}")

        except Exception as e:
            self.logger.debug(f"ملاحظة في تنظيف السجلات القديمة: {e}")

    # ==================== إدارة الصفقات المفتوحة ====================

    def register_active_position(
        self,
        user_id: int,
        symbol: str,
        strategy: str,
        timeframe: str,
        position_type: str,
        entry_price: float = None,
        quantity: float = None,
        stop_loss: float = None,
        take_profit: float = None,
        trailing_sl_price: float = None,
        signal_metadata: str = None,
    ):
        """تسجيل صفقة مفتوحة جديدة"""
        try:
            with self.get_write_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO active_positions 
                    (user_id, symbol, strategy, timeframe, position_type, entry_date,
                     entry_price, quantity, stop_loss, take_profit, trailing_sl_price,
                     is_active, created_at, updated_at, signal_metadata)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s, %s, TRUE, 
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, %s)
                """,
                    (
                        user_id,
                        symbol,
                        strategy,
                        timeframe,
                        position_type,
                        entry_price,
                        quantity,
                        stop_loss,
                        take_profit,
                        trailing_sl_price,
                        signal_metadata,
                    ),
                )

                self.logger.info(
                    f"تم تسجيل صفقة مفتوحة: {symbol} ({strategy}/{timeframe})"
                )

        except Exception as e:
            self.logger.error(f"خطأ في تسجيل الصفقة المفتوحة: {e}")

    def close_active_position(self, user_id: int, symbol: str, strategy: str = None):
        """إغلاق صفقة مفتوحة"""
        try:
            with self.get_write_connection() as conn:
                if strategy:
                    conn.execute(
                        """
                        UPDATE active_positions 
                        SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND symbol = %s AND strategy = %s AND is_active = TRUE
                    """,
                        (user_id, symbol, strategy),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE active_positions 
                        SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s AND symbol = %s AND is_active = TRUE
                    """,
                        (user_id, symbol),
                    )

                self.logger.info(f"تم إغلاق الصفقة: {symbol}")

        except Exception as e:
            self.logger.error(f"خطأ في إغلاق الصفقة: {e}")

    def update_position_trailing_sl(
        self, user_id: int, symbol: str, trailing_sl_price: float, strategy: str = None
    ):
        """تحديث Trailing Stop Loss لصفقة مفتوحة"""
        try:
            with self.get_write_connection() as conn:
                if strategy:
                    conn.execute(
                        """
                        UPDATE active_positions 
                        SET trailing_sl_price = %s, updated_at = %s
                        WHERE user_id = %s AND symbol = %s AND strategy = %s AND is_active = TRUE
                    """,
                        (
                            trailing_sl_price,
                            datetime.now().isoformat(),
                            user_id,
                            symbol,
                            strategy,
                        ),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE active_positions 
                        SET trailing_sl_price = %s, updated_at = %s
                        WHERE user_id = %s AND symbol = %s AND is_active = TRUE
                    """,
                        (
                            trailing_sl_price,
                            datetime.now().isoformat(),
                            user_id,
                            symbol,
                        ),
                    )

        except Exception as e:
            self.logger.error(f"خطأ في تحديث Trailing SL: {e}")

    def get_active_positions_for_user(
        self, user_id: int, is_demo: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """الحصول على جميع الصفقات المفتوحة للمستخدم مع trailing_sl_price"""
        try:
            with self.get_connection() as conn:
                if is_demo is None:
                    rows = conn.execute(
                        """
                        SELECT * FROM active_positions 
                        WHERE user_id = %s AND is_active = TRUE
                        ORDER BY created_at DESC
                    """,
                        (user_id,),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT * FROM active_positions 
                        WHERE user_id = %s AND is_demo = %s AND is_active = TRUE
                        ORDER BY created_at DESC
                    """,
                        (user_id, is_demo),
                    ).fetchall()

                return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"خطأ في جلب الصفقات المفتوحة: {e}")
            return []

    def get_active_positions(
        self, user_id: int, is_demo: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """الحصول على جميع الصفقات المفتوحة للمستخدم"""
        try:
            with self.get_connection() as conn:
                if is_demo is None:
                    rows = conn.execute(
                        """
                        SELECT * FROM active_positions 
                        WHERE user_id = %s AND is_active = TRUE
                        ORDER BY created_at DESC
                    """,
                        (user_id,),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT * FROM active_positions 
                        WHERE user_id = %s AND is_demo = %s AND is_active = TRUE
                        ORDER BY created_at DESC
                    """,
                        (user_id, is_demo),
                    ).fetchall()

                return [dict(row) for row in rows]

        except Exception as e:
            self.logger.error(f"خطأ في جلب الصفقات المفتوحة: {e}")
            return []

    def get_user_trades_paginated(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        status: str = "all",
        date_from: str = None,
        date_to: str = None,
        is_demo: Optional[int] = None,
    ) -> Dict[str, Any]:
        """جلب صفقات المستخدم مع Pagination — يقرأ من active_positions (المصدر الوحيد للبيانات)"""
        try:
            limit = min(limit, 200)

            with self.get_connection() as conn:
                where_clauses = ["user_id = %s"]
                params = [user_id]

                if is_demo is not None:
                    # Convert to boolean if passed as int (0/1) for DB compatibility
                    is_demo_bool = (
                        bool(is_demo) if isinstance(is_demo, (int, bool)) else is_demo
                    )
                    where_clauses.append("is_demo = %s")
                    params.append(is_demo_bool)

                if status == "open":
                    where_clauses.append("is_active = TRUE")
                elif status == "closed":
                    where_clauses.append("is_active = FALSE")

                if date_from:
                    where_clauses.append("COALESCE(entry_date, created_at::text) >= %s")
                    params.append(date_from)

                if date_to:
                    where_clauses.append("COALESCE(entry_date, created_at::text) <= %s")
                    params.append(date_to)

                where_sql = " AND ".join(where_clauses)

                count_query = f"SELECT COUNT(*) FROM active_positions WHERE {where_sql}"
                total = conn.execute(count_query, params).fetchone()[0]

                query = f"""
                    SELECT
                        id, user_id, symbol, strategy, is_demo,
                        entry_price, exit_price, quantity,
                        profit_loss,
                        profit_pct AS profit_loss_percentage,
                        CASE WHEN is_active = TRUE THEN 'open' ELSE 'closed' END AS status,
                        COALESCE(entry_date, created_at::text) AS entry_time,
                        closed_at AS exit_time,
                        CASE WHEN position_type IN ('long', 'LONG') THEN 'buy' ELSE 'sell' END AS side,
                        stop_loss, take_profit, timeframe,
                        exit_reason, ml_confidence,
                        created_at, updated_at
                    FROM active_positions
                    WHERE {where_sql}
                    ORDER BY COALESCE(entry_date, created_at::text) DESC
                    LIMIT %s OFFSET %s
                """
                params.extend([limit, offset])

                trades = conn.execute(query, params).fetchall()

                self.logger.debug(
                    f"✅ Pagination: {len(trades)} trades (total: {total}, offset: {offset})"
                )

                return {"trades": [dict(trade) for trade in trades], "total": total}

        except Exception as e:
            self.logger.error(f"خطأ في get_user_trades_paginated: {e}")
            return {"trades": [], "total": 0}

    def get_coins_for_monitoring(
        self, user_id: int, is_demo: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """الحصول على قائمة العملات للمراقبة (ناجحة + صفقات مفتوحة)"""
        try:
            successful_coins = self.get_successful_coins()
            active_positions = self.get_active_positions(user_id, is_demo=is_demo)

            all_symbols = {coin["symbol"]: coin for coin in successful_coins}

            for pos in active_positions:
                symbol = pos["symbol"]
                if symbol not in all_symbols:
                    all_symbols[symbol] = {
                        "symbol": symbol,
                        "strategy": pos["strategy"],
                        "timeframe": pos["timeframe"],
                        "profit_pct": 0.0,
                        "win_rate": 0.0,
                        "total_trades": 0,
                        "score": 0.0,
                        "market_trend": "neutral",
                        "analysis_date": pos["created_at"],
                        "is_active": True,
                        "source": "active_position",
                    }
                else:
                    all_symbols[symbol]["has_active_position"] = True
                    all_symbols[symbol]["original_strategy"] = pos["strategy"]
                    all_symbols[symbol]["original_timeframe"] = pos["timeframe"]
                    all_symbols[symbol]["position_entry_date"] = pos["created_at"]
                    all_symbols[symbol]["active_strategy"] = pos["strategy"]
                    all_symbols[symbol]["active_timeframe"] = pos["timeframe"]

            result = list(all_symbols.values())

            self.logger.info(
                f"📊 قائمة المراقبة للمستخدم {user_id}: {len(result)} عملة "
                f"({len(successful_coins)} ناجحة + {len(active_positions)} صفقة مفتوحة)"
            )

            return result

        except Exception as e:
            self.logger.error(f"خطأ في إنشاء قائمة المراقبة: {e}")
            return self.get_successful_coins()

    def cleanup_old_positions(self, days: int = 30):
        """تنظيف الصفقات المغلقة القديمة"""
        try:
            with self.get_write_connection() as conn:
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

                result = conn.execute(
                    """
                    DELETE FROM active_positions 
                    WHERE is_active = FALSE AND updated_at < %s
                """,
                    (cutoff_date,),
                )

                deleted_count = result.rowcount
                if deleted_count > 0:
                    self.logger.info(f"🧹 تم حذف {deleted_count} صفقة مغلقة قديمة")

        except Exception as e:
            self.logger.error(f"خطأ في تنظيف الصفقات القديمة: {e}")

    # ==================== الإشارات الحالية ====================

    def save_current_signals(self, signals: List[Dict[str, Any]]):
        """حفظ الإشارات الحالية من المجموعة B"""
        with self.get_write_connection() as conn:
            for signal in signals:
                confidence = signal.get("confidence", 0.0)
                try:
                    confidence = float(confidence or 0.0)
                except (TypeError, ValueError):
                    confidence = 0.0

                if confidence > 1.0:
                    confidence = confidence / 100.0

                confidence = max(0.0, min(confidence, 1.0))
                is_processed = bool(signal.get("is_processed", True))

                conn.execute(
                    """
                    INSERT OR REPLACE INTO trading_signals 
                    (symbol, strategy, timeframe, signal_type, price, confidence, generated_at, is_processed)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                """,
                    (
                        signal["symbol"],
                        signal["strategy"],
                        signal["timeframe"],
                        signal["signal_type"],
                        signal["price"],
                        confidence,
                        bool(is_processed),
                    ),
                )

        self.logger.info(f"تم حفظ {len(signals)} إشارة")

    def get_unprocessed_signals(self, user_id: int) -> List[Dict[str, Any]]:
        """الحصول على الإشارات غير المعالجة لمستخدم معين"""
        with self.get_connection() as conn:
            settings = conn.execute(
                """
                SELECT trading_enabled, max_positions FROM user_settings WHERE user_id = %s
            """,
                (user_id,),
            ).fetchone()

            if not settings or not settings["trading_enabled"]:
                return []

            active_trades = conn.execute(
                """
                SELECT COUNT(*) as count FROM active_positions
                WHERE user_id = %s AND is_active = TRUE
            """,
                (user_id,),
            ).fetchone()["count"]

            if active_trades >= settings["max_positions"]:
                return []

            rows = conn.execute("""
                SELECT * FROM trading_signals 
                WHERE is_processed = FALSE 
                ORDER BY generated_at DESC
            """).fetchall()

            return [dict(row) for row in rows]

    def mark_signal_processed(self, signal_id: int):
        """تحديد إشارة كمعالجة"""
        with self.get_write_connection() as conn:
            conn.execute(
                """
                UPDATE trading_signals SET is_processed = TRUE WHERE id = %s
            """,
                (signal_id,),
            )

    def cleanup_orphaned_signals(self, max_age_hours: int = 24) -> int:
        """تنظيف الإشارات القديمة غير المعالجة

        يقوم بتحديد الإشارات الأقدم من max_age_hours كمعالجة لمنع تراكمها.
        هذا يمنع الإشارات المعلقة من التأثير على أداء النظام.

        Args:
            max_age_hours: عمر الإشارة بالساعات قبل اعتبارها منتهية

        Returns:
            عدد الإشارات التي تم تنظيفها
        """
        try:
            with self.get_write_connection() as conn:
                result = conn.execute(
                    """
                    UPDATE trading_signals 
                    SET is_processed = TRUE 
                    WHERE is_processed = FALSE 
                    AND generated_at < NOW() - INTERVAL '%s hours'
                    """,
                    (max_age_hours,),
                )
                cleaned = result.rowcount if hasattr(result, "rowcount") else 0
                if cleaned > 0:
                    self.logger.info(
                        f"✅ Cleaned up {cleaned} orphaned signals older than {max_age_hours}h"
                    )
                return cleaned
        except Exception as e:
            self.logger.error(f"❌ Error cleaning up orphaned signals: {e}")
            return 0

    # ==================== دوال GroupBSystem ====================

    def get_user_active_positions(
        self, user_id: int, is_demo: bool = None
    ) -> List[Dict[str, Any]]:
        """جلب الصفقات المفتوحة للمستخدم حسب الوضع"""
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT * FROM active_positions 
                    WHERE user_id = %s AND is_active = TRUE
                """
                params = [user_id]

                if is_demo is not None:
                    query += " AND is_demo = %s"
                    # Convert to boolean for PostgreSQL (which stores is_demo as BOOLEAN)
                    params.append(bool(is_demo))

                query += " ORDER BY created_at DESC"

                rows = conn.execute(query, params).fetchall()

                return [dict(row) for row in rows] if rows else []
        except Exception as e:
            self.logger.error(f"خطأ في جلب الصفقات المفتوحة: {e}")
            return []

    def add_position_on_conn(
        self,
        conn,
        user_id: int,
        symbol: str,
        entry_price: float,
        quantity: float,
        position_size: float,
        signal_type: str,
        is_demo: bool = True,
        order_id: str = None,
        position_type: str = "long",
        stop_loss_price: float = None,
        take_profit_price: float = None,
        timeframe: str = "1h",
        signal_metadata: str = None,
        entry_commission: float = None,
    ) -> Optional[int]:
        """إضافة صفقة جديدة على اتصال كتابة خارجي (للمعاملات الذرية)."""
        if stop_loss_price is None:
            if position_type == "short":
                stop_loss_price = entry_price * 1.01
            else:
                stop_loss_price = entry_price * 0.99

        # V7/V8 trailing-only: لا نضع TP افتراضي إذا لم يُرسل
        if take_profit_price is None:
            take_profit_price = 0

        if entry_commission is None:
            entry_commission = position_size * 0.001 if bool(is_demo) else 0

        try:
            cursor = conn.execute(
                """
                INSERT INTO active_positions
                (user_id, symbol, entry_price, quantity, strategy,
                 stop_loss, take_profit, is_demo, order_id, entry_commission,
                 position_size, position_type, timeframe, entry_date,
                 is_active, created_at, highest_price, signal_metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, TRUE, CURRENT_TIMESTAMP, %s, %s)
                RETURNING id
            """,
                (
                    user_id,
                    symbol,
                    entry_price,
                    quantity,
                    signal_type,
                    stop_loss_price,
                    take_profit_price,
                    bool(is_demo),
                    order_id,
                    entry_commission,
                    position_size,
                    position_type,
                    timeframe,
                    0,
                    signal_metadata,
                ),
            )
        except Exception as _integrity_err:
            if (
                "unique" not in str(_integrity_err).lower()
                and "duplicate" not in str(_integrity_err).lower()
            ):
                raise
            self.logger.warning(
                f"⚠️ Skipped duplicate open position: {symbol} user={user_id} "
                f"strategy={signal_type} is_demo={is_demo} (UNIQUE constraint)"
            )
            return None

        self.logger.info(
            f"تم فتح صفقة {position_type.upper()}: {symbol} للمستخدم {user_id}"
        )
        try:
            row = cursor.fetchone()
            if row is None:
                self.logger.error(f"❌ RETURNING id returned None for {symbol}")
                return None
            if not hasattr(row, "__len__") or len(row) < 1:
                self.logger.error(f"❌ RETURNING id returned invalid row: {row}")
                return None
            return row[0]
        except Exception as e:
            self.logger.error(f"❌ Error fetching RETURNING id: {e}")
            raise

    def add_position(
        self,
        user_id: int,
        symbol: str,
        entry_price: float,
        quantity: float,
        position_size: float,
        signal_type: str,
        is_demo: bool = True,
        order_id: str = None,
        position_type: str = "long",
        stop_loss_price: float = None,
        take_profit_price: float = None,
        timeframe: str = "1h",
        signal_metadata: str = None,
    ) -> Optional[int]:
        """إضافة صفقة جديدة"""
        try:
            with self.get_write_connection() as conn:
                return self.add_position_on_conn(
                    conn=conn,
                    user_id=user_id,
                    symbol=symbol,
                    entry_price=entry_price,
                    quantity=quantity,
                    position_size=position_size,
                    signal_type=signal_type,
                    is_demo=is_demo,
                    order_id=order_id,
                    position_type=position_type,
                    stop_loss_price=stop_loss_price,
                    take_profit_price=take_profit_price,
                    timeframe=timeframe,
                    signal_metadata=signal_metadata,
                )
        except Exception as e:
            error_text = str(e)
            if (
                "UNIQUE constraint failed: active_positions.user_id, active_positions.symbol, active_positions.strategy"
                in error_text
            ):
                # توافق مع schema قديم: UNIQUE(user_id, symbol, strategy) حتى مع الصفقات المغلقة.
                # الحل المؤقت: إعادة استخدام الصف المغلق بنفس المفتاح بدلاً من فشل فتح الصفقة.
                try:
                    with self.get_write_connection() as conn:
                        existing = conn.execute(
                            """
                            SELECT id, is_active FROM active_positions
                            WHERE user_id = %s AND symbol = %s AND strategy = %s
                            LIMIT 1
                            """,
                            (user_id, symbol, signal_type),
                        ).fetchone()

                        if existing and int(existing["is_active"] or 0) == 0:
                            reused_id = int(existing["id"])
                            conn.execute(
                                """
                                UPDATE active_positions
                                SET entry_price = %s,
                                    quantity = %s,
                                    stop_loss = %s,
                                    take_profit = %s,
                                    is_demo = %s,
                                    order_id = %s,
                                    entry_commission = %s,
                                    exit_commission = 0,
                                    position_size = %s,
                                    position_type = %s,
                                    timeframe = %s,
                                    entry_date = CURRENT_TIMESTAMP,
                                    is_active = TRUE,
                                    created_at = CURRENT_TIMESTAMP,
                                    updated_at = CURRENT_TIMESTAMP,
                                    highest_price = %s,
                                    signal_metadata = %s,
                                    exit_reason = NULL,
                                    exit_price = NULL,
                                    profit_loss = NULL,
                                    profit_pct = NULL,
                                    closed_at = NULL,
                                    exit_order_id = NULL
                                WHERE id = %s
                                """,
                                (
                                    entry_price,
                                    quantity,
                                    stop_loss_price,
                                    take_profit_price,
                                    bool(is_demo),
                                    order_id,
                                    entry_commission,
                                    position_size,
                                    position_type,
                                    timeframe,
                                    entry_price,
                                    signal_metadata,
                                    reused_id,
                                ),
                            )
                            conn.commit()
                            self.logger.warning(
                                f"⚠️ Reused inactive active_positions row id={reused_id} "
                                f"for {symbol}/{signal_type} due to legacy UNIQUE constraint"
                            )
                            return reused_id
                except Exception as fallback_error:
                    self.logger.error(
                        f"فشل fallback فتح الصفقة بعد UNIQUE conflict: {fallback_error}"
                    )

            self.logger.error(
                f"خطأ Integrity عند فتح صفقة {symbol}/{signal_type} للمستخدم {user_id}: {error_text}"
            )
            return None
        except Exception as e:
            self.logger.error(
                f"خطأ في فتح صفقة {symbol}/{signal_type} للمستخدم {user_id}: {e}"
            )
            return None

    def close_position_on_conn(
        self,
        conn,
        position_id: int,
        exit_price: float,
        exit_reason: str,
        pnl: float,
        exit_commission: float = 0,
        exit_order_id: str = None,
    ) -> bool:
        """إغلاق صفقة على اتصال خارجي (للعمليات الذرية)"""
        position = conn.execute(
            "SELECT * FROM active_positions WHERE id = %s", (position_id,)
        ).fetchone()

        if position:
            pos = dict(position)
            entry_price = pos.get("entry_price", 0)
            quantity = pos.get("quantity", 0)
            initial_investment = entry_price * quantity
            pnl_pct = (pnl / initial_investment * 100) if initial_investment > 0 else 0
        else:
            pnl_pct = 0

        conn.execute(
            """
            UPDATE active_positions
            SET is_active = FALSE, exit_price = %s, exit_reason = %s,
                profit_loss = %s, profit_pct = %s, exit_commission = %s, exit_order_id = %s,
                closed_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """,
            (
                exit_price,
                exit_reason,
                pnl,
                pnl_pct,
                exit_commission,
                exit_order_id,
                position_id,
            ),
        )

        self.logger.info(f"تم إغلاق الصفقة {position_id}: {exit_reason}")
        return True

    def close_position(
        self,
        position_id: int,
        exit_price: float,
        exit_reason: str,
        pnl: float,
        exit_commission: float = 0,
        exit_order_id: str = None,
    ) -> bool:
        """إغلاق صفقة (standalone — يفتح اتصال خاص)"""
        try:
            with self.get_write_connection() as conn:
                self.close_position_on_conn(
                    conn,
                    position_id,
                    exit_price,
                    exit_reason,
                    pnl,
                    exit_commission,
                    exit_order_id,
                )
                return True
        except Exception as e:
            self.logger.error(f"خطأ في إغلاق صفقة: {e}")
            return False

    def update_user_balance_on_conn(
        self, conn, user_id: int, new_balance: float, is_demo: bool = True
    ) -> bool:
        """تحديث رصيد المحفظة على اتصال خارجي (للعمليات الذرية)"""
        is_demo_flag = bool(is_demo)

        # حساب إجمالي الربح/الخسارة من الصفقات المغلقة فقط (يجب أن يكون أولاً)
        try:
            stats_cursor = conn.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN is_active = FALSE THEN profit_loss ELSE 0 END), 0) as total_pnl,
                    SUM(CASE WHEN is_active = FALSE THEN 1 ELSE 0 END) as total_trades,
                    SUM(CASE WHEN is_active = FALSE AND profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN is_active = FALSE AND profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades
                FROM active_positions
                WHERE user_id = %s AND is_demo = %s
                """,
                (user_id, is_demo_flag),
            )
            stats_row = stats_cursor.fetchone()
        except Exception as e:
            self.logger.error(f"❌ Error fetching stats: {e}")
            stats_row = None

        # Fix: properly handle stats_row being None or invalid
        if stats_row is None or not hasattr(stats_row, "__len__") or len(stats_row) < 4:
            self.logger.warning(f"⚠️ Invalid stats_row, using defaults: {stats_row}")
            total_pnl = 0
            total_trades = 0
            winning_trades = 0
            losing_trades = 0
        else:
            total_pnl = stats_row[0] if stats_row[0] is not None else 0
            total_trades = int(stats_row[1] or 0)
            winning_trades = stats_row[2] if stats_row[2] is not None else 0
            losing_trades = stats_row[3] if stats_row[3] is not None else 0

        # الحصول على الرصيد الأولي
        try:
            if is_demo_flag:
                init_cursor = conn.execute(
                    "SELECT initial_balance FROM demo_accounts WHERE user_id = %s LIMIT 1",
                    (user_id,),
                )
            else:
                init_cursor = conn.execute(
                    """
                    SELECT initial_balance FROM portfolio WHERE user_id = %s AND is_demo = %s
                """,
                    (user_id, is_demo_flag),
                )
            initial_balance_row = init_cursor.fetchone()
        except Exception as e:
            self.logger.error(f"❌ Error fetching initial balance: {e}")
            initial_balance_row = None

        initial_balance = (
            float(initial_balance_row[0] or 0.0)
            if initial_balance_row
            and hasattr(initial_balance_row, "__len__")
            and len(initial_balance_row) > 0
            else 0.0
        )

        # حساب الرصيد المستثمر من الصفقات المفتوحة
        try:
            invested_cursor = conn.execute(
                """
                SELECT COALESCE(SUM(position_size), 0) as invested
                FROM active_positions
                WHERE user_id = %s AND is_active = TRUE AND is_demo = %s
            """,
                (user_id, is_demo_flag),
            )
            invested_row = invested_cursor.fetchone()
        except Exception as e:
            self.logger.error(f"❌ Error fetching invested balance: {e}")
            invested_row = None

        invested_balance = (
            invested_row[0]
            if invested_row
            and hasattr(invested_row, "__len__")
            and len(invested_row) > 0
            else 0
        )

        # total_balance = initial_balance + total_pnl (من الصفقات المغلقة)
        # هذا يضمن أن total_balance يعكس الأداء الحقيقي
        total_balance = initial_balance + total_pnl

        # available_balance = total_balance - invested_balance (ما يمكن سحبه)
        available_for_withdrawal = total_balance - invested_balance

        # التحقق من النشاط التجاري
        if (
            not is_demo_flag
            and initial_balance <= 0
            and total_balance > 0
            and (invested_balance > 0 or total_trades > 0)
        ):
            initial_balance = float(total_balance)
        has_real_trade_activity = (
            (not is_demo_flag)
            and total_balance > 0
            and (invested_balance > 0 or total_trades > 0)
        )
        portfolio_growth_pct = (
            ((total_pnl / initial_balance) * 100) if initial_balance > 0 else 0
        )

        conn.execute(
            """
            UPDATE portfolio
            SET total_balance = %s, available_balance = %s, invested_balance = %s,
                total_profit_loss = %s, total_profit_loss_percentage = %s,
                initial_balance = CASE
                    WHEN (initial_balance IS NULL OR initial_balance <= 0) AND %s > 0 THEN %s
                    ELSE initial_balance
                END,
                first_trade_balance = CASE
                    WHEN (first_trade_balance IS NULL OR first_trade_balance <= 0) AND %s THEN %s
                    ELSE first_trade_balance
                END,
                first_trade_at = CASE
                    WHEN first_trade_at IS NULL AND %s THEN CURRENT_TIMESTAMP
                    ELSE first_trade_at
                END,
                initial_balance_source = CASE
                    WHEN %s THEN 'first_system_trade_snapshot'
                    WHEN COALESCE(initial_balance_source, '') = '' THEN 'system_seed'
                    ELSE initial_balance_source
                END,
                total_trades = %s, winning_trades = %s, losing_trades = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND is_demo = %s
        """,
            (
                total_balance,
                available_for_withdrawal,
                invested_balance,
                total_pnl,
                portfolio_growth_pct,
                initial_balance,
                initial_balance,
                has_real_trade_activity,
                initial_balance,
                has_real_trade_activity,
                has_real_trade_activity,
                total_trades,
                winning_trades,
                losing_trades,
                user_id,
                is_demo_flag,
            ),
        )

        if is_demo_flag:
            conn.execute(
                """
                INSERT INTO demo_accounts (
                    user_id, initial_balance, available_balance, invested_balance,
                    total_balance, total_profit_loss, total_profit_loss_percentage,
                    total_trades, winning_trades, losing_trades, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    initial_balance = EXCLUDED.initial_balance,
                    available_balance = EXCLUDED.available_balance,
                    invested_balance = EXCLUDED.invested_balance,
                    total_balance = EXCLUDED.total_balance,
                    total_profit_loss = EXCLUDED.total_profit_loss,
                    total_profit_loss_percentage = EXCLUDED.total_profit_loss_percentage,
                    total_trades = EXCLUDED.total_trades,
                    winning_trades = EXCLUDED.winning_trades,
                    losing_trades = EXCLUDED.losing_trades,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    user_id,
                    initial_balance,
                    available_for_withdrawal,
                    invested_balance,
                    total_balance,
                    total_pnl,
                    portfolio_growth_pct,
                    total_trades,
                    winning_trades,
                    losing_trades,
                ),
            )

        return True

    def update_user_balance(
        self, user_id: int, new_balance: float, is_demo: bool = True
    ) -> bool:
        """تحديث رصيد المحفظة للمستخدم (standalone — يفتح اتصال خاص)"""
        try:
            is_demo_flag = bool(is_demo)
            with self.get_write_connection() as conn:
                # حساب إجمالي الربح/الخسارة من الصفقات المغلقة فقط (يجب أن يكون أولاً)
                stats_row = conn.execute(
                    """
                    SELECT
                        COALESCE(SUM(CASE WHEN is_active = FALSE THEN profit_loss ELSE 0 END), 0) as total_pnl,
                        SUM(CASE WHEN is_active = FALSE THEN 1 ELSE 0 END) as total_trades,
                        SUM(CASE WHEN is_active = FALSE AND profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(CASE WHEN is_active = FALSE AND profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades
                    FROM active_positions
                    WHERE user_id = %s AND is_demo = %s
                """,
                    (user_id, is_demo_flag),
                ).fetchone()

                total_pnl = stats_row[0] if stats_row else 0
                total_trades = int(stats_row[1] or 0) if stats_row else 0
                winning_trades = stats_row[2] if stats_row else 0
                losing_trades = stats_row[3] if stats_row else 0

                # الحصول على الرصيد الأولي
                if is_demo_flag:
                    initial_balance_row = conn.execute(
                        "SELECT initial_balance FROM demo_accounts WHERE user_id = %s LIMIT 1",
                        (user_id,),
                    ).fetchone()
                else:
                    initial_balance_row = conn.execute(
                        """
                        SELECT initial_balance FROM portfolio WHERE user_id = %s AND is_demo = %s
                    """,
                        (user_id, is_demo_flag),
                    ).fetchone()
                initial_balance = (
                    float(initial_balance_row[0] or 0.0) if initial_balance_row else 0.0
                )

                # حساب الرصيد المستثمر من الصفقات المفتوحة
                invested_row = conn.execute(
                    """
                    SELECT COALESCE(SUM(position_size), 0) as invested
                    FROM active_positions
                    WHERE user_id = %s AND is_active = TRUE AND is_demo = %s
                """,
                    (user_id, is_demo_flag),
                ).fetchone()
                invested_balance = invested_row[0] if invested_row else 0

                # total_balance = initial_balance + total_pnl (من الصفقات المغلقة)
                total_balance = initial_balance + total_pnl
                # available_balance = total_balance - invested_balance
                available_for_withdrawal = total_balance - invested_balance

                if (
                    not is_demo_flag
                    and initial_balance <= 0
                    and total_balance > 0
                    and (invested_balance > 0 or total_trades > 0)
                ):
                    initial_balance = float(total_balance)
                has_real_trade_activity = (
                    (not is_demo_flag)
                    and total_balance > 0
                    and (invested_balance > 0 or total_trades > 0)
                )
                portfolio_growth_pct = (
                    ((total_pnl / initial_balance) * 100) if initial_balance > 0 else 0
                )

                conn.execute(
                    """
                    UPDATE portfolio 
                    SET total_balance = %s, available_balance = %s, invested_balance = %s,
                        total_profit_loss = %s, total_profit_loss_percentage = %s,
                        initial_balance = CASE
                            WHEN (initial_balance IS NULL OR initial_balance <= 0) AND %s > 0 THEN %s
                            ELSE initial_balance
                        END,
                        first_trade_balance = CASE
                            WHEN (first_trade_balance IS NULL OR first_trade_balance <= 0) AND %s THEN %s
                            ELSE first_trade_balance
                        END,
                        first_trade_at = CASE
                            WHEN first_trade_at IS NULL AND %s THEN CURRENT_TIMESTAMP
                            ELSE first_trade_at
                        END,
                        initial_balance_source = CASE
                            WHEN %s THEN 'first_system_trade_snapshot'
                            WHEN COALESCE(initial_balance_source, '') = '' THEN 'system_seed'
                            ELSE initial_balance_source
                        END,
                        total_trades = %s, winning_trades = %s, losing_trades = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND is_demo = %s
                """,
                    (
                        total_balance,
                        available_for_withdrawal,
                        invested_balance,
                        total_pnl,
                        portfolio_growth_pct,
                        initial_balance,
                        initial_balance,
                        has_real_trade_activity,
                        initial_balance,
                        has_real_trade_activity,
                        has_real_trade_activity,
                        total_trades,
                        winning_trades,
                        losing_trades,
                        user_id,
                        is_demo_flag,
                    ),
                )

                if is_demo_flag:
                    conn.execute(
                        """
                        INSERT INTO demo_accounts (
                            user_id, initial_balance, available_balance, invested_balance,
                            total_balance, total_profit_loss, total_profit_loss_percentage,
                            total_trades, winning_trades, losing_trades, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id) DO UPDATE SET
                            initial_balance = EXCLUDED.initial_balance,
                            available_balance = EXCLUDED.available_balance,
                            invested_balance = EXCLUDED.invested_balance,
                            total_balance = EXCLUDED.total_balance,
                            total_profit_loss = EXCLUDED.total_profit_loss,
                            total_profit_loss_percentage = EXCLUDED.total_profit_loss_percentage,
                            total_trades = EXCLUDED.total_trades,
                            winning_trades = EXCLUDED.winning_trades,
                            losing_trades = EXCLUDED.losing_trades,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (
                            user_id,
                            initial_balance,
                            new_balance,
                            invested_balance,
                            total_balance,
                            total_pnl,
                            portfolio_growth_pct,
                            total_trades,
                            winning_trades,
                            losing_trades,
                        ),
                    )

                return True
        except Exception as e:
            self.logger.error(f"خطأ في تحديث رصيد المستخدم {user_id}: {e}")
            return False

    def update_position_trailing_stop(self, position_id: int, new_price: float) -> bool:
        """تحديث Trailing Stop"""
        try:
            with self.get_write_connection() as conn:
                conn.execute(
                    """
                    UPDATE active_positions 
                    SET trailing_sl_price = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """,
                    (new_price, position_id),
                )

                # get_write_connection يعمل commit تلقائياً
                return True
        except Exception as e:
            self.logger.error(f"خطأ في تحديث Trailing Stop: {e}")
            return False
