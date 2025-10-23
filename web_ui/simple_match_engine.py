"""
Simple Match Engine for Transaction Similarity
Provides keyword-based matching as an alternative to ML approaches

This module implements a transparent, fast keyword-matching algorithm for finding
similar transactions based on Origin, Destination, and Description fields.
"""

from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple
import re


def find_similar_simple(
    target_transaction: Dict,
    candidate_transactions: List[Dict],
    min_confidence: float = 0.3
) -> List[Dict]:
    """
    Find similar transactions using simple keyword-based matching.

    Args:
        target_transaction: The transaction to find matches for
        candidate_transactions: Pool of potential matching transactions
        min_confidence: Minimum confidence threshold (0.0-1.0)

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
    matches = []

    # Extract target transaction fields
    target_origin = str(target_transaction.get('origin', '')).strip()
    target_dest = str(target_transaction.get('destination', '')).strip()
    target_desc = str(target_transaction.get('description', '')).strip()
    target_amount = abs(float(target_transaction.get('amount', 0)))

    # Skip if target has no meaningful data
    if not target_origin and not target_dest and not target_desc:
        return []

    for candidate in candidate_transactions:
        # Skip if same transaction
        if candidate.get('transaction_id') == target_transaction.get('transaction_id'):
            continue

        # Extract candidate fields
        candidate_origin = str(candidate.get('origin', '')).strip()
        candidate_dest = str(candidate.get('destination', '')).strip()
        candidate_desc = str(candidate.get('description', '')).strip()
        candidate_amount = abs(float(candidate.get('amount', 0)))

        # Calculate field similarities
        origin_similarity = calculate_field_similarity(target_origin, candidate_origin)
        dest_similarity = calculate_field_similarity(target_dest, candidate_dest)
        desc_similarity = calculate_field_similarity(target_desc, candidate_desc)

        # Calculate amount ratio for penalty
        amount_ratio = 1.0
        if target_amount > 0 and candidate_amount > 0:
            amount_ratio = max(target_amount, candidate_amount) / min(target_amount, candidate_amount)

        # Calculate overall confidence
        confidence, match_details = calculate_confidence(
            origin_similarity,
            dest_similarity,
            desc_similarity,
            amount_ratio
        )

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

    # Sort by confidence (highest first)
    matches.sort(key=lambda x: x['confidence'], reverse=True)

    return matches


def calculate_field_similarity(field1: str, field2: str) -> float:
    """
    Calculate similarity between two text fields using fuzzy matching.

    Uses SequenceMatcher for fuzzy string comparison and keyword overlap.

    Args:
        field1: First text field
        field2: Second text field

    Returns:
        Similarity score between 0.0 (no match) and 1.0 (exact match)

    Examples:
        >>> calculate_field_similarity("Chase Bank", "Chase Bank")
        1.0
        >>> calculate_field_similarity("Chase Bank", "Chase")
        0.65  # Approximate - partial match
        >>> calculate_field_similarity("Anthropic", "Google")
        0.0  # No meaningful similarity
    """
    # Handle empty fields
    if not field1 or not field2:
        return 0.0

    # Normalize for comparison
    field1_norm = field1.upper().strip()
    field2_norm = field2.upper().strip()

    # Exact match
    if field1_norm == field2_norm:
        return 1.0

    # Check if one field contains the other (substring match)
    if field1_norm in field2_norm or field2_norm in field1_norm:
        # Return high score for substring matches
        return 0.85

    # Extract keywords (words 3+ characters)
    keywords1 = set(extract_keywords(field1_norm))
    keywords2 = set(extract_keywords(field2_norm))

    # Calculate keyword overlap
    if keywords1 and keywords2:
        intersection = keywords1.intersection(keywords2)
        union = keywords1.union(keywords2)

        if union:
            keyword_overlap = len(intersection) / len(union)

            # If significant keyword overlap, boost score
            if keyword_overlap > 0:
                # Use SequenceMatcher for character-level similarity
                sequence_similarity = SequenceMatcher(None, field1_norm, field2_norm).ratio()

                # Combine keyword overlap with sequence similarity
                # Weight keyword overlap more heavily (60/40)
                combined_score = (keyword_overlap * 0.6) + (sequence_similarity * 0.4)
                return combined_score

    # Fall back to pure sequence similarity
    return SequenceMatcher(None, field1_norm, field2_norm).ratio()


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
        'DATE', 'TRANSACTION', 'PAYMENT', 'PURCHASE', 'SALE', 'TRANSFER'
    }

    # Extract words (alphanumeric sequences)
    words = re.findall(r'\b[A-Z0-9]{3,}\b', text.upper())

    # Filter out common words
    keywords = [word for word in words if word not in common_words]

    return keywords


def calculate_confidence(
    origin_similarity: float,
    dest_similarity: float,
    desc_similarity: float,
    amount_ratio: float
) -> Tuple[float, Dict]:
    """
    Calculate overall confidence score based on field similarities and amount ratio.

    Scoring logic:
    - High confidence (0.8-1.0): All 3 fields match well
    - Medium confidence (0.5-0.79): 2 of 3 fields match
    - Low confidence (0.3-0.49): 1 of 3 fields match
    - Penalty: -0.2 if amount differs by more than 2x

    Args:
        origin_similarity: Origin field similarity (0.0-1.0)
        dest_similarity: Destination field similarity (0.0-1.0)
        desc_similarity: Description field similarity (0.0-1.0)
        amount_ratio: Ratio of larger amount to smaller amount

    Returns:
        Tuple of (confidence_score, match_details_dict)
    """
    # Threshold for considering a field "matched"
    MATCH_THRESHOLD = 0.6

    # Determine which fields match
    origin_match = origin_similarity >= MATCH_THRESHOLD
    dest_match = dest_similarity >= MATCH_THRESHOLD
    desc_match = desc_similarity >= MATCH_THRESHOLD

    matched_fields = []
    if origin_match:
        matched_fields.append('origin')
    if dest_match:
        matched_fields.append('destination')
    if desc_match:
        matched_fields.append('description')

    num_matches = len(matched_fields)

    # Calculate base confidence based on number of matched fields
    if num_matches == 3:
        # All fields match - high confidence
        # Use weighted average of similarities
        base_confidence = (origin_similarity * 0.3 +
                          dest_similarity * 0.3 +
                          desc_similarity * 0.4)
        # Ensure it's in high confidence range
        base_confidence = max(0.8, min(1.0, base_confidence))

    elif num_matches == 2:
        # Two fields match - medium confidence
        # Average the two matching fields
        similarities = []
        if origin_match:
            similarities.append(origin_similarity)
        if dest_match:
            similarities.append(dest_similarity)
        if desc_match:
            similarities.append(desc_similarity)

        base_confidence = sum(similarities) / len(similarities) if similarities else 0.6
        # Ensure it's in medium confidence range
        base_confidence = max(0.5, min(0.79, base_confidence))

    elif num_matches == 1:
        # One field matches - low confidence
        max_similarity = max(origin_similarity, dest_similarity, desc_similarity)
        base_confidence = max_similarity * 0.7  # Scale down
        # Ensure it's in low confidence range
        base_confidence = max(0.3, min(0.49, base_confidence))

    else:
        # No fields match sufficiently
        base_confidence = max(origin_similarity, dest_similarity, desc_similarity) * 0.5

    # Apply amount penalty if amounts differ significantly
    amount_penalty = 0.0
    if amount_ratio > 2.0:
        amount_penalty = 0.2

    # Calculate final confidence
    final_confidence = max(0.0, base_confidence - amount_penalty)

    # Build match details
    match_details = {
        'origin_similarity': round(origin_similarity, 3),
        'destination_similarity': round(dest_similarity, 3),
        'description_similarity': round(desc_similarity, 3),
        'matched_fields': matched_fields,
        'num_matched_fields': num_matches,
        'amount_ratio': round(amount_ratio, 2),
        'amount_penalty': amount_penalty,
        'base_confidence': round(base_confidence, 3)
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
