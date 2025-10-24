"""
Simple Match Engine for Transaction Similarity
Provides keyword-based matching as an alternative to ML approaches

This module implements a transparent, fast keyword-matching algorithm for finding
similar transactions based on Origin, Destination, and Description fields.
"""

from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple
import re
import logging

logger = logging.getLogger(__name__)


def is_wallet_address(field: str) -> bool:
    """
    Detect if field contains a blockchain wallet address

    Supports:
    - Ethereum/EVM: 0x followed by 40 hex chars (or shortened with ...)
    - Bitcoin: Base58, 26-35 chars starting with 1 or 3
    - Shortened display format: 0x1234...abcd

    Args:
        field: Text field to check

    Returns:
        True if field appears to be a wallet address

    Examples:
        >>> is_wallet_address("0x742d35Cc6634C0532925a3b844Bc454e4438f44e")
        True
        >>> is_wallet_address("0x742d35...438f44e")
        True
        >>> is_wallet_address("Chase Bank")
        False
    """
    if not field or len(field) < 10:
        return False

    field = str(field).strip()

    # Ethereum/EVM style (full address)
    if re.match(r'^0x[a-fA-F0-9]{40}$', field):
        return True

    # Shortened display format (0x...abc)
    if re.match(r'^0x[a-fA-F0-9]{6,10}\.\.\.[a-fA-F0-9]{6,12}$', field):
        return True

    # Bitcoin P2PKH (starts with 1)
    if re.match(r'^1[a-km-zA-HJ-NP-Z1-9]{25,34}$', field):
        return True

    # Bitcoin P2SH (starts with 3)
    if re.match(r'^3[a-km-zA-HJ-NP-Z1-9]{25,34}$', field):
        return True

    # Bitcoin Bech32 (starts with bc1)
    if re.match(r'^bc1[a-zA-HJ-NP-Z0-9]{39,87}$', field):
        return True

    return False


def match_wallet_addresses(addr1: str, addr2: str) -> float:
    """
    Match two wallet addresses with fuzzy matching for shortened formats

    For shortened formats (0x1234...abcd), matches both prefix and suffix.
    Full addresses are compared exactly.

    Args:
        addr1: First wallet address
        addr2: Second wallet address

    Returns:
        Similarity score from 0.0 (no match) to 1.0 (exact match)

    Examples:
        >>> match_wallet_addresses("0x742d35...438f44e", "0x742d35...438f44e")
        1.0
        >>> match_wallet_addresses("0x742d35...438f44e", "0x742d35...999999")
        0.7  # Prefix matches
        >>> match_wallet_addresses("0x123456...abcdef", "0x999999...abcdef")
        0.7  # Suffix matches
        >>> match_wallet_addresses("0x123456...abcdef", "0x999999...999999")
        0.0  # No match
    """
    if not addr1 or not addr2:
        return 0.0

    addr1 = str(addr1).strip()
    addr2 = str(addr2).strip()

    # Exact match
    if addr1 == addr2:
        return 1.0

    # Case-insensitive comparison for hex addresses
    if addr1.lower() == addr2.lower():
        return 1.0

    # Extract prefix and suffix from shortened format
    if '...' in addr1 and '...' in addr2:
        prefix1 = addr1.split('...')[0]
        suffix1 = addr1.split('...')[1] if len(addr1.split('...')) > 1 else ''

        prefix2 = addr2.split('...')[0]
        suffix2 = addr2.split('...')[1] if len(addr2.split('...')) > 1 else ''

        # Both prefix AND suffix match = exact match
        if prefix1.lower() == prefix2.lower() and suffix1.lower() == suffix2.lower():
            return 1.0

        # Prefix OR suffix match = partial match (high confidence)
        if prefix1.lower() == prefix2.lower() or suffix1.lower() == suffix2.lower():
            return 0.7

    # Try comparing full addresses if one is full and one is shortened
    if '...' in addr1 and '...' not in addr2:
        prefix1 = addr1.split('...')[0]
        suffix1 = addr1.split('...')[1] if len(addr1.split('...')) > 1 else ''
        if addr2.lower().startswith(prefix1.lower()) and addr2.lower().endswith(suffix1.lower()):
            return 1.0

    if '...' in addr2 and '...' not in addr1:
        prefix2 = addr2.split('...')[0]
        suffix2 = addr2.split('...')[1] if len(addr2.split('...')) > 1 else ''
        if addr1.lower().startswith(prefix2.lower()) and addr1.lower().endswith(suffix2.lower()):
            return 1.0

    # No match
    return 0.0


def normalize_counterparty(field: str) -> str:
    """
    Normalize counterparty identifiers for direct comparison.

    This function provides a generalized way to normalize any transaction counterparty,
    regardless of whether it's a wallet address, company name, or other identifier.

    Normalization rules:
    - Converts to lowercase for case-insensitive comparison
    - Removes extra whitespace
    - Handles special cases:
      - "None" → "" (empty string for missing data)
      - Wallet addresses → preserved as-is (already normalized by is_wallet_address)
      - Company names → stripped of legal suffixes (LLC, INC, SA, etc.)
      - PIX identifiers → extracts person/company name
      - Bank names → standardized format

    Args:
        field: Raw counterparty field (origin or destination)

    Returns:
        Normalized counterparty string

    Examples:
        >>> normalize_counterparty("0x742d35...438f44e")
        "0x742d35...438f44e"

        >>> normalize_counterparty("MEXC Global Exchange")
        "mexc"

        >>> normalize_counterparty("PIX: John Doe (CPF: 123456)")
        "john doe"

        >>> normalize_counterparty("Delta Mining Paraguay S.A.")
        "delta mining paraguay"

        >>> normalize_counterparty("None")
        ""
    """
    if not field or field.strip() == "" or field.strip().upper() == "NONE":
        return ""

    field = str(field).strip()

    # Preserve wallet addresses as-is (case-insensitive)
    if is_wallet_address(field):
        return field.lower()

    # Convert to lowercase for normalization
    normalized = field.lower()

    # Remove common legal entity suffixes
    legal_suffixes = [
        r'\s+llc$', r'\s+inc\.?$', r'\s+corp\.?$', r'\s+ltd\.?$',
        r'\s+s\.?a\.?$', r'\s+s\.?r\.?l\.?$', r'\s+gmbh$',
        r'\s+limited$', r'\s+corporation$', r'\s+incorporated$'
    ]
    for suffix in legal_suffixes:
        normalized = re.sub(suffix, '', normalized, flags=re.IGNORECASE)

    # Extract name from PIX format: "PIX: Name (CPF/CNPJ: ...)"
    pix_match = re.match(r'pix[:\s]+([a-z0-9\s]+)', normalized, re.IGNORECASE)
    if pix_match:
        normalized = pix_match.group(1).strip()

    # Remove parenthetical content (account numbers, IDs, etc.)
    normalized = re.sub(r'\([^)]*\)', '', normalized)

    # Remove common words/separators
    normalized = re.sub(r'\s*[|/\-]\s*', ' ', normalized)  # Replace separators with space
    normalized = re.sub(r'\s+acct:?\s*\d+', '', normalized, flags=re.IGNORECASE)  # Remove "Acct: 1234"
    normalized = re.sub(r'\s+account:?\s*\d+', '', normalized, flags=re.IGNORECASE)  # Remove "Account: 1234"

    # Normalize whitespace
    normalized = ' '.join(normalized.split())

    # Extract first significant word for exchanges/platforms (heuristic)
    # e.g., "MEXC Global Exchange" → "mexc"
    common_platform_words = ['exchange', 'global', 'platform', 'wallet', 'bank']
    words = normalized.split()
    if len(words) > 1 and words[-1] in common_platform_words:
        # Keep first word only if last word is a platform indicator
        normalized = words[0]

    return normalized.strip()


def find_similar_simple(
    target_transaction: Dict,
    candidate_transactions: List[Dict],
    min_confidence: float = 0.3,
    debug: bool = False
) -> List[Dict]:
    """
    Find similar transactions using simple keyword-based matching.

    Args:
        target_transaction: The transaction to find matches for
        candidate_transactions: Pool of potential matching transactions
        min_confidence: Minimum confidence threshold (0.0-1.0)
        debug: Enable detailed logging for debugging

    Returns:
        List of matching transactions with confidence scores and match details

    Example:
        >>> target = {
        ...     'transaction_id': 'tx1',
        ...     'origin': 'Chase Bank',
        ...     'destination': 'Anthropic',
        ...     'description': 'API Usage Feb 2025',
        ...     'amount': 150.00
        ... }
        >>> candidates = [...]
        >>> matches = find_similar_simple(target, candidates, min_confidence=0.5)
    """
    import logging
    matches = []

    # Extract target transaction fields
    target_origin = str(target_transaction.get('origin', '')).strip()
    target_dest = str(target_transaction.get('destination', '')).strip()
    target_desc = str(target_transaction.get('description', '')).strip()
    # Handle None amounts safely (convert None to 0)
    target_amount_raw = target_transaction.get('amount', 0)
    target_amount = abs(float(target_amount_raw)) if target_amount_raw is not None else 0.0

    # Skip if target has no meaningful data
    if not target_origin and not target_dest and not target_desc:
        return []

    # DEBUG: Log target transaction details
    if debug:
        target_origin_norm = normalize_counterparty(target_origin)
        target_dest_norm = normalize_counterparty(target_dest)
        enrichment_missing = (not target_origin_norm and not target_dest_norm)

        logging.info(f"[SIMPLE_MATCH_DEBUG] Target transaction: {target_transaction.get('transaction_id')}")
        logging.info(f"[SIMPLE_MATCH_DEBUG]   Description: '{target_desc[:80]}...'")
        logging.info(f"[SIMPLE_MATCH_DEBUG]   Origin: '{target_origin[:80]}...' (normalized: '{target_origin_norm}')")
        logging.info(f"[SIMPLE_MATCH_DEBUG]   Destination: '{target_dest[:80]}...' (normalized: '{target_dest_norm}')")
        logging.info(f"[SIMPLE_MATCH_DEBUG]   Amount: ${target_amount}")
        if enrichment_missing:
            logging.info(f"[SIMPLE_MATCH_DEBUG]   ⚠️  WARNING: Enrichment data missing - falling back to description-only matching")
        logging.info(f"[SIMPLE_MATCH_DEBUG] Scoring {len(candidate_transactions)} candidates...")

    candidates_scored = 0
    candidates_below_threshold = 0

    for candidate in candidate_transactions:
        # Skip if same transaction
        if candidate.get('transaction_id') == target_transaction.get('transaction_id'):
            continue

        # Extract candidate fields
        candidate_origin = str(candidate.get('origin', '')).strip()
        candidate_dest = str(candidate.get('destination', '')).strip()
        candidate_desc = str(candidate.get('description', '')).strip()
        # Handle None amounts safely (convert None to 0)
        candidate_amount_raw = candidate.get('amount', 0)
        candidate_amount = abs(float(candidate_amount_raw)) if candidate_amount_raw is not None else 0.0

        # Calculate amount ratio (used for filtering AND penalty calculation)
        amount_ratio = 1.0
        if target_amount > 0 and candidate_amount > 0:
            amount_ratio = max(target_amount, candidate_amount) / min(target_amount, candidate_amount)

            # 🔥 NEW: Reject candidates with amount difference > 2x
            # This prevents matching $10 transactions with $200+ transactions
            if amount_ratio > 2.0:
                # Skip this candidate - amount too different
                candidates_below_threshold += 1
                if debug and candidates_scored < 5:
                    logging.info(f"[SIMPLE_MATCH_DEBUG] Candidate {candidates_scored + 1}: {candidate.get('transaction_id')}")
                    logging.info(f"[SIMPLE_MATCH_DEBUG]   ❌ REJECTED: Amount ratio {amount_ratio:.2f} > 2.0 (${target_amount:.2f} vs ${candidate_amount:.2f})")
                continue

        # Calculate field similarities
        # Use counterparty-specific matching for origin/destination
        origin_similarity = calculate_counterparty_similarity(target_origin, candidate_origin)
        dest_similarity = calculate_counterparty_similarity(target_dest, candidate_dest)
        # Use description-specific matching for description
        desc_similarity = calculate_description_similarity(target_desc, candidate_desc)

        # Calculate overall confidence
        # 🔥 NEW: Pass origin and destination fields for crypto detection
        confidence, match_details = calculate_confidence(
            origin_similarity,
            dest_similarity,
            desc_similarity,
            amount_ratio,
            origin_field=target_origin,  # Pass for crypto detection
            dest_field=target_dest  # Pass for crypto detection
        )

        candidates_scored += 1

        # DEBUG: Log top 5 scoring candidates and why they failed threshold
        if debug and (confidence >= min_confidence or candidates_scored <= 5):
            logging.info(f"[SIMPLE_MATCH_DEBUG] Candidate {candidates_scored}: {candidate.get('transaction_id')}")
            logging.info(f"[SIMPLE_MATCH_DEBUG]   Description: '{candidate_desc[:80]}...'")
            logging.info(f"[SIMPLE_MATCH_DEBUG]   Origin similarity: {origin_similarity:.3f}")
            logging.info(f"[SIMPLE_MATCH_DEBUG]   Dest similarity: {dest_similarity:.3f}")
            logging.info(f"[SIMPLE_MATCH_DEBUG]   Desc similarity: {desc_similarity:.3f}")
            logging.info(f"[SIMPLE_MATCH_DEBUG]   Amount ratio: {amount_ratio:.2f}")
            logging.info(f"[SIMPLE_MATCH_DEBUG]   Final confidence: {confidence:.3f} (threshold: {min_confidence})")
            logging.info(f"[SIMPLE_MATCH_DEBUG]   Match details: {match_details}")
            if confidence < min_confidence:
                logging.info(f"[SIMPLE_MATCH_DEBUG]   ❌ Below threshold - Reason: {match_details.get('rejection_reason', 'Unknown')}")
            else:
                logging.info(f"[SIMPLE_MATCH_DEBUG]   ✅ Above threshold - MATCH!")

        # Only include if meets minimum confidence
        if confidence >= min_confidence:
            # Build match result
            match = {
                'transaction_id': candidate.get('transaction_id'),
                'date': candidate.get('date'),
                'origin': candidate_origin,
                'destination': candidate_dest,
                'description': candidate_desc,
                'amount': candidate.get('amount'),
                'confidence': round(confidence, 3),
                'match_details': match_details,
                'suggested_values': {
                    'classified_entity': candidate.get('classified_entity'),
                    'accounting_category': candidate.get('accounting_category'),
                    'subcategory': candidate.get('subcategory'),
                    'justification': candidate.get('justification')
                }
            }
            matches.append(match)
        else:
            candidates_below_threshold += 1

    # DEBUG: Summary
    if debug:
        logging.info(f"[SIMPLE_MATCH_DEBUG] ========== SUMMARY ==========")
        logging.info(f"[SIMPLE_MATCH_DEBUG] Total candidates scored: {candidates_scored}")
        logging.info(f"[SIMPLE_MATCH_DEBUG] Matches found: {len(matches)}")
        logging.info(f"[SIMPLE_MATCH_DEBUG] Below threshold: {candidates_below_threshold}")
        logging.info(f"[SIMPLE_MATCH_DEBUG] ==============================")

    # Sort by confidence (highest first)
    matches.sort(key=lambda x: x['confidence'], reverse=True)

    return matches


def calculate_counterparty_similarity(field1: str, field2: str) -> float:
    """
    Calculate similarity between two counterparty fields (origin/destination).

    Uses direct normalized comparison instead of keyword extraction to avoid
    false negatives from transaction-specific identifiers (hashes, account numbers, etc.).

    Strategy:
    1. Normalize both counterparties using normalize_counterparty()
    2. Direct string comparison (exact match)
    3. For wallet addresses, use wallet-specific matching
    4. For non-wallets, use sequence similarity on normalized strings

    Args:
        field1: First counterparty field (origin or destination)
        field2: Second counterparty field (origin or destination)

    Returns:
        Similarity score between 0.0 (no match) and 1.0 (exact match)

    Examples:
        >>> calculate_counterparty_similarity("0x742d35...438f44e", "0x742d35...438f44e")
        1.0  # Exact wallet match

        >>> calculate_counterparty_similarity("MEXC Global", "MEXC Exchange")
        1.0  # Both normalize to "mexc"

        >>> calculate_counterparty_similarity("Delta Mining Paraguay S.A.", "Delta Mining Paraguay LLC")
        1.0  # Legal suffixes stripped

        >>> calculate_counterparty_similarity("PIX: John Doe (123)", "PIX: John Doe (456)")
        1.0  # Account numbers removed

        >>> calculate_counterparty_similarity("Chase Bank", "Bank of America")
        0.0  # Different counterparties
    """
    # Handle empty fields
    if not field1 or not field2:
        return 0.0

    # Check if both are wallet addresses (use specialized matching)
    if is_wallet_address(field1) and is_wallet_address(field2):
        return match_wallet_addresses(field1, field2)

    # Normalize both counterparties
    norm1 = normalize_counterparty(field1)
    norm2 = normalize_counterparty(field2)

    # Handle missing/empty data
    if not norm1 or not norm2:
        return 0.0

    # Exact match after normalization
    if norm1 == norm2:
        return 1.0

    # Calculate sequence similarity on normalized strings
    # For counterparties, we want high precision (exact matches), not fuzzy matching
    sequence_sim = SequenceMatcher(None, norm1, norm2).ratio()

    # Only return high confidence if very similar (>= 85%)
    # This prevents false positives like "Chase" vs "Chase Manhattan"
    if sequence_sim >= 0.85:
        return sequence_sim
    else:
        return 0.0


def calculate_description_similarity(desc1: str, desc2: str) -> float:
    """
    Calculate similarity between two description fields.

    Uses keyword-based matching since descriptions contain transaction-specific
    identifiers that should be filtered out.

    Args:
        desc1: First description
        desc2: Second description

    Returns:
        Similarity score between 0.0 (no match) and 1.0 (exact match)

    Examples:
        >>> calculate_description_similarity("Tether transaction - 0.012 USDT", "Tether transaction - 0.045 USDT")
        0.95  # Same type of transaction, different amounts

        >>> calculate_description_similarity("COPETROL AYOLAS PY", "COPETROL PARAGUARI PY")
        0.75  # Same business, different location
    """
    # Handle empty fields
    if not desc1 or not desc2:
        return 0.0

    # Normalize for comparison
    desc1_norm = desc1.upper().strip()
    desc2_norm = desc2.upper().strip()

    # Exact match
    if desc1_norm == desc2_norm:
        return 1.0

    # Extract keywords (words 3+ characters, excluding numbers and common words)
    keywords1 = set(extract_keywords(desc1_norm))
    keywords2 = set(extract_keywords(desc2_norm))

    # If either field has no meaningful keywords, fall back to sequence similarity
    if not keywords1 or not keywords2:
        return SequenceMatcher(None, desc1_norm, desc2_norm).ratio()

    # Calculate keyword overlap (Jaccard similarity)
    intersection = keywords1.intersection(keywords2)
    union = keywords1.union(keywords2)

    if not union:
        # No keywords at all - use pure sequence similarity
        return SequenceMatcher(None, desc1_norm, desc2_norm).ratio()

    keyword_overlap = len(intersection) / len(union)

    # Require at least SOME keyword overlap for description matching
    if keyword_overlap == 0:
        # No keyword overlap = very low similarity
        # Use character-level similarity as fallback but heavily penalized
        sequence_similarity = SequenceMatcher(None, desc1_norm, desc2_norm).ratio()
        return sequence_similarity * 0.3  # Heavy penalty for no keyword match

    # Good keyword overlap - combine with sequence similarity
    sequence_similarity = SequenceMatcher(None, desc1_norm, desc2_norm).ratio()

    # Weight keyword overlap heavily (70%) since it's more meaningful than character similarity
    combined_score = (keyword_overlap * 0.7) + (sequence_similarity * 0.3)

    return combined_score


def calculate_field_similarity(field1: str, field2: str) -> float:
    """
    DEPRECATED: Legacy function for backward compatibility.
    Use calculate_counterparty_similarity() or calculate_description_similarity() instead.

    This function now defaults to description-based matching.
    """
    return calculate_description_similarity(field1, field2)


def extract_keywords(text: str) -> List[str]:
    """
    Extract meaningful keywords from text field.

    Filters out common words and short tokens, focusing on distinctive keywords.

    Args:
        text: Input text

    Returns:
        List of extracted keywords

    Example:
        >>> extract_keywords("PAYMENT TO ANTHROPIC API USAGE")
        ['PAYMENT', 'ANTHROPIC', 'API', 'USAGE']
    """
    # Common words to exclude
    common_words = {
        'THE', 'AND', 'FOR', 'WITH', 'FROM', 'TO', 'AT', 'BY', 'IN', 'ON',
        'A', 'AN', 'OF', 'OR', 'AS', 'IS', 'WAS', 'ARE', 'WERE', 'BE',
        'DATE', 'TRANSACTION', 'PAYMENT', 'PURCHASE', 'SALE', 'TRANSFER',
        'ACCT', 'ACCOUNT', 'ACC',
        # Date/time related words (transaction-specific identifiers)
        'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC',
        'JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER',
        'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN',
        'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'
    }

    # Extract words (alphanumeric sequences)
    words = re.findall(r'\b[A-Z0-9]{3,}\b', text.upper())

    # Filter out common words and pure numbers (like account numbers)
    keywords = [
        word for word in words
        if word not in common_words and not word.isdigit()
    ]

    return keywords


def calculate_confidence(
    origin_similarity: float,
    dest_similarity: float,
    desc_similarity: float,
    amount_ratio: float,
    origin_field: str = "",
    dest_field: str = ""
) -> Tuple[float, Dict]:
    """
    Calculate overall confidence score based on field similarities and amount ratio.

    NEW GENERALIZED APPROACH:
    - Counterparty match (origin or destination) is PRIMARY signal (70% weight)
    - Description similarity is SECONDARY signal (20% weight)
    - Amount similarity is TERTIARY signal (10% weight)

    This approach works for ANY transaction type:
    - Crypto: Matches on wallet addresses
    - Fiat: Matches on normalized merchant/bank names
    - PIX/ACH: Matches on normalized counterparty names

    Fallback behavior when enrichment data is missing:
    - If origin == "None" or destination == "None", falls back to description-only matching
    - Lower confidence threshold (0.4 * desc_similarity) for missing enrichment data

    Args:
        origin_similarity: Origin field similarity (0.0-1.0)
        dest_similarity: Destination field similarity (0.0-1.0)
        desc_similarity: Description field similarity (0.0-1.0)
        amount_ratio: Ratio of larger amount to smaller amount
        origin_field: Original origin text (for missing data detection)
        dest_field: Original destination text (for missing data detection)

    Returns:
        Tuple of (confidence_score, match_details_dict)
    """
    # Detect if enrichment data is missing
    origin_normalized = normalize_counterparty(origin_field)
    dest_normalized = normalize_counterparty(dest_field)
    enrichment_missing = (not origin_normalized and not dest_normalized)

    # Determine best counterparty match
    counterparty_similarity = max(origin_similarity, dest_similarity)

    # Build match details
    matched_fields = []
    if origin_similarity >= 0.85:  # High threshold for counterparty match
        matched_fields.append('origin')
    if dest_similarity >= 0.85:
        matched_fields.append('destination')
    if desc_similarity >= 0.3:  # Lower threshold for description
        matched_fields.append('description')

    # Calculate base confidence using weighted approach
    if counterparty_similarity >= 0.85:
        # Strong counterparty match - high confidence
        # 70% counterparty + 20% description + 10% amount
        amount_sim = 1.0 / amount_ratio if amount_ratio > 1.0 else 1.0
        base_confidence = (
            counterparty_similarity * 0.7 +
            desc_similarity * 0.2 +
            amount_sim * 0.1
        )

    elif enrichment_missing:
        # Enrichment data missing - fall back to description only
        # Lower confidence, mark for re-enrichment
        base_confidence = desc_similarity * 0.4
        matched_fields = ['description'] if desc_similarity >= 0.3 else []
        match_details = {
            'origin_similarity': round(origin_similarity, 3),
            'destination_similarity': round(dest_similarity, 3),
            'description_similarity': round(desc_similarity, 3),
            'matched_fields': matched_fields,
            'num_matched_fields': len(matched_fields),
            'amount_ratio': round(amount_ratio, 2),
            'amount_penalty': 0.0,
            'base_confidence': round(base_confidence, 3),
            'enrichment_missing': True,
            'rejection_reason': 'Origin/Destination enrichment data missing - needs re-enrichment' if base_confidence < 0.3 else None
        }
        return base_confidence, match_details

    else:
        # Weak or no counterparty match - only description matching
        # Low confidence
        base_confidence = desc_similarity * 0.4
        if base_confidence < 0.3:
            # Below threshold - not a match
            match_details = {
                'origin_similarity': round(origin_similarity, 3),
                'destination_similarity': round(dest_similarity, 3),
                'description_similarity': round(desc_similarity, 3),
                'matched_fields': [],
                'num_matched_fields': 0,
                'amount_ratio': round(amount_ratio, 2),
                'amount_penalty': 0.0,
                'base_confidence': 0.0,
                'enrichment_missing': False,
                'rejection_reason': 'No counterparty match and description similarity too low'
            }
            return 0.0, match_details

    # Apply amount penalty if amounts differ significantly (only for strong matches)
    amount_penalty = 0.0
    if amount_ratio > 5.0 and counterparty_similarity >= 0.85:
        # Large amount difference with same counterparty = possible fraud/error
        amount_penalty = 0.1

    # Calculate final confidence
    final_confidence = max(0.0, min(1.0, base_confidence - amount_penalty))

    # Build match details
    match_details = {
        'origin_similarity': round(origin_similarity, 3),
        'destination_similarity': round(dest_similarity, 3),
        'description_similarity': round(desc_similarity, 3),
        'matched_fields': matched_fields,
        'num_matched_fields': len(matched_fields),
        'amount_ratio': round(amount_ratio, 2),
        'amount_penalty': amount_penalty,
        'base_confidence': round(base_confidence, 3),
        'enrichment_missing': False
    }

    return final_confidence, match_details


def format_match_explanation(match_details: Dict) -> str:
    """
    Generate human-readable explanation of why transactions matched.

    Args:
        match_details: Match details dictionary from calculate_confidence

    Returns:
        Human-readable explanation string

    Example:
        >>> details = {
        ...     'matched_fields': ['origin', 'description'],
        ...     'num_matched_fields': 2,
        ...     'amount_penalty': 0.0
        ... }
        >>> format_match_explanation(details)
        'Matched 2 fields: origin, description'
    """
    matched_fields = match_details.get('matched_fields', [])
    num_matched = match_details.get('num_matched_fields', 0)
    amount_penalty = match_details.get('amount_penalty', 0)

    # Build explanation
    if num_matched == 0:
        explanation = "Weak similarity across all fields"
    elif num_matched == 1:
        explanation = f"Matched 1 field: {matched_fields[0]}"
    elif num_matched == 2:
        explanation = f"Matched 2 fields: {', '.join(matched_fields)}"
    else:  # num_matched == 3
        explanation = "Matched all 3 fields: origin, destination, description"

    # Add amount penalty note
    if amount_penalty > 0:
        explanation += f" (amount differs significantly, -{amount_penalty} penalty)"

    return explanation
