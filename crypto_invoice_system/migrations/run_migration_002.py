#!/usr/bin/env python3
"""
Migration Script: Add performance indexes
Runs migration 002_add_performance_indexes.sql
"""

import sys
import os
from pathlib import Path

# Add parent directories to path
current_dir = Path(__file__).parent.parent.parent
sys.path.append(str(current_dir / 'web_ui'))

from database import db_manager


def run_migration():
    """Run migration to add performance indexes"""

    print("=" * 80)
    print("MIGRATION 002: Add Performance Indexes")
    print("=" * 80)

    # Read migration SQL
    migration_path = Path(__file__).parent / '002_add_performance_indexes.sql'

    if not migration_path.exists():
        print(f"❌ Migration file not found: {migration_path}")
        return False

    with open(migration_path, 'r') as f:
        sql = f.read()

    # Split into individual statements
    statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]

    print(f"\n📋 Found {len(statements)} SQL statements to execute\n")

    try:
        for i, statement in enumerate(statements, 1):
            # Log what we're doing
            if statement.startswith('CREATE INDEX'):
                # Extract index name for better logging
                if 'idx_crypto_' in statement:
                    idx_name = statement.split('idx_crypto_')[1].split()[0] if 'idx_crypto_' in statement else 'unknown'
                    print(f"  [{i}/{len(statements)}] Creating index: idx_crypto_{idx_name}...")
            elif statement.startswith('COMMENT'):
                pass  # Skip logging comments
            elif statement.startswith('ANALYZE'):
                table = statement.split('ANALYZE')[1].strip() if 'ANALYZE' in statement else ''
                print(f"  [{i}/{len(statements)}] Analyzing table: {table}...")

            # Execute statement
            db_manager.execute_query(statement + ';')

        print("\n✅ Migration completed successfully!")
        print("\nIndexes created:")
        print("\n  Invoice Table:")
        print("    • idx_crypto_invoices_invoice_number (invoice number search)")
        print("    • idx_crypto_invoices_status (status filtering)")
        print("    • idx_crypto_invoices_client (client filtering)")
        print("    • idx_crypto_invoices_created_at (creation date sorting)")
        print("    • idx_crypto_invoices_issue_date (issue date sorting)")
        print("    • idx_crypto_invoices_due_date (due date filtering)")
        print("    • idx_crypto_invoices_paid_at (payment date sorting)")
        print("\n  Composite Indexes:")
        print("    • idx_crypto_invoices_status_created (pending invoices by date)")
        print("    • idx_crypto_invoices_client_status (client invoices by status)")
        print("    • idx_crypto_invoices_status_due (overdue detection)")
        print("\n  Other Tables:")
        print("    • idx_crypto_clients_name (client name search)")
        print("    • idx_crypto_payments_* (payment lookups)")
        print("    • idx_crypto_polling_* (polling log queries)")
        print("    • idx_crypto_notifications_* (notification queries)")
        print("\n" + "=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nPlease check:")
        print("  1. Database connection is working")
        print("  2. You have permission to CREATE INDEX")
        print("  3. Tables exist (run migration 001 first if needed)")
        return False


def verify_migration():
    """Verify that indexes were created"""
    print("\n🔍 Verifying migration...")

    try:
        # Query to check if indexes exist
        query = """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename LIKE 'crypto_%'
            AND indexname LIKE 'idx_crypto_%'
            ORDER BY indexname;
        """

        result = db_manager.execute_query(query, fetch_all=True)

        if result:
            print(f"✅ Found {len(result)} indexes created")
            print("\nIndexes:")
            for row in result[:10]:  # Show first 10
                print(f"  • {row['indexname']}")
            if len(result) > 10:
                print(f"  ... and {len(result) - 10} more")
            return True
        else:
            print("❌ No indexes found")
            return False

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def show_index_stats():
    """Show index usage statistics"""
    print("\n📊 Index Statistics:")

    try:
        query = """
            SELECT
                tablename,
                indexname,
                pg_size_pretty(pg_relation_size(indexname::regclass)) as size
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename LIKE 'crypto_%'
            AND indexname LIKE 'idx_crypto_%'
            ORDER BY tablename, indexname;
        """

        result = db_manager.execute_query(query, fetch_all=True)

        if result:
            current_table = None
            for row in result:
                if row['tablename'] != current_table:
                    current_table = row['tablename']
                    print(f"\n  {current_table}:")
                print(f"    • {row['indexname']}: {row['size']}")
        else:
            print("  No statistics available")

    except Exception as e:
        print(f"  Could not retrieve statistics: {e}")


if __name__ == '__main__':
    print("\n🚀 Starting migration...\n")

    # Check database connection
    if db_manager.db_type != 'postgresql':
        print("⚠️  WARNING: Database is not PostgreSQL. Indexes may not be created correctly.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            sys.exit(0)

    print(f"Database type: {db_manager.db_type}")
    print(f"Creating performance indexes for crypto invoice system")

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

        # Show stats
        show_index_stats()

        print("\n✅ Migration complete and verified!\n")
        print("📖 See DATABASE_QUERY_OPTIMIZATION.md for query optimization guide\n")
        sys.exit(0)
    else:
        print("\n❌ Migration failed. Please check errors above.\n")
        sys.exit(1)
