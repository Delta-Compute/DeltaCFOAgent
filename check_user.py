#!/usr/bin/env python3
"""
Script to check if user exists in PostgreSQL database
"""
from web_ui.database import db_manager

# Check for user in database
query = "SELECT id, firebase_uid, email, user_type, is_active FROM users WHERE email = %s"
result = db_manager.execute_query(query, ('ariel@delta-mining.com',), fetch_one=True)

if result:
    print(f"User found in database:")
    print(f"  ID: {result['id']}")
    print(f"  Firebase UID: {result['firebase_uid']}")
    print(f"  Email: {result['email']}")
    print(f"  User Type: {result['user_type']}")
    print(f"  Active: {result['is_active']}")
else:
    print("No user found in database with email: ariel@delta-mining.com")
