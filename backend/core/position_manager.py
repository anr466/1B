"""
Position Manager Mixin — إدارة فتح وإغلاق ومراقبة الصفقات
============================================================
Extracted from group_b_system.py (God Object split)

Methods:
    _get_open_positions, _manage_position, _close_position,
    _open_position, _get_current_price, _update_trailing_stop
"""

from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd


class PositionManagerMixin:
    """Mixin for position open/close/manage logic"""

    def _get_open_positions(self) -> List[Dict]:
        """جلب الصفقات المفتوحة من قاعدة البيانات"""
        try:
            positions = self.db.get_user_active_positions(self.user_id)
            return positions or []
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
    
    def _manage_position(self, position):
        """
        إدارة صفقة مفتوحة وفحص شروط الخروج
        ===== Strategy Exit Logic (via BaseStrategy interface) =====
        
        Args:
            position: بيانات الصفقة
            
        Returns:
            الإجراء المتخذ أو None
        """
        symbol = position.get('symbol')
        entry_price = position.get('entry_price', 0)
        position_id = position.get('id')
        position_type = position.get('position_type', 'long').upper()
        
        # جلب السعر الحالي
        current_price = self._get_current_price(symbol)
        if not current_price:
            return None
        
        # ✅ FIX-6: فحص تجاوز SL أثناء توقف النظام (حماية فورية)
        sl = position.get('stop_loss', 0)
        if sl and sl > 0:
            sl_breached = False
            if position_type == 'SHORT' and current_price >= sl:
                sl_breached = True
            elif position_type != 'SHORT' and current_price <= sl:
                sl_breached = True
            
            if sl_breached:
                self.logger.warning(
                    f"🚨 [{symbol}] SL BREACHED during downtime! "
                    f"SL=${sl:.4f} | Current=${current_price:.4f} | Closing immediately"
                )
                return self._close_position(position, current_price, 'SL_BREACH_ON_RESTART', 1.0)
        
        # حساب الربح/الخسارة (يعتمد على الاتجاه)
        if position_type == 'SHORT':
            pnl_pct = (entry_price - current_price) / entry_price if entry_price > 0 else 0
        else:
            pnl_pct = (current_price - entry_price) / entry_price if entry_price > 0 else 0
        
        self.logger.info(f"   📈 {symbol} ({position_type}): Entry ${entry_price:.4f} | "
                        f"Current ${current_price:.4f} | PnL {pnl_pct*100:+.2f}%")
        
        # ===== Strategy Exit System (عبر الواجهة الموحدة) =====
        if self.strategy:
            try:
                timeframe = self.config.get('execution_timeframe', '1h')
                df = self.data_provider.get_historical_data(symbol, timeframe, limit=200)
                if df is None or len(df) < 70:
                    self.logger.warning(f"⚠️ {symbol}: Insufficient data for exit analysis")
                    return None
                
                # تحضير البيانات (عبر الواجهة الموحدة)
                df = self.strategy.prepare_data(df)
                
                # فحص شروط الخروج (عبر الواجهة الموحدة — الاستراتيجية تتولى بناء pos_data داخلياً)
                exit_result = self.strategy.check_exit(df, position)
                
                # تحديث peak و trailing stop في DB
                updated = exit_result.get('updated', {})
                if updated.get('peak'):
                    try:
                        with self.db.get_write_connection() as conn:
                            conn.execute(
                                "UPDATE active_positions SET highest_price = ? WHERE id = ?",
                                (updated['peak'], position_id))
                    except Exception as e:
                        self.logger.warning(f"⚠️ Failed to update peak: {e}")
                
                if updated.get('trail'):
                    self._update_trailing_stop(position_id, updated['trail'])
                
                if exit_result['should_exit']:
                    exit_price = exit_result['exit_price']
                    strategy_name = self.strategy.name if self.strategy else 'unknown'
                    reason_code = str(exit_result.get('reason', ''))
                    reason = f"{strategy_name}_{reason_code}"

                    use_exit_confirmation = False
                    if hasattr(self, 'liquidity_filter') and getattr(self, 'liquidity_filter') is not None:
                        rc_upper = reason_code.upper()
                        if not any(tag in rc_upper for tag in ['SL', 'STOP_LOSS', 'EMERGENCY']):
                            use_exit_confirmation = True

                    if use_exit_confirmation:
                        try:
                            conf = self.liquidity_filter.evaluate_exit_confirmation(symbol, df, position, exit_result)
                            if conf.get('decision') == 'HOLD':
                                self.logger.info(
                                    f"   💧 [{symbol}] ExitConfirmation HOLD: exit_score={conf.get('exit_score', 0):.1f} "
                                    f"hold_score={conf.get('hold_score', 0):.1f}"
                                )
                                return None
                        except Exception as e:
                            self.logger.warning(f"⚠️ ExitConfirmation error for {symbol}: {e}")

                    entry_time = position.get('created_at')
                    hold_hours = 0
                    if entry_time:
                        if isinstance(entry_time, str):
                            try:
                                entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00')).replace(tzinfo=None)
                            except Exception:
                                entry_time = datetime.now()
                        hold_hours = (datetime.now() - entry_time).total_seconds() / 3600

                    self.logger.info(
                        f"   🚪 [{symbol}] Exit: {exit_result['reason']} | "
                        f"Price: ${exit_price:.4f} | Hold: {hold_hours:.1f}h"
                    )

                    return self._close_position(position, exit_price, reason, 1.0)
                else:
                    # عرض حالة الاحتفاظ من منظور الاستراتيجية
                    trail_level = exit_result.get('trail_level', 0)
                    if trail_level > 0:
                        self.logger.debug(
                            f"   📊 {symbol}: HOLD | Trail: ${trail_level:.4f} | "
                            f"Peak: ${exit_result.get('peak', 0):.4f}"
                        )

                    # ===== Liquidity-Cognitive Early Exit (إضافة سريعة فوق منطق الاستراتيجية) =====
                    # لا نمنع أي خروج تقرره الاستراتيجية؛ فقط نضيف خروجاً مبكراً إذا:
                    # - PnL سلبي/قريب من الصفر في سياق سيولة سيء، أو
                    # - ربح صغير جداً مع سياق سيولة ضعيف جداً.
                    if hasattr(self, 'liquidity_filter') and getattr(self, 'liquidity_filter') is not None:
                        try:
                            early = self.liquidity_filter.evaluate_early_exit(symbol, df, position)
                            if early.get('should_exit'):
                                early_price = float(early.get('exit_price', current_price) or current_price)
                                early_reason = early.get('reason', 'LIQ_EARLY_EXIT')
                                self.logger.info(
                                    f"   💧 [{symbol}] Early exit by LiquidityFilter: {early_reason} | "
                                    f"Price: ${early_price:.4f}"
                                )
                                return self._close_position(position, early_price, early_reason, 1.0)
                        except Exception as e:
                            self.logger.warning(f"⚠️ LiquidityFilter early-exit error for {symbol}: {e}")

                    return None
                    
            except Exception as e:
                self.logger.error(f"⚠️ [{symbol}] Strategy exit error: {e}")
                # Fallback: Basic SL/TP check if strategy fails
                sl = position.get('stop_loss', 0)
                tp = position.get('take_profit', 0)
                
                if position_type == 'SHORT':
                    if sl > 0 and current_price >= sl:
                        return self._close_position(position, current_price, 'STOP_LOSS_FALLBACK', 1.0)
                    if tp > 0 and current_price <= tp:
                        return self._close_position(position, current_price, 'TAKE_PROFIT_FALLBACK', 1.0)
                else:
                    if sl > 0 and current_price <= sl:
                        return self._close_position(position, current_price, 'STOP_LOSS_FALLBACK', 1.0)
                    if tp > 0 and current_price >= tp:
                        return self._close_position(position, current_price, 'TAKE_PROFIT_FALLBACK', 1.0)
        
        return None
    
    def _close_position(self, position: Dict, exit_price: float, reason: str, close_pct: float = 1.0) -> Dict:
        """إغلاق صفقة (كاملة أو جزئية)"""
        position_id = position.get('id')
        symbol = position.get('symbol')
        entry_price = position.get('entry_price', 0)
        quantity = position.get('quantity', 0)
        position_size_entry = entry_price * quantity
        position_type = position.get('position_type', 'long').upper()
        
        # 💰 حساب الربح/الخسارة الأولي (قبل العمولة) - يعتمد على الاتجاه
        if position_type == 'SHORT':
            pnl_raw = (entry_price - exit_price) * quantity
        else:
            pnl_raw = (exit_price - entry_price) * quantity
        
        # 💰 حساب عمولة الخروج وخصمها من PnL للحسابات الوهمية فقط
        exit_commission = 0
        exit_order_id = None
        entry_commission = position.get('entry_commission', 0)
        
        if self.is_demo_trading:
            # Demo: نحسب عمولة الخروج ونخصمها من PnL
            position_size_exit = abs(exit_price * quantity)
            exit_commission = position_size_exit * 0.001  # 0.1%
            # ✅ FIX: عمولة الدخول خُصمت بالفعل من الرصيد عند الفتح (total_deduction = position_size + entry_commission)
            # لذلك نخصم فقط عمولة الخروج من PnL الخام — لا نخصم عمولة الدخول مرة أخرى
            pnl = pnl_raw - exit_commission
            # ✅ النسبة المئوية الفعلية بعد عمولة الخروج فقط
            pnl_pct = pnl / position_size_entry if position_size_entry > 0 else 0
            self.logger.info(f"   💰 Demo Exit Commission: ${exit_commission:.4f} (Entry commission ${entry_commission:.4f} already deducted at open)")
        else:
            # 💱 تنفيذ إغلاق حقيقي على Binance
            if self.binance_manager:
                self.logger.info(f"   💱 Executing REAL close on Binance: {position_type} {symbol} qty={quantity:.6f}")
                
                if position_type == 'LONG':
                    close_result = self.binance_manager.execute_sell_order(self.user_id, symbol, quantity)
                else:
                    close_result = self.binance_manager.execute_buy_order(self.user_id, symbol, quantity)
                
                if close_result.get('success'):
                    real_exit_price = float(close_result.get('price', exit_price))
                    exit_commission = float(close_result.get('commission', 0))
                    exit_order_id = str(close_result.get('order_id', ''))
                    if real_exit_price > 0:
                        exit_price = real_exit_price
                    # إعادة حساب PnL بالسعر الحقيقي
                    if position_type == 'SHORT':
                        pnl_raw = (entry_price - exit_price) * quantity
                    else:
                        pnl_raw = (exit_price - entry_price) * quantity
                    self.logger.info(
                        f"   ✅ Binance close FILLED: price=${exit_price:.4f} "
                        f"commission=${exit_commission:.4f} order_id={exit_order_id}"
                    )
                else:
                    self.logger.error(
                        f"⚠️ Binance close FAILED: {close_result.get('message')} — "
                        f"closing in DB with market price ${exit_price:.4f}"
                    )
            
            # Real: PnL بعد خصم عمولة الخروج (عمولة الدخول خُصمت عند الفتح)
            pnl = pnl_raw - exit_commission
            if position_type == 'SHORT':
                pnl_pct = pnl / position_size_entry if position_size_entry > 0 else 0
            else:
                pnl_pct = pnl / position_size_entry if position_size_entry > 0 else 0
        
        self.logger.info(f"   💰 CLOSING {position_type} {symbol}: ${exit_price:.4f} | "
                        f"PnL ${pnl:.2f} ({pnl_pct*100:+.2f}%) | Reason: {reason}")
        
        # ========== إغلاق الصفقة وتحديث الرصيد بشكل atomic ==========
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                
                # 1. إغلاق في قاعدة البيانات
                self.db.close_position(position_id, exit_price, reason, pnl, 
                                      exit_commission=exit_commission,
                                      exit_order_id=exit_order_id)
                
                # 2. تحديث رصيد المحفظة
                current_balance = self.user_portfolio.get('balance', 0)
                returned_amount = position_size_entry + pnl
                new_balance = current_balance + returned_amount
                self.db.update_user_balance(self.user_id, new_balance, self.is_demo_trading)
                
                # 3. Commit معاً - إما تنجح العمليتان أو تفشلان
                conn.commit()
                
                # 4. تحديث الحالة المحلية بعد النجاح
                self.user_portfolio['balance'] = new_balance
                self.logger.info(f"   💰 Balance updated atomically: ${current_balance:.2f} → ${new_balance:.2f} (returned ${position_size_entry:.2f} + PnL {pnl:+.2f})")
                
        except Exception as e:
            self.logger.error(f"❌ CRITICAL: Atomic transaction failed for closing {symbol}: {e}")
            self.logger.error(f"   ⛔ Position NOT closed, balance NOT updated - transaction rolled back")
            return None
        
        # ========== التعلم من النتيجة ==========
        is_win = pnl > 0
        
        # ✅ Phase 1: تسجيل نتيجة الصفقة للحماية اليومية (Throttling + Cooldown)
        self._record_trade_result(pnl, is_win)
        
        # 📈 تسجيل الصفقة في المحسّن التكيّفي (للتعلم)
        if self.optimizer:
            try:
                entry_time = position.get('created_at')
                hold_min = 0
                if entry_time:
                    if isinstance(entry_time, str):
                        try:
                            entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00')).replace(tzinfo=None)
                            hold_min = int((datetime.now() - entry_dt).total_seconds() / 60)
                        except Exception:
                            pass
                
                # استخراج المؤشرات المحفوظة مع الصفقة
                saved_indicators = {}
                try:
                    meta = position.get('metadata') or position.get('signal_metadata') or '{}'
                    if isinstance(meta, str):
                        import json as _json
                        meta = _json.loads(meta)
                    saved_indicators = meta.get('entry_indicators', {})
                except Exception:
                    pass
                
                self.optimizer.record_trade(
                    symbol=symbol,
                    side=position_type.lower(),
                    entry_price=entry_price,
                    exit_price=exit_price,
                    pnl=pnl,
                    pnl_pct=pnl_pct * 100,
                    exit_reason=reason,
                    sl_pct_used=self.config.get('max_sl_pct', 0.01),
                    hold_minutes=hold_min,
                    open_positions_count=len(self._get_open_positions()),
                    indicators=saved_indicators,
                )
            except Exception as opt_err:
                self.logger.warning(f"⚠️ Optimizer record error: {opt_err}")
        
        # تسجيل في القائمة السوداء الديناميكية
        self.dynamic_blacklist.record_trade(symbol, is_win, pnl)
        try:
            self.notification_service.notify_trade_closed(
                user_id=self.user_id,
                symbol=symbol,
                profit_loss=pnl,
                profit_pct=pnl_pct * 100,
                exit_reason=reason
            )
        except Exception as e:
            self.logger.warning(f"⚠️ فشل إرسال إشعار إغلاق الصفقة: {e}")
        
        # ========== 3. تعليم ML من الصفقة الحقيقية ==========
        try:
            source = 'demo_trading' if self.is_demo_trading else 'real_trading'
            self.ml_training_manager.add_real_trade(
                symbol=symbol,
                strategy=position.get('signal_type', 'COMBINED'),
                timeframe='1h',
                entry_price=entry_price,
                exit_price=exit_price,
                profit_loss=pnl,
                profit_pct=pnl_pct * 100,
                source=source
            )
        except Exception as e:
            self.logger.warning(f"⚠️ فشل تسجيل الصفقة لـ ML: {e}")
        
        return {
            'type': 'CLOSE',
            'symbol': symbol,
            'reason': reason,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct * 100
        }

    def _open_position(self, symbol: str, signal: Dict) -> Optional[Dict]:
        """فتح صفقة جديدة (LONG أو SHORT)"""
        balance = self.user_portfolio.get('balance', 0)
        
        # ✅ Phase 0: حساب حجم الصفقة عبر Kelly (بدلاً من النسبة الثابتة)
        position_size = self._calculate_position_size(balance, signal)
        
        # 📈 تعديل الحجم بناءً على التعلم التكيّفي
        if self.optimizer:
            try:
                size_mult = self.optimizer.get_position_size_multiplier(
                    consecutive_losses=self.daily_state.get('consecutive_losses', 0),
                    daily_pnl=self.daily_state.get('daily_pnl', 0)
                )
                if size_mult != 1.0:
                    original_size = position_size
                    position_size = position_size * size_mult
                    self.logger.info(f"   📈 Adaptive size: ${original_size:.2f} × {size_mult:.2f} = ${position_size:.2f}")
            except Exception as e:
                self.logger.warning(f"⚠️ Adaptive size error: {e}")
        
        # ✅ رفض إذا أقل من الحد الأدنى $10 (Binance)
        if position_size < 10:
            self.logger.warning(f"❌ Rejected {symbol}: Position size ${position_size:.2f} < $10 minimum")
            return None
        
        entry_price = signal.get('entry_price', 0)
        quantity = position_size / entry_price if entry_price > 0 else 0
        side = signal.get('side', 'LONG').upper()
        
        # 💰 حساب عمولة الدخول (0.1% Binance) للحسابات الوهمية فقط
        entry_commission = 0
        order_id = None
        
        if self.is_demo_trading:
            entry_commission = position_size * 0.001  # 0.1%
            self.logger.info(f"   💰 Demo Commission (Entry): ${entry_commission:.4f}")
        else:
            # 💱 تنفيذ حقيقي على Binance
            if not self.binance_manager:
                self.logger.error(
                    f"⛔ Real trading requires BinanceManager. "
                    f"Add Binance API keys or switch to demo mode."
                )
                return None
            
            self.logger.info(f"   💱 Executing REAL {side} order on Binance: {symbol} qty={quantity:.6f}")
            
            if side == 'LONG':
                result = self.binance_manager.execute_buy_order(self.user_id, symbol, quantity)
            else:
                result = self.binance_manager.execute_sell_order(self.user_id, symbol, quantity)
            
            if not result.get('success'):
                self.logger.error(f"⛔ Binance order FAILED: {result.get('message', 'unknown error')}")
                return None
            
            # استخدام البيانات الحقيقية من Binance
            real_price = float(result.get('price', entry_price))
            real_qty = float(result.get('quantity', quantity))
            entry_commission = float(result.get('commission', 0))
            order_id = str(result.get('order_id', ''))
            
            # تحديث بالأسعار الحقيقية
            if real_price > 0:
                entry_price = real_price
            if real_qty > 0:
                quantity = real_qty
            position_size = entry_price * quantity
            
            self.logger.info(
                f"   ✅ Binance order FILLED: price=${entry_price:.4f} qty={quantity:.6f} "
                f"commission=${entry_commission:.4f} order_id={order_id}"
            )
        
        # حساب SL بناءً على V7 logic + التعلم التكيّفي
        sl_price = signal.get('stop_loss', 0)
        if sl_price == 0:
            # 📈 SL محسّن لكل عملة (إذا متاح)
            sl_pct = self.config['max_sl_pct']
            if self.optimizer:
                try:
                    adaptive_sl = self.optimizer.get_optimal_sl(symbol)
                    if adaptive_sl != sl_pct:
                        self.logger.info(f"   📈 Adaptive SL: {sl_pct*100:.1f}% → {adaptive_sl*100:.1f}% for {symbol}")
                        sl_pct = adaptive_sl
                except Exception as e:
                    self.logger.warning(f"⚠️ Adaptive SL error: {e}")
            
            if side == 'SHORT':
                sl_price = entry_price * (1 + sl_pct)
            else:
                sl_price = entry_price * (1 - sl_pct)
        
        self.logger.info(f"   📍 OPENING {side} {symbol}: ${entry_price:.4f} | "
                        f"SL ${sl_price:.4f} | Size ${position_size:.2f} | "
                        f"Score {signal.get('score', signal.get('confidence', 0))}")
        
        # حفظ المؤشرات كـ JSON للتعلم لاحقاً
        import json as _json
        metadata_json = None
        entry_indicators = signal.get('_entry_indicators', {})
        if entry_indicators:
            try:
                metadata_json = _json.dumps({'entry_indicators': entry_indicators})
            except Exception:
                pass
        
        # ========== حفظ الصفقة وخصم الرصيد بشكل atomic ==========
        try:
            with self.db.get_write_connection() as conn:
                cursor = conn.cursor()
                
                # 1. حفظ الصفقة في قاعدة البيانات
                position_id = self.db.add_position(
                    user_id=self.user_id,
                    symbol=symbol,
                    entry_price=entry_price,
                    quantity=quantity,
                    position_size=position_size,
                    signal_type=signal.get('signal_type', 'SCALP_V7'),
                    is_demo=1 if self.is_demo_trading else 0,
                    order_id=order_id,
                    position_type=side.lower(),
                    stop_loss_price=sl_price,
                    take_profit_price=None,  # V7 uses trailing, no fixed TP
                    timeframe='1h',
                    signal_metadata=metadata_json,
                )
                
                if position_id is None:
                    conn.rollback()
                    self.logger.error(f"❌ Failed to save position {symbol} in DB - aborting (balance NOT deducted)")
                    return None
                
                # 2. خصم الرصيد
                total_deduction = position_size + entry_commission
                new_balance = balance - total_deduction
                self.db.update_user_balance(self.user_id, new_balance, self.is_demo_trading)
                
                # 3. Commit معاً - إما تنجح العمليتان أو تفشلان
                conn.commit()
                
                # 4. تحديث الحالة المحلية بعد النجاح
                self.user_portfolio['balance'] = new_balance
                self.logger.info(f"   💰 Balance deducted atomically: ${balance:.2f} → ${new_balance:.2f} (-${total_deduction:.2f})")
                
        except Exception as e:
            self.logger.error(f"❌ CRITICAL: Atomic transaction failed for {symbol}: {e}")
            self.logger.error(f"   ⛔ Position NOT saved, balance NOT deducted - transaction rolled back")
            return None
        
        # ✅ Phase 1: تسجيل الصفقة في العداد اليومي
        self.daily_state['trades_today'] += 1
        
        # ========== إرسال إشعار فتح الصفقة ==========
        try:
            self.notification_service.notify_trade_opened(
                user_id=self.user_id,
                symbol=symbol,
                position_type=side,
                entry_price=entry_price,
                quantity=quantity
            )
        except Exception as e:
            self.logger.warning(f"⚠️ فشل إرسال إشعار فتح الصفقة: {e}")
        
        return {
            'type': 'OPEN',
            'position_id': position_id,
            'symbol': symbol,
            'side': side,
            'entry_price': entry_price,
            'stop_loss': sl_price,
            'position_size': position_size,
            'signal_type': signal.get('signal_type'),
            'strategy': signal.get('strategy'),
            'score': signal.get('score'),
            'confidence': signal.get('confidence'),
        }
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """جلب السعر الحالي مع retry للأخطاء العابرة"""
        import time as _time
        max_retries = 2
        for attempt in range(max_retries):
            try:
                df = self.data_provider.get_historical_data(symbol, '1m', limit=1)
                if df is not None and len(df) > 0:
                    return float(df.iloc[-1]['close'])
                if attempt < max_retries - 1:
                    _time.sleep(1)
                    continue
                return None
            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.debug(f"⚠️ Price fetch retry {attempt+1} for {symbol}: {e}")
                    _time.sleep(1)
                    continue
                self.logger.warning(f"❌ Failed to get price for {symbol} after {max_retries} attempts: {e}")
                return None
    
    def _update_trailing_stop(self, position_id: int, new_price: float):
        """تحديث Trailing Stop"""
        try:
            self.db.update_position_trailing_stop(position_id, new_price)
        except Exception as e:
            self.logger.error(f"Error updating trailing stop: {e}")
