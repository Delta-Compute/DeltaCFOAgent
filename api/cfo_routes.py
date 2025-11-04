"""
CFO-Specific API Routes

Provides REST API endpoints for Fractional CFO features like managing clients and assistants.
"""

import logging
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from middleware.auth_middleware import require_auth, require_user_type, get_current_user
from services.email_service import send_invitation_email
from web_ui.database import db_manager

logger = logging.getLogger(__name__)

cfo_bp = Blueprint('cfo', __name__, url_prefix='/api/cfo')


@cfo_bp.route('/clients', methods=['GET'])
@require_auth
@require_user_type(['fractional_cfo'])
def list_clients():
    """
    List all clients (tenants) for the current CFO.

    Returns:
        {
            "success": true,
            "clients": [...]
        }
    """
    try:
        user = get_current_user()

        query = """
            SELECT
                tc.id,
                tc.company_name,
                tc.description,
                tc.payment_owner,
                tc.subscription_status,
                tu.role,
                u_admin.display_name as admin_name,
                u_admin.email as admin_email,
                tc.created_at,
                (SELECT COUNT(*) FROM tenant_users WHERE tenant_id = tc.id AND is_active = true) as user_count,
                (SELECT MAX(last_login_at) FROM users u2
                 JOIN tenant_users tu2 ON u2.id = tu2.user_id
                 WHERE tu2.tenant_id = tc.id) as last_activity
            FROM tenant_configuration tc
            JOIN tenant_users tu ON tc.id = tu.tenant_id
            LEFT JOIN users u_admin ON tc.current_admin_user_id = u_admin.id
            WHERE tu.user_id = %s AND tu.is_active = true
            ORDER BY tc.company_name
        """

        results = db_manager.execute_query(query, (user['id'],))

        clients = []
        for row in results:
            clients.append({
                'id': row[0],
                'company_name': row[1],
                'description': row[2],
                'payment_owner': row[3],
                'subscription_status': row[4],
                'role': row[5],
                'admin_name': row[6],
                'admin_email': row[7],
                'created_at': row[8].isoformat() if row[8] else None,
                'user_count': row[9],
                'last_activity': row[10].isoformat() if row[10] else None
            })

        return jsonify({
            'success': True,
            'clients': clients
        }), 200

    except Exception as e:
        logger.error(f"List clients error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching clients'
        }), 500


@cfo_bp.route('/assistants', methods=['GET'])
@require_auth
@require_user_type(['fractional_cfo'])
def list_assistants():
    """
    List all assistants for the current CFO.

    Returns:
        {
            "success": true,
            "assistants": [...]
        }
    """
    try:
        user = get_current_user()

        query = """
            SELECT DISTINCT
                u.id,
                u.email,
                u.display_name,
                u.is_active,
                u.created_at,
                u.last_login_at,
                ARRAY_AGG(DISTINCT tc.company_name) as client_names,
                ARRAY_AGG(DISTINCT tc.tenant_id) as client_ids
            FROM users u
            JOIN tenant_users tu ON u.id = tu.user_id
            JOIN tenant_configuration tc ON tu.tenant_id = tc.id
            WHERE u.user_type = 'cfo_assistant'
            AND u.invited_by_user_id = %s
            AND tu.is_active = true
            GROUP BY u.id, u.email, u.display_name, u.is_active, u.created_at, u.last_login_at
            ORDER BY u.display_name
        """

        results = db_manager.execute_query(query, (user['id'],))

        assistants = []
        for row in results:
            assistants.append({
                'id': row[0],
                'email': row[1],
                'display_name': row[2],
                'is_active': row[3],
                'created_at': row[4].isoformat() if row[4] else None,
                'last_login_at': row[5].isoformat() if row[5] else None,
                'client_names': row[6] if row[6] else [],
                'client_ids': row[7] if row[7] else [],
                'client_count': len(row[6]) if row[6] else 0
            })

        return jsonify({
            'success': True,
            'assistants': assistants
        }), 200

    except Exception as e:
        logger.error(f"List assistants error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching assistants'
        }), 500


@cfo_bp.route('/assistants/invite', methods=['POST'])
@require_auth
@require_user_type(['fractional_cfo'])
def invite_assistant():
    """
    Invite a CFO assistant and grant access to specified clients.

    Request Body:
        {
            "email": "assistant@example.com",
            "display_name": "Assistant Name",
            "client_ids": ["client_id_1", "client_id_2"]
        }

    Returns:
        {
            "success": true,
            "invitations": [...],
            "message": "Assistant invited successfully"
        }
    """
    try:
        user = get_current_user()
        data = request.get_json()

        # Validate required fields
        required_fields = ['email', 'client_ids']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': 'missing_field',
                    'message': f'Missing required field: {field}'
                }), 400

        email = data['email']
        client_ids = data['client_ids']

        if not isinstance(client_ids, list) or len(client_ids) == 0:
            return jsonify({
                'success': False,
                'error': 'invalid_client_ids',
                'message': 'client_ids must be a non-empty array'
            }), 400

        # Verify CFO has access to all specified clients
        verify_query = """
            SELECT COUNT(*) FROM tenant_users
            WHERE user_id = %s AND tenant_id = ANY(%s) AND is_active = true
        """
        verify_result = db_manager.execute_query(verify_query, (user['id'], client_ids))

        if not verify_result or verify_result[0][0] != len(client_ids):
            return jsonify({
                'success': False,
                'error': 'invalid_clients',
                'message': 'You do not have access to all specified clients'
            }), 403

        # Create invitations for each client
        invitations = []

        for client_id in client_ids:
            # Check if invitation already exists
            existing_query = """
                SELECT id FROM user_invitations
                WHERE email = %s AND tenant_id = %s AND status = 'pending'
            """
            existing = db_manager.execute_query(existing_query, (email, client_id))

            if existing and len(existing) > 0:
                continue  # Skip if invitation already exists

            # Get client name
            client_query = "SELECT company_name FROM tenant_configuration WHERE id = %s"
            client_result = db_manager.execute_query(client_query, (client_id,))
            company_name = client_result[0][0] if client_result else "Client"

            # Create invitation
            invitation_id = str(uuid.uuid4())
            invitation_token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(days=7)

            insert_query = """
                INSERT INTO user_invitations
                (id, email, invited_by_user_id, tenant_id, user_type, role, invitation_token, status, expires_at)
                VALUES (%s, %s, %s, %s, 'cfo_assistant', 'cfo_assistant', %s, 'pending', %s)
                RETURNING id, email, tenant_id, invitation_token
            """

            result = db_manager.execute_query(
                insert_query,
                (invitation_id, email, user['id'], client_id, invitation_token, expires_at)
            )

            if result and len(result) > 0:
                inv = result[0]
                invitations.append({
                    'id': inv[0],
                    'email': inv[1],
                    'tenant_id': inv[2],
                    'invitation_token': inv[3],
                    'company_name': company_name
                })

                # Send invitation email
                try:
                    send_invitation_email(
                        to_email=email,
                        invitation_token=invitation_token,
                        inviter_name=user['display_name'],
                        company_name=company_name,
                        role='CFO Assistant',
                        expires_in_days=7
                    )
                except Exception as e:
                    logger.warning(f"Failed to send invitation email: {e}")

        logger.info(f"CFO {user['email']} invited assistant {email} to {len(invitations)} clients")

        return jsonify({
            'success': True,
            'invitations': invitations,
            'message': f'Assistant invited to {len(invitations)} client(s) successfully'
        }), 201

    except Exception as e:
        logger.error(f"Invite assistant error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while inviting assistant'
        }), 500


@cfo_bp.route('/assistants/<assistant_id>/clients', methods=['PUT'])
@require_auth
@require_user_type(['fractional_cfo'])
def update_assistant_clients(assistant_id):
    """
    Update which clients an assistant has access to.

    Request Body:
        {
            "client_ids": ["client_id_1", "client_id_2"]
        }

    Returns:
        {
            "success": true,
            "message": "Assistant access updated successfully"
        }
    """
    try:
        user = get_current_user()
        data = request.get_json()

        client_ids = data.get('client_ids', [])

        # Verify assistant exists and was invited by current CFO
        assistant_query = """
            SELECT id FROM users
            WHERE id = %s AND user_type = 'cfo_assistant' AND invited_by_user_id = %s
        """
        assistant_result = db_manager.execute_query(assistant_query, (assistant_id, user['id']))

        if not assistant_result or len(assistant_result) == 0:
            return jsonify({
                'success': False,
                'error': 'assistant_not_found',
                'message': 'Assistant not found or not managed by you'
            }), 404

        # Verify CFO has access to all specified clients
        if client_ids:
            verify_query = """
                SELECT COUNT(*) FROM tenant_users
                WHERE user_id = %s AND tenant_id = ANY(%s) AND is_active = true
            """
            verify_result = db_manager.execute_query(verify_query, (user['id'], client_ids))

            if not verify_result or verify_result[0][0] != len(client_ids):
                return jsonify({
                    'success': False,
                    'error': 'invalid_clients',
                    'message': 'You do not have access to all specified clients'
                }), 403

        # Get current assistant client access
        current_query = """
            SELECT tenant_id FROM tenant_users
            WHERE user_id = %s AND is_active = true
        """
        current_result = db_manager.execute_query(current_query, (assistant_id,))
        current_client_ids = [row[0] for row in current_result] if current_result else []

        # Deactivate access to clients not in new list
        clients_to_remove = set(current_client_ids) - set(client_ids)
        if clients_to_remove:
            deactivate_query = """
                UPDATE tenant_users
                SET is_active = false, removed_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND tenant_id = ANY(%s)
            """
            db_manager.execute_query(deactivate_query, (assistant_id, list(clients_to_remove)))

        # Add access to new clients
        clients_to_add = set(client_ids) - set(current_client_ids)
        for client_id in clients_to_add:
            tenant_user_id = str(uuid.uuid4())
            add_query = """
                INSERT INTO tenant_users (id, user_id, tenant_id, role, permissions, is_active, added_by_user_id)
                VALUES (%s, %s, %s, 'cfo_assistant', '{}', true, %s)
                ON CONFLICT (user_id, tenant_id) DO UPDATE
                SET is_active = true, removed_at = NULL
            """
            db_manager.execute_query(add_query, (tenant_user_id, assistant_id, client_id, user['id']))

        logger.info(f"CFO {user['email']} updated assistant {assistant_id} client access")

        return jsonify({
            'success': True,
            'message': 'Assistant access updated successfully'
        }), 200

    except Exception as e:
        logger.error(f"Update assistant clients error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while updating assistant access'
        }), 500


@cfo_bp.route('/stats', methods=['GET'])
@require_auth
@require_user_type(['fractional_cfo'])
def get_cfo_stats():
    """
    Get CFO dashboard statistics.

    Returns:
        {
            "success": true,
            "stats": {
                "total_clients": 10,
                "active_clients": 8,
                "total_assistants": 3,
                "total_users": 50
            }
        }
    """
    try:
        user = get_current_user()

        # Total clients
        clients_query = """
            SELECT COUNT(DISTINCT tc.id)
            FROM tenant_configuration tc
            JOIN tenant_users tu ON tc.id = tu.tenant_id
            WHERE tu.user_id = %s AND tu.is_active = true
        """
        clients_result = db_manager.execute_query(clients_query, (user['id'],))
        total_clients = clients_result[0][0] if clients_result else 0

        # Active clients (logged in within last 30 days)
        active_query = """
            SELECT COUNT(DISTINCT tc.id)
            FROM tenant_configuration tc
            JOIN tenant_users tu ON tc.id = tu.tenant_id
            JOIN users u ON tu.user_id = u.id
            WHERE tu.tenant_id IN (
                SELECT tenant_id FROM tenant_users WHERE user_id = %s AND is_active = true
            )
            AND u.last_login_at > NOW() - INTERVAL '30 days'
        """
        active_result = db_manager.execute_query(active_query, (user['id'],))
        active_clients = active_result[0][0] if active_result else 0

        # Total assistants
        assistants_query = """
            SELECT COUNT(DISTINCT id)
            FROM users
            WHERE user_type = 'cfo_assistant' AND invited_by_user_id = %s AND is_active = true
        """
        assistants_result = db_manager.execute_query(assistants_query, (user['id'],))
        total_assistants = assistants_result[0][0] if assistants_result else 0

        # Total users across all clients
        users_query = """
            SELECT COUNT(DISTINCT u.id)
            FROM users u
            JOIN tenant_users tu ON u.id = tu.user_id
            WHERE tu.tenant_id IN (
                SELECT tenant_id FROM tenant_users WHERE user_id = %s AND is_active = true
            )
            AND tu.is_active = true
        """
        users_result = db_manager.execute_query(users_query, (user['id'],))
        total_users = users_result[0][0] if users_result else 0

        stats = {
            'total_clients': total_clients,
            'active_clients': active_clients,
            'total_assistants': total_assistants,
            'total_users': total_users
        }

        return jsonify({
            'success': True,
            'stats': stats
        }), 200

    except Exception as e:
        logger.error(f"Get CFO stats error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching statistics'
        }), 500
