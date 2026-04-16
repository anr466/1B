# Trading Engine — نظام التداول الخلفي (Docker Microservices)

> **مبني على الملفات الفعلية الموجودة في `backend/` و `bin/` فقط.**
> **آخر تحديث:** 2026-04-14 — تصحيح البنية: Docker Microservices + Queue-Based Execution

## نظرة عامة
نظام تداول آلي يعمل كحزمة **Docker Microservices** متكاملة. يعتمد على طابور إشارات (`signals_queue`) للفصل بين التحليل (Scanner) والتنفيذ (Executor).

---

## 🏗️ البنية التحتية (Docker Services)

| الخدمة | الملف | الوظيفة |
|--------|------|---------|
| **api** | `start_server.py` | الخادم الموحد (FastAPI + Flask) — واجهة التطبيق |
| **scanner** | `bin/scanner_worker.py` | فحص السوق، تحليل العملات، وتوليد الإشارات |
| **executor** | `bin/executor_worker.py` | قراءة الإشارات، التنفيذ على Binance، والمراقبة |
| **postgres** | `database/postgres_schema.sql` | قاعدة البيانات الموحدة (PostgreSQL 16) |
| **nginx** | `docker/nginx/default.conf` | Reverse Proxy وتوجيه الطلبات |

---

## 🔄 تدفق البيانات (Data Flow)

1.  **Scanner Worker**:
    *   يجلب بيانات السوق (Binance API).
    *   يحلل العملات (`CoinStateAnalyzer` + `Modules`).
    *   يولد إشارات ويحفظها في جدول `signals_queue`.
2.  **Executor Worker**:
    *   يقرأ الإشارات المعلقة (`PENDING`) من `signals_queue`.
    *   يتحقق من إعدادات المستخدم (Risks, Max Positions).
    *   ينفذ الصفقة على Binance (أو محاكاة Demo).
    *   يسجل الصفقة في `active_positions` ويحدث حالة الإشارة إلى `FILLED`.
3.  **Monitor Loop (داخل Executor)**:
    *   يراقب الأسعار الحية للمراكز المفتوحة.
    *   يغلق الصفقة عند ضرب SL/TP.
    *   ينقل البيانات إلى `user_trades` ويحدث `portfolio`.
4.  **API (FastAPI/Flask)**:
    *   يقرأ من `active_positions` و `user_trades` و `portfolio`.
    *   يعرض البيانات لتطبيق Flutter.

---

## 🗄️ الجداول الحرجة (Critical Tables)

| الجدول | الوظيفة |
|--------|---------|
| `signals_queue` | طابور الإشارات بين Scanner و Executor |
| `active_positions` | المراكز المفتوحة حالياً |
| `user_trades` | سجل الصفقات المغلقة |
| `portfolio` | أرصدة المستخدمين (Demo/Real) |
| `user_settings` | إعدادات التداول لكل مستخدم |

---

## ✅ الإصلاحات الهيكلية المنفذة

| الإصلاح | الوصف |
|---------|-------|
| ✅ إضافة `signals_queue` | تم إنشاء الجدول المفقود في `postgres_schema.sql` |
| ✅ إصلاح `executor_worker.py` | استخدام `user_trades` بدلاً من `trading_history` المفقود |
| ✅ تمرير `is_demo` | ضمان عزل البيانات بين Demo و Real في التنفيذ |
| ✅ توحيد `.env` | استضافة قاعدة البيانات إلى `postgres` (Docker Network) |
| ✅ إصلاح `start_server.py` | إضافة `request: Request` لـ Rate Limiting |
