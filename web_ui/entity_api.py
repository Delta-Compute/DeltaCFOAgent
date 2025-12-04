#!/usr/bin/env python3
"""
Entity and Business Line Management API
Handles CRUD operations for entities (legal entities) and business lines (profit centers)

Author: Claude Code
Date: 2024-11-24
"""

import logging
from typing import Dict, Any, List, Optional
from flask import Blueprint, jsonify, request
from datetime import datetime
import uuid

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
entity_bp = Blueprint('entities', __name__, url_prefix='/api/entities')
business_line_bp = Blueprint('business_lines', __name__, url_prefix='/api/business-lines')


def register_entity_routes(app):
    """Register entity and business line routes with Flask app"""
    app.register_blueprint(entity_bp)
    app.register_blueprint(business_line_bp)


# ============================================================================
# ENTITY MANAGEMENT ENDPOINTS
# ============================================================================

@entity_bp.route('', methods=['GET'])
def list_entities():
    """
    List all entities for the current tenant

    Query params:
        - include_inactive: Include inactive entities (default: false)
        - include_stats: Include statistics for each entity (default: false)

    Returns:
        {
            "success": true,
            "entities": [
                {
                    "id": "uuid",
                    "tenant_id": "delta",
                    "code": "DLLC",
                    "name": "Delta Mining LLC",
                    "legal_name": "Delta Mining LLC",
                    "tax_id": "XX-XXXXXXX",
                    "tax_jurisdiction": "US-Delaware",
                    "entity_type": "LLC",
                    "base_currency": "USD",
                    "fiscal_year_end": "12-31",
                    "country_code": "US",
                    "is_active": true,
                    "incorporation_date": "2020-01-01",
                    "created_at": "2024-11-24T...",
                    "updated_at": "2024-11-24T...",
                    "business_lines_count": 3,  // if include_stats=true
                    "transactions_count": 1250  // if include_stats=true
                }
            ],
            "count": 5
        }
    """
    try:
        from database import db_manager
        from tenant_context import get_current_tenant_id

        # Get tenant (required)
        tenant_id = get_current_tenant_id(strict=True)

        # Get query params
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        include_stats = request.args.get('include_stats', 'false').lower() == 'true'

        # Build query
        if include_stats:
            query = """
            SELECT
                e.id, e.tenant_id, e.code, e.name, e.legal_name,
                e.tax_id, e.tax_jurisdiction, e.entity_type,
                e.base_currency, e.fiscal_year_end, e.address,
                e.country_code, e.is_active, e.incorporation_date,
                e.created_at, e.updated_at, e.created_by,
                COUNT(DISTINCT bl.id) as business_lines_count,
                COUNT(DISTINCT t.id) as transactions_count
            FROM entities e
            LEFT JOIN business_lines bl ON e.id = bl.entity_id
            LEFT JOIN transactions t ON e.id = t.entity_id
            WHERE e.tenant_id = %s
            """
            if not include_inactive:
                query += " AND e.is_active = TRUE"
            query += """
            GROUP BY e.id, e.tenant_id, e.code, e.name, e.legal_name,
                     e.tax_id, e.tax_jurisdiction, e.entity_type,
                     e.base_currency, e.fiscal_year_end, e.address,
                     e.country_code, e.is_active, e.incorporation_date,
                     e.created_at, e.updated_at, e.created_by
            ORDER BY e.name
            """
        else:
            query = """
            SELECT
                id, tenant_id, code, name, legal_name,
                tax_id, tax_jurisdiction, entity_type,
                base_currency, fiscal_year_end, address,
                country_code, is_active, incorporation_date,
                created_at, updated_at, created_by
            FROM entities
            WHERE tenant_id = %s
            """
            if not include_inactive:
                query += " AND is_active = TRUE"
            query += " ORDER BY name"

        results = db_manager.execute_query(query, (tenant_id,), fetch_all=True)

        entities = []
        for row in results:
            entity = {
                'id': str(row[0]),
                'tenant_id': row[1],
                'code': row[2],
                'name': row[3],
                'legal_name': row[4],
                'tax_id': row[5],
                'tax_jurisdiction': row[6],
                'entity_type': row[7],
                'base_currency': row[8],
                'fiscal_year_end': row[9],
                'address': row[10],
                'country_code': row[11],
                'is_active': row[12],
                'incorporation_date': row[13].isoformat() if row[13] else None,
                'created_at': row[14].isoformat() if row[14] else None,
                'updated_at': row[15].isoformat() if row[15] else None,
                'created_by': row[16]
            }

            if include_stats:
                entity['business_lines_count'] = row[17]
                entity['transactions_count'] = row[18]

            entities.append(entity)

        return jsonify({
            'success': True,
            'entities': entities,
            'count': len(entities)
        })

    except Exception as e:
        logger.error(f"Error listing entities: {e}")
        logger.exception("Exception details:")
        return jsonify({'success': False, 'error': str(e)}), 500


@entity_bp.route('', methods=['POST'])
def create_entity():
    """
    Create a new entity

    Request body:
        {
            "code": "DLLC",  // required, unique per tenant
            "name": "Delta Mining LLC",  // required
            "legal_name": "Delta Mining LLC",  // optional
            "tax_id": "XX-XXXXXXX",  // optional
            "tax_jurisdiction": "US-Delaware",  // optional
            "entity_type": "LLC",  // optional
            "base_currency": "USD",  // default: "USD"
            "fiscal_year_end": "12-31",  // default: "12-31"
            "address": "123 Main St",  // optional
            "country_code": "US",  // optional
            "incorporation_date": "2020-01-01",  // optional
            "create_default_business_line": true  // default: true
        }

    Returns:
        {
            "success": true,
            "entity": {...},
            "default_business_line": {...}  // if created
        }
    """
    try:
        from database import db_manager
        from tenant_context import get_current_tenant_id

        # Get tenant (required)
        tenant_id = get_current_tenant_id(strict=True)

        # Get request data
        data = request.get_json()

        # Validate required fields
        code = data.get('code', '').strip()
        name = data.get('name', '').strip()

        if not code:
            return jsonify({'success': False, 'error': 'Entity code is required'}), 400
        if not name:
            return jsonify({'success': False, 'error': 'Entity name is required'}), 400

        # Optional fields
        legal_name = data.get('legal_name', name).strip()
        tax_id = data.get('tax_id', '').strip() or None
        tax_jurisdiction = data.get('tax_jurisdiction', '').strip() or None
        entity_type = data.get('entity_type', '').strip() or None
        base_currency = data.get('base_currency', 'USD').strip()
        fiscal_year_end = data.get('fiscal_year_end', '12-31').strip()
        address = data.get('address', '').strip() or None
        country_code = data.get('country_code', '').strip() or None
        incorporation_date = data.get('incorporation_date') or None
        create_default_bl = data.get('create_default_business_line', True)

        # Create entity
        query = """
        INSERT INTO entities (
            tenant_id, code, name, legal_name, tax_id,
            tax_jurisdiction, entity_type, base_currency,
            fiscal_year_end, address, country_code,
            incorporation_date, is_active, created_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, tenant_id, code, name, legal_name, tax_id,
                  tax_jurisdiction, entity_type, base_currency,
                  fiscal_year_end, address, country_code, is_active,
                  incorporation_date, created_at, updated_at, created_by
        """

        params = (
            tenant_id, code, name, legal_name, tax_id,
            tax_jurisdiction, entity_type, base_currency,
            fiscal_year_end, address, country_code,
            incorporation_date, True, 'web_ui'
        )

        result = db_manager.execute_query(query, params, fetch_one=True)

        if not result:
            return jsonify({'success': False, 'error': 'Failed to create entity'}), 500

        # Format entity response
        entity = {
            'id': str(result[0]),
            'tenant_id': result[1],
            'code': result[2],
            'name': result[3],
            'legal_name': result[4],
            'tax_id': result[5],
            'tax_jurisdiction': result[6],
            'entity_type': result[7],
            'base_currency': result[8],
            'fiscal_year_end': result[9],
            'address': result[10],
            'country_code': result[11],
            'is_active': result[12],
            'incorporation_date': result[13].isoformat() if result[13] else None,
            'created_at': result[14].isoformat() if result[14] else None,
            'updated_at': result[15].isoformat() if result[15] else None,
            'created_by': result[16]
        }

        response = {
            'success': True,
            'entity': entity
        }

        # Create default business line if requested
        if create_default_bl:
            bl_query = """
            INSERT INTO business_lines (
                entity_id, code, name, is_default, is_active, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, entity_id, code, name, is_default, is_active,
                      created_at, updated_at
            """

            bl_result = db_manager.execute_query(
                bl_query,
                (entity['id'], 'DEFAULT', 'Default', True, True, 'web_ui'),
                fetch_one=True
            )

            if bl_result:
                response['default_business_line'] = {
                    'id': str(bl_result[0]),
                    'entity_id': str(bl_result[1]),
                    'code': bl_result[2],
                    'name': bl_result[3],
                    'is_default': bl_result[4],
                    'is_active': bl_result[5],
                    'created_at': bl_result[6].isoformat() if bl_result[6] else None,
                    'updated_at': bl_result[7].isoformat() if bl_result[7] else None
                }

        logger.info(f"Created entity: {entity['code']} ({entity['name']}) for tenant: {tenant_id}")

        return jsonify(response), 201

    except Exception as e:
        logger.error(f"Error creating entity: {e}")
        logger.exception("Exception details:")
        return jsonify({'success': False, 'error': str(e)}), 500


@entity_bp.route('/<entity_id>', methods=['GET'])
def get_entity(entity_id):
    """
    Get entity details by ID

    Returns:
        {
            "success": true,
            "entity": {...},
            "business_lines": [...]  // all business lines for this entity
        }
    """
    try:
        from database import db_manager
        from tenant_context import get_current_tenant_id

        # Get tenant (required)
        tenant_id = get_current_tenant_id(strict=True)

        # Get entity
        query = """
        SELECT
            id, tenant_id, code, name, legal_name,
            tax_id, tax_jurisdiction, entity_type,
            base_currency, fiscal_year_end, address,
            country_code, is_active, incorporation_date,
            created_at, updated_at, created_by
        FROM entities
        WHERE id = %s AND tenant_id = %s
        """

        result = db_manager.execute_query(query, (entity_id, tenant_id), fetch_one=True)

        if not result:
            return jsonify({'success': False, 'error': 'Entity not found'}), 404

        entity = {
            'id': str(result[0]),
            'tenant_id': result[1],
            'code': result[2],
            'name': result[3],
            'legal_name': result[4],
            'tax_id': result[5],
            'tax_jurisdiction': result[6],
            'entity_type': result[7],
            'base_currency': result[8],
            'fiscal_year_end': result[9],
            'address': result[10],
            'country_code': result[11],
            'is_active': result[12],
            'incorporation_date': result[13].isoformat() if result[13] else None,
            'created_at': result[14].isoformat() if result[14] else None,
            'updated_at': result[15].isoformat() if result[15] else None,
            'created_by': result[16]
        }

        # Get business lines for this entity
        bl_query = """
        SELECT id, entity_id, code, name, description, is_default,
               color_hex, is_active, start_date, end_date,
               created_at, updated_at, created_by
        FROM business_lines
        WHERE entity_id = %s
        ORDER BY is_default DESC, name
        """

        bl_results = db_manager.execute_query(bl_query, (entity_id,), fetch_all=True)

        business_lines = []
        for row in bl_results:
            business_lines.append({
                'id': str(row[0]),
                'entity_id': str(row[1]),
                'code': row[2],
                'name': row[3],
                'description': row[4],
                'is_default': row[5],
                'color_hex': row[6],
                'is_active': row[7],
                'start_date': row[8].isoformat() if row[8] else None,
                'end_date': row[9].isoformat() if row[9] else None,
                'created_at': row[10].isoformat() if row[10] else None,
                'updated_at': row[11].isoformat() if row[11] else None,
                'created_by': row[12]
            })

        return jsonify({
            'success': True,
            'entity': entity,
            'business_lines': business_lines
        })

    except Exception as e:
        logger.error(f"Error getting entity: {e}")
        logger.exception("Exception details:")
        return jsonify({'success': False, 'error': str(e)}), 500


@entity_bp.route('/<entity_id>', methods=['PUT'])
def update_entity(entity_id):
    """
    Update entity

    Request body: Any fields to update (same as POST)

    Returns:
        {
            "success": true,
            "entity": {...}
        }
    """
    try:
        from database import db_manager
        from tenant_context import get_current_tenant_id

        # Get tenant (required)
        tenant_id = get_current_tenant_id(strict=True)

        # Get request data
        data = request.get_json()

        # Build update query dynamically
        update_fields = []
        params = []

        allowed_fields = {
            'code': '%s', 'name': '%s', 'legal_name': '%s',
            'tax_id': '%s', 'tax_jurisdiction': '%s', 'entity_type': '%s',
            'base_currency': '%s', 'fiscal_year_end': '%s', 'address': '%s',
            'country_code': '%s', 'incorporation_date': '%s', 'is_active': '%s'
        }

        for field, placeholder in allowed_fields.items():
            if field in data:
                update_fields.append(f"{field} = {placeholder}")
                params.append(data[field])

        if not update_fields:
            return jsonify({'success': False, 'error': 'No fields to update'}), 400

        # Add updated_at
        update_fields.append("updated_at = CURRENT_TIMESTAMP")

        # Add WHERE clause params
        params.extend([entity_id, tenant_id])

        query = f"""
        UPDATE entities
        SET {', '.join(update_fields)}
        WHERE id = %s AND tenant_id = %s
        RETURNING id, tenant_id, code, name, legal_name, tax_id,
                  tax_jurisdiction, entity_type, base_currency,
                  fiscal_year_end, address, country_code, is_active,
                  incorporation_date, created_at, updated_at, created_by
        """

        result = db_manager.execute_query(query, tuple(params), fetch_one=True)

        if not result:
            return jsonify({'success': False, 'error': 'Entity not found'}), 404

        entity = {
            'id': str(result[0]),
            'tenant_id': result[1],
            'code': result[2],
            'name': result[3],
            'legal_name': result[4],
            'tax_id': result[5],
            'tax_jurisdiction': result[6],
            'entity_type': result[7],
            'base_currency': result[8],
            'fiscal_year_end': result[9],
            'address': result[10],
            'country_code': result[11],
            'is_active': result[12],
            'incorporation_date': result[13].isoformat() if result[13] else None,
            'created_at': result[14].isoformat() if result[14] else None,
            'updated_at': result[15].isoformat() if result[15] else None,
            'created_by': result[16]
        }

        logger.info(f"Updated entity: {entity['code']} for tenant: {tenant_id}")

        return jsonify({
            'success': True,
            'entity': entity
        })

    except Exception as e:
        logger.error(f"Error updating entity: {e}")
        logger.exception("Exception details:")
        return jsonify({'success': False, 'error': str(e)}), 500


@entity_bp.route('/<entity_id>', methods=['DELETE'])
def delete_entity(entity_id):
    """
    Soft delete entity (sets is_active = false)

    Returns:
        {
            "success": true,
            "message": "Entity deactivated successfully"
        }
    """
    try:
        from database import db_manager
        from tenant_context import get_current_tenant_id

        # Get tenant (required)
        tenant_id = get_current_tenant_id(strict=True)

        # Soft delete
        query = """
        UPDATE entities
        SET is_active = false, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND tenant_id = %s
        RETURNING id
        """

        result = db_manager.execute_query(query, (entity_id, tenant_id), fetch_one=True)

        if not result:
            return jsonify({'success': False, 'error': 'Entity not found'}), 404

        logger.info(f"Deactivated entity: {entity_id} for tenant: {tenant_id}")

        return jsonify({
            'success': True,
            'message': 'Entity deactivated successfully'
        })

    except Exception as e:
        logger.error(f"Error deleting entity: {e}")
        logger.exception("Exception details:")
        return jsonify({'success': False, 'error': str(e)}), 500


@entity_bp.route('/<entity_id>/stats', methods=['GET'])
def get_entity_stats(entity_id):
    """
    Get statistics for an entity

    Returns:
        {
            "success": true,
            "stats": {
                "business_lines_count": 3,
                "transactions_count": 1250,
                "revenue": 100000.00,
                "expenses": 50000.00,
                "net": 50000.00
            }
        }
    """
    try:
        from database import db_manager
        from tenant_context import get_current_tenant_id

        # Get tenant (required)
        tenant_id = get_current_tenant_id(strict=True)

        # Get stats
        query = """
        SELECT
            COUNT(DISTINCT bl.id) as business_lines_count,
            COUNT(DISTINCT t.id) as transactions_count,
            SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END) as revenue,
            SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END) as expenses,
            SUM(t.amount) as net
        FROM entities e
        LEFT JOIN business_lines bl ON e.id = bl.entity_id
        LEFT JOIN transactions t ON e.id = t.entity_id
        WHERE e.id = %s AND e.tenant_id = %s
        GROUP BY e.id
        """

        result = db_manager.execute_query(query, (entity_id, tenant_id), fetch_one=True)

        if not result:
            return jsonify({'success': False, 'error': 'Entity not found'}), 404

        stats = {
            'business_lines_count': result[0] or 0,
            'transactions_count': result[1] or 0,
            'revenue': float(result[2]) if result[2] else 0.0,
            'expenses': float(result[3]) if result[3] else 0.0,
            'net': float(result[4]) if result[4] else 0.0
        }

        return jsonify({
            'success': True,
            'stats': stats
        })

    except Exception as e:
        logger.error(f"Error getting entity stats: {e}")
        logger.exception("Exception details:")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# BUSINESS LINE MANAGEMENT ENDPOINTS
# ============================================================================

@business_line_bp.route('', methods=['GET'])
def list_business_lines():
    """
    List all business lines for the current tenant

    Query params:
        - entity_id: Filter by entity (optional)
        - include_inactive: Include inactive business lines (default: false)
        - include_stats: Include transaction counts (default: false)

    Returns:
        {
            "success": true,
            "business_lines": [...],
            "count": 12
        }
    """
    try:
        from database import db_manager
        from tenant_context import get_current_tenant_id

        # Get tenant (required)
        tenant_id = get_current_tenant_id(strict=True)

        # Get query params
        entity_id = request.args.get('entity_id')
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        include_stats = request.args.get('include_stats', 'false').lower() == 'true'

        # Build query
        if include_stats:
            query = """
            SELECT
                bl.id, bl.entity_id, e.code as entity_code, e.name as entity_name,
                bl.code, bl.name, bl.description, bl.is_default,
                bl.color_hex, bl.is_active, bl.start_date, bl.end_date,
                bl.created_at, bl.updated_at, bl.created_by,
                COUNT(t.id) as transactions_count
            FROM business_lines bl
            JOIN entities e ON bl.entity_id = e.id
            LEFT JOIN transactions t ON bl.id = t.business_line_id
            WHERE e.tenant_id = %s
            """
        else:
            query = """
            SELECT
                bl.id, bl.entity_id, e.code as entity_code, e.name as entity_name,
                bl.code, bl.name, bl.description, bl.is_default,
                bl.color_hex, bl.is_active, bl.start_date, bl.end_date,
                bl.created_at, bl.updated_at, bl.created_by
            FROM business_lines bl
            JOIN entities e ON bl.entity_id = e.id
            WHERE e.tenant_id = %s
            """

        params = [tenant_id]

        if entity_id:
            query += " AND bl.entity_id = %s"
            params.append(entity_id)

        if not include_inactive:
            query += " AND bl.is_active = TRUE"

        if include_stats:
            query += """
            GROUP BY bl.id, bl.entity_id, e.code, e.name, bl.code, bl.name,
                     bl.description, bl.is_default, bl.color_hex, bl.is_active,
                     bl.start_date, bl.end_date, bl.created_at, bl.updated_at, bl.created_by
            """

        query += " ORDER BY e.name, bl.is_default DESC, bl.name"

        results = db_manager.execute_query(query, tuple(params), fetch_all=True)

        business_lines = []
        for row in results:
            bl = {
                'id': str(row[0]),
                'entity_id': str(row[1]),
                'entity_code': row[2],
                'entity_name': row[3],
                'code': row[4],
                'name': row[5],
                'description': row[6],
                'is_default': row[7],
                'color_hex': row[8],
                'is_active': row[9],
                'start_date': row[10].isoformat() if row[10] else None,
                'end_date': row[11].isoformat() if row[11] else None,
                'created_at': row[12].isoformat() if row[12] else None,
                'updated_at': row[13].isoformat() if row[13] else None,
                'created_by': row[14]
            }

            if include_stats:
                bl['transactions_count'] = row[15]

            business_lines.append(bl)

        return jsonify({
            'success': True,
            'business_lines': business_lines,
            'count': len(business_lines)
        })

    except Exception as e:
        logger.error(f"Error listing business lines: {e}")
        logger.exception("Exception details:")
        return jsonify({'success': False, 'error': str(e)}), 500


@business_line_bp.route('', methods=['POST'])
def create_business_line():
    """
    Create a new business line

    Request body:
        {
            "entity_id": "uuid",  // required
            "code": "HOST",  // required, unique per entity
            "name": "Hosting Services",  // required
            "description": "Client hosting services",  // optional
            "color_hex": "#3B82F6",  // optional
            "start_date": "2024-01-01",  // optional
            "is_default": false  // default: false
        }

    Returns:
        {
            "success": true,
            "business_line": {...}
        }
    """
    try:
        from database import db_manager
        from tenant_context import get_current_tenant_id

        # Get tenant (required)
        tenant_id = get_current_tenant_id(strict=True)

        # Get request data
        data = request.get_json()

        # Validate required fields
        entity_id = data.get('entity_id', '').strip()
        code = data.get('code', '').strip()
        name = data.get('name', '').strip()

        if not entity_id:
            return jsonify({'success': False, 'error': 'Entity ID is required'}), 400
        if not code:
            return jsonify({'success': False, 'error': 'Business line code is required'}), 400
        if not name:
            return jsonify({'success': False, 'error': 'Business line name is required'}), 400

        # Verify entity belongs to tenant
        entity_check = db_manager.execute_query(
            "SELECT id FROM entities WHERE id = %s AND tenant_id = %s",
            (entity_id, tenant_id),
            fetch_one=True
        )

        if not entity_check:
            return jsonify({'success': False, 'error': 'Entity not found or access denied'}), 404

        # Optional fields
        description = data.get('description', '').strip() or None
        color_hex = data.get('color_hex', '').strip() or None
        start_date = data.get('start_date') or None
        is_default = data.get('is_default', False)

        # Create business line
        query = """
        INSERT INTO business_lines (
            entity_id, code, name, description, color_hex,
            start_date, is_default, is_active, created_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, entity_id, code, name, description, is_default,
                  color_hex, is_active, start_date, end_date,
                  created_at, updated_at, created_by
        """

        params = (
            entity_id, code, name, description, color_hex,
            start_date, is_default, True, 'web_ui'
        )

        result = db_manager.execute_query(query, params, fetch_one=True)

        if not result:
            return jsonify({'success': False, 'error': 'Failed to create business line'}), 500

        business_line = {
            'id': str(result[0]),
            'entity_id': str(result[1]),
            'code': result[2],
            'name': result[3],
            'description': result[4],
            'is_default': result[5],
            'color_hex': result[6],
            'is_active': result[7],
            'start_date': result[8].isoformat() if result[8] else None,
            'end_date': result[9].isoformat() if result[9] else None,
            'created_at': result[10].isoformat() if result[10] else None,
            'updated_at': result[11].isoformat() if result[11] else None,
            'created_by': result[12]
        }

        logger.info(f"Created business line: {business_line['code']} for entity: {entity_id}")

        return jsonify({
            'success': True,
            'business_line': business_line
        }), 201

    except Exception as e:
        logger.error(f"Error creating business line: {e}")
        logger.exception("Exception details:")
        return jsonify({'success': False, 'error': str(e)}), 500


@business_line_bp.route('/<business_line_id>', methods=['GET'])
def get_business_line(business_line_id):
    """Get business line details"""
    try:
        from database import db_manager
        from tenant_context import get_current_tenant_id

        tenant_id = get_current_tenant_id(strict=True)

        query = """
        SELECT
            bl.id, bl.entity_id, e.code as entity_code, e.name as entity_name,
            bl.code, bl.name, bl.description, bl.is_default,
            bl.color_hex, bl.is_active, bl.start_date, bl.end_date,
            bl.created_at, bl.updated_at, bl.created_by,
            COUNT(t.id) as transactions_count
        FROM business_lines bl
        JOIN entities e ON bl.entity_id = e.id
        LEFT JOIN transactions t ON bl.id = t.business_line_id
        WHERE bl.id = %s AND e.tenant_id = %s
        GROUP BY bl.id, bl.entity_id, e.code, e.name, bl.code, bl.name,
                 bl.description, bl.is_default, bl.color_hex, bl.is_active,
                 bl.start_date, bl.end_date, bl.created_at, bl.updated_at, bl.created_by
        """

        result = db_manager.execute_query(query, (business_line_id, tenant_id), fetch_one=True)

        if not result:
            return jsonify({'success': False, 'error': 'Business line not found'}), 404

        business_line = {
            'id': str(result[0]),
            'entity_id': str(result[1]),
            'entity_code': result[2],
            'entity_name': result[3],
            'code': result[4],
            'name': result[5],
            'description': result[6],
            'is_default': result[7],
            'color_hex': result[8],
            'is_active': result[9],
            'start_date': result[10].isoformat() if result[10] else None,
            'end_date': result[11].isoformat() if result[11] else None,
            'created_at': result[12].isoformat() if result[12] else None,
            'updated_at': result[13].isoformat() if result[13] else None,
            'created_by': result[14],
            'transactions_count': result[15]
        }

        return jsonify({
            'success': True,
            'business_line': business_line
        })

    except Exception as e:
        logger.error(f"Error getting business line: {e}")
        logger.exception("Exception details:")
        return jsonify({'success': False, 'error': str(e)}), 500


@business_line_bp.route('/<business_line_id>', methods=['PUT'])
def update_business_line(business_line_id):
    """Update business line"""
    try:
        from database import db_manager
        from tenant_context import get_current_tenant_id

        tenant_id = get_current_tenant_id(strict=True)
        data = request.get_json()

        # Build update query dynamically
        update_fields = []
        params = []

        allowed_fields = {
            'code': '%s', 'name': '%s', 'description': '%s',
            'color_hex': '%s', 'start_date': '%s', 'end_date': '%s',
            'is_default': '%s', 'is_active': '%s'
        }

        for field, placeholder in allowed_fields.items():
            if field in data:
                update_fields.append(f"{field} = {placeholder}")
                params.append(data[field])

        if not update_fields:
            return jsonify({'success': False, 'error': 'No fields to update'}), 400

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([business_line_id, tenant_id])

        query = f"""
        UPDATE business_lines bl
        SET {', '.join(update_fields)}
        FROM entities e
        WHERE bl.id = %s AND bl.entity_id = e.id AND e.tenant_id = %s
        RETURNING bl.id, bl.entity_id, bl.code, bl.name, bl.description,
                  bl.is_default, bl.color_hex, bl.is_active, bl.start_date,
                  bl.end_date, bl.created_at, bl.updated_at, bl.created_by
        """

        result = db_manager.execute_query(query, tuple(params), fetch_one=True)

        if not result:
            return jsonify({'success': False, 'error': 'Business line not found'}), 404

        business_line = {
            'id': str(result[0]),
            'entity_id': str(result[1]),
            'code': result[2],
            'name': result[3],
            'description': result[4],
            'is_default': result[5],
            'color_hex': result[6],
            'is_active': result[7],
            'start_date': result[8].isoformat() if result[8] else None,
            'end_date': result[9].isoformat() if result[9] else None,
            'created_at': result[10].isoformat() if result[10] else None,
            'updated_at': result[11].isoformat() if result[11] else None,
            'created_by': result[12]
        }

        logger.info(f"Updated business line: {business_line['code']}")

        return jsonify({
            'success': True,
            'business_line': business_line
        })

    except Exception as e:
        logger.error(f"Error updating business line: {e}")
        logger.exception("Exception details:")
        return jsonify({'success': False, 'error': str(e)}), 500


@business_line_bp.route('/<business_line_id>', methods=['DELETE'])
def delete_business_line(business_line_id):
    """Soft delete business line (sets is_active = false)"""
    try:
        from database import db_manager
        from tenant_context import get_current_tenant_id

        tenant_id = get_current_tenant_id(strict=True)

        # Check if it's the only business line for the entity
        check_query = """
        SELECT COUNT(*)
        FROM business_lines bl
        JOIN entities e ON bl.entity_id = e.id
        WHERE bl.entity_id = (
            SELECT entity_id FROM business_lines WHERE id = %s
        ) AND bl.is_active = true AND e.tenant_id = %s
        """

        count_result = db_manager.execute_query(check_query, (business_line_id, tenant_id), fetch_one=True)

        if count_result and count_result[0] <= 1:
            return jsonify({
                'success': False,
                'error': 'Cannot delete the only business line for an entity'
            }), 400

        # Soft delete
        query = """
        UPDATE business_lines bl
        SET is_active = false, updated_at = CURRENT_TIMESTAMP
        FROM entities e
        WHERE bl.id = %s AND bl.entity_id = e.id AND e.tenant_id = %s
        RETURNING bl.id
        """

        result = db_manager.execute_query(query, (business_line_id, tenant_id), fetch_one=True)

        if not result:
            return jsonify({'success': False, 'error': 'Business line not found'}), 404

        logger.info(f"Deactivated business line: {business_line_id}")

        return jsonify({
            'success': True,
            'message': 'Business line deactivated successfully'
        })

    except Exception as e:
        logger.error(f"Error deleting business line: {e}")
        logger.exception("Exception details:")
        return jsonify({'success': False, 'error': str(e)}), 500


@business_line_bp.route('/<business_line_id>/set-default', methods=['POST'])
def set_default_business_line(business_line_id):
    """Set a business line as the default for its entity"""
    try:
        from database import db_manager
        from tenant_context import get_current_tenant_id

        tenant_id = get_current_tenant_id(strict=True)

        # Get entity_id for this business line
        entity_query = """
        SELECT bl.entity_id
        FROM business_lines bl
        JOIN entities e ON bl.entity_id = e.id
        WHERE bl.id = %s AND e.tenant_id = %s
        """

        entity_result = db_manager.execute_query(entity_query, (business_line_id, tenant_id), fetch_one=True)

        if not entity_result:
            return jsonify({'success': False, 'error': 'Business line not found'}), 404

        entity_id = entity_result[0]

        # Unset all defaults for this entity
        db_manager.execute_query(
            "UPDATE business_lines SET is_default = false WHERE entity_id = %s",
            (entity_id,)
        )

        # Set new default
        db_manager.execute_query(
            "UPDATE business_lines SET is_default = true WHERE id = %s",
            (business_line_id,)
        )

        logger.info(f"Set business line {business_line_id} as default for entity {entity_id}")

        return jsonify({
            'success': True,
            'message': 'Default business line updated successfully'
        })

    except Exception as e:
        logger.error(f"Error setting default business line: {e}")
        logger.exception("Exception details:")
        return jsonify({'success': False, 'error': str(e)}), 500
