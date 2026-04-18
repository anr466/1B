"""
Mobile API Endpoints - Trading AI Bot
=====================================
نقاط نهاية API للتطبيق المحمول مع عزل كامل للبيانات

✅ كل مستخدم يرى بياناته فقط
✅ التحقق من الهوية في كل طلب
✅ عزل كامل بـ WHERE user_id = %s
"""

from backend.api.mobile_auth_routes import register_mobile_auth_routes
from backend.api.mobile_notifications_routes import (
    register_mobile_notifications_routes,
)
from backend.api.mobile_settings_routes import register_mobile_settings_routes
from backend.api.mobile_trades_routes import register_mobile_trades_routes
from backend.api.auth_middleware import require_auth
from backend.utils.safe_logger import SafeLogger
from backend.infrastructure.db_access import get_db_manager
from flask import Blueprint, request, jsonify, g
import sys
from backend.utils.response_formatter import success_response, error_response
from backend.utils.idempotency_manager import require_idempotency
from backend.utils.request_deduplicator import prevent_concurrent_duplicates
from backend.utils.trading_context import get_trading_context
from config.logging_config import log_api_error
import os

# ✅ Rate Limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

# إضافة مسار config للوصول لخدمة التشفير
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

# Database
db_manager = get_db_manager()

# User lookup service

# ✅ Phase 1: Safe Logger (يخفي البيانات الحساسة)
logger = SafeLogger(__name__)


def _resolve_key_state(db, user_id: int, is_admin: bool, is_demo: bool):
    db_rows = db.execute_query(
        "SELECT COUNT(*) as count FROM user_binance_keys WHERE user_id = %s AND is_active = TRUE",
        (user_id,),
    )
    has_configured_db_keys = bool(db_rows and db_rows[0].get("count", 0) > 0)
    env_keys_enabled = (
        os.getenv("ALLOW_ENV_BINANCE_KEYS_FOR_TESTING") or ""
    ).strip().lower() in ("1", "true", "yes", "on")
    env_api_key = (os.getenv("BINANCE_BACKEND_API_KEY") or "").strip()
    env_api_secret = (os.getenv("BINANCE_BACKEND_API_SECRET") or "").strip()
    using_env_test_keys = bool(
        env_keys_enabled
        and env_api_key
        and env_api_secret
        and not has_configured_db_keys
    )
    resolved_keys = db.get_binance_keys(user_id)
    actual_has_keys = bool(resolved_keys and resolved_keys.get("api_key"))
    keys_required_for_current_mode = not (is_admin and is_demo)
    logical_has_keys = True if not keys_required_for_current_mode else actual_has_keys
    return {
        "has_binance_keys": logical_has_keys,
        "has_configured_db_keys": has_configured_db_keys,
        "using_env_test_keys": using_env_test_keys,
        "keys_required_for_current_mode": keys_required_for_current_mode,
        "actual_has_keys": actual_has_keys,
    }


# ✅ Phase 2: Request Validation & Error Handling
try:
    VALIDATION_AVAILABLE = True
    logger.info("✅ Request Validation & Error Handling متاح")
except ImportError as e:
    VALIDATION_AVAILABLE = False
    logger.warning(f"⚠️ Request Validation غير متاح: {e}")

# ✅ Input Validation - التحقق من صحة البيانات المدخلة
try:
    INPUT_VALIDATION_AVAILABLE = True
    logger.info("✅ Input Validation System متاح")
except ImportError as e:
    INPUT_VALIDATION_AVAILABLE = False
    logger.warning(f"⚠️ Input Validation غير متاح: {e}")

# إنشاء Blueprint بدون /api (لأن Flask مثبت على /api في unified_server.py)
mobile_bp = Blueprint("mobile", __name__, url_prefix="/user")

# Audit Logger
try:
    from backend.utils.audit_logger import audit_logger
except (ImportError, ModuleNotFoundError):
    audit_logger = None


# ✅ تهيئة Rate Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # حد افتراضي
    storage_uri="memory://",  # تخزين في الذاكرة
)

# استيراد Rate Limiter Helper
try:
    from backend.utils.rate_limiter_helper import (
        rate_limit_general,
        rate_limit_trading,
        rate_limit_data,
        rate_limit_auth,
    )

    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False
    logger.warning("⚠️ Rate Limiter Helper غير متاح")

# استيراد نظام Token

# استيراد خدمة التشفير
try:
    ENCRYPTION_AVAILABLE = True
    logger.info("✅ خدمة تشفير Binance Keys متاحة")
except ImportError as e:
    ENCRYPTION_AVAILABLE = False
    logger.warning(f"⚠️ خدمة التشفير غير متاحة: {e}")

# ✅ Phase 1: استيراد نظام Cache البسيط
try:
    from backend.utils.simple_cache import SmartCache

    response_cache = SmartCache()
    CACHE_AVAILABLE = True
    logger.info("✅ نظام SmartCache متاح")
except ImportError as e:
    CACHE_AVAILABLE = False
    response_cache = None
    logger.warning(f"⚠️ نظام Cache غير متاح: {e}")


def verify_user_access(user_id):
    """
    التحقق من أن المستخدم يطلب بياناته فقط
    ✅ منع الوصول لبيانات مستخدمين آخرين
    ✅ السماح للأدمن بالوصول لبيانات أي مستخدم
    """
    user_type = getattr(g, "current_user_type", "user")
    if user_type == "admin":
        return True
    if g.current_user_id != user_id:
        logger.warning(
            f"⚠️ محاولة وصول غير مصرح: User {
                g.current_user_id
            } حاول الوصول لبيانات User {user_id}"
        )
        return False
    return True


# ==================== المحفظة (Portfolio) ====================


@mobile_bp.route("/portfolio/<int:user_id>", methods=["GET"])
@require_auth
@rate_limit_data
def get_user_portfolio(user_id):
    """
    الحصول على بيانات محفظة المستخدم

    ✅ عزل كامل: WHERE user_id = %s
    ✅ التحقق من الهوية
    ✅ بيانات حقيقية من Binance أو 0 إذا لم توجد مفاتيح

    Returns:
        {
            "success": true,
            "data": {
                "totalBalance": "1000.00",
                "dailyPnL": "+50.00",
                "dailyPnLPercentage": "+5.0",
                "hasKeys": true
            }
        }
    """
    # التحقق من أن المستخدم يطلب بياناته فقط
    if not verify_user_access(user_id):
        response_data, status_code = error_response(
            "لا توجد صلاحيات", "UNAUTHORIZED", 403
        )
        return jsonify(response_data), status_code

    # ✅ قراءة mode من query parameters (للأدمن)
    requested_mode = request.args.get("mode", None)

    try:
        # ✅ استخدام db_manager المُعرّف مسبقاً بدلاً من إنشاء instance جديد
        db = db_manager

        trading_context = get_trading_context(
            db, user_id, requested_mode=requested_mode
        )
        user_data = db.get_user_by_id(user_id)
        if not user_data:
            return error_response("المستخدم غير موجود", "NOT_FOUND", 404)

        is_admin = trading_context["is_admin"]
        is_demo = trading_context["is_demo"]
        portfolio_owner_id = trading_context["portfolio_owner_id"]
        key_state = _resolve_key_state(db, user_id, is_admin, bool(is_demo))
        resolved_mode = (
            requested_mode
            if requested_mode in ("demo", "real")
            else ("demo" if bool(is_demo) else "real")
        )
        cache_key = f"portfolio_{user_id}_{resolved_mode}"

        # ✅ محاولة الحصول من Cache بعد حسم الوضع الفعلي (تجنب خلط real/demo)
        if CACHE_AVAILABLE:
            cached_data = response_cache.get(cache_key)
            if cached_data:
                logger.debug(
                    f"✅ Portfolio من Cache للمستخدم {user_id} mode={resolved_mode}"
                )
                response_data, status_code = success_response(
                    cached_data, "تم جلب المحفظة من الذاكرة المؤقتة"
                )
                return jsonify(response_data), status_code

        def load_portfolio_base_balances(owner_id, demo_flag):
            try:
                base_query = "SELECT initial_balance, total_balance, invested_balance FROM portfolio WHERE user_id = %s AND is_demo = %s"
                rows = db.execute_query(base_query, (owner_id, demo_flag == 1))
                if rows and len(rows) > 0:
                    return rows[0]
            except Exception:
                pass
            return {}

        if is_admin and not is_demo:
            keys = db.get_binance_keys(user_id)
            if not keys:
                base_row = load_portfolio_base_balances(portfolio_owner_id, is_demo)
                initial_balance = float(base_row.get("initial_balance") or 0.0)
                current_balance = float(
                    base_row.get("total_balance") or initial_balance or 0.0
                )
                invested_balance = float(base_row.get("invested_balance") or 0.0)
                payload = {
                    "requiresSetup": True,
                    "message": "أضف مفاتيح Binance للبدء",
                    "hasBinanceKeys": False,
                    "hasKeys": False,
                    "hasConfiguredDbKeys": key_state["has_configured_db_keys"],
                    "usingEnvTestKeys": key_state["using_env_test_keys"],
                    "keysRequiredForCurrentMode": key_state[
                        "keys_required_for_current_mode"
                    ],
                    "currentBalance": round(current_balance, 2),
                    "totalBalance": round(current_balance, 2),
                    "availableBalance": round(current_balance, 2),
                    "lockedBalance": round(0.0, 2),
                    "investedBalance": round(invested_balance, 2),
                    "initialBalance": round(initial_balance, 2),
                    "dailyPnL": 0.0,
                    "dailyPnLPercentage": 0.0,
                    "totalPnL": 0.0,
                    "totalPnLPercentage": 0.0,
                    "realizedPnL": 0.0,
                    "realizedPnLPercentage": 0.0,
                    "unrealizedPnL": 0.0,
                    "unrealizedPnLPercentage": 0.0,
                    "totalProfitLoss": 0.0,
                }
                response_data, status_code = success_response(
                    payload, "يتطلب إعداد مفاتيح Binance"
                )
                return jsonify(response_data), status_code

        if not is_admin:
            # ✅ المستخدم العادي: Real فقط - التحقق من المفاتيح أولاً
            keys = db.get_binance_keys(user_id)
            if not keys:
                # ❌ بدون مفاتيح = لا بيانات
                payload = {
                    "requiresSetup": True,
                    "message": "أضف مفاتيح Binance للبدء",
                    "hasBinanceKeys": False,
                    "hasKeys": False,
                    "hasConfiguredDbKeys": key_state["has_configured_db_keys"],
                    "usingEnvTestKeys": key_state["using_env_test_keys"],
                    "keysRequiredForCurrentMode": key_state[
                        "keys_required_for_current_mode"
                    ],
                    "currentBalance": 0.0,
                    "totalBalance": 0.0,
                    "availableBalance": 0.0,
                    "lockedBalance": 0.0,
                    "investedBalance": 0.0,
                    "initialBalance": 0.0,
                    "dailyPnL": 0.0,
                    "dailyPnLPercentage": 0.0,
                    "totalPnL": 0.0,
                    "totalPnLPercentage": 0.0,
                    "realizedPnL": 0.0,
                    "realizedPnLPercentage": 0.0,
                    "unrealizedPnL": 0.0,
                    "unrealizedPnLPercentage": 0.0,
                    "totalProfitLoss": 0.0,
                }
                response_data, status_code = success_response(
                    payload, "يتطلب إعداد مفاتيح Binance"
                )
                return jsonify(response_data), status_code

            # مع مفاتيح → جلب البيانات الحقيقية
            is_demo = 0

        # ✅ جلب بيانات المحفظة حسب الوضع (demo/real)
        portfolio_data = db.get_user_portfolio(portfolio_owner_id, is_demo)

        if not portfolio_data:
            return error_response("المحفظة غير موجودة", "NOT_FOUND", 404)

        if portfolio_data.get("error"):
            return error_response(
                portfolio_data.get("message", "خطأ غير معروف"),
                "PORTFOLIO_ERROR",
                400,
            )

        # ✅ استخراج البيانات بشكل آمن
        has_keys = portfolio_data.get("hasKeys", False)

        # تحويل آمن للقيم
        def safe_float(value, default=0.0):
            try:
                if value is None:
                    return default
                if isinstance(value, str):
                    return float(
                        value.replace(",", "").replace("+", "").replace("%", "")
                    )
                return float(value) if value else default
            except (ValueError, AttributeError, TypeError):
                return default

        total_balance = safe_float(portfolio_data.get("totalBalance", "0.00"))
        available_balance = safe_float(portfolio_data.get("availableBalance", "0.00"))
        locked_balance = safe_float(
            portfolio_data.get(
                "lockedBalance", portfolio_data.get("investedBalance", "0.00")
            )
        )
        daily_pnl = safe_float(portfolio_data.get("dailyPnL", "+0.00"))
        daily_pnl_pct = safe_float(portfolio_data.get("dailyPnLPercentage", "+0.0"))
        total_pnl_raw = portfolio_data.get("totalPnL", "0.00")
        total_pnl = safe_float(total_pnl_raw, 0.0)
        realized_pnl = safe_float(portfolio_data.get("realizedPnL", 0.0), 0.0)
        unrealized_pnl = safe_float(portfolio_data.get("unrealizedPnL", 0.0), 0.0)

        initial_balance = safe_float(portfolio_data.get("initialBalance", "0.00"))
        invested_balance = safe_float(portfolio_data.get("investedBalance", "0.00"))
        should_backfill_from_db = is_demo or has_keys
        if should_backfill_from_db and (initial_balance == 0 or invested_balance == 0):
            try:
                extra = [load_portfolio_base_balances(portfolio_owner_id, is_demo)]
                if extra and len(extra) > 0:
                    if initial_balance == 0:
                        initial_balance = safe_float(extra[0].get("initial_balance", 0))
                    if invested_balance == 0:
                        invested_balance = safe_float(
                            extra[0].get("invested_balance", 0)
                        )
            except Exception:
                pass

        total_pnl = safe_float(
            portfolio_data.get("totalPnL", portfolio_data.get("totalProfitLoss", 0.0)),
            0.0,
        )
        total_pnl_pct = safe_float(
            portfolio_data.get(
                "totalPnLPercentage",
                portfolio_data.get("totalProfitLossPercentage", 0.0),
            ),
            0.0,
        )
        realized_pnl_pct = safe_float(
            portfolio_data.get("realizedPnLPercentage", 0.0), 0.0
        )
        unrealized_pnl_pct = safe_float(
            portfolio_data.get("unrealizedPnLPercentage", 0.0), 0.0
        )

        data = {
            "currentBalance": round(total_balance, 2),
            "totalBalance": round(total_balance, 2),
            "initialBalance": round(initial_balance, 2),
            "availableBalance": round(available_balance, 2),
            "lockedBalance": round(locked_balance, 2),
            "investedBalance": round(invested_balance, 2),
            "dailyPnL": round(daily_pnl, 2),
            "dailyPnLPercentage": round(daily_pnl_pct, 2),
            "totalPnL": round(total_pnl, 2),
            "totalPnLPercentage": round(total_pnl_pct, 2),
            "realizedPnL": round(realized_pnl, 2),
            "realizedPnLPercentage": round(realized_pnl_pct, 2),
            "unrealizedPnL": round(unrealized_pnl, 2),
            "unrealizedPnLPercentage": round(unrealized_pnl_pct, 2),
            "totalProfitLoss": round(total_pnl, 2),
            "hasKeys": has_keys,
            "hasConfiguredDbKeys": key_state["has_configured_db_keys"],
            "usingEnvTestKeys": key_state["using_env_test_keys"],
            "keysRequiredForCurrentMode": key_state["keys_required_for_current_mode"],
            "firstTradeDate": portfolio_data.get("firstTradeDate"),
            "firstTradeBalance": safe_float(
                portfolio_data.get("firstTradeBalance", 0.0), 0.0
            ),
            "initialBalanceSource": portfolio_data.get("initialBalanceSource"),
            "lastUpdate": portfolio_data.get("lastUpdate"),
        }

        # ✅ حفظ في Cache مع توحيد Cache Key + Dynamic TTL
        if CACHE_AVAILABLE:
            response_cache.set(cache_key, data, ttl=30, user_id=user_id)

        response_data, status_code = success_response(data, "تم جلب المحفظة بنجاح")
        return jsonify(response_data), status_code

    except Exception as e:
        log_api_error(logger, "get_user_portfolio", user_id, e)
        response_data, status_code = error_response(
            "خطأ في جلب المحفظة", "PORTFOLIO_ERROR", 500
        )
        return jsonify(response_data), status_code


# ==================== الإحصائيات (Stats) ====================


@mobile_bp.route("/stats/<int:user_id>", methods=["GET"])
@require_auth
@rate_limit_data
def get_user_stats(user_id):
    """
    الحصول على إحصائيات التداول للمستخدم

    ✅ عزل كامل: WHERE user_id = %s
    ✅ حساب من جدول active_positions (المصدر الوحيد للبيانات)

    Returns:
        {
            "success": true,
            "data": {
                "activeTrades": 5,
                "totalTrades": 100,
                "winRate": 65.5
            }
        }
    """
    # التحقق من أن المستخدم يطلب بياناته فقط
    if not verify_user_access(user_id):
        response_data, status_code = error_response(
            "لا توجد صلاحيات", "UNAUTHORIZED", 403
        )
        return jsonify(response_data), status_code

    # ✅ قراءة mode من query parameters (للأدمن)
    requested_mode = request.args.get("mode", None)

    try:
        # ✅ استخدام db_manager المُعرّف مسبقاً
        db = db_manager

        trading_context = get_trading_context(
            db, user_id, requested_mode=requested_mode
        )
        is_admin = trading_context["is_admin"]
        is_demo = trading_context["is_demo"]
        portfolio_owner_id = trading_context["portfolio_owner_id"]
        key_state = _resolve_key_state(db, user_id, is_admin, bool(is_demo))
        resolved_mode = (
            requested_mode
            if requested_mode in ("demo", "real")
            else ("demo" if bool(is_demo) else "real")
        )
        cache_key = f"stats_{user_id}_{resolved_mode}"

        # ✅ محاولة الحصول من Cache بعد حسم الوضع الفعلي (تجنب خلط real/demo)
        if CACHE_AVAILABLE:
            cached_data = response_cache.get(cache_key)
            if cached_data:
                logger.debug(
                    f"✅ Stats من Cache للمستخدم {user_id} mode={resolved_mode}"
                )
                response_data, status_code = success_response(
                    cached_data, "تم جلب الإحصائيات من الذاكرة المؤقتة"
                )
                return jsonify(response_data), status_code

        def load_stats_base_balances(owner_id, demo_flag):
            try:
                base_query = "SELECT initial_balance, total_balance FROM portfolio WHERE user_id = %s AND is_demo = %s"
                rows = db.execute_query(base_query, (owner_id, demo_flag == 1))
                if rows and len(rows) > 0:
                    return rows[0]
            except Exception:
                pass
            return {}

        if is_admin:
            # ✅ الأدمن الحقيقي يتبع نفس قاعدة المستخدم الحقيقي: مفاتيح Binance مطلوبة
            if not is_demo:
                keys = db.get_binance_keys(user_id)
                if not keys:
                    base_row = load_stats_base_balances(portfolio_owner_id, is_demo)
                    initial_balance = float(base_row.get("initial_balance") or 0.0)
                    current_balance = float(
                        base_row.get("total_balance") or initial_balance or 0.0
                    )
                    payload = {
                        "requiresSetup": True,
                        "message": "أضف مفاتيح Binance للبدء",
                        "hasConfiguredDbKeys": key_state["has_configured_db_keys"],
                        "usingEnvTestKeys": key_state["using_env_test_keys"],
                        "keysRequiredForCurrentMode": key_state[
                            "keys_required_for_current_mode"
                        ],
                        "activeTrades": 0,
                        "totalTrades": 0,
                        "closedTrades": 0,
                        "winningTrades": 0,
                        "losingTrades": 0,
                        "winRate": 0.0,
                        "successRate": "0.0%",
                        "averageProfit": 0.0,
                        "totalProfit": 0.0,
                        "totalProfitLoss": 0.0,
                        "realizedPnL": 0.0,
                        "unrealizedPnL": 0.0,
                        "bestTrade": 0.0,
                        "worstTrade": 0.0,
                        "profitFactor": 0.0,
                        "portfolioGrowth": 0.0,
                        "portfolioGrowthPct": 0.0,
                        "initialBalance": round(initial_balance, 2),
                        "currentBalance": round(current_balance, 2),
                    }
                    response_data, status_code = success_response(
                        payload, "يتطلب إعداد مفاتيح Binance"
                    )
                    return jsonify(response_data), status_code
        else:
            # ✅ المستخدم العادي: Real فقط - التحقق من المفاتيح
            keys = db.get_binance_keys(user_id)
            if not keys:
                # ❌ بدون مفاتيح = لا بيانات
                response_data, status_code = success_response(
                    {
                        "requiresSetup": True,
                        "message": "أضف مفاتيح Binance للبدء",
                        "hasConfiguredDbKeys": key_state["has_configured_db_keys"],
                        "usingEnvTestKeys": key_state["using_env_test_keys"],
                        "keysRequiredForCurrentMode": key_state[
                            "keys_required_for_current_mode"
                        ],
                        "totalTrades": 0,
                        "activeTrades": 0,
                        "winningTrades": 0,
                        "losingTrades": 0,
                        "closedTrades": 0,
                        "successRate": "0.0%",
                        "averageProfit": 0.0,
                        "totalProfit": 0.0,
                        "totalProfitLoss": 0.0,
                        "realizedPnL": 0.0,
                        "unrealizedPnL": 0.0,
                        "bestTrade": 0.0,
                        "worstTrade": 0.0,
                        "profitFactor": 0.0,
                        "portfolioGrowth": 0.0,
                        "portfolioGrowthPct": 0.0,
                        "initialBalance": 0.0,
                        "currentBalance": 0.0,
                        "winRate": 0.0,
                    },
                    "يتطلب إعداد مفاتيح Binance",
                )
                return jsonify(response_data), status_code

            is_demo = 0

        # حساب الإحصائيات حسب الوضع — يقرأ من active_positions (المصدر الوحيد
        # للبيانات)
        stats_query = """
            SELECT
                SUM(CASE WHEN is_active = FALSE THEN 1 ELSE 0 END) as closed_trades,
                SUM(CASE WHEN is_active = FALSE AND profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN is_active = FALSE AND profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
                AVG(CASE WHEN is_active = FALSE THEN profit_loss ELSE NULL END) as avg_profit,
                SUM(CASE WHEN is_active = FALSE THEN profit_loss ELSE 0 END) as total_profit,
                MAX(CASE WHEN is_active = FALSE THEN profit_loss ELSE NULL END) as best_trade,
                MIN(CASE WHEN is_active = FALSE THEN profit_loss ELSE NULL END) as worst_trade,
                MIN(COALESCE(entry_date, created_at)) as first_trade_date,
                COALESCE(SUM(CASE WHEN is_active = FALSE AND profit_loss > 0 THEN profit_loss ELSE 0 END), 0) as gross_profit,
                COALESCE(ABS(SUM(CASE WHEN is_active = FALSE AND profit_loss < 0 THEN profit_loss ELSE 0 END)), 0) as gross_loss
            FROM active_positions
            WHERE user_id = %s AND is_demo = %s
        """

        active_trades_query = """
            SELECT COUNT(*) as active_trades
            FROM active_positions
            WHERE user_id = %s AND is_demo = %s AND is_active = TRUE
        """

        stats_result = db.execute_query(
            stats_query, (portfolio_owner_id, bool(is_demo))
        )
        active_result = db.execute_query(
            active_trades_query, (portfolio_owner_id, bool(is_demo))
        )
        pnl_snapshot = db._calculate_user_pnl(portfolio_owner_id, is_demo)

        if is_demo:
            portfolio_result = db.execute_query(
                """
                SELECT initial_balance, total_balance, first_trade_balance, first_trade_at, initial_balance_source
                FROM portfolio
                WHERE user_id = %s AND is_demo = TRUE
                """,
                (portfolio_owner_id,),
            )
        else:
            portfolio_result = db.execute_query(
                """
                SELECT initial_balance, total_balance, first_trade_balance, first_trade_at, initial_balance_source
                FROM portfolio
                WHERE user_id = %s AND is_demo = %s
                """,
                (portfolio_owner_id, bool(is_demo)),
            )
        initial_balance = 0.0
        current_balance = 0.0
        first_trade_balance = 0.0
        first_trade_at = None
        initial_balance_source = "demo_account_seed" if is_demo else "system_seed"
        if portfolio_result and len(portfolio_result) > 0:
            initial_balance_raw = portfolio_result[0].get("initial_balance")
            current_balance_raw = portfolio_result[0].get("total_balance")
            first_trade_balance_raw = portfolio_result[0].get("first_trade_balance")
            first_trade_at = portfolio_result[0].get("first_trade_at")
            initial_balance_source = (
                portfolio_result[0].get("initial_balance_source")
                or initial_balance_source
            )

            initial_balance = (
                float(initial_balance_raw) if initial_balance_raw is not None else 0.0
            )
            current_balance = (
                float(current_balance_raw) if current_balance_raw is not None else 0.0
            )
            first_trade_balance = (
                float(first_trade_balance_raw)
                if first_trade_balance_raw is not None
                else 0.0
            )

        if stats_result and len(stats_result) > 0:
            stats = stats_result[0]
            active_trades = int(
                (active_result[0].get("active_trades", 0) if active_result else 0) or 0
            )
            closed_trades = int((stats.get("closed_trades", 0) or 0))
            total_trades = active_trades + closed_trades

            # حساب معدل النجاح
            win_rate = 0.0
            success_rate = 0.0
            if closed_trades > 0:
                win_rate = ((stats.get("winning_trades", 0) or 0) / closed_trades) * 100
                success_rate = win_rate

            portfolio_growth = 0.0
            portfolio_growth_pct = 0.0
            realized_pnl = float(pnl_snapshot.get("realized_pnl", 0) or 0)
            unrealized_pnl = float(pnl_snapshot.get("unrealized_pnl", 0) or 0)
            total_profit = float(pnl_snapshot.get("total_pnl", 0) or 0)

            has_system_activity = total_trades > 0
            if has_system_activity:
                portfolio_growth = total_profit
                if initial_balance is not None and initial_balance > 0:
                    portfolio_growth_pct = (portfolio_growth / initial_balance) * 100

            gross_profit = float(stats.get("gross_profit", 0) or 0)
            gross_loss = float(stats.get("gross_loss", 0) or 0)
            profit_factor = (
                round(gross_profit / gross_loss, 2)
                if gross_loss > 0
                else (999.0 if gross_profit > 0 else 0.0)
            )

            data = {
                "activeTrades": active_trades,
                "totalTrades": total_trades,
                "winRate": round(win_rate, 1),
                "successRate": f"{round(success_rate, 1)}%",
                "closedTrades": closed_trades,
                "winningTrades": stats.get("winning_trades", 0) or 0,
                "losingTrades": stats.get("losing_trades", 0) or 0,
                "averageProfit": (
                    round(stats["avg_profit"], 2) if stats["avg_profit"] else 0.00
                ),
                "totalProfit": round(total_profit, 2),
                "totalProfitLoss": round(total_profit, 2),
                "realizedPnL": round(realized_pnl, 2),
                "unrealizedPnL": round(unrealized_pnl, 2),
                "bestTrade": (
                    round(stats["best_trade"], 2) if stats["best_trade"] else 0.00
                ),
                "worstTrade": (
                    round(stats["worst_trade"], 2) if stats["worst_trade"] else 0.00
                ),
                "profitFactor": profit_factor,
                "portfolioGrowth": round(portfolio_growth, 2),
                "portfolioGrowthPct": round(portfolio_growth_pct, 2),
                "initialBalance": round(initial_balance, 2),
                "currentBalance": round(current_balance, 2),
                "firstTradeDate": first_trade_at or stats["first_trade_date"],
                "firstTradeBalance": round(first_trade_balance, 2),
                "initialBalanceSource": initial_balance_source,
                "hasConfiguredDbKeys": key_state["has_configured_db_keys"],
                "usingEnvTestKeys": key_state["using_env_test_keys"],
                "keysRequiredForCurrentMode": key_state[
                    "keys_required_for_current_mode"
                ],
                "isGrowing": portfolio_growth > 0,
            }

            # ✅ حفظ في Cache مع توحيد Cache Key + Dynamic TTL
            if CACHE_AVAILABLE:
                response_cache.set(cache_key, data, ttl=30, user_id=user_id)

            response_data, status_code = success_response(
                data, "تم جلب الإحصائيات بنجاح"
            )
            return jsonify(response_data), status_code
        else:
            data = {
                "activeTrades": 0,
                "totalTrades": 0,
                "winRate": 0.0,
                "successRate": "0.0%",
                "closedTrades": 0,
                "winningTrades": 0,
                "losingTrades": 0,
                "averageProfit": 0.00,
                "totalProfit": 0.00,
                "totalProfitLoss": 0.00,
                "realizedPnL": 0.0,
                "unrealizedPnL": 0.0,
                "bestTrade": 0.00,
                "worstTrade": 0.00,
                "hasConfiguredDbKeys": key_state["has_configured_db_keys"],
                "usingEnvTestKeys": key_state["using_env_test_keys"],
                "keysRequiredForCurrentMode": key_state[
                    "keys_required_for_current_mode"
                ],
                "firstTradeDate": None,
                "firstTradeBalance": 0.0,
                "initialBalanceSource": (
                    "demo_account_seed" if is_demo else "system_seed"
                ),
            }

            # ✅ حفظ في Cache مع Dynamic TTL
            if CACHE_AVAILABLE:
                response_cache.set(cache_key, data, ttl=30, user_id=user_id)

            response_data, status_code = success_response(
                data, "تم جلب الإحصائيات بنجاح"
            )
            return jsonify(response_data), status_code

    except Exception as e:
        logger.error(f"❌ خطأ في جلب الإحصائيات للمستخدم {user_id}: {e}")
        response_data, status_code = error_response(
            "خطأ في جلب الإحصائيات", "STATS_ERROR", 500
        )
        return jsonify(response_data), status_code


# ==================== العملات الناجحة (Successful Coins) ====================


@mobile_bp.route("/successful-coins/<int:user_id>", methods=["GET"])
@require_auth
@rate_limit_data
def get_successful_coins(user_id):
    """
    الحصول على قائمة العملات الناجحة (من Group B)

    ✅ مشترك لجميع المستخدمين (من successful_coins)
    ✅ لكن يتم التحقق من هوية المستخدم

    Returns:
        {
            "success": true,
            "data": {
                "coins": [...],
                "total_count": 10,
                "last_update": "..."
            }
        }
    """
    # التحقق من أن المستخدم يطلب بياناته
    if not verify_user_access(user_id):
        return jsonify({"success": False, "error": "Unauthorized access"}), 403

    try:
        # ✅ استخدام db_manager المُعرّف مسبقاً
        db = db_manager

        # جلب العملات الناجحة (مشتركة لجميع المستخدمين)
        # ✅ توحيد أسماء الحقول لتطابق التطبيق
        coins_query = """
            SELECT
                symbol,
                'scalping' as strategy,
                score,
                profit_pct,
                win_rate,
                0 as sharpe_ratio,
                0 as max_drawdown,
                total_trades,
                timeframe,
                analysis_date,
                market_trend,
                avg_trade_duration_hours,
                trading_style
            FROM successful_coins
            WHERE is_active = TRUE
            ORDER BY score DESC, analysis_date DESC
            LIMIT 10
        """

        try:
            coins_result = db.execute_query(coins_query)
        except Exception as e:
            # إذا كان الجدول غير موجود، أرجع بيانات فارغة
            logger.debug(f"جدول successful_coins قد يكون غير موجود: {e}")
            coins_result = []

        coins_list = []
        if coins_result:
            for coin in coins_result:
                # ✅ معالجة آمنة للحقول
                coins_list.append(
                    {
                        "symbol": coin.get("symbol"),
                        "strategy": coin.get("strategy", "unknown"),
                        "score": coin.get("score", 0),
                        "profit_pct": coin.get("profit_pct", 0),
                        "win_rate": coin.get("win_rate", 0),
                        "sharpe_ratio": coin.get("sharpe_ratio", 0),
                        "max_drawdown": coin.get("max_drawdown", 0),
                        "total_trades": coin.get("total_trades", 0),
                        "timeframe": coin.get("timeframe", "1h"),
                        "analysis_date": coin.get("analysis_date"),
                        "market_trend": coin.get("market_trend", "neutral"),
                        "avg_trade_duration_hours": coin.get(
                            "avg_trade_duration_hours", 0.0
                        ),
                        "trading_style": coin.get("trading_style", "swing"),
                    }
                )

        # آخر تحديث
        last_update = (
            coins_result[0]["analysis_date"]
            if coins_result and len(coins_result) > 0
            else None
        )

        return jsonify(
            {
                "success": True,
                "data": {
                    "coins": coins_list,
                    "total_count": len(coins_list),
                    "last_update": last_update,
                },
            }
        )

    except Exception as e:
        logger.error(f"❌ خطأ في جلب العملات الناجحة: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== Sub-routes registration (God Object split) ========


def _build_shared_context():
    """Build shared context dict for sub-route modules"""
    return {
        "db_manager": db_manager,
        "verify_user_access": verify_user_access,
        "require_auth": require_auth,
        "rate_limit_general": (
            rate_limit_general if RATE_LIMITER_AVAILABLE else (lambda f: f)
        ),
        "rate_limit_trading": (
            rate_limit_trading if RATE_LIMITER_AVAILABLE else (lambda f: f)
        ),
        "rate_limit_data": (
            rate_limit_data if RATE_LIMITER_AVAILABLE else (lambda f: f)
        ),
        "rate_limit_auth": (
            rate_limit_auth if RATE_LIMITER_AVAILABLE else (lambda f: f)
        ),
        "success_response": success_response,
        "error_response": error_response,
        "require_idempotency": require_idempotency,
        "prevent_concurrent_duplicates": prevent_concurrent_duplicates,
        "CACHE_AVAILABLE": CACHE_AVAILABLE,
        "response_cache": response_cache,
        "ENCRYPTION_AVAILABLE": ENCRYPTION_AVAILABLE,
        "audit_logger": audit_logger,
    }


# Register all sub-route modules
_shared = _build_shared_context()

register_mobile_trades_routes(mobile_bp, _shared)

register_mobile_settings_routes(mobile_bp, _shared)

register_mobile_notifications_routes(mobile_bp, _shared)

register_mobile_auth_routes(mobile_bp, _shared)
