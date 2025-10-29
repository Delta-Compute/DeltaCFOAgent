#!/usr/bin/env python3
"""Migrate existing tenant IDs from integers to strings"""
from web_ui.database import db_manager

print("Migrating existing tenant IDs...")
print("=" * 60)

# Get all tenants
tenants = db_manager.execute_query(
    "SELECT id, tenant_id, company_name FROM tenant_configuration ORDER BY id",
    fetch_all=True
)

print(f"\nFound {len(tenants)} tenants:")
for tenant in tenants:
    print(f"  ID: {tenant['id']:<10} tenant_id: {tenant['tenant_id']:<10} company: {tenant['company_name']}")

if len(tenants) == 0:
    print("\nNo tenants to migrate.")
    exit(0)

# If there's a tenant with id='1' and tenant_id='delta', update it
delta_tenant = [t for t in tenants if t['id'] == '1' and t['tenant_id'] == 'delta']

if delta_tenant:
    print("\n[INFO] Found tenant with ID='1' and tenant_id='delta'")
    print("[INFO] Updating ID from '1' to 'delta'...")

    # This is tricky because we need to:
    # 1. Temporarily disable the foreign key constraint
    # 2. Update the ID
    # 3. Re-enable the constraint

    try:
        # Update the ID
        db_manager.execute_query(
            "UPDATE tenant_configuration SET id = %s WHERE id = %s",
            ('delta', '1')
        )
        print("[OK] Tenant ID updated from '1' to 'delta'")

        # Verify
        updated_tenant = db_manager.execute_query(
            "SELECT id, tenant_id, company_name FROM tenant_configuration WHERE id = 'delta'",
            fetch_one=True
        )

        if updated_tenant:
            print(f"[OK] Verified: {updated_tenant['id']} - {updated_tenant['company_name']}")
        else:
            print("[ERROR] Tenant not found after update!")

    except Exception as e:
        print(f"[ERROR] Failed to update tenant ID: {e}")
        print("[INFO] This might be because there are dependent records.")
        print("[INFO] You may need to update dependent tables first.")

else:
    print("\n[INFO] No tenant with ID='1' found. Migration not needed.")

print("\n" + "=" * 60)
print("Migration complete!")
