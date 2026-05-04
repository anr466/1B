"""
📱 Client Logs Endpoint - استقبال سجلات التطبيق وتوحيدها مع سجل الخادم
"""

from flask import Blueprint, request, jsonify
from backend.api.auth_middleware import require_auth
import logging
import os

client_logs_bp = Blueprint("client_logs", __name__)

# إعداد logger منفصل لسجلات العملاء
client_logger = logging.getLogger("client_logs")
client_logger.setLevel(logging.DEBUG)

# استخدام مجلد logs داخل المشروع
_LOGS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs"
)
os.makedirs(_LOGS_DIR, exist_ok=True)

# إضافة handler لحفظ سجلات العملاء في ملف منفصل
client_handler = logging.FileHandler(
    os.path.join(_LOGS_DIR, "client_logs.log")
)
client_handler.setLevel(logging.DEBUG)

# تنسيق موحد للسجلات
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | CLIENT | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
client_handler.setFormatter(formatter)
client_logger.addHandler(client_handler)

# إضافة أيضاً إلى سجل الخادم الرئيسي
main_logger = logging.getLogger("__main__")


@client_logs_bp.route("/client-logs", methods=["POST"])
@require_auth
def receive_client_logs():
    """
    استقبال سجلات من التطبيق وحفظها في سجل الخادم

    Body:
    {
        "level": "INFO|WARN|ERROR|CRITICAL",
        "message": "رسالة السجل",
        "context": "اسم الشاشة أو الخدمة",
        "timestamp": "ISO timestamp",
        "userId": "معرف المستخدم (اختياري)",
        "device": "معلومات الجهاز (اختياري)"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return (
                jsonify({"success": False, "message": "No data provided"}),
                400,
            )

        level = data.get("level", "INFO").upper()
        message = data.get("message", "")
        context = data.get("context", "")
        user_id = data.get("userId", "guest")
        device = data.get("device", "unknown")

        # تنسيق الرسالة
        log_message = (
            f"[User:{user_id}] [Device:{device}] [{context}] {message}"
        )

        # كتابة في سجل العملاء
        if level == "DEBUG":
            client_logger.debug(log_message)
        elif level == "INFO":
            client_logger.info(log_message)
        elif level == "WARN" or level == "WARNING":
            client_logger.warning(log_message)
        elif level == "ERROR":
            client_logger.error(log_message)
        elif level == "CRITICAL":
            client_logger.critical(log_message)

        # كتابة أيضاً في سجل الخادم الرئيسي للأخطاء الحرجة
        if level in ["ERROR", "CRITICAL"]:
            main_logger.error(f"📱 CLIENT ERROR: {log_message}")

        return jsonify({"success": True, "data": {"accepted": True}}), 200

    except Exception as e:
        main_logger.error(f"❌ Error receiving client logs: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@client_logs_bp.route("/client-logs/batch", methods=["POST"])
@require_auth
def receive_client_logs_batch():
    """
    استقبال دفعة من السجلات

    Body:
    {
        "logs": [
            {
                "level": "INFO",
                "message": "...",
                "context": "...",
                "timestamp": "...",
                "userId": "...",
                "device": "..."
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()

        if not data or "logs" not in data:
            return (
                jsonify({"success": False, "message": "No logs provided"}),
                400,
            )

        logs = data.get("logs", [])
        processed = 0

        for log_entry in logs:
            try:
                level = log_entry.get("level", "INFO").upper()
                message = log_entry.get("message", "")
                context = log_entry.get("context", "")
                user_id = log_entry.get("userId", "guest")
                device = log_entry.get("device", "unknown")

                log_message = (
                    f"[User:{user_id}] [Device:{device}] [{context}] {message}"
                )

                if level == "DEBUG":
                    client_logger.debug(log_message)
                elif level == "INFO":
                    client_logger.info(log_message)
                elif level == "WARN" or level == "WARNING":
                    client_logger.warning(log_message)
                elif level == "ERROR":
                    client_logger.error(log_message)
                elif level == "CRITICAL":
                    client_logger.critical(log_message)

                if level in ["ERROR", "CRITICAL"]:
                    main_logger.error(f"📱 CLIENT ERROR: {log_message}")

                processed += 1

            except Exception as e:
                main_logger.warning(f"⚠️ Error processing log entry: {e}")
                continue

        return (
            jsonify(
                {"success": True, "processed": processed, "total": len(logs)}
            ),
            200,
        )

    except Exception as e:
        main_logger.error(f"❌ Error receiving batch logs: {e}")
        return jsonify({"success": False, "message": str(e)}), 500
