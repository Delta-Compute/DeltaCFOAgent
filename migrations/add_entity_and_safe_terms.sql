-- Migration: Add entity and SAFE terms to shareholder equity system
-- Created: 2025-11-17
-- Purpose: Add entity field for multi-entity support and SAFE-specific terms storage

-- Add entity field to shareholders table
ALTER TABLE shareholders
ADD COLUMN IF NOT EXISTS entity VARCHAR(255);

-- Add SAFE terms as JSONB to support discount_rate and cap
ALTER TABLE shareholders
ADD COLUMN IF NOT EXISTS safe_terms JSONB;

-- Create index on entity for faster filtering
CREATE INDEX IF NOT EXISTS idx_shareholders_entity ON shareholders(entity);

-- Create index on safe_terms for querying SAFE agreements
CREATE INDEX IF NOT EXISTS idx_shareholders_safe_terms ON shareholders USING gin(safe_terms);

-- Add comment explaining SAFE terms structure
COMMENT ON COLUMN shareholders.safe_terms IS 'JSON object storing SAFE-specific terms: {"discount_rate": 20.0, "cap": 5000000.0}';

-- Sample SAFE terms structure:
-- {
--   "discount_rate": 20.0,  -- Discount rate percentage (0-100)
--   "cap": 5000000.0        -- Valuation cap in currency
-- }
