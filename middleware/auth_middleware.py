"""
Authentication Middleware

Provides decorators and helper functions for protecting Flask routes and
managing user authentication and authorization.
"""

import logging
from functools import wraps
from typing import Optional, Dict, Any, List
from flask import request, jsonify, session, g
from auth.firebase_config import verify_firebase_token, verify_session_cookie

logger = logging.getLogger(__name__)


def get_token_from_request() -> Optional[str]:
    """
    Extract Firebase ID token from request headers or session.

    Looks for token in:
    1. Authorization header (Bearer token)
    2. Session cookie
    3. Custom X-Firebase-Token header

    Returns:
        Token string if found, None otherwise
    """
    # Check Authorization header
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split('Bearer ')[1]

    # Check custom Firebase token header
    firebase_token = request.headers.get('X-Firebase-Token')
    if firebase_token:
        return firebase_token

    # Check session for session cookie
    session_cookie = session.get('session_cookie')
    if session_cookie:
        return session_cookie

    return None


def get_current_user_from_db(firebase_uid: str) -> Optional[Dict[str, Any]]:
    """
    Fetch user from database by Firebase UID.

    Args:
        firebase_uid: Firebase user UID

    Returns:
        User dict if found, None otherwise
    """
    try:
        from web_ui.database import db_manager

        query = """
            SELECT id, firebase_uid, email, display_name, user_type, is_active
            FROM users
            WHERE firebase_uid = %s AND is_active = true
        """
        result = db_manager.execute_query(query, (firebase_uid,), fetch_one=True)

        if result:
            return {
                'id': result['id'],
                'firebase_uid': result['firebase_uid'],
                'email': result['email'],
                'display_name': result['display_name'],
                'user_type': result['user_type'],
                'is_active': result['is_active']
            }
        return None

    except Exception as e:
        logger.error(f"Error fetching user from database: {e}")
        return None


def get_user_tenants(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all tenants that a user has access to.

    Args:
        user_id: User ID from database

    Returns:
        List of tenant dicts with role information
    """
    try:
        from web_ui.database import db_manager

        query = """
            SELECT
                tc.tenant_id,
                tc.company_name,
                tc.company_description,
                tu.role,
                tu.permissions,
                tu.is_active
            FROM tenant_users tu
            JOIN tenant_configuration tc ON tu.tenant_id = tc.tenant_id
            WHERE tu.user_id = %s AND tu.is_active = true
        """
        results = db_manager.execute_query(query, (user_id,), fetch_all=True)

        tenants = []
        if results:
            for row in results:
                tenants.append({
                    'id': row['tenant_id'],
                    'company_name': row['company_name'],
                    'description': row.get('company_description', ''),
                    'role': row['role'],
                    'permissions': row['permissions'],
                    'is_active': row['is_active']
                })

        return tenants

    except Exception as e:
        logger.error(f"Error fetching user tenants: {e}")
        return []


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get the current authenticated user from Flask's g object.

    Returns:
        User dict if authenticated, None otherwise
    """
    return getattr(g, 'current_user', None)


def get_current_tenant() -> Optional[Dict[str, Any]]:
    """
    Get the current active tenant from Flask's g object.

    Returns:
        Tenant dict if set, None otherwise
    """
    return getattr(g, 'current_tenant', None)


def set_current_user(user: Dict[str, Any]):
    """
    Set the current user in Flask's g object.

    Args:
        user: User dict to set as current user
    """
    g.current_user = user


def set_current_tenant(tenant: Dict[str, Any]):
    """
    Set the current active tenant in Flask's g object.

    Args:
        tenant: Tenant dict to set as current tenant
    """
    g.current_tenant = tenant


def require_auth(f):
    """
    Decorator to require Firebase authentication for a route.

    Usage:
        @app.route('/protected')
        @require_auth
        def protected_route():
            user = get_current_user()
            return jsonify(user)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Extract token from request
        token = get_token_from_request()

        if not token:
            logger.warning("No authentication token provided")
            return jsonify({
                'success': False,
                'error': 'authentication_required',
                'message': 'Authentication token is required'
            }), 401

        # Verify Firebase token
        decoded_token = verify_firebase_token(token)

        if not decoded_token:
            logger.warning("Invalid or expired authentication token")
            return jsonify({
                'success': False,
                'error': 'invalid_token',
                'message': 'Invalid or expired authentication token'
            }), 401

        # Get user from database
        firebase_uid = decoded_token.get('uid')
        user = get_current_user_from_db(firebase_uid)

        if not user:
            logger.warning(f"User not found in database for Firebase UID: {firebase_uid}")
            return jsonify({
                'success': False,
                'error': 'user_not_found',
                'message': 'User not found in system. Please complete registration.'
            }), 404

        # Set current user in Flask g object
        set_current_user(user)

        # Get user's tenants
        tenants = get_user_tenants(user['id'])
        g.user_tenants = tenants

        # Set current tenant from session or default to first tenant
        from web_ui.tenant_context import get_current_tenant_id, set_tenant_id
        current_tenant_id = get_current_tenant_id()

        if current_tenant_id and current_tenant_id != 'delta':
            # Find tenant in user's tenants
            current_tenant = next((t for t in tenants if t['id'] == current_tenant_id), None)
            if current_tenant:
                # User has access to session tenant - use it
                set_current_tenant(current_tenant)
            else:
                # Session tenant not in user's list - reset to first tenant
                if tenants:
                    set_current_tenant(tenants[0])
                    set_tenant_id(tenants[0]['id'])
        elif tenants:
            # No session tenant - default to first tenant
            set_current_tenant(tenants[0])
            set_tenant_id(tenants[0]['id'])

        return f(*args, **kwargs)

    return decorated_function


def require_role(roles: List[str]):
    """
    Decorator to require specific role(s) for a route.

    Args:
        roles: List of allowed roles (e.g., ['owner', 'admin', 'cfo'])

    Usage:
        @app.route('/admin-only')
        @require_auth
        @require_role(['owner', 'admin'])
        def admin_route():
            return 'Admin access granted'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            tenant = get_current_tenant()

            if not user or not tenant:
                logger.warning("No authenticated user or tenant context")
                return jsonify({
                    'success': False,
                    'error': 'authorization_required',
                    'message': 'Authorization required'
                }), 403

            user_role = tenant.get('role')
            if user_role not in roles:
                logger.warning(f"User role '{user_role}' not in required roles: {roles}")
                return jsonify({
                    'success': False,
                    'error': 'insufficient_permissions',
                    'message': f'This action requires one of the following roles: {", ".join(roles)}'
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_permission(permission: str):
    """
    Decorator to require a specific permission for a route.

    Args:
        permission: Required permission key (e.g., 'users.manage', 'transactions.edit')

    Usage:
        @app.route('/manage-users')
        @require_auth
        @require_permission('users.manage')
        def manage_users():
            return 'User management access granted'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            tenant = get_current_tenant()

            if not user or not tenant:
                logger.warning("No authenticated user or tenant context")
                return jsonify({
                    'success': False,
                    'error': 'authorization_required',
                    'message': 'Authorization required'
                }), 403

            # Check if user has permission
            user_permissions = tenant.get('permissions', {})

            # Owner and admin roles have all permissions
            if tenant.get('role') in ['owner', 'admin']:
                return f(*args, **kwargs)

            # Check specific permission
            if isinstance(user_permissions, dict):
                if permission not in user_permissions or not user_permissions.get(permission):
                    logger.warning(f"User lacks required permission: {permission}")
                    return jsonify({
                        'success': False,
                        'error': 'insufficient_permissions',
                        'message': f'This action requires the permission: {permission}'
                    }), 403
            else:
                # If permissions is not a dict, deny access
                logger.warning(f"Invalid permissions format for user")
                return jsonify({
                    'success': False,
                    'error': 'insufficient_permissions',
                    'message': 'Insufficient permissions'
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_user_type(user_types: List[str]):
    """
    Decorator to require specific user type(s) for a route.

    Args:
        user_types: List of allowed user types (e.g., ['fractional_cfo', 'tenant_admin'])

    Usage:
        @app.route('/cfo-only')
        @require_auth
        @require_user_type(['fractional_cfo'])
        def cfo_route():
            return 'CFO access granted'
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()

            if not user:
                logger.warning("No authenticated user")
                return jsonify({
                    'success': False,
                    'error': 'authorization_required',
                    'message': 'Authorization required'
                }), 403

            user_type = user.get('user_type')
            if user_type not in user_types:
                logger.warning(f"User type '{user_type}' not in required types: {user_types}")
                return jsonify({
                    'success': False,
                    'error': 'insufficient_permissions',
                    'message': f'This action requires one of the following user types: {", ".join(user_types)}'
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_tenant_access(f):
    """
    Decorator to ensure user has access to the requested tenant.

    Validates that the tenant_id in URL parameters belongs to the current user.

    Usage:
        @app.route('/api/tenants/<tenant_id>/settings')
        @require_auth
        @require_tenant_access
        def tenant_settings(tenant_id):
            return 'Access granted to tenant settings'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        tenant_id = kwargs.get('tenant_id') or request.view_args.get('tenant_id')

        if not user or not tenant_id:
            logger.warning("Missing user or tenant_id")
            return jsonify({
                'success': False,
                'error': 'authorization_required',
                'message': 'Authorization required'
            }), 403

        # Check if user has access to this tenant
        user_tenants = getattr(g, 'user_tenants', [])
        has_access = any(t['id'] == tenant_id for t in user_tenants)

        if not has_access:
            logger.warning(f"User {user['id']} does not have access to tenant {tenant_id}")
            return jsonify({
                'success': False,
                'error': 'access_denied',
                'message': 'You do not have access to this tenant'
            }), 403

        return f(*args, **kwargs)

    return decorated_function


def optional_auth(f):
    """
    Decorator for routes that work with or without authentication.

    If user is authenticated, sets current_user in g object.
    If not authenticated, continues without error.

    Usage:
        @app.route('/public-or-private')
        @optional_auth
        def flexible_route():
            user = get_current_user()
            if user:
                return 'Authenticated content'
            return 'Public content'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_token_from_request()

        if token:
            decoded_token = verify_firebase_token(token)
            if decoded_token:
                firebase_uid = decoded_token.get('uid')
                user = get_current_user_from_db(firebase_uid)
                if user:
                    set_current_user(user)
                    tenants = get_user_tenants(user['id'])
                    g.user_tenants = tenants

                    if tenants:
                        current_tenant_id = session.get('current_tenant_id')
                        current_tenant = next((t for t in tenants if t['id'] == current_tenant_id), tenants[0])
                        set_current_tenant(current_tenant)

        return f(*args, **kwargs)

    return decorated_function