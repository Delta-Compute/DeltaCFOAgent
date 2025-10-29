#!/usr/bin/env python3
"""
Script to remove a Firebase user by UID
"""
import sys
from auth.firebase_config import initialize_firebase, delete_firebase_user

# Initialize Firebase
initialize_firebase()

# Remove user
firebase_uid = 'wlCbaOUK0yeVzy9ahzgHUb2tap43'
print(f'Removing Firebase user: {firebase_uid}')

result = delete_firebase_user(firebase_uid)
if result:
    print('✓ User removed from Firebase successfully')
else:
    print('✗ Failed to remove user from Firebase')
    sys.exit(1)
