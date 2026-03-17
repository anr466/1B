import 'package:flutter/material.dart';

/// Color Tokens — abstract interface for skin colors
/// كل skin يُنفذ هذا الـ interface بألوانه الخاصة
abstract class ColorTokens {
  // ─── Brand ──────────────────────────────────────
  Color get primary;
  Color get primaryDark;
  Color get primaryLight;
  Color get secondary;
  Color get accent;

  // ─── Semantic ───────────────────────────────────
  Color get success;
  Color get successLight;
  Color get warning;
  Color get error;
  Color get errorLight;
  Color get info;

  // ─── Surface ────────────────────────────────────
  Color get background;
  Color get bgSecondary;
  Color get bgTertiary;
  Color get card;
  Color get elevated;

  // ─── Text ───────────────────────────────────────
  Color get text;
  Color get textSecondary;
  Color get textTertiary;

  // ─── Financial ─────────────────────────────────
  Color get positive;
  Color get negative;

  // ─── Border ─────────────────────────────────────
  Color get border;
  Color get borderLight;

  // ─── Gradients ──────────────────────────────────
  List<Color> get gradientPrimary;
  List<Color> get gradientAccent;
  List<Color> get gradientSuccess;
  List<Color> get gradientDark;
  List<Color> get gradientCard;
}
