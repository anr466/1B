Deployment Plan: Safe update to server + rollback

1. Prerequisites
- Ensure Docker daemon is running and accessible on the target server.
- Confirm that health endpoints are reachable post-deploy.
- Confirm that database migrations are in a known good state (backup available).

2. Deployment Steps (step-by-step)
- Create patch branch and ensure tests pass locally.
- Push patch branch to remote and create a PR.
- On server: pull latest patch branch, run docker-compose build, then docker-compose down && docker-compose up -d.
- Validate health endpoints within 5-10 minutes after restart.
- Monitor logs for 24h for any anomalies (disk IO, IO errors, auth errors).

3. Rollback Plan
- If health endpoints fail or critical errors appear:
  - Roll back to previous commit/branch (git reset --hard to last good commit) or checkout the previous deployed tag.
  - Run docker-compose down and docker-compose up to restore previous state.
- Keep a hot backup of DB state prior to migrations.

4. Verification Checklist
- Health endpoint returns expected status.
- No recurring Disk IO errors in logs within first 24h.
- UI reflects updated trading state and notifications without duplicates.
- All tests pass in CI/local tests.

End Patch
