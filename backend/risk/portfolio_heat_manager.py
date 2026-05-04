"""
Portfolio Heat Manager - إدارة حرارة المحفظة
مراقبة إجمالي المخاطرة في جميع الصفقات المفتوحة
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class PortfolioHeatManager:
    """
    إدارة حرارة المحفظة

    Portfolio Heat = مجموع المخاطرة في جميع الصفقات المفتوحة
    """

    def __init__(self, max_heat_pct: float = 6.0):
        self.logger = logger
        self.max_heat_pct = max_heat_pct  # 6% حد أقصى

    def check_portfolio_heat(
        self, open_positions: List[Dict], balance: float
    ) -> Dict:
        """
        فحص حرارة المحفظة

        Args:
            open_positions: قائمة الصفقات المفتوحة
            balance: الرصيد الحالي

        Returns:
            Dict مع تفاصيل الحرارة
        """
        try:
            if not open_positions:
                return {
                    "current_heat_pct": 0,
                    "max_heat_pct": self.max_heat_pct,
                    "available_heat_pct": self.max_heat_pct,
                    "can_open_new": True,
                    "positions_count": 0,
                }

            total_risk = 0

            # حساب المخاطرة في كل صفقة
            for position in open_positions:
                risk = self._calculate_position_risk(position, balance)
                total_risk += risk

            current_heat_pct = (total_risk / balance) * 100
            available_heat_pct = max(0, self.max_heat_pct - current_heat_pct)

            return {
                "current_heat_pct": round(current_heat_pct, 2),
                "max_heat_pct": self.max_heat_pct,
                "available_heat_pct": round(available_heat_pct, 2),
                "can_open_new": current_heat_pct < self.max_heat_pct,
                "positions_count": len(open_positions),
                "heat_status": self._get_heat_status(current_heat_pct),
            }

        except Exception as e:
            self.logger.error(f"Error checking portfolio heat: {e}")
            return self._get_safe_heat_response()

    def _calculate_position_risk(
        self, position: Dict, balance: float
    ) -> float:
        """
        حساب المخاطرة في صفقة واحدة

        Risk = (Entry Price - Stop Loss) × Quantity
        """
        try:
            entry_price = position.get("entry_price", 0)
            stop_loss = position.get("stop_loss", 0)
            # ✅ FIX: الحقل الصحيح هو 'quantity' (من جدول active_positions)، وليس 'size'
            quantity = position.get("quantity", 0)

            if entry_price == 0 or stop_loss == 0 or quantity == 0:
                return 0

            # المخاطرة = المسافة من SL × الكمية
            risk_per_unit = abs(entry_price - stop_loss)
            total_risk = risk_per_unit * quantity

            return total_risk

        except Exception as e:
            self.logger.error(f"Error calculating position risk: {e}")
            return 0

    def can_add_position(
        self, new_position_risk_pct: float, current_heat_pct: float
    ) -> bool:
        """
        هل يمكن إضافة صفقة جديدة؟

        Args:
            new_position_risk_pct: مخاطرة الصفقة الجديدة (%)
            current_heat_pct: الحرارة الحالية (%)

        Returns:
            True إذا آمن فتح صفقة جديدة
        """
        total_heat = current_heat_pct + new_position_risk_pct
        return total_heat <= self.max_heat_pct

    def _get_heat_status(self, heat_pct: float) -> str:
        """تصنيف حالة الحرارة"""
        if heat_pct >= self.max_heat_pct:
            return "CRITICAL"
        elif heat_pct >= self.max_heat_pct * 0.8:
            return "HIGH"
        elif heat_pct >= self.max_heat_pct * 0.5:
            return "MEDIUM"
        else:
            return "LOW"

    def _get_safe_heat_response(self) -> Dict:
        """استجابة آمنة عند الخطأ"""
        return {
            "current_heat_pct": 999,  # رقم عالي لمنع فتح صفقات
            "max_heat_pct": self.max_heat_pct,
            "available_heat_pct": 0,
            "can_open_new": False,
            "positions_count": 0,
            "heat_status": "ERROR",
        }
