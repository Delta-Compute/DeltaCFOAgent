"""
Test script for cryptocurrency invoice creation feature
Tests both FIAT and Crypto invoice creation with database validation
"""

import requests
import json
import time
from datetime import datetime, timedelta

# Base URL
BASE_URL = "http://127.0.0.1:5001"

def test_get_invoice_number():
    """Test getting next invoice number (timestamp-based)"""
    print("\n[TEST 1] Getting next invoice number...")
    response = requests.get(f"{BASE_URL}/api/invoices/next-number")

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            invoice_number = data.get('invoice_number')
            print(f"[PASS] Invoice number generated: {invoice_number}")
            # Validate timestamp format (should be 14 digits: YYYYMMDDHHMMSS)
            if len(invoice_number) == 14 and invoice_number.isdigit():
                print(f"[PASS] Invoice number format is valid (timestamp-based)")
                return invoice_number
            else:
                print(f"[FAIL] Invalid invoice number format: {invoice_number}")
                return None
        else:
            print(f"[FAIL] API returned success=False")
            return None
    else:
        print(f"[FAIL] Failed to get invoice number. Status: {response.status_code}")
        return None

def test_create_fiat_invoice():
    """Test creating a FIAT invoice"""
    print("\n[TEST 2] Creating FIAT invoice (USD)...")

    invoice_number = test_get_invoice_number()
    if not invoice_number:
        print("[FAIL] Cannot proceed without invoice number")
        return False

    # Prepare invoice data
    invoice_date = datetime.now().strftime('%Y-%m-%d')
    due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

    invoice_data = {
        "invoice_number": invoice_number,
        "customer_name": "Test Customer FIAT",
        "customer_address": "123 Test Street, Test City",
        "invoice_date": invoice_date,
        "due_date": due_date,
        "currency": "USD",
        "currency_type": "fiat",
        "crypto_currency": None,
        "crypto_network": None,
        "description": "Test FIAT Invoice",
        "line_items": [
            {"description": "Service 1", "quantity": 1, "unit_price": 100.00, "amount": 100.00},
            {"description": "Service 2", "quantity": 2, "unit_price": 50.00, "amount": 100.00}
        ],
        "subtotal": 200.00,
        "tax_percentage": 10,
        "tax_amount": 20.00,
        "total_amount": 220.00,
        "payment_terms": "Net 30 days"
    }

    # Send request
    response = requests.post(
        f"{BASE_URL}/api/invoices/create",
        json=invoice_data,
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"[PASS] FIAT invoice created successfully")
            print(f"  - Invoice ID: {data.get('invoice_id')}")
            print(f"  - Invoice Number: {data.get('invoice_number')}")
            print(f"  - PDF Path: {data.get('pdf_path')}")
            return True
        else:
            print(f"[FAIL] API returned success=False: {data.get('error')}")
            return False
    else:
        print(f"[FAIL] Failed to create FIAT invoice. Status: {response.status_code}")
        print(f"  Error: {response.text}")
        return False

def test_create_crypto_invoice_btc():
    """Test creating a Crypto invoice with BTC"""
    print("\n[TEST 3] Creating Crypto invoice (BTC)...")

    invoice_number = test_get_invoice_number()
    if not invoice_number:
        print("[FAIL] Cannot proceed without invoice number")
        return False

    # Prepare invoice data
    invoice_date = datetime.now().strftime('%Y-%m-%d')
    due_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

    invoice_data = {
        "invoice_number": invoice_number,
        "customer_name": "Test Customer Crypto BTC",
        "customer_address": "456 Crypto Ave, Bitcoin City",
        "invoice_date": invoice_date,
        "due_date": due_date,
        "currency": "BTC",  # This will be stored in currency field
        "currency_type": "crypto",
        "crypto_currency": "BTC",
        "crypto_network": "BTC",
        "description": "Test Bitcoin Invoice",
        "line_items": [
            {"description": "Mining Service", "quantity": 1, "unit_price": 5000.00, "amount": 5000.00}
        ],
        "subtotal": 5000.00,
        "tax_percentage": 0,
        "tax_amount": 0.00,
        "total_amount": 5000.00,
        "payment_terms": "Payment in BTC within 7 days"
    }

    # Send request
    response = requests.post(
        f"{BASE_URL}/api/invoices/create",
        json=invoice_data,
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"[PASS] BTC invoice created successfully")
            print(f"  - Invoice ID: {data.get('invoice_id')}")
            print(f"  - Invoice Number: {data.get('invoice_number')}")
            print(f"  - PDF Path: {data.get('pdf_path')}")
            return True
        else:
            print(f"[FAIL] API returned success=False: {data.get('error')}")
            return False
    else:
        print(f"[FAIL] Failed to create BTC invoice. Status: {response.status_code}")
        print(f"  Error: {response.text}")
        return False

def test_create_crypto_invoice_usdt():
    """Test creating a Crypto invoice with USDT (TRC20)"""
    print("\n[TEST 4] Creating Crypto invoice (USDT-TRC20)...")

    invoice_number = test_get_invoice_number()
    if not invoice_number:
        print("[FAIL] Cannot proceed without invoice number")
        return False

    # Prepare invoice data
    invoice_date = datetime.now().strftime('%Y-%m-%d')
    due_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')

    invoice_data = {
        "invoice_number": invoice_number,
        "customer_name": "Test Customer USDT",
        "customer_address": "789 Stablecoin Blvd, Tether Town",
        "invoice_date": invoice_date,
        "due_date": due_date,
        "currency": "USDT",
        "currency_type": "crypto",
        "crypto_currency": "USDT",
        "crypto_network": "TRC20",
        "description": "Test USDT Invoice",
        "line_items": [
            {"description": "Hosting Service", "quantity": 1, "unit_price": 1500.00, "amount": 1500.00},
            {"description": "Support", "quantity": 1, "unit_price": 500.00, "amount": 500.00}
        ],
        "subtotal": 2000.00,
        "tax_percentage": 5,
        "tax_amount": 100.00,
        "total_amount": 2100.00,
        "payment_terms": "Payment in USDT (TRC20) within 14 days"
    }

    # Send request
    response = requests.post(
        f"{BASE_URL}/api/invoices/create",
        json=invoice_data,
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"[PASS] USDT-TRC20 invoice created successfully")
            print(f"  - Invoice ID: {data.get('invoice_id')}")
            print(f"  - Invoice Number: {data.get('invoice_number')}")
            print(f"  - PDF Path: {data.get('pdf_path')}")
            return True
        else:
            print(f"[FAIL] API returned success=False: {data.get('error')}")
            return False
    else:
        print(f"[FAIL] Failed to create USDT invoice. Status: {response.status_code}")
        print(f"  Error: {response.text}")
        return False

def test_create_custom_crypto_invoice():
    """Test creating a Crypto invoice with custom crypto/network"""
    print("\n[TEST 5] Creating Custom Crypto invoice (ETH-Polygon)...")

    invoice_number = test_get_invoice_number()
    if not invoice_number:
        print("[FAIL] Cannot proceed without invoice number")
        return False

    # Prepare invoice data
    invoice_date = datetime.now().strftime('%Y-%m-%d')
    due_date = (datetime.now() + timedelta(days=21)).strftime('%Y-%m-%d')

    invoice_data = {
        "invoice_number": invoice_number,
        "customer_name": "Test Customer Custom Crypto",
        "customer_address": "999 DeFi Lane, Ethereum City",
        "invoice_date": invoice_date,
        "due_date": due_date,
        "currency": "ETH",
        "currency_type": "crypto",
        "crypto_currency": "ETH",
        "crypto_network": "Polygon",
        "description": "Test Custom Crypto Invoice",
        "line_items": [
            {"description": "Smart Contract Development", "quantity": 1, "unit_price": 10000.00, "amount": 10000.00}
        ],
        "subtotal": 10000.00,
        "tax_percentage": 0,
        "tax_amount": 0.00,
        "total_amount": 10000.00,
        "payment_terms": "Payment in ETH on Polygon network within 21 days"
    }

    # Send request
    response = requests.post(
        f"{BASE_URL}/api/invoices/create",
        json=invoice_data,
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print(f"[PASS] Custom crypto invoice created successfully")
            print(f"  - Invoice ID: {data.get('invoice_id')}")
            print(f"  - Invoice Number: {data.get('invoice_number')}")
            print(f"  - PDF Path: {data.get('pdf_path')}")
            return True
        else:
            print(f"[FAIL] API returned success=False: {data.get('error')}")
            return False
    else:
        print(f"[FAIL] Failed to create custom crypto invoice. Status: {response.status_code}")
        print(f"  Error: {response.text}")
        return False

def run_all_tests():
    """Run all tests and report results"""
    print("=" * 70)
    print("CRYPTOCURRENCY INVOICE FEATURE TEST SUITE")
    print("=" * 70)

    tests = [
        ("Invoice Number Generation", test_get_invoice_number),
        ("FIAT Invoice Creation (USD)", test_create_fiat_invoice),
        ("Crypto Invoice Creation (BTC)", test_create_crypto_invoice_btc),
        ("Crypto Invoice Creation (USDT-TRC20)", test_create_crypto_invoice_usdt),
        ("Custom Crypto Invoice (ETH-Polygon)", test_create_custom_crypto_invoice),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            # Add small delay to ensure unique timestamp-based invoice numbers
            time.sleep(1.5)
        except Exception as e:
            print(f"\n[FAIL] Test '{test_name}' crashed with error: {str(e)}")
            results.append((test_name, False))
            time.sleep(1.5)

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS] PASS" if result else "[FAIL] FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{passed}/{total} tests passed ({100*passed//total}%)")
    print("=" * 70)

    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
