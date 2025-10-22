# PR: Hierarchical account-based file organization with gap detection

## Overview
This PR enhances the `/files` page to organize uploaded files by account type with hierarchical display and intelligent gap detection, making it easy for users to identify missing months across all their accounts.

## Problem Statement
Previously, the files page showed a flat list of all uploaded CSV files, making it difficult for users to:
- Identify which files belong to which account
- Spot missing months in their upload history
- Assess data completeness across multiple accounts
- Organize records from different sources (checking, credit cards, crypto wallets)

## Solution

### Backend Changes (`web_ui/app_db.py`)

#### Enhanced Account Categorization
- **Checking Accounts**: Detects Chase checking and generic bank patterns
- **Credit Cards**: Identifies Chase cards, Visa, MasterCard, Amex, Discover
- **Crypto Wallets**: Recognizes Coinbase, Binance, Kraken, Bitcoin, Ethereum
- **Pattern Recognition**: Intelligent regex matching for various file naming conventions

#### Intelligent Gap Detection
- Compares consecutive file date ranges within each account
- Flags gaps > 7 days as significant
- Calculates gap duration in days and approximate months
- Provides detailed date ranges for missing periods

#### Coverage Metrics
- Calculates percentage of time span covered by uploaded files
- Color-coded indicators: Green (≥90%), Orange (70-89%), Red (<70%)
- Helps users quickly assess data completeness per account

### Frontend Changes (`web_ui/templates/files.html`)

#### Hierarchical Display
Files now organized under collapsible account headers:
```
🏦 Chase Checking ...2345
   ├─ Coverage: 95% | 12 files | 450 transactions
   ├─ 2024-01-01 to 2024-12-31
   └─ [Expand to see files]
      ├─ file1.csv (Jan 2024)
      ├─ ⚠️ GAP: 30 days missing (Feb 2024)
      └─ file2.csv (Mar 2024)
```

#### Visual Enhancements
- **Category Icons**: 🏦 Checking, 💳 Credit Card, 🪙 Crypto Wallet, 📄 Other
- **Collapsible Sections**: All accounts collapsed by default for clean view
- **Gap Warning Rows**: Red-highlighted rows showing missing time periods
- **Coverage Badges**: Color-coded percentages showing data completeness
- **Account Statistics**: Total transactions, active count, coverage at a glance

## Key Features

### 1. Multi-Source Support
Works with various file naming patterns:
- Chase bank exports: `Chase4774_20240101_20240131.csv`
- Generic date patterns: `transactions_20240101_20240131.csv`
- Crypto platforms: `coinbase_2024_Q1.csv`
- Fallback to transaction dates if filename lacks date patterns

### 2. Smart Gap Detection
- Identifies missing statement periods automatically
- Visual warnings make gaps immediately obvious
- Detailed information: days missing, approximate months, date ranges
- Helps users maintain complete financial records

### 3. Coverage Metrics
- Shows what percentage of the time span is covered
- Color-coded for quick visual assessment
- Account-level aggregation

### 4. Backward Compatibility
- Maintains all existing upload functionality
- Duplicate detection modal still works
- File download capability preserved
- No breaking changes to existing workflows

## Files Changed

| File | Changes | Description |
|------|---------|-------------|
| `web_ui/app_db.py` | +216 -0 | Enhanced account categorization, gap detection, coverage calculation |
| `web_ui/templates/files.html` | +588 -215 | Hierarchical UI, collapsible sections, gap warnings |
| `tasks/todo.md` | +77 | Implementation planning |
| `tasks/IMPLEMENTATION_SUMMARY.md` | +238 | Detailed technical documentation |

## Testing

### Manual Testing Steps
1. Start application: `cd web_ui && python app_db.py`
2. Navigate to: http://localhost:5001/files
3. Verify files are grouped by account
4. Upload test files with various naming patterns
5. Upload non-consecutive months to verify gap detection
6. Check that coverage percentages are calculated correctly

### Test Scenarios
- [ ] Single account with consecutive months (no gaps)
- [ ] Multiple accounts with different types
- [ ] Files with missing months (gap detection)
- [ ] Chase bank files
- [ ] Generic CSV files
- [ ] Crypto wallet exports
- [ ] Files without date patterns in filename
- [ ] Upload new files and verify duplicate detection still works

## Benefits

### For Users
1. **Easy organization**: See all files grouped by account at a glance
2. **Gap visibility**: Immediately identify missing months or periods
3. **Quick assessment**: Coverage percentages show data completeness
4. **Clean interface**: Collapsible sections reduce clutter
5. **Clear categorization**: Know which type of account each file represents

### For System
1. **Maintainable**: Simple, focused code changes following project philosophy
2. **Extensible**: Easy to add new account types or patterns
3. **Efficient**: Single database query with in-memory processing
4. **Scalable**: Handles any number of accounts and files

## Screenshots

### Before
Flat table showing all files mixed together without organization.

### After
Hierarchical view with:
- Account headers showing category, date range, and statistics
- Collapsible file lists per account
- Gap warnings between non-consecutive files
- Color-coded coverage indicators

## Technical Details

### Account Detection Algorithm
Uses cascading pattern matching:
1. Chase-specific patterns (known account numbers)
2. Crypto wallet patterns (platform names)
3. Generic credit card patterns (last 4 digits)
4. Generic checking patterns
5. Fallback to "Unknown" category

### Gap Detection Logic
```python
gap_days = (curr_start - prev_end).days - 1
if gap_days > 7:  # More than a week
    gap_months = gap_days // 30
    # Store gap info for display
```

### Coverage Calculation
```python
total_days_covered = sum(file_date_spans)
total_span = overall_end - overall_start
coverage_pct = (total_days_covered / total_span) * 100
```

## Future Enhancements (Optional)

- Manual gap acknowledgment (mark intentional gaps)
- Date range filtering
- Account renaming/editing
- Coverage reports export
- Smart alerts for new gaps

## Checklist

- [x] Code follows project's simplicity guidelines
- [x] Changes are minimal and focused
- [x] Backward compatibility maintained
- [x] No breaking changes to existing features
- [x] Documentation added (IMPLEMENTATION_SUMMARY.md)
- [x] Implementation plan documented (todo.md)
- [x] All commits properly formatted with Co-Authored-By

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
