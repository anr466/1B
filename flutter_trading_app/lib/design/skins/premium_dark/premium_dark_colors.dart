import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Premium Dark — فحمي عميق + ألوان نيونية
class PremiumDarkColors implements ColorTokens {
  const PremiumDarkColors();

  // ─── Brand ──────────────────────────────────────
  @override Color get primary => const Color(0xFF448AFF);
  @override Color get primaryDark => const Color(0xFF2962FF);
  @override Color get primaryLight => const Color(0xFF82B1FF);
  @override Color get secondary => const Color(0xFF7C4DFF);
  @override Color get accent => const Color(0xFFFF4081);

  // ─── Semantic ───────────────────────────────────
  @override Color get success => const Color(0xFF00E676);
  @override Color get successLight => const Color(0xFF69F0AE);
  @override Color get warning => const Color(0xFFFF9100);
  @override Color get error => const Color(0xFFFF1744);
  @override Color get errorLight => const Color(0xFFFF5252);
  @override Color get info => const Color(0xFF448AFF);

  // ─── Surface ────────────────────────────────────
  @override Color get background => const Color(0xFF0A0E12);
  @override Color get bgSecondary => const Color(0xFF11161C);
  @override Color get bgTertiary => const Color(0xFF181E25);
  @override Color get card => const Color(0xFF11161C);
  @override Color get elevated => const Color(0xFF181E25);

  // ─── Text ───────────────────────────────────────
  @override Color get text => const Color(0xFFF8FAFC);
  @override Color get textSecondary => const Color(0xFF8A8D93);
  @override Color get textTertiary => const Color(0xFF5A5D63);

  // ─── Financial ─────────────────────────────────
  @override Color get positive => const Color(0xFF00E676);
  @override Color get negative => const Color(0xFFFF1744);

  // ─── Border ─────────────────────────────────────
  @override Color get border => const Color(0xFF1E242B);
  @override Color get borderLight => const Color(0xFF2A3038);

  // ─── Gradients ──────────────────────────────────
  @override List<Color> get gradientPrimary => [const Color(0xFF448AFF), const Color(0xFF7C4DFF)];
  @override List<Color> get gradientAccent => [const Color(0xFFFF4081), const Color(0xFFFF9100)];
  @override List<Color> get gradientSuccess => [const Color(0xFF00E676), const Color(0xFF00C853)];
  @override List<Color> get gradientDark => [const Color(0xFF0A0E12), const Color(0xFF181E25)];
  @override List<Color> get gradientCard => [const Color(0xFF11161C), const Color(0xFF181E25)];
}
