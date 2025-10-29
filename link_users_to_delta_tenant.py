#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Link all users to delta tenant"""
import sys
import io
import uuid

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from web_ui.database import db_manager

print("=" * 80)
print("LINK USERS TO DELTA TENANT")
print("=" * 80)

try:
    # Step 1: Get all users
    print("\n[1/3] Getting all users...")
    users = db_manager.execute_query(
        """
        SELECT u.id, u.email, u.user_type,
               (SELECT COUNT(*) FROM tenant_users tu WHERE tu.user_id = u.id) as tenant_count
        FROM users u
        WHERE u.is_active = true
        ORDER BY u.email
        """,
        fetch_all=True
    )
    print(f"[OK] Found {len(users)} active users")

    # Step 2: Find users without tenants
    print("\n[2/3] Finding users without tenant links...")
    users_without_tenant = [u for u in users if u['tenant_count'] == 0]

    if not users_without_tenant:
        print("[OK] All users are already linked to tenants!")
        sys.exit(0)

    print(f"[WARNING] Found {len(users_without_tenant)} users without tenant:")
    for user in users_without_tenant:
        print(f"  - {user['email']} ({user['user_type']})")

    # Step 3: Link users to delta tenant
    print("\n[3/3] Linking users to 'delta' tenant...")
    linked_count = 0
    failed_count = 0

    for user in users_without_tenant:
        try:
            tenant_user_id = str(uuid.uuid4())
            link_query = """
                INSERT INTO tenant_users (id, user_id, tenant_id, role, permissions, is_active)
                VALUES (%s, %s, %s, %s, %s, true)
                ON CONFLICT (user_id, tenant_id) DO NOTHING
                RETURNING id
            """
            result = db_manager.execute_query(
                link_query,
                (tenant_user_id, user['id'], 'delta', 'employee', '{}'),
                fetch_one=True
            )

            if result:
                print(f"[OK] Linked: {user['email']}")
                linked_count += 1
            else:
                print(f"[SKIP] Already linked: {user['email']}")

        except Exception as e:
            print(f"[ERROR] Failed to link {user['email']}: {e}")
            failed_count += 1

    print("\n" + "=" * 80)
    print("LINK COMPLETE!")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  - Total users: {len(users)}")
    print(f"  - Users without tenant: {len(users_without_tenant)}")
    print(f"  - Successfully linked: {linked_count}")
    print(f"  - Failed: {failed_count}")

    if linked_count > 0:
        print(f"\n[INFO] Linked users have been:")
        print(f"       - Assigned to tenant: 'delta'")
        print(f"       - Given role: 'employee'")
        print(f"       - Set as active")
        print(f"\n[NOTE] You may want to update their roles manually if needed")

    print("=" * 80)

except Exception as e:
    print(f"\n[ERROR] Link failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
