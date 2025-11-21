#!/usr/bin/env python3
"""
Migration: Fix bank_accounts table schema

This migration ensures the bank_accounts table has all required columns.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_ui.database import db_manager

def check_table_exists():
    """Check if table exists"""
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'bank_accounts'
            )
        """)
        exists = cursor.fetchone()[0]
        cursor.close()
        return exists

def get_existing_columns():
    """Get list of existing columns"""
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'bank_accounts'
        """)
        columns = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return columns

def fix_bank_accounts_schema():
    """Fix bank_accounts table schema"""
    print("=" * 80)
    print("MIGRATION: Fix bank_accounts Table Schema")
    print("=" * 80)
    print()

    if not check_table_exists():
        print("✗ Table 'bank_accounts' does not exist!")
        print("Creating table from scratch...")

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE bank_accounts (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id VARCHAR(100) NOT NULL,
                    account_name VARCHAR(255) NOT NULL,
                    institution_name VARCHAR(255) NOT NULL,
                    account_number VARCHAR(100),
                    account_number_encrypted TEXT,
                    routing_number VARCHAR(50),
                    account_type VARCHAR(50),
                    currency VARCHAR(3) DEFAULT 'USD',
                    current_balance DECIMAL(15,2),
                    available_balance DECIMAL(15,2),
                    last_sync_at TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'active',
                    is_primary BOOLEAN DEFAULT FALSE,
                    plaid_item_id TEXT,
                    plaid_access_token TEXT,
                    institution_logo_url TEXT,
                    account_color VARCHAR(7),
                    notes TEXT,
                    created_by VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(tenant_id, institution_name, account_number)
                )
            """)
            conn.commit()
            cursor.close()

        print("✓ Created bank_accounts table successfully")
        return

    # Get existing columns
    existing_columns = get_existing_columns()
    print(f"Found {len(existing_columns)} existing columns: {', '.join(existing_columns)}")
    print()

    # Define required columns with their types
    required_columns = {
        'institution_name': 'VARCHAR(255)',
        'current_balance': 'DECIMAL(15,2)',
        'available_balance': 'DECIMAL(15,2)',
        'last_sync_at': 'TIMESTAMP',
        'status': "VARCHAR(50) DEFAULT 'active'",
        'is_primary': 'BOOLEAN DEFAULT FALSE',
        'plaid_item_id': 'TEXT',
        'plaid_access_token': 'TEXT',
        'institution_logo_url': 'TEXT',
        'account_color': 'VARCHAR(7)',
        'notes': 'TEXT',
        'created_by': 'VARCHAR(100)',
        'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
        'account_number_encrypted': 'TEXT',
        'routing_number': 'VARCHAR(50)',
        'account_type': 'VARCHAR(50)',
        'currency': "VARCHAR(3) DEFAULT 'USD'"
    }

    # Add missing columns
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                print(f"Adding column: {column_name} ({column_type})")
                cursor.execute(f"""
                    ALTER TABLE bank_accounts
                    ADD COLUMN {column_name} {column_type}
                """)
                print(f"  ✓ Added {column_name}")

        conn.commit()
        cursor.close()

    print()
    print("✓ Migration completed successfully!")
    print("=" * 80)

if __name__ == '__main__':
    try:
        fix_bank_accounts_schema()
    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
