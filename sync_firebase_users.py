#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Synchronize Firebase users with PostgreSQL database

This script finds Firebase users that don't exist in the database
and creates corresponding database records for them.
"""
import sys
import io
import uuid
import argparse

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Parse command line arguments
parser = argparse.ArgumentParser(description='Sync Firebase users to database')
parser.add_argument('--auto-confirm', action='store_true', help='Automatically confirm sync without prompting')
args = parser.parse_args()

from auth.firebase_config import initialize_firebase
from firebase_admin import auth
from web_ui.database import db_manager

print("=" * 80)
print("FIREBASE TO DATABASE USER SYNCHRONIZATION")
print("=" * 80)

try:
    # Initialize Firebase
    print("\n[1/5] Initializing Firebase...")
    initialize_firebase()
    print("[OK] Firebase initialized")

    # Get all Firebase users
    print("\n[2/5] Fetching all Firebase users...")
    firebase_users = []
    page = auth.list_users()

    while page:
        for user in page.users:
            firebase_users.append({
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name or user.email.split('@')[0],
                'email_verified': user.email_verified
            })
        page = page.get_next_page()

    print(f"[OK] Found {len(firebase_users)} Firebase users")

    # Get all database users
    print("\n[3/5] Fetching all database users...")
    db_users_query = "SELECT firebase_uid FROM users WHERE firebase_uid IS NOT NULL"
    db_result = db_manager.execute_query(db_users_query, fetch_all=True)
    db_firebase_uids = {row['firebase_uid'] for row in (db_result or [])}
    print(f"[OK] Found {len(db_firebase_uids)} users in database")

    # Find Firebase users not in database
    print("\n[4/5] Finding users to sync...")
    users_to_sync = []
    for fb_user in firebase_users:
        if fb_user['uid'] not in db_firebase_uids:
            users_to_sync.append(fb_user)

    if not users_to_sync:
        print("[OK] All Firebase users already exist in database!")
        print("\n" + "=" * 80)
        print("SYNC COMPLETE - NO ACTION NEEDED")
        print("=" * 80)
        sys.exit(0)

    print(f"[WARNING] Found {len(users_to_sync)} users to sync:")
    for user in users_to_sync:
        print(f"  - {user['email']} (uid: {user['uid'][:20]}...)")

    # Ask for confirmation
    if not args.auto_confirm:
        print(f"\n[CONFIRM] Create database records for these {len(users_to_sync)} users?")
        print("          Default user_type will be 'tenant_admin'")
        print("          They will be assigned to 'delta' tenant with 'viewer' role")
        try:
            confirm = input("\nContinue? [y/N]: ").strip().lower()
            if confirm != 'y':
                print("[CANCELLED] User sync cancelled")
                sys.exit(0)
        except EOFError:
            print("\n[ERROR] Cannot prompt in non-interactive mode. Use --auto-confirm flag.")
            sys.exit(1)
    else:
        print(f"\n[AUTO-CONFIRM] Creating database records for {len(users_to_sync)} users...")

    # Sync users
    print("\n[5/5] Creating database users...")
    created_count = 0
    failed_count = 0

    for fb_user in users_to_sync:
        try:
            user_id = str(uuid.uuid4())

            # Create user in database
            create_user_query = """
                INSERT INTO users (id, firebase_uid, email, display_name, user_type, is_active, email_verified)
                VALUES (%s, %s, %s, %s, %s, true, %s)
                ON CONFLICT (firebase_uid) DO NOTHING
                RETURNING id
            """
            result = db_manager.execute_query(
                create_user_query,
                (
                    user_id,
                    fb_user['uid'],
                    fb_user['email'],
                    fb_user['display_name'],
                    'tenant_admin',  # Default user type
                    fb_user['email_verified']
                ),
                fetch_one=True
            )

            if result:
                # Link user to delta tenant
                tenant_user_id = str(uuid.uuid4())
                link_query = """
                    INSERT INTO tenant_users (id, user_id, tenant_id, role, permissions, is_active)
                    VALUES (%s, %s, %s, %s, %s, true)
                    ON CONFLICT (user_id, tenant_id) DO NOTHING
                """
                db_manager.execute_query(
                    link_query,
                    (tenant_user_id, user_id, 'delta', 'viewer', '{}')
                )

                print(f"[OK] Created: {fb_user['email']}")
                created_count += 1
            else:
                print(f"[SKIP] Already exists (race condition): {fb_user['email']}")

        except Exception as e:
            print(f"[ERROR] Failed to create {fb_user['email']}: {e}")
            failed_count += 1

    print("\n" + "=" * 80)
    print("SYNC COMPLETE!")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  - Firebase users: {len(firebase_users)}")
    print(f"  - Database users before: {len(db_firebase_uids)}")
    print(f"  - Users to sync: {len(users_to_sync)}")
    print(f"  - Successfully created: {created_count}")
    print(f"  - Failed: {failed_count}")
    print(f"  - Total database users now: {len(db_firebase_uids) + created_count}")

    if created_count > 0:
        print("\n[INFO] Synced users have been:")
        print("       - Assigned user_type: 'tenant_admin'")
        print("       - Linked to tenant: 'delta'")
        print("       - Given role: 'viewer'")
        print("       - Set as active")
        print("\n[NOTE] You may want to update their roles and permissions manually")

    print("=" * 80)

except Exception as e:
    print(f"\n[ERROR] Sync failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
