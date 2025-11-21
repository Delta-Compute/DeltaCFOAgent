#!/usr/bin/env python3
"""
Find entities in transactions that don't match business_entities.
This identifies entities that need to be updated after merging in /tenant-knowledge page.
"""

import sys
sys.path.append('web_ui')

from database import db_manager

tenant_id = 'delta'

# Get all entities from business_entities (the source of truth after merge)
print("=" * 80)
print("CURRENT BUSINESS ENTITIES (source of truth):")
print("=" * 80)
business_entities_query = """
SELECT name, entity_type
FROM business_entities
WHERE tenant_id = %s
AND active = true
ORDER BY name
"""
business_entities = db_manager.execute_query(business_entities_query, (tenant_id,), fetch_all=True)
business_entity_names = set()
for entity in business_entities:
    print(f"  {entity['name']:<50} ({entity['entity_type']})")
    business_entity_names.add(entity['name'])

print(f"\nTotal: {len(business_entities)} active business entities")

# Get all distinct entities from transactions
print("\n" + "=" * 80)
print("ENTITIES IN TRANSACTIONS:")
print("=" * 80)
transaction_entities_query = """
SELECT DISTINCT classified_entity, COUNT(*) as count
FROM transactions
WHERE tenant_id = %s
AND classified_entity IS NOT NULL
AND classified_entity <> 'Unknown Entity'
GROUP BY classified_entity
ORDER BY classified_entity
"""
transaction_entities = db_manager.execute_query(transaction_entities_query, (tenant_id,), fetch_all=True)

unmatched = []
matched = []

for entity in transaction_entities:
    name = entity['classified_entity']
    count = entity['count']
    if name in business_entity_names:
        matched.append((name, count))
        print(f"✓  {name:<50} ({count:>5} txns) - MATCHED")
    else:
        unmatched.append((name, count))
        print(f"❌ {name:<50} ({count:>5} txns) - NOT IN business_entities")

print("\n" + "=" * 80)
print("SUMMARY:")
print("=" * 80)
print(f"Matched entities:   {len(matched)}")
print(f"Unmatched entities: {len(unmatched)}")
print(f"Total transactions with unmatched entities: {sum(count for _, count in unmatched)}")

if unmatched:
    print("\n" + "=" * 80)
    print("ORPHANED ENTITIES (in transactions but not in business_entities):")
    print("=" * 80)
    for name, count in unmatched:
        print(f"  • {name:<50} ({count:>5} transactions)")

    print("\n" + "=" * 80)
    print("RECOMMENDATION:")
    print("=" * 80)
    print("These entities exist in transactions but were likely merged or deleted")
    print("from business_entities. You should either:")
    print("  1. Add them back to business_entities (if they should exist)")
    print("  2. Update transactions to use the merged entity name")
    print("\nTo fix, you can:")
    print("  • Run fix_entity_sync.py to add them to business_entities")
    print("  • OR manually update transactions to use the correct merged entity")
