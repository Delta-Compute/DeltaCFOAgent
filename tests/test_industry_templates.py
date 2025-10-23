#!/usr/bin/env python3
"""
Unit Tests for Industry Templates
Tests industry_templates.py functions for template management
"""

import sys
import os
import json
import unittest
from unittest.mock import Mock, patch, mock_open, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_ui'))

from industry_templates import (
    load_industry_templates,
    get_industry_template,
    list_available_industries,
    apply_industry_template,
    customize_entity_names,
    get_template_preview,
    export_template_as_json,
    import_custom_template,
    get_recommended_categories_for_industry
)


class TestLoadIndustryTemplates(unittest.TestCase):
    """Test loading industry templates from JSON file"""

    @patch('builtins.open', new_callable=mock_open, read_data='{"crypto_trading": {"name": "Crypto"}}')
    def test_load_templates_success(self, mock_file):
        """Test successful template loading"""
        result = load_industry_templates()

        self.assertIsInstance(result, dict)
        self.assertIn('crypto_trading', result)

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_templates_file_not_found(self, mock_file):
        """Test handling of missing template file"""
        result = load_industry_templates()

        self.assertEqual(result, {})

    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    def test_load_templates_invalid_json(self, mock_file):
        """Test handling of invalid JSON"""
        result = load_industry_templates()

        self.assertEqual(result, {})


class TestGetIndustryTemplate(unittest.TestCase):
    """Test getting specific industry template"""

    @patch('industry_templates.load_industry_templates')
    def test_get_template_success(self, mock_load):
        """Test getting template that exists"""
        mock_load.return_value = {
            'crypto_trading': {
                'name': 'Crypto Trading',
                'entities': []
            }
        }

        result = get_industry_template('crypto_trading')

        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Crypto Trading')

    @patch('industry_templates.load_industry_templates')
    def test_get_template_not_found(self, mock_load):
        """Test getting template that doesn't exist"""
        mock_load.return_value = {}

        result = get_industry_template('nonexistent')

        self.assertIsNone(result)


class TestListAvailableIndustries(unittest.TestCase):
    """Test listing available industry templates"""

    @patch('industry_templates.load_industry_templates')
    def test_list_industries(self, mock_load):
        """Test listing all available industries"""
        mock_load.return_value = {
            'crypto_trading': {
                'name': 'Crypto Trading',
                'description': 'For crypto businesses',
                'business_context': {
                    'specialized_features': {
                        'crypto_enabled': True
                    }
                }
            },
            'e_commerce': {
                'name': 'E-Commerce',
                'description': 'For online retail'
            }
        }

        result = list_available_industries()

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['key'], 'crypto_trading')
        self.assertEqual(result[0]['name'], 'Crypto Trading')
        self.assertIn('features', result[0])

    @patch('industry_templates.load_industry_templates')
    def test_list_industries_empty(self, mock_load):
        """Test listing when no templates exist"""
        mock_load.return_value = {}

        result = list_available_industries()

        self.assertEqual(len(result), 0)


class TestCustomizeEntityNames(unittest.TestCase):
    """Test customizing entity names with company name"""

    def test_customize_main_company(self):
        """Test customizing 'Main Company' entity"""
        entities = [
            {'name': 'Main Company', 'description': 'Main entity'}
        ]

        result = customize_entity_names(entities, 'Acme Corp')

        self.assertEqual(result[0]['name'], 'Acme Corp')
        self.assertEqual(result[0]['description'], 'Main entity')

    def test_customize_multiple_entities(self):
        """Test customizing multiple entity types"""
        entities = [
            {'name': 'Main Operating Company', 'description': 'Main'},
            {'name': 'Personal', 'description': 'Personal expenses'}
        ]

        result = customize_entity_names(entities, 'Acme Corp')

        self.assertEqual(result[0]['name'], 'Acme Corp')
        self.assertEqual(result[1]['name'], 'Personal')  # Should not change

    def test_customize_trading_entities(self):
        """Test customizing trading-specific entities"""
        entities = [
            {'name': 'Main Trading Entity', 'description': 'Trading'},
            {'name': 'Prop Trading Division', 'description': 'Prop trading'}
        ]

        result = customize_entity_names(entities, 'Acme Corp')

        self.assertEqual(result[0]['name'], 'Acme Corp Trading')
        self.assertEqual(result[1]['name'], 'Acme Corp Prop Trading')

    def test_customize_preserves_other_fields(self):
        """Test that customization preserves other entity fields"""
        entities = [
            {
                'name': 'Main Company',
                'description': 'Main entity',
                'entity_type': 'main',
                'business_context': 'Operations'
            }
        ]

        result = customize_entity_names(entities, 'Acme Corp')

        self.assertEqual(result[0]['entity_type'], 'main')
        self.assertEqual(result[0]['business_context'], 'Operations')


class TestApplyIndustryTemplate(unittest.TestCase):
    """Test applying industry template to tenant"""

    @patch('industry_templates.get_industry_template')
    @patch('industry_templates.update_tenant_configuration')
    def test_apply_template_success(self, mock_update, mock_get_template):
        """Test successful template application"""
        mock_template = {
            'entities': [{'name': 'Entity 1'}],
            'entity_families': {},
            'business_context': {'industry': 'crypto_trading'},
            'accounting_categories': {
                'revenue_categories': [],
                'expense_categories': []
            },
            'pattern_matching_rules': {}
        }
        mock_get_template.return_value = mock_template
        mock_update.return_value = True

        result = apply_industry_template('test_tenant', 'crypto_trading')

        self.assertTrue(result)
        # Should call update 4 times (entities, context, categories, rules)
        self.assertEqual(mock_update.call_count, 4)

    @patch('industry_templates.get_industry_template')
    def test_apply_template_not_found(self, mock_get_template):
        """Test applying non-existent template"""
        mock_get_template.return_value = None

        result = apply_industry_template('test_tenant', 'nonexistent')

        self.assertFalse(result)

    @patch('industry_templates.get_industry_template')
    @patch('industry_templates.customize_entity_names')
    @patch('industry_templates.update_tenant_configuration')
    def test_apply_template_with_company_name(self, mock_update, mock_customize, mock_get_template):
        """Test applying template with company name customization"""
        mock_template = {
            'entities': [{'name': 'Main Company'}],
            'entity_families': {},
            'business_context': {'industry': 'e_commerce'},
            'accounting_categories': {
                'revenue_categories': [],
                'expense_categories': []
            },
            'pattern_matching_rules': {}
        }
        mock_get_template.return_value = mock_template
        mock_customize.return_value = [{'name': 'Acme Corp'}]
        mock_update.return_value = True

        result = apply_industry_template('test_tenant', 'e_commerce', 'Acme Corp')

        self.assertTrue(result)
        mock_customize.assert_called_once()
        # Check that business context has company_name
        calls = mock_update.call_args_list
        business_context_call = [c for c in calls if c[0][1] == 'business_context'][0]
        self.assertEqual(business_context_call[0][2]['company_name'], 'Acme Corp')


class TestGetTemplatePreview(unittest.TestCase):
    """Test getting template preview"""

    @patch('industry_templates.get_industry_template')
    def test_preview_success(self, mock_get_template):
        """Test successful preview generation"""
        mock_template = {
            'name': 'Crypto Trading',
            'description': 'For crypto businesses',
            'entities': [
                {'name': 'Entity 1'},
                {'name': 'Entity 2'}
            ],
            'accounting_categories': {
                'revenue_categories': ['Rev 1', 'Rev 2', 'Rev 3'],
                'expense_categories': ['Exp 1', 'Exp 2']
            },
            'business_context': {
                'specialized_features': {
                    'crypto_enabled': True
                }
            }
        }
        mock_get_template.return_value = mock_template

        result = get_template_preview('crypto_trading')

        self.assertIsNotNone(result)
        self.assertEqual(result['industry_name'], 'Crypto Trading')
        self.assertEqual(result['entity_count'], 2)
        self.assertEqual(len(result['entity_names']), 2)
        self.assertEqual(result['revenue_categories_count'], 3)
        self.assertEqual(len(result['sample_revenue_categories']), 3)
        self.assertTrue(result['features']['crypto_enabled'])

    @patch('industry_templates.get_industry_template')
    def test_preview_not_found(self, mock_get_template):
        """Test preview of non-existent template"""
        mock_get_template.return_value = None

        result = get_template_preview('nonexistent')

        self.assertIsNone(result)


class TestExportTemplateAsJson(unittest.TestCase):
    """Test exporting template as JSON string"""

    @patch('industry_templates.get_industry_template')
    def test_export_success(self, mock_get_template):
        """Test successful template export"""
        mock_template = {
            'name': 'Test Template',
            'entities': []
        }
        mock_get_template.return_value = mock_template

        result = export_template_as_json('test_template')

        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)
        # Should be valid JSON
        parsed = json.loads(result)
        self.assertEqual(parsed['name'], 'Test Template')

    @patch('industry_templates.get_industry_template')
    def test_export_not_found(self, mock_get_template):
        """Test export of non-existent template"""
        mock_get_template.return_value = None

        result = export_template_as_json('nonexistent')

        self.assertIsNone(result)


class TestImportCustomTemplate(unittest.TestCase):
    """Test importing custom templates"""

    @patch('industry_templates.load_industry_templates')
    @patch('builtins.open', new_callable=mock_open)
    def test_import_success(self, mock_file, mock_load):
        """Test successful template import"""
        mock_load.return_value = {}

        template_json = json.dumps({
            'name': 'Custom Template',
            'entities': [{'name': 'Entity 1'}],
            'business_context': {'industry': 'custom'},
            'accounting_categories': {
                'revenue_categories': [],
                'expense_categories': []
            }
        })

        success, error = import_custom_template(template_json, 'custom_1')

        self.assertTrue(success)
        self.assertIsNone(error)
        mock_file.assert_called_once()

    def test_import_invalid_json(self):
        """Test import with invalid JSON"""
        success, error = import_custom_template('invalid json', 'custom_1')

        self.assertFalse(success)
        self.assertIn('Invalid JSON', error)

    @patch('industry_templates.load_industry_templates')
    def test_import_missing_required_field(self, mock_load):
        """Test import with missing required fields"""
        mock_load.return_value = {}

        template_json = json.dumps({
            'name': 'Incomplete Template'
            # Missing entities, business_context, accounting_categories
        })

        success, error = import_custom_template(template_json, 'custom_1')

        self.assertFalse(success)
        self.assertIn('Missing required field', error)

    @patch('industry_templates.load_industry_templates')
    @patch('builtins.open', new_callable=mock_open)
    def test_import_auto_key_generation(self, mock_file, mock_load):
        """Test import with automatic key generation"""
        mock_load.return_value = {
            'custom_1': {},
            'custom_2': {}
        }

        template_json = json.dumps({
            'name': 'Custom Template',
            'entities': [{'name': 'Entity 1'}],
            'business_context': {'industry': 'custom'},
            'accounting_categories': {
                'revenue_categories': [],
                'expense_categories': []
            }
        })

        success, error = import_custom_template(template_json)  # No key provided

        self.assertTrue(success)
        # Should have called json.dump with key 'custom_3'
        mock_file.assert_called_once()


class TestGetRecommendedCategories(unittest.TestCase):
    """Test getting recommended categories for industry"""

    @patch('industry_templates.get_industry_template')
    def test_get_revenue_categories(self, mock_get_template):
        """Test getting revenue categories"""
        mock_template = {
            'accounting_categories': {
                'revenue_categories': ['Rev 1', 'Rev 2'],
                'expense_categories': ['Exp 1', 'Exp 2']
            }
        }
        mock_get_template.return_value = mock_template

        result = get_recommended_categories_for_industry('crypto_trading', 'revenue')

        self.assertEqual(result, ['Rev 1', 'Rev 2'])

    @patch('industry_templates.get_industry_template')
    def test_get_expense_categories(self, mock_get_template):
        """Test getting expense categories"""
        mock_template = {
            'accounting_categories': {
                'revenue_categories': ['Rev 1'],
                'expense_categories': ['Exp 1', 'Exp 2', 'Exp 3']
            }
        }
        mock_get_template.return_value = mock_template

        result = get_recommended_categories_for_industry('e_commerce', 'expense')

        self.assertEqual(result, ['Exp 1', 'Exp 2', 'Exp 3'])

    @patch('industry_templates.get_industry_template')
    def test_get_asset_categories(self, mock_get_template):
        """Test getting asset categories"""
        mock_template = {
            'accounting_categories': {
                'asset_categories': ['Asset 1', 'Asset 2']
            }
        }
        mock_get_template.return_value = mock_template

        result = get_recommended_categories_for_industry('saas', 'asset')

        self.assertEqual(result, ['Asset 1', 'Asset 2'])

    @patch('industry_templates.get_industry_template')
    def test_get_categories_template_not_found(self, mock_get_template):
        """Test getting categories when template doesn't exist"""
        mock_get_template.return_value = None

        result = get_recommended_categories_for_industry('nonexistent', 'revenue')

        self.assertEqual(result, [])

    @patch('industry_templates.get_industry_template')
    def test_get_categories_invalid_type(self, mock_get_template):
        """Test getting categories with invalid type"""
        mock_template = {
            'accounting_categories': {
                'revenue_categories': ['Rev 1']
            }
        }
        mock_get_template.return_value = mock_template

        result = get_recommended_categories_for_industry('crypto_trading', 'invalid_type')

        self.assertEqual(result, [])


def run_tests():
    """Run all industry template tests"""
    print("=" * 70)
    print("Running Industry Templates Unit Tests")
    print("=" * 70)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLoadIndustryTemplates))
    suite.addTests(loader.loadTestsFromTestCase(TestGetIndustryTemplate))
    suite.addTests(loader.loadTestsFromTestCase(TestListAvailableIndustries))
    suite.addTests(loader.loadTestsFromTestCase(TestCustomizeEntityNames))
    suite.addTests(loader.loadTestsFromTestCase(TestApplyIndustryTemplate))
    suite.addTests(loader.loadTestsFromTestCase(TestGetTemplatePreview))
    suite.addTests(loader.loadTestsFromTestCase(TestExportTemplateAsJson))
    suite.addTests(loader.loadTestsFromTestCase(TestImportCustomTemplate))
    suite.addTests(loader.loadTestsFromTestCase(TestGetRecommendedCategories))

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
