import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';

double _contrastRatio(Color a, Color b) {
  final la = a.computeLuminance();
  final lb = b.computeLuminance();
  final hi = la > lb ? la : lb;
  final lo = la > lb ? lb : la;
  return (hi + 0.05) / (lo + 0.05);
}

Color _bestOnColor(Color background) {
  final whiteContrast = _contrastRatio(Colors.white, background);
  final blackContrast = _contrastRatio(Colors.black, background);
  return whiteContrast >= blackContrast ? Colors.white : Colors.black;
}

/// Shared theme builder — يُستخدم من جميع الـ skins لتجنب التكرار
ThemeData buildSkinTheme(ColorTokens c, Brightness brightness) {
  final isDark = brightness == Brightness.dark;
  final onPrimary = _bestOnColor(c.primary);
  final onSecondary = _bestOnColor(c.secondary);
  final onError = _bestOnColor(c.error);
  final onWarning = _bestOnColor(c.warning);

  final cs = ColorScheme(
    brightness: brightness,

    // ─── Primary ──────────────────────────────────
    primary: c.primary,
    onPrimary: onPrimary,
    primaryContainer: Color.alphaBlend(
      c.primary.withValues(alpha: isDark ? 0.18 : 0.12),
      c.background,
    ),
    onPrimaryContainer: isDark ? c.primaryLight : c.primaryDark,

    // ─── Secondary ────────────────────────────────
    secondary: c.secondary,
    onSecondary: onSecondary,
    secondaryContainer: Color.alphaBlend(
      c.secondary.withValues(alpha: isDark ? 0.18 : 0.12),
      c.background,
    ),
    onSecondaryContainer: c.secondary,

    // ─── Tertiary → warning semantic ──────────────
    tertiary: c.warning,
    onTertiary: onWarning,
    tertiaryContainer: Color.alphaBlend(
      c.warning.withValues(alpha: 0.14),
      c.background,
    ),
    onTertiaryContainer: c.warning,

    // ─── Error ────────────────────────────────────
    error: c.error,
    onError: onError,
    errorContainer: Color.alphaBlend(
      c.error.withValues(alpha: 0.14),
      c.background,
    ),
    onErrorContainer: c.error,

    // ─── Surface hierarchy ────────────────────────
    surface: c.background,
    onSurface: c.text,
    onSurfaceVariant: c.textSecondary,
    surfaceContainerLowest: c.background,
    surfaceContainerLow: c.bgSecondary,
    surfaceContainer: c.bgTertiary,
    surfaceContainerHigh: c.card,
    surfaceContainerHighest: c.elevated,
    surfaceTint: Colors.transparent,

    // ─── Outline ──────────────────────────────────
    outline: c.border,
    outlineVariant: c.borderLight,

    // ─── Inverse (neutral poles derived from tokens) ─
    inversePrimary: isDark ? c.primaryLight : c.primaryDark,
    inverseSurface: isDark ? c.text.withValues(alpha: 0.92) : c.text,
    onInverseSurface: isDark ? c.background : c.card,

    // ─── Misc ─────────────────────────────────────
    shadow: Colors.black,
    scrim: Colors.black,
  );

  // ─── Semantic Colors Extension ──────────────────
  final semanticColors = SemanticColors(
    positive: c.positive,
    negative: c.negative,
    success: c.success,
    successContainer: Color.alphaBlend(
      c.success.withValues(alpha: isDark ? 0.16 : 0.12),
      c.background,
    ),
    warning: c.warning,
    warningContainer: Color.alphaBlend(
      c.warning.withValues(alpha: isDark ? 0.16 : 0.12),
      c.background,
    ),
    info: c.info,
    infoContainer: Color.alphaBlend(
      c.info.withValues(alpha: isDark ? 0.16 : 0.12),
      c.background,
    ),
  );

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: cs,
    scaffoldBackgroundColor: c.background,
    textTheme: ThemeData(brightness: brightness).textTheme.apply(
      fontFamily: 'BarlowCondensed',
      bodyColor: c.text,
      displayColor: c.text,
    ),
    extensions: [semanticColors],

    // ─── AppBar ───────────────────────────────────
    appBarTheme: AppBarTheme(
      backgroundColor: c.background,
      foregroundColor: c.text,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: true,
      surfaceTintColor: Colors.transparent,
    ),

    // ─── Card ─────────────────────────────────────
    cardTheme: CardThemeData(
      color: c.card,
      elevation: isDark ? 0 : 1,
      shadowColor: isDark
          ? Colors.transparent
          : Colors.black.withValues(alpha: 0.08),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(SpacingTokens.radiusLg),
        side: BorderSide(color: c.border, width: 1),
      ),
    ),

    // ─── Input ────────────────────────────────────
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: c.bgSecondary,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
        borderSide: BorderSide(color: c.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
        borderSide: BorderSide(color: c.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
        borderSide: BorderSide(color: c.primary, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
        borderSide: BorderSide(color: c.error),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
        borderSide: BorderSide(color: c.error, width: 2),
      ),
      labelStyle: TextStyle(color: c.textSecondary),
      hintStyle: TextStyle(color: c.textTertiary),
    ),

    // ─── Elevated Button ──────────────────────────
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: c.primary,
        foregroundColor: onPrimary,
        elevation: isDark ? 0 : 2,
        shadowColor: isDark
            ? Colors.transparent
            : c.primary.withValues(alpha: 0.25),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
        ),
        minimumSize: const Size(double.infinity, SpacingTokens.buttonHeight),
      ),
    ),

    // ─── Outlined Button ──────────────────────────
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: c.primary,
        side: BorderSide(color: c.primary),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
        ),
        minimumSize: const Size(double.infinity, SpacingTokens.buttonHeight),
      ),
    ),

    // ─── Text Button ──────────────────────────────
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: c.primary),
    ),

    // ─── Bottom Navigation ────────────────────────
    bottomNavigationBarTheme: BottomNavigationBarThemeData(
      backgroundColor: isDark ? c.card : c.elevated,
      selectedItemColor: c.primary,
      unselectedItemColor: c.textTertiary,
      type: BottomNavigationBarType.fixed,
      elevation: isDark ? 0 : 4,
    ),

    // ─── Navigation Bar (M3) ──────────────────────
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: isDark ? c.card : c.elevated,
      indicatorColor: c.primary.withValues(alpha: 0.15),
      surfaceTintColor: Colors.transparent,
    ),

    // ─── Dialog ───────────────────────────────────
    dialogTheme: DialogThemeData(
      backgroundColor: isDark ? c.elevated : c.card,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(SpacingTokens.radiusXl),
      ),
    ),

    // ─── SnackBar ─────────────────────────────────
    snackBarTheme: SnackBarThemeData(
      backgroundColor: isDark ? c.elevated : c.text,
      contentTextStyle: TextStyle(color: isDark ? c.text : c.background),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
      ),
      behavior: SnackBarBehavior.floating,
    ),

    // ─── Switch ───────────────────────────────────
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) return c.primary;
        return isDark ? c.textTertiary : c.borderLight;
      }),
      trackColor: WidgetStateProperty.resolveWith((states) {
        if (states.contains(WidgetState.selected)) {
          return c.primary.withValues(alpha: 0.35);
        }
        return isDark ? c.border : c.borderLight;
      }),
      trackOutlineColor: WidgetStateProperty.resolveWith((states) {
        return Colors.transparent;
      }),
    ),

    // ─── Chip ─────────────────────────────────────
    chipTheme: ChipThemeData(
      backgroundColor: c.bgSecondary,
      selectedColor: c.primary.withValues(alpha: 0.18),
      labelStyle: TextStyle(color: c.text),
      side: BorderSide(color: c.border),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(SpacingTokens.radiusSm),
      ),
    ),

    // ─── ProgressIndicator ────────────────────────
    progressIndicatorTheme: ProgressIndicatorThemeData(
      color: c.primary,
      linearTrackColor: c.border,
    ),

    // ─── Divider ──────────────────────────────────
    dividerTheme: DividerThemeData(color: c.border, thickness: 1),

    // ─── Tooltip ──────────────────────────────────
    tooltipTheme: TooltipThemeData(
      decoration: BoxDecoration(
        color: isDark ? c.elevated : c.text,
        borderRadius: BorderRadius.circular(SpacingTokens.radiusSm),
      ),
      textStyle: TextStyle(color: isDark ? c.text : c.background, fontSize: 12),
    ),

    // ─── ListTile ─────────────────────────────────
    listTileTheme: ListTileThemeData(
      iconColor: c.textSecondary,
      textColor: c.text,
    ),

    // ─── Icon ─────────────────────────────────────
    iconTheme: IconThemeData(color: c.textSecondary),
  );
}
