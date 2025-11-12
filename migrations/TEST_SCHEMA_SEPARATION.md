# Testing Schema Separation

This guide provides step-by-step testing procedures to verify that the schema separation works correctly.

## Test Overview

We need to verify:
1. ✅ Clean schema installs without Delta data
2. ✅ Delta seed data applies correctly
3. ✅ New tenants start with empty tables
4. ✅ Delta seed script is idempotent
5. ✅ Verification script works correctly

## Prerequisites

```bash
# Ensure you have PostgreSQL client installed
psql --version

# Set environment variables for test database
export TEST_DB_HOST="localhost"  # or your Cloud SQL IP
export TEST_DB_PORT="5432"
export TEST_DB_USER="postgres"
export TEST_DB_PASSWORD="your_password"
export TEST_DB_NAME="delta_cfo_test"
```

## Test 1: Clean Schema Installation (No Delta Data)

**Purpose:** Verify that applying the main schema does NOT insert any Delta-specific data.

### Steps:

```bash
# 1. Create a test database
psql -h $TEST_DB_HOST -U $TEST_DB_USER -c "DROP DATABASE IF EXISTS delta_cfo_test;"
psql -h $TEST_DB_HOST -U $TEST_DB_USER -c "CREATE DATABASE delta_cfo_test;"

# 2. Apply the clean schema
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_test -f postgres_unified_schema.sql

# 3. Check for Delta entities (should return 0)
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_test -c \
  "SELECT COUNT(*) as delta_entities FROM business_entities WHERE name LIKE '%Delta%' OR name LIKE '%MMIW%' OR name LIKE '%Infinity%';"

# 4. Check for Delta clients (should return 0)
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_test -c \
  "SELECT COUNT(*) as delta_clients FROM clients WHERE name IN ('Alps Blockchain', 'Exos Capital', 'GM Data Centers');"

# 5. Check for Delta tenant config (should return 0)
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_test -c \
  "SELECT COUNT(*) as delta_tenant FROM tenant_configuration WHERE tenant_id = 'delta';"

# 6. Check for Delta wallets (should return 0)
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_test -c \
  "SELECT COUNT(*) as delta_wallets FROM wallet_addresses WHERE tenant_id = 'delta';"

# 7. Check for Delta bank accounts (should return 0)
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_test -c \
  "SELECT COUNT(*) as delta_banks FROM bank_accounts WHERE tenant_id = 'delta';"

# 8. Verify system config WAS inserted (should return 6)
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_test -c \
  "SELECT COUNT(*) as system_config_count FROM system_config;"
```

### Expected Results:

```
✅ delta_entities:        0
✅ delta_clients:         0
✅ delta_tenant:          0
✅ delta_wallets:         0
✅ delta_banks:           0
✅ system_config_count:   6
```

**Status:** PASS if all Delta counts are 0 and system_config is 6.

---

## Test 2: Delta Seed Data Application

**Purpose:** Verify that the Delta seed data script correctly inserts Delta-specific data.

### Steps:

```bash
# 1. Using the test database from Test 1 (should be clean)

# 2. Apply Delta seed data using Python helper (recommended)
python migrations/apply_delta_seed_data.py --verify

# OR apply directly via psql
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_test -f migrations/delta_tenant_seed_data.sql

# 3. Verify data was inserted
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_test -c \
  "SELECT
    (SELECT COUNT(*) FROM business_entities WHERE name LIKE '%Delta%' OR name LIKE '%MMIW%' OR name LIKE '%Infinity%') as entities,
    (SELECT COUNT(*) FROM clients WHERE name IN ('Alps Blockchain', 'Exos Capital', 'GM Data Centers', 'Other')) as clients,
    (SELECT COUNT(*) FROM tenant_configuration WHERE tenant_id = 'delta') as tenant_config,
    (SELECT COUNT(*) FROM wallet_addresses WHERE tenant_id = 'delta') as wallets,
    (SELECT COUNT(*) FROM bank_accounts WHERE tenant_id = 'delta') as banks;"
```

### Expected Results:

```
✅ entities:       6  (Delta LLC, Delta Prop Shop, Infinity Validator, MMIW, DM Mining, Delta Paraguay)
✅ clients:        4  (Alps Blockchain, Exos Capital, GM Data Centers, Other)
✅ tenant_config:  1  (Delta Capital Holdings)
✅ wallets:        3  (Coinbase Exchange, Delta Internal, Cold Storage BTC)
✅ banks:          3  (Operating, Savings, Business Credit)
```

**Status:** PASS if all counts match expected values.

---

## Test 3: Python Helper Script Verification

**Purpose:** Test the `apply_delta_seed_data.py` script's verification mode.

### Steps:

```bash
# 1. Run verification only (after Test 2 has inserted data)
python migrations/apply_delta_seed_data.py --verify

# 2. Check exit code
echo "Exit code: $?"
```

### Expected Output:

```
========================================
VERIFYING DELTA SEED DATA
========================================

✅ Tenant Configuration: Delta Capital Holdings
✅ Business Entities: 6 found (expected: 6)
✅ Crypto Invoice Clients: 4 found (expected: 4)
✅ Wallet Addresses: 3 found (expected: 3)
✅ Bank Accounts: 3 found (expected: 3)

========================================
✅ ALL CHECKS PASSED - Delta seed data is complete!
========================================

Exit code: 0
```

**Status:** PASS if all checks pass and exit code is 0.

---

## Test 4: Idempotency Test

**Purpose:** Verify that running the Delta seed script multiple times doesn't cause errors or duplicate data.

### Steps:

```bash
# 1. Apply Delta seed data again (should not fail)
python migrations/apply_delta_seed_data.py

# 2. Verify counts haven't changed
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_test -c \
  "SELECT
    (SELECT COUNT(*) FROM business_entities WHERE name LIKE '%Delta%' OR name LIKE '%MMIW%' OR name LIKE '%Infinity%') as entities,
    (SELECT COUNT(*) FROM clients WHERE name IN ('Alps Blockchain', 'Exos Capital', 'GM Data Centers', 'Other')) as clients,
    (SELECT COUNT(*) FROM wallet_addresses WHERE tenant_id = 'delta') as wallets,
    (SELECT COUNT(*) FROM bank_accounts WHERE tenant_id = 'delta') as banks;"

# 3. Apply again via SQL
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_test -f migrations/delta_tenant_seed_data.sql

# 4. Verify counts STILL haven't changed
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_test -c \
  "SELECT
    (SELECT COUNT(*) FROM business_entities) as all_entities,
    (SELECT COUNT(*) FROM clients) as all_clients,
    (SELECT COUNT(*) FROM wallet_addresses) as all_wallets,
    (SELECT COUNT(*) FROM bank_accounts) as all_banks;"
```

### Expected Results:

After each application:
```
✅ entities: 6 (unchanged)
✅ clients:  4 (unchanged)
✅ wallets:  3 (unchanged)
✅ banks:    3 (unchanged)
```

**Status:** PASS if counts remain the same after multiple applications (no duplicates).

---

## Test 5: Dry-Run Mode

**Purpose:** Verify that dry-run mode doesn't make changes.

### Steps:

```bash
# 1. Create a fresh test database
psql -h $TEST_DB_HOST -U $TEST_DB_USER -c "DROP DATABASE IF EXISTS delta_cfo_dryrun_test;"
psql -h $TEST_DB_HOST -U $TEST_DB_USER -c "CREATE DATABASE delta_cfo_dryrun_test;"

# 2. Apply clean schema
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_dryrun_test -f postgres_unified_schema.sql

# 3. Run dry-run
python migrations/apply_delta_seed_data.py --dry-run

# 4. Verify NO data was inserted
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_dryrun_test -c \
  "SELECT COUNT(*) as delta_data FROM business_entities WHERE name LIKE '%Delta%';"
```

### Expected Results:

```
✅ delta_data: 0 (no data inserted in dry-run mode)
✅ SQL preview displayed in console
```

**Status:** PASS if no data is inserted.

---

## Test 6: New Tenant Simulation

**Purpose:** Simulate creating a database for a new tenant (not Delta).

### Steps:

```bash
# 1. Create new tenant test database
psql -h $TEST_DB_HOST -U $TEST_DB_USER -c "DROP DATABASE IF EXISTS new_tenant_test;"
psql -h $TEST_DB_HOST -U $TEST_DB_USER -c "CREATE DATABASE new_tenant_test;"

# 2. Apply clean schema ONLY (no Delta seed data)
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d new_tenant_test -f postgres_unified_schema.sql

# 3. Verify tables exist but are empty
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d new_tenant_test -c \
  "SELECT
    (SELECT COUNT(*) FROM business_entities) as entities,
    (SELECT COUNT(*) FROM clients) as clients,
    (SELECT COUNT(*) FROM tenant_configuration) as tenants,
    (SELECT COUNT(*) FROM wallet_addresses) as wallets,
    (SELECT COUNT(*) FROM bank_accounts) as banks;"

# 4. Insert a test tenant
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d new_tenant_test -c \
  "INSERT INTO tenant_configuration (tenant_id, company_name, company_description, industry, default_currency)
   VALUES ('acme', 'Acme Corp', 'Test company', 'Retail', 'USD');"

# 5. Verify only new tenant exists (no Delta)
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d new_tenant_test -c \
  "SELECT tenant_id, company_name FROM tenant_configuration;"
```

### Expected Results:

Before inserting test tenant:
```
✅ entities: 0
✅ clients:  0
✅ tenants:  0
✅ wallets:  0
✅ banks:    0
```

After inserting test tenant:
```
✅ tenant_id: acme
✅ company_name: Acme Corp
✅ NO 'delta' tenant in results
```

**Status:** PASS if new tenant database is clean and test tenant inserts successfully.

---

## Test 7: Schema Validation

**Purpose:** Ensure the schema file is syntactically correct.

### Steps:

```bash
# 1. Validate SQL syntax (dry-run parse)
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d delta_cfo_test --single-transaction --set ON_ERROR_STOP=on -f postgres_unified_schema.sql --dry-run 2>&1 | grep -i error

# 2. Check for common issues
grep -n "INSERT INTO.*Delta" postgres_unified_schema.sql
grep -n "INSERT INTO.*Alps" postgres_unified_schema.sql
grep -n "INSERT INTO.*Exos" postgres_unified_schema.sql

# 3. Verify only system_config INSERT remains
grep -n "INSERT INTO" postgres_unified_schema.sql
```

### Expected Results:

```
✅ No syntax errors
✅ No Delta INSERT statements (only in comments)
✅ Only 1 INSERT INTO statement (system_config)
```

**Status:** PASS if grep returns no Delta INSERTs in executable SQL.

---

## Automated Test Suite

For quick validation, run all tests:

```bash
#!/bin/bash
# Quick test suite for schema separation

echo "=== Test 1: Clean Schema ==="
psql -h $TEST_DB_HOST -U $TEST_DB_USER -c "DROP DATABASE IF EXISTS test_clean; CREATE DATABASE test_clean;"
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d test_clean -f postgres_unified_schema.sql > /dev/null 2>&1
DELTA_COUNT=$(psql -h $TEST_DB_HOST -U $TEST_DB_USER -d test_clean -t -c "SELECT COUNT(*) FROM business_entities WHERE name LIKE '%Delta%';")
if [ "$DELTA_COUNT" -eq "0" ]; then
    echo "✅ PASS: No Delta entities in clean schema"
else
    echo "❌ FAIL: Found $DELTA_COUNT Delta entities"
fi

echo "=== Test 2: Delta Seed Data ==="
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d test_clean -f migrations/delta_tenant_seed_data.sql > /dev/null 2>&1
DELTA_COUNT=$(psql -h $TEST_DB_HOST -U $TEST_DB_USER -d test_clean -t -c "SELECT COUNT(*) FROM business_entities WHERE name LIKE '%Delta%' OR name LIKE '%MMIW%' OR name LIKE '%Infinity%';")
if [ "$DELTA_COUNT" -eq "6" ]; then
    echo "✅ PASS: Delta seed data inserted 6 entities"
else
    echo "❌ FAIL: Expected 6 Delta entities, found $DELTA_COUNT"
fi

echo "=== Test 3: Python Helper ==="
python migrations/apply_delta_seed_data.py --verify > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ PASS: Verification script succeeded"
else
    echo "❌ FAIL: Verification script failed"
fi

echo "=== Test 4: Idempotency ==="
psql -h $TEST_DB_HOST -U $TEST_DB_USER -d test_clean -f migrations/delta_tenant_seed_data.sql > /dev/null 2>&1
DELTA_COUNT_AFTER=$(psql -h $TEST_DB_HOST -U $TEST_DB_USER -d test_clean -t -c "SELECT COUNT(*) FROM business_entities WHERE name LIKE '%Delta%' OR name LIKE '%MMIW%' OR name LIKE '%Infinity%';")
if [ "$DELTA_COUNT_AFTER" -eq "6" ]; then
    echo "✅ PASS: Idempotent - no duplicates created"
else
    echo "❌ FAIL: Expected 6, found $DELTA_COUNT_AFTER after re-run"
fi

echo "=== Cleanup ==="
psql -h $TEST_DB_HOST -U $TEST_DB_USER -c "DROP DATABASE IF EXISTS test_clean;"
echo "✅ Test databases cleaned up"
```

Save this as `migrations/run_schema_tests.sh` and execute:

```bash
chmod +x migrations/run_schema_tests.sh
./migrations/run_schema_tests.sh
```

---

## Test Checklist

- [ ] Test 1: Clean schema installs without Delta data
- [ ] Test 2: Delta seed data applies correctly
- [ ] Test 3: Python helper verification works
- [ ] Test 4: Script is idempotent (no duplicates)
- [ ] Test 5: Dry-run mode doesn't insert data
- [ ] Test 6: New tenant database is clean
- [ ] Test 7: Schema syntax is valid

---

## Expected Test Duration

- Manual tests: ~15-20 minutes
- Automated test suite: ~2-3 minutes

---

## Troubleshooting Test Failures

### "Connection refused" errors
- Check database is running: `psql -h $TEST_DB_HOST -U $TEST_DB_USER -c "SELECT 1;"`
- Verify credentials in environment variables

### "Permission denied" errors
- Ensure user has CREATE DATABASE privileges
- Try with superuser if testing locally

### "Relation does not exist" errors
- Ensure schema was applied before seed data
- Check for syntax errors in schema file

### Delta data appears in clean schema
- Verify you're using `postgres_unified_schema.sql` from the project root
- Check file wasn't accidentally reverted
- Confirm with: `grep -n "INSERT INTO business_entities" postgres_unified_schema.sql`

---

## Integration with CI/CD

To add these tests to your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
test-schema-separation:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:15
      env:
        POSTGRES_PASSWORD: postgres
      options: >-
        --health-cmd pg_isready
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
  steps:
    - uses: actions/checkout@v3
    - name: Run schema tests
      env:
        TEST_DB_HOST: localhost
        TEST_DB_USER: postgres
        TEST_DB_PASSWORD: postgres
      run: |
        chmod +x migrations/run_schema_tests.sh
        ./migrations/run_schema_tests.sh
```

---

**Last Updated:** 2024-11-12
