#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Exit System API Endpoints
نقاط نهاية API لنظام الإغلاق الذكي
"""

from backend.api.auth_middleware import require_auth
from config.logging_config import get_logger
from backend.strategies.intelligent_exit_system import (
    get_intelligent_exit_system,
)
from backend.infrastructure.db_access import get_db_manager
from flask import Blueprint, request, jsonify
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd

# إضافة مسارات المشروع
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "database"))


# استيراد نظام التحقق من التوكن

# إنشاء Blueprint
smart_exit_bp = Blueprint("smart_exit", __name__, url_prefix="/smart-exit")

# إعداد Logger
logger = get_logger(__name__)

# إعداد قاعدة البيانات
db = get_db_manager()


# ============================================================================
# 1. إعدادات المستخدم
# ============================================================================


@smart_exit_bp.route("/settings/<int:user_id>", methods=["GET"])
@require_auth
def get_smart_exit_settings(user_id):
    """جلب إعدادات النظام الذكي"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    stop_loss_pct,
                    take_profit_pct,
                    trailing_distance,
                    volatility_buffer,
                    min_signal_strength,
                    max_positions,
                    position_size_percentage,
                    trading_enabled,
                    daily_loss_limit
                FROM user_settings
                WHERE user_id = %s
            """,
                (user_id,),
            )

            result = cursor.fetchone()
            if result:
                settings = {
                    "stop_loss_pct": result[0] or 2.0,
                    "take_profit_pct": result[1] or 5.0,
                    "trailing_distance": result[2] or 3.0,
                    "volatility_buffer": result[3] or 0.3,
                    "min_signal_strength": result[4] or 0.6,
                    "max_positions": result[5] or 5,
                    "position_size_percentage": result[6] or 10.0,
                    "trading_enabled": result[7] or True,
                    "daily_loss_limit": result[8] or 100.0,
                }
                return jsonify({"success": True, "data": settings})
            else:
                return (
                    jsonify({"success": False, "error": "Settings not found"}),
                    404,
                )
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الإعدادات: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@smart_exit_bp.route("/settings/<int:user_id>", methods=["PUT"])
@require_auth
def update_smart_exit_settings(user_id):
    """تحديث إعدادات النظام الذكي"""
    try:
        data = request.get_json()

        # التحقق من البيانات وتحويلها إلى أرقام
        try:
            stop_loss_pct = float(data.get("stop_loss_pct", 2.0))
            take_profit_pct = float(data.get("take_profit_pct", 5.0))
            float(data.get("trailing_distance", 3.0))
            int(data.get("max_positions", 5))
        except (ValueError, TypeError) as e:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Invalid data types: {str(e)}",
                    }
                ),
                400,
            )

        # التحقق من الحدود المعقولة
        if stop_loss_pct < 0.5 or stop_loss_pct > 10:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Stop loss must be between 0.5% and 10%",
                    }
                ),
                400,
            )

        if take_profit_pct < 1 or take_profit_pct > 50:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Take profit must be between 1% and 50%",
                    }
                ),
                400,
            )

        with db.get_write_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE user_settings
                SET
                    stop_loss_pct = %s,
                    take_profit_pct = %s,
                    trailing_distance = %s,
                    volatility_buffer = %s,
                    min_signal_strength = %s,
                    max_positions = %s,
                    position_size_percentage = %s,
                    trading_enabled = %s,
                    daily_loss_limit = %s
                WHERE user_id = %s
            """,
                (
                    stop_loss_pct,
                    take_profit_pct,
                    data.get("trailing_distance", 3.0),
                    data.get("volatility_buffer", 0.3),
                    data.get("min_signal_strength", 0.6),
                    data.get("max_positions", 5),
                    data.get("position_size_percentage", 10.0),
                    data.get("trading_enabled", True),
                    data.get("daily_loss_limit", 100.0),
                    user_id,
                ),
            )
            conn.commit()

            logger.info(f"✅ تم تحديث إعدادات المستخدم {user_id}")
            return jsonify(
                {"success": True, "message": "Settings updated successfully"}
            )
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث الإعدادات: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# 2. فحص شروط الإغلاق
# ============================================================================


@smart_exit_bp.route("/check-exit/<int:user_id>/<symbol>", methods=["POST"])
@require_auth
def check_exit_conditions(user_id, symbol):
    """فحص شروط الإغلاق الذكية لصفقة معينة"""
    try:
        data = request.get_json() or {}

        # إنشاء نظام الإغلاق الذكي
        smart_exit = get_intelligent_exit_system()
        if not smart_exit:
            return (
                jsonify(
                    {"success": False, "error": "Exit system not available"}
                ),
                503,
            )

        entry_price = float(data.get("entry_price", 0.0) or 0.0)
        current_price = float(
            data.get("current_price", entry_price) or entry_price or 0.0
        )
        quantity = float(data.get("quantity", 0.0) or 0.0)

        if entry_price <= 0 or quantity <= 0:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "entry_price and quantity must be greater than zero",
                    }),
                400,
            )

        smart_exit.register_position(
            symbol=symbol,
            entry_price=entry_price,
            quantity=quantity,
            entry_time=datetime.now(),
        )

        df = pd.DataFrame(
            [
                {
                    "timestamp": datetime.now(),
                    "open": entry_price,
                    "high": max(entry_price, current_price),
                    "low": min(entry_price, current_price),
                    "close": current_price,
                    "volume": 1.0,
                    "ema_8": current_price,
                    "ema_21": entry_price,
                    "rsi": 50.0,
                    "macd": 0.0,
                    "macd_signal": 0.0,
                }
            ]
        )

        signal = smart_exit.check_intelligent_exit(
            symbol=symbol,
            current_price=current_price,
            df=df,
            idx=0,
            smaller_tf_data=None,
        )

        execution_supported = (
            signal.exit_pct >= 1.0 and signal.decision.value != "hold"
        )
        result = {
            "should_exit": execution_supported,
            "exit_type": signal.decision.value,
            "reason": signal.reason,
            "confidence": signal.confidence,
            "pnl_pct": signal.pnl_pct,
            "exit_price": signal.exit_price,
            "trailing_stop": signal.trailing_stop,
            "next_tp": signal.next_tp,
            "trend_status": signal.trend_status.value,
            "exit_pct": 1.0 if execution_supported else 0.0,
            "requested_exit_pct": signal.exit_pct,
            "execution_supported": execution_supported,
        }

        return jsonify(
            {
                "success": True,
                "should_exit": result.get("should_exit", False),
                "exit_type": result.get("exit_type", "none"),
                "details": result,
            }
        )
    except Exception as e:
        logger.error(f"❌ خطأ في فحص شروط الإغلاق: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# 3. إحصائيات الإغلاق
# ============================================================================


@smart_exit_bp.route("/statistics/<int:user_id>", methods=["GET"])
@require_auth
def get_exit_statistics(user_id):
    """جلب إحصائيات الإغلاق الذكي"""
    try:
        smart_exit = get_intelligent_exit_system()
        if not smart_exit:
            return (
                jsonify(
                    {"success": False, "error": "Exit system not available"}
                ),
                503,
            )

        return jsonify(
            {
                "success": True,
                "data": {
                    "message": "Statistics available via admin dashboard"
                },
            }
        )
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الإحصائيات: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@smart_exit_bp.route("/statistics/<int:user_id>/detailed", methods=["GET"])
@require_auth
def get_detailed_statistics(user_id):
    """جلب إحصائيات مفصلة للإغلاق الذكي"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # إجمالي الإغلاقات والأرباح
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_exits,
                    SUM(profit_loss) as total_profit,
                    AVG(profit_pct) as avg_profit_pct,
                    MAX(profit_pct) as max_profit_pct,
                    MIN(profit_pct) as min_profit_pct
                FROM smart_exit_stats
                WHERE user_id = %s
            """,
                (user_id,),
            )

            result = cursor.fetchone()
            overall_stats = {
                "total_exits": result[0] or 0,
                "total_profit": result[1] or 0.0,
                "avg_profit_pct": result[2] or 0.0,
                "max_profit_pct": result[3] or 0.0,
                "min_profit_pct": result[4] or 0.0,
            }

            # توزيع أنواع الإغلاق
            cursor.execute(
                """
                SELECT
                    exit_type,
                    COUNT(*) as count,
                    AVG(profit_pct) as avg_profit,
                    SUM(profit_loss) as total_profit
                FROM smart_exit_stats
                WHERE user_id = %s
                GROUP BY exit_type
            """,
                (user_id,),
            )

            exit_types = {}
            for row in cursor.fetchall():
                exit_types[row[0]] = {
                    "count": row[1],
                    "avg_profit_pct": row[2],
                    "total_profit": row[3],
                }

            return jsonify(
                {
                    "success": True,
                    "data": {"overall": overall_stats, "by_type": exit_types},
                }
            )
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الإحصائيات المفصلة: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# 4. الأخطاء والمشاكل
# ============================================================================


@smart_exit_bp.route("/errors/<int:user_id>", methods=["GET"])
@require_auth
def get_exit_errors(user_id):
    """جلب أخطاء النظام الذكي"""
    try:
        limit = request.args.get("limit", 10, type=int)

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    id,
                    symbol,
                    error_type,
                    error_message,
                    error_timestamp
                FROM smart_exit_errors
                WHERE user_id = %s
                ORDER BY error_timestamp DESC
                LIMIT %s
            """,
                (user_id, limit),
            )

            errors = []
            for row in cursor.fetchall():
                errors.append(
                    {
                        "id": row[0],
                        "symbol": row[1],
                        "error_type": row[2],
                        "error_message": row[3],
                        "timestamp": row[4],
                    }
                )

            return jsonify({"success": True, "data": errors})
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الأخطاء: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# 5. الإعدادات الافتراضية
# ============================================================================


@smart_exit_bp.route("/defaults", methods=["GET"])
def get_default_settings():
    """جلب الإعدادات الافتراضية"""
    return jsonify(
        {
            "success": True,
            "data": {
                "stop_loss_pct": 2.0,
                "take_profit_pct": 5.0,
                "trailing_distance": 3.0,
                "volatility_buffer": 0.3,
                "min_signal_strength": 0.6,
                "max_positions": 5,
                "position_size_percentage": 10.0,
                "trading_enabled": True,
                "daily_loss_limit": 100.0,
                "recommendations": {
                    "stop_loss_pct": "حماية رأس المال (0.5% - 10%)",
                    "take_profit_pct": "الأرباح المستهدفة (1% - 50%)",
                    "trailing_distance": "مسافة الوقف المتحرك (1% - 5%)",
                    "max_positions": "الحد الأقصى للصفقات المفتوحة (1 - 10)",
                },
            },
        }
    )
