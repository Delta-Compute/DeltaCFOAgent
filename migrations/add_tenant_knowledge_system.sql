-- Migration: Add Tenant Knowledge System
-- Date: 2025-10-31
-- Description: Tables for storing tenant documents and AI-extracted business knowledge

-- Tenant documents (contracts, reports, business docs)
CREATE TABLE IF NOT EXISTS tenant_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    document_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(50), -- 'contract', 'report', 'invoice', 'statement', 'other'
    file_path TEXT, -- Where the file is stored
    file_size INTEGER, -- Size in bytes
    mime_type VARCHAR(100),
    uploaded_by_user_id VARCHAR(100),
    processed BOOLEAN DEFAULT false,
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenant_configuration(tenant_id) ON DELETE CASCADE
);

-- AI-extracted knowledge about the tenant's business
CREATE TABLE IF NOT EXISTS tenant_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    source_document_id UUID, -- Reference to tenant_documents if extracted from a document
    knowledge_type VARCHAR(50) NOT NULL, -- 'vendor_info', 'transaction_pattern', 'business_rule', 'entity_relationship', 'general'
    title VARCHAR(255),
    content TEXT NOT NULL, -- The actual knowledge/insight
    structured_data JSONB, -- Structured information (vendors, amounts, frequencies, etc.)
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenant_configuration(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (source_document_id) REFERENCES tenant_documents(id) ON DELETE SET NULL
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_tenant_documents_tenant ON tenant_documents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_documents_processed ON tenant_documents(processed);
CREATE INDEX IF NOT EXISTS idx_tenant_knowledge_tenant ON tenant_knowledge(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_knowledge_type ON tenant_knowledge(knowledge_type);
CREATE INDEX IF NOT EXISTS idx_tenant_knowledge_active ON tenant_knowledge(is_active);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_tenant_knowledge_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tenant_knowledge_updated_at
    BEFORE UPDATE ON tenant_knowledge
    FOR EACH ROW
    EXECUTE FUNCTION update_tenant_knowledge_updated_at();

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Tenant knowledge system tables created successfully!';
    RAISE NOTICE '- tenant_documents: For storing uploaded documents';
    RAISE NOTICE '- tenant_knowledge: For AI-extracted business insights';
END $$;
