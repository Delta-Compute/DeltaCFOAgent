#!/bin/bash
# Automated test suite for schema separation
# Tests that Delta-specific seed data has been properly separated from the main schema

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TEST_DB_NAME="deltacfo_test_$(date +%s)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Database connection parameters (can be overridden by environment variables)
DB_HOST="${TEST_DB_HOST:-localhost}"
DB_PORT="${TEST_DB_PORT:-5432}"
DB_USER="${TEST_DB_USER:-postgres}"
DB_PASSWORD="${TEST_DB_PASSWORD:-}"

# Set PGPASSWORD for non-interactive execution
export PGPASSWORD="$DB_PASSWORD"

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
print_test() {
    echo ""
    echo "========================================"
    echo "TEST $1: $2"
    echo "========================================"
}

pass_test() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    ((TESTS_PASSED++))
    ((TESTS_RUN++))
}

fail_test() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    ((TESTS_FAILED++))
    ((TESTS_RUN++))
}

info() {
    echo -e "${YELLOW}ℹ️  INFO${NC}: $1"
}

# Cleanup function
cleanup() {
    echo ""
    echo "========================================"
    echo "CLEANING UP"
    echo "========================================"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "DROP DATABASE IF EXISTS $TEST_DB_NAME;" 2>/dev/null || true
    echo "✅ Test database cleaned up"
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Main test execution
main() {
    echo "========================================"
    echo "SCHEMA SEPARATION TEST SUITE"
    echo "========================================"
    echo "Database: $DB_HOST:$DB_PORT"
    echo "Test DB: $TEST_DB_NAME"
    echo ""

    # Test database connectivity
    info "Testing database connectivity..."
    if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "SELECT 1;" > /dev/null 2>&1; then
        echo -e "${RED}❌ ERROR${NC}: Cannot connect to database"
        echo "Please check:"
        echo "  - Database is running"
        echo "  - Credentials are correct (TEST_DB_HOST, TEST_DB_USER, TEST_DB_PASSWORD)"
        exit 1
    fi
    echo "✅ Database connection successful"

    # Create test database
    print_test "0" "Database Setup"
    info "Creating test database: $TEST_DB_NAME"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $TEST_DB_NAME;" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        pass_test "Test database created"
    else
        fail_test "Could not create test database"
        exit 1
    fi

    # Test 1: Clean schema application
    print_test "1" "Clean Schema Installation (No Delta Data)"
    info "Applying postgres_unified_schema.sql..."

    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -f "$PROJECT_ROOT/postgres_unified_schema.sql" > /dev/null 2>&1; then
        pass_test "Schema applied successfully"
    else
        fail_test "Schema application failed"
        exit 1
    fi

    # Check for Delta entities (should be 0)
    DELTA_ENTITIES=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -t -c \
        "SELECT COUNT(*) FROM business_entities WHERE name LIKE '%Delta%' OR name LIKE '%MMIW%' OR name LIKE '%Infinity%';")
    DELTA_ENTITIES=$(echo $DELTA_ENTITIES | tr -d ' ')

    if [ "$DELTA_ENTITIES" -eq "0" ]; then
        pass_test "No Delta entities in clean schema (found: $DELTA_ENTITIES)"
    else
        fail_test "Found $DELTA_ENTITIES Delta entities (expected: 0)"
    fi

    # Check for Delta clients (should be 0)
    DELTA_CLIENTS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -t -c \
        "SELECT COUNT(*) FROM clients WHERE name IN ('Alps Blockchain', 'Exos Capital', 'GM Data Centers');")
    DELTA_CLIENTS=$(echo $DELTA_CLIENTS | tr -d ' ')

    if [ "$DELTA_CLIENTS" -eq "0" ]; then
        pass_test "No Delta clients in clean schema (found: $DELTA_CLIENTS)"
    else
        fail_test "Found $DELTA_CLIENTS Delta clients (expected: 0)"
    fi

    # Check for Delta tenant config (should be 0)
    DELTA_TENANT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -t -c \
        "SELECT COUNT(*) FROM tenant_configuration WHERE tenant_id = 'delta';")
    DELTA_TENANT=$(echo $DELTA_TENANT | tr -d ' ')

    if [ "$DELTA_TENANT" -eq "0" ]; then
        pass_test "No Delta tenant config in clean schema (found: $DELTA_TENANT)"
    else
        fail_test "Found $DELTA_TENANT Delta tenant configs (expected: 0)"
    fi

    # Check for Delta wallets (should be 0)
    DELTA_WALLETS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -t -c \
        "SELECT COUNT(*) FROM wallet_addresses WHERE tenant_id = 'delta';")
    DELTA_WALLETS=$(echo $DELTA_WALLETS | tr -d ' ')

    if [ "$DELTA_WALLETS" -eq "0" ]; then
        pass_test "No Delta wallets in clean schema (found: $DELTA_WALLETS)"
    else
        fail_test "Found $DELTA_WALLETS Delta wallets (expected: 0)"
    fi

    # Check for Delta bank accounts (should be 0)
    DELTA_BANKS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -t -c \
        "SELECT COUNT(*) FROM bank_accounts WHERE tenant_id = 'delta';")
    DELTA_BANKS=$(echo $DELTA_BANKS | tr -d ' ')

    if [ "$DELTA_BANKS" -eq "0" ]; then
        pass_test "No Delta bank accounts in clean schema (found: $DELTA_BANKS)"
    else
        fail_test "Found $DELTA_BANKS Delta bank accounts (expected: 0)"
    fi

    # Check that system config WAS inserted (should be 6)
    SYSTEM_CONFIG=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -t -c \
        "SELECT COUNT(*) FROM system_config;")
    SYSTEM_CONFIG=$(echo $SYSTEM_CONFIG | tr -d ' ')

    if [ "$SYSTEM_CONFIG" -eq "6" ]; then
        pass_test "System config inserted correctly (found: $SYSTEM_CONFIG)"
    else
        fail_test "Found $SYSTEM_CONFIG system configs (expected: 6)"
    fi

    # Test 2: Delta seed data application
    print_test "2" "Delta Seed Data Application"
    info "Applying migrations/delta_tenant_seed_data.sql..."

    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -f "$SCRIPT_DIR/delta_tenant_seed_data.sql" > /dev/null 2>&1; then
        pass_test "Delta seed data applied successfully"
    else
        fail_test "Delta seed data application failed"
    fi

    # Check for Delta entities (should be 6)
    DELTA_ENTITIES=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -t -c \
        "SELECT COUNT(*) FROM business_entities WHERE name LIKE '%Delta%' OR name LIKE '%MMIW%' OR name LIKE '%Infinity%';")
    DELTA_ENTITIES=$(echo $DELTA_ENTITIES | tr -d ' ')

    if [ "$DELTA_ENTITIES" -eq "6" ]; then
        pass_test "Delta entities inserted (found: $DELTA_ENTITIES)"
    else
        fail_test "Found $DELTA_ENTITIES Delta entities (expected: 6)"
    fi

    # Check for Delta clients (should be 4)
    DELTA_CLIENTS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -t -c \
        "SELECT COUNT(*) FROM clients WHERE name IN ('Alps Blockchain', 'Exos Capital', 'GM Data Centers', 'Other');")
    DELTA_CLIENTS=$(echo $DELTA_CLIENTS | tr -d ' ')

    if [ "$DELTA_CLIENTS" -eq "4" ]; then
        pass_test "Delta clients inserted (found: $DELTA_CLIENTS)"
    else
        fail_test "Found $DELTA_CLIENTS Delta clients (expected: 4)"
    fi

    # Check for Delta tenant config (should be 1)
    DELTA_TENANT=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -t -c \
        "SELECT COUNT(*) FROM tenant_configuration WHERE tenant_id = 'delta';")
    DELTA_TENANT=$(echo $DELTA_TENANT | tr -d ' ')

    if [ "$DELTA_TENANT" -eq "1" ]; then
        pass_test "Delta tenant config inserted (found: $DELTA_TENANT)"
    else
        fail_test "Found $DELTA_TENANT Delta tenant configs (expected: 1)"
    fi

    # Check for Delta wallets (should be 3)
    DELTA_WALLETS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -t -c \
        "SELECT COUNT(*) FROM wallet_addresses WHERE tenant_id = 'delta';")
    DELTA_WALLETS=$(echo $DELTA_WALLETS | tr -d ' ')

    if [ "$DELTA_WALLETS" -eq "3" ]; then
        pass_test "Delta wallets inserted (found: $DELTA_WALLETS)"
    else
        fail_test "Found $DELTA_WALLETS Delta wallets (expected: 3)"
    fi

    # Check for Delta bank accounts (should be 3)
    DELTA_BANKS=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -t -c \
        "SELECT COUNT(*) FROM bank_accounts WHERE tenant_id = 'delta';")
    DELTA_BANKS=$(echo $DELTA_BANKS | tr -d ' ')

    if [ "$DELTA_BANKS" -eq "3" ]; then
        pass_test "Delta bank accounts inserted (found: $DELTA_BANKS)"
    else
        fail_test "Found $DELTA_BANKS Delta bank accounts (expected: 3)"
    fi

    # Test 3: Idempotency
    print_test "3" "Idempotency Test"
    info "Re-applying Delta seed data..."

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -f "$SCRIPT_DIR/delta_tenant_seed_data.sql" > /dev/null 2>&1

    # Check counts haven't changed
    DELTA_ENTITIES_AFTER=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -t -c \
        "SELECT COUNT(*) FROM business_entities WHERE name LIKE '%Delta%' OR name LIKE '%MMIW%' OR name LIKE '%Infinity%';")
    DELTA_ENTITIES_AFTER=$(echo $DELTA_ENTITIES_AFTER | tr -d ' ')

    if [ "$DELTA_ENTITIES_AFTER" -eq "6" ]; then
        pass_test "Idempotency verified - no duplicate entities (still: 6)"
    else
        fail_test "Duplicate entities created: $DELTA_ENTITIES_AFTER (expected: 6)"
    fi

    DELTA_CLIENTS_AFTER=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" -t -c \
        "SELECT COUNT(*) FROM clients WHERE name IN ('Alps Blockchain', 'Exos Capital', 'GM Data Centers', 'Other');")
    DELTA_CLIENTS_AFTER=$(echo $DELTA_CLIENTS_AFTER | tr -d ' ')

    if [ "$DELTA_CLIENTS_AFTER" -eq "4" ]; then
        pass_test "Idempotency verified - no duplicate clients (still: 4)"
    else
        fail_test "Duplicate clients created: $DELTA_CLIENTS_AFTER (expected: 4)"
    fi

    # Print summary
    echo ""
    echo "========================================"
    echo "TEST SUMMARY"
    echo "========================================"
    echo "Tests run:    $TESTS_RUN"
    echo -e "${GREEN}Tests passed: $TESTS_PASSED${NC}"
    if [ $TESTS_FAILED -gt 0 ]; then
        echo -e "${RED}Tests failed: $TESTS_FAILED${NC}"
    else
        echo -e "${GREEN}Tests failed: $TESTS_FAILED${NC}"
    fi
    echo ""

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
        echo "Schema separation is working correctly!"
        return 0
    else
        echo -e "${RED}❌ SOME TESTS FAILED${NC}"
        echo "Please review the failures above."
        return 1
    fi
}

# Run main function
main
exit $?
