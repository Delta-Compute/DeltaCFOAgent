-- ========================================
-- DELTA TENANT SEED DATA
-- ========================================
-- This file contains seed data specific to the 'delta' tenant.
-- Run this ONLY for the Delta tenant - do NOT include in generic schema setup.
--
-- Usage:
--   psql -h <host> -U <user> -d <database> -f migrations/delta_tenant_seed_data.sql
--
-- Or via DatabaseManager:
--   python migrations/apply_delta_seed_data.py
--
-- IMPORTANT: This file should NEVER be run for new tenant onboarding.
-- New tenants should use the /api/onboarding flow instead.
-- ========================================

-- Ensure we're setting up data for the correct tenant
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Loading Delta Tenant Seed Data';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'This will insert Delta-specific:';
    RAISE NOTICE '  - Business entities';
    RAISE NOTICE '  - Crypto invoice clients';
    RAISE NOTICE '  - Tenant configuration';
    RAISE NOTICE '  - Wallet addresses';
    RAISE NOTICE '  - Bank accounts';
    RAISE NOTICE '';
END $$;

-- ========================================
-- DELTA BUSINESS ENTITIES
-- ========================================

INSERT INTO business_entities (name, description, entity_type) VALUES
    ('Delta LLC', 'Main business entity', 'subsidiary'),
    ('Delta Prop Shop LLC', 'Trading operations', 'subsidiary'),
    ('Infinity Validator', 'Validator operations', 'subsidiary'),
    ('MMIW LLC', 'Investment management', 'subsidiary'),
    ('DM Mining LLC', 'Mining operations', 'subsidiary'),
    ('Delta Mining Paraguay S.A.', 'Paraguay mining operations', 'subsidiary')
ON CONFLICT (name) DO NOTHING;

-- ========================================
-- DELTA CRYPTO INVOICE CLIENTS
-- ========================================

INSERT INTO clients (name, contact_email, billing_address, notes) VALUES
    ('Alps Blockchain', 'billing@alpsblockchain.com', 'Paraguay Mining Facility', 'Primary mining client'),
    ('Exos Capital', 'accounting@exoscapital.com', 'Paraguay Mining Facility', 'Investment fund client'),
    ('GM Data Centers', 'billing@gmdatacenters.com', 'Paraguay Mining Facility', 'Colocation services'),
    ('Other', null, null, 'Miscellaneous clients')
ON CONFLICT DO NOTHING;

-- ========================================
-- DELTA TENANT CONFIGURATION
-- ========================================

INSERT INTO tenant_configuration (
    tenant_id, company_name, company_tagline, company_description,
    industry, default_currency, timezone
) VALUES (
    'delta',
    'Delta Capital Holdings',
    'Diversified Technology & Innovation Portfolio',
    'A strategic holding company focused on emerging technologies, artificial intelligence, and digital transformation solutions. We build, acquire, and scale innovative businesses that shape the future of technology and commerce.',
    'Technology & Investment',
    'USD',
    'America/New_York'
) ON CONFLICT (tenant_id) DO UPDATE SET
    company_name = EXCLUDED.company_name,
    company_tagline = EXCLUDED.company_tagline,
    company_description = EXCLUDED.company_description,
    updated_at = CURRENT_TIMESTAMP;

-- ========================================
-- DELTA WALLET ADDRESSES
-- ========================================
-- WARNING: These are production wallet addresses for Delta tenant only
-- DO NOT expose these to other tenants

INSERT INTO wallet_addresses (
    tenant_id, wallet_address, entity_name, wallet_type, blockchain, purpose, created_by
) VALUES
    ('delta', '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb', 'Coinbase Exchange', 'exchange', 'ethereum', 'Primary CEX wallet for trading', 'system'),
    ('delta', '0x8f5832e8b0b0c8b8c9f0e5e3a2b1c0d9e8f7a6b5', 'Delta Internal Wallet', 'internal', 'ethereum', 'Company owned wallet for operations', 'system'),
    ('delta', 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', 'Cold Storage BTC', 'internal', 'bitcoin', 'Long-term BTC holdings', 'system')
ON CONFLICT (tenant_id, wallet_address) DO NOTHING;

-- ========================================
-- DELTA BANK ACCOUNTS
-- ========================================
-- NOTE: Account numbers are masked for security
-- Full encrypted account numbers should be added via secure admin interface

INSERT INTO bank_accounts (
    tenant_id, account_name, institution_name, account_number,
    account_type, status, is_primary, created_by
) VALUES
    ('delta', 'Operating Account', 'Chase Bank', '****1234', 'checking', 'active', TRUE, 'system'),
    ('delta', 'Savings Reserve', 'Chase Bank', '****5678', 'savings', 'active', FALSE, 'system'),
    ('delta', 'Business Credit', 'American Express', '****9012', 'credit', 'active', FALSE, 'system')
ON CONFLICT (tenant_id, institution_name, account_number) DO NOTHING;

-- ========================================
-- COMPLETION MESSAGE
-- ========================================

DO $$
DECLARE
    entity_count INTEGER;
    client_count INTEGER;
    wallet_count INTEGER;
    bank_count INTEGER;
BEGIN
    -- Count inserted records
    SELECT COUNT(*) INTO entity_count FROM business_entities WHERE name LIKE '%Delta%' OR name LIKE '%MMIW%' OR name LIKE '%Infinity%';
    SELECT COUNT(*) INTO client_count FROM clients WHERE name IN ('Alps Blockchain', 'Exos Capital', 'GM Data Centers', 'Other');
    SELECT COUNT(*) INTO wallet_count FROM wallet_addresses WHERE tenant_id = 'delta';
    SELECT COUNT(*) INTO bank_count FROM bank_accounts WHERE tenant_id = 'delta';

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Delta Tenant Seed Data Loaded Successfully!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Records inserted:';
    RAISE NOTICE '  - Business Entities: %', entity_count;
    RAISE NOTICE '  - Crypto Invoice Clients: %', client_count;
    RAISE NOTICE '  - Wallet Addresses: %', wallet_count;
    RAISE NOTICE '  - Bank Accounts: %', bank_count;
    RAISE NOTICE '  - Tenant Configuration: 1';
    RAISE NOTICE '';
    RAISE NOTICE '✅ Delta tenant is ready for use!';
    RAISE NOTICE '========================================';
END $$;
