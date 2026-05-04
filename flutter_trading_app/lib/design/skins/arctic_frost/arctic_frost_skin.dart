import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';
import 'package:trading_app/design/skins/skin_interface.dart';
import 'package:trading_app/design/skins/skin_theme_builder.dart';
import 'package:trading_app/design/skins/arctic_frost/arctic_frost_colors.dart';

/// Arctic Frost Skin — أبيض ثلجي
class ArcticFrostSkin implements SkinInterface {
  const ArcticFrostSkin();

  @override
  String get name => 'arctic_frost';
  @override
  String get displayNameAr => 'أبيض ثلجي';
  @override
  String get displayNameEn => 'Arctic Frost';

  @override
  ColorTokens get lightColors => const ArcticFrostLightColors();
  @override
  ColorTokens get darkColors => const ArcticFrostDarkColors();

  @override
  ThemeData buildLightTheme() => buildSkinTheme(lightColors, Brightness.light);
  @override
  ThemeData buildDarkTheme() => buildSkinTheme(darkColors, Brightness.dark);
}
