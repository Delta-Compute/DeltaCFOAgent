#!/usr/bin/env python3
"""
Tenant Context Manager for Multi-Tenant SaaS
Handles tenant identification and session management
"""

from flask import session, g, request
from functools import wraps
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# DEPRECATED: Default tenant removed for security
# Previously: DEFAULT_TENANT_ID = 'delta'
# Now: Tenant context must be explicitly set via authentication or headers
# This prevents accidental data leakage between tenants

def get_current_tenant_id(strict: bool = False) -> Optional[str]:
    """
    Get the current tenant ID from session or context.

    Priority:
    1. Flask g object (set per request by middleware)
    2. Flask session (persists across requests)
    3. Request header (X-Tenant-ID for API calls)

    Args:
        strict: If True, raises ValueError when no tenant context exists.
                If False, returns None (for backward compatibility during migration).
                Default: False (will become True in future versions)

    Returns:
        str: Tenant ID if found
        None: If no tenant context and strict=False

    Raises:
        ValueError: If strict=True and no tenant context exists

    Security Note:
        In production, all authenticated endpoints should have tenant context.
        Missing tenant context indicates a configuration error or security issue.
    """
    try:
        # Check Flask g object first (set per request by auth middleware)
        if hasattr(g, 'tenant_id') and g.tenant_id:
            return g.tenant_id

        # Check session (persists across requests)
        if 'tenant_id' in session and session['tenant_id']:
            tenant_id = session['tenant_id']
            g.tenant_id = tenant_id  # Cache in g for this request
            return tenant_id

        # Check request header for API calls
        if request:
            tenant_id = request.headers.get('X-Tenant-ID')
            if tenant_id:
                g.tenant_id = tenant_id
                return tenant_id

        # NO DEFAULT - Tenant context must be explicit
        if strict:
            raise ValueError(
                "Tenant context not set. User must be authenticated with a valid tenant "
                "or X-Tenant-ID header must be provided. This prevents accidental data "
                "leakage between tenants."
            )

        # Non-strict mode for backward compatibility (logs warning)
        logger.warning(
            f"[TENANT_CONTEXT] No tenant context found | "
            f"Endpoint: {request.method if request else 'N/A'} "
            f"{request.path if request else 'N/A'} | "
            f"This should be fixed - all authenticated requests need tenant context"
        )
        return None

    except RuntimeError:
        # Outside of Flask application context
        if strict:
            raise ValueError(
                "Cannot get tenant context outside of Flask application context"
            )
        logger.warning("[TENANT_CONTEXT] Called outside Flask context")
        return None

def set_tenant_id(tenant_id: str):
    """
    Set the current tenant ID in session

    Args:
        tenant_id: Tenant identifier
    """
    session['tenant_id'] = tenant_id
    g.tenant_id = tenant_id
    logger.info(f"Tenant context set to: {tenant_id}")

def clear_tenant_id():
    """
    Clear the tenant ID from session (reset to default)
    """
    if 'tenant_id' in session:
        del session['tenant_id']
    if hasattr(g, 'tenant_id'):
        delattr(g, 'tenant_id')
    logger.info("Tenant context cleared (reset to default)")

def require_tenant(f):
    """
    Decorator to ensure tenant_id is set before executing a function

    Usage:
        @app.route('/api/transactions')
        @require_tenant
        def get_transactions():
            tenant_id = get_current_tenant_id()
            # ... query with tenant_id filter
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tenant_id = get_current_tenant_id()

        if not tenant_id:
            return {
                'error': 'Tenant context not set',
                'message': 'Please set tenant_id in session or X-Tenant-ID header'
            }, 400

        logger.debug(f"Request processing for tenant: {tenant_id}")
        return f(*args, **kwargs)

    return decorated_function

def init_tenant_context(app):
    """
    Initialize tenant context for Flask app

    This sets up before_request handlers to ensure tenant_id is always available

    Args:
        app: Flask application instance
    """
    @app.before_request
    def set_tenant_context():
        """
        Before each request, ensure tenant_id is available in g
        """
        tenant_id = get_current_tenant_id()
        g.tenant_id = tenant_id

        # Log tenant context for debugging (only in development)
        if app.debug:
            logger.debug(f"Request: {request.method} {request.path} | Tenant: {tenant_id}")

    @app.after_request
    def add_tenant_header(response):
        """
        Add tenant ID to response headers for debugging
        """
        if hasattr(g, 'tenant_id'):
            response.headers['X-Current-Tenant'] = g.tenant_id
        return response

    logger.info("Tenant context initialized for Flask app")

# Convenience function for database queries
def get_tenant_filter() -> dict:
    """
    Get a dictionary filter for database queries

    Returns:
        dict: {'tenant_id': 'current_tenant'}

    Usage:
        query = "SELECT * FROM transactions WHERE tenant_id = %s AND date = %s"
        tenant_id = get_current_tenant_id()
        results = db.execute(query, (tenant_id, date))
    """
    return {'tenant_id': get_current_tenant_id()}

def build_tenant_query_params(*additional_params):
    """
    Build query parameters tuple starting with tenant_id

    Args:
        *additional_params: Additional query parameters

    Returns:
        tuple: (tenant_id, *additional_params)

    Usage:
        params = build_tenant_query_params(date, amount)
        # Returns: ('delta', '2024-10-14', 100.00)
    """
    return (get_current_tenant_id(),) + additional_params
