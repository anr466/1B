#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
فحص الرصيد الحر (Free Balance)
================================
التحقق من أن الرصيد الحر كافٍ لفتح صفقات جديدة
"""

from typing import Dict, Tuple


class BalanceChecker:
    """
    فحص الرصيد الحر والتأكد من إمكانية فتح صفقات جديدة
    """

    # الحد الأدنى للتداول في Binance (USDT)
    # يختلف حسب العملة، لكن عموماً 5-10 USDT
    MIN_TRADE_SIZE_BINANCE = 10.0

    # هامش أمان (للتأكد من أن الصفقة ستمر)
    SAFETY_MARGIN = 1.2  # 20% هامش أمان

    def __init__(self, binance_client, db_manager=None):
        """تهيئة الفاحص"""
        self.binance_client = binance_client
        self.db_manager = db_manager

    def get_free_balance(self) -> float:
        """
        جلب الرصيد الحر (Free Balance) من Binance

        Returns:
            الرصيد الحر بالـ USDT
        """
        try:
            balance_data = self.binance_client.get_asset_balance("USDT")

            if balance_data:
                free_balance = float(balance_data.get("free", 0))
                return free_balance

            return 0.0

        except Exception as e:
            print(f"خطأ في جلب الرصيد الحر: {e}")
            return 0.0

    def get_total_balance(self) -> Dict[str, float]:
        """
        جلب تفاصيل الرصيد الكامل

        Returns:
            {
                'free': الرصيد الحر,
                'locked': الرصيد المحجوز في صفقات,
                'total': إجمالي الرصيد
            }
        """
        try:
            balance_data = self.binance_client.get_asset_balance("USDT")

            if balance_data:
                free = float(balance_data.get("free", 0))
                locked = float(balance_data.get("locked", 0))
                total = free + locked

                return {"free": free, "locked": locked, "total": total}

            return {"free": 0.0, "locked": 0.0, "total": 0.0}

        except Exception as e:
            print(f"خطأ في جلب تفاصيل الرصيد: {e}")
            return {"free": 0.0, "locked": 0.0, "total": 0.0}

    def can_open_new_trade(
        self, required_size: float = None
    ) -> Tuple[bool, str]:
        """
        التحقق من إمكانية فتح صفقة جديدة

        Args:
            required_size: حجم الصفقة المطلوب (اختياري)

        Returns:
            (bool, str): (هل يمكن فتح الصفقة, السبب)
        """
        try:
            free_balance = self.get_free_balance()

            # إذا لم يُحدد حجم الصفقة، استخدم الحد الأدنى
            if required_size is None:
                required_size = self.MIN_TRADE_SIZE_BINANCE

            # إضافة هامش أمان
            required_with_margin = required_size * self.SAFETY_MARGIN

            # التحقق
            if free_balance < self.MIN_TRADE_SIZE_BINANCE:
                return False, f"الرصيد الحر ({
                    free_balance:.2f} USDT) أقل من الحد الأدنى ({
                    self.MIN_TRADE_SIZE_BINANCE} USDT)"

            if free_balance < required_with_margin:
                return False, f"الرصيد الحر ({
                    free_balance:.2f} USDT) لا يكفي للصفقة المطلوبة ({
                    required_size:.2f} USDT + هامش)"

            return True, f"الرصيد الحر كافٍ ({free_balance:.2f} USDT)"

        except Exception as e:
            return False, f"خطأ في فحص الرصيد: {e}"

    def is_balance_too_low_for_trading(self) -> bool:
        """
        التحقق من أن الرصيد الحر منخفض جداً (يحتاج إشعار)

        المعيار:
        - الرصيد الحر < الحد الأدنى للتداول في Binance

        Returns:
            True إذا كان الرصيد منخفض جداً
        """
        try:
            free_balance = self.get_free_balance()

            # الرصيد منخفض إذا كان أقل من الحد الأدنى
            is_low = free_balance < self.MIN_TRADE_SIZE_BINANCE

            return is_low

        except Exception as e:
            print(f"خطأ في فحص انخفاض الرصيد: {e}")
            return False

    def get_max_trade_size(self, risk_percentage: float = 0.05) -> float:
        """
        حساب أقصى حجم صفقة ممكن بناءً على الرصيد الحر

        Args:
            risk_percentage: نسبة المخاطرة (افتراضي 5%)

        Returns:
            أقصى حجم صفقة ممكن
        """
        try:
            free_balance = self.get_free_balance()

            # أقصى حجم = الرصيد الحر × نسبة المخاطرة
            max_size = free_balance * risk_percentage

            # التأكد من أنه فوق الحد الأدنى
            if max_size < self.MIN_TRADE_SIZE_BINANCE:
                return 0.0  # لا يمكن فتح صفقة

            return max_size

        except Exception as e:
            print(f"خطأ في حساب أقصى حجم صفقة: {e}")
            return 0.0

    def get_available_slots(self, avg_trade_size: float) -> int:
        """
        حساب عدد الصفقات الممكن فتحها بناءً على الرصيد الحر

        Args:
            avg_trade_size: متوسط حجم الصفقة

        Returns:
            عدد الصفقات الممكنة
        """
        try:
            free_balance = self.get_free_balance()

            if avg_trade_size <= 0:
                return 0

            # عدد الصفقات = الرصيد الحر / متوسط حجم الصفقة
            slots = int(free_balance / avg_trade_size)

            return max(0, slots)

        except Exception as e:
            print(f"خطأ في حساب الصفقات المتاحة: {e}")
            return 0

    def get_balance_status(self) -> Dict:
        """
        جلب حالة الرصيد الكاملة

        Returns:
            {
                'free': الرصيد الحر,
                'locked': الرصيد المحجوز,
                'total': إجمالي الرصيد,
                'can_trade': هل يمكن التداول,
                'is_low': هل الرصيد منخفض,
                'available_slots': عدد الصفقات الممكنة,
                'max_trade_size': أقصى حجم صفقة
            }
        """
        try:
            balance = self.get_total_balance()
            can_trade, reason = self.can_open_new_trade()
            is_low = self.is_balance_too_low_for_trading()

            # افتراض متوسط حجم صفقة 50 USDT
            avg_trade_size = 50
            available_slots = self.get_available_slots(avg_trade_size)
            max_trade_size = self.get_max_trade_size()

            return {
                "free": balance["free"],
                "locked": balance["locked"],
                "total": balance["total"],
                "can_trade": can_trade,
                "trade_status_reason": reason,
                "is_low": is_low,
                "available_slots": available_slots,
                "max_trade_size": max_trade_size,
                "min_required": self.MIN_TRADE_SIZE_BINANCE,
            }

        except Exception as e:
            print(f"خطأ في جلب حالة الرصيد: {e}")
            return {
                "free": 0.0,
                "locked": 0.0,
                "total": 0.0,
                "can_trade": False,
                "trade_status_reason": str(e),
                "is_low": True,
                "available_slots": 0,
                "max_trade_size": 0.0,
                "min_required": self.MIN_TRADE_SIZE_BINANCE,
            }


# ============================================================================
# مثال على الاستخدام
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("  مثال على فحص الرصيد الحر")
    print("=" * 80)

    # محاكاة بيانات Binance
    class MockBinanceClient:
        def get_asset_balance(self, asset):
            return {
                "asset": "USDT",
                "free": "5.50",  # رصيد حر منخفض
                "locked": "994.50",  # محجوز في صفقات
            }

    # إنشاء الفاحص
    checker = BalanceChecker(MockBinanceClient())

    # جلب الحالة
    status = checker.get_balance_status()

    print("\n📊 حالة الرصيد:\n")
    print(f"   الرصيد الحر: {status['free']:.2f} USDT")
    print(f"   الرصيد المحجوز: {status['locked']:.2f} USDT")
    print(f"   إجمالي الرصيد: {status['total']:.2f} USDT")
    print(f"   الحد الأدنى المطلوب: {status['min_required']:.2f} USDT")
    print()
    print(
        f"   هل يمكن التداول: {'✅ نعم' if status['can_trade'] else '❌ لا'}"
    )
    print(f"   السبب: {status['trade_status_reason']}")
    print(f"   هل الرصيد منخفض: {'✅ نعم' if status['is_low'] else '❌ لا'}")
    print(f"   عدد الصفقات الممكنة: {status['available_slots']}")
    print(f"   أقصى حجم صفقة: {status['max_trade_size']:.2f} USDT")

    print("\n" + "=" * 80)

    if status["is_low"]:
        print("\n⚠️  تحذير: الرصيد الحر منخفض!")
        print("   لا يمكن فتح صفقات جديدة حتى يتم إغلاق بعض الصفقات المفتوحة.")
