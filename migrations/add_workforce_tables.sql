-- ========================================
-- Workforce Management System - Database Migration
-- ========================================
-- This migration adds tables for employee/contractor management,
-- payslip generation, and payslip-transaction matching.
--
-- Tables created:
-- 1. workforce_members - Employee and contractor records
-- 2. payslips - Payslip records with payment details
-- 3. pending_payslip_matches - Potential transaction matches
-- 4. payslip_match_log - Match action audit trail
--
-- Run: psql -d your_database -f migrations/add_workforce_tables.sql
-- ========================================

-- ========================================
-- 1. WORKFORCE MEMBERS TABLE
-- ========================================

CREATE TABLE IF NOT EXISTS workforce_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,

    -- Basic Information
    full_name VARCHAR(255) NOT NULL,
    employment_type VARCHAR(50) NOT NULL, -- 'employee', 'contractor'
    document_type VARCHAR(50), -- 'ssn', 'ein', 'tax_id', 'passport', 'national_id'
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

-- ========================================
-- 2. PAYSLIPS TABLE
-- ========================================

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
    line_items JSONB, -- [{type: 'salary'|'bonus'|'overtime', description: string, amount: number, hours: number}]
    deductions_items JSONB, -- [{type: 'tax'|'insurance'|'401k'|'other', description: string, amount: number}]

    -- Payment Status
    status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'approved', 'paid', 'cancelled'
    payment_method VARCHAR(50), -- 'bank_transfer', 'check', 'cash', 'crypto', 'wire'

    -- Transaction Matching (links to transactions table)
    transaction_id INTEGER, -- Links to transactions.id when matched
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

-- ========================================
-- 3. PENDING PAYSLIP MATCHES TABLE
-- ========================================
-- Stores potential matches between payslips and transactions
-- Similar to pending_invoice_matches table

CREATE TABLE IF NOT EXISTS pending_payslip_matches (
    id SERIAL PRIMARY KEY,
    payslip_id UUID NOT NULL REFERENCES payslips(id) ON DELETE CASCADE,
    transaction_id INTEGER NOT NULL, -- References transactions.id
    score DECIMAL(3,2) NOT NULL, -- Match confidence score 0.00 - 1.00
    match_type TEXT NOT NULL, -- 'amount_date', 'semantic', 'vendor_name', 'combined'
    criteria_scores JSONB, -- {amount: 0.95, date: 0.80, description: 0.70, ...}
    confidence_level TEXT NOT NULL, -- 'high', 'medium', 'low'
    explanation TEXT, -- Human-readable explanation of the match
    status TEXT DEFAULT 'pending', -- 'pending', 'confirmed', 'rejected'
    reviewed_by TEXT,
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(payslip_id, transaction_id)
);

-- ========================================
-- 4. PAYSLIP MATCH LOG TABLE
-- ========================================
-- Audit trail for all match actions

CREATE TABLE IF NOT EXISTS payslip_match_log (
    id SERIAL PRIMARY KEY,
    payslip_id UUID NOT NULL REFERENCES payslips(id) ON DELETE CASCADE,
    transaction_id INTEGER NOT NULL, -- References transactions.id
    action TEXT NOT NULL, -- 'confirmed', 'rejected', 'manual_link', 'unmatched'
    score DECIMAL(3,2), -- Match score at time of action
    match_type TEXT, -- Match type at time of action
    user_id TEXT,
    notes TEXT, -- Optional notes about the action
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- Workforce members indexes
CREATE INDEX IF NOT EXISTS idx_workforce_members_tenant ON workforce_members(tenant_id);
CREATE INDEX IF NOT EXISTS idx_workforce_members_status ON workforce_members(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_workforce_members_type ON workforce_members(employment_type);
CREATE INDEX IF NOT EXISTS idx_workforce_members_hire_date ON workforce_members(date_of_hire);

-- Payslips indexes
CREATE INDEX IF NOT EXISTS idx_payslips_tenant ON payslips(tenant_id);
CREATE INDEX IF NOT EXISTS idx_payslips_member ON payslips(workforce_member_id);
CREATE INDEX IF NOT EXISTS idx_payslips_status ON payslips(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_payslips_payment_date ON payslips(payment_date);
CREATE INDEX IF NOT EXISTS idx_payslips_transaction ON payslips(transaction_id);
CREATE INDEX IF NOT EXISTS idx_payslips_period ON payslips(pay_period_start, pay_period_end);

-- Pending matches indexes
CREATE INDEX IF NOT EXISTS idx_pending_payslip_matches_payslip ON pending_payslip_matches(payslip_id);
CREATE INDEX IF NOT EXISTS idx_pending_payslip_matches_transaction ON pending_payslip_matches(transaction_id);
CREATE INDEX IF NOT EXISTS idx_pending_payslip_matches_status ON pending_payslip_matches(status);

-- Match log indexes
CREATE INDEX IF NOT EXISTS idx_payslip_match_log_payslip ON payslip_match_log(payslip_id);
CREATE INDEX IF NOT EXISTS idx_payslip_match_log_transaction ON payslip_match_log(transaction_id);
CREATE INDEX IF NOT EXISTS idx_payslip_match_log_created ON payslip_match_log(created_at);

-- ========================================
-- TRIGGERS FOR AUTOMATIC TIMESTAMPS
-- ========================================

-- Reuse existing update_updated_at_column function
CREATE TRIGGER update_workforce_members_updated_at BEFORE UPDATE ON workforce_members
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payslips_updated_at BEFORE UPDATE ON payslips
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- INITIAL SEED DATA (OPTIONAL)
-- ========================================

-- Insert sample workforce member for Delta tenant (for testing)
-- Commented out by default - uncomment if you want test data
/*
INSERT INTO workforce_members (
    tenant_id, full_name, employment_type, document_type, document_number,
    date_of_hire, status, pay_rate, pay_frequency, currency,
    email, job_title, department, created_by
) VALUES (
    'delta', 'John Doe', 'employee', 'ssn', '***-**-1234',
    '2024-01-01', 'active', 85000.00, 'annual', 'USD',
    'john.doe@example.com', 'Senior Developer', 'Engineering', 'system'
) ON CONFLICT (tenant_id, document_number) DO NOTHING;
*/

-- ========================================
-- COMPLETION MESSAGE
-- ========================================

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Workforce Management Migration Complete!';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '- workforce_members: Employee and contractor records';
    RAISE NOTICE '- payslips: Payslip records with payment details';
    RAISE NOTICE '- pending_payslip_matches: Transaction matching';
    RAISE NOTICE '- payslip_match_log: Match action audit trail';
    RAISE NOTICE '';
    RAISE NOTICE 'Indexes created for optimal query performance';
    RAISE NOTICE 'Triggers configured for automatic timestamps';
    RAISE NOTICE '==============================================';
END $$;
