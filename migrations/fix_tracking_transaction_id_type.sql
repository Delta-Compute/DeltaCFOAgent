-- Migration: Fix transaction_id type mismatch in user_classification_tracking
-- Issue: tracking table has UUID type but transactions table uses VARCHAR
-- Date: 2025-11-17

-- Drop the UUID column and recreate as VARCHAR to match transactions table
ALTER TABLE user_classification_tracking
DROP COLUMN IF EXISTS transaction_id;

ALTER TABLE user_classification_tracking
ADD COLUMN transaction_id VARCHAR(100);

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_tracking_transaction_id ON user_classification_tracking(transaction_id);

COMMENT ON COLUMN user_classification_tracking.transaction_id IS 'Links to transactions table (VARCHAR type to match transactions.transaction_id)';

-- Note: No foreign key constraint because transactions table primary key is 'id' (SERIAL)
-- and the actual transaction_id field format varies (VARCHAR/hex strings)
