#!/usr/bin/env python3
"""
Admin Users Management Routes — extracted from admin_unified_api.py (God Object split)
======================================================================================
Routes: users/all, users/<id> (GET detail), users/create, users/<id>/update, users/<id>/delete
"""

from flask import request, jsonify

from config.logging_config import get_logger
from backend.infrastructure.db_access import get_db_manager
from backend.utils.password_utils import hash_password as _hash_pw
from backend.utils.trading_context import get_effective_is_demo


def _normalize_identity_value(value):
    if value is None:
        return ""
    return str(value).strip()


def _normalize_email(value):
    return _normalize_identity_value(value).lower()


def _normalize_phone(value):
    raw = _normalize_identity_value(value)
    return "".join(ch for ch in raw if ch.isdigit())


logger = get_logger(__name__)
db_manager = get_db_manager()


def register_admin_users_routes(bp, shared):
    """Register all user management routes on the admin blueprint."""
    require_admin = shared["require_admin"]
    audit_logger = shared["audit_logger"]

    @bp.route("/users/all", methods=["GET"])
    @require_admin
    def get_all_users_with_stats():
        """جلب جميع المستخدمين مع إحصائياتهم"""
        try:
            db = db_manager
            with db.get_connection() as conn:
                # Single query replaces the previous 1+N×2 pattern.
                # trading_enabled and is_demo come from the latest user_settings row
                # per user. For regular users is_demo is always FALSE; for admins
                # we pick the row that has trading_enabled=TRUE (their active
                # mode).
                cursor = conn.execute("""
                    SELECT
                        u.id, u.username, u.email, u.name, u.phone_number,
                        u.user_type, u.is_active, u.created_at, u.last_login_at,
                        (SELECT COUNT(*) FROM active_positions WHERE user_id = u.id) as total_trades,
                        (SELECT COUNT(*) FROM active_positions
                            WHERE user_id = u.id AND is_active = FALSE AND profit_loss > 0
                        ) as winning_trades,
                        COALESCE((
                            SELECT trading_enabled FROM user_settings s
                            WHERE s.user_id = u.id
                            ORDER BY
                                CASE WHEN s.trading_enabled = TRUE THEN 0 ELSE 1 END,
                                COALESCE(s.updated_at, s.created_at) DESC
                            LIMIT 1
                        ), FALSE) as trading_enabled,
                        COALESCE((
                            SELECT s.is_demo FROM user_settings s
                            WHERE s.user_id = u.id
                            ORDER BY
                                CASE WHEN s.trading_enabled = TRUE THEN 0 ELSE 1 END,
                                COALESCE(s.updated_at, s.created_at) DESC
                            LIMIT 1
                        ), FALSE) as effective_is_demo
                    FROM users u
                    ORDER BY u.created_at DESC
                    LIMIT 50
                """)

                users = []
                for row in cursor.fetchall():
                    row_dict = (
                        dict(row)
                        if hasattr(row, "keys")
                        else {
                            "id": row[0],
                            "username": row[1],
                            "email": row[2],
                            "name": row[3],
                            "phone_number": row[4],
                            "user_type": row[5],
                            "is_active": row[6],
                            "created_at": row[7],
                            "last_login_at": row[8],
                            "total_trades": row[9],
                            "winning_trades": row[10],
                            "trading_enabled": row[11],
                            "effective_is_demo": row[12],
                        }
                    )
                    user_id = row_dict["id"]
                    total_trades = row_dict["total_trades"] or 0
                    winning_trades = row_dict["winning_trades"] or 0
                    win_rate = (
                        (winning_trades / total_trades * 100) if total_trades > 0 else 0
                    )
                    effective_is_demo = bool(row_dict["effective_is_demo"])
                    # Regular users are always in real mode regardless of DB
                    # flag
                    if row_dict["user_type"] != "admin":
                        effective_is_demo = False
                    trading_mode = "demo" if effective_is_demo else "real"

                    users.append(
                        {
                            "id": user_id,
                            "username": row_dict["username"],
                            "email": row_dict["email"],
                            "fullName": row_dict["name"],
                            "phoneNumber": row_dict["phone_number"],
                            "userType": row_dict["user_type"],
                            "isActive": bool(row_dict["is_active"]),
                            "createdAt": row_dict["created_at"],
                            "lastLogin": row_dict["last_login_at"],
                            "totalTrades": total_trades,
                            "winningTrades": winning_trades,
                            "winRate": round(win_rate, 1),
                            "tradingEnabled": bool(row_dict["trading_enabled"]),
                            "tradingMode": trading_mode,
                        }
                    )

                total_users = len(users)
                active_users = len([u for u in users if u["isActive"]])
                admin_users = len([u for u in users if u["userType"] == "admin"])

                stats = {
                    "totalUsers": total_users,
                    "activeUsers": active_users,
                    "inactiveUsers": total_users - active_users,
                    "adminUsers": admin_users,
                    "regularUsers": total_users - admin_users,
                }

                return jsonify(
                    {"success": True, "data": {"users": users, "stats": stats}}
                )

        except Exception as e:
            logger.error(f"خطأ في جلب المستخدمين: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/users/<int:user_id>", methods=["GET"])
    @require_admin
    def get_user_details(user_id):
        """جلب تفاصيل مستخدم معين"""
        try:
            db = db_manager
            with db.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT
                        id, username, email,
                        name AS full_name,
                        phone_number AS phone,
                        user_type, is_active, created_at,
                        last_login_at AS last_login
                    FROM users
                    WHERE id = %s
                """,
                    (user_id,),
                )

                row = cursor.fetchone()
                if not row:
                    return (
                        jsonify({"success": False, "error": "المستخدم غير موجود"}),
                        404,
                    )

                (
                    user_id,
                    username,
                    email,
                    full_name,
                    phone,
                    user_type,
                    is_active,
                    created_at,
                    last_login,
                ) = row

                return jsonify(
                    {
                        "success": True,
                        "data": {
                            "id": user_id,
                            "username": username,
                            "email": email,
                            "fullName": full_name,
                            "phoneNumber": phone,
                            "userType": user_type,
                            "isActive": bool(is_active),
                            "createdAt": created_at,
                            "lastLogin": last_login,
                        },
                    }
                )

        except Exception as e:
            logger.error(f"خطأ في جلب تفاصيل المستخدم: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/users/create", methods=["POST"])
    @require_admin
    def create_user():
        """إنشاء مستخدم جديد"""
        try:
            data = request.get_json(silent=True) or {}
            if not data:
                return (
                    jsonify({"success": False, "error": "بيانات مطلوبة"}),
                    400,
                )

            # قبول full_name / name كبديل لـ username
            if "username" not in data:
                fallback = (
                    data.get("fullName")
                    or data.get("full_name")
                    or data.get("name")
                    or data.get("email", "").split("@")[0]
                )
                data["username"] = fallback

            if "userType" in data and "user_type" not in data:
                data["user_type"] = data["userType"]

            required_fields = ["username", "email", "password", "user_type"]
            for field in required_fields:
                if not data.get(field):
                    return (
                        jsonify({"success": False, "error": f"الحقل {field} مطلوب"}),
                        400,
                    )

            if data["user_type"] not in ["admin", "user"]:
                return (
                    jsonify({"success": False, "error": "نوع المستخدم غير صحيح"}),
                    400,
                )

            normalized_username = _normalize_identity_value(data["username"])
            normalized_email = _normalize_email(data["email"])
            normalized_phone = _normalize_phone(
                data.get(
                    "phoneNumber",
                    data.get("phone", data.get("phone_number", "")),
                )
            )

            db = db_manager
            with db.get_write_connection() as conn:
                duplicate_cursor = (
                    conn.execute(
                        """
                    SELECT id, username, email, phone_number FROM users
                    WHERE LOWER(username) = LOWER(%s)
                       OR LOWER(email) = LOWER(%s)
                       OR (%s <> '' AND REGEXP_REPLACE(COALESCE(phone_number, ''), '[^0-9]', '', 'g') = %s)
                    LIMIT 1
                    """,
                        (
                            normalized_username,
                            normalized_email,
                            normalized_phone,
                            normalized_phone,
                        ),
                    )
                    if getattr(db, "is_postgres", lambda: False)()
                    else conn.execute(
                        """
                    SELECT id, username, email, phone_number FROM users
                    WHERE LOWER(username) = LOWER(%s)
                       OR LOWER(email) = LOWER(%s)
                       OR (%s <> '' AND REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(COALESCE(phone_number, ''), '+', ''), '-', ''), ' ', ''), '(', ''), ')', '') = %s)
                    LIMIT 1
                    """,
                        (
                            normalized_username,
                            normalized_email,
                            normalized_phone,
                            normalized_phone,
                        ),
                    )
                )

                existing_user = duplicate_cursor.fetchone()
                if existing_user:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "يوجد مستخدم بنفس اسم المستخدم أو البريد الإلكتروني أو رقم الهاتف",
                            }
                        ),
                        409,
                    )

                if getattr(db, "is_postgres", lambda: False)():
                    conn.execute("""
                        SELECT setval(
                            pg_get_serial_sequence('users', 'id'),
                            COALESCE((SELECT MAX(id) FROM users), 1),
                            COALESCE((SELECT MAX(id) FROM users), 0) > 0
                        )
                    """)

                cursor = conn.execute(
                    """
                    INSERT INTO users (
                        username, email, password_hash, name, phone_number,
                        user_type, is_active, email_verified, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, TRUE, TRUE, CURRENT_TIMESTAMP)
                    RETURNING id
                """,
                    (
                        normalized_username,
                        normalized_email,
                        _hash_pw(data["password"]),
                        data.get(
                            "fullName",
                            data.get("full_name", data.get("name", "")),
                        ),
                        data.get(
                            "phoneNumber",
                            data.get("phone", data.get("phone_number", "")),
                        ),
                        data["user_type"],
                    ),
                )

                # PostgreSQL: RETURNING id requires fetchone(), not lastrowid
                row = cursor.fetchone()
                user_id = row[0] if row else None
                if user_id is None:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "فشل إنشاء المستخدم",
                                "error_code": "USER_CREATION_FAILED",
                            }
                        ),
                        500,
                    )

                is_admin_user = data["user_type"] == "admin"

                conn.execute(
                    """
                    INSERT INTO user_settings (
                        user_id, is_demo, trading_enabled, trade_amount,
                        position_size_percentage, stop_loss_pct, take_profit_pct,
                        max_positions, risk_level, max_daily_loss_pct, trading_mode,
                        created_at, updated_at
                    ) VALUES (%s, FALSE, FALSE, 100.0, 10.0, 2.0, 5.0, 5, 'medium', 10.0, 'real', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                    (user_id,),
                )

                conn.execute(
                    """
                    INSERT INTO portfolio (
                        user_id, total_balance, available_balance, invested_balance,
                        total_profit_loss, total_profit_loss_percentage, initial_balance,
                        is_demo, created_at, updated_at
                    ) VALUES (%s, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                    (user_id,),
                )

                if is_admin_user:
                    conn.execute(
                        """
                        INSERT INTO user_settings (
                            user_id, is_demo, trading_enabled, trade_amount,
                            position_size_percentage, stop_loss_pct, take_profit_pct,
                            max_positions, risk_level, max_daily_loss_pct, trading_mode,
                            created_at, updated_at
                        ) VALUES (%s, TRUE, FALSE, 100.0, 10.0, 2.0, 5.0, 5, 'medium', 10.0, 'demo', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                        (user_id,),
                    )
                    conn.execute(
                        """
                        INSERT INTO portfolio (
                            user_id, total_balance, available_balance, invested_balance,
                            total_profit_loss, total_profit_loss_percentage, initial_balance,
                            is_demo, created_at, updated_at
                        ) VALUES (%s, 10000.0, 10000.0, 0.0, 0.0, 0.0, 10000.0, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                        (user_id,),
                    )

                if audit_logger:
                    audit_logger.log(
                        action="create_user",
                        user_id=user_id,
                        details={
                            "username": data["username"],
                            "email": data["email"],
                            "user_type": data["user_type"],
                        },
                    )

                return jsonify(
                    {
                        "success": True,
                        "data": {
                            "userId": user_id,
                            "username": data["username"],
                            "email": data["email"],
                            "userType": data["user_type"],
                        },
                    }
                )

        except Exception as e:
            logger.error(f"خطأ في إنشاء المستخدم: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/users/<int:user_id>/update", methods=["PUT", "POST"])
    @require_admin
    def update_user(user_id):
        """تحديث بيانات المستخدم"""
        try:
            data = request.get_json(silent=True) or {}
            if not data:
                return (
                    jsonify({"success": False, "error": "بيانات مطلوبة"}),
                    400,
                )

            if "userType" in data and "user_type" not in data:
                data["user_type"] = data["userType"]
            if "fullName" in data and "full_name" not in data:
                data["full_name"] = data["fullName"]
            if (
                "phoneNumber" in data
                and "phone" not in data
                and "phone_number" not in data
            ):
                data["phone_number"] = data["phoneNumber"]

            db = db_manager
            with db.get_write_connection() as conn:
                cursor = conn.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                if not cursor.fetchone():
                    return (
                        jsonify({"success": False, "error": "المستخدم غير موجود"}),
                        404,
                    )

                if "user_type" in data and data["user_type"] not in [
                    "admin",
                    "regular",
                ]:
                    return (
                        jsonify(
                            {
                                "success": False,
                                "error": "نوع المستخدم غير صحيح",
                            }
                        ),
                        400,
                    )

                update_fields = []
                update_values = []

                candidate_username = (
                    _normalize_identity_value(data.get("username"))
                    if "username" in data
                    else ""
                )
                candidate_email = (
                    _normalize_email(data.get("email")) if "email" in data else ""
                )
                candidate_phone = _normalize_phone(
                    data.get("phone_number", data.get("phone", ""))
                )

                if candidate_username or candidate_email or candidate_phone:
                    duplicate_cursor = (
                        conn.execute(
                            """
                        SELECT id FROM users
                        WHERE id <> %s
                          AND (
                              (%s <> '' AND LOWER(username) = LOWER(%s))
                              OR (%s <> '' AND LOWER(email) = LOWER(%s))
                              OR (%s <> '' AND REGEXP_REPLACE(COALESCE(phone_number, ''), '[^0-9]', '', 'g') = %s)
                          )
                        LIMIT 1
                        """,
                            (
                                user_id,
                                candidate_username,
                                candidate_username,
                                candidate_email,
                                candidate_email,
                                candidate_phone,
                                candidate_phone,
                            ),
                        )
                        if getattr(db, "is_postgres", lambda: False)()
                        else conn.execute(
                            """
                        SELECT id FROM users
                        WHERE id <> %s
                          AND (
                              (%s <> '' AND LOWER(username) = LOWER(%s))
                              OR (%s <> '' AND LOWER(email) = LOWER(%s))
                              OR (%s <> '' AND REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(COALESCE(phone_number, ''), '+', ''), '-', ''), ' ', ''), '(', ''), ')', '') = %s)
                          )
                        LIMIT 1
                        """,
                            (
                                user_id,
                                candidate_username,
                                candidate_username,
                                candidate_email,
                                candidate_email,
                                candidate_phone,
                                candidate_phone,
                            ),
                        )
                    )
                    if duplicate_cursor.fetchone():
                        return (
                            jsonify(
                                {
                                    "success": False,
                                    "error": "يوجد مستخدم آخر بنفس اسم المستخدم أو البريد الإلكتروني أو رقم الهاتف",
                                }
                            ),
                            409,
                        )

                field_mapping = {
                    "username": "username",
                    "email": "email",
                    "full_name": "name",
                    "name": "name",
                    "phone": "phone_number",
                    "phone_number": "phone_number",
                    "user_type": "user_type",
                    "is_active": "is_active",
                }

                for input_key, column_name in field_mapping.items():
                    if input_key in data:
                        value = data[input_key]
                        if input_key == "username":
                            value = candidate_username
                        elif input_key == "email":
                            value = candidate_email
                        update_fields.append(f"{column_name} = %s")
                        update_values.append(value)

                if not update_fields:
                    return (
                        jsonify({"success": False, "error": "لا توجد حقول للتحديث"}),
                        400,
                    )

                update_values.append(user_id)
                query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"

                conn.execute(query, update_values)

                if audit_logger:
                    audit_logger.log(
                        action="update_user", user_id=user_id, details=data
                    )

                return jsonify({"success": True, "message": "تم تحديث المستخدم بنجاح"})

        except Exception as e:
            logger.error(f"خطأ في تحديث المستخدم: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/users/<int:user_id>/toggle-trading", methods=["POST"])
    @require_admin
    def toggle_user_trading(user_id):
        """تفعيل/تعطيل التداول لمستخدم معين"""
        try:
            data = request.get_json() or {}
            enabled = data.get("tradingEnabled")
            if enabled is None:
                enabled = data.get("trading_enabled")
            if enabled is None:
                return (
                    jsonify({"success": False, "error": "tradingEnabled مطلوب"}),
                    400,
                )

            db = db_manager
            target_is_demo = get_effective_is_demo(db, user_id)
            target_mode = "demo" if target_is_demo else "real"

            with db.get_write_connection() as conn:
                existing = conn.execute(
                    "SELECT id FROM user_settings WHERE user_id=%s AND is_demo=%s LIMIT 1",
                    (user_id, target_is_demo),
                ).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE user_settings SET trading_enabled=%s, trading_mode=%s, updated_at=CURRENT_TIMESTAMP WHERE user_id=%s AND is_demo=%s",
                        (bool(enabled), target_mode, user_id, target_is_demo),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO user_settings (
                            user_id, is_demo, trading_enabled, trade_amount,
                            position_size_percentage, stop_loss_pct, take_profit_pct,
                            max_positions, risk_level, max_daily_loss_pct, trading_mode,
                            created_at, updated_at
                        ) VALUES (%s, %s, %s, 100.0, 10.0, 2.0, 5.0, 5, 'medium', 10.0, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """,
                        (user_id, target_is_demo, bool(enabled), target_mode),
                    )
                    if not target_is_demo:
                        conn.execute(
                            """
                            INSERT INTO portfolio (
                                user_id, total_balance, available_balance, invested_balance,
                                total_profit_loss, total_profit_loss_percentage, initial_balance,
                                is_demo, created_at, updated_at
                            )
                            SELECT %s, %s, %s, 0.0, 0.0, 0.0, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                            WHERE NOT EXISTS (
                                SELECT 1 FROM portfolio WHERE user_id = %s AND is_demo = %s
                            )
                            """,
                            (
                                user_id,
                                0.0,
                                0.0,
                                0.0,
                                target_is_demo,
                                user_id,
                                target_is_demo,
                            ),
                        )

                if audit_logger:
                    audit_logger.log(
                        action="toggle_user_trading",
                        user_id=user_id,
                        details={"tradingEnabled": enabled},
                    )

            return jsonify(
                {
                    "success": True,
                    "tradingEnabled": enabled,
                    "message": ("تم تفعيل التداول" if enabled else "تم تعطيل التداول"),
                }
            )

        except Exception as e:
            logger.error(f"خطأ في toggle trading للمستخدم {user_id}: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/users/<int:user_id>/force-close", methods=["POST"])
    @require_admin
    def force_close_user_positions(user_id):
        """إغلاق جميع الصفقات المفتوحة لمستخدم معين"""
        try:
            db = db_manager
            with db.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, user_id, symbol, entry_price, quantity, position_type, is_demo
                    FROM active_positions
                    WHERE user_id = %s AND is_active = TRUE
                    """,
                    (user_id,),
                )
                positions = cursor.fetchall()

            if not positions:
                return jsonify(
                    {"success": True, "message": "لا توجد صفقات مفتوحة", "count": 0}
                )

            admin_user_id = getattr(g, "current_user_id", "unknown")
            admin_username = getattr(g, "current_username", "unknown")

            closed = 0
            errors = []

            for pos in positions:
                pid = pos["id"] if hasattr(pos, "keys") else pos[0]
                symbol = pos["symbol"] if hasattr(pos, "keys") else pos[2]
                raw_entry = pos["entry_price"] if hasattr(pos, "keys") else pos[3]
                raw_qty = pos["quantity"] if hasattr(pos, "keys") else pos[4]
                raw_type = pos["position_type"] if hasattr(pos, "keys") else pos[5]
                raw_demo = pos["is_demo"] if hasattr(pos, "keys") else pos[6]

                entry_price = float(raw_entry or 0)
                quantity = float(raw_qty or 0)
                if entry_price <= 0 or quantity <= 0:
                    errors.append({"position_id": pid, "error": "invalid_data"})
                    continue

                exit_price = 0.0
                try:
                    from backend.utils.data_provider import DataProvider

                    market_price = DataProvider().get_current_price(symbol)
                    if market_price and float(market_price) > 0:
                        exit_price = float(market_price)
                except Exception:
                    pass

                if exit_price <= 0:
                    exit_price = entry_price

                position_type = str(raw_type or "long").lower()
                is_long = position_type in ("long", "buy")
                pnl_raw = (
                    ((exit_price - entry_price) * quantity)
                    if is_long
                    else ((entry_price - exit_price) * quantity)
                )

                is_demo = int(raw_demo or 0)
                DEMO_COMMISSION_RATE = 0.001
                exit_commission = (
                    round(exit_price * quantity * DEMO_COMMISSION_RATE, 8)
                    if bool(is_demo)
                    else 0.0
                )
                pnl = pnl_raw - exit_commission

                close_ok = db.close_position(
                    position_id=pid,
                    exit_price=exit_price,
                    exit_reason="ADMIN_FORCE_CLOSE",
                    pnl=pnl,
                    exit_commission=exit_commission,
                    exit_order_id=f"ADMIN_FORCE_CLOSE_{admin_user_id}",
                )

                if close_ok:
                    try:
                        with db.get_connection() as balance_conn:
                            bal_row = balance_conn.execute(
                                "SELECT available_balance FROM portfolio WHERE user_id = %s AND is_demo = %s LIMIT 1",
                                (user_id, bool(is_demo)),
                            ).fetchone()
                        if bal_row is not None:
                            available_before = float(bal_row[0] or 0)
                            new_available = available_before + pnl
                            db.update_user_balance(
                                user_id, new_available, bool(is_demo)
                            )
                    except Exception as bal_err:
                        logger.warning(
                            f"⚠️ force-close balance sync failed for pos #{pid}: {bal_err}"
                        )

                    closed += 1
                else:
                    errors.append(
                        {"position_id": pid, "error": "close_position_failed"}
                    )

            logger.info(
                f"🔒 Admin {admin_username} (id={admin_user_id}) force-closed {closed}"
                f" positions for user {user_id}"
            )

            if audit_logger:
                audit_logger.log(
                    action="force_close_user_positions",
                    user_id=user_id,
                    details={
                        "closed_count": closed,
                        "total": len(positions),
                        "errors": errors if errors else None,
                        "admin_id": admin_user_id,
                    },
                )

            return jsonify(
                {
                    "success": True,
                    "message": f"تم إغلاق {closed} صفقة",
                    "data": {
                        "closed_count": closed,
                        "total": len(positions),
                        "errors": errors if errors else None,
                    },
                }
            )

        except Exception as e:
            logger.error(f"خطأ في force close للمستخدم {user_id}: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @bp.route("/users/<int:user_id>/delete", methods=["DELETE"])
    @require_admin
    def delete_user(user_id):
        """حذف مستخدم (تعطيل بدلاً من الحذف الكامل)"""
        try:
            db = db_manager
            with db.get_write_connection() as conn:
                conn.execute(
                    "UPDATE users SET is_active = FALSE WHERE id = %s",
                    (user_id,),
                )

                if audit_logger:
                    audit_logger.log(
                        action="deactivate_user",
                        user_id=user_id,
                        details={"action": "deactivated"},
                    )

                return jsonify({"success": True, "message": "تم تعطيل المستخدم بنجاح"})

        except Exception as e:
            logger.error(f"خطأ في حذف المستخدم: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
