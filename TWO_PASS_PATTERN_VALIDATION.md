# Two-Pass Pattern Validation System

## Overview

The pattern learning system now uses an intelligent **two-pass validation** approach that recognizes recurring business transactions even when the description pattern isn't perfect.

## How It Works

### PASS 1: Basic Validation

Claude validates the pattern using:
- Pattern syntax quality
- Business context (entities, existing patterns)
- Sample transactions (up to 5 examples)
- Safety assessment (risk of false positives)

**If approved**: Pattern is created immediately
**If rejected**: System checks if this deserves a second look

### PASS 2: Enriched Validation (Triggered Automatically)

Pass 2 is triggered when EITHER:
1. **Recurring pattern detected**: Daily/weekly/monthly frequency + low amount variance (<15%)
2. **High user confidence**: 15+ manual classifications of the same transaction type

Pass 2 provides Claude with enriched context:
- **Temporal Analysis**: Frequency (daily/weekly/monthly), time span, regularity
- **Amount Consistency**: Mean, range, variance (coefficient of variation)
- **User Behavior Signal**: How many times the user manually classified this
- **Previous Rejection Reason**: What Pass 1 flagged as problematic

## Key Insight

**User behavior is a strong signal!** When someone manually classifies the same type of transaction 20+ times, they clearly recognize a pattern - even if the auto-generated description pattern has issues (like reversed word order).

## Example Scenario

**Your Bitcoin Mining Transactions**:

```
Transactions: 25 nearly identical Bitcoin deposits
Frequency: Daily
Amount: $285-$310 (variance <10%)
User classifications: 25 manual entries
```

**Pass 1 Result**:
- ❌ Rejected: "Pattern has reversed word order, won't match future transactions"

**Pass 2 Analysis**:
```
Temporal Pattern: daily
Amount Variance: 8.5% (very consistent!)
User has classified this 25 times
Previous rejection: Pattern syntax issue
```

**Pass 2 Result**:
- ✅ Approved: "Despite pattern syntax issues, the daily frequency (25 days), low amount variance (8.5%), and user's 25 manual classifications clearly indicate this is a legitimate recurring business transaction. The user recognizes this pattern and it should be automated."

## Configuration

The two-pass system activates automatically when:

```python
# Pass 2 triggers if:
if pattern_stats['is_recurring'] or pattern_data['occurrence_count'] >= 15:
    # Run enriched validation
```

### Recurring Pattern Criteria:

```python
is_recurring = (
    frequency in ['daily', 'weekly', 'monthly'] and
    amount_variance < 0.15  # Less than 15% variation
)
```

### Temporal Frequency Detection:

- **Daily**: Average interval ≤ 2 days, variance ≤ 2 days
- **Weekly**: Average interval ≤ 8 days, variance ≤ 3 days
- **Monthly**: Average interval ≤ 35 days, variance ≤ 7 days
- **Irregular**: Everything else

## Benefits

1. **Smarter Pattern Recognition**: Recognizes legitimate recurring transactions
2. **User-Centric**: Respects the user's repeated intent
3. **Temporal Awareness**: Understands daily/weekly/monthly patterns
4. **Amount Consistency**: Detects regular payments/receipts
5. **Cost-Effective**: Only runs Pass 2 when warranted (saves API calls)

## Testing

To test with your existing rejected patterns:

```bash
# Reset their status to pending
psql -h <host> -U <user> -d <database> << EOF
UPDATE pattern_suggestions
SET status = 'pending', llm_validation_result = NULL
WHERE id IN (6, 7, 8);
EOF

# Run validation
python3 process_pending_patterns.py
```

The system should now approve patterns that show:
- High occurrence count (15+)
- Temporal consistency (daily/weekly/monthly)
- Low amount variance (<20%)
- Business context alignment

## Next Steps

1. Continue classifying similar transactions (the system learns from your behavior)
2. When a new pattern is created, you'll see a toast notification
3. The pattern will automatically classify future similar transactions
4. Review approved patterns at `/tenant-knowledge`

## Technical Implementation

Files modified:
- `web_ui/pattern_learning.py`:
  - Added `calculate_pattern_statistics()` function
  - Enhanced `validate_pattern_with_llm()` with two-pass logic
  - Updated `build_validation_prompt()` to include enrichment context
  - Added `parse_validation_response()` helper function

The system is fully integrated - no manual intervention needed!
