#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add existing user to a tenant with specified role
"""
import sys
import io
import uuid
import argparse

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from web_ui.database import db_manager

print("=" * 80)
print("ADD USER TO TENANT")
print("=" * 80)

# Parse arguments
parser = argparse.ArgumentParser(description='Add user to tenant')
parser.add_argument('--tenant-id', required=True, help='Tenant ID')
parser.add_argument('--user-email', required=True, help='User email')
parser.add_argument('--role', required=True, choices=['owner', 'admin', 'cfo', 'cfo_assistant', 'employee'], help='User role')
args = parser.parse_args()

try:
    # Step 1: Check if tenant exists
    print(f"\n[1/4] Checking tenant '{args.tenant_id}'...")
    tenant = db_manager.execute_query(
        "SELECT id, company_name FROM tenant_configuration WHERE id = %s",
        (args.tenant_id,),
        fetch_one=True
    )

    if not tenant:
        print(f"[ERROR] Tenant '{args.tenant_id}' not found")
        sys.exit(1)

    print(f"[OK] Tenant found: {tenant['company_name']}")

    # Step 2: Check if user exists
    print(f"\n[2/4] Checking user '{args.user_email}'...")
    user = db_manager.execute_query(
        "SELECT id, email, display_name, user_type FROM users WHERE email = %s",
        (args.user_email,),
        fetch_one=True
    )

    if not user:
        print(f"[ERROR] User '{args.user_email}' not found")
        print("[INFO] Create user first with create_new_tenant.py or Firebase registration")
        sys.exit(1)

    print(f"[OK] User found: {user['display_name']} ({user['user_type']})")

    # Step 3: Check if already linked
    print(f"\n[3/4] Checking existing relationship...")
    existing = db_manager.execute_query(
        """
        SELECT id, role, is_active
        FROM tenant_users
        WHERE user_id = %s AND tenant_id = %s
        """,
        (user['id'], args.tenant_id),
        fetch_one=True
    )

    if existing:
        if existing['is_active']:
            print(f"[WARNING] User already linked as '{existing['role']}'")
            print(f"[INFO] Updating role to '{args.role}'...")

            db_manager.execute_query(
                """
                UPDATE tenant_users
                SET role = %s
                WHERE user_id = %s AND tenant_id = %s
                """,
                (args.role, user['id'], args.tenant_id)
            )
            print(f"[OK] Role updated to '{args.role}'")
        else:
            print(f"[INFO] User was previously linked but inactive")
            print(f"[INFO] Reactivating with role '{args.role}'...")

            db_manager.execute_query(
                """
                UPDATE tenant_users
                SET role = %s, is_active = true
                WHERE user_id = %s AND tenant_id = %s
                """,
                (args.role, user['id'], args.tenant_id)
            )
            print(f"[OK] User reactivated as '{args.role}'")
    else:
        # Step 4: Create new relationship
        print(f"\n[4/4] Linking user to tenant as '{args.role}'...")
        tenant_user_id = str(uuid.uuid4())

        db_manager.execute_query(
            """
            INSERT INTO tenant_users (id, user_id, tenant_id, role, permissions, is_active)
            VALUES (%s, %s, %s, %s, %s, true)
            """,
            (tenant_user_id, user['id'], args.tenant_id, args.role, '{}')
        )
        print(f"[OK] User linked successfully")

    # Verify final state
    print(f"\n[VERIFY] Checking final state...")
    final_state = db_manager.execute_query(
        """
        SELECT tu.role, tu.is_active,
               u.email, u.display_name,
               tc.company_name
        FROM tenant_users tu
        JOIN users u ON tu.user_id = u.id
        JOIN tenant_configuration tc ON tu.tenant_id = tc.tenant_id
        WHERE u.email = %s AND tc.tenant_id = %s
        """,
        (args.user_email, args.tenant_id),
        fetch_one=True
    )

    print("\n" + "=" * 80)
    print("USER ADDED TO TENANT SUCCESSFULLY!")
    print("=" * 80)
    print(f"\nUser: {final_state['display_name']} ({final_state['email']})")
    print(f"Tenant: {final_state['company_name']}")
    print(f"Role: {final_state['role']}")
    print(f"Status: {'Active' if final_state['is_active'] else 'Inactive'}")
    print("\n" + "=" * 80)

except Exception as e:
    print(f"\n[ERROR] Operation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
