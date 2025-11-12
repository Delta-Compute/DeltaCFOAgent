#!/usr/bin/env python3
"""
Apply Delta Tenant Seed Data

This script applies Delta-specific seed data to the database.
Should ONLY be run for the Delta tenant, not for new tenant onboarding.

Usage:
    python migrations/apply_delta_seed_data.py [options]

Options:
    --dry-run    : Show what would be executed without making changes
    --verify     : Verify data was loaded correctly
"""

import os
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from web_ui.database import db_manager


def apply_delta_seed_data(dry_run=False):
    """
    Apply Delta tenant seed data from SQL file

    Args:
        dry_run: If True, print SQL without executing

    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 60)
    print("DELTA TENANT SEED DATA APPLICATION")
    print("=" * 60)
    print()

    # Check if database is accessible
    health = db_manager.health_check()
    if health['status'] != 'healthy':
        print(f"❌ Database health check failed: {health.get('error')}")
        return False

    print(f"✅ Database connection: {health['db_type']}")
    print(f"   Response time: {health['response_time_ms']}ms")
    print()

    # Load SQL file
    sql_file = Path(__file__).parent / 'delta_tenant_seed_data.sql'

    if not sql_file.exists():
        print(f"❌ SQL file not found: {sql_file}")
        return False

    print(f"📄 Loading seed data from: {sql_file.name}")

    with open(sql_file, 'r') as f:
        sql_content = f.read()

    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN MODE - SQL that would be executed:")
        print("=" * 60)
        print(sql_content)
        print("=" * 60)
        print("\n⚠️  No changes were made (dry-run mode)")
        return True

    # Execute SQL
    print("\n🔄 Applying seed data...")

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Execute the SQL file
            cursor.execute(sql_content)

            conn.commit()
            cursor.close()

        print("✅ Seed data applied successfully!")
        return True

    except Exception as e:
        print(f"❌ Error applying seed data: {e}")
        return False


def verify_delta_data():
    """
    Verify that Delta seed data was loaded correctly

    Returns:
        bool: True if all data present, False otherwise
    """
    print("\n" + "=" * 60)
    print("VERIFYING DELTA SEED DATA")
    print("=" * 60)
    print()

    checks = []

    try:
        # Check tenant configuration
        result = db_manager.execute_query(
            "SELECT company_name FROM tenant_configuration WHERE tenant_id = 'delta'",
            fetch_one=True
        )
        tenant_exists = result is not None
        checks.append(('Tenant Configuration', tenant_exists))
        if tenant_exists:
            print(f"✅ Tenant Configuration: {result['company_name']}")
        else:
            print("❌ Tenant Configuration: NOT FOUND")

        # Check business entities
        result = db_manager.execute_query(
            "SELECT COUNT(*) as count FROM business_entities WHERE name LIKE '%Delta%' OR name LIKE '%MMIW%' OR name LIKE '%Infinity%'",
            fetch_one=True
        )
        entity_count = result['count'] if result else 0
        checks.append(('Business Entities', entity_count >= 6))
        print(f"{'✅' if entity_count >= 6 else '❌'} Business Entities: {entity_count} found (expected: 6)")

        # Check clients
        result = db_manager.execute_query(
            "SELECT COUNT(*) as count FROM clients WHERE name IN ('Alps Blockchain', 'Exos Capital', 'GM Data Centers', 'Other')",
            fetch_one=True
        )
        client_count = result['count'] if result else 0
        checks.append(('Crypto Invoice Clients', client_count >= 4))
        print(f"{'✅' if client_count >= 4 else '❌'} Crypto Invoice Clients: {client_count} found (expected: 4)")

        # Check wallet addresses
        result = db_manager.execute_query(
            "SELECT COUNT(*) as count FROM wallet_addresses WHERE tenant_id = 'delta'",
            fetch_one=True
        )
        wallet_count = result['count'] if result else 0
        checks.append(('Wallet Addresses', wallet_count >= 3))
        print(f"{'✅' if wallet_count >= 3 else '❌'} Wallet Addresses: {wallet_count} found (expected: 3)")

        # Check bank accounts
        result = db_manager.execute_query(
            "SELECT COUNT(*) as count FROM bank_accounts WHERE tenant_id = 'delta'",
            fetch_one=True
        )
        bank_count = result['count'] if result else 0
        checks.append(('Bank Accounts', bank_count >= 3))
        print(f"{'✅' if bank_count >= 3 else '❌'} Bank Accounts: {bank_count} found (expected: 3)")

        print()
        print("=" * 60)

        all_passed = all(check[1] for check in checks)
        if all_passed:
            print("✅ ALL CHECKS PASSED - Delta seed data is complete!")
        else:
            print("❌ SOME CHECKS FAILED - Delta seed data may be incomplete")

        print("=" * 60)

        return all_passed

    except Exception as e:
        print(f"❌ Error verifying data: {e}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Apply Delta tenant seed data to the database'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show SQL without executing'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify seed data after applying (or just verify if already applied)'
    )

    args = parser.parse_args()

    # If only verify flag, skip application
    if args.verify and not args.dry_run:
        # Check if data already exists
        result = db_manager.execute_query(
            "SELECT tenant_id FROM tenant_configuration WHERE tenant_id = 'delta'",
            fetch_one=True
        )
        if result:
            print("ℹ️  Delta seed data appears to be already loaded.")
            print("   Running verification only...\n")
            success = verify_delta_data()
            sys.exit(0 if success else 1)

    # Apply seed data
    success = apply_delta_seed_data(dry_run=args.dry_run)

    if not success:
        sys.exit(1)

    # Verify if requested
    if args.verify and not args.dry_run:
        success = verify_delta_data()
        sys.exit(0 if success else 1)

    print("\n✅ Done!")
    sys.exit(0)


if __name__ == '__main__':
    main()
