# Task: Improve /files Page Organization

## Objective
Enhance the /files page to better organize uploaded files by account type (checking, credit card, crypto wallet) with clear time frame indicators to help users identify missing months.

## Current State Analysis
- **Route Handler:** `web_ui/app_db.py:4801-4878` - Files page query and categorization
- **Template:** `web_ui/templates/files.html` - Current flat table display
- **Account Detection:** Only detects Chase accounts (hardcoded account numbers)
- **Display:** Shows files in a simple table without grouping

## Planned Improvements

### 1. Enhanced Account Categorization
- **Current:** Only Chase credit cards and Chase accounts detected
- **New:** Support multiple account types:
  - **Checking Accounts** - Bank checking accounts
  - **Credit Cards** - All credit card accounts
  - **Crypto Wallets** - Cryptocurrency wallet statements
  - **Unknown** - Files that don't match patterns

### 2. Grouping and Organization
- Group files by account type and number
- Collapsible sections for each account
- Sort files within each account by date range
- Show account summary (total files, date coverage, transaction count)

### 3. Time Gap Detection
- Detect missing months between uploaded files
- Visual indicators showing gaps in coverage
- Calculate total time span covered per account
- Highlight accounts with incomplete coverage

### 4. UI Improvements
- **Account Headers:** Clear section headers for each account
- **Expandable Sections:** Click to expand/collapse each account group
- **Time Timeline:** Visual representation of covered periods
- **Gap Warnings:** Alert users to missing months
- **Statistics:** Show coverage metrics per account

## Implementation Plan

### Step 1: Backend Changes (app_db.py)
- Enhance account detection beyond just Chase
- Add logic to group files by account
- Implement time gap detection algorithm
- Calculate coverage statistics

### Step 2: Frontend Changes (files.html)
- Replace flat table with grouped account sections
- Add collapsible headers for each account
- Create timeline visualization for each account
- Add gap indicators between files

### Step 3: Testing
- Test with various file naming patterns
- Verify gap detection works correctly
- Ensure UI is responsive and intuitive

## Success Criteria
- [ ] Files are organized under account headers
- [ ] Users can easily see which accounts have uploads
- [ ] Time frames are clearly visible for each file
- [ ] Missing months are highlighted
- [ ] UI is clean and intuitive
- [ ] Works with Chase, crypto, and generic file patterns

## Technical Notes
- Keep changes minimal and focused
- Maintain backward compatibility
- Don't break existing upload functionality
- Use existing CSS classes where possible
- Follow project's simple, clean code philosophy

## Files to Modify
1. `web_ui/app_db.py` - Update `files_page()` function
2. `web_ui/templates/files.html` - Redesign template structure
