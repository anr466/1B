import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';
import 'package:trading_app/design/skins/skin_interface.dart';
import 'package:trading_app/design/skins/skin_theme_builder.dart';
import 'package:trading_app/design/skins/cyber_neon/cyber_neon_colors.dart';

/// Cyber Neon Skin — سماوي نيون
class CyberNeonSkin implements SkinInterface {
  const CyberNeonSkin();

  @override
  String get name => 'cyber_neon';
  @override
  String get displayNameAr => 'سماوي نيون';
  @override
  String get displayNameEn => 'Cyber Neon';

  @override
  ColorTokens get lightColors => const CyberNeonLightColors();
  @override
  ColorTokens get darkColors => const CyberNeonDarkColors();

  @override
  ThemeData buildLightTheme() => buildSkinTheme(lightColors, Brightness.light);
  @override
  ThemeData buildDarkTheme() => buildSkinTheme(darkColors, Brightness.dark);
}
