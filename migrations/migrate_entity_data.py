#!/usr/bin/env python3
"""
Entity Data Migration Script
Migrates existing VARCHAR entity data to new entities and business_lines tables

This script:
1. Extracts unique entity names from transactions table per tenant
2. Creates entity records in entities table
3. Creates default business line for each entity
4. Updates transactions.entity_id with FK references
5. Validates migration success

Author: Claude Code
Date: 2024-11-24
"""

import os
import sys
import argparse
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_ui.database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Delta-Specific Entity Mapping
# ============================================================================

DELTA_ENTITY_MAPPING = {
    'Delta LLC': {
        'code': 'DLLC',
        'legal_name': 'Delta Mining LLC',
        'tax_jurisdiction': 'US-Delaware',
        'entity_type': 'LLC',
        'base_currency': 'USD',
        'country_code': 'US',
        'business_lines': [
            {'code': 'ADMIN', 'name': 'Corporate/Admin', 'is_default': True},
            {'code': 'INVEST', 'name': 'Investment Activities', 'is_default': False}
        ]
    },
    'Delta Paraguay': {
        'code': 'DPY',
        'legal_name': 'Delta Mining Paraguay S.A.',
        'tax_jurisdiction': 'Paraguay',
        'entity_type': 'S.A.',
        'base_currency': 'USD',
        'country_code': 'PY',
        'business_lines': [
            {'code': 'HOST', 'name': 'Hosting Services', 'is_default': True},
            {'code': 'ENERGY', 'name': 'Energy Operations', 'is_default': False},
            {'code': 'INFRA', 'name': 'Infrastructure', 'is_default': False}
        ]
    },
    'Delta Brazil': {
        'code': 'DBR',
        'legal_name': 'Delta Mining Brazil Ltda',
        'tax_jurisdiction': 'Brazil',
        'entity_type': 'Ltda',
        'base_currency': 'USD',
        'country_code': 'BR',
        'business_lines': [
            {'code': 'COLO', 'name': 'Colocation Services', 'is_default': True},
            {'code': 'LOCAL', 'name': 'Local Operations', 'is_default': False}
        ]
    },
    'Delta Prop Shop': {
        'code': 'DPS',
        'legal_name': 'Delta Prop Shop LLC',
        'tax_jurisdiction': 'US-Delaware',
        'entity_type': 'LLC',
        'base_currency': 'USD',
        'country_code': 'US',
        'business_lines': [
            {'code': 'TAOSHI', 'name': 'Taoshi Contract', 'is_default': True},
            {'code': 'MINER', 'name': 'Miner Reward Splits', 'is_default': False},
            {'code': 'MARKET', 'name': 'Marketplace Fees', 'is_default': False}
        ]
    },
    'Delta Infinity': {
        'code': 'DIN',
        'legal_name': 'Delta Infinity LLC',
        'tax_jurisdiction': 'US-Delaware',
        'entity_type': 'LLC',
        'base_currency': 'USD',
        'country_code': 'US',
        'business_lines': [
            {'code': 'VAL', 'name': 'Validator Operations', 'is_default': True},
            {'code': 'JV', 'name': 'JV Revenue Share', 'is_default': False}
        ]
    }
}


class EntityMigration:
    """Handles migration of entity data from VARCHAR to new structure"""

    def __init__(self, db_manager: DatabaseManager, dry_run: bool = False):
        self.db = db_manager
        self.dry_run = dry_run
        self.entity_map = {}  # Maps (tenant_id, old_entity_name) -> new entity_id

    def get_unique_entities_per_tenant(self) -> Dict[str, List[str]]:
        """Extract unique entity names from transactions table per tenant"""
        logger.info("Extracting unique entities from transactions table...")

        query = """
        SELECT DISTINCT tenant_id, entity
        FROM transactions
        WHERE entity IS NOT NULL AND entity != ''
        ORDER BY tenant_id, entity
        """

        results = self.db.execute_query(query)

        # Group by tenant_id
        entities_by_tenant = {}
        for row in results:
            tenant_id = row[0]
            entity_name = row[1]

            if tenant_id not in entities_by_tenant:
                entities_by_tenant[tenant_id] = []

            entities_by_tenant[tenant_id].append(entity_name)

        # Log summary
        for tenant_id, entities in entities_by_tenant.items():
            logger.info(f"Tenant '{tenant_id}': {len(entities)} unique entities")
            for entity in entities:
                logger.info(f"  - {entity}")

        return entities_by_tenant

    def create_entity(
        self,
        tenant_id: str,
        name: str,
        code: str,
        legal_name: Optional[str] = None,
        tax_jurisdiction: Optional[str] = None,
        entity_type: Optional[str] = None,
        base_currency: str = 'USD',
        country_code: Optional[str] = None
    ) -> Optional[str]:
        """Create a new entity record and return its UUID"""

        logger.info(f"Creating entity: {name} (code: {code}) for tenant: {tenant_id}")

        if self.dry_run:
            logger.info("[DRY RUN] Would create entity")
            return f"mock-uuid-{code}"

        query = """
        INSERT INTO entities (
            tenant_id, code, name, legal_name, tax_jurisdiction,
            entity_type, base_currency, country_code, is_active, created_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (tenant_id, code) DO UPDATE
        SET name = EXCLUDED.name,
            legal_name = EXCLUDED.legal_name,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """

        params = (
            tenant_id,
            code,
            name,
            legal_name or name,
            tax_jurisdiction,
            entity_type,
            base_currency,
            country_code,
            True,  # is_active
            'migration_script'
        )

        result = self.db.execute_query(query, params)

        if result and len(result) > 0:
            entity_id = str(result[0][0])
            logger.info(f"✓ Entity created with ID: {entity_id}")
            return entity_id
        else:
            logger.error(f"✗ Failed to create entity: {name}")
            return None

    def create_business_line(
        self,
        entity_id: str,
        code: str,
        name: str,
        is_default: bool = False,
        color_hex: Optional[str] = None
    ) -> Optional[str]:
        """Create a business line for an entity"""

        logger.info(f"Creating business line: {name} (code: {code}) for entity: {entity_id}")

        if self.dry_run:
            logger.info("[DRY RUN] Would create business line")
            return f"mock-bl-uuid-{code}"

        query = """
        INSERT INTO business_lines (
            entity_id, code, name, is_default, color_hex, is_active, created_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (entity_id, code) DO UPDATE
        SET name = EXCLUDED.name,
            is_default = EXCLUDED.is_default,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """

        params = (
            entity_id,
            code,
            name,
            is_default,
            color_hex,
            True,  # is_active
            'migration_script'
        )

        result = self.db.execute_query(query, params)

        if result and len(result) > 0:
            bl_id = str(result[0][0])
            logger.info(f"✓ Business line created with ID: {bl_id}")
            return bl_id
        else:
            logger.error(f"✗ Failed to create business line: {name}")
            return None

    def migrate_delta_entities(self) -> bool:
        """Migrate Delta tenant entities with specific mapping"""
        logger.info("=" * 80)
        logger.info("Migrating Delta tenant entities...")
        logger.info("=" * 80)

        tenant_id = 'delta'

        for old_name, config in DELTA_ENTITY_MAPPING.items():
            # Create entity
            entity_id = self.create_entity(
                tenant_id=tenant_id,
                name=old_name,  # Keep original name for backward compatibility
                code=config['code'],
                legal_name=config['legal_name'],
                tax_jurisdiction=config['tax_jurisdiction'],
                entity_type=config['entity_type'],
                base_currency=config['base_currency'],
                country_code=config['country_code']
            )

            if not entity_id:
                logger.error(f"Failed to create entity: {old_name}")
                return False

            # Store mapping
            self.entity_map[(tenant_id, old_name)] = entity_id

            # Create business lines
            for bl_config in config['business_lines']:
                bl_id = self.create_business_line(
                    entity_id=entity_id,
                    code=bl_config['code'],
                    name=bl_config['name'],
                    is_default=bl_config['is_default']
                )

                if not bl_id:
                    logger.error(f"Failed to create business line: {bl_config['name']}")
                    return False

        logger.info(f"✓ Delta entities migrated successfully")
        return True

    def migrate_generic_tenant_entities(self, tenant_id: str, entity_names: List[str]) -> bool:
        """Migrate entities for non-Delta tenants (generic mapping)"""
        logger.info("=" * 80)
        logger.info(f"Migrating entities for tenant: {tenant_id}")
        logger.info("=" * 80)

        for entity_name in entity_names:
            # Generate code from name (first 4 letters, uppercase)
            code = entity_name.replace(' ', '')[:4].upper()

            # Create entity
            entity_id = self.create_entity(
                tenant_id=tenant_id,
                name=entity_name,
                code=code,
                legal_name=entity_name,
                base_currency='USD'  # Default to USD
            )

            if not entity_id:
                logger.error(f"Failed to create entity: {entity_name}")
                return False

            # Store mapping
            self.entity_map[(tenant_id, entity_name)] = entity_id

            # Create default business line (hidden until user adds second)
            bl_id = self.create_business_line(
                entity_id=entity_id,
                code='DEFAULT',
                name='Default',
                is_default=True
            )

            if not bl_id:
                logger.error(f"Failed to create default business line for: {entity_name}")
                return False

        logger.info(f"✓ Entities migrated for tenant: {tenant_id}")
        return True

    def update_transaction_entity_ids(self) -> bool:
        """Update transactions.entity_id to reference new entities table"""
        logger.info("=" * 80)
        logger.info("Updating transaction entity_id references...")
        logger.info("=" * 80)

        if self.dry_run:
            logger.info("[DRY RUN] Would update transaction entity_id references")
            return True

        # Update transactions for each mapped entity
        for (tenant_id, old_entity_name), entity_id in self.entity_map.items():
            logger.info(f"Updating transactions: tenant={tenant_id}, entity={old_entity_name}")

            query = """
            UPDATE transactions
            SET entity_id = %s
            WHERE tenant_id = %s AND entity = %s
            """

            self.db.execute_query(query, (entity_id, tenant_id, old_entity_name))

            # Get count of updated transactions
            count_query = """
            SELECT COUNT(*) FROM transactions
            WHERE tenant_id = %s AND entity = %s AND entity_id = %s
            """

            result = self.db.execute_query(count_query, (tenant_id, old_entity_name, entity_id))
            count = result[0][0] if result else 0

            logger.info(f"✓ Updated {count} transactions for entity: {old_entity_name}")

        return True

    def validate_migration(self) -> bool:
        """Validate that migration was successful"""
        logger.info("=" * 80)
        logger.info("Validating migration...")
        logger.info("=" * 80)

        all_valid = True

        # Check 1: All transactions have entity_id
        query = "SELECT COUNT(*) FROM transactions WHERE entity_id IS NULL"
        result = self.db.execute_query(query)
        null_count = result[0][0] if result else 0

        if null_count > 0:
            logger.warning(f"✗ {null_count} transactions have NULL entity_id")
            all_valid = False
        else:
            logger.info(f"✓ All transactions have entity_id")

        # Check 2: All entities have at least one business line
        query = """
        SELECT e.id, e.name, COUNT(bl.id) as bl_count
        FROM entities e
        LEFT JOIN business_lines bl ON e.id = bl.entity_id
        GROUP BY e.id, e.name
        HAVING COUNT(bl.id) = 0
        """

        result = self.db.execute_query(query)

        if result and len(result) > 0:
            logger.warning(f"✗ {len(result)} entities have no business lines")
            for row in result:
                logger.warning(f"  - Entity: {row[1]}")
            all_valid = False
        else:
            logger.info(f"✓ All entities have at least one business line")

        # Check 3: Entity summary
        query = "SELECT COUNT(*) FROM entities"
        result = self.db.execute_query(query)
        entity_count = result[0][0] if result else 0
        logger.info(f"Total entities created: {entity_count}")

        query = "SELECT COUNT(*) FROM business_lines"
        result = self.db.execute_query(query)
        bl_count = result[0][0] if result else 0
        logger.info(f"Total business lines created: {bl_count}")

        # Check 4: Transactions mapped
        query = "SELECT COUNT(*) FROM transactions WHERE entity_id IS NOT NULL"
        result = self.db.execute_query(query)
        mapped_count = result[0][0] if result else 0
        logger.info(f"Transactions with entity_id: {mapped_count}")

        logger.info("=" * 80)

        if all_valid:
            logger.info("✓ Migration validation PASSED")
        else:
            logger.error("✗ Migration validation FAILED")

        return all_valid

    def run(self) -> bool:
        """Run the complete migration"""
        logger.info("=" * 80)
        logger.info("Starting Entity Data Migration")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info("=" * 80)

        try:
            # Step 1: Get unique entities per tenant
            entities_by_tenant = self.get_unique_entities_per_tenant()

            if not entities_by_tenant:
                logger.warning("No entities found to migrate")
                return True

            # Step 2: Migrate Delta entities (if exists)
            if 'delta' in entities_by_tenant:
                if not self.migrate_delta_entities():
                    return False

            # Step 3: Migrate other tenant entities
            for tenant_id, entity_names in entities_by_tenant.items():
                if tenant_id != 'delta':  # Skip delta, already done
                    if not self.migrate_generic_tenant_entities(tenant_id, entity_names):
                        return False

            # Step 4: Update transaction entity_id references
            if not self.update_transaction_entity_ids():
                return False

            # Step 5: Validate migration
            if not self.validate_migration():
                return False

            logger.info("=" * 80)
            logger.info("✓ Migration completed successfully!")
            logger.info("=" * 80)

            return True

        except Exception as e:
            logger.error(f"Migration failed with error: {e}")
            logger.exception("Exception details:")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Migrate entity data from VARCHAR to entities/business_lines tables'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (no database changes)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize database connection
    db_manager = DatabaseManager()

    # Run migration
    migration = EntityMigration(db_manager, dry_run=args.dry_run)
    success = migration.run()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
