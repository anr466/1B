"""
Mobile Settings Routes — extracted from mobile_endpoints.py (God Object split)
===============================================================================
Routes: /settings, /settings/validate, /settings/trading-mode, /binance-keys, /profile, /reset-data
"""

from flask import request, jsonify, g
from datetime import datetime, timedelta
import json
import logging
import os
import re

from backend.utils.trading_context import get_trading_context

logger = logging.getLogger(__name__)


def register_mobile_settings_routes(bp, shared):
    """Register settings-related routes on the mobile blueprint"""
    db_manager = shared['db_manager']
    verify_user_access = shared['verify_user_access']
    require_auth = shared['require_auth']
    rate_limit_general = shared.get('rate_limit_general', lambda f: f)
    rate_limit_trading = shared.get('rate_limit_trading', lambda f: f)
    rate_limit_auth = shared.get('rate_limit_auth', lambda f: f)
    success_response = shared['success_response']
    error_response = shared['error_response']
    require_idempotency = shared.get('require_idempotency', lambda *a: (lambda f: f))
    prevent_concurrent_duplicates = shared.get('prevent_concurrent_duplicates', lambda f: f)
    CACHE_AVAILABLE = shared.get('CACHE_AVAILABLE', False)
    response_cache = shared.get('response_cache', None)
    ENCRYPTION_AVAILABLE = shared.get('ENCRYPTION_AVAILABLE', False)
    audit_logger = shared.get('audit_logger', None)

    def load_api_permissions(client):
        if hasattr(client, 'get_api_key_permission'):
            return client.get_api_key_permission()
        if hasattr(client, 'get_account_api_permissions'):
            return client.get_account_api_permissions()
        raise AttributeError('Binance client permissions API is unavailable')

    def resolve_key_state(db, user_id: int, is_admin: bool, is_demo: bool):
        db_rows = db.execute_query(
            "SELECT COUNT(*) as count FROM user_binance_keys WHERE user_id = %s AND is_active = TRUE",
            (user_id,),
        )
        has_configured_db_keys = bool(db_rows and db_rows[0].get('count', 0) > 0)
        env_keys_enabled = (os.getenv('ALLOW_ENV_BINANCE_KEYS_FOR_TESTING') or '').strip().lower() in ('1', 'true', 'yes', 'on')
        env_api_key = (os.getenv('BINANCE_BACKEND_API_KEY') or '').strip()
        env_api_secret = (os.getenv('BINANCE_BACKEND_API_SECRET') or '').strip()
        using_env_test_keys = bool(env_keys_enabled and env_api_key and env_api_secret and not has_configured_db_keys)
        resolved_keys = db.get_binance_keys(user_id)
        actual_has_keys = bool(resolved_keys and resolved_keys.get('api_key'))
        keys_required_for_current_mode = not (is_admin and is_demo)
        logical_has_keys = True if not keys_required_for_current_mode else actual_has_keys
        return {
            'has_binance_keys': logical_has_keys,
            'has_configured_db_keys': has_configured_db_keys,
            'using_env_test_keys': using_env_test_keys,
            'keys_required_for_current_mode': keys_required_for_current_mode,
            'actual_has_keys': actual_has_keys,
        }

    # ==================== إعدادات التداول (Settings) ====================

    @bp.route('/settings/<int:user_id>', methods=['GET'])
    @require_auth
    @rate_limit_general
    def get_user_settings(user_id):
        """الحصول على إعدادات التداول - عزل كامل"""
        if not verify_user_access(user_id):
            response_data, status_code = error_response('لا توجد صلاحيات', 'UNAUTHORIZED', 403)
            return jsonify(response_data), status_code

        try:
            db = db_manager

            requested_mode = request.args.get('mode')
            trading_context = get_trading_context(db, user_id, requested_mode=requested_mode)
            is_admin = trading_context['is_admin']
            current_mode = trading_context['trading_mode']
            is_demo = bool(trading_context['is_demo'])

            # ✅ للأدمن: قراءة الإعدادات حسب المحفظة النشطة (trading_mode)
            if is_admin:
                # قراءة الإعدادات الخاصة بالمحفظة النشطة
                settings_query = """
                    SELECT trading_enabled, trade_amount, position_size_percentage,
                           risk_level, stop_loss_pct, trailing_distance,
                           take_profit_pct, max_positions, trading_mode, is_demo,
                           max_daily_loss_pct
                    FROM user_settings 
                    WHERE user_id = %s AND is_demo = %s
                    LIMIT 1
                """
                result = db.execute_query(settings_query, (user_id, is_demo))
            else:
                # ✅ للمستخدمين العاديين: قراءة إعدادات Real فقط
                settings_query = """
                    SELECT trading_enabled, trade_amount, position_size_percentage,
                           risk_level, stop_loss_pct, trailing_distance,
                           take_profit_pct, max_positions, trading_mode, is_demo,
                           max_daily_loss_pct
                    FROM user_settings 
                    WHERE user_id = %s AND is_demo = FALSE
                    LIMIT 1
                """
                result = db.execute_query(settings_query, (user_id, ))

            if not result:
                effective_is_demo = is_demo if is_admin else False
                with db.get_write_connection() as conn:
                    conn.execute(
                        """
                        INSERT INTO user_settings (user_id, is_demo, trading_mode)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id, is_demo) DO NOTHING
                        """,
                        (user_id, effective_is_demo, 'demo' if effective_is_demo else 'real'),
                    )
                    conn.commit()
                result = db.execute_query(
                    settings_query,
                    (user_id, is_demo) if is_admin else (user_id,),
                )

            if not result:
                response_data, status_code = error_response(
                    'تعذر تحميل إعدادات المستخدم',
                    'SETTINGS_NOT_FOUND',
                    500,
                )
                return jsonify(response_data), status_code

            s = result[0]
            effective_mode = current_mode if is_admin else 'real'
            effective_is_demo = is_demo if is_admin else False

            def as_float(value, fallback=0.0):
                try:
                    return float(value) if value is not None else fallback
                except (TypeError, ValueError):
                    return fallback

            def as_int(value, fallback=0):
                try:
                    return int(value) if value is not None else fallback
                except (TypeError, ValueError):
                    return fallback

            # ✅ فحص وجود مفاتيح Binance
            key_state = resolve_key_state(db, user_id, is_admin, effective_is_demo)

            data = {
                'tradingEnabled': bool(s.get('trading_enabled')),
                'tradeAmount': as_float(s.get('trade_amount')),
                'positionSizePercentage': as_float(s.get('position_size_percentage')),
                'riskLevel': s.get('risk_level') or 'medium',
                'stopLossPercentage': as_float(s.get('stop_loss_pct')),
                'takeProfitPercentage': as_float(s.get('take_profit_pct')),
                'trailingDistance': as_float(s.get('trailing_distance')),
                'maxDailyLossPct': as_float(s.get('max_daily_loss_pct')),
                'maxConcurrentTrades': as_int(s.get('max_positions')),
                'tradingMode': effective_mode,
                'activePortfolio': 'demo' if effective_is_demo else 'real',
                'canToggle': is_admin,
                'hasBinanceKeys': key_state['has_binance_keys'],
                'hasConfiguredDbKeys': key_state['has_configured_db_keys'],
                'usingEnvTestKeys': key_state['using_env_test_keys'],
                'keysRequiredForCurrentMode': key_state['keys_required_for_current_mode'],
            }
            response_data, status_code = success_response(data, 'تم جلب الإعدادات بنجاح')
            return jsonify(response_data), status_code
        except Exception as e:
            logger.error(f"❌ خطأ Settings {user_id}: {e}")
            response_data, status_code = error_response('خطأ في جلب الإعدادات', 'SETTINGS_ERROR', 500)
            return jsonify(response_data), status_code


    @bp.route('/settings/<int:user_id>/validate', methods=['POST'])
    @require_auth
    @rate_limit_general
    def validate_trading_settings(user_id):
        """
        التحقق من صحة إعدادات التداول وفحص المتطلبات

        Returns:
            Dict: {
                'can_trade': bool,
                'reason': str,
                'has_keys': bool,
                'sufficient_balance': bool,
                'current_positions': int,
                'max_allowed_positions': int,
                'available_balance': float,
                'required_amount': float,
                'validation_errors': List[str]
            }
        """
        if not verify_user_access(user_id):
            response_data, status_code = error_response('لا توجد صلاحيات', 'UNAUTHORIZED', 403)
            return jsonify(response_data), status_code

        try:
            from backend.core.group_b_system import GroupBSystem

            requested_mode = request.args.get('mode')

            group_b = GroupBSystem(user_id, requested_mode=requested_mode)

            # 1. فحص المتطلبات الأساسية
            settings = group_b.user_settings
            portfolio = group_b.user_portfolio
            balance = portfolio.get('balance', 0)
            risk_balance = portfolio.get('total_value', balance)
            key_state = resolve_key_state(db_manager, user_id, getattr(g, 'current_user_type', None) == 'admin', group_b.is_demo_trading)
            actual_has_keys = key_state['actual_has_keys']
            keys_required = not group_b.is_demo_trading
            has_keys = key_state['has_binance_keys']
            open_positions = group_b._get_open_positions()

            position_size_pct = settings.get('position_size_percentage', 0)
            max_positions = settings.get('max_positions', 0)

            # 2. فحص بوابات الحماية
            can_trade_gate, gate_reason = group_b._check_risk_gates(open_positions, risk_balance)

            # 3. حساب حجم الصفقة
            position_size = group_b._calculate_position_size(balance) if balance > 0 else 0

            # 4. تحديد الأخطاء والتحذيرات
            errors = []
            warnings = []

            if keys_required and not actual_has_keys:
                errors.append('مفاتيح Binance غير مضافة')
            if balance < 10:
                errors.append(f'الرصيد غير كافٍ: ${balance:.2f} (الحد الأدنى $10)')
            if position_size_pct <= 0:
                errors.append('نسبة حجم الصفقة غير محددة')
            if max_positions <= 0:
                errors.append('الحد الأقصى للصفقات غير محدد')
            if not can_trade_gate and gate_reason != "OK":
                warnings.append(f'بوابة الحماية: {gate_reason}')

            can_trade = len(errors) == 0 and settings.get('trading_enabled', False)
            reason = 'جاهز للتداول' if can_trade else (errors[0] if errors else 'التداول معطّل')

            data = {
                'can_trade': can_trade,
                'reason': reason,
                'has_keys': has_keys,
                'hasConfiguredDbKeys': key_state['has_configured_db_keys'],
                'usingEnvTestKeys': key_state['using_env_test_keys'],
                'keysRequiredForCurrentMode': key_state['keys_required_for_current_mode'],
                'sufficient_balance': balance >= 10,
                'current_positions': len(open_positions),
                'max_allowed_positions': max_positions,
                'available_balance': balance,
                'required_amount': position_size,
                'validation_errors': errors,
                'validation_warnings': warnings,
            }

            response_data, status_code = success_response(data, 'تم التحقق من متطلبات التداول')
            return jsonify(response_data), status_code

        except Exception as e:
            logger.error(f"❌ خطأ في التحقق من إعدادات التداول {user_id}: {e}")
            response_data, status_code = error_response('خطأ في التحقق من الإعدادات', 'VALIDATION_ERROR', 500)
            return jsonify(response_data), status_code


    @bp.route('/settings/<int:user_id>', methods=['PUT'])
    @require_auth
    @rate_limit_trading
    @prevent_concurrent_duplicates
    @require_idempotency('update_settings')
    def update_user_settings(user_id):
        """تحديث إعدادات التداول - عزل كامل + Validation للحد اليومي + إبطال Cache"""
        if not verify_user_access(user_id):
            response_data, status_code = error_response('لا توجد صلاحيات', 'UNAUTHORIZED', 403)
            return jsonify(response_data), status_code

        try:
            db = db_manager
            data = request.get_json(silent=True) or {}
            requested_mode = request.args.get('mode')

            # ═══════════════════════════════════════════════════════════════
            # ✅ FIX: تطبيع أسماء الحقول — القبول بـ snake_case و camelCase
            # Frontend interceptor يحوّل كل المفاتيح إلى snake_case تلقائياً
            # لكن الكود أدناه يقرأ camelCase — لذلك نطبّع هنا
            # ═══════════════════════════════════════════════════════════════
            if data:
                normalized = {}
                for key, value in data.items():
                    camel_key = re.sub(r'_([a-z])', lambda m: m.group(1).upper(), key)
                    normalized[camel_key] = value
                    if key != camel_key:
                        normalized[key] = value  # نحتفظ بالمفتاح الأصلي أيضاً
                data = normalized

            # ═══════════════════════════════════════════════════════════════
            # ✅ التحقق من صحة البيانات المدخلة (Input Validation)
            # ═══════════════════════════════════════════════════════════════

            # التحقق من tradeAmount
            if 'tradeAmount' in data:
                try:
                    trade_amount_val = float(data['tradeAmount'])
                    if trade_amount_val < 5 or trade_amount_val > 10000:
                        return jsonify({
                            'success': False,
                            'error': 'مبلغ التداول يجب أن يكون بين 5 و 10000 USDT',
                            'error_code': 'INVALID_TRADE_AMOUNT'
                        }), 400
                    data['tradeAmount'] = trade_amount_val
                except (ValueError, TypeError):
                    return jsonify({
                        'success': False,
                        'error': 'مبلغ التداول يجب أن يكون رقماً صحيحاً',
                        'error_code': 'INVALID_TRADE_AMOUNT'
                    }), 400

            # التحقق من maxConcurrentTrades
            if 'maxConcurrentTrades' in data:
                try:
                    max_trades_val = int(data['maxConcurrentTrades'])
                    if max_trades_val < 1 or max_trades_val > 20:
                        return jsonify({
                            'success': False,
                            'error': 'عدد الصفقات المتزامنة يجب أن يكون بين 1 و 20',
                            'error_code': 'INVALID_MAX_TRADES'
                        }), 400
                    data['maxConcurrentTrades'] = max_trades_val
                except (ValueError, TypeError):
                    return jsonify({
                        'success': False,
                        'error': 'عدد الصفقات يجب أن يكون رقماً صحيحاً',
                        'error_code': 'INVALID_MAX_TRADES'
                    }), 400

            # التحقق من stopLossPercentage
            if 'stopLossPercentage' in data:
                try:
                    sl_val = float(data['stopLossPercentage'])
                    if sl_val < 0.5 or sl_val > 10:
                        return jsonify({
                            'success': False,
                            'error': 'نسبة وقف الخسارة يجب أن تكون بين 0.5% و 10%',
                            'error_code': 'INVALID_STOP_LOSS'
                        }), 400
                    data['stopLossPercentage'] = sl_val
                except (ValueError, TypeError):
                    return jsonify({
                        'success': False,
                        'error': 'نسبة وقف الخسارة يجب أن تكون رقماً',
                        'error_code': 'INVALID_STOP_LOSS'
                    }), 400

            # التحقق من takeProfitPercentage
            if 'takeProfitPercentage' in data:
                try:
                    tp_val = float(data['takeProfitPercentage'])
                    if tp_val < 1 or tp_val > 50:
                        return jsonify({
                            'success': False,
                            'error': 'نسبة جني الأرباح يجب أن تكون بين 1% و 50%',
                            'error_code': 'INVALID_TAKE_PROFIT'
                        }), 400
                    data['takeProfitPercentage'] = tp_val
                except (ValueError, TypeError):
                    return jsonify({
                        'success': False,
                        'error': 'نسبة جني الأرباح يجب أن تكون رقماً',
                        'error_code': 'INVALID_TAKE_PROFIT'
                    }), 400

            # ═══════════════════════════════════════════════════════════════
            # ✅ فحص شروط تفعيل التداول
            # ═══════════════════════════════════════════════════════════════
            trading_enabled = data.get('tradingEnabled', False)

            if trading_enabled:
                # ✅ فحص نوع المستخدم ووضع التداول لتحديد الاستثناءات
                # ملاحظة: حجم الصفقة وعدد المراكز يتحكم فيها backend تلقائياً — لا نتحقق منها هنا
                user_type_query = "SELECT user_type FROM users WHERE id = %s"
                user_type_result = db.execute_query(user_type_query, (user_id,))
                is_admin_user = user_type_result[0]['user_type'] == 'admin' if user_type_result else False

                # ✅ جلب وضع التداول الحالي
                current_context = get_trading_context(db, user_id, requested_mode=requested_mode)
                current_mode = current_context['trading_mode']
                current_is_demo = bool(current_context['is_demo'])

                # ✅ استثناء الأدمن في الوضع التجريبي: لا يحتاج مفاتيح Binance
                skip_binance_check = is_admin_user and current_is_demo

                if not skip_binance_check:
                    # 1️⃣ فحص وجود مفاتيح Binance (مطلوب للتداول الحقيقي)
                    keys_query = "SELECT api_key, api_secret FROM user_binance_keys WHERE user_id = %s AND is_active = TRUE"
                    keys_result = db.execute_query(keys_query, (user_id,))
                    has_keys = keys_result and len(keys_result) > 0 and keys_result[0].get('api_key')

                    if not has_keys:
                        return jsonify({
                            'success': False,
                            'error': 'لا يمكن تفعيل التداول بدون ربط حساب Binance',
                            'error_code': 'NO_BINANCE_KEYS',
                            'message': '🔑 يرجى إضافة مفاتيح Binance API أولاً من إعدادات التداول',
                            'action_required': 'add_binance_keys'
                        }), 400

                # 2️⃣ ✅ جلب الرصيد - من DB للتجريبي، من Binance للحقيقي
                # trade_amount: يُقرأ من DB إذا لم يُرسَل في الطلب (backend يتحكم فيه)
                if 'tradeAmount' in data:
                    trade_amount = float(data['tradeAmount'])
                else:
                    _amt_q = "SELECT trade_amount FROM user_settings WHERE user_id = %s AND is_demo = %s"
                    _amt_r = db.execute_query(_amt_q, (user_id, current_is_demo))
                    trade_amount = float(_amt_r[0]['trade_amount'] or 100.0) if _amt_r else 100.0
                available_balance = 0.0
                binance_error = None

                if skip_binance_check:
                    # ✅ الأدمن في الوضع التجريبي: جلب الرصيد من قاعدة البيانات
                    demo_query = "SELECT available_balance FROM portfolio WHERE user_id = %s AND is_demo = TRUE"
                    demo_result = db.execute_query(demo_query, (user_id,))
                    available_balance = float(demo_result[0]['available_balance'] or 0) if demo_result else 0.0
                    logger.info(f"✅ Demo balance for admin {user_id}: {available_balance:.2f} USDT")
                else:
                    try:
                        from backend.utils.binance_balance_checker import BinanceBalanceChecker
                        balance_checker = BinanceBalanceChecker(user_id)
                        balance_result = balance_checker.get_available_balance()

                        if balance_result.get('success'):
                            available_balance = float(balance_result.get('free_usdt', 0))
                            logger.info(f"✅ جلب رصيد Binance للمستخدم {user_id}: {available_balance:.2f} USDT")
                        else:
                            binance_error = balance_result.get('error', 'خطأ في الاتصال بـ Binance')
                    except ImportError:
                        logger.error(f"❌ BinanceBalanceChecker غير متاح — لا يمكن التحقق من الرصيد")
                        binance_error = 'خدمة فحص الرصيد غير متاحة حالياً. يرجى المحاولة لاحقاً.'
                    except Exception as e:
                        binance_error = str(e)
                        logger.error(f"❌ خطأ في جلب رصيد Binance: {e}")

                # إذا فشل الاتصال بـ Binance
                if binance_error:
                    return jsonify({
                        'success': False,
                        'error': 'فشل التحقق من رصيد Binance',
                        'error_code': 'BINANCE_CONNECTION_ERROR',
                        'message': f'⚠️ لم نتمكن من التحقق من رصيدك في Binance.\n\n{binance_error}\n\nتأكد من صحة مفاتيح API وأنها تملك صلاحية القراءة.',
                        'action_required': 'check_binance_keys'
                    }), 400

                # 3️⃣ فحص الرصيد الحر الكافي
                if available_balance < trade_amount:
                    return jsonify({
                        'success': False,
                        'error': 'الرصيد المتاح غير كافٍ',
                        'error_code': 'INSUFFICIENT_BALANCE',
                        'message': f'💰 رصيدك الحر في Binance ({available_balance:.2f} USDT) أقل من مبلغ التداول ({trade_amount:.2f} USDT).\n\nيرجى إيداع المزيد في حساب Binance الخاص بك أو تقليل مبلغ التداول.',
                        'available_balance': available_balance,
                        'required_amount': trade_amount,
                        'action_required': 'deposit_funds'
                    }), 400

                # 4️⃣ فحص المراكز المفتوحة (للتحذير فقط)
                # ✅ FIX: user_trades لا يحتوي status='open' — استخدام active_positions WHERE is_active=1
                positions_query = """
                    SELECT COUNT(*) as count, SUM(COALESCE(quantity * entry_price, 0)) as locked_amount
                    FROM active_positions 
                    WHERE user_id = %s AND is_active = TRUE AND is_demo = %s
                """
                positions_result = db.execute_query(positions_query, (user_id, current_is_demo))
                open_positions = positions_result[0]['count'] if positions_result else 0
                locked_amount = positions_result[0]['locked_amount'] or 0 if positions_result else 0

                # إذا كان هناك مراكز مفتوحة، نضيف تحذير (لكن نسمح بالتفعيل)
                if open_positions > 0:
                    logger.info(f"⚠️ المستخدم {user_id} يفعّل التداول مع {open_positions} مراكز مفتوحة (مبلغ مقفل: {locked_amount:.2f} USDT)")

                logger.info(f"✅ المستخدم {user_id}: تفعيل التداول - رصيد حر: {available_balance:.2f} USDT")

            # ✅ Validation لحد الخسارة اليومي — لا نكتبه إلا إذا أُرسِل صراحةً في الطلب
            _raw_mdl = data.get('maxDailyLoss') or data.get('maxDailyLossPct') or data.get('max_daily_loss_pct')
            max_daily_loss = float(_raw_mdl) if _raw_mdl is not None else None
            if max_daily_loss is not None:
                # فرض الحدود من النظام (5%-15%)
                if max_daily_loss < 5.0:
                    logger.warning(f"⚠️ المستخدم {user_id}: حد الخسارة اليومي أقل من 5%، تم التعديل")
                    max_daily_loss = 5.0
                elif max_daily_loss > 15.0:
                    logger.warning(f"⚠️ المستخدم {user_id}: حد الخسارة اليومي أكبر من 15%، تم التعديل")
                    max_daily_loss = 15.0

            # ✅ تحديد المحفظة المستهدفة (للأدمن حسب trading_mode، للمستخدمين دائماً وهمية)
            user_query = "SELECT user_type FROM users WHERE id = %s"
            user_result = db.execute_query(user_query, (user_id,))
            is_admin = user_result[0]['user_type'] == 'admin' if user_result else False

            if is_admin:
                # جلب trading_mode الحالي لتحديد المحفظة المستهدفة
                target_context = get_trading_context(db, user_id, requested_mode=requested_mode)
                current_mode = target_context['trading_mode']
                target_is_demo = bool(target_context['is_demo'])
            else:
                target_is_demo = False  # ✅ المستخدمون العاديون دائماً Real
                current_mode = 'real'

            # فحص وجود إعدادات للمحفظة المستهدفة
            check_query = "SELECT id FROM user_settings WHERE user_id = %s AND is_demo = %s"
            existing = db.execute_query(check_query, (user_id, target_is_demo))
            stop_loss_value = data.get('stopLossPercentage') or data.get('stopLossPct') or data.get('stop_loss_pct', 3.0)
            take_profit_value = data.get('takeProfitPercentage') or data.get('takeProfitPct') or data.get('take_profit_pct', 6.0)
            effective_mode = current_mode if is_admin else 'real'
            normalized_response = {
                'tradingEnabled': bool(data.get('tradingEnabled', False)),
                'tradeAmount': float(data.get('tradeAmount', 100.0)),
                'positionSizePercentage': float(data.get('positionSizePercentage', 10.0)),
                'riskLevel': data.get('riskLevel', 'medium'),
                'stopLossPercentage': float(stop_loss_value),
                'takeProfitPercentage': float(take_profit_value),
                'trailingDistance': float(data.get('trailingDistance', 3.0)),
                'maxDailyLossPct': float(max_daily_loss) if max_daily_loss is not None else None,
                'maxConcurrentTrades': int(data.get('maxConcurrentTrades', 5)),
                'tradingMode': effective_mode,
                'activePortfolio': 'demo' if target_is_demo else 'real',
                'canToggle': is_admin,
            }

            if existing and len(existing) > 0:
                # ✅ تحديث فقط الحقول الموجودة في الطلب — لا نكتب defaults للحقول غير المرسلة
                field_map = {}
                if 'tradingEnabled' in data:
                    field_map['trading_enabled'] = bool(data['tradingEnabled'])
                if 'tradeAmount' in data:
                    field_map['trade_amount'] = float(data['tradeAmount'])
                if 'positionSizePercentage' in data:
                    field_map['position_size_percentage'] = float(data['positionSizePercentage'])
                if 'riskLevel' in data:
                    field_map['risk_level'] = str(data['riskLevel'])
                if any(k in data for k in ('stopLossPercentage', 'stopLossPct', 'stop_loss_pct')):
                    field_map['stop_loss_pct'] = float(stop_loss_value)
                if any(k in data for k in ('takeProfitPercentage', 'takeProfitPct', 'take_profit_pct')):
                    field_map['take_profit_pct'] = float(take_profit_value)
                if 'trailingDistance' in data:
                    field_map['trailing_distance'] = float(data['trailingDistance'])
                if 'maxConcurrentTrades' in data:
                    field_map['max_positions'] = int(data['maxConcurrentTrades'])
                if max_daily_loss is not None:
                    field_map['max_daily_loss_pct'] = float(max_daily_loss)
                field_map['trading_mode'] = effective_mode  # دائماً نحدّث وضع التداول
                set_clauses = ', '.join(f"{k} = %s" for k in field_map.keys())
                update_query = f"""
                    UPDATE user_settings
                    SET {set_clauses}, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND is_demo = %s
                """
                db.execute_query(update_query, (*field_map.values(), user_id, target_is_demo))
            else:
                # إنشاء إعدادات جديدة للمحفظة المستهدفة
                insert_query = """
                    INSERT INTO user_settings (user_id, is_demo, trading_enabled, trade_amount,
                        position_size_percentage, stop_loss_pct, take_profit_pct, trailing_distance,
                        max_positions, risk_level, max_daily_loss_pct, trading_mode, 
                        created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
                db.execute_query(insert_query, (
                    user_id, target_is_demo,
                    bool(data.get('tradingEnabled', False)),
                    float(data.get('tradeAmount', 100.0)),
                    float(data.get('positionSizePercentage', 12.0)),  # backend default: 12%
                    float(data.get('stopLossPercentage', data.get('stopLossPct', 1.0))),  # backend default: 1%
                    float(data.get('takeProfitPercentage', data.get('takeProfitPct', 2.0))),  # backend default: 2%
                    float(data.get('trailingDistance', 0.4)),  # backend default: 0.4%
                    int(data.get('maxConcurrentTrades', 5)),
                    str(data.get('riskLevel', 'medium')),
                    float(max_daily_loss) if max_daily_loss is not None else 3.0,  # backend enforces 3%
                    effective_mode
                ))
                if not target_is_demo:
                    initial_balance = 0.0
                    db.execute_query(
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
                        (user_id, initial_balance, initial_balance, initial_balance, target_is_demo, user_id, target_is_demo)
                    )

            # ✅ إبطال Cache بعد التحديث - جميع بيانات المستخدم
            if CACHE_AVAILABLE:
                response_cache.invalidate_user_cache(user_id)
                logger.debug(f"🗑️ تم إبطال Cache الكامل - المستخدم {user_id}")

            return jsonify({
                'success': True,
                'message': 'تم تحديث الإعدادات',
                'data': normalized_response
            })
        except Exception as e:
            error_str = str(e)
            logger.error(f"❌ خطأ Update Settings {user_id}: {error_str}")

            # ✅ معالجة خاصة لـ database is locked
            if 'database is locked' in error_str.lower():
                return jsonify({
                    'success': False, 
                    'error': 'النظام مشغول حالياً، يرجى المحاولة بعد قليل',
                    'error_code': 'DATABASE_BUSY',
                    'retry_after': 3
                }), 503

            return jsonify({'success': False, 'error': error_str}), 500


    @bp.route('/settings/trading-mode/<int:user_id>', methods=['GET'])
    @require_auth
    @rate_limit_general
    def get_trading_mode(user_id):
        """جلب وضع التداول الحالي - للأدمن فقط"""
        if getattr(g, 'current_user_type', None) != 'admin':
            return jsonify({
                'success': False,
                'error': 'Only admin can view trading mode'
            }), 403

        try:
            db = db_manager

            user_query = "SELECT user_type FROM users WHERE id = %s"
            user_result = db.execute_query(user_query, (user_id,))

            if not user_result:
                return jsonify({'success': False, 'error': 'User not found'}), 404

            target_user_type = user_result[0]['user_type']
            is_admin = target_user_type == 'admin'

            current_mode = get_trading_context(db, user_id)['trading_mode']
            current_is_demo = current_mode == 'demo'

            key_state = resolve_key_state(db, user_id, is_admin, current_is_demo)

            return jsonify({
                'success': True,
                'data': {
                    'tradingMode': current_mode,
                    'hasBinanceKeys': key_state['has_binance_keys'],
                    'hasConfiguredDbKeys': key_state['has_configured_db_keys'],
                    'usingEnvTestKeys': key_state['using_env_test_keys'],
                    'keysRequiredForCurrentMode': key_state['keys_required_for_current_mode'],
                    'canToggle': is_admin,
                    'availableModes': ['demo', 'real']
                }
            })

        except Exception as e:
            logger.error(f"❌ خطأ في جلب trading_mode: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @bp.route('/settings/trading-mode/<int:user_id>', methods=['PUT'])
    @require_auth
    @rate_limit_trading
    def update_trading_mode(user_id):
        """تحديث وضع التداول (Toggle Mode) - للأدمن فقط"""
        if getattr(g, 'current_user_type', None) != 'admin':
            return jsonify({'success': False, 'error': 'Only admin can toggle trading mode'}), 403

        try:
            data = request.json
            new_mode = data.get('mode')

            # التحقق من صحة القيمة
            if new_mode not in ['demo', 'real']:
                return jsonify({'success': False, 'error': 'Invalid mode. Must be: demo or real'}), 400

            db = db_manager

            # فحص نوع المستخدم
            user_query = "SELECT user_type FROM users WHERE id = %s"
            user_result = db.execute_query(user_query, (user_id,))

            if not user_result:
                return jsonify({'success': False, 'error': 'User not found'}), 404

            user_type = user_result[0]['user_type']

            # إذا كان real، تحقق من المفاتيح
            if new_mode == 'real':
                keys_query = "SELECT COUNT(*) as count FROM user_binance_keys WHERE user_id = %s AND is_active = TRUE"
                keys_result = db.execute_query(keys_query, (user_id,))
                has_keys = keys_result[0]['count'] > 0 if keys_result else False

                if not has_keys:
                    return jsonify({
                        'success': False,
                        'error': 'Real trading requires Binance API keys'
                    }), 400

            # جلب الوضع القديم (للـ audit log)
            old_mode = get_trading_context(db, user_id)['trading_mode']

            # ضمان وجود صف إعدادات للمحفظة المستهدفة قبل التبديل لتفادي دورة إعدادات غير مكتملة
            target_is_demo = new_mode == 'demo'
            target_row_query = "SELECT id FROM user_settings WHERE user_id = %s AND is_demo = %s LIMIT 1"
            target_row = db.execute_query(target_row_query, (user_id, target_is_demo))
            if not target_row:
                source_query = """
                    SELECT trade_amount, position_size_percentage, stop_loss_pct, take_profit_pct,
                           trailing_distance, max_positions, risk_level, max_daily_loss_pct
                    FROM user_settings
                    WHERE user_id = %s
                    ORDER BY COALESCE(updated_at, created_at) DESC
                    LIMIT 1
                """
                source_result = db.execute_query(source_query, (user_id,))
                if source_result:
                    src = source_result[0]
                    db.execute_query(
                        """
                        INSERT INTO user_settings (
                            user_id, is_demo, trading_enabled, trade_amount, position_size_percentage,
                            stop_loss_pct, take_profit_pct, trailing_distance, max_positions,
                            risk_level, max_daily_loss_pct, trading_mode, created_at, updated_at
                        ) VALUES (%s, %s, FALSE, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """,
                        (
                            user_id,
                            target_is_demo,
                            src.get('trade_amount', 100.0),
                            src.get('position_size_percentage', 10.0),
                            src.get('stop_loss_pct', 3.0),
                            src.get('take_profit_pct', 6.0),
                            src.get('trailing_distance', 3.0),
                            src.get('max_positions', 5),
                            src.get('risk_level', 'medium'),
                            src.get('max_daily_loss_pct', 10.0),
                            new_mode,
                        ),
                    )
                    if not target_is_demo:
                        initial_balance = 0.0
                        db.execute_query(
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
                                initial_balance,
                                initial_balance,
                                initial_balance,
                                target_is_demo,
                                user_id,
                                target_is_demo,
                            )
                        )
                else:
                    db.execute_query(
                        """
                        INSERT INTO user_settings (
                            user_id, is_demo, trading_enabled, trade_amount, position_size_percentage,
                            stop_loss_pct, take_profit_pct, trailing_distance, max_positions,
                            risk_level, max_daily_loss_pct, trading_mode, created_at, updated_at
                        ) VALUES (%s, %s, FALSE, 100.0, 10.0, 3.0, 6.0, 3.0, 5, 'medium', 10.0, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """,
                        (user_id, target_is_demo, new_mode),
                    )
                    if not target_is_demo:
                        initial_balance = 0.0
                        db.execute_query(
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
                                initial_balance,
                                initial_balance,
                                initial_balance,
                                target_is_demo,
                                user_id,
                                target_is_demo,
                            )
                        )

            # ✅ تحديث الوضع في جميع إعدادات المستخدم
            # trading_mode يجب أن يكون متزامن في كلا الصفين
            update_query = """
                UPDATE user_settings
                SET trading_mode = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """
            db.execute_query(update_query, (new_mode, user_id))

            # ✅ تسجيل في activity_logs (باستخدام audit_logger الموحد)
            if audit_logger:
                audit_logger.log(
                    action='trading_mode_change',
                    user_id=user_id,
                    details={'old_mode': old_mode, 'new_mode': new_mode}
                )

            # ✅ إبطال Cache لجميع البيانات المتأثرة
            if CACHE_AVAILABLE:
                # حذف cache keys الأساسية
                response_cache.delete(f"settings_{user_id}")
                response_cache.delete(f"portfolio_{user_id}")
                response_cache.delete(f"stats_{user_id}")
                response_cache.delete(f"trading_mode_{user_id}")

                # حذف جميع صفحات trades (متعدد الصفحات)
                # نحذف بـ pattern بدل حذف كل صفحة على حدة
                for page in range(1, 50):  # حد أقصى 50 صفحة
                    for limit in [10, 20, 50, 100, 200]:
                        for status in ['all', 'open', 'closed']:
                            cache_key = f"trades_{user_id}_{page}_{limit}_{status}_None_None"
                            try:
                                response_cache.delete(cache_key)
                            except Exception as e:
                                logger.debug(f"Cache delete skipped: {cache_key}")

                logger.debug(f"✅ تم إبطال cache لجميع البيانات للمستخدم {user_id}")

            logger.info(f"✅ الأدمن {user_id}: تبديل trading_mode من {old_mode} إلى {new_mode}")

            return jsonify({
                'success': True,
                'message': 'تم تحديث وضع التداول',
                'old_mode': old_mode,
                'new_mode': new_mode
            })

        except Exception as e:
            logger.error(f"❌ خطأ في تحديث trading_mode: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    # ==================== مفاتيح Binance ====================

    @bp.route('/binance-keys/<int:user_id>', methods=['GET'])
    @require_auth
    @rate_limit_general
    def get_binance_keys(user_id):
        """الحصول على مفاتيح Binance - بدون Secret (مع فك التشفير)"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        try:
            db = db_manager

            key = db.get_binance_keys(user_id)

            if key and key.get('api_key'):
                api_key_encrypted = key['api_key']

                # فك تشفير API Key للعرض (masked)
                if ENCRYPTION_AVAILABLE and api_key_encrypted:
                    try:
                        from config.security.encryption_service import decrypt_text
                        api_key_decrypted = decrypt_text(api_key_encrypted)
                        masked_key = api_key_decrypted[:8] + '...' + api_key_decrypted[-8:] if len(api_key_decrypted) > 16 else '***'
                    except Exception as decrypt_error:
                        logger.warning(f"⚠️ فشل فك التشفير، ربما مفتاح قديم غير مشفر: {decrypt_error}")
                        # إذا فشل فك التشفير، نفترض أنه غير مشفر (للتوافق مع البيانات القديمة)
                        masked_key = api_key_encrypted[:8] + '...' + api_key_encrypted[-8:] if len(api_key_encrypted) > 16 else '***'
                else:
                    masked_key = api_key_encrypted[:8] + '...' + api_key_encrypted[-8:] if api_key_encrypted and len(api_key_encrypted) > 16 else '***'

                return jsonify({'success': True, 'data': {
                    'hasKeys': True, 'keyId': key.get('id'), 'apiKey': masked_key,
                    'createdAt': key.get('created_at'), 'isActive': bool(key.get('is_active', True)),
                    'isConfigured': True
                }})
            else:
                return jsonify({'success': True, 'data': {
                    'hasKeys': False, 'keyId': None, 'apiKey': None, 'createdAt': None, 'isActive': False,
                    'isConfigured': False
                }})
        except Exception as e:
            logger.error(f"❌ خطأ Binance Keys {user_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @bp.route('/binance-keys', methods=['POST'])
    @require_auth
    @rate_limit_auth
    @prevent_concurrent_duplicates
    @require_idempotency('save_binance_keys')
    def save_binance_keys():
        """حفظ مفاتيح Binance - مع تشفير AES"""
        try:
            db = db_manager
            data = request.get_json()
            user_id = g.current_user_id

            # دعم جميع التنسيقات المحتملة من التطبيق
            api_key = data.get('apiKey') or data.get('api_key')
            api_secret = data.get('apiSecret') or data.get('api_secret') or data.get('secretKey') or data.get('secret_key')

            if not api_key or not api_secret:
                return error_response('بيانات المفاتيح مطلوبة', 'MISSING_CREDENTIALS', 400)

            # 🔒 فحص أمان المفتاح قبل الحفظ — منع المفاتيح ذات صلاحية السحب
            try:
                from binance.client import Client
                client = Client(api_key, api_secret)

                # التحقق الفعلي من صحة المفاتيح عبر جلب بيانات الحساب
                account = client.get_account()
                if not isinstance(account, dict):
                    return jsonify({
                        'success': False,
                        'error': 'تعذر التحقق من بيانات الحساب في Binance',
                        'error_code': 'ACCOUNT_VALIDATION_FAILED'
                    }), 400

                api_perms = load_api_permissions(client)

                # يجب أن تكون صلاحية التداول مفعلة
                if not api_perms.get('enableSpotAndMarginTrading', False):
                    return jsonify({
                        'success': False,
                        'error': 'صلاحية التداول غير مفعّلة. فعّل Enable Spot & Margin Trading أولاً.',
                        'error_code': 'TRADING_PERMISSION_DISABLED'
                    }), 400

                if api_perms.get('enableWithdrawals', False):
                    return jsonify({
                        'success': False,
                        'error': '🚨 المفتاح يملك صلاحية السحب!\n\n'
                                 'لحماية أموالك، يجب تعطيل Enable Withdrawals '
                                 'من إعدادات API في Binance قبل الحفظ.',
                        'error_code': 'WITHDRAWAL_ENABLED'
                    }), 400

                if not api_perms.get('ipRestrict', False):
                    logger.warning(f"⚠️ User {user_id} saving keys without IP restriction")
            except Exception as perm_error:
                logger.warning(f"⚠️ Could not verify key permissions before save: {perm_error}")
                return jsonify({
                    'success': False,
                    'error': 'تعذر التحقق من صلاحيات المفتاح مع Binance. أعد المحاولة لاحقاً.',
                    'error_code': 'BINANCE_VALIDATION_UNAVAILABLE'
                }), 503

            # 🔒 FIX #5: ENFORCE encryption - no fallback allowed
            if not ENCRYPTION_AVAILABLE:
                logger.critical("❌ CRITICAL: Encryption service not available - cannot save keys")
                return jsonify({
                    'success': False,
                    'error': 'نظام التشفير غير متاح حالياً. يرجى المحاولة لاحقاً.',
                    'error_code': 'ENCRYPTION_UNAVAILABLE'
                }), 503

            # تشفير المفاتيح - إلزامي
            try:
                encrypted_key, encrypted_secret = encrypt_binance_keys(api_key, api_secret)
                logger.info(f"✅ تم تشفير مفاتيح Binance للمستخدم {user_id}")
            except Exception as encrypt_error:
                logger.error(f"❌ خطأ في التشفير: {encrypt_error}")
                return jsonify({
                    'success': False,
                    'error': 'فشل في تشفير المفاتيح',
                    'error_code': 'ENCRYPTION_FAILED'
                }), 500

            # حذف القديم وإضافة الجديد
            db.execute_query("UPDATE user_binance_keys SET is_active = FALSE WHERE user_id = %s", (user_id,))
            db.execute_query(
                "INSERT INTO user_binance_keys (user_id, api_key, api_secret, is_active, created_at) VALUES (%s, %s, %s, TRUE, CURRENT_TIMESTAMP)",
                (user_id, encrypted_key, encrypted_secret)
            )

            return success_response(
                {'encrypted': ENCRYPTION_AVAILABLE},
                'تم حفظ المفاتيح بشكل آمن',
                201
            )
        except Exception as e:
            logger.error(f"❌ خطأ Save Keys: {e}")
            return error_response('فشل في حفظ المفاتيح', 'SAVE_ERROR', 500)


    @bp.route('/binance-keys/<int:key_id>', methods=['DELETE'])
    @require_auth
    def delete_binance_key(key_id):
        """حذف مفتاح Binance - مع التحقق"""
        try:
            db = db_manager
            user_id = g.current_user_id

            check_query = "SELECT user_id FROM user_binance_keys WHERE id = %s"
            result = db.execute_query(check_query, (key_id,))

            if not result or result[0]['user_id'] != user_id:
                return error_response('لا توجد صلاحيات', 'UNAUTHORIZED', 403)

            db.execute_query("UPDATE user_binance_keys SET is_active = FALSE WHERE id = %s", (key_id,))
            return success_response(None, 'تم حذف المفتاح')
        except Exception as e:
            logger.error(f"❌ خطأ Delete Key: {e}")
            return error_response('فشل في حذف المفتاح', 'DELETE_ERROR', 500)


    @bp.route('/binance-keys/validate', methods=['POST'])
    @require_auth
    def validate_binance_keys():
        """
        ✅ اختبار صحة مفاتيح Binance مع Binance API

        Request Body:
            {
                "apiKey": "...",
                "apiSecret": "..."
            }

        Response:
            {
                "success": true,
                "valid": true,
                "message": "المفاتيح صحيحة",
                "account_type": "spot",
                "can_trade": true
            }
        """
        try:
            db = db_manager
            user_id = g.current_user_id
            data = request.get_json()

            api_key = data.get('apiKey') or data.get('api_key')
            api_secret = data.get('apiSecret') or data.get('api_secret')

            if not api_key or not api_secret:
                return jsonify({
                    'success': False,
                    'valid': False,
                    'error': 'Missing API key or secret'
                }), 400

            # فك تشفير المفاتيح إذا كانت مشفرة
            if ENCRYPTION_AVAILABLE:
                try:
                    from config.security.encryption_service import decrypt_text
                    api_key_decrypted = decrypt_text(api_key) if len(api_key) > 50 else api_key
                    api_secret_decrypted = decrypt_text(api_secret) if len(api_secret) > 50 else api_secret
                except Exception as e:
                    logger.warning(f"⚠️ فشل فك تشفير المفاتيح، استخدام القيم الأصلية: {e}")
                    api_key_decrypted = api_key
                    api_secret_decrypted = api_secret
            else:
                api_key_decrypted = api_key
                api_secret_decrypted = api_secret

            # اختبار الاتصال مع Binance API
            try:
                from binance.client import Client
                from binance.exceptions import BinanceAPIException, BinanceRequestException

                client = Client(api_key_decrypted, api_secret_decrypted)

                # محاولة الحصول على معلومات الحساب
                account = client.get_account()

                # التحقق من الصلاحيات الأساسية
                can_trade = account.get('canTrade', False)
                can_withdraw = account.get('canWithdraw', False)
                account_type = 'spot'

                # ===== فحص صلاحيات المفتاح التفصيلية =====
                ip_restricted = False
                ip_list = []
                enable_withdrawals = can_withdraw
                enable_spot = can_trade
                security_warnings = []
                security_score = 100  # يبدأ من 100 وينقص مع كل مشكلة

                try:
                    api_restrictions = load_api_permissions(client)
                    ip_restricted = api_restrictions.get('ipRestrict', False)
                    enable_withdrawals = api_restrictions.get('enableWithdrawals', False)
                    enable_spot = api_restrictions.get('enableSpotAndMarginTrading', False)
                    # enableInternalTransfer, enableFutures, etc.

                    if enable_withdrawals:
                        security_warnings.append({
                            'level': 'critical',
                            'message': 'صلاحية السحب مفعّلة! يجب تعطيلها لحماية أموالك',
                            'action': 'قم بتعطيل Enable Withdrawals من إعدادات API في Binance'
                        })
                        security_score -= 50

                    if not ip_restricted:
                        security_warnings.append({
                            'level': 'warning',
                            'message': 'المفتاح غير مقيّد بعنوان IP — أي جهاز يمكنه استخدامه',
                            'action': 'قم بإضافة IP السيرفر في Restrict access to trusted IPs only'
                        })
                        security_score -= 30

                    if not enable_spot:
                        security_warnings.append({
                            'level': 'info',
                            'message': 'صلاحية التداول غير مفعّلة',
                            'action': 'قم بتفعيل Enable Spot & Margin Trading'
                        })
                        security_score -= 20

                except Exception as perm_error:
                    logger.warning(f"⚠️ تعذر جلب صلاحيات المفتاح: {perm_error}")
                    security_warnings.append({
                        'level': 'info',
                        'message': 'تعذر التحقق من صلاحيات المفتاح التفصيلية',
                        'action': 'تحقق يدوياً من إعدادات API في Binance'
                    })

                security_score = max(0, security_score)

                logger.info(f"✅ مفاتيح Binance صحيحة للمستخدم {user_id} | "
                            f"withdraw={enable_withdrawals}, ip_restricted={ip_restricted}, "
                            f"security_score={security_score}")

                return jsonify({
                    'success': True,
                    'valid': True,
                    'message': 'المفاتيح صحيحة وتعمل بشكل صحيح',
                    'account_type': account_type,
                    'can_trade': can_trade,
                    'balances_count': len(account.get('balances', [])),
                    'security': {
                        'score': security_score,
                        'ip_restricted': ip_restricted,
                        'withdrawals_enabled': enable_withdrawals,
                        'spot_enabled': enable_spot,
                        'warnings': security_warnings,
                        'is_safe': security_score >= 70 and not enable_withdrawals
                    }
                })

            except BinanceAPIException as e:
                logger.warning(f"⚠️ خطأ Binance API للمستخدم {user_id}: {e}")
                return jsonify({
                    'success': False,
                    'valid': False,
                    'error': f'خطأ في Binance API: {str(e)}',
                    'error_code': e.status_code
                }), 400

            except BinanceRequestException as e:
                logger.warning(f"⚠️ خطأ في الاتصال بـ Binance للمستخدم {user_id}: {e}")
                return jsonify({
                    'success': False,
                    'valid': False,
                    'error': 'فشل الاتصال بـ Binance. تحقق من الاتصال بالإنترنت'
                }), 503

            except Exception as e:
                logger.error(f"❌ خطأ في اختبار المفاتيح للمستخدم {user_id}: {e}")
                return jsonify({
                    'success': False,
                    'valid': False,
                    'error': f'خطأ في الاختبار: {str(e)}'
                }), 500

        except Exception as e:
            logger.error(f"❌ خطأ Validate Keys: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    # ==================== الملف الشخصي ====================

    @bp.route('/profile/<int:user_id>', methods=['GET'])
    @require_auth
    @rate_limit_general
    def get_user_profile(user_id):
        """الحصول على الملف الشخصي"""
        if not verify_user_access(user_id):
            return jsonify({'success': False, 'error': 'Unauthorized access'}), 403

        try:
            db = db_manager

            profile_query = "SELECT id, username, name, email, phone_number, user_type, is_active, created_at, last_login_at FROM users WHERE id = %s"
            result = db.execute_query(profile_query, (user_id,))

            if result and len(result) > 0:
                user = result[0]
                return jsonify({'success': True, 'data': {
                    'id': user['id'], 'username': user['username'], 'name': user['name'] or '',
                    'email': user['email'], 'phoneNumber': user['phone_number'] or '',
                    'userType': user['user_type'], 'isActive': bool(user['is_active']),
                    'createdAt': user['created_at'], 'lastLogin': user['last_login_at']
                }})
            else:
                return jsonify({'success': False, 'error': 'User not found'}), 404
        except Exception as e:
            logger.error(f"❌ خطأ Profile {user_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @bp.route('/profile/<int:user_id>', methods=['PUT'])
    @require_auth
    @rate_limit_general
    @prevent_concurrent_duplicates
    @require_idempotency('update_profile')
    def update_user_profile(user_id):
        """تحديث الملف الشخصي"""
        if not verify_user_access(user_id):
            return error_response('لا توجد صلاحيات', 'UNAUTHORIZED', 403)

        try:
            data = request.get_json(silent=True) or {}

            if not data:
                return error_response('لا توجد بيانات', 'MISSING_DATA', 400)

            # ✅ استخدام get_write_connection لتجنب database lock
            with db_manager.get_write_connection() as conn:
                cursor = conn.cursor()

                # تحديث البيانات المتاحة فقط (بدون username)
                updates = []
                params = []

                full_name = data.get('fullName') or data.get('full_name') or data.get('name')
                phone_number = data.get('phoneNumber') or data.get('phone_number') or data.get('phone')

                if full_name is not None:
                    updates.append("name = %s")
                    params.append((full_name or '').strip() or None)
                if 'bio' in data:
                    updates.append("bio = %s")
                    params.append((data['bio'] or '').strip() or None)
                if 'avatar' in data:
                    updates.append("avatar = %s")
                    params.append((data['avatar'] or '').strip() or None)
                if phone_number is not None:
                    updates.append("phone_number = %s")
                    params.append((phone_number or '').strip() or None)

                if updates:
                    params.append(user_id)
                    query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
                    cursor.execute(query, params)

            return success_response(None, 'تم تحديث الملف الشخصي بنجاح')
        except Exception as e:
            logger.error(f"❌ خطأ Update Profile {user_id}: {e}")
            return error_response('خطأ في الخادم', 'INTERNAL_ERROR', 500)



    # ==================== إعادة ضبط البيانات ====================

    @bp.route('/reset-data/<int:user_id>', methods=['POST'])
    @require_auth
    @prevent_concurrent_duplicates
    @require_idempotency('reset_account')
    def reset_account_data(user_id):
        """
        إعادة ضبط بيانات الحساب (حذف الصفقات والإعدادات)
        ⚠️ عملية خطيرة - تتطلب تأكيد
        """
        if not verify_user_access(user_id):
            response_data, status_code = error_response('غير مصرح', 'UNAUTHORIZED', 403)
            return jsonify(response_data), status_code

        try:
            user_row = db_manager.execute_query("SELECT user_type FROM users WHERE id = %s", (user_id,))
            is_admin_user = user_row[0]['user_type'] == 'admin' if user_row else False
            reset_mode = 'demo' if is_admin_user else 'real'
            reset_is_demo = is_admin_user

            if reset_is_demo:
                initial_balance = getattr(db_manager, 'DEMO_ACCOUNT_INITIAL_BALANCE', 1000.0)
                if not db_manager.reset_user_portfolio(user_id, initial_balance=initial_balance):
                    response_data, status_code = error_response('فشل في إعادة ضبط الحساب التجريبي', 'RESET_ERROR', 500)
                    return jsonify(response_data), status_code

                with db_manager.get_write_connection() as conn:
                    conn.execute("""
                        UPDATE user_settings 
                        SET trading_mode = 'demo', stop_loss_pct = 2.0, take_profit_pct = 5.0,
                            max_positions = 5, trading_enabled = TRUE
                        WHERE user_id = %s AND is_demo = TRUE
                    """, (user_id,))

                logger.info(f"✅ تم إعادة ضبط الحساب التجريبي للمستخدم {user_id} من المصدر الموحد")
                response_data, status_code = success_response({'reset': True, 'mode': 'demo'}, 'تم إعادة ضبط البيانات بنجاح')
                return jsonify(response_data), status_code

            with db_manager.get_write_connection() as conn:
                # حذف المراكز النشطة
                conn.execute("DELETE FROM active_positions WHERE user_id = %s AND is_demo = FALSE", (user_id,))

                # إعادة ضبط المحفظة (استخدام الأعمدة الصحيحة)
                # ✅ FIX: الرصيد الافتراضي = 1000 USDT (يتطابق مع UI والتوثيق)
                portfolio_row = conn.execute("""
                    SELECT initial_balance FROM portfolio WHERE user_id = %s AND is_demo = %s LIMIT 1
                """, (user_id, reset_is_demo)).fetchone()
                initial_balance = float(portfolio_row[0] or 1000.0) if portfolio_row else 1000.0
                conn.execute("""
                    UPDATE portfolio 
                    SET total_balance = %s, available_balance = %s, 
                        invested_balance = 0.0, total_profit_loss = 0.0, 
                        total_profit_loss_percentage = 0.0, initial_balance = %s
                    WHERE user_id = %s AND is_demo = %s
                """, (initial_balance, initial_balance, initial_balance, user_id, reset_is_demo))

                # إعادة ضبط الإعدادات للقيم الافتراضية
                conn.execute("""
                    UPDATE user_settings 
                    SET trading_mode = %s, stop_loss_pct = 2.0, take_profit_pct = 5.0,
                        max_positions = 5, trading_enabled = TRUE
                    WHERE user_id = %s AND is_demo = %s
                """, (reset_mode, user_id, reset_is_demo))

                conn.commit()

            logger.info(f"✅ تم إعادة ضبط بيانات المستخدم {user_id}")
            response_data, status_code = success_response({'reset': True}, 'تم إعادة ضبط البيانات بنجاح')
            return jsonify(response_data), status_code

        except Exception as e:
            logger.error(f"❌ خطأ في إعادة ضبط البيانات: {e}")
            response_data, status_code = error_response('خطأ في إعادة ضبط البيانات', 'RESET_ERROR', 500)
            return jsonify(response_data), status_code


    @bp.route('/daily-status/<int:user_id>', methods=['GET'])
    @require_auth
    @rate_limit_general
    def get_daily_risk_status(user_id):
        """
        حالة المخاطرة اليومية — حد الخسارة اليومي ونسبة الاستهلاك.
        يُستخدم من واجهة Flutter لعرض مؤشر المخاطرة للمستخدم.
        """
        if not verify_user_access(user_id):
            response_data, status_code = error_response('غير مصرح', 'UNAUTHORIZED', 403)
            return jsonify(response_data), status_code

        try:
            from datetime import date as _date
            today = str(_date.today())
            requested_mode = request.args.get('mode')
            trading_context = get_trading_context(db_manager, user_id, requested_mode=requested_mode)
            is_demo = bool(trading_context['is_demo'])
            portfolio_owner_id = trading_context['portfolio_owner_id']

            with db_manager.get_connection() as conn:
                # 1️⃣ إعدادات المستخدم (حد الخسارة + الوضع)
                settings_row = conn.execute("""
                    SELECT max_daily_loss_pct
                    FROM user_settings
                    WHERE user_id = %s AND is_demo = %s
                    ORDER BY COALESCE(updated_at, created_at) DESC
                    LIMIT 1
                """, (user_id, is_demo)).fetchone()

                max_daily_loss_pct = float(settings_row[0]) if settings_row and settings_row[0] else 10.0

                # 2️⃣ رصيد المحفظة (للحساب النسبي)
                port_row = conn.execute("""
                    SELECT COALESCE(initial_balance, total_balance, 0.0) as base
                    FROM portfolio
                    WHERE user_id = %s AND is_demo = %s
                    LIMIT 1
                """, (portfolio_owner_id, is_demo)).fetchone()
                base_balance = float(port_row[0]) if port_row else 0.0

                # 3️⃣ الخسارة اليومية من الصفقات المغلقة اليوم
                pnl_row = conn.execute("""
                    SELECT COALESCE(SUM(profit_loss), 0.0) as daily_pnl,
                           COUNT(*) as trades_today
                    FROM active_positions
                    WHERE user_id = %s
                      AND is_active = FALSE
                      AND is_demo = %s
                      AND DATE(COALESCE(closed_at, updated_at)) = %s
                """, (portfolio_owner_id, is_demo, today)).fetchone()

                daily_pnl = float(pnl_row[0]) if pnl_row else 0.0
                trades_today = int(pnl_row[1]) if pnl_row else 0

            # 4️⃣ حساب نسبة الاستهلاك
            daily_loss_abs = max(0.0, -daily_pnl)  # positive number representing loss
            daily_loss_used_pct = round((daily_loss_abs / base_balance) * 100, 2) if base_balance > 0 else 0.0
            daily_limit_usdt = round((max_daily_loss_pct / 100.0) * base_balance, 2)
            remaining_usdt = round(max(0.0, daily_limit_usdt - daily_loss_abs), 2)
            limit_breached = daily_loss_used_pct >= max_daily_loss_pct

            return jsonify({
                'success': True,
                'data': {
                    'daily_pnl': round(daily_pnl, 2),
                    'daily_loss_abs': round(daily_loss_abs, 2),
                    'daily_loss_used_pct': daily_loss_used_pct,
                    'max_daily_loss_pct': max_daily_loss_pct,
                    'daily_limit_usdt': daily_limit_usdt,
                    'remaining_usdt': remaining_usdt,
                    'limit_breached': limit_breached,
                    'trades_today': trades_today,
                    'base_balance': round(base_balance, 2),
                    'is_demo': bool(is_demo),
                    'date': today,
                }
            })

        except Exception as e:
            logger.error(f"❌ خطأ في جلب حالة المخاطرة اليومية: {e}")
            response_data, status_code = error_response('خطأ في جلب البيانات', 'DAILY_STATUS_ERROR', 500)
            return jsonify(response_data), status_code


