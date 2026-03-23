#!/usr/bin/env python3
"""
🔒 Unified Authentication Middleware
====================================
Single source of truth for all authentication decorators.
All API blueprints should import from here instead of defining their own.

Usage:
    from backend.api.auth_middleware import require_auth, require_admin
"""

import jwt
from functools import wraps
from flask import request, jsonify, g

from config.logging_config import get_logger

logger = get_logger(__name__)

# Import token verification
try:
    from backend.api.token_refresh_endpoint import verify_token, verify_token_with_lock

    TOKEN_VERIFICATION_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    TOKEN_VERIFICATION_AVAILABLE = False
    logger.warning("⚠️ Token verification not available")


def _verify_jwt_and_set_g():
    """
    Shared JWT verification logic. Extracts token from Authorization header,
    verifies it, and sets g.current_user_id / g.current_username / g.current_user_type.

    Returns None on success, or (response, status_code) tuple on failure.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"success": False, "error": "Authorization header missing"}), 401

    if not auth_header.startswith("Bearer "):
        return jsonify(
            {
                "success": False,
                "error": "Invalid authorization format. Use: Bearer <token>",
            }
        ), 401

    token = auth_header.split(" ")[1] if len(auth_header.split(" ")) > 1 else None
    if not token:
        return jsonify({"success": False, "error": "Token missing"}), 401

    if TOKEN_VERIFICATION_AVAILABLE:
        try:
            payload = verify_token(token, "access")

            g.current_user_id = payload["user_id"]
            g.current_username = payload.get("username", "")
            g.current_user_type = payload.get("user_type", "user")
            g.user_id = payload["user_id"]  # backward compat

        except jwt.InvalidTokenError as e:
            logger.warning(f"⚠️ Invalid token: {e}")
            return jsonify({"success": False, "error": "Invalid token"}), 401
        except Exception as e:
            logger.error(f"❌ Token verification error: {e}")
            return jsonify(
                {"success": False, "error": "Token verification failed"}
            ), 401
    else:
        logger.error("❌ JWT verification system not available")
        return jsonify(
            {
                "success": False,
                "error": "Authentication system unavailable",
                "code": "AUTH_SYSTEM_UNAVAILABLE",
            }
        ), 503

    return None  # success


def _verify_jwt_atomic():
    """
    Atomic JWT verification using advisory locks.
    Use this for critical operations like trading, balance changes.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"success": False, "error": "Authorization header missing"}), 401

    if not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "error": "Invalid authorization format"}), 401

    token = auth_header.split(" ")[1] if len(auth_header.split(" ")) > 1 else None
    if not token:
        return jsonify({"success": False, "error": "Token missing"}), 401

    if TOKEN_VERIFICATION_AVAILABLE:
        try:
            payload = verify_token_with_lock(token, "access")

            g.current_user_id = payload["user_id"]
            g.current_username = payload.get("username", "")
            g.current_user_type = payload.get("user_type", "user")
            g.user_id = payload["user_id"]

        except jwt.InvalidTokenError as e:
            logger.warning(f"⚠️ Invalid token (atomic): {e}")
            return jsonify({"success": False, "error": "Invalid token"}), 401
        except Exception as e:
            logger.error(f"❌ Token verification error (atomic): {e}")
            return jsonify(
                {"success": False, "error": "Token verification failed"}
            ), 401
    else:
        return jsonify(
            {"success": False, "error": "Authentication system unavailable"}
        ), 503

    return None


def require_auth_atomic(f):
    """
    Atomic authentication decorator for critical operations.
    Uses advisory locks to prevent race conditions in token revocation.
    Use for: trading, balance updates, settings changes.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        error_response = _verify_jwt_atomic()
        if error_response is not None:
            return error_response

        user_id_from_url = kwargs.get("user_id")
        if user_id_from_url and getattr(g, "current_user_type", None) != "admin":
            try:
                user_id_int = int(user_id_from_url)
                if g.current_user_id != user_id_int:
                    logger.warning(
                        f"⚠️ Unauthorized access: User {g.current_user_id} "
                        f"tried to access User {user_id_from_url} data"
                    )
                    return jsonify(
                        {"success": False, "error": "Unauthorized access"}
                    ), 403
            except ValueError:
                return jsonify({"success": False, "error": "Invalid user ID"}), 400

        return f(*args, **kwargs)

    return decorated_function


def require_admin(f):
    """
    Decorator for admin-only endpoints.
    Must be used AFTER @require_auth.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, "current_user_type") or g.current_user_type != "admin":
            return jsonify({"success": False, "error": "Admin access required"}), 403
        return f(*args, **kwargs)

    return decorated_function
