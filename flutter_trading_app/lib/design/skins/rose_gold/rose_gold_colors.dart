import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Rose Gold Dark Colors — وردي ذهبي
class RoseGoldDarkColors implements ColorTokens {
  const RoseGoldDarkColors();

  @override
  Color get primary => const Color(0xFFF472B6);
  @override
  Color get primaryDark => const Color(0xFFEC4899);
  @override
  Color get primaryLight => const Color(0xFFF9A8D4);
  @override
  Color get secondary => const Color(0xFFEAB308);
  @override
  Color get accent => const Color(0xFFF59E0B);

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
  Color get info => const Color(0xFF3B82F6);

  @override
  Color get background => const Color(0xFF140C11);
  @override
  Color get bgSecondary => const Color(0xFF201218);
  @override
  Color get bgTertiary => const Color(0xFF2D1A24);
  @override
  Color get card => const Color(0xFF3A2531);
  @override
  Color get elevated => const Color(0xFF4A2E3D);

  @override
  Color get text => const Color(0xFFFFFFFF);
  @override
  Color get textSecondary => const Color(0xFFB8A8B2);
  @override
  Color get textTertiary => const Color(0xFF8A7A84);

  // ─── Financial ────────────────────────────────────
  @override
  Color get positive => const Color(0xFF10B981);
  @override
  Color get negative => const Color(0xFFEF4444);

  @override
  Color get border => const Color(0xFF6A4C5F);
  @override
  Color get borderLight => const Color(0xFF846178);

  @override
  List<Color> get gradientPrimary => const [
    Color(0xFFF472B6),
    Color(0xFFEAB308),
  ];
  @override
  List<Color> get gradientAccent => const [
    Color(0xFFF59E0B),
    Color(0xFFF472B6),
  ];
  @override
  List<Color> get gradientSuccess => const [
    Color(0xFF10B981),
    Color(0xFF059669),
  ];
  @override
  List<Color> get gradientDark => const [Color(0xFF2A1720), Color(0xFF140C11)];
  @override
  List<Color> get gradientCard => const [Color(0xFF3A2531), Color(0xFF201218)];
}

/// Rose Gold Light Colors
class RoseGoldLightColors implements ColorTokens {
  const RoseGoldLightColors();

  @override
  Color get primary => const Color(0xFFEC4899);
  @override
  Color get primaryDark => const Color(0xFFDB2777);
  @override
  Color get primaryLight => const Color(0xFFF9A8D4);
  @override
  Color get secondary => const Color(0xFFD97706);
  @override
  Color get accent => const Color(0xFFEC4899);

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
  Color get background => const Color(0xFFFFF7F5);
  @override
  Color get bgSecondary => const Color(0xFFFDEEEA);
  @override
  Color get bgTertiary => const Color(0xFFFADFD6);
  @override
  Color get card => const Color(0xFFFFFFFF);
  @override
  Color get elevated => const Color(0xFFFFF3EF);

  @override
  Color get text => const Color(0xFF4A1F24);
  @override
  Color get textSecondary => const Color(0xFF6B5C5E);
  @override
  Color get textTertiary => const Color(0xFF8A7F86);

  // ─── Financial ────────────────────────────────────
  @override
  Color get positive => const Color(0xFF059669);
  @override
  Color get negative => const Color(0xFFDC2626);

  @override
  Color get border => const Color(0xFFF1B8B0);
  @override
  Color get borderLight => const Color(0xFFF8D8D2);

  @override
  List<Color> get gradientPrimary => const [
    Color(0xFFEC4899),
    Color(0xFFD97706),
  ];
  @override
  List<Color> get gradientAccent => const [
    Color(0xFFEC4899),
    Color(0xFFF59E0B),
  ];
  @override
  List<Color> get gradientSuccess => const [
    Color(0xFF10B981),
    Color(0xFF059669),
  ];
  @override
  List<Color> get gradientDark => const [Color(0xFFFDEEEA), Color(0xFFFFF7F5)];
  @override
  List<Color> get gradientCard => const [Color(0xFFFFFFFF), Color(0xFFFFF3EF)];
}
