# Chatbot Implementation Plan

## Overview
Build a context-aware AI chatbot that appears on all pages of the DeltaCFOAgent application. The chatbot will have knowledge of the current tenant and their local accounting rules/business type.

## Implementation Tasks

### 1. Frontend Component (chatbot.html + chatbot.css + chatbot.js)
**Files to Create:**
- `web_ui/templates/components/chatbot.html` - HTML structure
- `web_ui/static/chatbot.css` - Styling for collapsed/expanded states
- `web_ui/static/chatbot.js` - Client-side chat logic

**Features:**
- Floating button in bottom-right corner
- Smooth expand/collapse animation
- Chat history display
- Message input field
- Loading indicators
- Mobile-responsive design

**Design:**
- Collapsed: Small circular button with chat icon (60x60px)
- Expanded: Chat window (350x500px) with header, messages area, and input
- Position: Fixed bottom-right with 20px margin
- Z-index: High (9999) to stay above all content

### 2. Backend API Endpoint
**File to Modify:**
- `web_ui/app_db.py` - Add `/api/chatbot` endpoint

**Functionality:**
- Accept POST requests with: `{message: string, history: array}`
- Load tenant context from session
- Load business knowledge for tenant
- Call Claude API with enriched context
- Return response with proper error handling

**Context Loading:**
- Tenant ID from `get_current_tenant_id()`
- Business entities from `business_knowledge.md`
- Transaction patterns and accounting rules
- Jurisdiction-specific accounting rules (to be extracted from tenant profile)

### 3. Tenant Context Loader
**File to Create:**
- `web_ui/chatbot_context.py` - Context builder for chatbot

**Functionality:**
- `get_tenant_profile(tenant_id)` - Load tenant business info
- `get_accounting_rules(tenant_id)` - Load jurisdiction-specific rules
- `build_chatbot_system_prompt()` - Create Claude system prompt with full context
- `format_chat_history()` - Format conversation history for Claude API

**Context Elements:**
- Tenant name and business entities
- Jurisdiction (US, Brazil, Paraguay, etc.)
- Accounting standards (GAAP, IFRS, local)
- Business type (trading, mining, services)
- Current financial metrics (optional)

### 4. Claude API Integration
**Use Existing:**
- Existing `claude_client` from `app_db.py:97`
- Existing `ANTHROPIC_API_KEY` environment variable

**Implementation:**
- Use `claude-3-5-sonnet-20241022` model
- System prompt with tenant context
- Conversation history support
- Streaming responses (optional enhancement)
- Error handling and fallback messages

### 5. Template Integration
**Files to Modify:**
- All templates in `web_ui/templates/`

**Approach:**
- Create `web_ui/templates/components/chatbot.html` as include
- Add `{% include 'components/chatbot.html' %}` to all pages
- Ensure CSS and JS files are linked in all templates
- Test on: dashboard.html, dashboard_advanced.html, revenue.html, invoices.html, etc.

### 6. Testing Checklist
- [ ] Chatbot appears on all pages
- [ ] Expand/collapse animations work smoothly
- [ ] Messages send and receive properly
- [ ] Tenant context is correctly loaded
- [ ] Accounting rules are mentioned in responses
- [ ] Chat history persists during conversation
- [ ] Mobile responsiveness works
- [ ] Error handling works (API failures)

## Technical Specifications

### Frontend Stack
- Pure HTML/CSS/JavaScript (no framework)
- Fetch API for backend communication
- LocalStorage for chat history persistence (optional)

### Backend Stack
- Flask endpoint: `POST /api/chatbot`
- Claude API: `anthropic` Python library
- Context from: PostgreSQL database + business_knowledge.md

### Security Considerations
- Validate tenant_id from session
- Sanitize user input before sending to Claude
- Rate limiting (future enhancement)
- Don't expose sensitive business data unnecessarily

## Files to Create/Modify

### New Files
1. `web_ui/templates/components/chatbot.html`
2. `web_ui/static/chatbot.css`
3. `web_ui/static/chatbot.js`
4. `web_ui/chatbot_context.py`

### Modified Files
1. `web_ui/app_db.py` - Add `/api/chatbot` endpoint
2. All templates in `web_ui/templates/` - Add chatbot include
3. Potentially create accounting rules data structure or file

## Implementation Principles
- **Simplicity**: Keep code simple and minimal
- **No Breaking Changes**: Only add new code, don't modify existing functionality
- **Reuse**: Use existing Claude client and tenant context
- **Consistency**: Match existing UI/UX patterns in the application

## Next Steps
1. Get approval for this plan
2. Implement step-by-step in order listed above
3. Test each component before moving to next
4. Commit changes with clear messages
5. Add review section to tasks/todo.md when complete

---

## Questions/Clarifications Needed
1. Should we add jurisdiction/accounting rules to the database or keep in markdown?
2. Do you want streaming responses or simple request/response?
3. Should chat history persist across page navigations?
4. Any specific accounting topics the chatbot should prioritize?
