-- Migration: Add tenant_business_summary table for AI classification context
-- Stores a generated markdown summary of tenant's business knowledge
-- Overwritten each time a file upload triggers Pass 2 AI review

CREATE TABLE IF NOT EXISTS tenant_business_summary (
    tenant_id VARCHAR(255) PRIMARY KEY,

    -- The generated summary document
    summary_markdown TEXT NOT NULL,

    -- Metadata
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    triggered_by VARCHAR(100),  -- 'upload', 'manual', 'scheduled'
    source_file VARCHAR(500),   -- Filename that triggered generation

    -- Statistics at generation time
    transaction_count INTEGER DEFAULT 0,
    pattern_count INTEGER DEFAULT 0,
    entity_count INTEGER DEFAULT 0,
    workforce_count INTEGER DEFAULT 0,

    -- Foreign key
    CONSTRAINT fk_tenant_summary FOREIGN KEY (tenant_id)
        REFERENCES tenant_configuration(tenant_id) ON DELETE CASCADE
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_business_summary_generated
    ON tenant_business_summary(generated_at DESC);

COMMENT ON TABLE tenant_business_summary IS 'Stores AI-readable business knowledge summary per tenant, regenerated on each file upload';
COMMENT ON COLUMN tenant_business_summary.summary_markdown IS 'Structured markdown document used as context for AI classification review';
