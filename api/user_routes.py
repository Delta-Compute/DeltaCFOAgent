"""
User Management API Routes

Provides REST API endpoints for managing users, invitations, and permissions.
"""

import logging
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from middleware.auth_middleware import (
    require_auth,
    require_permission,
    require_role,
    get_current_user,
    get_current_tenant
)
from services.email_service import send_invitation_email
from web_ui.database import db_manager

logger = logging.getLogger(__name__)

user_bp = Blueprint('users', __name__, url_prefix='/api/users')


@user_bp.route('', methods=['GET'])
@require_auth
@require_permission('users.view')
def list_users():
    """
    List all users with access to the current tenant.

    Query Parameters:
        - include_inactive: Include inactive users (default: false)

    Returns:
        {
            "success": true,
            "users": [...]
        }
    """
    try:
        tenant = get_current_tenant()
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'

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
                tu.role,
                tu.permissions,
                tu.added_at,
                tu.is_active as tenant_active
            FROM users u
            JOIN tenant_users tu ON u.id = tu.user_id
            WHERE tu.tenant_id = %s
        """

        params = [tenant['id']]

        if not include_inactive:
            query += " AND u.is_active = true AND tu.is_active = true"

        query += " ORDER BY u.created_at DESC"

        results = db_manager.execute_query(query, params)

        users = []
        for row in results:
            users.append({
                'id': row[0],
                'firebase_uid': row[1],
                'email': row[2],
                'display_name': row[3],
                'user_type': row[4],
                'is_active': row[5],
                'email_verified': row[6],
                'created_at': row[7].isoformat() if row[7] else None,
                'last_login_at': row[8].isoformat() if row[8] else None,
                'role': row[9],
                'permissions': row[10],
                'added_at': row[11].isoformat() if row[11] else None,
                'tenant_active': row[12]
            })

        return jsonify({
            'success': True,
            'users': users
        }), 200

    except Exception as e:
        logger.error(f"List users error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching users'
        }), 500


@user_bp.route('/<user_id>', methods=['GET'])
@require_auth
@require_permission('users.view')
def get_user(user_id):
    """
    Get detailed information about a specific user.

    Returns:
        {
            "success": true,
            "user": {...}
        }
    """
    try:
        tenant = get_current_tenant()

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
                tu.role,
                tu.permissions,
                tu.added_at,
                tu.added_by_user_id
            FROM users u
            JOIN tenant_users tu ON u.id = tu.user_id
            WHERE u.id = %s AND tu.tenant_id = %s
        """

        result = db_manager.execute_query(query, (user_id, tenant['id']))

        if not result or len(result) == 0:
            return jsonify({
                'success': False,
                'error': 'user_not_found',
                'message': 'User not found'
            }), 404

        row = result[0]
        user = {
            'id': row[0],
            'firebase_uid': row[1],
            'email': row[2],
            'display_name': row[3],
            'user_type': row[4],
            'is_active': row[5],
            'email_verified': row[6],
            'created_at': row[7].isoformat() if row[7] else None,
            'last_login_at': row[8].isoformat() if row[8] else None,
            'role': row[9],
            'permissions': row[10],
            'added_at': row[11].isoformat() if row[11] else None,
            'added_by_user_id': row[12]
        }

        return jsonify({
            'success': True,
            'user': user
        }), 200

    except Exception as e:
        logger.error(f"Get user error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred'
        }), 500


@user_bp.route('/invite', methods=['POST'])
@require_auth
@require_permission('users.invite')
def invite_user():
    """
    Invite a new user to the current tenant.

    Request Body:
        {
            "email": "user@example.com",
            "user_type": "employee" | "cfo_assistant" | "fractional_cfo",
            "role": "employee" | "cfo_assistant" | "cfo",
            "permissions": {} (optional)
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
        tenant = get_current_tenant()
        data = request.get_json()

        # Validate required fields
        required_fields = ['email', 'user_type', 'role']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': 'missing_field',
                    'message': f'Missing required field: {field}'
                }), 400

        email = data['email']
        user_type = data['user_type']
        role = data['role']
        permissions = data.get('permissions', {})

        # Validate user type based on current user
        if current_user['user_type'] == 'tenant_admin':
            # Tenant admins can invite employees and fractional CFOs
            if user_type not in ['employee', 'fractional_cfo']:
                return jsonify({
                    'success': False,
                    'error': 'invalid_user_type',
                    'message': 'Tenant admins can only invite employees or fractional CFOs'
                }), 400
        elif current_user['user_type'] == 'fractional_cfo':
            # Fractional CFOs can invite assistants
            if user_type != 'cfo_assistant':
                return jsonify({
                    'success': False,
                    'error': 'invalid_user_type',
                    'message': 'Fractional CFOs can only invite CFO assistants'
                }), 400
        else:
            return jsonify({
                'success': False,
                'error': 'insufficient_permissions',
                'message': 'You do not have permission to invite users'
            }), 403

        # Check if user already exists and has access to this tenant
        existing_query = """
            SELECT u.id FROM users u
            JOIN tenant_users tu ON u.id = tu.user_id
            WHERE u.email = %s AND tu.tenant_id = %s
        """
        existing = db_manager.execute_query(existing_query, (email, tenant['id']))

        if existing and len(existing) > 0:
            return jsonify({
                'success': False,
                'error': 'user_exists',
                'message': 'User already has access to this tenant'
            }), 400

        # Check for pending invitation
        pending_query = """
            SELECT id FROM user_invitations
            WHERE email = %s AND tenant_id = %s AND status = 'pending'
        """
        pending = db_manager.execute_query(pending_query, (email, tenant['id']))

        if pending and len(pending) > 0:
            return jsonify({
                'success': False,
                'error': 'invitation_exists',
                'message': 'A pending invitation already exists for this email'
            }), 400

        # Create invitation
        invitation_id = str(uuid.uuid4())
        invitation_token = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=7)

        insert_query = """
            INSERT INTO user_invitations
            (id, email, invited_by_user_id, tenant_id, user_type, role, invitation_token, status, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s)
            RETURNING id, email, user_type, role, invitation_token, expires_at
        """

        result = db_manager.execute_query(
            insert_query,
            (invitation_id, email, current_user['id'], tenant['id'], user_type, role, invitation_token, expires_at)
        )

        if not result or len(result) == 0:
            return jsonify({
                'success': False,
                'error': 'database_error',
                'message': 'Failed to create invitation'
            }), 500

        inv = result[0]
        invitation = {
            'id': inv[0],
            'email': inv[1],
            'user_type': inv[2],
            'role': inv[3],
            'invitation_token': inv[4],
            'expires_at': inv[5].isoformat() if inv[5] else None
        }

        # Send invitation email
        try:
            send_invitation_email(
                to_email=email,
                invitation_token=invitation_token,
                inviter_name=current_user['display_name'],
                company_name=tenant['company_name'],
                role=role,
                expires_in_days=7
            )
        except Exception as e:
            logger.error(f"Failed to send invitation email: {e}")
            # Don't fail the request if email fails
            pass

        logger.info(f"User invitation created: {email} invited to {tenant['company_name']} by {current_user['email']}")

        return jsonify({
            'success': True,
            'invitation': invitation,
            'message': 'Invitation sent successfully'
        }), 201

    except Exception as e:
        logger.error(f"Invite user error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while sending invitation'
        }), 500


@user_bp.route('/<user_id>', methods=['PUT'])
@require_auth
@require_permission('users.manage')
def update_user(user_id):
    """
    Update user information (display_name, role, permissions).

    Request Body:
        {
            "display_name": "New Name" (optional),
            "role": "new_role" (optional),
            "permissions": {} (optional)
        }

    Returns:
        {
            "success": true,
            "user": {...},
            "message": "User updated successfully"
        }
    """
    try:
        current_user = get_current_user()
        tenant = get_current_tenant()
        data = request.get_json()

        # Check if user exists in this tenant
        check_query = """
            SELECT u.id FROM users u
            JOIN tenant_users tu ON u.id = tu.user_id
            WHERE u.id = %s AND tu.tenant_id = %s
        """
        check_result = db_manager.execute_query(check_query, (user_id, tenant['id']))

        if not check_result or len(check_result) == 0:
            return jsonify({
                'success': False,
                'error': 'user_not_found',
                'message': 'User not found in this tenant'
            }), 404

        # Update display_name if provided
        if 'display_name' in data:
            update_query = "UPDATE users SET display_name = %s WHERE id = %s"
            db_manager.execute_query(update_query, (data['display_name'], user_id))

        # Update role and/or permissions if provided
        if 'role' in data or 'permissions' in data:
            update_parts = []
            params = []

            if 'role' in data:
                update_parts.append("role = %s")
                params.append(data['role'])

            if 'permissions' in data:
                update_parts.append("permissions = %s::jsonb")
                import json
                params.append(json.dumps(data['permissions']))

            params.extend([user_id, tenant['id']])

            update_query = f"""
                UPDATE tenant_users
                SET {', '.join(update_parts)}
                WHERE user_id = %s AND tenant_id = %s
            """
            db_manager.execute_query(update_query, params)

        # Log the action
        logger.info(f"User {user_id} updated by {current_user['email']} in tenant {tenant['company_name']}")

        # Get updated user info
        get_query = """
            SELECT
                u.id, u.email, u.display_name, u.user_type,
                tu.role, tu.permissions
            FROM users u
            JOIN tenant_users tu ON u.id = tu.user_id
            WHERE u.id = %s AND tu.tenant_id = %s
        """
        result = db_manager.execute_query(get_query, (user_id, tenant['id']))

        if result and len(result) > 0:
            row = result[0]
            user = {
                'id': row[0],
                'email': row[1],
                'display_name': row[2],
                'user_type': row[3],
                'role': row[4],
                'permissions': row[5]
            }
        else:
            user = None

        return jsonify({
            'success': True,
            'user': user,
            'message': 'User updated successfully'
        }), 200

    except Exception as e:
        logger.error(f"Update user error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while updating user'
        }), 500


@user_bp.route('/<user_id>', methods=['DELETE'])
@require_auth
@require_permission('users.manage')
def deactivate_user(user_id):
    """
    Deactivate a user (soft delete).

    Returns:
        {
            "success": true,
            "message": "User deactivated successfully"
        }
    """
    try:
        current_user = get_current_user()
        tenant = get_current_tenant()

        # Cannot deactivate yourself
        if user_id == current_user['id']:
            return jsonify({
                'success': False,
                'error': 'cannot_deactivate_self',
                'message': 'You cannot deactivate your own account'
            }), 400

        # Check if user exists in this tenant
        check_query = """
            SELECT u.id, u.email FROM users u
            JOIN tenant_users tu ON u.id = tu.user_id
            WHERE u.id = %s AND tu.tenant_id = %s
        """
        check_result = db_manager.execute_query(check_query, (user_id, tenant['id']))

        if not check_result or len(check_result) == 0:
            return jsonify({
                'success': False,
                'error': 'user_not_found',
                'message': 'User not found in this tenant'
            }), 404

        user_email = check_result[0][1]

        # Deactivate user in tenant_users
        deactivate_query = """
            UPDATE tenant_users
            SET is_active = false, removed_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND tenant_id = %s
        """
        db_manager.execute_query(deactivate_query, (user_id, tenant['id']))

        logger.info(f"User {user_email} deactivated by {current_user['email']} in tenant {tenant['company_name']}")

        return jsonify({
            'success': True,
            'message': 'User deactivated successfully'
        }), 200

    except Exception as e:
        logger.error(f"Deactivate user error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while deactivating user'
        }), 500


@user_bp.route('/invitations', methods=['GET'])
@require_auth
@require_permission('users.view')
def list_invitations():
    """
    List all pending invitations for the current tenant.

    Returns:
        {
            "success": true,
            "invitations": [...]
        }
    """
    try:
        tenant = get_current_tenant()

        query = """
            SELECT
                ui.id,
                ui.email,
                ui.user_type,
                ui.role,
                ui.status,
                ui.sent_at,
                ui.expires_at,
                u.display_name as invited_by_name
            FROM user_invitations ui
            JOIN users u ON ui.invited_by_user_id = u.id
            WHERE ui.tenant_id = %s
            ORDER BY ui.sent_at DESC
        """

        results = db_manager.execute_query(query, (tenant['id'],))

        invitations = []
        for row in results:
            invitations.append({
                'id': row[0],
                'email': row[1],
                'user_type': row[2],
                'role': row[3],
                'status': row[4],
                'sent_at': row[5].isoformat() if row[5] else None,
                'expires_at': row[6].isoformat() if row[6] else None,
                'invited_by_name': row[7],
                'is_expired': row[6] < datetime.now() if row[6] else False
            })

        return jsonify({
            'success': True,
            'invitations': invitations
        }), 200

    except Exception as e:
        logger.error(f"List invitations error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching invitations'
        }), 500


@user_bp.route('/invitations/<invitation_id>', methods=['DELETE'])
@require_auth
@require_permission('users.manage')
def revoke_invitation(invitation_id):
    """
    Revoke a pending invitation.

    Returns:
        {
            "success": true,
            "message": "Invitation revoked successfully"
        }
    """
    try:
        tenant = get_current_tenant()

        # Check if invitation exists and belongs to this tenant
        check_query = """
            SELECT id, status FROM user_invitations
            WHERE id = %s AND tenant_id = %s
        """
        check_result = db_manager.execute_query(check_query, (invitation_id, tenant['id']))

        if not check_result or len(check_result) == 0:
            return jsonify({
                'success': False,
                'error': 'invitation_not_found',
                'message': 'Invitation not found'
            }), 404

        status = check_result[0][1]

        if status != 'pending':
            return jsonify({
                'success': False,
                'error': 'invitation_not_pending',
                'message': f'Cannot revoke invitation with status: {status}'
            }), 400

        # Revoke invitation
        revoke_query = "UPDATE user_invitations SET status = 'revoked' WHERE id = %s"
        db_manager.execute_query(revoke_query, (invitation_id,))

        logger.info(f"Invitation {invitation_id} revoked in tenant {tenant['company_name']}")

        return jsonify({
            'success': True,
            'message': 'Invitation revoked successfully'
        }), 200

    except Exception as e:
        logger.error(f"Revoke invitation error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while revoking invitation'
        }), 500


@user_bp.route('/invitations/<invitation_id>/resend', methods=['POST'])
@require_auth
@require_permission('users.invite')
def resend_invitation(invitation_id):
    """
    Resend a pending invitation email.

    Returns:
        {
            "success": true,
            "message": "Invitation resent successfully"
        }
    """
    try:
        current_user = get_current_user()
        tenant = get_current_tenant()

        # Get invitation details
        query = """
            SELECT email, user_type, role, invitation_token, status, expires_at
            FROM user_invitations
            WHERE id = %s AND tenant_id = %s
        """
        result = db_manager.execute_query(query, (invitation_id, tenant['id']))

        if not result or len(result) == 0:
            return jsonify({
                'success': False,
                'error': 'invitation_not_found',
                'message': 'Invitation not found'
            }), 404

        inv = result[0]
        email = inv[0]
        user_type = inv[1]
        role = inv[2]
        invitation_token = inv[3]
        status = inv[4]
        expires_at = inv[5]

        if status != 'pending':
            return jsonify({
                'success': False,
                'error': 'invitation_not_pending',
                'message': f'Cannot resend invitation with status: {status}'
            }), 400

        # Calculate days until expiry
        days_until_expiry = (expires_at - datetime.now()).days if expires_at else 0

        # Send invitation email
        try:
            send_invitation_email(
                to_email=email,
                invitation_token=invitation_token,
                inviter_name=current_user['display_name'],
                company_name=tenant['company_name'],
                role=role,
                expires_in_days=max(days_until_expiry, 1)
            )
        except Exception as e:
            logger.error(f"Failed to resend invitation email: {e}")
            return jsonify({
                'success': False,
                'error': 'email_error',
                'message': 'Failed to send invitation email'
            }), 500

        logger.info(f"Invitation resent to {email} for tenant {tenant['company_name']}")

        return jsonify({
            'success': True,
            'message': 'Invitation resent successfully'
        }), 200

    except Exception as e:
        logger.error(f"Resend invitation error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while resending invitation'
        }), 500
