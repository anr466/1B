# 🔍 تقرير التدقيق الجنائي البرمجي — Forensic Software Audit Report
# نظام التداول الآلي — Automated Trading System

**التاريخ**: 2026-02-13
**المدقق**: Senior Software Forensic Auditor (AI)
**المنهجية**: 9-Phase Forensic Scan (Context → Dead Code → Logic Gaps → State Conflicts → Race Conditions → Weak Protection → Data Flow → Duplication → Crash Points)
**نطاق الفحص**: Backend API (20 files) + Database Layer + Mobile App (34 screens) + State Machines + Data Flow

---

# 1️⃣ أخطاء مؤكدة (CRITICAL — تمنع الإنتاج)

---

## CRIT-01: `secure_actions_endpoints.py` — كتابة على اتصال قراءة (WRITE on READ connection)

**الملف**: `backend/api/secure_actions_endpoints.py:494`
**المشكلة**: `execute_secure_action()` يستخدم `db_manager.get_connection()` (قراءة فقط — بدون قفل) لتنفيذ:
- `UPDATE users` (تغيير اسم، إيميل، هاتف، كلمة مرور)
- `INSERT OR REPLACE INTO user_binance_keys` (حفظ مفاتيح)
- `DELETE FROM user_binance_keys` (حذف مفاتيح)

**الخطورة**: `get_connection()` لا يحتوي `_write_lock` ولا `BEGIN IMMEDIATE`. طلبان متزامنان يمكنهما إفساد البيانات. عمليات كتابة بدون Transaction safety.
**الإصلاح**: استبدال بـ `get_write_connection()`

---

## CRIT-02: `smart_exit_api.py` — كتابة على اتصال قراءة

**الملف**: `backend/api/smart_exit_api.py:133`
**المشكلة**: `update_smart_exit_settings()` يستخدم `db.get_connection()` لتنفيذ `UPDATE user_settings`
**الخطورة**: نفس CRIT-01 — كتابة بدون قفل
**الإصلاح**: استبدال بـ `get_write_connection()`

---

## CRIT-03: `system_endpoints.py` — كتابة مدمرة على اتصال قراءة

**الملف**: `backend/api/system_endpoints.py:125`
**المشكلة**: `reset_account_data()` يستخدم `db.get_connection()` لتنفيذ:
- `DELETE FROM user_trades`
- `DELETE FROM trades`
- `DELETE FROM active_positions`
- `UPDATE user_portfolios`
- `DELETE FROM user_settings`
- `DELETE FROM notifications`

**الخطورة**: **6 عمليات حذف مدمرة** على اتصال قراءة بدون Transaction safety. إذا فشلت العملية الرابعة، الأولى والثانية والثالثة تنفذت بالفعل ← بيانات غير متسقة.
**الإصلاح**: استبدال بـ `get_write_connection()`

---

## CRIT-04: `database_manager.py` — 7 دوال كتابة على اتصال قراءة

**الملف**: `database/database_manager.py`
**المشكلة**: الدوال التالية تستخدم `get_connection()` بدلاً من `get_write_connection()`:

| السطر | الدالة | العملية |
|-------|--------|---------|
| 579 | `update_system_status()` | UPDATE system_status |
| 1565 | `update_trading_settings()` | UPDATE user_settings |
| 1596 | `update_user_profile()` | UPDATE users |
| 1718 | `update_notification_preferences()` | UPDATE user_notification_settings |
| 1956 | `reset_user_portfolio()` | DELETE + INSERT (6+ جداول) |
| 2498 | `clear_email_verification()` | DELETE FROM verification_codes |
| 3048 | `delete_user_binance_keys()` | DELETE FROM user_binance_keys |

**الخطورة**: كل دالة عرضة لـ Race Condition. `reset_user_portfolio` أخطرها (عمليات حذف متعددة بدون قفل).
**الإصلاح**: استبدال كل `get_connection()` في دوال الكتابة بـ `get_write_connection()`

---

## CRIT-05: `smart_exit_api.py` — `require_auth` لا يتحقق من التوقيع

**الملف**: `backend/api/smart_exit_api.py:34-42`
**المشكلة**:
```python
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({...}), 401
        return f(*args, **kwargs)  # ← يمر بدون أي تحقق!
```
**الخطورة**: أي نص عشوائي كـ Bearer token يمنح وصول كامل. جميع endpoints في smart_exit_api غير محمية فعلياً:
- `GET /settings/<user_id>` — قراءة إعدادات أي مستخدم
- `PUT /settings/<user_id>` — تعديل إعدادات أي مستخدم
- `POST /check-exit/<user_id>/<symbol>` — فحص شروط إغلاق
- `GET /statistics/<user_id>` — إحصائيات أي مستخدم
- `GET /errors/<user_id>` — أخطاء أي مستخدم

**الإصلاح**: استخدام `verify_token()` من `token_refresh_endpoint.py`

---

## CRIT-06: `system_health.py` — `restart_system()` بدون أي مصادقة

**الملف**: `backend/api/system_health.py:220`
**المشكلة**: `restart_system()` ليس عليه أي decorator مصادقة (`@require_admin` أو `@require_auth`)
```python
@health_bp.route('/admin/system/restart', methods=['POST'])
def restart_system():  # ← NO AUTH!
    subprocess.run(['pkill', '-9', '-f', 'background_trading_manager.py'], ...)
    subprocess.Popen(["python3", "bin/background_trading_manager.py", "--start"], ...)
```
**الخطورة**: **أي شخص يمكنه إعادة تشغيل نظام التداول** بدون أي مصادقة. بالإضافة إلى ذلك، يتجاوز State Machine بالكامل.

**ملاحظة**: `health_bp` غير مسجل في `start_server.py` حالياً ← الخطر معلق لكن يصبح حرجاً فور التسجيل.

**الإصلاح**: إضافة `@require_admin` + استبدال subprocess بـ `TradingStateMachine.start()/stop()`

---

## CRIT-07: `smart_exit_api.py` — `SmartExitSystem` غير موجود

**الملف**: `backend/api/smart_exit_api.py:187,224`
**المشكلة**: Endpoints `check_exit_conditions` و `get_exit_statistics` تستدعي:
```python
smart_exit = SmartExitSystem(user_id)  # NameError — لم يتم import أو تعريف
```
**فقط** `get_intelligent_exit_system` مستورد في السطر 21، لكن لم يُستخدم.
**الخطورة**: هذان الـ Endpoints يُرجعان 500 دائماً.
**الإصلاح**: استبدال بـ `get_intelligent_exit_system()` أو حذف الـ endpoints الميتة.

---

## CRIT-08: `database_manager.py` — `reset_user_portfolio()` عمود مكرر

**الملف**: `database/database_manager.py:2010-2011`
**المشكلة**:
```sql
INSERT OR REPLACE INTO user_settings 
(user_id, trade_amount, max_positions, risk_level, stop_loss_pct, 
 take_profit_pct, trading_enabled, trading_enabled, max_trades, ...)
                       ^^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^  ← مكرر!
```
`trading_enabled` مكرر مرتين في قائمة الأعمدة ← SQLite سيرفض هذا الاستعلام بخطأ.
**الخطورة**: `reset_user_portfolio()` يفشل دائماً عند مرحلة إعادة ضبط الإعدادات.
**الإصلاح**: حذف العمود المكرر

---

## CRIT-09: `system_endpoints.py` — `reset_account_data` بدون فلتر is_demo

**الملف**: `backend/api/system_endpoints.py:125-155`
**المشكلة**: `reset_account_data()` يحذف **كل** بيانات المستخدم بدون تمييز demo/real:
```python
conn.execute("DELETE FROM user_trades WHERE user_id = ?", (user_id,))
conn.execute("DELETE FROM active_positions WHERE user_id = ?", (user_id,))
conn.execute("DELETE FROM user_settings WHERE user_id = ?", (user_id,))
```
**الخطورة**: إذا استدعاها أي مستخدم، تُمسح صفقاته الحقيقية مع التجريبية.
**الإصلاح**: إضافة `AND is_demo = 1` أو حذف هذا الـ endpoint (يوجد بديل أفضل في admin_unified_api)

---

## CRIT-10: `secure_actions_endpoints.py` — تضارب OTP (المستخدم يستلم كود مختلف)

**الملف**: `backend/api/secure_actions_endpoints.py:120-316`
**المشكلة**: تسلسل منطقي معطل:
1. **سطر 297**: يُولّد `otp_code = generate_otp()` ← كود محلي
2. **سطر 304**: يُخزن الكود المحلي في `pending_verifications[user_id][action]['otp'] = otp_code`
3. **سطر 316**: يستدعي `send_otp_email(target, otp_code, ...)` ← يمرر الكود المحلي
4. **سطر 125-126**: `send_otp_email()` تستدعي `otp_service.send_email_otp()` التي تولّد **كوداً خاصاً بها** وتُرسله للمستخدم
5. **سطر 388**: يُتحقق من `otp_code != pending['otp']` ← يقارن بالكود المحلي

**النتيجة**: المستخدم يستلم كود X من `otp_service`، لكن النظام يتوقع كود Y المحلي ← **التحقق يفشل دائماً عبر Email**.

**الاستثناء الوحيد**: إذا `otp_service` غير متاح ← يُخزن الكود المحلي في `otp_storage` (سطر 134) ← يعمل فقط في بيئة التطوير.

**الإصلاح**: استخدام `otp_service.verify_email_otp()` بدلاً من المقارنة اليدوية، أو تمرير الكود المحلي لـ `otp_service` بدلاً من توليد جديد.

---

# 2️⃣ أخطاء منطقية (HIGH)

---

## HIGH-01: `system_health.py` — `restart_system` يتجاوز State Machine

**الملف**: `backend/api/system_health.py:233-253`
**المشكلة**: يستخدم `pkill` و `subprocess.Popen` مباشرة بدون تحديث `trading_state` في DB.
**النتيجة**: DB يقول STOPPED بينما النظام يعمل فعلاً، أو DB يقول RUNNING بينما النظام متوقف.
**الخطورة**: آلية تحكم رابعة تتجاوز State Machine بالكامل.

---

## HIGH-02: `system_endpoints.py` — `reset_account_data` جدول خاطئ

**الملف**: `backend/api/system_endpoints.py:136-147`
**المشكلة**: `UPDATE user_portfolios SET ...` ← الجدول الفعلي اسمه `user_portfolios` (بحسب migration) لكن `update_user_balance()` في database_manager يستخدم `portfolio` و `user_portfolio` (بدون s).
**الخطورة**: الاستعلام قد يُحدّث جدولاً مختلفاً أو يفشل إذا الجدول غير موجود.

---

## HIGH-03: `database_manager.py` — `reset_user_portfolio` يحذف بدون فلتر is_demo

**الملف**: `database/database_manager.py:1956-2017`
**المشكلة**: `DELETE FROM user_trades WHERE user_id = ?` بدون `AND is_demo = 1`
**الخطورة**: إعادة ضبط الحساب التجريبي يمسح الصفقات الحقيقية أيضاً (نفس نمط CRIT-09).

---

## HIGH-04: `fcm_endpoints.py` — DELETE يسمح بحذف FCM token أي مستخدم

**الملف**: `backend/api/fcm_endpoints.py:134`
**المشكلة**: `user_id = data.get('user_id')` بدلاً من `g.user_id` من المصادقة
**الخطورة**: مستخدم مصادق يمكنه حذف FCM tokens أي مستخدم آخر ← تعطيل إشعاراته.
**الإصلاح**: `user_id = g.user_id`

---

## HIGH-05: `login_otp_endpoints.py` — تسريب `user_id` في الاستجابة

**الملف**: `backend/api/login_otp_endpoints.py:169`
**المشكلة**: `'user_id': user['id']` في استجابة `send-otp`
**الخطورة**: مهاجم يمكنه تعداد user IDs الصالحة عبر محاولات تسجيل دخول.

---

## HIGH-06: `smart_exit_api.py` — جداول غير موجودة

**الملف**: `backend/api/smart_exit_api.py:248-327`
**المشكلة**: الاستعلامات تقرأ من `smart_exit_stats` و `smart_exit_errors` — هذه الجداول غير موجودة في `database_manager.py` ولا في أي migration.
**الخطورة**: `get_detailed_statistics` و `get_exit_errors` يُرجعان 500 دائماً.

---

## HIGH-07: `trading_state_machine.py` — تسريب File Handles

**الملف**: `backend/core/trading_state_machine.py:584-585`
**المشكلة**:
```python
stdout_log = open(log_dir / 'trading_process_stdout.log', 'w')
stderr_log = open(log_dir / 'trading_process_stderr.log', 'w')
process = subprocess.Popen(..., stdout=stdout_log, stderr=stderr_log, ...)
# ← File handles NEVER closed!
```
**الخطورة**: كل start/stop cycle يسرب file handle واحد. بعد عشرات الدورات ← استنزاف file descriptors.
**الإصلاح**: حفظ المرجع وإغلاقه، أو استخدام `subprocess.DEVNULL`

---

# 3️⃣ أكواد ميتة (Dead Code)

---

## DEAD-01: `smart_exit_api.py` — endpoints ميتة بالكامل

- `check_exit_conditions()` — يستدعي `SmartExitSystem` غير موجود → 500 دائماً
- `get_exit_statistics()` — نفس السبب → 500 دائماً
- `get_detailed_statistics()` — يقرأ من `smart_exit_stats` غير موجود → 500 دائماً
- `get_exit_errors()` — يقرأ من `smart_exit_errors` غير موجود → 500 دائماً

**التصنيف**: ميت فعلياً (4 endpoints من أصل 6)

---

## DEAD-02: `trading_state_machine.py` — `_check_settings_configured()` غير مستخدم

**الملف**: `backend/core/trading_state_machine.py:526-541`
**التصنيف**: ميت فعلياً — لا يُستدعى من أي مكان (أُزيل من `start()` و `get_state()` سابقاً)

---

## DEAD-03: `system_health.py` — Blueprint غير مسجل

**الملف**: `backend/api/system_health.py` — `health_bp` غير مسجل في `start_server.py`
**التصنيف**: ميت فعلياً — جميع endpoints غير قابلة للوصول:
- `GET /admin/system/health`
- `GET /admin/system/critical-errors`
- `POST /admin/system/errors/<error_id>/resolve`
- `POST /admin/system/restart`

---

## DEAD-04: `secure_actions_endpoints.py` — `otp_storage` dict مزدوج

**الملف**: `backend/api/secure_actions_endpoints.py:95,118`
**المشكلة**: `pending_verifications` (سطر 95) و `otp_storage` (سطر 118) — نظامان مختلفان يُخزنان OTP.
`otp_storage` يُكتب في `send_otp_email` fallback لكن لا يُقرأ أبداً في `verify_and_execute`.
**التصنيف**: ميت فعلياً

---

## DEAD-05: 17 ملف غير مستورد في الإنتاج (موثق سابقاً)

الملفات في `backend/core/`, `backend/strategies/`, `backend/services/`, `backend/selection/` — مفصلة في التقرير السابق.

---

# 4️⃣ فجوات معمارية (Architecture Gaps)

---

## ARCH-01: آليات تحكم متعددة

| المسار | الآلية | الحالة |
|--------|--------|--------|
| `/admin/trading/start\|stop` | TradingStateMachine ✅ | نشط — المصدر الوحيد |
| `/admin/background/start\|stop` | background_control.py | مُلغى → 410 Gone ✅ |
| `/admin/trading/group-b/start\|stop` | admin_unified_api.py | مُلغى → 410 Gone ✅ |
| `/admin/system/restart` | system_health.py | **غير مسجل لكن موجود** ⚠️ |
| `system_fast_api.py` | UnifiedSystemManager | **نشط — يتجاوز State Machine** ⚠️ |

**الفجوة**: `system_fast_api.py` لا يزال يحتوي آلية start/stop مستقلة عبر `UnifiedSystemManager` — لم تُلغى بعد.

---

## ARCH-02: `pending_verifications` — تخزين OTP في الذاكرة

**الملف**: `backend/api/secure_actions_endpoints.py:95`
**المشكلة**: `pending_verifications = {}` في ذاكرة العملية
- **يُفقد عند إعادة التشغيل** — أي OTP معلق يضيع
- **لا يُشارك بين Workers** — إذا استخدم Flask أكثر من worker
- **لا ينظف نفسه** — OTPs منتهية الصلاحية تبقى في الذاكرة للأبد

---

## ARCH-03: تكرار `require_auth` في 5+ ملفات

كل ملف API يُعرّف `require_auth` بطريقة مختلفة:

| الملف | التحقق الفعلي |
|-------|--------------|
| `trading_control_api.py` | `require_admin` (صحيح) |
| `smart_exit_api.py` | لا تحقق! فقط token موجود |
| `fcm_endpoints.py` | `verify_token()` (صحيح) |
| `system_endpoints.py` | `JWTManager.verify_token()` (مختلف) |
| `secure_actions_endpoints.py` | JWT decode يدوي + fallback |
| `login_otp_endpoints.py` | لا يحتاج (عام) |

**الخطورة**: لا يوجد middleware موحد — كل ملف يمكن أن ينسى التحقق أو يستخدم طريقة مختلفة.

---

## ARCH-04: 3 جداول محفظة غير متسقة

- `portfolio` — يُستخدم في `reset_user_portfolio()`, `update_user_balance()`
- `user_portfolio` — يُستخدم في `update_user_balance()`
- `user_portfolios` — يُستخدم في `system_endpoints.py:reset_account_data()`

**لا يوجد مصدر حقيقة واحد للرصيد.** `update_user_balance()` يُحدّث `portfolio` + `user_portfolio`، لكن `reset_account_data()` يُحدّث `user_portfolios`.

---

# 5️⃣ احتمالات انهيار (Crash Points)

---

## CRASH-01: إعادة تشغيل مفاجئة + صفقات مفتوحة

**السيناريو**: السعر يتجاوز SL أثناء توقف النظام
**الحماية**: ✅ تم إضافة SL breach check في `_manage_position()` (FIX-6 سابق)
**الفجوة المتبقية**: لا يوجد timeout على فترة التوقف — إذا توقف النظام يوماً كاملاً، الصفقات تبقى مفتوحة بدون حماية.

---

## CRASH-02: ضغط متكرر على Start/Stop

**الحماية**: ✅ State Machine يمنع Double-start/Double-stop (يُرجع الحالة الحالية بدون خطأ)
**الحالة**: آمن

---

## CRASH-03: فشل DB أثناء إغلاق صفقة

**السيناريو**: `close_position()` → تُحدث `active_positions` → تفشل `INSERT INTO user_trades`
**الحماية**: ✅ يستخدم `get_write_connection()` مع `BEGIN IMMEDIATE` — عند الفشل يُعمل rollback
**الحالة**: آمن

---

## CRASH-04: فقدان اتصال الشبكة أثناء التداول الحقيقي

**السيناريو**: أمر شراء يُرسل لـ Binance → انقطاع شبكة → لا نعرف إذا نُفذ
**الحماية**: ❌ لا يوجد نظام تحقق من تنفيذ الأوامر (order reconciliation)
**الخطورة**: يمكن أن يُخصم الرصيد في DB بدون تنفيذ فعلي على Binance، أو العكس.

---

## CRASH-05: DB locked أثناء كتابة متعددة

**السيناريو**: `get_connection()` (7 دوال كتابة من CRIT-04) + `get_write_connection()` يكتبان معاً
**الحماية**: ❌ `get_connection()` لا يحتوي قفل ← `SQLITE_BUSY` errors ممكنة
**الخطورة**: بيانات قد لا تُحفظ بصمت (WAL mode يساعد لكن لا يضمن)

---

# 6️⃣ سوء تنظيم (Code Organization Issues)

---

## ORG-01: `admin_unified_api.py` — God Object

**الحجم**: ~1000+ سطر — يحتوي إدارة مستخدمين + إحصائيات + تحكم تداول + إعادة ضبط + صفقات نشطة + إشعارات
**الخطورة**: صعوبة صيانة، سهولة إدخال أخطاء

---

## ORG-02: `mobile_endpoints.py` — God Object

**الحجم**: ~3900+ سطر — يحتوي كل endpoints المستخدم العادي
**الخطورة**: نفس ORG-01

---

## ORG-03: `database_manager.py` — God Object

**الحجم**: 3555 سطر — يحتوي كل عمليات DB من إنشاء جداول إلى إغلاق صفقات
**الخطورة**: مستحيل اختباره بشكل منفصل

---

## ORG-04: تشفير كلمات المرور بـ SHA-256 بدون salt

**الملفات**: `secure_actions_endpoints.py:110-115`, `login_otp_endpoints.py:87`
```python
hashed = hashlib.sha256(password.encode()).hexdigest()
```
**الخطورة**: Rainbow table attacks — كل كلمتي مرور متشابهتين لهما نفس الـ hash. لا يوجد salt أو bcrypt.

---

# 7️⃣ توصيات تصحيح واضحة ومباشرة

---

## الأولوية القصوى (يجب إصلاحها قبل الإنتاج):

| # | الإصلاح | الملف | التعقيد |
|---|---------|-------|---------|
| 1 | استبدال `get_connection()` بـ `get_write_connection()` في 7 دوال DB | `database_manager.py` | منخفض |
| 2 | استبدال `get_connection()` بـ `get_write_connection()` في 3 ملفات API | `secure_actions_endpoints.py`, `smart_exit_api.py`, `system_endpoints.py` | منخفض |
| 3 | إصلاح `require_auth` في `smart_exit_api.py` ← تحقق فعلي من JWT | `smart_exit_api.py` | منخفض |
| 4 | إصلاح تضارب OTP في `secure_actions_endpoints.py` | `secure_actions_endpoints.py` | متوسط |
| 5 | حذف العمود المكرر `trading_enabled` في `reset_user_portfolio` | `database_manager.py:2011` | منخفض |
| 6 | إضافة `AND is_demo=1` في `reset_user_portfolio` و `reset_account_data` | `database_manager.py`, `system_endpoints.py` | منخفض |
| 7 | إصلاح أو حذف `SmartExitSystem` references | `smart_exit_api.py` | منخفض |
| 8 | إضافة `@require_admin` لـ `restart_system` أو حذفه | `system_health.py` | منخفض |
| 9 | استخدام `g.user_id` بدلاً من `data.get('user_id')` في FCM DELETE | `fcm_endpoints.py` | منخفض |
| 10 | إغلاق file handles في `_start_process` | `trading_state_machine.py` | منخفض |

## الأولوية العالية (إصلاح قبل التوسع):

| # | الإصلاح | التعقيد |
|---|---------|---------|
| 11 | توحيد `require_auth` في middleware واحد | متوسط |
| 12 | نقل `pending_verifications` من ذاكرة → DB | متوسط |
| 13 | توحيد جداول المحفظة (portfolio / user_portfolio / user_portfolios) | عالي |
| 14 | ترقية SHA-256 إلى bcrypt | متوسط |
| 15 | إضافة order reconciliation لتداول Binance الحقيقي | عالي |

---

## ملخص إحصائي

| الفئة | العدد |
|-------|-------|
| أخطاء مؤكدة (CRITICAL) | 10 |
| أخطاء منطقية (HIGH) | 7 |
| أكواد ميتة | 5 فئات (20+ عنصر) |
| فجوات معمارية | 4 |
| احتمالات انهيار | 5 (2 محمية ✅, 3 غير محمية ❌) |
| سوء تنظيم | 4 |
| **توصيات تصحيح** | **15** |

---

**الخلاصة**: النظام يحتوي **10 أخطاء حرجة** تمنع الإطلاق للإنتاج بأمان. أخطرها: كتابة قاعدة البيانات بدون قفل (7 دوال + 3 ملفات API)، وتحقق أمني وهمي في smart_exit_api، وتضارب OTP يمنع تغيير كلمة المرور/الإيميل.

---

# 8️⃣ الإصلاحات المطبقة (Applied Fixes)

## ✅ إصلاحات هذه الجلسة (13 إصلاح)

| # | المعرف | الإصلاح | الملف |
|---|--------|---------|-------|
| 1 | CRIT-01 | `execute_secure_action()`: `get_connection()` → `get_write_connection()` + إزالة `conn.commit()` يدوي (9 عمليات كتابة) | `secure_actions_endpoints.py` |
| 2 | CRIT-02 | `update_smart_exit_settings()`: `get_connection()` → `get_write_connection()` | `smart_exit_api.py` |
| 3 | CRIT-03 | `reset_account_data()`: `get_connection()` → `get_write_connection()` | `system_endpoints.py` |
| 4 | CRIT-04 | 7 دوال DB: `get_connection()` → `get_write_connection()` (`update_system_status`, `update_trading_settings`, `update_user_profile`, `update_notification_preferences`, `reset_user_portfolio`, `clear_email_verification`, `delete_user_binance_keys`) | `database_manager.py` |
| 5 | CRIT-05 | `require_auth` الآن يتحقق فعلياً من JWT عبر `verify_token()` بدلاً من فحص وجود token فقط | `smart_exit_api.py` |
| 6 | CRIT-06 | `restart_system()` مُعطل → 410 Gone (كان بدون مصادقة ويتجاوز State Machine) | `system_health.py` |
| 7 | CRIT-07 | `SmartExitSystem` (غير موجود) → `get_intelligent_exit_system()` | `smart_exit_api.py` |
| 8 | CRIT-08 | عمود `trading_enabled` المكرر محذوف من INSERT في `reset_user_portfolio` | `database_manager.py` |
| 9 | CRIT-09 | `reset_account_data`: إضافة `AND is_demo = 1` لمنع مسح الحساب الحقيقي + إزالة حذف `user_settings` و `trades` | `system_endpoints.py` |
| 10 | CRIT-10 | تضارب OTP: `send_otp_email` الآن يُرجع `(success, actual_code)` + الكود الفعلي يُحدّث في `pending_verifications` | `secure_actions_endpoints.py` |
| 11 | HIGH-03 | `reset_user_portfolio`: إضافة `AND is_demo = 1` لـ `DELETE FROM user_trades` و `user_binance_orders` | `database_manager.py` |
| 12 | HIGH-04 | FCM DELETE: `data.get('user_id')` → `g.user_id` لمنع حذف tokens مستخدمين آخرين | `fcm_endpoints.py` |
| 13 | HIGH-07 | تسريب File Handles: إضافة `_close_log_handles()` يُستدعى عند `_stop_all_processes()` | `trading_state_machine.py` |

## 📁 الملفات المعدلة (7 ملفات)

| الملف | عدد الإصلاحات |
|-------|--------------|
| `database/database_manager.py` | 9 (7 write connections + duplicate column + is_demo filter) |
| `backend/api/secure_actions_endpoints.py` | 2 (write connection + OTP conflict) |
| `backend/api/smart_exit_api.py` | 3 (auth + write connection + SmartExitSystem) |
| `backend/api/system_endpoints.py` | 2 (write connection + is_demo filter) |
| `backend/api/system_health.py` | 1 (restart neutralized) |
| `backend/api/fcm_endpoints.py` | 1 (user_id from auth) |
| `backend/core/trading_state_machine.py` | 1 (file handle leak) |

## ⚠️ مسائل موثقة لم تُعالج (تحتاج قراراً معمارياً)

| المسألة | السبب |
|---------|-------|
| ARCH-02: `pending_verifications` في الذاكرة | نقل إلى DB يحتاج إعادة تصميم OTP flow |
| ARCH-03: تكرار `require_auth` في 5+ ملفات | توحيد يحتاج middleware مركزي |
| ARCH-04: 3 جداول محفظة متضاربة | توحيد يحتاج migration + تعديل كل الاستعلامات |
| ORG-04: SHA-256 بدون salt | ترقية إلى bcrypt يحتاج migration لكل كلمات المرور |
| CRASH-04: لا يوجد order reconciliation | يحتاج بناء نظام تحقق من تنفيذ أوامر Binance |
| HIGH-05: تسريب user_id في login OTP | حذف `user_id` من الاستجابة يحتاج تعديل frontend |
| HIGH-06: جداول `smart_exit_stats`/`smart_exit_errors` غير موجودة | إنشاء migration أو حذف endpoints |
