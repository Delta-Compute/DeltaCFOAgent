# Database Migration Guide

## Overview

This guide explains how to run the Phase 1 database migrations for the crypto invoice system on Google Cloud SQL.

**⚠️ IMPORTANT:** These migrations should be run in order on a staging/test database first before production.

---

## Prerequisites

✅ Access to Google Cloud SQL instance: `aicfo-473816:southamerica-east1:delta-cfo-db`
✅ Database credentials (DB_USER=delta_user, DB_PASSWORD from Secret Manager)
✅ Cloud SQL Proxy installed (optional but recommended)
✅ PostgreSQL client (psql) or Python with psycopg2

---

## Migration Files

| Migration | Description | Type |
|-----------|-------------|------|
| 001_add_invoice_fields.sql | Add 6 new invoice fields | ALTER TABLE |
| 002_add_performance_indexes.sql | Add 28 performance indexes | CREATE INDEX |
| 003_add_blockchain_config_tables.sql | Add blockchain config tables + seed data | CREATE TABLE |
| 004_add_cfo_sync_mapping.sql | Add CFO sync mapping tables | CREATE TABLE |

---

## Method 1: Using Cloud SQL Proxy (Recommended)

### Step 1: Start Cloud SQL Proxy

```bash
cloud_sql_proxy -instances=aicfo-473816:southamerica-east1:delta-cfo-db=tcp:5432
```

### Step 2: Run Migrations

```bash
cd /home/user/DeltaCFOAgent

# Migration 001 (Python runner with verification)
python crypto_invoice_system/migrations/run_migration_001.py

# Migration 002 (Python runner with verification)
python crypto_invoice_system/migrations/run_migration_002.py

# Migration 003 (Direct SQL)
psql -h localhost -U delta_user -d delta_cfo -f crypto_invoice_system/migrations/003_add_blockchain_config_tables.sql

# Migration 004 (Direct SQL)
psql -h localhost -U delta_user -d delta_cfo -f crypto_invoice_system/migrations/004_add_cfo_sync_mapping.sql
```

---

## Method 2: Direct Connection

### Using psql

```bash
# Set password
export PGPASSWORD="<password_from_secret_manager>"

# Run each migration
psql -h 34.39.143.82 -U delta_user -d delta_cfo -f crypto_invoice_system/migrations/001_add_invoice_fields.sql
psql -h 34.39.143.82 -U delta_user -d delta_cfo -f crypto_invoice_system/migrations/002_add_performance_indexes.sql
psql -h 34.39.143.82 -U delta_user -d delta_cfo -f crypto_invoice_system/migrations/003_add_blockchain_config_tables.sql
psql -h 34.39.143.82 -U delta_user -d delta_cfo -f crypto_invoice_system/migrations/004_add_cfo_sync_mapping.sql
```

### Using Python

```python
import psycopg2
import os

# Connect to database
conn = psycopg2.connect(
    host="34.39.143.82",
    port=5432,
    database="delta_cfo",
    user="delta_user",
    password=os.getenv("DB_PASSWORD")
)

# Run migrations
cursor = conn.cursor()

# Migration 001
with open('crypto_invoice_system/migrations/001_add_invoice_fields.sql', 'r') as f:
    cursor.execute(f.read())

# Migration 002
with open('crypto_invoice_system/migrations/002_add_performance_indexes.sql', 'r') as f:
    cursor.execute(f.read())

# Migration 003
with open('crypto_invoice_system/migrations/003_add_blockchain_config_tables.sql', 'r') as f:
    cursor.execute(f.read())

# Migration 004
with open('crypto_invoice_system/migrations/004_add_cfo_sync_mapping.sql', 'r') as f:
    cursor.execute(f.read())

conn.commit()
cursor.close()
conn.close()
```

---

## Verification Steps

After running migrations, verify:

### 1. Check New Invoice Fields

```sql
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'crypto_invoices'
AND column_name IN (
    'transaction_fee_percent',
    'tax_percent',
    'rate_locked_until',
    'expiration_hours',
    'allow_client_choice',
    'client_wallet_address'
);
```

Expected: 6 rows

### 2. Check Indexes Created

```sql
SELECT indexname
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename LIKE 'crypto_%'
AND indexname LIKE 'idx_crypto_%'
ORDER BY indexname;
```

Expected: 28+ indexes

### 3. Check Blockchain Config Tables

```sql
SELECT COUNT(*) FROM crypto_blockchain_chains;
SELECT COUNT(*) FROM crypto_blockchain_tokens;
```

Expected: 8 chains, 27 tokens

### 4. Check CFO Sync Tables

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('crypto_invoice_cfo_sync', 'crypto_cfo_sync_log');
```

Expected: 2 tables

### 5. Check Views Created

```sql
SELECT viewname
FROM pg_views
WHERE schemaname = 'public'
AND viewname LIKE 'v_crypto_%';
```

Expected: 2 views (v_crypto_invoices_pending_sync, v_crypto_invoices_synced)

### 6. Check Functions Created

```sql
SELECT proname
FROM pg_proc
WHERE proname = 'get_invoices_ready_for_sync';
```

Expected: 1 function

---

## Rollback Procedures

If migrations fail or need to be rolled back:

### Rollback Migration 004 (CFO Sync)

```sql
DROP VIEW IF EXISTS v_crypto_invoices_synced;
DROP VIEW IF EXISTS v_crypto_invoices_pending_sync;
DROP FUNCTION IF EXISTS get_invoices_ready_for_sync();
DROP TABLE IF EXISTS crypto_cfo_sync_log CASCADE;
DROP TABLE IF EXISTS crypto_invoice_cfo_sync CASCADE;
```

### Rollback Migration 003 (Blockchain Config)

```sql
DROP TABLE IF EXISTS crypto_blockchain_tokens CASCADE;
DROP TABLE IF EXISTS crypto_blockchain_chains CASCADE;
```

### Rollback Migration 002 (Indexes)

```sql
DROP INDEX IF EXISTS idx_crypto_invoices_invoice_number;
DROP INDEX IF EXISTS idx_crypto_invoices_status;
-- ... (drop all 28 indexes - see migration file for full list)
```

### Rollback Migration 001 (Invoice Fields)

```sql
ALTER TABLE crypto_invoices DROP COLUMN IF EXISTS transaction_fee_percent;
ALTER TABLE crypto_invoices DROP COLUMN IF EXISTS tax_percent;
ALTER TABLE crypto_invoices DROP COLUMN IF EXISTS rate_locked_until;
ALTER TABLE crypto_invoices DROP COLUMN IF EXISTS expiration_hours;
ALTER TABLE crypto_invoices DROP COLUMN IF EXISTS allow_client_choice;
ALTER TABLE crypto_invoices DROP COLUMN IF EXISTS client_wallet_address;
```

---

## Migration Order

**CRITICAL:** Migrations must be run in this exact order:

1. ✅ Migration 001 - Add invoice fields (ALTERs existing table)
2. ✅ Migration 002 - Add indexes (depends on 001 fields)
3. ✅ Migration 003 - Add blockchain config (new tables)
4. ✅ Migration 004 - Add CFO sync (references crypto_invoices)

**Dependencies:**
- Migration 002 requires Migration 001 (indexes reference new fields)
- Migration 004 requires existing crypto_invoices table
- No dependencies between 003 and others (independent tables)

---

## Testing Migrations (Recommended)

### Option 1: Local PostgreSQL

```bash
# Install PostgreSQL locally
# Create test database
createdb delta_cfo_test

# Run migrations
psql -d delta_cfo_test -f crypto_invoice_system/migrations/001_add_invoice_fields.sql
psql -d delta_cfo_test -f crypto_invoice_system/migrations/002_add_performance_indexes.sql
psql -d delta_cfo_test -f crypto_invoice_system/migrations/003_add_blockchain_config_tables.sql
psql -d delta_cfo_test -f crypto_invoice_system/migrations/004_add_cfo_sync_mapping.sql

# Verify
psql -d delta_cfo_test -c "\dt crypto_*"
psql -d delta_cfo_test -c "\di crypto_*"
```

### Option 2: Cloud SQL Staging Instance

Create a staging instance that mirrors production, run migrations there first.

---

## Expected Results

After successful migration:

### Tables (Existing Modified)
- ✅ crypto_invoices (+6 fields)

### Tables (New)
- ✅ crypto_blockchain_chains
- ✅ crypto_blockchain_tokens
- ✅ crypto_invoice_cfo_sync
- ✅ crypto_cfo_sync_log

### Indexes
- ✅ 28 new indexes

### Views
- ✅ v_crypto_invoices_pending_sync
- ✅ v_crypto_invoices_synced

### Functions
- ✅ get_invoices_ready_for_sync()

### Seed Data
- ✅ 8 blockchain chains
- ✅ 27 tokens across chains

---

## Troubleshooting

### Error: "column already exists"

**Cause:** Migration 001 already run
**Solution:** Skip migration 001 or check if fields match expected schema

### Error: "relation already exists"

**Cause:** Tables from migrations 003 or 004 already exist
**Solution:** Skip those migrations or drop existing tables first

### Error: "permission denied"

**Cause:** Insufficient database privileges
**Solution:** Ensure delta_user has CREATE, ALTER, and INDEX privileges

### Error: "connection refused"

**Cause:** Cannot connect to Cloud SQL
**Solution:** Check Cloud SQL Proxy is running or firewall rules allow connection

---

## Post-Migration Tasks

After successful migration:

1. ✅ Update application code to use new fields
2. ✅ Test invoice creation with new fields
3. ✅ Verify blockchain config API works
4. ✅ Test CFO sync workflow
5. ✅ Monitor query performance with new indexes
6. ✅ Update documentation with schema changes

---

## Migration Log

Keep track of migrations run:

```sql
-- Create migration tracking table (optional)
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    applied_by VARCHAR(100)
);

-- Record migrations
INSERT INTO schema_migrations (migration_name, applied_by) VALUES
    ('001_add_invoice_fields', 'admin'),
    ('002_add_performance_indexes', 'admin'),
    ('003_add_blockchain_config_tables', 'admin'),
    ('004_add_cfo_sync_mapping', 'admin');
```

---

## Contact & Support

If you encounter issues:
- Review migration SQL files for syntax errors
- Check PostgreSQL logs: `SELECT * FROM pg_stat_activity;`
- Verify database user permissions
- Test migrations on local/staging first

---

**Last Updated:** 2025-10-22
**Phase:** 1 (Database Enhancements)
**Status:** Ready for Execution
