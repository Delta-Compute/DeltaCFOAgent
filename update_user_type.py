#!/usr/bin/env python3
"""
Update user type from fractional_cfo to tenant_admin
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web_ui.database import db_manager

def update_user_type(email, new_user_type):
    """Update user type for a specific user"""
    try:
        # Update user type
        update_query = """
            UPDATE users
            SET user_type = %s
            WHERE email = %s
            RETURNING id, email, user_type, display_name
        """
        result = db_manager.execute_query(
            update_query,
            (new_user_type, email),
            fetch_one=True
        )

        if result:
            print(f"✓ Updated user: {result['email']}")
            print(f"  User Type: {result['user_type']}")
            print(f"  Display Name: {result['display_name']}")
            print(f"  User ID: {result['id']}")
            return True
        else:
            print(f"✗ User not found: {email}")
            return False

    except Exception as e:
        print(f"✗ Error updating user: {e}")
        return False

if __name__ == '__main__':
    email = 'whit@delta-mining.com'
    new_type = 'tenant_admin'

    print(f"Updating user {email} to {new_type}...")
    success = update_user_type(email, new_type)

    sys.exit(0 if success else 1)
