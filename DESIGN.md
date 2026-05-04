---
version: alpha
name: 1B Trading — Obsidian Titanium
description: هوية بصرية احترافية لمنصة تداول آلي. أسود عميق مع أزرق صلب وذهبي ناعم.
colors:
  primary: "#6B9FD4"
  primary-dark: "#4A7BB0"
  primary-light: "#9AC2E8"
  secondary: "#DFD0AA"
  accent: "#F0D89E"
  success: "#22C55E"
  warning: "#F59E0B"
  error: "#EF4444"
  info: "#7FA4D8"
  background: "#080C14"
  surface: "#101824"
  surface-high: "#182336"
  card: "#1C2840"
  elevated: "#24334E"
  on-primary: "#FFFFFF"
  on-surface: "#F8FAFC"
  on-surface-secondary: "#BCC8D8"
  on-surface-tertiary: "#8899AE"
  border: "#334D6E"
  border-light: "#456080"
  positive: "#22C55E"
  negative: "#EF4444"
typography:
  hero:
    fontSize: 36px
    fontWeight: 700
    letterSpacing: -0.15px
    fontFeature: "'tnum'"
  h1:
    fontSize: 28px
    fontWeight: 700
    letterSpacing: -0.3px
  h2:
    fontSize: 22px
    fontWeight: 600
  h3:
    fontSize: 18px
    fontWeight: 600
  h4:
    fontSize: 15px
    fontWeight: 600
  body:
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.55
  body-sm:
    fontSize: 13px
    fontWeight: 400
    lineHeight: 1.45
  caption:
    fontSize: 11px
    fontWeight: 400
    lineHeight: 1.35
  label:
    fontSize: 13px
    fontWeight: 500
  button:
    fontSize: 16px
    fontWeight: 500
  mono:
    fontSize: 15px
    fontWeight: 600
    fontFeature: "'tnum'"
  code:
    fontFamily: monospace
    fontSize: 13px
    fontWeight: 400
  overline:
    fontSize: 11px
    fontWeight: 600
spacing:
  xxs: 2px
  xs: 4px
  sm: 8px
  md: 12px
  base: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  xxxl: 64px
rounded:
  sm: 8px
  md: 12px
  lg: 14px
  xl: 16px
  xxl: 24px
  badge: 12px
  full: 999px
components:
  app-button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
    padding: 16px
    height: 52px
    typography: "{typography.button}"
  app-button-danger:
    backgroundColor: "{colors.error}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
  app-card:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.md}"
    padding: 16px
  app-input:
    backgroundColor: "{colors.surface-high}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.md}"
    height: 52px
  app-screen-header:
    height: 56px
    typography: "{typography.h3}"
  status-badge-success:
    backgroundColor: "{colors.success}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.full}"
  status-badge-error:
    backgroundColor: "{colors.error}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.full}"
  status-badge-warning:
    backgroundColor: "{colors.warning}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.full}"
  tab-bar:
    height: 64px
    activeIcon: 28px
    inactiveIcon: 24px
---

## Overview — شخصية العلامة

**Obsidian Titanium**. أسود احترافي عميق بعمق المعادن الداكنة، يوحِي بالثقة والقوة. أزرق صلب (#6B9FD4) هو لون التفاعل الوحيد. ذهبي ناعم (#DFD0AA) للتوكيدات الراقية.

**الفئة المستهدفة:** متداول العملات الرقمية المحترف. يحتاج الدقة، السرعة، والثقة.

**الإحساس المستهدف:** قوي. نظيف. مباشر. لا زخرفة. لا إلهاء.

## Colors — نظام الألوان

لوحة الألوان متجذرة في تباين عالٍ بين الأسود العميق والأبيض الناصع، مع لونين توكيديين فقط:

- **Primary (#6B9FD4):** أزرق صلب — اللون الوحيد المسموح به للتفاعلات (أزرار، روابط، أيقونات نشطة، تبويب نشط).
- **Secondary (#DFD0AA):** ذهبي شاحب — للتوكيدات الراقية حصراً (أصول مميزة، مقاييس نجمية). لا يُستخدم كزر تفاعل.
- **Accent (#F0D89E):** ذهبي فاتح — تدرجات خلفية فقط.
- **Success (#22C55E):** أخضر مالي — أرباح، صفقات رابحة، تأكيد.
- **Error (#EF4444):** أحمر مالي — خسائر، صفقات خاسرة، أخطاء، تدمير.
- **Warning (#F59E0B):** برتقالي — تحذيرات، إيقاف طارئ.
- **Background (#080C14):** أسود متطرف — خلفية الشاشات الرئيسية.
- **Surface (#101824):** أسود ثانوي — خلفية القوائم والمناطق الثانوية.
- **Card (#1C2840):** أزرق داكن — خلفية البطاقات والمحتوى المرتفع.

### قواعد الألوان

- ✅ استخدم `ColorScheme.primary` للتفاعلات فقط
- ✅ استخدم `SemanticColors.positive` للأرباح و `negative` للخسائر
- ❌ لا تستخدم ألواناً مباشرة (`Color(0xFF...)`) — استخدم `ColorScheme` و `SemanticColors`
- ❌ لا تستخدم الذهبي كزر — هو للعرض فقط

## Typography — استراتيجية الخطوط

الخط الأساسي هو خط النظام (System Default) بتدرجات أوزان موحدة. نمط طباعي صارم: لا أكثر من 3 أحجام في الشاشة الواحدة، لا أكثر من وزنين.

### هرمية النصوص

| المستوى | القياس | الوزن | الاستخدام |
|---------|--------|-------|-----------|
| `hero` | 36px | 700 | الأرقام المالية الكبيرة في بطاقة الرصيد الرئيسية |
| `h1` | 28px | 700 | عنوان الشاشة |
| `h2` | 22px | 600 | عنوان القسم |
| `h3` | 18px | 600 | AppScreenHeader، عنوان البطاقة |
| `body` | 15px | 400 | النص الأساسي، المحتوى |
| `body-sm` | 13px | 400 | نص ثانوي، أوصاف |
| `caption` | 11px | 400 | بيانات وصفية، تسميات صغيرة |
| `label` | 13px | 500 | تسميات الأزرار الصغيرة، رقائق |
| `button` | 16px | 500 | تسميات الأزرار |
| `mono` | 15px | 600 | أرقام مالية (tabular figures) |
| `code` | 13px | 400 | أكواد، مفاتيح API، سجلات النظام |

### قواعد النصوص

- ✅ استخدم `TypographyTokens.xxx(color)` لكل النصوص
- ✅ استخدم `withValues(alpha: opSecondary)` للتدرج — لا تكتب اللون مبعثراً
- ❌ لا تستخدم `TextStyle()` مباشر — استخدم التوكنز
- ❌ لا تستخدم أكثر من 3 أحجام خط في الشاشة الواحدة

## Layout — نظام المسافات

شبكة 8-نقاط. كل مسافة بين العناصر هي من مضاعفات الـ 4.

```
xxs:2  xs:4  sm:8  md:12  base:16  lg:24  xl:32  xxl:48  xxxl:64
```

### الزوايا المدورة

```
sm:8  md:12  lg:14  xl:16  xxl:24  badge:12  full:999
```

### قواعد المسافات

- ✅ استخدم `SpacingTokens.xxx` لكل padding/margin/gap
- ✅ البطاقات تستخدم `radiusMd` (12px)
- ✅ الأزرار تستخدم `radiusMd` (12px)
- ✅ الحقول تستخدم `radiusMd` (12px)
- ❌ لا تستخدم `EdgeInsets.all(16)` مبعثر — استخدم `SpacingTokens.base`

## Components — مكونات موحدة

### AppButton (`design/widgets/app_button.dart`)
الزر الوحيد المسموح به في التطبيق. 5 أنماط:
- `primary`: أزرق صلب — للإجراء الرئيسي الوحيد في الشاشة
- `secondary`: شفاف مع حدود زرقاء — للإجراءات الثانوية
- `outline`: حدود فقط — للإجراءات الثلاثية
- `text`: نص فقط بدون حدود — للروابط
- `danger`: أحمر — للتدمير (حذف، إيقاف طارئ)

المعاملات: `label`, `onPressed`, `variant`, `isLoading`, `icon`, `isFullWidth`

### AppCard (`design/widgets/app_card.dart`)
البطاقة الوحيدة المسموح بها. لها `onTap` اختياري للبطاقات التفاعلية.

### StatusBadge (`design/widgets/status_badge.dart`)
الشارة الوحيدة المسموح بها. 4 أنماط: `success`, `warning`, `error`, `info`.

### TradingToggleButton (`design/widgets/trading_toggle_button.dart`)
الزر الوحيد لتفعيل/تعطيل التداول. وضعان:
- `self` mode: المستخدم يبدل تداوله
- `admin` mode: الأدمن يبدل تداول مستخدم آخر (بـ `targetUserId`)

### LoadingShimmer (`design/widgets/loading_shimmer.dart`)
مؤشر التحميل الوحيد. `itemCount` + `itemHeight`.

### ErrorState (`design/widgets/error_state.dart`)
شاشة الخطأ الوحيدة. `message` + `onRetry`.

### AppScreenHeader (`design/widgets/app_screen_header.dart`)
الـ Header الوحيد. `title` + `showBack` + `padding`.

### AppSnackbar (`design/widgets/app_snackbar.dart`)
الإشعار السفلي الوحيد. `message` + `type` (success/error/warning/info).

## Do's and Don'ts — المحظورات

### ✅ افعل

- استخدم `AppButton` لكل زر في التطبيق
- استخدم `AppCard` لكل بطاقة — لا `Container(borderRadius)`
- استخدم `TypographyTokens` لكل النصوص — لا `TextStyle()`
- استخدم `SpacingTokens` لكل المسافات — لا `EdgeInsets` بأرقام عشوائية
- استخدم `StatusBadge` لكل شارة حالة — لا تبني chips يدوياً
- استخدم `LoadingShimmer` للتحميل — لا `CircularProgressIndicator` منفرد
- استخدم `ErrorState` للأخطاء — لا رسائل نصية مبعثرة
- استخدم `AppScreenHeader` للعناوين — لا `AppBar` خام
- استخدم `AppSnackbar` للإشعارات — لا `ScaffoldMessenger` مباشر
- استخدم `SemanticColors.positive` للأرباح و `negative` للخسائر
- اعرض حالة فارغة واضحة عندما لا توجد بيانات

### ❌ لا تفعل

- لا تستخدم `ElevatedButton`، `TextButton`، `OutlinedButton` مباشر
- لا تستخدم `Container(borderRadius)` لبناء بطاقات — استخدم `AppCard`
- لا تستخدم `TextStyle(...)` مباشر — استخدم `TypographyTokens`
- لا تستخدم `EdgeInsets.all(12)` أو `EdgeInsets.symmetric(vertical: 8)` عشوائي
- لا تستخدم أكثر من لون تفاعلي واحد في الشاشة (الأزرق فقط)
- لا تستخدم الذهبي للتفاعل — هو للعرض فقط
- لا تستخدم `Color(0xFF...)` مباشر — استخدم `ColorScheme` و `SemanticColors`
- لا تستخدم أكثر من 3 أحجام خط في الشاشة الواحدة
- لا تستخدم أكثر من وزنين خط في الشاشة الواحدة
- لا تترك الشاشة فارغة عند عدم وجود بيانات — استخدم empty state
- لا تترك الزر بدون مؤشر تحميل أثناء العمليات غير المتزامنة
