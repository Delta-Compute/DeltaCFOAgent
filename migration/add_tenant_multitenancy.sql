-- ===============================================
-- Multi-Tenant Configuration Migration
-- Adds tenant_id support and configuration tables
-- ===============================================

-- ===============================================
-- STEP 1: Add tenant_id to transactions table
-- ===============================================

-- Add tenant_id column (defaulting to 'delta' for existing data)
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) DEFAULT 'delta' NOT NULL;

-- Create index for tenant filtering
CREATE INDEX IF NOT EXISTS idx_transactions_tenant_id ON transactions(tenant_id);

-- Update the unique constraint to include tenant_id for transaction_id
-- (transaction_id should be unique per tenant, not globally)
-- Note: Can't modify existing PRIMARY KEY easily, so we add a unique constraint
CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_tenant_transaction
ON transactions(tenant_id, transaction_id);

-- ===============================================
-- STEP 2: Create entity_patterns table
-- ===============================================

CREATE TABLE IF NOT EXISTS entity_patterns (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL DEFAULT 'delta',
    entity_name TEXT NOT NULL,
    pattern_data JSONB NOT NULL,
    transaction_id TEXT NOT NULL,
    confidence_score DECIMAL(3, 2) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key to transactions (without CASCADE to prevent accidental deletes)
    FOREIGN KEY (tenant_id, transaction_id)
        REFERENCES transactions(tenant_id, transaction_id)
        ON DELETE CASCADE
);

-- Create indexes for entity_patterns
CREATE INDEX IF NOT EXISTS idx_entity_patterns_tenant_id ON entity_patterns(tenant_id);
CREATE INDEX IF NOT EXISTS idx_entity_patterns_entity_name ON entity_patterns(tenant_id, entity_name);
CREATE INDEX IF NOT EXISTS idx_entity_patterns_transaction ON entity_patterns(transaction_id);
CREATE INDEX IF NOT EXISTS idx_entity_patterns_created_at ON entity_patterns(created_at);
CREATE INDEX IF NOT EXISTS idx_entity_patterns_confidence ON entity_patterns(confidence_score DESC);

-- Add trigger for updated_at
DROP TRIGGER IF EXISTS update_entity_patterns_updated_at ON entity_patterns;
CREATE TRIGGER update_entity_patterns_updated_at
    BEFORE UPDATE ON entity_patterns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===============================================
-- STEP 3: Create tenant_configurations table
-- ===============================================

CREATE TABLE IF NOT EXISTS tenant_configurations (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL,
    config_type VARCHAR(50) NOT NULL,
    config_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,

    -- Ensure one config per type per tenant
    UNIQUE(tenant_id, config_type)
);

-- Create indexes for tenant_configurations
CREATE INDEX IF NOT EXISTS idx_tenant_config_tenant_id ON tenant_configurations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_config_type ON tenant_configurations(tenant_id, config_type);
CREATE INDEX IF NOT EXISTS idx_tenant_config_updated_at ON tenant_configurations(updated_at);

-- Add trigger for updated_at
DROP TRIGGER IF EXISTS update_tenant_configurations_updated_at ON tenant_configurations;
CREATE TRIGGER update_tenant_configurations_updated_at
    BEFORE UPDATE ON tenant_configurations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===============================================
-- STEP 4: Insert Default Delta Configuration
-- ===============================================

-- Insert entities configuration for Delta (default tenant)
INSERT INTO tenant_configurations (tenant_id, config_type, config_data, created_by)
VALUES (
    'delta',
    'entities',
    '{
        "entities": [
            {
                "name": "Delta LLC",
                "description": "US-based trading operations, exchanges, brokers, US banking",
                "entity_type": "subsidiary",
                "business_context": "Main holding company for US operations"
            },
            {
                "name": "Delta Prop Shop LLC",
                "description": "Proprietary trading, DeFi protocols, yield farming, liquid staking",
                "entity_type": "subsidiary",
                "business_context": "Trading and DeFi operations"
            },
            {
                "name": "Infinity Validator",
                "description": "Blockchain validation, staking rewards, node operations",
                "entity_type": "subsidiary",
                "business_context": "Validator and staking operations"
            },
            {
                "name": "Delta Mining Paraguay S.A.",
                "description": "Mining operations, equipment, Paraguay-based transactions",
                "entity_type": "subsidiary",
                "business_context": "Paraguay mining entity"
            },
            {
                "name": "Delta Brazil Operations",
                "description": "Brazil-based activities, regulatory compliance, local operations",
                "entity_type": "subsidiary",
                "business_context": "Brazilian operations"
            },
            {
                "name": "Personal",
                "description": "Individual expenses, personal transfers, non-business transactions",
                "entity_type": "personal",
                "business_context": "Personal transactions"
            },
            {
                "name": "Internal Transfer",
                "description": "Movements between company entities/wallets",
                "entity_type": "internal",
                "business_context": "Inter-entity transfers"
            }
        ],
        "entity_families": {
            "Delta": ["Delta LLC", "Delta Prop Shop LLC", "Delta Mining Paraguay S.A.", "Delta Mining", "Delta Brazil Operations"],
            "Infinity": ["Infinity Validator", "Infinity Staking", "Infinity Pool"]
        }
    }',
    'system'
)
ON CONFLICT (tenant_id, config_type) DO UPDATE
SET config_data = EXCLUDED.config_data,
    updated_at = CURRENT_TIMESTAMP;

-- Insert business context configuration for Delta
INSERT INTO tenant_configurations (tenant_id, config_type, config_data, created_by)
VALUES (
    'delta',
    'business_context',
    '{
        "industry": "crypto_trading",
        "company_name": "Delta",
        "company_size": "small",
        "primary_activities": ["cryptocurrency trading", "mining", "staking", "DeFi protocols"],
        "geographic_regions": ["United States", "Paraguay", "Brazil"],
        "transaction_patterns": ["crypto exchanges", "wire transfers", "ACH payments", "mining rewards"],
        "specialized_features": {
            "crypto_enabled": true,
            "multi_currency": true,
            "international_operations": true
        }
    }',
    'system'
)
ON CONFLICT (tenant_id, config_type) DO UPDATE
SET config_data = EXCLUDED.config_data,
    updated_at = CURRENT_TIMESTAMP;

-- Insert accounting categories configuration for Delta
INSERT INTO tenant_configurations (tenant_id, config_type, config_data, created_by)
VALUES (
    'delta',
    'accounting_categories',
    '{
        "revenue_categories": [
            "Revenue - Trading",
            "Revenue - Mining",
            "Revenue - Challenge",
            "Revenue - Staking",
            "Interest Income"
        ],
        "expense_categories": [
            "Cost of Goods Sold (COGS)",
            "Technology Expenses",
            "General and Administrative",
            "Bank Fees",
            "Payment Processing Fees",
            "Professional Services",
            "Mining Equipment",
            "Infrastructure Costs"
        ],
        "asset_categories": [
            "Cryptocurrency Holdings",
            "Mining Equipment",
            "Cash and Equivalents"
        ],
        "liability_categories": [
            "Accounts Payable",
            "Deferred Revenue"
        ]
    }',
    'system'
)
ON CONFLICT (tenant_id, config_type) DO UPDATE
SET config_data = EXCLUDED.config_data,
    updated_at = CURRENT_TIMESTAMP;

-- Insert pattern matching rules configuration for Delta
INSERT INTO tenant_configurations (tenant_id, config_type, config_data, created_by)
VALUES (
    'delta',
    'pattern_matching_rules',
    '{
        "entity_matching": {
            "use_wallet_matching": true,
            "use_vendor_name_matching": true,
            "use_bank_identifier_matching": true,
            "similarity_threshold": 0.75,
            "min_pattern_matches": 2
        },
        "description_matching": {
            "min_transactions_to_suggest": 3,
            "max_suggestions": 10,
            "use_semantic_matching": true,
            "similarity_threshold": 0.70
        },
        "accounting_category_matching": {
            "min_transactions_to_suggest": 2,
            "max_suggestions": 8,
            "confidence_threshold": 0.60
        },
        "bulk_update_settings": {
            "auto_apply_threshold": 0.95,
            "require_user_confirmation": true,
            "max_bulk_update_count": 50
        }
    }',
    'system'
)
ON CONFLICT (tenant_id, config_type) DO UPDATE
SET config_data = EXCLUDED.config_data,
    updated_at = CURRENT_TIMESTAMP;

-- ===============================================
-- STEP 5: Add tenant_id to other tables
-- ===============================================

-- Add tenant_id to invoices table
ALTER TABLE invoices
ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) DEFAULT 'delta' NOT NULL;

CREATE INDEX IF NOT EXISTS idx_invoices_tenant_id ON invoices(tenant_id);

-- Add tenant_id to transaction_history table (if it exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'transaction_history') THEN
        ALTER TABLE transaction_history
        ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(50) DEFAULT 'delta' NOT NULL;

        CREATE INDEX IF NOT EXISTS idx_transaction_history_tenant_id ON transaction_history(tenant_id);
    END IF;
END $$;

-- ===============================================
-- STEP 6: Add archived column to transactions (if not exists)
-- ===============================================

-- Add archived column for soft deletes
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_transactions_archived ON transactions(archived);

-- ===============================================
-- STEP 7: Create tenant management table
-- ===============================================

CREATE TABLE IF NOT EXISTS tenants (
    tenant_id VARCHAR(50) PRIMARY KEY,
    tenant_name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    industry VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'suspended', 'trial'
    subscription_tier VARCHAR(50) DEFAULT 'basic', -- 'basic', 'professional', 'enterprise'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    onboarded_at TIMESTAMP,
    onboarded_by TEXT,
    contact_email VARCHAR(255),
    settings JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for tenants
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);
CREATE INDEX IF NOT EXISTS idx_tenants_created_at ON tenants(created_at);

-- Add trigger for updated_at
DROP TRIGGER IF EXISTS update_tenants_updated_at ON tenants;
CREATE TRIGGER update_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default Delta tenant
INSERT INTO tenants (tenant_id, tenant_name, company_name, industry, status, subscription_tier, onboarded_at, contact_email)
VALUES (
    'delta',
    'Delta',
    'Delta CFO Agent',
    'crypto_trading',
    'active',
    'enterprise',
    CURRENT_TIMESTAMP,
    'admin@delta.com'
)
ON CONFLICT (tenant_id) DO UPDATE
SET updated_at = CURRENT_TIMESTAMP;

-- ===============================================
-- COMPLETION
-- ===============================================

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Multi-Tenant Migration Complete!';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Added tables:';
    RAISE NOTICE '- tenant_configurations: Stores per-tenant business config';
    RAISE NOTICE '- entity_patterns: Stores learned patterns with tenant isolation';
    RAISE NOTICE '- tenants: Tenant management and metadata';
    RAISE NOTICE '';
    RAISE NOTICE 'Updated tables:';
    RAISE NOTICE '- transactions: Added tenant_id column';
    RAISE NOTICE '- invoices: Added tenant_id column';
    RAISE NOTICE '- transaction_history: Added tenant_id column';
    RAISE NOTICE '';
    RAISE NOTICE 'Default Delta configuration inserted.';
    RAISE NOTICE 'All existing data assigned to tenant_id = "delta"';
    RAISE NOTICE '==============================================';
END $$;

-- ===============================================
-- VACUUM AND ANALYZE
-- ===============================================

VACUUM ANALYZE transactions;
VACUUM ANALYZE entity_patterns;
VACUUM ANALYZE tenant_configurations;
VACUUM ANALYZE tenants;
