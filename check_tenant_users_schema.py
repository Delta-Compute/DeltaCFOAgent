#!/usr/bin/env python3
"""Check tenant_users table schema"""
from web_ui.database import db_manager

query = """
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'tenant_users'
ORDER BY ordinal_position;
"""

columns = db_manager.execute_query(query, fetch_all=True)

print("tenant_users table schema:")
print("-" * 60)
for col in columns:
    length = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
    print(f"{col['column_name']:<30} {col['data_type']}{length}")
