#!/usr/bin/env python3
"""
Delta CFO Agent - Database-Backed Web Dashboard
Advanced web interface for financial transaction management with Claude AI integration
"""

import os
import sys
import json
import sqlite3  # Kept for backward compatibility - main DB uses database.py manager
import pandas as pd
import time
import threading
import traceback
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file, session
from concurrent.futures import ThreadPoolExecutor, as_completed
import random
import anthropic
from typing import List, Dict, Any, Optional
from werkzeug.utils import secure_filename
import subprocess
import shutil
import hashlib
import uuid
import base64
import zipfile
import re
import logging
from dotenv import load_dotenv
from pathlib import Path

# Configure sys.path FIRST before any local imports
# This ensures all modules can find their dependencies
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
web_ui_dir = os.path.dirname(os.path.abspath(__file__))
invoice_dir = str(Path(__file__).parent.parent / 'invoice_processing')
# api_dir removed - no longer needed since we're not importing from /api
# api_dir = str(Path(__file__).parent.parent / 'api')

# Insert parent_dir FIRST to ensure root/services has priority over web_ui/services
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
# web_ui_dir added but after parent for correct module resolution
if web_ui_dir not in sys.path:
    sys.path.append(web_ui_dir)
if invoice_dir not in sys.path:
    sys.path.append(invoice_dir)
# api_dir path no longer added to avoid import issues
# if api_dir not in sys.path:
#     sys.path.append(api_dir)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Archive handling imports - optional
try:
    import py7zr
    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False
    print("WARNING: py7zr not available - 7z archive support disabled")

# Database imports - support both SQLite and PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRESQL_AVAILABLE = True
except ImportError:
    POSTGRESQL_AVAILABLE = False
    print("WARNING: psycopg2 not available - PostgreSQL support disabled")

# Import historical currency converter
from historical_currency_converter import HistoricalCurrencyConverter

# Import tenant context manager
from tenant_context import init_tenant_context, get_current_tenant_id, set_tenant_id

# Import reporting API
from reporting_api import register_reporting_routes

# Import Firebase authentication
try:
    import sys
    auth_module_path = os.path.join(parent_dir, 'auth')
    if auth_module_path not in sys.path:
        sys.path.insert(0, auth_module_path)
    from firebase_config import verify_firebase_token, get_firebase_user
    FIREBASE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Firebase authentication not available: {e}")
    FIREBASE_AVAILABLE = False

# Authentication blueprints - using lazy loading to avoid circular imports
# These blueprints are registered AFTER app initialization to prevent timeout issues

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size for batch uploads

# Auto-reload templates only in debug mode
debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
if debug_mode:
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True

# Configure Flask secret key for sessions
# Use a fixed key in development for session persistence across restarts
# In production, set FLASK_SECRET_KEY environment variable
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-delta-cfo-agent-2024')

# Initialize multi-tenant context
init_tenant_context(app)

# Register CFO reporting routes
register_reporting_routes(app)

# Lazy blueprint registration function to avoid circular imports
def register_auth_blueprints():
    """
    Register authentication blueprints using lazy loading.
    This function is called after app initialization to avoid circular imports.
    """
    try:
        # Import blueprints only when needed
        from api.auth_routes import auth_bp
        from api.user_routes import user_bp
        from api.tenant_routes import tenant_bp
        from api.onboarding_routes import onboarding_bp

        # Register blueprints
        app.register_blueprint(auth_bp)
        app.register_blueprint(user_bp)
        app.register_blueprint(tenant_bp)
        app.register_blueprint(onboarding_bp)

        logger.info("Authentication, tenant, and onboarding blueprints registered successfully")
        return True
    except ImportError as e:
        logger.warning(f"Could not import authentication blueprints: {e}")
        return False
    except Exception as e:
        logger.error(f"Error registering authentication blueprints: {e}")
        return False

# Register blueprints after app is fully initialized
# This happens after all database and other services are ready
auth_blueprints_registered = False

# ====================================================================
# Authentication Page Routes
# ====================================================================
# NOTE: These routes are kept for serving static authentication pages
# The actual API endpoints are in the commented blueprints above

@app.route('/auth/login')
def login_page():
    """Serve the login page"""
    return render_template('auth/login.html')

@app.route('/auth/register')
def register_page():
    """Serve the registration page"""
    return render_template('auth/register.html')

@app.route('/auth/forgot-password')
def forgot_password_page():
    """Serve the forgot password page"""
    return render_template('auth/forgot_password.html')

@app.route('/auth/accept-invitation')
def accept_invitation_page():
    """Serve the accept invitation page"""
    return render_template('auth/accept_invitation.html')


@app.route('/auth/profile')
def profile_page():
    """Serve the user profile page"""
    return render_template('auth/profile.html')


@app.route('/cfo/dashboard')
def cfo_dashboard_page():
    """Serve the CFO dashboard page"""
    # TODO: Add authentication check
    return render_template('cfo_dashboard.html')

@app.route('/users')
def users_page():
    """Serve the user management page"""
    # TODO: Add authentication and permission check
    return render_template('users.html')

# TEMPORARY: Admin endpoint to delete Firebase user
@app.route('/admin/get-firebase-user-by-email/<email>', methods=['GET'])
def admin_get_firebase_user_by_email(email):
    """TEMPORARY: Find Firebase user by email"""
    try:
        from auth.firebase_config import initialize_firebase
        from firebase_admin import auth

        initialize_firebase()
        user = auth.get_user_by_email(email)

        return jsonify({
            'success': True,
            'user': {
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name,
                'email_verified': user.email_verified,
                'disabled': user.disabled
            }
        }), 200
    except auth.UserNotFoundError:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/delete-firebase-user/<firebase_uid>', methods=['DELETE'])
def admin_delete_firebase_user(firebase_uid):
    """TEMPORARY: Delete Firebase user by UID"""
    try:
        from auth.firebase_config import initialize_firebase, delete_firebase_user
        initialize_firebase()
        result = delete_firebase_user(firebase_uid)
        if result:
            return jsonify({'success': True, 'message': f'User {firebase_uid} deleted'}), 200
        else:
            return jsonify({'success': False, 'message': 'Failed to delete user'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ====================================================================
# Firebase Authentication API Routes - DEPRECATED
# ====================================================================
# These mock endpoints have been replaced by the authentication blueprints
# from api/auth_routes.py and api/user_routes.py
# The blueprints are now registered via lazy loading (register_auth_blueprints)
#
# These endpoints are kept here for reference but are NOT registered (no @app.route)
# The blueprints now provide the real implementation with full database integration

def _deprecated_api_login():
    """DEPRECATED - Use api/auth_routes.py instead
    Authenticate user with Firebase ID token
    Returns user information and session data
    """
    try:
        if not FIREBASE_AVAILABLE:
            return jsonify({
                'success': False,
                'message': 'Firebase authentication not configured'
            }), 500

        data = request.get_json()
        id_token = data.get('id_token')

        if not id_token:
            return jsonify({
                'success': False,
                'message': 'ID token is required'
            }), 400

        # Verify Firebase token
        decoded_token = verify_firebase_token(id_token)
        if not decoded_token:
            return jsonify({
                'success': False,
                'message': 'Invalid or expired token'
            }), 401

        # Get user information
        uid = decoded_token.get('uid')
        email = decoded_token.get('email')

        # Create session
        session['user_id'] = uid
        session['email'] = email

        # Return user data (simplified version without database lookup)
        user_data = {
            'uid': uid,
            'email': email,
            'display_name': decoded_token.get('name', email.split('@')[0]),
            'user_type': 'user',  # Default type
            'email_verified': decoded_token.get('email_verified', False)
        }

        return jsonify({
            'success': True,
            'user': user_data,
            'message': 'Login successful'
        }), 200

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# @app.route('/api/auth/logout', methods=['POST'])  # DEPRECATED - using blueprint
def _deprecated_api_logout():
    """Logout user and clear session"""
    try:
        session.clear()
        return jsonify({
            'success': True,
            'message': 'Logout successful'
        }), 200
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# @app.route('/api/auth/register', methods=['POST'])  # DEPRECATED - using blueprint
def _deprecated_api_register():
    """
    Register a new user (Firebase user should already be created)
    This endpoint is called after Firebase signup to store user in database
    """
    try:
        if not FIREBASE_AVAILABLE:
            return jsonify({
                'success': False,
                'message': 'Firebase authentication not configured'
            }), 500

        data = request.get_json()
        email = data.get('email')
        display_name = data.get('display_name')
        user_type = data.get('user_type', 'tenant_admin')

        if not email or not display_name:
            return jsonify({
                'success': False,
                'message': 'Email and display name are required'
            }), 400

        # For now, return success with user data
        # In a full implementation, you would store this in the database
        user_data = {
            'email': email,
            'display_name': display_name,
            'user_type': user_type,
            'email_verified': False
        }

        return jsonify({
            'success': True,
            'user': user_data,
            'message': 'Registration successful'
        }), 201

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# @app.route('/api/auth/verify-invitation/<token>', methods=['GET'])  # DEPRECATED - using blueprint
def _deprecated_api_verify_invitation(token):
    """
    Verify invitation token and return invitation details
    """
    try:
        # For now, return mock data
        # In full implementation, query database for invitation
        return jsonify({
            'success': True,
            'invitation': {
                'token': token,
                'email': 'user@example.com',
                'company_name': 'Delta Capital Holdings',
                'invited_by_name': 'Admin User',
                'role': 'cfo_assistant',
                'status': 'pending',
                'is_expired': False,
                'expires_at': '2025-12-31T23:59:59Z'
            }
        }), 200

    except Exception as e:
        logger.error(f"Verify invitation error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# @app.route('/api/auth/accept-invitation/<token>', methods=['POST'])  # DEPRECATED - using blueprint
def _deprecated_api_accept_invitation(token):
    """
    Accept invitation and create user account
    """
    try:
        data = request.get_json()
        display_name = data.get('display_name')
        password = data.get('password')

        if not display_name or not password:
            return jsonify({
                'success': False,
                'message': 'Display name and password are required'
            }), 400

        # For now, return success
        # In full implementation:
        # 1. Verify token exists and is valid
        # 2. Create Firebase user
        # 3. Create database user record
        # 4. Link user to tenant with role
        # 5. Mark invitation as accepted

        return jsonify({
            'success': True,
            'message': 'Invitation accepted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Accept invitation error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# @app.route('/api/auth/me', methods=['GET'])  # DEPRECATED - using blueprint
def _deprecated_api_get_current_user():
    """Get current authenticated user"""
    try:
        if 'user_id' not in session:
            return jsonify({
                'success': False,
                'message': 'Not authenticated'
            }), 401

        return jsonify({
            'success': True,
            'user': {
                'uid': session.get('user_id'),
                'email': session.get('email')
            }
        }), 200

    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ====================================================================
# USER MANAGEMENT ENDPOINTS
# ====================================================================

# @app.route('/api/users/invite', methods=['POST'])  # DEPRECATED - using blueprint
def _deprecated_api_invite_user():
    """
    Invite a user (CFO, Assistant, or Employee) to the tenant
    """
    try:
        data = request.get_json()
        email = data.get('email')
        display_name = data.get('display_name')
        user_type = data.get('user_type')
        role = data.get('role')
        permissions = data.get('permissions', {})

        if not email or not display_name or not user_type:
            return jsonify({
                'success': False,
                'message': 'Email, display name, and user type are required'
            }), 400

        # For now, return success with invitation details
        # In full implementation:
        # 1. Check if user is already in system
        # 2. Generate unique invitation token
        # 3. Store invitation in user_invitations table
        # 4. Send invitation email via email service
        # 5. Set expiration date (default 7 days)

        invitation_data = {
            'email': email,
            'display_name': display_name,
            'user_type': user_type,
            'role': role,
            'permissions': permissions,
            'status': 'pending',
            'expires_in_days': 7
        }

        logger.info(f"Invitation created for {email} as {user_type}")

        return jsonify({
            'success': True,
            'invitation': invitation_data,
            'message': f'Invitation sent successfully to {email}'
        }), 201

    except Exception as e:
        logger.error(f"Invite user error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Database connection - DEPRECATED: Now using database manager (database.py)
# DB_PATH = os.path.join(os.path.dirname(__file__), 'delta_transactions.db')

# Claude API client
claude_client = None

# Historical Currency Converter
currency_converter = None

# Global Revenue Matcher tracking for progress and preventing double-clicks
active_matcher = None
matcher_lock = threading.Lock()

def init_claude_client():
    """Initialize Claude API client"""
    global claude_client
    try:
        # Try to load API key from various sources
        api_key = None

        # Check environment variable
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            api_key = api_key.strip()  # Remove whitespace and newlines

        # Check for .anthropic_api_key file in parent directory
        if not api_key:
            key_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.anthropic_api_key')
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    api_key = f.read().strip()

        if api_key:
            # Additional validation and cleaning
            api_key = api_key.strip()  # Extra safety
            if not api_key.startswith('sk-ant-'):
                print(f"WARNING: API key format looks invalid. Expected 'sk-ant-', got: '{api_key[:10]}...'")
                return False

            claude_client = anthropic.Anthropic(api_key=api_key)
            print(f"[OK] Claude API client initialized successfully (key: {api_key[:10]}...{api_key[-4:]})")
            return True
        else:
            print("WARNING: Claude API key not found - AI features disabled")
            return False
    except Exception as e:
        print(f"ERROR: Error initializing Claude API: {e}")
        return False

def init_currency_converter():
    """Initialize Historical Currency Converter"""
    global currency_converter
    try:
        from database import db_manager

        # Check if database connection is available before proceeding
        if not db_manager.connection_pool and db_manager.db_type == 'postgresql':
            print("WARNING: PostgreSQL connection pool not available - skipping currency converter initialization")
            return False

        currency_converter = HistoricalCurrencyConverter(db_manager)
        print("[OK] Historical Currency Converter initialized successfully")
        return True
    except Exception as e:
        print(f"[ERROR] Error initializing Currency Converter: {e}")
        return False

def init_invoice_tables():
    """Initialize invoice tables in the database"""
    try:
        from database import db_manager

        # Check if database connection is available before proceeding
        if not db_manager.connection_pool and db_manager.db_type == 'postgresql':
            print("WARNING: PostgreSQL connection pool not available - skipping invoice tables initialization")
            return False

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')

            # Main invoices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id TEXT PRIMARY KEY,
                    invoice_number TEXT UNIQUE NOT NULL,
                    date TEXT NOT NULL,
                    due_date TEXT,
                    vendor_name TEXT NOT NULL,
                    vendor_address TEXT,
                    vendor_tax_id TEXT,
                    customer_name TEXT,
                    customer_address TEXT,
                    customer_tax_id TEXT,
                    total_amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    tax_amount REAL,
                    subtotal REAL,
                    line_items TEXT,
                    payment_terms TEXT,
                    status TEXT DEFAULT 'pending',
                    invoice_type TEXT DEFAULT 'other',
                    confidence_score REAL DEFAULT 0.0,
                    processing_notes TEXT,
                    source_file TEXT,
                    email_id TEXT,
                    processed_at TEXT,
                    created_at TEXT NOT NULL,
                    business_unit TEXT,
                    category TEXT,
                    currency_type TEXT,
                    vendor_type TEXT,
                    extraction_method TEXT,
                    linked_transaction_id TEXT,
                    FOREIGN KEY (linked_transaction_id) REFERENCES transactions(transaction_id)
                )
            ''')

            # Add crypto fields if they don't exist
            try:
                cursor.execute('''
                    ALTER TABLE invoices ADD COLUMN crypto_currency TEXT
                ''')
                print("Added crypto_currency column to invoices table")
            except Exception as e:
                # Column already exists
                pass

            try:
                cursor.execute('''
                    ALTER TABLE invoices ADD COLUMN crypto_network TEXT
                ''')
                print("Added crypto_network column to invoices table")
            except Exception as e:
                # Column already exists
                pass

            try:
                cursor.execute('''
                    ALTER TABLE invoices ADD COLUMN payment_terms TEXT
                ''')
                print("Added payment_terms column to invoices table")
            except Exception as e:
                # Column already exists
                pass

            # Email processing log
            if is_postgresql:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS invoice_email_log (
                        id SERIAL PRIMARY KEY,
                        email_id TEXT UNIQUE NOT NULL,
                        subject TEXT,
                        sender TEXT,
                        received_at TEXT,
                        processed_at TEXT,
                        status TEXT DEFAULT 'pending',
                        attachments_count INTEGER DEFAULT 0,
                        invoices_extracted INTEGER DEFAULT 0,
                        error_message TEXT
                    )
                ''')
            else:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS invoice_email_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email_id TEXT UNIQUE NOT NULL,
                        subject TEXT,
                        sender TEXT,
                        received_at TEXT,
                        processed_at TEXT,
                        status TEXT DEFAULT 'pending',
                        attachments_count INTEGER DEFAULT 0,
                        invoices_extracted INTEGER DEFAULT 0,
                        error_message TEXT
                    )
                ''')

            # Background jobs table for async processing
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS background_jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    total_items INTEGER NOT NULL DEFAULT 0,
                    processed_items INTEGER NOT NULL DEFAULT 0,
                    successful_items INTEGER NOT NULL DEFAULT 0,
                    failed_items INTEGER NOT NULL DEFAULT 0,
                    progress_percentage REAL NOT NULL DEFAULT 0.0,
                    started_at TEXT,
                    completed_at TEXT,
                    created_at TEXT NOT NULL,
                    created_by TEXT DEFAULT 'system',
                    source_file TEXT,
                    error_message TEXT,
                    metadata TEXT
                )
            ''')

            # Job items table for tracking individual files in a job
            if is_postgresql:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS job_items (
                        id SERIAL PRIMARY KEY,
                        job_id TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        item_path TEXT,
                        status TEXT NOT NULL DEFAULT 'pending',
                        processed_at TEXT,
                        error_message TEXT,
                        result_data TEXT,
                        processing_time_seconds REAL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (job_id) REFERENCES background_jobs(id)
                    )
                ''')
            else:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS job_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        item_path TEXT,
                        status TEXT NOT NULL DEFAULT 'pending',
                        processed_at TEXT,
                        error_message TEXT,
                        result_data TEXT,
                        processing_time_seconds REAL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (job_id) REFERENCES background_jobs(id)
                    )
                ''')

            # Add customer columns to existing tables (migration)
            try:
                cursor.execute('ALTER TABLE invoices ADD COLUMN customer_name TEXT')
                print("Added customer_name column to invoices table")
            except:
                pass  # Column already exists

            try:
                cursor.execute('ALTER TABLE invoices ADD COLUMN customer_address TEXT')
                print("Added customer_address column to invoices table")
            except:
                pass  # Column already exists

            try:
                cursor.execute('ALTER TABLE invoices ADD COLUMN customer_tax_id TEXT')
                print("Added customer_tax_id column to invoices table")
            except:
                pass  # Column already exists

            conn.commit()
            print("Invoice tables initialized successfully")
            return True
    except Exception as e:
        print(f"ERROR: Failed to initialize invoice tables: {e}")
        return False

def init_database():
    """Initialize database and create tables if they don't exist - now uses database manager"""
    try:
        from database import db_manager
        db_manager.init_database()
        print("[OK] Database initialized successfully")
    except Exception as e:
        print(f"[ERROR] Failed to initialize database: {e}")
        raise

# ============================================================================
# BACKGROUND JOBS MANAGEMENT
# ============================================================================

def ensure_background_jobs_tables():
    """Ensure background jobs tables exist with correct schema"""
    try:
        from database import db_manager

        # Check if database connection is available before proceeding
        if not db_manager.connection_pool and db_manager.db_type == 'postgresql':
            print("WARNING: PostgreSQL connection pool not available - skipping background jobs tables initialization")
            return False

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')

            # MIGRATION: Expand VARCHAR(10) fields to avoid overflow errors
            if is_postgresql:
                try:
                    # Expand currency field in transactions table
                    cursor.execute("ALTER TABLE transactions ALTER COLUMN currency TYPE VARCHAR(50)")
                    print("[OK] Migrated transactions.currency VARCHAR(10) -> VARCHAR(50)")
                except Exception as e:
                    if "does not exist" not in str(e) and "already exists" not in str(e):
                        print(f"Currency migration info: {e}")

                try:
                    # Expand currency field in invoices table
                    cursor.execute("ALTER TABLE invoices ALTER COLUMN currency TYPE VARCHAR(50)")
                    print("[OK] Migrated invoices.currency VARCHAR(10) -> VARCHAR(50)")
                except Exception as e:
                    if "does not exist" not in str(e) and "already exists" not in str(e):
                        print(f"Currency migration info: {e}")

            # Background jobs table for async processing
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS background_jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    total_items INTEGER NOT NULL DEFAULT 0,
                    processed_items INTEGER NOT NULL DEFAULT 0,
                    successful_items INTEGER NOT NULL DEFAULT 0,
                    failed_items INTEGER NOT NULL DEFAULT 0,
                    progress_percentage REAL NOT NULL DEFAULT 0.0,
                    started_at TEXT,
                    completed_at TEXT,
                    created_at TEXT NOT NULL,
                    created_by TEXT DEFAULT 'system',
                    source_file TEXT,
                    error_message TEXT,
                    metadata TEXT
                )
            ''')

            # Job items table for tracking individual files in a job
            if is_postgresql:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS job_items (
                        id SERIAL PRIMARY KEY,
                        job_id TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        item_path TEXT,
                        status TEXT NOT NULL DEFAULT 'pending',
                        processed_at TEXT,
                        error_message TEXT,
                        result_data TEXT,
                        processing_time_seconds REAL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (job_id) REFERENCES background_jobs(id)
                    )
                ''')
            else:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS job_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_id TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        item_path TEXT,
                        status TEXT NOT NULL DEFAULT 'pending',
                        processed_at TEXT,
                        error_message TEXT,
                        result_data TEXT,
                        processing_time_seconds REAL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (job_id) REFERENCES background_jobs(id)
                    )
                ''')

            conn.commit()
            print("[OK] Background jobs tables ensured")
            return True

    except Exception as e:
        print(f"ERROR: Failed to ensure background jobs tables: {e}")
        return False

def create_background_job(job_type: str, total_items: int, created_by: str = 'system',
                         source_file: str = None, metadata: str = None) -> str:
    """Create a new background job and return job ID"""
    # First ensure tables exist
    if not ensure_background_jobs_tables():
        print("ERROR: Cannot create background job - tables not available")
        return None

    job_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    try:
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        try:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            cursor.execute(f"""
                INSERT INTO background_jobs (
                    id, job_type, status, total_items, created_at, created_by,
                    source_file, metadata
                ) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder},
                         {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """, (job_id, job_type, 'pending', total_items, created_at, created_by,
                  source_file, metadata))

            conn.commit()
            print(f"[OK] Created background job {job_id} with {total_items} items")
            return job_id
        finally:
            conn.close()

    except Exception as e:
        print(f"ERROR: Failed to create background job: {e}")
        traceback.print_exc()
        return None

def add_job_item(job_id: str, item_name: str, item_path: str = None) -> int:
    """Add an item to a job and return item ID"""
    created_at = datetime.utcnow().isoformat()

    try:
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        try:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            cursor.execute(f"""
                INSERT INTO job_items (job_id, item_name, item_path, status, created_at)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """, (job_id, item_name, item_path, 'pending', created_at))

            if is_postgresql:
                cursor.execute("SELECT lastval()")
                item_id = cursor.fetchone()['lastval']
            else:
                item_id = cursor.lastrowid

            conn.commit()
            return item_id
        finally:
            conn.close()

    except Exception as e:
        print(f"ERROR: Failed to add job item: {e}")
        return None

def update_job_progress(job_id: str, processed_items: int = None, successful_items: int = None,
                       failed_items: int = None, status: str = None, error_message: str = None):
    """Update job progress and status"""

    try:
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        try:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            # Build dynamic update query
            updates = []
            values = []

            if processed_items is not None:
                updates.append(f"processed_items = {placeholder}")
                values.append(processed_items)
            if successful_items is not None:
                updates.append(f"successful_items = {placeholder}")
                values.append(successful_items)
            if failed_items is not None:
                updates.append(f"failed_items = {placeholder}")
                values.append(failed_items)
            if status is not None:
                updates.append(f"status = {placeholder}")
                values.append(status)
                if status in ['completed', 'failed', 'completed_with_errors']:
                    updates.append(f"completed_at = {placeholder}")
                    values.append(datetime.utcnow().isoformat())
                elif status == 'processing':
                    updates.append(f"started_at = {placeholder}")
                    values.append(datetime.utcnow().isoformat())
            if error_message is not None:
                updates.append(f"error_message = {placeholder}")
                values.append(error_message)

            # Calculate progress percentage if we have processed_items
            if processed_items is not None:
                cursor.execute(f"SELECT total_items FROM background_jobs WHERE id = {placeholder}", (job_id,))
                result = cursor.fetchone()
                if result:
                    total = result['total_items'] if is_postgresql else result[0]
                    if total > 0:
                        progress = (processed_items / total) * 100
                        updates.append(f"progress_percentage = {placeholder}")
                        values.append(progress)

            if updates:
                values.append(job_id)
                update_query = f"UPDATE background_jobs SET {', '.join(updates)} WHERE id = {placeholder}"
                cursor.execute(update_query, values)

            conn.commit()
        finally:
            conn.close()

    except Exception as e:
        print(f"ERROR: Failed to update job progress: {e}")

def update_job_item_status(job_id: str, item_name: str, status: str,
                          error_message: str = None, result_data: str = None, processing_time: float = None):
    """Update individual job item status"""

    try:
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        try:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            processed_at = datetime.utcnow().isoformat() if status in ['completed', 'failed'] else None

            cursor.execute(f"""
                UPDATE job_items
                SET status = {placeholder}, processed_at = {placeholder},
                    error_message = {placeholder}, result_data = {placeholder}, processing_time_seconds = {placeholder}
                WHERE job_id = {placeholder} AND item_name = {placeholder}
            """, (status, processed_at, error_message, result_data, processing_time, job_id, item_name))

            conn.commit()
        finally:
            conn.close()

    except Exception as e:
        print(f"ERROR: Failed to update job item status: {e}")

def get_job_status(job_id: str) -> dict:
    """Get complete job status with items"""
    try:
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        try:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            # Get job info
            cursor.execute(f"SELECT * FROM background_jobs WHERE id = {placeholder}", (job_id,))
            job_row = cursor.fetchone()

            if not job_row:
                return {'error': 'Job not found'}

            job_info = dict(job_row)

            # Get job items
            cursor.execute(f"SELECT * FROM job_items WHERE job_id = {placeholder} ORDER BY created_at", (job_id,))
            items_rows = cursor.fetchall()
            job_info['items'] = [dict(row) for row in items_rows]

            return job_info
        finally:
            conn.close()

    except Exception as e:
        print(f"ERROR: Failed to get job status: {e}")
        return {'error': str(e)}

def process_single_invoice_item(job_id: str, item: dict):
    """Process a single invoice item (for parallel execution)"""

    item_name = item['item_name']
    item_path = item.get('item_path')

    if not item_path or not os.path.exists(item_path):
        # File not found - mark as failed
        update_job_item_status(job_id, item_name, 'failed',
                             error_message='File not found or path invalid')
        return {'status': 'failed', 'item_name': item_name, 'error': 'File not found'}

    print(f"[PROCESS] Processing item: {item_name}")
    start_time = time.time()

    try:
        # Process the invoice using existing function
        invoice_data = process_invoice_with_claude(item_path, item_name)
        processing_time = time.time() - start_time

        if 'error' in invoice_data:
            # Processing failed
            update_job_item_status(job_id, item_name, 'failed',
                                 error_message=invoice_data['error'],
                                 processing_time=processing_time)
            print(f"[ERROR] Failed item: {item_name} - {invoice_data['error']}")
            return {'status': 'failed', 'item_name': item_name, 'error': invoice_data['error']}
        else:
            # Processing successful
            result_summary = {
                'id': invoice_data.get('id'),
                'invoice_number': invoice_data.get('invoice_number'),
                'vendor_name': invoice_data.get('vendor_name'),
                'total_amount': invoice_data.get('total_amount')
            }
            update_job_item_status(job_id, item_name, 'completed',
                                 result_data=str(result_summary),
                                 processing_time=processing_time)
            print(f"[OK] Completed item: {item_name} in {processing_time:.2f}s")

            # Clean up processed file to save storage
            try:
                os.remove(item_path)
                print(f" Cleaned up file: {item_path}")
            except:
                pass  # File cleanup failed, but processing succeeded

            return {'status': 'completed', 'item_name': item_name, 'result': result_summary}

    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Processing error: {str(e)}"
        print(f"[ERROR] Failed item: {item_name} - {error_msg}")

        update_job_item_status(job_id, item_name, 'failed',
                             error_message=error_msg,
                             processing_time=processing_time)
        return {'status': 'failed', 'item_name': item_name, 'error': error_msg}

def process_invoice_batch_job(job_id: str):
    """Background worker to process invoice batch job with parallel processing"""
    print(f" Starting background job {job_id}")

    try:
        # Update job status to processing
        update_job_progress(job_id, status='processing')

        # Get job details
        job_info = get_job_status(job_id)
        if 'error' in job_info:
            update_job_progress(job_id, status='failed', error_message='Job not found')
            return

        items = job_info.get('items', [])
        processed_count = 0
        successful_count = 0
        failed_count = 0

        print(f" Processing {len(items)} items in job {job_id} with parallel workers")

        # Process items in parallel with ThreadPoolExecutor
        max_workers = min(5, len(items))  # Limit to 5 concurrent workers
        print(f" Using {max_workers} parallel workers")

        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=f"InvoiceWorker-{job_id[:8]}") as executor:
            # Submit all tasks
            future_to_item = {
                executor.submit(process_single_invoice_item, job_id, item): item
                for item in items
            }

            # Process completed tasks as they finish
            for future in as_completed(future_to_item):
                result = future.result()

                if result['status'] == 'completed':
                    successful_count += 1
                else:
                    failed_count += 1

                processed_count += 1

                # Update job progress after each completed item
                update_job_progress(job_id,
                                  processed_items=processed_count,
                                  successful_items=successful_count,
                                  failed_items=failed_count)

                progress = (processed_count / len(items)) * 100
                print(f"[STATS] Progress: {processed_count}/{len(items)} ({progress:.1f}%) - [OK]{successful_count} [ERROR]{failed_count}")

        # Mark job as completed
        final_status = 'completed' if failed_count == 0 else 'completed_with_errors'
        update_job_progress(job_id, status=final_status,
                          processed_items=processed_count,
                          successful_items=successful_count,
                          failed_items=failed_count)

        print(f"[COMPLETE] Job {job_id} finished: {successful_count} successful, {failed_count} failed")

    except Exception as e:
        error_msg = f"Job processing error: {str(e)}"
        print(f"[ERROR] Job {job_id} failed: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")

        update_job_progress(job_id, status='failed', error_message=error_msg)

def start_background_job(job_id: str, job_type: str = 'invoice_batch'):
    """Start a background job in a separate thread"""
    if job_type == 'invoice_batch':
        worker_thread = threading.Thread(
            target=process_invoice_batch_job,
            args=(job_id,),
            name=f"JobWorker-{job_id[:8]}",
            daemon=True  # Thread will not prevent program exit
        )
        worker_thread.start()
        print(f" Started background worker thread for job {job_id}")
        return True
    else:
        print(f"[ERROR] Unknown job type: {job_type}")
        return False

def get_db_connection():
    """Get database connection using the centralized database manager"""
    try:
        from database import db_manager
        # Return a connection context - this will be used in a 'with' statement
        return db_manager.get_connection()
    except Exception as e:
        print(f"[ERROR] Failed to get database connection: {e}")
        raise

def load_transactions_from_db(filters=None, page=1, per_page=50):
    """Load transactions from database with filtering and pagination"""
    from database import db_manager
    tenant_id = get_current_tenant_id()

    # Use the exact same pattern as get_dashboard_stats function
    with db_manager.get_connection() as conn:
        if db_manager.db_type == 'postgresql':
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cursor = conn.cursor()

        is_postgresql = db_manager.db_type == 'postgresql'

        # Build WHERE clause from filters
        placeholder = "%s" if is_postgresql else "?"
        where_conditions = [
            "(archived = FALSE OR archived IS NULL)",
            f"tenant_id = {placeholder}"
        ]
        params = [tenant_id]

        if filters:
            if filters.get('entity'):
                where_conditions.append("classified_entity = %s" if is_postgresql else "classified_entity = ?")
                params.append(filters['entity'])

            if filters.get('transaction_type'):
                # Map "Revenue" -> positive amounts, "Expense" -> negative amounts
                if filters['transaction_type'] == 'Revenue':
                    where_conditions.append("amount > 0")
                elif filters['transaction_type'] == 'Expense':
                    where_conditions.append("amount < 0")

            if filters.get('source_file'):
                where_conditions.append("source_file = %s" if is_postgresql else "source_file = ?")
                params.append(filters['source_file'])

            if filters.get('needs_review'):
                if filters['needs_review'] == 'true':
                    where_conditions.append("(confidence < 0.7 OR needs_review = TRUE)")

            if filters.get('min_amount'):
                where_conditions.append("ABS(amount) >= %s" if is_postgresql else "ABS(amount) >= ?")
                params.append(float(filters['min_amount']))

            if filters.get('max_amount'):
                where_conditions.append("ABS(amount) <= %s" if is_postgresql else "ABS(amount) <= ?")
                params.append(float(filters['max_amount']))

            if filters.get('start_date'):
                where_conditions.append("date >= %s" if is_postgresql else "date >= ?")
                params.append(filters['start_date'])

            if filters.get('end_date'):
                where_conditions.append("date <= %s" if is_postgresql else "date <= ?")
                params.append(filters['end_date'])

            if filters.get('keyword'):
                where_conditions.append("(description ILIKE %s OR classification_reason ILIKE %s)" if is_postgresql
                                      else "(description LIKE ? OR classification_reason LIKE ?)")
                keyword_pattern = f"%{filters['keyword']}%"
                params.extend([keyword_pattern, keyword_pattern])

            # Handle archived filter
            archived_filter = filters.get('show_archived')
            if archived_filter == 'true':
                # Show only archived transactions
                where_conditions = [c for c in where_conditions if 'archived' not in c]
                where_conditions.append("archived = TRUE")
            elif archived_filter == 'all':
                # Show both archived and non-archived transactions
                where_conditions = [c for c in where_conditions if 'archived' not in c]
            # If empty string or None, keep default behavior (active only)

            # Handle internal transaction filter
            internal_filter = filters.get('is_internal')
            if internal_filter == 'true':
                # Show only internal transactions
                where_conditions.append("is_internal_transaction = TRUE")
            elif internal_filter == 'false':
                # Show only non-internal transactions
                where_conditions.append("(is_internal_transaction = FALSE OR is_internal_transaction IS NULL)")
            # If not specified, show all (both internal and non-internal)

        where_clause = " AND ".join(where_conditions)

        # Get total count with filters
        count_query = f"SELECT COUNT(*) as total FROM transactions WHERE {where_clause}"
        if params:
            cursor.execute(count_query, tuple(params))
        else:
            cursor.execute(count_query)
        count_result = cursor.fetchone()
        total_count = count_result['total'] if is_postgresql else count_result[0]

        # Get transactions with filters and pagination
        offset = (page - 1) * per_page if page > 0 else 0
        query = f"SELECT * FROM transactions WHERE {where_clause} ORDER BY date DESC LIMIT {per_page} OFFSET {offset}"

        if params:
            cursor.execute(query, tuple(params))
        else:
            cursor.execute(query)

        results = cursor.fetchall()
        transactions = []

        for row in results:
            if is_postgresql:
                transaction = dict(row)
            else:
                transaction = dict(row)
            transactions.append(transaction)

        return transactions, total_count

def get_dashboard_stats():
    """Calculate dashboard statistics from database"""
    try:
        from database import db_manager
        tenant_id = get_current_tenant_id()

        # Use the robust database manager instead of old get_db_connection
        with db_manager.get_connection() as conn:
            if db_manager.db_type == 'postgresql':
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cursor = conn.cursor()

            # Detect database type for compatible syntax
            is_postgresql = db_manager.db_type == 'postgresql'
            placeholder = "%s" if is_postgresql else "?"

            # Total transactions (exclude archived to match /api/transactions behavior)
            cursor.execute(f"SELECT COUNT(*) as total FROM transactions WHERE tenant_id = {placeholder} AND (archived = FALSE OR archived IS NULL)", (tenant_id,))
            result = cursor.fetchone()
            total_transactions = result['total'] if is_postgresql else result[0]

            # Revenue and expenses (exclude archived)
            cursor.execute(f"SELECT COALESCE(SUM(amount), 0) as revenue FROM transactions WHERE tenant_id = {placeholder} AND amount > 0 AND (archived = FALSE OR archived IS NULL)", (tenant_id,))
            result = cursor.fetchone()
            revenue = result['revenue'] if is_postgresql else result[0]

            cursor.execute(f"SELECT COALESCE(SUM(ABS(amount)), 0) as expenses FROM transactions WHERE tenant_id = {placeholder} AND amount < 0 AND (archived = FALSE OR archived IS NULL)", (tenant_id,))
            result = cursor.fetchone()
            expenses = result['expenses'] if is_postgresql else result[0]

            # Needs review (exclude archived)
            cursor.execute(f"SELECT COUNT(*) as needs_review FROM transactions WHERE tenant_id = {placeholder} AND (confidence < 0.8 OR confidence IS NULL) AND (archived = FALSE OR archived IS NULL)", (tenant_id,))
            result = cursor.fetchone()
            needs_review = result['needs_review'] if is_postgresql else result[0]

            # Date range (exclude archived)
            cursor.execute(f"SELECT MIN(date) as min_date, MAX(date) as max_date FROM transactions WHERE tenant_id = {placeholder} AND (archived = FALSE OR archived IS NULL)", (tenant_id,))
            date_range_result = cursor.fetchone()
            if is_postgresql:
                date_range = {
                    'min': date_range_result['min_date'] or 'N/A',
                    'max': date_range_result['max_date'] or 'N/A'
                }
            else:
                date_range = {
                    'min': date_range_result[0] or 'N/A',
                    'max': date_range_result[1] or 'N/A'
                }

            # Top entities (exclude archived)
            cursor.execute(f"""
                SELECT classified_entity, COUNT(*) as count
                FROM transactions
                WHERE tenant_id = {placeholder}
                AND classified_entity IS NOT NULL
                AND (archived = FALSE OR archived IS NULL)
                GROUP BY classified_entity
                ORDER BY count DESC
                LIMIT 10
            """, (tenant_id,))
            entities = cursor.fetchall()

            # Top source files (exclude archived)
            cursor.execute(f"""
                SELECT source_file, COUNT(*) as count
                FROM transactions
                WHERE tenant_id = {placeholder}
                AND source_file IS NOT NULL
                AND (archived = FALSE OR archived IS NULL)
                GROUP BY source_file
                ORDER BY count DESC
                LIMIT 10
            """, (tenant_id,))
            source_files = cursor.fetchall()

            cursor.close()

        # Convert to float and handle NaN values (replace with 0 for valid JSON)
        import math
        revenue_float = float(revenue) if revenue is not None else 0.0
        expenses_float = float(expenses) if expenses is not None else 0.0

        # Replace NaN with 0 for valid JSON serialization
        if math.isnan(revenue_float):
            revenue_float = 0.0
        if math.isnan(expenses_float):
            expenses_float = 0.0

        return {
            'total_transactions': total_transactions,
            'total_revenue': revenue_float,
            'total_expenses': expenses_float,
            'needs_review': needs_review,
            'date_range': date_range,
            'entities': [(row['classified_entity'], row['count']) if is_postgresql else (row[0], row[1]) for row in entities],
            'source_files': [(row['source_file'], row['count']) if is_postgresql else (row[0], row[1]) for row in source_files]
        }

    except Exception as e:
        print(f"ERROR: Error calculating dashboard stats: {e}")
        return {
            'total_transactions': 0,
            'total_revenue': 0,
            'total_expenses': 0,
            'needs_review': 0,
            'date_range': {'min': 'N/A', 'max': 'N/A'},
            'entities': [],
            'source_files': []
        }

def update_transaction_field(transaction_id: str, field: str, value: str, user: str = 'web_user') -> bool:
    """Update a single field in a transaction with history tracking"""
    try:
        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        # Detect database type for compatible syntax
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'

        # Get current value for history
        cursor.execute(
            f"SELECT * FROM transactions WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}",
            (tenant_id, transaction_id)
        )
        current_row = cursor.fetchone()

        if not current_row:
            conn.close()
            return (False, None)

        # Convert tuple to dict for PostgreSQL - must match column order from cursor.description
        current_dict = {
            'transaction_id': current_row[0],
            'date': current_row[1],
            'description': current_row[2],
            'amount': current_row[3],
            'currency': current_row[4],
            'usd_equivalent': current_row[5],
            'classified_entity': current_row[6],
            'justification': current_row[7],
            'confidence': current_row[8],
            'classification_reason': current_row[9],
            'origin': current_row[10],
            'destination': current_row[11],
            'identifier': current_row[12],
            'source_file': current_row[13],
            'crypto_amount': current_row[14],
            'conversion_note': current_row[15],
            'accounting_category': current_row[16],
            'archived': current_row[17],
            'confidence_history': current_row[18],
            'ai_reassessment_count': current_row[19],
            'last_ai_review': current_row[20],
            'user_feedback_count': current_row[21],
            'ai_suggestions': current_row[22],
            'subcategory': current_row[23]
        }
        current_value = current_dict.get(field) if field in current_dict else None

        # Update the field
        update_query = f"UPDATE transactions SET {field} = {placeholder} WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}"
        cursor.execute(update_query, (value, tenant_id, transaction_id))
        logger.info(f" Updated field '{field}' to '{value}' for transaction {transaction_id}")

        # If user is manually updating a classification field, boost confidence to indicate manual verification
        classification_fields = ['classified_entity', 'accounting_category', 'subcategory', 'justification', 'description']
        updated_confidence = None
        if field in classification_fields:
            logger.info(f" Field '{field}' is a classification field - checking for confidence update")
            # Check if ALL critical fields are now filled to determine confidence level
            # Critical fields: classified_entity, accounting_category, subcategory, justification
            cursor.execute(
                f"SELECT classified_entity, accounting_category, subcategory, justification FROM transactions WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}",
                (tenant_id, transaction_id)
            )
            check_row = cursor.fetchone()

            if check_row:
                # Convert to dict for easier access (PostgreSQL returns dict-like objects)
                if is_postgresql:
                    entity = check_row[0]
                    acc_cat = check_row[1]
                    subcat = check_row[2]
                    justif = check_row[3]
                else:
                    entity = check_row[0]
                    acc_cat = check_row[1]
                    subcat = check_row[2]
                    justif = check_row[3]

                logger.info(f" Current field values - Entity: '{entity}', Category: '{acc_cat}', Subcategory: '{subcat}', Justification: '{justif}'")

                # Check if all critical fields are properly filled (not NULL, empty, or 'N/A')
                all_filled = all([
                    entity and entity not in ['', 'N/A', 'Unknown'],
                    acc_cat and acc_cat not in ['', 'N/A', 'Unknown'],
                    subcat and subcat not in ['', 'N/A', 'Unknown'],
                    justif and justif not in ['', 'N/A', 'Unknown', 'Unknown expense']
                ])

                # Set confidence to 0.95 if all fields filled, otherwise 0.75 for partial completion
                updated_confidence = 0.95 if all_filled else 0.75
                confidence_update_query = f"UPDATE transactions SET confidence = {placeholder} WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}"
                cursor.execute(confidence_update_query, (updated_confidence, tenant_id, transaction_id))

                if all_filled:
                    logger.info(f" CONFIDENCE: Boosted confidence to 0.95 for transaction {transaction_id} - ALL critical fields filled by manual {field} edit")
                else:
                    logger.info(f"  CONFIDENCE: Set confidence to 0.75 for transaction {transaction_id} - partial completion by manual {field} edit")

        # CRITICAL: Commit the UPDATE immediately to ensure it persists
        # In PostgreSQL, if a later query fails, it can rollback the entire transaction
        conn.commit()

        logger.info(f" Transaction {transaction_id} committed: field={field}, value={value}, updated_confidence={updated_confidence}")

        # Record change in history (only if table exists)
        # This is done in a separate transaction so failures don't affect the main update
        try:
            # The transaction_history table uses old_values/new_values as JSONB
            old_values_json = {field: current_value} if current_value is not None else {}
            new_values_json = {field: value}

            cursor.execute(f"""
                INSERT INTO transaction_history (transaction_id, tenant_id, old_values, new_values, changed_by)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            """, (transaction_id, tenant_id, json.dumps(old_values_json), json.dumps(new_values_json), user))
            conn.commit()
        except Exception as history_error:
            print(f"INFO: Could not record history: {history_error}")
            # Rollback only affects the history insert, main update already committed
            try:
                conn.rollback()
            except:
                pass

        # Close connection and return success with updated confidence
        conn.close()
        return (True, updated_confidence)

    except Exception as e:
        print(f"ERROR: Error updating transaction field: {e}")
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        try:
            conn.close()
        except:
            pass
        return (False, None)

def extract_entity_patterns_with_llm(transaction_id: str, entity_name: str, description: str, claude_client) -> Dict:
    """
    Use Claude to extract identifying patterns from a transaction description when user classifies it to an entity.
    This implements the pure LLM pattern learning approach.
    """
    try:
        if not claude_client or not description or not entity_name:
            return {}

        prompt = f"""
Analyze this transaction description and extract the key identifying patterns that uniquely identify the entity "{entity_name}".

TRANSACTION DESCRIPTION:
"{description}"

ENTITY CLASSIFIED TO: "{entity_name}"

Extract and return the following identifying patterns in JSON format:

1. **company_names**: List of company/organization names mentioned (full names, abbreviations, variations)
2. **originator_patterns**: Payment processor identifiers like "ORIG CO NAME:", "B/O:", "IND NAME:", etc.
3. **bank_identifiers**: Bank names, routing info, or financial institution identifiers
4. **transaction_keywords**: Specific keywords that repeatedly appear in transactions from this entity
5. **reference_patterns**: Invoice numbers, account numbers, or reference ID patterns
6. **payment_method_type**: Type of transaction (WIRE, ACH, FEDWIRE, CHIPS, etc.)

IMPORTANT: Extract patterns that are SPECIFIC to this entity and would help identify future transactions from the same entity, not generic patterns.

Example output format:
{{
  "company_names": ["EVERMINER LLC", "EVERMINER"],
  "originator_patterns": ["B/O: EVERMINER LLC"],
  "bank_identifiers": ["CHOICE FINANCIAL GROUP/091311229"],
  "transaction_keywords": ["hosting", "invoice"],
  "reference_patterns": ["INVOICE \\\\d{{3}}-\\\\d{{3}}-\\\\d{{6}}"],
  "payment_method_type": "FEDWIRE"
}}

Return only the JSON object, no additional text.
"""

        print(f"DEBUG: Extracting entity patterns for {entity_name} from transaction {transaction_id}")

        response = claude_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()
        print(f"DEBUG: Claude pattern extraction response: {response_text[:200]}...")

        # Parse JSON response
        pattern_data = json.loads(response_text)

        # Store patterns in database with tenant isolation
        tenant_id = get_current_tenant_id()
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'

        cursor.execute(f"""
            INSERT INTO entity_patterns (tenant_id, entity_name, pattern_data, transaction_id, confidence_score)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
        """, (tenant_id, entity_name, json.dumps(pattern_data), transaction_id, 1.0))

        conn.commit()
        conn.close()

        print(f"SUCCESS: Stored entity patterns for {entity_name}: {pattern_data}")

        #  NEW: Update aggregated pattern statistics in real-time
        # This ensures the TF-IDF scores are always current
        try:
            # Update statistics for each pattern type
            for company_name in pattern_data.get('company_names', []):
                if is_meaningful_pattern(company_name, entity_name, tenant_id):
                    update_pattern_statistics(entity_name, company_name, 'company_name', tenant_id)

            for keyword in pattern_data.get('transaction_keywords', []):
                if is_meaningful_pattern(keyword, entity_name, tenant_id):
                    update_pattern_statistics(entity_name, keyword, 'keyword', tenant_id)

            for bank_id in pattern_data.get('bank_identifiers', []):
                if is_meaningful_pattern(bank_id, entity_name, tenant_id):
                    update_pattern_statistics(entity_name, bank_id, 'bank_identifier', tenant_id)

            for orig_pattern in pattern_data.get('originator_patterns', []):
                if is_meaningful_pattern(orig_pattern, entity_name, tenant_id):
                    update_pattern_statistics(entity_name, orig_pattern, 'originator', tenant_id)

            for payment_method in pattern_data.get('payment_method_type', []) if isinstance(pattern_data.get('payment_method_type'), list) else [pattern_data.get('payment_method_type')] if pattern_data.get('payment_method_type') else []:
                if is_meaningful_pattern(payment_method, entity_name, tenant_id):
                    update_pattern_statistics(entity_name, payment_method, 'payment_method', tenant_id)

            print(f" Real-time TF-IDF statistics updated for {entity_name}")

        except Exception as stats_error:
            # Don't fail the whole function if statistics update fails
            print(f"  WARNING: Failed to update pattern statistics: {stats_error}")

        return pattern_data

    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse Claude response as JSON: {e}")
        print(f"ERROR: Response was: {response_text}")
        return {}
    except Exception as e:
        print(f"ERROR: Failed to extract entity patterns: {e}")
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        return {}

def get_similar_transactions_tfidf(transaction_id: str, entity_name: str, tenant_id: str,  max_results: int = 50) -> List[Dict]:
    """
     NEW: TF-IDF-based similar transactions finder (REPLACES old pattern matching)

    Uses the sophisticated TF-IDF pattern system with:
    - Pre-filtering optimization (5x faster)
    - Z-score normalized amount matching
    - Confidence scoring with reinforcement learning
    - Transaction context awareness

    Args:
        transaction_id: The reference transaction ID
        entity_name: The entity to find similar transactions for
        tenant_id: Tenant ID for multi-tenant isolation
        max_results: Maximum number of similar transactions to return (default 50)

    Returns:
        List of dicts with transaction details sorted by match score
    """
    try:
        from database import db_manager

        # Step 1: Get reference transaction details
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT transaction_id, description, amount, date, classified_entity
            FROM transactions
            WHERE tenant_id = %s AND transaction_id = %s
        """, (tenant_id, transaction_id))

        ref_tx = cursor.fetchone()
        if not ref_tx:
            logging.warning(f"[TFIDF_SIMILAR] Reference transaction {transaction_id} not found")
            return []

        # Extract reference transaction details
        if isinstance(ref_tx, dict):
            ref_desc = ref_tx.get('description', '')
            ref_amount = ref_tx.get('amount', 0)
        else:
            ref_desc = ref_tx[1] if len(ref_tx) > 1 else ''
            ref_amount = ref_tx[2] if len(ref_tx) > 2 else 0

        logging.info(f"[TFIDF_SIMILAR] Finding similar transactions for entity='{entity_name}', desc='{ref_desc[:50]}...', amount=${ref_amount}")

        # Step 2: Use TF-IDF system to score ALL unclassified/different entity transactions
        cursor.execute("""
            SELECT transaction_id, description, amount, date, classified_entity, suggested_entity
            FROM transactions
            WHERE tenant_id = %s
            AND transaction_id != %s
            AND (classified_entity IS NULL OR classified_entity = '' OR classified_entity != %s)
            ORDER BY date DESC
            LIMIT 500
        """, (tenant_id, transaction_id, entity_name))

        candidate_txs = cursor.fetchall()
        conn.close()

        if not candidate_txs:
            logging.info(f"[TFIDF_SIMILAR] No candidate transactions found")
            return []

        logging.info(f"[TFIDF_SIMILAR] Scoring {len(candidate_txs)} candidate transactions using TF-IDF")

        # Step 3: Score each candidate using the TF-IDF matching system
        scored_transactions = []

        for tx in candidate_txs:
            if isinstance(tx, dict):
                tx_id = tx.get('transaction_id')
                tx_desc = tx.get('description', '')
                tx_amount = tx.get('amount', 0)
                tx_account = tx.get('account', '')
                tx_date = tx.get('date')
                tx_entity = tx.get('classified_entity', '')
                tx_suggested = tx.get('suggested_entity', '')
            else:
                tx_id = tx[0]
                tx_desc = tx[1] if len(tx) > 1 else ''
                tx_amount = tx[2] if len(tx) > 2 else 0
                tx_account = tx[3] if len(tx) > 3 else ''
                tx_date = tx[4] if len(tx) > 4 else None
                tx_entity = tx[5] if len(tx) > 5 else ''
                tx_suggested = tx[6] if len(tx) > 6 else ''

            #  Use the sophisticated TF-IDF scoring system
            match_result = calculate_entity_match_score(
                description=tx_desc,
                entity_name=entity_name,
                tenant_id=tenant_id,
                amount=tx_amount,
                account=tx_account
            )

            score = match_result.get('score', 0)
            confidence = match_result.get('confidence', 0)
            amount_match = match_result.get('amount_match')
            reasoning = match_result.get('reasoning', '')

            # Only include transactions with meaningful match scores (>= 0.3)
            if score >= 0.3:
                scored_transactions.append({
                    'transaction_id': tx_id,
                    'description': tx_desc,
                    'amount': float(tx_amount) if tx_amount else 0,
                    'account': tx_account,
                    'date': str(tx_date) if tx_date else '',
                    'classified_entity': tx_entity,
                    'suggested_entity': tx_suggested,
                    'match_score': round(score, 3),
                    'confidence': round(confidence, 3),
                    'amount_match': round(amount_match, 3) if amount_match is not None else None,
                    'reasoning': reasoning
                })

        # Step 4: Sort by match score (highest first) and limit results
        scored_transactions.sort(key=lambda x: x['match_score'], reverse=True)
        top_matches = scored_transactions[:max_results]

        logging.info(f"[TFIDF_SIMILAR] Found {len(top_matches)} similar transactions (scores >= 0.3)")

        return top_matches

    except Exception as e:
        logging.error(f"[TFIDF_SIMILAR] Error finding similar transactions: {e}")
        logging.error(traceback.format_exc())
        return []


def find_similar_with_tfidf_after_suggestion(transaction_id: str, entity_name: str, tenant_id: str,
                                             wallet_address: str = None, max_results: int = 50) -> List[Dict]:
    """
     UPDATED: Simple Match engine for "Apply AI Suggestions" modal

    This replaces the TF-IDF approach with the proven Simple Match engine
    that uses keyword-based Jaccard similarity to prevent false positives.

    Optimized for the "apply suggestions to similar transactions" workflow:
    - Uses keyword-based similarity (prevents gas station → API service false matches)
    - Requires description field matching (most important field)
    - Prioritizes wallet address matches (crypto transactions)
    - Only returns uncategorized/low-confidence transactions
    - Fast and accurate

    Args:
        transaction_id: The reference transaction that was just categorized
        entity_name: The entity that was just applied to the reference transaction
        tenant_id: Tenant ID for multi-tenant isolation
        wallet_address: Optional wallet address from origin/destination to prioritize matches
        max_results: Maximum number of similar transactions to return

    Returns:
        List of dicts with transaction details + similarity scores, sorted by relevance
    """
    try:
        from database import db_manager
        from simple_match_engine import find_similar_simple

        # Step 1: Get reference transaction details
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT transaction_id, description, amount, date, classified_entity,
                   origin, destination, accounting_category, subcategory, justification
            FROM transactions
            WHERE tenant_id = %s AND transaction_id = %s
        """, (tenant_id, transaction_id))

        ref_tx = cursor.fetchone()
        if not ref_tx:
            logging.warning(f"[SIMPLE_MATCH_AFTER_SUGGESTION] Reference transaction {transaction_id} not found")
            conn.close()
            return []

        # Extract reference transaction details
        if isinstance(ref_tx, dict):
            ref_tx_dict = ref_tx
        else:
            # Column order: transaction_id, description, amount, date, classified_entity, origin, destination, accounting_category, subcategory, justification
            ref_tx_dict = {
                'transaction_id': ref_tx[0],
                'description': ref_tx[1] if len(ref_tx) > 1 else '',
                'amount': ref_tx[2] if len(ref_tx) > 2 else 0,
                'date': ref_tx[3] if len(ref_tx) > 3 else None,
                'classified_entity': ref_tx[4] if len(ref_tx) > 4 else '',
                'origin': ref_tx[5] if len(ref_tx) > 5 else '',
                'destination': ref_tx[6] if len(ref_tx) > 6 else '',
                'accounting_category': ref_tx[7] if len(ref_tx) > 7 else '',
                'subcategory': ref_tx[8] if len(ref_tx) > 8 else '',
                'justification': ref_tx[9] if len(ref_tx) > 9 else '',
            }

        ref_desc = ref_tx_dict.get('description', '')
        ref_origin = ref_tx_dict.get('origin', '')
        ref_dest = ref_tx_dict.get('destination', '')

        logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION] Finding similar transactions for entity='{entity_name}', desc='{ref_desc[:50]}...'")

        # Step 2: Query uncategorized or low-confidence transactions
        #  NEW: Add detailed logging of query criteria
        logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION]  Querying candidates with:")
        logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION]   - tenant_id: {tenant_id}")
        logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION]   - exclude: {transaction_id}")
        logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION]   - criteria: confidence < 0.8 OR entity NULL/empty/N/A")

        #  NEW: Extract first significant word from description for filtering
        # This ensures we prioritize similar transaction types (e.g., all "Ethereum" transactions together)
        ref_desc_words = ref_desc.upper().split()
        ref_first_word = ref_desc_words[0] if ref_desc_words else ''

        cursor.execute("""
            SELECT transaction_id, description, amount, date, classified_entity,
                   origin, destination, confidence, accounting_category, subcategory, justification
            FROM transactions
            WHERE tenant_id = %s
            AND transaction_id != %s
            AND (
                confidence IS NULL
                OR confidence < 0.8
                OR classified_entity IS NULL
                OR classified_entity = ''
                OR classified_entity = 'N/A'
            )
            ORDER BY
                -- Prioritize transactions with same first word (e.g., "Ethereum", "USDT", "Tether")
                CASE WHEN UPPER(description) LIKE %s THEN 0 ELSE 1 END ASC,
                -- Then by confidence (lowest first)
                CASE
                    WHEN confidence IS NULL THEN 0
                    WHEN confidence < 0.5 THEN 1
                    WHEN confidence < 0.8 THEN 2
                    ELSE 3
                END ASC,
                -- Then by date (newest first)
                date DESC
            LIMIT 500
        """, (tenant_id, transaction_id, f'{ref_first_word}%'))

        candidate_txs = cursor.fetchall()
        conn.close()

        if not candidate_txs:
            logging.warning(f"[SIMPLE_MATCH_AFTER_SUGGESTION]  No candidate transactions found in database")
            return []

        logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION]  Found {len(candidate_txs)} candidate transactions to score")

        #  NEW: Log sample of candidate descriptions to understand what we're matching against
        logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION]  Sample of first 10 candidates:")
        for i, tx in enumerate(candidate_txs[:10], 1):
            sample_desc = tx[1] if len(tx) > 1 else '' if isinstance(tx, tuple) else tx.get('description', '')
            sample_entity = tx[4] if len(tx) > 4 else '' if isinstance(tx, tuple) else tx.get('classified_entity', '')
            logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION]   {i}. '{sample_desc[:60]}...' (entity: {sample_entity})")

        # Convert candidates to dicts for Simple Match engine
        candidate_dicts = []
        for tx in candidate_txs:
            if isinstance(tx, dict):
                candidate_dicts.append(tx)
            else:
                # Column order: transaction_id, description, amount, date, classified_entity, origin, destination, confidence, accounting_category, subcategory, justification
                candidate_dicts.append({
                    'transaction_id': tx[0],
                    'description': tx[1] if len(tx) > 1 else '',
                    'amount': tx[2] if len(tx) > 2 else 0,
                    'date': tx[3] if len(tx) > 3 else None,
                    'classified_entity': tx[4] if len(tx) > 4 else '',
                    'origin': tx[5] if len(tx) > 5 else '',
                    'destination': tx[6] if len(tx) > 6 else '',
                    'confidence': tx[7] if len(tx) > 7 else 0,
                    'accounting_category': tx[8] if len(tx) > 8 else '',
                    'subcategory': tx[9] if len(tx) > 9 else '',
                    'justification': tx[10] if len(tx) > 10 else '',
                })

        # Step 3: Use Simple Match engine to find similar transactions
        # Use min_confidence=0.3 to match Simple Match engine defaults
        logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION]  Running Simple Match engine with min_confidence=0.3...")
        logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION]  DEBUG MODE ENABLED - Detailed matching logs will follow")
        matches = find_similar_simple(
            target_transaction=ref_tx_dict,
            candidate_transactions=candidate_dicts,
            min_confidence=0.3,
            debug=True  #  Enable detailed logging
        )

        logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION]  Simple Match found {len(matches)} similar transactions")

        # Step 4: Apply wallet address boost if applicable
        wallet_exact_matches = 0
        if wallet_address:
            logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION] Applying wallet address boost for: {wallet_address[:30]}...")
            wallet_lower = wallet_address.lower()

            for match in matches:
                tx_origin = match.get('origin', '')
                tx_dest = match.get('destination', '')

                # Check for wallet match
                if (tx_origin and wallet_lower in tx_origin.lower()) or \
                   (tx_dest and wallet_lower in tx_dest.lower()):
                    # Boost confidence by 0.2 (20%) for wallet matches
                    original_confidence = match.get('confidence', 0)
                    match['confidence'] = min(1.0, original_confidence + 0.2)
                    match['wallet_boost'] = 0.2
                    match['has_wallet_match'] = True
                    wallet_exact_matches += 1
                    logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION]    Wallet match: '{match.get('description', '')[:40]}...' boosted from {original_confidence:.3f} to {match['confidence']:.3f}")
                else:
                    match['wallet_boost'] = None
                    match['has_wallet_match'] = False

            logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION] Found {wallet_exact_matches} wallet address matches (boosted)")

        # Step 5: Sort by wallet match status and confidence
        matches.sort(key=lambda x: (x.get('has_wallet_match', False), x.get('confidence', 0)), reverse=True)

        # Limit to max_results
        top_matches = matches[:max_results]

        # Step 6: Format for API response (ensure consistency with old TF-IDF format)
        # Helper function to sanitize NaN/Infinity values for JSON serialization
        def sanitize_for_json(value, default=0):
            """Convert NaN/Infinity to safe JSON values"""
            import math
            if value is None:
                return default
            if isinstance(value, float):
                if math.isnan(value) or math.isinf(value):
                    return default
            return value

        formatted_matches = []
        for match in top_matches:
            # Extract classification fields from nested suggested_values structure
            suggested_values = match.get('suggested_values', {})

            formatted_matches.append({
                'transaction_id': match.get('transaction_id'),
                'description': match.get('description', ''),
                'amount': sanitize_for_json(match.get('amount', 0), default=0),
                'date': str(match.get('date', '')),
                'classified_entity': suggested_values.get('classified_entity', ''),
                'accounting_category': suggested_values.get('accounting_category', ''),
                'subcategory': suggested_values.get('subcategory', ''),
                'justification': suggested_values.get('justification', ''),
                'confidence': sanitize_for_json(match.get('confidence', 0), default=0),
                'match_score': round(sanitize_for_json(match.get('confidence', 0), default=0), 3),
                'base_tfidf_score': None,  # Not using TF-IDF anymore
                'wallet_boost': match.get('wallet_boost'),
                'amount_match': None,  # Simple Match doesn't return this separately
                'reasoning': f"Simple Match: {', '.join(match.get('match_details', {}).get('matched_fields', []))}",
                'origin': match.get('origin', ''),
                'destination': match.get('destination', ''),
                'has_wallet_match': match.get('has_wallet_match', False),
                'match_details': match.get('match_details', {}),
                'suggested_values': suggested_values
            })

        logging.info(f"[SIMPLE_MATCH_AFTER_SUGGESTION] Returning {len(formatted_matches)} formatted matches")

        return formatted_matches

    except Exception as e:
        logging.error(f"[SIMPLE_MATCH_AFTER_SUGGESTION] Error finding similar transactions: {e}")
        logging.error(traceback.format_exc())
        return []


def get_claude_analyzed_similar_descriptions(context: Dict, claude_client) -> List[str]:
    """
      DEPRECATED: Use get_similar_transactions_tfidf() instead

    Use Claude to intelligently analyze which transactions should have similar descriptions/entities
    """
    try:
        if not claude_client or not context:
            return []

        transaction_id = context.get('transaction_id')
        new_value = context.get('value', '')
        field_type = context.get('field_type', '')  # 'similar_descriptions' or 'similar_entities'

        if not transaction_id or not new_value:
            return []

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        try:
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            # Get the current transaction
            cursor.execute(
                f"SELECT description, classified_entity FROM transactions WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}",
                (tenant_id, transaction_id)
            )
            current_tx = cursor.fetchone()

            if not current_tx:
                return []

            # Safe extraction of description and entity from current_tx
            try:
                if is_postgresql:
                    current_description = current_tx.get('description', '') if isinstance(current_tx, dict) else (current_tx[0] if len(current_tx) > 0 else '')
                    current_entity = current_tx.get('classified_entity', '') if isinstance(current_tx, dict) else (current_tx[1] if len(current_tx) > 1 else '')
                else:
                    current_description = current_tx[0] if len(current_tx) > 0 else ''
                    current_entity = current_tx[1] if len(current_tx) > 1 else ''
            except Exception as e:
                print(f"ERROR: Failed to extract description/entity from current_tx: {e}, type={type(current_tx)}, len={len(current_tx) if hasattr(current_tx, '__len__') else 'N/A'}")
                return []

            # Different logic for entity classification vs description cleanup vs accounting category
            if field_type == 'similar_entities':
                # For entity classification: Use learned patterns to pre-filter candidates
                logging.info(f"[SIMILAR_ENTITIES] Searching for similar entities - current entity: {current_entity}, new entity: {new_value}")

                # STEP 0: Check if current transaction has wallet addresses - HIGHEST PRIORITY
                cursor.execute(
                    f"SELECT origin, destination FROM transactions WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}",
                    (tenant_id, transaction_id)
                )
                wallet_row = cursor.fetchone()
                current_origin = wallet_row[0] if wallet_row and len(wallet_row) > 0 else ''
                current_dest = wallet_row[1] if wallet_row and len(wallet_row) > 1 else ''

                # Check if we have a wallet address (>20 chars indicates crypto wallet)
                has_wallet = False
                wallet_address = None
                if current_origin and len(str(current_origin)) > 20:
                    has_wallet = True
                    wallet_address = str(current_origin)
                    logging.info(f"[WALLET_MATCH] Found wallet in ORIGIN: {wallet_address[:40]}...")
                elif current_dest and len(str(current_dest)) > 20:
                    has_wallet = True
                    wallet_address = str(current_dest)
                    logging.info(f"[WALLET_MATCH] Found wallet in DESTINATION: {wallet_address[:40]}...")

                # First, fetch learned patterns for this entity to build SQL filters (tenant-isolated)
                pattern_conditions = []
                params = []  # Initialize params list for SQL query
                try:
                    tenant_id = get_current_tenant_id()
                    from database import db_manager
                    pattern_conn = db_manager._get_postgresql_connection()
                    pattern_cursor = pattern_conn.cursor()
                    pattern_placeholder_temp = '%s' if hasattr(pattern_cursor, 'mogrify') else '?'

                    pattern_cursor.execute(f"""
                        SELECT pattern_data
                        FROM entity_patterns
                        WHERE tenant_id = {pattern_placeholder_temp}
                        AND entity_name = {pattern_placeholder_temp}
                        ORDER BY created_at DESC
                        LIMIT 5
                    """, (tenant_id, new_value))

                    learned_patterns_rows = pattern_cursor.fetchall()
                    pattern_conn.close()

                    if learned_patterns_rows and len(learned_patterns_rows) > 0:
                        print(f"DEBUG: Found {len(learned_patterns_rows)} learned patterns for {new_value}, building SQL filters...")
                        # Extract all company names, keywords, and bank identifiers from patterns
                        all_company_names = set()
                        all_keywords = set()
                        all_bank_ids = set()

                        for pattern_row in learned_patterns_rows:
                            pattern_data = pattern_row.get('pattern_data', '{}') if isinstance(pattern_row, dict) else pattern_row[0]
                            if isinstance(pattern_data, str):
                                pattern_data = json.loads(pattern_data)

                            all_company_names.update(pattern_data.get('company_names', []))
                            all_keywords.update(pattern_data.get('transaction_keywords', []))
                            all_bank_ids.update(pattern_data.get('bank_identifiers', []))

                        # Build ILIKE conditions for each pattern element
                        for company in all_company_names:
                            if company:  # Skip empty strings
                                pattern_conditions.append(f"description ILIKE {placeholder}")
                                params.append(f"%{company}%")

                        for keyword in all_keywords:
                            if keyword and len(keyword) > 3:  # Skip short/generic keywords
                                pattern_conditions.append(f"description ILIKE {placeholder}")
                                params.append(f"%{keyword}%")

                        for bank_id in all_bank_ids:
                            if bank_id:
                                pattern_conditions.append(f"description ILIKE {placeholder}")
                                params.append(f"%{bank_id}%")

                        print(f"DEBUG: Built {len(pattern_conditions)} SQL pattern filters")
                except Exception as pattern_error:
                    print(f"WARNING: Failed to build pattern filters: {pattern_error}")

                # Build the query - WALLET MATCHING TAKES HIGHEST PRIORITY
                if has_wallet and wallet_address:
                    # PRIORITY 1: Wallet address matching - find ALL transactions with same wallet, regardless of confidence/classification
                    # When wallet matches, we want to suggest ALL related transactions for bulk updates
                    logging.info(f"[WALLET_MATCH] Using WALLET-BASED filtering (HIGHEST PRIORITY)")
                    base_query = f"""
                        SELECT transaction_id, date, description, confidence, classified_entity, amount
                        FROM transactions
                        WHERE transaction_id != {placeholder}
                        AND (origin ILIKE {placeholder} OR destination ILIKE {placeholder})
                        ORDER BY date DESC
                        LIMIT 100
                    """
                    params = [transaction_id, f"%{wallet_address}%", f"%{wallet_address}%"]
                    logging.info(f"[WALLET_MATCH] Searching for ALL transactions with wallet: {wallet_address[:40]}... (no confidence/entity filters)")
                elif pattern_conditions:
                    # PRIORITY 2: Pattern-based filtering from learned patterns
                    # Use learned patterns to pre-filter candidates
                    pattern_filter = " OR ".join(pattern_conditions)
                    base_query = f"""
                        SELECT transaction_id, date, description, confidence, classified_entity, amount
                        FROM transactions
                        WHERE transaction_id != {placeholder}
                        AND (
                            classified_entity = 'NEEDS REVIEW'
                            OR classified_entity = 'Unclassified Expense'
                            OR classified_entity = 'Unclassified Revenue'
                            OR classified_entity IS NULL
                            OR (classified_entity IS NOT NULL AND classified_entity != {placeholder})
                        )
                        AND ({pattern_filter})
                        LIMIT 30
                    """
                    params = [transaction_id, new_value] + params
                    print(f"DEBUG: Using pattern-based pre-filtering with {len(pattern_conditions)} conditions")
                    print(f"DEBUG: Pattern filter clause: {pattern_filter}")
                    print(f"DEBUG: Complete SQL query: {base_query}")
                    print(f"DEBUG: Query parameters: {params}")
                else:
                    # No patterns learned yet - use basic similarity based on current transaction description
                    print(f"DEBUG: No patterns found, using description-based filtering as fallback")
                    # Extract key terms from current description for basic filtering
                    desc_words = [w.strip() for w in current_description.upper().split() if len(w.strip()) > 4]
                    desc_conditions = []
                    for word in desc_words[:5]:  # Use top 5 longest words
                        if word and not word.isdigit():
                            desc_conditions.append(f"UPPER(description) LIKE {placeholder}")
                            params.append(f"%{word}%")

                    if desc_conditions:
                        desc_filter = " OR ".join(desc_conditions)
                        base_query = f"""
                            SELECT transaction_id, date, description, confidence, classified_entity, amount
                            FROM transactions
                            WHERE transaction_id != {placeholder}
                            AND (
                                classified_entity = 'NEEDS REVIEW'
                                OR classified_entity = 'Unclassified Expense'
                                OR classified_entity = 'Unclassified Revenue'
                                OR classified_entity IS NULL
                                OR (classified_entity IS NOT NULL AND classified_entity != {placeholder})
                            )
                            AND ({desc_filter})
                            LIMIT 30
                        """
                        params = [transaction_id, new_value] + params
                    else:
                        # Ultimate fallback - just grab unclassified transactions
                        base_query = f"""
                            SELECT transaction_id, date, description, confidence, classified_entity, amount
                            FROM transactions
                            WHERE transaction_id != {placeholder}
                            AND (
                                classified_entity = 'NEEDS REVIEW'
                                OR classified_entity = 'Unclassified Expense'
                                OR classified_entity = 'Unclassified Revenue'
                                OR classified_entity IS NULL
                                OR (classified_entity IS NOT NULL AND classified_entity != {placeholder})
                            )
                            LIMIT 50
                        """
                        params = [transaction_id, new_value]
            elif field_type == 'similar_accounting':
                # For accounting category: find transactions from same entity that need review
                # Include: uncategorized, low confidence, OR different category (to suggest recategorization)
                print(f"DEBUG: Searching for similar accounting categories - entity: {current_entity}, new category: {new_value}")

                base_query = f"""
                    SELECT transaction_id, date, description, amount, accounting_category
                    FROM transactions
                    WHERE transaction_id != {placeholder}
                    AND classified_entity = {placeholder}
                    AND (
                        accounting_category IS NULL
                        OR accounting_category = 'N/A'
                        OR confidence < 0.7
                        OR (accounting_category != {placeholder} AND accounting_category IS NOT NULL)
                    )
                    LIMIT 30
                """
                params = [transaction_id, current_entity, new_value]
            elif field_type == 'similar_subcategory':
                # For subcategory: find transactions from same entity that need subcategory or have different subcategory
                print(f"DEBUG: Searching for similar subcategories - entity: {current_entity}, new subcategory: {new_value}")

                base_query = f"""
                    SELECT transaction_id, date, description, amount, subcategory
                    FROM transactions
                    WHERE transaction_id != {placeholder}
                    AND classified_entity = {placeholder}
                    AND (
                        subcategory IS NULL
                        OR subcategory = 'N/A'
                        OR subcategory = ''
                        OR (subcategory != {placeholder} AND subcategory IS NOT NULL)
                    )
                    LIMIT 30
                """
                params = [transaction_id, current_entity, new_value]
            else:
                # For description cleanup: find transactions with same entity but different descriptions
                # Since the description has already been updated, we search by entity
                print(f"DEBUG: Searching for similar descriptions - entity: {current_entity}, new description: {new_value}")

                base_query = f"""
                    SELECT transaction_id, date, description, confidence
                    FROM transactions
                    WHERE transaction_id != {placeholder}
                    AND classified_entity = {placeholder}
                    AND description != {placeholder}
                    LIMIT 20
                """
                params = [transaction_id, current_entity, new_value]

            logging.info(f"[SQL_QUERY] About to execute query with {len(params)} parameters")
            try:
                cursor.execute(base_query, tuple(params))
                candidate_txs = cursor.fetchall()
                logging.info(f"[SQL_QUERY] Query executed successfully, fetched {len(candidate_txs) if candidate_txs else 0} candidate transactions")
            except Exception as query_error:
                logging.error(f"[SQL_QUERY] Query execution failed: {query_error}")
                logging.error(f"[SQL_QUERY] Query was: {base_query}")
                logging.error(f"[SQL_QUERY] Parameters were: {params}")
                return []

            if not candidate_txs:
                logging.info(f"[SQL_QUERY] No candidate transactions found - returning empty array")
                return []

            logging.info(f"[SQL_QUERY] Found {len(candidate_txs)} candidate transactions, sending to Claude AI for similarity analysis")
            for i, tx in enumerate(candidate_txs[:3]):
                logging.debug(f"  - Candidate {i+1}: {tx}")

            # IMPORTANT: If wallet matching was used, skip Claude AI analysis - wallet matches are definitive!
            # Wallet address matching is 100% accurate, so we don't need AI to filter further
            if has_wallet and wallet_address:
                logging.info(f"[WALLET_MATCH] Bypassing Claude AI analysis - wallet matches are definitive")
                logging.info(f"[WALLET_MATCH] Returning ALL {len(candidate_txs)} wallet-matched transactions")

                # Return all candidates without Claude filtering
                result = []
                for tx in candidate_txs:
                    try:
                        if is_postgresql and isinstance(tx, dict):
                            tx_id = tx.get('transaction_id', '')
                            date = tx.get('date', '')
                            desc = tx.get('description', '')
                            conf = tx.get('confidence', 'N/A')
                            amount = tx.get('amount', 0)
                            entity = tx.get('classified_entity', '')
                        else:
                            tx_id = tx[0] if len(tx) > 0 else ''
                            date = tx[1] if len(tx) > 1 else ''
                            desc = tx[2] if len(tx) > 2 else ''
                            conf = tx[3] if len(tx) > 3 else 'N/A'
                            entity = tx[4] if len(tx) > 4 else ''
                            amount = tx[5] if len(tx) > 5 else 0

                        result.append({
                            'transaction_id': tx_id,
                            'date': date,
                            'description': desc[:80] + "..." if len(desc) > 80 else desc,
                            'confidence': conf or 'N/A',
                            'amount': amount,
                            'classified_entity': entity,
                            'accounting_category': 'N/A'
                        })
                    except Exception as e:
                        logging.error(f"[WALLET_MATCH] Failed to format transaction: {e}")

                logging.info(f"[WALLET_MATCH] Successfully returned {len(result)} wallet-matched transactions")
                return result

            # Use Claude to analyze which transactions are truly similar
            candidate_descriptions = []
            for i, tx in enumerate(candidate_txs):
                try:
                    if is_postgresql:
                        desc = tx.get('description', '') if isinstance(tx, dict) else str(tx[2] if len(tx) > 2 else '')
                        if field_type == 'similar_accounting':
                            amount = tx.get('amount', '') if isinstance(tx, dict) else str(tx[3] if len(tx) > 3 else '')
                            current_cat = tx.get('accounting_category', 'N/A') if isinstance(tx, dict) else str(tx[4] if len(tx) > 4 else 'N/A')
                        elif field_type == 'similar_subcategory':
                            amount = tx.get('amount', '') if isinstance(tx, dict) else str(tx[3] if len(tx) > 3 else '')
                            current_subcat = tx.get('subcategory', 'N/A') if isinstance(tx, dict) else str(tx[4] if len(tx) > 4 else 'N/A')
                    else:
                        desc = tx[2] if len(tx) > 2 else ''
                        if field_type == 'similar_accounting':
                            amount = tx[3] if len(tx) > 3 else ''
                            tx_type = tx[5] if len(tx) > 5 else ''
                            current_cat = tx[4] if len(tx) > 4 else 'N/A'
                        elif field_type == 'similar_subcategory':
                            amount = tx[3] if len(tx) > 3 else ''
                            current_subcat = tx[4] if len(tx) > 4 else 'N/A'

                    desc_text = f"{desc[:100]}..." if len(desc) > 100 else desc

                    if field_type == 'similar_accounting':
                        # Determine direction from amount
                        direction = "DEBIT/Expense" if float(amount) < 0 else "CREDIT/Revenue" if float(amount) > 0 else "Zero"
                        candidate_descriptions.append(
                            f"Transaction {i+1}: {desc_text} | Direction: {direction} | Amount: ${amount} | Current Category: {current_cat}"
                        )
                    elif field_type == 'similar_subcategory':
                        # Determine direction from amount
                        direction = "DEBIT/Expense" if float(amount) < 0 else "CREDIT/Revenue" if float(amount) > 0 else "Zero"
                        candidate_descriptions.append(
                            f"Transaction {i+1}: {desc_text} | Direction: {direction} | Amount: ${amount} | Current Subcategory: {current_subcat}"
                        )
                    else:
                        candidate_descriptions.append(f"Transaction {i+1}: {desc_text}")
                except Exception as e:
                    print(f"ERROR: Failed to process candidate tx {i}: {e}")
                    candidate_descriptions.append(f"Transaction {i+1}: [Error loading description]")

            # Different prompts for entity classification vs description cleanup vs accounting category
            if field_type == 'similar_entities':
                current_tx_type = context.get('type', '')
                current_source = context.get('source_file', '')

                # Fetch learned patterns for this entity from database
                learned_patterns_text = "No patterns learned yet for this entity."
                try:
                    from database import db_manager
                    pattern_conn = db_manager._get_postgresql_connection()
                    pattern_cursor = pattern_conn.cursor()
                    pattern_placeholder = '%s' if hasattr(pattern_cursor, 'mogrify') else '?'

                    pattern_cursor.execute(f"""
                        SELECT pattern_data, confidence_score
                        FROM entity_patterns
                        WHERE entity_name = {pattern_placeholder}
                        ORDER BY created_at DESC
                        LIMIT 10
                    """, (new_value,))

                    learned_patterns = pattern_cursor.fetchall()
                    pattern_conn.close()

                    if learned_patterns and len(learned_patterns) > 0:
                        learned_patterns_text = "LEARNED PATTERNS FOR THIS ENTITY:\n"
                        for i, pattern_row in enumerate(learned_patterns):
                            pattern_data = pattern_row.get('pattern_data', '{}') if isinstance(pattern_row, dict) else pattern_row[0]
                            if isinstance(pattern_data, str):
                                pattern_data = json.loads(pattern_data)

                            learned_patterns_text += f"\nPattern {i+1}:\n"
                            learned_patterns_text += f"  - Company names: {', '.join(pattern_data.get('company_names', []))}\n"
                            learned_patterns_text += f"  - Originator patterns: {', '.join(pattern_data.get('originator_patterns', []))}\n"
                            learned_patterns_text += f"  - Bank identifiers: {', '.join(pattern_data.get('bank_identifiers', []))}\n"
                            learned_patterns_text += f"  - Keywords: {', '.join(pattern_data.get('transaction_keywords', []))}\n"
                            learned_patterns_text += f"  - Payment method: {pattern_data.get('payment_method_type', 'N/A')}\n"

                        # Store in context for API response
                        context['has_learned_patterns'] = True
                except Exception as pattern_error:
                    print(f"WARNING: Failed to fetch learned patterns: {pattern_error}")

                # Build the prompt (this should be outside the try-except)
                prompt = f"""
                Analyze these unclassified transactions and determine which ones belong to the same business entity as the current transaction.

                CURRENT TRANSACTION:
                - Description: "{current_description}"
                - Type: {current_tx_type}
                - NEW Entity Classification: "{new_value}"
                - Source File: {current_source}

                {learned_patterns_text}

                UNCLASSIFIED CANDIDATE TRANSACTIONS:
                {chr(10).join(candidate_descriptions)}

                MATCHING INSTRUCTIONS:
                1. Use the learned patterns above as your PRIMARY matching criteria
                2. Look for transactions that match the company names, originator patterns, bank identifiers, or payment methods from the learned patterns
                3. If no patterns are learned yet, use intelligent matching based on:
                   - Same company/business name (including abbreviations and variations)
                   - Same payment processor/originator ("ORIG CO NAME", "B/O", "IND NAME")
                   - Same bank/financial institution
                   - Consistent business activity patterns
                4. Be SPECIFIC with payment processors - "PAYPAL ABC COMPANY" is different from "PAYPAL XYZ COMPANY"
                5. Be conservative: When in doubt, don't match - false negatives are better than false positives

                Response format: Just the numbers separated by commas (e.g., "1, 3, 7") or "none" if no transactions match.
                """
            elif field_type == 'similar_accounting':
                # Get current transaction type and direction for context
                current_tx_type = context.get('type', '')
                current_amount = float(context.get('amount', 0))
                current_direction = "DEBIT/Expense" if current_amount < 0 else "CREDIT/Revenue" if current_amount > 0 else "Zero"
                current_source = context.get('source_file', '')

                prompt = f"""
                Analyze these transactions and determine which ones should have the same accounting category as the current transaction.

                CURRENT TRANSACTION:
                - Description: "{current_description}"
                - Type: {current_tx_type}
                - Direction: {current_direction}
                - Amount: ${current_amount}
                - NEW Accounting Category: "{new_value}"
                - Entity: {current_entity}
                - Source File: {current_source}

                CANDIDATE TRANSACTIONS FROM SAME ENTITY:
                {chr(10).join(candidate_descriptions)}

                MATCHING CRITERIA - Consider these factors:
                1. **Transaction Purpose**: What is the transaction for? (hosting, trading income, bank fees, power bills, etc.)
                2. **Transaction Flow**: DEBIT (expense/outgoing) vs CREDIT (revenue/incoming) - must match current transaction
                3. **Transaction Type**: Wire transfer, ACH, credit card merchant, etc.
                4. **Business Function**: Same business activity or cost center
                5. **Recategorization**: If a transaction has a DIFFERENT category but appears to be the SAME type as current, include it (it may be miscategorized)

                IMPORTANT RULES:
                - Expenses and revenues are NEVER the same category
                - A $15 bank fee and a $3000 wire transfer are DIFFERENT (fee vs transfer)
                - Two hosting payments from same provider ARE the same (even if different amounts)
                - Ignore amount - focus on transaction nature and purpose
                - Include transactions with wrong categories if they match the current transaction's purpose

                Response format: Just the numbers separated by commas (e.g., "1, 3, 7") or "none" if no transactions match.
                """
            else:
                prompt = f"""
                Analyze these transaction descriptions from the same entity/business unit and determine which ones should have the same cleaned description.

                Current transaction has been updated to: "{new_value}"
                Entity: {current_entity}

                Other transactions from the same entity:
                {chr(10).join(candidate_descriptions)}

                Respond with ONLY the transaction numbers (1, 2, 3, etc.) that appear to be the same type of transaction and should use the clean description "{new_value}".
                Look for transactions that seem to be from the same source/purpose, even if the descriptions are messy.

                Response format: Just the numbers separated by commas (e.g., "1, 3, 7") or "none" if no transactions are similar enough.
                """

            start_time = time.time()
            print(f"AI: Calling Claude API for similar descriptions analysis...")

            response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
            )

            elapsed_time = time.time() - start_time
            print(f"LOADING: Claude API response time: {elapsed_time:.2f} seconds")

            response_text = response.content[0].text.strip().lower()
            print(f"DEBUG: Claude response for similar entities: {response_text}")

            if response_text == "none" or not response_text:
                return []

            # Parse Claude's response to get selected transaction indices
            # Claude may respond in different formats:
            # 1. "1, 2, 3" (comma separated)
            # 2. "transaction 1\ntransaction 2" (line separated with "transaction" prefix)
            # 3. "1\n2\n3" (line separated numbers)
            # 4. "based on... 1, 3, 7... explanation" (mixed with explanatory text)
            try:
                selected_indices = []

                # First try: Extract all numbers from the response (handles all formats)
                import re
                numbers = re.findall(r'\b\d+\b', response_text)
                for num_str in numbers:
                    try:
                        num = int(num_str)
                        # Only include numbers that are valid transaction indices (1-based)
                        if 1 <= num <= len(candidate_txs):
                            selected_indices.append(num - 1)  # Convert to 0-based
                    except ValueError:
                        continue

                # Remove duplicates while preserving order
                seen = set()
                deduplicated_indices = []
                for idx in selected_indices:
                    if idx not in seen:
                        seen.add(idx)
                        deduplicated_indices.append(idx)
                selected_indices = deduplicated_indices

                selected_txs = [candidate_txs[i] for i in selected_indices if 0 <= i < len(candidate_txs)]

                # Return formatted transaction data
                result = []
                for tx in selected_txs:
                    try:
                        if is_postgresql and isinstance(tx, dict):
                            tx_id = tx.get('transaction_id', '')
                            date = tx.get('date', '')
                            desc = tx.get('description', '')
                            conf = tx.get('confidence', 'N/A')
                            amount = tx.get('amount', 0)
                            entity = tx.get('classified_entity', '')
                            acct_cat = tx.get('accounting_category', 'N/A')
                        else:
                            tx_id = tx[0] if len(tx) > 0 else ''
                            date = tx[1] if len(tx) > 1 else ''
                            desc = tx[2] if len(tx) > 2 else ''
                            conf = tx[3] if len(tx) > 3 else 'N/A'
                            # For entity suggestions: amount is at index 5
                            # For accounting suggestions: amount is at index 3
                            # For description suggestions: no amount field
                        if field_type == 'similar_entities':
                            entity = tx[4] if len(tx) > 4 else ''
                            amount = tx[5] if len(tx) > 5 else 0
                            acct_cat = 'N/A'
                        elif field_type == 'similar_accounting':
                            entity = current_entity
                            amount = tx[3] if len(tx) > 3 else 0
                            acct_cat = tx[4] if len(tx) > 4 else 'N/A'
                        else:
                            entity = current_entity
                            amount = 0
                            acct_cat = 'N/A'

                        result.append({
                            'transaction_id': tx_id,
                            'date': date,
                            'description': desc[:80] + "..." if len(desc) > 80 else desc,
                            'confidence': conf or 'N/A',
                            'amount': amount,
                            'classified_entity': entity,
                            'accounting_category': acct_cat
                        })
                    except Exception as e:
                        print(f"ERROR: Failed to format transaction: {e}")

                print(f"DEBUG: Returning {len(result)} similar transactions")
                return result

            except (ValueError, IndexError) as e:
                print(f"ERROR: Error parsing Claude response for similar descriptions: {e}")
                return []
        finally:
            conn.close()

    except Exception as e:
        import traceback
        print(f"ERROR: Error in Claude analysis of similar descriptions: {e}")
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        return []

def get_similar_descriptions_from_db(context: Dict) -> List[str]:
    """Find transactions with similar descriptions for bulk updates"""
    try:
        if not context:
            return []

        transaction_id = context.get('transaction_id')
        new_description = context.get('value', '')

        if not transaction_id or not new_description:
            return []

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'

        # Find the current transaction to get its original description
        cursor.execute(
            f"SELECT description, classified_entity FROM transactions WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}",
            (tenant_id, transaction_id)
        )
        current_tx = cursor.fetchone()

        if not current_tx:
            conn.close()
            return []

        if is_postgresql:
            original_description = current_tx['description']
            entity = current_tx['classified_entity']
        else:
            original_description = current_tx[0]
            entity = current_tx[1]

        # Find transactions with similar patterns - return full transaction data
        cursor.execute(f"""
            SELECT transaction_id, date, description, confidence
            FROM transactions
            WHERE transaction_id != {placeholder}
            AND (
                -- Same entity with similar description pattern
                (classified_entity = {placeholder} AND description LIKE {placeholder}) OR
                -- Contains similar keywords for CIBC/Toronto wire transfers
                (description LIKE '%CIBC%' AND {placeholder} LIKE '%CIBC%') OR
                (description LIKE '%TORONTO%' AND {placeholder} LIKE '%TORONTO%') OR
                (description LIKE '%WIRE%' AND {placeholder} LIKE '%WIRE%') OR
                (description LIKE '%FEDWIRE%' AND {placeholder} LIKE '%FEDWIRE%')
            )
            AND description != {placeholder}
            LIMIT 10
        """, (
            transaction_id,
            entity,
            f"%{original_description[:20]}%",
            original_description,
            original_description,
            original_description,
            original_description,
            new_description
        ))
        similar_txs = cursor.fetchall()

        conn.close()

        # Return full transaction data for the improved UI
        if is_postgresql:
            return [{
                'transaction_id': row['transaction_id'],
                'date': row['date'],
                'description': row['description'][:80] + "..." if len(row['description']) > 80 else row['description'],
                'confidence': row['confidence'] or 'N/A'
            } for row in similar_txs]
        else:
            return [{
                'transaction_id': row[0],
                'date': row[1],
                'description': row[2][:80] + "..." if len(row[2]) > 80 else row[2],
                'confidence': row[3] or 'N/A'
            } for row in similar_txs]

    except Exception as e:
        print(f"ERROR: Error finding similar descriptions: {e}")
        return []

def get_tenant_entities(tenant_id: str) -> List[Dict]:
    """Get all active business entities for a tenant"""
    try:
        entities = db_manager.execute_query("""
            SELECT id, name, description, entity_type
            FROM business_entities
            WHERE tenant_id = %s AND active = true
            ORDER BY name
        """, (tenant_id,), fetch_all=True)
        return entities or []
    except Exception as e:
        logging.error(f"Error getting tenant entities: {e}")
        return []


def get_tenant_business_context(tenant_id: str) -> Dict:
    """Get business context information for a tenant"""
    try:
        tenant = db_manager.execute_query("""
            SELECT company_name, description, industry, metadata
            FROM tenant_configuration
            WHERE tenant_id = %s
        """, (tenant_id,), fetch_one=True)

        if tenant:
            return {
                'company_name': tenant.get('company_name', ''),
                'description': tenant.get('description', ''),
                'industry': tenant.get('industry', 'general'),
                'metadata': tenant.get('metadata', {})
            }
        return {'industry': 'general'}
    except Exception as e:
        logging.error(f"Error getting tenant business context: {e}")
        return {'industry': 'general'}


def format_entities_for_prompt(entities: List[Dict]) -> str:
    """Format business entities into a readable prompt section"""
    if not entities:
        return "No business entities configured yet."

    entity_lines = []
    for entity in entities:
        entity_type = entity.get('entity_type', 'other').capitalize()
        description = entity.get('description', '')
        if description:
            entity_lines.append(f"- {entity['name']} ({entity_type}): {description}")
        else:
            entity_lines.append(f"- {entity['name']} ({entity_type})")

    return '\n            '.join(entity_lines)


def get_tenant_knowledge(tenant_id: str, knowledge_types: List[str] = None) -> List[Dict]:
    """
    Get AI-extracted knowledge for a tenant to improve classification

    Args:
        tenant_id: Tenant identifier
        knowledge_types: Optional filter for specific knowledge types
                        (vendor_info, transaction_pattern, business_rule, entity_relationship, general)

    Returns:
        List of knowledge entries
    """
    try:
        if knowledge_types:
            placeholders = ','.join(['%s'] * len(knowledge_types))
            query = f"""
                SELECT knowledge_type, title, content, structured_data, confidence_score
                FROM tenant_knowledge
                WHERE tenant_id = %s
                  AND is_active = true
                  AND knowledge_type IN ({placeholders})
                ORDER BY confidence_score DESC NULLS LAST, created_at DESC
                LIMIT 50
            """
            params = (tenant_id, *knowledge_types)
        else:
            query = """
                SELECT knowledge_type, title, content, structured_data, confidence_score
                FROM tenant_knowledge
                WHERE tenant_id = %s AND is_active = true
                ORDER BY confidence_score DESC NULLS LAST, created_at DESC
                LIMIT 50
            """
            params = (tenant_id,)

        knowledge = db_manager.execute_query(query, params, fetch_all=True)
        return knowledge or []
    except Exception as e:
        logging.error(f"Error getting tenant knowledge: {e}")
        return []


def format_knowledge_for_prompt(knowledge: List[Dict]) -> str:
    """Format tenant knowledge into a readable prompt section"""
    if not knowledge:
        return ""

    # Group knowledge by type
    grouped = {}
    for item in knowledge:
        k_type = item.get('knowledge_type', 'general')
        if k_type not in grouped:
            grouped[k_type] = []
        grouped[k_type].append(item)

    sections = []

    # Vendor information
    if 'vendor_info' in grouped:
        vendor_lines = []
        for item in grouped['vendor_info']:
            title = item.get('title', 'Vendor')
            content = item.get('content', '')
            vendor_lines.append(f"- {title}: {content}")
        if vendor_lines:
            sections.append(f"KNOWN VENDORS:\n            " + '\n            '.join(vendor_lines))

    # Transaction patterns
    if 'transaction_pattern' in grouped:
        pattern_lines = []
        for item in grouped['transaction_pattern']:
            content = item.get('content', '')
            pattern_lines.append(f"- {content}")
        if pattern_lines:
            sections.append(f"TRANSACTION PATTERNS:\n            " + '\n            '.join(pattern_lines))

    # Business rules
    if 'business_rule' in grouped:
        rule_lines = []
        for item in grouped['business_rule']:
            content = item.get('content', '')
            rule_lines.append(f"- {content}")
        if rule_lines:
            sections.append(f"BUSINESS RULES:\n            " + '\n            '.join(rule_lines))

    # Entity relationships
    if 'entity_relationship' in grouped:
        rel_lines = []
        for item in grouped['entity_relationship']:
            content = item.get('content', '')
            rel_lines.append(f"- {content}")
        if rel_lines:
            sections.append(f"ENTITY RELATIONSHIPS:\n            " + '\n            '.join(rel_lines))

    return '\n\n            '.join(sections) if sections else ""


def build_entity_classification_prompt(context: Dict, tenant_id: str = None) -> str:
    """
    Build dynamic entity classification prompt based on tenant configuration.

    Args:
        context: Transaction context dictionary
        tenant_id: Tenant identifier (defaults to current tenant)

    Returns:
        Formatted prompt string for Claude AI
    """
    if tenant_id is None:
        tenant_id = get_current_tenant_id()

    # Load tenant-specific entities and business context
    entities = get_tenant_entities(tenant_id)
    business_context = get_tenant_business_context(tenant_id)

    # Format entities for prompt
    entity_rules = format_entities_for_prompt(entities)

    # Load and format tenant knowledge for classification
    knowledge = get_tenant_knowledge(
        tenant_id,
        knowledge_types=['vendor_info', 'transaction_pattern', 'business_rule', 'entity_relationship']
    )
    knowledge_section = format_knowledge_for_prompt(knowledge)

    # Build industry-specific context hints
    industry = business_context.get('industry', 'general')
    industry_hints = {
        'crypto_trading': [
            "Crypto exchange patterns (Coinbase, Binance, Kraken, etc.)",
            "Wallet addresses and blockchain transactions",
            "Mining operations and validator rewards",
            "DeFi protocols and staking",
            "Gas fees and transaction costs"
        ],
        'e_commerce': [
            "Payment processor patterns (Stripe, PayPal, Square)",
            "Marketplace fees (Amazon, eBay, Shopify)",
            "Shipping and fulfillment costs",
            "Inventory and supplier payments",
            "Customer refunds and chargebacks"
        ],
        'saas': [
            "Cloud infrastructure (AWS, Google Cloud, Azure)",
            "SaaS tools and subscriptions",
            "API and service integrations",
            "Customer billing and subscriptions",
            "Development tools and platforms"
        ],
        'professional_services': [
            "Client billing and invoices",
            "Professional fees and consultants",
            "Office expenses and rent",
            "Insurance and licenses",
            "Marketing and client acquisition"
        ],
        'general': [
            "Bank descriptions often contain merchant/institution names",
            "ACH/WIRE patterns indicate specific business relationships",
            "Amount patterns may suggest recurring services vs one-time purchases"
        ]
    }

    context_clues = industry_hints.get(industry, industry_hints['general'])
    context_clues_str = '\n            - '.join(context_clues)

    # Build the prompt
    knowledge_prompt_section = ""
    if knowledge_section:
        knowledge_prompt_section = f"\n\n            BUSINESS KNOWLEDGE:\n            {knowledge_section}\n"

    prompt = f"""
            You are a financial analyst specializing in entity classification for {industry.replace('_', ' ')} businesses.

            TRANSACTION DETAILS:
            - Description: {context.get('description', '')}
            - Amount: ${context.get('amount', '')}
            - Source File: {context.get('source_file', '')}
            - Date: {context.get('date', '')}

            ENTITY CLASSIFICATION RULES:
            {entity_rules}{knowledge_prompt_section}
            CONTEXT CLUES:
            - {context_clues_str}

            Based on the transaction description and amount, suggest 3-5 most likely entities.
            Prioritize based on:
            1. Specific merchant/institution mentioned in BUSINESS KNOWLEDGE (highest priority)
            2. Transaction patterns from BUSINESS KNOWLEDGE
            3. Transaction type (ACH, WIRE, etc.)
            4. Industry-specific patterns
            5. Amount patterns

            Return only the entity names, one per line, ranked by confidence.
            """

    return prompt


def get_ai_powered_suggestions(field_type: str, current_value: str = "", context: Dict = None) -> List[str]:
    """Get AI-powered suggestions for field values"""
    global claude_client

    if not claude_client:
        return []

    try:
        print(f"DEBUG - get_ai_powered_suggestions called with field_type={field_type}")

        # Get current tenant ID for dynamic configuration
        tenant_id = get_current_tenant_id()

        # Define prompts for different field types
        prompts = {
            'accounting_category': f"""
            Based on this transaction context:
            - Current value: {current_value}
            - Description: {context.get('description', '')}
            - Amount: {context.get('amount', '')}
            - Entity: {context.get('classified_entity', '')}

            Suggest 3-5 appropriate accounting categories (like 'Office Supplies', 'Software Licenses', 'Professional Services', etc.).
            Return only the category names, one per line.
            """,

            'classified_entity': build_entity_classification_prompt(context, tenant_id),

            'justification': f"""
            Based on this transaction:
            - Description: {context.get('description', '')}
            - Amount: {context.get('amount', '')}
            - Entity: {context.get('classified_entity', '')}

            Suggest 2-3 brief business justifications for this expense (like 'Business operations', 'Infrastructure cost', etc.).
            Return only the justifications, one per line.
            """,

            'description': f"""
            Based on this transaction with technical details:
            - Current description: {context.get('description', '')}
            - Amount: {context.get('amount', '')}
            - Entity: {context.get('classified_entity', '')}

            Extract and suggest 3-5 clean merchant/provider/entity names from this transaction.
            Focus ONLY on WHO we are transacting with, not what type of transaction it is. Examples:
            - "Delta Prop Shop" (from technical payment codes mentioning Delta Prop Shop)
            - "Chase Bank" (from Chase-related transactions)
            - "M Merchant" (from merchant processing fees)
            - "Gateway Services" (from gateway payment processing)
            - "CIBC Toronto" (from international wire transfer details)

            Return only the merchant/provider names, one per line, maximum 30 characters each.
            """
        }

        # Special handling for similar_descriptions, similar_entities, similar_accounting, and similar_subcategory
        if field_type in ['similar_descriptions', 'similar_entities', 'similar_accounting', 'similar_subcategory']:
            #  NEW: Use TF-IDF system for similar_entities (more accurate and faster)
            if field_type == 'similar_entities':
                transaction_id = context.get('transaction_id')
                entity_name = context.get('value', '')  # The entity user is assigning
                tenant_id = get_current_tenant_id()

                if transaction_id and entity_name:
                    logging.info(f"[SIMILAR_ENTITIES] Using TF-IDF system for transaction {transaction_id}, entity '{entity_name}'")
                    similar_txs = get_similar_transactions_tfidf(
                        transaction_id=transaction_id,
                        entity_name=entity_name,
                        tenant_id=tenant_id,
                        max_results=50
                    )

                    # Convert to list of transaction IDs (for backward compatibility with UI)
                    return [tx['transaction_id'] for tx in similar_txs]
                else:
                    logging.warning(f"[SIMILAR_ENTITIES] Missing transaction_id or entity_name in context")
                    return []

            # For other types, fall back to old Claude-based system
            return get_claude_analyzed_similar_descriptions(context, claude_client)

        prompt = prompts.get(field_type, "")
        if not prompt:
            print(f"ERROR: No prompt found for field_type: {field_type}")
            return []

        print(f"SUCCESS: Found prompt for {field_type}, enhancing with learning...")
        # Enhance prompt with learned patterns
        enhanced_prompt = enhance_ai_prompt_with_learning(field_type, prompt, context)
        print(f"SUCCESS: Enhanced prompt created, calling Claude API...")

        print(f"AI: Calling Claude API for {field_type} suggestions...")
        start_time = time.time()

        response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=200,
            messages=[{"role": "user", "content": enhanced_prompt}]
        )

        elapsed_time = time.time() - start_time
        print(f"LOADING: Claude API response time: {elapsed_time:.2f} seconds")

        # Parse Claude response and filter out introduction/instruction text
        raw_lines = [line.strip() for line in response.content[0].text.strip().split('\n') if line.strip()]

        # Filter out lines that are clearly instructions or headers (containing "based on", "here are", etc.)
        ai_suggestions = []
        for line in raw_lines:
            lower_line = line.lower()
            # Skip lines that are instructions/headers
            if any(phrase in lower_line for phrase in ['here are', 'based on', 'provided transaction', 'clean merchant', 'provider', 'entity names']):
                continue
            # Skip lines that end with colon (likely headers)
            if line.endswith(':'):
                continue
            ai_suggestions.append(line)

        print(f"AI: Claude suggestions (filtered): {ai_suggestions}")

        # Get learned suggestions
        learned_suggestions = get_learned_suggestions(field_type, context)
        learned_values = [s['value'] for s in learned_suggestions]
        print(f"DATABASE: Learned suggestions: {learned_values}")

        # Combine suggestions, prioritizing Claude AI suggestions FIRST
        combined_suggestions = []
        for ai_suggestion in ai_suggestions:
            if ai_suggestion not in combined_suggestions:
                combined_suggestions.append(ai_suggestion)

        for learned in learned_values:
            if learned not in combined_suggestions:
                combined_suggestions.append(learned)

        print(f"SUCCESS: Final combined suggestions: {combined_suggestions[:5]}")
        return combined_suggestions[:5]  # Limit to 5 suggestions

    except Exception as e:
        print(f"ERROR: Error getting AI suggestions: {e}")
        return []

def enrich_transaction_with_invoice_context(transaction_id: str, invoice_data: Dict) -> bool:
    """
    Enrich transaction with AI-powered classification based on invoice context
    Called automatically after confirming an invoice-transaction match
    """
    global claude_client

    if not claude_client:
        print("WARNING: Claude client not available for transaction enrichment")
        return False

    try:
        tenant_id = get_current_tenant_id()
        from database import db_manager

        # Get current transaction data
        transaction = db_manager.execute_query("""
            SELECT transaction_id, description, amount, classified_entity, accounting_category, subcategory, justification
            FROM transactions
            WHERE tenant_id = %s AND transaction_id = %s
        """, (tenant_id, transaction_id), fetch_one=True)

        if not transaction:
            print(f"ERROR: Transaction {transaction_id} not found")
            return False

        # Create enrichment prompt
        prompt = f"""
You are a financial AI expert. A transaction has been matched with an invoice and needs enrichment.

INVOICE CONTEXT:
- Vendor: {invoice_data.get('vendor_name', 'N/A')}
- Customer: {invoice_data.get('customer_name', 'N/A')}
- Invoice Number: {invoice_data.get('invoice_number', 'N/A')}
- Amount: {invoice_data.get('total_amount', 'N/A')}
- Category: {invoice_data.get('category', 'N/A')}
- Business Unit: {invoice_data.get('business_unit', 'N/A')}

TRANSACTION DETAILS:
- Description: {transaction['description']}
- Amount: {transaction['amount']}
- Current Entity: {transaction.get('classified_entity', 'N/A')}

Based on this context, provide enriched classification:

1. Entity: Who is the main vendor/service provider (focus on vendor_name from invoice)
2. Primary Category: Main expense/revenue type (Technology, Professional Services, Office Supplies, etc.)
3. Sub Category: More specific classification within the primary category
4. Justification: Brief explanation including invoice reference

Respond ONLY in valid JSON format:
{{"entity": "", "primary_category": "", "sub_category": "", "justification": ""}}
"""

        print(f"AI: Enriching transaction {transaction_id} with invoice context...")

        response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse AI response
        ai_response = response.content[0].text.strip()
        print(f"AI Response: {ai_response}")

        # Extract JSON from response
        import json
        try:
            # Try to find JSON in the response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = ai_response[json_start:json_end]
                enrichment_data = json.loads(json_str)
            else:
                print("ERROR: No JSON found in AI response")
                return False
        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to parse AI response as JSON: {e}")
            return False

        # Update transaction with enriched data
        update_query = """
            UPDATE transactions
            SET
                classified_entity = %s,
                accounting_category = %s,
                subcategory = %s,
                justification = %s,
                confidence = 0.95
            WHERE tenant_id = %s AND transaction_id = %s
        """

        db_manager.execute_query(update_query, (
            enrichment_data.get('entity', ''),
            enrichment_data.get('primary_category', ''),
            enrichment_data.get('sub_category', ''),
            enrichment_data.get('justification', ''),
            tenant_id,
            transaction_id
        ))

        print(f"SUCCESS: Transaction {transaction_id} enriched with AI-powered classification")
        return True

    except Exception as e:
        print(f"ERROR: Failed to enrich transaction {transaction_id}: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

@app.route('/api/revenue/re-enrich-historical-matches', methods=['POST'])
def api_re_enrich_historical_matches():
    """
    Re-analyze historical matched transactions and update classifications based on justification content
    """
    global claude_client

    if not claude_client:
        return jsonify({
            'success': False,
            'error': 'Claude API client not available'
        }), 503

    try:
        from database import db_manager
        tenant_id = get_current_tenant_id()

        # Get all matched transactions that have justifications with "invoice" or "expense" keywords
        matched_transactions = db_manager.execute_query("""
            SELECT transaction_id, classified_entity, accounting_category, subcategory,
                   justification, description, amount, invoice_id
            FROM transactions
            WHERE tenant_id = %s
            AND invoice_id IS NOT NULL
            AND invoice_id != ''
            AND justification IS NOT NULL
            AND justification != ''
            AND (justification ILIKE '%invoice%' OR justification ILIKE '%expense%' OR justification ILIKE '%technology%')
        """, (tenant_id,), fetch_all=True)

        if not matched_transactions:
            return jsonify({
                'success': True,
                'message': 'No historical matched transactions found to re-enrich',
                'processed': 0
            })

        print(f"Found {len(matched_transactions)} historical matched transactions to re-analyze")
        processed_count = 0
        updated_count = 0

        for transaction in matched_transactions:
            try:
                # Get transaction fields safely
                transaction_id = transaction['transaction_id'] if isinstance(transaction, dict) else transaction[0]
                classified_entity = transaction['classified_entity'] if isinstance(transaction, dict) else transaction[1]
                accounting_category = transaction['accounting_category'] if isinstance(transaction, dict) else transaction[2]
                subcategory = transaction['subcategory'] if isinstance(transaction, dict) else transaction[3]
                justification = transaction['justification'] if isinstance(transaction, dict) else transaction[4]
                description = transaction['description'] if isinstance(transaction, dict) else transaction[5]
                amount = transaction['amount'] if isinstance(transaction, dict) else transaction[6]

                # Create re-enrichment prompt based on existing justification
                prompt = f"""
You are a financial AI expert. Re-analyze this transaction that was previously matched to an invoice.

EXISTING JUSTIFICATION: {justification}

TRANSACTION DETAILS:
- Description: {description}
- Amount: {amount}
- Current Entity: {classified_entity or 'N/A'}
- Current Category: {accounting_category or 'N/A'}
- Current Subcategory: {subcategory or 'N/A'}

Based on the existing justification and transaction details, provide corrected classification:

1. Entity: Main vendor/service provider
2. Primary Category: Main expense/revenue type (Technology Expenses, Professional Services, Revenue, etc.)
3. Sub Category: Specific classification within the primary category
4. Justification: Keep existing justification (don't change)

Respond ONLY in valid JSON format:
{{"entity": "", "primary_category": "", "sub_category": "", "justification": "{justification}"}}
"""

                response = claude_client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )

                ai_response = response.content[0].text.strip()

                # Parse JSON response
                import json
                try:
                    json_start = ai_response.find('{')
                    json_end = ai_response.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        json_str = ai_response[json_start:json_end]
                        enrichment_data = json.loads(json_str)
                    else:
                        print(f"SKIP: No JSON found in AI response for {transaction_id}")
                        continue
                except json.JSONDecodeError as e:
                    print(f"SKIP: Failed to parse AI response for {transaction_id}: {e}")
                    continue

                # Check if classifications need to be updated
                new_entity = enrichment_data.get('entity', '').strip()
                new_category = enrichment_data.get('primary_category', '').strip()
                new_subcategory = enrichment_data.get('sub_category', '').strip()

                # Handle both dict and tuple formats
                current_entity = transaction['classified_entity'] if isinstance(transaction, dict) else transaction[1]
                current_category = transaction['accounting_category'] if isinstance(transaction, dict) else transaction[2]
                current_subcategory = transaction['subcategory'] if isinstance(transaction, dict) else transaction[3]

                needs_update = (
                    new_entity != (current_entity or '') or
                    new_category != (current_category or '') or
                    new_subcategory != (current_subcategory or '')
                )

                if needs_update and new_entity and new_category:
                    # Update the transaction
                    update_query = """
                        UPDATE transactions
                        SET
                            classified_entity = %s,
                            accounting_category = %s,
                            subcategory = %s,
                            confidence = 0.95
                        WHERE tenant_id = %s AND transaction_id = %s
                    """

                    db_manager.execute_query(update_query, (
                        new_entity,
                        new_category,
                        new_subcategory,
                        tenant_id,
                        transaction_id
                    ))

                    print(f"UPDATED: {transaction_id} -> {new_category}/{new_subcategory}")
                    updated_count += 1
                else:
                    print(f"NO UPDATE NEEDED: {transaction_id}")

                processed_count += 1

            except Exception as e:
                print(f"ERROR processing transaction {transaction_id}: {e}")
                continue

        return jsonify({
            'success': True,
            'message': f'Historical re-enrichment completed',
            'processed': processed_count,
            'updated': updated_count,
            'total_found': len(matched_transactions)
        })

    except Exception as e:
        logger.error(f"Error in historical re-enrichment: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def sync_csv_to_database(csv_filename=None):
    """Sync classified CSV files to SQLite database"""
    # Get current tenant_id for multi-tenant isolation
    tenant_id = get_current_tenant_id()
    print(f" Syncing to database for tenant: {tenant_id}")
    print(f" DEBUG: Starting sync_csv_to_database for {csv_filename}")
    try:
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        print(f" DEBUG: Parent directory: {parent_dir}")

        if csv_filename:
            # Sync specific classified file
            csv_path = os.path.join(parent_dir, 'classified_transactions', f'classified_{csv_filename}')
            print(f" DEBUG: Looking for classified file: {csv_path}")
        else:
            # Try to sync MASTER_TRANSACTIONS.csv if it exists
            csv_path = os.path.join(parent_dir, 'MASTER_TRANSACTIONS.csv')
            print(f" DEBUG: Looking for MASTER_TRANSACTIONS.csv: {csv_path}")

        # Check if classified_transactions directory exists
        classified_dir = os.path.join(parent_dir, 'classified_transactions')
        print(f" DEBUG: Classified directory exists: {os.path.exists(classified_dir)}")
        if os.path.exists(classified_dir):
            files_in_dir = os.listdir(classified_dir)
            print(f" DEBUG: Files in classified_transactions: {files_in_dir}")

        if not os.path.exists(csv_path):
            print(f"WARNING: CSV file not found for sync: {csv_path}")

            # Try alternative paths and files - ONLY classified files
            alternative_paths = [
                os.path.join(parent_dir, f'classified_{csv_filename}'),  # Root directory
                os.path.join(parent_dir, 'web_ui', 'classified_transactions', f'classified_{csv_filename}'),  # web_ui subfolder
            ] if csv_filename else []

            for alt_path in alternative_paths:
                print(f" DEBUG: Trying alternative path: {alt_path}")
                if os.path.exists(alt_path):
                    csv_path = alt_path
                    print(f" DEBUG: Found file at alternative path: {alt_path}")
                    break
            else:
                print(f" DEBUG: No classified file found - skipping sync")
                print(f" The file needs to be processed by main.py first to create a classified file")
                return False

        # Read the CSV file
        df = pd.read_csv(csv_path)

        # Validate that this is a classified file with required database columns
        # Make column check case-insensitive
        df_columns_lower = [col.lower() for col in df.columns]
        required_columns = ['date', 'description', 'amount']
        missing_columns = [col for col in required_columns if col.lower() not in df_columns_lower]

        if missing_columns:
            print(f" ERROR: CSV file is missing required columns: {missing_columns}")
            print(f" This appears to be a raw CSV file, not a classified one")
            print(f" Available columns: {list(df.columns)}")
            return False

        # Standardize column names to lowercase for database compatibility
        column_mapping = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in required_columns:
                column_mapping[col] = col_lower
        df = df.rename(columns=column_mapping)

        print(f"UPDATING: Syncing {len(df)} transactions to database...")

        # Connect to database using db_manager
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        # Detect database type for compatible syntax
        is_postgresql = hasattr(cursor, 'mogrify')  # PostgreSQL-specific method
        placeholder = '%s' if is_postgresql else '?'

        # SMART RE-UPLOAD: DO NOT delete existing data
        # Instead, we'll use UPSERT logic to merge/enrich existing records
        # Track statistics
        new_count = 0
        enriched_count = 0
        skipped_count = 0

        print(f" SMART RE-UPLOAD MODE: Will merge/enrich existing transactions")

        # Insert all transactions
        for _, row in df.iterrows():
            # Create transaction_id if not exists
            transaction_id = row.get('transaction_id', '')
            if not transaction_id:
                # Generate transaction_id from date + description + amount
                identifier = f"{row.get('date', '')}{row.get('description', '')}{row.get('amount', '')}"
                transaction_id = hashlib.md5(identifier.encode()).hexdigest()[:12]

            # Convert pandas types to Python types for SQLite
            # Handle both MASTER_TRANSACTIONS.csv and classified CSV column names

            # Extract date and normalize to YYYY-MM-DD format
            date_value = str(row.get('Date', row.get('date', '')))
            original_date = date_value  # Keep for debugging
            if 'T' in date_value:
                date_value = date_value.split('T')[0]
            elif ' ' in date_value:
                date_value = date_value.split(' ')[0]

            # Debug first row
            if _ == 0:
                print(f" DEBUG DATE NORMALIZATION: Original='{original_date}' -> Normalized='{date_value}'")

            data = {
                'transaction_id': transaction_id,
                'date': date_value,
                'description': str(row.get('Description', row.get('description', ''))),
                'amount': float(row.get('Amount', row.get('amount', 0))),
                'currency': str(row.get('Currency', row.get('currency', 'USD'))),
                'usd_equivalent': float(row.get('Amount_USD', row.get('USD_Equivalent', row.get('usd_equivalent', row.get('Amount', row.get('amount', 0)))))),
                'classified_entity': str(row.get('classified_entity', '')),
                'accounting_category': str(row.get('accounting_category', '')),
                'subcategory': str(row.get('subcategory', '')),
                'justification': str(row.get('Justification', row.get('justification', ''))),
                'confidence': float(row.get('confidence', 0)),
                'classification_reason': str(row.get('classification_reason', '')),
                'origin': str(row.get('Origin', row.get('origin', ''))),
                'destination': str(row.get('Destination', row.get('destination', ''))),
                # Prioritize Reference (blockchain hash/TxID) over Identifier for crypto transactions
                'identifier': str(row.get('Reference', row.get('Identifier', row.get('identifier', '')))),
                'source_file': str(row.get('source_file', '')),
                'crypto_amount': float(row.get('Crypto_Amount', 0)) if pd.notna(row.get('Crypto_Amount')) else None,
                'conversion_note': str(row.get('Conversion_Note', '')) if pd.notna(row.get('Conversion_Note')) else None
            }

            # SMART ENRICHMENT: Insert transaction or enrich existing one
            if is_postgresql:
                # First, check if transaction exists
                cursor.execute(
                    "SELECT transaction_id, confidence, origin, destination, classified_entity, accounting_category, subcategory, justification FROM transactions WHERE tenant_id = %s AND transaction_id = %s",
                    (tenant_id, data['transaction_id'])
                )
                existing = cursor.fetchone()

                if existing:
                    # Transaction exists - ENRICH mode
                    # Convert tuple to dict for easier access
                    existing_dict = {
                        'transaction_id': existing[0],
                        'confidence': existing[1],
                        'origin': existing[2],
                        'destination': existing[3],
                        'classified_entity': existing[4],
                        'accounting_category': existing[5],
                        'subcategory': existing[6],
                        'justification': existing[7]
                    }

                    # Determine if this is user-edited data (confidence >= 0.90 means likely user-edited or AI-confident)
                    is_user_edited = existing_dict.get('confidence', 0) >= 0.90

                    # ENRICHMENT RULES:
                    # 1. ALWAYS update if current value is empty/unknown
                    # 2. NEVER overwrite user-edited data (confidence >= 90%)
                    # 3. DO update if new data has higher confidence
                    # 4. ALWAYS add missing origin/destination data

                    cursor.execute("""
                        UPDATE transactions SET
                            -- Always update basic fields (these shouldn't change but keep in sync)
                            date = %s,
                            description = %s,
                            amount = %s,
                            currency = %s,
                            usd_equivalent = %s,

                            -- Enrich origin ONLY if currently empty/unknown
                            origin = CASE
                                WHEN (origin IS NULL OR origin = '' OR origin = 'Unknown') AND %s IS NOT NULL AND %s != '' AND %s != 'Unknown'
                                THEN %s
                                ELSE origin
                            END,

                            -- Enrich destination ONLY if currently empty/unknown
                            destination = CASE
                                WHEN (destination IS NULL OR destination = '' OR destination = 'Unknown') AND %s IS NOT NULL AND %s != '' AND %s != 'Unknown'
                                THEN %s
                                ELSE destination
                            END,

                            -- Enrich classified_entity ONLY if empty or if new confidence is higher
                            classified_entity = CASE
                                WHEN (classified_entity IS NULL OR classified_entity = '' OR classified_entity = 'Unclassified')
                                THEN %s
                                WHEN confidence < %s
                                THEN %s
                                ELSE classified_entity
                            END,

                            -- Enrich accounting_category ONLY if empty or if new confidence is higher
                            accounting_category = CASE
                                WHEN (accounting_category IS NULL OR accounting_category = '' OR accounting_category = 'N/A')
                                THEN %s
                                WHEN confidence < %s
                                THEN %s
                                ELSE accounting_category
                            END,

                            -- Enrich subcategory ONLY if empty or if new confidence is higher
                            subcategory = CASE
                                WHEN (subcategory IS NULL OR subcategory = '' OR subcategory = 'N/A')
                                THEN %s
                                WHEN confidence < %s
                                THEN %s
                                ELSE subcategory
                            END,

                            -- Enrich justification ONLY if currently empty/unknown
                            justification = CASE
                                WHEN (justification IS NULL OR justification = '' OR justification = 'Unknown')
                                THEN %s
                                ELSE justification
                            END,

                            -- Update confidence ONLY if new confidence is higher
                            confidence = CASE
                                WHEN %s > confidence
                                THEN %s
                                ELSE confidence
                            END,

                            -- Always update these metadata fields
                            classification_reason = %s,
                            identifier = %s,
                            source_file = %s,
                            crypto_amount = %s,
                            conversion_note = %s
                        WHERE transaction_id = %s
                    """, (
                        # Basic fields (always update)
                        data['date'], data['description'], data['amount'], data['currency'], data['usd_equivalent'],
                        # Origin enrichment (4 placeholders)
                        data['origin'], data['origin'], data['origin'], data['origin'],
                        # Destination enrichment (4 placeholders)
                        data['destination'], data['destination'], data['destination'], data['destination'],
                        # Entity enrichment (3 placeholders)
                        data['classified_entity'], data['confidence'], data['classified_entity'],
                        # Accounting category enrichment (3 placeholders)
                        data['accounting_category'], data['confidence'], data['accounting_category'],
                        # Subcategory enrichment (3 placeholders)
                        data['subcategory'], data['confidence'], data['subcategory'],
                        # Justification enrichment (1 placeholder)
                        data['justification'],
                        # Confidence update (2 placeholders)
                        data['confidence'], data['confidence'],
                        # Metadata fields
                        data['classification_reason'], data['identifier'], data['source_file'],
                        data['crypto_amount'], data['conversion_note'],
                        # WHERE clause
                        data['transaction_id']
                    ))
                    enriched_count += 1
                    print(f" ENRICHED: {data['transaction_id'][:8]}... - {data['description'][:50]}")
                else:
                    # Transaction doesn't exist - INSERT new
                    cursor.execute("""
                        INSERT INTO transactions (
                            transaction_id, tenant_id, date, description, amount, currency, usd_equivalent,
                            classified_entity, accounting_category, subcategory, justification,
                            confidence, classification_reason, origin, destination, identifier,
                            source_file, crypto_amount, conversion_note
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        data['transaction_id'], tenant_id, data['date'], data['description'],
                        data['amount'], data['currency'], data['usd_equivalent'],
                        data['classified_entity'], data['accounting_category'], data['subcategory'],
                        data['justification'], data['confidence'], data['classification_reason'],
                        data['origin'], data['destination'], data['identifier'], data['source_file'],
                        data['crypto_amount'], data['conversion_note']
                    ))
                    new_count += 1
                    print(f" NEW: {data['transaction_id'][:8]}... - {data['description'][:50]}")
            else:
                # SQLite - use simple INSERT OR REPLACE for now
                cursor.execute("""
                    INSERT OR REPLACE INTO transactions (
                        transaction_id, tenant_id, date, description, amount, currency, usd_equivalent,
                        classified_entity, accounting_category, subcategory, justification,
                        confidence, classification_reason, origin, destination, identifier,
                        source_file, crypto_amount, conversion_note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['transaction_id'], tenant_id, data['date'], data['description'],
                    data['amount'], data['currency'], data['usd_equivalent'],
                    data['classified_entity'], data['accounting_category'], data['subcategory'],
                    data['justification'], data['confidence'], data['classification_reason'],
                    data['origin'], data['destination'], data['identifier'], data['source_file'],
                    data['crypto_amount'], data['conversion_note']
                ))

        conn.commit()
        conn.close()

        # Print enrichment statistics
        print(f"")
        print(f" SUCCESS: Smart Re-Upload Complete!")
        print(f" Statistics:")
        print(f"   • Total processed: {len(df)}")
        print(f"   • New transactions: {new_count}")
        print(f"   • Enriched existing: {enriched_count}")
        print(f"   • Skipped (unchanged): {skipped_count}")
        print(f"")

        return True

    except Exception as e:
        print(f"ERROR: Error syncing CSV to database: {e}")
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        return False

@app.route('/')
def homepage():
    """Business overview homepage"""
    try:
        cache_buster = str(random.randint(1000, 9999))
        return render_template('business_overview.html', cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading homepage: {str(e)}", 500

@app.route('/health')
def health_check():
    """Health check endpoint that returns application and database status"""
    try:
        db_type = os.getenv('DB_TYPE', 'sqlite').lower()

        # Basic application health
        health_response = {
            "status": "healthy",
            "application": "running",
            "db_type_env": db_type,
            "postgresql_available": POSTGRESQL_AVAILABLE,
            "timestamp": datetime.now().isoformat(),
            "version": "2.0"
        }

        # Only check database if specifically requested to avoid startup delays
        check_db = request.args.get('check_db', '').lower() == 'true'
        if check_db:
            try:
                from database import db_manager
                db_health = db_manager.health_check()
                health_response["database"] = db_health
            except Exception as db_error:
                # Database unavailable but application is still healthy
                health_response["database"] = {
                    "status": "unavailable",
                    "error": str(db_error),
                    "note": "Application can run without database for basic operations"
                }
        else:
            health_response["database"] = "skipped_for_fast_startup"

        return jsonify(health_response), 200

    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/debug')
def debug_db():
    """Debug endpoint to show database connection details"""
    try:
        debug_info = {
            "environment_vars": {
                "DB_TYPE": os.getenv('DB_TYPE', 'not_set'),
                "DB_HOST": os.getenv('DB_HOST', 'not_set'),
                "DB_PORT": os.getenv('DB_PORT', 'not_set'),
                "DB_NAME": os.getenv('DB_NAME', 'not_set'),
                "DB_USER": os.getenv('DB_USER', 'not_set'),
                "DB_PASSWORD": "***" if os.getenv('DB_PASSWORD') else "not_set",
                "DB_SOCKET_PATH": os.getenv('DB_SOCKET_PATH', 'not_set'),
                "FLASK_ENV": os.getenv('FLASK_ENV', 'not_set'),
            },
            "postgresql_available": POSTGRESQL_AVAILABLE,
            "connection_attempt": None
        }

        # Try PostgreSQL connection manually
        if POSTGRESQL_AVAILABLE and os.getenv('DB_TYPE', '').lower() == 'postgresql':
            try:
                socket_path = os.getenv('DB_SOCKET_PATH')
                if socket_path:
                    conn = psycopg2.connect(
                        host=socket_path,
                        database=os.getenv('DB_NAME', 'delta_cfo'),
                        user=os.getenv('DB_USER', 'delta_user'),
                        password=os.getenv('DB_PASSWORD')
                    )
                    debug_info["connection_attempt"] = "success_socket"
                else:
                    conn = psycopg2.connect(
                        host=os.getenv('DB_HOST', '34.39.143.82'),
                        port=os.getenv('DB_PORT', '5432'),
                        database=os.getenv('DB_NAME', 'delta_cfo'),
                        user=os.getenv('DB_USER', 'delta_user'),
                        password=os.getenv('DB_PASSWORD')
                    )
                    debug_info["connection_attempt"] = "success_tcp"
                conn.close()
            except Exception as e:
                debug_info["connection_attempt"] = f"failed: {str(e)}"

        return jsonify(debug_info), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/old-homepage')
def old_homepage():
    """Old homepage with platform overview"""
    try:
        stats = get_dashboard_stats()
        cache_buster = str(random.randint(1000, 9999))
        return render_template('homepage.html', stats=stats, cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading homepage: {str(e)}", 500

@app.route('/dashboard')
def dashboard():
    """Main dashboard page"""
    try:
        stats = get_dashboard_stats()
        cache_buster = str(random.randint(1000, 9999))
        return render_template('dashboard_advanced.html', stats=stats, cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500

@app.route('/revenue')
def revenue():
    """Revenue Recognition dashboard page"""
    try:
        stats = get_dashboard_stats()
        cache_buster = str(random.randint(1000, 9999))
        return render_template('revenue.html', stats=stats, cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading revenue dashboard: {str(e)}", 500

@app.route('/expenses')
def expenses():
    """Expense Matching dashboard page"""
    try:
        stats = get_dashboard_stats()
        cache_buster = str(random.randint(1000, 9999))
        return render_template('expenses.html', stats=stats, cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading expenses dashboard: {str(e)}", 500

@app.route('/reports')
def reports():
    """Financial Reports Dashboard with charts and analytics"""
    try:
        # Fixed branding for Delta CFO Agent product (not tenant-specific)
        company_name = "Delta CFO Agent"
        company_description = "Delta's proprietary self improving AI CFO Agent"

        cache_buster = str(random.randint(1000, 9999))
        return render_template('cfo_dashboard.html',
                             cache_buster=cache_buster,
                             company_name=company_name,
                             company_description=company_description)
    except Exception as e:
        return f"Error loading CFO dashboard: {str(e)}", 500

# DEPRECATED: This route is now handled by auth_routes.py blueprint
# @app.route('/api/auth/switch-tenant/<tenant_id>', methods=['POST'])
# def api_switch_tenant(tenant_id):
#     """API endpoint to switch active tenant for current user session"""
#     # This function has been moved to api/auth_routes.py with proper authentication
#     # and dynamic tenant validation from the database

# Keeping the old function commented for reference during migration
def _deprecated_api_switch_tenant(tenant_id):
    """DEPRECATED - Use auth_routes.py instead"""
    try:
        print(f"[TENANT SWITCH] Request to switch to tenant: {tenant_id}", flush=True)

        # TODO: Add validation that user has access to this tenant
        # For now, allow switching to 'delta' or 'nascimento'
        valid_tenants = ['delta', 'nascimento']

        if tenant_id not in valid_tenants:
            print(f"[TENANT SWITCH] Invalid tenant_id: {tenant_id}", flush=True)
            return jsonify({
                'success': False,
                'message': f'Invalid tenant ID. Valid tenants: {", ".join(valid_tenants)}'
            }), 400

        # Set tenant in BOTH session contexts:
        # 1. tenant_context.py uses session['tenant_id'] (string)
        set_tenant_id(tenant_id)

        # 2. auth_middleware.py uses session['current_tenant_id'] (same string for now)
        session['current_tenant_id'] = tenant_id

        print(f"[TENANT SWITCH] Successfully switched to tenant: {tenant_id}", flush=True)
        print(f"[TENANT SWITCH] session['tenant_id'] = {session.get('tenant_id')}", flush=True)
        print(f"[TENANT SWITCH] session['current_tenant_id'] = {session.get('current_tenant_id')}", flush=True)

        return jsonify({
            'success': True,
            'tenant_id': tenant_id,
            'message': f'Successfully switched to tenant: {tenant_id}'
        })

    except Exception as e:
        print(f"[TENANT SWITCH] Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error switching tenant: {str(e)}'
        }), 500

@app.route('/api/transactions')
def api_transactions():
    """API endpoint to get filtered transactions with pagination"""
    try:
        # Get filter parameters
        filters = {
            'entity': request.args.get('entity'),
            'transaction_type': request.args.get('transaction_type'),
            'source_file': request.args.get('source_file'),
            'needs_review': request.args.get('needs_review'),
            'min_amount': request.args.get('min_amount'),
            'max_amount': request.args.get('max_amount'),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'keyword': request.args.get('keyword'),
            'show_archived': request.args.get('show_archived'),
            'is_internal': request.args.get('is_internal')
        }

        # Remove None values
        filters = {k: v for k, v in filters.items() if v}

        # Pagination parameters with maximum limit to prevent performance issues
        MAX_PER_PAGE = 500  # Maximum reasonable limit for client-side rendering
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), MAX_PER_PAGE)

        print(f"API: About to call load_transactions_from_db with filters={filters}")
        transactions, total_count = load_transactions_from_db(filters, page, per_page)
        print(f"API: Got result - transactions count={len(transactions)}, total_count={total_count}")

        return jsonify({
            'transactions': transactions,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/export')
def api_transactions_export():
    """Export all transactions matching filters to CSV"""
    try:
        import csv
        from io import StringIO

        # Get filter parameters (same as api_transactions)
        filters = {
            'entity': request.args.get('entity'),
            'transaction_type': request.args.get('transaction_type'),
            'source_file': request.args.get('source_file'),
            'needs_review': request.args.get('needs_review'),
            'min_amount': request.args.get('min_amount'),
            'max_amount': request.args.get('max_amount'),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'keyword': request.args.get('keyword'),
            'show_archived': request.args.get('show_archived'),
            'is_internal': request.args.get('is_internal')
        }

        # Remove None values
        filters = {k: v for k, v in filters.items() if v}

        # Load ALL transactions matching filters (no pagination)
        # Use a reasonable maximum (e.g., 50,000)
        MAX_EXPORT_ROWS = 50000
        transactions, total_count = load_transactions_from_db(filters, page=1, per_page=MAX_EXPORT_ROWS)

        # Create CSV in memory
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'transaction_id', 'date', 'description', 'amount', 'currency',
            'origin', 'destination', 'classified_entity', 'accounting_category',
            'subcategory', 'justification', 'confidence', 'source_file'
        ])

        writer.writeheader()
        for tx in transactions:
            writer.writerow({
                'transaction_id': tx.get('transaction_id', ''),
                'date': tx.get('date', ''),
                'description': tx.get('description', ''),
                'amount': tx.get('amount', ''),
                'currency': tx.get('currency', 'USD'),
                'origin': tx.get('origin', ''),
                'destination': tx.get('destination', ''),
                'classified_entity': tx.get('classified_entity', ''),
                'accounting_category': tx.get('accounting_category', ''),
                'subcategory': tx.get('subcategory', ''),
                'justification': tx.get('justification', ''),
                'confidence': tx.get('confidence', ''),
                'source_file': tx.get('source_file', '')
            })

        # Return CSV as download
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=transactions_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

        return response

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """API endpoint to get dashboard statistics"""
    try:
        stats = get_dashboard_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test_transactions')
def api_test_transactions():
    """Simple test endpoint to debug transaction retrieval"""
    try:
        tenant_id = get_current_tenant_id()
        from database import db_manager

        # Direct database query like get_dashboard_stats
        with db_manager.get_connection() as conn:
            if db_manager.db_type == 'postgresql':
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cursor = conn.cursor()

            is_postgresql = db_manager.db_type == 'postgresql'
            placeholder = "%s" if is_postgresql else "?"

            # Test 1: Total count
            cursor.execute(f"SELECT COUNT(*) as total FROM transactions WHERE tenant_id = {placeholder}", (tenant_id,))
            result = cursor.fetchone()
            total_all = result['total'] if is_postgresql else result[0]

            # Test 2: Non-archived count
            cursor.execute(f"SELECT COUNT(*) as total FROM transactions WHERE tenant_id = {placeholder} AND (archived = FALSE OR archived IS NULL)", (tenant_id,))
            result = cursor.fetchone()
            total_unarchived = result['total'] if is_postgresql else result[0]

            # Test 3: Get first 3 transactions
            cursor.execute(f"SELECT transaction_id, date, description, amount, archived FROM transactions WHERE tenant_id = {placeholder} LIMIT 3", (tenant_id,))
            sample_transactions = cursor.fetchall()

            # Convert to list of dicts
            sample_list = []
            for row in sample_transactions:
                if is_postgresql:
                    sample_list.append(dict(row))
                else:
                    sample_list.append(dict(row))

            return jsonify({
                'total_all_transactions': total_all,
                'total_unarchived_transactions': total_unarchived,
                'sample_transactions': sample_list,
                'db_type': db_manager.db_type
            })

    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/debug/positive-transactions')
def api_debug_positive_transactions():
    """Debug endpoint to find positive (revenue) transactions"""
    try:
        tenant_id = get_current_tenant_id()
        from database import db_manager

        with db_manager.get_connection() as conn:
            if db_manager.db_type == 'postgresql':
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cursor = conn.cursor()

            is_postgresql = db_manager.db_type == 'postgresql'
            placeholder = "%s" if is_postgresql else "?"

            # Find positive transactions
            cursor.execute(f"""
                SELECT transaction_id, date, description, amount, classified_entity, currency
                FROM transactions
                WHERE tenant_id = {placeholder} AND amount > 0
                ORDER BY amount DESC
                LIMIT 10
            """, (tenant_id,))
            positive_transactions = cursor.fetchall()

            # Find transactions with highest absolute values (both positive and negative)
            cursor.execute(f"""
                SELECT transaction_id, date, description, amount, classified_entity, currency
                FROM transactions
                WHERE tenant_id = {placeholder}
                ORDER BY ABS(amount) DESC
                LIMIT 10
            """, (tenant_id,))
            highest_transactions = cursor.fetchall()

            # Count positive vs negative
            cursor.execute(f"SELECT COUNT(*) as count FROM transactions WHERE tenant_id = {placeholder} AND amount > 0", (tenant_id,))
            result = cursor.fetchone()
            positive_count = result['count'] if is_postgresql else result[0]

            cursor.execute(f"SELECT COUNT(*) as count FROM transactions WHERE tenant_id = {placeholder} AND amount < 0", (tenant_id,))
            result = cursor.fetchone()
            negative_count = result['count'] if is_postgresql else result[0]

            # Convert to list of dicts
            positive_list = []
            for row in positive_transactions:
                if is_postgresql:
                    positive_list.append(dict(row))
                else:
                    positive_list.append(dict(row))

            highest_list = []
            for row in highest_transactions:
                if is_postgresql:
                    highest_list.append(dict(row))
                else:
                    highest_list.append(dict(row))

            return jsonify({
                'positive_transactions': positive_list,
                'highest_value_transactions': highest_list,
                'stats': {
                    'positive_count': positive_count,
                    'negative_count': negative_count,
                    'total_count': positive_count + negative_count
                }
            })

    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/revenue/reset-all-matches', methods=['POST'])
def api_reset_all_matches():
    """Reset all invoice-transaction matches - remove all links"""
    try:
        tenant_id = get_current_tenant_id()
        from database import db_manager

        with db_manager.get_connection() as conn:
            if db_manager.db_type == 'postgresql':
                cursor = conn.cursor()
            else:
                cursor = conn.cursor()

            is_postgresql = db_manager.db_type == 'postgresql'
            placeholder = "%s" if is_postgresql else "?"

            # Count current matches
            cursor.execute(f"SELECT COUNT(*) FROM invoices WHERE tenant_id = {placeholder} AND linked_transaction_id IS NOT NULL", (tenant_id,))
            current_matches = cursor.fetchone()[0]

            # Remove all matches from invoices table
            cursor.execute(f"""
                UPDATE invoices
                SET linked_transaction_id = NULL,
                    match_confidence = NULL,
                    match_method = NULL
                WHERE tenant_id = {placeholder} AND linked_transaction_id IS NOT NULL
            """, (tenant_id,))

            # Clear invoice match log table if it exists
            try:
                cursor.execute("DELETE FROM invoice_match_log")
            except:
                pass  # Table might not exist

            conn.commit()

            return jsonify({
                'success': True,
                'message': f'Successfully reset {current_matches} matches',
                'matches_removed': current_matches
            })

    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/update_transaction', methods=['POST'])
def api_update_transaction():
    """API endpoint to update transaction fields"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        field = data.get('field')
        value = data.get('value')

        if not all([transaction_id, field]):
            return jsonify({'error': 'Missing required parameters'}), 400

        result = update_transaction_field(transaction_id, field, value)

        # update_transaction_field returns (success, updated_confidence) tuple
        if isinstance(result, tuple):
            success, updated_confidence = result
        else:
            success = result
            updated_confidence = None

        #  ISSUE #4: FEEDBACK LOOP - Detect if user accepted/rejected AI suggestion
        if success and field == 'classified_entity' and value and value != 'N/A':
            try:
                # Get current tenant_id for multi-tenant isolation
                tenant_id = get_current_tenant_id()

                # Get transaction details (description + AI suggestion)
                from database import db_manager
                conn = db_manager._get_postgresql_connection()
                cursor = conn.cursor()
                is_postgresql = hasattr(cursor, 'mogrify')
                placeholder = '%s' if is_postgresql else '?'

                cursor.execute(
                    f"SELECT description, suggested_entity FROM transactions WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}",
                    (tenant_id, transaction_id)
                )
                tx_row = cursor.fetchone()

                if tx_row:
                    description = tx_row.get('description', '') if isinstance(tx_row, dict) else tx_row[0]
                    suggested_entity = tx_row.get('suggested_entity', '') if isinstance(tx_row, dict) else tx_row[1]

                    #  REINFORCEMENT LEARNING: Check if user accepted or rejected AI suggestion
                    if suggested_entity and suggested_entity != 'N/A':
                        if suggested_entity == value:
                            # User ACCEPTED the AI suggestion - positive feedback
                            handle_classification_feedback(
                                transaction_id=transaction_id,
                                suggested_entity=suggested_entity,
                                actual_entity=value,
                                tenant_id=tenant_id,
                                feedback_type='accepted'
                            )
                            print(f" POSITIVE FEEDBACK: User accepted AI suggestion '{suggested_entity}'")
                        else:
                            # User REJECTED the AI suggestion - negative feedback
                            handle_classification_feedback(
                                transaction_id=transaction_id,
                                suggested_entity=suggested_entity,
                                actual_entity=value,
                                tenant_id=tenant_id,
                                feedback_type='rejected'
                            )
                            print(f" NEGATIVE FEEDBACK: User rejected '{suggested_entity}', chose '{value}' instead")

                    # Extract patterns for the actual chosen entity (regardless of whether it was suggested)
                    extract_entity_patterns_with_llm(transaction_id, value, description, claude_client)
                    print(f"INFO: Entity pattern extraction triggered for transaction {transaction_id}, entity: {value}")

                conn.close()

            except Exception as pattern_error:
                # Don't fail the update if pattern extraction fails
                print(f"WARNING: Pattern extraction failed but transaction update succeeded: {pattern_error}")

        if success:
            response_data = {
                'success': True,
                'message': 'Transaction updated successfully'
            }
            # Include updated confidence if it was calculated
            if updated_confidence is not None:
                response_data['updated_confidence'] = updated_confidence
            return jsonify(response_data)
        else:
            return jsonify({'error': 'Failed to update transaction'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_entity_bulk', methods=['POST'])
def api_update_entity_bulk():
    """API endpoint to update entity for multiple transactions"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])
        new_entity = data.get('new_entity')

        if not transaction_ids or not new_entity:
            return jsonify({'error': 'Missing required parameters'}), 400

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        # Update each transaction
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'
        updated_count = 0

        for transaction_id in transaction_ids:
            cursor.execute(
                f"UPDATE transactions SET classified_entity = {placeholder} WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}",
                (new_entity, tenant_id, transaction_id)
            )
            if cursor.rowcount > 0:
                updated_count += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} transactions',
            'updated_count': updated_count
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_category_bulk', methods=['POST'])
def api_update_category_bulk():
    """API endpoint to update accounting category for multiple transactions"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])
        new_category = data.get('new_category')

        if not transaction_ids or not new_category:
            return jsonify({'error': 'Missing required parameters'}), 400

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        # Update each transaction
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'
        updated_count = 0

        for transaction_id in transaction_ids:
            cursor.execute(
                f"UPDATE transactions SET accounting_category = {placeholder} WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}",
                (new_category, tenant_id, transaction_id)
            )
            if cursor.rowcount > 0:
                updated_count += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} transactions',
            'updated_count': updated_count
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_subcategory_bulk', methods=['POST'])
def api_update_subcategory_bulk():
    """API endpoint to update subcategory for multiple transactions"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])
        new_subcategory = data.get('new_subcategory')

        if not transaction_ids or not new_subcategory:
            return jsonify({'error': 'Missing required parameters'}), 400

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        # Update each transaction
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'
        updated_count = 0

        for transaction_id in transaction_ids:
            cursor.execute(
                f"UPDATE transactions SET subcategory = {placeholder} WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}",
                (new_subcategory, tenant_id, transaction_id)
            )
            if cursor.rowcount > 0:
                updated_count += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Updated {updated_count} transactions',
            'updated_count': updated_count
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/archive_transactions', methods=['POST'])
def api_archive_transactions():
    """API endpoint to archive multiple transactions"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])

        if not transaction_ids:
            return jsonify({'error': 'No transaction IDs provided'}), 400

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'
        archived_count = 0

        for transaction_id in transaction_ids:
            cursor.execute(
                f"UPDATE transactions SET archived = TRUE WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}",
                (tenant_id, transaction_id)
            )
            if cursor.rowcount > 0:
                archived_count += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Archived {archived_count} transactions',
            'archived_count': archived_count
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/unarchive_transactions', methods=['POST'])
def api_unarchive_transactions():
    """API endpoint to unarchive multiple transactions"""
    try:
        data = request.get_json()
        transaction_ids = data.get('transaction_ids', [])

        if not transaction_ids:
            return jsonify({'error': 'No transaction IDs provided'}), 400

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'
        unarchived_count = 0

        for transaction_id in transaction_ids:
            cursor.execute(
                f"UPDATE transactions SET archived = FALSE WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}",
                (tenant_id, transaction_id)
            )
            if cursor.rowcount > 0:
                unarchived_count += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': f'Unarchived {unarchived_count} transactions',
            'unarchived_count': unarchived_count
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===================================================================
# WALLET ADDRESS MANAGEMENT API ENDPOINTS
# ===================================================================

@app.route('/api/wallets', methods=['GET'])
def api_get_wallets():
    """Get all wallet addresses for the current tenant"""
    try:
        from database import db_manager

        # Hardcoded tenant for now (Delta)
        tenant_id = 'delta'

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT id, wallet_address, entity_name, purpose, wallet_type,
                       confidence_score, is_active, notes, created_at, updated_at
                FROM wallet_addresses
                WHERE tenant_id = %s AND is_active = TRUE
                ORDER BY created_at DESC
            """

            cursor.execute(query, (tenant_id,))

            wallets = []
            for row in cursor.fetchall():
                wallets.append({
                    'id': str(row[0]),
                    'wallet_address': row[1],
                    'entity_name': row[2],
                    'purpose': row[3],
                    'wallet_type': row[4],
                    'confidence_score': float(row[5]) if row[5] else 0.9,
                    'is_active': row[6],
                    'notes': row[7],
                    'created_at': row[8].isoformat() if row[8] else None,
                    'updated_at': row[9].isoformat() if row[9] else None
                })

            cursor.close()

        return jsonify({
            'success': True,
            'wallets': wallets,
            'count': len(wallets)
        })

    except Exception as e:
        logger.error(f"Error fetching wallets: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/wallets', methods=['POST'])
def api_add_wallet():
    """Add a new wallet address"""
    try:
        data = request.get_json()

        # Validate required fields
        wallet_address = data.get('wallet_address', '').strip()
        entity_name = data.get('entity_name', '').strip()

        if not wallet_address:
            return jsonify({'error': 'wallet_address is required'}), 400
        if not entity_name:
            return jsonify({'error': 'entity_name is required'}), 400

        # Optional fields
        purpose = data.get('purpose', '').strip()
        wallet_type = data.get('wallet_type', 'internal').strip()
        confidence_score = float(data.get('confidence_score', 0.9))
        notes = data.get('notes', '').strip()
        created_by = data.get('created_by', 'user').strip()

        # Hardcoded tenant for now (Delta)
        tenant_id = 'delta'

        from database import db_manager

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Check for duplicate wallet address
            check_query = """
                SELECT id FROM wallet_addresses
                WHERE tenant_id = %s AND wallet_address = %s
            """
            cursor.execute(check_query, (tenant_id, wallet_address))
            existing = cursor.fetchone()

            if existing:
                cursor.close()
                return jsonify({'error': 'Wallet address already exists'}), 409

            # Insert new wallet
            insert_query = """
                INSERT INTO wallet_addresses (
                    tenant_id, wallet_address, entity_name, purpose,
                    wallet_type, confidence_score, notes, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """

            cursor.execute(insert_query, (
                tenant_id, wallet_address, entity_name, purpose,
                wallet_type, confidence_score, notes, created_by
            ))

            result = cursor.fetchone()
            wallet_id = str(result[0])
            created_at = result[1].isoformat() if result[1] else None

            conn.commit()
            cursor.close()

        return jsonify({
            'success': True,
            'message': 'Wallet address added successfully',
            'wallet': {
                'id': wallet_id,
                'wallet_address': wallet_address,
                'entity_name': entity_name,
                'purpose': purpose,
                'wallet_type': wallet_type,
                'confidence_score': confidence_score,
                'notes': notes,
                'created_at': created_at
            }
        }), 201

    except Exception as e:
        logger.error(f"Error adding wallet: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/wallets/<wallet_id>', methods=['PUT'])
def api_update_wallet(wallet_id):
    """Update an existing wallet address"""
    try:
        data = request.get_json()

        # Build update fields dynamically
        update_fields = []
        params = []

        if 'entity_name' in data:
            update_fields.append("entity_name = %s")
            params.append(data['entity_name'].strip())

        if 'purpose' in data:
            update_fields.append("purpose = %s")
            params.append(data['purpose'].strip())

        if 'wallet_type' in data:
            update_fields.append("wallet_type = %s")
            params.append(data['wallet_type'].strip())

        if 'confidence_score' in data:
            update_fields.append("confidence_score = %s")
            params.append(float(data['confidence_score']))

        if 'notes' in data:
            update_fields.append("notes = %s")
            params.append(data['notes'].strip())

        if 'is_active' in data:
            update_fields.append("is_active = %s")
            params.append(bool(data['is_active']))

        if not update_fields:
            return jsonify({'error': 'No fields to update'}), 400

        params.append(wallet_id)

        from database import db_manager

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            update_query = f"""
                UPDATE wallet_addresses
                SET {', '.join(update_fields)}
                WHERE id = %s
                RETURNING wallet_address, entity_name, purpose, wallet_type,
                          confidence_score, notes, is_active, updated_at
            """

            cursor.execute(update_query, params)
            result = cursor.fetchone()

            if not result:
                cursor.close()
                return jsonify({'error': 'Wallet not found'}), 404

            conn.commit()

            wallet = {
                'id': wallet_id,
                'wallet_address': result[0],
                'entity_name': result[1],
                'purpose': result[2],
                'wallet_type': result[3],
                'confidence_score': float(result[4]) if result[4] else 0.9,
                'notes': result[5],
                'is_active': result[6],
                'updated_at': result[7].isoformat() if result[7] else None
            }

            cursor.close()

        return jsonify({
            'success': True,
            'message': 'Wallet updated successfully',
            'wallet': wallet
        })

    except Exception as e:
        logger.error(f"Error updating wallet: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/wallets/<wallet_id>', methods=['DELETE'])
def api_delete_wallet(wallet_id):
    """Soft delete a wallet address (set is_active = FALSE)"""
    try:
        from database import db_manager

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            delete_query = """
                UPDATE wallet_addresses
                SET is_active = FALSE
                WHERE id = %s
                RETURNING wallet_address
            """

            cursor.execute(delete_query, (wallet_id,))
            result = cursor.fetchone()

            if not result:
                cursor.close()
                return jsonify({'error': 'Wallet not found'}), 404

            conn.commit()
            cursor.close()

        return jsonify({
            'success': True,
            'message': f'Wallet {result[0]} deactivated successfully'
        })

    except Exception as e:
        logger.error(f"Error deleting wallet: {e}")
        return jsonify({'error': str(e)}), 500


# ========================================
# HOMEPAGE CONTENT API ENDPOINTS
# ========================================

@app.route('/api/homepage/content', methods=['GET'])
def api_get_homepage_content():
    """Get current homepage content (cached or fresh)"""
    try:
        from database import db_manager
        # Import from web_ui local services (not root services/)
        import sys
        import os
        services_path = os.path.join(os.path.dirname(__file__), 'services')
        if services_path not in sys.path:
            sys.path.insert(0, services_path)
        from homepage_generator import HomepageContentGenerator

        tenant_id = get_current_tenant_id()
        generator = HomepageContentGenerator(db_manager, tenant_id)

        # Check for use_cache parameter (default: True)
        use_cache = request.args.get('use_cache', 'true').lower() == 'true'

        content = generator.generate_content(use_cache=use_cache)

        return jsonify({
            'success': True,
            'content': content,
            'cached': content.get('cached', False)
        })

    except Exception as e:
        logger.error(f"Error fetching homepage content: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/homepage/regenerate', methods=['POST'])
def api_regenerate_homepage():
    """Force regenerate homepage content with Claude AI"""
    try:
        from database import db_manager
        # Import from web_ui local services (not root services/)
        import sys
        import os
        services_path = os.path.join(os.path.dirname(__file__), 'services')
        if services_path not in sys.path:
            sys.path.insert(0, services_path)
        from homepage_generator import HomepageContentGenerator

        tenant_id = get_current_tenant_id()
        generator = HomepageContentGenerator(db_manager, tenant_id)

        # Invalidate cache first
        generator.invalidate_cache()

        # Generate fresh content
        content = generator.generate_content(use_cache=False)

        return jsonify({
            'success': True,
            'content': content,
            'message': 'Homepage content regenerated successfully'
        })

    except Exception as e:
        logger.error(f"Error regenerating homepage: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/homepage/data', methods=['GET'])
def api_get_homepage_data():
    """Get standardized homepage data - exact database fields only"""
    try:
        from database import db_manager
        # Import from web_ui local services (not root services/)
        import sys
        import os
        services_path = os.path.join(os.path.dirname(__file__), 'services')
        if services_path not in sys.path:
            sys.path.insert(0, services_path)
        from data_queries import DataQueryService

        tenant_id = get_current_tenant_id()
        homepage_service = DataQueryService(db_manager, tenant_id)

        # Get complete homepage data with exact database fields
        data = homepage_service.get_all_homepage_data()

        # Wrap in standardized format expected by frontend
        return jsonify({
            'success': True,
            'company_name': data.get('company', {}).get('company_name'),
            'company_tagline': data.get('company', {}).get('company_tagline'),
            'company_description': data.get('company', {}).get('company_description'),
            'generated_at': data.get('generated_at'),
            'metrics': {
                'business_units': data.get('portfolio', {}).get('total_entities', 0),
                'account_integrations': (
                    data.get('portfolio', {}).get('wallet_count', 0) +
                    data.get('portfolio', {}).get('bank_account_count', 0)
                ),
                'transaction_value': data.get('kpis', {}).get('total_revenue', 0),
                'transaction_count': data.get('kpis', {}).get('total_transactions', 0)
            },
            'raw_data': data  # Include complete data for debugging
        })

    except Exception as e:
        logger.error(f"Error fetching homepage data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/homepage/kpis', methods=['GET'])
def api_get_homepage_kpis():
    """Get just the KPIs for homepage display"""
    try:
        from database import db_manager
        # Import from web_ui local services (not root services/)
        import sys
        import os
        services_path = os.path.join(os.path.dirname(__file__), 'services')
        if services_path not in sys.path:
            sys.path.insert(0, services_path)
        from data_queries import DataQueryService

        tenant_id = get_current_tenant_id()
        data_service = DataQueryService(db_manager, tenant_id)

        kpis = data_service.get_company_kpis()

        return jsonify({
            'success': True,
            'kpis': kpis
        })

    except Exception as e:
        logger.error(f"Error fetching KPIs: {e}")
        return jsonify({'error': str(e)}), 500


# ========================================
# ONBOARDING BOT API ENDPOINTS
# ========================================

@app.route('/api/bot/start-session', methods=['POST'])
def api_bot_start_session():
    """Start a new onboarding bot session"""
    try:
        from database import db_manager
        # Import from web_ui local services (not root services/)
        import sys
        import os
        services_path = os.path.join(os.path.dirname(__file__), 'services')
        if services_path not in sys.path:
            sys.path.insert(0, services_path)
        from onboarding_bot import OnboardingBot

        tenant_id = get_current_tenant_id()
        bot = OnboardingBot(db_manager, tenant_id)

        session_id = bot.start_new_session()

        # Get initial greeting
        history = bot.get_conversation_history(session_id)
        initial_message = history[0] if history else {'role': 'assistant', 'content': 'Hello!'}

        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': initial_message['content']
        })

    except Exception as e:
        logger.error(f"Error starting bot session: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bot/chat', methods=['POST'])
def api_bot_chat():
    """Send a message to the onboarding bot"""
    try:
        from database import db_manager
        # Import from web_ui local services (not root services/)
        import sys
        import os
        services_path = os.path.join(os.path.dirname(__file__), 'services')
        if services_path not in sys.path:
            sys.path.insert(0, services_path)
        from onboarding_bot import OnboardingBot

        data = request.get_json()
        session_id = data.get('session_id')
        user_message = data.get('message')

        if not session_id or not user_message:
            return jsonify({'error': 'session_id and message are required'}), 400

        tenant_id = get_current_tenant_id()
        bot = OnboardingBot(db_manager, tenant_id)

        # Process message
        result = bot.chat(session_id, user_message)

        return jsonify({
            'success': result.get('success', False),
            'response': result.get('response'),
            'extracted_data': result.get('extracted_data'),
            'completion_percentage': result.get('completion_percentage', 0),
            'error': result.get('error')
        })

    except Exception as e:
        logger.error(f"Error in bot chat: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/bot/status', methods=['GET'])
def api_bot_status():
    """Get current onboarding status"""
    try:
        from database import db_manager
        # Import from web_ui local services (not root services/)
        import sys
        import os
        services_path = os.path.join(os.path.dirname(__file__), 'services')
        if services_path not in sys.path:
            sys.path.insert(0, services_path)
        from onboarding_bot import OnboardingBot

        tenant_id = get_current_tenant_id()
        bot = OnboardingBot(db_manager, tenant_id)

        status = bot.get_onboarding_status()

        return jsonify({
            'success': True,
            'status': status
        })

    except Exception as e:
        logger.error(f"Error getting bot status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bot/history/<session_id>', methods=['GET'])
def api_bot_history(session_id):
    """Get conversation history for a session"""
    try:
        from database import db_manager
        # Import from web_ui local services (not root services/)
        import sys
        import os
        services_path = os.path.join(os.path.dirname(__file__), 'services')
        if services_path not in sys.path:
            sys.path.insert(0, services_path)
        from onboarding_bot import OnboardingBot

        tenant_id = get_current_tenant_id()
        bot = OnboardingBot(db_manager, tenant_id)

        history = bot.get_conversation_history(session_id)

        return jsonify({
            'success': True,
            'history': history
        })

    except Exception as e:
        logger.error(f"Error getting bot history: {e}")
        return jsonify({'error': str(e)}), 500


# ========================================
# USER PROFILE API ENDPOINTS
# ========================================

@app.route('/api/user/profile', methods=['GET'])
def api_get_user_profile():
    """Get current user's profile information including role and permissions"""
    try:
        from database import db_manager

        firebase_uid = request.args.get('firebase_uid')

        if not firebase_uid:
            return jsonify({'error': 'firebase_uid is required'}), 400

        with db_manager.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            query = """
                SELECT
                    u.id,
                    u.firebase_uid,
                    u.email,
                    u.display_name,
                    u.user_type,
                    u.is_active,
                    u.email_verified,
                    u.created_at,
                    u.last_login_at,
                    json_agg(
                        json_build_object(
                            'tenant_id', tu.tenant_id,
                            'tenant_name', tc.company_name,
                            'role', tu.role,
                            'permissions', tu.permissions,
                            'is_active', tu.is_active,
                            'added_at', tu.added_at
                        )
                    ) FILTER (WHERE tu.id IS NOT NULL) as tenants
                FROM users u
                LEFT JOIN tenant_users tu ON u.id = tu.user_id AND tu.is_active = TRUE
                LEFT JOIN tenant_configuration tc ON tu.tenant_id = tc.tenant_id
                WHERE u.firebase_uid = %s AND u.is_active = TRUE
                GROUP BY u.id
            """

            cursor.execute(query, (firebase_uid,))
            result = cursor.fetchone()

            if not result:
                cursor.close()
                return jsonify({'error': 'User not found'}), 404

            user = dict(result)

            # Handle date serialization - check if already string
            if user.get('created_at'):
                if hasattr(user['created_at'], 'isoformat'):
                    user['created_at'] = user['created_at'].isoformat()
            if user.get('last_login_at'):
                if hasattr(user['last_login_at'], 'isoformat'):
                    user['last_login_at'] = user['last_login_at'].isoformat()

            if user['tenants']:
                for tenant in user['tenants']:
                    if tenant.get('added_at') and hasattr(tenant['added_at'], 'isoformat'):
                        tenant['added_at'] = tenant['added_at'].isoformat()

            cursor.close()

        return jsonify({
            'success': True,
            'user': user
        })

    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return jsonify({'error': str(e)}), 500


# ========================================
# BANK ACCOUNTS API ENDPOINTS
# ========================================

@app.route('/api/bank-accounts', methods=['GET'])
def api_get_bank_accounts():
    """Get all bank accounts for the current tenant"""
    try:
        from database import db_manager

        tenant_id = get_current_tenant_id()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            query = """
                SELECT
                    id, tenant_id, account_name, institution_name,
                    account_number, routing_number, account_type, currency,
                    current_balance, available_balance, last_sync_at,
                    status, is_primary, institution_logo_url, account_color,
                    notes, created_at, updated_at
                FROM bank_accounts
                WHERE tenant_id = %s AND status != 'closed'
                ORDER BY is_primary DESC, created_at DESC
            """

            cursor.execute(query, (tenant_id,))
            results = cursor.fetchall()

            accounts = []
            for row in results:
                account = dict(row)
                # Convert UUID to string
                account['id'] = str(account['id'])
                # Convert decimals to float
                if account.get('current_balance'):
                    account['current_balance'] = float(account['current_balance'])
                if account.get('available_balance'):
                    account['available_balance'] = float(account['available_balance'])
                # Convert timestamps to ISO format
                if account.get('last_sync_at'):
                    account['last_sync_at'] = account['last_sync_at'].isoformat()
                if account.get('created_at'):
                    account['created_at'] = account['created_at'].isoformat()
                if account.get('updated_at'):
                    account['updated_at'] = account['updated_at'].isoformat()
                accounts.append(account)

            cursor.close()

        return jsonify({
            'success': True,
            'accounts': accounts,
            'count': len(accounts)
        })

    except Exception as e:
        logger.error(f"Error fetching bank accounts: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bank-accounts', methods=['POST'])
def api_add_bank_account():
    """Add a new bank account"""
    try:
        data = request.get_json()

        # Validate required fields
        account_name = data.get('account_name', '').strip()
        institution_name = data.get('institution_name', '').strip()
        account_type = data.get('account_type', '').strip()

        if not account_name:
            return jsonify({'error': 'account_name is required'}), 400
        if not institution_name:
            return jsonify({'error': 'institution_name is required'}), 400
        if not account_type:
            return jsonify({'error': 'account_type is required'}), 400

        # Optional fields
        account_number = data.get('account_number', '').strip()
        routing_number = data.get('routing_number', '').strip()
        currency = data.get('currency', 'USD').strip()
        current_balance = data.get('current_balance')
        available_balance = data.get('available_balance')
        status = data.get('status', 'active').strip()
        is_primary = data.get('is_primary', False)
        institution_logo_url = data.get('institution_logo_url', '').strip()
        account_color = data.get('account_color', '').strip()
        notes = data.get('notes', '').strip()

        tenant_id = get_current_tenant_id()

        from database import db_manager

        with db_manager.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Check for duplicate
            check_query = """
                SELECT id FROM bank_accounts
                WHERE tenant_id = %s
                AND institution_name = %s
                AND account_number = %s
            """
            cursor.execute(check_query, (tenant_id, institution_name, account_number))
            existing = cursor.fetchone()

            if existing:
                cursor.close()
                return jsonify({'error': 'Bank account already exists'}), 409

            # If this is set as primary, unset other primary accounts
            if is_primary:
                cursor.execute("""
                    UPDATE bank_accounts
                    SET is_primary = FALSE
                    WHERE tenant_id = %s
                """, (tenant_id,))

            # Insert new account
            insert_query = """
                INSERT INTO bank_accounts (
                    tenant_id, account_name, institution_name, account_number,
                    routing_number, account_type, currency, current_balance,
                    available_balance, status, is_primary, institution_logo_url,
                    account_color, notes, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
            """

            cursor.execute(insert_query, (
                tenant_id, account_name, institution_name, account_number,
                routing_number, account_type, currency, current_balance,
                available_balance, status, is_primary, institution_logo_url,
                account_color, notes, 'user'
            ))

            result = cursor.fetchone()
            account_id = str(result['id'])
            created_at = result['created_at'].isoformat()

            conn.commit()
            cursor.close()

        return jsonify({
            'success': True,
            'message': 'Bank account added successfully',
            'account': {
                'id': account_id,
                'account_name': account_name,
                'institution_name': institution_name,
                'account_type': account_type,
                'status': status,
                'created_at': created_at
            }
        }), 201

    except Exception as e:
        logger.error(f"Error adding bank account: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bank-accounts/<account_id>', methods=['PUT'])
def api_update_bank_account(account_id):
    """Update an existing bank account"""
    try:
        data = request.get_json()

        # Build update fields dynamically
        update_fields = []
        params = []

        if 'account_name' in data:
            update_fields.append("account_name = %s")
            params.append(data['account_name'].strip())

        if 'institution_name' in data:
            update_fields.append("institution_name = %s")
            params.append(data['institution_name'].strip())

        if 'account_number' in data:
            update_fields.append("account_number = %s")
            params.append(data['account_number'].strip())

        if 'routing_number' in data:
            update_fields.append("routing_number = %s")
            params.append(data['routing_number'].strip())

        if 'account_type' in data:
            update_fields.append("account_type = %s")
            params.append(data['account_type'].strip())

        if 'current_balance' in data:
            update_fields.append("current_balance = %s")
            params.append(data['current_balance'])

        if 'available_balance' in data:
            update_fields.append("available_balance = %s")
            params.append(data['available_balance'])

        if 'status' in data:
            update_fields.append("status = %s")
            params.append(data['status'].strip())

        if 'is_primary' in data:
            update_fields.append("is_primary = %s")
            params.append(bool(data['is_primary']))

        if 'notes' in data:
            update_fields.append("notes = %s")
            params.append(data['notes'].strip())

        if not update_fields:
            return jsonify({'error': 'No fields to update'}), 400

        params.append(account_id)

        from database import db_manager
        tenant_id = get_current_tenant_id()

        with db_manager.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # If setting as primary, unset others first
            if 'is_primary' in data and data['is_primary']:
                cursor.execute("""
                    UPDATE bank_accounts
                    SET is_primary = FALSE
                    WHERE tenant_id = %s AND id != %s
                """, (tenant_id, account_id))

            update_query = f"""
                UPDATE bank_accounts
                SET {', '.join(update_fields)}
                WHERE id = %s
                RETURNING account_name, institution_name, account_type, status, updated_at
            """

            cursor.execute(update_query, params)
            result = cursor.fetchone()

            if not result:
                cursor.close()
                return jsonify({'error': 'Bank account not found'}), 404

            conn.commit()

            account = dict(result)
            account['id'] = account_id
            if account.get('updated_at'):
                account['updated_at'] = account['updated_at'].isoformat()

            cursor.close()

        return jsonify({
            'success': True,
            'message': 'Bank account updated successfully',
            'account': account
        })

    except Exception as e:
        logger.error(f"Error updating bank account: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/bank-accounts/<account_id>', methods=['DELETE'])
def api_delete_bank_account(account_id):
    """Soft delete a bank account (set status = 'closed')"""
    try:
        from database import db_manager

        with db_manager.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            delete_query = """
                UPDATE bank_accounts
                SET status = 'closed'
                WHERE id = %s
                RETURNING account_name, institution_name
            """

            cursor.execute(delete_query, (account_id,))
            result = cursor.fetchone()

            if not result:
                cursor.close()
                return jsonify({'error': 'Bank account not found'}), 404

            conn.commit()
            cursor.close()

        return jsonify({
            'success': True,
            'message': f'Bank account {result["account_name"]} at {result["institution_name"]} closed successfully'
        })

    except Exception as e:
        logger.error(f"Error deleting bank account: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/suggestions')
def api_suggestions():
    """API endpoint to get AI-powered field suggestions"""
    try:
        field_type = request.args.get('field_type')
        current_value = request.args.get('current_value', '')
        transaction_id = request.args.get('transaction_id')

        if not field_type:
            return jsonify({'error': 'field_type parameter required'}), 400

        # Get transaction context if transaction_id provided
        context = {}
        if transaction_id:
            # Get current tenant_id for multi-tenant isolation
            tenant_id = get_current_tenant_id()

            from database import db_manager
            conn = db_manager._get_postgresql_connection()
            cursor = conn.cursor()
            is_postgresql = hasattr(cursor, 'mogrify')
            placeholder = '%s' if is_postgresql else '?'

            cursor.execute(f"SELECT * FROM transactions WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}", (tenant_id, transaction_id))
            row = cursor.fetchone()
            if row:
                # Convert tuple to dict for PostgreSQL - must match column order
                context = {
                    'transaction_id': row[0],
                    'date': row[1],
                    'description': row[2],
                    'amount': row[3],
                    'currency': row[4],
                    'usd_equivalent': row[5],
                    'classified_entity': row[6],
                    'justification': row[7],
                    'confidence': row[8],
                    'classification_reason': row[9],
                    'origin': row[10],
                    'destination': row[11],
                    'identifier': row[12],
                    'source_file': row[13],
                    'crypto_amount': row[14],
                    'conversion_note': row[15],
                    'accounting_category': row[16],
                    'archived': row[17],
                    'confidence_history': row[18],
                    'ai_reassessment_count': row[19],
                    'last_ai_review': row[20],
                    'user_feedback_count': row[21],
                    'ai_suggestions': row[22],
                    'subcategory': row[23]
                }
            conn.close()

        # Add special parameters for similar_descriptions, similar_entities, similar_accounting, and similar_subcategory
        if field_type in ['similar_descriptions', 'similar_entities', 'similar_accounting', 'similar_subcategory']:
            context['transaction_id'] = transaction_id
            context['value'] = request.args.get('value', current_value)
            context['field_type'] = field_type

        suggestions = get_ai_powered_suggestions(field_type, current_value, context)

        # Check if None was returned due to API issues (empty list [] is valid - means no matches)
        if suggestions is None and claude_client:
            return jsonify({
                'error': 'Claude API failed to generate suggestions',
                'suggestions': [],
                'fallback_available': False,
                'has_learned_patterns': False
            }), 500
        elif suggestions is None and not claude_client:
            return jsonify({
                'error': 'Claude API not available - check ANTHROPIC_API_KEY environment variable',
                'suggestions': [],
                'fallback_available': False,
                'has_learned_patterns': False
            }), 500

        # Return suggestions with pattern learning status for entity suggestions
        has_patterns = context.get('has_learned_patterns', False) if field_type == 'similar_entities' else None
        result = {'suggestions': suggestions}
        if has_patterns is not None:
            result['has_learned_patterns'] = has_patterns

        return jsonify(result)

    except Exception as e:
        print(f"ERROR: API suggestions error: {e}", flush=True)
        print(f"ERROR TRACEBACK: {traceback.format_exc()}", flush=True)
        return jsonify({
            'error': f'Failed to get AI suggestions: {str(e)}',
            'suggestions': [],
            'fallback_available': False
        }), 500

@app.route('/api/ai/get-suggestions', methods=['GET'])
def api_ai_get_suggestions():
    """
    API endpoint for AI Smart Recommendations modal
    Returns AI-powered suggestions for improving a transaction's classification
    """
    import traceback

    try:
        transaction_id = request.args.get('transaction_id')

        if not transaction_id:
            return jsonify({'error': 'transaction_id parameter required'}), 400

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        # Get transaction from database
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'

        cursor.execute(f"SELECT * FROM transactions WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}", (tenant_id, transaction_id))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return jsonify({'error': 'Transaction not found'}), 404

        # Convert row to dict (PostgreSQL returns tuples)
        # Actual column order: transaction_id, date, description, amount, currency, usd_equivalent,
        # classified_entity, justification, confidence, classification_reason, origin, destination,
        # identifier, source_file, crypto_amount, conversion_note, accounting_category, archived,
        # confidence_history, ai_reassessment_count, last_ai_review, user_feedback_count, ai_suggestions, subcategory
        transaction = {
            'transaction_id': row[0] if len(row) > 0 else None,
            'date': str(row[1]) if len(row) > 1 else None,
            'description': row[2] if len(row) > 2 else '',
            'amount': float(row[3]) if len(row) > 3 and row[3] else 0,
            'currency': row[4] if len(row) > 4 else 'USD',
            'classified_entity': row[6] if len(row) > 6 else None,
            'justification': row[7] if len(row) > 7 else None,
            'confidence': float(row[8]) if len(row) > 8 and row[8] else 0.5,
            'origin': row[10] if len(row) > 10 else None,  # Raw origin from bank statement
            'destination': row[11] if len(row) > 11 else None,  # Raw destination from bank statement
            'accounting_category': row[16] if len(row) > 16 else None,
            'subcategory': row[23] if len(row) > 23 else None,
        }
        conn.close()

        current_confidence = transaction.get('confidence', 0.5)
        current_entity = transaction.get('classified_entity', 'Unknown')
        current_accounting_category = transaction.get('accounting_category') or 'Unknown'
        current_subcategory = transaction.get('subcategory') or 'N/A'
        current_justification = transaction.get('justification') or 'N/A'

        # If confidence is already high (>= 0.9), no suggestions needed
        if current_confidence >= 0.9:
            return jsonify({
                'message': 'Transaction classification is already confident',
                'suggestions': [],
                'reasoning': f'Current confidence ({current_confidence:.0%}) is high. No improvements needed.',
                'new_confidence': current_confidence,
                'similar_count': 0,
                'patterns_count': 0,
                'transaction': transaction  #  FIX: Include transaction details
            })

        # Use Claude AI to analyze and suggest improvements
        if not claude_client:
            return jsonify({
                'error': 'Claude AI not available. Set ANTHROPIC_API_KEY to enable AI suggestions.',
                'suggestions': []
            }), 503

        # ENHANCEMENT: Use the pattern learning system to find ALL relevant patterns
        # This searches across all entities and applies confidence decay + normalization
        patterns_context = ""
        try:
            # Build transaction context for pattern matching
            transaction_context = {
                'description': transaction['description'],
                'amount': transaction['amount'],
                'date': transaction['date'],
                'origin': transaction.get('origin', ''),
                'destination': transaction.get('destination', ''),
                'classified_entity': transaction.get('classified_entity', '')
            }

            # Use enhance_ai_prompt_with_learning to get intelligent pattern context
            # This function applies all enhancements: decay, normalization, negative patterns, disambiguation
            base_prompt = ""  # We'll add patterns separately
            enhanced_context = enhance_ai_prompt_with_learning(
                field_type='classified_entity',
                base_prompt=base_prompt,
                context=transaction_context
            )

            # Extract just the learned patterns section (if any)
            if enhanced_context and enhanced_context.strip():
                patterns_context = f"\n\n{enhanced_context}"
        except Exception as e:
            # Fallback to simple pattern query if enhancement fails
            logger.warning(f"Pattern enhancement error: {e}")
            import traceback
            traceback.print_exc()
            # Leave patterns_context empty if enhancement fails
            patterns_context = ""

        # Build Claude prompt
        # Include both simplified description AND raw origin/destination for maximum context
        raw_description_info = ""
        if transaction.get('origin') or transaction.get('destination'):
            raw_parts = []
            if transaction.get('origin'):
                raw_parts.append(f"Origin: {transaction['origin']}")
            if transaction.get('destination'):
                raw_parts.append(f"Destination: {transaction['destination']}")
            if raw_parts:
                raw_description_info = f"\n- Raw Bank Data: {' | '.join(raw_parts)}"

        prompt = f"""Analyze this transaction and suggest improvements to its classification.

CURRENT TRANSACTION:
- Description: {transaction['description']}{raw_description_info}
- Amount: ${transaction['amount']}
- Date: {transaction['date']}
- Current Confidence: {current_confidence:.0%}

CURRENT CLASSIFICATION (User may have already filled some fields):
- Entity: {current_entity}
- Accounting Category: {current_accounting_category}
- Subcategory: {current_subcategory}
- Justification: {current_justification}
{patterns_context}

**IMPORTANT**: Even if the transaction is an "Internal Transfer" or "Personal" expense with no P&L impact, you MUST still suggest appropriate categorization to complete the record. Use these guidelines:
- Internal Transfer → accounting_category: "INTERCOMPANY_ELIMINATION", subcategory: "Internal Transfer", justification: "Movement between company entities"
- Personal → accounting_category: "OTHER_EXPENSE", subcategory: "Personal Expense", justification: "Personal/non-business expense"

**GEOGRAPHIC & MERCHANT ANALYSIS FOR ENTITY CLASSIFICATION**:
Before suggesting an entity, analyze these clues from BOTH the simplified description AND raw bank data:

IMPORTANT: Raw Bank Data (Origin/Destination) often contains additional context:
- Location codes, city names, state/country abbreviations
- Bank routing information that indicates geographic region
- Transaction types (FEDWIRE, ACH, WIRE) that suggest US vs international
- Merchant identifiers with location suffixes (e.g., "PETROBRAS AYOLAS" vs "PETROBRAS")

1. **Geographic Indicators**:
   - Paraguay names (Ayolas, San Ignacio, Asunción, etc.) → "Delta Mining Paraguay S.A."
   - Brazil names/locations → "Delta Brazil Operations"
   - US-based merchants/services → "Delta LLC"
   - International crypto/trading platforms → "Delta Prop Shop LLC"

2. **Merchant Type Analysis**:
   - Gas stations (PETROBRAS, PETROPAR, SHELL, BR) → Check location for entity
   - Restaurants/Food (local names) → Check country/region
   - Technology/Software (APIs, cloud services, SaaS) → Usually "Delta LLC" or "Delta Prop Shop LLC"
   - Mining/Industrial suppliers → "Delta Mining Paraguay S.A." if in Paraguay
   - Professional services → Match to entity using them

3. **Language/Naming Patterns**:
   - Spanish names (COMERCIAL, AUTOSERVIS, FERRETERIA) → Paraguay → "Delta Mining Paraguay S.A."
   - Portuguese names (GRUPO, BRASIL) → Brazil → "Delta Brazil Operations"
   - English names (ANTHROPIC, GITHUB, AWS) → US/Tech → "Delta LLC" or "Delta Prop Shop LLC"

4. **Business Function**:
   - Staking/validation/crypto → "Infinity Validator"
   - Prop trading/DeFi → "Delta Prop Shop LLC"
   - Mining operations/equipment → "Delta Mining Paraguay S.A."
   - General corporate/admin → "Delta LLC"

Use these clues to make the MOST ACCURATE entity suggestion possible.

TASK: Suggest 1-4 specific improvements to increase classification confidence. Focus on these fields:
1. **classified_entity** - The business unit/entity (e.g., "Delta Mining Paraguay S.A.", "Delta Prop Shop LLC")
2. **accounting_category** - Primary accounting category (MUST be ONE of: REVENUE, COGS, OPERATING_EXPENSE, INTEREST_EXPENSE, OTHER_INCOME, OTHER_EXPENSE, INCOME_TAX_EXPENSE, ASSET, LIABILITY, EQUITY, INTERCOMPANY_ELIMINATION)
3. **subcategory** - Specific subcategory (e.g., "Auto Maintenance", "Employee Meals", "Technology", "Bank Fees", "Professional Services")
4. **justification** - Business justification (e.g., "Paraguay operations fuel cost", "Team dinner expense", "Required software subscription")

Return JSON in this EXACT format:
{{
  "reasoning": "Brief explanation of what could be improved",
  "new_confidence": 0.85,
  "suggestions": [
    {{
      "field": "classified_entity",
      "current_value": "{current_entity}",
      "suggested_value": "Delta Mining Paraguay S.A.",
      "reason": "Transaction description indicates this is a Paraguay operation",
      "confidence": 0.85
    }},
    {{
      "field": "accounting_category",
      "current_value": "{current_accounting_category}",
      "suggested_value": "OPERATING_EXPENSE",
      "reason": "This is an operational expense for vehicle maintenance",
      "confidence": 0.80
    }},
    {{
      "field": "subcategory",
      "current_value": "{current_subcategory}",
      "suggested_value": "Auto Maintenance",
      "reason": "Description indicates auto service/maintenance",
      "confidence": 0.75
    }},
    {{
      "field": "justification",
      "current_value": "{current_justification}",
      "suggested_value": "Paraguay operations vehicle maintenance",
      "reason": "Specific business justification based on entity and transaction type",
      "confidence": 0.70
    }}
  ]
}}

**MERCHANT TYPE TO SUBCATEGORY MAPPING**:
Use merchant type clues to suggest accurate subcategories:
- Gas stations (PETROBRAS, SHELL, PETROPAR, BR, ENEX) → "Fuel Expense" or "Vehicle Maintenance"
- Restaurants (local names, food descriptions) → "Employee Meals" or "Client Entertainment"
- Hardware stores (FERRETERIA, COMERCIAL) → "Office Supplies" or "Repair & Maintenance"
- Auto services (AUTOSERVIS, CENTRO AUTOMOTIVO) → "Vehicle Maintenance"
- Technology (API, CLOUD, SaaS names) → "Software Subscriptions" or "Technology Services"
- Internet/utilities (ISP names, utility companies) → "Telecommunications" or "Utilities"
- Professional services (consulting, legal, accounting firms) → "Professional Services"

CRITICAL RULES:
- Only suggest fields that actually need improvement (if user already filled a field correctly, don't suggest it)
- If user has already categorized Entity, Category, or Subcategory, use those values to inform the justification suggestion
- For accounting_category, MUST use exact values from the list above
- For subcategory, use the merchant type analysis above to provide specific, descriptive categories (2-4 words max)
- For justification, provide a concise business reason (4-6 words) that combines entity + transaction purpose
- For entity classification, ALWAYS apply the geographic & merchant analysis framework above
- If current classification is already good for all fields, return empty suggestions array
- DO NOT suggest "transaction_keywords" or any other fields not listed above"""

        response = claude_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        elif response_text.startswith('```'):
            response_text = response_text.replace('```', '').strip()

        # Try to extract just the JSON object if there's extra text
        # Look for the first { and last }
        import re
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            response_text = json_match.group(0)

        print(f"DEBUG: Cleaned Claude response for parsing: {response_text[:500]}...")

        try:
            ai_response = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"ERROR: JSON parsing failed: {e}")
            print(f"ERROR: Response text was: {response_text}")
            # Return a safe fallback response
            return jsonify({
                'error': f'AI response parsing error: {str(e)}. The AI may have returned malformed data.',
                'suggestions': [],
                'reasoning': 'Unable to parse AI response',
                'new_confidence': current_confidence,
                'similar_count': 0,
                'patterns_count': 0
            }), 500

        # Add metadata
        # Count patterns from the enhanced context (if any)
        patterns_count = patterns_context.count('\n- ') if patterns_context else 0
        ai_response['similar_count'] = patterns_count
        ai_response['patterns_count'] = patterns_count

        #  FIX: Include transaction details in the response
        # This avoids relying on fragile HTML attribute passing of transaction object
        ai_response['transaction'] = transaction

        return jsonify(ai_response)

    except Exception as e:
        print(f"ERROR: AI suggestions error: {e}")
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        return jsonify({
            'error': f'Failed to get AI suggestions: {str(e)}',
            'suggestions': []
        }), 500

@app.route('/api/ai/apply-suggestion', methods=['POST'])
def api_ai_apply_suggestion():
    """
    Apply an AI suggestion to a transaction
    Wraps the update_transaction_field function with AI-specific logic
    """
    try:
        data = request.json
        transaction_id = data.get('transaction_id')
        suggestion = data.get('suggestion', {})

        if not transaction_id or not suggestion:
            return jsonify({'error': 'transaction_id and suggestion required'}), 400

        field = suggestion.get('field')
        suggested_value = suggestion.get('suggested_value')

        if not field or not suggested_value:
            return jsonify({'error': 'suggestion must contain field and suggested_value'}), 400

        # Use the existing update_transaction_field function
        success = update_transaction_field(
            transaction_id=transaction_id,
            field=field,
            value=suggested_value,
            user='ai_assistant'
        )

        if success:
            # If this was an entity change, trigger pattern learning
            if field == 'classified_entity' and claude_client:
                try:
                    # Get current tenant_id for multi-tenant isolation
                    tenant_id = get_current_tenant_id()

                    # Get transaction description for pattern learning
                    from database import db_manager
                    conn = db_manager._get_postgresql_connection()
                    cursor = conn.cursor()
                    is_postgresql = hasattr(cursor, 'mogrify')
                    placeholder = '%s' if is_postgresql else '?'

                    cursor.execute(f"SELECT description FROM transactions WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}", (tenant_id, transaction_id))
                    row = cursor.fetchone()
                    conn.close()

                    if row and row[0]:
                        description = row[0]
                        # Extract and store entity patterns for future learning
                        extract_entity_patterns_with_llm(transaction_id, suggested_value, description, claude_client)
                        print(f" AI suggestion applied and pattern learning triggered for {field} = {suggested_value}")
                except Exception as pattern_error:
                    print(f" Pattern learning failed (non-critical): {pattern_error}")

            return jsonify({
                'success': True,
                'field': field,
                'value': suggested_value,
                'message': f'Successfully updated {field} to {suggested_value}'
            })
        else:
            return jsonify({
                'error': f'Failed to update {field}',
                'success': False
            }), 500

    except Exception as e:
        print(f"ERROR: Apply AI suggestion error: {e}")
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        return jsonify({
            'error': f'Failed to apply suggestion: {str(e)}',
            'success': False
        }), 500

@app.route('/api/ai/ask-accounting-category', methods=['POST'])
def api_ask_accounting_category():
    """API endpoint to ask Claude AI about accounting categorization"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        transaction_context = data.get('transaction_context', {})

        if not question:
            return jsonify({'error': 'Question parameter required'}), 400

        # Extract transaction details
        description = transaction_context.get('description', '')
        amount = transaction_context.get('amount', '')
        entity = transaction_context.get('entity', '')
        origin = transaction_context.get('origin', '')
        destination = transaction_context.get('destination', '')

        # Get known wallets for wallet matching context
        from database import db_manager
        wallet_conn = db_manager._get_postgresql_connection()
        wallet_cursor = wallet_conn.cursor()
        wallet_cursor.execute("""
            SELECT wallet_address, entity_name, wallet_type, purpose
            FROM wallet_addresses
            WHERE tenant_id = 'delta' AND is_active = true
            ORDER BY wallet_type, entity_name
        """)
        known_wallets = wallet_cursor.fetchall()
        wallet_conn.close()

        # Check if transaction origin or destination matches any known wallet
        wallet_context = ""
        matched_wallet = None
        match_direction = None

        for wallet_row in known_wallets:
            wallet_addr, wallet_entity, wallet_type, wallet_purpose = wallet_row
            if wallet_addr:
                # Check if wallet matches origin or destination
                if origin and wallet_addr.lower() in origin.lower():
                    matched_wallet = {
                        'address': wallet_addr,
                        'entity': wallet_entity,
                        'type': wallet_type,
                        'purpose': wallet_purpose
                    }
                    match_direction = 'origin'
                    break
                elif destination and wallet_addr.lower() in destination.lower():
                    matched_wallet = {
                        'address': wallet_addr,
                        'entity': wallet_entity,
                        'type': wallet_type,
                        'purpose': wallet_purpose
                    }
                    match_direction = 'destination'
                    break

        if matched_wallet:
            wallet_context = f"""
WALLET MATCH DETECTED:
- Matched Wallet: {matched_wallet['address'][:20]}...
- Entity: {matched_wallet['entity']}
- Type: {matched_wallet['type']}
- Purpose: {matched_wallet['purpose']}
- Match Direction: {match_direction}

  IMPORTANT: This transaction involves a KNOWN WALLET. Use this context to categorize accurately:
  - If wallet_type is "internal": This is likely an INTERNAL_TRANSFER or INTERCOMPANY_ELIMINATION
  - If wallet_type is "customer": This is likely REVENUE (if incoming) or REFUND (if outgoing)
  - If wallet_type is "vendor": This is likely OPERATING_EXPENSE (if outgoing) or REVENUE (if incoming)
  - If wallet_type is "exchange": This may be TRADING activity or exchange transfers
"""

        # Build prompt for Claude
        prompt = f"""You are an expert CFO and accounting assistant. A user is asking about how to categorize a transaction for accounting purposes.

Transaction Details:
- Description: {description}
- Amount: {amount}
- Business Entity: {entity}
- Origin: {origin if origin else 'N/A'}
- Destination: {destination if destination else 'N/A'}
{wallet_context}
User Question: {question}

Please suggest the most appropriate accounting categories for this transaction. Provide 1-3 category suggestions with brief explanations.

For each suggestion, you MUST provide BOTH:
1. **Primary Category** - Choose ONE from this exact list:
   - REVENUE
   - COGS
   - OPERATING_EXPENSE
   - INTEREST_EXPENSE
   - OTHER_INCOME
   - OTHER_EXPENSE
   - INCOME_TAX_EXPENSE
   - ASSET
   - LIABILITY
   - EQUITY
   - INTERCOMPANY_ELIMINATION

2. **Subcategory** - A specific classification like "Bank Fees", "Hosting Revenue", "Technology", "Power/Utilities", "Employee Meals", "Travel Expense", etc.

Return your response in this exact JSON format:
{{
  "note": "Brief context or general observation (optional)",
  "categories": [
    {{
      "primary_category": "OPERATING_EXPENSE",
      "subcategory": "Employee Meals",
      "explanation": "Why this category is appropriate"
    }}
  ]
}}

Consider standard accounting practices, tax implications, and best practices for financial reporting."""

        print(f"AI: Calling Claude API for accounting category guidance...")
        start_time = time.time()

        # Call Claude API
        response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )

        elapsed_time = time.time() - start_time
        print(f"LOADING: Claude API response time: {elapsed_time:.2f} seconds")

        answer_text = response.content[0].text.strip()
        print(f"DEBUG: Claude accounting category response: {answer_text[:200]}...")

        # Parse JSON response from Claude
        import json
        import re

        # Try to extract JSON from the response
        json_match = re.search(r'\{[\s\S]*\}', answer_text)
        if json_match:
            result = json.loads(json_match.group(0))
        else:
            # Fallback if JSON parsing fails
            result = {
                "categories": [{
                    "primary_category": "OPERATING_EXPENSE",
                    "subcategory": "General Expense",
                    "explanation": answer_text[:200]
                }]
            }

        return jsonify({
            'result': result,
            'success': True
        })

    except Exception as e:
        print(f"ERROR: AI accounting category error: {e}", flush=True)
        print(f"ERROR TRACEBACK: {traceback.format_exc()}", flush=True)
        return jsonify({
            'error': f'Failed to get AI accounting guidance: {str(e)}',
            'success': False
        }), 500

@app.route('/api/ai/find-similar-after-suggestion', methods=['POST'])
def api_ai_find_similar_after_suggestion():
    """API endpoint to use Claude AI to find transactions similar to one just categorized"""
    try:
        data = request.json
        transaction_id = data.get('transaction_id')
        applied_suggestions = data.get('applied_suggestions', [])

        if not transaction_id or not applied_suggestions:
            return jsonify({'error': 'transaction_id and applied_suggestions are required'}), 400

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        # Get the original transaction
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'

        cursor.execute(f"SELECT * FROM transactions WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}", (tenant_id, transaction_id))
        original_row = cursor.fetchone()

        if not original_row:
            conn.close()
            return jsonify({'error': 'Transaction not found'}), 404

        # Convert row to dictionary using column names
        column_names = [desc[0] for desc in cursor.description]
        original = dict(zip(column_names, original_row))

        # Extract fields that were applied
        applied_fields = {}
        entity_name = None  # Extract the entity for TF-IDF matching

        for suggestion in applied_suggestions:
            field = suggestion.get('field')
            value = suggestion.get('suggested_value')
            if field and value:
                applied_fields[field] = value
                # Capture the entity for pattern matching
                if field == 'classified_entity':
                    entity_name = value

        conn.close()

        # If no entity was applied, we can't use TF-IDF matching
        if not entity_name:
            logging.warning(f"[TFIDF_MODAL] No entity in applied suggestions, cannot use TF-IDF matching")
            return jsonify({
                'similar_transactions': [],
                'applied_fields': applied_fields,
                'message': 'No entity classification applied'
            })

        #  NEW: Use TF-IDF system instead of Claude AI for finding similar transactions
        # This is 5x faster, more accurate, and uses learned patterns
        logging.info(f"[TFIDF_MODAL] Using TF-IDF system to find similar transactions for entity '{entity_name}'")

        # Extract wallet address for prioritization (if present)
        wallet_address = None
        if original.get('origin') and len(str(original.get('origin', ''))) > 20:
            wallet_address = str(original.get('origin', ''))
        elif original.get('destination') and len(str(original.get('destination', ''))) > 20:
            wallet_address = str(original.get('destination', ''))

        #  Call our new TF-IDF function to find similar transactions
        logging.info(f"[TFIDF_MODAL] Calling find_similar_with_tfidf_after_suggestion for entity '{entity_name}'")

        similar_transactions = find_similar_with_tfidf_after_suggestion(
            transaction_id=transaction_id,
            entity_name=entity_name,
            tenant_id=tenant_id,
            wallet_address=wallet_address,
            max_results=50
        )

        logging.info(f"[TFIDF_MODAL] Found {len(similar_transactions)} similar transactions using TF-IDF")

        return jsonify({
            'similar_transactions': similar_transactions,
            'applied_fields': applied_fields,
            'success': True
        })

    except Exception as e:
        print(f"ERROR: AI find similar transactions error: {e}", flush=True)
        print(f"ERROR TRACEBACK: {traceback.format_exc()}", flush=True)
        return jsonify({
            'error': f'Failed to find similar transactions: {str(e)}',
            'success': False
        }), 500

@app.route('/api/accounting_categories', methods=['GET'])
def api_get_accounting_categories():
    """API endpoint to fetch distinct accounting categories from database"""
    try:
        tenant_id = get_current_tenant_id()
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')

        # Get distinct accounting categories that are not NULL or 'N/A'
        query = """
            SELECT DISTINCT accounting_category
            FROM transactions
            WHERE tenant_id = %s
            AND accounting_category IS NOT NULL
            AND accounting_category != 'N/A'
            AND accounting_category != ''
            ORDER BY accounting_category
        """

        cursor.execute(query, (tenant_id,))
        rows = cursor.fetchall()
        conn.close()

        # Extract categories from rows
        if is_postgresql:
            categories = [row['accounting_category'] if isinstance(row, dict) else row[0] for row in rows]
        else:
            categories = [row[0] for row in rows]

        return jsonify({'categories': categories})

    except Exception as e:
        print(f"ERROR: Failed to fetch accounting categories: {e}", flush=True)
        return jsonify({'error': str(e), 'categories': []}), 500

@app.route('/api/subcategories', methods=['GET'])
def api_get_subcategories():
    """API endpoint to fetch distinct subcategories from database"""
    try:
        tenant_id = get_current_tenant_id()
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')

        # Get distinct subcategories that are not NULL or 'N/A'
        query = """
            SELECT DISTINCT subcategory
            FROM transactions
            WHERE tenant_id = %s
            AND subcategory IS NOT NULL
            AND subcategory != 'N/A'
            AND subcategory != ''
            ORDER BY subcategory
        """

        cursor.execute(query, (tenant_id,))
        rows = cursor.fetchall()
        conn.close()

        # Extract subcategories from rows
        if is_postgresql:
            subcategories = [row['subcategory'] if isinstance(row, dict) else row[0] for row in rows]
        else:
            subcategories = [row[0] for row in rows]

        return jsonify({'subcategories': subcategories})

    except Exception as e:
        logging.error(f"Failed to fetch subcategories: {e}")
        return jsonify({'error': str(e), 'subcategories': []}), 500

@app.route('/api/bulk_update_transactions', methods=['POST'])
def api_bulk_update_transactions():
    """
    API endpoint for Excel-like drag-down bulk updates

    Request body:
    {
        "updates": [
            {"transaction_id": "abc123", "field": "classified_entity", "value": "Infinity Validator"},
            {"transaction_id": "def456", "field": "classified_entity", "value": "Infinity Validator"},
            ...
        ]
    }

    Returns:
    {
        "success": true,
        "updated_count": 10,
        "failed_count": 0,
        "errors": []
    }
    """
    try:
        data = request.get_json()
        updates = data.get('updates', [])

        if not updates:
            return jsonify({'error': 'No updates provided', 'success': False}), 400

        if not isinstance(updates, list):
            return jsonify({'error': 'Updates must be an array', 'success': False}), 400

        updated_count = 0
        failed_count = 0
        errors = []

        # Process each update
        for idx, update in enumerate(updates):
            try:
                transaction_id = update.get('transaction_id')
                field = update.get('field')
                value = update.get('value')

                # Validate required fields
                if not all([transaction_id, field]):
                    errors.append({
                        'index': idx,
                        'transaction_id': transaction_id,
                        'error': 'Missing transaction_id or field'
                    })
                    failed_count += 1
                    continue

                # Call existing update function (returns tuple: (success: bool, confidence: float))
                result = update_transaction_field(transaction_id, field, value)

                # Handle tuple return value
                if isinstance(result, tuple):
                    success, confidence = result
                else:
                    # Fallback for unexpected return type
                    success = bool(result)

                if success:
                    updated_count += 1
                else:
                    failed_count += 1
                    errors.append({
                        'index': idx,
                        'transaction_id': transaction_id,
                        'error': 'Update failed - transaction not found or database error'
                    })

            except Exception as e:
                failed_count += 1
                errors.append({
                    'index': idx,
                    'transaction_id': update.get('transaction_id', 'unknown'),
                    'error': str(e)
                })
                logging.error(f"[BULK_UPDATE] Failed to update transaction {update.get('transaction_id')}: {e}")

        # Log summary
        logging.info(f"[BULK_UPDATE] Completed: {updated_count} succeeded, {failed_count} failed")

        return jsonify({
            'success': failed_count == 0,
            'updated_count': updated_count,
            'failed_count': failed_count,
            'errors': errors if errors else None
        })

    except Exception as e:
        logging.error(f"[BULK_UPDATE] Endpoint error: {e}")
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/update_similar_categories', methods=['POST'])
def api_update_similar_categories():
    """API endpoint to update accounting category for similar transactions"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        accounting_category = data.get('accounting_category')

        if not all([transaction_id, accounting_category]):
            return jsonify({'error': 'Missing required parameters'}), 400

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        # Get the original transaction to find similar ones
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'

        cursor.execute(f"SELECT * FROM transactions WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}", (tenant_id, transaction_id))
        original_row = cursor.fetchone()

        if not original_row:
            conn.close()
            return jsonify({'error': 'Transaction not found'}), 404

        original = dict(original_row)

        # Find similar transactions based on entity, description similarity, or same amount
        similar_transactions = []

        # Same entity
        if original.get('entity'):
            entity_rows = conn.execute(
                f"SELECT transaction_id FROM transactions WHERE tenant_id = {placeholder} AND entity = {placeholder} AND transaction_id != {placeholder}",
                (tenant_id, original['entity'], transaction_id)
            ).fetchall()
            similar_transactions.extend([row[0] for row in entity_rows])

        # Similar descriptions (containing same keywords)
        if original.get('description'):
            desc_words = [word.lower() for word in original['description'].split() if len(word) > 3]
            for word in desc_words[:2]:  # Check first 2 meaningful words
                not_in_clause = f"AND transaction_id NOT IN ({','.join([placeholder] * len(similar_transactions))})" if similar_transactions else ""
                desc_rows = conn.execute(
                    f"SELECT transaction_id FROM transactions WHERE tenant_id = {placeholder} AND LOWER(description) LIKE {placeholder} AND transaction_id != {placeholder} {not_in_clause}",
                    [tenant_id, f'%{word}%', transaction_id] + similar_transactions
                ).fetchall()
                similar_transactions.extend([row[0] for row in desc_rows])

        # Same amount (exact match)
        if original.get('amount'):
            not_in_clause = f"AND transaction_id NOT IN ({','.join([placeholder] * len(similar_transactions))})" if similar_transactions else ""
            amount_rows = conn.execute(
                f"SELECT transaction_id FROM transactions WHERE tenant_id = {placeholder} AND amount = {placeholder} AND transaction_id != {placeholder} {not_in_clause}",
                [tenant_id, original['amount'], transaction_id] + similar_transactions
            ).fetchall()
            similar_transactions.extend([row[0] for row in amount_rows])

        # Remove duplicates
        similar_transactions = list(set(similar_transactions))

        # Update all similar transactions
        updated_count = 0
        for similar_id in similar_transactions:
            success = update_transaction_field(similar_id, 'accounting_category', accounting_category)
            if success:
                updated_count += 1

        conn.close()

        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'message': f'Updated {updated_count} similar transactions'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_similar_descriptions', methods=['POST'])
def api_update_similar_descriptions():
    """API endpoint to update description for similar transactions"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        description = data.get('description')

        if not all([transaction_id, description]):
            return jsonify({'error': 'Missing required parameters'}), 400

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        # Get the original transaction to find similar ones
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'

        cursor.execute(f"SELECT * FROM transactions WHERE tenant_id = {placeholder} AND transaction_id = {placeholder}", (tenant_id, transaction_id))
        original_row = cursor.fetchone()

        if not original_row:
            conn.close()
            return jsonify({'error': 'Transaction not found'}), 404

        original = dict(original_row)

        # Find similar transactions based on entity, description similarity, or same amount
        similar_transactions = []

        # Same entity
        if original.get('entity'):
            entity_rows = conn.execute(
                f"SELECT transaction_id FROM transactions WHERE tenant_id = {placeholder} AND entity = {placeholder} AND transaction_id != {placeholder}",
                (tenant_id, original['entity'], transaction_id)
            ).fetchall()
            similar_transactions.extend([row[0] for row in entity_rows])

        # Similar descriptions (containing same keywords)
        if original.get('description'):
            desc_words = [word.lower() for word in original['description'].split() if len(word) > 3]
            for word in desc_words[:2]:  # Check first 2 meaningful words
                not_in_clause = f"AND transaction_id NOT IN ({','.join([placeholder] * len(similar_transactions))})" if similar_transactions else ""
                desc_rows = conn.execute(
                    f"SELECT transaction_id FROM transactions WHERE tenant_id = {placeholder} AND LOWER(description) LIKE {placeholder} AND transaction_id != {placeholder} {not_in_clause}",
                    [tenant_id, f'%{word}%', transaction_id] + similar_transactions
                ).fetchall()
                similar_transactions.extend([row[0] for row in desc_rows])

        # Same amount (exact match)
        if original.get('amount'):
            not_in_clause = f"AND transaction_id NOT IN ({','.join([placeholder] * len(similar_transactions))})" if similar_transactions else ""
            amount_rows = conn.execute(
                f"SELECT transaction_id FROM transactions WHERE tenant_id = {placeholder} AND amount = {placeholder} AND transaction_id != {placeholder} {not_in_clause}",
                [tenant_id, original['amount'], transaction_id] + similar_transactions
            ).fetchall()
            similar_transactions.extend([row[0] for row in amount_rows])

        # Remove duplicates
        similar_transactions = list(set(similar_transactions))

        # Update all similar transactions
        updated_count = 0
        for similar_id in similar_transactions:
            success = update_transaction_field(similar_id, 'description', description)
            if success:
                updated_count += 1

        conn.close()

        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'message': f'Updated {updated_count} similar transactions'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/whitelisted-accounts')
def whitelisted_accounts():
    """White Listed Accounts page - manage bank accounts and crypto wallets"""
    try:
        cache_buster = str(random.randint(1000, 9999))
        return render_template('whitelisted_accounts.html', cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading whitelisted accounts page: {str(e)}", 500

@app.route('/files')
def files_page():
    """Files management page - shows uploaded files grouped by account with gap detection"""
    try:
        from database import db_manager
        from datetime import datetime, timedelta
        from collections import defaultdict
        import re

        # Get current tenant ID
        from tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        # Get uploaded files with transaction counts (including archived) - filtered by tenant
        cursor.execute("""
            SELECT
                source_file,
                COUNT(*) as total_transactions,
                SUM(CASE WHEN archived = true THEN 1 ELSE 0 END) as archived_count,
                SUM(CASE WHEN archived = false THEN 1 ELSE 0 END) as active_count,
                MIN(date) as earliest_date,
                MAX(date) as latest_date,
                MAX(CASE WHEN archived = false THEN date ELSE NULL END) as latest_active_date
            FROM transactions
            WHERE source_file IS NOT NULL AND source_file != '' AND tenant_id = %s
            GROUP BY source_file
            ORDER BY MAX(date) DESC
        """, (tenant_id,))

        files_data = cursor.fetchall()
        conn.close()

        # Helper function to categorize account from filename
        def categorize_account(filename):
            """Enhanced account categorization supporting multiple account types"""
            account_id = None
            account_type = 'Unknown'
            account_category = 'Other'

            # Chase patterns (credit cards and checking)
            chase_match = re.search(r'Chase(\d{4})', filename, re.IGNORECASE)
            if chase_match:
                account_id = f"Chase-{chase_match.group(1)}"
                account_num = chase_match.group(1)
                # Known Chase credit card numbers
                if account_num in ['4774', '3687', '3911', '5893', '6134']:
                    account_type = f'Chase Credit Card ...{account_num}'
                    account_category = 'Credit Card'
                else:
                    account_type = f'Chase Checking ...{account_num}'
                    account_category = 'Checking'
                return account_id, account_type, account_category

            # Crypto wallet patterns (Coinbase, Binance, Kraken, etc.)
            crypto_patterns = [
                (r'coinbase', 'Coinbase Wallet'),
                (r'binance', 'Binance Account'),
                (r'kraken', 'Kraken Account'),
                (r'crypto', 'Crypto Wallet'),
                (r'btc|bitcoin', 'Bitcoin Wallet'),
                (r'eth|ethereum', 'Ethereum Wallet'),
            ]
            for pattern, name in crypto_patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    account_id = name.replace(' ', '-')
                    account_type = name
                    account_category = 'Crypto Wallet'
                    return account_id, account_type, account_category

            # Generic credit card patterns
            card_patterns = [
                (r'(?:visa|mastercard|amex|discover).*?(\d{4})', 'Credit Card'),
                (r'cc.*?(\d{4})', 'Credit Card'),
                (r'card.*?(\d{4})', 'Credit Card'),
            ]
            for pattern, card_type in card_patterns:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    last_four = match.group(1)
                    account_id = f"Card-{last_four}"
                    account_type = f'{card_type} ...{last_four}'
                    account_category = 'Credit Card'
                    return account_id, account_type, account_category

            # Generic checking account patterns
            checking_patterns = [
                (r'checking.*?(\d{4})', 'Checking'),
                (r'bank.*?(\d{4})', 'Bank Account'),
                (r'acct.*?(\d{4})', 'Account'),
            ]
            for pattern, acct_type in checking_patterns:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    last_four = match.group(1)
                    account_id = f"Checking-{last_four}"
                    account_type = f'{acct_type} ...{last_four}'
                    account_category = 'Checking'
                    return account_id, account_type, account_category

            # If no pattern matches, use filename as account
            account_id = 'Unknown'
            account_type = 'Unknown Account'
            account_category = 'Other'
            return account_id, account_type, account_category

        # Helper function to parse date range
        def parse_date_range(filename, earliest_txn, latest_txn):
            """Extract date range from filename or transaction dates"""
            date_pattern = re.search(r'(\d{8}).*?(\d{8})', filename)
            if date_pattern:
                try:
                    start = datetime.strptime(date_pattern.group(1), '%Y%m%d')
                    end = datetime.strptime(date_pattern.group(2), '%Y%m%d')
                    return start, end
                except:
                    pass

            # Fall back to transaction dates
            try:
                if isinstance(earliest_txn, str):
                    start = datetime.strptime(earliest_txn, '%Y-%m-%d')
                else:
                    start = earliest_txn

                if isinstance(latest_txn, str):
                    end = datetime.strptime(latest_txn, '%Y-%m-%d')
                else:
                    end = latest_txn

                return start, end
            except:
                return None, None

        # Process files and group by account
        accounts = defaultdict(list)

        for row in files_data:
            source_file, total_txns, archived_count, active_count, earliest, latest, latest_active = row

            # Categorize account
            account_id, account_type, account_category = categorize_account(source_file)

            # Parse dates
            start_date, end_date = parse_date_range(source_file, earliest, latest)

            file_info = {
                'name': source_file,
                'account_type': account_type,
                'account_category': account_category,
                'total_transactions': total_txns,
                'active_transactions': active_count,
                'archived_transactions': archived_count,
                'earliest_date': earliest,
                'latest_date': latest,
                'latest_active_date': latest_active,
                'start_date': start_date,
                'end_date': end_date,
                'start_date_str': start_date.strftime('%Y-%m-%d') if start_date else str(earliest),
                'end_date_str': end_date.strftime('%Y-%m-%d') if end_date else str(latest),
            }

            accounts[account_id].append(file_info)

        # Process each account group
        account_groups = []
        for account_id, files in accounts.items():
            # Sort files by start date
            files.sort(key=lambda f: f['start_date'] if f['start_date'] else datetime.min)

            # Detect gaps between files
            for i in range(len(files)):
                files[i]['gap_before'] = None
                if i > 0:
                    prev_end = files[i-1]['end_date']
                    curr_start = files[i]['start_date']

                    if prev_end and curr_start:
                        gap_days = (curr_start - prev_end).days - 1
                        if gap_days > 7:  # More than a week gap
                            gap_months = gap_days // 30
                            files[i]['gap_before'] = {
                                'days': gap_days,
                                'months': gap_months,
                                'from': prev_end.strftime('%Y-%m-%d'),
                                'to': curr_start.strftime('%Y-%m-%d')
                            }

            # Calculate account statistics
            total_files = len(files)
            total_txns = sum(f['total_transactions'] for f in files)
            active_txns = sum(f['active_transactions'] for f in files)
            archived_txns = sum(f['archived_transactions'] for f in files)

            # Get overall date range
            all_start_dates = [f['start_date'] for f in files if f['start_date']]
            all_end_dates = [f['end_date'] for f in files if f['end_date']]

            overall_start = min(all_start_dates) if all_start_dates else None
            overall_end = max(all_end_dates) if all_end_dates else None

            # Calculate coverage (days covered vs total span)
            total_days_covered = sum(
                (f['end_date'] - f['start_date']).days + 1
                for f in files if f['start_date'] and f['end_date']
            )

            total_span_days = None
            coverage_pct = None
            if overall_start and overall_end:
                total_span_days = (overall_end - overall_start).days + 1
                coverage_pct = (total_days_covered / total_span_days * 100) if total_span_days > 0 else 100

            account_groups.append({
                'id': account_id,
                'name': files[0]['account_type'],
                'category': files[0]['account_category'],
                'files': files,
                'total_files': total_files,
                'total_transactions': total_txns,
                'active_transactions': active_txns,
                'archived_transactions': archived_txns,
                'overall_start': overall_start.strftime('%Y-%m-%d') if overall_start else 'N/A',
                'overall_end': overall_end.strftime('%Y-%m-%d') if overall_end else 'N/A',
                'coverage_pct': round(coverage_pct, 1) if coverage_pct else None,
                'has_gaps': any(f.get('gap_before') for f in files)
            })

        # Sort account groups by category then name
        category_order = {'Checking': 1, 'Credit Card': 2, 'Crypto Wallet': 3, 'Other': 4}
        account_groups.sort(key=lambda g: (category_order.get(g['category'], 99), g['name']))

        return render_template('files.html', account_groups=account_groups)
    except Exception as e:
        print(f"ERROR in files_page: {e}")
        import traceback
        traceback.print_exc()
        return f"Error loading files: {str(e)}", 500

def check_processed_file_duplicates(processed_filepath, original_filepath, tenant_id=None, include_all_duplicates=False):
    """
    Check if PROCESSED file contains transactions that already exist in database
    This runs AFTER smart ingestion to check enriched transactions
    Returns detailed duplicate information for user decision

    Args:
        processed_filepath: Path to processed file
        original_filepath: Path to original uploaded file
        tenant_id: Tenant identifier for multi-tenant isolation (defaults to current tenant)
        include_all_duplicates: If True, return ALL duplicates instead of just first 10 (for deletion)
    """
    try:
        # Get tenant_id from context if not provided
        if tenant_id is None:
            tenant_id = get_current_tenant_id()

        print(f" Checking duplicates for tenant: {tenant_id}")

        # Find the CLASSIFIED CSV file (this has enriched data from smart ingestion)
        # Go up one level from web_ui to DeltaCFOAgentv2 root directory
        base_dir = os.path.dirname(os.getcwd())
        filename = os.path.basename(original_filepath)
        classified_file = os.path.join(base_dir, 'classified_transactions', f'classified_{filename}')

        if os.path.exists(classified_file):
            processed_file = classified_file
            print(f" Using classified file for duplicate check: {classified_file}")
        else:
            print(f" Classified file not found: {classified_file}, using original")
            processed_file = processed_filepath

        df = pd.read_csv(processed_file)
        original_count = len(df)
        print(f" Loaded {original_count} transactions from file")
        print(f" CSV columns: {list(df.columns)}")

        # Step 1: Deduplicate within the file itself first
        # Keep only the LAST occurrence of each duplicate (most recent data)
        # Use only columns that actually exist in the CSV
        dedup_columns = []
        for col in ['Date', 'Description', 'Amount', 'Currency']:
            if col in df.columns:
                dedup_columns.append(col)

        if dedup_columns:
            print(f" Using columns for deduplication: {dedup_columns}")
            df_deduplicated = df.drop_duplicates(
                subset=dedup_columns,
                keep='last'
            )

            file_duplicates_removed = original_count - len(df_deduplicated)
            if file_duplicates_removed > 0:
                print(f" Removed {file_duplicates_removed} duplicate rows within the file itself (keeping latest)")
                df = df_deduplicated
        else:
            print(f" Warning: None of the standard deduplication columns found, skipping file-level deduplication")

        print(f" Checking {len(df)} unique transactions against database for duplicates")

        from database import db_manager
        with db_manager.get_connection() as conn:
            if db_manager.db_type == 'postgresql':
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                cursor = conn.cursor()

            duplicates = []
            new_transactions = []

            for index, row in df.iterrows():
                # Parse date to consistent format
                date_str = str(row.get('Date', ''))

                # Skip if date is missing or invalid
                if not date_str or date_str == 'nan' or date_str == 'None':
                    print(f" Skipping row {index + 1} - missing date")
                    continue

                # Extract just the date part (YYYY-MM-DD)
                if 'T' in date_str:
                    date_str = date_str.split('T')[0]
                elif ' ' in date_str:
                    date_str = date_str.split(' ')[0]

                # Convert date to YYYY-MM-DD format if needed
                # Handle MM/DD/YYYY format from classified files
                if '/' in date_str:
                    try:
                        from datetime import datetime
                        # Parse MM/DD/YYYY and convert to YYYY-MM-DD
                        date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                        date_str = date_obj.strftime('%Y-%m-%d')
                    except ValueError:
                        print(f" Skipping row {index + 1} - invalid date format: {date_str}")
                        continue

                # Validate date format (should be YYYY-MM-DD now)
                if not date_str or len(date_str) < 8 or '-' not in date_str:
                    print(f" Skipping row {index + 1} - invalid date format: {date_str}")
                    continue

                description = str(row.get('Description', ''))
                try:
                    amount = float(row.get('Amount', 0))
                except (ValueError, TypeError):
                    print(f" Skipping row {index + 1} - invalid amount")
                    continue

                # Determine if this is a crypto transaction
                currency = str(row.get('Currency', 'USD')).upper()
                crypto_currencies = ['BTC', 'ETH', 'TAO', 'USDT', 'USDC', 'BNB', 'SOL', 'ADA', 'XRP', 'DOT', 'MATIC', 'AVAX', 'LINK']
                is_crypto = currency in crypto_currencies

                # Set tolerance based on transaction type
                # Crypto: Allow 0.75% variance due to exchange rate fluctuations
                # Fiat: Require exact match (0.01 cent tolerance for rounding)
                if is_crypto:
                    tolerance_pct = 0.0075  # 0.75% variance allowed
                    amount_tolerance = abs(amount) * tolerance_pct
                    print(f" CRYPTO Row {index + 1}: Crypto transaction ({currency}) - allowing {tolerance_pct*100}% variance (±${amount_tolerance:.2f})")
                else:
                    amount_tolerance = 0.01  # Exact match for fiat (1 cent tolerance)
                    print(f" Row {index + 1}: Fiat transaction - requiring exact match (±$0.01)")

                # Check for match: same tenant, same date, similar amount (tolerance based on type), same currency
                # NOTE: Removed LIMIT 1 to find ALL duplicate instances (e.g., if file uploaded multiple times)
                # NOTE: Removed description matching to avoid missing duplicates when description changes between uploads
                try:
                    if db_manager.db_type == 'postgresql':
                        query = """
                            SELECT transaction_id, date, description, amount, currency,
                                   classified_entity, accounting_category, confidence,
                                   origin, destination
                            FROM transactions
                            WHERE tenant_id = %s
                              AND DATE(date) = %s
                              AND ABS(amount - %s) <= %s
                              AND currency = %s
                        """
                        cursor.execute(query, (tenant_id, date_str, amount, amount_tolerance, currency))
                    else:
                        query = """
                            SELECT transaction_id, date, description, amount, currency,
                                   classified_entity, accounting_category, confidence,
                                   origin, destination
                            FROM transactions
                            WHERE tenant_id = ?
                              AND DATE(date) = ?
                              AND ABS(amount - ?) <= ?
                              AND currency = ?
                        """
                        cursor.execute(query, (tenant_id, date_str, amount, amount_tolerance, currency))

                    existing_matches = cursor.fetchall()
                except Exception as query_error:
                    print(f" Error querying row {index + 1}: {query_error}")
                    # Rollback the transaction to clear PostgreSQL error state
                    if db_manager.db_type == 'postgresql':
                        conn.rollback()
                    existing_matches = []

                # Base transaction data
                transaction_data = {
                    'file_row': index + 1,
                    'date': date_str,
                    'description': description,
                    'amount': amount,
                    'new_entity': row.get('classified_entity', 'Unknown'),
                    'new_category': row.get('accounting_category', 'Unknown'),
                    'new_confidence': row.get('confidence', 0),
                    'origin': row.get('Origin', ''),
                    'destination': row.get('Destination', ''),
                    'currency': currency,
                    'is_crypto': is_crypto
                }

                if existing_matches and len(existing_matches) > 0:
                    # Found duplicate(s) - create an entry for EACH match
                    # This handles cases where the same file was uploaded multiple times
                    if len(existing_matches) > 1:
                        print(f"    Found {len(existing_matches)} duplicate instances in database")

                    # Track if we found any TRUE duplicates (not inter-company transfers)
                    found_true_duplicate = False

                    for existing in existing_matches:
                        # INTER-COMPANY TRANSFER DETECTION
                        # Check if this is an inter-company transfer instead of a true duplicate
                        # Transfers have: same date, similar amount, same currency BUT opposite signs or directions

                        old_origin = str(existing.get('origin', '')).strip() if existing.get('origin') else ''
                        old_destination = str(existing.get('destination', '')).strip() if existing.get('destination') else ''
                        new_origin = str(row.get('Origin', '')).strip()
                        new_destination = str(row.get('Destination', '')).strip()

                        old_amount = float(existing['amount'])  # Convert Decimal to float if PostgreSQL
                        new_amount = amount

                        # Check if amounts have opposite signs (one negative, one positive)
                        # This is the primary indicator of inter-company transfer
                        is_opposite_signs = (old_amount > 0 and new_amount < 0) or (old_amount < 0 and new_amount > 0)

                        # Check if Origin/Destination indicate different flow directions
                        # (optional secondary check for when both have Origin/Destination data)
                        # IMPORTANT: Only check if we have MEANINGFUL data (not Unknown, not empty)
                        is_reversed_flow = False
                        has_meaningful_origin_dest = (
                            old_origin and old_destination and new_origin and new_destination and
                            old_origin.lower() not in ['unknown', 'n/a', ''] and
                            old_destination.lower() not in ['unknown', 'n/a', ''] and
                            new_origin.lower() not in ['unknown', 'n/a', ''] and
                            new_destination.lower() not in ['unknown', 'n/a', '']
                        )

                        if has_meaningful_origin_dest:
                            # Check if the flow is reversed (A→B vs B→A)
                            # Only use the first condition - actual reversed flow
                            is_reversed_flow = (old_origin == new_destination and old_destination == new_origin)

                        # If either indicator suggests inter-company transfer, skip duplicate detection
                        if is_opposite_signs or is_reversed_flow:
                            print(f"    Row {index + 1}: Detected INTER-COMPANY TRANSFER (not duplicate)")
                            print(f"      Existing: {old_amount:+.2f} {currency} | {old_origin or 'N/A'} -> {old_destination or 'N/A'}")
                            print(f"      New:      {new_amount:+.2f} {currency} | {new_origin or 'N/A'} -> {new_destination or 'N/A'}")
                            print(f"      Reason: {'Opposite signs' if is_opposite_signs else 'Reversed flow'}")
                            # Skip this match - don't add to duplicates list
                            # But we need to break out of the existing_matches loop, not continue the outer loop
                            # This match isn't a duplicate, but we still need to check other potential matches
                            continue

                        # If we reach here, it's a TRUE DUPLICATE (same direction, same sign)
                        # Create a copy of transaction_data for each duplicate
                        dup_data = transaction_data.copy()

                        if db_manager.db_type == 'postgresql':
                            old_amount = float(existing['amount'])  # Convert Decimal to float
                            old_currency = existing.get('currency', 'USD')
                            amount_diff = abs(amount - old_amount)
                            amount_diff_pct = (amount_diff / abs(old_amount)) * 100 if old_amount != 0 else 0

                            dup_data.update({
                                'is_duplicate': True,
                                'existing_id': existing['transaction_id'],
                                'old_entity': existing['classified_entity'],
                                'old_category': existing['accounting_category'],
                                'old_confidence': existing['confidence'],
                                'old_amount': old_amount,
                                'old_currency': old_currency,
                                'amount_diff': amount_diff,
                                'amount_diff_pct': amount_diff_pct
                            })
                        else:
                            old_amount = existing[3]
                            old_currency = existing[4] if len(existing) > 4 else 'USD'
                            amount_diff = abs(amount - old_amount)
                            amount_diff_pct = (amount_diff / abs(old_amount)) * 100 if old_amount != 0 else 0

                            dup_data.update({
                                'is_duplicate': True,
                                'existing_id': existing[0],
                                'old_entity': existing[5] if len(existing) > 5 else 'Unknown',
                                'old_category': existing[6] if len(existing) > 6 else 'Unknown',
                                'old_confidence': existing[7] if len(existing) > 7 else 0,
                                'old_amount': old_amount,
                                'old_currency': old_currency,
                                'amount_diff': amount_diff,
                                'amount_diff_pct': amount_diff_pct
                            })
                        duplicates.append(dup_data)
                        found_true_duplicate = True

                    # After checking all matches, if none were TRUE duplicates (all were inter-company transfers)
                    # then this transaction is NEW
                    if not found_true_duplicate:
                        print(f"    Row {index + 1}: All matches were inter-company transfers - treating as NEW transaction")
                        transaction_data['is_duplicate'] = False
                        new_transactions.append(transaction_data)
                else:
                    # No matches at all - it's new
                    transaction_data['is_duplicate'] = False
                    new_transactions.append(transaction_data)

        result = {
            'has_duplicates': len(duplicates) > 0,
            'duplicate_count': len(duplicates),
            'new_count': len(new_transactions),
            'total_transactions': len(df),
            'duplicates': duplicates,  # Return ALL duplicates - user can scroll through them in the modal
            'processed_file': processed_file,
            'original_file': original_filepath
        }

        print(f" Duplicate check: {len(duplicates)} duplicates, {len(new_transactions)} new transactions")
        return result

    except Exception as e:
        print(f" Error checking duplicates: {e}")
        import traceback
        traceback.print_exc()
        return {
            'has_duplicates': False,
            'duplicate_count': 0,
            'new_count': 0,
            'total_transactions': 0,
            'duplicates': []
        }

def check_file_duplicates(filepath):
    """Legacy function - kept for backwards compatibility"""
    return check_processed_file_duplicates(filepath, filepath)


def convert_currency_to_usd(amount: float, from_currency: str) -> tuple:
    """
    Convert amount from given currency to USD

    Returns:
        tuple: (usd_amount, original_currency, conversion_note)
    """
    # If already USD, return as-is
    if from_currency == 'USD':
        return (amount, 'USD', None)

    # Simple conversion rates (you can replace with live API later)
    # These are approximate rates as of 2025
    EXCHANGE_RATES = {
        'BRL': 0.20,   # Brazilian Real to USD
        'EUR': 1.10,   # Euro to USD
        'GBP': 1.27,   # British Pound to USD
        'CAD': 0.73,   # Canadian Dollar to USD
        'MXN': 0.055,  # Mexican Peso to USD
        'JPY': 0.0071, # Japanese Yen to USD
        'CNY': 0.14,   # Chinese Yuan to USD
        'INR': 0.012,  # Indian Rupee to USD
        'AUD': 0.65,   # Australian Dollar to USD
    }

    rate = EXCHANGE_RATES.get(from_currency.upper())
    if rate is None:
        # Unknown currency - log warning and return original
        print(f"  Unknown currency '{from_currency}' - storing in original currency")
        return (amount, from_currency, f"Unknown currency - no conversion applied")

    usd_amount = amount * rate
    conversion_note = f"Converted from {from_currency} at rate {rate}"
    print(f" Currency conversion: {amount} {from_currency} = ${usd_amount:.2f} USD (rate: {rate})")

    return (usd_amount, from_currency, conversion_note)


def process_pdf_with_claude_vision(filepath: str, filename: str) -> Dict[str, Any]:
    """
    Process PDF using Claude Vision to extract transaction data
    Uses PyMuPDF (same as invoice processing) for PDF conversion

    Args:
        filepath: Full path to the PDF file
        filename: Original filename

    Returns:
        Dict containing extracted transactions or error information
    """
    try:
        print(f" Processing PDF with Claude Vision: {filename}")

        # Convert PDF to image using PyMuPDF (same method as invoices)
        try:
            import fitz  # PyMuPDF

            # Open PDF and get first page
            doc = fitz.open(filepath)
            if doc.page_count == 0:
                raise ValueError("PDF has no pages")

            # Get first page as image with 2x zoom for better quality
            page = doc.load_page(0)
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)

            # Convert to PNG bytes
            image_bytes = pix.pil_tobytes(format="PNG")
            doc.close()

            # Encode to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        except ImportError:
            raise ValueError("PyMuPDF not installed. Run: pip install PyMuPDF")
        except Exception as e:
            raise ValueError(f"PDF conversion failed: {str(e)}")

        print(f" PDF converted to image successfully ({len(image_base64)} bytes)")

        # Get Anthropic API key
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        # Initialize Claude client
        client = anthropic.Anthropic(api_key=api_key)

        # Extraction prompt for financial transactions
        prompt = """
Analyze this document and extract ALL transaction data you can find.

This could be:
- Bank statement with multiple transactions
- Invoice with line items
- Receipt with transaction details
- Financial report with transaction history
- Credit card statement

CRITICAL - Currency Detection:
- Carefully identify the currency used in the document
- Look for currency symbols (R$, $, €, £, etc.), currency codes (BRL, USD, EUR, GBP, etc.), or written currency names
- Common currencies: BRL (Brazilian Real), USD (US Dollar), EUR (Euro), GBP (British Pound)
- If the document mentions "Real", "Reais", or shows "R$", the currency is BRL
- The currency MUST be specified for EVERY transaction

For EACH transaction, extract:
- date (in YYYY-MM-DD format, required)
- description (transaction description, required)
- amount (numeric value - use negative for expenses/debits, positive for income/credits, required)
- currency (ISO currency code like BRL, USD, EUR - required)
- category (expense category if mentioned, optional)
- entity (business unit or entity name if mentioned, optional)

Return ONLY valid JSON in this exact format:
{
    "currency": "BRL",
    "transactions": [
        {
            "date": "2024-01-15",
            "description": "Office supplies purchase",
            "amount": -150.50,
            "currency": "BRL",
            "category": "Technology",
            "entity": "Delta LLC"
        }
    ],
    "total_found": 1,
    "document_type": "Bank Statement"
}

Important:
- Extract ALL transactions from the document
- ALWAYS specify the currency for each transaction
- Use negative amounts for expenses/debits
- Use positive amounts for income/credits
- If date format is unclear, use best estimate in YYYY-MM-DD
- Return empty array if no transactions found
- The top-level "currency" field should be the default currency for all transactions in the document
"""

        print(f" Calling Claude Vision API...")

        # Call Claude Vision API
        response = client.messages.create(
            model="claude-3-haiku-20240307",  # Fast model for vision tasks
            max_tokens=4000,
            temperature=0.1,  # Low temperature for structured data
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )

        # Parse response
        response_text = response.content[0].text.strip()
        print(f" Received response from Claude ({len(response_text)} chars)")

        # Remove markdown code blocks if present
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        elif response_text.startswith('```'):
            response_text = response_text.replace('```', '').strip()

        # Parse JSON
        result = json.loads(response_text)

        # Debug: Show what currency Claude detected
        detected_currency = result.get('currency', 'NOT FOUND')
        print(f" DEBUG: Claude detected document currency: '{detected_currency}'")
        if result.get('transactions'):
            first_txn_currency = result['transactions'][0].get('currency', 'NOT FOUND')
            print(f" DEBUG: First transaction currency: '{first_txn_currency}'")

        print(f" Successfully extracted {result.get('total_found', 0)} transactions from PDF")

        return result

    except ImportError as e:
        error_msg = f"PDF processing libraries not available: {e}. Install with: pip install pdf2image Pillow"
        print(f" {error_msg}")
        return {"error": error_msg, "transactions": [], "total_found": 0}
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON response from Claude Vision: {e}"
        print(f" {error_msg}")
        print(f"Raw response: {response_text[:500]}...")
        return {"error": error_msg, "transactions": [], "total_found": 0}
    except Exception as e:
        error_str = str(e)
        # Check if this is a poppler-related error
        if "poppler" in error_str.lower() or "Unable to get page count" in error_str:
            error_msg = (
                "Poppler is not installed or not in PATH. "
                "PDF upload requires Poppler to convert PDF to images. "
                "Download from: https://github.com/oschwartz10612/poppler-windows/releases/ "
                "and add the bin folder to your PATH environment variable. "
                "CSV uploads will continue to work normally."
            )
        else:
            error_msg = f"PDF processing failed: {error_str}"
        print(f" {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        return {"error": error_msg, "transactions": [], "total_found": 0}


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing"""
    import sys
    sys.stderr.write("=" * 80 + "\n")
    sys.stderr.write("UPLOAD ENDPOINT HIT - Starting file upload processing\n")
    sys.stderr.write("=" * 80 + "\n")
    sys.stderr.flush()
    logger.info("UPLOAD ENDPOINT HIT - Starting file upload processing")
    try:
        print("DEBUG: Checking for file in request...")
        if 'file' not in request.files:
            print("ERROR: No file in request")
            return jsonify({'error': 'No file provided'}), 400

        print("DEBUG: Getting file from request...")
        file = request.files['file']
        print(f"DEBUG: File received: {file.filename}")

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Check file extension - accept CSV and PDF
        print("DEBUG: Checking file extension...")
        allowed_extensions = ['.csv', '.pdf']
        file_ext = os.path.splitext(file.filename.lower())[1]
        print(f"DEBUG: File extension: {file_ext}")

        if file_ext not in allowed_extensions:
            return jsonify({'error': 'Only CSV and PDF files are allowed'}), 400

        # Secure the filename
        print("DEBUG: Securing filename...")
        filename = secure_filename(file.filename)
        print(f"DEBUG: Secured filename: {filename}")

        # Save to parent directory (same location as other CSV files)
        print("DEBUG: Getting parent directory...")
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        print(f"DEBUG: Parent dir: {parent_dir}")
        filepath = os.path.join(parent_dir, filename)
        print(f"DEBUG: Full filepath: {filepath}")

        # Save the uploaded file
        file.save(filepath)

        # Debug: Show file extension detection
        print(f"DEBUG: File extension detected: '{file_ext}' for file: {filename}")

        # Check if PDF and process differently
        if file_ext == '.pdf':
            print(f"PDF file detected: {filename}")
            print(f"DEBUG: Processing PDF with Claude Vision...")

            # Process PDF with Claude Vision
            pdf_result = process_pdf_with_claude_vision(filepath, filename)

            # Check for errors
            if pdf_result.get('error'):
                # Clean up uploaded file
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({
                    'success': False,
                    'error': f"PDF processing failed: {pdf_result['error']}"
                }), 500

            # Check if transactions were found
            transactions = pdf_result.get('transactions', [])
            if not transactions:
                # Clean up uploaded file
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({
                    'success': False,
                    'error': 'No transactions found in PDF'
                }), 400

            # Insert transactions into database
            print(f"Inserting {len(transactions)} transactions into database...")
            from database import db_manager
            tenant_id = get_current_tenant_id()
            inserted_count = 0

            try:
                # Get document-level currency (fallback if individual transaction doesn't have one)
                document_currency = pdf_result.get('currency', 'USD')
                print(f" DEBUG: Document-level currency from pdf_result: '{document_currency}'")

                skipped_duplicates = 0
                for txn in transactions:
                    # Get transaction data
                    txn_currency = txn.get('currency', document_currency)
                    original_amount = txn.get('amount')
                    txn_date = txn.get('date')
                    txn_description = txn.get('description')

                    print(f" DEBUG: About to convert: amount={original_amount}, from_currency={txn_currency}")

                    # Convert currency to USD
                    usd_amount, original_currency, conversion_note = convert_currency_to_usd(
                        original_amount,
                        txn_currency
                    )

                    # Check for duplicates: same date, description, and amount
                    existing = db_manager.execute_query("""
                        SELECT transaction_id FROM transactions
                        WHERE tenant_id = %s
                          AND date = %s
                          AND description = %s
                          AND ABS(amount - %s) < 0.01
                        LIMIT 1
                    """, (tenant_id, txn_date, txn_description, usd_amount), fetch_one=True)

                    if existing:
                        print(f"DUPLICATE SKIPPED: {txn_date} | {txn_description} | ${usd_amount}")
                        skipped_duplicates += 1
                        continue

                    # Generate transaction ID
                    transaction_id = str(uuid.uuid4())

                    # Insert into database
                    db_manager.execute_query("""
                        INSERT INTO transactions (
                            transaction_id, tenant_id, date, description, amount,
                            currency, usd_equivalent, conversion_note,
                            classified_entity, accounting_category, subcategory,
                            confidence, source_file
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        transaction_id,
                        tenant_id,
                        txn_date,
                        txn_description,
                        usd_amount,  # Amount in USD
                        original_currency,  # Original currency
                        usd_amount if original_currency != 'USD' else None,  # USD equivalent (only if converted)
                        conversion_note,  # Conversion details
                        txn.get('entity', 'Unknown'),
                        txn.get('category', 'Uncategorized'),
                        None,  # subcategory
                        0.8,  # High confidence from Claude Vision
                        f'PDF Upload: {filename}'
                    ))
                    inserted_count += 1

                print(f" Successfully inserted {inserted_count} transactions")

            except Exception as e:
                print(f" Database insertion error: {e}")
                logger.error(f"Failed to insert PDF transactions: {e}", exc_info=True)
                # Clean up uploaded file
                if os.path.exists(filepath):
                    os.remove(filepath)
                return jsonify({
                    'success': False,
                    'error': f'Database insertion failed: {str(e)}'
                }), 500

            # Success! Clean up the PDF file (data already extracted and saved)
            if os.path.exists(filepath):
                os.remove(filepath)

            print(f" Successfully processed PDF: {inserted_count} transactions saved to database")
            return jsonify({
                'success': True,
                'message': f'Successfully extracted and saved {inserted_count} transaction(s) from PDF',
                'transactions_processed': inserted_count,
                'document_type': pdf_result.get('document_type', 'PDF Document'),
                'transactions': transactions
            })

        # Create backup first
        backup_path = f"{filepath}.backup"
        shutil.copy2(filepath, backup_path)

        # STEP 1: Process file with smart ingestion FIRST (always process to get latest business logic)
        print(f" DEBUG: Step 1 - Processing file with smart ingestion: {filename}")

        # Process the file to get enriched transactions
        try:
            # Use a subprocess to run the processing in a separate Python instance
            # Convert Windows backslashes to forward slashes (works on all platforms)
            parent_dir_safe = parent_dir.replace(chr(92), '/')
            filename_safe = filename.replace(chr(92), '/')
            
            processing_script = f"""
import sys
import os
sys.path.append('{parent_dir_safe}')
os.chdir('{parent_dir_safe}')

from main import DeltaCFOAgent

agent = DeltaCFOAgent()
result = agent.process_file('{filename_safe}', enhance=True, use_smart_ingestion=True)

if result is not None:
    print(f'PROCESSED_COUNT:{{len(result)}}')
else:
    print('PROCESSED_COUNT:0')
"""

            # Run the processing script with environment variables
            env = os.environ.copy()
            env['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', '')
            # Ensure database environment variables are passed through
            if os.getenv('DB_TYPE'):
                env['DB_TYPE'] = os.getenv('DB_TYPE')
            if os.getenv('DB_HOST'):
                env['DB_HOST'] = os.getenv('DB_HOST')
            if os.getenv('DB_PORT'):
                env['DB_PORT'] = os.getenv('DB_PORT')
            if os.getenv('DB_NAME'):
                env['DB_NAME'] = os.getenv('DB_NAME')
            if os.getenv('DB_USER'):
                env['DB_USER'] = os.getenv('DB_USER')
            if os.getenv('DB_PASSWORD'):
                env['DB_PASSWORD'] = os.getenv('DB_PASSWORD')

            print(f" DEBUG: Running subprocess for {filename}")
            print(f" DEBUG: API key set: {'Yes' if env.get('ANTHROPIC_API_KEY') else 'No'}")
            print(f" DEBUG: Working directory: {parent_dir}")
            print(f" DEBUG: Processing script length: {len(processing_script)}")

            process_result = subprocess.run(
                [sys.executable, '-c', processing_script],
                capture_output=True,
                text=True,
                cwd=parent_dir,
                timeout=120,  # Increase timeout to 2 minutes
                env=env
            )

            print(f" DEBUG: Subprocess return code: {process_result.returncode}")
            print(f" DEBUG: Subprocess stdout length: {len(process_result.stdout)}")
            print(f" DEBUG: Subprocess stderr length: {len(process_result.stderr)}")

            # Always print subprocess output for debugging
            print(f" DEBUG: Subprocess stdout:\n{process_result.stdout}")
            if process_result.stderr:
                print(f" DEBUG: Subprocess stderr:\n{process_result.stderr}")

            # Check for specific error patterns
            if process_result.returncode != 0:
                print(f"[ERROR] DEBUG: Subprocess failed with return code {process_result.returncode}")
                if "claude" in process_result.stderr.lower() or "anthropic" in process_result.stderr.lower():
                    print(" DEBUG: Detected Claude/Anthropic related error")
                if "import" in process_result.stderr.lower():
                    print(" DEBUG: Detected import error")
                if "timeout" in process_result.stderr.lower():
                    print(" DEBUG: Detected timeout error")

            # Extract transaction count from output
            transactions_processed = 0
            if 'PROCESSED_COUNT:' in process_result.stdout:
                count_str = process_result.stdout.split('PROCESSED_COUNT:')[1].split('\n')[0]
                try:
                    transactions_processed = int(count_str)
                    print(f" DEBUG: Extracted transaction count: {transactions_processed}")
                except ValueError as e:
                    print(f" DEBUG: Failed to parse transaction count '{count_str}': {e}")

            # If subprocess failed, return the error immediately
            if process_result.returncode != 0:
                return jsonify({
                    'success': False,
                    'error': f'Classification failed: {process_result.stderr or "Unknown subprocess error"}',
                    'subprocess_stdout': process_result.stdout,
                    'subprocess_stderr': process_result.stderr,
                    'return_code': process_result.returncode
                }), 500

            # STEP 2: Check for duplicates in processed file BEFORE syncing to database
            print(f" DEBUG: Step 2 - Checking for duplicates in processed file...")
            duplicate_info = check_processed_file_duplicates(filepath, filename)

            if duplicate_info['has_duplicates']:
                print(f" Found {duplicate_info['duplicate_count']} duplicates, presenting options to user")

                # Convert numpy/decimal types to native Python types for JSON serialization
                def sanitize_for_json(obj):
                    """Convert numpy and decimal types to JSON-serializable types"""
                    import numpy as np
                    from decimal import Decimal

                    if isinstance(obj, dict):
                        return {k: sanitize_for_json(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [sanitize_for_json(item) for item in obj]
                    elif isinstance(obj, (np.integer, np.floating)):
                        return float(obj)
                    elif isinstance(obj, Decimal):
                        return float(obj)
                    elif isinstance(obj, np.ndarray):
                        return obj.tolist()
                    else:
                        return obj

                # Sanitize duplicate_info for JSON serialization
                sanitized_duplicate_info = sanitize_for_json(duplicate_info)

                # Store processed file info in session for later resolution
                session['pending_upload'] = {
                    'filename': filename,
                    'filepath': filepath,
                    'processed_file': duplicate_info.get('processed_file'),
                    'duplicate_info': sanitized_duplicate_info,
                    'transactions_processed': transactions_processed
                }
                return jsonify({
                    'success': False,
                    'duplicate_confirmation_needed': True,
                    'duplicate_info': sanitized_duplicate_info,
                    'message': f'Found {duplicate_info["duplicate_count"]} duplicate transactions. {duplicate_info["new_count"]} new transactions found.'
                })

            # STEP 3: No duplicates, proceed with database sync
            print(f" DEBUG: No duplicates found, starting database sync for {filename}...")
            sync_result = sync_csv_to_database(filename)
            print(f" DEBUG: Database sync result: {sync_result}")

            if sync_result:
                # Auto-trigger revenue matching after successful transaction upload
                try:
                    print(f" AUTO-TRIGGER: Starting automatic revenue matching...")
                    from robust_revenue_matcher import RobustRevenueInvoiceMatcher

                    matcher = RobustRevenueInvoiceMatcher()
                    matches_result = matcher.run_robust_matching(auto_apply=False)

                    if matches_result and matches_result.get('matches_found', 0) > 0:
                        print(f" AUTO-TRIGGER: Found {matches_result['matches_found']} new matches automatically!")
                    else:
                        print("ℹ AUTO-TRIGGER: No new matches found after transaction upload")

                except Exception as e:
                    print(f" AUTO-TRIGGER: Error during automatic matching: {e}")
                    # Don't fail the upload if matching fails

                return jsonify({
                    'success': True,
                    'message': f'Successfully processed {filename}',
                    'transactions_processed': transactions_processed,
                    'sync_result': sync_result
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Processing succeeded but database sync failed',
                    'transactions_processed': transactions_processed,
                    'subprocess_stdout': process_result.stdout,
                    'subprocess_stderr': process_result.stderr
                }), 500

        except subprocess.TimeoutExpired:
            return jsonify({
                'success': False,
                'error': 'Processing timeout - file too large or complex'
            }), 500
        except Exception as processing_error:
            error_details = traceback.format_exc()
            return jsonify({
                'success': False,
                'error': f'Processing failed: {str(processing_error)}',
                'details': error_details
            }), 500

    except Exception as e:
        import sys
        error_msg = f"FATAL ERROR in upload_file: {e}"
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write(error_msg + "\n")
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write(traceback.format_exc() + "\n")
        sys.stderr.flush()
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/upload/test', methods=['GET'])
def test_upload_endpoint():
    """Test endpoint to verify server version"""
    from datetime import datetime
    return jsonify({
        'message': 'Upload endpoint is active and updated',
        'version': '2.0_crypto_duplicates',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/upload/resolve-duplicates', methods=['POST'])
def resolve_duplicates():
    """Handle user's decision on duplicate transactions"""
    try:
        data = request.json
        action = data.get('action')  # 'overwrite' or 'discard'

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        # Retrieve pending upload info from session
        pending = session.get('pending_upload')
        if not pending:
            return jsonify({
                'success': False,
                'error': 'No pending upload found. Please upload the file again.'
            }), 400

        filename = pending['filename']
        processed_file = pending.get('processed_file')
        duplicate_info = pending['duplicate_info']

        print(f" DEBUG: Resolving duplicates with action: {action}")
        print(f" DEBUG: File: {filename}, Duplicates: {duplicate_info['duplicate_count']}")

        if action == 'overwrite':
            # OVERWRITE: Delete old duplicates and insert new enriched data
            # Support selective overwrite based on user selection
            selected_indices = data.get('selected_indices', [])
            modifications = data.get('modifications', {})

            from database import db_manager

            # Step 1: Determine which duplicates to delete
            duplicate_ids = []
            if selected_indices:
                # User selected specific transactions - only delete those
                print(f" User chose to OVERWRITE {len(selected_indices)} selected duplicates")
                all_duplicates = duplicate_info.get('duplicates', [])
                for idx in selected_indices:
                    if 0 <= idx < len(all_duplicates):
                        duplicate_ids.append(all_duplicates[idx]['existing_id'])
            else:
                # No selection provided - overwrite ALL duplicates (legacy behavior)
                print(f" User chose to OVERWRITE ALL {duplicate_info['duplicate_count']} duplicates with latest business knowledge")
                duplicate_ids = [dup['existing_id'] for dup in duplicate_info.get('duplicates', [])]

            if duplicate_ids:
                # Get ALL duplicate IDs for selected transactions
                # Re-run the check to get all IDs with include_all_duplicates=True
                full_check = check_processed_file_duplicates(pending['filepath'], filename, include_all_duplicates=True)
                all_duplicates_full = full_check.get('duplicates', [])

                # Filter to only selected IDs if user made a selection
                if selected_indices:
                    all_duplicate_ids = duplicate_ids  # Use only selected IDs
                else:
                    all_duplicate_ids = [dup['existing_id'] for dup in all_duplicates_full]

                # Deduplicate the ID list (in case same transaction matched multiple times)
                original_count = len(all_duplicate_ids)
                all_duplicate_ids = list(set(all_duplicate_ids))
                deduped_count = len(all_duplicate_ids)

                if original_count != deduped_count:
                    print(f" Found {original_count} duplicate references but only {deduped_count} unique transaction IDs")

                print(f" Deleting {len(all_duplicate_ids)} unique duplicate transactions...")

                with db_manager.get_connection() as conn:
                    if db_manager.db_type == 'postgresql':
                        cursor = conn.cursor()
                        # First, delete any foreign key references in pending_invoice_matches
                        # Note: pending_invoice_matches references transactions, so we filter by transaction_id only
                        delete_matches_query = "DELETE FROM pending_invoice_matches WHERE transaction_id = ANY(%s)"
                        cursor.execute(delete_matches_query, (all_duplicate_ids,))
                        print(f" Deleted {cursor.rowcount} invoice match references")

                        # Delete any foreign key references in entity_patterns
                        # Note: entity_patterns references transactions, so we filter by transaction_id only
                        delete_patterns_query = "DELETE FROM entity_patterns WHERE transaction_id = ANY(%s)"
                        cursor.execute(delete_patterns_query, (all_duplicate_ids,))
                        print(f" Deleted {cursor.rowcount} entity pattern references")

                        # Now delete the transactions - with tenant_id for data isolation
                        delete_query = "DELETE FROM transactions WHERE tenant_id = %s AND transaction_id = ANY(%s)"
                        cursor.execute(delete_query, (tenant_id, all_duplicate_ids))
                        conn.commit()
                        print(f" Deleted {cursor.rowcount} duplicate transactions")
                    else:
                        cursor = conn.cursor()
                        placeholders = ','.join('?' * len(all_duplicate_ids))
                        delete_query = f"DELETE FROM transactions WHERE tenant_id = ? AND transaction_id IN ({placeholders})"
                        cursor.execute(delete_query, [tenant_id] + all_duplicate_ids)
                        conn.commit()
                        print(f" Deleted {cursor.rowcount} duplicate transactions")

            # Step 1.5: Apply entity modifications to the CSV file before syncing (if any)
            if modifications:
                print(f" Applying {len(modifications)} entity modifications to CSV before syncing...")
                try:
                    import pandas as pd
                    import csv

                    # Read the processed CSV file
                    csv_path = pending.get('processed_file')
                    if csv_path and os.path.exists(csv_path):
                        df = pd.read_csv(csv_path)

                        # Apply modifications to matching rows
                        modifications_applied = 0
                        for txn_id, mods in modifications.items():
                            # Find rows matching this transaction (by multiple fields since we don't have ID yet)
                            # We need to match by the duplicate detection criteria
                            if 'entity' in mods:
                                new_entity = mods['entity']
                                # Update all matching rows in the DataFrame
                                # Note: This is a best-effort update based on the data we have
                                # The modifications dict should contain the row indices from the frontend
                                print(f"   Updating transaction ID {txn_id} -> Entity: {new_entity}")
                                modifications_applied += 1

                        # For now, we'll apply modifications based on row indices instead
                        # The frontend sends modifications keyed by existing_id, but for new uploads
                        # we should match by row index in the duplicates list

                        # Actually, let's use a different approach: match modifications to new rows
                        # by using the duplicate_info to map indices to new transaction data
                        if 'duplicates' in duplicate_info:
                            for idx in selected_indices:
                                if 0 <= idx < len(duplicate_info['duplicates']):
                                    dup = duplicate_info['duplicates'][idx]
                                    # Find the corresponding row in the CSV by matching key fields
                                    mask = (
                                        (df['Date'].astype(str) == str(dup.get('date', ''))) &
                                        (df['Amount'].astype(float).round(2) == float(dup.get('new_amount', 0))) &
                                        (df['Currency'] == dup.get('currency', ''))
                                    )

                                    # Apply entity modification if this duplicate has one
                                    existing_id = dup.get('existing_id')
                                    if existing_id in modifications and 'entity' in modifications[existing_id]:
                                        new_entity = modifications[existing_id]['entity']
                                        matched_count = mask.sum()
                                        if matched_count > 0:
                                            df.loc[mask, 'Classified Entity'] = new_entity
                                            print(f"    Updated {matched_count} row(s) at index {idx} -> Entity: {new_entity}")
                                            modifications_applied += 1

                        # Write modified DataFrame back to CSV
                        if modifications_applied > 0:
                            df.to_csv(csv_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
                            print(f" Applied {modifications_applied} entity modifications to CSV file")
                        else:
                            print(f" No modifications were applied (no matching rows found)")
                    else:
                        print(f" Could not find processed CSV file at: {csv_path}")

                except Exception as e:
                    print(f" Error applying modifications to CSV: {e}")
                    import traceback
                    traceback.print_exc()

            # Step 2: Sync the new processed file to database
            print(f" Syncing new enriched transactions to database...")
            sync_result = sync_csv_to_database(filename)

            if sync_result:
                # Clear session
                session.pop('pending_upload', None)

                # Auto-trigger revenue matching
                try:
                    from robust_revenue_matcher import RobustRevenueInvoiceMatcher
                    matcher = RobustRevenueInvoiceMatcher()
                    matches_result = matcher.run_robust_matching(auto_apply=False)
                    if matches_result and matches_result.get('matches_found', 0) > 0:
                        print(f" AUTO-TRIGGER: Found {matches_result['matches_found']} new matches!")
                except Exception as e:
                    print(f" AUTO-TRIGGER: Error during automatic matching: {e}")

                return jsonify({
                    'success': True,
                    'action': 'overwrite',
                    'message': f'Successfully updated {duplicate_info["duplicate_count"]} transactions with latest business knowledge',
                    'duplicates_updated': duplicate_info['duplicate_count'],
                    'new_added': duplicate_info.get('new_count', 0),
                    'sync_result': sync_result
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to sync new transactions to database'
                }), 500

        elif action == 'discard':
            # DISCARD: Delete processed files and keep existing database entries
            print(f" User chose to DISCARD upload, keeping existing {duplicate_info['duplicate_count']} transactions")

            # Delete processed CSV file
            if processed_file and os.path.exists(processed_file):
                os.remove(processed_file)
                print(f" Deleted processed file: {processed_file}")

            # Delete uploaded file
            if os.path.exists(pending['filepath']):
                os.remove(pending['filepath'])
                print(f" Deleted uploaded file: {pending['filepath']}")

            # Clear session
            session.pop('pending_upload', None)

            return jsonify({
                'success': True,
                'action': 'discard',
                'message': f'Upload discarded. Existing {duplicate_info["duplicate_count"]} transactions preserved.',
                'duplicates_kept': duplicate_info['duplicate_count']
            })

        else:
            return jsonify({
                'success': False,
                'error': f'Invalid action: {action}. Must be "overwrite" or "discard".'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/download/<filename>')
def download_file(filename):
    """Download a CSV file"""
    try:
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        filepath = os.path.join(parent_dir, secure_filename(filename))

        if not os.path.exists(filepath):
            return "File not found", 404

        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return f"Error downloading file: {str(e)}", 500

@app.route('/api/process-duplicates', methods=['POST'])
def process_duplicates():
    """Process a file that was already uploaded with specific duplicate handling"""
    try:
        duplicate_handling = request.form.get('duplicateHandling', 'overwrite')
        filename = request.form.get('filename', '')

        if not filename:
            return jsonify({'error': 'No filename provided'}), 400

        print(f"[PROCESS] Processing duplicates for {filename} with mode: {duplicate_handling}")

        # File should already exist from initial upload
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        filepath = os.path.join(parent_dir, filename)

        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 400

        # Use same processing logic as upload_file but force the duplicate handling
        # Convert Windows backslashes to forward slashes (works on all platforms)
        parent_dir_safe = parent_dir.replace(chr(92), '/')
        filename_safe = filename.replace(chr(92), '/')
        
        processing_script = f"""
import sys
import os
sys.path.append('{parent_dir_safe}')
os.chdir('{parent_dir_safe}')

from main import DeltaCFOAgent

agent = DeltaCFOAgent()
result = agent.process_file('{filename_safe}', enhance=True, use_smart_ingestion=True)

if result is not None:
    print(f'PROCESSED_COUNT:{{len(result)}}')
else:
    print('PROCESSED_COUNT:0')
"""

        env = os.environ.copy()
        env['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', '')
        env['PYTHONPATH'] = parent_dir
        # Ensure database environment variables are passed through
        if os.getenv('DB_TYPE'):
            env['DB_TYPE'] = os.getenv('DB_TYPE')
        if os.getenv('DB_HOST'):
            env['DB_HOST'] = os.getenv('DB_HOST')
        if os.getenv('DB_PORT'):
            env['DB_PORT'] = os.getenv('DB_PORT')
        if os.getenv('DB_NAME'):
            env['DB_NAME'] = os.getenv('DB_NAME')
        if os.getenv('DB_USER'):
            env['DB_USER'] = os.getenv('DB_USER')
        if os.getenv('DB_PASSWORD'):
            env['DB_PASSWORD'] = os.getenv('DB_PASSWORD')

        process_result = subprocess.run(
            ['python', '-c', processing_script],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=parent_dir,
            env=env
        )

        # Extract transaction count
        transactions_processed = 0
        if 'PROCESSED_COUNT:' in process_result.stdout:
            count_str = process_result.stdout.split('PROCESSED_COUNT:')[1].split('\n')[0]
            transactions_processed = int(count_str)

        # Sync to database
        sync_result = sync_csv_to_database(filename)

        if sync_result:
            action_msg = "updated" if duplicate_handling == 'overwrite' else "processed"
            return jsonify({
                'success': True,
                'message': f'Successfully {action_msg} {transactions_processed} transactions from {filename}',
                'transactions_processed': transactions_processed
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Processing succeeded but database sync failed'
            }), 500

    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/log_interaction', methods=['POST'])
def api_log_interaction():
    """API endpoint to log user interactions for learning system"""
    try:
        data = request.get_json()

        required_fields = ['transaction_id', 'field_type', 'original_value', 'user_choice', 'action_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Extract data with defaults for optional fields
        transaction_id = data['transaction_id']
        field_type = data['field_type']
        original_value = data['original_value']
        ai_suggestions = data.get('ai_suggestions', [])
        user_choice = data['user_choice']
        action_type = data['action_type']
        transaction_context = data.get('transaction_context', {})
        session_id = data.get('session_id')

        # Log the interaction
        log_user_interaction(
            transaction_id=transaction_id,
            field_type=field_type,
            original_value=original_value,
            ai_suggestions=ai_suggestions,
            user_choice=user_choice,
            action_type=action_type,
            transaction_context=transaction_context,
            session_id=session_id
        )

        return jsonify({'success': True, 'message': 'Interaction logged successfully'})

    except Exception as e:
        print(f"ERROR: Error in api_log_interaction: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# INVOICE PROCESSING ROUTES
# ============================================================================

@app.route('/invoices')
def invoices_page():
    """Invoice management page"""
    try:
        cache_buster = str(random.randint(1000, 9999))
        return render_template('invoices.html', cache_buster=cache_buster)
    except Exception as e:
        return f"Error loading invoices page: {str(e)}", 500

@app.route('/invoices/create-preview')
def create_invoice_preview():
    """Preview of crypto invoice creation template"""
    try:
        return render_template('create_invoice_preview.html')
    except Exception as e:
        return f"Error loading create invoice preview: {str(e)}", 500

@app.route('/invoices/create')
def create_invoice():
    """Render invoice creation form"""
    try:
        return render_template('create_invoice.html')
    except Exception as e:
        return f"Error loading create invoice page: {str(e)}", 500

@app.route('/api/invoices/next-number')
def api_get_next_invoice_number():
    """API endpoint to get next available invoice number based on timestamp"""
    try:
        from datetime import datetime

        # Generate invoice number from current timestamp: YYYYMMDDHHMMSS
        now = datetime.now()
        invoice_number = now.strftime('%Y%m%d%H%M%S')

        return jsonify({'success': True, 'invoice_number': invoice_number})

    except Exception as e:
        print(f"Error generating invoice number: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/invoices/vendors')
def api_get_vendors():
    """API endpoint to get unique vendors from invoices"""
    try:
        tenant_id = get_current_tenant_id()
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        # Get distinct vendor names from invoices (excluding NULL and empty strings)
        cursor.execute("""
            SELECT DISTINCT vendor_name
            FROM invoices
            WHERE tenant_id = %s
            AND vendor_name IS NOT NULL
            AND vendor_name != ''
            ORDER BY vendor_name
        """, (tenant_id,))

        vendors = [row[0] for row in cursor.fetchall()]
        cursor.close()

        return jsonify({'success': True, 'vendors': vendors})

    except Exception as e:
        print(f"Error fetching vendors: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/invoices/create', methods=['POST'])
def api_create_invoice():
    """API endpoint to create a new invoice with PDF generation"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.pdfgen import canvas
        import os
        from datetime import datetime
        from database import db_manager

        tenant_id = get_current_tenant_id()
        data = request.get_json()

        # Extract data
        invoice_number = data.get('invoice_number')
        vendor_name = data.get('vendor_name', 'DELTA ENERGY')  # Default to DELTA ENERGY
        vendor_address = data.get('vendor_address', '')  # Get vendor address from form
        customer_name = data.get('customer_name')
        customer_address = data.get('customer_address', '')
        invoice_date = data.get('invoice_date')
        due_date = data.get('due_date')
        currency = data.get('currency', 'USD')
        description = data.get('description', '')
        line_items = data.get('line_items', [])
        subtotal = float(data.get('subtotal', 0))
        tax_percentage = float(data.get('tax_percentage', 0))
        tax_amount = float(data.get('tax_amount', 0))
        total_amount = float(data.get('total_amount', 0))
        payment_terms = data.get('payment_terms', '')

        # Extract crypto fields
        currency_type = data.get('currency_type', 'fiat')
        crypto_currency = data.get('crypto_currency')
        crypto_network = data.get('crypto_network')

        # Create invoices/issued directory if it doesn't exist (use absolute path)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        issued_dir = os.path.join(base_dir, 'invoices', 'issued')
        os.makedirs(issued_dir, exist_ok=True)

        # Generate PDF filename
        pdf_filename = f"{invoice_number}_{invoice_date}.pdf"
        pdf_path = os.path.join(issued_dir, pdf_filename)

        # Create PDF with modern design and better margins
        doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                               rightMargin=0.75*inch, leftMargin=0.75*inch,
                               topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = []
        styles = getSampleStyleSheet()

        # Define custom colors - softer, more vibrant palette
        delta_blue = colors.HexColor('#2563eb')  # Brighter blue
        delta_light_blue = colors.HexColor('#60a5fa')  # Lighter, more visible blue
        delta_header = colors.HexColor('#1e40af')  # Rich blue for headers
        crypto_gold = colors.HexColor('#f59e0b')
        crypto_bg = colors.HexColor('#fef3c7')  # Soft yellow
        light_gray = colors.HexColor('#f8fafc')  # Very light gray
        medium_gray = colors.HexColor('#e2e8f0')  # Medium gray for borders
        dark_gray = colors.HexColor('#475569')  # Softer dark gray

        # Business entity data
        business_entities = {
            'DELTA ENERGY': {
                'address': '123 Energy Way, Miami, FL 33101',
                'tax_id': 'EIN: 12-3456789',
                'contact': 'info@deltaenergy.com | +1 (305) 555-0100'
            },
            'Delta LLC': {
                'address': '456 Commerce St, New York, NY 10001',
                'tax_id': 'EIN: 98-7654321',
                'contact': 'contact@deltallc.com | +1 (212) 555-0200'
            },
            'Delta Prop Shop LLC': {
                'address': '789 Trading Blvd, Chicago, IL 60601',
                'tax_id': 'EIN: 11-2233445',
                'contact': 'trading@deltapropshop.com | +1 (312) 555-0300'
            },
            'Delta Mining Paraguay S.A.': {
                'address': 'Av. Mariscal Lopez 1234, Asunción, Paraguay',
                'tax_id': 'RUC: 80123456-7',
                'contact': 'mining@deltaparaguay.com | +595 21 555 0400'
            },
            'Delta Brazil': {
                'address': 'Av. Paulista 1000, São Paulo, SP 01310-100, Brasil',
                'tax_id': 'CNPJ: 12.345.678/0001-90',
                'contact': 'contato@deltabrasil.com.br | +55 11 5555-0500'
            }
        }

        # Get vendor entity data if available, or use custom address from form
        vendor_entity_data = business_entities.get(vendor_name)

        # Header section with vendor name - improved alignment
        header_data = [[Paragraph(f"<b><font size='28' color='white'>{vendor_name.upper()}</font></b>", styles['Normal'])]]
        header_table = Table(header_data, colWidths=[6.5*inch])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), delta_header),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 20),
            ('TOPPADDING', (0, 0), (-1, -1), 25),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 25),
            ('ROUNDEDCORNERS', [8, 8, 0, 0]),  # Rounded top corners
        ]))
        story.append(header_table)

        # Add vendor entity info - prioritize custom address from form, fallback to predefined entities
        if vendor_address:
            # Use custom vendor address from the form
            vendor_info_data = [[
                Paragraph(f"<font size='9' color='#64748b'>{vendor_address}</font>", styles['Normal'])
            ]]
            vendor_info_table = Table(vendor_info_data, colWidths=[6.5*inch])
            vendor_info_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 20),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(vendor_info_table)
            story.append(Spacer(1, 0.3*inch))
        elif vendor_entity_data:
            # Use predefined entity data
            vendor_info_data = [[
                Paragraph(f"<font size='9' color='#64748b'>{vendor_entity_data['address']}<br/>{vendor_entity_data['tax_id']}<br/>{vendor_entity_data['contact']}</font>", styles['Normal'])
            ]]
            vendor_info_table = Table(vendor_info_data, colWidths=[6.5*inch])
            vendor_info_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 20),
                ('TOPPADDING', (0, 0), (-1, -1), 15),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(vendor_info_table)
            story.append(Spacer(1, 0.3*inch))
        else:
            story.append(Spacer(1, 0.4*inch))

        # Invoice number and type badge with modern styling and better spacing
        invoice_type_color = crypto_gold if currency_type == 'crypto' else delta_blue
        invoice_type_text = 'CRYPTOCURRENCY INVOICE' if currency_type == 'crypto' else 'INVOICE'
        type_color_hex = '#f59e0b' if currency_type == 'crypto' else '#2563eb'

        invoice_header_data = [
            [Paragraph(f"<b><font size='22' color='{type_color_hex}'>{invoice_type_text}</font></b>", styles['Normal']),
             Paragraph(f"<b><font size='16' color='#475569'>#{invoice_number}</font></b>", styles['Normal'])]
        ]
        invoice_header_table = Table(invoice_header_data, colWidths=[4.2*inch, 2.3*inch])
        invoice_header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(invoice_header_table)
        story.append(Spacer(1, 0.3*inch))

        # Two-column info section with improved layout
        left_col_data = [
            [Paragraph("<b>BILL TO:</b>", styles['Normal'])],
            [Paragraph(f"<font size='11'><b>{customer_name}</b></font>", styles['Normal'])],
            [Paragraph(f"<font size='9'>{customer_address or ''}</font>", styles['Normal'])],
        ]

        right_col_data = [
            [Paragraph("<b>Invoice Date:</b>", styles['Normal']), Paragraph(invoice_date, styles['Normal'])],
            [Paragraph("<b>Due Date:</b>", styles['Normal']), Paragraph(due_date, styles['Normal'])],
        ]

        if description:
            right_col_data.append([Paragraph("<b>Description:</b>", styles['Normal']), Paragraph(description, styles['Normal'])])

        left_table = Table(left_col_data, colWidths=[3*inch])
        left_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), light_gray),
            ('LEFTPADDING', (0, 0), (-1, -1), 16),
            ('RIGHTPADDING', (0, 0), (-1, -1), 16),
            ('TOPPADDING', (0, 0), (-1, -1), 16),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),  # All corners rounded
            ('LINEABOVE', (0, 0), (-1, 0), 0.5, medium_gray),
        ]))

        right_table = Table(right_col_data, colWidths=[1.2*inch, 2*inch])
        right_table.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        info_layout = Table([[left_table, right_table]], colWidths=[3*inch, 3.2*inch], hAlign='LEFT', spaceBefore=0, spaceAfter=0)
        info_layout.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(info_layout)
        story.append(Spacer(1, 0.35*inch))

        # Crypto payment info box (if applicable) - with rounded corners and modern style
        if currency_type == 'crypto' and crypto_currency:
            crypto_display = f"{crypto_currency}"
            if crypto_network:
                crypto_display += f" ({crypto_network})"

            crypto_box_data = [[Paragraph(f"<b><font size='12' color='#92400e'>PAYMENT CURRENCY: {crypto_display}</font></b>", styles['Normal'])]]
            crypto_box = Table(crypto_box_data, colWidths=[7*inch])
            crypto_box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), crypto_bg),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('LEFTPADDING', (0, 0), (-1, -1), 20),
                ('RIGHTPADDING', (0, 0), (-1, -1), 20),
                ('TOPPADDING', (0, 0), (-1, -1), 16),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
                ('BOX', (0, 0), (-1, -1), 2, crypto_gold),
                ('ROUNDEDCORNERS', [8, 8, 8, 8]),  # All corners rounded
            ]))
            story.append(crypto_box)
            story.append(Spacer(1, 0.3*inch))

        # Line items table with modern styling
        line_items_data = [[
            Paragraph("<b>DESCRIPTION</b>", styles['Normal']),
            Paragraph("<b>QTY</b>", styles['Normal']),
            Paragraph("<b>UNIT PRICE</b>", styles['Normal']),
            Paragraph("<b>AMOUNT</b>", styles['Normal'])
        ]]

        for item in line_items:
            # Add main item row
            line_items_data.append([
                Paragraph(f"<b>{item['description']}</b>", styles['Normal']),
                Paragraph(str(item['quantity']), styles['Normal']),
                Paragraph(f"{currency} {item['unit_price']:.2f}", styles['Normal']),
                Paragraph(f"{currency} {item['amount']:.2f}", styles['Normal'])
            ])

            # Add details row if details exist
            if item.get('details') and item['details'].strip():
                line_items_data.append([
                    Paragraph(f"<font size='8' color='#64748b'><i>{item['details']}</i></font>", styles['Normal']),
                    '', '', ''
                ])

        items_table = Table(line_items_data, colWidths=[3.3*inch, 0.7*inch, 1.2*inch, 1.3*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), delta_blue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_gray]),
            ('GRID', (0, 0), (-1, -1), 0.5, medium_gray),
            ('TOPPADDING', (0, 1), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),  # Rounded corners for table
        ]))
        story.append(items_table)
        story.append(Spacer(1, 0.3*inch))

        # Summary table
        summary_data = []
        summary_data.append(['Subtotal:', f"{currency} {subtotal:.2f}"])
        if tax_amount > 0:
            summary_data.append([f'Tax ({tax_percentage}%):', f"{currency} {tax_amount:.2f}"])
        summary_data.append(['TOTAL:', f"{currency} {total_amount:.2f}"])

        summary_table = Table(summary_data, colWidths=[1.5*inch, 1.5*inch], hAlign='RIGHT')
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('FONTSIZE', (0, 0), (-1, -2), 11),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, -1), (-1, -1), delta_light_blue),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('LINEABOVE', (0, -1), (-1, -1), 2, delta_blue),
            ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        ]))
        story.append(summary_table)

        # Payment terms
        if payment_terms:
            story.append(Spacer(1, 0.4*inch))
            terms_header = Paragraph("<b><font size='11' color='#1e40af'>PAYMENT TERMS & NOTES</font></b>", styles['Normal'])
            story.append(terms_header)
            story.append(Spacer(1, 0.1*inch))

            terms_box_data = [[Paragraph(f"<font size='9'>{payment_terms}</font>", styles['Normal'])]]
            terms_box = Table(terms_box_data, colWidths=[7*inch])
            terms_box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), light_gray),
                ('LEFTPADDING', (0, 0), (-1, -1), 15),
                ('RIGHTPADDING', (0, 0), (-1, -1), 15),
                ('TOPPADDING', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('ROUNDEDCORNERS', [6, 6, 6, 6]),
            ]))
            story.append(terms_box)

        # Footer
        story.append(Spacer(1, 0.3*inch))
        footer_text = Paragraph("<font size='8' color='gray'>Thank you for your business!</font>", styles['Normal'])
        footer_table = Table([[footer_text]], colWidths=[7*inch])
        footer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(footer_table)

        # Build PDF
        doc.build(story)

        # Save to database
        invoice_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()

        db_manager.execute_query("""
            INSERT INTO invoices (
                id, tenant_id, invoice_number, date, due_date,
                vendor_name, customer_name, customer_address, total_amount, currency,
                tax_amount, subtotal, line_items, payment_terms,
                status, invoice_type, source_file, created_at,
                currency_type, crypto_currency, crypto_network
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            invoice_id, tenant_id, invoice_number, invoice_date, due_date,
            vendor_name, customer_name, customer_address, total_amount, currency,
            tax_amount, subtotal, json.dumps(line_items), payment_terms,
            'pending', 'issued', pdf_path, created_at,
            currency_type, crypto_currency, crypto_network
        ))

        return jsonify({
            'success': True,
            'invoice_number': invoice_number,
            'invoice_id': invoice_id,
            'pdf_path': pdf_path
        })

    except Exception as e:
        print(f"Error creating invoice: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/invoices/pdf/<path:filename>')
def api_download_invoice_pdf(filename):
    """API endpoint to download invoice PDF"""
    try:
        from flask import send_file
        import os

        # Construct the full path (use absolute path)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_path = os.path.join(base_dir, 'invoices', 'issued', filename)

        # Check if file exists
        if not os.path.exists(pdf_path):
            return jsonify({'success': False, 'error': 'PDF file not found'}), 404

        # Send the file
        return send_file(pdf_path, mimetype='application/pdf', as_attachment=True, download_name=filename)

    except Exception as e:
        print(f"Error downloading invoice PDF: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/invoices')
def api_get_invoices():
    """API endpoint to get invoices with pagination and filtering"""
    try:
        tenant_id = get_current_tenant_id()
        print(f"[DEBUG] api_get_invoices called with args: {request.args}")
        # Get basic filter parameters
        filters = {
            'business_unit': request.args.get('business_unit'),
            'category': request.args.get('category'),
            'vendor_name': request.args.get('vendor_name'),
            'customer_name': request.args.get('customer_name'),
            'linked_transaction_id': request.args.get('linked_transaction_id')
        }

        # Get keyword search parameter
        keyword = request.args.get('keyword')

        # Get advanced filter parameters
        advanced_filters = {
            'invoice_number': request.args.get('invoice_number'),
            'date_from': request.args.get('date_from'),
            'date_to': request.args.get('date_to'),
            'amount_min': request.args.get('amount_min'),
            'amount_max': request.args.get('amount_max'),
            'currency': request.args.get('currency')
        }

        # Get sorting parameters
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc').upper()

        # Validate sort order
        if sort_order not in ['ASC', 'DESC']:
            sort_order = 'DESC'

        # Validate sort field (prevent SQL injection)
        allowed_sort_fields = ['invoice_number', 'date', 'due_date', 'vendor_name', 'customer_name',
                              'total_amount', 'currency', 'business_unit', 'category', 'created_at']
        if sort_by not in allowed_sort_fields:
            sort_by = 'created_at'

        # Remove None values
        filters = {k: v for k, v in filters.items() if v}
        advanced_filters = {k: v for k, v in advanced_filters.items() if v}

        # Pagination
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        offset = (page - 1) * per_page

        from database import db_manager

        # Use PostgreSQL placeholders since we're using db_manager
        placeholder = '%s'

        # Build query - add tenant_id filter
        query = f"SELECT * FROM invoices WHERE tenant_id = {placeholder}"
        params = [tenant_id]

        # Apply keyword search across multiple fields (case-insensitive with ILIKE)
        if keyword:
            keyword_condition = f"""
                AND (
                    invoice_number ILIKE {placeholder} OR
                    vendor_name ILIKE {placeholder} OR
                    customer_name ILIKE {placeholder} OR
                    business_unit ILIKE {placeholder} OR
                    category ILIKE {placeholder} OR
                    processing_notes ILIKE {placeholder} OR
                    CAST(total_amount AS TEXT) ILIKE {placeholder}
                )
            """
            query += keyword_condition
            keyword_param = f"%{keyword}%"
            params.extend([keyword_param] * 7)  # 7 fields being searched

        if filters.get('business_unit'):
            query += f" AND business_unit = {placeholder}"
            params.append(filters['business_unit'])

        if filters.get('category'):
            query += f" AND category = {placeholder}"
            params.append(filters['category'])

        if filters.get('vendor_name'):
            query += f" AND vendor_name LIKE {placeholder}"
            params.append(f"%{filters['vendor_name']}%")

        if filters.get('customer_name'):
            query += f" AND customer_name LIKE {placeholder}"
            params.append(f"%{filters['customer_name']}%")

        # Apply advanced filters
        if advanced_filters.get('invoice_number'):
            query += f" AND invoice_number LIKE {placeholder}"
            params.append(f"%{advanced_filters['invoice_number']}%")

        if advanced_filters.get('date_from'):
            query += f" AND date >= {placeholder}"
            params.append(advanced_filters['date_from'])

        if advanced_filters.get('date_to'):
            query += f" AND date <= {placeholder}"
            params.append(advanced_filters['date_to'])

        if advanced_filters.get('amount_min'):
            query += f" AND total_amount >= {placeholder}"
            params.append(float(advanced_filters['amount_min']))

        if advanced_filters.get('amount_max'):
            query += f" AND total_amount <= {placeholder}"
            params.append(float(advanced_filters['amount_max']))

        if advanced_filters.get('currency'):
            query += f" AND currency = {placeholder}"
            params.append(advanced_filters['currency'])

        # Filter by linked_transaction_id (special handling before filters cleanup)
        linked_filter = request.args.get('linked_transaction_id')
        if linked_filter:
            if linked_filter.lower() in ['null', 'none', 'unlinked']:
                # Show only unlinked invoices
                query += " AND (linked_transaction_id IS NULL OR linked_transaction_id = '')"
                print(f"[DEBUG] Applied unlinked filter: {query}")
            elif linked_filter.lower() in ['not_null', 'linked']:
                # Show only linked invoices
                query += " AND linked_transaction_id IS NOT NULL AND linked_transaction_id != ''"
                print(f"[DEBUG] Applied linked filter: {query}")
            else:
                # Show invoices with specific transaction ID
                query += f" AND linked_transaction_id = {placeholder}"
                params.append(linked_filter)
                print(f"[DEBUG] Applied specific ID filter: {query}")

        # Get total count
        count_query = query.replace("SELECT *", "SELECT COUNT(*) as total")
        count_result = db_manager.execute_query(count_query, tuple(params), fetch_one=True)
        total_count = count_result['total'] if count_result else 0

        # Add ordering and pagination - use validated sort_by and sort_order
        query += f" ORDER BY {sort_by} {sort_order} LIMIT {placeholder} OFFSET {placeholder}"
        params.extend([per_page, offset])

        results = db_manager.execute_query(query, tuple(params), fetch_all=True)
        invoices = []

        if results:
            for row in results:
                invoice = dict(row)
                # Parse JSON fields
                if invoice.get('line_items'):
                    try:
                        invoice['line_items'] = json.loads(invoice['line_items'])
                    except:
                        invoice['line_items'] = []
                invoices.append(invoice)

        return jsonify({
            'invoices': invoices,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/<invoice_id>')
def api_get_invoice(invoice_id):
    """Get single invoice by ID"""
    try:
        tenant_id = get_current_tenant_id()
        from database import db_manager

        # Execute query using db_manager - filter by tenant_id
        row = db_manager.execute_query("SELECT * FROM invoices WHERE tenant_id = %s AND id = %s", (tenant_id, invoice_id), fetch_one=True)

        if not row:
            return jsonify({'error': 'Invoice not found'}), 404

        invoice = dict(row)
        # Parse JSON fields
        if invoice.get('line_items'):
            try:
                invoice['line_items'] = json.loads(invoice['line_items'])
            except:
                invoice['line_items'] = []

        return jsonify(invoice)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def extract_compressed_file(file_path: str, extract_dir: str) -> List[str]:
    """
    Extract files from compressed archives (ZIP, RAR, 7z) with support for nested directories.
    Recursively walks through all subdirectories to find supported invoice files.

    Args:
        file_path: Path to the compressed archive file
        extract_dir: Directory to extract files to

    Returns:
        List of file paths for all supported invoice files found in the archive,
        or dict with 'error' key if extraction fails
    """
    try:

        file_ext = os.path.splitext(file_path)[1].lower()

        os.makedirs(extract_dir, exist_ok=True)

        # Extract archive based on file type
        if file_ext == '.zip':
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

        elif file_ext == '.7z':
            if not PY7ZR_AVAILABLE:
                return {'error': '7z support not available - py7zr package required'}
            with py7zr.SevenZipFile(file_path, mode='r') as archive:
                archive.extractall(path=extract_dir)

        elif file_ext == '.rar':
            return {'error': 'RAR format requires additional setup. Please use ZIP or 7Z format.'}

        else:
            return {'error': f'Unsupported archive format: {file_ext}'}

        # Recursively walk through all directories to find supported files
        # This handles nested folder structures of any depth
        allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
        filtered_files = []

        for root, dirs, files in os.walk(extract_dir):
            for filename in files:
                file_path_in_archive = os.path.join(root, filename)
                file_extension = os.path.splitext(filename)[1].lower()

                # Only include files with supported extensions
                if file_extension in allowed_extensions and os.path.isfile(file_path_in_archive):
                    filtered_files.append(file_path_in_archive)

        return filtered_files

    except zipfile.BadZipFile:
        return {'error': 'Invalid or corrupted ZIP file'}
    except Exception as e:
        return {'error': f'Failed to extract archive: {str(e)}'}

@app.route('/api/invoices/upload', methods=['POST'])
def api_upload_invoice():
    """Upload and process invoice file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Check file type
        allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'}), 400

        # Save file
        upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'invoices')
        os.makedirs(upload_dir, exist_ok=True)

        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)

        # Process invoice with Claude Vision
        invoice_data = process_invoice_with_claude(file_path, file.filename)

        if 'error' in invoice_data:
            return jsonify(invoice_data), 500

        # Auto-trigger revenue matching after successful invoice upload
        try:
            print(f" AUTO-TRIGGER: Starting automatic revenue matching after invoice upload...")
            from robust_revenue_matcher import RobustRevenueInvoiceMatcher

            matcher = RobustRevenueInvoiceMatcher()
            # Focus on the newly uploaded invoice
            matches_result = matcher.run_robust_matching(auto_apply=False, match_all=True)

            if matches_result and matches_result.get('matches_found', 0) > 0:
                print(f" AUTO-TRIGGER: Found {matches_result['matches_found']} new matches automatically!")
            else:
                print("ℹ AUTO-TRIGGER: No new matches found after invoice upload")

        except Exception as e:
            print(f" AUTO-TRIGGER: Error during automatic matching: {e}")
            # Don't fail the upload if matching fails

        return jsonify({
            'success': True,
            'invoice_id': invoice_data['id'],
            'invoice': invoice_data
        })

    except Exception as e:
        error_details = {
            'error': str(e),
            'error_type': type(e).__name__,
            'claude_client_status': 'initialized' if claude_client else 'not_initialized',
            'api_key_present': bool(os.getenv('ANTHROPIC_API_KEY')),
            'traceback': traceback.format_exc()
        }
        print(f"[ERROR] Invoice upload error: {error_details}")
        return jsonify(error_details), 500

@app.route('/api/invoices/upload-batch', methods=['POST'])
def api_upload_batch_invoices():
    """Upload and process multiple invoice files or compressed archive"""
    try:
        if 'files' not in request.files and 'file' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'invoices')
        temp_extract_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'temp_extract')
        os.makedirs(upload_dir, exist_ok=True)

        results = {
            'success': True,
            'total_files': 0,
            'total_files_in_archive': 0,  # Total files found in ZIP (all types)
            'files_found': 0,  # Supported invoice files found
            'files_skipped': 0,  # Unsupported files skipped
            'processed': 0,
            'failed': 0,
            'invoices': [],
            'errors': [],
            'skipped_files': [],  # List of skipped filenames with reasons
            'archive_info': None  # Info about the archive structure
        }

        files_to_process = []
        cleanup_paths = []

        # Check if it's a compressed file
        if 'file' in request.files:
            file = request.files['file']
            file_ext = os.path.splitext(file.filename)[1].lower()

            if file_ext in ['.zip', '.7z', '.rar']:
                # Save compressed file
                compressed_path = os.path.join(upload_dir, f"{uuid.uuid4()}{file_ext}")
                file.save(compressed_path)
                cleanup_paths.append(compressed_path)

                # Count total files in archive before extraction
                total_in_archive = 0
                all_files_in_archive = []
                try:
                    if file_ext == '.zip':
                        with zipfile.ZipFile(compressed_path, 'r') as zip_ref:
                            all_files_in_archive = [name for name in zip_ref.namelist() if not name.endswith('/')]
                            total_in_archive = len(all_files_in_archive)
                    elif file_ext == '.7z':
                        if PY7ZR_AVAILABLE:
                            with py7zr.SevenZipFile(compressed_path, mode='r') as archive:
                                all_files_in_archive = archive.getnames()
                                total_in_archive = len([f for f in all_files_in_archive if not f.endswith('/')])
                except:
                    pass

                results['total_files_in_archive'] = total_in_archive

                # Extract files
                extract_result = extract_compressed_file(compressed_path, temp_extract_dir)

                if isinstance(extract_result, dict) and 'error' in extract_result:
                    return jsonify(extract_result), 400

                files_to_process = [(f, os.path.basename(f)) for f in extract_result]
                results['files_found'] = len(files_to_process)

                # Calculate skipped files
                allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
                for file_in_archive in all_files_in_archive:
                    file_extension = os.path.splitext(file_in_archive)[1].lower()
                    if file_extension not in allowed_extensions and file_extension:
                        results['skipped_files'].append({
                            'filename': os.path.basename(file_in_archive),
                            'path': file_in_archive,
                            'reason': f'Unsupported file type: {file_extension}'
                        })

                results['files_skipped'] = len(results['skipped_files'])
                results['archive_info'] = {
                    'filename': file.filename,
                    'type': file_ext,
                    'nested_structure': any('/' in f or '\\' in f for f in all_files_in_archive)
                }

                cleanup_paths.append(temp_extract_dir)
            else:
                # Single file upload
                unique_filename = f"{uuid.uuid4()}{file_ext}"
                file_path = os.path.join(upload_dir, unique_filename)
                file.save(file_path)
                files_to_process = [(file_path, file.filename)]

        # Check for multiple files
        elif 'files' in request.files:
            files = request.files.getlist('files')
            for file in files:
                if file.filename:
                    file_ext = os.path.splitext(file.filename)[1].lower()
                    unique_filename = f"{uuid.uuid4()}{file_ext}"
                    file_path = os.path.join(upload_dir, unique_filename)
                    file.save(file_path)
                    files_to_process.append((file_path, file.filename))

        results['total_files'] = len(files_to_process)

        # Process each file
        for file_path, original_filename in files_to_process:
            try:
                # Validate file type
                allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
                file_ext = os.path.splitext(file_path)[1].lower()

                if file_ext not in allowed_extensions:
                    results['failed'] += 1
                    results['errors'].append({
                        'file': original_filename,
                        'error': f'Unsupported file type: {file_ext}'
                    })
                    continue

                # Process invoice
                invoice_data = process_invoice_with_claude(file_path, original_filename)

                if 'error' in invoice_data:
                    results['failed'] += 1
                    results['errors'].append({
                        'file': original_filename,
                        'error': invoice_data['error']
                    })
                else:
                    results['processed'] += 1
                    results['invoices'].append({
                        'id': invoice_data['id'],
                        'invoice_number': invoice_data.get('invoice_number'),
                        'vendor_name': invoice_data.get('vendor_name'),
                        'total_amount': invoice_data.get('total_amount'),
                        'currency': invoice_data.get('currency'),
                        'original_filename': original_filename
                    })

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'file': original_filename,
                    'error': str(e)
                })

        # Cleanup temporary files
        for path in cleanup_paths:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.isfile(path):
                    os.remove(path)
            except:
                pass

        # Set overall success status
        results['success'] = results['processed'] > 0

        # Auto-trigger revenue matching after successful batch invoice upload
        if results['processed'] > 0:
            try:
                print(f" AUTO-TRIGGER: Starting automatic revenue matching after batch upload ({results['processed']} invoices)...")
                from robust_revenue_matcher import RobustRevenueInvoiceMatcher

                matcher = RobustRevenueInvoiceMatcher()
                matches_result = matcher.run_robust_matching(auto_apply=False, match_all=True)

                if matches_result and matches_result.get('matches_found', 0) > 0:
                    print(f" AUTO-TRIGGER: Found {matches_result['matches_found']} new matches automatically!")
                    results['auto_matches_found'] = matches_result['matches_found']
                else:
                    print("ℹ AUTO-TRIGGER: No new matches found after batch upload")
                    results['auto_matches_found'] = 0

            except Exception as e:
                print(f" AUTO-TRIGGER: Error during automatic matching: {e}")
                results['auto_trigger_error'] = str(e)

        return jsonify(results)

    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/invoices/upload-batch-async', methods=['POST'])
def api_upload_batch_invoices_async():
    """Upload and process multiple invoice files asynchronously using background jobs"""
    try:
        if 'files' not in request.files and 'file' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        upload_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'invoices')
        temp_extract_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'temp_extract')
        os.makedirs(upload_dir, exist_ok=True)

        files_to_process = []
        cleanup_paths = []
        source_file_name = None

        # Handle file upload (same logic as sync version)
        if 'file' in request.files:
            file = request.files['file']
            file_ext = os.path.splitext(file.filename)[1].lower()
            source_file_name = file.filename

            if file_ext in ['.zip', '.7z', '.rar']:
                # Save compressed file
                compressed_path = os.path.join(upload_dir, f"{uuid.uuid4()}{file_ext}")
                file.save(compressed_path)
                cleanup_paths.append(compressed_path)

                # Extract files
                extract_result = extract_compressed_file(compressed_path, temp_extract_dir)

                if isinstance(extract_result, dict) and 'error' in extract_result:
                    return jsonify(extract_result), 400

                files_to_process = [(f, os.path.basename(f)) for f in extract_result]
                cleanup_paths.append(temp_extract_dir)
            else:
                # Single file upload
                unique_filename = f"{uuid.uuid4()}{file_ext}"
                file_path = os.path.join(upload_dir, unique_filename)
                file.save(file_path)
                files_to_process = [(file_path, file.filename)]

        # Handle multiple files
        elif 'files' in request.files:
            files = request.files.getlist('files')
            for file in files:
                if file.filename:
                    file_ext = os.path.splitext(file.filename)[1].lower()
                    unique_filename = f"{uuid.uuid4()}{file_ext}"
                    file_path = os.path.join(upload_dir, unique_filename)
                    file.save(file_path)
                    files_to_process.append((file_path, file.filename))
            source_file_name = f"{len(files)} files uploaded"

        if not files_to_process:
            return jsonify({'error': 'No valid files to process'}), 400

        # Filter supported file types
        allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'}
        valid_files = []

        for file_path, original_name in files_to_process:
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in allowed_extensions:
                valid_files.append((file_path, original_name))
            else:
                # Clean up unsupported files
                try:
                    os.remove(file_path)
                except:
                    pass

        if not valid_files:
            return jsonify({'error': 'No supported file types found'}), 400

        # Create background job
        metadata = f"Source: {source_file_name}, Files: {len(valid_files)}"
        job_id = create_background_job(
            job_type='invoice_batch',
            total_items=len(valid_files),
            created_by='web_user',
            source_file=source_file_name,
            metadata=metadata
        )

        if not job_id:
            return jsonify({'error': 'Failed to create background job'}), 500

        # Add all files as job items
        for file_path, original_name in valid_files:
            add_job_item(job_id, original_name, file_path)

        # Start background processing
        success = start_background_job(job_id, 'invoice_batch')

        if not success:
            return jsonify({'error': 'Failed to start background processing'}), 500

        # Return immediately with job ID
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': f'Background job created successfully. Processing {len(valid_files)} files.',
            'total_files': len(valid_files),
            'status_url': f'/api/jobs/{job_id}'
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/invoices/<invoice_id>', methods=['PUT'])
def api_update_invoice(invoice_id):
    """Update invoice fields - supports single field or multiple fields"""
    try:
        from database import db_manager
        data = request.get_json()

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        # Check if invoice exists
        existing = db_manager.execute_query("SELECT id FROM invoices WHERE tenant_id = %s AND id = %s", (tenant_id, invoice_id), fetch_one=True)
        if not existing:
            return jsonify({'error': 'Invoice not found'}), 404

        # Handle both single field update and multiple field update
        if 'field' in data and 'value' in data:
            # Single field update (for inline editing)
            field = data['field']
            value = data['value']

            # Validate field name to prevent SQL injection
            allowed_fields = ['invoice_number', 'date', 'due_date', 'vendor_name', 'vendor_address',
                            'vendor_tax_id', 'customer_name', 'customer_address', 'customer_tax_id',
                            'total_amount', 'currency', 'tax_amount', 'subtotal',
                            'business_unit', 'category', 'payment_terms']

            if field not in allowed_fields:
                return jsonify({'error': 'Invalid field name'}), 400

            update_query = f"UPDATE invoices SET {field} = %s WHERE id = %s"
            db_manager.execute_query(update_query, (value, invoice_id))
        else:
            # Multiple field update (for modal editing)
            allowed_fields = ['invoice_number', 'date', 'due_date', 'vendor_name', 'vendor_address',
                            'vendor_tax_id', 'customer_name', 'customer_address', 'customer_tax_id',
                            'total_amount', 'currency', 'tax_amount', 'subtotal',
                            'business_unit', 'category', 'payment_terms']

            updates = []
            values = []

            for field, value in data.items():
                if field in allowed_fields and value is not None:
                    updates.append(f"{field} = %s")
                    values.append(value)

            if not updates:
                return jsonify({'error': 'No valid fields to update'}), 400

            update_query = f"UPDATE invoices SET {', '.join(updates)} WHERE id = %s"
            values.append(invoice_id)
            db_manager.execute_query(update_query, tuple(values))

        return jsonify({'success': True, 'message': 'Invoice updated'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/<invoice_id>', methods=['DELETE'])
def api_delete_invoice(invoice_id):
    """Delete invoice"""
    try:
        from database import db_manager

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        # Execute delete query
        rows_affected = db_manager.execute_query("DELETE FROM invoices WHERE tenant_id = %s AND id = %s", (tenant_id, invoice_id))

        if rows_affected == 0:
            return jsonify({'error': 'Invoice not found'}), 404

        return jsonify({'success': True, 'message': 'Invoice deleted'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/bulk-update', methods=['POST'])
def api_bulk_update_invoices():
    """Bulk update multiple invoices"""
    try:
        from database import db_manager
        data = request.get_json()
        invoice_ids = data.get('invoice_ids', [])
        updates = data.get('updates', {})

        if not invoice_ids or not updates:
            return jsonify({'error': 'Missing invoice_ids or updates'}), 400

        # Validate field names
        allowed_fields = ['business_unit', 'category', 'currency', 'due_date', 'payment_terms',
                         'customer_name', 'customer_address', 'customer_tax_id']

        # Build update query
        update_parts = []
        values = []

        for field, value in updates.items():
            if field in allowed_fields and value:
                update_parts.append(f"{field} = %s")
                values.append(value)

        if not update_parts:
            return jsonify({'error': 'No valid fields to update'}), 400

        updated_count = 0

        # Use transaction for consistency
        with db_manager.get_transaction() as conn:
            cursor = conn.cursor()

            # Update each invoice
            for invoice_id in invoice_ids:
                update_query = f"UPDATE invoices SET {', '.join(update_parts)} WHERE id = %s"
                cursor.execute(update_query, values + [invoice_id])
                if cursor.rowcount > 0:
                    updated_count += 1

            cursor.close()

        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'message': f'Successfully updated {updated_count} invoices'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/bulk-delete', methods=['POST'])
def api_bulk_delete_invoices():
    """Bulk delete multiple invoices"""
    try:
        from database import db_manager
        data = request.get_json()
        invoice_ids = data.get('invoice_ids', [])

        if not invoice_ids:
            return jsonify({'error': 'No invoice IDs provided'}), 400

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        deleted_count = 0

        # Use transaction for consistency
        with db_manager.get_transaction() as conn:
            cursor = conn.cursor()

            # Delete each invoice
            for invoice_id in invoice_ids:
                cursor.execute("DELETE FROM invoices WHERE tenant_id = %s AND id = %s", (tenant_id, invoice_id))
                if cursor.rowcount > 0:
                    deleted_count += 1

            cursor.close()

        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Successfully deleted {deleted_count} invoices'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/stats')
def api_invoice_stats():
    """Get invoice statistics"""
    try:
        from database import db_manager

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        # Total invoices
        total_result = db_manager.execute_query("SELECT COUNT(*) as count FROM invoices WHERE tenant_id = %s", (tenant_id,), fetch_one=True)
        total = total_result['count'] if total_result else 0

        # Total amount - Use USD equivalent when available, fallback to original
        amount_query = """
        SELECT COALESCE(SUM(
            CASE
                WHEN currency = 'USD' THEN total_amount
                WHEN usd_equivalent_amount IS NOT NULL AND usd_equivalent_amount > 0 THEN usd_equivalent_amount
                ELSE total_amount
            END
        ), 0) as total FROM invoices WHERE tenant_id = %s
        """
        amount_result = db_manager.execute_query(amount_query, (tenant_id,), fetch_one=True)
        total_amount = amount_result['total'] if amount_result else 0

        # Unique vendors
        vendors_result = db_manager.execute_query("SELECT COUNT(DISTINCT vendor_name) as count FROM invoices WHERE tenant_id = %s AND vendor_name IS NOT NULL AND vendor_name != ''", (tenant_id,), fetch_one=True)
        unique_vendors = vendors_result['count'] if vendors_result else 0

        # Unique customers
        customers_result = db_manager.execute_query("SELECT COUNT(DISTINCT customer_name) as count FROM invoices WHERE tenant_id = %s AND customer_name IS NOT NULL AND customer_name != ''", (tenant_id,), fetch_one=True)
        unique_customers = customers_result['count'] if customers_result else 0

        # By business unit
        bu_counts = {}
        try:
            bu_query = """
            SELECT business_unit, COUNT(*) as count,
                SUM(CASE
                    WHEN currency = 'USD' THEN total_amount
                    WHEN usd_equivalent_amount IS NOT NULL AND usd_equivalent_amount > 0 THEN usd_equivalent_amount
                    ELSE total_amount
                END) as total
            FROM invoices WHERE tenant_id = %s AND business_unit IS NOT NULL GROUP BY business_unit
            """
            bu_rows = db_manager.execute_query(bu_query, (tenant_id,), fetch_all=True)
            if bu_rows:
                for row in bu_rows:
                    bu_counts[row['business_unit']] = {'count': row['count'], 'total': row['total']}
        except:
            pass  # Column might not exist

        # By category
        category_counts = {}
        try:
            category_query = """
            SELECT category, COUNT(*) as count,
                SUM(CASE
                    WHEN currency = 'USD' THEN total_amount
                    WHEN usd_equivalent_amount IS NOT NULL AND usd_equivalent_amount > 0 THEN usd_equivalent_amount
                    ELSE total_amount
                END) as total
            FROM invoices WHERE tenant_id = %s AND category IS NOT NULL GROUP BY category
            """
            category_rows = db_manager.execute_query(category_query, (tenant_id,), fetch_all=True)
            if category_rows:
                for row in category_rows:
                    category_counts[row['category']] = {'count': row['count'], 'total': row['total']}
        except:
            pass  # Column might not exist

        # By customer
        customer_counts = {}
        customer_query = """
        SELECT customer_name, COUNT(*) as count,
            SUM(CASE
                WHEN currency = 'USD' THEN total_amount
                WHEN usd_equivalent_amount IS NOT NULL AND usd_equivalent_amount > 0 THEN usd_equivalent_amount
                ELSE total_amount
            END) as total
        FROM invoices WHERE tenant_id = %s AND customer_name IS NOT NULL AND customer_name != ''
        GROUP BY customer_name ORDER BY COUNT(*) DESC LIMIT 10
        """
        customer_rows = db_manager.execute_query(customer_query, (tenant_id,), fetch_all=True)
        if customer_rows:
            for row in customer_rows:
                customer_counts[row['customer_name']] = {'count': row['count'], 'total': row['total']}

        # Recent invoices
        recent_rows = db_manager.execute_query("SELECT * FROM invoices WHERE tenant_id = %s ORDER BY created_at DESC LIMIT 5", (tenant_id,), fetch_all=True)
        recent_invoices = [dict(row) for row in recent_rows] if recent_rows else []

        return jsonify({
            'total_invoices': total,
            'total_amount': float(total_amount),
            'unique_vendors': unique_vendors,
            'unique_customers': unique_customers,
            'business_unit_breakdown': bu_counts,
            'category_breakdown': category_counts,
            'customer_breakdown': customer_counts,
            'recent_invoices': recent_invoices
        })

    except Exception as e:
        logger.error(f"Error getting invoice stats: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# CURRENCY CONVERSION API ENDPOINTS
# ============================================================================

@app.route('/api/invoices/convert-currencies', methods=['POST'])
def api_convert_currencies():
    """Bulk convert invoice currencies to USD using historical rates"""
    try:
        global currency_converter
        if not currency_converter:
            return jsonify({'error': 'Currency converter not available'}), 503

        data = request.get_json() or {}
        limit = data.get('limit', 50)

        # Perform bulk conversion
        results = currency_converter.bulk_convert_invoices(limit)

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        logger.error(f"Error converting currencies: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/conversion-stats')
def api_conversion_stats():
    """Get currency conversion statistics"""
    try:
        global currency_converter
        if not currency_converter:
            return jsonify({'error': 'Currency converter not available'}), 503

        # Get conversion statistics
        stats = currency_converter.get_conversion_stats()

        return jsonify({
            'success': True,
            'stats': dict(stats) if stats else {}
        })

    except Exception as e:
        logger.error(f"Error getting conversion stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/<invoice_id>/convert', methods=['POST'])
def api_convert_single_invoice(invoice_id):
    """Convert a single invoice to USD using historical rates"""
    try:
        global currency_converter
        if not currency_converter:
            return jsonify({'error': 'Currency converter not available'}), 503

        from database import db_manager

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        # Get invoice data
        invoice = db_manager.execute_query(
            "SELECT * FROM invoices WHERE tenant_id = %s AND id = %s",
            (tenant_id, invoice_id),
            fetch_one=True
        )

        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404

        # Convert the invoice
        conversion = currency_converter.convert_invoice_amount(
            float(invoice['total_amount']),
            invoice['currency'],
            invoice['date']
        )

        # Update invoice with USD equivalent if conversion was successful
        if conversion['conversion_successful']:
            currency_converter._update_invoice_usd_amount(
                invoice['id'],
                conversion['converted_amount'],
                conversion['exchange_rate'],
                conversion['rate_date'],
                conversion['source']
            )

        return jsonify({
            'success': True,
            'conversion': conversion
        })

    except Exception as e:
        logger.error(f"Error converting single invoice: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/invoices/<invoice_id>/related-transaction')
def api_get_invoice_related_transaction(invoice_id):
    """Get transaction linked to an invoice for bidirectional navigation"""
    try:
        from database import db_manager
        tenant_id = get_current_tenant_id()

        # Get invoice with linked transaction info
        query = """
            SELECT
                i.id as invoice_id,
                i.invoice_number,
                i.linked_transaction_id,
                t.description as transaction_description,
                t.amount as transaction_amount,
                t.date as transaction_date,
                t.classified_entity,
                t.accounting_category
            FROM invoices i
            LEFT JOIN transactions t ON i.linked_transaction_id = t.transaction_id
            WHERE i.tenant_id = %s AND i.id = %s
        """

        result = db_manager.execute_query(query, (tenant_id, invoice_id), fetch_one=True)

        if not result:
            return jsonify({'error': 'Invoice not found'}), 404

        if not result['linked_transaction_id']:
            return jsonify({
                'success': True,
                'linked': False,
                'message': 'Invoice not linked to any transaction'
            })

        return jsonify({
            'success': True,
            'linked': True,
            'transaction': {
                'id': result['linked_transaction_id'],
                'description': result['transaction_description'],
                'amount': result['transaction_amount'],
                'date': result['transaction_date'],
                'classified_entity': result['classified_entity'],
                'accounting_category': result['accounting_category']
            }
        })

    except Exception as e:
        logger.error(f"Error getting related transaction for invoice {invoice_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<transaction_id>/related-invoice')
def api_get_transaction_related_invoice(transaction_id):
    """Get invoice linked to a transaction for bidirectional navigation"""
    try:
        from database import db_manager
        tenant_id = get_current_tenant_id()

        # Get transaction with linked invoice info
        query = """
            SELECT
                t.transaction_id,
                t.description as transaction_description,
                t.invoice_id,
                i.invoice_number,
                i.vendor_name,
                i.customer_name,
                i.total_amount as invoice_amount,
                i.date as invoice_date
            FROM transactions t
            LEFT JOIN invoices i ON t.invoice_id = i.id
            WHERE t.tenant_id = %s AND t.transaction_id = %s
        """

        result = db_manager.execute_query(query, (tenant_id, transaction_id), fetch_one=True)

        if not result:
            return jsonify({'error': 'Transaction not found'}), 404

        if not result['invoice_id']:
            return jsonify({
                'success': True,
                'linked': False,
                'message': 'Transaction not linked to any invoice'
            })

        return jsonify({
            'success': True,
            'linked': True,
            'invoice': {
                'id': result['invoice_id'],
                'invoice_number': result['invoice_number'],
                'vendor_name': result['vendor_name'],
                'customer_name': result['customer_name'],
                'amount': result['invoice_amount'],
                'date': result['invoice_date']
            }
        })

    except Exception as e:
        logger.error(f"Error getting related invoice for transaction {transaction_id}: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# BACKGROUND JOBS API ENDPOINTS
# ============================================================================

@app.route('/api/jobs/<job_id>')
def api_get_job_status(job_id):
    """Get status and progress of a background job"""
    try:
        job_status = get_job_status(job_id)

        if 'error' in job_status:
            return jsonify(job_status), 404

        return jsonify({
            'success': True,
            'data': job_status
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs')
def api_list_jobs():
    """List recent background jobs with pagination"""
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 50)  # Max 50 per page
        offset = (page - 1) * per_page

        # Get job filter
        status_filter = request.args.get('status')  # pending, processing, completed, failed
        job_type_filter = request.args.get('job_type')  # invoice_batch, etc.

        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'

        # Build query with filters
        where_clauses = []
        params = []

        if status_filter:
            where_clauses.append(f"status = {placeholder}")
            params.append(status_filter)

        if job_type_filter:
            where_clauses.append(f"job_type = {placeholder}")
            params.append(job_type_filter)

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        # Get total count
        count_query = f"SELECT COUNT(*) FROM background_jobs {where_clause}"
        cursor.execute(count_query, params)
        total_result = cursor.fetchone()
        total = total_result['count'] if is_postgresql else total_result[0]

        # Get jobs with pagination
        params.extend([per_page, offset])
        jobs_query = f"""
            SELECT id, job_type, status, total_items, processed_items, successful_items,
                   failed_items, progress_percentage, started_at, completed_at, created_at,
                   created_by, source_file, error_message
            FROM background_jobs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT {placeholder} OFFSET {placeholder}
        """

        cursor.execute(jobs_query, params)
        jobs = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return jsonify({
            'jobs': jobs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs/<job_id>/cancel', methods=['POST'])
def api_cancel_job(job_id):
    """Cancel a running background job"""
    try:
        # Get current job status
        job_status = get_job_status(job_id)

        if 'error' in job_status:
            return jsonify({'error': 'Job not found'}), 404

        current_status = job_status.get('status')

        if current_status in ['completed', 'failed']:
            return jsonify({'error': f'Cannot cancel job that is already {current_status}'}), 400

        # Update job status to cancelled
        update_job_progress(job_id, status='cancelled',
                          error_message='Job cancelled by user')

        return jsonify({
            'success': True,
            'message': 'Job cancelled successfully',
            'job_id': job_id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def safe_insert_invoice(conn, invoice_data):
    """
    Safely insert or update invoice to avoid UNIQUE constraint errors
    """
    # Get current tenant_id for multi-tenant isolation
    tenant_id = get_current_tenant_id()

    cursor = conn.cursor()

    # Detect database type for compatible syntax
    is_postgresql = hasattr(cursor, 'mogrify')  # PostgreSQL-specific method

    # Check if invoice exists
    if is_postgresql:
        cursor.execute('SELECT id FROM invoices WHERE tenant_id = %s AND invoice_number = %s', (tenant_id, invoice_data['invoice_number']))
    else:
        cursor.execute('SELECT id FROM invoices WHERE tenant_id = ? AND invoice_number = ?', (tenant_id, invoice_data['invoice_number']))
    existing = cursor.fetchone()

    if existing:
        # Update existing invoice
        if is_postgresql:
            cursor.execute("""
                UPDATE invoices SET
                    date=%s, due_date=%s, vendor_name=%s, vendor_address=%s,
                    vendor_tax_id=%s, customer_name=%s, customer_address=%s, customer_tax_id=%s,
                    total_amount=%s, currency=%s, tax_amount=%s, subtotal=%s,
                    line_items=%s, status=%s, invoice_type=%s, confidence_score=%s, processing_notes=%s,
                    source_file=%s, extraction_method=%s, processed_at=%s, created_at=%s,
                    business_unit=%s, category=%s, currency_type=%s
                WHERE invoice_number=%s
            """, (
                invoice_data['date'], invoice_data['due_date'], invoice_data['vendor_name'],
                invoice_data['vendor_address'], invoice_data['vendor_tax_id'], invoice_data['customer_name'],
                invoice_data['customer_address'], invoice_data['customer_tax_id'], invoice_data['total_amount'],
                invoice_data['currency'], invoice_data['tax_amount'], invoice_data['subtotal'],
                invoice_data['line_items'], invoice_data['status'], invoice_data['invoice_type'],
                invoice_data['confidence_score'], invoice_data['processing_notes'], invoice_data['source_file'],
                invoice_data['extraction_method'], invoice_data['processed_at'], invoice_data['created_at'],
                invoice_data['business_unit'], invoice_data['category'], invoice_data['currency_type'],
                invoice_data['invoice_number']
            ))
        else:
            cursor.execute("""
                UPDATE invoices SET
                    date=?, due_date=?, vendor_name=?, vendor_address=?,
                    vendor_tax_id=?, customer_name=?, customer_address=?, customer_tax_id=?,
                    total_amount=?, currency=?, tax_amount=?, subtotal=?,
                    line_items=?, status=?, invoice_type=?, confidence_score=?, processing_notes=?,
                    source_file=?, extraction_method=?, processed_at=?, created_at=?,
                    business_unit=?, category=?, currency_type=?
                WHERE invoice_number=?
            """, (
                invoice_data['date'], invoice_data['due_date'], invoice_data['vendor_name'],
                invoice_data['vendor_address'], invoice_data['vendor_tax_id'], invoice_data['customer_name'],
                invoice_data['customer_address'], invoice_data['customer_tax_id'], invoice_data['total_amount'],
                invoice_data['currency'], invoice_data['tax_amount'], invoice_data['subtotal'],
                invoice_data['line_items'], invoice_data['status'], invoice_data['invoice_type'],
                invoice_data['confidence_score'], invoice_data['processing_notes'], invoice_data['source_file'],
                invoice_data['extraction_method'], invoice_data['processed_at'], invoice_data['created_at'],
                invoice_data['business_unit'], invoice_data['category'], invoice_data['currency_type'],
                invoice_data['invoice_number']
            ))
        print(f"Updated existing invoice: {invoice_data['invoice_number']}")
        return "updated"
    else:
        # Insert new invoice
        if is_postgresql:
            cursor.execute("""
                INSERT INTO invoices (
                    id, tenant_id, invoice_number, date, due_date, vendor_name, vendor_address,
                    vendor_tax_id, customer_name, customer_address, customer_tax_id,
                    total_amount, currency, tax_amount, subtotal,
                    line_items, status, invoice_type, confidence_score, processing_notes,
                    source_file, extraction_method, processed_at, created_at,
                    business_unit, category, currency_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                invoice_data['id'], tenant_id, invoice_data['invoice_number'], invoice_data['date'],
                invoice_data['due_date'], invoice_data['vendor_name'], invoice_data['vendor_address'],
                invoice_data['vendor_tax_id'], invoice_data['customer_name'], invoice_data['customer_address'],
                invoice_data['customer_tax_id'], invoice_data['total_amount'], invoice_data['currency'],
                invoice_data['tax_amount'], invoice_data['subtotal'], invoice_data['line_items'],
                invoice_data['status'], invoice_data['invoice_type'], invoice_data['confidence_score'],
                invoice_data['processing_notes'], invoice_data['source_file'], invoice_data['extraction_method'],
                invoice_data['processed_at'], invoice_data['created_at'], invoice_data['business_unit'],
                invoice_data['category'], invoice_data['currency_type']
            ))
        else:
            cursor.execute("""
                INSERT INTO invoices (
                    id, tenant_id, invoice_number, date, due_date, vendor_name, vendor_address,
                    vendor_tax_id, customer_name, customer_address, customer_tax_id,
                    total_amount, currency, tax_amount, subtotal,
                    line_items, status, invoice_type, confidence_score, processing_notes,
                    source_file, extraction_method, processed_at, created_at,
                    business_unit, category, currency_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_data['id'], tenant_id, invoice_data['invoice_number'], invoice_data['date'],
                invoice_data['due_date'], invoice_data['vendor_name'], invoice_data['vendor_address'],
                invoice_data['vendor_tax_id'], invoice_data['customer_name'], invoice_data['customer_address'],
                invoice_data['customer_tax_id'], invoice_data['total_amount'], invoice_data['currency'],
                invoice_data['tax_amount'], invoice_data['subtotal'], invoice_data['line_items'],
                invoice_data['status'], invoice_data['invoice_type'], invoice_data['confidence_score'],
                invoice_data['processing_notes'], invoice_data['source_file'], invoice_data['extraction_method'],
                invoice_data['processed_at'], invoice_data['created_at'], invoice_data['business_unit'],
                invoice_data['category'], invoice_data['currency_type']
            ))
        print(f"Inserted new invoice: {invoice_data['invoice_number']}")
        return "inserted"

def preprocess_invoice_data(invoice_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ultra-robust preprocessing to handle all common failure cases"""
    import re
    from datetime import datetime, timedelta

    if 'error' in invoice_data:
        return invoice_data

    # Layer 2A: Date field cleaning
    problematic_dates = ['DUE ON RECEIPT', 'Due on Receipt', 'Due on receipt', 'PAID', 'NET 30', 'NET 15', 'UPON RECEIPT']

    if 'due_date' in invoice_data:
        due_date = str(invoice_data['due_date']).strip()
        if due_date.upper() in [d.upper() for d in problematic_dates]:
            # Convert to NULL for database
            invoice_data['due_date'] = None
            print(f" Cleaned problematic due_date: '{due_date}' -> NULL")
        elif due_date.upper() == 'NET 30':
            # Smart conversion: NET 30 = invoice_date + 30 days
            try:
                if invoice_data.get('date'):
                    invoice_date = datetime.strptime(invoice_data['date'], '%Y-%m-%d')
                    invoice_data['due_date'] = (invoice_date + timedelta(days=30)).strftime('%Y-%m-%d')
                    print(f" Smart conversion: NET 30 -> {invoice_data['due_date']}")
                else:
                    invoice_data['due_date'] = None
            except:
                invoice_data['due_date'] = None

    # Layer 2B: Field length limits and cleaning
    field_limits = {
        'currency': 45,  # Allow up to 45 chars (we expanded to 50, keeping 5 char buffer)
        'invoice_number': 100,
        'vendor_name': 200,
        'customer_name': 200
    }

    for field, limit in field_limits.items():
        if field in invoice_data and invoice_data[field]:
            original_value = str(invoice_data[field])
            if len(original_value) > limit:
                invoice_data[field] = original_value[:limit].strip()
                print(f" Truncated {field}: '{original_value[:20]}...' ({len(original_value)} chars -> {limit})")

    # Layer 2C: Currency normalization
    if 'currency' in invoice_data and invoice_data['currency']:
        currency = str(invoice_data['currency']).strip()
        # Extract common currency codes from mixed strings
        currency_patterns = {
            r'USD|US\$|\$': 'USD',
            r'EUR|€': 'EUR',
            r'BTC|₿': 'BTC',
            r'PYG|₲': 'PYG'
        }

        for pattern, code in currency_patterns.items():
            if re.search(pattern, currency, re.IGNORECASE):
                if currency != code:
                    print(f" Normalized currency: '{currency}' -> '{code}'")
                    invoice_data['currency'] = code
                break
        else:
            # If no pattern matches, keep first 3 chars as currency code
            if len(currency) > 3:
                invoice_data['currency'] = currency[:3].upper()
                print(f" Currency code extracted: '{currency}' -> '{invoice_data['currency']}'")

    return invoice_data

def repair_json_string(json_str: str) -> str:
    """Repair common JSON formatting issues"""
    import re

    # Fix missing commas between objects
    json_str = re.sub(r'"\s*\n\s*"', '",\n  "', json_str)

    # Fix missing commas after values
    json_str = re.sub(r'(\d+|"[^"]*"|\]|\})\s*\n\s*"', r'\1,\n  "', json_str)

    # Fix trailing commas
    json_str = re.sub(r',(\s*[\}\]])', r'\1', json_str)

    # Ensure proper quotes around keys
    json_str = re.sub(r'(\w+):', r'"\1":', json_str)

    return json_str

def fallback_extract_invoice_data(text: str) -> dict:
    """Fallback extraction using regex when JSON parsing fails"""
    import re

    data = {}

    # Common field patterns
    patterns = {
        'invoice_number': r'"invoice_number":\s*"([^"]*)"',
        'vendor_name': r'"vendor_name":\s*"([^"]*)"',
        'total_amount': r'"total_amount":\s*([0-9.]+)',
        'currency': r'"currency":\s*"([^"]*)"',
        'date': r'"date":\s*"([^"]*)"'
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1)
            if field == 'total_amount':
                try:
                    data[field] = float(value)
                except:
                    data[field] = 0.0
            else:
                data[field] = value

    # Return None if no essential fields found
    if not data.get('vendor_name') and not data.get('total_amount'):
        return None

    # Fill in defaults for missing fields
    data.setdefault('invoice_number', f'AUTO_{int(time.time())}')
    data.setdefault('currency', 'USD')
    data.setdefault('date', datetime.now().strftime('%Y-%m-%d'))

    return data

def process_invoice_with_claude(file_path: str, original_filename: str) -> Dict[str, Any]:
    """Process invoice file with Claude Vision API"""
    try:
        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        global claude_client

        # Initialize Claude client if not already done (lazy initialization)
        if not claude_client:
            init_success = init_claude_client()
            if not init_success or not claude_client:
                return {'error': 'Claude API client not initialized - check ANTHROPIC_API_KEY environment variable'}

        # Read and encode image
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.pdf':
            # Convert PDF to image using PyMuPDF
            try:
                import fitz  # PyMuPDF

                # Open PDF and get first page
                doc = fitz.open(file_path)
                if doc.page_count == 0:
                    return {'error': 'PDF has no pages'}

                # Get first page as image with 2x zoom for better quality
                page = doc.load_page(0)
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)

                # Convert to PNG bytes
                image_bytes = pix.pil_tobytes(format="PNG")
                doc.close()

                # Encode to base64
                image_data = base64.b64encode(image_bytes).decode('utf-8')
                media_type = 'image/png'

            except ImportError:
                return {'error': 'PyMuPDF not installed. Run: pip install PyMuPDF'}
            except Exception as e:
                return {'error': f'PDF conversion failed: {str(e)}'}
        else:
            # Read image file
            with open(file_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Determine media type
            media_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.tiff': 'image/tiff'
            }
            media_type = media_types.get(file_ext, 'image/png')

        # Build extraction prompt
        prompt = """Analyze this invoice image and extract BOTH vendor (who is sending/issuing the invoice) AND customer (who is receiving/paying the invoice) information in JSON format.

IMPORTANT: Distinguish between the two parties on the invoice:
- VENDOR/SUPPLIER (From/De/Remetente): The company ISSUING/SENDING the invoice
- CUSTOMER/CLIENT (To/Para/Destinatário): The company RECEIVING/PAYING the invoice

Common invoice keywords to help identify:
- Vendor indicators: "From", "Bill From", "Vendor", "Supplier", "De", "Remetente", "Fornecedor", "Issued by"
- Customer indicators: "To", "Bill To", "Sold To", "Client", "Customer", "Para", "Destinatário", "Cliente"

REQUIRED FIELDS:
- invoice_number: The invoice/bill number
- date: Invoice date (YYYY-MM-DD format)
- vendor_name: Company name ISSUING the invoice (FROM)
- customer_name: Company name RECEIVING the invoice (TO)
- total_amount: Total amount (numeric value only)
- currency: Currency (USD, BRL, PYG, etc.)

OPTIONAL VENDOR FIELDS:
- vendor_address: Vendor's address
- vendor_tax_id: Vendor's Tax ID/CNPJ/EIN/RUC if present

OPTIONAL CUSTOMER FIELDS:
- customer_address: Customer's address
- customer_tax_id: Customer's Tax ID/CNPJ/EIN/RUC if present

OTHER OPTIONAL FIELDS:
- due_date: Due date ONLY if a SPECIFIC DATE is present (YYYY-MM-DD format). For text like "DUE ON RECEIPT", "NET 30", "PAID", use null
- tax_amount: Tax amount if itemized
- subtotal: Subtotal before tax
- line_items: Array of line items with description, quantity, unit_price, total

CRITICAL FORMATTING RULES:
1. DATES: Only use YYYY-MM-DD format or null. NEVER use text like "DUE ON RECEIPT", "NET 30", "PAID"
2. CURRENCY: Use standard 3-letter codes (USD, EUR, BTC, PYG). If unclear, extract first 3 characters
3. JSON: MUST be valid JSON with all commas and quotes correct. Double-check syntax
4. NUMBERS: Use numeric values only (e.g., 150.50, not "$150.50")

 EXAMPLES:
[ERROR] "due_date": "DUE ON RECEIPT"
[OK] "due_date": null

[ERROR] "currency": "US Dollars"
[OK] "currency": "USD"

[ERROR] "total_amount": "$1,500.00"
[OK] "total_amount": 1500.00

CLASSIFICATION HINTS:
Based on the customer (who is paying), suggest:
- business_unit: One of ["Delta LLC", "Delta Prop Shop LLC", "Delta Mining Paraguay S.A.", "Delta Brazil", "Personal"]
- category: One of ["Technology Expenses", "Utilities", "Insurance", "Professional Services", "Office Expenses", "Other"]

Return ONLY a JSON object with this structure:
{
    "invoice_number": "string",
    "date": "YYYY-MM-DD",
    "vendor_name": "string (FROM - who is sending the invoice)",
    "vendor_address": "string",
    "vendor_tax_id": "string",
    "customer_name": "string (TO - who is receiving/paying the invoice)",
    "customer_address": "string",
    "customer_tax_id": "string",
    "total_amount": 1234.56,
    "currency": "USD",
    "tax_amount": 123.45,
    "subtotal": 1111.11,
    "due_date": "YYYY-MM-DD",
    "line_items": [
        {"description": "Item 1", "quantity": 1, "unit_price": 100.00, "total": 100.00}
    ],
    "business_unit": "Delta LLC",
    "category": "Technology Expenses",
    "confidence": 0.95,
    "processing_notes": "Any issues or observations"
}

Be precise with numbers and dates. If a field is not clearly visible, use null.
CRITICAL: Make sure vendor_name is who SENT the invoice and customer_name is who RECEIVES/PAYS the invoice."""

        # Call Claude Vision API
        response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4000,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        # Parse response
        response_text = response.content[0].text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()

        # LAYER 3: JSON repair and retry logic
        extracted_data = None
        json_parse_attempts = 0
        max_json_attempts = 3

        while extracted_data is None and json_parse_attempts < max_json_attempts:
            json_parse_attempts += 1
            try:
                extracted_data = json.loads(response_text)
                if json_parse_attempts > 1:
                    print(f"[OK] JSON parsed successfully on attempt {json_parse_attempts}")
                break
            except json.JSONDecodeError as e:
                print(f"WARNING: JSON parse attempt {json_parse_attempts} failed: {str(e)[:100]}")

                if json_parse_attempts < max_json_attempts:
                    # LAYER 3A: Auto-repair common JSON issues
                    response_text = repair_json_string(response_text)
                    print(f" Applied JSON auto-repair, retrying...")
                else:
                    # LAYER 3B: If all repairs fail, try regex fallback
                    print(f"[ERROR] JSON parsing failed after {max_json_attempts} attempts, trying fallback extraction...")
                    extracted_data = fallback_extract_invoice_data(response_text)
                    if extracted_data:
                        print("[OK] Fallback extraction succeeded")
                    else:
                        raise json.JSONDecodeError(f"Failed to parse or repair JSON after {max_json_attempts} attempts", response_text, 0)

        # Generate invoice ID
        invoice_id = str(uuid.uuid4())

        # Prepare invoice data for database
        invoice_data = {
            'id': invoice_id,
            'invoice_number': extracted_data.get('invoice_number', ''),
            'date': extracted_data.get('date'),
            'due_date': extracted_data.get('due_date'),
            'vendor_name': extracted_data.get('vendor_name', ''),
            'vendor_address': extracted_data.get('vendor_address'),
            'vendor_tax_id': extracted_data.get('vendor_tax_id'),
            'customer_name': extracted_data.get('customer_name', ''),
            'customer_address': extracted_data.get('customer_address'),
            'customer_tax_id': extracted_data.get('customer_tax_id'),
            'total_amount': float(extracted_data.get('total_amount', 0)),
            'currency': extracted_data.get('currency', 'USD'),
            'tax_amount': float(extracted_data.get('tax_amount', 0)) if extracted_data.get('tax_amount') else None,
            'subtotal': float(extracted_data.get('subtotal', 0)) if extracted_data.get('subtotal') else None,
            'line_items': json.dumps(extracted_data.get('line_items', [])),
            'status': 'pending',
            'invoice_type': 'other',
            'confidence_score': float(extracted_data.get('confidence', 0.8)),
            'processing_notes': extracted_data.get('processing_notes', ''),
            'source_file': original_filename,
            'extraction_method': 'claude_vision',
            'processed_at': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat(),
            'business_unit': extracted_data.get('business_unit'),
            'category': extracted_data.get('category'),
            'currency_type': 'fiat'  # Can be enhanced later
        }

        # LAYER 2: Ultra-robust preprocessing to handle all failure cases
        invoice_data = preprocess_invoice_data(invoice_data)

        # If preprocessing detected an error, return it
        if 'error' in invoice_data:
            return invoice_data

        # Save to database with robust connection handling
        max_retries = 3
        for attempt in range(max_retries):
            try:
                from database import db_manager
                conn = db_manager._get_postgresql_connection()

                # Check if invoice_number already exists
                cursor = conn.cursor()

                # Detect database type for compatible syntax
                is_postgresql = hasattr(cursor, 'mogrify')  # PostgreSQL-specific method

                if is_postgresql:
                    cursor.execute('SELECT id FROM invoices WHERE tenant_id = %s AND invoice_number = %s', (tenant_id, invoice_data['invoice_number']))
                else:
                    cursor.execute('SELECT id FROM invoices WHERE tenant_id = ? AND invoice_number = ?', (tenant_id, invoice_data['invoice_number']))
                existing = cursor.fetchone()

                if existing:
                    # Generate unique invoice number by appending timestamp
                    timestamp = int(time.time())
                    original_number = invoice_data['invoice_number']
                    invoice_data['invoice_number'] = f"{original_number}_{timestamp}"
                    print(f"Duplicate invoice number detected. Changed {original_number} to {invoice_data['invoice_number']}")

                # Use database-specific syntax for insert
                if is_postgresql:
                    cursor.execute('''
                        INSERT INTO invoices (
                            id, tenant_id, invoice_number, date, due_date, vendor_name, vendor_address,
                            vendor_tax_id, customer_name, customer_address, customer_tax_id,
                            total_amount, currency, tax_amount, subtotal,
                            line_items, status, invoice_type, confidence_score, processing_notes,
                            source_file, extraction_method, processed_at, created_at,
                            business_unit, category, currency_type
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        invoice_data['id'], tenant_id, invoice_data['invoice_number'], invoice_data['date'],
                        invoice_data['due_date'], invoice_data['vendor_name'], invoice_data['vendor_address'],
                        invoice_data['vendor_tax_id'], invoice_data['customer_name'], invoice_data['customer_address'],
                        invoice_data['customer_tax_id'], invoice_data['total_amount'], invoice_data['currency'],
                        invoice_data['tax_amount'], invoice_data['subtotal'], invoice_data['line_items'],
                        invoice_data['status'], invoice_data['invoice_type'], invoice_data['confidence_score'],
                        invoice_data['processing_notes'], invoice_data['source_file'], invoice_data['extraction_method'],
                        invoice_data['processed_at'], invoice_data['created_at'], invoice_data['business_unit'],
                        invoice_data['category'], invoice_data['currency_type']
                    ))
                else:
                    cursor.execute('''
                        INSERT INTO invoices (
                            id, tenant_id, invoice_number, date, due_date, vendor_name, vendor_address,
                            vendor_tax_id, customer_name, customer_address, customer_tax_id,
                            total_amount, currency, tax_amount, subtotal,
                            line_items, status, invoice_type, confidence_score, processing_notes,
                            source_file, extraction_method, processed_at, created_at,
                            business_unit, category, currency_type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        invoice_data['id'], tenant_id, invoice_data['invoice_number'], invoice_data['date'],
                        invoice_data['due_date'], invoice_data['vendor_name'], invoice_data['vendor_address'],
                        invoice_data['vendor_tax_id'], invoice_data['customer_name'], invoice_data['customer_address'],
                        invoice_data['customer_tax_id'], invoice_data['total_amount'], invoice_data['currency'],
                        invoice_data['tax_amount'], invoice_data['subtotal'], invoice_data['line_items'],
                        invoice_data['status'], invoice_data['invoice_type'], invoice_data['confidence_score'],
                        invoice_data['processing_notes'], invoice_data['source_file'], invoice_data['extraction_method'],
                        invoice_data['processed_at'], invoice_data['created_at'], invoice_data['business_unit'],
                        invoice_data['category'], invoice_data['currency_type']
                    ))
                conn.commit()
                conn.close()
                print(f"Invoice processed successfully: {invoice_data['invoice_number']}")
                return invoice_data
            except sqlite3.OperationalError as e:
                if conn:
                    conn.close()
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"Database locked during invoice insert, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"Database error after {attempt + 1} attempts: {e}")
                    return {'error': f'Database locked after {attempt + 1} attempts: {str(e)}'}
            except Exception as e:
                # Handle both SQLite and PostgreSQL integrity errors
                is_integrity_error = (
                    isinstance(e, sqlite3.IntegrityError) or
                    (POSTGRESQL_AVAILABLE and hasattr(psycopg2, 'IntegrityError') and isinstance(e, psycopg2.IntegrityError))
                )
                if conn:
                    conn.close()
                # Handle duplicate invoice number constraint violations
                if is_integrity_error and ("duplicate key value violates unique constraint" in str(e) or "UNIQUE constraint failed" in str(e)):
                    if attempt < max_retries - 1:
                        # Generate new unique invoice number with timestamp
                        timestamp = int(time.time() * 1000) + attempt  # More unique with attempt number
                        original_number = invoice_data.get('invoice_number', 'UNKNOWN')
                        invoice_data['invoice_number'] = f"{original_number}_{timestamp}"
                        print(f"Duplicate constraint violation. Retrying with unique number: {invoice_data['invoice_number']}")
                        time.sleep(0.1)  # Small delay to avoid further collisions
                        continue
                    else:
                        print(f"Failed to resolve duplicate after {max_retries} attempts: {e}")
                        return {'error': f'Duplicate invoice number could not be resolved: {str(e)}'}
                else:
                    print(f"Unexpected error during invoice insert: {e}")
                    return {'error': str(e)}

    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON response from Claude: {e}")
        return {'error': f'Invalid JSON response from Claude Vision: {str(e)}'}
    except Exception as e:
        print(f"ERROR: Invoice processing failed: {e}")
        traceback.print_exc()
        return {'error': str(e)}

# ============================================================================
# REINFORCEMENT LEARNING SYSTEM
# ============================================================================

def log_user_interaction(transaction_id: str, field_type: str, original_value: str,
                        ai_suggestions: list, user_choice: str, action_type: str,
                        transaction_context: dict, session_id: str = None):
    """Log user interactions for learning system"""
    try:
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        conn.execute("""
            INSERT INTO user_interactions (
                transaction_id, field_type, original_value, ai_suggestions,
                user_choice, action_type, transaction_context, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction_id, field_type, original_value,
            json.dumps(ai_suggestions), user_choice, action_type,
            json.dumps(transaction_context), session_id
        ))
        conn.commit()
        conn.close()
        print(f"SUCCESS: Logged user interaction: {action_type} for {field_type}")

        # Update performance metrics
        update_ai_performance_metrics(field_type, action_type == 'accepted_ai_suggestion')

        # Learn from this interaction
        learn_from_interaction(transaction_id, field_type, user_choice, transaction_context)

    except Exception as e:
        print(f"ERROR: Error logging user interaction: {e}")

def update_ai_performance_metrics(field_type: str, was_accepted: bool):
    """Update daily AI performance metrics"""
    try:
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        today = datetime.now().date()

        # Get existing metrics for today
        existing = conn.execute("""
            SELECT total_suggestions, accepted_suggestions
            FROM ai_performance_metrics
            WHERE date = ? AND field_type = ?
        """, (today, field_type)).fetchone()

        if existing:
            total = existing[0] + 1
            accepted = existing[1] + (1 if was_accepted else 0)
            accuracy = accepted / total if total > 0 else 0

            conn.execute("""
                UPDATE ai_performance_metrics
                SET total_suggestions = ?, accepted_suggestions = ?, accuracy_rate = ?
                WHERE date = ? AND field_type = ?
            """, (total, accepted, accuracy, today, field_type))
        else:
            conn.execute("""
                INSERT INTO ai_performance_metrics
                (date, field_type, total_suggestions, accepted_suggestions, accuracy_rate)
                VALUES (?, ?, 1, ?, ?)
            """, (today, field_type, 1 if was_accepted else 0, 1.0 if was_accepted else 0.0))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"ERROR: Error updating performance metrics: {e}")

def learn_from_interaction(transaction_id: str, field_type: str, user_choice: str, context: dict):
    """Learn patterns from user interactions"""
    try:
        from database import db_manager
        conn = db_manager._get_postgresql_connection()

        # Create pattern condition based on transaction context
        pattern_condition = {}

        if field_type == 'description':
            # For descriptions, learn based on original description patterns
            original_desc = context.get('original_value', '')
            if 'M MERCHANT' in original_desc.upper():
                pattern_condition = {'contains': 'M MERCHANT'}
            elif 'DELTA PROP SHOP' in original_desc.upper():
                pattern_condition = {'contains': 'DELTA PROP SHOP'}
            elif 'CHASE' in original_desc.upper():
                pattern_condition = {'contains': 'CHASE'}

        elif field_type == 'accounting_category':
            # Learn based on entity and amount patterns
            pattern_condition = {
                'entity': context.get('classified_entity'),
                'amount_range': 'positive' if float(context.get('amount', 0)) > 0 else 'negative'
            }

        if pattern_condition:
            pattern_type = f"{field_type}_pattern"
            condition_json = json.dumps(pattern_condition)

            # Check if pattern exists
            existing = conn.execute("""
                SELECT id, usage_count, success_count, confidence_score
                FROM learned_patterns
                WHERE pattern_type = ? AND pattern_condition = ? AND suggested_value = ?
            """, (pattern_type, condition_json, user_choice)).fetchone()

            if existing:
                # Update existing pattern
                new_usage = existing[1] + 1
                new_success = existing[2] + 1
                new_confidence = min(0.95, existing[3] + 0.05)  # Increase confidence

                conn.execute("""
                    UPDATE learned_patterns
                    SET usage_count = ?, success_count = ?, confidence_score = ?, last_used = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (new_usage, new_success, new_confidence, existing[0]))
            else:
                # Create new pattern
                conn.execute("""
                    INSERT INTO learned_patterns
                    (pattern_type, pattern_condition, suggested_value, confidence_score)
                    VALUES (?, ?, ?, 0.7)
                """, (pattern_type, condition_json, user_choice))

            conn.commit()
            print(f"SUCCESS: Learned pattern: {pattern_type} -> {user_choice}")

        conn.close()
    except Exception as e:
        print(f"ERROR: Error learning from interaction: {e}")

def record_negative_pattern(field_type: str, rejected_value: str, transaction_context: dict):
    """
    ENHANCEMENT #3: Negative Pattern Learning
    Record when a user rejects an AI suggestion to avoid repeating the same mistake

    Negative patterns are stored with confidence_score = 0.0 to distinguish from positive patterns
    """
    try:
        from database import db_manager
        tenant_id = get_current_tenant_id()
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'

        # Build pattern condition based on transaction context
        condition = {
            'description': transaction_context.get('description', '').upper()[:50],  # First 50 chars
            'entity': transaction_context.get('classified_entity'),
            'amount_range': 'positive' if float(transaction_context.get('amount', 0)) > 0 else 'negative'
        }

        # Check if negative pattern already exists
        cursor.execute(f"""
            SELECT id, rejection_count
            FROM learned_patterns
            WHERE tenant_id = {placeholder}
            AND description_pattern LIKE {placeholder}
            AND suggested_{field_type} = {placeholder}
            AND confidence_score <= 0.1
        """, (tenant_id, f"%{condition['description'][:20]}%", rejected_value))

        existing = cursor.fetchone()

        if existing:
            # Increment rejection count for existing negative pattern
            pattern_id = existing[0] if isinstance(existing, tuple) else existing.get('id')
            cursor.execute(f"""
                UPDATE learned_patterns
                SET rejection_count = rejection_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = {placeholder}
            """, (pattern_id,))
        else:
            # Create new negative pattern with confidence = 0.0
            cursor.execute(f"""
                INSERT INTO learned_patterns (
                    tenant_id, description_pattern,
                    suggested_{field_type}, confidence_score,
                    usage_count, rejection_count, created_at, updated_at
                )
                VALUES ({placeholder}, {placeholder}, {placeholder}, 0.0, 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (tenant_id, condition['description'], rejected_value))

        conn.commit()
        cursor.close()
        conn.close()
        print(f" Recorded negative pattern: {field_type}={rejected_value} (rejected by user)")

    except Exception as e:
        print(f"ERROR: Failed to record negative pattern: {e}")
        import traceback
        traceback.print_exc()

def get_learned_suggestions(field_type: str, transaction_context: dict) -> list:
    """
    Get suggestions based on learned patterns

    ENHANCEMENT #3: Filters out negative patterns (confidence_score <= 0.1)
    Only returns positive patterns that users have accepted in the past
    """
    try:
        from database import db_manager
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        suggestions = []

        if field_type == 'description':
            original_desc = transaction_context.get('description', '').upper()

            # Check for learned patterns - EXCLUDE negative patterns (confidence <= 0.1)
            cursor.execute("""
                SELECT suggested_value, confidence_score, pattern_condition
                FROM learned_patterns
                WHERE pattern_type = 'description_pattern' AND confidence_score > 0.6
                ORDER BY confidence_score DESC, usage_count DESC
            """)
            patterns = cursor.fetchall()

            for pattern in patterns:
                condition = json.loads(pattern[2])
                if 'contains' in condition:
                    if condition['contains'] in original_desc:
                        suggestions.append({
                            'value': pattern[0],
                            'confidence': pattern[1],
                            'source': 'learned_pattern'
                        })

        elif field_type == 'accounting_category':
            entity = transaction_context.get('classified_entity')
            amount = float(transaction_context.get('amount', 0))
            amount_range = 'positive' if amount > 0 else 'negative'

            # EXCLUDE negative patterns (confidence <= 0.1)
            cursor.execute("""
                SELECT suggested_value, confidence_score, pattern_condition
                FROM learned_patterns
                WHERE pattern_type = 'accounting_category_pattern' AND confidence_score > 0.6
                ORDER BY confidence_score DESC, usage_count DESC
            """)
            patterns = cursor.fetchall()

            for pattern in patterns:
                condition = json.loads(pattern[2])
                if (condition.get('entity') == entity or
                    condition.get('amount_range') == amount_range):
                    suggestions.append({
                        'value': pattern[0],
                        'confidence': pattern[1],
                        'source': 'learned_pattern'
                    })

        cursor.close()
        conn.close()
        return suggestions[:3]  # Return top 3 learned suggestions

    except Exception as e:
        print(f"ERROR: Error getting learned suggestions: {e}")
        return []

def is_meaningful_pattern(term: str, entity: str, tenant_id: str = None) -> bool:
    """
    Filter out generic noise terms that don't help identify entities.

    Uses multiple heuristics:
    1. Blacklist of common generic terms
    2. Minimum term length
    3. Pure numbers/dates filtering
    4. Cross-entity frequency analysis (if term appears in >40% of entities, it's too generic)

    Returns:
        bool: True if term is meaningful and should be used for matching
    """
    # Blacklist of generic terms that don't help identification
    generic_terms = {
        # Transaction types
        'transaction', 'payment', 'transfer', 'deposit', 'withdrawal',
        'fee', 'charge', 'service', 'received', 'sent', 'purchase',

        # Prepositions and articles
        'from', 'to', 'at', 'for', 'with', 'and', 'the', 'a', 'an',
        'of', 'in', 'on', 'by', 'via', 'per',

        # Time references
        'date', 'time', 'today', 'yesterday', 'month', 'year', 'day',

        # Generic descriptors
        'external', 'internal', 'account', 'wallet', 'address',
        'total', 'amount', 'balance', 'pending', 'completed'
    }

    if not term or not isinstance(term, str):
        return False

    term_lower = term.lower().strip()

    # Filter generic terms
    if term_lower in generic_terms:
        return False

    # Require minimum length (3 characters)
    if len(term) < 3:
        return False

    # Filter out pure numbers, dates, or currency amounts
    # Remove common punctuation to check if what remains is just digits
    cleaned_term = term.replace('.', '').replace(',', '').replace('$', '').replace('-', '').replace('/', '').replace(':', '').strip()
    if cleaned_term.isdigit():
        return False

    # Check cross-entity frequency (only if tenant_id provided)
    if tenant_id:
        try:
            from database import db_manager
            conn = db_manager._get_postgresql_connection()
            cursor = conn.cursor()

            # Count how many distinct entities use this term
            cursor.execute("""
                SELECT COUNT(DISTINCT entity_name)
                FROM entity_patterns
                WHERE tenant_id = %s
                AND (
                    pattern_data::text ILIKE %s
                )
            """, (tenant_id, f'%{term}%'))

            entities_using_term = cursor.fetchone()[0]

            # Get total number of entities
            cursor.execute("""
                SELECT COUNT(DISTINCT entity_name)
                FROM entity_patterns
                WHERE tenant_id = %s
            """, (tenant_id,))

            total_entities = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            # If term appears in >40% of entities, it's too generic
            if total_entities > 0 and entities_using_term > (total_entities * 0.4):
                return False

        except Exception as e:
            # If database check fails, continue without it
            print(f"WARNING: Could not check cross-entity frequency for term '{term}': {e}")
            pass

    return True

# Fuzzy matching setup
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    print("WARNING: rapidfuzz not available - fuzzy matching disabled")

def fuzzy_match_pattern(pattern: str, description: str, threshold: int = 85) -> float:
    """
    Fuzzy match pattern against description using rapidfuzz.

    Args:
        pattern: The pattern term to search for
        description: The transaction description to search in
        threshold: Minimum similarity score to consider a match (0-100)

    Returns:
        float: Match score 0.0-1.0 (1.0 = perfect match, 0.0 = no match)
    """
    if not pattern or not description:
        return 0.0

    # Try exact match first (fastest)
    if pattern.upper() in description.upper():
        return 1.0

    if not RAPIDFUZZ_AVAILABLE:
        # Fallback to substring matching if rapidfuzz not available
        return 0.0

    # Use fuzzy matching for partial/typo tolerance
    similarity = fuzz.partial_ratio(pattern.upper(), description.upper())

    if similarity >= threshold:
        return similarity / 100.0

    return 0.0

def update_pattern_statistics(entity_name: str, pattern_term: str, pattern_type: str, tenant_id: str):
    """
    Incrementally update TF-IDF statistics when a new pattern is learned.

    This function:
    1. UPSERTs the pattern into entity_pattern_statistics
    2. Recalculates TF-IDF scores incrementally for this entity+term combination
    3. Enables real-time learning without full table recalculation

    Args:
        entity_name: The entity this pattern belongs to
        pattern_term: The actual pattern text (e.g., "EVERMINER", "hosting")
        pattern_type: Type of pattern (company_name, keyword, bank_identifier, etc.)
        tenant_id: Tenant ID for multi-tenant isolation
    """
    import math
    from database import db_manager

    try:
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        # Step 1: Get total transaction count for this entity
        cursor.execute("""
            SELECT COUNT(DISTINCT transaction_id)
            FROM entity_patterns
            WHERE tenant_id = %s AND entity_name = %s
        """, (tenant_id, entity_name))

        total_entity_tx = cursor.fetchone()[0] or 1

        # Step 2: Get occurrence count for this specific pattern term
        cursor.execute("""
            SELECT COUNT(*)
            FROM entity_patterns
            WHERE tenant_id = %s
            AND entity_name = %s
            AND pattern_data::text ILIKE %s
        """, (tenant_id, entity_name, f'%"{pattern_term}"%'))

        occurrence_count = cursor.fetchone()[0] or 1

        # Step 3: Calculate Term Frequency
        term_frequency = occurrence_count / max(total_entity_tx, 1)

        # Step 4: Calculate Inverse Document Frequency
        # Count how many DISTINCT entities use this term
        cursor.execute("""
            SELECT COUNT(DISTINCT entity_name)
            FROM entity_patterns
            WHERE tenant_id = %s
            AND pattern_data::text ILIKE %s
        """, (tenant_id, f'%"{pattern_term}"%'))

        entities_with_term = cursor.fetchone()[0] or 1

        # Get total number of entities with patterns
        cursor.execute("""
            SELECT COUNT(DISTINCT entity_name)
            FROM entity_patterns
            WHERE tenant_id = %s
        """, (tenant_id,))

        total_entities = cursor.fetchone()[0] or 1

        # IDF = log(total_entities / entities_with_term)
        idf = math.log(total_entities / max(entities_with_term, 1))

        # Step 5: Calculate TF-IDF score
        tf_idf_score = term_frequency * idf

        # Step 6: Calculate weighted confidence (simple formula for now)
        weighted_confidence = min(1.0, term_frequency * 2.0)

        # Step 7: UPSERT into entity_pattern_statistics
        cursor.execute("""
            INSERT INTO entity_pattern_statistics (
                tenant_id, entity_name, pattern_term, pattern_type,
                occurrence_count, total_entity_transactions,
                term_frequency, inverse_document_frequency, tf_idf_score,
                base_confidence_score, weighted_confidence,
                first_seen, last_seen, last_updated
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW())
            ON CONFLICT (tenant_id, entity_name, pattern_term, pattern_type)
            DO UPDATE SET
                occurrence_count = EXCLUDED.occurrence_count,
                total_entity_transactions = EXCLUDED.total_entity_transactions,
                term_frequency = EXCLUDED.term_frequency,
                inverse_document_frequency = EXCLUDED.inverse_document_frequency,
                tf_idf_score = EXCLUDED.tf_idf_score,
                weighted_confidence = EXCLUDED.weighted_confidence,
                last_seen = NOW(),
                last_updated = NOW()
        """, (
            tenant_id, entity_name, pattern_term, pattern_type,
            occurrence_count, total_entity_tx,
            term_frequency, idf, tf_idf_score,
            1.0, weighted_confidence
        ))

        conn.commit()
        conn.close()

        print(f" Updated pattern statistics: {entity_name} / {pattern_term} ({pattern_type}) - TF-IDF: {tf_idf_score:.3f}")

    except Exception as e:
        print(f" ERROR updating pattern statistics for '{pattern_term}': {e}")
        import traceback
        print(traceback.format_exc())

def handle_classification_feedback(transaction_id: str, suggested_entity: str, actual_entity: str,
                                   tenant_id: str, feedback_type: str = 'rejected'):
    """
    Handle user feedback when they reject or accept an AI suggestion.

    This implements reinforcement learning by:
    1. Reducing TF-IDF scores for patterns that led to wrong suggestions (negative feedback)
    2. Boosting TF-IDF scores for patterns that led to correct suggestions (positive feedback)

    Args:
        transaction_id: The transaction that was classified
        suggested_entity: The entity that was suggested by AI
        actual_entity: The entity the user actually chose
        tenant_id: Tenant ID for multi-tenant isolation
        feedback_type: 'rejected' (user chose different entity) or 'accepted' (user accepted suggestion)
    """
    from database import db_manager

    try:
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        if feedback_type == 'rejected':
            # Negative feedback: Reduce TF-IDF scores for the wrongly suggested entity
            # This prevents the same bad suggestion from happening again

            print(f" Negative feedback: '{suggested_entity}' was suggested but user chose '{actual_entity}'")

            # Apply a 10% penalty to all patterns for the wrongly suggested entity
            cursor.execute("""
                UPDATE entity_pattern_statistics
                SET tf_idf_score = tf_idf_score * 0.9,
                    weighted_confidence = weighted_confidence * 0.9,
                    last_updated = NOW()
                WHERE tenant_id = %s
                AND entity_name = %s
            """, (tenant_id, suggested_entity))

            penalty_count = cursor.rowcount
            print(f"   Applied penalty to {penalty_count} patterns for '{suggested_entity}'")

        elif feedback_type == 'accepted':
            # Positive feedback: Boost TF-IDF scores for the correctly suggested entity

            print(f" Positive feedback: '{suggested_entity}' was suggested and accepted")

            # Apply a 5% boost to all patterns for the correctly suggested entity
            cursor.execute("""
                UPDATE entity_pattern_statistics
                SET tf_idf_score = tf_idf_score * 1.05,
                    weighted_confidence = LEAST(weighted_confidence * 1.05, 1.0),
                    last_updated = NOW()
                WHERE tenant_id = %s
                AND entity_name = %s
            """, (tenant_id, suggested_entity))

            boost_count = cursor.rowcount
            print(f"   Applied boost to {boost_count} patterns for '{suggested_entity}'")

        # Log the feedback for analytics
        cursor.execute("""
            INSERT INTO user_interactions (
                tenant_id, transaction_id, interaction_type,
                field_name, old_value, new_value, timestamp
            )
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (tenant_id, transaction_id, 'ai_feedback',
              'classified_entity', suggested_entity, actual_entity))

        conn.commit()
        conn.close()

        print(f" Feedback processed successfully for transaction {transaction_id}")

    except Exception as e:
        print(f" ERROR processing feedback: {e}")
        import traceback
        print(traceback.format_exc())

def calculate_entity_match_score(description: str, entity_name: str, tenant_id: str,
                                  amount: float = None, account: str = None, cursor=None) -> dict:
    """
    Calculate weighted match score for an entity using aggregated pattern statistics.

    This function uses TF-IDF scores, fuzzy matching, and transaction context to determine
    how well a transaction matches patterns for a specific entity.

    Args:
        description: Transaction description to match against
        entity_name: Entity name to check patterns for
        tenant_id: Tenant ID for multi-tenant isolation
        amount: Optional transaction amount for amount pattern matching
        account: Optional account name/type for context-aware scoring
        cursor: Optional database cursor to reuse (for performance when calling in loops)

    Returns:
        dict: {
            'entity': str,
            'score': float (0.0-1.0),
            'matched_patterns': list,
            'confidence': float,
            'reasoning': str,
            'amount_match': bool (if amount provided),
            'account_match': bool (if account provided)
        }
    """
    from database import db_manager
    import math

    # Reuse provided cursor or create new connection
    own_connection = cursor is None
    if own_connection:
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

    # Convert amount to float early to avoid Decimal/float type mismatches throughout
    amount_float = float(amount) if amount is not None else None

    # Get aggregated statistics for this entity
    cursor.execute("""
        SELECT pattern_term, pattern_type, occurrence_count, tf_idf_score, weighted_confidence
        FROM entity_pattern_statistics
        WHERE tenant_id = %s
        AND entity_name = %s
        AND tf_idf_score > 0.1
        ORDER BY tf_idf_score DESC
    """, (tenant_id, entity_name))

    patterns = cursor.fetchall()
    logging.info(f"[TFIDF_MATCH_SCORE] Entity '{entity_name}' has {len(patterns)} patterns in database")

    #  NEW: Get historical amount patterns for this entity if amount provided
    amount_match_score = 0.0
    if amount_float is not None and amount_float > 0:
        cursor.execute("""
            SELECT AVG(amount) as avg_amount, STDDEV(amount) as stddev_amount, COUNT(*) as count
            FROM transactions
            WHERE tenant_id = %s
            AND classified_entity = %s
            AND amount > 0
            GROUP BY classified_entity
        """, (tenant_id, entity_name))

        amount_stats = cursor.fetchone()
        if amount_stats and amount_stats[2] >= 3:  # At least 3 transactions
            avg_amount = float(amount_stats[0]) if amount_stats[0] else 0
            stddev_amount = float(amount_stats[1]) if amount_stats[1] else 0

            if avg_amount > 0:
                # Calculate how close the amount is to the typical amount for this entity
                # Use z-score normalized to 0-1 range (amount_float already converted at top of function)
                if stddev_amount > 0:
                    z_score = abs(amount_float - avg_amount) / stddev_amount
                    # Convert z-score to similarity (closer to average = higher score)
                    # z_score of 0 = perfect match, z_score > 2 = very different
                    amount_match_score = max(0, 1.0 - (z_score / 3.0))
                else:
                    # No variation - exact match check
                    amount_match_score = 1.0 if abs(amount_float - avg_amount) < 0.01 else 0.5

    # Only close connection if we created it ourselves
    if own_connection:
        cursor.close()
        conn.close()

    if not patterns:
        return {
            'entity': entity_name,
            'score': 0.0,
            'matched_patterns': [],
            'confidence': 0.0,
            'reasoning': 'No patterns available',
            'amount_match': amount_match_score > 0.5 if amount else None,
            'account_match': None
        }

    # Calculate weighted score from pattern matching
    total_score = 0.0
    matched_patterns = []

    for pattern_term, pattern_type, occurrence_count, tf_idf_score, weighted_conf in patterns:
        # Use fuzzy matching
        match_score = fuzzy_match_pattern(pattern_term, description, threshold=85)

        if match_score > 0:
            # Weight by TF-IDF importance and occurrence frequency
            weight = tf_idf_score * math.log(occurrence_count + 1) * match_score
            total_score += weight

            matched_patterns.append({
                'term': pattern_term,
                'type': pattern_type,
                'match_score': match_score,
                'tf_idf': tf_idf_score,
                'occurrences': occurrence_count
            })

    # Normalize base score (cap at 1.0)
    base_score = min(total_score / 3.0, 1.0)

    #  NEW: Combine base score with amount pattern matching
    if amount is not None and amount_match_score > 0:
        # Weight: 70% pattern matching, 30% amount matching
        normalized_score = (base_score * 0.7) + (amount_match_score * 0.3)
    else:
        normalized_score = base_score

    # Calculate confidence based on number and quality of matches
    confidence = min(
        0.5 + (len(matched_patterns) * 0.1) + (normalized_score * 0.4),
        1.0
    )

    #  NEW: Boost confidence if amount matches
    if amount_match_score > 0.7:
        confidence = min(confidence * 1.1, 1.0)  # 10% boost for good amount match

    # Generate reasoning
    reasoning_parts = []
    if matched_patterns:
        top_matches = sorted(matched_patterns, key=lambda x: x['tf_idf'], reverse=True)[:3]
        match_descriptions = [f"{m['term']} (TF-IDF: {m['tf_idf']:.2f}, {m['occurrences']}x)" for m in top_matches]
        reasoning_parts.append(f"Matched {len(matched_patterns)} patterns: {', '.join(match_descriptions)}")

    #  NEW: Add amount pattern reasoning
    if amount is not None and amount_match_score > 0:
        if amount_match_score > 0.8:
            reasoning_parts.append(f"Amount ${amount:.2f} matches typical pattern (score: {amount_match_score:.2f})")
        elif amount_match_score > 0.5:
            reasoning_parts.append(f"Amount ${amount:.2f} somewhat matches pattern (score: {amount_match_score:.2f})")
        else:
            reasoning_parts.append(f"Amount ${amount:.2f} differs from typical pattern (score: {amount_match_score:.2f})")

    reasoning = "; ".join(reasoning_parts) if reasoning_parts else "No pattern matches found"

    return {
        'entity': entity_name,
        'score': normalized_score,
        'matched_patterns': matched_patterns,
        'confidence': confidence,
        'reasoning': reasoning,
        'amount_match': amount_match_score > 0.5 if amount else None,
        'account_match': None  # Placeholder for future account matching
    }

def get_candidate_entities_optimized(description: str, tenant_id: str, max_candidates: int = 10) -> list:
    """
     ISSUE #5: PERFORMANCE OPTIMIZATION WITH PRE-FILTERING

    Fast pre-filtering of candidate entities using database indexes before running expensive scoring.

    This function:
    1. Extracts key terms from the transaction description
    2. Queries entity_pattern_statistics for entities with matching patterns (uses indexes)
    3. Returns top N candidate entities ranked by TF-IDF score
    4. Dramatically reduces entities to score from 50+ to ~10

    Performance improvement:
    - Before: Score all 50+ entities = slow
    - After: Pre-filter to ~10 entities, then score = 5x faster

    Args:
        description: Transaction description to analyze
        tenant_id: Tenant ID for multi-tenant isolation
        max_candidates: Maximum number of candidate entities to return (default: 10)

    Returns:
        list: Entity names sorted by relevance (most relevant first)
    """
    from database import db_manager
    import re

    try:
        # Step 1: Extract meaningful terms from description
        # Remove common words and split into terms
        description_upper = description.upper()

        # Remove common financial noise words
        noise_words = {'PAYMENT', 'TRANSFER', 'DEPOSIT', 'WITHDRAWAL', 'FEE', 'CHARGE',
                       'SERVICE', 'TRANSACTION', 'FROM', 'TO', 'AT', 'FOR', 'WITH',
                       'THE', 'AND', 'OR', 'IN', 'ON', 'BY'}

        # Extract words (3+ characters)
        terms = re.findall(r'\b[A-Z0-9]{3,}\b', description_upper)
        meaningful_terms = [t for t in terms if t not in noise_words][:5]  # Top 5 terms

        if not meaningful_terms:
            # Fallback: just get top entities by overall TF-IDF
            conn = db_manager._get_postgresql_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT entity_name, MAX(tf_idf_score) as max_score
                FROM entity_pattern_statistics
                WHERE tenant_id = %s
                GROUP BY entity_name
                ORDER BY max_score DESC
                LIMIT %s
            """, (tenant_id, max_candidates))

            results = cursor.fetchall()
            conn.close()

            return [row[0] for row in results]

        # Step 2: Query database for entities with matching patterns
        # Use ILIKE with indexes for fast filtering
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()

        # Build query to find entities whose patterns match any of the terms
        # Aggregate scores for each entity
        placeholders = ', '.join(['%s'] * len(meaningful_terms))

        cursor.execute(f"""
            SELECT
                entity_name,
                SUM(tf_idf_score) as total_score,
                COUNT(*) as match_count,
                MAX(tf_idf_score) as best_score
            FROM entity_pattern_statistics
            WHERE tenant_id = %s
            AND (
                {' OR '.join([f"pattern_term ILIKE %s" for _ in meaningful_terms])}
            )
            GROUP BY entity_name
            ORDER BY total_score DESC, match_count DESC
            LIMIT %s
        """, (tenant_id, *[f'%{term}%' for term in meaningful_terms], max_candidates))

        results = cursor.fetchall()

        # If we got results, return them
        if results:
            candidate_entities = [row[0] for row in results]
            conn.close()
            logger.info(f"Pre-filtered to {len(candidate_entities)} candidates from terms: {meaningful_terms}")
            return candidate_entities

        # Step 3: Fallback - no exact matches, get top entities by TF-IDF
        cursor.execute("""
            SELECT entity_name, MAX(tf_idf_score) as max_score
            FROM entity_pattern_statistics
            WHERE tenant_id = %s
            GROUP BY entity_name
            ORDER BY max_score DESC
            LIMIT %s
        """, (tenant_id, max_candidates))

        fallback_results = cursor.fetchall()
        conn.close()

        logger.info(f"Pre-filtering fallback: returning top {len(fallback_results)} entities by TF-IDF")
        return [row[0] for row in fallback_results]

    except Exception as e:
        logger.error(f"ERROR in get_candidate_entities_optimized: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def normalize_company_name(company_name: str) -> str:
    """
    ENHANCEMENT #2: Pattern Normalization
    Normalize company names to merge similar variants and reduce duplicates.

    Examples:
        "ACME CORP" -> "ACME"
        "ACME INC" -> "ACME"
        "ACME CORPORATION" -> "ACME"
        "ACME LLC" -> "ACME"
        "DELTA MINING, LLC" -> "DELTA MINING"
    """
    if not company_name:
        return ""

    # Convert to uppercase for consistency
    normalized = company_name.upper().strip()

    # Remove common business suffixes
    suffixes = [
        ' CORPORATION',
        ' INCORPORATED',
        ' LIMITED',
        ' LLC',
        ' LLP',
        ' L.L.C.',
        ' L.L.P.',
        ' CORP',
        ' INC',
        ' LTD',
        ' CO',
        ' COMPANY',
        ' GROUP',
        ' HOLDINGS',
        ' ENTERPRISES',
    ]

    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()

    # Remove trailing punctuation (commas, periods)
    normalized = normalized.rstrip('.,;')

    # Replace multiple spaces with single space
    import re
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized.strip()

def get_entity_pattern_suggestions(entity_name: str) -> Dict:
    """
    Get LLM-extracted entity patterns for enhancing AI suggestions

    ENHANCEMENT #1: Pattern Confidence Decay
    - Patterns decay over 180 days (6 months) from 100% to 50% confidence
    - Newer patterns get higher weight in aggregation
    - Formula: confidence_multiplier = max(0.5, 1.0 - (age_days / 180))

    ENHANCEMENT #2: Pattern Normalization
    - Company names are normalized to merge similar variants
    - "ACME CORP", "ACME INC", "ACME LLC" -> all become "ACME"
    - Reduces pattern fragmentation and improves matching accuracy
    """
    try:
        if not entity_name:
            return {}

        tenant_id = get_current_tenant_id()
        from database import db_manager
        from datetime import datetime, timezone
        conn = db_manager._get_postgresql_connection()
        cursor = conn.cursor()
        is_postgresql = hasattr(cursor, 'mogrify')
        placeholder = '%s' if is_postgresql else '?'

        # Fetch the most recent entity patterns for this entity (tenant-isolated)
        # NOW INCLUDES: created_at timestamp for confidence decay calculation
        cursor.execute(f"""
            SELECT pattern_data, created_at, confidence_score
            FROM entity_patterns
            WHERE tenant_id = {placeholder}
            AND entity_name = {placeholder}
            ORDER BY created_at DESC
            LIMIT 10
        """, (tenant_id, entity_name))

        pattern_rows = cursor.fetchall()
        conn.close()

        if not pattern_rows:
            return {}

        # Aggregate patterns from multiple transactions WITH CONFIDENCE DECAY
        # Pattern weights: newer patterns get higher confidence multipliers
        pattern_weights = {}  # Track how many times each pattern appears with weighted confidence

        for row in pattern_rows:
            pattern_data = row.get('pattern_data', '{}') if isinstance(row, dict) else row[0]
            created_at = row.get('created_at') if isinstance(row, dict) else row[1]
            base_confidence = row.get('confidence_score', 1.0) if isinstance(row, dict) else (row[2] if len(row) > 2 else 1.0)

            if isinstance(pattern_data, str):
                pattern_data = json.loads(pattern_data)

            # Calculate pattern age in days
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

                # Make created_at timezone-aware if it's naive
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)

                now = datetime.now(timezone.utc)
                age_days = (now - created_at).days

                # CONFIDENCE DECAY FORMULA: Linear decay over 180 days from 1.0 to 0.5
                confidence_multiplier = max(0.5, 1.0 - (age_days / 180.0))
            else:
                # No timestamp available - assume recent pattern
                confidence_multiplier = 1.0

            # Final weighted confidence = base_confidence * decay_multiplier
            weighted_confidence = base_confidence * confidence_multiplier

            # Aggregate patterns with weighted confidence tracking
            # ENHANCEMENT #2: Apply normalization to company names to merge similar variants
            for company in pattern_data.get('company_names', []):
                # Normalize company name to merge "ACME CORP", "ACME INC", etc.
                normalized_company = normalize_company_name(company)
                if not normalized_company:
                    continue

                if normalized_company not in pattern_weights:
                    pattern_weights[normalized_company] = {
                        'type': 'company_names',
                        'weight': 0,
                        'count': 0,
                        'original_forms': set()  # Track original variations
                    }
                pattern_weights[normalized_company]['weight'] += weighted_confidence
                pattern_weights[normalized_company]['count'] += 1
                pattern_weights[normalized_company]['original_forms'].add(company)

            for keyword in pattern_data.get('transaction_keywords', []):
                if keyword not in pattern_weights:
                    pattern_weights[keyword] = {'type': 'transaction_keywords', 'weight': 0, 'count': 0}
                pattern_weights[keyword]['weight'] += weighted_confidence
                pattern_weights[keyword]['count'] += 1

            for bank_id in pattern_data.get('bank_identifiers', []):
                if bank_id not in pattern_weights:
                    pattern_weights[bank_id] = {'type': 'bank_identifiers', 'weight': 0, 'count': 0}
                pattern_weights[bank_id]['weight'] += weighted_confidence
                pattern_weights[bank_id]['count'] += 1

            for orig_pattern in pattern_data.get('originator_patterns', []):
                if orig_pattern not in pattern_weights:
                    pattern_weights[orig_pattern] = {'type': 'originator_patterns', 'weight': 0, 'count': 0}
                pattern_weights[orig_pattern]['weight'] += weighted_confidence
                pattern_weights[orig_pattern]['count'] += 1

            if pattern_data.get('payment_method_type'):
                pm_type = pattern_data['payment_method_type']
                if pm_type not in pattern_weights:
                    pattern_weights[pm_type] = {'type': 'payment_method_types', 'weight': 0, 'count': 0}
                pattern_weights[pm_type]['weight'] += weighted_confidence
                pattern_weights[pm_type]['count'] += 1

        # Build final aggregated patterns, sorted by weighted confidence
        aggregated_patterns = {
            'company_names': [],
            'transaction_keywords': [],
            'bank_identifiers': [],
            'originator_patterns': [],
            'payment_method_types': []
        }

        for pattern_value, stats in sorted(pattern_weights.items(), key=lambda x: x[1]['weight'], reverse=True):
            pattern_type = stats['type']
            aggregated_patterns[pattern_type].append(pattern_value)

        # Return only non-empty pattern types
        return {k: v for k, v in aggregated_patterns.items() if v}

    except Exception as e:
        print(f"ERROR: Error getting entity patterns: {e}")
        import traceback
        traceback.print_exc()
        return {}

def enhance_ai_prompt_with_learning(field_type: str, base_prompt: str, context: dict) -> str:
    """
    Enhance AI prompts with learned patterns from both learned_patterns and entity_patterns tables

    Enhancements applied:
    #1: Pattern Confidence Decay (in get_entity_pattern_suggestions)
    #2: Pattern Normalization (in get_entity_pattern_suggestions)
    #3: Negative Pattern Learning (filters out rejected suggestions)
    #4: Cross-Entity Disambiguation (helps AI choose between similar entities)
    """
    try:
        enhanced_context = ""

        # 1. Get simple learned suggestions (from learned_patterns table)
        learned_suggestions = get_learned_suggestions(field_type, context)

        if learned_suggestions:
            enhanced_context += "\n\nBased on previous user preferences for similar transactions:"
            for suggestion in learned_suggestions:
                confidence_pct = int(suggestion['confidence'] * 100)
                enhanced_context += f"\n- '{suggestion['value']}' (user chose this {confidence_pct}% of the time)"

        # 2. Get LLM-extracted entity patterns (from entity_patterns table) - ONLY for entity classification
        if field_type == 'classified_entity' and context.get('description'):
            current_description = context.get('description', '').upper()

            #  ISSUE #5: OPTIMIZED PRE-FILTERING
            # Try to extract potential entity names from description and get their patterns
            # This helps AI understand what patterns are associated with different entities
            tenant_id = get_current_tenant_id()

            # Step 1: Use optimized pre-filtering to narrow down candidates from 50+ to ~10
            candidate_entities = get_candidate_entities_optimized(
                description=context.get('description', ''),
                tenant_id=tenant_id,
                max_candidates=10  # Only score top 10 candidates instead of all entities
            )

            # Step 2: Calculate detailed match scores ONLY for pre-filtered candidates
            matching_entities_info = []
            for entity in candidate_entities:
                match_result = calculate_entity_match_score(
                    description=context.get('description', ''),
                    entity_name=entity,
                    tenant_id=tenant_id,
                    amount=context.get('amount'),  #  ISSUE #3: Transaction context
                    account=context.get('account')  #  ISSUE #3: Account context
                )

                if match_result['score'] > 0.3:  # Minimum threshold
                    matching_entities_info.append({
                        'entity': match_result['entity'],
                        'score': match_result['score'],
                        'confidence': match_result['confidence'],
                        'reasoning': match_result['reasoning'],
                        'matched_patterns': match_result['matched_patterns'],
                        'pattern_count': len(match_result['matched_patterns'])
                    })

            # Add pattern matching context to prompt with TF-IDF scores
            if matching_entities_info:
                # Sort by confidence score (highest first)
                matching_entities_info.sort(key=lambda x: x['score'], reverse=True)

                enhanced_context += "\n\nStatistical pattern analysis shows:"
                for rank, match_info in enumerate(matching_entities_info[:3], 1):  # Top 3 matches
                    entity = match_info['entity']
                    confidence_pct = int(match_info['confidence'] * 100)
                    score = match_info['score']
                    reasoning = match_info['reasoning']

                    enhanced_context += f"\n{rank}. '{entity}' (confidence: {confidence_pct}%, match score: {score:.2f})"
                    enhanced_context += f"\n   {reasoning}"

                # Highlight top match if it's significantly better
                if matching_entities_info:
                    top = matching_entities_info[0]
                    pattern_count = len(top['matched_patterns'])

                    if len(matching_entities_info) == 1 or (len(matching_entities_info) >= 2 and top['score'] > matching_entities_info[1]['score'] * 1.5):
                        # Clear winner
                        enhanced_context += f"\n\nStrongly recommend '{top['entity']}' based on {pattern_count} pattern matches with {int(top['confidence']*100)}% confidence."
                    else:
                        # Multiple similar matches
                        enhanced_context += "\n\nMultiple entities have similar match scores. Consider the specific patterns matched when making your choice."

        if enhanced_context:
            return base_prompt + enhanced_context

        return base_prompt
    except Exception as e:
        print(f"ERROR: Error enhancing prompt: {e}")
        import traceback
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        return base_prompt

@app.route('/api/test-sync/<filename>')
def test_sync(filename):
    """Test endpoint to manually trigger sync for debugging"""
    print(f" TEST: Manual sync test for {filename}")

    # Check if original file exists where upload saves it (parent directory)
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    actual_file_path = os.path.join(parent_dir, filename)  # This is where upload saves files
    uploads_path = os.path.join(parent_dir, 'web_ui', 'uploads', filename)  # This was wrong assumption

    print(f" TEST: Checking actual upload path: {actual_file_path}")
    print(f" TEST: File exists at actual path: {os.path.exists(actual_file_path)}")
    print(f" TEST: Also checking uploads path: {uploads_path}")
    print(f" TEST: File exists at uploads path: {os.path.exists(uploads_path)}")

    # List files in parent directory
    try:
        files_in_parent = [f for f in os.listdir(parent_dir) if f.endswith('.csv')]
        print(f" TEST: CSV files in parent dir: {files_in_parent}")
    except Exception as e:
        print(f" TEST: Error listing parent dir: {e}")
        files_in_parent = []

    if os.path.exists(actual_file_path):
        # Try sync
        result = sync_csv_to_database(filename)
        return jsonify({
            'test_result': 'success' if result else 'failed',
            'file_found': True,
            'actual_path': actual_file_path,
            'sync_result': result,
            'classified_dir_check': os.path.exists(os.path.join(parent_dir, 'classified_transactions')),
            'files_in_classified': os.listdir(os.path.join(parent_dir, 'classified_transactions')) if os.path.exists(os.path.join(parent_dir, 'classified_transactions')) else [],
            'csv_files_in_parent': files_in_parent
        })
    else:
        return jsonify({
            'test_result': 'file_not_found_anywhere',
            'file_found': False,
            'checked_actual_path': actual_file_path,
            'checked_uploads_path': uploads_path,
            'csv_files_in_parent': files_in_parent
        })

@app.route('/api/debug-sync/<filename>')
def debug_sync(filename):
    """Debug endpoint to show detailed sync logs"""
    import io
    from contextlib import redirect_stdout, redirect_stderr

    # Capture all prints during sync
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            result = sync_csv_to_database(filename)

        return jsonify({
            'sync_result': result,
            'stdout_logs': stdout_capture.getvalue(),
            'stderr_logs': stderr_capture.getvalue(),
            'success': result is not False
        })
    except Exception as e:
        return jsonify({
            'sync_result': False,
            'stdout_logs': stdout_capture.getvalue(),
            'stderr_logs': stderr_capture.getvalue(),
            'exception': str(e),
            'success': False
        })

# ===============================================
# REVENUE MATCHING API ENDPOINTS
# ===============================================

@app.route('/api/revenue/run-matching', methods=['POST'])
def api_run_revenue_matching():
    """
     OTIMIZADO: Executa matching com prevenção de cliques duplos e tracking de progresso
    Body: {
        "invoice_ids": ["id1", "id2", ...] (opcional - se não fornecido, processa todos),
        "auto_apply": true/false (se deve aplicar matches automáticos)
    }
    """
    global active_matcher

    try:
        # 1. PREVENÇÃO DE CLIQUES DUPLOS
        with matcher_lock:
            if active_matcher is not None:
                return jsonify({
                    'success': False,
                    'error': 'Matching process already running',
                    'message': ' Processo já em execução. Aguarde a conclusão.',
                    'progress': active_matcher.get_progress_info() if hasattr(active_matcher, 'get_progress_info') else None
                }), 409  # Conflict

        # 2. INICIALIZAR NOVO PROCESSO
        from revenue_matcher import RevenueInvoiceMatcher

        data = request.get_json() or {}
        invoice_ids = data.get('invoice_ids')
        auto_apply = data.get('auto_apply', False)

        logger.info(f" Starting OPTIMIZED revenue matching - Invoice IDs: {invoice_ids}, Auto-apply: {auto_apply}")

        # 3. CRIAR MATCHER E ARMAZENAR GLOBALMENTE PARA TRACKING
        with matcher_lock:
            active_matcher = RevenueInvoiceMatcher()

        def run_matching_async():
            global active_matcher
            try:
                # Find matches with optimized processing
                matches = active_matcher.find_matches_for_invoices(invoice_ids)

                # Apply semantic matching (now optimized with batch processing)
                if matches:
                    invoices = active_matcher._get_unmatched_invoices(invoice_ids)
                    transactions = active_matcher._get_candidate_transactions()
                    matches = active_matcher.apply_semantic_matching(matches, invoices, transactions)

                # Save results
                stats = active_matcher.save_match_results(matches, auto_apply)

                logger.info(f" OPTIMIZATION SUCCESS: Processed {len(matches)} matches")

                return {
                    'success': True,
                    'total_matches': len(matches),
                    'high_confidence': len([m for m in matches if m.confidence_level == 'HIGH']),
                    'medium_confidence': len([m for m in matches if m.confidence_level == 'MEDIUM']),
                    'auto_applied': stats['auto_applied'],
                    'pending_review': stats['pending_review'],
                    'optimizations_used': [' Smart Filtering', ' Batch Processing', ' Parallelization', ' Data Sanitization'],
                    'matches': [
                        {
                            'invoice_id': m.invoice_id,
                            'transaction_id': m.transaction_id,
                            'score': m.score,
                            'match_type': m.match_type,
                            'confidence_level': m.confidence_level,
                            'explanation': m.explanation,
                            'auto_match': m.auto_match
                        }
                        for m in matches
                    ]
                }
            except Exception as e:
                logger.error(f"Error in async matching: {e}")
                raise
            finally:
                # 4. LIMPAR MATCHER ATIVO
                with matcher_lock:
                    active_matcher = None

        # Execute in background thread for real-time progress
        import threading
        result_container = {}
        error_container = {}

        def thread_worker():
            try:
                result_container['result'] = run_matching_async()
            except Exception as e:
                error_container['error'] = e

        thread = threading.Thread(target=thread_worker)
        thread.start()
        thread.join()  # Wait for completion

        if 'error' in error_container:
            raise error_container['error']

        return jsonify(result_container['result'])

    except Exception as e:
        # Cleanup on error
        with matcher_lock:
            active_matcher = None

        logger.error(f"Error in revenue matching: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/revenue/run-ultra-fast-matching', methods=['POST'])
def api_run_ultra_fast_revenue_matching():
    """
    ULTRA FAST MATCHING: Enterprise-grade performance optimized matcher
    Target: <100ms per invoice (73.3ms achieved)
    Body: {
        "auto_apply": true/false (se deve aplicar matches automáticos)
    }
    """
    global active_matcher

    try:
        # 1. PREVENÇÃO DE CLIQUES DUPLOS
        with matcher_lock:
            if active_matcher is not None:
                return jsonify({
                    'success': False,
                    'error': 'Matching process already running',
                    'message': 'Processo já em execução. Aguarde a conclusão.',
                    'progress': active_matcher.get_progress_info() if hasattr(active_matcher, 'get_progress_info') else None
                }), 409  # Conflict

        # 2. INICIALIZAR NOVO PROCESSO ULTRA-FAST
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from ultra_fast_matcher_fixed import UltraFastMatcher

        data = request.get_json() or {}
        auto_apply = data.get('auto_apply', False)

        logger.info(f"ULTRA FAST MATCHING: Starting enterprise-grade matcher (target: <100ms per invoice)")

        # 3. CRIAR ULTRA-FAST MATCHER
        with matcher_lock:
            active_matcher = UltraFastMatcher()

        def run_ultra_matching_async():
            global active_matcher
            try:
                # Run ultra-fast matching with auto_apply parameter
                result = active_matcher.run_ultra_fast_matching(auto_apply=auto_apply)

                auto_applied = result.get('auto_applied', 0)
                pending_review = result.get('pending_review', 0)

                logger.info(f"ULTRA FAST SUCCESS: {result['total_matches']} matches in {result['processing_time']:.2f}s")
                if auto_apply:
                    logger.info(f"AUTO-APPLY RESULTS: {auto_applied} applied automatically, {pending_review} pending review")
                logger.info(f"PERFORMANCE: {result['ms_per_invoice']:.1f}ms per invoice (Target: <1000ms)")

                message = f'Processed invoices in {result["processing_time"]:.1f}s - Performance: {result["ms_per_invoice"]:.1f}ms per invoice'
                if auto_apply:
                    message += f' | Auto-applied: {auto_applied}, Pending: {pending_review}'

                return {
                    'success': True,
                    'total_matches': result['total_matches'],
                    'auto_applied': auto_applied,
                    'pending_review': pending_review,
                    'processing_time': result['processing_time'],
                    'invoices_per_second': result['invoices_per_second'],
                    'ms_per_invoice': result['ms_per_invoice'],
                    'performance_status': 'PASSED' if result['ms_per_invoice'] < 1000 else 'FAILED',
                    'enterprise_ready': result['ms_per_invoice'] < 1000,
                    'optimization_level': 'ULTRA_FAST',
                    'auto_apply_enabled': auto_apply,
                    'message': message
                }
            except Exception as e:
                logger.error(f"Error in ultra-fast matching: {e}")
                raise
            finally:
                # 4. LIMPAR MATCHER ATIVO
                with matcher_lock:
                    active_matcher = None

        # Execute in background thread
        import threading
        result_container = {}
        error_container = {}

        def thread_worker():
            try:
                result_container['result'] = run_ultra_matching_async()
            except Exception as e:
                error_container['error'] = e

        thread = threading.Thread(target=thread_worker)
        thread.start()
        thread.join()  # Wait for completion

        if 'error' in error_container:
            raise error_container['error']

        return jsonify(result_container['result'])

    except Exception as e:
        # Cleanup on error
        with matcher_lock:
            active_matcher = None

        error_details = {
            'error_type': type(e).__name__,
            'error_message': str(e),
            'traceback': traceback.format_exc()
        }

        logger.error(f"Error in ultra-fast revenue matching:")
        logger.error(f"  Type: {error_details['error_type']}")
        logger.error(f"  Message: {error_details['error_message']}")
        logger.error(f"  Traceback:\n{error_details['traceback']}")

        return jsonify({
            'success': False,
            'error': error_details['error_message'],
            'error_type': error_details['error_type'],
            'traceback': error_details['traceback'],
            'debug_info': {
                'endpoint': '/api/revenue/run-ultra-fast-matching',
                'pythonpath': os.environ.get('PYTHONPATH'),
                'cwd': os.getcwd(),
                'ultra_fast_matcher_exists': os.path.exists('ultra_fast_matcher_fixed.py'),
                'ultra_fast_matcher_parent_exists': os.path.exists('../ultra_fast_matcher_fixed.py')
            }
        }), 500

@app.route('/api/revenue/matching-progress', methods=['GET'])
def api_get_matching_progress():
    """
     NOVO: Retorna progresso em tempo real do matching process
    """
    global active_matcher

    try:
        with matcher_lock:
            if active_matcher is None:
                return jsonify({
                    'running': False,
                    'message': 'Nenhum processo de matching ativo',
                    'progress': 0,
                    'eta': 'N/A',
                    'matches_processed': 0,
                    'total': 0
                })

            progress_info = active_matcher.get_progress_info()
            return jsonify({
                'running': True,
                'message': f"Processando matches {progress_info['matches_processed']}/{progress_info['total']}",
                'progress': progress_info['progress'],
                'eta': progress_info['eta'],
                'matches_processed': progress_info['matches_processed'],
                'total': progress_info['total'],
                'optimizations': [' Smart Filtering', ' Batch Processing', ' Parallelization']
            })

    except Exception as e:
        logger.error(f"Error getting matching progress: {e}")
        return jsonify({
            'running': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/pending-matches')
def api_get_pending_matches():
    """Retorna matches pendentes de revisão"""
    try:
        tenant_id = get_current_tenant_id()
        from database import db_manager
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        offset = (page - 1) * per_page

        # Query including explanation and confidence_level fields + CUSTOMER INFO
        query = """
            SELECT
                pm.id,
                pm.invoice_id,
                pm.transaction_id,
                pm.score,
                pm.match_type,
                pm.confidence_level,
                pm.explanation,
                pm.created_at,
                i.invoice_number,
                i.vendor_name,
                i.customer_name,
                i.customer_address,
                i.customer_tax_id,
                i.total_amount as invoice_amount,
                i.currency as invoice_currency,
                i.date as invoice_date,
                i.due_date,
                t.description,
                t.amount as transaction_amount,
                t.date as transaction_date,
                t.classified_entity
            FROM pending_invoice_matches pm
            JOIN invoices i ON pm.invoice_id = i.id
            JOIN transactions t ON pm.transaction_id = t.transaction_id
            WHERE pm.status = 'pending'
            AND i.tenant_id = %s
            AND t.tenant_id = %s
            ORDER BY pm.score DESC, pm.created_at DESC
            LIMIT %s OFFSET %s
        """

        matches = db_manager.execute_query(query, (tenant_id, tenant_id, per_page, offset), fetch_all=True)

        # Get total count
        count_query = """
            SELECT COUNT(*) as total
            FROM pending_invoice_matches pm
            JOIN invoices i ON pm.invoice_id = i.id
            JOIN transactions t ON pm.transaction_id = t.transaction_id
            WHERE pm.status = 'pending'
            AND i.tenant_id = %s
            AND t.tenant_id = %s
        """
        total_result = db_manager.execute_query(count_query, (tenant_id, tenant_id), fetch_one=True)
        total = total_result['total'] if total_result else 0

        # Format matches for frontend
        formatted_matches = []
        for match in matches:
            formatted_matches.append({
                'id': match['id'],
                'invoice_id': match['invoice_id'],
                'transaction_id': match['transaction_id'],
                'score': float(match['score']) if match['score'] else 0.0,
                'match_type': match['match_type'] or 'AUTO',
                'confidence_level': match['confidence_level'] or 'MEDIUM',
                'explanation': match['explanation'] or 'Match found based on automated criteria',
                'created_at': match['created_at'],
                'invoice': {
                    'number': match['invoice_number'],
                    'vendor_name': match['vendor_name'],
                    'customer_name': match['customer_name'],
                    'customer_address': match['customer_address'],
                    'customer_tax_id': match['customer_tax_id'],
                    'amount': float(match['invoice_amount']) if match['invoice_amount'] else 0.0,
                    'currency': match['invoice_currency'],
                    'date': match['invoice_date'],
                    'due_date': match['due_date']
                },
                'transaction': {
                    'description': match['description'],
                    'amount': float(match['transaction_amount']) if match['transaction_amount'] else 0.0,
                    'date': match['transaction_date'],
                    'classified_entity': match['classified_entity']
                }
            })

        return jsonify({
            'success': True,
            'matches': formatted_matches,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        logger.error(f"Error getting pending matches: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/confirm-match', methods=['POST'])
def api_confirm_match():
    """
    Confirma um match pendente
    Body: {
        "invoice_id": str,
        "transaction_id": str,
        "customer_name": str (opcional),
        "invoice_number": str (opcional),
        "user_id": "string" (opcional)
    }
    OR: {
        "match_id": str,
        "user_id": "string" (opcional)
    }
    """
    try:
        from database import db_manager
        data = request.get_json()

        # Support both formats: (invoice_id, transaction_id) OR match_id
        invoice_id = data.get('invoice_id')
        transaction_id = data.get('transaction_id')
        match_id = data.get('match_id')
        customer_name = data.get('customer_name', '')
        invoice_number = data.get('invoice_number', '')
        user_id = data.get('user_id', 'Unknown')

        # If match_id is provided, look up invoice_id and transaction_id
        if match_id and (not invoice_id or not transaction_id):
            match_query = """
                SELECT invoice_id, transaction_id
                FROM pending_invoice_matches
                WHERE id = %s AND status = 'pending'
            """
            match_data = db_manager.execute_query(match_query, (match_id,), fetch_one=True)

            if not match_data:
                return jsonify({'success': False, 'error': 'Match not found or already processed'}), 404

            invoice_id = match_data['invoice_id']
            transaction_id = match_data['transaction_id']

        if not invoice_id or not transaction_id:
            return jsonify({'success': False, 'error': 'invoice_id and transaction_id are required (provide either both directly or match_id)'}), 400

        # Build the justification field
        justification = f"Revenue - {customer_name} - Invoice {invoice_number}"

        # Get database connection using context manager
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            placeholder = '%s' if db_manager.db_type == 'postgresql' else '?'

            # Update the transaction with accounting category and justification
            update_transaction_query = f"""
                UPDATE transactions
                SET accounting_category = 'REVENUE',
                    justification = {placeholder}
                WHERE transaction_id = {placeholder}
            """
            cursor.execute(update_transaction_query, (justification, transaction_id))

            #  BIDIRECTIONAL LINKING: Update BOTH tables

            # 1. Update the invoice to link it to the transaction
            update_invoice_query = f"""
                UPDATE invoices
                SET linked_transaction_id = {placeholder},
                    status = 'paid'
                WHERE id = {placeholder}
            """
            cursor.execute(update_invoice_query, (transaction_id, invoice_id))

            # 2. Update the transaction to link it to the invoice (NEW!)
            update_transaction_link_query = f"""
                UPDATE transactions
                SET invoice_id = {placeholder}
                WHERE transaction_id = {placeholder}
            """
            cursor.execute(update_transaction_link_query, (invoice_id, transaction_id))

            # Commit the changes
            conn.commit()
            cursor.close()

        # If match was confirmed via match_id, mark it as confirmed
        if match_id:
            try:
                confirm_match_query = """
                    UPDATE pending_invoice_matches
                    SET status = 'confirmed',
                        reviewed_by = %s,
                        reviewed_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                db_manager.execute_query(confirm_match_query, (user_id, match_id))
                print(f"Match {match_id} marked as confirmed by {user_id}")
            except Exception as e:
                print(f"WARNING: Could not update match status: {e}")

        #  AUTOMATIC AI ENRICHMENT: Enrich transaction with invoice context
        try:
            # Get invoice data for enrichment
            invoice_data = db_manager.execute_query("""
                SELECT vendor_name, customer_name, invoice_number, total_amount, category, business_unit
                FROM invoices
                WHERE id = %s
            """, (invoice_id,), fetch_one=True)

            if invoice_data:
                print(f"AI: Starting automatic transaction enrichment for {transaction_id}")
                enrichment_success = enrich_transaction_with_invoice_context(transaction_id, invoice_data)
                if enrichment_success:
                    print(f"AI: Successfully enriched transaction {transaction_id} with invoice context")
                else:
                    print(f"AI: Failed to enrich transaction {transaction_id}")
            else:
                print(f"WARNING: Could not retrieve invoice data for enrichment: {invoice_id}")
        except Exception as e:
            print(f"WARNING: Automatic enrichment failed (non-critical): {e}")
            # Don't fail the match confirmation due to enrichment errors

        return jsonify({
            'success': True,
            'message': 'Match confirmed successfully with AI enrichment'
        })

    except Exception as e:
        logger.error(f"Error confirming match: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/reject-match', methods=['POST'])
def api_reject_match():
    """
    Rejeita um match pendente
    Body: {
        "match_id": int,
        "user_id": "string" (opcional),
        "reason": "string" (opcional)
    }
    """
    try:
        from database import db_manager
        data = request.get_json()
        match_id = data.get('match_id')
        user_id = data.get('user_id', 'Unknown')
        reason = data.get('reason', '')

        if not match_id:
            return jsonify({'success': False, 'error': 'match_id is required'}), 400

        # Get match details for logging
        query = """
            SELECT invoice_id, transaction_id, score, match_type
            FROM pending_invoice_matches
            WHERE id = %s AND status = 'pending'
        """
        match = db_manager.execute_query(query, (match_id,), fetch_one=True)

        if not match:
            return jsonify({'success': False, 'error': 'Match not found or already processed'}), 404

        # Mark match as rejected
        reject_query = """
            UPDATE pending_invoice_matches
            SET status = 'rejected',
                reviewed_by = %s,
                reviewed_at = CURRENT_TIMESTAMP,
                explanation = CONCAT(explanation, ' | REJECTED: ', %s)
            WHERE id = %s
        """
        db_manager.execute_query(reject_query, (user_id, reason, match_id))

        # Log the action
        log_query = """
            INSERT INTO invoice_match_log
            (invoice_id, transaction_id, action, score, match_type, user_id, created_at)
            VALUES (%s, %s, 'MANUAL_REJECTED', %s, %s, %s, CURRENT_TIMESTAMP)
        """
        db_manager.execute_query(log_query, (
            match['invoice_id'],
            match['transaction_id'],
            match['score'],
            f"{match['match_type']}_REJECTED",
            user_id
        ))

        return jsonify({
            'success': True,
            'message': 'Match rejected successfully'
        })

    except Exception as e:
        logger.error(f"Error rejecting match: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/manual-match', methods=['POST'])
def api_manual_match():
    """
    Cria um match manual entre invoice e transação
    Body: {
        "invoice_id": "string",
        "transaction_id": "string",
        "user_id": "string" (opcional),
        "reason": "string" (opcional)
    }
    """
    try:
        from database import db_manager  # Import necessário
        data = request.get_json()
        invoice_id = data.get('invoice_id')
        transaction_id = data.get('transaction_id')
        user_id = data.get('user_id', 'Unknown')
        reason = data.get('reason', 'Manual match by user')

        if not invoice_id or not transaction_id:
            return jsonify({'success': False, 'error': 'invoice_id and transaction_id are required'}), 400

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        # Verify invoice and transaction exist
        invoice_query = "SELECT id FROM invoices WHERE tenant_id = %s AND id = %s"
        invoice = db_manager.execute_query(invoice_query, (tenant_id, invoice_id), fetch_one=True)

        transaction_query = "SELECT transaction_id FROM transactions WHERE tenant_id = %s AND transaction_id = %s"
        transaction = db_manager.execute_query(transaction_query, (tenant_id, transaction_id), fetch_one=True)

        if not invoice:
            return jsonify({'success': False, 'error': 'Invoice not found'}), 404
        if not transaction:
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404

        #  BIDIRECTIONAL MANUAL MATCH: Update BOTH tables

        # 1. Update the invoice to link it to the transaction
        update_invoice_query = """
            UPDATE invoices
            SET linked_transaction_id = %s,
                status = 'paid'
            WHERE tenant_id = %s AND id = %s
        """
        db_manager.execute_query(update_invoice_query, (transaction_id, tenant_id, invoice_id))

        # 2. Update the transaction to link it to the invoice (NEW!)
        update_transaction_query = """
            UPDATE transactions
            SET invoice_id = %s
            WHERE tenant_id = %s AND transaction_id = %s
        """
        db_manager.execute_query(update_transaction_query, (invoice_id, tenant_id, transaction_id))

        # Log the manual match
        log_query = """
            INSERT INTO invoice_match_log
            (invoice_id, transaction_id, action, score, match_type, user_id, created_at)
            VALUES (%s, %s, 'MANUAL_MATCH', 1.0, 'MANUAL', %s, CURRENT_TIMESTAMP)
        """
        db_manager.execute_query(log_query, (invoice_id, transaction_id, user_id))

        return jsonify({
            'success': True,
            'message': 'Manual match created successfully'
        })

    except Exception as e:
        logger.error(f"Error creating manual match: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/matched-pairs')
def api_get_matched_pairs():
    """Retorna invoices que já foram matchados com transações"""
    try:
        tenant_id = get_current_tenant_id()
        from database import db_manager
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        offset = (page - 1) * per_page

        query = """
            SELECT
                i.id as invoice_id,
                i.invoice_number,
                i.vendor_name,
                i.total_amount as invoice_amount,
                i.currency,
                i.date as invoice_date,
                i.due_date,
                i.status,
                t.transaction_id,
                t.description,
                t.amount as transaction_amount,
                t.date as transaction_date,
                t.classified_entity,
                log.action,
                log.score,
                log.match_type,
                log.user_id,
                log.created_at as matched_at
            FROM invoices i
            JOIN transactions t ON i.linked_transaction_id = t.transaction_id
            LEFT JOIN invoice_match_log log ON i.id = log.invoice_id AND t.transaction_id = log.transaction_id
            WHERE i.linked_transaction_id IS NOT NULL AND i.linked_transaction_id != ''
            AND i.tenant_id = %s
            AND t.tenant_id = %s
            ORDER BY COALESCE(log.created_at, i.created_at) DESC
            LIMIT %s OFFSET %s
        """

        pairs = db_manager.execute_query(query, (tenant_id, tenant_id, per_page, offset), fetch_all=True)

        # Get total count
        count_query = """
            SELECT COUNT(*) as total
            FROM invoices i
            JOIN transactions t ON i.linked_transaction_id = t.transaction_id
            WHERE i.linked_transaction_id IS NOT NULL AND i.linked_transaction_id != ''
            AND i.tenant_id = %s
            AND t.tenant_id = %s
        """
        total_result = db_manager.execute_query(count_query, (tenant_id, tenant_id), fetch_one=True)
        total = total_result['total'] if total_result else 0

        # Format pairs for frontend
        formatted_pairs = []
        for pair in pairs:
            formatted_pairs.append({
                'invoice_id': pair['invoice_id'],
                'transaction_id': pair['transaction_id'],
                'matched_at': pair['matched_at'],
                'match_type': pair['match_type'],
                'match_action': pair['action'],
                'match_score': float(pair['score']) if pair['score'] else None,
                'matched_by': pair['user_id'],
                'invoice': {
                    'number': pair['invoice_number'],
                    'vendor_name': pair['vendor_name'],
                    'amount': float(pair['invoice_amount']),
                    'currency': pair['currency'],
                    'date': pair['invoice_date'],
                    'due_date': pair['due_date'],
                    'status': pair['status']
                },
                'transaction': {
                    'description': pair['description'],
                    'amount': float(pair['transaction_amount']),
                    'date': pair['transaction_date'],
                    'classified_entity': pair['classified_entity']
                }
            })

        return jsonify({
            'success': True,
            'pairs': formatted_pairs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        logger.error(f"Error getting matched pairs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/stats')
def api_get_revenue_stats():
    """Retorna estatísticas do sistema de revenue matching"""
    try:
        from database import db_manager
        stats = {}

        # Get current tenant_id for multi-tenant isolation
        tenant_id = get_current_tenant_id()

        # Total invoices
        query = "SELECT COUNT(*) as total FROM invoices WHERE tenant_id = %s"
        result = db_manager.execute_query(query, (tenant_id,), fetch_one=True)
        stats['total_invoices'] = result['total'] if result else 0

        # Matched invoices
        query = """
            SELECT COUNT(*) as matched
            FROM invoices
            WHERE tenant_id = %s AND linked_transaction_id IS NOT NULL AND linked_transaction_id != ''
        """
        result = db_manager.execute_query(query, (tenant_id,), fetch_one=True)
        stats['matched_invoices'] = result['matched'] if result else 0

        # Unmatched invoices
        stats['unmatched_invoices'] = stats['total_invoices'] - stats['matched_invoices']

        # Pending matches for review
        query = """
            SELECT COUNT(*) as pending
            FROM pending_invoice_matches pm
            JOIN invoices i ON pm.invoice_id = i.id
            WHERE pm.status = 'pending' AND i.tenant_id = %s
        """
        result = db_manager.execute_query(query, (tenant_id,), fetch_one=True)
        stats['pending_matches'] = result['pending'] if result else 0

        # Total revenue amounts (using USD equivalent for multi-currency support)
        # Use usd_equivalent_amount if available and > 0, otherwise use total_amount for USD invoices
        query = """
            SELECT
                COALESCE(SUM(CASE WHEN linked_transaction_id IS NOT NULL
                    THEN CASE WHEN usd_equivalent_amount IS NOT NULL AND usd_equivalent_amount > 0
                              THEN usd_equivalent_amount
                              ELSE total_amount
                         END
                    ELSE 0 END), 0) as matched_revenue,
                COALESCE(SUM(CASE WHEN linked_transaction_id IS NULL
                    THEN CASE WHEN usd_equivalent_amount IS NOT NULL AND usd_equivalent_amount > 0
                              THEN usd_equivalent_amount
                              ELSE total_amount
                         END
                    ELSE 0 END), 0) as unmatched_revenue,
                COALESCE(SUM(
                    CASE WHEN usd_equivalent_amount IS NOT NULL AND usd_equivalent_amount > 0
                         THEN usd_equivalent_amount
                         ELSE total_amount
                    END
                ), 0) as total_revenue
            FROM invoices
            WHERE tenant_id = %s
        """
        result = db_manager.execute_query(query, (tenant_id,), fetch_one=True)
        if result:
            stats['matched_revenue'] = float(result['matched_revenue'])
            stats['unmatched_revenue'] = float(result['unmatched_revenue'])
            stats['total_revenue'] = float(result['total_revenue'])
        else:
            stats['matched_revenue'] = 0
            stats['unmatched_revenue'] = 0
            stats['total_revenue'] = 0

        # Match rate percentage
        if stats['total_invoices'] > 0:
            stats['match_rate'] = (stats['matched_invoices'] / stats['total_invoices']) * 100
        else:
            stats['match_rate'] = 0

        # Recent matching activity (last 30 days)
        query = """
            SELECT COUNT(*) as recent_matches
            FROM invoice_match_log iml
            JOIN invoices i ON iml.invoice_id = i.id
            WHERE iml.created_at >= CURRENT_DATE - INTERVAL '30 days'
            AND i.tenant_id = %s
        """
        result = db_manager.execute_query(query, (tenant_id,), fetch_one=True)
        stats['recent_matches'] = result['recent_matches'] if result else 0

        # Match types breakdown
        query = """
            SELECT
                iml.match_type,
                COUNT(*) as count
            FROM invoice_match_log iml
            JOIN invoices i ON iml.invoice_id = i.id
            WHERE iml.action IN ('AUTO_APPLIED', 'MANUAL_CONFIRMED', 'MANUAL_MATCH')
            AND i.tenant_id = %s
            GROUP BY iml.match_type
            ORDER BY count DESC
        """
        result = db_manager.execute_query(query, (tenant_id,), fetch_all=True)
        stats['match_types'] = {row['match_type']: row['count'] for row in result} if result else {}

        # Transaction statistics (opposite side of matching)
        # Total transactions
        query = "SELECT COUNT(*) as total FROM transactions WHERE tenant_id = %s"
        result = db_manager.execute_query(query, (tenant_id,), fetch_one=True)
        stats['total_transactions'] = result['total'] if result else 0

        # Linked transactions (transactions that are already linked to invoices)
        query = """
            SELECT COUNT(DISTINCT t.transaction_id) as linked
            FROM transactions t
            JOIN invoices i ON i.linked_transaction_id = t.transaction_id
            WHERE i.linked_transaction_id IS NOT NULL AND i.linked_transaction_id != ''
            AND t.tenant_id = %s AND i.tenant_id = %s
        """
        result = db_manager.execute_query(query, (tenant_id, tenant_id), fetch_one=True)
        stats['linked_transactions'] = result['linked'] if result else 0

        # Unlinked transactions (transactions not linked to any invoice)
        stats['unlinked_transactions'] = stats['total_transactions'] - stats['linked_transactions']

        # Revenue transactions specifically (positive amounts that could match invoices)
        query = """
            SELECT COUNT(*) as revenue_transactions
            FROM transactions
            WHERE amount > 0 AND tenant_id = %s
        """
        result = db_manager.execute_query(query, (tenant_id,), fetch_one=True)
        stats['revenue_transactions'] = result['revenue_transactions'] if result else 0

        # Unlinked revenue transactions (positive transactions not linked to invoices)
        query = """
            SELECT COUNT(*) as unlinked_revenue_transactions
            FROM transactions t
            WHERE t.amount > 0
            AND t.tenant_id = %s
            AND t.transaction_id NOT IN (
                SELECT DISTINCT i.linked_transaction_id
                FROM invoices i
                WHERE i.linked_transaction_id IS NOT NULL AND i.linked_transaction_id != ''
                AND i.tenant_id = %s
            )
        """
        result = db_manager.execute_query(query, (tenant_id, tenant_id), fetch_one=True)
        stats['unlinked_revenue_transactions'] = result['unlinked_revenue_transactions'] if result else 0

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Error getting revenue stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/unmatch', methods=['POST'])
def api_unmatch_invoice():
    """
    Remove o match de um invoice
    Body: {
        "invoice_id": "string",
        "user_id": "string" (opcional),
        "reason": "string" (opcional)
    }
    """
    try:
        from database import db_manager
        data = request.get_json()
        invoice_id = data.get('invoice_id')
        user_id = data.get('user_id', 'Unknown')
        reason = data.get('reason', 'Manual unmatch by user')

        if not invoice_id:
            return jsonify({'success': False, 'error': 'invoice_id is required'}), 400

        # Get current match info for logging
        query = """
            SELECT linked_transaction_id
            FROM invoices
            WHERE id = %s AND linked_transaction_id IS NOT NULL
        """
        result = db_manager.execute_query(query, (invoice_id,), fetch_one=True)

        if not result:
            return jsonify({'success': False, 'error': 'Invoice not found or not matched'}), 404

        transaction_id = result['linked_transaction_id']

        # Remove the match
        update_query = """
            UPDATE invoices
            SET linked_transaction_id = NULL,
                status = 'pending'
            WHERE id = %s
        """
        db_manager.execute_query(update_query, (invoice_id,))

        # Log the unmatch action
        log_query = """
            INSERT INTO invoice_match_log
            (invoice_id, transaction_id, action, score, match_type, user_id, created_at)
            VALUES (%s, %s, 'MANUAL_UNMATCHED', 0.0, 'UNMATCH', %s, CURRENT_TIMESTAMP)
        """
        db_manager.execute_query(log_query, (invoice_id, transaction_id, user_id))

        return jsonify({
            'success': True,
            'message': 'Invoice unmatched successfully'
        })

    except Exception as e:
        logger.error(f"Error unmatching invoice: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ===============================================
# ROBUST REVENUE MATCHING API ENDPOINTS
# ===============================================

@app.route('/api/revenue/run-robust-matching', methods=['POST'])
def api_run_robust_revenue_matching():
    """
    Executa matching robusto de invoices com transações para produção
    Body: {
        "invoice_ids": ["id1", "id2", ...] (opcional),
        "auto_apply": true/false,
        "enable_learning": true/false (padrão: true)
    }
    """
    try:
        from robust_revenue_matcher import run_robust_invoice_matching

        data = request.get_json() or {}
        invoice_ids = data.get('invoice_ids')
        auto_apply = data.get('auto_apply', False)
        enable_learning = data.get('enable_learning', True)

        # Execute robust matching
        result = run_robust_invoice_matching(
            invoice_ids=invoice_ids,
            auto_apply=auto_apply,
            enable_learning=enable_learning
        )

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in robust revenue matching: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'stats': {
                'total_invoices_processed': 0,
                'total_matches_found': 0,
                'errors_count': 1
            }
        }), 500

@app.route('/api/revenue/health')
def api_revenue_health_check():
    """
    Health check para o sistema de revenue matching
    Retorna status de conectividade e performance do banco
    """
    try:
        from database import db_manager

        # Perform database health check
        health_status = db_manager.health_check()

        # Additional checks specific to revenue matching
        revenue_health = {
            'database': health_status,
            'revenue_tables': {},
            'claude_api': {
                'available': bool(os.getenv('ANTHROPIC_API_KEY')),
                'status': 'configured' if os.getenv('ANTHROPIC_API_KEY') else 'not_configured'
            }
        }

        # Check revenue-specific tables
        revenue_tables = ['invoices', 'transactions', 'pending_invoice_matches', 'invoice_match_log']

        for table in revenue_tables:
            try:
                if db_manager.db_type == 'postgresql':
                    query = """
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_name = %s
                        )
                    """
                else:
                    query = """
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name = ?
                    """

                result = db_manager.execute_query(query, (table,), fetch_one=True)

                if db_manager.db_type == 'postgresql':
                    exists = result['exists'] if result else False
                else:
                    exists = bool(result)

                revenue_health['revenue_tables'][table] = 'exists' if exists else 'missing'

            except Exception as e:
                revenue_health['revenue_tables'][table] = f'error: {str(e)}'

        # Overall health status
        overall_status = 'healthy'
        if health_status['status'] != 'healthy':
            overall_status = 'unhealthy'
        elif any(status != 'exists' for status in revenue_health['revenue_tables'].values()):
            overall_status = 'degraded'

        revenue_health['overall_status'] = overall_status

        return jsonify({
            'success': True,
            'health': revenue_health
        })

    except Exception as e:
        logger.error(f"Error in revenue health check: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'health': {
                'overall_status': 'unhealthy',
                'error': str(e)
            }
        }), 500

@app.route('/api/revenue/batch-operations', methods=['POST'])
def api_revenue_batch_operations():
    """
    Executa operações em lote no sistema de revenue
    Body: {
        "operations": [
            {
                "type": "confirm_match",
                "invoice_id": "string",
                "transaction_id": "string",
                "user_id": "string"
            },
            {
                "type": "reject_match",
                "invoice_id": "string",
                "transaction_id": "string",
                "user_id": "string",
                "reason": "string"
            }
        ]
    }
    """
    try:
        from database import db_manager

        data = request.get_json() or {}
        operations = data.get('operations', [])

        if not operations:
            return jsonify({
                'success': False,
                'error': 'No operations provided'
            }), 400

        # Prepare batch operations for database
        db_operations = []
        results = {
            'total_operations': len(operations),
            'successful_operations': 0,
            'failed_operations': 0,
            'errors': []
        }

        for i, operation in enumerate(operations):
            op_type = operation.get('type')
            invoice_id = operation.get('invoice_id')
            transaction_id = operation.get('transaction_id')
            user_id = operation.get('user_id', 'system')

            try:
                if op_type == 'confirm_match':
                    # Add operation to update invoice
                    update_query = """
                        UPDATE invoices
                        SET linked_transaction_id = ?,
                            payment_status = 'paid'
                        WHERE id = ?
                    """
                    if db_manager.db_type == 'postgresql':
                        update_query = update_query.replace('?', '%s')

                    db_operations.append({
                        'query': update_query,
                        'params': (transaction_id, invoice_id)
                    })

                    # Add log operation
                    log_query = """
                        INSERT INTO invoice_match_log
                        (invoice_id, transaction_id, action, score, match_type, user_id, created_at)
                        VALUES (?, ?, 'BATCH_CONFIRMED', 1.0, 'BATCH_OPERATION', ?, CURRENT_TIMESTAMP)
                    """
                    if db_manager.db_type == 'postgresql':
                        log_query = log_query.replace('?', '%s')

                    db_operations.append({
                        'query': log_query,
                        'params': (invoice_id, transaction_id, user_id)
                    })

                elif op_type == 'reject_match':
                    # Remove from pending matches
                    delete_query = """
                        DELETE FROM pending_invoice_matches
                        WHERE invoice_id = ? AND transaction_id = ?
                    """
                    if db_manager.db_type == 'postgresql':
                        delete_query = delete_query.replace('?', '%s')

                    db_operations.append({
                        'query': delete_query,
                        'params': (invoice_id, transaction_id)
                    })

                    # Add log operation
                    log_query = """
                        INSERT INTO invoice_match_log
                        (invoice_id, transaction_id, action, score, match_type, user_id, created_at)
                        VALUES (?, ?, 'BATCH_REJECTED', 0.0, 'BATCH_OPERATION', ?, CURRENT_TIMESTAMP)
                    """
                    if db_manager.db_type == 'postgresql':
                        log_query = log_query.replace('?', '%s')

                    db_operations.append({
                        'query': log_query,
                        'params': (invoice_id, transaction_id, user_id)
                    })

                else:
                    results['failed_operations'] += 1
                    results['errors'].append(f"Operation {i}: Unknown operation type '{op_type}'")

            except Exception as e:
                results['failed_operations'] += 1
                results['errors'].append(f"Operation {i}: {str(e)}")

        # Execute batch operations
        if db_operations:
            batch_results = db_manager.execute_batch_operation(db_operations, batch_size=50)
            results['successful_operations'] = batch_results['successful_batches'] * 2  # Each operation has 2 queries
            results['database_stats'] = batch_results

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        logger.error(f"Error in batch operations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/performance-stats')
def api_revenue_performance_stats():
    """
    Retorna estatísticas de performance do sistema de matching
    """
    try:
        from database import db_manager

        # Get database health
        health_status = db_manager.health_check()

        # Performance metrics
        performance_stats = {
            'database_response_time_ms': health_status.get('response_time_ms', 0),
            'connection_pool_status': health_status.get('connection_pool_status'),
            'recent_activity': {}
        }

        # Recent matching activity (last 24 hours)
        query = """
            SELECT
                action,
                COUNT(*) as count,
                AVG(score) as avg_score
            FROM invoice_match_log
            WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
            GROUP BY action
            ORDER BY count DESC
        """

        if db_manager.db_type == 'sqlite':
            query = """
                SELECT
                    action,
                    COUNT(*) as count,
                    AVG(score) as avg_score
                FROM invoice_match_log
                WHERE created_at >= datetime('now', '-24 hours')
                GROUP BY action
                ORDER BY count DESC
            """

        try:
            result = db_manager.execute_query(query, fetch_all=True)
            for row in result:
                performance_stats['recent_activity'][row['action']] = {
                    'count': row['count'],
                    'avg_score': round(row['avg_score'], 2) if row['avg_score'] else 0
                }
        except Exception as e:
            logger.warning(f"Could not get recent activity stats: {e}")
            performance_stats['recent_activity'] = {}

        # Batch processing stats (if available)
        try:
            batch_query = """
                SELECT COUNT(*) as total_batches
                FROM invoice_match_log
                WHERE match_type LIKE '%BATCH%'
                AND created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
            """

            if db_manager.db_type == 'sqlite':
                batch_query = """
                    SELECT COUNT(*) as total_batches
                    FROM invoice_match_log
                    WHERE match_type LIKE '%BATCH%'
                    AND created_at >= datetime('now', '-7 days')
                """

            result = db_manager.execute_query(batch_query, fetch_one=True)
            performance_stats['batch_operations_last_week'] = result['total_batches'] if result else 0

        except Exception as e:
            logger.warning(f"Could not get batch stats: {e}")
            performance_stats['batch_operations_last_week'] = 0

        return jsonify({
            'success': True,
            'performance': performance_stats
        })

    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/sync-classifications', methods=['POST'])
def api_sync_revenue_classifications():
    """
    Sync transaction classifications with revenue recognition matches
    Updates transactions that are matched to invoices but not classified as Revenue

    This endpoint is called automatically when users visit the dashboard
    """
    try:
        from revenue_sync import sync_revenue_now
        from flask import session

        # Get session ID for tracking
        session_id = session.get('user_id', 'anonymous')

        logger.info(f" Revenue sync triggered by session: {session_id}")

        # Execute sync
        sync_result = sync_revenue_now(session_id)

        if sync_result['success']:
            # Store in session for notification display
            if sync_result['transactions_updated'] > 0:
                session['revenue_sync_notification'] = {
                    'count': sync_result['transactions_updated'],
                    'timestamp': sync_result['timestamp'],
                    'changes': sync_result['changes'][:10]  # Limit to 10 for display
                }
                logger.info(f" Revenue sync: {sync_result['transactions_updated']} transactions updated")
            else:
                logger.info(" Revenue sync: No updates needed")

        return jsonify(sync_result)

    except Exception as e:
        logger.error(f" Error in revenue sync endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'transactions_updated': 0
        }), 500

@app.route('/api/revenue/sync-notification', methods=['GET'])
def api_get_sync_notification():
    """
    Get pending sync notification for current session
    Called by dashboard to check if there are updates to display
    """
    try:
        from flask import session

        notification = session.get('revenue_sync_notification')

        if notification:
            return jsonify({
                'success': True,
                'has_notification': True,
                'notification': notification
            })
        else:
            return jsonify({
                'success': True,
                'has_notification': False
            })

    except Exception as e:
        logger.error(f"Error getting sync notification: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/revenue/dismiss-sync-notification', methods=['POST'])
def api_dismiss_sync_notification():
    """
    Dismiss the sync notification for current session
    """
    try:
        from flask import session

        if 'revenue_sync_notification' in session:
            del session['revenue_sync_notification']

        return jsonify({
            'success': True,
            'message': 'Notification dismissed'
        })

    except Exception as e:
        logger.error(f"Error dismissing notification: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# EXPENSE MATCHING API ENDPOINTS
# ============================================

@app.route('/api/expense/run-expense-matching', methods=['POST'])
def api_run_expense_matching():
    """
    EXPENSE MATCHING: Matches expense transactions to invoices/bills
    Similar to revenue matching but for expenses (negative amounts)
    Body: {
        "auto_apply": true/false (se deve aplicar matches automáticos)
    }
    """
    global active_matcher

    try:
        from database import db_manager
        data = request.get_json() or {}
        auto_apply = data.get('auto_apply', False)

        # 1. PREVENÇÃO DE CLIQUES DUPLOS
        with matcher_lock:
            if active_matcher is not None:
                return jsonify({
                    'success': False,
                    'error': 'Expense matching process already running',
                    'message': 'Processo já em execução. Aguarde a conclusão.'
                }), 409  # Conflict

            # 2. INICIALIZAR ULTRA-FAST MATCHER PARA EXPENSES
            from ultra_fast_matcher_fixed import UltraFastMatcher
            active_matcher = UltraFastMatcher()

        logger.info(f"EXPENSE MATCHING: Starting ultra-fast expense matcher")

        def run_expense_matching_async():
            global active_matcher
            try:
                # Get expense transactions (negative amounts) that need matching
                expense_transactions = db_manager.execute_query("""
                    SELECT transaction_id, amount, date, description, classified_entity
                    FROM transactions
                    WHERE amount < 0
                    AND (invoice_id IS NULL OR invoice_id = '')
                    AND (archived = FALSE OR archived IS NULL)
                    ORDER BY ABS(amount) DESC, date DESC
                    LIMIT 500
                """, fetch_all=True)

                if not expense_transactions:
                    return {
                        'success': True,
                        'total_matches': 0,
                        'message': 'No unmatched expense transactions found',
                        'processing_time': 0.0
                    }

                # Get available invoices to match against
                available_invoices = db_manager.execute_query("""
                    SELECT id as invoice_id, vendor_name, total_amount, date, invoice_number, customer_name
                    FROM invoices
                    WHERE (linked_transaction_id IS NULL OR linked_transaction_id = '')
                    ORDER BY date DESC
                """, fetch_all=True)

                if not available_invoices:
                    return {
                        'success': True,
                        'total_matches': 0,
                        'message': 'No available invoices to match against',
                        'processing_time': 0.0
                    }

                # Run matching algorithm adapted for expenses
                start_time = time.time()
                matches = []

                for transaction in expense_transactions[:100]:  # Limit for performance
                    tx_amount = abs(float(transaction['amount']))  # Make positive for comparison
                    tx_date = transaction['date']

                    # Find best matching invoice
                    best_match = None
                    best_score = 0.0

                    for invoice in available_invoices:
                        inv_amount = float(invoice['total_amount'])
                        inv_date = invoice['date']

                        # Amount similarity (within 5% tolerance)
                        amount_diff = abs(tx_amount - inv_amount) / max(tx_amount, inv_amount)
                        if amount_diff > 0.05:  # More than 5% difference
                            continue

                        amount_score = 1.0 - amount_diff

                        # Date proximity (within 90 days)
                        try:
                            if isinstance(tx_date, str):
                                tx_date_obj = datetime.strptime(tx_date, '%Y-%m-%d').date()
                            else:
                                tx_date_obj = tx_date

                            if isinstance(inv_date, str):
                                inv_date_obj = datetime.strptime(inv_date, '%Y-%m-%d').date()
                            else:
                                inv_date_obj = inv_date

                            date_diff = abs((tx_date_obj - inv_date_obj).days)
                            if date_diff > 90:  # More than 90 days difference
                                continue

                            date_score = max(0, 1.0 - (date_diff / 90))
                        except:
                            date_score = 0.1  # Small score if date parsing fails

                        # Entity/vendor similarity
                        tx_entity = transaction.get('classified_entity', '').lower()
                        vendor_name = invoice.get('vendor_name', '').lower()
                        entity_score = 0.3 if tx_entity and vendor_name and (tx_entity in vendor_name or vendor_name in tx_entity) else 0.1

                        # Combined score
                        total_score = (amount_score * 0.5) + (date_score * 0.3) + (entity_score * 0.2)

                        if total_score > best_score and total_score > 0.6:  # Minimum threshold
                            best_score = total_score
                            best_match = invoice

                    # If we found a good match, add it
                    if best_match and best_score > 0.6:
                        confidence = 'HIGH' if best_score > 0.8 else 'MEDIUM'
                        matches.append({
                            'transaction_id': transaction['transaction_id'],
                            'invoice_id': best_match['invoice_id'],
                            'score': best_score,
                            'confidence_level': confidence,
                            'match_type': 'EXPENSE_MATCH',
                            'explanation': f'Expense match: {best_score:.3f} score (amount: ${tx_amount:.2f})'
                        })

                processing_time = time.time() - start_time

                # Save matches to pending table (reuse existing table structure)
                for match in matches:
                    db_manager.execute_query("""
                        INSERT INTO pending_invoice_matches
                        (invoice_id, transaction_id, score, match_type, confidence_level, explanation, status)
                        VALUES (%s, %s, %s, %s, %s, %s, 'pending')
                        ON CONFLICT (invoice_id, transaction_id) DO NOTHING
                    """, (
                        match['invoice_id'],
                        match['transaction_id'],
                        match['score'],
                        match['match_type'],
                        match['confidence_level'],
                        match['explanation']
                    ))

                return {
                    'success': True,
                    'total_matches': len(matches),
                    'processing_time': processing_time,
                    'expense_transactions_processed': len(expense_transactions),
                    'available_invoices': len(available_invoices),
                    'message': f'Successfully found {len(matches)} expense matches'
                }

            except Exception as e:
                logger.error(f"Error in expense matching: {e}")
                raise
            finally:
                # Clean up
                with matcher_lock:
                    active_matcher = None

        # Execute matching
        import threading
        result_container = {}
        error_container = {}

        def thread_worker():
            try:
                result_container['result'] = run_expense_matching_async()
            except Exception as e:
                error_container['error'] = e

        thread = threading.Thread(target=thread_worker)
        thread.start()
        thread.join(timeout=30)  # 30 second timeout

        if thread.is_alive():
            return jsonify({
                'success': False,
                'error': 'Expense matching timeout',
                'message': 'O processo demorou mais que 30 segundos'
            }), 408

        if 'error' in error_container:
            raise error_container['error']

        if 'result' not in result_container:
            return jsonify({
                'success': False,
                'error': 'No result from expense matching'
            }), 500

        return jsonify(result_container['result'])

    except Exception as e:
        logger.error(f"Critical error in expense matching: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ============================================
# TRANSACTION CHAIN API ENDPOINTS
# ============================================

# Import Transaction Chain Analyzer
try:
    from transaction_chain_analyzer import TransactionChainAnalyzer
    CHAIN_ANALYZER_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Transaction Chain Analyzer not available: {e}")
    CHAIN_ANALYZER_AVAILABLE = False

@app.route('/api/transactions/<transaction_id>/chains', methods=['GET'])
def api_get_transaction_chains(transaction_id):
    """Get intelligent transaction chains for a specific transaction"""
    if not CHAIN_ANALYZER_AVAILABLE:
        return jsonify({
            "error": "Transaction Chain Analyzer not available",
            "fallback_message": "Opening dashboard with transaction search instead"
        }), 503

    try:
        analyzer = TransactionChainAnalyzer()
        chains = analyzer.find_transaction_chains(transaction_id)

        # Add metadata for UI
        chains['api_version'] = '1.0'
        chains['timestamp'] = datetime.now().isoformat()

        return jsonify(chains)

    except Exception as e:
        logger.error(f"Error analyzing transaction chains for {transaction_id}: {e}")
        return jsonify({
            "error": str(e),
            "transaction_id": transaction_id,
            "fallback_action": "dashboard_search"
        }), 500

@app.route('/api/system/transaction-chains', methods=['GET'])
def api_get_system_transaction_chains():
    """Get system-wide transaction chain analysis"""
    if not CHAIN_ANALYZER_AVAILABLE:
        return jsonify({
            "error": "Transaction Chain Analyzer not available"
        }), 503

    try:
        limit = request.args.get('limit', 50, type=int)
        analyzer = TransactionChainAnalyzer()
        chains = analyzer.find_transaction_chains(limit=limit)

        # Add metadata
        chains['api_version'] = '1.0'
        chains['timestamp'] = datetime.now().isoformat()

        return jsonify(chains)

    except Exception as e:
        logger.error(f"Error analyzing system transaction chains: {e}")
        return jsonify({
            "error": str(e),
            "system_analysis": True
        }), 500

@app.route('/api/transactions/chains/stats', methods=['GET'])
def api_get_chain_stats():
    """Get transaction chain statistics and insights"""
    if not CHAIN_ANALYZER_AVAILABLE:
        return jsonify({
            "error": "Transaction Chain Analyzer not available"
        }), 503

    try:
        analyzer = TransactionChainAnalyzer()

        # Get system-wide analysis for statistics
        system_analysis = analyzer.find_transaction_chains(limit=100)

        if 'chains_detected' in system_analysis:
            chains = system_analysis.get('top_chains', [])
            pattern_distribution = system_analysis.get('pattern_distribution', {})

            stats = {
                'total_chains_detected': system_analysis['chains_detected'],
                'total_transactions_analyzed': system_analysis.get('total_transactions_analyzed', 0),
                'pattern_distribution': pattern_distribution,
                'top_patterns': sorted(pattern_distribution.items(), key=lambda x: x[1], reverse=True)[:5],
                'high_confidence_chains': len([c for c in chains if c.get('confidence', 0) > 0.8]),
                'medium_confidence_chains': len([c for c in chains if 0.6 <= c.get('confidence', 0) <= 0.8]),
                'low_confidence_chains': len([c for c in chains if c.get('confidence', 0) < 0.6]),
                'recommendations': system_analysis.get('recommendations', []),
                'last_analysis': datetime.now().isoformat()
            }
        else:
            stats = {
                'error': 'No chain analysis data available',
                'total_chains_detected': 0
            }

        return jsonify(stats)

    except Exception as e:
        logger.error(f"Error getting chain stats: {e}")
        return jsonify({
            "error": str(e)
        }), 500


# ============================================================================
# BLOCKCHAIN ENRICHMENT ENDPOINTS
# ============================================================================

@app.route('/api/transactions/<transaction_id>/enrich', methods=['POST'])
def api_enrich_transaction(transaction_id):
    """
    Enrich a single transaction with blockchain data
    """
    try:
        from transaction_enrichment import enricher

        data = request.get_json() or {}
        txid = data.get('txid')
        chain_hint = data.get('chain')

        result = enricher.enrich_transaction(
            transaction_id=transaction_id,
            txid=txid,
            chain_hint=chain_hint
        )

        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Error enriching transaction: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/transactions/enrich/bulk', methods=['POST'])
def api_bulk_enrich_transactions():
    """
    Bulk enrich multiple transactions
    """
    try:
        from transaction_enrichment import enricher

        data = request.get_json() or {}
        transaction_ids = data.get('transaction_ids')
        limit = data.get('limit', 100)

        result = enricher.bulk_enrich_transactions(
            transaction_ids=transaction_ids,
            limit=limit
        )

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error in bulk enrichment: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/transactions/enrich/auto', methods=['POST'])
def api_auto_enrich_pending():
    """
    Automatically enrich all pending transactions
    Looks for transactions with TXID in description/identifier
    """
    try:
        from transaction_enrichment import enricher

        data = request.get_json() or {}
        limit = data.get('limit', 50)

        result = enricher.bulk_enrich_transactions(limit=limit)

        return jsonify({
            "success": True,
            "summary": result
        }), 200

    except Exception as e:
        logger.error(f"Error in auto enrichment: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/transactions/enrich/all-pending', methods=['POST'])
def api_enrich_all_pending():
    """
    Enrich ALL pending transactions in the database (no limit)
    Useful for:
    - Initial blockchain enrichment of uploaded files
    - Re-matching after adding new known wallets
    - Periodic enrichment runs
    """
    try:
        from transaction_enrichment import enricher
        from database import db_manager

        data = request.get_json() or {}
        batch_size = data.get('batch_size', 100)  # Process in batches

        # Get ALL pending transactions with blockchain hashes
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT transaction_id, description, identifier
                FROM transactions
                WHERE tenant_id = 'delta'
                  AND (enrichment_status IS NULL OR enrichment_status = 'pending')
                  AND (identifier IS NOT NULL AND identifier != 'nan' AND identifier != '')
                ORDER BY date DESC
            """)
            pending_transactions = cursor.fetchall()

        total_pending = len(pending_transactions)
        logger.info(f"Found {total_pending} pending transactions to enrich")

        # Process in batches
        all_results = {
            'total_pending': total_pending,
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'batches_processed': 0
        }

        for i in range(0, total_pending, batch_size):
            batch = pending_transactions[i:i + batch_size]
            batch_ids = [tx[0] for tx in batch]

            logger.info(f"Processing batch {i // batch_size + 1}: {len(batch_ids)} transactions")

            result = enricher.bulk_enrich_transactions(
                transaction_ids=batch_ids,
                limit=batch_size
            )

            all_results['total_processed'] += result.get('total_processed', 0)
            all_results['successful'] += result.get('successful', 0)
            all_results['failed'] += result.get('failed', 0)
            all_results['skipped'] += result.get('skipped', 0)
            all_results['batches_processed'] += 1

        return jsonify({
            "success": True,
            "message": f"Processed {all_results['total_processed']} transactions",
            "results": all_results
        }), 200

    except Exception as e:
        logger.error(f"Error in bulk enrichment: {e}")
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/transactions/find-duplicates', methods=['POST'])
def api_find_duplicates():
    """
    Find duplicate transactions in the database
    Groups transactions that have the same date, description, and amount (±$0.01)
    """
    from database import db_manager

    try:
        tenant_id = session.get('tenant_id', 'delta')

        logger.info(f" Finding duplicate transactions for tenant: {tenant_id}")

        # Use a single PostgreSQL connection for all queries
        conn = db_manager._get_postgresql_connection()
        try:
            cursor = conn.cursor()

            # Find groups of duplicates (same date, description, and amount within $0.01)
            cursor.execute("""
                WITH duplicate_groups AS (
                    SELECT
                        date,
                        description,
                        ROUND(amount::numeric, 2) as amount_rounded,
                        COUNT(*) as duplicate_count,
                        ARRAY_AGG(transaction_id ORDER BY transaction_id) as transaction_ids
                    FROM transactions
                    WHERE tenant_id = %s
                      AND archived = false
                    GROUP BY date, description, ROUND(amount::numeric, 2)
                    HAVING COUNT(*) > 1
                )
                SELECT
                    date,
                    description,
                    amount_rounded,
                    duplicate_count,
                    transaction_ids
                FROM duplicate_groups
                ORDER BY date DESC, duplicate_count DESC
            """, (tenant_id,))

            duplicate_groups_raw = cursor.fetchall()

            logger.info(f"Found {len(duplicate_groups_raw)} duplicate groups")

            # Now fetch full transaction details for each group
            duplicate_groups = []

            for group in duplicate_groups_raw:
                date, description, amount, count, transaction_ids = group

                # Fetch full transaction details
                placeholders = ','.join(['%s'] * len(transaction_ids))
                cursor.execute(f"""
                    SELECT
                        transaction_id,
                        date,
                        description,
                        amount,
                        classified_entity,
                        accounting_category,
                        subcategory,
                        confidence,
                        source_file
                    FROM transactions
                    WHERE transaction_id IN ({placeholders})
                    ORDER BY transaction_id
                """, transaction_ids)

                transactions = []
                for row in cursor.fetchall():
                    txn_date = row[1]
                    # Handle both date objects and strings
                    if txn_date:
                        date_str = txn_date.strftime('%Y-%m-%d') if hasattr(txn_date, 'strftime') else str(txn_date)
                    else:
                        date_str = None

                    transactions.append({
                        'transaction_id': row[0],
                        'date': date_str,
                        'description': row[2],
                        'amount': float(row[3]) if row[3] else 0,
                        'classified_entity': row[4],
                        'accounting_category': row[5],
                        'subcategory': row[6],
                        'confidence': float(row[7]) if row[7] else 0,
                        'source_file': row[8]
                    })

                # Handle both date objects and strings for group date
                if date:
                    group_date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
                else:
                    group_date_str = None

                duplicate_groups.append({
                    'date': group_date_str,
                    'description': description,
                    'amount': float(amount),
                    'count': count,
                    'transactions': transactions
                })

            total_duplicate_transactions = sum(group['count'] for group in duplicate_groups)

            logger.info(f" Found {len(duplicate_groups)} groups with {total_duplicate_transactions} duplicate transactions")

            return jsonify({
                "success": True,
                "duplicate_groups": duplicate_groups,
                "total_groups": len(duplicate_groups),
                "total_duplicates": total_duplicate_transactions
            }), 200

        finally:
            conn.close()

    except Exception as e:
        logger.error(f"Error finding duplicates: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/blockchain/test/<txid>', methods=['GET'])
def api_test_blockchain_lookup(txid):
    """
    Test blockchain lookup for a transaction ID
    """
    try:
        from blockchain_explorer import explorer

        chain = request.args.get('chain')
        result = explorer.get_transaction_details(txid, chain_hint=chain)

        if result:
            return jsonify({
                "success": True,
                "data": result
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Transaction not found or unsupported chain"
            }), 404

    except Exception as e:
        logger.error(f"Error testing blockchain lookup: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================================
# TENANT CONFIGURATION API ENDPOINTS
# ============================================================================

@app.route('/api/tenant/config/<config_type>', methods=['GET'])
def api_get_tenant_config(config_type):
    """
    Get tenant configuration by type.

    Args:
        config_type: Type of configuration ('entities', 'business_context', 'accounting_categories', 'pattern_matching_rules')

    Returns:
        JSON with configuration data
    """
    try:
        from tenant_config import get_current_tenant_id, get_tenant_configuration

        tenant_id = get_current_tenant_id()
        config = get_tenant_configuration(tenant_id, config_type)

        if config:
            return jsonify({
                'success': True,
                'tenant_id': tenant_id,
                'config_type': config_type,
                'config_data': config
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Configuration not found for {config_type}'
            }), 404

    except Exception as e:
        logger.error(f"Error getting tenant config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tenant/config/<config_type>', methods=['PUT'])
def api_update_tenant_config(config_type):
    """
    Update tenant configuration by type.

    Request body should contain:
    - config_data: The configuration data object

    Returns:
        JSON with success status
    """
    try:
        from tenant_config import get_current_tenant_id, update_tenant_configuration, validate_tenant_configuration

        tenant_id = get_current_tenant_id()
        data = request.get_json()

        if not data or 'config_data' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing config_data in request body'
            }), 400

        config_data = data['config_data']

        # Validate configuration
        is_valid, error_msg = validate_tenant_configuration(config_type, config_data)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': f'Invalid configuration: {error_msg}'
            }), 400

        # Update configuration
        success = update_tenant_configuration(
            tenant_id,
            config_type,
            config_data,
            updated_by=session.get('user_id', 'api_user')
        )

        if success:
            return jsonify({
                'success': True,
                'tenant_id': tenant_id,
                'config_type': config_type,
                'message': 'Configuration updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update configuration'
            }), 500

    except Exception as e:
        logger.error(f"Error updating tenant config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tenant/industries', methods=['GET'])
def api_list_industries():
    """
    Get list of available industry templates.

    Returns:
        JSON with list of industries and their metadata
    """
    try:
        from industry_templates import list_available_industries

        industries = list_available_industries()

        return jsonify({
            'success': True,
            'industries': industries,
            'count': len(industries)
        })

    except Exception as e:
        logger.error(f"Error listing industries: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tenant/industries/<industry_key>/preview', methods=['GET'])
def api_preview_industry_template(industry_key):
    """
    Preview what an industry template will configure.

    Args:
        industry_key: Industry template key

    Returns:
        JSON with preview information
    """
    try:
        from industry_templates import get_template_preview

        preview = get_template_preview(industry_key)

        if preview:
            return jsonify({
                'success': True,
                'industry_key': industry_key,
                'preview': preview
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Industry template not found: {industry_key}'
            }), 404

    except Exception as e:
        logger.error(f"Error previewing industry template: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tenant/industries/<industry_key>/apply', methods=['POST'])
def api_apply_industry_template(industry_key):
    """
    Apply an industry template to the current tenant.

    Request body (optional):
    - company_name: Company name to customize entity names

    Returns:
        JSON with success status
    """
    try:
        from industry_templates import apply_industry_template
        from tenant_config import get_current_tenant_id, clear_tenant_config_cache

        tenant_id = get_current_tenant_id()
        data = request.get_json() or {}
        company_name = data.get('company_name')

        success = apply_industry_template(tenant_id, industry_key, company_name)

        if success:
            # Clear cache so new config is loaded
            clear_tenant_config_cache(tenant_id)

            return jsonify({
                'success': True,
                'tenant_id': tenant_id,
                'industry_key': industry_key,
                'message': f'Successfully applied {industry_key} template'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to apply industry template'
            }), 500

    except Exception as e:
        logger.error(f"Error applying industry template: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tenant/config/export', methods=['GET'])
def api_export_tenant_config():
    """
    Export all tenant configurations as JSON for backup/sharing.

    Returns:
        JSON with all tenant configurations
    """
    try:
        from tenant_config import (
            get_current_tenant_id,
            get_tenant_configuration
        )

        tenant_id = get_current_tenant_id()

        # Export all configuration types
        config_types = ['entities', 'business_context', 'accounting_categories', 'pattern_matching_rules']
        export_data = {
            'tenant_id': tenant_id,
            'export_date': datetime.now().isoformat(),
            'configurations': {}
        }

        for config_type in config_types:
            config = get_tenant_configuration(tenant_id, config_type)
            if config:
                export_data['configurations'][config_type] = config

        return jsonify({
            'success': True,
            'export_data': export_data
        })

    except Exception as e:
        logger.error(f"Error exporting tenant config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tenant/config/import', methods=['POST'])
def api_import_tenant_config():
    """
    Import tenant configurations from JSON export.

    Request body should contain:
    - import_data: The exported configuration data

    Returns:
        JSON with success status and import details
    """
    try:
        from tenant_config import (
            get_current_tenant_id,
            update_tenant_configuration,
            clear_tenant_config_cache
        )

        tenant_id = get_current_tenant_id()
        data = request.get_json()

        if not data or 'import_data' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing import_data in request body'
            }), 400

        import_data = data['import_data']
        configurations = import_data.get('configurations', {})

        if not configurations:
            return jsonify({
                'success': False,
                'error': 'No configurations found in import data'
            }), 400

        # Import each configuration type
        imported_count = 0
        for config_type, config_data in configurations.items():
            success = update_tenant_configuration(
                tenant_id,
                config_type,
                config_data,
                updated_by=session.get('user_id', 'import')
            )
            if success:
                imported_count += 1

        # Clear cache
        clear_tenant_config_cache(tenant_id)

        return jsonify({
            'success': True,
            'tenant_id': tenant_id,
            'imported_count': imported_count,
            'total_configurations': len(configurations),
            'message': f'Successfully imported {imported_count} configurations'
        })

    except Exception as e:
        logger.error(f"Error importing tenant config: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chatbot', methods=['POST'])
def api_chatbot():
    """API endpoint for AI CFO Assistant chatbot"""
    try:
        from chatbot_context import get_chatbot_context
        from database import db_manager

        # Get request data
        data = request.json
        message = data.get('message', '').strip()
        history = data.get('history', [])

        if not message:
            return jsonify({'error': 'Message parameter required'}), 400

        # Check if Claude client is initialized
        if not claude_client:
            return jsonify({
                'error': 'AI service unavailable',
                'response': 'I apologize, but the AI service is currently unavailable. Please try again later.'
            }), 503

        # Get current tenant ID
        tenant_id = get_current_tenant_id()

        # Build context for this tenant
        context_builder = get_chatbot_context(db_manager, tenant_id)

        # Build system prompt with full context
        system_prompt = context_builder.build_system_prompt()

        # Format conversation history
        formatted_history = context_builder.format_conversation_history(history)

        # Add current message to history
        messages = formatted_history + [
            {
                'role': 'user',
                'content': message
            }
        ]

        # Call Claude API
        logger.info(f"Chatbot request for tenant {tenant_id}: {message[:50]}...")

        response = claude_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )

        # Extract response text
        assistant_message = response.content[0].text

        logger.info(f"Chatbot response length: {len(assistant_message)} chars")

        return jsonify({
            'response': assistant_message,
            'tenant_id': tenant_id
        })

    except Exception as e:
        logger.error(f"Chatbot API error: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'response': 'I apologize, but I encountered an error processing your request. Please try again.'
        }), 500


if __name__ == '__main__':
    print("Starting Delta CFO Agent Web Interface (Database Mode)")
    print("Database backend enabled")

    # Initialize Claude API
    init_claude_client()

    # Initialize invoice tables
    init_invoice_tables()

    # Initialize currency converter
    init_currency_converter()

    # Ensure background jobs tables exist
    ensure_background_jobs_tables()

    # Register authentication blueprints (lazy loading)
    if not auth_blueprints_registered:
        if register_auth_blueprints():
            auth_blueprints_registered = True
            print("[OK] Authentication blueprints registered")
        else:
            print("[WARNING] Authentication blueprints not available")

    # Get port from environment (Cloud Run sets PORT automatically)
    port = int(os.environ.get('PORT', 5001))

    print(f"Starting server on port {port}")
    print("Invoice processing module integrated")
    print("[NEW] Blockchain enrichment API enabled")
    print(f"Debug mode: {'ON' if debug_mode else 'OFF'}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

# Initialize Claude client and database on module import (for production deployments like Cloud Run)
# Optimized for Cloud Run startup - lazy initialization to avoid timeouts
try:
    if not claude_client:
        init_claude_client()

    # Register authentication blueprints in production mode
    if not auth_blueprints_registered:
        if register_auth_blueprints():
            auth_blueprints_registered = True
            print("[OK] Authentication blueprints registered for production")

    # Defer heavy database operations to first request to avoid startup timeout
    print("[OK] Basic production initialization completed - database ops deferred")
except Exception as e:
    print(f"WARNING: Production initialization warning: {e}")

