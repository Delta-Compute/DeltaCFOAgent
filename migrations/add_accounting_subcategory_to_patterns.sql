-- Migration: Add accounting_subcategory column to classification_patterns table
-- Date: 2025-11-17
-- Purpose: Support subcategory classification in pattern learning system

BEGIN;

-- Add accounting_subcategory column
ALTER TABLE classification_patterns
ADD COLUMN accounting_subcategory VARCHAR(255);

-- Add comment
COMMENT ON COLUMN classification_patterns.accounting_subcategory IS 'Subcategory for more granular transaction classification';

COMMIT;
