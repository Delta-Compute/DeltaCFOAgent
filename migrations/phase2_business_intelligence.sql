-- ========================================
-- Phase 2: Business Intelligence Migration
-- ========================================
-- This migration adds business intelligence capabilities to DeltaCFOAgent
-- Run this AFTER phase1_chatbot_enhancement.sql
--
-- Changes:
-- 1. Creates investor tracking tables
-- 2. Creates vendor management tables
-- 3. Creates dynamic business rules system
-- 4. Adds indexes for performance
-- 5. Enables chatbot to manage business relationships

BEGIN;

-- ========================================
-- STEP 1: Create Investor Tracking Tables
-- ========================================

-- Investor relationships for funding tracking
CREATE TABLE IF NOT EXISTS investor_relationships (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    investor_name VARCHAR(255) NOT NULL,
    investor_type VARCHAR(50),  -- 'VC', 'angel', 'institutional', 'individual'
    country VARCHAR(100),
    contact_email VARCHAR(255),
    investment_focus TEXT,
    total_invested DECIMAL(15,2),
    first_investment_date DATE,
    last_investment_date DATE,
    status VARCHAR(20),  -- 'active', 'inactive', 'prospect'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Investment records
CREATE TABLE IF NOT EXISTS investments (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    investor_id INTEGER NOT NULL REFERENCES investor_relationships(id) ON DELETE CASCADE,
    entity_id INTEGER NOT NULL REFERENCES business_entities(id) ON DELETE CASCADE,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    investment_date DATE NOT NULL,
    terms TEXT,
    status VARCHAR(20),  -- 'proposed', 'active', 'completed', 'exited'
    transaction_id INTEGER REFERENCES transactions(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- STEP 2: Create Vendor Management Tables
-- ========================================

-- Vendor profiles for vendor intelligence
CREATE TABLE IF NOT EXISTS vendor_profiles (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    vendor_name VARCHAR(255) NOT NULL,
    vendor_type VARCHAR(50),  -- 'service_provider', 'supplier', 'contractor'
    country VARCHAR(100),
    tax_id VARCHAR(50),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(20),
    payment_terms VARCHAR(50),  -- 'net30', 'net60', 'immediate'
    quality_score DECIMAL(3,2),
    reliability_score DECIMAL(3,2),
    total_spent DECIMAL(15,2),
    transaction_count INTEGER DEFAULT 0,
    last_transaction_date DATE,
    notes TEXT,
    is_preferred BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vendor interactions history
CREATE TABLE IF NOT EXISTS vendor_interactions (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    vendor_id INTEGER NOT NULL REFERENCES vendor_profiles(id) ON DELETE CASCADE,
    transaction_id INTEGER REFERENCES transactions(id),
    interaction_type VARCHAR(50),  -- 'payment', 'inquiry', 'complaint', 'praise'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- STEP 3: Create Business Rules System
-- ========================================

-- Business rules for dynamic categorization
CREATE TABLE IF NOT EXISTS business_rules (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50),  -- 'classification', 'alert', 'validation'
    description TEXT,
    priority INTEGER DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    UNIQUE(tenant_id, rule_name)
);

-- Rule conditions for business logic
CREATE TABLE IF NOT EXISTS rule_conditions (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER NOT NULL REFERENCES business_rules(id) ON DELETE CASCADE,
    field_name VARCHAR(100),  -- 'description', 'amount', 'date', etc.
    operator VARCHAR(20),  -- 'contains', 'equals', 'greater_than', 'regex_match'
    condition_value TEXT,
    order_num INTEGER DEFAULT 0
);

-- Rule actions for execution
CREATE TABLE IF NOT EXISTS rule_actions (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER NOT NULL REFERENCES business_rules(id) ON DELETE CASCADE,
    action_type VARCHAR(50),  -- 'classify', 'alert', 'escalate'
    target_category VARCHAR(100),
    target_subcategory VARCHAR(100),
    target_entity VARCHAR(100),
    confidence_score DECIMAL(5,2)
);

-- ========================================
-- STEP 4: Create Indexes
-- ========================================

-- Investor tracking indexes
CREATE INDEX IF NOT EXISTS idx_investor_relationships_tenant_id ON investor_relationships(tenant_id);
CREATE INDEX IF NOT EXISTS idx_investor_relationships_investor_type ON investor_relationships(investor_type);
CREATE INDEX IF NOT EXISTS idx_investor_relationships_status ON investor_relationships(status);

CREATE INDEX IF NOT EXISTS idx_investments_investor_id ON investments(investor_id);
CREATE INDEX IF NOT EXISTS idx_investments_entity_id ON investments(entity_id);
CREATE INDEX IF NOT EXISTS idx_investments_tenant_id ON investments(tenant_id);
CREATE INDEX IF NOT EXISTS idx_investments_date ON investments(investment_date);

-- Vendor management indexes
CREATE INDEX IF NOT EXISTS idx_vendor_profiles_tenant_id ON vendor_profiles(tenant_id);
CREATE INDEX IF NOT EXISTS idx_vendor_profiles_vendor_type ON vendor_profiles(vendor_type);
CREATE INDEX IF NOT EXISTS idx_vendor_profiles_is_preferred ON vendor_profiles(is_preferred);

CREATE INDEX IF NOT EXISTS idx_vendor_interactions_vendor_id ON vendor_interactions(vendor_id);
CREATE INDEX IF NOT EXISTS idx_vendor_interactions_tenant_id ON vendor_interactions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_vendor_interactions_transaction_id ON vendor_interactions(transaction_id);

-- Business rules indexes
CREATE INDEX IF NOT EXISTS idx_business_rules_tenant_id ON business_rules(tenant_id);
CREATE INDEX IF NOT EXISTS idx_business_rules_is_active ON business_rules(is_active);
CREATE INDEX IF NOT EXISTS idx_business_rules_rule_type ON business_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_business_rules_priority ON business_rules(priority);

CREATE INDEX IF NOT EXISTS idx_rule_conditions_rule_id ON rule_conditions(rule_id);
CREATE INDEX IF NOT EXISTS idx_rule_actions_rule_id ON rule_actions(rule_id);

-- ========================================
-- STEP 5: Create Triggers
-- ========================================

-- Trigger for investor_relationships updated_at
DROP TRIGGER IF EXISTS update_investor_relationships_updated_at ON investor_relationships;
CREATE TRIGGER update_investor_relationships_updated_at
    BEFORE UPDATE ON investor_relationships
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for vendor_profiles updated_at
DROP TRIGGER IF EXISTS update_vendor_profiles_updated_at ON vendor_profiles;
CREATE TRIGGER update_vendor_profiles_updated_at
    BEFORE UPDATE ON vendor_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for business_rules updated_at
DROP TRIGGER IF EXISTS update_business_rules_updated_at ON business_rules;
CREATE TRIGGER update_business_rules_updated_at
    BEFORE UPDATE ON business_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMIT;

-- ========================================
-- Completion message
-- ========================================

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Phase 2 Migration Complete!';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Changes applied:';
    RAISE NOTICE '- Created investor tracking tables (2 tables)';
    RAISE NOTICE '- Created vendor management tables (2 tables)';
    RAISE NOTICE '- Created business rules system (3 tables)';
    RAISE NOTICE '- Added 15+ performance indexes';
    RAISE NOTICE '- Added 3 automatic triggers';
    RAISE NOTICE '';
    RAISE NOTICE 'New capabilities:';
    RAISE NOTICE '  - Track investors and funding sources';
    RAISE NOTICE '  - Manage vendor relationships and performance';
    RAISE NOTICE '  - Define dynamic business rules in database';
    RAISE NOTICE '  - Chatbot can now manage business relationships';
    RAISE NOTICE '';
    RAISE NOTICE 'Next: Run Phase 3 migration for chatbot backend';
    RAISE NOTICE '==============================================';
END $$;
