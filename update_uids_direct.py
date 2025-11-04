#!/usr/bin/env python3
"""
Update Firebase UIDs directly with provided UIDs
"""
import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

# UIDs from Firebase
UPDATES = [
    {
        'email': 'renan.donadon@leapsolutions.com.br',
        'firebase_uid': '6SwcynWVFhSjGnWq4IJIEihASBx2',
        'name': 'Renan Donadon'
    },
    {
        'email': 'renan.salomao@leapsolutions.com.br',
        'firebase_uid': 'mF5lyVt5XtW6stpc6H0RE4JG6vH2',
        'name': 'Renan Salomao'
    }
]

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

def update_user(conn, email, firebase_uid, name):
    """Update user's Firebase UID"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get current user info
            cursor.execute("""
                SELECT id, firebase_uid, email_verified, is_active
                FROM users
                WHERE email = %s
            """, (email,))

            user = cursor.fetchone()
            if not user:
                print(f"  ERROR: User not found: {email}")
                return False

            old_uid = user['firebase_uid']
            print(f"\n  User ID: {user['id']}")
            print(f"  Old Firebase UID: {old_uid}")
            print(f"  New Firebase UID: {firebase_uid}")

            # Update Firebase UID
            cursor.execute("""
                UPDATE users
                SET firebase_uid = %s, email_verified = true
                WHERE email = %s
                RETURNING id, firebase_uid, email_verified
            """, (firebase_uid, email))

            updated = cursor.fetchone()
            conn.commit()

            if updated:
                print(f"  Status: SUCCESS")
                print(f"  Email Verified: {updated['email_verified']}")
                return True
            else:
                print(f"  Status: FAILED")
                return False

    except Exception as e:
        conn.rollback()
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    print("\n" + "="*80)
    print("Update Firebase UIDs - Direct Update")
    print("="*80)

    conn = get_db_connection()
    results = []

    try:
        for update_info in UPDATES:
            print(f"\n{'='*80}")
            print(f"Updating: {update_info['name']}")
            print(f"Email: {update_info['email']}")
            print(f"{'='*80}")

            success = update_user(
                conn,
                update_info['email'],
                update_info['firebase_uid'],
                update_info['name']
            )

            results.append({
                'name': update_info['name'],
                'email': update_info['email'],
                'uid': update_info['firebase_uid'],
                'success': success
            })

        # Summary
        print("\n" + "="*80)
        print("UPDATE SUMMARY")
        print("="*80)

        success_count = sum(1 for r in results if r['success'])
        print(f"\nTotal Updates: {len(results)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {len(results) - success_count}\n")

        for result in results:
            status = "✓ SUCCESS" if result['success'] else "✗ FAILED"
            print(f"{status}: {result['name']}")
            print(f"         Email: {result['email']}")
            print(f"         UID: {result['uid']}")
            print()

        if success_count == len(results):
            print("="*80)
            print("ALL USERS UPDATED SUCCESSFULLY!")
            print("="*80)
            print("\nBoth CFO users are now ready to login:")
            print("- renan.donadon@leapsolutions.com.br")
            print("- renan.salomao@leapsolutions.com.br")
            print("\nPasswords:")
            print("- Renan Donadon: EvrXvLs3Twk6%14o")
            print("- Renan Salomao: &2s1$dVYxTi#LBQS")
            print("\nNext steps:")
            print("1. Run verification: python verify_cfo_users.py")
            print("2. Send credentials to users securely")
            print("3. Instruct them to change password on first login")
            print("="*80 + "\n")
            return True
        else:
            print("\nSome updates failed. Check errors above.\n")
            return False

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
