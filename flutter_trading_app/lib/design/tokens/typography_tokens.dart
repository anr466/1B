import 'package:flutter/material.dart';

/// Typography Tokens — أنماط النصوص الموحدة
/// تصميم صافي — لا يعتمد على أي منطق أعمال
class TypographyTokens {
  TypographyTokens._();

  static const String _fontFamily = 'BarlowCondensed';

  // ─── Hero — الأرقام المالية الكبيرة ─────────────
  static TextStyle hero(Color color) => TextStyle(
    fontSize: 36,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.15,
    color: color,
    fontFeatures: const [FontFeature.tabularFigures()],
  );

  // ─── Headings ───────────────────────────────────
  static TextStyle h1(Color color) => TextStyle(
    fontFamily: _fontFamily,
    fontSize: 28,
    fontWeight: FontWeight.w700,
    letterSpacing: -0.5,
    color: color,
  );

  static TextStyle h2(Color color) => TextStyle(
    fontFamily: _fontFamily,
    fontSize: 22,
    fontWeight: FontWeight.w600,
    color: color,
  );

  static TextStyle h3(Color color) => TextStyle(
    fontFamily: _fontFamily,
    fontSize: 18,
    fontWeight: FontWeight.w600,
    color: color,
  );

  static TextStyle h4(Color color) => TextStyle(
    fontFamily: _fontFamily,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    color: color,
  );

  // ─── Body ───────────────────────────────────────
  static TextStyle body(Color color) => TextStyle(
    fontFamily: _fontFamily,
    fontSize: 15,
    fontWeight: FontWeight.w400,
    height: 1.5,
    color: color,
  );

  static TextStyle bodySmall(Color color) => TextStyle(
    fontFamily: _fontFamily,
    fontSize: 13,
    fontWeight: FontWeight.w400,
    color: color,
  );

  // ─── Caption & Label ────────────────────────────
  static TextStyle caption(Color color) => TextStyle(
    fontFamily: _fontFamily,
    fontSize: 11,
    fontWeight: FontWeight.w400,
    color: color,
  );

  static TextStyle label(Color color) => TextStyle(
    fontFamily: _fontFamily,
    fontSize: 13,
    fontWeight: FontWeight.w500,
    letterSpacing: 0.5,
    color: color,
  );

  // ─── Button ─────────────────────────────────────
  static TextStyle button(Color color) => TextStyle(
    fontFamily: _fontFamily,
    fontSize: 16,
    fontWeight: FontWeight.w600,
    color: color,
  );

  // ─── Monospace for numbers ──────────────────────
  static TextStyle mono(Color color, {double fontSize = 15}) => TextStyle(
    fontSize: fontSize,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.1,
    color: color,
    fontFeatures: const [FontFeature.tabularFigures()],
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
