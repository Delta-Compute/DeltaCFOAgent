"""
Apply Business Entities Multi-Tenant Migration

Safely migrates business_entities table to support multi-tenant isolation.
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web_ui.database import db_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def apply_migration():
    """Apply the business entities multi-tenant migration."""
    try:
        migration_file = os.path.join(os.path.dirname(__file__), 'fix_business_entities_multi_tenant.sql')

        logger.info("=" * 80)
        logger.info("APPLYING BUSINESS_ENTITIES MULTI-TENANT MIGRATION")
        logger.info("=" * 80)

        # Read the migration file
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql = f.read()

        logger.info("\n[1/3] Reading migration SQL...")
        logger.info(f"[OK] Migration file loaded: {migration_file}")

        logger.info("\n[2/3] Executing migration...")

        # Use db_manager's connection
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Execute the migration
            cursor.execute(sql)
            conn.commit()

            cursor.close()

        logger.info("[OK] Migration executed successfully!")

        logger.info("\n[3/3] Verifying changes...")

        # Verify tenant_id column exists
        result = db_manager.execute_query("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'business_entities'
            AND column_name = 'tenant_id'
        """, fetch_one=True)

        if result:
            logger.info(f"[OK] tenant_id column added: {result['data_type']}, NOT NULL: {result['is_nullable'] == 'NO'}")
        else:
            logger.error("[ERROR] tenant_id column not found!")
            return False

        # Verify constraint exists
        constraint_result = db_manager.execute_query("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'business_entities'
            AND constraint_name = 'business_entities_tenant_name_unique'
        """, fetch_one=True)

        if constraint_result:
            logger.info(f"[OK] Unique constraint added: {constraint_result['constraint_name']}")
        else:
            logger.warning("[WARNING] Unique constraint not found - may already exist")

        # Show sample data
        sample_entities = db_manager.execute_query("""
            SELECT id, tenant_id, name, entity_type, active
            FROM business_entities
            LIMIT 5
        """, fetch_all=True)

        if sample_entities:
            logger.info("\n[OK] Sample entities with tenant_id:")
            for entity in sample_entities:
                logger.info(f"  - {entity['name']} (tenant: {entity['tenant_id']}, active: {entity['active']})")
        else:
            logger.info("\n[INFO] No entities in database yet")

        logger.info("\n" + "=" * 80)
        logger.info("MIGRATION COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        logger.info("\nNext steps:")
        logger.info("1. Update application code to include tenant_id in all entity queries")
        logger.info("2. Test entity creation with new tenant_id column")
        logger.info("3. Verify entities appear in filters and classifications")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"\n[ERROR] Migration failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    success = apply_migration()
    sys.exit(0 if success else 1)
