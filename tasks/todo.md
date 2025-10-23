# Task: Simplify Similar Transactions Feature

## Problem Statement

The current "Find Similar Transactions" feature uses a complex machine learning approach that may be overcomplicated for the user's needs. We need to add a simpler, more transparent keyword-based matching approach alongside the existing ML approach, allowing users to toggle between the two methods.

## Current Implementation Analysis

### Existing Components:
1. **Backend** (`web_ui/app_db.py`):
   - `/api/ai/find-similar-after-suggestion` endpoint (line ~4132)
   - Uses Claude AI to analyze and find similar transactions
   - Pre-filters by wallet addresses and vendor keywords
   - Complex confidence scoring and candidate prioritization

2. **Frontend** (`web_ui/static/script_advanced.js`):
   - `findSimilarTransactionsAfterAISuggestion()` function (line ~2778)
   - Handles the "AI Suggestion" button workflow
   - Shows modal with similar transactions

3. **Chain Analyzer** (`web_ui/transaction_chain_analyzer.py`):
   - Complex pattern detection system
   - Multiple chain types (crypto, vendor, entity, amount, invoice)
   - Used for transaction relationship discovery

## Proposed Solution: "Simple Match" Approach

### Core Logic:
1. **Keyword-based matching** on:
   - Origin field
   - Destination field
   - Description field

2. **Fuzzy matching** using string similarity algorithms

3. **Confidence scoring**:
   - **High confidence (0.8-1.0)**: Matches all 3 fields (Origin + Destination + Description)
   - **Medium confidence (0.5-0.79)**: Matches 2 of 3 fields
   - **Low confidence (0.3-0.49)**: Matches 1 of 3 fields
   - **Penalty**: Reduce confidence by 0.2 if transaction amount differs by more than 2x

4. **Filter criteria**: Only suggest transactions that:
   - Match at least 1 field (Origin, Destination, or Description)
   - Already have Entity/Category/Subcategory that the target transaction is missing
   - Are not archived

### Implementation Plan:

## Task 1: Create Simple Match Engine Module ✅ COMPLETED
**File**: `web_ui/simple_match_engine.py`

**Purpose**: Standalone module for simple keyword-based transaction matching

**Key Functions**:
- `find_similar_simple(transaction, all_transactions, min_confidence=0.3)`
  - Takes a transaction and a pool of candidates
  - Returns matches with confidence scores

- `calculate_field_similarity(str1, str2)`
  - Fuzzy string matching using `difflib` or `fuzzywuzzy`
  - Returns similarity score 0.0-1.0

- `calculate_confidence(origin_match, dest_match, desc_match, amount_ratio)`
  - Combines field matches into overall confidence
  - Applies amount difference penalty

**Data Structure**:
```python
{
    'transaction_id': 'abc123',
    'confidence': 0.85,
    'match_details': {
        'origin_match': 0.9,
        'destination_match': 0.95,
        'description_match': 0.7,
        'amount_penalty': 0.0,
        'matched_fields': ['origin', 'destination', 'description']
    },
    'suggested_values': {
        'classified_entity': 'Delta LLC',
        'accounting_category': 'Technology',
        'subcategory': 'Software Licenses'
    }
}
```

## Task 2: Add Simple Match API Endpoint ✅ COMPLETED
**File**: `web_ui/app_db.py`

**New Route**: `/api/ai/find-similar-simple` (POST)

**Request Body**:
```json
{
    "transaction_id": "abc123",
    "match_mode": "simple",  // or "ml"
    "min_confidence": 0.3
}
```

**Response**:
```json
{
    "success": true,
    "match_mode": "simple",
    "original_transaction": {...},
    "similar_transactions": [
        {
            "transaction_id": "def456",
            "confidence": 0.85,
            "match_details": {...},
            "suggested_values": {...}
        }
    ],
    "total_found": 5
}
```

**Implementation Steps**:
1. Add new route handler
2. Fetch target transaction from database
3. Fetch candidate transactions (uncategorized or low confidence)
4. Call `simple_match_engine.find_similar_simple()`
5. Return results in standardized format

## Task 3: Update Frontend JavaScript ✅ COMPLETED
**File**: `web_ui/static/script_advanced.js`

**Changes**:
1. Add global state variable for match mode:
   ```javascript
   let matchMode = 'simple'; // default to simple
   ```

2. Create new function `getMatchModePreference()`:
   ```javascript
   function getMatchModePreference() {
       return localStorage.getItem('matchMode') || 'simple';
   }
   ```

3. Update `findSimilarTransactionsAfterAISuggestion()`:
   - Check match mode from toggle
   - Call appropriate endpoint based on mode
   - Display results with mode-specific UI elements

4. Add new function `toggleMatchMode()`:
   - Save preference to localStorage
   - Update UI toggle state
   - Show toast notification of mode change

## Task 4: Add UI Toggle Switch ✅ COMPLETED
**File**: `web_ui/templates/dashboard_advanced.html`

**Location**: Filter section (after line ~147, before "Apply Filters" button)

**HTML Structure**:
```html
<div class="filter-group" style="grid-column: 1 / -1;">
    <label style="display: block; margin-bottom: 10px;">
        <strong>🔍 Similar Transaction Matching Mode:</strong>
    </label>
    <div class="match-mode-toggle">
        <div class="toggle-container">
            <input type="radio" id="modeSimple" name="matchMode" value="simple" checked>
            <label for="modeSimple" class="toggle-option">
                <span class="toggle-icon">⚡</span>
                <span class="toggle-text">
                    <strong>Simple Match</strong>
                    <small>Fast keyword-based matching</small>
                </span>
            </label>
        </div>
        <div class="toggle-container">
            <input type="radio" id="modeML" name="matchMode" value="ml">
            <label for="modeML" class="toggle-option">
                <span class="toggle-icon">🤖</span>
                <span class="toggle-text">
                    <strong>ML Approach</strong>
                    <small>AI-powered intelligent matching</small>
                </span>
            </label>
        </div>
    </div>
    <div class="match-mode-description">
        <p id="modeDescription">
            <strong>Simple Match:</strong> Finds transactions with matching keywords in Origin, Destination, and Description fields.
            Best for quick categorization of similar vendors or recurring transactions.
        </p>
    </div>
</div>
```

**CSS Additions** (in `web_ui/static/style_advanced.css`):
```css
.match-mode-toggle {
    display: flex;
    gap: 15px;
    margin-bottom: 15px;
}

.toggle-container {
    flex: 1;
}

.toggle-container input[type="radio"] {
    display: none;
}

.toggle-option {
    display: flex;
    align-items: center;
    padding: 15px;
    border: 2px solid #ddd;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s ease;
    background: white;
}

.toggle-option:hover {
    border-color: #4CAF50;
    background: #f8f9fa;
}

.toggle-container input[type="radio"]:checked + .toggle-option {
    border-color: #4CAF50;
    background: #e8f5e9;
    box-shadow: 0 2px 8px rgba(76, 175, 80, 0.2);
}

.toggle-icon {
    font-size: 24px;
    margin-right: 12px;
}

.toggle-text {
    display: flex;
    flex-direction: column;
}

.toggle-text strong {
    font-size: 14px;
    color: #333;
}

.toggle-text small {
    font-size: 12px;
    color: #666;
    margin-top: 3px;
}

.match-mode-description {
    padding: 12px;
    background: #f5f5f5;
    border-radius: 6px;
    font-size: 13px;
    color: #555;
}
```

## Task 5: Handle AI Suggestion Button with Both Modes ✅ COMPLETED
**Location**: `web_ui/static/script_advanced.js`

**Update `showAISuggestions()` function**:
1. Check current match mode
2. When applying suggestions, use appropriate endpoint
3. Update modal UI to show which mode was used

**Modal Display Updates**:
- Show "Simple Match Results" or "ML Match Results" in header
- Display match confidence with mode-specific context
- For simple mode: Show which fields matched (Origin ✓, Destination ✓, Description ✓)

## Task 6: Testing Plan

### Manual Test Cases:

1. **Simple Mode - All Fields Match**:
   - Create transaction with distinct Origin/Dest/Description
   - Create similar transaction with same fields
   - Categorize first, check if second appears with high confidence

2. **Simple Mode - Partial Match**:
   - Create transaction with partial field matches
   - Verify confidence is medium (2 fields) or low (1 field)

3. **Simple Mode - Amount Penalty**:
   - Create transactions with same keywords but 3x different amounts
   - Verify confidence is reduced by penalty

4. **ML Mode - Existing Behavior**:
   - Verify ML mode still works with Claude AI
   - Check that complex patterns are detected

5. **Toggle Persistence**:
   - Switch between modes
   - Refresh page
   - Verify mode is remembered via localStorage

6. **UI/UX**:
   - Toggle should highlight selected mode
   - Description should update when mode changes
   - Modal should show mode-specific results

### Test Data Scenarios:
```
Transaction 1: Origin="Chase Bank", Dest="Anthropic", Desc="API Usage Feb 2025", Amount=$150
Transaction 2: Origin="Chase Bank", Dest="Anthropic", Desc="API Usage Jan 2025", Amount=$140
Expected: High confidence match (all 3 fields similar, amount similar)

Transaction 3: Origin="Chase Bank", Dest="Google Cloud", Desc="Cloud Services", Amount=$300
Expected: Medium confidence match (1 field similar - Origin)

Transaction 4: Origin="Wallet 0x1234", Dest="Exchange", Desc="USDT Transfer", Amount=$10000
Expected: Low/No match (different fields)
```

## Task 7: Documentation Updates

### Files to Update:
1. **README.md**: Add section about Simple Match vs ML Approach
2. **CLAUDE.md**: Document the new simple_match_engine module
3. **Code Comments**: Add detailed docstrings to new functions

### User Guide Content:
```markdown
## Similar Transaction Matching Modes

DeltaCFOAgent offers two approaches for finding similar transactions:

### ⚡ Simple Match (Recommended for Quick Categorization)
- **How it works**: Matches transactions based on keywords in Origin, Destination, and Description fields
- **Best for**:
  - Recurring vendors (e.g., monthly Anthropic API charges)
  - Same counterparty transactions (e.g., transfers to/from same wallet)
  - Quick bulk categorization
- **Confidence scoring**:
  - High (0.8-1.0): All 3 fields match
  - Medium (0.5-0.79): 2 of 3 fields match
  - Low (0.3-0.49): 1 of 3 fields match

### 🤖 ML Approach (Advanced Pattern Detection)
- **How it works**: Uses Claude AI to understand context, business logic, and complex patterns
- **Best for**:
  - Complex transaction chains
  - Cross-entity patterns
  - Crypto transaction sequences
  - Invoice-transaction matching

**To switch modes**: Use the toggle in the Advanced Filters section of the dashboard.
```

## Task 8: Commit and Push ⏳ PENDING

**Git Commands**:
```bash
git status
git add web_ui/simple_match_engine.py
git add web_ui/app_db.py
git add web_ui/static/script_advanced.js
git add web_ui/static/style_advanced.css
git add web_ui/templates/dashboard_advanced.html
git add tasks/todo.md
git commit -m "feat: Add Simple Match approach for finding similar transactions

- Create simple_match_engine.py for keyword-based matching
- Add fuzzy string matching with confidence scoring
- Implement UI toggle between Simple Match and ML Approach
- Add /api/ai/find-similar-simple endpoint
- Update frontend to support both matching modes
- Add comprehensive tests and documentation

Addresses user request to simplify similar transaction feature with transparent keyword matching alongside existing ML approach."

git push -u origin claude/simplify-similar-transactions-011CUQjgRuUK7easBKHEZ2Bb
```

## Implementation Order:

✅ 1. Research current implementation (COMPLETED)
✅ 2. Write this plan (COMPLETED)
⏳ 3. Create simple_match_engine.py (NEXT)
⏳ 4. Add API endpoint
⏳ 5. Update JavaScript
⏳ 6. Add UI toggle
⏳ 7. Test functionality
⏳ 8. Update documentation
⏳ 9. Commit and push

---

## Design Principles:

1. **Simplicity**: The simple match should be truly simple - just keyword matching with fuzzy logic
2. **Transparency**: Users should clearly see WHY a match was suggested (which fields matched)
3. **Choice**: Both modes should coexist - let users choose what works for them
4. **Performance**: Simple mode should be fast (no AI API calls)
5. **Consistency**: Results format should be similar between both modes for easy frontend handling

## Success Criteria:

- [ ] Simple match mode finds transactions with matching Origin, Destination, or Description
- [ ] Confidence scores accurately reflect match quality
- [ ] UI toggle works smoothly and persists preference
- [ ] AI suggestion button works with both modes
- [ ] Performance is noticeably faster for simple mode
- [ ] Code is well-documented and maintainable
- [ ] All existing functionality continues to work

---

**Status**: Plan complete, ready for user approval before implementation.
