#!/usr/bin/env python3
"""
Migration Script: Pattern Learning System
Description: Applies the auto-learning system with user approval workflow
Run: python migrations/apply_pattern_learning_migration.py
"""

import sys
import os

# Add parent directory to path to import database module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from web_ui.database import db_manager


def apply_migration():
    """Apply the pattern learning system migration"""

    print("=" * 70)
    print("PATTERN LEARNING SYSTEM MIGRATION")
    print("=" * 70)
    print("\nThis migration will:")
    print("  1. Add justification column to classification_patterns")
    print("  2. Create user_classification_tracking table")
    print("  3. Create pattern_suggestions table")
    print("  4. Create pattern signature generation function")
    print("  5. Create auto-suggestion trigger (50 classification threshold)")
    print("  6. Add priority column to pattern_suggestions")
    print("\n" + "=" * 70)

    # Read SQL migration file
    migration_file = os.path.join(os.path.dirname(__file__), 'add_pattern_learning_system.sql')

    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
    except FileNotFoundError:
        print(f"\n❌ ERROR: Migration file not found: {migration_file}")
        return False

    print(f"\n📄 Loaded migration SQL from: {migration_file}")
    print(f"   Size: {len(sql_content)} characters")

    # Connect to database using context manager
    print("\n🔌 Connecting to PostgreSQL database...")

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            print("✅ Connected successfully")

            # Execute migration
            print("\n🚀 Executing migration SQL...")
            cursor.execute(sql_content)
            conn.commit()

            print("✅ Migration executed successfully")

            # Verify tables were created
            print("\n🔍 Verifying tables...")

            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('user_classification_tracking', 'pattern_suggestions')
                ORDER BY table_name
            """)

            tables = cursor.fetchall()

            if len(tables) == 2:
                print("✅ Tables verified:")
                for table in tables:
                    print(f"   • {table[0]}")
            else:
                print(f"⚠️  WARNING: Expected 2 tables, found {len(tables)}")

            # Verify justification column was added
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'classification_patterns'
                AND column_name = 'justification'
            """)

            if cursor.fetchone():
                print("✅ Justification column added to classification_patterns")
            else:
                print("⚠️  WARNING: Justification column not found in classification_patterns")

            # Verify trigger was created
            cursor.execute("""
                SELECT trigger_name
                FROM information_schema.triggers
                WHERE trigger_name = 'trigger_check_pattern_suggestion'
            """)

            if cursor.fetchone():
                print("✅ Auto-suggestion trigger created")
            else:
                print("⚠️  WARNING: Trigger not found")

            # Verify function was created
            cursor.execute("""
                SELECT routine_name
                FROM information_schema.routines
                WHERE routine_name IN ('generate_pattern_signature', 'check_and_create_pattern_suggestion')
                AND routine_schema = 'public'
            """)

            functions = cursor.fetchall()
            print(f"✅ Functions created: {len(functions)} of 2")
            for func in functions:
                print(f"   • {func[0]}")

            cursor.close()

            print("\n" + "=" * 70)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 70)
            print("\nNext steps:")
            print("  1. Add justification field to pattern modal UI")
            print("  2. Create pattern suggestion approval modal")
            print("  3. Implement tracking in transaction classification endpoint")
            print("  4. Create API endpoints for suggestions")
            print("  5. Add notification badge for pending suggestions")
            print("\n")

            return True

    except Exception as e:
        print(f"\n❌ ERROR: Migration failed")
        print(f"   {str(e)}")
        return False


def check_migration_status():
    """Check if migration has already been applied"""

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Check if pattern_suggestions table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'pattern_suggestions'
                )
            """)

            exists = cursor.fetchone()[0]
            cursor.close()

            return exists

    except Exception as e:
        print(f"Warning: Could not check migration status: {e}")
        return False


if __name__ == "__main__":
    print("\n🔧 Pattern Learning System Migration\n")

    # Check if already applied
    if check_migration_status():
        print("⚠️  WARNING: Migration appears to have already been applied.")
        print("   pattern_suggestions table already exists.")

        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            print("\n❌ Migration cancelled by user")
            sys.exit(0)

    # Apply migration
    success = apply_migration()

    # Exit with appropriate code
    sys.exit(0 if success else 1)
