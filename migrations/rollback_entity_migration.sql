-- ============================================================================
-- Entity Migration Rollback Script
-- ============================================================================
-- This script rolls back the entity and business line migration
-- IMPORTANT: Only run this if migration needs to be reversed
--
-- This script will:
-- 1. Backup entity_id mappings to entity VARCHAR (if needed)
-- 2. Remove entity_id and business_line_id columns
-- 3. Drop business_lines table
-- 4. Drop entities table
-- 5. Clean up views and indexes
--
-- Author: Claude Code
-- Date: 2024-11-24
-- ============================================================================

-- ============================================================================
-- SAFETY CHECK
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'ENTITY MIGRATION ROLLBACK';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'WARNING: This will remove all entity and business line data!';
    RAISE NOTICE '';
    RAISE NOTICE 'Before proceeding, ensure you have:';
    RAISE NOTICE '  1. Full database backup';
    RAISE NOTICE '  2. Verified entity VARCHAR column still exists';
    RAISE NOTICE '  3. Confirmed this rollback is necessary';
    RAISE NOTICE '';
    RAISE NOTICE 'To proceed, comment out the RAISE EXCEPTION below';
    RAISE NOTICE '========================================';

    -- SAFETY: Uncomment the line below to enable rollback
    RAISE EXCEPTION 'Rollback safety check - remove this line to proceed';
END $$;

-- ============================================================================
-- STEP 1: Verify entity VARCHAR column exists
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'transactions' AND column_name = 'entity'
    ) THEN
        RAISE EXCEPTION 'entity VARCHAR column does not exist - cannot rollback safely';
    END IF;

    RAISE NOTICE '✓ entity VARCHAR column exists';
END $$;

-- ============================================================================
-- STEP 2: Backup transaction counts (for verification)
-- ============================================================================

DO $$
DECLARE
    v_total_transactions INTEGER;
    v_transactions_with_entity_id INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_total_transactions FROM transactions;
    SELECT COUNT(*) INTO v_transactions_with_entity_id FROM transactions WHERE entity_id IS NOT NULL;

    RAISE NOTICE 'Backup counts:';
    RAISE NOTICE '  Total transactions: %', v_total_transactions;
    RAISE NOTICE '  Transactions with entity_id: %', v_transactions_with_entity_id;
END $$;

-- ============================================================================
-- STEP 3: Drop foreign key constraints from dependent tables
-- ============================================================================

-- Drop constraints from transactions table
ALTER TABLE transactions
DROP CONSTRAINT IF EXISTS transactions_entity_id_fkey;

ALTER TABLE transactions
DROP CONSTRAINT IF EXISTS transactions_business_line_id_fkey;

-- Drop constraints from invoices table
ALTER TABLE invoices
DROP CONSTRAINT IF EXISTS invoices_entity_id_fkey;

ALTER TABLE invoices
DROP CONSTRAINT IF EXISTS invoices_business_line_id_fkey;

-- Drop constraints from classification_patterns table
ALTER TABLE classification_patterns
DROP CONSTRAINT IF EXISTS classification_patterns_entity_id_fkey;

ALTER TABLE classification_patterns
DROP CONSTRAINT IF EXISTS classification_patterns_business_line_id_fkey;

RAISE NOTICE '✓ Foreign key constraints dropped';

-- ============================================================================
-- STEP 4: Drop columns from transactions table
-- ============================================================================

ALTER TABLE transactions
DROP COLUMN IF EXISTS entity_id;

ALTER TABLE transactions
DROP COLUMN IF EXISTS business_line_id;

RAISE NOTICE '✓ entity_id and business_line_id columns dropped from transactions';

-- ============================================================================
-- STEP 5: Drop columns from invoices table
-- ============================================================================

ALTER TABLE invoices
DROP COLUMN IF EXISTS entity_id;

ALTER TABLE invoices
DROP COLUMN IF EXISTS business_line_id;

RAISE NOTICE '✓ entity_id and business_line_id columns dropped from invoices';

-- ============================================================================
-- STEP 6: Drop columns from classification_patterns table
-- ============================================================================

ALTER TABLE classification_patterns
DROP COLUMN IF EXISTS entity_id;

ALTER TABLE classification_patterns
DROP COLUMN IF EXISTS business_line_id;

RAISE NOTICE '✓ entity_id and business_line_id columns dropped from classification_patterns';

-- ============================================================================
-- STEP 7: Drop views
-- ============================================================================

DROP VIEW IF EXISTS entity_summary;
DROP VIEW IF EXISTS business_line_summary;

RAISE NOTICE '✓ Views dropped';

-- ============================================================================
-- STEP 8: Drop business_lines table
-- ============================================================================

DROP TABLE IF EXISTS business_lines CASCADE;

RAISE NOTICE '✓ business_lines table dropped';

-- ============================================================================
-- STEP 9: Drop entities table
-- ============================================================================

DROP TABLE IF EXISTS entities CASCADE;

RAISE NOTICE '✓ entities table dropped';

-- ============================================================================
-- STEP 10: Verify rollback
-- ============================================================================

DO $$
DECLARE
    v_total_transactions INTEGER;
BEGIN
    -- Check transactions table still exists and has data
    SELECT COUNT(*) INTO v_total_transactions FROM transactions;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Rollback Complete';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Verification:';
    RAISE NOTICE '  Total transactions after rollback: %', v_total_transactions;

    -- Check that new tables are gone
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'entities') THEN
        RAISE NOTICE '  ✓ entities table removed';
    ELSE
        RAISE WARNING '  ✗ entities table still exists';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'business_lines') THEN
        RAISE NOTICE '  ✓ business_lines table removed';
    ELSE
        RAISE WARNING '  ✗ business_lines table still exists';
    END IF;

    -- Check that entity VARCHAR column still exists
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'transactions' AND column_name = 'entity') THEN
        RAISE NOTICE '  ✓ entity VARCHAR column preserved';
    ELSE
        RAISE WARNING '  ✗ entity VARCHAR column missing';
    END IF;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'System reverted to VARCHAR entity model';
    RAISE NOTICE '========================================';
END $$;

-- ============================================================================
-- Post-Rollback Notes
-- ============================================================================
--
-- After rollback:
-- 1. Verify application still works with entity VARCHAR column
-- 2. Check transaction data integrity
-- 3. Review logs for any errors
-- 4. Consider what went wrong with migration before retrying
--
-- ============================================================================
