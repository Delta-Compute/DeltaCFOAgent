"""
Tenant Configuration Management
Handles loading and caching of tenant-specific business configurations
"""

import json
import logging
from typing import Dict, List, Optional, Any
from functools import lru_cache
from datetime import datetime, timedelta

# Import tenant context management - NO hardcoded defaults
from tenant_context import get_current_tenant_id

logger = logging.getLogger(__name__)

# Global cache for tenant configurations (in-memory cache with TTL)
_config_cache = {}
_cache_ttl = timedelta(minutes=15)  # Cache configs for 15 minutes


def clear_tenant_config_cache(tenant_id: Optional[str] = None):
    """
    Clear the configuration cache for a specific tenant or all tenants.

    Args:
        tenant_id: Specific tenant to clear, or None for all tenants
    """
    global _config_cache

    if tenant_id:
        if tenant_id in _config_cache:
            del _config_cache[tenant_id]
            logger.info(f"Cleared config cache for tenant: {tenant_id}")
    else:
        _config_cache.clear()
        logger.info("Cleared all tenant config caches")


def _is_cache_valid(cache_entry: Dict) -> bool:
    """Check if a cache entry is still valid based on TTL."""
    if 'cached_at' not in cache_entry:
        return False

    cached_at = cache_entry['cached_at']
    return datetime.now() - cached_at < _cache_ttl


def get_tenant_configuration(tenant_id: str, config_type: str, use_cache: bool = True) -> Optional[Dict]:
    """
    Load tenant configuration from database with caching.

    Args:
        tenant_id: Tenant identifier
        config_type: Type of configuration to load ('general', 'entities', 'business_context',
                     'accounting_categories', 'pattern_matching_rules')
        use_cache: Whether to use cached configuration (default: True)

    Returns:
        Dict containing configuration data, or None if not found
    """
    global _config_cache

    # Check cache first
    cache_key = f"{tenant_id}:{config_type}"
    if use_cache and cache_key in _config_cache:
        cache_entry = _config_cache[cache_key]
        if _is_cache_valid(cache_entry):
            logger.debug(f"Cache hit for {cache_key}")
            return cache_entry['config_data']
        else:
            # Cache expired, remove it
            del _config_cache[cache_key]

    # Load from database
    try:
        from database import db_manager

        # Special handling for 'general' config type - query tenant_configuration table
        if config_type == 'general':
            query = """
                SELECT tenant_id, company_name, company_description, industry,
                       default_currency, timezone, primary_color, secondary_color, logo_url
                FROM tenant_configuration
                WHERE tenant_id = %s
            """
            result = db_manager.execute_query(query, (tenant_id,), fetch_one=True)

            if result:
                # Build config_data in the format expected by frontend
                if isinstance(result, tuple):
                    config_data = {
                        'tenant_id': result[0],
                        'company_name': result[1],
                        'company_description': result[2],
                        'industry': result[3],
                        'primary_currency': result[4],
                        'timezone': result[5],
                        'branding': {
                            'primary_color': result[6],
                            'secondary_color': result[7],
                            'logo_url': result[8]
                        }
                    }
                else:
                    config_data = {
                        'tenant_id': result.get('tenant_id'),
                        'company_name': result.get('company_name'),
                        'company_description': result.get('company_description'),
                        'industry': result.get('industry'),
                        'primary_currency': result.get('default_currency'),
                        'timezone': result.get('timezone'),
                        'branding': {
                            'primary_color': result.get('primary_color'),
                            'secondary_color': result.get('secondary_color'),
                            'logo_url': result.get('logo_url')
                        }
                    }

                # Cache the result
                _config_cache[cache_key] = {
                    'config_data': config_data,
                    'cached_at': datetime.now()
                }

                logger.info(f"Loaded general config for {tenant_id} from database")
                return config_data
            else:
                logger.warning(f"No general configuration found for {tenant_id}")
                return None

        # Standard config types - query tenant_configurations table
        query = """
            SELECT config_data
            FROM tenant_configurations
            WHERE tenant_id = %s AND config_type = %s
        """

        result = db_manager.execute_query(query, (tenant_id, config_type), fetch_one=True)

        if result:
            config_data = result[0] if isinstance(result, tuple) else result.get('config_data')

            # Parse JSON if it's a string
            if isinstance(config_data, str):
                config_data = json.loads(config_data)

            # Cache the result
            _config_cache[cache_key] = {
                'config_data': config_data,
                'cached_at': datetime.now()
            }

            logger.info(f"Loaded config for {tenant_id}/{config_type} from database")
            return config_data
        else:
            logger.warning(f"No configuration found for {tenant_id}/{config_type}")
            return None

    except Exception as e:
        logger.error(f"Error loading tenant configuration: {e}")
        return None


def get_tenant_entities(tenant_id: str) -> List[Dict]:
    """
    Get the list of business entities for a tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        List of entity dictionaries with 'name', 'description', 'entity_type', 'business_context'
    """
    config = get_tenant_configuration(tenant_id, 'entities')

    if config and 'entities' in config:
        return config['entities']

    # Fallback to empty list if no configuration found
    logger.warning(f"No entities configuration for tenant {tenant_id}, returning empty list")
    return []


def get_tenant_entity_families(tenant_id: str) -> Dict[str, List[str]]:
    """
    Get entity family relationships for a tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        Dictionary mapping family names to list of entity names
        Example: {'Delta': ['Delta LLC', 'Delta Prop Shop LLC'], 'Infinity': [...]}
    """
    config = get_tenant_configuration(tenant_id, 'entities')

    if config and 'entity_families' in config:
        return config['entity_families']

    return {}


def get_tenant_business_context(tenant_id: str) -> Dict:
    """
    Get business context information for a tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        Dictionary with industry, company info, and operational context
    """
    config = get_tenant_configuration(tenant_id, 'business_context')

    if config:
        return config

    # Fallback to generic context
    return {
        'industry': 'general',
        'company_name': 'Company',
        'company_size': 'small',
        'primary_activities': [],
        'geographic_regions': [],
        'transaction_patterns': []
    }


def get_tenant_accounting_categories(tenant_id: str) -> Dict[str, List[str]]:
    """
    Get accounting categories for a tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        Dictionary with revenue_categories, expense_categories, asset_categories, liability_categories
    """
    config = get_tenant_configuration(tenant_id, 'accounting_categories')

    if config:
        return config

    # Fallback to basic categories
    return {
        'revenue_categories': ['Revenue', 'Other Income'],
        'expense_categories': ['Operating Expenses', 'Cost of Goods Sold'],
        'asset_categories': ['Assets'],
        'liability_categories': ['Liabilities']
    }


def get_tenant_pattern_matching_rules(tenant_id: str) -> Dict:
    """
    Get pattern matching configuration rules for a tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        Dictionary with matching thresholds and behavior settings
    """
    config = get_tenant_configuration(tenant_id, 'pattern_matching_rules')

    if config:
        return config

    # Fallback to default rules
    return {
        'entity_matching': {
            'use_wallet_matching': False,
            'use_vendor_name_matching': True,
            'use_bank_identifier_matching': True,
            'similarity_threshold': 0.75,
            'min_pattern_matches': 2
        },
        'description_matching': {
            'min_transactions_to_suggest': 3,
            'max_suggestions': 10,
            'use_semantic_matching': True,
            'similarity_threshold': 0.70
        },
        'accounting_category_matching': {
            'min_transactions_to_suggest': 2,
            'max_suggestions': 8,
            'confidence_threshold': 0.60
        },
        'bulk_update_settings': {
            'auto_apply_threshold': 0.95,
            'require_user_confirmation': True,
            'max_bulk_update_count': 50
        }
    }


def update_tenant_configuration(tenant_id: str, config_type: str, config_data: Dict, updated_by: str = 'system') -> bool:
    """
    Update tenant configuration in database and clear cache.

    Args:
        tenant_id: Tenant identifier
        config_type: Type of configuration to update
        config_data: Configuration data dictionary
        updated_by: User or system that made the update

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from database import db_manager

        # Convert dict to JSON string
        config_json = json.dumps(config_data)

        query = """
            INSERT INTO tenant_configurations (tenant_id, config_type, config_data, created_by)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (tenant_id, config_type)
            DO UPDATE SET
                config_data = EXCLUDED.config_data,
                updated_at = CURRENT_TIMESTAMP
        """

        db_manager.execute_query(query, (tenant_id, config_type, config_json, updated_by))

        # Clear cache for this configuration
        clear_tenant_config_cache(tenant_id)

        logger.info(f"Updated configuration {tenant_id}/{config_type} by {updated_by}")
        return True

    except Exception as e:
        logger.error(f"Error updating tenant configuration: {e}")
        return False


def format_entities_for_prompt(entities: List[Dict]) -> str:
    """
    Format entity list for inclusion in AI prompts.

    Args:
        entities: List of entity dictionaries

    Returns:
        Formatted string for prompt inclusion
    """
    if not entities:
        return "No entities configured."

    formatted = []
    for entity in entities:
        name = entity.get('name', 'Unknown')
        description = entity.get('description', '')
        formatted.append(f"• {name}: {description}")

    return '\n'.join(formatted)


def get_all_entity_names(tenant_id: str) -> List[str]:
    """
    Get a simple list of all entity names for a tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        List of entity names
    """
    entities = get_tenant_entities(tenant_id)
    return [entity.get('name') for entity in entities if entity.get('name')]


def validate_tenant_configuration(config_type: str, config_data: Dict) -> tuple[bool, Optional[str]]:
    """
    Validate tenant configuration data structure.

    Args:
        config_type: Type of configuration
        config_data: Configuration data to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if config_type == 'entities':
        if 'entities' not in config_data:
            return False, "Missing 'entities' key in configuration"

        if not isinstance(config_data['entities'], list):
            return False, "'entities' must be a list"

        for entity in config_data['entities']:
            if 'name' not in entity:
                return False, "Each entity must have a 'name' field"

    elif config_type == 'business_context':
        required_fields = ['industry', 'company_name']
        for field in required_fields:
            if field not in config_data:
                return False, f"Missing required field: {field}"

    elif config_type == 'accounting_categories':
        required_fields = ['revenue_categories', 'expense_categories']
        for field in required_fields:
            if field not in config_data:
                return False, f"Missing required field: {field}"
            if not isinstance(config_data[field], list):
                return False, f"'{field}' must be a list"

    elif config_type == 'pattern_matching_rules':
        if 'entity_matching' not in config_data:
            return False, "Missing 'entity_matching' configuration"

    return True, None


# Convenience function for getting current tenant config
def get_current_tenant_entities() -> List[Dict]:
    """Get entities for the current tenant from request context."""
    tenant_id = get_current_tenant_id()
    return get_tenant_entities(tenant_id)


def get_current_tenant_business_context() -> Dict:
    """Get business context for the current tenant from request context."""
    tenant_id = get_current_tenant_id()
    return get_tenant_business_context(tenant_id)


def get_current_tenant_accounting_categories() -> Dict[str, List[str]]:
    """Get accounting categories for the current tenant from request context."""
    tenant_id = get_current_tenant_id()
    return get_tenant_accounting_categories(tenant_id)
