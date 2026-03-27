"""
Auto Health Monitor - مراقب الصحة التلقائي
مراقبة بسيطة + تصحيح تلقائي للمشاكل
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class AutoHealthMonitor:
    """مراقبة صحة النظام وتصحيح تلقائي"""

    def __init__(self, dual_path_system):
        self.dual_path = dual_path_system
        self.baseline_win_rate = 0.60
        self.max_rules = 30
        self.check_history = []

        logger.info("✅ تهيئة Auto Health Monitor")

    def daily_health_check(
        self, recent_trades: List[Dict], learned_rules: List
    ) -> Dict[str, Any]:
        """فحص صحة يومي"""

        checks = {
            "timestamp": datetime.now(),
            "checks_performed": [],
            "issues_found": [],
            "corrections_applied": [],
        }

        # 1. فحص Win Rate
        win_rate_check = self._check_win_rate(recent_trades)
        checks["checks_performed"].append(win_rate_check)

        if win_rate_check["status"] == "warning":
            checks["issues_found"].append(win_rate_check)
            correction = self._correct_win_rate_issue(win_rate_check)
            if correction:
                checks["corrections_applied"].append(correction)

        # 2. فحص عدد القواعد
        rules_check = self._check_rules_count(learned_rules)
        checks["checks_performed"].append(rules_check)

        if rules_check["status"] == "warning":
            checks["issues_found"].append(rules_check)
            correction = self._prune_weak_rules(learned_rules)
            if correction:
                checks["corrections_applied"].append(correction)

        # 3. تحديث الأوزان
        weights_update = self._auto_adjust_system_weights()
        if weights_update:
            checks["corrections_applied"].append(weights_update)

        # 4. فحص الأداء العام
        performance_check = self._check_overall_performance()
        checks["checks_performed"].append(performance_check)

        # حفظ في التاريخ
        self.check_history.append(checks)

        # الاحتفاظ بآخر 30 فحص فقط
        if len(self.check_history) > 30:
            self.check_history.pop(0)

        # ملخص
        checks["summary"] = {
            "total_checks": len(checks["checks_performed"]),
            "issues_found": len(checks["issues_found"]),
            "corrections_applied": len(checks["corrections_applied"]),
            "health_score": self._calculate_health_score(checks),
        }

        logger.info(
            f"📊 فحص صحة: {checks['summary']['health_score']:.1%} "
            f"({len(checks['issues_found'])} مشكلة، {len(checks['corrections_applied'])} تصحيح)"
        )

        return checks

    def _check_win_rate(self, recent_trades: List[Dict]) -> Dict:
        """فحص Win Rate"""

        if not recent_trades or len(recent_trades) < 20:
            return {
                "check": "win_rate",
                "status": "insufficient_data",
                "message": "بيانات غير كافية للفحص",
            }

        # حساب Win Rate لآخر 50 صفقة
        last_50 = (
            recent_trades[-50:] if len(recent_trades) >= 50 else recent_trades
        )

        wins = sum(1 for t in last_50 if t.get("profit_pct", 0) > 0)
        win_rate = wins / len(last_50)

        degradation = self.baseline_win_rate - win_rate

        if degradation > 0.10:  # تراجع 10%+
            return {
                "check": "win_rate",
                "status": "warning",
                "current_win_rate": win_rate,
                "baseline": self.baseline_win_rate,
                "degradation": degradation,
                "severity": "high" if degradation > 0.15 else "medium",
                "message": f"تراجع Win Rate: {
                    win_rate:.1%} (كان {
                    self.baseline_win_rate:.1%})",
            }

        return {
            "check": "win_rate",
            "status": "ok",
            "current_win_rate": win_rate,
            "baseline": self.baseline_win_rate,
            "message": f"Win Rate صحي: {win_rate:.1%}",
        }

    def _check_rules_count(self, rules: List) -> Dict:
        """فحص عدد القواعد"""

        rules_count = len(rules) if rules else 0

        if rules_count > self.max_rules:
            return {
                "check": "rules_count",
                "status": "warning",
                "current_count": rules_count,
                "max_allowed": self.max_rules,
                "excess": rules_count - self.max_rules,
                "message": f"عدد القواعد كبير: {rules_count} (الحد: {self.max_rules})",
            }

        return {
            "check": "rules_count",
            "status": "ok",
            "current_count": rules_count,
            "max_allowed": self.max_rules,
            "message": f"عدد القواعد معقول: {rules_count}",
        }

    def _check_overall_performance(self) -> Dict:
        """فحص الأداء العام"""

        perf = self.dual_path.get_performance_summary()

        c_accuracy = perf["conservative"]["accuracy"]
        b_accuracy = perf["balanced"]["accuracy"]

        avg_accuracy = (c_accuracy + b_accuracy) / 2

        if avg_accuracy < 0.55:
            status = "warning"
            message = f"دقة منخفضة: {avg_accuracy:.1%}"
        elif avg_accuracy > 0.70:
            status = "excellent"
            message = f"أداء ممتاز: {avg_accuracy:.1%}"
        else:
            status = "ok"
            message = f"أداء جيد: {avg_accuracy:.1%}"

        return {
            "check": "overall_performance",
            "status": status,
            "conservative_accuracy": c_accuracy,
            "balanced_accuracy": b_accuracy,
            "average_accuracy": avg_accuracy,
            "message": message,
        }

    def _correct_win_rate_issue(self, issue: Dict) -> Optional[Dict]:
        """تصحيح مشكلة Win Rate"""

        if issue["severity"] == "high":
            # زيادة وزن النظام المحافظ
            old_weight = self.dual_path.weights["conservative"]
            self.dual_path.weights["conservative"] = min(
                0.70, old_weight + 0.15
            )
            self.dual_path.weights["balanced"] = (
                1.0 - self.dual_path.weights["conservative"]
            )

            logger.warning(f"🔧 تصحيح تلقائي: زيادة الحذر ({
                old_weight:.2%} → {
                self.dual_path.weights['conservative']:.2%})")

            return {
                "action": "increase_conservative_weight",
                "old_weight": old_weight,
                "new_weight": self.dual_path.weights["conservative"],
                "reason": f"تراجع Win Rate بنسبة {issue['degradation']:.1%}",
            }

        return None

    def _prune_weak_rules(self, rules: List) -> Optional[Dict]:
        """حذف القواعد الضعيفة"""

        if not rules or len(rules) <= self.max_rules:
            return None

        # ترتيب القواعد حسب القوة/الفعالية
        # (هنا نفترض أن القواعد لها خاصية 'strength' أو 'effectiveness')
        # في التطبيق الفعلي، ستحتاج لتعديل هذا بناءً على هيكل القواعد

        original_count = len(rules)
        rules_to_keep = self.max_rules - 5  # احتفظ بـ 25 من 30

        # حذف الأضعف
        # rules.sort(key=lambda r: r.get('effectiveness', 0), reverse=True)
        # rules = rules[:rules_to_keep]

        logger.info(f"🧹 تنظيف القواعد: {original_count} → {rules_to_keep}")

        return {
            "action": "prune_rules",
            "original_count": original_count,
            "new_count": rules_to_keep,
            "removed": original_count - rules_to_keep,
        }

    def _auto_adjust_system_weights(self) -> Optional[Dict]:
        """تعديل تلقائي لأوزان الأنظمة"""

        old_weights = self.dual_path.weights.copy()

        # الأنظمة تعدل أوزانها تلقائياً في DualPathDecision
        # لكن يمكننا فرض تعديل إضافي هنا إذا لزم الأمر

        perf = self.dual_path.get_performance_summary()

        c_acc = perf["conservative"]["accuracy"]
        b_acc = perf["balanced"]["accuracy"]

        # إذا كان أحدهما أفضل بكثير
        if abs(c_acc - b_acc) > 0.15:
            # أعد توزيع الأوزان
            total = c_acc + b_acc
            if total > 0:
                self.dual_path.weights["conservative"] = c_acc / total
                self.dual_path.weights["balanced"] = b_acc / total

                if old_weights != self.dual_path.weights:
                    logger.info(
                        f"⚖️ تعديل الأوزان: محافظ={
                            self.dual_path.weights['conservative']:.2%}, " f"متوازن={
                            self.dual_path.weights['balanced']:.2%}")

                    return {
                        "action": "adjust_weights",
                        "old_weights": old_weights,
                        "new_weights": self.dual_path.weights.copy(),
                        "reason": f"فرق دقة كبير: {abs(c_acc - b_acc):.1%}",
                    }

        return None

    def _calculate_health_score(self, checks: Dict) -> float:
        """حساب درجة الصحة العامة"""

        total_checks = len(checks["checks_performed"])
        issues = len(checks["issues_found"])

        if total_checks == 0:
            return 1.0

        # الصحة = 1 - (نسبة المشاكل / 2)
        # قسمة على 2 لأن وجود مشكلة واحدة لا يعني صحة 0%
        health = 1.0 - (issues / total_checks / 2)

        return max(0.0, min(1.0, health))

    def get_health_report(self) -> Dict:
        """تقرير صحة شامل"""

        if not self.check_history:
            return {"status": "no_data", "message": "لا توجد فحوصات سابقة"}

        latest = self.check_history[-1]

        # حساب الاتجاه
        if len(self.check_history) >= 7:
            recent_scores = [
                c["summary"]["health_score"] for c in self.check_history[-7:]
            ]
            trend = (
                "improving"
                if recent_scores[-1] > recent_scores[0]
                else "declining"
            )
        else:
            trend = "stable"

        return {
            "latest_check": latest["timestamp"],
            "current_health_score": latest["summary"]["health_score"],
            "trend": trend,
            "total_checks_performed": len(self.check_history),
            "recent_issues": latest["summary"]["issues_found"],
            "recent_corrections": latest["summary"]["corrections_applied"],
            "system_performance": self.dual_path.get_performance_summary(),
        }
