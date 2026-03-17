import 'package:flutter/material.dart';
import 'package:trading_app/design/skins/skin_interface.dart';
import 'package:trading_app/design/skins/skin_theme_builder.dart';
import 'package:trading_app/design/skins/obsidian_titanium/obsidian_titanium_colors.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Obsidian Titanium Skin — أسود احترافي بهوية 1B
class ObsidianTitaniumSkin implements SkinInterface {
  const ObsidianTitaniumSkin();

  @override
  String get name => 'obsidian_titanium';
  @override
  String get displayNameAr => 'أسود احترافي';
  @override
  String get displayNameEn => 'Obsidian Titanium';

  @override
  ColorTokens get lightColors => const ObsidianTitaniumLightColors();
  @override
  ColorTokens get darkColors => const ObsidianTitaniumDarkColors();

  @override
  ThemeData buildLightTheme() => buildSkinTheme(lightColors, Brightness.light);
  @override
  ThemeData buildDarkTheme() => buildSkinTheme(darkColors, Brightness.dark);
}
