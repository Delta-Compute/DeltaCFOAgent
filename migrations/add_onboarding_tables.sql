-- Migration: Add Enhanced Onboarding Tables
-- Date: 2025-10-31
-- Description: Tables for advanced onboarding features (custom categories and onboarding status)

-- Custom accounting categories per tenant
CREATE TABLE IF NOT EXISTS custom_categories (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL,
    category_type VARCHAR(50) NOT NULL, -- 'revenue', 'expense', 'asset', 'liability', 'equity'
    category_name VARCHAR(255) NOT NULL,
    parent_category VARCHAR(255),
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenant_configuration(tenant_id) ON DELETE CASCADE
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_custom_categories_tenant ON custom_categories(tenant_id);
CREATE INDEX IF NOT EXISTS idx_custom_categories_type ON custom_categories(category_type);
CREATE INDEX IF NOT EXISTS idx_custom_categories_active ON custom_categories(is_active);

-- Tenant onboarding progress tracking
CREATE TABLE IF NOT EXISTS tenant_onboarding_status (
    tenant_id VARCHAR(100) PRIMARY KEY,
    basic_info_complete BOOLEAN DEFAULT false,
    entities_complete BOOLEAN DEFAULT false,
    coa_complete BOOLEAN DEFAULT false,
    accounts_complete BOOLEAN DEFAULT false,
    documents_complete BOOLEAN DEFAULT false,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenant_configuration(tenant_id) ON DELETE CASCADE
);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_onboarding_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_custom_categories_updated_at
    BEFORE UPDATE ON custom_categories
    FOR EACH ROW
    EXECUTE FUNCTION update_onboarding_updated_at();

CREATE TRIGGER update_tenant_onboarding_status_updated_at
    BEFORE UPDATE ON tenant_onboarding_status
    FOR EACH ROW
    EXECUTE FUNCTION update_onboarding_updated_at();

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Onboarding tables created successfully!';
    RAISE NOTICE '- custom_categories: For tenant-specific chart of accounts';
    RAISE NOTICE '- tenant_onboarding_status: For tracking onboarding progress';
END $$;
