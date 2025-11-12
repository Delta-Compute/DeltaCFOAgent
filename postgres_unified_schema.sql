-- ========================================
-- DeltaCFOAgent - Unified PostgreSQL Schema
-- ========================================
-- This script creates all tables needed for the complete DeltaCFOAgent system
-- Run this script on a fresh PostgreSQL database to initialize all components

-- ========================================
-- MAIN TRANSACTIONS SYSTEM (web_ui)
-- ========================================

-- Transactions table (core financial data)
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    description TEXT NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    type VARCHAR(50),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    entity VARCHAR(100) NOT NULL,
    origin VARCHAR(100),
    destination VARCHAR(100),
    confidence_score DECIMAL(5,2) DEFAULT 0.0,
    ai_generated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Learned patterns for AI improvement
CREATE TABLE IF NOT EXISTS learned_patterns (
    id SERIAL PRIMARY KEY,
    description_pattern TEXT NOT NULL,
    suggested_category VARCHAR(100),
    suggested_subcategory VARCHAR(100),
    suggested_entity VARCHAR(100),
    confidence_score DECIMAL(5,2) DEFAULT 0.0,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User interactions for reinforcement learning
CREATE TABLE IF NOT EXISTS user_interactions (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER REFERENCES transactions(id) ON DELETE CASCADE,
    original_category VARCHAR(100),
    user_category VARCHAR(100),
    original_entity VARCHAR(100),
    user_entity VARCHAR(100),
    feedback_type VARCHAR(50), -- 'correction', 'confirmation', 'manual_input'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Business knowledge base
CREATE TABLE IF NOT EXISTS business_entities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    entity_type VARCHAR(50), -- 'subsidiary', 'vendor', 'customer', 'internal'
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- CRYPTO PRICING SYSTEM
-- ========================================

-- Historic crypto prices for USD conversions
CREATE TABLE IF NOT EXISTS crypto_historic_prices (
    date DATE NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    price_usd DECIMAL(18,8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (date, symbol)
);

-- ========================================
-- CRYPTO INVOICE SYSTEM
-- ========================================

-- Clients for crypto invoicing
CREATE TABLE IF NOT EXISTS clients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    contact_email VARCHAR(255),
    billing_address TEXT,
    tax_id VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Invoice status enum values
-- 'draft', 'sent', 'partially_paid', 'paid', 'overdue', 'cancelled'

-- Main invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    client_id INTEGER REFERENCES clients(id) ON DELETE RESTRICT,
    status VARCHAR(20) DEFAULT 'draft',
    amount_usd DECIMAL(10,2) NOT NULL,
    crypto_currency VARCHAR(10) NOT NULL,
    crypto_amount DECIMAL(18,8) NOT NULL,
    crypto_network VARCHAR(20) NOT NULL,
    exchange_rate DECIMAL(18,8) NOT NULL,
    deposit_address TEXT NOT NULL,
    memo_tag TEXT,
    billing_period VARCHAR(100),
    description TEXT,
    line_items JSONB,
    due_date DATE NOT NULL,
    issue_date DATE DEFAULT CURRENT_DATE,
    paid_at TIMESTAMP,
    payment_tolerance DECIMAL(5,3) DEFAULT 0.005,
    pdf_path TEXT,
    qr_code_path TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Payment status enum values
-- 'pending', 'detected', 'confirmed', 'failed'

-- Payment transactions
CREATE TABLE IF NOT EXISTS payment_transactions (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
    transaction_hash VARCHAR(255) UNIQUE NOT NULL,
    amount_received DECIMAL(18,8) NOT NULL,
    currency VARCHAR(10) NOT NULL,
    network VARCHAR(20) NOT NULL,
    deposit_address TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    confirmations INTEGER DEFAULT 0,
    required_confirmations INTEGER DEFAULT 3,
    is_manual_verification BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR(100),
    mexc_transaction_id VARCHAR(255),
    raw_api_response JSONB,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- MEXC address caching
CREATE TABLE IF NOT EXISTS mexc_addresses (
    id SERIAL PRIMARY KEY,
    currency VARCHAR(10) NOT NULL,
    network VARCHAR(20) NOT NULL,
    address TEXT NOT NULL,
    memo_tag TEXT,
    is_primary BOOLEAN DEFAULT FALSE,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(currency, network, address)
);

-- Address usage tracking
CREATE TABLE IF NOT EXISTS address_usage (
    id SERIAL PRIMARY KEY,
    address TEXT NOT NULL,
    invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Payment polling logs
CREATE TABLE IF NOT EXISTS polling_logs (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL,
    deposits_found INTEGER DEFAULT 0,
    error_message TEXT,
    api_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Email notifications log
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER REFERENCES invoices(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL, -- 'invoice_created', 'payment_detected', 'payment_confirmed', 'overdue'
    recipient_email VARCHAR(255) NOT NULL,
    subject TEXT,
    message TEXT,
    sent_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'failed'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System configuration
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

-- Main transactions indexes
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_entity ON transactions(entity);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_transactions_amount ON transactions(amount);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);

-- Crypto pricing indexes
CREATE INDEX IF NOT EXISTS idx_crypto_historic_prices_symbol ON crypto_historic_prices(symbol);
CREATE INDEX IF NOT EXISTS idx_crypto_historic_prices_date ON crypto_historic_prices(date);

-- Invoice system indexes
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_client_id ON invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_invoices_due_date ON invoices(due_date);
CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at);
CREATE INDEX IF NOT EXISTS idx_invoices_crypto_currency ON invoices(crypto_currency);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_invoice_id ON payment_transactions(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_status ON payment_transactions(status);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_hash ON payment_transactions(transaction_hash);

CREATE INDEX IF NOT EXISTS idx_mexc_addresses_currency_network ON mexc_addresses(currency, network);
CREATE INDEX IF NOT EXISTS idx_polling_logs_invoice_id ON polling_logs(invoice_id);
CREATE INDEX IF NOT EXISTS idx_polling_logs_created_at ON polling_logs(created_at);

-- ========================================
-- SYSTEM CONFIGURATION DATA
-- ========================================
-- Note: Tenant-specific seed data has been moved to migrations/delta_tenant_seed_data.sql
-- This schema file only contains generic system configuration applicable to all tenants

-- System-wide configuration (applies to all tenants)
-- Default system configuration
INSERT INTO system_config (key, value, description) VALUES
    ('invoice_overdue_days', '7', 'Days after due date to mark invoice as overdue'),
    ('default_payment_tolerance', '0.005', 'Default payment tolerance percentage (0.5%)'),
    ('polling_interval_seconds', '30', 'Payment polling interval in seconds'),
    ('btc_confirmations_required', '3', 'Required confirmations for BTC payments'),
    ('usdt_confirmations_required', '20', 'Required confirmations for USDT payments'),
    ('tao_confirmations_required', '12', 'Required confirmations for TAO payments')
ON CONFLICT (key) DO NOTHING;

-- ========================================
-- DATABASE FUNCTIONS AND TRIGGERS
-- ========================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for automatic updated_at timestamps
CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_learned_patterns_updated_at BEFORE UPDATE ON learned_patterns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_business_entities_updated_at BEFORE UPDATE ON business_entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_crypto_historic_prices_updated_at BEFORE UPDATE ON crypto_historic_prices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clients_updated_at BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_invoices_updated_at BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- VIEWS FOR ANALYTICS
-- ========================================

-- Monthly transaction summary view
CREATE OR REPLACE VIEW monthly_transaction_summary AS
SELECT
    DATE_TRUNC('month', date) as month,
    entity,
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expenses,
    SUM(amount) as net_flow,
    COUNT(*) as transaction_count
FROM transactions
WHERE date >= CURRENT_DATE - INTERVAL '24 months'
GROUP BY month, entity
ORDER BY month DESC, entity;

-- Entity performance view
CREATE OR REPLACE VIEW entity_performance AS
SELECT
    entity,
    COUNT(*) as total_transactions,
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_income,
    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_expenses,
    SUM(amount) as net_position,
    AVG(amount) as avg_transaction_size,
    MIN(date) as first_transaction,
    MAX(date) as last_transaction
FROM transactions
GROUP BY entity
ORDER BY total_transactions DESC;

-- Invoice status summary view
CREATE OR REPLACE VIEW invoice_status_summary AS
SELECT
    status,
    COUNT(*) as count,
    SUM(amount_usd) as total_usd,
    AVG(amount_usd) as avg_usd,
    MIN(created_at) as oldest_invoice,
    MAX(created_at) as newest_invoice
FROM invoices
GROUP BY status
ORDER BY count DESC;

-- ========================================
-- MULTI-TENANT & CONFIGURATION SYSTEM
-- ========================================

-- Tenant configuration and branding
CREATE TABLE IF NOT EXISTS tenant_configuration (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) UNIQUE NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    company_tagline TEXT,
    company_description TEXT,
    logo_url TEXT,
    primary_color VARCHAR(7) DEFAULT '#3b82f6',
    secondary_color VARCHAR(7) DEFAULT '#10b981',
    industry VARCHAR(100),
    founded_date DATE,
    headquarters_location VARCHAR(255),
    website_url TEXT,
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    tax_id VARCHAR(100),
    fiscal_year_end VARCHAR(10) DEFAULT '12-31',
    default_currency VARCHAR(3) DEFAULT 'USD',
    timezone VARCHAR(50) DEFAULT 'UTC',
    is_active BOOLEAN DEFAULT TRUE,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Wallet addresses for crypto transaction classification
CREATE TABLE IF NOT EXISTS wallet_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    wallet_address TEXT NOT NULL,
    entity_name VARCHAR(255) NOT NULL,
    wallet_type VARCHAR(50) NOT NULL, -- 'internal', 'exchange', 'customer', 'vendor', 'partner'
    blockchain VARCHAR(50), -- 'ethereum', 'bitcoin', 'polygon', etc.
    purpose TEXT,
    confidence_score DECIMAL(5,2) DEFAULT 0.90,
    is_active BOOLEAN DEFAULT TRUE,
    balance DECIMAL(18,8),
    last_balance_check TIMESTAMP,
    notes TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, wallet_address)
);

-- Bank accounts for traditional banking integration
CREATE TABLE IF NOT EXISTS bank_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    institution_name VARCHAR(255) NOT NULL,
    account_number VARCHAR(100), -- Last 4 digits or masked
    account_number_encrypted TEXT, -- Full encrypted account number
    routing_number VARCHAR(50),
    account_type VARCHAR(50), -- 'checking', 'savings', 'credit', 'investment', 'loan'
    currency VARCHAR(3) DEFAULT 'USD',
    current_balance DECIMAL(15,2),
    available_balance DECIMAL(15,2),
    last_sync_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active', -- 'active', 'inactive', 'closed', 'pending'
    is_primary BOOLEAN DEFAULT FALSE,
    plaid_item_id TEXT, -- For Plaid integration
    plaid_access_token TEXT, -- Encrypted Plaid token
    institution_logo_url TEXT,
    account_color VARCHAR(7),
    notes TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, institution_name, account_number)
);

-- AI-generated homepage content storage
CREATE TABLE IF NOT EXISTS homepage_content (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) UNIQUE NOT NULL,
    company_name VARCHAR(255),
    tagline TEXT,
    description TEXT,
    kpis_json JSONB, -- Stores KPI data: transactions, revenue, expenses, etc.
    entities_json JSONB, -- Stores business entities/portfolio companies
    metrics_json JSONB, -- Stores calculated metrics
    ai_insights TEXT, -- AI-generated insights and highlights
    generation_prompt TEXT, -- Prompt used to generate content
    generated_by VARCHAR(50) DEFAULT 'claude-ai',
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_by VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- ========================================
-- INDEXES FOR NEW TABLES
-- ========================================

CREATE INDEX IF NOT EXISTS idx_wallet_addresses_tenant ON wallet_addresses(tenant_id);
CREATE INDEX IF NOT EXISTS idx_wallet_addresses_active ON wallet_addresses(tenant_id, is_active);
CREATE INDEX IF NOT EXISTS idx_wallet_addresses_type ON wallet_addresses(wallet_type);

CREATE INDEX IF NOT EXISTS idx_bank_accounts_tenant ON bank_accounts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_bank_accounts_status ON bank_accounts(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_bank_accounts_type ON bank_accounts(account_type);

CREATE INDEX IF NOT EXISTS idx_tenant_configuration_tenant ON tenant_configuration(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_configuration_active ON tenant_configuration(is_active);

CREATE INDEX IF NOT EXISTS idx_homepage_content_tenant ON homepage_content(tenant_id);

-- ========================================
-- TRIGGERS FOR NEW TABLES
-- ========================================

CREATE TRIGGER update_tenant_configuration_updated_at BEFORE UPDATE ON tenant_configuration
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_wallet_addresses_updated_at BEFORE UPDATE ON wallet_addresses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bank_accounts_updated_at BEFORE UPDATE ON bank_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_homepage_content_updated_at BEFORE UPDATE ON homepage_content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- TENANT-SPECIFIC SEED DATA
-- ========================================
-- NOTE: Tenant-specific seed data has been removed from this schema file.
-- This ensures new tenant databases start with a clean slate.
--
-- For existing tenant 'delta', run the following migration file separately:
--   migrations/delta_tenant_seed_data.sql
--
-- For new tenants, use the onboarding flow at /api/onboarding to set up:
--   - Company/tenant configuration
--   - Business entities
--   - Wallet addresses
--   - Bank accounts
--   - Initial classification patterns

-- ========================================
-- COMPLETION MESSAGE
-- ========================================

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'DeltaCFOAgent PostgreSQL Schema Setup Complete!';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '- Main System: transactions, learned_patterns, user_interactions, business_entities';
    RAISE NOTICE '- Crypto Pricing: crypto_historic_prices';
    RAISE NOTICE '- Invoice System: clients, invoices, payment_transactions, mexc_addresses, etc.';
    RAISE NOTICE '- Multi-Tenant: tenant_configuration, wallet_addresses, bank_accounts, homepage_content';
    RAISE NOTICE '- Analytics Views: monthly_transaction_summary, entity_performance, invoice_status_summary';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  IMPORTANT: No tenant-specific seed data inserted.';
    RAISE NOTICE '   - For Delta tenant: Run migrations/delta_tenant_seed_data.sql';
    RAISE NOTICE '   - For new tenants: Use /api/onboarding flow';
    RAISE NOTICE '';
    RAISE NOTICE 'Schema is ready for multi-tenant production use!';
    RAISE NOTICE '==============================================';
END $$;