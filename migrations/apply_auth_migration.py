#!/usr/bin/env python3
"""
Apply Authentication Schema Migration

This script applies the authentication system database migration to PostgreSQL.
It creates all necessary tables, indexes, and constraints for the Firebase
authentication integration.

Usage:
    python migrations/apply_auth_migration.py [--dry-run] [--verbose]

Options:
    --dry-run    Print SQL without executing
    --verbose    Show detailed output
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from web_ui.database import db_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def read_migration_file() -> str:
    """Read the authentication migration SQL file."""
    migration_file = Path(__file__).parent / 'add_auth_tables.sql'

    if not migration_file.exists():
        raise FileNotFoundError(f"Migration file not found: {migration_file}")

    with open(migration_file, 'r') as f:
        return f.read()


def check_existing_tables() -> dict:
    """Check which tables already exist in the database."""
    tables_to_check = [
        'users',
        'tenant_users',
        'user_permissions',
        'user_invitations',
        'audit_log'
    ]

    existing_tables = {}

    for table in tables_to_check:
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """
        try:
            result = db_manager.execute_query(query, (table,))
            existing_tables[table] = result[0][0] if result else False
        except Exception as e:
            logger.warning(f"Error checking table {table}: {e}")
            existing_tables[table] = False

    return existing_tables


def check_tenant_configuration_columns() -> dict:
    """Check which auth columns exist in tenant_configuration table."""
    columns_to_check = [
        'created_by_user_id',
        'current_admin_user_id',
        'payment_owner',
        'payment_method_id',
        'subscription_status'
    ]

    existing_columns = {}

    for column in columns_to_check:
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'tenant_configuration'
                AND column_name = %s
            )
        """
        try:
            result = db_manager.execute_query(query, (column,))
            existing_columns[column] = result[0][0] if result else False
        except Exception as e:
            logger.warning(f"Error checking column {column}: {e}")
            existing_columns[column] = False

    return existing_columns


def apply_migration(dry_run=False, verbose=False) -> bool:
    """
    Apply the authentication migration.

    Args:
        dry_run: If True, print SQL without executing
        verbose: If True, show detailed output

    Returns:
        True if migration successful, False otherwise
    """
    try:
        # Read migration SQL
        logger.info("Reading migration file...")
        sql = read_migration_file()

        if verbose:
            logger.info(f"Migration SQL ({len(sql)} characters):")
            logger.info("=" * 60)
            logger.info(sql[:500] + "..." if len(sql) > 500 else sql)
            logger.info("=" * 60)

        # Check existing state
        logger.info("Checking existing database state...")
        existing_tables = check_existing_tables()
        existing_columns = check_tenant_configuration_columns()

        logger.info("\nCurrent database state:")
        logger.info("  Tables:")
        for table, exists in existing_tables.items():
            status = "EXISTS" if exists else "NOT FOUND"
            logger.info(f"    - {table}: {status}")

        logger.info("  Tenant configuration columns:")
        for column, exists in existing_columns.items():
            status = "EXISTS" if exists else "NOT FOUND"
            logger.info(f"    - {column}: {status}")

        if dry_run:
            logger.info("\n[DRY RUN] Would execute migration SQL")
            logger.info("Migration file: migrations/add_auth_tables.sql")
            return True

        # Confirm before proceeding
        if not dry_run:
            logger.info("\n" + "=" * 60)
            logger.warning("WARNING: This will modify your database schema!")
            logger.info("=" * 60)
            response = input("\nProceed with migration? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                logger.info("Migration cancelled by user")
                return False

        # Apply migration
        logger.info("\nApplying authentication schema migration...")

        # Get a connection and execute the migration
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(sql)
            conn.commit()
            logger.info("Migration executed successfully!")

        except Exception as e:
            conn.rollback()
            logger.error(f"Migration failed: {e}")
            raise

        finally:
            cursor.close()
            db_manager.close_connection(conn)

        # Verify migration
        logger.info("\nVerifying migration...")
        new_tables = check_existing_tables()
        new_columns = check_tenant_configuration_columns()

        logger.info("\nPost-migration state:")
        logger.info("  Tables:")
        for table, exists in new_tables.items():
            status = "EXISTS" if exists else "NOT FOUND"
            emoji = "✓" if exists else "✗"
            logger.info(f"    {emoji} {table}: {status}")

        logger.info("  Tenant configuration columns:")
        for column, exists in new_columns.items():
            status = "EXISTS" if exists else "NOT FOUND"
            emoji = "✓" if exists else "✗"
            logger.info(f"    {emoji} {column}: {status}")

        # Check for any failures
        all_tables_exist = all(new_tables.values())
        all_columns_exist = all(new_columns.values())

        if all_tables_exist and all_columns_exist:
            logger.info("\n" + "=" * 60)
            logger.info("SUCCESS: Authentication schema migration completed!")
            logger.info("=" * 60)
            logger.info("\nNext steps:")
            logger.info("  1. Configure Firebase credentials in .env")
            logger.info("  2. Create initial admin user")
            logger.info("  3. Test authentication endpoints")
            logger.info("  4. Deploy to production")
            return True
        else:
            logger.warning("\n" + "=" * 60)
            logger.warning("WARNING: Some tables or columns may not have been created")
            logger.warning("=" * 60)
            return False

    except FileNotFoundError as e:
        logger.error(f"Migration file not found: {e}")
        return False

    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        if verbose:
            import traceback
            logger.error(traceback.format_exc())
        return False


def rollback_migration(verbose=False) -> bool:
    """
    Rollback the authentication migration.

    WARNING: This will DROP all authentication tables and data!

    Args:
        verbose: If True, show detailed output

    Returns:
        True if rollback successful, False otherwise
    """
    logger.warning("\n" + "=" * 60)
    logger.warning("WARNING: ROLLBACK WILL DELETE ALL AUTHENTICATION DATA!")
    logger.warning("=" * 60)
    response = input("\nAre you ABSOLUTELY SURE you want to rollback? (type 'DELETE' to confirm): ")

    if response != 'DELETE':
        logger.info("Rollback cancelled")
        return False

    try:
        logger.info("Rolling back authentication migration...")

        rollback_sql = """
            -- Drop views
            DROP VIEW IF EXISTS v_pending_invitations CASCADE;
            DROP VIEW IF EXISTS v_active_tenant_users CASCADE;

            -- Drop triggers
            DROP TRIGGER IF EXISTS update_users_updated_at ON users;

            -- Drop functions
            DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;
            DROP FUNCTION IF EXISTS expire_old_invitations CASCADE;

            -- Drop tables
            DROP TABLE IF EXISTS audit_log CASCADE;
            DROP TABLE IF EXISTS user_invitations CASCADE;
            DROP TABLE IF EXISTS user_permissions CASCADE;
            DROP TABLE IF EXISTS tenant_users CASCADE;
            DROP TABLE IF EXISTS users CASCADE;

            -- Remove columns from tenant_configuration
            ALTER TABLE IF EXISTS tenant_configuration
                DROP COLUMN IF EXISTS created_by_user_id,
                DROP COLUMN IF EXISTS current_admin_user_id,
                DROP COLUMN IF EXISTS payment_owner,
                DROP COLUMN IF EXISTS payment_method_id,
                DROP COLUMN IF EXISTS subscription_status,
                DROP COLUMN IF EXISTS subscription_started_at,
                DROP COLUMN IF EXISTS subscription_ends_at;

            -- Drop enums
            DROP TYPE IF EXISTS invitation_status_enum CASCADE;
            DROP TYPE IF EXISTS subscription_status_enum CASCADE;
            DROP TYPE IF EXISTS payment_owner_enum CASCADE;
            DROP TYPE IF EXISTS user_role_enum CASCADE;
            DROP TYPE IF EXISTS user_type_enum CASCADE;
        """

        conn = db_manager.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(rollback_sql)
            conn.commit()
            logger.info("Rollback completed successfully!")
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Rollback failed: {e}")
            raise

        finally:
            cursor.close()
            db_manager.close_connection(conn)

    except Exception as e:
        logger.error(f"Rollback failed with error: {e}")
        if verbose:
            import traceback
            logger.error(traceback.format_exc())
        return False


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description='Apply authentication schema migration to PostgreSQL'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print SQL without executing'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed output'
    )
    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Rollback the migration (WARNING: Deletes all auth data!)'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("Delta CFO Agent - Authentication Migration")
    logger.info("=" * 60)

    # Check database connection
    logger.info("Checking database connection...")
    try:
        conn = db_manager.get_connection()
        db_manager.close_connection(conn)
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.error("Please check your database configuration in .env")
        sys.exit(1)

    # Execute rollback or migration
    if args.rollback:
        success = rollback_migration(verbose=args.verbose)
    else:
        success = apply_migration(dry_run=args.dry_run, verbose=args.verbose)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
