"""
Middleware Module

Provides authentication and authorization middleware for Flask routes.
"""

from .auth_middleware import (
    get_token_from_request,
    get_current_user_from_db,
    get_user_tenants,
    get_current_user,
    get_current_tenant,
    set_current_user,
    set_current_tenant,
    require_auth,
    require_role,
    require_permission,
    require_user_type,
    require_tenant_access,
    optional_auth
)

__all__ = [
    'get_token_from_request',
    'get_current_user_from_db',
    'get_user_tenants',
    'get_current_user',
    'get_current_tenant',
    'set_current_user',
    'set_current_tenant',
    'require_auth',
    'require_role',
    'require_permission',
    'require_user_type',
    'require_tenant_access',
    'optional_auth'
]
