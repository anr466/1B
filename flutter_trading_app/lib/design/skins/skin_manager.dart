import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/design/skins/skin_interface.dart';
import 'package:trading_app/design/skins/violet_brand/violet_brand_skin.dart';
import 'package:trading_app/design/skins/midnight_ocean/midnight_ocean_skin.dart';
import 'package:trading_app/design/skins/emerald_trading/emerald_trading_skin.dart';
import 'package:trading_app/design/skins/arctic_frost/arctic_frost_skin.dart';
import 'package:trading_app/design/skins/rose_gold/rose_gold_skin.dart';
import 'package:trading_app/design/skins/cyber_neon/cyber_neon_skin.dart';
import 'package:trading_app/design/skins/obsidian_titanium/obsidian_titanium_skin.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Skin Manager — تسجيل واسترجاع الـ skins
/// تصميم صافي — لا يعتمد على أي منطق أعمال
class SkinManager {
  SkinManager._();

  static final Map<String, SkinInterface> _skins = {
    'obsidian_titanium': const ObsidianTitaniumSkin(),
    'violet_brand': const VioletBrandSkin(),
    'midnight_ocean': const MidnightOceanSkin(),
    'emerald_trading': const EmeraldTradingSkin(),
    'arctic_frost': const ArcticFrostSkin(),
    'rose_gold': const RoseGoldSkin(),
    'cyber_neon': const CyberNeonSkin(),
  };

  static List<SkinInterface> get allSkins => _skins.values.toList();

  static SkinInterface getSkin(String name) {
    return _skins[name] ?? const ObsidianTitaniumSkin();
  }

  static SkinInterface get defaultSkin => const ObsidianTitaniumSkin();
}

// ─── Riverpod Providers (design-only state) ─────────

/// اسم الـ skin المختار (يُحفظ في SharedPreferences)
final skinNameProvider = StateProvider<String>((ref) => 'obsidian_titanium');

/// الـ skin object بناءً على الاسم
final skinProvider = Provider<SkinInterface>((ref) {
  final name = ref.watch(skinNameProvider);
  return SkinManager.getSkin(name);
});

/// وضع الثيم (light/dark/system)
final themeModeProvider = StateProvider<ThemeMode>((ref) => ThemeMode.dark);

/// الألوان الحالية بناءً على الـ skin + الوضع
final colorTokensProvider = Provider<ColorTokens>((ref) {
  final skin = ref.watch(skinProvider);
  final mode = ref.watch(themeModeProvider);
  return mode == ThemeMode.light ? skin.lightColors : skin.darkColors;
});
