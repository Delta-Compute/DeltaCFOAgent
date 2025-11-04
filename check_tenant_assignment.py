#!/usr/bin/env python3
"""
Check tenant assignment for CFO users in detail
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

def check_everything():
    """Check all tenant assignments"""
    print("\n" + "="*80)
    print("COMPLETE TENANT ASSIGNMENT CHECK")
    print("="*80 + "\n")

    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # 1. Check if 'delta' tenant exists
            print("1. CHECKING IF 'delta' TENANT EXISTS:")
            print("-" * 80)
            cursor.execute("""
                SELECT id, company_name, description
                FROM tenant_configuration
            """)
            all_tenants = cursor.fetchall()

            print(f"Found {len(all_tenants)} tenant(s) in tenant_configuration:\n")
            delta_exists = False
            for tenant in all_tenants:
                is_delta = " <- TARGET TENANT" if tenant['id'] == 'delta' else ""
                print(f"  ID: {tenant['id']}{is_delta}")
                print(f"    Name: {tenant['company_name']}")
                print(f"    Description: {tenant['description'] or '(empty)'}")
                print()
                if tenant['id'] == 'delta':
                    delta_exists = True

            if not delta_exists:
                print("ERROR: 'delta' tenant NOT FOUND in tenant_configuration!")
                print("Available tenants:", [t['id'] for t in all_tenants])
                return False

            # 2. Check users
            print("\n2. CHECKING CFO USERS:")
            print("-" * 80)
            cursor.execute("""
                SELECT id, firebase_uid, email, display_name, user_type
                FROM users
                WHERE email IN (
                    'renan.donadon@leapsolutions.com.br',
                    'renan.salomao@leapsolutions.com.br'
                )
            """)
            users = cursor.fetchall()

            if not users:
                print("ERROR: CFO users NOT FOUND!")
                return False

            print(f"Found {len(users)} user(s):\n")
            user_ids = []
            for user in users:
                print(f"  Email: {user['email']}")
                print(f"    ID: {user['id']}")
                print(f"    Firebase UID: {user['firebase_uid']}")
                print()
                user_ids.append(user['id'])

            # 3. Check tenant_users assignments
            print("\n3. CHECKING TENANT_USERS ASSIGNMENTS:")
            print("-" * 80)
            cursor.execute("""
                SELECT
                    tu.id,
                    tu.user_id,
                    tu.tenant_id,
                    tu.role,
                    tu.is_active,
                    u.email
                FROM tenant_users tu
                JOIN users u ON tu.user_id = u.id
                WHERE u.email IN (
                    'renan.donadon@leapsolutions.com.br',
                    'renan.salomao@leapsolutions.com.br'
                )
            """)
            tenant_users = cursor.fetchall()

            if not tenant_users:
                print("ERROR: NO tenant_users assignments found for CFO users!")
                print("\nThese users exist but have NO tenant assignments:")
                for user in users:
                    print(f"  - {user['email']} (ID: {user['id']})")
                print("\nNeed to create tenant_users records!")
                return False

            print(f"Found {len(tenant_users)} assignment(s):\n")
            correct_assignments = 0
            for tu in tenant_users:
                is_delta = tu['tenant_id'] == 'delta'
                status = "OK" if is_delta else "WRONG TENANT!"

                print(f"  [{status}] {tu['email']}")
                print(f"    Tenant ID: {tu['tenant_id']}")
                print(f"    Role: {tu['role']}")
                print(f"    Is Active: {tu['is_active']}")
                print(f"    Assignment ID: {tu['id']}")
                print()

                if is_delta:
                    correct_assignments += 1

            # 4. Summary
            print("\n" + "="*80)
            print("SUMMARY")
            print("="*80)
            print(f"Delta tenant exists: {'YES' if delta_exists else 'NO'}")
            print(f"CFO users found: {len(users)}")
            print(f"Tenant assignments: {len(tenant_users)}")
            print(f"Correct (delta) assignments: {correct_assignments}")
            print()

            if correct_assignments == len(users):
                print("STATUS: ALL USERS CORRECTLY ASSIGNED TO 'delta' TENANT")
                print("="*80 + "\n")
                return True
            else:
                print("STATUS: SOME USERS NOT ASSIGNED TO 'delta' TENANT")
                print("\nISSUES TO FIX:")
                if not delta_exists:
                    print("  - 'delta' tenant doesn't exist")
                if len(tenant_users) == 0:
                    print("  - No tenant_users records exist")
                elif correct_assignments < len(users):
                    print("  - Some users assigned to wrong tenant")
                print("="*80 + "\n")
                return False

    finally:
        conn.close()

if __name__ == "__main__":
    try:
        success = check_everything()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
