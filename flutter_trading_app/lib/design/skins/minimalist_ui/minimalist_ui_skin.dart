import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:trading_app/design/skins/skin_interface.dart';
import 'package:trading_app/design/skins/skin_theme_builder.dart';
import 'package:trading_app/design/skins/minimalist_ui/minimalist_ui_colors.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';

/// Minimalist UI Skin — Premium Utilitarian Minimalism
///
/// Features:
/// - Warm monochrome palette (Bone/Off-white backgrounds).
/// - Ultra-flat component architecture (1px borders, no shadows).
/// - Editorial typography (Serif headers, Sans body).
/// - Muted pastel semantic colors.
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
    return _applyMinimalistOverrides(baseTheme, lightColors, Brightness.light);
  }

  @override
  ThemeData buildDarkTheme() {
    final baseTheme = buildSkinTheme(darkColors, Brightness.dark);
    return _applyMinimalistOverrides(baseTheme, darkColors, Brightness.dark);
  }

  ThemeData _applyMinimalistOverrides(
    ThemeData base,
    ColorTokens c,
    Brightness brightness,
  ) {
    final isDark = brightness == Brightness.dark;
    final primaryColor = c.primary;
    final onPrimary = isDark ? c.background : Colors.white;
    final surfaceColor = c.card;
    final borderColor = c.border;

    return base.copyWith(
      // ─── Typography (Editorial Hierarchy) ──────────
      textTheme: GoogleFonts.dmSansTextTheme(base.textTheme).copyWith(
        displayLarge: GoogleFonts.newsreader(
          color: c.text,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.02,
          height: 1.1,
        ),
        headlineLarge: GoogleFonts.newsreader(
          color: c.text,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.02,
          height: 1.15,
        ),
        labelSmall: GoogleFonts.jetBrainsMono(
          color: c.textSecondary,
          letterSpacing: 0.05,
        ),
      ),

      // ─── Cards (Flat, 1px Border, Crisp Radius) ────
      cardTheme: base.cardTheme.copyWith(
        elevation: 0,
        shadowColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
          side: BorderSide(color: borderColor, width: 1),
        ),
      ),

      // ─── Buttons (Solid Black, No Shadow) ──────────
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryColor,
          foregroundColor: onPrimary,
          elevation: 0,
          shadowColor: Colors.transparent,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(6), // Crisp, professional
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: SpacingTokens.lg,
            vertical: SpacingTokens.md,
          ),
          textStyle: GoogleFonts.dmSans(
            fontWeight: FontWeight.w600,
            letterSpacing: 0,
          ),
        ),
      ),

      // ─── Outlined Buttons ──────────────────────────
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primaryColor,
          side: BorderSide(color: primaryColor, width: 1),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(6),
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: SpacingTokens.lg,
            vertical: SpacingTokens.md,
          ),
        ),
      ),

      // ─── Text Buttons ──────────────────────────────
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primaryColor,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(4),
          ),
        ),
      ),

      // ─── Inputs (Clean, Minimal Borders) ───────────
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark ? c.bgSecondary : c.background,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: BorderSide(color: borderColor, width: 1),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: BorderSide(color: borderColor, width: 1),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(6),
          borderSide: BorderSide(color: primaryColor, width: 1.5),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: SpacingTokens.md,
          vertical: SpacingTokens.md,
        ),
      ),

      // ─── Chips / Tags (Pill, Muted Pastels) ────────
      chipTheme: ChipThemeData(
        backgroundColor: c.bgSecondary,
        selectedColor: primaryColor.withValues(alpha: 0.12),
        labelStyle: GoogleFonts.dmSans(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.05,
          color: c.text,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(999), // Pill shape
          side: BorderSide(color: borderColor, width: 0.5),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 0),
      ),

      // ─── Bottom Navigation (Flat, Minimal) ─────────
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: surfaceColor,
        selectedItemColor: primaryColor,
        unselectedItemColor: c.textTertiary,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
      ),

      // ─── Divider (Structural) ──────────────────────
      dividerTheme: DividerThemeData(
        color: borderColor,
        thickness: 1,
        space: 1,
      ),
    );
  }
}
