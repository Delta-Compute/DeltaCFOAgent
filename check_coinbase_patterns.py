#!/usr/bin/env python3
"""Check if Coinbase Bitcoin deposit transactions should have triggered patterns"""

import sys
sys.path.insert(0, '/Users/whitdhamer/DeltaCFOAgentv2/web_ui')

from database import DatabaseManager

db_manager = DatabaseManager()

print("=" * 80)
print("COINBASE BITCOIN DEPOSIT CLASSIFICATION TRACKING")
print("=" * 80)

# Get all classifications for transactions with "Received" and "Bitcoin deposit" in description
query = """
    SELECT
        uct.id,
        uct.created_at,
        uct.field_changed,
        uct.old_value,
        uct.new_value,
        uct.description_pattern,
        uct.origin,
        uct.destination,
        t.description as full_description
    FROM user_classification_tracking uct
    LEFT JOIN transactions t ON uct.transaction_id::text = t.transaction_id AND uct.tenant_id = t.tenant_id
    WHERE uct.tenant_id = 'delta'
    AND uct.description_pattern LIKE '%Received%'
    AND uct.description_pattern LIKE '%Bitcoin%'
    ORDER BY uct.created_at
"""

result = db_manager.execute_query(query, fetch_all=True)

print(f"\nFound {len(result) if result else 0} classifications for Coinbase Bitcoin deposits:\n")

if result and len(result) > 0:
    for i, row in enumerate(result, 1):
        print(f"{i}. ID: {row['id']} | {row['created_at']}")
        print(f"   Field: {row['field_changed']}")
        print(f"   Old: '{row['old_value']}' → New: '{row['new_value']}'")
        print(f"   Description Pattern: {row['description_pattern']}")
        print(f"   Full Description: {row['full_description']}")
        print(f"   Origin: {row['origin']} | Destination: {row['destination']}")
        print()

# Check if these should have triggered a pattern
print("=" * 80)
print("PATTERN TRIGGER ANALYSIS")
print("=" * 80)

# Group by field + new_value + description similarity
query = """
    SELECT
        field_changed,
        new_value,
        description_pattern,
        COUNT(*) as count,
        array_agg(id ORDER BY created_at) as record_ids
    FROM user_classification_tracking
    WHERE tenant_id = 'delta'
    AND description_pattern LIKE '%Received%'
    AND description_pattern LIKE '%Bitcoin%'
    GROUP BY field_changed, new_value, description_pattern
    ORDER BY count DESC
"""

result = db_manager.execute_query(query, fetch_all=True)

if result and len(result) > 0:
    print(f"\nGrouped patterns (exact description match):")
    for row in result:
        status = "🟢 SHOULD TRIGGER" if row['count'] >= 3 else f"🟡 {row['count']}/3"
        print(f"\n{status}")
        print(f"Field: {row['field_changed']} → {row['new_value']}")
        print(f"Description: {row['description_pattern']}")
        print(f"Count: {row['count']}")
        print(f"Record IDs: {row['record_ids']}")

# Check for trigram similarity (what the trigger uses)
print("\n" + "=" * 80)
print("TRIGRAM SIMILARITY CHECK")
print("=" * 80)

query = """
    SELECT DISTINCT description_pattern
    FROM user_classification_tracking
    WHERE tenant_id = 'delta'
    AND description_pattern LIKE '%Received%'
    AND description_pattern LIKE '%Bitcoin%'
"""

patterns = db_manager.execute_query(query, fetch_all=True)

if patterns and len(patterns) > 1:
    print(f"\nFound {len(patterns)} DIFFERENT description patterns:")
    for i, p in enumerate(patterns, 1):
        print(f"{i}. {p['description_pattern']}")

    print("\n⚠️ ISSUE FOUND: Each transaction has a DIFFERENT description!")
    print("The trigger requires description_pattern % NEW.description_pattern (trigram similarity)")
    print("BUT these descriptions are TOO DIFFERENT (different amounts in each)")
    print("\nThe trigger is matching TOO STRICTLY - it's looking for EXACT or very similar descriptions")
    print("But 'Received 0.00695...' and 'Received 0.00705...' are considered different!")
else:
    print("\nAll patterns match exactly - should have triggered!")

# Check actual pattern suggestions
print("\n" + "=" * 80)
print("ACTUAL PATTERN SUGGESTIONS CREATED")
print("=" * 80)

query = """
    SELECT id, pattern_type, supporting_classifications_count, status, created_at
    FROM pattern_suggestions
    WHERE tenant_id = 'delta'
    ORDER BY created_at DESC
"""

suggestions = db_manager.execute_query(query, fetch_all=True)

if suggestions and len(suggestions) > 0:
    print(f"\nFound {len(suggestions)} pattern suggestions:")
    for s in suggestions:
        print(f"ID: {s['id']} | Type: {s['pattern_type']} | Count: {s['supporting_classifications_count']} | Status: {s['status']}")
else:
    print("\nNO pattern suggestions found")
    print("\n❌ CONFIRMED: The trigger is NOT creating pattern suggestions!")
