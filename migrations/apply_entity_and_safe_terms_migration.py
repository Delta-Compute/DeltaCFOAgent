#!/usr/bin/env python3
"""
Migration Script: Add entity and SAFE terms to shareholder equity system
Created: 2025-11-17
Purpose: Apply database changes for entity support and SAFE agreements
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_ui.database import db_manager

def apply_migration():
    """Apply the entity and SAFE terms migration"""
    print("=" * 60)
    print("Applying Entity and SAFE Terms Migration")
    print("=" * 60)

    try:
        # Read migration SQL
        migration_path = os.path.join(
            os.path.dirname(__file__),
            'add_entity_and_safe_terms.sql'
        )

        print(f"\nReading migration file: {migration_path}")
        with open(migration_path, 'r') as f:
            migration_sql = f.read()

        # Execute migration - split into individual statements
        print("\nExecuting migration...")
        statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip() and not stmt.strip().startswith('--')]

        for statement in statements:
            if statement:
                db_manager.execute_query(statement)

        print("\n✓ Migration applied successfully!")

        # Verify changes
        print("\n" + "=" * 60)
        print("Verifying Migration")
        print("=" * 60)

        # Check if columns exist
        check_query = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'shareholders'
        AND column_name IN ('entity', 'safe_terms')
        ORDER BY column_name;
        """

        columns = db_manager.execute_query(check_query, fetch_all=True)

        if len(columns) == 2:
            print("\n✓ Verification successful!")
            print("\nColumns added to shareholders table:")
            for col in columns:
                print(f"  - {col['column_name']}: {col['data_type']}")
        else:
            print("\n⚠ Warning: Expected 2 columns but found", len(columns))

        print("\n" + "=" * 60)
        print("Migration Complete")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Update API endpoints to handle entity and safe_terms")
        print("2. Update frontend forms to include entity dropdown")
        print("3. Add conditional SAFE fields (discount_rate, cap)")
        print("4. Test the complete implementation")

        return True

    except Exception as e:
        print(f"\n✗ Error applying migration: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = apply_migration()
    sys.exit(0 if success else 1)
