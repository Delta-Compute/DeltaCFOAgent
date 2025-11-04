"""
Tenant Management API Routes

Provides REST API endpoints for managing tenants, admin transfers, and payment settings.
"""

import logging
import uuid
from flask import Blueprint, request, jsonify, session
from middleware.auth_middleware import (
    require_auth,
    require_role,
    require_user_type,
    get_current_user,
    get_current_tenant
)
from services.email_service import send_admin_transfer_notification, send_invitation_email
from datetime import timedelta
from web_ui.database import db_manager
from web_ui.tenant_context import set_tenant_id

logger = logging.getLogger(__name__)

tenant_bp = Blueprint('tenants', __name__, url_prefix='/api/tenants')


@tenant_bp.route('', methods=['GET'])
@require_auth
def list_tenants():
    """
    List all tenants the current user has access to.

    Returns:
        {
            "success": true,
            "tenants": [...]
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
                tu.permissions,
                u_created.display_name as created_by_name,
                u_admin.display_name as admin_name
            FROM tenant_configuration tc
            JOIN tenant_users tu ON tc.id = tu.tenant_id
            LEFT JOIN users u_created ON tc.created_by_user_id = u_created.id
            LEFT JOIN users u_admin ON tc.current_admin_user_id = u_admin.id
            WHERE tu.user_id = %s AND tu.is_active = true
            ORDER BY tc.company_name
        """

        results = db_manager.execute_query(query, (user['id'],))

        tenants = []
        for row in results:
            tenants.append({
                'id': row[0],
                'company_name': row[1],
                'description': row[2],
                'payment_owner': row[3],
                'subscription_status': row[4],
                'role': row[5],
                'permissions': row[6],
                'created_by_name': row[7],
                'admin_name': row[8]
            })

        return jsonify({
            'success': True,
            'tenants': tenants
        }), 200

    except Exception as e:
        logger.error(f"List tenants error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while fetching tenants'
        }), 500


@tenant_bp.route('', methods=['POST'])
@require_auth
@require_user_type(['fractional_cfo', 'tenant_admin'])
def create_tenant():
    """
    Create a new tenant (Fractional CFO or Tenant Admin).

    Request Body:
        {
            "company_name": "Company Name",
            "description": "Company description" (optional),
            "admin_email": "admin@company.com" (optional)
        }

    Returns:
        {
            "success": true,
            "tenant": {...},
            "message": "Tenant created successfully"
        }
    """
    try:
        user = get_current_user()
        data = request.get_json()

        if not data.get('company_name'):
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'company_name is required'
            }), 400

        company_name = data['company_name']
        description = data.get('description', '')
        admin_email = data.get('admin_email')

        # Generate tenant ID
        tenant_id = str(uuid.uuid4())[:8]  # Short ID for tenant

        # Create tenant
        create_tenant_query = """
            INSERT INTO tenant_configuration
            (tenant_id, company_name, company_description, created_by_user_id, current_admin_user_id, payment_owner, subscription_status)
            VALUES (%s, %s, %s, %s, %s, 'cfo', 'trial')
            RETURNING tenant_id, company_name, company_description
        """

        # Use direct connection to get RETURNING values
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    create_tenant_query,
                    (tenant_id, company_name, description, user['id'], user['id'])
                )
                tenant_data = cursor.fetchone()
                conn.commit()

                if not tenant_data:
                    return jsonify({
                        'success': False,
                        'error': 'database_error',
                        'message': 'Failed to create tenant'
                    }), 500
            except Exception as e:
                conn.rollback()
                logger.error(f"Create tenant error: {e}")
                return jsonify({
                    'success': False,
                    'error': 'database_error',
                    'message': str(e)
                }), 500
            finally:
                cursor.close()

        # Add CFO as owner in tenant_users
        tenant_user_id = str(uuid.uuid4())
        link_query = """
            INSERT INTO tenant_users (id, user_id, tenant_id, role, permissions, is_active, added_by_user_id)
            VALUES (%s, %s, %s, 'owner', '{}', true, %s)
        """
        db_manager.execute_query(
            link_query,
            (tenant_user_id, user['id'], tenant_id, user['id'])
        )

        tenant = {
            'id': tenant_data[0],
            'company_name': tenant_data[1],
            'description': tenant_data[2],
            'role': 'owner',
            'payment_owner': 'cfo',
            'subscription_status': 'trial'
        }

        # Send invitation to admin if email provided
        if admin_email:
            try:
                from datetime import datetime
                invitation_id = str(uuid.uuid4())
                invitation_token = str(uuid.uuid4())
                expires_at = datetime.now() + timedelta(days=7)

                inv_query = """
                    INSERT INTO user_invitations
                    (id, email, invited_by_user_id, tenant_id, user_type, role, invitation_token, status, expires_at)
                    VALUES (%s, %s, %s, %s, 'tenant_admin', 'admin', %s, 'pending', %s)
                """
                db_manager.execute_query(
                    inv_query,
                    (invitation_id, admin_email, user['id'], tenant_id, invitation_token, expires_at)
                )

                send_invitation_email(
                    to_email=admin_email,
                    invitation_token=invitation_token,
                    inviter_name=user['display_name'],
                    company_name=company_name,
                    role='admin',
                    expires_in_days=7
                )
            except Exception as e:
                logger.warning(f"Failed to send admin invitation: {e}")

        # Automatically switch to the new tenant
        # This ensures both session keys are synchronized
        set_tenant_id(tenant_id)
        session['current_tenant_id'] = tenant_id

        logger.info(f"Tenant created: {company_name} by {user['email']}")

        return jsonify({
            'success': True,
            'tenant': tenant,
            'message': 'Tenant created successfully'
        }), 201

    except Exception as e:
        logger.error(f"Create tenant error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while creating tenant'
        }), 500


@tenant_bp.route('/<tenant_id>', methods=['GET'])
@require_auth
def get_tenant(tenant_id):
    """
    Get detailed tenant information.

    Returns:
        {
            "success": true,
            "tenant": {...}
        }
    """
    try:
        user = get_current_user()

        # Check user has access
        access_query = """
            SELECT COUNT(*) FROM tenant_users
            WHERE user_id = %s AND tenant_id = %s AND is_active = true
        """
        access_result = db_manager.execute_query(access_query, (user['id'], tenant_id))

        if not access_result or access_result[0][0] == 0:
            return jsonify({
                'success': False,
                'error': 'access_denied',
                'message': 'You do not have access to this tenant'
            }), 403

        query = """
            SELECT
                tc.id,
                tc.company_name,
                tc.description,
                tc.payment_owner,
                tc.payment_method_id,
                tc.subscription_status,
                u_created.display_name as created_by_name,
                u_admin.display_name as admin_name,
                u_admin.email as admin_email
            FROM tenant_configuration tc
            LEFT JOIN users u_created ON tc.created_by_user_id = u_created.id
            LEFT JOIN users u_admin ON tc.current_admin_user_id = u_admin.id
            WHERE tc.id = %s
        """

        result = db_manager.execute_query(query, (tenant_id,))

        if not result or len(result) == 0:
            return jsonify({
                'success': False,
                'error': 'tenant_not_found',
                'message': 'Tenant not found'
            }), 404

        row = result[0]
        tenant = {
            'id': row[0],
            'company_name': row[1],
            'description': row[2],
            'payment_owner': row[3],
            'has_payment_method': row[4] is not None,
            'subscription_status': row[5],
            'created_by_name': row[6],
            'admin_name': row[7],
            'admin_email': row[8]
        }

        return jsonify({
            'success': True,
            'tenant': tenant
        }), 200

    except Exception as e:
        logger.error(f"Get tenant error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred'
        }), 500


@tenant_bp.route('/<tenant_id>', methods=['PUT'])
@require_auth
@require_role(['owner', 'admin'])
def update_tenant(tenant_id):
    """
    Update tenant settings.

    Request Body:
        {
            "company_name": "New Name" (optional),
            "description": "New Description" (optional)
        }

    Returns:
        {
            "success": true,
            "tenant": {...},
            "message": "Tenant updated successfully"
        }
    """
    try:
        user = get_current_user()
        data = request.get_json()

        # Verify user has access and is admin/owner
        check_query = """
            SELECT role FROM tenant_users
            WHERE user_id = %s AND tenant_id = %s AND is_active = true
        """
        check_result = db_manager.execute_query(check_query, (user['id'], tenant_id))

        if not check_result or check_result[0][0] not in ['owner', 'admin']:
            return jsonify({
                'success': False,
                'error': 'insufficient_permissions',
                'message': 'Only owners and admins can update tenant settings'
            }), 403

        update_parts = []
        params = []

        if 'company_name' in data:
            update_parts.append("company_name = %s")
            params.append(data['company_name'])

        if 'description' in data:
            update_parts.append("description = %s")
            params.append(data['description'])

        if not update_parts:
            return jsonify({
                'success': False,
                'error': 'no_updates',
                'message': 'No fields to update'
            }), 400

        params.append(tenant_id)

        update_query = f"""
            UPDATE tenant_configuration
            SET {', '.join(update_parts)}
            WHERE id = %s
            RETURNING id, company_name, description
        """

        result = db_manager.execute_query(update_query, params)

        if result and len(result) > 0:
            row = result[0]
            tenant = {
                'id': row[0],
                'company_name': row[1],
                'description': row[2]
            }
        else:
            tenant = None

        logger.info(f"Tenant {tenant_id} updated by {user['email']}")

        return jsonify({
            'success': True,
            'tenant': tenant,
            'message': 'Tenant updated successfully'
        }), 200

    except Exception as e:
        logger.error(f"Update tenant error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while updating tenant'
        }), 500


@tenant_bp.route('/<tenant_id>/transfer-admin', methods=['POST'])
@require_auth
@require_role(['owner'])
def transfer_admin(tenant_id):
    """
    Transfer admin role to another user (Owner only).

    Request Body:
        {
            "new_admin_user_id": "user_uuid"
        }

    Returns:
        {
            "success": true,
            "message": "Admin role transferred successfully"
        }
    """
    try:
        user = get_current_user()
        data = request.get_json()

        new_admin_user_id = data.get('new_admin_user_id')
        if not new_admin_user_id:
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'new_admin_user_id is required'
            }), 400

        # Check new admin has access to tenant
        check_query = """
            SELECT u.email, u.display_name
            FROM users u
            JOIN tenant_users tu ON u.id = tu.user_id
            WHERE u.id = %s AND tu.tenant_id = %s AND tu.is_active = true
        """
        check_result = db_manager.execute_query(check_query, (new_admin_user_id, tenant_id))

        if not check_result or len(check_result) == 0:
            return jsonify({
                'success': False,
                'error': 'user_not_found',
                'message': 'New admin user not found in this tenant'
            }), 404

        new_admin_email = check_result[0][0]
        new_admin_name = check_result[0][1]

        # Update tenant_configuration
        update_tenant_query = """
            UPDATE tenant_configuration
            SET current_admin_user_id = %s
            WHERE id = %s
        """
        db_manager.execute_query(update_tenant_query, (new_admin_user_id, tenant_id))

        # Update new admin role to 'admin'
        update_role_query = """
            UPDATE tenant_users
            SET role = 'admin'
            WHERE user_id = %s AND tenant_id = %s
        """
        db_manager.execute_query(update_role_query, (new_admin_user_id, tenant_id))

        # Get tenant name for email
        tenant_query = "SELECT company_name FROM tenant_configuration WHERE id = %s"
        tenant_result = db_manager.execute_query(tenant_query, (tenant_id,))
        company_name = tenant_result[0][0] if tenant_result else "your company"

        # Send notification email
        try:
            send_admin_transfer_notification(
                to_email=new_admin_email,
                new_admin_name=new_admin_name,
                company_name=company_name,
                transferred_by_name=user['display_name']
            )
        except Exception as e:
            logger.warning(f"Failed to send admin transfer email: {e}")

        logger.info(f"Admin role transferred in tenant {tenant_id} from {user['email']} to {new_admin_email}")

        return jsonify({
            'success': True,
            'message': 'Admin role transferred successfully'
        }), 200

    except Exception as e:
        logger.error(f"Transfer admin error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while transferring admin role'
        }), 500


@tenant_bp.route('/<tenant_id>/payment-method', methods=['PUT'])
@require_auth
@require_role(['owner', 'admin'])
def update_payment_method(tenant_id):
    """
    Add or update payment method (placeholder for future Stripe integration).

    Request Body:
        {
            "payment_method_id": "pm_xxxxx"
        }

    Returns:
        {
            "success": true,
            "message": "Payment method updated successfully"
        }
    """
    try:
        user = get_current_user()
        data = request.get_json()

        payment_method_id = data.get('payment_method_id')
        if not payment_method_id:
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'payment_method_id is required'
            }), 400

        # Update payment method and change ownership to tenant
        update_query = """
            UPDATE tenant_configuration
            SET payment_method_id = %s, payment_owner = 'tenant'
            WHERE id = %s
        """
        db_manager.execute_query(update_query, (payment_method_id, tenant_id))

        logger.info(f"Payment method updated for tenant {tenant_id} by {user['email']}")

        return jsonify({
            'success': True,
            'message': 'Payment method updated successfully'
        }), 200

    except Exception as e:
        logger.error(f"Update payment method error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred while updating payment method'
        }), 500
