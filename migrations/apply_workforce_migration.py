"""
Apply Workforce Tables Migration

Applies the add_workforce_tables.sql migration to the PostgreSQL database.
Creates tables for workforce management, payslips, and payslip-transaction matching.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web_ui.database import db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def apply_migration():
    """Apply the workforce tables migration."""
    try:
        # Read the migration file
        migration_file = os.path.join(os.path.dirname(__file__), 'add_workforce_tables.sql')

        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        logger.info("Applying workforce tables migration...")

        # Use db_manager's connection context manager
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Execute the entire SQL script
            cursor.execute(sql)
            conn.commit()

            cursor.close()

            logger.info("=" * 60)
            logger.info("Workforce Management Migration Applied Successfully!")
            logger.info("=" * 60)
            logger.info("Created tables:")
            logger.info("  - workforce_members: Employee and contractor records")
            logger.info("  - payslips: Payslip records with payment details")
            logger.info("  - pending_payslip_matches: Transaction matching")
            logger.info("  - payslip_match_log: Match action audit trail")
            logger.info("")
            logger.info("Indexes and triggers configured for optimal performance")
            logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    success = apply_migration()
    sys.exit(0 if success else 1)
