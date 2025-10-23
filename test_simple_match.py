#!/usr/bin/env python3
"""
Test script for simple_match_engine
Tests the keyword-based matching functionality
"""

import sys
sys.path.insert(0, '/home/user/DeltaCFOAgent/web_ui')

from simple_match_engine import find_similar_simple, calculate_field_similarity, extract_keywords

def test_field_similarity():
    """Test field similarity calculation"""
    print("=" * 60)
    print("TEST 1: Field Similarity")
    print("=" * 60)

    test_cases = [
        ("Chase Bank", "Chase Bank", 1.0),  # Exact match
        ("Chase Bank", "Chase", 0.85),      # Substring match (approx)
        ("Anthropic", "Google", 0.0),       # No match
        ("ANTHROPIC API USAGE", "ANTHROPIC API", 0.85),  # Substring
    ]

    for field1, field2, expected_min in test_cases:
        similarity = calculate_field_similarity(field1, field2)
        status = "✅" if similarity >= expected_min else "❌"
        print(f"{status} '{field1}' vs '{field2}': {similarity:.2f} (expected >= {expected_min})")

    print()


def test_keyword_extraction():
    """Test keyword extraction"""
    print("=" * 60)
    print("TEST 2: Keyword Extraction")
    print("=" * 60)

    test_cases = [
        "PAYMENT TO ANTHROPIC API USAGE",
        "Chase Bank Transfer",
        "THE GOOGLE CLOUD SERVICES FOR MARCH"
    ]

    for text in test_cases:
        keywords = extract_keywords(text)
        print(f"Text: '{text}'")
        print(f"  Keywords: {keywords}")
        print()


def test_simple_match():
    """Test simple match with sample transactions"""
    print("=" * 60)
    print("TEST 3: Simple Transaction Matching")
    print("=" * 60)

    # Target transaction
    target = {
        'transaction_id': 'tx_target',
        'origin': 'Chase Bank',
        'destination': 'Anthropic',
        'description': 'API Usage February 2025',
        'amount': 150.00,
        'classified_entity': 'Delta LLC',
        'accounting_category': 'Technology',
        'subcategory': 'Software Licenses'
    }

    # Candidate transactions
    candidates = [
        {
            # HIGH MATCH: All 3 fields similar
            'transaction_id': 'tx_1',
            'origin': 'Chase Bank',
            'destination': 'Anthropic',
            'description': 'API Usage January 2025',
            'amount': 140.00,
            'classified_entity': 'Delta LLC',
            'accounting_category': 'Technology',
            'subcategory': 'Software Licenses'
        },
        {
            # MEDIUM MATCH: 2 fields match (Origin + Destination)
            'transaction_id': 'tx_2',
            'origin': 'Chase Bank',
            'destination': 'Anthropic',
            'description': 'Different service',
            'amount': 200.00,
            'classified_entity': None,
            'accounting_category': None,
            'subcategory': None
        },
        {
            # LOW MATCH: 1 field matches (Origin)
            'transaction_id': 'tx_3',
            'origin': 'Chase Bank',
            'destination': 'Google Cloud',
            'description': 'Cloud Services',
            'amount': 300.00,
            'classified_entity': None,
            'accounting_category': None,
            'subcategory': None
        },
        {
            # NO MATCH: Different wallet/crypto transaction
            'transaction_id': 'tx_4',
            'origin': 'Wallet 0x1234abcd',
            'destination': 'Exchange',
            'description': 'USDT Transfer',
            'amount': 10000.00,
            'classified_entity': None,
            'accounting_category': None,
            'subcategory': None
        },
        {
            # PENALIZED MATCH: Similar fields but 3x amount difference
            'transaction_id': 'tx_5',
            'origin': 'Chase Bank',
            'destination': 'Anthropic',
            'description': 'API Usage March 2025',
            'amount': 500.00,  # More than 2x different
            'classified_entity': None,
            'accounting_category': None,
            'subcategory': None
        }
    ]

    print(f"Target Transaction:")
    print(f"  ID: {target['transaction_id']}")
    print(f"  Origin: {target['origin']}")
    print(f"  Destination: {target['destination']}")
    print(f"  Description: {target['description']}")
    print(f"  Amount: ${target['amount']}")
    print()

    # Find matches
    matches = find_similar_simple(target, candidates, min_confidence=0.1)

    print(f"Found {len(matches)} matches:\n")

    for i, match in enumerate(matches, 1):
        details = match['match_details']
        print(f"{i}. Transaction {match['transaction_id']}")
        print(f"   Confidence: {match['confidence']:.2f}")
        print(f"   Matched Fields: {', '.join(details['matched_fields'])}")
        print(f"   Origin Similarity: {details['origin_similarity']:.2f}")
        print(f"   Dest Similarity: {details['destination_similarity']:.2f}")
        print(f"   Desc Similarity: {details['description_similarity']:.2f}")
        if details['amount_penalty'] > 0:
            print(f"   ⚠️  Amount Penalty: -{details['amount_penalty']}")
        print()

    print()


def test_confidence_levels():
    """Test confidence level categorization"""
    print("=" * 60)
    print("TEST 4: Confidence Levels")
    print("=" * 60)

    target = {
        'transaction_id': 'tx_target',
        'origin': 'Vendor A',
        'destination': 'Company B',
        'description': 'Service X',
        'amount': 100.00
    }

    test_cases = [
        {
            'name': '3 Fields Match - High Confidence',
            'candidate': {
                'transaction_id': 'tx_test_1',
                'origin': 'Vendor A',
                'destination': 'Company B',
                'description': 'Service X',
                'amount': 100.00,
                'classified_entity': 'Test Entity'
            },
            'expected_min': 0.8
        },
        {
            'name': '2 Fields Match - Medium Confidence',
            'candidate': {
                'transaction_id': 'tx_test_2',
                'origin': 'Vendor A',
                'destination': 'Company B',
                'description': 'Different Service',
                'amount': 100.00,
                'classified_entity': 'Test Entity'
            },
            'expected_min': 0.5,
            'expected_max': 0.79
        },
        {
            'name': '1 Field Match - Low Confidence',
            'candidate': {
                'transaction_id': 'tx_test_3',
                'origin': 'Vendor A',
                'destination': 'Different Company',
                'description': 'Different Service',
                'amount': 100.00,
                'classified_entity': 'Test Entity'
            },
            'expected_min': 0.3,
            'expected_max': 0.49
        }
    ]

    for test in test_cases:
        matches = find_similar_simple(target, [test['candidate']], min_confidence=0.1)

        if matches:
            confidence = matches[0]['confidence']
            expected_min = test.get('expected_min', 0)
            expected_max = test.get('expected_max', 1.0)

            if expected_min <= confidence <= expected_max:
                status = "✅"
            else:
                status = "❌"

            print(f"{status} {test['name']}")
            print(f"   Confidence: {confidence:.2f} (expected {expected_min:.2f}-{expected_max:.2f})")
            print(f"   Matched: {', '.join(matches[0]['match_details']['matched_fields'])}")
        else:
            print(f"❌ {test['name']}")
            print(f"   No matches found!")
        print()


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("SIMPLE MATCH ENGINE - TEST SUITE")
    print("=" * 60 + "\n")

    try:
        test_field_similarity()
        test_keyword_extraction()
        test_simple_match()
        test_confidence_levels()

        print("=" * 60)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 60)
        print("\nNote: Some tests use approximate thresholds.")
        print("Visual inspection of results is recommended.")
        print()

    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR:")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
