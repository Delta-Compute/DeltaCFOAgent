# Phase 3: Frontend Implementation - Simplified Plan

## Current Status
✅ **Phase 1 Complete**: Database tables created (entities, business_lines, FK columns added)
✅ **Phase 2 Complete**: Backend APIs implemented (Entity & Business Line CRUD, Transaction API updates)

## Phase 3: Frontend UI (CURRENT)

### Overview
Create user interface for managing entities and business lines, following the same patterns as existing features (workforce, whitelisted accounts).

### Implementation Tasks

#### Task 3.1: Create Entity Management Page & JavaScript
**Goal**: Full CRUD interface for entities
**Files**:
- `web_ui/templates/entities.html` (NEW)
- `web_ui/static/js/entities.js` (NEW)

**Features**:
- Two-tab interface: "Entities" | "Business Lines"
- Entity list with statistics (transaction count, business line count)
- Create/Edit entity modal form
- Soft delete (mark as inactive)
- Visual indicators for active/inactive status
- Search and pagination
- Entity detail cards with key info (code, name, tax ID, currency)

**Pattern to Follow**: Similar to `workforce.html` and `workforce.js`

**Data from API**:
- GET `/api/entities` - List all entities
- POST `/api/entities` - Create new entity
- PUT `/api/entities/<id>` - Update entity
- DELETE `/api/entities/<id>` - Deactivate entity
- GET `/api/entities/<id>/stats` - Get entity statistics

#### Task 3.2: Create Business Line Management UI (Second Tab)
**Goal**: Manage business lines within entities
**Files**: Same as Task 3.1 (second tab in entities.html)

**Features**:
- Business lines grouped by entity
- Create/Edit business line modal
- Color picker for visual coding
- Set default business line per entity
- Active/inactive status toggle
- Shows transaction count per business line

**Data from API**:
- GET `/api/business-lines` - List all business lines
- GET `/api/business-lines?entity_id=<id>` - Filter by entity
- POST `/api/business-lines` - Create new
- PUT `/api/business-lines/<id>` - Update
- DELETE `/api/business-lines/<id>` - Deactivate

#### Task 3.3: Add Navigation Link
**Goal**: Make entities page accessible
**Files**: `web_ui/templates/_navbar.html`

**Changes**:
- Add link to `/entities` in navigation bar
- Position after "Workforce" before "File Manager"
- Use proper i18n keys

#### Task 3.4: Create Entity/Business Line Filters on Dashboard
**Goal**: Filter transactions by entity and business line
**Files**:
- `web_ui/templates/dashboard.html` (or transaction_categorization.html)
- Corresponding JavaScript file

**Features**:
- Entity dropdown filter (top-level)
- Business line dropdown filter (filtered by selected entity)
- "All Entities" / "All Business Lines" options
- Persist filter selection in session/localStorage
- Update transaction list when filters change

**Note**: Need to identify which dashboard template is the main transaction manager

#### Task 3.5: Update Transaction List Display
**Goal**: Show entity and business line badges on transactions
**Files**: Transaction list templates and JavaScript

**Features**:
- Entity badge (with entity code) on each transaction row
- Business line badge (with color) on each transaction row
- Clickable badges to filter by that entity/business line
- Visual hierarchy: Entity > Business Line

#### Task 3.6: Update Transaction Edit Modal
**Goal**: Allow assigning entity and business line when editing transaction
**Files**: Transaction detail/edit modal templates and JavaScript

**Features**:
- Entity dropdown (required)
- Business line dropdown (optional, filtered by entity)
- Cascading selection: changing entity updates business line options
- Auto-populate from current transaction values
- Validation: entity required, business line optional

#### Task 3.7: Add Homepage/Business Overview Widgets
**Goal**: Show entity summary on main dashboard
**Files**: `web_ui/templates/business_overview.html`, homepage JavaScript

**Features**:
- Entity statistics widget (count, total transactions)
- Entity selector for dashboard view
- Quick stats per entity (revenue, expenses)
- Link to full entity management page

### Implementation Approach

**Step 1**: Create standalone entities management page (Tasks 3.1-3.3)
- Build complete CRUD interface
- Test all operations work correctly
- Verify data isolation by tenant_id

**Step 2**: Integrate with transactions (Tasks 3.4-3.6)
- Add filters to transaction list
- Update transaction display
- Enable entity/business line assignment

**Step 3**: Dashboard integration (Task 3.7)
- Add widgets to homepage
- Enable entity-level reporting

### Design Patterns to Follow

1. **Reuse existing patterns**: Copy structure from `workforce.html` / `workforce.js`
2. **Two-tab layout**: Entities tab | Business Lines tab
3. **Modal forms**: Create/Edit in modals (not separate pages)
4. **Status badges**: Color-coded active/inactive indicators
5. **Responsive design**: Mobile-friendly like other pages
6. **Error handling**: Show user-friendly messages
7. **Loading states**: Spinners during API calls

### Validation Rules

**Entity Creation**:
- Code: Required, 2-20 characters, alphanumeric + underscore
- Name: Required, 1-255 characters, unique per tenant
- Base Currency: Required, 3-letter code (USD, EUR, BRL, etc.)
- Tax ID: Optional
- Entity Type: Optional

**Business Line Creation**:
- Entity: Required (dropdown selection)
- Code: Required, 2-20 characters, unique per entity
- Name: Required, 1-100 characters, unique per entity
- Color: Optional, hex format #RRGGBB
- Default: Only one default per entity

### Testing Checklist

**After Task 3.1-3.2 (Entity Management Page)**:
- [ ] Can create new entity
- [ ] Can edit existing entity
- [ ] Can deactivate entity (soft delete)
- [ ] Can create business line for entity
- [ ] Can edit business line
- [ ] Can set default business line
- [ ] Entity code and name validation works
- [ ] Business line code and name validation works
- [ ] Color picker works for business lines
- [ ] Pagination works
- [ ] Search works

**After Task 3.3 (Navigation)**:
- [ ] "Entities" link appears in nav bar
- [ ] Link navigates to /entities
- [ ] Active state shows on entities page

**After Task 3.4-3.6 (Transaction Integration)**:
- [ ] Entity filter shows all entities
- [ ] Business line filter updates when entity changes
- [ ] Filters work correctly
- [ ] Transaction rows show entity badge
- [ ] Transaction rows show business line badge (if assigned)
- [ ] Can assign entity when editing transaction
- [ ] Can assign business line when editing transaction
- [ ] Business line dropdown filtered by entity

**After Task 3.7 (Homepage)**:
- [ ] Entity stats widget shows on homepage
- [ ] Entity selector works
- [ ] Quick stats update when entity selected

### Success Criteria

1. ✅ Entities management page fully functional
2. ✅ Business lines management working
3. ✅ Navigation accessible and intuitive
4. ✅ Transactions can be filtered by entity/business line
5. ✅ Transactions display entity and business line clearly
6. ✅ Transaction editing includes entity/business line assignment
7. ✅ All features work with multi-tenant isolation
8. ✅ UI is consistent with existing application style
9. ✅ No JavaScript console errors
10. ✅ Mobile responsive

### Files to Create/Modify

**New Files**:
- `web_ui/templates/entities.html`
- `web_ui/static/js/entities.js`

**Modified Files**:
- `web_ui/templates/_navbar.html` (add navigation link)
- `web_ui/templates/dashboard.html` or transaction list template (add filters)
- Transaction list JavaScript (add entity/business line display)
- Transaction edit modal template (add entity/business line selectors)
- Transaction edit JavaScript (add cascading dropdown logic)
- `web_ui/templates/business_overview.html` (add entity stats widget)

### Technical Notes

1. **API Endpoints Available** (from Phase 2):
   - `/api/entities` (GET, POST)
   - `/api/entities/<id>` (GET, PUT, DELETE)
   - `/api/entities/<id>/stats` (GET)
   - `/api/business-lines` (GET, POST)
   - `/api/business-lines/<id>` (GET, PUT, DELETE)
   - `/api/transactions` (updated to support entity_id, business_line_id)

2. **Database Schema**:
   - `entities` table with UUID primary key
   - `business_lines` table with entity_id FK
   - `transactions.entity_id` FK (nullable for now)
   - `transactions.business_line_id` FK (nullable)

3. **Progressive Disclosure** (for future - Phase 4):
   - For now, show all entity/business line features
   - Phase 4 will add hiding logic for simple businesses

### Next Phase Preview
Phase 4 will add:
- Onboarding flow for entity setup
- Progressive disclosure (hide features for simple businesses)
- Smart defaults based on business complexity

---

## Implementation Order

1. **Start**: Task 3.1 (Entities page - Entities tab)
2. **Then**: Task 3.2 (Entities page - Business Lines tab)
3. **Then**: Task 3.3 (Add navigation link)
4. **Then**: Identify main transaction dashboard
5. **Then**: Task 3.4 (Add filters)
6. **Then**: Task 3.5 (Update transaction display)
7. **Then**: Task 3.6 (Update transaction edit modal)
8. **Finally**: Task 3.7 (Homepage widgets)

---

## Ready to Start?
Once approved, I'll begin with Task 3.1: Creating the entities management page following the workforce.html pattern.
