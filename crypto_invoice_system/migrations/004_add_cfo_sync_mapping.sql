-- Migration: Add invoice-to-CFO-transaction mapping table
-- Date: 2025-10-22
-- Description: Creates table to track invoices synced to AI CFO system

-- =============================================================================
-- CFO SYNC MAPPING TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS crypto_invoice_cfo_sync (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES crypto_invoices(id) ON DELETE CASCADE,
    cfo_transaction_id INTEGER,
    sync_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    sync_timestamp TIMESTAMP,
    cfo_database_table VARCHAR(100) DEFAULT 'transactions',
    entity_mapped VARCHAR(255),
    category_mapped VARCHAR(100),
    confidence_score DECIMAL(3,2) DEFAULT 1.00,
    sync_error TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(invoice_id)
);

COMMENT ON TABLE crypto_invoice_cfo_sync IS 'Maps crypto invoices to AI CFO system transactions';
COMMENT ON COLUMN crypto_invoice_cfo_sync.invoice_id IS 'Reference to crypto_invoices table';
COMMENT ON COLUMN crypto_invoice_cfo_sync.cfo_transaction_id IS 'ID in main CFO transactions table';
COMMENT ON COLUMN crypto_invoice_cfo_sync.sync_status IS 'Sync status: pending, synced, failed, retry';
COMMENT ON COLUMN crypto_invoice_cfo_sync.entity_mapped IS 'Entity assigned in CFO system';
COMMENT ON COLUMN crypto_invoice_cfo_sync.category_mapped IS 'Category in CFO system (Revenue)';
COMMENT ON COLUMN crypto_invoice_cfo_sync.confidence_score IS 'Classification confidence (1.0 for invoice payments)';
COMMENT ON COLUMN crypto_invoice_cfo_sync.sync_error IS 'Error message if sync failed';
COMMENT ON COLUMN crypto_invoice_cfo_sync.retry_count IS 'Number of sync retry attempts';

-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_cfo_sync_invoice ON crypto_invoice_cfo_sync(invoice_id);
CREATE INDEX IF NOT EXISTS idx_cfo_sync_status ON crypto_invoice_cfo_sync(sync_status);
CREATE INDEX IF NOT EXISTS idx_cfo_sync_timestamp ON crypto_invoice_cfo_sync(sync_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_cfo_sync_cfo_txid ON crypto_invoice_cfo_sync(cfo_transaction_id);

-- =============================================================================
-- SYNC LOG TABLE (Optional - for audit trail)
-- =============================================================================

CREATE TABLE IF NOT EXISTS crypto_cfo_sync_log (
    id SERIAL PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES crypto_invoices(id) ON DELETE CASCADE,
    sync_attempt_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sync_status VARCHAR(20) NOT NULL,
    cfo_transaction_id INTEGER,
    error_message TEXT,
    request_payload JSONB,
    response_data JSONB
);

COMMENT ON TABLE crypto_cfo_sync_log IS 'Audit log for all CFO sync attempts';

CREATE INDEX IF NOT EXISTS idx_cfo_sync_log_invoice ON crypto_cfo_sync_log(invoice_id);
CREATE INDEX IF NOT EXISTS idx_cfo_sync_log_timestamp ON crypto_cfo_sync_log(sync_attempt_timestamp DESC);

-- =============================================================================
-- HELPER VIEWS
-- =============================================================================

-- View: Invoices pending CFO sync
CREATE OR REPLACE VIEW v_crypto_invoices_pending_sync AS
SELECT
    i.id as invoice_id,
    i.invoice_number,
    i.client_id,
    c.name as client_name,
    i.status as invoice_status,
    i.amount_usd,
    i.crypto_currency,
    i.paid_at,
    s.sync_status,
    s.retry_count,
    s.last_retry_at
FROM crypto_invoices i
LEFT JOIN crypto_clients c ON i.client_id = c.id
LEFT JOIN crypto_invoice_cfo_sync s ON i.id = s.invoice_id
WHERE i.status = 'paid'
AND (s.sync_status IS NULL OR s.sync_status IN ('pending', 'failed'))
ORDER BY i.paid_at DESC;

COMMENT ON VIEW v_crypto_invoices_pending_sync IS 'Invoices that are paid but not yet synced to CFO';

-- View: Successfully synced invoices
CREATE OR REPLACE VIEW v_crypto_invoices_synced AS
SELECT
    i.id as invoice_id,
    i.invoice_number,
    c.name as client_name,
    i.amount_usd,
    i.paid_at,
    s.cfo_transaction_id,
    s.sync_timestamp,
    s.entity_mapped,
    s.category_mapped,
    s.confidence_score
FROM crypto_invoices i
JOIN crypto_clients c ON i.client_id = c.id
JOIN crypto_invoice_cfo_sync s ON i.id = s.invoice_id
WHERE s.sync_status = 'synced'
ORDER BY s.sync_timestamp DESC;

COMMENT ON VIEW v_crypto_invoices_synced IS 'Successfully synced invoices with CFO transaction details';

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function: Get invoices ready for sync
CREATE OR REPLACE FUNCTION get_invoices_ready_for_sync()
RETURNS TABLE (
    invoice_id INTEGER,
    invoice_number VARCHAR,
    client_name VARCHAR,
    amount_usd DECIMAL,
    crypto_currency VARCHAR,
    crypto_amount DECIMAL,
    transaction_hash VARCHAR,
    paid_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.id,
        i.invoice_number,
        c.name,
        i.amount_usd,
        i.crypto_currency,
        i.crypto_amount,
        p.transaction_hash,
        i.paid_at
    FROM crypto_invoices i
    JOIN crypto_clients c ON i.client_id = c.id
    LEFT JOIN crypto_payment_transactions p ON i.id = p.invoice_id AND p.status = 'confirmed'
    LEFT JOIN crypto_invoice_cfo_sync s ON i.id = s.invoice_id
    WHERE i.status = 'paid'
    AND (s.sync_status IS NULL OR s.sync_status = 'failed')
    AND (s.retry_count IS NULL OR s.retry_count < 3)  -- Max 3 retries
    ORDER BY i.paid_at ASC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_invoices_ready_for_sync() IS 'Returns invoices that are paid and ready to sync to CFO';

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_cfo_sync_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_cfo_sync_updated_at
BEFORE UPDATE ON crypto_invoice_cfo_sync
FOR EACH ROW
EXECUTE FUNCTION update_cfo_sync_timestamp();
