# System Fix and Redeployment Plan

## Objective
Correct errors, clean up code, unify responsibilities, redeploy to server, and verify stable operation before production release.

## Steps
1. **Environment & Service Recovery**
   - Ensure Docker daemon is running.
   - Recreate Docker volumes if corrupted.
   - Bring up all services with `docker compose up -d --build`.
   - Verify health endpoint (`/health`) returns 200.

2. **Database I/O Resilience**
   - Implement retry with exponential backoff (max 5 attempts) for all DB read/write operations in `backend/core/trading_state_machine.py` and any direct DB calls.
   - On final failure, return a safe default state (`ERROR` with `last_error` set) instead of triggering Emergency Stop.
   - Ensure all DB access goes through the unified `backend/core/db.py` wrapper.

3. **Authentication Fix**
   - Verify `backend/api/auth_middleware.py` defines `def require_auth(f): ...` and includes `__all__ = ['require_auth']`.
   - Update all import statements to `from backend.api.auth_middleware import require_auth`.
   - Run unit tests to confirm no import errors.

4. **Notification Deduplication**
   - Ensure `notification_delivery_log` table exists with `UNIQUE(user_id, notification_id)` (already in `postgres_schema.sql`).
   - Implement `NotificationService.log_delivery(user_id, notification_id, status, delivered_at=None)` and `is_duplicate(user_id, notification_id)`.
   - Integrate dedupe check before inserting a notification; skip duplicate inserts.
   - Pass `user_id` explicitly in all notification creation calls.

5. **Real‑time State Updates (UI)**
   - Add SSE endpoint `/stream/status` that streams the latest row from `system_status` every 2‑3 seconds.
   - In Flutter, replace polling with an `EventSource` listener updating UI state on each message.
   - As a fallback, reduce polling interval to ≤ 3 seconds and ensure API responses contain `last_update` and `reconcile_stats`.

6. **Test Environment Fix**
   - Ensure `tests/__init__.py` exists (already present) and is a proper package.
   - Adjust any test imports that rely on absolute paths; run tests from project root.
   - Run `pytest -q` (excluding heavy e2e if DB not yet stable) to verify unit test suite passes.

7. **Cleanup & Code Unification**
   - Remove any duplicate or dead code (e.g., `.Asynchronous_State_Machine` if obsolete).
   - Ensure consistent use of the DB wrapper across all modules.
   - Standardize API response DTOs (`state`, `last_update`, `reconcile_stats`, `message`).
   - Run lint (`flake8`) and fix any style issues.

8. **Deployment & Verification**
   - Create a feature branch: `patch/server-health-fix-YYYYMMDD`.
   - Push branch, open PR, run CI (unit tests, lint, build).
   - Deploy to staging/server: `docker compose down && docker compose up -d`.
   - Monitor health endpoint and logs for 24 hours.
   - Perform manual verification:
     - Check that user balances/positions update in near real‑time.
     - Verify notifications are not duplicated.
     - Confirm trading engine opens new trades when state is `RUNNING` and respects risk limits.
     - Validate that after a simulated DB IO fault, the system recovers to a safe state without entering Emergency Stop.
   - If all checks pass, merge to main and promote to production.

## Success Criteria
- Docker services all show `Up` in `docker compose ps`.
- Health endpoint returns `{"status":"ok"}` (or equivalent) consistently.
- No `Disk I/O error` messages in logs for at least 10 minutes.
- No `Connection refused` or 500 errors from auth imports.
- Notification deduplication verified (no duplicate alerts in UI).
- UI reflects state changes within ≤ 3 seconds.
- Trading engine executes trades according to strategy without stalling.
- All unit tests pass; lint passes with zero errors.
- Post‑deployment verification shows stable operation for 24 hours.

## Rollback Plan
- If any critical error appears post‑deploy, revert to previous tag/branch: `git checkout <previous-tag>` and `docker compose down && docker compose up -d`.
- Keep a backup of the database volume before running migrations.
