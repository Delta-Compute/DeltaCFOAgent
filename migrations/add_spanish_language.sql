-- Migration: Add Spanish language support
-- Purpose: Extend bilingual support to trilingual (English/Portuguese/Spanish)
-- Date: 2025-01-28

-- Update CHECK constraints to include 'es' (Spanish)
-- First, drop the existing constraints, then recreate them

DO $$
BEGIN
    -- Drop existing constraint on users table if it exists
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_users_language'
    ) THEN
        ALTER TABLE users DROP CONSTRAINT chk_users_language;
    END IF;

    -- Drop existing constraint on tenant_configuration table if it exists
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_tenant_language'
    ) THEN
        ALTER TABLE tenant_configuration DROP CONSTRAINT chk_tenant_language;
    END IF;
END $$;

-- Add updated CHECK constraints that include Spanish
ALTER TABLE users
ADD CONSTRAINT chk_users_language
CHECK (preferred_language IN ('en', 'pt', 'es'));

ALTER TABLE tenant_configuration
ADD CONSTRAINT chk_tenant_language
CHECK (preferred_language IN ('en', 'pt', 'es'));

-- Update column comments to reflect trilingual support
COMMENT ON COLUMN users.preferred_language IS 'User preferred language: en (English), pt (Portuguese), or es (Spanish)';
COMMENT ON COLUMN tenant_configuration.preferred_language IS 'Tenant default language: en (English), pt (Portuguese), or es (Spanish)';

-- Verify the constraints were updated successfully
DO $$
DECLARE
    users_constraint_exists BOOLEAN;
    tenant_constraint_exists BOOLEAN;
BEGIN
    -- Check if updated constraints exist
    SELECT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_users_language'
    ) INTO users_constraint_exists;

    SELECT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_tenant_language'
    ) INTO tenant_constraint_exists;

    -- Report results
    IF users_constraint_exists AND tenant_constraint_exists THEN
        RAISE NOTICE 'Migration successful: Spanish language support added to users and tenant_configuration';
    ELSE
        RAISE EXCEPTION 'Migration failed: Constraints not properly created';
    END IF;
END $$;
