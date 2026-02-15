#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safe Logger - يخفي البيانات الحساسة في السجلات
"""

import logging
import re


class SafeLogger:
    """Logger يخفي البيانات الحساسة"""
    
    SENSITIVE_PATTERNS = [
        (r'password["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', 'password: ***'),
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', 'api_key: ***'),
        (r'secret["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', 'secret: ***'),
        (r'token["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', 'token: ***'),
    ]
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def _sanitize(self, msg: str) -> str:
        """إخفاء البيانات الحساسة"""
        if not isinstance(msg, str):
            msg = str(msg)
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
        return msg
    
    def debug(self, msg, *args, **kwargs):
        self.logger.debug(self._sanitize(msg), *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        self.logger.info(self._sanitize(msg), *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        self.logger.warning(self._sanitize(msg), *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self.logger.error(self._sanitize(msg), *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        self.logger.critical(self._sanitize(msg), *args, **kwargs)
