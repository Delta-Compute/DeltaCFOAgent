"""
Apply Shareholder Equity Migration

Applies the add_shareholder_equity.sql migration to the PostgreSQL database.
Creates tables for shareholder tracking, equity contributions, and cap table management.
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
    """Apply the shareholder equity tables migration."""
    try:
        # Read the migration file
        migration_file = os.path.join(os.path.dirname(__file__), 'add_shareholder_equity.sql')

        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        logger.info("Applying shareholder equity migration...")

        # Use db_manager's connection context manager
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Execute the entire SQL script
            cursor.execute(sql)
            conn.commit()

            cursor.close()

            logger.info("=" * 60)
            logger.info("Shareholder Equity Migration Applied Successfully!")
            logger.info("=" * 60)
            logger.info("Created tables:")
            logger.info("  - shareholders: Shareholder information and ownership")
            logger.info("  - equity_contributions: Equity investments and cash contributions")
            logger.info("  - equity_events: Stock splits, buybacks, and corporate actions")
            logger.info("  - cap_table_snapshots: Historical capitalization records")
            logger.info("")
            logger.info("Created views:")
            logger.info("  - shareholder_ownership_summary")
            logger.info("  - share_class_distribution")
            logger.info("  - equity_contribution_timeline")
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
