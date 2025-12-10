"""
Super Admin Dashboard API Routes

Provides REST API endpoints for cross-tenant analytics and system health monitoring.
All endpoints require super_admin user type - these are for internal product team use only.

IMPORTANT: This dashboard is READ-ONLY and does NOT expose financial data.
Only aggregate usage metrics and patterns are provided.
"""

import logging
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from middleware.auth_middleware import (
    require_auth,
    require_super_admin,
    get_current_user
)
from web_ui.database import db_manager
from services.email_service import email_service

# Try to import analytics logger for audit logging
try:
    from web_ui.services.analytics_logger import log_super_admin_access
    AUDIT_LOGGER_AVAILABLE = True
except ImportError:
    AUDIT_LOGGER_AVAILABLE = False

logger = logging.getLogger(__name__)

super_admin_bp = Blueprint('super_admin', __name__, url_prefix='/api/super-admin')


def _log_access(action: str, resource_type: str = None, resource_id: str = None):
    """Log super admin access for audit trail."""
    if AUDIT_LOGGER_AVAILABLE:
        try:
            log_super_admin_access(action, resource_type, resource_id)
        except Exception as e:
            logger.error(f"Failed to log super admin access: {e}")


def _parse_date_range(request_args):
    """Parse date range from query parameters."""
    days = int(request_args.get('days', 30))
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Allow override with specific dates
    if request_args.get('start_date'):
        start_date = datetime.fromisoformat(request_args.get('start_date'))
    if request_args.get('end_date'):
        end_date = datetime.fromisoformat(request_args.get('end_date'))

    return start_date, end_date


# ==============================================================================
# USER ENGAGEMENT ENDPOINTS
# ==============================================================================

@super_admin_bp.route('/users/activity', methods=['GET'])
@require_auth
@require_super_admin
def get_user_activity():
    """
    Get active user counts by day/week/month.

    Query Parameters:
        - days: Number of days to include (default: 30)

    Returns:
        {
            "success": true,
            "data": {
                "daily_active_users": [...],
                "weekly_active_users": N,
                "monthly_active_users": N,
                "total_users": N
            }
        }
    """
    try:
        _log_access('viewed_user_activity', 'users')
        start_date, end_date = _parse_date_range(request.args)

        # Daily active users (users with sessions in each day)
        daily_query = """
            SELECT DATE(login_at) as date, COUNT(DISTINCT user_id) as count
            FROM user_session_log
            WHERE login_at >= %s AND login_at <= %s
            GROUP BY DATE(login_at)
            ORDER BY date DESC
        """
        daily_results = db_manager.execute_query(daily_query, (start_date, end_date), fetch_all=True)
        daily_active = [
            {'date': row['date'].isoformat(), 'count': row['count']}
            for row in (daily_results or [])
        ]

        # Weekly active users (last 7 days)
        week_ago = end_date - timedelta(days=7)
        wau_query = """
            SELECT COUNT(DISTINCT user_id) as count
            FROM user_session_log
            WHERE login_at >= %s AND login_at <= %s
        """
        wau_result = db_manager.execute_query(wau_query, (week_ago, end_date), fetch_one=True)
        weekly_active = wau_result['count'] if wau_result else 0

        # Monthly active users (last 30 days)
        month_ago = end_date - timedelta(days=30)
        mau_query = """
            SELECT COUNT(DISTINCT user_id) as count
            FROM user_session_log
            WHERE login_at >= %s AND login_at <= %s
        """
        mau_result = db_manager.execute_query(mau_query, (month_ago, end_date), fetch_one=True)
        monthly_active = mau_result['count'] if mau_result else 0

        # Total users
        total_query = "SELECT COUNT(*) as count FROM users WHERE is_active = true"
        total_result = db_manager.execute_query(total_query, fetch_one=True)
        total_users = total_result['count'] if total_result else 0

        return jsonify({
            'success': True,
            'data': {
                'daily_active_users': daily_active,
                'weekly_active_users': weekly_active,
                'monthly_active_users': monthly_active,
                'total_users': total_users
            }
        }), 200

    except Exception as e:
        logger.error(f"Get user activity error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching user activity'
        }), 500


@super_admin_bp.route('/users/sessions', methods=['GET'])
@require_auth
@require_super_admin
def get_user_sessions():
    """
    Get session duration statistics.

    Query Parameters:
        - days: Number of days to include (default: 30)

    Returns:
        {
            "success": true,
            "data": {
                "average_duration_minutes": N,
                "median_duration_minutes": N,
                "total_sessions": N,
                "sessions_by_day": [...]
            }
        }
    """
    try:
        _log_access('viewed_user_sessions', 'users')
        start_date, end_date = _parse_date_range(request.args)

        # Average and median session duration
        stats_query = """
            SELECT
                AVG(duration_minutes) as avg_duration,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_minutes) as median_duration,
                COUNT(*) as total_sessions
            FROM user_session_log
            WHERE login_at >= %s AND login_at <= %s
            AND duration_minutes IS NOT NULL
        """
        stats_result = db_manager.execute_query(stats_query, (start_date, end_date), fetch_one=True)

        avg_duration = round(float(stats_result['avg_duration'] or 0), 1)
        median_duration = round(float(stats_result['median_duration'] or 0), 1)
        total_sessions = stats_result['total_sessions'] or 0

        # Sessions by day
        daily_query = """
            SELECT DATE(login_at) as date, COUNT(*) as count
            FROM user_session_log
            WHERE login_at >= %s AND login_at <= %s
            GROUP BY DATE(login_at)
            ORDER BY date DESC
        """
        daily_results = db_manager.execute_query(daily_query, (start_date, end_date), fetch_all=True)
        sessions_by_day = [
            {'date': row['date'].isoformat(), 'count': row['count']}
            for row in (daily_results or [])
        ]

        return jsonify({
            'success': True,
            'data': {
                'average_duration_minutes': avg_duration,
                'median_duration_minutes': median_duration,
                'total_sessions': total_sessions,
                'sessions_by_day': sessions_by_day
            }
        }), 200

    except Exception as e:
        logger.error(f"Get user sessions error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching session data'
        }), 500


@super_admin_bp.route('/users/retention', methods=['GET'])
@require_auth
@require_super_admin
def get_user_retention():
    """
    Get cohort retention analysis.

    Returns retention rates for users grouped by signup week.

    Query Parameters:
        - weeks: Number of weeks to analyze (default: 8)

    Returns:
        {
            "success": true,
            "data": {
                "cohorts": [
                    {
                        "week": "2025-W01",
                        "users": 10,
                        "retention": [100, 80, 60, ...]
                    }
                ]
            }
        }
    """
    try:
        _log_access('viewed_user_retention', 'users')
        weeks = int(request.args.get('weeks', 8))

        # Get user signup cohorts
        cohort_query = """
            SELECT
                DATE_TRUNC('week', u.created_at) as cohort_week,
                COUNT(DISTINCT u.id) as cohort_size
            FROM users u
            WHERE u.created_at >= NOW() - INTERVAL '%s weeks'
            AND u.is_active = true
            GROUP BY DATE_TRUNC('week', u.created_at)
            ORDER BY cohort_week DESC
        """
        cohorts = db_manager.execute_query(cohort_query, (weeks,), fetch_all=True)

        cohort_data = []
        for cohort in (cohorts or []):
            cohort_week = cohort['cohort_week']
            cohort_size = cohort['cohort_size']

            # Calculate retention for each subsequent week
            retention_query = """
                SELECT
                    EXTRACT(WEEK FROM s.login_at) - EXTRACT(WEEK FROM %s) as week_number,
                    COUNT(DISTINCT s.user_id) as retained_users
                FROM user_session_log s
                JOIN users u ON s.user_id = u.id
                WHERE DATE_TRUNC('week', u.created_at) = %s
                AND s.login_at >= %s
                GROUP BY week_number
                ORDER BY week_number
            """
            retention_results = db_manager.execute_query(
                retention_query,
                (cohort_week, cohort_week, cohort_week),
                fetch_all=True
            )

            # Build retention array
            retention = []
            for i in range(min(weeks, 8)):
                week_data = next(
                    (r for r in (retention_results or []) if r['week_number'] == i),
                    None
                )
                if week_data and cohort_size > 0:
                    retention.append(round(week_data['retained_users'] / cohort_size * 100, 1))
                else:
                    retention.append(0)

            cohort_data.append({
                'week': cohort_week.strftime('%Y-W%W'),
                'users': cohort_size,
                'retention': retention
            })

        return jsonify({
            'success': True,
            'data': {
                'cohorts': cohort_data
            }
        }), 200

    except Exception as e:
        logger.error(f"Get user retention error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while calculating retention'
        }), 500


@super_admin_bp.route('/users/list', methods=['GET'])
@require_auth
@require_super_admin
def list_all_users():
    """
    List all users with engagement metrics.

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 50, max: 100)
        - search: Search by email
        - user_type: Filter by user type

    Returns:
        {
            "success": true,
            "data": {
                "users": [...],
                "total": N,
                "page": N,
                "per_page": N
            }
        }
    """
    try:
        _log_access('viewed_user_list', 'users')

        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        search = request.args.get('search', '')
        user_type = request.args.get('user_type')
        offset = (page - 1) * per_page

        # Build query
        where_clauses = ["u.is_active = true"]
        params = []

        if search:
            where_clauses.append("u.email ILIKE %s")
            params.append(f"%{search}%")

        if user_type:
            where_clauses.append("u.user_type = %s")
            params.append(user_type)

        where_sql = " AND ".join(where_clauses)

        # Count total
        count_query = f"""
            SELECT COUNT(*) as total FROM users u
            WHERE {where_sql}
        """
        count_result = db_manager.execute_query(count_query, tuple(params), fetch_one=True)
        total = count_result['total'] if count_result else 0

        # Get users with engagement metrics
        users_query = f"""
            SELECT
                u.id,
                u.email,
                u.display_name,
                u.user_type,
                u.created_at,
                u.last_login_at,
                (
                    SELECT COUNT(*) FROM user_session_log s
                    WHERE s.user_id = u.id
                    AND s.login_at >= NOW() - INTERVAL '7 days'
                ) as sessions_7d,
                (
                    SELECT COUNT(*) FROM feature_usage_log f
                    WHERE f.user_id = u.id
                    AND f.created_at >= NOW() - INTERVAL '7 days'
                ) as actions_7d,
                (
                    SELECT array_agg(DISTINCT tu.tenant_id)
                    FROM tenant_users tu
                    WHERE tu.user_id = u.id AND tu.is_active = true
                ) as tenant_ids
            FROM users u
            WHERE {where_sql}
            ORDER BY u.last_login_at DESC NULLS LAST
            LIMIT %s OFFSET %s
        """
        params.extend([per_page, offset])

        users_results = db_manager.execute_query(users_query, tuple(params), fetch_all=True)

        users = []
        for row in (users_results or []):
            users.append({
                'id': str(row['id']),
                'email': row['email'],
                'display_name': row['display_name'],
                'user_type': row['user_type'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'last_login_at': row['last_login_at'].isoformat() if row['last_login_at'] else None,
                'sessions_7d': row['sessions_7d'] or 0,
                'actions_7d': row['actions_7d'] or 0,
                'tenant_ids': row['tenant_ids'] or []
            })

        return jsonify({
            'success': True,
            'data': {
                'users': users,
                'total': total,
                'page': page,
                'per_page': per_page
            }
        }), 200

    except Exception as e:
        logger.error(f"List users error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching users'
        }), 500


# ==============================================================================
# TENANT ANALYTICS ENDPOINTS
# ==============================================================================

@super_admin_bp.route('/tenants', methods=['GET'])
@require_auth
@require_super_admin
def list_tenants():
    """
    List all tenants with health metrics.

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 50)
        - search: Search by company name

    Returns:
        {
            "success": true,
            "data": {
                "tenants": [...],
                "total": N
            }
        }
    """
    try:
        _log_access('viewed_tenant_list', 'tenants')

        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        search = request.args.get('search', '')
        offset = (page - 1) * per_page

        # Build query
        where_clause = ""
        params = []

        if search:
            where_clause = "WHERE tc.company_name ILIKE %s"
            params.append(f"%{search}%")

        # Count total
        count_query = f"""
            SELECT COUNT(*) as total FROM tenant_configuration tc
            {where_clause}
        """
        count_result = db_manager.execute_query(count_query, tuple(params), fetch_one=True)
        total = count_result['total'] if count_result else 0

        # Get tenants with metrics
        tenants_query = f"""
            SELECT
                tc.tenant_id,
                tc.company_name,
                tc.company_description,
                tc.created_at,
                (
                    SELECT COUNT(DISTINCT tu.user_id)
                    FROM tenant_users tu
                    WHERE tu.tenant_id = tc.tenant_id AND tu.is_active = true
                ) as user_count,
                (
                    SELECT MAX(s.login_at)
                    FROM user_session_log s
                    WHERE s.tenant_id = tc.tenant_id
                ) as last_activity,
                (
                    SELECT COUNT(*) FROM transactions t
                    WHERE t.tenant_id = tc.tenant_id
                    AND t.created_at >= NOW() - INTERVAL '30 days'
                ) as transactions_30d
            FROM tenant_configuration tc
            {where_clause}
            ORDER BY last_activity DESC NULLS LAST
            LIMIT %s OFFSET %s
        """
        params.extend([per_page, offset])

        tenants_results = db_manager.execute_query(tenants_query, tuple(params), fetch_all=True)

        tenants = []
        for row in (tenants_results or []):
            # Calculate health score (simple algorithm)
            health_score = 100
            last_activity = row['last_activity']
            transactions_30d = row['transactions_30d'] or 0

            if last_activity:
                days_inactive = (datetime.utcnow() - last_activity).days
                if days_inactive > 14:
                    health_score -= 30
                elif days_inactive > 7:
                    health_score -= 15
            else:
                health_score -= 50

            if transactions_30d == 0:
                health_score -= 20
            elif transactions_30d < 10:
                health_score -= 10

            # Determine churn risk
            churn_risk = 'low'
            if health_score < 50:
                churn_risk = 'high'
            elif health_score < 70:
                churn_risk = 'medium'

            tenants.append({
                'id': row['tenant_id'],
                'company_name': row['company_name'],
                'description': row['company_description'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'user_count': row['user_count'] or 0,
                'last_activity': last_activity.isoformat() if last_activity else None,
                'transactions_30d': transactions_30d,
                'health_score': max(0, health_score),
                'churn_risk': churn_risk
            })

        return jsonify({
            'success': True,
            'data': {
                'tenants': tenants,
                'total': total,
                'page': page,
                'per_page': per_page
            }
        }), 200

    except Exception as e:
        logger.error(f"List tenants error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching tenants'
        }), 500


@super_admin_bp.route('/tenants/<tenant_id>/activity', methods=['GET'])
@require_auth
@require_super_admin
def get_tenant_activity(tenant_id):
    """
    Get detailed activity for a specific tenant.

    Query Parameters:
        - days: Number of days to include (default: 30)

    Returns:
        {
            "success": true,
            "data": {
                "tenant": {...},
                "daily_sessions": [...],
                "top_features": [...],
                "user_activity": [...]
            }
        }
    """
    try:
        _log_access('viewed_tenant_activity', 'tenants', tenant_id)
        start_date, end_date = _parse_date_range(request.args)

        # Get tenant info
        tenant_query = """
            SELECT tenant_id, company_name, company_description, created_at
            FROM tenant_configuration
            WHERE tenant_id = %s
        """
        tenant_result = db_manager.execute_query(tenant_query, (tenant_id,), fetch_one=True)

        if not tenant_result:
            return jsonify({
                'success': False,
                'error': 'not_found',
                'message': 'Tenant not found'
            }), 404

        tenant = {
            'id': tenant_result['tenant_id'],
            'company_name': tenant_result['company_name'],
            'description': tenant_result['company_description'],
            'created_at': tenant_result['created_at'].isoformat() if tenant_result['created_at'] else None
        }

        # Daily sessions
        sessions_query = """
            SELECT DATE(login_at) as date, COUNT(*) as count
            FROM user_session_log
            WHERE tenant_id = %s AND login_at >= %s AND login_at <= %s
            GROUP BY DATE(login_at)
            ORDER BY date DESC
        """
        sessions_results = db_manager.execute_query(
            sessions_query, (tenant_id, start_date, end_date), fetch_all=True
        )
        daily_sessions = [
            {'date': row['date'].isoformat(), 'count': row['count']}
            for row in (sessions_results or [])
        ]

        # Top features used
        features_query = """
            SELECT feature_name, COUNT(*) as count
            FROM feature_usage_log
            WHERE tenant_id = %s AND created_at >= %s AND created_at <= %s
            GROUP BY feature_name
            ORDER BY count DESC
            LIMIT 10
        """
        features_results = db_manager.execute_query(
            features_query, (tenant_id, start_date, end_date), fetch_all=True
        )
        top_features = [
            {'feature': row['feature_name'], 'count': row['count']}
            for row in (features_results or [])
        ]

        # User activity breakdown
        users_query = """
            SELECT
                u.email,
                u.display_name,
                COUNT(DISTINCT s.id) as sessions,
                COUNT(DISTINCT f.id) as actions
            FROM users u
            JOIN tenant_users tu ON u.id = tu.user_id
            LEFT JOIN user_session_log s ON u.id = s.user_id
                AND s.login_at >= %s AND s.login_at <= %s
            LEFT JOIN feature_usage_log f ON u.id = f.user_id
                AND f.created_at >= %s AND f.created_at <= %s
            WHERE tu.tenant_id = %s AND tu.is_active = true
            GROUP BY u.id, u.email, u.display_name
            ORDER BY sessions DESC
            LIMIT 20
        """
        users_results = db_manager.execute_query(
            users_query, (start_date, end_date, start_date, end_date, tenant_id), fetch_all=True
        )
        user_activity = [
            {
                'email': row['email'],
                'display_name': row['display_name'],
                'sessions': row['sessions'] or 0,
                'actions': row['actions'] or 0
            }
            for row in (users_results or [])
        ]

        return jsonify({
            'success': True,
            'data': {
                'tenant': tenant,
                'daily_sessions': daily_sessions,
                'top_features': top_features,
                'user_activity': user_activity
            }
        }), 200

    except Exception as e:
        logger.error(f"Get tenant activity error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching tenant activity'
        }), 500


@super_admin_bp.route('/tenants/growth', methods=['GET'])
@require_auth
@require_super_admin
def get_tenant_growth():
    """
    Get tenant growth over time.

    Query Parameters:
        - days: Number of days to include (default: 90)

    Returns:
        {
            "success": true,
            "data": {
                "new_tenants_by_week": [...],
                "total_tenants": N,
                "active_tenants_30d": N
            }
        }
    """
    try:
        _log_access('viewed_tenant_growth', 'tenants')
        start_date, end_date = _parse_date_range(request.args)

        # New tenants by week
        weekly_query = """
            SELECT
                DATE_TRUNC('week', created_at) as week,
                COUNT(*) as count
            FROM tenant_configuration
            WHERE created_at >= %s AND created_at <= %s
            GROUP BY DATE_TRUNC('week', created_at)
            ORDER BY week DESC
        """
        weekly_results = db_manager.execute_query(weekly_query, (start_date, end_date), fetch_all=True)
        new_tenants_by_week = [
            {'week': row['week'].strftime('%Y-W%W'), 'count': row['count']}
            for row in (weekly_results or [])
        ]

        # Total tenants
        total_query = "SELECT COUNT(*) as count FROM tenant_configuration"
        total_result = db_manager.execute_query(total_query, fetch_one=True)
        total_tenants = total_result['count'] if total_result else 0

        # Active tenants (had activity in last 30 days)
        active_query = """
            SELECT COUNT(DISTINCT tenant_id) as count
            FROM user_session_log
            WHERE login_at >= NOW() - INTERVAL '30 days'
        """
        active_result = db_manager.execute_query(active_query, fetch_one=True)
        active_tenants = active_result['count'] if active_result else 0

        return jsonify({
            'success': True,
            'data': {
                'new_tenants_by_week': new_tenants_by_week,
                'total_tenants': total_tenants,
                'active_tenants_30d': active_tenants
            }
        }), 200

    except Exception as e:
        logger.error(f"Get tenant growth error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching tenant growth'
        }), 500


@super_admin_bp.route('/tenants/churn-risk', methods=['GET'])
@require_auth
@require_super_admin
def get_churn_risk_tenants():
    """
    Get tenants at risk of churning.

    Churn risk indicators:
    - No logins in 14+ days
    - Declining feature usage
    - No transactions in 30+ days

    Returns:
        {
            "success": true,
            "data": {
                "at_risk_tenants": [...],
                "risk_summary": {...}
            }
        }
    """
    try:
        _log_access('viewed_churn_risk', 'tenants')

        # Find at-risk tenants
        risk_query = """
            SELECT
                tc.tenant_id,
                tc.company_name,
                (
                    SELECT MAX(s.login_at)
                    FROM user_session_log s
                    WHERE s.tenant_id = tc.tenant_id
                ) as last_login,
                (
                    SELECT COUNT(*) FROM transactions t
                    WHERE t.tenant_id = tc.tenant_id
                    AND t.created_at >= NOW() - INTERVAL '30 days'
                ) as transactions_30d,
                (
                    SELECT COUNT(*) FROM feature_usage_log f
                    WHERE f.tenant_id = tc.tenant_id
                    AND f.created_at >= NOW() - INTERVAL '7 days'
                ) as actions_7d
            FROM tenant_configuration tc
        """
        results = db_manager.execute_query(risk_query, fetch_all=True)

        at_risk = []
        high_risk = 0
        medium_risk = 0

        for row in (results or []):
            last_login = row['last_login']
            transactions_30d = row['transactions_30d'] or 0
            actions_7d = row['actions_7d'] or 0

            risk_factors = []
            risk_level = 'low'

            if last_login:
                days_inactive = (datetime.utcnow() - last_login).days
                if days_inactive >= 14:
                    risk_factors.append(f"No login in {days_inactive} days")
                    risk_level = 'high'
                elif days_inactive >= 7:
                    risk_factors.append(f"No login in {days_inactive} days")
                    risk_level = 'medium'
            else:
                risk_factors.append("Never logged in")
                risk_level = 'high'

            if transactions_30d == 0:
                risk_factors.append("No transactions in 30 days")
                if risk_level != 'high':
                    risk_level = 'medium'

            if actions_7d == 0:
                risk_factors.append("No feature usage in 7 days")

            if risk_level in ['high', 'medium']:
                at_risk.append({
                    'tenant_id': row['tenant_id'],
                    'company_name': row['company_name'],
                    'last_login': last_login.isoformat() if last_login else None,
                    'transactions_30d': transactions_30d,
                    'actions_7d': actions_7d,
                    'risk_level': risk_level,
                    'risk_factors': risk_factors
                })

                if risk_level == 'high':
                    high_risk += 1
                else:
                    medium_risk += 1

        # Sort by risk level
        at_risk.sort(key=lambda x: (0 if x['risk_level'] == 'high' else 1, x['company_name']))

        return jsonify({
            'success': True,
            'data': {
                'at_risk_tenants': at_risk,
                'risk_summary': {
                    'high_risk': high_risk,
                    'medium_risk': medium_risk,
                    'total_at_risk': len(at_risk)
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Get churn risk error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while analyzing churn risk'
        }), 500


# ==============================================================================
# FEATURE USAGE ENDPOINTS
# ==============================================================================

@super_admin_bp.route('/features/usage', methods=['GET'])
@require_auth
@require_super_admin
def get_feature_usage():
    """
    Get feature adoption rates.

    Query Parameters:
        - days: Number of days to include (default: 30)

    Returns:
        {
            "success": true,
            "data": {
                "features": [
                    {
                        "feature": "file_upload",
                        "total_uses": N,
                        "unique_users": N,
                        "adoption_rate": N
                    }
                ],
                "total_active_users": N
            }
        }
    """
    try:
        _log_access('viewed_feature_usage', 'features')
        start_date, end_date = _parse_date_range(request.args)

        # Get total active users in period
        users_query = """
            SELECT COUNT(DISTINCT user_id) as count
            FROM user_session_log
            WHERE login_at >= %s AND login_at <= %s
        """
        users_result = db_manager.execute_query(users_query, (start_date, end_date), fetch_one=True)
        total_active_users = users_result['count'] if users_result else 0

        # Get feature usage
        features_query = """
            SELECT
                feature_name,
                COUNT(*) as total_uses,
                COUNT(DISTINCT user_id) as unique_users
            FROM feature_usage_log
            WHERE created_at >= %s AND created_at <= %s
            GROUP BY feature_name
            ORDER BY total_uses DESC
        """
        features_results = db_manager.execute_query(features_query, (start_date, end_date), fetch_all=True)

        features = []
        for row in (features_results or []):
            adoption_rate = 0
            if total_active_users > 0:
                adoption_rate = round(row['unique_users'] / total_active_users * 100, 1)

            features.append({
                'feature': row['feature_name'],
                'total_uses': row['total_uses'],
                'unique_users': row['unique_users'],
                'adoption_rate': adoption_rate
            })

        return jsonify({
            'success': True,
            'data': {
                'features': features,
                'total_active_users': total_active_users
            }
        }), 200

    except Exception as e:
        logger.error(f"Get feature usage error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching feature usage'
        }), 500


@super_admin_bp.route('/features/trends', methods=['GET'])
@require_auth
@require_super_admin
def get_feature_trends():
    """
    Get feature usage trends over time.

    Query Parameters:
        - days: Number of days to include (default: 30)
        - feature: Specific feature to filter (optional)

    Returns:
        {
            "success": true,
            "data": {
                "trends": [
                    {
                        "date": "2025-12-08",
                        "feature_counts": {...}
                    }
                ]
            }
        }
    """
    try:
        _log_access('viewed_feature_trends', 'features')
        start_date, end_date = _parse_date_range(request.args)
        feature_filter = request.args.get('feature')

        # Build query
        where_clause = "WHERE created_at >= %s AND created_at <= %s"
        params = [start_date, end_date]

        if feature_filter:
            where_clause += " AND feature_name = %s"
            params.append(feature_filter)

        trends_query = f"""
            SELECT
                DATE(created_at) as date,
                feature_name,
                COUNT(*) as count
            FROM feature_usage_log
            {where_clause}
            GROUP BY DATE(created_at), feature_name
            ORDER BY date DESC, count DESC
        """
        results = db_manager.execute_query(trends_query, tuple(params), fetch_all=True)

        # Group by date
        trends_by_date = {}
        for row in (results or []):
            date_str = row['date'].isoformat()
            if date_str not in trends_by_date:
                trends_by_date[date_str] = {}
            trends_by_date[date_str][row['feature_name']] = row['count']

        trends = [
            {'date': date, 'feature_counts': counts}
            for date, counts in sorted(trends_by_date.items(), reverse=True)
        ]

        return jsonify({
            'success': True,
            'data': {
                'trends': trends
            }
        }), 200

    except Exception as e:
        logger.error(f"Get feature trends error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching feature trends'
        }), 500


@super_admin_bp.route('/features/by-tenant', methods=['GET'])
@require_auth
@require_super_admin
def get_feature_usage_by_tenant():
    """
    Get feature usage breakdown by tenant.

    Query Parameters:
        - days: Number of days to include (default: 30)
        - feature: Specific feature to filter (optional)

    Returns:
        {
            "success": true,
            "data": {
                "tenant_usage": [...]
            }
        }
    """
    try:
        _log_access('viewed_feature_by_tenant', 'features')
        start_date, end_date = _parse_date_range(request.args)
        feature_filter = request.args.get('feature')

        # Build query
        where_clause = "WHERE f.created_at >= %s AND f.created_at <= %s"
        params = [start_date, end_date]

        if feature_filter:
            where_clause += " AND f.feature_name = %s"
            params.append(feature_filter)

        query = f"""
            SELECT
                tc.tenant_id,
                tc.company_name,
                f.feature_name,
                COUNT(*) as count
            FROM feature_usage_log f
            JOIN tenant_configuration tc ON f.tenant_id = tc.tenant_id
            {where_clause}
            GROUP BY tc.tenant_id, tc.company_name, f.feature_name
            ORDER BY count DESC
            LIMIT 100
        """
        results = db_manager.execute_query(query, tuple(params), fetch_all=True)

        tenant_usage = [
            {
                'tenant_id': row['tenant_id'],
                'company_name': row['company_name'],
                'feature': row['feature_name'],
                'count': row['count']
            }
            for row in (results or [])
        ]

        return jsonify({
            'success': True,
            'data': {
                'tenant_usage': tenant_usage
            }
        }), 200

    except Exception as e:
        logger.error(f"Get feature by tenant error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching feature usage by tenant'
        }), 500


# ==============================================================================
# ERROR & PERFORMANCE ENDPOINTS
# ==============================================================================

@super_admin_bp.route('/errors', methods=['GET'])
@require_auth
@require_super_admin
def list_errors():
    """
    List application errors.

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 50)
        - error_type: Filter by error type
        - days: Number of days to include (default: 7)

    Returns:
        {
            "success": true,
            "data": {
                "errors": [...],
                "total": N
            }
        }
    """
    try:
        _log_access('viewed_errors', 'errors')

        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        error_type = request.args.get('error_type')
        offset = (page - 1) * per_page

        days = int(request.args.get('days', 7))
        start_date = datetime.utcnow() - timedelta(days=days)

        # Build query
        where_clauses = ["created_at >= %s"]
        params = [start_date]

        if error_type:
            where_clauses.append("error_type = %s")
            params.append(error_type)

        where_sql = " AND ".join(where_clauses)

        # Count total
        count_query = f"SELECT COUNT(*) as total FROM error_log WHERE {where_sql}"
        count_result = db_manager.execute_query(count_query, tuple(params), fetch_one=True)
        total = count_result['total'] if count_result else 0

        # Get errors
        errors_query = f"""
            SELECT
                e.id,
                e.error_type,
                e.error_code,
                e.message,
                e.stack_trace,
                e.endpoint,
                e.user_id,
                e.tenant_id,
                e.created_at,
                u.email as user_email
            FROM error_log e
            LEFT JOIN users u ON e.user_id = u.id
            WHERE {where_sql}
            ORDER BY e.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([per_page, offset])

        results = db_manager.execute_query(errors_query, tuple(params), fetch_all=True)

        errors = []
        for row in (results or []):
            errors.append({
                'id': str(row['id']),
                'error_type': row['error_type'],
                'error_code': row['error_code'],
                'message': row['message'],
                'stack_trace': row['stack_trace'],
                'endpoint': row['endpoint'],
                'user_id': str(row['user_id']) if row['user_id'] else None,
                'user_email': row['user_email'],
                'tenant_id': row['tenant_id'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            })

        return jsonify({
            'success': True,
            'data': {
                'errors': errors,
                'total': total,
                'page': page,
                'per_page': per_page
            }
        }), 200

    except Exception as e:
        logger.error(f"List errors error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching errors'
        }), 500


@super_admin_bp.route('/errors/trends', methods=['GET'])
@require_auth
@require_super_admin
def get_error_trends():
    """
    Get error rate trends over time.

    Query Parameters:
        - days: Number of days to include (default: 7)

    Returns:
        {
            "success": true,
            "data": {
                "daily_errors": [...],
                "total_errors": N
            }
        }
    """
    try:
        _log_access('viewed_error_trends', 'errors')
        start_date, end_date = _parse_date_range(request.args)

        # Daily error counts
        daily_query = """
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM error_log
            WHERE created_at >= %s AND created_at <= %s
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """
        daily_results = db_manager.execute_query(daily_query, (start_date, end_date), fetch_all=True)
        daily_errors = [
            {'date': row['date'].isoformat(), 'count': row['count']}
            for row in (daily_results or [])
        ]

        # Total errors
        total_query = """
            SELECT COUNT(*) as count FROM error_log
            WHERE created_at >= %s AND created_at <= %s
        """
        total_result = db_manager.execute_query(total_query, (start_date, end_date), fetch_one=True)
        total_errors = total_result['count'] if total_result else 0

        return jsonify({
            'success': True,
            'data': {
                'daily_errors': daily_errors,
                'total_errors': total_errors
            }
        }), 200

    except Exception as e:
        logger.error(f"Get error trends error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching error trends'
        }), 500


@super_admin_bp.route('/errors/by-type', methods=['GET'])
@require_auth
@require_super_admin
def get_errors_by_type():
    """
    Get errors grouped by type.

    Query Parameters:
        - days: Number of days to include (default: 7)

    Returns:
        {
            "success": true,
            "data": {
                "error_types": [...]
            }
        }
    """
    try:
        _log_access('viewed_errors_by_type', 'errors')
        start_date, end_date = _parse_date_range(request.args)

        query = """
            SELECT error_type, COUNT(*) as count
            FROM error_log
            WHERE created_at >= %s AND created_at <= %s
            GROUP BY error_type
            ORDER BY count DESC
        """
        results = db_manager.execute_query(query, (start_date, end_date), fetch_all=True)

        error_types = [
            {'type': row['error_type'], 'count': row['count']}
            for row in (results or [])
        ]

        return jsonify({
            'success': True,
            'data': {
                'error_types': error_types
            }
        }), 200

    except Exception as e:
        logger.error(f"Get errors by type error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching errors by type'
        }), 500


@super_admin_bp.route('/performance/api', methods=['GET'])
@require_auth
@require_super_admin
def get_api_performance():
    """
    Get API performance metrics.

    Query Parameters:
        - days: Number of days to include (default: 7)

    Returns:
        {
            "success": true,
            "data": {
                "avg_response_time_ms": N,
                "p95_response_time_ms": N,
                "requests_per_minute": N,
                "error_rate": N
            }
        }
    """
    try:
        _log_access('viewed_api_performance', 'system')
        start_date, end_date = _parse_date_range(request.args)

        # Performance stats
        perf_query = """
            SELECT
                AVG(duration_ms) as avg_duration,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration,
                COUNT(*) as total_requests,
                COUNT(*) FILTER (WHERE response_code >= 500) as error_count
            FROM api_request_log
            WHERE created_at >= %s AND created_at <= %s
        """
        perf_result = db_manager.execute_query(perf_query, (start_date, end_date), fetch_one=True)

        avg_response_time = round(float(perf_result['avg_duration'] or 0), 1)
        p95_response_time = round(float(perf_result['p95_duration'] or 0), 1)
        total_requests = perf_result['total_requests'] or 0
        error_count = perf_result['error_count'] or 0

        # Calculate requests per minute
        time_span_minutes = (end_date - start_date).total_seconds() / 60
        requests_per_minute = round(total_requests / max(time_span_minutes, 1), 2)

        # Calculate error rate
        error_rate = round(error_count / max(total_requests, 1) * 100, 2)

        return jsonify({
            'success': True,
            'data': {
                'avg_response_time_ms': avg_response_time,
                'p95_response_time_ms': p95_response_time,
                'requests_per_minute': requests_per_minute,
                'total_requests': total_requests,
                'error_rate': error_rate
            }
        }), 200

    except Exception as e:
        logger.error(f"Get API performance error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching API performance'
        }), 500


@super_admin_bp.route('/performance/slow-endpoints', methods=['GET'])
@require_auth
@require_super_admin
def get_slow_endpoints():
    """
    Get slowest API endpoints.

    Query Parameters:
        - days: Number of days to include (default: 7)
        - threshold_ms: Minimum avg response time (default: 500)

    Returns:
        {
            "success": true,
            "data": {
                "slow_endpoints": [...]
            }
        }
    """
    try:
        _log_access('viewed_slow_endpoints', 'system')
        start_date, end_date = _parse_date_range(request.args)
        threshold_ms = int(request.args.get('threshold_ms', 500))

        query = """
            SELECT
                endpoint,
                method,
                AVG(duration_ms) as avg_duration,
                MAX(duration_ms) as max_duration,
                COUNT(*) as request_count
            FROM api_request_log
            WHERE created_at >= %s AND created_at <= %s
            GROUP BY endpoint, method
            HAVING AVG(duration_ms) >= %s
            ORDER BY avg_duration DESC
            LIMIT 20
        """
        results = db_manager.execute_query(query, (start_date, end_date, threshold_ms), fetch_all=True)

        slow_endpoints = [
            {
                'endpoint': row['endpoint'],
                'method': row['method'],
                'avg_duration_ms': round(float(row['avg_duration']), 1),
                'max_duration_ms': row['max_duration'],
                'request_count': row['request_count']
            }
            for row in (results or [])
        ]

        return jsonify({
            'success': True,
            'data': {
                'slow_endpoints': slow_endpoints
            }
        }), 200

    except Exception as e:
        logger.error(f"Get slow endpoints error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching slow endpoints'
        }), 500


# ==============================================================================
# SYSTEM HEALTH ENDPOINTS
# ==============================================================================

@super_admin_bp.route('/health/overview', methods=['GET'])
@require_auth
@require_super_admin
def get_health_overview():
    """
    Get system health overview.

    Returns:
        {
            "success": true,
            "data": {
                "status": "healthy",
                "database": {...},
                "recent_errors": N,
                "active_users_24h": N
            }
        }
    """
    try:
        _log_access('viewed_health_overview', 'system')

        # Check database connection
        db_status = 'healthy'
        try:
            db_manager.execute_query("SELECT 1", fetch_one=True)
        except Exception:
            db_status = 'unhealthy'

        # Recent errors (last 24 hours)
        errors_query = """
            SELECT COUNT(*) as count FROM error_log
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """
        errors_result = db_manager.execute_query(errors_query, fetch_one=True)
        recent_errors = errors_result['count'] if errors_result else 0

        # Active users (last 24 hours)
        users_query = """
            SELECT COUNT(DISTINCT user_id) as count FROM user_session_log
            WHERE login_at >= NOW() - INTERVAL '24 hours'
        """
        users_result = db_manager.execute_query(users_query, fetch_one=True)
        active_users_24h = users_result['count'] if users_result else 0

        # Overall status
        overall_status = 'healthy'
        if db_status == 'unhealthy':
            overall_status = 'critical'
        elif recent_errors > 100:
            overall_status = 'degraded'

        return jsonify({
            'success': True,
            'data': {
                'status': overall_status,
                'database': {
                    'status': db_status
                },
                'recent_errors': recent_errors,
                'active_users_24h': active_users_24h,
                'timestamp': datetime.utcnow().isoformat()
            }
        }), 200

    except Exception as e:
        logger.error(f"Get health overview error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching health overview'
        }), 500


@super_admin_bp.route('/health/database', methods=['GET'])
@require_auth
@require_super_admin
def get_database_health():
    """
    Get database statistics.

    Returns:
        {
            "success": true,
            "data": {
                "table_stats": [...],
                "connection_info": {...}
            }
        }
    """
    try:
        _log_access('viewed_database_health', 'system')

        # Get table row counts for key tables
        tables = [
            'users', 'tenant_configuration', 'transactions', 'invoices',
            'user_session_log', 'feature_usage_log', 'error_log', 'api_request_log'
        ]

        table_stats = []
        for table in tables:
            try:
                count_query = f"SELECT COUNT(*) as count FROM {table}"
                result = db_manager.execute_query(count_query, fetch_one=True)
                table_stats.append({
                    'table': table,
                    'row_count': result['count'] if result else 0
                })
            except Exception:
                table_stats.append({
                    'table': table,
                    'row_count': -1,
                    'error': 'Table not found or access denied'
                })

        # Get database size info (PostgreSQL specific)
        try:
            size_query = """
                SELECT pg_database_size(current_database()) as size_bytes
            """
            size_result = db_manager.execute_query(size_query, fetch_one=True)
            db_size_bytes = size_result['size_bytes'] if size_result else 0
            db_size_mb = round(db_size_bytes / (1024 * 1024), 2)
        except Exception:
            db_size_mb = -1

        return jsonify({
            'success': True,
            'data': {
                'table_stats': table_stats,
                'database_size_mb': db_size_mb,
                'connection_info': {
                    'status': 'connected'
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Get database health error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching database health'
        }), 500


# ==============================================================================
# USER INVITATION ENDPOINTS
# ==============================================================================

@super_admin_bp.route('/invitations', methods=['POST'])
@require_auth
@require_super_admin
def create_super_admin_invitation():
    """
    Create an invitation for a new user (CFO or Business Owner).

    Super Admin can invite:
    - fractional_cfo: CFOs who can create their own tenants
    - tenant_admin: Business owners who will have a tenant created for them

    Request Body:
        {
            "email": "user@example.com",
            "user_type": "fractional_cfo" | "tenant_admin",
            "company_name": "Company Name" (required for tenant_admin)
        }

    Returns:
        {
            "success": true,
            "invitation": {...},
            "message": "Invitation sent successfully"
        }
    """
    try:
        current_user = get_current_user()
        data = request.get_json()

        # Validate required fields
        email = data.get('email')
        user_type = data.get('user_type')
        company_name = data.get('company_name')

        if not email:
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'Email is required'
            }), 400

        if not user_type:
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'User type is required'
            }), 400

        # Validate user type
        if user_type not in ['fractional_cfo', 'tenant_admin']:
            return jsonify({
                'success': False,
                'error': 'invalid_user_type',
                'message': 'User type must be fractional_cfo or tenant_admin'
            }), 400

        # Company name required for business owners
        if user_type == 'tenant_admin' and not company_name:
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'Company name is required for business owners'
            }), 400

        # Check if user already exists
        existing_query = "SELECT id FROM users WHERE email = %s"
        existing = db_manager.execute_query(existing_query, (email,), fetch_one=True)

        if existing:
            return jsonify({
                'success': False,
                'error': 'user_exists',
                'message': 'A user with this email already exists'
            }), 400

        # Check for pending invitation
        pending_query = """
            SELECT id FROM user_invitations
            WHERE email = %s AND status = 'pending' AND tenant_id IS NULL
        """
        pending = db_manager.execute_query(pending_query, (email,), fetch_one=True)

        if pending:
            return jsonify({
                'success': False,
                'error': 'invitation_exists',
                'message': 'A pending invitation already exists for this email'
            }), 400

        # Create invitation
        invitation_id = str(uuid.uuid4())
        invitation_token = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=7)

        # For super admin invitations, tenant_id is NULL
        # Role is determined by user_type: fractional_cfo -> 'cfo', tenant_admin -> 'owner'
        role_value = 'cfo' if user_type == 'fractional_cfo' else 'owner'

        # Store company_name in invitation_data JSONB field
        import json
        invitation_data = {}
        if company_name:
            invitation_data['company_name'] = company_name

        insert_query = """
            INSERT INTO user_invitations
            (id, email, invited_by_user_id, tenant_id, user_type, role, invitation_token, status, expires_at, invitation_data)
            VALUES (%s, %s, %s, NULL, %s, %s, %s, 'pending', %s, %s)
            RETURNING id, email, user_type, role, invitation_token, expires_at, invitation_data
        """

        result = db_manager.execute_query(
            insert_query,
            (invitation_id, email, current_user['id'], user_type, role_value, invitation_token, expires_at, json.dumps(invitation_data)),
            fetch_one=True
        )

        if not result:
            return jsonify({
                'success': False,
                'error': 'database_error',
                'message': 'Failed to create invitation'
            }), 500

        # Extract company_name from invitation_data
        inv_data = result.get('invitation_data') or {}
        if isinstance(inv_data, str):
            inv_data = json.loads(inv_data)

        invitation = {
            'id': str(result['id']),
            'email': result['email'],
            'user_type': result['user_type'],
            'company_name': inv_data.get('company_name') if user_type == 'tenant_admin' else None,
            'expires_at': result['expires_at'].isoformat() if result['expires_at'] else None
        }

        # Send invitation email
        try:
            email_sent = _send_super_admin_invitation_email(
                to_email=email,
                invitation_token=invitation_token,
                inviter_name=current_user.get('display_name', 'Delta CFO Admin'),
                user_type=user_type,
                company_name=company_name,
                expires_in_days=7
            )
            if not email_sent:
                logger.warning(f"Failed to send invitation email to {email}")
        except Exception as e:
            logger.error(f"Failed to send invitation email: {e}")

        _log_access('created_invitation', 'invitations', invitation_id)
        logger.info(f"Super admin invitation created: {email} as {user_type} by {current_user.get('email')}")

        return jsonify({
            'success': True,
            'invitation': invitation,
            'message': 'Invitation sent successfully'
        }), 201

    except Exception as e:
        logger.error(f"Create super admin invitation error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while creating invitation'
        }), 500


@super_admin_bp.route('/invitations', methods=['GET'])
@require_auth
@require_super_admin
def list_super_admin_invitations():
    """
    List all super admin invitations (tenant_id IS NULL).

    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 50)
        - status: Filter by status (pending, accepted, expired, revoked)

    Returns:
        {
            "success": true,
            "data": {
                "invitations": [...],
                "total": N,
                "page": N,
                "per_page": N
            }
        }
    """
    try:
        _log_access('viewed_invitations', 'invitations')

        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 50)), 100)
        status_filter = request.args.get('status')
        offset = (page - 1) * per_page

        # Build query for super admin invitations (tenant_id IS NULL)
        where_clauses = ["ui.tenant_id IS NULL"]
        params = []

        if status_filter:
            where_clauses.append("ui.status = %s")
            params.append(status_filter)

        where_sql = " AND ".join(where_clauses)

        # Count total
        count_query = f"""
            SELECT COUNT(*) as total FROM user_invitations ui
            WHERE {where_sql}
        """
        count_result = db_manager.execute_query(count_query, tuple(params), fetch_one=True)
        total = count_result['total'] if count_result else 0

        # Get invitations
        invitations_query = f"""
            SELECT
                ui.id,
                ui.email,
                ui.user_type,
                ui.role,
                ui.status,
                ui.expires_at,
                ui.created_at,
                ui.invitation_data,
                u.display_name as invited_by_name,
                u.email as invited_by_email
            FROM user_invitations ui
            LEFT JOIN users u ON ui.invited_by_user_id = u.id
            WHERE {where_sql}
            ORDER BY ui.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([per_page, offset])

        results = db_manager.execute_query(invitations_query, tuple(params), fetch_all=True)

        invitations = []
        for row in (results or []):
            is_expired = row['expires_at'] < datetime.now() if row['expires_at'] else False
            # Extract company_name from invitation_data JSONB field
            invitation_data = row.get('invitation_data') or {}
            company_name = invitation_data.get('company_name') if isinstance(invitation_data, dict) else None
            invitations.append({
                'id': str(row['id']),
                'email': row['email'],
                'user_type': row['user_type'],
                'company_name': company_name,
                'status': 'expired' if is_expired and row['status'] == 'pending' else row['status'],
                'expires_at': row['expires_at'].isoformat() if row['expires_at'] else None,
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'invited_by_name': row['invited_by_name'],
                'invited_by_email': row['invited_by_email']
            })

        return jsonify({
            'success': True,
            'data': {
                'invitations': invitations,
                'total': total,
                'page': page,
                'per_page': per_page
            }
        }), 200

    except Exception as e:
        logger.error(f"List super admin invitations error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching invitations'
        }), 500


@super_admin_bp.route('/invitations/<invitation_id>', methods=['DELETE'])
@require_auth
@require_super_admin
def revoke_super_admin_invitation(invitation_id):
    """
    Revoke a pending super admin invitation.

    Returns:
        {
            "success": true,
            "message": "Invitation revoked successfully"
        }
    """
    try:
        # Check if invitation exists and is a super admin invitation
        check_query = """
            SELECT id, email, status FROM user_invitations
            WHERE id = %s AND tenant_id IS NULL
        """
        check_result = db_manager.execute_query(check_query, (invitation_id,), fetch_one=True)

        if not check_result:
            return jsonify({
                'success': False,
                'error': 'invitation_not_found',
                'message': 'Invitation not found'
            }), 404

        if check_result['status'] != 'pending':
            return jsonify({
                'success': False,
                'error': 'invitation_not_pending',
                'message': f"Cannot revoke invitation with status: {check_result['status']}"
            }), 400

        # Revoke invitation
        revoke_query = "UPDATE user_invitations SET status = 'revoked' WHERE id = %s"
        db_manager.execute_query(revoke_query, (invitation_id,))

        _log_access('revoked_invitation', 'invitations', invitation_id)
        logger.info(f"Super admin invitation revoked: {check_result['email']}")

        return jsonify({
            'success': True,
            'message': 'Invitation revoked successfully'
        }), 200

    except Exception as e:
        logger.error(f"Revoke super admin invitation error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while revoking invitation'
        }), 500


@super_admin_bp.route('/invitations/<invitation_id>/resend', methods=['POST'])
@require_auth
@require_super_admin
def resend_super_admin_invitation(invitation_id):
    """
    Resend a pending super admin invitation email.

    Returns:
        {
            "success": true,
            "message": "Invitation resent successfully"
        }
    """
    try:
        current_user = get_current_user()

        # Get invitation details
        query = """
            SELECT email, user_type, role, invitation_token, status, expires_at
            FROM user_invitations
            WHERE id = %s AND tenant_id IS NULL
        """
        result = db_manager.execute_query(query, (invitation_id,), fetch_one=True)

        if not result:
            return jsonify({
                'success': False,
                'error': 'invitation_not_found',
                'message': 'Invitation not found'
            }), 404

        if result['status'] != 'pending':
            return jsonify({
                'success': False,
                'error': 'invitation_not_pending',
                'message': f"Cannot resend invitation with status: {result['status']}"
            }), 400

        email = result['email']
        user_type = result['user_type']
        invitation_token = result['invitation_token']
        expires_at = result['expires_at']
        company_name = result['role'] if user_type == 'tenant_admin' else None

        # Calculate days until expiry
        days_until_expiry = (expires_at - datetime.now()).days if expires_at else 0

        # Send invitation email
        try:
            email_sent = _send_super_admin_invitation_email(
                to_email=email,
                invitation_token=invitation_token,
                inviter_name=current_user.get('display_name', 'Delta CFO Admin'),
                user_type=user_type,
                company_name=company_name,
                expires_in_days=max(days_until_expiry, 1)
            )
            if not email_sent:
                return jsonify({
                    'success': False,
                    'error': 'email_error',
                    'message': 'Failed to send invitation email'
                }), 500
        except Exception as e:
            logger.error(f"Failed to resend invitation email: {e}")
            return jsonify({
                'success': False,
                'error': 'email_error',
                'message': 'Failed to send invitation email'
            }), 500

        _log_access('resent_invitation', 'invitations', invitation_id)
        logger.info(f"Super admin invitation resent to {email}")

        return jsonify({
            'success': True,
            'message': 'Invitation resent successfully'
        }), 200

    except Exception as e:
        logger.error(f"Resend super admin invitation error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while resending invitation'
        }), 500


def _send_super_admin_invitation_email(
    to_email: str,
    invitation_token: str,
    inviter_name: str,
    user_type: str,
    company_name: str = None,
    expires_in_days: int = 7
) -> bool:
    """
    Send invitation email for Super Admin invitations (CFO or Business Owner).
    """
    import os

    app_base_url = os.getenv('APP_BASE_URL', 'http://localhost:3000')
    invitation_url = f"{app_base_url}/auth/accept-invitation?token={invitation_token}"
    expiry_date = (datetime.now() + timedelta(days=expires_in_days)).strftime('%B %d, %Y')

    # Customize message based on user type
    if user_type == 'fractional_cfo':
        role_display = 'Fractional CFO'
        welcome_message = 'As a Fractional CFO, you will be able to create and manage multiple client companies on the Delta CFO Agent platform.'
        features = [
            'Create and manage multiple client tenants',
            'Access AI-powered financial insights',
            'Generate comprehensive financial reports',
            'Invite and manage your CFO assistants'
        ]
    else:  # tenant_admin
        role_display = 'Business Owner'
        welcome_message = f'You have been invited to set up your company "{company_name}" on the Delta CFO Agent platform.'
        features = [
            'AI-powered transaction classification',
            'Automated invoice and payment matching',
            'Real-time financial dashboards',
            'Comprehensive financial reporting'
        ]

    subject = f"You're invited to join Delta CFO Agent as a {role_display}"

    features_html = '\n'.join([f'<li>{feature}</li>' for feature in features])

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Invitation to Delta CFO Agent</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4F46E5; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background-color: #ffffff; padding: 30px; border: 1px solid #e5e7eb; border-top: none; }}
            .button {{ display: inline-block; padding: 14px 32px; background-color: #4F46E5; color: white; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: bold; }}
            .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }}
            .info-box {{ background-color: #f3f4f6; padding: 20px; border-radius: 6px; margin: 20px 0; }}
            .features {{ margin: 15px 0; padding-left: 20px; }}
            .features li {{ margin: 8px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to Delta CFO Agent</h1>
                <p style="margin: 0; opacity: 0.9;">{role_display} Invitation</p>
            </div>
            <div class="content">
                <p>Hello,</p>
                <p><strong>{inviter_name}</strong> has invited you to join Delta CFO Agent.</p>

                <div class="info-box">
                    <p style="margin: 0 0 10px 0;"><strong>Your Role:</strong> {role_display}</p>
                    <p style="margin: 0;">{welcome_message}</p>
                </div>

                <p><strong>What you'll get access to:</strong></p>
                <ul class="features">
                    {features_html}
                </ul>

                <center>
                    <a href="{invitation_url}" class="button">Accept Invitation</a>
                </center>

                <p style="color: #6b7280; font-size: 14px; margin-top: 20px;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{invitation_url}">{invitation_url}</a>
                </p>

                <p style="color: #ef4444; font-size: 14px; margin-top: 20px;">
                    This invitation expires on {expiry_date}.
                </p>
            </div>
            <div class="footer">
                <p>&copy; 2025 Delta CFO Agent. All rights reserved.</p>
                <p>Powered by AI-driven financial intelligence.</p>
            </div>
        </div>
    </body>
    </html>
    """

    plain_text = f"""
    Welcome to Delta CFO Agent - {role_display} Invitation

    {inviter_name} has invited you to join Delta CFO Agent.

    Your Role: {role_display}
    {welcome_message}

    Accept your invitation by visiting:
    {invitation_url}

    This invitation expires on {expiry_date}.

    - Delta CFO Agent Team
    """

    return email_service.send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
        plain_text_content=plain_text
    )
