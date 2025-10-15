#!/usr/bin/env python3
"""
Tenant Context Manager for Delta CFO Agent
Manages multi-tenant context for the application
"""

import os
from flask import g, request, session
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Default tenant ID for Delta (main company)
DEFAULT_TENANT_ID = 'delta'

def init_tenant_context(app):
    """Initialize tenant context for Flask app"""

    @app.before_request
    def load_tenant_context():
        """Load tenant context before each request"""
        # For now, use default tenant (Delta)
        # In the future, this can be determined from:
        # - Subdomain (tenant.deltacfo.com)
        # - Header (X-Tenant-ID)
        # - URL path (/tenant/dashboard)
        # - Authentication token

        tenant_id = DEFAULT_TENANT_ID

        # Store in Flask's request context
        g.tenant_id = tenant_id

        # Also store in session for consistency
        session['tenant_id'] = tenant_id

        logger.debug(f"Request tenant context set to: {tenant_id}")

def get_current_tenant_id():
    """Get the current tenant ID from request context"""
    # Try to get from Flask's g object first
    if hasattr(g, 'tenant_id'):
        return g.tenant_id

    # Fallback to session
    if 'tenant_id' in session:
        return session['tenant_id']

    # Ultimate fallback to default
    return DEFAULT_TENANT_ID

def set_tenant_id(tenant_id):
    """Set the tenant ID for current request"""
    g.tenant_id = tenant_id
    session['tenant_id'] = tenant_id
    logger.info(f"Tenant context changed to: {tenant_id}")

def require_tenant(tenant_id=None):
    """Decorator to require specific tenant access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_tenant = get_current_tenant_id()

            if tenant_id and current_tenant != tenant_id:
                logger.warning(f"Access denied: Required tenant {tenant_id}, current tenant {current_tenant}")
                return {"error": "Access denied: Invalid tenant"}, 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_tenant_database_config(tenant_id=None):
    """Get database configuration for specific tenant"""
    if not tenant_id:
        tenant_id = get_current_tenant_id()

    # For now, all tenants use the same database with tenant_id filtering
    # In the future, this could return tenant-specific database configs

    return {
        'tenant_id': tenant_id,
        'use_tenant_filtering': True,
        'database_type': 'postgresql'  # All tenants use PostgreSQL
    }

def get_tenant_config(tenant_id=None):
    """Get configuration for specific tenant"""
    if not tenant_id:
        tenant_id = get_current_tenant_id()

    # Default configuration for Delta tenant
    configs = {
        'delta': {
            'name': 'Delta Mining',
            'currency': 'USD',
            'timezone': 'America/New_York',
            'date_format': 'MM/DD/YYYY',
            'features': {
                'crypto_pricing': True,
                'invoice_processing': True,
                'revenue_matching': True,
                'advanced_analytics': True
            }
        }
    }

    return configs.get(tenant_id, configs['delta'])

# Tenant-aware utility functions
def add_tenant_filter_to_query(query, table_alias='t'):
    """Add tenant filter to SQL query"""
    tenant_id = get_current_tenant_id()

    # Add WHERE clause for tenant filtering
    if 'WHERE' in query.upper():
        return query + f" AND {table_alias}.tenant_id = '{tenant_id}'"
    else:
        return query + f" WHERE {table_alias}.tenant_id = '{tenant_id}'"

def get_tenant_table_name(base_table_name, tenant_id=None):
    """Get tenant-specific table name (if using table-per-tenant strategy)"""
    if not tenant_id:
        tenant_id = get_current_tenant_id()

    # For now, using shared tables with tenant_id column
    # In the future, could return tenant-specific table names
    return base_table_name