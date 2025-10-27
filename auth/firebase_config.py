"""
Firebase Admin SDK Configuration

This module initializes and configures the Firebase Admin SDK for server-side
authentication and user management.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
import firebase_admin
from firebase_admin import auth, credentials

logger = logging.getLogger(__name__)

# Global Firebase app instance
_firebase_app: Optional[firebase_admin.App] = None


def initialize_firebase() -> firebase_admin.App:
    """
    Initialize Firebase Admin SDK.

    Loads credentials from environment variables or Google Cloud Secret Manager.
    Returns the Firebase app instance.

    Environment Variables:
        FIREBASE_SERVICE_ACCOUNT_KEY: JSON string of service account key
        FIREBASE_SERVICE_ACCOUNT_PATH: Path to service account JSON file
        GOOGLE_APPLICATION_CREDENTIALS: Path to GCP service account (fallback)

    Returns:
        firebase_admin.App: Initialized Firebase app instance

    Raises:
        ValueError: If no valid Firebase credentials are found
    """
    global _firebase_app

    # Return existing app if already initialized
    if _firebase_app is not None:
        logger.info("Firebase Admin SDK already initialized")
        return _firebase_app

    try:
        # Option 1: Load from JSON string in environment variable
        service_account_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
        if service_account_json:
            try:
                service_account_dict = json.loads(service_account_json)
                cred = credentials.Certificate(service_account_dict)
                _firebase_app = firebase_admin.initialize_app(cred)
                logger.info("Firebase initialized from FIREBASE_SERVICE_ACCOUNT_KEY")
                return _firebase_app
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse FIREBASE_SERVICE_ACCOUNT_KEY: {e}")

        # Option 2: Load from file path in environment variable
        service_account_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
        if service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info(f"Firebase initialized from {service_account_path}")
            return _firebase_app

        # Option 3: Use Google Application Default Credentials (for Cloud Run)
        google_app_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if google_app_creds and os.path.exists(google_app_creds):
            cred = credentials.Certificate(google_app_creds)
            _firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized from GOOGLE_APPLICATION_CREDENTIALS")
            return _firebase_app

        # Option 4: Try default initialization (works in some GCP environments)
        try:
            _firebase_app = firebase_admin.initialize_app()
            logger.info("Firebase initialized with default credentials")
            return _firebase_app
        except Exception as e:
            logger.error(f"Failed to initialize Firebase with default credentials: {e}")

        # No valid credentials found
        raise ValueError(
            "No valid Firebase credentials found. Please set one of: "
            "FIREBASE_SERVICE_ACCOUNT_KEY, FIREBASE_SERVICE_ACCOUNT_PATH, or "
            "GOOGLE_APPLICATION_CREDENTIALS environment variables."
        )

    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        raise


def get_firebase_app() -> firebase_admin.App:
    """
    Get the Firebase app instance.
    Initializes Firebase if not already initialized.

    Returns:
        firebase_admin.App: Firebase app instance
    """
    global _firebase_app
    if _firebase_app is None:
        return initialize_firebase()
    return _firebase_app


def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Firebase ID token and return the decoded token.

    Args:
        id_token: Firebase ID token from client

    Returns:
        Dict containing user information (uid, email, etc.) if valid
        None if token is invalid
    """
    try:
        # Ensure Firebase is initialized
        get_firebase_app()

        # Verify the token
        decoded_token = auth.verify_id_token(id_token)
        logger.info(f"Token verified successfully for user: {decoded_token.get('uid')}")
        return decoded_token

    except auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid Firebase token: {e}")
        return None
    except auth.ExpiredIdTokenError as e:
        logger.warning(f"Expired Firebase token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {e}")
        return None


def create_firebase_user(email: str, password: str, display_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Create a new Firebase user.

    Args:
        email: User's email address
        password: User's password
        display_name: Optional display name

    Returns:
        Dict containing user information (uid, email, etc.) if successful
        None if creation failed
    """
    try:
        # Ensure Firebase is initialized
        get_firebase_app()

        # Create user
        user_record = auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            email_verified=False
        )

        logger.info(f"Successfully created Firebase user: {user_record.uid}")
        return {
            'uid': user_record.uid,
            'email': user_record.email,
            'display_name': user_record.display_name,
            'email_verified': user_record.email_verified
        }

    except auth.EmailAlreadyExistsError:
        logger.warning(f"Email already exists: {email}")
        return None
    except Exception as e:
        logger.error(f"Error creating Firebase user: {e}")
        return None


def get_firebase_user(uid: str) -> Optional[Dict[str, Any]]:
    """
    Get Firebase user information by UID.

    Args:
        uid: Firebase user UID

    Returns:
        Dict containing user information if found
        None if user not found
    """
    try:
        # Ensure Firebase is initialized
        get_firebase_app()

        user_record = auth.get_user(uid)
        return {
            'uid': user_record.uid,
            'email': user_record.email,
            'display_name': user_record.display_name,
            'email_verified': user_record.email_verified,
            'disabled': user_record.disabled
        }

    except auth.UserNotFoundError:
        logger.warning(f"Firebase user not found: {uid}")
        return None
    except Exception as e:
        logger.error(f"Error fetching Firebase user: {e}")
        return None


def update_firebase_user(uid: str, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Update Firebase user information.

    Args:
        uid: Firebase user UID
        **kwargs: Fields to update (email, display_name, password, etc.)

    Returns:
        Dict containing updated user information if successful
        None if update failed
    """
    try:
        # Ensure Firebase is initialized
        get_firebase_app()

        user_record = auth.update_user(uid, **kwargs)
        logger.info(f"Successfully updated Firebase user: {uid}")
        return {
            'uid': user_record.uid,
            'email': user_record.email,
            'display_name': user_record.display_name,
            'email_verified': user_record.email_verified
        }

    except auth.UserNotFoundError:
        logger.warning(f"Firebase user not found: {uid}")
        return None
    except Exception as e:
        logger.error(f"Error updating Firebase user: {e}")
        return None


def delete_firebase_user(uid: str) -> bool:
    """
    Delete a Firebase user.

    Args:
        uid: Firebase user UID

    Returns:
        True if deletion successful, False otherwise
    """
    try:
        # Ensure Firebase is initialized
        get_firebase_app()

        auth.delete_user(uid)
        logger.info(f"Successfully deleted Firebase user: {uid}")
        return True

    except auth.UserNotFoundError:
        logger.warning(f"Firebase user not found: {uid}")
        return False
    except Exception as e:
        logger.error(f"Error deleting Firebase user: {e}")
        return False


def send_password_reset_email(email: str) -> bool:
    """
    Send password reset email to user.

    Note: This is typically handled on the client side using Firebase Client SDK.
    This function is here for completeness but may have limited server-side usage.

    Args:
        email: User's email address

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Note: Firebase Admin SDK doesn't directly support sending password reset emails
        # This should be handled by the Firebase Client SDK on the frontend
        # We can generate a password reset link here if needed

        get_firebase_app()
        link = auth.generate_password_reset_link(email)
        logger.info(f"Generated password reset link for: {email}")
        # Link should be sent via email service
        return True

    except Exception as e:
        logger.error(f"Error generating password reset link: {e}")
        return False


def generate_email_verification_link(email: str) -> Optional[str]:
    """
    Generate email verification link for a user.

    Args:
        email: User's email address

    Returns:
        Verification link if successful, None otherwise
    """
    try:
        get_firebase_app()
        link = auth.generate_email_verification_link(email)
        logger.info(f"Generated email verification link for: {email}")
        return link

    except Exception as e:
        logger.error(f"Error generating email verification link: {e}")
        return None


def verify_session_cookie(session_cookie: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Firebase session cookie.

    Args:
        session_cookie: Session cookie to verify

    Returns:
        Dict containing user information if valid, None otherwise
    """
    try:
        get_firebase_app()
        decoded_claims = auth.verify_session_cookie(session_cookie, check_revoked=True)
        logger.info(f"Session cookie verified for user: {decoded_claims.get('uid')}")
        return decoded_claims

    except auth.InvalidSessionCookieError as e:
        logger.warning(f"Invalid session cookie: {e}")
        return None
    except auth.RevokedSessionCookieError as e:
        logger.warning(f"Revoked session cookie: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying session cookie: {e}")
        return None


def create_session_cookie(id_token: str, expires_in_days: int = 14) -> Optional[str]:
    """
    Create a session cookie from an ID token.

    Args:
        id_token: Firebase ID token
        expires_in_days: Number of days until cookie expires (default 14)

    Returns:
        Session cookie if successful, None otherwise
    """
    try:
        get_firebase_app()

        # Session cookie expires in specified days
        expires_in = expires_in_days * 24 * 60 * 60 * 1000  # Convert to milliseconds

        session_cookie = auth.create_session_cookie(id_token, expires_in=expires_in)
        logger.info("Session cookie created successfully")
        return session_cookie

    except Exception as e:
        logger.error(f"Error creating session cookie: {e}")
        return None
