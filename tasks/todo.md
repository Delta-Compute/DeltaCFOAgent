# P&L Trend Chart - Implementation Plan

## Overview
Build a new P&L Trend chart in the /reports section that displays monthly Revenue, COGS, SG&A, and Net Income as vertical bar groups with interactive hover features including drill-down expense details and AI-generated Net Income insights.

## Requirements Summary
1. **Bar Chart**: Monthly bars showing Revenue, COGS, SG&A, Net Income
2. **Expense Drill-down**: On hover over expense bars (COGS, SG&A), show line item breakdown (leverage Sankey code)
3. **Net Income AI Summary**: On hover over Net Income bar, send data to Claude API for 1-paragraph summary
4. **Gross Margin Line**: Visual line connecting tops of Revenue and COGS bars showing GM %

## Implementation Tasks

### Phase 1: Backend API (2 files)
- [x] Add new endpoint `/api/reports/pl-trend` in `reporting_api.py`
  - Returns monthly data with Revenue, COGS, SG&A, Net Income
  - Includes subcategory breakdowns for drill-down
  - Calculates Gross Margin % per month
- [x] Add new endpoint `/api/reports/pl-trend/ai-summary` for Claude Net Income analysis
  - Receives month data (revenue, cogs, sga, net_income, trends)
  - Returns 1-paragraph AI summary of Net Income performance

### Phase 2: Frontend Page (2 files)
- [x] Create new template `pl_trend.html` in `web_ui/templates/`
  - Chart container with proper sizing
  - Loading state indicator
  - Date range filters (reuse existing filter UI)
- [x] Create JavaScript file `pl_trend.js` in `web_ui/static/js/`
  - Bar chart with Chart.js (mixed type for line overlay)
  - Four bar datasets: Revenue, COGS, SG&A, Net Income
  - Gross Margin % line dataset

### Phase 3: Hover Features (1 file - extend pl_trend.js)
- [x] Add expense breakdown hover
  - Debounced hover events
  - Display tooltip with category breakdown from API response
- [x] Add Net Income AI summary hover
  - On hover, call `/api/reports/pl-trend/ai-summary`
  - Display AI paragraph in tooltip
  - Cache response to avoid repeated API calls

### Phase 4: Route & Navigation (1 file)
- [x] Add route `/reports/pl-trend` in `app_db.py` to render pl_trend.html
- [x] Add P&L Trend card to CFO dashboard reports grid

### Phase 5: Testing & Polish
- [x] Add unit tests for new API endpoints
- [x] Verify multi-tenant isolation (tenant_id required)
- [x] Error handling with fallbacks

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `web_ui/reporting_api.py` | Edit | Added `/api/reports/pl-trend` and `/api/reports/pl-trend/ai-summary` endpoints (~400 lines) |
| `web_ui/templates/pl_trend.html` | Create | New template for P&L Trend page |
| `web_ui/static/js/pl_trend.js` | Create | JavaScript for chart and hover interactions (~450 lines) |
| `web_ui/app_db.py` | Edit | Added `/reports/pl-trend` route |
| `web_ui/templates/cfo_dashboard.html` | Edit | Added P&L Trend card to reports grid |
| `tests/test_pl_trend_api.py` | Create | Unit tests for new API endpoints |

## Key Technical Decisions

1. **Use Chart.js Mixed Type**: Bar chart with line overlay for Gross Margin %
2. **Custom Breakdown Display**: Built-in breakdown from API response instead of Sankey API (simpler, dedicated data)
3. **Simple Claude Integration**: New endpoint specifically for NI summary with fallback when API unavailable
4. **Caching**: AI summary responses cached in memory to avoid repeated API calls

## Success Criteria
- [x] Bar chart displays monthly Revenue, COGS, SG&A, Net Income
- [x] Hovering on COGS/SG&A bars shows expense line items
- [x] Hovering on Net Income bar shows AI-generated summary paragraph
- [x] Gross Margin % line visible (purple line with right Y-axis)
- [x] Works correctly with multi-tenant data isolation
- [x] All existing functionality preserved (no regressions)

## Review Checklist
- [x] Code follows KISS principle
- [x] No hardcoded tenant IDs (uses get_current_tenant_id with strict=True)
- [x] PostgreSQL-only queries
- [x] Error handling with fallbacks
- [x] Responsive chart sizing
- [x] Unit tests added

---

## Review Section

### Summary of Changes Made

**Backend (reporting_api.py):**
1. Added `/api/reports/pl-trend` endpoint (lines 6111-6375):
   - Queries transactions with COGS/SG&A separation based on category keywords
   - Returns monthly data with revenue, cogs, sga, net_income, gross_margin_percent
   - Includes category breakdowns for both COGS and SG&A
   - Supports date range filters and internal transaction filtering

2. Added `/api/reports/pl-trend/ai-summary` endpoint (lines 6377-6504):
   - Accepts month data and trend context
   - Calls Claude API (claude-sonnet-4-5-20250929) for analysis
   - Returns 1-paragraph professional CFO summary
   - Falls back to generated summary when API unavailable

**Frontend:**
1. Created `pl_trend.html` template:
   - Summary stats cards (Revenue, COGS, SG&A, Net Income, Gross Margin)
   - Filter controls (time range, transaction type)
   - Chart container and breakdown sections
   - Firebase auth integration

2. Created `pl_trend.js` JavaScript:
   - Chart.js bar chart with 4 datasets + line overlay
   - Debounced hover events for tooltips
   - AI summary caching to reduce API calls
   - Dynamic tooltip positioning

**Navigation:**
1. Added `/reports/pl-trend` route in app_db.py
2. Added P&L Trend card to CFO dashboard reports grid

**Testing:**
1. Created `tests/test_pl_trend_api.py` with unit tests for:
   - pl-trend endpoint success/empty/filters
   - ai-summary endpoint with/without Claude API
   - Page route rendering

### Notes
- COGS detection uses category keyword matching (material, inventory, cogs, cost of goods, cost of sales)
- All other expenses are classified as SG&A
- Gross margin line uses secondary Y-axis (0-100%)
- AI summaries are cached per month+net_income combination
