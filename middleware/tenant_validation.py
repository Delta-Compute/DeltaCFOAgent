"""
Tenant Validation Middleware

Provides decorators for validating tenant context is properly set.
Prevents data leakage by ensuring all API requests have explicit tenant context.
"""

import logging
from functools import wraps
from typing import Optional
from flask import request, jsonify, g

logger = logging.getLogger(__name__)


def require_tenant_context(f):
    """
    Decorator that validates tenant context is set for the current request.

    This should be used AFTER @require_auth decorator to ensure the user
    has an active tenant context set.

    Usage:
        @app.route('/api/protected-endpoint')
        @require_auth
        @require_tenant_context
        def protected_endpoint():
            tenant = get_current_tenant()
            # Process request with tenant context

    Returns:
        400 error if no tenant context is set
        Proceeds with request if tenant context exists
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from middleware.auth_middleware import get_current_tenant, get_current_user

        # Get current tenant from g (should be set by require_auth)
        tenant = get_current_tenant()

        if not tenant:
            # Get user info for logging
            user = get_current_user()
            user_email = user.get('email') if user else 'anonymous'

            logger.error(
                f"[TENANT_VALIDATION] Tenant context missing | "
                f"Endpoint: {request.method} {request.path} | "
                f"User: {user_email}"
            )

            return jsonify({
                'success': False,
                'error': 'tenant_context_required',
                'message': (
                    'No tenant context available. '
                    'Please select a tenant or complete onboarding to create one.'
                )
            }), 400

        # Log successful tenant context for audit trail
        logger.info(
            f"[TENANT_VALIDATION] Request authorized | "
            f"Endpoint: {request.method} {request.path} | "
            f"Tenant: {tenant.get('id')} ({tenant.get('company_name', 'Unknown')})"
        )

        return f(*args, **kwargs)

    return decorated_function


def optional_tenant_context(f):
    """
    Decorator for routes that work with or without tenant context.

    Unlike require_tenant_context, this will NOT error if tenant is missing,
    but it will log a warning. Useful for transitional endpoints or endpoints
    that can work in both authenticated and unauthenticated modes.

    Usage:
        @app.route('/api/flexible-endpoint')
        @optional_auth
        @optional_tenant_context
        def flexible_endpoint():
            tenant = get_current_tenant()
            if tenant:
                # Tenant-specific logic
            else:
                # General logic
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from middleware.auth_middleware import get_current_tenant, get_current_user

        tenant = get_current_tenant()

        if not tenant:
            user = get_current_user()
            if user:
                # User is authenticated but has no tenant - log warning
                logger.warning(
                    f"[TENANT_VALIDATION] Authenticated user without tenant | "
                    f"Endpoint: {request.method} {request.path} | "
                    f"User: {user.get('email')}"
                )
        else:
            logger.debug(
                f"[TENANT_VALIDATION] Optional tenant context present | "
                f"Endpoint: {request.method} {request.path} | "
                f"Tenant: {tenant.get('id')}"
            )

        return f(*args, **kwargs)

    return decorated_function


def validate_tenant_id_param(f):
    """
    Decorator to validate that tenant_id URL parameter matches user's access.

    Ensures users can only access tenants they have permission for.
    Useful for routes like /api/tenants/<tenant_id>/settings

    Usage:
        @app.route('/api/tenants/<tenant_id>/data')
        @require_auth
        @validate_tenant_id_param
        def get_tenant_data(tenant_id):
            # tenant_id is validated - user has access
            return get_data(tenant_id)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from middleware.auth_middleware import get_current_user

        # Extract tenant_id from URL parameters
        tenant_id = kwargs.get('tenant_id') or request.view_args.get('tenant_id')

        if not tenant_id:
            logger.error(
                f"[TENANT_VALIDATION] No tenant_id in URL parameters | "
                f"Endpoint: {request.method} {request.path}"
            )
            return jsonify({
                'success': False,
                'error': 'tenant_id_required',
                'message': 'tenant_id parameter is required'
            }), 400

        # Check if user has access to this tenant
        user = get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'error': 'authentication_required',
                'message': 'Authentication required'
            }), 401

        # Get user's accessible tenants
        user_tenants = getattr(g, 'user_tenants', [])
        has_access = any(t['id'] == tenant_id for t in user_tenants)

        if not has_access:
            logger.warning(
                f"[TENANT_VALIDATION] Access denied | "
                f"User: {user.get('email')} | "
                f"Attempted tenant: {tenant_id}"
            )
            return jsonify({
                'success': False,
                'error': 'access_denied',
                'message': 'You do not have access to this tenant'
            }), 403

        logger.info(
            f"[TENANT_VALIDATION] Tenant access validated | "
            f"User: {user.get('email')} | "
            f"Tenant: {tenant_id}"
        )

        return f(*args, **kwargs)

    return decorated_function


def log_tenant_context(label: str = "") -> Optional[dict]:
    """
    Helper function to log current tenant context for debugging.

    Args:
        label: Optional label to identify the calling location

    Returns:
        Current tenant dict or None
    """
    from middleware.auth_middleware import get_current_tenant, get_current_user

    tenant = get_current_tenant()
    user = get_current_user()

    log_msg = f"[TENANT_DEBUG] {label} | "

    if user:
        log_msg += f"User: {user.get('email')} | "
    else:
        log_msg += "User: None | "

    if tenant:
        log_msg += f"Tenant: {tenant.get('id')} ({tenant.get('company_name', 'Unknown')})"
    else:
        log_msg += "Tenant: None"

    logger.debug(log_msg)

    return tenant
