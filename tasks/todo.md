# Workforce Feature - Implementation Plan

## Overview
Build a complete Workforce management system for employees and contractors, including payslip generation and automatic transaction matching.

## Requirements
1. **Employee/Contractor Management**: Create and manage workforce members with name, document number, date of hire, and pay rate
2. **Payslip Generation**: Create payslips that can be sent to employees as proof of payment
3. **Payment Marking**: Mark payslips as paid by employer
4. **Transaction Matching**: Match payslip payments with transactions in the Transaction categorization page (reuse existing invoice-transaction matching logic)

## System Architecture Analysis

### Existing Invoice-Transaction Matching System (to be reused)
- **Database Tables**:
  - `invoices`: Stores invoice data
  - `pending_invoice_matches`: Stores potential matches between invoices and transactions
  - `invoice_match_log`: Logs all matching actions (confirmed/rejected)

- **Matching Engine**: `RevenueInvoiceMatcher` in `web_ui/revenue_matcher.py`
  - Amount matching with 3% tolerance
  - Date proximity matching
  - Description/vendor fuzzy matching
  - AI-powered semantic matching with Claude
  - Confidence scoring (high/medium/low)

- **Frontend Pattern**:
  - Main list page showing all items
  - Detail modal/page with tabs (details, matches, etc.)
  - Matches tab shows potential transaction matches with scores
  - Actions: Confirm match, Reject match, Manual link

- **API Endpoints Pattern**:
  - GET `/api/invoices` - List all
  - POST `/api/invoices` - Create new
  - GET `/api/invoices/<id>` - Get details
  - GET `/api/invoices/<id>/find-matching-transactions` - Find matches
  - POST `/api/invoices/<id>/link-transaction` - Manual link
  - POST `/api/revenue/confirm-match` - Confirm auto-match
  - POST `/api/revenue/reject-match` - Reject match

## Database Schema Design

### 1. workforce_members table
```sql
CREATE TABLE IF NOT EXISTS workforce_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,

    -- Basic Information
    full_name VARCHAR(255) NOT NULL,
    employment_type VARCHAR(50) NOT NULL, -- 'employee', 'contractor'
    document_type VARCHAR(50), -- 'ssn', 'ein', 'tax_id', 'passport'
    document_number VARCHAR(100),

    -- Employment Details
    date_of_hire DATE NOT NULL,
    termination_date DATE,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'terminated'

    -- Compensation
    pay_rate DECIMAL(15,2) NOT NULL,
    pay_frequency VARCHAR(50) NOT NULL, -- 'hourly', 'daily', 'weekly', 'biweekly', 'monthly', 'annual'
    currency VARCHAR(3) DEFAULT 'USD',

    -- Contact Information
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,

    -- Additional Details
    job_title VARCHAR(255),
    department VARCHAR(255),
    notes TEXT,

    -- Metadata
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(tenant_id, document_number)
);
```

### 2. payslips table
```sql
CREATE TABLE IF NOT EXISTS payslips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    workforce_member_id UUID NOT NULL REFERENCES workforce_members(id) ON DELETE RESTRICT,

    -- Payslip Identification
    payslip_number VARCHAR(50) UNIQUE NOT NULL,

    -- Period Information
    pay_period_start DATE NOT NULL,
    pay_period_end DATE NOT NULL,
    payment_date DATE NOT NULL,

    -- Payment Details
    gross_amount DECIMAL(15,2) NOT NULL,
    deductions DECIMAL(15,2) DEFAULT 0,
    net_amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',

    -- Line Items (detailed breakdown)
    line_items JSONB, -- {type: 'salary'|'bonus'|'overtime', description, amount, hours}
    deductions_items JSONB, -- {type: 'tax'|'insurance'|'401k', description, amount}

    -- Payment Status
    status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'approved', 'paid', 'cancelled'
    payment_method VARCHAR(50), -- 'bank_transfer', 'check', 'cash', 'crypto'

    -- Transaction Matching
    transaction_id INTEGER, -- Links to transactions table when matched
    match_confidence INTEGER, -- 0-100 matching confidence score
    match_method VARCHAR(50), -- 'automatic', 'manual', 'ai_suggested'

    -- Document Management
    pdf_path TEXT,
    sent_to_employee_at TIMESTAMP,
    employee_viewed_at TIMESTAMP,

    -- Notes
    notes TEXT,
    internal_notes TEXT, -- Not visible to employee

    -- Metadata
    created_by VARCHAR(100),
    approved_by VARCHAR(100),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3. pending_payslip_matches table (similar to pending_invoice_matches)
```sql
CREATE TABLE IF NOT EXISTS pending_payslip_matches (
    id SERIAL PRIMARY KEY,
    payslip_id UUID NOT NULL,
    transaction_id TEXT NOT NULL,
    score DECIMAL(3,2) NOT NULL,
    match_type TEXT NOT NULL,
    criteria_scores JSONB,
    confidence_level TEXT NOT NULL,
    explanation TEXT,
    status TEXT DEFAULT 'pending',
    reviewed_by TEXT,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(payslip_id, transaction_id)
);
```

### 4. payslip_match_log table
```sql
CREATE TABLE IF NOT EXISTS payslip_match_log (
    id SERIAL PRIMARY KEY,
    payslip_id UUID NOT NULL,
    transaction_id TEXT NOT NULL,
    action TEXT NOT NULL, -- 'confirmed', 'rejected', 'manual_link', 'unmatched'
    score DECIMAL(3,2),
    match_type TEXT,
    user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Implementation Tasks

### Phase 1: Database & Backend Core (4 files)
- [ ] Create migration script: `migrations/add_workforce_tables.sql`
- [ ] Create Payslip Matcher class: `web_ui/payslip_matcher.py` (based on revenue_matcher.py)
- [ ] Add workforce API endpoints to `web_ui/app_db.py`
- [ ] Write unit tests: `tests/test_workforce_api.py`

### Phase 2: Frontend Pages (3 files)
- [ ] Create workforce list page: `web_ui/templates/workforce.html`
- [ ] Create workforce JavaScript: `web_ui/static/js/workforce.js`
- [ ] Create payslip matching JavaScript: `web_ui/static/js/payslip_matches.js`

### Phase 3: Integration & Polish (3 files)
- [ ] Update navigation menu to include Workforce link
- [ ] Update transaction enrichment to recognize payslip matches
- [ ] Add workforce stats to homepage/dashboard

### Phase 4: Testing & Documentation (2 files)
- [ ] Integration testing with sample data
- [ ] Update CLAUDE.md with Workforce documentation

## API Endpoints to Implement

### Workforce Members
- GET `/api/workforce` - List all workforce members (with filters)
- POST `/api/workforce` - Create new workforce member
- GET `/api/workforce/<id>` - Get workforce member details
- PUT `/api/workforce/<id>` - Update workforce member
- DELETE `/api/workforce/<id>` - Soft delete (set status=inactive)

### Payslips
- GET `/api/payslips` - List all payslips (with filters)
- POST `/api/payslips` - Create new payslip
- GET `/api/payslips/<id>` - Get payslip details
- PUT `/api/payslips/<id>` - Update payslip
- DELETE `/api/payslips/<id>` - Delete payslip (if not paid)
- POST `/api/payslips/<id>/mark-paid` - Mark as paid
- POST `/api/payslips/<id>/send-to-employee` - Send via email
- GET `/api/payslips/<id>/pdf` - Generate/download PDF

### Payslip-Transaction Matching
- GET `/api/payslips/<id>/find-matching-transactions` - Find potential matches
- POST `/api/payslips/<id>/link-transaction` - Manual link
- POST `/api/payroll/run-matching` - Run matching for all unmatched payslips
- GET `/api/payroll/matched-pairs` - Get confirmed matches
- POST `/api/payroll/confirm-match` - Confirm a suggested match
- POST `/api/payroll/reject-match` - Reject a suggested match
- POST `/api/payroll/unmatch` - Remove existing match
- GET `/api/payroll/stats` - Get matching statistics

## Frontend Features

### Workforce Members Page
- **List View**: Table with name, type, hire date, pay rate, status
- **Filters**: employment type, status, department
- **Actions**: Add new, Edit, View payslips, Deactivate
- **Bulk Actions**: Export to CSV, Bulk update status

### Workforce Member Detail Modal
- **Tabs**:
  1. **Details**: Personal info, employment details, compensation
  2. **Payslips**: List of all payslips for this member
  3. **Activity**: History of changes and actions

### Payslips Page/Section
- **List View**: Table with employee name, period, amount, status, payment date
- **Filters**: employee, status, date range, payment method
- **Actions**: Create new, Edit, View matches, Mark paid, Send to employee, Download PDF

### Payslip Detail Modal
- **Tabs**:
  1. **Details**: Employee info, period, amounts breakdown, deductions
  2. **Matches**: Potential transaction matches (reuses invoice matching UI pattern)
  3. **History**: Payment status changes, emails sent

### Matching Interface (similar to invoice matching)
- Show list of potential transaction matches with scores
- Display match confidence (Excellent/Good/Fair)
- Show date difference and amount difference
- Actions: Confirm Match, Reject, Manual Link to Different Transaction
- Visual indicators for already matched transactions

## Code Reuse Strategy

### 1. Payslip Matcher (80% code reuse from RevenueInvoiceMatcher)
```python
# web_ui/payslip_matcher.py
class PayslipMatcher(RevenueInvoiceMatcher):
    """
    Extends RevenueInvoiceMatcher for payslip-transaction matching
    Changes needed:
    - Query payslips instead of invoices
    - Match against employee names in transaction descriptions
    - Look for payroll-related keywords
    - Filter transactions by negative amounts (outgoing payments)
    """
```

### 2. Frontend Matching UI (90% code reuse from invoice_matches.js)
- Copy invoice_matches.js → payslip_matches.js
- Update API endpoints from `/api/invoices/` to `/api/payslips/`
- Update terminology from "invoice" to "payslip"

### 3. API Endpoints Pattern (same structure as invoices)
- Copy invoice endpoints structure
- Update table names and field mappings
- Reuse same transaction enrichment logic

## Simplified Approach (KISS Principle)

### Key Simplifications:
1. **No Complex Payroll Calculations**: Just gross/net/deductions fields, no tax engine
2. **Reuse Matching Logic**: Copy & adapt invoice matcher, don't rebuild from scratch
3. **Simple PDF Generation**: Text-based PDF (can enhance later with templates)
4. **Email Integration**: Reuse existing email service if available, else skip for MVP
5. **No Automated Payslip Creation**: Manual creation only for MVP (can add recurring later)

### Out of Scope for MVP:
- Automated tax calculations
- Benefits management
- Time tracking integration
- Automated recurring payslip generation
- Employee self-service portal
- Complex approval workflows
- Multi-currency automatic conversion
- Payroll reporting/analytics (beyond basic stats)

## Testing Strategy

### Manual Testing Checklist:
1. Create employee with all fields
2. Create contractor with minimal fields
3. Create payslip for employee
4. Mark payslip as paid
5. Upload transaction that matches payslip
6. Verify auto-matching finds the transaction
7. Confirm the match
8. Verify transaction gets enriched with employee name
9. Test unmatching
10. Test manual linking to different transaction

### Unit Tests (if time permits):
- Test payslip creation
- Test amount matching algorithm
- Test date proximity scoring
- Test AI matching (mock Claude API)

## Success Criteria

- [ ] Can create employees and contractors
- [ ] Can create payslips with line items
- [ ] Can mark payslips as paid
- [ ] Payslip-transaction matching works (finds correct matches)
- [ ] Can confirm/reject matches from UI
- [ ] Matched transactions show employee name in classification
- [ ] All matching functionality reuses existing invoice code
- [ ] Code changes are minimal and focused
- [ ] No bugs introduced in existing features

## Review Checklist

- [ ] All database migrations run successfully
- [ ] All API endpoints tested manually
- [ ] Frontend loads without console errors
- [ ] Matching algorithm finds correct transactions
- [ ] Transaction enrichment works correctly
- [ ] Code follows project style and conventions
- [ ] No hardcoded values (use environment variables)
- [ ] PostgreSQL-only (no SQLite code)
- [ ] Multi-tenant ready (tenant_id in all queries)
- [ ] Documentation updated in CLAUDE.md
