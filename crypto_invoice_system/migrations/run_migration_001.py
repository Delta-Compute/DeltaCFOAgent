#!/usr/bin/env python3
"""
Migration Script: Add new invoice fields
Runs migration 001_add_invoice_fields.sql
"""

import sys
import os
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent.parent.parent
sys.path.append(str(current_dir / 'web_ui'))

from database import db_manager


def run_migration():
    """Run migration to add new invoice fields"""

    print("=" * 80)
    print("MIGRATION 001: Add Invoice Fields")
    print("=" * 80)

    # Read migration SQL
    migration_path = Path(__file__).parent / '001_add_invoice_fields.sql'

    if not migration_path.exists():
        print(f"❌ Migration file not found: {migration_path}")
        return False

    with open(migration_path, 'r') as f:
        sql = f.read()

    # Split into individual statements (PostgreSQL can handle multiple in one query, but safer to split)
    statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

    print(f"\n📋 Found {len(statements)} SQL statements to execute\n")

    try:
        for i, statement in enumerate(statements, 1):
            # Skip comment-only statements
            if statement.startswith('COMMENT'):
                print(f"  [{i}/{len(statements)}] Adding column comment...")
            elif statement.startswith('ALTER TABLE'):
                # Extract column name for better logging
                if 'ADD COLUMN' in statement:
                    col_name = statement.split('ADD COLUMN')[1].split()[2] if len(statement.split('ADD COLUMN')) > 1 else 'unknown'
                    print(f"  [{i}/{len(statements)}] Adding column: {col_name}...")

            # Execute statement
            db_manager.execute_query(statement + ';')

        print("\n✅ Migration completed successfully!")
        print("\nNew fields added to crypto_invoices table:")
        print("  • transaction_fee_percent (DECIMAL)")
        print("  • tax_percent (DECIMAL)")
        print("  • rate_locked_until (TIMESTAMP)")
        print("  • expiration_hours (INTEGER)")
        print("  • allow_client_choice (BOOLEAN)")
        print("  • client_wallet_address (VARCHAR)")
        print("\n" + "=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nPlease check:")
        print("  1. Database connection is working")
        print("  2. You have permission to ALTER TABLE")
        print("  3. Columns don't already exist")
        return False


def verify_migration():
    """Verify that new columns exist"""
    print("\n🔍 Verifying migration...")

    try:
        # Try to query with new columns
        query = """
            SELECT
                transaction_fee_percent,
                tax_percent,
                rate_locked_until,
                expiration_hours,
                allow_client_choice,
                client_wallet_address
            FROM crypto_invoices
            LIMIT 1
        """

        result = db_manager.execute_query(query, fetch_one=True)
        print("✅ All new columns are accessible")
        return True

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


if __name__ == '__main__':
    print("\n🚀 Starting migration...\n")

    # Check database connection
    if db_manager.db_type != 'postgresql':
        print("⚠️  WARNING: Database is not PostgreSQL. Migration may not work correctly.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            sys.exit(0)

    print(f"Database type: {db_manager.db_type}")
    print(f"Target table: crypto_invoices")

    # Confirm before running
    response = input("\nRun migration? (y/n): ")
    if response.lower() != 'y':
        print("Migration cancelled.")
        sys.exit(0)

    # Run migration
    success = run_migration()

    if success:
        # Verify
        verify_migration()
        print("\n✅ Migration complete and verified!\n")
        sys.exit(0)
    else:
        print("\n❌ Migration failed. Please check errors above.\n")
        sys.exit(1)
