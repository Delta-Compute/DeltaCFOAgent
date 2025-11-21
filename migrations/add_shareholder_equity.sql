-- ========================================
-- Shareholder Equity Tracking System
-- ========================================
-- Migration to add shareholder equity tracking functionality
-- Run this migration to enable shareholder and equity contribution management

-- ========================================
-- SHAREHOLDERS TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS shareholders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    shareholder_name VARCHAR(255) NOT NULL,
    shareholder_type VARCHAR(50) NOT NULL, -- 'individual', 'corporate', 'institutional', 'founder', 'angel', 'vc'
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    tax_id VARCHAR(100), -- SSN, EIN, or international equivalent
    address TEXT,
    ownership_percentage DECIMAL(5,2), -- Current ownership percentage (calculated from contributions)
    total_shares INTEGER, -- Total number of shares owned
    share_class VARCHAR(50), -- 'common', 'preferred', 'series-a', 'series-b', etc.
    board_member BOOLEAN DEFAULT FALSE,
    voting_rights BOOLEAN DEFAULT TRUE,
    joining_date DATE,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'exited'
    exit_date DATE,
    exit_price DECIMAL(15,2),
    notes TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, shareholder_name)
);

-- ========================================
-- EQUITY CONTRIBUTIONS TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS equity_contributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    shareholder_id UUID REFERENCES shareholders(id) ON DELETE CASCADE,
    contribution_date DATE NOT NULL,
    contribution_type VARCHAR(50) NOT NULL, -- 'cash', 'property', 'services', 'intellectual_property', 'debt_conversion'
    cash_amount DECIMAL(15,2) DEFAULT 0.00, -- Cash contribution amount (if applicable)
    non_cash_value DECIMAL(15,2) DEFAULT 0.00, -- Fair market value of non-cash contributions
    shares_issued INTEGER NOT NULL, -- Number of shares issued for this contribution
    price_per_share DECIMAL(15,4), -- Price per share at time of contribution
    share_class VARCHAR(50), -- 'common', 'preferred', 'series-a', etc.
    valuation_at_contribution DECIMAL(18,2), -- Company valuation at time of contribution
    dilution_percentage DECIMAL(5,2), -- Dilution caused by this contribution
    transaction_reference VARCHAR(255), -- Reference to related transaction (if any)
    description TEXT,
    documentation_path TEXT, -- Path to subscription agreement, stock certificate, etc.
    verified BOOLEAN DEFAULT FALSE, -- Whether contribution has been verified/audited
    verified_by VARCHAR(100),
    verified_at TIMESTAMP,
    notes TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- EQUITY EVENTS TABLE
-- ========================================
-- Track significant equity events (splits, buybacks, dilutions, etc.)
CREATE TABLE IF NOT EXISTS equity_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- 'stock_split', 'reverse_split', 'buyback', 'dividend', 'rights_offering', 'conversion'
    event_date DATE NOT NULL,
    description TEXT,
    affects_all_shareholders BOOLEAN DEFAULT TRUE,
    affected_shareholder_id UUID REFERENCES shareholders(id) ON DELETE SET NULL, -- NULL if affects all
    share_class VARCHAR(50), -- Affected share class
    multiplier DECIMAL(10,4), -- For splits (e.g., 2.0 for 2-for-1 split)
    shares_affected INTEGER,
    financial_impact DECIMAL(15,2),
    documentation_path TEXT,
    notes TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- CAP TABLE SNAPSHOTS
-- ========================================
-- Periodic snapshots of capitalization table for historical tracking
CREATE TABLE IF NOT EXISTS cap_table_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    snapshot_date DATE NOT NULL,
    total_shares_outstanding INTEGER NOT NULL,
    company_valuation DECIMAL(18,2),
    fully_diluted_shares INTEGER, -- Including options, warrants, etc.
    snapshot_data JSONB, -- Complete cap table data as JSON
    notes TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, snapshot_date)
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- Shareholders indexes
CREATE INDEX IF NOT EXISTS idx_shareholders_tenant ON shareholders(tenant_id);
CREATE INDEX IF NOT EXISTS idx_shareholders_status ON shareholders(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_shareholders_type ON shareholders(shareholder_type);
CREATE INDEX IF NOT EXISTS idx_shareholders_share_class ON shareholders(share_class);

-- Equity contributions indexes
CREATE INDEX IF NOT EXISTS idx_equity_contributions_tenant ON equity_contributions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_equity_contributions_shareholder ON equity_contributions(shareholder_id);
CREATE INDEX IF NOT EXISTS idx_equity_contributions_date ON equity_contributions(contribution_date);
CREATE INDEX IF NOT EXISTS idx_equity_contributions_type ON equity_contributions(contribution_type);
CREATE INDEX IF NOT EXISTS idx_equity_contributions_verified ON equity_contributions(verified);

-- Equity events indexes
CREATE INDEX IF NOT EXISTS idx_equity_events_tenant ON equity_events(tenant_id);
CREATE INDEX IF NOT EXISTS idx_equity_events_date ON equity_events(event_date);
CREATE INDEX IF NOT EXISTS idx_equity_events_type ON equity_events(event_type);
CREATE INDEX IF NOT EXISTS idx_equity_events_shareholder ON equity_events(affected_shareholder_id);

-- Cap table snapshots indexes
CREATE INDEX IF NOT EXISTS idx_cap_table_snapshots_tenant ON cap_table_snapshots(tenant_id);
CREATE INDEX IF NOT EXISTS idx_cap_table_snapshots_date ON cap_table_snapshots(snapshot_date);

-- ========================================
-- TRIGGERS FOR AUTOMATIC TIMESTAMPS
-- ========================================

CREATE TRIGGER update_shareholders_updated_at BEFORE UPDATE ON shareholders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_equity_contributions_updated_at BEFORE UPDATE ON equity_contributions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_equity_events_updated_at BEFORE UPDATE ON equity_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- ANALYTICS VIEWS
-- ========================================

-- Shareholder ownership summary view
CREATE OR REPLACE VIEW shareholder_ownership_summary AS
SELECT
    s.tenant_id,
    s.id as shareholder_id,
    s.shareholder_name,
    s.shareholder_type,
    s.share_class,
    s.total_shares,
    s.ownership_percentage,
    s.status,
    SUM(ec.cash_amount) as total_cash_contributed,
    SUM(ec.non_cash_value) as total_non_cash_contributed,
    SUM(ec.cash_amount + ec.non_cash_value) as total_value_contributed,
    COUNT(ec.id) as contribution_count,
    MIN(ec.contribution_date) as first_contribution_date,
    MAX(ec.contribution_date) as last_contribution_date
FROM shareholders s
LEFT JOIN equity_contributions ec ON s.id = ec.shareholder_id
WHERE s.status = 'active'
GROUP BY s.tenant_id, s.id, s.shareholder_name, s.shareholder_type, s.share_class,
         s.total_shares, s.ownership_percentage, s.status
ORDER BY s.ownership_percentage DESC;

-- Share class distribution view
CREATE OR REPLACE VIEW share_class_distribution AS
SELECT
    tenant_id,
    share_class,
    COUNT(DISTINCT id) as shareholder_count,
    SUM(total_shares) as total_shares,
    SUM(ownership_percentage) as total_ownership_percentage,
    AVG(ownership_percentage) as avg_ownership_percentage
FROM shareholders
WHERE status = 'active'
GROUP BY tenant_id, share_class
ORDER BY total_ownership_percentage DESC;

-- Equity contribution timeline view
CREATE OR REPLACE VIEW equity_contribution_timeline AS
SELECT
    ec.tenant_id,
    ec.contribution_date,
    s.shareholder_name,
    s.shareholder_type,
    ec.contribution_type,
    ec.cash_amount,
    ec.non_cash_value,
    (ec.cash_amount + ec.non_cash_value) as total_value,
    ec.shares_issued,
    ec.price_per_share,
    ec.valuation_at_contribution,
    ec.share_class
FROM equity_contributions ec
JOIN shareholders s ON ec.shareholder_id = s.id
ORDER BY ec.contribution_date DESC, ec.created_at DESC;

-- ========================================
-- COMPLETION MESSAGE
-- ========================================

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Shareholder Equity Tracking Migration Complete!';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '- shareholders: Track shareholder information';
    RAISE NOTICE '- equity_contributions: Record equity investments';
    RAISE NOTICE '- equity_events: Track stock splits, buybacks, etc.';
    RAISE NOTICE '- cap_table_snapshots: Historical cap table records';
    RAISE NOTICE '';
    RAISE NOTICE 'Views created:';
    RAISE NOTICE '- shareholder_ownership_summary';
    RAISE NOTICE '- share_class_distribution';
    RAISE NOTICE '- equity_contribution_timeline';
    RAISE NOTICE '';
    RAISE NOTICE 'Ready for shareholder equity management!';
    RAISE NOTICE '==============================================';
END $$;
