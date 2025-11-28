#!/usr/bin/env python3
"""
Unit Tests for P&L Trend API Endpoints
Tests /api/reports/pl-trend and /api/reports/pl-trend/ai-summary
"""

import sys
import os
import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_ui'))


class TestPLTrendAPIEndpoints(unittest.TestCase):
    """Test P&L Trend API endpoints"""

    def setUp(self):
        """Set up test Flask app"""
        from app_db import app
        app.config['TESTING'] = True
        self.app = app.test_client()

    @patch('reporting_api.get_current_tenant_id')
    @patch('reporting_api.db_manager')
    def test_get_pl_trend_success(self, mock_db, mock_tenant):
        """Test GET /api/reports/pl-trend success"""
        mock_tenant.return_value = 'test_tenant'

        # Mock monthly data response
        mock_db.execute_query.side_effect = [
            # First call: monthly P&L data
            [
                {
                    'year': 2024,
                    'month_number': 11,
                    'revenue': 100000,
                    'cogs': 30000,
                    'sga': 40000,
                    'transaction_count': 50
                },
                {
                    'year': 2024,
                    'month_number': 12,
                    'revenue': 120000,
                    'cogs': 35000,
                    'sga': 45000,
                    'transaction_count': 60
                }
            ],
            # Second call: COGS breakdown
            [
                {'category': 'Materials', 'total': 30000, 'count': 10},
                {'category': 'Inventory', 'total': 5000, 'count': 5}
            ],
            # Third call: SG&A breakdown
            [
                {'category': 'Salaries', 'total': 50000, 'count': 20},
                {'category': 'Utilities', 'total': 10000, 'count': 15}
            ]
        ]

        response = self.app.get('/api/reports/pl-trend?months_back=12')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('monthly_pl', data['data'])
        self.assertIn('totals', data['data'])
        self.assertIn('breakdowns', data['data'])

        # Verify monthly data
        monthly_pl = data['data']['monthly_pl']
        self.assertEqual(len(monthly_pl), 2)
        self.assertEqual(monthly_pl[0]['month'], 'Nov 2024')
        self.assertEqual(monthly_pl[0]['revenue'], 100000)
        self.assertEqual(monthly_pl[0]['cogs'], 30000)
        self.assertEqual(monthly_pl[0]['sga'], 40000)
        self.assertEqual(monthly_pl[0]['net_income'], 30000)  # 100000 - 30000 - 40000

    @patch('reporting_api.get_current_tenant_id')
    @patch('reporting_api.db_manager')
    def test_get_pl_trend_empty_data(self, mock_db, mock_tenant):
        """Test GET /api/reports/pl-trend with no data"""
        mock_tenant.return_value = 'test_tenant'
        mock_db.execute_query.return_value = []

        response = self.app.get('/api/reports/pl-trend')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['data']['monthly_pl']), 0)

    @patch('reporting_api.get_current_tenant_id')
    def test_get_pl_trend_no_tenant(self, mock_tenant):
        """Test GET /api/reports/pl-trend without tenant context"""
        mock_tenant.side_effect = ValueError("Tenant context required")

        response = self.app.get('/api/reports/pl-trend')

        # Should return 500 error when tenant is missing
        self.assertEqual(response.status_code, 500)

    @patch('reporting_api.get_current_tenant_id')
    @patch('reporting_api.db_manager')
    def test_get_pl_trend_with_filters(self, mock_db, mock_tenant):
        """Test GET /api/reports/pl-trend with date filters"""
        mock_tenant.return_value = 'test_tenant'
        mock_db.execute_query.return_value = []

        # Test with custom date range
        response = self.app.get(
            '/api/reports/pl-trend?start_date=2024-01-01&end_date=2024-12-31'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])

    @patch('reporting_api.get_current_tenant_id')
    @patch('reporting_api.db_manager')
    def test_get_pl_trend_gross_margin_calculation(self, mock_db, mock_tenant):
        """Test gross margin percentage calculation"""
        mock_tenant.return_value = 'test_tenant'

        mock_db.execute_query.side_effect = [
            [{
                'year': 2024,
                'month_number': 1,
                'revenue': 100000,
                'cogs': 40000,  # 60% gross margin
                'sga': 30000,
                'transaction_count': 10
            }],
            [],  # COGS breakdown
            []   # SG&A breakdown
        ]

        response = self.app.get('/api/reports/pl-trend')
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        monthly_pl = data['data']['monthly_pl']
        self.assertEqual(len(monthly_pl), 1)

        # Gross margin should be (100000 - 40000) / 100000 * 100 = 60%
        self.assertEqual(monthly_pl[0]['gross_margin_percent'], 60.0)


class TestPLTrendAISummaryEndpoint(unittest.TestCase):
    """Test P&L Trend AI Summary endpoint"""

    def setUp(self):
        """Set up test Flask app"""
        from app_db import app
        app.config['TESTING'] = True
        self.app = app.test_client()

    @patch('reporting_api.get_current_tenant_id')
    @patch('reporting_api.db_manager')
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': ''})
    def test_ai_summary_fallback_no_api_key(self, mock_db, mock_tenant):
        """Test AI summary fallback when no API key"""
        mock_tenant.return_value = 'test_tenant'
        mock_db.execute_query.return_value = {'company_name': 'Test Co', 'industry': 'Tech'}

        payload = {
            'month': 'Nov 2024',
            'revenue': 100000,
            'cogs': 30000,
            'sga': 40000,
            'net_income': 30000,
            'gross_margin_percent': 70.0,
            'trend_data': []
        }

        response = self.app.post(
            '/api/reports/pl-trend/ai-summary',
            data=json.dumps(payload),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('summary', data)
        self.assertEqual(data['generated_by'], 'fallback')

    @patch('reporting_api.get_current_tenant_id')
    @patch('reporting_api.db_manager')
    @patch('anthropic.Anthropic')
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test_key'})
    def test_ai_summary_with_claude(self, mock_anthropic, mock_db, mock_tenant):
        """Test AI summary with Claude API"""
        mock_tenant.return_value = 'test_tenant'
        mock_db.execute_query.return_value = {'company_name': 'Test Co', 'industry': 'Tech'}

        # Mock Claude response
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='Test AI Summary for November 2024.')]
        mock_client.messages.create.return_value = mock_response

        payload = {
            'month': 'Nov 2024',
            'revenue': 100000,
            'cogs': 30000,
            'sga': 40000,
            'net_income': 30000,
            'gross_margin_percent': 70.0,
            'trend_data': []
        }

        response = self.app.post(
            '/api/reports/pl-trend/ai-summary',
            data=json.dumps(payload),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('summary', data)
        self.assertEqual(data['generated_by'], 'claude')

    @patch('reporting_api.get_current_tenant_id')
    def test_ai_summary_missing_body(self, mock_tenant):
        """Test AI summary with missing JSON body"""
        mock_tenant.return_value = 'test_tenant'

        response = self.app.post(
            '/api/reports/pl-trend/ai-summary',
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(data['success'])
        self.assertIn('error', data)

    @patch('reporting_api.get_current_tenant_id')
    @patch('reporting_api.db_manager')
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': ''})
    def test_ai_summary_with_trend_data(self, mock_db, mock_tenant):
        """Test AI summary includes trend context"""
        mock_tenant.return_value = 'test_tenant'
        mock_db.execute_query.return_value = {'company_name': 'Test Co', 'industry': 'Tech'}

        payload = {
            'month': 'Nov 2024',
            'revenue': 100000,
            'cogs': 30000,
            'sga': 40000,
            'net_income': 30000,
            'gross_margin_percent': 70.0,
            'trend_data': [
                {'month': 'Sep 2024', 'revenue': 80000, 'net_income': 20000},
                {'month': 'Oct 2024', 'revenue': 90000, 'net_income': 25000},
                {'month': 'Nov 2024', 'revenue': 100000, 'net_income': 30000}
            ]
        }

        response = self.app.post(
            '/api/reports/pl-trend/ai-summary',
            data=json.dumps(payload),
            content_type='application/json'
        )
        data = json.loads(response.data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])


class TestPLTrendPageRoute(unittest.TestCase):
    """Test P&L Trend page route"""

    def setUp(self):
        """Set up test Flask app"""
        from app_db import app
        app.config['TESTING'] = True
        self.app = app.test_client()

    def test_pl_trend_page_loads(self):
        """Test /reports/pl-trend page renders"""
        response = self.app.get('/reports/pl-trend')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'P&L Trend', response.data)


if __name__ == '__main__':
    unittest.main()
