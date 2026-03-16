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

try:
    from backend.utils.error_logger import error_logger, ErrorLevel, ErrorSource
    ERROR_LOGGER_AVAILABLE = True
except Exception:
    ERROR_LOGGER_AVAILABLE = False


class PositionManagerMixin:
    """Mixin for position open/close/manage logic"""

    def _report_trading_error(
        self,
        message: str,
        details: str = None,
        critical: bool = False,
        requires_admin: bool = False,
        auto_action: str = None,
    ) -> None:
        """تسجيل خطأ التداول في system_errors بالإضافة إلى logs التقليدية."""
        if not ERROR_LOGGER_AVAILABLE:
            return
        try:
            level = ErrorLevel.CRITICAL if critical else ErrorLevel.ERROR
            status = 'escalated' if (critical or requires_admin) else 'new'
            error_logger.log_error(
                level=level,
                source=ErrorSource.GROUP_B,
                message=message,
                details=details,
                include_traceback=critical,
                status=status,
                requires_admin=requires_admin,
                auto_action=auto_action,
            )
        except Exception:
            # لا نكسر مسار التداول بسبب فشل تسجيل خطأ ثانوي
            pass

    def _generate_demo_order_id(self, symbol: str, side: str) -> str:
        """إنشاء معرف أمر تجريبي قريب من شكل exchange order id."""
        import uuid
        ts = int(datetime.now().timestamp())
        return f"DEMO_{side}_{symbol}_{ts}_{uuid.uuid4().hex[:8]}"

    def _quantize_demo_quantity(self, quantity: float, step_size: float) -> float:
        """تقريب كمية الأمر وفق step size (محاكاة فلاتر المنصة)."""
        if step_size <= 0:
            return quantity
        steps = int(quantity / step_size)
        return steps * step_size

    def _get_demo_symbol_rules(self, symbol: str) -> Dict:
        """جلب قواعد الرمز الفعلية من Binance exchange info لاستخدامها في demo."""
        default_rules = {
            'step': 0.001,
            'min_qty': 0.0,
            'min_notional': 10.0,
            'tick_size': 0.0001,
            'status': 'TRADING',
            'slip_min_bps': 2,
            'slip_max_bps': 12,
            'spread_fallback_bps': 2,
        }

        # تحسينات بسيطة لرموز شائعة لو فشل exchange info
        if symbol == 'BTCUSDT':
            default_rules.update({'step': 0.00001, 'tick_size': 0.01, 'slip_min_bps': 1, 'slip_max_bps': 6})
        elif symbol == 'ETHUSDT':
            default_rules.update({'step': 0.0001, 'tick_size': 0.01, 'slip_min_bps': 1, 'slip_max_bps': 8})

        try:
            if not getattr(self, 'data_provider', None):
                return default_rules

            symbol_info = self.data_provider.get_symbol_info(symbol)
            if not symbol_info:
                return default_rules

            rules = dict(default_rules)
            rules['status'] = str(symbol_info.get('status', 'TRADING')).upper()

            for f in symbol_info.get('filters', []):
                f_type = f.get('filterType')
                if f_type == 'LOT_SIZE':
                    rules['step'] = float(f.get('stepSize', rules['step']) or rules['step'])
                    rules['min_qty'] = float(f.get('minQty', rules['min_qty']) or rules['min_qty'])
                elif f_type == 'MIN_NOTIONAL':
                    rules['min_notional'] = float(f.get('minNotional', rules['min_notional']) or rules['min_notional'])
                elif f_type == 'PRICE_FILTER':
                    rules['tick_size'] = float(f.get('tickSize', rules['tick_size']) or rules['tick_size'])

            return rules
        except Exception as e:
            self.logger.debug(f"Demo rules fallback for {symbol}: {e}")
            return default_rules

    def _get_demo_execution_price(self, symbol: str, side: str, reference_price: float, spread_fallback_bps: float) -> float:
        """اختيار سعر التنفيذ الأساسي من bid/ask إن توفر، وإلا استخدام spread fallback."""
        side_upper = side.upper()
        try:
            if getattr(self, 'data_provider', None) and getattr(self.data_provider, 'client', None):
                book_ticker = self.data_provider.client.get_orderbook_ticker(symbol=symbol)
                bid = float(book_ticker.get('bidPrice', 0) or 0)
                ask = float(book_ticker.get('askPrice', 0) or 0)
                if bid > 0 and ask > 0:
                    return ask if side_upper == 'BUY' else bid
        except Exception as e:
            self.logger.debug(f"Orderbook ticker unavailable for {symbol}: {e}")

        # استخدام spread أكبر وأكثر واقعية للتداول التجريبي (10 bps = 0.1% بدلاً من 2 bps)
        # هذا يضمن اختلاف أسعار الدخول والخروج بشكل حقيقي
        spread = max(0.0, float(spread_fallback_bps or 0)) / 10000.0
        if spread < 0.0005:  # minimum 5 bps
            spread = 0.001  # 10 bps minimum for demo
            
        if side_upper == 'BUY':
            return reference_price * (1 + spread)
        return reference_price * (1 - spread)

    def _simulate_demo_fill(self, symbol: str, side: str, quantity: float, reference_price: float) -> Dict:
        """محاكاة تنفيذ Market Order للحساب التجريبي بشكل أقرب للتداول الحقيقي.

        - Slippage بسيط
        - Latency قصير
        - Quantity step-size
        - Min notional check
        """
        import random
        import time

        if reference_price <= 0 or quantity <= 0:
            return {'success': False, 'message': 'invalid_reference_price_or_quantity'}

        rules = self._get_demo_symbol_rules(symbol)
        side_upper = side.upper()

        if rules.get('status') != 'TRADING':
            return {'success': False, 'message': f"symbol_not_trading ({rules.get('status')})"}

        latency_ms = random.randint(90, 350)
        time.sleep(latency_ms / 1000.0)

        base_exec_price = self._get_demo_execution_price(
            symbol=symbol,
            side=side_upper,
            reference_price=reference_price,
            spread_fallback_bps=rules.get('spread_fallback_bps', 10),
        )
        if base_exec_price <= 0:
            return {'success': False, 'message': 'invalid_base_execution_price'}

        slip_bps = random.uniform(rules['slip_min_bps'], rules['slip_max_bps'])

        if side_upper == 'BUY':
            exec_price = base_exec_price * (1 + (slip_bps / 10000.0))
        else:
            exec_price = base_exec_price * (1 - (slip_bps / 10000.0))

        exec_qty = self._quantize_demo_quantity(quantity, rules['step'])
        if exec_qty <= 0 or exec_qty < float(rules.get('min_qty', 0) or 0):
            return {'success': False, 'message': 'quantity_below_step_size'}

        notional = exec_price * exec_qty
        min_notional = float(rules.get('min_notional', 10.0) or 10.0)
        if notional < min_notional:
            return {
                'success': False,
                'message': f'min_notional_not_met ({notional:.4f} < {min_notional:.4f})'
            }

        # Partial fills simulation: تقسيم التنفيذ إلى 1-3 تعبئات حسب حجم الكمية
        step = rules['step']
        fill_count = 1
        if exec_qty >= step * 3:
            roll = random.random()
            if roll > 0.75:
                fill_count = 3
            elif roll > 0.35:
                fill_count = 2

        fills = []
        remaining_qty = exec_qty
        total_quote = 0.0
        total_commission = 0.0

        for i in range(fill_count):
            is_last = i == (fill_count - 1)
            if is_last:
                fill_qty = remaining_qty
            else:
                min_remaining_after = step * (fill_count - i - 1)
                max_fill_qty = max(step, remaining_qty - min_remaining_after)
                raw_fill_qty = random.uniform(step, max_fill_qty)
                fill_qty = self._quantize_demo_quantity(raw_fill_qty, step)
                if fill_qty < step:
                    fill_qty = step
                if fill_qty > max_fill_qty:
                    fill_qty = self._quantize_demo_quantity(max_fill_qty, step)
                if fill_qty <= 0:
                    fill_qty = step

            remaining_qty = max(0.0, remaining_qty - fill_qty)

            # تذبذب بسيط بين التعبئات (±2 bps) حول السعر التنفيذي
            jitter_bps = random.uniform(-2.0, 2.0)
            fill_price = exec_price * (1 + (jitter_bps / 10000.0))
            fill_quote = fill_qty * fill_price
            fill_commission = fill_quote * 0.001

            total_quote += fill_quote
            total_commission += fill_commission
            fills.append({
                'price': fill_price,
                'qty': fill_qty,
                'commission': fill_commission,
            })

        if exec_qty <= 0:
            return {'success': False, 'message': 'invalid_executed_quantity'}

        avg_exec_price = total_quote / exec_qty if exec_qty > 0 else exec_price

        return {
            'success': True,
            'order_id': self._generate_demo_order_id(symbol, side_upper),
            'price': avg_exec_price,
            'quantity': exec_qty,
            'commission': total_commission,
            'fills': fills,
            'status': 'FILLED',
            'latency_ms': latency_ms,
            'slippage_bps': slip_bps,
            'fills_count': fill_count,
        }

    def _execute_real_order_with_retry(self, action: str, symbol: str, quantity: float, purpose: str) -> Dict:
        """تنفيذ أمر حقيقي مع إعادة محاولة عند الفشل.

        ملاحظة: يُستخدم فقط في مسار التداول الحقيقي.
        حساب الأدمن التجريبي/الوهمي يبقى في مساره الداخلي بدون Binance retries.
        """
        import time

        max_attempts = 3
        last_result = {}

        for attempt in range(1, max_attempts + 1):
            if action == 'buy':
                result = self.binance_manager.execute_buy_order(self.user_id, symbol, quantity)
            else:
                result = self.binance_manager.execute_sell_order(self.user_id, symbol, quantity)

            last_result = result if isinstance(result, dict) else {}
            success_with_order = last_result.get('success') and last_result.get('order_id')
            if success_with_order:
                return last_result

            message = last_result.get('message', 'unknown error')
            self.logger.warning(
                f"⚠️ Binance {purpose} attempt {attempt}/{max_attempts} failed for {symbol}: {message}"
            )

            if attempt < max_attempts:
                time.sleep(1.5)

        return {
            'success': False,
            'message': (
                f"Binance {purpose} failed after {max_attempts} attempts: "
                f"{last_result.get('message', 'unknown error')}"
            ),
        }

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
                
                # V8: persist breakeven SL updates
                if updated.get('sl'):
                    self._update_stop_loss(position_id, updated['sl'])
                
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
                                entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                            except Exception:
                                entry_time = None
                        if isinstance(entry_time, datetime):
                            now_dt = datetime.now(entry_time.tzinfo) if entry_time.tzinfo else datetime.now()
                            hold_hours = (now_dt - entry_time).total_seconds() / 3600

                    self.logger.info(
                        f"   🚪 [{symbol}] Exit: {exit_result['reason']} | "
                        f"Price: ${exit_price:.4f} | Hold: {hold_hours:.1f}h"
                    )

                    return self._close_position(position, exit_price, reason, 1.0)
                else:
                    # V8: persist SL/trail updates even when holding
                    if updated.get('sl'):
                        self._update_stop_loss(position_id, updated['sl'])
                    
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
            # Demo: محاكاة تنفيذ أقرب للواقع (سعر/انزلاق/زمن/عمولة)
            demo_close_side = 'SELL' if position_type != 'SHORT' else 'BUY'
            demo_close_fill = self._simulate_demo_fill(symbol, demo_close_side, quantity, exit_price)
            if not demo_close_fill.get('success'):
                self.logger.warning(
                    f"⚠️ Demo close simulation failed for {symbol}: {demo_close_fill.get('message')}"
                )
                return None

            exit_price = float(demo_close_fill.get('price', exit_price))
            exit_commission = float(demo_close_fill.get('commission', 0))
            exit_order_id = str(demo_close_fill.get('order_id', ''))

            # إعادة حساب PnL بعد سعر التنفيذ المحاكى
            if position_type == 'SHORT':
                pnl_raw = (entry_price - exit_price) * quantity
            else:
                pnl_raw = (exit_price - entry_price) * quantity

            # ✅ FIX: عمولة الدخول خُصمت بالفعل من الرصيد عند الفتح (total_deduction = position_size + entry_commission)
            # لذلك نخصم فقط عمولة الخروج من PnL الخام — لا نخصم عمولة الدخول مرة أخرى
            pnl = pnl_raw - exit_commission
            # ✅ النسبة المئوية الفعلية بعد عمولة الخروج فقط
            pnl_pct = pnl / position_size_entry if position_size_entry > 0 else 0
            self.logger.info(
                f"   💰 Demo Exit Fill: ${exit_price:.4f} | Commission ${exit_commission:.4f} "
                f"(Entry commission ${entry_commission:.4f} already deducted at open)"
            )
        else:
            # 💱 تنفيذ إغلاق حقيقي على Binance
            if self.binance_manager:
                self.logger.info(f"   💱 Executing REAL close on Binance: {position_type} {symbol} qty={quantity:.6f}")
                
                if position_type == 'LONG':
                    close_result = self._execute_real_order_with_retry('sell', symbol, quantity, 'close')
                else:
                    close_result = self._execute_real_order_with_retry('buy', symbol, quantity, 'close')
                
                if close_result.get('success'):
                    if not close_result.get('order_id'):
                        self.logger.error(
                            "⛔ Binance close returned without order_id — keep position open in DB"
                        )
                        return None
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
                        "position remains OPEN in DB"
                    )
                    self._report_trading_error(
                        message="Binance close failed",
                        details=f"user_id={self.user_id}, symbol={symbol}, message={close_result.get('message')}",
                        critical=False,
                        requires_admin=False,
                        auto_action="retry_close_order",
                    )
                    return None
            
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
                # 1. إغلاق في قاعدة البيانات (على نفس الاتصال)
                self.db.close_position_on_conn(conn, position_id, exit_price, reason, pnl,
                                               exit_commission=exit_commission,
                                               exit_order_id=exit_order_id)
                
                # 2. تحديث رصيد المحفظة (على نفس الاتصال)
                current_balance = self.user_portfolio.get('balance', 0)
                returned_amount = position_size_entry + pnl
                new_balance = current_balance + returned_amount
                self.db.update_user_balance_on_conn(conn, self.user_id, new_balance, self.is_demo_trading)
                
                # 3. get_write_connection يعمل commit تلقائياً عند الخروج بنجاح
                #    وrollback تلقائياً عند حدوث exception — ذرية حقيقية
                
                # 4. تحديث الحالة المحلية بعد النجاح
                self.user_portfolio['balance'] = new_balance
                self.logger.info(f"   💰 Balance updated atomically: ${current_balance:.2f} → ${new_balance:.2f} (returned ${position_size_entry:.2f} + PnL {pnl:+.2f})")
                
        except Exception as e:
            self.logger.error(f"❌ CRITICAL: Atomic transaction failed for closing {symbol}: {e}")
            self.logger.error(f"   ⛔ Position NOT closed, balance NOT updated - transaction rolled back")
            self._report_trading_error(
                message="Atomic close transaction failed",
                details=f"user_id={self.user_id}, symbol={symbol}, error={e}",
                critical=True,
                requires_admin=True,
                auto_action="check_db_integrity",
            )
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
                    entry_dt = entry_time
                    if isinstance(entry_time, str):
                        try:
                            entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                        except Exception:
                            entry_dt = None
                    if isinstance(entry_dt, datetime):
                        now_dt = datetime.now(entry_dt.tzinfo) if entry_dt.tzinfo else datetime.now()
                        hold_min = int((now_dt - entry_dt).total_seconds() / 60)
                
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
                exit_reason=reason,
                trade_id=position_id  # ✅ تمرير معرف الصفقة
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

            # تدريب دوري تلقائي كل دفعة صفقات مغلقة
            cycle_size = len(self.ml_training_manager.current_cycle_data)
            if cycle_size >= 20:
                train_result = self.ml_training_manager.end_cycle_and_train()
                if train_result.get('success'):
                    self.logger.info(
                        f"🧠 Periodic ML training completed | "
                        f"accuracy={train_result.get('accuracy', 0):.2%} | "
                        f"ready={train_result.get('is_ready', False)}"
                    )
                else:
                    self.logger.info(
                        f"🧠 Periodic ML training skipped/failed | "
                        f"reason={train_result.get('reason') or train_result.get('error', 'unknown')}"
                    )
                self.ml_training_manager.start_cycle()
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
            # Demo: محاكاة تنفيذ أقرب للواقع (سعر/انزلاق/زمن/عمولة)
            demo_open_side = 'BUY' if side != 'SHORT' else 'SELL'
            demo_open_fill = self._simulate_demo_fill(symbol, demo_open_side, quantity, entry_price)
            if not demo_open_fill.get('success'):
                self.logger.warning(
                    f"⚠️ Demo open simulation failed for {symbol}: {demo_open_fill.get('message')}"
                )
                return None

            entry_price = float(demo_open_fill.get('price', entry_price))
            quantity = float(demo_open_fill.get('quantity', quantity))
            position_size = entry_price * quantity
            entry_commission = float(demo_open_fill.get('commission', 0))
            order_id = str(demo_open_fill.get('order_id', ''))

            self.logger.info(
                f"   💰 Demo Entry Fill: ${entry_price:.4f} qty={quantity:.6f} "
                f"commission=${entry_commission:.4f} order_id={order_id}"
            )
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
                result = self._execute_real_order_with_retry('buy', symbol, quantity, 'open')
            else:
                result = self._execute_real_order_with_retry('sell', symbol, quantity, 'open')
            
            if not result.get('success'):
                self.logger.error(f"⛔ Binance order FAILED: {result.get('message', 'unknown error')}")
                self._report_trading_error(
                    message="Binance open order failed",
                    details=f"user_id={self.user_id}, symbol={symbol}, side={side}, message={result.get('message', 'unknown error')}",
                    critical=False,
                    requires_admin=False,
                    auto_action="retry_open_order",
                )
                return None

            if not result.get('order_id'):
                self.logger.error("⛔ Binance order missing order_id — trade considered NOT executed")
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
                # 1. حفظ الصفقة في قاعدة البيانات
                position_id = self.db.add_position_on_conn(
                    conn=conn,
                    user_id=self.user_id,
                    symbol=symbol,
                    entry_price=entry_price,
                    quantity=quantity,
                    position_size=position_size,
                    signal_type=signal.get('signal_type', 'SCALP_V8'),
                    is_demo=1 if self.is_demo_trading else 0,
                    order_id=order_id,
                    position_type=side.lower(),
                    stop_loss_price=sl_price,
                    take_profit_price=None,  # V7 uses trailing, no fixed TP
                    timeframe='1h',
                    signal_metadata=metadata_json,
                    entry_commission=entry_commission,
                )
                
                if position_id is None:
                    self.logger.warning(f"⚠️ Position {symbol} not saved — duplicate or constraint violation (balance NOT deducted)")
                    return None
                
                # 2. خصم الرصيد
                total_deduction = position_size + entry_commission
                new_balance = balance - total_deduction
                self.db.update_user_balance_on_conn(conn, self.user_id, new_balance, self.is_demo_trading)
                
                # 4. تحديث الحالة المحلية بعد النجاح
                self.user_portfolio['balance'] = new_balance
                self.logger.info(f"   💰 Balance deducted atomically: ${balance:.2f} → ${new_balance:.2f} (-${total_deduction:.2f})")
                
        except Exception as e:
            self.logger.error(f"❌ CRITICAL: Atomic transaction failed for {symbol}: {e}")
            self.logger.error(f"   ⛔ Position NOT saved, balance NOT deducted - transaction rolled back")
            self._report_trading_error(
                message="Atomic open transaction failed",
                details=f"user_id={self.user_id}, symbol={symbol}, error={e}",
                critical=True,
                requires_admin=True,
                auto_action="check_db_write_path",
            )
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
                quantity=quantity,
                trade_id=position_id  # ✅ تمرير معرف الصفقة
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

    def _update_stop_loss(self, position_id: int, new_sl: float):
        """تحديث Stop Loss (V8 breakeven)"""
        try:
            with self.db.get_write_connection() as conn:
                conn.execute(
                    "UPDATE active_positions SET stop_loss = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (new_sl, position_id))
            self.logger.debug(f"   🛡️ SL updated to ${new_sl:.4f} (breakeven)")
        except Exception as e:
            self.logger.error(f"Error updating stop loss: {e}")
