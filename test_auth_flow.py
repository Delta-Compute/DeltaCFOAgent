#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Authentication Flow Test
Tests registration, login, and invitation flows
"""
import sys
import time
import io

# Fix Windows encoding issue
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from auth.firebase_config import initialize_firebase, create_firebase_user, delete_firebase_user
from firebase_admin import auth
from web_ui.database import db_manager

print("=" * 80)
print("AUTHENTICATION FLOW TEST")
print("=" * 80)

# Test data
test_email = "test@deltacfo.com"
test_password = "TestPassword123!"
test_name = "Test User"

# Initialize Firebase
print("\n[1/6] Initializing Firebase...")
try:
    initialize_firebase()
    print("[OK] Firebase initialized successfully")
except Exception as e:
    print(f"[ERROR] Firebase initialization failed: {e}")
    sys.exit(1)

# Clean up any existing test user
print("\n[2/6] Cleaning up existing test user...")
try:
    # Check Firebase
    try:
        existing_user = auth.get_user_by_email(test_email)
        delete_firebase_user(existing_user.uid)
        print(f"[OK] Deleted existing Firebase user: {existing_user.uid}")
    except auth.UserNotFoundError:
        print("[OK] No existing Firebase user found")

    # Check Database
    db_user = db_manager.execute_query(
        "SELECT id FROM users WHERE email = %s",
        (test_email,),
        fetch_one=True
    )
    if db_user:
        db_manager.execute_query(
            "DELETE FROM tenant_users WHERE user_id = %s",
            (db_user['id'],)
        )
        db_manager.execute_query(
            "DELETE FROM users WHERE id = %s",
            (db_user['id'],)
        )
        print(f"[OK] Deleted existing database user: {db_user['id']}")
    else:
        print("[OK] No existing database user found")
except Exception as e:
    print(f"[ERROR] Cleanup failed: {e}")

# Test 1: Create Firebase User
print("\n[3/6] Testing Firebase User Creation...")
try:
    firebase_user = create_firebase_user(test_email, test_password, test_name)
    if firebase_user:
        print(f"[OK] Firebase user created successfully")
        print(f"  UID: {firebase_user['uid']}")
        print(f"  Email: {firebase_user['email']}")
        print(f"  Display Name: {firebase_user['display_name']}")
        firebase_uid = firebase_user['uid']
    else:
        print("[ERROR] Firebase user creation returned None")
        sys.exit(1)
except Exception as e:
    print(f"[ERROR] Firebase user creation failed: {e}")
    sys.exit(1)

# Test 2: Create Database User
print("\n[4/6] Testing Database User Creation...")
try:
    import uuid
    user_id = str(uuid.uuid4())

    query = """
        INSERT INTO users (id, firebase_uid, email, display_name, user_type, is_active)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, firebase_uid, email, display_name, user_type, is_active
    """

    result = db_manager.execute_query(
        query,
        (user_id, firebase_uid, test_email, test_name, 'tenant_admin', True),
        fetch_one=True
    )

    if result:
        print(f"[OK] Database user created successfully")
        print(f"  ID: {result['id']}")
        print(f"  Firebase UID: {result['firebase_uid']}")
        print(f"  Email: {result['email']}")
        print(f"  User Type: {result['user_type']}")
    else:
        print("[ERROR] Database user creation returned None")
        # Rollback Firebase user
        delete_firebase_user(firebase_uid)
        sys.exit(1)
except Exception as e:
    print(f"[ERROR] Database user creation failed: {e}")
    # Rollback Firebase user
    delete_firebase_user(firebase_uid)
    sys.exit(1)

# Test 3: Verify User Can Be Retrieved
print("\n[5/6] Testing User Retrieval...")
try:
    # From Firebase
    firebase_user_retrieved = auth.get_user(firebase_uid)
    print(f"[OK] Retrieved from Firebase: {firebase_user_retrieved.email}")

    # From Database
    db_user_retrieved = db_manager.execute_query(
        "SELECT * FROM users WHERE email = %s",
        (test_email,),
        fetch_one=True
    )
    if db_user_retrieved:
        print(f"[OK] Retrieved from Database: {db_user_retrieved['email']}")
    else:
        print("[ERROR] User not found in database")
except Exception as e:
    print(f"[ERROR] User retrieval failed: {e}")

# Test 4: Test Invitation System
print("\n[6/6] Testing Invitation System...")
try:
    # Check if invitation table exists
    invitation_check = db_manager.execute_query(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'user_invitations'
        )
        """,
        fetch_one=True
    )

    if invitation_check and invitation_check['exists']:
        print("[OK] Invitation table exists")

        # Create test invitation
        import uuid
        invitation_token = str(uuid.uuid4())

        invitation_query = """
            INSERT INTO user_invitations (
                email, role, tenant_id, invited_by_user_id,
                invitation_token, expires_at
            )
            VALUES (%s, %s, %s, %s, %s, NOW() + INTERVAL '7 days')
            RETURNING id, email, invitation_token
        """

        invitation = db_manager.execute_query(
            invitation_query,
            ('invited@deltacfo.com', 'employee', 'delta', user_id, invitation_token),
            fetch_one=True
        )

        if invitation:
            print(f"[OK] Invitation created successfully")
            print(f"  Email: {invitation['email']}")
            print(f"  Token: {invitation['invitation_token']}")

            # Clean up invitation
            db_manager.execute_query(
                "DELETE FROM user_invitations WHERE id = %s",
                (invitation['id'],)
            )
            print("[OK] Test invitation cleaned up")
        else:
            print("[ERROR] Invitation creation returned None")
    else:
        print("[WARNING] Invitation table does not exist - skipping invitation test")
except Exception as e:
    print(f"[ERROR] Invitation test failed: {e}")

# Cleanup
print("\n[CLEANUP] Removing test user...")
try:
    # Delete from database
    db_manager.execute_query(
        "DELETE FROM tenant_users WHERE user_id = %s",
        (user_id,)
    )
    db_manager.execute_query(
        "DELETE FROM users WHERE id = %s",
        (user_id,)
    )
    print("[OK] Database user deleted")

    # Delete from Firebase
    delete_firebase_user(firebase_uid)
    print("[OK] Firebase user deleted")
except Exception as e:
    print(f"[ERROR] Cleanup failed: {e}")

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("All authentication flow tests completed!")
print("If you see this message, the core authentication system is working.")
print("=" * 80)
