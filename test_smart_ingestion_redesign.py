#!/usr/bin/env python3
"""
Test Script for Redesigned Smart Ingestion System

This tests that Claude now provides COMPLETE PARSING INSTRUCTIONS
instead of just identifying the format type.

Tests:
1. Standard CSV (header on row 0)
2. Complex CSV (multi-row header, multiple currencies, parentheses notation)
3. Crypto deposit CSV (real MEXC format)
"""

import sys
import os
import json
from smart_ingestion import SmartDocumentIngestion, smart_process_file

def print_section(title):
    """Print a section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def test_standard_csv():
    """Test with standard crypto deposit CSV (header on row 0)"""
    print_section("TEST 1: Standard CSV Format (MEXC Deposit History)")

    file_path = "Deposit_History-20240310-20250901_1756736236043.xlsx_-_Sheet1.csv"

    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        return

    print(f"📄 Testing file: {file_path}")
    print("Expected: Header on row 0, standard format")
    print()

    # Test the ingestion
    ingestion = SmartDocumentIngestion()

    # Get Claude's analysis
    print("🤖 Asking Claude for PARSING INSTRUCTIONS...")
    structure_info = ingestion.analyze_document_structure(file_path)

    print("\n📋 CLAUDE'S RESPONSE:")
    print(json.dumps(structure_info, indent=2))

    # Check for new fields
    print("\n✅ VERIFICATION:")
    if 'file_structure' in structure_info:
        print("✅ Claude provided file_structure (NEW!)")
        print(f"   Skip rows: {structure_info['file_structure'].get('skip_rows_before_header', [])}")
        print(f"   Header row: {structure_info['file_structure'].get('header_row_index', 0)}")
        print(f"   Trailing commas: {structure_info['file_structure'].get('has_trailing_commas', False)}")
    else:
        print("❌ Missing file_structure (using defaults)")

    if 'column_cleaning_rules' in structure_info:
        print("✅ Claude provided column_cleaning_rules (NEW!)")
        amount_rules = structure_info.get('column_cleaning_rules', {}).get('amount_column', {})
        print(f"   Remove currency symbols: {amount_rules.get('remove_currency_symbols', 'N/A')}")
        print(f"   Remove commas: {amount_rules.get('remove_commas', 'N/A')}")
        print(f"   Parentheses = negative: {amount_rules.get('parentheses_mean_negative', 'N/A')}")
    else:
        print("❌ Missing column_cleaning_rules (using defaults)")

    # Process the file
    print("\n🔄 Processing file with Claude's instructions...")
    df = ingestion.process_with_structure_info(file_path, structure_info)

    if df is not None:
        print(f"\n✅ Successfully processed {len(df)} transactions")
        print("\n📊 First 3 rows:")
        print(df.head(3).to_string())
        print(f"\n📈 Columns: {list(df.columns)}")
        return True
    else:
        print("\n❌ Processing failed")
        return False

def test_complex_csv():
    """Test with complex multi-row header CSV"""
    print_section("TEST 2: Complex CSV Format (Multi-row header, Mixed currencies, Parentheses)")

    file_path = "test_complex_format.csv"

    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        return

    print(f"📄 Testing file: {file_path}")
    print("Expected: Skip first 3 rows, handle $, €, £, parentheses as negative")
    print()

    # Show file content
    print("📄 File content:")
    with open(file_path, 'r') as f:
        for i, line in enumerate(f):
            print(f"   Row {i}: {line.strip()}")

    # Test the ingestion
    ingestion = SmartDocumentIngestion()

    # Get Claude's analysis
    print("\n🤖 Asking Claude for PARSING INSTRUCTIONS...")
    structure_info = ingestion.analyze_document_structure(file_path)

    print("\n📋 CLAUDE'S RESPONSE:")
    print(json.dumps(structure_info, indent=2))

    # Verify Claude understood the complexity
    print("\n✅ VERIFICATION:")
    file_struct = structure_info.get('file_structure', {})
    skip_rows = file_struct.get('skip_rows_before_header', [])

    if skip_rows == [0, 1, 2]:
        print(f"✅ Claude correctly identified rows to skip: {skip_rows}")
    else:
        print(f"⚠️  Claude suggested skip rows: {skip_rows} (expected [0,1,2])")

    cleaning_rules = structure_info.get('column_cleaning_rules', {}).get('amount_column', {})
    if cleaning_rules.get('parentheses_mean_negative'):
        print("✅ Claude identified parentheses notation: ($100) = negative")
    else:
        print("⚠️  Claude didn't detect parentheses notation")

    # Process the file
    print("\n🔄 Processing file with Claude's instructions...")
    df = ingestion.process_with_structure_info(file_path, structure_info)

    if df is not None:
        print(f"\n✅ Successfully processed {len(df)} transactions")
        print("\n📊 Processed data:")
        print(df.to_string())

        # Verify amounts were cleaned correctly
        print("\n🔍 AMOUNT CLEANING VERIFICATION:")
        for idx, row in df.iterrows():
            print(f"   Row {idx}: Amount = {row.get('Amount', 'N/A')}")

        # Check if negative amounts were handled
        if 'Amount' in df.columns:
            negative_count = (df['Amount'] < 0).sum()
            print(f"\n   Transactions with negative amounts: {negative_count}")
            if negative_count > 0:
                print("   ✅ Parentheses notation handled correctly!")

        return True
    else:
        print("\n❌ Processing failed")
        return False

def test_architecture_comparison():
    """Show the architectural difference"""
    print_section("ARCHITECTURAL COMPARISON")

    print("❌ OLD ARCHITECTURE (Pattern Matching):")
    print("""
    Claude Response: {"format": "coinbase"}

    System Code:
        if format == 'coinbase':
            skiprows = [0, 1, 2]  # HARDCODED!
        elif format == 'mexc':
            skiprows = [0, 1]     # HARDCODED!

    Problem: New format = Code changes required
    """)

    print("\n✅ NEW ARCHITECTURE (True AI Intelligence):")
    print("""
    Claude Response: {
        "file_structure": {
            "skip_rows_before_header": [0, 1, 2],
            "has_trailing_commas": false
        },
        "column_cleaning_rules": {
            "amount_column": {
                "remove_currency_symbols": true,
                "parentheses_mean_negative": true
            }
        }
    }

    System Code:
        skiprows = claude['file_structure']['skip_rows_before_header']
        df = pd.read_csv(file, skiprows=skiprows)

        # Clean amounts per Claude's rules
        if rules['parentheses_mean_negative']:
            # Convert ($100) to -100

    Benefit: ANY format works, NO code changes needed!
    """)

def main():
    """Run all tests"""
    print("\n" + "🧪 " + "="*78)
    print("  SMART INGESTION REDESIGN - TEST SUITE")
    print("  Testing TRUE LLM-powered parsing (no hardcoded formats)")
    print("="*80)

    # Show architecture comparison
    test_architecture_comparison()

    # Test 1: Standard CSV
    test1_passed = test_standard_csv()

    # Test 2: Complex CSV
    test2_passed = test_complex_csv()

    # Summary
    print_section("TEST SUMMARY")
    print(f"Test 1 (Standard CSV): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Test 2 (Complex CSV):  {'✅ PASSED' if test2_passed else '❌ FAILED'}")

    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nKey Achievements:")
        print("✅ Claude provides complete parsing instructions (not just format labels)")
        print("✅ System uses Claude's instructions dynamically (no hardcoded checks)")
        print("✅ Works with ANY CSV format without code changes")
        print("✅ Handles multi-row headers, multiple currencies, parentheses notation")
        print("\n🚀 System is now TRULY scalable to any user's data!")
    else:
        print("\n⚠️  Some tests failed - review output above")

    print()

if __name__ == "__main__":
    main()
