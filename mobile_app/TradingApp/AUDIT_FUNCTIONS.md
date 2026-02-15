# 🔍 App Function Audit Map
## كل شاشة ← كل وظيفة ← حالة الفحص

## 🐛 Bugs Found & Fixed (11 total)
| # | Bug | Severity | File | Fix |
|---|-----|----------|------|-----|
| 1 | Duplicate `/portfolio/<user_id>` route override — wrong data source | **CRITICAL** | `mobile_endpoints.py:3673` | Removed duplicate that read from `user_binance_balance` instead of `portfolio` |
| 2 | `jsonify(success_response(...))` returns `[dict,200]` array | **HIGH** | `mobile_endpoints.py:2864,2953` | Unpack tuple before jsonify |
| 3 | Missing `initialBalance` in portfolio response → PnL badge broken | **MEDIUM** | `mobile_endpoints.py:347` | Added DB query for `initial_balance` |
| 4 | Missing `investedBalance` + `totalPnLPercentage` in portfolio | **MEDIUM** | `mobile_endpoints.py:372` | Added both fields to response |
| 5 | ProfileScreen `phone_number` vs `phoneNumber` mismatch | **LOW** | `ProfileScreen.js:43,106` | Handle both snake_case and camelCase |
| 6 | Notification settings PUT/GET used wrong DB schema (individual cols vs `settings_data` JSON) | **HIGH** | `mobile_endpoints.py:2151-2248` | Rewrote to use `settings_data` JSON column |
| 7 | CreateUser used wrong column names (`full_name`→`name`, `phone`→`phone_number`) | **HIGH** | `admin_unified_api.py:2652` | Fixed column names to match actual schema |
| 8 | CreateUser `db.hash_password()` — method doesn't exist on DatabaseManager | **HIGH** | `admin_unified_api.py:2659` | Use `hashlib.sha256()` directly + added import |
| 9 | Portfolio API returns ALL numeric fields as strings (`"1000.00"`) | **HIGH** | `mobile_endpoints.py:368-377` | Changed to `round(float, 2)` — proper numbers |
| 10 | `totalPnL` / `totalPnLPercentage` could use stale DB values | **MEDIUM** | `mobile_endpoints.py:361-362` | Recalculate from `totalBalance - initialBalance` always |
| 11 | Delete account 500 when called without body | **LOW** | `auth_endpoints.py:2238` | `request.get_json()` → `request.get_json(silent=True)` |

## ✅ Verification Results: 25/25 Endpoints Pass
| Category | Endpoints | Status |
|----------|-----------|--------|
| Portfolio (11 fields) | GET `/portfolio/1` | ✅ |
| Stats | GET `/stats/1` | ✅ |
| Active Positions | GET `/active-positions/1` | ✅ |
| Trades | GET `/trades/1` | ✅ |
| Profile | GET `/profile/1` | ✅ |
| Settings GET+PUT | round-trip verified | ✅ |
| Charts (5) | portfolio-growth, admin-demo-growth, distribution, daily-pnl, favorites | ✅ |
| Binance Keys | GET `/binance-keys/1` | ✅ |
| Notifications GET+PUT | round-trip verified | ✅ |
| Auth OTP | send-change-email-otp | ✅ |
| Admin (6) | trading/state, users/all, errors, errors/stats, system/status, demo/reset | ✅ |

## ✅ Data Interconnection Verified
- Mode switch → `changeTradingMode()` → increments `refreshCounter` → all screens re-fetch ✅
- `PortfolioContext` listens to `refreshCounter` and re-fetches via `DatabaseApiService.getPortfolio()` ✅
- Central auto-refresh every 60s via `TradingModeContext` ✅
- App foreground resume triggers refresh ✅

---

## 1️⃣ شاشة الرئيسية (DashboardScreen)
| # | الوظيفة | الاتصال (API) | الحالة |
|---|---------|---------------|--------|
| D1 | عرض الرصيد الإجمالي | `getPortfolio()` → `/api/user/portfolio/<id>` | ✅ |
| D2 | شارت نمو المحفظة (PortfolioChart) | `portfolio-growth/<id>` | ✅ |
| D3 | نسبة التغير (PnL Badge) | محسوبة من initialBalance vs currentBalance | ✅ |
| D4 | بطاقة الصفقات المفتوحة (ActivePositionsCard) | `getActivePositions()` → `/api/user/active-positions/<id>` | ✅ |
| D5 | إحصائيات الأداء العام (إجمالي الربح + معدل النجاح) | `getStats()` → `/api/user/stats/<id>` | ✅ |
| D6 | زر الإشعارات → NotificationsScreen | Navigation only | ✅ |
| D7 | زر الإعدادات → ProfileScreen | Navigation only | ✅ |
| D8 | زر الإعدادات في بطاقة المساعدة → Settings | Navigation only | ✅ |
| D9 | زر سجل التداول في بطاقة المساعدة → TradeHistory | Navigation only | ✅ |
| D10 | Pull-to-Refresh | يعيد تحميل كل البيانات | ✅ |
| D11 | AdminModeBanner (للأدمن) | يعرض وضع التداول الحالي | ✅ |
| D12 | تبديل Demo/Real (للأدمن) | `changeTradingMode()` → Context | ✅ |

## 2️⃣ شاشة المحفظة (PortfolioScreen)
| # | الوظيفة | الاتصال (API) | الحالة |
|---|---------|---------------|--------|
| P1 | عرض الرصيد ($) + نسبة التغير | `fetchPortfolio()` → PortfolioContext | ✅ |
| P2 | شارت نمو المحفظة | PortfolioChart component | ✅ |
| P3 | قائمة الأصول (Assets) | من بيانات المحفظة | ✅ |
| P4 | شارت توزيع الرصيد (Pie) | PortfolioDistributionChart | ✅ |
| P5 | Pull-to-Refresh | يعيد fetchPortfolio() | ✅ |

## 3️⃣ شاشة سجل الصفقات (TradeHistoryScreen)
| # | الوظيفة | الاتصال (API) | الحالة |
|---|---------|---------------|--------|
| T1 | عرض قائمة الصفقات المغلقة | `getTrades()` → `/api/user/trades/<id>` | ✅ |
| T2 | فلتر الفترة الزمنية (أسبوع/شهر/الكل) | client-side filter on fetched data | ✅ |
| T3 | فلتر النتيجة (الكل/رابحة/خاسرة) | client-side filter on fetched data | ✅ |
| T4 | البحث بالعملة | فلتر محلي على البيانات | ✅ |
| T5 | إحصائيات (إجمالي صفقات + رابحة + معدل نجاح + ربح) | من API response | ✅ |
| T6 | شارت الأرباح اليومية (DailyHeatmap) | `/daily-pnl/<id>` | ✅ |
| T7 | شارت توزيع الصفقات (TradeDistributionChart) | `/trades/distribution/<id>` | ✅ |
| T8 | Pull-to-Refresh | يعيد loadData() | ✅ |

## 4️⃣ شاشة إعدادات التداول (TradingSettingsScreen)
| # | الوظيفة | الاتصال (API) | الحالة |
|---|---------|---------------|--------|
| S1 | تفعيل/تعطيل التداول (Switch) | `updateSettings()` → PUT `/api/user/settings/<id>` | ✅ |
| S2 | تغيير نسبة حجم الصفقة (Slider 5-20%) | `updateSettings()` | ✅ |
| S3 | تغيير عدد الصفقات المتزامنة | `updateSettings()` | ✅ |
| S4 | عرض حجم الصفقة المتوقع ($) | محسوب من الرصيد × النسبة | ✅ |
| S5 | زر حفظ الإعدادات | `updateSettings()` → PUT | ✅ |
| S6 | تأكيد المغادرة بدون حفظ | Back handler check | ✅ |

## 5️⃣ شاشة الملف الشخصي (ProfileScreen)
| # | الوظيفة | الاتصال (API) | الحالة |
|---|---------|---------------|--------|
| PR1 | عرض بيانات المستخدم (اسم، إيميل، هاتف) | `getProfile()` → `/api/user/profile/<id>` | ✅ |
| PR2 | تعديل الاسم (مباشر بدون OTP) | `updateProfile()` → PUT `/api/user/profile/<id>` | ✅ |
| PR3 | تعديل الإيميل (يحتاج OTP) | `/auth/send-change-email-otp` → verify | ✅ |
| PR4 | تعديل كلمة المرور (يحتاج OTP) | `/auth/send-change-password-otp` → verify | ✅ |
| PR5 | تعديل رقم الهاتف (يحتاج OTP) | → VerifyActionScreen → API | ✅ |
| PR6 | تفعيل/تعطيل البصمة | BiometricService + OTP | ✅ |
| PR7 | زر تسجيل الخروج (Double Confirmation) | clearUserData() → logout | ✅ |
| PR8 | زر حذف الحساب (Triple Confirmation) | `/auth/delete-account` + password | ✅ |
| PR9 | عرض الإصدار | من package.json | ✅ |
| PR10 | زر → إعدادات الإشعارات | Navigation | ✅ |
| PR11 | زر → الشروط والأحكام | Navigation | ✅ |
| PR12 | زر → سياسة الخصوصية | Navigation | ✅ |
| PR13 | Pull-to-Refresh | loadUserProfile() | ✅ |

## 6️⃣ شاشة مفاتيح Binance (BinanceKeysScreen)
| # | الوظيفة | الاتصال (API) | الحالة |
|---|---------|---------------|--------|
| B1 | عرض حالة المفاتيح (مهيأة/غير مهيأة) | `getBinanceKeys()` → `/api/user/binance-keys/<id>` | ✅ |
| B2 | إدخال API Key + Secret Key | حقول إدخال | ✅ |
| B3 | اختبار المفاتيح (Test) | `/api/user/binance-keys/validate` | ✅ |
| B4 | حفظ المفاتيح | POST `/api/user/binance-keys` + OTP | ✅ |
| B5 | حذف المفاتيح | DELETE `/api/user/binance-keys/<keyId>` + OTP | ✅ |
| B6 | Pull-to-Refresh | loadBinanceKeys() | ✅ |

## 7️⃣ لوحة إدارة الأدمن (AdminDashboard)
| # | الوظيفة | الاتصال (API) | الحالة |
|---|---------|---------------|--------|
| A1 | حالة الاتصال بالخادم (متصل/غير متصل) | Trading State Polling | ✅ |
| A2 | حالة النظام (يعمل/متوقف/خطأ/بدء/إيقاف) | `getTradingState()` → `/admin/trading/state` | ✅ |
| A3 | زر تشغيل النظام | `startTradingSystem()` → `/admin/trading/start` | ✅ |
| A4 | زر إيقاف النظام | `stopTradingSystem()` → `/admin/trading/stop` | ✅ |
| A5 | زر إيقاف الطوارئ 🚨 | `emergencyStopTradingSystem()` → `/admin/trading/emergency-stop` | ✅ |
| A6 | زر إعادة التعيين (من ERROR) | `resetTradingError()` → `/admin/trading/reset-error` | ✅ |
| A7 | عرض PID + Uptime + Session | من Trading State response | ✅ |
| A8 | حالة ML (جاهز/نسبة التقدم) | `getSystemMLStatus()` | ✅ |
| A9 | حالة Group B (صفقات/عملات/آخر دورة) | `getGroupBStatus()` | ✅ |
| A10 | سجل الأخطاء (عدد + حرجة + أحدث 3) | `getBackgroundErrors()` → `/admin/errors` | ✅ |
| A11 | زر → سجل الأخطاء الكامل | Navigation → AdminErrorsScreen | ✅ |
| A12 | إعادة ضبط Demo ($1000) | POST `/admin/demo/reset` | ✅ |
| A13 | عدد المستخدمين (إجمالي/نشط) | `getAllUsers()` → `/admin/users/all` | ✅ |
| A14 | زر → إدارة المستخدمين | Navigation → UserManagementScreen | ✅ |
| A15 | زر → إضافة مستخدم | Navigation → CreateUserScreen | ✅ |
| A16 | Polling كل 5 ثواني (Trading State) | auto-refresh | ✅ |
| A17 | Polling كل 15 ثانية (بيانات إضافية) | auto-refresh | ✅ |

## 8️⃣ شاشة إدارة المستخدمين (UserManagementScreen)
| # | الوظيفة | الاتصال (API) | الحالة |
|---|---------|---------------|--------|
| U1 | عرض قائمة المستخدمين + إحصائيات | `getAllUsers()` → `/admin/users/all` | ✅ |
| U2 | بحث بالاسم/الإيميل | فلتر محلي | ✅ |
| U3 | تفعيل/تعطيل مستخدم | `updateUser()` → PUT `/admin/users/<id>/update` | ✅ |
| U4 | تغيير دور المستخدم | `updateUser()` → PUT | ✅ |
| U5 | حذف (تعطيل) مستخدم | `deleteUser()` → DELETE `/admin/users/<id>/delete` | ✅ |
| U6 | زر → إضافة مستخدم جديد | Navigation → CreateUserScreen | ✅ |

## 9️⃣ شاشة إضافة مستخدم (CreateUserScreen)
| # | الوظيفة | الاتصال (API) | الحالة |
|---|---------|---------------|--------|
| C1 | نموذج إدخال (اسم/إيميل/كلمة مرور/هاتف) | حقول + validation | ✅ |
| C2 | اختيار نوع الحساب (مستخدم/مدير) | Radio buttons (admin/regular) | ✅ |
| C3 | مؤشرات قوة كلمة المرور | Local validation | ✅ |
| C4 | زر إنشاء المستخدم | POST `/admin/users/create` | ✅ |

---
## إجمالي الوظائف: ~70 وظيفة
## الفحص: وظيفة بوظيفة بالتسلسل
