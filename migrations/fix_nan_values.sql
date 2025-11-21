-- Fix NaN values in transactions table
-- This migration cleans up string "nan" values that were incorrectly stored

-- Fix entity column (replace 'nan' with 'Unknown Entity')
UPDATE transactions
SET entity = 'Unknown Entity'
WHERE entity IN ('nan', 'NaN', 'None', '') OR entity IS NULL;

-- Fix origin column (replace 'nan' with 'Unknown')
UPDATE transactions
SET origin = 'Unknown'
WHERE origin IN ('nan', 'NaN', 'None', '') OR origin IS NULL;

-- Fix destination column (replace 'nan' with 'Unknown')
UPDATE transactions
SET destination = 'Unknown'
WHERE destination IN ('nan', 'NaN', 'None', '') OR destination IS NULL;

-- Show counts of affected rows
SELECT
    COUNT(*) FILTER (WHERE entity = 'Unknown Entity') as fixed_entities,
    COUNT(*) FILTER (WHERE origin = 'Unknown') as fixed_origins,
    COUNT(*) FILTER (WHERE destination = 'Unknown') as fixed_destinations
FROM transactions;
