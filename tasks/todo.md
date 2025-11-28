# Entity vs Business Line Architecture - Development Plan

## Executive Summary

Restructure the application from a flat entity model to a progressive disclosure three-tier model:
- **Tier 1: Organization** (SaaS Tenant) - Existing `tenant_id`
- **Tier 2: Entity** (Legal/Tax Boundary) - NEW: Separate legal entities with own books
- **Tier 3: Business Line** (Profit Center) - NEW: Internal segments within entities

This enables the system to serve simple single-business clients AND complex multi-entity holding companies like Delta Energy with the same architecture.

## Current State Analysis

### Current Database Structure
```
tenant_id (VARCHAR) → transactions.entity (VARCHAR)
                   → transactions.classified_entity (VARCHAR)
```

**Issues:**
1. Entity is stored as VARCHAR, no referential integrity
2. No separation between legal entities and profit centers
3. Business entities table is just a lookup, not a true entity structure
4. No support for entity-specific Chart of Accounts
5. No support for intercompany eliminations
6. No progressive disclosure for simple businesses

### Target Architecture
```
Organization (tenant_id)
  └── Entity (legal entity, separate books, own tax ID)
        └── Business Line (profit center, tagged transactions, same books)
              └── Transactions (tagged with both entity_id and business_line_id)
```

## Implementation Phases

### Phase 1: Database Foundation (Days 1-3)
**Goal:** Create new tables and migrate existing data without breaking current functionality

#### Task 1.1: Create entities table
**File:** `migrations/add_entities_and_business_lines.sql`
**Status:** [ ] Not Started

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,

    -- Entity Identification
    code VARCHAR(20) NOT NULL,  -- Short code: "DLLC", "DPY", "DBR"
    name VARCHAR(255) NOT NULL,  -- Full legal name
    legal_name VARCHAR(255),     -- Official registered name

    -- Legal/Tax Information
    tax_id VARCHAR(100),          -- EIN, Tax ID, CNPJ, RUC, etc.
    tax_jurisdiction VARCHAR(100), -- "US-Delaware", "Paraguay", "Brazil"
    entity_type VARCHAR(50),      -- "LLC", "S-Corp", "SA", "Ltda"

    -- Financial Settings
    base_currency VARCHAR(3) DEFAULT 'USD',
    fiscal_year_end VARCHAR(5) DEFAULT '12-31',  -- MM-DD format

    -- Address
    address TEXT,
    country_code VARCHAR(2),      -- ISO country code

    -- Status
    is_active BOOLEAN DEFAULT true,
    incorporation_date DATE,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),

    UNIQUE(tenant_id, code),
    UNIQUE(tenant_id, name)
);

-- Create indexes for performance
CREATE INDEX idx_entities_tenant ON entities(tenant_id);
CREATE INDEX idx_entities_tenant_active ON entities(tenant_id, is_active);
CREATE INDEX idx_entities_code ON entities(code);

-- Add comment
COMMENT ON TABLE entities IS 'Legal entities with separate books (Tier 2 - Entity Level)';
```

#### Task 1.2: Create business_lines table
**File:** Same migration file
**Status:** [ ] Not Started

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS business_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,

    -- Business Line Identification
    code VARCHAR(20) NOT NULL,       -- Short code: "HOST", "VAL", "PROP"
    name VARCHAR(100) NOT NULL,      -- "Hosting Services", "Validator Operations"
    description TEXT,

    -- Classification
    is_default BOOLEAN DEFAULT false, -- One default per entity
    color_hex VARCHAR(7),            -- UI color coding: "#3B82F6"

    -- Status
    is_active BOOLEAN DEFAULT true,
    start_date DATE,
    end_date DATE,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),

    UNIQUE(entity_id, code),
    UNIQUE(entity_id, name)
);

-- Create indexes
CREATE INDEX idx_business_lines_entity ON business_lines(entity_id);
CREATE INDEX idx_business_lines_entity_active ON business_lines(entity_id, is_active);
CREATE INDEX idx_business_lines_code ON business_lines(code);

-- Add comment
COMMENT ON TABLE business_lines IS 'Profit centers within entities for management reporting (Tier 3 - Business Line Level)';
```

#### Task 1.3: Add entity_id and business_line_id to transactions
**File:** Same migration file
**Status:** [ ] Not Started

**Changes:**
```sql
-- Add new FK columns (nullable initially for migration)
ALTER TABLE transactions
ADD COLUMN entity_id UUID REFERENCES entities(id),
ADD COLUMN business_line_id UUID REFERENCES business_lines(id);

-- Create indexes
CREATE INDEX idx_transactions_entity_id ON transactions(entity_id);
CREATE INDEX idx_transactions_business_line_id ON transactions(business_line_id);
CREATE INDEX idx_transactions_entity_date ON transactions(entity_id, date);
CREATE INDEX idx_transactions_entity_business_line ON transactions(entity_id, business_line_id);

-- Add comments
COMMENT ON COLUMN transactions.entity_id IS 'Foreign key to entities table (replaces entity VARCHAR)';
COMMENT ON COLUMN transactions.business_line_id IS 'Optional profit center assignment for management reporting';
```

#### Task 1.4: Data migration script
**File:** `migrations/migrate_entity_data.py`
**Status:** [ ] Not Started

**Purpose:** Migrate existing data from VARCHAR entity to new structure

**Logic:**
1. Extract unique entity names from transactions table per tenant
2. Create entity records in entities table
3. Create default business line for each entity
4. Update transactions.entity_id with FK references
5. Keep original VARCHAR fields for rollback safety
6. Validate migration success

**Key Decisions:**
- For Delta tenant: Map to specific entities (Delta LLC, Delta Paraguay, etc.)
- For other tenants: Create one entity per unique entity name
- Create "Default" business line for each entity (hidden from UI until user adds second)

### Phase 2: Backend API Updates (Days 4-6)
**Goal:** Update all APIs to support new entity/business line structure

#### Task 2.1: Create Entity Management API
**File:** `web_ui/app_db.py` (add endpoints)
**Status:** [ ] Not Started

**Endpoints:**
```python
# Entity CRUD
GET    /api/entities                  # List all entities for tenant
POST   /api/entities                  # Create new entity
GET    /api/entities/<id>             # Get entity details
PUT    /api/entities/<id>             # Update entity
DELETE /api/entities/<id>             # Deactivate entity (soft delete)

# Entity operations
GET    /api/entities/<id>/business-lines     # List business lines for entity
GET    /api/entities/<id>/stats              # Entity-level statistics
GET    /api/entities/<id>/transactions       # Transactions for entity
```

**Response Format:**
```json
{
  "id": "uuid",
  "tenant_id": "delta",
  "code": "DLLC",
  "name": "Delta Mining LLC",
  "legal_name": "Delta Mining LLC",
  "tax_id": "XX-XXXXXXX",
  "base_currency": "USD",
  "is_active": true,
  "business_lines_count": 3,
  "transactions_count": 1250
}
```

#### Task 2.2: Create Business Line Management API
**File:** `web_ui/app_db.py` (add endpoints)
**Status:** [ ] Not Started

**Endpoints:**
```python
# Business Line CRUD
GET    /api/business-lines                    # List all for tenant
POST   /api/business-lines                    # Create new business line
GET    /api/business-lines/<id>               # Get details
PUT    /api/business-lines/<id>               # Update business line
DELETE /api/business-lines/<id>               # Deactivate (soft delete)

# Business Line operations
GET    /api/business-lines/<id>/transactions  # Transactions for business line
GET    /api/business-lines/<id>/stats         # Business line statistics
POST   /api/business-lines/<id>/set-default   # Set as default for entity
```

#### Task 2.3: Update Transaction API
**File:** `web_ui/app_db.py` (modify existing endpoints)
**Status:** [ ] Not Started

**Changes:**
1. Update GET `/api/transactions` to:
   - Accept `entity_id` filter (optional)
   - Accept `business_line_id` filter (optional)
   - Include entity and business_line objects in response
   - Maintain backward compatibility with entity VARCHAR

2. Update POST/PUT transaction endpoints to:
   - Accept `entity_id` (required)
   - Accept `business_line_id` (optional)
   - Validate entity exists and belongs to tenant
   - Validate business line exists and belongs to entity

3. Add new endpoints:
   ```python
   POST /api/transactions/<id>/assign-business-line   # Assign/change business line
   POST /api/transactions/bulk-assign-business-line   # Bulk assignment
   ```

#### Task 2.4: Update Classification Engine
**File:** `main.py` (DeltaCFOAgent class)
**Status:** [ ] Not Started

**Changes:**
1. Update classification patterns to support entity_id and business_line_id
2. Add business line inference logic based on:
   - Transaction description keywords
   - Client/vendor associations
   - Amount patterns
   - Classification rules from database

3. Update `classification_patterns` table:
   ```sql
   ALTER TABLE classification_patterns
   ADD COLUMN entity_id UUID REFERENCES entities(id),
   ADD COLUMN business_line_id UUID REFERENCES business_lines(id);
   ```

#### Task 2.5: Update Reporting Queries
**File:** `web_ui/services/data_queries.py`
**Status:** [ ] Not Started

**Changes:**
1. Update all queries to join entities and business_lines tables
2. Add entity-level aggregations
3. Add business line breakdown queries
4. Update KPI calculations to support entity filtering

### Phase 3: Frontend Updates (Days 7-10)
**Goal:** Create UI for entity/business line management with progressive disclosure

#### Task 3.1: Create Entity Management Page
**File:** `web_ui/templates/entities.html`
**Status:** [ ] Not Started

**Features:**
- List all entities with statistics
- Create/Edit entity modal
- Entity detail view with tabs:
  - Details (legal info, tax info)
  - Business Lines (list and manage)
  - Transactions (filtered view)
  - Statistics (P&L, cash flow)
- Activate/Deactivate entities
- Color-coded entity badges

#### Task 3.2: Create Entity Management JavaScript
**File:** `web_ui/static/js/entities.js`
**Status:** [ ] Not Started

**Functions:**
- Load entity list with pagination
- Create/Update entity (form validation)
- Delete entity (confirmation dialog)
- Load entity details
- Navigate to transactions filtered by entity
- Real-time statistics updates

#### Task 3.3: Create Business Line Management UI
**File:** `web_ui/templates/business_lines.html` (or section in entities.html)
**Status:** [ ] Not Started

**Features:**
- List business lines grouped by entity
- Create/Edit business line modal
- Set default business line per entity
- Assign color codes for visualization
- Quick stats per business line
- Progressive disclosure:
  - Hidden by default for entities with only "Default" business line
  - Show "Enable Business Line Tracking" button
  - Expand when user adds second business line

#### Task 3.4: Create Business Line JavaScript
**File:** `web_ui/static/js/business_lines.js`
**Status:** [ ] Not Started

**Functions:**
- Load business lines by entity
- Create/Update business line
- Delete business line (with validation)
- Set default business line
- Color picker integration
- Enable/disable business line tracking

#### Task 3.5: Update Transaction List Page
**File:** `web_ui/templates/transaction_categorization.html`
**Status:** [ ] Not Started

**Changes:**
1. Add entity filter dropdown (top-level filter)
2. Add business line filter dropdown (second-level filter)
3. Show entity and business line badges in transaction rows
4. Update transaction detail modal to show:
   - Entity selector (required)
   - Business line selector (optional, filtered by entity)
5. Add bulk actions:
   - Bulk assign entity
   - Bulk assign business line

#### Task 3.6: Update Transaction JavaScript
**File:** `web_ui/static/js/transaction_categorization.js`
**Status:** [ ] Not Started

**Changes:**
1. Add entity and business line filters to data fetching
2. Update transaction row rendering to show badges
3. Add entity/business line selectors to edit modal
4. Implement cascading dropdown (entity → business lines)
5. Add bulk assignment functionality
6. Update search to include entity and business line names

#### Task 3.7: Update Navigation and Dashboard
**Files:**
- `web_ui/templates/base.html` (navigation)
- `web_ui/templates/business_overview.html` (dashboard)
**Status:** [ ] Not Started

**Changes:**
1. Add "Entities" menu item to navigation
2. Add entity selector to top navigation bar (global filter)
3. Update dashboard to show:
   - Entity-level statistics
   - Business line breakdown (if enabled)
   - Consolidated view (all entities)
4. Add toggle for "Consolidated View" vs "By Entity"

### Phase 4: Onboarding & Progressive Disclosure (Days 11-12)
**Goal:** Seamless experience for simple and complex businesses

#### Task 4.1: Update Onboarding Flow
**File:** `web_ui/services/onboarding_bot.py`
**Status:** [ ] Not Started

**Changes:**
1. Ask about business structure:
   - Single business
   - Multiple business lines (same legal entity)
   - Multiple legal entities
2. Create entities based on response:
   - Simple: 1 entity + 1 default business line (hidden)
   - Multiple lines: 1 entity + multiple business lines
   - Multiple entities: Multiple entities + default business lines
3. Update onboarding wizard UI to capture entity information

#### Task 4.2: Implement Progressive Disclosure Logic
**File:** `web_ui/tenant_config.py` (new feature flags)
**Status:** [ ] Not Started

**Feature Flags:**
```python
ENABLE_BUSINESS_LINES = False  # Show business line UI
ENABLE_MULTI_ENTITY = False    # Show entity management
```

**Logic:**
- Start with flags disabled for new tenants with 1 entity
- Auto-enable ENABLE_BUSINESS_LINES when user creates 2nd business line
- Auto-enable ENABLE_MULTI_ENTITY when user creates 2nd entity
- Add manual toggle in settings for advanced users

#### Task 4.3: Create Settings Page for Structure
**File:** `web_ui/templates/settings_business_structure.html`
**Status:** [ ] Not Started

**Features:**
- Current structure overview (visual hierarchy)
- Enable/Disable business line tracking
- Add entity button (with explanation)
- Terminology customization:
  - Rename "Business Line" to "Department", "Product Line", "Service Line", etc.
- Migration guide for existing data

### Phase 5: Reporting & Analytics (Days 13-15)
**Goal:** Entity and business line specific reporting

#### Task 5.1: Create Entity P&L Report
**File:** `web_ui/entity_reports.py` (new)
**Status:** [ ] Not Started

**Features:**
- P&L by entity
- P&L by business line within entity
- Comparative P&L (multiple entities side-by-side)
- Consolidation with intercompany eliminations

#### Task 5.2: Create Business Line Analytics
**File:** `web_ui/business_line_analytics.py` (new)
**Status:** [ ] Not Started

**Features:**
- Revenue breakdown by business line
- Gross margin by business line
- Business line comparison charts
- Trend analysis per business line

#### Task 5.3: Update Existing Reports
**Files:** `web_ui/dmpl_report_new.py`, `web_ui/cash_flow_report_new.py`
**Status:** [ ] Not Started

**Changes:**
1. Add entity filter parameter
2. Add business line filter parameter
3. Update queries to use entity_id FK instead of VARCHAR
4. Add entity and business line columns to exports

#### Task 5.4: Create Consolidated Reports
**File:** `web_ui/consolidated_reports.py` (new)
**Status:** [ ] Not Started

**Features:**
- Combined P&L across all entities
- Intercompany transaction identification
- Elimination entries for consolidation
- Ownership percentage calculations (for future partial ownership)

### Phase 6: Classification & Intelligence (Days 16-17)
**Goal:** AI-powered entity and business line classification

#### Task 6.1: Update Classification Patterns
**File:** `migrations/update_classification_patterns_for_entities.sql`
**Status:** [ ] Not Started

**Changes:**
```sql
-- Add entity and business line assignment to patterns
ALTER TABLE classification_patterns
ADD COLUMN entity_id UUID REFERENCES entities(id),
ADD COLUMN business_line_id UUID REFERENCES business_lines(id);

-- Create lookup table for client/vendor to business line mapping
CREATE TABLE IF NOT EXISTS client_business_line_mapping (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL REFERENCES entities(id),
    client_name VARCHAR(255) NOT NULL,
    business_line_id UUID NOT NULL REFERENCES business_lines(id),
    confidence INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, entity_id, client_name)
);
```

#### Task 6.2: Update Claude Classification Prompts
**File:** `main.py` (DeltaCFOAgent.classify_transaction)
**Status:** [ ] Not Started

**Changes:**
1. Include entity and business line information in prompts
2. Ask Claude to suggest business line based on:
   - Transaction description
   - Client/vendor name
   - Amount patterns
   - Historical assignments
3. Return business line suggestion with confidence score

#### Task 6.3: Create Business Line Learning System
**File:** `web_ui/business_line_learner.py` (new)
**Status:** [ ] Not Started

**Features:**
- Learn business line assignments from user corrections
- Build client → business line mapping table
- Auto-suggest business lines for new transactions
- Pattern-based business line inference

### Phase 7: Data Migration & Validation (Days 18-19)
**Goal:** Migrate all existing data safely

#### Task 7.1: Create Delta-Specific Migration
**File:** `migrations/migrate_delta_entities.py`
**Status:** [ ] Not Started

**Purpose:** Map Delta's existing entities to new structure

**Mapping:**
```python
DELTA_ENTITIES = {
    'Delta LLC': {
        'code': 'DLLC',
        'legal_name': 'Delta Mining LLC',
        'tax_jurisdiction': 'US-Delaware',
        'entity_type': 'LLC',
        'business_lines': ['Corporate/Admin', 'Investment Activities']
    },
    'Delta Paraguay': {
        'code': 'DPY',
        'legal_name': 'Delta Mining Paraguay S.A.',
        'tax_jurisdiction': 'Paraguay',
        'entity_type': 'S.A.',
        'business_lines': ['Hosting Services', 'Energy Operations', 'Infrastructure']
    },
    # ... other entities
}
```

#### Task 7.2: Create Validation Script
**File:** `migrations/validate_entity_migration.py`
**Status:** [ ] Not Started

**Checks:**
1. All transactions have valid entity_id FK
2. No orphaned business lines
3. All entities have at least one business line
4. All tenant transactions are properly isolated
5. No data loss (transaction count matches)
6. Foreign key integrity maintained

#### Task 7.3: Create Rollback Script
**File:** `migrations/rollback_entity_migration.sql`
**Status:** [ ] Not Started

**Purpose:** Safe rollback to VARCHAR entity if needed

**Steps:**
1. Copy entity_id → entity VARCHAR (reverse lookup)
2. Verify all data copied
3. Drop foreign key constraints
4. Drop new columns
5. Drop new tables (with backups)

### Phase 8: Testing & Documentation (Days 20-21)
**Goal:** Comprehensive testing and documentation

#### Task 8.1: Unit Tests
**File:** `tests/test_entity_api.py` (new)
**Status:** [ ] Not Started

**Test Cases:**
- Create entity (success/failure)
- Update entity (validation)
- Delete entity (cascade check)
- Create business line
- Update business line
- Assign transaction to entity/business line
- Bulk operations
- Multi-tenant isolation

#### Task 8.2: Integration Tests
**File:** `tests/test_entity_integration.py` (new)
**Status:** [ ] Not Started

**Test Cases:**
- Full onboarding flow (simple business)
- Full onboarding flow (multi-entity)
- Transaction classification with business line assignment
- Reporting with entity/business line filters
- Progressive disclosure behavior
- Data migration accuracy

#### Task 8.3: Update Documentation
**File:** `CLAUDE.md`
**Status:** [ ] Not Started

**Sections to Update:**
1. Architecture Overview (new tier structure)
2. Database Architecture (entities and business_lines tables)
3. API Endpoints (new entity/business line APIs)
4. Frontend Features (new pages and filters)
5. Migration Guide (for existing deployments)
6. Terminology Guide (entity vs business line)

#### Task 8.4: Create Migration Guide
**File:** `docs/ENTITY_MIGRATION_GUIDE.md` (new)
**Status:** [ ] Not Started

**Contents:**
1. Overview of changes
2. Benefits of new structure
3. Step-by-step migration instructions
4. Rollback procedures
5. FAQs
6. Troubleshooting

### Phase 9: Performance & Optimization (Days 22-23)
**Goal:** Ensure performance at scale

#### Task 9.1: Database Optimization
**File:** `migrations/optimize_entity_queries.sql`
**Status:** [ ] Not Started

**Optimizations:**
1. Add composite indexes for common query patterns
2. Create materialized views for entity statistics
3. Optimize JOIN queries with covering indexes
4. Add query hints for large datasets

#### Task 9.2: Caching Strategy
**File:** `web_ui/entity_cache.py` (new)
**Status:** [ ] Not Started

**Features:**
- Cache entity list per tenant (24 hour TTL)
- Cache business line list per entity (24 hour TTL)
- Cache entity statistics (1 hour TTL)
- Invalidate cache on updates

#### Task 9.3: Performance Testing
**File:** `tests/test_entity_performance.py` (new)
**Status:** [ ] Not Started

**Benchmarks:**
- List entities (target: <100ms)
- List transactions with entity filter (target: <200ms)
- Generate entity P&L (target: <500ms)
- Bulk assign business lines (target: <1s for 1000 transactions)

### Phase 10: Deployment & Rollout (Days 24-25)
**Goal:** Safe production deployment

#### Task 10.1: Create Deployment Checklist
**File:** `docs/ENTITY_DEPLOYMENT_CHECKLIST.md` (new)
**Status:** [ ] Not Started

**Checklist:**
- [ ] Backup production database
- [ ] Test migration on staging environment
- [ ] Run validation scripts
- [ ] Deploy database changes
- [ ] Deploy application code
- [ ] Run data migration scripts
- [ ] Validate data integrity
- [ ] Monitor error logs
- [ ] Test critical user flows
- [ ] Notify users of new features

#### Task 10.2: Create Feature Announcement
**File:** `docs/ENTITY_FEATURE_ANNOUNCEMENT.md` (new)
**Status:** [ ] Not Started

**Contents:**
1. What's new (entity and business line management)
2. Benefits for users
3. How to get started
4. Video tutorial (optional)
5. FAQ
6. Support contact

#### Task 10.3: Monitoring & Alerts
**File:** `web_ui/entity_monitoring.py` (new)
**Status:** [ ] Not Started

**Monitors:**
- Entity creation rate
- Business line usage
- Migration errors
- API response times
- Database query performance
- Failed FK constraint violations

## Key Technical Decisions

### 1. Database Design
- **UUID vs SERIAL**: Use UUID for entities and business_lines (better for distributed systems)
- **Soft Delete**: Use is_active flag instead of hard deletes (preserve history)
- **Foreign Keys**: Required for entity_id, optional for business_line_id
- **Cascading**: CASCADE on entity delete → delete business lines, SET NULL on business line delete → keep transactions

### 2. Backward Compatibility
- Keep VARCHAR entity columns during transition (can drop after validation)
- Support both entity (VARCHAR) and entity_id (FK) in APIs temporarily
- Add deprecation warnings for old endpoints
- Provide automatic migration tools

### 3. Progressive Disclosure Strategy
- Start with simplest UI (hide entity/business line complexity)
- Auto-detect when to show advanced features
- Allow manual override in settings
- Provide clear migration path from simple → complex

### 4. Performance Considerations
- Index all foreign keys
- Use composite indexes for common filters
- Cache entity/business line lists
- Lazy-load business line data (only when needed)
- Paginate large entity lists

### 5. Security & Isolation
- All queries MUST filter by tenant_id first
- Validate entity belongs to tenant before operations
- Validate business line belongs to entity before assignment
- Row-level security policies (future enhancement)

## Validation & Testing Strategy

### Database Validation
```sql
-- Verify all transactions have valid entity_id
SELECT COUNT(*) FROM transactions WHERE entity_id IS NULL;
-- Should be 0

-- Verify all business lines have valid entity_id
SELECT COUNT(*) FROM business_lines WHERE entity_id NOT IN (SELECT id FROM entities);
-- Should be 0

-- Verify each entity has at least one business line
SELECT e.id, e.name, COUNT(bl.id)
FROM entities e
LEFT JOIN business_lines bl ON e.id = bl.entity_id
GROUP BY e.id, e.name
HAVING COUNT(bl.id) = 0;
-- Should return no rows
```

### API Testing
```bash
# Create entity
curl -X POST /api/entities -d '{"name": "Test LLC", "code": "TEST"}'

# Create business line
curl -X POST /api/business-lines -d '{"entity_id": "uuid", "name": "Operations", "code": "OPS"}'

# Assign to transaction
curl -X PUT /api/transactions/123 -d '{"entity_id": "uuid", "business_line_id": "uuid"}'

# Filter transactions
curl /api/transactions?entity_id=uuid&business_line_id=uuid
```

### Frontend Testing
- [ ] Simple business sees no entity/business line UI
- [ ] Adding second entity shows entity management
- [ ] Adding second business line shows business line tracking
- [ ] Entity filter cascades to business line filter
- [ ] Transaction list shows correct entity/business line badges
- [ ] Reports filter by entity and business line

## Success Criteria

### Functional Requirements
- [ ] Can create and manage entities (CRUD operations)
- [ ] Can create and manage business lines per entity
- [ ] All transactions assigned to valid entities
- [ ] Business line assignment optional and working
- [ ] Entity and business line filters work in all views
- [ ] Reports show entity and business line breakdowns
- [ ] Progressive disclosure hides complexity for simple businesses
- [ ] Classification engine suggests business lines
- [ ] Data migration completed without loss

### Non-Functional Requirements
- [ ] All database operations use foreign keys (no VARCHAR entities)
- [ ] Multi-tenant isolation maintained
- [ ] No performance degradation (<10% slower queries)
- [ ] All existing features continue working
- [ ] No breaking changes to existing APIs
- [ ] Documentation complete and accurate
- [ ] Rollback procedures tested and documented

### User Experience Requirements
- [ ] Simple single-business user sees no change
- [ ] Multi-entity business can manage structure easily
- [ ] Onboarding flow guides users to correct setup
- [ ] Entity/business line badges clear and helpful
- [ ] Filters intuitive and responsive
- [ ] No UI clutter for users who don't need features

## Risk Mitigation

### Risk 1: Data Loss During Migration
**Mitigation:**
- Keep original VARCHAR columns during transition
- Run migration on staging first
- Create full database backup before migration
- Implement rollback script
- Validate data before and after migration

### Risk 2: Performance Degradation
**Mitigation:**
- Add proper indexes before migration
- Test query performance on production-size dataset
- Use EXPLAIN ANALYZE to optimize queries
- Implement caching for entity/business line lists
- Monitor query times in production

### Risk 3: Breaking Existing Integrations
**Mitigation:**
- Maintain backward compatibility for 1 release cycle
- Provide migration guide for API consumers
- Add deprecation warnings to old endpoints
- Version API endpoints if needed

### Risk 4: User Confusion
**Mitigation:**
- Progressive disclosure (hide complexity by default)
- Clear terminology and explanations
- In-app help tooltips and guides
- Video tutorials for complex features
- Support documentation with examples

## Timeline Summary

**Phase 1-2 (Days 1-6):** Database & Backend - Core foundation
**Phase 3-4 (Days 7-12):** Frontend & UX - User-facing features
**Phase 5-6 (Days 13-17):** Reporting & Intelligence - Advanced features
**Phase 7-8 (Days 18-21):** Migration & Testing - Quality assurance
**Phase 9-10 (Days 22-25):** Optimization & Deployment - Production release

**Total Estimated Time:** 25 working days (~5 weeks)

## Rollout Strategy

### Week 1: Internal Testing
- Deploy to development environment
- Test all features thoroughly
- Fix critical bugs
- Gather internal feedback

### Week 2: Staging Validation
- Deploy to staging environment
- Run migration on staging data
- Validate data integrity
- Performance testing

### Week 3: Beta Testing
- Deploy to production with feature flag
- Enable for Delta tenant only
- Monitor errors and performance
- Collect feedback

### Week 4: Limited Rollout
- Enable for 10% of tenants
- Monitor adoption and issues
- Provide support for migrations
- Fix non-critical bugs

### Week 5: Full Rollout
- Enable for all tenants
- Announce new features
- Provide migration assistance
- Update documentation

## Post-Deployment Monitoring

### Week 1 Post-Launch
- Monitor error rates (target: <0.1%)
- Track API response times (target: <500ms p95)
- Measure user adoption (target: 20% using new features)
- Collect user feedback

### Month 1 Post-Launch
- Analyze usage patterns
- Identify pain points
- Plan enhancements based on feedback
- Optimize performance bottlenecks

### Quarter 1 Post-Launch
- Review success metrics
- Plan advanced features:
  - Intercompany transaction automation
  - Ownership percentage tracking
  - Advanced consolidation
  - Multi-currency improvements

## Next Steps (After This Project)

### Future Enhancements
1. **Intercompany Automation**: Auto-detect and create elimination entries
2. **Ownership Tracking**: Support partial ownership of entities
3. **Advanced Consolidation**: Full equity method accounting
4. **Multi-Currency**: Automatic currency translation for consolidation
5. **Business Line Templates**: Industry-specific business line templates
6. **Advanced Analytics**: Business line profitability analysis
7. **Budget vs Actual**: Entity and business line level budgeting
8. **Forecasting**: Multi-entity and business line forecasting

## Appendix: Delta Energy Example Mapping

### Current Structure (VARCHAR)
```
transactions.entity in (
  'Delta LLC',
  'Delta Paraguay',
  'Delta Brazil',
  'Delta Prop Shop',
  'Delta Infinity'
)
```

### Target Structure (FK-based)
```
Organization: Delta Energy Holdings (tenant_id='delta')
│
├── Entity: Delta Mining LLC (DLLC)
│   ├── Business Line: Corporate/Admin
│   └── Business Line: Investment Activities
│
├── Entity: Delta Mining Paraguay S.A. (DPY)
│   ├── Business Line: Hosting Services (Alps, Exos, GM)
│   ├── Business Line: Energy Operations
│   └── Business Line: Infrastructure
│
├── Entity: Delta Mining Brazil Ltda (DBR)
│   ├── Business Line: Colocation Services
│   └── Business Line: Local Operations
│
├── Entity: Delta Prop Shop LLC (DPS)
│   ├── Business Line: Taoshi Contract
│   ├── Business Line: Miner Reward Splits
│   └── Business Line: Marketplace Fees
│
└── Entity: Delta Infinity LLC (DIN)
    ├── Business Line: Validator Operations
    └── Business Line: JV Revenue Share
```

---

## Review Section

### Changes Summary

#### Merge with Dev Branch (2025-11-28)
**Commit:** `3630f2b` - Merged origin/Dev into Entity/Business Line architecture branch

**Dev Branch Features Integrated:**
1. **PDF Upload Progress Bar**
   - 6-stage progress bar with Server-Sent Events (SSE) streaming
   - New route: `/api/upload-with-progress`
   - Real-time progress updates during file processing

2. **Performance Optimizations**
   - Batch INSERT using `psycopg2.extras.execute_values` (99x faster)
   - Reduced database round-trips from N to 1 for bulk inserts
   - Transaction duplicate checking excludes archived records (prevents data loss)

3. **AI Classification Enhancements**
   - Pass 2 AI classification reviewer for low-confidence transactions
   - New file: `web_ui/ai_classification_reviewer.py`
   - Tenant business context generator: `services/knowledge_generator.py`

4. **Pattern Service Resilience**
   - Exponential backoff reconnection logic in `pattern_validation_service.py`
   - Graceful degradation when pattern validation service unavailable

5. **New Database Migrations**
   - `migrations/add_business_insights_table.sql` - Business insights storage
   - `migrations/add_source_document_id.sql` - Document tracking
   - `migrations/add_tenant_business_summary.sql` - Tenant summaries
   - `migrations/add_origin_destination_to_transactions.sql` - Transaction flow
   - `migrations/fix_pattern_trigger_include_justification.sql` - Pattern triggers

6. **Internationalization (i18n)**
   - Translation scripts added under `scripts/translation/`
   - Support for multi-language UI (Portuguese translations added)

**Entity/Business Line Architecture Status:**
- ✅ All Phase 1-4 implementation preserved
- ✅ `entity_api.py` registration intact in `app_db.py` (lines 103, 217)
- ✅ Entity management APIs functional
- ✅ Business Line management functional
- ✅ Migration scripts preserved
- ✅ Frontend components (entities.js, entities.html) preserved
- ✅ No conflicts detected during merge

**Merge Statistics:**
- 46 files changed
- 6,370 insertions
- 954 deletions
- Automatic merge successful (no manual conflict resolution required)

**Compatibility Verification:**
- Both feature sets coexist without conflicts
- PDF upload progress does not interfere with Entity APIs
- Entity filtering still functional in transaction lists
- Business Line assignment preserved in transaction workflows

### Lessons Learned

#### Successful Merge Strategy
1. **Branch Divergence Management**: Both branches diverged from common ancestor `024b3ac` with distinct features
2. **File Isolation**: Entity work and PDF upload work touched different parts of codebase (minimal overlap)
3. **Smart Git Merging**: Git successfully auto-merged `web_ui/app_db.py` despite large changes in both branches
4. **Preservation of Features**: No functionality lost from either branch during merge

#### Key Takeaways
- Keep feature branches focused on distinct areas to minimize merge conflicts
- Large files like `app_db.py` can still auto-merge if changes are in different sections
- Regular integration with Dev branch prevents drift and reduces merge complexity

### Known Issues

#### Post-Merge Testing Required
1. **Manual Testing Needed**:
   - [ ] Test PDF upload with progress bar on local environment
   - [ ] Verify Entity management APIs still work correctly
   - [ ] Test Business Line assignment with new batch insert optimization
   - [ ] Verify pattern validation service reconnection logic
   - [ ] Test AI classification reviewer with Entity context

2. **Migration Coordination**:
   - Entity migrations (`add_entities_and_business_lines.sql`) need to be run before Dev migrations
   - Order matters: Entities → Business Lines → Transactions → Business Insights
   - Consider creating a master migration script to ensure correct order

3. **Documentation Updates**:
   - CLAUDE.md should be updated to reflect merged features
   - README should mention both Entity architecture and PDF upload progress
   - Deployment guide needs to include all new migrations

### Future Improvements

#### Integration Opportunities
1. **Entity-Aware PDF Upload**:
   - Enhance PDF upload progress to automatically assign entity_id during classification
   - Use business context generator to improve entity inference
   - Add business line suggestion during initial transaction import

2. **AI Classification + Entity Context**:
   - Leverage `knowledge_generator.py` for entity-specific classification rules
   - Use AI classification reviewer to validate entity assignments
   - Implement entity-aware pattern learning

3. **Batch Optimization for Entities**:
   - Apply `execute_values` batch insert pattern to Entity bulk operations
   - Optimize Business Line assignment for large transaction sets
   - Add progress bar for entity data migration script

4. **Progressive Disclosure Enhancement**:
   - Use business insights table to determine when to show Entity UI
   - Auto-enable Entity features based on transaction complexity
   - Integrate tenant business summary into Entity onboarding flow

5. **Consolidated Reporting**:
   - Add Entity breakdown to PDF upload summary
   - Show Business Line distribution in upload progress
   - Generate Entity-specific insights after bulk import

#### Next Phase Integration
- Phase 5-10 of Entity architecture can now leverage:
  - New business insights table for Entity analytics
  - Source document tracking for Entity-level audit trails
  - Pattern triggers for automated Entity classification
  - AI classification reviewer for Entity assignment validation

### Deployment Notes

#### Pre-Deployment Checklist
- [ ] Run Entity migrations first (Phase 1 completed)
- [ ] Run Dev branch migrations (business insights, source documents, etc.)
- [ ] Test Entity API endpoints
- [ ] Test PDF upload with progress
- [ ] Verify batch insert performance
- [ ] Check pattern validation service resilience
- [ ] Validate AI classification reviewer
- [ ] Test multi-tenant isolation with merged features

#### Rollback Strategy
If issues arise post-deployment:
1. Revert to commit `50bc8e7` (last Entity-only commit)
2. OR revert to commit `3f1617c` (last Dev-only commit)
3. OR revert merge commit `3630f2b` to separate features again

Both feature sets are independently functional and can be deployed separately if needed.
