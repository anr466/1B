Patch Plan v4 — Core separation, dedupe, and state consistency

1) Objective
- Solidify separation of concerns: Data Layer, Trading State Machine, Notifications, Identity, API, Frontend.
- Ensure end-to-end communication against a single source of truth (DB).
- Implement idempotent notification delivery, user_id propagation, and a minimal streaming path for live updates.

2) Changes by component
- Data Layer
  - Use DB wrapper (backend/core/db.py) for all writes/reads.
  - Ensure all DB access goes through get_read_connection/get_write_connection.

- Trading State Machine
  - Update get_state() to read from DB via wrapper; add _get_default_state(last_error) to return a safe fallback state.
  - Ensure all transitions AND reads update through a single write path to DB.

- Notifications
  - Implement notification_delivery_log table entry (user_id, notification_id, delivered_at, status) with unique constraint on (user_id, notification_id).
  - Implement NotificationService.log_delivery(user_id, notification_id, status, delivered_at=None) and is_duplicate(user_id, notification_id)
  - Integrate dedupe via log_delivery before sending a new notification, backed by DB wrapper.
  - Add correlation_id passthrough and an ACK mechanism placeholder.

- Identity/Auth
  - Ensure require_auth usage is consistent across routes; propagate user_id across services.
  - Guard critical endpoints with proper authentication checks.

- API & Frontend DTOs
  - Standardize responses for /system/status and /notifications to include last_update, reconcile_stats.
  - Align Flutter DTO parsing with new shapes.

- Streaming
  - Add skeleton WebSocket/SSE endpoint for live status updates (feature-flagged).

- Tests & Quality
  - Unit tests: DB wrapper integration, _get_default_state fallback, dedupe behavior.
  - Integration tests: end-to-end smoke test for a single trade lifecycle including notification.
  - Lint/build: ensure clean run locally.

- Deployment & Rollback
  - Branch: patch/server-health-fix-YYYYMMDD
  - Define Rollback: revert to previous tag/branch, restore previous DB state if needed.

3) Patch Snippets (pseudocode, to be adapted to actual code)
- backend/core/db.py: (already added)
- backend/core/trading_state_machine.py:
  - try:
      # read state via DB wrapper
    except Exception as e:
      return self._get_default_state(str(e))
  - def _get_default_state(self, last_error):
      return {"success": False, "trading_state": "ERROR", "state": "ERROR", "message": last_error, "last_update": now, ...}

- backend/core/notification_service.py:
  - def log_delivery(self, user_id, notification_id, status, delivered_at=None):
      # insert into notification_delivery_log
      pass
  - def is_duplicate(self, user_id, notification_id):
      return False

- database/postgres_schema.sql:
  - CREATE TABLE IF NOT EXISTS notification_delivery_log (
      id BIGSERIAL PRIMARY KEY,
      user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      notification_id BIGINT NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
      delivered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
      status TEXT DEFAULT 'delivered',
      UNIQUE(user_id, notification_id)
    );
  - CREATE INDEX IF NOT EXISTS idx_notification_delivery_user ON notification_delivery_log(user_id);

4) اختبارات مقترحة
- tests/test_notification_delivery.py: test_dedupe_delivery()
- tests/test_trading_state_fallback.py: test_fault_tolerance_on_db_io()
- tests/test_api_contracts.py: ensure DTOs are stable

5) خطة النشر وال Rollback
- CI: run full test suite ومراجعة الكود
- Deploy to staging: use patch/server-health-fix-YYYYMMDD
- Verify health endpoints post deployment (24h)
- Rollback: revert patch branch if issues emerge

End Patch Plan v4
