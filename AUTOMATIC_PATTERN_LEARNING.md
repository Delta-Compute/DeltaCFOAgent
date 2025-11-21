# Automatic Pattern Learning System

## Overview

The system automatically learns classification patterns from your manual transaction classifications and validates them with Claude AI - **no manual intervention needed!**

## How It Works

```
1. User classifies transactions manually
          ↓
2. After 3 similar classifications, PostgreSQL trigger creates pattern suggestion
          ↓
3. Trigger sends NOTIFY to background service
          ↓
4. Background service automatically validates with Claude LLM
          ↓
5. If approved → Creates classification pattern + shows toast notification
6. If rejected → Logs reasoning (pattern was too generic/specific/unsafe)
```

## Setup (One-Time)

### 1. Apply Database Migration

```bash
# This adds the PostgreSQL NOTIFY to the trigger
psql -h 34.39.143.82 -U delta_user -d delta_cfo -f migrations/add_automatic_pattern_validation.sql
```

Or use Python helper:
```bash
python3 migrations/apply_automatic_validation_migration.py
```

### 2. Background Service (Automatic)

The pattern validation service **starts automatically** when Flask app launches. No manual intervention needed!

The service is integrated into `web_ui/app_db.py` and runs in a background daemon thread:

```python
# Automatically starts on Flask app launch
from pattern_validation_service import start_listener
import threading

pattern_thread = threading.Thread(target=start_listener, daemon=True)
pattern_thread.start()
```

**For Manual Testing Only:**
```bash
# Only use this for standalone testing (not needed in production)
./start_pattern_service.sh
```

## Usage

**That's it!** Just classify transactions normally. The system will:

1. ✅ Automatically detect patterns after 3 similar classifications
2. ✅ Automatically validate with Claude AI
3. ✅ Automatically create classification patterns if approved
4. ✅ Show toast notifications in the UI when patterns are created

## Monitoring

### Check Service Status
```bash
python3 check_pattern_system_status.py
```

Shows:
- Recent user classifications
- Pattern suggestions by status
- Most recent patterns
- Trigger status
- Notifications count

### View Logs
```bash
# If running manually
./start_pattern_service.sh
# Watch the console output

# If running as systemd service
sudo journalctl -u pattern-validation -f
```

### Check Database
```sql
-- See all pattern suggestions
SELECT * FROM pattern_suggestions ORDER BY created_at DESC;

-- See approved patterns
SELECT * FROM classification_patterns WHERE created_by = 'llm_validated';

-- See notifications
SELECT * FROM pattern_notifications ORDER BY created_at DESC;
```

## Toast Notifications

The system includes a complete real-time toast notification system that automatically alerts users when new patterns are approved by Claude AI.

### How It Works:

1. **Backend API**: Endpoints at `/api/pattern-notifications` serve unread notifications
2. **Frontend Polling**: JavaScript polls every 10 seconds for new notifications
3. **Toast Display**: Beautiful gradient toasts appear in top-right corner
4. **Auto-dismiss**: Toasts auto-hide after 8 seconds
5. **Smart Tracking**: localStorage prevents duplicate notifications
6. **Responsive**: Pauses when tab is hidden to save resources

### Implementation:

**API Endpoints** (already in `app_db.py`):
- `GET /api/pattern-notifications` - Fetch notifications (supports `unread_only` and `limit` params)
- `POST /api/pattern-notifications/<id>/mark-read` - Mark notification as read

**Frontend** (`static/js/pattern_notifications.js`):
- `PatternNotificationManager` class handles polling and display
- Automatically included in all pages via `_navbar.html`
- Exposes `window.patternNotificationManager` for debugging

**Debug Commands** (browser console):
```javascript
// Check for new notifications immediately
window.patternNotificationManager.checkNow()

// Clear seen notifications (for testing)
window.patternNotificationManager.clearSeen()

// Stop polling
window.patternNotificationManager.stopPolling()

// Resume polling
window.patternNotificationManager.startPolling()
```

## Troubleshooting

### Service not starting
- Check `ANTHROPIC_API_KEY` is set in environment
- Check database connection in `.env`
- Check logs for specific errors

### Patterns not being created
- Verify trigger exists: `SELECT * FROM pg_trigger WHERE tgname LIKE '%pattern%';`
- Check pattern_suggestions table for pending patterns
- Verify background service is running
- Check Claude API key is valid

### All patterns being rejected
- This is normal! Claude is conservative and rejects:
  - Too-specific patterns (exact amounts, dates)
  - Too-generic patterns (single keywords)
  - Unsafe patterns (might match unrelated transactions)
- Try classifying different types of transactions with clear, consistent patterns

## Files Created

1. `migrations/add_automatic_pattern_validation.sql` - Database migration with PostgreSQL NOTIFY
2. `web_ui/pattern_validation_service.py` - Background service (listens for notifications)
3. `web_ui/static/js/pattern_notifications.js` - Frontend toast notification system
4. `start_pattern_service.sh` - Startup script for background service
5. `check_pattern_system_status.py` - Status checker and diagnostic tool
6. This README

## Files Modified

1. `web_ui/templates/_navbar.html` - Added pattern notifications script include
2. `web_ui/app_db.py` - Integrated pattern validation service startup in background thread

## Next Steps

- [x] ~~Add WebSocket/SSE for real-time toast notifications~~ **COMPLETED** - Polling-based system implemented
- [x] ~~Integrate service startup into Flask app~~ **COMPLETED** - Runs automatically in background thread
- [ ] Add UI page to view/manage pattern suggestions
- [ ] Add ability to manually approve/reject patterns from UI
- [ ] Add pattern effectiveness metrics (how many transactions auto-classified)
