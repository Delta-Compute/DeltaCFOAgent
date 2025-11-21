#!/usr/bin/env python3
"""
Apply migration to fix NaN values in transactions table
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_ui.database import db_manager

def apply_migration():
    """Apply the NaN fix migration"""

    print("=" * 80)
    print("APPLYING MIGRATION: Fix NaN Values in Transactions")
    print("=" * 80)

    # Read the SQL migration file
    sql_file = os.path.join(os.path.dirname(__file__), 'fix_nan_values.sql')
    with open(sql_file, 'r') as f:
        sql_content = f.read()

    # Split into individual statements
    statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            print("\n[1/4] Counting affected rows before migration...")
            cursor.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE classified_entity IN ('nan', 'NaN', 'None', '') OR classified_entity IS NULL) as nan_entities,
                    COUNT(*) FILTER (WHERE origin IN ('nan', 'NaN', 'None', '') OR origin IS NULL) as nan_origins,
                    COUNT(*) FILTER (WHERE destination IN ('nan', 'NaN', 'None', '') OR destination IS NULL) as nan_destinations
                FROM transactions
            """)
            before_counts = cursor.fetchone()
            print(f"   - Entities with 'nan': {before_counts[0]}")
            print(f"   - Origins with 'nan': {before_counts[1]}")
            print(f"   - Destinations with 'nan': {before_counts[2]}")

            print("\n[2/4] Fixing classified_entity column...")
            cursor.execute("""
                UPDATE transactions
                SET classified_entity = 'Unknown Entity'
                WHERE classified_entity IN ('nan', 'NaN', 'None', '') OR classified_entity IS NULL
            """)
            entity_updated = cursor.rowcount
            print(f"   ✓ Updated {entity_updated} rows")

            print("\n[3/4] Fixing origin column...")
            cursor.execute("""
                UPDATE transactions
                SET origin = 'Unknown'
                WHERE origin IN ('nan', 'NaN', 'None', '') OR origin IS NULL
            """)
            origin_updated = cursor.rowcount
            print(f"   ✓ Updated {origin_updated} rows")

            print("\n[4/4] Fixing destination column...")
            cursor.execute("""
                UPDATE transactions
                SET destination = 'Unknown'
                WHERE destination IN ('nan', 'NaN', 'None', '') OR destination IS NULL
            """)
            destination_updated = cursor.rowcount
            print(f"   ✓ Updated {destination_updated} rows")

            # Commit the changes
            conn.commit()

            print("\n" + "=" * 80)
            print("MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print(f"\nSummary:")
            print(f"  - {entity_updated} entities fixed")
            print(f"  - {origin_updated} origins fixed")
            print(f"  - {destination_updated} destinations fixed")
            print(f"  - Total: {entity_updated + origin_updated + destination_updated} field updates")

            cursor.close()

    except Exception as e:
        print(f"\n❌ ERROR: Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    apply_migration()
