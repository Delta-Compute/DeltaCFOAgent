#!/usr/bin/env python3
"""
Check actual database schema for business_entities and classification_patterns
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_ui'))
from database import db_manager

with db_manager.get_connection() as conn:
    cursor = conn.cursor()

    print('=' * 70)
    print('DATABASE SCHEMA CHECK')
    print('=' * 70)

    # Check business_entities columns
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'business_entities'
        ORDER BY ordinal_position
    """)

    print('\nbusiness_entities table columns:')
    for row in cursor.fetchall():
        print(f'  - {row[0]} ({row[1]})')

    # Check classification_patterns columns
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'classification_patterns'
        ORDER BY ordinal_position
    """)

    print('\nclassification_patterns table columns:')
    for row in cursor.fetchall():
        print(f'  - {row[0]} ({row[1]})')

    cursor.close()

    print('\n' + '=' * 70)
