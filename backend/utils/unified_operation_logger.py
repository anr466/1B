"""
Unified Operation Logger - Unified logging for trading operations
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

LOG_DIR = os.environ.get("LOG_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runtime", "logs"))


class UnifiedOperationLogger:
    """Logs all trading operations to a unified JSONL log file"""

    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        self.log_path = os.path.join(LOG_DIR, "operations.jsonl")
        self.logger = logger

    def log(self, operation_type, data, user_id=None, status="success"):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "operation_type": operation_type,
            "user_id": user_id,
            "status": status,
            "data": data,
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            self.logger.debug(f"Operation logged: {operation_type} ({status})")
        except Exception as e:
            self.logger.error(f"Failed to log operation: {e}")

    def log_start(self, process_name, details=None):
        self.log("process_start", {
            "process": process_name,
            "details": details or {},
        })

    def log_stop(self, process_name, reason=None):
        self.log("process_stop", {
            "process": process_name,
            "reason": reason or "manual",
        })

    def log_trade(self, symbol, action, quantity, price, profit=None):
        self.log("trade", {
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "profit": profit,
        })

    def log_error(self, source, error_message, traceback_str=None):
        self.log("error", {
            "source": source,
            "error": str(error_message)[:500],
            "traceback": str(traceback_str)[:1000] if traceback_str else None,
        }, status="error")

    def get_recent_operations(self, limit=50):
        entries = []
        try:
            if not os.path.exists(self.log_path):
                return entries
            with open(self.log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines[-limit:]:
                try:
                    entries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
            entries.reverse()
        except Exception as e:
            self.logger.error(f"Failed to read operations: {e}")
        return entries

    def clear_log(self):
        try:
            if os.path.exists(self.log_path):
                os.remove(self.log_path)
        except Exception as e:
            self.logger.error(f"Failed to clear log: {e}")


_unified_logger_instance = None


def get_unified_logger():
    global _unified_logger_instance
    if _unified_logger_instance is None:
        _unified_logger_instance = UnifiedOperationLogger()
    return _unified_logger_instance


unified_logger = get_unified_logger()
