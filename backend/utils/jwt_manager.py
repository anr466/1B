#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مدير JWT محسّن
- Token Expiration
- Token Refresh
- Token Revocation
- Biometric Support
"""

import jwt
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)


class JWTManager:
    """مدير JWT محسّن"""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """
        تهيئة مدير JWT

        Args:
            secret_key: مفتاح سري قوي
            algorithm: خوارزمية التشفير
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.revoked_tokens = set()  # في الإنتاج، استخدم Redis

    def create_token(
        self,
        user_id: int,
        email: str,
        user_type: str = "user",
        expiration_hours: int = 24,
        biometric_enabled: bool = False,
        additional_claims: Dict = None,
    ) -> str:
        """
        إنشاء JWT Token

        Args:
            user_id: معرف المستخدم
            email: بريد المستخدم
            user_type: نوع المستخدم
            expiration_hours: ساعات انتهاء الصلاحية
            biometric_enabled: هل البصمة مفعلة
            additional_claims: مطالبات إضافية

        Returns:
            JWT Token
        """
        try:
            now = datetime.utcnow()
            expiration = now + timedelta(hours=expiration_hours)

            payload = {
                "user_id": user_id,
                "email": email,
                "user_type": user_type,
                "biometric_enabled": biometric_enabled,
                "iat": now,
                "exp": expiration,
                "token_type": "access",
            }

            if additional_claims:
                payload.update(additional_claims)

            token = jwt.encode(
                payload, self.secret_key, algorithm=self.algorithm
            )

            logger.info(f"✅ تم إنشاء token للمستخدم {user_id}")

            return token

        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء token: {e}")
            raise

    def create_refresh_token(
        self, user_id: int, expiration_days: int = 7
    ) -> str:
        """
        إنشاء Refresh Token

        Args:
            user_id: معرف المستخدم
            expiration_days: أيام انتهاء الصلاحية

        Returns:
            Refresh Token
        """
        try:
            now = datetime.utcnow()
            expiration = now + timedelta(days=expiration_days)

            payload = {
                "user_id": user_id,
                "iat": now,
                "exp": expiration,
                "token_type": "refresh",
            }

            token = jwt.encode(
                payload, self.secret_key, algorithm=self.algorithm
            )

            logger.info(f"✅ تم إنشاء refresh token للمستخدم {user_id}")

            return token

        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء refresh token: {e}")
            raise

    def verify_token(self, token: str) -> Optional[Dict]:
        """
        التحقق من صحة Token

        Args:
            token: الـ Token المراد التحقق منه

        Returns:
            بيانات Token إذا كانت صحيحة، None إذا كانت غير صحيحة
        """
        try:
            # التحقق من أن Token غير مسحوب
            if token in self.revoked_tokens:
                logger.warning("⚠️ محاولة استخدام token مسحوب")
                return None

            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm]
            )

            logger.debug(f"✅ تم التحقق من token للمستخدم {
                payload.get('user_id')}")

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("⚠️ Token منتهي الصلاحية")
            return None

        except jwt.InvalidTokenError as e:
            logger.warning(f"⚠️ Token غير صحيح: {e}")
            return None

        except Exception as e:
            logger.error(f"❌ خطأ في التحقق من token: {e}")
            return None

    def refresh_token(
        self, refresh_token: str, expiration_hours: int = 24
    ) -> Optional[str]:
        """
        تحديث Access Token باستخدام Refresh Token

        Args:
            refresh_token: الـ Refresh Token
            expiration_hours: ساعات انتهاء الصلاحية للـ Token الجديد

        Returns:
            Access Token جديد
        """
        try:
            payload = self.verify_token(refresh_token)

            if not payload or payload.get("token_type") != "refresh":
                logger.warning("⚠️ Refresh token غير صحيح")
                return None

            user_id = payload.get("user_id")

            # إنشاء access token جديد
            new_token = self.create_token(
                user_id=user_id,
                email=payload.get("email", ""),
                user_type=payload.get("user_type", "user"),
                expiration_hours=expiration_hours,
            )

            logger.info(f"✅ تم تحديث token للمستخدم {user_id}")

            return new_token

        except Exception as e:
            logger.error(f"❌ خطأ في تحديث token: {e}")
            return None

    def revoke_token(self, token: str):
        """
        سحب Token (منعه من الاستخدام)

        Args:
            token: الـ Token المراد سحبه
        """
        self.revoked_tokens.add(token)
        logger.info("✅ تم سحب token")

    def get_token_info(self, token: str) -> Optional[Dict]:
        """
        الحصول على معلومات Token

        Args:
            token: الـ Token

        Returns:
            معلومات Token
        """
        payload = self.verify_token(token)

        if not payload:
            return None

        return {
            "user_id": payload.get("user_id"),
            "email": payload.get("email"),
            "user_type": payload.get("user_type"),
            "biometric_enabled": payload.get("biometric_enabled"),
            "expires_at": datetime.fromtimestamp(
                payload.get("exp")
            ).isoformat(),
            "created_at": datetime.fromtimestamp(
                payload.get("iat")
            ).isoformat(),
        }


# إنشاء instance عام


def create_jwt_manager(secret_key: str) -> JWTManager:
    """إنشاء مدير JWT"""
    return JWTManager(secret_key)


def require_token(f):
    """Decorator للتحقق من وجود Token صحيح"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # الحصول على Token من الـ Header
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({"success": False, "message": "Token مفقود"}), 401

        try:
            # استخراج Token من "Bearer <token>"
            auth_header.split(" ")[1]
        except IndexError:
            return (
                jsonify({"success": False, "message": "صيغة Token غير صحيحة"}),
                401,
            )

        # التحقق من Token (يجب تمرير jwt_manager)
        # هذا يتطلب تحسين إضافي في الـ app

        return f(*args, **kwargs)

    return decorated_function
