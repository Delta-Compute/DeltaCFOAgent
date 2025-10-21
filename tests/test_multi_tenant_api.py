#!/usr/bin/env python3
"""
Integration Tests for Multi-Tenant API Endpoints
Tests API routes for tenant configuration management
"""

import sys
import os
import json
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_ui'))


class TestTenantConfigAPIEndpoints(unittest.TestCase):
    """Test tenant configuration API endpoints"""

    def setUp(self):
        """Set up test Flask app"""
        # Import app here to avoid loading it at module level
        from app_db import app
        app.config['TESTING'] = True
        self.app = app.test_client()

    @patch('app_db.get_tenant_configuration')
    def test_get_tenant_config_success(self, mock_get_config):
        """Test GET /api/tenant/config/<type> success"""
        mock_get_config.return_value = {
            'entities': [{'name': 'Test Entity'}]
        }

        response = self.app.get('/api/tenant/config/entities')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['config_type'], 'entities')
        self.assertIn('config_data', data)

    @patch('app_db.get_tenant_configuration')
    def test_get_tenant_config_not_found(self, mock_get_config):
        """Test GET /api/tenant/config/<type> not found"""
        mock_get_config.return_value = None

        response = self.app.get('/api/tenant/config/nonexistent')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(data['success'])

    @patch('app_db.validate_tenant_configuration')
    @patch('app_db.update_tenant_configuration')
    def test_update_tenant_config_success(self, mock_update, mock_validate):
        """Test PUT /api/tenant/config/<type> success"""
        mock_validate.return_value = (True, None)
        mock_update.return_value = True

        config_data = {
            'config_data': {
                'entities': [{'name': 'New Entity'}]
            }
        }

        response = self.app.put(
            '/api/tenant/config/entities',
            data=json.dumps(config_data),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        mock_update.assert_called_once()

    def test_update_tenant_config_missing_data(self):
        """Test PUT /api/tenant/config/<type> missing config_data"""
        response = self.app.put(
            '/api/tenant/config/entities',
            data=json.dumps({}),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('Missing config_data', data['error'])

    @patch('app_db.validate_tenant_configuration')
    def test_update_tenant_config_invalid_data(self, mock_validate):
        """Test PUT /api/tenant/config/<type> invalid config data"""
        mock_validate.return_value = (False, 'Invalid configuration')

        config_data = {
            'config_data': {
                'invalid': 'data'
            }
        }

        response = self.app.put(
            '/api/tenant/config/entities',
            data=json.dumps(config_data),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('Invalid configuration', data['error'])


class TestIndustryTemplateAPIEndpoints(unittest.TestCase):
    """Test industry template API endpoints"""

    def setUp(self):
        """Set up test Flask app"""
        from app_db import app
        app.config['TESTING'] = True
        self.app = app.test_client()

    @patch('app_db.list_available_industries')
    def test_list_industries(self, mock_list):
        """Test GET /api/tenant/industries"""
        mock_list.return_value = [
            {
                'key': 'crypto_trading',
                'name': 'Crypto Trading',
                'description': 'For crypto businesses'
            },
            {
                'key': 'e_commerce',
                'name': 'E-Commerce',
                'description': 'For online retail'
            }
        ]

        response = self.app.get('/api/tenant/industries')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['industries']), 2)
        self.assertEqual(data['count'], 2)

    @patch('app_db.get_template_preview')
    def test_preview_industry_template_success(self, mock_preview):
        """Test GET /api/tenant/industries/<key>/preview success"""
        mock_preview.return_value = {
            'industry_name': 'Crypto Trading',
            'entity_count': 5,
            'revenue_categories_count': 6
        }

        response = self.app.get('/api/tenant/industries/crypto_trading/preview')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['industry_key'], 'crypto_trading')
        self.assertIn('preview', data)

    @patch('app_db.get_template_preview')
    def test_preview_industry_template_not_found(self, mock_preview):
        """Test GET /api/tenant/industries/<key>/preview not found"""
        mock_preview.return_value = None

        response = self.app.get('/api/tenant/industries/nonexistent/preview')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(data['success'])

    @patch('app_db.apply_industry_template')
    @patch('app_db.clear_tenant_config_cache')
    def test_apply_industry_template_success(self, mock_clear_cache, mock_apply):
        """Test POST /api/tenant/industries/<key>/apply success"""
        mock_apply.return_value = True

        request_data = {
            'company_name': 'Acme Corp'
        }

        response = self.app.post(
            '/api/tenant/industries/crypto_trading/apply',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['industry_key'], 'crypto_trading')
        mock_clear_cache.assert_called_once()

    @patch('app_db.apply_industry_template')
    def test_apply_industry_template_without_company_name(self, mock_apply):
        """Test POST /api/tenant/industries/<key>/apply without company name"""
        mock_apply.return_value = True

        response = self.app.post(
            '/api/tenant/industries/e_commerce/apply',
            data=json.dumps({}),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        # Should be called with company_name=None
        mock_apply.assert_called_with('delta', 'e_commerce', None)

    @patch('app_db.apply_industry_template')
    def test_apply_industry_template_failure(self, mock_apply):
        """Test POST /api/tenant/industries/<key>/apply failure"""
        mock_apply.return_value = False

        response = self.app.post(
            '/api/tenant/industries/crypto_trading/apply',
            data=json.dumps({}),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])


class TestConfigExportImportAPIEndpoints(unittest.TestCase):
    """Test configuration export/import API endpoints"""

    def setUp(self):
        """Set up test Flask app"""
        from app_db import app
        app.config['TESTING'] = True
        self.app = app.test_client()

    @patch('app_db.get_tenant_configuration')
    def test_export_tenant_config_success(self, mock_get_config):
        """Test GET /api/tenant/config/export success"""
        def get_config_side_effect(tenant_id, config_type):
            configs = {
                'entities': {'entities': []},
                'business_context': {'industry': 'crypto_trading'},
                'accounting_categories': {'revenue_categories': []},
                'pattern_matching_rules': {'entity_matching': {}}
            }
            return configs.get(config_type)

        mock_get_config.side_effect = get_config_side_effect

        response = self.app.get('/api/tenant/config/export')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('export_data', data)
        self.assertIn('configurations', data['export_data'])
        self.assertEqual(mock_get_config.call_count, 4)  # Should call for each config type

    @patch('app_db.update_tenant_configuration')
    @patch('app_db.clear_tenant_config_cache')
    def test_import_tenant_config_success(self, mock_clear_cache, mock_update):
        """Test POST /api/tenant/config/import success"""
        mock_update.return_value = True

        import_data = {
            'import_data': {
                'configurations': {
                    'entities': {'entities': []},
                    'business_context': {'industry': 'e_commerce'}
                }
            }
        }

        response = self.app.post(
            '/api/tenant/config/import',
            data=json.dumps(import_data),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['imported_count'], 2)
        mock_clear_cache.assert_called_once()

    def test_import_tenant_config_missing_data(self):
        """Test POST /api/tenant/config/import missing import_data"""
        response = self.app.post(
            '/api/tenant/config/import',
            data=json.dumps({}),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('Missing import_data', data['error'])

    def test_import_tenant_config_no_configurations(self):
        """Test POST /api/tenant/config/import with no configurations"""
        import_data = {
            'import_data': {
                'configurations': {}
            }
        }

        response = self.app.post(
            '/api/tenant/config/import',
            data=json.dumps(import_data),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('No configurations found', data['error'])

    @patch('app_db.update_tenant_configuration')
    @patch('app_db.clear_tenant_config_cache')
    def test_import_tenant_config_partial_success(self, mock_clear_cache, mock_update):
        """Test POST /api/tenant/config/import with partial success"""
        # First call succeeds, second fails
        mock_update.side_effect = [True, False, True]

        import_data = {
            'import_data': {
                'configurations': {
                    'entities': {'entities': []},
                    'business_context': {'industry': 'e_commerce'},
                    'accounting_categories': {'revenue_categories': []}
                }
            }
        }

        response = self.app.post(
            '/api/tenant/config/import',
            data=json.dumps(import_data),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['imported_count'], 2)  # 2 out of 3 succeeded
        self.assertEqual(data['total_configurations'], 3)


class TestAPIErrorHandling(unittest.TestCase):
    """Test API error handling"""

    def setUp(self):
        """Set up test Flask app"""
        from app_db import app
        app.config['TESTING'] = True
        self.app = app.test_client()

    @patch('app_db.get_tenant_configuration')
    def test_api_exception_handling(self, mock_get_config):
        """Test that API handles exceptions gracefully"""
        mock_get_config.side_effect = Exception('Database error')

        response = self.app.get('/api/tenant/config/entities')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 500)
        self.assertFalse(data['success'])
        self.assertIn('error', data)

    def test_api_invalid_json(self):
        """Test API handling of invalid JSON"""
        response = self.app.put(
            '/api/tenant/config/entities',
            data='invalid json',
            content_type='application/json'
        )

        # Should return 400 or 500 depending on Flask version
        self.assertIn(response.status_code, [400, 500])


def run_tests():
    """Run all multi-tenant API tests"""
    print("=" * 70)
    print("Running Multi-Tenant API Integration Tests")
    print("=" * 70)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTenantConfigAPIEndpoints))
    suite.addTests(loader.loadTestsFromTestCase(TestIndustryTemplateAPIEndpoints))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigExportImportAPIEndpoints))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIErrorHandling))

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
