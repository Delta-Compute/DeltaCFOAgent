#!/usr/bin/env python3
"""
Check what tenant data actually exists in the database
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_ui'))
from database import db_manager

with db_manager.get_connection() as conn:
    cursor = conn.cursor()

    print('=' * 70)
    print('TENANT CONFIGURATION FOR DELTA')
    print('=' * 70)

    # Check tenant_configuration table
    cursor.execute("""
        SELECT tenant_id, company_name, industry, description
        FROM tenant_configuration
        WHERE tenant_id = 'delta'
    """)

    config = cursor.fetchone()
    if config:
        print(f'\nTenant ID: {config[0]}')
        print(f'Company Name: {config[1]}')
        print(f'Industry: {config[2]}')
        print(f'Description: {config[3]}')
    else:
        print('\n❌ No tenant_configuration found for delta')

    print('\n' + '=' * 70)
    print('BUSINESS ENTITIES FOR DELTA')
    print('=' * 70)

    cursor.execute("""
        SELECT id, name, description, entity_type, active
        FROM business_entities
        WHERE tenant_id = 'delta'
        ORDER BY name
    """)

    entities = cursor.fetchall()
    if entities:
        print(f'\nFound {len(entities)} business entities:\n')
        for entity in entities:
            active_status = '✓' if entity[4] else '✗'
            print(f'{active_status} {entity[1]}')
            if entity[2]:
                print(f'  Description: {entity[2][:100]}')
            if entity[3]:
                print(f'  Type: {entity[3]}')
            print()
    else:
        print('\n❌ No business entities found for delta')

    print('=' * 70)
    print('CLASSIFICATION PATTERNS FOR DELTA')
    print('=' * 70)

    cursor.execute("""
        SELECT pattern_id, description_pattern, entity, accounting_category,
               accounting_subcategory, confidence_score
        FROM classification_patterns
        WHERE tenant_id = 'delta'
        ORDER BY created_at DESC
        LIMIT 10
    """)

    patterns = cursor.fetchall()
    if patterns:
        print(f'\nFound {len(patterns)} classification patterns:\n')
        for p in patterns:
            print(f'Pattern #{p[0]}:')
            print(f'  Pattern: {p[1][:80]}...' if len(p[1]) > 80 else f'  Pattern: {p[1]}')
            print(f'  Entity: {p[2]}')
            print(f'  Category: {p[3]}')
            if p[4]:
                print(f'  Subcategory: {p[4]}')
            print(f'  Confidence: {p[5]:.2f}')
            print()
    else:
        print('\n❌ No classification patterns found for delta')

    cursor.close()

    print('=' * 70)
