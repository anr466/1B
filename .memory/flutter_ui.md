# Flutter UI — واجهة المستخدم

> **مبني على الملفات الفعلية في `flutter_trading_app/lib/` فقط — 100 ملف Dart**

## نظرة عامة
تطبيق Flutter عربي (RTL) متعدد المنصات للتداول الآلي. يستخدم GoRouter للتنقل، Riverpod لإدارة الحالة، ونظام Skins قابل للتبديل مع 7 ثيمات.

---

## الملفات الفعلية (100 ملف)

### نقطة الدخول (2 ملف)

| الملف | الوظيفة |
|-------|---------|
| `main.dart` | التهيئة: Firebase, FCM, Local Notifications, Storage, Skin loading |
| `app.dart` | TradingApp: MaterialApp.router مع ScreenUtil, GoRouter, Skin System |

### التنقل (3 ملفات)

| الملف | الوظيفة |
|-------|---------|
| `navigation/app_router.dart` | GoRouter — جميع المسارات + redirect logic + auth guard |
| `navigation/main_shell.dart` | MainShell — Scaffold + BottomNavigationBar (5 tabs بأيقونات فقط) |
| `navigation/route_names.dart` | RouteNames — كل أسماء المسارات في مكان واحد |

**التنقل الفعلي:**
```
/splash → /login → /register → /otp-verification → /forgot-password → /reset-password → /onboarding

Main Shell (5 tabs):
  /dashboard  (home)
  /portfolio  (wallet)
  /trades     (history)
  /analytics  (chart)
  /profile    (user) — يتحول إلى shield (admin) إذا كان المستخدم مسؤولاً

Non-shell routes:
  /trades/detail
  /settings/trading
  /settings/binance-keys
  /settings/notifications
  /settings/security
  /settings/skin
  /notifications
  /admin/dashboard
  /admin/trading-control
  /admin/users
  /admin/logs
  /admin/logs/error
```

### الشاشات الفعلية (22 شاشة)

| الميزة | الشاشات |
|--------|---------|
| **Auth** (7 ملفات) | `splash_screen.dart`, `login_screen.dart`, `register_screen.dart`, `otp_verification_screen.dart`, `forgot_password_screen.dart`, `reset_password_screen.dart`, `countdown_timer.dart` |
| **Dashboard** (1 ملف) | `dashboard_screen.dart` |
| **Portfolio** (1 ملف) | `portfolio_screen.dart` |
| **Trades** (2 ملف) | `trades_screen.dart`, `trade_detail_screen.dart` |
| **Analytics** (1 ملف) | `analytics_screen.dart` |
| **Profile** (1 ملف) | `profile_screen.dart` |
| **Settings** (4 ملفات) | `trading_settings_screen.dart`, `binance_keys_screen.dart`, `security_settings_screen.dart`, `skin_picker_screen.dart` |
| **Notifications** (2 ملف) | `notifications_screen.dart`, `notification_settings_screen.dart` |
| **Onboarding** (1 ملف) | `onboarding_screen.dart` |
| **Admin** (5 ملفات) | `admin_dashboard_screen.dart`, `trading_control_screen.dart`, `user_management_screen.dart`, `system_logs_screen.dart`, `error_details_screen.dart` |

### النماذج (8 ملفات)

| الملف | الوظيفة |
|-------|---------|
| `core/models/user_model.dart` | نموذج المستخدم |
| `core/models/trade_model.dart` | نموذج الصفقة |
| `core/models/portfolio_model.dart` | نموذج المحفظة |
| `core/models/settings_model.dart` | نموذج الإعدادات |
| `core/models/notification_model.dart` | نموذج الإشعار |
| `core/models/notification_settings_model.dart` | نموذج إعدادات الإشعارات |
| `core/models/stats_model.dart` | نموذج الإحصائيات |
| `core/models/system_status_model.dart` | نموذج حالة النظام |

### المزودين (7 ملفات)

| الملف | الوظيفة |
|-------|---------|
| `core/providers/auth_provider.dart` | حالة المصادقة (AuthState: initial/loading/authenticated/unauthenticated) |
| `core/providers/portfolio_provider.dart` | حالة المحفظة |
| `core/providers/trades_provider.dart` | حالة الصفقات |
| `core/providers/notifications_provider.dart` | حالة الإشعارات |
| `core/providers/admin_provider.dart` | حالة الإدارة |
| `core/providers/privacy_provider.dart` | مزود الخصوصية |
| `core/providers/service_providers.dart` | الخدمات والمستودعات (ApiService, AuthService, Repositories) |

### المستودعات (5 ملفات)

| الملف | الوظيفة |
|-------|---------|
| `core/repositories/trades_repository.dart` | مستودع الصفقات |
| `core/repositories/portfolio_repository.dart` | مستودع المحفظة |
| `core/repositories/notifications_repository.dart` | مستودع الإشعارات |
| `core/repositories/admin_repository.dart` | مستودع الإدارة |
| `core/repositories/settings_repository.dart` | مستودع الإعدادات |

### الخدمات (10 ملفات)

| الملف | الوظيفة |
|-------|---------|
| `core/services/api_service.dart` | عميل HTTP |
| `core/services/auth_service.dart` | خدمة المصادقة |
| `core/services/storage_service.dart` | التخزين المحلي |
| `core/services/push_notification_service.dart` | خدمة الإشعارات |
| `core/services/connectivity_service.dart` | خدمة الاتصال |
| `core/services/biometric_service.dart` | خدمة البصمة |
| `core/services/credential_encryption.dart` | تشفير البيانات |
| `core/services/debounce_service.dart` | خدمة التأخير |
| `core/services/parsing_service.dart` | خدمة التحليل |
| `core/services/api_cache.dart` | التخزين المؤقت للـ API |

### الثوابت (4 ملفات)

| الملف | الوظيفة |
|-------|---------|
| `core/constants/app_constants.dart` | ثوابت التطبيق |
| `core/constants/api_endpoints.dart` | نقاط نهاية API |
| `core/constants/ux_messages.dart` | رسائل UX |
| `core/constants/verification_types.dart` | أنواع التحقق |

### نظام التصميم (50 ملف)

#### Skins (7 ثيمات — 16 ملف)

| الثيم | الملفات |
|-------|---------|
| `emerald_trading` | `emerald_trading_skin.dart`, `emerald_trading_colors.dart` |
| `midnight_ocean` | `midnight_ocean_skin.dart`, `midnight_ocean_colors.dart` |
| `violet_brand` | `violet_brand_skin.dart`, `violet_brand_colors.dart` |
| `arctic_frost` | `arctic_frost_skin.dart`, `arctic_frost_colors.dart` |
| `rose_gold` | `rose_gold_skin.dart`, `rose_gold_colors.dart` |
| `obsidian_titanium` | `obsidian_titanium_skin.dart`, `obsidian_titanium_colors.dart` |
| `cyber_neon` | `cyber_neon_skin.dart`, `cyber_neon_colors.dart` |

#### إدارة الثيمات (3 ملفات)

| الملف | الوظيفة |
|-------|---------|
| `design/skins/skin_manager.dart` | مدير الثيمات |
| `design/skins/skin_interface.dart` | واجهة الثيم |
| `design/skins/skin_theme_builder.dart` | باني الثيم |

#### Design Tokens (4 ملفات)

| الملف | الوظيفة |
|-------|---------|
| `design/tokens/color_tokens.dart` | رموز الألوان |
| `design/tokens/semantic_colors.dart` | الألوان الدلالية |
| `design/tokens/spacing_tokens.dart` | رموز المسافات |
| `design/tokens/typography_tokens.dart` | رموز الطباعة |

#### الأيقونات (2 ملف)

| الملف | الوظيفة |
|-------|---------|
| `design/icons/brand_icons.dart` | أيقونات العلامة التجارية |
| `design/icons/brand_logo.dart` | شعار العلامة التجارية |

#### الأدوات المساعدة (1 ملف)

| الملف | الوظيفة |
|-------|---------|
| `design/utils/responsive_utils.dart` | أدوات الاستجابة |

#### Widgets (21_widget)

| الملف | الوظيفة |
|-------|---------|
| `design/widgets/app_button.dart` | زر التطبيق |
| `design/widgets/app_card.dart` | بطاقة التطبيق |
| `design/widgets/app_input.dart` | حقل إدخال |
| `design/widgets/app_icon_button.dart` | زر أيقونة |
| `design/widgets/app_info_row.dart` | صف معلومات |
| `design/widgets/app_screen_header.dart` | رأس الشاشة |
| `design/widgets/app_section_label.dart` | عنوان القسم |
| `design/widgets/app_setting_tile.dart` | بلاط الإعدادات |
| `design/widgets/app_snackbar.dart` | شريط Snackbar |
| `design/widgets/gradient_background.dart` | خلفية متدرجة |
| `design/widgets/empty_state.dart` | حالة فارغة |
| `design/widgets/error_state.dart` | حالة خطأ |
| `design/widgets/loading_shimmer.dart` | تحميل Shimmer |
| `design/widgets/status_badge.dart` | شارة الحالة |
| `design/widgets/pnl_indicator.dart` | مؤشر الربح/الخسارة |
| `design/widgets/money_text.dart` | نص مالي |
| `design/widgets/financial_metric_tile.dart` | بلاط_metric مالي |
| `design/widgets/section_header.dart` | رأس القسم |
| `design/widgets/trading_status_strip.dart` | شريط حالة التداول |
| `design/widgets/flow_stepper.dart` | متتبع التدفق |
| `design/widgets/registration_stepper.dart` | متتبع التسجيل |
| `design/widgets/context_feedback.dart` | ملاحظات السياق |

---

## بنية إدارة الحالة الفعلية

```
main.dart
  └── ProviderScope
       ├── storageServiceProvider (StorageService)
       ├── skinNameProvider (saved skin)
       ├── themeModeProvider (saved theme)
       └── TradingApp
            └── service_providers.dart
                 ├── apiServiceProvider → ApiService(storage)
                 ├── authServiceProvider → AuthService(api, storage)
                 ├── biometricServiceProvider → BiometricService
                 ├── pushNotificationServiceProvider → PushNotificationService
                 ├── portfolioRepositoryProvider → PortfolioRepository(api)
                 ├── tradesRepositoryProvider → TradesRepository(api)
                 ├── settingsRepositoryProvider → SettingsRepository(api)
                 ├── notificationsRepositoryProvider → NotificationsRepository(api)
                 ├── adminRepositoryProvider → AdminRepository(api)
                 ├── biometricTrustProvider → StateNotifierProvider
                 └── notificationSettingsProvider → FutureProvider
```

---

## الصلاحيات الفعلية

| الميزة | المستخدم العادي | المسؤول |
|--------|----------------|---------|
| Splash/Login/Register | ✅ | ✅ |
| OTP Verification | ✅ | ✅ |
| Dashboard | ✅ | ✅ |
| Portfolio | ✅ | ✅ |
| Trades | ✅ | ✅ |
| Analytics | ✅ | ✅ |
| Profile | ✅ | ✅ |
| Trading Settings | ✅ | ✅ |
| Binance Keys | ✅ | ✅ |
| Notifications | ✅ | ✅ |
| Security Settings | ✅ | ✅ |
| Skin Picker | ✅ | ✅ |
| Admin Dashboard | ❌ | ✅ |
| Trading Control | ❌ | ✅ |
| User Management | ❌ | ✅ |
| System Logs | ❌ | ✅ |
| Error Details | ❌ | ✅ |

**آلية الحماية:** `app_router.dart` → `redirect` يتحقق من `auth.isAuthenticated` و `auth.isAdmin`

---

## Bottom Navigation الفعلي

5 tabs بأيقونات فقط (بدون نص):
1. **Home** — Dashboard
2. **Wallet** — Portfolio
3. **History** — Trades
4. **Chart** — Analytics
5. **User** (عادي) / **Shield** (مسؤول) — Profile / Admin

المسؤول يرى نقطة (dot) على تبويب Profile للإشارة إلى لوحة الإدارة.

---

## ملفات التكوين

| الملف | الوظيفة |
|-------|---------|
| `pubspec.yaml` | التبعيات والإعدادات |
| `analysis_options.yaml` | إعدادات التحليل |
| `android/` | تكوين Android |
| `assets/` | الأصول (خطوط، صور) |
