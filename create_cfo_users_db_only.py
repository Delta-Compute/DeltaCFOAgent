#!/usr/bin/env python3
"""
Create CFO Fractional users in database with provisional Firebase UIDs
This script creates database records for CFO users that can be linked to Firebase accounts later
"""
import os
import sys
import secrets
import string
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

def generate_strong_password(length=16):
    """Generate a strong random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

def get_db_connection():
    """Get PostgreSQL database connection"""
    # Try DATABASE_URL first (for Cloud Run)
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        conn = psycopg2.connect(db_url)
        return conn

    # Otherwise, use individual database settings
    db_config = {
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
    }

    # Add SSL mode if specified
    ssl_mode = os.getenv('DB_SSL_MODE')
    if ssl_mode:
        db_config['sslmode'] = ssl_mode

    # Check required fields
    if not all([db_config['host'], db_config['database'], db_config['user'], db_config['password']]):
        raise ValueError("Missing required database configuration. Please set DB_HOST, DB_NAME, DB_USER, and DB_PASSWORD")

    conn = psycopg2.connect(**db_config)
    return conn

def create_user_in_database(conn, email, display_name, provisional_password, user_type='fractional_cfo'):
    """Create user record in PostgreSQL database with provisional Firebase UID"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check if user already exists
            cursor.execute(
                "SELECT id, firebase_uid, email FROM users WHERE email = %s",
                (email,)
            )
            existing_user = cursor.fetchone()

            if existing_user:
                print(f"  User already exists in database: {existing_user['email']}")
                print(f"  User ID: {existing_user['id']}")
                print(f"  Firebase UID: {existing_user['firebase_uid']}")
                return existing_user['id'], existing_user['firebase_uid']

            # Generate provisional Firebase UID (will be updated when Firebase account is created)
            # Use a prefix to identify provisional UIDs
            firebase_uid = f"provisional_{uuid.uuid4().hex}"

            # Insert new user
            cursor.execute("""
                INSERT INTO users (firebase_uid, email, display_name, user_type, is_active, email_verified)
                VALUES (%s, %s, %s, %s, true, false)
                RETURNING id
            """, (firebase_uid, email, display_name, user_type))

            user_id = cursor.fetchone()['id']
            conn.commit()
            print(f"  User created in database with ID: {user_id}")
            print(f"  Provisional Firebase UID: {firebase_uid}")
            return user_id, firebase_uid

    except Exception as e:
        conn.rollback()
        print(f"  ERROR creating user in database: {e}")
        raise

def add_user_to_tenant(conn, user_id, tenant_id='delta', role='cfo'):
    """Add user to tenant with CFO role"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check if relationship already exists
            cursor.execute(
                "SELECT id FROM tenant_users WHERE user_id = %s AND tenant_id = %s",
                (user_id, tenant_id)
            )
            existing = cursor.fetchone()

            if existing:
                print(f"  User already assigned to tenant {tenant_id}")
                return existing['id']

            # Define CFO permissions - full access
            cfo_permissions = {
                "transactions": ["view", "create", "edit", "delete", "export"],
                "invoices": ["view", "create", "edit", "delete", "approve"],
                "users": ["view", "invite"],
                "reports": ["view", "generate", "export"],
                "settings": ["view", "edit"],
                "accounts": ["view", "manage"]
            }

            # Insert tenant_user relationship
            cursor.execute("""
                INSERT INTO tenant_users (user_id, tenant_id, role, permissions, is_active)
                VALUES (%s, %s, %s, %s, true)
                RETURNING id
            """, (user_id, tenant_id, role, psycopg2.extras.Json(cfo_permissions)))

            tenant_user_id = cursor.fetchone()['id']
            conn.commit()
            print(f"  User assigned to tenant {tenant_id} with role: {role}")
            return tenant_user_id

    except Exception as e:
        conn.rollback()
        print(f"  ERROR adding user to tenant: {e}")
        raise

def create_audit_log(conn, user_id, tenant_id, action, metadata):
    """Create audit log entry"""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO audit_log (user_id, tenant_id, action, resource_type, metadata, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, tenant_id, action, 'user', psycopg2.extras.Json(metadata), datetime.now(timezone.utc)))
            conn.commit()
    except Exception as e:
        print(f"  Warning: Failed to create audit log: {e}")

def create_cfo_user(email, display_name, tenant_id='delta'):
    """Create a complete CFO user account in database"""
    print(f"\n{'='*60}")
    print(f"Creating CFO Fractional User: {email}")
    print(f"{'='*60}")

    try:
        # Generate strong password
        password = generate_strong_password()

        # Connect to database
        print("Step 1: Creating database records...")
        conn = get_db_connection()

        try:
            # Create user in database
            user_id, firebase_uid = create_user_in_database(
                conn,
                email,
                display_name,
                password,
                user_type='fractional_cfo'
            )

            # Add user to tenant
            print(f"\nStep 2: Assigning user to tenant '{tenant_id}'...")
            add_user_to_tenant(conn, user_id, tenant_id, role='cfo')

            # Create audit log
            create_audit_log(conn, user_id, tenant_id, 'user.created', {
                'email': email,
                'user_type': 'fractional_cfo',
                'role': 'cfo',
                'created_by': 'system_script',
                'status': 'provisional - Firebase account pending'
            })

            print(f"\n{'='*60}")
            print("SUCCESS! User database record created")
            print(f"{'='*60}")
            print(f"Email: {email}")
            print(f"Provisional Password: {password}")
            print(f"User Type: Fractional CFO")
            print(f"Tenant: {tenant_id}")
            print(f"Role: CFO")
            print(f"Database ID: {user_id}")
            print(f"\nNOTE: Firebase account must be created separately")
            print(f"The provisional Firebase UID will be updated when the")
            print(f"actual Firebase account is linked.")
            print(f"{'='*60}\n")

            return {
                'email': email,
                'password': password,
                'firebase_uid': firebase_uid,
                'user_id': user_id
            }

        finally:
            conn.close()

    except Exception as e:
        print(f"\nERROR: Failed to create user: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main function to create both CFO users"""
    print("\n" + "="*60)
    print("Delta CFO Agent - Create CFO Fractional Users")
    print("Database-Only Mode (Firebase accounts to be created separately)")
    print("="*60)

    # List of CFO users to create
    cfo_users = [
        {
            'email': 'renan.donadon@leapsolutions.com.br',
            'display_name': 'Renan Donadon'
        },
        {
            'email': 'renan.salomao@leapsolutions.com.br',
            'display_name': 'Renan Salomao'
        }
    ]

    results = []

    for user_info in cfo_users:
        result = create_cfo_user(
            email=user_info['email'],
            display_name=user_info['display_name'],
            tenant_id='delta'
        )

        if result:
            results.append(result)

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY - Created Users")
    print("="*60)

    if results:
        print("\nDatabase records created successfully!\n")
        for result in results:
            print(f"User: {result['email']}")
            print(f"  Provisional Password: {result['password']}")
            print(f"  Database ID: {result['user_id']}")
            print(f"  Provisional Firebase UID: {result['firebase_uid']}")
            print()

        print("="*60)
        print("NEXT STEPS:")
        print("="*60)
        print("1. Create Firebase accounts manually or through Firebase Console")
        print("2. Update the 'firebase_uid' in the users table with actual UIDs")
        print("3. Send login credentials to users securely")
        print("4. Users should change passwords on first login")
        print()
        print("Firebase Console: https://console.firebase.google.com")
        print("="*60 + "\n")

        # Generate SQL update statements for convenience
        print("="*60)
        print("SQL UPDATE STATEMENTS (for after Firebase account creation):")
        print("="*60)
        for result in results:
            print(f"\n-- Update Firebase UID for {result['email']}")
            print(f"UPDATE users SET firebase_uid = 'YOUR_FIREBASE_UID_HERE', email_verified = true")
            print(f"WHERE email = '{result['email']}';")

        print("\n" + "="*60 + "\n")
    else:
        print("\nNo users were created. Please check the errors above.\n")

    return len(results) > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
