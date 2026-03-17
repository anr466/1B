import 'package:flutter/material.dart';
import 'package:trading_app/design/skins/skin_interface.dart';
import 'package:trading_app/design/skins/skin_theme_builder.dart';
import 'package:trading_app/design/skins/midnight_ocean/midnight_ocean_colors.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Midnight Ocean Skin — أزرق بحري
class MidnightOceanSkin implements SkinInterface {
  const MidnightOceanSkin();

  @override
  String get name => 'midnight_ocean';
  @override
  String get displayNameAr => 'أزرق بحري';
  @override
  String get displayNameEn => 'Midnight Ocean';

  @override
  ColorTokens get lightColors => const MidnightOceanLightColors();
  @override
  ColorTokens get darkColors => const MidnightOceanDarkColors();

  @override
  ThemeData buildLightTheme() => buildSkinTheme(lightColors, Brightness.light);
  @override
  ThemeData buildDarkTheme() => buildSkinTheme(darkColors, Brightness.dark);
}
