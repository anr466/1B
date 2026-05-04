import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Emerald Trading Dark Colors — أخضر زمردي
class EmeraldTradingDarkColors implements ColorTokens {
  const EmeraldTradingDarkColors();

  @override
  Color get primary => const Color(0xFF10B981);
  @override
  Color get primaryDark => const Color(0xFF059669);
  @override
  Color get primaryLight => const Color(0xFF34D399);
  @override
  Color get secondary => const Color(0xFF0D9488);
  @override
  Color get accent => const Color(0xFF34D399);

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
  Color get background => const Color(0xFF081510);
  @override
  Color get bgSecondary => const Color(0xFF0F2119);
  @override
  Color get bgTertiary => const Color(0xFF173025);
  @override
  Color get card => const Color(0xFF1E3D31);
  @override
  Color get elevated => const Color(0xFF275042);

  @override
  Color get text => const Color(0xFFFFFFFF);
  @override
  Color get textSecondary => const Color(0xFFA4B4B0);
  @override
  Color get textTertiary => const Color(0xFF748884);

  // ─── Financial ────────────────────────────────────
  @override
  Color get positive => const Color(0xFF4ADE80);
  @override
  Color get negative => const Color(0xFFEF4444);

  @override
  Color get border => const Color(0xFF2F6053);
  @override
  Color get borderLight => const Color(0xFF3E7868);

  @override
  List<Color> get gradientPrimary => const [
    Color(0xFF10B981),
    Color(0xFF0D9488),
  ];
  @override
  List<Color> get gradientAccent => const [
    Color(0xFF34D399),
    Color(0xFF10B981),
  ];
  @override
  List<Color> get gradientSuccess => const [
    Color(0xFF10B981),
    Color(0xFF059669),
  ];
  @override
  List<Color> get gradientDark => const [Color(0xFF133025), Color(0xFF081510)];
  @override
  List<Color> get gradientCard => const [Color(0xFF1E3D31), Color(0xFF0F2119)];
}

/// Emerald Trading Light Colors
class EmeraldTradingLightColors implements ColorTokens {
  const EmeraldTradingLightColors();

  @override
  Color get primary => const Color(0xFF059669);
  @override
  Color get primaryDark => const Color(0xFF047857);
  @override
  Color get primaryLight => const Color(0xFF34D399);
  @override
  Color get secondary => const Color(0xFF0D9488);
  @override
  Color get accent => const Color(0xFF34D399);

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
  Color get background => const Color(0xFFEEFCF5);
  @override
  Color get bgSecondary => const Color(0xFFD9F8E8);
  @override
  Color get bgTertiary => const Color(0xFFB7F0D3);
  @override
  Color get card => const Color(0xFFFFFFFF);
  @override
  Color get elevated => const Color(0xFFF3FCF7);

  @override
  Color get text => const Color(0xFF14532D);
  @override
  Color get textSecondary => const Color(0xFF475569);
  @override
  Color get textTertiary => const Color(0xFF64748B);

  // ─── Financial ────────────────────────────────────
  @override
  Color get positive => const Color(0xFF047857);
  @override
  Color get negative => const Color(0xFFDC2626);

  @override
  Color get border => const Color(0xFF9DE7C8);
  @override
  Color get borderLight => const Color(0xFFC9F2DD);

  @override
  List<Color> get gradientPrimary => const [
    Color(0xFF059669),
    Color(0xFF0D9488),
  ];
  @override
  List<Color> get gradientAccent => const [
    Color(0xFF34D399),
    Color(0xFF059669),
  ];
  @override
  List<Color> get gradientSuccess => const [
    Color(0xFF10B981),
    Color(0xFF059669),
  ];
  @override
  List<Color> get gradientDark => const [Color(0xFFD9F8E8), Color(0xFFEEFCF5)];
  @override
  List<Color> get gradientCard => const [Color(0xFFFFFFFF), Color(0xFFF3FCF7)];
}
