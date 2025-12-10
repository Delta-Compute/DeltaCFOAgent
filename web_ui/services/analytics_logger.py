"""
Analytics Logger Service

Provides methods for logging user activity, feature usage, errors, and
API performance metrics for the Super Admin Dashboard.
"""

import logging
import hashlib
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from flask import request, g

logger = logging.getLogger(__name__)

# Environment variable to disable tracking (for testing/development)
ANALYTICS_ENABLED = os.environ.get('ANALYTICS_ENABLED', 'true').lower() == 'true'


def _get_db_manager():
    """Lazy import to avoid circular dependencies."""
    from web_ui.database import db_manager
    return db_manager


def _get_current_user_id() -> Optional[str]:
    """Get current user ID from Flask g object."""
    user = getattr(g, 'current_user', None)
    return user.get('id') if user else None


def _get_current_tenant_id() -> Optional[str]:
    """Get current tenant ID from Flask g object."""
    tenant = getattr(g, 'current_tenant', None)
    return tenant.get('id') if tenant else None


def _get_client_ip() -> Optional[str]:
    """Get client IP address from request."""
    if not request:
        return None
    # Check for forwarded headers (behind load balancer)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr


def _get_user_agent() -> Optional[str]:
    """Get user agent from request."""
    if not request:
        return None
    return request.headers.get('User-Agent', '')[:500]  # Limit length


def _hash_token(token: str) -> str:
    """Create SHA-256 hash of session token for audit purposes."""
    return hashlib.sha256(token.encode()).hexdigest()


def log_api_request(
    endpoint: str,
    method: str,
    response_code: int,
    duration_ms: int,
    request_size_bytes: Optional[int] = None,
    response_size_bytes: Optional[int] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None
) -> bool:
    """
    Log an API request for performance and usage analytics.

    Args:
        endpoint: The API endpoint path
        method: HTTP method (GET, POST, etc.)
        response_code: HTTP response status code
        duration_ms: Request duration in milliseconds
        request_size_bytes: Optional request body size
        response_size_bytes: Optional response body size
        user_id: Optional user ID (falls back to current user)
        tenant_id: Optional tenant ID (falls back to current tenant)

    Returns:
        True if logged successfully, False otherwise
    """
    if not ANALYTICS_ENABLED:
        return True

    try:
        db = _get_db_manager()
        query = """
            INSERT INTO api_request_log (
                endpoint, method, user_id, tenant_id, response_code,
                duration_ms, request_size_bytes, response_size_bytes,
                ip_address, user_agent
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        db.execute_query(query, (
            endpoint[:255],
            method[:10],
            user_id or _get_current_user_id(),
            tenant_id or _get_current_tenant_id(),
            response_code,
            duration_ms,
            request_size_bytes,
            response_size_bytes,
            _get_client_ip(),
            _get_user_agent()
        ))
        return True
    except Exception as e:
        logger.error(f"Failed to log API request: {e}")
        return False


def log_page_view(
    page_path: str,
    page_title: Optional[str] = None,
    session_id: Optional[str] = None,
    referrer: Optional[str] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None
) -> bool:
    """
    Log a page view from the frontend.

    Args:
        page_path: The page URL path
        page_title: Optional page title
        session_id: Optional session identifier
        referrer: Optional referrer URL
        user_id: Optional user ID
        tenant_id: Optional tenant ID

    Returns:
        True if logged successfully, False otherwise
    """
    if not ANALYTICS_ENABLED:
        return True

    try:
        db = _get_db_manager()
        query = """
            INSERT INTO page_view_log (
                page_path, page_title, user_id, tenant_id,
                session_id, referrer
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        db.execute_query(query, (
            page_path[:255],
            page_title[:255] if page_title else None,
            user_id or _get_current_user_id(),
            tenant_id or _get_current_tenant_id(),
            session_id[:100] if session_id else None,
            referrer[:500] if referrer else None
        ))
        return True
    except Exception as e:
        logger.error(f"Failed to log page view: {e}")
        return False


def log_feature_usage(
    feature_name: str,
    action: str,
    metadata: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None
) -> bool:
    """
    Log a feature usage event.

    Args:
        feature_name: Name of the feature (e.g., 'file_upload', 'transaction_edit')
        action: Type of action (e.g., 'click', 'submit', 'complete')
        metadata: Optional additional context as JSON
        user_id: Optional user ID
        tenant_id: Optional tenant ID

    Returns:
        True if logged successfully, False otherwise
    """
    if not ANALYTICS_ENABLED:
        return True

    try:
        db = _get_db_manager()
        import json
        query = """
            INSERT INTO feature_usage_log (
                feature_name, action, user_id, tenant_id, metadata
            ) VALUES (%s, %s, %s, %s, %s)
        """
        db.execute_query(query, (
            feature_name[:100],
            action[:50],
            user_id or _get_current_user_id(),
            tenant_id or _get_current_tenant_id(),
            json.dumps(metadata) if metadata else None
        ))
        return True
    except Exception as e:
        logger.error(f"Failed to log feature usage: {e}")
        return False


def log_session_start(
    user_id: str,
    tenant_id: Optional[str] = None,
    session_token: Optional[str] = None
) -> Optional[str]:
    """
    Log start of a user session.

    Args:
        user_id: The user ID
        tenant_id: Optional tenant ID
        session_token: Optional session token (will be hashed)

    Returns:
        Session log ID if successful, None otherwise
    """
    if not ANALYTICS_ENABLED:
        return None

    try:
        db = _get_db_manager()
        query = """
            INSERT INTO user_session_log (
                user_id, tenant_id, login_at, ip_address,
                user_agent, session_token_hash
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        result = db.execute_query(query, (
            user_id,
            tenant_id,
            datetime.utcnow(),
            _get_client_ip(),
            _get_user_agent(),
            _hash_token(session_token) if session_token else None
        ), fetch_one=True)
        return str(result['id']) if result else None
    except Exception as e:
        logger.error(f"Failed to log session start: {e}")
        return None


def log_session_end(session_id: str) -> bool:
    """
    Log end of a user session.

    Args:
        session_id: The session log ID from log_session_start

    Returns:
        True if logged successfully, False otherwise
    """
    if not ANALYTICS_ENABLED:
        return True

    try:
        db = _get_db_manager()
        query = """
            UPDATE user_session_log
            SET logout_at = %s,
                duration_minutes = EXTRACT(EPOCH FROM (%s - login_at)) / 60
            WHERE id = %s AND logout_at IS NULL
        """
        now = datetime.utcnow()
        db.execute_query(query, (now, now, session_id))
        return True
    except Exception as e:
        logger.error(f"Failed to log session end: {e}")
        return False


def log_error(
    error_type: str,
    message: str,
    error_code: Optional[str] = None,
    stack_trace: Optional[str] = None,
    endpoint: Optional[str] = None,
    request_data: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    tenant_id: Optional[str] = None
) -> bool:
    """
    Log an application error.

    Args:
        error_type: Type of error (e.g., 'ValidationError', 'DatabaseError')
        message: Error message
        error_code: Optional error code
        stack_trace: Optional stack trace
        endpoint: Optional API endpoint where error occurred
        request_data: Optional sanitized request data (no sensitive info)
        user_id: Optional user ID
        tenant_id: Optional tenant ID

    Returns:
        True if logged successfully, False otherwise
    """
    if not ANALYTICS_ENABLED:
        return True

    try:
        db = _get_db_manager()
        import json

        # Sanitize request data - remove sensitive fields
        sanitized_data = None
        if request_data:
            sensitive_keys = {'password', 'token', 'api_key', 'secret', 'authorization'}
            sanitized_data = {
                k: '***' if k.lower() in sensitive_keys else v
                for k, v in request_data.items()
            }

        query = """
            INSERT INTO error_log (
                error_type, error_code, message, stack_trace,
                user_id, tenant_id, endpoint, request_data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        db.execute_query(query, (
            error_type[:100],
            error_code[:50] if error_code else None,
            message[:5000] if message else None,  # Limit message length
            stack_trace[:10000] if stack_trace else None,  # Limit stack trace
            user_id or _get_current_user_id(),
            tenant_id or _get_current_tenant_id(),
            endpoint[:255] if endpoint else None,
            json.dumps(sanitized_data) if sanitized_data else None
        ))
        return True
    except Exception as e:
        logger.error(f"Failed to log error: {e}")
        return False


def log_super_admin_access(
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None
) -> bool:
    """
    Log super admin access to analytics data (for security audit).

    Args:
        action: The action performed (e.g., 'viewed_users', 'exported_data')
        resource_type: Optional resource type (e.g., 'users', 'tenants')
        resource_id: Optional specific resource ID

    Returns:
        True if logged successfully, False otherwise
    """
    if not ANALYTICS_ENABLED:
        return True

    try:
        db = _get_db_manager()
        user_id = _get_current_user_id()

        if not user_id:
            logger.warning("Attempted to log super admin access without user context")
            return False

        query = """
            INSERT INTO super_admin_audit_log (
                super_admin_id, action, resource_type, resource_id,
                ip_address, user_agent
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        db.execute_query(query, (
            user_id,
            action[:100],
            resource_type[:50] if resource_type else None,
            resource_id[:100] if resource_id else None,
            _get_client_ip(),
            _get_user_agent()
        ))
        return True
    except Exception as e:
        logger.error(f"Failed to log super admin access: {e}")
        return False


def log_batch_events(events: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Log a batch of frontend events (page views and feature usage).

    Used by the frontend to batch events and reduce API calls.

    Args:
        events: List of event dictionaries with 'type' and event-specific data

    Returns:
        Dict with counts: {'page_views': N, 'features': N, 'errors': N}
    """
    if not ANALYTICS_ENABLED:
        return {'page_views': 0, 'features': 0, 'errors': 0}

    counts = {'page_views': 0, 'features': 0, 'errors': 0}

    for event in events:
        event_type = event.get('type')
        try:
            if event_type == 'page_view':
                if log_page_view(
                    page_path=event.get('page_path', ''),
                    page_title=event.get('page_title'),
                    session_id=event.get('session_id'),
                    referrer=event.get('referrer'),
                    user_id=event.get('user_id'),
                    tenant_id=event.get('tenant_id')
                ):
                    counts['page_views'] += 1

            elif event_type == 'feature':
                if log_feature_usage(
                    feature_name=event.get('feature_name', ''),
                    action=event.get('action', ''),
                    metadata=event.get('metadata'),
                    user_id=event.get('user_id'),
                    tenant_id=event.get('tenant_id')
                ):
                    counts['features'] += 1

            elif event_type == 'error':
                if log_error(
                    error_type=event.get('error_type', 'FrontendError'),
                    message=event.get('message', ''),
                    error_code=event.get('error_code'),
                    stack_trace=event.get('stack_trace'),
                    user_id=event.get('user_id'),
                    tenant_id=event.get('tenant_id')
                ):
                    counts['errors'] += 1

        except Exception as e:
            logger.error(f"Failed to log batch event: {e}")

    return counts
