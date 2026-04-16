"""
Database Users Mixin — extracted from database_manager.py (God Object split)
=============================================================================
Methods: user CRUD, authentication, settings, profile, email verification
"""

from datetime import datetime
from typing import Dict, Any, Optional

from backend.utils.trading_context import get_effective_is_demo, is_admin_user


class DbUsersMixin:
    """User-related database methods (users, settings, profile, verification)"""

    # ==================== المستخدمين والإعدادات ====================

    def get_user_by_username(self, username: str):
        """الحصول على بيانات المستخدم باسم المستخدم"""
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM users WHERE username = %s
            """,
                (username,),
            ).fetchone()

            if row:
                return dict(row)
            return None

    def get_user_by_email(self, email: str):
        """الحصول على بيانات المستخدم بالبريد الإلكتروني"""
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM users WHERE email = %s
            """,
                (email,),
            ).fetchone()

            if row:
                return dict(row)
            return None

    def authenticate_user(self, username: str, password: str):
        """التحقق من صحة بيانات المستخدم"""
        from backend.utils.password_utils import verify_password

        self.logger.info(f"محاولة تسجيل دخول للمستخدم: {username}")

        user = self.get_user_by_username(username)
        if user:
            self.logger.info(
                f"تم العثور على المستخدم: {username} (ID: {user.get('id')})"
            )

            stored_hash = user.get("password_hash")
            if stored_hash and verify_password(password, stored_hash):
                self.logger.info(f"تسجيل دخول ناجح للمستخدم: {username}")
                return user
            else:
                self.logger.warning(f"كلمة المرور غير صحيحة للمستخدم: {username}")
        else:
            self.logger.warning(f"المستخدم غير موجود: {username}")

        return None

    def create_user(self, username: str, email: str, password: str):
        """إنشاء مستخدم جديد مع إعدادات افتراضية"""
        try:
            from backend.utils.password_utils import hash_password

            with self.get_write_connection() as conn:
                password_hash = hash_password(password)

                self.logger.info(f"إنشاء مستخدم جديد: {username}")

                cursor = conn.execute(
                    """
                    INSERT INTO users (username, email, password_hash, user_type, created_at, is_active)
                    VALUES (%s, %s, %s, 'user', CURRENT_TIMESTAMP, TRUE)
                    RETURNING id
                """,
                    (username, email, password_hash),
                )

                user_id = cursor.lastrowid

                self.logger.info(f"تم إنشاء المستخدم بنجاح: {username} (ID: {user_id})")

                # إنشاء إعدادات افتراضية للمستخدم
                self._create_default_user_settings(user_id)

                # ❌ لا محفظة افتراضية - البيانات تُجلب من Binance API فقط

                conn.commit()

                return user_id
        except Exception as e:
            self.logger.error(f"خطأ في إنشاء المستخدم: {e}")
            return None

    def _create_default_user_settings(self, user_id: int):
        """إنشاء إعدادات افتراضية للمستخدم الجديد"""
        try:
            with self.get_write_connection() as conn:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO user_settings (
                        user_id, is_demo, trading_enabled, trade_amount,
                        position_size_percentage, stop_loss_pct, take_profit_pct, trailing_distance,
                        max_positions, risk_level, max_daily_loss_pct, daily_loss_limit,
                        trading_mode, volatility_buffer, min_signal_strength,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                    (
                        user_id,
                        0,
                        False,
                        100.0,
                        10.0,
                        2.0,
                        5.0,
                        3.0,
                        5,
                        "medium",
                        10.0,
                        100.0,
                        "demo",
                        0.3,
                        0.6,
                    ),
                )
                self.logger.info(f"تم إنشاء إعدادات افتراضية للمستخدم {user_id}")
        except Exception as e:
            self.logger.error(f"خطأ في إنشاء الإعدادات الافتراضية: {e}")

    def get_user_by_id(self, user_id: int):
        """الحصول على بيانات المستخدم بمعرف المستخدم"""
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM users WHERE id = %s
            """,
                (user_id,),
            ).fetchone()

            if row:
                return dict(row)
            return None

    def get_user_settings(self, user_id: int):
        """الحصول على إعدادات المستخدم مع إنشاء افتراضية إذا لم توجد"""
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM user_settings WHERE user_id = %s
            """,
                (user_id,),
            ).fetchone()

            if row:
                return dict(row)

            # إنشاء إعدادات افتراضية إذا لم توجد
            self.logger.info(f"إنشاء إعدادات افتراضية للمستخدم {user_id}")
            self._create_default_user_settings(user_id)

            row = conn.execute(
                """
                SELECT * FROM user_settings WHERE user_id = %s
            """,
                (user_id,),
            ).fetchone()

            return dict(row) if row else {}

    def update_user_settings(self, user_id: int, **settings):
        """تحديث إعدادات المستخدم مع إنشاء السجل إذا لم يكن موجوداً"""
        if not settings:
            return True

        try:
            with self.get_write_connection() as conn:
                existing = conn.execute(
                    """
                    SELECT user_id FROM user_settings WHERE user_id = %s
                """,
                    (user_id,),
                ).fetchone()

                if not existing:
                    self.logger.info(f"إنشاء إعدادات افتراضية للمستخدم {user_id}")
                    self._create_default_user_settings(user_id)

                update_fields = []
                values = []

                for key, value in settings.items():
                    update_fields.append(f"{key} = %s")
                    values.append(value)

                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                values.append(user_id)

                query = f"UPDATE user_settings SET {', '.join(update_fields)} WHERE user_id = %s"
                result = conn.execute(query, values)
                conn.commit()

                if result.rowcount > 0:
                    self.logger.info(f"تم تحديث إعدادات المستخدم {user_id} بنجاح")
                    return True
                else:
                    self.logger.warning(f"لم يتم تحديث أي سجل للمستخدم {user_id}")
                    return False

        except Exception as e:
            self.logger.error(f"خطأ في تحديث إعدادات المستخدم {user_id}: {e}")
            return False

    def get_trading_settings(self, user_id: int, is_demo: int = None) -> Dict[str, Any]:
        """الحصول على إعدادات التداول حسب الوضع"""
        try:
            is_admin = is_admin_user(self, user_id)

            with self.get_connection() as conn:
                if is_admin:
                    if is_demo is None:
                        is_demo = get_effective_is_demo(self, user_id)

                    settings_row = conn.execute(
                        """
                        SELECT trading_enabled, max_positions, stop_loss_pct, 
                               take_profit_pct, risk_level, trade_amount, 
                               max_daily_loss_pct, trading_mode, trailing_distance,
                               volatility_buffer, min_signal_strength, position_size_percentage,
                               daily_loss_limit, created_at, updated_at
                        FROM user_settings WHERE user_id = %s AND is_demo = %s
                    """,
                        (user_id, is_demo),
                    ).fetchone()
                else:
                    # المستخدم العادي = real فقط (is_demo = FALSE)
                    settings_row = conn.execute(
                        """
                        SELECT trading_enabled, max_positions, stop_loss_pct, 
                               take_profit_pct, risk_level, trade_amount, 
                               max_daily_loss_pct, trading_mode, trailing_distance,
                               volatility_buffer, min_signal_strength, position_size_percentage,
                               daily_loss_limit, created_at, updated_at
                        FROM user_settings WHERE user_id = %s AND is_demo = FALSE
                    """,
                        (user_id,),
                    ).fetchone()

                if not settings_row:
                    self.logger.debug(
                        f"إعدادات المستخدم {user_id} غير موجودة - استخدام الافتراضية"
                    )
                    return self._get_default_trading_settings()

                # psycopg2 returns tuples, not dicts — map manually
                cols = [
                    "trading_enabled",
                    "max_positions",
                    "stop_loss_pct",
                    "take_profit_pct",
                    "risk_level",
                    "trade_amount",
                    "max_daily_loss_pct",
                    "trading_mode",
                    "trailing_distance",
                    "volatility_buffer",
                    "min_signal_strength",
                    "position_size_percentage",
                    "daily_loss_limit",
                    "created_at",
                    "updated_at",
                ]
                settings_data = dict(zip(cols, settings_row))

                return {
                    "stop_loss_pct": float(settings_data.get("stop_loss_pct", 2.0)),
                    "take_profit_pct": float(settings_data.get("take_profit_pct", 5.0)),
                    "max_positions": int(settings_data.get("max_positions", 5)),
                    "trading_enabled": bool(
                        settings_data.get("trading_enabled", False)
                    ),
                    "trade_amount": float(settings_data.get("trade_amount", 100.0)),
                    "risk_level": settings_data.get("risk_level", "medium"),
                    "max_daily_loss_pct": float(
                        settings_data.get("max_daily_loss_pct", 10.0)
                    ),
                    "trading_mode": settings_data.get("trading_mode", "demo"),
                    "trailing_distance": float(
                        settings_data.get("trailing_distance", 3.0)
                    ),
                    "volatility_buffer": float(
                        settings_data.get("volatility_buffer", 0.3)
                    ),
                    "min_signal_strength": float(
                        settings_data.get("min_signal_strength", 0.6)
                    ),
                    "position_size_percentage": float(
                        settings_data.get("position_size_percentage", 10.0)
                    ),
                    "daily_loss_limit": float(
                        settings_data.get("daily_loss_limit", 100.0)
                    ),
                    "created_at": settings_data.get("created_at"),
                    "updated_at": settings_data.get("updated_at"),
                }

        except Exception as e:
            self.logger.error(f"خطأ في جلب إعدادات التداول: {e}")
            return self._get_default_trading_settings()

    def _get_default_trading_settings(self) -> Dict[str, Any]:
        """إعدادات التداول الافتراضية متوافقة مع schema.sql"""
        return {
            "stop_loss_pct": 2.0,
            "take_profit_pct": 5.0,
            "max_positions": 5,
            "trading_enabled": False,
            "trade_amount": 100.0,
            "risk_level": "medium",
            "max_daily_loss_pct": 10.0,
            "trading_mode": "demo",
            "trailing_distance": 3.0,
            "volatility_buffer": 0.3,
            "min_signal_strength": 0.6,
            "position_size_percentage": 10.0,
            "daily_loss_limit": 100.0,
            "created_at": None,
            "updated_at": None,
        }

    def update_trading_settings(
        self, user_id: int, settings: Dict[str, Any], is_demo: bool = False
    ) -> bool:
        """تحديث إعدادات التداول مع التحقق من الصحة - جميع الحقول في user_settings"""
        try:
            settings_updates = {}
            with self.get_connection() as conn:
                user_settings_columns = {
                    row[0]
                    for row in conn.execute("""
                        SELECT column_name FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = 'user_settings'
                    """).fetchall()
                }

            if "stop_loss_pct" in settings:
                sl = float(settings["stop_loss_pct"])
                if 0.5 <= sl <= 20.0:
                    settings_updates["stop_loss_pct"] = sl
                else:
                    raise ValueError(f"نسبة وقف الخسارة يجب أن تكون بين 0.5% و 20%")

            if "take_profit_pct" in settings:
                tp = float(settings["take_profit_pct"])
                if 1.0 <= tp <= 50.0:
                    settings_updates["take_profit_pct"] = tp
                else:
                    raise ValueError(f"نسبة جني الأرباح يجب أن تكون بين 1% و 50%")

            if "max_positions" in settings:
                max_pos = int(settings["max_positions"])
                if 1 <= max_pos <= 20:
                    settings_updates["max_positions"] = max_pos
                else:
                    raise ValueError(f"عدد الصفقات المتزامنة يجب أن يكون بين 1 و 20")

            if "trading_enabled" in settings:
                settings_updates["trading_enabled"] = bool(settings["trading_enabled"])

            if "risk_level" in settings and settings["risk_level"] in [
                "low",
                "medium",
                "high",
            ]:
                settings_updates["risk_level"] = settings["risk_level"]

            if "trade_amount" in settings:
                amount = float(settings["trade_amount"])
                if 5.0 <= amount <= 10000.0:
                    settings_updates["trade_amount"] = amount
                else:
                    raise ValueError(f"مبلغ التداول يجب أن يكون بين 5 و 10000")

            if "capital_percentage" in settings:
                cap_pct = float(settings["capital_percentage"])
                if 1.0 <= cap_pct <= 50.0:
                    # توافق خلفي: نستقبل capital_percentage ونخزنه في الحقل القياسي
                    settings_updates["position_size_percentage"] = cap_pct
                else:
                    raise ValueError(f"نسبة رأس المال يجب أن تكون بين 1% و 50%")

            # ⚡ دعم اختياري لحقول متقدمة إذا كانت موجودة في الـ schema
            if "exit_strategy" in settings and "exit_strategy" in user_settings_columns:
                settings_updates["exit_strategy"] = settings["exit_strategy"]
            if (
                "safe_mode_enabled" in settings
                and "safe_mode_enabled" in user_settings_columns
            ):
                settings_updates["safe_mode_enabled"] = bool(
                    settings["safe_mode_enabled"]
                )

            # ✅ Toggle Mode للأدمن
            if "trading_mode" in settings:
                valid_modes = ["demo", "real"]
                if settings["trading_mode"] in valid_modes:
                    settings_updates["trading_mode"] = settings["trading_mode"]
                else:
                    raise ValueError(
                        f"trading_mode يجب أن يكون واحد من: {', '.join(valid_modes)}"
                    )

            if settings_updates:
                with self.get_write_connection() as conn:
                    filtered_updates = {
                        key: value
                        for key, value in settings_updates.items()
                        if key in user_settings_columns
                    }

                    if not filtered_updates:
                        return True

                    update_fields = [f"{key} = %s" for key in filtered_updates.keys()]
                    update_fields.append("updated_at = CURRENT_TIMESTAMP")
                    values = list(filtered_updates.values()) + [user_id]

                    query = f"UPDATE user_settings SET {', '.join(update_fields)} WHERE user_id = %s AND is_demo = %s"
                    conn.execute(query, values + [is_demo])
                    self.logger.info(f"تم تحديث إعدادات التداول للمستخدم {user_id}")

            return True

        except Exception as e:
            self.logger.error(f"خطأ في تحديث إعدادات التداول: {e}")
            return False

    # ==================== إدارة الملف الشخصي المحسن ====================

    def get_user_full_profile(self, user_id: int) -> Dict[str, Any]:
        """الحصول على الملف الشخصي الكامل للمستخدم"""
        with self.get_connection() as conn:
            row = conn.execute(
                """
                SELECT u.id, u.username, u.email, u.name, u.phone_number,
                       u.user_type, u.is_active, u.email_verified,
                       u.is_phone_verified, u.preferred_verification_method,
                       u.created_at, u.updated_at, u.last_login_at,
                       us.trading_enabled, us.trading_mode, us.trade_amount,
                       us.position_size_percentage, us.stop_loss_pct,
                       us.take_profit_pct, us.max_positions,
                       us.max_daily_loss_pct, us.risk_level, us.is_demo
                FROM users u
                LEFT JOIN user_settings us
                    ON us.user_id = u.id AND us.is_demo = FALSE
                WHERE u.id = %s
            """,
                (user_id,),
            ).fetchone()

            if row:
                return dict(row)
            return {}

    def update_user_profile(self, user_id: int, profile_data: Dict[str, Any]) -> bool:
        """تحديث الملف الشخصي الكامل للمستخدم"""
        try:
            with self.get_write_connection() as conn:
                update_fields = []
                values = []

                allowed_fields = [
                    "first_name",
                    "last_name",
                    "phone_number",
                    "date_of_birth",
                    "country_code",
                    "preferred_language",
                    "timezone",
                    "profile_image_url",
                    "two_factor_enabled",
                ]

                for field in allowed_fields:
                    if field in profile_data:
                        update_fields.append(f"{field} = %s")
                        values.append(profile_data[field])

                if update_fields:
                    update_fields.append("updated_at = CURRENT_TIMESTAMP")
                    values.append(user_id)

                    query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
                    conn.execute(query, values)
                    self.logger.info(f"تم تحديث الملف الشخصي للمستخدم {user_id}")

                return True

        except Exception as e:
            self.logger.error(f"خطأ في تحديث الملف الشخصي: {e}")
            return False

    def get_user_stats(self, user_id: int, is_demo: bool = None) -> Dict[str, Any]:
        """الحصول على إحصائيات التداول للمستخدم"""
        try:
            with self.get_connection() as conn:
                trades_query = """
                    SELECT
                        COUNT(CASE WHEN is_active = FALSE THEN 1 END) as total_trades,
                        COUNT(CASE WHEN is_active = FALSE AND profit_loss > 0 THEN 1 END) as winning_trades,
                        COUNT(CASE WHEN is_active = FALSE AND profit_loss < 0 THEN 1 END) as losing_trades,
                        AVG(CASE WHEN is_active = FALSE THEN profit_loss END) as avg_profit_loss,
                        SUM(CASE WHEN is_active = FALSE THEN profit_loss ELSE 0 END) as total_profit_loss,
                        MAX(CASE WHEN is_active = FALSE THEN profit_loss END) as max_profit,
                        MIN(CASE WHEN is_active = FALSE THEN profit_loss END) as min_profit
                    FROM active_positions
                    WHERE user_id = %s
                """

                params = [user_id]
                if is_demo is not None:
                    trades_query += " AND is_demo = %s"
                    params.append(bool(is_demo))

                cursor = conn.execute(trades_query, params)
                stats_row = cursor.fetchone()

                if not stats_row or stats_row[0] == 0:
                    return {
                        "totalTrades": 0,
                        "winningTrades": 0,
                        "losingTrades": 0,
                        "winRate": 0.0,
                        "avgProfitLoss": 0.0,
                        "totalProfitLoss": 0.0,
                        "maxProfit": 0.0,
                        "minProfit": 0.0,
                        "activeTrades": 0,
                    }

                total_trades = stats_row[0] or 0
                winning_trades = stats_row[1] or 0
                losing_trades = stats_row[2] or 0
                avg_profit_loss = stats_row[3] or 0.0
                total_profit_loss = stats_row[4] or 0.0
                max_profit = stats_row[5] or 0.0
                min_profit = stats_row[6] or 0.0

                win_rate = (
                    (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
                )

                active_query = """
                    SELECT COUNT(*) FROM active_positions 
                    WHERE user_id = %s AND is_active = TRUE
                """
                active_params = [user_id]
                if is_demo is not None:
                    active_query += " AND is_demo = %s"
                    active_params.append(bool(is_demo))

                cursor = conn.execute(active_query, active_params)
                active_trades = cursor.fetchone()[0] or 0

                return {
                    "totalTrades": total_trades,
                    "winningTrades": winning_trades,
                    "losingTrades": losing_trades,
                    "winRate": round(win_rate, 1),
                    "avgProfitLoss": round(avg_profit_loss, 2),
                    "totalProfitLoss": round(total_profit_loss, 2),
                    "maxProfit": round(max_profit, 2),
                    "minProfit": round(min_profit, 2),
                    "activeTrades": active_trades,
                }

        except Exception as e:
            self.logger.error(f"خطأ في جلب إحصائيات المستخدم {user_id}: {e}")
            return {
                "totalTrades": 0,
                "winningTrades": 0,
                "losingTrades": 0,
                "winRate": 0.0,
                "avgProfitLoss": 0.0,
                "totalProfitLoss": 0.0,
                "maxProfit": 0.0,
                "minProfit": 0.0,
                "activeTrades": 0,
            }

    def update_notification_preferences(
        self, user_id: int, preferences: Dict[str, Any]
    ) -> bool:
        """تحديث تفضيلات الإشعارات"""
        try:
            with self.get_write_connection() as conn:
                user_settings_columns = {
                    row[0]
                    for row in conn.execute("""
                        SELECT column_name FROM information_schema.columns
                        WHERE table_schema = 'public' AND table_name = 'user_settings'
                    """).fetchall()
                }

                notifications_enabled = None
                candidate_fields = [
                    "notifications_enabled",
                    "push_notifications_enabled",
                    "email_notifications_enabled",
                    "sms_notifications_enabled",
                    "price_alerts_enabled",
                ]

                provided = [
                    bool(preferences[f]) for f in candidate_fields if f in preferences
                ]
                if provided:
                    notifications_enabled = any(provided)

                if notifications_enabled is None:
                    return True

                if "notifications_enabled" in user_settings_columns:
                    conn.execute(
                        """
                        UPDATE user_settings
                        SET notifications_enabled = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                        """,
                        (int(notifications_enabled), user_id),
                    )
                    self.logger.info(f"تم تحديث تفضيلات الإشعارات للمستخدم {user_id}")

                return True

        except Exception as e:
            self.logger.error(f"خطأ في تحديث تفضيلات الإشعارات: {e}")
            return False

    # ===== دوال التحقق من الإيميل =====

    def save_verification_code(self, verification_data: dict) -> bool:
        """حفظ رمز التحقق في قاعدة البيانات"""
        try:
            with self.get_write_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO verification_codes 
                    (email, otp_code, purpose, created_at, expires_at, attempts, verified)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        verification_data["email"],
                        verification_data["otp_code"],
                        verification_data["purpose"],
                        verification_data["created_at"],
                        verification_data["expires_at"],
                        verification_data["attempts"],
                        verification_data["verified"],
                    ),
                )
                conn.commit()
                self.logger.info(
                    f"تم حفظ رمز التحقق للإيميل {verification_data['email']}"
                )
                return True
        except Exception as e:
            self.logger.error(f"خطأ في حفظ رمز التحقق: {e}")
            return False

    def mark_email_verified(self, email: str) -> bool:
        """تحديث حالة التحقق من الإيميل"""
        try:
            with self.get_write_connection() as conn:
                conn.execute(
                    """
                    UPDATE verification_codes 
                    SET verified = TRUE, verified_at = datetime('now')
                    WHERE email = %s AND verified = FALSE
                """,
                    (email,),
                )

                try:
                    conn.execute(
                        """
                        UPDATE users 
                        SET email_verified = TRUE, email_verified_at = datetime('now')
                        WHERE email = %s
                    """,
                        (email,),
                    )
                except Exception:
                    conn.execute(
                        """
                        UPDATE users 
                        SET email_verified = TRUE
                        WHERE email = %s
                    """,
                        (email,),
                    )

                conn.commit()
                self.logger.info(f"تم تأكيد التحقق من الإيميل {email}")
                return True
        except Exception as e:
            self.logger.error(f"خطأ في تحديث حالة التحقق: {e}")
            return False

    def get_email_verification_status(self, email: str) -> dict:
        """الحصول على حالة التحقق من الإيميل"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT verified, verified_at, created_at
                    FROM verification_codes 
                    WHERE email = %s 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """,
                    (email,),
                )

                result = cursor.fetchone()
                if result:
                    return {
                        "verified": bool(result[0]),
                        "verified_at": result[1],
                        "last_otp_sent": result[2],
                    }
                else:
                    return {
                        "verified": False,
                        "verified_at": None,
                        "last_otp_sent": None,
                    }
        except Exception as e:
            self.logger.error(f"خطأ في الحصول على حالة التحقق: {e}")
            return {"verified": False, "verified_at": None, "last_otp_sent": None}

    def get_last_otp_sent_time(self, email: str) -> Optional[float]:
        """الحصول على وقت آخر إرسال OTP"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT expires_at FROM verification_codes 
                    WHERE email = %s 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """,
                    (email,),
                )

                result = cursor.fetchone()
                if result:
                    return float(result[0]) - 300
                return None
        except Exception as e:
            self.logger.error(f"خطأ في الحصول على وقت آخر إرسال: {e}")
            return None

    def increment_verification_attempts(self, email: str) -> bool:
        """زيادة عدد محاولات التحقق"""
        try:
            with self.get_write_connection() as conn:
                conn.execute(
                    """
                    UPDATE verification_codes 
                    SET attempts = attempts + 1 
                    WHERE email = %s
                """,
                    (email,),
                )
                conn.commit()
                self.logger.info(f"تم زيادة محاولات التحقق للإيميل {email}")
                return True
        except Exception as e:
            self.logger.error(f"خطأ في زيادة محاولات التحقق: {e}")
            return False

    def clear_email_verification(self, email: str) -> bool:
        """مسح بيانات التحقق من الإيميل"""
        try:
            with self.get_write_connection() as conn:
                conn.execute(
                    "DELETE FROM verification_codes WHERE email = %s", (email,)
                )
                self.logger.info(f"تم مسح بيانات التحقق للإيميل {email}")
                return True
        except Exception as e:
            self.logger.error(f"خطأ في مسح بيانات التحقق: {e}")
            return False
