import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';
import 'package:trading_app/design/skins/skin_interface.dart';
import 'package:trading_app/design/skins/skin_theme_builder.dart';
import 'package:trading_app/design/skins/emerald_trading/emerald_trading_colors.dart';

/// Emerald Trading Skin — أخضر زمردي
class EmeraldTradingSkin implements SkinInterface {
  const EmeraldTradingSkin();

  @override
  String get name => 'emerald_trading';
  @override
  String get displayNameAr => 'أخضر زمردي';
  @override
  String get displayNameEn => 'Emerald Trading';

  @override
  ColorTokens get lightColors => const EmeraldTradingLightColors();
  @override
  ColorTokens get darkColors => const EmeraldTradingDarkColors();

  @override
  ThemeData buildLightTheme() => buildSkinTheme(lightColors, Brightness.light);
  @override
  ThemeData buildDarkTheme() => buildSkinTheme(darkColors, Brightness.dark);
}
