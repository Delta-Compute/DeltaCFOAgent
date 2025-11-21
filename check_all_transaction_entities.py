#!/usr/bin/env python3
"""Check all distinct entities in transactions table"""

import sys
sys.path.append('web_ui')

from database import db_manager

# Get all distinct entities from transactions
query = """
SELECT DISTINCT classified_entity, COUNT(*) as transaction_count
FROM transactions
WHERE tenant_id = 'delta'
AND classified_entity IS NOT NULL
AND classified_entity <> 'Unknown Entity'
GROUP BY classified_entity
ORDER BY classified_entity
"""

result = db_manager.execute_query(query, fetch_all=True)

print('All entities in transactions table:')
print('=' * 80)
for row in result:
    print(f'{row["classified_entity"]:<50} | {row["transaction_count"]:>5} transactions')

print('\n' + '=' * 80)
print(f'Total distinct entities: {len(result)}')

# Now check which ones are in business_entities
print('\n' + '=' * 80)
print('Checking against business_entities table:')
print('=' * 80)

orphaned = []
for row in result:
    entity_name = row['classified_entity']
    check_query = """
    SELECT name FROM business_entities
    WHERE tenant_id = 'delta' AND name = %s
    """
    exists = db_manager.execute_query(check_query, (entity_name,), fetch_one=True)

    if exists:
        print(f'✓  {entity_name:<50} | In business_entities')
    else:
        print(f'❌ {entity_name:<50} | NOT in business_entities')
        orphaned.append(entity_name)

if orphaned:
    print('\n' + '=' * 80)
    print(f'Found {len(orphaned)} orphaned entities:')
    for entity in orphaned:
        print(f'  - {entity}')
