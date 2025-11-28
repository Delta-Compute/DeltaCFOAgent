-- Migration: Add origin and destination fields to transactions table
-- Purpose: Track sender/source and recipient/destination for better transaction tracking
-- Date: 2025-11-25

-- Add origin column (sender/source of funds)
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS origin VARCHAR(500);

-- Add destination column (recipient/where funds went)
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS destination VARCHAR(500);

-- Add comments for documentation
COMMENT ON COLUMN transactions.origin IS 'Sender or source of funds (person, company, account holder, or "Self")';
COMMENT ON COLUMN transactions.destination IS 'Recipient or destination of funds (person, company, merchant, or "Self")';

-- Create index for faster searching by origin/destination
CREATE INDEX IF NOT EXISTS idx_transactions_origin ON transactions(origin);
CREATE INDEX IF NOT EXISTS idx_transactions_destination ON transactions(destination);

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Successfully added origin and destination columns to transactions table';
    RAISE NOTICE 'Created indexes: idx_transactions_origin, idx_transactions_destination';
END $$;
