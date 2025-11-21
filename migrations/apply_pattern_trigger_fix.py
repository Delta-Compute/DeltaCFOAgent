#!/usr/bin/env python3
"""
Apply the Pattern Trigger Fix Migration

This fixes the trigger to preserve natural word order instead of alphabetical sorting.

Before: "received bitcoin deposit from external" → "%account bitcoin deposit external from received%"
After:  "received bitcoin deposit from external" → "%received%bitcoin%deposit%external%"
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_ui'))

from database import db_manager


def apply_migration():
    """Apply the pattern trigger fix migration"""

    print("=" * 80)
    print("APPLYING PATTERN TRIGGER FIX MIGRATION")
    print("=" * 80)

    migration_file = os.path.join(os.path.dirname(__file__), 'fix_pattern_trigger_word_order.sql')

    if not os.path.exists(migration_file):
        print(f"ERROR: Migration file not found: {migration_file}")
        sys.exit(1)

    # Read migration SQL
    with open(migration_file, 'r') as f:
        migration_sql = f.read()

    print(f"\nMigration file: {migration_file}")
    print(f"SQL length: {len(migration_sql)} chars")
    print("\nChanges:")
    print("  - Drop old trigger_check_pattern_suggestion_v3()")
    print("  - Create new trigger_check_pattern_suggestion_v4()")
    print("  - Preserve natural word order (no alphabetical sorting)")
    print("  - Filter out stop words")
    print("  - Take first 5 significant words")
    print()

    # Apply migration
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            print("Executing migration SQL...")
            cursor.execute(migration_sql)

            conn.commit()
            cursor.close()

            print("✅ Migration applied successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print()
    print("1. Classify 3+ similar transactions to test the new trigger")
    print("2. Check pattern_suggestions table - pattern should preserve word order")
    print("3. The background service will automatically validate new patterns")
    print("4. You should see toast notifications if patterns are approved!")
    print()
    print("=" * 80)


if __name__ == '__main__':
    apply_migration()
