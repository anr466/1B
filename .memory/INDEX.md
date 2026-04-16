# Project Memory Index — فهرس الذاكرة

> **آخر تحديث:** 2026-04-14 (تصحيح البنية: Docker Unified Architecture)
> **المشروع:** Trading AI Bot — نظام تداول آلي متعدد الاستراتيجيات
> **بيئة التشغيل:** Docker Compose (Microservices) — **لا تشغيل محلي (Local)**

---

## 🏗️ البنية التحتية الموحدة (Docker Architecture)

النظام يعمل كحزمة واحدة متكاملة عبر `docker-compose.yml`:

| الخدمة (Service) | الوصف | الملف | المنفذ |
|------------------|-------|-------|--------|
| **api** | الخادم الموحد (FastAPI + Flask) | `start_server.py` | 3002 |
| **scanner** | عامل فحص السوق | `bin/scanner_worker.py` | - |
| **executor** | عامل تنفيذ الصفقات | `bin/executor_worker.py` | - |
| **postgres** | قاعدة البيانات (PostgreSQL 16) | `docker-entrypoint-initdb.d` | 5432 |
| **nginx** | Reverse Proxy | `docker/nginx/default.conf` | 80 |

### 🔑 قواعد البيانات والاتصال
- **المضيف:** `postgres` (داخل الشبكة الداخلية لـ Docker).
- **التهيئة:** يتم إنشاء الجداول تلقائياً عند أول تشغيل عبر `database/postgres_schema.sql`.
- **الصلاحيات:** يديرها Docker تلقائياً (`trading_user` / `trading_ai_bot`).
- **تحذير:** ❌ **ممنوع** استخدام `psql` محلياً أو تعديل `.env` للإشارة لـ `127.0.0.1`.

### 📦 المكتبات (Requirements)
- **الأساسية:** FastAPI, Flask, psycopg2-binary, python-binance.
- **التحليل:** pandas, numpy, scikit-learn, xgboost.
- **ملاحظة:** `pandas-ta` موجود في `requirements.txt` (v0.4.71b0).

---

## 📱 التطبيق (Flutter)
- **الاتصال:** يتصل بـ `http://<LOCAL_IP>:3002` أو `http://10.0.2.2:3002` (Emulator).
- **المصادقة:** JWT Bearer Token.
- **التكامل:** يتطابق تماماً مع مسارات `start_server.py` و Blueprints.

---

## 🧠 حالة النظام الحالية
| المكون | الحالة | الملاحظات |
|--------|--------|-----------|
| **Backend Logic** | ✅ **سليم** | الكود منطقي ومتكامل. |
| **Database Schema** | ✅ **سليم** | `postgres_schema.sql` شامل. |
| **Docker Setup** | ✅ **جاهز** | `docker-compose.yml` موحد وصحيح. |
| **Flutter App** | ✅ **متطابق** | المسارات والنماذج متوافقة. |
| **التشغيل المحلي** | ❌ **مرفوض** | النظام مصمم للعمل عبر Docker فقط. |

---

## إحصائيات المشروع الفعلية

| المكون | عدد الملفات |
|--------|------------|
| Backend Python | 109 ملف (بعد حذف unified_trading_engine.py) |
| Flutter Dart | 100 ملف |
| Database SQL | 16 ملف (schema + 15 migration) |
| Database Python | 5 ملفات |
| **الإجمالي** | **230 ملف** |

---

## البيئة الافتراضية

| العنصر | القيمة |
|--------|--------|
| Python | 3.13.7 |
| Virtual Env | `.venv/` (موجود ومفعّل) |
| Requirements | `requirements.txt` + `requirements-frozen.txt` (116 حزمة) |
| Setup Script | `setup.sh` (يعمل على Linux/macOS) |
| حالة التثبيت | ✅ 44/44 وحدة تعمل بنجاح |

---

## حالة النظام (2026-04-14 — محرك النمو الذكي)

| المكون | الحالة | الوصف |
|--------|--------|-------|
| **Smart Risk Manager** | ✅ **نشط** | أوضاع ديناميكية (Launch/Growth/Standard/Pro) |
| **Autonomous Learning** | ✅ **نشط** | يحفظ الأداء في `data/risk_learning_state.json` |
| **Unified Orchestrator** | ✅ **نشط** | محرك تداول واحد (TradingOrchestrator) |
| **Exit Manager** | ✅ **نشط** | LONG + SHORT متساويان |
| **Coin Analyzer** | ✅ **نشط** | 3 confirmations + divergence |
| **Database Schema** | ✅ **محدث** | يدعم Growth Modes + SHORT positions |
| **Flutter App** | ✅ **جاهز** | واجهة كاملة (22 شاشة + 7 skins) |

### أوضاع النمو (Growth Modes)
| الوضع | الرصيد | المخاطرة | الهدف |
|-------|--------|---------|-------|
| 🚀 Launch | <$100 | 20% | كسر حاجز $10 |
| 📈 Growth | $100-$1k | 10% | نمو متوازن |
| ⚖️ Standard | $1k-$10k | 5% | حماية رأس المال |
| 🛡️ Pro | >$10k | 2% | استقرار طويل الأمد |
| 5. إرجاع | أعلى N عملة + majors دائماً |

### التحسينات المنفذة
| التحسين | الوصف |
|---------|-------|
| ✅ CoinStateAnalyzer | 3 confirmations (4H+MACD+Volume) + divergence detection + bb_position |
| ✅ CognitiveDecisionMatrix | regime-aware weights + signal_quality + ensemble bonus |
| ✅ MTFConfirmation | volume confirmation (15m+5m) |
| ✅ Migration 004 | إضافة عمود `growth_mode` لجدول `portfolio` |
| ✅ Migration 005 | تصحيح نوع `entry_date` إلى TIMESTAMPTZ |
| ✅ verify_integration.py | سكربت تحقق من تكامل DB + Backend + Flutter (نجح 100%) |
| ✅ growth_mode DB sync | `update_growth_mode_in_db()` يحفظ الوضع في قاعدة البيانات |
| ✅ تنظيف Flutter | حذف 3 widgets غير مستخدمة (section_header, context_feedback, gradient_background) |
| ✅ database_config.json | تحديث ليعكس PostgreSQL بدلاً من SQLite القديم |
| ✅ ExitManager | evaluate_positions method + SHORT support كامل |
| ✅ TradingOrchestrator | ensemble scoring + multi-factor confirmation + ExitManager |
| ✅ PositionManager | TOCTOU مزدوج + available_balance موحد |
| ✅ إصلاح التشفير | إضافة استيراد `encrypt_binance_keys` المفقود في `mobile_settings_routes.py` |
| ✅ إصلاح OTP | استخدام `CURRENT_TIMESTAMP` في `simple_email_otp_service.py` |
| ✅ تفعيل Growth Mode | استدعاء `update_growth_mode_in_db` في `TradingOrchestrator.run_cycle` |

---

## كتل الذاكرة المتاحة

| الكتلة | الملف | الوصف |
|--------|-------|-------|
| `trading_engine` | `.memory/trading_engine.md` | 14 وحدة backend — 110 ملف Python |
| `database_schema` | `.memory/database_schema.md` | 27 جدول + 24 فهرس + 14 migration |
| `flutter_ui` | `.memory/flutter_ui.md` | 100 ملف Dart — 22 شاشة — 7 skins |

---

## البنية الفعلية المختصرة

### Backend (14 وحدة)
```
backend/
├── core/          (26) — المحرك الأساسي
├── strategies/    (18) — الاستراتيجيات
├── api/           (31) — واجهة API
├── ml/            (15) — التعلم الآلي
├── cognitive/     (3)  — النظام المعرفي
├── analysis/      (5)  — التحليل
├── learning/      (2)  — التعلم التكيفي
├── monitoring/    (3)  — المراقبة
├── risk/          (3)  — إدارة المخاطر
├── selection/     (2)  — الاختيار
├── services/      (4)  — الخدمات
├── utils/         (24) — الأدوات المساعدة
├── infrastructure/(1)  — البنية التحتية
└── schedulers/    (1)  — المجدولات
```

### Flutter (100 ملف)
```
flutter_trading_app/lib/
├── main.dart, app.dart
├── navigation/    (3)  — GoRouter + MainShell
├── core/
│   ├── models/    (8)  — النماذج
│   ├── providers/ (7)  — Riverpod
│   ├── repositories/ (5) — المستودعات
│   ├── services/  (10) — الخدمات
│   └── constants/ (4)  — الثوابت
├── design/        (50) — نظام التصميم + 7 skins
└── features/      (22) — الشاشات
    ├── auth/      (7)
    ├── dashboard/ (1)
    ├── portfolio/ (1)
    ├── trades/    (2)
    ├── analytics/ (1)
    ├── profile/   (1)
    ├── settings/  (4)
    ├── notifications/ (2)
    ├── onboarding/ (1)
    └── admin/     (5)
```

### Database
```
database/
├── database_manager.py  (1566 سطر — 4 Mixins)
├── db_trading_mixin.py
├── db_users_mixin.py
├── db_portfolio_mixin.py
├── db_notifications_mixin.py
├── postgres_schema.sql  (487 سطر — 27 جدول)
├── database_config.json
└── migrations/          (14 ملف SQL)
```

---

## كيفية الاستخدام

### في بداية كل جلسة:
```
اقرأ جميع كتل الذاكرة في هذا المشروع، ثم تابع من حيث توقفنا.
```

### للبحث عن معلومة محددة:
```
اقرأ ملف .memory/trading_engine.md للبحث عن معلومات محرك التداول.
اقرأ ملف .memory/database_schema.md للبحث عن معلومات قاعدة البيانات.
اقرأ ملف .memory/flutter_ui.md للبحث عن معلومات واجهة المستخدم.
```

---

## البروتوكول المطبق

هذا المشروع يتبع **REASONING PROTOCOL — CORE v6.0** المحدد في `AGENTS.md`:
1. UNDERSTAND — الفهم العميق
2. ASSESS — التقييم واتخاذ القرار
3. PLAN — التخطيط الذكي
4. EXECUTE — التنفيذ الذاتي المتواصل
5. VERIFY — التحقق الشامل
6. REPORT — الإبلاغ عن الأثر

---

## القواعد الذهبية للنظام

1. **Single Source of Truth:** كل البيانات من PostgreSQL
2. **عزل المستخدمين:** كل مستخدم له بيانات منفصلة (user_id)
3. **قاعدة التفعيل/الإيقاف:** المستخدم المعطل لا تفتح له صفقات
4. **Demo/Live Separation:** حساب تجريبي وحقيقي منفصلان
5. **4-Phase System:** Backtest → Paper → Validation → Live
6. **ML-Enhanced Decisions:** قرارات التداول مدعومة بـ ML

---

## التقنيات الفعلية

| الطبقة | التقنية |
|--------|---------|
| Backend | Python 3 |
| Database | PostgreSQL (psycopg2) |
| Mobile | Flutter (Dart) |
| State Management | Riverpod |
| Navigation | GoRouter |
| Exchange | Binance API |
| Notifications | Firebase Cloud Messaging |
| UI Theming | Skin System (7 ثيمات) |
| Localization | Arabic (RTL) |
| Deployment | Docker + PM2 |
