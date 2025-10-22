#!/usr/bin/env python3
"""
Receipt Transaction Matcher Service
Matches receipt data to existing transactions using fuzzy matching algorithms
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from difflib import SequenceMatcher
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DatabaseManager

# Configure logging
logger = logging.getLogger(__name__)


class MatchingStrategy:
    """Enumeration of matching strategies"""
    EXACT_AMOUNT_AND_DATE = "exact_amount_and_date"
    FUZZY_AMOUNT_AND_DATE = "fuzzy_amount_and_date"
    VENDOR_SIMILARITY = "vendor_similarity"
    REFERENCE_NUMBER = "reference_number"
    DESCRIPTION_SIMILARITY = "description_similarity"
    CARD_LAST_4 = "card_last_4"


class TransactionMatch:
    """Represents a potential transaction match"""

    def __init__(
        self,
        transaction_id: int,
        transaction_data: Dict[str, Any],
        confidence: float,
        matching_strategies: List[str],
        match_details: Dict[str, Any]
    ):
        self.transaction_id = transaction_id
        self.transaction_data = transaction_data
        self.confidence = confidence
        self.matching_strategies = matching_strategies
        self.match_details = match_details

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'transaction_id': self.transaction_id,
            'transaction_data': self.transaction_data,
            'confidence': round(self.confidence, 3),
            'matching_strategies': self.matching_strategies,
            'match_details': self.match_details,
            'recommendation': self._get_recommendation()
        }

    def _get_recommendation(self) -> str:
        """Get recommendation based on confidence score"""
        if self.confidence >= 0.95:
            return "auto_apply"  # Very high confidence - can auto-apply
        elif self.confidence >= 0.80:
            return "suggested"  # High confidence - suggest to user
        elif self.confidence >= 0.60:
            return "possible"  # Medium confidence - show as possible match
        else:
            return "uncertain"  # Low confidence - show but mark uncertain


class ReceiptMatcher:
    """Service for matching receipts to existing transactions"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize the receipt matcher

        Args:
            db_manager: Optional database manager (will create one if not provided)
        """
        self.db_manager = db_manager or DatabaseManager()

        # Matching configuration
        self.config = {
            'date_range_days': 3,  # ±3 days from receipt date
            'amount_fuzzy_percent': 5,  # ±5% for fuzzy amount matching
            'vendor_similarity_threshold': 0.6,  # 60% similarity for vendor names
            'description_similarity_threshold': 0.5,  # 50% similarity for descriptions
            'min_confidence_threshold': 0.4,  # Minimum confidence to return a match
            'max_matches_returned': 10  # Maximum number of matches to return
        }

        logger.info("ReceiptMatcher initialized")

    def find_matches(
        self,
        receipt_data: Dict[str, Any],
        limit: Optional[int] = None
    ) -> List[TransactionMatch]:
        """Find matching transactions for a receipt

        Args:
            receipt_data: Extracted receipt data from ReceiptProcessor
            limit: Optional limit on number of matches to return

        Returns:
            List of TransactionMatch objects, sorted by confidence (highest first)
        """
        try:
            logger.info(f"Finding matches for receipt: {receipt_data.get('vendor', 'Unknown')}")

            # Extract key matching fields
            receipt_date = self._parse_date(receipt_data.get('date'))
            receipt_amount = receipt_data.get('amount')
            receipt_vendor = receipt_data.get('vendor', '')
            receipt_description = receipt_data.get('description', '')
            receipt_reference = receipt_data.get('reference_number')
            receipt_card_last_4 = receipt_data.get('card_last_4')

            # Validate required fields
            if not receipt_date:
                logger.warning("Receipt has no date - matching will be limited")

            if not receipt_amount:
                logger.warning("Receipt has no amount - matching will be limited")

            # Get candidate transactions from database
            candidates = self._get_candidate_transactions(
                receipt_date,
                receipt_amount,
                receipt_vendor
            )

            logger.info(f"Found {len(candidates)} candidate transactions")

            if not candidates:
                logger.info("No candidate transactions found")
                return []

            # Score each candidate
            matches = []
            for candidate in candidates:
                match = self._score_transaction(
                    receipt_data,
                    candidate,
                    receipt_date,
                    receipt_amount,
                    receipt_vendor,
                    receipt_description,
                    receipt_reference,
                    receipt_card_last_4
                )

                # Only include matches above minimum confidence threshold
                if match and match.confidence >= self.config['min_confidence_threshold']:
                    matches.append(match)

            # Sort by confidence (highest first)
            matches.sort(key=lambda m: m.confidence, reverse=True)

            # Limit results if specified
            max_limit = limit or self.config['max_matches_returned']
            matches = matches[:max_limit]

            logger.info(f"Returning {len(matches)} matches (confidence >= {self.config['min_confidence_threshold']})")

            return matches

        except Exception as e:
            logger.error(f"Error finding matches: {e}", exc_info=True)
            return []

    def _get_candidate_transactions(
        self,
        receipt_date: Optional[datetime],
        receipt_amount: Optional[float],
        receipt_vendor: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Query database for candidate transactions

        Args:
            receipt_date: Receipt date (for date range filtering)
            receipt_amount: Receipt amount (for amount range filtering)
            receipt_vendor: Receipt vendor (for vendor filtering)

        Returns:
            List of candidate transaction dictionaries
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # Build dynamic query based on available data
                query_parts = ["SELECT * FROM transactions WHERE 1=1"]
                params = []

                # Date range filter (if date available)
                if receipt_date:
                    date_min = receipt_date - timedelta(days=self.config['date_range_days'])
                    date_max = receipt_date + timedelta(days=self.config['date_range_days'])

                    if self.db_manager.db_type == 'postgresql':
                        query_parts.append("AND date BETWEEN %s AND %s")
                    else:
                        query_parts.append("AND date BETWEEN ? AND ?")

                    params.extend([date_min.date(), date_max.date()])

                # Amount range filter (if amount available)
                if receipt_amount:
                    amount_min = receipt_amount * (1 - self.config['amount_fuzzy_percent'] / 100)
                    amount_max = receipt_amount * (1 + self.config['amount_fuzzy_percent'] / 100)

                    if self.db_manager.db_type == 'postgresql':
                        query_parts.append("AND ABS(amount) BETWEEN %s AND %s")
                    else:
                        query_parts.append("AND ABS(amount) BETWEEN ? AND ?")

                    params.extend([amount_min, amount_max])

                # Limit to recent transactions if no date provided
                if not receipt_date:
                    # Last 90 days
                    cutoff_date = datetime.now() - timedelta(days=90)

                    if self.db_manager.db_type == 'postgresql':
                        query_parts.append("AND date >= %s")
                    else:
                        query_parts.append("AND date >= ?")

                    params.append(cutoff_date.date())

                # Order by date (most recent first) and limit
                query_parts.append("ORDER BY date DESC LIMIT 100")

                query = " ".join(query_parts)

                logger.debug(f"Query: {query}")
                logger.debug(f"Params: {params}")

                cursor.execute(query, params)

                # Fetch results as dictionaries
                if self.db_manager.db_type == 'postgresql':
                    columns = [desc[0] for desc in cursor.description]
                    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                else:
                    cursor.row_factory = sqlite3.Row
                    results = [dict(row) for row in cursor.fetchall()]

                return results

        except Exception as e:
            logger.error(f"Error querying candidate transactions: {e}", exc_info=True)
            return []

    def _score_transaction(
        self,
        receipt_data: Dict[str, Any],
        transaction: Dict[str, Any],
        receipt_date: Optional[datetime],
        receipt_amount: Optional[float],
        receipt_vendor: str,
        receipt_description: str,
        receipt_reference: Optional[str],
        receipt_card_last_4: Optional[str]
    ) -> Optional[TransactionMatch]:
        """Score a transaction against receipt data

        Args:
            receipt_data: Full receipt data
            transaction: Transaction database record
            receipt_date, receipt_amount, etc.: Extracted receipt fields

        Returns:
            TransactionMatch object or None if no meaningful match
        """
        try:
            matching_strategies = []
            match_details = {}
            confidence_scores = []

            # 1. REFERENCE NUMBER MATCH (highest priority)
            if receipt_reference and transaction.get('identifier'):
                if self._normalize_reference(receipt_reference) == self._normalize_reference(transaction['identifier']):
                    matching_strategies.append(MatchingStrategy.REFERENCE_NUMBER)
                    match_details['reference_match'] = 'exact'
                    confidence_scores.append(0.99)  # Very high confidence for exact reference match
                    logger.debug(f"Reference number match: {receipt_reference}")

            # 2. CARD LAST 4 MATCH (if available)
            if receipt_card_last_4 and transaction.get('identifier'):
                # Check if transaction identifier contains card last 4
                if receipt_card_last_4 in str(transaction['identifier']):
                    matching_strategies.append(MatchingStrategy.CARD_LAST_4)
                    match_details['card_match'] = receipt_card_last_4
                    confidence_scores.append(0.85)
                    logger.debug(f"Card last 4 match: {receipt_card_last_4}")

            # 3. EXACT AMOUNT AND DATE MATCH
            if receipt_date and receipt_amount:
                transaction_date = self._parse_date(transaction.get('date'))
                transaction_amount = abs(float(transaction.get('amount', 0)))

                if transaction_date:
                    date_diff_days = abs((transaction_date - receipt_date).days)

                    # Exact amount match
                    if abs(transaction_amount - receipt_amount) < 0.01:  # Within 1 cent
                        if date_diff_days == 0:
                            matching_strategies.append(MatchingStrategy.EXACT_AMOUNT_AND_DATE)
                            match_details['amount_match'] = 'exact'
                            match_details['date_diff_days'] = 0
                            confidence_scores.append(0.95)
                            logger.debug(f"Exact amount and date match: ${receipt_amount} on {receipt_date.date()}")
                        elif date_diff_days <= 1:
                            matching_strategies.append(MatchingStrategy.EXACT_AMOUNT_AND_DATE)
                            match_details['amount_match'] = 'exact'
                            match_details['date_diff_days'] = date_diff_days
                            confidence_scores.append(0.90)
                        elif date_diff_days <= self.config['date_range_days']:
                            matching_strategies.append(MatchingStrategy.FUZZY_AMOUNT_AND_DATE)
                            match_details['amount_match'] = 'exact'
                            match_details['date_diff_days'] = date_diff_days
                            confidence_scores.append(0.80 - (date_diff_days * 0.05))
                    else:
                        # Fuzzy amount match
                        amount_diff_percent = abs(transaction_amount - receipt_amount) / receipt_amount * 100

                        if amount_diff_percent <= self.config['amount_fuzzy_percent']:
                            if date_diff_days <= 1:
                                matching_strategies.append(MatchingStrategy.FUZZY_AMOUNT_AND_DATE)
                                match_details['amount_match'] = 'fuzzy'
                                match_details['amount_diff_percent'] = round(amount_diff_percent, 2)
                                match_details['date_diff_days'] = date_diff_days
                                confidence_scores.append(0.75 - (amount_diff_percent * 0.01))
                            elif date_diff_days <= self.config['date_range_days']:
                                matching_strategies.append(MatchingStrategy.FUZZY_AMOUNT_AND_DATE)
                                match_details['amount_match'] = 'fuzzy'
                                match_details['amount_diff_percent'] = round(amount_diff_percent, 2)
                                match_details['date_diff_days'] = date_diff_days
                                confidence_scores.append(0.65 - (amount_diff_percent * 0.01) - (date_diff_days * 0.03))

            # 4. VENDOR NAME SIMILARITY
            if receipt_vendor and transaction.get('description'):
                vendor_similarity = self._calculate_similarity(
                    receipt_vendor,
                    transaction['description']
                )

                if vendor_similarity >= self.config['vendor_similarity_threshold']:
                    matching_strategies.append(MatchingStrategy.VENDOR_SIMILARITY)
                    match_details['vendor_similarity'] = round(vendor_similarity, 3)
                    # Vendor similarity contributes to confidence
                    confidence_scores.append(vendor_similarity * 0.7)  # Scale down slightly
                    logger.debug(f"Vendor similarity: {vendor_similarity:.2%}")

            # 5. DESCRIPTION SIMILARITY
            if receipt_description and transaction.get('description'):
                description_similarity = self._calculate_similarity(
                    receipt_description,
                    transaction['description']
                )

                if description_similarity >= self.config['description_similarity_threshold']:
                    matching_strategies.append(MatchingStrategy.DESCRIPTION_SIMILARITY)
                    match_details['description_similarity'] = round(description_similarity, 3)
                    # Description similarity contributes less than vendor
                    confidence_scores.append(description_similarity * 0.5)
                    logger.debug(f"Description similarity: {description_similarity:.2%}")

            # Calculate overall confidence
            if not confidence_scores:
                return None  # No meaningful matches

            # Take weighted average of confidence scores (favor higher scores)
            confidence_scores.sort(reverse=True)
            if len(confidence_scores) == 1:
                overall_confidence = confidence_scores[0]
            else:
                # Weighted average: first score gets 50%, second gets 30%, rest split remaining 20%
                overall_confidence = confidence_scores[0] * 0.5
                overall_confidence += confidence_scores[1] * 0.3

                if len(confidence_scores) > 2:
                    remaining_weight = 0.2 / (len(confidence_scores) - 2)
                    for score in confidence_scores[2:]:
                        overall_confidence += score * remaining_weight

            # Create match object
            match = TransactionMatch(
                transaction_id=transaction.get('id'),
                transaction_data=transaction,
                confidence=overall_confidence,
                matching_strategies=matching_strategies,
                match_details=match_details
            )

            return match

        except Exception as e:
            logger.error(f"Error scoring transaction: {e}", exc_info=True)
            return None

    def _parse_date(self, date_value: Any) -> Optional[datetime]:
        """Parse date from various formats

        Args:
            date_value: Date as string, datetime, or date object

        Returns:
            datetime object or None
        """
        if not date_value:
            return None

        if isinstance(date_value, datetime):
            return date_value

        if isinstance(date_value, str):
            try:
                # Try ISO format first (YYYY-MM-DD)
                return datetime.fromisoformat(date_value)
            except:
                try:
                    # Try common formats
                    from dateutil import parser
                    return parser.parse(date_value)
                except:
                    logger.warning(f"Could not parse date: {date_value}")
                    return None

        # Try converting to datetime
        try:
            return datetime(date_value.year, date_value.month, date_value.day)
        except:
            return None

    def _normalize_reference(self, reference: str) -> str:
        """Normalize reference number for comparison

        Args:
            reference: Reference number string

        Returns:
            Normalized reference (lowercase, no spaces/special chars)
        """
        if not reference:
            return ""

        # Convert to lowercase and remove common separators
        normalized = str(reference).lower().strip()
        normalized = normalized.replace('-', '').replace('_', '').replace(' ', '')
        normalized = normalized.replace('#', '').replace('/', '')

        return normalized

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity ratio between two strings

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity ratio (0.0 to 1.0)
        """
        if not str1 or not str2:
            return 0.0

        # Normalize strings
        str1_norm = str1.lower().strip()
        str2_norm = str2.lower().strip()

        # Use SequenceMatcher for fuzzy string matching
        similarity = SequenceMatcher(None, str1_norm, str2_norm).ratio()

        # Also check if one string contains the other (partial match bonus)
        if str1_norm in str2_norm or str2_norm in str1_norm:
            # Boost similarity if one contains the other
            similarity = max(similarity, 0.7)

        return similarity

    def suggest_new_transaction(self, receipt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest creating a new transaction from receipt data

        Args:
            receipt_data: Extracted receipt data

        Returns:
            Suggested transaction data
        """
        return {
            'date': receipt_data.get('date'),
            'description': receipt_data.get('description') or f"Receipt: {receipt_data.get('vendor', 'Unknown')}",
            'amount': -abs(receipt_data.get('amount', 0)),  # Expenses are negative
            'entity': receipt_data.get('suggested_business_unit', 'Unknown'),
            'category': receipt_data.get('suggested_category'),
            'origin': receipt_data.get('suggested_business_unit'),
            'destination': receipt_data.get('vendor'),
            'confidence_score': receipt_data.get('confidence', 0.5),
            'source': 'receipt_upload',
            'suggested': True
        }


def test_receipt_matcher():
    """Test the receipt matcher with sample data"""
    try:
        matcher = ReceiptMatcher()
        logger.info("✅ ReceiptMatcher initialized")

        # Sample receipt data
        sample_receipt = {
            'date': '2025-10-20',
            'vendor': 'Amazon',
            'amount': 49.99,
            'currency': 'USD',
            'description': 'Purchase at Amazon.com',
            'reference_number': 'AMZ-123456',
            'confidence': 0.95
        }

        logger.info(f"Testing with sample receipt: {sample_receipt}")

        # Find matches
        matches = matcher.find_matches(sample_receipt)

        logger.info(f"📊 MATCHING RESULTS:")
        logger.info(f"   Found {len(matches)} potential matches")

        for i, match in enumerate(matches, 1):
            match_dict = match.to_dict()
            logger.info(f"\n   Match {i}:")
            logger.info(f"      Transaction ID: {match_dict['transaction_id']}")
            logger.info(f"      Confidence: {match_dict['confidence']:.1%}")
            logger.info(f"      Recommendation: {match_dict['recommendation']}")
            logger.info(f"      Strategies: {', '.join(match_dict['matching_strategies'])}")
            logger.info(f"      Details: {match_dict['match_details']}")

        if not matches:
            suggestion = matcher.suggest_new_transaction(sample_receipt)
            logger.info(f"\n   No matches found. Suggested new transaction:")
            logger.info(f"      {suggestion}")

        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    # Configure logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    test_receipt_matcher()
