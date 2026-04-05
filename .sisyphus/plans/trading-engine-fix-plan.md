# Trading Engine Comprehensive Fix Plan

## Overview

This plan covers ALL identified issues across the entire trading engine,
organized by phase, module, and priority. Each fix is designed to work
harmoniously with the existing architecture without breaking existing functionality.

---

## Phase 1: Critical Trading Engine Fixes (Immediate — Breaks Trading)

### 1.1 Scanner: Prevent Duplicate Symbol Opens
**Module:** `backend/core/scanner_mixin.py`
**Problem:** Scanner tries to open BNBUSDT every cycle despite active position existing
**Impact:** UNIQUE constraint violations, phantom orders, wasted API calls
**Fix:**
- Before calling `_open_position()`, check if symbol already has active position
- Add to existing `open_positions_for_entry` check:
  ```python
  existing_symbols = {p['symbol'] for p in open_positions_for_entry}
  if sym in existing_symbols:
      continue  # Skip — already have position in this symbol
  ```
**Dependencies:** None
**Risk:** Low — only prevents duplicate opens

### 1.2 LIQ_EARLY_EXIT: Fix Premature Trade Killing
**Module:** `backend/analysis/liquidity_cognitive_filter.py`
**Problem:** Closes trades at -0.2% after 60 seconds (pnl <= 0 + liquidity < 55)
**Impact:** 4+ trades killed immediately, guaranteed losses
**Fix:**
- Change threshold from `pnl_frac <= 0` to `pnl_frac <= -0.01` (1% loss)
- Change liquidity threshold from `< 55` to `< 35` (very weak only)
- Change small profit exit from `< 0.005` to `< 0.003` with liquidity `< 25`
**Dependencies:** None
**Risk:** Low — only makes exit more conservative

### 1.3 MAX_HOLD: Smart Exit Instead of Blind Close
**Module:** `backend/core/position_manager.py` → `_manage_position()`
**Problem:** Closes at 6h regardless of PnL (loses -0.5% to -2.2%)
**Impact:** Legitimate positions closed prematurely
**Fix:**
- At MAX_HOLD: only close if losing OR profit < 0.3%
- If profit >= 0.3%: extend by 2h with tighter trailing
- If profit >= 1.0%: extend by 4h with aggressive trailing
**Dependencies:** 1.2 (LIQ_EARLY_EXIT fix)
**Risk:** Medium — changes exit timing

---

## Phase 2: Data Flow & Storage Fixes

### 2.1 Trailing Stop Persistence
**Module:** `backend/core/position_manager.py`
**Problem:** trailing_sl_price and highest_price never updated in DB (always 0)
**Impact:** On restart, trailing state is lost, positions managed incorrectly
**Fix:**
- In `_manage_position()`, after updating peak/trail in memory:
  ```python
  self.db.update_position_trailing(
      position_id, new_peak, new_trail_sl
  )
  ```
- Add `update_position_trailing()` method to database_manager
**Dependencies:** None
**Risk:** Low — adds DB writes, no logic change

### 2.2 entry_date Column Type Fix
**Module:** Database schema
**Problem:** `entry_date` is `text` type, cannot do time calculations
**Impact:** Cannot calculate hold duration, age of positions
**Fix:**
```sql
ALTER TABLE active_positions
  ALTER COLUMN entry_date TYPE timestamp with time zone
  USING entry_date::timestamp with time zone;
```
**Dependencies:** None
**Risk:** Medium — schema change, needs migration

### 2.3 Field Name Unification (position_type vs side)
**Module:** All layers
**Problem:** `position_type` in DB, `side` in signals, `position_type` in strategy
**Impact:** Confusion, potential bugs in exit logic
**Fix:**
- Standardize on `position_type` everywhere
- In signal dict: add `position_type` alias for `side`
- In strategy.check_exit: read `position_type` with fallback to `side`
**Dependencies:** None
**Risk:** Low — adds compatibility, no removal

### 2.4 Atomic Open: DB Before Demo Fill
**Module:** `backend/core/position_manager.py` → `_open_position()`
**Problem:** Demo fill executes before DB insert → phantom orders on failure
**Impact:** Balance deducted but no position record
**Fix:**
- Move DB insert BEFORE demo fill
- If DB insert fails → return immediately (no demo fill)
- If DB insert succeeds → execute demo fill
**Dependencies:** None
**Risk:** Medium — changes order of operations

---

## Phase 3: API & Integration Fixes

### 3.1 Active Positions API — is_demo Consistency
**Module:** `backend/api/mobile_trades_routes.py`
**Problem:** Already working (verified: mode=demo returns 2 positions, mode=real returns 0)
**Status:** ✅ No fix needed — already correct

### 3.2 Notification Auto-Mark-As-Read
**Module:** `backend/api/mobile_notifications_routes.py`
**Problem:** 10 of 13 notifications unread → user sees same notifications repeatedly
**Impact:** Poor UX, notification fatigue
**Fix:**
- Add `auto_mark_read=true` parameter to GET /notifications
- When app fetches notifications, mark fetched ones as read after 30s
- Add `mark_all_as_read` endpoint for bulk operation
**Dependencies:** None
**Risk:** Low

### 3.3 Portfolio API — Real Mode Empty
**Module:** `backend/api/mobile_endpoints.py`
**Problem:** Real portfolio shows $83.59 but no trades ever executed
**Impact:** Confusing for admin user
**Fix:**
- If real portfolio has no trades, show message: "No real trades yet"
- Add demo→real migration option in UI
**Dependencies:** None
**Risk:** Low

---

## Phase 4: Performance & Reliability

### 4.1 Scanner: Signal Quality Threshold
**Module:** `backend/core/scanner_mixin.py`
**Problem:** Same signal (BNBUSDT, score=23.17) qualifies every cycle
**Impact:** Wasted scanning, duplicate open attempts
**Fix:**
- Add minimum score threshold (e.g., score > 30)
- Add signal cooldown: same symbol cannot re-qualify for 4 hours after open
**Dependencies:** 1.1 (duplicate prevention)
**Risk:** Low — only filters weak signals

### 4.2 Cooldown Logic: Day Boundary Fix
**Module:** `backend/core/risk_manager_mixin.py`
**Problem:** Daily state reset at midnight may cause issues with timezone
**Impact:** Cooldown may not reset correctly
**Fix:**
- Use UTC for daily reset
- Store `last_reset` as date (not datetime)
- Compare dates, not timestamps
**Dependencies:** None
**Risk:** Low

### 4.3 Database Connection Pool
**Module:** `backend/infrastructure/db_access.py`
**Problem:** No connection pooling, each query opens new connection
**Impact:** Slow queries under load, potential connection exhaustion
**Fix:**
- Add connection pool (min=2, max=10)
- Reuse connections for batch operations
- Add connection health check
**Dependencies:** None
**Risk:** Medium — changes DB access pattern

---

## Phase 5: Testing & Verification

### 5.1 Backtest Verification
**Module:** Test suite
**Problem:** No automated verification that fixes improve results
**Fix:**
- Run backtest with all fixes applied
- Compare WR, PF, PnL against baseline
- Verify no regression in existing functionality
**Dependencies:** All previous phases
**Risk:** None — testing only

### 5.2 Live Monitoring Dashboard
**Module:** New feature
**Problem:** No real-time visibility into engine state
**Fix:**
- Add `/api/engine/status` endpoint with:
  - Current cycle status
  - Active positions with live PnL
  - Recent signals (qualified/rejected)
  - Error count
  - Memory usage
**Dependencies:** None
**Risk:** Low

### 5.3 Integration Tests
**Module:** Test suite
**Problem:** No tests for end-to-end trading flow
**Fix:**
- Test: Signal → Open → Manage → Close → Log
- Test: Duplicate prevention
- Test: LIQ_EARLY_EXIT thresholds
- Test: MAX_HOLD smart exit
- Test: Trailing persistence
**Dependencies:** All previous phases
**Risk:** None — testing only

---

## Execution Order

```
Phase 1 (Critical — Do First)
├── 1.1 Scanner: Prevent Duplicate Opens
├── 1.2 LIQ_EARLY_EXIT: Fix Premature Killing
└── 1.3 MAX_HOLD: Smart Exit

Phase 2 (Data Flow — Do Second)
├── 2.1 Trailing Stop Persistence
├── 2.2 entry_date Column Type Fix
├── 2.3 Field Name Unification
└── 2.4 Atomic Open: DB Before Demo Fill

Phase 3 (API — Do Third)
├── 3.2 Notification Auto-Mark-As-Read
└── 3.3 Portfolio API — Real Mode Empty

Phase 4 (Performance — Do Fourth)
├── 4.1 Scanner: Signal Quality Threshold
├── 4.2 Cooldown Logic: Day Boundary Fix
└── 4.3 Database Connection Pool

Phase 5 (Testing — Do Last)
├── 5.1 Backtest Verification
├── 5.2 Live Monitoring Dashboard
└── 5.3 Integration Tests
```

---

## Success Criteria

| Metric | Before | After |
|--------|--------|-------|
| Duplicate open attempts | Every 60s | 0 |
| LIQ_EARLY_EXIT false kills | 4+ per session | 0 |
| MAX_HOLD blind closes | All at 6h | Only losing/flat |
| Trailing persistence | 0% (never saved) | 100% |
| Unread notifications | 77% | <10% |
| Signal quality | Score 23 qualifies | Score >30 required |
| Backtest WR | 61.9% | >65% |
| Backtest PF | 1.94 | >2.5 |
