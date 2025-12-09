#!/usr/bin/env python3
"""
Unit tests for AI Transaction Tools
Tests tool definitions, date helpers, and execution handlers.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_tools import (
    TRANSACTION_TOOLS,
    get_date_range,
    format_period_name,
    AIToolExecutor,
    get_tool_executor
)


class TestToolDefinitions(unittest.TestCase):
    """Test that tool definitions are valid for Claude API"""

    def test_tools_list_not_empty(self):
        """Tools list should contain tools"""
        self.assertGreater(len(TRANSACTION_TOOLS), 0)

    def test_all_tools_have_required_fields(self):
        """Each tool should have name, description, and input_schema"""
        for tool in TRANSACTION_TOOLS:
            self.assertIn('name', tool, f"Tool missing 'name' field")
            self.assertIn('description', tool, f"Tool missing 'description' field")
            self.assertIn('input_schema', tool, f"Tool missing 'input_schema' field")

    def test_input_schemas_are_valid(self):
        """Input schemas should be valid JSON Schema format"""
        for tool in TRANSACTION_TOOLS:
            schema = tool['input_schema']
            self.assertEqual(schema['type'], 'object', f"Tool {tool['name']} schema type should be 'object'")
            self.assertIn('properties', schema, f"Tool {tool['name']} schema missing 'properties'")

    def test_expected_tools_exist(self):
        """All expected tools should be defined"""
        expected_tools = [
            'get_financial_summary',
            'search_transactions',
            'get_category_breakdown',
            'get_entity_summary',
            'get_recent_transactions',
            'get_top_expenses',
            'get_top_revenue'
        ]
        tool_names = [t['name'] for t in TRANSACTION_TOOLS]
        for expected in expected_tools:
            self.assertIn(expected, tool_names, f"Expected tool '{expected}' not found")


class TestDateHelpers(unittest.TestCase):
    """Test date range calculation helpers"""

    def test_today_returns_same_date(self):
        """'today' should return today's date for both start and end"""
        start, end = get_date_range('today')
        today = str(datetime.now().date())
        self.assertEqual(start, today)
        self.assertEqual(end, today)

    def test_yesterday_returns_previous_day(self):
        """'yesterday' should return yesterday's date"""
        start, end = get_date_range('yesterday')
        yesterday = str((datetime.now() - timedelta(days=1)).date())
        self.assertEqual(start, yesterday)
        self.assertEqual(end, yesterday)

    def test_this_month_starts_on_first(self):
        """'this_month' should start on the first of the month"""
        start, end = get_date_range('this_month')
        today = datetime.now().date()
        expected_start = str(today.replace(day=1))
        self.assertEqual(start, expected_start)
        self.assertEqual(end, str(today))

    def test_last_30_days(self):
        """'last_30_days' should return 30-day range"""
        start, end = get_date_range('last_30_days')
        today = datetime.now().date()
        expected_start = str(today - timedelta(days=30))
        self.assertEqual(start, expected_start)
        self.assertEqual(end, str(today))

    def test_all_time_returns_none(self):
        """'all_time' should return None for both dates (no filter)"""
        start, end = get_date_range('all_time')
        self.assertIsNone(start)
        self.assertIsNone(end)

    def test_unknown_period_defaults_to_30_days(self):
        """Unknown period should default to last 30 days"""
        start, end = get_date_range('unknown_period')
        today = datetime.now().date()
        expected_start = str(today - timedelta(days=30))
        self.assertEqual(start, expected_start)


class TestFormatPeriodName(unittest.TestCase):
    """Test period name formatting"""

    def test_known_periods(self):
        """Known periods should return human-readable names"""
        self.assertEqual(format_period_name('today'), 'Today')
        self.assertEqual(format_period_name('this_month'), 'This Month')
        self.assertEqual(format_period_name('last_30_days'), 'Last 30 Days')
        self.assertEqual(format_period_name('all_time'), 'All Time')

    def test_unknown_period_formats_nicely(self):
        """Unknown period should be title-cased with underscores replaced"""
        result = format_period_name('some_custom_period')
        self.assertEqual(result, 'Some Custom Period')


class TestAIToolExecutor(unittest.TestCase):
    """Test AIToolExecutor class"""

    def setUp(self):
        """Set up mock database manager"""
        self.mock_db = Mock()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value.__enter__ = Mock(return_value=self.mock_conn)
        self.mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)
        self.mock_conn.cursor.return_value = self.mock_cursor

    def test_executor_requires_tenant_id(self):
        """Executor should raise error if tenant_id is missing"""
        with self.assertRaises(ValueError):
            AIToolExecutor(self.mock_db, None)

        with self.assertRaises(ValueError):
            AIToolExecutor(self.mock_db, '')

    def test_executor_initializes_with_valid_tenant(self):
        """Executor should initialize with valid tenant_id"""
        executor = AIToolExecutor(self.mock_db, 'test_tenant')
        self.assertEqual(executor.tenant_id, 'test_tenant')
        self.assertEqual(executor.db_manager, self.mock_db)

    def test_unknown_tool_returns_error(self):
        """Unknown tool name should return error message"""
        executor = AIToolExecutor(self.mock_db, 'test_tenant')
        result = executor.execute('unknown_tool', {})
        self.assertIn('Unknown tool', result)

    def test_format_currency(self):
        """Currency formatting should work correctly"""
        executor = AIToolExecutor(self.mock_db, 'test_tenant')

        self.assertEqual(executor._format_currency(1000), '$1,000.00')
        self.assertEqual(executor._format_currency(1234.56), '$1,234.56')
        self.assertEqual(executor._format_currency(0), '$0.00')
        self.assertEqual(executor._format_currency(None), '$0.00')
        self.assertEqual(executor._format_currency(1000, 'EUR'), '1,000.00 EUR')


class TestFinancialSummaryTool(unittest.TestCase):
    """Test get_financial_summary tool"""

    def setUp(self):
        """Set up mock database manager"""
        self.mock_db = Mock()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value.__enter__ = Mock(return_value=self.mock_conn)
        self.mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)
        self.mock_conn.cursor.return_value = self.mock_cursor

    @patch.dict('sys.modules', {'psycopg2': MagicMock(), 'psycopg2.extras': MagicMock()})
    def test_financial_summary_returns_data(self):
        """Financial summary should return formatted data"""
        # Mock database response
        self.mock_cursor.fetchone.return_value = {
            'transaction_count': 100,
            'total_revenue': 50000.00,
            'total_expenses': 30000.00,
            'revenue_count': 40,
            'expense_count': 60,
            'entity_count': 3
        }

        executor = AIToolExecutor(self.mock_db, 'test_tenant')
        result = executor.execute('get_financial_summary', {'period': 'this_month'})

        self.assertIn('Financial Summary', result)
        self.assertIn('$50,000.00', result)
        self.assertIn('$30,000.00', result)
        self.assertIn('$20,000.00', result)  # Net income

    @patch.dict('sys.modules', {'psycopg2': MagicMock(), 'psycopg2.extras': MagicMock()})
    def test_financial_summary_no_data(self):
        """Financial summary should handle no data case"""
        self.mock_cursor.fetchone.return_value = {'transaction_count': 0}

        executor = AIToolExecutor(self.mock_db, 'test_tenant')
        result = executor.execute('get_financial_summary', {'period': 'this_month'})

        self.assertIn('No transactions found', result)


class TestSearchTransactionsTool(unittest.TestCase):
    """Test search_transactions tool"""

    def setUp(self):
        """Set up mock database manager"""
        self.mock_db = Mock()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_db.get_connection.return_value.__enter__ = Mock(return_value=self.mock_conn)
        self.mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)
        self.mock_conn.cursor.return_value = self.mock_cursor

    @patch.dict('sys.modules', {'psycopg2': MagicMock(), 'psycopg2.extras': MagicMock()})
    def test_search_returns_transactions(self):
        """Search should return formatted transaction list"""
        self.mock_cursor.fetchall.return_value = [
            {
                'id': 1,
                'date': '2024-01-15',
                'description': 'Test transaction',
                'amount': 100.00,
                'classified_entity': 'Test Entity',
                'accounting_category': 'Revenue',
                'subcategory': None,
                'currency': 'USD'
            }
        ]

        executor = AIToolExecutor(self.mock_db, 'test_tenant')
        result = executor.execute('search_transactions', {'keyword': 'test'})

        self.assertIn('Found 1 transaction', result)
        self.assertIn('Test transaction', result)

    @patch.dict('sys.modules', {'psycopg2': MagicMock(), 'psycopg2.extras': MagicMock()})
    def test_search_no_results(self):
        """Search should handle no results"""
        self.mock_cursor.fetchall.return_value = []

        executor = AIToolExecutor(self.mock_db, 'test_tenant')
        result = executor.execute('search_transactions', {'keyword': 'nonexistent'})

        self.assertIn('No transactions found', result)

    @patch.dict('sys.modules', {'psycopg2': MagicMock(), 'psycopg2.extras': MagicMock()})
    def test_search_respects_limit(self):
        """Search should respect the limit parameter"""
        self.mock_cursor.fetchall.return_value = []
        executor = AIToolExecutor(self.mock_db, 'test_tenant')

        # Test default limit
        executor.execute('search_transactions', {})
        call_args = self.mock_cursor.execute.call_args
        self.assertIn(10, call_args[0][1])  # Default limit

        # Test custom limit (should be capped at 50)
        executor.execute('search_transactions', {'limit': 100})
        call_args = self.mock_cursor.execute.call_args
        self.assertIn(50, call_args[0][1])  # Capped limit


class TestFactoryFunction(unittest.TestCase):
    """Test get_tool_executor factory function"""

    def test_factory_creates_executor(self):
        """Factory should create AIToolExecutor instance"""
        mock_db = Mock()
        executor = get_tool_executor(mock_db, 'test_tenant')
        self.assertIsInstance(executor, AIToolExecutor)
        self.assertEqual(executor.tenant_id, 'test_tenant')


if __name__ == '__main__':
    unittest.main()
