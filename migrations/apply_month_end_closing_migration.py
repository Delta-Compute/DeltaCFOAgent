"""
Apply Month-End Closing Tables Migration

Applies the add_month_end_closing_tables.sql migration to the PostgreSQL database.
Creates tables for accounting period management, closing checklists, adjusting entries,
and audit logging.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web_ui.database import db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_tables_exist():
    """Check if the month-end closing tables already exist."""
    tables = [
        'cfo_accounting_periods',
        'close_checklist_templates',
        'close_checklist_items',
        'close_adjusting_entries',
        'close_activity_log',
        'period_locks'
    ]

    existing = []
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            for table in tables:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = %s
                    )
                """, (table,))
                if cursor.fetchone()[0]:
                    existing.append(table)
            cursor.close()
    except Exception as e:
        logger.warning(f"Could not check existing tables: {e}")

    return existing


def apply_migration(force=False):
    """Apply the month-end closing tables migration."""
    try:
        # Check if tables already exist
        existing = check_tables_exist()
        if existing and not force:
            logger.info("The following tables already exist:")
            for table in existing:
                logger.info(f"  - {table}")
            logger.info("")
            logger.info("Use --force to re-run migration (may cause errors if tables exist)")
            return True

        # Read the migration file
        migration_file = os.path.join(os.path.dirname(__file__), 'add_month_end_closing_tables.sql')

        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        logger.info("Applying month-end closing tables migration...")

        # Use db_manager's connection context manager
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Execute the entire SQL script
            cursor.execute(sql)
            conn.commit()

            cursor.close()

            logger.info("=" * 60)
            logger.info("Month-End Closing Migration Applied Successfully!")
            logger.info("=" * 60)
            logger.info("Created tables:")
            logger.info("  - cfo_accounting_periods: Period tracking with status")
            logger.info("  - close_checklist_templates: Reusable checklist templates")
            logger.info("  - close_checklist_items: Period-specific checklist instances")
            logger.info("  - close_adjusting_entries: Adjustment entries with approval")
            logger.info("  - close_activity_log: Audit trail for close activities")
            logger.info("  - period_locks: Granular locking (A/P, A/R, Payroll, All)")
            logger.info("")
            logger.info("Default checklist templates created (12 items)")
            logger.info("Indexes and triggers configured for optimal performance")
            logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def verify_migration():
    """Verify that all tables were created correctly."""
    tables = [
        'cfo_accounting_periods',
        'close_checklist_templates',
        'close_checklist_items',
        'close_adjusting_entries',
        'close_activity_log',
        'period_locks'
    ]

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            logger.info("Verifying migration...")
            all_exist = True

            for table in tables:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = %s
                    )
                """, (table,))
                exists = cursor.fetchone()[0]
                status = "OK" if exists else "MISSING"
                logger.info(f"  {table}: {status}")
                if not exists:
                    all_exist = False

            # Check default templates
            cursor.execute("SELECT COUNT(*) FROM close_checklist_templates WHERE tenant_id = 'default'")
            template_count = cursor.fetchone()[0]
            logger.info(f"  Default templates: {template_count}")

            cursor.close()

            if all_exist:
                logger.info("")
                logger.info("All tables verified successfully!")
            else:
                logger.error("Some tables are missing. Please run the migration again.")

            return all_exist

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Apply Month-End Closing Migration')
    parser.add_argument('--force', action='store_true', help='Force re-run even if tables exist')
    parser.add_argument('--verify', action='store_true', help='Only verify tables exist')
    args = parser.parse_args()

    if args.verify:
        success = verify_migration()
    else:
        success = apply_migration(force=args.force)
        if success:
            verify_migration()

    sys.exit(0 if success else 1)
