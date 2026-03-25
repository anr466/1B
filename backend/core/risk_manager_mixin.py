"""
Risk Manager Mixin — إدارة المخاطر وحماية رأس المال
=====================================================
Extracted from group_b_system.py (God Object split)

Methods:
    _calculate_position_size, _restore_daily_state_from_db,
    _reset_daily_state_if_needed, _check_risk_gates,
    _check_directional_stress, _record_trade_result
"""

from datetime import datetime, timedelta
from typing import Dict, List


class RiskManagerMixin:
    """Mixin for risk management, position sizing, and daily state tracking"""

    def _calculate_position_size(self, balance: float, signal: Dict = None) -> float:
        """حساب حجم الصفقة الذكي — يجمع Kelly + قوة الإشارة + إعدادات المستخدم.

        المنطق:
        1. استخراج قوة الإشارة (confidence/score) من الإشارة.
        2. حساب حجم الصفقة بناءً على قوة الإشارة:
           - إشارة قوية (>= 70%): Kelly كامل + مضاعف من الإعدادات
           - إشارة متوسطة (50-70%): Kelly متوسط + نسبة من الإعدادات
           - إشارة ضعيفة (< 50%): إعدادات المستخدم فقط
        3. تطبيق معامل السيولة والحذر.
        4. لا نقل عن $10 (Binance minimum).
        5. لا نتجاوز 15% من الرصيد.
        """
        self.logger.info(f"💰 Position calc: balance=${balance:.2f}")

        # استخراج قوة الإشارة
        confidence = self._get_signal_confidence(signal)
        self.logger.info(f"📊 Signal confidence: {confidence:.0%}")

        # الحد الأقصى لحجم الصفقة (نسبة من الرصيد)
        max_pct = self.config.get("max_position_pct", 0.10)

        # نسبة إعدادات المستخدم
        user_pct = self.user_settings.get("position_size_percentage", 10.0) / 100.0

        # حساب Kelly Criterion
        kelly_pct = self._calculate_kelly_pct(balance, max_pct, signal)

        # تحديد الحجم بناءً على قوة الإشارة
        if confidence >= 0.70:
            # إشارة قوية: Kelly كامل + نسبة محسنة
            position_pct = max(kelly_pct, user_pct * 1.2)
            self.logger.info(
                f"📊 Strong signal - using Kelly + boost: {position_pct * 100:.1f}%"
            )
        elif confidence >= 0.50:
            # إشارة متوسطة: مزيج من Kelly والإعدادات
            position_pct = (kelly_pct + user_pct) / 2
            self.logger.info(
                f"📊 Medium signal - using Kelly+User blend: {position_pct * 100:.1f}%"
            )
        else:
            # إشارة ضعيفة: إعدادات المستخدم فقط (مخفضة)
            position_pct = user_pct * 0.7
            self.logger.info(
                f"📊 Weak signal - using reduced user settings: {position_pct * 100:.1f}%"
            )

        # تطبيق الحد الأقصى
        position_pct = min(position_pct, max_pct)
        position_size = balance * position_pct

        # تطبيق معامل حجم إضافي من فلتر السيولة/المعرفة (إن وجد)
        size_factor = 1.0
        if signal is not None:
            try:
                size_factor = float(signal.get("_size_factor", 1.0) or 1.0)
            except Exception:
                size_factor = 1.0

        if size_factor != 1.0:
            original_size = position_size
            position_size = max(0.0, position_size * size_factor)
            self.logger.info(
                f"💧 Liquidity-adjusted size: ${original_size:.2f} × {size_factor:.2f} = ${position_size:.2f}"
            )

        # Fix-A: تطبيق معامل الحذر من حالة السوق (يُضبط في _check_market_regime)
        # 1.0 = طبيعي | 0.7 = هبوط BTC 3-5% | 0.5 = RSI < 25
        caution = getattr(self, "_market_caution_factor", 1.0)
        if caution < 1.0 and caution > 0.0:
            original_size = position_size
            position_size = position_size * caution
            self.logger.info(
                f"🌡️ Market caution: ${original_size:.2f} × {caution:.1f} = ${position_size:.2f}"
            )

        # ✅ لا يتجاوز 15% من الرصيد (حماية — أكثر صرامة مع Kelly)
        max_size = balance * 0.15
        if position_size > max_size:
            position_size = max_size
            self.logger.warning(f"⚠️ Position size capped at 15%: ${position_size:.2f}")

        # ✅ تطبيق الحد الأقصى للمبلغ الاسمي (trade_amount) من إعدادات المستخدم إن وجد
        try:
            trade_amount_limit = float(self.user_settings.get("trade_amount", 0))
            if trade_amount_limit > 0 and position_size > trade_amount_limit:
                position_size = trade_amount_limit
                self.logger.info(
                    f"🚦 Position size capped by User trade_amount limit: ${position_size:.2f}"
                )
        except Exception:
            pass

        # ✅ الحد الأدنى $10 (متطلبات Binance)
        if position_size < 10:
            self.logger.warning(f"⚠️ Position size ${position_size:.2f} < $10 minimum")
            return 0  # لا يكفي للتداول

        self.logger.info(f"📊 Final Position size: ${position_size:.2f}")

        return position_size

    def _get_signal_confidence(self, signal: Dict = None) -> float:
        """استخراج قوة الإشارة (confidence) من الإشارة."""
        if signal is None:
            return 0.0

        confidence = 0.0

        if signal.get("confidence") is not None:
            conf = signal.get("confidence")
            if isinstance(conf, (int, float)):
                confidence = float(conf)
                if confidence > 1:
                    confidence = confidence / 100.0

        if confidence == 0.0 and signal.get("score") is not None:
            score = signal.get("score")
            if isinstance(score, (int, float)):
                confidence = float(score)
                if confidence > 1:
                    confidence = confidence / 100.0

        if signal.get("win_rate") is not None:
            wr = signal.get("win_rate")
            if isinstance(wr, (int, float)):
                confidence = max(confidence, float(wr))
                if confidence > 1:
                    confidence = confidence / 100.0

        return max(0.0, min(1.0, confidence))

    def _calculate_kelly_pct(
        self, balance: float, max_pct: float, signal: Dict = None
    ) -> float:
        """حساب Kelly Criterion مع معلومات الأداء التاريخية."""
        if self.kelly_sizer:
            try:
                kelly_result = self.kelly_sizer.calculate_position_size(
                    balance=balance,
                    max_position_pct=max_pct,
                    symbol=signal.get("symbol") if signal else None,
                )
                kelly_pct = kelly_result.get("kelly_pct", max_pct)
                self.logger.info(
                    f"📊 Kelly: {kelly_pct * 100:.1f}% "
                    f"(WR={kelly_result.get('win_rate', 0):.0%}, "
                    f"RR={kelly_result.get('avg_rr', 0):.2f})"
                )
                return kelly_pct
            except Exception as e:
                self.logger.warning(f"⚠️ Kelly calculation failed: {e}")

        user_pct = self.user_settings.get("position_size_percentage", 10.0) / 100.0
        self.logger.info(f"📊 Kelly fallback to user settings: {user_pct * 100:.1f}%")
        return user_pct

        return position_size

    def _restore_daily_state_from_db(self):
        """
        استعادة الحالة اليومية من DB عند التشغيل
        يحسب trades_today و daily_pnl و consecutive_losses من الصفقات المغلقة اليوم
        """
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            with self.db.get_connection() as conn:
                # صفقات اليوم المغلقة
                rows = conn.execute(
                    """
                    SELECT profit_loss, closed_at
                    FROM active_positions
                    WHERE user_id = %s AND is_active = FALSE AND is_demo = %s
                      AND DATE(closed_at) = %s
                    ORDER BY closed_at ASC
                """,
                    (self.user_id, bool(self.is_demo_trading), today_str),
                ).fetchall()

            if not rows:
                return

            trades = 0
            losses = 0
            daily_pnl = 0.0
            consecutive_losses = 0

            for row in rows:
                pnl = row["profit_loss"] or 0
                trades += 1
                daily_pnl += pnl
                if pnl > 0:
                    consecutive_losses = 0
                elif pnl < 0:
                    losses += 1
                    consecutive_losses += 1

            self.daily_state["trades_today"] = trades
            self.daily_state["losses_today"] = losses
            self.daily_state["daily_pnl"] = daily_pnl
            self.daily_state["consecutive_losses"] = consecutive_losses

            # إعادة تفعيل cooldown إذا كانت الخسائر المتتالية >= الحد
            if consecutive_losses >= self.daily_state["max_consecutive_losses"]:
                # آخر صفقة خاسرة + مدة الـ cooldown
                last_loss_time = rows[-1]["closed_at"]
                if isinstance(last_loss_time, str):
                    try:
                        last_dt = datetime.fromisoformat(
                            last_loss_time.replace("Z", "+00:00")
                        ).replace(tzinfo=None)
                        cooldown_end = last_dt + timedelta(
                            hours=self.daily_state["cooldown_hours"]
                        )
                        if cooldown_end > datetime.now():
                            self.daily_state["cooldown_until"] = cooldown_end
                            self.logger.warning(
                                f"🛡️ Restored cooldown until {cooldown_end.strftime('%H:%M')} "
                                f"({consecutive_losses} consecutive losses)"
                            )
                    except Exception:
                        pass

            self.logger.info(
                f"🛡️ Daily state restored from DB: "
                f"{trades} trades, PnL=${daily_pnl:+.2f}, "
                f"{consecutive_losses} consecutive losses"
            )
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to restore daily state: {e}")

    def _reset_daily_state_if_needed(self):
        """تصفير الحالة اليومية عند بداية يوم جديد"""
        today = datetime.now().date()
        if self.daily_state["last_reset"] != today:
            self.logger.info("📅 يوم جديد — تصفير الحالة اليومية")
            self.daily_state["trades_today"] = 0
            self.daily_state["losses_today"] = 0
            self.daily_state["consecutive_losses"] = 0
            self.daily_state["daily_pnl"] = 0.0
            self.daily_state["last_reset"] = today
            self.daily_state["cooldown_until"] = None

    def _check_risk_gates(self, open_positions: List[Dict], balance: float) -> tuple:
        """
        فحص جميع بوابات الحماية قبل فتح صفقة جديدة

        Returns:
            (can_trade: bool, reason: str)
        """
        # 1. تصفير يومي
        self._reset_daily_state_if_needed()

        # 2. Self-Throttling: حد يومي للصفقات
        if self.daily_state["trades_today"] >= self.daily_state["max_daily_trades"]:
            return (
                False,
                f"حد يومي: {self.daily_state['trades_today']}/{self.daily_state['max_daily_trades']} صفقة",
            )

        # 3. Self-Throttling: حد خسارة يومي
        max_loss = balance * self.daily_state["max_daily_loss_pct"]
        if self.daily_state["daily_pnl"] < -max_loss:
            return (
                False,
                f"حد خسارة يومي: ${self.daily_state['daily_pnl']:.2f} (حد: -${max_loss:.2f})",
            )

        # 4. System-wide Cooldown
        if self.daily_state["cooldown_until"]:
            if datetime.now() < self.daily_state["cooldown_until"]:
                remaining = (
                    self.daily_state["cooldown_until"] - datetime.now()
                ).total_seconds() / 60
                return (
                    False,
                    f"cooldown: {remaining:.0f} دقيقة متبقية (بعد {self.daily_state['consecutive_losses']} خسائر)",
                )
            else:
                self.daily_state["cooldown_until"] = None
                self.daily_state["consecutive_losses"] = 0
                self.logger.info("✅ انتهى cooldown — استئناف التداول")

        # 5. Portfolio Heat Manager (Phase 0 — تفعيل الكود الميت)
        heat_result = self.heat_manager.check_portfolio_heat(open_positions, balance)
        if not heat_result["can_open_new"]:
            return (
                False,
                f"حرارة المحفظة: {heat_result['current_heat_pct']}% (حد: {heat_result['max_heat_pct']}%)",
            )

        # ✅ FIX: Max Drawdown Stop — فحص الحد الأقصى للسحب
        max_drawdown_pct = self.daily_state.get("max_drawdown_pct", 0.30)  # 30% افتراضي
        peak_balance = self.daily_state.get("peak_balance", balance)

        if peak_balance > 0:
            current_drawdown = (peak_balance - balance) / peak_balance
            if current_drawdown >= max_drawdown_pct:
                self.logger.critical(
                    f"🚨 MAX DRAWDOWN STOP: {current_drawdown * 100:.1f}% drawdown reached "
                    f"(balance=${balance:.2f}, peak=${peak_balance:.2f}, limit={max_drawdown_pct * 100:.0f}%)"
                )
                return (
                    False,
                    f"توقف max drawdown: {current_drawdown * 100:.1f}% (حد: {max_drawdown_pct * 100:.0f}%)",
                )

        return True, "OK"

    def _check_directional_stress(
        self, open_positions: List[Dict], new_signal_side: str
    ) -> tuple:
        """
        Capital Stress Awareness: فحص تكدس الاتجاه

        Returns:
            (can_trade: bool, reason: str)
        """
        if not open_positions:
            return True, "OK"

        same_direction_count = sum(
            1
            for p in open_positions
            if p.get("position_type", "long").upper() == new_signal_side.upper()
        )

        if same_direction_count >= self.daily_state["max_same_direction"]:
            return (
                False,
                f"تكدس اتجاهي: {same_direction_count} صفقات {new_signal_side} (حد: {self.daily_state['max_same_direction']})",
            )

        return True, "OK"

    def _record_trade_result(self, pnl: float, is_win: bool):
        """تسجيل نتيجة الصفقة للحماية اليومية"""
        self._reset_daily_state_if_needed()

        self.daily_state["daily_pnl"] += pnl

        if pnl > 0:
            self.daily_state["consecutive_losses"] = 0
        elif pnl < 0:
            self.daily_state["losses_today"] += 1
            self.daily_state["consecutive_losses"] += 1

            if (
                self.daily_state["consecutive_losses"]
                >= self.daily_state["max_consecutive_losses"]
            ):
                cooldown_hours = self.daily_state["cooldown_hours"]
                self.daily_state["cooldown_until"] = datetime.now() + timedelta(
                    hours=cooldown_hours
                )
                self.logger.warning(
                    f"🛑 System Cooldown: {self.daily_state['consecutive_losses']} خسائر متتالية "
                    f"→ توقف {cooldown_hours} ساعة حتى {self.daily_state['cooldown_until'].strftime('%H:%M')}"
                )

        # ✅ FIX: تحديث peak_balance بعد كل صفقة
        current_balance = self._load_user_portfolio().get("total_value", 0)
        if current_balance > self.daily_state.get("peak_balance", 0):
            self.daily_state["peak_balance"] = current_balance
