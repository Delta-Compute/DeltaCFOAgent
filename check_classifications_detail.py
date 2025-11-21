#!/usr/bin/env python3
"""Check user classification details"""

import sys
sys.path.insert(0, '/Users/whitdhamer/DeltaCFOAgentv2/web_ui')

from database import DatabaseManager

db_manager = DatabaseManager()

print("=" * 80)
print("USER CLASSIFICATION DETAILS")
print("=" * 80)

# Get all user classifications with grouping
query = """
    SELECT
        description_pattern,
        new_value,
        origin,
        destination,
        COUNT(*) as count
    FROM user_classification_tracking
    WHERE tenant_id = 'delta'
    GROUP BY description_pattern, new_value, origin, destination
    ORDER BY count DESC, new_value, description_pattern
"""

result = db_manager.execute_query(query, fetch_all=True)

if result and len(result) > 0:
    print(f"\nFound {len(result)} unique pattern groups:\n")
    for i, row in enumerate(result, 1):
        print(f"{i}. Count: {row['count']}")
        print(f"   New Value: {row['new_value']}")
        print(f"   Description Pattern: {row['description_pattern']}")
        print(f"   Origin: {row['origin']}")
        print(f"   Destination: {row['destination']}")
        print()
else:
    print("No classifications found")

print("=" * 80)
print("SIMILARITY ANALYSIS")
print("=" * 80)

# Check for patterns that might be similar but not exactly matching
query = """
    SELECT
        description_pattern,
        new_value,
        COUNT(*) as count
    FROM user_classification_tracking
    WHERE tenant_id = 'delta'
    GROUP BY description_pattern, new_value
    HAVING COUNT(*) >= 2
    ORDER BY count DESC
"""

result = db_manager.execute_query(query, fetch_all=True)

if result and len(result) > 0:
    print(f"\nPatterns with 2+ occurrences (ignoring origin/destination):\n")
    for row in result:
        print(f"Count: {row['count']} | Value: {row['new_value']}")
        print(f"Pattern: {row['description_pattern']}")
        print()
else:
    print("\nNo patterns with 2+ occurrences found")

# Check individual records
print("=" * 80)
print("ALL INDIVIDUAL RECORDS")
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
"""

result = db_manager.execute_query(query, fetch_all=True)

if result and len(result) > 0:
    for i, row in enumerate(result, 1):
        print(f"\n{i}. ID: {row['id']} | Created: {row['created_at']}")
        print(f"   Field: {row['field_changed']}")
        print(f"   Old Value: {row['old_value']}")
        print(f"   New Value: {row['new_value']}")
        print(f"   Description: {row['description_pattern']}")
        print(f"   Origin: {row['origin']}")
        print(f"   Destination: {row['destination']}")

db_manager.close()
