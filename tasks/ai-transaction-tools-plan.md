# AI Transaction Tools Feature Plan

## Problem Statement

The current chatbot implementation (`/api/chatbot`) has a significant limitation:

**Current State:**
- User asks: "Give me a financial summary"
- Bot responds with: Generic framework and concepts, then says "Please access your financial dashboard" or "I don't have access to your specific transaction data"

**Desired State:**
- User asks: "Give me a financial summary"
- Bot responds with: Actual data - "You have $125,450 in revenue this month, $89,320 in expenses, net income of $36,130. Your top expense categories are..."

## Root Cause

The chatbot uses direct Claude API calls without tool calling capabilities:

```python
# Current: web_ui/app_db.py:21249-21254
response = claude_client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    system=system_prompt,
    messages=messages
)
```

There are no tools defined, so Claude cannot query actual transaction data.

---

## Proposed Solution: Claude Tool Calling

Implement Claude's native tool calling feature to give the AI access to transaction data.

### Architecture Overview

```
[User Message]
    -> [/api/chatbot]
    -> [Claude API with tools]
    -> [Tool Call: get_transactions / get_financial_summary / etc.]
    -> [Execute tool, return data]
    -> [Claude generates response with actual data]
    -> [User sees real financial data]
```

---

## Implementation Tasks

### Phase 1: Define Transaction Tools

**Task 1.1: Create AI Tools Module**
- [ ] Create `web_ui/ai_tools.py` - Define tool schemas and execution handlers
- Tools to implement:
  1. `get_financial_summary` - Period-based summary (revenue, expenses, net income)
  2. `search_transactions` - Filter transactions by criteria
  3. `get_category_breakdown` - Spending/revenue by category
  4. `get_entity_summary` - Summary per business entity
  5. `get_recent_transactions` - List recent transactions
  6. `get_expense_analysis` - Top expenses, trends
  7. `get_revenue_analysis` - Top revenue sources, trends

**Task 1.2: Tool Schema Definitions**
```python
TRANSACTION_TOOLS = [
    {
        "name": "get_financial_summary",
        "description": "Get financial summary for a time period including total revenue, expenses, and net income",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["today", "this_week", "this_month", "last_month", "this_quarter", "this_year", "last_30_days", "last_90_days", "all_time"],
                    "description": "Time period for the summary"
                },
                "entity": {
                    "type": "string",
                    "description": "Optional: Filter by specific business entity"
                }
            },
            "required": ["period"]
        }
    },
    {
        "name": "search_transactions",
        "description": "Search and filter transactions by various criteria",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "transaction_type": {"type": "string", "enum": ["Revenue", "Expense", "All"]},
                "category": {"type": "string", "description": "Accounting category"},
                "entity": {"type": "string", "description": "Business entity"},
                "min_amount": {"type": "number", "description": "Minimum amount"},
                "max_amount": {"type": "number", "description": "Maximum amount"},
                "keyword": {"type": "string", "description": "Search in description"},
                "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20}
            }
        }
    },
    {
        "name": "get_category_breakdown",
        "description": "Get spending or revenue breakdown by category",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "enum": ["this_month", "last_month", "this_quarter", "this_year", "last_30_days"]},
                "type": {"type": "string", "enum": ["expenses", "revenue", "both"], "default": "both"}
            },
            "required": ["period"]
        }
    },
    # ... more tools
]
```

### Phase 2: Tool Execution Layer

**Task 2.1: Implement Tool Handlers**
- [ ] Create `execute_tool(tool_name, tool_input, tenant_id)` function
- [ ] Each tool handler queries the database using existing `load_transactions_from_db()`
- [ ] Format results for Claude to understand

**Task 2.2: Data Formatting**
- [ ] Create formatters that return concise, readable data
- [ ] Handle large result sets (summarize if >20 transactions)
- [ ] Include relevant metadata (totals, counts, percentages)

### Phase 3: Update Chatbot Endpoint

**Task 3.1: Modify `/api/chatbot` to use tool calling**
```python
# Updated approach
response = claude_client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=2048,  # Increased for data responses
    system=system_prompt,
    messages=messages,
    tools=TRANSACTION_TOOLS  # NEW: Add tools
)

# Handle tool use
while response.stop_reason == "tool_use":
    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    tool_result = execute_tool(
        tool_use_block.name,
        tool_use_block.input,
        tenant_id
    )

    # Continue conversation with tool result
    messages.append({"role": "assistant", "content": response.content})
    messages.append({
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": tool_use_block.id, "content": tool_result}]
    })

    response = claude_client.messages.create(...)
```

**Task 3.2: Update System Prompt**
- [ ] Add instructions for when to use tools
- [ ] Explain available tools and their purposes
- [ ] Guidelines for presenting data clearly

### Phase 4: Frontend Enhancements

**Task 4.1: Update Chat UI**
- [ ] Show loading indicator during tool execution
- [ ] Format financial data nicely (tables, charts if applicable)
- [ ] Add quick action buttons based on AI suggestions

**Task 4.2: Add Data Visualization (Optional)**
- [ ] Parse structured data from AI responses
- [ ] Render inline charts/tables in chat
- [ ] Link to full dashboard for detailed views

---

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `web_ui/ai_tools.py` | NEW | Tool definitions and execution handlers |
| `web_ui/app_db.py` | MODIFY | Update `/api/chatbot` endpoint for tool calling |
| `web_ui/chatbot_context.py` | MODIFY | Update system prompt with tool instructions |
| `web_ui/static/chatbot.js` | MODIFY | Handle tool execution indicators |

---

## Example User Interactions (After Implementation)

### Example 1: Financial Summary
```
User: Give me a financial summary

Bot: [Calls get_financial_summary(period="this_month")]

Bot Response:
Here's your financial summary for December 2024:

**Revenue**: $125,450.00 (42 transactions)
**Expenses**: $89,320.00 (156 transactions)
**Net Income**: $36,130.00

Top Revenue Sources:
- Trading Gains: $78,500 (62.5%)
- Consulting Fees: $32,450 (25.9%)
- Interest Income: $14,500 (11.6%)

Would you like me to break down the expenses by category?
```

### Example 2: Specific Query
```
User: What did we spend on software this quarter?

Bot: [Calls search_transactions(category="Software", period="this_quarter")]

Bot Response:
Your software expenses for Q4 2024:

**Total**: $12,450.00 across 8 transactions

Breakdown:
- Adobe Creative Cloud: $599.88/month x 3 = $1,799.64
- GitHub Enterprise: $21/user x 15 users x 3mo = $945.00
- AWS Services: $9,705.36

This is 14% of your total expenses this quarter.
```

### Example 3: Transaction Search
```
User: Show me all payments over $10,000 last month

Bot: [Calls search_transactions(min_amount=10000, period="last_month")]

Bot Response:
I found 5 transactions over $10,000 in November 2024:

1. Nov 5: Wire to Vendor ABC - $45,000 (Inventory)
2. Nov 12: Tax Payment - $23,500 (Tax Expense)
3. Nov 15: Payroll - $18,750 (Payroll)
4. Nov 22: Equipment Purchase - $15,200 (Capital Expense)
5. Nov 28: Insurance Premium - $12,000 (Insurance)

Total: $114,450.00
```

---

## Future Improvements (After Tool Implementation)

### 1. Conversational Data Exploration
- "Drill down into the trading gains"
- "Compare this month to last month"
- "Show me the trend over the last 6 months"

### 2. Proactive Insights
- AI identifies anomalies and alerts user
- "I noticed an unusual $50,000 expense yesterday"
- "Your revenue is down 15% compared to last month"

### 3. Action Suggestions
- "Would you like me to categorize this transaction as..."
- "I can create a recurring entry for this payment"
- "Should I flag this for review?"

### 4. Report Generation
- "Generate a monthly expense report"
- "Create a cash flow summary for the board"
- Export to PDF/CSV via AI command

### 5. Multi-Turn Analysis
- Maintain context across conversation
- "Now filter that by entity X"
- "Exclude internal transfers"

### 6. Natural Language Queries
- "How much did we pay John's company?"
- "What's our biggest expense category?"
- "Are we profitable this year?"

---

## Security Considerations

1. **Tenant Isolation**: All tool queries MUST filter by tenant_id
2. **Rate Limiting**: Limit tool calls per conversation
3. **Data Limits**: Cap transaction results to prevent token overflow
4. **Audit Logging**: Log all tool calls for security review
5. **Permission Checking**: Verify user has access to requested data

---

## Testing Plan

1. **Unit Tests**: Test each tool handler independently
2. **Integration Tests**: Test full conversation flow with tools
3. **Edge Cases**: Empty results, large datasets, invalid inputs
4. **Security Tests**: Cross-tenant access attempts, SQL injection
5. **Performance Tests**: Response time with tool calls

---

## Implementation Priority

| Priority | Task | Effort |
|----------|------|--------|
| 1 | Create ai_tools.py with get_financial_summary | Medium |
| 2 | Update /api/chatbot for tool calling | Medium |
| 3 | Add search_transactions tool | Low |
| 4 | Add category_breakdown tool | Low |
| 5 | Update frontend for better data display | Medium |
| 6 | Add remaining tools | Low |
| 7 | Add proactive insights | High |

---

## Review Checklist

- [x] All tools filter by tenant_id (security)
- [x] Error handling for database failures
- [x] Token limits respected (summarize large results)
- [x] System prompt updated with tool instructions
- [x] Frontend handles loading states
- [x] Unit tests for all tool handlers
- [ ] Integration test for full conversation flow (requires live API)

---

## Implementation Review (Completed Dec 9, 2024)

### Files Created/Modified

| File | Type | Description |
|------|------|-------------|
| `web_ui/ai_tools.py` | NEW | 700+ lines - Tool definitions and execution handlers |
| `web_ui/app_db.py` | MODIFIED | Updated `/api/chatbot` endpoint for tool calling |
| `web_ui/chatbot_context.py` | MODIFIED | Updated system prompt with tool usage instructions |
| `web_ui/static/chatbot.js` | MODIFIED | Added markdown formatting for bot responses |
| `web_ui/static/chatbot.css` | MODIFIED | Added styles for financial data display |
| `web_ui/tests/test_ai_tools.py` | NEW | 22 unit tests for AI tools |

### Tools Implemented

1. **get_financial_summary** - Period-based financial summaries with revenue, expenses, net income
2. **search_transactions** - Full-featured transaction search with filters
3. **get_category_breakdown** - Expense/revenue breakdown by category
4. **get_entity_summary** - Per-entity financial comparison
5. **get_recent_transactions** - Recent transaction list
6. **get_top_expenses** - Largest expense transactions
7. **get_top_revenue** - Largest revenue transactions

### Key Implementation Details

1. **Tool Calling Loop**: The chatbot endpoint now handles multiple tool calls (max 5 iterations) to prevent infinite loops while allowing complex queries.

2. **Tenant Security**: All tool handlers require and validate tenant_id. No fallbacks - queries fail explicitly if tenant context is missing.

3. **Data Formatting**: Results are formatted with currency symbols, percentages, and clear structure for Claude to interpret and present.

4. **Frontend Markdown**: Bot messages now parse markdown-like syntax for bold, lists, and highlights currency/percentage values with distinct styling.

### Test Results

```
Ran 22 tests in 0.013s
OK
```

All tests pass including:
- Tool definition validation
- Date range calculations
- Currency formatting
- Financial summary with data
- Search with results
- Empty result handling
- Limit enforcement

### What the User Gets

**Before:** "I don't have access to your specific transaction data. Please use the dashboard."

**After:** Real data like:
```
Financial Summary - This Month:

TOTALS:
- Total Revenue: $125,450.00 (42 transactions)
- Total Expenses: $89,320.00 (156 transactions)
- Net Income: $36,130.00
- Profit Margin: 28.8%
```
