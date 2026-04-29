# Memory Strategy — Trading AI Bot

## Session Continuity
عند بدء جلسة جديدة، اقرأ:
1. `AGENTS.md` — قواعد المشروع
2. `opencode.json` — إعدادات السلوك
3. `.opencode/memory/session_brief.md` — آخر ملخص جلسة (إن وجد)

## ما يجب حفظه بين الجلسات
احفظ في `.opencode/memory/session_brief.md` عند انتهاء الجلسة:
- **ما تم إنجازه**: الملفات التي تم تعديلها، الميزات المضافة، الإصلاحات
- **قرارات معمارية**: أي قرار مهم تم اتخاذه مع التبرير
- **مشاكل مفتوحة**: الأخطاء المعروفة، المهام المعلقة
- **حالة الأنظمة**: حالة trading_state، Group B، cognitive cycle

## Never Forget (Critical State)
- `dual_mode_router.py` — هل النظام في وضع Real أم Demo حالياً؟
- `trading_state_machine` — ما هي حالة التداول الحالية (RUNNING/STOPPED/ERROR)؟
- `start_server.py` — غير موجود بعد، يجب إنشاؤه قبل النشر
- `bin/telegram_external_watchdog.py` — غير موجود بعد، يجب إنشاؤه قبل النشر
- حالة الاختبارات: ملف اختبار واحد فقط — أي تغيير يحتاج تغطية

## Project Hotspots (Files That Break Everything)
1. `backend/strategies/base_strategy.py` — لا تلمسها أبداً
2. `config/unified_settings.py` — مصدر الإعدادات الوحيد
3. `backend/core/dual_mode_router.py` — يتحكم في وضع Real/Demo
4. `database/database_manager.py` — God Object، كل شيء يمر من هنا
5. `flutter_trading_app/lib/navigation/app_router.dart` — ShellRoute، لا تضيف Scaffold
6. `database/migrations/` — لا تعدل الملفات الموجودة

## File Age Awareness
- `database/migrations/` — 22 ملف، أقدمها قديم جداً
- `tests/` — ملف اختبار واحد فقط
- `runtime/logs/` — لا تحذف أبداً
- PM2 config — يشير لملفات غير موجودة
