#!/usr/bin/env python3
"""Check shareholders in database"""

import sys
sys.path.append('web_ui')

from database import db_manager

# Check shareholders
query = """
SELECT id, shareholder_name, entity, share_class, safe_terms, tenant_id, created_at
FROM shareholders
WHERE tenant_id = 'delta'
ORDER BY created_at DESC
LIMIT 10
"""

result = db_manager.execute_query(query, fetch_all=True)

print('Shareholders in database:')
print('=' * 80)
if result:
    for row in result:
        print(f"ID: {row['id']}")
        print(f"Name: {row['shareholder_name']}")
        print(f"Entity: {row['entity']}")
        print(f"Share Class: {row['share_class']}")
        print(f"SAFE Terms: {row['safe_terms']}")
        print(f"Tenant: {row['tenant_id']}")
        print(f"Created: {row['created_at']}")
        print('-' * 80)
else:
    print('No shareholders found')
