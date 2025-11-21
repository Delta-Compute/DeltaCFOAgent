#!/usr/bin/env python3
"""
Migration Script: Add file_hash and metadata columns to tenant_documents
Applies: migrations/add_file_hash_metadata_columns.sql
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def apply_migration():
    """Apply file storage migration"""

    # Get database connection details
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
    print("FILE STORAGE MIGRATION - Add file_hash and metadata columns")
    print("=" * 80)
    print(f"\nDatabase: {db_name} on {db_host}")
    print(f"User: {db_user}")

    # Read SQL file
    sql_file = os.path.join(os.path.dirname(__file__), 'add_file_hash_metadata_columns.sql')

    if not os.path.exists(sql_file):
        print(f"\nERROR: SQL file not found: {sql_file}")
        sys.exit(1)

    with open(sql_file, 'r') as f:
        sql = f.read()

    print(f"\nSQL file: {sql_file}")
    print("\nApplying migration...")

    try:
        # Connect to database
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )

        cursor = conn.cursor()

        # Execute migration
        cursor.execute(sql)

        # Commit changes
        conn.commit()

        print("\n✓ Migration applied successfully!")

        # Verify columns exist
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'tenant_documents'
            AND column_name IN ('file_hash', 'metadata')
            ORDER BY column_name
        """)

        columns = cursor.fetchall()

        print("\nVerification:")
        for col_name, col_type in columns:
            print(f"  ✓ {col_name}: {col_type}")

        # Check indexes
        cursor.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'tenant_documents'
            AND indexname IN ('idx_tenant_documents_tenant_type', 'idx_tenant_documents_hash')
            ORDER BY indexname
        """)

        indexes = cursor.fetchall()

        print("\nIndexes:")
        for idx in indexes:
            print(f"  ✓ {idx[0]}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Update .env with GCS_BUCKET_NAME (deltacfo-uploads-dev or deltacfo-uploads-prod)")
        print("2. Install google-cloud-storage: pip install google-cloud-storage")
        print("3. Authenticate with gcloud: gcloud auth application-default login")
        print("4. Test file upload with new GCS storage service")

    except psycopg2.Error as e:
        print(f"\n✗ ERROR: Database error occurred")
        print(f"  {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    apply_migration()
