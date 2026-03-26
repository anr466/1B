Patch Plan: notifications, identities, and streaming enhancements

1. Objective
- Introduce robust, idempotent notification delivery and ensure user-context integrity across trading state and UI layers. Enable streaming updates where feasible and prepare for safer deployment.

2. Scope
- backend/core/trading_state_machine.py: add resilient fallback path on DB IO/fatal errors; introduce clearer state transitions.
- backend/api/notifications.py / related modules: introduce delivery tracking (dedupe) and correlation IDs; ensure safe marking of read statuses.
- database/postgres_schema.sql: add notification_delivery_log to enable idempotent delivery verification.
- flutter_trading_app: updates to UI ISR points if needed (high-level; optional per UI schedule).

3. Concrete changes (high level)
- Add table notification_delivery_log with fields: id, user_id, notification_id, delivered_at, status; add index on user_id.
- Extend notifications flow to log each delivery attempt and avoid duplicates. Include a correlation_id and idempotent checks.
- Ensure all notification endpoints pass the correct user_id (validate ownership) and support a read-status workflow.
- Introduce a conservative retry policy for DB IO failures in the TradingStateMachine, with a fallback default state rather than a crash.
- Consider adding a WebSocket/SSE endpoint for real-time updates where feasible.

4. Tests & Validation
- Unit tests: add tests for idempotent delivery logic and read/mark flows.
- Integration tests: end-to-end path from trigger to notification to UI reflect state accurately.
- Lint/build: ensure code passes lint rules and builds for both Python backend and Flutter front-end where applicable.

5. Deployment plan (high level)
- Feature branch: patch/server-health-fix-V1
- PR with review; run backend tests and UI smoke tests locally.
- Deploy to staging; monitor health and logs for 24h; have rollback plan to previous commit.

6. Risks & Mitigations
- IO/DB errors could persist; mitigation includes increasing retry backoff and fallback state logging.
- UI-flash risk if streaming endpoints are not ready; plan incremental rollout and feature flags.

End Patch
