#!/usr/bin/env python3
"""
Migration: Add institution_name column to bank_accounts table

This migration adds the institution_name column that was missing from the production database
but exists in the schema file.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_ui.database import db_manager

def check_column_exists():
    """Check if the column already exists"""
    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'bank_accounts'
            AND column_name = 'institution_name'
        """)
        result = cursor.fetchone()
        cursor.close()
        return result is not None

def add_institution_name_column():
    """Add institution_name column to bank_accounts table"""
    print("=" * 80)
    print("MIGRATION: Add institution_name to bank_accounts")
    print("=" * 80)
    print()

    # Check if column already exists
    if check_column_exists():
        print("✓ Column 'institution_name' already exists in bank_accounts table")
        print("  No migration needed.")
        return

    print("Adding institution_name column to bank_accounts table...")

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        # Add the column
        cursor.execute("""
            ALTER TABLE bank_accounts
            ADD COLUMN IF NOT EXISTS institution_name VARCHAR(255)
        """)

        # Update existing rows with a default value
        cursor.execute("""
            UPDATE bank_accounts
            SET institution_name = 'Unknown Institution'
            WHERE institution_name IS NULL
        """)

        # Make the column NOT NULL after setting default values
        cursor.execute("""
            ALTER TABLE bank_accounts
            ALTER COLUMN institution_name SET NOT NULL
        """)

        conn.commit()
        cursor.close()

    print("✓ Successfully added institution_name column")
    print()
    print("Migration completed successfully!")
    print("=" * 80)

if __name__ == '__main__':
    try:
        add_institution_name_column()
    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        sys.exit(1)
