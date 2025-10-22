-- Migration: Add performance indexes for search and filtering
-- Date: 2025-10-22
-- Description: Creates indexes to optimize invoice search, filtering, and sorting operations

-- ============================================================================
-- INVOICE TABLE INDEXES
-- ============================================================================

-- Single column indexes for basic queries
CREATE INDEX IF NOT EXISTS idx_crypto_invoices_invoice_number ON crypto_invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_crypto_invoices_status ON crypto_invoices(status);
CREATE INDEX IF NOT EXISTS idx_crypto_invoices_client ON crypto_invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_crypto_invoices_created_at ON crypto_invoices(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crypto_invoices_issue_date ON crypto_invoices(issue_date DESC);
CREATE INDEX IF NOT EXISTS idx_crypto_invoices_due_date ON crypto_invoices(due_date);
CREATE INDEX IF NOT EXISTS idx_crypto_invoices_paid_at ON crypto_invoices(paid_at DESC);

-- Composite indexes for complex queries (status + date filtering)
CREATE INDEX IF NOT EXISTS idx_crypto_invoices_status_created ON crypto_invoices(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crypto_invoices_client_status ON crypto_invoices(client_id, status);
CREATE INDEX IF NOT EXISTS idx_crypto_invoices_status_due ON crypto_invoices(status, due_date);

-- ============================================================================
-- CLIENT TABLE INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_crypto_clients_name ON crypto_clients(name);

-- ============================================================================
-- PAYMENT TRANSACTION INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_crypto_payments_invoice ON crypto_payment_transactions(invoice_id);
CREATE INDEX IF NOT EXISTS idx_crypto_payments_status ON crypto_payment_transactions(status);
CREATE INDEX IF NOT EXISTS idx_crypto_payments_txhash ON crypto_payment_transactions(transaction_hash);
CREATE INDEX IF NOT EXISTS idx_crypto_payments_detected_at ON crypto_payment_transactions(detected_at DESC);

-- ============================================================================
-- POLLING LOG INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_crypto_polling_invoice ON crypto_polling_log(invoice_id);
CREATE INDEX IF NOT EXISTS idx_crypto_polling_timestamp ON crypto_polling_log(poll_timestamp DESC);

-- ============================================================================
-- NOTIFICATION INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_crypto_notifications_invoice ON crypto_notifications(invoice_id);
CREATE INDEX IF NOT EXISTS idx_crypto_notifications_status ON crypto_notifications(status);

-- ============================================================================
-- INDEX USAGE DOCUMENTATION
-- ============================================================================

COMMENT ON INDEX idx_crypto_invoices_invoice_number IS 'Search by invoice number (exact match)';
COMMENT ON INDEX idx_crypto_invoices_status IS 'Filter invoices by status';
COMMENT ON INDEX idx_crypto_invoices_client IS 'Filter invoices by client';
COMMENT ON INDEX idx_crypto_invoices_created_at IS 'Sort by creation date (newest first)';
COMMENT ON INDEX idx_crypto_invoices_issue_date IS 'Sort by issue date (newest first)';
COMMENT ON INDEX idx_crypto_invoices_due_date IS 'Filter/sort by due date';
COMMENT ON INDEX idx_crypto_invoices_paid_at IS 'Sort by payment date (newest first)';

COMMENT ON INDEX idx_crypto_invoices_status_created IS 'Get pending invoices ordered by date';
COMMENT ON INDEX idx_crypto_invoices_client_status IS 'Get client invoices filtered by status';
COMMENT ON INDEX idx_crypto_invoices_status_due IS 'Find overdue invoices by status and due date';

COMMENT ON INDEX idx_crypto_payments_txhash IS 'Search payments by transaction hash';
COMMENT ON INDEX idx_crypto_payments_detected_at IS 'Recent payments ordered by detection time';

-- ============================================================================
-- VACUUM ANALYZE FOR QUERY PLANNER
-- ============================================================================

ANALYZE crypto_invoices;
ANALYZE crypto_clients;
ANALYZE crypto_payment_transactions;
ANALYZE crypto_polling_log;
ANALYZE crypto_notifications;
