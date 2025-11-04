-- Migration: Add wallet display columns to transactions table
-- Purpose: Store friendly names for wallet addresses in origin and destination fields
-- Date: 2025-11-04

-- Add columns for displaying wallet entity names instead of addresses
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS origin_display VARCHAR(255),
ADD COLUMN IF NOT EXISTS destination_display VARCHAR(255);

-- Add index for better query performance when looking up by wallet addresses
CREATE INDEX IF NOT EXISTS idx_transactions_origin ON transactions(origin);
CREATE INDEX IF NOT EXISTS idx_transactions_destination ON transactions(destination);

-- Add index on wallet_addresses for faster lookups
CREATE INDEX IF NOT EXISTS idx_wallet_addresses_lookup ON wallet_addresses(tenant_id, wallet_address);

-- Add comments for documentation
COMMENT ON COLUMN transactions.origin_display IS 'Friendly name for origin wallet address (from wallet_addresses.entity_name)';
COMMENT ON COLUMN transactions.destination_display IS 'Friendly name for destination wallet address (from wallet_addresses.entity_name)';
