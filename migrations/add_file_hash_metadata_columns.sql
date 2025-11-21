-- Migration: Add file_hash and metadata columns to tenant_documents
-- Purpose: Support Google Cloud Storage file integrity checking and additional metadata
-- Date: 2025-01-16

-- Add file_hash column for MD5 integrity checking
ALTER TABLE tenant_documents
ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);

-- Add metadata column for additional file information (JSONB)
ALTER TABLE tenant_documents
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Add index for faster queries by tenant and document type
CREATE INDEX IF NOT EXISTS idx_tenant_documents_tenant_type
ON tenant_documents(tenant_id, document_type);

-- Add index for file hash (useful for deduplication and integrity checks)
CREATE INDEX IF NOT EXISTS idx_tenant_documents_hash
ON tenant_documents(file_hash);

-- Add comment to file_hash column
COMMENT ON COLUMN tenant_documents.file_hash IS 'MD5 hash of file contents for integrity verification';

-- Add comment to metadata column
COMMENT ON COLUMN tenant_documents.metadata IS 'Additional file metadata stored as JSONB (description, tags, source, etc.)';

-- Verify columns were added
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'tenant_documents'
        AND column_name IN ('file_hash', 'metadata')
    ) THEN
        RAISE NOTICE 'Migration successful: file_hash and metadata columns added to tenant_documents';
    ELSE
        RAISE EXCEPTION 'Migration failed: columns not found';
    END IF;
END $$;
