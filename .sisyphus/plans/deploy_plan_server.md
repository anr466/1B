# Deployment Plan: Safe update to server + rollback

## 1. Prerequisites
- Ensure Docker daemon is running and accessible on the target server.
- Confirm that health endpoints are reachable post-deploy.
- Confirm that database migrations are in a known good state (backup available).
- Ensure you have SSH access to the server with the necessary permissions.
- Ensure you have the latest code from the local machine (or from a remote repository if pushing is set up).

## 2. Deployment Steps (step-by-step)
### 2.1 Preparation on Local Machine
- Run the full test suite locally to ensure nothing is broken: `pytest tests/ -v`
- Ensure lint passes: `flake8 backend/ --count` (should return 0)
- If there are any uncommitted changes, either commit them or stash them for a clean deployment.
- Tag the current commit (e.g., `git tag -a deploy-pre-$(date +%Y%m%d%H%M%S) -m "Pre-deployment backup"`).

### 2.2 On the Server
- SSH into the server: `ssh root@72.60.190.188` (password: provided separately)
- Navigate to the project directory: 
  - First check if it's in the common locations: `ls -ld /root/trading_ai_bot-1 /home/anr/trading_ai_bot-1 /var/www/trading_ai_bot-1 2>/dev/null || echo "Checking common locations..."`
  - Then navigate to the correct one (based on environment, likely `/root/trading_ai_bot-1` or `/home/anr/trading_ai_bot-1`)
  - For this deployment we'll use: `cd /root/trading_ai_bot-1` (verify this is correct by checking for docker-compose.yml and .env)
- Fetch the latest changes: `git fetch origin`
- Reset to the latest main (or the branch we want to deploy): `git reset --hard origin/main`
- Alternatively, if we have a specific tag or branch for deployment, checkout that.

### 2.3 Database Backup and Migration Check
- Backup the database (if PostgreSQL is used): 
  ```
  docker exec trading-ai-postgres pg_dump -U trading_user trading_ai_bot > /tmp/trading_ai_bot_$(date +%Y%m%d%H%M%S).sql
  ```
  Then copy the backup to the host if needed: `docker cp trading-ai-postgres:/tmp/trading_ai_bot_*.sql ./backups/`
- Check if the `notification_delivery_log` table exists (we added this in our local schema):
  ```
  docker exec trading-ai-postgres psql -U trading_user -d trading_ai_bot -c "\d notification_delivery_log"
  ```
  If the table does not exist, apply the schema changes from `database/postgres_schema.sql`:
  ```
  docker exec -i trading-ai-postgres psql -U trading_user -d trading_ai_bot < database/postgres_schema.sql
  ```
  Note: This should be idempotent if the table already exists (due to `IF NOT EXISTS` in the schema, but we should verify).

### 2.4 Rebuild and Restart Services
- Rebuild the Docker images (if there were changes to the Dockerfile or dependencies): 
  ```
  docker-compose build
  ```
- Bring up the services in detached mode:
  ```
  docker-compose down
  docker-compose up -d
  ```

### 2.5 Post-Deployment Validation
- Wait for the services to start (give them ~30 seconds).
- Validate the health endpoint: 
  ```
  curl -s http://localhost:3002/health | jq .
  ```
  Expected output: `{"status":"healthy","database":"connected","server":"unified","version":"1.0.0"}`
- Monitor the logs for any errors in the first 5 minutes:
  ```
  docker-compose logs --tail=100 -f
  ```
  Look for any tracebacks, Disk I/O errors, or authentication errors.

## 3. Rollback Plan
- If health endpoints fail or critical errors appear:
  - Roll back to the previous commit/branch (we tagged before deployment): 
    ```
    git reset --hard <previous-tag>
    ```
    Alternatively, if we didn't tag, we can use the reflog or known good commit.
  - Restore the database from the backup taken before deployment:
    ```
    cat /tmp/trading_ai_bot_<backup-time>.sql | docker exec -i trading-ai-postgres psql -U trading_user trading_ai_bot
    ```
  - Restart the services:
    ```
    docker-compose down
    docker-compose up -d
    ```
- Keep a hot backup of the database state prior to migrations (already done in step 2.3).

## 4. Verification Checklist
- Health endpoint returns expected status.
- No recurring Disk IO errors in logs within first 24h.
- UI reflects updated trading state and notifications without duplicates.
- All tests pass in CI/local tests.
- Check that the notification_delivery_log table exists and is being used (if applicable).
- Verify that the trading engine state transitions are logged correctly (check logs for state transitions).

## 5. Post-Deployment Monitoring (Optional but Recommended)
- Set up a simple cron job or monitoring script to check the health endpoint every 5 minutes for the next 24 hours.
- Monitor the worker logs for any unusual patterns in the decision logs.

## End of Plan