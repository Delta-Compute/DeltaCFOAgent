"""
Onboarding API Routes

Provides REST API endpoints for enhanced tenant onboarding with business entities,
chart of accounts, bank accounts, and document upload.
"""

import logging
import uuid
import os
import base64
from datetime import datetime
from flask import Blueprint, request, jsonify
from middleware.auth_middleware import require_auth, get_current_user
from web_ui.database import db_manager
from web_ui.tenant_context import get_current_tenant_id
import anthropic

logger = logging.getLogger(__name__)

onboarding_bp = Blueprint('onboarding', __name__, url_prefix='/api/onboarding')


# Industry templates for chart of accounts
INDUSTRY_TEMPLATES = {
    'technology': {
        'revenue': ['Software Sales', 'Subscription Revenue', 'Consulting Services', 'Licensing Fees'],
        'expenses': ['Salaries & Wages', 'Cloud Infrastructure', 'Software & Tools', 'Marketing & Advertising',
                    'R&D Expenses', 'Office Rent', 'Travel & Entertainment'],
        'assets': ['Cash', 'Accounts Receivable', 'Equipment', 'Software Development Costs'],
        'liabilities': ['Accounts Payable', 'Deferred Revenue', 'Loans Payable', 'Accrued Expenses'],
        'equity': ['Common Stock', 'Retained Earnings', 'Additional Paid-in Capital']
    },
    'retail': {
        'revenue': ['Product Sales', 'Online Sales', 'In-Store Sales', 'Returns & Refunds'],
        'expenses': ['Cost of Goods Sold', 'Inventory Purchases', 'Store Rent', 'Salaries & Wages',
                    'Marketing', 'Utilities', 'Shipping & Delivery'],
        'assets': ['Cash', 'Accounts Receivable', 'Inventory', 'Store Equipment', 'Point of Sale Systems'],
        'liabilities': ['Accounts Payable', 'Credit Card Payables', 'Loans', 'Sales Tax Payable'],
        'equity': ['Owner\'s Capital', 'Retained Earnings']
    },
    'consulting': {
        'revenue': ['Consulting Fees', 'Project Revenue', 'Retainer Fees', 'Training Services'],
        'expenses': ['Consultant Salaries', 'Professional Fees', 'Travel Expenses', 'Office Expenses',
                    'Marketing', 'Insurance', 'Technology'],
        'assets': ['Cash', 'Accounts Receivable', 'Prepaid Expenses', 'Equipment'],
        'liabilities': ['Accounts Payable', 'Accrued Wages', 'Client Deposits', 'Loans Payable'],
        'equity': ['Partner Capital', 'Retained Earnings', 'Distributions']
    },
    'healthcare': {
        'revenue': ['Patient Services', 'Insurance Reimbursements', 'Consultation Fees', 'Lab Services'],
        'expenses': ['Medical Staff Salaries', 'Medical Supplies', 'Equipment Maintenance', 'Facility Rent',
                    'Insurance', 'Utilities', 'Administrative Costs'],
        'assets': ['Cash', 'Accounts Receivable', 'Medical Equipment', 'Supplies Inventory'],
        'liabilities': ['Accounts Payable', 'Medical Loans', 'Accrued Payroll', 'Insurance Payable'],
        'equity': ['Owner\'s Capital', 'Retained Earnings']
    },
    'generic': {
        'revenue': ['Sales Revenue', 'Service Revenue', 'Other Income', 'Interest Income'],
        'expenses': ['Salaries & Wages', 'Rent', 'Utilities', 'Office Supplies', 'Marketing',
                    'Professional Fees', 'Insurance', 'Depreciation'],
        'assets': ['Cash', 'Accounts Receivable', 'Inventory', 'Equipment', 'Prepaid Expenses'],
        'liabilities': ['Accounts Payable', 'Loans Payable', 'Accrued Expenses', 'Credit Cards Payable'],
        'equity': ['Owner\'s Equity', 'Retained Earnings', 'Dividends']
    }
}


@onboarding_bp.route('/templates/<industry>', methods=['GET'])
@require_auth
def get_industry_template(industry):
    """
    Get chart of accounts template for a specific industry.

    Args:
        industry: Industry name (technology, retail, consulting, healthcare, generic)

    Returns:
        {
            "success": true,
            "template": {
                "industry": "technology",
                "categories": { ... }
            }
        }
    """
    try:
        # Normalize industry name
        industry_key = industry.lower().replace(' ', '_')

        # Get template or fall back to generic
        template = INDUSTRY_TEMPLATES.get(industry_key, INDUSTRY_TEMPLATES['generic'])

        return jsonify({
            'success': True,
            'template': {
                'industry': industry_key,
                'categories': template
            }
        }), 200

    except Exception as e:
        logger.error(f"Get template error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred'
        }), 500


@onboarding_bp.route('/complete-setup', methods=['POST'])
@require_auth
def complete_tenant_setup():
    """
    Complete tenant setup with all onboarding data in one request.

    Request Body:
        {
            "basic_info": {
                "company_name": "...",
                "description": "...",
                "industry": "..."
            },
            "entities": [
                {"name": "...", "type": "...", "is_internal": false}
            ],
            "chart_of_accounts": {
                "template": "technology" | null,
                "custom_categories": { ... } | null
            },
            "bank_accounts": [ ... ],
            "crypto_wallets": [ ... ]
        }

    Returns:
        {
            "success": true,
            "tenant": { ... },
            "onboarding_status": { ... }
        }
    """
    try:
        user = get_current_user()
        data = request.get_json()

        # Validate required fields
        if not data.get('basic_info') or not data['basic_info'].get('company_name'):
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'basic_info.company_name is required'
            }), 400

        basic_info = data['basic_info']
        entities = data.get('entities', [])
        coa = data.get('chart_of_accounts', {})
        bank_accounts = data.get('bank_accounts', [])
        crypto_wallets = data.get('crypto_wallets', [])

        # Generate tenant ID
        tenant_id = str(uuid.uuid4())[:8]

        # 1. Create tenant configuration
        create_tenant_query = """
            INSERT INTO tenant_configuration
            (tenant_id, company_name, company_description, industry, created_by_user_id,
             current_admin_user_id, payment_owner, subscription_status)
            VALUES (%s, %s, %s, %s, %s, %s, 'cfo', 'trial')
            RETURNING tenant_id, company_name, company_description, industry
        """

        tenant_result = db_manager.execute_query(
            create_tenant_query,
            (tenant_id, basic_info['company_name'], basic_info.get('description', ''),
             basic_info.get('industry', ''), user['id'], user['id']),
            fetch_one=True
        )

        if not tenant_result:
            return jsonify({
                'success': False,
                'error': 'database_error',
                'message': 'Failed to create tenant'
            }), 500

        # 2. Add user as owner
        tenant_user_id = str(uuid.uuid4())
        link_query = """
            INSERT INTO tenant_users (id, user_id, tenant_id, role, permissions, is_active, added_by_user_id)
            VALUES (%s, %s, %s, 'owner', '{}', true, %s)
        """
        db_manager.execute_query(link_query, (tenant_user_id, user['id'], tenant_id, user['id']))

        # 2.5. Create entities and business lines if provided
        entity_id_map = {}  # Map entity codes to UUIDs
        for entity in entities:
            entity_code = entity.get('code', entity.get('name', '').upper()[:4])
            entity_name = entity.get('name')

            if not entity_name:
                continue

            # Create entity
            result = db_manager.execute_query("""
                INSERT INTO entities
                (tenant_id, code, name, legal_name, entity_type, base_currency,
                 fiscal_year_end, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, true)
                RETURNING id
            """, (
                tenant_id,
                entity_code,
                entity_name,
                entity.get('legal_name', entity_name),
                entity.get('entity_type', 'LLC'),
                entity.get('base_currency', 'USD'),
                entity.get('fiscal_year_end', '12-31')
            ), fetch_one=True)

            if result:
                entity_id = str(result['id'])
                entity_id_map[entity_code] = entity_id

                # Create default business line for this entity
                db_manager.execute_query("""
                    INSERT INTO business_lines
                    (entity_id, code, name, description, is_default, is_active)
                    VALUES (%s, 'DEFAULT', %s, 'General operations', true, true)
                """, (entity_id, f"{entity_name} - General"))

        # Create additional business lines if provided
        business_lines = data.get('business_lines', [])
        for bl in business_lines:
            entity_code = bl.get('entity_code')
            if entity_code and entity_code in entity_id_map:
                db_manager.execute_query("""
                    INSERT INTO business_lines
                    (entity_id, code, name, description, color_hex, is_default, is_active)
                    VALUES (%s, %s, %s, %s, %s, false, true)
                """, (
                    entity_id_map[entity_code],
                    bl.get('code'),
                    bl.get('name'),
                    bl.get('description', ''),
                    bl.get('color_hex', '#3B82F6')
                ))

        # 3. Create custom categories if provided
        if coa.get('custom_categories'):
            categories = coa['custom_categories']
            for category_type, category_list in categories.items():
                for category_name in category_list:
                    category_id = str(uuid.uuid4())
                    db_manager.execute_query("""
                        INSERT INTO custom_categories
                        (id, tenant_id, category_type, category_name, is_active)
                        VALUES (%s, %s, %s, %s, true)
                    """, (category_id, tenant_id, category_type, category_name))
        elif coa.get('template'):
            # Use industry template
            template = INDUSTRY_TEMPLATES.get(coa['template'], INDUSTRY_TEMPLATES['generic'])
            for category_type, category_list in template.items():
                for category_name in category_list:
                    category_id = str(uuid.uuid4())
                    db_manager.execute_query("""
                        INSERT INTO custom_categories
                        (id, tenant_id, category_type, category_name, is_active)
                        VALUES (%s, %s, %s, %s, true)
                    """, (category_id, tenant_id, category_type, category_name))

        # 4. Create bank accounts
        for account in bank_accounts:
            account_id = str(uuid.uuid4())
            db_manager.execute_query("""
                INSERT INTO bank_accounts
                (id, tenant_id, account_name, institution_name, account_type, last_four,
                 currency, initial_balance, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true)
            """, (
                account_id, tenant_id, account.get('account_name'),
                account.get('institution_name'), account.get('account_type', 'checking'),
                account.get('last_four'), account.get('currency', 'USD'),
                account.get('initial_balance', 0.0)
            ))

        # 5. Create crypto wallets
        for wallet in crypto_wallets:
            wallet_id = str(uuid.uuid4())
            db_manager.execute_query("""
                INSERT INTO wallet_addresses
                (id, tenant_id, wallet_name, blockchain, address, currency, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, true)
            """, (
                wallet_id, tenant_id, wallet.get('wallet_name'),
                wallet.get('blockchain'), wallet.get('address', ''),
                wallet.get('currency', 'ETH')
            ))

        # 6. Create onboarding status record
        db_manager.execute_query("""
            INSERT INTO tenant_onboarding_status
            (tenant_id, basic_info_complete, entities_complete, coa_complete,
             accounts_complete, documents_complete, completed_at)
            VALUES (%s, true, %s, %s, %s, false, CURRENT_TIMESTAMP)
        """, (
            tenant_id,
            len(entities) > 0,
            bool(coa.get('template') or coa.get('custom_categories')),
            len(bank_accounts) > 0 or len(crypto_wallets) > 0
        ))

        logger.info(f"Complete tenant setup: {basic_info['company_name']} by {user['email']}")

        return jsonify({
            'success': True,
            'tenant': {
                'id': tenant_id,
                'company_name': tenant_result['company_name'],
                'description': tenant_result['company_description'],
                'industry': tenant_result['industry'],
                'role': 'owner',
                'payment_owner': 'cfo',
                'subscription_status': 'trial'
            },
            'onboarding_status': {
                'basic_info_complete': True,
                'entities_complete': len(entities) > 0,
                'coa_complete': bool(coa.get('template') or coa.get('custom_categories')),
                'accounts_complete': len(bank_accounts) > 0 or len(crypto_wallets) > 0,
                'documents_complete': False
            },
            'message': 'Tenant setup completed successfully'
        }), 201

    except Exception as e:
        logger.error(f"Complete setup error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': f'An error occurred: {str(e)}'
        }), 500


@onboarding_bp.route('/entities', methods=['GET'])
@require_auth
def get_entities():
    """
    Get all entities with their business lines for current tenant.

    Returns:
        {
            "success": true,
            "entities": [
                {
                    "id": "uuid",
                    "code": "DLLC",
                    "name": "Delta Mining LLC",
                    "entity_type": "LLC",
                    "is_active": true,
                    "business_lines": [
                        {
                            "id": "uuid",
                            "code": "HOST",
                            "name": "Hosting Services",
                            "is_default": false
                        }
                    ]
                }
            ]
        }
    """
    try:
        tenant_id = get_current_tenant_id()

        # Get entities
        entities = db_manager.execute_query("""
            SELECT id, tenant_id, code, name, legal_name, entity_type,
                   base_currency, is_active, created_at
            FROM entities
            WHERE tenant_id = %s AND is_active = true
            ORDER BY name
        """, (tenant_id,), fetch_all=True)

        # Get business lines
        business_lines = db_manager.execute_query("""
            SELECT bl.id, bl.entity_id, bl.code, bl.name, bl.description,
                   bl.color_hex, bl.is_default
            FROM business_lines bl
            JOIN entities e ON bl.entity_id = e.id
            WHERE e.tenant_id = %s AND bl.is_active = true
            ORDER BY e.name, bl.name
        """, (tenant_id,), fetch_all=True)

        # Build result with business lines nested under entities
        result_entities = []
        if entities:
            for entity in entities:
                entity_dict = dict(entity)
                entity_dict['id'] = str(entity_dict['id'])
                entity_dict['business_lines'] = [
                    {
                        'id': str(bl['id']),
                        'code': bl['code'],
                        'name': bl['name'],
                        'description': bl['description'],
                        'color_hex': bl['color_hex'],
                        'is_default': bl['is_default']
                    }
                    for bl in business_lines
                    if str(bl['entity_id']) == entity_dict['id']
                ]
                result_entities.append(entity_dict)

        return jsonify({
            'success': True,
            'entities': result_entities
        }), 200

    except Exception as e:
        logger.error(f"Get entities error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred'
        }), 500


@onboarding_bp.route('/entities', methods=['POST'])
@require_auth
def create_entity():
    """
    Create a new entity with default business line for current tenant.

    Request Body:
        {
            "code": "DLLC",  // Required: Short code
            "name": "Delta Mining LLC",  // Required
            "legal_name": "Delta Mining LLC",  // Optional
            "entity_type": "LLC",  // Optional
            "base_currency": "USD"  // Optional
        }

    Returns:
        {
            "success": true,
            "entity": {...},
            "default_business_line": {...}
        }
    """
    try:
        tenant_id = get_current_tenant_id()
        data = request.get_json()

        if not data.get('code') or not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'code and name are required'
            }), 400

        # Insert entity
        entity_result = db_manager.execute_query("""
            INSERT INTO entities
            (tenant_id, code, name, legal_name, entity_type, base_currency,
             fiscal_year_end, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, true)
            RETURNING id, tenant_id, code, name, legal_name, entity_type,
                      base_currency, is_active, created_at
        """, (
            tenant_id,
            data['code'],
            data['name'],
            data.get('legal_name', data['name']),
            data.get('entity_type', 'LLC'),
            data.get('base_currency', 'USD'),
            data.get('fiscal_year_end', '12-31')
        ), fetch_one=True)

        entity_id = str(entity_result['id'])

        # Create default business line
        bl_result = db_manager.execute_query("""
            INSERT INTO business_lines
            (entity_id, code, name, description, is_default, is_active)
            VALUES (%s, 'DEFAULT', %s, 'General operations', true, true)
            RETURNING id, entity_id, code, name, description, is_default, created_at
        """, (entity_id, f"{data['name']} - General"), fetch_one=True)

        logger.info(f"Created entity: {data['name']} with default business line for tenant: {tenant_id}")

        # Convert UUIDs to strings for JSON
        entity_dict = dict(entity_result)
        entity_dict['id'] = entity_id
        bl_dict = dict(bl_result)
        bl_dict['id'] = str(bl_dict['id'])
        bl_dict['entity_id'] = entity_id

        return jsonify({
            'success': True,
            'entity': entity_dict,
            'default_business_line': bl_dict
        }), 201

    except Exception as e:
        logger.error(f"Create entity error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': f'An error occurred: {str(e)}'
        }), 500


@onboarding_bp.route('/business-lines', methods=['POST'])
@require_auth
def create_business_line():
    """
    Create a new business line under an entity.

    Request Body:
        {
            "entity_id": "uuid",  // Required
            "code": "HOST",  // Required
            "name": "Hosting Services",  // Required
            "description": "Web hosting operations",  // Optional
            "color_hex": "#3B82F6"  // Optional
        }

    Returns:
        {
            "success": true,
            "business_line": {...}
        }
    """
    try:
        tenant_id = get_current_tenant_id()
        data = request.get_json()

        if not data.get('entity_id') or not data.get('code') or not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'missing_field',
                'message': 'entity_id, code, and name are required'
            }), 400

        # Verify entity belongs to tenant
        entity_check = db_manager.execute_query("""
            SELECT id FROM entities
            WHERE id = %s AND tenant_id = %s
        """, (data['entity_id'], tenant_id), fetch_one=True)

        if not entity_check:
            return jsonify({
                'success': False,
                'error': 'invalid_entity',
                'message': 'Entity not found or access denied'
            }), 404

        # Insert business line
        result = db_manager.execute_query("""
            INSERT INTO business_lines
            (entity_id, code, name, description, color_hex, is_default, is_active)
            VALUES (%s, %s, %s, %s, %s, false, true)
            RETURNING id, entity_id, code, name, description, color_hex,
                      is_default, is_active, created_at
        """, (
            data['entity_id'],
            data['code'],
            data['name'],
            data.get('description', ''),
            data.get('color_hex', '#3B82F6')
        ), fetch_one=True)

        logger.info(f"Created business line: {data['name']} for tenant: {tenant_id}")

        # Convert UUIDs to strings
        bl_dict = dict(result)
        bl_dict['id'] = str(bl_dict['id'])
        bl_dict['entity_id'] = str(bl_dict['entity_id'])

        return jsonify({
            'success': True,
            'business_line': bl_dict
        }), 201

    except Exception as e:
        logger.error(f"Create business line error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': f'An error occurred: {str(e)}'
        }), 500


@onboarding_bp.route('/upload-document', methods=['POST'])
@require_auth
def upload_document():
    """
    Upload and process a document with AI to extract business knowledge.

    Request Body (multipart/form-data):
        - file: The document file (PDF, DOCX, TXT)
        - document_type: Optional type ('contract', 'report', 'invoice', 'statement', 'other')
        - process_immediately: Boolean, whether to process with AI immediately (default: true)

    Returns:
        {
            "success": true,
            "document": {...},
            "knowledge_extracted": [...] (if processed)
        }
    """
    try:
        user = get_current_user()
        tenant_id = get_current_tenant_id()

        if not tenant_id or tenant_id == 'delta':
            return jsonify({
                'success': False,
                'error': 'no_tenant',
                'message': 'Please select a tenant first'
            }), 400

        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'no_file',
                'message': 'No file was uploaded'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'empty_filename',
                'message': 'No file selected'
            }), 400

        # Get metadata
        document_type = request.form.get('document_type', 'other')
        process_immediately = request.form.get('process_immediately', 'true').lower() == 'true'

        # Create uploads directory if it doesn't exist
        uploads_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', tenant_id)
        os.makedirs(uploads_dir, exist_ok=True)

        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(uploads_dir, unique_filename)

        # Save file
        file.save(file_path)
        file_size = os.path.getsize(file_path)

        # Store document record in database
        doc_id = str(uuid.uuid4())
        doc_result = db_manager.execute_query("""
            INSERT INTO tenant_documents
            (id, tenant_id, document_name, document_type, file_path, file_size, mime_type, uploaded_by_user_id, processed)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, false)
            RETURNING id, document_name, document_type, file_size, created_at
        """, (
            doc_id, tenant_id, file.filename, document_type,
            file_path, file_size, file.content_type, user['id']
        ), fetch_one=True)

        logger.info(f"Document uploaded: {file.filename} for tenant {tenant_id}")

        response_data = {
            'success': True,
            'document': dict(doc_result)
        }

        # Process with AI if requested
        if process_immediately:
            knowledge = process_document_with_ai(doc_id, tenant_id, file_path, file.content_type)
            response_data['knowledge_extracted'] = knowledge
            response_data['processed'] = True

        return jsonify(response_data), 201

    except Exception as e:
        logger.error(f"Upload document error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': f'An error occurred: {str(e)}'
        }), 500


def process_document_with_ai(doc_id, tenant_id, file_path, mime_type):
    """
    Process document with Claude AI to extract business knowledge.

    Returns list of knowledge items extracted.
    """
    try:
        # Get Claude API client
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not set")
            return []

        client = anthropic.Anthropic(api_key=api_key)

        # Read file content
        with open(file_path, 'rb') as f:
            file_content = f.read()

        # Prepare prompt
        prompt = """Analyze this business document and extract key information that would help understand:
1. Business operations and processes
2. Vendor/supplier relationships
3. Transaction patterns and frequencies
4. Business entities and their relationships
5. Common expense categories
6. Revenue sources
7. Any business rules or patterns

Please provide structured insights in the following format:
- Type of insight (vendor_info, transaction_pattern, business_rule, etc.)
- Title: Brief summary
- Content: Detailed description
- Structured data: Any specific values, amounts, dates, frequencies

Focus on information that would help automate and improve transaction classification."""

        # Call Claude AI based on file type
        if mime_type == 'application/pdf':
            # For PDF, encode as base64
            file_b64 = base64.standard_b64encode(file_content).decode('utf-8')

            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": file_b64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )
        else:
            # For text files, send as text
            try:
                text_content = file_content.decode('utf-8')
            except:
                text_content = file_content.decode('latin-1')

            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": f"{prompt}\n\nDocument content:\n{text_content}"
                }]
            )

        # Extract insights from Claude's response
        ai_response = message.content[0].text
        logger.info(f"AI analysis complete for document {doc_id}")

        # Parse and store knowledge
        knowledge_items = parse_ai_insights(ai_response, doc_id, tenant_id)

        # Update document as processed
        db_manager.execute_query("""
            UPDATE tenant_documents
            SET processed = true, processed_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (doc_id,))

        return knowledge_items

    except Exception as e:
        logger.error(f"AI processing error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def parse_ai_insights(ai_response, doc_id, tenant_id):
    """
    Parse AI response and store as structured knowledge.

    Returns list of created knowledge items.
    """
    knowledge_items = []

    try:
        # For now, store the entire response as general knowledge
        # TODO: Implement more sophisticated parsing
        knowledge_id = str(uuid.uuid4())

        db_manager.execute_query("""
            INSERT INTO tenant_knowledge
            (id, tenant_id, source_document_id, knowledge_type, title, content, confidence_score, is_active)
            VALUES (%s, %s, %s, 'general', 'Business Document Analysis', %s, 0.85, true)
        """, (knowledge_id, tenant_id, doc_id, ai_response))

        knowledge_items.append({
            'id': knowledge_id,
            'type': 'general',
            'title': 'Business Document Analysis',
            'summary': ai_response[:200] + '...' if len(ai_response) > 200 else ai_response
        })

        logger.info(f"Stored {len(knowledge_items)} knowledge items from document {doc_id}")

    except Exception as e:
        logger.error(f"Parse insights error: {e}")

    return knowledge_items


@onboarding_bp.route('/knowledge', methods=['GET'])
@require_auth
def get_tenant_knowledge():
    """
    Get all knowledge for current tenant.

    Query params:
        - type: Filter by knowledge_type (optional)
        - limit: Max results (default 50)

    Returns:
        {
            "success": true,
            "knowledge": [...]
        }
    """
    try:
        tenant_id = get_current_tenant_id()

        if not tenant_id or tenant_id == 'delta':
            return jsonify({
                'success': False,
                'error': 'no_tenant',
                'message': 'Please select a tenant first'
            }), 400

        knowledge_type = request.args.get('type')
        limit = int(request.args.get('limit', 50))

        # Build query
        if knowledge_type:
            knowledge = db_manager.execute_query("""
                SELECT id, knowledge_type, title, content, structured_data,
                       confidence_score, created_at
                FROM tenant_knowledge
                WHERE tenant_id = %s AND knowledge_type = %s AND is_active = true
                ORDER BY created_at DESC
                LIMIT %s
            """, (tenant_id, knowledge_type, limit), fetch_all=True)
        else:
            knowledge = db_manager.execute_query("""
                SELECT id, knowledge_type, title, content, structured_data,
                       confidence_score, created_at
                FROM tenant_knowledge
                WHERE tenant_id = %s AND is_active = true
                ORDER BY created_at DESC
                LIMIT %s
            """, (tenant_id, limit), fetch_all=True)

        return jsonify({
            'success': True,
            'knowledge': [dict(k) for k in knowledge] if knowledge else []
        }), 200

    except Exception as e:
        logger.error(f"Get knowledge error: {e}")
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred'
        }), 500


@onboarding_bp.route('/start-session', methods=['POST'])
@require_auth
def start_session():
    """
    Start a new onboarding session with context-aware greeting.

    Returns the session_id, greeting message, and current completion percentage.
    The greeting is context-aware based on how much data has been collected.
    """
    try:
        from web_ui.services.onboarding_bot import OnboardingBot

        tenant_id = get_current_tenant_id()

        # Create OnboardingBot instance
        bot = OnboardingBot(db_manager, tenant_id)

        # Start new session (creates context-aware greeting)
        session_id = bot.start_new_session()

        # Get the greeting from the conversation history
        history = bot.get_conversation_history(session_id)
        greeting = history[0]['content'] if history else "Hi! How can I help you?"

        # Get completion status
        status = bot.get_onboarding_status()

        return jsonify({
            'success': True,
            'session_id': session_id,
            'greeting': greeting,
            'completion_percentage': status.get('completion_percentage', 0)
        }), 200

    except Exception as e:
        logger.error(f"Start session error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred starting the session'
        }), 500


@onboarding_bp.route('/chat', methods=['POST'])
@require_auth
def chat():
    """
    AI conversational onboarding chat using OnboardingBot service.

    Uses the OnboardingBot class for natural conversation that:
    - Extracts tenant configuration data (company info, etc.)
    - Extracts business entities with revenue/description
    - Learns business knowledge from conversation
    """
    try:
        from web_ui.services.onboarding_bot import OnboardingBot

        data = request.get_json()
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')

        if not user_message:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': 'Message is required'
            }), 400

        tenant_id = get_current_tenant_id()

        # Create OnboardingBot instance
        bot = OnboardingBot(db_manager, tenant_id)

        # Create new session if not provided
        if not session_id:
            session_id = bot.start_new_session()

        # Process message through bot
        result = bot.chat(session_id, user_message)

        if result.get('error'):
            return jsonify({
                'success': False,
                'error': result.get('error'),
                'message': result.get('response', 'An error occurred')
            }), 500

        return jsonify({
            'success': True,
            'session_id': session_id,
            'response': result.get('response'),
            'extracted_data': result.get('extracted_data'),
            'entities_saved': result.get('entities_saved', []),
            'completion_percentage': result.get('completion_percentage', 0)
        }), 200

    except Exception as e:
        logger.error(f"Chat error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred processing your message'
        }), 500


@onboarding_bp.route('/capabilities', methods=['GET'])
@require_auth
def get_capabilities():
    """
    Get tenant capabilities based on setup completion milestones.

    Returns completion percentage, milestone status, capabilities,
    and next steps for incomplete milestones.

    Returns:
        {
            'success': True,
            'completion_percentage': 65,
            'milestones': {...},
            'capabilities': {...},
            'next_steps': [...]
        }
    """
    try:
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            return jsonify({
                'success': False,
                'error': 'no_tenant',
                'message': 'No tenant context available'
            }), 400

        bot = OnboardingBot(db_manager, tenant_id)
        milestones_data = bot.get_completion_milestones()

        return jsonify({
            'success': True,
            'completion_percentage': milestones_data.get('completion_percentage', 0),
            'milestones': milestones_data.get('milestones', {}),
            'capabilities': milestones_data.get('capabilities', {}),
            'next_steps': milestones_data.get('next_steps', []),
            'is_fully_setup': milestones_data.get('is_fully_setup', False)
        }), 200

    except Exception as e:
        logger.error(f"Get capabilities error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'server_error',
            'message': 'An error occurred fetching capabilities'
        }), 500
