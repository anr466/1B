#!/usr/bin/env python3
"""
🎯 خدمة توجيه المستخدم الجديد
User Onboarding Service

نظام إشعارات ذكي غير مزعج:
- كل إشعار يظهر مرة واحدة فقط
- توجيه بسيط حسب مرحلة المستخدم
- لا إشعارات تداول حتى يُفعّل المستخدم حسابه
"""

import logging
from enum import Enum
from typing import Dict, Optional

from backend.infrastructure.db_access import get_db_manager

import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
)


class UserStage(Enum):
    """مراحل المستخدم"""

    NEW = "new"  # تسجيل جديد
    PROFILE_COMPLETE = "profile"  # أكمل الملف الشخصي
    KEYS_ADDED = "keys_added"  # أضاف مفاتيح Binance
    KEYS_VERIFIED = "keys_verified"  # تم التحقق من المفاتيح
    TRADING_ACTIVE = "active"  # فعّل التداول


class OnboardingStep(Enum):
    """خطوات التوجيه - كل خطوة تظهر مرة واحدة"""

    WELCOME = "welcome"
    COMPLETE_PROFILE = "complete_profile"
    ADD_BINANCE_KEYS = "add_binance_keys"
    KEYS_VERIFIED = "keys_verified"
    CONFIGURE_SETTINGS = "configure_settings"
    ACTIVATE_TRADING = "activate_trading"
    FIRST_TRADE = "first_trade"


# رسائل التوجيه
ONBOARDING_MESSAGES = {
    OnboardingStep.WELCOME: {
        "title": "👋 مرحباً بك!",
        "message": "شكراً لانضمامك. ابدأ بإعداد حسابك للتداول الآلي.",
        "action": "profile",
    },
    OnboardingStep.COMPLETE_PROFILE: {
        "title": "📝 أكمل ملفك الشخصي",
        "message": "أضف معلوماتك الأساسية لتجربة أفضل.",
        "action": "profile",
    },
    OnboardingStep.ADD_BINANCE_KEYS: {
        "title": "🔑 ربط حساب Binance",
        "message": "أضف مفاتيح API للبدء في التداول الآلي.",
        "action": "binance_keys",
    },
    OnboardingStep.KEYS_VERIFIED: {
        "title": "✅ تم التحقق من حسابك",
        "message": "مفاتيح Binance جاهزة. اضبط إعدادات التداول.",
        "action": "settings",
    },
    OnboardingStep.CONFIGURE_SETTINGS: {
        "title": "⚙️ إعدادات التداول",
        "message": "اضبط وقف الخسارة وجني الأرباح حسب تفضيلاتك.",
        "action": "settings",
    },
    OnboardingStep.ACTIVATE_TRADING: {
        "title": "🚀 جاهز للانطلاق!",
        "message": "فعّل التداول الآلي لبدء تحقيق الأرباح.",
        "action": "trading",
    },
    OnboardingStep.FIRST_TRADE: {
        "title": "🎉 صفقتك الأولى!",
        "message": "تهانينا! تم تنفيذ أول صفقة لك.",
        "action": None,
    },
}


class UserOnboardingService:
    """خدمة توجيه المستخدم - إشعارات ذكية غير مزعجة"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_manager = get_db_manager()

    def get_user_stage(self, user_id: int) -> UserStage:
        """تحديد مرحلة المستخدم الحالية"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # فحص: هل التداول مُفعّل؟
                cursor.execute(
                    """
                    SELECT trading_enabled FROM user_settings WHERE user_id = %s
                """,
                    (user_id,),
                )
                settings = cursor.fetchone()

                if settings and settings[0]:
                    return UserStage.TRADING_ACTIVE

                # فحص: هل لديه مفاتيح Binance مُفعّلة؟
                cursor.execute(
                    """
                    SELECT is_active FROM user_binance_keys
                    WHERE user_id = %s AND is_active = TRUE
                """,
                    (user_id,),
                )
                keys = cursor.fetchone()

                if keys:
                    return UserStage.KEYS_VERIFIED

                # فحص: هل لديه مفاتيح (غير مُفعّلة)؟
                cursor.execute(
                    """
                    SELECT id FROM user_binance_keys WHERE user_id = %s
                """,
                    (user_id,),
                )
                if cursor.fetchone():
                    return UserStage.KEYS_ADDED

                # فحص: هل أكمل الملف الشخصي؟
                cursor.execute(
                    """
                    SELECT name, phone_number FROM users WHERE id = %s
                """,
                    (user_id,),
                )
                user = cursor.fetchone()

                if user and user[0] and user[0] != "User":
                    return UserStage.PROFILE_COMPLETE

                return UserStage.NEW

        except Exception as e:
            self.logger.error(f"خطأ في تحديد مرحلة المستخدم: {e}")
            return UserStage.NEW

    def get_next_step(self, user_id: int) -> Optional[Dict]:
        """
        جلب الخطوة التالية للمستخدم
        تُرجع None إذا لا توجد خطوات جديدة
        """
        stage = self.get_user_stage(user_id)

        # تحديد الخطوة المناسبة حسب المرحلة
        step_for_stage = {
            UserStage.NEW: OnboardingStep.ADD_BINANCE_KEYS,
            UserStage.PROFILE_COMPLETE: OnboardingStep.ADD_BINANCE_KEYS,
            UserStage.KEYS_ADDED: OnboardingStep.KEYS_VERIFIED,
            UserStage.KEYS_VERIFIED: OnboardingStep.ACTIVATE_TRADING,
            UserStage.TRADING_ACTIVE: None,  # لا توجد خطوات
        }

        next_step = step_for_stage.get(stage)

        if not next_step:
            return None

        # فحص: هل تم عرض هذه الخطوة من قبل؟
        if self._is_step_shown(user_id, next_step):
            return None

        # جلب رسالة الخطوة
        message = ONBOARDING_MESSAGES.get(next_step, {})

        return {
            "step": next_step.value,
            "title": message.get("title", ""),
            "message": message.get("message", ""),
            "action": message.get("action"),
            "stage": stage.value,
        }

    def _is_step_shown(self, user_id: int, step: OnboardingStep) -> bool:
        """فحص إذا تم عرض الخطوة من قبل"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id FROM user_onboarding
                    WHERE user_id = %s AND step = %s
                """,
                    (user_id, step.value),
                )
                return cursor.fetchone() is not None
        except Exception:
            return False

    def mark_step_shown(self, user_id: int, step: str) -> bool:
        """تسجيل أن الخطوة تم عرضها (لن تظهر مرة أخرى)"""
        try:
            with self.db_manager.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO user_onboarding (user_id, step, shown_at)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id, step) DO NOTHING
                """,
                    (user_id, step),
                )
                return True
        except Exception as e:
            self.logger.error(f"خطأ في تسجيل الخطوة: {e}")
            return False

    def dismiss_step(self, user_id: int, step: str) -> bool:
        """تجاهل الخطوة (المستخدم أغلقها)"""
        try:
            with self.db_manager.get_write_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE user_onboarding
                    SET dismissed_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND step = %s
                """,
                    (user_id, step),
                )

                # إذا لم تكن موجودة، أضفها
                if cursor.rowcount == 0:
                    cursor.execute(
                        """
                        INSERT INTO user_onboarding (user_id, step, shown_at, dismissed_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                        (user_id, step),
                    )

                return True
        except Exception as e:
            self.logger.error(f"خطأ في تجاهل الخطوة: {e}")
            return False

    def can_receive_trading_notifications(self, user_id: int) -> bool:
        """
        فحص إذا يمكن للمستخدم استلام إشعارات التداول
        فقط إذا: لديه مفاتيح + التداول مُفعّل
        """
        stage = self.get_user_stage(user_id)
        return stage == UserStage.TRADING_ACTIVE

    def get_user_progress(self, user_id: int) -> Dict:
        """جلب تقدم المستخدم في الإعداد"""
        stage = self.get_user_stage(user_id)

        progress_map = {
            UserStage.NEW: 0,
            UserStage.PROFILE_COMPLETE: 25,
            UserStage.KEYS_ADDED: 50,
            UserStage.KEYS_VERIFIED: 75,
            UserStage.TRADING_ACTIVE: 100,
        }

        return {
            "stage": stage.value,
            "progress": progress_map.get(stage, 0),
            "can_trade": stage == UserStage.TRADING_ACTIVE,
            "next_step": self.get_next_step(user_id),
        }


# Singleton instance
_onboarding_service = None


def get_onboarding_service() -> UserOnboardingService:
    """جلب instance واحد من الخدمة"""
    global _onboarding_service
    if _onboarding_service is None:
        _onboarding_service = UserOnboardingService()
    return _onboarding_service
