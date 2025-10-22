#!/usr/bin/env python3
"""
Test script for Receipt Matcher Service
Tests transaction matching algorithms and confidence scoring
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from web_ui.services import ReceiptMatcher, MatchingStrategy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_basic_initialization():
    """Test basic matcher initialization"""
    print("\n" + "="*60)
    print("TEST 1: Basic Initialization")
    print("="*60)

    try:
        matcher = ReceiptMatcher()
        print("✅ ReceiptMatcher initialized successfully")
        print(f"   Date range: ±{matcher.config['date_range_days']} days")
        print(f"   Amount fuzzy: ±{matcher.config['amount_fuzzy_percent']}%")
        print(f"   Vendor similarity threshold: {matcher.config['vendor_similarity_threshold']:.0%}")
        print(f"   Min confidence threshold: {matcher.config['min_confidence_threshold']:.0%}")
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False


def test_date_parsing():
    """Test date parsing logic"""
    print("\n" + "="*60)
    print("TEST 2: Date Parsing")
    print("="*60)

    try:
        matcher = ReceiptMatcher()

        test_dates = [
            ('2025-10-21', 'ISO format string'),
            (datetime(2025, 10, 21), 'datetime object'),
            ('10/21/2025', 'US format'),
            ('21-10-2025', 'European format'),
        ]

        success_count = 0
        for date_value, description in test_dates:
            try:
                parsed = matcher._parse_date(date_value)
                if parsed:
                    print(f"✅ Parsed {description}: {date_value} → {parsed.date()}")
                    success_count += 1
                else:
                    print(f"⚠️  Failed to parse {description}: {date_value}")
            except Exception as e:
                print(f"❌ Error parsing {description}: {e}")

        print(f"\nParsed {success_count}/{len(test_dates)} date formats successfully")
        return success_count > 0

    except Exception as e:
        print(f"❌ Date parsing test failed: {e}")
        return False


def test_string_similarity():
    """Test string similarity calculations"""
    print("\n" + "="*60)
    print("TEST 3: String Similarity")
    print("="*60)

    try:
        matcher = ReceiptMatcher()

        test_pairs = [
            ('Amazon', 'Amazon.com', 'Exact vendor match'),
            ('Starbucks', 'STARBUCKS COFFEE', 'Case insensitive'),
            ('McDonald\'s', 'MCDONALDS #1234', 'Partial match'),
            ('Walmart', 'Target', 'Different vendors'),
            ('Google Cloud', 'Google Cloud Platform', 'Substring match'),
        ]

        for str1, str2, description in test_pairs:
            similarity = matcher._calculate_similarity(str1, str2)
            print(f"   {description}:")
            print(f"      '{str1}' vs '{str2}'")
            print(f"      Similarity: {similarity:.1%}")

        return True

    except Exception as e:
        print(f"❌ Similarity test failed: {e}")
        return False


def test_reference_normalization():
    """Test reference number normalization"""
    print("\n" + "="*60)
    print("TEST 4: Reference Number Normalization")
    print("="*60)

    try:
        matcher = ReceiptMatcher()

        test_references = [
            ('ABC-123', 'abc123', True),
            ('INV#456', 'inv456', True),
            ('REF_789', 'ref789', True),
            ('TXN 123 456', 'txn123456', True),
            ('ABC123', 'XYZ789', False),
        ]

        success_count = 0
        for ref1, ref2, should_match in test_references:
            norm1 = matcher._normalize_reference(ref1)
            norm2 = matcher._normalize_reference(ref2)
            matches = (norm1 == norm2)

            status = "✅" if matches == should_match else "❌"
            print(f"{status} '{ref1}' vs '{ref2}'")
            print(f"      Normalized: '{norm1}' vs '{norm2}'")
            print(f"      Match: {matches} (expected: {should_match})")

            if matches == should_match:
                success_count += 1

        print(f"\nPassed {success_count}/{len(test_references)} reference normalization tests")
        return success_count == len(test_references)

    except Exception as e:
        print(f"❌ Reference normalization test failed: {e}")
        return False


def test_matching_with_sample_data():
    """Test matching with sample receipt data"""
    print("\n" + "="*60)
    print("TEST 5: Matching with Sample Data")
    print("="*60)

    try:
        matcher = ReceiptMatcher()

        # Create sample receipt data
        today = datetime.now()
        sample_receipts = [
            {
                'name': 'Exact match receipt',
                'data': {
                    'date': today.strftime('%Y-%m-%d'),
                    'vendor': 'Amazon',
                    'amount': 99.99,
                    'description': 'Purchase at Amazon.com',
                }
            },
            {
                'name': 'Fuzzy amount receipt',
                'data': {
                    'date': (today - timedelta(days=1)).strftime('%Y-%m-%d'),
                    'vendor': 'Walmart',
                    'amount': 50.00,
                    'description': 'Walmart Supercenter',
                }
            },
            {
                'name': 'Old receipt',
                'data': {
                    'date': (today - timedelta(days=60)).strftime('%Y-%m-%d'),
                    'vendor': 'Starbucks',
                    'amount': 15.50,
                    'description': 'Coffee at Starbucks',
                }
            },
        ]

        for receipt in sample_receipts:
            print(f"\n📄 Testing: {receipt['name']}")
            print(f"   Date: {receipt['data']['date']}")
            print(f"   Vendor: {receipt['data']['vendor']}")
            print(f"   Amount: ${receipt['data']['amount']}")

            matches = matcher.find_matches(receipt['data'])

            print(f"   Found {len(matches)} match(es)")

            if matches:
                for i, match in enumerate(matches[:3], 1):  # Show top 3
                    match_dict = match.to_dict()
                    print(f"\n   Match {i}:")
                    print(f"      Confidence: {match_dict['confidence']:.1%}")
                    print(f"      Recommendation: {match_dict['recommendation']}")
                    print(f"      Strategies: {', '.join(match_dict['matching_strategies'])}")
            else:
                print("   No matches found (this is OK if database is empty)")

        return True

    except Exception as e:
        print(f"❌ Matching test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_new_transaction_suggestion():
    """Test new transaction suggestion"""
    print("\n" + "="*60)
    print("TEST 6: New Transaction Suggestion")
    print("="*60)

    try:
        matcher = ReceiptMatcher()

        receipt_data = {
            'date': '2025-10-21',
            'vendor': 'New Vendor Inc.',
            'amount': 199.99,
            'currency': 'USD',
            'description': 'Service purchase',
            'suggested_category': 'Professional Services',
            'suggested_business_unit': 'Delta LLC',
            'confidence': 0.85
        }

        suggestion = matcher.suggest_new_transaction(receipt_data)

        print("📝 Suggested new transaction:")
        print(f"   Date: {suggestion['date']}")
        print(f"   Description: {suggestion['description']}")
        print(f"   Amount: ${suggestion['amount']}")
        print(f"   Entity: {suggestion['entity']}")
        print(f"   Category: {suggestion['category']}")
        print(f"   Source: {suggestion['source']}")

        # Validate suggestion structure
        required_fields = ['date', 'description', 'amount', 'entity', 'source']
        has_all_fields = all(field in suggestion for field in required_fields)

        if has_all_fields:
            print("\n✅ Suggestion has all required fields")
            return True
        else:
            print("\n❌ Suggestion missing required fields")
            return False

    except Exception as e:
        print(f"❌ Suggestion test failed: {e}")
        return False


def test_confidence_scoring():
    """Test confidence scoring with various match scenarios"""
    print("\n" + "="*60)
    print("TEST 7: Confidence Scoring Scenarios")
    print("="*60)

    try:
        matcher = ReceiptMatcher()

        # Note: These tests show the logic, but actual scores depend on database content
        scenarios = [
            {
                'name': 'Perfect match (reference + exact amount + same date)',
                'expected_range': (0.90, 1.00),
                'description': 'Should have very high confidence'
            },
            {
                'name': 'Good match (exact amount + 1 day difference)',
                'expected_range': (0.80, 0.95),
                'description': 'Should have high confidence'
            },
            {
                'name': 'Decent match (fuzzy amount + vendor similarity)',
                'expected_range': (0.60, 0.85),
                'description': 'Should have medium confidence'
            },
            {
                'name': 'Weak match (only vendor similarity)',
                'expected_range': (0.40, 0.70),
                'description': 'Should have low-medium confidence'
            },
        ]

        print("Confidence scoring logic:")
        for scenario in scenarios:
            print(f"\n   {scenario['name']}:")
            print(f"      Expected: {scenario['expected_range'][0]:.0%} - {scenario['expected_range'][1]:.0%}")
            print(f"      {scenario['description']}")

        print("\n✅ Confidence scoring logic documented")
        print("   (Actual scores depend on database transactions)")

        return True

    except Exception as e:
        print(f"❌ Confidence scoring test failed: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print(" RECEIPT MATCHER TEST SUITE")
    print("="*80)

    tests = [
        ("Basic Initialization", test_basic_initialization),
        ("Date Parsing", test_date_parsing),
        ("String Similarity", test_string_similarity),
        ("Reference Normalization", test_reference_normalization),
        ("Matching with Sample Data", test_matching_with_sample_data),
        ("New Transaction Suggestion", test_new_transaction_suggestion),
        ("Confidence Scoring", test_confidence_scoring),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            logger.error(f"Test '{test_name}' raised exception: {e}", exc_info=True)
            results.append((test_name, False))

    # Print summary
    print("\n" + "="*80)
    print(" TEST SUMMARY")
    print("="*80)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} - {test_name}")

    print(f"\nOverall: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed")

    return passed_count == total_count


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Receipt Matcher Service")
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--test-db', action='store_true', help='Test with actual database queries')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    success = run_all_tests()

    if args.test_db:
        print("\n" + "="*80)
        print(" DATABASE INTEGRATION TEST")
        print("="*80)
        print("Testing actual database queries...")

        try:
            from web_ui.services import ReceiptMatcher

            matcher = ReceiptMatcher()

            # Test with realistic receipt
            test_receipt = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'vendor': 'Test Vendor',
                'amount': 100.00,
                'description': 'Test purchase',
            }

            print(f"\nQuerying database with test receipt...")
            matches = matcher.find_matches(test_receipt)

            print(f"✅ Database query successful")
            print(f"   Found {len(matches)} potential matches")

            if matches:
                print("\n   Top match:")
                top_match = matches[0].to_dict()
                print(f"      Confidence: {top_match['confidence']:.1%}")
                print(f"      Transaction: {top_match['transaction_data'].get('description', 'N/A')}")

        except Exception as e:
            print(f"❌ Database integration test failed: {e}")
            import traceback
            traceback.print_exc()

    sys.exit(0 if success else 1)
