-- ========================================
-- ENHANCE CLASSIFICATION PATTERNS FOR DATABASE-DRIVEN CLASSIFICATION
-- ========================================
-- This migration extends the classification_patterns table to support
-- ALL classification logic currently hardcoded in classify_transaction()
--
-- Date: 2025-01-14
-- Purpose: Enable 100% database-driven, multi-tenant classification
-- ========================================

-- Create classification_patterns table if it doesn't exist
CREATE TABLE IF NOT EXISTS classification_patterns (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL,
    pattern_type VARCHAR(50) NOT NULL, -- 'revenue', 'transfer', 'expense', 'technology', 'card_mapping', etc.
    description_pattern TEXT NOT NULL, -- SQL LIKE pattern (e.g., '%COINBASE%') or exact match
    entity VARCHAR(255), -- Entity name to assign (can be NULL for expense patterns)
    accounting_category VARCHAR(100), -- Category to assign
    confidence_score DECIMAL(5,2) DEFAULT 0.50,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenant_configuration(tenant_id) ON DELETE CASCADE
);

-- Add new columns for advanced classification logic
ALTER TABLE classification_patterns
ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 500,
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS rule_conditions JSONB DEFAULT '{}',
ADD COLUMN IF NOT EXISTS subcategory VARCHAR(100),
ADD COLUMN IF NOT EXISTS created_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS notes TEXT;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_classification_patterns_tenant ON classification_patterns(tenant_id);
CREATE INDEX IF NOT EXISTS idx_classification_patterns_type ON classification_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_classification_patterns_priority ON classification_patterns(tenant_id, priority DESC, is_active);
CREATE INDEX IF NOT EXISTS idx_classification_patterns_active ON classification_patterns(tenant_id, is_active);

-- Add trigger for updated_at
CREATE OR REPLACE FUNCTION update_classification_patterns_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_classification_patterns_updated_at
    BEFORE UPDATE ON classification_patterns
    FOR EACH ROW
    EXECUTE FUNCTION update_classification_patterns_updated_at();

-- ========================================
-- EXPLANATION OF NEW COLUMNS
-- ========================================

-- priority: Controls execution order (0-1000)
--   0-99: Intermediate routing patterns (highest priority)
--   100-199: Currency-based rules
--   200-299: Wallet address lookups (system-managed)
--   300-399: Specific vendor/employee patterns
--   400-499: General description patterns
--   500-899: Expense/revenue patterns
--   900-999: Default fallback rules

-- rule_conditions: JSONB for complex matching logic
--   {
--     "type": "currency_match",       // Type of rule
--     "currency": "BTC",               // Match on currency field
--     "min_amount": 0.0,               // Minimum amount (optional)
--     "max_amount": null,              // Maximum amount (optional)
--     "match_mode": "exact|contains|regex",  // How to match description_pattern
--     "account_filter": "CHASE BUSINESS",    // Filter by account (optional)
--     "amount_sign": "positive|negative|any" // Transaction direction
--   }
--
--   {
--     "type": "compound_pattern",     // Multiple conditions
--     "all_of": ["COINBASE", "ROUTING"],  // All must match
--     "none_of": ["FINAL DESTINATION"],   // None can match
--     "any_of": ["SEND", "RECEIVE"]       // At least one must match
--   }
--
--   {
--     "type": "intermediate_routing", // Intermediate step classification
--     "final_entity": null,            // Don't set entity yet
--     "mark_for_reprocessing": true    // Flag for second pass
--   }

-- Success message
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Classification Patterns Enhanced Successfully!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'New capabilities:';
    RAISE NOTICE '  - Priority-based execution (0-999)';
    RAISE NOTICE '  - Complex rule conditions (JSONB)';
    RAISE NOTICE '  - Subcategory support';
    RAISE NOTICE '  - Active/inactive toggle';
    RAISE NOTICE '  - Audit trail (created_by, notes)';
    RAISE NOTICE '';
    RAISE NOTICE 'Ready for migration of hardcoded patterns!';
    RAISE NOTICE '========================================';
END $$;
