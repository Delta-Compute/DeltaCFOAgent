# Tenant Setup Guide

## Overview

As of the multi-tenant migration, **tenant-specific seed data has been removed from the main schema file**. This ensures that new tenant databases start with a clean slate.

## Schema Files

### Main Schema (For All Tenants)
- **File:** `postgres_unified_schema.sql` (in project root)
- **Purpose:** Creates all tables, indexes, views, and triggers
- **Contains:** Generic system configuration only (no tenant-specific data)
- **Usage:** Run this for every new database initialization

### Delta Tenant Seed Data (Delta Only)
- **File:** `migrations/delta_tenant_seed_data.sql`
- **Purpose:** Loads Delta-specific business data
- **Contains:**
  - Delta business entities (Delta LLC, Delta Prop Shop, etc.)
  - Delta crypto invoice clients (Alps Blockchain, Exos Capital, etc.)
  - Delta tenant configuration
  - Delta wallet addresses (production wallets)
  - Delta bank accounts
- **Usage:** Run this ONLY for the Delta tenant

### Helper Script
- **File:** `migrations/apply_delta_seed_data.py`
- **Purpose:** Python wrapper for applying Delta seed data with verification
- **Usage:**
  ```bash
  # Apply Delta seed data
  python migrations/apply_delta_seed_data.py

  # Dry run (preview without executing)
  python migrations/apply_delta_seed_data.py --dry-run

  # Apply and verify
  python migrations/apply_delta_seed_data.py --verify

  # Just verify existing data
  python migrations/apply_delta_seed_data.py --verify
  ```

## Database Initialization Workflows

### For Delta Tenant (Existing Production)

1. **Apply main schema:**
   ```bash
   psql -h <host> -U <user> -d delta_cfo -f postgres_unified_schema.sql
   ```

2. **Apply Delta seed data:**
   ```bash
   # Option 1: Using Python helper (recommended)
   python migrations/apply_delta_seed_data.py --verify

   # Option 2: Direct SQL
   psql -h <host> -U <user> -d delta_cfo -f migrations/delta_tenant_seed_data.sql
   ```

### For New Tenants (Multi-Tenant SaaS)

1. **Apply main schema:**
   ```bash
   psql -h <host> -U <user> -d <database> -f postgres_unified_schema.sql
   ```

2. **Use onboarding flow:**
   - Navigate to `/api/onboarding` in the web interface
   - Follow the guided setup process
   - The system will create:
     - Tenant configuration
     - Initial business entities
     - Chart of accounts (industry-specific)
     - Classification patterns based on industry

3. **Do NOT run Delta seed data** for new tenants

## Migration from Old Setup

If you have an existing database that was initialized with Delta seed data in the schema:

1. **Your existing data is safe** - no action needed
2. **For new databases**, use the workflows above
3. **Update deployment scripts** to use new workflow:
   - Replace references to `migration/postgresql_schema.sql` with `postgres_unified_schema.sql`
   - Add Delta seed data step only for Delta tenant

## Deployment Scripts

### Scripts That May Need Updates

The following scripts may reference the old schema file and should be updated:

- ❌ `apply_schema_sa.py` - Uses old `migration/postgresql_schema.sql`
- ❌ `apply_schema_direct.py` - Uses old schema file
- ❌ `apply_schema_simple.py` - Uses old schema file
- ⚠️ `scripts/setup_cloud_sql.sh` - Uses old schema file
- ⚠️ `setup_cloud_complete.bat` - May use old schema file

### Recommended Updates

Replace schema application steps in deployment scripts with:

```bash
# Apply main schema
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f postgres_unified_schema.sql

# For Delta tenant only
if [ "$TENANT_ID" = "delta" ]; then
    python migrations/apply_delta_seed_data.py --verify
fi
```

## Security Considerations

### Delta Seed Data Contains Sensitive Information

The `delta_tenant_seed_data.sql` file contains:
- Real production wallet addresses
- Bank account information (masked but identifiable)
- Business structure information

**Important:**
- ⚠️ Keep this file secure - do NOT expose to other tenants
- ⚠️ Do NOT include in public repositories if open-sourcing
- ⚠️ Add to `.gitignore` if needed for additional security
- ✅ Use environment variables or secure vaults for truly sensitive data

## Verification

After setup, verify the database state:

### For Delta Tenant:
```bash
python migrations/apply_delta_seed_data.py --verify
```

Expected output:
```
✅ Tenant Configuration: Delta Capital Holdings
✅ Business Entities: 6 found (expected: 6)
✅ Crypto Invoice Clients: 4 found (expected: 4)
✅ Wallet Addresses: 3 found (expected: 3)
✅ Bank Accounts: 3 found (expected: 3)
✅ ALL CHECKS PASSED
```

### For New Tenants:
```bash
# Check tenant exists
psql -h <host> -U <user> -d <database> -c \
  "SELECT tenant_id, company_name FROM tenant_configuration WHERE tenant_id = 'your_tenant_id';"

# Should return 0 Delta entities
psql -h <host> -U <user> -d <database> -c \
  "SELECT COUNT(*) FROM business_entities WHERE name LIKE '%Delta%';"
```

## Troubleshooting

### Problem: "Delta entities showing up for new tenant"
**Cause:** Old schema file was used that included Delta seed data
**Solution:**
1. Delete Delta-specific records:
   ```sql
   DELETE FROM business_entities WHERE name IN (
     'Delta LLC', 'Delta Prop Shop LLC', 'Infinity Validator',
     'MMIW LLC', 'DM Mining LLC', 'Delta Mining Paraguay S.A.'
   );
   DELETE FROM clients WHERE name IN (
     'Alps Blockchain', 'Exos Capital', 'GM Data Centers'
   );
   DELETE FROM wallet_addresses WHERE tenant_id = 'delta';
   DELETE FROM bank_accounts WHERE tenant_id = 'delta';
   DELETE FROM tenant_configuration WHERE tenant_id = 'delta';
   ```

### Problem: "Schema file not found"
**Cause:** Using old migration path
**Solution:** Use `postgres_unified_schema.sql` from project root, not `migration/postgresql_schema.sql`

### Problem: "Delta seed data verification fails"
**Cause:** Data not loaded or partial load
**Solution:**
```bash
# Re-run with verification
python migrations/apply_delta_seed_data.py --verify

# Check for errors in output
# Re-run if needed (script is idempotent with ON CONFLICT clauses)
```

## Related Documentation

- Main schema: `postgres_unified_schema.sql` (see comments at top of file)
- Migration guide: `POSTGRESQL_MIGRATION_GUIDE.md`
- Multi-tenant guide: `MULTI_TENANT_OVERHAUL_SUMMARY.md`
- Onboarding API: `api/onboarding_routes.py`
- Claude.md: Project overview and development guidelines

## Questions?

If you encounter issues:
1. Check the completion messages from schema execution
2. Run verification scripts
3. Check database logs for errors
4. Review this document for your specific use case

---

**Last Updated:** 2024-11 (Multi-tenant schema separation)
