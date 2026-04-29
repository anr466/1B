# Skill: add-flutter-screen
# إضافة شاشة Flutter جديدة

## Structure
- أنشئ `lib/features/{feature_name}/{feature_name}_screen.dart`
- استخدم Riverpod لـ state management
- استخدم go_router للملاحة
- **CRITICAL**: لا تستخدم `Scaffold` في الشاشة — `ShellRoute` يوفر الـ Scaffold
- استخدم `DesignTokens` من `lib/design/tokens/` للتنسيق
- اسحب الـ providers من `lib/core/providers/`

## Verification
```bash
cd flutter_trading_app && flutter analyze
```

## Gotchas
- Admin actions تحتاج biometric gate (`biometricServiceProvider`)
- Admin tab مخفي إذا `!isAdmin`
- الثيمات: `minimalist_ui` و `soft_pastel` في `lib/design/skins/`
