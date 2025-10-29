#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List all users of a specific tenant"""
import sys
import io
import argparse

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from web_ui.database import db_manager

# Parse arguments
parser = argparse.ArgumentParser(description='List users of a tenant')
parser.add_argument('--tenant-id', required=True, help='Tenant ID')
args = parser.parse_args()

print("=" * 80)
print(f"USERS OF TENANT: {args.tenant_id}")
print("=" * 80)

# Get tenant info
tenant = db_manager.execute_query(
    "SELECT id, company_name, company_tagline FROM tenant_configuration WHERE id = %s",
    (args.tenant_id,),
    fetch_one=True
)

if not tenant:
    print(f"\n[ERROR] Tenant '{args.tenant_id}' not found")
    sys.exit(1)

print(f"\nTenant: {tenant['company_name']}")
print(f"Tagline: {tenant['company_tagline'] or '(none)'}")
print()

# Get users
users = db_manager.execute_query(
    """
    SELECT
        u.email,
        u.display_name,
        u.user_type,
        u.email_verified,
        u.is_active as user_active,
        tu.role,
        tu.is_active as tenant_active,
        tu.added_at
    FROM tenant_users tu
    JOIN users u ON tu.user_id = u.id
    WHERE tu.tenant_id = %s
    ORDER BY
        CASE tu.role
            WHEN 'owner' THEN 1
            WHEN 'admin' THEN 2
            WHEN 'cfo' THEN 3
            WHEN 'cfo_assistant' THEN 4
            WHEN 'employee' THEN 5
        END,
        tu.added_at
    """,
    (args.tenant_id,),
    fetch_all=True
)

if not users:
    print("[INFO] No users found for this tenant")
else:
    print(f"Found {len(users)} user(s):\n")
    print("-" * 80)

    for user in users:
        status = "[ACTIVE]" if user['tenant_active'] and user['user_active'] else "[INACTIVE]"
        verified = "[VERIFIED]" if user['email_verified'] else "[NOT VERIFIED]"

        print(f"Email: {user['email']}")
        print(f"  Name: {user['display_name']}")
        print(f"  Role: {user['role']}")
        print(f"  Type: {user['user_type']}")
        print(f"  Status: {status} {verified}")
        print(f"  Added: {user['added_at']}")
        print()

print("=" * 80)
