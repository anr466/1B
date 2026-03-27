# Simulated Offline Verification Plan (No Live Server Access)

Objective
- Validate integration contracts across UI, API, DB, and Trading State Machine using a fully mocked/local test environment when live server access is unavailable.

Scope (single-task, non-regression focus)
- Verify data shapes for /health, /api/v2/version, /api/v2/portfolio (mocked data expectations)
- Validate RBAC boundaries using mocked users (admin vs normal)
- Validate trading enable/disable flows and UI propagation in a simulated state machine
- Validate notification_delivery_log logging in a mock DB (in-memory or sqlite)
- Exercise edge-cases: nulls, missing fields, timeouts, partial outages in mocked calls

Approach
- Build a lightweight docker-based mock stack that mimics the real endpoints and data models:
  - Mock FastAPI app exposing /health, /api/v2/version, /api/v2/portfolio
  - Mock Flask app exposing /portfolio
  - In-memory data stores for portfolio, system_status, notification_delivery_log
  - Simple TradingStateMachine mock with enable/disable and safety fallbacks
- Run integration tests against the mock stack and record outputs
- Compare mock outputs against the expected contracts; document any gaps

Artifacts to append to Windsurfrules notepads
- Verification results, any deviations from contract, and mitigation plan
- Re-audit notes with issues found and how they would be addressed in live environment

Limitations
- This offline simulation cannot validate live DB connections, actual RBAC enforcement against real data, or proper UI-provider wiring against live Flutter UI. It provides contract-level validation and a traceable audit trail for later live verification.

Execution steps (to run when authorized):
- Set up docker-compose with mock-fastapi, mock-flask, and sqlite instances
- Run mocks and collect logs from API responses and state transitions
- Append results to:
  - .sisyphus/notepads/deploy_plan_server/learnings.md
  - .sisyphus/notepads/deploy_plan_server/issues.md
  - .sisyphus/reports/re_audit_report.md
