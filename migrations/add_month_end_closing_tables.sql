-- ========================================
-- Month-End Closing System - Database Migration
-- ========================================
-- This migration adds tables for accounting period management,
-- closing checklists, adjusting entries, and audit logging.
--
-- Tables created:
-- 1. cfo_accounting_periods - Period tracking with status
-- 2. close_checklist_templates - Reusable checklist templates
-- 3. close_checklist_items - Period-specific checklist instances
-- 4. close_adjusting_entries - Adjustment entries with approval
-- 5. close_activity_log - Audit trail for close activities
-- 6. period_locks - Granular locking (A/P, A/R, Payroll, All)
--
-- Run: psql -d your_database -f migrations/add_month_end_closing_tables.sql
-- ========================================

-- ========================================
-- 1. ACCOUNTING PERIODS TABLE
-- ========================================

CREATE TABLE IF NOT EXISTS cfo_accounting_periods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,

    -- Period Identification
    period_name VARCHAR(50) NOT NULL,  -- "2024-01", "2024-02", "2024-Q1", etc.
    period_type VARCHAR(20) DEFAULT 'monthly',  -- 'monthly', 'quarterly', 'yearly'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,

    -- Status Tracking
    status VARCHAR(20) DEFAULT 'open',  -- 'open', 'in_progress', 'pending_approval', 'locked', 'closed'

    -- Lock Information
    locked_at TIMESTAMP,
    locked_by UUID,

    -- Approval Information
    submitted_at TIMESTAMP,
    submitted_by UUID,
    approved_at TIMESTAMP,
    approved_by UUID,
    rejection_reason TEXT,

    -- Close Information
    closed_at TIMESTAMP,
    closed_by UUID,

    -- Additional Info
    notes TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(tenant_id, period_name)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_accounting_periods_tenant ON cfo_accounting_periods(tenant_id);
CREATE INDEX IF NOT EXISTS idx_accounting_periods_status ON cfo_accounting_periods(status);
CREATE INDEX IF NOT EXISTS idx_accounting_periods_dates ON cfo_accounting_periods(start_date, end_date);

-- ========================================
-- 2. CLOSE CHECKLIST TEMPLATES TABLE
-- ========================================

CREATE TABLE IF NOT EXISTS close_checklist_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,

    -- Template Information
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,  -- 'bank_reconciliation', 'revenue', 'expenses', 'payroll', 'adjustments', 'review'

    -- Ordering and Requirements
    sequence_order INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT true,

    -- Auto-Check Configuration
    auto_check_type VARCHAR(50),  -- null for manual, or: 'bank_reconciled', 'invoices_matched', 'payslips_matched', 'low_confidence_reviewed', 'unclassified_resolved'
    auto_check_threshold DECIMAL(5,2),  -- e.g., 95.00 for 95% matched

    -- Assignment
    assigned_role VARCHAR(50),  -- 'accountant', 'senior_accountant', 'controller', 'cfo'
    estimated_minutes INTEGER,

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_checklist_templates_tenant ON close_checklist_templates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_checklist_templates_category ON close_checklist_templates(category);
CREATE INDEX IF NOT EXISTS idx_checklist_templates_active ON close_checklist_templates(is_active);

-- ========================================
-- 3. CLOSE CHECKLIST ITEMS TABLE
-- ========================================

CREATE TABLE IF NOT EXISTS close_checklist_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_id UUID NOT NULL REFERENCES cfo_accounting_periods(id) ON DELETE CASCADE,
    template_id UUID REFERENCES close_checklist_templates(id) ON DELETE SET NULL,

    -- Item Information
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL,

    -- Ordering and Requirements
    sequence_order INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT true,

    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'in_progress', 'completed', 'skipped', 'blocked'

    -- Auto-Check Results
    auto_check_type VARCHAR(50),
    auto_check_result JSONB,  -- {matched: 45, total: 50, percentage: 90, details: [...]}
    last_auto_check_at TIMESTAMP,

    -- Completion Information
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    completed_by UUID,

    -- Review Information
    reviewed_by UUID,
    reviewed_at TIMESTAMP,

    -- Additional Info
    notes TEXT,
    blockers TEXT,  -- reason if blocked
    skip_reason TEXT,  -- reason if skipped

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_checklist_items_period ON close_checklist_items(period_id);
CREATE INDEX IF NOT EXISTS idx_checklist_items_status ON close_checklist_items(status);
CREATE INDEX IF NOT EXISTS idx_checklist_items_template ON close_checklist_items(template_id);

-- ========================================
-- 4. CLOSE ADJUSTING ENTRIES TABLE
-- ========================================

CREATE TABLE IF NOT EXISTS close_adjusting_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_id UUID NOT NULL REFERENCES cfo_accounting_periods(id) ON DELETE CASCADE,
    tenant_id VARCHAR(100) NOT NULL,

    -- Entry Type
    entry_type VARCHAR(50) NOT NULL,  -- 'accrual', 'depreciation', 'prepaid', 'deferral', 'correction', 'reclassification', 'other'

    -- Entry Details
    description TEXT NOT NULL,
    debit_account VARCHAR(100) NOT NULL,
    credit_account VARCHAR(100) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    entity VARCHAR(100),

    -- Status
    status VARCHAR(20) DEFAULT 'draft',  -- 'draft', 'pending_approval', 'approved', 'posted', 'rejected'

    -- Approval Workflow
    created_by UUID,
    submitted_at TIMESTAMP,
    approved_by UUID,
    approved_at TIMESTAMP,
    rejected_by UUID,
    rejected_at TIMESTAMP,
    rejection_reason TEXT,

    -- Posting Information
    posted_at TIMESTAMP,
    posted_by UUID,
    transaction_id INTEGER,  -- Reference to transactions table after posting

    -- Auto-Reversal (for accruals)
    is_reversing BOOLEAN DEFAULT false,
    reversal_period_id UUID REFERENCES cfo_accounting_periods(id),
    original_entry_id UUID REFERENCES close_adjusting_entries(id),

    -- Additional Info
    notes TEXT,
    supporting_documents JSONB,  -- [{filename: string, path: string, uploaded_at: timestamp}]

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_adjusting_entries_period ON close_adjusting_entries(period_id);
CREATE INDEX IF NOT EXISTS idx_adjusting_entries_tenant ON close_adjusting_entries(tenant_id);
CREATE INDEX IF NOT EXISTS idx_adjusting_entries_status ON close_adjusting_entries(status);
CREATE INDEX IF NOT EXISTS idx_adjusting_entries_type ON close_adjusting_entries(entry_type);

-- ========================================
-- 5. CLOSE ACTIVITY LOG TABLE
-- ========================================

CREATE TABLE IF NOT EXISTS close_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_id UUID NOT NULL REFERENCES cfo_accounting_periods(id) ON DELETE CASCADE,
    tenant_id VARCHAR(100) NOT NULL,

    -- Action Information
    action VARCHAR(50) NOT NULL,  -- 'period_created', 'period_started', 'checklist_completed', 'entry_created', 'entry_approved', 'period_locked', 'period_approved', 'period_closed', etc.
    entity_type VARCHAR(50),  -- 'period', 'checklist_item', 'adjusting_entry', etc.
    entity_id UUID,

    -- User Information
    user_id UUID,
    user_name VARCHAR(255),
    user_role VARCHAR(50),

    -- Details
    details JSONB,  -- action-specific details
    old_value JSONB,  -- for changes, the previous value
    new_value JSONB,  -- for changes, the new value

    -- Metadata
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_activity_log_period ON close_activity_log(period_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_tenant ON close_activity_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_action ON close_activity_log(action);
CREATE INDEX IF NOT EXISTS idx_activity_log_user ON close_activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_created ON close_activity_log(created_at);

-- ========================================
-- 6. PERIOD LOCKS TABLE
-- ========================================

CREATE TABLE IF NOT EXISTS period_locks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_id UUID NOT NULL REFERENCES cfo_accounting_periods(id) ON DELETE CASCADE,

    -- Lock Type
    lock_type VARCHAR(50) NOT NULL,  -- 'transactions', 'invoices', 'payroll', 'adjustments', 'all'

    -- Lock Status
    is_locked BOOLEAN DEFAULT false,
    locked_at TIMESTAMP,
    locked_by UUID,

    -- Unlock Information (for emergency unlocks)
    unlocked_at TIMESTAMP,
    unlocked_by UUID,
    unlock_reason TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(period_id, lock_type)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_period_locks_period ON period_locks(period_id);
CREATE INDEX IF NOT EXISTS idx_period_locks_locked ON period_locks(is_locked);

-- ========================================
-- 7. INSERT DEFAULT CHECKLIST TEMPLATES
-- ========================================

-- Note: These are inserted only if they don't exist
-- Tenant-specific templates should be created during onboarding

INSERT INTO close_checklist_templates (tenant_id, name, description, category, sequence_order, is_required, auto_check_type, auto_check_threshold, assigned_role, estimated_minutes)
SELECT 'default', 'Bank Reconciliation', 'Reconcile all bank account transactions with bank statements', 'bank_reconciliation', 1, true, 'bank_reconciled', 100.00, 'accountant', 60
WHERE NOT EXISTS (SELECT 1 FROM close_checklist_templates WHERE tenant_id = 'default' AND name = 'Bank Reconciliation');

INSERT INTO close_checklist_templates (tenant_id, name, description, category, sequence_order, is_required, auto_check_type, auto_check_threshold, assigned_role, estimated_minutes)
SELECT 'default', 'Match Revenue Invoices', 'Match all revenue invoices to payment transactions', 'revenue', 2, true, 'invoices_matched', 95.00, 'accountant', 45
WHERE NOT EXISTS (SELECT 1 FROM close_checklist_templates WHERE tenant_id = 'default' AND name = 'Match Revenue Invoices');

INSERT INTO close_checklist_templates (tenant_id, name, description, category, sequence_order, is_required, auto_check_type, auto_check_threshold, assigned_role, estimated_minutes)
SELECT 'default', 'Match Payroll Transactions', 'Match all payslips to payment transactions', 'payroll', 3, true, 'payslips_matched', 95.00, 'accountant', 30
WHERE NOT EXISTS (SELECT 1 FROM close_checklist_templates WHERE tenant_id = 'default' AND name = 'Match Payroll Transactions');

INSERT INTO close_checklist_templates (tenant_id, name, description, category, sequence_order, is_required, auto_check_type, auto_check_threshold, assigned_role, estimated_minutes)
SELECT 'default', 'Review Low Confidence Transactions', 'Review and confirm transactions with confidence score below 70%', 'review', 4, true, 'low_confidence_reviewed', 100.00, 'senior_accountant', 45
WHERE NOT EXISTS (SELECT 1 FROM close_checklist_templates WHERE tenant_id = 'default' AND name = 'Review Low Confidence Transactions');

INSERT INTO close_checklist_templates (tenant_id, name, description, category, sequence_order, is_required, auto_check_type, auto_check_threshold, assigned_role, estimated_minutes)
SELECT 'default', 'Resolve Unclassified Transactions', 'Classify all unclassified transactions', 'review', 5, true, 'unclassified_resolved', 100.00, 'accountant', 30
WHERE NOT EXISTS (SELECT 1 FROM close_checklist_templates WHERE tenant_id = 'default' AND name = 'Resolve Unclassified Transactions');

INSERT INTO close_checklist_templates (tenant_id, name, description, category, sequence_order, is_required, auto_check_type, auto_check_threshold, assigned_role, estimated_minutes)
SELECT 'default', 'Post Depreciation Entries', 'Record depreciation for all fixed assets', 'adjustments', 6, true, NULL, NULL, 'accountant', 20
WHERE NOT EXISTS (SELECT 1 FROM close_checklist_templates WHERE tenant_id = 'default' AND name = 'Post Depreciation Entries');

INSERT INTO close_checklist_templates (tenant_id, name, description, category, sequence_order, is_required, auto_check_type, auto_check_threshold, assigned_role, estimated_minutes)
SELECT 'default', 'Post Accrual Entries', 'Record all accrued expenses and revenues', 'adjustments', 7, true, NULL, NULL, 'accountant', 30
WHERE NOT EXISTS (SELECT 1 FROM close_checklist_templates WHERE tenant_id = 'default' AND name = 'Post Accrual Entries');

INSERT INTO close_checklist_templates (tenant_id, name, description, category, sequence_order, is_required, auto_check_type, auto_check_threshold, assigned_role, estimated_minutes)
SELECT 'default', 'Reconcile Accounts Receivable', 'Verify A/R balances match subsidiary ledger', 'review', 8, true, NULL, NULL, 'senior_accountant', 30
WHERE NOT EXISTS (SELECT 1 FROM close_checklist_templates WHERE tenant_id = 'default' AND name = 'Reconcile Accounts Receivable');

INSERT INTO close_checklist_templates (tenant_id, name, description, category, sequence_order, is_required, auto_check_type, auto_check_threshold, assigned_role, estimated_minutes)
SELECT 'default', 'Reconcile Accounts Payable', 'Verify A/P balances match subsidiary ledger', 'review', 9, true, NULL, NULL, 'senior_accountant', 30
WHERE NOT EXISTS (SELECT 1 FROM close_checklist_templates WHERE tenant_id = 'default' AND name = 'Reconcile Accounts Payable');

INSERT INTO close_checklist_templates (tenant_id, name, description, category, sequence_order, is_required, auto_check_type, auto_check_threshold, assigned_role, estimated_minutes)
SELECT 'default', 'Generate Trial Balance', 'Generate and review trial balance for the period', 'review', 10, true, NULL, NULL, 'controller', 15
WHERE NOT EXISTS (SELECT 1 FROM close_checklist_templates WHERE tenant_id = 'default' AND name = 'Generate Trial Balance');

INSERT INTO close_checklist_templates (tenant_id, name, description, category, sequence_order, is_required, auto_check_type, auto_check_threshold, assigned_role, estimated_minutes)
SELECT 'default', 'Review Financial Statements', 'Review P&L, Balance Sheet, and Cash Flow Statement', 'review', 11, true, NULL, NULL, 'controller', 45
WHERE NOT EXISTS (SELECT 1 FROM close_checklist_templates WHERE tenant_id = 'default' AND name = 'Review Financial Statements');

INSERT INTO close_checklist_templates (tenant_id, name, description, category, sequence_order, is_required, auto_check_type, auto_check_threshold, assigned_role, estimated_minutes)
SELECT 'default', 'CFO Final Review', 'CFO review and approval of period close', 'review', 12, true, NULL, NULL, 'cfo', 30
WHERE NOT EXISTS (SELECT 1 FROM close_checklist_templates WHERE tenant_id = 'default' AND name = 'CFO Final Review');

-- ========================================
-- 8. UPDATE TRIGGER FOR TIMESTAMPS
-- ========================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_close_tables_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for each table
DROP TRIGGER IF EXISTS update_accounting_periods_timestamp ON cfo_accounting_periods;
CREATE TRIGGER update_accounting_periods_timestamp
    BEFORE UPDATE ON cfo_accounting_periods
    FOR EACH ROW
    EXECUTE FUNCTION update_close_tables_timestamp();

DROP TRIGGER IF EXISTS update_checklist_templates_timestamp ON close_checklist_templates;
CREATE TRIGGER update_checklist_templates_timestamp
    BEFORE UPDATE ON close_checklist_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_close_tables_timestamp();

DROP TRIGGER IF EXISTS update_checklist_items_timestamp ON close_checklist_items;
CREATE TRIGGER update_checklist_items_timestamp
    BEFORE UPDATE ON close_checklist_items
    FOR EACH ROW
    EXECUTE FUNCTION update_close_tables_timestamp();

DROP TRIGGER IF EXISTS update_adjusting_entries_timestamp ON close_adjusting_entries;
CREATE TRIGGER update_adjusting_entries_timestamp
    BEFORE UPDATE ON close_adjusting_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_close_tables_timestamp();

DROP TRIGGER IF EXISTS update_period_locks_timestamp ON period_locks;
CREATE TRIGGER update_period_locks_timestamp
    BEFORE UPDATE ON period_locks
    FOR EACH ROW
    EXECUTE FUNCTION update_close_tables_timestamp();

-- ========================================
-- MIGRATION COMPLETE
-- ========================================
-- Run with: psql -d your_database -f migrations/add_month_end_closing_tables.sql
--
-- To verify:
-- SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'cfo_%' OR table_name LIKE 'close_%' OR table_name = 'period_locks';
