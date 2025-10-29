#!/usr/bin/env python3
"""
Script to remove orphaned user from PostgreSQL database
"""
from web_ui.database import db_manager

# Email to remove
email = 'ariel@delta-mining.com'

# First, check if user exists
query = "SELECT id, firebase_uid, email FROM users WHERE email = %s"
result = db_manager.execute_query(query, (email,), fetch_one=True)

if result:
    print(f"Found user:")
    print(f"  ID: {result['id']}")
    print(f"  Firebase UID: {result['firebase_uid']}")
    print(f"  Email: {result['email']}")

    # Delete from tenant_users first (foreign key constraint)
    delete_tenant_users = "DELETE FROM tenant_users WHERE user_id = %s"
    db_manager.execute_query(delete_tenant_users, (result['id'],))
    print(f"  Deleted from tenant_users")

    # Delete from users table
    delete_user = "DELETE FROM users WHERE id = %s"
    db_manager.execute_query(delete_user, (result['id'],))
    print(f"  Deleted from users table")

    print(f"User {email} successfully removed from database")
else:
    print(f"No user found with email: {email}")
