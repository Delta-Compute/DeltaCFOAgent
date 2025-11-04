-- Migration: Add invoice_payments table
-- Purpose: Track multiple partial payments per invoice for crypto split transactions
-- Date: 2025-11-04
-- Database: PostgreSQL

-- Create invoice_payments table
CREATE TABLE IF NOT EXISTS invoice_payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    invoice_id TEXT NOT NULL,
    tenant_id VARCHAR(100) NOT NULL,
    payment_date DATE NOT NULL,
    payment_amount DECIMAL(15,2) NOT NULL,
    payment_currency VARCHAR(10) DEFAULT 'USD',
    payment_method VARCHAR(50),
    payment_reference VARCHAR(200),
    payment_notes TEXT,
    attachment_id UUID,
    recorded_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_invoice_payments_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    CONSTRAINT fk_invoice_payments_attachment FOREIGN KEY (attachment_id) REFERENCES invoice_attachments(id) ON DELETE SET NULL
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_invoice_payments_invoice
    ON invoice_payments(invoice_id, tenant_id);

CREATE INDEX IF NOT EXISTS idx_invoice_payments_tenant
    ON invoice_payments(tenant_id);

CREATE INDEX IF NOT EXISTS idx_invoice_payments_date
    ON invoice_payments(payment_date);

CREATE INDEX IF NOT EXISTS idx_invoice_payments_attachment
    ON invoice_payments(attachment_id);
