#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create a new tenant with admin user

This script creates a complete tenant setup including:
1. Tenant configuration
2. Admin user (if needed)
3. User-tenant relationship
"""
import sys
import io
import uuid
import argparse

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from web_ui.database import db_manager
from auth.firebase_config import initialize_firebase, create_firebase_user

print("=" * 80)
print("CREATE NEW TENANT")
print("=" * 80)

# Parse arguments
parser = argparse.ArgumentParser(description='Create a new tenant')
parser.add_argument('--tenant-id', required=True, help='Unique tenant ID (e.g., nascimento)')
parser.add_argument('--company-name', required=True, help='Company name')
parser.add_argument('--company-tagline', default='', help='Company tagline')
parser.add_argument('--company-description', default='', help='Company description')
parser.add_argument('--admin-email', required=True, help='Admin user email')
parser.add_argument('--admin-name', required=True, help='Admin user display name')
parser.add_argument('--admin-password', help='Admin password (if creating new user)')
parser.add_argument('--existing-user', action='store_true', help='Use existing user as admin')
args = parser.parse_args()

try:
    # Step 1: Check if tenant already exists
    print(f"\n[1/5] Checking if tenant '{args.tenant_id}' exists...")
    existing_tenant = db_manager.execute_query(
        "SELECT id, company_name FROM tenant_configuration WHERE id = %s",
        (args.tenant_id,),
        fetch_one=True
    )

    if existing_tenant:
        print(f"[ERROR] Tenant '{args.tenant_id}' already exists: {existing_tenant['company_name']}")
        sys.exit(1)

    print(f"[OK] Tenant ID '{args.tenant_id}' is available")

    # Step 2: Create tenant
    print(f"\n[2/5] Creating tenant '{args.company_name}'...")
    db_manager.execute_query(
        """
        INSERT INTO tenant_configuration (
            id, tenant_id, company_name, company_tagline, company_description, is_active
        )
        VALUES (%s, %s, %s, %s, %s, true)
        """,
        (
            args.tenant_id,
            args.tenant_id,  # tenant_id same as id
            args.company_name,
            args.company_tagline or f'{args.company_name} - Financial Management',
            args.company_description or f'{args.company_name} - Powered by Delta CFO Agent',
        )
    )
    print(f"[OK] Tenant created: {args.company_name}")

    # Step 3: Check if admin user exists
    print(f"\n[3/5] Checking admin user '{args.admin_email}'...")
    existing_user = db_manager.execute_query(
        "SELECT id, email, display_name, user_type FROM users WHERE email = %s",
        (args.admin_email,),
        fetch_one=True
    )

    user_id = None
    firebase_uid = None

    if existing_user:
        if args.existing_user:
            print(f"[OK] Using existing user: {existing_user['email']} ({existing_user['user_type']})")
            user_id = existing_user['id']
        else:
            print(f"[ERROR] User {args.admin_email} already exists. Use --existing-user to link existing user.")
            sys.exit(1)
    else:
        # Create new user
        if not args.admin_password:
            print("[ERROR] --admin-password required for new user creation")
            sys.exit(1)

        print(f"[INFO] Creating new user in Firebase...")
        initialize_firebase()
        firebase_user = create_firebase_user(args.admin_email, args.admin_password, args.admin_name)

        if not firebase_user:
            print(f"[ERROR] Failed to create Firebase user. Email may already be in use.")
            sys.exit(1)

        print(f"[OK] Firebase user created")

        # Create user in database
        user_id = str(uuid.uuid4())
        db_manager.execute_query(
            """
            INSERT INTO users (id, firebase_uid, email, display_name, user_type, is_active, email_verified)
            VALUES (%s, %s, %s, %s, %s, true, false)
            """,
            (user_id, firebase_user['uid'], args.admin_email, args.admin_name, 'tenant_admin')
        )
        print(f"[OK] Database user created: {args.admin_email}")

    # Step 4: Link user to tenant as owner
    print(f"\n[4/5] Linking user to tenant as 'owner'...")
    tenant_user_id = str(uuid.uuid4())

    db_manager.execute_query(
        """
        INSERT INTO tenant_users (id, user_id, tenant_id, role, permissions, is_active)
        VALUES (%s, %s, %s, %s, %s, true)
        ON CONFLICT (user_id, tenant_id) DO UPDATE SET role = 'owner', is_active = true
        """,
        (
            tenant_user_id,
            user_id,
            args.tenant_id,
            'owner',
            '{}'  # Empty permissions - owner has all permissions
        )
    )
    print(f"[OK] User linked as owner")

    # Step 5: Verify setup
    print(f"\n[5/5] Verifying tenant setup...")
    tenant = db_manager.execute_query(
        """
        SELECT tc.id, tc.company_name, tc.company_tagline,
               COUNT(tu.id) as user_count
        FROM tenant_configuration tc
        LEFT JOIN tenant_users tu ON tc.id = tu.tenant_id AND tu.is_active = true
        WHERE tc.id = %s
        GROUP BY tc.id, tc.company_name, tc.company_tagline
        """,
        (args.tenant_id,),
        fetch_one=True
    )

    print("\n" + "=" * 80)
    print("TENANT CREATED SUCCESSFULLY!")
    print("=" * 80)
    print(f"\nTenant Information:")
    print(f"  - ID: {tenant['id']}")
    print(f"  - Company Name: {tenant['company_name']}")
    print(f"  - Tagline: {tenant['company_tagline']}")
    print(f"  - Active Users: {tenant['user_count']}")
    print(f"\nAdmin User:")
    print(f"  - Email: {args.admin_email}")
    print(f"  - Name: {args.admin_name}")
    print(f"  - Role: owner")
    print(f"\nNext Steps:")
    print(f"  1. Admin should verify their email")
    print(f"  2. Admin can invite other users via the web interface")
    print(f"  3. Configure tenant settings in the admin panel")
    print("=" * 80)

except Exception as e:
    print(f"\n[ERROR] Tenant creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
