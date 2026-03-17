import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Skin Interface — العقد الذي يلتزم به كل skin
/// تصميم صافي — لا يعتمد على أي منطق أعمال
abstract class SkinInterface {
  String get name;
  String get displayNameAr;
  String get displayNameEn;

  ColorTokens get lightColors;
  ColorTokens get darkColors;

  ThemeData buildLightTheme();
  ThemeData buildDarkTheme();
}
