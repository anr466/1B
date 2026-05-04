import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/color_tokens.dart';

/// Minimalist UI Light Colors — Warm Monochrome + Muted Pastels
/// Protocol: Premium Utilitarian Minimalism
class MinimalistUILightColors implements ColorTokens {
  const MinimalistUILightColors();

  // ─── Core Palette ────────────────────────────────
  // Primary: Ultra-dark charcoal for maximum contrast
  @override
  Color get primary => const Color(0xFF111111);
  @override
  Color get primaryDark => const Color(0xFF000000);
  @override
  Color get primaryLight => const Color(0xFF333333);

  // Secondary: Muted warm gray
  @override
  Color get secondary => const Color(0xFF787774);
  @override
  Color get accent => const Color(0xFF956400); // Pale Yellow Text

  // ─── Semantic Colors (Muted Pastels) ─────────────
  // Positive: Pale Green background with Dark Green text
  @override
  Color get success => const Color(0xFF346538);
  @override
  Color get successLight => const Color(0xFFEDF3EC);

  // Warning: Pale Yellow background with Dark Yellow text
  @override
  Color get warning => const Color(0xFF956400);
  @override
  Color get error => const Color(0xFF9F2F2D); // Pale Red Text
  @override
  Color get errorLight => const Color(0xFFFDEBEC); // Pale Red Bg
  @override
  Color get info => const Color(0xFF1F6C9F); // Pale Blue Text

  // ─── Surfaces (Warm Bone/Off-White) ──────────────
  @override
  Color get background => const Color(0xFFFBFBFA); // Main Canvas
  @override
  Color get bgSecondary => const Color(0xFFF7F6F3); // Warm Bone
  @override
  Color get bgTertiary => const Color(0xFFEAEAEA); // Structural Borders
  @override
  Color get card => const Color(0xFFFFFFFF); // Pure White
  @override
  Color get elevated => const Color(0xFFF9F9F8); // Slightly off-white

  // ─── Typography ──────────────────────────────────
  @override
  Color get text => const Color(0xFF111111); // Off-black
  @override
  Color get textSecondary => const Color(0xFF787774); // Muted Gray
  @override
  Color get textTertiary => const Color(0xFFA09E9B); // Faint Gray

  // ─── Financial ───────────────────────────────────
  @override
  Color get positive => const Color(0xFF346538);
  @override
  Color get negative => const Color(0xFF9F2F2D);

  // ─── Borders (Ultra-light gray) ──────────────────
  @override
  Color get border => const Color(0xFFEAEAEA);
  @override
  Color get borderLight => const Color(0xFFF0F0F0);

  // ─── Gradients (Minimalist uses flat colors, but we define subtle ones)
  @override
  List<Color> get gradientPrimary => const [Color(0xFF111111), Color(0xFF333333)];
  @override
  List<Color> get gradientAccent => const [Color(0xFFFBF3DB), Color(0xFFF0E0B0)];
  @override
  List<Color> get gradientSuccess => const [Color(0xFFEDF3EC), Color(0xFFD8E8D6)];
  @override
  List<Color> get gradientDark => const [Color(0xFFFBFBFA), Color(0xFFF7F6F3)];
  @override
  List<Color> get gradientCard => const [Color(0xFFFFFFFF), Color(0xFFF9F9F8)];
}

/// Minimalist UI Dark Colors — Inverted Monochrome
/// Note: The protocol focuses on Light mode, but we provide a usable Dark mode
/// that maintains the "Flat" and "Border-based" aesthetic.
class MinimalistUIDarkColors implements ColorTokens {
  const MinimalistUIDarkColors();

  @override
  Color get primary => const Color(0xFFEAEAEA);
  @override
  Color get primaryDark => const Color(0xFFCCCCCC);
  @override
  Color get primaryLight => const Color(0xFFFFFFFF);

  @override
  Color get secondary => const Color(0xFF888888);
  @override
  Color get accent => const Color(0xFFD4AF37);

  @override
  Color get success => const Color(0xFF4ADE80);
  @override
  Color get successLight => const Color(0xFF064E3B);

  @override
  Color get warning => const Color(0xFFFBBF24);
  @override
  Color get error => const Color(0xFFF87171);
  @override
  Color get errorLight => const Color(0xFF450A0A);
  @override
  Color get info => const Color(0xFF60A5FA);

  @override
  Color get background => const Color(0xFF0A0A0A);
  @override
  Color get bgSecondary => const Color(0xFF111111);
  @override
  Color get bgTertiary => const Color(0xFF1A1A1A);
  @override
  Color get card => const Color(0xFF141414);
  @override
  Color get elevated => const Color(0xFF1C1C1C);

  @override
  Color get text => const Color(0xFFEAEAEA);
  @override
  Color get textSecondary => const Color(0xFF999999);
  @override
  Color get textTertiary => const Color(0xFF666666);

  @override
  Color get positive => const Color(0xFF4ADE80);
  @override
  Color get negative => const Color(0xFFF87171);

  @override
  Color get border => const Color(0xFF2A2A2A);
  @override
  Color get borderLight => const Color(0xFF222222);

  @override
  List<Color> get gradientPrimary => const [Color(0xFFEAEAEA), Color(0xFFCCCCCC)];
  @override
  List<Color> get gradientAccent => const [Color(0xFF2A2A2A), Color(0xFF1A1A1A)];
  @override
  List<Color> get gradientSuccess => const [Color(0xFF064E3B), Color(0xFF022C22)];
  @override
  List<Color> get gradientDark => const [Color(0xFF111111), Color(0xFF0A0A0A)];
  @override
  List<Color> get gradientCard => const [Color(0xFF141414), Color(0xFF0A0A0A)];
}
