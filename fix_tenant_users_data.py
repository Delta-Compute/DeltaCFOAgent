#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix tenant_users data - update tenant_id from 1 to 'delta'"""
import sys
import io

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from web_ui.database import db_manager

print("=" * 80)
print("FIXING TENANT_USERS DATA")
print("=" * 80)

try:
    # Step 1: Check current data
    print("\n[1/3] Checking tenant_users data...")
    tenant_users = db_manager.execute_query(
        "SELECT id, user_id, tenant_id FROM tenant_users",
        fetch_all=True
    )
    print(f"[OK] Found {len(tenant_users)} tenant_user relationships")
    for tu in tenant_users:
        print(f"     - user_id: {tu['user_id']}, tenant_id: {tu['tenant_id']}")

    # Step 2: Update tenant_id from 1 to 'delta'
    print("\n[2/3] Updating tenant_id from 1 to 'delta'...")
    db_manager.execute_query(
        "UPDATE tenant_users SET tenant_id = 'delta' WHERE tenant_id = '1'"
    )
    print("[OK] Updated tenant_id values")

    # Step 3: Verify
    print("\n[3/3] Verifying changes...")
    updated_users = db_manager.execute_query(
        "SELECT id, user_id, tenant_id FROM tenant_users",
        fetch_all=True
    )
    print(f"[OK] After update:")
    for tu in updated_users:
        print(f"     - user_id: {tu['user_id']}, tenant_id: {tu['tenant_id']}")

    print("\n" + "=" * 80)
    print("SUCCESS: TENANT_USERS DATA FIXED!")
    print("=" * 80)

except Exception as e:
    print(f"\n[ERROR] Fix failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
