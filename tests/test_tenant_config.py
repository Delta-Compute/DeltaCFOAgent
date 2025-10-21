#!/usr/bin/env python3
"""
Unit Tests for Tenant Configuration Management
Tests tenant_config.py functions for multi-tenant system
"""

import sys
import os
import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_ui'))

from tenant_config import (
    get_current_tenant_id,
    get_tenant_configuration,
    get_tenant_entities,
    get_tenant_entity_families,
    get_tenant_business_context,
    get_tenant_accounting_categories,
    get_tenant_pattern_matching_rules,
    update_tenant_configuration,
    validate_tenant_configuration,
    format_entities_for_prompt,
    get_all_entity_names,
    clear_tenant_config_cache,
    _is_cache_valid
)


class TestTenantConfigCache(unittest.TestCase):
    """Test configuration caching functionality"""

    def setUp(self):
        """Clear cache before each test"""
        clear_tenant_config_cache()

    def test_cache_validation_fresh(self):
        """Test that fresh cache entries are valid"""
        cache_entry = {
            'cached_at': datetime.now(),
            'config_data': {'test': 'data'}
        }
        self.assertTrue(_is_cache_valid(cache_entry))

    def test_cache_validation_expired(self):
        """Test that expired cache entries are invalid"""
        cache_entry = {
            'cached_at': datetime.now() - timedelta(minutes=20),
            'config_data': {'test': 'data'}
        }
        self.assertFalse(_is_cache_valid(cache_entry))

    def test_cache_validation_missing_timestamp(self):
        """Test that cache entries without timestamp are invalid"""
        cache_entry = {
            'config_data': {'test': 'data'}
        }
        self.assertFalse(_is_cache_valid(cache_entry))

    def test_clear_specific_tenant_cache(self):
        """Test clearing cache for specific tenant"""
        # This will be tested with mock database
        clear_tenant_config_cache('test_tenant')
        # Should not raise any errors


class TestGetCurrentTenantId(unittest.TestCase):
    """Test tenant ID detection"""

    def test_default_tenant_id(self):
        """Test that default tenant is 'delta'"""
        tenant_id = get_current_tenant_id()
        self.assertEqual(tenant_id, 'delta')


class TestValidateTenantConfiguration(unittest.TestCase):
    """Test configuration validation"""

    def test_validate_entities_valid(self):
        """Test valid entities configuration"""
        config_data = {
            'entities': [
                {'name': 'Test Entity', 'description': 'Test'}
            ]
        }
        is_valid, error = validate_tenant_configuration('entities', config_data)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_entities_missing_key(self):
        """Test entities validation with missing 'entities' key"""
        config_data = {'wrong_key': []}
        is_valid, error = validate_tenant_configuration('entities', config_data)
        self.assertFalse(is_valid)
        self.assertIn('entities', error.lower())

    def test_validate_entities_not_list(self):
        """Test entities validation when entities is not a list"""
        config_data = {'entities': 'not a list'}
        is_valid, error = validate_tenant_configuration('entities', config_data)
        self.assertFalse(is_valid)
        self.assertIn('list', error.lower())

    def test_validate_entities_missing_name(self):
        """Test entities validation when entity missing name"""
        config_data = {
            'entities': [
                {'description': 'No name field'}
            ]
        }
        is_valid, error = validate_tenant_configuration('entities', config_data)
        self.assertFalse(is_valid)
        self.assertIn('name', error.lower())

    def test_validate_business_context_valid(self):
        """Test valid business context configuration"""
        config_data = {
            'industry': 'crypto_trading',
            'company_name': 'Test Company'
        }
        is_valid, error = validate_tenant_configuration('business_context', config_data)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_business_context_missing_industry(self):
        """Test business context validation missing industry"""
        config_data = {'company_name': 'Test'}
        is_valid, error = validate_tenant_configuration('business_context', config_data)
        self.assertFalse(is_valid)
        self.assertIn('industry', error.lower())

    def test_validate_accounting_categories_valid(self):
        """Test valid accounting categories"""
        config_data = {
            'revenue_categories': ['Revenue 1', 'Revenue 2'],
            'expense_categories': ['Expense 1', 'Expense 2']
        }
        is_valid, error = validate_tenant_configuration('accounting_categories', config_data)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_accounting_categories_missing_revenue(self):
        """Test accounting categories missing revenue_categories"""
        config_data = {
            'expense_categories': ['Expense 1']
        }
        is_valid, error = validate_tenant_configuration('accounting_categories', config_data)
        self.assertFalse(is_valid)
        self.assertIn('revenue_categories', error.lower())

    def test_validate_accounting_categories_not_list(self):
        """Test accounting categories when not a list"""
        config_data = {
            'revenue_categories': 'not a list',
            'expense_categories': []
        }
        is_valid, error = validate_tenant_configuration('accounting_categories', config_data)
        self.assertFalse(is_valid)
        self.assertIn('list', error.lower())

    def test_validate_pattern_matching_rules_valid(self):
        """Test valid pattern matching rules"""
        config_data = {
            'entity_matching': {
                'use_wallet_matching': True,
                'similarity_threshold': 0.75
            }
        }
        is_valid, error = validate_tenant_configuration('pattern_matching_rules', config_data)
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_pattern_matching_rules_missing_entity_matching(self):
        """Test pattern matching rules missing entity_matching"""
        config_data = {
            'other_config': {}
        }
        is_valid, error = validate_tenant_configuration('pattern_matching_rules', config_data)
        self.assertFalse(is_valid)
        self.assertIn('entity_matching', error.lower())


class TestFormatEntitiesForPrompt(unittest.TestCase):
    """Test entity formatting for AI prompts"""

    def test_format_entities_normal(self):
        """Test formatting normal entity list"""
        entities = [
            {'name': 'Entity 1', 'description': 'Description 1'},
            {'name': 'Entity 2', 'description': 'Description 2'}
        ]
        result = format_entities_for_prompt(entities)
        self.assertIn('Entity 1', result)
        self.assertIn('Description 1', result)
        self.assertIn('Entity 2', result)
        self.assertIn('Description 2', result)
        self.assertIn('•', result)  # Check for bullet points

    def test_format_entities_empty(self):
        """Test formatting empty entity list"""
        result = format_entities_for_prompt([])
        self.assertEqual(result, "No entities configured.")

    def test_format_entities_missing_fields(self):
        """Test formatting entities with missing fields"""
        entities = [
            {'name': 'Entity 1'},  # Missing description
            {'description': 'Description only'}  # Missing name
        ]
        result = format_entities_for_prompt(entities)
        self.assertIn('Entity 1', result)


class TestGetAllEntityNames(unittest.TestCase):
    """Test extracting entity names"""

    @patch('tenant_config.get_tenant_entities')
    def test_get_all_entity_names(self, mock_get_entities):
        """Test getting all entity names"""
        mock_get_entities.return_value = [
            {'name': 'Entity 1', 'description': 'Desc 1'},
            {'name': 'Entity 2', 'description': 'Desc 2'}
        ]

        result = get_all_entity_names('test_tenant')
        self.assertEqual(result, ['Entity 1', 'Entity 2'])

    @patch('tenant_config.get_tenant_entities')
    def test_get_all_entity_names_empty(self, mock_get_entities):
        """Test getting entity names from empty list"""
        mock_get_entities.return_value = []
        result = get_all_entity_names('test_tenant')
        self.assertEqual(result, [])

    @patch('tenant_config.get_tenant_entities')
    def test_get_all_entity_names_missing_name(self, mock_get_entities):
        """Test getting entity names when some have no name"""
        mock_get_entities.return_value = [
            {'name': 'Entity 1'},
            {'description': 'No name'},
            {'name': 'Entity 2'}
        ]
        result = get_all_entity_names('test_tenant')
        # Should only return entities with names
        self.assertEqual(len(result), 2)


class TestGetTenantConfiguration(unittest.TestCase):
    """Test loading tenant configuration from database"""

    @patch('tenant_config.db_manager')
    def test_get_tenant_configuration_success(self, mock_db_manager):
        """Test successful configuration load"""
        mock_config = {
            'entities': [{'name': 'Test Entity'}]
        }

        # Mock database response
        mock_db_manager.execute_query.return_value = (json.dumps(mock_config),)

        result = get_tenant_configuration('test_tenant', 'entities', use_cache=False)

        self.assertIsNotNone(result)
        self.assertEqual(result['entities'][0]['name'], 'Test Entity')

    @patch('tenant_config.db_manager')
    def test_get_tenant_configuration_not_found(self, mock_db_manager):
        """Test configuration not found"""
        mock_db_manager.execute_query.return_value = None

        result = get_tenant_configuration('test_tenant', 'entities', use_cache=False)
        self.assertIsNone(result)

    @patch('tenant_config.db_manager')
    def test_get_tenant_configuration_json_string(self, mock_db_manager):
        """Test configuration returned as JSON string"""
        mock_config = {'test': 'data'}
        mock_db_manager.execute_query.return_value = (json.dumps(mock_config),)

        result = get_tenant_configuration('test_tenant', 'entities', use_cache=False)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)

    @patch('tenant_config.db_manager')
    def test_get_tenant_configuration_already_dict(self, mock_db_manager):
        """Test configuration already parsed as dict"""
        mock_config = {'test': 'data'}
        mock_result = Mock()
        mock_result.get.return_value = mock_config
        mock_db_manager.execute_query.return_value = mock_result

        result = get_tenant_configuration('test_tenant', 'entities', use_cache=False)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)


class TestGetTenantEntities(unittest.TestCase):
    """Test getting tenant entities"""

    @patch('tenant_config.get_tenant_configuration')
    def test_get_tenant_entities_success(self, mock_get_config):
        """Test getting entities successfully"""
        mock_config = {
            'entities': [
                {'name': 'Entity 1', 'description': 'Desc 1'},
                {'name': 'Entity 2', 'description': 'Desc 2'}
            ]
        }
        mock_get_config.return_value = mock_config

        result = get_tenant_entities('test_tenant')

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'Entity 1')

    @patch('tenant_config.get_tenant_configuration')
    def test_get_tenant_entities_no_config(self, mock_get_config):
        """Test getting entities when no config exists"""
        mock_get_config.return_value = None

        result = get_tenant_entities('test_tenant')

        self.assertEqual(result, [])

    @patch('tenant_config.get_tenant_configuration')
    def test_get_tenant_entities_missing_key(self, mock_get_config):
        """Test getting entities when config missing 'entities' key"""
        mock_get_config.return_value = {'wrong_key': []}

        result = get_tenant_entities('test_tenant')

        self.assertEqual(result, [])


class TestGetTenantEntityFamilies(unittest.TestCase):
    """Test getting entity families"""

    @patch('tenant_config.get_tenant_configuration')
    def test_get_entity_families_success(self, mock_get_config):
        """Test getting entity families successfully"""
        mock_config = {
            'entity_families': {
                'Family 1': ['Entity A', 'Entity B'],
                'Family 2': ['Entity C']
            }
        }
        mock_get_config.return_value = mock_config

        result = get_tenant_entity_families('test_tenant')

        self.assertEqual(len(result), 2)
        self.assertEqual(result['Family 1'], ['Entity A', 'Entity B'])

    @patch('tenant_config.get_tenant_configuration')
    def test_get_entity_families_no_config(self, mock_get_config):
        """Test getting entity families when no config"""
        mock_get_config.return_value = None

        result = get_tenant_entity_families('test_tenant')

        self.assertEqual(result, {})


class TestGetTenantBusinessContext(unittest.TestCase):
    """Test getting business context"""

    @patch('tenant_config.get_tenant_configuration')
    def test_get_business_context_success(self, mock_get_config):
        """Test getting business context successfully"""
        mock_config = {
            'industry': 'crypto_trading',
            'company_name': 'Test Company'
        }
        mock_get_config.return_value = mock_config

        result = get_tenant_business_context('test_tenant')

        self.assertEqual(result['industry'], 'crypto_trading')
        self.assertEqual(result['company_name'], 'Test Company')

    @patch('tenant_config.get_tenant_configuration')
    def test_get_business_context_fallback(self, mock_get_config):
        """Test getting business context with fallback"""
        mock_get_config.return_value = None

        result = get_tenant_business_context('test_tenant')

        # Should return fallback values
        self.assertEqual(result['industry'], 'general')
        self.assertEqual(result['company_name'], 'Company')
        self.assertIsInstance(result['primary_activities'], list)


class TestGetTenantAccountingCategories(unittest.TestCase):
    """Test getting accounting categories"""

    @patch('tenant_config.get_tenant_configuration')
    def test_get_accounting_categories_success(self, mock_get_config):
        """Test getting accounting categories successfully"""
        mock_config = {
            'revenue_categories': ['Revenue 1', 'Revenue 2'],
            'expense_categories': ['Expense 1', 'Expense 2']
        }
        mock_get_config.return_value = mock_config

        result = get_tenant_accounting_categories('test_tenant')

        self.assertEqual(len(result['revenue_categories']), 2)
        self.assertEqual(len(result['expense_categories']), 2)

    @patch('tenant_config.get_tenant_configuration')
    def test_get_accounting_categories_fallback(self, mock_get_config):
        """Test getting accounting categories with fallback"""
        mock_get_config.return_value = None

        result = get_tenant_accounting_categories('test_tenant')

        # Should return fallback categories
        self.assertIn('revenue_categories', result)
        self.assertIn('expense_categories', result)
        self.assertIsInstance(result['revenue_categories'], list)


class TestGetTenantPatternMatchingRules(unittest.TestCase):
    """Test getting pattern matching rules"""

    @patch('tenant_config.get_tenant_configuration')
    def test_get_pattern_matching_rules_success(self, mock_get_config):
        """Test getting pattern matching rules successfully"""
        mock_config = {
            'entity_matching': {
                'use_wallet_matching': True,
                'similarity_threshold': 0.8
            },
            'description_matching': {
                'min_transactions_to_suggest': 5
            }
        }
        mock_get_config.return_value = mock_config

        result = get_tenant_pattern_matching_rules('test_tenant')

        self.assertTrue(result['entity_matching']['use_wallet_matching'])
        self.assertEqual(result['entity_matching']['similarity_threshold'], 0.8)

    @patch('tenant_config.get_tenant_configuration')
    def test_get_pattern_matching_rules_fallback(self, mock_get_config):
        """Test getting pattern matching rules with fallback"""
        mock_get_config.return_value = None

        result = get_tenant_pattern_matching_rules('test_tenant')

        # Should return fallback rules
        self.assertIn('entity_matching', result)
        self.assertIn('description_matching', result)
        self.assertIsInstance(result['entity_matching'], dict)


class TestUpdateTenantConfiguration(unittest.TestCase):
    """Test updating tenant configuration"""

    @patch('tenant_config.db_manager')
    @patch('tenant_config.clear_tenant_config_cache')
    def test_update_configuration_success(self, mock_clear_cache, mock_db_manager):
        """Test successful configuration update"""
        config_data = {
            'entities': [{'name': 'New Entity'}]
        }

        mock_db_manager.execute_query.return_value = True

        result = update_tenant_configuration('test_tenant', 'entities', config_data, 'test_user')

        self.assertTrue(result)
        mock_clear_cache.assert_called_once_with('test_tenant')

    @patch('tenant_config.db_manager')
    def test_update_configuration_failure(self, mock_db_manager):
        """Test configuration update failure"""
        config_data = {'test': 'data'}

        mock_db_manager.execute_query.side_effect = Exception('Database error')

        result = update_tenant_configuration('test_tenant', 'entities', config_data)

        self.assertFalse(result)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions for current tenant"""

    @patch('tenant_config.get_current_tenant_id')
    @patch('tenant_config.get_tenant_entities')
    def test_get_current_tenant_entities(self, mock_get_entities, mock_get_tenant_id):
        """Test convenience function for getting current tenant entities"""
        from tenant_config import get_current_tenant_entities

        mock_get_tenant_id.return_value = 'test_tenant'
        mock_get_entities.return_value = [{'name': 'Entity 1'}]

        result = get_current_tenant_entities()

        mock_get_entities.assert_called_once_with('test_tenant')
        self.assertEqual(len(result), 1)

    @patch('tenant_config.get_current_tenant_id')
    @patch('tenant_config.get_tenant_business_context')
    def test_get_current_tenant_business_context(self, mock_get_context, mock_get_tenant_id):
        """Test convenience function for getting current tenant business context"""
        from tenant_config import get_current_tenant_business_context

        mock_get_tenant_id.return_value = 'test_tenant'
        mock_get_context.return_value = {'industry': 'crypto_trading'}

        result = get_current_tenant_business_context()

        mock_get_context.assert_called_once_with('test_tenant')
        self.assertEqual(result['industry'], 'crypto_trading')


def run_tests():
    """Run all tenant config tests"""
    print("=" * 70)
    print("Running Tenant Configuration Unit Tests")
    print("=" * 70)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTenantConfigCache))
    suite.addTests(loader.loadTestsFromTestCase(TestGetCurrentTenantId))
    suite.addTests(loader.loadTestsFromTestCase(TestValidateTenantConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestFormatEntitiesForPrompt))
    suite.addTests(loader.loadTestsFromTestCase(TestGetAllEntityNames))
    suite.addTests(loader.loadTestsFromTestCase(TestGetTenantConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestGetTenantEntities))
    suite.addTests(loader.loadTestsFromTestCase(TestGetTenantEntityFamilies))
    suite.addTests(loader.loadTestsFromTestCase(TestGetTenantBusinessContext))
    suite.addTests(loader.loadTestsFromTestCase(TestGetTenantAccountingCategories))
    suite.addTests(loader.loadTestsFromTestCase(TestGetTenantPatternMatchingRules))
    suite.addTests(loader.loadTestsFromTestCase(TestUpdateTenantConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestConvenienceFunctions))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
