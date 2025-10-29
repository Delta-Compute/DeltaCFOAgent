#!/usr/bin/env python3
"""List all users in Firebase and database"""
from auth.firebase_config import initialize_firebase
from firebase_admin import auth
from web_ui.database import db_manager

print("=" * 80)
print("USER LIST - FIREBASE vs DATABASE")
print("=" * 80)

# Initialize Firebase
initialize_firebase()

# Get Firebase users
print("\n[FIREBASE USERS]")
print("-" * 80)
fb_users = []
page = auth.list_users()
while page:
    for user in page.users:
        fb_users.append(user)
        verified = "[VERIFIED]" if user.email_verified else "[NOT VERIFIED]"
        print(f"  {user.email:<40} {verified}")
    page = page.get_next_page()

print(f"\nTotal Firebase users: {len(fb_users)}")

# Get database users
print("\n[DATABASE USERS]")
print("-" * 80)
db_users = db_manager.execute_query(
    """
    SELECT u.email, u.display_name, u.user_type, u.email_verified, u.is_active,
           COALESCE(
               (SELECT COUNT(*) FROM tenant_users tu WHERE tu.user_id = u.id AND tu.is_active = true),
               0
           ) as tenant_count
    FROM users u
    ORDER BY u.email
    """,
    fetch_all=True
)

for user in db_users:
    status = "[ACTIVE]" if user['is_active'] else "[INACTIVE]"
    verified = "[VERIFIED]" if user['email_verified'] else "[NOT VERIFIED]"
    tenants = f"(tenants: {user['tenant_count']})"
    print(f"  {user['email']:<40} {user['user_type']:<20} {status} {verified} {tenants}")

print(f"\nTotal database users: {len(db_users)}")

print("\n" + "=" * 80)
