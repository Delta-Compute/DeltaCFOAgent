#!/usr/bin/env python3
"""
Apply migration to add accounting_subcategory column to classification_patterns table
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_ui'))
from database import db_manager

def apply_migration():
    """Apply the accounting_subcategory migration"""

    print('=' * 70)
    print('ADDING accounting_subcategory COLUMN TO classification_patterns')
    print('=' * 70)

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()

        try:
            # Check if column already exists
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'classification_patterns'
                AND column_name = 'accounting_subcategory'
            """)

            if cursor.fetchone():
                print('\n✓ Column accounting_subcategory already exists in classification_patterns')
                cursor.close()
                return

            # Add the column
            print('\nAdding accounting_subcategory column...')
            cursor.execute("""
                ALTER TABLE classification_patterns
                ADD COLUMN accounting_subcategory VARCHAR(255)
            """)

            # Add comment
            cursor.execute("""
                COMMENT ON COLUMN classification_patterns.accounting_subcategory
                IS 'Subcategory for more granular transaction classification'
            """)

            conn.commit()

            print('✓ Successfully added accounting_subcategory column')

            # Verify
            cursor.execute("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'classification_patterns'
                AND column_name = 'accounting_subcategory'
            """)

            result = cursor.fetchone()
            if result:
                print(f'\nVerified: {result[0]} ({result[1]}({result[2]}))')

            cursor.close()

        except Exception as e:
            print(f'\n✗ Error applying migration: {e}')
            conn.rollback()
            raise

    print('\n' + '=' * 70)
    print('MIGRATION COMPLETED SUCCESSFULLY')
    print('=' * 70)

if __name__ == '__main__':
    apply_migration()
