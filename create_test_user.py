#!/usr/bin/env python3
"""
Create a test user in Firebase Authentication
"""
import os
import sys
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth
from pathlib import Path

# Load environment variables
load_dotenv()

def create_test_user():
    """Create a test user in Firebase"""
    try:
        # Get Firebase service account path
        service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', 'config/firebase-service-account.json')

        if not os.path.exists(service_account_path):
            print(f"ERROR: Firebase service account file not found at: {service_account_path}")
            return False

        # Initialize Firebase Admin SDK
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)

        print("Firebase Admin SDK initialized successfully")
        print()

        # Get user details
        print("=== Create Firebase Test User ===")
        email = input("Enter email (e.g., admin@deltacfo.com): ").strip()
        if not email:
            email = "admin@deltacfo.com"

        password = input("Enter password (min 6 characters): ").strip()
        if not password:
            password = "DeltaCFO2024!"

        display_name = input("Enter display name (e.g., Admin User): ").strip()
        if not display_name:
            display_name = "Admin User"

        print()
        print(f"Creating user with:")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print(f"  Display Name: {display_name}")
        print()

        # Create user
        user = auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=True  # Auto-verify for test user
        )

        print(f"SUCCESS! User created:")
        print(f"  UID: {user.uid}")
        print(f"  Email: {user.email}")
        print(f"  Display Name: {user.display_name}")
        print(f"  Email Verified: {user.email_verified}")
        print()
        print("You can now login with these credentials!")

        return True

    except auth.EmailAlreadyExistsError:
        print("ERROR: A user with this email already exists.")
        print("Try a different email or use the existing credentials to login.")
        return False

    except Exception as e:
        print(f"ERROR: Failed to create user: {e}")
        return False

if __name__ == "__main__":
    create_test_user()
