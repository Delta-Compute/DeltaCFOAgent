-- ============================================================================
-- Entity and Business Line Architecture Migration
-- ============================================================================
-- This migration creates the Entity and Business Line architecture,
-- restructuring from flat entity VARCHAR to a 3-tier model:
--   Tier 1: Organization (tenant_id) - Already exists
--   Tier 2: Entity (Legal entity with separate books)
--   Tier 3: Business Line (Profit center within entity)
--
-- Author: Claude Code
-- Date: 2024-11-24
-- Based on: Entity vs Business Line Architecture Research
-- ============================================================================

-- ============================================================================
-- STEP 1: Create entities table (Tier 2 - Legal Entities)
-- ============================================================================

CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,

    -- Entity Identification
    code VARCHAR(20) NOT NULL,           -- Short code: "DLLC", "DPY", "DBR"
    name VARCHAR(255) NOT NULL,          -- Full legal name: "Delta Mining LLC"
    legal_name VARCHAR(255),             -- Official registered name (if different)

    -- Legal/Tax Information
    tax_id VARCHAR(100),                 -- EIN, Tax ID, CNPJ, RUC, etc.
    tax_jurisdiction VARCHAR(100),       -- "US-Delaware", "Paraguay", "Brazil"
    entity_type VARCHAR(50),             -- "LLC", "S-Corp", "SA", "Ltda", etc.

    -- Financial Settings
    base_currency VARCHAR(3) DEFAULT 'USD',
    fiscal_year_end VARCHAR(5) DEFAULT '12-31',  -- MM-DD format

    -- Address Information
    address TEXT,
    country_code VARCHAR(2),             -- ISO 3166-1 alpha-2 country code

    -- Status
    is_active BOOLEAN DEFAULT true,
    incorporation_date DATE,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),

    -- Constraints
    UNIQUE(tenant_id, code),
    UNIQUE(tenant_id, name)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_entities_tenant
    ON entities(tenant_id);

CREATE INDEX IF NOT EXISTS idx_entities_tenant_active
    ON entities(tenant_id, is_active);

CREATE INDEX IF NOT EXISTS idx_entities_code
    ON entities(code);

CREATE INDEX IF NOT EXISTS idx_entities_name
    ON entities(name);

-- Add table comment
COMMENT ON TABLE entities IS
    'Legal entities with separate books (Tier 2). Each entity represents a distinct legal/tax entity.';

COMMENT ON COLUMN entities.code IS
    'Short unique code for entity (e.g., DLLC, DPY). Used for reporting and UI display.';

COMMENT ON COLUMN entities.base_currency IS
    'Base currency for this entity. All reporting is done in this currency.';

-- ============================================================================
-- STEP 2: Create business_lines table (Tier 3 - Profit Centers)
-- ============================================================================

CREATE TABLE IF NOT EXISTS business_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,

    -- Business Line Identification
    code VARCHAR(20) NOT NULL,           -- Short code: "HOST", "VAL", "PROP"
    name VARCHAR(100) NOT NULL,          -- "Hosting Services", "Validator Operations"
    description TEXT,

    -- Classification
    is_default BOOLEAN DEFAULT false,    -- One default per entity (for progressive disclosure)
    color_hex VARCHAR(7),                -- UI color coding: "#3B82F6" (blue), "#10B981" (green)

    -- Status
    is_active BOOLEAN DEFAULT true,
    start_date DATE,                     -- When business line started operating
    end_date DATE,                       -- When business line was closed (if applicable)

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),

    -- Constraints
    UNIQUE(entity_id, code),
    UNIQUE(entity_id, name)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_business_lines_entity
    ON business_lines(entity_id);

CREATE INDEX IF NOT EXISTS idx_business_lines_entity_active
    ON business_lines(entity_id, is_active);

CREATE INDEX IF NOT EXISTS idx_business_lines_code
    ON business_lines(code);

-- Add table comment
COMMENT ON TABLE business_lines IS
    'Profit centers within entities for management reporting (Tier 3). Business lines share the parent entity''s books.';

COMMENT ON COLUMN business_lines.is_default IS
    'If true, this is the default business line for the entity. Used for progressive disclosure - hidden until user creates a second business line.';

COMMENT ON COLUMN business_lines.color_hex IS
    'Hex color code for UI visualization (charts, badges, etc.). Example: #3B82F6';

-- ============================================================================
-- STEP 3: Add entity_id and business_line_id to transactions table
-- ============================================================================

-- Add entity_id column (nullable for now to allow migration)
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS entity_id UUID REFERENCES entities(id);

-- Add business_line_id column (nullable - optional assignment)
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS business_line_id UUID REFERENCES business_lines(id);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_transactions_entity_id
    ON transactions(entity_id);

CREATE INDEX IF NOT EXISTS idx_transactions_business_line_id
    ON transactions(business_line_id);

-- Composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_transactions_entity_date
    ON transactions(entity_id, date);

CREATE INDEX IF NOT EXISTS idx_transactions_entity_business_line
    ON transactions(entity_id, business_line_id);

-- Add comments
COMMENT ON COLUMN transactions.entity_id IS
    'Foreign key to entities table. Replaces entity VARCHAR field. Will be required after migration.';

COMMENT ON COLUMN transactions.business_line_id IS
    'Optional profit center assignment for management reporting. NULL means not assigned to specific business line.';

-- ============================================================================
-- STEP 4: Add entity_id and business_line_id to invoices table
-- ============================================================================

-- Add entity_id column (nullable for now to allow migration)
ALTER TABLE invoices
ADD COLUMN IF NOT EXISTS entity_id UUID REFERENCES entities(id);

-- Add business_line_id column (nullable - optional assignment)
ALTER TABLE invoices
ADD COLUMN IF NOT EXISTS business_line_id UUID REFERENCES business_lines(id);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_invoices_entity_id
    ON invoices(entity_id);

CREATE INDEX IF NOT EXISTS idx_invoices_business_line_id
    ON invoices(business_line_id);

-- Add comments
COMMENT ON COLUMN invoices.entity_id IS
    'Foreign key to entities table. Links invoice to legal entity.';

COMMENT ON COLUMN invoices.business_line_id IS
    'Optional business line assignment for invoice categorization.';

-- ============================================================================
-- STEP 5: Update classification_patterns table
-- ============================================================================

-- Add entity_id and business_line_id to classification patterns
ALTER TABLE classification_patterns
ADD COLUMN IF NOT EXISTS entity_id UUID REFERENCES entities(id),
ADD COLUMN IF NOT EXISTS business_line_id UUID REFERENCES business_lines(id);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_classification_patterns_entity
    ON classification_patterns(entity_id);

CREATE INDEX IF NOT EXISTS idx_classification_patterns_business_line
    ON classification_patterns(business_line_id);

-- Add comments
COMMENT ON COLUMN classification_patterns.entity_id IS
    'Entity to assign when this pattern matches. NULL means pattern applies to all entities.';

COMMENT ON COLUMN classification_patterns.business_line_id IS
    'Business line to auto-assign when this pattern matches.';

-- ============================================================================
-- STEP 6: Create triggers for updated_at timestamps
-- ============================================================================

-- Trigger for entities table
CREATE TRIGGER update_entities_updated_at
    BEFORE UPDATE ON entities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for business_lines table
CREATE TRIGGER update_business_lines_updated_at
    BEFORE UPDATE ON business_lines
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- STEP 7: Create helper views for reporting
-- ============================================================================

-- View: Entity summary with transaction counts
CREATE OR REPLACE VIEW entity_summary AS
SELECT
    e.id,
    e.tenant_id,
    e.code,
    e.name,
    e.base_currency,
    e.is_active,
    COUNT(DISTINCT bl.id) as business_lines_count,
    COUNT(DISTINCT t.id) as transactions_count,
    SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) as total_income,
    SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END) as total_expenses
FROM entities e
LEFT JOIN business_lines bl ON e.id = bl.entity_id
LEFT JOIN transactions t ON e.id = t.entity_id
GROUP BY e.id, e.tenant_id, e.code, e.name, e.base_currency, e.is_active;

COMMENT ON VIEW entity_summary IS
    'Summary statistics for each entity including transaction and business line counts.';

-- View: Business line summary with transaction counts
CREATE OR REPLACE VIEW business_line_summary AS
SELECT
    bl.id,
    bl.entity_id,
    e.code as entity_code,
    e.name as entity_name,
    bl.code,
    bl.name,
    bl.is_active,
    bl.is_default,
    COUNT(t.id) as transactions_count,
    SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) as total_income,
    SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END) as total_expenses
FROM business_lines bl
JOIN entities e ON bl.entity_id = e.id
LEFT JOIN transactions t ON bl.id = t.business_line_id
GROUP BY bl.id, bl.entity_id, e.code, e.name, bl.code, bl.name, bl.is_active, bl.is_default;

COMMENT ON VIEW business_line_summary IS
    'Summary statistics for each business line including transaction counts.';

-- ============================================================================
-- STEP 8: Create validation constraints
-- ============================================================================

-- Ensure only one default business line per entity
CREATE UNIQUE INDEX IF NOT EXISTS idx_business_lines_one_default_per_entity
    ON business_lines(entity_id)
    WHERE is_default = true;

COMMENT ON INDEX idx_business_lines_one_default_per_entity IS
    'Ensures only one default business line per entity for progressive disclosure.';

-- ============================================================================
-- STEP 9: Migration verification queries (informational)
-- ============================================================================

-- These queries can be run after migration to verify success

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Entity and Business Line Migration Complete!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  - entities (Tier 2 - Legal Entities)';
    RAISE NOTICE '  - business_lines (Tier 3 - Profit Centers)';
    RAISE NOTICE '';
    RAISE NOTICE 'Columns added:';
    RAISE NOTICE '  - transactions.entity_id (FK to entities)';
    RAISE NOTICE '  - transactions.business_line_id (FK to business_lines)';
    RAISE NOTICE '  - invoices.entity_id (FK to entities)';
    RAISE NOTICE '  - invoices.business_line_id (FK to business_lines)';
    RAISE NOTICE '  - classification_patterns.entity_id';
    RAISE NOTICE '  - classification_patterns.business_line_id';
    RAISE NOTICE '';
    RAISE NOTICE 'Views created:';
    RAISE NOTICE '  - entity_summary (statistics per entity)';
    RAISE NOTICE '  - business_line_summary (statistics per business line)';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Run data migration script to populate entities and business_lines';
    RAISE NOTICE '  2. Update transactions.entity_id from entity VARCHAR';
    RAISE NOTICE '  3. Validate migration with validation queries';
    RAISE NOTICE '  4. Update application code to use new structure';
    RAISE NOTICE '========================================';
END $$;

-- ============================================================================
-- Validation Queries (run after migration complete)
-- ============================================================================

-- Uncomment these after data migration to validate:

-- Check entities were created
-- SELECT COUNT(*) as entity_count FROM entities;

-- Check business lines were created
-- SELECT COUNT(*) as business_line_count FROM business_lines;

-- Check transactions have entity_id populated
-- SELECT COUNT(*) as transactions_with_entity FROM transactions WHERE entity_id IS NOT NULL;
-- SELECT COUNT(*) as transactions_without_entity FROM transactions WHERE entity_id IS NULL;

-- Check each entity has at least one business line
-- SELECT e.id, e.name, COUNT(bl.id) as business_lines
-- FROM entities e
-- LEFT JOIN business_lines bl ON e.id = bl.entity_id
-- GROUP BY e.id, e.name
-- HAVING COUNT(bl.id) = 0;
-- -- Should return no rows

-- Check entity summary view
-- SELECT * FROM entity_summary;

-- Check business line summary view
-- SELECT * FROM business_line_summary;

-- ============================================================================
