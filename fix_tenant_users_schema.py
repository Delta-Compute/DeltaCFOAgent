#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix tenant_users table tenant_id column type"""
import sys
import io

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from web_ui.database import db_manager

print("=" * 80)
print("FIXING TENANT_USERS SCHEMA")
print("=" * 80)

try:
    # Step 1: Check current type
    print("\n[1/5] Checking current schema...")
    current_type = db_manager.execute_query(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = 'tenant_users' AND column_name = 'tenant_id'
        """,
        fetch_one=True
    )
    print(f"[OK] tenant_users.tenant_id is: {current_type['data_type']}")

    if current_type['data_type'] != 'integer':
        print(f"\n[SKIP] Column is already {current_type['data_type']}")
        sys.exit(0)

    # Step 2: Drop foreign key constraint
    print("\n[2/5] Dropping foreign key constraint...")
    db_manager.execute_query(
        """
        ALTER TABLE tenant_users
        DROP CONSTRAINT IF EXISTS tenant_users_tenant_id_fkey
        """
    )
    print("[OK] Foreign key constraint dropped")

    # Step 3: Change column type
    print("\n[3/5] Changing tenant_id to VARCHAR(50)...")
    db_manager.execute_query(
        """
        ALTER TABLE tenant_users
        ALTER COLUMN tenant_id TYPE VARCHAR(50)
        """
    )
    print("[OK] Column type changed")

    # Step 4: Re-add foreign key constraint
    print("\n[4/5] Re-adding foreign key constraint...")
    db_manager.execute_query(
        """
        ALTER TABLE tenant_users
        ADD CONSTRAINT tenant_users_tenant_id_fkey
        FOREIGN KEY (tenant_id) REFERENCES tenant_configuration(id) ON DELETE CASCADE
        """
    )
    print("[OK] Foreign key constraint re-added")

    # Step 5: Verify
    print("\n[5/5] Verifying changes...")
    new_type = db_manager.execute_query(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_name = 'tenant_users' AND column_name = 'tenant_id'
        """,
        fetch_one=True
    )
    print(f"[OK] tenant_users.tenant_id is now: {new_type['data_type']}")

    print("\n" + "=" * 80)
    print("SUCCESS: TENANT_USERS SCHEMA FIXED!")
    print("=" * 80)

except Exception as e:
    print(f"\n[ERROR] Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
