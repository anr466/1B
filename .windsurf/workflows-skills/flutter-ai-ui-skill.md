---
name: flutter-ai-ui-skill
description: >-
  A master-level Flutter UI/UX design skill that equips AI coding assistants
  with curated design intelligence, colour palettes, typography pairings,
  animation patterns, component blueprints and actionable checklists for
  building beautiful, accessible, production-ready Flutter applications. Covers
  Material 3, Cupertino, adaptive layouts, animations, theming, state management
  integration, accessibility and performance optimization.
---

# Flutter AI UI Skill 🎨

> **Design intelligence for Flutter** — turn any AI coding assistant into a Flutter UI expert.

---

## Overview

This skill provides comprehensive design intelligence for building and
refining Flutter applications. It combines curated Flutter-specific best
practices with professional UI/UX heuristics to produce beautiful, accessible,
performant, and maintainable mobile interfaces.

### When does this skill activate?

The skill activates automatically when you:
- Request UI/UX work in a Flutter project
- Ask to build, create, design, or improve any screen or component
- Use the `/flutter-ai-ui` slash command (Kiro, Copilot, Roo Code)

---

## How to Use This Skill

### Step 1 – Gather Context

Before writing a single line of code, understand:

- **App domain**: healthcare, fintech, e-commerce, social, productivity, etc.
- **Target audience**: age group, technical literacy, accessibility needs
- **Brand personality**: playful, professional, minimal, bold, luxurious, warm
- **Platform priorities**: Android-first, iOS-first, cross-platform + web
- **Color & font preferences**: any existing assets or brand guidelines

### Step 2 – Generate a Design System

Use `data/flutter_colors.csv` to choose your primary, secondary, surface and
error palette based on category. Use `data/flutter_typography.csv` to pick a
font-pairing that matches the app mood. Then generate a `AppTheme` class:

```dart
// Example — do NOT hardcode colours across widgets
final theme = ThemeData(
  useMaterial3: true,
  colorScheme: ColorScheme.fromSeed(
    seedColor: const Color(0xFF2563EB),
    brightness: Brightness.light,
  ),
  textTheme: GoogleFonts.poppinsTextTheme(),
);
```

### Step 3 – Apply Flutter Design Guidelines

Consult `data/stacks/flutter_guidelines.csv` before implementing any component.
Run the keyword search tool to find relevant dos & don'ts:

```sh
python scripts/search_guidelines.py --keyword "animation"
python scripts/search_guidelines.py --category "accessibility"
python scripts/search_guidelines.py --severity "critical"
```

### Step 4 – Scaffold or Analyse

**New project:**
```sh
python scripts/create_flutter_project.py --name my_app --template material3
python scripts/create_flutter_project.py --name my_app --template cupertino
python scripts/create_flutter_project.py --name my_app --template adaptive
```

**Existing project:**
```sh
python scripts/analyse_flutter_project.py --path path/to/project
python scripts/analyse_flutter_project.py --path path/to/project --fix-suggestions
```

### Step 5 – Pre-Delivery Checklist

Before handing off any UI work, verify:

#### ✅ Accessibility
- [ ] All images have `semantic` labels or `excludeFromSemantics: true` for decorative ones
- [ ] Interactive elements have `Tooltip` or `Semantics(label: ...)`
- [ ] Color contrast meets WCAG AA (4.5:1 for text, 3:1 for UI components)
- [ ] Dynamic text scaling works — wrap with `MediaQuery.textScalerOf`
- [ ] `FocusTraversalGroup` and `onKey` keyboard navigation for desktop/web

#### ✅ Responsiveness
- [ ] `LayoutBuilder` or `AdaptiveLayout` used for breakpoints
- [ ] Orientation not locked unless specifically required
- [ ] Content scrollable on small screens — never overflow
- [ ] Safe area respected with `SafeArea` widget

#### ✅ Theming
- [ ] `ThemeData` with `ColorScheme` — no hardcoded hex colors in widgets
- [ ] `darkTheme` provided in `MaterialApp`
- [ ] Dynamic color (`DynamicColorBuilder`) supported where possible
- [ ] Custom fonts loaded via `pubspec.yaml` or `google_fonts`

#### ✅ Performance
- [ ] `const` constructors everywhere possible
- [ ] `ListView.builder` / `GridView.builder` for long lists
- [ ] `RepaintBoundary` around heavy or animated widgets
- [ ] Images loaded via `cached_network_image`
- [ ] Build methods < 50 lines; heavy logic extracted to helpers

#### ✅ Navigation & State
- [ ] Declarative routing via `GoRouter` (preferred) or Navigator 2.0
- [ ] `PopScope` handles Android predictive back gesture
- [ ] State management chosen and applied consistently (Riverpod / Bloc / Provider)
- [ ] Providers/Notifiers disposed correctly

#### ✅ Code Quality
- [ ] Widgets extracted into separate files once > 80 lines
- [ ] No `setState` called inside `build()`
- [ ] No `BuildContext` stored across async gaps without checking `mounted`
- [ ] Widget tests cover critical UI flows

---

## Design Principles — Flutter Edition

### 1. Material 3 First
Always use `useMaterial3: true`. Leverage `ColorScheme`, `Typography`,
`NavigationBar`, `Card`, `FilledButton`, `ElevatedButton`, `InputDecoration`
with Material 3 defaults. Avoid overriding M3 tokens unnecessarily.

### 2. Adaptive, Not Responsive Only
Flutter runs on mobile, tablet, web, and desktop. Use `AdaptiveLayout` or
`LayoutBuilder` with breakpoints:
- Mobile: < 600px
- Tablet: 600px – 1200px  
- Desktop: > 1200px

### 3. Animation as Communication
Animations should communicate state changes, not just look pretty.
- Use `AnimatedContainer`, `AnimatedOpacity`, `AnimatedSwitcher` for implicit animations
- Use `AnimationController` + `Tween` for explicit control
- Use `Hero` for shared element transitions
- Keep durations between 150ms–400ms; 300ms is the sweet spot
- Use `Curves.easeInOut` by default; `Curves.elasticOut` for playful UIs

### 4. Elevation & Depth
Material 3 uses tonal elevation (color-based), not shadow-based by default.
Use `elevation` with `surfaceTintColor` for cards. Use `BoxShadow` sparingly
and consistently — define shadow tokens in your theme.

### 5. Typography Hierarchy
Always define a complete `TextTheme`:
- `displayLarge/Medium/Small` — Hero sections, splash screens
- `headlineLarge/Medium/Small` — Page and section titles
- `titleLarge/Medium/Small` — Card titles, list items, dialogs
- `bodyLarge/Medium/Small` — Body copy, descriptions
- `labelLarge/Medium/Small` — Buttons, tabs, chips

### 6. Spacing System
Use an 8-point spacing grid. Define constants:
```dart
class AppSpacing {
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;
}
```

### 7. Color Token System
Never use raw hex in widgets. Use semantic tokens:
```dart
// ✅ Correct
color: Theme.of(context).colorScheme.primary

// ❌ Wrong
color: const Color(0xFF2563EB)
```

---

## UI Style Catalog

The following Flutter-specific UI styles are supported. Reference these
when asked to build in a particular aesthetic:

| Style | Description | Key Widgets & Techniques |
|-------|-------------|--------------------------|
| **Material 3 Clean** | Google's latest design language, tonal color, gentle curves | `FilledButton`, `Card`, `NavigationBar`, `ColorScheme.fromSeed` |
| **Cupertino Native** | iOS-native look and feel | `CupertinoApp`, `CupertinoNavigationBar`, `CupertinoButton` |
| **Glassmorphism** | Frosted glass, blur, translucency | `BackdropFilter`, `ImageFilter.blur`, gradient overlays |
| **Neumorphism** | Soft embossed shadows, monochromatic depth | Layered `BoxShadow` with light/dark offset |
| **Dark Neon** | Dark background with glowing neon accents | Custom `ColorScheme`, `BoxShadow` with colored spread |
| **Minimal Flat** | Ultra-clean, plenty of whitespace, subtle borders | `Container`, `Divider`, precise typography |
| **Claymorphism** | Soft, pillowy 3D-like components | Large border radius, colored shadow, pastel palette |
| **Brutalist** | Raw, high-contrast, bold typography | Borders, monochrome, loud text, tight spacing |
| **Gradient Premium** | Layered gradients, depth and richness | `LinearGradient`, `RadialGradient`, `ShaderMask` |
| **Organic Biophilic** | Natural forms, earthy colors, soft curves | Custom clip paths, earth tones, organic shapes |
| **Retro/Y2K** | Nostalgic, pixel-inspired, bold colors | Custom painters, chunky UI, high saturation |
| **Enterprise Dark** | Professional dark dashboard aesthetic | Dark surface colors, data-dense layout, subtle dividers |

---

## Flutter-Specific Component Blueprints

### Bottom Navigation
```dart
// Prefer NavigationBar (M3) over BottomNavigationBar
NavigationBar(
  destinations: const [
    NavigationDestination(icon: Icon(Icons.home), label: 'Home'),
    NavigationDestination(icon: Icon(Icons.search), label: 'Search'),
  ],
  selectedIndex: _selectedIndex,
  onDestinationSelected: (i) => setState(() => _selectedIndex = i),
)
```

### Loading States
```dart
// Use Shimmer loading — never show empty containers
Shimmer.fromColors(
  baseColor: Colors.grey.shade300,
  highlightColor: Colors.grey.shade100,
  child: Container(height: 80, color: Colors.white),
)
```

### Error States
```dart
// Always handle error states visually
ErrorStateWidget(
  icon: Icons.cloud_off,
  title: 'Something went wrong',
  subtitle: error.toString(),
  onRetry: () => ref.refresh(myProvider),
)
```

### Pull-to-Refresh
```dart
RefreshIndicator.adaptive( // Use adaptive for iOS/Android
  onRefresh: () async => ref.refresh(myProvider),
  child: ListView.builder(...),
)
```

---

## Supported AI Platforms

This skill works with all major AI coding assistants:

| Platform | Activation Mode | Setup Location |
|----------|----------------|----------------|
| **Antigravity** | Skill auto-activation | `.agents/skills/` |
| **Claude Code** | CLAUDE.md / skill | `.claude/` |
| **Cursor** | Rules file | `.cursor/rules/` |
| **Windsurf** | Rules file | `.windsurf/rules/` |
| **GitHub Copilot** | Slash command | `.github/copilot-instructions.md` |
| **Gemini CLI** | GEMINI.md | `GEMINI.md` |
| **Kiro** | Spec/hook | `.kiro/` |
| **Roo Code** | Rules | `.roo/` |
| **OpenCode** | Rules | `opencode.json` |
| **Continue** | Config | `.continue/rules/` |
| **Zed** | Rules | `.zed/settings.json` |

---

## File Structure Reference

```
flutter-ai-ui-skill/
├── SKILL.md                          ← You are here (AI reads this)
├── README.md                         ← Human-facing documentation
├── data/
│   ├── flutter_colors.csv            ← 30+ Flutter app-type palettes
│   ├── flutter_typography.csv        ← 15 Google Fonts pairings
│   └── stacks/
│       └── flutter_guidelines.csv    ← 120+ Flutter UI guidelines
├── scripts/
│   ├── analyse_flutter_project.py    ← Project audit tool
│   ├── search_guidelines.py          ← Guideline keyword search
│   └── create_flutter_project.py     ← Project scaffolder
└── templates/
    ├── material3/                    ← Material 3 starter
    ├── cupertino/                    ← Cupertino/iOS starter
    └── adaptive/                     ← Adaptive multi-platform starter
```

---

## Quick Reference: Top 20 Flutter UI Rules

| # | Rule | Severity |
|---|------|----------|
| 1 | Use `const` constructors for immutable widgets | 🔴 Critical |
| 2 | Never hardcode colors — use `Theme.of(context).colorScheme` | 🔴 Critical |
| 3 | Keep `build()` methods under 50 lines | 🔴 Critical |
| 4 | Use `ListView.builder` for any list > 10 items | 🔴 Critical |
| 5 | Provide `darkTheme` in `MaterialApp` | 🟠 High |
| 6 | Add `Semantics` labels to all interactive/image widgets | 🟠 High |
| 7 | Use `RepaintBoundary` around animated widgets | 🟠 High |
| 8 | Check `mounted` before using `BuildContext` after async | 🟠 High |
| 9 | Use `cached_network_image` for all network images | 🟠 High |
| 10 | Use `GoRouter` for declarative routing | 🟡 Medium |
| 11 | Prefer `AnimatedContainer` over explicit animations for simple transitions | 🟡 Medium |
| 12 | Use `LayoutBuilder` for responsive breakpoints | 🟡 Medium |
| 13 | Extract reusable widgets into separate files | 🟡 Medium |
| 14 | Use `SafeArea` for content near edges | 🟡 Medium |
| 15 | Prefer `Flexible`/`Expanded` over fixed sizes in rows/columns | 🟡 Medium |
| 16 | Use `Hero` widget for page transition shared elements | 🟢 Low |
| 17 | Apply `TextScaler` support for accessibility | 🟢 Low |
| 18 | Use `PopScope` for Android back gesture | 🟢 Low |
| 19 | Prefer `SelectableText` for copyable content | 🟢 Low |
| 20 | Use `AdaptiveLayout` from `flutter_adaptive_scaffold` for multi-platform | 🟢 Low |

---

*Flutter AI UI Skill — Built with ❤️ for the Flutter community.*
*See README.md for installation instructions and full documentation.*