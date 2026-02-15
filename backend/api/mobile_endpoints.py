"""
Mobile API Endpoints - Trading AI Bot
=====================================
نقاط نهاية API للتطبيق المحمول مع عزل كامل للبيانات

✅ كل مستخدم يرى بياناته فقط
✅ التحقق من الهوية في كل طلب
✅ عزل كامل بـ WHERE user_id = ?
"""

from flask import Blueprint, request, jsonify, g
import logging
import sqlite3
import sys
from datetime import datetime, timedelta
from functools import wraps
import jwt
from backend.utils.response_formatter import success_response, error_response, paginated_response
from backend.utils.unified_error_handler import handle_errors, ValidationError, NotFoundError, AuthenticationError
from backend.utils.idempotency_manager import require_idempotency
from backend.utils.request_deduplicator import prevent_concurrent_duplicates
from config.logging_config import log_api_error
import os

# ✅ Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# إضافة مسار config للوصول لخدمة التشفير
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Database
from database.database_manager import DatabaseManager
db_manager = DatabaseManager()

# User lookup service
from backend.utils.user_lookup_service import get_user_by_email

# ✅ Phase 1: Safe Logger (يخفي البيانات الحساسة)
from backend.utils.safe_logger import SafeLogger
logger = SafeLogger(__name__)

# ✅ Phase 2: Request Validation & Error Handling
from pydantic import ValidationError
try:
    from backend.api.schemas import (
        UserSettingsUpdate,
        BinanceKeysCreate,
        TradesQueryParams,
        NotificationSettingsUpdate,
        ProfileUpdate,
        ChangePasswordRequest
    )
    from backend.utils.error_handler import (
        ErrorMessages,
        HTTPStatus
    )
    VALIDATION_AVAILABLE = True
    logger.info("✅ Request Validation & Error Handling متاح")
except ImportError as e:
    VALIDATION_AVAILABLE = False
    logger.warning(f"⚠️ Request Validation غير متاح: {e}")

# ✅ Input Validation - التحقق من صحة البيانات المدخلة
try:
    from backend.utils.validation_schemas import (
        TradeValidator,
        APIValidator,
        StrategyValidator,
        UserValidator,
        validate_input
    )
    INPUT_VALIDATION_AVAILABLE = True
    logger.info("✅ Input Validation System متاح")
except ImportError as e:
    INPUT_VALIDATION_AVAILABLE = False
    logger.warning(f"⚠️ Input Validation غير متاح: {e}")

# إنشاء Blueprint بدون /api (لأن Flask مثبت على /api في unified_server.py)
mobile_bp = Blueprint('mobile', __name__, url_prefix='/user')

# Audit Logger
try:
    from backend.utils.audit_logger import audit_logger
except (ImportError, ModuleNotFoundError):
    audit_logger = None


# ✅ تهيئة Rate Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # حد افتراضي
    storage_uri="memory://"  # تخزين في الذاكرة
)

# استيراد Rate Limiter Helper
try:
    from backend.utils.rate_limiter_helper import (
        rate_limit_general,
        rate_limit_trading,
        rate_limit_data,
        rate_limit_auth
    )
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False
    logger.warning("⚠️ Rate Limiter Helper غير متاح")

# استيراد نظام Token
from backend.api.auth_middleware import require_auth

# استيراد خدمة التشفير
try:
    from config.security.encryption_service import encrypt_binance_keys, decrypt_binance_keys
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
    """
    if g.current_user_id != user_id:
        logger.warning(f"⚠️ محاولة وصول غير مصرح: User {g.current_user_id} حاول الوصول لبيانات User {user_id}")
        return False
    return True


# ==================== المحفظة (Portfolio) ====================

@mobile_bp.route('/portfolio/<int:user_id>', methods=['GET'])
@require_auth
@rate_limit_data
def get_user_portfolio(user_id):
    """
    الحصول على بيانات محفظة المستخدم
    
    ✅ عزل كامل: WHERE user_id = ?
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
        response_data, status_code = error_response('لا توجد صلاحيات', 'UNAUTHORIZED', 403)
        return jsonify(response_data), status_code
    
    # ✅ قراءة mode من query parameters (للأدمن)
    requested_mode = request.args.get('mode', None)
    
    # ✅ محاولة الحصول من Cache أولاً
    if CACHE_AVAILABLE:
        cache_key = f"portfolio_{user_id}_{requested_mode}" if requested_mode else f"portfolio_{user_id}"
        cached_data = response_cache.get(cache_key)
        if cached_data:
            logger.debug(f"✅ Portfolio من Cache للمستخدم {user_id}")
            response_data, status_code = success_response(cached_data, 'تم جلب المحفظة من الذاكرة المؤقتة')
            return jsonify(response_data), status_code
    
    try:
        # ✅ استخدام db_manager المُعرّف مسبقاً بدلاً من إنشاء instance جديد
        db = db_manager
        
        # ✅ تحديد is_demo من trading_mode للأدمن
        user_data = db.get_user_by_id(user_id)
        if not user_data:
            return error_response('المستخدم غير موجود', 'NOT_FOUND', 404)
        
        is_admin = user_data.get('user_type') == 'admin'
        is_demo = None
        
        if is_admin:
            # ✅ الأدمن: يمكنه التبديل بين Demo و Real
            if requested_mode:
                is_demo = 1 if requested_mode == 'demo' else 0
            else:
                # استخدام الوضع المحفوظ في الإعدادات
                settings = db.get_trading_settings(user_id)
                if settings:
                    trading_mode = settings.get('trading_mode', 'auto')
                    if trading_mode == 'demo':
                        is_demo = 1
                    elif trading_mode == 'real':
                        is_demo = 0
                    else:  # auto
                        keys = db.get_binance_keys(user_id)
                        is_demo = 0 if keys else 1
        else:
            # ✅ المستخدم العادي: Real فقط - التحقق من المفاتيح أولاً
            keys = db.get_binance_keys(user_id)
            if not keys:
                # ❌ بدون مفاتيح = لا بيانات
                response_data, status_code = success_response({
                    'requiresSetup': True,
                    'message': 'أضف مفاتيح Binance للبدء',
                    'hasBinanceKeys': False
                }, 'يتطلب إعداد مفاتيح Binance')
                return jsonify(response_data), status_code
            
            # مع مفاتيح → جلب البيانات الحقيقية
            is_demo = 0
        
        # ✅ جلب بيانات المحفظة حسب الوضع (demo/real)
        portfolio_data = db.get_user_portfolio(user_id, is_demo)
        
        if not portfolio_data:
            return error_response('المحفظة غير موجودة', 'NOT_FOUND', 404)
        
        if portfolio_data.get('error'):
            return error_response(portfolio_data.get('message', 'خطأ غير معروف'), 'PORTFOLIO_ERROR', 400)
        
        # ✅ استخراج البيانات بشكل آمن
        has_keys = portfolio_data.get('hasKeys', False)
        
        # تحويل آمن للقيم
        def safe_float(value, default=0.0):
            try:
                if isinstance(value, str):
                    return float(value.replace(',', '').replace('+', '').replace('%', ''))
                return float(value) if value else default
            except (ValueError, AttributeError, TypeError):
                return default
        
        total_balance = safe_float(portfolio_data.get('totalBalance', '0.00'))
        available_balance = safe_float(portfolio_data.get('availableBalance', '0.00'))
        locked_balance = safe_float(portfolio_data.get('lockedBalance', '0.00'))
        daily_pnl = safe_float(portfolio_data.get('dailyPnL', '+0.00'))
        daily_pnl_pct = safe_float(portfolio_data.get('dailyPnLPercentage', '+0.0'))
        total_pnl = safe_float(portfolio_data.get('totalPnL', '0.00'))
        
        # ✅ جلب الرصيد الأولي + المستثمر من جدول portfolio
        initial_balance = safe_float(portfolio_data.get('initialBalance', '0.00'))
        invested_balance = safe_float(portfolio_data.get('investedBalance', '0.00'))
        if initial_balance == 0 or invested_balance == 0:
            try:
                extra = db.execute_query(
                    "SELECT initial_balance, invested_balance FROM portfolio WHERE user_id = ? AND is_demo = ?",
                    (user_id, is_demo)
                )
                if extra and len(extra) > 0:
                    if initial_balance == 0:
                        initial_balance = safe_float(extra[0].get('initial_balance', 0))
                    if invested_balance == 0:
                        invested_balance = safe_float(extra[0].get('invested_balance', 0))
            except Exception:
                pass
        
        # ✅ FIX: حساب totalPnL و totalPnLPercentage بشكل موحد من البيانات الفعلية
        # totalPnL = totalBalance - initialBalance (الربح/الخسارة الفعلية)
        total_pnl = total_balance - initial_balance if initial_balance > 0 else total_pnl
        total_pnl_pct = (total_pnl / initial_balance * 100) if initial_balance > 0 else 0.0
        
        # ✅ البيانات الكاملة للـ Frontend (Dashboard + PortfolioScreen)
        # ✅ FIX: إرجاع أرقام حقيقية (float) بدلاً من نصوص — حتى يتمكن الـ Frontend من الحساب مباشرة
        data = {
            'totalBalance': round(total_balance, 2),
            'initialBalance': round(initial_balance, 2),
            'availableBalance': round(available_balance, 2),
            'lockedBalance': round(locked_balance, 2),
            'investedBalance': round(invested_balance, 2),
            'dailyPnL': round(daily_pnl, 2),
            'dailyPnLPercentage': round(daily_pnl_pct, 2),
            'totalPnL': round(total_pnl, 2),
            'totalPnLPercentage': round(total_pnl_pct, 2),
            'hasKeys': has_keys,
            'lastUpdate': portfolio_data.get('lastUpdate')
        }
        
        # ✅ حفظ في Cache مع توحيد Cache Key + Dynamic TTL
        if CACHE_AVAILABLE:
            cache_key = f"portfolio_{user_id}_{requested_mode}" if requested_mode else f"portfolio_{user_id}"
            response_cache.set(cache_key, data, ttl=300, user_id=user_id)
        
        response_data, status_code = success_response(data, 'تم جلب المحفظة بنجاح')
        return jsonify(response_data), status_code
        
    except Exception as e:
        log_api_error(logger, 'get_user_portfolio', user_id, e)
        response_data, status_code = error_response('خطأ في جلب المحفظة', 'PORTFOLIO_ERROR', 500)
        return jsonify(response_data), status_code


# ==================== الإحصائيات (Stats) ====================

@mobile_bp.route('/stats/<int:user_id>', methods=['GET'])
@require_auth
@rate_limit_data
def get_user_stats(user_id):
    """
    الحصول على إحصائيات التداول للمستخدم
    
    ✅ عزل كامل: WHERE user_id = ?
    ✅ حساب من جدول user_trades فقط
    
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
        response_data, status_code = error_response('لا توجد صلاحيات', 'UNAUTHORIZED', 403)
        return jsonify(response_data), status_code
    
    # ✅ قراءة mode من query parameters (للأدمن)
    requested_mode = request.args.get('mode', None)
    
    # ✅ محاولة الحصول من Cache
    if CACHE_AVAILABLE:
        cache_key = f"stats_{user_id}_{requested_mode}" if requested_mode else f"stats_{user_id}"
        cached_data = response_cache.get(cache_key)
        if cached_data:
            logger.debug(f"✅ Stats من Cache للمستخدم {user_id}")
            response_data, status_code = success_response(cached_data, 'تم جلب الإحصائيات من الذاكرة المؤقتة')
            return jsonify(response_data), status_code
    
    try:
        # ✅ استخدام db_manager المُعرّف مسبقاً
        db = db_manager
        
        # ✅ تحديد is_demo من trading_mode
        user_data = db.get_user_by_id(user_id)
        is_admin = user_data.get('user_type') == 'admin' if user_data else False
        
        is_demo = None
        if is_admin:
            # ✅ إذا تم تمرير mode في الطلب، استخدمه مباشرة
            if requested_mode:
                is_demo = 1 if requested_mode == 'demo' else 0
            else:
                settings = db.get_trading_settings(user_id)
                trading_mode = settings.get('trading_mode', 'auto') if settings else 'auto'
                if trading_mode == 'demo':
                    is_demo = 1
                elif trading_mode == 'real':
                    is_demo = 0
                else:  # auto
                    keys = db.get_binance_keys(user_id)
                    is_demo = 0 if keys else 1
        else:
            # ✅ المستخدم العادي: Real فقط - التحقق من المفاتيح
            keys = db.get_binance_keys(user_id)
            if not keys:
                # ❌ بدون مفاتيح = لا بيانات
                response_data, status_code = success_response({
                    'requiresSetup': True,
                    'message': 'أضف مفاتيح Binance للبدء',
                    'totalTrades': 0,
                    'activeTrades': 0,
                    'winningTrades': 0,
                    'losingTrades': 0,
                    'closedTrades': 0,
                    'totalProfit': 0.0,
                    'winRate': 0.0
                }, 'يتطلب إعداد مفاتيح Binance')
                return jsonify(response_data), status_code
            
            is_demo = 0
        
        # حساب الإحصائيات حسب الوضع
        stats_query = """
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as active_trades,
                SUM(CASE WHEN status = 'closed' AND profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN status = 'closed' AND profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_trades,
                AVG(CASE WHEN status = 'closed' THEN profit_loss ELSE NULL END) as avg_profit,
                SUM(CASE WHEN status = 'closed' THEN profit_loss ELSE 0 END) as total_profit,
                MAX(CASE WHEN status = 'closed' THEN profit_loss ELSE NULL END) as best_trade,
                MIN(CASE WHEN status = 'closed' THEN profit_loss ELSE NULL END) as worst_trade,
                MIN(entry_time) as first_trade_date
            FROM user_trades
            WHERE user_id = ? AND is_demo = ?
        """
        
        stats_result = db.execute_query(stats_query, (user_id, is_demo))
        
        # ✅ جلب الرصيد الأولي عند أول تداول (لحساب نمو المحفظة)
        initial_balance_query = """
            SELECT initial_balance, total_balance 
            FROM portfolio 
            WHERE user_id = ? AND is_demo = ?
        """
        portfolio_result = db.execute_query(initial_balance_query, (user_id, is_demo))
        initial_balance = 0.0
        current_balance = 0.0
        if portfolio_result and len(portfolio_result) > 0:
            initial_balance = float(portfolio_result[0].get('initial_balance') or 0)
            current_balance = float(portfolio_result[0].get('total_balance') or 0)
        
        if stats_result and len(stats_result) > 0:
            stats = stats_result[0]
            
            # حساب معدل النجاح
            win_rate = 0.0
            success_rate = 0.0
            if stats['closed_trades'] and stats['closed_trades'] > 0:
                win_rate = (stats['winning_trades'] / stats['closed_trades']) * 100
                success_rate = win_rate
            
            # ✅ حساب نمو المحفظة من أول تداول
            portfolio_growth = 0.0
            portfolio_growth_pct = 0.0
            total_profit = float(stats['total_profit'] or 0)
            
            if initial_balance > 0:
                # النمو = (الرصيد الحالي - الرصيد الأولي) / الرصيد الأولي * 100
                portfolio_growth = current_balance - initial_balance
                portfolio_growth_pct = (portfolio_growth / initial_balance) * 100
            elif total_profit != 0:
                # إذا لم يكن هناك رصيد أولي، نستخدم إجمالي الأرباح
                portfolio_growth = total_profit
            
            data = {
                'activeTrades': stats['active_trades'] or 0,
                'totalTrades': stats['total_trades'] or 0,
                'winRate': round(win_rate, 1),
                'successRate': f"{round(success_rate, 1)}%",
                'closedTrades': stats['closed_trades'] or 0,
                'winningTrades': stats['winning_trades'] or 0,
                'losingTrades': stats['losing_trades'] or 0,
                'averageProfit': round(stats['avg_profit'], 2) if stats['avg_profit'] else 0.00,
                'totalProfit': round(total_profit, 2),
                'bestTrade': round(stats['best_trade'], 2) if stats['best_trade'] else 0.00,
                'worstTrade': round(stats['worst_trade'], 2) if stats['worst_trade'] else 0.00,
                # ✅ بيانات نمو المحفظة الجديدة
                'portfolioGrowth': round(portfolio_growth, 2),
                'portfolioGrowthPct': round(portfolio_growth_pct, 2),
                'initialBalance': round(initial_balance, 2),
                'currentBalance': round(current_balance, 2),
                'firstTradeDate': stats['first_trade_date'],
                'isGrowing': portfolio_growth > 0
            }
            
            # ✅ حفظ في Cache مع توحيد Cache Key + Dynamic TTL
            if CACHE_AVAILABLE:
                cache_key = f"stats_{user_id}_{requested_mode}" if requested_mode else f"stats_{user_id}"
                response_cache.set(cache_key, data, ttl=300, user_id=user_id)
            
            response_data, status_code = success_response(data, 'تم جلب الإحصائيات بنجاح')
            return jsonify(response_data), status_code
        else:
            data = {
                'activeTrades': 0,
                'totalTrades': 0,
                'winRate': 0.0,
                'successRate': '0.0%',
                'closedTrades': 0,
                'winningTrades': 0,
                'losingTrades': 0,
                'averageProfit': 0.00,
                'totalProfit': 0.00,
                'bestTrade': 0.00,
                'worstTrade': 0.00
            }
            
            # ✅ حفظ في Cache مع Dynamic TTL
            if CACHE_AVAILABLE:
                cache_key = f"stats_{user_id}"
                response_cache.set(cache_key, data, ttl=300, user_id=user_id)
            
            response_data, status_code = success_response(data, 'تم جلب الإحصائيات بنجاح')
            return jsonify(response_data), status_code
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الإحصائيات للمستخدم {user_id}: {e}")
        response_data, status_code = error_response('خطأ في جلب الإحصائيات', 'STATS_ERROR', 500)
        return jsonify(response_data), status_code


# ==================== العملات الناجحة (Successful Coins) ====================

@mobile_bp.route('/successful-coins/<int:user_id>', methods=['GET'])
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
        return jsonify({
            'success': False,
            'error': 'Unauthorized access'
        }), 403
    
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
            WHERE is_active = 1
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
                coins_list.append({
                    'symbol': coin.get('symbol'),
                    'strategy': coin.get('strategy', 'unknown'),
                    'score': coin.get('score', 0),
                    'profit_pct': coin.get('profit_pct', 0),
                    'win_rate': coin.get('win_rate', 0),
                    'sharpe_ratio': coin.get('sharpe_ratio', 0),
                    'max_drawdown': coin.get('max_drawdown', 0),
                    'total_trades': coin.get('total_trades', 0),
                    'timeframe': coin.get('timeframe', '1h'),
                    'analysis_date': coin.get('analysis_date'),
                    'market_trend': coin.get('market_trend', 'neutral'),
                    'avg_trade_duration_hours': coin.get('avg_trade_duration_hours', 0.0),
                    'trading_style': coin.get('trading_style', 'swing')
                })
        
        # آخر تحديث
        last_update = coins_result[0]['analysis_date'] if coins_result and len(coins_result) > 0 else None
        
        return jsonify({
            'success': True,
            'data': {
                'coins': coins_list,
                'total_count': len(coins_list),
                'last_update': last_update
            }
        })
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب العملات الناجحة: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500



# ==================== Sub-routes registration (God Object split) ====================

def _build_shared_context():
    """Build shared context dict for sub-route modules"""
    return {
        'db_manager': db_manager,
        'verify_user_access': verify_user_access,
        'require_auth': require_auth,
        'rate_limit_general': rate_limit_general if RATE_LIMITER_AVAILABLE else (lambda f: f),
        'rate_limit_trading': rate_limit_trading if RATE_LIMITER_AVAILABLE else (lambda f: f),
        'rate_limit_data': rate_limit_data if RATE_LIMITER_AVAILABLE else (lambda f: f),
        'rate_limit_auth': rate_limit_auth if RATE_LIMITER_AVAILABLE else (lambda f: f),
        'success_response': success_response,
        'error_response': error_response,
        'require_idempotency': require_idempotency,
        'prevent_concurrent_duplicates': prevent_concurrent_duplicates,
        'CACHE_AVAILABLE': CACHE_AVAILABLE,
        'response_cache': response_cache,
        'ENCRYPTION_AVAILABLE': ENCRYPTION_AVAILABLE,
        'audit_logger': audit_logger,
    }

# Register all sub-route modules
_shared = _build_shared_context()

from backend.api.mobile_trades_routes import register_mobile_trades_routes
register_mobile_trades_routes(mobile_bp, _shared)

from backend.api.mobile_settings_routes import register_mobile_settings_routes
register_mobile_settings_routes(mobile_bp, _shared)

from backend.api.mobile_notifications_routes import register_mobile_notifications_routes
register_mobile_notifications_routes(mobile_bp, _shared)

from backend.api.mobile_auth_routes import register_mobile_auth_routes
register_mobile_auth_routes(mobile_bp, _shared)
