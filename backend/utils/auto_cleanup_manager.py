#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام التنظيف التلقائي - Auto Cleanup Manager
يدير ملفات النسخ الاحتياطية وسجلات الأخطاء والعمليات وملفات JSON

الميزات:
1. حذف النسخ الاحتياطية القديمة (يبقي الأحدث فقط)
2. تنظيف سجلات الأخطاء القديمة
3. تنظيف سجلات العمليات
4. تنظيف ملفات JSON المؤقتة
5. يعمل تلقائياً عند تشغيل النظام
"""

import os
import glob
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

# إعداد التسجيل
logger = logging.getLogger(__name__)


class AutoCleanupManager:
    """
    مدير التنظيف التلقائي
    يحذف الملفات القديمة ويبقي ملف واحد من كل نوع
    """

    def __init__(self, project_root: str = None):
        """
        تهيئة مدير التنظيف

        Args:
            project_root: المسار الجذر للمشروع
        """
        if project_root:
            self.project_root = Path(project_root)
        else:
            # تحديد المسار تلقائياً
            self.project_root = Path(__file__).parent.parent.parent

        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        # افتراضيًا: مفعل في التطوير، ومعطل في الإنتاج إلا إذا تم تفعيله صراحة
        enabled_default = "0" if self.environment == "production" else "1"
        self.cleanup_enabled = (
            os.getenv("AUTO_CLEANUP_ENABLED", enabled_default) == "1"
        )
        # في الإنتاج: dry-run افتراضيًا لحماية الملفات والسجلات
        dry_run_default = "1" if self.environment == "production" else "0"
        self.production_dry_run = (
            os.getenv("AUTO_CLEANUP_DRY_RUN", dry_run_default) == "1"
        )

        # إعدادات التنظيف
        self.config = {
            # النسخ الاحتياطية لقاعدة البيانات
            "database_backups": {
                "path": self.project_root / "database",
                # PostgreSQL — all .db files are legacy artifacts
                "patterns": ["*.db"],
                "keep_count": 1,  # يبقي نسخة واحدة فقط
                "description": "نسخ قاعدة البيانات الاحتياطية",
            },
            # سجلات الأخطاء
            "error_logs": {
                "path": self.project_root / "logs",
                "patterns": ["error*.log", "errors*.log", "*.error.log"],
                "keep_count": 1,
                "description": "سجلات الأخطاء",
            },
            # سجلات العمليات
            "operation_logs": {
                "path": self.project_root / "logs",
                "patterns": ["*.log", "!error*.log"],
                "keep_count": 5,
                "description": "سجلات العمليات",
            },
            # ملفات JSON المؤقتة
            "temp_json": {
                "path": self.project_root,
                "patterns": ["*_temp.json", "*_backup*.json", "*_old.json"],
                "keep_count": 0,  # حذف الكل
                "description": "ملفات JSON المؤقتة",
            },
            # ملفات __pycache__
            "pycache": {
                "path": self.project_root,
                "patterns": ["__pycache__"],
                "keep_count": 0,
                "is_directory": True,
                "description": "ملفات Python المؤقتة",
                "enabled_in_production": False,
            },
            # ملفات .pyc
            "pyc_files": {
                "path": self.project_root,
                "patterns": ["*.pyc"],
                "keep_count": 0,
                "description": "ملفات Python المترجمة",
                "enabled_in_production": False,
            },
        }

        self._apply_environment_policy()

        # إحصائيات التنظيف
        self.stats = {"files_deleted": 0, "space_freed": 0, "errors": []}

    def cleanup_all(self, dry_run: bool = False) -> Dict:
        """
        تنظيف جميع الملفات القديمة

        Args:
            dry_run: إذا True، يعرض ما سيتم حذفه بدون حذف فعلي

        Returns:
            إحصائيات التنظيف
        """
        if not self.cleanup_enabled:
            logger.info("ℹ️ Auto cleanup disabled by policy/environment")
            return {
                "files_deleted": 0,
                "directories_deleted": 0,
                "space_freed": 0,
                "errors": [],
                "details": {},
                "dry_run": True,
                "cleanup_enabled": False,
            }

        effective_dry_run = dry_run or self.production_dry_run
        logger.info(
            f"🧹 بدء التنظيف التلقائي... (dry_run={effective_dry_run})"
        )

        self.stats = {
            "files_deleted": 0,
            "directories_deleted": 0,
            "space_freed": 0,
            "errors": [],
            "details": {},
        }

        for category, config in self.config.items():
            if (
                self.environment == "production"
                and config.get("enabled_in_production") is False
            ):
                self.stats["details"][category] = {
                    "deleted": [],
                    "kept": [],
                    "errors": [],
                    "skipped": "production_policy",
                }
                continue

            result = self._cleanup_category(
                category, config, effective_dry_run
            )
            self.stats["details"][category] = result

        # ملخص
        if effective_dry_run:
            logger.info(f"🔍 [معاينة] سيتم حذف {
                self.stats['files_deleted']} ملف")
        else:
            logger.info(f"✅ تم حذف {self.stats['files_deleted']} ملف")
            logger.info(f"💾 تم توفير {
                self.stats['space_freed'] /
                1024 /
                1024:.2f} MB")

        self.stats["dry_run"] = effective_dry_run
        self.stats["cleanup_enabled"] = self.cleanup_enabled

        return self.stats

    def _apply_environment_policy(self):
        """تطبيق سياسة أمان البيئة (خصوصًا الإنتاج)."""
        if self.environment != "production":
            return

        # في الإنتاج نرفع الاحتفاظ بالملفات المهمة
        if "error_logs" in self.config:
            self.config["error_logs"]["keep_count"] = max(
                7, self.config["error_logs"].get("keep_count", 1)
            )
        if "operation_logs" in self.config:
            self.config["operation_logs"]["keep_count"] = max(
                7, self.config["operation_logs"].get("keep_count", 1)
            )
        if "database_backups" in self.config:
            self.config["database_backups"]["keep_count"] = max(
                3, self.config["database_backups"].get("keep_count", 1)
            )

    def _cleanup_category(
        self, category: str, config: Dict, dry_run: bool
    ) -> Dict:
        """
        تنظيف فئة معينة من الملفات
        """
        result = {"deleted": [], "kept": [], "errors": []}

        path = config["path"]
        patterns = config["patterns"]
        keep_count = config["keep_count"]
        is_directory = config.get("is_directory", False)

        if not path.exists():
            return result

        # جمع الملفات المطابقة
        files_to_check = []

        for pattern in patterns:
            # تجاهل الأنماط المستثناة (تبدأ بـ !)
            if pattern.startswith("!"):
                continue

            if is_directory:
                # البحث عن المجلدات
                for root, dirs, _ in os.walk(path):
                    for d in dirs:
                        if d == pattern or glob.fnmatch.fnmatch(d, pattern):
                            dir_path = Path(root) / d
                            files_to_check.append(dir_path)
            else:
                # البحث عن الملفات
                for file_path in path.rglob(pattern):
                    # التحقق من الاستثناءات
                    excluded = False
                    for exc_pattern in patterns:
                        if exc_pattern.startswith("!"):
                            if glob.fnmatch.fnmatch(
                                file_path.name, exc_pattern[1:]
                            ):
                                excluded = True
                                break

                    if not excluded and file_path.is_file():
                        files_to_check.append(file_path)

        # إزالة التكرارات
        files_to_check = list(set(files_to_check))

        if not files_to_check:
            return result

        # ترتيب حسب تاريخ التعديل (الأحدث أولاً)
        files_to_check.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # تحديد الملفات للحذف
        files_to_keep = files_to_check[:keep_count]
        files_to_delete = files_to_check[keep_count:]

        result["kept"] = [str(f) for f in files_to_keep]

        # الحذف
        for file_path in files_to_delete:
            try:
                size = self._get_size(file_path)

                if not dry_run:
                    if file_path.is_dir():
                        shutil.rmtree(file_path)
                        self.stats["directories_deleted"] += 1
                    else:
                        file_path.unlink()
                        self.stats["files_deleted"] += 1

                    self.stats["space_freed"] += size
                else:
                    self.stats["files_deleted"] += 1
                    self.stats["space_freed"] += size

                result["deleted"].append(str(file_path))

            except Exception as e:
                error_msg = f"خطأ في حذف {file_path}: {e}"
                result["errors"].append(error_msg)
                self.stats["errors"].append(error_msg)
                logger.warning(error_msg)

        return result

    def _get_size(self, path: Path) -> int:
        """حساب حجم ملف أو مجلد"""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            total = 0
            for f in path.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
            return total
        return 0

    def cleanup_database_backups(self, keep_latest: int = 1) -> Dict:
        """
        تنظيف نسخ قاعدة البيانات الاحتياطية

        Args:
            keep_latest: عدد النسخ للإبقاء عليها
        """
        db_path = self.project_root / "database"

        # البحث عن ملفات .db ما عدا الرئيسي
        db_files = []
        for f in db_path.glob("*.db"):
            if f.name.endswith(".db"):
                db_files.append(f)

        # ترتيب حسب التاريخ
        db_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # الحذف
        deleted = []
        kept = db_files[:keep_latest]

        for f in db_files[keep_latest:]:
            try:
                size = f.stat().st_size
                f.unlink()
                deleted.append({"file": str(f), "size": size})
                logger.info(f"🗑️ تم حذف: {f.name}")
            except Exception as e:
                logger.error(f"خطأ في حذف {f}: {e}")

        return {
            "deleted": deleted,
            "kept": [str(f) for f in kept],
            "total_freed": sum(d["size"] for d in deleted),
        }

    def cleanup_logs(
        self, max_age_days: int = 7, keep_latest: int = 1
    ) -> Dict:
        """
        تنظيف ملفات السجلات

        Args:
            max_age_days: حذف الملفات الأقدم من هذا العدد من الأيام
            keep_latest: الإبقاء على هذا العدد من الملفات الأحدث
        """
        logs_path = self.project_root / "logs"

        if not logs_path.exists():
            return {"deleted": [], "kept": []}

        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        log_files = list(logs_path.glob("*.log"))
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        deleted = []
        kept = log_files[:keep_latest]

        for f in log_files[keep_latest:]:
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff_date:
                    size = f.stat().st_size
                    f.unlink()
                    deleted.append({"file": str(f), "size": size})
                    logger.info(f"🗑️ تم حذف: {f.name}")
                else:
                    kept.append(f)
            except Exception as e:
                logger.error(f"خطأ في حذف {f}: {e}")

        return {
            "deleted": deleted,
            "kept": [str(f) for f in kept],
            "total_freed": sum(d["size"] for d in deleted),
        }

    def cleanup_temp_files(self) -> Dict:
        """تنظيف الملفات المؤقتة"""
        patterns = [
            "**/*.pyc",
            "**/__pycache__",
            "**/*.tmp",
            "**/*_temp.json",
            "**/*_backup_*.json",
        ]

        deleted = []

        for pattern in patterns:
            for f in self.project_root.glob(pattern):
                try:
                    if f.is_dir():
                        shutil.rmtree(f)
                    else:
                        f.unlink()
                    deleted.append(str(f))
                except Exception as e:
                    logger.debug(f"تجاهل: {f}: {e}")

        return {"deleted": deleted}

    def get_cleanup_report(self) -> str:
        """إنشاء تقرير التنظيف"""
        report = []
        report.append("=" * 60)
        report.append("📋 تقرير التنظيف التلقائي")
        report.append("=" * 60)
        report.append(f"التاريخ: {
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # إحصائيات
        report.append("📊 الإحصائيات:")
        report.append(
            f"   - الملفات المحذوفة: {self.stats.get('files_deleted', 0)}"
        )
        report.append(
            f"   - المجلدات المحذوفة: {self.stats.get('directories_deleted', 0)}"
        )
        report.append(
            f"   - المساحة المحررة: {self.stats.get('space_freed', 0) / 1024 / 1024:.2f} MB"
        )
        report.append("")

        # التفاصيل
        if "details" in self.stats:
            report.append("📁 التفاصيل:")
            for category, details in self.stats["details"].items():
                if details.get("deleted"):
                    report.append(f"\n   {category}:")
                    for f in details["deleted"][:5]:
                        report.append(f"      🗑️ {Path(f).name}")
                    if len(details["deleted"]) > 5:
                        report.append(
                            f"      ... و {len(details['deleted']) - 5} ملفات أخرى"
                        )

        # الأخطاء
        if self.stats.get("errors"):
            report.append("\n⚠️ الأخطاء:")
            for error in self.stats["errors"][:5]:
                report.append(f"   - {error}")

        report.append("")
        report.append("=" * 60)

        return "\n".join(report)


# ============================================================
# دالة التنظيف السريع
# ============================================================


def quick_cleanup(dry_run: bool = False) -> Dict:
    """
    تنظيف سريع - يُستدعى عند تشغيل النظام

    Args:
        dry_run: معاينة بدون حذف فعلي

    Returns:
        إحصائيات التنظيف
    """
    manager = AutoCleanupManager()
    return manager.cleanup_all(dry_run=dry_run)


def cleanup_on_startup():
    """
    يُستدعى تلقائياً عند تشغيل النظام
    """
    try:
        manager = AutoCleanupManager()
        stats = manager.cleanup_all(dry_run=False)

        if stats.get("files_deleted", 0) > 0:
            print(f"🧹 تنظيف تلقائي: حذف {stats['files_deleted']} ملف")
            print(f"💾 توفير: {stats['space_freed'] / 1024 / 1024:.2f} MB")

        return stats
    except Exception as e:
        logger.error(f"خطأ في التنظيف التلقائي: {e}")
        return None


# ============================================================
# Singleton
# ============================================================

_cleanup_manager = None


def get_cleanup_manager() -> AutoCleanupManager:
    """الحصول على مدير التنظيف (Singleton)"""
    global _cleanup_manager
    if _cleanup_manager is None:
        _cleanup_manager = AutoCleanupManager()
    return _cleanup_manager


# ============================================================
# التشغيل المباشر
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="نظام التنظيف التلقائي")
    parser.add_argument(
        "--dry-run", action="store_true", help="معاينة بدون حذف"
    )
    parser.add_argument(
        "--report", action="store_true", help="عرض التقرير فقط"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🧹 نظام التنظيف التلقائي")
    print("=" * 60)

    manager = AutoCleanupManager()

    if args.dry_run:
        print("\n🔍 وضع المعاينة (بدون حذف فعلي):\n")

    stats = manager.cleanup_all(dry_run=args.dry_run)

    print(manager.get_cleanup_report())
