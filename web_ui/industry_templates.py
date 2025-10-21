"""
Industry Template Management
Handles loading and applying industry-specific configuration templates for new tenants
"""

import json
import os
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to industry templates
TEMPLATES_PATH = Path(__file__).parent.parent / 'config' / 'industry_templates.json'


def load_industry_templates() -> Dict:
    """
    Load all industry templates from JSON file.

    Returns:
        Dictionary with industry templates
    """
    try:
        with open(TEMPLATES_PATH, 'r') as f:
            templates = json.load(f)
        logger.info(f"Loaded {len(templates)} industry templates")
        return templates
    except FileNotFoundError:
        logger.error(f"Industry templates file not found: {TEMPLATES_PATH}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing industry templates JSON: {e}")
        return {}


def get_industry_template(industry_key: str) -> Optional[Dict]:
    """
    Get a specific industry template.

    Args:
        industry_key: Industry identifier (e.g., 'crypto_trading', 'e_commerce')

    Returns:
        Dictionary with template configuration or None if not found
    """
    templates = load_industry_templates()
    return templates.get(industry_key)


def list_available_industries() -> List[Dict]:
    """
    Get a list of all available industry templates with metadata.

    Returns:
        List of dictionaries with 'key', 'name', and 'description'
    """
    templates = load_industry_templates()

    industries = []
    for key, template in templates.items():
        industries.append({
            'key': key,
            'name': template.get('name', key),
            'description': template.get('description', ''),
            'features': template.get('business_context', {}).get('specialized_features', {})
        })

    return industries


def apply_industry_template(tenant_id: str, industry_key: str, company_name: str = None) -> bool:
    """
    Apply an industry template to a tenant's configuration.

    Args:
        tenant_id: Tenant identifier
        industry_key: Industry template to apply
        company_name: Optional company name to customize entities

    Returns:
        bool: True if successful, False otherwise
    """
    template = get_industry_template(industry_key)

    if not template:
        logger.error(f"Industry template not found: {industry_key}")
        return False

    try:
        from tenant_config import update_tenant_configuration

        # Customize entity names if company_name provided
        entities_config = template.get('entities', [])
        if company_name:
            entities_config = customize_entity_names(entities_config, company_name)

        # Apply entities configuration
        entities_data = {
            'entities': entities_config,
            'entity_families': template.get('entity_families', {})
        }
        update_tenant_configuration(tenant_id, 'entities', entities_data, 'industry_template')

        # Apply business context
        business_context = template.get('business_context', {})
        if company_name:
            business_context['company_name'] = company_name
        update_tenant_configuration(tenant_id, 'business_context', business_context, 'industry_template')

        # Apply accounting categories
        accounting_categories = template.get('accounting_categories', {})
        update_tenant_configuration(tenant_id, 'accounting_categories', accounting_categories, 'industry_template')

        # Apply pattern matching rules
        pattern_rules = template.get('pattern_matching_rules', {})
        update_tenant_configuration(tenant_id, 'pattern_matching_rules', pattern_rules, 'industry_template')

        logger.info(f"Successfully applied {industry_key} template to tenant {tenant_id}")
        return True

    except Exception as e:
        logger.error(f"Error applying industry template: {e}")
        return False


def customize_entity_names(entities: List[Dict], company_name: str) -> List[Dict]:
    """
    Customize entity names to include company name.

    Args:
        entities: List of entity dictionaries
        company_name: Company name to use

    Returns:
        List of customized entity dictionaries
    """
    customized = []

    replacements = {
        'Main Company': f'{company_name}',
        'Main Operating Company': f'{company_name}',
        'Main Firm': f'{company_name}',
        'Main Trading Entity': f'{company_name} Trading',
        'Prop Trading Division': f'{company_name} Prop Trading',
        'Validator Operations': f'{company_name} Validator',
        'Mining Operations': f'{company_name} Mining'
    }

    for entity in entities:
        new_entity = entity.copy()
        original_name = entity.get('name', '')

        # Apply replacement if found
        if original_name in replacements:
            new_entity['name'] = replacements[original_name]

        customized.append(new_entity)

    return customized


def get_template_preview(industry_key: str) -> Optional[Dict]:
    """
    Get a preview of what will be configured for an industry template.

    Args:
        industry_key: Industry template key

    Returns:
        Dictionary with preview information
    """
    template = get_industry_template(industry_key)

    if not template:
        return None

    entities = template.get('entities', [])
    accounting_cats = template.get('accounting_categories', {})

    return {
        'industry_name': template.get('name', ''),
        'description': template.get('description', ''),
        'entity_count': len(entities),
        'entity_names': [e.get('name') for e in entities],
        'revenue_categories_count': len(accounting_cats.get('revenue_categories', [])),
        'expense_categories_count': len(accounting_cats.get('expense_categories', [])),
        'features': template.get('business_context', {}).get('specialized_features', {}),
        'sample_revenue_categories': accounting_cats.get('revenue_categories', [])[:5],
        'sample_expense_categories': accounting_cats.get('expense_categories', [])[:5]
    }


def export_template_as_json(industry_key: str) -> Optional[str]:
    """
    Export an industry template as JSON string for download/sharing.

    Args:
        industry_key: Industry template key

    Returns:
        JSON string or None if template not found
    """
    template = get_industry_template(industry_key)

    if not template:
        return None

    return json.dumps(template, indent=2)


def import_custom_template(template_json: str, custom_key: str = None) -> tuple[bool, Optional[str]]:
    """
    Import a custom industry template from JSON.

    Args:
        template_json: JSON string with template configuration
        custom_key: Optional custom key for the template

    Returns:
        Tuple of (success, error_message)
    """
    try:
        template_data = json.loads(template_json)

        # Validate required fields
        required_fields = ['name', 'entities', 'business_context', 'accounting_categories']
        for field in required_fields:
            if field not in template_data:
                return False, f"Missing required field: {field}"

        # Load existing templates
        templates = load_industry_templates()

        # Generate key if not provided
        if not custom_key:
            custom_key = f"custom_{len([k for k in templates.keys() if k.startswith('custom_')]) + 1}"

        # Add to templates
        templates[custom_key] = template_data

        # Save back to file
        with open(TEMPLATES_PATH, 'w') as f:
            json.dump(templates, f, indent=2)

        logger.info(f"Successfully imported custom template: {custom_key}")
        return True, None

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {str(e)}"
    except Exception as e:
        return False, f"Error importing template: {str(e)}"


def get_recommended_categories_for_industry(industry_key: str, category_type: str = 'expense') -> List[str]:
    """
    Get recommended accounting categories for an industry.

    Args:
        industry_key: Industry template key
        category_type: 'revenue' or 'expense'

    Returns:
        List of recommended category names
    """
    template = get_industry_template(industry_key)

    if not template:
        return []

    accounting_cats = template.get('accounting_categories', {})

    if category_type == 'revenue':
        return accounting_cats.get('revenue_categories', [])
    elif category_type == 'expense':
        return accounting_cats.get('expense_categories', [])
    elif category_type == 'asset':
        return accounting_cats.get('asset_categories', [])
    elif category_type == 'liability':
        return accounting_cats.get('liability_categories', [])
    else:
        return []
