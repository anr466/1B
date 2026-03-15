---
description: مهارة تصميم الواجهات الاحترافية - Anthropic Frontend Design Skill مكيّفة لتطبيق التداول React Native
---

# Frontend Design Skill - Trading App Edition

This skill guides creation of distinctive, production-grade mobile interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

**Source**: https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md
**Adapted for**: React Native Trading App (mobile_app/TradingApp/)

---

## PROTECTED ZONES - DO NOT MODIFY

The following files/components are PROTECTED and must NEVER be changed when applying this skill:

```
PROTECTED (NO TOUCH):
├── src/components/charts/*          ← ALL chart components
│   ├── PortfolioChart.js
│   ├── MiniPortfolioChart.js
│   ├── PortfolioDistributionChart.js
│   ├── TradeDistributionChart.js
│   ├── WinLossPieChart.js
│   ├── DailyHeatmap.js
│   └── index.js
├── src/services/*                   ← ALL API services
├── src/config/*                     ← ALL configuration
├── src/context/PortfolioContext.js   ← Portfolio data logic
├── src/context/TradingModeContext.js ← Trading mode logic
└── src/hooks/*                      ← ALL hooks
```

---

## Design Thinking (Before Any UI Work)

Before coding, understand the context and commit to a BOLD aesthetic direction:

- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. Use these for inspiration but design one that is true to the aesthetic direction.
- **Constraints**: React Native framework, mobile performance, accessibility, RTL support for Arabic.
- **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity.

Then implement working React Native code that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

---

## Frontend Aesthetics Guidelines (React Native Adapted)

### Typography
- Choose fonts that are beautiful, unique, and interesting
- **AVOID**: Default system fonts without character. If using system font, leverage fontWeight and letterSpacing creatively
- For React Native: Use `expo-font` or bundled custom fonts when available
- Pair a distinctive display weight (800/900) with a refined body weight (400/500)
- Use `letterSpacing` and `lineHeight` to create rhythm and breathing room

### Color & Theme
- Commit to a cohesive aesthetic. Use the existing `theme.js` variables for consistency
- Dominant colors with sharp accents outperform timid, evenly-distributed palettes
- The current theme uses Purple (#8B5CF6) as primary — when extending, create contrast through:
  - Unexpected accent pairings (cyan #06B6D4 already available)
  - Strategic use of gradients (LinearGradient from expo-linear-gradient)
  - Light/dark surface layering for depth

### Motion & Micro-interactions (React Native)
- Use `react-native-reanimated` or `Animated` API for effects
- Focus on high-impact moments: screen entry animations with staggered reveals
- Subtle scale/opacity transitions on card press (TouchableOpacity → Pressable with animated feedback)
- Loading states that feel alive (SkeletonLoader already exists — enhance, don't replace)
- Scroll-based animations for immersive data browsing

### Spatial Composition
- Unexpected layouts: Asymmetry. Overlap. Grid-breaking hero elements
- Generous negative space OR controlled density — pick one and commit
- Use `marginTop: -20` overlapping cards for depth illusion
- Full-bleed sections breaking the standard padding rhythm
- Hero numbers (balance, PnL) deserve dramatic sizing and spacing

### Backgrounds & Visual Details
- Create atmosphere and depth rather than flat solid backgrounds
- Layer translucent cards over gradient backgrounds
- Use `BlurView` (expo-blur) for glassmorphism effects where appropriate
- Subtle border treatments: 1px borders with low-opacity primary color
- Card shadows that match the theme darkness level
- Status indicators with glowing dot effects (animated opacity)

---

## NEVER DO THIS (Anti-patterns)

```
BANNED in this project:
├── Generic system font styling without character
├── Cookie-cutter card layouts with no visual hierarchy
├── Predictable spacing (same padding everywhere)
├── Flat, lifeless color usage (no gradients, no depth)
├── Ignoring the existing theme.js color system
├── Modifying ANY chart component
├── Breaking API service calls or data flow
├── Adding heavy libraries without justification
├── Removing existing functionality for aesthetics
└── Ignoring RTL layout considerations
```

---

## Trading App Specific Design Patterns

### Financial Data Display
- Balance/PnL numbers are HERO elements — they deserve dramatic treatment
- Positive values: success green with subtle glow
- Negative values: error red with subtle warning feel
- Use `tabular-nums` equivalent (monospace for numbers) for alignment
- Percentage badges with pill-shaped containers and color coding

### Status Indicators
- System status (Running/Stopped/Error) needs instant visual recognition
- Use color + icon + animation combined (not just color alone)
- Pulse animation for "active" states
- Gentle breathing effect for "monitoring" states

### Card Hierarchy
- Primary cards: gradient border or gradient background, larger shadow
- Secondary cards: solid surface color, subtle border, small shadow
- Interactive cards: scale feedback on press, border highlight
- Info cards: accent-colored left border strip

### Navigation & Tab Bar
- Active tab: bold icon + primary color + subtle indicator
- Inactive tab: muted icon + textTertiary color
- Transition between tabs should feel smooth

---

## Implementation Rules

1. **Always read the target file COMPLETELY before editing**
2. **Preserve all existing functionality** — aesthetics enhance, never replace logic
3. **Use existing theme.js tokens** — extend theme if new values needed, don't hardcode
4. **Test on both iOS and Android** mental model — avoid platform-specific hacks
5. **Performance first** — no heavy animations on list items, no unnecessary re-renders
6. **Accessibility** — maintain contrast ratios (WCAG AA minimum), touch targets ≥ 44pt
7. **Charts are sacred** — NEVER modify chart components or their data flow

---

## Quality Checklist (Before Completing Any UI Task)

```
□ Does it follow a clear, intentional aesthetic direction?
□ Is every spacing/color/font choice deliberate (not default)?
□ Are hero elements (balance, PnL) visually striking?
□ Do interactions feel responsive and delightful?
□ Is the visual hierarchy crystal clear?
□ Does it use the existing theme.js system?
□ Are all chart components untouched?
□ Does existing functionality still work?
□ Is it performant (no jank, no unnecessary renders)?
□ Would a designer approve this as production-ready?
```
