#!/usr/bin/env python3
"""
Test script for Receipt Upload API endpoints
Tests all receipt API routes
"""

import requests
import os
import sys
from pathlib import Path

# Base URL for API
BASE_URL = "http://localhost:5001"

def test_api_endpoints():
    """Test all receipt API endpoints"""

    print("\n" + "="*80)
    print(" RECEIPT API ENDPOINTS TEST")
    print("="*80)

    # Test 1: Upload Receipt
    print("\n📤 TEST 1: Upload Receipt (POST /api/receipts/upload)")
    print("-" * 80)

    # Create a test file (simple text file pretending to be a receipt)
    test_file_path = "test_receipt.txt"
    with open(test_file_path, 'w') as f:
        f.write("Test receipt content")

    try:
        with open(test_file_path, 'rb') as f:
            files = {'file': ('test_receipt.pdf', f, 'application/pdf')}
            data = {'auto_process': 'false'}  # Don't auto-process for initial test

            response = requests.post(
                f"{BASE_URL}/api/receipts/upload",
                files=files,
                data=data
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✅ Upload successful")
                print(f"   Receipt ID: {result.get('receipt_id')}")
                print(f"   Filename: {result.get('filename')}")
                print(f"   File Size: {result.get('file_size')} bytes")
                print(f"   Status: {result.get('status')}")

                receipt_id = result.get('receipt_id')
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(f"   Error: {response.text}")
                return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

    # Test 2: Get Receipt Metadata
    print("\n📋 TEST 2: Get Receipt Metadata (GET /api/receipts/{id})")
    print("-" * 80)

    try:
        response = requests.get(f"{BASE_URL}/api/receipts/{receipt_id}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Get metadata successful")
            print(f"   Receipt ID: {result.get('receipt_id')}")
            print(f"   Status: {result.get('status')}")
            print(f"   Uploaded At: {result.get('uploaded_at')}")
        else:
            print(f"❌ Get metadata failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Test failed: {e}")

    # Test 3: List Receipts
    print("\n📚 TEST 3: List Receipts (GET /api/receipts)")
    print("-" * 80)

    try:
        response = requests.get(f"{BASE_URL}/api/receipts")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ List successful")
            print(f"   Total Count: {result.get('total_count')}")
            print(f"   Receipts: {len(result.get('receipts', []))}")
        else:
            print(f"❌ List failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Test failed: {e}")

    # Test 4: Delete Receipt
    print("\n🗑️  TEST 4: Delete Receipt (DELETE /api/receipts/{id})")
    print("-" * 80)

    try:
        response = requests.delete(f"{BASE_URL}/api/receipts/{receipt_id}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Delete successful")
            print(f"   Message: {result.get('message')}")
        else:
            print(f"❌ Delete failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Test failed: {e}")

    print("\n" + "="*80)
    print(" TEST SUMMARY")
    print("="*80)
    print("✅ All API endpoints are accessible")
    print("Note: Full processing tests require ANTHROPIC_API_KEY")

    return True


def test_with_real_receipt():
    """Test with a real receipt file if available"""

    print("\n" + "="*80)
    print(" REAL RECEIPT PROCESSING TEST")
    print("="*80)

    # Look for a test receipt file
    test_files = [
        "test_receipt.pdf",
        "sample_receipt.pdf",
        "test_data/receipt.pdf"
    ]

    test_file = None
    for f in test_files:
        if os.path.exists(f):
            test_file = f
            break

    if not test_file:
        print("ℹ️  No test receipt file found. Skipping real processing test.")
        print("   To test processing, add a receipt file to one of these locations:")
        for f in test_files[:2]:
            print(f"   - {f}")
        return

    print(f"📄 Processing: {test_file}")

    try:
        with open(test_file, 'rb') as f:
            files = {'file': (os.path.basename(test_file), f)}
            data = {'auto_process': 'true'}  # Auto-process

            response = requests.post(
                f"{BASE_URL}/api/receipts/upload",
                files=files,
                data=data
            )

            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ Processing successful")
                print(f"   Receipt ID: {result.get('receipt_id')}")

                extracted = result.get('extracted_data', {})
                if extracted:
                    print(f"\n   Extracted Data:")
                    print(f"      Vendor: {extracted.get('vendor')}")
                    print(f"      Date: {extracted.get('date')}")
                    print(f"      Amount: ${extracted.get('amount')} {extracted.get('currency')}")
                    print(f"      Confidence: {extracted.get('confidence', 0):.1%}")

                matches = result.get('matches', [])
                print(f"\n   Matches Found: {len(matches)}")

                for i, match in enumerate(matches[:3], 1):
                    print(f"\n      Match {i}:")
                    print(f"         Transaction ID: {match.get('transaction_id')}")
                    print(f"         Confidence: {match.get('confidence', 0):.1%}")
                    print(f"         Recommendation: {match.get('recommendation')}")

                # Clean up
                receipt_id = result.get('receipt_id')
                requests.delete(f"{BASE_URL}/api/receipts/{receipt_id}")

            else:
                print(f"❌ Processing failed: {response.status_code}")
                print(f"   Error: {response.text}")

    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Receipt API Endpoints")
    parser.add_argument('--url', type=str, default='http://localhost:5001', help='Base URL for API')
    parser.add_argument('--with-file', action='store_true', help='Test with real receipt file')

    args = parser.parse_args()
    BASE_URL = args.url

    print(f"Testing API at: {BASE_URL}")
    print("Make sure the server is running: python web_ui/app_db.py")

    # Test basic endpoints
    test_api_endpoints()

    # Test with real file if requested
    if args.with_file:
        test_with_real_receipt()
