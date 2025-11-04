#!/usr/bin/env python3
"""
Apply migration to add wallet display columns to transactions table
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2

load_dotenv()

def get_db_connection():
    """Get PostgreSQL database connection"""
    db_config = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
    }

    ssl_mode = os.getenv('DB_SSL_MODE')
    if ssl_mode:
        db_config['sslmode'] = ssl_mode

    conn = psycopg2.connect(**db_config)
    return conn

def apply_migration():
    """Apply the migration"""
    print("\n" + "="*80)
    print("APPLYING WALLET DISPLAY COLUMNS MIGRATION")
    print("="*80 + "\n")

    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            # Read migration file
            migration_file = os.path.join(os.path.dirname(__file__), 'add_wallet_display_columns.sql')
            with open(migration_file, 'r') as f:
                migration_sql = f.read()

            print("Executing migration SQL...")
            cursor.execute(migration_sql)
            conn.commit()

            print("\nSUCCESS: Migration applied successfully!")
            print("\nVerifying new columns...")

            # Verify columns were added
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'transactions'
                AND column_name IN ('origin_display', 'destination_display')
                ORDER BY column_name
            """)

            columns = cursor.fetchall()
            if columns:
                print("\nColumns added:")
                for col in columns:
                    print(f"  - {col[0]} ({col[1]})")
            else:
                print("\nWARNING: Columns not found after migration!")

            # Verify indexes were created
            cursor.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'transactions'
                AND indexname IN ('idx_transactions_origin', 'idx_transactions_destination')
                ORDER BY indexname
            """)

            indexes = cursor.fetchall()
            if indexes:
                print("\nIndexes created:")
                for idx in indexes:
                    print(f"  - {idx[0]}")

            cursor.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = 'wallet_addresses'
                AND indexname = 'idx_wallet_addresses_lookup'
            """)

            wallet_idx = cursor.fetchone()
            if wallet_idx:
                print(f"  - {wallet_idx[0]}")

            print("\n" + "="*80)
            print("MIGRATION COMPLETE!")
            print("="*80 + "\n")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    apply_migration()
