"""
🔐 Unified Password Utilities
==============================
Single source of truth for password hashing and verification.
Supports bcrypt (preferred) with SHA-256 backward compatibility.

Usage:
    from backend.utils.password_utils import hash_password, verify_password
"""

import hashlib

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt (preferred) or SHA-256 (fallback).
    New passwords are ALWAYS hashed with bcrypt if available.
    """
    if BCRYPT_AVAILABLE:
        salt = bcrypt.gensalt(rounds=10)  # 10 rounds = ~100ms, good balance
        return bcrypt.hashpw(password.encode(), salt).decode()
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against a hash.
    Supports both bcrypt ($2b$ prefix) and legacy SHA-256 (64-char hex).
    """
    if BCRYPT_AVAILABLE and password_hash.startswith('$2b$'):
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except Exception:
            return False
    # Legacy SHA-256
    return hashlib.sha256(password.encode()).hexdigest() == password_hash


def needs_upgrade(password_hash: str) -> bool:
    """Check if a password hash should be upgraded from SHA-256 to bcrypt."""
    if not BCRYPT_AVAILABLE:
        return False
    return len(password_hash) == 64 and not password_hash.startswith('$2b$')


def upgrade_hash(password: str) -> str:
    """Re-hash a password with bcrypt. Call only after verify_password succeeds."""
    return hash_password(password)
