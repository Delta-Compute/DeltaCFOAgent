"""
Authentication Module

Provides Firebase authentication and user management functionality.
"""

from .firebase_config import (
    initialize_firebase,
    get_firebase_app,
    verify_firebase_token,
    create_firebase_user,
    get_firebase_user,
    update_firebase_user,
    delete_firebase_user,
    send_password_reset_email,
    generate_email_verification_link,
    verify_session_cookie,
    create_session_cookie
)

__all__ = [
    'initialize_firebase',
    'get_firebase_app',
    'verify_firebase_token',
    'create_firebase_user',
    'get_firebase_user',
    'update_firebase_user',
    'delete_firebase_user',
    'send_password_reset_email',
    'generate_email_verification_link',
    'verify_session_cookie',
    'create_session_cookie'
]
