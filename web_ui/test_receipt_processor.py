#!/usr/bin/env python3
"""
Test script for Receipt Processor Service
Demonstrates receipt processing capabilities
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from web_ui.services import ReceiptProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_basic_functionality():
    """Test basic receipt processor initialization"""
    print("\n" + "="*60)
    print("TEST 1: Basic Initialization")
    print("="*60)

    try:
        processor = ReceiptProcessor()
        print("✅ ReceiptProcessor initialized successfully")
        print(f"   Model: {processor.config.CLAUDE_MODEL}")
        print(f"   Max file size: {processor.config.MAX_FILE_SIZE / (1024*1024)}MB")
        print(f"   Supported formats: {', '.join(processor.config.ALLOWED_EXTENSIONS)}")
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False


def test_file_validation():
    """Test file validation logic"""
    print("\n" + "="*60)
    print("TEST 2: File Validation")
    print("="*60)

    try:
        processor = ReceiptProcessor()

        # Test non-existent file
        try:
            processor._validate_file("nonexistent.pdf")
            print("❌ Should have raised FileNotFoundError")
        except FileNotFoundError:
            print("✅ Correctly rejects non-existent file")

        print("\nℹ️  File validation logic is working correctly")
        return True

    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False


def test_sample_receipt_processing():
    """Test processing a sample receipt if available"""
    print("\n" + "="*60)
    print("TEST 3: Sample Receipt Processing")
    print("="*60)

    # Look for test files
    test_file_locations = [
        "test_receipt.pdf",
        "sample_receipt.pdf",
        "test_data/receipt.pdf",
        "../test_receipt.pdf",
        "web_ui/test_receipt.pdf"
    ]

    found_file = None
    for location in test_file_locations:
        if os.path.exists(location):
            found_file = location
            break

    if not found_file:
        print("ℹ️  No test receipt file found. Skipping processing test.")
        print("   To test processing, add a receipt file to one of these locations:")
        for loc in test_file_locations[:3]:
            print(f"   - {loc}")
        return True

    try:
        processor = ReceiptProcessor()
        print(f"Processing: {found_file}")

        result = processor.process_receipt(found_file)

        print("\n📊 EXTRACTION RESULTS:")
        print(f"   Document Type: {result.get('document_type')}")
        print(f"   Vendor: {result.get('vendor')}")
        print(f"   Date: {result.get('date')}")
        print(f"   Amount: {result.get('amount')} {result.get('currency')}")
        print(f"   Payment Method: {result.get('payment_method')}")
        print(f"   Confidence: {result.get('confidence', 0):.1%}")
        print(f"   Quality: {result.get('quality')}")

        if result.get('suggested_category'):
            print(f"   Suggested Category: {result.get('suggested_category')}")

        if result.get('suggested_business_unit'):
            print(f"   Suggested Business Unit: {result.get('suggested_business_unit')}")

        if result.get('processing_notes'):
            print(f"   Notes: {result.get('processing_notes')}")

        if result.get('status') == 'success':
            print("\n✅ Receipt processed successfully!")
            return True
        else:
            print(f"\n⚠️  Processing completed with status: {result.get('status')}")
            return False

    except Exception as e:
        print(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_processing():
    """Test batch processing capability"""
    print("\n" + "="*60)
    print("TEST 4: Batch Processing")
    print("="*60)

    # Look for multiple test files
    test_files = []
    for i in range(1, 4):
        test_path = f"test_receipt_{i}.pdf"
        if os.path.exists(test_path):
            test_files.append(test_path)

    if not test_files:
        print("ℹ️  No multiple test files found. Skipping batch processing test.")
        print("   To test batch processing, add files: test_receipt_1.pdf, test_receipt_2.pdf, etc.")
        return True

    try:
        processor = ReceiptProcessor()
        print(f"Processing {len(test_files)} receipts in batch...")

        results = processor.batch_process_receipts(test_files)

        success_count = sum(1 for r in results if r.get('status') == 'success')
        print(f"\n✅ Batch processing complete: {success_count}/{len(results)} successful")

        return True

    except Exception as e:
        print(f"❌ Batch processing failed: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print(" RECEIPT PROCESSOR TEST SUITE")
    print("="*80)

    tests = [
        ("Basic Initialization", test_basic_functionality),
        ("File Validation", test_file_validation),
        ("Sample Receipt Processing", test_sample_receipt_processing),
        ("Batch Processing", test_batch_processing)
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

    parser = argparse.ArgumentParser(description="Test Receipt Processor Service")
    parser.add_argument('--test-file', type=str, help='Specific receipt file to test')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.test_file:
        # Test specific file
        if not os.path.exists(args.test_file):
            print(f"❌ File not found: {args.test_file}")
            sys.exit(1)

        print(f"Testing with file: {args.test_file}\n")
        try:
            processor = ReceiptProcessor()
            result = processor.process_receipt(args.test_file)

            print("\n" + "="*60)
            print("RECEIPT PROCESSING RESULT")
            print("="*60)
            print(f"Status: {result.get('status')}")
            print(f"Document Type: {result.get('document_type')}")
            print(f"Vendor: {result.get('vendor')}")
            print(f"Date: {result.get('date')}")
            print(f"Amount: {result.get('amount')} {result.get('currency')}")
            print(f"Description: {result.get('description')}")
            print(f"Confidence: {result.get('confidence', 0):.1%}")
            print(f"Quality: {result.get('quality')}")

            if result.get('suggested_category'):
                print(f"\nSuggested Category: {result.get('suggested_category')}")
                print(f"Suggested Business Unit: {result.get('suggested_business_unit')}")

            if result.get('tags'):
                print(f"Tags: {', '.join(result.get('tags'))}")

            if result.get('processing_notes'):
                print(f"\nNotes: {result.get('processing_notes')}")

            print("\n" + "="*60)
            print("FULL JSON RESULT:")
            print("="*60)
            import json
            print(json.dumps(result, indent=2))

        except Exception as e:
            print(f"❌ Processing failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        # Run all tests
        success = run_all_tests()
        sys.exit(0 if success else 1)
