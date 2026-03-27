## Known Problems / Open Risks
- Open risk: No access to the target server; cannot validate endpoints or DB connectivity today.
- Open risk: If provided credentials, there may be RBAC constraints that must be tested (admin vs normal user) and proper logging.
- Open risk: Potential data drift between backend state and UI state if not all providers refresh correctly.
- Open risk: No rollback steps executable in this sandbox; must document rollback plan for production-like environment.
 - Open risk: Network security restrictions (CORS, auth tokens) may block API interactions between FastAPI and Flask endpoints.
- Action plan: Define mitigations (CORS policies, token exchange) and document fallback modes in case of partial outages.
