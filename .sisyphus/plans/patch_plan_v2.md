Patch Plan v2: Local baseline, diffs, and concrete changes

1. Local baseline (collect)
- Branch: main
- Commit window: last 5 commits (as per local HEAD)
- Dependencies: requirements.txt (85 lines listed)
- Environment: sanitized .env snapshot (no secrets)

2. Diffs (server vs local)
- Affected files:
  - .Asynchronous_State_Machine
  - backend/core/trading_state_machine.py
  - flutter_trading_app/lib/core/providers/admin_provider.dart
  - flutter_trading_app/lib/features/admin/screens/trading_control_screen.dart
  - flutter_trading_app/lib/features/auth/screens/splash_screen.dart
  - flutter_trading_app/lib/features/dashboard/screens/dashboard_screen.dart
- Summary of changes: ~196 insertions, ~94 deletions across these files (diff stat provided in logs).

3. Patch plan (concrete changes)
- Notification delivery:
  - Add notification_delivery_log table (ID, user_id, notification_id, delivered_at, status)
  - Update notifications flow to log delivery attempts and implement idempotency using notification_id + correlation_id
  - Ensure ownership checks on read/mark operations
- User identity linkage:
  - Ensure user_id is propagated across notification/trades/portfolio operations; validate foreign-key integrity
- Streaming updates (optional for first pass):
  - Introduce a minimal WebSocket path or SSE endpoint for live state updates (feature flag or incremental rollout)
- Trading State Machine resilience:
  - Introduce fallback to a safe default state on IO errors and add structured error reporting
- Tests:
  - Add unit tests for dedupe path and for state machine fallback
  - Add integration tests for end-to-end notification path (mocked DB for test)

4. Validation plan
- Local unit tests pass; lint passes; build passes
- If possible: run the integration path with mocked DB to simulate IO errors and verify fallback paths

5. Deployment plan (high level)
- Branch: patch/server-health-fix-YYYYMMDD
- PR to main; CI should run tests and lint
- Deploy to staging; monitor health and logs for 24h
- Rollback plan: revert patch branch or roll back to previous tag

End Patch
