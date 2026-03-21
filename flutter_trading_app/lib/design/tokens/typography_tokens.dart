import 'package:flutter/material.dart';

/// Typography Tokens — أنماط النصوص الموحدة
/// تصميم صافي — لا يعتمد على أي منطق أعمال
class TypographyTokens {
  TypographyTokens._();

  static TextStyle _baseTextStyle() => const TextStyle();

  // ─── Hero — الأرقام المالية الكبيرة ─────────────
  static TextStyle hero(Color color) => _baseTextStyle().copyWith(
    fontSize: 36,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.15,
    color: color,
    fontFeatures: const [FontFeature.tabularFigures()],
  );

  // ─── Headings ───────────────────────────────────
  static TextStyle h1(Color color) => _baseTextStyle().copyWith(
    fontSize: 28,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.3,
    color: color,
  );

  static TextStyle h2(Color color) => _baseTextStyle().copyWith(
    fontSize: 22,
    fontWeight: FontWeight.w600,
    color: color,
  );

  static TextStyle h3(Color color) => _baseTextStyle().copyWith(
    fontSize: 18,
    fontWeight: FontWeight.w600,
    color: color,
  );

  static TextStyle h4(Color color) => _baseTextStyle().copyWith(
    fontSize: 15,
    fontWeight: FontWeight.w600,
    letterSpacing: 0,
    color: color,
  );

  // ─── Body ───────────────────────────────────────
  static TextStyle body(Color color) => _baseTextStyle().copyWith(
    fontSize: 15,
    fontWeight: FontWeight.w400,
    height: 1.55,
    color: color,
  );

  static TextStyle bodySmall(Color color) => _baseTextStyle().copyWith(
    fontSize: 13,
    fontWeight: FontWeight.w400,
    height: 1.45,
    color: color,
  );

  // ─── Caption & Label ────────────────────────────
  static TextStyle caption(Color color) => _baseTextStyle().copyWith(
    fontSize: 11,
    fontWeight: FontWeight.w400,
    height: 1.35,
    color: color,
  );

  static TextStyle label(Color color) => _baseTextStyle().copyWith(
    fontSize: 13,
    fontWeight: FontWeight.w500,
    letterSpacing: 0,
    color: color,
  );

  // ─── Button ─────────────────────────────────────
  static TextStyle button(Color color) => _baseTextStyle().copyWith(
    fontSize: 16,
    fontWeight: FontWeight.w500,
    color: color,
  );

  // ─── Monospace for numbers ──────────────────────
  static TextStyle mono(Color color, {double fontSize = 15}) => _baseTextStyle().copyWith(
    fontSize: fontSize,
    fontWeight: FontWeight.w600,
    letterSpacing: 0,
    color: color,
    fontFeatures: const [FontFeature.tabularFigures()],
  );

  // ─── Semantic Opacity Tiers ─────────────────────
  /// Primary — محتوى رئيسي (alpha 1.0)
  static const double opPrimary = 1.0;
  /// Secondary — نصوص ثانوية، عناوين (alpha 0.55)
  static const double opSecondary = 0.55;
  /// Tertiary — ملاحظات، تسميات معتمة (alpha 0.35)
  static const double opTertiary = 0.35;
  /// Disabled — معطّل، غير نشط (alpha 0.25)
  static const double opDisabled = 0.25;

  // ─── Overline — section labels (caps, muted) ───
  static TextStyle overline(Color color) => _baseTextStyle().copyWith(
    fontSize: 11,
    fontWeight: FontWeight.w600,
    letterSpacing: 0,
    color: color,
  );

  // ─── Code ───────────────────────────────────────
  static TextStyle code(Color color) => TextStyle(
    fontFamily: 'monospace',
    fontSize: 13,
    fontWeight: FontWeight.w400,
    color: color,
    height: 1.4,
  );
}
