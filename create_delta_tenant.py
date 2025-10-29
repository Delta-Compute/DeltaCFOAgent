#!/usr/bin/env python3
"""Create delta tenant"""
from web_ui.database import db_manager

print("Creating 'delta' tenant...")

db_manager.execute_query(
    """
    INSERT INTO tenant_configuration (
        id, tenant_id, company_name, company_tagline, company_description, is_active
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO NOTHING
    """,
    (
        'delta',
        'delta',  # tenant_id same as id
        'Delta Mining & Computing',
        'AI-Powered CFO Intelligence',
        'Delta Mining & Computing Company - Financial Management Platform',
        True
    )
)

print("[OK] Delta tenant created/verified!")

# Verify
tenant = db_manager.execute_query(
    "SELECT id, company_name FROM tenant_configuration WHERE id = 'delta'",
    fetch_one=True
)

if tenant:
    print(f"[OK] Tenant verified: {tenant['id']} - {tenant['company_name']}")
else:
    print("[ERROR] Tenant not found after creation!")
