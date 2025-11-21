#!/usr/bin/env python3
"""
Migration Script: Fuzzy Pattern Matching System
Description: Implements keyword-based and trigram similarity matching for pattern learning
Run: python migrations/apply_fuzzy_matching_migration.py
"""

import sys
import os

# Add parent directory to path to import database module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from web_ui.database import db_manager


def apply_migration():
    """Apply the fuzzy pattern matching migration"""

    print("=" * 70)
    print("FUZZY PATTERN MATCHING MIGRATION")
    print("=" * 70)
    print("\nThis migration will:")
    print("  1. Enable PostgreSQL pg_trgm extension")
    print("  2. Create extract_pattern_keywords() function")
    print("  3. Add normalized_pattern column to tracking table")
    print("  4. Create generate_fuzzy_signature() function")
    print("  5. Update trigger to use fuzzy matching (v2)")
    print("  6. Backfill normalized patterns for existing records")
    print("\n" + "=" * 70)

    # Read SQL migration file
    migration_file = os.path.join(os.path.dirname(__file__), 'add_fuzzy_pattern_matching.sql')

    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
    except FileNotFoundError:
        print(f"\n ERROR: Migration file not found: {migration_file}")
        return False

    print(f"\n Loaded migration SQL from: {migration_file}")
    print(f"   Size: {len(sql_content)} characters")

    # Connect to database using context manager
    print("\n Connecting to PostgreSQL database...")

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            print(" Connected successfully")

            # Execute migration
            print("\n Executing migration SQL...")
            cursor.execute(sql_content)
            conn.commit()

            print(" Migration executed successfully")

            # Verify normalized_pattern column was added
            print("\n Verifying migration...")

            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'user_classification_tracking'
                AND column_name = 'normalized_pattern'
            """)

            if cursor.fetchone():
                print(" normalized_pattern column added")
            else:
                print("  WARNING: normalized_pattern column not found")

            # Verify pg_trgm extension was enabled
            cursor.execute("""
                SELECT extname
                FROM pg_extension
                WHERE extname = 'pg_trgm'
            """)

            if cursor.fetchone():
                print(" pg_trgm extension enabled")
            else:
                print("  WARNING: pg_trgm extension not found")

            # Verify functions were created
            cursor.execute("""
                SELECT routine_name
                FROM information_schema.routines
                WHERE routine_name IN (
                    'extract_pattern_keywords',
                    'generate_fuzzy_signature',
                    'check_and_create_pattern_suggestion_v2'
                )
                AND routine_schema = 'public'
            """)

            functions = cursor.fetchall()
            print(f" Functions created: {len(functions)} of 3")
            for func in functions:
                print(f"   • {func[0]}")

            # Verify trigger was updated
            cursor.execute("""
                SELECT trigger_name
                FROM information_schema.triggers
                WHERE trigger_name = 'trigger_check_pattern_suggestion'
            """)

            if cursor.fetchone():
                print(" Auto-suggestion trigger updated")
            else:
                print("  WARNING: Trigger not found")

            # Check how many records were backfilled
            cursor.execute("""
                SELECT COUNT(*)
                FROM user_classification_tracking
                WHERE normalized_pattern IS NOT NULL
            """)

            backfilled_count = cursor.fetchone()[0]
            print(f" Backfilled {backfilled_count} existing tracking records")

            cursor.close()

            print("\n" + "=" * 70)
            print(" MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 70)
            print("\nFuzzy matching is now enabled!")
            print("\nHow it works:")
            print("  • Removes variable data (amounts, dates, numbers)")
            print("  • Extracts keywords from descriptions")
            print("  • Uses trigram similarity for 85%+ matches")
            print("  • Creates patterns after 3 similar classifications")
            print("\nExample:")
            print('  "Bitcoin deposit - 0.0076146 BTC @ $42,776.10"')
            print('  "Bitcoin deposit - 0.0082345 BTC @ $43,120.00"')
            print('  Both match as: "bitcoin deposit"')
            print("\n")

            return True

    except Exception as e:
        print(f"\n ERROR: Migration failed")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def check_migration_status():
    """Check if migration has already been applied"""

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Check if normalized_pattern column exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'user_classification_tracking'
                    AND column_name = 'normalized_pattern'
                )
            """)

            exists = cursor.fetchone()[0]
            cursor.close()

            return exists

    except Exception as e:
        print(f"Warning: Could not check migration status: {e}")
        return False


if __name__ == "__main__":
    print("\n Fuzzy Pattern Matching Migration\n")

    # Check if already applied
    if check_migration_status():
        print("  WARNING: Migration appears to have already been applied.")
        print("   normalized_pattern column already exists.")

        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            print("\n Migration cancelled by user")
            sys.exit(0)

    # Apply migration
    success = apply_migration()

    # Exit with appropriate code
    sys.exit(0 if success else 1)
