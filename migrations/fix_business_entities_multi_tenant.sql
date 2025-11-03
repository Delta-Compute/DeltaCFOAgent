-- Migration: Add Multi-Tenant Support to business_entities
-- Date: 2025-10-31
-- Description: Adds tenant_id column and proper constraints for multi-tenant isolation

BEGIN;

-- Step 1: Add tenant_id column (nullable initially to handle existing data)
ALTER TABLE business_entities
ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(100);

-- Step 2: Set default tenant for existing records (assuming 'delta' tenant)
UPDATE business_entities
SET tenant_id = 'delta'
WHERE tenant_id IS NULL;

-- Step 3: Make tenant_id NOT NULL now that all records have values
ALTER TABLE business_entities
ALTER COLUMN tenant_id SET NOT NULL;

-- Step 4: Drop old UNIQUE constraint on name alone
ALTER TABLE business_entities
DROP CONSTRAINT IF EXISTS business_entities_name_key;

-- Step 5: Add composite UNIQUE constraint (tenant_id + name)
-- This allows same entity name across different tenants
ALTER TABLE business_entities
ADD CONSTRAINT business_entities_tenant_name_unique
UNIQUE (tenant_id, name);

-- Step 6: Add foreign key to tenant_configuration
ALTER TABLE business_entities
ADD CONSTRAINT business_entities_tenant_fkey
FOREIGN KEY (tenant_id) REFERENCES tenant_configuration(tenant_id)
ON DELETE CASCADE;

-- Step 7: Create index for faster tenant-based queries
CREATE INDEX IF NOT EXISTS idx_business_entities_tenant
ON business_entities(tenant_id);

-- Step 8: Create index for active entities
CREATE INDEX IF NOT EXISTS idx_business_entities_tenant_active
ON business_entities(tenant_id, active);

COMMIT;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Business entities table successfully migrated to multi-tenant!';
    RAISE NOTICE ' - Added tenant_id column';
    RAISE NOTICE ' - Updated existing records to delta tenant';
    RAISE NOTICE ' - Added tenant-based unique constraint';
    RAISE NOTICE ' - Added foreign key to tenant_configuration';
    RAISE NOTICE ' - Created performance indexes';
END $$;
