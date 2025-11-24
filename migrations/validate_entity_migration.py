#!/usr/bin/env python3
"""
Entity Migration Validation Script
Validates that the entity migration was successful

Author: Claude Code
Date: 2024-11-24
"""

import os
import sys
import argparse
import logging
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_ui.database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EntityMigrationValidator:
    """Validates entity migration integrity"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.errors = []
        self.warnings = []

    def check_transactions_have_entity_id(self) -> bool:
        """Verify all transactions have valid entity_id"""
        logger.info("Checking: All transactions have entity_id...")

        query = "SELECT COUNT(*) FROM transactions WHERE entity_id IS NULL"
        result = self.db.execute_query(query)
        null_count = result[0][0] if result else 0

        if null_count > 0:
            self.errors.append(f"{null_count} transactions have NULL entity_id")
            logger.error(f"✗ FAILED: {null_count} transactions missing entity_id")
            return False
        else:
            logger.info("✓ PASSED: All transactions have entity_id")
            return True

    def check_entities_have_business_lines(self) -> bool:
        """Verify all entities have at least one business line"""
        logger.info("Checking: All entities have business lines...")

        query = """
        SELECT e.id, e.name, COUNT(bl.id) as bl_count
        FROM entities e
        LEFT JOIN business_lines bl ON e.id = bl.entity_id
        GROUP BY e.id, e.name
        HAVING COUNT(bl.id) = 0
        """

        result = self.db.execute_query(query)

        if result and len(result) > 0:
            for row in result:
                error_msg = f"Entity '{row[1]}' has no business lines"
                self.errors.append(error_msg)
                logger.error(f"✗ {error_msg}")
            return False
        else:
            logger.info("✓ PASSED: All entities have business lines")
            return True

    def check_no_orphaned_business_lines(self) -> bool:
        """Verify no business lines reference non-existent entities"""
        logger.info("Checking: No orphaned business lines...")

        query = """
        SELECT COUNT(*)
        FROM business_lines bl
        WHERE bl.entity_id NOT IN (SELECT id FROM entities)
        """

        result = self.db.execute_query(query)
        orphan_count = result[0][0] if result else 0

        if orphan_count > 0:
            self.errors.append(f"{orphan_count} orphaned business lines found")
            logger.error(f"✗ FAILED: {orphan_count} orphaned business lines")
            return False
        else:
            logger.info("✓ PASSED: No orphaned business lines")
            return True

    def check_tenant_isolation(self) -> bool:
        """Verify tenant isolation is maintained"""
        logger.info("Checking: Tenant isolation...")

        # Check that entities don't cross tenant boundaries
        query = """
        SELECT t.tenant_id, e.tenant_id, COUNT(*) as mismatch_count
        FROM transactions t
        JOIN entities e ON t.entity_id = e.id
        WHERE t.tenant_id != e.tenant_id
        GROUP BY t.tenant_id, e.tenant_id
        """

        result = self.db.execute_query(query)

        if result and len(result) > 0:
            for row in result:
                error_msg = f"Tenant isolation breach: transaction tenant={row[0]}, entity tenant={row[1]}, count={row[2]}"
                self.errors.append(error_msg)
                logger.error(f"✗ {error_msg}")
            return False
        else:
            logger.info("✓ PASSED: Tenant isolation maintained")
            return True

    def check_foreign_key_integrity(self) -> bool:
        """Verify all foreign key relationships are valid"""
        logger.info("Checking: Foreign key integrity...")

        checks_passed = True

        # Check transactions -> entities FK
        query = """
        SELECT COUNT(*)
        FROM transactions t
        WHERE t.entity_id IS NOT NULL
          AND t.entity_id NOT IN (SELECT id FROM entities)
        """

        result = self.db.execute_query(query)
        invalid_count = result[0][0] if result else 0

        if invalid_count > 0:
            error_msg = f"{invalid_count} transactions reference non-existent entities"
            self.errors.append(error_msg)
            logger.error(f"✗ {error_msg}")
            checks_passed = False

        # Check transactions -> business_lines FK
        query = """
        SELECT COUNT(*)
        FROM transactions t
        WHERE t.business_line_id IS NOT NULL
          AND t.business_line_id NOT IN (SELECT id FROM business_lines)
        """

        result = self.db.execute_query(query)
        invalid_count = result[0][0] if result else 0

        if invalid_count > 0:
            error_msg = f"{invalid_count} transactions reference non-existent business lines"
            self.errors.append(error_msg)
            logger.error(f"✗ {error_msg}")
            checks_passed = False

        if checks_passed:
            logger.info("✓ PASSED: Foreign key integrity validated")

        return checks_passed

    def check_data_consistency(self) -> bool:
        """Check that old entity VARCHAR matches new entity_id"""
        logger.info("Checking: Data consistency (entity VARCHAR vs entity_id)...")

        query = """
        SELECT t.id, t.entity, e.name
        FROM transactions t
        JOIN entities e ON t.entity_id = e.id
        WHERE t.entity != e.name
        LIMIT 10
        """

        result = self.db.execute_query(query)

        if result and len(result) > 0:
            warning_msg = f"{len(result)} transactions have entity VARCHAR != entity.name"
            self.warnings.append(warning_msg)
            logger.warning(f"⚠ WARNING: {warning_msg}")
            logger.warning("Sample mismatches:")
            for row in result[:5]:
                logger.warning(f"  Transaction {row[0]}: '{row[1]}' != '{row[2]}'")
            return True  # Warning, not error
        else:
            logger.info("✓ PASSED: Data consistency validated")
            return True

    def print_summary_statistics(self):
        """Print summary statistics"""
        logger.info("=" * 80)
        logger.info("Migration Summary Statistics")
        logger.info("=" * 80)

        # Entity count by tenant
        query = """
        SELECT tenant_id, COUNT(*) as entity_count
        FROM entities
        GROUP BY tenant_id
        ORDER BY tenant_id
        """

        result = self.db.execute_query(query)

        logger.info("Entities per tenant:")
        for row in result:
            logger.info(f"  {row[0]}: {row[1]} entities")

        # Business line count
        query = "SELECT COUNT(*) FROM business_lines"
        result = self.db.execute_query(query)
        bl_count = result[0][0] if result else 0
        logger.info(f"\nTotal business lines: {bl_count}")

        # Transactions with entity_id
        query = "SELECT COUNT(*) FROM transactions WHERE entity_id IS NOT NULL"
        result = self.db.execute_query(query)
        mapped_count = result[0][0] if result else 0

        query = "SELECT COUNT(*) FROM transactions"
        result = self.db.execute_query(query)
        total_count = result[0][0] if result else 0

        percentage = (mapped_count / total_count * 100) if total_count > 0 else 0
        logger.info(f"\nTransactions with entity_id: {mapped_count}/{total_count} ({percentage:.1f}%)")

        # Transactions with business_line_id
        query = "SELECT COUNT(*) FROM transactions WHERE business_line_id IS NOT NULL"
        result = self.db.execute_query(query)
        bl_mapped_count = result[0][0] if result else 0

        percentage = (bl_mapped_count / total_count * 100) if total_count > 0 else 0
        logger.info(f"Transactions with business_line_id: {bl_mapped_count}/{total_count} ({percentage:.1f}%)")

        logger.info("=" * 80)

    def run(self) -> bool:
        """Run all validation checks"""
        logger.info("=" * 80)
        logger.info("Entity Migration Validation")
        logger.info("=" * 80)

        checks = [
            self.check_transactions_have_entity_id,
            self.check_entities_have_business_lines,
            self.check_no_orphaned_business_lines,
            self.check_tenant_isolation,
            self.check_foreign_key_integrity,
            self.check_data_consistency
        ]

        all_passed = True

        for check in checks:
            try:
                if not check():
                    all_passed = False
            except Exception as e:
                logger.error(f"Check failed with exception: {e}")
                logger.exception("Exception details:")
                all_passed = False

        # Print summary
        self.print_summary_statistics()

        # Print results
        logger.info("=" * 80)
        logger.info("Validation Results")
        logger.info("=" * 80)

        if self.errors:
            logger.error(f"Errors found: {len(self.errors)}")
            for error in self.errors:
                logger.error(f"  ✗ {error}")

        if self.warnings:
            logger.warning(f"Warnings found: {len(self.warnings)}")
            for warning in self.warnings:
                logger.warning(f"  ⚠ {warning}")

        if all_passed and not self.errors:
            logger.info("✓ All validation checks PASSED")
            return True
        else:
            logger.error("✗ Validation FAILED")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Validate entity migration integrity'
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

    # Run validation
    validator = EntityMigrationValidator(db_manager)
    success = validator.run()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
