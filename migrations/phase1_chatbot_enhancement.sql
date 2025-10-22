-- ========================================
-- Phase 1: Chatbot Enhancement Migration
-- ========================================
-- This migration adds chatbot functionality to existing DeltaCFOAgent databases
-- Run this on an existing database to add Phase 1 chatbot features
--
-- Changes:
-- 1. Adds tenant_id to core tables
-- 2. Creates classification_patterns table (fixes main.py:93 bug)
-- 3. Creates session and chatbot tables
-- 4. Creates audit and feedback tables
-- 5. Adds indexes for performance
-- 6. Migrates business rules from business_knowledge.md

BEGIN;

-- ========================================
-- STEP 1: Add tenant_id to existing tables
-- ========================================

-- Add tenant_id to transactions
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'transactions' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE transactions ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta';
        CREATE INDEX idx_transactions_tenant_id ON transactions(tenant_id);
        CREATE INDEX idx_transactions_tenant_date ON transactions(tenant_id, date);
        RAISE NOTICE 'Added tenant_id to transactions table';
    ELSE
        RAISE NOTICE 'tenant_id already exists in transactions table';
    END IF;
END $$;

-- Add tenant_id to learned_patterns
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'learned_patterns' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE learned_patterns ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta';
        CREATE INDEX idx_learned_patterns_tenant_id ON learned_patterns(tenant_id);
        RAISE NOTICE 'Added tenant_id to learned_patterns table';
    ELSE
        RAISE NOTICE 'tenant_id already exists in learned_patterns table';
    END IF;
END $$;

-- Add tenant_id and new fields to user_interactions
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'user_interactions' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE user_interactions
            ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
            ADD COLUMN user_id VARCHAR(100),
            ADD COLUMN session_id VARCHAR(100),
            ADD COLUMN interaction_type VARCHAR(50),
            ADD COLUMN outcome VARCHAR(20),
            ADD COLUMN confidence_adjustment DECIMAL(3,2);

        CREATE INDEX idx_user_interactions_user_id ON user_interactions(user_id);
        CREATE INDEX idx_user_interactions_session_id ON user_interactions(session_id);
        CREATE INDEX idx_user_interactions_tenant_id ON user_interactions(tenant_id);
        RAISE NOTICE 'Added tenant_id and new fields to user_interactions table';
    ELSE
        RAISE NOTICE 'tenant_id already exists in user_interactions table';
    END IF;
END $$;

-- Add tenant_id to business_entities and update unique constraint
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'business_entities' AND column_name = 'tenant_id'
    ) THEN
        -- Add tenant_id column
        ALTER TABLE business_entities ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta';

        -- Drop old unique constraint on name
        ALTER TABLE business_entities DROP CONSTRAINT IF EXISTS business_entities_name_key;

        -- Add new unique constraint on tenant_id + name
        ALTER TABLE business_entities ADD CONSTRAINT business_entities_tenant_name_key UNIQUE (tenant_id, name);

        CREATE INDEX idx_business_entities_tenant_id ON business_entities(tenant_id);
        RAISE NOTICE 'Added tenant_id to business_entities table';
    ELSE
        RAISE NOTICE 'tenant_id already exists in business_entities table';
    END IF;
END $$;

-- ========================================
-- STEP 2: Create new tables
-- ========================================

-- Classification patterns table (CRITICAL - fixes main.py:93 bug)
CREATE TABLE IF NOT EXISTS classification_patterns (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    pattern_type VARCHAR(50) NOT NULL,  -- 'revenue', 'expense', 'crypto', 'transfer'
    description_pattern TEXT NOT NULL,
    entity VARCHAR(100),
    accounting_category VARCHAR(100),
    confidence_score DECIMAL(5,2) DEFAULT 0.75,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    UNIQUE(tenant_id, pattern_type, description_pattern)
);

-- Pattern feedback for continuous learning
CREATE TABLE IF NOT EXISTS pattern_feedback (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    pattern_id INTEGER REFERENCES learned_patterns(id) ON DELETE CASCADE,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    user_id VARCHAR(100),
    feedback_type VARCHAR(50),  -- 'correct', 'incorrect', 'partial', 'helpful'
    accuracy_score DECIMAL(3,2),
    provided_answer TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    useful BOOLEAN
);

-- Transaction audit history for compliance
CREATE TABLE IF NOT EXISTS transaction_audit_history (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    action VARCHAR(20) NOT NULL,  -- 'CREATE', 'UPDATE', 'DELETE'
    changes JSONB,
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

-- User sessions for conversation tracking
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    user_id VARCHAR(100) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_agent TEXT,
    ip_address VARCHAR(45),
    context_data JSONB
);

-- Chatbot interactions for conversation history
CREATE TABLE IF NOT EXISTS chatbot_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'delta',
    session_id UUID NOT NULL REFERENCES user_sessions(id) ON DELETE CASCADE,
    user_id VARCHAR(100) NOT NULL,
    user_message TEXT NOT NULL,
    chatbot_response TEXT,
    intent VARCHAR(50),
    entities_mentioned JSONB,
    confidence_score DECIMAL(3,2),
    feedback_type VARCHAR(20),
    is_resolved BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chatbot context for session state
CREATE TABLE IF NOT EXISTS chatbot_context (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES user_sessions(id) ON DELETE CASCADE,
    context_key VARCHAR(100),
    context_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, context_key)
);

-- ========================================
-- STEP 3: Create indexes
-- ========================================

-- Classification patterns indexes
CREATE INDEX IF NOT EXISTS idx_classification_patterns_tenant_pattern ON classification_patterns(tenant_id, pattern_type);
CREATE INDEX IF NOT EXISTS idx_classification_patterns_active ON classification_patterns(is_active);
CREATE INDEX IF NOT EXISTS idx_classification_patterns_entity ON classification_patterns(entity);

-- Pattern feedback indexes
CREATE INDEX IF NOT EXISTS idx_pattern_feedback_pattern_id ON pattern_feedback(pattern_id);
CREATE INDEX IF NOT EXISTS idx_pattern_feedback_transaction_id ON pattern_feedback(transaction_id);
CREATE INDEX IF NOT EXISTS idx_pattern_feedback_user_id ON pattern_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_pattern_feedback_timestamp ON pattern_feedback(timestamp);

-- Transaction audit history indexes
CREATE INDEX IF NOT EXISTS idx_audit_history_transaction_id ON transaction_audit_history(transaction_id);
CREATE INDEX IF NOT EXISTS idx_audit_history_tenant_id ON transaction_audit_history(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_history_timestamp ON transaction_audit_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_history_user_id ON transaction_audit_history(user_id);

-- User sessions indexes
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_tenant_id ON user_sessions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_started_at ON user_sessions(started_at);

-- Chatbot interactions indexes
CREATE INDEX IF NOT EXISTS idx_chatbot_interactions_session_id ON chatbot_interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_chatbot_interactions_user_id ON chatbot_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_chatbot_interactions_intent ON chatbot_interactions(intent);
CREATE INDEX IF NOT EXISTS idx_chatbot_interactions_timestamp ON chatbot_interactions(timestamp);

-- ========================================
-- STEP 4: Create triggers
-- ========================================

-- Trigger for classification_patterns updated_at
DROP TRIGGER IF EXISTS update_classification_patterns_updated_at ON classification_patterns;
CREATE TRIGGER update_classification_patterns_updated_at
    BEFORE UPDATE ON classification_patterns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger for chatbot_context updated_at
DROP TRIGGER IF EXISTS update_chatbot_context_updated_at ON chatbot_context;
CREATE TRIGGER update_chatbot_context_updated_at
    BEFORE UPDATE ON chatbot_context
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- STEP 5: Insert initial data
-- ========================================

-- Default classification patterns (migrated from business_knowledge.md)
INSERT INTO classification_patterns (pattern_type, description_pattern, entity, accounting_category, confidence_score, created_by) VALUES
    -- Revenue Patterns
    ('revenue', 'Challenge', NULL, 'Revenue - Challenge', 0.85, 'system'),
    ('revenue', 'Contest', NULL, 'Revenue - Challenge', 0.85, 'system'),
    ('revenue', 'Prize', NULL, 'Revenue - Challenge', 0.85, 'system'),
    ('revenue', 'Trading', NULL, 'Revenue - Trading', 0.80, 'system'),
    ('revenue', 'Exchange', NULL, 'Revenue - Trading', 0.80, 'system'),
    ('revenue', 'Market', NULL, 'Revenue - Trading', 0.75, 'system'),
    ('revenue', 'Mining', 'Infinity Validator', 'Revenue - Mining', 0.90, 'system'),
    ('revenue', 'Validator', 'Infinity Validator', 'Revenue - Mining', 0.90, 'system'),
    ('revenue', 'Staking', 'Infinity Validator', 'Revenue - Mining', 0.85, 'system'),
    ('revenue', 'Interest', NULL, 'Interest Income', 0.85, 'system'),
    ('revenue', 'Savings', NULL, 'Interest Income', 0.80, 'system'),
    ('revenue', 'APY', NULL, 'Interest Income', 0.85, 'system'),

    -- Expense Patterns
    ('expense', 'AWS', NULL, 'Technology Expenses', 0.95, 'system'),
    ('expense', 'Google Cloud', NULL, 'Technology Expenses', 0.95, 'system'),
    ('expense', 'Software', NULL, 'Technology Expenses', 0.80, 'system'),
    ('expense', 'SaaS', NULL, 'Technology Expenses', 0.85, 'system'),
    ('expense', 'Monthly Service Fee', NULL, 'Bank Fees', 0.95, 'system'),
    ('expense', 'Overdraft', NULL, 'Bank Fees', 0.95, 'system'),
    ('expense', 'Wire', NULL, 'Bank Fees', 0.85, 'system'),
    ('expense', 'Gateway', NULL, 'Technology Expenses', 0.80, 'system'),
    ('expense', 'Merchant', NULL, 'Technology Expenses', 0.75, 'system'),
    ('expense', 'Processing Fee', NULL, 'Bank Fees', 0.85, 'system'),
    ('expense', 'Office', NULL, 'General and Administrative', 0.80, 'system'),
    ('expense', 'Supplies', NULL, 'General and Administrative', 0.80, 'system'),
    ('expense', 'Professional', NULL, 'General and Administrative', 0.75, 'system'),

    -- Crypto/Transfer Patterns
    ('crypto', 'BTC', NULL, NULL, 0.90, 'system'),
    ('crypto', 'ETH', NULL, NULL, 0.90, 'system'),
    ('crypto', 'USDT', NULL, NULL, 0.90, 'system'),
    ('crypto', 'TAO', NULL, NULL, 0.90, 'system'),
    ('transfer', 'Internal Transfer', NULL, NULL, 0.90, 'system'),
    ('transfer', 'Between Accounts', NULL, NULL, 0.85, 'system')
ON CONFLICT (tenant_id, pattern_type, description_pattern) DO NOTHING;

COMMIT;

-- ========================================
-- Completion message
-- ========================================

DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Phase 1 Migration Complete!';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Changes applied:';
    RAISE NOTICE '- Added tenant_id to 4 core tables';
    RAISE NOTICE '- Created classification_patterns table (fixes main.py bug)';
    RAISE NOTICE '- Created 6 new tables for chatbot functionality';
    RAISE NOTICE '- Added 20+ performance indexes';
    RAISE NOTICE '- Migrated 31 business rules from markdown to database';
    RAISE NOTICE '';
    RAISE NOTICE 'New tables:';
    RAISE NOTICE '  - classification_patterns (31 patterns)';
    RAISE NOTICE '  - pattern_feedback';
    RAISE NOTICE '  - transaction_audit_history';
    RAISE NOTICE '  - user_sessions';
    RAISE NOTICE '  - chatbot_interactions';
    RAISE NOTICE '  - chatbot_context';
    RAISE NOTICE '';
    RAISE NOTICE 'System is ready for Phase 2 development!';
    RAISE NOTICE '==============================================';
END $$;
