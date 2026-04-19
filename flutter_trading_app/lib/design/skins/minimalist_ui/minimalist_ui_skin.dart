import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:trading_app/design/skins/skin_interface.dart';
import 'package:trading_app/design/skins/skin_theme_builder.dart';
import 'package:trading_app/design/skins/minimalist_ui/minimalist_ui_colors.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Minimalist UI Skin — Premium Utilitarian Minimalism
///
/// Features:
/// - Warm monochrome palette (Bone/Off-white backgrounds).
/// - Ultra-flat component architecture (1px borders, no shadows).
/// - Editorial typography (Serif headers, Sans body).
class MinimalistUISkin implements SkinInterface {
  const MinimalistUISkin();

  @override
  String get name => 'minimalist_ui';
  @override
  String get displayNameAr => 'بسيط وأنيق';
  @override
  String get displayNameEn => 'Minimalist UI';

  @override
  ColorTokens get lightColors => const MinimalistUILightColors();
  @override
  ColorTokens get darkColors => const MinimalistUIDarkColors();

  @override
  ThemeData buildLightTheme() {
    final baseTheme = buildSkinTheme(lightColors, Brightness.light);
    return baseTheme.copyWith(
      // Enforce flat borders and crisp radii
      cardTheme: baseTheme.cardTheme.copyWith(
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: Color(0xFFEAEAEA), width: 1),
        ),
      ),
      // Typography adjustments for Editorial feel using Google Fonts
      textTheme: GoogleFonts.dmSansTextTheme(baseTheme.textTheme).copyWith(
        displayLarge: GoogleFonts.newsreader(
          color: const Color(0xFF111111),
          fontWeight: FontWeight.w700,
          letterSpacing: -0.02,
        ),
        headlineLarge: GoogleFonts.newsreader(
          color: const Color(0xFF111111),
          fontWeight: FontWeight.w700,
          letterSpacing: -0.02,
        ),
        labelSmall: GoogleFonts.jetBrainsMono(
          color: const Color(0xFF787774),
          letterSpacing: 0.05,
        ),
      ),
    );
  }

  @override
  ThemeData buildDarkTheme() {
    final baseTheme = buildSkinTheme(darkColors, Brightness.dark);
    return baseTheme.copyWith(
      cardTheme: baseTheme.cardTheme.copyWith(
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: Color(0xFF2A2A2A), width: 1),
        ),
      ),
      textTheme: GoogleFonts.dmSansTextTheme(baseTheme.textTheme).copyWith(
        displayLarge: GoogleFonts.newsreader(
          color: const Color(0xFFEAEAEA),
          fontWeight: FontWeight.w700,
          letterSpacing: -0.02,
        ),
        headlineLarge: GoogleFonts.newsreader(
          color: const Color(0xFFEAEAEA),
          fontWeight: FontWeight.w700,
          letterSpacing: -0.02,
        ),
        labelSmall: GoogleFonts.jetBrainsMono(
          color: const Color(0xFF999999),
          letterSpacing: 0.05,
        ),
      ),
    );
  }
}
