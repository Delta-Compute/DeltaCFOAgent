-- Migration: Add source_document_id to transactions table
-- Links transactions to their source files in GCS

-- Add column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'transactions'
        AND column_name = 'source_document_id'
    ) THEN
        ALTER TABLE transactions
        ADD COLUMN source_document_id UUID REFERENCES tenant_documents(id) ON DELETE SET NULL;

        CREATE INDEX IF NOT EXISTS idx_transactions_source_document
        ON transactions(source_document_id);

        COMMENT ON COLUMN transactions.source_document_id IS 'References the GCS document that this transaction was imported from';
    END IF;
END $$;
