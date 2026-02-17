---
description: مهارة إدارة تنظيف الملفات التلقائي - File Cleanup Management Skill
---

# File Cleanup Management Skill

مهارة ذكية لتنظيف وإدارة الملفات المؤقتة والزائدة في المشروع تلقائياً مع الحفاظ على الملفات المهمة.

---

## 🎯 الهدف من المهارة

**المشكلة**: تراكم الملفات المؤقتة، ملفات الاختبار المنجزة، نسخ محسنة، توثيق مؤقت
**الحل**: تنظيف تلقائي ذكي مع حماية الملفات المهمة

---

## 🔒 قواعد الأمان الإلزامية (NEVER DELETE)

```
PROTECTED FILES - لا تحذف أبداً:
├── .env                           ← إعدادات البيئة
├── .gitignore                     ← قواعد Git
├── .windsurfrules*                ← قواعد النظام
├── .windsurf/workflows/*          ← جميع المهارات
├── requirements*.txt              ← مكتبات Python
├── package.json                   ← مكتبات Node.js
├── README.md                      ← توثيق المشروع
├── ARCHITECTURE.md                ← معمارية النظام
├── start_*.py|sh                  ← ملفات التشغيل
├── database/*.sql                 ← قاعدة البيانات
├── mobile_app/TradingApp/         ← كامل التطبيق المحمول
│   ├── src/                       ← جميع مكونات React Native
│   ├── package.json               ← تكوين المشروع
│   └── app.json                   ← تكوين Expo
├── backend/                       ← جميع ملفات الخلفية
│   ├── api/                       ← جميع APIs
│   ├── core/                      ← المنطق الأساسي
│   ├── strategies/                ← استراتيجيات التداول
│   ├── cognitive/                 ← الذكاء الاصطناعي
│   ├── analysis/                  ← تحليل البيانات
│   └── ml/                        ← التعلم الآلي
├── config/                        ← جميع الإعدادات
├── monitoring/                    ← نظام المراقبة
├── utils/                         ← الأدوات المساعدة
├── bin/                          ← السكريبتات التنفيذية
└── models/                       ← نماذج البيانات
```

---

## 🗑️ أنواع الملفات القابلة للحذف

### 1. الملفات المحسنة (Improved Files)
```
PATTERNS:
├── *_v1.py  → يُحذف عند وجود *_v2.py أو أحدث
├── *_old.py → يُحذف بعد التحقق من وجود النسخة الجديدة
├── *_backup.py → يُحذف بعد 30 يوم من إنشائه
├── *_draft.py → يُحذف بعد وجود النسخة النهائية
└── *.bak → يُحذف بعد التحقق من النسخة الأصلية
```

### 2. ملفات الاختبار المؤقتة
```
SAFE TO DELETE:
├── test_*.py (في مجلد /tmp/ أو /temp/)
├── *_test_temp.py
├── debug_*.py
├── temp_*.py
├── quick_test_*.py
├── verification_*.py (المؤقت فقط)
└── *.log (أكبر من 100MB أو أقدم من 30 يوم)
```

### 3. ملفات التوثيق المؤقت
```
CLEANUP CANDIDATES:
├── TEMP_*.md
├── DRAFT_*.md
├── notes_*.txt
├── todo_*.md (بعد اكتمال المهام)
├── analysis_*.md (المؤقت)
├── debug_report_*.md (أقدم من 7 أيام)
└── *_WORKING.md
```

### 4. ملفات النتائج والتقارير القديمة
```
ARCHIVE OR DELETE:
├── backtest_results_*.json (أقدم من 60 يوم)
├── trading_report_*.json (أقدم من 30 يوم)
├── performance_*.csv (أقدم من 45 يوم)
├── error_log_*.txt (أقدر من 14 يوم)
└── screenshot_*.png (أقدم من 7 أيام)
```

---

## 🔍 آلية التنظيف الذكي

### المرحلة 1: التحليل والفحص
```python
def analyze_file_for_cleanup(file_path):
    """تحليل الملف لتحديد إمكانية حذفه"""
    
    # فحص قائمة الحماية
    if is_protected_file(file_path):
        return {"action": "KEEP", "reason": "Protected file"}
    
    # فحص النمط
    pattern_match = check_cleanup_patterns(file_path)
    if pattern_match:
        return analyze_pattern_safety(file_path, pattern_match)
    
    return {"action": "KEEP", "reason": "No cleanup pattern matched"}
```

### المرحلة 2: التحقق من الأمان
```python
def verify_safe_to_delete(file_path):
    """التحقق المضاعف من أمان الحذف"""
    
    checks = [
        check_file_dependencies(file_path),      # هل يعتمد عليه ملف آخر؟
        check_recent_modifications(file_path),   # هل تم تعديله مؤخراً؟
        check_git_tracking(file_path),          # هل مُتتبع في Git؟
        check_import_usage(file_path),          # هل مُستورد في كود آخر؟
        verify_backup_exists(file_path)         # هل يوجد نسخة احتياطية؟
    ]
    
    return all(check["safe"] for check in checks)
```

### المرحلة 3: التنفيذ التدريجي
```python
def execute_cleanup(cleanup_plan):
    """تنفيذ خطة التنظيف بحذر"""
    
    # إنشاء نسخة احتياطية مؤقتة
    backup_location = create_temp_backup(cleanup_plan["files"])
    
    try:
        for file_info in cleanup_plan["files"]:
            if file_info["confidence"] >= 0.95:  # ثقة عالية
                safe_delete(file_info["path"])
            elif file_info["confidence"] >= 0.80:  # ثقة متوسطة
                archive_file(file_info["path"])
            else:
                skip_file(file_info["path"])  # تخطي للأمان
                
    except Exception as e:
        restore_from_backup(backup_location)
        raise e
```

---

## 🎛️ مستويات التنظيف

### Level 1: Conservative (آمن جداً)
- حذف الملفات المؤكدة 100% (*.tmp, *.log الكبيرة)
- نقل الملفات المشكوك بها إلى `/_cleanup_queue/`
- عدم حذف أي شيء أقل من 99% ثقة

### Level 2: Standard (متوازن)
- حذف الملفات ذات الثقة 90%+
- أرشفة الملفات ذات الثقة 70-89%
- تنظيف ملفات الاختبار المكتملة

### Level 3: Aggressive (قوي)
- حذف الملفات ذات الثقة 80%+
- تنظيف شامل للملفات القديمة
- حذف النسخ المتعددة من نفس الوظيفة

---

## 📋 نماذج التنفيذ

### نموذج 1: تنظيف ما بعد تطوير الميزة
```
التريجر: بعد دمج branch جديد
الإجراء:
1. البحث عن ملفات test_* مؤقتة
2. حذف ملفات debug_* 
3. أرشفة نتائج الاختبار القديمة
4. تنظيف ملفات التوثيق المؤقت
```

### نموذج 2: تنظيف دوري أسبوعي
```
التريجر: كل أحد صباحاً
الإجراء:
1. فحص الملفات القديمة (>30 يوم)
2. ضغط ملفات اللوغ الكبيرة
3. نقل النسخ القديمة إلى _archive/
4. حذف ملفات cache منتهية الصلاحية
```

### نموذج 3: تنظيف طارئ (امتلاء القرص)
```
التريجر: مساحة القرص < 10%
الإجراء:
1. حذف فوري لملفات *.log الكبيرة
2. ضغط جميع ملفات النسخ الاحتياطية
3. نقل ملفات البيانات القديمة للتخزين السحابي
4. تنظيف مجلدات tmp/ و cache/
```

---

## 🚦 قواعد التطبيق في المشروع

### عند إنشاء ملف محسن:
```python
# مثال: تحسين scalping_v7_engine.py إلى scalping_v8_engine.py
def on_improved_file_created(old_file, new_file):
    """عند إنشاء نسخة محسنة"""
    
    # التحقق من عمل النسخة الجديدة
    if validate_new_version(new_file):
        # نقل النسخة القديمة للأرشيف
        archive_file(old_file, reason="superseded_by", new_version=new_file)
    else:
        # الاحتفاظ بالنسخة القديمة كـ backup
        mark_as_backup(old_file, temporary=True, expires_in="30days")
```

### عند إنهاء الاختبار:
```python
def on_test_completion(test_file):
    """عند انتهاء الاختبار"""
    
    if test_file.startswith("temp_") or test_file.startswith("quick_test_"):
        # حذف فوري للاختبارات المؤقتة
        safe_delete(test_file)
    elif test_passed_all_requirements(test_file):
        # أرشفة نتائج الاختبار الناجح
        archive_results(test_file)
    else:
        # الاحتفاظ بالاختبارات الفاشلة للمراجعة
        move_to_review_queue(test_file)
```

---

## 🔧 أدوات المساعدة

### الكشف التلقائي عن الملفات المرشحة:
```bash
# البحث عن ملفات مرشحة للتنظيف
find . -name "*_old.*" -type f -mtime +7
find . -name "test_temp_*" -type f
find . -name "*.log" -type f -size +100M
find . -name "*_backup.*" -type f -mtime +30
```

### تقرير التنظيف:
```
CLEANUP REPORT - 2026-02-16
=============================
Files Analyzed: 1,247
Files Deleted: 23 (156MB freed)
Files Archived: 7 (89MB moved)
Files Skipped: 8 (safety reasons)
Space Saved: 245MB total

Categories:
- Old test files: 12 files (67MB)
- Backup files: 8 files (78MB)  
- Log files: 3 files (100MB)
- Temp documentation: 7 files (15MB)
```

---

## ⚙️ إعدادات التكوين

```json
{
  "cleanup_settings": {
    "level": "standard",
    "auto_cleanup": true,
    "cleanup_schedule": "weekly",
    "retention_days": {
      "test_files": 7,
      "backup_files": 30,
      "log_files": 14,
      "temp_docs": 3
    },
    "size_limits": {
      "single_log_file": "100MB",
      "total_temp_files": "1GB"
    },
    "safety_checks": {
      "dependency_scan": true,
      "git_tracking_check": true,
      "recent_modification_threshold": "24hours"
    }
  }
}
```

---

## 🎯 كيفية الاستخدام

### التشغيل التلقائي:
- اكتب `/file-cleanup-skill` لتطبيق المهارة
- المهارة ستعمل تلقائياً عند إنشاء ملفات محسنة
- تنظيف دوري حسب الإعدادات

### التشغيل اليدوي:
```
أمثلة للاستخدام:
- "نظف ملفات الاختبار المؤقتة"
- "أرشف النسخ القديمة من scalping engine" 
- "احذف ملفات اللوغ الكبيرة"
- "نظف مجلد التقارير المؤقتة"
```

### التحكم الدقيق:
```python
# استخدام مخصص في الكود
from file_cleanup_skill import CleanupManager

cleanup = CleanupManager(level="conservative")
cleanup.analyze_and_clean(target_directory="backend/tests/")
```

---

## ✅ مؤشرات النجاح

- ✅ **تقليل حجم المشروع** بنسبة 15-30%
- ✅ **تحسين سرعة البحث** في الملفات
- ✅ **إزالة التشويش** البصري في مستكشف الملفات  
- ✅ **تنظيم تلقائي** بدون تدخل يدوي
- ✅ **أمان 100%** - عدم حذف أي ملف مهم
- ✅ **شفافية كاملة** - تقارير تفصيلية لكل عملية

هذه المهارة تعمل في الخلفية وتحافظ على نظافة وتنظيم المشروع تلقائياً! 🧹✨
