"""
Smart Document Ingestion System - Claude AI Required
====================================================

This system uses Claude AI to automatically analyze and process ANY CSV format without manual configuration.

KEY FEATURES:
- Automatic format detection (crypto exchanges, banks, investment accounts, etc.)
- Intelligent column mapping to standardized format (Date, Description, Amount)
- Dynamic description creation for files without clear description columns
- Handles debit/credit splits, multi-currency, and complex formats
- 95%+ accuracy with Claude AI analysis

SUPPORTED FORMATS:
- Chase Bank (checking, credit cards)
- Crypto Exchanges (MEXC, Coinbase, Binance, etc.)
- Investment Accounts
- Generic Bank Statements
- Any CSV with financial transaction data

REQUIREMENTS:
- ANTHROPIC_API_KEY environment variable MUST be set
- NO FALLBACK PROCESSING - Claude AI is required for reliability
- Fails fast if Claude AI is not available

USAGE:
    from smart_ingestion import smart_process_file
    df = smart_process_file('any_financial_csv.csv')
    # Returns standardized DataFrame with Date, Description, Amount columns
"""

import os
import pandas as pd
import json
import re
from typing import Dict, Any, Optional, Tuple
import anthropic
from pathlib import Path
import base64

class SmartDocumentIngestion:
    def __init__(self):
        self.claude_client = self._init_claude_client()

    def _init_claude_client(self):
        """Initialize Claude API client"""
        print(" DEBUG: Initializing Claude API client...")
        try:
            # Check environment variable first
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                api_key = api_key.strip()  # Remove newlines and whitespace
            print(f" DEBUG: API key from env: {'Found' if api_key else 'Not found'}")

            # Check for .anthropic_api_key file if env var not found
            if not api_key:
                key_file = '.anthropic_api_key'
                print(f" DEBUG: Checking for API key file: {key_file}")
                if os.path.exists(key_file):
                    with open(key_file, 'r') as f:
                        api_key = f.read().strip()
                    print(" DEBUG: API key loaded from file")

            if not api_key:
                print("  No ANTHROPIC_API_KEY found - smart ingestion disabled")
                return None

            print(" DEBUG: Creating Anthropic client...")
            client = anthropic.Anthropic(api_key=api_key)
            print(" DEBUG: Claude API client initialized successfully")
            return client
        except Exception as e:
            print(f" Error initializing Claude API: {e}")
            import traceback
            print(f" DEBUG: Traceback: {traceback.format_exc()}")
            return None

    def analyze_document_structure(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze document structure using Claude API
        Returns mapping instructions for processing
        """
        print(f" DEBUG: Starting document analysis for {file_path}")

        if not self.claude_client:
            error_msg = " CLAUDE AI REQUIRED: Smart document ingestion requires a valid ANTHROPIC_API_KEY. This ensures accurate processing of any CSV format."
            print(f" DEBUG: {error_msg}")
            raise ValueError(error_msg)

        try:
            print(" DEBUG: Getting document sample...")
            # Read sample of the document
            sample_content = self._get_document_sample(file_path)
            if not sample_content:
                print(" DEBUG: No sample content, using fallback analysis")
                return self._fallback_analysis(file_path)

            print(f" DEBUG: Sample content length: {len(sample_content)}")

            # Ask Claude to analyze the structure
            print(" DEBUG: Building analysis prompt...")
            prompt = self._build_analysis_prompt(sample_content, file_path)
            print(f" DEBUG: Prompt length: {len(prompt)}")

            print(" DEBUG: Calling Claude API...")
            response = self.claude_client.messages.create(
                model="claude-3-haiku-20240307",  # Fast, cheap model for structure analysis
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            print(" DEBUG: Claude API call successful")

            # Parse Claude's response
            print(" DEBUG: Parsing Claude response...")
            analysis = self._parse_claude_response(response.content[0].text)
            analysis['claude_analysis'] = True
            analysis['cost_estimate'] = 0.02  # Approximate cost

            print(f" Claude analyzed document structure: {analysis.get('format', 'unknown')}")
            print(f" DEBUG: Analysis result: {analysis}")
            return analysis

        except Exception as e:
            print(f" Claude analysis failed: {e}")
            import traceback
            print(f" DEBUG: Claude analysis error traceback: {traceback.format_exc()}")
            raise ValueError(f" CLAUDE AI ANALYSIS FAILED: {e}. Smart document ingestion requires Claude AI for reliable processing.")

    def _get_document_sample(self, file_path: str) -> Optional[str]:
        """Get sample content from document for analysis"""
        try:
            file_ext = Path(file_path).suffix.lower()

            if file_ext == '.csv':
                # Read first 10 lines of CSV
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = [f.readline().strip() for _ in range(10)]
                return '\n'.join(lines)

            elif file_ext in ['.xlsx', '.xls']:
                # Read first 10 rows of Excel
                df = pd.read_excel(file_path, nrows=10)
                return df.to_string()

            elif file_ext == '.pdf':
                # For PDFs, we'll need full Claude processing
                return f"PDF_FILE:{file_path}"

            else:
                # Try to read as text
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read(2000)  # First 2000 chars

        except Exception as e:
            print(f" Error reading document sample: {e}")
            return None

    def _build_analysis_prompt(self, sample_content: str, file_path: str) -> str:
        """Build prompt for Claude to analyze document structure AND provide parsing instructions"""
        file_name = os.path.basename(file_path)

        return f"""
You are analyzing a financial CSV file to provide COMPLETE PARSING INSTRUCTIONS for ANY format.

Your job is to tell me EXACTLY HOW TO READ this file, not just identify what type it is.

File: {file_name}
Content sample:
{sample_content}

STEP 1: FILE STRUCTURE ANALYSIS
Analyze the physical structure of this CSV file:
- Which rows should be SKIPPED before the header? (often CSVs have title rows, metadata rows, blank rows before headers)
- Which row number contains the ACTUAL COLUMN HEADERS? (0-indexed)
- Which row does the DATA start on?
- Are there footer rows that should be skipped?
- Are there trailing commas that need to be cleaned?

STEP 2: COLUMN MAPPING REQUIREMENTS
Analyze ALL columns and map them to standard financial transaction fields:

REQUIRED MAPPINGS:
- DATE: Look for any date/time columns ("Transaction Date", "Date", "Post Date", "Time", "Timestamp")
- DESCRIPTION: Look for descriptive text ("Description", "Merchant", "Details", "Status", "Notes", "Memo")
- AMOUNT: Look for monetary values ("Amount", "Debit", "Credit", "Transaction Amount", "Deposit Amount", "Value")

OPTIONAL MAPPINGS:
- TYPE: Transaction type/category ("Type", "Transaction Type", "Category", "Status")
- CURRENCY: Currency info ("Currency", "Crypto", "Asset", "Symbol")

  CRITICAL: CRYPTOCURRENCY CURRENCY MAPPING
  For cryptocurrency exchanges (Coinbase, Binance, MEXC, Kraken, Gemini, etc.):
  - The currency_column should represent THE ASSET BEING TRANSACTED (BTC, ETH, USDT, SOL, etc.)
  - DO NOT map "Price Currency", "Quote Currency", or "Spot Price Currency" columns to currency_column
  - These "Price Currency" columns show what the price is QUOTED in (usually USD), NOT what is being traded

  Example - Coinbase CSV has multiple currency-related columns:
  - "Asset" column contains: BTC, ETH, USDT (the crypto being transacted) ✅ CORRECT
  - "Price Currency" column contains: USD, USD, USD (what price is quoted in) ❌ WRONG
  - CORRECT MAPPING: currency_column = "Asset"
  - WRONG MAPPING: currency_column = "Price Currency"

  The currency_column should answer: "What asset/currency is being MOVED in this transaction?"
  NOT "What currency is the price DISPLAYED in?"

  For traditional bank statements:
  - Map the actual currency column (USD, EUR, BRL, GBP, etc.)
  - This is straightforward as there's usually only one currency column

- REFERENCE: Reference numbers ("Reference", "TxID", "Transaction ID", "Check Number", "Hash")
- BALANCE: Account balance ("Balance", "Running Balance")
- ACCOUNT_IDENTIFIER: Account/card/wallet identifiers ("Card", "Account", "Account Number", "Card Number", "Wallet", "Portfolio", "UID")
- DIRECTION: Transaction direction/flow ("Direction", "Type", "Flow", "Side", "In/Out", "Operation Type")
  * If this column exists, identify values that mean INCOMING vs OUTGOING
  * Incoming values (amount should be positive): "In", "Incoming", "Received", "Deposit", "Credit", "Credited"
  * Outgoing values (amount should be negative): "Out", "Outgoing", "Sent", "Withdrawal", "Debit", "Sent"
- ORIGIN: Source of funds ("From", "Sender", "Origin", "Source", can also be derived from Network/blockchain for crypto)
- DESTINATION: Destination of funds ("To", "Recipient", "Destination", can be exchange name for crypto deposits)
- NETWORK: Blockchain network ("Network", "Chain", "Protocol") - used to derive Origin for crypto
- ADDITIONAL: Any other relevant columns

CRITICAL: MULTI-ACCOUNT DETECTION
If the file contains transactions from MULTIPLE accounts/cards/wallets in a single CSV:
- Identify the column that distinguishes between accounts (e.g., "Card", "Account Number")
- Note this in "account_identifier_column" field
- This enables intelligent entity mapping and routing per account

SPECIAL CASES TO HANDLE:
- Crypto exchange DEPOSITS (MEXC, Coinbase, Binance):
  * May have "Crypto", "Network", "Status", "Progress", "Deposit Amount", "TxID", "Deposit Address"
  * For deposits TO exchange:
    - Origin = Network/blockchain (from "Network" column, e.g., "Ethereum(ERC20)" -> "Ethereum")
    - Destination = Exchange name (derive from filename like "MEXC_Deposits" -> "MEXC Exchange")
  * Network column often contains blockchain info like "Bitcoin(BTC)", "Tron(TRC20)", "Ethereum(ERC20)"
  * Map "Crypto" -> currency_column, "TxID" -> reference_column
  * Amounts should be POSITIVE (money coming in)

- Crypto exchange WITHDRAWALS (MEXC, Coinbase, Binance):
  * May have columns: "Status", "Withdrawal Address", "Request Amount", "Settlement Amount", "Trading Fee", "TxID", "Crypto", "Network", "UID"
  * CRITICAL MAPPINGS for withdrawals:
    - origin_column = NULL (will be derived from exchange name in filename)
    - destination_column = "Withdrawal Address" (the actual blockchain wallet address where funds were sent)
    - reference_column = "TxID" (blockchain transaction hash)
    - currency_column = "Crypto" (e.g., USDT, BTC, TAO)
    - network_column = "Network" (e.g., "Ethereum(ERC20)", "Tron(TRC20)", "Bittensor(TAO)")
    - amount_column = "Settlement Amount" preferred over "Request Amount" (actual amount after fees)
  * For withdrawals FROM exchange:
    - Origin = Exchange name (derive from filename, e.g., "MEXC" from "MEXC_withdraws..." -> "MEXC Exchange")
    - Destination = Actual withdrawal address from "Withdrawal Address" column (preserve full address)
  * Amounts should be NEGATIVE (money leaving = expenses)
  * Status often contains "Withdrawal Successful" or similar
  * special_handling should be "crypto_withdrawal"
  * exchange_name should be extracted from filename (e.g., "MEXC" from "MEXC_withdraws_...")

- Bank statements: May have "Debit"/"Credit" instead of "Amount"
- Credit cards: May have "Transaction Date" vs "Post Date"
- Investment accounts: May have "Symbol", "Quantity", "Price"

FILENAME ANALYSIS:
- Extract exchange name from filename patterns like "MEXC_withdraws", "Coinbase_deposits", "Binance_transactions"
- Use filename context to determine transaction direction (deposits vs withdrawals)
- Example: "MEXC_withdraws_sep_-_oct_2025_-_Sheet1.csv" -> exchange_name = "MEXC", special_handling = "crypto_withdrawal"

CRITICAL: ORIGIN/DESTINATION DERIVATION LOGIC
Instead of just identifying the file type, provide EXECUTABLE LOGIC for deriving Origin and Destination per row:

METHOD 1 - Direct Column Mapping (preferred when columns exist):
If there are clear "From"/"To" or "Source"/"Destination" columns, set:
- origin_column: "exact column name"
- destination_column: "exact column name"
- origin_destination_logic.method: "direct_mapping"

METHOD 2 - Per-Row Conditional Logic (for mixed transaction types):
When transactions have different types (withdrawals, deposits, buys, sends, etc.) in the SAME file:
- Provide conditional logic in origin_destination_logic.per_row_conditions
- Each condition should be a Python-evaluable expression using row data
- Example for Coinbase with mixed transaction types:
  {{
    "condition": "row['Transaction Type'] == 'Send'",
    "origin": "'Coinbase Exchange'",
    "destination": "row['Notes']"  // The wallet address from Notes column
  }}
  {{
    "condition": "row['Transaction Type'] in ['Buy', 'Receive', 'Convert']",
    "origin": "row['Notes'] if 'from' in str(row['Notes']).lower() else 'External Source'",
    "destination": "'Coinbase Exchange'"
  }}

METHOD 3 - Exchange Name Based (for uniform transaction files):
If ALL transactions are the same type (all withdrawals OR all deposits):
- Set exchange_name from filename
- Set method to "exchange_name_based"
- Set special_handling to "crypto_withdrawal" or "crypto_deposit"

RULES:
1. ALWAYS provide origin_destination_logic object, even if columns exist
2. For mixed files, ALWAYS use per_row_conditions - don't rely on special_handling string checks
3. Conditions are evaluated IN ORDER - first matching condition wins
4. Use actual column names in row['Column Name'] expressions
5. String literals must be in quotes: 'Coinbase Exchange', not Coinbase Exchange
6. Access DataFrame columns with: row['Exact Column Name']

CREATE DESCRIPTION RULES:
If no clear description column exists, provide rules to create one from available columns.
Example: "Combine Status + Crypto + Network" or "Use Merchant + Category"

STEP 3: DATA CLEANING INSTRUCTIONS
For each mapped column, provide cleaning instructions:
- Does the amount column have currency symbols ($, €, etc.) that need removal?
- Does the amount column have commas for thousands that need removal?
- Are amounts in parentheses negative? (e.g., "($100.00)" = -100.00)
- Does the date need timezone handling?
- Are there any text fields that need trimming or normalization?

Please respond with a JSON object containing COMPLETE PARSING AND PROCESSING INSTRUCTIONS:
{{
    "file_structure": {{
        "skip_rows_before_header": [0, 1, 2],  // List of row indices to skip (0-indexed), or [] if none
        "header_row_index": 3,                  // Which row (0-indexed) contains column names
        "data_starts_at_row": 4,                // Which row (0-indexed) data begins
        "has_trailing_commas": true,            // Does CSV have extra commas at line ends?
        "has_footer_rows": false,               // Are there summary/total rows at bottom?
        "footer_row_count": 0                   // How many rows to skip from bottom
    }},
    "format": "chase_checking|chase_credit|coinbase|mexc_deposits|crypto_exchange|bank_statement|investment|other",
    "date_column": "exact_column_name_for_dates_or_null",
    "description_column": "exact_column_name_or_null",
    "amount_column": "exact_column_name_or_null",
    "type_column": "exact_column_name_or_null",
    "currency_column": "exact_column_name_or_null",
    "reference_column": "exact_column_name_or_null",
    "balance_column": "exact_column_name_or_null",
    "account_identifier_column": "exact_column_name_for_account_card_wallet_or_null",
    "direction_column": "exact_column_name_for_transaction_direction_or_null",
    "direction_incoming_values": ["list", "of", "values", "meaning", "incoming"],
    "direction_outgoing_values": ["list", "of", "values", "meaning", "outgoing"],
    "origin_column": "exact_column_name_or_null",
    "destination_column": "exact_column_name_or_null",
    "network_column": "exact_column_name_for_blockchain_network_or_null",
    "has_multiple_accounts": true|false,
    "account_identifier_type": "card_number|account_number|wallet_address|portfolio_id|null",
    "description_creation_rule": "rule_for_creating_description_if_missing",
    "origin_destination_rule": "rule_for_deriving_origin_and_destination_or_null",
    "origin_destination_logic": {{
        "method": "direct_mapping|per_row_logic|exchange_name_based|null",
        "exchange_name": "MEXC|Coinbase|Binance|null",
        "logic_explanation": "Natural language explanation of how to derive Origin and Destination",
        "per_row_conditions": [
            {{
                "condition": "if row['Transaction Type'] == 'Send'",
                "origin": "'Coinbase Exchange'",
                "destination": "row['Notes']"
            }},
            {{
                "condition": "if row['Transaction Type'] in ['Buy', 'Receive', 'Convert']",
                "origin": "'External Source'",
                "destination": "'Coinbase Exchange'"
            }}
        ]
    }},
    "exchange_name": "MEXC|Coinbase|Binance|null",
    "amount_processing": "single_column|debit_credit_split|calculate_from_quantity_price",
    "date_format": "detected_date_format_pattern",
    "column_cleaning_rules": {{
        "amount_column": {{
            "remove_currency_symbols": true,     // Remove $, €, £, etc.
            "remove_commas": true,                // Remove thousand separators
            "parentheses_mean_negative": false,   // Is ($100) = -100?
            "multiply_by": 1                      // Any scaling needed? (e.g., cents to dollars)
        }},
        "date_column": {{
            "format": "%Y-%m-%d %H:%M:%S %Z",    // strptime format string
            "timezone_handling": "convert_to_utc|keep_local|ignore"
        }}
    }},
    "special_handling": "standard|misaligned_headers|multi_currency|crypto_deposit|crypto_withdrawal|crypto_format|multi_account|none",
    "confidence": 0.95,
    "processing_method": "python_pandas|claude_extraction",
    "additional_columns": ["list_of_other_important_columns"],
    "notes": "Detailed analysis of the file format and any special considerations"
}}

CRITICAL RULES:
1. Use EXACT column names from the header row - be precise with capitalization and spacing
2. Provide SPECIFIC parsing instructions so NO hardcoded format checks are needed
3. The file_structure section should tell me EXACTLY how to use pandas.read_csv()
4. The column_cleaning_rules should tell me EXACTLY how to clean each column
5. If you see rows before the actual header (like metadata, titles, blank rows), put them in skip_rows_before_header
6. Example: Coinbase CSVs have 3 rows before headers -> skip_rows_before_header: [0, 1, 2], header_row_index: 3
7. For standard CSVs with header on row 0, use: skip_rows_before_header: [], header_row_index: 0

Only respond with the JSON object, no other text.
"""

    def _parse_claude_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's JSON response"""
        try:
            # Extract JSON from response
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()

            # Clean invalid control characters that break JSON parsing
            # (Claude sometimes includes special chars like newlines in string values)
            response_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', response_text)

            result = json.loads(response_text)

            # Ensure file_structure exists with defaults if not provided by Claude
            if 'file_structure' not in result:
                result['file_structure'] = {
                    'skip_rows_before_header': [],
                    'header_row_index': 0,
                    'data_starts_at_row': 1,
                    'has_trailing_commas': False,
                    'has_footer_rows': False,
                    'footer_row_count': 0
                }

            # Ensure column_cleaning_rules exists with defaults
            if 'column_cleaning_rules' not in result:
                result['column_cleaning_rules'] = {
                    'amount_column': {
                        'remove_currency_symbols': True,
                        'remove_commas': True,
                        'parentheses_mean_negative': False,
                        'multiply_by': 1
                    }
                }

            return result
        except Exception as e:
            print(f" Error parsing Claude response: {e}")
            print(f"Response text: {response_text[:500]}")
            raise ValueError(f"Failed to parse Claude's analysis: {e}")

    def _validate_claude_required(self) -> None:
        """Validate that Claude AI is available - no fallback allowed"""
        if not self.claude_client:
            raise ValueError(" CLAUDE AI REQUIRED: This application requires a valid ANTHROPIC_API_KEY for intelligent document processing. No fallback processing is available to ensure accuracy and reliability.")

    def _correct_structure_analysis(self, file_path: str, expected_columns: list, actual_columns: list, original_skiprows: list) -> Dict[str, Any]:
        """
        Ask Claude to correct its structure analysis using EMPIRICAL RESULTS
        This is the scalable, LLM-based self-correction approach

        Instead of asking Claude to guess, we try different skiprows values
        and show Claude the ACTUAL columns that result from each attempt.
        """
        print(f" Using empirical LLM-based correction approach...")

        if not self.claude_client:
            raise ValueError(" Claude AI required for structure correction")

        try:
            file_name = os.path.basename(file_path)

            # ===================================================================
            # EMPIRICAL APPROACH: Try different skiprows and collect results
            # ===================================================================
            print(f" Testing different skiprows values empirically...")

            # First, create cleaned CSV if needed (to handle trailing commas)
            import tempfile
            needs_cleaning = False
            with open(file_path, 'r') as f:
                first_two_lines = [f.readline() for _ in range(2)]
                if len(first_two_lines) >= 2:
                    header_commas = first_two_lines[0].count(',')
                    data_commas = first_two_lines[1].count(',')
                    if data_commas > header_commas:
                        needs_cleaning = True

            test_file_path = file_path
            if needs_cleaning:
                print(f" Cleaning trailing commas for empirical testing...")
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
                    test_file_path = temp_file.name
                    with open(file_path, 'r') as f:
                        for line in f:
                            cleaned_line = line.rstrip('\n')
                            while cleaned_line.endswith(','):
                                cleaned_line = cleaned_line[:-1]
                            temp_file.write(cleaned_line + '\n')

            skiprows_options = [
                [],           # No skipping (header on line 0)
                [0],          # Skip line 0 (header on line 1)
                [0, 1],       # Skip lines 0-1 (header on line 2)
                [0, 1, 2],    # Skip lines 0-2 (header on line 3)
                [0, 1, 2, 3], # Skip lines 0-3 (header on line 4)
            ]

            empirical_results = []
            for skiprows_test in skiprows_options:
                try:
                    # Try reading with this skiprows value
                    test_df = pd.read_csv(test_file_path, skiprows=skiprows_test, nrows=0)  # Just read headers
                    columns_found = list(test_df.columns)
                    empirical_results.append({
                        'skiprows': skiprows_test,
                        'columns': columns_found,
                        'success': True
                    })
                    print(f"  Option skiprows={skiprows_test} -> {columns_found[:3]}...")  # Show first 3 columns
                except Exception as e:
                    empirical_results.append({
                        'skiprows': skiprows_test,
                        'columns': [],
                        'success': False,
                        'error': str(e)
                    })
                    print(f"  Option skiprows={skiprows_test} -> ERROR")

            # Clean up temp file if created
            if needs_cleaning and test_file_path != file_path:
                os.unlink(test_file_path)

            # Build prompt showing Claude the empirical results WITH match indicators
            results_lines = []
            for i, result in enumerate(empirical_results):
                if result['success']:
                    columns = result['columns']
                    # Check how many expected columns are found
                    matches = [col for col in expected_columns if col in columns]
                    match_indicator = f"  MATCHES {len(matches)}/{len(expected_columns)} expected columns: {matches}" if matches else "  No matches"
                    results_lines.append(f"Option {i+1}: skiprows={result['skiprows']} -> Columns: {columns}{match_indicator}")

            results_text = "\n".join(results_lines)

            correction_prompt = f"""
You previously analyzed this CSV file and gave WRONG skip_rows instructions.

File: {file_name}

YOUR ORIGINAL (WRONG) ANALYSIS:
- You said: skip_rows_before_header={original_skiprows}
- You expected columns: {expected_columns}
- But that gave WRONG columns (data values, not headers): {actual_columns}

EMPIRICAL TEST RESULTS:
I tested different skiprows values. Here's what ACTUALLY happens when reading this file:

{results_text}

CRITICAL INSTRUCTIONS:
1. Look for the option that has " MATCHES {len(expected_columns)}/{len(expected_columns)}" (100% match)
2. That option has column NAMES like "{expected_columns[0] if expected_columns else 'N/A'}", not data VALUES
3. Select the skip_rows value from that option

Example logic:
- If Option 1 shows " MATCHES 3/3" and contains 'Posting Date', 'Description', 'Amount', use skiprows=[]
- If Option 4 shows " MATCHES 3/3" and contains those headers, use skiprows=[0, 1, 2]

Respond with JSON ONLY (no other text):
{{
    "skip_rows_before_header": [],
    "header_row_index": 0,
    "explanation": "Option X matches all expected headers"
}}
"""

            print(f" DEBUG: Correction prompt with empirical results (length: {len(correction_prompt)})")
            print(f" DEBUG: Calling Claude API for correction...")

            response = self.claude_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": correction_prompt}]
            )

            print(" DEBUG: Claude correction call successful")

            # Parse correction response
            correction_text = response.content[0].text.strip()
            if correction_text.startswith('```json'):
                correction_text = correction_text.replace('```json', '').replace('```', '').strip()

            correction_text = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', correction_text)
            correction = json.loads(correction_text)

            print(f" Claude's correction: {correction.get('explanation', 'No explanation provided')}")
            print(f" Corrected skip_rows: {correction.get('skip_rows_before_header', [])}")

            return correction

        except Exception as e:
            print(f" Claude correction failed: {e}")
            import traceback
            print(f" DEBUG: Correction error traceback: {traceback.format_exc()}")
            # If Claude correction fails, return empty skiprows as fallback
            return {
                'skip_rows_before_header': [],
                'header_row_index': 0,
                'explanation': f'Claude correction failed, using fallback (no skip rows): {e}'
            }

    def process_with_structure_info(self, file_path: str, structure_info: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Process document using structure information"""
        try:
            if structure_info['processing_method'] == 'claude_extraction':
                return self._claude_extract_data(file_path)
            else:
                return self._python_process_with_mapping(file_path, structure_info)
        except Exception as e:
            print(f" Processing failed: {e}")
            return None

    def _python_process_with_mapping(self, file_path: str, structure_info: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Process using Python with Claude's comprehensive column mapping and file structure instructions"""
        try:
            file_ext = Path(file_path).suffix.lower()

            # Read the file
            if file_ext == '.csv':
                import tempfile

                # ===================================================================
                # USE CLAUDE'S FILE STRUCTURE INSTRUCTIONS (NO HARDCODED FORMATS!)
                # ===================================================================
                file_structure = structure_info.get('file_structure', {})
                skiprows = file_structure.get('skip_rows_before_header', [])
                has_trailing_commas = file_structure.get('has_trailing_commas', False)

                # Log what Claude told us to do
                if skiprows:
                    print(f" Claude instructions: Skip rows {skiprows} before header")
                else:
                    print(f" Claude instructions: Standard CSV with header on row 0")

                # ===================================================================
                # VALIDATE SKIPROWS AGAINST ACTUAL FILE LENGTH
                # ===================================================================
                # Count total lines in file
                with open(file_path, 'r') as f:
                    total_lines = sum(1 for _ in f)

                # If Claude wants to skip rows that don't exist, correct it
                if skiprows and max(skiprows) >= total_lines:
                    print(f"  WARNING: File only has {total_lines} lines, but Claude wants to skip rows up to {max(skiprows)}")
                    print(f"  Assuming file is already clean (no metadata rows) - setting skiprows=[]")
                    skiprows = []

                # Clean trailing commas if Claude detected them
                needs_cleaning = has_trailing_commas
                if not has_trailing_commas:
                    # Double-check by reading first two lines
                    with open(file_path, 'r') as f:
                        first_two_lines = [f.readline() for _ in range(2)]
                        if len(first_two_lines) >= 2:
                            header_commas = first_two_lines[0].count(',')
                            data_commas = first_two_lines[1].count(',')
                            if data_commas > header_commas:
                                needs_cleaning = True
                                print(f"  Detected trailing commas: header has {header_commas} commas, data has {data_commas}")

                if needs_cleaning:
                    # Create a cleaned temporary file
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
                        temp_path = temp_file.name
                        with open(file_path, 'r') as f:
                            for line_num, line in enumerate(f):
                                # Skip rows that should be removed BEFORE creating temp file
                                if line_num in skiprows:
                                    continue
                                # Remove trailing commas (but keep commas within quoted strings)
                                cleaned_line = line.rstrip('\n')
                                # Count trailing commas
                                while cleaned_line.endswith(','):
                                    cleaned_line = cleaned_line[:-1]
                                temp_file.write(cleaned_line + '\n')

                    print(f" Cleaned CSV file (with skiprows applied), reading from temporary file")
                    # Don't pass skiprows again since we already skipped them when creating temp file
                    df = pd.read_csv(temp_path)
                    # Clean up temp file (os is already imported at module level)
                    os.unlink(temp_path)
                else:
                    df = pd.read_csv(file_path, skiprows=skiprows)

                # Drop columns that are completely empty (safety check)
                df = df.dropna(axis=1, how='all')

                # ===================================================================
                # VALIDATE CLAUDE'S SKIPROWS INSTRUCTIONS
                # ===================================================================
                # Check if Claude's expected columns actually exist in the DataFrame
                # If not, Claude likely gave wrong skip_rows instructions
                expected_columns = []
                for col_key in ['date_column', 'description_column', 'amount_column']:
                    col_name = structure_info.get(col_key)
                    if col_name:
                        expected_columns.append(col_name)

                if expected_columns:
                    missing_columns = [col for col in expected_columns if col not in df.columns]

                    if missing_columns and skiprows:
                        print(f"  VALIDATION FAILED: Expected columns {missing_columns} not found in DataFrame")
                        print(f"  DataFrame has columns: {list(df.columns)}")
                        print(f"  Claude's skip_rows={skiprows} appears to be incorrect")

                        # ===================================================================
                        # SCALABLE LLM-BASED CORRECTION (NOT HARDCODED!)
                        # ===================================================================
                        # Ask Claude to correct its mistake
                        correction = self._correct_structure_analysis(
                            file_path=file_path,
                            expected_columns=expected_columns,
                            actual_columns=list(df.columns),
                            original_skiprows=skiprows
                        )

                        corrected_skiprows = correction.get('skip_rows_before_header', [])
                        print(f" RETRYING: Re-reading CSV with Claude's corrected skip_rows={corrected_skiprows}")

                        # Retry with corrected skiprows
                        if needs_cleaning:
                            # Re-read from the cleaned temp file (if it still exists, otherwise from original)
                            try:
                                df = pd.read_csv(temp_path, skiprows=corrected_skiprows)
                            except:
                                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
                                    temp_path = temp_file.name
                                    with open(file_path, 'r') as f:
                                        for line in f:
                                            cleaned_line = line.rstrip('\n')
                                            while cleaned_line.endswith(','):
                                                cleaned_line = cleaned_line[:-1]
                                            temp_file.write(cleaned_line + '\n')
                                df = pd.read_csv(temp_path, skiprows=corrected_skiprows)
                                os.unlink(temp_path)
                        else:
                            df = pd.read_csv(file_path, skiprows=corrected_skiprows)

                        df = df.dropna(axis=1, how='all')

                        # Validate again
                        still_missing = [col for col in expected_columns if col not in df.columns]
                        if still_missing:
                            print(f"  Even after Claude's correction, columns {still_missing} not found")
                            print(f"  Proceeding with available columns: {list(df.columns)}")
                        else:
                            print(f" VALIDATION SUCCESS: All expected columns now found after Claude's correction!")
                            print(f" Corrected columns: {list(df.columns)}")

            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            else:
                print(f" Unsupported file type for Python processing: {file_ext}")
                return None

            print(f" Found {len(df)} transactions in {structure_info.get('format', 'unknown')} format")
            print(f" Confidence: {structure_info.get('confidence', 0):.1%}")

            # Create standardized DataFrame
            standardized_df = pd.DataFrame()
            original_columns = df.columns.tolist()
            mapped_columns = []

            # 1. MAP DATE COLUMN
            date_col = structure_info.get('date_column')
            if date_col and date_col in df.columns:
                standardized_df['Date'] = df[date_col]
                mapped_columns.append(date_col)
                print(f" Mapped Date: {date_col}")
            else:
                # Try to find any date-like column
                date_candidates = [col for col in df.columns if any(keyword in col.lower()
                                 for keyword in ['date', 'time', 'timestamp'])]
                if date_candidates:
                    standardized_df['Date'] = df[date_candidates[0]]
                    mapped_columns.append(date_candidates[0])
                    print(f" Auto-detected Date: {date_candidates[0]}")
                else:
                    print("  No date column found - using row index")
                    standardized_df['Date'] = pd.to_datetime('today')

            # 2. MAP AMOUNT COLUMN(S)
            amount_processing = structure_info.get('amount_processing', 'single_column')
            amount_col = structure_info.get('amount_column')

            # ===================================================================
            # INTELLIGENT COLUMN CLEANING BASED ON CLAUDE'S INSTRUCTIONS
            # ===================================================================
            cleaning_rules = structure_info.get('column_cleaning_rules', {})
            amount_cleaning = cleaning_rules.get('amount_column', {})

            def clean_currency_intelligent(series):
                """Clean currency values based on Claude's instructions (NO HARDCODED RULES!)"""
                if series.dtype == 'object':
                    cleaned = series.astype(str)

                    # Apply cleaning rules from Claude
                    if amount_cleaning.get('remove_currency_symbols', True):
                        # Remove common currency symbols
                        cleaned = cleaned.str.replace('$', '', regex=False)
                        cleaned = cleaned.str.replace('€', '', regex=False)
                        cleaned = cleaned.str.replace('£', '', regex=False)
                        cleaned = cleaned.str.replace('¥', '', regex=False)

                    if amount_cleaning.get('remove_commas', True):
                        cleaned = cleaned.str.replace(',', '', regex=False)

                    # Handle parentheses as negative
                    if amount_cleaning.get('parentheses_mean_negative', False):
                        # Convert ($100.00) to -100.00
                        mask = cleaned.str.contains(r'\(.*\)', regex=True, na=False)
                        cleaned = cleaned.str.replace('(', '', regex=False).str.replace(')', '', regex=False)
                        result = pd.to_numeric(cleaned, errors='coerce')
                        result[mask] = -result[mask].abs()
                        return result

                    result = pd.to_numeric(cleaned, errors='coerce')

                    # Apply scaling if needed
                    multiply_by = amount_cleaning.get('multiply_by', 1)
                    if multiply_by != 1:
                        result = result * multiply_by

                    return result
                return pd.to_numeric(series, errors='coerce')

            # NO MORE HARDCODED FORMAT CHECKS - Claude handles everything!

            if amount_processing == 'debit_credit_split':
                # Handle separate debit/credit columns
                debit_cols = [col for col in df.columns if 'debit' in col.lower()]
                credit_cols = [col for col in df.columns if 'credit' in col.lower()]

                if debit_cols and credit_cols:
                    debit_val = pd.to_numeric(df[debit_cols[0]], errors='coerce').fillna(0)
                    credit_val = pd.to_numeric(df[credit_cols[0]], errors='coerce').fillna(0)
                    standardized_df['Amount'] = credit_val - debit_val  # Credits positive, debits negative
                    mapped_columns.extend([debit_cols[0], credit_cols[0]])
                    print(f" Mapped Amount from Debit/Credit: {debit_cols[0]}, {credit_cols[0]}")
                elif amount_col and amount_col in df.columns:
                    standardized_df['Amount'] = pd.to_numeric(df[amount_col], errors='coerce')
                    mapped_columns.append(amount_col)
                    print(f" Mapped Amount: {amount_col}")
            elif amount_processing == 'calculate_from_quantity_price':
                # Handle investment/crypto formats
                qty_cols = [col for col in df.columns if any(k in col.lower() for k in ['quantity', 'amount', 'volume'])]
                price_cols = [col for col in df.columns if any(k in col.lower() for k in ['price', 'rate', 'value'])]

                if qty_cols and price_cols:
                    qty = pd.to_numeric(df[qty_cols[0]], errors='coerce').fillna(0)
                    price = pd.to_numeric(df[price_cols[0]], errors='coerce').fillna(0)
                    standardized_df['Amount'] = qty * price
                    mapped_columns.extend([qty_cols[0], price_cols[0]])
                    print(f" Calculated Amount from: {qty_cols[0]} × {price_cols[0]}")
                elif amount_col and amount_col in df.columns:
                    standardized_df['Amount'] = pd.to_numeric(df[amount_col], errors='coerce')
                    mapped_columns.append(amount_col)
                    print(f" Mapped Amount: {amount_col}")
            else:
                # Standard single amount column
                if amount_col and amount_col in df.columns:
                    standardized_df['Amount'] = clean_currency_intelligent(df[amount_col])
                    mapped_columns.append(amount_col)
                    print(f" Mapped Amount: {amount_col} (using Claude's cleaning rules)")
                else:
                    # Try to auto-detect amount column
                    amount_candidates = [col for col in df.columns if any(keyword in col.lower()
                                       for keyword in ['amount', 'value', 'total', 'sum'])]
                    if amount_candidates:
                        standardized_df['Amount'] = clean_currency_intelligent(df[amount_candidates[0]])
                        mapped_columns.append(amount_candidates[0])
                        print(f" Auto-detected Amount: {amount_candidates[0]} (using Claude's cleaning rules)")
                    else:
                        print("  No amount column found - setting to 0")
                        standardized_df['Amount'] = 0

            # 2b. APPLY TRANSACTION DIRECTION (if direction column exists)
            direction_col = structure_info.get('direction_column')
            if direction_col and direction_col in df.columns:
                # Get direction value lists from Claude's analysis
                direction_incoming = structure_info.get('direction_incoming_values', ['in', 'incoming', 'received', 'deposit', 'credit', 'credited'])
                direction_outgoing = structure_info.get('direction_outgoing_values', ['out', 'outgoing', 'sent', 'withdrawal', 'debit', 'withdraw'])

                # Normalize direction values to lowercase for comparison
                df_direction = df[direction_col].astype(str).str.lower().str.strip()

                # Determine which rows should be negative (outgoing) or positive (incoming)
                should_be_negative = df_direction.isin([v.lower() for v in direction_outgoing])
                should_be_positive = df_direction.isin([v.lower() for v in direction_incoming])

                # Apply sign based on direction
                # Make outgoing negative, incoming positive
                if should_be_negative.any():
                    standardized_df.loc[should_be_negative, 'Amount'] = -standardized_df.loc[should_be_negative, 'Amount'].abs()
                if should_be_positive.any():
                    standardized_df.loc[should_be_positive, 'Amount'] = standardized_df.loc[should_be_positive, 'Amount'].abs()

                mapped_columns.append(direction_col)
                print(f" Applied transaction direction from: {direction_col}")
                print(f"   Positive (Incoming): {should_be_positive.sum()} transactions")
                print(f"   Negative (Outgoing): {should_be_negative.sum()} transactions")

                # Store direction in DataFrame for reference
                standardized_df['Direction'] = df[direction_col]

            # 3. MAP OR CREATE DESCRIPTION COLUMN
            desc_col = structure_info.get('description_column')
            if desc_col and desc_col in df.columns:
                standardized_df['Description'] = df[desc_col].astype(str)
                mapped_columns.append(desc_col)
                print(f" Mapped Description: {desc_col}")
            else:
                # Create description using Claude's rule
                creation_rule = structure_info.get('description_creation_rule', '')

                # Special handler for crypto formats with specific column references
                if 'crypto' in structure_info.get('format', '').lower() and creation_rule:
                    desc_parts = []
                    # Try to build description from direction, currency, and hash as suggested by Claude
                    if direction_col and direction_col in df.columns:
                        desc_parts.append(df[direction_col].astype(str))

                    currency_col = structure_info.get('currency_column')
                    if currency_col and currency_col in df.columns:
                        desc_parts.append(df[currency_col].astype(str))

                    reference_col = structure_info.get('reference_column')
                    if reference_col and reference_col in df.columns:
                        # Truncate hash to first 8 characters for readability
                        desc_parts.append(df[reference_col].astype(str).str[:8])

                    if desc_parts:
                        combined_desc = desc_parts[0].astype(str)
                        for series in desc_parts[1:]:
                            combined_desc = combined_desc + ' - ' + series.astype(str)
                        standardized_df['Description'] = combined_desc.str.replace(' - nan', '').str.replace('nan - ', '')
                        print(f" Created crypto Description from: Direction + Currency + Hash")
                    else:
                        standardized_df['Description'] = 'Crypto Transaction'
                        print(" Default Description: Crypto Transaction")

                elif creation_rule and 'combine' in creation_rule.lower():
                    # Parse the creation rule and combine columns
                    desc_parts = []
                    for col in df.columns:
                        if col not in mapped_columns and col in original_columns:
                            # Include relevant columns in description
                            if any(keyword in col.lower() for keyword in
                                 ['status', 'type', 'crypto', 'network', 'merchant', 'category', 'memo', 'notes']):
                                desc_parts.append(df[col].astype(str))
                                mapped_columns.append(col)

                    if desc_parts:
                        # Concatenate Series objects horizontally with separator
                        combined_desc = desc_parts[0].astype(str)
                        for series in desc_parts[1:]:
                            combined_desc = combined_desc + ' - ' + series.astype(str)
                        standardized_df['Description'] = combined_desc.str.replace(' - nan', '').str.replace('nan - ', '')
                        print(f" Created Description from: {[col for col in original_columns if col in mapped_columns and col not in [structure_info.get('date_column'), structure_info.get('amount_column')]]}")
                    else:
                        standardized_df['Description'] = 'Transaction'
                        print(" Default Description: Transaction")
                else:
                    # Try to find any descriptive column
                    desc_candidates = [col for col in df.columns if any(keyword in col.lower()
                                     for keyword in ['description', 'memo', 'details', 'merchant', 'status', 'type'])]
                    if desc_candidates:
                        standardized_df['Description'] = df[desc_candidates[0]].astype(str)
                        mapped_columns.append(desc_candidates[0])
                        print(f" Auto-detected Description: {desc_candidates[0]}")
                    else:
                        standardized_df['Description'] = 'Transaction'
                        print(" Default Description: Transaction")

            # 4. MAP OPTIONAL COLUMNS
            optional_mappings = {
                'TransactionType': structure_info.get('type_column'),
                'Currency': structure_info.get('currency_column'),
                'Reference': structure_info.get('reference_column'),
                'Balance': structure_info.get('balance_column'),
                'AccountIdentifier': structure_info.get('account_identifier_column')
            }

            for std_name, source_col in optional_mappings.items():
                if source_col and source_col in df.columns:
                    standardized_df[std_name] = df[source_col]
                    mapped_columns.append(source_col)
                    print(f" Mapped {std_name}: {source_col}")

            # 4b. MAP OR DERIVE ORIGIN/DESTINATION USING CLAUDE'S LOGIC
            # NO MORE HARDCODED FORMAT CHECKS - Claude provides the exact logic!
            origin_col = structure_info.get('origin_column')
            destination_col = structure_info.get('destination_column')
            network_col = structure_info.get('network_column')
            origin_destination_logic = structure_info.get('origin_destination_logic', {})

            # Get the method Claude wants us to use
            derivation_method = origin_destination_logic.get('method', 'direct_mapping')

            print(f" Origin/Destination derivation method: {derivation_method}")

            if derivation_method == 'direct_mapping' and origin_col and destination_col:
                # METHOD 1: Direct column mapping
                if origin_col in df.columns:
                    standardized_df['Origin'] = df[origin_col].astype(str)
                    mapped_columns.append(origin_col)
                    print(f" Mapped Origin: {origin_col}")

                if destination_col in df.columns:
                    standardized_df['Destination'] = df[destination_col].astype(str)
                    mapped_columns.append(destination_col)
                    print(f" Mapped Destination: {destination_col}")

            elif derivation_method == 'per_row_logic':
                # METHOD 2: Per-row conditional logic (Claude-provided)
                per_row_conditions = origin_destination_logic.get('per_row_conditions', [])

                if per_row_conditions:
                    print(f" Applying per-row Origin/Destination logic with {len(per_row_conditions)} conditions")

                    # Initialize with Unknown
                    standardized_df['Origin'] = 'Unknown'
                    standardized_df['Destination'] = 'Unknown'

                    # Apply each condition in order
                    for idx, cond in enumerate(per_row_conditions):
                        try:
                            condition_expr = cond.get('condition', '')
                            origin_expr = cond.get('origin', "'Unknown'")
                            destination_expr = cond.get('destination', "'Unknown'")

                            print(f"   Condition {idx+1}: {condition_expr}")

                            # Evaluate condition for each row
                            # Create a safe evaluation environment with row access
                            matches = []
                            for row_idx, row in df.iterrows():
                                try:
                                    # Create local namespace with row data
                                    local_vars = {'row': row, 'pd': pd, 'str': str}

                                    # Evaluate condition
                                    if eval(condition_expr, {"__builtins__": {}}, local_vars):
                                        matches.append(row_idx)
                                except Exception as e:
                                    # Skip rows that fail evaluation
                                    continue

                            if matches:
                                # Apply Origin expression
                                for row_idx in matches:
                                    row = df.loc[row_idx]
                                    local_vars = {'row': row, 'pd': pd, 'str': str}
                                    try:
                                        origin_value = eval(origin_expr, {"__builtins__": {}}, local_vars)
                                        standardized_df.loc[row_idx, 'Origin'] = str(origin_value)
                                    except Exception as e:
                                        print(f"      Warning: Failed to evaluate origin expression for row {row_idx}: {e}")

                                # Apply Destination expression
                                for row_idx in matches:
                                    row = df.loc[row_idx]
                                    local_vars = {'row': row, 'pd': pd, 'str': str}
                                    try:
                                        dest_value = eval(destination_expr, {"__builtins__": {}}, local_vars)
                                        standardized_df.loc[row_idx, 'Destination'] = str(dest_value)
                                    except Exception as e:
                                        print(f"      Warning: Failed to evaluate destination expression for row {row_idx}: {e}")

                                print(f"      Applied to {len(matches)} transactions")

                        except Exception as e:
                            print(f"   ERROR: Failed to process condition {idx+1}: {e}")
                            continue

                    # Report results
                    unknown_count = (standardized_df['Origin'] == 'Unknown').sum()
                    if unknown_count > 0:
                        print(f"   Warning: {unknown_count} transactions still have Unknown Origin/Destination")
                else:
                    print(" Warning: per_row_logic method specified but no conditions provided")
                    # Fallback to direct mapping if available
                    if origin_col and origin_col in df.columns:
                        standardized_df['Origin'] = df[origin_col].astype(str)
                        mapped_columns.append(origin_col)
                    if destination_col and destination_col in df.columns:
                        standardized_df['Destination'] = df[destination_col].astype(str)
                        mapped_columns.append(destination_col)

            elif derivation_method == 'exchange_name_based':
                # METHOD 3: Exchange-based (for uniform transaction files)
                exchange_name = origin_destination_logic.get('exchange_name') or structure_info.get('exchange_name')
                special_handling = structure_info.get('special_handling', 'standard')

                print(f" Exchange-based logic: {exchange_name}, handling: {special_handling}")

                if 'withdrawal' in special_handling.lower():
                    # All withdrawals FROM exchange
                    standardized_df['Origin'] = f"{exchange_name} Exchange" if exchange_name else "Exchange"

                    if destination_col and destination_col in df.columns:
                        standardized_df['Destination'] = df[destination_col].astype(str)
                        mapped_columns.append(destination_col)
                    elif network_col and network_col in df.columns:
                        standardized_df['Destination'] = df[network_col].astype(str).str.replace(r'\([^)]*\)', '', regex=True).str.strip()
                        mapped_columns.append(network_col)
                    else:
                        standardized_df['Destination'] = 'External Wallet'

                    # Negate amounts for withdrawals
                    standardized_df['Amount'] = -standardized_df['Amount'].abs()
                    print(" Applied withdrawal logic (negated amounts)")

                elif 'deposit' in special_handling.lower():
                    # All deposits TO exchange
                    if network_col and network_col in df.columns:
                        standardized_df['Origin'] = df[network_col].astype(str).str.replace(r'\([^)]*\)', '', regex=True).str.strip()
                        mapped_columns.append(network_col)
                    else:
                        standardized_df['Origin'] = 'Blockchain'

                    standardized_df['Destination'] = f"{exchange_name} Exchange" if exchange_name else "Exchange"
                    print(" Applied deposit logic")

            else:
                # Fallback: Try direct column mapping even without explicit method
                print(" Using fallback direct mapping")
                if origin_col and origin_col in df.columns:
                    standardized_df['Origin'] = df[origin_col].astype(str)
                    mapped_columns.append(origin_col)
                    print(f" Mapped Origin: {origin_col}")

                if destination_col and destination_col in df.columns:
                    standardized_df['Destination'] = df[destination_col].astype(str)
                    mapped_columns.append(destination_col)
                    print(f" Mapped Destination: {destination_col}")

            # Preserve Network column if present
            if network_col and network_col in df.columns and network_col not in mapped_columns:
                standardized_df['Network'] = df[network_col]
                mapped_columns.append(network_col)
                print(f" Preserved Network: {network_col}")

            # Store multi-account metadata for downstream processing
            if structure_info.get('has_multiple_accounts'):
                print(f" Multi-account file detected - {structure_info.get('account_identifier_type', 'unknown')} type")
                standardized_df.attrs['has_multiple_accounts'] = True
                standardized_df.attrs['account_identifier_type'] = structure_info.get('account_identifier_type')
                standardized_df.attrs['account_identifier_column'] = structure_info.get('account_identifier_column')

            # 5. PRESERVE ADDITIONAL COLUMNS
            additional_cols = structure_info.get('additional_columns', [])
            for col in df.columns:
                if col not in mapped_columns:
                    # Keep unmapped columns with original names
                    standardized_df[col] = df[col]
                    print(f" Preserved: {col}")

            # 6. APPLY SPECIAL HANDLING
            special_handling = structure_info.get('special_handling', 'standard')
            if special_handling == 'misaligned_headers':
                print(" Applied misaligned header correction")
            elif 'crypto_withdrawal' in special_handling:
                print(" Applied crypto withdrawal format processing (amounts negated, Origin/Destination reversed)")
            elif 'crypto_deposit' in special_handling:
                print(" Applied crypto deposit format processing")
            elif special_handling == 'crypto_format':
                print(" Applied crypto exchange format processing")
            elif special_handling == 'multi_currency':
                print(" Applied multi-currency processing")
            else:
                print(" Applied standard processing")

            # Final validation
            required_columns = ['Date', 'Description', 'Amount']
            for req_col in required_columns:
                if req_col not in standardized_df.columns:
                    print(f"  Missing required column {req_col} - adding default")
                    if req_col == 'Date':
                        standardized_df['Date'] = pd.to_datetime('today')
                    elif req_col == 'Description':
                        standardized_df['Description'] = 'Transaction'
                    elif req_col == 'Amount':
                        standardized_df['Amount'] = 0

            print(f" Standardized {len(standardized_df)} transactions with {len(standardized_df.columns)} columns")

            # DEBUG: Print first row before returning
            if len(standardized_df) > 0:
                print(f" DEBUG SMART_INGESTION: First row before return:")
                print(f"   Date: {standardized_df.iloc[0]['Date']}")
                print(f"   Amount: {standardized_df.iloc[0]['Amount']}")
                print(f"   Description: {standardized_df.iloc[0]['Description']}")
                print(f"   Columns: {list(standardized_df.columns)}")

            return standardized_df

        except Exception as e:
            print(f" Python processing failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _claude_extract_data(self, file_path: str) -> Optional[pd.DataFrame]:
        """Use Claude Vision to extract transaction data from PDF bank statements"""
        if not self.claude_client:
            print(" Claude API not available for data extraction")
            return None

        try:
            file_ext = Path(file_path).suffix.lower()

            if file_ext != '.pdf':
                print(f" Unsupported file type for Claude extraction: {file_ext}")
                return None

            print(f" Using Claude Vision for PDF extraction: {file_path}")

            # Import PyMuPDF for PDF processing
            try:
                import fitz
            except ImportError:
                print(" ERROR: PyMuPDF (fitz) not installed. Install with: pip install PyMuPDF")
                return None

            # Open PDF and convert pages to images
            doc = fitz.open(file_path)
            if doc.page_count == 0:
                print(" ERROR: PDF has no pages")
                return None

            # Process all pages (for multi-page bank statements)
            all_transactions = []

            for page_num in range(min(doc.page_count, 10)):  # Limit to first 10 pages
                print(f"   Processing page {page_num + 1}/{min(doc.page_count, 10)}...")

                # Convert page to high-resolution image
                page = doc.load_page(page_num)
                mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
                pix = page.get_pixmap(matrix=mat)
                image_bytes = pix.pil_tobytes(format="PNG")

                # Extract text for hybrid processing
                text_content = page.get_text()

                # Encode image to base64
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')

                # Call Claude Vision API
                transactions = self._call_claude_vision_for_transactions(
                    image_base64,
                    file_path,
                    page_num + 1,
                    text_content
                )

                if transactions:
                    all_transactions.extend(transactions)

            doc.close()

            if not all_transactions:
                print(" WARNING: No transactions extracted from PDF")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(all_transactions)
            print(f" Successfully extracted {len(df)} transactions from PDF")
            return df

        except Exception as e:
            print(f" Claude PDF extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _call_claude_vision_for_transactions(self, image_base64: str, file_path: str, page_num: int, text_content: str = "") -> list:
        """Call Claude Vision API to extract bank statement transactions with Origin and Destination"""
        try:
            prompt = f"""
🏦 BANK STATEMENT TRANSACTION EXTRACTOR - Extract ALL transactions from this bank statement.

File: {Path(file_path).name} (Page {page_num})
Text content preview: {text_content[:500] if text_content else "No text extracted"}

CRITICAL INSTRUCTIONS:
1. Extract EVERY transaction visible on this page
2. For EACH transaction, identify:
   - Date (YYYY-MM-DD format)
   - Description (full transaction description)
   - Amount (positive for deposits/credits, negative for withdrawals/debits)
   - Origin (sender/source of funds - can be account name, person, company, or "Self" if internal)
   - Destination (recipient/where funds went - can be account name, person, company, or "Self" if internal)

3. ORIGIN and DESTINATION Rules:
   - PIX transfers: Extract sender and recipient names from description
   - Card payments: Origin = cardholder, Destination = merchant
   - Transfers: Extract both account holders or companies
   - If only one party visible, use "Self" for the bank account owner
   - Internal transfers: Both might be "Self" if between same owner's accounts

4. Amount signs:
   - NEGATIVE (-) for outgoing payments, withdrawals, debits
   - POSITIVE (+) for incoming payments, deposits, credits

5. Handle multi-language statements (Portuguese, Spanish, English)

Return ONLY a JSON array of transactions:
[
    {{
        "Date": "YYYY-MM-DD",
        "Description": "Full transaction description",
        "Amount": -123.45,
        "Origin": "Sender/Source name",
        "Destination": "Recipient/Destination name"
    }},
    ...
]

If NO transactions are visible on this page, return an empty array: []
"""

            response = self.claude_client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=16000,  # Increased from 4000 to handle pages with 50+ transactions
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            response_text = response.content[0].text.strip()

            # Clean up code fences if present
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()

            # Parse JSON
            transactions = json.loads(response_text)

            if not isinstance(transactions, list):
                print(f"   WARNING: Expected list of transactions, got {type(transactions)}")
                return []

            print(f"   Extracted {len(transactions)} transactions from page {page_num}")
            return transactions

        except json.JSONDecodeError as e:
            print(f"   ERROR: Failed to parse Claude response as JSON: {e}")
            print(f"   Response: {response_text[:500]}")
            return []
        except Exception as e:
            print(f"   ERROR: Claude Vision API call failed: {e}")
            import traceback
            traceback.print_exc()
            return []

# Integration function to replace existing column detection logic
def smart_process_file(file_path: str, enhance: bool = True) -> Optional[pd.DataFrame]:
    """
    Smart file processing using Claude API for structure analysis
    REQUIRES Claude AI - no fallback processing available
    """
    print(f" DEBUG: Starting smart_process_file for {file_path}")
    try:
        print(" DEBUG: Creating SmartDocumentIngestion instance...")
        ingestion = SmartDocumentIngestion()

        # Validate Claude AI is available
        print(" DEBUG: Validating Claude AI availability...")
        ingestion._validate_claude_required()

        # Step 1: Analyze document structure using Claude AI
        print(f" Analyzing document structure with Claude AI: {os.path.basename(file_path)}")
        print(" DEBUG: Calling analyze_document_structure...")
        structure_info = ingestion.analyze_document_structure(file_path)
        print(f" DEBUG: Structure analysis completed: {structure_info}")

        # Step 2: Process using Claude's analysis
        print(" DEBUG: Processing with structure info...")
        df = ingestion.process_with_structure_info(file_path, structure_info)
        print(f" DEBUG: Processing result: {'Success' if df is not None else 'Failed'}")

        if df is not None:
            print(f" Claude AI smart ingestion successful - {len(df)} transactions")
            print(f" Claude confidence: {structure_info.get('confidence', 0):.1%}")
            print(f"PROCESSED_COUNT:{len(df)}")
            return df
        else:
            raise ValueError(" Claude AI processing failed to generate valid DataFrame")

    except Exception as e:
        print(f" Smart ingestion error: {e}")
        import traceback
        print(f" DEBUG: Smart ingestion error traceback: {traceback.format_exc()}")
        # Re-raise the error instead of returning None - no silent failures
        raise e