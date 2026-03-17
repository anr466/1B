import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Obsidian Titanium Dark Colors — أسود احترافي مستوحى من شعار 1B
class ObsidianTitaniumDarkColors implements ColorTokens {
  const ObsidianTitaniumDarkColors();

  @override
  Color get primary => const Color(0xFF6B9FD4);
  @override
  Color get primaryDark => const Color(0xFF4A7BB0);
  @override
  Color get primaryLight => const Color(0xFF9AC2E8);
  @override
  Color get secondary => const Color(0xFFDFD0AA);
  @override
  Color get accent => const Color(0xFFF0D89E);

  @override
  Color get success => const Color(0xFF22C55E);
  @override
  Color get successLight => const Color(0xFF4ADE80);
  @override
  Color get warning => const Color(0xFFF59E0B);
  @override
  Color get error => const Color(0xFFEF4444);
  @override
  Color get errorLight => const Color(0xFFF87171);
  @override
  Color get info => const Color(0xFF7FA4D8);

  @override
  Color get background => const Color(0xFF080C14);
  @override
  Color get bgSecondary => const Color(0xFF101824);
  @override
  Color get bgTertiary => const Color(0xFF182336);
  @override
  Color get card => const Color(0xFF1C2840);
  @override
  Color get elevated => const Color(0xFF24334E);

  @override
  Color get text => const Color(0xFFF8FAFC);
  @override
  Color get textSecondary => const Color(0xFFBCC8D8);
  @override
  Color get textTertiary => const Color(0xFF8899AE);

  // ─── Financial ────────────────────────────────────
  @override
  Color get positive => const Color(0xFF22C55E);
  @override
  Color get negative => const Color(0xFFEF4444);

  @override
  Color get border => const Color(0xFF334D6E);
  @override
  Color get borderLight => const Color(0xFF456080);

  @override
  List<Color> get gradientPrimary => const [
    Color(0xFF9AC2E8),
    Color(0xFF5A8DC0),
  ];
  @override
  List<Color> get gradientAccent => const [
    Color(0xFFF2DEB0),
    Color(0xFFC49A52),
  ];
  @override
  List<Color> get gradientSuccess => const [
    Color(0xFF22C55E),
    Color(0xFF16A34A),
  ];
  @override
  List<Color> get gradientDark => const [Color(0xFF1C2840), Color(0xFF080C14)];
  @override
  List<Color> get gradientCard => const [Color(0xFF24334E), Color(0xFF101824)];
}

/// Obsidian Titanium Light Colors — انعكاس الألوان لنفس الهوية
class ObsidianTitaniumLightColors implements ColorTokens {
  const ObsidianTitaniumLightColors();

  @override
  Color get primary => const Color(0xFF2E4A73);
  @override
  Color get primaryDark => const Color(0xFF1D3557);
  @override
  Color get primaryLight => const Color(0xFF4B6A98);
  @override
  Color get secondary => const Color(0xFF6B7C94);
  @override
  Color get accent => const Color(0xFF9C7840);

  @override
  Color get success => const Color(0xFF16A34A);
  @override
  Color get successLight => const Color(0xFF22C55E);
  @override
  Color get warning => const Color(0xFFD97706);
  @override
  Color get error => const Color(0xFFDC2626);
  @override
  Color get errorLight => const Color(0xFFEF4444);
  @override
  Color get info => const Color(0xFF4F6F98);

  @override
  Color get background => const Color(0xFFF6F8FC);
  @override
  Color get bgSecondary => const Color(0xFFEAF0F7);
  @override
  Color get bgTertiary => const Color(0xFFDDE6F1);
  @override
  Color get card => const Color(0xFFFFFFFF);
  @override
  Color get elevated => const Color(0xFFF8FAFD);

  @override
  Color get text => const Color(0xFF111827);
  @override
  Color get textSecondary => const Color(0xFF475569);
  @override
  Color get textTertiary => const Color(0xFF64748B);

  // ─── Financial ────────────────────────────────────
  @override
  Color get positive => const Color(0xFF16A34A);
  @override
  Color get negative => const Color(0xFFDC2626);

  @override
  Color get border => const Color(0xFFCBD5E1);
  @override
  Color get borderLight => const Color(0xFFDDE5EF);

  @override
  List<Color> get gradientPrimary => const [
    Color(0xFF4B6A98),
    Color(0xFF2E4A73),
  ];
  @override
  List<Color> get gradientAccent => const [
    Color(0xFFE6D2AA),
    Color(0xFF9C7840),
  ];
  @override
  List<Color> get gradientSuccess => const [
    Color(0xFF22C55E),
    Color(0xFF16A34A),
  ];
  @override
  List<Color> get gradientDark => const [Color(0xFFEAF0F7), Color(0xFFF6F8FC)];
  @override
  List<Color> get gradientCard => const [Color(0xFFFFFFFF), Color(0xFFF8FAFD)];
}
