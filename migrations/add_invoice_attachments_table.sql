-- Migration: Add invoice_attachments table
-- Purpose: Track multiple attachments per invoice (payment proofs, supporting docs, etc.)
-- Date: 2025-11-04
-- Database: PostgreSQL

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create invoice_attachments table
CREATE TABLE IF NOT EXISTS invoice_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id TEXT NOT NULL,
    tenant_id VARCHAR(100) NOT NULL,
    attachment_type VARCHAR(50) DEFAULT 'other',
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(100),
    description TEXT,
    ai_extracted_data JSONB,
    ai_analysis_status VARCHAR(20) DEFAULT 'pending',
    uploaded_by VARCHAR(100),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analyzed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_invoice_attachments_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_invoice_attachments_invoice
    ON invoice_attachments(invoice_id, tenant_id);

CREATE INDEX IF NOT EXISTS idx_invoice_attachments_tenant
    ON invoice_attachments(tenant_id);

CREATE INDEX IF NOT EXISTS idx_invoice_attachments_type
    ON invoice_attachments(invoice_id, attachment_type);
