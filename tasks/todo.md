# P&L Trend Chart - Implementation Plan

## Overview
Build a new P&L Trend chart in the /reports section that displays monthly Revenue, COGS, SG&A, and Net Income as vertical bar groups with interactive hover features including drill-down expense details and AI-generated Net Income insights.

## Requirements Summary
1. **Bar Chart**: Monthly bars showing Revenue, COGS, SG&A, Net Income
2. **Expense Drill-down**: On hover over expense bars (COGS, SG&A), show line item breakdown (leverage Sankey code)
3. **Net Income AI Summary**: On hover over Net Income bar, send data to Claude API for 1-paragraph summary
4. **Gross Margin Line**: Visual line connecting tops of Revenue and COGS bars showing GM %

## Architecture Analysis

### Existing Code to Leverage
1. **Sankey Breakdown API** (`reporting_api.py:3708-3852`):
   - `/api/reports/sankey-breakdown` endpoint
   - `extract_keywords_from_transactions()` function
   - Keyword extraction from justification/destination fields
   - Caching with 5-minute TTL

2. **Sankey Hover UI** (`cfo_dashboard.js:3147-3300`):
   - `showSankeyBreakdown()` function with cache
   - `createBreakdownTooltip()` for tooltip display
   - Debounced hover events (200ms)
   - Draggable tooltips

3. **Claude API Integration** (`homepage_generator.py`):
   - `anthropic.Anthropic` client usage
   - JSON response parsing
   - Error handling with fallback content

4. **Monthly P&L Data** (`reporting_api.py:2716-2915`):
   - `/api/reports/monthly-pl` endpoint
   - Revenue, expenses, profit per month
   - Category breakdowns

### Data Structure Needed
The P&L bars should map to these transaction categories:
- **Revenue**: Positive amounts (amount > 0)
- **COGS**: Negative amounts with categories containing "material", "inventory", "cost of goods", "COGS"
- **SG&A**: All other negative amounts (operating expenses)
- **Net Income**: Revenue - COGS - SG&A

## Implementation Tasks

### Phase 1: Backend API (2 files)
- [ ] Add new endpoint `/api/reports/pl-trend` in `reporting_api.py`
  - Returns monthly data with Revenue, COGS, SG&A, Net Income
  - Includes subcategory breakdowns for drill-down
  - Calculates Gross Margin % per month
- [ ] Add new endpoint `/api/reports/pl-trend/ai-summary` for Claude Net Income analysis
  - Receives month data (revenue, cogs, sga, net_income, trends)
  - Returns 1-paragraph AI summary of Net Income performance

### Phase 2: Frontend Page (2 files)
- [ ] Create new template `pl_trend.html` in `web_ui/templates/`
  - Chart container with proper sizing
  - Loading state indicator
  - Date range filters (reuse existing filter UI)
- [ ] Create JavaScript file `pl_trend.js` in `web_ui/static/js/`
  - Bar chart with Chart.js (mixed type for line overlay)
  - Four bar datasets: Revenue, COGS, SG&A, Net Income
  - Gross Margin % line dataset

### Phase 3: Hover Features (1 file - extend pl_trend.js)
- [ ] Add expense breakdown hover (leverage Sankey code)
  - Debounced hover events
  - Call existing `/api/reports/sankey-breakdown` with expense category
  - Display tooltip with line item breakdown
- [ ] Add Net Income AI summary hover
  - On hover, call `/api/reports/pl-trend/ai-summary`
  - Display AI paragraph in tooltip
  - Cache response to avoid repeated API calls

### Phase 4: Route & Navigation (1 file)
- [ ] Add route `/reports` in `app_db.py` to render pl_trend.html
- [ ] Add navigation link to navbar (if not already present)

### Phase 5: Testing & Polish
- [ ] Test with real data
- [ ] Handle empty/missing data gracefully
- [ ] Verify multi-tenant isolation
- [ ] Add unit tests for new API endpoints

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `web_ui/reporting_api.py` | Edit | Add `/api/reports/pl-trend` and `/api/reports/pl-trend/ai-summary` endpoints |
| `web_ui/templates/pl_trend.html` | Create | New template for P&L Trend page |
| `web_ui/static/js/pl_trend.js` | Create | JavaScript for chart and interactions |
| `web_ui/app_db.py` | Edit | Add `/reports` route |
| `web_ui/templates/_navbar.html` | Edit | Add Reports navigation link (if needed) |

## Key Technical Decisions

1. **Use Chart.js Mixed Type**: Bar chart with line overlay for Gross Margin %
2. **Reuse Sankey Breakdown API**: No new drill-down endpoint needed, leverage existing
3. **Simple Claude Integration**: New endpoint specifically for NI summary (don't modify existing homepage generator)
4. **Month Selection**: Click on month label or bar group to focus date range

## Success Criteria
- [ ] Bar chart displays monthly Revenue, COGS, SG&A, Net Income
- [ ] Hovering on COGS/SG&A bars shows expense line items
- [ ] Hovering on Net Income bar shows AI-generated summary paragraph
- [ ] Gross Margin % line visible between Revenue and COGS tops
- [ ] Works correctly with multi-tenant data isolation
- [ ] All existing functionality preserved (no regressions)

## Review Checklist
- [ ] Code follows KISS principle
- [ ] No hardcoded tenant IDs
- [ ] PostgreSQL-only queries
- [ ] Error handling with fallbacks
- [ ] Responsive chart sizing
- [ ] Documentation updated
