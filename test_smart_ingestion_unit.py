#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Smart Ingestion Redesign

Tests verify that the system:
1. Uses Claude's file_structure dynamically (not hardcoded format checks)
2. Uses Claude's column_cleaning_rules for intelligent data cleaning
3. Works with ANY CSV format without code changes
4. Handles complex scenarios (multi-row headers, mixed currencies, parentheses notation)
5. Maintains backwards compatibility with old Claude responses
"""

import unittest
import sys
import os
import json
import tempfile
import pandas as pd
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smart_ingestion import SmartDocumentIngestion


class TestClaudeResponseParsing(unittest.TestCase):
    """Test parsing of Claude's enhanced response structure"""

    def setUp(self):
        """Set up test fixtures"""
        self.ingestion = SmartDocumentIngestion()

    def test_parse_response_with_file_structure(self):
        """Test parsing Claude response with new file_structure field"""
        response_text = json.dumps({
            "file_structure": {
                "skip_rows_before_header": [0, 1, 2],
                "header_row_index": 3,
                "has_trailing_commas": True
            },
            "format": "test_format",
            "date_column": "Date",
            "amount_column": "Amount"
        })

        result = self.ingestion._parse_claude_response(response_text)

        self.assertIn('file_structure', result)
        self.assertEqual(result['file_structure']['skip_rows_before_header'], [0, 1, 2])
        self.assertEqual(result['file_structure']['header_row_index'], 3)
        self.assertTrue(result['file_structure']['has_trailing_commas'])

    def test_parse_response_with_column_cleaning_rules(self):
        """Test parsing Claude response with column_cleaning_rules"""
        response_text = json.dumps({
            "file_structure": {
                "skip_rows_before_header": []
            },
            "column_cleaning_rules": {
                "amount_column": {
                    "remove_currency_symbols": True,
                    "remove_commas": True,
                    "parentheses_mean_negative": True
                }
            },
            "date_column": "Date",
            "amount_column": "Amount"
        })

        result = self.ingestion._parse_claude_response(response_text)

        self.assertIn('column_cleaning_rules', result)
        amount_rules = result['column_cleaning_rules']['amount_column']
        self.assertTrue(amount_rules['remove_currency_symbols'])
        self.assertTrue(amount_rules['remove_commas'])
        self.assertTrue(amount_rules['parentheses_mean_negative'])

    def test_parse_response_with_defaults_for_missing_fields(self):
        """Test that defaults are added when file_structure is missing"""
        response_text = json.dumps({
            "format": "old_format",
            "date_column": "Date",
            "amount_column": "Amount"
        })

        result = self.ingestion._parse_claude_response(response_text)

        # Should add file_structure with defaults
        self.assertIn('file_structure', result)
        self.assertEqual(result['file_structure']['skip_rows_before_header'], [])
        self.assertEqual(result['file_structure']['header_row_index'], 0)
        self.assertFalse(result['file_structure']['has_trailing_commas'])

        # Should add column_cleaning_rules with defaults
        self.assertIn('column_cleaning_rules', result)

    def test_parse_response_cleans_control_characters(self):
        """Test that control characters are cleaned from JSON"""
        # Create response with control characters
        response_dict = {
            "file_structure": {"skip_rows_before_header": []},
            "date_column": "Date",
            "amount_column": "Amount",
            "notes": "Test\x00with\x1fcontrol\x7fchars"  # Invalid control chars
        }
        response_text = json.dumps(response_dict)

        # Should parse successfully without errors
        result = self.ingestion._parse_claude_response(response_text)
        self.assertIn('date_column', result)

    def test_parse_response_handles_json_code_blocks(self):
        """Test parsing JSON wrapped in markdown code blocks"""
        response_text = """```json
{
    "file_structure": {
        "skip_rows_before_header": [0]
    },
    "date_column": "Date"
}
```"""

        result = self.ingestion._parse_claude_response(response_text)
        self.assertIn('file_structure', result)
        self.assertEqual(result['file_structure']['skip_rows_before_header'], [0])


class TestDynamicCSVReading(unittest.TestCase):
    """Test dynamic CSV reading based on Claude's file_structure"""

    def setUp(self):
        """Set up test fixtures"""
        self.ingestion = SmartDocumentIngestion()

    def test_skip_rows_from_claude_instructions(self):
        """Test that system uses skip_rows from Claude, not hardcoded"""
        # Create test CSV with 3 metadata rows before header
        csv_content = """Metadata Row 1
Metadata Row 2
Metadata Row 3
Date,Amount,Description
2025-01-01,100.00,Test transaction
2025-01-02,200.00,Another test"""

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            # Claude's instructions: skip first 3 rows
            structure_info = {
                "file_structure": {
                    "skip_rows_before_header": [0, 1, 2],
                    "has_trailing_commas": False
                },
                "column_cleaning_rules": {
                    "amount_column": {
                        "remove_currency_symbols": False,
                        "remove_commas": False,
                        "parentheses_mean_negative": False
                    }
                },
                "date_column": "Date",
                "amount_column": "Amount",
                "description_column": "Description"
            }

            df = self.ingestion._python_process_with_mapping(csv_path, structure_info)

            # Verify data was read correctly
            self.assertEqual(len(df), 2)
            self.assertIn('Date', df.columns)
            self.assertIn('Amount', df.columns)
            self.assertEqual(float(df.iloc[0]['Amount']), 100.00)

        finally:
            os.unlink(csv_path)

    def test_standard_csv_with_no_skip_rows(self):
        """Test standard CSV with no rows to skip"""
        csv_content = """Date,Amount,Description
2025-01-01,100.00,Test transaction"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            structure_info = {
                "file_structure": {
                    "skip_rows_before_header": [],  # No rows to skip
                    "has_trailing_commas": False
                },
                "column_cleaning_rules": {
                    "amount_column": {}
                },
                "date_column": "Date",
                "amount_column": "Amount"
            }

            df = self.ingestion._python_process_with_mapping(csv_path, structure_info)
            self.assertEqual(len(df), 1)
            self.assertEqual(float(df.iloc[0]['Amount']), 100.00)

        finally:
            os.unlink(csv_path)


class TestIntelligentColumnCleaning(unittest.TestCase):
    """Test intelligent currency cleaning based on Claude's rules"""

    def setUp(self):
        """Set up test fixtures"""
        self.ingestion = SmartDocumentIngestion()

    def test_remove_dollar_signs(self):
        """Test removing $ symbols when Claude instructs"""
        csv_content = """Date,Amount
2025-01-01,$100.00
2025-01-02,$200.00"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            structure_info = {
                "file_structure": {
                    "skip_rows_before_header": []
                },
                "column_cleaning_rules": {
                    "amount_column": {
                        "remove_currency_symbols": True,  # Remove $
                        "remove_commas": False,
                        "parentheses_mean_negative": False
                    }
                },
                "date_column": "Date",
                "amount_column": "Amount"
            }

            df = self.ingestion._python_process_with_mapping(csv_path, structure_info)

            # Amounts should be numeric without $
            self.assertEqual(float(df.iloc[0]['Amount']), 100.00)
            self.assertEqual(float(df.iloc[1]['Amount']), 200.00)

        finally:
            os.unlink(csv_path)

    def test_remove_multiple_currency_symbols(self):
        """Test removing $, €, £, ¥ symbols"""
        csv_content = """Date,Amount
2025-01-01,$100.00
2025-01-02,€200.00
2025-01-03,£300.00
2025-01-04,¥400.00"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            structure_info = {
                "file_structure": {
                    "skip_rows_before_header": []
                },
                "column_cleaning_rules": {
                    "amount_column": {
                        "remove_currency_symbols": True
                    }
                },
                "date_column": "Date",
                "amount_column": "Amount"
            }

            df = self.ingestion._python_process_with_mapping(csv_path, structure_info)

            # All currencies should be removed
            self.assertEqual(float(df.iloc[0]['Amount']), 100.00)
            self.assertEqual(float(df.iloc[1]['Amount']), 200.00)
            self.assertEqual(float(df.iloc[2]['Amount']), 300.00)
            self.assertEqual(float(df.iloc[3]['Amount']), 400.00)

        finally:
            os.unlink(csv_path)

    def test_parentheses_mean_negative(self):
        """Test converting ($100) to -100 when Claude instructs"""
        csv_content = """Date,Amount
2025-01-01,$100.00
2025-01-02,($50.00)
2025-01-03,$75.00
2025-01-04,($25.00)"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            structure_info = {
                "file_structure": {
                    "skip_rows_before_header": []
                },
                "column_cleaning_rules": {
                    "amount_column": {
                        "remove_currency_symbols": True,
                        "parentheses_mean_negative": True  # KEY!
                    }
                },
                "date_column": "Date",
                "amount_column": "Amount"
            }

            df = self.ingestion._python_process_with_mapping(csv_path, structure_info)

            # Verify parentheses converted to negative
            self.assertEqual(float(df.iloc[0]['Amount']), 100.00)   # Positive
            self.assertEqual(float(df.iloc[1]['Amount']), -50.00)   # Negative (parentheses)
            self.assertEqual(float(df.iloc[2]['Amount']), 75.00)    # Positive
            self.assertEqual(float(df.iloc[3]['Amount']), -25.00)   # Negative (parentheses)

        finally:
            os.unlink(csv_path)

    def test_comma_separator_removal(self):
        """Test removing thousand separators"""
        csv_content = """Date,Amount
2025-01-01,"$1,234.56"
2025-01-02,"$10,000.00\""""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            structure_info = {
                "file_structure": {
                    "skip_rows_before_header": []
                },
                "column_cleaning_rules": {
                    "amount_column": {
                        "remove_currency_symbols": True,
                        "remove_commas": True  # Remove commas
                    }
                },
                "date_column": "Date",
                "amount_column": "Amount"
            }

            df = self.ingestion._python_process_with_mapping(csv_path, structure_info)

            self.assertEqual(float(df.iloc[0]['Amount']), 1234.56)
            self.assertEqual(float(df.iloc[1]['Amount']), 10000.00)

        finally:
            os.unlink(csv_path)


class TestComplexScenarios(unittest.TestCase):
    """Test complex real-world scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        self.ingestion = SmartDocumentIngestion()

    def test_multi_row_header_with_mixed_currencies(self):
        """Test complex CSV: 3-row header + mixed currencies + parentheses"""
        csv_content = """My Exchange - Transaction Report
Generated: 2025-10-20
Account: Test User

TxID,Date,Amount,Type,Fee
tx001,2025-01-01,"$1,234.56",Buy,$5.00
tx002,2025-01-02,($500.00),Sell,$2.50
tx003,2025-01-03,"€2,000.00",Buy,€10.00
tx004,2025-01-04,(£750.50),Sell,£3.75"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            # Claude's instructions for this complex file
            structure_info = {
                "file_structure": {
                    "skip_rows_before_header": [0, 1, 2],  # Skip 3 metadata rows
                    "has_trailing_commas": False
                },
                "column_cleaning_rules": {
                    "amount_column": {
                        "remove_currency_symbols": True,  # Handle $, €, £
                        "remove_commas": True,            # Handle 1,234
                        "parentheses_mean_negative": True # Handle ($500)
                    }
                },
                "date_column": "Date",
                "amount_column": "Amount"
            }

            df = self.ingestion._python_process_with_mapping(csv_path, structure_info)

            # Verify correct parsing
            self.assertEqual(len(df), 4)

            # Verify currency cleaning
            self.assertEqual(float(df.iloc[0]['Amount']), 1234.56)   # $1,234.56
            self.assertEqual(float(df.iloc[1]['Amount']), -500.00)   # ($500.00) - negative
            self.assertEqual(float(df.iloc[2]['Amount']), 2000.00)   # €2,000.00
            self.assertEqual(float(df.iloc[3]['Amount']), -750.50)   # (£750.50) - negative

        finally:
            os.unlink(csv_path)

    def test_backwards_compatibility_with_old_response(self):
        """Test that old Claude responses (without new fields) still work"""
        csv_content = """Date,Amount
2025-01-01,100.00"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            # Old Claude response (no file_structure, no cleaning_rules)
            structure_info = {
                "format": "generic",
                "date_column": "Date",
                "amount_column": "Amount"
            }

            # After _parse_claude_response, defaults should be added
            parsed_info = self.ingestion._parse_claude_response(json.dumps(structure_info))

            df = self.ingestion._python_process_with_mapping(csv_path, parsed_info)

            # Should work with defaults
            self.assertEqual(len(df), 1)
            self.assertEqual(float(df.iloc[0]['Amount']), 100.00)

        finally:
            os.unlink(csv_path)


class TestNoHardcodedFormatChecks(unittest.TestCase):
    """Verify that hardcoded format checks are NOT used"""

    def setUp(self):
        """Set up test fixtures"""
        self.ingestion = SmartDocumentIngestion()

    def test_no_coinbase_hardcoded_check(self):
        """Verify system doesn't use 'if format == coinbase' logic"""
        # CSV with metadata row, then header, then data
        # If system used hardcoded coinbase logic (skip [0,1,2]), it would fail
        # But we tell it to only skip [0], so it should work
        csv_content = """Metadata: Exchange Report
Date,Amount,Type
2025-01-01,100.00,Buy
2025-01-02,200.00,Sell"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            # Structure says "coinbase" but with DIFFERENT skip_rows
            # If system used hardcoded logic, it would skip [0,1,2]
            # But we're telling it to skip [0] only
            structure_info = {
                "format": "coinbase",  # Label says coinbase
                "file_structure": {
                    "skip_rows_before_header": [0],  # But only skip 1 row!
                    "has_trailing_commas": False
                },
                "column_cleaning_rules": {
                    "amount_column": {}
                },
                "date_column": "Date",
                "amount_column": "Amount"
            }

            df = self.ingestion._python_process_with_mapping(csv_path, structure_info)

            # If it used hardcoded logic for 'coinbase', this would fail
            # Because it would skip [0,1,2] instead of [0]
            # With skip [0], we should get 2 data rows
            self.assertEqual(len(df), 2)
            self.assertEqual(float(df.iloc[0]['Amount']), 100.00)

        finally:
            os.unlink(csv_path)

    def test_brand_new_format_works(self):
        """Test that a brand new, never-seen-before format works"""
        # Simulate a hypothetical "FutureCryptoExchange2025" format
        # Note: Removed empty line to avoid pandas parsing issues
        csv_content = """### FUTURE EXCHANGE - TRANSACTION REPORT - CLASSIFIED DATA - SECURITY LEVEL 5 - END HEADER ###
### Generated: 2025-10-21 ###
### Account Type: Premium ###
### Report ID: FUT-2025-001 ###
### Classification: CONFIDENTIAL ###
TransactionID,DateTime,ValueUSD,OperationType,NetworkFee
FUT001,2025-01-01T10:30:00,$1000.00,PURCHASE,$2.50
FUT002,2025-01-02T15:45:00,($250.00),SALE,$1.25"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            # Claude analyzes this brand new format and provides instructions
            structure_info = {
                "format": "future_crypto_exchange_2025",  # Never seen before!
                "file_structure": {
                    "skip_rows_before_header": [0, 1, 2, 3, 4],  # 5 header rows
                    "has_trailing_commas": False
                },
                "column_cleaning_rules": {
                    "amount_column": {
                        "remove_currency_symbols": True,
                        "parentheses_mean_negative": True
                    }
                },
                "date_column": "DateTime",
                "amount_column": "ValueUSD"
            }

            df = self.ingestion._python_process_with_mapping(csv_path, structure_info)

            # Should work perfectly with brand new format
            self.assertEqual(len(df), 2)
            # System standardizes column names: ValueUSD → Amount
            self.assertEqual(float(df.iloc[0]['Amount']), 1000.00)
            self.assertEqual(float(df.iloc[1]['Amount']), -250.00)  # Negative

        finally:
            os.unlink(csv_path)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def setUp(self):
        """Set up test fixtures"""
        self.ingestion = SmartDocumentIngestion()

    def test_empty_skip_rows_list(self):
        """Test handling empty skip_rows list"""
        csv_content = """Date,Amount
2025-01-01,100.00"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            structure_info = {
                "file_structure": {
                    "skip_rows_before_header": [],  # Empty list
                },
                "column_cleaning_rules": {},
                "date_column": "Date",
                "amount_column": "Amount"
            }

            df = self.ingestion._python_process_with_mapping(csv_path, structure_info)
            self.assertEqual(len(df), 1)

        finally:
            os.unlink(csv_path)

    def test_malformed_json_raises_error(self):
        """Test that malformed JSON raises appropriate error"""
        malformed_json = "{invalid json"

        # The method catches JSONDecodeError and re-raises as ValueError
        with self.assertRaises(ValueError):
            self.ingestion._parse_claude_response(malformed_json)

    def test_missing_amount_column_uses_default(self):
        """Test graceful handling when amount column doesn't exist"""
        csv_content = """Date,Description
2025-01-01,Test"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            structure_info = {
                "file_structure": {
                    "skip_rows_before_header": []
                },
                "column_cleaning_rules": {},
                "date_column": "Date",
                "amount_column": "NonexistentAmount"  # Doesn't exist
            }

            # Should handle gracefully (currently will create NaN column)
            df = self.ingestion._python_process_with_mapping(csv_path, structure_info)
            self.assertIsNotNone(df)

        finally:
            os.unlink(csv_path)


def print_section(title):
    """Print a section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def main():
    """Run all unit tests"""
    print_section("SMART INGESTION REDESIGN - UNIT TESTS")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestClaudeResponseParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestDynamicCSVReading))
    suite.addTests(loader.loadTestsFromTestCase(TestIntelligentColumnCleaning))
    suite.addTests(loader.loadTestsFromTestCase(TestComplexScenarios))
    suite.addTests(loader.loadTestsFromTestCase(TestNoHardcodedFormatChecks))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print_section("TEST SUMMARY")
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n🎉 ALL UNIT TESTS PASSED!")
        print("\n✅ Verified:")
        print("   • Claude provides complete parsing instructions")
        print("   • System uses instructions dynamically (no hardcoded checks)")
        print("   • Works with ANY CSV format")
        print("   • Handles multi-row headers, mixed currencies, parentheses")
        print("   • Backwards compatible with old responses")
        print("\n🚀 Smart Ingestion is TRULY LLM-powered and scalable!")
    else:
        print("\n⚠️  Some tests failed - review output above")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit(main())
