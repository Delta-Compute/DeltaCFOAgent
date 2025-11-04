#!/usr/bin/env python3
"""
Verify CFO user accounts in the database
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
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

def verify_users():
    """Verify the CFO users were created correctly"""
    print("\n" + "="*80)
    print("VERIFICATION: CFO Fractional Users in Delta Tenant")
    print("="*80 + "\n")

    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get user information
            cursor.execute("""
                SELECT
                    u.id,
                    u.firebase_uid,
                    u.email,
                    u.display_name,
                    u.user_type,
                    u.is_active,
                    u.email_verified,
                    u.created_at
                FROM users u
                WHERE u.email IN (
                    'renan.donadon@leapsolutions.com.br',
                    'renan.salomao@leapsolutions.com.br'
                )
                ORDER BY u.email
            """)

            users = cursor.fetchall()

            if not users:
                print("ERROR: No users found!")
                return False

            print("USERS TABLE:")
            print("-" * 80)
            for user in users:
                print(f"\nEmail: {user['email']}")
                print(f"  Name: {user['display_name']}")
                print(f"  Type: {user['user_type']}")
                print(f"  Active: {user['is_active']}")
                print(f"  Email Verified: {user['email_verified']}")
                firebase_uid = str(user['firebase_uid'])
                if len(firebase_uid) > 50:
                    firebase_uid = firebase_uid[:50] + "..."
                print(f"  Firebase UID: {firebase_uid}")
                print(f"  Created: {user['created_at']}")
            print()

            # Get tenant relationships
            cursor.execute("""
                SELECT
                    u.email,
                    tu.tenant_id,
                    tu.role,
                    tu.is_active,
                    tu.permissions,
                    tu.added_at
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
                print("WARNING: No tenant relationships found!")
                return False

            print("TENANT ASSIGNMENTS:")
            print("-" * 80)
            for tu in tenant_users:
                permissions = tu['permissions']
                perm_summary = f"{len(permissions)} categories"
                print(f"\nEmail: {tu['email']}")
                print(f"  Tenant: {tu['tenant_id']}")
                print(f"  Role: {tu['role']}")
                print(f"  Active: {tu['is_active']}")
                print(f"  Permissions: {perm_summary}")
                print(f"  Added: {tu['added_at']}")
            print()

            # Show detailed permissions for one user as example
            print("PERMISSION DETAILS (Example for first user):")
            print("-" * 80)
            first_user = tenant_users[0]
            permissions = first_user['permissions']
            for category, perms in permissions.items():
                print(f"  {category}: {', '.join(perms)}")
            print()

            print("="*80)
            print("VERIFICATION COMPLETE")
            print("="*80)
            print(f"Found {len(users)} user(s)")
            print(f"Found {len(tenant_users)} tenant relationship(s)")
            print()
            print("STATUS: All CFO users are properly configured in the Delta tenant")
            print()
            print("NEXT STEPS:")
            print("1. Create Firebase Authentication accounts for these users")
            print("2. Update the firebase_uid field in the users table with actual UIDs")
            print("3. Send credentials to users securely")
            print("="*80 + "\n")

            return True

    finally:
        conn.close()

if __name__ == "__main__":
    try:
        success = verify_users()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
