#!/usr/bin/env python3
"""
Unit Tests for Dynamic Prompt Generation
Tests build_entity_classification_prompt() and related functions
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_ui'))

from app_db import build_entity_classification_prompt


class TestBuildEntityClassificationPrompt(unittest.TestCase):
    """Test dynamic entity classification prompt building"""

    @patch('app_db.get_tenant_business_context')
    @patch('app_db.get_tenant_entities')
    @patch('app_db.get_current_tenant_id')
    def test_build_prompt_crypto_industry(self, mock_tenant_id, mock_entities, mock_context):
        """Test prompt building for crypto industry"""
        mock_tenant_id.return_value = 'test_tenant'
        mock_entities.return_value = [
            {
                'name': 'Test Trading LLC',
                'description': 'Main trading operations',
                'entity_type': 'subsidiary'
            },
            {
                'name': 'Test Mining',
                'description': 'Mining operations',
                'entity_type': 'subsidiary'
            }
        ]
        mock_context.return_value = {
            'industry': 'crypto_trading',
            'company_name': 'Test Company'
        }

        context = {
            'description': 'Test transaction',
            'amount': 1000.00,
            'source_file': 'test.csv',
            'date': '2024-01-01'
        }

        result = build_entity_classification_prompt(context)

        # Check that prompt contains expected elements
        self.assertIn('Test Trading LLC', result)
        self.assertIn('Main trading operations', result)
        self.assertIn('crypto trading', result.lower())
        self.assertIn('Test transaction', result)
        self.assertIn('1000', result)

        # Check for crypto-specific context clues
        self.assertIn('Crypto exchange', result)
        self.assertIn('Wallet addresses', result)

    @patch('app_db.get_tenant_business_context')
    @patch('app_db.get_tenant_entities')
    @patch('app_db.get_current_tenant_id')
    def test_build_prompt_ecommerce_industry(self, mock_tenant_id, mock_entities, mock_context):
        """Test prompt building for e-commerce industry"""
        mock_tenant_id.return_value = 'test_tenant'
        mock_entities.return_value = [
            {
                'name': 'Acme Corp',
                'description': 'Main e-commerce business',
                'entity_type': 'main'
            }
        ]
        mock_context.return_value = {
            'industry': 'e_commerce',
            'company_name': 'Acme Corp'
        }

        context = {
            'description': 'Amazon marketplace fee',
            'amount': -50.00,
            'source_file': 'transactions.csv',
            'date': '2024-01-15'
        }

        result = build_entity_classification_prompt(context)

        # Check for e-commerce specific content
        self.assertIn('Acme Corp', result)
        self.assertIn('e commerce', result.lower())
        self.assertIn('Amazon marketplace fee', result)

        # Check for e-commerce context clues
        self.assertIn('Payment processor', result)
        self.assertIn('Marketplace fees', result)
        self.assertIn('Shipping', result)

    @patch('app_db.get_tenant_business_context')
    @patch('app_db.get_tenant_entities')
    @patch('app_db.get_current_tenant_id')
    def test_build_prompt_saas_industry(self, mock_tenant_id, mock_entities, mock_context):
        """Test prompt building for SaaS industry"""
        mock_tenant_id.return_value = 'test_tenant'
        mock_entities.return_value = [
            {
                'name': 'SaaS Company Inc',
                'description': 'Software company',
                'entity_type': 'main'
            }
        ]
        mock_context.return_value = {
            'industry': 'saas',
            'company_name': 'SaaS Company Inc'
        }

        context = {
            'description': 'AWS cloud services',
            'amount': -500.00,
            'source_file': 'expenses.csv',
            'date': '2024-02-01'
        }

        result = build_entity_classification_prompt(context)

        # Check for SaaS specific content
        self.assertIn('saas', result.lower())
        self.assertIn('AWS cloud services', result)

        # Check for SaaS context clues
        self.assertIn('Cloud infrastructure', result)
        self.assertIn('SaaS tools', result)
        self.assertIn('API', result)

    @patch('app_db.get_tenant_business_context')
    @patch('app_db.get_tenant_entities')
    @patch('app_db.get_current_tenant_id')
    def test_build_prompt_professional_services_industry(self, mock_tenant_id, mock_entities, mock_context):
        """Test prompt building for professional services industry"""
        mock_tenant_id.return_value = 'test_tenant'
        mock_entities.return_value = [
            {
                'name': 'Consulting Firm LLC',
                'description': 'Professional consulting',
                'entity_type': 'main'
            }
        ]
        mock_context.return_value = {
            'industry': 'professional_services',
            'company_name': 'Consulting Firm LLC'
        }

        context = {
            'description': 'Client invoice payment',
            'amount': 10000.00,
            'source_file': 'revenue.csv',
            'date': '2024-03-01'
        }

        result = build_entity_classification_prompt(context)

        # Check for professional services specific content
        self.assertIn('professional services', result.lower())
        self.assertIn('Client invoice payment', result)

        # Check for professional services context clues
        self.assertIn('Client billing', result)
        self.assertIn('Professional fees', result)

    @patch('app_db.get_tenant_business_context')
    @patch('app_db.get_tenant_entities')
    @patch('app_db.get_current_tenant_id')
    def test_build_prompt_general_industry(self, mock_tenant_id, mock_entities, mock_context):
        """Test prompt building for general industry (fallback)"""
        mock_tenant_id.return_value = 'test_tenant'
        mock_entities.return_value = [
            {
                'name': 'General Business',
                'description': 'Generic business',
                'entity_type': 'main'
            }
        ]
        mock_context.return_value = {
            'industry': 'unknown',  # Unknown industry
            'company_name': 'General Business'
        }

        context = {
            'description': 'Office supplies',
            'amount': -100.00,
            'source_file': 'expenses.csv',
            'date': '2024-04-01'
        }

        result = build_entity_classification_prompt(context)

        # Check for general/fallback content
        self.assertIn('General Business', result)
        self.assertIn('Office supplies', result)

        # Check for general context clues (fallback)
        self.assertIn('Bank descriptions', result)
        self.assertIn('ACH/WIRE', result)

    @patch('app_db.get_tenant_business_context')
    @patch('app_db.get_tenant_entities')
    @patch('app_db.get_current_tenant_id')
    def test_build_prompt_multiple_entities(self, mock_tenant_id, mock_entities, mock_context):
        """Test prompt with multiple entities"""
        mock_tenant_id.return_value = 'test_tenant'
        mock_entities.return_value = [
            {'name': 'Entity 1', 'description': 'Description 1'},
            {'name': 'Entity 2', 'description': 'Description 2'},
            {'name': 'Entity 3', 'description': 'Description 3'}
        ]
        mock_context.return_value = {
            'industry': 'general',
            'company_name': 'Test Company'
        }

        context = {
            'description': 'Test',
            'amount': 100,
            'source_file': 'test.csv',
            'date': '2024-01-01'
        }

        result = build_entity_classification_prompt(context)

        # All entities should be in the prompt
        self.assertIn('Entity 1', result)
        self.assertIn('Entity 2', result)
        self.assertIn('Entity 3', result)
        self.assertIn('Description 1', result)

    @patch('app_db.get_tenant_business_context')
    @patch('app_db.get_tenant_entities')
    @patch('app_db.get_current_tenant_id')
    def test_build_prompt_with_explicit_tenant_id(self, mock_tenant_id, mock_entities, mock_context):
        """Test prompt building with explicitly provided tenant_id"""
        mock_tenant_id.return_value = 'default_tenant'  # Should not be used
        mock_entities.return_value = [
            {'name': 'Explicit Tenant Entity', 'description': 'Test'}
        ]
        mock_context.return_value = {
            'industry': 'crypto_trading',
            'company_name': 'Explicit Tenant'
        }

        context = {
            'description': 'Test',
            'amount': 100,
            'source_file': 'test.csv',
            'date': '2024-01-01'
        }

        result = build_entity_classification_prompt(context, tenant_id='explicit_tenant')

        # Should use explicitly provided tenant_id
        mock_entities.assert_called_with('explicit_tenant')
        mock_context.assert_called_with('explicit_tenant')
        self.assertIn('Explicit Tenant Entity', result)

    @patch('app_db.get_tenant_business_context')
    @patch('app_db.get_tenant_entities')
    @patch('app_db.get_current_tenant_id')
    def test_build_prompt_empty_entities(self, mock_tenant_id, mock_entities, mock_context):
        """Test prompt building with no entities configured"""
        mock_tenant_id.return_value = 'test_tenant'
        mock_entities.return_value = []  # No entities
        mock_context.return_value = {
            'industry': 'general',
            'company_name': 'Test Company'
        }

        context = {
            'description': 'Test transaction',
            'amount': 100,
            'source_file': 'test.csv',
            'date': '2024-01-01'
        }

        result = build_entity_classification_prompt(context)

        # Should still generate a prompt
        self.assertIsNotNone(result)
        self.assertIn('Test transaction', result)
        # Should contain "No entities configured" message
        self.assertIn('No entities configured', result)

    @patch('app_db.get_tenant_business_context')
    @patch('app_db.get_tenant_entities')
    @patch('app_db.format_entities_for_prompt')
    def test_build_prompt_calls_format_entities(self, mock_format, mock_entities, mock_context):
        """Test that prompt building calls format_entities_for_prompt"""
        mock_entities.return_value = [{'name': 'Entity 1', 'description': 'Desc'}]
        mock_context.return_value = {'industry': 'general', 'company_name': 'Test'}
        mock_format.return_value = '• Entity 1: Desc'

        context = {
            'description': 'Test',
            'amount': 100,
            'source_file': 'test.csv',
            'date': '2024-01-01'
        }

        result = build_entity_classification_prompt(context, 'test_tenant')

        # Should call format_entities_for_prompt
        mock_format.assert_called_once()
        called_with_entities = mock_format.call_args[0][0]
        self.assertEqual(called_with_entities[0]['name'], 'Entity 1')


class TestPromptStructure(unittest.TestCase):
    """Test prompt structure and required elements"""

    @patch('app_db.get_tenant_business_context')
    @patch('app_db.get_tenant_entities')
    @patch('app_db.get_current_tenant_id')
    def test_prompt_contains_transaction_details_section(self, mock_tenant_id, mock_entities, mock_context):
        """Test that prompt contains TRANSACTION DETAILS section"""
        mock_tenant_id.return_value = 'test'
        mock_entities.return_value = [{'name': 'Entity', 'description': 'Desc'}]
        mock_context.return_value = {'industry': 'general', 'company_name': 'Test'}

        context = {
            'description': 'Test desc',
            'amount': 123.45,
            'source_file': 'file.csv',
            'date': '2024-01-01'
        }

        result = build_entity_classification_prompt(context)

        self.assertIn('TRANSACTION DETAILS', result)
        self.assertIn('Description:', result)
        self.assertIn('Amount:', result)
        self.assertIn('Source File:', result)
        self.assertIn('Date:', result)

    @patch('app_db.get_tenant_business_context')
    @patch('app_db.get_tenant_entities')
    @patch('app_db.get_current_tenant_id')
    def test_prompt_contains_entity_classification_rules_section(self, mock_tenant_id, mock_entities, mock_context):
        """Test that prompt contains ENTITY CLASSIFICATION RULES section"""
        mock_tenant_id.return_value = 'test'
        mock_entities.return_value = [{'name': 'Entity', 'description': 'Desc'}]
        mock_context.return_value = {'industry': 'general', 'company_name': 'Test'}

        context = {'description': 'Test', 'amount': 100, 'source_file': 'f.csv', 'date': '2024-01-01'}

        result = build_entity_classification_prompt(context)

        self.assertIn('ENTITY CLASSIFICATION RULES', result)

    @patch('app_db.get_tenant_business_context')
    @patch('app_db.get_tenant_entities')
    @patch('app_db.get_current_tenant_id')
    def test_prompt_contains_context_clues_section(self, mock_tenant_id, mock_entities, mock_context):
        """Test that prompt contains CONTEXT CLUES section"""
        mock_tenant_id.return_value = 'test'
        mock_entities.return_value = [{'name': 'Entity', 'description': 'Desc'}]
        mock_context.return_value = {'industry': 'crypto_trading', 'company_name': 'Test'}

        context = {'description': 'Test', 'amount': 100, 'source_file': 'f.csv', 'date': '2024-01-01'}

        result = build_entity_classification_prompt(context)

        self.assertIn('CONTEXT CLUES', result)

    @patch('app_db.get_tenant_business_context')
    @patch('app_db.get_tenant_entities')
    @patch('app_db.get_current_tenant_id')
    def test_prompt_contains_instructions(self, mock_tenant_id, mock_entities, mock_context):
        """Test that prompt contains classification instructions"""
        mock_tenant_id.return_value = 'test'
        mock_entities.return_value = [{'name': 'Entity', 'description': 'Desc'}]
        mock_context.return_value = {'industry': 'general', 'company_name': 'Test'}

        context = {'description': 'Test', 'amount': 100, 'source_file': 'f.csv', 'date': '2024-01-01'}

        result = build_entity_classification_prompt(context)

        # Should contain instructions for AI
        self.assertIn('suggest', result.lower())
        self.assertIn('entities', result.lower())
        self.assertIn('ranked by confidence', result.lower())


def run_tests():
    """Run all dynamic prompt tests"""
    print("=" * 70)
    print("Running Dynamic Prompt Generation Unit Tests")
    print("=" * 70)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestBuildEntityClassificationPrompt))
    suite.addTests(loader.loadTestsFromTestCase(TestPromptStructure))

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
