import 'package:flutter/material.dart';
import 'package:trading_app/design/skins/skin_interface.dart';
import 'package:trading_app/design/skins/skin_theme_builder.dart';
import 'package:trading_app/design/skins/soft_pastel/soft_pastel_colors.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Soft Pastel Skin — ألوان ناعمة بأسلوب Bento Grid
class SoftPastelSkin implements SkinInterface {
  const SoftPastelSkin();

  @override
  String get name => 'soft_pastel';
  @override
  String get displayNameAr => 'ألوان ناعمة';
  @override
  String get displayNameEn => 'Soft Pastel';

  @override
  ColorTokens get lightColors => SoftPastelLightColors();
  @override
  ColorTokens get darkColors => SoftPastelDarkColors();

  @override
  ThemeData buildLightTheme() => buildSkinTheme(lightColors, Brightness.light);
  @override
  ThemeData buildDarkTheme() => buildSkinTheme(darkColors, Brightness.dark);
}
