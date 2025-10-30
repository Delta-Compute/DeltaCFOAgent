-- Performance Optimization Indexes for DeltaCFOAgent
-- Created: 2025-10-30
-- Purpose: Improve transaction query performance

-- Index for tenant_id + date queries with archived filter
-- This is the most common query pattern: filter by tenant and sort by date
CREATE INDEX IF NOT EXISTS idx_transactions_tenant_date
ON transactions(tenant_id, date DESC)
WHERE (archived = FALSE OR archived IS NULL);

-- Index for entity filtering within tenant
CREATE INDEX IF NOT EXISTS idx_transactions_tenant_entity
ON transactions(tenant_id, classified_entity)
WHERE tenant_id IS NOT NULL;

-- Index for full-text search on description field
-- Requires PostgreSQL 9.6+ with GIN index support
CREATE INDEX IF NOT EXISTS idx_transactions_description_fts
ON transactions USING gin(to_tsvector('english', description));

-- Index for amount range queries
CREATE INDEX IF NOT EXISTS idx_transactions_amount
ON transactions(tenant_id, amount);

-- Index for date range queries (used in exports and filters)
CREATE INDEX IF NOT EXISTS idx_transactions_date_range
ON transactions(tenant_id, date);

-- Index for source_file filtering (File Manager)
CREATE INDEX IF NOT EXISTS idx_transactions_source_file
ON transactions(tenant_id, source_file)
WHERE source_file IS NOT NULL AND source_file != '';

-- Composite index for common multi-filter scenarios
CREATE INDEX IF NOT EXISTS idx_transactions_composite
ON transactions(tenant_id, date, classified_entity, archived);

-- Show all indexes on transactions table
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'transactions'
ORDER BY indexname;
