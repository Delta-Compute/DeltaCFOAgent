"""
Invoice Payment Manager
Handles multiple partial payments per invoice with automatic status calculation
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal


class PaymentManager:
    """Manage invoice payments with automatic status calculation"""

    def __init__(self, db_manager):
        """Initialize with database manager"""
        self.db_manager = db_manager

    def add_payment(
        self,
        invoice_id: str,
        tenant_id: str,
        payment_amount: float,
        payment_date: str = None,
        payment_currency: str = 'USD',
        payment_method: str = None,
        payment_reference: str = None,
        payment_notes: str = None,
        attachment_id: str = None,
        recorded_by: str = 'system'
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Add a payment record for an invoice

        Args:
            invoice_id: Invoice ID
            tenant_id: Tenant ID
            payment_amount: Amount paid
            payment_date: Date of payment (defaults to today)
            payment_currency: Currency code (defaults to USD)
            payment_method: Payment method (crypto, wire, check, etc.)
            payment_reference: Transaction reference/hash
            payment_notes: Additional notes
            attachment_id: ID of payment proof attachment
            recorded_by: User who recorded the payment

        Returns:
            Tuple of (success, message, payment_data)
        """
        try:
            # Validate invoice exists and belongs to tenant
            invoice = self._get_invoice(invoice_id, tenant_id)
            if not invoice:
                return False, "Invoice not found", None

            # Use today's date if not provided
            if not payment_date:
                payment_date = datetime.now().strftime('%Y-%m-%d')

            # Validate payment amount
            if payment_amount <= 0:
                return False, "Payment amount must be greater than zero", None

            # Insert payment record
            payment_id = str(uuid.uuid4())
            insert_query = """
                INSERT INTO invoice_payments (
                    id, invoice_id, tenant_id, payment_date, payment_amount,
                    payment_currency, payment_method, payment_reference,
                    payment_notes, attachment_id, recorded_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            self.db_manager.execute_query(
                insert_query,
                (payment_id, invoice_id, tenant_id, payment_date, payment_amount,
                 payment_currency, payment_method, payment_reference,
                 payment_notes, attachment_id, recorded_by)
            )

            # Update invoice payment status
            self.update_invoice_payment_status(invoice_id, tenant_id)

            # Get the created payment
            payment_data = self.get_payment(payment_id, tenant_id)

            return True, "Payment recorded successfully", payment_data

        except Exception as e:
            return False, f"Failed to add payment: {str(e)}", None

    def get_payments(
        self,
        invoice_id: str,
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """
        List all payments for an invoice

        Args:
            invoice_id: Invoice ID
            tenant_id: Tenant ID

        Returns:
            List of payment dictionaries
        """
        try:
            query = """
                SELECT
                    p.id, p.invoice_id, p.payment_date, p.payment_amount,
                    p.payment_currency, p.payment_method, p.payment_reference,
                    p.payment_notes, p.attachment_id, p.recorded_by,
                    p.created_at, p.updated_at,
                    a.file_name as attachment_file_name,
                    a.file_path as attachment_file_path
                FROM invoice_payments p
                LEFT JOIN invoice_attachments a ON p.attachment_id = a.id
                WHERE p.invoice_id = %s AND p.tenant_id = %s
                ORDER BY p.payment_date DESC, p.created_at DESC
            """

            payments = self.db_manager.execute_query(
                query,
                (invoice_id, tenant_id),
                fetch_all=True
            )

            return payments if payments else []

        except Exception as e:
            print(f"Error listing payments: {e}")
            return []

    def get_payment(
        self,
        payment_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get single payment details

        Args:
            payment_id: Payment ID
            tenant_id: Tenant ID

        Returns:
            Payment dictionary or None
        """
        try:
            query = """
                SELECT
                    p.id, p.invoice_id, p.payment_date, p.payment_amount,
                    p.payment_currency, p.payment_method, p.payment_reference,
                    p.payment_notes, p.attachment_id, p.recorded_by,
                    p.created_at, p.updated_at,
                    a.file_name as attachment_file_name,
                    a.file_path as attachment_file_path
                FROM invoice_payments p
                LEFT JOIN invoice_attachments a ON p.attachment_id = a.id
                WHERE p.id = %s AND p.tenant_id = %s
            """

            payment = self.db_manager.execute_query(
                query,
                (payment_id, tenant_id),
                fetch_one=True
            )

            return payment

        except Exception as e:
            print(f"Error getting payment: {e}")
            return None

    def calculate_payment_summary(
        self,
        invoice_id: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Calculate payment summary for an invoice

        Args:
            invoice_id: Invoice ID
            tenant_id: Tenant ID

        Returns:
            Dictionary with payment summary:
            - total_amount: Invoice total
            - total_paid: Sum of all payments
            - remaining: Amount still owed
            - payment_count: Number of payments
            - percentage_paid: Percentage of invoice paid
            - status: pending, partially_paid, paid, overpaid
        """
        try:
            # Get invoice total
            invoice = self._get_invoice(invoice_id, tenant_id)
            if not invoice:
                return {
                    'error': 'Invoice not found',
                    'total_amount': 0,
                    'total_paid': 0,
                    'remaining': 0,
                    'payment_count': 0,
                    'percentage_paid': 0,
                    'status': 'pending'
                }

            total_amount = float(invoice.get('total_amount', 0))

            # Calculate total paid
            query = """
                SELECT
                    COALESCE(SUM(payment_amount), 0) as total_paid,
                    COUNT(*) as payment_count
                FROM invoice_payments
                WHERE invoice_id = %s AND tenant_id = %s
            """

            result = self.db_manager.execute_query(
                query,
                (invoice_id, tenant_id),
                fetch_one=True
            )

            total_paid = float(result.get('total_paid', 0)) if result else 0
            payment_count = int(result.get('payment_count', 0)) if result else 0

            # Calculate remaining and percentage
            remaining = total_amount - total_paid
            percentage_paid = (total_paid / total_amount * 100) if total_amount > 0 else 0

            # Determine status
            if total_paid == 0:
                status = 'pending'
            elif total_paid >= total_amount:
                status = 'paid' if total_paid == total_amount else 'overpaid'
            else:
                status = 'partially_paid'

            return {
                'total_amount': total_amount,
                'total_paid': total_paid,
                'remaining': remaining,
                'payment_count': payment_count,
                'percentage_paid': round(percentage_paid, 2),
                'status': status
            }

        except Exception as e:
            print(f"Error calculating payment summary: {e}")
            return {
                'error': str(e),
                'total_amount': 0,
                'total_paid': 0,
                'remaining': 0,
                'payment_count': 0,
                'percentage_paid': 0,
                'status': 'pending'
            }

    def update_invoice_payment_status(
        self,
        invoice_id: str,
        tenant_id: str
    ) -> Tuple[bool, str]:
        """
        Update invoice payment status based on payments

        Args:
            invoice_id: Invoice ID
            tenant_id: Tenant ID

        Returns:
            Tuple of (success, message)
        """
        try:
            # Calculate summary
            summary = self.calculate_payment_summary(invoice_id, tenant_id)

            if 'error' in summary:
                return False, summary['error']

            status = summary['status']

            # Update invoice with new status
            update_query = """
                UPDATE invoices
                SET payment_status = %s
                WHERE id = %s AND tenant_id = %s
            """

            self.db_manager.execute_query(
                update_query,
                (status, invoice_id, tenant_id)
            )

            # If fully paid, set payment_date to last payment date
            if status == 'paid':
                last_payment_query = """
                    SELECT payment_date
                    FROM invoice_payments
                    WHERE invoice_id = %s AND tenant_id = %s
                    ORDER BY payment_date DESC, created_at DESC
                    LIMIT 1
                """
                last_payment = self.db_manager.execute_query(
                    last_payment_query,
                    (invoice_id, tenant_id),
                    fetch_one=True
                )

                if last_payment:
                    self.db_manager.execute_query(
                        """
                        UPDATE invoices
                        SET payment_date = %s
                        WHERE id = %s AND tenant_id = %s
                        """,
                        (last_payment['payment_date'], invoice_id, tenant_id)
                    )

            return True, f"Invoice status updated to {status}"

        except Exception as e:
            return False, f"Failed to update status: {str(e)}"

    def delete_payment(
        self,
        payment_id: str,
        tenant_id: str
    ) -> Tuple[bool, str]:
        """
        Delete a payment record

        Args:
            payment_id: Payment ID
            tenant_id: Tenant ID

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get payment to update invoice after deletion
            payment = self.get_payment(payment_id, tenant_id)
            if not payment:
                return False, "Payment not found"

            invoice_id = payment['invoice_id']

            # Delete payment
            delete_query = """
                DELETE FROM invoice_payments
                WHERE id = %s AND tenant_id = %s
            """

            self.db_manager.execute_query(delete_query, (payment_id, tenant_id))

            # Update invoice status
            self.update_invoice_payment_status(invoice_id, tenant_id)

            return True, "Payment deleted successfully"

        except Exception as e:
            return False, f"Failed to delete payment: {str(e)}"

    def update_payment(
        self,
        payment_id: str,
        tenant_id: str,
        payment_amount: float = None,
        payment_date: str = None,
        payment_method: str = None,
        payment_reference: str = None,
        payment_notes: str = None,
        attachment_id: str = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Update payment details

        Args:
            payment_id: Payment ID
            tenant_id: Tenant ID
            payment_amount: New amount (optional)
            payment_date: New date (optional)
            payment_method: New method (optional)
            payment_reference: New reference (optional)
            payment_notes: New notes (optional)
            attachment_id: New attachment ID (optional)

        Returns:
            Tuple of (success, message, updated_payment_data)
        """
        try:
            # Get existing payment
            payment = self.get_payment(payment_id, tenant_id)
            if not payment:
                return False, "Payment not found", None

            # Build update query dynamically
            updates = []
            params = []

            if payment_amount is not None:
                if payment_amount <= 0:
                    return False, "Payment amount must be greater than zero", None
                updates.append("payment_amount = %s")
                params.append(payment_amount)

            if payment_date is not None:
                updates.append("payment_date = %s")
                params.append(payment_date)

            if payment_method is not None:
                updates.append("payment_method = %s")
                params.append(payment_method)

            if payment_reference is not None:
                updates.append("payment_reference = %s")
                params.append(payment_reference)

            if payment_notes is not None:
                updates.append("payment_notes = %s")
                params.append(payment_notes)

            if attachment_id is not None:
                updates.append("attachment_id = %s")
                params.append(attachment_id)

            if not updates:
                return False, "No updates provided", None

            # Add updated_at
            updates.append("updated_at = CURRENT_TIMESTAMP")

            # Add WHERE clause params
            params.extend([payment_id, tenant_id])

            update_query = f"""
                UPDATE invoice_payments
                SET {', '.join(updates)}
                WHERE id = %s AND tenant_id = %s
            """

            self.db_manager.execute_query(update_query, tuple(params))

            # Update invoice status if amount changed
            if payment_amount is not None:
                self.update_invoice_payment_status(payment['invoice_id'], tenant_id)

            # Get updated payment
            updated_payment = self.get_payment(payment_id, tenant_id)

            return True, "Payment updated successfully", updated_payment

        except Exception as e:
            return False, f"Failed to update payment: {str(e)}", None

    def link_payment_to_attachment(
        self,
        payment_id: str,
        attachment_id: str,
        tenant_id: str
    ) -> Tuple[bool, str]:
        """
        Link a payment to an attachment (payment proof)

        Args:
            payment_id: Payment ID
            attachment_id: Attachment ID
            tenant_id: Tenant ID

        Returns:
            Tuple of (success, message)
        """
        try:
            # Verify both exist
            payment = self.get_payment(payment_id, tenant_id)
            if not payment:
                return False, "Payment not found"

            # Simple update
            update_query = """
                UPDATE invoice_payments
                SET attachment_id = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s AND tenant_id = %s
            """

            self.db_manager.execute_query(
                update_query,
                (attachment_id, payment_id, tenant_id)
            )

            return True, "Payment linked to attachment successfully"

        except Exception as e:
            return False, f"Failed to link payment: {str(e)}"

    def _get_invoice(
        self,
        invoice_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get invoice details (internal helper)"""
        try:
            query = """
                SELECT id, invoice_number, total_amount, payment_status,
                       payment_date, tenant_id
                FROM invoices
                WHERE id = %s AND tenant_id = %s
            """

            invoice = self.db_manager.execute_query(
                query,
                (invoice_id, tenant_id),
                fetch_one=True
            )

            return invoice

        except Exception as e:
            print(f"Error getting invoice: {e}")
            return None
