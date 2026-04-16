# PROJECT BRAIN — فكرة المشروع وثوابته

> **آخر تحديث:** 2026-04-14 (بعد الإصلاحات والتوحيد)
> **الحالة:** ✅ 45/45 وحدة تعمل | بيئة افتراضية مكتملة | جاهز للنقل للسيرفر

---

## 1. نظرة عامة

**الاسم:** Trading AI Bot — نظام تداول آلي ذكي متعدد الاستراتيجيات
**النوع:** نظام تداول آلي (Automated Trading System) مع واجهة موبايل
**الهدف الأساسي:** تشغيل تداول آلي ذكي على Binance باستخدام استراتيجيات متعددة مدعومة بالتعلم الآلي، مع واجهة تحكم كاملة عبر تطبيق Flutter

**القيمة المقدمة:**
- تداول آلي 24/7 بدون تدخل بشري
- استراتيجيات متعددة تتكيف مع ظروف السوق
- تعلم آلي يتحسن مع الوقت من الأخطاء والنجاحات
- واجهة موبايل عربية كاملة للتحكم والمراقبة
- نظام 4 مراحل: Backtest → Paper → Validation → Live

---

## 2. المكونات التقنية (Stack)

| الطبقة | التقنية | الإصدار |
|--------|---------|---------|
| **Backend** | Python (FastAPI + Flask) | Python 3.13.7 |
| **Database** | PostgreSQL | psycopg2-binary 2.9.10 |
| **Mobile** | Flutter (Dart) | مع GoRouter + Riverpod |
| **Exchange** | Binance API | python-binance 1.0.32 |
| **ML** | scikit-learn + XGBoost | scikit-learn 1.8.0, xgboost 3.2.0 |
| **Data** | pandas + numpy + pandas_ta | pandas 2.3.3 |
| **Notifications** | Firebase Cloud Messaging | firebase_admin 7.1.0 |
| **Deployment** | Docker + PM2 | — |
| **Virtual Env** | `.venv/` | 116 حزمة مثبتة |

---

## 3. الأنظمة الفرعية (13 وحدة)

### 3.1 المحرك الأساسي (`backend/core/` — 26 ملف)
**المحرك الموحد الوحيد:** `TradingOrchestrator` (بعد حذف `UnifiedTradingEngine`)

| المكون | الوظيفة |
|--------|---------|
| `TradingOrchestrator` | **المحرك الرئيسي** — يربط كل الأنظمة (كشف → توجيه → دخول → خروج) |
| `TradingStateMachine` | آلة الحالة: STOPPED → STARTING → RUNNING → HALTING → STOPPED |
| `StrategyRouter` | يوجه الاستراتيجيات حسب نظام السوق |
| `DualModeRouter` | LONG→Spot, SHORT→Margin |
| `EntryExecutor` | منفذ الدخول (يحسب SL/TP/الكمية) |
| `ExitEngine` | حساب PnL + عمولة |
| `ExitManager` | **جديد** — نظام خروج موحد (SL/TP/Trailing/Time/Partial) يدعم LONG+SHORT |
| `PositionManager` | مدير المراكز (Mixin) |
| `CoinStateAnalyzer` | تحليل حالة العملة (Trend/Volatility/Regime/Momentum) مع تأكيد 4H |
| `DynamicCoinSelector` | اختيار العملات ديناميكياً حسب السيولة والتقلب |
| `PortfolioRiskManager` | إدارة المخاطر (6 Tiers: MICRO→WHALE) |
| `MTFConfirmationEngine` | تأكيد متعدد الأطر (1H + 15m + 5m) |
| `CognitiveDecisionMatrix` | مصفوفة القرار المعرفي (وزن 6 عوامل) |
| `StateManager` | مدير الحالة (DB-only — `system_status` table) |
| `HeartbeatMonitor` | مراقب النبض (warning >30s, critical >60s) |
| `MonitoringEngine` | محرك مراقبة المراكز المفتوحة |
| `BinanceConnector` | الاتصال بـ Binance |
| `GroupBSystem` | **المحرك الرئيسي** — يربط كل المكونات في دورة تداول |

### 3.2 الاستراتيجيات (`backend/strategies/` — 18 ملف)
| الاستراتيجية | النوع | الحالة |
|-------------|-------|--------|
| `ScalpingV8` | سكالبينج (الرئيسية) | ✅ PF=1.72 WR=62% |
| `ScalpingV7` | سكالبينج (احتياطية) | ✅ |
| `ScalpingEMA` | سكالبينج بـ EMA | ✅ |
| `TrendFollowing` | متابعة الاتجاه | ✅ |
| `MeanReversion` | العودة إلى المتوسط | ✅ |
| `MomentumBreakout` | كسر الزخم | ✅ |
| `RSIDivergence` | تباعد RSI | ✅ |
| `VolumePriceTrend` | اتجاه الحجم والسعر | ✅ |
| `PeakValleyScalping` | سكالبينج القمم والقيعان | ✅ |
| `MTFAOptimized` | تحليل متعدد الأطر | ✅ |

### 3.3 التعلم الآلي (`backend/ml/` — 15 ملف)
| المكون | الوظيفة |
|--------|---------|
| `TradingBrain` | الدماغ التداولي — قرار مركزي مع ذاكرة أخطاء |
| `HybridMLSystem` | تعلم هجين (Backtest + بيانات حقيقية) |
| `SignalClassifier` | مصنف الإشارات |
| `PatternSimilarityMatcher` | مطابقة الأنماط التاريخية |
| `BacktestImporter` | استيراد نتائج Backtest لتدريب ML |
| `PaperTrading` | التداول الورقي (المرحلة 2) |
| `LiveValidator` | التحقق المباشر (المرحلة 3) |

### 3.4 النظام المعرفي (`backend/cognitive/` — 3 ملفات)
| المكون | الوظيفة |
|--------|---------|
| `CognitiveOrchestrator` | المُنسّق المعرفي (1133 سطر) |
| `MultiExitEngine` | محرك الخروج المتعدد |

### 3.5 التحليل (`backend/analysis/` — 5 ملفات)
| المكون | الوظيفة |
|--------|---------|
| `MarketRegimeDetector` | كشف نظام السوق (BULL/BEAR/NEUTRAL/VOLATILE) |
| `LiquidityCognitiveFilter` | فلتر السيولة المعرفي |
| `VolatilityAnalyzer` | تحليل التقلب |

### 3.6 واجهة API (`backend/api/` — 31 ملف)
| المجموعة | الملفات |
|----------|---------|
| المصادقة | 7 ملفات (JWT + OTP + تسجيل) |
| التداول | 4 ملفات (تحكم + محفظة + صفقات) |
| الإشعارات | 3 ملفات (FCM + إشعارات) |
| الإدارة | 4 ملفات (مستخدمين + سجلات + ML) |
| النظام | 4 ملفات (صحة + استعادة + خلفية) |

### 3.7 الأدوات المساعدة (`backend/utils/` — 25 ملف)
| المكون | الوظيفة |
|--------|---------|
| `indicator_calculator.py` | **جديد** — مصدر واحد لكل المؤشرات الفنية (RSI/ADX/ATR/MACD/BB/OBV) |
| `DataProvider` | مزود البيانات من Binance مع caching |
| `ErrorLogger` | مسجل الأخطاء الموحد |
| `CircuitBreaker` | قاطع الدائرة لحماية API |
| `TradingNotificationService` | خدمة إشعارات التداول |

### 3.8 الوحدات الأخرى
| الوحدة | الملفات | الوظيفة |
|--------|---------|---------|
| `learning/` | 2 | التعلم التكيفي (AdaptiveOptimizer) |
| `monitoring/` | 3 | المراقبة (HealthCheck + SystemAlerts) |
| `risk/` | 3 | إدارة المخاطر (KellySizer + HeatManager) |
| `selection/` | 2 | القائمة السوداء الديناميكية |
| `services/` | 4 | الخدمات (Auth + Notifications + Onboarding) |
| `infrastructure/` | 1 | طبقة الوصول لقاعدة البيانات |
| `schedulers/` | 1 | المجدولات |

---

## 4. أنواع المستخدمين والصلاحيات

### 4.1 الأدمن (`user_type = 'admin'`)
- ✅ محفظة واحدة يختارها (Demo أو Real) — **ليستاثنتان**
- ✅ تبديل حصري بين Demo/Real عبر `user_settings.is_demo`
- ✅ لوحة إدارة كاملة (مستخدمين + سجلات + ML + نظام)
- ✅ التحكم في تشغيل/إيقاف النظام محرك نظام التداول الخلفي وهذا يوقف جميع العمليات على المستخدمين 
- الادمن هو مستخدم عادي في المحفظه الحقيقيه ويعامل مثلما يعامل المستخدمون 
- يمكن للادمن تفعيل التداول الخاص بحساباته مثل الحساب التجريبي والحقيقي 
- المحفظه التجريبيه حصري للادمن فقط وتعمل مثل الحقيقه فقط التنفيذ الصفقات الاموال وهمي ويحاكي الواقع مثل الانزلاق والعموله 
- كل محافظ الادمن معزوله ويمكن للادمن التبديل بينهم وعند التبديل تنعكس الشاشات لتعرض بيانات المحفظه النشطه 

### 4.2 المستخدم العادي (`user_type = 'user'`)
- ✅ محفظة حقيقية واحدة فقط
- ✅ تفعيل/إيقاف التداول (إذا سمح له)
- ✅ عرض صفقاته ومحفظته وإشعاراته فقط
- ✅ إدارة مفاتيح Binance الخاصة به
- ❌ لا يصل للوحة الإدارة
- ❌ لا يصل لبيانات مستخدمين آخرين

### 4.3 قاعدة العزل
- كل جدول يحتوي `user_id`
- كل استعلام يفلتر بـ `WHERE user_id = %s`
- `UNIQUE(user_id, is_demo)` في `user_settings` و `portfolio`

---

## 5. القواعد الثابتة للنظام

### 5.1 مصدر واحد للحقيقة
- **قاعدة البيانات PostgreSQL** هي المصدر الوحيد
- ❌ لا ملفات JSON للحالة (تم حذفها)
- ✅ `system_status` table لحالة النظام
- ✅ `StateManager` يقرأ/يكتب من DB فقط

### 5.2 قاعدة التفعيل/الإيقاف
- المستخدم المعطل (`trading_enabled = false`) لا تفتح له صفقات جديدة
- الصفقات المفتوحة تُدار حتى تُغلق
- حالة النظام: STOPPED → STARTING → RUNNING → HALTING → STOPPED

### 5.3 نظام المراحل الأربع (4-Phase System)
```
Phase 1: BACKTEST_BOOTSTRAP → استيراد نتائج الاختبار الخلفي
Phase 2: PAPER_TRADING      → تداول ورقي بدون مال حقيقي
Phase 3: VALIDATION          → تحقق من نتائج Paper
Phase 4: LIVE_TRADING        → تداول حقيقي
```
- ❌ لا تخطي المراحل
- ✅ كل مرحلة تحتاج حد أدنى من الصفقات ومعدل ربح

### 5.4 Demo/Live Separation
- محفظتان منفصلتان تماماً (`portfolio.is_demo`)
- إعدادات منفصلة (`user_settings.is_demo`)
- صفقات منفصلة (`user_trades.is_demo`, `active_positions.is_demo`)

### 5.5 محرك تداول واحد
- ✅ `TradingOrchestrator` هو المحرك الوحيد
- ❌ `UnifiedTradingEngine` تم حذفه (كان يدير صفقات في الذاكرة فقط)
- ✅ `GroupBSystem` يستدعي `TradingOrchestrator` فقط

### 5.6 مؤشرات فنية موحدة
- ✅ `indicator_calculator.py` هو المصدر الوحيد
- ❌ لا حسابات مكررة في الملفات الأخرى

### 5.7 نظام خروج موحد
- ✅ `ExitManager` يجمع كل شروط الخروج
- ✅ يدعم LONG و SHORT بشكل متساوٍ
- ✅ SL/TP/Trailing/Time/Partial في مكان واحد

---

## 6. هيكل البيانات الأساسي (27 جدول)

### مجموعة المستخدمين (5)
| الجدول | الأعمدة الرئيسية |
|--------|-----------------|
| `users` | id, username, email, password_hash, user_type, is_active |
| `user_settings` | user_id, is_demo, trading_enabled, trade_amount, position_size_percentage, stop_loss_pct, risk_level |
| `user_binance_keys` | user_id, api_key, api_secret, is_active, is_testnet |
| `user_sessions` | user_id, session_token, is_active, expires_at |
| `user_devices` | user_id, device_id, push_token, fcm_token |

### مجموعة التداول (4)
| الجدول | الأعمدة الرئيسية |
|--------|-----------------|
| `active_positions` | user_id, symbol, strategy, entry_price, stop_loss, take_profit, trailing_sl_price, is_active, is_demo |
| `user_trades` | user_id, symbol, entry_time, exit_time, entry_price, exit_price, profit_loss, status, is_demo |
| `trading_signals` | symbol, signal_type, strategy, confidence, is_processed |
| `successful_coins` | symbol, strategy, timeframe, success_rate, score, win_rate |

### مجموعة المحفظة (3)
| الجدول | الأعمدة الرئيسية |
|--------|-----------------|
| `portfolio` | user_id, initial_balance, total_balance, available_balance, invested_balance, is_demo |
| `demo_accounts` | user_id, initial_balance(1000), available_balance, total_trades |
| `portfolio_growth_history` | user_id, date, total_balance, daily_pnl, is_demo |

### مجموعة النظام (5)
| الجدول | الأعمدة الرئيسية |
|--------|-----------------|
| `system_status` | id(1), trading_state, mode, is_running, subsystem_status(JSON), message |
| `system_errors` | error_type, error_message, component, severity, resolved |
| `activity_logs` | user_id, component, action, details, status |
| `security_audit_log` | user_id, action, resource, ip_address, status |
| `admin_notification_settings` | telegram_enabled, email_enabled, webhook_enabled (سجل واحد) |

### مجموعة ML (3)
| الجدول | الأعمدة الرئيسية |
|--------|-----------------|
| `backtest_results` | symbol, strategy, timeframe, profit_pct, is_win, indicators(JSONB), imported_to_ml |
| `paper_trading_log` | user_id, symbol, strategy, entry_price, exit_price, pnl_pct, is_win |
| `trading_phase_state` | current_phase, backtest_win_rate, paper_win_rate, validation_passed (سجل واحد) |

### مجموعة الإشعارات (4)
| الجدول | الأعمدة الرئيسية |
|--------|-----------------|
| `notifications` | user_id, title, message, type, is_read |
| `notification_history` | user_id, notification_type, sent_via, status, read_at |
| `user_notification_settings` | user_id, trade_notifications, price_alerts, push_enabled |
| `fcm_tokens` | user_id, fcm_token(unique), platform, is_active |

### مجموعة المصادقة (3)
| الجدول | الأعمدة الرئيسية |
|--------|-----------------|
| `verification_codes` | email, otp_code, purpose, expires_at, verified |
| `pending_verifications` | user_id, action, otp, method, new_value, expires_at |
| `user_binance_balance` | user_id, asset, free_balance, locked_balance, total_balance |

---

## 7. البنية المعمارية بعد التوحيد

```
┌─────────────────────────────────────────────────────────┐
│                    GroupBSystem                         │
│              (المحرك الرئيسي — دورة تداول)                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│               TradingOrchestrator                       │
│         (المحرك الموحد الوحيد للتداول)                    │
│                                                         │
│  1. DynamicCoinSelector → اختيار العملات               │
│  2. CoinStateAnalyzer  → تحليل الحالة (+ df_4h)        │
│  3. StrategyRouter     → توجيه الاستراتيجية            │
│  4. MTFConfirmation    → تأكيد متعدد الأطر              │
│  5. CognitiveMatrix    → مصفوفة القرار                  │
│  6. TradingBrain       → قرار ML                       │
│  7. EntryExecutor      → تنفيذ الدخول                  │
│  8. ExitManager        → إدارة الخروج (موحد)           │
│  9. PositionManager    → تحديث DB                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              TradingStateMachine                        │
│         (آلة الحالة: START/STOP/HALT)                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              DatabaseManager (PostgreSQL)                │
│         (المصدر الوحيد للحقيقة)                          │
│  ├── db_users_mixin.py                                  │
│  ├── db_trading_mixin.py                                │
│  ├── db_portfolio_mixin.py                              │
│  └── db_notifications_mixin.py                          │
└─────────────────────────────────────────────────────────┘
```

---

## 8. التكنولوجيا والإصدارات

| المكون | الإصدار |
|--------|---------|
| Python | 3.13.7 |
| FastAPI | 0.121.0 |
| Flask | 3.1.2 |
| pandas | 2.3.3 |
| numpy | 2.2.6 |
| scikit-learn | 1.8.0 |
| XGBoost | 3.2.0 |
| psycopg2 | 2.9.10 |
| python-binance | 1.0.32 |
| firebase_admin | 7.1.0 |
| pandas_ta | 0.4.71b0 |
| Flutter | (موجود في flutter_trading_app/) |
| Virtual Env | `.venv/` — 116 حزمة |

---

## 9. حالة المشروع الحالية (2026-04-14 — بعد التحسينات الشاملة)

### ✅ ما يعمل
- 29/29 وحدة تستورد بنجاح
- `indicator_calculator.py` — مصدر واحد للمؤشرات
- `ExitManager` — نظام خروج موحد LONG+SHORT + evaluate_positions
- `MonitoringEngine` — LONG+SHORT متساويان (trailing/breakeven/partial)
- `CoinStateAnalyzer` المحسّن — 3 confirmations (4H+MACD+Volume) + divergence detection + bb_position
- `CognitiveDecisionMatrix` المحسّنة — regime-aware weights + signal_quality
- `MTFConfirmation` — volume confirmation (15m+5m)
- `TradingOrchestrator` المحسّن — ensemble scoring + multi-factor confirmation + ExitManager
- `PositionManager` — TOCTOU مزدوج + `available_balance` موحد
- `setup.sh` — سكربت إعداد يعمل على Linux/macOS
- `requirements-frozen.txt` — 116 حزمة مجمّدة
- `setup.sh` — سكربت إعداد يعمل على Linux/macOS
- `requirements-frozen.txt` — 116 حزمة مجمّدة

### ❌ ما تم حذفه
- `unified_trading_engine.py` — محرك موازي في الذاكرة (dead code)
- حسابات المؤشرات المكررة في 4 ملفات
- استيراد `dynamic_universe_selector` غير الموجود
- استيراد `market_state_detector` غير الموجود

### ⚠️ ما يحتاج انتباه
- PostgreSQL غير متصل محلياً (يعمل عبر Docker على السيرفر)
- `pandas_ta` مطلوب لـ StrategyEnsemble (مثبت)
- `StrategyRouter` + `EntryExecutor` — dead code (ازدواجية مع modules)
- مفاتيح Binance مطلوبة للتداول الحقيقي

---

## 10. معلومات لا تتغير

- **اللغة:** الواجهة عربية (RTL)
- **المنصة:** macOS (تطوير) → Linux (إنتاج)
- **نمط التوزيع:** Docker + PM2
- **حد الطلبات:** 200 طلب/دقيقة لـ Binance
- **دورة التداول:** كل 60 ثانية
- **الحد الأقصى للصفقات:** 5 يومياً (حقيقي) / 15 يومياً (تجريبي)
- **الحد الأقصى للخسارة:** 3% يومياً (قابل للتعديل)
- **الحد الأقصى للمراكز:** حسب Tier المحفظة (2-8)
