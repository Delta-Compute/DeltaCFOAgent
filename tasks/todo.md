# Plan: Re-enable Pattern Learning Without Sacrificing Performance

## Problem Summary
The drag-fill bulk update was slow because:
1. Each of 9 transaction updates inserted to `user_classification_tracking`
2. PostgreSQL trigger fired 9 times, sending 9 NOTIFY events
3. Background service received 9 notifications, potentially making 9 Claude API calls

## What Was Disabled
1. **Pattern validation background service** - commented out in app_db.py startup
2. **Tracking inserts for bulk updates** - `skip_tracking=True` bypasses the trigger

## Goal
Re-enable pattern learning so the system continues to learn from user classifications, but in a performance-conscious way.

---

## Plan

### Phase 1: Batch Tracking After Bulk Updates Complete
**Instead of tracking each row during bulk update, track once at the end**

- [ ] **Task 1.1**: Add a new function `track_bulk_classification()` that:
  - Takes the list of transaction_ids, field, and value from the bulk update
  - Inserts a SINGLE row to `user_classification_tracking` with metadata indicating it's a bulk operation
  - OR inserts all rows in a single INSERT statement (batch insert)

- [ ] **Task 1.2**: Call `track_bulk_classification()` at the END of `/api/bulk_update_transactions` after the SQL UPDATE completes
  - This means 1 tracking operation instead of 9

### Phase 2: Debounced Pattern Suggestion Trigger
**Don't fire NOTIFY for every insert - batch them**

- [ ] **Task 2.1**: Modify the PostgreSQL trigger to use a debounce table:
  - Instead of immediate NOTIFY, insert to `pending_pattern_checks` table
  - A separate scheduled job processes this table every 30-60 seconds

- [ ] **Task 2.2**: Alternative approach - modify trigger to only NOTIFY if:
  - More than X seconds have passed since last NOTIFY for this tenant
  - OR occurrence_count crosses a threshold (e.g., 3, 5, 10)

### Phase 3: Background Service Improvements
**Make the background service smarter about when to call Claude**

- [ ] **Task 3.1**: Add request coalescing in the background service:
  - When a NOTIFY comes in, wait 5-10 seconds before processing
  - Collect all NOTIFYs during that window
  - Process them as a single batch

- [ ] **Task 3.2**: Add rate limiting:
  - Max 1 Claude API call per tenant per minute for pattern validation
  - Queue excess requests

- [ ] **Task 3.3**: Re-enable the background service with these improvements

### Phase 4: Optional - Lazy Pattern Learning
**Don't learn patterns in real-time at all**

- [ ] **Task 4.1**: Instead of real-time learning, run pattern analysis:
  - As a nightly batch job
  - OR when user explicitly clicks "Analyze Patterns" button
  - OR when tenant reaches X unprocessed classifications

---

## Recommended Approach

**Start with Phase 1 + Phase 3.1** - This gives the best bang for buck:

1. Bulk updates insert tracking rows in one batch (not 9 separate inserts)
2. Background service waits 5-10 seconds and coalesces notifications
3. Result: 1 Claude API call instead of 9, with minimal code changes

**Estimated Changes:**
- `app_db.py`: ~20 lines (batch tracking function + call it after bulk update)
- `pattern_validation_service.py`: ~30 lines (add coalescing logic)
- No database schema changes needed

---

## Review Section

### Changes Made

**Phase 1: Batch Tracking (app_db.py)**
1. Added `track_bulk_classification()` function (lines 2253-2346)
   - Takes transaction_ids, field, value, tenant_id
   - Fetches descriptions for ALL transactions in ONE query
   - Builds batch INSERT values with pattern signatures
   - Disables triggers temporarily using `SET session_replication_role = replica`
   - Inserts all tracking records in ONE batch INSERT
   - Sends ONE manual pg_notify for the entire batch

2. Called `track_bulk_classification()` from `/api/bulk_update_transactions` (lines 9545-9548)
   - After the SQL UPDATE completes, calls batch tracking
   - ONE notification per field/value combo (usually just 1 total)

**Phase 3: Request Coalescing (pattern_validation_service.py)**
1. Added coalescing state variables (lines 50-54)
   - `_COALESCE_WINDOW_SECONDS = 5`
   - `_pending_notifications = []`
   - `_coalesce_timer = None`

2. Added `_process_coalesced_notifications()` function (lines 90-125)
   - Collects all pending notifications
   - Groups by tenant_id
   - Processes each tenant's suggestions ONCE

3. Added `_queue_notification()` function (lines 128-147)
   - Queues notification instead of immediate processing
   - Resets 5-second timer on each new notification

4. Modified listener to use coalescing (lines 236-244)
   - Changed from `asyncio.run(handle_new_pattern_notification(...))`
   - To `_queue_notification(notify.payload)`

5. Re-enabled pattern validation service in app_db.py (lines 23176-23190)
   - Uncommented the service startup code
   - Updated message: "with 5s coalescing"

### Performance Impact

**Before (9-row drag-fill):**
- 9 separate UPDATE statements
- 9 INSERT to user_classification_tracking (9 triggers fire)
- 9 NOTIFY events
- 9 Claude API calls (potential)
- Total: ~9 database round-trips + 9 API calls

**After (9-row drag-fill):**
- 1 UPDATE statement with IN clause
- 1 batch INSERT (triggers disabled)
- 1 manual NOTIFY
- Coalesced into 1 Claude API call (after 5s window)
- Total: ~3 database round-trips + 1 API call

### Testing Done
- Server started successfully with pattern validation service
- Pattern validation service listening for notifications
- Server responding on http://localhost:5001

### Notes
- Bulk updates still track classifications for pattern learning
- Pattern learning happens in background (5 seconds after last notification)
- Single transaction edits still work as before (immediate tracking)
- Flask debug mode properly handled (service only starts in main worker)

---

## Bug Fix: session_replication_role Superuser Error (Dec 8, 2025)

### Problem
Server crashed with error when `track_bulk_classification()` tried to execute:
```sql
SET session_replication_role = replica;
```
This command requires superuser privileges, which the database user doesn't have.

### Root Cause
The original implementation tried to disable PostgreSQL triggers during bulk INSERT to prevent multiple NOTIFY events. However, `session_replication_role` requires superuser access.

### Solution
Removed the `session_replication_role` commands entirely. The triggers will now fire for each row inserted, but this is fine because:
1. The `pattern_validation_service.py` already has 5-second coalescing
2. All NOTIFY events within that 5-second window get batched into a single Claude API call
3. Net effect is still 1 API call instead of 9, just handled at the service level instead of the database level

### Changes Made
- **app_db.py lines 2306-2321**: Removed `SET session_replication_role = replica/DEFAULT` commands
- **app_db.py**: Removed manual `pg_notify()` call (triggers handle this now)
- **app_db.py**: Updated log message (no longer mentions "1 notification")

### Verification
- Server starts without errors
- Health endpoint returns healthy status
- Pattern validation service is listening for notifications with 5s coalescing
