#!/usr/bin/env python3
"""Check recent classification tracking records"""

import sys
sys.path.insert(0, '/Users/whitdhamer/DeltaCFOAgentv2/web_ui')

from database import DatabaseManager

db_manager = DatabaseManager()

print("=" * 80)
print("RECENT CLASSIFICATION TRACKING RECORDS (Last 20)")
print("=" * 80)

query = """
    SELECT
        id,
        created_at,
        field_changed,
        old_value,
        new_value,
        description_pattern,
        origin,
        destination
    FROM user_classification_tracking
    WHERE tenant_id = 'delta'
    ORDER BY created_at DESC
    LIMIT 20
"""

result = db_manager.execute_query(query, fetch_all=True)

if result and len(result) > 0:
    for row in result:
        same_value = "⚠️ SAME" if row['old_value'] == row['new_value'] else "✅ CHANGED"
        print(f"\nID: {row['id']} | {row['created_at']} | {same_value}")
        print(f"Field: {row['field_changed']}")
        print(f"Old: '{row['old_value']}' → New: '{row['new_value']}'")
        print(f"Description: {row['description_pattern']}")
        print(f"Origin: {row['origin']} | Destination: {row['destination']}")
else:
    print("No tracking records found")

print("\n" + "=" * 80)
print("ANALYSIS")
print("=" * 80)

# Count records with same old/new values
query = """
    SELECT COUNT(*) as count
    FROM user_classification_tracking
    WHERE tenant_id = 'delta'
    AND old_value = new_value
"""
result = db_manager.execute_query(query, fetch_one=True)
same_value_count = result['count'] if result else 0

# Count total
query = "SELECT COUNT(*) as count FROM user_classification_tracking WHERE tenant_id = 'delta'"
result = db_manager.execute_query(query, fetch_one=True)
total_count = result['count'] if result else 0

print(f"\nTotal tracking records: {total_count}")
print(f"Records with SAME old/new value: {same_value_count}")
print(f"Records with ACTUAL changes: {total_count - same_value_count}")

if same_value_count > 0:
    print("\n⚠️ WARNING: Some tracking records have identical old and new values!")
    print("These records are created when you update a field to the value it already has.")
    print("The trigger uses description + value matching, so these won't group with real changes.")
