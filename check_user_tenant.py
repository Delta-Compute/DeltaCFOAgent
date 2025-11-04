#!/usr/bin/env python3
"""
Check user and tenant configuration for authentication debugging
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

def get_db_connection():
    """Get PostgreSQL database connection"""
    db_config = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
    }

    ssl_mode = os.getenv('DB_SSL_MODE')
    if ssl_mode:
        db_config['sslmode'] = ssl_mode

    conn = psycopg2.connect(**db_config)
    return conn

def check_users():
    """Check user configuration"""
    print("\n" + "="*80)
    print("USER & TENANT AUTHENTICATION DEBUG")
    print("="*80 + "\n")

    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check users
            print("1. USERS TABLE:")
            print("-" * 80)
            cursor.execute("""
                SELECT
                    id,
                    firebase_uid,
                    email,
                    display_name,
                    user_type,
                    is_active,
                    email_verified,
                    created_at
                FROM users
                WHERE email IN (
                    'renan.donadon@leapsolutions.com.br',
                    'renan.salomao@leapsolutions.com.br'
                )
                ORDER BY email
            """)

            users = cursor.fetchall()
            if not users:
                print("ERROR: No users found!")
                return

            for user in users:
                print(f"\nEmail: {user['email']}")
                print(f"  ID: {user['id']}")
                print(f"  Firebase UID: {user['firebase_uid']}")
                print(f"  Display Name: {user['display_name']}")
                print(f"  User Type: {user['user_type']}")
                print(f"  Is Active: {user['is_active']}")
                print(f"  Email Verified: {user['email_verified']}")

            # Check tenant_users
            print("\n\n2. TENANT_USERS TABLE:")
            print("-" * 80)
            cursor.execute("""
                SELECT
                    tu.id,
                    tu.user_id,
                    tu.tenant_id,
                    tu.role,
                    tu.is_active,
                    tu.added_at,
                    u.email,
                    u.display_name
                FROM tenant_users tu
                JOIN users u ON tu.user_id = u.id
                WHERE u.email IN (
                    'renan.donadon@leapsolutions.com.br',
                    'renan.salomao@leapsolutions.com.br'
                )
                ORDER BY u.email
            """)

            tenant_users = cursor.fetchall()
            if not tenant_users:
                print("ERROR: No tenant_users relationships found!")
                return

            for tu in tenant_users:
                print(f"\nEmail: {tu['email']}")
                print(f"  Tenant ID: {tu['tenant_id']}")
                print(f"  Role: {tu['role']}")
                print(f"  Is Active: {tu['is_active']}")
                print(f"  User ID: {tu['user_id']}")
                print(f"  Added At: {tu['added_at']}")

            # Check tenant_configuration
            print("\n\n3. TENANT_CONFIGURATION TABLE:")
            print("-" * 80)
            cursor.execute("""
                SELECT
                    id,
                    company_name,
                    description,
                    created_at
                FROM tenant_configuration
                WHERE id = 'delta'
            """)

            tenant = cursor.fetchone()
            if tenant:
                print(f"\nTenant ID: {tenant['id']}")
                print(f"  Company Name: {tenant['company_name']}")
                print(f"  Description: {tenant['description']}")
                print(f"  Created At: {tenant['created_at']}")
            else:
                print("ERROR: Tenant 'delta' not found!")
                print("\nChecking all tenants:")
                cursor.execute("SELECT id, company_name FROM tenant_configuration")
                all_tenants = cursor.fetchall()
                for t in all_tenants:
                    print(f"  - {t['id']}: {t['company_name']}")

            # Check complete authentication flow
            print("\n\n4. COMPLETE AUTHENTICATION QUERY:")
            print("-" * 80)
            print("\nQuery that authentication middleware should use:")
            cursor.execute("""
                SELECT
                    u.id as user_id,
                    u.firebase_uid,
                    u.email,
                    u.display_name,
                    u.user_type,
                    u.is_active as user_active,
                    tu.tenant_id,
                    tu.role,
                    tu.is_active as tenant_user_active,
                    tu.permissions,
                    tc.company_name as tenant_name
                FROM users u
                JOIN tenant_users tu ON u.id = tu.user_id
                JOIN tenant_configuration tc ON tu.tenant_id = tc.id
                WHERE u.firebase_uid IN (
                    '6SwcynWVFhSjGnWq4IJIEihASBx2',
                    'mF5lyVt5XtW6stpc6H0RE4JG6vH2'
                )
                AND u.is_active = true
                AND tu.is_active = true
            """)

            auth_data = cursor.fetchall()
            if not auth_data:
                print("ERROR: Authentication query returned no results!")
                print("This means the middleware won't find these users!")
            else:
                for data in auth_data:
                    print(f"\nFirebase UID: {data['firebase_uid']}")
                    print(f"  User ID: {data['user_id']}")
                    print(f"  Email: {data['email']}")
                    print(f"  User Type: {data['user_type']}")
                    print(f"  Tenant ID: {data['tenant_id']}")
                    print(f"  Tenant Name: {data['tenant_name']}")
                    print(f"  Role: {data['role']}")
                    print(f"  User Active: {data['user_active']}")
                    print(f"  Tenant User Active: {data['tenant_user_active']}")
                    print(f"  Permissions: {len(data['permissions'])} categories")

            print("\n" + "="*80)
            print("DEBUG COMPLETE")
            print("="*80 + "\n")

    finally:
        conn.close()

if __name__ == "__main__":
    try:
        check_users()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
