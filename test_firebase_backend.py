#!/usr/bin/env python3
"""
Test Firebase backend configuration
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from auth.firebase_config import initialize_firebase, verify_firebase_token, create_firebase_user

# Load environment variables
load_dotenv()

def test_firebase_initialization():
    """Test Firebase initialization"""
    try:
        print("=== Testing Firebase Backend Configuration ===")
        print()

        # Test initialization
        print("1. Testing Firebase initialization...")
        app = initialize_firebase()
        print("   SUCCESS: Firebase Admin SDK initialized")
        print(f"   App name: {app.name}")
        print(f"   Project ID: {app.project_id}")
        print()

        # Test user lookup
        print("2. Testing user lookup...")
        from firebase_admin import auth
        try:
            user = auth.get_user_by_email('admin@deltacfo.com')
            print(f"   SUCCESS: Found user 'admin@deltacfo.com'")
            print(f"   UID: {user.uid}")
            print(f"   Email verified: {user.email_verified}")
            print()
        except auth.UserNotFoundError:
            print("   WARNING: User 'admin@deltacfo.com' not found")
            print("   You may need to create this user")
            print()

        print("=== Firebase Backend Configuration is WORKING ===")
        return True

    except Exception as e:
        print(f"   ERROR: {e}")
        print()
        print("=== Firebase Backend Configuration FAILED ===")
        return False

if __name__ == "__main__":
    test_firebase_initialization()
