import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Arctic Frost Dark Colors — أبيض ثلجي (dark mode variant)
class ArcticFrostDarkColors implements ColorTokens {
  const ArcticFrostDarkColors();

  @override
  Color get primary => const Color(0xFFB8C0CC);
  @override
  Color get primaryDark => const Color(0xFF8E99A8);
  @override
  Color get primaryLight => const Color(0xFFDCE2EA);
  @override
  Color get secondary => const Color(0xFF8F99A6);
  @override
  Color get accent => const Color(0xFFC5D4E6);

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
  Color get background => const Color(0xFF161A20);
  @override
  Color get bgSecondary => const Color(0xFF1F242C);
  @override
  Color get bgTertiary => const Color(0xFF292F38);
  @override
  Color get card => const Color(0xFF333A45);
  @override
  Color get elevated => const Color(0xFF3D4652);

  @override
  Color get text => const Color(0xFFF1F5F9);
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
  Color get border => const Color(0xFF566273);
  @override
  Color get borderLight => const Color(0xFF6D7C8F);

  @override
  List<Color> get gradientPrimary => const [
    Color(0xFFB8C0CC),
    Color(0xFF8F99A6),
  ];
  @override
  List<Color> get gradientAccent => const [
    Color(0xFFC5D4E6),
    Color(0xFFB8C0CC),
  ];
  @override
  List<Color> get gradientSuccess => const [
    Color(0xFF10B981),
    Color(0xFF059669),
  ];
  @override
  List<Color> get gradientDark => const [Color(0xFF252B33), Color(0xFF161A20)];
  @override
  List<Color> get gradientCard => const [Color(0xFF353D49), Color(0xFF1F242C)];
}

/// Arctic Frost Light Colors — الوضع الفاتح الأنيق
class ArcticFrostLightColors implements ColorTokens {
  const ArcticFrostLightColors();

  @override
  Color get primary => const Color(0xFF7F8A97);
  @override
  Color get primaryDark => const Color(0xFF697483);
  @override
  Color get primaryLight => const Color(0xFFB8C0CC);
  @override
  Color get secondary => const Color(0xFF9AA5B2);
  @override
  Color get accent => const Color(0xFFC5D4E6);

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
  Color get background => const Color(0xFFF7F8FA);
  @override
  Color get bgSecondary => const Color(0xFFF0F2F5);
  @override
  Color get bgTertiary => const Color(0xFFE4E8EE);
  @override
  Color get card => const Color(0xFFFFFFFF);
  @override
  Color get elevated => const Color(0xFFF5F6F9);

  @override
  Color get text => const Color(0xFF0F172A);
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
  Color get border => const Color(0xFFCFD6DF);
  @override
  Color get borderLight => const Color(0xFFE1E6EE);

  @override
  List<Color> get gradientPrimary => const [
    Color(0xFF7F8A97),
    Color(0xFFB8C0CC),
  ];
  @override
  List<Color> get gradientAccent => const [
    Color(0xFFC5D4E6),
    Color(0xFF7F8A97),
  ];
  @override
  List<Color> get gradientSuccess => const [
    Color(0xFF10B981),
    Color(0xFF059669),
  ];
  @override
  List<Color> get gradientDark => const [Color(0xFFF0F2F5), Color(0xFFF7F8FA)];
  @override
  List<Color> get gradientCard => const [Color(0xFFFFFFFF), Color(0xFFF5F6F9)];
}
