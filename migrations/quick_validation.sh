#!/bin/bash
# Quick validation script - checks files without needing a database
# This can be run immediately to verify the schema separation was done correctly

# Don't use set -e since grep may return non-zero when no match found

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "QUICK SCHEMA SEPARATION VALIDATION"
echo "========================================"
echo "This validates files without needing database access"
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Check main schema file exists
echo "Test 1: Main schema file exists"
if [ -f "$PROJECT_ROOT/postgres_unified_schema.sql" ]; then
    echo -e "${GREEN}✅ PASS${NC}: postgres_unified_schema.sql exists"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: postgres_unified_schema.sql not found"
    ((TESTS_FAILED++))
fi

# Test 2: Check Delta seed file exists
echo "Test 2: Delta seed data file exists"
if [ -f "$SCRIPT_DIR/delta_tenant_seed_data.sql" ]; then
    echo -e "${GREEN}✅ PASS${NC}: delta_tenant_seed_data.sql exists"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: delta_tenant_seed_data.sql not found"
    ((TESTS_FAILED++))
fi

# Test 3: Check Python helper exists
echo "Test 3: Python helper script exists"
if [ -f "$SCRIPT_DIR/apply_delta_seed_data.py" ]; then
    echo -e "${GREEN}✅ PASS${NC}: apply_delta_seed_data.py exists"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: apply_delta_seed_data.py not found"
    ((TESTS_FAILED++))
fi

# Test 4: No Delta entities in main schema
echo "Test 4: No Delta entities in main schema"
DELTA_INSERTS=$(grep -c "INSERT INTO business_entities.*Delta LLC" "$PROJECT_ROOT/postgres_unified_schema.sql" || true)
if [ "$DELTA_INSERTS" -eq "0" ]; then
    echo -e "${GREEN}✅ PASS${NC}: No Delta entity INSERTs in main schema"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Found $DELTA_INSERTS Delta entity INSERTs in main schema"
    ((TESTS_FAILED++))
fi

# Test 5: No Delta clients in main schema
echo "Test 5: No Delta clients in main schema"
CLIENT_INSERTS=$(grep -c "INSERT INTO clients.*Alps Blockchain" "$PROJECT_ROOT/postgres_unified_schema.sql" || true)
if [ "$CLIENT_INSERTS" -eq "0" ]; then
    echo -e "${GREEN}✅ PASS${NC}: No Delta client INSERTs in main schema"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Found $CLIENT_INSERTS Delta client INSERTs in main schema"
    ((TESTS_FAILED++))
fi

# Test 6: No Delta wallet addresses in main schema
echo "Test 6: No Delta wallet addresses in main schema"
WALLET_INSERTS=$(grep -c "INSERT INTO wallet_addresses.*'delta'" "$PROJECT_ROOT/postgres_unified_schema.sql" || true)
if [ "$WALLET_INSERTS" -eq "0" ]; then
    echo -e "${GREEN}✅ PASS${NC}: No Delta wallet INSERTs in main schema"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Found $WALLET_INSERTS Delta wallet INSERTs in main schema"
    ((TESTS_FAILED++))
fi

# Test 7: No Delta bank accounts in main schema
echo "Test 7: No Delta bank accounts in main schema"
BANK_INSERTS=$(grep -c "INSERT INTO bank_accounts.*'delta'" "$PROJECT_ROOT/postgres_unified_schema.sql" || true)
if [ "$BANK_INSERTS" -eq "0" ]; then
    echo -e "${GREEN}✅ PASS${NC}: No Delta bank account INSERTs in main schema"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Found $BANK_INSERTS Delta bank account INSERTs in main schema"
    ((TESTS_FAILED++))
fi

# Test 8: Delta entities ARE in seed file
echo "Test 8: Delta entities present in seed file"
DELTA_SEED_ENTITIES=$(grep -c "Delta LLC" "$SCRIPT_DIR/delta_tenant_seed_data.sql" || true)
if [ "$DELTA_SEED_ENTITIES" -gt "0" ]; then
    echo -e "${GREEN}✅ PASS${NC}: Delta entities found in seed file"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: No Delta entities in seed file (expected at least 1 INSERT)"
    ((TESTS_FAILED++))
fi

# Test 9: Delta clients ARE in seed file
echo "Test 9: Delta clients present in seed file"
CLIENT_SEED=$(grep -c "Alps Blockchain" "$SCRIPT_DIR/delta_tenant_seed_data.sql" || true)
if [ "$CLIENT_SEED" -gt "0" ]; then
    echo -e "${GREEN}✅ PASS${NC}: Delta clients found in seed file"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: No Delta clients in seed file"
    ((TESTS_FAILED++))
fi

# Test 10: Delta wallets ARE in seed file
echo "Test 10: Delta wallets present in seed file"
WALLET_SEED=$(grep -c "'delta'" "$SCRIPT_DIR/delta_tenant_seed_data.sql" || true)
if [ "$WALLET_SEED" -gt "0" ]; then
    echo -e "${GREEN}✅ PASS${NC}: Delta wallets found in seed file"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: No Delta wallets in seed file"
    ((TESTS_FAILED++))
fi

# Test 11: System config still in main schema
echo "Test 11: System config present in main schema"
SYSTEM_CONFIG=$(grep -c "INSERT INTO system_config" "$PROJECT_ROOT/postgres_unified_schema.sql" || true)
if [ "$SYSTEM_CONFIG" -gt "0" ]; then
    echo -e "${GREEN}✅ PASS${NC}: System config still in main schema"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: System config missing from main schema"
    ((TESTS_FAILED++))
fi

# Test 12: Python script is executable
echo "Test 12: Python helper script is executable"
if [ -x "$SCRIPT_DIR/apply_delta_seed_data.py" ]; then
    echo -e "${GREEN}✅ PASS${NC}: Python script is executable"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Python script is not executable (run: chmod +x migrations/apply_delta_seed_data.py)"
    ((TESTS_FAILED++))
fi

# Test 13: Check documentation exists
echo "Test 13: Setup documentation exists"
if [ -f "$SCRIPT_DIR/README_TENANT_SETUP.md" ]; then
    echo -e "${GREEN}✅ PASS${NC}: README_TENANT_SETUP.md exists"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: README_TENANT_SETUP.md not found"
    ((TESTS_FAILED++))
fi

# Summary
echo ""
echo "========================================"
echo "VALIDATION SUMMARY"
echo "========================================"
echo "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo "Tests failed: ${RED}$TESTS_FAILED${NC}"
else
    echo "Tests failed: ${GREEN}$TESTS_FAILED${NC}"
fi
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ QUICK VALIDATION PASSED${NC}"
    echo ""
    echo "File-level validation complete!"
    echo "Schema separation appears to be correct."
    echo ""
    echo "Next steps:"
    echo "  1. To test with a real database, run:"
    echo "     ./migrations/run_schema_tests.sh"
    echo ""
    echo "  2. Or manually apply to your database:"
    echo "     psql -f postgres_unified_schema.sql"
    echo "     python migrations/apply_delta_seed_data.py --verify"
    exit 0
else
    echo -e "${RED}❌ VALIDATION FAILED${NC}"
    echo ""
    echo "Some file-level checks failed."
    echo "Please review the failures above."
    exit 1
fi
