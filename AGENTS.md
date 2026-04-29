# AGENTS.md — Trading AI Bot

## 1. Mandatory Verification Gates
- **Flutter**: Run `flutter analyze` after EVERY UI change. Do NOT claim UI work done if it fails.
- **Backend tests**: Run `python -m pytest tests/` after backend changes. Only 1 test file exists (`tests/test_trading_engine_comprehensive.py`).
- **Import path**: The project uses `backend/` as a package root. Imports look like `from backend.core.state_manager import StateManager`. `sys.path` hacks appear in some files — do NOT add more.

## 2. Stack & Entrypoints (EASY TO MISS)
- **Backend**: Flask with Blueprints — NOT FastAPI. Entrypoint: `backend/api/admin_unified_api.py`.
- **Database**: PostgreSQL via raw `psycopg2` — no ORM. Thin wrapper: `backend/infrastructure/db_access.py`.
- **DatabaseManager** is a God Object split into 4 mixins: `trading`, `users`, `portfolio`, `notifications`. Use `db.get_connection()` for reads, `db.get_write_connection()` for writes. Always use context managers.
- **Frontend**: Flutter — `flutter_trading_app/` is the main app. `flutter_trading_bot-1/` is a nested copy — IGNORE IT.
- **State**: Riverpod providers in `lib/core/providers/`. Repositories in `lib/core/repositories/`.
- **Config**: Single source of truth = `config/unified_settings.py` (reads from env vars).
- **Binance keys**: Stored encrypted in `user_binance_keys` table — NEVER from env vars.
- **Auth**: Firebase Auth + JWT. Admin check via `authProvider.isAdmin`.

## 3. Database Gotchas (WILL BREAK THINGS)
- **Successful coins**: `save_successful_coins` caps at 50 coins with score-based ranking and upsert merge.
- **Demo account**: Admin-only (`_ensure_demo_account` guard). Initial balance = 1000.0 USD.
- **Notifications**: `DbNotificationsMixin` has fallback schema handling. If `notification_history` columns are missing, it falls back to a simplified query. Do NOT remove this pattern.
- **Migrations**: 22 files in `database/migrations/`. ALWAYS add new migrations — NEVER modify existing ones.

## 4. Flutter Architecture Rules
- **ShellRoute**: `ShellRoute` in `app_router.dart`. Child screens MUST NOT wrap themselves in `Scaffold` — causes UI stuttering/double bars.
- **Biometric gate**: Admin actions gated by `biometricServiceProvider`. Mock or bypass when testing.
- **Admin tab**: Tab 5 (Shield icon) in `main_shell.dart` → `adminDashboard`. Hidden when `!isAdmin`.
- **Skin system**: Two themes (`minimalist_ui`, `soft_pastel`) in `lib/design/skins/`. Design tokens in `lib/design/tokens/`.
- **Feature structure**: `lib/features/{feature_name}/` with `{feature_name}_screen.dart` pattern.

## 5. Backend Architecture — The Trading Pipeline
```
Scanner → Signal → Entry → Exit (with cognitive layer wrapping everything)
```
- **Core loop**: `backend/core/trading_orchestrator.py`
- **Group B auto-trading**: `backend/core/group_b_system.py` — 60-second cycle (sole auto-system; Group A removed)
- **Dual mode**: `backend/core/dual_mode_router.py` toggles Real vs Demo. ALWAYS check mode before executing trades.
- **Deployment**: Docker-based (4 services: api, scanner, executor, postgres + nginx reverse proxy). VPS: `ssh root@72.60.190.188`.
- **Port**: Server runs on port 3002 (mapped by nginx on port 80).
- **Health endpoint**: `/admin/system/health` (Flask Blueprint in `system_health.py`).
- **Start script**: `start_server.py` (Docker CMD).
- **Refresh deps**: `pip freeze > requirements-frozen.txt` after adding packages.
- **WARNING**: `infra/ecosystem.config.js` is a stale PM2 config — IGNORE IT.

## 6. Strategy System — NEVER BREAK THIS CONTRACT
- **Base contract**: `backend/strategies/base_strategy.py` — abstract class with `prepare_data()`, `detect_entry()`, `check_exit()`, `get_config()`.
- **LAW**: Add strategies by creating a NEW file inheriting `BaseStrategy`. NEVER modify the base class or existing strategies to add new behavior.
- **Routing**: `strategy_router.py` maps market regimes to strategies. `strategy_ensemble.py` combines signals.

## 7. Cognitive Layer — Mandatory Cycle
The cognitive orchestrator enforces a non-negotiable cycle:
**READ → ANALYZE → THINK → INFER → DECIDE → EXECUTE → MONITOR → ADAPT**
- 6 subsystems coordinated in `backend/cognitive/cognitive_orchestrator.py`
- **Strict rules**: No entry without market context. No exit without proven reason. Capital preservation is priority.
- **5 exit engines** in `multi_exit_engine.py`: Weakness, StructureBreak, VolatilityShift, Reversal, Emergency. Each votes independently with urgency levels (NONE→LOW→MEDIUM→HIGH→CRITICAL). Partial exit support via `exit_pct`.

## 8. ML Pipeline — Key Thresholds
- **MistakeMemory**: Max 500 mistakes in `trading_brain.py`. Tracks pattern, count, total_loss, conditions.
- **DualPathDecision**: Two learners — Conservative (LR=0.3, min_sample=30, confidence=0.65) + Balanced (LR=0.5, min_sample=15, confidence=0.55). Weighted voting.
- **HybridLearning**: Phase transition by real trade count — 0-50 (backtest 70%), 50-100 (backtest 50%), 100-200 (backtest 30%), 200+ (backtest 15%). MarketRegime enum: BULL, BEAR, SIDEWAYS, VOLATILE, UNKNOWN.

## 9. Risk System — Hard Limits
- **Kelly Criterion**: Conservative mode. WR=63.9%, avg_win=1.35%, avg_loss=1.62%. Position bounds: min 1%, max 15%.
- **Portfolio heat**: Max 6% total exposure across all positions (`portfolio_heat_manager.py`). Returns `can_open_new` boolean.
- **Circuit breaker**: `backend/utils/circuit_breaker.py` — respect it.

## 10. Market Regime Detection
- **SimpleRegimeDetector**: Single timeframe — TRENDING_VOLATILE, TRENDING_CALM, RANGING_TIGHT, CHOPPY_VOLATILE, NEUTRAL.
- **MarketRegimeDetector**: Multi-TF (1h/4h/1d) — BULL_STRONG, BULL_WEAK, NEUTRAL, BEAR_WEAK, BEAR_STRONG, HIGH_VOLATILITY.
- Regime maps to: position size multipliers, stop-loss multipliers, and allowed strategies (long/short).
- At least 50 candles required for Simple, 100 for Multi-TF. Returns UNKNOWN/NEUTRAL on insufficient data.

## 11. Smart Money Orchestrator
- 5 weighted components: liquidity_zones (0.25), vwap (0.20), liquidity_sweeps (0.20), order_blocks (0.20), fair_value_gaps (0.15).
- Confluence score threshold: 60 for signal generation.
- Signals: BUY / SELL / WAIT.

## 12. Never Delete / Never Touch
- `runtime/logs/` — NEVER delete. Backend logs go here.
- `database/migrations/` — NEVER modify existing migration files.
- `config/unified_settings.py` — single config source. Read from it, don't write to it.
- Strategy base class — NEVER modify. Add new strategies in new files only.

## 13. Files That Don't Exist Yet (Known Gaps)
- Only 1 test file — almost zero coverage. Financial system demands comprehensive test suite.

## 14. Language & Verification
- **Chat in Arabic, code in English.**
- After any code change: `flutter analyze` (Flutter) or `python -m pytest tests/` (backend).
- Config values in `.env.example` — Arabic comments. Environment file is `.env` (gitignored).
