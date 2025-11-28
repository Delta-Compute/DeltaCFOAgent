-- Migration: Add business_insights table for AI knowledge generation
-- This table stores EVIDENCE for why patterns were created

CREATE TABLE IF NOT EXISTS business_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(255) NOT NULL,

    -- What type of insight
    insight_type VARCHAR(50) NOT NULL,  -- 'account_usage', 'vendor_pattern', 'entity_behavior', 'category_pattern'
    subject_id VARCHAR(255),  -- Account number, vendor name, entity ID, etc.
    subject_type VARCHAR(50),  -- 'bank_account', 'vendor', 'entity', 'category'

    -- Evidence from transaction analysis
    transaction_count INTEGER DEFAULT 0,
    date_range_start DATE,
    date_range_end DATE,
    pattern_frequency DECIMAL(5,2),  -- Percentage (0.00-100.00)
    total_amount DECIMAL(15,2),
    avg_amount DECIMAL(15,2),

    -- Pattern details (what we detected)
    detected_entity VARCHAR(255),
    detected_category VARCHAR(100),
    detected_subcategory VARCHAR(100),

    -- AI analysis
    ai_summary TEXT,  -- Human-readable description
    ai_justification TEXT,  -- Why this pattern makes sense
    confidence_score DECIMAL(3,2),  -- 0.00-1.00

    -- Link to generated pattern
    generated_pattern_id INTEGER,  -- Links to classification_patterns.pattern_id

    -- Supporting data (JSON)
    supporting_data JSONB,  -- Additional evidence, statistics, examples

    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'approved', 'rejected', 'active'
    verified_by_user BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR(255),  -- user_id who verified
    verified_at TIMESTAMP,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) DEFAULT 'ai',  -- 'ai' or user_id

    -- Indexes
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenant_configuration(tenant_id),
    CONSTRAINT fk_pattern FOREIGN KEY (generated_pattern_id) REFERENCES classification_patterns(pattern_id)
);

-- Indexes for performance
CREATE INDEX idx_business_insights_tenant ON business_insights(tenant_id);
CREATE INDEX idx_business_insights_type ON business_insights(tenant_id, insight_type);
CREATE INDEX idx_business_insights_subject ON business_insights(tenant_id, subject_id);
CREATE INDEX idx_business_insights_status ON business_insights(status);
CREATE INDEX idx_business_insights_pattern ON business_insights(generated_pattern_id);

-- Add created_by column to classification_patterns if not exists
ALTER TABLE classification_patterns
ADD COLUMN IF NOT EXISTS created_by VARCHAR(50) DEFAULT 'user';

-- Add status column to classification_patterns if not exists
ALTER TABLE classification_patterns
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';

-- Comments
COMMENT ON TABLE business_insights IS 'Stores AI-generated business intelligence and evidence for classification patterns';
COMMENT ON COLUMN business_insights.insight_type IS 'Type of insight: account_usage, vendor_pattern, entity_behavior, category_pattern';
COMMENT ON COLUMN business_insights.pattern_frequency IS 'Percentage of transactions matching this pattern (0.00-100.00)';
COMMENT ON COLUMN business_insights.generated_pattern_id IS 'Links to the classification pattern created from this insight';
COMMENT ON COLUMN business_insights.status IS 'pending: awaiting review, approved: user confirmed, rejected: user rejected, active: pattern in use';
