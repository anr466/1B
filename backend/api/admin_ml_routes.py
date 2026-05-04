#!/usr/bin/env python3
"""
Admin ML & AI Routes — extracted from admin_unified_api.py (God Object split)
==============================================================================
Routes: system/ml-status, ml/backtest-status, ml/reliability, ml/status,
        ml/progress, ml/quality-metrics, notification-settings/*
"""

from flask import request, jsonify, g
from datetime import datetime

from config.logging_config import get_logger
from backend.utils.trading_context import get_trading_context

logger = get_logger(__name__)


def register_admin_ml_routes(bp, shared):
    """Register all ML/AI and notification-settings routes on the admin blueprint."""
    require_admin = shared["require_admin"]
    get_safe_connection = shared["get_safe_connection"]
    db = shared["db"]

    @bp.route("/system/ml-status", methods=["GET"])
    @require_admin
    def get_system_ml_status():
        """حالة النظام الشاملة للأدمن مع ML"""
        try:
            admin_id = getattr(g, "current_user_id", None) or getattr(
                g, "user_id", None
            )
            requested_mode = request.args.get("mode")
            trading_context = get_trading_context(
                db, admin_id, requested_mode=requested_mode
            )
            trading_mode = trading_context["active_portfolio"]
            is_demo = trading_context["is_demo"]

            result = {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "current_mode": trading_mode,
                "ml": {},
                "trading": {},
                "portfolio": {},
                "patterns": {},
            }

            # 1️⃣ حالة ML
            try:
                from backend.ml import get_ml_classifier, get_hybrid_system

                classifier = get_ml_classifier()
                hybrid_system = get_hybrid_system()
                hybrid_status = hybrid_system.get_system_status()

                total_samples = classifier.training_history.get(
                    "total_samples", 0
                )
                required_samples = classifier.MIN_SAMPLES_FOR_READINESS
                is_ready = classifier.is_ready()
                best_accuracy = classifier.training_history.get(
                    "best_accuracy", 0
                )

                result["ml"] = {
                    "enabled": classifier.enabled,
                    "is_ready": is_ready,
                    "phase": hybrid_status.get("current_phase", "initial"),
                    "phase_description": hybrid_status.get(
                        "phase_description", "جمع البيانات"
                    ),
                    "backtest_weight": hybrid_status.get(
                        "backtest_weight", 0.7
                    ),
                    "real_weight": hybrid_status.get("real_weight", 0.3),
                    "total_samples": total_samples,
                    "required_samples": required_samples,
                    "accuracy": best_accuracy,
                    "progress_pct": min(
                        100, round((total_samples / required_samples) * 100, 1)
                    ),
                    "status_text": (
                        f"دقة {
                            best_accuracy * 100:.1f}% ({total_samples} صفقة)"
                        if is_ready
                        else f"جمع البيانات ({total_samples}/{required_samples})"
                    ),
                }
            except Exception as ml_err:
                logger.error(f"خطأ في تحميل نظام ML: {ml_err}")
                result["ml"] = {
                    "enabled": False,
                    "is_ready": False,
                    "phase": "initial",
                    "phase_description": "النظام غير متاح",
                    "backtest_weight": 0,
                    "real_weight": 1,
                    "total_samples": 0,
                    "required_samples": 200,
                    "accuracy": 0,
                    "progress_pct": 0,
                    "status_text": "النظام غير نشط",
                }

            # 3️⃣ حالة التداول
            conn = get_safe_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT trading_enabled, trading_mode FROM user_settings WHERE user_id=%s AND is_demo=%s",
                (admin_id, is_demo),
            )
            settings = cursor.fetchone()

            cursor.execute(
                "SELECT COUNT(*) FROM successful_coins WHERE is_active=TRUE"
            )
            active_coins = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM active_positions WHERE user_id=%s AND is_demo=%s AND is_active=TRUE",
                (admin_id, is_demo),
            )
            active_positions = cursor.fetchone()[0]

            result["trading"] = {
                "enabled": bool(settings[0]) if settings else False,
                "mode": trading_mode,
                "active_coins": active_coins,
                "active_positions": active_positions,
            }

            # 4️⃣ حالة المحفظة
            cursor.execute(
                """
                SELECT total_balance, initial_balance, total_profit_loss
                FROM portfolio WHERE user_id=%s AND is_demo=%s
            """,
                (admin_id, is_demo),
            )
            portfolio = cursor.fetchone()

            cursor.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(profit_loss) as total_pnl
                FROM active_positions WHERE user_id=%s AND is_demo=%s AND is_active=FALSE
            """,
                (admin_id, is_demo),
            )
            trades_stats = cursor.fetchone()

            total_trades = trades_stats[0] or 0
            wins = trades_stats[1] or 0
            total_pnl = trades_stats[2] or 0

            balance = float(portfolio[0] or 0) if portfolio else 0.0
            initial_balance = float(portfolio[1] or 0) if portfolio else 0.0
            result["portfolio"] = {
                "balance": balance,
                "initial_balance": initial_balance,
                "total_pnl": round(total_pnl, 2),
                "total_trades": total_trades,
                "winning_trades": wins,
                "win_rate": (
                    round(wins / total_trades * 100, 1)
                    if total_trades > 0
                    else 0
                ),
                "growth_pct": (
                    round(
                        (balance - initial_balance) / initial_balance * 100, 2
                    )
                    if initial_balance > 0
                    else 0
                ),
            }

            # 5️⃣ الصفقات النشطة
            cursor.execute(
                """
                SELECT symbol, entry_price, COALESCE(highest_price, entry_price) as current_price,
                       quantity, COALESCE(profit_loss, 0) as profit_loss,
                       COALESCE(profit_pct, 0) as profit_loss_percentage, created_at
                FROM active_positions
                WHERE user_id=%s AND is_demo=%s AND is_active=TRUE
                ORDER BY created_at DESC
                LIMIT 10
            """,
                (admin_id, is_demo),
            )

            active_positions_data = []
            for row in cursor.fetchall():
                active_positions_data.append(
                    {
                        "symbol": row[0],
                        "entry_price": row[1],
                        "current_price": row[2],
                        "quantity": row[3],
                        "profit_loss": row[4],
                        "profit_loss_percentage": row[5],
                        "created_at": row[6],
                    }
                )

            result["active_positions"] = active_positions_data

            # 6️⃣ النشاط الأخير
            cursor.execute(
                """
                SELECT symbol, profit_loss, COALESCE(closed_at, updated_at) as exit_time
                FROM active_positions
                WHERE user_id=%s AND is_demo=%s AND is_active=FALSE
                ORDER BY COALESCE(closed_at, updated_at) DESC
                LIMIT 5
            """,
                (admin_id, is_demo),
            )

            recent_activity_data = []
            for row in cursor.fetchall():
                recent_activity_data.append(
                    {
                        "type": (
                            "win"
                            if row[1] > 0
                            else "loss" if row[1] < 0 else "neutral"
                        ),
                        "symbol": row[0],
                        "profit": row[1],
                        "time": row[2],
                    }
                )

            result["recent_activity"] = recent_activity_data
            conn.close()

            return jsonify(result)

        except Exception as e:
            logger.error(f"❌ خطأ في جلب حالة النظام: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/ml/backtest-status", methods=["GET"])
    @require_admin
    def get_ml_backtest_status():
        """حالة التعلم الآلي - نظام Backtest Reliability"""
        try:
            conn = get_safe_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM active_positions WHERE is_active = FALSE"
            )
            total_trades = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(DISTINCT symbol) FROM active_positions WHERE is_active = FALSE"
            )
            total_symbols = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM active_positions WHERE is_active = FALSE AND profit_loss > 0"
            )
            winning_trades = cursor.fetchone()[0]

            conn.close()

            reliability = round(
                (
                    (winning_trades / total_trades * 100)
                    if total_trades > 0
                    else 0
                ),
                1,
            )
            is_ready = total_trades >= 10

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "model_type": "backtest_reliability",
                        "enabled": True,
                        "is_ready": is_ready,
                        "total_records": total_trades,
                        "total_combos": total_symbols,
                        "ready_combos": total_symbols if is_ready else 0,
                        "avg_reliability": reliability,
                        "min_trades_for_reliability": 10,
                        "min_trades_for_influence": 30,
                        "progress_pct": min(
                            100, round(total_trades / 100 * 100, 1)
                        ),
                        "status_text": (
                            f"موثوقية {reliability}% ({total_symbols} عملة)"
                            if is_ready
                            else f"جمع البيانات ({total_trades} صفقة)"
                        ),
                        "best_combos": [],
                        "worst_combos": [],
                    },
                }
            )
        except Exception as e:
            logger.error(f"خطأ في backtest status: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/ml/reliability", methods=["GET"])
    @require_admin
    def get_ml_reliability():
        """جلب موثوقية جميع التركيبات - من قاعدة البيانات الفعلية"""
        try:
            conn = get_safe_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    symbol,
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                    AVG(profit_loss) as avg_profit
                FROM active_positions
                WHERE is_active = FALSE
                GROUP BY symbol
                HAVING COUNT(*) >= 3
                ORDER BY total_trades DESC
            """)

            combos = []
            for row in cursor.fetchall():
                symbol, total, wins, avg_profit = row
                win_rate = round((wins / total * 100) if total > 0 else 0, 1)
                combos.append(
                    {
                        "symbol": symbol,
                        "total_trades": total,
                        "win_rate": win_rate,
                        "is_reliable": win_rate >= 50 and total >= 10,
                        "has_enough_data": total >= 10,
                        "avg_profit": round(float(avg_profit), 2),
                    }
                )

            conn.close()

            reliable = len([c for c in combos if c["is_reliable"]])
            unreliable = len(
                [
                    c
                    for c in combos
                    if not c["is_reliable"] and c["has_enough_data"]
                ]
            )

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "status": {
                            "enabled": True,
                            "is_ready": len(combos) > 0,
                        },
                        "combos": combos,
                        "summary": {
                            "total": len(combos),
                            "reliable": reliable,
                            "unreliable": unreliable,
                            "pending": 0,
                        },
                    },
                }
            )
        except Exception as e:
            logger.error(f"خطأ في ML reliability: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/notification-settings", methods=["GET"])
    @require_admin
    def get_notification_settings():
        """جلب إعدادات إشعارات الأدمن"""
        try:
            from backend.services.admin_notification_service import (
                get_admin_notification_service,
            )

            service = get_admin_notification_service()
            settings = service.get_settings()
            unread_count = service.get_unread_count()

            return jsonify(
                {
                    "success": True,
                    "data": {**settings, "unread_count": unread_count},
                }
            )
        except Exception as e:
            logger.error(f"فشل جلب إعدادات الإشعارات: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/notification-settings", methods=["PUT"])
    @require_admin
    def update_notification_settings():
        """تحديث إعدادات إشعارات الأدمن"""
        try:
            from backend.services.admin_notification_service import (
                get_admin_notification_service,
            )

            service = get_admin_notification_service()

            data = request.get_json()
            success = service.update_settings(data)

            if success:
                return jsonify(
                    {"success": True, "message": "تم تحديث الإعدادات"}
                )
            else:
                return (
                    jsonify({"success": False, "message": "فشل التحديث"}),
                    500,
                )
        except Exception as e:
            logger.error(f"فشل تحديث إعدادات الإشعارات: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/notification-settings/test", methods=["POST"])
    @require_admin
    def test_notification():
        """اختبار إرسال إشعار"""
        try:
            from backend.services.admin_notification_service import (
                get_admin_notification_service,
            )

            service = get_admin_notification_service()

            data = request.get_json() or {}
            data.get("channel", "all")

            service.notify_admin(
                title="🧪 إشعار اختباري",
                message="هذا إشعار اختباري للتأكد من عمل نظام الإشعارات",
                severity="info",
                alert_type="test",
            )

            return jsonify(
                {"success": True, "message": "تم إرسال الإشعار الاختباري"}
            )
        except Exception as e:
            logger.error(f"فشل إرسال الإشعار الاختباري: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/ml/status", methods=["GET"])
    @require_admin
    def get_ml_status():
        """حالة نظام التعلم الكامل مع مؤشرات النجاح"""
        try:
            from backend.ml.training_manager import MLTrainingManager
            from backend.ml.signal_classifier import get_ml_classifier
            from backend.ml.independent_learning_system import (
                IndependentLearningSystem,
            )

            admin_id = getattr(g, "current_user_id", None) or getattr(
                g, "user_id", None
            )
            requested_mode = request.args.get("mode")
            trading_context = get_trading_context(
                db, admin_id, requested_mode=requested_mode
            )
            trading_mode = trading_context["active_portfolio"]
            is_demo = trading_context["is_demo"]

            MLTrainingManager()
            classifier = get_ml_classifier()
            ils = IndependentLearningSystem()

            ml_metrics = {
                "accuracy": 0,
                "precision": 0,
                "recall": 0,
                "f1_score": 0,
                "is_ready": False,
            }

            if classifier and classifier.enabled:
                try:
                    status_info = classifier.get_status()
                    ml_metrics["accuracy"] = status_info.get("accuracy", 0)
                    ml_metrics["precision"] = status_info.get("precision", 0)
                    ml_metrics["recall"] = status_info.get("recall", 0)
                    ml_metrics["f1_score"] = status_info.get("f1_score", 0)
                    ml_metrics["is_ready"] = status_info.get("is_ready", False)
                except Exception as e:
                    logger.debug(f"ML metrics fetch skipped: {e}")

            total_samples = (
                len(classifier.accumulated_data)
                if classifier and hasattr(classifier, "accumulated_data")
                else 0
            )
            required_samples = (
                classifier.MIN_SAMPLES_FOR_READINESS if classifier else 200
            )
            is_ready = total_samples >= required_samples

            conn = get_safe_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT trading_enabled FROM user_settings WHERE user_id = %s AND is_demo = %s LIMIT 1",
                (admin_id, is_demo),
            )
            settings = cursor.fetchone()
            cursor.execute(
                "SELECT COUNT(*) FROM successful_coins WHERE is_active = TRUE"
            )
            active_coins = cursor.fetchone()[0] or 0
            cursor.execute(
                "SELECT COUNT(*) FROM active_positions WHERE user_id = %s AND is_demo = %s AND is_active = TRUE",
                (admin_id, is_demo),
            )
            active_positions = cursor.fetchone()[0] or 0
            cursor.execute(
                "SELECT total_balance FROM portfolio WHERE user_id = %s AND is_demo = %s LIMIT 1",
                (admin_id, is_demo),
            )
            portfolio_row = cursor.fetchone()
            cursor.execute(
                """
                SELECT COUNT(*),
                       SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END)
                FROM active_positions
                WHERE user_id = %s AND is_demo = %s AND is_active = FALSE
                """,
                (admin_id, is_demo),
            )
            trade_stats = cursor.fetchone()
            conn.close()

            total_trades = trade_stats[0] or 0 if trade_stats else 0
            winning_trades = trade_stats[1] or 0 if trade_stats else 0
            balance = float(portfolio_row[0] or 0) if portfolio_row else 0.0

            status = {
                "success": True,
                "ml": {
                    "enabled": classifier.enabled if classifier else False,
                    "is_ready": is_ready,
                    "total_samples": total_samples,
                    "required_samples": required_samples,
                    "progress_pct": (
                        min((total_samples / required_samples) * 100, 100)
                        if required_samples > 0
                        else 0
                    ),
                    "accuracy": ml_metrics["accuracy"],
                    "precision": ml_metrics["precision"],
                    "recall": ml_metrics["recall"],
                    "f1_score": ml_metrics["f1_score"],
                },
                "portfolio": {
                    "balance": balance,
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "win_rate": (
                        round((winning_trades / total_trades) * 100, 1)
                        if total_trades > 0
                        else 0
                    ),
                },
                "trading": {
                    "enabled": bool(settings[0]) if settings else False,
                    "mode": trading_mode,
                    "active_coins": active_coins,
                    "active_positions": active_positions,
                },
                "patterns": {
                    "total_patterns": ils.learning_stats["patterns_learned"],
                    "live_trades": ils.learning_stats["total_real_trades"],
                },
            }

            return jsonify(status)
        except Exception as e:
            logger.error(f"خطأ في جلب حالة ML: {e}")
            return (
                jsonify(
                    {
                        "success": False,
                        "ml": {
                            "enabled": False,
                            "is_ready": False,
                            "total_samples": 0,
                            "required_samples": 200,
                            "progress_pct": 0,
                            "accuracy": 0,
                            "precision": 0,
                            "recall": 0,
                            "f1_score": 0,
                        },
                        "error": str(e),
                    }
                ),
                500,
            )

    @bp.route("/ml/progress", methods=["GET"])
    @require_admin
    def get_ml_progress():
        """تقدم التعلم الفعلي"""
        try:
            from backend.ml.training_manager import MLTrainingManager
            from backend.ml.signal_classifier import get_ml_classifier

            tm = MLTrainingManager()
            classifier = get_ml_classifier()

            if not classifier or not classifier.enabled:
                return (
                    jsonify(
                        {"success": False, "error": "ML System not available"}
                    ),
                    503,
                )

            status = classifier.get_status()
            total_samples = (
                len(classifier.accumulated_data)
                if hasattr(classifier, "accumulated_data")
                else 0
            )

            progress = {
                "success": True,
                "data": {
                    "training_progress": {
                        "total_samples": total_samples,
                        "min_required": classifier.MIN_SAMPLES_FOR_TRAINING,
                        "readiness_required": classifier.MIN_SAMPLES_FOR_READINESS,
                        "progress_percent": min(
                            (
                                total_samples
                                / classifier.MIN_SAMPLES_FOR_READINESS
                            )
                            * 100,
                            100,
                        ),
                        "status": (
                            "ready"
                            if total_samples
                            >= classifier.MIN_SAMPLES_FOR_READINESS
                            else "training"
                        ),
                    },
                    "model_metrics": {
                        "accuracy": status.get("accuracy", 0),
                        "precision": status.get("precision", 0),
                        "recall": status.get("recall", 0),
                        "f1_score": status.get("f1_score", 0),
                        "is_ready": status.get("is_ready", False),
                    },
                    "training_history": {
                        "total_cycles": tm.cycle_count,
                        "current_cycle_samples": len(tm.current_cycle_data),
                    },
                    "timestamp": datetime.now().isoformat(),
                },
            }

            return jsonify(progress)
        except Exception as e:
            logger.error(f"خطأ في جلب تقدم ML: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @bp.route("/ml/quality-metrics", methods=["GET"])
    @require_admin
    def get_ml_quality_metrics():
        """مقاييس جودة النموذج والبيانات - من البيانات الفعلية"""
        try:
            conn = get_safe_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    AVG(profit_loss) as avg_profit,
                    MAX(profit_loss) as max_profit,
                    MIN(profit_loss) as max_loss,
                    SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as wins
                FROM active_positions
                WHERE is_active = FALSE
            """)

            row = cursor.fetchone()
            total, avg_profit, max_profit, max_loss, wins = (
                row if row else (0, 0, 0, 0, 0)
            )

            win_rate = round((wins / total * 100) if total > 0 else 0, 1)
            quality_score = min(100, win_rate) if total >= 10 else 0

            conn.close()

            return jsonify(
                {
                    "success": True,
                    "data": {
                        "overall_quality": quality_score,
                        "data_quality": {
                            "total_samples": total,
                            "valid_samples": total,
                            "completeness": 100.0,
                        },
                        "model_quality": {
                            "accuracy": win_rate,
                            "precision": win_rate,
                            "win_rate": win_rate,
                        },
                        "performance_metrics": {
                            "avg_profit": round(
                                float(avg_profit) if avg_profit else 0, 2
                            ),
                            "max_profit": round(
                                float(max_profit) if max_profit else 0, 2
                            ),
                            "max_loss": round(
                                float(max_loss) if max_loss else 0, 2
                            ),
                            "total_trades": total,
                            "winning_trades": wins,
                        },
                        "status": (
                            "ready" if total >= 10 else "collecting_data"
                        ),
                        "recommendations": [
                            (
                                "النظام يعمل بشكل جيد"
                                if win_rate >= 50
                                else "يحتاج تحسين الاستراتيجية"
                            )
                        ],
                    },
                }
            )
        except Exception as e:
            logger.error(f"خطأ في جلب مقاييس الجودة: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
