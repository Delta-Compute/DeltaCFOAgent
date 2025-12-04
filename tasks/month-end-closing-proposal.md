# Month-End Closing Feature - Research & Proposal

## Executive Summary

This document proposes a Month-End Closing feature for DeltaCFOAgent, based on research of industry-standard practices from leading financial close software (FloQast, BlackLine, NetSuite, Numeric) and an analysis of the existing codebase architecture.

The feature will enable CFOs and controllers to systematically close accounting periods with proper workflow management, reconciliation tracking, approval chains, and audit trails.

---

## Research Findings

### Industry Standards for Month-End Close

Based on research from [Vena Solutions](https://www.venasolutions.com/blog/month-end-close-process-checklist), [HighRadius](https://www.highradius.com/resources/Blog/what-is-month-end-close-process/), [Numeric](https://www.numeric.io/blog/financial-close-software), and [NetGain](https://www.netgain.tech/blog/gl-transaction-locking), the month-end close process typically involves:

#### Core Close Steps
1. **Data Collection** - Gather all financial documents and transaction records
2. **Bank Reconciliation** - Match bank statements to internal records
3. **Revenue Reconciliation** - Match invoices to payments received
4. **Expense Reconciliation** - Match payroll, vendor invoices to payments made
5. **Accrual Entries** - Record expenses/revenues not yet paid/received
6. **Adjusting Entries** - Depreciation, prepaid expenses, deferrals
7. **Account Reconciliation** - Verify all balance sheet accounts
8. **Financial Statement Review** - Generate and review P&L, Balance Sheet, Cash Flow
9. **Approval & Lock** - Controller/CFO approval and period lock

#### Key Features in Leading Software

| Feature | FloQast | BlackLine | NetSuite |
|---------|---------|-----------|----------|
| Task Checklists | Yes | Yes | Yes (Period Close Checklist) |
| Reconciliation Management | Yes | Yes (98% automation) | Yes |
| Transaction Locking | No | Yes | Yes (A/P, A/R, Payroll, All) |
| AI-Assisted Matching | Yes | Yes | Limited |
| Approval Workflows | Yes | Yes | Yes |
| Audit Trail | Yes | Yes | Yes |
| Real-time Dashboard | Yes | Yes | Yes |

#### Industry Statistics
- 94% of teams still use Excel for month-end close processes
- By 2027, 50% of midsize companies will adopt close management software
- Average close time reduced from 7+ days (2014) to 4 days (2019) with automation

---

## Current DeltaCFOAgent Capabilities

### Already Available (Leverage Points)

| Capability | Location | Status |
|------------|----------|--------|
| Financial Statements (P&L, Balance Sheet, Cash Flow) | `reporting_api.py` | Ready |
| Revenue/Invoice Matching | `revenue_matcher.py` | Ready |
| Payslip/Payroll Matching | `payslip_matcher.py` | Ready |
| Transaction Classification | `main.py` (DeltaCFOAgent) | Ready |
| Period-Based Reporting | 32 API endpoints | Ready |
| Fiscal Year Configuration | `tenant_configuration` table | Ready |
| Multi-Tenant Support | All components | Ready |
| AI Integration (Claude) | Multiple modules | Ready |
| Audit Logging | `user_interactions`, match logs | Partial |

### Missing (Needs Implementation)

| Capability | Priority | Effort |
|------------|----------|--------|
| Accounting Periods Table | High | Low |
| Period Lock Mechanism | High | Medium |
| Close Workflow/Checklist | High | Medium |
| Reconciliation Dashboard | High | Medium |
| Adjustment Entry Management | Medium | Medium |
| Accrual Automation | Medium | High |
| Approval Chain System | Medium | Medium |
| Close Status Tracking | High | Low |

---

## Proposed Architecture

### Database Schema

#### New Tables

```sql
-- Accounting periods with status tracking
CREATE TABLE cfo_accounting_periods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenant_configuration(tenant_id),
    period_name VARCHAR(50) NOT NULL,  -- "2024-01", "2024-02", etc.
    period_type VARCHAR(20) DEFAULT 'monthly',  -- monthly, quarterly, yearly
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'open',  -- open, in_progress, pending_approval, locked, closed
    locked_at TIMESTAMP,
    locked_by UUID REFERENCES users(id),
    closed_at TIMESTAMP,
    closed_by UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, period_name)
);

-- Closing checklist items (template + instance)
CREATE TABLE close_checklist_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenant_configuration(tenant_id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,  -- bank_reconciliation, revenue, expenses, payroll, adjustments, review
    sequence_order INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT true,
    auto_check_type VARCHAR(50),  -- null for manual, or: bank_reconciled, invoices_matched, payslips_matched, etc.
    auto_check_threshold DECIMAL(5,2),  -- e.g., 95.00 for 95% matched
    assigned_role VARCHAR(50),  -- accountant, controller, cfo
    estimated_minutes INTEGER,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Period-specific checklist instances
CREATE TABLE close_checklist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_id UUID NOT NULL REFERENCES cfo_accounting_periods(id) ON DELETE CASCADE,
    template_id UUID REFERENCES close_checklist_templates(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    sequence_order INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, in_progress, completed, skipped, blocked
    is_required BOOLEAN DEFAULT true,
    auto_check_result JSONB,  -- stores auto-check details: {matched: 45, total: 50, percentage: 90}
    completed_at TIMESTAMP,
    completed_by UUID REFERENCES users(id),
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP,
    notes TEXT,
    blockers TEXT,  -- reason if blocked
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Adjusting journal entries for period
CREATE TABLE close_adjusting_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_id UUID NOT NULL REFERENCES cfo_accounting_periods(id) ON DELETE CASCADE,
    tenant_id VARCHAR(50) NOT NULL REFERENCES tenant_configuration(tenant_id),
    entry_type VARCHAR(50) NOT NULL,  -- accrual, depreciation, prepaid, deferral, correction, other
    description TEXT NOT NULL,
    debit_account VARCHAR(100) NOT NULL,
    credit_account VARCHAR(100) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    entity VARCHAR(100),
    status VARCHAR(20) DEFAULT 'draft',  -- draft, pending_approval, approved, posted, rejected
    created_by UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP,
    posted_at TIMESTAMP,
    reversal_period_id UUID REFERENCES cfo_accounting_periods(id),  -- for auto-reversal entries
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Close activity log (audit trail)
CREATE TABLE close_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_id UUID NOT NULL REFERENCES cfo_accounting_periods(id) ON DELETE CASCADE,
    tenant_id VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,  -- checklist_completed, entry_created, period_locked, etc.
    entity_type VARCHAR(50),  -- checklist_item, adjusting_entry, period, etc.
    entity_id UUID,
    user_id UUID REFERENCES users(id),
    details JSONB,  -- action-specific details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lock status per subsystem (granular locking)
CREATE TABLE period_locks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_id UUID NOT NULL REFERENCES cfo_accounting_periods(id) ON DELETE CASCADE,
    lock_type VARCHAR(50) NOT NULL,  -- transactions, invoices, payroll, adjustments, all
    is_locked BOOLEAN DEFAULT false,
    locked_at TIMESTAMP,
    locked_by UUID REFERENCES users(id),
    unlock_reason TEXT,  -- if temporarily unlocked
    UNIQUE(period_id, lock_type)
);
```

### API Endpoints

```
# Period Management
GET    /api/close/periods                    # List all periods
POST   /api/close/periods                    # Create new period
GET    /api/close/periods/<id>               # Get period details
PUT    /api/close/periods/<id>               # Update period
POST   /api/close/periods/<id>/start         # Start close process
POST   /api/close/periods/<id>/lock          # Lock period
POST   /api/close/periods/<id>/unlock        # Unlock (with reason)
POST   /api/close/periods/<id>/submit        # Submit for approval
POST   /api/close/periods/<id>/approve       # CFO approval
POST   /api/close/periods/<id>/reject        # Reject with comments
POST   /api/close/periods/<id>/close         # Final close

# Checklist Management
GET    /api/close/periods/<id>/checklist     # Get period checklist
PUT    /api/close/checklist/<item_id>        # Update checklist item
POST   /api/close/checklist/<item_id>/complete  # Mark complete
POST   /api/close/checklist/<item_id>/skip   # Skip with reason
POST   /api/close/periods/<id>/run-auto-checks  # Run all auto-checks

# Reconciliation Status
GET    /api/close/periods/<id>/reconciliation-status  # Get all reconciliation metrics
GET    /api/close/periods/<id>/bank-reconciliation    # Bank recon details
GET    /api/close/periods/<id>/revenue-reconciliation # Invoice matching status
GET    /api/close/periods/<id>/payroll-reconciliation # Payslip matching status
GET    /api/close/periods/<id>/unmatched-items        # All unmatched items

# Adjusting Entries
GET    /api/close/periods/<id>/entries       # List entries
POST   /api/close/periods/<id>/entries       # Create entry
PUT    /api/close/entries/<id>               # Update entry
POST   /api/close/entries/<id>/approve       # Approve entry
POST   /api/close/entries/<id>/post          # Post to ledger
DELETE /api/close/entries/<id>               # Delete draft entry

# Templates
GET    /api/close/templates                  # List templates
POST   /api/close/templates                  # Create template
PUT    /api/close/templates/<id>             # Update template

# Reports
GET    /api/close/periods/<id>/pre-close-report   # Pre-close review
GET    /api/close/periods/<id>/close-summary      # Close summary
GET    /api/close/periods/<id>/trial-balance      # Trial balance
GET    /api/close/periods/<id>/activity-log       # Audit trail
```

### Frontend Components

#### New Pages

1. **Period Close Dashboard** (`/close` or `/month-end-close`)
   - Period selector
   - Status overview (progress bar)
   - Checklist with completion status
   - Quick metrics (unmatched count, pending entries)
   - Action buttons (Lock, Submit, Approve)

2. **Reconciliation Dashboard** (`/close/<period_id>/reconciliation`)
   - Bank reconciliation status
   - Revenue (invoice) matching status
   - Payroll matching status
   - Unmatched items list with actions

3. **Adjusting Entries Page** (`/close/<period_id>/entries`)
   - Entry list with status filters
   - Create/edit entry form
   - Approval workflow buttons

4. **Close Review Page** (`/close/<period_id>/review`)
   - Pre-close checklist verification
   - Financial statement preview
   - Variance analysis
   - Approval/rejection with comments

### Workflow States

```
PERIOD STATES:
  open -> in_progress -> pending_approval -> locked -> closed
                    \-> rejected (back to in_progress)

CHECKLIST ITEM STATES:
  pending -> in_progress -> completed
         \-> skipped (with reason)
         \-> blocked (with blocker)

ADJUSTING ENTRY STATES:
  draft -> pending_approval -> approved -> posted
       \-> rejected (back to draft)
```

### Auto-Check Logic

The system can automatically verify certain checklist items:

```python
AUTO_CHECKS = {
    'bank_reconciled': {
        'description': 'All bank transactions reconciled',
        'query': 'Check transactions with bank_reconciled=false for period',
        'threshold': 100  # 100% required
    },
    'invoices_matched': {
        'description': 'Revenue invoices matched to payments',
        'query': 'Check pending_invoice_matches status',
        'threshold': 95  # 95% matched acceptable
    },
    'payslips_matched': {
        'description': 'Payroll matched to bank transactions',
        'query': 'Check pending_payslip_matches status',
        'threshold': 95
    },
    'low_confidence_reviewed': {
        'description': 'Low confidence transactions reviewed',
        'query': 'Check transactions with confidence < 0.7 have user_reviewed=true',
        'threshold': 100
    },
    'unclassified_resolved': {
        'description': 'No unclassified transactions',
        'query': 'Check transactions with category IS NULL',
        'threshold': 100
    }
}
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (MVP)
**Goal:** Enable basic period management and checklist workflow

#### Tasks:
1. Create database migration for all new tables
2. Implement `cfo_accounting_periods` CRUD operations
3. Create default checklist templates
4. Build basic close dashboard UI
5. Implement checklist item management
6. Add period lock/unlock functionality
7. Implement transaction date validation against locked periods

**Deliverables:**
- Periods can be created, started, and locked
- Checklist items can be manually completed
- Transactions cannot be added/modified in locked periods
- Basic dashboard shows close progress

### Phase 2: Reconciliation Integration
**Goal:** Connect existing matching systems to close workflow

#### Tasks:
1. Add reconciliation status API endpoints
2. Integrate revenue_matcher.py metrics into close dashboard
3. Integrate payslip_matcher.py metrics into close dashboard
4. Build reconciliation dashboard UI
5. Implement auto-check logic for matching status
6. Add "unmatched items" summary with drill-down

**Deliverables:**
- Dashboard shows real-time reconciliation status
- Auto-checks verify matching completeness
- One-click access to unmatched items

### Phase 3: Adjusting Entries
**Goal:** Enable adjustment entry management with approval workflow

#### Tasks:
1. Implement adjusting entries CRUD
2. Build entry approval workflow
3. Create entry form UI
4. Add entry posting to transactions table
5. Implement auto-reversal for accruals

**Deliverables:**
- Users can create adjusting entries
- Entries require approval before posting
- Posted entries appear in financial statements

### Phase 4: Approval & Audit
**Goal:** Complete approval workflow and audit trail

#### Tasks:
1. Implement submit for approval workflow
2. Add CFO/Controller approval actions
3. Build activity log system
4. Create audit trail UI
5. Implement notification system for approvals
6. Add rejection with comments flow

**Deliverables:**
- Complete approval chain from preparer to approver
- Full audit trail of all close activities
- Notifications for pending approvals

### Phase 5: Advanced Features
**Goal:** AI-powered assistance and automation

#### Tasks:
1. AI-suggested adjusting entries (based on historical patterns)
2. Anomaly detection in period data
3. Comparative analysis with prior periods
4. Pre-close report generation
5. Close timeline optimization suggestions

**Deliverables:**
- Claude AI suggests missing accruals
- System flags unusual variances
- Automated pre-close reports

---

## User Interface Mockups

### Close Dashboard

```
+------------------------------------------------------------------+
| Month-End Close                                    [Jan 2024 v]  |
+------------------------------------------------------------------+
| Status: IN PROGRESS (65% complete)                               |
| [============================------------] 13 of 20 tasks done   |
+------------------------------------------------------------------+
| QUICK STATS                                                       |
| +----------------+ +----------------+ +----------------+          |
| | Unmatched      | | Pending        | | Low Confidence |          |
| | Invoices: 3    | | Entries: 5     | | Txns: 12       |          |
| +----------------+ +----------------+ +----------------+          |
+------------------------------------------------------------------+
| CHECKLIST                                              [Run Auto-Checks]
+------------------------------------------------------------------+
| [ ] 1. Bank Reconciliation                    [In Progress] @John |
|     Last check: 45/50 transactions reconciled (90%)              |
| [x] 2. Record Revenue                         [Completed]   @Jane |
| [x] 3. Match Invoices to Payments             [Completed]   Auto  |
|     47/50 invoices matched (94%)                                 |
| [ ] 4. Match Payroll                          [Pending]     @John |
| [ ] 5. Review Low Confidence Transactions     [Pending]     @Jane |
| [ ] 6. Post Depreciation Entries              [Pending]     @John |
| [ ] 7. Post Accruals                          [Pending]     @Jane |
| [ ] 8. Reconcile A/R                          [Pending]     @John |
| [ ] 9. Reconcile A/P                          [Pending]     @Jane |
| [x] 10. Generate Trial Balance                [Completed]   Auto  |
+------------------------------------------------------------------+
| ACTIONS                                                           |
| [Lock Period]  [Submit for Approval]  [View Pre-Close Report]    |
+------------------------------------------------------------------+
```

### Reconciliation Dashboard

```
+------------------------------------------------------------------+
| Reconciliation Status - January 2024                             |
+------------------------------------------------------------------+
| REVENUE MATCHING                                                  |
| +-------------------------------------------------------------+  |
| | Matched: 47 | Unmatched: 3 | Total: 50 | Rate: 94%         |  |
| | [View Unmatched Invoices]                                   |  |
| +-------------------------------------------------------------+  |
|                                                                   |
| PAYROLL MATCHING                                                  |
| +-------------------------------------------------------------+  |
| | Matched: 12 | Unmatched: 2 | Total: 14 | Rate: 86%         |  |
| | [View Unmatched Payslips]                                   |  |
| +-------------------------------------------------------------+  |
|                                                                   |
| BANK RECONCILIATION                                               |
| +-------------------------------------------------------------+  |
| | Reconciled: 245 | Unreconciled: 5 | Total: 250 | Rate: 98% |  |
| | [View Unreconciled Transactions]                            |  |
| +-------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

---

## Integration with Existing Systems

### Transaction Locking

When a period is locked, the system must prevent:
1. Creating transactions dated within the locked period
2. Modifying transactions dated within the locked period
3. Deleting transactions dated within the locked period

Implementation approach:
```python
def validate_transaction_date(transaction_date, tenant_id):
    """Check if transaction date falls in locked period"""
    period = db.query("""
        SELECT id, status FROM cfo_accounting_periods
        WHERE tenant_id = %s
        AND %s BETWEEN start_date AND end_date
        AND status IN ('locked', 'closed')
    """, [tenant_id, transaction_date])

    if period:
        raise ValidationError(f"Cannot modify transactions in locked period")
```

### Matching System Integration

The existing `RevenueInvoiceMatcher` and `PayslipMatcher` classes can be queried for metrics:

```python
def get_reconciliation_metrics(period_id, tenant_id):
    period = get_period(period_id)

    # Invoice matching stats
    invoice_stats = db.query("""
        SELECT
            COUNT(*) FILTER (WHERE i.payment_status = 'paid') as matched,
            COUNT(*) FILTER (WHERE i.payment_status != 'paid') as unmatched,
            COUNT(*) as total
        FROM invoices i
        WHERE i.tenant_id = %s
        AND i.issue_date BETWEEN %s AND %s
    """, [tenant_id, period.start_date, period.end_date])

    # Similar queries for payslips and bank transactions
    return {
        'invoices': invoice_stats,
        'payslips': payslip_stats,
        'bank': bank_stats
    }
```

---

## Security & Permissions

### New Permissions Required

```python
CLOSE_PERMISSIONS = {
    'close.view': 'View close dashboard and status',
    'close.manage': 'Start close process, update checklist',
    'close.entries.create': 'Create adjusting entries',
    'close.entries.approve': 'Approve adjusting entries',
    'close.lock': 'Lock accounting period',
    'close.unlock': 'Unlock accounting period (emergency)',
    'close.approve': 'Approve period for close (CFO/Controller)',
    'close.reject': 'Reject period close',
    'close.finalize': 'Finalize and close period'
}
```

### Role Mapping

| Role | Permissions |
|------|-------------|
| Accountant | view, manage, entries.create |
| Senior Accountant | view, manage, entries.create, entries.approve |
| Controller | view, manage, entries.create, entries.approve, lock, approve, reject |
| CFO | All permissions |
| Tenant Admin | All permissions |

---

## Success Metrics

### MVP Success Criteria
- [ ] Periods can be created and managed
- [ ] Checklist items can be completed
- [ ] Period locking prevents transaction modifications
- [ ] Basic close dashboard is functional
- [ ] Reconciliation status is visible

### Full Feature Success Criteria
- [ ] Average close time reduced by 50%
- [ ] 100% audit trail for all close activities
- [ ] Zero unauthorized modifications to locked periods
- [ ] 90%+ checklist automation rate
- [ ] CFO approval workflow fully functional

---

## Estimated Effort

| Phase | Description | Estimated Effort |
|-------|-------------|------------------|
| Phase 1 | Core Infrastructure (MVP) | 3-4 weeks |
| Phase 2 | Reconciliation Integration | 2 weeks |
| Phase 3 | Adjusting Entries | 2 weeks |
| Phase 4 | Approval & Audit | 2 weeks |
| Phase 5 | Advanced Features | 3-4 weeks |

**Total: 12-14 weeks for full implementation**

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Transaction lock bypass | High | Add database triggers for enforcement |
| Incomplete reconciliation data | Medium | Add fallback manual override with audit |
| Complex multi-entity close | Medium | Phase implementation, start single-entity |
| User adoption | Low | Provide training, gradual rollout |

---

## Implementation Status

### Phase 1: Core Infrastructure (MVP) - COMPLETED

| Component | Status | File(s) |
|-----------|--------|---------|
| Database migration | Done | `migrations/add_month_end_closing_tables.sql` |
| Migration script | Done | `migrations/apply_month_end_closing_migration.py` |
| Period management service | Done | `web_ui/services/month_end_close.py` |
| API endpoints (15+) | Done | `web_ui/routes/close_routes.py` |
| Dashboard UI | Done | `web_ui/templates/month_end_close.html` |
| Dashboard JavaScript | Done | `web_ui/static/js/month_end_close.js` |
| Navigation link | Done | `web_ui/templates/_navbar.html` |
| i18n translations | Done | `en.json`, `es.json`, `pt.json` |
| Transaction period lock validation | Done | `web_ui/app_db.py` (check_period_lock_for_transaction) |

### Phase 2: Reconciliation Integration - COMPLETED

| Component | Status | File(s) |
|-----------|--------|---------|
| Reconciliation metrics service | Done | `web_ui/services/month_end_close.py` (lines 930-1423) |
| Invoice matching stats | Done | `get_invoice_matching_stats()` method |
| Payslip matching stats | Done | `get_payslip_matching_stats()` method |
| Transaction classification stats | Done | `get_transaction_classification_stats()` method |
| Overall health calculation | Done | `_calculate_overall_health()` method |
| Unmatched items query | Done | `get_unmatched_items()` method |
| Auto-check system | Done | `run_auto_checks()`, `run_single_auto_check()` methods |
| Reconciliation API endpoints | Done | `web_ui/routes/close_routes.py` (lines 542-745) |
| Reconciliation UI section | Done | `web_ui/templates/month_end_close.html` |
| Unmatched items modal | Done | `web_ui/templates/month_end_close.html` |
| Frontend reconciliation JS | Done | `web_ui/static/js/month_end_close.js` (lines 786-1028) |

### Remaining Work

**Phase 1-2: COMPLETE**

**Phase 3: Adjusting Entries (Not Started)**
- Adjusting entries CRUD
- Entry approval workflow
- Entry posting to transactions

**Phase 4: Approval & Audit (Not Started)**
- Submit for approval workflow enhancements
- Notification system
- Enhanced audit trail

**Phase 5: Advanced Features (Not Started)**
- AI-suggested adjusting entries
- Anomaly detection
- Pre-close report generation

## Next Steps

1. **Apply migration** to database: `python migrations/apply_month_end_closing_migration.py`
2. **Test the feature** by navigating to `/month-end-close`
3. **Implement Phase 2** - Reconciliation integration

---

## References

- [Vena Solutions - Month-End Close Process Checklist](https://www.venasolutions.com/blog/month-end-close-process-checklist)
- [Numeric - Financial Close Software](https://www.numeric.io/blog/financial-close-software)
- [HighRadius - Month-End Close Process](https://www.highradius.com/resources/Blog/what-is-month-end-close-process/)
- [NetGain - GL Transaction Locking](https://www.netgain.tech/blog/gl-transaction-locking)
- [FloQast vs BlackLine Comparison](https://www.numeric.io/blog/floqast-vs-blackline)
- [NetSuite Period Close Documentation](https://docs.oracle.com/en/cloud/saas/netsuite/ns-online-help/section_N1452509.html)
- [SolveXia - Month-End Close](https://www.solvexia.com/blog/month-end-close)
