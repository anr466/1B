## Blockers and Issues
- Issue 1: No remote access to server 72.60.190.188 from this environment. SSH/API keys not provided.
- Issue 2: Unclear current server state (is trading engine on? which flavors of DB are connected?).
- Issue 3: No DB credentials or connection strings available in this sandbox to validate Postgres schema and data.
- Issue 4: Flutter UI linkage verification requires running frontend and backend together; not possible offline.

- Open questions (to resolve with orchestrator):
- Are credentials and VPN accessible for a controlled live test?
- Is there a staging mirror we can deploy to first?
- Can we obtain a read-only DB snapshot to validate endpoints in isolation?
- If live access is blocked, we will perform offline/mock verification with documented caveats.
