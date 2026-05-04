import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Violet Brand Dark Colors — الثيم الافتراضي (بنفسجي)
class VioletBrandDarkColors implements ColorTokens {
  const VioletBrandDarkColors();

  // ─── Brand ──────────────────────────────────────
  @override
  Color get primary => const Color(0xFF8B5CF6);
  @override
  Color get primaryDark => const Color(0xFF7C3AED);
  @override
  Color get primaryLight => const Color(0xFFA78BFA);
  @override
  Color get secondary => const Color(0xFFEC4899);
  @override
  Color get accent => const Color(0xFF06B6D4);

  // ─── Semantic ───────────────────────────────────
  @override
  Color get success => const Color(0xFF10B981);
  @override
  Color get successLight => const Color(0xFF34D399);
  @override
  Color get warning => const Color(0xFFF59E0B);
  @override
  Color get error => const Color(0xFFEF4444);
  @override
  Color get errorLight => const Color(0xFFF87171);
  @override
  Color get info => const Color(0xFF60A5FA);

  // ─── Surface ────────────────────────────────────
  @override
  Color get background => const Color(0xFF120E1D);
  @override
  Color get bgSecondary => const Color(0xFF1A1428);
  @override
  Color get bgTertiary => const Color(0xFF231B35);
  @override
  Color get card => const Color(0xFF2B2240);
  @override
  Color get elevated => const Color(0xFF34294C);

  // ─── Text ───────────────────────────────────────
  @override
  Color get text => const Color(0xFFFFFFFF);
  @override
  Color get textSecondary => const Color(0xFFB0B0BC);
  @override
  Color get textTertiary => const Color(0xFF7E7E90);

  // ─── Financial ────────────────────────────────────
  @override
  Color get positive => const Color(0xFF10B981);
  @override
  Color get negative => const Color(0xFFEF4444);

  // ─── Border ─────────────────────────────────────
  @override
  Color get border => const Color(0xFF4A3C63);
  @override
  Color get borderLight => const Color(0xFF5E4F7A);

  // ─── Gradients ──────────────────────────────────
  @override
  List<Color> get gradientPrimary => const [
    Color(0xFF8B5CF6),
    Color(0xFFEC4899),
  ];
  @override
  List<Color> get gradientAccent => const [
    Color(0xFF06B6D4),
    Color(0xFF8B5CF6),
  ];
  @override
  List<Color> get gradientSuccess => const [
    Color(0xFF10B981),
    Color(0xFF059669),
  ];
  @override
  List<Color> get gradientDark => const [Color(0xFF2A2140), Color(0xFF120E1D)];
  @override
  List<Color> get gradientCard => const [Color(0xFF33274D), Color(0xFF1A1428)];
}

/// Violet Brand Light Colors
class VioletBrandLightColors implements ColorTokens {
  const VioletBrandLightColors();

  @override
  Color get primary => const Color(0xFF8B5CF6);
  @override
  Color get primaryDark => const Color(0xFF7C3AED);
  @override
  Color get primaryLight => const Color(0xFFA78BFA);
  @override
  Color get secondary => const Color(0xFFEC4899);
  @override
  Color get accent => const Color(0xFF06B6D4);

  @override
  Color get success => const Color(0xFF059669);
  @override
  Color get successLight => const Color(0xFF34D399);
  @override
  Color get warning => const Color(0xFFD97706);
  @override
  Color get error => const Color(0xFFDC2626);
  @override
  Color get errorLight => const Color(0xFFF87171);
  @override
  Color get info => const Color(0xFF2563EB);

  @override
  Color get background => const Color(0xFFFCFAFF);
  @override
  Color get bgSecondary => const Color(0xFFF4EEFF);
  @override
  Color get bgTertiary => const Color(0xFFE9E0FF);
  @override
  Color get card => const Color(0xFFFFFFFF);
  @override
  Color get elevated => const Color(0xFFF8F3FF);

  @override
  Color get text => const Color(0xFF1A1F3A);
  @override
  Color get textSecondary => const Color(0xFF5A6277);
  @override
  Color get textTertiary => const Color(0xFF6B7280);

  // ─── Financial ────────────────────────────────────
  @override
  Color get positive => const Color(0xFF059669);
  @override
  Color get negative => const Color(0xFFDC2626);

  @override
  Color get border => const Color(0xFFD8CCF2);
  @override
  Color get borderLight => const Color(0xFFE8DFFD);

  @override
  List<Color> get gradientPrimary => const [
    Color(0xFF8B5CF6),
    Color(0xFFEC4899),
  ];
  @override
  List<Color> get gradientAccent => const [
    Color(0xFF06B6D4),
    Color(0xFF8B5CF6),
  ];
  @override
  List<Color> get gradientSuccess => const [
    Color(0xFF10B981),
    Color(0xFF059669),
  ];
  @override
  List<Color> get gradientDark => const [Color(0xFFF4EEFF), Color(0xFFFCFAFF)];
  @override
  List<Color> get gradientCard => const [Color(0xFFFFFFFF), Color(0xFFF8F3FF)];
}
