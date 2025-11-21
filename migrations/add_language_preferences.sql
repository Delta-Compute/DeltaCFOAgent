-- Migration: Add language preference support for internationalization
-- Purpose: Enable bilingual support (English/Portuguese) for users and tenants
-- Date: 2025-01-16

-- Add preferred_language column to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS preferred_language VARCHAR(5) DEFAULT 'en';

-- Add preferred_language column to tenant_configuration table
ALTER TABLE tenant_configuration
ADD COLUMN IF NOT EXISTS preferred_language VARCHAR(5) DEFAULT 'en';

-- Add check constraints to ensure only valid language codes (with IF NOT EXISTS logic)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_users_language'
    ) THEN
        ALTER TABLE users
        ADD CONSTRAINT chk_users_language
        CHECK (preferred_language IN ('en', 'pt'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_tenant_language'
    ) THEN
        ALTER TABLE tenant_configuration
        ADD CONSTRAINT chk_tenant_language
        CHECK (preferred_language IN ('en', 'pt'));
    END IF;
END $$;

-- Add index for faster queries by language preference
CREATE INDEX IF NOT EXISTS idx_users_language
ON users(preferred_language);

CREATE INDEX IF NOT EXISTS idx_tenant_configuration_language
ON tenant_configuration(preferred_language);

-- Add comments to columns
COMMENT ON COLUMN users.preferred_language IS 'User preferred language: en (English) or pt (Portuguese)';
COMMENT ON COLUMN tenant_configuration.preferred_language IS 'Tenant default language: en (English) or pt (Portuguese)';

-- Verify columns were added successfully
DO $$
DECLARE
    users_col_exists BOOLEAN;
    tenant_col_exists BOOLEAN;
BEGIN
    -- Check if users.preferred_language exists
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name = 'preferred_language'
    ) INTO users_col_exists;

    -- Check if tenant_configuration.preferred_language exists
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'tenant_configuration'
        AND column_name = 'preferred_language'
    ) INTO tenant_col_exists;

    -- Report results
    IF users_col_exists AND tenant_col_exists THEN
        RAISE NOTICE 'Migration successful: preferred_language columns added to users and tenant_configuration';
    ELSIF users_col_exists THEN
        RAISE WARNING 'Partial migration: preferred_language added to users only (tenant_configuration missing)';
    ELSIF tenant_col_exists THEN
        RAISE WARNING 'Partial migration: preferred_language added to tenant_configuration only (users missing)';
    ELSE
        RAISE EXCEPTION 'Migration failed: preferred_language columns not found in either table';
    END IF;
END $$;
