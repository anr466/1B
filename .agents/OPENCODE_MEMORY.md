# OpenCode System Memory

**Purpose**: This memory file is shared across all your sessions within this project. Use it strictly to query and store context summarizing significant events, architectural decisions, and error-resolutions to avoid repeating mistakes or forgetting the project context.

> [!NOTE]
> Do NOT store large code snippets here. Only store contextual human-readable insights. Update this file implicitly when a significant event concludes.

## 1. Project Learned Rules & Quirks
*(Append new rules you discover that are not explicitly documented in AGENTS.md or PROJECT_BRAIN.md)*

- The primary tracking and intelligence model avoids blindly overwriting previous structural logic.
- We implement strict TOCTOU concurrency strategies across the `PositionManager`.

## 2. Event Log & Decisions
*(Append a brief line summarizing what happened, when, and the takeaway)*

| Date | Event / Issue Resolved | Key Takeaway / Decision |
|------|------------------------|-------------------------|
| 2026-04-14 | TradingOrchestrator Refactor | Consolidated trading checks. Deleted `UnifiedTradingEngine` because it was a parallel unreliable duplicate. |
| 2026-04-25 | Agent Memory Integration | Established `.agents/OPENCODE_MEMORY.md` as the core cross-session event-listener system to retain context without polluting the file system. |
