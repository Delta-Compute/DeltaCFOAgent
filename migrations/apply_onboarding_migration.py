"""
Apply Onboarding Tables Migration

Applies the add_onboarding_tables.sql migration to the PostgreSQL database.
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web_ui.database import db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def apply_migration():
    """Apply the onboarding tables migration."""
    try:
        # Read the migration file
        migration_file = os.path.join(os.path.dirname(__file__), 'add_onboarding_tables.sql')

        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        logger.info("Applying onboarding tables migration...")

        # Use db_manager's connection context manager
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Execute the entire SQL script
            cursor.execute(sql)
            conn.commit()

            cursor.close()

            logger.info("Migration applied successfully!")
            logger.info("Created tables:")
            logger.info("  - custom_categories: For tenant-specific chart of accounts")
            logger.info("  - tenant_onboarding_status: For tracking onboarding progress")

        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    success = apply_migration()
    sys.exit(0 if success else 1)
