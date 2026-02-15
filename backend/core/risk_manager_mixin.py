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
        """
        حساب حجم الصفقة — Phase 0: Kelly مفعّل
        
        المنطق:
        1. Kelly Criterion يحدد النسبة المثلى
        2. لا نتجاوز max_position_pct
        3. لا نقل عن $10 (Binance minimum)
        """
        # الحد الأقصى لحجم الصفقة (نسبة من الرصيد)
        max_pct = self.config.get('max_position_pct', 0.10)
        
        # ✅ Phase 0: Kelly Criterion
        kelly_pct = max_pct  # fallback
        if self.kelly_sizer:
            try:
                kelly_result = self.kelly_sizer.calculate_position_size(
                    balance=balance,
                    max_position_pct=max_pct,
                    symbol=signal.get('symbol') if signal else None
                )
                kelly_pct = kelly_result.get('kelly_pct', max_pct)
                self.logger.info(
                    f"📊 Kelly: {kelly_pct*100:.1f}% "
                    f"(WR={kelly_result.get('win_rate', 0):.0%}, "
                    f"RR={kelly_result.get('avg_rr', 0):.2f})"
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Kelly calculation failed: {e}")
        
        # الحجم النهائي (Kelly أو الإعدادات)
        if kelly_pct != max_pct:
            position_pct = min(kelly_pct, max_pct)
            position_size = balance * position_pct
        else:
            # Fallback: نسبة ثابتة من الإعدادات
            position_pct = self.user_settings.get('position_size_percentage', 12.0) / 100.0
            position_size = balance * position_pct
            self.logger.info(f"📊 Fixed Position: ${position_size:.2f} (balance=${balance:.2f}, pct={position_pct*100:.1f}%)")
        
        # ✅ الحد الأدنى $10 (متطلبات Binance)
        if position_size < 10:
            self.logger.warning(f"⚠️ Position size ${position_size:.2f} < $10 minimum")
            return 0  # لا يكفي للتداول
        
        # ✅ لا يتجاوز 15% من الرصيد (حماية — أكثر صرامة مع Kelly)
        max_size = balance * 0.15
        if position_size > max_size:
            position_size = max_size
            self.logger.warning(f"⚠️ Position size capped at 15%: ${position_size:.2f}")
        
        self.logger.info(f"📊 Final Position size: ${position_size:.2f}")
        
        return position_size

    def _restore_daily_state_from_db(self):
        """
        ✅ استعادة الحالة اليومية من DB عند التشغيل
        يحسب trades_today و daily_pnl و consecutive_losses من الصفقات المغلقة اليوم
        """
        try:
            today_str = datetime.now().strftime('%Y-%m-%d')
            with self.db.get_connection() as conn:
                # صفقات اليوم المغلقة
                rows = conn.execute("""
                    SELECT profit_loss, closed_at
                    FROM active_positions
                    WHERE user_id = ? AND is_active = 0
                      AND DATE(closed_at) = ?
                    ORDER BY closed_at ASC
                """, (self.user_id, today_str)).fetchall()
            
            if not rows:
                return
            
            trades = 0
            losses = 0
            daily_pnl = 0.0
            consecutive_losses = 0
            
            for row in rows:
                pnl = row['profit_loss'] or 0
                trades += 1
                daily_pnl += pnl
                if pnl > 0:
                    consecutive_losses = 0
                else:
                    losses += 1
                    consecutive_losses += 1
            
            self.daily_state['trades_today'] = trades
            self.daily_state['losses_today'] = losses
            self.daily_state['daily_pnl'] = daily_pnl
            self.daily_state['consecutive_losses'] = consecutive_losses
            
            # إعادة تفعيل cooldown إذا كانت الخسائر المتتالية >= الحد
            if consecutive_losses >= self.daily_state['max_consecutive_losses']:
                # آخر صفقة خاسرة + مدة الـ cooldown
                last_loss_time = rows[-1]['closed_at']
                if isinstance(last_loss_time, str):
                    try:
                        last_dt = datetime.fromisoformat(last_loss_time.replace('Z', '+00:00')).replace(tzinfo=None)
                        cooldown_end = last_dt + timedelta(hours=self.daily_state['cooldown_hours'])
                        if cooldown_end > datetime.now():
                            self.daily_state['cooldown_until'] = cooldown_end
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
        if self.daily_state['last_reset'] != today:
            self.logger.info("📅 يوم جديد — تصفير الحالة اليومية")
            self.daily_state['trades_today'] = 0
            self.daily_state['losses_today'] = 0
            self.daily_state['consecutive_losses'] = 0
            self.daily_state['daily_pnl'] = 0.0
            self.daily_state['last_reset'] = today
            self.daily_state['cooldown_until'] = None

    def _check_risk_gates(self, open_positions: List[Dict], balance: float) -> tuple:
        """
        فحص جميع بوابات الحماية قبل فتح صفقة جديدة
        
        Returns:
            (can_trade: bool, reason: str)
        """
        # 1. تصفير يومي
        self._reset_daily_state_if_needed()
        
        # 2. Self-Throttling: حد يومي للصفقات
        if self.daily_state['trades_today'] >= self.daily_state['max_daily_trades']:
            return False, f"حد يومي: {self.daily_state['trades_today']}/{self.daily_state['max_daily_trades']} صفقة"
        
        # 3. Self-Throttling: حد خسارة يومي
        max_loss = balance * self.daily_state['max_daily_loss_pct']
        if self.daily_state['daily_pnl'] < -max_loss:
            return False, f"حد خسارة يومي: ${self.daily_state['daily_pnl']:.2f} (حد: -${max_loss:.2f})"
        
        # 4. System-wide Cooldown
        if self.daily_state['cooldown_until']:
            if datetime.now() < self.daily_state['cooldown_until']:
                remaining = (self.daily_state['cooldown_until'] - datetime.now()).total_seconds() / 60
                return False, f"cooldown: {remaining:.0f} دقيقة متبقية (بعد {self.daily_state['consecutive_losses']} خسائر)"
            else:
                self.daily_state['cooldown_until'] = None
                self.daily_state['consecutive_losses'] = 0
                self.logger.info("✅ انتهى cooldown — استئناف التداول")
        
        # 5. Portfolio Heat Manager (Phase 0 — تفعيل الكود الميت)
        heat_result = self.heat_manager.check_portfolio_heat(open_positions, balance)
        if not heat_result['can_open_new']:
            return False, f"حرارة المحفظة: {heat_result['current_heat_pct']}% (حد: {heat_result['max_heat_pct']}%)"
        
        return True, "OK"

    def _check_directional_stress(self, open_positions: List[Dict], new_signal_side: str) -> tuple:
        """
        Capital Stress Awareness: فحص تكدس الاتجاه
        
        Returns:
            (can_trade: bool, reason: str)
        """
        if not open_positions:
            return True, "OK"
        
        same_direction_count = sum(
            1 for p in open_positions 
            if p.get('position_type', 'long').upper() == new_signal_side.upper()
        )
        
        if same_direction_count >= self.daily_state['max_same_direction']:
            return False, f"تكدس اتجاهي: {same_direction_count} صفقات {new_signal_side} (حد: {self.daily_state['max_same_direction']})"
        
        return True, "OK"

    def _record_trade_result(self, pnl: float, is_win: bool):
        """تسجيل نتيجة الصفقة للحماية اليومية"""
        self._reset_daily_state_if_needed()
        
        self.daily_state['daily_pnl'] += pnl
        
        if is_win:
            self.daily_state['consecutive_losses'] = 0
        else:
            self.daily_state['losses_today'] += 1
            self.daily_state['consecutive_losses'] += 1
            
            if self.daily_state['consecutive_losses'] >= self.daily_state['max_consecutive_losses']:
                cooldown_hours = self.daily_state['cooldown_hours']
                self.daily_state['cooldown_until'] = datetime.now() + timedelta(hours=cooldown_hours)
                self.logger.warning(
                    f"🛑 System Cooldown: {self.daily_state['consecutive_losses']} خسائر متتالية "
                    f"→ توقف {cooldown_hours} ساعة حتى {self.daily_state['cooldown_until'].strftime('%H:%M')}"
                )
