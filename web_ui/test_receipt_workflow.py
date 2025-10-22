#!/usr/bin/env python3
"""
End-to-End Test for Receipt Upload Workflow
Tests the complete receipt upload, processing, matching, and linking workflow
"""

import os
import sys
import time
import requests
from pathlib import Path

# Test configuration
BASE_URL = "http://127.0.0.1:5001"
TEST_RECEIPTS_DIR = os.path.join(os.path.dirname(__file__), 'uploads', 'test_receipts')

def test_health_check():
    """Test 1: Health check"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)

    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            data = response.json()
            print(f"   Status: {data.get('status')}")
            print(f"   Version: {data.get('version')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running")
        print("   Please start the server with: cd web_ui && python app_db.py")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


def test_receipts_page():
    """Test 2: Receipts page loads"""
    print("\n" + "="*60)
    print("TEST 2: Receipts Page")
    print("="*60)

    try:
        response = requests.get(f"{BASE_URL}/receipts", timeout=5)
        if response.status_code == 200:
            print("✅ Receipts page loads successfully")
            print(f"   Page size: {len(response.text)} bytes")

            # Check for key elements
            if 'receipt-upload.js' in response.text:
                print("   ✅ JavaScript file loaded")
            if 'uploadArea' in response.text:
                print("   ✅ Upload area present")
            return True
        else:
            print(f"❌ Receipts page failed to load: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error loading receipts page: {e}")
        return False


def test_receipt_upload_without_processing():
    """Test 3: Upload receipt without auto-processing"""
    print("\n" + "="*60)
    print("TEST 3: Receipt Upload (No Processing)")
    print("="*60)

    try:
        receipt_path = os.path.join(TEST_RECEIPTS_DIR, 'test_receipt.pdf')

        if not os.path.exists(receipt_path):
            print(f"❌ Test receipt not found: {receipt_path}")
            return False

        print(f"   Uploading: {os.path.basename(receipt_path)}")

        with open(receipt_path, 'rb') as f:
            files = {'file': ('test_receipt.pdf', f, 'application/pdf')}
            data = {'auto_process': 'false'}

            response = requests.post(
                f"{BASE_URL}/api/receipts/upload",
                files=files,
                data=data,
                timeout=30
            )

        if response.status_code == 200:
            result = response.json()
            print("✅ Receipt uploaded successfully")
            print(f"   Receipt ID: {result['receipt_id']}")
            print(f"   Filename: {result['filename']}")
            print(f"   File size: {result['file_size']} bytes")
            print(f"   Status: {result['status']}")
            return result['receipt_id']
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_receipt_upload_with_processing():
    """Test 4: Upload receipt with auto-processing (MAIN TEST)"""
    print("\n" + "="*60)
    print("TEST 4: Receipt Upload with Processing (MAIN TEST)")
    print("="*60)

    try:
        receipt_path = os.path.join(TEST_RECEIPTS_DIR, 'test_receipt.pdf')

        if not os.path.exists(receipt_path):
            print(f"❌ Test receipt not found: {receipt_path}")
            return None

        print(f"   Uploading: {os.path.basename(receipt_path)}")
        print("   Auto-processing: ENABLED")
        print("   This will test Claude Vision extraction...")

        with open(receipt_path, 'rb') as f:
            files = {'file': ('test_receipt.pdf', f, 'application/pdf')}
            data = {'auto_process': 'true'}

            response = requests.post(
                f"{BASE_URL}/api/receipts/upload",
                files=files,
                data=data,
                timeout=60  # Longer timeout for Claude API
            )

        if response.status_code == 200:
            result = response.json()
            print("✅ Receipt uploaded and processed successfully")
            print(f"\n   Receipt ID: {result['receipt_id']}")
            print(f"   Filename: {result['filename']}")
            print(f"   Status: {result['status']}")
            print(f"   Processing Status: {result.get('processing_status')}")

            # Check extracted data
            if result.get('extracted_data'):
                extracted = result['extracted_data']
                print("\n   📋 Extracted Data:")
                print(f"      Status: {extracted.get('status')}")

                if extracted.get('status') == 'success':
                    print(f"      Vendor: {extracted.get('vendor')}")
                    print(f"      Date: {extracted.get('date')}")
                    print(f"      Amount: ${extracted.get('amount')}")
                    print(f"      Currency: {extracted.get('currency')}")
                    print(f"      Document Type: {extracted.get('document_type')}")

                    if extracted.get('suggested_category'):
                        print(f"      Suggested Category: {extracted.get('suggested_category')}")
                    if extracted.get('suggested_business_unit'):
                        print(f"      Suggested Business Unit: {extracted.get('suggested_business_unit')}")
                    if extracted.get('confidence'):
                        print(f"      Confidence: {extracted.get('confidence'):.1%}")
                else:
                    print(f"      ⚠️  Processing status: {extracted.get('status')}")
                    if extracted.get('error'):
                        print(f"      Error: {extracted.get('error')}")

            # Check matches
            if result.get('matches'):
                matches = result['matches']
                print(f"\n   🎯 Found {len(matches)} transaction match(es):")

                for i, match in enumerate(matches[:3], 1):  # Show top 3
                    print(f"\n      Match {i}:")
                    print(f"         Transaction ID: {match['transaction_id']}")
                    print(f"         Confidence: {match['confidence']:.1%}")
                    print(f"         Recommendation: {match['recommendation']}")
                    print(f"         Strategies: {', '.join(match['matching_strategies'])}")

                    trans_data = match.get('transaction_data', {})
                    if trans_data:
                        print(f"         Description: {trans_data.get('description', 'N/A')}")
                        print(f"         Amount: ${abs(trans_data.get('amount', 0)):.2f}")
                        print(f"         Date: {trans_data.get('date', 'N/A')}")
            else:
                print("\n   ℹ️  No transaction matches found (database might be empty)")

            return result

        else:
            print(f"❌ Upload/processing failed: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return None

    except Exception as e:
        print(f"❌ Upload/processing error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_list_receipts():
    """Test 5: List all receipts"""
    print("\n" + "="*60)
    print("TEST 5: List Receipts")
    print("="*60)

    try:
        response = requests.get(f"{BASE_URL}/api/receipts", timeout=5)

        if response.status_code == 200:
            result = response.json()
            receipts = result.get('receipts', [])
            print(f"✅ Retrieved {len(receipts)} receipt(s)")

            for i, receipt in enumerate(receipts[:5], 1):  # Show first 5
                print(f"\n   Receipt {i}:")
                print(f"      ID: {receipt['receipt_id']}")
                print(f"      Filename: {receipt['original_filename']}")
                print(f"      Status: {receipt['status']}")
                print(f"      Uploaded: {receipt['uploaded_at']}")

            return True
        else:
            print(f"❌ Failed to list receipts: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error listing receipts: {e}")
        return False


def test_mining_payout_receipt():
    """Test 6: Upload mining payout receipt"""
    print("\n" + "="*60)
    print("TEST 6: Mining Payout Receipt")
    print("="*60)

    try:
        receipt_path = os.path.join(TEST_RECEIPTS_DIR, 'test_mining_payout.pdf')

        if not os.path.exists(receipt_path):
            print(f"❌ Mining payout receipt not found: {receipt_path}")
            return None

        print(f"   Uploading: {os.path.basename(receipt_path)}")
        print("   Testing mining-specific data extraction...")

        with open(receipt_path, 'rb') as f:
            files = {'file': ('test_mining_payout.pdf', f, 'application/pdf')}
            data = {'auto_process': 'true'}

            response = requests.post(
                f"{BASE_URL}/api/receipts/upload",
                files=files,
                data=data,
                timeout=60
            )

        if response.status_code == 200:
            result = response.json()
            print("✅ Mining payout receipt processed")

            if result.get('extracted_data'):
                extracted = result['extracted_data']
                print(f"\n   Status: {extracted.get('status')}")

                if extracted.get('status') == 'success':
                    print(f"   Document Type: {extracted.get('document_type')}")

                    # Check for mining-specific fields
                    mining_data = extracted.get('mining_data', {})
                    if mining_data:
                        print("\n   ⛏️  Mining Data:")
                        print(f"      Pool: {mining_data.get('pool')}")
                        print(f"      Coin: {mining_data.get('coin')}")
                        print(f"      Amount: {mining_data.get('amount')}")
                        print(f"      Wallet: {mining_data.get('wallet_address', '')[:20]}...")

            return result
        else:
            print(f"❌ Mining receipt processing failed: {response.status_code}")
            return None

    except Exception as e:
        print(f"❌ Mining receipt error: {e}")
        return None


def run_all_tests():
    """Run all end-to-end tests"""
    print("\n" + "="*80)
    print(" RECEIPT UPLOAD WORKFLOW - END-TO-END TESTS")
    print("="*80)

    results = []

    # Test 1: Health check
    results.append(("Health Check", test_health_check()))

    if not results[0][1]:
        print("\n❌ Server is not running. Please start it first.")
        print("   Command: cd web_ui && python app_db.py")
        return False

    # Test 2: Receipts page
    results.append(("Receipts Page", test_receipts_page()))

    # Test 3: Upload without processing
    receipt_id = test_receipt_upload_without_processing()
    results.append(("Upload (No Processing)", receipt_id is not None))

    # Test 4: Upload with processing (MAIN TEST)
    result = test_receipt_upload_with_processing()
    results.append(("Upload with Processing", result is not None))

    # Test 5: List receipts
    results.append(("List Receipts", test_list_receipts()))

    # Test 6: Mining payout
    mining_result = test_mining_payout_receipt()
    results.append(("Mining Payout Receipt", mining_result is not None))

    # Print summary
    print("\n" + "="*80)
    print(" TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} - {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        print("\n📝 Next Steps:")
        print("   1. Open browser to http://127.0.0.1:5001/receipts")
        print("   2. Try drag-and-drop upload")
        print("   3. Verify modal displays correctly")
        print("   4. Test receipt linking workflow")
    else:
        print("⚠️  Some tests failed")

        # Check for common issues
        if not results[0][1]:
            print("\n💡 Tip: Make sure the server is running:")
            print("   cd web_ui && python app_db.py")

    return passed == total


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Receipt Upload Workflow")
    parser.add_argument('--url', default="http://127.0.0.1:5001", help='Base URL of the server')
    parser.add_argument('--quick', action='store_true', help='Run only basic tests')

    args = parser.parse_args()
    BASE_URL = args.url

    success = run_all_tests()

    sys.exit(0 if success else 1)
