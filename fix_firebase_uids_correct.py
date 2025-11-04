#!/usr/bin/env python3
"""
Fix Firebase UIDs with the CORRECT values from Firebase Console
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

# CORRECT UIDs from Firebase Console
CORRECT_UIDS = {
    'renan.donadon@leapsolutions.com.br': 'egfvUl0Gg7XIlD7PnIYgVVlcVMz2',
    'renan.salomao@leapsolutions.com.br': 'sgvJmHMSClYiz6xtjnxIGyg9YD'
}

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

def fix_uids():
    """Fix the Firebase UIDs"""
    print("\n" + "="*80)
    print("FIXING FIREBASE UIDs WITH CORRECT VALUES")
    print("="*80 + "\n")

    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            for email, correct_uid in CORRECT_UIDS.items():
                print(f"Updating: {email}")
                print(f"  New UID: {correct_uid}")

                # Get current UID
                cursor.execute("""
                    SELECT firebase_uid FROM users WHERE email = %s
                """, (email,))

                result = cursor.fetchone()
                if result:
                    print(f"  Old UID: {result['firebase_uid']}")

                # Update with correct UID
                cursor.execute("""
                    UPDATE users
                    SET firebase_uid = %s, email_verified = true
                    WHERE email = %s
                    RETURNING id
                """, (correct_uid, email))

                updated = cursor.fetchone()
                if updated:
                    print(f"  ✓ SUCCESS - User ID: {updated['id']}")
                else:
                    print(f"  ✗ FAILED - User not found")
                print()

            conn.commit()

            # Verify
            print("="*80)
            print("VERIFICATION")
            print("="*80 + "\n")

            for email in CORRECT_UIDS.keys():
                cursor.execute("""
                    SELECT email, firebase_uid, is_active, email_verified
                    FROM users
                    WHERE email = %s
                """, (email,))

                user = cursor.fetchone()
                if user:
                    print(f"✓ {user['email']}")
                    print(f"  UID: {user['firebase_uid']}")
                    print(f"  Active: {user['is_active']}")
                    print(f"  Verified: {user['email_verified']}")
                    print()

            print("="*80)
            print("DONE! Try logging in now!")
            print("="*80 + "\n")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_uids()
