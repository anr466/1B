Patch Plan v3: Systematic separation of concerns and core fixes

1) Objective
- Implement robust, independent components with a single source of truth for data, and ensure end-to-end communication across layers (Data Layer → Trading State Machine → Notifications → Identity → API → Frontend).

2) Scope of changes
- Data Layer: introduce DB wrapper (backend/core/db.py) for unified DB access.
- Trading State Machine: add resilient fallback via _get_default_state; centralize DB reads/writes through DB wrapper.
- Notifications: introduce notification_delivery_log and idempotent delivery path with correlation_id and ACK flows.
- Identity/Auth: ensure require_auth path is correctly wired; pass user_id consistently across services.
- API: align responses to use a consistent DTO structure; reflect system state with last_update and reconcile_stats.
- Frontend: adapt UI to consume unified DTOs and reflect consistent state.
- Streaming: plan a minimal WebSocket/SSE for live state updates.
- Tests: unit tests for dedupe/fallback; integration tests for end-to-end flows; lint and build checks.
- Deployment: safe deployment plan with rollback and post-deploy verification checks.

3) Concrete changes (high-level patches)
- Add/modify files:
  - backend/core/db.py (DB wrapper)
  - backend/core/trading_state_machine.py (fallback state, DB access via wrapper)
  - backend/core/notification_service.py (log_delivery, is_duplicate placeholders; to be wired later)
  - database/postgres_schema.sql (notification_delivery_log table + index)
- Implement: require_auth wiring and user_id propagation (auth module changes)
- API DTOs: standardize responses for /system/status, /notifications, etc.
- Frontend: updated DTO mapping in flutter_trading_app (providers/ DTOs)
- Streaming: add skeleton WebSocket/SSE endpoints and client stubs

4) Tests & Quality Assurance
- Backend: unit tests for: dedupe logic, fallback state, DB wrapper
- Integration tests: end-to-end test planning for trigger → notification → UI update
- Lint/build: ensure clean run on local env

5) Deployment & Rollback
- Create feature branch patch/server-health-fix-YYYYMMDD
- PR with CI; run all tests
- Deploy to staging; monitor health for 24h
- Rollback plan: revert patch branch or roll back containers

6) Validation & Verification
- Health endpoints stability post-deploy
- No duplicate notifications
- Trading state remains consistent and reflected in UI
- All components can operate against the same database (Single Source of Truth)

End Patch Plan
