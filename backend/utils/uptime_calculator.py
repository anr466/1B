"""
Uptime Calculator - System uptime tracking
"""

import os
import time
from datetime import datetime

_start_time = time.time()


def get_uptime_seconds():
    """Return seconds since module was first imported"""
    return time.time() - _start_time


def get_uptime_formatted():
    """Return human-readable uptime string"""
    seconds = get_uptime_seconds()
    days, rem = divmod(int(seconds), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def get_start_time():
    """Return ISO datetime of when uptime tracking started"""
    return datetime.fromtimestamp(_start_time).isoformat()


def uptime_calc():
    """Compatibility wrapper returning full uptime dict"""
    return {
        "uptime_seconds": get_uptime_seconds(),
        "uptime_formatted": get_uptime_formatted(),
        "start_time": get_start_time(),
    }
