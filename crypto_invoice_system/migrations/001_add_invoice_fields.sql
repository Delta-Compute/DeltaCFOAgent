-- Migration: Add new invoice fields for fee/tax calculation and rate locking
-- Date: 2025-10-22
-- Description: Adds transaction_fee_percent, tax_percent, expiration_hours,
--              allow_client_choice, rate_locked_until, and client_wallet_address

-- Add transaction fee percent (0-10%)
ALTER TABLE crypto_invoices
ADD COLUMN IF NOT EXISTS transaction_fee_percent DECIMAL(5,3) DEFAULT 0.000;

-- Add tax percent (0-30%)
ALTER TABLE crypto_invoices
ADD COLUMN IF NOT EXISTS tax_percent DECIMAL(5,3) DEFAULT 0.000;

-- Add rate lock expiration timestamp
ALTER TABLE crypto_invoices
ADD COLUMN IF NOT EXISTS rate_locked_until TIMESTAMP;

-- Add invoice expiration hours (default 24 hours)
ALTER TABLE crypto_invoices
ADD COLUMN IF NOT EXISTS expiration_hours INTEGER DEFAULT 24;

-- Add flag to allow client to choose payment chain/token
ALTER TABLE crypto_invoices
ADD COLUMN IF NOT EXISTS allow_client_choice BOOLEAN DEFAULT FALSE;

-- Add client wallet address (optional, for returns/refunds)
ALTER TABLE crypto_invoices
ADD COLUMN IF NOT EXISTS client_wallet_address VARCHAR(255);

-- Add comments for documentation
COMMENT ON COLUMN crypto_invoices.transaction_fee_percent IS 'Transaction processing fee as percentage (e.g., 2.5 for 2.5%)';
COMMENT ON COLUMN crypto_invoices.tax_percent IS 'Tax rate as percentage (e.g., 18.0 for 18%)';
COMMENT ON COLUMN crypto_invoices.rate_locked_until IS 'Timestamp when exchange rate lock expires (typically 15 minutes from creation)';
COMMENT ON COLUMN crypto_invoices.expiration_hours IS 'Hours after creation when invoice expires if unpaid';
COMMENT ON COLUMN crypto_invoices.allow_client_choice IS 'Whether client can select different chain/token for payment';
COMMENT ON COLUMN crypto_invoices.client_wallet_address IS 'Client wallet address for refunds or verification';
