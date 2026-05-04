import 'package:flutter/material.dart';
import '../../tokens/color_tokens.dart';

/// Soft Pastel Light Colors — ألوان ناعمة للوضع الفاتح
class SoftPastelLightColors implements ColorTokens {
  // ─── Brand ──────────────────────────────────────
  @override
  Color get primary => const Color(0xFFA8B4FF); // periwinkle
  @override
  Color get primaryDark => const Color(0xFF8B9AE8);
  @override
  Color get primaryLight => const Color(0xFFC4CEFF);
  @override
  Color get secondary => const Color(0xFFC4B5FD); // lavender
  @override
  Color get accent => const Color(0xFFFFD966); // butter yellow

  // ─── Semantic ──────────────────────────────────
  @override
  Color get success => const Color(0xFF7ED4A6); // mint
  @override
  Color get successLight => const Color(0xFFB8E8CC);
  @override
  Color get warning => const Color(0xFFFFD966);
  @override
  Color get error => const Color(0xFFFF8C8C); // salmon
  @override
  Color get errorLight => const Color(0xFFFFB8B8);
  @override
  Color get info => const Color(0xFF7DD3FC); // sky blue

  // ─── Surface ───────────────────────────────────
  @override
  Color get background => const Color(0xFFF5F3F0); // warm bone
  @override
  Color get bgSecondary => const Color(0xFFEDEAE5);
  @override
  Color get bgTertiary => const Color(0xFFE5E1DB);
  @override
  Color get card => const Color(0xFFFFFFFF);
  @override
  Color get elevated => const Color(0xFFFFFFFF);

  // ─── Text ───────────────────────────────────────
  @override
  Color get text => const Color(0xFF1A1A1A); // charcoal
  @override
  Color get textSecondary => const Color(0xFF6B6B6B);
  @override
  Color get textTertiary => const Color(0xFF999999);

  // ─── Financial ────────────────────────────────
  @override
  Color get positive => const Color(0xFF7ED4A6); // mint
  @override
  Color get negative => const Color(0xFFFF8C8C); // salmon

  // ─── Border ────────────────────────────────────
  @override
  Color get border => const Color(0xFFE0DCD6);
  @override
  Color get borderLight => const Color(0xFFEDEAE5);

  // ─── Gradients ──────────────────────────────────
  @override
  List<Color> get gradientPrimary => [
    const Color(0xFFA8B4FF),
    const Color(0xFFC4B5FD),
  ];
  @override
  List<Color> get gradientAccent => [
    const Color(0xFFFFD966),
    const Color(0xFFFFB866),
  ];
  @override
  List<Color> get gradientSuccess => [
    const Color(0xFF7ED4A6),
    const Color(0xFF5BBF8A),
  ];
  @override
  List<Color> get gradientDark => [
    const Color(0xFF2A2A2A),
    const Color(0xFF1A1A1A),
  ];
  @override
  List<Color> get gradientCard => [
    const Color(0xFFFFFFFF),
    const Color(0xFFF9F7F4),
  ];
}

/// Soft Pastel Dark Colors — ألوان ناعمة للوضع الداكن
class SoftPastelDarkColors implements ColorTokens {
  // ─── Brand ──────────────────────────────────────
  @override
  Color get primary => const Color(0xFFA8B4FF); // periwinkle
  @override
  Color get primaryDark => const Color(0xFF8B9AE8);
  @override
  Color get primaryLight => const Color(0xFFC4CEFF);
  @override
  Color get secondary => const Color(0xFFC4B5FD); // lavender
  @override
  Color get accent => const Color(0xFFFFD966); // butter yellow

  // ─── Semantic ──────────────────────────────────
  @override
  Color get success => const Color(0xFF7ED4A6); // mint
  @override
  Color get successLight => const Color(0xFF4A9E72);
  @override
  Color get warning => const Color(0xFFFFD966);
  @override
  Color get error => const Color(0xFFFF8C8C); // salmon
  @override
  Color get errorLight => const Color(0xFFD46666);
  @override
  Color get info => const Color(0xFF7DD3FC); // sky blue

  // ─── Surface ───────────────────────────────────
  @override
  Color get background => const Color(0xFF1A1A1A); // deep charcoal
  @override
  Color get bgSecondary => const Color(0xFF242424);
  @override
  Color get bgTertiary => const Color(0xFF2A2A2A);
  @override
  Color get card => const Color(0xFF242424);
  @override
  Color get elevated => const Color(0xFF2A2A2A);

  // ─── Text ───────────────────────────────────────
  @override
  Color get text => const Color(0xFFF0F0F0);
  @override
  Color get textSecondary => const Color(0xFF999999);
  @override
  Color get textTertiary => const Color(0xFF666666);

  // ─── Financial ─────────────────────────────────
  @override
  Color get positive => const Color(0xFF7ED4A6); // mint
  @override
  Color get negative => const Color(0xFFFF8C8C); // salmon

  // ─── Border ────────────────────────────────────
  @override
  Color get border => const Color(0xFF333333);
  @override
  Color get borderLight => const Color(0xFF2A2A2A);

  // ─── Gradients ──────────────────────────────────
  @override
  List<Color> get gradientPrimary => [
    const Color(0xFFA8B4FF).withValues(alpha: 0.15),
    const Color(0xFFC4B5FD).withValues(alpha: 0.08),
  ];
  @override
  List<Color> get gradientAccent => [
    const Color(0xFFFFD966).withValues(alpha: 0.15),
    const Color(0xFFFFB866).withValues(alpha: 0.08),
  ];
  @override
  List<Color> get gradientSuccess => [
    const Color(0xFF7ED4A6).withValues(alpha: 0.15),
    const Color(0xFF5BBF8A).withValues(alpha: 0.08),
  ];
  @override
  List<Color> get gradientDark => [
    const Color(0xFF242424),
    const Color(0xFF1A1A1A),
  ];
  @override
  List<Color> get gradientCard => [
    const Color(0xFF2A2A2A),
    const Color(0xFF242424),
  ];
}
