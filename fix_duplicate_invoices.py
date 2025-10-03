#!/usr/bin/env python3
"""
Fix Duplicate Invoice Numbers
Adiciona verificação para evitar UNIQUE constraint failed
"""

import os
import re

def patch_duplicate_check():
    """
    Adiciona verificação de duplicatas na função process_invoice_with_claude
    """
    app_db_path = "web_ui/app_db.py"

    if not os.path.exists(app_db_path):
        print(f"Error: {app_db_path} not found")
        return False

    try:
        print("Adding duplicate invoice check...")

        with open(app_db_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the place where we insert the invoice and add duplicate check
        insert_pattern = """        # Save to database with robust connection handling
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = get_db_connection()
                conn.execute('''
                    INSERT INTO invoices ("""

        new_pattern = """        # Save to database with robust connection handling
        max_retries = 3
        for attempt in range(max_retries):
            try:
                conn = get_db_connection()

                # Check if invoice_number already exists
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM invoices WHERE invoice_number = ?', (invoice_data['invoice_number'],))
                existing = cursor.fetchone()

                if existing:
                    # Generate unique invoice number by appending timestamp
                    import time
                    timestamp = int(time.time())
                    original_number = invoice_data['invoice_number']
                    invoice_data['invoice_number'] = f"{original_number}_{timestamp}"
                    print(f"Duplicate invoice number detected. Changed {original_number} to {invoice_data['invoice_number']}")

                conn.execute('''
                    INSERT INTO invoices ("""

        if insert_pattern in content:
            content = content.replace(insert_pattern, new_pattern)

            # Write updated file
            with open(app_db_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print("SUCCESS: Added duplicate invoice check")
            return True
        else:
            print("WARNING: Could not find insert pattern")
            return False

    except Exception as e:
        print(f"ERROR: Failed to add duplicate check: {e}")
        return False

def add_upsert_functionality():
    """
    Adiciona funcionalidade de UPSERT como alternativa
    """
    app_db_path = "web_ui/app_db.py"

    try:
        with open(app_db_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add a new function for safe invoice insertion
        upsert_function = '''
def safe_insert_invoice(conn, invoice_data):
    """
    Safely insert or update invoice to avoid UNIQUE constraint errors
    """
    cursor = conn.cursor()

    # Check if invoice exists
    cursor.execute('SELECT id FROM invoices WHERE invoice_number = ?', (invoice_data['invoice_number'],))
    existing = cursor.fetchone()

    if existing:
        # Update existing invoice
        cursor.execute("""
            UPDATE invoices SET
                date=?, due_date=?, vendor_name=?, vendor_address=?,
                vendor_tax_id=?, customer_name=?, customer_address=?, customer_tax_id=?,
                total_amount=?, currency=?, tax_amount=?, subtotal=?,
                line_items=?, status=?, invoice_type=?, confidence_score=?, processing_notes=?,
                source_file=?, extraction_method=?, processed_at=?, created_at=?,
                business_unit=?, category=?, currency_type=?
            WHERE invoice_number=?
        """, (
            invoice_data['date'], invoice_data['due_date'], invoice_data['vendor_name'],
            invoice_data['vendor_address'], invoice_data['vendor_tax_id'], invoice_data['customer_name'],
            invoice_data['customer_address'], invoice_data['customer_tax_id'], invoice_data['total_amount'],
            invoice_data['currency'], invoice_data['tax_amount'], invoice_data['subtotal'],
            invoice_data['line_items'], invoice_data['status'], invoice_data['invoice_type'],
            invoice_data['confidence_score'], invoice_data['processing_notes'], invoice_data['source_file'],
            invoice_data['extraction_method'], invoice_data['processed_at'], invoice_data['created_at'],
            invoice_data['business_unit'], invoice_data['category'], invoice_data['currency_type'],
            invoice_data['invoice_number']
        ))
        print(f"Updated existing invoice: {invoice_data['invoice_number']}")
        return "updated"
    else:
        # Insert new invoice
        cursor.execute("""
            INSERT INTO invoices (
                id, invoice_number, date, due_date, vendor_name, vendor_address,
                vendor_tax_id, customer_name, customer_address, customer_tax_id,
                total_amount, currency, tax_amount, subtotal,
                line_items, status, invoice_type, confidence_score, processing_notes,
                source_file, extraction_method, processed_at, created_at,
                business_unit, category, currency_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            invoice_data['id'], invoice_data['invoice_number'], invoice_data['date'],
            invoice_data['due_date'], invoice_data['vendor_name'], invoice_data['vendor_address'],
            invoice_data['vendor_tax_id'], invoice_data['customer_name'], invoice_data['customer_address'],
            invoice_data['customer_tax_id'], invoice_data['total_amount'], invoice_data['currency'],
            invoice_data['tax_amount'], invoice_data['subtotal'], invoice_data['line_items'],
            invoice_data['status'], invoice_data['invoice_type'], invoice_data['confidence_score'],
            invoice_data['processing_notes'], invoice_data['source_file'], invoice_data['extraction_method'],
            invoice_data['processed_at'], invoice_data['created_at'], invoice_data['business_unit'],
            invoice_data['category'], invoice_data['currency_type']
        ))
        print(f"Inserted new invoice: {invoice_data['invoice_number']}")
        return "inserted"

'''

        # Find a good place to insert the function (before process_invoice_with_claude)
        function_insert_point = content.find("def process_invoice_with_claude")
        if function_insert_point > 0:
            content = content[:function_insert_point] + upsert_function + content[function_insert_point:]

            # Write updated content
            with open(app_db_path, 'w', encoding='utf-8') as f:
                f.write(content)

            print("SUCCESS: Added safe_insert_invoice function")
            return True

    except Exception as e:
        print(f"ERROR: Failed to add upsert functionality: {e}")
        return False

def main():
    print("Fix Duplicate Invoice Numbers")
    print("=" * 30)

    # Apply both patches
    success1 = patch_duplicate_check()
    success2 = add_upsert_functionality()

    if success1 and success2:
        print("\nSUCCESS: All patches applied")
        print("The application now handles:")
        print("  - Database locks with retry logic")
        print("  - Duplicate invoice numbers automatically")
        print("  - UPSERT functionality for safer operations")
        return True
    else:
        print("\nWARNING: Some patches failed")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\nRestart the application to apply changes:")
        print("cd web_ui && python app_db.py")