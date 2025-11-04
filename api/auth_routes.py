"""
Authentication API Routes

Provides REST API endpoints for user authentication, registration, and session management.
"""

import logging
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from auth.firebase_config import create_firebase_user, verify_firebase_token
from middleware.auth_middleware import require_auth, get_current_user, get_current_tenant
# Import from root services module (not web_ui/services)
from services.email_service import send_invitation_email, send_welcome_email
from web_ui.database import db_manager
from web_ui.tenant_context import set_tenant_id

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user (self-registration for Fractional CFO or Tenant Admin only).

    Request Body:
        {
            "email": "user@example.com",
            "password": "password123",
            "display_name": "John Doe",
            "user_type": "fractional_cfo" | "tenant_admin"
        }

    Returns:
        {
            "success": true,
            "user": {...},
            "message": "Registration successful"
        }
    """
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['email', 'password', 'display_name', 'user_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': 'missing_field',
                    'message': f'Missing required field: {field}'
                }), 400

        email = data['email']
        password = data['password']
        display_name = data['display_name']
        user_type = data['user_type']

        # Validate user type (only fractional_cfo and tenant_admin can self-register)
        if user_type not in ['fractional_cfo', 'tenant_admin']:
            return jsonify({
                'success': False,
                'error': 'invalid_user_type',
                'message': 'Only fractional_cfo and tenant_admin can self-register'
            }), 400

        # Create Firebase user
        firebase_user = create_firebase_user(email, password, display_name)

        if not firebase_user:
            return jsonify({
                'success': False,
                'error': 'firebase_error',
                'message': 'Failed to create Firebase user. Email may already be in use.'
            }), 400

        # Create user in database
        user_id = str(uuid.uuid4())
        query = """
            INSERT INTO users (id, firebase_uid, email, display_name, user_type, is_active, email_verified)
            VALUES (%s, %s, %s, %s, %s, true, false)
            RETURNING id, firebase_uid, email, display_name, user_type, is_active
        """

        try:
            result = db_manager.execute_query(
                query,
                (user_id, firebase_user['uid'], email, display_name, user_type),
                fetch_one=True
            )

            if not result:
                # Rollback Firebase user if database insert fails
                from auth.firebase_config import delete_firebase_user
                delete_firebase_user(firebase_user['uid'])
                return jsonify({
                    'success': False,
                    'error': 'database_error',
                    'message': 'Failed to create user in database'
                }), 500
        except Exception as db_error:
            # Rollback Firebase user if database error occurs
            from auth.firebase_config import delete_firebase_user
            logger.error(f"Database error during registration: {db_error}")
            delete_firebase_user(firebase_user['uid'])
            return jsonify({
                'success': False,
                'error': 'database_error',
                'message': f'Failed to create user in database: {str(db_error)}'
            }), 500

        user = {
            'id': result['id'],
            'firebase_uid': result['firebase_uid'],
            'email': result['email'],
            'display_name': result['display_name'],
            'user_type': result['user_type'],
            'is_active': result['is_active']
        }

        logger.info(f"User registered successfully: {email} ({user_type})")

        # Send welcome email
        try:
            send_welcome_email(email, display_name, "Delta CFO Agent")
        except Exception as e:
            logger.warning(f"Failed to send welcome email to {email}: {e}")

        return jsonify({
            'success': True,
            'user': user,
            'message': 'Registration successful. Please verify your email.'
        }), 201

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred during registration'
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login with Firebase ID token.

    Request Body:
        {
            "id_token": "firebase_id_token"
        }

    Returns:
        {
            "success": true,
            "user": {...},
            "tenants": [...],
            "current_tenant": {...}
        }
    """
    try:
        data = request.get_json()
        id_token = data.get('id_token')

        if not id_token:
            return jsonify({
                'success': False,
                'error': 'missing_token',
                'message': 'ID token is required'
            }), 400

        # Verify Firebase token
        decoded_token = verify_firebase_token(id_token)

        if not decoded_token:
            return jsonify({
                'success': False,
                'error': 'invalid_token',
                'message': 'Invalid or expired token'
            }), 401

        firebase_uid = decoded_token.get('uid')

        # Get user from database
        query = """
            SELECT id, firebase_uid, email, display_name, user_type, is_active
            FROM users
            WHERE firebase_uid = %s
        """
        result = db_manager.execute_query(query, (firebase_uid,), fetch_one=True)

        if not result:
            return jsonify({
                'success': False,
                'error': 'user_not_found',
                'message': 'User not found. Please complete registration.'
            }), 404

        user_data = result

        if not user_data['is_active']:
            return jsonify({
                'success': False,
                'error': 'user_inactive',
                'message': 'User account is inactive'
            }), 403

        user = {
            'id': user_data['id'],
            'firebase_uid': user_data['firebase_uid'],
            'email': user_data['email'],
            'display_name': user_data['display_name'],
            'user_type': user_data['user_type'],
            'is_active': user_data['is_active']
        }

        # Update last login time
        update_query = "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %s"
        db_manager.execute_query(update_query, (user['id'],))

        # Get user's tenants
        tenants_query = """
            SELECT
                tc.id as tenant_id,
                tc.company_name,
                tc.description as company_description,
                tu.role,
                tu.permissions
            FROM tenant_users tu
            JOIN tenant_configuration tc ON tu.tenant_id = tc.id
            WHERE tu.user_id = %s AND tu.is_active = true
        """
        tenant_results = db_manager.execute_query(tenants_query, (user['id'],), fetch_all=True)

        tenants = []
        for t in (tenant_results or []):
            tenants.append({
                'id': t['tenant_id'],
                'company_name': t['company_name'],
                'description': t['company_description'],
                'role': t['role'],
                'permissions': t['permissions']
            })

        # Set session data
        session['user_id'] = user['id']
        session['firebase_uid'] = user['firebase_uid']

        # Set current tenant (first tenant or previously selected)
        current_tenant = None
        if tenants:
            current_tenant_id = session.get('current_tenant_id')
            if current_tenant_id:
                current_tenant = next((t for t in tenants if t['id'] == current_tenant_id), tenants[0])
            else:
                current_tenant = tenants[0]
                session['current_tenant_id'] = current_tenant['id']

            # Sync with tenant_context.py session key
            from web_ui.tenant_context import set_tenant_id
            set_tenant_id(current_tenant['id'])

        logger.info(f"User logged in successfully: {user['email']}")

        return jsonify({
            'success': True,
            'user': user,
            'tenants': tenants,
            'current_tenant': current_tenant
        }), 200

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred during login'
        }), 500


@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """
    Logout current user.

    Returns:
        {
            "success": true,
            "message": "Logged out successfully"
        }
    """
    try:
        user = get_current_user()

        # Clear session
        session.clear()

        logger.info(f"User logged out: {user.get('email', 'unknown')}")

        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred during logout'
        }), 500


@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_me():
    """
    Get current authenticated user information.

    Returns:
        {
            "success": true,
            "user": {...},
            "tenants": [...],
            "current_tenant": {...}
        }
    """
    try:
        user = get_current_user()
        current_tenant = get_current_tenant()

        # Get user's tenants
        tenants_query = """
            SELECT
                tc.id as tenant_id,
                tc.company_name,
                tc.description as company_description,
                tu.role,
                tu.permissions
            FROM tenant_users tu
            JOIN tenant_configuration tc ON tu.tenant_id = tc.id
            WHERE tu.user_id = %s AND tu.is_active = true
        """
        tenant_results = db_manager.execute_query(tenants_query, (user['id'],), fetch_all=True)

        tenants = []
        for t in (tenant_results or []):
            tenants.append({
                'id': t['tenant_id'],
                'company_name': t['company_name'],
                'description': t['company_description'],
                'role': t['role'],
                'permissions': t['permissions']
            })

        return jsonify({
            'success': True,
            'user': user,
            'tenants': tenants,
            'current_tenant': current_tenant
        }), 200

    except Exception as e:
        logger.error(f"Get me error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred'
        }), 500


@auth_bp.route('/accept-invitation/<invitation_token>', methods=['POST'])
def accept_invitation(invitation_token):
    """
    Accept an email invitation and create user account.

    Request Body:
        {
            "password": "password123",
            "display_name": "John Doe" (optional if user exists)
        }

    Returns:
        {
            "success": true,
            "user": {...},
            "tenant": {...},
            "message": "Invitation accepted successfully"
        }
    """
    try:
        data = request.get_json() or {}

        # Find invitation
        invitation_query = """
            SELECT id, email, invited_by_user_id, tenant_id, user_type, role, status, expires_at
            FROM user_invitations
            WHERE invitation_token = %s
        """
        result = db_manager.execute_query(invitation_query, (invitation_token,))

        if not result or len(result) == 0:
            return jsonify({
                'success': False,
                'error': 'invitation_not_found',
                'message': 'Invitation not found'
            }), 404

        invitation = result[0]
        invitation_id = invitation[0]
        email = invitation[1]
        invited_by_user_id = invitation[2]
        tenant_id = invitation[3]
        user_type = invitation[4]
        role = invitation[5]
        status = invitation[6]
        expires_at = invitation[7]

        # Check invitation status
        if status != 'pending':
            return jsonify({
                'success': False,
                'error': 'invitation_invalid',
                'message': f'Invitation is {status}'
            }), 400

        # Check expiry
        if expires_at < datetime.now():
            # Mark as expired
            db_manager.execute_query(
                "UPDATE user_invitations SET status = 'expired' WHERE id = %s",
                (invitation_id,)
            )
            return jsonify({
                'success': False,
                'error': 'invitation_expired',
                'message': 'Invitation has expired'
            }), 400

        # Check if user already exists
        user_query = "SELECT id, firebase_uid, display_name FROM users WHERE email = %s"
        user_result = db_manager.execute_query(user_query, (email,))

        if user_result and len(user_result) > 0:
            # User exists - just link to tenant
            user_id = user_result[0][0]
            firebase_uid = user_result[0][1]
            display_name = user_result[0][2]
        else:
            # Create new user
            password = data.get('password')
            display_name = data.get('display_name')

            if not password or not display_name:
                return jsonify({
                    'success': False,
                    'error': 'missing_fields',
                    'message': 'Password and display_name required for new users'
                }), 400

            # Create Firebase user
            firebase_user = create_firebase_user(email, password, display_name)

            if not firebase_user:
                return jsonify({
                    'success': False,
                    'error': 'firebase_error',
                    'message': 'Failed to create Firebase user'
                }), 400

            # Create user in database
            user_id = str(uuid.uuid4())
            create_user_query = """
                INSERT INTO users (id, firebase_uid, email, display_name, user_type, is_active, invited_by_user_id)
                VALUES (%s, %s, %s, %s, %s, true, %s)
            """
            db_manager.execute_query(
                create_user_query,
                (user_id, firebase_user['uid'], email, display_name, user_type, invited_by_user_id)
            )
            firebase_uid = firebase_user['uid']

        # Link user to tenant
        tenant_user_id = str(uuid.uuid4())
        link_query = """
            INSERT INTO tenant_users (id, user_id, tenant_id, role, permissions, is_active, added_by_user_id)
            VALUES (%s, %s, %s, %s, %s, true, %s)
            ON CONFLICT (user_id, tenant_id) DO NOTHING
        """
        db_manager.execute_query(
            link_query,
            (tenant_user_id, user_id, tenant_id, role, '{}', invited_by_user_id)
        )

        # Mark invitation as accepted
        db_manager.execute_query(
            "UPDATE user_invitations SET status = 'accepted', accepted_at = CURRENT_TIMESTAMP, accepted_by_user_id = %s WHERE id = %s",
            (user_id, invitation_id)
        )

        # Get tenant info
        tenant_query = "SELECT id, company_name, description FROM tenant_configuration WHERE id = %s"
        tenant_result = db_manager.execute_query(tenant_query, (tenant_id,))

        tenant = {
            'id': tenant_result[0][0],
            'company_name': tenant_result[0][1],
            'description': tenant_result[0][2],
            'role': role
        } if tenant_result else None

        logger.info(f"Invitation accepted: {email} joined {tenant['company_name']}")

        # Send welcome email
        try:
            send_welcome_email(email, display_name, tenant['company_name'])
        except Exception as e:
            logger.warning(f"Failed to send welcome email: {e}")

        return jsonify({
            'success': True,
            'user': {
                'id': user_id,
                'email': email,
                'display_name': display_name,
                'user_type': user_type
            },
            'tenant': tenant,
            'message': 'Invitation accepted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Accept invitation error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while accepting invitation'
        }), 500


@auth_bp.route('/switch-tenant/<tenant_id>', methods=['POST'])
@require_auth
def switch_tenant(tenant_id):
    """
    Switch active tenant for current user.

    Returns:
        {
            "success": true,
            "tenant": {...},
            "message": "Switched to tenant successfully"
        }
    """
    try:
        user = get_current_user()

        # Check if user has access to this tenant
        query = """
            SELECT
                tc.id,
                tc.company_name,
                tc.description,
                tu.role,
                tu.permissions
            FROM tenant_users tu
            JOIN tenant_configuration tc ON tu.tenant_id = tc.id
            WHERE tu.user_id = %s AND tu.tenant_id = %s AND tu.is_active = true
        """
        result = db_manager.execute_query(query, (user['id'], tenant_id), fetch_one=True)

        if not result:
            return jsonify({
                'success': False,
                'error': 'access_denied',
                'message': 'You do not have access to this tenant'
            }), 403

        tenant = {
            'id': result['tenant_id'],
            'company_name': result['company_name'],
            'description': result['company_description'],
            'role': result['role'],
            'permissions': result['permissions']
        }

        # Update session using both tenant_context module and session key
        # This ensures compatibility with both tenant_context.py and auth_middleware.py
        set_tenant_id(tenant_id)
        session['current_tenant_id'] = tenant_id

        logger.info(f"User {user['email']} switched to tenant {tenant['company_name']}")

        return jsonify({
            'success': True,
            'tenant': tenant,
            'message': 'Switched to tenant successfully'
        }), 200

    except Exception as e:
        logger.error(f"Switch tenant error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while switching tenant'
        }), 500


@auth_bp.route('/verify-invitation/<invitation_token>', methods=['GET'])
def verify_invitation(invitation_token):
    """
    Verify invitation token and get invitation details (without accepting).

    Returns:
        {
            "success": true,
            "invitation": {...}
        }
    """
    try:
        query = """
            SELECT
                ui.email,
                ui.user_type,
                ui.role,
                ui.status,
                ui.expires_at,
                tc.company_name,
                u.display_name as invited_by_name
            FROM user_invitations ui
            JOIN tenant_configuration tc ON ui.tenant_id = tc.id
            JOIN users u ON ui.invited_by_user_id = u.id
            WHERE ui.invitation_token = %s
        """
        result = db_manager.execute_query(query, (invitation_token,))

        if not result or len(result) == 0:
            return jsonify({
                'success': False,
                'error': 'invitation_not_found',
                'message': 'Invitation not found'
            }), 404

        inv = result[0]
        invitation = {
            'email': inv[0],
            'user_type': inv[1],
            'role': inv[2],
            'status': inv[3],
            'expires_at': inv[4].isoformat() if inv[4] else None,
            'company_name': inv[5],
            'invited_by_name': inv[6],
            'is_expired': inv[4] < datetime.now() if inv[4] else False
        }

        return jsonify({
            'success': True,
            'invitation': invitation
        }), 200

    except Exception as e:
        logger.error(f"Verify invitation error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred'
        }), 500
