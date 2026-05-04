"""
Rolling Window Learner - متعلم النافذة المتحركة
يتعلم من آخر X يوم فقط لضمان الحداثة
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import numpy as np

logger = logging.getLogger(__name__)


class RollingWindowLearner:
    """تعلم من البيانات الحديثة فقط (نافذة متحركة)"""

    def __init__(self, window_days: int = 90):
        self.window_days = window_days
        self.min_sample_size = 30

        logger.info(
            f"✅ تهيئة Rolling Window Learner (نافذة: {window_days} يوم)"
        )

    def get_recent_signals(
        self, all_signals: List[Dict], combination: str
    ) -> List[Dict]:
        """الحصول على الإشارات الحديثة فقط"""

        cutoff = datetime.now() - timedelta(days=self.window_days)

        recent = [
            s
            for s in all_signals
            if s.get("combination") == combination
            and s.get("timestamp", datetime.min) > cutoff
            and s.get("signal_quality_score") is not None
        ]

        return recent

    def should_learn(self, recent_signals: List[Dict]) -> bool:
        """هل العينة كافية للتعلم؟"""

        if len(recent_signals) < self.min_sample_size:
            logger.debug(f"⚠️ عينة صغيرة: {
                len(recent_signals)} < {
                self.min_sample_size}")
            return False

        # عدد الإشارات الناجحة
        good_signals = [
            s for s in recent_signals if s["signal_quality_score"] > 0.7
        ]

        if len(good_signals) < 10:
            logger.debug(f"⚠️ إشارات ناجحة قليلة: {len(good_signals)} < 10")
            return False

        return True

    def extract_patterns(self, recent_signals: List[Dict]) -> Optional[Dict]:
        """استخراج الأنماط من الإشارات الحديثة"""

        if not self.should_learn(recent_signals):
            return None

        good_signals = [
            s for s in recent_signals if s["signal_quality_score"] > 0.7
        ]
        bad_signals = [
            s for s in recent_signals if s["signal_quality_score"] < 0.4
        ]

        patterns = {
            "window_days": self.window_days,
            "total_signals": len(recent_signals),
            "good_signals": len(good_signals),
            "bad_signals": len(bad_signals),
            "success_rate": len(good_signals) / len(recent_signals),
            # الأنماط المثلى
            "optimal_conditions": self._extract_optimal_conditions(
                good_signals
            ),
            # الأنماط التي يجب تجنبها
            "avoid_conditions": (
                self._extract_avoid_conditions(bad_signals)
                if bad_signals
                else []
            ),
            "last_updated": datetime.now(),
            "data_age_days": self._calculate_data_age(recent_signals),
        }

        return patterns

    def _extract_optimal_conditions(self, good_signals: List[Dict]) -> Dict:
        """استخراج الظروف المثلى"""

        conditions = {}

        # RSI
        rsi_values = [
            s.get("entry_rsi", 50) for s in good_signals if s.get("entry_rsi")
        ]
        if rsi_values:
            conditions["rsi"] = {
                "min": float(np.percentile(rsi_values, 10)),
                "optimal_low": float(np.percentile(rsi_values, 25)),
                "median": float(np.median(rsi_values)),
                "optimal_high": float(np.percentile(rsi_values, 75)),
                "max": float(np.percentile(rsi_values, 90)),
            }

        # Volatility
        vol_values = [
            s.get("volatility", 0)
            for s in good_signals
            if s.get("volatility", 0) > 0
        ]
        if vol_values:
            conditions["volatility"] = {
                "min": float(np.percentile(vol_values, 10)),
                "optimal_low": float(np.percentile(vol_values, 25)),
                "median": float(np.median(vol_values)),
                "optimal_high": float(np.percentile(vol_values, 75)),
                "max": float(np.percentile(vol_values, 90)),
            }

        # Volume
        vol_values = [
            s.get("entry_volume", 0)
            for s in good_signals
            if s.get("entry_volume", 0) > 0
        ]
        if vol_values:
            conditions["volume"] = {
                "min": float(np.percentile(vol_values, 10)),
                "median": float(np.median(vol_values)),
                "max": float(np.percentile(vol_values, 90)),
            }

        return conditions

    def _extract_avoid_conditions(self, bad_signals: List[Dict]) -> List[Dict]:
        """استخراج الظروف التي يجب تجنبها"""

        avoid = []

        # تحليل RSI المتطرف
        extreme_rsi = [
            s
            for s in bad_signals
            if s.get("entry_rsi", 50) > 75 or s.get("entry_rsi", 50) < 25
        ]
        if len(extreme_rsi) / len(bad_signals) > 0.6:
            avoid.append(
                {
                    "condition": "extreme_rsi",
                    "description": "RSI متطرف (> 75 أو < 25)",
                    "failure_rate": len(extreme_rsi) / len(bad_signals),
                    "penalty": -0.25,
                }
            )

        # تحليل التقلب العالي
        high_vol = [s for s in bad_signals if s.get("volatility", 0) > 0.06]
        if len(high_vol) / len(bad_signals) > 0.5:
            avoid.append(
                {
                    "condition": "high_volatility",
                    "description": "تقلب عالي (> 0.06)",
                    "failure_rate": len(high_vol) / len(bad_signals),
                    "penalty": -0.20,
                }
            )

        return avoid

    def _calculate_data_age(self, signals: List[Dict]) -> float:
        """حساب متوسط عمر البيانات"""

        if not signals:
            return 0

        now = datetime.now()
        ages = [
            (now - s["timestamp"]).days for s in signals if s.get("timestamp")
        ]

        return float(np.mean(ages)) if ages else 0

    def is_data_fresh(self, patterns: Dict) -> bool:
        """هل البيانات حديثة؟"""

        if not patterns:
            return False

        last_updated = patterns.get("last_updated")
        if not last_updated:
            return False

        # البيانات قديمة إذا مر عليها أكثر من 7 أيام
        age = (datetime.now() - last_updated).days

        return age < 7
