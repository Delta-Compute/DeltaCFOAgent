#!/usr/bin/env python3
"""
Apply Payment Proof Migration to Invoices Table
Adds columns for payment tracking and receipt storage
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

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

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name=%s AND column_name=%s
    """, (table_name, column_name))
    return cursor.fetchone() is not None

def apply_migration(dry_run=False):
    """Apply the payment proof migration"""
    print("\n" + "="*80)
    print("PAYMENT PROOF MIGRATION - APPLY")
    print("="*80 + "\n")

    if dry_run:
        print("DRY RUN MODE - No changes will be made\n")

    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Read migration SQL
            migration_file = os.path.join(os.path.dirname(__file__), 'add_payment_proof_columns.sql')
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration_sql = f.read()

            # Remove rollback section and comments
            lines = migration_sql.split('\n')
            sql_lines = []
            skip_section = False

            for line in lines:
                if '/*' in line:
                    skip_section = True
                if not skip_section and not line.strip().startswith('--'):
                    sql_lines.append(line)
                if '*/' in line:
                    skip_section = False

            migration_sql = '\n'.join(sql_lines)

            # Check existing columns
            columns_to_add = [
                'payment_date',
                'payment_proof_path',
                'payment_method',
                'payment_confirmation_number',
                'payment_notes',
                'payment_proof_uploaded_at',
                'payment_proof_uploaded_by'
            ]

            print("Checking existing columns...")
            existing_columns = []
            new_columns = []

            for col in columns_to_add:
                exists = check_column_exists(cursor, 'invoices', col)
                if exists:
                    existing_columns.append(col)
                    print(f"  ✓ {col} - Already exists")
                else:
                    new_columns.append(col)
                    print(f"  + {col} - Will be added")

            print()

            if not new_columns:
                print("All columns already exist. No migration needed.")
                return

            if dry_run:
                print(f"DRY RUN: Would add {len(new_columns)} columns:")
                for col in new_columns:
                    print(f"  - {col}")
                print()
                return

            # Apply migration
            print(f"Applying migration ({len(new_columns)} new columns)...")
            cursor.execute(migration_sql)
            conn.commit()

            # Verify
            print("\nVerifying migration...")
            all_added = True
            for col in columns_to_add:
                exists = check_column_exists(cursor, 'invoices', col)
                if exists:
                    print(f"  ✓ {col}")
                else:
                    print(f"  ✗ {col} - FAILED")
                    all_added = False

            if all_added:
                print("\n" + "="*80)
                print("SUCCESS: Payment proof migration applied successfully!")
                print("="*80 + "\n")
            else:
                print("\n" + "="*80)
                print("WARNING: Some columns may not have been added")
                print("="*80 + "\n")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

def rollback_migration():
    """Rollback the payment proof migration"""
    print("\n" + "="*80)
    print("PAYMENT PROOF MIGRATION - ROLLBACK")
    print("="*80 + "\n")
    print("WARNING: This will remove all payment proof data!")

    confirm = input("Type 'YES' to confirm rollback: ")
    if confirm != 'YES':
        print("Rollback cancelled.")
        return

    conn = get_db_connection()

    try:
        with conn.cursor() as cursor:
            columns_to_drop = [
                'payment_date',
                'payment_proof_path',
                'payment_method',
                'payment_confirmation_number',
                'payment_notes',
                'payment_proof_uploaded_at',
                'payment_proof_uploaded_by'
            ]

            print("Dropping columns...")
            for col in columns_to_drop:
                cursor.execute(f"ALTER TABLE invoices DROP COLUMN IF EXISTS {col}")
                print(f"  ✓ Dropped {col}")

            print("\nDropping indexes...")
            cursor.execute("DROP INDEX IF EXISTS idx_invoices_payment_status")
            cursor.execute("DROP INDEX IF EXISTS idx_invoices_payment_date")
            cursor.execute("DROP INDEX IF EXISTS idx_invoices_payment_proof")
            print("  ✓ Dropped all indexes")

            conn.commit()

            print("\n" + "="*80)
            print("SUCCESS: Payment proof migration rolled back!")
            print("="*80 + "\n")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Apply payment proof migration')
    parser.add_argument('--dry-run', action='store_true', help='Check what would be done without applying')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')

    args = parser.parse_args()

    if args.rollback:
        rollback_migration()
    else:
        apply_migration(dry_run=args.dry_run)
