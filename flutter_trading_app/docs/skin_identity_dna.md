# Skin Identity DNA (Fintech Theme System)

This document defines a non-overlap visual identity for each skin to avoid palette convergence over time.

## Design constraints (must stay true)

1. Keep semantic financial colors unified across skins (`positive` / `negative`) for UX consistency.
2. Differentiate skins through brand + surfaces + dark/card gradients.
3. Never make two skins share near-identical `background`, `bgSecondary`, `card`, and `gradientDark` families.
4. If adding a new skin, check nearest-neighbor distance against existing skins before merge.

---

## 1) Obsidian Titanium

- **Core mood:** Professional metallic / premium enterprise
- **Hue family:** Steel blue + titanium gold
- **Dark base:** Deep navy-black surfaces
- **Light base:** Cool slate surfaces
- **Do not drift into:** Arctic Frost neutral ice or Midnight Ocean vivid blue

**Source:** `lib/design/skins/obsidian_titanium/obsidian_titanium_colors.dart`

## 2) Violet Brand

- **Core mood:** Signature brand / expressive premium
- **Hue family:** Violet + pink with subtle cyan accents
- **Dark base:** Violet-tinted charcoal
- **Light base:** Soft violet mist
- **Do not drift into:** Rose Gold warm pink-champagne

**Source:** `lib/design/skins/violet_brand/violet_brand_colors.dart`

## 3) Midnight Ocean

- **Core mood:** Deep ocean / focused trading desk
- **Hue family:** Royal blue + ocean cyan (reduced neon)
- **Dark base:** Deep blue-black ocean surfaces
- **Light base:** Pale blue paper with strong blue primaries
- **Do not drift into:** Cyber Neon electric cyan-magenta

**Source:** `lib/design/skins/midnight_ocean/midnight_ocean_colors.dart`

## 4) Arctic Frost

- **Core mood:** Minimal arctic / clean neutral
- **Hue family:** Icy neutral gray-blue (desaturated)
- **Dark base:** Graphite-ice neutral surfaces
- **Light base:** Frosted neutral paper
- **Do not drift into:** Obsidian Titanium steel-premium tones

**Source:** `lib/design/skins/arctic_frost/arctic_frost_colors.dart`

## 5) Emerald Trading

- **Core mood:** Growth / market-positive / institutional green
- **Hue family:** Emerald + jade
- **Dark base:** Deep emerald-green surfaces
- **Light base:** Mint-emerald soft surfaces
- **Do not drift into:** Midnight/Cyber blue-cyan lanes

**Source:** `lib/design/skins/emerald_trading/emerald_trading_colors.dart`

## 6) Cyber Neon

- **Core mood:** Tech-forward / high-energy / modern neon
- **Hue family:** Electric cyan + magenta
- **Dark base:** Near-black neon platform
- **Light base:** Bright cyan paper with neon accents
- **Do not drift into:** Midnight Ocean royal-blue tonality

**Source:** `lib/design/skins/cyber_neon/cyber_neon_colors.dart`

## 7) Rose Gold

- **Core mood:** Warm luxury / boutique fintech
- **Hue family:** Rose + champagne gold
- **Dark base:** Warm rose-plum surfaces
- **Light base:** Warm blush paper
- **Do not drift into:** Violet Brand cool violet-pink

**Source:** `lib/design/skins/rose_gold/rose_gold_colors.dart`

---

## Maintenance checklist (for any palette change)

- [ ] Keep semantic token consistency (`success/warning/error/info`, `positive/negative`)
- [ ] Validate dark and light readability (WCAG AA target)
- [ ] Compare nearest skin distance (dark + light)
- [ ] Check dashboard and key widgets visually in all skins
- [ ] Run `flutter analyze`
