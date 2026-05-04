import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Cyber Neon Dark Colors — سماوي نيون
class CyberNeonDarkColors implements ColorTokens {
  const CyberNeonDarkColors();

  @override
  Color get primary => const Color(0xFF22D3EE);
  @override
  Color get primaryDark => const Color(0xFF00C2D9);
  @override
  Color get primaryLight => const Color(0xFF67E8F9);
  @override
  Color get secondary => const Color(0xFFA855F7);
  @override
  Color get accent => const Color(0xFF14B8A6);

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
  Color get background => const Color(0xFF05050B);
  @override
  Color get bgSecondary => const Color(0xFF0D0D17);
  @override
  Color get bgTertiary => const Color(0xFF151526);
  @override
  Color get card => const Color(0xFF1D1C32);
  @override
  Color get elevated => const Color(0xFF2A2744);

  @override
  Color get text => const Color(0xFFFFFFFF);
  @override
  Color get textSecondary => const Color(0xFFACB4C0);
  @override
  Color get textTertiary => const Color(0xFF7C8498);

  // ─── Financial ────────────────────────────────────
  @override
  Color get positive => const Color(0xFF10B981);
  @override
  Color get negative => const Color(0xFFEF4444);

  @override
  Color get border => const Color(0xFF3A3A67);
  @override
  Color get borderLight => const Color(0xFF52528A);

  @override
  List<Color> get gradientPrimary => const [
    Color(0xFF22D3EE),
    Color(0xFFA855F7),
  ];
  @override
  List<Color> get gradientAccent => const [
    Color(0xFF14B8A6),
    Color(0xFF22D3EE),
  ];
  @override
  List<Color> get gradientSuccess => const [
    Color(0xFF10B981),
    Color(0xFF059669),
  ];
  @override
  List<Color> get gradientDark => const [Color(0xFF1A1730), Color(0xFF05050B)];
  @override
  List<Color> get gradientCard => const [Color(0xFF262346), Color(0xFF111122)];
}

/// Cyber Neon Light Colors
class CyberNeonLightColors implements ColorTokens {
  const CyberNeonLightColors();

  @override
  Color get primary => const Color(0xFF0E7490);
  @override
  Color get primaryDark => const Color(0xFF155E75);
  @override
  Color get primaryLight => const Color(0xFF22D3EE);
  @override
  Color get secondary => const Color(0xFF9333EA);
  @override
  Color get accent => const Color(0xFF14B8A6);

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
  Color get background => const Color(0xFFF4FBFC);
  @override
  Color get bgSecondary => const Color(0xFFE6F5F7);
  @override
  Color get bgTertiary => const Color(0xFFD3EBEE);
  @override
  Color get card => const Color(0xFFFFFFFF);
  @override
  Color get elevated => const Color(0xFFF7FBFC);

  @override
  Color get text => const Color(0xFF164E63);
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
  Color get border => const Color(0xFFB4DCE3);
  @override
  Color get borderLight => const Color(0xFFD7EBEF);

  @override
  List<Color> get gradientPrimary => const [
    Color(0xFF0E7490),
    Color(0xFF9333EA),
  ];
  @override
  List<Color> get gradientAccent => const [
    Color(0xFF14B8A6),
    Color(0xFF0E7490),
  ];
  @override
  List<Color> get gradientSuccess => const [
    Color(0xFF10B981),
    Color(0xFF059669),
  ];
  @override
  List<Color> get gradientDark => const [Color(0xFFE6F5F7), Color(0xFFF4FBFC)];
  @override
  List<Color> get gradientCard => const [Color(0xFFFFFFFF), Color(0xFFF7FBFC)];
}
