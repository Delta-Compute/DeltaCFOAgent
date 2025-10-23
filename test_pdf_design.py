"""Test PDF design by creating sample invoices"""
import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:5001"

def create_sample_crypto_invoice():
    """Create a sample crypto invoice to test the new PDF design"""
    print("Creating sample CRYPTOCURRENCY invoice...")

    # Get invoice number
    response = requests.get(f"{BASE_URL}/api/invoices/next-number")
    if response.status_code != 200:
        print(f"Failed to get invoice number: {response.text}")
        return False

    invoice_number = response.json().get('invoice_number')
    print(f"Invoice number: {invoice_number}")

    # Prepare invoice data
    invoice_date = datetime.now().strftime('%Y-%m-%d')
    due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

    invoice_data = {
        "invoice_number": invoice_number,
        "customer_name": "Blockchain Solutions Inc.",
        "customer_address": "123 Crypto Street, San Francisco, CA 94102",
        "invoice_date": invoice_date,
        "due_date": due_date,
        "currency": "BTC",
        "currency_type": "crypto",
        "crypto_currency": "BTC",
        "crypto_network": "Bitcoin",
        "description": "Monthly Hosting & Data Center Services",
        "line_items": [
            {"description": "Server Hosting (10 Servers)", "quantity": 10, "unit_price": 500.00, "amount": 5000.00},
            {"description": "Network Bandwidth (10TB)", "quantity": 10, "unit_price": 100.00, "amount": 1000.00},
            {"description": "24/7 Technical Support", "quantity": 1, "unit_price": 2000.00, "amount": 2000.00},
        ],
        "subtotal": 8000.00,
        "tax_percentage": 0,
        "tax_amount": 0.00,
        "total_amount": 8000.00,
        "payment_terms": "Payment due within 30 days. Please send payment in BTC to the address provided. Late payments subject to 1.5% monthly interest charge."
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
            print(f"SUCCESS! Crypto invoice created:")
            print(f"  - Invoice ID: {data.get('invoice_id')}")
            print(f"  - Invoice Number: {data.get('invoice_number')}")
            print(f"  - PDF Path: {data.get('pdf_path')}")
            return True
        else:
            print(f"FAILED: {data.get('error')}")
            return False
    else:
        print(f"FAILED: Status {response.status_code}")
        print(f"  Error: {response.text}")
        return False

def create_sample_fiat_invoice():
    """Create a sample FIAT invoice to test the new PDF design"""
    print("\nCreating sample FIAT invoice...")
    time.sleep(1.5)  # Ensure unique timestamp

    # Get invoice number
    response = requests.get(f"{BASE_URL}/api/invoices/next-number")
    if response.status_code != 200:
        print(f"Failed to get invoice number: {response.text}")
        return False

    invoice_number = response.json().get('invoice_number')
    print(f"Invoice number: {invoice_number}")

    # Prepare invoice data
    invoice_date = datetime.now().strftime('%Y-%m-%d')
    due_date = (datetime.now() + timedelta(days=45)).strftime('%Y-%m-%d')

    invoice_data = {
        "invoice_number": invoice_number,
        "customer_name": "Enterprise Technologies LLC",
        "customer_address": "456 Business Ave, New York, NY 10001",
        "invoice_date": invoice_date,
        "due_date": due_date,
        "currency": "USD",
        "currency_type": "fiat",
        "crypto_currency": None,
        "crypto_network": None,
        "description": "Quarterly Cloud Infrastructure Services",
        "line_items": [
            {"description": "Cloud Computing Resources", "quantity": 1, "unit_price": 15000.00, "amount": 15000.00},
            {"description": "Database Management", "quantity": 1, "unit_price": 5000.00, "amount": 5000.00},
            {"description": "Security & Compliance", "quantity": 1, "unit_price": 3000.00, "amount": 3000.00},
            {"description": "Technical Support", "quantity": 1, "unit_price": 2000.00, "amount": 2000.00},
        ],
        "subtotal": 25000.00,
        "tax_percentage": 8.5,
        "tax_amount": 2125.00,
        "total_amount": 27125.00,
        "payment_terms": "Net 45 days. Payment accepted via wire transfer, ACH, or check. Please reference invoice number on all payments."
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
            print(f"SUCCESS! FIAT invoice created:")
            print(f"  - Invoice ID: {data.get('invoice_id')}")
            print(f"  - Invoice Number: {data.get('invoice_number')}")
            print(f"  - PDF Path: {data.get('pdf_path')}")
            return True
        else:
            print(f"FAILED: {data.get('error')}")
            return False
    else:
        print(f"FAILED: Status {response.status_code}")
        print(f"  Error: {response.text}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("PDF DESIGN TEST - Creating Sample Invoices")
    print("=" * 70)

    crypto_success = create_sample_crypto_invoice()
    fiat_success = create_sample_fiat_invoice()

    print("\n" + "=" * 70)
    print("RESULTS:")
    print("=" * 70)
    print(f"Crypto Invoice: {'SUCCESS' if crypto_success else 'FAILED'}")
    print(f"FIAT Invoice: {'SUCCESS' if fiat_success else 'FAILED'}")
    print("\nCheck the generated PDFs in: invoices/issued/")
    print("=" * 70)
