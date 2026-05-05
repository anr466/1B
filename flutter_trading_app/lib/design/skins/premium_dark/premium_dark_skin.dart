import 'package:flutter/material.dart';
import 'package:trading_app/design/skins/skin_interface.dart';
import 'package:trading_app/design/skins/skin_theme_builder.dart';
import 'package:trading_app/design/skins/premium_dark/premium_dark_colors.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Premium Dark Skin — فحمي عميق + ألوان نيونية
class PremiumDarkSkin implements SkinInterface {
  const PremiumDarkSkin();

  @override String get name => 'premium_dark';
  @override String get displayNameAr => 'داكن ممتاز';
  @override String get displayNameEn => 'Premium Dark';

  @override ColorTokens get lightColors => const PremiumDarkColors();
  @override ColorTokens get darkColors => const PremiumDarkColors();

  @override ThemeData buildLightTheme() => buildSkinTheme(lightColors, Brightness.dark);
  @override ThemeData buildDarkTheme() => buildSkinTheme(darkColors, Brightness.dark);
}
