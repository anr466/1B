# 🧠 AGENTS.md — Trading AI Bot

## 1. Personality & Expertise
- **Language**: Chat in Arabic, write code in English.
- **Style**: Concise and direct.
- **Expertise**: Trading, Crypto, ML, Flutter, Flask, PostgreSQL.

## 2. Mandatory Verification Hooks
- **Flutter**: Run `flutter analyze` after EVERY UI change.
- **Backend**: Run `python -m pytest tests/` after any engine/logic change.
- **Migrations**: Never modify existing `.sql` files in `database/migrations/`. Always create new ones.

## 3. Behavioral Guardrails
- **Never Guess**: Don't guess on `trading_logic`, `risk_parameters`, or `strategy_behavior`.
- **Prefer Patterns**: Follow the repository's established code style.
- **Protected Files**:
    - `runtime/logs/` (Never delete)
    - `backend/strategies/base_strategy.py` (Never modify)
    - `config/unified_settings.py` (Never modify)
- **Security**: Always check `dual_mode_router.py` to differentiate Real vs Demo execution.
- **Binance Keys**: Always fetch from `user_binance_keys` table, NEVER from env vars.

## 4. Critical "Gotchas" (Double-Check)
- **Framework**: It's **Flask** with Blueprints (NOT FastAPI).
- **Flutter UI**: Child screens must NOT include a `Scaffold` (it causes UI stuttering as `ShellRoute` provides it).
- **Demo Account**: Admin-only feature; ensure `_ensure_demo_account` guard is respected.
- **Start Script**: `start_server.py` is the Docker entrypoint (not for manual dev use).

## 5. Technical Environment
- **Project Root**: `/Users/anr/Desktop/trading_ai_bot-1`
- **Deployment**: Docker-based on VPS `root@72.60.190.188`.
- **Navigation**: GoRouter with 5 bottom tabs. Tab 5 is Admin (role-gated).

## 6. Commands Reference
```bash
flutter analyze          # Dart linting
flutter pub get          # Fetch deps
python -m pytest tests/  # Backend logic tests
```

## 7. Architecture Reference

Full architecture, provider hierarchy, navigation rules, screen data conflicts, and anti-patterns are in **`ARCHITECTURE.md`** at the project root.

- **Working on screens?** → Load `ARCHITECTURE.md` first to understand provider flow and data conflicts.
- **Working on backend APIs?** → Load `ARCHITECTURE.md` to see auth layer, DB mixins, and endpoint patterns.
- **Adding a new provider?** → Check `ARCHITECTURE.md` §8 for invalidation rules.
- **Adding a new route?** → Check `ARCHITECTURE.md` §6 for navigation rules (go vs push).

## 8. Design System Reference

Full visual identity, colors, typography, spacing, component patterns, and do's/don'ts are in **`DESIGN.md`** at the project root.

- **Building UI?** → Load `DESIGN.md` first — never use raw `TextStyle()`, `TextButton`, `ElevatedButton`, or `Container(borderRadius)`.
- **Adding a button?** → Use `AppButton` with the correct variant.
- **Adding a card?** → Use `AppCard`.
- **Adding a badge?** → Use `StatusBadge`.
- **Choosing colors?** → Use `ColorScheme` and `SemanticColors` — never `Color(0xFF...)`.
- **Choosing text style?** → Use `TypographyTokens.xxx(color)`.
