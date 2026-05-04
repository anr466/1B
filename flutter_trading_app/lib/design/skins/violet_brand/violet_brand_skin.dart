import 'package:flutter/material.dart';
import 'package:trading_app/design/skins/skin_interface.dart';
import 'package:trading_app/design/skins/skin_theme_builder.dart';
import 'package:trading_app/design/skins/violet_brand/violet_brand_colors.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Violet Brand Skin — الثيم الافتراضي (بنفسجي)
class VioletBrandSkin implements SkinInterface {
  const VioletBrandSkin();

  @override
  String get name => 'violet_brand';
  @override
  String get displayNameAr => 'البنفسجي الأساسي';
  @override
  String get displayNameEn => 'Violet Brand';

  @override
  ColorTokens get lightColors => const VioletBrandLightColors();
  @override
  ColorTokens get darkColors => const VioletBrandDarkColors();

  @override
  ThemeData buildLightTheme() => buildSkinTheme(lightColors, Brightness.light);
  @override
  ThemeData buildDarkTheme() => buildSkinTheme(darkColors, Brightness.dark);
}
