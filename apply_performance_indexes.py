#!/usr/bin/env python3
"""Apply performance indexes to PostgreSQL database"""

import sys
import os

# Add web_ui to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_ui'))

from database import db_manager

print("="*80)
print("APPLYING PERFORMANCE INDEXES TO DATABASE")
print("="*80)

# Read SQL file
with open('add_performance_indexes.sql', 'r') as f:
    sql_content = f.read()

# Split into individual statements (by semicolon)
statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip() and not stmt.strip().startswith('--')]

success_count = 0
error_count = 0

for i, statement in enumerate(statements, 1):
    # Skip comments and empty statements
    if statement.startswith('--') or not statement:
        continue

    # Extract index name for better logging
    if 'CREATE INDEX' in statement:
        try:
            index_name = statement.split('IF NOT EXISTS')[1].split('ON')[0].strip()
        except:
            index_name = f"statement_{i}"
    elif 'SELECT' in statement:
        index_name = "listing_indexes"
    else:
        index_name = f"statement_{i}"

    print(f"\n[{i}] Executing: {index_name}...")

    try:
        result = db_manager.execute_query(statement + ';')

        if result is not None and isinstance(result, list):
            print(f"    [OK] Success - {len(result)} rows returned")
            if index_name == "listing_indexes" and result:
                print("\n    Current indexes on transactions table:")
                for row in result:
                    print(f"      - {row.get('indexname', 'unknown')}")
        else:
            print(f"    [OK] Success")
        success_count += 1
    except Exception as e:
        print(f"    [ERROR] {e}")
        error_count += 1

print("\n" + "="*80)
print(f"SUMMARY: {success_count} successful, {error_count} errors")
print("="*80)

if error_count == 0:
    print("\n[SUCCESS] All performance indexes applied successfully!")
else:
    print(f"\n[WARNING] Some indexes may have failed. Check errors above.")
    sys.exit(1)
