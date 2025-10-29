#!/usr/bin/env python3
"""Check user_role_enum values"""
from web_ui.database import db_manager

query = """
SELECT enumlabel
FROM pg_enum
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'user_role_enum')
ORDER BY enumsortorder;
"""

values = db_manager.execute_query(query, fetch_all=True)

print("user_role_enum valid values:")
print("-" * 40)
for v in values:
    print(f"  - {v['enumlabel']}")
