#!/usr/bin/env python3
"""
Run Migration 005: User Accounts and Email Preferences
Adds multi-tenant SaaS support with email notification preferences
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from web_ui.database import db_manager

def run_migration():
    """Execute migration 005"""

    print("\n" + "="*80)
    print("MIGRATION 005: User Accounts and Email Preferences")
    print("="*80)
    print("\nThis migration will:")
    print("  1. Create 'users' table for SaaS company accounts")
    print("  2. Create 'email_preferences' table for notification settings")
    print("  3. Create 'email_log' table for delivery tracking")
    print("  4. Add 'user_id' column to crypto_invoices")
    print("  5. Create indexes for performance")
    print("  6. Insert default Delta Energy user")
    print("  7. Insert default email preferences")
    print("\n" + "="*80)

    response = input("\nProceed with migration? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        return False

    try:
        # Read migration SQL
        migration_file = os.path.join(
            os.path.dirname(__file__),
            '005_add_user_accounts_and_email_preferences.sql'
        )

        with open(migration_file, 'r') as f:
            migration_sql = f.read()

        print("\n📊 Executing migration...")

        # Execute migration
        db_manager.execute_query(migration_sql)

        print("✅ Migration completed successfully!")

        # Verify tables created
        print("\n📋 Verifying tables...")

        tables = ['users', 'email_preferences', 'email_log']
        for table in tables:
            result = db_manager.execute_query(
                f"SELECT COUNT(*) as count FROM {table}",
                fetch_one=True
            )
            count = result['count'] if result else 0
            print(f"  ✓ {table}: {count} rows")

        # Show default user
        user = db_manager.execute_query(
            "SELECT * FROM users WHERE email = 'cfo@deltaenergy.com'",
            fetch_one=True
        )
        if user:
            print(f"\n👤 Default user created:")
            print(f"  Company: {user['company_name']}")
            print(f"  Email: {user['email']}")
            print(f"  ID: {user['id']}")

        # Show email preferences
        prefs = db_manager.execute_query(
            """SELECT notification_type, enabled
               FROM email_preferences
               WHERE user_id = (SELECT id FROM users WHERE email = 'cfo@deltaenergy.com')""",
            fetch_all=True
        )
        print(f"\n📧 Email preferences configured:")
        for pref in prefs:
            status = "✓ Enabled" if pref['enabled'] else "✗ Disabled"
            print(f"  {status}: {pref['notification_type']}")

        print("\n" + "="*80)
        print("MIGRATION COMPLETE!")
        print("="*80)

        return True

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
