#!/usr/bin/env python3
"""
Migration Script: Add language preference support for internationalization
Applies: migrations/add_language_preferences.sql
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def apply_migration():
    """Apply language preferences migration"""

    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')

    if not all([db_host, db_name, db_user, db_password]):
        print("ERROR: Missing database connection environment variables")
        print("Required: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD")
        sys.exit(1)

    print("=" * 80)
    print("LANGUAGE PREFERENCES MIGRATION - Add i18n support (English/Portuguese)")
    print("=" * 80)
    print(f"\nDatabase: {db_name} on {db_host}")
    print(f"User: {db_user}")

    sql_file = os.path.join(os.path.dirname(__file__), 'add_language_preferences.sql')

    if not os.path.exists(sql_file):
        print(f"\nERROR: SQL file not found: {sql_file}")
        sys.exit(1)

    with open(sql_file, 'r') as f:
        sql = f.read()

    print(f"\nSQL file: {sql_file}")
    print("\nApplying migration...")

    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )

        cursor = conn.cursor()

        cursor.execute(sql)

        conn.commit()

        print("\n✓ Migration applied successfully!")

        cursor.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'users'
            AND column_name = 'preferred_language'
        """)

        users_col = cursor.fetchone()

        cursor.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'tenant_configuration'
            AND column_name = 'preferred_language'
        """)

        tenant_col = cursor.fetchone()

        print("\nVerification:")
        if users_col:
            print(f"  ✓ users.preferred_language: {users_col[1]} (default: {users_col[2]})")
        else:
            print("  ✗ users.preferred_language: NOT FOUND")

        if tenant_col:
            print(f"  ✓ tenant_configuration.preferred_language: {tenant_col[1]} (default: {tenant_col[2]})")
        else:
            print("  ✗ tenant_configuration.preferred_language: NOT FOUND")

        cursor.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename IN ('users', 'tenant_configuration')
            AND indexname IN ('idx_users_language', 'idx_tenant_configuration_language')
            ORDER BY indexname
        """)

        indexes = cursor.fetchall()

        print("\nIndexes:")
        for idx in indexes:
            print(f"  ✓ {idx[0]}")

        cursor.execute("""
            SELECT conname, contype
            FROM pg_constraint
            WHERE conname IN ('chk_users_language', 'chk_tenant_language')
            ORDER BY conname
        """)

        constraints = cursor.fetchall()

        print("\nConstraints:")
        for const in constraints:
            print(f"  ✓ {const[0]} (type: {const[1]})")

        cursor.close()
        conn.close()

        print("\n" + "=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Install Flask-Babel: pip install Flask-Babel>=4.0.0")
        print("2. Configure Flask-Babel in app_db.py")
        print("3. Add language selector UI to Settings/Profile page")
        print("4. Extract translatable strings: pybabel extract")
        print("5. Initialize Portuguese translation catalog: pybabel init -l pt")
        print("6. Translate strings and compile: pybabel compile")

    except psycopg2.Error as e:
        print(f"\n✗ ERROR: Database error occurred")
        print(f"  {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    apply_migration()
