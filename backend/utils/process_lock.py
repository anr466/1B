"""
Process Lock - Prevents duplicate system processes
"""

import os
import fcntl
import logging

logger = logging.getLogger(__name__)

LOCK_DIR = os.environ.get("LOCK_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tmp"))
LOCK_FILE = os.path.join(LOCK_DIR, "system.lock")
PID_FILE = os.path.join(LOCK_DIR, "system.pid")

os.makedirs(LOCK_DIR, exist_ok=True)


def get_process_lock():
    """Acquire a system-wide process lock. Returns lock fd or None."""
    try:
        lock_fd = open(LOCK_FILE, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        logger.info("Process lock acquired")
        return lock_fd
    except (IOError, OSError):
        logger.warning("Process lock already held — another instance may be running")
        return None


def release_process_lock(lock_fd):
    """Release the system-wide process lock"""
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        logger.info("Process lock released")
    except Exception as e:
        logger.error(f"Failed to release lock: {e}")


def is_system_running():
    """Check if another system instance is already running"""
    try:
        if not os.path.exists(PID_FILE):
            return False
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        # Check if PID is still alive
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False
    except Exception:
        return False
