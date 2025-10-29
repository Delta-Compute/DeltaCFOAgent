#!/usr/bin/env python3
"""List all tenants in the system"""
from web_ui.database import db_manager

print("=" * 80)
print("ALL TENANTS IN SYSTEM")
print("=" * 80)

tenants = db_manager.execute_query(
    """
    SELECT
        tc.id,
        tc.company_name,
        tc.company_tagline,
        tc.is_active,
        tc.created_at,
        COUNT(DISTINCT tu.user_id) as user_count,
        COUNT(DISTINCT CASE WHEN tu.role = 'owner' THEN tu.user_id END) as owner_count
    FROM tenant_configuration tc
    LEFT JOIN tenant_users tu ON tc.id = tu.tenant_id AND tu.is_active = true
    GROUP BY tc.id, tc.company_name, tc.company_tagline, tc.is_active, tc.created_at
    ORDER BY tc.created_at DESC
    """,
    fetch_all=True
)

if not tenants:
    print("\n[INFO] No tenants found in system")
else:
    print(f"\nFound {len(tenants)} tenant(s):\n")

    for tenant in tenants:
        status = "[ACTIVE]" if tenant['is_active'] else "[INACTIVE]"
        print(f"Tenant ID: {tenant['id']}")
        print(f"  Company: {tenant['company_name']}")
        print(f"  Tagline: {tenant['company_tagline'] or '(none)'}")
        print(f"  Status: {status}")
        print(f"  Users: {tenant['user_count']} (Owners: {tenant['owner_count']})")
        print(f"  Created: {tenant['created_at']}")
        print()

print("=" * 80)
