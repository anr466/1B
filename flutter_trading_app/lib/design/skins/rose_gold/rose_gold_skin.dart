import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';
import 'package:trading_app/design/skins/skin_interface.dart';
import 'package:trading_app/design/skins/skin_theme_builder.dart';
import 'package:trading_app/design/skins/rose_gold/rose_gold_colors.dart';

/// Rose Gold Skin — وردي ذهبي
class RoseGoldSkin implements SkinInterface {
  const RoseGoldSkin();

  @override
  String get name => 'rose_gold';
  @override
  String get displayNameAr => 'وردي ذهبي';
  @override
  String get displayNameEn => 'Rose Gold';

  @override
  ColorTokens get lightColors => const RoseGoldLightColors();
  @override
  ColorTokens get darkColors => const RoseGoldDarkColors();

  @override
  ThemeData buildLightTheme() => buildSkinTheme(lightColors, Brightness.light);
  @override
  ThemeData buildDarkTheme() => buildSkinTheme(darkColors, Brightness.dark);
}
