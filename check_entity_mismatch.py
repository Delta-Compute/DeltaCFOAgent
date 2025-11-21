#!/usr/bin/env python3
"""Check for entity name mismatches between business_entities and transactions"""

import sys
sys.path.append('web_ui')

from database import db_manager

# Check for entity name mismatches
query = """
SELECT DISTINCT t.classified_entity, be.name as business_entity_name
FROM transactions t
LEFT JOIN business_entities be ON t.classified_entity = be.name AND t.tenant_id = be.tenant_id
WHERE t.tenant_id = 'delta'
AND t.classified_entity IS NOT NULL
AND t.classified_entity <> 'Unknown Entity'
ORDER BY t.classified_entity
LIMIT 30
"""

result = db_manager.execute_query(query, fetch_all=True)

print('Entity mismatches in transactions vs business_entities:')
print('=' * 80)
orphaned = []
matched = []

for row in result:
    if row['business_entity_name'] is None:
        orphaned.append(row['classified_entity'])
        print(f'❌ Transaction entity: {row["classified_entity"]:<50} | NOT in business_entities')
    else:
        matched.append(row['classified_entity'])
        print(f'✓  Transaction entity: {row["classified_entity"]:<50} | Matches')

print('\n' + '=' * 80)
print(f'Summary: {len(matched)} matched, {len(orphaned)} orphaned')

if orphaned:
    print('\nOrphaned entities (in transactions but not in business_entities):')
    for entity in orphaned:
        print(f'  - {entity}')
