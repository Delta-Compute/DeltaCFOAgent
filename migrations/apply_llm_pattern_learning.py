#!/usr/bin/env python3
"""
Migration Script: LLM-Validated Pattern Learning Enhancement
Description: Applies 3-occurrence pattern learning with LLM validation
Run: python migrations/apply_llm_pattern_learning.py
"""

import sys
import os

# Add parent directory to path to import database module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from web_ui.database import db_manager


def apply_migration():
    """Apply the LLM pattern learning enhancement migration"""

    print("=" * 70)
    print("LLM-VALIDATED PATTERN LEARNING MIGRATION")
    print("=" * 70)
    print("\nThis migration will:")
    print("  1. Add origin/destination columns to user_classification_tracking")
    print("  2. Add LLM validation fields to pattern_suggestions")
    print("  3. Add LLM tracking to classification_patterns")
    print("  4. Create pattern_notifications table")
    print("  5. Update trigger to 3-occurrence threshold")
    print("  6. Install pg_trgm extension for similarity matching")
    print("  7. Add pattern_learning_config to tenant_configuration")
    print("\n" + "=" * 70)

    # Read SQL migration file
    migration_file = os.path.join(os.path.dirname(__file__), 'enhance_pattern_learning_llm.sql')

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

            # Verify tables and columns were created
            print("\n🔍 Verifying migration...")

            # Check pattern_notifications table
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'pattern_notifications'
            """)

            if cursor.fetchone():
                print("✅ pattern_notifications table created")
            else:
                print("⚠️  WARNING: pattern_notifications table not found")

            # Check new columns in user_classification_tracking
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'user_classification_tracking'
                AND column_name IN ('origin', 'destination')
                ORDER BY column_name
            """)

            columns = cursor.fetchall()
            if len(columns) == 2:
                print("✅ origin and destination columns added to user_classification_tracking")
            else:
                print(f"⚠️  WARNING: Expected 2 columns, found {len(columns)}")

            # Check LLM validation columns in pattern_suggestions
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'pattern_suggestions'
                AND column_name IN ('llm_validation_result', 'llm_validated_at', 'validation_model')
                ORDER BY column_name
            """)

            columns = cursor.fetchall()
            if len(columns) == 3:
                print("✅ LLM validation columns added to pattern_suggestions")
            else:
                print(f"⚠️  WARNING: Expected 3 columns, found {len(columns)}")

            # Check LLM columns in classification_patterns
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'classification_patterns'
                AND column_name IN ('created_by', 'llm_confidence_adjustment', 'risk_assessment')
                ORDER BY column_name
            """)

            columns = cursor.fetchall()
            if len(columns) == 3:
                print("✅ LLM tracking columns added to classification_patterns")
            else:
                print(f"⚠️  WARNING: Expected 3 columns, found {len(columns)}")

            # Check pattern_learning_config in tenant_configuration
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'tenant_configuration'
                AND column_name = 'pattern_learning_config'
            """)

            if cursor.fetchone():
                print("✅ pattern_learning_config column added to tenant_configuration")
            else:
                print("⚠️  WARNING: pattern_learning_config column not found")

            # Check pg_trgm extension
            cursor.execute("""
                SELECT extname
                FROM pg_extension
                WHERE extname = 'pg_trgm'
            """)

            if cursor.fetchone():
                print("✅ pg_trgm extension installed")
            else:
                print("⚠️  WARNING: pg_trgm extension not found")

            # Check updated trigger
            cursor.execute("""
                SELECT trigger_name
                FROM information_schema.triggers
                WHERE trigger_name = 'trigger_check_pattern_suggestion'
            """)

            if cursor.fetchone():
                print("✅ Updated trigger created (3-occurrence threshold)")
            else:
                print("⚠️  WARNING: Trigger not found")

            # Check updated function
            cursor.execute("""
                SELECT routine_name
                FROM information_schema.routines
                WHERE routine_name = 'check_and_create_pattern_suggestion_v2'
                AND routine_schema = 'public'
            """)

            if cursor.fetchone():
                print("✅ Updated pattern suggestion function created")
            else:
                print("⚠️  WARNING: Function not found")

            cursor.close()

            print("\n" + "=" * 70)
            print("✅ MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 70)
            print("\nNext steps:")
            print("  1. Create web_ui/pattern_learning.py module")
            print("  2. Implement LLM validation function")
            print("  3. Update transaction update endpoint")
            print("  4. Create pattern notifications API")
            print("  5. Add notification UI components")
            print("\n")

            return True

    except Exception as e:
        print(f"\n❌ ERROR: Migration failed")
        print(f"   {str(e)}")
        import traceback
        print(f"\n{traceback.format_exc()}")
        return False


def check_migration_status():
    """Check if migration has already been applied"""

    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Check if pattern_notifications table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'pattern_notifications'
                )
            """)

            exists = cursor.fetchone()[0]
            cursor.close()

            return exists

    except Exception as e:
        print(f"Warning: Could not check migration status: {e}")
        return False


if __name__ == "__main__":
    print("\n🔧 LLM-Validated Pattern Learning Migration\n")

    # Check if already applied
    if check_migration_status():
        print("⚠️  WARNING: Migration appears to have already been applied.")
        print("   pattern_notifications table already exists.")

        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            print("\n❌ Migration cancelled by user")
            sys.exit(0)

    # Apply migration
    success = apply_migration()

    # Exit with appropriate code
    sys.exit(0 if success else 1)
