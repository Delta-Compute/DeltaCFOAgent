"""
Receipt Invoice Matcher - Automatically match payment receipts to invoices
Matches based on amount, date, and other criteria
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dateutil import parser as date_parser


class ReceiptInvoiceMatcher:
    """Match payment receipts to invoices using smart algorithms"""

    # Matching thresholds
    AMOUNT_TOLERANCE_PERCENT = 2.0  # Allow 2% difference
    MAX_DATE_DIFF_DAYS = 90  # Payment within 90 days of invoice

    def __init__(self, db_manager):
        """Initialize with database manager"""
        self.db_manager = db_manager

    def find_matching_invoices(self, payment_data: Dict[str, Any], tenant_id: str) -> List[Dict[str, Any]]:
        """
        Find invoices that match the payment receipt data

        Args:
            payment_data: Extracted payment data from receipt
            tenant_id: Tenant ID

        Returns:
            List of matching invoices with match scores
        """
        payment_amount = payment_data.get('payment_amount')
        payment_date_str = payment_data.get('payment_date')
        payment_currency = payment_data.get('payment_currency', 'USD')

        if not payment_amount:
            return []

        try:
            payment_amount = float(payment_amount)
        except (ValueError, TypeError):
            return []

        # Parse payment date
        payment_date = None
        if payment_date_str:
            try:
                if isinstance(payment_date_str, str):
                    payment_date = date_parser.parse(payment_date_str)
                else:
                    payment_date = payment_date_str
            except:
                pass

        # Build query to find candidate invoices
        # Use case-insensitive matching and include partially_paid invoices
        query = """
            SELECT
                id,
                invoice_number,
                customer_name,
                vendor_name,
                total_amount,
                currency,
                date,
                payment_status,
                payment_date as existing_payment_date
            FROM invoices
            WHERE tenant_id = %s
            AND UPPER(payment_status) IN ('PENDING', 'PENDING_REVIEW', 'PARTIALLY_PAID')
            AND total_amount IS NOT NULL
        """
        params = [tenant_id]

        # Add currency filter if specified
        if payment_currency:
            query += " AND currency = %s"
            params.append(payment_currency.upper())

        invoices = self.db_manager.execute_query(query, tuple(params), fetch_all=True)

        if not invoices:
            return []

        # Score each invoice
        matches = []
        for invoice in invoices:
            score = self._calculate_match_score(payment_data, invoice, payment_amount, payment_date)

            if score['total_score'] > 0:
                match_info = {
                    'invoice': invoice,
                    'score': score['total_score'],
                    'score_breakdown': score,
                    'confidence': self._score_to_confidence(score['total_score'])
                }
                matches.append(match_info)

        # Sort by score (highest first)
        matches.sort(key=lambda x: x['score'], reverse=True)

        return matches

    def _calculate_match_score(
        self,
        payment_data: Dict[str, Any],
        invoice: Dict[str, Any],
        payment_amount: float,
        payment_date: Optional[datetime]
    ) -> Dict[str, Any]:
        """
        Calculate match score between payment and invoice

        Returns score breakdown with total_score
        """
        score_breakdown = {
            'amount_score': 0,
            'date_score': 0,
            'currency_score': 0,
            'status_score': 0,
            'total_score': 0
        }

        # Score 1: Amount matching (0-50 points)
        invoice_amount = float(invoice.get('total_amount', 0))
        if invoice_amount > 0:
            amount_diff_pct = abs(payment_amount - invoice_amount) / invoice_amount * 100

            if amount_diff_pct == 0:
                score_breakdown['amount_score'] = 50  # Perfect match
            elif amount_diff_pct <= 0.5:
                score_breakdown['amount_score'] = 45  # Almost perfect
            elif amount_diff_pct <= self.AMOUNT_TOLERANCE_PERCENT:
                score_breakdown['amount_score'] = 40  # Within tolerance
            elif amount_diff_pct <= 5:
                score_breakdown['amount_score'] = 20  # Close
            elif amount_diff_pct <= 10:
                score_breakdown['amount_score'] = 10  # Possible
            else:
                score_breakdown['amount_score'] = 0  # Too different

        # Score 2: Date matching (0-30 points)
        if payment_date and invoice.get('date'):
            try:
                invoice_date_str = invoice['date']
                if not isinstance(invoice_date_str, str):
                    invoice_date_str = str(invoice_date_str)

                invoice_date = date_parser.parse(invoice_date_str)
                days_diff = abs((payment_date - invoice_date).days)

                if days_diff == 0:
                    score_breakdown['date_score'] = 30  # Same day
                elif days_diff <= 7:
                    score_breakdown['date_score'] = 25  # Within a week
                elif days_diff <= 30:
                    score_breakdown['date_score'] = 20  # Within a month
                elif days_diff <= self.MAX_DATE_DIFF_DAYS:
                    score_breakdown['date_score'] = 10  # Within 3 months
                else:
                    score_breakdown['date_score'] = 0  # Too far apart
            except:
                score_breakdown['date_score'] = 5  # Unknown, give small score

        # Score 3: Currency matching (0-10 points)
        payment_currency = payment_data.get('payment_currency', 'USD').upper()
        invoice_currency = invoice.get('currency', 'USD').upper()

        if payment_currency == invoice_currency:
            score_breakdown['currency_score'] = 10
        else:
            score_breakdown['currency_score'] = 0

        # Score 4: Payment status (0-10 points)
        payment_status = invoice.get('payment_status', 'pending').lower()
        if payment_status == 'pending':
            score_breakdown['status_score'] = 10  # Prefer unpaid invoices
        elif payment_status == 'partially_paid':
            score_breakdown['status_score'] = 8  # Partially paid still needs matching
        elif payment_status == 'pending_review':
            score_breakdown['status_score'] = 5
        else:
            score_breakdown['status_score'] = 0

        # Calculate total score
        score_breakdown['total_score'] = (
            score_breakdown['amount_score'] +
            score_breakdown['date_score'] +
            score_breakdown['currency_score'] +
            score_breakdown['status_score']
        )

        return score_breakdown

    def _score_to_confidence(self, score: float) -> str:
        """Convert match score to confidence level"""
        if score >= 90:
            return 'very_high'  # Almost certain match
        elif score >= 75:
            return 'high'  # Strong match
        elif score >= 50:
            return 'medium'  # Possible match
        elif score >= 30:
            return 'low'  # Weak match
        else:
            return 'very_low'  # Unlikely match

    def get_best_match(self, payment_data: Dict[str, Any], tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the single best matching invoice

        Returns:
            Best match with invoice data and score, or None if no good match
        """
        matches = self.find_matching_invoices(payment_data, tenant_id)

        if not matches:
            return None

        best_match = matches[0]

        # Only return if confidence is at least medium
        if best_match['confidence'] in ['very_high', 'high', 'medium']:
            return best_match

        return None

    def format_match_result(self, match: Dict[str, Any]) -> str:
        """Format match result as human-readable text"""
        if not match:
            return "No matching invoice found"

        invoice = match['invoice']
        score = match['score']
        confidence = match['confidence']
        breakdown = match['score_breakdown']

        invoice_number = invoice.get('invoice_number', invoice['id'][:8])
        customer_name = invoice.get('customer_name') or invoice.get('vendor_name', 'Unknown')
        amount = float(invoice.get('total_amount', 0))
        currency = invoice.get('currency', 'USD')

        confidence_label = {
            'very_high': 'Very High (Almost Certain)',
            'high': 'High (Strong Match)',
            'medium': 'Medium (Possible Match)',
            'low': 'Low (Weak Match)',
            'very_low': 'Very Low (Unlikely)'
        }.get(confidence, 'Unknown')

        result = f"""
Match Found: Invoice #{invoice_number} - {customer_name}
Amount: ${amount:.2f} {currency}
Confidence: {confidence_label}
Match Score: {score}/100

Score Breakdown:
  - Amount Match: {breakdown['amount_score']}/50
  - Date Match: {breakdown['date_score']}/30
  - Currency Match: {breakdown['currency_score']}/10
  - Status Score: {breakdown['status_score']}/10
"""
        return result.strip()
