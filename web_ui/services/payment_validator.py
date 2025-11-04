"""
Payment Validator - Validation rules for payment proof data
Validates payment data against invoices and business rules
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime
from dateutil import parser as date_parser


class PaymentValidator:
    """Validate payment proof data against invoices"""

    # Validation thresholds
    AMOUNT_TOLERANCE_PERCENT = 2.0  # Allow 2% difference for fees/conversion
    MAX_DAYS_BEFORE_INVOICE = 0  # Payment cannot be before invoice date
    MAX_DAYS_AFTER_INVOICE = 365  # Payment must be within 1 year

    def __init__(self):
        """Initialize validator"""
        pass

    def validate_payment_data(self, payment_data: Dict[str, Any], invoice_data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate payment data against invoice

        Args:
            payment_data: Extracted payment data
            invoice_data: Invoice data from database

        Returns:
            Tuple of (is_valid, errors, warnings)
            - is_valid: True if payment can be accepted (no critical errors)
            - errors: List of critical validation errors
            - warnings: List of non-critical warnings
        """
        errors = []
        warnings = []

        # Check required fields
        missing_errors = self._check_required_fields(payment_data)
        errors.extend(missing_errors)

        # Validate amount
        amount_errors, amount_warnings = self._validate_amount(payment_data, invoice_data)
        errors.extend(amount_errors)
        warnings.extend(amount_warnings)

        # Validate currency
        currency_errors, currency_warnings = self._validate_currency(payment_data, invoice_data)
        errors.extend(currency_errors)
        warnings.extend(currency_warnings)

        # Validate date
        date_errors, date_warnings = self._validate_date(payment_data, invoice_data)
        errors.extend(date_errors)
        warnings.extend(date_warnings)

        # Validate payment method
        method_warnings = self._validate_payment_method(payment_data)
        warnings.extend(method_warnings)

        # Check confidence score
        confidence_warnings = self._check_confidence(payment_data)
        warnings.extend(confidence_warnings)

        is_valid = len(errors) == 0

        return is_valid, errors, warnings

    def _check_required_fields(self, payment_data: Dict[str, Any]) -> List[str]:
        """Check that required fields are present"""
        errors = []

        required_fields = ['payment_date', 'payment_amount', 'payment_currency']

        for field in required_fields:
            value = payment_data.get(field)
            if value is None or value == '' or value == 0:
                errors.append(f"Missing required field: {field}")

        return errors

    def _validate_amount(self, payment_data: Dict[str, Any], invoice_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate payment amount against invoice"""
        errors = []
        warnings = []

        payment_amount = payment_data.get('payment_amount')
        invoice_amount = invoice_data.get('total_amount')

        if not payment_amount:
            return errors, warnings

        if not invoice_amount:
            warnings.append("Cannot validate amount: invoice total_amount not found")
            return errors, warnings

        try:
            payment_amount = float(payment_amount)
            invoice_amount = float(invoice_amount)

            # Calculate difference
            diff = abs(payment_amount - invoice_amount)
            diff_pct = (diff / invoice_amount) * 100

            if diff_pct > self.AMOUNT_TOLERANCE_PERCENT:
                # Check if over or under payment
                if payment_amount > invoice_amount:
                    warnings.append(
                        f"Overpayment detected: Payment ${payment_amount:.2f} exceeds invoice ${invoice_amount:.2f} by ${diff:.2f} ({diff_pct:.1f}%)"
                    )
                else:
                    errors.append(
                        f"Underpayment: Payment ${payment_amount:.2f} is less than invoice ${invoice_amount:.2f} by ${diff:.2f} ({diff_pct:.1f}%)"
                    )
            elif diff_pct > 0.5:  # 0.5% - 2%
                warnings.append(
                    f"Small amount difference: Payment ${payment_amount:.2f} vs Invoice ${invoice_amount:.2f} (${diff:.2f}, {diff_pct:.1f}%)"
                )

        except (ValueError, TypeError) as e:
            errors.append(f"Invalid amount format: {e}")

        return errors, warnings

    def _validate_currency(self, payment_data: Dict[str, Any], invoice_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate payment currency against invoice"""
        errors = []
        warnings = []

        payment_currency = payment_data.get('payment_currency', '').upper()
        invoice_currency = invoice_data.get('currency', 'USD').upper()

        if not payment_currency:
            warnings.append("Payment currency not specified")
            return errors, warnings

        if payment_currency != invoice_currency:
            # Check if common cross-currency payment
            common_conversions = {
                ('USD', 'BRL'),
                ('USD', 'PYG'),
                ('USD', 'EUR'),
                ('BRL', 'USD'),
                ('PYG', 'USD'),
            }

            if (payment_currency, invoice_currency) in common_conversions:
                warnings.append(
                    f"Currency mismatch (common conversion): Payment in {payment_currency}, invoice in {invoice_currency}"
                )
            else:
                errors.append(
                    f"Currency mismatch: Payment in {payment_currency}, invoice in {invoice_currency}"
                )

        return errors, warnings

    def _validate_date(self, payment_data: Dict[str, Any], invoice_data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate payment date against invoice date"""
        errors = []
        warnings = []

        payment_date_str = payment_data.get('payment_date')
        invoice_date_str = invoice_data.get('date')

        if not payment_date_str:
            warnings.append("Payment date not specified")
            return errors, warnings

        if not invoice_date_str:
            warnings.append("Cannot validate date: invoice date not found")
            return errors, warnings

        try:
            payment_date = date_parser.parse(payment_date_str)
            invoice_date = date_parser.parse(invoice_date_str)

            # Calculate days difference
            days_diff = (payment_date - invoice_date).days

            if days_diff < self.MAX_DAYS_BEFORE_INVOICE:
                errors.append(
                    f"Payment date ({payment_date.strftime('%Y-%m-%d')}) is before invoice date ({invoice_date.strftime('%Y-%m-%d')})"
                )
            elif days_diff > self.MAX_DAYS_AFTER_INVOICE:
                warnings.append(
                    f"Payment is {days_diff} days after invoice date (over 1 year old)"
                )
            elif days_diff > 90:  # More than 3 months
                warnings.append(
                    f"Payment is {days_diff} days after invoice date"
                )

        except Exception as e:
            errors.append(f"Date validation error: {e}")

        return errors, warnings

    def _validate_payment_method(self, payment_data: Dict[str, Any]) -> List[str]:
        """Validate payment method"""
        warnings = []

        payment_method = payment_data.get('payment_method', '').strip()

        if not payment_method:
            warnings.append("Payment method not specified")
        elif payment_method.lower() in ['cash', 'dinheiro', 'efectivo']:
            warnings.append("Cash payment - ensure proper documentation")

        return warnings

    def _check_confidence(self, payment_data: Dict[str, Any]) -> List[str]:
        """Check extraction confidence score"""
        warnings = []

        confidence = payment_data.get('confidence', 0.0)

        try:
            confidence = float(confidence)

            if confidence < 0.5:
                warnings.append(
                    f"Low extraction confidence ({confidence:.0%}) - manual verification recommended"
                )
            elif confidence < 0.7:
                warnings.append(
                    f"Medium extraction confidence ({confidence:.0%}) - review suggested"
                )

        except (ValueError, TypeError):
            warnings.append("Could not determine extraction confidence")

        return warnings

    def validate_payment_method_format(self, payment_method: str) -> Tuple[bool, str]:
        """
        Validate and normalize payment method string

        Returns:
            Tuple of (is_valid, normalized_method)
        """
        if not payment_method:
            return False, ''

        payment_method = payment_method.strip()

        # Known payment methods
        known_methods = {
            'PIX': ['pix', 'transferencia pix'],
            'Bank Transfer': ['bank transfer', 'transferencia bancaria', 'wire transfer', 'ted', 'doc'],
            'Credit Card': ['credit card', 'cartao de credito', 'tarjeta de credito'],
            'Debit Card': ['debit card', 'cartao de debito'],
            'Cash': ['cash', 'dinheiro', 'efectivo'],
            'Crypto': ['crypto', 'cryptocurrency', 'bitcoin', 'btc', 'usdt', 'usdc', 'eth'],
            'Check': ['check', 'cheque'],
            'Direct Debit': ['direct debit', 'debito automatico'],
        }

        # Normalize
        method_lower = payment_method.lower()

        for standard_name, variations in known_methods.items():
            if any(var in method_lower for var in variations):
                return True, standard_name

        # Unknown method - return as-is but valid
        return True, payment_method

    def format_validation_report(self, is_valid: bool, errors: List[str], warnings: List[str]) -> str:
        """
        Format validation results as human-readable report

        Args:
            is_valid: Validation result
            errors: List of errors
            warnings: List of warnings

        Returns:
            Formatted report string
        """
        report_lines = []

        if is_valid:
            report_lines.append("✓ Payment validation PASSED")
        else:
            report_lines.append("✗ Payment validation FAILED")

        if errors:
            report_lines.append(f"\nErrors ({len(errors)}):")
            for i, error in enumerate(errors, 1):
                report_lines.append(f"  {i}. {error}")

        if warnings:
            report_lines.append(f"\nWarnings ({len(warnings)}):")
            for i, warning in enumerate(warnings, 1):
                report_lines.append(f"  {i}. {warning}")

        if not errors and not warnings:
            report_lines.append("\nAll validation checks passed.")

        return '\n'.join(report_lines)
