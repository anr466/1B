import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Midnight Ocean Dark Colors — أزرق بحري غامق
class MidnightOceanDarkColors implements ColorTokens {
  const MidnightOceanDarkColors();

  @override
  Color get primary => const Color(0xFF3B82F6);
  @override
  Color get primaryDark => const Color(0xFF0284C7);
  @override
  Color get primaryLight => const Color(0xFF60A5FA);
  @override
  Color get secondary => const Color(0xFF2563EB);
  @override
  Color get accent => const Color(0xFF0284C7);

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
  Color get background => const Color(0xFF060B16);
  @override
  Color get bgSecondary => const Color(0xFF0D1628);
  @override
  Color get bgTertiary => const Color(0xFF13213A);
  @override
  Color get card => const Color(0xFF18304E);
  @override
  Color get elevated => const Color(0xFF214064);

  @override
  Color get text => const Color(0xFFFFFFFF);
  @override
  Color get textSecondary => const Color(0xFFA4B4C8);
  @override
  Color get textTertiary => const Color(0xFF7488A0);

  // ─── Financial ────────────────────────────────────
  @override
  Color get positive => const Color(0xFF10B981);
  @override
  Color get negative => const Color(0xFFEF4444);

  @override
  Color get border => const Color(0xFF27496E);
  @override
  Color get borderLight => const Color(0xFF35618C);

  @override
  List<Color> get gradientPrimary => const [
    Color(0xFF3B82F6),
    Color(0xFF2563EB),
  ];
  @override
  List<Color> get gradientAccent => const [
    Color(0xFF0284C7),
    Color(0xFF2563EB),
  ];
  @override
  List<Color> get gradientSuccess => const [
    Color(0xFF10B981),
    Color(0xFF059669),
  ];
  @override
  List<Color> get gradientDark => const [Color(0xFF10203A), Color(0xFF060B16)];
  @override
  List<Color> get gradientCard => const [Color(0xFF193455), Color(0xFF0E1A2F)];
}

/// Midnight Ocean Light Colors
class MidnightOceanLightColors implements ColorTokens {
  const MidnightOceanLightColors();

  @override
  Color get primary => const Color(0xFF1D4ED8);
  @override
  Color get primaryDark => const Color(0xFF1E40AF);
  @override
  Color get primaryLight => const Color(0xFF3B82F6);
  @override
  Color get secondary => const Color(0xFF2563EB);
  @override
  Color get accent => const Color(0xFF0284C7);

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
  Color get background => const Color(0xFFF4F7FC);
  @override
  Color get bgSecondary => const Color(0xFFE8EEF8);
  @override
  Color get bgTertiary => const Color(0xFFD7E1F2);
  @override
  Color get card => const Color(0xFFFFFFFF);
  @override
  Color get elevated => const Color(0xFFF7F9FD);

  @override
  Color get text => const Color(0xFF1E3A66);
  @override
  Color get textSecondary => const Color(0xFF475569);
  @override
  Color get textTertiary => const Color(0xFF64748B);

  // ─── Financial ────────────────────────────────────
  @override
  Color get positive => const Color(0xFF059669);
  @override
  Color get negative => const Color(0xFFDC2626);

  @override
  Color get border => const Color(0xFFBAC8E2);
  @override
  Color get borderLight => const Color(0xFFDCE4F2);

  @override
  List<Color> get gradientPrimary => const [
    Color(0xFF1D4ED8),
    Color(0xFF2563EB),
  ];
  @override
  List<Color> get gradientAccent => const [
    Color(0xFF0284C7),
    Color(0xFF1D4ED8),
  ];
  @override
  List<Color> get gradientSuccess => const [
    Color(0xFF10B981),
    Color(0xFF059669),
  ];
  @override
  List<Color> get gradientDark => const [Color(0xFFE8EEF8), Color(0xFFF4F7FC)];
  @override
  List<Color> get gradientCard => const [Color(0xFFFFFFFF), Color(0xFFF7F9FD)];
}
